"""콘텐츠 기반 signal: 이수 과목 텍스트 ↔ 후보 텍스트 TF-IDF 코사인 (0~100).

강의계획서 개요(overviews)가 있으면 과목 텍스트에 결합한다 (2026-07-13 — 부분 커버리지:
없는 과목은 기존 과목명+설명 원문만). 결합·감산·컷오프는 hybrid + scoring 담당.
"""

from typing import Mapping, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _text(row: Mapping, overviews: Mapping[str, str]) -> str:
    base = f"{row['course_name'] or ''} {row['description_raw'] or ''}"
    return f"{base} {overviews.get(row['course_id'], '')}".strip()


def score(
    taken_rows: Sequence[Mapping],
    pool_rows: Sequence[Mapping],
    overviews: Mapping[str, str] | None = None,
) -> dict[str, float]:
    if not taken_rows or not pool_rows:
        return {}
    ov = overviews or {}
    docs = [_text(r, ov) for r in taken_rows] + [_text(r, ov) for r in pool_rows]
    try:
        matrix = TfidfVectorizer().fit_transform(docs)
    except ValueError:  # 전부 빈 문서 → 어휘 없음
        return {}
    n_taken = len(taken_rows)
    centroid = np.asarray(matrix[:n_taken].mean(axis=0))
    sims = cosine_similarity(centroid, matrix[n_taken:])[0]
    return {
        pool_rows[i]["course_id"]: round(float(sims[i]) * 100, 1)
        for i in range(len(pool_rows))
    }
