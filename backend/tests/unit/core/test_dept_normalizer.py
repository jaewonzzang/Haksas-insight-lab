"""dept_normalizer — 표기 별칭 + 대학 → 학과 합집합 (산출·대조 시점에만 적용)."""

from app.core.dept_normalizer import (
    DEPT_ALIASES,
    DEPT_COLLEGES,
    FACULTY_COLLEGES,
    canonical,
    candidate_departments,
)


def test_union_for_mapped_faculty():
    result = candidate_departments("지식융합미디어학부")
    assert result == [
        "지식융합미디어대학",
        "신문방송학과",
        "미디어&엔터테인먼트학과",
        "아트&테크놀로지학과",
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


def test_faculty_spelling_resolves_to_college_not_a_department():
    """계열/학부 입학 표기는 특정 학과로 내리면 안 된다 — 대학까지만.

    실측: 이 표기로 기록된 1,185명 전원이 1~2학년(학과 선택 전).
    어간 규칙으로 밀면 "사회과학부"가 "사회학과"에 잘못 합쳐진다.
    """
    assert canonical("사회과학부") == "사회과학대학"
    assert canonical("인문학부") == "인문대학"
    assert canonical("지식융합미디어학부") == "지식융합미디어대학"


def test_undeclared_students_stay_out_of_department_cohorts():
    """학과 미선택자를 학과 코호트에 넣으면 다전공 분포가 오염된다 (의도된 배제)."""
    assert canonical("사회과학부") not in candidate_departments("사회학과")
    assert canonical("인문학부") not in candidate_departments("국어국문학과")


def test_college_expands_to_member_departments():
    assert candidate_departments("사회과학부") == [
        "사회과학대학", "정치외교학과", "사회학과", "심리학과",
    ]


def test_candidate_departments_normalizes_spelling():
    assert candidate_departments("컴퓨터공학전공") == ["컴퓨터공학과"]


def test_college_members_are_not_themselves_colleges():
    """학과가 대학 이름과 겹치면 candidate_departments 가 무한 확장된다."""
    members = {m for ms in DEPT_COLLEGES.values() for m in ms}
    assert members & set(DEPT_COLLEGES) == set()


def test_faculty_targets_are_known_colleges():
    assert set(FACULTY_COLLEGES.values()) <= set(DEPT_COLLEGES)
