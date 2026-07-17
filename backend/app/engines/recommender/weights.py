"""카드 A 추천도 가중치·감산·컷오프 (전문가 prior).

⚠️ 잠정 수치 — 실데이터(졸업생 실제 수강 = 튜닝 정답) 확보 후 재조정. A5.
튜닝은 이 파일만 수정. 키 순서 = factors[] 표시 순서.
합은 1.0이 아니어도 된다 — scoring 이 "있는 요인"만으로 재정규화하므로 비율만 유효.
스펙: docs/superpowers/specs/2026-06-30-card-a-scoring-weights-design.md
"""

FACTOR_WEIGHTS: dict[str, float] = {
    "코호트 선호도": 0.25,
    "콘텐츠 유사도": 0.22,
    "사용자 선호 매칭": 0.15,
    "학년 적합도": 0.08,
}

PREREQ_PENALTY_MAX: int = 40

GRADE_CUTOFFS: dict[str, int] = {"강추": 80, "고려": 60}
