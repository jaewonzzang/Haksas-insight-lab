"""협업 signal: 졸업생 이수 이력 기반 코호트 선호도 (0~100).

user-based — 학생 이수 집합과의 Jaccard 유사도로 각 졸업생을 가중,
후보 과목의 가중 수강 빈도를 정규화한다. 학과 필터는 두지 않는다
(유사도 가중이 코호트 신호를 대신하며, mock 학과명 표기 차이에 안전).
"""

from typing import Iterable, Sequence

from app.adapters.alumni_types import AlumniRecord


def score(
    taken: set[str],
    candidate_ids: Sequence[str],
    alumni: Iterable[AlumniRecord],
) -> dict[str, float]:
    weighted = {cid: 0.0 for cid in candidate_ids}
    total = 0.0
    for record in alumni:
        courses = {e.course_id for e in record.enrollment}
        if not courses:
            continue
        union = taken | courses
        weight = len(taken & courses) / len(union) if union else 0.0
        if weight == 0.0:
            continue
        total += weight
        for cid in candidate_ids:
            if cid in courses:
                weighted[cid] += weight
    if total == 0.0:
        return {}
    return {cid: round(w / total * 100, 1) for cid, w in weighted.items()}
