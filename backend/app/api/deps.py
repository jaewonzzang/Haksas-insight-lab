"""FastAPI Depends 의존성 모음 (DB 커넥션, 어댑터 등)."""

import sqlite3
from collections.abc import Iterator
from functools import lru_cache

from app import config
from app.adapters.alumni_source import AlumniSource
from app.adapters.mock_alumni import MockAlumniSource
from app.db.connection import get_connection


def get_db() -> Iterator[sqlite3.Connection]:
    """요청 스코프 sqlite3 커넥션 (읽기 전용 사용)."""
    con = get_connection()
    try:
        yield con
    finally:
        con.close()


def _source(kind: str) -> AlumniSource:
    if kind == "real":
        from app.adapters.real_alumni import RealAlumniSource

        return RealAlumniSource(config.ALUMNI_REAL_PATH)
    return MockAlumniSource(config.ALUMNI_MOCK_PATH)


@lru_cache(maxsize=1)
def get_alumni_source() -> AlumniSource:
    """카드 A/C 코호트 = 이수 이력 공급자 (교체점).

    빌드 산출물이라 프로세스 수명 동안 불변 → 캐시(실데이터 14,942명 JSON 재파싱 방지).
    """
    return _source(config.ALUMNI_SOURCE)


@lru_cache(maxsize=1)
def get_career_alumni_source() -> AlumniSource:
    """카드 D 진로 클러스터 공급자 — 실데이터에 진로 컬럼이 없어 분리 (A14)."""
    return _source(config.CAREER_ALUMNI_SOURCE)
