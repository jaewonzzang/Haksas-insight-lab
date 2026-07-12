"""signal 결합: 후보별 signals + 선이수 충족률 → ScoredCandidate.

각 signal은 candidate_ids 집합 내 최대값 기준 0~100 상대 강도로 리스케일 후 결합한다
(2026-07-12 max-스케일 도입 → 2026-07-13 그룹 한정으로 확장, 사용자 승인).
호출부가 그룹(전공/교양)별로 나눠 부르면 그룹 내 상대 강도가 된다.
가중 결합·감산·컷오프·factors 분해는 scoring.score_candidate
(스펙 2026-06-30 확정 구현)에 위임한다.
"""

from typing import Optional, Sequence

from app.engines.recommender.scoring import ScoredCandidate, score_candidate


def _max_scale(scores: dict[str, float]) -> dict[str, float]:
    """풀 내 상대 강도: 최대값 기준 0~100 리스케일. 최대가 0 이하면 그대로."""
    m = max(scores.values(), default=0.0)
    if m <= 0:
        return dict(scores)
    return {cid: v / m * 100 for cid, v in scores.items()}


def combine(
    signals_by_label: dict[str, dict[str, float]],
    fulfillments: dict[str, Optional[float]],
    candidate_ids: Sequence[str],
) -> dict[str, ScoredCandidate]:
    idset = set(candidate_ids)
    scaled = {
        label: _max_scale({cid: v for cid, v in scores.items() if cid in idset})
        for label, scores in signals_by_label.items()
    }
    out: dict[str, ScoredCandidate] = {}
    for cid in candidate_ids:
        signals = {
            label: scores[cid]
            for label, scores in scaled.items()
            if cid in scores
        }
        out[cid] = score_candidate(signals, fulfillments.get(cid))
    return out
