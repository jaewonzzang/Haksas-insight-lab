"""'과목 설명' / '비고' → 별칭(옛 코드, 대체과목) 추출.

역할:
    - (구) 옛코드 패턴 → source_type = 'old_code'
        형태: '(구) ABC1234' / '(구)ABC1234' / '구) ABC1234'
    - 대체과목 패턴 → source_type = 'replacement'
        형태: '대체과목: XYZ5678' / '대체과목 XYZ5678(YYY)' 등
    - 학번/조건 정보가 있으면 condition_raw 에 보존
        예: '2015-2018학번'

입력:
    new_course_id (str), source_text (Optional[str])

출력:
    (aliases: list[AliasRow], warnings: list[WarningRow])

의미:
    old_* 이수 → new_course_id 이수로 간주 (단방향 매핑).

관련 schema 테이블: course_aliases, parse_warnings.
관련 결정: 추가 결정 2·3 (영어 enum, condition_raw 보존).
"""

import re
from typing import List, Optional, Tuple

from app.schemas import AliasRow, WarningRow

_OLD_CODE_PATTERN = re.compile(
    r'(?:\()?구\)\s*([A-Z]{2,5}\d{3,4}[A-Z]?)(?:\s*\(([^)]+)\))?'
)

_REPLACEMENT_PATTERN = re.compile(
    r'대체과목\s*[:：]\s*([A-Z]{2,5}\d{3,4}[A-Z]?)(?:\s*\(([^)]+)\))?'
)


def parse_aliases(
    new_course_id: str,
    source_text: Optional[str],
) -> Tuple[List[AliasRow], List[WarningRow]]:
    """별칭 텍스트에서 옛 코드 / 대체과목 패턴을 추출.

    Args:
        new_course_id: 현재 과목 코드 (별칭의 '신' 측).
        source_text: 별칭이 포함될 가능성 있는 원문
                     (description_raw 또는 remarks_raw).

    Returns:
        (aliases, warnings):
          aliases: AliasRow 리스트 (course_aliases 행).
          warnings: WarningRow 리스트.
    """
    if not source_text:
        return [], []

    aliases: List[AliasRow] = []
    aliases.extend(_extract_old_code_pattern(new_course_id, source_text))
    aliases.extend(_extract_replacement_pattern(new_course_id, source_text))
    return aliases, []


def _extract_old_code_pattern(
    new_course_id: str, text: str
) -> List[AliasRow]:
    """'(구) ABC1234' 또는 '구) ABC1234' 형태 매칭.

    Args:
        new_course_id: 현재 과목 코드.
        text: 검사할 원문.

    Returns:
        AliasRow 리스트.
    """
    return [
        AliasRow(
            new_course_id=new_course_id,
            old_course_id=m.group(1),
            old_course_name=None,
            source_type='old_code',
            condition_raw=m.group(2),
            raw_text=m.group(0).strip(),
        )
        for m in _OLD_CODE_PATTERN.finditer(text)
    ]


def _extract_replacement_pattern(
    new_course_id: str, text: str
) -> List[AliasRow]:
    """'대체과목: XYZ5678' 형태 매칭.

    Args:
        new_course_id: 현재 과목 코드.
        text: 검사할 원문.

    Returns:
        AliasRow 리스트.
    """
    return [
        AliasRow(
            new_course_id=new_course_id,
            old_course_id=m.group(1),
            old_course_name=None,
            source_type='replacement',
            condition_raw=m.group(2),
            raw_text=m.group(0).strip(),
        )
        for m in _REPLACEMENT_PATTERN.finditer(text)
    ]
