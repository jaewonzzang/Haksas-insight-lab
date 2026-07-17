"""career/track — 대학원 연계 과목(G코드) 이수 관측."""

from app.adapters.alumni_types import AlumniRecord, Enrollment
from app.engines.career import track


def _alum(aid, courses):
    return AlumniRecord(
        alumni_id=aid, department="컴퓨터공학과",
        enrollment=[Enrollment(course_id=c) for c in courses],
    )


def test_grad_course_pattern():
    """학과코드 + G + 숫자3. 학부 과목이 걸리면 안 된다."""
    rec = _alum("a", ["CSEG483", "CBEG011", "CSE4085", "AAT2002", "COR1003"])
    assert track.grad_courses(rec) == ["CSEG483", "CBEG011"]


def test_split_two_groups():
    records = [_alum("a", ["CSEG483"]), _alum("b", ["CSE1010"]), _alum("c", ["MGTG505"])]
    groups = track.split(records)
    assert [(g.label, g.count, g.career_type) for g in groups] == [
        ("대학원 연계 과목 이수", 2, "grad"),
        ("미이수", 1, "other"),
    ]


def test_split_omits_empty_side():
    """0명 항목을 카드에 내보내지 않는다."""
    assert [g.label for g in track.split([_alum("a", ["CSEG483"])])] == ["대학원 연계 과목 이수"]
    assert [g.label for g in track.split([_alum("a", ["CSE1010"])])] == ["미이수"]
    assert track.split([]) == []


def test_top_grad_courses_is_deterministic():
    """동수는 코드 사전순."""
    records = [_alum("a", ["CSEG483", "MGTG505"]), _alum("b", ["MGTG505"]), _alum("c", ["AATG501"])]
    assert track.top_grad_courses(records) == [("MGTG505", 2), ("AATG501", 1), ("CSEG483", 1)]
