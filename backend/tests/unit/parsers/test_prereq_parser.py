"""prereq_parser 단위 테스트."""

import json

from app.parsers import prereq_parser


def test_no_prereq_keyword():
    """'선수과목' 키워드 없으면 (None, []).

    입력: description_raw='이 과목은 선형대수의 응용을 다룬다.'
    기대: (None, [])
    """
    record, warnings = prereq_parser.parse_prerequisites(
        "CSE2000", "이 과목은 선형대수의 응용을 다룬다."
    )
    assert record is None
    assert warnings == []


def test_single_course():
    """선수과목 1개 → leaf 노드.

    입력: '선수과목: CSE1010'
    기대 tree: {"type":"course","code":"CSE1010"}
    """
    record, _ = prereq_parser.parse_prerequisites("CSE2000", "선수과목: CSE1010")
    assert json.loads(record["prereq_tree_json"]) == {"type": "course", "code": "CSE1010"}


def test_and_two_courses():
    """콤마 = AND.

    입력: '선수과목: CSE1010, CSE1020'
    기대 tree: AND[leaf('CSE1010'), leaf('CSE1020')]
    """
    record, _ = prereq_parser.parse_prerequisites("CSE2000", "선수과목: CSE1010, CSE1020")
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "and",
        "children": [
            {"type": "course", "code": "CSE1010"},
            {"type": "course", "code": "CSE1020"},
        ],
    }


def test_or_two_courses_korean():
    """'또는' = OR (한국어).

    입력: '선수과목: CSE1010 또는 CSE1020'
    기대 tree: OR[leaf('CSE1010'), leaf('CSE1020')]
    """
    record, _ = prereq_parser.parse_prerequisites("CSE2000", "선수과목: CSE1010 또는 CSE1020")
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "or",
        "children": [
            {"type": "course", "code": "CSE1010"},
            {"type": "course", "code": "CSE1020"},
        ],
    }


def test_or_two_courses_english():
    """'or' = OR (영어).

    입력: '선수과목: CSE1010 or CSE1020'
    기대 tree: OR[leaf('CSE1010'), leaf('CSE1020')]
    """
    record, _ = prereq_parser.parse_prerequisites("CSE2000", "선수과목: CSE1010 or CSE1020")
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "or",
        "children": [
            {"type": "course", "code": "CSE1010"},
            {"type": "course", "code": "CSE1020"},
        ],
    }


def test_or_group_in_paren_then_and():
    """괄호 OR 그룹 + AND 조합.

    입력: '선수과목: (CSE1010 또는 CSE1020), MAT2001'
    기대 tree: AND[OR[leaf('CSE1010'), leaf('CSE1020')], leaf('MAT2001')]
    """
    record, _ = prereq_parser.parse_prerequisites(
        "CSE2000", "선수과목: (CSE1010 또는 CSE1020), MAT2001"
    )
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "and",
        "children": [
            {"type": "or", "children": [
                {"type": "course", "code": "CSE1010"},
                {"type": "course", "code": "CSE1020"},
            ]},
            {"type": "course", "code": "MAT2001"},
        ],
    }


def test_trailing_alpha():
    """trailing 알파벳 코드 매칭 ([A-Z]?).

    입력: '선수과목: LING1001A'
    기대 tree: leaf('LING1001A')
    """
    record, _ = prereq_parser.parse_prerequisites("LING2001", "선수과목: LING1001A")
    assert json.loads(record["prereq_tree_json"]) == {"type": "course", "code": "LING1001A"}


def test_unbalanced_paren_warning():
    """괄호 비대칭 → error warning.

    입력: '선수과목: (CSE1010, MAT2001'
    기대: (None, warning 1건 severity='error')
    """
    record, warnings = prereq_parser.parse_prerequisites(
        "CSE2000", "선수과목: (CSE1010, MAT2001"
    )
    assert record is None
    assert len(warnings) == 1
    assert warnings[0].severity == "error"


def test_regex_no_match_warning():
    """선수과목 키워드 있는데 코드 매칭 0건 → warning.

    입력: '선수과목: 자료구조와 알고리즘'
    기대: (None, warning 1건 severity='warning')
    """
    record, warnings = prereq_parser.parse_prerequisites(
        "CSE2000", "선수과목: 자료구조와 알고리즘"
    )
    assert record is None
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"


def test_or_group_in_paren_after_and():
    """선수과목 케이스: 'A, B(또는 C 또는 D)'.

    괄호가 직전 코드 B 부터 OR 그룹의 첫 원소로 끌어들이는 해석.

    입력:  '선수과목: ECO2001, ECO2003(또는 STS2005 또는 STS2006)'
    기대 트리:
        AND[
            leaf('ECO2001'),
            OR[
                leaf('ECO2003'),
                leaf('STS2005'),
                leaf('STS2006'),
            ]
        ]

    구버전 placeholder (tests/unit/test_prereq_tree.py) 에서
    명시된 케이스를 4a-clean-2 단계에서 이관.
    4b 본문 구현 시 실제 데이터로 검증되면 해석 조정 가능.
    """
    record, _ = prereq_parser.parse_prerequisites(
        "ECO3000", "선수과목: ECO2001, ECO2003(또는 STS2005 또는 STS2006)"
    )
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "and",
        "children": [
            {"type": "course", "code": "ECO2001"},
            {"type": "or", "children": [
                {"type": "course", "code": "ECO2003"},
                {"type": "course", "code": "STS2005"},
                {"type": "course", "code": "STS2006"},
            ]},
        ],
    }
