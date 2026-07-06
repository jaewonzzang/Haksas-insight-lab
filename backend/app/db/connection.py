"""sqlite3 커넥션 팩토리.

- raw sqlite3 사용 (ORM 없음).
- row_factory = sqlite3.Row 권장 (dict-like 접근).
- 컨텍스트 매니저 또는 FastAPI Depends로 주입.
"""

import sqlite3
from pathlib import Path

from app import config


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """s_compass_courses.db 읽기용 커넥션 (row_factory=Row, FK ON)."""
    con = sqlite3.connect(db_path or config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con
