"""pathway/distribution — 다전공 조합별 집계 (정형만)."""

from app.adapters.alumni_types import AlumniRecord, Major
from app.engines.pathway import distribution


def _alum(aid, majors):
    return AlumniRecord(alumni_id=aid, department="아트&테크놀로지학과", majors=majors)


def _m(label, role, credits):
    return Major(label=label, role=role, credits=credits)


ALUMNI = [
    _alum("a1", [_m("아트&테크놀로지학과", "primary", 80.0)]),
    _alum("a2", [_m("아트&테크놀로지학과", "primary", 84.0)]),
    _alum("a3", [_m("아트&테크놀로지학과", "primary", 60.0), _m("컴퓨터공학", "double", 40.0)]),
    _alum("a4", [_m("아트&테크놀로지학과", "primary", 64.0), _m("컴퓨터공학", "double", 44.0)]),
    _alum("a5", [_m("아트&테크놀로지학과", "primary", 61.0), _m("경영학", "double", 38.0),
                 _m("심리학", "triple", 22.0)]),
]


def test_groups_and_averages():
    groups = distribution.aggregate(ALUMNI)
    assert [(g.extra_majors, g.count) for g in groups] == [
        ([], 2),
        (["컴퓨터공학"], 2),
        (["경영학", "심리학"], 1),
    ]
    single = groups[0]
    assert single.avg_primary_credits == 82.0
    assert single.avg_second_credits is None
    double = groups[1]
    assert double.avg_primary_credits == 62.0
    assert double.avg_second_credits == 42.0
    triple = groups[2]
    assert triple.avg_third_credits == 22.0


def test_tie_breaks_lexicographic():
    alumni = [
        _alum("b1", [_m("X", "primary", 60.0), _m("경영학", "double", 40.0)]),
        _alum("b2", [_m("X", "primary", 60.0), _m("심리학", "double", 40.0)]),
    ]
    groups = distribution.aggregate(alumni)
    assert [g.extra_majors for g in groups] == [["경영학"], ["심리학"]]


def test_empty_input():
    assert distribution.aggregate([]) == []
