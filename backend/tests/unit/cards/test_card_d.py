"""card_d — top-N/클러스터/sub_chips/ClusterEvidence 결정론 검증."""

import sqlite3
from pathlib import Path

import pytest

from app.adapters.alumni_types import AlumniRecord, Career, Enrollment
from app.cards import card_d
from app.schemas.input import StudentInput

SCHEMA = (
    Path(__file__).resolve().parents[3] / "app" / "db" / "schema.sql"
).read_text(encoding="utf-8")


@pytest.fixture()
def con():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO courses (course_id, course_name, department, credit, year, semester) "
        "VALUES (?, ?, '컴퓨터공학과', 3.0, 2026, 1)",
        [("CSE1010", "프로그래밍입문"), ("CSE2020", "자료구조"), ("AAT3001", "미디어아트")],
    )
    yield con
    con.close()


def _alum(aid, courses, ctype, label, dept="아트&테크놀로지학과"):
    return AlumniRecord(
        alumni_id=aid, department=dept,
        enrollment=[Enrollment(course_id=c) for c in courses],
        career=Career(type=ctype, label=label),
    )


ALUMNI = [
    _alum("a1", ["CSE1010", "CSE2020"], "job", "IT 취업"),
    _alum("a2", ["CSE1010", "CSE2020", "AAT3001"], "job", "IT 취업"),
    _alum("a3", ["CSE1010", "AAT3001"], "grad", "국내 대학원 (CS)"),
    _alum("a4", ["REL1001", "PHI1001"], "other", "창업", dept="화학과"),
]
STUDENT = StudentInput(
    student_id="S1", department="지식융합미디어학부",
    taken_course_ids=["CSE1010", "CSE2020"],
)


def test_build_card_and_evidence(con):
    card, evidence = card_d.build(STUDENT, con, ALUMNI, top_n=3)
    assert card.sample_size == 3
    assert card.similar_label == "유사 경로 3명"
    assert sum(e.count for e in card.entries) == 3
    assert card.sub_title == "대학원 진학 세부 분포"
    assert card.sub_chips[0].label == "국내 대학원 (CS)"
    assert card.pattern_summary
    assert len(evidence.factors) == 3
    assert all(0 <= f.percent <= 100 for f in evidence.factors)
    names = [c.name for c in evidence.common_courses]
    assert "프로그래밍입문" in names  # id → 과목명 매핑
    assert evidence.career_patterns and evidence.summary


def test_deterministic(con):
    a = card_d.build(STUDENT, con, ALUMNI, top_n=3)
    b = card_d.build(STUDENT, con, ALUMNI, top_n=3)
    assert a == b


def test_no_enrollment_alumni(con):
    empty = [AlumniRecord(alumni_id="x", department="d")]
    card, evidence = card_d.build(STUDENT, con, empty)
    assert card.sample_size == 0
    assert card.entries == []
    assert evidence.factors == []
