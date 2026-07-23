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


def all_course_ids(con: sqlite3.Connection) -> set[str]:
    """현행 교과과정(courses 테이블)의 전체 course_id."""
    return {r["course_id"] for r in con.execute("SELECT course_id FROM courses")}


def offered_in_semester(con: sqlite3.Connection, semester: int) -> set[str]:
    """해당 학기(1|2)에 개설 이력이 있고 아직 살아있는 course_id 집합.

    개설 학기는 과목마다 다르다 (실측 2026-07-17: 1학기만 717 · 2학기만 709 ·
    둘 다 381) → 대상 학기에 안 여는 과목을 추천하면 안 된다.

    "살아있음" = 최근 두 학기에 개설. 이 조건이 없으면 폐강 과목이 섞인다
    (2026-07-12 확인: 2024-2에만 개설된 216과목이 2026-2 풀에 오염).
    반대로 "최신 연도의 해당 학기"로만 좁히면 격년 개설 과목이 빠진다
    (2026-07-17 확인: 화공유체역학 등 42종 — 2024-2 개설 + 2026-1 생존).
    """
    rows = con.execute(
        """
        WITH recent AS (
            SELECT DISTINCT year, semester FROM course_offerings
            ORDER BY year DESC, semester DESC LIMIT 2
        )
        SELECT DISTINCT o.course_id
        FROM course_offerings o
        WHERE o.semester = ?
          AND o.course_id IN (
              SELECT c.course_id FROM course_offerings c
              JOIN recent r ON c.year = r.year AND c.semester = r.semester
          )
        """,
        (semester,),
    ).fetchall()
    return {r["course_id"] for r in rows}


def syllabus_attrs(
    con: sqlite3.Connection, course_ids: Sequence[str]
) -> dict[str, sqlite3.Row]:
    """course_syllabi 속성 (강의계획서 병합분만 존재 — 부분 커버리지)."""
    if not course_ids:
        return {}
    marks = ", ".join("?" for _ in course_ids)
    rows = con.execute(
        f"SELECT * FROM course_syllabi WHERE course_id IN ({marks})", tuple(course_ids)
    ).fetchall()
    return {r["course_id"]: r for r in rows}


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


def category_credits(
    con: sqlite3.Connection, course_ids: Sequence[str]
) -> list[sqlite3.Row]:
    """이수과목의 (성격·학과) × 학점 — course_categories ⋈ courses(credit).

    한 과목이 (과목 × 전공) 다대다라 여러 행이 나올 수 있다. courses 에 없는
    폐강 코드는 학점을 못 구해 제외된다(집계 대상 아님).
    """
    if not course_ids:
        return []
    marks = ", ".join("?" for _ in course_ids)
    return con.execute(
        f"""SELECT cc.course_id, cc.major_canonical, cc.category, c.credit
            FROM course_categories cc
            JOIN courses c ON c.course_id = cc.course_id
            WHERE cc.course_id IN ({marks})""",
        tuple(course_ids),
    ).fetchall()
