"""카드 D 오케스트레이터: 임베딩 → 유사도 top-N → 클러스터 → CardD + ClusterEvidence.

pattern_summary/summary/text 는 W5(llm/translator) 도입 전까지 결정론 폴백.
"""

import sqlite3
from collections import Counter

from app.adapters.alumni_types import AlumniRecord
from app.core.dept_normalizer import candidate_departments
from app.db.queries import course_queries
from app.engines.career import cluster as career_cluster
from app.engines.career import embedding, similarity
from app.schemas.cards import (
    CardD,
    CareerEntry,
    CareerPattern,
    CareerSubChip,
    ClusterEvidence,
    CommonCourse,
    SimilarityFactor,
)
from app.schemas.input import StudentInput

TOP_N = 30
K_CLUSTERS = 3
TYPE_NAMES = {"job": "취업", "grad": "대학원 진학", "other": "기타 진로"}


def _empty() -> tuple[CardD, ClusterEvidence]:
    return (
        CardD(
            similar_label="유사 경로 0명", sample_size=0, entries=[],
            sub_title="", sub_chips=[], pattern_summary="",
        ),
        ClusterEvidence(factors=[], common_courses=[], career_patterns=[], summary=""),
    )


def build(
    student: StudentInput,
    con: sqlite3.Connection,
    alumni: list[AlumniRecord],
    top_n: int = TOP_N,
) -> tuple[CardD, ClusterEvidence]:
    with_courses = [r for r in alumni if r.enrollment]
    sets = [{e.course_id for e in r.enrollment} for r in with_courses]
    taken = set(student.taken_course_ids)

    embedded = embedding.embed_sets(sets, taken)
    if embedded is None:
        return _empty()
    matrix, student_vec = embedded

    ranked = similarity.top_n(student_vec, matrix, top_n)
    subset = [with_courses[i] for i, _ in ranked]
    subset_sets = [sets[i] for i, _ in ranked]
    scores = [s for _, s in ranked]
    n = len(subset)
    if n == 0:
        return _empty()

    groups = career_cluster.cluster(
        subset, matrix[[i for i, _ in ranked]], k=K_CLUSTERS
    )
    entries = [
        CareerEntry(
            cluster_label=g.label,
            type=g.career_type,
            count=g.count,
            share_percent=round(g.count / n * 100),
        )
        for g in groups
    ]

    # sub_chips — grad 우선, 없으면 최다 유형 세부
    by_type = Counter(
        (r.career.type if r.career and r.career.type else "other") for r in subset
    )
    focus = "grad" if by_type.get("grad") else by_type.most_common(1)[0][0]
    focus_labels = Counter(
        (r.career.label if r.career and r.career.label else "미분류")
        for r in subset
        if (r.career.type if r.career and r.career.type else "other") == focus
    )
    sub_chips = [
        CareerSubChip(label=label, n=cnt)
        for label, cnt in sorted(focus_labels.items(), key=lambda x: (-x[1], x[0]))[:5]
    ]
    sub_title = f"{TYPE_NAMES[focus]} 세부 분포"

    top_entry = entries[0]
    card = CardD(
        similar_label=f"유사 경로 {n}명",
        sample_size=n,
        entries=entries,
        sub_title=sub_title,
        sub_chips=sub_chips,
        pattern_summary=(
            f"유사 경로 {n}명 중 {top_entry.cluster_label} 계열이 "
            f"{top_entry.share_percent}%로 가장 많습니다."
        ),
    )

    # ClusterEvidence — 결정론 분해 (A13)
    def _jaccard(a: set[str], b: set[str]) -> float:
        return len(a & b) / len(a | b) if (a | b) else 0.0

    depts = {student.department, *candidate_departments(student.department)}
    factors = [
        SimilarityFactor(
            label="이수과목 중복도",
            percent=round(sum(_jaccard(taken, s) for s in subset_sets) / n * 100),
        ),
        SimilarityFactor(
            label="이수경로 유사도",
            percent=round(sum(scores) / n * 100),
        ),
        SimilarityFactor(
            label="학과 코호트 일치",
            percent=round(sum(1 for r in subset if r.department in depts) / n * 100),
        ),
    ]
    course_freq = Counter(cid for s in subset_sets for cid in s)
    top_courses = sorted(course_freq.items(), key=lambda x: (-x[1], x[0]))[:5]
    names = {
        r["course_id"]: r["course_name"]
        for r in course_queries.list_by_ids(con, [cid for cid, _ in top_courses])
    }
    common_courses = [
        CommonCourse(name=names.get(cid, cid), n=cnt) for cid, cnt in top_courses
    ]
    career_patterns = [
        CareerPattern(
            label=g.label,
            type=g.career_type,
            text=f"유사 졸업생 {g.count}명이 이 경로를 선택",
        )
        for g in groups[:3]
    ]
    evidence = ClusterEvidence(
        factors=factors,
        common_courses=common_courses,
        career_patterns=career_patterns,
        summary=f"이수 패턴이 유사한 졸업생 {n}명의 진로 분포 기반",
    )
    return card, evidence
