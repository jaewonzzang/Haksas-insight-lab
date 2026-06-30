# 카드 A 점수 결합 모듈 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** signal(0~100) 입력을 받아 카드 A 추천도(점수·등급·factors)를 산출하는 결정론 점수 결합 모듈과 가중치 prior를 구현한다.

**Architecture:** `weights.py`(가중치/감산/컷오프 상수) + `scoring.py`(정규화 가중합 → 선이수 감산 → 고정 컷오프, 순수 함수). signal 계산과 분리되어 mock signal로 TDD. restriction·signal 계산·LLM은 범위 밖.

**Tech Stack:** Python ≥3.11, pydantic, pytest, uv.

**Spec:** `docs/superpowers/specs/2026-06-30-card-a-scoring-weights-design.md`

## Global Constraints

- 답변/주석/문서 한국어, 코드 식별자 영어.
- `engines/`=정형 결과만, 자연어 금지. 점수 결합 순서 고정: `content+cohort → hybrid → prereq 감산 → restriction 차단`. 이 모듈은 hybrid(정규화 가중합)+prereq 감산까지. restriction은 상류.
- factor 가중치/감산/컷오프는 **전문가 prior(잠정)** — `weights.py` 한 곳에서만 수정. 데이터 확보 후 재조정(A5).
- contribution 음수 표기는 **U+2212 "−"** (fixture 정합), 양수는 ASCII "+".
- 테스트: `uv run pytest <path> -v` (cwd = `backend/`).
- 커밋 메시지 한국어, 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- 요청 범위 밖 개선 금지.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/app/engines/recommender/weights.py` | 신규 — `FACTOR_WEIGHTS`, `PREREQ_PENALTY_MAX`, `GRADE_CUTOFFS` 상수 |
| `backend/app/engines/recommender/scoring.py` | 신규 — `Factor`, `ScoredCandidate`, `score_candidate()` |
| `backend/tests/unit/test_scoring.py` | 신규 — TDD (mock signal) |
| `docs/OPEN_QUESTIONS.md` | A5 갱신 |

---

### Task 1: 점수 결합 모듈 (weights + scoring)

**Files:**
- Create: `backend/app/engines/recommender/weights.py`
- Create: `backend/app/engines/recommender/scoring.py`
- Test: `backend/tests/unit/test_scoring.py`

**Interfaces:**
- Consumes: (없음 — 순수 함수)
- Produces:
  - `weights.FACTOR_WEIGHTS: dict[str, float]` (6 label, 합 1.00), `weights.PREREQ_PENALTY_MAX: int`, `weights.GRADE_CUTOFFS: dict[str, int]`
  - `scoring.Factor(label:str, weight_percent:int, contribution:str, kind:Literal["pos","neg","mid","na"])`
  - `scoring.ScoredCandidate(score_percent:int, grade:Literal["강추","고려","유보"], factors:list[Factor])`
  - `scoring.score_candidate(signals: dict[str, float | None], prereq_fulfillment: float | None) -> ScoredCandidate`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/unit/test_scoring.py`:
```python
"""score_candidate 단위 테스트 (mock signal)."""

from app.engines.recommender.scoring import score_candidate

ALL_SIX = ["코호트 선호도", "콘텐츠 유사도", "시간 가중 평점",
           "사용자 선호 매칭", "트랙 충족도", "학년 적합도"]


def test_all_present_full_signal_no_prereq():
    s = {label: 100 for label in ALL_SIX}
    r = score_candidate(s, None)
    assert r.score_percent == 100
    assert r.grade == "강추"
    assert len(r.factors) == 6  # 선이수 factor 없음
    assert all(f.kind == "pos" for f in r.factors)
    assert sum(int(f.contribution) for f in r.factors) == 100


def test_na_factors_do_not_deflate_score():
    # 코호트·콘텐츠만 만점, 나머지 4개 N/A → 정규화로 100 유지
    s = {"코호트 선호도": 100, "콘텐츠 유사도": 100,
         "시간 가중 평점": None, "사용자 선호 매칭": None,
         "트랙 충족도": None, "학년 적합도": None}
    r = score_candidate(s, None)
    assert r.score_percent == 100
    na = [f for f in r.factors if f.kind == "na"]
    assert len(na) == 4
    assert all(f.contribution == "N/A" and f.weight_percent == 0 for f in na)


def test_prereq_penalty_subtracts_after_hybrid():
    s = {label: 80 for label in ALL_SIX}
    r = score_candidate(s, 50)  # penalty = round(40 * (1 - 0.5)) = 20
    assert r.score_percent == 60  # 80 - 20
    assert r.grade == "고려"
    prereq = next(f for f in r.factors if f.label == "선이수 충족도")
    assert prereq.contribution == "−20"  # U+2212
    assert prereq.kind == "neg"
    assert prereq.weight_percent == 50


def test_prereq_fully_met_no_penalty():
    r = score_candidate({"코호트 선호도": 90}, 100)  # penalty 0
    prereq = next(f for f in r.factors if f.label == "선이수 충족도")
    assert prereq.contribution == "+0"
    assert prereq.kind == "pos"


def test_all_none_yields_zero_yubo():
    s = {label: None for label in ALL_SIX}
    r = score_candidate(s, None)
    assert r.score_percent == 0
    assert r.grade == "유보"


def test_grade_cutoff_boundaries():
    # 단일 factor → score == round(signal) (정규화로 신호값 그대로)
    assert score_candidate({"코호트 선호도": 80}, None).grade == "강추"
    assert score_candidate({"코호트 선호도": 79}, None).grade == "고려"
    assert score_candidate({"코호트 선호도": 60}, None).grade == "고려"
    assert score_candidate({"코호트 선호도": 59}, None).grade == "유보"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/unit/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.engines.recommender.scoring'`

- [ ] **Step 3: weights.py 작성**

`backend/app/engines/recommender/weights.py`:
```python
"""카드 A 추천도 가중치·감산·컷오프 (전문가 prior).

⚠️ 잠정 수치 — 실데이터(졸업생 실제 수강 = 튜닝 정답) 확보 후 재조정. A5.
튜닝은 이 파일만 수정. 키 순서 = factors[] 표시 순서.
스펙: docs/superpowers/specs/2026-06-30-card-a-scoring-weights-design.md
"""

FACTOR_WEIGHTS: dict[str, float] = {
    "코호트 선호도": 0.25,
    "콘텐츠 유사도": 0.22,
    "시간 가중 평점": 0.18,
    "사용자 선호 매칭": 0.15,
    "트랙 충족도": 0.12,
    "학년 적합도": 0.08,
}

PREREQ_PENALTY_MAX: int = 40

GRADE_CUTOFFS: dict[str, int] = {"강추": 80, "고려": 60}
```

- [ ] **Step 4: scoring.py 작성**

`backend/app/engines/recommender/scoring.py`:
```python
"""카드 A 추천도 점수 결합 (결정론).

정규화 가중합(hybrid) → 선이수 감산 → 고정 컷오프. signal 계산과 분리된 순수 함수.
가중치/감산/컷오프는 weights.py (전문가 prior). restriction·LLM·signal 계산은 범위 밖.
스펙: docs/superpowers/specs/2026-06-30-card-a-scoring-weights-design.md
"""

from typing import Literal

from pydantic import BaseModel

from app.engines.recommender.weights import (
    FACTOR_WEIGHTS,
    GRADE_CUTOFFS,
    PREREQ_PENALTY_MAX,
)

PREREQ_LABEL = "선이수 충족도"


class Factor(BaseModel):
    label: str
    weight_percent: int
    contribution: str
    kind: Literal["pos", "neg", "mid", "na"]


class ScoredCandidate(BaseModel):
    score_percent: int
    grade: Literal["강추", "고려", "유보"]
    factors: list[Factor]


def _grade(score: int) -> str:
    if score >= GRADE_CUTOFFS["강추"]:
        return "강추"
    if score >= GRADE_CUTOFFS["고려"]:
        return "고려"
    return "유보"


def score_candidate(
    signals: dict[str, float | None],
    prereq_fulfillment: float | None,
) -> ScoredCandidate:
    present = {
        label: s
        for label, s in signals.items()
        if label in FACTOR_WEIGHTS and s is not None
    }
    w_sum = sum(FACTOR_WEIGHTS[label] for label in present)

    factors: list[Factor] = []
    hybrid_base = 0.0
    for label in FACTOR_WEIGHTS:  # 고정 순서 = weights.py 정의 순서
        if label in present:
            contrib = FACTOR_WEIGHTS[label] / w_sum * present[label]
            hybrid_base += contrib
            factors.append(Factor(
                label=label,
                weight_percent=round(present[label]),
                contribution=f"+{round(contrib)}",
                kind="pos",
            ))
        else:
            factors.append(Factor(
                label=label, weight_percent=0, contribution="N/A", kind="na",
            ))

    penalty = 0
    if prereq_fulfillment is not None:
        penalty = round(PREREQ_PENALTY_MAX * (1 - prereq_fulfillment / 100))
        factors.append(Factor(
            label=PREREQ_LABEL,
            weight_percent=round(prereq_fulfillment),
            contribution=f"−{penalty}" if penalty > 0 else "+0",  # U+2212
            kind="neg" if penalty > 0 else "pos",
        ))

    score = max(0, min(100, round(hybrid_base) - penalty))
    return ScoredCandidate(score_percent=score, grade=_grade(score), factors=factors)
```
> 주의: `contribution`의 음수 부호는 **U+2212 "−"** (fixture `"−18"`과 동일). ASCII 하이픈 금지.

- [ ] **Step 5: 테스트 통과 확인**

Run: `uv run pytest tests/unit/test_scoring.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/engines/recommender/weights.py backend/app/engines/recommender/scoring.py backend/tests/unit/test_scoring.py
git commit -m "feat: 카드 A 점수 결합 모듈 + 가중치 prior

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: OPEN_QUESTIONS A5 갱신

**Files:**
- Modify: `docs/OPEN_QUESTIONS.md`

**Interfaces:**
- Consumes: (없음) / Produces: (없음)

- [ ] **Step 1: A5 블록 교체**

`docs/OPEN_QUESTIONS.md` 에서 아래 **기존 블록** (정확히 이 4줄)을:
```
### A5. 추천도 감산 폭 수치
- "엑셀 명시 선수 미이수 → -50점" 같은 구체 수치 미결정.
- 등급 컷오프(강추/고려/유보)도 함께.
- 실 후보 풀의 점수 분포 확인 후 튜닝.
```
아래 **새 블록** 으로 교체:
```
### A5. 추천도 가중치 재조정 (잔여)
- **부분 결정**: 점수 공식·가중치 prior·선이수 감산(최대 −40)·등급 컷오프(강추≥80/고려60~79/유보<60) 잠정 확정 — `engines/recommender/weights.py`, `scoring.py`. 스펙: `superpowers/specs/2026-06-30-card-a-scoring-weights-design.md`.
- **잔여**: 실 후보 풀 점수 분포 + 졸업생 실제 수강(튜닝 정답)으로 가중치·컷오프 재조정.
```
(다른 A 항목은 그대로 둔다.)

- [ ] **Step 2: 커밋**

```bash
git add docs/OPEN_QUESTIONS.md
git commit -m "docs: A5 부분 종료 (점수 모듈·가중치 prior 잠정 확정)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 전체 검증

- [ ] `uv run pytest tests/unit/test_scoring.py -v` → 6 passed
- [ ] 회귀: `uv run pytest tests/unit -q` → 기존 테스트 깨지지 않음
