"""get_alumni_source 스위치 단위 테스트."""

from app import config
from app.adapters.mock_alumni import MockAlumniSource
from app.api.deps import get_alumni_source


def test_get_alumni_source_defaults_to_mock(tmp_path, monkeypatch):
    p = tmp_path / "alumni.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(config, "ALUMNI_SOURCE", "mock")
    monkeypatch.setattr(config, "ALUMNI_MOCK_PATH", p)
    src = get_alumni_source()
    assert isinstance(src, MockAlumniSource)
    assert src.all() == []
