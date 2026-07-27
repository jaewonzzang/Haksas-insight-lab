# Saint+

[![CI](https://github.com/jaewonzzang/Haksas-insight-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/jaewonzzang/Haksas-insight-lab/actions/workflows/ci.yml)

<div align="center">
<img width="240" alt="서강대학교" src="./logo_sogang.png">
</div>

# Saint+ · 학사 데이터 기반 학업 설계 대시보드
> **2026 서강대학교 생성형 AI 기반 아이디어 공모전 — ① 교육 혁신 분야** <br/> **개발기간: 2026.06 ~ 2026.08**

## 배포 주소

> **데모 (mock 모드):** `TODO_VERCEL_URL`
> 샘플 프로필 A~D로 대시보드 전체 동작을 확인할 수 있다. 실 학사 데이터는 쓰지 않는다.
>
> 실데이터 구동은 비공개 미러에서만 한다 — 공개 리포에는 데이터가 없어
> [`render.yaml`](./render.yaml) 만으로는 백엔드가 뜨지 않는다(의도된 제약).

## 팀 소개

|      김재원       |          김명진 선생님         |       이민우 과장님         |
| :------------------------------: | :------------------------------: | :------------------------------: |
| 서강대학교 아트&테크놀로지학과 | 서강대학교 학사지원팀 | 서강대학교 학사지원팀 |
| 기술 총괄 — 백엔드 · 프론트엔드 · 분석 파이프라인 전체 | 기획 · 학사 데이터 | 기획 · 학사 데이터 |

3인 팀(학생 1명 + 학사지원팀 직원 2명)에서 개발은 단독 담당 — 이 리포의 전 커밋을 작성했다.

## 프로젝트 소개

다전공·연계전공·마이크로전공으로 이수 경로가 복잡해졌지만, 학생들은 요람·강의계획서·에브리타임처럼 **파편화되고 주관적인 데이터**를 뒤져 가며 수강신청을 한다. Saint+는 학번·이수 내역·관심 진로를 **한 번 입력**하면, 졸업생 14,942명의 실제 수강 데이터(38만 행)로 계산한 결과를 대시보드 한 화면으로 돌려주는 **학기당 1회 배치 분석 시스템**이다.

- **카드 A** — 추천 과목 (전공/교양)
- **카드 C** — 학과 선배들의 다전공 경로 분포 + 추가 이수 학점
- **카드 D** — 유사 이수 경로 선배 N명 추출 → 진학 지향(대학원 연계 과목) 관측

**챗봇이 아니다.** 정형 입력 → 대시보드형 정형 출력 + 짧은 자연어 사유 하이브리드.
LLM은 정형 결과를 1~2문장으로 **통역**하는 데만 쓰고, 점수 계산·판정·추천은 전부 결정론적 알고리즘 + ML이 맡는다. LLM 키가 없으면 결정론 폴백으로 동작한다.

추천 가중치(코호트 40 · 콘텐츠 25 · 학년 20 · 선호 15)는 졸업생 홀드아웃 343케이스로 실측 검증했다 — **R@8 0.391 · R@20 0.559**, 등급 버킷 실수강률은 **강추 39.6% > 고려 18.1% > 유보 1.2%** 로 단조 분리된다. 재현율 최적 조합이 아니라 상위 추천의 정밀도와 해석 가능성을 택한 값이다. 근거: [`docs/scoring_rationale.md`](./docs/scoring_rationale.md)

## 시작 가이드

### Requirements

For building and running the application you need:

- [Python 3.11+](https://www.python.org/downloads/) (배포 환경 3.13)
- [uv](https://docs.astral.sh/uv/) — 백엔드 패키지 관리
- [Node.js 20.19+](https://nodejs.org/) / npm 10+

### Installation

``` bash
$ git clone https://github.com/jaewonzzang/Haksas-insight-lab.git
$ cd Haksas-insight-lab
```

#### Backend

```bash
$ cd backend
$ uv sync
$ uv run uvicorn app.main:app --reload
# → http://localhost:8000/health · http://localhost:8000/docs (Swagger)
```

#### Frontend

```bash
$ cd frontend
$ npm install
$ npm run dev
```

> 프론트엔드는 mock 모드로 단독 실행된다. 백엔드는 학사 원본 데이터의 빌드 산출물이 필요한데
> 개인정보 이슈로 git에서 제외돼 있어 **클론만으로는 전체 실행이 재현되지 않는다.**

---

## Stacks 🧭

### Environment
![Visual Studio Code](https://img.shields.io/badge/Visual%20Studio%20Code-007ACC?style=for-the-badge&logo=Visual%20Studio%20Code&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=Git&logoColor=white)
![Github](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=GitHub&logoColor=white)

### Backend
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=Python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=SQLite&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=Pydantic&logoColor=white)

### Analysis / LLM
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=NumPy&logoColor=white)
![Anthropic](https://img.shields.io/badge/Claude%20API-D97757?style=for-the-badge&logo=Anthropic&logoColor=white)

### Frontend
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=TypeScript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=Vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=for-the-badge&logo=Tailwind%20CSS&logoColor=white)

### Deploy
![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=Render&logoColor=white)

---

## 화면 구성 📺

| 입력 화면 | 대시보드 (카드 A/C/D) |
| :---: | :---: |
| <img width="329" src="./docs/screenshot/input.png"/> | <img width="329" src="./docs/screenshot/dashboard.png"/> |

> 데모 모드(mock) 화면. 실 학사 데이터 화면은 개인정보 이슈로 미공개.

---

## 주요 기능 📦

### ⭐️ 카드 A — 추천 과목 (전공/교양)
- 졸업생 수강 이력 기반 **협업필터링 + 콘텐츠 유사도 하이브리드** 추천, 전공·교양 각 상위 4과목
- 신호 가중치 **코호트 선호도 40 · 콘텐츠 유사도 25 · 학년 적합도 20 · 사용자 선호 15** (총합 100)
- **이수구분 체크박스 필터** — 전공필수/전공선택/교양 등으로 후보 풀에서 재선별
- 추천 과목마다 **강의계획서 PDF 링크** (파일이 없으면 자동 숨김)

### ⭐️ 카드 C — 다전공 경로 분포
- 같은 학과 선배들이 실제로 택한 다전공 조합 분포 + 그에 필요한 추가 이수 학점

### ⭐️ 카드 D — 유사 이수 경로 선배 진로 클러스터
- 이수 이력이 가까운 선배 N명을 추출해 진학 지향(대학원 연계 과목 이수) 신호를 관측

### ⭐️ 이수 현황 집계
- 전공별 · 과목 성격별(전공입문/전공필수/전공선택 등) 학점·과목수 카운트

### ⭐️ "왜?" 패널
- 점수를 만든 신호별 기여도를 그대로 노출. 자연어 사유는 결정론 결과의 **통역**일 뿐

---

## 아키텍처

- Interface(React · FastAPI 라우트) → Recommendation(엔진 + LLM 통역) → Analysis(평가 · 파서) → Data(SQLite · 졸업생 어댑터)의 **4계층 단방향**.
- 데이터는 `raw → parsers → build 스크립트 → SQLite → 엔진 → 카드 → API` 파이프라인으로만 흐르고, 빌드 산출물은 런타임에 재생성하지 않는다.
- 추천 점수는 `콘텐츠+협업필터링 → 하이브리드 → 선이수 감산 → 수강제한 차단` 순서 고정 — 필터를 앞에 두면 코호트 신호가 깨진다.
- API 핸들러는 카드 오케스트레이터만 호출(엔진/LLM/DB 직접 접근 금지). mock ↔ 실데이터 교체점은 어댑터 한 곳.

상세: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) · 추천 알고리즘 요약: [`docs/recommendation_algorithm.md`](./docs/recommendation_algorithm.md)

### 디렉토리 구조

```bash
├── README.md
├── render.yaml : Render 배포 블루프린트
│
├── backend/ : FastAPI + raw sqlite3 (ORM 없음, uv 관리)
│   ├── app/
│   │   ├── api/ : HTTP 라우트만 (analyze, syllabus, health)
│   │   ├── schemas/ : Pydantic 입출력 단일 정의
│   │   ├── cards/ : 카드 A/C/D 오케스트레이션 (엔진 + LLM + 어댑터 조합)
│   │   ├── engines/ : 정형 결과만 생산 — 자연어 금지
│   │   │   ├── recommender/ : 카드 A — 하이브리드 점수·선이수·수강제한 필터
│   │   │   ├── pathway/ : 카드 C — 다전공 경로 분포
│   │   │   └── career/ : 카드 D — 진로 클러스터
│   │   ├── llm/ : 통역만 — 점수/판정 금지
│   │   ├── core/ : 평가·규칙 (prereq, alias, dept_normalizer)
│   │   ├── parsers/ : 원본 → 구조화
│   │   ├── db/ : schema.sql 단일 정의 + queries/
│   │   └── adapters/ : 졸업생 데이터 mock ↔ 실데이터 교체점
│   ├── scripts/ : 1회성 오프라인 빌드 (build_course_db 등)
│   ├── data/ : git 제외 (raw/ processed/ external/ mock/)
│   └── tests/ : unit / integration
│
├── frontend/ : Vite + React 18 + TypeScript + Tailwind
│   ├── src/
│   │   ├── components/ : BrandHeader, KpiStrip, CreditSummary, WhyPanel ...
│   │   │   └── cards/ : CardA / CardC / CardD
│   │   ├── pages/Dashboard.tsx
│   │   ├── lib/api.ts : POST /analyze 클라이언트
│   │   ├── types/api.ts : 백엔드 schemas 와 수동 동기화
│   │   ├── mock/ : 데모 프로필 A~D fixture
│   │   └── styles/
│   └── legacy/ : 디자인 프로토타입 (빌드 제외, 참조용)
│
└── docs/ : 아키텍처 / 데이터 스키마 / API / 미결정 사항
```

## 필수 읽기 순서 (신규 합류자)

1. [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — 4계층 + 카드 ↔ 엔진 매핑
2. [`docs/DATA_SCHEMA.md`](./docs/DATA_SCHEMA.md) — 1단계 산출물 테이블
3. [`docs/OPEN_QUESTIONS.md`](./docs/OPEN_QUESTIONS.md) — 미결정 사항 (작업 전 확인)

## 컨텍스트

- 대회: 2026 서강대학교 생성형 AI 기반 아이디어 공모전 — ① 교육 혁신 분야
- 주최: 서강대 디지털정보처·RISE 사업단, 협력기업 마인드로직
- 기간(본선 진출 시): 2026년 7~8월 약 2개월

## 이용 안내

2026 서강대학교 생성형 AI 기반 아이디어 공모전 출품작입니다.
코드 이용·인용 문의는 이슈로 남겨 주세요.
