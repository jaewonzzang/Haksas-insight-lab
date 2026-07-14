"""선호 매칭 — 팀플·출석·발표 비중 (잠정 prior, 2026-07-13/15)."""

from app.engines.recommender import preference

ATTRS = {
    "C1": {"team_project": "required", "attendance_ratio": 0.05, "presentation_ratio": 0.30},
    "C2": {"team_project": "none", "attendance_ratio": 0.30, "presentation_ratio": 0.0},
    "C3": {"team_project": "optional", "attendance_ratio": 0.15, "presentation_ratio": 0.10},
}


def test_team_preference_tiers():
    out = preference.score(True, False, False, ATTRS)
    assert out["C1"] == 100.0 and out["C3"] == 50.0 and out["C2"] == 0.0


def test_low_attendance_tiers():
    out = preference.score(False, True, False, ATTRS)
    assert out["C1"] == 100.0  # 참여도 5% ≤ 10%
    assert out["C3"] == 50.0  # ≤ 20%
    assert out["C2"] == 0.0


def test_presentation_tiers():
    out = preference.score(False, False, True, ATTRS)
    assert out["C1"] == 100.0  # 발표 배점 30% ≥ 20%
    assert out["C3"] == 50.0  # >0
    assert out["C2"] == 0.0


def test_multiple_prefs_averaged():
    # 팀플+발표 평균: C1=(100+100)/2, C3=(50+50)/2, C2=(0+0)/2
    out = preference.score(True, False, True, ATTRS)
    assert out["C1"] == 100.0 and out["C3"] == 50.0 and out["C2"] == 0.0


def test_no_selection_or_no_attrs_empty():
    assert preference.score(False, False, False, ATTRS) == {}
    assert preference.score(True, True, True, {}) == {}
