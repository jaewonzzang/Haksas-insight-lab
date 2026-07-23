"""강의계획서 파싱 산출물(JSON) → course_prerequisites 병합 (선이수 사전 준비).

실행: uv run python scripts/build_syllabus_prereqs.py --input syllabi_parsed.json
입력: scripts/syllabus_parser.py 출력 — [{"course_id", "prerequisites_raw", ...}, ...].

강의계획서가 전부 입력되면 이 스크립트 1회 실행으로 선이수 트리가 채워지고,
선이수 충족도 점수(감산·factors 표시)는 기존 prereq_filter/scoring 로직이
그대로 계산한다 (2026-07-13 사용자 요청 — 데이터 대기 상태의 사전 로직).

병합 정책: 편람 유래 기존 트리 우선 보존 — 없는 과목만 추가.
자유 서술 처리 (2026-07-23 파서 보강): 코드 파스 실패 시 ① 부정 표현이면 무선수,
② 아니면 DB 과목명 실명 매칭 폴백(_match_prose_names) — 그래도 실패하면 unparsed.
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


# "선수과목 없음" 명시 표현 (2026-07-13 실PDF 실측 + 2026-07-23 unparsed 809건 실측 확장:
# "None", "n/a", "필요로 하지 않는다", "선수 과목은 없으며" 등)
_NO_PREREQ = re.compile(
    r"없음|없다|없습니|없으며|없고|무관|않는다|않습니다|않음|않으며|않으나|않다"
    r"|no\s+prereq|not\s+required|\bnone\b|\bn/?a\b|\bno\b[^.\n]*\brequired\b",
    re.IGNORECASE,
)
_CODE_PREFIX = re.compile(r"^([A-Z]{2,5}\d{3,4})")
# 강의계획서 PDF 추출 시 '수업방법' 표가 선수학습 칸에 섞여 들어오는 양식 누수 — 이후 절단
_FORM_NOISE = re.compile(r"수업\s*방법")
# 일반명사로 흔히 쓰여 오매칭되는 과목명 (실측: "고교/중등/수학과 교육과정" 언급 7건 중 5건 오신호)
_GENERIC_NAMES = {"교육과정"}


def _course_name_index(con: sqlite3.Connection) -> tuple[dict[str, list[str]], dict[str, str]]:
    """(공백 제거 과목명 → 코드 리스트, 코드 → 공백 제거 과목명). 4자 미만·일반명사형 제외."""
    name_to_ids: dict[str, list[str]] = {}
    id_to_name: dict[str, str] = {}
    for cid, cname in con.execute("SELECT course_id, course_name FROM courses"):
        key = re.sub(r"\s+", "", cname or "")
        id_to_name[cid] = key
        if len(key) >= 4 and key not in _GENERIC_NAMES:
            name_to_ids.setdefault(key, []).append(cid)
    return name_to_ids, id_to_name


def _match_prose_names(
    cid: str, raw: str, name_to_ids: dict[str, list[str]], self_key: str
) -> dict | None:
    """자유 서술에서 DB 과목명 실명 매칭 → 선수 트리 (코드 파스 실패 시 폴백).

    공백 제거 부분일치. 위치 기반 최장일치 — 다른 매칭 구간에 완전히 포함되는
    구간만 제거하므로 "일반화학 I, 일반화학 II"처럼 겹치는 이름이 둘 다 실재하면
    둘 다 남는다. 동명이코드(캠퍼스/학과 중복)는 OR 노드. 자기 자신은 제외.
    """
    noise = _FORM_NOISE.search(raw)
    if noise:
        raw = raw[: noise.start()].strip()
    compact = re.sub(r"\s+", "", raw)
    spans: list[tuple[int, int, str]] = []
    for key in name_to_ids:
        for m in re.finditer(re.escape(key), compact):
            spans.append((m.start(), m.end(), key))
    # 자기 이름은 트리에 안 넣지만 스팬은 남긴다 — 자기 이름 안의 하위 이름 억제용
    # (예: 고등미적분학I 계획서의 "고등미적분학I" 언급에서 "미적분학I"을 추출하면 안 됨)
    keys: list[str] = []  # 첫 등장 순서 유지
    for s, e, key in sorted(spans):
        contained = any(
            s2 <= s and e <= e2 and (s2, e2) != (s, e) for s2, e2, _ in spans
        )
        if not contained and key != self_key and key not in keys:
            keys.append(key)
    children: list[dict] = []
    for key in keys:
        codes = [c for c in name_to_ids[key] if c != cid]
        if len(codes) == 1:
            children.append({"type": "course", "code": codes[0]})
        elif codes:
            children.append(
                {"type": "or", "children": [{"type": "course", "code": c} for c in sorted(codes)]}
            )
    if not children:
        return None
    tree = children[0] if len(children) == 1 else {"type": "and", "children": children}
    return {
        "course_id": cid,
        "prereq_raw": raw,
        "prereq_tree_json": json.dumps(tree, ensure_ascii=False),
    }


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
    """반환 집계: inserted / inserted_prose(부분집합) / skipped_existing / no_prereq / no_course / unparsed."""
    existing = {r[0] for r in con.execute("SELECT course_id FROM course_prerequisites")}
    known = {r[0] for r in con.execute("SELECT course_id FROM courses")}
    name_to_ids, id_to_name = _course_name_index(con)
    stats = {
        "inserted": 0, "inserted_prose": 0, "skipped_existing": 0,
        "no_prereq": 0, "no_course": 0, "unparsed": 0,
    }

    for rec in records:
        cid = _resolve_course_id(con, rec)
        raw = (rec.get("prerequisites_raw") or "").strip()
        if not cid or cid not in known:
            stats["no_course"] += 1
            continue
        if not raw:
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
            # 코드 명시가 없는 산문 — 부정 표현("없음"/"필요하지 않다")이면 무선수,
            # 아니면 과목명 실명 매칭 폴백. 순서 중요: 부정 명시 산문에서 언급된
            # 과목을 선수로 오추출하지 않기 위해 무선수 판정이 먼저다.
            if _NO_PREREQ.search(raw):
                stats["no_prereq"] += 1
                continue
            parsed = _match_prose_names(cid, raw, name_to_ids, id_to_name.get(cid, ""))
            if parsed is not None:
                stats["inserted_prose"] += 1
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


_SYLLABI_DDL = (
    "CREATE TABLE IF NOT EXISTS course_syllabi ("
    "course_id TEXT PRIMARY KEY, overview_text TEXT, team_project TEXT, "
    "attendance_ratio REAL, presentation_ratio REAL, source_file TEXT)"
)


def merge_syllabus_attrs(con: sqlite3.Connection, records: list[dict]) -> dict[str, int]:
    """개요·팀플·출석 속성 upsert (과목당 1행, 재실행 시 최신 계획서로 교체)."""
    con.execute(_SYLLABI_DDL)
    known = {r[0] for r in con.execute("SELECT course_id FROM courses")}
    stats = {"upserted": 0, "no_course": 0}
    for rec in records:
        cid = _resolve_course_id(con, rec)
        if not cid or cid not in known:
            stats["no_course"] += 1
            continue
        con.execute(
            "INSERT OR REPLACE INTO course_syllabi VALUES (?, ?, ?, ?, ?, ?)",
            (
                cid,
                (rec.get("overview_text") or "").strip(),
                rec.get("team_project") or "none",
                float(rec.get("attendance_ratio") or 0.0),
                round(float(rec.get("presentation_ratio") or 0.0), 2),
                rec.get("file") or "",
            ),
        )
        stats["upserted"] += 1
    con.commit()
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(
        description="강의계획서 선수과목 + 속성(개요·팀플·출석) → DB 병합"
    )
    ap.add_argument("--input", required=True, help="syllabus_parser.py 출력 JSON 경로")
    ap.add_argument("--db", default=str(config.DB_PATH))
    args = ap.parse_args()

    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    con = sqlite3.connect(args.db)
    try:
        prereq_stats = merge_syllabus_prereqs(con, records)
        attr_stats = merge_syllabus_attrs(con, records)
    finally:
        con.close()
    print("prereq:", prereq_stats)
    print("attrs:", attr_stats)


if __name__ == "__main__":
    main()
