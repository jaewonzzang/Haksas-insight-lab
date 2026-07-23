"""card_a.build — 풀 구성/이수 제외/차단/분류/정렬 검증."""

import sqlite3
from pathlib import Path

import pytest

from app.adapters.alumni_types import AlumniRecord, Enrollment
from app.cards import card_a
from app.schemas.input import StudentInput

SCHEMA = (
    Path(__file__).resolve().parents[3] / "app" / "db" / "schema.sql"
).read_text(encoding="utf-8")

# (course_id, name, department, credit, course_type, is_general, description)
COURSES = [
    ("CSE1010", "프로그래밍입문", "컴퓨터공학과", 3.0, "regular", 0, "파이썬 기초"),
    ("CSE2020", "자료구조", "컴퓨터공학과", 3.0, "regular", 0, "파이썬 리스트 트리"),
    ("CSE3030", "알고리즘", "컴퓨터공학과", 3.0, "regular", 0, "파이썬 그래프 탐색"),
    ("CSE4040", "제한과목", "컴퓨터공학과", 3.0, "regular", 0, "파이썬 심화"),
    ("DUM0001", "더미", "컴퓨터공학과", None, "dummy", 0, None),
    ("REL1001", "종교학개론", "전인교육원", 3.0, "regular", 1, "세계 종교 전통"),
    ("PHI1001", "철학산책", "전인교육원", 3.0, "regular", 1, "고전 철학 파이썬"),
]


@pytest.fixture()
def con():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO courses (course_id, course_name, department, credit, year, semester, "
        "course_type, is_general, description_raw) VALUES (?, ?, ?, ?, 2026, 1, ?, ?, ?)",
        COURSES,
    )
    con.executemany(
        "INSERT INTO course_offerings (course_id, year, semester) VALUES (?, 2025, 2)",
        [(c[0],) for c in COURSES],
    )
    con.execute(
        "INSERT INTO course_prerequisites (course_id, prereq_raw, prereq_tree_json) "
        'VALUES (\'CSE3030\', \'선수과목: CSE2020\', \'{"type": "course", "code": "CSE2020"}\')'
    )
    con.execute(
        "INSERT INTO course_restrictions (course_id, target_dept, status, raw_text) "
        "VALUES ('CSE4040', '컴퓨터공학과', 'forbidden', '컴퓨터공학과(불가능)')"
    )
    con.executemany(
        "INSERT INTO course_categories (course_id, major_raw, major_canonical, category) "
        "VALUES (?, ?, ?, ?)",
        [
            ("CSE2020", "컴퓨터공학", "컴퓨터공학과", "전공선택"),
            ("CSE2020", "인공지능학", "인공지능학과", "전공필수"),  # 타전공 구분 — 제외돼야 함
            ("REL1001", None, None, "교양"),
        ],
    )
    yield con
    con.close()


STUDENT = StudentInput(
    student_id="S1", department="컴퓨터공학과", taken_course_ids=["CSE1010"],
)
ALUMNI = [
    AlumniRecord(
        alumni_id="a1", department="컴퓨터공학과",
        enrollment=[Enrollment(course_id=c) for c in ["CSE1010", "CSE2020", "REL1001"]],
    ),
]


def test_build_full_pipeline(con):
    card = card_a.build(STUDENT, con, ALUMNI)
    all_ids = {c.course_id for c in card.candidates}
    assert "CSE1010" not in all_ids        # 이수 과목 제외
    assert "CSE4040" not in all_ids        # forbidden 차단
    assert "DUM0001" not in all_ids        # dummy 제외
    assert {c.course_id for c in card.major} <= {"CSE2020", "CSE3030"}
    assert {c.course_id for c in card.general} <= {"REL1001", "PHI1001"}
    for c in card.candidates:
        assert c.area_label is None                        # A6 미결
        assert c.kind in ("major", "free")
        assert c.factors and c.reason_short and c.why_summary
    # 이수구분 주석: 학생 전공(컴공) 구분만 — 타전공(인공지능학과) 구분은 제외
    by_id = {c.course_id: c for c in card.candidates}
    assert by_id["CSE2020"].categories == ["전공선택"]
    assert by_id["REL1001"].categories == ["교양"]
    assert by_id["CSE3030"].categories == []               # 성격표 없는 과목


def test_deterministic_order(con):
    a = card_a.build(STUDENT, con, ALUMNI)
    b = card_a.build(STUDENT, con, ALUMNI)
    assert [c.course_id for c in a.candidates] == [c.course_id for c in b.candidates]


def test_empty_pool_returns_empty_card(con):
    student = StudentInput(student_id="S2", department="없는학과")
    card = card_a.build(student, con, [])
    assert card.major == []
    assert card.general != []  # 교양 풀(전인교육원)은 학과와 무관하게 항상 포함
