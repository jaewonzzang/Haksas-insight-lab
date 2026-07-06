"""콘텐츠 기반 signal: 이수 과목 텍스트 ↔ 후보 텍스트 TF-IDF 코사인 (0~100).

결합·감산·컷오프는 hybrid + scoring 담당. 정형 수치만 산출.
"""

from typing import Mapping, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _text(row: Mapping) -> str:
    return f"{row['course_name'] or ''} {row['description_raw'] or ''}".strip()


def score(
    taken_rows: Sequence[Mapping], pool_rows: Sequence[Mapping]
) -> dict[str, float]:
    if not taken_rows or not pool_rows:
        return {}
    docs = [_text(r) for r in taken_rows] + [_text(r) for r in pool_rows]
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
