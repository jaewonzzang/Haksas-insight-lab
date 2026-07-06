"""restriction_filter — forbidden/major_only_forbidden 차단."""

from app.engines.recommender import restriction_filter
from app.engines.recommender.scoring import score_candidate

SCORED = {cid: score_candidate({"콘텐츠 유사도": 80.0}, None) for cid in ["C1", "C2", "C3", "C4"]}


def _r(cid, dept, status):
    return {"course_id": cid, "target_dept": dept, "status": status}


RESTRICTIONS = [
    _r("C1", "컴퓨터공학과", "forbidden"),
    _r("C2", "컴퓨터공학과", "major_only_forbidden"),
    _r("C3", "컴퓨터공학과", "allowed"),        # 차단 안 함
    _r("C4", "경영학과", "forbidden"),          # 타 학과 대상 → 무관
]


def test_forbidden_blocked():
    out = restriction_filter.apply(dict(SCORED), {"컴퓨터공학과"}, True, RESTRICTIONS)
    assert set(out) == {"C3", "C4"}


def test_major_only_forbidden_passes_for_non_first_major():
    out = restriction_filter.apply(dict(SCORED), {"컴퓨터공학과"}, False, RESTRICTIONS)
    assert set(out) == {"C2", "C3", "C4"}
