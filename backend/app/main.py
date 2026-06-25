"""FastAPI 진입점.

api/* 의 라우터 등록만 한다. 비즈니스 로직은 cards/ 오케스트레이터에 위임.
"""

from fastapi import FastAPI

from app.api import analyze, courses, health

app = FastAPI(title="S-Compass", version="0.1.0")

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(courses.router)
