"""4개 실 CSV → s_compass_courses.db 빌드 통합 검증 (스펙 §5).

실데이터(data/raw) 의존. 파일 없으면 skip.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BACKEND_DIR / "data" / "raw"
EXPECTED_CSVS = [
    "개설교과목정보_2024-2.csv",
    "개설교과목정보_2025-1.csv",
    "개설교과목정보_2025-2.csv",
    "개설교과목정보_2026-1.csv",
]
TABLES = [
    "courses", "course_offerings", "course_prerequisites",
    "course_aliases", "course_restrictions", "parse_warnings",
]


@pytest.fixture(scope="module")
def built_db(tmp_path_factory):
    if not all((RAW_DIR / name).exists() for name in EXPECTED_CSVS):
        pytest.skip("data/raw 실 CSV 4개 필요")
    db_path = tmp_path_factory.mktemp("build") / "s_compass_courses.db"
    subprocess.run(
        [sys.executable, str(BACKEND_DIR / "scripts" / "build_course_db.py"),
         "--db", str(db_path)],
        check=True,
        cwd=BACKEND_DIR,
    )
    con = sqlite3.connect(db_path)
    yield con
    con.close()


def test_courses_unique_course_id(built_db):
    """① courses 행수 = 고유 course_id 수 (≈1,807)."""
    n_courses = built_db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    n_ids = built_db.execute(
        "SELECT COUNT(DISTINCT course_id) FROM course_offerings"
    ).fetchone()[0]
    assert n_courses == n_ids
    assert 1500 <= n_courses <= 2200


def test_offerings_reflect_multi_semester(built_db):
    """② 다학기 중복 반영 — 2개 학기 이상 과목 다수(분석상 1,039개)."""
    n_courses = built_db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    n_offerings = built_db.execute(
        "SELECT COUNT(*) FROM course_offerings"
    ).fetchone()[0]
    assert n_offerings > n_courses
    multi = built_db.execute(
        "SELECT COUNT(*) FROM (SELECT course_id FROM course_offerings "
        "GROUP BY course_id HAVING COUNT(*) >= 2)"
    ).fetchone()[0]
    assert multi >= 900


def test_all_six_tables_populated(built_db):
    """③ 6테이블 모두 존재·채워짐."""
    for table in TABLES:
        n = built_db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert n > 0, table


def test_fk_integrity(built_db):
    """④ offerings/prereq/alias/restriction 의 course_id 가 courses 에 존재."""
    for table in ("course_offerings", "course_prerequisites", "course_restrictions"):
        orphans = built_db.execute(
            f"SELECT COUNT(*) FROM {table} t "
            "LEFT JOIN courses c ON c.course_id = t.course_id "
            "WHERE c.course_id IS NULL"
        ).fetchone()[0]
        assert orphans == 0, table
    orphans = built_db.execute(
        "SELECT COUNT(*) FROM course_aliases a "
        "LEFT JOIN courses c ON c.course_id = a.new_course_id "
        "WHERE c.course_id IS NULL"
    ).fetchone()[0]
    assert orphans == 0
