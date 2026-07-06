"""다전공 경로 분포 집계: majors 조합별 인원·평균 학점 (정형만).

라벨 문자열 조립("단일전공 유지" 등)은 cards/card_c 책임.
"""

from typing import Optional, Sequence

from pydantic import BaseModel

from app.adapters.alumni_types import AlumniRecord

_ROLE_ORDER = {"double": 0, "triple": 1, "minor": 2}


class PathwayGroup(BaseModel):
    extra_majors: list[str]  # primary 제외, role 순서 (double → triple → minor)
    count: int
    avg_primary_credits: Optional[float]
    avg_second_credits: Optional[float]
    avg_third_credits: Optional[float]


def _mean(values: list[float]) -> Optional[float]:
    return round(sum(values) / len(values), 1) if values else None


def aggregate(alumni: Sequence[AlumniRecord]) -> list[PathwayGroup]:
    buckets: dict[tuple[str, ...], list[AlumniRecord]] = {}
    for record in alumni:
        extras = sorted(
            (m for m in record.majors if m.role in _ROLE_ORDER),
            key=lambda m: _ROLE_ORDER[m.role],
        )
        key = tuple(m.label for m in extras)
        buckets.setdefault(key, []).append(record)

    groups: list[PathwayGroup] = []
    for key, members in buckets.items():
        def _credits(pick) -> list[float]:
            out = []
            for r in members:
                m = pick(r)
                if m is not None and m.credits is not None:
                    out.append(m.credits)
            return out

        def _primary(r):
            return next((m for m in r.majors if m.role == "primary"), None)

        def _nth_extra(r, i):
            extras_r = sorted(
                (m for m in r.majors if m.role in _ROLE_ORDER),
                key=lambda m: _ROLE_ORDER[m.role],
            )
            return extras_r[i] if len(extras_r) > i else None

        groups.append(
            PathwayGroup(
                extra_majors=list(key),
                count=len(members),
                avg_primary_credits=_mean(_credits(_primary)),
                avg_second_credits=_mean(_credits(lambda r: _nth_extra(r, 0))),
                avg_third_credits=_mean(_credits(lambda r: _nth_extra(r, 1))),
            )
        )
    groups.sort(key=lambda g: (-g.count, g.extra_majors))
    return groups
