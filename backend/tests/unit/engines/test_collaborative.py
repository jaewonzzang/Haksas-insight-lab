"""collaborative — Jaccard 가중 코호트 선호도 signal."""

from app.adapters.alumni_types import AlumniRecord, Enrollment
from app.engines.recommender import collaborative


def _alum(aid, course_ids):
    return AlumniRecord(
        alumni_id=aid,
        department="아트&테크놀로지",
        enrollment=[Enrollment(course_id=c) for c in course_ids],
    )


ALUMNI = [
    _alum("a1", ["CSE1010", "CSE2020", "AAT3001"]),  # 학생과 겹침 큼
    _alum("a2", ["REL1001", "AAT3001"]),             # 겹침 없음 → 가중치 0
]
TAKEN = {"CSE1010", "CSE2020"}


def test_weighted_by_similarity():
    scores = collaborative.score(TAKEN, ["AAT3001", "REL1001"], ALUMNI)
    # a1(가중치>0)만 반영: AAT3001 수강 → 100, REL1001 미수강 → 0
    assert scores["AAT3001"] == 100.0
    assert scores["REL1001"] == 0.0


def test_no_similar_alumni_returns_empty():
    assert collaborative.score({"XXX9999"}, ["AAT3001"], ALUMNI) == {}


def test_empty_enrollment_skipped():
    empty = AlumniRecord(alumni_id="a3", department="경영학과")
    assert collaborative.score(TAKEN, ["AAT3001"], [empty]) == {}
