"""합성 졸업생 이수경로/진로 데이터 생성.

실 데이터 수령 전 개발/시연용. 출력: data/mock/alumni.json (AlumniRecord[]).
course_id 는 빌드된 courses.db 에서 샘플, 없으면 합성 코드로 폴백.
스키마는 실데이터 합의가 완료되면 맞춰 갱신.
실행: uv run python scripts/generate_mock_alumni.py
"""

import json
import random
import sqlite3
import sys
from pathlib import Path

# 프로젝트 미설치 venv 에서 scripts/ 직접 실행을 위한 경로 부트스트랩.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.adapters.alumni_types import AlumniRecord, Career, Enrollment, Major

# DB courses.department 원문과 일치 (dept_normalizer 합집합 코호트 매칭 전제)
DEPARTMENTS = [
    "아트&테크놀로지학과",
    "미디어&엔터테인먼트학과",
    "신문방송학과",
    "컴퓨터공학과",
]
GENERAL_DEPT = "전인교육원"
CAREER_POOL = {
    "job": ["IT 취업", "금융 취업", "일반 기업"],
    "grad": ["국내 대학원 (CS)", "국내 대학원 (데이터)", "해외 대학원"],
    "other": ["창업", "해외", "미정"],
}
MULTIMAJOR_LABELS = ["컴퓨터공학", "경영학", "심리학", "데이터사이언스"]
_SYNTHETIC_POOL = [f"SYN{n:04d}" for n in range(1, 201)]


def _load_course_pools(db_path: Path) -> tuple[dict[str, list[str]], list[str]]:
    """학과별 course_id 풀 + 교양(전인교육원) 풀. DB 없으면 합성 폴백."""
    if not db_path.exists():
        return {d: list(_SYNTHETIC_POOL) for d in DEPARTMENTS}, list(_SYNTHETIC_POOL)
    con = sqlite3.connect(db_path)
    try:
        by_dept: dict[str, list[str]] = {}
        for dept in [*DEPARTMENTS, GENERAL_DEPT]:
            rows = con.execute(
                "SELECT course_id FROM courses WHERE department = ? "
                "AND course_type = 'regular' ORDER BY course_id",
                (dept,),
            ).fetchall()
            by_dept[dept] = [r[0] for r in rows] or list(_SYNTHETIC_POOL)
    finally:
        con.close()
    return {d: by_dept[d] for d in DEPARTMENTS}, by_dept[GENERAL_DEPT]


def _sample_term(dept_pool: list[str], general_pool: list[str], rng: random.Random) -> list[str]:
    """학기당 5과목: 자기 학과 3 + 교양 2 편향 샘플링."""
    own = rng.sample(dept_pool, min(3, len(dept_pool)))
    gen = rng.sample(general_pool, min(2, len(general_pool)))
    return own + gen


def _one_record(
    alumni_id: str,
    dept: str,
    dept_pool: list[str],
    general_pool: list[str],
    rng: random.Random,
) -> AlumniRecord:
    n_extra = rng.choices([0, 1, 2], weights=[40, 45, 15])[0]
    majors = [Major(label=dept, role="primary", credits=float(rng.randint(60, 90)))]
    for role in ("double", "triple")[:n_extra]:
        majors.append(
            Major(label=rng.choice(MULTIMAJOR_LABELS), role=role, credits=float(rng.randint(36, 50)))
        )
    enrollment: list[Enrollment] = []
    for year in range(1, 5):
        for term in (1, 2):
            for cid in _sample_term(dept_pool, general_pool, rng):
                enrollment.append(Enrollment(course_id=cid, year_taken=year, term_taken=term))
    ctype = rng.choice(["job", "grad", "other"])
    career = Career(type=ctype, label=rng.choice(CAREER_POOL[ctype]))
    return AlumniRecord(
        alumni_id=alumni_id,
        department=dept,
        majors=majors,
        enrollment=enrollment,
        career=career,
    )


def generate_records(
    *,
    n_per_dept: int = 60,
    departments: list[str] = DEPARTMENTS,
    course_pools: dict[str, list[str]] | None = None,
    general_pool: list[str] | None = None,
    seed: int = 42,
) -> list[AlumniRecord]:
    rng = random.Random(seed)
    pools = course_pools if course_pools is not None else {d: list(_SYNTHETIC_POOL) for d in departments}
    gen_pool = general_pool if general_pool is not None else list(_SYNTHETIC_POOL)
    records: list[AlumniRecord] = []
    counter = 0
    for dept in departments:
        for _ in range(n_per_dept):
            counter += 1
            records.append(_one_record(f"alum_{counter:05d}", dept, pools[dept], gen_pool, rng))
    return records


def main() -> None:
    pools, general_pool = _load_course_pools(config.DB_PATH)
    records = generate_records(course_pools=pools, general_pool=general_pool)
    config.MOCK_DIR.mkdir(parents=True, exist_ok=True)
    out = config.ALUMNI_MOCK_PATH
    out.write_text(
        json.dumps([r.model_dump() for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(records)} records -> {out}")


if __name__ == "__main__":
    main()
