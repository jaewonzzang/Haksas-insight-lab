"""강의계획서 파싱 산출물(JSON) → course_prerequisites 병합 (선이수 사전 준비).

실행: uv run python scripts/build_syllabus_prereqs.py --input syllabi_parsed.json
입력: scripts/syllabus_parser.py 출력 — [{"course_id", "prerequisites_raw", ...}, ...].

강의계획서가 전부 입력되면 이 스크립트 1회 실행으로 선이수 트리가 채워지고,
선이수 충족도 점수(감산·factors 표시)는 기존 prereq_filter/scoring 로직이
그대로 계산한다 (2026-07-13 사용자 요청 — 데이터 대기 상태의 사전 로직).

병합 정책: 편람 유래 기존 트리 우선 보존 — 없는 과목만 추가.
⚠️ 강의계획서 '선수학습내용'은 자유 서술이 많아 파싱 실패 시 unparsed로 집계만
한다 (원문 형식은 실데이터 수령 후 검증 — prereq_parser 패턴 보강 여지).
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.parsers.prereq_parser import parse_prerequisites


# "선수과목 없음" 명시 표현 (2026-07-13 실PDF 6건 실측: "없음.", "no prerequisites needed")
_NO_PREREQ = re.compile(r"없음|없다|no\s+prereq", re.IGNORECASE)
_CODE_PREFIX = re.compile(r"^([A-Z]{2,5}\d{3,4})")


def _resolve_course_id(con: sqlite3.Connection, rec: dict) -> str | None:
    """course_id 결정: 파서 추출 → 영문 양식 폴백(과목명 내 코드, 파일명 과목명 유일 일치)."""
    cid = (rec.get("course_id") or "").split("/")[0].strip()
    if cid:
        return cid
    m = _CODE_PREFIX.match((rec.get("course_name") or "").strip())
    if m:
        return m.group(1)  # 영문 양식이 과목명 칸에 "CSE3030-01" 형태로 담는 경우
    parts = (rec.get("file") or "").rsplit("_", 2)  # "..._{과목명}_강의계획서.pdf"
    if len(parts) == 3:
        rows = con.execute(
            "SELECT DISTINCT course_id FROM courses WHERE course_name = ?", (parts[1],)
        ).fetchall()
        if len(rows) == 1:
            return rows[0][0]
    return None


def merge_syllabus_prereqs(
    con: sqlite3.Connection, records: list[dict]
) -> dict[str, int]:
    """반환 집계: inserted / skipped_existing / no_prereq / no_course / unparsed."""
    existing = {r[0] for r in con.execute("SELECT course_id FROM course_prerequisites")}
    known = {r[0] for r in con.execute("SELECT course_id FROM courses")}
    stats = {"inserted": 0, "skipped_existing": 0, "no_prereq": 0, "no_course": 0, "unparsed": 0}

    for rec in records:
        cid = _resolve_course_id(con, rec)
        raw = (rec.get("prerequisites_raw") or "").strip()
        if not cid or cid not in known:
            stats["no_course"] += 1
            continue
        if not raw or _NO_PREREQ.search(raw):
            stats["no_prereq"] += 1
            continue
        if cid in existing:
            stats["skipped_existing"] += 1
            continue

        parsed, _ = parse_prerequisites(cid, raw)
        if parsed is None:
            # 편람 패턴("선수과목 : ...")이 아닌 자유 서술 대비 재시도
            parsed, _ = parse_prerequisites(cid, f"선수과목 : {raw}")
        if parsed is None:
            stats["unparsed"] += 1
            continue

        con.execute(
            "INSERT INTO course_prerequisites (course_id, prereq_raw, prereq_tree_json) "
            "VALUES (:course_id, :prereq_raw, :prereq_tree_json)",
            parsed,
        )
        existing.add(cid)
        stats["inserted"] += 1

    con.commit()
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="강의계획서 선수과목 → course_prerequisites 병합")
    ap.add_argument("--input", required=True, help="syllabus_parser.py 출력 JSON 경로")
    ap.add_argument("--db", default=str(config.DB_PATH))
    args = ap.parse_args()

    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    con = sqlite3.connect(args.db)
    try:
        stats = merge_syllabus_prereqs(con, records)
    finally:
        con.close()
    print(stats)


if __name__ == "__main__":
    main()
