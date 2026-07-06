"""career/cluster — K-Means(A11 확정) + 최빈 진로 라벨."""

import numpy as np

from app.adapters.alumni_types import AlumniRecord, Career
from app.engines.career import cluster


def _alum(aid, ctype, label):
    return AlumniRecord(
        alumni_id=aid, department="컴퓨터공학과",
        career=Career(type=ctype, label=label),
    )


# 임베딩 공간에서 뚜렷이 갈리는 두 무리
RECORDS = [
    _alum("a1", "job", "IT 취업"),
    _alum("a2", "job", "IT 취업"),
    _alum("a3", "grad", "국내 대학원 (CS)"),
    _alum("a4", "grad", "국내 대학원 (CS)"),
]
EMB = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]])


def test_two_clear_clusters():
    groups = cluster.cluster(RECORDS, EMB, k=2)
    assert [(g.label, g.career_type, g.count) for g in groups] == [
        ("IT 취업", "job", 2),
        ("국내 대학원 (CS)", "grad", 2),
    ]


def test_deterministic():
    a = cluster.cluster(RECORDS, EMB, k=2)
    b = cluster.cluster(RECORDS, EMB, k=2)
    assert a == b


def test_k_capped_by_records():
    groups = cluster.cluster(RECORDS[:1], EMB[:1], k=3)
    assert len(groups) == 1
    assert groups[0].count == 1


def test_none_career_bucketed():
    records = [AlumniRecord(alumni_id="x", department="d")] * 2
    groups = cluster.cluster(records, EMB[:2], k=1)
    assert groups[0].label == "미분류"
    assert groups[0].career_type == "other"
