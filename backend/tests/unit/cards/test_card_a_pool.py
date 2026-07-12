"""카드 A 풀 제외 판정: 대학원 G코드·캡스톤 (2026-07-12 사용자 승인)."""

from app.cards.card_a import _excluded_from_pool, _major_departments
from app.schemas.input import StudentInput


def test_grad_gcode_excluded():
    assert _excluded_from_pool("AATG800", "Art,Technology,and Social Impact(캡스톤디자인)")
    assert _excluded_from_pool("AIEG102", "패턴인식")
    assert _excluded_from_pool("CSEG001", "아무거나")


def test_capstone_excluded():
    assert _excluded_from_pool("AAT4002", "Advanced Web Development(캡스톤디자인)")


def test_normal_courses_kept():
    assert not _excluded_from_pool("ENG2009", "영미단편소설")  # 학과코드가 G로 끝나는 정상 과목
    assert not _excluded_from_pool("CSE3080", "자료구조")
    assert not _excluded_from_pool("AAT2003", "Intro to Digital Arts")


def test_major_departments_union_with_extra_majors():
    s = StudentInput(
        student_id="A",
        department="지식융합미디어학부",
        extra_majors=["컴퓨터공학과"],
        taken_course_ids=[],
        interest_career=None,
        consider_multimajor=True,
    )
    depts = _major_departments(s)
    assert "아트&테크놀로지학과" in depts      # 소속 학부 합집합
    assert "컴퓨터공학과" in depts             # 복수전공
    assert len(depts) == len(set(depts))       # 중복 없음


def test_major_departments_default_empty_extras():
    s = StudentInput(student_id="A", department="컴퓨터공학과")
    assert _major_departments(s) == ["컴퓨터공학과"]
