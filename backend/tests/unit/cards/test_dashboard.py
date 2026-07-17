"""dashboard 오케스트레이터: 카드 스텁 + provider 몽키패치로 조립 로직만 검증."""

from app.cards import dashboard
from app.schemas.cards import (
    CardC,
    CardD,
    CareerEntry,
    ClusterEvidence,
)
from app.schemas.input import StudentInput
from tests.unit.llm.fixtures import make_card_a
from tests.unit.llm.test_translator import FakeProvider  # 정상/실패 provider 재사용
from app.llm.prompts import CardAItem, CardATranslation


def _student() -> StudentInput:
    return StudentInput(
        student_id="A",
        department="지식융합미디어학부",
        taken_course_ids=["CSE3080", "MAS1001"],
        interest_career=None,
        consider_multimajor=True,
    )


def _stub_cards(monkeypatch):
    card_d_obj = CardD(
        similar_label="유사 경로 30명", sample_size=30,
        entries=[CareerEntry(cluster_label="개발자", type="job", count=18, share_percent=60.0)],
        sub_title="취업 세부 분포", sub_chips=[],
        pattern_summary="유사 경로 30명 중 개발자 계열이 60%로 가장 많습니다.",
    )
    evidence = ClusterEvidence(factors=[], common_courses=[], career_patterns=[], summary="근거 폴백")
    monkeypatch.setattr(dashboard.card_a, "build", lambda s, con, al: make_card_a())
    monkeypatch.setattr(
        dashboard.card_c, "build",
        lambda s, al: CardC(cohort_label="지식융합미디어학부 · 졸업생 180명", entries=[], baseline_note=""),
    )
    monkeypatch.setattr(dashboard.card_d, "build", lambda s, con, al: (card_d_obj, evidence))
    monkeypatch.setattr(
        dashboard.course_queries, "list_by_ids",
        lambda con, ids: [{"credit": 3.0}, {"credit": None}],
    )


def test_assembles_profile_kpi_with_fallback(monkeypatch):
    _stub_cards(monkeypatch)
    monkeypatch.setattr(dashboard, "get_provider", lambda: None)  # 키 없음 = 폴백
    resp = dashboard.build(_student(), con=None, alumni=[], career_alumni=[])
    assert resp.profile.name == "학생 A"
    assert resp.profile.department == "지식융합미디어학부"
    assert resp.profile.report_semester == "2026-1학기"
    assert resp.profile.next_semester == "2026-2"
    assert resp.kpi.earned_credits == 3.0  # credit None은 0 취급
    assert resp.kpi.gpa is None and resp.kpi.gpa_scale == 4.3
    assert resp.kpi.similar_alumni_n == 30
    # provider 없음 → 폴백 문구 그대로
    assert resp.card_a.major[0].reason_short == "코호트 선호도 신호가 가장 강한 과목"
    assert resp.cluster.summary == "근거 폴백"


def test_injects_translator_when_provider_available(monkeypatch):
    _stub_cards(monkeypatch)
    ids = [f"AIE100{i}" for i in range(1, 5)] + [f"GEN200{i}" for i in range(1, 5)]
    out = CardATranslation(items=[CardAItem(course_id=i, reason=f"{i} 통역") for i in ids])
    monkeypatch.setattr(dashboard, "get_provider", lambda: FakeProvider(out))
    # FakeProvider는 스키마 인자를 무시하고 CardATranslation을 카드 D에도 반환하므로
    # pattern_texts 접근에서 AttributeError — 카드 D 통역은 우회 (test_translator에서 검증 완료).
    monkeypatch.setattr(dashboard.translator, "translate_card_d", lambda c, e, p: (c, e))
    resp = dashboard.build(_student(), con=None, alumni=[], career_alumni=[])
    assert resp.card_a.major[0].reason_short == "AIE1001 통역"
