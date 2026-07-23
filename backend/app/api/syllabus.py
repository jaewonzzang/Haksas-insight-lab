"""GET /syllabus/{course_id} — 강의계획서 PDF 서빙 (로컬 파일 실재 시).

핸들러는 cards/syllabus 해석기만 호출한다. 파일이 없으면(배포 데모) 404.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_db
from app.cards import syllabus

router = APIRouter(tags=["syllabus"])


@router.get("/syllabus/{course_id}")
def get_syllabus(
    course_id: str, con: sqlite3.Connection = Depends(get_db)
) -> FileResponse:
    path = syllabus.pdf_path(con, course_id)
    if path is None:
        raise HTTPException(status_code=404, detail="강의계획서 없음")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
