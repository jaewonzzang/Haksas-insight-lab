"""학생 벡터 ↔ 졸업생 행렬 코사인 유사도 top-N (결정론)."""

from typing import List, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def top_n(student_vec, alumni_matrix, n: int) -> List[Tuple[int, float]]:
    scores = cosine_similarity(student_vec, alumni_matrix)[0]
    order = np.lexsort((np.arange(len(scores)), -scores))  # 점수 desc, 인덱스 asc
    return [(int(i), float(scores[i])) for i in order[:n]]
