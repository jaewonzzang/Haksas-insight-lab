"""'과목 설명' 원문 → 선수과목 AND/OR 트리 JSON.

역할:
    - '선수과목' 키워드 이후 섹션 추출
    - 정규식 [A-Z]{2,5}\\d{3,4}[A-Z]? 로 과목 코드 매칭
    - 콤마 = AND, '또는'/'or' = OR, 괄호 = OR 그룹 경계
    - 트리 JSON 직렬화

입력:
    course_id (str), description_raw (Optional[str])

출력:
    (prereq_record: Optional[dict], warnings: list[dict])
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

from typing import Any, Dict, List, Optional, Tuple


def parse_prerequisites(
    course_id: str,
    description_raw: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
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
          warnings: 정규식 매칭 실패, 괄호 비대칭 등.
    """
    raise NotImplementedError("4b 단계에서 구현")


def _extract_prereq_section(text: str) -> Optional[str]:
    """text 에서 '선수과목' 키워드 이후 섹션만 잘라 반환.

    Args:
        text: 과목 설명 원문.

    Returns:
        선수과목 섹션 문자열, 또는 키워드가 없으면 None.
    """
    raise NotImplementedError("4b 단계에서 구현")


def _tokenize(text: str) -> List[str]:
    """선수과목 섹션을 토큰 리스트로 분해.

    토큰 종류: 과목 코드 | '또는' | 'or' | ',' | '(' | ')'.

    Args:
        text: 선수과목 섹션 문자열.

    Returns:
        토큰 문자열 리스트.
    """
    raise NotImplementedError("4b 단계에서 구현")


def _build_tree(tokens: List[str]) -> Dict[str, Any]:
    """토큰 리스트 → AND/OR 트리 dict.

    Args:
        tokens: _tokenize 출력.

    Returns:
        루트 노드 dict (leaf / and / or).

    Raises:
        ValueError: 괄호 비대칭, 알 수 없는 토큰 등 파싱 실패.
    """
    raise NotImplementedError("4b 단계에서 구현")
