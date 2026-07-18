"""카드 A 추천도 가중치·감산·컷오프.

가중치는 홀드아웃 실측으로 조정 (2026-07-18, A5 종결): 2차 수령분 이력에서
마지막 정규학기를 숨기고 실제 수강 적중률로 그리드 탐색 — 방법·수치는
docs/scoring_rationale.md, scripts/evaluate_recommender.py.
선호 매칭은 졸업생 이력에 튜닝 정답이 없어 prior 0.15 유지.
튜닝은 이 파일만 수정. 키 순서 = factors[] 표시 순서.
합은 1.0이 아니어도 된다 — scoring 이 "있는 요인"만으로 재정규화하므로 비율만 유효.
스펙: docs/superpowers/specs/2026-06-30-card-a-scoring-weights-design.md
"""

FACTOR_WEIGHTS: dict[str, float] = {
    "코호트 선호도": 0.35,
    "콘텐츠 유사도": 0.10,
    "사용자 선호 매칭": 0.15,
    "학년 적합도": 0.30,
}

PREREQ_PENALTY_MAX: int = 40

GRADE_CUTOFFS: dict[str, int] = {"강추": 80, "고려": 60}
