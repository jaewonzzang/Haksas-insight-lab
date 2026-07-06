"""hybrid — 후보별 signal 조립 → scoring.score_candidate 위임."""

from app.engines.recommender import hybrid


def test_combine_delegates_to_scoring():
    signals_by_label = {
        "콘텐츠 유사도": {"C1": 90.0, "C2": 10.0},
        "코호트 선호도": {"C1": 80.0},  # C2 는 결측
    }
    fulfill = {"C1": None, "C2": 0.0}
    out = hybrid.combine(signals_by_label, fulfill, ["C1", "C2"])
    assert set(out) == {"C1", "C2"}
    assert out["C1"].score_percent > out["C2"].score_percent
    # C1: 감산 없음(None) / C2: prereq=0 → 최대 감산 −40 반영 → 0점 바닥
    assert out["C2"].score_percent == 0
    labels_c1 = {f.label for f in out["C1"].factors}
    assert "콘텐츠 유사도" in labels_c1 and "코호트 선호도" in labels_c1


def test_candidate_without_signals_gets_zero():
    out = hybrid.combine({}, {"C9": None}, ["C9"])
    assert out["C9"].score_percent == 0
    assert out["C9"].grade == "유보"
