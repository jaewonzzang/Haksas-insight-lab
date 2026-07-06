"""alias_resolver — 옛 코드/과목명 → 신 과목 단방향 확장."""

from app.core.alias_resolver import expand_taken

ALIASES = [
    ("CS101", "컴퓨터입문", "CSE1010"),
    (None, "구프로그래밍", "CSE1020"),
    ("MAT200", None, "MAT2001"),
]


def test_expand_by_old_id():
    assert expand_taken({"CS101"}, ALIASES) == {"CS101", "CSE1010"}


def test_expand_by_old_name():
    assert expand_taken({"구프로그래밍"}, ALIASES) == {"구프로그래밍", "CSE1020"}


def test_no_match_returns_copy():
    taken = {"CSE9999"}
    result = expand_taken(taken, ALIASES)
    assert result == {"CSE9999"}
    assert result is not taken  # 원본 비변조


def test_multiple_matches():
    assert expand_taken({"CS101", "MAT200"}, ALIASES) == {
        "CS101", "MAT200", "CSE1010", "MAT2001",
    }
