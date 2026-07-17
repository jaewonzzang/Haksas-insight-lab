"""card_d — top-N/이수 트랙/sub_chips/ClusterEvidence 결정론 검증.

진로 컬럼이 없어 대학원 연계 과목(G코드) 이수를 관측한다 (A14, engines/career/track).
"""

import sqlite3
from pathlib import Path

import pytest

from app.adapters.alumni_types import AlumniRecord, Enrollment
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
        [
            ("CSE1010", "프로그래밍입문"),
            ("CSE2020", "자료구조"),
            ("AAT3001", "미디어아트"),
            ("CSEG483", "기초 GPU 프로그래밍"),  # 대학원 연계
        ],
    )
    yield con
    con.close()


def _alum(aid, courses, dept="아트&테크놀로지학과"):
    return AlumniRecord(
        alumni_id=aid, department=dept,
        enrollment=[Enrollment(course_id=c) for c in courses],
        career=None,  # 실데이터에 진로 컬럼 없음
    )


ALUMNI = [
    _alum("a1", ["CSE1010", "CSE2020"]),                       # 미이수
    _alum("a2", ["CSE1010", "CSE2020", "CSEG483"]),            # 이수
    _alum("a3", ["CSE1010", "AAT3001", "CSEG483"]),            # 이수
    _alum("a4", ["REL1001", "PHI1001"], dept="화학과"),         # 유사도 낮음
]
STUDENT = StudentInput(
    student_id="S1", department="지식융합미디어학부",
    taken_course_ids=["CSE1010", "CSE2020"],
)


def test_build_card_and_evidence(con):
    card, evidence = card_d.build(STUDENT, con, ALUMNI, top_n=3)
    assert card.sample_size == 3
    assert card.similar_label == "유사 이수 경로 3명"
    assert sum(e.count for e in card.entries) == 3
    assert card.sub_title == "이수한 대학원 연계 과목"
    assert card.sub_chips[0].label == "기초 GPU 프로그래밍"  # 코드 → 과목명
    assert card.sub_chips[0].n == 2
    assert card.pattern_summary
    assert len(evidence.factors) == 3
    assert all(0 <= f.percent <= 100 for f in evidence.factors)
    names = [c.name for c in evidence.common_courses]
    assert "프로그래밍입문" in names  # id → 과목명 매핑
    assert evidence.career_patterns and evidence.summary


def test_entries_split_by_grad_course(con):
    card, _ = card_d.build(STUDENT, con, ALUMNI, top_n=3)
    by_label = {e.cluster_label: e for e in card.entries}
    assert by_label["대학원 연계 과목 이수"].count == 2
    assert by_label["대학원 연계 과목 이수"].type == "grad"
    assert by_label["미이수"].count == 1
    assert "2명" in card.pattern_summary


def test_enrolled_students_excluded(con):
    """'어디로 갔나'는 이력이 끝난 사람 기준이어야 의미가 있다 (A17)."""
    enrolled = _alum("e1", ["CSE1010", "CSE2020", "CSEG483"])
    enrolled.history_complete = False
    card, _ = card_d.build(STUDENT, con, [*ALUMNI, enrolled], top_n=10)
    assert card.sample_size == 4  # enrolled 제외


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
