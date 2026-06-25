# 실데이터 전환 + Claude "왜?" 생성 — 구현 계획

> **성격:** 이 문서는 순수 TDD 바이트사이즈 플랜이 아니라 **방향성 로드맵 + 즉시 착수 가능한 구체 묶음**의 하이브리드다. 백엔드가 스텁이고 핵심 선행조건(특히 `OPEN_QUESTIONS` A1 실 졸업생 데이터 스키마)이 미결정이라, 전 구간을 바이트사이즈로 못 박으면 플레이스홀더가 된다. 막히지 않은 부분(§2 Claude "왜?")은 실제 코드 수준으로, 데이터에 막힌 부분(§3 카드 C/D)은 단계 + 결정 게이트로 둔다.

**목표:** mock 기반 데모를 실데이터/실분석 파이프라인으로 전환하고, "왜?" 칸을 Claude API 통역으로 채운다.

**아키텍처:** 단방향 파이프라인 `raw → parsers → build_* → processed.db → queries → engines → cards(+llm) → api → frontend`. 점수/판정은 결정론+ML 엔진, LLM은 통역만. 프론트는 `lib/api.ts` 시임으로 mock ↔ real 전환.

**기술 스택:** 백엔드 FastAPI + raw sqlite3 + uv + 공식 `anthropic` Python SDK. 프론트 Vite+React+TS. 모델 `claude-opus-4-8`.

---

## 0. 현재 상태 (출발점)

| 레이어 | 지금 | 비고 |
|---|---|---|
| 프론트 | 프로필 A~D별 하드코딩 `DashboardResponse` (`profiles.fixture.ts`) | 동작함. `lib/api.ts`는 휴면 시임 |
| 백엔드 카드/엔진/LLM | 전부 스텁 (`# TODO`) | `main.py` 라우터 등록만 실제 |
| 백엔드 1단계 빌드 | 미실행, `data/processed/` 비어있음 | parsers/build 진행 중 (메모리) |
| 계약 | 프론트 `types/api.ts` ⊃ 백엔드 `schemas/cards.py` | **프론트가 더 확장됨** (factors/profile/cluster) → 백엔드 미러 필요 (A12) |

---

## 1. 방향성 — 구조를 어떻게 바꿀까 (mock → real)

전환은 **프론트 재작성이 아니라 데이터 소스 교체**다. 시임이 이미 있다.

### 단계
- **P1. 1단계 빌드 완성** — `parsers/*` + `scripts/build_course_db.py` → `data/processed/s_compass_courses.db` (5테이블). *이미 진행 중인 작업.* 모든 하류의 뿌리.
- **P2. 카드 A 실경로 수직 슬라이스** — `api/analyze` → `cards/card_a` → `engines/recommender` → `engines/prereq` → `llm/translator` → `schemas/cards.CardA`. **지금 안 막힌 유일한 카드.**
- **P3. 계약 동기화 (A12)** — 백엔드 `schemas/cards.py`를 프론트 `types/api.ts`에 맞춰 확장: `RecommendationFactor`, `RecommendedCourse.factors/why_summary/kind/area_label`, `StudentProfile`, `ClusterEvidence`. 그다음 프론트 `lib/api.ts`의 `USE_MOCK`를 끄고 `/analyze` 실호출 → `profiles.fixture`는 입력 프리셋(학생 A=실제 데이터)으로 강등.
- **P4. 카드 C/D** — A1(졸업생 데이터) 수령 후. (§3)

### 핵심: 프론트는 거의 안 바뀐다
`useAnalysis.run()`이 지금은 `selected.dashboard`(하드코딩)를 쓴다. P3에서 이 한 줄을 `await analyze(studentInput)`로 바꾸면 끝. 컴포넌트·타입은 그대로(이미 mockup 기준으로 확장돼 있음). 데모 프로필 A~D는 "실제 학생 입력 프리셋"으로 의미만 바뀐다.

---

## 2. Claude API로 "왜?" 짧은 답변 생성 — 프로세스

### 2.1 경계 (절대 규칙)
`engines/` = 점수·등급·**factors(기여도)** 산출. `llm/translator` = 그 정형 수치를 받아 **1~2문장 한국어로 통역만**. LLM은 숫자를 만들거나 바꾸지 않는다. → 이게 **A13("왜?" 데이터 출처 미정)을 닫는 방식**이다: 엔진이 과목별 `RecommendationFactor[]`를 내보내고, translator가 그걸 문장으로 옮긴다.

### 2.2 호출 형태
"통역"은 **단일 LLM 호출**(요약/분류류) — 에이전트·툴 불필요. 공식 `anthropic` Python SDK의 `client.messages.create` 한 번.

- **입력:** 과목별 `{course_name, grade, score_percent, factors:[{label, contribution}]}` 직렬화
- **출력:** 과목별 `reason_short`(카드 1줄) + `why_summary`(패널 한 줄 요약)
- **모델:** `claude-opus-4-8` (기본). *짧은 배치 번역이라 비용을 줄이고 싶으면 `claude-haiku-4-5`도 후보 — 단 Anthropic 기본은 opus, 다운그레이드는 결정 사항이니 너가 정해라.*
- **파라미터:** `output_config={"effort":"low"}` (단순 작업), `thinking` 생략(복잡 추론 아님). thinking이 꺼지면 opus가 본문에 설명을 길게 쓸 수 있으니 **시스템 프롬프트에 "문장만 출력, 서두 금지"** 명시.
- **프롬프트 캐싱:** translator 시스템 프롬프트(통역 규칙 + 단정회피 톤 + few-shot)는 모든 과목·학생에 고정 → `cache_control:{type:"ephemeral"}`로 캐시. 과목별 가변 데이터는 user 턴(브레이크포인트 뒤). `usage.cache_read_input_tokens`로 검증.
- **구조화 출력:** 과목 여러 개를 한 번에 → `output_config.format`에 `json_schema`로 `{course_id: {reason_short, why_summary}}` 강제(파싱 안정성).
- **배치:** S-Compass는 학기당 1회 배치. 한 학생의 추천 과목 ~8개는 `/analyze` 한 호출(JSON 배열)로 처리. *다수 학생 오프라인 사전생성*이 필요하면 Message Batches API(50% 비용).
- **폴백 체인 (A7):** 마인드로직 → Claude → GPT. `providers/` 추상화에 이미 자리 있음. 한 공급자 실패(예외/`refusal`) 시 다음으로.

### 2.3 파일 / 코드 (즉시 착수 가능)

**`backend/app/llm/providers/anthropic.py`** (스텁 → 구현)
```python
from anthropic import Anthropic

from app.config import settings


class LLMRefusal(RuntimeError):
    pass


class AnthropicProvider:
    name = "claude"

    def __init__(self) -> None:
        self._client = Anthropic(api_key=settings.anthropic_api_key)

    def complete(self, prompt: str, *, system: str, json_schema: dict | None = None) -> str:
        output_config: dict = {"effort": "low"}
        if json_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": json_schema}
        resp = self._client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            output_config=output_config,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.stop_reason == "refusal":  # opus 4.8도 refusal 가능 → 폴백 트리거
            raise LLMRefusal(str(resp.stop_details))
        return "".join(b.text for b in resp.content if b.type == "text")
```
> 주의: `thinking`/`temperature`/`top_p`/`budget_tokens` **넣지 말 것** — opus 4.8에서 이들은 400. 단순 통역이라 불필요하기도 함.

**`backend/app/llm/translator.py`** (스텁 → 구현)
```python
import json

from app.llm.providers import provider_chain  # 폴백 체인 (마인드로직→Claude→GPT)

TRANSLATOR_SYSTEM = """너는 학업 분석 대시보드의 '통역기'다.
- 점수·등급·판정을 만들거나 바꾸지 않는다. 주어진 수치만 근거로 '왜'를 설명한다.
- 한국어 1~2문장. 단정 회피 톤(~할 수 있어요, ~경향이 있어요). 인과 단정 금지.
- 서두·군더더기 없이 문장만 출력한다."""

_CARD_A_SCHEMA = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "properties": {"reason_short": {"type": "string"}, "why_summary": {"type": "string"}},
        "required": ["reason_short", "why_summary"],
        "additionalProperties": False,
    },
}


def translate_card_a(courses: list[dict]) -> dict[str, dict]:
    """courses: [{course_id, course_name, grade, score_percent, factors:[{label, contribution}]}]
    반환: {course_id: {reason_short, why_summary}}"""
    prompt = json.dumps({"courses": courses}, ensure_ascii=False)
    raw = provider_chain().complete(prompt, system=TRANSLATOR_SYSTEM, json_schema=_CARD_A_SCHEMA)
    return json.loads(raw)
```

**`backend/app/llm/providers/__init__.py`** — `provider_chain()` = 순서대로 시도, 실패 시 다음. (마인드로직 엔드포인트 미확정이면 Claude를 1순위로 임시 운용 — A7.)

### 2.4 결정론 가드레일
- 엔진이 `grade`/`score_percent`를 확정 → translator는 그 값을 **입력으로만** 받고 prose만 낸다.
- 시스템 프롬프트에 "숫자 변경 금지" 명시 + 구조화 출력은 `reason_short`/`why_summary` 두 문자열만 허용(점수 필드 없음) → 구조적으로 LLM이 점수를 못 건드림.

---

## 3. 실데이터 들어오면 분석 어떻게 — 엔진

### 3.1 카드 A 추천기 (지금 설계 가능)
점수 결합 **고정 순서**(CLAUDE.md): `content + cohort → hybrid → prereq_filter(감산) → restriction_filter(차단)`.
- **content-based:** 과목 특성/설명 유사도 (이수 과목 ↔ 후보).
- **cohort 통계:** 유사 코호트의 수강 비율. *협업필터링(CF)은 코어로 부적합(표본 작고 희소) — 코호트 통계 + 콘텐츠 유사도가 권장, CF는 추후 확장.*
- **prereq 감산:** 1단계 산출물의 `prereq_tree_json`(AND/OR 트리)로 선이수 충족도 평가 → 미충족 시 감산.
- **restriction 차단:** 4정형 패턴(`allowed`/`forbidden`/`major_only_*`)으로 수강 불가 차단.

### 3.2 factors ↔ 엔진 신호 (why-panel과 직결)
mockup "왜?" 패널의 요소가 곧 엔진 신호다 — 엔진이 과목별로 이 값들을 `RecommendationFactor[]`로 내보내면 점수와 통역이 같은 소스를 쓴다:

| factor 라벨 | 엔진 신호 |
|---|---|
| 콘텐츠 유사도 | content-based |
| 코호트 선호도 | cohort 통계 |
| 시간 가중 평점 | 학기 가중 평점 |
| 사용자 선호 매칭 | 입력 체크박스(영역/선호) |
| 트랙 충족도 | 교양 영역 매핑 (A6) |
| 선이수 충족도 | prereq_filter |
| 학년 적합도 | 권장 학년 |

### 3.3 카드 C/D (A1 의존 — 지금 막힘)
- **카드 C** 다전공 경로 분포 + 평균 추가학점: 졸업생 이수경로 데이터 필요.
- **카드 D** 유사 졸업생 진로 클러스터: 이수경로 **임베딩**(A10: 과목ID BoW/TF-IDF vs 설명 임베딩 평균 vs Sentence-BERT) → 거리로 유사 N명 추출 → **클러스터링**(A11: K-Means vs HDBSCAN) → 진로 분포.
- 둘 다 A1(필드 구성: 학기별 이수 시퀀스? 평점? 진로 라벨?) 확정 전엔 엔진 시그니처를 못 박는다.

### 3.4 튜닝 (실 분포 확인 후)
- **A5** 감산 폭 수치 + 등급 컷오프(강추/고려/유보)는 실 후보 풀 점수 분포 보고 결정.

---

## 4. 단계별 로드맵 + 결정 게이트

| Phase | 산출물 | 선행 | 막는 미결정 |
|---|---|---|---|
| P1 | `s_compass_courses.db` (5테이블) | — | 없음 (진행 중) |
| **§2 "왜?"** | anthropic provider + translator + 폴백 | P1 일부(엔진 factors) | A7(폴백 우선순위)·A13(이 계획이 닫음) |
| P2 | 카드 A 실 `/analyze` | P1, 엔진 recommender | A5(감산 수치)·A6(교양 영역) |
| P3 | 계약 동기화 + 프론트 실연결 | P2 | A12(수동 vs codegen) |
| P4 | 카드 C/D 엔진 | **A1 졸업생 데이터** | A1·A10·A11 |

**지금 병렬 착수 가능:** P1(빌드), §2(Claude "왜?" — 엔진 factors 인터페이스만 합의되면 mock factors로 먼저 통역 테스트 가능).
**본선/데이터 수령 후:** P4 라인.

---

## 5. 첫 묶음 — Claude "왜?" 실제 태스크 (TDD)

> 엔진이 아직 없어도, factors 입력 형태만 고정하면 translator는 **지금** 만들고 테스트할 수 있다(mock factors 입력).

- [ ] **T1.** `anthropic` 의존성 추가: `uv add anthropic` → `backend/pyproject.toml` 확인
- [ ] **T2.** 실패 테스트: `backend/tests/unit/test_translator.py` — `translate_card_a([{course_id:"CSE3013", ...factors}])`가 각 course_id에 `reason_short`/`why_summary` 문자열을 반환하고 **점수 필드는 없음**을 단언 (provider는 fake로 주입해 결정론 테스트)
- [ ] **T3.** `providers/base.py`에 `complete(prompt, *, system, json_schema=None)` 시그니처 확정(현재 Protocol 갱신) + `FakeProvider`(테스트용)
- [ ] **T4.** `translator.py` 구현(§2.3) → T2 통과
- [ ] **T5.** `providers/anthropic.py` 구현(§2.3) + `provider_chain()`(폴백) — 네트워크 호출은 통합 테스트로 분리(`tests/integration`, 키 있을 때만)
- [ ] **T6.** 가드레일 테스트: fake provider가 점수를 바꾼 JSON을 줘도 translator 반환 타입에 점수 필드가 없음을 단언(구조적 차단 확인)
- [ ] **T7.** 커밋

---

## 결정 필요 (이 계획이 새로 던지는 것)
- **모델/비용:** "왜?" 통역에 `claude-opus-4-8`(기본) vs `claude-haiku-4-5`(저비용). — 너의 선택.
- **A13 종료안 확정:** "엔진이 factors 산출 → translator 통역" 으로 닫을지. (이 계획의 전제)
- **A7:** 마인드로직 엔드포인트 미확정 동안 Claude 1순위 임시 운용 여부.
