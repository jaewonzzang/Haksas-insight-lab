"""학과별 수강 제한 차단.

course_restrictions.status:
- forbidden, major_only_forbidden (학생이 1전공 아닐 때) → 후보에서 제외
- allowed, major_only_allowed → 통과
"""

# TODO: apply(scores, student_dept, is_first_major) -> dict[course_id, float]
