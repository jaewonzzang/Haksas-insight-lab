"""카드 A 오케스트레이션: 추천 과목 (전공/교양 2단).

흐름:
1) 후보 풀 = dept_normalizer로 학생 학과의 합집합 → db/queries/course_queries
2) engines/recommender 점수 계산
3) prereq_eval로 충족도 평가 → 강추/고려/유보 등급
4) llm/translator로 1줄 사유 통역
5) schemas/cards.CardA 응답으로 직렬화
"""

# TODO: build(student_input) -> CardA
