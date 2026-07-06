# Open Questions

미결정 사항 추적. 결정될 때마다 해당 항목을 닫고 결정 내용을 기록한다.

## 결정 완료 (참고용)

- **백엔드 패키지 관리** → `pyproject.toml` + uv. `requirements.txt`는 `uv export`로 변환.
- **DB 접근** → raw `sqlite3` + `app/db/schema.sql` 단일 스키마. ORM 없음.
- **프론트 빌드** → Vite + React + TypeScript. 프로토타입은 디자인 토큰만 추출, 원본은 `frontend/legacy/` 보존.
- **카드 구성** → A (추천 과목, 가로 2칸), C (다전공 경로), D (유사 졸업생 진로). 카드 B 제거.
- **학과명 정규화** → 원문 보존, 추천 풀 산출 시점에 합집합 적용.
- **수강 제한 패턴** → 4가지 정형 (`allowed`, `forbidden`, `major_only_allowed`, `major_only_forbidden`). 비정형 0건.
- **다학기 저장** → course_offerings 테이블 신설 (courses 는 latest-wins 1행, 개설 이력 분리). 6테이블.
- **카드 A 응답 구조 (구 A2)** → 통합 `DashboardResponse` 유지. `frontend/src/types/api.ts` 확장 계약이 진실원, 백엔드 `schemas/cards.py`가 미러 (2026-07-06 확정).
- **"왜?" 패널 데이터 (구 A13)** → 전용 why 필드 신설 없이 기존 `factors`/`why_summary`/`cluster` 필드를 백엔드가 결정론 점수 분해로 채움 (2026-07-06 확정).

## 미결정 — 본격 구현 전에 정해야 함

### A1. 졸업생 데이터 실 컬럼 매핑 (잔여)
- **부분 결정**: 잠정 프레임 확정 — `app/adapters/alumni_types.AlumniRecord` (코어 `alumni_id`+`department`, 나머지 Optional). 스펙: `superpowers/specs/2026-06-29-alumni-data-frame-design.md`.
- **잔여**: 학사팀 실데이터 실 컬럼 → `AlumniRecord` 매핑. `adapters/real_alumni.py` 한 곳에서 수령 후 작성. 프레임은 입력 데이터에 따라 비파괴적으로 수정될 수 있음.

### A3. 강의계획서 PDF 통합 시점
- 본선 시연 범위 포함 vs 자리만 만들고 추후.
- "왜?" 패널의 깊이 차이가 큼.

### A4. 시연 학과 범위
- 전 학과 vs 컴공 한정 vs 지식융합미디어학부 한정.
- UI 상 사용자는 "지식융합미디어학부 3학년"으로 설정됨 → 그 학부 우선 자연스러움.
- 데이터/시간 제약 보고 결정.

### A5. 추천도 가중치 재조정 (잔여)
- **부분 결정**: 점수 공식·가중치 prior·선이수 감산(최대 −40)·등급 컷오프(강추≥80/고려60~79/유보<60) 잠정 확정 — `engines/recommender/weights.py`, `scoring.py`. 스펙: `superpowers/specs/2026-06-30-card-a-scoring-weights-design.md`.
- **잔여**: 실 후보 풀 점수 분포 + 졸업생 실제 수강(튜닝 정답)으로 가중치·컷오프 재조정.

### A6. 카드 A 교양 영역 매핑
- UI에 공통선택 4영역, 자유선택 9영역 구현됨.
- 1단계 산출물 스키마(`courses`)에는 교양 영역 분류 필드가 없음.
- 추가 컬럼 필요 여부 결정 + 매핑 데이터 소스 확보.

### A7. LLM 키 fallback 체인 우선순위 (잔여)
- **부분 결정**: AnthropicProvider 우선 구현 (키 보유, `config.ANTHROPIC_API_KEY`). 마인드로직/GPT는 스텁 유지 (2026-07-06).
- **잔여**: 마인드로직 엔드포인트/인증/한도 확정 시 fallback 체인(마인드로직 → Claude → GPT) 구성.

### A8. 환경 분리
- 단일 환경 vs dev/prod 분리.
- 시연 일정과 데이터 민감도(실 졸업생) 따라 결정.

### A9. 마이그레이션 도구
- Alembic 도입 여부.
- 5테이블 잠겨있고 빌드 스크립트가 DB를 재생성하는 구조라 현재로선 불필요. 본선 후 운영 단계 진입하면 재검토.

### A10. 임베딩 표현 (잔여)
- **부분 결정**: mock 단계는 (1) 과목 ID TF-IDF 채택 (2026-07-06).
- **잔여**: 실데이터 표본 수·학기별 시퀀스 보존 여부 확인 후 (2) 과목 설명 임베딩 평균, (3) Sentence-BERT 문장화 재검토.

### A11. 카드 D 클러스터링 알고리즘 (잔여)
- **부분 결정**: mock 단계는 K-Means 채택 (k = mock 진로 라벨 수 기반, 2026-07-06).
- **잔여**: 실 졸업생 수·진로 라벨 카디널리티 확인 후 HDBSCAN 재검토.

### A12. 프론트 ↔ 백엔드 타입 동기화
- 수동 미러 vs codegen(예: openapi-typescript).
- 본선 일정 빠듯하면 수동, 여유 있으면 codegen.

## 추가/변경 시 규칙

- 새 미결정 사항이 생기면 이 문서에 추가하고 사용자에게 보고.
- 결정되면 위 "결정 완료" 섹션에 한 줄로 옮기고 미결정 항목 본문 삭제.
