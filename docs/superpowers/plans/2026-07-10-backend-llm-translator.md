# W5: llm/translator + prompts + AnthropicProvider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카드 A/D의 결정론 폴백 문구(카드 A 표시 8개 `reason_short` + 카드 D `pattern_summary`·`ClusterEvidence.summary`·`career_patterns[].text`)를 Haiku 통역으로 교체하는 순수 함수 계층을 만든다. LLM 실패·키 부재 시 기존 폴백 그대로.

**Architecture:** 별도 통역 패스(스펙 안 A) — `build()`는 불변, `translator.translate_card_a/d`가 완성 카드 객체를 받아 텍스트 필드만 `model_copy`로 교체. 카드 단위 배치 2콜(카드 A 1콜 = reason 8개 배열, 카드 D 1콜 = 서사 묶음), 실패는 카드 단위 격리(입력 그대로 반환). 가용성 스위치 = `config.ANTHROPIC_API_KEY` 유무(`get_provider()` 팩토리가 판정, 새 config 플래그 없음). 배선(api→cards 호출 지점)은 W6 — W5는 함수·팩토리·프롬프트·테스트까지만.

**Tech Stack:** Python 3.12 + uv, `anthropic` SDK(구조화 출력 `client.messages.parse(output_format=PydanticModel)` → `.parsed_output`), pydantic v2, pytest.

**스펙:** `docs/superpowers/specs/2026-07-10-w5-llm-translator-design.md` (사용자 승인 2026-07-10)

## Global Constraints

- 모든 명령은 `backend/` 디렉토리에서 실행 (`uv run ...`).
- **`llm/` = 통역만. 점수·판정·순위 생성 금지.** 프롬프트는 정형 값만 전달하고 문장화만 요청.
- **`engines/`·`cards/`·`schemas/`·`api/` 수정 금지** — build 결정론 테스트 불변이 완료 기준. `frontend/`, `docs/` 수정 금지(플랜 체크박스 갱신 제외).
- 카드 A `candidates`(≤20)와 `why_summary`는 통역 대상 아님(결정론 유지). 카드 C는 W5 범위 밖.
- 모델 `claude-haiku-4-5` 고정. `timeout=8.0`, `max_retries=1`, `max_tokens=1024`.
- provider·LLM의 모든 실패(키 없음 제외 — 그건 팩토리가 None)는 `translate()`가 `None` 반환으로 흡수. 예외 전파 금지.
- translator는 순수 함수: 입력 카드 객체를 변이하지 않고 `model_copy(update=...)`로 새 객체 반환. 실패 = 입력 그대로.
- 커밋은 자기 변경 파일만 명시적 `git add`(`git add -A` 금지). push 금지. 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: prompts.py — 통역 스키마 + 프롬프트 빌더

**Files:**
- Create: `backend/app/llm/__init__.py` (빈 파일)
- Create: `backend/app/llm/prompts.py`
- Create: `backend/tests/unit/llm/__init__.py` (빈 파일)
- Test: `backend/tests/unit/llm/test_prompts.py`

**Interfaces:**
- Produces: `CardAItem(course_id: str, reason: str)`, `CardATranslation(items: list[CardAItem])`, `CardDTranslation(pattern_summary: str, cluster_summary: str, pattern_texts: list[str])`.
- Produces: `build_card_a_prompt(card: CardA) -> tuple[str, str, type[CardATranslation]]`, `build_card_d_prompt(card: CardD, evidence: ClusterEvidence) -> tuple[str, str, type[CardDTranslation]]` — 반환 = `(system, user, schema)`. Task 2 translator와 Task 3 provider가 그대로 사용.

- [x] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/llm/test_prompts.py`:

```python
"""prompts 빌더: 정형 값만 담고 (system, user, schema)를 반환하는지."""

from app.llm import prompts
from app.schemas.cards import (
    CardD,
    CareerEntry,
    CareerPattern,
    CareerSubChip,
    ClusterEvidence,
    CommonCourse,
    SimilarityFactor,
)
from tests.unit.llm.fixtures import make_card_a


def test_card_a_prompt_contains_values_and_schema():
    card = make_card_a()
    system, user, schema = prompts.build_card_a_prompt(card)
    assert schema is prompts.CardATranslation
    assert "점수" in system  # 점수·판정 금지 지시
    # 정형 값이 user 페이로드에 그대로 들어간다
    assert "AIE1001" in user and "인공지능개론" in user
    assert "강추" in user and "82" in user
    assert "코호트 선호도" in user  # 최상위 pos factor label


def test_card_d_prompt_contains_values_and_schema():
    card = CardD(
        similar_label="유사 경로 30명", sample_size=30,
        entries=[CareerEntry(cluster_label="개발자", type="job", count=18, share_percent=60.0)],
        sub_title="취업 세부 분포",
        sub_chips=[CareerSubChip(label="개발자", n=18)],
        pattern_summary="유사 경로 30명 중 개발자 계열이 60%로 가장 많습니다.",
    )
    evidence = ClusterEvidence(
        factors=[SimilarityFactor(label="이수과목 중복도", percent=41.0)],
        common_courses=[CommonCourse(name="자료구조", n=22)],
        career_patterns=[CareerPattern(label="개발자", type="job", text="유사 졸업생 18명이 이 경로를 선택")],
        summary="이수 패턴이 유사한 졸업생 30명의 진로 분포 기반",
    )
    system, user, schema = prompts.build_card_d_prompt(card, evidence)
    assert schema is prompts.CardDTranslation
    assert "개발자" in user and "60" in user
    assert "이수과목 중복도" in user and "41" in user
    assert "취업 세부 분포" in user
```

공용 픽스처 `backend/tests/unit/llm/fixtures.py` (Task 2 테스트도 재사용):

```python
"""llm 테스트 공용 카드 픽스처."""

from app.schemas.cards import CardA, RecommendationFactor, RecommendedCourse


def make_course(course_id: str = "AIE1001", reason: str = "코호트 선호도 신호가 가장 강한 과목") -> RecommendedCourse:
    return RecommendedCourse(
        course_id=course_id,
        course_name="인공지능개론",
        credit=3.0,
        grade="강추",
        score_percent=82,
        reason_short=reason,
        kind="major",
        kind_label="전공",
        area_label=None,
        factors=[
            RecommendationFactor(label="코호트 선호도", weight_percent=25.0, contribution="+21", kind="pos"),
            RecommendationFactor(label="콘텐츠 유사도", weight_percent=22.0, contribution="+12", kind="pos"),
        ],
        why_summary="강추 · 추천도 82%",
    )


def make_card_a() -> CardA:
    major = [make_course(f"AIE100{i}") for i in range(1, 5)]
    general = [make_course(f"GEN200{i}") for i in range(1, 5)]
    return CardA(major=major, general=general, candidates=major + general)
```

- [x] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/llm/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm'`

- [x] **Step 3: prompts.py 구현**

```python
"""카드별 (system, user, schema) 프롬프트 빌더 + 통역 출력 스키마.

LLM에는 정형 값만 전달하고 문장화만 요청한다. 점수·판정 로직 금지 (CLAUDE.md).
스펙: docs/superpowers/specs/2026-07-10-w5-llm-translator-design.md
"""

import json

from pydantic import BaseModel

from app.schemas.cards import CardA, CardD, ClusterEvidence

_SYSTEM = (
    "학사 추천 정형 데이터를 학생이 읽을 짧은 한국어로 통역한다. "
    "점수·등급·순위를 새로 만들지 말고, 주어진 값만 자연스럽게 문장화한다."
)

SYSTEM_CARD_A = _SYSTEM + " reason은 과목당 1문장(40자 내외), 기존 추천 사유 톤을 유지한다."
SYSTEM_CARD_D = _SYSTEM + " pattern_summary와 cluster_summary는 각각 1~2문장으로 쓴다."


class CardAItem(BaseModel):
    course_id: str
    reason: str


class CardATranslation(BaseModel):
    items: list[CardAItem]


class CardDTranslation(BaseModel):
    pattern_summary: str
    cluster_summary: str
    pattern_texts: list[str]  # career_patterns 순서 일치


def _top_pos_factor(course) -> str:
    pos = [f for f in course.factors if f.kind == "pos"]
    if not pos:
        return ""
    return max(pos, key=lambda f: f.weight_percent).label


def build_card_a_prompt(card: CardA) -> tuple[str, str, type[CardATranslation]]:
    rows = [
        {
            "course_id": c.course_id,
            "course_name": c.course_name,
            "grade": c.grade,
            "score_percent": c.score_percent,
            "top_factor": _top_pos_factor(c),
        }
        for c in [*card.major, *card.general]
    ]
    user = json.dumps({"courses": rows}, ensure_ascii=False)
    return SYSTEM_CARD_A, user, CardATranslation


def build_card_d_prompt(
    card: CardD, evidence: ClusterEvidence
) -> tuple[str, str, type[CardDTranslation]]:
    payload = {
        "sample_size": card.sample_size,
        "sub_title": card.sub_title,
        "entries": [
            {
                "cluster_label": e.cluster_label,
                "type": e.type,
                "count": e.count,
                "share_percent": e.share_percent,
            }
            for e in card.entries
        ],
        "factors": [{"label": f.label, "percent": f.percent} for f in evidence.factors],
        "career_patterns": [
            {"label": p.label, "type": p.type} for p in evidence.career_patterns
        ],
    }
    user = json.dumps(payload, ensure_ascii=False)
    return SYSTEM_CARD_D, user, CardDTranslation
```

- [x] **Step 4: 통과 확인**

Run: `uv run pytest tests/unit/llm/test_prompts.py -v`
Expected: PASS (2 passed)

- [x] **Step 5: Commit**

```bash
git add app/llm/__init__.py app/llm/prompts.py tests/unit/llm/__init__.py tests/unit/llm/fixtures.py tests/unit/llm/test_prompts.py
git commit -m "feat: llm/prompts 통역 스키마 + 카드 A/D 프롬프트 빌더"
```

---

### Task 2: Provider 프로토콜 + translator 통역 패스

**Files:**
- Create: `backend/app/llm/providers/__init__.py` (빈 파일)
- Create: `backend/app/llm/providers/base.py`
- Create: `backend/app/llm/translator.py`
- Test: `backend/tests/unit/llm/test_translator.py`

**Interfaces:**
- Consumes: Task 1의 `prompts.build_card_a_prompt` / `build_card_d_prompt` / `CardATranslation` / `CardDTranslation`.
- Produces: `Provider` 프로토콜 — `translate(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel | None`.
- Produces: `translate_card_a(card: CardA, provider: Provider | None) -> CardA`, `translate_card_d(card: CardD, evidence: ClusterEvidence, provider: Provider | None) -> tuple[CardD, ClusterEvidence]` — W6 배선이 이 시그니처를 그대로 사용.

- [x] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/llm/test_translator.py`:

```python
"""translator: FakeProvider로 교체·폴백 경로 검증. 실 API 호출 없음."""

from pydantic import BaseModel

from app.llm import translator
from app.llm.prompts import CardAItem, CardATranslation, CardDTranslation
from app.schemas.cards import (
    CardD,
    CareerEntry,
    CareerPattern,
    ClusterEvidence,
)
from tests.unit.llm.fixtures import make_card_a


class FakeProvider:
    def __init__(self, out: BaseModel | None):
        self.out = out
        self.calls: list[tuple[str, str, type]] = []

    def translate(self, system, user, schema):
        self.calls.append((system, user, schema))
        return self.out


def _card_d() -> tuple[CardD, ClusterEvidence]:
    card = CardD(
        similar_label="유사 경로 30명", sample_size=30,
        entries=[CareerEntry(cluster_label="개발자", type="job", count=18, share_percent=60.0)],
        sub_title="취업 세부 분포", sub_chips=[],
        pattern_summary="유사 경로 30명 중 개발자 계열이 60%로 가장 많습니다.",
    )
    evidence = ClusterEvidence(
        factors=[], common_courses=[],
        career_patterns=[
            CareerPattern(label="개발자", type="job", text="유사 졸업생 18명이 이 경로를 선택"),
            CareerPattern(label="대학원", type="grad", text="유사 졸업생 7명이 이 경로를 선택"),
        ],
        summary="이수 패턴이 유사한 졸업생 30명의 진로 분포 기반",
    )
    return card, evidence


# --- 카드 A ---

def test_card_a_replaces_display_reasons_only():
    card = make_card_a()
    ids = [c.course_id for c in [*card.major, *card.general]]
    out = CardATranslation(items=[CardAItem(course_id=i, reason=f"{i} 통역") for i in ids])
    result = translator.translate_card_a(card, FakeProvider(out))
    assert [c.reason_short for c in result.major] == [f"{i} 통역" for i in ids[:4]]
    assert [c.reason_short for c in result.general] == [f"{i} 통역" for i in ids[4:]]
    # candidates·why_summary는 결정론 유지
    assert all(c.reason_short == "코호트 선호도 신호가 가장 강한 과목" for c in result.candidates)
    assert all(c.why_summary == "강추 · 추천도 82%" for c in result.major)
    # 순수 함수 — 입력 불변
    assert card.major[0].reason_short == "코호트 선호도 신호가 가장 강한 과목"


def test_card_a_partial_ids_keep_fallback():
    card = make_card_a()
    first = card.major[0].course_id
    out = CardATranslation(items=[CardAItem(course_id=first, reason="통역됨")])
    result = translator.translate_card_a(card, FakeProvider(out))
    assert result.major[0].reason_short == "통역됨"
    assert result.major[1].reason_short == "코호트 선호도 신호가 가장 강한 과목"


def test_card_a_provider_failure_returns_input():
    card = make_card_a()
    assert translator.translate_card_a(card, FakeProvider(None)) is card


def test_card_a_no_provider_returns_input():
    card = make_card_a()
    assert translator.translate_card_a(card, None) is card


def test_card_a_empty_card_skips_call():
    from app.schemas.cards import CardA
    empty = CardA(major=[], general=[], candidates=[])
    fake = FakeProvider(None)
    assert translator.translate_card_a(empty, fake) is empty
    assert fake.calls == []


# --- 카드 D ---

def test_card_d_replaces_three_fields():
    card, evidence = _card_d()
    out = CardDTranslation(
        pattern_summary="요약 통역", cluster_summary="근거 통역",
        pattern_texts=["패턴1 통역", "패턴2 통역"],
    )
    new_card, new_ev = translator.translate_card_d(card, evidence, FakeProvider(out))
    assert new_card.pattern_summary == "요약 통역"
    assert new_ev.summary == "근거 통역"
    assert [p.text for p in new_ev.career_patterns] == ["패턴1 통역", "패턴2 통역"]
    # 나머지 필드 불변
    assert new_card.entries == card.entries
    assert new_ev.career_patterns[0].label == "개발자"


def test_card_d_short_pattern_texts_keep_fallback_tail():
    card, evidence = _card_d()
    out = CardDTranslation(pattern_summary="요약", cluster_summary="근거", pattern_texts=["하나만"])
    _, new_ev = translator.translate_card_d(card, evidence, FakeProvider(out))
    assert new_ev.career_patterns[0].text == "하나만"
    assert new_ev.career_patterns[1].text == "유사 졸업생 7명이 이 경로를 선택"


def test_card_d_provider_failure_returns_inputs():
    card, evidence = _card_d()
    new_card, new_ev = translator.translate_card_d(card, evidence, FakeProvider(None))
    assert new_card is card and new_ev is evidence


def test_card_d_empty_sample_skips_call():
    card, evidence = _card_d()
    empty = card.model_copy(update={"sample_size": 0})
    fake = FakeProvider(None)
    new_card, _ = translator.translate_card_d(empty, evidence, fake)
    assert new_card is empty
    assert fake.calls == []
```

- [x] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/llm/test_translator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.translator'`

- [x] **Step 3: base.py + translator.py 구현**

`backend/app/llm/providers/base.py`:

```python
"""LLM Provider 프로토콜 — 구조화 통역 1콜, 실패는 None.

AnthropicProvider 외 공급자(마인드로직/GPT)는 A7 잔여 — 만들지 않음 (YAGNI).
"""

from typing import Protocol

from pydantic import BaseModel


class Provider(Protocol):
    def translate(
        self, system: str, user: str, schema: type[BaseModel]
    ) -> BaseModel | None:
        """구조화 통역 1콜. 실패(타임아웃·오류·파싱)면 None."""
        ...
```

`backend/app/llm/translator.py`:

```python
"""카드별 통역 패스: 완성 카드 객체의 텍스트 필드만 교체하는 순수 함수.

build()는 불변(스펙 안 A). provider=None·LLM 실패는 전부 입력 그대로 반환으로 흡수.
스펙: docs/superpowers/specs/2026-07-10-w5-llm-translator-design.md
"""

from app.llm import prompts
from app.llm.providers.base import Provider
from app.schemas.cards import CardA, CardD, ClusterEvidence, RecommendedCourse


def translate_card_a(card: CardA, provider: Provider | None) -> CardA:
    if provider is None or not (card.major or card.general):
        return card
    system, user, schema = prompts.build_card_a_prompt(card)
    out = provider.translate(system, user, schema)
    if out is None:
        return card
    by_id = {i.course_id: i.reason for i in out.items}

    def _swap(courses: list[RecommendedCourse]) -> list[RecommendedCourse]:
        return [
            c.model_copy(update={"reason_short": by_id[c.course_id]})
            if c.course_id in by_id
            else c
            for c in courses
        ]

    return card.model_copy(update={"major": _swap(card.major), "general": _swap(card.general)})


def translate_card_d(
    card: CardD, evidence: ClusterEvidence, provider: Provider | None
) -> tuple[CardD, ClusterEvidence]:
    if provider is None or card.sample_size == 0:
        return card, evidence
    system, user, schema = prompts.build_card_d_prompt(card, evidence)
    out = provider.translate(system, user, schema)
    if out is None:
        return card, evidence
    patterns = [
        p.model_copy(update={"text": t})
        for p, t in zip(evidence.career_patterns, out.pattern_texts)
    ] + list(evidence.career_patterns[len(out.pattern_texts):])
    return (
        card.model_copy(update={"pattern_summary": out.pattern_summary}),
        evidence.model_copy(update={"summary": out.cluster_summary, "career_patterns": patterns}),
    )
```

- [x] **Step 4: 통과 확인**

Run: `uv run pytest tests/unit/llm -v`
Expected: PASS (test_prompts 2 + test_translator 9 = 11 passed)

- [x] **Step 5: Commit**

```bash
git add app/llm/providers/__init__.py app/llm/providers/base.py app/llm/translator.py tests/unit/llm/test_translator.py
git commit -m "feat: llm/translator 카드 A/D 통역 패스 + Provider 프로토콜"
```

---

### Task 3: AnthropicProvider + get_provider() 팩토리

**Files:**
- Modify: `backend/pyproject.toml` (`# "anthropic",` 주석 해제 — 그 줄만)
- Create: `backend/app/llm/providers/anthropic.py`
- Test: `backend/tests/unit/llm/test_anthropic_provider.py`

**Interfaces:**
- Consumes: `config.ANTHROPIC_API_KEY` (기존 — 새 플래그 추가 금지), Task 2의 `Provider`.
- Produces: `AnthropicProvider(api_key: str, timeout: float = 8.0)` (`MODEL = "claude-haiku-4-5"`), `get_provider() -> Provider | None` — W6가 호출해 주입만 한다.

- [x] **Step 1: 의존성 활성화**

`backend/pyproject.toml`에서 `# "anthropic",` → `"anthropic",` (openai/chromadb 주석은 유지).

Run: `uv sync`
Expected: `anthropic` 설치 성공.

- [x] **Step 2: 실패하는 테스트 작성**

`backend/tests/unit/llm/test_anthropic_provider.py`:

```python
"""AnthropicProvider 단위: 팩토리 스위치 + 실패 흡수. 실 API 호출 없음."""

from app import config
from app.llm.prompts import CardATranslation
from app.llm.providers import anthropic as provider_mod


def test_get_provider_none_without_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert provider_mod.get_provider() is None


def test_get_provider_with_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-test")
    p = provider_mod.get_provider()
    assert isinstance(p, provider_mod.AnthropicProvider)


def test_translate_absorbs_exceptions(monkeypatch):
    p = provider_mod.AnthropicProvider(api_key="sk-test")

    class Boom:
        class messages:
            @staticmethod
            def parse(**kwargs):
                raise RuntimeError("api down")

    monkeypatch.setattr(p, "_client", Boom)
    assert p.translate("sys", "user", CardATranslation) is None


def test_translate_returns_parsed_output(monkeypatch):
    p = provider_mod.AnthropicProvider(api_key="sk-test")
    expected = CardATranslation(items=[])

    class Resp:
        parsed_output = expected

    class Stub:
        class messages:
            @staticmethod
            def parse(**kwargs):
                assert kwargs["model"] == "claude-haiku-4-5"
                assert kwargs["output_format"] is CardATranslation
                return Resp

    monkeypatch.setattr(p, "_client", Stub)
    assert p.translate("sys", "user", CardATranslation) is expected
```

- [x] **Step 3: 실패 확인**

Run: `uv run pytest tests/unit/llm/test_anthropic_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.providers.anthropic'`

- [x] **Step 4: anthropic.py 구현**

```python
"""AnthropicProvider — Haiku 구조화 통역 1콜 + 키 스위치 팩토리.

키 부재 스위치는 get_provider()가 판정 (스펙: 새 config 플래그 없음).
W6는 get_provider()를 호출해 translate_card_*에 주입만 한다.
"""

import anthropic
from pydantic import BaseModel

from app import config
from app.llm.providers.base import Provider


class AnthropicProvider:
    MODEL = "claude-haiku-4-5"

    def __init__(self, api_key: str, timeout: float = 8.0):
        self._client = anthropic.Anthropic(
            api_key=api_key, timeout=timeout, max_retries=1
        )

    def translate(
        self, system: str, user: str, schema: type[BaseModel]
    ) -> BaseModel | None:
        try:
            resp = self._client.messages.parse(
                model=self.MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
            return resp.parsed_output
        except Exception:
            return None  # 모든 실패 → 폴백 신호


def get_provider() -> Provider | None:
    if not config.ANTHROPIC_API_KEY:
        return None
    return AnthropicProvider(config.ANTHROPIC_API_KEY)
```

- [x] **Step 5: 통과 확인**

Run: `uv run pytest tests/unit/llm -v`
Expected: PASS (11 + 4 = 15 passed)

- [x] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock app/llm/providers/anthropic.py tests/unit/llm/test_anthropic_provider.py
git commit -m "feat: AnthropicProvider(claude-haiku-4-5 구조화 통역) + get_provider 키 스위치"
```

---

### Task 4: 실 Haiku 통합 스모크 + 전체 회귀

**Files:**
- Test: `backend/tests/integration/test_translator_live.py`

**Interfaces:**
- Consumes: Task 1~3 전부 (`get_provider`, `build_card_a_prompt`, `translate_card_d`).

- [x] **Step 1: 통합 스모크 작성**

`backend/tests/integration/test_translator_live.py`:

```python
"""실 Haiku 1콜 스모크 — ANTHROPIC_API_KEY 있을 때만. 없으면 skip."""

import pytest

from app import config
from app.llm import prompts, translator
from app.llm.providers.anthropic import get_provider
from app.schemas.cards import CardD, CareerEntry, CareerPattern, ClusterEvidence

pytestmark = pytest.mark.skipif(
    not config.ANTHROPIC_API_KEY, reason="ANTHROPIC_API_KEY 없음"
)


def test_live_card_d_translation():
    card = CardD(
        similar_label="유사 경로 30명", sample_size=30,
        entries=[
            CareerEntry(cluster_label="개발자", type="job", count=18, share_percent=60.0),
            CareerEntry(cluster_label="대학원", type="grad", count=7, share_percent=23.0),
        ],
        sub_title="취업 세부 분포", sub_chips=[],
        pattern_summary="유사 경로 30명 중 개발자 계열이 60%로 가장 많습니다.",
    )
    evidence = ClusterEvidence(
        factors=[], common_courses=[],
        career_patterns=[CareerPattern(label="개발자", type="job", text="유사 졸업생 18명이 이 경로를 선택")],
        summary="이수 패턴이 유사한 졸업생 30명의 진로 분포 기반",
    )
    provider = get_provider()
    assert provider is not None

    new_card, new_ev = translator.translate_card_d(card, evidence, provider)
    # 실 통역 성공 시 교체, 실패 시 폴백 — 어느 쪽이든 비어 있지 않아야 한다
    assert new_card.pattern_summary.strip()
    assert new_ev.summary.strip()
    # 구조화 출력이 실제로 파싱되는지 직접 1콜 확인
    system, user, schema = prompts.build_card_d_prompt(card, evidence)
    out = provider.translate(system, user, schema)
    assert out is not None, "실 Haiku 구조화 통역 실패 — 키/모델/SDK 확인"
    assert isinstance(out.pattern_summary, str) and out.pattern_summary.strip()
```

- [ ] **Step 2: 통합 스모크 실행**

Run: `uv run pytest tests/integration/test_translator_live.py -v`
Expected: `.env`에 키 있으면 PASS(1 passed), 없으면 1 skipped. 실패 시 중단하고 원인 보고(키·네트워크·SDK 버전).

- [ ] **Step 3: 전체 회귀**

Run: `uv run pytest tests/unit tests/integration -q`
Expected: 기존 125 passed/1 skipped 기준 + 신규 15 unit + live 1 (pass 또는 skip). 실패 0. 특히 `tests/unit/cards`·`tests/integration/test_cards_cd_real_data.py`(build 결정론) 회귀 없음 확인.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_translator_live.py
git commit -m "test: 실 Haiku 통역 통합 스모크 (키 없으면 skip)"
```

- [ ] **Step 5: 플랜 체크박스 갱신 + 완료 보고**

이 파일의 체크박스를 갱신해 커밋하고, 최종 테스트 수치(unit/integration passed·skipped)와 라이브 스모크 결과(pass/skip)를 보고한다.

```bash
git add ../docs/superpowers/plans/2026-07-10-backend-llm-translator.md
git commit -m "docs: W5 플랜 체크박스 완료 갱신"
```
