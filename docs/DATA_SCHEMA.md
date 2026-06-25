# Data Schema

> 단일 진실원: [`backend/app/db/schema.sql`](../backend/app/db/schema.sql). 이 문서는 그것의 사람용 요약이다.

대상 DB: `backend/data/processed/s_compass_courses.db` (SQLite, 빌드 스크립트로만 갱신).

## 5테이블 요약

### `courses` — 과목 마스터 (약 903행)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `course_id` | TEXT PK | `CSE3080` |
| `course_name` | TEXT NN | `자료구조` |
| `department` | TEXT NN | 원문 보존, 정규화 X |
| `credit` | REAL | NULL 8건 (교환학기 등 더미 과목) |
| `recommended_year` | TEXT | `2-4학년` 원문 |
| `target_audience` | TEXT | `전학년` 원문 |
| `is_general` | INTEGER NN | 학과=='전인교육원' → 1, 아니면 0 |
| `description_raw` | TEXT | 과목 설명 원문 |
| `restrictions_raw` | TEXT | 수강신청 참조사항 원문 |

### `course_prerequisites` — AND/OR 트리 (약 50행)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `course_id` | TEXT PK / FK | |
| `prereq_tree_json` | TEXT NN | `{"AND":[...,{"OR":[...]}]}` |
| `prereq_raw` | TEXT NN | `"선수과목 : ..."` 원문 |

**파싱 규칙**: 콤마=AND, `또는`/`or`=OR, 괄호=OR 그룹. 과목코드 정규식 `[A-Z]{2,5}\d{3,4}[A-Z]?`.

예: `"ECO2001, ECO2003(또는 STS2005 또는 STS2006)"`
→ `{"AND": ["ECO2001", {"OR": ["ECO2003", "STS2005", "STS2006"]}]}`

### `course_aliases` — 옛 코드/대체과목 (예상 ~100행)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | INTEGER PK AUTOINC | |
| `new_course_id` | TEXT NN / FK | 현재 개설 과목 |
| `old_course_id` | TEXT | 옛 코드 (있을 때) |
| `old_course_name` | TEXT | 옛 이름 (코드 없을 때) |
| `source_type` | TEXT NN | `'구'` 또는 `'대체과목'` |
| `condition_raw` | TEXT | `'(2015-2018학번)'` 같은 조건 |
| `raw_snippet` | TEXT | |

**의미**: `old_*` 이수 → `new_course_id` 이수로 간주 (단방향).

추출 패턴: `(구)XXX`, `(구) XXX`, `구) XXX`, `XXX 대체과목`, `XXX(YYY)의 대체과목`.

### `course_restrictions` — 학과별 수강 제한 (예상 ~400행)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | INTEGER PK AUTOINC | |
| `course_id` | TEXT NN / FK | |
| `target_dept` | TEXT NN | |
| `status` | TEXT NN | `allowed` / `forbidden` / `major_only_allowed` / `major_only_forbidden` |

**원문 → 정형 매핑**:
- `학과명(가능)` → `allowed`
- `학과명(불가능)` → `forbidden`
- `학과명(1전공 가능)` → `major_only_allowed`
- `학과명(1전공 불가능)` → `major_only_forbidden`

검증된 사실: 수강신청 참조사항 65종 토큰 전부 위 4가지 정형 패턴. 비정형 0건.

### `parse_warnings` — 빌드 시 모호/실패 케이스 로그
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | INTEGER PK AUTOINC | |
| `course_id` | TEXT NN | |
| `field` | TEXT NN | `prerequisites` / `aliases` / `restrictions` |
| `issue` | TEXT NN | |
| `raw_text` | TEXT | |

## 인덱스

- `idx_courses_dept` on `courses(department)`
- `idx_aliases_new` on `course_aliases(new_course_id)`
- `idx_aliases_old` on `course_aliases(old_course_id)`
- `idx_restrictions_course` on `course_restrictions(course_id)`
- `idx_restrictions_dept` on `course_restrictions(target_dept)`

## 졸업생 데이터 (별도)

본선 진출 후 학사지원팀에서 수령. 스키마 미확정 → `OPEN_QUESTIONS.md` A1 참조.
어댑터 인터페이스만 `app/adapters/alumni_source.py`에 잠정 정의.
