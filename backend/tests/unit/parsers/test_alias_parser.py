"""alias_parser 단위 테스트."""

from app.parsers.alias_parser import parse_aliases
from app.schemas import AliasRow


def test_no_alias():
    """별칭 패턴 없으면 ([], []).

    입력: source_text='과목 일반 설명.'
    기대: ([], [])
    """
    assert parse_aliases('NEW001', '과목 일반 설명.') == ([], [])


def test_old_code_with_paren():
    """'(구) ANT2003' 매칭 → old_code.

    입력: '(구) ANT2003'
    기대: 1건, source_type='old_code', old_course_id='ANT2003'
    """
    aliases, warnings = parse_aliases('NEW001', '(구) ANT2003')
    assert aliases == [
        AliasRow(
            new_course_id='NEW001',
            old_course_id='ANT2003',
            old_course_name=None,
            source_type='old_code',
            condition_raw=None,
            raw_text='(구) ANT2003',
        )
    ]
    assert warnings == []


def test_old_code_without_open_paren():
    """'구) ANT2003' (변형) 매칭 → old_code.

    입력: '구) ANT2003'
    기대: 1건, source_type='old_code', old_course_id='ANT2003'
    """
    aliases, warnings = parse_aliases('NEW001', '구) ANT2003')
    assert len(aliases) == 1
    assert aliases[0].new_course_id == 'NEW001'
    assert aliases[0].old_course_id == 'ANT2003'
    assert aliases[0].source_type == 'old_code'
    assert aliases[0].condition_raw is None
    assert '구) ANT2003' in aliases[0].raw_text
    assert warnings == []


def test_replacement_single():
    """'대체과목: XYZ5678' 매칭 → replacement.

    입력: '대체과목: XYZ5678'
    기대: 1건, source_type='replacement', old_course_id='XYZ5678'
    """
    aliases, warnings = parse_aliases('NEW001', '대체과목: XYZ5678')
    assert len(aliases) == 1
    assert aliases[0].new_course_id == 'NEW001'
    assert aliases[0].old_course_id == 'XYZ5678'
    assert aliases[0].source_type == 'replacement'
    assert aliases[0].condition_raw is None
    assert warnings == []


def test_alias_with_condition():
    """학번 조건 추출 → condition_raw.

    입력: '(구) ANT2003 (2015-2018학번)'
    기대: 1건, source_type='old_code', condition_raw='2015-2018학번'
    """
    aliases, warnings = parse_aliases('NEW001', '(구) ANT2003 (2015-2018학번)')
    assert len(aliases) == 1
    assert aliases[0].source_type == 'old_code'
    assert aliases[0].old_course_id == 'ANT2003'
    assert aliases[0].condition_raw == '2015-2018학번'
    assert warnings == []
