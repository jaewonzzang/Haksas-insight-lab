"""prereq_filter — 후보별 선이수 충족률(0~100|None)."""

from app.engines.recommender import prereq_filter

TREE_A = {"type": "course", "code": "CSE1010"}
TREE_AND = {"type": "and", "children": [
    {"type": "course", "code": "CSE1010"},
    {"type": "course", "code": "MAT2001"},
]}


def test_fulfillments():
    trees = {"CSE2020": TREE_A, "CSE3030": TREE_AND, "REL1001": None}
    result = prereq_filter.fulfillments({"CSE1010"}, ["CSE2020", "CSE3030", "REL1001"], trees)
    assert result == {"CSE2020": 100.0, "CSE3030": 50.0, "REL1001": None}


def test_missing_tree_key_is_none():
    assert prereq_filter.fulfillments(set(), ["X1"], {}) == {"X1": None}
