"""유사 졸업생 클러스터링: K-Means (A11 확정 — mock 단계, random_state 고정).

클러스터 라벨 = 구성원 최빈 career.label (결정론). 실데이터 후 HDBSCAN 재검토.
"""

from collections import Counter
from typing import Literal, Sequence

from pydantic import BaseModel
from sklearn.cluster import KMeans

from app.adapters.alumni_types import AlumniRecord

UNLABELED = "미분류"


class ClusterGroup(BaseModel):
    label: str
    career_type: Literal["job", "grad", "other"]
    count: int


def _majority(records: Sequence[AlumniRecord]) -> tuple[str, str]:
    labels = Counter(
        (r.career.label if r.career and r.career.label else UNLABELED) for r in records
    )
    types = Counter(
        (r.career.type if r.career and r.career.type else "other") for r in records
    )
    # 최빈, 동수는 사전순 (결정론)
    label = min(labels, key=lambda x: (-labels[x], x))
    ctype = min(types, key=lambda x: (-types[x], x))
    return label, ctype


def cluster(
    records: Sequence[AlumniRecord], embeddings, k: int = 3
) -> list[ClusterGroup]:
    if not records:
        return []
    k = min(k, len(records))
    if k == 1:
        assignments = [0] * len(records)
    else:
        km = KMeans(n_clusters=k, random_state=0, n_init=10)
        assignments = km.fit_predict(embeddings)

    merged: dict[tuple[str, str], int] = {}
    for cid in range(k):
        members = [records[i] for i, a in enumerate(assignments) if a == cid]
        if not members:
            continue
        key = _majority(members)
        merged[key] = merged.get(key, 0) + len(members)

    groups = [
        ClusterGroup(label=label, career_type=ctype, count=n)
        for (label, ctype), n in merged.items()
    ]
    groups.sort(key=lambda g: (-g.count, g.label))
    return groups
