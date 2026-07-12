"""build_syllabus_prereqs — 강의계획서 선수과목 병합 정책 (기존 보존·없는 것만 추가)."""

import sqlite3

from scripts.build_syllabus_prereqs import merge_syllabus_prereqs


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE courses (course_id TEXT PRIMARY KEY)")
    con.execute(
        "CREATE TABLE course_prerequisites "
        "(course_id TEXT, prereq_raw TEXT, prereq_tree_json TEXT)"
    )
    con.executemany(
        "INSERT INTO courses VALUES (?)", [("CSE3080",), ("CSE4070",), ("CSE4175",)]
    )
    con.execute(
        "INSERT INTO course_prerequisites VALUES ('CSE3080', '선수과목 : CSE2003', '{}')"
    )
    return con


def test_merge_inserts_only_missing_courses():
    con = _db()
    records = [
        {"course_id": "CSE4070", "prerequisites_raw": "선수과목 : CSE3080"},  # 신규 → 추가
        {"course_id": "CSE3080", "prerequisites_raw": "선수과목 : CSE2003"},  # 기존 → 보존
        {"course_id": "NOPE999", "prerequisites_raw": "선수과목 : CSE3080"},  # 미존재 과목
        {"course_id": "CSE4175", "prerequisites_raw": ""},                    # 선수 없음
    ]
    stats = merge_syllabus_prereqs(con, records)
    assert stats["inserted"] == 1
    assert stats["skipped_existing"] == 1
    assert stats["no_course"] == 1
    assert stats["no_prereq"] == 1

    rows = con.execute(
        "SELECT course_id, prereq_tree_json FROM course_prerequisites ORDER BY course_id"
    ).fetchall()
    assert [r[0] for r in rows] == ["CSE3080", "CSE4070"]
    assert rows[0][1] == "{}"  # 기존 트리 미변경
    assert "CSE3080" in rows[1][1]  # 신규 트리에 선수과목 코드 포함


def test_merge_counts_unparsed_free_text():
    con = _db()
    stats = merge_syllabus_prereqs(
        con, [{"course_id": "CSE4070", "prerequisites_raw": "열심히 하려는 마음가짐"}]
    )
    assert stats["inserted"] == 0
    assert stats["unparsed"] + stats["no_prereq"] >= 1  # 파서가 트리를 못 만들면 삽입하지 않는다


def test_no_prereq_phrases_detected():
    # 실PDF 실측 표현 (2026-07-13): "없음.", "...so no\nprerequisites needed."
    con = _db()
    stats = merge_syllabus_prereqs(
        con,
        [
            {"course_id": "CSE4070", "prerequisites_raw": "없음."},
            {"course_id": "CSE4175", "prerequisites_raw": "so no\nprerequisites needed."},
        ],
    )
    assert stats["no_prereq"] == 2 and stats["unparsed"] == 0


def test_course_id_fallbacks_for_english_forms():
    con = _db()
    con.executemany("INSERT INTO courses VALUES (?)", [("AAT3019",)])
    # courses에 과목명 조회용 컬럼이 필요 — 테스트 스키마 확장
    con.execute("ALTER TABLE courses ADD COLUMN course_name TEXT")
    con.execute("UPDATE courses SET course_name = 'Data Visualization' WHERE course_id='AAT3019'")
    records = [
        # 폴백 ①: 과목명 칸에 코드("CSE3030-01" 형태 — 여기선 CSE4070-01)
        {"course_id": None, "course_name": "CSE4070-01", "prerequisites_raw": "선수과목 : CSE3080"},
        # 폴백 ②: 파일명 과목명 유일 일치
        {
            "course_id": None,
            "course_name": None,
            "file": "2026년도_1학기_Data Visualization_강의계획서.pdf",
            "prerequisites_raw": "없음",
        },
    ]
    stats = merge_syllabus_prereqs(con, records)
    assert stats["inserted"] == 1  # CSE4070 트리 삽입
    assert stats["no_prereq"] == 1  # AAT3019 — 파일명으로 식별 후 '없음' 분류
    assert stats["no_course"] == 0
