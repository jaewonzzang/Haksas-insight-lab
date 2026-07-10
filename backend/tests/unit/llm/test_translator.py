"""translator: FakeProvider로 교체·폴백 경로 검증. 실 API 호출 없음."""

from pydantic import BaseModel

from app.llm import translator
from app.llm.prompts import CardAItem, CardATranslation, CardDTranslation
from app.schemas.cards import (
    CardD,
    CareerEntry,
    CareerPattern,
    ClusterEvidence,
)
from tests.unit.llm.fixtures import make_card_a


class FakeProvider:
    def __init__(self, out: BaseModel | None):
        self.out = out
        self.calls: list[tuple[str, str, type]] = []

    def translate(self, system, user, schema):
        self.calls.append((system, user, schema))
        return self.out


def _card_d() -> tuple[CardD, ClusterEvidence]:
    card = CardD(
        similar_label="유사 경로 30명", sample_size=30,
        entries=[CareerEntry(cluster_label="개발자", type="job", count=18, share_percent=60.0)],
        sub_title="취업 세부 분포", sub_chips=[],
        pattern_summary="유사 경로 30명 중 개발자 계열이 60%로 가장 많습니다.",
    )
    evidence = ClusterEvidence(
        factors=[], common_courses=[],
        career_patterns=[
            CareerPattern(label="개발자", type="job", text="유사 졸업생 18명이 이 경로를 선택"),
            CareerPattern(label="대학원", type="grad", text="유사 졸업생 7명이 이 경로를 선택"),
        ],
        summary="이수 패턴이 유사한 졸업생 30명의 진로 분포 기반",
    )
    return card, evidence


# --- 카드 A ---

def test_card_a_replaces_display_reasons_only():
    card = make_card_a()
    ids = [c.course_id for c in [*card.major, *card.general]]
    out = CardATranslation(items=[CardAItem(course_id=i, reason=f"{i} 통역") for i in ids])
    result = translator.translate_card_a(card, FakeProvider(out))
    assert [c.reason_short for c in result.major] == [f"{i} 통역" for i in ids[:4]]
    assert [c.reason_short for c in result.general] == [f"{i} 통역" for i in ids[4:]]
    # candidates·why_summary는 결정론 유지
    assert all(c.reason_short == "코호트 선호도 신호가 가장 강한 과목" for c in result.candidates)
    assert all(c.why_summary == "강추 · 추천도 82%" for c in result.major)
    # 순수 함수 — 입력 불변
    assert card.major[0].reason_short == "코호트 선호도 신호가 가장 강한 과목"


def test_card_a_partial_ids_keep_fallback():
    card = make_card_a()
    first = card.major[0].course_id
    out = CardATranslation(items=[CardAItem(course_id=first, reason="통역됨")])
    result = translator.translate_card_a(card, FakeProvider(out))
    assert result.major[0].reason_short == "통역됨"
    assert result.major[1].reason_short == "코호트 선호도 신호가 가장 강한 과목"


def test_card_a_provider_failure_returns_input():
    card = make_card_a()
    assert translator.translate_card_a(card, FakeProvider(None)) is card


def test_card_a_no_provider_returns_input():
    card = make_card_a()
    assert translator.translate_card_a(card, None) is card


def test_card_a_empty_card_skips_call():
    from app.schemas.cards import CardA
    empty = CardA(major=[], general=[], candidates=[])
    fake = FakeProvider(None)
    assert translator.translate_card_a(empty, fake) is empty
    assert fake.calls == []


# --- 카드 D ---

def test_card_d_replaces_three_fields():
    card, evidence = _card_d()
    out = CardDTranslation(
        pattern_summary="요약 통역", cluster_summary="근거 통역",
        pattern_texts=["패턴1 통역", "패턴2 통역"],
    )
    new_card, new_ev = translator.translate_card_d(card, evidence, FakeProvider(out))
    assert new_card.pattern_summary == "요약 통역"
    assert new_ev.summary == "근거 통역"
    assert [p.text for p in new_ev.career_patterns] == ["패턴1 통역", "패턴2 통역"]
    # 나머지 필드 불변
    assert new_card.entries == card.entries
    assert new_ev.career_patterns[0].label == "개발자"


def test_card_d_short_pattern_texts_keep_fallback_tail():
    card, evidence = _card_d()
    out = CardDTranslation(pattern_summary="요약", cluster_summary="근거", pattern_texts=["하나만"])
    _, new_ev = translator.translate_card_d(card, evidence, FakeProvider(out))
    assert new_ev.career_patterns[0].text == "하나만"
    assert new_ev.career_patterns[1].text == "유사 졸업생 7명이 이 경로를 선택"


def test_card_d_provider_failure_returns_inputs():
    card, evidence = _card_d()
    new_card, new_ev = translator.translate_card_d(card, evidence, FakeProvider(None))
    assert new_card is card and new_ev is evidence


def test_card_d_empty_sample_skips_call():
    card, evidence = _card_d()
    empty = card.model_copy(update={"sample_size": 0})
    fake = FakeProvider(None)
    new_card, _ = translator.translate_card_d(empty, evidence, fake)
    assert new_card is empty
    assert fake.calls == []
