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
CURRICULUM = {"CSE1010", "CSE2020", "AAT3001", "REL1001"}


def test_weighted_by_similarity():
    scores = collaborative.score(TAKEN, ["AAT3001", "REL1001"], ALUMNI, CURRICULUM)
    # a1(가중치>0)만 반영: AAT3001 수강 → 100, REL1001 미수강 → 0
    assert scores["AAT3001"] == 100.0
    assert scores["REL1001"] == 0.0


def test_no_similar_alumni_returns_empty():
    assert collaborative.score({"XXX9999"}, ["AAT3001"], ALUMNI, CURRICULUM) == {}


def test_empty_enrollment_skipped():
    empty = AlumniRecord(alumni_id="a3", department="경영학과")
    assert collaborative.score(TAKEN, ["AAT3001"], [empty], CURRICULUM) == {}


def test_retired_courses_do_not_dilute_similarity():
    """폐지 과목은 교집합엔 0, 합집합엔 +1 → 옛 졸업생의 표를 깎는다.

    실측 2026-07-17: 20학번 -5.9% · 24학번 이후 0% (학번 단조).
    현행 교과과정 과목만 세면 두 졸업생이 동률이어야 한다.
    """
    old = _alum("old", ["CSE1010", "CSE2020", "AAT3001", "OLD9001", "OLD9002"])
    new = _alum("new", ["CSE1010", "CSE2020", "AAT3001"])
    both = collaborative.score(TAKEN, ["AAT3001"], [old], CURRICULUM)
    only_new = collaborative.score(TAKEN, ["AAT3001"], [new], CURRICULUM)
    assert both == only_new == {"AAT3001": 100.0}


def test_curriculum_filter_applies_to_student_side_too():
    """학생이 폐지 과목을 이수했어도 분모를 키우면 안 된다 (대칭)."""
    a = collaborative.score({"CSE1010", "CSE2020", "OLD9001"}, ["AAT3001"], ALUMNI, CURRICULUM)
    b = collaborative.score(TAKEN, ["AAT3001"], ALUMNI, CURRICULUM)
    assert a == b
