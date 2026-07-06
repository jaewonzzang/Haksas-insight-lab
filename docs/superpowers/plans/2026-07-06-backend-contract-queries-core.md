# W2: 계약 미러 + db 쿼리 + core 평가 계층 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ① `schemas/cards.py`를 `frontend/src/types/api.ts` 확장 계약으로 미러하고, ② `db/connection` + `db/queries/{course,prereq}`를 구현하고, ③ `core/{prereq_eval, alias_resolver, dept_normalizer}` 평가 계층을 구현한다. W3(추천 엔진+카드 A)의 토대.

**Architecture:** 계약 진실원 = `types/api.ts` (2026-07-06 확정, `docs/OPEN_QUESTIONS.md` 결정 완료 참조). 쿼리는 `sqlite3.Connection`을 첫 인자로 받는 순수 SELECT 함수(테스트는 in-memory DB + schema.sql). core는 DB 접근 없는 순수 함수 — 별칭 데이터는 쿼리 결과를 인자로 주입받는다. `prereq_eval`은 W3의 `scoring.score_candidate(signals, prereq_fulfillment: float | None)`(0~100 스케일)에 바로 넣을 수 있는 충족률을 산출한다.

**Tech Stack:** Python 3.12 + uv, pydantic v2, raw sqlite3, pytest.

## Global Constraints

- 모든 명령은 `backend/` 디렉토리에서 실행 (`uv run ...`).
- `engines/` = 정형 결과만·자연어 금지, `core/` = 구조 → 평가 (CLAUDE.md 책임 경계). 이 플랜은 `engines/`·`cards/`·`api/`·`llm/`을 건드리지 않는다.
- `frontend/` 수정 금지. docs 수정은 Task 1의 `docs/API_SPEC.md`만.
- 계약 미러의 필드명·optional 여부는 `frontend/src/types/api.ts`와 **정확히 일치**해야 한다 (구현 전 해당 파일을 직접 읽고 대조할 것).
- 기존 스텁 파일들의 모듈 docstring은 유지·현행화 (통째로 삭제 금지).
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: 계약 미러 — `schemas/cards.py` 확장 (TDD)

**Files:**
- Modify: `backend/app/schemas/cards.py` (전면 교체)
- Modify: `docs/API_SPEC.md` (Response 요약 블록만 갱신)
- Test: `backend/tests/unit/test_cards_schema.py` (신규)

**Interfaces:**
- Produces: `DashboardResponse{profile, kpi, card_a, card_c, card_d, cluster}` 및 하위 모델 전부 — W3~W6의 카드/API가 소비. 모델명·필드는 아래 코드 그대로.

- [x] **Step 1: 실패하는 테스트 작성**

`tests/unit/test_cards_schema.py`:

```python
"""cards.py ↔ frontend/src/types/api.ts 계약 미러 검증."""

from app.schemas.cards import DashboardResponse


def _empty_dashboard() -> dict:
    # frontend src/mock/profiles.fixture.ts 의 emptyDashboard 와 동일 형태
    return {
        "profile": {
            "name": "학생 B", "department": "—", "year": "—",
            "analysis_date": "—", "report_semester": "2026-1학기",
            "next_semester": "2026-2",
        },
        "kpi": {"earned_credits": 0, "gpa": None, "gpa_scale": 4.3, "similar_alumni_n": 0},
        "card_a": {"major": [], "general": [], "candidates": []},
        "card_c": {"cohort_label": "—", "entries": [], "baseline_note": ""},
        "card_d": {"similar_label": "—", "sample_size": 0, "entries": [],
                   "sub_title": "", "sub_chips": [], "pattern_summary": ""},
        "cluster": {"factors": [], "common_courses": [], "career_patterns": [], "summary": ""},
    }


def test_empty_dashboard_validates():
    resp = DashboardResponse.model_validate(_empty_dashboard())
    assert resp.kpi.gpa is None
    assert resp.card_a.candidates == []


def test_populated_course_and_pathway():
    data = _empty_dashboard()
    data["card_a"]["major"] = [{
        "course_id": "CSE3013", "course_name": "컴퓨터그래픽스", "credit": 3.0,
        "grade": "강추", "score_percent": 87, "reason_short": "사유",
        "kind": "major", "kind_label": "전공선택", "area_label": None,
        "factors": [{"label": "코호트 선호도", "weight_percent": 72,
                     "contribution": "+26", "kind": "pos"}],
        "why_summary": "요약",
    }]
    data["card_c"]["entries"] = [{
        "id": "p1", "label": "복수전공", "count": 58, "share_percent": 31.5,
        "bar_percent": 100, "detail_label": "복수전공 상세",
        "credits": {"major1": 36, "major2": 36, "major3": None},
    }]
    data["card_d"]["entries"] = [{
        "cluster_label": "IT 취업", "type": "job", "count": 12, "share_percent": 44.4,
    }]
    resp = DashboardResponse.model_validate(data)
    assert resp.card_a.major[0].grade == "강추"
    entry = resp.card_c.entries[0]
    assert entry.tag is None and entry.dim is False  # ts optional 필드 기본값
```

- [x] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/test_cards_schema.py -v`
Expected: FAIL (`profile` 필드 없음 등 ValidationError).

- [x] **Step 3: cards.py 전면 교체**

```python
"""카드 A/C/D 응답 Pydantic 모델 + 통합 dashboard 응답.

진실원: frontend/src/types/api.ts 의 확장 계약을 미러한다 (2026-07-06 확정).
변경 시 types/api.ts 와 함께 갱신 (수동 동기화 — OPEN_QUESTIONS A12).
"""

from typing import Literal

from pydantic import BaseModel, Field

RecommendationGrade = Literal["강추", "고려", "유보"]
CourseKind = Literal["major", "common", "free"]  # 전공 / 공통선택 / 자유선택
FactorKind = Literal["pos", "neg", "mid", "na"]  # why-panel 기여도 색
CareerType = Literal["job", "grad", "other"]


class RecommendationFactor(BaseModel):
    label: str
    weight_percent: float = Field(..., ge=0, le=100, description="막대 폭 0~100")
    contribution: str = Field(..., description='"+26" / "−18" / "N/A"')
    kind: FactorKind


class RecommendedCourse(BaseModel):
    course_id: str
    course_name: str
    credit: float | None
    grade: RecommendationGrade
    score_percent: int = Field(..., ge=0, le=100, description="추천도 %")
    reason_short: str = Field(..., description="LLM 통역 1줄 사유")
    kind: CourseKind
    kind_label: str = Field(..., description='모달 구분 표기, 예: "전공선택" / "교양"')
    area_label: str | None = None
    factors: list[RecommendationFactor] = Field(..., description="why-panel 기여도 분해")
    why_summary: str = Field(..., description="why-panel 한 줄 요약")


class CardA(BaseModel):
    """추천 과목 (전공/교양 2단). candidates = '과목 더 보기' 모달 전체 목록."""

    major: list[RecommendedCourse]
    general: list[RecommendedCourse]
    candidates: list[RecommendedCourse]


class PathwayCredits(BaseModel):
    major1: float | None
    major2: float | None
    major3: float | None


class PathwayEntry(BaseModel):
    id: str
    label: str
    tag: str | None = None
    count: int
    share_percent: float
    bar_percent: float = Field(..., description="막대 폭 (최다 대비 상대값)")
    detail_label: str
    credits: PathwayCredits
    dim: bool = False


class CardC(BaseModel):
    """다전공 경로 분포 + 추가 이수 학점."""

    cohort_label: str
    entries: list[PathwayEntry]
    baseline_note: str = Field(..., description="학칙 발췌")


class CareerEntry(BaseModel):
    cluster_label: str
    type: CareerType
    count: int
    share_percent: float


class CareerSubChip(BaseModel):
    label: str
    n: int


class CardD(BaseModel):
    """유사 졸업생 진로 분포 + 패턴 요약."""

    similar_label: str
    sample_size: int
    entries: list[CareerEntry]
    sub_title: str
    sub_chips: list[CareerSubChip]
    pattern_summary: str = Field(..., description="LLM 1단락 통역")


class SimilarityFactor(BaseModel):
    label: str
    percent: float


class CommonCourse(BaseModel):
    name: str
    n: int


class CareerPattern(BaseModel):
    label: str
    type: CareerType
    text: str


class ClusterEvidence(BaseModel):
    """유사 판정 근거 (cluster 패널)."""

    factors: list[SimilarityFactor]
    common_courses: list[CommonCourse]
    career_patterns: list[CareerPattern]
    summary: str


class StudentProfile(BaseModel):
    name: str
    department: str
    year: str
    analysis_date: str
    report_semester: str = Field(..., description='헤더 subtitle, 예: "2026-1학기"')
    next_semester: str = Field(..., description='추천 대상 학기, 예: "2026-2"')


class KpiStrip(BaseModel):
    earned_credits: float
    gpa: float | None
    gpa_scale: float
    similar_alumni_n: int


class DashboardResponse(BaseModel):
    """POST /analyze 통합 응답."""

    profile: StudentProfile
    kpi: KpiStrip
    card_a: CardA
    card_c: CardC
    card_d: CardD
    cluster: ClusterEvidence
```

교체 후 `frontend/src/types/api.ts`를 읽고 필드명/optional/타입을 1:1 대조할 것 (누락·오타 발견 시 이 코드가 아니라 types/api.ts 기준으로 수정).

- [x] **Step 4: 통과 + 회귀 확인**

Run: `uv run pytest tests/unit -q`
Expected: 실패 0. (기존 `RecommendedCourse`/`CardA` 등을 import 하는 코드는 현재 없음 — grep으로 `from app.schemas.cards import` 사용처 확인.)

- [x] **Step 5: API_SPEC.md Response 블록 갱신**

`docs/API_SPEC.md`의 Response 코드 블록을 다음으로 교체 (나머지 섹션 유지):

```
{
  profile: { name, department, year, analysis_date, report_semester, next_semester },
  kpi: { earned_credits, gpa, gpa_scale, similar_alumni_n },
  card_a: { major: RecommendedCourse[], general: RecommendedCourse[], candidates: RecommendedCourse[] },
  card_c: { cohort_label, entries: PathwayEntry[], baseline_note },
  card_d: { similar_label, sample_size, entries: CareerEntry[], sub_title, sub_chips, pattern_summary },
  cluster: { factors, common_courses, career_patterns, summary }
}
```

- [x] **Step 6: Commit**

```bash
git add app/schemas/cards.py tests/unit/test_cards_schema.py docs/API_SPEC.md
git commit -m "feat: 카드 응답 스키마를 types/api.ts 확장 계약으로 미러"
```

---

### Task 2: `db/connection` + 쿼리 (TDD)

**Files:**
- Modify: `backend/app/db/connection.py`
- Modify: `backend/app/db/queries/course_queries.py`
- Modify: `backend/app/db/queries/prereq_queries.py`
- Test: `backend/tests/unit/db/__init__.py` (빈 파일), `backend/tests/unit/db/test_queries.py` (신규)

**Interfaces:**
- Produces (W3 엔진·카드가 소비):
  - `get_connection(db_path: Path | None = None) -> sqlite3.Connection` (기본 `config.DB_PATH`, `row_factory=sqlite3.Row`, FK ON)
  - `course_queries.list_by_department(con, departments: Sequence[str]) -> list[sqlite3.Row]`
  - `course_queries.get_course(con, course_id: str) -> sqlite3.Row | None`
  - `course_queries.list_restrictions_for(con, course_ids: Sequence[str]) -> list[sqlite3.Row]`
  - `course_queries.list_aliases(con) -> list[sqlite3.Row]` — 컬럼 `(old_course_id, old_course_name, new_course_id)`, Task 4 `expand_taken` 입력
  - `prereq_queries.get_prereq_tree(con, course_id: str) -> dict | None`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/db/test_queries.py`:

```python
"""queries/* SELECT 함수 검증 — in-memory DB + schema.sql."""

import sqlite3
from pathlib import Path

import pytest

from app.db.connection import get_connection
from app.db.queries import course_queries, prereq_queries

SCHEMA = (
    Path(__file__).resolve().parents[3] / "app" / "db" / "schema.sql"
).read_text(encoding="utf-8")


@pytest.fixture()
def con():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO courses (course_id, course_name, department, credit, year, semester) "
        "VALUES (?, ?, ?, ?, 2026, 1)",
        [
            ("CSE1010", "프로그래밍입문", "컴퓨터공학과", 3.0),
            ("CSE2020", "자료구조", "컴퓨터공학과", 3.0),
            ("AAT2001", "크리에이티브컴퓨팅", "아트&테크놀로지학과", 3.0),
        ],
    )
    con.execute(
        "INSERT INTO course_prerequisites (course_id, prereq_raw, prereq_tree_json) "
        'VALUES (\'CSE2020\', \'선수과목: CSE1010\', \'{"type": "course", "code": "CSE1010"}\')'
    )
    con.execute(
        "INSERT INTO course_aliases (new_course_id, old_course_id, old_course_name, source_type, raw_text) "
        "VALUES ('CSE1010', 'CS101', '컴퓨터입문', 'old_code', '구 CS101')"
    )
    con.execute(
        "INSERT INTO course_restrictions (course_id, target_dept, status, raw_text) "
        "VALUES ('CSE1010', '컴퓨터공학과', 'forbidden', '컴퓨터공학과(불가능)')"
    )
    yield con
    con.close()


def test_get_connection_row_factory_and_fk(tmp_path):
    db = tmp_path / "t.db"
    sqlite3.connect(db).executescript(SCHEMA)
    con = get_connection(db)
    assert con.row_factory is sqlite3.Row
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    con.close()


def test_list_by_department_union(con):
    rows = course_queries.list_by_department(con, ["컴퓨터공학과", "아트&테크놀로지학과"])
    assert {r["course_id"] for r in rows} == {"CSE1010", "CSE2020", "AAT2001"}


def test_list_by_department_empty(con):
    assert course_queries.list_by_department(con, []) == []


def test_get_course(con):
    row = course_queries.get_course(con, "CSE1010")
    assert row["course_name"] == "프로그래밍입문"
    assert course_queries.get_course(con, "NOPE999") is None


def test_list_restrictions_for(con):
    rows = course_queries.list_restrictions_for(con, ["CSE1010", "CSE2020"])
    assert len(rows) == 1
    assert rows[0]["status"] == "forbidden"
    assert course_queries.list_restrictions_for(con, []) == []


def test_list_aliases(con):
    rows = course_queries.list_aliases(con)
    assert [tuple(r) for r in rows] == [("CS101", "컴퓨터입문", "CSE1010")]


def test_get_prereq_tree(con):
    tree = prereq_queries.get_prereq_tree(con, "CSE2020")
    assert tree == {"type": "course", "code": "CSE1010"}
    assert prereq_queries.get_prereq_tree(con, "CSE1010") is None
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/db -v`
Expected: ImportError/AttributeError로 전부 FAIL.

- [ ] **Step 3: 구현**

`app/db/connection.py` (docstring 유지):

```python
import sqlite3
from pathlib import Path

from app import config


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """s_compass_courses.db 읽기용 커넥션 (row_factory=Row, FK ON)."""
    con = sqlite3.connect(db_path or config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con
```

`app/db/queries/course_queries.py` (모듈 docstring을 "courses·course_restrictions·course_aliases 관련 SELECT 묶음."으로 갱신):

```python
import sqlite3
from typing import Optional, Sequence


def list_by_department(
    con: sqlite3.Connection, departments: Sequence[str]
) -> list[sqlite3.Row]:
    """departments 합집합(원문 학과명)에 속한 과목 전부."""
    if not departments:
        return []
    marks = ", ".join("?" for _ in departments)
    return con.execute(
        f"SELECT * FROM courses WHERE department IN ({marks})",
        tuple(departments),
    ).fetchall()


def get_course(con: sqlite3.Connection, course_id: str) -> Optional[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM courses WHERE course_id = ?", (course_id,)
    ).fetchone()


def list_restrictions_for(
    con: sqlite3.Connection, course_ids: Sequence[str]
) -> list[sqlite3.Row]:
    if not course_ids:
        return []
    marks = ", ".join("?" for _ in course_ids)
    return con.execute(
        f"SELECT * FROM course_restrictions WHERE course_id IN ({marks})",
        tuple(course_ids),
    ).fetchall()


def list_aliases(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """core/alias_resolver.expand_taken 입력용 전체 별칭 3열."""
    return con.execute(
        "SELECT old_course_id, old_course_name, new_course_id FROM course_aliases"
    ).fetchall()
```

`app/db/queries/prereq_queries.py` (docstring 유지):

```python
import json
import sqlite3
from typing import Any, Optional


def get_prereq_tree(
    con: sqlite3.Connection, course_id: str
) -> Optional[dict[str, Any]]:
    row = con.execute(
        "SELECT prereq_tree_json FROM course_prerequisites WHERE course_id = ?",
        (course_id,),
    ).fetchone()
    return json.loads(row["prereq_tree_json"]) if row else None
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/unit/db -v`
Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/db/connection.py app/db/queries/course_queries.py app/db/queries/prereq_queries.py tests/unit/db
git commit -m "feat: db 커넥션 팩토리 + course/prereq/alias 쿼리"
```

---

### Task 3: `core/prereq_eval` 충족도 평가 (TDD)

**Files:**
- Modify: `backend/app/core/prereq_eval.py`
- Test: `backend/tests/unit/core/__init__.py` (빈 파일), `backend/tests/unit/core/test_prereq_eval.py` (신규)

**Interfaces:**
- Consumes: `prereq_queries.get_prereq_tree`가 반환하는 트리 dict (leaf `{"type":"course","code":...}` / `{"type":"and"|"or","children":[...]}`).
- Produces: `evaluate(taken: set[str], tree: dict) -> EvaluationResult`. `EvaluationResult.fulfillment`(0~100)는 W3에서 `scoring.score_candidate(signals, prereq_fulfillment)`에 그대로 입력된다. 트리가 없는 과목(W3에서 `get_prereq_tree` → None)은 evaluate를 호출하지 않고 `prereq_fulfillment=None` 처리.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/core/test_prereq_eval.py`:

```python
"""prereq_eval — AND/OR 트리 충족도 평가."""

import pytest

from app.core.prereq_eval import evaluate

LEAF_A = {"type": "course", "code": "CSE1010"}
LEAF_B = {"type": "course", "code": "CSE1020"}
LEAF_C = {"type": "course", "code": "MAT2001"}


def test_leaf_met():
    r = evaluate({"CSE1010"}, LEAF_A)
    assert r.satisfied is True
    assert r.fulfillment == 100.0
    assert r.missing == []


def test_leaf_unmet():
    r = evaluate(set(), LEAF_A)
    assert r.satisfied is False
    assert r.fulfillment == 0.0
    assert r.missing == ["CSE1010"]


def test_and_partial():
    tree = {"type": "and", "children": [LEAF_A, LEAF_B]}
    r = evaluate({"CSE1010"}, tree)
    assert r.satisfied is False
    assert r.fulfillment == 50.0
    assert r.missing == ["CSE1020"]


def test_or_met_by_one():
    tree = {"type": "or", "children": [LEAF_A, LEAF_B]}
    r = evaluate({"CSE1020"}, tree)
    assert r.satisfied is True
    assert r.fulfillment == 100.0
    assert r.missing == []


def test_or_unmet_lists_all_leaves():
    tree = {"type": "or", "children": [LEAF_A, LEAF_B]}
    r = evaluate(set(), tree)
    assert r.satisfied is False
    assert r.fulfillment == 0.0
    assert set(r.missing) == {"CSE1010", "CSE1020"}


def test_nested_and_of_or():
    # AND[OR[A, B], C] — OR 충족 + C 미이수 → 50%
    tree = {"type": "and", "children": [
        {"type": "or", "children": [LEAF_A, LEAF_B]},
        LEAF_C,
    ]}
    r = evaluate({"CSE1010"}, tree)
    assert r.satisfied is False
    assert r.fulfillment == 50.0
    assert r.missing == ["MAT2001"]


def test_unknown_node_type():
    with pytest.raises(ValueError):
        evaluate(set(), {"type": "xor", "children": [LEAF_A]})
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/core/test_prereq_eval.py -v`
Expected: ImportError로 FAIL.

- [ ] **Step 3: 구현**

`app/core/prereq_eval.py` (기존 모듈 docstring 유지):

```python
from pydantic import BaseModel


class EvaluationResult(BaseModel):
    satisfied: bool
    fulfillment: float  # 0~100. scoring.score_candidate 의 prereq_fulfillment 입력
    missing: list[str]  # 미충족 leaf 과목 코드 (OR 미충족 시 그룹 전체)


def evaluate(taken: set[str], tree: dict) -> EvaluationResult:
    fulfillment, missing = _eval_node(taken, tree)
    return EvaluationResult(
        satisfied=fulfillment >= 100.0, fulfillment=fulfillment, missing=missing
    )


def _eval_node(taken: set[str], node: dict) -> tuple[float, list[str]]:
    kind = node["type"]
    if kind == "course":
        if node["code"] in taken:
            return 100.0, []
        return 0.0, [node["code"]]
    if kind not in ("and", "or"):
        raise ValueError(f"알 수 없는 노드 타입: {kind}")
    results = [_eval_node(taken, child) for child in node["children"]]
    if kind == "and":
        fulfillment = sum(f for f, _ in results) / len(results)
        missing = [code for _, m in results for code in m]
        return fulfillment, missing
    best = max(f for f, _ in results)
    if best >= 100.0:
        return 100.0, []
    return best, [code for _, m in results for code in m]
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/unit/core/test_prereq_eval.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/core/prereq_eval.py tests/unit/core
git commit -m "feat: prereq_eval AND/OR 트리 충족도 평가 (0~100 스케일)"
```

---

### Task 4: `core/alias_resolver` 이수 set 확장 (TDD)

**Files:**
- Modify: `backend/app/core/alias_resolver.py`
- Test: `backend/tests/unit/core/test_alias_resolver.py` (신규)

**Interfaces:**
- Consumes: `course_queries.list_aliases` 결과 (`(old_course_id, old_course_name, new_course_id)` 3열 Row — 시퀀스라 언패킹 가능).
- Produces: `expand_taken(taken: set[str], aliases: Iterable[tuple[str | None, str | None, str]]) -> set[str]` — W3 추천 엔진이 이수 판정 전 호출.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/core/test_alias_resolver.py`:

```python
"""alias_resolver — 옛 코드/과목명 → 신 과목 단방향 확장."""

from app.core.alias_resolver import expand_taken

ALIASES = [
    ("CS101", "컴퓨터입문", "CSE1010"),
    (None, "구프로그래밍", "CSE1020"),
    ("MAT200", None, "MAT2001"),
]


def test_expand_by_old_id():
    assert expand_taken({"CS101"}, ALIASES) == {"CS101", "CSE1010"}


def test_expand_by_old_name():
    assert expand_taken({"구프로그래밍"}, ALIASES) == {"구프로그래밍", "CSE1020"}


def test_no_match_returns_copy():
    taken = {"CSE9999"}
    result = expand_taken(taken, ALIASES)
    assert result == {"CSE9999"}
    assert result is not taken  # 원본 비변조


def test_multiple_matches():
    assert expand_taken({"CS101", "MAT200"}, ALIASES) == {
        "CS101", "MAT200", "CSE1010", "MAT2001",
    }
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/core/test_alias_resolver.py -v`
Expected: ImportError로 FAIL.

- [ ] **Step 3: 구현**

`app/core/alias_resolver.py` (기존 모듈 docstring 유지):

```python
from typing import Iterable, Optional, Tuple

AliasTriple = Tuple[Optional[str], Optional[str], str]
# (old_course_id, old_course_name, new_course_id) — course_queries.list_aliases 순서


def expand_taken(taken: set[str], aliases: Iterable[AliasTriple]) -> set[str]:
    """taken 에 old 코드/과목명이 있으면 new_course_id 를 추가 (단방향 1-pass)."""
    expanded = set(taken)
    for old_id, old_name, new_id in aliases:
        if (old_id and old_id in taken) or (old_name and old_name in taken):
            expanded.add(new_id)
    return expanded
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/unit/core/test_alias_resolver.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/core/alias_resolver.py tests/unit/core/test_alias_resolver.py
git commit -m "feat: alias_resolver 이수 set 확장 (옛 코드·과목명 매칭)"
```

---

### Task 5: `core/dept_normalizer` 학부 합집합 (TDD)

**Files:**
- Modify: `backend/app/core/dept_normalizer.py`
- Test: `backend/tests/unit/core/test_dept_normalizer.py` (신규)

**Interfaces:**
- Produces: `candidate_departments(student_dept: str) -> list[str]` — W3 추천 풀 산출 시 `course_queries.list_by_department` 인자로 사용.
- 합집합 학과명 4개는 빌드된 DB `courses.department` 실측으로 확인된 원문이다 (2026-07-06): `지식융합미디어대학`(14과목), `미디어&엔터테인먼트학과`(39), `아트&테크놀로지학과`(35), `신문방송학과`(43).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/core/test_dept_normalizer.py`:

```python
"""dept_normalizer — 학부 → 학과 합집합 (추천 풀 산출 시점에만 적용)."""

from app.core.dept_normalizer import candidate_departments


def test_union_for_mapped_faculty():
    result = candidate_departments("지식융합미디어학부")
    assert result == [
        "지식융합미디어대학",
        "미디어&엔터테인먼트학과",
        "아트&테크놀로지학과",
        "신문방송학과",
    ]


def test_passthrough_for_unmapped():
    assert candidate_departments("컴퓨터공학과") == ["컴퓨터공학과"]


def test_returns_copy():
    a = candidate_departments("지식융합미디어학부")
    a.append("오염")
    assert "오염" not in candidate_departments("지식융합미디어학부")
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/core/test_dept_normalizer.py -v`
Expected: ImportError로 FAIL.

- [ ] **Step 3: 구현**

`app/core/dept_normalizer.py` (기존 모듈 docstring 유지):

```python
# 학부명 → 추천 풀 학과 합집합 (courses.department 원문, 4학기 DB 실측 확인 2026-07-06).
# A4(시연 학과 범위) 확정 시 항목 추가.
DEPT_UNIONS: dict[str, list[str]] = {
    "지식융합미디어학부": [
        "지식융합미디어대학",
        "미디어&엔터테인먼트학과",
        "아트&테크놀로지학과",
        "신문방송학과",
    ],
}


def candidate_departments(student_dept: str) -> list[str]:
    """합집합 매핑이 있으면 그 목록(복사본), 없으면 원문 단일 목록."""
    return list(DEPT_UNIONS.get(student_dept, [student_dept]))
```

- [ ] **Step 4: 통과 + 전체 회귀**

Run: `uv run pytest tests/unit tests/integration -q`
Expected: 실패 0 (W1 기준 61 passed + 신규 ~22개).

- [ ] **Step 5: Commit**

```bash
git add app/core/dept_normalizer.py tests/unit/core/test_dept_normalizer.py
git commit -m "feat: dept_normalizer 학부 합집합 매핑 (지식융합미디어학부)"
```

---

## 완료 기준

- `uv run pytest tests/unit tests/integration` 전체 통과 (실패 0).
- `DashboardResponse.model_validate(<프론트 emptyDashboard 형태 dict>)` 성공 — 계약 미러 확인.
- `frontend/` 및 명시된 docs 외 파일 미변경.
