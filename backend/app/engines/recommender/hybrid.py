"""signal 결합: 후보별 signals + 선이수 충족률 → ScoredCandidate.

가중 결합·감산·컷오프·factors 분해는 scoring.score_candidate
(스펙 2026-06-30 확정 구현)에 위임한다.
"""

from typing import Optional, Sequence

from app.engines.recommender.scoring import ScoredCandidate, score_candidate


def combine(
    signals_by_label: dict[str, dict[str, float]],
    fulfillments: dict[str, Optional[float]],
    candidate_ids: Sequence[str],
) -> dict[str, ScoredCandidate]:
    out: dict[str, ScoredCandidate] = {}
    for cid in candidate_ids:
        signals = {
            label: scores[cid]
            for label, scores in signals_by_label.items()
            if cid in scores
        }
        out[cid] = score_candidate(signals, fulfillments.get(cid))
    return out
