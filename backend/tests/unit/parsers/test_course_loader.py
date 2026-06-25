"""course_loader 단위 테스트 골격.

4a 단계에서는 케이스 정의와 skip 만. 본문 구현은 4b 단계.
"""

import pytest

from app.parsers import course_loader


def test_classify_course_type_dummy():
    """course_id 가 'DUM' 으로 시작하면 'dummy'.

    입력: course_id='DUMEX01', credit=None
    기대: 'dummy'
    """
    pytest.skip("4b 단계에서 구현")


def test_classify_course_type_special():
    """credit 이 None 이고 DUM 아닌 경우 'special'.

    입력: course_id='AII1001', credit=None
    기대: 'special'
    """
    pytest.skip("4b 단계에서 구현")


def test_classify_course_type_regular_normal():
    """일반 과목 (DUM 아님, credit 존재) → 'regular'.

    입력: course_id='CSE1010', credit=3.0
    기대: 'regular'
    """
    pytest.skip("4b 단계에서 구현")


def test_classify_course_type_regular_credit_none_not_special():
    """credit 빈값 + non-DUM 은 'special' (Q9 결정).

    입력: course_id='ABC9999', credit=None
    기대: 'special'
    """
    pytest.skip("4b 단계에서 구현")


def test_classify_is_general_yes():
    """전인교육원 = 교양.

    입력: department='전인교육원'
    기대: 1
    """
    pytest.skip("4b 단계에서 구현")


def test_classify_is_general_no():
    """일반 학과는 교양 아님.

    입력: department='컴퓨터공학과'
    기대: 0
    """
    pytest.skip("4b 단계에서 구현")


def test_flag_to_int_o():
    """'O' → 1.

    입력: 'O'
    기대: 1
    """
    pytest.skip("4b 단계에서 구현")


def test_flag_to_int_empty():
    """빈 문자열 → 0.

    입력: ''
    기대: 0
    """
    pytest.skip("4b 단계에서 구현")


def test_flag_to_int_nan():
    """NaN → 0 (pandas 결측치).

    입력: float('nan')
    기대: 0
    """
    pytest.skip("4b 단계에서 구현")


def test_resolve_multi_sections_consistent():
    """같은 course_id 의 3분반, 컬럼 값 모두 동일.

    입력: 동일 course_id × 3, 동일 카탈로그 값
    기대: 통합 1행, warnings 없음
    """
    pytest.skip("4b 단계에서 구현")


def test_resolve_multi_sections_inconsistent_credit():
    """같은 course_id 의 2분반, credit 만 다름.

    입력: 동일 course_id × 2, credit 만 상이
    기대: 첫 분반 채택, multi_section warning 1건 severity='warning'
    """
    pytest.skip("4b 단계에서 구현")


def test_load_courses_from_xls_smoke():
    """실제 xls 로드 통합 테스트.

    skip 사유: integration 영역. unit 에서는 검증 안 함.
    integration 테스트(`tests/integration/`)에서 별도 다룸.
    """
    pytest.skip("integration 영역 (tests/integration/ 에서 다룸)")
