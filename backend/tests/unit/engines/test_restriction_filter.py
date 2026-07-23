"""restriction_filter — 블랙리스트 차단 + 화이트리스트 시행 (2026-07-23 확장)."""

from app.engines.recommender import restriction_filter
from app.engines.recommender.scoring import score_candidate

SCORED = {
    cid: score_candidate({"콘텐츠 유사도": 80.0}, None)
    for cid in ["C1", "C2", "C3", "C4", "C5", "C6"]
}


def _r(cid, dept, status):
    return {"course_id": cid, "target_dept": dept, "status": status}


RESTRICTIONS = [
    _r("C1", "컴퓨터공학과", "forbidden"),
    _r("C2", "컴퓨터공학과", "major_only_forbidden"),
    _r("C3", "컴퓨터공학과", "allowed"),             # 화이트리스트: 컴공(전공 무관)만
    _r("C4", "경영학과", "forbidden"),               # 타 학과 대상 → 무관
    _r("C5", "컴퓨터공학과", "major_only_allowed"),  # 화이트리스트: 컴공 1전공만
    # C6: 제한 없음 → 항상 통과
]


def test_primary_major_student():
    """컴공 1전공: forbidden·major_only_forbidden 차단, 화이트리스트는 전부 충족."""
    out = restriction_filter.apply(
        dict(SCORED), primary_depts={"컴퓨터공학과"}, all_depts={"컴퓨터공학과"},
        restrictions=RESTRICTIONS,
    )
    assert set(out) == {"C3", "C4", "C5", "C6"}


def test_secondary_major_student():
    """컴공 2전공(1전공 아트&테크): '1전공 가능'(C5) 화이트리스트 미충족 → 차단.

    학생 A 실사례 — CSE2035 "컴퓨터공학과(1전공 가능)" 가 복수전공생에게 추천되던 문제.
    """
    out = restriction_filter.apply(
        dict(SCORED),
        primary_depts={"아트&테크놀로지학과"},
        all_depts={"아트&테크놀로지학과", "컴퓨터공학과"},
        restrictions=RESTRICTIONS,
    )
    # C1 forbidden(컴공 소속) 차단 · C2 major_only_forbidden 은 1전공 아니라 통과
    # C3 allowed(전공 무관) 통과 · C5 major_only_allowed 미충족 차단
    assert set(out) == {"C2", "C3", "C4", "C6"}


def test_unrelated_student_blocked_by_whitelist():
    """무관 학과 학생: 화이트리스트 걸린 C3·C5 차단, 블랙리스트는 무관."""
    out = restriction_filter.apply(
        dict(SCORED), primary_depts={"심리학과"}, all_depts={"심리학과"},
        restrictions=RESTRICTIONS,
    )
    assert set(out) == {"C1", "C2", "C4", "C6"}
