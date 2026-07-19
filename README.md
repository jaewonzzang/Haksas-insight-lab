# Saint+ (코드명 S-Compass) · 리포 Haksas-insight-lab

![Saint+ 대시보드](docs/screenshot.png) <!-- TODO: 대시보드 3카드 스크린샷 -->

**학번·이수 내역·관심 진로를 한 번 입력하면, 졸업생 14,942명의 실제 수강 데이터(38만 행)로 계산한 추천 과목 · 다전공 경로 · 유사 선배 이수 경로를 대시보드 한 화면으로 돌려주는 학기당 1회 배치 분석 시스템.**

- **카드 A** — 추천 과목 (전공/교양)
- **카드 C** — 학과 선배들의 다전공 경로 분포 + 추가 이수 학점
- **카드 D** — 유사 이수 경로 선배 N명 추출 → 진학 지향(대학원 연계 과목) 관측

**챗봇이 아니다.** 정형 입력 → 대시보드형 정형 출력 + 짧은 자연어 사유 하이브리드.
LLM은 정형 결과 통역에만 사용. 점수 계산·판정·추천은 결정론적 알고리즘 + ML 모델.

## 내 역할

3인 팀(학생 1명 + 학사지원팀 직원 2명)에서 **단독 기술 담당** — 이 리포의 전 커밋(120+)을 작성.

- **백엔드 전체** — FastAPI 4계층(API → 카드 오케스트레이터 → 추천/경로/진로 엔진 → 데이터 어댑터), raw sqlite3 스키마 설계
- **분석 파이프라인** — 수강편람 xls·강의계획서 PDF(OCR) 파서, 과목 DB 빌드, 졸업생 14,942명 수강 이력 정제·어댑터, 협업필터링+콘텐츠 하이브리드 추천, 홀드아웃 검증(마지막 학기 숨김) 기반 가중치 실측 튜닝
- **LLM 통합** — 결정론 점수를 1~2문장으로 통역하는 translator 계층(Claude API). 판정·점수에 LLM 개입 금지 설계
- **프론트엔드** — React + TypeScript 대시보드 (디자인 프로토타입 → 컴포넌트 이관)
- **외부 기술 협의** — 학사팀 실데이터 수령·비식별화 협의, 협력기업 기술 미팅 창구

## 아키텍처 (요약)

- Interface(React · FastAPI 라우트) → Recommendation(엔진 + LLM 통역) → Analysis(평가 · 파서) → Data(SQLite · 졸업생 어댑터)의 **4계층 단방향**.
- 데이터는 `raw → parsers → build 스크립트 → SQLite → 엔진 → 카드 → API` 파이프라인으로만 흐르고, 빌드 산출물은 런타임에 재생성하지 않는다.
- 추천 점수는 `콘텐츠+협업필터링 → 하이브리드 → 선이수 감산 → 수강제한 차단` 순서 고정 — 필터를 앞에 두면 코호트 신호가 깨진다.
- API 핸들러는 카드 오케스트레이터만 호출(엔진/LLM/DB 직접 접근 금지). mock ↔ 실데이터 교체점은 어댑터 한 곳.

상세: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)

## 모노레포 구성

| 폴더 | 스택 |
|---|---|
| [`backend/`](./backend/) | FastAPI + raw sqlite3 + LLM 통역기 (uv 관리) |
| [`frontend/`](./frontend/) | Vite + React 18 + TypeScript + Tailwind |
| [`docs/`](./docs/) | 아키텍처 / 데이터 스키마 / API / 미결정 사항 |

## 빠른 시작

프론트엔드는 mock 모드로 단독 실행된다. 백엔드는 학사 원본 데이터의 빌드 산출물이 필요한데 개인정보 이슈로 git에서 제외돼 있어 **클론만으로는 전체 실행이 재현되지 않는다** — 공모전 본선 진행 중인 내부 시연용.

```bash
# 백엔드
cd backend
uv sync
uv run uvicorn app.main:app --reload

# 프론트
cd frontend
npm install
npm run dev
```

## 필수 읽기 순서 (신규 합류자)

1. [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — 4계층 + 카드 ↔ 엔진 매핑
2. [`docs/DATA_SCHEMA.md`](./docs/DATA_SCHEMA.md) — 1단계 산출물 5테이블
3. [`docs/OPEN_QUESTIONS.md`](./docs/OPEN_QUESTIONS.md) — 미결정 사항 (작업 전 확인)

## 컨텍스트

- 대회: 2026 서강대학교 생성형 AI 기반 아이디어 공모전 — ① 교육 혁신 분야
- 주최: 서강대 디지털정보처·RISE 사업단, 협력기업 마인드로직
- 기간(본선 진출 시): 2026년 7~8월 약 2개월
- 팀: 학생 1명(아트&테크놀로지학과) + 학사지원팀 직원 2명
