# W6-B: POST /analyze 배선 + CORS + 디버그 라우트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `POST /analyze`가 실 DB + mock 졸업생 240명으로 `DashboardResponse` 전체를 반환하게 한다 — 카드 A/C/D 빌드 → W5 통역 패스(실패 시 폴백) → profile/kpi 조립. CORS·`/courses` 디버그 라우트·`docs/API_SPEC.md` 최종화 포함.

**Architecture:** 배선 지점 확정(W5 스펙 미결 해소) = **cards 오케스트레이터**. 신규 `cards/dashboard.py::build(student, con, alumni) -> DashboardResponse`가 card_a/c/d 빌드, `get_provider()` 호출·주입, `translator.translate_card_a/d`, profile/kpi 조립까지 전부 담당. `api/analyze.py` 핸들러는 deps(커넥션·어댑터)만 받아 `dashboard.build` 1회 호출 (CLAUDE.md: 핸들러는 cards만 호출). profile은 백엔드가 계산 가능한 것만 채우고(name은 `"학생 {student_id}"` placeholder — 데모 헤더 실명·학년은 프론트 W6-F가 병합), kpi.gpa는 성적 데이터 미보유로 None.

**Tech Stack:** FastAPI + raw sqlite3, pydantic v2, pytest + fastapi TestClient(httpx).

## Global Constraints

- 모든 명령은 `backend/` 디렉토리에서 실행 (`uv run ...`).
- **`api/analyze.py` 핸들러는 `cards/dashboard`만 호출** — 엔진/LLM/DB 직접 import 금지. LLM 통역은 `cards/dashboard.py` 안에서만.
- **예외 확정: `/courses`·`/health`는 디버그/내부 라우트라 `db/queries` 직접 사용 허용** (cards 경유가 무의미). 이 해석은 완료 보고에 명시할 것.
- `engines/`, `cards/card_a·c·d`, `schemas/`, `llm/`, `core/`, `frontend/` 수정 금지. docs는 `docs/API_SPEC.md`와 이 플랜 파일만 수정 가능 (**`docs/OPEN_QUESTIONS.md` 수정 금지** — EOL 노이즈 보류 중).
- 워킹트리의 기존 미커밋 변경(EOL 노이즈 20개 파일 + 미커밋 `tests/integration/test_translator_live.py`)은 add/commit/checkout 금지. **예외: `app/api/deps.py`는 이 플랜이 수정하는 파일이라 커밋 대상** — 14줄 파일이므로 EOL 정규화가 diff에 섞여도 그대로 커밋.
- 통합 테스트 assertion은 통역 문구 원문에 의존 금지 (크레딧 충전 여부에 따라 폴백/통역이 갈림 — 어느 쪽이든 통과해야 함).
- 커밋은 자기 변경 파일만 명시적 `git add`. push 금지. `index.lock` 충돌 시 몇 초 후 재시도(frontend 에이전트 병행 중). 커밋 메시지 끝 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: cards/dashboard.py — 대시보드 오케스트레이터

**Files:**
- Create: `backend/app/cards/dashboard.py`
- Test: `backend/tests/unit/cards/test_dashboard.py`

**Interfaces:**
- Consumes: `card_a.build(student, con, alumni) -> CardA`, `card_c.build(student, alumni) -> CardC`, `card_d.build(student, con, alumni) -> tuple[CardD, ClusterEvidence]`, `translator.translate_card_a/d`, `get_provider()`, `course_queries.list_by_ids(con, ids)`.
- Produces: `build(student: StudentInput, con: sqlite3.Connection, alumni: list[AlumniRecord]) -> DashboardResponse` — Task 2 핸들러가 그대로 사용.

- [x] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/cards/test_dashboard.py`:

```python
"""dashboard 오케스트레이터: 카드 스텁 + provider 몽키패치로 조립 로직만 검증."""

from app.cards import dashboard
from app.schemas.cards import (
    CardC,
    CardD,
    CareerEntry,
    ClusterEvidence,
)
from app.schemas.input import StudentInput
from tests.unit.llm.fixtures import make_card_a
from tests.unit.llm.test_translator import FakeProvider  # 정상/실패 provider 재사용
from app.llm.prompts import CardAItem, CardATranslation


def _student() -> StudentInput:
    return StudentInput(
        student_id="A",
        department="지식융합미디어학부",
        taken_course_ids=["CSE3080", "MAS1001"],
        interest_career=None,
        consider_multimajor=True,
    )


def _stub_cards(monkeypatch):
    card_d_obj = CardD(
        similar_label="유사 경로 30명", sample_size=30,
        entries=[CareerEntry(cluster_label="개발자", type="job", count=18, share_percent=60.0)],
        sub_title="취업 세부 분포", sub_chips=[],
        pattern_summary="유사 경로 30명 중 개발자 계열이 60%로 가장 많습니다.",
    )
    evidence = ClusterEvidence(factors=[], common_courses=[], career_patterns=[], summary="근거 폴백")
    monkeypatch.setattr(dashboard.card_a, "build", lambda s, con, al: make_card_a())
    monkeypatch.setattr(
        dashboard.card_c, "build",
        lambda s, al: CardC(cohort_label="지식융합미디어학부 · 졸업생 180명", entries=[], baseline_note=""),
    )
    monkeypatch.setattr(dashboard.card_d, "build", lambda s, con, al: (card_d_obj, evidence))
    monkeypatch.setattr(
        dashboard.course_queries, "list_by_ids",
        lambda con, ids: [{"credit": 3.0}, {"credit": None}],
    )


def test_assembles_profile_kpi_with_fallback(monkeypatch):
    _stub_cards(monkeypatch)
    monkeypatch.setattr(dashboard, "get_provider", lambda: None)  # 키 없음 = 폴백
    resp = dashboard.build(_student(), con=None, alumni=[])
    assert resp.profile.name == "학생 A"
    assert resp.profile.department == "지식융합미디어학부"
    assert resp.profile.report_semester == "2026-1학기"
    assert resp.profile.next_semester == "2026-2"
    assert resp.kpi.earned_credits == 3.0  # credit None은 0 취급
    assert resp.kpi.gpa is None and resp.kpi.gpa_scale == 4.3
    assert resp.kpi.similar_alumni_n == 30
    # provider 없음 → 폴백 문구 그대로
    assert resp.card_a.major[0].reason_short == "코호트 선호도 신호가 가장 강한 과목"
    assert resp.cluster.summary == "근거 폴백"


def test_injects_translator_when_provider_available(monkeypatch):
    _stub_cards(monkeypatch)
    ids = [f"AIE100{i}" for i in range(1, 5)] + [f"GEN200{i}" for i in range(1, 5)]
    out = CardATranslation(items=[CardAItem(course_id=i, reason=f"{i} 통역") for i in ids])
    monkeypatch.setattr(dashboard, "get_provider", lambda: FakeProvider(out))
    resp = dashboard.build(_student(), con=None, alumni=[])
    assert resp.card_a.major[0].reason_short == "AIE1001 통역"
    # 카드 D 통역은 CardDTranslation이 아니므로(스키마 불일치) FakeProvider가 CardATranslation을
    # 반환해도 translator가 그대로 쓰지 않도록 — 여기선 카드 A만 검증하고 카드 D 폴백 유지 확인은
    # FakeProvider(None) 경로가 test_translator에서 이미 커버.
```

참고: `FakeProvider`는 `tests/unit/llm/test_translator.py`에 이미 정의돼 있다(임포트해서 재사용). 카드 D에도 같은 `out`이 반환되면 `CardATranslation`에는 `pattern_summary` 속성이 없어 `AttributeError`가 날 수 있으므로, 구현에서 카드별로 provider를 각각 호출하되 **테스트의 FakeProvider는 스키마 인자를 무시하고 동일 out을 반환**한다는 점을 감안해 두 번째 테스트에서는 카드 D 쪽이 예외 없이 지나가는지도 함께 확인된다 — 만약 `AttributeError`가 나면 그것은 translator가 아니라 FakeProvider 한계이므로, 두 번째 테스트에서는 `monkeypatch.setattr(dashboard.translator, "translate_card_d", lambda c, e, p: (c, e))`로 카드 D 통역을 우회해도 된다(카드 D 통역 자체는 test_translator에서 검증 완료).

- [x] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/cards/test_dashboard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.cards.dashboard'` (또는 ImportError)

- [x] **Step 3: dashboard.py 구현**

```python
"""대시보드 오케스트레이터: 카드 A/C/D 조립 + W5 통역 패스 + profile/kpi.

api/analyze 핸들러의 유일한 진입점 (핸들러는 cards만 호출 — CLAUDE.md).
통역 배선 지점 = cards (W5 스펙 미결 확정): get_provider() 호출·주입도 여기서.
profile.name·year는 SAINT 연계 전 placeholder — 데모 헤더는 프론트가 병합(W6-F).
"""

import sqlite3
from datetime import date

from app.adapters.alumni_types import AlumniRecord
from app.cards import card_a, card_c, card_d
from app.db.queries import course_queries
from app.llm import translator
from app.llm.providers.anthropic import get_provider
from app.schemas.cards import DashboardResponse, KpiStrip, StudentProfile
from app.schemas.input import StudentInput

REPORT_SEMESTER = "2026-1학기"
NEXT_SEMESTER = "2026-2"
GPA_SCALE = 4.3


def build(
    student: StudentInput,
    con: sqlite3.Connection,
    alumni: list[AlumniRecord],
) -> DashboardResponse:
    a = card_a.build(student, con, alumni)
    c = card_c.build(student, alumni)
    d, evidence = card_d.build(student, con, alumni)

    provider = get_provider()
    a = translator.translate_card_a(a, provider)
    d, evidence = translator.translate_card_d(d, evidence, provider)

    taken_rows = course_queries.list_by_ids(con, student.taken_course_ids)
    earned = sum(r["credit"] or 0 for r in taken_rows)

    profile = StudentProfile(
        name=f"학생 {student.student_id}",
        department=student.department,
        year="—",
        analysis_date=date.today().isoformat(),
        report_semester=REPORT_SEMESTER,
        next_semester=NEXT_SEMESTER,
    )
    kpi = KpiStrip(
        earned_credits=earned,
        gpa=None,  # 성적 데이터 미보유 (SAINT 연계 전)
        gpa_scale=GPA_SCALE,
        similar_alumni_n=d.sample_size,
    )
    return DashboardResponse(
        profile=profile, kpi=kpi, card_a=a, card_c=c, card_d=d, cluster=evidence
    )
```

단, `list_by_ids`가 빈 리스트 인자에서 어떻게 동작하는지 확인하고(빈 IN 절), 빈 입력이면 호출 없이 `earned = 0`으로 두는 편이 안전하면 `taken_rows = course_queries.list_by_ids(con, student.taken_course_ids) if student.taken_course_ids else []`로.

- [x] **Step 4: 통과 확인**

Run: `uv run pytest tests/unit/cards -v`
Expected: PASS (기존 cards 테스트 + 신규 2)

- [x] **Step 5: Commit**

```bash
git add app/cards/dashboard.py tests/unit/cards/test_dashboard.py
git commit -m "feat: cards/dashboard 오케스트레이터 — 카드 조립 + 통역 주입 + profile/kpi"
```

---

### Task 2: deps.get_db + POST /analyze 핸들러

**Files:**
- Modify: `backend/app/api/deps.py` (get_db 추가 — 파일 전체 EOL 정규화가 diff에 섞여도 커밋)
- Modify: `backend/app/api/analyze.py` (TODO 스텁 → 핸들러)
- Modify: `backend/pyproject.toml` (dev extras에 `"httpx"` 추가 — TestClient 의존)
- Test: `backend/tests/integration/test_analyze_flow.py` (기존 TODO 스텁 교체)

**Interfaces:**
- Consumes: Task 1 `dashboard.build`, 기존 `deps.get_alumni_source()`(`.all()` 사용), `db/connection.get_connection`.
- Produces: `POST /analyze` (request `StudentInput`, response `DashboardResponse`), `deps.get_db()` — Task 3 courses 라우트도 사용.

- [x] **Step 1: 실패하는 통합 테스트 작성**

`backend/pyproject.toml` dev extras에 `"httpx",` 추가 후 `uv sync --extra dev`.

`backend/tests/integration/test_analyze_flow.py` (기존 `# TODO` 스텁 교체):

```python
"""POST /analyze 통합 흐름 — 실 DB + mock 240명 + TestClient. 산출물 없으면 skip."""

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.schemas.cards import DashboardResponse

pytestmark = pytest.mark.skipif(
    not config.DB_PATH.exists() or not config.ALUMNI_MOCK_PATH.exists(),
    reason="실 DB 또는 mock alumni 없음 (build_course_db / generate_mock_alumni 필요)",
)

# 학생 A 실 이수 32과목 (frontend takenCourses.fixture 매핑과 동일) + 군이러닝 placeholder 2건
TAKEN = [
    "COR1012", "HFS2002", "AAT3019", "CSE3030", "CSE3080", "CSE4010", "CSE4175",
    "ETS2001", "AAT2004", "COR1010", "MAS2003", "COR1007", "CSE3006", "CSE3015",
    "CSE3040", "MAS1004", "MAS2008", "STS2008", "COR1021", "GKS3002", "HSS3001",
    "PUB2005", "SHS2002", "ETS2003", "LED3015", "MAS2002", "STS2002", "STS2004",
    "COR1003", "MAS1001", "MAS1002", "GKS1001", "T12", "T13",
]


def test_analyze_returns_full_dashboard():
    client = TestClient(app)
    res = client.post(
        "/analyze",
        json={
            "student_id": "A",
            "department": "지식융합미디어학부",
            "taken_course_ids": TAKEN,
            "interest_career": None,
            "consider_multimajor": True,
        },
    )
    assert res.status_code == 200
    dash = DashboardResponse.model_validate(res.json())
    assert dash.profile.department == "지식융합미디어학부"
    assert 1 <= len(dash.card_a.major) <= 4
    assert 1 <= len(dash.card_a.general) <= 4
    assert len(dash.card_a.candidates) <= 20
    assert dash.card_c.entries, "카드 C 분포 비어 있음"
    assert dash.card_d.sample_size > 0
    assert dash.kpi.similar_alumni_n == dash.card_d.sample_size
    assert dash.kpi.earned_credits > 0  # 32과목 학점 합
    # 통역 문구 원문 의존 금지 — 비어 있지 않음만 확인 (폴백/통역 어느 쪽이든 통과)
    assert dash.card_d.pattern_summary.strip()
    assert all(c.reason_short.strip() for c in dash.card_a.major)


def test_health():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
```

(`/health`의 기존 응답 형식은 `app/api/health.py`를 읽고 맞출 것 — 경로가 다르면 테스트를 실제 경로에 맞춘다.)

- [x] **Step 2: 실패 확인**

Run: `uv run pytest tests/integration/test_analyze_flow.py -v`
Expected: FAIL — `/analyze` 404 (라우트 미정의)

- [x] **Step 3: deps.get_db + analyze 핸들러 구현**

`backend/app/api/deps.py`에 추가:

```python
import sqlite3
from collections.abc import Iterator

from app.db.connection import get_connection


def get_db() -> Iterator[sqlite3.Connection]:
    """요청 스코프 sqlite3 커넥션 (읽기 전용 사용)."""
    con = get_connection()
    try:
        yield con
    finally:
        con.close()
```

`backend/app/api/analyze.py` (스텁 교체):

```python
"""POST /analyze — 학생 입력 1회 → 카드 A/C/D 통합 dashboard 응답.

핸들러는 schemas/input 검증 → cards/dashboard 오케스트레이터 호출 → 응답 반환만 한다.
엔진/LLM/DB를 직접 import 하지 않는다.
"""

import sqlite3

from fastapi import APIRouter, Depends

from app.adapters.alumni_source import AlumniSource
from app.api.deps import get_alumni_source, get_db
from app.cards import dashboard
from app.schemas.cards import DashboardResponse
from app.schemas.input import StudentInput

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=DashboardResponse)
def analyze(
    student: StudentInput,
    con: sqlite3.Connection = Depends(get_db),
    source: AlumniSource = Depends(get_alumni_source),
) -> DashboardResponse:
    return dashboard.build(student, con, source.all())
```

- [x] **Step 4: 통과 확인**

Run: `uv run pytest tests/integration/test_analyze_flow.py -v`
Expected: PASS (2 passed 또는 DB 부재 시 skip — 이 환경엔 DB 있으므로 PASS여야 함)

- [x] **Step 5: Commit**

```bash
git add app/api/deps.py app/api/analyze.py pyproject.toml uv.lock tests/integration/test_analyze_flow.py
git commit -m "feat: POST /analyze 배선 — deps.get_db + dashboard.build 호출 + 통합 흐름 테스트"
```

---

### Task 3: CORS + /courses 디버그 라우트

**Files:**
- Modify: `backend/app/main.py` (CORSMiddleware)
- Modify: `backend/app/api/courses.py` (TODO 스텁 → GET /courses/{course_id})
- Test: `backend/tests/integration/test_analyze_flow.py` (courses 테스트 2개 추가)

**Interfaces:**
- Consumes: Task 2 `deps.get_db`, 기존 `course_queries.get_course(con, course_id) -> Optional[sqlite3.Row]`.
- Produces: `GET /courses/{course_id}` → 과목 row dict, 404 if missing. CORS 허용 origin: Vite dev 서버.

- [x] **Step 1: 실패하는 테스트 추가**

`test_analyze_flow.py`에 추가:

```python
def test_courses_debug_lookup():
    client = TestClient(app)
    res = client.get("/courses/CSE3080")  # 자료구조
    assert res.status_code == 200
    assert res.json()["course_id"] == "CSE3080"


def test_courses_debug_404():
    client = TestClient(app)
    assert client.get("/courses/NOPE9999").status_code == 404
```

Run: `uv run pytest tests/integration/test_analyze_flow.py -v` — 신규 2개 FAIL 확인.

- [x] **Step 2: 구현**

`backend/app/api/courses.py` (스텁 교체 — 디버그 라우트는 db/queries 직접 사용 허용, Global Constraints 참조):

```python
"""디버그/내부용 과목 조회 라우트. 외부 노출 X — db/queries 직접 사용 허용(디버그 예외)."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db
from app.db.queries import course_queries

router = APIRouter(prefix="/courses", tags=["debug"])


@router.get("/{course_id}")
def get_course(course_id: str, con: sqlite3.Connection = Depends(get_db)) -> dict:
    row = course_queries.get_course(con, course_id)
    if row is None:
        raise HTTPException(status_code=404, detail="course not found")
    return dict(row)
```

`backend/app/main.py`의 `app = FastAPI(...)` 아래 추가:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [x] **Step 3: 통과 확인 + 전체 회귀**

Run: `uv run pytest tests/integration/test_analyze_flow.py -v` — PASS.
Run: `uv run pytest tests/unit tests/integration -q --ignore=tests/integration/test_translator_live.py` — 실패 0 (기존 140 passed/1 skip + 신규 6).

- [x] **Step 4: Commit**

```bash
git add app/main.py app/api/courses.py tests/integration/test_analyze_flow.py
git commit -m "feat: CORS(Vite dev) + GET /courses/{course_id} 디버그 라우트"
```

---

### Task 4: 서버 기동 스모크 + docs/API_SPEC.md 최종화

**Files:**
- Modify: `docs/API_SPEC.md`

- [x] **Step 1: 실 서버 스모크**

Run (backend/에서): `uv run uvicorn app.main:app --port 8000` 을 백그라운드로 띄우고,

```bash
curl -s -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d '{"student_id":"A","department":"지식융합미디어학부","taken_course_ids":["CSE3080","MAS1001"],"interest_career":null,"consider_multimajor":true}'
```

Expected: HTTP 200 + JSON에 `card_a`/`card_c`/`card_d`/`cluster` 키 존재. 확인 후 서버 종료.

- [x] **Step 2: API_SPEC.md 갱신**

`docs/API_SPEC.md`의 "기타 라우트" 표를 실제 구현에 맞게 확정:

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/health` | liveness |
| `GET` | `/courses/{course_id}` | 디버그용 과목 단건 조회. 외부 노출 X. |

그리고 문서 하단에 한 줄 추가: `CORS: Vite dev 서버(localhost:5173) 허용 — app/main.py.`
그 외 기존 내용(스키마 요약)은 이미 구현과 일치하므로 변경하지 않는다.

- [x] **Step 3: Commit + 플랜 체크박스 갱신**

```bash
git add ../docs/API_SPEC.md
git commit -m "docs: API_SPEC 라우트 확정 (analyze 구현·courses 단건 조회·CORS)"
git add ../docs/superpowers/plans/2026-07-10-backend-analyze-api.md
git commit -m "docs: W6-B 플랜 체크박스 갱신"
```

완료 보고: ① 커밋 해시 목록, ② 전체 테스트 수치, ③ curl 스모크 응답 요약(카드별 항목 수), ④ 플랜 이탈/결정 사항(특히 디버그 라우트 db 직접 사용 예외), ⑤ 막힌 지점.
