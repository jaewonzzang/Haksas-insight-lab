"""POST /analyze — 학생 입력 1회 → 카드 A/C/D 통합 dashboard 응답.

핸들러는 schemas/input 검증 → cards/ 오케스트레이터 호출 → cards 응답 반환만 한다.
엔진/LLM/DB를 직접 import 하지 않는다.
"""

from fastapi import APIRouter

router = APIRouter(tags=["analyze"])

# TODO: POST /analyze 엔드포인트 정의
