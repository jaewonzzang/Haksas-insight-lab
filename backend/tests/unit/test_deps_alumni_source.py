"""get_alumni_source 스위치 단위 테스트."""

import json

import pytest

from app import config
from app.adapters.mock_alumni import MockAlumniSource
from app.adapters.real_alumni import RealAlumniSource
from app.api.deps import get_alumni_source, get_career_alumni_source


@pytest.fixture(autouse=True)
def _clear_cache():
    """lru_cache — 플래그를 바꾸는 테스트마다 비운다."""
    for f in (get_alumni_source, get_career_alumni_source):
        f.cache_clear()
    yield
    for f in (get_alumni_source, get_career_alumni_source):
        f.cache_clear()


def test_get_alumni_source_defaults_to_mock(tmp_path, monkeypatch):
    p = tmp_path / "alumni.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(config, "ALUMNI_SOURCE", "mock")
    monkeypatch.setattr(config, "ALUMNI_MOCK_PATH", p)
    src = get_alumni_source()
    assert isinstance(src, MockAlumniSource)
    assert src.all() == []


def test_get_alumni_source_real_flag_loads_real(tmp_path, monkeypatch):
    p = tmp_path / "alumni.json"
    p.write_text(
        json.dumps([{"alumni_id": "20학번-1", "department": "경영학과"}], ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ALUMNI_SOURCE", "real")
    monkeypatch.setattr(config, "ALUMNI_REAL_PATH", p)
    src = get_alumni_source()
    assert isinstance(src, RealAlumniSource)
    assert [r.alumni_id for r in src.all()] == ["20학번-1"]


def test_get_alumni_source_caches_instance(tmp_path, monkeypatch):
    p = tmp_path / "alumni.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(config, "ALUMNI_SOURCE", "mock")
    monkeypatch.setattr(config, "ALUMNI_MOCK_PATH", p)
    assert get_alumni_source() is get_alumni_source()


def test_career_source_is_independent_of_alumni_source(tmp_path, monkeypatch):
    """카드 D 는 실데이터에 진로가 없어 A/C 와 다른 공급자를 쓴다 (A14)."""
    mock_p, real_p = tmp_path / "mock.json", tmp_path / "real.json"
    mock_p.write_text(
        json.dumps([{"alumni_id": "m1", "department": "화학과"}], ensure_ascii=False),
        encoding="utf-8",
    )
    real_p.write_text(
        json.dumps([{"alumni_id": "r1", "department": "경영학과"}], ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ALUMNI_SOURCE", "real")
    monkeypatch.setattr(config, "CAREER_ALUMNI_SOURCE", "mock")
    monkeypatch.setattr(config, "ALUMNI_REAL_PATH", real_p)
    monkeypatch.setattr(config, "ALUMNI_MOCK_PATH", mock_p)
    assert [r.alumni_id for r in get_alumni_source().all()] == ["r1"]
    assert [r.alumni_id for r in get_career_alumni_source().all()] == ["m1"]
