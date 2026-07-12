"""year_rules — 수강/권장학년 파싱 + 학년 적합도 (2026-07-13 사용자 확정 규칙)."""

from app.core.year_rules import (
    parse_recommended_years,
    parse_target_years,
    year_fit_score,
)


def test_target_all_years_and_missing():
    assert parse_target_years("전학년") == {1, 2, 3, 4}
    assert parse_target_years(None) == {1, 2, 3, 4}


def test_target_listed_years():
    assert parse_target_years("2,3,4학년") == {2, 3, 4}
    assert parse_target_years("1학년") == {1}


def test_recommended_range_and_single():
    assert parse_recommended_years("2-4학년") == {2, 3, 4}
    assert parse_recommended_years("3학년") == {3}
    assert parse_recommended_years("1-2학년") == {1, 2}


def test_year_fit_score_tiers():
    assert year_fit_score(3, {2, 3, 4}) == 100.0
    assert year_fit_score(1, {2, 3}) == 50.0  # 인접 학년
    assert year_fit_score(1, {3, 4}) == 0.0
