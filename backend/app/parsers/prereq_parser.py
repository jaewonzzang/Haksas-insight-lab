"""'과목 설명' 원문 → 선수과목 AND/OR 트리 JSON.

역할:
    - '선수과목' 키워드 이후 섹션 추출
    - 정규식 [A-Z]{2,5}\\d{3,4}[A-Z]? 로 과목 코드 매칭
    - 콤마 = AND, '또는'/'or' = OR, 괄호 = OR 그룹 경계
    - 트리 JSON 직렬화

입력:
    course_id (str), description_raw (Optional[str])

출력:
    (prereq_record: Optional[dict], warnings: list[WarningRow])
    - prereq_record: schema.sql 의 course_prerequisites 행
                     ({course_id, prereq_raw, prereq_tree_json})
                     또는 None (선수과목 없음 / 파싱 실패).
    - warnings: parse_warnings 행 리스트.

트리 JSON 스키마:
    leaf: {"type": "course", "code": "CSE1010"}
    AND : {"type": "and",    "children": [...]}
    OR  : {"type": "or",     "children": [...]}

관련 schema 테이블: course_prerequisites, parse_warnings.
관련 결정: Q-새2 (정규식 trailing [A-Z]? 포함).
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas import WarningRow

_KEYWORD = "선수과목"
_CODE_RE = re.compile(r"[A-Z]{2,5}\d{3,4}[A-Z]?")
_TOKEN_RE = re.compile(r"[A-Z]{2,5}\d{3,4}[A-Z]?|또는|\bor\b|,|\(|\)")
_OR_WORDS = {"또는", "or"}


def parse_prerequisites(
    course_id: str,
    description_raw: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], List[WarningRow]]:
    """선수과목 텍스트를 AND/OR 트리로 파싱.

    Args:
        course_id: 대상 과목 코드.
        description_raw: '과목 설명' 원문. None 가능.

    Returns:
        (prereq_record, warnings):
          prereq_record:
            None (선수과목 없음 또는 파싱 실패) 또는
            {
              "course_id": str,
              "prereq_raw": str,           # 선수과목 섹션 원문
              "prereq_tree_json": str,     # 트리의 JSON 직렬화
            }
          warnings: 정규식 매칭 실패, 괄호 비대칭 등 (WarningRow 리스트).
    """
    if not description_raw:
        return None, []
    section = _extract_prereq_section(description_raw)
    if section is None:
        return None, []
    tokens = _tokenize(section)
    if not any(_CODE_RE.fullmatch(t) for t in tokens):
        return None, [
            WarningRow(
                course_id=course_id,
                field="prerequisites",
                severity="warning",
                issue="선수과목 키워드 존재하나 과목 코드 매칭 0건",
                raw_text=section,
            )
        ]
    try:
        tree = _build_tree(tokens)
    except ValueError as exc:
        return None, [
            WarningRow(
                course_id=course_id,
                field="prerequisites",
                severity="error",
                issue=str(exc),
                raw_text=section,
            )
        ]
    record = {
        "course_id": course_id,
        "prereq_raw": section,
        "prereq_tree_json": json.dumps(tree, ensure_ascii=False),
    }
    return record, []


def _extract_prereq_section(text: str) -> Optional[str]:
    """text 에서 '선수과목' 키워드 이후 섹션만 잘라 반환.

    Args:
        text: 과목 설명 원문.

    Returns:
        선수과목 섹션 문자열, 또는 키워드가 없으면 None.
    """
    idx = text.find(_KEYWORD)
    if idx == -1:
        return None
    return text[idx:]


def _tokenize(text: str) -> List[str]:
    """선수과목 섹션을 토큰 리스트로 분해.

    토큰 종류: 과목 코드 | '또는' | 'or' | ',' | '(' | ')'.

    Args:
        text: 선수과목 섹션 문자열.

    Returns:
        토큰 문자열 리스트.
    """
    return _TOKEN_RE.findall(text)


def _build_tree(tokens: List[str]) -> Dict[str, Any]:
    """토큰 리스트 → AND/OR 트리 dict.

    Args:
        tokens: _tokenize 출력.

    Returns:
        루트 노드 dict (leaf / and / or).

    Raises:
        ValueError: 괄호 비대칭, 파싱 가능한 토큰 없음 등 파싱 실패.
    """
    segments = _split_top_level(tokens)
    children = [_parse_segment(seg) for seg in segments if seg]
    if not children:
        raise ValueError("파싱 가능한 선수과목 토큰 없음")
    if len(children) == 1:
        return children[0]
    return {"type": "and", "children": children}


def _split_top_level(tokens: List[str]) -> List[List[str]]:
    """괄호 깊이 0의 콤마로 분할. 괄호 비대칭이면 ValueError."""
    segments: List[List[str]] = []
    current: List[str] = []
    depth = 0
    for tok in tokens:
        if tok == "(":
            depth += 1
        elif tok == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("괄호 비대칭: 닫는 괄호 초과")
        if tok == "," and depth == 0:
            segments.append(current)
            current = []
        else:
            current.append(tok)
    if depth != 0:
        raise ValueError("괄호 비대칭: 여는 괄호 미닫힘")
    segments.append(current)
    return segments


def _collect_group(tokens: List[str], i: int) -> Tuple[List[str], int]:
    """tokens[i] == '(' 전제. 매칭 ')'까지 내부 토큰과 다음 인덱스 반환."""
    depth = 1
    j = i + 1
    while j < len(tokens):
        if tokens[j] == "(":
            depth += 1
        elif tokens[j] == ")":
            depth -= 1
            if depth == 0:
                return tokens[i + 1 : j], j + 1
        j += 1
    raise ValueError("괄호 비대칭: 여는 괄호 미닫힘")


def _parse_segment(tokens: List[str]) -> Dict[str, Any]:
    """콤마 없는 구간 파싱. '또는'/'or' 연결 → OR.

    'B(또는 C ...)' 처럼 괄호 내용이 OR 접속사로 시작하면
    직전 노드를 OR 그룹의 첫 원소로 끌어들인다 (테스트 케이스 기준).
    """
    items: List[Dict[str, Any]] = []
    or_seen = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _OR_WORDS:
            or_seen = True
            i += 1
        elif tok == "(":
            inner, i = _collect_group(tokens, i)
            if inner and inner[0] in _OR_WORDS and items:
                prev = items.pop()
                group = _parse_segment(inner)
                members = (
                    group["children"] if group.get("type") == "or" else [group]
                )
                items.append({"type": "or", "children": [prev, *members]})
            else:
                items.append(_parse_segment(inner))
        elif tok == ")":
            raise ValueError("괄호 비대칭: 닫는 괄호 초과")
        else:
            items.append({"type": "course", "code": tok})
            i += 1
    if not items:
        raise ValueError("빈 괄호 그룹")
    if or_seen and len(items) > 1:
        return {"type": "or", "children": items}
    if len(items) == 1:
        return items[0]
    return {"type": "and", "children": items}
