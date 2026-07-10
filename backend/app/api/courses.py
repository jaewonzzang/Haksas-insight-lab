"""디버그/내부용 과목 조회 라우트. 외부 노출 X — db/queries 직접 사용 허용(디버그 예외)."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db
from app.db.queries import course_queries

router = APIRouter(prefix="/courses", tags=["debug"])


@router.get("/{course_id}")
def get_course(course_id: str, con: sqlite3.Connection = Depends(get_db)) -> dict:
    row = course_queries.get_course(con, course_id)
    if row is None:
        raise HTTPException(status_code=404, detail="course not found")
    return dict(row)
