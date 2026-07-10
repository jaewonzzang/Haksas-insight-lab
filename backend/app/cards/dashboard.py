"""대시보드 오케스트레이터: 카드 A/C/D 조립 + W5 통역 패스 + profile/kpi.

api/analyze 핸들러의 유일한 진입점 (핸들러는 cards만 호출 — CLAUDE.md).
통역 배선 지점 = cards (W5 스펙 미결 확정): get_provider() 호출·주입도 여기서.
profile.name·year는 SAINT 연계 전 placeholder — 데모 헤더는 프론트가 병합(W6-F).
"""

import sqlite3
from datetime import date

from app.adapters.alumni_types import AlumniRecord
from app.cards import card_a, card_c, card_d
from app.db.queries import course_queries
from app.llm import translator
from app.llm.providers.anthropic import get_provider
from app.schemas.cards import DashboardResponse, KpiStrip, StudentProfile
from app.schemas.input import StudentInput

REPORT_SEMESTER = "2026-1학기"
NEXT_SEMESTER = "2026-2"
GPA_SCALE = 4.3


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
        profile=profile, kpi=kpi, card_a=a, card_c=c, card_d=d, cluster=evidence
    )
