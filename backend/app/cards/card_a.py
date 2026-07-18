"""카드 A 오케스트레이터: 풀 구성 → 신호 → 결합 → 차단 → CardA.

reason_short/why_summary 는 W5(llm/translator) 도입 전까지 결정론 폴백.
"""

import re
import sqlite3
from typing import NamedTuple

from app.adapters.alumni_types import AlumniRecord
from app.core import year_rules
from app.core.alias_resolver import expand_taken
from app.core.dept_normalizer import candidate_departments
from app.db.queries import course_queries, prereq_queries
from app.engines.recommender import (
    collaborative,
    content_based,
    hybrid,
    preference,
    prereq_filter,
    restriction_filter,
)
from app.engines.recommender.scoring import ScoredCandidate
from app.schemas.cards import CardA, RecommendationFactor, RecommendedCourse
from app.schemas.input import StudentInput

TOP_N_PER_GROUP = 4
CANDIDATES_CAP = 20
TARGET_SEMESTER = 2  # 추천 대상 = 다음 학기 (2026-2)
GENERAL_DEPT = "전인교육원"

# 대학원 연계(G코드: 학과코드+G+숫자3) · 캡스톤 과목은 학부 추천 풀에서 제외 (2026-07-12)
_GRAD_CODE = re.compile(r"[A-Z]{2,4}G\d{3}")


def _excluded_from_pool(course_id: str, course_name: str) -> bool:
    return bool(_GRAD_CODE.fullmatch(course_id)) or "캡스톤" in course_name


def _enrollable(row: sqlite3.Row, student_year: int | None) -> bool:
    """수강학년 불일치 = 신청 불가 → 표시 자체 제외 (2026-07-13 사용자 확정).

    학년 미입력이면 필터 생략.
    """
    if student_year is None:
        return True
    return student_year in year_rules.parse_target_years(row["target_year_raw"])


def _major_departments(student: StudentInput) -> list[str]:
    """주전공+복수전공의 추천 풀 학과 합집합 (원문, 순서 보존 중복 제거)."""
    out: list[str] = []
    for dept in (student.department, *student.extra_majors):
        for d in candidate_departments(dept):
            if d not in out:
                out.append(d)
    return out


class Collected(NamedTuple):
    """가중치와 무관한 수집 결과 — rank 가 가중 결합. 평가 스크립트 재사용점 (A5)."""

    major_pool: list[sqlite3.Row]
    general_pool: list[sqlite3.Row]
    signals_by_label: dict[str, dict[str, float]]
    fulfill: dict[str, float | None]
    restrictions: list[sqlite3.Row]
    student_depts: set[str]


def collect(
    student: StudentInput,
    con: sqlite3.Connection,
    alumni: list[AlumniRecord],
    target_semester: int = TARGET_SEMESTER,
) -> Collected:
    taken = expand_taken(
        set(student.taken_course_ids),
        [tuple(r) for r in course_queries.list_aliases(con)],
    )
    offered = course_queries.offered_in_semester(con, target_semester)

    def _pool(departments: list[str]) -> list[sqlite3.Row]:
        return [
            r
            for r in course_queries.list_by_department(con, departments)
            if r["course_type"] == "regular"
            and r["course_id"] not in taken
            and r["course_id"] in offered
            and not _excluded_from_pool(r["course_id"], r["course_name"])
            and _enrollable(r, student.year)
        ]

    major_pool = _pool(_major_departments(student))
    general_pool = _pool([GENERAL_DEPT])
    pool = major_pool + general_pool
    pool_ids = [r["course_id"] for r in pool]
    student_depts = {student.department, *student.extra_majors, *_major_departments(student)}

    signals_by_label: dict[str, dict[str, float]] = {}
    fulfill: dict[str, float | None] = {}
    restrictions: list[sqlite3.Row] = []
    if pool_ids:
        taken_rows = course_queries.list_by_ids(con, sorted(taken))
        # 강의계획서 속성 (부분 커버리지) — 개요는 콘텐츠 신호에, 팀플·출석은 선호 매칭에
        attrs = course_queries.syllabus_attrs(con, [*pool_ids, *sorted(taken)])
        overviews = {cid: a["overview_text"] for cid, a in attrs.items() if a["overview_text"]}
        content = content_based.score(taken_rows, pool, overviews)
        if content:
            signals_by_label["콘텐츠 유사도"] = content
        # 유사도는 현행 교과과정 과목만 센다 — 폐지 과목이 분모만 키워 옛 졸업생의
        # 표를 깎는다 (collaborative 참조)
        collab = collaborative.score(taken, pool_ids, alumni, course_queries.all_course_ids(con))
        if collab:
            signals_by_label["코호트 선호도"] = collab
        pool_attrs = {cid: attrs[cid] for cid in pool_ids if cid in attrs}
        pref = preference.score(
            student.prefer_team_project,
            student.prefer_low_attendance,
            student.prefer_presentation,
            pool_attrs,
        )
        if pref:
            signals_by_label["사용자 선호 매칭"] = pref
        if student.year is not None:
            signals_by_label["학년 적합도"] = {
                r["course_id"]: year_rules.year_fit_score(
                    student.year, year_rules.parse_recommended_years(r["recommended_year_raw"])
                )
                for r in pool
            }

        trees = {cid: prereq_queries.get_prereq_tree(con, cid) for cid in pool_ids}
        fulfill = prereq_filter.fulfillments(taken, pool_ids, trees)
        restrictions = course_queries.list_restrictions_for(con, pool_ids)

    return Collected(major_pool, general_pool, signals_by_label, fulfill, restrictions, student_depts)


def rank(c: Collected) -> dict[str, ScoredCandidate]:
    # 정규화는 그룹(전공/교양) 내 상대 강도 — combine이 candidate_ids 기준으로 스케일 (2026-07-13)
    scored = {
        **hybrid.combine(c.signals_by_label, c.fulfill, [r["course_id"] for r in c.major_pool]),
        **hybrid.combine(c.signals_by_label, c.fulfill, [r["course_id"] for r in c.general_pool]),
    }
    return restriction_filter.apply(
        scored,
        c.student_depts,
        True,  # StudentInput 에 전공 구분 없음 — 데모 학생은 1전공 관점
        c.restrictions,
    )


def build(
    student: StudentInput,
    con: sqlite3.Connection,
    alumni: list[AlumniRecord],
) -> CardA:
    c = collect(student, con, alumni)
    pool = c.major_pool + c.general_pool
    pool_ids = [r["course_id"] for r in pool]
    if not pool_ids:
        return CardA(major=[], general=[], candidates=[])
    scored = rank(c)

    major_ids = {r["course_id"] for r in c.major_pool}
    rows_by_id = {r["course_id"]: r for r in pool}
    ranked = sorted(
        (cid for cid in pool_ids if cid in scored),
        key=lambda cid: (-scored[cid].score_percent, cid),
    )
    major_top = [c for c in ranked if c in major_ids][:TOP_N_PER_GROUP]
    general_top = [c for c in ranked if c not in major_ids][:TOP_N_PER_GROUP]

    def _course(cid: str) -> RecommendedCourse:
        row, sc = rows_by_id[cid], scored[cid]
        is_major = cid in major_ids
        return RecommendedCourse(
            course_id=cid,
            course_name=row["course_name"],
            credit=row["credit"],
            grade=sc.grade,
            score_percent=sc.score_percent,
            reason_short=_fallback_reason(sc),
            kind="major" if is_major else "free",
            kind_label="전공" if is_major else "교양",
            area_label=None,  # A6 미결 — 교양 영역 매핑 없음
            factors=[RecommendationFactor(**f.model_dump()) for f in sc.factors],
            why_summary=f"{sc.grade} · 추천도 {sc.score_percent}%",
        )

    return CardA(
        major=[_course(c) for c in major_top],
        general=[_course(c) for c in general_top],
        candidates=[_course(c) for c in ranked[:CANDIDATES_CAP]],
    )


def _fallback_reason(sc: ScoredCandidate) -> str:
    """W5 llm/translator 도입 전 결정론 1줄 (통역 대체)."""
    pos = [f for f in sc.factors if f.kind == "pos"]
    if not pos:
        return "신호 부족 — 참고용 추천"
    top = max(pos, key=lambda f: f.weight_percent)
    return f"{top.label} 신호가 가장 강한 과목"
