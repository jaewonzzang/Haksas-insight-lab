"""카드 A/C/D 응답 Pydantic 모델 + 통합 dashboard 응답.

진실원: frontend/src/types/api.ts 의 확장 계약을 미러한다 (2026-07-06 확정).
변경 시 types/api.ts 와 함께 갱신 (수동 동기화 — OPEN_QUESTIONS A12).
"""

from typing import Literal

from pydantic import BaseModel, Field

RecommendationGrade = Literal["강추", "고려", "유보"]
CourseKind = Literal["major", "common", "free"]  # 전공 / 공통선택 / 자유선택
FactorKind = Literal["pos", "neg", "mid", "na"]  # why-panel 기여도 색
CareerType = Literal["job", "grad", "other"]


class RecommendationFactor(BaseModel):
    label: str
    weight_percent: float = Field(..., ge=0, le=100, description="막대 폭 0~100")
    contribution: str = Field(..., description='"+26" / "−18" / "N/A"')
    kind: FactorKind


class RecommendedCourse(BaseModel):
    course_id: str
    course_name: str
    credit: float | None
    grade: RecommendationGrade
    score_percent: int = Field(..., ge=0, le=100, description="추천도 %")
    reason_short: str = Field(..., description="LLM 통역 1줄 사유")
    kind: CourseKind
    kind_label: str = Field(..., description='모달 구분 표기, 예: "전공선택" / "교양"')
    area_label: str | None = None
    factors: list[RecommendationFactor] = Field(..., description="why-panel 기여도 분해")
    why_summary: str = Field(..., description="why-panel 한 줄 요약")


class CardA(BaseModel):
    """추천 과목 (전공/교양 2단). candidates = '과목 더 보기' 모달 전체 목록."""

    major: list[RecommendedCourse]
    general: list[RecommendedCourse]
    candidates: list[RecommendedCourse]


class PathwayCredits(BaseModel):
    major1: float | None
    major2: float | None
    major3: float | None


class PathwayEntry(BaseModel):
    id: str
    label: str
    tag: str | None = None
    count: int
    share_percent: float
    bar_percent: float = Field(..., description="막대 폭 (최다 대비 상대값)")
    detail_label: str
    credits: PathwayCredits
    dim: bool = False


class CardC(BaseModel):
    """다전공 경로 분포 + 추가 이수 학점."""

    cohort_label: str
    entries: list[PathwayEntry]
    baseline_note: str = Field(..., description="학칙 발췌")


class CareerEntry(BaseModel):
    cluster_label: str
    type: CareerType
    count: int
    share_percent: float


class CareerSubChip(BaseModel):
    label: str
    n: int


class CardD(BaseModel):
    """유사 졸업생 진로 분포 + 패턴 요약."""

    similar_label: str
    sample_size: int
    entries: list[CareerEntry]
    sub_title: str
    sub_chips: list[CareerSubChip]
    pattern_summary: str = Field(..., description="LLM 1단락 통역")


class SimilarityFactor(BaseModel):
    label: str
    percent: float


class CommonCourse(BaseModel):
    name: str
    n: int


class CareerPattern(BaseModel):
    label: str
    type: CareerType
    text: str


class ClusterEvidence(BaseModel):
    """유사 판정 근거 (cluster 패널)."""

    factors: list[SimilarityFactor]
    common_courses: list[CommonCourse]
    career_patterns: list[CareerPattern]
    summary: str


class StudentProfile(BaseModel):
    name: str
    department: str
    year: str
    analysis_date: str
    report_semester: str = Field(..., description='헤더 subtitle, 예: "2026-1학기"')
    next_semester: str = Field(..., description='추천 대상 학기, 예: "2026-2"')


class KpiStrip(BaseModel):
    earned_credits: float
    gpa: float | None
    gpa_scale: float
    similar_alumni_n: int


class DashboardResponse(BaseModel):
    """POST /analyze 통합 응답."""

    profile: StudentProfile
    kpi: KpiStrip
    card_a: CardA
    card_c: CardC
    card_d: CardD
    cluster: ClusterEvidence
