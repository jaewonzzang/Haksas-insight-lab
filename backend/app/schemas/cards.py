"""카드 A/C/D 응답 Pydantic 모델 + 통합 dashboard 응답.

프론트엔드 src/types/api.ts 는 이 정의와 동기화되어야 한다 (수동 또는 codegen).
실 필드는 UI 프로토타입 + 엔진 출력 합의 후 확정.
"""

from typing import Literal

from pydantic import BaseModel, Field

RecommendationGrade = Literal["강추", "고려", "유보"]


class RecommendedCourse(BaseModel):
    course_id: str
    course_name: str
    credit: float | None
    grade: RecommendationGrade
    score_percent: int = Field(..., ge=0, le=100, description="추천도 % (등급과 함께 표시)")
    reason_short: str = Field(..., description="LLM 통역 1줄 사유")


class CardA(BaseModel):
    """추천 과목 (전공/교양 2단). 각 4개 항목 기본."""

    major: list[RecommendedCourse]
    general: list[RecommendedCourse]


class PathwayEntry(BaseModel):
    label: str = Field(..., description="다전공 경로 라벨 (단일전공 유지 포함)")
    share_percent: float
    avg_extra_credits: float


class CardC(BaseModel):
    """다전공 경로 분포 + 추가 이수 학점."""

    entries: list[PathwayEntry]


class CareerEntry(BaseModel):
    cluster_label: str
    share_percent: float


class CardD(BaseModel):
    """유사 졸업생 진로 분포 + 패턴 요약."""

    sample_size: int
    pattern_summary: str = Field(..., description="LLM 1단락 통역")
    entries: list[CareerEntry]


class KpiStrip(BaseModel):
    earned_credits: float
    gpa: float | None
    similar_alumni_n: int


class DashboardResponse(BaseModel):
    """POST /analyze 통합 응답."""

    kpi: KpiStrip
    card_a: CardA
    card_c: CardC
    card_d: CardD
