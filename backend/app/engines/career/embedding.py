"""이수경로 임베딩. 졸업생/현 학생 모두 동일 공간에 투영.

표현 후보: (1) 과목 ID 시퀀스 → BoW/TF-IDF, (2) 과목 설명 임베딩 평균, (3) Sentence-BERT 한국어 문장화.
선택은 OPEN_QUESTIONS에 추가 후 결정.
"""

# TODO: embed(taken_courses: list[str]) -> np.ndarray
