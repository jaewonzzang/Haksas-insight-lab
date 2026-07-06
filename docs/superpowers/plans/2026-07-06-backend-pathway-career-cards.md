# W4: pathway/career 엔진 + 카드 C/D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `engines/pathway/distribution` + `engines/career/{embedding, similarity, cluster}` + `cards/card_c`·`card_d`를 구현해, 학생 입력 → `CardC`(다전공 경로 분포)·`CardD`(유사 졸업생 진로)·`ClusterEvidence`(유사 판정 근거)를 결정론적으로 산출한다. mock 졸업생 생성기의 학과명·수강 샘플링도 DB 원문 기준으로 현실화한다.

**Architecture:** 카드 D 흐름(ARCHITECTURE 고정): 임베딩 → 유사도 top-N → 클러스터. 임베딩 = **과목 ID TF-IDF** (A10 확정), 클러스터 = **K-Means(random_state 고정)** (A11 확정), 클러스터 라벨 = 구성원 최빈 진로 라벨(결정론). 카드 C = 코호트(학부 합집합 매칭, 비면 전체 폴백) 다전공 조합별 집계. engines는 정형 구조만 반환하고 한국어 라벨/문구 조립은 cards 계층에서 (W5 전까지 결정론 폴백, LLM 통역으로 교체 예정). `card_d.build`는 `(CardD, ClusterEvidence)` 튜플 반환 — 두 산출물이 같은 top-N 계산을 공유하기 때문.

**Tech Stack:** Python 3.12 + uv, scikit-learn(TfidfVectorizer, KMeans)+numpy, raw sqlite3, pydantic v2, pytest.

## Global Constraints

- 모든 명령은 `backend/` 디렉토리에서 실행 (`uv run ...`).
- **`engines/` = 정형 결과만, 자연어 금지.** 라벨 문자열("단일전공 유지" 등)·문구 조립은 `cards/`에서.
- 결정론 필수: KMeans `random_state=0, n_init=10`, 정렬 tie-break 명시, mock 생성기 `seed=42` 유지.
- 확정 결정: A10=과목 ID TF-IDF, A11=K-Means, A13=ClusterEvidence를 결정론 분해로 채움.
- `frontend/`, `docs/` 수정 금지 (플랜 파일 체크박스 갱신 제외). `llm/`, `api/`, `engines/recommender`, `cards/card_a`, `core/`, `parsers/`, `db/`, `schemas/` 수정 금지.
- `data/mock/alumni.json`은 git 제외 데이터 — 재생성만, 커밋 대상 아님.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: mock 졸업생 생성기 현실화

**Files:**
- Modify: `backend/scripts/generate_mock_alumni.py`
- Test: `backend/tests/unit/test_generate_mock_alumni.py` (기존 — 영향 확인 후 필요한 곳만 갱신)

**Interfaces:**
- Produces: `data/mock/alumni.json` 재생성 — 학과명이 DB `courses.department` 원문과 일치, 수강 이력이 자기 학과+교양 편향. Task 3~8의 코호트 매칭·신호 품질 전제.

배경: 현재 `DEPARTMENTS = ["아트&테크놀로지", "컴퓨터공학과", "경영학과"]`는 DB 원문("아트&테크놀로지학과")과 불일치 → `dept_normalizer` 합집합 코호트 매칭 0명. 수강 이력도 전체 ~1,800과목 무작위 균등이라 협업 신호가 눌림 (W3 보고).

- [x] **Step 1: 기존 테스트 확인**

Run: `uv run pytest tests/unit/test_generate_mock_alumni.py -v` — 현재 통과 상태와 assert 내용 파악 (학과명/구조 하드코딩 여부).

- [x] **Step 2: 생성기 수정**

`generate_mock_alumni.py` 변경점:

```python
# DB courses.department 원문과 일치 (dept_normalizer 합집합 코호트 매칭 전제)
DEPARTMENTS = [
    "아트&테크놀로지학과",
    "미디어&엔터테인먼트학과",
    "신문방송학과",
    "컴퓨터공학과",
]
GENERAL_DEPT = "전인교육원"
```

`_load_course_pool`을 학과별 풀로 확장:

```python
def _load_course_pools(db_path: Path) -> tuple[dict[str, list[str]], list[str]]:
    """학과별 course_id 풀 + 교양(전인교육원) 풀. DB 없으면 합성 폴백."""
    if not db_path.exists():
        return {d: list(_SYNTHETIC_POOL) for d in DEPARTMENTS}, list(_SYNTHETIC_POOL)
    con = sqlite3.connect(db_path)
    try:
        by_dept: dict[str, list[str]] = {}
        for dept in [*DEPARTMENTS, GENERAL_DEPT]:
            rows = con.execute(
                "SELECT course_id FROM courses WHERE department = ? "
                "AND course_type = 'regular' ORDER BY course_id",
                (dept,),
            ).fetchall()
            by_dept[dept] = [r[0] for r in rows] or list(_SYNTHETIC_POOL)
    finally:
        con.close()
    return {d: by_dept[d] for d in DEPARTMENTS}, by_dept[GENERAL_DEPT]
```

`_one_record`의 학기별 샘플링을 편향 샘플링으로 (courses_per_term=5 기준 자기 학과 3 + 교양 2):

```python
def _sample_term(dept_pool: list[str], general_pool: list[str], rng: random.Random) -> list[str]:
    own = rng.sample(dept_pool, min(3, len(dept_pool)))
    gen = rng.sample(general_pool, min(2, len(general_pool)))
    return own + gen
```

`_one_record`/`generate_records`/`main`의 시그니처와 호출을 위 구조에 맞게 최소 조정 (`pool` 단일 리스트 → `dept_pool`+`general_pool`). seed=42, n_per_dept=60 유지 → 240명.

- [x] **Step 3: 테스트 갱신·통과 + 재생성**

기존 테스트가 구 시그니처/학과명을 참조하면 새 구조로 갱신 (검증 의도 유지).

Run: `uv run pytest tests/unit/test_generate_mock_alumni.py tests/unit/test_mock_alumni.py -v` — PASS.
Run: `uv run python scripts/generate_mock_alumni.py` — `wrote 240 records` 확인.
Run: `uv run pytest tests/unit tests/integration -q` — 전체 회귀 (기존 카드 A 통합 스모크 포함) 실패 0.

- [x] **Step 4: Commit**

```bash
git add scripts/generate_mock_alumni.py tests/unit/test_generate_mock_alumni.py
git commit -m "feat: mock 졸업생 학과명 DB 원문화 + 학과 편향 수강 샘플링"
```

---

### Task 2: `engines/pathway/distribution.aggregate` (TDD)

**Files:**
- Modify: `backend/app/engines/pathway/distribution.py`
- Test: `backend/tests/unit/engines/test_pathway_distribution.py` (신규)

**Interfaces:**
- Consumes: `AlumniRecord.majors` (`Major(label, role: primary|double|triple|minor, credits)`).
- Produces: `aggregate(alumni: Sequence[AlumniRecord]) -> list[PathwayGroup]`,
  `PathwayGroup(extra_majors: list[str], count: int, avg_primary_credits: float | None, avg_second_credits: float | None, avg_third_credits: float | None)` — count 내림차순, 동수는 extra_majors 사전순. Task 3 `card_c`가 소비.

- [x] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_pathway_distribution.py`:

```python
"""pathway/distribution — 다전공 조합별 집계 (정형만)."""

from app.adapters.alumni_types import AlumniRecord, Major
from app.engines.pathway import distribution


def _alum(aid, majors):
    return AlumniRecord(alumni_id=aid, department="아트&테크놀로지학과", majors=majors)


def _m(label, role, credits):
    return Major(label=label, role=role, credits=credits)


ALUMNI = [
    _alum("a1", [_m("아트&테크놀로지학과", "primary", 80.0)]),
    _alum("a2", [_m("아트&테크놀로지학과", "primary", 84.0)]),
    _alum("a3", [_m("아트&테크놀로지학과", "primary", 60.0), _m("컴퓨터공학", "double", 40.0)]),
    _alum("a4", [_m("아트&테크놀로지학과", "primary", 64.0), _m("컴퓨터공학", "double", 44.0)]),
    _alum("a5", [_m("아트&테크놀로지학과", "primary", 61.0), _m("경영학", "double", 38.0),
                 _m("심리학", "triple", 22.0)]),
]


def test_groups_and_averages():
    groups = distribution.aggregate(ALUMNI)
    assert [(g.extra_majors, g.count) for g in groups] == [
        ([], 2),
        (["컴퓨터공학"], 2),
        (["경영학", "심리학"], 1),
    ]
    single = groups[0]
    assert single.avg_primary_credits == 82.0
    assert single.avg_second_credits is None
    double = groups[1]
    assert double.avg_primary_credits == 62.0
    assert double.avg_second_credits == 42.0
    triple = groups[2]
    assert triple.avg_third_credits == 22.0


def test_tie_breaks_lexicographic():
    alumni = [
        _alum("b1", [_m("X", "primary", 60.0), _m("경영학", "double", 40.0)]),
        _alum("b2", [_m("X", "primary", 60.0), _m("심리학", "double", 40.0)]),
    ]
    groups = distribution.aggregate(alumni)
    assert [g.extra_majors for g in groups] == [["경영학"], ["심리학"]]


def test_empty_input():
    assert distribution.aggregate([]) == []
```

(참고: 동수 그룹 정렬 — `([], 2)` vs `(["컴퓨터공학"], 2)`는 extra_majors 사전순으로 빈 리스트가 먼저.)

- [x] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines/test_pathway_distribution.py -v` / Expected: FAIL.

- [x] **Step 3: 구현**

`distribution.py` (기존 docstring 현행화):

```python
"""다전공 경로 분포 집계: majors 조합별 인원·평균 학점 (정형만).

라벨 문자열 조립("단일전공 유지" 등)은 cards/card_c 책임.
"""

from typing import Optional, Sequence

from pydantic import BaseModel

from app.adapters.alumni_types import AlumniRecord

_ROLE_ORDER = {"double": 0, "triple": 1, "minor": 2}


class PathwayGroup(BaseModel):
    extra_majors: list[str]  # primary 제외, role 순서 (double → triple → minor)
    count: int
    avg_primary_credits: Optional[float]
    avg_second_credits: Optional[float]
    avg_third_credits: Optional[float]


def _mean(values: list[float]) -> Optional[float]:
    return round(sum(values) / len(values), 1) if values else None


def aggregate(alumni: Sequence[AlumniRecord]) -> list[PathwayGroup]:
    buckets: dict[tuple[str, ...], list[AlumniRecord]] = {}
    for record in alumni:
        extras = sorted(
            (m for m in record.majors if m.role in _ROLE_ORDER),
            key=lambda m: _ROLE_ORDER[m.role],
        )
        key = tuple(m.label for m in extras)
        buckets.setdefault(key, []).append(record)

    groups: list[PathwayGroup] = []
    for key, members in buckets.items():
        def _credits(pick) -> list[float]:
            out = []
            for r in members:
                m = pick(r)
                if m is not None and m.credits is not None:
                    out.append(m.credits)
            return out

        def _primary(r):
            return next((m for m in r.majors if m.role == "primary"), None)

        def _nth_extra(r, i):
            extras_r = sorted(
                (m for m in r.majors if m.role in _ROLE_ORDER),
                key=lambda m: _ROLE_ORDER[m.role],
            )
            return extras_r[i] if len(extras_r) > i else None

        groups.append(
            PathwayGroup(
                extra_majors=list(key),
                count=len(members),
                avg_primary_credits=_mean(_credits(_primary)),
                avg_second_credits=_mean(_credits(lambda r: _nth_extra(r, 0))),
                avg_third_credits=_mean(_credits(lambda r: _nth_extra(r, 1))),
            )
        )
    groups.sort(key=lambda g: (-g.count, g.extra_majors))
    return groups
```

- [x] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines/test_pathway_distribution.py -v` / Expected: 3 PASS.

- [x] **Step 5: Commit**

```bash
git add app/engines/pathway/distribution.py tests/unit/engines/test_pathway_distribution.py
git commit -m "feat: pathway/distribution 다전공 조합별 집계"
```

---

### Task 3: `cards/card_c.build` (TDD)

**Files:**
- Modify: `backend/app/cards/card_c.py`
- Test: `backend/tests/unit/cards/test_card_c.py` (신규)

**Interfaces:**
- Consumes: `distribution.aggregate`(Task 2), `candidate_departments`(W2), `CardC`/`PathwayEntry`/`PathwayCredits`(W2 schemas), `StudentInput`, `AlumniRecord`.
- Produces: `build(student: StudentInput, alumni: list[AlumniRecord]) -> CardC` — W6 `/analyze`가 소비. DB 불필요.

설계 (frontend `dashboard.fixture.ts` 표기 관례 준수):
- 코호트 = department가 `{student.department} ∪ candidate_departments(student.department)`에 속한 졸업생. 비면 전체 폴백 (`cohort_label` = "전체 졸업생 N명").
- 상위 4개 그룹 + 나머지 "기타 경로 N건"(dim=True, credits 전부 None, detail_label "").
- 라벨: `[]` → "단일전공 유지" / `[X]` → "X (다전공)" / `[X, Y]` → "X + Y (3전공)".
- detail_label: 단일전공 → "이 경로 졸업생 N명의 평균 이수 학점", 그 외 → "...평균 추가 이수 학점".
- `share_percent = round(count/total*100)`, `bar_percent = round(count/max_count*100)` (최상위=100), 최상위에만 `tag="최다"`.
- `baseline_note` = 학칙 발췌 상수 (frontend fixture와 동일 문구):

```python
BASELINE_NOTE = (
    "추가전공은 주 전공을 포함하여 제3전공까지 이수할 수 있다 · "
    "연계전공·학생설계전공의 이수학점은 36학점 이상을 원칙으로 한다 · "
    "심화전공은 전공 60학점 이상 이수함을 원칙으로 한다 · "
    "다전공 이수로 전공간 이수과목이 중복된 경우 6학점 이내에서 중복 인정될 수 있으며, "
    "본인의 학점 인정 사항은 소속 학과 협의에 따른다."
)
```

- [x] **Step 1: 실패하는 테스트 작성**

`tests/unit/cards/test_card_c.py`:

```python
"""card_c — 코호트 필터·라벨·기타 묶음·표기 규칙."""

from app.adapters.alumni_types import AlumniRecord, Major
from app.cards import card_c
from app.schemas.input import StudentInput


def _alum(aid, dept, extras):
    majors = [Major(label=dept, role="primary", credits=70.0)]
    for i, label in enumerate(extras):
        majors.append(Major(label=label, role=("double", "triple")[i], credits=40.0))
    return AlumniRecord(alumni_id=aid, department=dept, majors=majors)


STUDENT = StudentInput(student_id="S1", department="지식융합미디어학부")

# 코호트(합집합 매칭) 6명: 단일 3, 컴퓨터공학 2, 경영학 1 / 비코호트 1명
ALUMNI = (
    [_alum(f"s{i}", "아트&테크놀로지학과", []) for i in range(3)]
    + [_alum(f"c{i}", "신문방송학과", ["컴퓨터공학"]) for i in range(2)]
    + [_alum("b1", "미디어&엔터테인먼트학과", ["경영학"])]
    + [_alum("x1", "화학과", ["심리학"])]  # 코호트 밖 — 제외돼야 함
)


def test_cohort_filter_and_entries():
    card = card_c.build(STUDENT, ALUMNI)
    assert card.cohort_label == "지식융합미디어학부 · 졸업생 6명"
    top = card.entries[0]
    assert top.label == "단일전공 유지"
    assert top.tag == "최다"
    assert top.count == 3
    assert top.share_percent == 50
    assert top.bar_percent == 100
    assert "평균 이수 학점" in top.detail_label
    second = card.entries[1]
    assert second.label == "컴퓨터공학 (다전공)"
    assert second.tag is None
    assert "평균 추가 이수 학점" in second.detail_label
    assert card.baseline_note.startswith("추가전공은")


def test_fallback_to_all_when_no_cohort():
    student = StudentInput(student_id="S2", department="화학과")
    card = card_c.build(student, ALUMNI[:1])  # 아트&테크만 → 화학과 코호트 없음
    assert card.cohort_label == "전체 졸업생 1명"


def test_other_bucket_dim():
    alumni = ALUMNI[:6] + [
        _alum("e1", "신문방송학과", ["심리학"]),
        _alum("e2", "신문방송학과", ["데이터사이언스"]),
    ]
    card = card_c.build(STUDENT, alumni)
    other = card.entries[-1]
    assert other.dim is True
    assert other.label == "기타 경로 2건"
    assert other.credits.major1 is None


def test_empty_alumni():
    card = card_c.build(STUDENT, [])
    assert card.entries == []
```

주의: `test_other_bucket_dim`은 그룹 5종(단일3·컴공2·경영1·심리1·데사1) → 상위 4개 + 기타 1건이 아니라, 동수(1) 그룹의 사전순 정렬로 상위 4번째가 결정된다. 구현 후 실제 산출로 기타 묶음 count를 확인하고 assert(`기타 경로 N건`)를 실측값으로 맞출 것 — 정렬 규칙(count desc, extra_majors 사전순)은 완화 금지.

- [x] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/cards/test_card_c.py -v` / Expected: FAIL.

- [x] **Step 3: 구현**

`card_c.py`:

```python
"""카드 C 오케스트레이터: 코호트 → 다전공 분포 집계 → CardC.

라벨/문구는 결정론 조립 (W5 LLM 통역 대상 아님 — 카드 C는 정형 표기만).
"""

from app.adapters.alumni_types import AlumniRecord
from app.core.dept_normalizer import candidate_departments
from app.engines.pathway.distribution import PathwayGroup, aggregate
from app.schemas.cards import CardC, PathwayCredits, PathwayEntry
from app.schemas.input import StudentInput

TOP_GROUPS = 4

BASELINE_NOTE = (
    "추가전공은 주 전공을 포함하여 제3전공까지 이수할 수 있다 · "
    "연계전공·학생설계전공의 이수학점은 36학점 이상을 원칙으로 한다 · "
    "심화전공은 전공 60학점 이상 이수함을 원칙으로 한다 · "
    "다전공 이수로 전공간 이수과목이 중복된 경우 6학점 이내에서 중복 인정될 수 있으며, "
    "본인의 학점 인정 사항은 소속 학과 협의에 따른다."
)


def _label(group: PathwayGroup) -> str:
    if not group.extra_majors:
        return "단일전공 유지"
    if len(group.extra_majors) == 1:
        return f"{group.extra_majors[0]} (다전공)"
    return f"{' + '.join(group.extra_majors)} (3전공)"


def build(student: StudentInput, alumni: list[AlumniRecord]) -> CardC:
    depts = {student.department, *candidate_departments(student.department)}
    cohort = [r for r in alumni if r.department in depts]
    if cohort:
        cohort_label_prefix = student.department
    else:
        cohort = list(alumni)
        cohort_label_prefix = "전체"
    label = (
        f"{cohort_label_prefix} · 졸업생 {len(cohort)}명"
        if cohort_label_prefix != "전체"
        else f"전체 졸업생 {len(cohort)}명"
    )
    if not cohort:
        return CardC(cohort_label=label, entries=[], baseline_note=BASELINE_NOTE)

    groups = aggregate(cohort)
    total = len(cohort)
    max_count = groups[0].count
    top, rest = groups[:TOP_GROUPS], groups[TOP_GROUPS:]

    entries: list[PathwayEntry] = []
    for i, g in enumerate(top):
        detail_noun = "평균 이수 학점" if not g.extra_majors else "평균 추가 이수 학점"
        entries.append(
            PathwayEntry(
                id=f"p{i + 1}",
                label=_label(g),
                tag="최다" if i == 0 else None,
                count=g.count,
                share_percent=round(g.count / total * 100),
                bar_percent=round(g.count / max_count * 100),
                detail_label=f"이 경로 졸업생 {g.count}명의 {detail_noun}",
                credits=PathwayCredits(
                    major1=g.avg_primary_credits,
                    major2=g.avg_second_credits,
                    major3=g.avg_third_credits,
                ),
            )
        )
    if rest:
        rest_count = sum(g.count for g in rest)
        entries.append(
            PathwayEntry(
                id="other",
                label=f"기타 경로 {len(rest)}건",
                count=rest_count,
                share_percent=round(rest_count / total * 100),
                bar_percent=round(rest_count / max_count * 100),
                detail_label="",
                credits=PathwayCredits(major1=None, major2=None, major3=None),
                dim=True,
            )
        )
    return CardC(cohort_label=label, entries=entries, baseline_note=BASELINE_NOTE)
```

- [x] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/cards/test_card_c.py -v` / Expected: 4 PASS.

- [x] **Step 5: Commit**

```bash
git add app/cards/card_c.py tests/unit/cards/test_card_c.py
git commit -m "feat: card_c 다전공 경로 분포 (코호트·기타 묶음·학칙 발췌)"
```

---

### Task 4: `engines/career/embedding` — 과목 ID TF-IDF (TDD)

**Files:**
- Modify: `backend/app/engines/career/embedding.py`
- Test: `backend/tests/unit/engines/test_career_embedding.py` (신규)

**Interfaces:**
- Produces: `embed_sets(alumni_course_sets: Sequence[Iterable[str]], student_courses: Iterable[str]) -> tuple[matrix, vector] | None` — TF-IDF sparse 행렬(졸업생 N행) + 학생 1행. 유효 문서 없으면 None. Task 5·7이 소비.

- [x] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_career_embedding.py`:

```python
"""career/embedding — 과목 ID TF-IDF (A10 확정)."""

from sklearn.metrics.pairwise import cosine_similarity

from app.engines.career import embedding

SETS = [
    {"CSE1010", "CSE2020", "AAT3001"},
    {"REL1001", "PHI1001"},
]


def test_embed_shapes_and_similarity():
    result = embedding.embed_sets(SETS, {"CSE1010", "CSE2020"})
    assert result is not None
    matrix, student = result
    assert matrix.shape[0] == 2
    sims = cosine_similarity(student, matrix)[0]
    assert sims[0] > sims[1]  # 겹치는 졸업생과 더 유사


def test_unseen_student_courses_zero_vector():
    result = embedding.embed_sets(SETS, {"ZZZ9999"})
    matrix, student = result
    assert student.nnz == 0  # 어휘 밖 → 영벡터


def test_empty_alumni_returns_none():
    assert embedding.embed_sets([], {"CSE1010"}) is None
    assert embedding.embed_sets([set(), set()], {"CSE1010"}) is None
```

- [x] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines/test_career_embedding.py -v` / Expected: FAIL.

- [x] **Step 3: 구현**

`embedding.py` (기존 docstring 현행화 — A10 확정 명시):

```python
"""이수경로 임베딩: 과목 ID TF-IDF (A10 확정 — mock 단계).

문서 = 졸업생 1명의 이수 course_id 집합을 공백 결합한 문자열.
실데이터 수령 후 표현(설명 임베딩 등) 재검토 — OPEN_QUESTIONS A10 잔여.
"""

from typing import Iterable, Optional, Sequence, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer


def _doc(courses: Iterable[str]) -> str:
    return " ".join(sorted(courses))


def embed_sets(
    alumni_course_sets: Sequence[Iterable[str]],
    student_courses: Iterable[str],
) -> Optional[Tuple[object, object]]:
    docs = [_doc(s) for s in alumni_course_sets]
    if not any(docs):
        return None
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(docs)
    student = vectorizer.transform([_doc(student_courses)])
    return matrix, student
```

- [x] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines/test_career_embedding.py -v` / Expected: 3 PASS.

- [x] **Step 5: Commit**

```bash
git add app/engines/career/embedding.py tests/unit/engines/test_career_embedding.py
git commit -m "feat: career/embedding 과목 ID TF-IDF"
```

---

### Task 5: `engines/career/similarity.top_n` (TDD)

**Files:**
- Modify: `backend/app/engines/career/similarity.py`
- Test: `backend/tests/unit/engines/test_career_similarity.py` (신규)

**Interfaces:**
- Consumes: Task 4의 (matrix, student_vec).
- Produces: `top_n(student_vec, alumni_matrix, n: int) -> list[tuple[int, float]]` — (졸업생 행 인덱스, 코사인 점수) 점수 내림차순, 동점은 인덱스 오름차순(결정론). Task 7이 소비.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_career_similarity.py`:

```python
"""career/similarity — 코사인 top-N (결정론 tie-break)."""

import numpy as np

from app.engines.career import similarity


def test_top_n_orders_by_score_then_index():
    matrix = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]])
    student = np.array([[1.0, 0.0]])
    result = similarity.top_n(student, matrix, 3)
    assert [i for i, _ in result] == [0, 2, 1]  # 동점(0,2)은 인덱스순
    assert result[0][1] == 1.0


def test_n_larger_than_rows():
    matrix = np.array([[1.0, 0.0]])
    student = np.array([[1.0, 0.0]])
    assert len(similarity.top_n(student, matrix, 10)) == 1
```

- [ ] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines/test_career_similarity.py -v` / Expected: FAIL.

- [ ] **Step 3: 구현**

`similarity.py` (docstring 현행화):

```python
"""학생 벡터 ↔ 졸업생 행렬 코사인 유사도 top-N (결정론)."""

from typing import List, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def top_n(student_vec, alumni_matrix, n: int) -> List[Tuple[int, float]]:
    scores = cosine_similarity(student_vec, alumni_matrix)[0]
    order = np.lexsort((np.arange(len(scores)), -scores))  # 점수 desc, 인덱스 asc
    return [(int(i), float(scores[i])) for i in order[:n]]
```

- [ ] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines/test_career_similarity.py -v` / Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/engines/career/similarity.py tests/unit/engines/test_career_similarity.py
git commit -m "feat: career/similarity 코사인 top-N"
```

---

### Task 6: `engines/career/cluster` — K-Means (TDD)

**Files:**
- Modify: `backend/app/engines/career/cluster.py`
- Test: `backend/tests/unit/engines/test_career_cluster.py` (신규)

**Interfaces:**
- Consumes: top-N 졸업생 레코드 + 그 임베딩 행렬(행 정렬 일치).
- Produces: `cluster(records: Sequence[AlumniRecord], embeddings, k: int = 3) -> list[ClusterGroup]`,
  `ClusterGroup(label: str, career_type: Literal["job","grad","other"], count: int)` — 라벨 = 클러스터 구성원 최빈 `career.label`(None → "미분류"/type None → "other"), 동일 (label, career_type) 클러스터는 병합, count 내림차순·라벨 사전순. Task 7이 소비.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/engines/test_career_cluster.py`:

```python
"""career/cluster — K-Means(A11 확정) + 최빈 진로 라벨."""

import numpy as np

from app.adapters.alumni_types import AlumniRecord, Career
from app.engines.career import cluster


def _alum(aid, ctype, label):
    return AlumniRecord(
        alumni_id=aid, department="컴퓨터공학과",
        career=Career(type=ctype, label=label),
    )


# 임베딩 공간에서 뚜렷이 갈리는 두 무리
RECORDS = [
    _alum("a1", "job", "IT 취업"),
    _alum("a2", "job", "IT 취업"),
    _alum("a3", "grad", "국내 대학원 (CS)"),
    _alum("a4", "grad", "국내 대학원 (CS)"),
]
EMB = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]])


def test_two_clear_clusters():
    groups = cluster.cluster(RECORDS, EMB, k=2)
    assert [(g.label, g.career_type, g.count) for g in groups] == [
        ("IT 취업", "job", 2),
        ("국내 대학원 (CS)", "grad", 2),
    ]


def test_deterministic():
    a = cluster.cluster(RECORDS, EMB, k=2)
    b = cluster.cluster(RECORDS, EMB, k=2)
    assert a == b


def test_k_capped_by_records():
    groups = cluster.cluster(RECORDS[:1], EMB[:1], k=3)
    assert len(groups) == 1
    assert groups[0].count == 1


def test_none_career_bucketed():
    records = [AlumniRecord(alumni_id="x", department="d")] * 2
    groups = cluster.cluster(records, EMB[:2], k=1)
    assert groups[0].label == "미분류"
    assert groups[0].career_type == "other"
```

(`test_two_clear_clusters`의 정렬: 동수(2,2)는 라벨 사전순 — "IT 취업" < "국내 대학원 (CS)".)

- [ ] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/engines/test_career_cluster.py -v` / Expected: FAIL.

- [ ] **Step 3: 구현**

`cluster.py` (docstring 현행화 — A11 확정 명시):

```python
"""유사 졸업생 클러스터링: K-Means (A11 확정 — mock 단계, random_state 고정).

클러스터 라벨 = 구성원 최빈 career.label (결정론). 실데이터 후 HDBSCAN 재검토.
"""

from collections import Counter
from typing import Literal, Optional, Sequence

from pydantic import BaseModel
from sklearn.cluster import KMeans

from app.adapters.alumni_types import AlumniRecord

UNLABELED = "미분류"


class ClusterGroup(BaseModel):
    label: str
    career_type: Literal["job", "grad", "other"]
    count: int


def _majority(records: Sequence[AlumniRecord]) -> tuple[str, str]:
    labels = Counter(
        (r.career.label if r.career and r.career.label else UNLABELED) for r in records
    )
    types = Counter(
        (r.career.type if r.career and r.career.type else "other") for r in records
    )
    # 최빈, 동수는 사전순 (결정론)
    label = min(labels, key=lambda x: (-labels[x], x))
    ctype = min(types, key=lambda x: (-types[x], x))
    return label, ctype


def cluster(
    records: Sequence[AlumniRecord], embeddings, k: int = 3
) -> list[ClusterGroup]:
    if not records:
        return []
    k = min(k, len(records))
    if k == 1:
        assignments = [0] * len(records)
    else:
        km = KMeans(n_clusters=k, random_state=0, n_init=10)
        assignments = km.fit_predict(embeddings)

    merged: dict[tuple[str, str], int] = {}
    for cid in range(k):
        members = [records[i] for i, a in enumerate(assignments) if a == cid]
        if not members:
            continue
        key = _majority(members)
        merged[key] = merged.get(key, 0) + len(members)

    groups = [
        ClusterGroup(label=label, career_type=ctype, count=n)
        for (label, ctype), n in merged.items()
    ]
    groups.sort(key=lambda g: (-g.count, g.label))
    return groups
```

- [ ] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/engines/test_career_cluster.py -v` / Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/engines/career/cluster.py tests/unit/engines/test_career_cluster.py
git commit -m "feat: career/cluster K-Means + 최빈 진로 라벨"
```

---

### Task 7: `cards/card_d.build` — CardD + ClusterEvidence (TDD)

**Files:**
- Modify: `backend/app/cards/card_d.py`
- Test: `backend/tests/unit/cards/test_card_d.py` (신규)

**Interfaces:**
- Consumes: Task 4·5·6 + `course_queries.list_by_ids`(과목명) + `candidate_departments`(W2) + `CardD`/`CareerEntry`/`CareerSubChip`/`ClusterEvidence`/`SimilarityFactor`/`CommonCourse`/`CareerPattern`(W2 schemas).
- Produces: `build(student: StudentInput, con: sqlite3.Connection, alumni: list[AlumniRecord], top_n: int = 30) -> tuple[CardD, ClusterEvidence]` — W6 `/analyze`가 소비 (`cluster`는 DashboardResponse 최상위 필드).

설계:
- 이수 이력 있는 졸업생만 대상. 임베딩 불가/대상 0명 → 빈 CardD(`similar_label="유사 경로 0명"`)+빈 ClusterEvidence.
- top-N 유사 졸업생 → K-Means k=3 → entries (share = count/sample_size*100 round).
- sub_chips: top-N 중 `grad` 유형이 있으면 그 세부 label 상위 5 (`sub_title="대학원 진학 세부 분포"`), 없으면 최다 유형 세부 (`sub_title="{유형명} 세부 분포"`, 유형명: job→"취업", other→"기타 진로").
- ClusterEvidence (A13 — 결정론 분해):
  - factors: `이수과목 중복도`(평균 Jaccard×100), `이수경로 유사도`(평균 코사인×100), `학과 코호트 일치`(top-N 중 합집합 학과 비율×100) — 전부 round.
  - common_courses: top-N 이수과목 빈도 상위 5 → `list_by_ids`로 과목명 (DB에 없으면 id 그대로).
  - career_patterns: 상위 3개 ClusterGroup → `text = f"유사 졸업생 {count}명이 이 경로를 선택"` (결정론 폴백).
  - summary: `f"이수 패턴이 유사한 졸업생 {n}명의 진로 분포 기반"` (W5 LLM 교체 대상).
- pattern_summary 폴백: `f"유사 경로 {n}명 중 {최다 entry.label} 계열이 {share}%로 가장 많습니다."` (W5 교체 대상).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit/cards/test_card_d.py`:

```python
"""card_d — top-N/클러스터/sub_chips/ClusterEvidence 결정론 검증."""

import sqlite3
from pathlib import Path

import pytest

from app.adapters.alumni_types import AlumniRecord, Career, Enrollment
from app.cards import card_d
from app.schemas.input import StudentInput

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
        "VALUES (?, ?, '컴퓨터공학과', 3.0, 2026, 1)",
        [("CSE1010", "프로그래밍입문"), ("CSE2020", "자료구조"), ("AAT3001", "미디어아트")],
    )
    yield con
    con.close()


def _alum(aid, courses, ctype, label, dept="아트&테크놀로지학과"):
    return AlumniRecord(
        alumni_id=aid, department=dept,
        enrollment=[Enrollment(course_id=c) for c in courses],
        career=Career(type=ctype, label=label),
    )


ALUMNI = [
    _alum("a1", ["CSE1010", "CSE2020"], "job", "IT 취업"),
    _alum("a2", ["CSE1010", "CSE2020", "AAT3001"], "job", "IT 취업"),
    _alum("a3", ["CSE1010", "AAT3001"], "grad", "국내 대학원 (CS)"),
    _alum("a4", ["REL1001", "PHI1001"], "other", "창업", dept="화학과"),
]
STUDENT = StudentInput(
    student_id="S1", department="지식융합미디어학부",
    taken_course_ids=["CSE1010", "CSE2020"],
)


def test_build_card_and_evidence(con):
    card, evidence = card_d.build(STUDENT, con, ALUMNI, top_n=3)
    assert card.sample_size == 3
    assert card.similar_label == "유사 경로 3명"
    assert sum(e.count for e in card.entries) == 3
    assert card.sub_title == "대학원 진학 세부 분포"
    assert card.sub_chips[0].label == "국내 대학원 (CS)"
    assert card.pattern_summary
    assert len(evidence.factors) == 3
    assert all(0 <= f.percent <= 100 for f in evidence.factors)
    names = [c.name for c in evidence.common_courses]
    assert "프로그래밍입문" in names  # id → 과목명 매핑
    assert evidence.career_patterns and evidence.summary


def test_deterministic(con):
    a = card_d.build(STUDENT, con, ALUMNI, top_n=3)
    b = card_d.build(STUDENT, con, ALUMNI, top_n=3)
    assert a == b


def test_no_enrollment_alumni(con):
    empty = [AlumniRecord(alumni_id="x", department="d")]
    card, evidence = card_d.build(STUDENT, con, empty)
    assert card.sample_size == 0
    assert card.entries == []
    assert evidence.factors == []
```

- [ ] **Step 2: 실패 확인** — Run: `uv run pytest tests/unit/cards/test_card_d.py -v` / Expected: FAIL.

- [ ] **Step 3: 구현**

`card_d.py`:

```python
"""카드 D 오케스트레이터: 임베딩 → 유사도 top-N → 클러스터 → CardD + ClusterEvidence.

pattern_summary/summary/text 는 W5(llm/translator) 도입 전까지 결정론 폴백.
"""

import sqlite3
from collections import Counter

from app.adapters.alumni_types import AlumniRecord
from app.core.dept_normalizer import candidate_departments
from app.db.queries import course_queries
from app.engines.career import cluster as career_cluster
from app.engines.career import embedding, similarity
from app.schemas.cards import (
    CardD,
    CareerEntry,
    CareerPattern,
    CareerSubChip,
    ClusterEvidence,
    CommonCourse,
    SimilarityFactor,
)
from app.schemas.input import StudentInput

TOP_N = 30
K_CLUSTERS = 3
TYPE_NAMES = {"job": "취업", "grad": "대학원 진학", "other": "기타 진로"}


def _empty() -> tuple[CardD, ClusterEvidence]:
    return (
        CardD(
            similar_label="유사 경로 0명", sample_size=0, entries=[],
            sub_title="", sub_chips=[], pattern_summary="",
        ),
        ClusterEvidence(factors=[], common_courses=[], career_patterns=[], summary=""),
    )


def build(
    student: StudentInput,
    con: sqlite3.Connection,
    alumni: list[AlumniRecord],
    top_n: int = TOP_N,
) -> tuple[CardD, ClusterEvidence]:
    with_courses = [r for r in alumni if r.enrollment]
    sets = [{e.course_id for e in r.enrollment} for r in with_courses]
    taken = set(student.taken_course_ids)

    embedded = embedding.embed_sets(sets, taken)
    if embedded is None:
        return _empty()
    matrix, student_vec = embedded

    ranked = similarity.top_n(student_vec, matrix, top_n)
    subset = [with_courses[i] for i, _ in ranked]
    subset_sets = [sets[i] for i, _ in ranked]
    scores = [s for _, s in ranked]
    n = len(subset)
    if n == 0:
        return _empty()

    groups = career_cluster.cluster(
        subset, matrix[[i for i, _ in ranked]], k=K_CLUSTERS
    )
    entries = [
        CareerEntry(
            cluster_label=g.label,
            type=g.career_type,
            count=g.count,
            share_percent=round(g.count / n * 100),
        )
        for g in groups
    ]

    # sub_chips — grad 우선, 없으면 최다 유형 세부
    by_type = Counter(
        (r.career.type if r.career and r.career.type else "other") for r in subset
    )
    focus = "grad" if by_type.get("grad") else by_type.most_common(1)[0][0]
    focus_labels = Counter(
        (r.career.label if r.career and r.career.label else "미분류")
        for r in subset
        if (r.career.type if r.career and r.career.type else "other") == focus
    )
    sub_chips = [
        CareerSubChip(label=label, n=cnt)
        for label, cnt in sorted(focus_labels.items(), key=lambda x: (-x[1], x[0]))[:5]
    ]
    sub_title = f"{TYPE_NAMES[focus]} 세부 분포"

    top_entry = entries[0]
    card = CardD(
        similar_label=f"유사 경로 {n}명",
        sample_size=n,
        entries=entries,
        sub_title=sub_title,
        sub_chips=sub_chips,
        pattern_summary=(
            f"유사 경로 {n}명 중 {top_entry.cluster_label} 계열이 "
            f"{top_entry.share_percent}%로 가장 많습니다."
        ),
    )

    # ClusterEvidence — 결정론 분해 (A13)
    def _jaccard(a: set[str], b: set[str]) -> float:
        return len(a & b) / len(a | b) if (a | b) else 0.0

    depts = {student.department, *candidate_departments(student.department)}
    factors = [
        SimilarityFactor(
            label="이수과목 중복도",
            percent=round(sum(_jaccard(taken, s) for s in subset_sets) / n * 100),
        ),
        SimilarityFactor(
            label="이수경로 유사도",
            percent=round(sum(scores) / n * 100),
        ),
        SimilarityFactor(
            label="학과 코호트 일치",
            percent=round(sum(1 for r in subset if r.department in depts) / n * 100),
        ),
    ]
    course_freq = Counter(cid for s in subset_sets for cid in s)
    top_courses = sorted(course_freq.items(), key=lambda x: (-x[1], x[0]))[:5]
    names = {
        r["course_id"]: r["course_name"]
        for r in course_queries.list_by_ids(con, [cid for cid, _ in top_courses])
    }
    common_courses = [
        CommonCourse(name=names.get(cid, cid), n=cnt) for cid, cnt in top_courses
    ]
    career_patterns = [
        CareerPattern(
            label=g.label,
            type=g.career_type,
            text=f"유사 졸업생 {g.count}명이 이 경로를 선택",
        )
        for g in groups[:3]
    ]
    evidence = ClusterEvidence(
        factors=factors,
        common_courses=common_courses,
        career_patterns=career_patterns,
        summary=f"이수 패턴이 유사한 졸업생 {n}명의 진로 분포 기반",
    )
    return card, evidence
```

주의: `matrix[[i for i, _ in ranked]]` — scipy sparse 행 인덱싱. numpy 배열 테스트 입력에서도 동작하도록 `matrix[[...], :]` 형태가 필요하면 조정 (numpy 2차원 배열은 `matrix[list]`로 행 선택 가능, sparse csr도 동일).

- [ ] **Step 4: 통과 확인** — Run: `uv run pytest tests/unit/cards/test_card_d.py -v` / Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/cards/card_d.py tests/unit/cards/test_card_d.py
git commit -m "feat: card_d 유사 졸업생 진로 + ClusterEvidence 결정론 분해"
```

---

### Task 8: 통합 스모크 — 실 DB + mock 240명

**Files:**
- Create: `backend/tests/integration/test_cards_cd_real_data.py`

**Interfaces:**
- Consumes: 실 `s_compass_courses.db` + 재생성된 `data/mock/alumni.json`(Task 1) + `card_c`/`card_d`.

- [ ] **Step 1: 통합 테스트 작성**

```python
"""카드 C/D — 실 DB + mock 졸업생 240명 스모크. 산출물 없으면 skip."""

import json
from pathlib import Path

import pytest

from app import config
from app.adapters.alumni_types import AlumniRecord
from app.cards import card_c, card_d
from app.db.connection import get_connection
from app.schemas.input import StudentInput


@pytest.fixture(scope="module")
def con():
    if not config.DB_PATH.exists():
        pytest.skip("s_compass_courses.db 필요")
    con = get_connection()
    yield con
    con.close()


@pytest.fixture(scope="module")
def alumni():
    if not config.ALUMNI_MOCK_PATH.exists():
        pytest.skip("data/mock/alumni.json 필요")
    raw = json.loads(Path(config.ALUMNI_MOCK_PATH).read_text(encoding="utf-8"))
    return [AlumniRecord.model_validate(r) for r in raw]


@pytest.fixture(scope="module")
def student(con):
    sample_taken = [r["course_id"] for r in con.execute(
        "SELECT course_id FROM courses WHERE department = '아트&테크놀로지학과' "
        "AND course_type = 'regular' ORDER BY course_id LIMIT 10"
    )]
    return StudentInput(
        student_id="S1", department="지식융합미디어학부", taken_course_ids=sample_taken,
    )


def test_card_c_cohort_matched(student, alumni):
    card = card_c.build(student, alumni)
    # Task 1 재생성 후 미디어 3개 학과 × 60 = 180명이 합집합 코호트에 매칭돼야 함
    assert card.cohort_label == "지식융합미디어학부 · 졸업생 180명"
    assert card.entries
    assert card.entries[0].tag == "최다"
    assert abs(sum(e.share_percent for e in card.entries) - 100) <= 3  # 반올림 오차


def test_card_d_smoke(student, con, alumni):
    card, evidence = card_d.build(student, con, alumni)
    assert card.sample_size == 30
    assert card.entries and sum(e.count for e in card.entries) == 30
    assert card.sub_chips
    assert len(evidence.factors) == 3
    assert len(evidence.common_courses) == 5
    a = card_d.build(student, con, alumni)
    assert a == (card, evidence)  # 결정론
```

- [ ] **Step 2: 실행 + 전체 회귀**

Run: `uv run pytest tests/integration/test_cards_cd_real_data.py -v` — 2 PASS.
Run: `uv run pytest tests/unit tests/integration -q` — 실패 0 (기존 103 + 신규 ~21).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_cards_cd_real_data.py
git commit -m "test: 카드 C/D 실 DB + mock 240명 통합 스모크"
```

---

## 완료 기준

- `uv run pytest tests/unit tests/integration` 전체 통과.
- 카드 C: 코호트 180명 매칭(합집합), 최다 태그·기타 dim·share 합 ≈ 100.
- 카드 D: sample_size 30, entries 합 = 30, ClusterEvidence 3 factors + 5 common_courses(과목명 매핑).
- 동일 입력 → 동일 출력 (KMeans random_state 고정 포함).
- `engines/` 산출물에 자연어 문구 없음 (라벨/문구 조립은 cards).

## 알려진 후속 이슈 (범위 밖 — 보고만)

- mock 재생성으로 카드 A 코호트 신호 분포가 바뀜 — W3 통합 스모크가 점수 범위만 검증하므로 통과 예상이나, 실패 시 원인 확인 후 보고.
- W5: card_a `reason_short`·card_d `pattern_summary`/`summary`/`text` 폴백 문구를 llm/translator로 교체.
