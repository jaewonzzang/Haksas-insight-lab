# CLAUDE.md

S-Compass 작업 가드레일. 상세는 `docs/ARCHITECTURE.md`, `docs/DATA_SCHEMA.md`, `docs/OPEN_QUESTIONS.md`.

## 프로젝트

학생 입력 1회 → 대시보드(카드 A/C/D + KPI + "왜?"). 챗봇 아님. 모노레포: `backend/` (FastAPI + raw sqlite3 + uv) · `frontend/` (Vite + React + TS + Tailwind).

- 카드 A: 추천 과목 (전공/교양)
- 카드 C: 다전공 경로 분포 + 추가 학점
- 카드 D: 유사 졸업생 진로 클러스터

LLM = 통역만. 점수/판정/추천은 결정론적 + ML.

## 4계층 / 데이터 흐름

```
Interface (frontend/, app/api/)
   → Recommendation (app/engines/, app/llm/)
   → Analysis (app/core/, app/parsers/)
   → Data (app/db/, app/adapters/, data/)
```

파이프라인 (단방향, 런타임 재생성 금지):
```
raw → parsers → scripts/build_* → data/processed/*.db → db/queries → engines → cards (+llm/translator) → api → frontend
```

## 책임 경계 (잘 헷갈림 — 지키기)

- `engines/` = 정형 결과만. **자연어 금지.**
- `llm/translator` = 1~2문장 통역만. **점수/판정 금지.**
- `parsers/` = 원본 → 구조. `core/` = 구조 → 평가. 섞지 말 것.
- `api/` 핸들러 = `cards/` 만 호출. 엔진/LLM/DB 직접 import 금지.
- DB는 원문 보존. 학과명 합집합은 `core/dept_normalizer`에서만.

## 점수 결합 순서 (고정)

```
content + collab → hybrid → prereq_filter(감산) → restriction_filter(차단)
```
필터를 hybrid 이전에 두면 협업필터링 코호트 신호가 망가진다.

## 카드 ↔ 엔진

| 카드 | 오케스트레이터 | 엔진 |
|---|---|---|
| A | `app/cards/card_a` | `engines/recommender/` |
| C | `app/cards/card_c` | `engines/pathway/` |
| D | `app/cards/card_d` | `engines/career/` |

## API / 계약

- 메인: `POST /analyze` → `DashboardResponse` (`app/schemas/cards.py`)
- 디버그: `/courses`, `/health` (외부 노출 X)
- 단일 진실원: `app/schemas/` ↔ `frontend/src/types/api.ts` (수동 동기화, codegen 미결)

## 명령 (요약 — 상세는 각 README)

- 백엔드: `uv sync && uv run uvicorn app.main:app --reload`
- 1단계 빌드: `uv run python scripts/build_course_db.py`
- 프론트: `npm install && npm run dev`
- 테스트: `uv run pytest tests/{unit,integration}`

## 데이터 폴더

- `data/raw/` 원본, `data/processed/` 빌드 산출물, `data/external/` 학사팀 실데이터, `data/mock/` 합성. 전부 git 제외 (`.gitkeep`만).
- 어댑터(`app/adapters/`)가 `mock` ↔ `external` 교체점.

## 응답 / 작업 규칙

- 답변 텍스트는 한국어 (코드/경로/식별자 제외).
- 추측 단정 금지. 여러 해석 가능하면 평등하게 제시.
- 결정 안 된 것은 결정 안 됐다고 표시. 새 미결정은 `docs/OPEN_QUESTIONS.md`에 추가하고 보고.
- 요청 범위 밖 "개선" 금지. 인접 코드/주석/포매팅 건드리지 않음. 매칭 스타일.
- 최소 코드. 200줄을 50줄로 줄일 수 있으면 줄여라. 사변적 추상화/방어 코드/플래그 금지.
- 변경된 모든 라인은 사용자 요청에 직접 추적 가능해야 함.
- 다단계 작업은 짧은 플랜 + 검증 기준 명시 후 진행.
- 위험 작업(삭제/이름변경/구조 이동/푸시) 전에는 확인.
