"""사용자 선호 매칭 signal: 강의계획서 속성(팀플·참여도) ↔ 폼 선호 (0~100).

⚠️ 매칭 티어는 잠정 prior — 실데이터/피드백 후 조정. S/U 선호는 재료 부재로 미사용.
강의계획서 없는 과목은 dict에서 제외 → 해당 과목 요인 N/A (부분 커버리지).
"""

from typing import Mapping


def _team(team_project: str) -> float:
    return {"required": 100.0, "optional": 50.0}.get(team_project, 0.0)


def _low_attendance(ratio: float) -> float:
    if ratio <= 0.10:
        return 100.0
    if ratio <= 0.20:
        return 50.0
    return 0.0


def score(
    prefer_team_project: bool,
    prefer_low_attendance: bool,
    attrs_by_id: Mapping[str, Mapping],
) -> dict[str, float]:
    if not (prefer_team_project or prefer_low_attendance):
        return {}
    out: dict[str, float] = {}
    for cid, a in attrs_by_id.items():
        parts: list[float] = []
        if prefer_team_project:
            parts.append(_team(a["team_project"]))
        if prefer_low_attendance:
            parts.append(_low_attendance(a["attendance_ratio"]))
        out[cid] = round(sum(parts) / len(parts), 1)
    return out
