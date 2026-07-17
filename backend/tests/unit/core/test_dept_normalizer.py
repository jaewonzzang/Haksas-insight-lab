"""dept_normalizer — 표기 별칭 + 학부 → 학과 합집합 (산출·대조 시점에만 적용)."""

from app.core.dept_normalizer import DEPT_ALIASES, canonical, candidate_departments


def test_union_for_mapped_faculty():
    result = candidate_departments("지식융합미디어학부")
    assert result == [
        "지식융합미디어대학",
        "미디어&엔터테인먼트학과",
        "아트&테크놀로지학과",
        "신문방송학과",
    ]


def test_passthrough_for_unmapped():
    assert candidate_departments("컴퓨터공학과") == ["컴퓨터공학과"]


def test_returns_copy():
    a = candidate_departments("지식융합미디어학부")
    a.append("오염")
    assert "오염" not in candidate_departments("지식융합미디어학부")


def test_canonical_maps_major_spelling_to_department():
    """수강내역은 "X전공", courses.db 는 "X학과" — 같은 학과로 봐야 한다."""
    assert canonical("컴퓨터공학전공") == "컴퓨터공학과"
    assert canonical("아트&테크놀로지전공") == "아트&테크놀로지학과"


def test_canonical_passthrough_for_unknown():
    assert canonical("컴퓨터공학과") == "컴퓨터공학과"
    assert canonical("듣도보도못한학과") == "듣도보도못한학과"


def test_canonical_is_idempotent():
    """정규형을 다시 정규화해도 그대로 — 양쪽 정규화 후 비교가 성립하려면 필수."""
    for target in DEPT_ALIASES.values():
        assert canonical(target) == target


def test_aliases_do_not_merge_distinct_departments():
    """서로 다른 원문이 한 정규형으로 뭉치면 코호트가 오염된다.

    특히 계열/학부(사회과학부·인문학부)는 여러 학과를 아우르므로 별칭 금지 — A16.
    """
    for faculty in ("사회과학부", "인문학부", "영문학부", "지식융합미디어학부"):
        assert canonical(faculty) == faculty


def test_candidate_departments_normalizes_spelling():
    assert candidate_departments("컴퓨터공학전공") == ["컴퓨터공학과"]
