"""POST /analyze 통합 흐름 — 실 DB + mock 240명 + TestClient. 산출물 없으면 skip."""

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.schemas.cards import DashboardResponse

pytestmark = [
    pytest.mark.requires_data,
    pytest.mark.skipif(
        not config.DB_PATH.exists() or not config.ALUMNI_MOCK_PATH.exists(),
        reason="실 DB 또는 mock alumni 없음 (build_course_db / generate_mock_alumni 필요)",
    ),
]

# 학생 A 실 이수 32과목 (frontend takenCourses.fixture 매핑과 동일) + 군이러닝 placeholder 2건
TAKEN = [
    "COR1012", "HFS2002", "AAT3019", "CSE3030", "CSE3080", "CSE4010", "CSE4175",
    "ETS2001", "AAT2004", "COR1010", "MAS2003", "COR1007", "CSE3006", "CSE3015",
    "CSE3040", "MAS1004", "MAS2008", "STS2008", "COR1021", "GKS3002", "HSS3001",
    "PUB2005", "SHS2002", "ETS2003", "LED3015", "MAS2002", "STS2002", "STS2004",
    "COR1003", "MAS1001", "MAS1002", "GKS1001", "T12", "T13",
]


def test_analyze_returns_full_dashboard():
    client = TestClient(app)
    res = client.post(
        "/analyze",
        json={
            "student_id": "A",
            "department": "지식융합미디어학부",
            "extra_majors": ["컴퓨터공학과"],
            "year": 3,
            "prefer_team_project": True,
            "prefer_su_eval": True,
            "prefer_low_attendance": True,
            "taken_course_ids": TAKEN,
            "interest_career": None,
            "consider_multimajor": True,
        },
    )
    assert res.status_code == 200
    dash = DashboardResponse.model_validate(res.json())
    assert dash.profile.department == "지식융합미디어학부"
    assert 1 <= len(dash.card_a.major) <= 4
    assert 1 <= len(dash.card_a.general) <= 4
    assert len(dash.card_a.candidates) <= 20
    assert dash.card_c.entries, "카드 C 분포 비어 있음"
    assert dash.card_d.sample_size > 0
    assert dash.kpi.similar_alumni_n == dash.card_d.sample_size
    assert dash.kpi.earned_credits > 0  # 32과목 학점 합
    # 통역 문구 원문 의존 금지 — 비어 있지 않음만 확인 (폴백/통역 어느 쪽이든 통과)
    assert dash.card_d.pattern_summary.strip()
    assert all(c.reason_short.strip() for c in dash.card_a.major)
    import re as _re
    all_recs = dash.card_a.major + dash.card_a.general + dash.card_a.candidates
    assert all(not _re.fullmatch(r"[A-Z]{2,4}G\d{3}", c.course_id) for c in all_recs)
    assert all("캡스톤" not in c.course_name for c in all_recs)
    all_recs = dash.card_a.major + dash.card_a.candidates
    assert any(c.course_id.startswith("CSE") for c in all_recs), "복수전공(컴공) 과목이 전공 후보에 없음"


def test_health():
    client = TestClient(app)
    assert client.get("/health").status_code == 200


def test_courses_debug_lookup():
    client = TestClient(app)
    res = client.get("/courses/CSE3080")  # 자료구조
    assert res.status_code == 200
    assert res.json()["course_id"] == "CSE3080"


def test_courses_debug_404():
    client = TestClient(app)
    assert client.get("/courses/NOPE9999").status_code == 404
