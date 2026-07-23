"""실 Haiku 1콜 스모크 — ANTHROPIC_API_KEY 있을 때만. 없으면 skip."""

import pytest

from app import config
from app.llm import prompts, translator
from app.llm.providers.anthropic import get_provider
from app.schemas.cards import CardD, CareerEntry, CareerPattern, ClusterEvidence

pytestmark = pytest.mark.skipif(
    not config.ANTHROPIC_API_KEY, reason="ANTHROPIC_API_KEY 없음"
)


def test_live_card_d_translation():
    card = CardD(
        similar_label="유사 경로 30명", sample_size=30,
        entries=[
            CareerEntry(cluster_label="개발자", type="job", count=18, share_percent=60.0),
            CareerEntry(cluster_label="대학원", type="grad", count=7, share_percent=23.0),
        ],
        sub_title="취업 세부 분포", sub_chips=[],
        pattern_summary="유사 경로 30명 중 개발자 계열이 60%로 가장 많습니다.",
    )
    evidence = ClusterEvidence(
        factors=[], common_courses=[],
        career_patterns=[CareerPattern(label="개발자", type="job", text="유사 졸업생 18명이 이 경로를 선택")],
        summary="이수 패턴이 유사한 졸업생 30명의 진로 분포 기반",
    )
    provider = get_provider()
    assert provider is not None

    new_card, new_ev = translator.translate_card_d(card, evidence, provider)
    # 실 통역 성공 시 교체, 실패 시 폴백 — 어느 쪽이든 비어 있지 않아야 한다
    assert new_card.pattern_summary.strip()
    assert new_ev.summary.strip()
    # 구조화 출력이 실제로 파싱되는지 직접 1콜 확인
    system, user, schema = prompts.build_card_d_prompt(card, evidence)
    out = provider.translate(system, user, schema)
    assert out is not None, "실 Haiku 구조화 통역 실패 — 키/모델/SDK 확인"
    assert isinstance(out.pattern_summary, str) and out.pattern_summary.strip()
