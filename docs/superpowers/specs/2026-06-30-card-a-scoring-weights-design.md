# 카드 A 점수 결합 모듈 (추천도 가중치 prior) — 설계

> **목적:** 카드 A 추천도를 산출하는 **결정론 점수 결합 모듈**과 그 가중치 prior를 정의한다. signal 계산(콘텐츠·코호트 등)과 분리되어 mock signal로 지금 구현·테스트 가능하다(translator와 동일 전략). `OPEN_QUESTIONS.md` A5(가중치 수치·등급 컷오프)를 **잠정 확정**한다 — 모든 수치는 전문가 prior이며 데이터 확보 후 재조정한다.

> ⚠️ **잠정 수치.** 가중치·감산폭·컷오프는 데이터 없이 정한 prior다. 실 후보 풀 점수 분포와 졸업생 실제 수강(튜닝 정답)이 확보되면 재조정한다(A5 잔존). 근거는 `docs/AI_ROLE_RATIONALE.md`(추천도=결정론) 기조를 따른다.

## 1. 모듈 경계 & 인터페이스

`engines/recommender/scoring.py` — 순수 결정론 함수. 같은 입력 → 같은 출력.

```python
def score_candidate(
    signals: dict[str, float | None],   # factor_label → 0~100 신호강도 (None = N/A)
    prereq_fulfillment: float | None,    # 선이수 충족도 0~100 (None = 선수과목 없음)
) -> ScoredCandidate: ...
```

`ScoredCandidate` (내부 표현):
```python
class ScoredCandidate(BaseModel):
    score_percent: int        # 0~100
    grade: Literal["강추", "고려", "유보"]
    factors: list[Factor]     # 프론트 RecommendationFactor 형태
```

`Factor` (프론트 `types/api.ts`의 `RecommendationFactor`와 동일 필드):
```python
class Factor(BaseModel):
    label: str
    weight_percent: int                       # 막대 채움 = 신호강도(0~100)
    contribution: str                         # "+26" / "−18" / "N/A"
    kind: Literal["pos", "neg", "mid", "na"]
```

**경계:**
- restriction(수강 차단)은 이 모듈 밖. 차단 과목은 상류 `restriction_filter`에서 이미 제외된 채 들어온다 (CLAUDE.md 고정 순서 `… → prereq 감산 → restriction 차단` 준수).
- signal 값은 입력으로만 받는다. 콘텐츠·코호트 등의 계산은 이 모듈 책임이 아니다.
- `engines/recommender/hybrid.py` 스텁은 이 `scoring`을 호출하는 얇은 래퍼로 남긴다.

## 2. 점수 공식 (CLAUDE.md 결합 순서 준수)

```
양의 factor 집합 P = signals 중 값이 None 아닌 factor
W = Σ wᵢ           (i ∈ P)
hybrid_base = Σ (wᵢ/W · sᵢ)        (i ∈ P)          # 존재 factor로 정규화한 가중평균, 0~100
prereq_penalty = round(PREREQ_PENALTY_MAX × (1 − prereq_fulfillment/100))   # 선이수 충족도 있을 때만
score_percent = clamp(round(hybrid_base) − prereq_penalty, 0, 100)
grade = cutoff(score_percent)
```

- **선이수 충족도는 양의 가중합에 넣지 않고 hybrid 이후 감산**으로 처리한다(코호트 신호 보존 — CLAUDE.md). 단 표시상 `factors[]`에 `kind:"neg"` 기여도로 노출한다.
- `prereq_fulfillment is None` → 선수과목 없음 → 감산 0, 선이수 factor 미표시.

### factors[] 구성 규칙
- **양의 factor (i ∈ P):** `weight_percent = round(sᵢ)`, `contribution = "+{round(wᵢ/W · sᵢ)}"`, `kind = "pos"`.
- **N/A factor (signal None):** `weight_percent = 0`, `contribution = "N/A"`, `kind = "na"`.
- **선이수 factor (prereq_fulfillment not None):** `weight_percent = round(prereq_fulfillment)`, `contribution = "−{prereq_penalty}"` (penalty>0) / `"+0"` (penalty=0), `kind = "neg"` (penalty>0) / `"pos"` (penalty=0).
- 표시 contribution 합은 score_percent와 ±1 이내(독립 반올림 허용). 점수 자체는 위 공식의 값이 진실원.

## 3. factor 가중치 prior + 근거

양의 6개 factor, 합 = 1.00 (정규화되므로 비율만 의미):

| factor (label) | w(prior) | 근거 |
|---|---|---|
| 코호트 선호도 | 0.25 | 동학년·동진로 선배의 실제 수강이 가장 직접적 적합 신호 (+가중치 튜닝 정답과 동일 출처) |
| 콘텐츠 유사도 | 0.22 | 이수과목과 강의계획서 내용 연계 |
| 시간 가중 평점 | 0.18 | 최근 학기 평판/만족 — **현재 평점 데이터 없음 → 당분간 N/A** |
| 사용자 선호 매칭 | 0.15 | 학생이 명시한 선호(영역/방식) |
| 트랙 충족도 | 0.12 | 졸업요건(교양 영역) 충족 — **A6 미정 → 당분간 N/A** |
| 학년 적합도 | 0.08 | 권장학년 부합 (약한 신호) |

N/A 2개는 §2 정규화로 자동 흡수된다(분모에서 빠져 점수를 인위적으로 낮추지 않음).

## 4. 감산·컷오프 prior

- `PREREQ_PENALTY_MAX = 40` — 선수 완전 미충족 시 −40 (예: 80 → 40, 강추→유보). 완전 차단(0점)은 restriction 몫이므로 감산 상한은 40.
- 컷오프 (`GRADE_CUTOFFS`): **강추 ≥ 80 / 고려 60~79 / 유보 < 60**.

## 5. 파일 구조

| 파일 | 책임 |
|---|---|
| `backend/app/engines/recommender/weights.py` | **신규** — `FACTOR_WEIGHTS: dict[str,float]`, `PREREQ_PENALTY_MAX: int`, `GRADE_CUTOFFS`. 튜닝은 이 파일 한 곳. |
| `backend/app/engines/recommender/scoring.py` | **신규** — `Factor`, `ScoredCandidate`, `score_candidate(...)`. |
| `backend/tests/unit/test_scoring.py` | **신규** — 정규화·감산·N/A·등급·엣지(전부 N/A) 검증 (TDD, mock signal). |

`FACTOR_WEIGHTS` 키는 §3의 6개 label 문자열. signals dict의 키도 동일 label을 쓴다(단일 진실원 = `weights.py`).

## 6. 엣지 케이스 (테스트 대상)

- 모든 양의 signal이 None (W=0) → `score_percent = 0`, `grade = "유보"`, 양의 factor는 전부 N/A.
- `prereq_fulfillment = None` → 감산 0, 선이수 factor 미표시.
- `prereq_fulfillment = 0` → 감산 = `PREREQ_PENALTY_MAX`.
- 정규화 확인: 일부 factor N/A여도 나머지가 만점이면 score가 100 근처에 도달.

## 7. 범위 밖

- signal 계산(콘텐츠 유사도·코호트 통계·시간 가중 평점·사용자 선호·트랙·학년) — 별도 작업, 데이터/파서 의존.
- 실 가중치 학습(③ LTR) — A5 잔존, 데이터 확보 후.
- restriction 필터, LLM 통역(translator), 카드 A 오케스트레이션(`cards/card_a`).

## 8. 문서 갱신

- `OPEN_QUESTIONS.md` A5 → "점수 공식·가중치 prior·감산·컷오프 잠정 확정(`engines/recommender/weights.py`, `scoring.py`). 잔존: 실데이터 기반 재조정(정답 신호 = 졸업생 실제 수강)."

## 변경/구현 대상 파일 요약

| 파일 | 작업 |
|---|---|
| `app/engines/recommender/weights.py` | 신규 — 가중치/감산/컷오프 상수 |
| `app/engines/recommender/scoring.py` | 신규 — `score_candidate` + 모델 |
| `tests/unit/test_scoring.py` | 신규 — TDD |
| `docs/OPEN_QUESTIONS.md` | A5 갱신 |
