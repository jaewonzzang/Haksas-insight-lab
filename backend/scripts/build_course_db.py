"""1단계 산출물 빌드: 4학기 개설교과목정보 CSV → s_compass_courses.db.

오프라인 1회성 스크립트. API 서버 코드 경로에서 호출 금지.
parsers/* 를 조합해 6테이블 (courses, course_offerings, course_prerequisites,
course_aliases, course_restrictions, parse_warnings)을 채운다.

Phase 1: 학기별 CSV 적재 (연도-학기 오름차순, courses 는 latest-wins)
         + course_offerings 에 개설 이력 기록.
Phase 2: 확정된 courses 1회 순회 — remarks/prereq/alias/restriction 파싱.

usage: python scripts/build_course_db.py [--raw-dir DIR] [--db PATH]
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

# 프로젝트 미설치 venv 에서 scripts/ 직접 실행을 위한 경로 부트스트랩.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.parsers.alias_parser import parse_aliases
from app.parsers.course_loader import load_courses_from_csv
from app.parsers.prereq_parser import parse_prerequisites
from app.parsers.remarks_parser import parse_linked_majors
from app.parsers.restriction_parser import parse_restrictions
from app.schemas import CourseRow, OfferingRow, WarningRow

SCHEMA_PATH = config.BASE_DIR / "app" / "db" / "schema.sql"
TABLES = (
    "courses", "course_offerings", "course_prerequisites",
    "course_aliases", "course_restrictions", "parse_warnings",
)
_CSV_NAME_RE = re.compile(r"개설교과목정보_(\d{4})-([12])\.csv$")

_COURSE_FIELDS = list(CourseRow.model_fields)
_INSERT_COURSE = (
    f"INSERT OR REPLACE INTO courses ({', '.join(_COURSE_FIELDS)}) "
    f"VALUES ({', '.join(':' + f for f in _COURSE_FIELDS)})"
)


def _find_csvs(raw_dir: Path) -> list[tuple[int, int, Path]]:
    """파일명에서 (year, semester) 파싱 후 연도-학기 오름차순 정렬."""
    found = []
    for path in raw_dir.glob("개설교과목정보_*.csv"):
        m = _CSV_NAME_RE.search(path.name)
        if m:
            found.append((int(m.group(1)), int(m.group(2)), path))
    return sorted(found)


def main() -> None:
    parser = argparse.ArgumentParser(description="4학기 CSV → s_compass_courses.db")
    parser.add_argument("--raw-dir", type=Path, default=config.RAW_DIR)
    parser.add_argument("--db", type=Path, default=config.DB_PATH)
    args = parser.parse_args()

    csvs = _find_csvs(args.raw_dir)
    if not csvs:
        raise SystemExit(f"개설교과목정보_*.csv 없음: {args.raw_dir}")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(args.db)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    warnings: list[WarningRow] = []

    # Phase 1 — 학기별 적재. 오름차순이라 최신 학기가 덮어씀 = latest-wins.
    for year, semester, path in csvs:
        courses, load_warnings = load_courses_from_csv(str(path), year, semester)
        warnings.extend(load_warnings)
        for course in courses:
            con.execute(_INSERT_COURSE, course.model_dump())
            offering = OfferingRow(course_id=course.course_id, year=year, semester=semester)
            con.execute(
                "INSERT INTO course_offerings (course_id, year, semester) "
                "VALUES (:course_id, :year, :semester)",
                offering.model_dump(),
            )
        print(f"{path.name}: courses {len(courses)}건 적재")

    # Phase 2 — 확정된 courses 1회 순회 (학기 반복 시 중복 INSERT 되므로 금지).
    final_rows = con.execute(
        "SELECT course_id, description_raw, restrictions_raw, remarks_raw FROM courses"
    ).fetchall()
    for course_id, description_raw, restrictions_raw, remarks_raw in final_rows:
        linked_json, w = parse_linked_majors(course_id, remarks_raw)
        warnings.extend(w)
        if linked_json is not None:
            con.execute(
                "UPDATE courses SET linked_majors_parsed = ? WHERE course_id = ?",
                (linked_json, course_id),
            )

        prereq_record, w = parse_prerequisites(course_id, description_raw)
        warnings.extend(w)
        if prereq_record is not None:
            con.execute(
                "INSERT INTO course_prerequisites "
                "(course_id, prereq_raw, prereq_tree_json) "
                "VALUES (:course_id, :prereq_raw, :prereq_tree_json)",
                prereq_record,
            )

        for source_text in (description_raw, remarks_raw):
            aliases, w = parse_aliases(course_id, source_text)
            warnings.extend(w)
            for alias in aliases:
                con.execute(
                    "INSERT INTO course_aliases "
                    "(new_course_id, old_course_id, old_course_name, "
                    "source_type, condition_raw, raw_text) "
                    "VALUES (:new_course_id, :old_course_id, :old_course_name, "
                    ":source_type, :condition_raw, :raw_text)",
                    alias.model_dump(),
                )

        restrictions, w = parse_restrictions(course_id, restrictions_raw)
        warnings.extend(w)
        for restriction in restrictions:
            con.execute(
                "INSERT INTO course_restrictions "
                "(course_id, target_dept, status, raw_text) "
                "VALUES (:course_id, :target_dept, :status, :raw_text)",
                restriction.model_dump(),
            )

    for warning in warnings:
        con.execute(
            "INSERT INTO parse_warnings (course_id, field, severity, issue, raw_text) "
            "VALUES (:course_id, :field, :severity, :issue, :raw_text)",
            warning.model_dump(),
        )

    con.commit()

    print(f"\n빌드 완료: {args.db}")
    for table in TABLES:
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n}행")
    con.close()


if __name__ == "__main__":
    main()
