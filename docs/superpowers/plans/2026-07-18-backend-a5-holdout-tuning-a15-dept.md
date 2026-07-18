# A5 가중치 홀드아웃 튜닝 + A15 소속 변경 검증 Implementation Plan

> **진행 상태 (2026-07-18)**: Task 1~4 완료 (커밋 5033a65·29009b8·f49fcf2). Task 5(A15)는
> `ENROLLMENT_XLSX_PASSWORD` 부재로 사용자 입력 대기 — xlsx 복호화 없이는 학기별 소속
> 시퀀스를 얻을 수 없다 (alumni.json 은 최신 소속만 보존).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 2차 수령분 실이력(14,942명)으로 ① 추천 가중치·컷오프를 홀드아웃 검증으로 재조정(A5 잔여 종결), ② 소속 변경 2,258명을 분류해 "최신 소속" 잠정 결정을 실측 근거로 확정(A15 종결).

**Architecture:** `card_a.build`를 `collect`(풀·신호 수집, 가중치 무관)와 `rank`(가중 결합·차단, 가중치 의존)로 분리 — 평가 스크립트가 학생당 `collect` 1회 + 가중치 그리드마다 `rank`만 재실행해 튜닝 비용을 낮춘다. 홀드아웃 = 각 학생의 마지막 정규학기를 숨기고 이전 이력으로 `StudentInput` 구성, 숨긴 학기의 실제 수강(∩ 추천 풀)을 정답으로 Recall@K/MRR 측정. A15는 xlsx 원본(암호 필요)에서 학기별 소속 시퀀스를 뽑아 `dept_normalizer`로 4분류.

**Tech Stack:** 기존 스택 그대로 (raw sqlite3, pydantic, openpyxl+msoffcrypto). 신규 의존성 없음.

## Global Constraints

- 모든 명령은 `backend/`에서 `uv run ...`.
- 수정 허용: `app/cards/card_a.py`, `app/engines/recommender/weights.py`(**수치·주석만**), `scripts/evaluate_recommender.py`(신규), `docs/scoring_rationale.md`, `docs/OPEN_QUESTIONS.md`, 이 플랜 체크박스.
- **`scoring.py`·`hybrid.py` 로직 변경 금지** — 튜닝은 `weights.py`만 (weights.py 자체 규칙).
- 평가·분석은 결정론: 시드 42 고정, 표본 선정·순위 tie-break 명시.
- A15 분석 스크립트는 커밋하지 않는다(scratchpad) — A16 실측과 같은 방식으로 결과 수치만 `docs/OPEN_QUESTIONS.md`에 기록.
- 기존 미커밋(`.claude/settings.local.json`, `tests/integration/test_translator_live.py`) add 금지.
- 커밋 메시지 끝: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. push 금지.
- 가중치 갱신은 **실측이 prior보다 나을 때만** — 나쁘면 prior 유지 + 결과 보고(추측 단정 금지).

## 검증 기준 (전체)

1. Task 1 후 기존 테스트 전부 통과 (`uv run pytest tests/unit tests/integration -x`, translator_live 제외) = 리팩터 동등성.
2. baseline 평가가 표본 통계(스킵 사유 포함)와 Recall@8/@20·MRR을 출력.
3. 그리드 최적 구성이 **valid 절반에서도** baseline 이상 — tune에서만 좋으면 과적합으로 기각.
4. A15 분류 합계 = 소속 변경자 총수와 일치.

---

### Task 1: `card_a` collect/rank 분리 (동작 불변 리팩터)

**Files:**
- Modify: `backend/app/cards/card_a.py`

**Interfaces:**
- Produces: `Collected` NamedTuple, `collect(student, con, alumni, target_semester=TARGET_SEMESTER) -> Collected`, `rank(c: Collected) -> dict[str, ScoredCandidate]`. `build`는 둘을 호출하는 조립만 담당. 기존 `build` 시그니처·출력 불변.

- [ ] **Step 1: 분리 구현**

`build` 본문을 아래 구조로 재배치 (로직 변경 없음, 이동만):

```python
class Collected(NamedTuple):
    """가중치와 무관한 수집 결과 — rank가 가중 결합. 평가 스크립트 재사용점."""
    major_pool: list[sqlite3.Row]
    general_pool: list[sqlite3.Row]
    signals_by_label: dict[str, dict[str, float]]
    fulfill: dict[str, float | None]
    restrictions: list[sqlite3.Row]
    student_depts: set[str]


def collect(student, con, alumni, target_semester=TARGET_SEMESTER) -> Collected:
    # 기존 build 앞부분: taken/offered/풀 구성 → 신호 수집 → fulfillments
    # offered = course_queries.offered_in_semester(con, target_semester)
    # restrictions = course_queries.list_restrictions_for(con, pool_ids)
    ...


def rank(c: Collected) -> dict[str, ScoredCandidate]:
    major_ids = [r["course_id"] for r in c.major_pool]
    general_ids = [r["course_id"] for r in c.general_pool]
    scored = {
        **hybrid.combine(c.signals_by_label, c.fulfill, major_ids),
        **hybrid.combine(c.signals_by_label, c.fulfill, general_ids),
    }
    return restriction_filter.apply(scored, c.student_depts, True, c.restrictions)
```

- [ ] **Step 2: 기존 테스트로 동등성 확인**

Run: `uv run pytest tests/unit tests/integration --deselect tests/integration/test_translator_live.py -q`
Expected: 전부 PASS (스킵 제외).

- [ ] **Step 3: Commit**

```bash
git add backend/app/cards/card_a.py
git commit -m "refactor: card_a collect/rank 분리 — 홀드아웃 평가 재사용점 (A5)"
```

### Task 2: `scripts/evaluate_recommender.py` — 홀드아웃 baseline

**Files:**
- Create: `backend/scripts/evaluate_recommender.py`

**Interfaces:**
- Consumes: `card_a.collect`/`card_a.rank` (Task 1), `data/processed/alumni.json`, `s_compass_courses.db`.
- Produces: CLI. `uv run python scripts/evaluate_recommender.py [--sample N] [--grid]`.

- [ ] **Step 1: 케이스 구성 + 평가 루프 구현**

핵심 설계 (docstring에 명시할 한계 포함):

```python
SEED = 42
MIN_REGULAR_SEMESTERS = 4          # 이전 이력 3학기+ 숨긴 학기 1
# 케이스: 마지막 정규학기 숨김. truth = 그 학기 수강(별칭 확장) ∩ 추천 풀.
#   풀 밖 과목(폐강 등)은 채점 대상 아님. truth 공집합이면 스킵(카운트 보고).
# StudentInput: department=record.department, extra_majors=double/triple,
#   year=min(4, (완료 정규학기수)//2 + 1)  ← enrollment_inference 원칙,
#   taken=숨긴 학기 이전 전체(계절 포함, 동계 혼입 한계는 docstring).
# 누수 방지: 평가 학생은 alumni에서 제외(leave-one-out).
#   한계: 타 학생 미래 이력은 코호트에 남음(시점 절단 아님) — 문서화.
# 지표: Recall@8(카드 노출 4+4), Recall@20(후보 캡), MRR. tie-break=(−score, cid).
```

- [ ] **Step 2: baseline 실행**

Run: `uv run python scripts/evaluate_recommender.py --sample 400`
Expected: `케이스 N (스킵: 풀없음 a, 정답없음 b)` + baseline 지표 출력. 소요 시간 확인(그리드 예산 판단).

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/evaluate_recommender.py
git commit -m "feat: A5 홀드아웃 평가 스크립트 — 마지막 학기 숨김, Recall@K/MRR"
```

### Task 3: `--grid` 가중치 튜닝 (tune/valid 이분)

**Files:**
- Modify: `backend/scripts/evaluate_recommender.py`

- [ ] **Step 1: 그리드 구현**

- 표본을 인덱스 홀짝으로 tune/valid 이분 (시드 42 셔플 후).
- 튜닝 대상: 코호트·콘텐츠·학년 3요인 {0.05..0.40, step 0.05}. **선호 매칭은 0.15 고정** — 졸업생 이력에 선호 입력이 없어 튜닝 정답이 없다(재정규화로 평가에선 자동 제외됨을 docstring 명시).
- 학생당 `collect` 1회 캐시 → 구성마다 `weights.FACTOR_WEIGHTS` in-place 갱신 후 `rank`만 재실행.
- 출력: baseline 행 + tune 상위 10 구성의 tune/valid 지표 markdown 표.

- [ ] **Step 2: 실행·판정**

Run: `uv run python scripts/evaluate_recommender.py --sample 400 --grid`
Expected: 최적 구성이 valid에서도 baseline 이상이면 채택 후보. 아니면 prior 유지 보고.

- [ ] **Step 3: 컷오프 캘리브레이션 리포트 추가**

최종 가중치로 valid 케이스의 후보를 등급 버킷(강추/고려/유보)으로 나눠 버킷별 적중률(P(수강 | 등급)) 출력. 단조 분리되면 컷오프 80/60 유지, 아니면 조정 근거 보고.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/evaluate_recommender.py
git commit -m "feat: A5 가중치 그리드 튜닝 + 등급 컷오프 캘리브레이션"
```

### Task 4: `weights.py` 갱신 + 문서 + A5 종결

**Files:**
- Modify: `backend/app/engines/recommender/weights.py` (수치·주석), `docs/scoring_rationale.md`, `docs/OPEN_QUESTIONS.md`

- [ ] **Step 1: 실측 결과에 따라 `FACTOR_WEIGHTS`/`GRADE_CUTOFFS` 갱신** (valid 개선 확인된 경우만; "잠정 수치" 경고 문구를 실측 근거 참조로 교체)
- [ ] **Step 2: 전체 테스트 재실행** — `uv run pytest tests/unit tests/integration --deselect tests/integration/test_translator_live.py -q` 전부 PASS
- [ ] **Step 3: `docs/scoring_rationale.md`에 방법론·수치(홀드아웃 설계, baseline↔채택 구성, 버킷 적중률) 추가, `docs/OPEN_QUESTIONS.md` A5를 결정 완료로 이동**
- [ ] **Step 4: Commit**

```bash
git add backend/app/engines/recommender/weights.py docs/scoring_rationale.md docs/OPEN_QUESTIONS.md
git commit -m "feat: A5 종결 — 가중치·컷오프 홀드아웃 실측 반영"
```

### Task 5: A15 소속 변경 2,258명 분류 (분석 스크립트는 미커밋)

**Files:**
- Create (scratchpad, 미커밋): `analyze_dept_changes.py`
- Modify: `docs/OPEN_QUESTIONS.md`

**Interfaces:**
- Consumes: `data/external/*수강내역*.xlsx` (`ENROLLMENT_XLSX_PASSWORD` 필요 — 없으면 사용자에게 요청), `build_alumni_from_enrollment.read_rows/_decrypt`, `app.core.dept_normalizer.{canonical, DEPT_COLLEGES, FACULTY_COLLEGES}`.

- [ ] **Step 1: 분류 구현** — 학생별 시간순 소속 시퀀스에서 인접 전이를 분류:

```python
# ① canonical 동일        → 표기 변동 (실변경 아님, A16 별칭)
# ② 이전=계열/학부 입학 표기(FACULTY_COLLEGES) → 학과 배정 (전과 아님)
# ③ canonical 상이 + 같은 대학(DEPT_COLLEGES 역인덱스) → 단대 내 이동
# ④ canonical 상이 + 다른 대학 → 단대 간 이동(전과 추정)
# 학생 단위 라벨 = 가장 "강한" 전이 (④>③>②>①). 합계가 2,258과 일치하는지 검증.
```

- [ ] **Step 2: 실행·판정** — 분류 분포 + 각 유형 예시 3건 출력. "최신 소속 채택"이 ②(배정)·③④(졸업 시점 소속) 모두에서 타당한지 판단. 반례(예: 마지막 학기만 튀는 노이즈)가 유의미하면 보고.
- [ ] **Step 3: `docs/OPEN_QUESTIONS.md` A15 → 결정 완료 이동** (실측 표 포함, A16 스타일)
- [ ] **Step 4: Commit**

```bash
git add docs/OPEN_QUESTIONS.md
git commit -m "docs: A15 종결 — 소속 변경 2,258명 분류 실측, 최신 소속 채택 확정"
```
