"""카드 C/D — 실 DB + mock 졸업생 240명 스모크. 산출물 없으면 skip."""

import json
from pathlib import Path

import pytest

from app import config
from app.adapters.alumni_types import AlumniRecord
from app.cards import card_c, card_d
from app.db.connection import get_connection
from app.schemas.input import StudentInput


@pytest.fixture(scope="module")
def con():
    if not config.DB_PATH.exists():
        pytest.skip("s_compass_courses.db 필요")
    con = get_connection()
    yield con
    con.close()


@pytest.fixture(scope="module")
def alumni():
    if not config.ALUMNI_MOCK_PATH.exists():
        pytest.skip("data/mock/alumni.json 필요")
    raw = json.loads(Path(config.ALUMNI_MOCK_PATH).read_text(encoding="utf-8"))
    return [AlumniRecord.model_validate(r) for r in raw]


@pytest.fixture(scope="module")
def student(con):
    sample_taken = [r["course_id"] for r in con.execute(
        "SELECT course_id FROM courses WHERE department = '아트&테크놀로지학과' "
        "AND course_type = 'regular' ORDER BY course_id LIMIT 10"
    )]
    return StudentInput(
        student_id="S1", department="지식융합미디어학부", taken_course_ids=sample_taken,
    )


def test_card_c_cohort_matched(student, alumni):
    card = card_c.build(student, alumni)
    # Task 1 재생성 후 미디어 3개 학과 × 60 = 180명이 합집합 코호트에 매칭돼야 함
    assert card.cohort_label == "지식융합미디어학부 · 졸업생 180명"
    assert card.entries
    assert card.entries[0].tag == "최다"
    assert abs(sum(e.share_percent for e in card.entries) - 100) <= 3  # 반올림 오차


def test_card_d_smoke(student, con, alumni):
    card, evidence = card_d.build(student, con, alumni)
    assert card.sample_size == 30
    assert card.entries and sum(e.count for e in card.entries) == 30
    assert card.sub_chips
    assert len(evidence.factors) == 3
    assert len(evidence.common_courses) == 5
    a = card_d.build(student, con, alumni)
    assert a == (card, evidence)  # 결정론
