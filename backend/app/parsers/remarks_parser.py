"""'비고' 원문 → 연계전공 키워드 JSON 배열.

역할:
    - "스타트업연계전공 가능" / "가상융합연계전공 가능" 등 키워드 추출
    - linked_majors_parsed 컬럼에 들어갈 JSON 배열 문자열 생성
        예: '["스타트업연계전공","가상융합연계전공"]'

입력:
    course_id (str), remarks_raw (Optional[str])

출력:
    (linked_majors_json: Optional[str], warnings: list[dict])

관련 schema 테이블: courses.linked_majors_parsed, parse_warnings.
관련 결정: Q4 (비고 → linked_majors_parsed JSON 배열).
"""

import json
import re
from typing import List, Optional, Tuple

from app.schemas import WarningRow

_PATTERN = re.compile(r'([\w가-힣]+연계전공)\s*가능')


def parse_linked_majors(
    course_id: str,
    remarks_raw: Optional[str],
) -> Tuple[Optional[str], List[WarningRow]]:
    """비고 원문에서 연계전공 키워드를 추출하여 JSON 배열로 반환.

    Args:
        course_id: 대상 과목 코드.
        remarks_raw: '비고' 원문. None 가능.

    Returns:
        (linked_majors_json, warnings):
          linked_majors_json:
            JSON 문자열 (예: '["스타트업연계전공","가상융합연계전공"]'),
            또는 None (연계전공 키워드 없음).
          warnings: parse_warnings 행 리스트.
    """
    if not remarks_raw:
        return None, []

    matches = _PATTERN.findall(remarks_raw)
    if not matches:
        return None, []

    unique_ordered = list(dict.fromkeys(matches))
    return json.dumps(unique_ordered, ensure_ascii=False, separators=(',', ':')), []
