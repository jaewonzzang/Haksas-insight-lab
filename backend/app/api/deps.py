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


@lru_cache(maxsize=1)
def get_alumni_source() -> AlumniSource:
    """설정 플래그에 따라 mock/real 졸업생 공급자를 반환 (교체점).

    빌드 산출물이라 프로세스 수명 동안 불변 → 캐시(실데이터 14,942명 JSON 재파싱 방지).
    """
    if config.ALUMNI_SOURCE == "real":
        from app.adapters.real_alumni import RealAlumniSource

        return RealAlumniSource(config.ALUMNI_REAL_PATH)
    return MockAlumniSource(config.ALUMNI_MOCK_PATH)
