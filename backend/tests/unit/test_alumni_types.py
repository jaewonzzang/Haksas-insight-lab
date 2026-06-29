"""졸업생 캐노니컬 프레임 단위 테스트."""

import pytest
from pydantic import ValidationError

from app.adapters.alumni_types import AlumniRecord, Career, Enrollment, Major


def test_core_only_record_valid():
    """코어(alumni_id+department)만으로 생성 가능, 나머지는 빈 기본값."""
    rec = AlumniRecord(alumni_id="a1", department="아트&테크놀로지")
    assert rec.majors == []
    assert rec.enrollment == []
    assert rec.career is None


def test_full_record_parses_nested():
    """dict 입력이 중첩 모델로 파싱된다."""
    rec = AlumniRecord(
        alumni_id="a2",
        department="아트&테크놀로지",
        majors=[{"label": "컴퓨터공학", "role": "double", "credits": 42.0}],
        enrollment=[{"course_id": "CSE3013", "year_taken": 3, "term_taken": 1}],
        career={"type": "grad", "label": "국내 대학원 (CS)"},
    )
    assert rec.majors[0].label == "컴퓨터공학"
    assert rec.enrollment[0].year_taken == 3
    assert rec.career.type == "grad"


def test_optional_fields_default_none():
    """하위 모델의 비코어 필드는 None 허용."""
    m = Major(label="경영학")
    assert m.role is None and m.credits is None
    e = Enrollment(course_id="MGT1001")
    assert e.year_taken is None and e.term_taken is None


def test_missing_core_raises():
    """department 누락은 검증 실패."""
    with pytest.raises(ValidationError):
        AlumniRecord(alumni_id="a3")


def test_invalid_role_rejected():
    """role enum 밖의 값은 거부."""
    with pytest.raises(ValidationError):
        Major(label="X", role="quad")
