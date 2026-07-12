# W6.5-B: 신호 정규화 + 대학원/캡스톤 필터 + 복수전공 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자 피드백(2026-07-12 승인) 3건 반영 — ① 카드 A 점수가 11%대에 눌리는 문제: 신호를 풀 내 상대 강도(max-스케일 0~100)로 정규화, ② 대학원 연계(G코드)·캡스톤 과목을 추천 풀에서 제외, ③ `StudentInput.extra_majors`(복수전공) 추가로 컴퓨터공학 등 복수전공 과목이 전공 추천에 포함되게 한다.

**Architecture:** 가중치 재정규화는 `scoring.score_candidate`에 이미 있음 — 문제는 신호 원값(코호트 14/100, 콘텐츠 10/100)이 낮은 것. 해법 = `hybrid.combine` 진입 시 각 신호 dict를 최대값 기준 0~100으로 리스케일(결정론, 풀 내 상대 강도 의미). 풀 제외와 전공 합집합은 `cards/card_a`의 풀 구성 정책이므로 card_a에. 스키마 변경(`extra_majors`)은 프론트 `types/api.ts` 미러(W6.5-F가 동일 필드명으로 병행 작업 중).

**Tech Stack:** 기존과 동일 (raw sqlite3, pydantic v2, pytest).

## Global Constraints

- 모든 명령은 `backend/`에서 (`uv run ...`).
- 수정 허용: `app/engines/recommender/hybrid.py`, `app/cards/card_a.py`, `app/schemas/input.py`, `docs/API_SPEC.md`, 테스트, 이 플랜 체크박스. **`scoring.py`·`weights.py`(EOL 노이즈 파일)·`llm/`·`frontend/`·`docs/OPEN_QUESTIONS.md` 수정 금지.**
- 워킹트리 기존 미커밋 변경(EOL 노이즈 + `tests/integration/test_translator_live.py`)은 add/commit/checkout 금지.
- 계약 필드명 고정: **`extra_majors: list[str]`** (프론트가 같은 이름으로 미러 중 — 변경 금지).
- 점수 정규화는 결정론 유지 (동일 입력 → 동일 출력). 컷오프(강추 80/고려 60)는 변경하지 않는다.
- frontend 에이전트 병행 중 — `index.lock` 충돌 시 몇 초 후 재시도. 커밋은 명시적 `git add`, push 금지, 메시지 끝 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: 신호 max-스케일 정규화 (hybrid)

**Files:**
- Modify: `backend/app/engines/recommender/hybrid.py`
- Test: `backend/tests/unit/engines/test_hybrid.py` (테스트 추가)

**Interfaces:**
- Produces: `combine()` 동작 변경 — 각 신호를 풀 내 최대값 기준 0~100으로 리스케일 후 결합. 시그니처 불변.

- [x] **Step 1: 실패하는 테스트 추가**

`test_hybrid.py`에 추가:

```python
def test_combine_max_scales_signals_within_pool():
    # 원신호가 낮아도(14/7) 풀 내 최강 = 100으로 리스케일된다 (2026-07-12 사용자 승인)
    signals = {"코호트 선호도": {"C1": 14.0, "C2": 7.0}}
    out = hybrid.combine(signals, {"C1": None, "C2": None}, ["C1", "C2"])
    assert out["C1"].score_percent == 100
    assert out["C2"].score_percent == 50


def test_combine_all_zero_signal_stays_zero():
    out = hybrid.combine({"코호트 선호도": {"C1": 0.0}}, {"C1": None}, ["C1"])
    assert out["C1"].score_percent == 0
```

Run: `uv run pytest tests/unit/engines/test_hybrid.py -v` — 신규 2개 FAIL 확인 (기존 2개는 통과 유지 예상).

- [x] **Step 2: 구현**

`hybrid.py`를 다음으로 교체:

```python
"""signal 결합: 후보별 signals + 선이수 충족률 → ScoredCandidate.

각 signal은 풀 내 최대값 기준 0~100 상대 강도로 리스케일 후 결합한다
(2026-07-12: mock 신호 저강도로 점수가 10%대에 눌리는 문제 대응, 사용자 승인).
가중 결합·감산·컷오프·factors 분해는 scoring.score_candidate
(스펙 2026-06-30 확정 구현)에 위임한다.
"""

from typing import Optional, Sequence

from app.engines.recommender.scoring import ScoredCandidate, score_candidate


def _max_scale(scores: dict[str, float]) -> dict[str, float]:
    """풀 내 상대 강도: 최대값 기준 0~100 리스케일. 최대가 0 이하면 그대로."""
    m = max(scores.values(), default=0.0)
    if m <= 0:
        return dict(scores)
    return {cid: v / m * 100 for cid, v in scores.items()}


def combine(
    signals_by_label: dict[str, dict[str, float]],
    fulfillments: dict[str, Optional[float]],
    candidate_ids: Sequence[str],
) -> dict[str, ScoredCandidate]:
    scaled = {label: _max_scale(scores) for label, scores in signals_by_label.items()}
    out: dict[str, ScoredCandidate] = {}
    for cid in candidate_ids:
        signals = {
            label: scores[cid]
            for label, scores in scaled.items()
            if cid in scores
        }
        out[cid] = score_candidate(signals, fulfillments.get(cid))
    return out
```

- [x] **Step 3: 통과 + 회귀 확인**

Run: `uv run pytest tests/unit/engines tests/unit/cards tests/integration/test_card_a_real_db.py -v`
기존 테스트가 절대 점수값에 의존해 실패하면, 검증 의도를 유지한 채 정규화 후 값으로 갱신하고 보고에 기록.

- [x] **Step 4: Commit**

```bash
git add app/engines/recommender/hybrid.py tests/unit/engines/test_hybrid.py
git commit -m "feat: 추천 신호 풀 내 max-스케일 정규화 — 점수 저강도 문제 대응"
```

---

### Task 2: 대학원(G코드)·캡스톤 과목 풀 제외

**Files:**
- Modify: `backend/app/cards/card_a.py`
- Test: `backend/tests/unit/cards/test_card_a_pool.py` (신규)

**Interfaces:**
- Produces: `_excluded_from_pool(course_id: str, course_name: str) -> bool` — 풀 구성 시 제외 판정.

배경(DB 실측 2026-07-12): G코드 = `학과코드(2~4자)+G+숫자3자리` 전체일치 — 141과목 (예: AATG800, AIEG102, CSEG###). 주의: `ENG2009` 같은 영미어문 과목은 학과코드가 G로 끝날 뿐이므로 **반드시 `re.fullmatch(r"[A-Z]{2,4}G\d{3}", ...)`** 를 쓸 것 (느슨한 패턴은 오탐). 캡스톤 = 과목명에 "캡스톤" 포함 70과목. 제외 후 풀: 아트&테크 35→23, 컴공 53→42, 전인교육원 284→283.

- [x] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/cards/test_card_a_pool.py`:

```python
"""카드 A 풀 제외 판정: 대학원 G코드·캡스톤 (2026-07-12 사용자 승인)."""

from app.cards.card_a import _excluded_from_pool


def test_grad_gcode_excluded():
    assert _excluded_from_pool("AATG800", "Art,Technology,and Social Impact(캡스톤디자인)")
    assert _excluded_from_pool("AIEG102", "패턴인식")
    assert _excluded_from_pool("CSEG001", "아무거나")


def test_capstone_excluded():
    assert _excluded_from_pool("AAT4002", "Advanced Web Development(캡스톤디자인)")


def test_normal_courses_kept():
    assert not _excluded_from_pool("ENG2009", "영미단편소설")  # 학과코드가 G로 끝나는 정상 과목
    assert not _excluded_from_pool("CSE3080", "자료구조")
    assert not _excluded_from_pool("AAT2003", "Intro to Digital Arts")
```

Run: `uv run pytest tests/unit/cards/test_card_a_pool.py -v` — ImportError FAIL 확인.

- [x] **Step 2: 구현**

`card_a.py` 상단에 (`import sqlite3` 아래):

```python
import re
```

상수부에:

```python
# 대학원 연계(G코드: 학과코드+G+숫자3) · 캡스톤 과목은 학부 추천 풀에서 제외 (2026-07-12)
_GRAD_CODE = re.compile(r"[A-Z]{2,4}G\d{3}")


def _excluded_from_pool(course_id: str, course_name: str) -> bool:
    return bool(_GRAD_CODE.fullmatch(course_id)) or "캡스톤" in course_name
```

`_pool()`의 조건에 추가:

```python
            if r["course_type"] == "regular"
            and r["course_id"] not in taken
            and r["course_id"] in offered
            and not _excluded_from_pool(r["course_id"], r["course_name"])
```

- [x] **Step 3: 통과 + 통합 확인**

Run: `uv run pytest tests/unit/cards tests/integration/test_card_a_real_db.py tests/integration/test_analyze_flow.py -v`
`tests/integration/test_analyze_flow.py`의 `test_analyze_returns_full_dashboard`에 assertion 2줄 추가:

```python
    import re as _re
    all_recs = dash.card_a.major + dash.card_a.general + dash.card_a.candidates
    assert all(not _re.fullmatch(r"[A-Z]{2,4}G\d{3}", c.course_id) for c in all_recs)
    assert all("캡스톤" not in c.course_name for c in all_recs)
```

- [x] **Step 4: Commit**

```bash
git add app/cards/card_a.py tests/unit/cards/test_card_a_pool.py tests/integration/test_analyze_flow.py
git commit -m "feat: 카드 A 풀에서 대학원 G코드·캡스톤 과목 제외"
```

---

### Task 3: StudentInput.extra_majors 복수전공

**Files:**
- Modify: `backend/app/schemas/input.py`
- Modify: `backend/app/cards/card_a.py`
- Modify: `docs/API_SPEC.md` (Request 테이블 행 추가)
- Test: `backend/tests/unit/cards/test_card_a_pool.py` (추가), `backend/tests/integration/test_analyze_flow.py` (페이로드 확장)

**Interfaces:**
- Produces: `StudentInput.extra_majors: list[str]` (기본 `[]`) — 프론트 `types/api.ts`가 동일 이름으로 미러(W6.5-F).
- Produces: `card_a._major_departments(student) -> list[str]` — 주전공+복수전공 합집합(원문, 순서 보존 중복 제거).
- 결정(보고에 명시): 복수전공은 **카드 A 전공 풀과 수강제한 판정에만** 반영. 카드 C/D 코호트는 소속 학부 기준 유지 — 유사 졸업생 탐색은 이수 이력 기반이라 전공 정보 불필요.

- [x] **Step 1: 실패하는 테스트 작성**

`schemas/input.py`에 필드 먼저 추가:

```python
    extra_majors: list[str] = Field(
        default_factory=list, description="복수전공 학과/학부 원문 목록"
    )
```

`test_card_a_pool.py`에 추가:

```python
from app.cards.card_a import _major_departments
from app.schemas.input import StudentInput


def test_major_departments_union_with_extra_majors():
    s = StudentInput(
        student_id="A",
        department="지식융합미디어학부",
        extra_majors=["컴퓨터공학과"],
        taken_course_ids=[],
        interest_career=None,
        consider_multimajor=True,
    )
    depts = _major_departments(s)
    assert "아트&테크놀로지학과" in depts      # 소속 학부 합집합
    assert "컴퓨터공학과" in depts             # 복수전공
    assert len(depts) == len(set(depts))       # 중복 없음


def test_major_departments_default_empty_extras():
    s = StudentInput(student_id="A", department="컴퓨터공학과")
    assert _major_departments(s) == ["컴퓨터공학과"]
```

Run: FAIL(ImportError) 확인.

- [x] **Step 2: card_a 구현**

`card_a.py`에 헬퍼 추가:

```python
def _major_departments(student: StudentInput) -> list[str]:
    """주전공+복수전공의 추천 풀 학과 합집합 (원문, 순서 보존 중복 제거)."""
    out: list[str] = []
    for dept in (student.department, *student.extra_majors):
        for d in candidate_departments(dept):
            if d not in out:
                out.append(d)
    return out
```

`build()` 내 두 곳 교체:

```python
    major_pool = _pool(_major_departments(student))
```

```python
    student_depts = {student.department, *student.extra_majors, *_major_departments(student)}
```

- [x] **Step 3: 통합 테스트 확장 + 전체 회귀**

`test_analyze_flow.py` 페이로드에 `"extra_majors": ["컴퓨터공학과"]` 추가하고 assertion 추가:

```python
    all_recs = dash.card_a.major + dash.card_a.candidates
    assert any(c.course_id.startswith("CSE") for c in all_recs), "복수전공(컴공) 과목이 전공 후보에 없음"
```

Run: `uv run pytest tests/unit tests/integration -q --ignore=tests/integration/test_translator_live.py` — 실패 0.

- [x] **Step 4: API_SPEC 갱신 + Commit**

`docs/API_SPEC.md` Request 테이블에 행 추가:

```
| `extra_majors` | string[] | 복수전공 학과/학부 원문 (기본 `[]`) |
```

```bash
git add app/schemas/input.py app/cards/card_a.py tests/unit/cards/test_card_a_pool.py tests/integration/test_analyze_flow.py ../docs/API_SPEC.md
git commit -m "feat: StudentInput.extra_majors 복수전공 — 카드 A 전공 풀·수강제한 반영"
```

---

### Task 4: 서버 스모크 + 플랜 체크박스

- [x] **Step 1: 실 서버 스모크**

uvicorn 기동 후 학생 A 시나리오(department="지식융합미디어학부", extra_majors=["컴퓨터공학과"], 실 이수 32과목)로 POST /analyze — UTF-8 파일 페이로드 사용(Windows 콘솔 한글 인코딩 주의). 확인:
- 전공 추천 4개에 AAT/CSE 혼재(또는 후보 20 안에 CSE 존재)
- 1위 score_percent가 정규화로 상승 (10%대 탈출)
- G코드·캡스톤 부재
확인 후 서버 종료. 결과 수치를 보고에 포함.

- [x] **Step 2: 플랜 체크박스 커밋**

```bash
git add ../docs/superpowers/plans/2026-07-12-backend-score-scale-multimajor.md
git commit -m "docs: W6.5-B 플랜 체크박스 갱신"
```

완료 보고: ① 커밋 해시, ② 테스트 수치, ③ 스모크 결과(1위 점수·등급, 전공 목록, CSE 포함 여부), ④ 절대 점수 assert 갱신이 있었다면 목록, ⑤ 막힌 지점.
