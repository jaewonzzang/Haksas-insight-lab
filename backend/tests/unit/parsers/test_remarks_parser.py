"""remarks_parser 단위 테스트."""

from app.parsers.remarks_parser import parse_linked_majors


def test_no_remarks():
    """None 입력 → (None, []).

    입력: None
    기대: (None, [])
    """
    assert parse_linked_majors('COURSE001', None) == (None, [])


def test_single_linked_major():
    """단일 연계전공 키워드.

    입력: '스타트업연계전공 가능'
    기대 JSON: '["스타트업연계전공"]'
    """
    assert parse_linked_majors('COURSE001', '스타트업연계전공 가능') == (
        '["스타트업연계전공"]',
        [],
    )


def test_two_linked_majors():
    """두 개 연계전공 키워드 추출.

    입력: '스타트업연계전공 가능, 가상융합연계전공 가능'
    기대 JSON: '["스타트업연계전공","가상융합연계전공"]'
    """
    assert parse_linked_majors(
        'COURSE001',
        '스타트업연계전공 가능, 가상융합연계전공 가능',
    ) == (
        '["스타트업연계전공","가상융합연계전공"]',
        [],
    )


def test_no_keyword():
    """연계전공 키워드 없음.

    입력: '특이사항 없음'
    기대: (None, [])
    """
    assert parse_linked_majors('COURSE001', '특이사항 없음') == (None, [])
