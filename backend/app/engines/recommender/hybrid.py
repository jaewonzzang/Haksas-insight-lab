"""하이브리드 점수 결합: content_based + collaborative.

순서: hybrid(여기) → prereq_filter (감산) → restriction_filter (차단).
"""

# TODO: combine(content_scores, collab_scores, weights) -> dict[course_id, float]
