# 졸업생 데이터 잠정 프레임 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카드 C/D 소비측에서 역산한 졸업생 내부 표준 레코드(`AlumniRecord`)와 그 어댑터·mock 생성기를 구현해, 실데이터 없이도 mock으로 카드 C/D를 구동할 배선을 완성한다.

**Architecture:** Pydantic 프레임(`adapters/alumni_types.py`)을 데이터 계층에 두고, `AlumniSource` Protocol이 mock↔real 교체점이 된다. `MockAlumniSource`는 생성기 산출 JSON을 로드하고, `RealAlumniSource`는 실데이터 수령 후 채울 자리만 둔다. 코어(`alumni_id`+`department`) 외 전부 Optional → 부분 데이터에도 깨지지 않는다.

**Tech Stack:** Python ≥3.11, pydantic, raw sqlite3, pytest, uv.

**Spec:** `docs/superpowers/specs/2026-06-29-alumni-data-frame-design.md`

## Global Constraints

- 답변/주석/문서는 한국어 (코드·경로·식별자 제외).
- `AlumniRecord` 프레임은 **API 계약이 아니다** — `schemas/`(프론트 미러 대상)가 아닌 `app/adapters/`에 둔다.
- 코어 필수 = `alumni_id` + `department`. 나머지(`majors`/`enrollment`/`career` 및 하위 필드)는 전부 Optional.
- **잠정 명세** — 실 입력 데이터 확정 시 프레임이 수정될 수 있음(비파괴적 Optional 추가 원칙).
- DB 접근은 raw `sqlite3`. ORM 없음.
- 데이터 산출물(`data/mock/alumni.json`)은 git 제외 — 커밋하지 않는다. 스크립트/테스트만 커밋.
- 테스트 실행: `uv run pytest <path> -v` (cwd = `backend/`).
- 커밋 메시지 한국어, 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- 요청 범위 밖 개선 금지. 엔진(career/pathway)·카드 C/D 본체는 이 계획 범위 아님(A10/A11 알고리즘 미결).

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/app/adapters/alumni_types.py` | **신규** — `Major`/`Enrollment`/`Career`/`AlumniRecord` Pydantic 프레임 |
| `backend/app/adapters/alumni_source.py` | 수정 — Protocol 반환 타입 `list[AlumniRecord]` |
| `backend/app/adapters/mock_alumni.py` | 수정(구현) — `MockAlumniSource` (JSON 로드→검증) |
| `backend/app/adapters/real_alumni.py` | 수정 — `RealAlumniSource` 자리 + 매핑 TODO |
| `backend/app/config.py` | 수정 — `ALUMNI_SOURCE` 플래그 + `ALUMNI_MOCK_PATH` |
| `backend/app/api/deps.py` | 수정 — `get_alumni_source()` 스위치 |
| `backend/scripts/generate_mock_alumni.py` | 수정(구현) — 생성기 → `data/mock/alumni.json` |
| `backend/docs`(저장소 루트 `docs/`) | `OPEN_QUESTIONS.md` A1, `DATA_SCHEMA.md` 갱신 |
| `backend/tests/unit/test_alumni_types.py` | 신규 |
| `backend/tests/unit/test_mock_alumni.py` | 신규 |
| `backend/tests/unit/test_deps_alumni_source.py` | 신규 |
| `backend/tests/unit/test_generate_mock_alumni.py` | 신규 |

---

### Task 1: 캐노니컬 프레임 (`alumni_types.py`)

**Files:**
- Create: `backend/app/adapters/alumni_types.py`
- Test: `backend/tests/unit/test_alumni_types.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `Major(label: str, role: Literal["primary","double","triple","minor"] | None = None, credits: float | None = None)`
  - `Enrollment(course_id: str, year_taken: int | None = None, term_taken: int | None = None)`
  - `Career(type: Literal["job","grad","other"] | None = None, label: str | None = None)`
  - `AlumniRecord(alumni_id: str, department: str, majors: list[Major] = [], enrollment: list[Enrollment] = [], career: Career | None = None)`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/unit/test_alumni_types.py`:
```python
"""졸업생 캐노니컬 프레임 단위 테스트."""

import pytest
from pydantic import ValidationError

from app.adapters.alumni_types import AlumniRecord, Career, Enrollment, Major


def test_core_only_record_valid():
    """코어(alumni_id+department)만으로 생성 가능, 나머지는 빈 기본값."""
    rec = AlumniRecord(alumni_id="a1", department="아트&테크놀로지")
    assert rec.majors == []
    assert rec.enrollment == []
    assert rec.career is None


def test_full_record_parses_nested():
    """dict 입력이 중첩 모델로 파싱된다."""
    rec = AlumniRecord(
        alumni_id="a2",
        department="아트&테크놀로지",
        majors=[{"label": "컴퓨터공학", "role": "double", "credits": 42.0}],
        enrollment=[{"course_id": "CSE3013", "year_taken": 3, "term_taken": 1}],
        career={"type": "grad", "label": "국내 대학원 (CS)"},
    )
    assert rec.majors[0].label == "컴퓨터공학"
    assert rec.enrollment[0].year_taken == 3
    assert rec.career.type == "grad"


def test_optional_fields_default_none():
    """하위 모델의 비코어 필드는 None 허용."""
    m = Major(label="경영학")
    assert m.role is None and m.credits is None
    e = Enrollment(course_id="MGT1001")
    assert e.year_taken is None and e.term_taken is None


def test_missing_core_raises():
    """department 누락은 검증 실패."""
    with pytest.raises(ValidationError):
        AlumniRecord(alumni_id="a3")


def test_invalid_role_rejected():
    """role enum 밖의 값은 거부."""
    with pytest.raises(ValidationError):
        Major(label="X", role="quad")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/unit/test_alumni_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.adapters.alumni_types'`

- [ ] **Step 3: 최소 구현**

`backend/app/adapters/alumni_types.py`:
```python
"""졸업생 데이터 내부 표준 레코드(canonical frame).

API 계약(schemas/)이 아니라 백엔드 데이터 계층의 내부 표현이다.
실데이터 컬럼/규모 미상 → 코어(alumni_id, department) 외 전부 Optional.
실 컬럼 매핑은 adapters/real_alumni.py 한 곳으로 흡수.
잠정 명세 — 실 입력 데이터 확정 시 수정될 수 있음.
스펙: docs/superpowers/specs/2026-06-29-alumni-data-frame-design.md
"""

from typing import Literal

from pydantic import BaseModel


class Major(BaseModel):
    label: str
    role: Literal["primary", "double", "triple", "minor"] | None = None
    credits: float | None = None


class Enrollment(BaseModel):
    course_id: str
    year_taken: int | None = None
    term_taken: int | None = None


class Career(BaseModel):
    type: Literal["job", "grad", "other"] | None = None
    label: str | None = None


class AlumniRecord(BaseModel):
    alumni_id: str
    department: str
    majors: list[Major] = []
    enrollment: list[Enrollment] = []
    career: Career | None = None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/unit/test_alumni_types.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/adapters/alumni_types.py backend/tests/unit/test_alumni_types.py
git commit -m "feat: 졸업생 캐노니컬 프레임 AlumniRecord 추가

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: AlumniSource Protocol + MockAlumniSource

**Files:**
- Modify: `backend/app/adapters/alumni_source.py`
- Modify: `backend/app/adapters/mock_alumni.py`
- Test: `backend/tests/unit/test_mock_alumni.py`

**Interfaces:**
- Consumes: `AlumniRecord` (Task 1)
- Produces:
  - `AlumniSource` Protocol: `list_by_department(department: str) -> list[AlumniRecord]`, `all() -> list[AlumniRecord]`
  - `MockAlumniSource(path: pathlib.Path)` with `.all() -> list[AlumniRecord]`, `.list_by_department(department: str) -> list[AlumniRecord]`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/unit/test_mock_alumni.py`:
```python
"""MockAlumniSource 단위 테스트."""

import json

from app.adapters.alumni_types import AlumniRecord
from app.adapters.mock_alumni import MockAlumniSource


def _write_sample(path):
    path.write_text(
        json.dumps(
            [
                {"alumni_id": "a1", "department": "아트&테크놀로지"},
                {
                    "alumni_id": "a2",
                    "department": "경영학과",
                    "career": {"type": "job", "label": "IT 취업"},
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_all_returns_alumni_records(tmp_path):
    p = tmp_path / "alumni.json"
    _write_sample(p)
    src = MockAlumniSource(p)
    recs = src.all()
    assert len(recs) == 2
    assert all(isinstance(r, AlumniRecord) for r in recs)


def test_list_by_department_filters(tmp_path):
    p = tmp_path / "alumni.json"
    _write_sample(p)
    src = MockAlumniSource(p)
    out = src.list_by_department("아트&테크놀로지")
    assert [r.alumni_id for r in out] == ["a1"]


def test_empty_file_yields_empty(tmp_path):
    p = tmp_path / "alumni.json"
    p.write_text("[]", encoding="utf-8")
    assert MockAlumniSource(p).all() == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/unit/test_mock_alumni.py -v`
Expected: FAIL — `ImportError: cannot import name 'MockAlumniSource'`

- [ ] **Step 3: Protocol 갱신**

`backend/app/adapters/alumni_source.py` 전체 교체:
```python
"""졸업생 데이터 추상 인터페이스.

실 데이터 vs mock 의 교체점. 호출부(엔진/카드)는 이 Protocol 만 의존한다.
반환은 내부 표준 레코드 AlumniRecord (adapters/alumni_types.py).
"""

from typing import Protocol

from app.adapters.alumni_types import AlumniRecord


class AlumniSource(Protocol):
    def list_by_department(self, department: str) -> list[AlumniRecord]: ...
    def all(self) -> list[AlumniRecord]: ...
```

- [ ] **Step 4: MockAlumniSource 구현**

`backend/app/adapters/mock_alumni.py` 전체 교체:
```python
"""합성 mock 졸업생 데이터 공급자 (개발 단계 기본값).

scripts/generate_mock_alumni.py 산출물(JSON, AlumniRecord[]) 을 로드.
스키마는 실데이터 합의 전까지 잠정.
"""

import json
from pathlib import Path

from app.adapters.alumni_types import AlumniRecord


class MockAlumniSource:
    def __init__(self, path: Path) -> None:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self._records = [AlumniRecord.model_validate(r) for r in raw]

    def all(self) -> list[AlumniRecord]:
        return list(self._records)

    def list_by_department(self, department: str) -> list[AlumniRecord]:
        return [r for r in self._records if r.department == department]
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `uv run pytest tests/unit/test_mock_alumni.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/adapters/alumni_source.py backend/app/adapters/mock_alumni.py backend/tests/unit/test_mock_alumni.py
git commit -m "feat: AlumniSource Protocol 갱신 + MockAlumniSource 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: config 플래그 + deps 스위치 + RealAlumniSource 자리

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/adapters/real_alumni.py`
- Test: `backend/tests/unit/test_deps_alumni_source.py`

**Interfaces:**
- Consumes: `MockAlumniSource` (Task 2), `config.ALUMNI_SOURCE`, `config.ALUMNI_MOCK_PATH`
- Produces: `get_alumni_source() -> AlumniSource`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/unit/test_deps_alumni_source.py`:
```python
"""get_alumni_source 스위치 단위 테스트."""

from app import config
from app.adapters.mock_alumni import MockAlumniSource
from app.api.deps import get_alumni_source


def test_get_alumni_source_defaults_to_mock(tmp_path, monkeypatch):
    p = tmp_path / "alumni.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(config, "ALUMNI_SOURCE", "mock")
    monkeypatch.setattr(config, "ALUMNI_MOCK_PATH", p)
    src = get_alumni_source()
    assert isinstance(src, MockAlumniSource)
    assert src.all() == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/unit/test_deps_alumni_source.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_alumni_source'`

- [ ] **Step 3: config 플래그 추가**

`backend/app/config.py` 의 마지막 `DB_PATH` 줄 아래에 추가:
```python
# 졸업생 데이터 공급자 선택 — 실데이터 수령 후 "real" 로 전환 (스펙 §5)
ALUMNI_SOURCE: str = "mock"          # "mock" | "real"
ALUMNI_MOCK_PATH: Path = MOCK_DIR / "alumni.json"
```

- [ ] **Step 4: deps 스위치 구현**

`backend/app/api/deps.py` 전체 교체:
```python
"""FastAPI Depends 의존성 모음 (DB 커넥션, 어댑터 등)."""

from app import config
from app.adapters.alumni_source import AlumniSource
from app.adapters.mock_alumni import MockAlumniSource


def get_alumni_source() -> AlumniSource:
    """설정 플래그에 따라 mock/real 졸업생 공급자를 반환 (교체점)."""
    if config.ALUMNI_SOURCE == "real":
        from app.adapters.real_alumni import RealAlumniSource

        return RealAlumniSource()
    return MockAlumniSource(config.ALUMNI_MOCK_PATH)
```

- [ ] **Step 5: RealAlumniSource 자리 작성**

`backend/app/adapters/real_alumni.py` 전체 교체:
```python
"""학사지원팀 실 졸업생 데이터 공급자 (본선 진출 후 활성화).

실데이터 수령 시 작업 지점 (스펙 §5):
  1. 익명화 export → data/external/ (config.EXTERNAL_DIR)
  2. 아래 메서드에 실 컬럼 → AlumniRecord 매핑 구현 (유일한 매핑 지점)
  3. config.ALUMNI_SOURCE = "real" 로 스위치
매핑 안 되는 필드는 비워둔다(Optional → 엔진이 우아하게 후퇴).
"""

from app.adapters.alumni_types import AlumniRecord


class RealAlumniSource:
    def __init__(self) -> None:
        raise NotImplementedError("실데이터 수령 후 구현 — 스펙 §5")

    def all(self) -> list[AlumniRecord]:
        raise NotImplementedError("실데이터 수령 후 구현 — 스펙 §5")

    def list_by_department(self, department: str) -> list[AlumniRecord]:
        raise NotImplementedError("실데이터 수령 후 구현 — 스펙 §5")
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run pytest tests/unit/test_deps_alumni_source.py -v`
Expected: PASS (1 passed)

- [ ] **Step 7: 커밋**

```bash
git add backend/app/config.py backend/app/api/deps.py backend/app/adapters/real_alumni.py backend/tests/unit/test_deps_alumni_source.py
git commit -m "feat: 졸업생 공급자 스위치(get_alumni_source) + RealAlumniSource 자리

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: mock 생성기 (`generate_mock_alumni.py`)

**Files:**
- Modify: `backend/scripts/generate_mock_alumni.py`
- Test: `backend/tests/unit/test_generate_mock_alumni.py`

**Interfaces:**
- Consumes: `AlumniRecord`, `Major`, `Enrollment`, `Career` (Task 1), `config.DB_PATH`/`config.MOCK_DIR`/`config.ALUMNI_MOCK_PATH`
- Produces:
  - `generate_records(*, n_per_dept: int = 60, departments: list[str] = ..., course_pool: list[str] | None = None, courses_per_term: int = 5, seed: int = 42) -> list[AlumniRecord]`
  - `_load_course_pool(db_path: Path) -> list[str]`
  - `main() -> None` (→ `data/mock/alumni.json` 기록)

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/unit/test_generate_mock_alumni.py`:
```python
"""mock 졸업생 생성기 단위 테스트."""

from app.adapters.alumni_types import AlumniRecord
from scripts.generate_mock_alumni import generate_records

POOL = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]


def test_count_and_type():
    recs = generate_records(n_per_dept=3, departments=["A", "B"], course_pool=POOL, seed=1)
    assert len(recs) == 6
    assert all(isinstance(r, AlumniRecord) for r in recs)


def test_deterministic_with_seed():
    a = generate_records(n_per_dept=2, departments=["A"], course_pool=POOL, seed=7)
    b = generate_records(n_per_dept=2, departments=["A"], course_pool=POOL, seed=7)
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]


def test_core_and_primary_major_present():
    recs = generate_records(
        n_per_dept=1, departments=["아트&테크놀로지"], course_pool=POOL, seed=3
    )
    r = recs[0]
    assert r.alumni_id and r.department == "아트&테크놀로지"
    assert r.majors[0].role == "primary"
    assert r.career is not None and r.career.type in {"job", "grad", "other"}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/unit/test_generate_mock_alumni.py -v`
Expected: FAIL — `ImportError: cannot import name 'generate_records'`

- [ ] **Step 3: 생성기 구현**

`backend/scripts/generate_mock_alumni.py` 전체 교체:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/unit/test_generate_mock_alumni.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 생성기 수동 실행 확인 (산출물은 커밋하지 않음)**

Run: `uv run python scripts/generate_mock_alumni.py`
Expected: `wrote 180 records -> .../data/mock/alumni.json` (courses.db 없으면 합성 풀 사용). 파일이 `data/mock/alumni.json` 에 생성됨.

- [ ] **Step 6: 커밋 (스크립트·테스트만 — JSON 산출물 제외)**

```bash
git add backend/scripts/generate_mock_alumni.py backend/tests/unit/test_generate_mock_alumni.py
git commit -m "feat: mock 졸업생 생성기 generate_mock_alumni 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 문서 갱신 (OPEN_QUESTIONS A1 + DATA_SCHEMA)

**Files:**
- Modify: `docs/OPEN_QUESTIONS.md`
- Modify: `docs/DATA_SCHEMA.md`

**Interfaces:**
- Consumes: (없음 — 문서)
- Produces: (없음)

- [ ] **Step 1: OPEN_QUESTIONS.md A1 갱신**

`docs/OPEN_QUESTIONS.md` 의 `### A1. mock 졸업생 데이터 스키마` 블록(다음 `### A2` 직전까지)을 아래로 교체:
```markdown
### A1. 졸업생 데이터 실 컬럼 매핑 (잔여)
- **부분 결정**: 잠정 프레임 확정 — `app/adapters/alumni_types.AlumniRecord` (코어 `alumni_id`+`department`, 나머지 Optional). 스펙: `superpowers/specs/2026-06-29-alumni-data-frame-design.md`.
- **잔여**: 학사팀 실데이터 실 컬럼 → `AlumniRecord` 매핑. `adapters/real_alumni.py` 한 곳에서 수령 후 작성. 프레임은 입력 데이터에 따라 비파괴적으로 수정될 수 있음.
```

- [ ] **Step 2: DATA_SCHEMA.md 졸업생 절 갱신**

`docs/DATA_SCHEMA.md` 의 `## 졸업생 데이터 (별도)` 절 본문을 아래로 교체:
```markdown
## 졸업생 데이터 (별도)

본선 진출 후 학사지원팀에서 수령. 실 컬럼 미확정 → 카드 C/D 소비측에서 역산한 **잠정 내부 프레임** `app/adapters/alumni_types.AlumniRecord` 로 표현 (API 계약 아님).

- 코어 필수: `alumni_id`, `department`. 나머지(`majors`, `enrollment`, `career`)는 전부 Optional → 부분 데이터에도 후퇴 동작.
- mock 산출: `scripts/generate_mock_alumni.py` → `data/mock/alumni.json`.
- 실데이터 매핑/스위치: `adapters/real_alumni.py` + `config.ALUMNI_SOURCE` (스펙 §5).

상세: `superpowers/specs/2026-06-29-alumni-data-frame-design.md`, 미결정 잔여는 `OPEN_QUESTIONS.md` A1.
```

- [ ] **Step 3: 커밋**

```bash
git add docs/OPEN_QUESTIONS.md docs/DATA_SCHEMA.md
git commit -m "docs: A1 부분 종료(잠정 프레임 확정) + DATA_SCHEMA 졸업생 절 갱신

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 전체 검증

- [ ] 단위 테스트 전체 통과: `uv run pytest tests/unit/test_alumni_types.py tests/unit/test_mock_alumni.py tests/unit/test_deps_alumni_source.py tests/unit/test_generate_mock_alumni.py -v`
- [ ] 회귀 확인(기존 skip 테스트 깨지지 않음): `uv run pytest tests/unit -q`
