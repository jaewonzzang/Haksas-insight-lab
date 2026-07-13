"""content_based — 이수 과목 텍스트 ↔ 후보 TF-IDF 코사인 signal."""

from app.engines.recommender import content_based


def _row(cid, name, desc):
    return {"course_id": cid, "course_name": name, "description_raw": desc}


TAKEN = [_row("CSE1010", "프로그래밍입문", "파이썬 프로그래밍 기초와 자료형")]
POOL = [
    _row("CSE2020", "자료구조", "자료형 리스트 트리 그래프 파이썬 실습"),
    _row("REL1001", "종교학개론", "세계 종교 전통과 의례"),
]


def test_similar_course_scores_higher():
    scores = content_based.score(TAKEN, POOL)
    assert set(scores) == {"CSE2020", "REL1001"}
    assert scores["CSE2020"] > scores["REL1001"]
    assert all(0 <= v <= 100 for v in scores.values())


def test_empty_taken_returns_empty():
    assert content_based.score([], POOL) == {}


def test_empty_pool_returns_empty():
    assert content_based.score(TAKEN, []) == {}


def test_no_text_returns_empty():
    taken = [_row("X1", "", None)]
    pool = [_row("Y1", "", None)]
    assert content_based.score(taken, pool) == {}


def test_overview_text_changes_similarity():
    # 강의계획서 개요 결합 (2026-07-13) — 개요가 있으면 유사도에 반영된다
    taken = [_row("T1", "운영체제", "")]
    pool = [_row("P1", "과목갑", ""), _row("P2", "과목을", "")]
    overviews = {"P1": "운영체제 프로세스 스케줄링 심화", "P2": "르네상스 미술사 개관"}
    out = content_based.score(taken, pool, overviews)
    assert out["P1"] > out["P2"]
