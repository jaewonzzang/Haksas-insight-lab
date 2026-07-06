"""queries/* SELECT 함수 검증 — in-memory DB + schema.sql."""

import sqlite3
from pathlib import Path

import pytest

from app.db.connection import get_connection
from app.db.queries import course_queries, prereq_queries

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
        "VALUES (?, ?, ?, ?, 2026, 1)",
        [
            ("CSE1010", "프로그래밍입문", "컴퓨터공학과", 3.0),
            ("CSE2020", "자료구조", "컴퓨터공학과", 3.0),
            ("AAT2001", "크리에이티브컴퓨팅", "아트&테크놀로지학과", 3.0),
        ],
    )
    con.executemany(
        "INSERT INTO course_offerings (course_id, year, semester) VALUES (?, ?, ?)",
        [("CSE1010", 2025, 2), ("CSE1010", 2026, 1), ("CSE2020", 2026, 1)],
    )
    con.execute(
        "INSERT INTO course_prerequisites (course_id, prereq_raw, prereq_tree_json) "
        'VALUES (\'CSE2020\', \'선수과목: CSE1010\', \'{"type": "course", "code": "CSE1010"}\')'
    )
    con.execute(
        "INSERT INTO course_aliases (new_course_id, old_course_id, old_course_name, source_type, raw_text) "
        "VALUES ('CSE1010', 'CS101', '컴퓨터입문', 'old_code', '구 CS101')"
    )
    con.execute(
        "INSERT INTO course_restrictions (course_id, target_dept, status, raw_text) "
        "VALUES ('CSE1010', '컴퓨터공학과', 'forbidden', '컴퓨터공학과(불가능)')"
    )
    yield con
    con.close()


def test_get_connection_row_factory_and_fk(tmp_path):
    db = tmp_path / "t.db"
    sqlite3.connect(db).executescript(SCHEMA)
    con = get_connection(db)
    assert con.row_factory is sqlite3.Row
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    con.close()


def test_list_by_department_union(con):
    rows = course_queries.list_by_department(con, ["컴퓨터공학과", "아트&테크놀로지학과"])
    assert {r["course_id"] for r in rows} == {"CSE1010", "CSE2020", "AAT2001"}


def test_list_by_department_empty(con):
    assert course_queries.list_by_department(con, []) == []


def test_get_course(con):
    row = course_queries.get_course(con, "CSE1010")
    assert row["course_name"] == "프로그래밍입문"
    assert course_queries.get_course(con, "NOPE999") is None


def test_list_restrictions_for(con):
    rows = course_queries.list_restrictions_for(con, ["CSE1010", "CSE2020"])
    assert len(rows) == 1
    assert rows[0]["status"] == "forbidden"
    assert course_queries.list_restrictions_for(con, []) == []


def test_list_aliases(con):
    rows = course_queries.list_aliases(con)
    assert [tuple(r) for r in rows] == [("CS101", "컴퓨터입문", "CSE1010")]


def test_list_by_ids(con):
    rows = course_queries.list_by_ids(con, ["CSE1010", "NOPE999"])
    assert [r["course_id"] for r in rows] == ["CSE1010"]
    assert course_queries.list_by_ids(con, []) == []


def test_offered_in_semester(con):
    assert course_queries.offered_in_semester(con, 2) == {"CSE1010"}
    assert course_queries.offered_in_semester(con, 1) == {"CSE1010", "CSE2020"}


def test_get_prereq_tree(con):
    tree = prereq_queries.get_prereq_tree(con, "CSE2020")
    assert tree == {"type": "course", "code": "CSE1010"}
    assert prereq_queries.get_prereq_tree(con, "CSE1010") is None
