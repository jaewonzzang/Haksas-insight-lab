"""prereq_eval — AND/OR 트리 충족도 평가."""

import pytest

from app.core.prereq_eval import evaluate

LEAF_A = {"type": "course", "code": "CSE1010"}
LEAF_B = {"type": "course", "code": "CSE1020"}
LEAF_C = {"type": "course", "code": "MAT2001"}


def test_leaf_met():
    r = evaluate({"CSE1010"}, LEAF_A)
    assert r.satisfied is True
    assert r.fulfillment == 100.0
    assert r.missing == []


def test_leaf_unmet():
    r = evaluate(set(), LEAF_A)
    assert r.satisfied is False
    assert r.fulfillment == 0.0
    assert r.missing == ["CSE1010"]


def test_and_partial():
    tree = {"type": "and", "children": [LEAF_A, LEAF_B]}
    r = evaluate({"CSE1010"}, tree)
    assert r.satisfied is False
    assert r.fulfillment == 50.0
    assert r.missing == ["CSE1020"]


def test_or_met_by_one():
    tree = {"type": "or", "children": [LEAF_A, LEAF_B]}
    r = evaluate({"CSE1020"}, tree)
    assert r.satisfied is True
    assert r.fulfillment == 100.0
    assert r.missing == []


def test_or_unmet_lists_all_leaves():
    tree = {"type": "or", "children": [LEAF_A, LEAF_B]}
    r = evaluate(set(), tree)
    assert r.satisfied is False
    assert r.fulfillment == 0.0
    assert set(r.missing) == {"CSE1010", "CSE1020"}


def test_nested_and_of_or():
    # AND[OR[A, B], C] — OR 충족 + C 미이수 → 50%
    tree = {"type": "and", "children": [
        {"type": "or", "children": [LEAF_A, LEAF_B]},
        LEAF_C,
    ]}
    r = evaluate({"CSE1010"}, tree)
    assert r.satisfied is False
    assert r.fulfillment == 50.0
    assert r.missing == ["MAT2001"]


def test_unknown_node_type():
    with pytest.raises(ValueError):
        evaluate(set(), {"type": "xor", "children": [LEAF_A]})
