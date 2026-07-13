# W8-B: 강의계획서 신호 확장 — 개요→콘텐츠, 팀플·출석→선호 매칭 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 강의계획서 2개년치(공개 자료, 수령 확정) 투입에 대비해 ① 수업 개요 텍스트 → 콘텐츠 유사도 신호, ② 팀플 여부·출석(참여도) 비중 → "사용자 선호 매칭" 요인(배점 15%, 현재 N/A)을 활성화한다. 지금 있는 실PDF 6개로 개발·검증하고, 대량 PDF 도착 시 병합 스크립트 1회 실행으로 켜지는 구조.

**Architecture:** 파서(`scripts/syllabus_parser.py`)에 개요 추출 추가 → 병합 스크립트가 신규 `course_syllabi` 테이블에 적재(과목당 1행, 최신 우선) → 런타임은 `course_queries.syllabus_attrs`로 조회해 content_based(개요 결합)와 신규 `engines/recommender/preference`(선호 매칭)에 공급. 강의계획서 없는 과목은 기존 동작 유지(부분 커버리지): 콘텐츠는 기존 텍스트만, 선호 매칭은 해당 과목 N/A.

**계약 (프론트 W8-F와 병행 — 필드명 변경 금지):** `StudentInput`에 `prefer_team_project: bool=False`, `prefer_su_eval: bool=False`, `prefer_low_attendance: bool=False`. **S/U 선호는 전송만 받고 신호 미사용** — S/U 평가 여부 데이터가 어디에도 없음(파서·개설교과목정보 모두). 잔여 항목으로 보고에 명시.

## Global Constraints

- 모든 명령은 `backend/`에서 (`uv run ...`).
- 수정 허용: `scripts/syllabus_parser.py`, `scripts/build_syllabus_prereqs.py`, `scripts/build_course_db.py`(테이블 정의만), `app/db/queries/course_queries.py`, `app/engines/recommender/content_based.py`, `app/engines/recommender/preference.py`(신규), `app/cards/card_a.py`, `app/schemas/input.py`, `docs/API_SPEC.md`, `docs/DATA_SCHEMA.md`, 테스트, 이 플랜 체크박스.
- **`scoring.py`·`weights.py`·`docs/OPEN_QUESTIONS.md` 수정 금지.** `frontend/` 금지.
- `scripts/syllabus_parser.py`·`scripts/metadata_parser.py`는 EOL 노이즈 미커밋 상태 — **syllabus_parser.py는 이 플랜이 수정하는 파일이라 전체 EOL 정규화가 diff에 섞여도 그대로 커밋**(내용 동일 확인됨). metadata_parser.py는 건드리지 말 것. 그 외 기존 미커밋 변경(EOL 노이즈·`tests/integration/test_translator_live.py`)도 add 금지.
- 신호·매칭 규칙은 결정론. 새 매칭 규칙 수치는 잠정 prior로 주석 명시.
- 커밋은 명시적 `git add`, push 금지, 메시지 끝 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: 파서 개요 추출 (`extract_overview`)

**Files:**
- Modify: `backend/scripts/syllabus_parser.py`

**Interfaces:**
- Produces: 파서 출력 레코드에 `overview_text: str` 추가 (없으면 빈 문자열).

- [x] **Step 1: extract_overview 구현**

`extract_prerequisites` 아래에 추가:

```python
def extract_overview(text: str, lang: str) -> str:
    """"교과목 개요"/"수업개요"(ko) 또는 "Course Overview"(en) 섹션 본문."""
    if lang == "ko":
        match = re.search(
            r"(?:교과목 개요|수업개요)\s*\n+(.*?)(?=\n\s*\d+\.\s|\n\s*선수학습내용|\n\s*Ⅱ\.)",
            text, re.DOTALL,
        )
    else:
        match = re.search(
            r"Course\s*Overview\s*\n+(.*?)(?=\n\s*\d+\.\s|\n\s*Prerequisite|\n\s*II\.)",
            text, re.DOTALL | re.IGNORECASE,
        )
    if not match:
        return ""
    lines = [l.strip() for l in match.group(1).splitlines()]
    return "\n".join(l for l in lines if l).strip()
```

`parse_syllabus`의 반환 dict에 `"overview_text": extract_overview(text, lang),` 추가.

- [x] **Step 2: 실PDF 6개로 검증**

Run: `uv run python scripts/syllabus_parser.py --input_dir data/raw/syllabi --output data/processed/syllabi_parsed.json`
JSON에서 6건의 `overview_text` 확인 — **몇 건에서 비어 있지 않은 개요가 나오는지 세어 보고**, 0~2건뿐이면 실제 PDF 텍스트(`pdftotext -layout` 출력)를 열어 섹션 헤더 표기를 확인하고 정규식을 조정한다(목표: 한국어 양식 전부 + 영어 양식 최소 1건). 조정 내역은 보고에 기록.

- [x] **Step 3: Commit**

```bash
git add scripts/syllabus_parser.py
git commit -m "feat: 강의계획서 파서에 수업 개요 텍스트 추출 추가"
```

---

### Task 2: course_syllabi 테이블 + 병합 확장

**Files:**
- Modify: `backend/scripts/build_course_db.py` (테이블 DDL 추가)
- Modify: `backend/scripts/build_syllabus_prereqs.py` (attrs 병합 추가)
- Modify: `docs/DATA_SCHEMA.md` (테이블 문서화)
- Test: `backend/tests/unit/test_build_syllabus_prereqs.py` (추가)

**Interfaces:**
- Produces: 테이블 `course_syllabi(course_id TEXT PRIMARY KEY, overview_text TEXT, team_project TEXT, attendance_ratio REAL, source_file TEXT)` — team_project ∈ "required"|"optional"|"none".
- Produces: `merge_syllabus_attrs(con, records) -> dict[str, int]` (`upserted` / `no_course` 집계). main()이 prereq 병합과 함께 실행.

- [x] **Step 1: 실패하는 테스트 작성**

`test_build_syllabus_prereqs.py`에 추가:

```python
from scripts.build_syllabus_prereqs import merge_syllabus_attrs


def test_attrs_upsert_and_replace():
    con = _db()
    recs = [{
        "course_id": "CSE4070", "overview_text": "운영체제의 구조와 원리",
        "team_project": "none", "attendance_ratio": 0.1, "file": "a.pdf",
    }]
    stats = merge_syllabus_attrs(con, recs)
    assert stats["upserted"] == 1
    # 같은 과목 재병합(최신 계획서) → 교체
    recs[0]["overview_text"] = "개정판 개요"
    merge_syllabus_attrs(con, recs)
    row = con.execute(
        "SELECT overview_text, team_project FROM course_syllabi WHERE course_id='CSE4070'"
    ).fetchone()
    assert row == ("개정판 개요", "none")


def test_attrs_unknown_course_skipped():
    con = _db()
    stats = merge_syllabus_attrs(con, [{"course_id": "NOPE999", "overview_text": "x"}])
    assert stats["upserted"] == 0 and stats["no_course"] == 1
```

Run: FAIL(ImportError) 확인.

- [x] **Step 2: 구현**

`build_syllabus_prereqs.py`에 추가 (모듈 docstring도 "선수과목+개요·팀플·출석 속성 병합"으로 갱신):

```python
_SYLLABI_DDL = (
    "CREATE TABLE IF NOT EXISTS course_syllabi ("
    "course_id TEXT PRIMARY KEY, overview_text TEXT, team_project TEXT, "
    "attendance_ratio REAL, source_file TEXT)"
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
            "INSERT OR REPLACE INTO course_syllabi VALUES (?, ?, ?, ?, ?)",
            (
                cid,
                (rec.get("overview_text") or "").strip(),
                rec.get("team_project") or "none",
                float(rec.get("attendance_ratio") or 0.0),
                rec.get("file") or "",
            ),
        )
        stats["upserted"] += 1
    con.commit()
    return stats
```

main()에서 prereq 병합 후 `attrs = merge_syllabus_attrs(con, records)` 실행, 두 집계 모두 print.

`build_course_db.py`: 기존 테이블 생성부에 `_SYLLABI_DDL`과 동일한 DDL 추가 (새 빌드에도 테이블 존재 — 데이터 적재는 병합 스크립트 몫). `docs/DATA_SCHEMA.md`에 테이블 섹션 추가(컬럼·출처 = 강의계획서 병합, 행수는 "병합 실행에 따라 가변").

- [x] **Step 3: 통과 + 실 병합**

Run: `uv run pytest tests/unit/test_build_syllabus_prereqs.py -v` — PASS.
Run: `uv run python scripts/build_syllabus_prereqs.py --input data/processed/syllabi_parsed.json` — upserted 수 확인(과목 식별되는 5건 기대).

- [x] **Step 4: Commit**

```bash
git add scripts/build_syllabus_prereqs.py scripts/build_course_db.py tests/unit/test_build_syllabus_prereqs.py ../docs/DATA_SCHEMA.md
git commit -m "feat: course_syllabi 테이블 + 강의계획서 속성(개요·팀플·출석) 병합"
```

---

### Task 3: 개요 텍스트 → 콘텐츠 유사도 결합

**Files:**
- Modify: `backend/app/db/queries/course_queries.py`
- Modify: `backend/app/engines/recommender/content_based.py`
- Modify: `backend/app/cards/card_a.py`
- Test: `backend/tests/unit/engines/test_content_based.py` (있으면 추가, 없으면 신규)

**Interfaces:**
- Produces: `course_queries.syllabus_attrs(con, course_ids) -> dict[str, sqlite3.Row]` — course_syllabi 조회 (테이블은 Task 2가 보장).
- Produces: `content_based.score(taken_rows, pool_rows, overviews: Mapping[str, str] | None = None)` — overview가 있는 과목은 텍스트에 결합. 기본 None = 기존 동작(기존 테스트 불변).

- [x] **Step 1: 실패하는 테스트**

```python
def test_overview_text_changes_similarity():
    taken = [{"course_id": "T1", "course_name": "운영체제", "description_raw": ""}]
    pool = [
        {"course_id": "P1", "course_name": "과목甲", "description_raw": ""},
        {"course_id": "P2", "course_name": "과목乙", "description_raw": ""},
    ]
    overviews = {"P1": "운영체제 프로세스 스케줄링 심화", "P2": "르네상스 미술사"}
    out = score(taken, pool, overviews)
    assert out["P1"] > out["P2"]
```

- [x] **Step 2: 구현**

`course_queries.py`:

```python
def syllabus_attrs(
    con: sqlite3.Connection, course_ids: Sequence[str]
) -> dict[str, sqlite3.Row]:
    """course_syllabi 속성 (강의계획서 병합분만 존재 — 부분 커버리지)."""
    if not course_ids:
        return {}
    marks = ", ".join("?" for _ in course_ids)
    rows = con.execute(
        f"SELECT * FROM course_syllabi WHERE course_id IN ({marks})", tuple(course_ids)
    ).fetchall()
    return {r["course_id"]: r for r in rows}
```

`content_based.py`:

```python
def _text(row: Mapping, overviews: Mapping[str, str]) -> str:
    base = f"{row['course_name'] or ''} {row['description_raw'] or ''}"
    return f"{base} {overviews.get(row['course_id'], '')}".strip()


def score(taken_rows, pool_rows, overviews: Mapping[str, str] | None = None) -> dict[str, float]:
    ov = overviews or {}
    # docs: 강의계획서 개요가 있으면 결합 (2026-07-13) — 이하 docs 결합만 변경
    docs = [_text(r, ov) for r in taken_rows] + [_text(r, ov) for r in pool_rows]
```

`card_a.build`: 신호 계산 직전에 attrs 조회 후 전달:

```python
    attrs = course_queries.syllabus_attrs(con, [*pool_ids, *sorted(taken)])
    overviews = {cid: a["overview_text"] for cid, a in attrs.items() if a["overview_text"]}
    content = content_based.score(taken_rows, pool, overviews)
```

(`attrs`는 Task 4의 선호 매칭도 재사용.)

- [x] **Step 3: 통과 + 회귀**

Run: `uv run pytest tests/unit -q` — 실패 0.

- [x] **Step 4: Commit**

```bash
git add app/db/queries/course_queries.py app/engines/recommender/content_based.py app/cards/card_a.py tests/unit/engines/test_content_based.py
git commit -m "feat: 강의계획서 개요 텍스트를 콘텐츠 유사도 신호에 결합"
```

---

### Task 4: 사용자 선호 매칭 요인 활성화

**Files:**
- Modify: `backend/app/schemas/input.py` (3 필드)
- Create: `backend/app/engines/recommender/preference.py`
- Modify: `backend/app/cards/card_a.py`
- Modify: `docs/API_SPEC.md` (Request 3행)
- Test: `backend/tests/unit/engines/test_preference.py` (신규), `backend/tests/integration/test_analyze_flow.py` (페이로드 확장)

**Interfaces:**
- Produces: `preference.score(prefer_team_project: bool, prefer_low_attendance: bool, attrs_by_id: Mapping[str, Mapping]) -> dict[str, float]` — 선택된 선호 없거나 attrs 비면 `{}`. weights.py의 라벨 `"사용자 선호 매칭"` 그대로 사용.

- [x] **Step 1: 실패하는 테스트**

`test_preference.py`:

```python
"""선호 매칭 — 팀플·출석 비중 (잠정 prior, 2026-07-13)."""

from app.engines.recommender import preference


ATTRS = {
    "C1": {"team_project": "required", "attendance_ratio": 0.05},
    "C2": {"team_project": "none", "attendance_ratio": 0.30},
    "C3": {"team_project": "optional", "attendance_ratio": 0.15},
}


def test_team_preference_tiers():
    out = preference.score(True, False, ATTRS)
    assert out["C1"] == 100.0 and out["C3"] == 50.0 and out["C2"] == 0.0


def test_low_attendance_tiers():
    out = preference.score(False, True, ATTRS)
    assert out["C1"] == 100.0  # 참여도 5% ≤ 10%
    assert out["C3"] == 50.0   # ≤ 20%
    assert out["C2"] == 0.0


def test_both_prefs_averaged():
    out = preference.score(True, True, ATTRS)
    assert out["C1"] == 100.0 and out["C3"] == 50.0


def test_no_selection_or_no_attrs_empty():
    assert preference.score(False, False, ATTRS) == {}
    assert preference.score(True, True, {}) == {}
```

- [x] **Step 2: 구현**

`schemas/input.py`에 (year 아래):

```python
    prefer_team_project: bool = Field(False, description="팀플레이 선호")
    prefer_su_eval: bool = Field(False, description="S/U 평가 선호 — 재료 없음, 현재 신호 미사용")
    prefer_low_attendance: bool = Field(False, description="출석(참여도) 비중 낮음 선호")
```

`preference.py`:

```python
"""사용자 선호 매칭 signal: 강의계획서 속성(팀플·참여도) ↔ 폼 선호 (0~100).

⚠️ 매칭 티어는 잠정 prior — 실데이터/피드백 후 조정. S/U 선호는 재료 부재로 미사용.
"""

from typing import Mapping


def _team(team_project: str) -> float:
    return {"required": 100.0, "optional": 50.0}.get(team_project, 0.0)


def _low_attendance(ratio: float) -> float:
    if ratio <= 0.10:
        return 100.0
    if ratio <= 0.20:
        return 50.0
    return 0.0


def score(
    prefer_team_project: bool,
    prefer_low_attendance: bool,
    attrs_by_id: Mapping[str, Mapping],
) -> dict[str, float]:
    if not (prefer_team_project or prefer_low_attendance):
        return {}
    out: dict[str, float] = {}
    for cid, a in attrs_by_id.items():
        parts: list[float] = []
        if prefer_team_project:
            parts.append(_team(a["team_project"]))
        if prefer_low_attendance:
            parts.append(_low_attendance(a["attendance_ratio"]))
        out[cid] = round(sum(parts) / len(parts), 1)
    return out
```

`card_a.build` 신호부에 (학년 적합도 아래, Task 3의 `attrs` 재사용 — pool에 있는 과목만):

```python
    pool_attrs = {cid: attrs[cid] for cid in pool_ids if cid in attrs}
    pref = preference.score(
        student.prefer_team_project, student.prefer_low_attendance, pool_attrs
    )
    if pref:
        signals_by_label["사용자 선호 매칭"] = pref
```

임포트에 `preference` 추가. `docs/API_SPEC.md` Request 테이블에 3행 추가 (S/U는 "현재 신호 미사용" 명기).

- [x] **Step 3: 통과 + 통합 회귀**

`test_analyze_flow.py` 페이로드에 `"prefer_team_project": True, "prefer_su_eval": True, "prefer_low_attendance": True` 추가 (기존 assertion 불변 — 6개 계획서 과목이 대부분 이수 과목이라 풀 커버리지가 적어 요인이 N/A일 수 있음: 응답 정상 여부만 보장하면 됨).
Run: `uv run pytest tests/unit tests/integration -q --ignore=tests/integration/test_translator_live.py` — 실패 0.

- [x] **Step 4: Commit**

```bash
git add app/schemas/input.py app/engines/recommender/preference.py app/cards/card_a.py tests/unit/engines/test_preference.py tests/integration/test_analyze_flow.py ../docs/API_SPEC.md
git commit -m "feat: 사용자 선호 매칭 요인 활성화 — 팀플·출석 비중 (S/U는 재료 부재 미사용)"
```

---

### Task 5: 최종 검증 + 플랜 체크박스

- [x] **Step 1: 전체 회귀 + 스모크**

Run: `uv run pytest tests/unit tests/integration -q --ignore=tests/integration/test_translator_live.py` — 실패 0.
uvicorn 스모크: 학생 A 페이로드(1전공 아트&테크놀로지학과·2전공 컴퓨터공학과·3학년·32과목·선호 3개 true) POST /analyze → 200, 응답의 factors에서 "사용자 선호 매칭" kind 확인(N/A여도 무방 — 커버리지 문제), 콘텐츠 유사도 값 변화 여부 기록.

- [x] **Step 2: 체크박스 커밋**

```bash
git add ../docs/superpowers/plans/2026-07-13-backend-syllabus-signals.md
git commit -m "docs: W8-B 플랜 체크박스 갱신"
```

완료 보고: ① 커밋 해시, ② 테스트 수치, ③ 개요 추출 성공 건수(6개 중)와 정규식 조정 내역, ④ course_syllabi 병합 건수, ⑤ 스모크 결과, ⑥ 플랜 이탈 사항.
