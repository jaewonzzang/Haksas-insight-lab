"""mock 졸업생 생성기 단위 테스트."""

from app.adapters.alumni_types import AlumniRecord
from scripts.generate_mock_alumni import generate_records

DEPT_POOL = ["C1", "C2", "C3", "C4", "C5"]
GEN_POOL = ["G1", "G2", "G3"]


def _pools(departments):
    return {d: DEPT_POOL for d in departments}


def test_count_and_type():
    recs = generate_records(
        n_per_dept=3, departments=["A", "B"], course_pools=_pools(["A", "B"]),
        general_pool=GEN_POOL, seed=1,
    )
    assert len(recs) == 6
    assert all(isinstance(r, AlumniRecord) for r in recs)


def test_deterministic_with_seed():
    a = generate_records(
        n_per_dept=2, departments=["A"], course_pools=_pools(["A"]),
        general_pool=GEN_POOL, seed=7,
    )
    b = generate_records(
        n_per_dept=2, departments=["A"], course_pools=_pools(["A"]),
        general_pool=GEN_POOL, seed=7,
    )
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]


def test_core_and_primary_major_present():
    recs = generate_records(
        n_per_dept=1, departments=["아트&테크놀로지학과"],
        course_pools=_pools(["아트&테크놀로지학과"]), general_pool=GEN_POOL, seed=3,
    )
    r = recs[0]
    assert r.alumni_id and r.department == "아트&테크놀로지학과"
    assert r.majors[0].role == "primary"
    assert r.career is not None and r.career.type in {"job", "grad", "other"}


def test_term_sampling_biased_to_dept_and_general():
    recs = generate_records(
        n_per_dept=1, departments=["A"], course_pools=_pools(["A"]),
        general_pool=GEN_POOL, seed=5,
    )
    first_term = [e for e in recs[0].enrollment if e.year_taken == 1 and e.term_taken == 1]
    assert len(first_term) == 5
    assert sum(1 for e in first_term if e.course_id in DEPT_POOL) == 3
    assert sum(1 for e in first_term if e.course_id in GEN_POOL) == 2
