# S-Compass 멀티에이전트 구현 로드맵 (2026-07-06)

> **운영 방식:** 메인 세션(플래너)이 웨이브별 상세 플랜을 작성하고, **backend 담당 에이전트**와 **frontend 담당 에이전트**가 각자 플랜 md를 실행한다. `docs/`는 두 에이전트 공유 참조.

## 현황 스냅샷 (2026-07-06)

**구현 완료:** 파서 3종(restriction/remarks/alias) + 유닛 테스트 17개, Row 스키마(`schemas/rows.py`), 졸업생 프레임(`adapters/alumni_types`, mock 어댑터, generate_mock_alumni), 카드 A 점수 모듈(`engines/recommender/scoring.py`+`weights.py`), `.env` 키 로드(`config.py`), 프론트 전체 화면(mock 픽스처 구동).

**스텁(미구현):** `course_loader`·`prereq_parser`·`build_course_db`, `db/connection`+`queries/*`, `core/{prereq_eval,alias_resolver,dept_normalizer}`, `engines/{recommender 5모듈, pathway, career}`, `cards/*`, `llm/{translator,prompts,providers}`, `api/{analyze,courses}`, 프론트 실 API 연동.

## ⚠️ 발견된 계약 격차 (Wave 2에서 해소)

`frontend/src/types/api.ts`는 mockup UI 요구대로 확장됨(profile, cluster, factors, candidates, CardC/D 확장 필드)인데 `backend/app/schemas/cards.py`는 구버전 최소 스키마. 프론트 코드 주석 방침대로 **types/api.ts를 진실원으로 보고 백엔드가 미러**한다(A2 통합 응답 유지). `StudentInput` 5필드는 양쪽 일치 — 변경 금지.

## 에이전트 분담 / 참조 문서

| 에이전트 | 작업 영역 | 필수 참조 md |
|---|---|---|
| backend | `backend/` (+ 지정된 docs 갱신) | 루트 `CLAUDE.md` → `backend/README.md` → `docs/ARCHITECTURE.md` → `docs/DATA_SCHEMA.md` → 웨이브 플랜 md |
| frontend | `frontend/` | 루트 `CLAUDE.md` → `frontend/README.md` → `docs/ARCHITECTURE.md` → 웨이브 플랜 md |
| 공유 | `docs/` (읽기는 자유, 쓰기는 플랜에 명시된 파일만) | `docs/API_SPEC.md`, `docs/OPEN_QUESTIONS.md` |

**충돌 방지 규칙:** ① 서로의 디렉토리 수정 금지. ② 공유 `docs/` 쓰기는 웨이브 플랜에 명시된 파일만(동일 웨이브에서 두 에이전트가 같은 docs 파일을 쓰지 않도록 플랜에서 보장). ③ 커밋은 자기 변경 파일만 명시적으로 `git add`(『`git add -A` 금지』). ④ `index.lock` 충돌 시 몇 초 후 재시도. ⑤ push 금지.

## 웨이브 계획

| 웨이브 | 담당 | 내용 | 의존성 | 플랜 문서 |
|---|---|---|---|---|
| **W1-B** (진행) | backend | course DB 빌드: `course_offerings` 스키마, `course_loader`(CSV), `prereq_parser`, `build_course_db`, 통합 테스트 | 없음 (스펙 완료) | `2026-07-06-backend-course-db-build.md` |
| **W1-F** (진행) | frontend | 입력 폼 → `StudentInput` 배선, `api.analyze` 경유(mock 토글 유지), 에러 화면 | 없음 | `2026-07-06-frontend-analyze-wiring.md` |
| **W2** | backend | 계약 미러(`schemas/cards.py` ← `types/api.ts`) + `db/connection`+`queries/{course,prereq}` + `core/{prereq_eval, alias_resolver, dept_normalizer}` | W1-B (DB 존재) | 웨이브 시작 시 작성 |
| **W3** | backend | recommender 5모듈(content/collab/hybrid/prereq_filter/restriction_filter — 기존 scoring·weights 결합) + `cards/card_a` + factors/why_summary 채움 | W2 | 〃 (교양 후보 A6 미결 → `is_general=1` 풀, `area_label=null`) |
| **W4** | backend | `engines/pathway` + `engines/career`(mock alumni) + `cards/card_c`·`card_d` | W2 (W3와 부분 병행 가능) | 〃 |
| **W5** | backend | `llm/translator` + `prompts` + `providers/anthropic` (통역 1~2문장, 실패 시 결정론 문구 폴백) | W3·W4 | 〃 |
| **W6** | backend + frontend | `api/analyze` 배선(+CORS), `api/courses` 디버그, 프론트 `VITE_USE_MOCK=false` E2E 검증, `docs/API_SPEC.md` 최종화 | W1~W5 | 〃 |
| **W7** (실데이터 수령 후) | backend | `adapters/real_alumni` 매핑(A1), 가중치·컷오프 튜닝(A5), 시연 학과 범위(A4) | 학사팀 데이터 | 〃 |

각 웨이브 시작 시 메인 세션이 superpowers:writing-plans로 상세 플랜(파일·코드·TDD 단계 포함)을 작성한 뒤 해당 에이전트에 디스패치한다. 웨이브 종료 시 메인 세션이 결과 리뷰 후 다음 웨이브 진행.

## 잠정 채택 (사용자 확인 대기 — 반대 시 해당 웨이브 전에 변경)

- **A2**: 통합 `DashboardResponse` 유지 (현행).
- **A7**: LLM은 **AnthropicProvider 우선 구현** (키 보유). 마인드로직/GPT는 스텁 유지 — 엔드포인트 확정 시 추가.
- **A10**: 이수경로 임베딩 = **과목 ID TF-IDF** (mock 단계 최소 구현, 실데이터 후 재검토).
- **A11**: 카드 D 클러스터링 = **K-Means** (mock 진로 라벨 수 기반 k, 실데이터 후 HDBSCAN 재검토).
- **A13**: "왜?" 패널 = `types/api.ts`에 이미 있는 `factors`/`why_summary`/`cluster` 필드를 **백엔드가 결정론 점수 분해로 채움** (전용 why 필드 신설 안 함).

## 미결정 유지 (블로킹 아님)

A1 잔여(실 컬럼 매핑), A3(강의계획서 PDF — W7 이후 재검토), A4, A5 잔여, A6(교양 영역 매핑 — W3는 area_label 없이 진행), A8, A9, A12(수동 동기화 유지).

## 웨이브 공통 검증 기준

- backend: `uv run pytest tests/unit tests/integration` 전체 통과 + 해당 웨이브 산출물 실행 확인.
- frontend: `npm run build` (tsc 포함) 성공 + mock 모드 기존 동작 회귀 없음.
- W6: 백엔드 기동 + `VITE_USE_MOCK=false` 프론트에서 프로필 A 분석 → 대시보드 렌더 확인.
