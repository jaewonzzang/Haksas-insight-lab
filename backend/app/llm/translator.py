"""카드별 통역 패스: 완성 카드 객체의 텍스트 필드만 교체하는 순수 함수.

build()는 불변(스펙 안 A). provider=None·LLM 실패는 전부 입력 그대로 반환으로 흡수.
스펙: docs/superpowers/specs/2026-07-10-w5-llm-translator-design.md
"""

from app.llm import prompts
from app.llm.providers.base import Provider
from app.schemas.cards import CardA, CardD, ClusterEvidence, RecommendedCourse


def translate_card_a(card: CardA, provider: Provider | None) -> CardA:
    if provider is None or not (card.major or card.general):
        return card
    system, user, schema = prompts.build_card_a_prompt(card)
    out = provider.translate(system, user, schema)
    if out is None:
        return card
    by_id = {i.course_id: i.reason for i in out.items}

    def _swap(courses: list[RecommendedCourse]) -> list[RecommendedCourse]:
        return [
            c.model_copy(update={"reason_short": by_id[c.course_id]})
            if c.course_id in by_id
            else c
            for c in courses
        ]

    return card.model_copy(update={"major": _swap(card.major), "general": _swap(card.general)})


def translate_card_d(
    card: CardD, evidence: ClusterEvidence, provider: Provider | None
) -> tuple[CardD, ClusterEvidence]:
    if provider is None or card.sample_size == 0:
        return card, evidence
    system, user, schema = prompts.build_card_d_prompt(card, evidence)
    out = provider.translate(system, user, schema)
    if out is None:
        return card, evidence
    patterns = [
        p.model_copy(update={"text": t})
        for p, t in zip(evidence.career_patterns, out.pattern_texts)
    ] + list(evidence.career_patterns[len(out.pattern_texts):])
    return (
        card.model_copy(update={"pattern_summary": out.pattern_summary}),
        evidence.model_copy(update={"summary": out.cluster_summary, "career_patterns": patterns}),
    )
