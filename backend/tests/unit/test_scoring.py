"""score_candidate 단위 테스트 (mock signal)."""

from app.engines.recommender.scoring import score_candidate

ALL_SIX = ["코호트 선호도", "콘텐츠 유사도", "시간 가중 평점",
           "사용자 선호 매칭", "트랙 충족도", "학년 적합도"]


def test_all_present_full_signal_no_prereq():
    s = {label: 100 for label in ALL_SIX}
    r = score_candidate(s, None)
    assert r.score_percent == 100
    assert r.grade == "강추"
    assert len(r.factors) == 6  # 선이수 factor 없음
    assert all(f.kind == "pos" for f in r.factors)
    assert sum(int(f.contribution) for f in r.factors) == 100


def test_na_factors_do_not_deflate_score():
    # 코호트·콘텐츠만 만점, 나머지 4개 N/A → 정규화로 100 유지
    s = {"코호트 선호도": 100, "콘텐츠 유사도": 100,
         "시간 가중 평점": None, "사용자 선호 매칭": None,
         "트랙 충족도": None, "학년 적합도": None}
    r = score_candidate(s, None)
    assert r.score_percent == 100
    na = [f for f in r.factors if f.kind == "na"]
    assert len(na) == 4
    assert all(f.contribution == "N/A" and f.weight_percent == 0 for f in na)


def test_prereq_penalty_subtracts_after_hybrid():
    s = {label: 80 for label in ALL_SIX}
    r = score_candidate(s, 50)  # penalty = round(40 * (1 - 0.5)) = 20
    assert r.score_percent == 60  # 80 - 20
    assert r.grade == "고려"
    prereq = next(f for f in r.factors if f.label == "선이수 충족도")
    assert prereq.contribution == "−20"  # U+2212
    assert prereq.kind == "neg"
    assert prereq.weight_percent == 50


def test_prereq_fully_met_no_penalty():
    r = score_candidate({"코호트 선호도": 90}, 100)  # penalty 0
    prereq = next(f for f in r.factors if f.label == "선이수 충족도")
    assert prereq.contribution == "+0"
    assert prereq.kind == "pos"


def test_prereq_zero_yields_max_penalty():
    # 스펙 §6: prereq_fulfillment=0 → 감산 = PREREQ_PENALTY_MAX(40)
    s = {label: 80 for label in ALL_SIX}
    r = score_candidate(s, 0)  # penalty = round(40 * (1 - 0)) = 40
    assert r.score_percent == 40  # 80 - 40
    assert r.grade == "유보"
    prereq = next(f for f in r.factors if f.label == "선이수 충족도")
    assert prereq.contribution == "−40"  # U+2212
    assert prereq.kind == "neg"
    assert prereq.weight_percent == 0


def test_all_none_yields_zero_yubo():
    s = {label: None for label in ALL_SIX}
    r = score_candidate(s, None)
    assert r.score_percent == 0
    assert r.grade == "유보"


def test_grade_cutoff_boundaries():
    # 단일 factor → score == round(signal) (정규화로 신호값 그대로)
    assert score_candidate({"코호트 선호도": 80}, None).grade == "강추"
    assert score_candidate({"코호트 선호도": 79}, None).grade == "고려"
    assert score_candidate({"코호트 선호도": 60}, None).grade == "고려"
    assert score_candidate({"코호트 선호도": 59}, None).grade == "유보"
