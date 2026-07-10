"""FastAPI 진입점.

api/* 의 라우터 등록만 한다. 비즈니스 로직은 cards/ 오케스트레이터에 위임.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, courses, health

app = FastAPI(title="S-Compass", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(courses.router)
