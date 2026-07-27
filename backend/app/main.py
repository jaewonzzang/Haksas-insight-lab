"""FastAPI 진입점.

api/* 의 라우터 등록만 한다. 비즈니스 로직은 cards/ 오케스트레이터에 위임.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import analyze, courses, health, syllabus

app = FastAPI(title="Saint+", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",  # Vite dev
        *([config.CORS_EXTRA_ORIGIN] if config.CORS_EXTRA_ORIGIN else []),  # 배포 프론트
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(syllabus.router)  # PDF 없는 배포 데모에선 404 — 프론트가 링크 자체를 숨김
if config.EXPOSE_DEBUG_ROUTES:  # 디버그 라우트 — 데모 배포에서 비노출 (외부 노출 X 규칙)
    app.include_router(courses.router)
