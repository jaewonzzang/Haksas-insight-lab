"""개설교과목정보.xls (HTML) → schema.sql 의 courses 행 + warnings.

역할:
    - xls 로드 (pd.read_html)
    - 28개 원본 컬럼 → courses 컬럼 매핑
    - 'O' / '' → 1 / 0 (5개 플래그)
    - course_type 분류 (Q9): regular / special / dummy
    - is_general 분류 (department == '전인교육원')
    - 같은 course_id 의 여러 분반 통합 — 첫 분반 채택 (Q8)
    - 분반 간 컬럼 불일치 시 multi_section warning 생성

입력:
    xls_path (str), year (int), semester (int)

출력:
    (courses: list[dict], warnings: list[dict])
    - courses: schema.sql 의 courses 테이블 INSERT 형식. unique course_id 기준.
      description_raw / restrictions_raw / remarks_raw 원문 보존.
      linked_majors_parsed = None (remarks_parser 가 별도로 채움).
    - warnings: schema.sql 의 parse_warnings 테이블 INSERT 형식.

관련 schema 테이블: courses, parse_warnings.
관련 결정: Q2, Q3, Q4(원문 보존만), Q7, Q8, Q9, 추가 결정 1·5.
"""

from typing import Any, Dict, List, Optional, Tuple


def load_courses_from_xls(
    xls_path: str,
    year: int,
    semester: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """xls 파일을 읽어 정규화된 과목 dict 리스트 + warnings 반환.

    Args:
        xls_path: 개설교과목정보.xls 절대 경로.
        year: 적재 학년도 (예: 2026). courses.year 에 들어감.
        semester: 적재 학기 (1 또는 2). courses.semester 에 들어감.

    Returns:
        (courses, warnings):
          courses: schema.sql 의 courses 테이블에 INSERT 가능한
                   dict 리스트. 분반 통합 후 unique course_id 기준.
                   description_raw, restrictions_raw, remarks_raw
                   원문 보존. linked_majors_parsed 는 None
                   (remarks_parser 에서 채움).
          warnings: parse_warnings 에 INSERT 가능한 dict 리스트.

    Raises:
        FileNotFoundError: xls_path 가 존재하지 않을 때.
        ValueError: 컬럼 구조가 예상과 다를 때.
    """
    raise NotImplementedError("4b 단계에서 구현")


def _resolve_multi_sections(
    rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """같은 course_id 의 여러 분반을 첫 분반 채택으로 통합.

    분반 간 컬럼 값 불일치 시 warning 생성 (field='multi_section', severity='warning').

    Args:
        rows: 분반 중복 포함 raw 행 리스트 (1720행 수준).

    Returns:
        (unique_courses, warnings)
    """
    raise NotImplementedError("4b 단계에서 구현")


def _classify_course_type(
    course_id: str,
    credit: Optional[float],
) -> str:
    """course_type 분류 (Q9).

    Args:
        course_id: 과목 코드.
        credit: 학점 (None 가능).

    Returns:
        'dummy' if course_id starts with 'DUM',
        'special' if credit is None and not dummy (예: AII1001),
        'regular' otherwise.
    """
    raise NotImplementedError("4b 단계에서 구현")


def _classify_is_general(department: str) -> int:
    """교양 여부 분류.

    Args:
        department: courses.department 원문.

    Returns:
        1 if department == '전인교육원', 0 otherwise.
    """
    raise NotImplementedError("4b 단계에서 구현")


def _flag_to_int(value: Any) -> int:
    """xls 'O' / 빈값 / NaN 을 1 / 0 으로 변환.

    Args:
        value: xls 셀 값 (str / float NaN / None).

    Returns:
        1 if value strips to 'O', 0 otherwise.
    """
    raise NotImplementedError("4b 단계에서 구현")
