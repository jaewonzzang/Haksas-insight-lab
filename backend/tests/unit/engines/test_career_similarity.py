"""career/similarity — 코사인 top-N (결정론 tie-break)."""

import numpy as np

from app.engines.career import similarity


def test_top_n_orders_by_score_then_index():
    matrix = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]])
    student = np.array([[1.0, 0.0]])
    result = similarity.top_n(student, matrix, 3)
    assert [i for i, _ in result] == [0, 2, 1]  # 동점(0,2)은 인덱스순
    assert result[0][1] == 1.0


def test_n_larger_than_rows():
    matrix = np.array([[1.0, 0.0]])
    student = np.array([[1.0, 0.0]])
    assert len(similarity.top_n(student, matrix, 10)) == 1
