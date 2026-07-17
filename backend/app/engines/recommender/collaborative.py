"""협업 signal: 졸업생 이수 이력 기반 코호트 선호도 (0~100).

user-based — 학생 이수 집합과의 Jaccard 유사도로 각 졸업생을 가중,
후보 과목의 가중 수강 빈도를 정규화한다. 학과 필터는 두지 않는다
(유사도 가중이 코호트 신호를 대신하며, mock 학과명 표기 차이에 안전).

유사도는 **현행 교과과정 과목만** 센다(curriculum_ids). 폐지 과목은 학생 이수
목록에 있을 수 없어 교집합엔 0을 기여하고 합집합만 키운다 → 옛 과목을 많이 들은
졸업생일수록 자기 표가 깎인다. 실측 2026-07-17: 20학번 -5.9% · 21학번 -4.3% ·
22학번 -3.1% · 23학번 -2.3% · 24학번 이후 0%. 하필 카드 D 코호트(이력 완결자)가
20·21학번이라 가장 쓸모 있는 표본이 가장 손해였다.
"""

from typing import Iterable, Sequence

from app.adapters.alumni_types import AlumniRecord


def score(
    taken: set[str],
    candidate_ids: Sequence[str],
    alumni: Iterable[AlumniRecord],
    curriculum_ids: set[str],
) -> dict[str, float]:
    weighted = {cid: 0.0 for cid in candidate_ids}
    total = 0.0
    taken_now = taken & curriculum_ids
    for record in alumni:
        courses = {e.course_id for e in record.enrollment} & curriculum_ids
        if not courses:
            continue
        union = taken_now | courses
        weight = len(taken_now & courses) / len(union) if union else 0.0
        if weight == 0.0:
            continue
        total += weight
        for cid in candidate_ids:
            if cid in courses:
                weighted[cid] += weight
    if total == 0.0:
        return {}
    return {cid: round(w / total * 100, 1) for cid, w in weighted.items()}
