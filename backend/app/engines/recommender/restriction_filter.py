"""수강 제한 차단: forbidden / major_only_forbidden 만 제거.

allowed / major_only_allowed 는 차단하지 않는다 (ARCHITECTURE 확정, 정보성).
파이프라인 마지막 단계 — 점수 산출 이후 적용해 협업 신호를 보존한다.
"""

from typing import Iterable, Mapping

from app.engines.recommender.scoring import ScoredCandidate


def apply(
    scored: dict[str, ScoredCandidate],
    student_depts: set[str],
    is_first_major: bool,
    restrictions: Iterable[Mapping],
) -> dict[str, ScoredCandidate]:
    blocked: set[str] = set()
    for row in restrictions:
        if row["target_dept"] not in student_depts:
            continue
        if row["status"] == "forbidden":
            blocked.add(row["course_id"])
        elif row["status"] == "major_only_forbidden" and is_first_major:
            blocked.add(row["course_id"])
    return {cid: sc for cid, sc in scored.items() if cid not in blocked}
