"""개설교과목정보 CSV → schema.sql 의 courses 행 + warnings.

역할:
    - CSV 로드 (pd.read_csv, utf-8-sig, 헤더 1행)
    - 28개 원본 컬럼 → courses 컬럼 매핑 (미사용 컬럼은 버림)
    - 'O' / '' → 1 / 0 (5개 플래그)
    - course_type 분류 (Q9): regular / special / dummy
    - is_general 분류 (department == '전인교육원')
    - 같은 course_id 의 여러 분반 통합 — 첫 분반 채택 (Q8)
    - 분반 간 컬럼 불일치 시 multi_section warning 생성

입력:
    csv_path (str), year (int), semester (int)

출력:
    (courses: list[CourseRow], warnings: list[WarningRow])
    - courses: schema.sql 의 courses 테이블 INSERT 형식. unique course_id 기준.
      description_raw / restrictions_raw / remarks_raw 원문 보존.
      linked_majors_parsed = None (remarks_parser 가 별도로 채움).
    - warnings: schema.sql 의 parse_warnings 테이블 INSERT 형식.

관련 schema 테이블: courses, parse_warnings.
관련 결정: Q2, Q3, Q4(원문 보존만), Q7, Q8, Q9, 추가 결정 1·5.
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.schemas import CourseRow, WarningRow

# CSV 헤더(4개 파일 동일 확인) → CourseRow 필드 매핑. 미사용 컬럼은 버린다.
_FIELD_BY_COL: Dict[str, str] = {
    "학과": "department",
    "과목번호": "course_id",
    "과목명": "course_name",
    "학점": "credit",
    "수강대상": "target_year_raw",
    "권장학년": "recommended_year_raw",
    "영어강의": "is_english",
    "CU과목": "is_cu",
    "HUSS과목": "is_huss",
    "탐구공동체(CI)과목": "is_ci",
    "Honors과목": "is_honors",
    "수강신청 참조사항": "restrictions_raw",
    "과목 설명": "description_raw",
    "비고": "remarks_raw",
}


def load_courses_from_csv(
    csv_path: str,
    year: int,
    semester: int,
) -> Tuple[List[CourseRow], List[WarningRow]]:
    """CSV 파일을 읽어 정규화된 CourseRow 리스트 + warnings 반환.

    Args:
        csv_path: 개설교과목정보 CSV 절대 경로.
        year: 적재 학년도 (예: 2026). courses.year 에 들어감.
        semester: 적재 학기 (1 또는 2). courses.semester 에 들어감.

    Returns:
        (courses, warnings):
          courses: CourseRow 리스트. 분반 통합 후 unique course_id 기준.
                   description_raw, restrictions_raw, remarks_raw
                   원문 보존. linked_majors_parsed 는 None
                   (remarks_parser 에서 채움).
          warnings: WarningRow 리스트 (parse_warnings 행).

    Raises:
        FileNotFoundError: csv_path 가 존재하지 않을 때.
        ValueError: 컬럼 구조가 예상과 다를 때.
    """
    df = pd.read_csv(
        csv_path, encoding="utf-8-sig", header=0, dtype=str, keep_default_na=False
    )
    missing = set(_FIELD_BY_COL) - set(df.columns)
    if missing:
        raise ValueError(f"컬럼 구조가 예상과 다름 — 누락: {sorted(missing)}")

    mapped = [
        {field: str(rec[col]).strip() for col, field in _FIELD_BY_COL.items()}
        for rec in df.to_dict(orient="records")
    ]
    unique_rows, warnings = _resolve_multi_sections(mapped)

    courses: List[CourseRow] = []
    for row in unique_rows:
        credit = float(row["credit"]) if row["credit"] else None
        courses.append(
            CourseRow(
                course_id=row["course_id"],
                course_name=row["course_name"],
                department=row["department"],
                credit=credit,
                year=year,
                semester=semester,
                target_year_raw=row["target_year_raw"] or None,
                recommended_year_raw=row["recommended_year_raw"] or None,
                is_english=_flag_to_int(row["is_english"]),
                is_cu=_flag_to_int(row["is_cu"]),
                is_huss=_flag_to_int(row["is_huss"]),
                is_ci=_flag_to_int(row["is_ci"]),
                is_honors=_flag_to_int(row["is_honors"]),
                course_type=_classify_course_type(row["course_id"], credit),
                is_general=_classify_is_general(row["department"]),
                description_raw=row["description_raw"] or None,
                restrictions_raw=row["restrictions_raw"] or None,
                remarks_raw=row["remarks_raw"] or None,
                linked_majors_parsed=None,
            )
        )
    return courses, warnings


def _resolve_multi_sections(
    rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[WarningRow]]:
    """같은 course_id 의 여러 분반을 첫 분반 채택으로 통합.

    분반 간 컬럼 값 불일치 시 warning 생성 (field='multi_section', severity='warning').

    Args:
        rows: 분반 중복 포함, 컬럼 매핑 후 필드 dict 리스트 (값은 str).

    Returns:
        (unique_rows, warnings)
    """
    by_id: Dict[str, Dict[str, Any]] = {}
    warnings: List[WarningRow] = []
    for row in rows:
        first = by_id.get(row["course_id"])
        if first is None:
            by_id[row["course_id"]] = row
            continue
        diff = [k for k in first if k != "course_id" and first[k] != row[k]]
        if diff:
            warnings.append(
                WarningRow(
                    course_id=row["course_id"],
                    field="multi_section",
                    severity="warning",
                    issue=f"분반 간 값 불일치: {', '.join(sorted(diff))}",
                    raw_text=None,
                )
            )
    return list(by_id.values()), warnings


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
    if course_id.startswith("DUM"):
        return "dummy"
    if credit is None:
        return "special"
    return "regular"


def _classify_is_general(department: str) -> int:
    """교양 여부 분류.

    Args:
        department: courses.department 원문.

    Returns:
        1 if department == '전인교육원', 0 otherwise.
    """
    return 1 if department == "전인교육원" else 0


def _flag_to_int(value: Any) -> int:
    """CSV 'O' / 빈값 / NaN 을 1 / 0 으로 변환.

    Args:
        value: CSV 셀 값 (str / float NaN / None).

    Returns:
        1 if value strips to 'O', 0 otherwise.
    """
    if isinstance(value, str):
        return 1 if value.strip() == "O" else 0
    return 0
