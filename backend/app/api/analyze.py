"""POST /analyze — 학생 입력 1회 → 카드 A/C/D 통합 dashboard 응답.

핸들러는 schemas/input 검증 → cards/dashboard 오케스트레이터 호출 → 응답 반환만 한다.
엔진/LLM/DB를 직접 import 하지 않는다.
"""

import sqlite3

from fastapi import APIRouter, Depends

from app.adapters.alumni_source import AlumniSource
from app.api.deps import get_alumni_source, get_db
from app.cards import dashboard
from app.schemas.cards import DashboardResponse
from app.schemas.input import StudentInput

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=DashboardResponse)
def analyze(
    student: StudentInput,
    con: sqlite3.Connection = Depends(get_db),
    source: AlumniSource = Depends(get_alumni_source),
) -> DashboardResponse:
    return dashboard.build(student, con, source.all())
