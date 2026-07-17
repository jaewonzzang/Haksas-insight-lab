"""학사팀 수강내역(암호화 xlsx) → AlumniRecord[] 빌드.

입력: data/external/*수강내역*.xlsx — 컬럼 9개
      학년도 | 학기 | 과목코드 | 과목명 | 학번_암호화 | 소속학과 | 1전공 | 2전공 | 3전공
출력: data/processed/alumni.json (AlumniRecord[]) — RealAlumniSource 가 로드.

암호는 리포에 두지 않는다. 환경변수 ENROLLMENT_XLSX_PASSWORD 또는 --password.

매핑 주의 (docs/OPEN_QUESTIONS.md A1/A14/A15):
  - department/majors 는 학생의 **최신 학기** 값 (기간 중 변경 2,258명 — A15 잠정 결정)
  - career 는 원본에 진로 컬럼이 없어 항상 None (A14)
  - Major.credits 는 과목구분(전필/전선/교양)이 없어 산출 불가 → None

실행: uv run python scripts/build_alumni_from_enrollment.py --password '***'
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path

import msoffcrypto
import openpyxl

# 프로젝트 미설치 venv 에서 scripts/ 직접 실행을 위한 경로 부트스트랩.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.adapters.alumni_types import AlumniRecord, Enrollment, Major

_TERM = {"1학기": 1, "2학기": 2}  # 계절학기(하계/동계) → None
_ROLES = ("primary", "double", "triple")
# 이력 완결(졸업 추정) 판정: 정규학기 N개 이상 등록 + 마지막 등록이 데이터 창 끝이 아님.
# 조기졸업 7학기를 포함하려고 7. 실측(2026-07-17): 14,942명 중 1,919명(12.8%).
_COMPLETE_MIN_SEMESTERS = 7


def _decrypt(path: Path, password: str) -> io.BytesIO:
    buf = io.BytesIO()
    with path.open("rb") as f:
        office = msoffcrypto.OfficeFile(f)
        office.load_key(password=password)
        office.decrypt(buf)
    buf.seek(0)
    return buf


def read_rows(xlsx: io.BytesIO):
    """복호화된 xlsx → 정규화 튜플. (year, term, course_id, student, dept, majors)"""
    ws = openpyxl.load_workbook(xlsx, read_only=True).worksheets[0]
    it = ws.iter_rows(values_only=True)
    next(it)  # 헤더
    for year, term, code, _name, student, dept, m1, m2, m3 in it:
        if not student or not code:
            continue
        yield year, str(term), str(code).split("-")[0], str(student), dept, (m1, m2, m3)


def _regular_semesters(items: list[Enrollment]) -> list[tuple[int, int]]:
    """등록한 정규학기 (계절학기 제외), 시간순."""
    return sorted({(e.year_taken, e.term_taken) for e in items if e.term_taken})


def build(rows) -> list[AlumniRecord]:
    # 학생별로 (학년도, 학기순번) 최신 행의 소속/전공을 채택 → A15 잠정 결정
    latest: dict[str, tuple[tuple[int, int], str, tuple]] = {}
    enrollments: dict[str, list[Enrollment]] = {}

    for year, term, code, student, dept, majors in rows:
        t = _TERM.get(term)
        enrollments.setdefault(student, []).append(
            Enrollment(course_id=code, year_taken=year, term_taken=t)
        )
        rank = (year, t or 0)
        if student not in latest or rank > latest[student][0]:
            latest[student] = (rank, dept, majors)

    # 데이터 창의 마지막 정규학기 = "현재". 여기 등록 중이면 재학생.
    now = max(
        (s for items in enrollments.values() for s in _regular_semesters(items)),
        default=None,
    )

    records = []
    for student, items in enrollments.items():
        _, dept, majors = latest[student]
        sems = _regular_semesters(items)
        records.append(
            AlumniRecord(
                alumni_id=student,
                department=(dept or "").strip(),
                majors=[
                    Major(label=str(m).strip(), role=role)
                    for role, m in zip(_ROLES, majors)
                    if m and str(m).strip()
                ],
                enrollment=items,
                career=None,  # 원본에 진로 컬럼 없음 (A14)
                history_complete=bool(sems)
                and len(sems) >= _COMPLETE_MIN_SEMESTERS
                and sems[-1] != now,
            )
        )
    records.sort(key=lambda r: r.alumni_id)
    return records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=None, help="기본: data/external 의 *수강내역*.xlsx")
    ap.add_argument("--password", default=os.getenv("ENROLLMENT_XLSX_PASSWORD", ""))
    ap.add_argument("--out", type=Path, default=config.PROCESSED_DIR / "alumni.json")
    args = ap.parse_args()

    src = args.source
    if src is None:
        found = sorted(config.EXTERNAL_DIR.glob("*수강내역*.xlsx"))
        if not found:
            sys.exit(f"수강내역 xlsx 없음: {config.EXTERNAL_DIR}")
        src = found[0]
    if not args.password:
        sys.exit("암호 필요 — --password 또는 ENROLLMENT_XLSX_PASSWORD")

    records = build(read_rows(_decrypt(src, args.password)))
    args.out.write_text(
        json.dumps([r.model_dump() for r in records], ensure_ascii=False),
        encoding="utf-8",
    )
    n_enr = sum(len(r.enrollment) for r in records)
    print(f"입력: {src.name}")
    print(f"학생 {len(records):,}명 / 수강 {n_enr:,}행 → {args.out}")
    print(f"크기: {args.out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
