"""llm 테스트 공용 카드 픽스처."""

from app.schemas.cards import CardA, RecommendationFactor, RecommendedCourse


def make_course(course_id: str = "AIE1001", reason: str = "코호트 선호도 신호가 가장 강한 과목") -> RecommendedCourse:
    return RecommendedCourse(
        course_id=course_id,
        course_name="인공지능개론",
        credit=3.0,
        grade="강추",
        score_percent=82,
        reason_short=reason,
        kind="major",
        kind_label="전공",
        area_label=None,
        factors=[
            RecommendationFactor(label="코호트 선호도", weight_percent=25.0, contribution="+21", kind="pos"),
            RecommendationFactor(label="콘텐츠 유사도", weight_percent=22.0, contribution="+12", kind="pos"),
        ],
        why_summary="강추 · 추천도 82%",
    )


def make_card_a() -> CardA:
    major = [make_course(f"AIE100{i}") for i in range(1, 5)]
    general = [make_course(f"GEN200{i}") for i in range(1, 5)]
    return CardA(major=major, general=general, candidates=major + general)
