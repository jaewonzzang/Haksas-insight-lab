# W5: llm/translator + prompts + AnthropicProvider 설계 (2026-07-10)

엔진/카드가 만든 **결정론 정형 결과**를 1~2문장 자연어로 통역한다. 실패 시 기존 결정론 폴백 유지. 카드/엔진의 결정론과 테스트는 건드리지 않는다.

## 배경 / 제약

- CLAUDE.md: `llm/translator = 통역만, 점수/판정 금지`. `api/ 핸들러 = cards/ 만 호출, LLM 직접 import 금지`. 파이프라인 `engines → cards (+llm/translator) → api`.
- 현재 상태(2026-07-10): `backend/app/llm/` 디렉토리 **부재**. `anthropic` SDK는 `pyproject.toml`에 주석. `config.ANTHROPIC_API_KEY` 로드됨. `card_a.build`/`card_d.build`는 결정론 산출 + 폴백 문구를 이미 채우고 있고 determinism 테스트가 존재.
- 확정 결정(A7): AnthropicProvider 우선. 마인드로직/GPT는 잔여.

## 통역 대상 (범위 확정)

| 카드 | 필드 | 개수 |
|---|---|---|
| A | `RecommendedCourse.reason_short` (`major` 4 + `general` 4) | 8 |
| D | `CardD.pattern_summary` | 1 |
| D | `ClusterEvidence.summary` | 1 |
| D | `ClusterEvidence.career_patterns[].text` | ≤3 |

- 카드 A `candidates`(≤20)의 `reason_short`, `why_summary`는 **결정론 유지**(통역 대상 아님).
- 카드 C는 통역 대상 아님(정형 표기만).

## 결정 (사용자 승인 2026-07-10)

- **범위**: 카드 D 서사 + 카드 A 표시 8개 (~13 필드).
- **호출 구조**: 카드 단위 배치 **2콜**(카드 A 1콜=8개 reason 배열, 카드 D 1콜=서사 묶음). 실패는 카드 단위로 격리.
- **가용성 스위치**: `ANTHROPIC_API_KEY` 유무 = 스위치. 있으면 시도(타임아웃/오류/파싱실패 시 폴백), 없으면 통역 스킵→폴백. **새 config 플래그 없음.**
- **모델**: `claude-haiku-4-5` (짧은 통역에 충분, 지연·비용 최소).
- **구조화 출력**: `client.messages.parse(output_format=PydanticModel)` → `parsed_output`. 파싱 보장, 실패 시 폴백.
- **프롬프트 캐싱**: 미적용. 프롬프트가 캐시 최소 프리픽스(Haiku 4096토큰)보다 작고 학생마다 페이로드가 달라 히트 불가.
- **thinking**: 미지정(단순 통역, 불필요).
- **seam**: 별도 통역 패스(안 A). `build()`는 불변, translator가 완성 카드 객체를 받아 텍스트 필드만 교체, 실패=입력 그대로.

## 컴포넌트

```
backend/app/llm/
  __init__.py
  providers/
    __init__.py
    base.py       # Provider 프로토콜
    anthropic.py  # AnthropicProvider
  prompts.py      # 프롬프트 + 스키마 빌더
  translator.py   # 카드별 통역 패스
```

### `providers/base.py`

```python
from typing import Optional, Protocol, Type
from pydantic import BaseModel

class Provider(Protocol):
    def translate(
        self, system: str, user: str, schema: Type[BaseModel]
    ) -> Optional[BaseModel]:
        """구조화 통역 1콜. 실패(키 없음·타임아웃·오류·파싱)면 None."""
        ...
```

- 마인드로직/GPT provider는 **만들지 않음**(YAGNI, A7 잔여). Protocol + AnthropicProvider만.

### `providers/anthropic.py`

```python
class AnthropicProvider:
    MODEL = "claude-haiku-4-5"

    def __init__(self, api_key: str, timeout: float = 8.0):
        # 키 없으면 생성 측(get_translator)에서 None 반환 — 여기선 키 있다고 가정
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=1)

    def translate(self, system, user, schema):
        try:
            resp = self._client.messages.parse(
                model=self.MODEL, max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
            return resp.parsed_output
        except Exception:
            return None   # 모든 실패 → 폴백 신호
```

- `timeout=8.0`, `max_retries=1` — 실패→폴백을 빠르게.
- **키 부재 스위치는 W5가 팩토리로 제공**: 모듈 함수 `get_provider() -> Optional[Provider]` — `config.ANTHROPIC_API_KEY` 비었으면 `None`, 있으면 `AnthropicProvider(config.ANTHROPIC_API_KEY)`. `translator`는 provider=None이면 통역 스킵(입력 그대로). W6는 이 팩토리를 호출해 주입만 한다.

### `prompts.py`

카드별 (system, user, schema) 빌더. LLM에는 **정형 값만** 전달, 문장화만 요청.

```python
class CardAItem(BaseModel):
    course_id: str
    reason: str            # 1문장 통역 결과

class CardATranslation(BaseModel):
    items: list[CardAItem]

class CardDTranslation(BaseModel):
    pattern_summary: str
    cluster_summary: str
    pattern_texts: list[str]   # career_patterns 순서 일치
```

- 카드 A user 입력(과목별): `course_id, course_name, grade, score_percent, 최상위 pos factor label`.
- 카드 D user 입력: `entries(cluster_label, type, count, share_percent)`, `factors(label, percent)`, `sub_title`.
- system 공통: "학사 추천 정형 데이터를 학생이 읽을 짧은 한국어로 통역한다. **점수·등급·순위를 새로 만들지 말고**, 주어진 값만 자연스럽게 문장화한다."
- 톤: `reason` 1문장 ~40자(기존 폴백 톤 매칭), `pattern_summary`/`cluster_summary` 1~2문장.

### `translator.py`

```python
def translate_card_a(card: CardA, provider: Optional[Provider]) -> CardA:
    if provider is None or not (card.major or card.general):
        return card
    system, user, schema = prompts.build_card_a_prompt(card)
    out = provider.translate(system, user, schema)
    if out is None:
        return card                      # 폴백 유지
    by_id = {i.course_id: i.reason for i in out.items}
    # major/general 의 reason_short 만 교체(id 매칭), 누락 id는 폴백 유지
    ...
    return card.model_copy(update=...)

def translate_card_d(
    card: CardD, evidence: ClusterEvidence, provider: Optional[Provider]
) -> tuple[CardD, ClusterEvidence]:
    if provider is None or card.sample_size == 0:
        return card, evidence
    ...
    if out is None:
        return card, evidence            # 폴백 유지
    # pattern_summary / summary / career_patterns[].text 교체
    ...
```

- 순수 함수. provider·LLM 실패는 전부 입력 그대로 반환으로 흡수.
- 카드 객체를 불변 취급하고 `model_copy(update=...)`로 새 객체 반환.

## 배선 (W5 범위 밖 — W6)

W5는 translator 함수·provider·`get_provider()` 팩토리·프롬프트·테스트를 제공한다. 실제 호출 지점(build→translate 순, `api → cards`만 허용)과 provider 주입은 W6 `api/analyze` 배선에서 확정. W6는 `get_provider()`를 호출해 translate에 주입만 한다. 본 스펙은 배선 위치를 규정하지 않되 함수 시그니처가 W6에서 그대로 쓰이도록 고정한다.

## 테스트

- `tests/unit/llm/test_translator.py`
  - `FakeProvider`(정상 JSON 반환): 카드 A 8개 reason 교체, candidates 불변 검증. 카드 D 3필드 교체 검증.
  - `FakeProvider`(예외/None 반환): 원본 폴백 문구 그대로 유지 검증.
  - provider=None: 입력 그대로.
  - id 부분 누락: 누락 과목만 폴백 유지, 나머지 교체.
- `tests/unit/llm/test_prompts.py`: 빌더가 정형 값을 담고 schema를 반환하는지(자연어 지시 없음, 값만).
- `tests/integration/test_translator_live.py`: `ANTHROPIC_API_KEY` 있으면 실 Haiku 1콜 스모크, 없으면 `pytest.skip`.

## 완료 기준

- `uv run pytest tests/unit tests/integration` 통과(기존 회귀 0 + 신규).
- FakeProvider로 교체·폴백 경로 모두 검증.
- `engines/`·`cards/`·`schemas/` **미수정**(build 결정론 테스트 불변). `pyproject.toml`에 `anthropic` 추가.
- translator/prompts는 점수·판정 로직 없음(값 문장화만).

## 미결정 유지

- A7 잔여: 마인드로직/GPT fallback 체인(엔드포인트 확정 후).
- 배선 지점(cards 오케스트레이터 vs deps 주입)은 W6에서 확정.
