# Architecture

> 이 문서는 `CLAUDE.md`의 모듈 책임 경계를 보강한다. 신규 합류자는 이 문서 → `CLAUDE.md` 순으로 읽으면 된다.

## 4계층 (제안서 2.2 기준)

| 계층 | 디렉토리 | 책임 |
|---|---|---|
| Interface | `frontend/`, `backend/app/api/` | 입력 폼 / 대시보드 / HTTP 라우트 |
| Recommendation | `backend/app/engines/`, `backend/app/llm/` | 점수 계산 + 자연어 통역 |
| Analysis | `backend/app/core/`, `backend/app/parsers/` | 평가 + 원본 구조화 |
| Data | `backend/app/db/`, `backend/app/adapters/`, `backend/data/` | SQLite + 졸업생 어댑터 + 벡터 인덱스 |

## 데이터 파이프라인 (단방향)

```
raw xls/pdf  →  parsers/  →  scripts/build_*  →  data/processed/*.db  →
db/queries/  →  engines/  →  cards/ (+ llm/translator)  →  api/  →  frontend
```

- 1단계 산출물 `s_compass_courses.db`는 **런타임 재생성하지 않는다.**
- API 핸들러는 `cards/` 만 호출. 엔진/LLM/DB를 직접 import 하지 않는다.

## 카드 ↔ 엔진 매핑

| 카드 | 오케스트레이터 | 엔진 위치 | 핵심 흐름 |
|---|---|---|---|
| A — 추천 과목 | `app/cards/card_a.py` | `app/engines/recommender/` | content + collab → hybrid → prereq_filter (감산) → restriction_filter (차단) |
| C — 다전공 경로 | `app/cards/card_c.py` | `app/engines/pathway/` | 다전공 분포 집계 + 경로별 추가학점 평균 |
| D — 유사 졸업생 진로 | `app/cards/card_d.py` | `app/engines/career/` | 임베딩 → 유사도 top-N → 클러스터 |

**카드 B(졸업 진척도)는 제거됨.** SAINT가 이미 제공하는 정보 제공형 기능과 차별화 약함.

## 추천 점수 결합 순서 (절대 깨지면 안 됨)

```
content_based + collaborative
        ▼
      hybrid
        ▼
  prereq_filter   (감산: 미이수 시 -50점 등. 배제 아님)
        ▼
restriction_filter (차단: forbidden / major_only_forbidden)
```

필터를 hybrid 이전에 적용하면 협업필터링 코호트 신호가 망가진다.

## 차별화 — "LLM ≠ 생성형 AI"

대다수 출품작이 LLM 챗봇 형태인 것과 달리, S-Compass는:

- 점수 계산·판정·추천: 결정론적 알고리즘 + ML 모델 (임베딩/추천/클러스터링/예측).
- LLM 역할: **정형 결과를 1~2문장 자연어로 통역만**. "왜?" 패널에서 더 긴 설명.
- 입력은 **정형 폼**, 출력은 **정형 대시보드 + 짧은 자연어 사유**의 하이브리드. 챗봇 아님.

## 데이터 자산 (출처/우선순위)

| 자산 | 용도 | 상태 |
|---|---|---|
| 학사팀 익명화 졸업생 이수경로/진로 (메인) | 카드 C·D 학습 데이터 | 본선 진출 후 접근. 그 전엔 mock 사용 |
| `개설교과목정보.xls` (보조 1) | 카드 A 후보 풀, 5테이블 빌드 | 확보 완료, 분석 완료 |
| 강의계획서 PDF (보조 2) | "왜?" 패널 보강, 권장 선수 추출 | 일부 확보, Poppler 파서 동작 검증 |

**강의계획서를 메인 자산으로 강조 금지.** 메인은 이수경로·진로.

## 1단계 산출물 스키마

6테이블 (DDL은 `backend/app/db/schema.sql` 단일 정의):

- `courses` — 과목 마스터 (~903행)
- `course_offerings` — 학기별 개설 이력
- `course_prerequisites` — AND/OR 트리 JSON (~50행)
- `course_aliases` — 옛 코드/대체과목 별칭 (~100행 예상)
- `course_restrictions` — 학과별 수강 제한 (~400행 예상, 4가지 정형 패턴)
- `parse_warnings` — 파싱 실패/모호 케이스 로그

`docs/DATA_SCHEMA.md` 와 `backend/app/db/schema.sql` 가 동일 진실원.

## 학과명 정규화

DB는 원문 그대로. **계층 구조 정규화하지 않음.**
추천 풀 산출 시점(`app/core/dept_normalizer.py`)에서만 학부+학과 합집합 적용.

예: 지식융합미디어학부 학생 → 지식융합미디어대학(22) + 미디어&엔터테인먼트학과(20) + 아트&테크놀로지학과(19) + 신문방송학과(17) = 78개 후보.

## 어댑터 격리 (mock ↔ real)

`app/adapters/alumni_source.py`가 Protocol. `mock_alumni.py`(개발 기본값)와 `real_alumni.py`(본선 후) 구현체. 엔진/카드는 Protocol만 의존하므로 데이터 소스 교체가 한 곳에 집중된다.
