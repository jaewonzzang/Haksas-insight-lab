"""career/embedding — 과목 ID TF-IDF (A10 확정)."""

from sklearn.metrics.pairwise import cosine_similarity

from app.engines.career import embedding

SETS = [
    {"CSE1010", "CSE2020", "AAT3001"},
    {"REL1001", "PHI1001"},
]


def test_embed_shapes_and_similarity():
    result = embedding.embed_sets(SETS, {"CSE1010", "CSE2020"})
    assert result is not None
    matrix, student = result
    assert matrix.shape[0] == 2
    sims = cosine_similarity(student, matrix)[0]
    assert sims[0] > sims[1]  # 겹치는 졸업생과 더 유사


def test_unseen_student_courses_zero_vector():
    result = embedding.embed_sets(SETS, {"ZZZ9999"})
    matrix, student = result
    assert student.nnz == 0  # 어휘 밖 → 영벡터


def test_empty_alumni_returns_none():
    assert embedding.embed_sets([], {"CSE1010"}) is None
    assert embedding.embed_sets([set(), set()], {"CSE1010"}) is None
