"""card_a — 실 DB + mock 졸업생 스모크. 산출물 없으면 skip."""

import json
from pathlib import Path

import pytest

from app import config
from app.adapters.alumni_types import AlumniRecord
from app.cards import card_a
from app.db.connection import get_connection
from app.schemas.input import StudentInput


@pytest.fixture(scope="module")
def con():
    if not config.DB_PATH.exists():
        pytest.skip("s_compass_courses.db 필요 (scripts/build_course_db.py)")
    con = get_connection()
    yield con
    con.close()


@pytest.fixture(scope="module")
def alumni():
    if not config.ALUMNI_MOCK_PATH.exists():
        pytest.skip("data/mock/alumni.json 필요 (scripts/generate_mock_alumni.py)")
    raw = json.loads(Path(config.ALUMNI_MOCK_PATH).read_text(encoding="utf-8"))
    return [AlumniRecord.model_validate(r) for r in raw]


def test_smoke_knowledge_convergence_media(con, alumni):
    sample_taken = [r["course_id"] for r in con.execute(
        "SELECT course_id FROM courses WHERE department = '컴퓨터공학과' "
        "AND course_type = 'regular' ORDER BY course_id LIMIT 5"
    )]
    student = StudentInput(
        student_id="S1", department="지식융합미디어학부", taken_course_ids=sample_taken,
    )
    card = card_a.build(student, con, alumni)
    assert len(card.major) == 4
    assert len(card.general) == 4
    assert len(card.candidates) <= 20
    assert all(0 <= c.score_percent <= 100 for c in card.candidates)
