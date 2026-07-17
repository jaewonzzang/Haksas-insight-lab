"""RealAlumniSource + 수강내역 → AlumniRecord 빌드 매핑 단위 테스트."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_alumni_from_enrollment import build  # noqa: E402

from app.adapters.real_alumni import RealAlumniSource  # noqa: E402

# read_rows 산출 형태: (year, term, course_id, student, dept, (m1, m2, m3))
_ROWS = [
    (2020, "1학기", "COR1003", "20학번-1", "지식융합미디어학부", ("지식융합미디어학부", "", None)),
    (2020, "2학기", "CSE2001", "20학번-1", "지식융합미디어학부", ("지식융합미디어학부", "", None)),
    (2023, "1학기", "CSE4011", "20학번-1", "아트&테크놀로지학과", ("아트&테크놀로지학과", "컴퓨터공학", None)),
    (2021, "하계", "COR1009", "21학번-2", "경영학과", ("경영학과", None, None)),
]


def test_build_maps_student_to_record():
    recs = build(_ROWS)
    assert [r.alumni_id for r in recs] == ["20학번-1", "21학번-2"]
    assert [e.course_id for e in recs[0].enrollment] == ["COR1003", "CSE2001", "CSE4011"]


def test_build_takes_latest_department_and_majors():
    """소속/전공이 기간 중 바뀌면 최신 학기 값 채택 (OPEN_QUESTIONS A15)."""
    rec = build(_ROWS)[0]
    assert rec.department == "아트&테크놀로지학과"
    assert [(m.label, m.role) for m in rec.majors] == [
        ("아트&테크놀로지학과", "primary"),
        ("컴퓨터공학", "double"),
    ]


def test_build_seasonal_term_is_none():
    """계절학기는 1/2 학기가 아니므로 term_taken=None, 수강 자체는 보존."""
    rec = build(_ROWS)[1]
    assert [(e.course_id, e.year_taken, e.term_taken) for e in rec.enrollment] == [
        ("COR1009", 2021, None)
    ]


def test_build_career_is_always_none():
    """원본에 진로 컬럼 없음 (OPEN_QUESTIONS A14)."""
    assert all(r.career is None for r in build(_ROWS))


def test_build_marks_history_complete():
    """이력 완결 = 정규학기 7개+ 등록 & 마지막 등록이 데이터 창 끝이 아님 (A17).

    창의 끝은 입력에서 관측한다 — 아래에선 (2026, 1).
    """
    def rows(sid, spans):
        return [(y, t, f"C{i:03}", sid, "화학과", ("화학", None, None))
                for i, (y, t) in enumerate(spans)]

    eight = [(y, t) for y in (2020, 2021, 2022, 2023) for t in ("1학기", "2학기")]
    recs = {
        r.alumni_id: r
        for r in build([
            *rows("20학번-1", eight),          # 8학기, 2023 끝 → 완결
            *rows("22학번-2", eight[:6]),      # 6학기 → 미달
            *rows("23학번-3", [*eight, (2026, "1학기")]),  # 9학기지만 현재 등록 중
        ])
    }
    assert recs["20학번-1"].history_complete is True
    assert recs["22학번-2"].history_complete is False
    assert recs["23학번-3"].history_complete is False


def test_build_seasonal_only_is_not_complete():
    """계절학기만 있으면 정규학기 0 → 완결 아님."""
    assert build(_ROWS)[1].history_complete is False


def test_real_source_loads_and_filters(tmp_path):
    p = tmp_path / "alumni.json"
    p.write_text(
        json.dumps([r.model_dump() for r in build(_ROWS)], ensure_ascii=False),
        encoding="utf-8",
    )
    src = RealAlumniSource(p)
    assert len(src.all()) == 2
    assert [r.alumni_id for r in src.list_by_department("경영학과")] == ["21학번-2"]


def test_real_source_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_alumni_from_enrollment"):
        RealAlumniSource(tmp_path / "없음.json")
