"""카드 A 풀 제외 판정: 대학원 G코드·캡스톤 (2026-07-12 사용자 승인)."""

from app.cards.card_a import _excluded_from_pool


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
