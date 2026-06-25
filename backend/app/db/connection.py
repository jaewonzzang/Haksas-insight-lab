"""sqlite3 커넥션 팩토리.

- raw sqlite3 사용 (ORM 없음).
- row_factory = sqlite3.Row 권장 (dict-like 접근).
- 컨텍스트 매니저 또는 FastAPI Depends로 주입.
"""

# TODO: get_connection() -> sqlite3.Connection
