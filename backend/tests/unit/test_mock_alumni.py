"""MockAlumniSource 단위 테스트."""

import json

from app.adapters.alumni_types import AlumniRecord
from app.adapters.mock_alumni import MockAlumniSource


def _write_sample(path):
    path.write_text(
        json.dumps(
            [
                {"alumni_id": "a1", "department": "아트&테크놀로지"},
                {
                    "alumni_id": "a2",
                    "department": "경영학과",
                    "career": {"type": "job", "label": "IT 취업"},
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_all_returns_alumni_records(tmp_path):
    p = tmp_path / "alumni.json"
    _write_sample(p)
    src = MockAlumniSource(p)
    recs = src.all()
    assert len(recs) == 2
    assert all(isinstance(r, AlumniRecord) for r in recs)


def test_list_by_department_filters(tmp_path):
    p = tmp_path / "alumni.json"
    _write_sample(p)
    src = MockAlumniSource(p)
    out = src.list_by_department("아트&테크놀로지")
    assert [r.alumni_id for r in out] == ["a1"]


def test_empty_file_yields_empty(tmp_path):
    p = tmp_path / "alumni.json"
    p.write_text("[]", encoding="utf-8")
    assert MockAlumniSource(p).all() == []
