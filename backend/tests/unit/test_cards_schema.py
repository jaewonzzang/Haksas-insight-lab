"""cards.py ↔ frontend/src/types/api.ts 계약 미러 검증."""

from app.schemas.cards import DashboardResponse


def _empty_dashboard() -> dict:
    # frontend src/mock/profiles.fixture.ts 의 emptyDashboard 와 동일 형태
    return {
        "profile": {
            "name": "학생 B", "department": "—", "year": "—",
            "analysis_date": "—", "report_semester": "2026-1학기",
            "next_semester": "2026-2",
        },
        "kpi": {"earned_credits": 0, "gpa": None, "gpa_scale": 4.3, "similar_alumni_n": 0},
        "card_a": {"major": [], "general": [], "candidates": []},
        "card_c": {"cohort_label": "—", "entries": [], "baseline_note": ""},
        "card_d": {"similar_label": "—", "sample_size": 0, "entries": [],
                   "sub_title": "", "sub_chips": [], "pattern_summary": ""},
        "cluster": {"factors": [], "common_courses": [], "career_patterns": [], "summary": ""},
    }


def test_empty_dashboard_validates():
    resp = DashboardResponse.model_validate(_empty_dashboard())
    assert resp.kpi.gpa is None
    assert resp.card_a.candidates == []


def test_populated_course_and_pathway():
    data = _empty_dashboard()
    data["card_a"]["major"] = [{
        "course_id": "CSE3013", "course_name": "컴퓨터그래픽스", "credit": 3.0,
        "grade": "강추", "score_percent": 87, "reason_short": "사유",
        "kind": "major", "kind_label": "전공선택", "area_label": None,
        "factors": [{"label": "코호트 선호도", "weight_percent": 72,
                     "contribution": "+26", "kind": "pos"}],
        "why_summary": "요약",
    }]
    data["card_c"]["entries"] = [{
        "id": "p1", "label": "복수전공", "count": 58, "share_percent": 31.5,
        "bar_percent": 100, "detail_label": "복수전공 상세",
        "credits": {"major1": 36, "major2": 36, "major3": None},
    }]
    data["card_d"]["entries"] = [{
        "cluster_label": "IT 취업", "type": "job", "count": 12, "share_percent": 44.4,
    }]
    resp = DashboardResponse.model_validate(data)
    assert resp.card_a.major[0].grade == "강추"
    entry = resp.card_c.entries[0]
    assert entry.tag is None and entry.dim is False  # ts optional 필드 기본값
