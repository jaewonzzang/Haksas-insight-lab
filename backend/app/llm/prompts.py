"""카드별 (system, user, schema) 프롬프트 빌더 + 통역 출력 스키마.

LLM에는 정형 값만 전달하고 문장화만 요청한다. 점수·판정 로직 금지 (CLAUDE.md).
스펙: docs/superpowers/specs/2026-07-10-w5-llm-translator-design.md
"""

import json

from pydantic import BaseModel

from app.schemas.cards import CardA, CardD, ClusterEvidence

_SYSTEM = (
    "학사 추천 정형 데이터를 학생이 읽을 짧은 한국어로 통역한다. "
    "점수·등급·순위를 새로 만들지 말고, 주어진 값만 자연스럽게 문장화한다."
)

SYSTEM_CARD_A = _SYSTEM + " reason은 과목당 1문장(40자 내외), 기존 추천 사유 톤을 유지한다."
SYSTEM_CARD_D = _SYSTEM + " pattern_summary와 cluster_summary는 각각 1~2문장으로 쓴다."


class CardAItem(BaseModel):
    course_id: str
    reason: str


class CardATranslation(BaseModel):
    items: list[CardAItem]


class CardDTranslation(BaseModel):
    pattern_summary: str
    cluster_summary: str
    pattern_texts: list[str]  # career_patterns 순서 일치


def _top_pos_factor(course) -> str:
    pos = [f for f in course.factors if f.kind == "pos"]
    if not pos:
        return ""
    return max(pos, key=lambda f: f.weight_percent).label


def build_card_a_prompt(card: CardA) -> tuple[str, str, type[CardATranslation]]:
    rows = [
        {
            "course_id": c.course_id,
            "course_name": c.course_name,
            "grade": c.grade,
            "score_percent": c.score_percent,
            "top_factor": _top_pos_factor(c),
        }
        for c in [*card.major, *card.general]
    ]
    user = json.dumps({"courses": rows}, ensure_ascii=False)
    return SYSTEM_CARD_A, user, CardATranslation


def build_card_d_prompt(
    card: CardD, evidence: ClusterEvidence
) -> tuple[str, str, type[CardDTranslation]]:
    payload = {
        "sample_size": card.sample_size,
        "sub_title": card.sub_title,
        "entries": [
            {
                "cluster_label": e.cluster_label,
                "type": e.type,
                "count": e.count,
                "share_percent": e.share_percent,
            }
            for e in card.entries
        ],
        "factors": [{"label": f.label, "percent": f.percent} for f in evidence.factors],
        "career_patterns": [
            {"label": p.label, "type": p.type} for p in evidence.career_patterns
        ],
    }
    user = json.dumps(payload, ensure_ascii=False)
    return SYSTEM_CARD_D, user, CardDTranslation
