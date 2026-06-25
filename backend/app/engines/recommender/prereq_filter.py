"""선수과목 충족 여부에 따른 점수 감산 (배제 아님).

- 엑셀 과목설명 선수 미이수: 강한 감산 (예: -50점, 수치는 OPEN_QUESTIONS 11)
- 강의계획서만 권장: 약한 감산 또는 표시만
"""

# TODO: apply(scores, student_taken) -> dict[course_id, float]
