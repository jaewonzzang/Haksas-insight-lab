"""추가학점 근사(observed_credits) 단위 테스트."""

from scripts.enrich_alumni_credits import observed_credits

COURSES = {
    "BUS101": ("경영학부(경영학전공)", 3.0, 0),
    "BUS201": ("경영학부(경영학전공)", 3.0, 0),
    "GEN001": ("전인교육원", 3.0, 1),
    "CSE100": ("컴퓨터공학과", 3.0, 0),
}
ALIAS = {"OLDBUS": "BUS201"}
DEPTS = {"경영학부(경영학전공)"}


def test_sums_only_target_dept_non_general():
    ids = ["BUS101", "GEN001", "CSE100"]
    assert observed_credits(ids, DEPTS, COURSES, ALIAS) == 3.0


def test_alias_maps_old_code():
    assert observed_credits(["OLDBUS"], DEPTS, COURSES, ALIAS) == 3.0


def test_retake_counts_once():
    assert observed_credits(["BUS101", "BUS101"], DEPTS, COURSES, ALIAS) == 3.0


def test_unknown_course_ignored():
    assert observed_credits(["NOPE999"], DEPTS, COURSES, ALIAS) == 0.0
