"""수강학년·권장학년 원문 파싱 + 학년 적합도 점수.

- 수강학년(target_year_raw) = 신청 가능 학년 — 불일치 과목은 추천 풀에서 제외(표시 금지).
- 권장학년(recommended_year_raw) = 교수 설정 권장 — 학년 적합도 점수 요인.
(2026-07-13 사용자 확정. 원문 형태 DB 실측: 수강학년 "전학년"|"2,3,4학년"|None,
권장학년 "2-4학년"|"3학년" — 결측 없음.)
"""

import re

ALL_YEARS = frozenset({1, 2, 3, 4})


def parse_target_years(raw: str | None) -> set[int]:
    """수강 가능 학년 집합. '전학년'·None(제한 정보 없음)은 전 학년 허용."""
    if not raw or "전학년" in raw:
        return set(ALL_YEARS)
    return {int(n) for n in re.findall(r"\d", raw)} or set(ALL_YEARS)


def parse_recommended_years(raw: str | None) -> set[int]:
    """권장 학년 집합. "A-B학년" 범위형과 "N학년" 단일형 지원."""
    if not raw:
        return set(ALL_YEARS)
    m = re.match(r"\s*(\d)\s*-\s*(\d)", raw)
    if m:
        return set(range(int(m.group(1)), int(m.group(2)) + 1))
    return {int(n) for n in re.findall(r"\d", raw)} or set(ALL_YEARS)


def year_fit_score(student_year: int, recommended: set[int]) -> float:
    """권장학년 일치 100 / 한 학년 차이 50 / 그 외 0.

    ⚠️ 잠정 prior — 실데이터 확보 후 weights(A5)와 함께 재조정.
    """
    if student_year in recommended:
        return 100.0
    if any(abs(student_year - y) == 1 for y in recommended):
        return 50.0
    return 0.0
