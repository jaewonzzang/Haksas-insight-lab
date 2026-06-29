"""합성 졸업생 이수경로/진로 데이터 생성.

실 데이터 수령 전 개발/시연용. 출력: data/mock/alumni.json (AlumniRecord[]).
course_id 는 빌드된 courses.db 에서 샘플, 없으면 합성 코드로 폴백.
스키마는 실데이터 합의가 완료되면 맞춰 갱신.
실행: uv run python scripts/generate_mock_alumni.py
"""

import json
import random
import sqlite3
from pathlib import Path

from app import config
from app.adapters.alumni_types import AlumniRecord, Career, Enrollment, Major

DEPARTMENTS = ["아트&테크놀로지", "컴퓨터공학과", "경영학과"]
CAREER_POOL = {
    "job": ["IT 취업", "금융 취업", "일반 기업"],
    "grad": ["국내 대학원 (CS)", "국내 대학원 (데이터)", "해외 대학원"],
    "other": ["창업", "해외", "미정"],
}
MULTIMAJOR_LABELS = ["컴퓨터공학", "경영학", "심리학", "데이터사이언스"]
_SYNTHETIC_POOL = [f"SYN{n:04d}" for n in range(1, 201)]


def _load_course_pool(db_path: Path) -> list[str]:
    """courses.db 에서 course_id 샘플. 없거나 비면 합성 폴백."""
    if not db_path.exists():
        return list(_SYNTHETIC_POOL)
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute("SELECT course_id FROM courses").fetchall()
    finally:
        con.close()
    return [r[0] for r in rows] or list(_SYNTHETIC_POOL)


def _one_record(
    alumni_id: str,
    dept: str,
    pool: list[str],
    courses_per_term: int,
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
            for cid in rng.sample(pool, min(courses_per_term, len(pool))):
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
    course_pool: list[str] | None = None,
    courses_per_term: int = 5,
    seed: int = 42,
) -> list[AlumniRecord]:
    rng = random.Random(seed)
    pool = course_pool if course_pool is not None else list(_SYNTHETIC_POOL)
    records: list[AlumniRecord] = []
    counter = 0
    for dept in departments:
        for _ in range(n_per_dept):
            counter += 1
            records.append(_one_record(f"alum_{counter:05d}", dept, pool, courses_per_term, rng))
    return records


def main() -> None:
    pool = _load_course_pool(config.DB_PATH)
    records = generate_records(course_pool=pool)
    config.MOCK_DIR.mkdir(parents=True, exist_ok=True)
    out = config.ALUMNI_MOCK_PATH
    out.write_text(
        json.dumps([r.model_dump() for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(records)} records -> {out}")


if __name__ == "__main__":
    main()
