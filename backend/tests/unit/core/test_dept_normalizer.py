"""dept_normalizer — 학부 → 학과 합집합 (추천 풀 산출 시점에만 적용)."""

from app.core.dept_normalizer import candidate_departments


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
