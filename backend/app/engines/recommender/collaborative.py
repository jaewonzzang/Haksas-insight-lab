"""협업필터링: 유사 학생 코호트의 이수 패턴 → 추천 신호.

주의: 어떤 필터(prereq/restriction)도 이 단계 이전에 적용하면 코호트 신호가 망가진다.
"""

# TODO: score(student, candidates) -> dict[course_id, float]
