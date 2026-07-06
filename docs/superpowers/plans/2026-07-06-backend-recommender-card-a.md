# W3: 추천 엔진 5모듈 + 카드 A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `engines/recommender/` 5모듈(content_based·collaborative·prereq_filter·hybrid·restriction_filter)과 `cards/card_a.build()`를 구현해, 학생 입력 → `CardA`(전공 4 + 교양 4 + 후보 20, factors/why_summary 포함)를 결정론적으로 산출한다.

**Architecture:** 점수 결합 순서(CLAUDE.md 고정) `content + collab → hybrid → prereq_filter(감산) → restriction_filter(차단)` 준수. content/collab은 **필터 전 전체 풀**에 signal(0~100)을 산출하고, 가중 결합·선이수 감산·컷오프·factors 분해는 기존 스펙 확정 구현 `scoring.score_candidate(signals, prereq_fulfillment)`에 위임(`hybrid.combine`이 호출), 마지막에 restriction이 차단한다. `prereq_filter`는 점수를 직접 깎지 않고 후보별 충족률(0~100|None)을 산출해 결합 단계에 공급한다 — 감산 로직 이중화 방지. LLM 통역(reason_short)은 W5 전까지 `card_a`의 결정론 폴백 템플릿(engines에는 자연어 없음).

**Tech Stack:** Python 3.12 + uv, scikit-learn(TF-IDF)+numpy, raw sqlite3, pydantic v2, pytest.

## Global Constraints

- 모든 명령은 `backend/` 디렉토리에서 실행 (`uv run ...`).
- **`engines/` = 정형 결과만, 자연어 금지.** 폴백 문구는 `cards/card_a`에만.
- 확정 결정 반영: A13 = factors/why_summary는 `scoring` 결정론 분해로 채움. A6 미결 → 교양 풀은 `is_general=1`(전인교육원), `area_label=None`, `kind="free"`/`kind_label="교양"`.
- 기존 스텁 docstring 유지·현행화. 스텁의 TODO 시그니처는 아래 설계로 대체된다(스펙 확정 `scoring` 재사용 + A13 factors 요구 때문 — W1·W2와 동일하게 시그니처 정련 허용).
- `frontend/`, `docs/` 수정 금지 (플랜 파일 체크박스 갱신 제외). `llm/`, `api/`, `engines/pathway`, `engines/career`, `cards/card_c·card_d` 수정 금지.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- 시작 전 확인: `uv run python -c "import sklearn, numpy"` — 실패 시 `uv add scikit-learn` 후 진행 (numpy는 동반 설치).

---

### Task 1: 쿼리 보강 — `list_by_ids` + `offered_in_semester` (TDD)

**Files:**
- Modify: `backend/app/db/queries/course_queries.py`
- Test: `backend/tests/unit/db/test_queries.py` (테스트 추가)

**Interfaces:**
- Produces: `list_by_ids(con, course_ids: Sequence[str]) -> list[sqlite3.Row]`, `offered_in_semester(con, semester: int) -> set[str]` — Task 7 `card_a`가 소비.

- [x] **Step 1: 실패하는 테스트 추가**

`tests/unit/db/test_queries.py`의 기존 `con` fixture에 offerings INSERT를 추가:

```python
    con.executemany(
        "INSERT INTO course_offerings (course_id, year, semester) VALUES (?, ?, ?)",
        [("CSE1010", 2025, 2), ("CSE1010", 2026, 1), ("CSE2020", 2026, 1)],
    )
```

테스트 추가:

```python
def test_list_by_ids(con):
    rows = course_queries.list_by_ids(con, ["CSE1010", "NOPE999"])
    assert [r["course_id"] for r in rows] == ["CSE1010"]
    assert course_queries.list_by_ids(con, []) == []


def test_offered_in_semester(con):
    assert course_queries.offered_in_semester(con, 2) == {"CSE1010"}
    assert course_queries.offered_in_semester(con, 1) == {"CSE1010", "CSE2020"}
```

- [x] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/db -v` / Expected: 신규 2개 FAIL (AttributeError).

- [x] **Step 3: 구현** — `course_queries.py`에 추가:

```python
def list_by_ids(
    con: sqlite3.Connection, course_ids: Sequence[str]
) -> list[sqlite3.Row]:
    if not course_ids:
        return []
    marks = ", ".join("?" for _ in course_ids)
    return con.execute(
        f"SELECT * FROM courses WHERE course_id IN ({marks})", tuple(course_ids)
    ).fetchall()


def offered_in_semester(con: sqlite3.Connection, semester: int) -> set[str]:
    """해당 학기(1|2)에 개설 이력이 있는 course_id 집합 (연도 무관)."""
    rows = con.execute(
        "SELECT DISTINCT course_id FROM course_offerings WHERE semester = ?",
        (semester,),
    ).fetchall()
    return {r["course_id"] for r in rows}
```

- [x] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/db -v` / Expected: 전부 PASS.

- [x] **Step 5: Commit**

```bash
git add app/db/queries/course_queries.py tests/unit/db/test_queries.py
git commit -m "feat: 과목 id 조회 + 학기별 개설 이력 쿼리 추가"
```

---

### Task 2: `content_based` — TF-IDF 콘텐츠 유사도 signal (TDD)

**Files:**
- Modify: `backend/app/engines/recommender/content_based.py`
- Test: `backend/tests/unit/engines/__init__.py` (빈 파일), `backend/tests/unit/engines/test_content_based.py` (신규)

**Interfaces:**
- Consumes: 과목 행(Mapping — `course_id`/`course_name`/`description_raw` 키 접근, sqlite3.Row·dict 모두 가능).
- Produces: `score(taken_rows, pool_rows) -> dict[course_id, float]` — 0~100 "콘텐츠 유사도" signal. 산출 불가(이수 없음/텍스트 없음)면 `{}` (→ 해당 signal 결측, `scoring`이 N/A 처리).

- [x] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_content_based.py`:

```python
"""content_based — 이수 과목 텍스트 ↔ 후보 TF-IDF 코사인 signal."""

from app.engines.recommender import content_based


def _row(cid, name, desc):
    return {"course_id": cid, "course_name": name, "description_raw": desc}


TAKEN = [_row("CSE1010", "프로그래밍입문", "파이썬 프로그래밍 기초와 자료형")]
POOL = [
    _row("CSE2020", "자료구조", "자료형 리스트 트리 그래프 파이썬 실습"),
    _row("REL1001", "종교학개론", "세계 종교 전통과 의례"),
]


def test_similar_course_scores_higher():
    scores = content_based.score(TAKEN, POOL)
    assert set(scores) == {"CSE2020", "REL1001"}
    assert scores["CSE2020"] > scores["REL1001"]
    assert all(0 <= v <= 100 for v in scores.values())


def test_empty_taken_returns_empty():
    assert content_based.score([], POOL) == {}


def test_empty_pool_returns_empty():
    assert content_based.score(TAKEN, []) == {}


def test_no_text_returns_empty():
    taken = [_row("X1", "", None)]
    pool = [_row("Y1", "", None)]
    assert content_based.score(taken, pool) == {}
```

- [x] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines -v` / Expected: FAIL.

- [x] **Step 3: 구현**

`content_based.py` (기존 docstring 현행화):

```python
"""콘텐츠 기반 signal: 이수 과목 텍스트 ↔ 후보 텍스트 TF-IDF 코사인 (0~100).

결합·감산·컷오프는 hybrid + scoring 담당. 정형 수치만 산출.
"""

from typing import Mapping, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _text(row: Mapping) -> str:
    return f"{row['course_name'] or ''} {row['description_raw'] or ''}".strip()


def score(
    taken_rows: Sequence[Mapping], pool_rows: Sequence[Mapping]
) -> dict[str, float]:
    if not taken_rows or not pool_rows:
        return {}
    docs = [_text(r) for r in taken_rows] + [_text(r) for r in pool_rows]
    try:
        matrix = TfidfVectorizer().fit_transform(docs)
    except ValueError:  # 전부 빈 문서 → 어휘 없음
        return {}
    n_taken = len(taken_rows)
    centroid = np.asarray(matrix[:n_taken].mean(axis=0))
    sims = cosine_similarity(centroid, matrix[n_taken:])[0]
    return {
        pool_rows[i]["course_id"]: round(float(sims[i]) * 100, 1)
        for i in range(len(pool_rows))
    }
```

- [x] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines -v` / Expected: 4 PASS.

- [x] **Step 5: Commit**

```bash
git add app/engines/recommender/content_based.py tests/unit/engines
git commit -m "feat: content_based TF-IDF 콘텐츠 유사도 signal"
```

---

### Task 3: `collaborative` — 코호트 선호도 signal (TDD)

**Files:**
- Modify: `backend/app/engines/recommender/collaborative.py`
- Test: `backend/tests/unit/engines/test_collaborative.py` (신규)

**Interfaces:**
- Consumes: `AlumniRecord`(`adapters/alumni_types` — `enrollment: list[Enrollment(course_id, ...)]`).
- Produces: `score(taken: set[str], candidate_ids: Sequence[str], alumni: Iterable[AlumniRecord]) -> dict[course_id, float]` — 이수 집합 Jaccard 유사도로 가중한 코호트 수강 빈도(0~100). 유사 졸업생 없음(가중치 전부 0)이면 `{}`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_collaborative.py`:

```python
"""collaborative — Jaccard 가중 코호트 선호도 signal."""

from app.adapters.alumni_types import AlumniRecord, Enrollment
from app.engines.recommender import collaborative


def _alum(aid, course_ids):
    return AlumniRecord(
        alumni_id=aid,
        department="아트&테크놀로지",
        enrollment=[Enrollment(course_id=c) for c in course_ids],
    )


ALUMNI = [
    _alum("a1", ["CSE1010", "CSE2020", "AAT3001"]),  # 학생과 겹침 큼
    _alum("a2", ["REL1001", "AAT3001"]),             # 겹침 없음 → 가중치 0
]
TAKEN = {"CSE1010", "CSE2020"}


def test_weighted_by_similarity():
    scores = collaborative.score(TAKEN, ["AAT3001", "REL1001"], ALUMNI)
    # a1(가중치>0)만 반영: AAT3001 수강 → 100, REL1001 미수강 → 0
    assert scores["AAT3001"] == 100.0
    assert scores["REL1001"] == 0.0


def test_no_similar_alumni_returns_empty():
    assert collaborative.score({"XXX9999"}, ["AAT3001"], ALUMNI) == {}


def test_empty_enrollment_skipped():
    empty = AlumniRecord(alumni_id="a3", department="경영학과")
    assert collaborative.score(TAKEN, ["AAT3001"], [empty]) == {}
```

- [ ] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines/test_collaborative.py -v` / Expected: FAIL.

- [ ] **Step 3: 구현**

`collaborative.py` (기존 docstring 현행화):

```python
"""협업 signal: 졸업생 이수 이력 기반 코호트 선호도 (0~100).

user-based — 학생 이수 집합과의 Jaccard 유사도로 각 졸업생을 가중,
후보 과목의 가중 수강 빈도를 정규화한다. 학과 필터는 두지 않는다
(유사도 가중이 코호트 신호를 대신하며, mock 학과명 표기 차이에 안전).
"""

from typing import Iterable, Sequence

from app.adapters.alumni_types import AlumniRecord


def score(
    taken: set[str],
    candidate_ids: Sequence[str],
    alumni: Iterable[AlumniRecord],
) -> dict[str, float]:
    weighted = {cid: 0.0 for cid in candidate_ids}
    total = 0.0
    for record in alumni:
        courses = {e.course_id for e in record.enrollment}
        if not courses:
            continue
        union = taken | courses
        weight = len(taken & courses) / len(union) if union else 0.0
        if weight == 0.0:
            continue
        total += weight
        for cid in candidate_ids:
            if cid in courses:
                weighted[cid] += weight
    if total == 0.0:
        return {}
    return {cid: round(w / total * 100, 1) for cid, w in weighted.items()}
```

- [ ] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines/test_collaborative.py -v` / Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/engines/recommender/collaborative.py tests/unit/engines/test_collaborative.py
git commit -m "feat: collaborative Jaccard 가중 코호트 선호도 signal"
```

---

### Task 4: `prereq_filter` — 후보별 충족률 산출 (TDD)

**Files:**
- Modify: `backend/app/engines/recommender/prereq_filter.py`
- Test: `backend/tests/unit/engines/test_prereq_filter.py` (신규)

**Interfaces:**
- Consumes: `core/prereq_eval.evaluate`, 트리 dict(`prereq_queries.get_prereq_tree` 산출).
- Produces: `fulfillments(taken: set[str], candidate_ids, trees: dict[str, dict | None]) -> dict[str, float | None]` — None = 선수과목 없음. 감산 자체는 `scoring.score_candidate`가 수행(스펙 확정 구현 재사용, 결합 순서는 hybrid 내부에서 signal 결합 후 감산으로 보존).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_prereq_filter.py`:

```python
"""prereq_filter — 후보별 선이수 충족률(0~100|None)."""

from app.engines.recommender import prereq_filter

TREE_A = {"type": "course", "code": "CSE1010"}
TREE_AND = {"type": "and", "children": [
    {"type": "course", "code": "CSE1010"},
    {"type": "course", "code": "MAT2001"},
]}


def test_fulfillments():
    trees = {"CSE2020": TREE_A, "CSE3030": TREE_AND, "REL1001": None}
    result = prereq_filter.fulfillments({"CSE1010"}, ["CSE2020", "CSE3030", "REL1001"], trees)
    assert result == {"CSE2020": 100.0, "CSE3030": 50.0, "REL1001": None}


def test_missing_tree_key_is_none():
    assert prereq_filter.fulfillments(set(), ["X1"], {}) == {"X1": None}
```

- [ ] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines/test_prereq_filter.py -v` / Expected: FAIL.

- [ ] **Step 3: 구현**

`prereq_filter.py` (기존 docstring 현행화 — "점수를 직접 깎지 않는 이유" 포함):

```python
"""선이수 필터: 후보별 충족률(0~100 | None) 산출.

감산 수치는 scoring.score_candidate(PREREQ_PENALTY_MAX)가 계산한다 —
여기서 점수를 깎으면 감산 로직이 이중화되므로 충족률만 공급한다.
hybrid 이후 감산이라는 결합 순서(CLAUDE.md)는 hybrid.combine 내부에서
signal 가중 결합 → 감산 순으로 적용되어 보존된다.
"""

from typing import Optional, Sequence

from app.core.prereq_eval import evaluate


def fulfillments(
    taken: set[str],
    candidate_ids: Sequence[str],
    trees: dict[str, Optional[dict]],
) -> dict[str, Optional[float]]:
    out: dict[str, Optional[float]] = {}
    for cid in candidate_ids:
        tree = trees.get(cid)
        out[cid] = evaluate(taken, tree).fulfillment if tree else None
    return out
```

- [ ] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines/test_prereq_filter.py -v` / Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/engines/recommender/prereq_filter.py tests/unit/engines/test_prereq_filter.py
git commit -m "feat: prereq_filter 후보별 선이수 충족률 산출"
```

---

### Task 5: `hybrid` — signal 결합 → ScoredCandidate (TDD)

**Files:**
- Modify: `backend/app/engines/recommender/hybrid.py`
- Test: `backend/tests/unit/engines/test_hybrid.py` (신규)

**Interfaces:**
- Consumes: `scoring.score_candidate(signals: dict[str, float | None], prereq_fulfillment: float | None) -> ScoredCandidate` (기존 구현 — 수정 금지), signal dict들(Task 2·3), 충족률(Task 4).
- Produces: `combine(signals_by_label: dict[str, dict[str, float]], fulfillments: dict[str, float | None], candidate_ids) -> dict[str, ScoredCandidate]` — Task 6·7이 소비.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_hybrid.py`:

```python
"""hybrid — 후보별 signal 조립 → scoring.score_candidate 위임."""

from app.engines.recommender import hybrid


def test_combine_delegates_to_scoring():
    signals_by_label = {
        "콘텐츠 유사도": {"C1": 90.0, "C2": 10.0},
        "코호트 선호도": {"C1": 80.0},  # C2 는 결측
    }
    fulfill = {"C1": None, "C2": 0.0}
    out = hybrid.combine(signals_by_label, fulfill, ["C1", "C2"])
    assert set(out) == {"C1", "C2"}
    assert out["C1"].score_percent > out["C2"].score_percent
    # C1: 감산 없음(None) / C2: prereq=0 → 최대 감산 −40 반영 → 0점 바닥
    assert out["C2"].score_percent == 0
    labels_c1 = {f.label for f in out["C1"].factors}
    assert "콘텐츠 유사도" in labels_c1 and "코호트 선호도" in labels_c1


def test_candidate_without_signals_gets_zero():
    out = hybrid.combine({}, {"C9": None}, ["C9"])
    assert out["C9"].score_percent == 0
    assert out["C9"].grade == "유보"
```

- [ ] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines/test_hybrid.py -v` / Expected: FAIL.

- [ ] **Step 3: 구현**

`hybrid.py` (기존 docstring 현행화):

```python
"""signal 결합: 후보별 signals + 선이수 충족률 → ScoredCandidate.

가중 결합·감산·컷오프·factors 분해는 scoring.score_candidate
(스펙 2026-06-30 확정 구현)에 위임한다.
"""

from typing import Optional, Sequence

from app.engines.recommender.scoring import ScoredCandidate, score_candidate


def combine(
    signals_by_label: dict[str, dict[str, float]],
    fulfillments: dict[str, Optional[float]],
    candidate_ids: Sequence[str],
) -> dict[str, ScoredCandidate]:
    out: dict[str, ScoredCandidate] = {}
    for cid in candidate_ids:
        signals = {
            label: scores[cid]
            for label, scores in signals_by_label.items()
            if cid in scores
        }
        out[cid] = score_candidate(signals, fulfillments.get(cid))
    return out
```

- [ ] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines/test_hybrid.py -v` / Expected: 2 PASS. (`test_combine_delegates_to_scoring`의 C2=0 기대가 실제 scoring 수치와 다르면 — 유일하게 허용되는 조정: 실제 산출값으로 assert 갱신하되 근거를 보고에 기록.)

- [ ] **Step 5: Commit**

```bash
git add app/engines/recommender/hybrid.py tests/unit/engines/test_hybrid.py
git commit -m "feat: hybrid signal 결합 (scoring.score_candidate 위임)"
```

---

### Task 6: `restriction_filter` — forbidden 차단 (TDD)

**Files:**
- Modify: `backend/app/engines/recommender/restriction_filter.py`
- Test: `backend/tests/unit/engines/test_restriction_filter.py` (신규)

**Interfaces:**
- Consumes: `ScoredCandidate` dict(Task 5), restriction 행(Mapping — `course_id`/`target_dept`/`status`).
- Produces: `apply(scored: dict[str, ScoredCandidate], student_depts: set[str], is_first_major: bool, restrictions) -> dict[str, ScoredCandidate]`. **차단은 `forbidden`/`major_only_forbidden`만** (ARCHITECTURE 확정 — allowed 계열은 정보성).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_restriction_filter.py`:

```python
"""restriction_filter — forbidden/major_only_forbidden 차단."""

from app.engines.recommender import restriction_filter
from app.engines.recommender.scoring import score_candidate

SCORED = {cid: score_candidate({"콘텐츠 유사도": 80.0}, None) for cid in ["C1", "C2", "C3", "C4"]}


def _r(cid, dept, status):
    return {"course_id": cid, "target_dept": dept, "status": status}


RESTRICTIONS = [
    _r("C1", "컴퓨터공학과", "forbidden"),
    _r("C2", "컴퓨터공학과", "major_only_forbidden"),
    _r("C3", "컴퓨터공학과", "allowed"),        # 차단 안 함
    _r("C4", "경영학과", "forbidden"),          # 타 학과 대상 → 무관
]


def test_forbidden_blocked():
    out = restriction_filter.apply(dict(SCORED), {"컴퓨터공학과"}, True, RESTRICTIONS)
    assert set(out) == {"C3", "C4"}


def test_major_only_forbidden_passes_for_non_first_major():
    out = restriction_filter.apply(dict(SCORED), {"컴퓨터공학과"}, False, RESTRICTIONS)
    assert set(out) == {"C2", "C3", "C4"}
```

- [ ] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines/test_restriction_filter.py -v` / Expected: FAIL.

- [ ] **Step 3: 구현**

`restriction_filter.py` (기존 docstring 현행화):

```python
"""수강 제한 차단: forbidden / major_only_forbidden 만 제거.

allowed / major_only_allowed 는 차단하지 않는다 (ARCHITECTURE 확정, 정보성).
파이프라인 마지막 단계 — 점수 산출 이후 적용해 협업 신호를 보존한다.
"""

from typing import Iterable, Mapping

from app.engines.recommender.scoring import ScoredCandidate


def apply(
    scored: dict[str, ScoredCandidate],
    student_depts: set[str],
    is_first_major: bool,
    restrictions: Iterable[Mapping],
) -> dict[str, ScoredCandidate]:
    blocked: set[str] = set()
    for row in restrictions:
        if row["target_dept"] not in student_depts:
            continue
        if row["status"] == "forbidden":
            blocked.add(row["course_id"])
        elif row["status"] == "major_only_forbidden" and is_first_major:
            blocked.add(row["course_id"])
    return {cid: sc for cid, sc in scored.items() if cid not in blocked}
```

- [ ] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines/test_restriction_filter.py -v` / Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/engines/recommender/restriction_filter.py tests/unit/engines/test_restriction_filter.py
git commit -m "feat: restriction_filter forbidden 계열 차단"
```

---

### Task 7: `cards/card_a.build` 오케스트레이터 (TDD + 실 DB 스모크)

**Files:**
- Modify: `backend/app/cards/card_a.py`
- Test: `backend/tests/unit/cards/__init__.py` (빈 파일), `backend/tests/unit/cards/test_card_a.py` (신규), `backend/tests/integration/test_card_a_real_db.py` (신규)

**Interfaces:**
- Consumes: Task 1~6 전부 + `expand_taken`/`candidate_departments`(W2 core) + `CardA`/`RecommendedCourse`/`RecommendationFactor`(W2 schemas) + `StudentInput` + `AlumniRecord`.
- Produces: `build(student: StudentInput, con: sqlite3.Connection, alumni: list[AlumniRecord]) -> CardA` — W6 `/analyze`가 소비.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/cards/test_card_a.py` — in-memory DB로 전 파이프라인 검증:

```python
"""card_a.build — 풀 구성/이수 제외/차단/분류/정렬 검증."""

import sqlite3
from pathlib import Path

import pytest

from app.adapters.alumni_types import AlumniRecord, Enrollment
from app.cards import card_a
from app.schemas.input import StudentInput

SCHEMA = (
    Path(__file__).resolve().parents[3] / "app" / "db" / "schema.sql"
).read_text(encoding="utf-8")

# (course_id, name, department, credit, course_type, is_general, description)
COURSES = [
    ("CSE1010", "프로그래밍입문", "컴퓨터공학과", 3.0, "regular", 0, "파이썬 기초"),
    ("CSE2020", "자료구조", "컴퓨터공학과", 3.0, "regular", 0, "파이썬 리스트 트리"),
    ("CSE3030", "알고리즘", "컴퓨터공학과", 3.0, "regular", 0, "파이썬 그래프 탐색"),
    ("CSE4040", "제한과목", "컴퓨터공학과", 3.0, "regular", 0, "파이썬 심화"),
    ("DUM0001", "더미", "컴퓨터공학과", None, "dummy", 0, None),
    ("REL1001", "종교학개론", "전인교육원", 3.0, "regular", 1, "세계 종교 전통"),
    ("PHI1001", "철학산책", "전인교육원", 3.0, "regular", 1, "고전 철학 파이썬"),
]


@pytest.fixture()
def con():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO courses (course_id, course_name, department, credit, year, semester, "
        "course_type, is_general, description_raw) VALUES (?, ?, ?, ?, 2026, 1, ?, ?, ?)",
        COURSES,
    )
    con.executemany(
        "INSERT INTO course_offerings (course_id, year, semester) VALUES (?, 2025, 2)",
        [(c[0],) for c in COURSES],
    )
    con.execute(
        "INSERT INTO course_prerequisites (course_id, prereq_raw, prereq_tree_json) "
        'VALUES (\'CSE3030\', \'선수과목: CSE2020\', \'{"type": "course", "code": "CSE2020"}\')'
    )
    con.execute(
        "INSERT INTO course_restrictions (course_id, target_dept, status, raw_text) "
        "VALUES ('CSE4040', '컴퓨터공학과', 'forbidden', '컴퓨터공학과(불가능)')"
    )
    yield con
    con.close()


STUDENT = StudentInput(
    student_id="S1", department="컴퓨터공학과", taken_course_ids=["CSE1010"],
)
ALUMNI = [
    AlumniRecord(
        alumni_id="a1", department="컴퓨터공학과",
        enrollment=[Enrollment(course_id=c) for c in ["CSE1010", "CSE2020", "REL1001"]],
    ),
]


def test_build_full_pipeline(con):
    card = card_a.build(STUDENT, con, ALUMNI)
    all_ids = {c.course_id for c in card.candidates}
    assert "CSE1010" not in all_ids        # 이수 과목 제외
    assert "CSE4040" not in all_ids        # forbidden 차단
    assert "DUM0001" not in all_ids        # dummy 제외
    assert {c.course_id for c in card.major} <= {"CSE2020", "CSE3030"}
    assert {c.course_id for c in card.general} <= {"REL1001", "PHI1001"}
    for c in card.candidates:
        assert c.area_label is None                        # A6 미결
        assert c.kind in ("major", "free")
        assert c.factors and c.reason_short and c.why_summary


def test_deterministic_order(con):
    a = card_a.build(STUDENT, con, ALUMNI)
    b = card_a.build(STUDENT, con, ALUMNI)
    assert [c.course_id for c in a.candidates] == [c.course_id for c in b.candidates]


def test_empty_pool_returns_empty_card(con):
    student = StudentInput(student_id="S2", department="없는학과")
    card = card_a.build(student, con, [])
    assert card.major == [] and card.general == []
```

주의: `없는학과`여도 교양 풀(전인교육원)은 잡힌다 — 마지막 테스트 기대를 구현 설계에 맞출 것: 교양 풀은 항상 포함되므로 `card.major == []`만 확실. `card.general`은 비어있지 않음 → assert 를 `assert card.major == []`와 `assert card.general != []`로 작성한다.

`tests/integration/test_card_a_real_db.py`:

```python
"""card_a — 실 DB + mock 졸업생 스모크. 산출물 없으면 skip."""

import json
from pathlib import Path

import pytest

from app import config
from app.adapters.alumni_types import AlumniRecord
from app.cards import card_a
from app.db.connection import get_connection
from app.schemas.input import StudentInput


@pytest.fixture(scope="module")
def con():
    if not config.DB_PATH.exists():
        pytest.skip("s_compass_courses.db 필요 (scripts/build_course_db.py)")
    con = get_connection()
    yield con
    con.close()


@pytest.fixture(scope="module")
def alumni():
    if not config.ALUMNI_MOCK_PATH.exists():
        pytest.skip("data/mock/alumni.json 필요 (scripts/generate_mock_alumni.py)")
    raw = json.loads(Path(config.ALUMNI_MOCK_PATH).read_text(encoding="utf-8"))
    return [AlumniRecord.model_validate(r) for r in raw]


def test_smoke_knowledge_convergence_media(con, alumni):
    sample_taken = [r["course_id"] for r in con.execute(
        "SELECT course_id FROM courses WHERE department = '컴퓨터공학과' "
        "AND course_type = 'regular' ORDER BY course_id LIMIT 5"
    )]
    student = StudentInput(
        student_id="S1", department="지식융합미디어학부", taken_course_ids=sample_taken,
    )
    card = card_a.build(student, con, alumni)
    assert len(card.major) == 4
    assert len(card.general) == 4
    assert len(card.candidates) <= 20
    assert all(0 <= c.score_percent <= 100 for c in card.candidates)
```

- [ ] **Step 2: mock 졸업생 산출물 확인/생성**

Run: `uv run python -c "from app import config; print(config.ALUMNI_MOCK_PATH.exists())"`
False 면: `uv run python scripts/generate_mock_alumni.py` (빌드된 DB에서 course_id 샘플).

- [ ] **Step 3: 실패 확인** — Run: `uv run pytest tests/unit/cards tests/integration/test_card_a_real_db.py -v` / Expected: FAIL (card_a.build 미구현).

- [ ] **Step 4: 구현**

`app/cards/card_a.py`:

```python
"""카드 A 오케스트레이터: 풀 구성 → 신호 → 결합 → 차단 → CardA.

reason_short/why_summary 는 W5(llm/translator) 도입 전까지 결정론 폴백.
"""

import sqlite3

from app.adapters.alumni_types import AlumniRecord
from app.core.alias_resolver import expand_taken
from app.core.dept_normalizer import candidate_departments
from app.db.queries import course_queries, prereq_queries
from app.engines.recommender import (
    collaborative,
    content_based,
    hybrid,
    prereq_filter,
    restriction_filter,
)
from app.engines.recommender.scoring import ScoredCandidate
from app.schemas.cards import CardA, RecommendationFactor, RecommendedCourse
from app.schemas.input import StudentInput

TOP_N_PER_GROUP = 4
CANDIDATES_CAP = 20
TARGET_SEMESTER = 2  # 추천 대상 = 다음 학기 (2026-2)
GENERAL_DEPT = "전인교육원"


def build(
    student: StudentInput,
    con: sqlite3.Connection,
    alumni: list[AlumniRecord],
) -> CardA:
    taken = expand_taken(
        set(student.taken_course_ids),
        [tuple(r) for r in course_queries.list_aliases(con)],
    )
    offered = course_queries.offered_in_semester(con, TARGET_SEMESTER)

    def _pool(departments: list[str]) -> list[sqlite3.Row]:
        return [
            r
            for r in course_queries.list_by_department(con, departments)
            if r["course_type"] == "regular"
            and r["course_id"] not in taken
            and r["course_id"] in offered
        ]

    major_pool = _pool(candidate_departments(student.department))
    general_pool = _pool([GENERAL_DEPT])
    pool = major_pool + general_pool
    pool_ids = [r["course_id"] for r in pool]
    if not pool_ids:
        return CardA(major=[], general=[], candidates=[])

    signals_by_label: dict[str, dict[str, float]] = {}
    taken_rows = course_queries.list_by_ids(con, sorted(taken))
    content = content_based.score(taken_rows, pool)
    if content:
        signals_by_label["콘텐츠 유사도"] = content
    collab = collaborative.score(taken, pool_ids, alumni)
    if collab:
        signals_by_label["코호트 선호도"] = collab

    trees = {cid: prereq_queries.get_prereq_tree(con, cid) for cid in pool_ids}
    fulfill = prereq_filter.fulfillments(taken, pool_ids, trees)
    scored = hybrid.combine(signals_by_label, fulfill, pool_ids)

    student_depts = {student.department, *candidate_departments(student.department)}
    scored = restriction_filter.apply(
        scored,
        student_depts,
        True,  # StudentInput 에 전공 구분 없음 — 데모 학생은 1전공 관점
        course_queries.list_restrictions_for(con, pool_ids),
    )

    major_ids = {r["course_id"] for r in major_pool}
    rows_by_id = {r["course_id"]: r for r in pool}
    ranked = sorted(
        (cid for cid in pool_ids if cid in scored),
        key=lambda cid: (-scored[cid].score_percent, cid),
    )
    major_top = [c for c in ranked if c in major_ids][:TOP_N_PER_GROUP]
    general_top = [c for c in ranked if c not in major_ids][:TOP_N_PER_GROUP]

    def _course(cid: str) -> RecommendedCourse:
        row, sc = rows_by_id[cid], scored[cid]
        is_major = cid in major_ids
        return RecommendedCourse(
            course_id=cid,
            course_name=row["course_name"],
            credit=row["credit"],
            grade=sc.grade,
            score_percent=sc.score_percent,
            reason_short=_fallback_reason(sc),
            kind="major" if is_major else "free",
            kind_label="전공" if is_major else "교양",
            area_label=None,  # A6 미결 — 교양 영역 매핑 없음
            factors=[RecommendationFactor(**f.model_dump()) for f in sc.factors],
            why_summary=f"{sc.grade} · 추천도 {sc.score_percent}%",
        )

    return CardA(
        major=[_course(c) for c in major_top],
        general=[_course(c) for c in general_top],
        candidates=[_course(c) for c in ranked[:CANDIDATES_CAP]],
    )


def _fallback_reason(sc: ScoredCandidate) -> str:
    """W5 llm/translator 도입 전 결정론 1줄 (통역 대체)."""
    pos = [f for f in sc.factors if f.kind == "pos"]
    if not pos:
        return "신호 부족 — 참고용 추천"
    top = max(pos, key=lambda f: f.weight_percent)
    return f"{top.label} 신호가 가장 강한 과목"
```

- [ ] **Step 5: 통과 + 전체 회귀**

Run: `uv run pytest tests/unit tests/integration -q`
Expected: 실패 0 (기존 84 + 신규 ~16).

- [ ] **Step 6: Commit**

```bash
git add app/cards/card_a.py tests/unit/cards tests/integration/test_card_a_real_db.py
git commit -m "feat: card_a 오케스트레이터 (풀→신호→결합→차단→CardA)"
```

---

## 완료 기준

- `uv run pytest tests/unit tests/integration` 전체 통과.
- 실 DB 스모크: 지식융합미디어학부 학생 → 전공 4 + 교양 4 + candidates ≤ 20, 점수 0~100, factors/why_summary 채워짐.
- 동일 입력 → 동일 출력 (결정론) 확인.
- `engines/` 산출물에 자연어 문자열 없음 (폴백 문구는 `cards/card_a`에만).

## 알려진 후속 이슈 (이 플랜 범위 밖 — 보고만)

- 프론트 `takenCourses.fixture.ts`의 이수과목 id가 placeholder(`T01`~) — 실 course_id 매핑 전에는 데모 프로필 A의 content/collab 신호가 0에 수렴. W6 통합 시 실 코드 매핑 필요 (프로필 A의 34과목 이름 → DB course_id).
