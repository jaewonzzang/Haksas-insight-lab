"""선이수 필터: 후보별 충족률(0~100 | None) 산출.

감산 수치는 scoring.score_candidate(PREREQ_PENALTY_MAX)가 계산한다 —
여기서 점수를 깎으면 감산 로직이 이중화되므로 충족률만 공급한다.
hybrid 이후 감산이라는 결합 순서(CLAUDE.md)는 hybrid.combine 내부에서
signal 가중 결합 → 감산 순으로 적용되어 보존된다.
"""

from typing import Optional, Sequence

from app.core.prereq_eval import evaluate


def fulfillments(
    taken: set[str],
    candidate_ids: Sequence[str],
    trees: dict[str, Optional[dict]],
) -> dict[str, Optional[float]]:
    out: dict[str, Optional[float]] = {}
    for cid in candidate_ids:
        tree = trees.get(cid)
        out[cid] = evaluate(taken, tree).fulfillment if tree else None
    return out
