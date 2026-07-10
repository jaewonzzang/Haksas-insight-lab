"""prompts 빌더: 정형 값만 담고 (system, user, schema)를 반환하는지."""

from app.llm import prompts
from app.schemas.cards import (
    CardD,
    CareerEntry,
    CareerPattern,
    CareerSubChip,
    ClusterEvidence,
    CommonCourse,
    SimilarityFactor,
)
from tests.unit.llm.fixtures import make_card_a


def test_card_a_prompt_contains_values_and_schema():
    card = make_card_a()
    system, user, schema = prompts.build_card_a_prompt(card)
    assert schema is prompts.CardATranslation
    assert "점수" in system  # 점수·판정 금지 지시
    # 정형 값이 user 페이로드에 그대로 들어간다
    assert "AIE1001" in user and "인공지능개론" in user
    assert "강추" in user and "82" in user
    assert "코호트 선호도" in user  # 최상위 pos factor label


def test_card_d_prompt_contains_values_and_schema():
    card = CardD(
        similar_label="유사 경로 30명", sample_size=30,
        entries=[CareerEntry(cluster_label="개발자", type="job", count=18, share_percent=60.0)],
        sub_title="취업 세부 분포",
        sub_chips=[CareerSubChip(label="개발자", n=18)],
        pattern_summary="유사 경로 30명 중 개발자 계열이 60%로 가장 많습니다.",
    )
    evidence = ClusterEvidence(
        factors=[SimilarityFactor(label="이수과목 중복도", percent=41.0)],
        common_courses=[CommonCourse(name="자료구조", n=22)],
        career_patterns=[CareerPattern(label="개발자", type="job", text="유사 졸업생 18명이 이 경로를 선택")],
        summary="이수 패턴이 유사한 졸업생 30명의 진로 분포 기반",
    )
    system, user, schema = prompts.build_card_d_prompt(card, evidence)
    assert schema is prompts.CardDTranslation
    assert "개발자" in user and "60" in user
    assert "이수과목 중복도" in user and "41" in user
    assert "취업 세부 분포" in user
