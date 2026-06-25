# S-Compass (UI: Saint+)

학생 학번·이수내역·관심 진로를 입력받아 다음 3개 카드를 한 화면에 반환하는 학기당 1회 배치 분석 시스템.

- **카드 A** — 추천 과목 (전공/교양)
- **카드 C** — 학과 선배들의 다전공 경로 분포 + 추가 이수 학점
- **카드 D** — 유사 졸업생 N명 추출 → 진로 클러스터 분포

**챗봇이 아니다.** 정형 입력 → 대시보드형 정형 출력 + 짧은 자연어 사유 하이브리드.
LLM은 정형 결과 통역에만 사용. 점수 계산·판정·추천은 결정론적 알고리즘 + ML 모델.

## 모노레포 구성

| 폴더 | 스택 |
|---|---|
| [`backend/`](./backend/) | FastAPI + raw sqlite3 + LLM 통역기 (uv 관리) |
| [`frontend/`](./frontend/) | Vite + React 18 + TypeScript + Tailwind |
| [`docs/`](./docs/) | 아키텍처 / 데이터 스키마 / API / 미결정 사항 |

## 빠른 시작 (예정)

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

1. [`CLAUDE.md`](./CLAUDE.md) — 모듈 책임 경계 + 작업 규칙
2. [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — 4계층 + 카드 ↔ 엔진 매핑
3. [`docs/DATA_SCHEMA.md`](./docs/DATA_SCHEMA.md) — 1단계 산출물 5테이블
4. [`docs/OPEN_QUESTIONS.md`](./docs/OPEN_QUESTIONS.md) — 미결정 사항 (작업 전 확인)

## 컨텍스트

- 대회: 2026 서강대학교 생성형 AI 기반 아이디어 공모전 — ① 교육 혁신 분야
- 주최: 서강대 디지털정보처·RISE 사업단, 협력기업 마인드로직
- 기간(본선 진출 시): 2026년 7~8월 약 2개월
- 팀: 학생 1명(아트&테크놀로지학과) + 학사지원팀 직원 2명
