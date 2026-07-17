"""이수 트랙 관측: 대학원 연계 과목(G코드) 이수 여부.

진로 데이터가 없다(A14). 진로를 **추론하지 않고** 재학 중 선택을 **관측**한다
— 등록학기 순번과 같은 원칙 (docs/enrollment_inference.md).

캡스톤은 쓰지 않는다: 학과 졸업요건이라 코호트 안에서 변별력이 0이다
(실측 2026-07-17 — 유사 코호트 30명 중 28명, 컴퓨터공학과 98%·전자공학과 93%).
G코드는 갈린다: 같은 코호트 30명 중 19명, 학과 내 20~75%.

한계: "대학원 과목을 들었다" ≠ "진학했다". 라벨을 진로로 부르면 안 된다.
"""

import re
from collections import Counter
from typing import Literal, Sequence

from pydantic import BaseModel

from app.adapters.alumni_types import AlumniRecord

# 학과코드 + G + 숫자3. card_a 가 학부 추천 풀에서 빼는 그 코드.
GRAD_COURSE = re.compile(r"[A-Z]{2,4}G\d{3}")

TAKEN_LABEL = "대학원 연계 과목 이수"
NOT_TAKEN_LABEL = "미이수"


class TrackGroup(BaseModel):
    label: str
    career_type: Literal["job", "grad", "other"]
    count: int


def grad_courses(record: AlumniRecord) -> list[str]:
    """이 졸업생이 이수한 대학원 연계 과목 코드."""
    return [e.course_id for e in record.enrollment if GRAD_COURSE.fullmatch(e.course_id)]


def split(records: Sequence[AlumniRecord]) -> list[TrackGroup]:
    """이수/미이수 2분할. 빈 쪽은 내보내지 않는다 (0명 항목 표시 방지)."""
    taken = sum(1 for r in records if grad_courses(r))
    groups: list[TrackGroup] = []
    if taken:
        groups.append(TrackGroup(label=TAKEN_LABEL, career_type="grad", count=taken))
    if len(records) - taken:
        groups.append(
            TrackGroup(label=NOT_TAKEN_LABEL, career_type="other", count=len(records) - taken)
        )
    return groups


def top_grad_courses(records: Sequence[AlumniRecord], n: int = 5) -> list[tuple[str, int]]:
    """코호트가 실제로 이수한 대학원 연계 과목 상위 N. 동수는 코드 사전순(결정론)."""
    freq = Counter(cid for r in records for cid in grad_courses(r))
    return sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:n]
