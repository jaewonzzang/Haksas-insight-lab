"""course_loader 단위 테스트."""

import pytest

from app.parsers import course_loader


def _row(course_id="CSE1010", credit="3", **over):
    row = {
        "course_id": course_id,
        "course_name": "자료구조",
        "department": "컴퓨터공학과",
        "credit": credit,
        "target_year_raw": "전학년",
        "recommended_year_raw": "2-3학년",
        "is_english": "O",
        "is_cu": "",
        "is_huss": "",
        "is_ci": "",
        "is_honors": "",
        "restrictions_raw": "",
        "description_raw": "",
        "remarks_raw": "",
    }
    row.update(over)
    return row


def test_classify_course_type_dummy():
    """course_id 가 'DUM' 으로 시작하면 'dummy'.

    입력: course_id='DUMEX01', credit=None
    기대: 'dummy'
    """
    assert course_loader._classify_course_type("DUMEX01", None) == "dummy"


def test_classify_course_type_special():
    """credit 이 None 이고 DUM 아닌 경우 'special'.

    입력: course_id='AII1001', credit=None
    기대: 'special'
    """
    assert course_loader._classify_course_type("AII1001", None) == "special"


def test_classify_course_type_regular_normal():
    """일반 과목 (DUM 아님, credit 존재) → 'regular'.

    입력: course_id='CSE1010', credit=3.0
    기대: 'regular'
    """
    assert course_loader._classify_course_type("CSE1010", 3.0) == "regular"


def test_classify_course_type_regular_credit_none_not_special():
    """credit 빈값 + non-DUM 은 'special' (Q9 결정).

    입력: course_id='ABC9999', credit=None
    기대: 'special'
    """
    assert course_loader._classify_course_type("ABC9999", None) == "special"


def test_classify_is_general_yes():
    """전인교육원 = 교양.

    입력: department='전인교육원'
    기대: 1
    """
    assert course_loader._classify_is_general("전인교육원") == 1


def test_classify_is_general_no():
    """일반 학과는 교양 아님.

    입력: department='컴퓨터공학과'
    기대: 0
    """
    assert course_loader._classify_is_general("컴퓨터공학과") == 0


def test_flag_to_int_o():
    """'O' → 1.

    입력: 'O'
    기대: 1
    """
    assert course_loader._flag_to_int("O") == 1


def test_flag_to_int_empty():
    """빈 문자열 → 0.

    입력: ''
    기대: 0
    """
    assert course_loader._flag_to_int("") == 0


def test_flag_to_int_nan():
    """NaN → 0 (pandas 결측치).

    입력: float('nan')
    기대: 0
    """
    assert course_loader._flag_to_int(float("nan")) == 0


def test_resolve_multi_sections_consistent():
    """같은 course_id 의 3분반, 컬럼 값 모두 동일.

    입력: 동일 course_id × 3, 동일 카탈로그 값
    기대: 통합 1행, warnings 없음
    """
    unique, warnings = course_loader._resolve_multi_sections([_row(), _row(), _row()])
    assert len(unique) == 1
    assert warnings == []


def test_resolve_multi_sections_inconsistent_credit():
    """같은 course_id 의 2분반, credit 만 다름.

    입력: 동일 course_id × 2, credit 만 상이
    기대: 첫 분반 채택, multi_section warning 1건 severity='warning'
    """
    unique, warnings = course_loader._resolve_multi_sections(
        [_row(credit="3"), _row(credit="2")]
    )
    assert len(unique) == 1
    assert unique[0]["credit"] == "3"
    assert len(warnings) == 1
    assert warnings[0].field == "multi_section"
    assert warnings[0].severity == "warning"


def test_load_courses_from_csv_smoke():
    """실제 csv 로드 통합 테스트.

    skip 사유: integration 영역. unit 에서는 검증 안 함.
    integration 테스트(`tests/integration/`)에서 별도 다룸.
    """
    pytest.skip("integration 영역 (tests/integration/ 에서 다룸)")
