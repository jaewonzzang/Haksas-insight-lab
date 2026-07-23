"""강의계획서 PDF 조회: course_id → 로컬 PDF 경로/URL (파일 실재 시에만).

배포 데모엔 PDF 원본(629MB)을 싣지 않는다 — 파일이 없으면 syllabus_url=None 으로
프론트가 링크를 숨긴다 (로컬 전용 기능, 우아한 강등).
"""

import sqlite3
from pathlib import Path
from typing import Sequence

from app import config
from app.db.queries import course_queries

SYLLABI_DIR = config.RAW_DIR / "syllabi" / "extracted"


def pdf_path(con: sqlite3.Connection, course_id: str) -> Path | None:
    """실재하는 PDF 절대 경로. 계획서 미보유·파일 없음이면 None."""
    row = course_queries.syllabus_attrs(con, [course_id]).get(course_id)
    if row is None or not row["source_file"]:
        return None
    path = SYLLABI_DIR / row["source_file"]
    return path if path.is_file() else None


def urls_for(con: sqlite3.Connection, course_ids: Sequence[str]) -> dict[str, str]:
    """추천 표시용 — 파일이 실재하는 과목만 /syllabus/{course_id} URL."""
    out: dict[str, str] = {}
    for cid, row in course_queries.syllabus_attrs(con, course_ids).items():
        if row["source_file"] and (SYLLABI_DIR / row["source_file"]).is_file():
            out[cid] = f"/syllabus/{cid}"
    return out
