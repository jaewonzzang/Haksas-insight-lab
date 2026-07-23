"""수강 제한 차단: 블랙리스트(forbidden 계) + 화이트리스트(allowed 계) 시행.

2026-07-23 사용자 확정 — 구 "allowed 계열은 정보성" 결정을 뒤집음: 화이트리스트 행이
있는 과목은 학생이 그 목록에 들 때만 통과 (예: "컴퓨터공학과(1전공 가능)"만 걸린
과목은 컴공 2전공생 차단). 학과별 전공 지위(1전공/2전공)를 구분해 판정한다.
파이프라인 마지막 단계 — 점수 산출 이후 적용해 협업 신호를 보존한다.
비정형 비고(remarks_raw 학번 홀짝 등)는 시행 불가 — 최종 판정은 수강신청 시스템 게이트.
"""

from typing import Iterable, Mapping

from app.engines.recommender.scoring import ScoredCandidate


def apply(
    scored: dict[str, ScoredCandidate],
    primary_depts: set[str],
    all_depts: set[str],
    restrictions: Iterable[Mapping],
) -> dict[str, ScoredCandidate]:
    """primary_depts = 1전공(주전공) 학과 합집합, all_depts = 전 전공 학과 합집합 (원문 표기)."""
    blocked: set[str] = set()
    whitelisted: dict[str, bool] = {}  # 화이트리스트 행 보유 과목 → 학생 포함 여부
    for row in restrictions:
        cid, dept, status = row["course_id"], row["target_dept"], row["status"]
        if status == "forbidden":
            if dept in all_depts:
                blocked.add(cid)
        elif status == "major_only_forbidden":
            if dept in primary_depts:
                blocked.add(cid)
        elif status == "allowed":
            whitelisted[cid] = whitelisted.get(cid, False) or dept in all_depts
        elif status == "major_only_allowed":
            whitelisted[cid] = whitelisted.get(cid, False) or dept in primary_depts
    blocked.update(cid for cid, ok in whitelisted.items() if not ok)
    return {cid: sc for cid, sc in scored.items() if cid not in blocked}
