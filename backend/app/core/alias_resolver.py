"""학생 이수 set 확장: 옛 코드/대체과목 → 신 과목으로 단방향 매핑.

course_aliases 테이블 기반. old_course_id 또는 old_course_name 매칭 → new_course_id 추가.
"""

from typing import Iterable, Optional, Tuple

AliasTriple = Tuple[Optional[str], Optional[str], str]
# (old_course_id, old_course_name, new_course_id) — course_queries.list_aliases 순서


def expand_taken(taken: set[str], aliases: Iterable[AliasTriple]) -> set[str]:
    """taken 에 old 코드/과목명이 있으면 new_course_id 를 추가 (단방향 1-pass)."""
    expanded = set(taken)
    for old_id, old_name, new_id in aliases:
        if (old_id and old_id in taken) or (old_name and old_name in taken):
            expanded.add(new_id)
    return expanded
