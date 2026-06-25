"""'수강신청 참조사항' 원문 → 학과별 수강 제한 4패턴 추출.

역할:
    - 토큰 분리 (콤마 기준, 괄호 안 콤마는 분할 안 함)
    - 4패턴 매핑:
        '학과명(가능)'        → allowed
        '학과명(불가능)'      → forbidden
        '학과명(1전공 가능)'  → major_only_allowed
        '학과명(1전공 불가능)' → major_only_forbidden
    - 중복 토큰 dedupe (Q10) — 중복 발견 시 severity='info' warning

입력:
    course_id (str), restrictions_raw (Optional[str])

출력:
    (restrictions: list[RestrictionRow], warnings: list[WarningRow])

관련 schema 테이블: course_restrictions, parse_warnings.
관련 결정: Q10, 추가 결정 4 (target_dept 컬럼명 유지).
"""

import re
from typing import List, Optional, Tuple

from app.schemas import RestrictionRow, WarningRow

_TOKEN_PATTERN = re.compile(r'^\s*(.+?)\s*\(\s*(.+?)\s*\)\s*$')

_STATUS_MAP = {
    '가능': 'allowed',
    '불가능': 'forbidden',
    '1전공 가능': 'major_only_allowed',
    '1전공 불가능': 'major_only_forbidden',
}


def parse_restrictions(
    course_id: str,
    restrictions_raw: Optional[str],
) -> Tuple[List[RestrictionRow], List[WarningRow]]:
    """수강신청 참조사항 원문에서 4패턴 토큰을 추출.

    Args:
        course_id: 대상 과목 코드.
        restrictions_raw: '수강신청 참조사항' 원문. None 가능.

    Returns:
        (restrictions, warnings):
          restrictions: RestrictionRow 리스트 (course_restrictions 행).
          warnings: WarningRow 리스트 (parse_warnings 행).
          중복 토큰은 제거. 중복 발견 시 warning (severity 'info').
    """
    if not restrictions_raw:
        return [], []

    restrictions: List[RestrictionRow] = []
    warnings: List[WarningRow] = []
    seen: set = set()

    for raw_token in _split_tokens(restrictions_raw):
        token = raw_token.strip()
        if not token:
            continue

        m = _TOKEN_PATTERN.match(token)
        if not m:
            warnings.append(WarningRow(
                course_id=course_id,
                field='restrictions',
                severity='warning',
                issue=f'Unrecognized token format: {token!r}',
                raw_text=token,
            ))
            continue

        target_dept = m.group(1).strip()
        suffix = m.group(2).strip()
        status = _classify_status(suffix)
        if status is None:
            warnings.append(WarningRow(
                course_id=course_id,
                field='restrictions',
                severity='warning',
                issue=f'Unknown suffix: {suffix!r}',
                raw_text=token,
            ))
            continue

        key = (target_dept, status)
        if key in seen:
            warnings.append(WarningRow(
                course_id=course_id,
                field='restrictions',
                severity='info',
                issue=f'Duplicate token dropped: {token!r}',
                raw_text=token,
            ))
            continue

        seen.add(key)
        restrictions.append(RestrictionRow(
            course_id=course_id,
            target_dept=target_dept,
            status=status,
            raw_text=token,
        ))

    return restrictions, warnings


def _split_tokens(text: str) -> List[str]:
    """원문을 콤마 기준 토큰으로 분할. 괄호 안 콤마는 분할하지 않음.

    Args:
        text: 수강신청 참조사항 원문.

    Returns:
        토큰 문자열 리스트.
    """
    tokens: List[str] = []
    depth = 0
    buf: List[str] = []
    for ch in text:
        if ch == '(':
            depth += 1
            buf.append(ch)
        elif ch == ')':
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == ',' and depth == 0:
            tokens.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append(''.join(buf))
    return tokens


def _classify_status(suffix: str) -> Optional[str]:
    """괄호 안 문자열에서 4 상태 분류.

    Args:
        suffix: 예 '가능', '1전공 불가능'.

    Returns:
        4 상태 중 하나, 또는 매칭 안 되면 None.
    """
    return _STATUS_MAP.get(suffix)
