"""카드 D 오케스트레이터: 임베딩 → 유사도 top-N → 이수 트랙 → CardD + ClusterEvidence.

진로 데이터가 없어 진로를 추론하지 않고 대학원 연계 과목 이수를 관측한다
(engines/career/track, OPEN_QUESTIONS A14).
pattern_summary/summary/text 는 W5(llm/translator) 도입 전까지 결정론 폴백.
"""

import sqlite3
from collections import Counter

from app.adapters.alumni_types import AlumniRecord
from app.core.dept_normalizer import canonical, candidate_departments
from app.db.queries import course_queries
from app.engines.career import embedding, similarity, track
from app.schemas.cards import (
    CardD,
    CareerEntry,
    CareerPattern,
    CareerSubChip,
    ClusterEvidence,
    CommonCourse,
    SimilarityFactor,
)
from app.schemas.input import StudentInput

TOP_N = 30


def _empty() -> tuple[CardD, ClusterEvidence]:
    return (
        CardD(
            similar_label="유사 경로 0명", sample_size=0, entries=[],
            sub_title="", sub_chips=[], pattern_summary="",
        ),
        ClusterEvidence(factors=[], common_courses=[], career_patterns=[], summary=""),
    )


def build(
    student: StudentInput,
    con: sqlite3.Connection,
    alumni: list[AlumniRecord],
    top_n: int = TOP_N,
) -> tuple[CardD, ClusterEvidence]:
    # 재학생 제외 — "어디로 갔나"는 이력이 끝난 사람 기준이어야 의미가 있다 (A17).
    with_courses = [r for r in alumni if r.enrollment and r.history_complete is not False]
    sets = [{e.course_id for e in r.enrollment} for r in with_courses]
    taken = set(student.taken_course_ids)

    embedded = embedding.embed_sets(sets, taken)
    if embedded is None:
        return _empty()
    matrix, student_vec = embedded

    ranked = similarity.top_n(student_vec, matrix, top_n)
    subset = [with_courses[i] for i, _ in ranked]
    subset_sets = [sets[i] for i, _ in ranked]
    scores = [s for _, s in ranked]
    n = len(subset)
    if n == 0:
        return _empty()

    groups = track.split(subset)
    entries = [
        CareerEntry(
            cluster_label=g.label,
            type=g.career_type,
            count=g.count,
            share_percent=round(g.count / n * 100),
        )
        for g in groups
    ]

    # sub_chips — 코호트가 실제로 이수한 대학원 연계 과목
    top_grad = track.top_grad_courses(subset)
    grad_names = {
        r["course_id"]: r["course_name"]
        for r in course_queries.list_by_ids(con, [cid for cid, _ in top_grad])
    }
    sub_chips = [
        CareerSubChip(label=grad_names.get(cid, cid), n=cnt) for cid, cnt in top_grad
    ]

    grad_group = next((g for g in groups if g.label == track.TAKEN_LABEL), None)
    card = CardD(
        similar_label=f"유사 이수 경로 {n}명",
        sub_title="이수한 대학원 연계 과목",
        sample_size=n,
        entries=entries,
        sub_chips=sub_chips,
        pattern_summary=(
            f"유사 이수 경로 {n}명 중 {grad_group.count}명"
            f"({round(grad_group.count / n * 100)}%)이 대학원 연계 과목을 이수했습니다."
            if grad_group
            else f"유사 이수 경로 {n}명 중 대학원 연계 과목 이수자는 없습니다."
        ),
    )

    # ClusterEvidence — 결정론 분해 (A13)
    def _jaccard(a: set[str], b: set[str]) -> float:
        return len(a & b) / len(a | b) if (a | b) else 0.0

    depts = {canonical(student.department), *candidate_departments(student.department)}
    factors = [
        SimilarityFactor(
            label="이수과목 중복도",
            percent=round(sum(_jaccard(taken, s) for s in subset_sets) / n * 100),
        ),
        SimilarityFactor(
            label="이수경로 유사도",
            percent=round(sum(scores) / n * 100),
        ),
        SimilarityFactor(
            label="학과 코호트 일치",
            percent=round(sum(1 for r in subset if canonical(r.department) in depts) / n * 100),
        ),
    ]
    course_freq = Counter(cid for s in subset_sets for cid in s)
    top_courses = sorted(course_freq.items(), key=lambda x: (-x[1], x[0]))[:5]
    names = {
        r["course_id"]: r["course_name"]
        for r in course_queries.list_by_ids(con, [cid for cid, _ in top_courses])
    }
    common_courses = [
        CommonCourse(name=names.get(cid, cid), n=cnt) for cid, cnt in top_courses
    ]
    career_patterns = [
        CareerPattern(
            label=g.label,
            type=g.career_type,
            text=f"유사 졸업생 {g.count}명",
        )
        for g in groups
    ]
    evidence = ClusterEvidence(
        factors=factors,
        common_courses=common_courses,
        career_patterns=career_patterns,
        summary=(
            f"이수 패턴이 유사한 졸업생 {n}명의 대학원 연계 과목 이수 여부 기반 "
            "(진학 결과가 아니라 재학 중 선택을 관측한 값)"
        ),
    )
    return card, evidence
