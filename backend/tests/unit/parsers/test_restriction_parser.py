"""restriction_parser 단위 테스트."""

from app.parsers.restriction_parser import parse_restrictions
from app.schemas import RestrictionRow


def test_no_restriction():
    """None 입력 → ([], []).

    입력: None
    기대: ([], [])
    """
    assert parse_restrictions('C001', None) == ([], [])


def test_allowed():
    """'(가능)' → allowed.

    입력: '인공지능학과(가능)'
    기대: 1건, target_dept='인공지능학과', status='allowed'
    """
    restrictions, warnings = parse_restrictions('C001', '인공지능학과(가능)')
    assert restrictions == [
        RestrictionRow(
            course_id='C001',
            target_dept='인공지능학과',
            status='allowed',
            raw_text='인공지능학과(가능)',
        )
    ]
    assert warnings == []


def test_forbidden():
    """'(불가능)' → forbidden.

    입력: '컴퓨터공학과(불가능)'
    기대: 1건, status='forbidden'
    """
    restrictions, warnings = parse_restrictions('C001', '컴퓨터공학과(불가능)')
    assert len(restrictions) == 1
    assert restrictions[0].course_id == 'C001'
    assert restrictions[0].target_dept == '컴퓨터공학과'
    assert restrictions[0].status == 'forbidden'
    assert restrictions[0].raw_text == '컴퓨터공학과(불가능)'
    assert warnings == []


def test_major_only_allowed():
    """'(1전공 가능)' → major_only_allowed.

    입력: '인공지능학과(1전공 가능)'
    기대: 1건, status='major_only_allowed'
    """
    restrictions, warnings = parse_restrictions('C001', '인공지능학과(1전공 가능)')
    assert len(restrictions) == 1
    assert restrictions[0].target_dept == '인공지능학과'
    assert restrictions[0].status == 'major_only_allowed'
    assert restrictions[0].raw_text == '인공지능학과(1전공 가능)'
    assert warnings == []


def test_major_only_forbidden():
    """'(1전공 불가능)' → major_only_forbidden.

    입력: '인공지능학과(1전공 불가능)'
    기대: 1건, status='major_only_forbidden'
    """
    restrictions, warnings = parse_restrictions('C001', '인공지능학과(1전공 불가능)')
    assert len(restrictions) == 1
    assert restrictions[0].target_dept == '인공지능학과'
    assert restrictions[0].status == 'major_only_forbidden'
    assert restrictions[0].raw_text == '인공지능학과(1전공 불가능)'
    assert warnings == []


def test_multiple_tokens_comma():
    """콤마 분리 다중 토큰.

    입력: '인공지능학과(가능),컴퓨터공학과(가능)'
    기대: 2건
    """
    restrictions, warnings = parse_restrictions(
        'C001', '인공지능학과(가능),컴퓨터공학과(가능)'
    )
    assert len(restrictions) == 2
    assert restrictions[0].target_dept == '인공지능학과'
    assert restrictions[0].status == 'allowed'
    assert restrictions[1].target_dept == '컴퓨터공학과'
    assert restrictions[1].status == 'allowed'
    assert warnings == []


def test_dedupe_duplicate():
    """동일 토큰 중복 → 1건 + info warning (Q10).

    입력: '인공지능학과(1전공 가능),인공지능학과(1전공 가능)'
    기대: restrictions 1건 (dedupe), warnings 1건 severity='info'
    """
    restrictions, warnings = parse_restrictions(
        'C001', '인공지능학과(1전공 가능),인공지능학과(1전공 가능)'
    )
    assert len(restrictions) == 1
    assert restrictions[0].target_dept == '인공지능학과'
    assert restrictions[0].status == 'major_only_allowed'
    assert len(warnings) == 1
    assert warnings[0].course_id == 'C001'
    assert warnings[0].field == 'restrictions'
    assert warnings[0].severity == 'info'
    assert 'Duplicate' in warnings[0].issue


def test_unknown_suffix_warning():
    """4패턴 외 suffix → 매칭 실패 warning.

    입력: '인공지능학과(허용)'
    기대: ([], warnings 1건 severity='warning')
    """
    restrictions, warnings = parse_restrictions('C001', '인공지능학과(허용)')
    assert restrictions == []
    assert len(warnings) == 1
    assert warnings[0].course_id == 'C001'
    assert warnings[0].field == 'restrictions'
    assert warnings[0].severity == 'warning'
    assert 'Unknown suffix' in warnings[0].issue
