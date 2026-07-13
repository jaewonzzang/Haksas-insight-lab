"""선호 매칭 — 팀플·출석 비중 (잠정 prior, 2026-07-13)."""

from app.engines.recommender import preference

ATTRS = {
    "C1": {"team_project": "required", "attendance_ratio": 0.05},
    "C2": {"team_project": "none", "attendance_ratio": 0.30},
    "C3": {"team_project": "optional", "attendance_ratio": 0.15},
}


def test_team_preference_tiers():
    out = preference.score(True, False, ATTRS)
    assert out["C1"] == 100.0 and out["C3"] == 50.0 and out["C2"] == 0.0


def test_low_attendance_tiers():
    out = preference.score(False, True, ATTRS)
    assert out["C1"] == 100.0  # 참여도 5% ≤ 10%
    assert out["C3"] == 50.0  # ≤ 20%
    assert out["C2"] == 0.0


def test_both_prefs_averaged():
    out = preference.score(True, True, ATTRS)
    assert out["C1"] == 100.0 and out["C3"] == 50.0


def test_no_selection_or_no_attrs_empty():
    assert preference.score(False, False, ATTRS) == {}
    assert preference.score(True, True, {}) == {}
