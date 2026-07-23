"""대시보드 오케스트레이터: 카드 A/C/D 조립 + W5 통역 패스 + profile/kpi.

api/analyze 핸들러의 유일한 진입점 (핸들러는 cards만 호출 — CLAUDE.md).
통역 배선 지점 = cards (W5 스펙 미결 확정): get_provider() 호출·주입도 여기서.
profile.name·year는 SAINT 연계 전 placeholder — 데모 헤더는 프론트가 병합(W6-F).
"""

import sqlite3
from collections import defaultdict
from datetime import date

from app.adapters.alumni_types import AlumniRecord
from app.cards import card_a, card_c, card_d
from app.core.dept_normalizer import canonical
from app.db.queries import course_queries
from app.llm import translator
from app.llm.providers.anthropic import get_provider
from app.schemas.cards import CategoryCredit, DashboardResponse, KpiStrip, StudentProfile
from app.schemas.input import StudentInput

REPORT_SEMESTER = "2026-1학기"
NEXT_SEMESTER = "2026-2"
GPA_SCALE = 4.3

# 전공측 성격 (학생 전공별 집계) · 교양측 성격 (전공 무관 합산). 표시 순서 = 이 순서.
_MAJOR_CATS = card_a.MAJOR_CATS
_GENERAL_CATS = card_a.GENERAL_CATS


def _credit_summary(student: StudentInput, con: sqlite3.Connection) -> list[CategoryCredit]:
    """이수과목을 성격별 학점으로 집계. 전공측은 학생 전공별로, 교양/자유선택은 전공 무관.

    다전공 참고용 카운트다(요건 판정 아님). 한 과목이 두 성격에 잡히면 각 그룹에 계상된다.
    """
    student_majors: list[str] = []
    for m in (student.department, *student.extra_majors):
        c = canonical(m)
        if c not in student_majors:
            student_majors.append(c)

    agg: dict[tuple[str | None, str], list] = defaultdict(lambda: [0.0, set()])
    for r in course_queries.category_credits(con, student.taken_course_ids):
        mc, cat, cid, credit = r["major_canonical"], r["category"], r["course_id"], r["credit"] or 0
        if cat in _MAJOR_CATS and mc in student_majors:
            key = (mc, cat)
        elif cat in _GENERAL_CATS:
            key = (None, cat)
        else:
            continue
        if cid not in agg[key][1]:
            agg[key][0] += credit
            agg[key][1].add(cid)

    out: list[CategoryCredit] = []
    for mj in student_majors:
        for cat in _MAJOR_CATS:
            if (mj, cat) in agg:
                s, ids = agg[(mj, cat)]
                out.append(CategoryCredit(major=mj, category=cat, credits=s, course_count=len(ids)))
    for cat in _GENERAL_CATS:
        if (None, cat) in agg:
            s, ids = agg[(None, cat)]
            out.append(CategoryCredit(major=None, category=cat, credits=s, course_count=len(ids)))
    return out


def build(
    student: StudentInput,
    con: sqlite3.Connection,
    alumni: list[AlumniRecord],
) -> DashboardResponse:
    a = card_a.build(student, con, alumni)
    c = card_c.build(student, alumni)
    d, evidence = card_d.build(student, con, alumni)

    provider = get_provider()
    a = translator.translate_card_a(a, provider)
    d, evidence = translator.translate_card_d(d, evidence, provider)

    taken_rows = course_queries.list_by_ids(con, student.taken_course_ids)
    earned = sum(r["credit"] or 0 for r in taken_rows)

    profile = StudentProfile(
        name=f"학생 {student.student_id}",
        department=student.department,
        year="—",
        analysis_date=date.today().isoformat(),
        report_semester=REPORT_SEMESTER,
        next_semester=NEXT_SEMESTER,
    )
    kpi = KpiStrip(
        earned_credits=earned,
        gpa=None,  # 성적 데이터 미보유 (SAINT 연계 전)
        gpa_scale=GPA_SCALE,
        similar_alumni_n=d.sample_size,
    )
    return DashboardResponse(
        profile=profile, kpi=kpi, card_a=a, card_c=c, card_d=d, cluster=evidence,
        credit_summary=_credit_summary(student, con),
    )
