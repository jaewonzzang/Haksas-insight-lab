"""카드 A 추천도 점수 결합 (결정론).

정규화 가중합(hybrid) → 선이수 감산 → 고정 컷오프. signal 계산과 분리된 순수 함수.
가중치/감산/컷오프는 weights.py (전문가 prior). restriction·LLM·signal 계산은 범위 밖.
스펙: docs/superpowers/specs/2026-06-30-card-a-scoring-weights-design.md
"""

from typing import Literal

from pydantic import BaseModel

from app.engines.recommender.weights import (
    FACTOR_WEIGHTS,
    GRADE_CUTOFFS,
    PREREQ_PENALTY_MAX,
)

PREREQ_LABEL = "선이수 충족도"


class Factor(BaseModel):
    label: str
    weight_percent: int
    contribution: str
    kind: Literal["pos", "neg", "mid", "na"]


class ScoredCandidate(BaseModel):
    score_percent: int
    grade: Literal["강추", "고려", "유보"]
    factors: list[Factor]


def _grade(score: int) -> str:
    if score >= GRADE_CUTOFFS["강추"]:
        return "강추"
    if score >= GRADE_CUTOFFS["고려"]:
        return "고려"
    return "유보"


def score_candidate(
    signals: dict[str, float | None],
    prereq_fulfillment: float | None,
) -> ScoredCandidate:
    present = {
        label: s
        for label, s in signals.items()
        if label in FACTOR_WEIGHTS and s is not None
    }
    w_sum = sum(FACTOR_WEIGHTS[label] for label in present)

    factors: list[Factor] = []
    hybrid_base = 0.0
    for label in FACTOR_WEIGHTS:  # 고정 순서 = weights.py 정의 순서
        if label in present:
            contrib = FACTOR_WEIGHTS[label] / w_sum * present[label]
            hybrid_base += contrib
            factors.append(Factor(
                label=label,
                weight_percent=round(present[label]),
                contribution=f"+{round(contrib)}",
                kind="pos",
            ))
        else:
            factors.append(Factor(
                label=label, weight_percent=0, contribution="N/A", kind="na",
            ))

    penalty = 0
    if prereq_fulfillment is not None:
        penalty = round(PREREQ_PENALTY_MAX * (1 - prereq_fulfillment / 100))
        factors.append(Factor(
            label=PREREQ_LABEL,
            weight_percent=round(prereq_fulfillment),
            contribution=f"−{penalty}" if penalty > 0 else "+0",  # U+2212
            kind="neg" if penalty > 0 else "pos",
        ))

    score = max(0, min(100, round(hybrid_base) - penalty))
    return ScoredCandidate(score_percent=score, grade=_grade(score), factors=factors)
