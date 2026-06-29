# 졸업생 데이터 잠정 프레임 — 설계 (A1)

> **성격:** 실데이터(학사지원팀)의 컬럼/규모를 모르는 상태에서, 카드 C/D가 *소비*하는 형태로부터 역산한 **백엔드 내부 표준 레코드(canonical frame)**를 정의한다. 실 컬럼 매핑은 어댑터 한 곳으로 연기한다. `OPEN_QUESTIONS.md` A1을 부분적으로 닫는다(잠정 프레임 확정, 실 매핑만 잔여).

> ⚠️ **잠정 명세 — 입력 데이터에 따라 수정될 수 있음.** 본 문서는 실 입력 데이터를 보기 전에 *소비 측*만으로 역산한 잠정안이다. 학사지원팀 실데이터의 실제 컬럼/규모/형태가 확정되면 프레임 필드·Optional 여부·"비었을 때 후퇴" 계약(§4)이 바뀔 수 있다. 변경은 §5 절차를 따르고 본 문서를 함께 갱신한다(프레임에 없던 유용한 신호 → Optional 필드 추가는 비파괴적 변경).

**설계 기준:** 프론트 `dashboard.fixture.ts`가 그려내는 카드 C/D·cluster·KPI를 mock으로 재현할 수 있는 **최소** 프레임. 단 필드 구성은 실데이터에서 나올 법한 단위로 잡고, 핵심 식별자(`alumni_id`+`department`) 외 전부 Optional로 두어 부분 데이터에도 깨지지 않게 한다.

---

## 1. 캐노니컬 프레임 — `app/adapters/alumni_types.py` (신규, Pydantic)

이 프레임은 **API 계약이 아니다**(`DashboardResponse`에 안 들어감). 백엔드 데이터 계층의 내부 표현이므로 `schemas/`(프론트 미러 대상)가 아닌 `adapters/` 옆에 둔다.

```python
from typing import Literal
from pydantic import BaseModel


class Major(BaseModel):
    label: str                                                  # "컴퓨터공학", "경영학"
    role: Literal["primary", "double", "triple", "minor"] | None = None
    credits: float | None = None                                # 이 전공으로 이수한 학점


class Enrollment(BaseModel):
    course_id: str
    year_taken: int | None = None                               # 1~4 학년
    term_taken: int | None = None                               # 1 | 2


class Career(BaseModel):
    type: Literal["job", "grad", "other"] | None = None         # 카드 D 군집 버킷
    label: str | None = None                                    # 세부 진로 "국내 대학원 (CS)" → sub_chips 원천


class AlumniRecord(BaseModel):
    alumni_id: str                                              # 필수 (카운트/중복제거)
    department: str                                             # 필수 (코호트 필터)
    majors: list[Major] = []                                    # 카드 C — 비면 []
    enrollment: list[Enrollment] = []                           # 카드 D — 비면 []
    career: Career | None = None                                # 카드 D
```

### fixture 항목 ↔ 프레임 매핑

| 소비처 | 사용하는 프레임 필드 | 산출 |
|---|---|---|
| 카드 C 경로 분포 | `department`, `majors[].label/role` | 같은 학과 졸업생을 전공 조합으로 그룹 → count/share |
| 카드 C 평균 추가학점 | `majors[].credits` | 경로별 major1/major2/major3 학점 평균 |
| 카드 C `cohort_label` | `department` | 학과별 졸업생 총수 |
| 카드 D 유사도 / `similar_alumni_n` | `enrollment[].course_id` (+`year_taken`/`term_taken`) | 학생 ↔ 졸업생 임베딩 거리 → top-N |
| 카드 D 진로 분포 | `career.type` | job/grad/other 버킷 count/share |
| 카드 D `sub_chips` | `career.label` (type 필터 후 그룹) | 세부 진로 칩 |
| cluster `common_courses` | `enrollment[].course_id` | 과목 중첩 카운트 |
| cluster factors (순서/학년별 학점) | `enrollment[].year_taken/term_taken` + `course_id`→`courses.credit` 조인 | 이수 순서·학년별 학점 분포 신호 |
| `pattern_summary` 등 문구 | 위 신호 → `llm/translator` 통역 | (점수/판정은 엔진, 문장은 LLM) |

> `cluster_label`("대학원 진학" 등 coarse 버킷)은 `career.type`에서 엔진이 매핑한다. `career.label`은 fine 단위로 두고 `sub_chips`로 그룹한다. 세부 분야를 별도 필드로 더 쪼개는 것은 실데이터 형태 확인 후 재검토(현재 YAGNI).

---

## 2. 어댑터 경계

호출부(엔진/카드)는 `AlumniSource` Protocol만 의존한다. mock ↔ real 교체점은 어댑터 한 곳.

- **`app/adapters/alumni_source.py`** — `AlumniSource` Protocol 반환 타입을 `list[dict]` → `list[AlumniRecord]`로 갱신.
  ```python
  class AlumniSource(Protocol):
      def list_by_department(self, department: str) -> list[AlumniRecord]: ...
      def all(self) -> list[AlumniRecord]: ...
  ```
- **`app/adapters/mock_alumni.py`** — `MockAlumniSource(AlumniSource)`. `data/mock/alumni.json` 로드 → `AlumniRecord`로 검증/파싱. 개발·시연 기본값.
- **`app/adapters/real_alumni.py`** — `RealAlumniSource(AlumniSource)`. 실 컬럼 → `AlumniRecord` 매핑. **지금은 자리 + 매핑 TODO만.** (§5 참조)
- **`app/api/deps.py`** — `get_alumni_source()`가 설정 플래그에 따라 Mock/Real 중 하나를 반환(스위치).

---

## 3. mock 생성기 — `scripts/generate_mock_alumni.py`

규모 미상 대응으로 전부 기본값 있는 파라미터:

- `n_per_dept` (학과당 졸업생 수), `departments` (대상 학과 목록)
- 다전공 비율 분포 (단일전공/2전공/3전공 비중)
- `career` 라벨 풀 (type별 fine label 후보)
- 학기 시퀀스 길이 / 학기당 과목 수

course_id는 빌드된 `data/processed/s_compass_courses.db`에서 샘플(없으면 합성 코드로 폴백). 출력: `data/mock/alumni.json` (`AlumniRecord[]` 직렬화).

> 데이터를 런타임에 재생성하지 않는다(파이프라인 단방향). 이 스크립트로만 mock 갱신.

---

## 4. "비었을 때 후퇴" 계약 (프레임의 핵심)

부분 데이터에도 깨지지 않게, 엔진은 빈 Optional 필드를 다음과 같이 후퇴 처리한다. 프론트는 이미 대응 장치를 갖고 있다.

| 빈 필드 | 엔진 후퇴 동작 | 프론트 기존 장치 |
|---|---|---|
| `majors` / `credits` 없음 | 카드 C "기타 경로"로 흡수, 학점 `null` | `PathwayEntry.dim`, `credits: null` |
| `year_taken` / `term_taken` 없음 | cluster "이수 순서"·"학년별 학점" factor → N/A | `FactorKind: "na"` |
| `enrollment` 빈약 | 유사도 신뢰↓ → 해당 패턴 "표본 부족·보류" | `career_patterns` 기존 문구 |
| `career` 없음 | 진로 분포 분모에서 제외 | — |

---

## 5. 실데이터 수령 시 작업 지점 (4곳)

본선 진출 후 학사지원팀 데이터를 받으면, **아래 순서로 4곳만** 손대면 mock → real 전환이 끝난다. 프레임·엔진·카드·프론트는 그대로다.

1. **파일 안착** → `backend/data/external/` 에 익명화 export 파일을 둔다 (`config.EXTERNAL_DIR`). git 제외(`data/README.md` 정책), `.gitignore` 패턴은 이 시점에 잠금.
2. **매핑 구현** → `app/adapters/real_alumni.py` 의 `RealAlumniSource` 에서 **실 컬럼 → `AlumniRecord`** 변환을 작성한다. 매핑되지 않는 필드는 비워둔다(Optional이므로 §4 후퇴가 작동). **이 한 곳이 유일한 매핑 지점.**
3. **스위치 전환** → `app/api/deps.py` 의 `get_alumni_source()` 가 `MockAlumniSource` 대신 `RealAlumniSource` 를 반환하도록 설정 플래그를 바꾼다 (`config.py` 에 플래그 추가).
4. **문서 갱신** → `OPEN_QUESTIONS.md` A1 을 닫고, `DATA_SCHEMA.md` "졸업생 데이터" 절을 실 매핑 기준으로 갱신.

> 실 컬럼이 프레임 일부만 채워도 정상 동작한다(§4). 프레임이 실데이터보다 더 많은 필드를 기대하면 그 필드는 N/A로 후퇴할 뿐이다. 반대로 실데이터에 프레임에 없는 유용한 신호가 있으면, 그때 프레임에 Optional 필드를 *추가*하고 엔진이 선택적으로 소비하게 한다(파괴적 변경 아님).

---

## 6. 스코프 경계 (이 설계가 다루지 않는 것)

- **실 컬럼 매핑** → `real_alumni.py`로 연기 (A1 잔여분).
- **임베딩 표현(A10)·클러스터링(A11)** → 엔진 알고리즘 결정. 프레임은 `enrollment` 시퀀스라는 raw material만 제공하므로 **알고리즘 불문** — 이 결정들을 막지도, 미리 정하지도 않는다.
- **카드 A 튜닝(A5 등)** → 무관.

---

## 7. 문서 갱신 (이 설계의 산출 일부)

- `OPEN_QUESTIONS.md` A1 → "잠정 프레임 확정(`adapters/alumni_types.AlumniRecord`), 실 컬럼 매핑만 잔여"로 갱신.
- `DATA_SCHEMA.md` "졸업생 데이터(별도)" 절 → 프레임 요약 + 본 스펙 링크 추가.

---

## 변경/구현 대상 파일 요약

| 파일 | 작업 |
|---|---|
| `app/adapters/alumni_types.py` | **신규** — `Major`/`Enrollment`/`Career`/`AlumniRecord` Pydantic |
| `app/adapters/alumni_source.py` | Protocol 반환 타입 `list[AlumniRecord]`로 갱신 |
| `app/adapters/mock_alumni.py` | `MockAlumniSource` 구현 (json 로드→검증) |
| `app/adapters/real_alumni.py` | 자리 + 매핑 TODO (구현은 데이터 수령 후) |
| `app/api/deps.py` | `get_alumni_source()` 스위치 |
| `scripts/generate_mock_alumni.py` | mock 생성기 구현 → `data/mock/alumni.json` |
| `docs/OPEN_QUESTIONS.md` / `docs/DATA_SCHEMA.md` | 갱신 |
