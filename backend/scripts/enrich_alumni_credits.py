"""alumni.json 후처리: Major.credits 근사 채움 (카드 C 추가 이수 학점).

원본에 과목구분(전필/전선) 컬럼이 없어 요건 인정 학점은 산출 불가 — 대신
**관측 이수 학점**으로 근사한다: 이수 과목 중 "그 전공의 개설 학과
(dept_normalizer.major_label_departments) + 비교양(is_general=0)" 학점 합.
카드 C 문구("평균 (추가) 이수 학점")는 관측 표현이라 그대로 정합.

검증 실측 (2026-07-18, 이력 완결 다전공자 895명): 2전공 근사 중앙값 33,
상위 조합 평균 37~41 — 다전공 이수 요건(36~42학점)과 같은 자리수.
라벨 미해석(폐지 연계전공 "한국사회문화"·학생설계전공 등)은 None(미상) 유지.

입력·출력: data/processed/alumni.json (in-place).
선행: build_course_db.py (courses.db), build_alumni_from_enrollment.py.
실행: uv run python scripts/enrich_alumni_credits.py
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.adapters.alumni_types import AlumniRecord
from app.core.dept_normalizer import major_label_departments

CourseInfo = dict[str, tuple[str, float, int]]  # course_id → (개설 학과, 학점, is_general)


def observed_credits(
    course_ids: list[str],
    depts: set[str],
    course_info: CourseInfo,
    alias: dict[str, str],
) -> float:
    """이수 과목 중 depts 개설·비교양 과목의 학점 합 (중복 이수 1회, old→new 별칭)."""
    total = 0.0
    for cid in {alias.get(c, c) for c in course_ids}:
        row = course_info.get(cid)
        if row and row[0] in depts and not row[2]:
            total += row[1]
    return total


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 출력 깨짐 방지
    records = [
        AlumniRecord.model_validate(o)
        for o in json.loads(config.ALUMNI_REAL_PATH.read_text("utf-8"))
    ]
    con = sqlite3.connect(config.DB_PATH)
    course_info: CourseInfo = {
        cid: (dept, credit or 0.0, gen)
        for cid, dept, credit, gen in con.execute(
            "SELECT course_id, department, credit, is_general FROM courses"
        )
    }
    alias = dict(
        con.execute(
            "SELECT old_course_id, new_course_id FROM course_aliases"
            " WHERE old_course_id IS NOT NULL"
        )
    )
    con.close()
    db_depts = {dept for dept, _, _ in course_info.values()}

    filled = unmapped = 0
    missed: dict[str, int] = {}
    for r in records:
        ids = [e.course_id for e in r.enrollment]
        for m in r.majors:
            depts = set(major_label_departments(m.label, db_depts))
            if depts:
                m.credits = observed_credits(ids, depts, course_info, alias)
                filled += 1
            else:
                m.credits = None
                unmapped += 1
                missed[m.label] = missed.get(m.label, 0) + 1
    config.ALUMNI_REAL_PATH.write_text(
        json.dumps([r.model_dump() for r in records], ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"전공 슬롯 {filled + unmapped:,}개: 채움 {filled:,} · 미상 {unmapped:,} (라벨 {len(missed)}종)")
    top = sorted(missed.items(), key=lambda kv: -kv[1])[:5]
    if top:
        print(f"미해석 상위: {top}")


if __name__ == "__main__":
    main()
