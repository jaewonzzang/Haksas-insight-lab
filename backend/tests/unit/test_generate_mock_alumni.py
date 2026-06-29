"""mock 졸업생 생성기 단위 테스트."""

from app.adapters.alumni_types import AlumniRecord
from scripts.generate_mock_alumni import generate_records

POOL = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]


def test_count_and_type():
    recs = generate_records(n_per_dept=3, departments=["A", "B"], course_pool=POOL, seed=1)
    assert len(recs) == 6
    assert all(isinstance(r, AlumniRecord) for r in recs)


def test_deterministic_with_seed():
    a = generate_records(n_per_dept=2, departments=["A"], course_pool=POOL, seed=7)
    b = generate_records(n_per_dept=2, departments=["A"], course_pool=POOL, seed=7)
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]


def test_core_and_primary_major_present():
    recs = generate_records(
        n_per_dept=1, departments=["아트&테크놀로지"], course_pool=POOL, seed=3
    )
    r = recs[0]
    assert r.alumni_id and r.department == "아트&테크놀로지"
    assert r.majors[0].role == "primary"
    assert r.career is not None and r.career.type in {"job", "grad", "other"}
