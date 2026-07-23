"""과목구분표 CSV → course_categories 테이블 (카드 A 성격 필터·이수 학점 카운트용).

과목구분 = "{전공} {유형}" 결합 문자열 → (major_raw, major_canonical, category, area_label)로 분해·정규화.
- 유형: 전공입문/전공필수/전공선택/학부공통(전공측) · 자유선택 · 교양 · 기타 · 계열입학표기 · 미상
- 전공: dept_normalizer.major_label_departments 로 canonical 학과 매핑. 학부/계열은 소속 학과로 전개
  (college 항목은 제외). 매핑 실패(연계전공 일부 등)는 major_canonical=None 으로 원문만 보존.
키가 (과목 × 전공) 다대다라 courses 에 못 붙임 → 별도 테이블. 설계: docs/advisory_2026-07-22.md.

입력: data/raw/과목구분_*.csv   선행: build_course_db.py (db_departments 조회)
실행: uv run python scripts/build_course_categories.py
"""

import glob
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.core.dept_normalizer import DEPT_COLLEGES, major_label_departments

MAJOR_TYPES = ("전공입문", "전공필수", "전공선택", "학부공통")
ETC = {"국제하계대학", "교직과목", "무관후보생교육(R.O.T.C.)", "군이러닝",
       "봉사와 리더십", "한국가톨릭교양공유대학"}
FACULTY = {"인문학부", "사회과학부", "지식융합미디어학부", "인문계", "사회과학계"}

DDL = """
DROP TABLE IF EXISTS course_categories;
CREATE TABLE course_categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       TEXT    NOT NULL,
    major_raw       TEXT,
    major_canonical TEXT,
    category        TEXT    NOT NULL,
    area_label      TEXT
);
CREATE INDEX idx_categories_course ON course_categories(course_id);
CREATE INDEX idx_categories_major  ON course_categories(major_canonical);
"""


def parse_category(raw: str) -> tuple[str | None, str, str | None]:
    """과목구분 원문 → (major_raw|None, category, area_label|None)."""
    s = re.sub(r"\(X\)\s*$", "", re.sub(r"\((?:19|20)\d{2}\)\s*$", "", raw.strip())).strip()
    if s == "":
        return (None, "미상", None)
    if s == "자유선택":
        return (None, "자유선택", None)
    if s == "공통필수" or s.endswith("의 이해") or s.endswith("의 탐구") or s.startswith("인간과 "):
        return (None, "교양", s)
    if s in ETC:
        return (None, "기타", s)
    if s in FACULTY:
        return (None, "계열입학표기", s)
    for t in MAJOR_TYPES:
        if s.endswith(t):
            return (s[: -len(t)].strip() or None, t, None)
    if s == "전공입문":
        return (None, "전공입문", None)
    return (s, "미분류", None)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    csvs = sorted(glob.glob(str(config.RAW_DIR / "과목구분_*.csv")))
    if not csvs:
        sys.exit(f"과목구분 CSV 없음: {config.RAW_DIR}")
    df = pd.read_csv(csvs[-1], dtype=str, keep_default_na=False, encoding="utf-8-sig")

    con = sqlite3.connect(config.DB_PATH)
    db_depts = {r[0] for r in con.execute("SELECT department FROM courses")}
    db_courses = {r[0] for r in con.execute("SELECT course_id FROM courses")}
    con.executescript(DDL)

    canon_cache: dict[str, list[str]] = {}
    rows: list[tuple] = []
    seen: set = set()
    unmapped: set[str] = set()

    for rec in df.to_dict(orient="records"):
        cid = str(rec["과목코드"]).strip()
        if not cid:
            continue
        major_raw, category, area = parse_category(str(rec["과목구분"]))

        if major_raw:
            if major_raw not in canon_cache:
                dl = major_label_departments(major_raw, db_depts)
                canon_cache[major_raw] = [d for d in dl if d not in DEPT_COLLEGES]  # college 제외
            depts = canon_cache[major_raw]
            if not depts:
                unmapped.add(major_raw)
                targets = [None]
            else:
                targets = depts
        else:
            targets = [None]

        for canon in targets:
            key = (cid, major_raw, canon, category, area)
            if key in seen:
                continue
            seen.add(key)
            rows.append(key)

    con.executemany(
        "INSERT INTO course_categories (course_id, major_raw, major_canonical, category, area_label)"
        " VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    con.commit()

    catc = Counter(r[3] for r in rows)
    print(f"course_categories: {len(rows):,}행 삽입 (원본 {len(df):,}행)")
    for k, v in catc.most_common():
        print(f"  {k}: {v}")
    print(f"미매핑 전공 {len(unmapped)}종: {sorted(unmapped)}")
    cov = len({r[0] for r in rows} & db_courses)
    print(f"DB 과목 {len(db_courses):,}개 중 성격 보유: {cov:,} ({cov / len(db_courses) * 100:.1f}%)")
    con.close()


if __name__ == "__main__":
    main()
