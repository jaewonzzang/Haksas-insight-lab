"""courses·course_restrictions·course_aliases 관련 SELECT 묶음."""

import sqlite3
from typing import Optional, Sequence


def list_by_department(
    con: sqlite3.Connection, departments: Sequence[str]
) -> list[sqlite3.Row]:
    """departments 합집합(원문 학과명)에 속한 과목 전부."""
    if not departments:
        return []
    marks = ", ".join("?" for _ in departments)
    return con.execute(
        f"SELECT * FROM courses WHERE department IN ({marks})",
        tuple(departments),
    ).fetchall()


def list_by_ids(
    con: sqlite3.Connection, course_ids: Sequence[str]
) -> list[sqlite3.Row]:
    if not course_ids:
        return []
    marks = ", ".join("?" for _ in course_ids)
    return con.execute(
        f"SELECT * FROM courses WHERE course_id IN ({marks})", tuple(course_ids)
    ).fetchall()


def offered_in_semester(con: sqlite3.Connection, semester: int) -> set[str]:
    """해당 학기(1|2)에 개설 이력이 있는 course_id 집합 (연도 무관)."""
    rows = con.execute(
        "SELECT DISTINCT course_id FROM course_offerings WHERE semester = ?",
        (semester,),
    ).fetchall()
    return {r["course_id"] for r in rows}


def get_course(con: sqlite3.Connection, course_id: str) -> Optional[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM courses WHERE course_id = ?", (course_id,)
    ).fetchone()


def list_restrictions_for(
    con: sqlite3.Connection, course_ids: Sequence[str]
) -> list[sqlite3.Row]:
    if not course_ids:
        return []
    marks = ", ".join("?" for _ in course_ids)
    return con.execute(
        f"SELECT * FROM course_restrictions WHERE course_id IN ({marks})",
        tuple(course_ids),
    ).fetchall()


def list_aliases(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """core/alias_resolver.expand_taken 입력용 전체 별칭 3열."""
    return con.execute(
        "SELECT old_course_id, old_course_name, new_course_id FROM course_aliases"
    ).fetchall()
