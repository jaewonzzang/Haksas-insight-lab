"""build_syllabus_prereqs — 강의계획서 선수과목 병합 정책 (기존 보존·없는 것만 추가)."""

import sqlite3

from scripts.build_syllabus_prereqs import merge_syllabus_attrs, merge_syllabus_prereqs


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE courses (course_id TEXT PRIMARY KEY, course_name TEXT)")
    con.execute(
        "CREATE TABLE course_prerequisites "
        "(course_id TEXT, prereq_raw TEXT, prereq_tree_json TEXT)"
    )
    con.executemany(
        "INSERT INTO courses VALUES (?, ?)",
        [("CSE3080", "자료구조"), ("CSE4070", "운영체제"), ("CSE4175", "분산시스템")],
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


def test_attrs_upsert_and_replace():
    con = _db()
    recs = [{
        "course_id": "CSE4070", "overview_text": "운영체제의 구조와 원리",
        "team_project": "none", "attendance_ratio": 0.1, "file": "a.pdf",
    }]
    stats = merge_syllabus_attrs(con, recs)
    assert stats["upserted"] == 1
    # 같은 과목 재병합(최신 계획서) → 교체
    recs[0]["overview_text"] = "개정판 개요"
    merge_syllabus_attrs(con, recs)
    row = con.execute(
        "SELECT overview_text, team_project FROM course_syllabi WHERE course_id='CSE4070'"
    ).fetchone()
    assert row == ("개정판 개요", "none")


def test_attrs_unknown_course_skipped():
    con = _db()
    stats = merge_syllabus_attrs(con, [{"course_id": "NOPE999", "overview_text": "x"}])
    assert stats["upserted"] == 0 and stats["no_course"] == 1


def test_no_prereq_phrases_detected():
    # 실PDF 실측 표현 (2026-07-13): "없음.", "...so no\nprerequisites needed."
    # + 2026-07-23 unparsed 809건 실측 확장: "None", "n/a", "필요로 하지 않는다"
    con = _db()
    con.execute("INSERT INTO courses VALUES ('CHI2004', '중국문화입문')")
    con.execute("INSERT INTO courses VALUES ('ENG3227', '영어학연습')")
    stats = merge_syllabus_prereqs(
        con,
        [
            {"course_id": "CSE4070", "prerequisites_raw": "없음."},
            {"course_id": "CSE4175", "prerequisites_raw": "so no\nprerequisites needed."},
            {"course_id": "CHI2004", "prerequisites_raw": "별도의 선수 과목을 필요로 하지 않는다."},
            {"course_id": "ENG3227", "prerequisites_raw": "None"},
        ],
    )
    assert stats["no_prereq"] == 4 and stats["unparsed"] == 0


def test_prose_course_name_fallback():
    """코드 없는 산문에서 DB 과목명 실명 매칭 → 트리 (2026-07-23 파서 보강)."""
    con = _db()
    con.execute("INSERT INTO courses VALUES ('AIE3050', '자료구조')")  # 동명이코드
    stats = merge_syllabus_prereqs(
        con,
        [{
            "course_id": "CSE4070",
            "prerequisites_raw": "자료 구조 과목 이수를 권장하며, 프로그래밍에 익숙해야 한다.",
        }],
    )
    assert stats["inserted"] == 1 and stats["inserted_prose"] == 1
    tree = con.execute(
        "SELECT prereq_tree_json FROM course_prerequisites WHERE course_id='CSE4070'"
    ).fetchone()[0]
    # 동명이코드(자료구조 = CSE3080·AIE3050)는 OR 노드
    assert '"or"' in tree and "CSE3080" in tree and "AIE3050" in tree


def test_prose_positional_longest_match_keeps_both_variants():
    """"일반화학 I, 일반화학 II" — II가 있어도 I의 독립 등장은 남아야 한다."""
    con = _db()
    con.executemany(
        "INSERT INTO courses VALUES (?, ?)",
        [("CHM1001", "일반화학I"), ("CHM1002", "일반화학II"), ("CHM2351", "분석화학")],
    )
    stats = merge_syllabus_prereqs(
        con,
        [{"course_id": "CHM2351", "prerequisites_raw": "일반화학 I, 일반화학 II 내용을 알면 도움이 됨"}],
    )
    assert stats["inserted_prose"] == 1
    tree = con.execute(
        "SELECT prereq_tree_json FROM course_prerequisites WHERE course_id='CHM2351'"
    ).fetchone()[0]
    assert "CHM1001" in tree and "CHM1002" in tree


def test_prose_guards_noise_and_generic_and_self():
    """양식 누수('수업방법' 이후) 미매칭 · 일반명사형('교육과정') 차단 · 자기 자신 제외."""
    con = _db()
    con.executemany(
        "INSERT INTO courses VALUES (?, ?)",
        [("EDU3001", "교육과정"), ("MAT2210", "고등미적분학I"), ("STS2005", "미적분학I")],
    )
    stats = merge_syllabus_prereqs(
        con,
        [
            # 고교 교육과정 언급 — 과목 EDU3001 로 오추출하면 안 됨
            {"course_id": "CSE4070", "prerequisites_raw": "고등학교 수학과 교육과정 중 미적분 이해"},
            # 양식 누수: '수업방법' 표 이후에만 과목명 등장 — 미매칭
            {"course_id": "CSE4175", "prerequisites_raw": "성실한 태도. 수업방법 강의 토의 미적분학I 발표"},
            # 자기 자신 이름 언급 — 제외 (다른 매칭 없으면 unparsed)
            {"course_id": "MAT2210", "prerequisites_raw": "고등미적분학I 은 심화 과목이다"},
        ],
    )
    assert stats["inserted"] == 0 and stats["unparsed"] == 3


def test_course_id_fallbacks_for_english_forms():
    con = _db()
    con.execute("INSERT INTO courses VALUES ('AAT3019', 'Data Visualization')")
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
