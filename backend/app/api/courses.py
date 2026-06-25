"""디버그/내부용 과목 조회 라우트. 외부 노출 X."""

from fastapi import APIRouter

router = APIRouter(prefix="/courses", tags=["debug"])

# TODO: 디버그용 과목 조회 엔드포인트
