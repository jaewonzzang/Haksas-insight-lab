# course DB 빌드 (4학기 CSV → s_compass_courses.db) — 설계

> **목적:** 4개 학기(2024-2, 2025-1, 2025-2, 2026-1) 개설교과목 CSV를 1단계 산출물 `s_compass_courses.db`로 빌드한다. 파서 3종(restriction·remarks·alias)과 Row 스키마는 이미 구현·테스트 완료. 이 작업은 **`course_loader`(CSV)·`prereq_parser`·`build_course_db`** 구현 + 다학기 저장을 위한 스키마 1테이블 추가다.

> ⚠️ **스키마 결정 변경:** 기존 "5테이블 잠금"(단일 학기 적재 전제)은 4학기 데이터로 재개된다. `courses.course_id` 단독 PK를 유지하려면(=prereq/alias/restriction FK 보존), 학기별 개설 정보를 분리해야 한다 → `course_offerings` 테이블 신설(총 6테이블). 근거: 1,807개 고유 과목 중 1,039개가 2개 학기 이상에 등장.

## 0. 현재 상태 (출발점)

| 구성요소 | 상태 |
|---|---|
| `schema.sql` 5테이블 | 확정 |
| Row 스키마 (`schemas/rows.py`: CourseRow/PrereqRow/AliasRow/RestrictionRow/WarningRow) | 구현 완료 |
| `restriction_parser`·`remarks_parser`·`alias_parser` | 구현 완료 + 유닛 테스트 17개 통과 |
| `course_loader`·`prereq_parser` | 스텁 (유닛 테스트 22개 skip 상태로 케이스 정의됨) |
| `build_course_db` | 스텁 (`# TODO`) |
| 입력 데이터 | `data/raw/개설교과목정보_{2024-2,2025-1,2025-2,2026-1}.csv` — 28열·헤더 동일·utf-8-sig 확인 |

## 1. 스키마 변경 — `course_offerings` 신설

- **`courses`**: `course_id` PK 유지, course_id당 1행, **latest-wins 메타데이터**(가장 최근 year-semester 행이 값을 채움). prereq/alias/restriction의 `course_id` FK 그대로 유효.
- **신규 `course_offerings`** — "어느 학기에 개설됐나"만 보관(최소 컬럼). 학기별 학점/분반 변동은 추적하지 않음(YAGNI).

```sql
CREATE TABLE course_offerings (
    course_id  TEXT    NOT NULL,
    year       INTEGER NOT NULL,
    semester   INTEGER NOT NULL CHECK (semester IN (1, 2)),
    PRIMARY KEY (course_id, year, semester),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);
CREATE INDEX idx_offerings_year_sem ON course_offerings(year, semester);
```
- DROP 블록에 `course_offerings`를 `courses`보다 먼저 추가(FK 역순).
- `schemas/rows.py`에 빌드 타임 모델 `OfferingRow(course_id: str, year: int, semester: Literal[1,2])` 추가.

## 2. `course_loader` (CSV) — 스텁 구현

```python
def load_courses_from_csv(
    csv_path: str, year: int, semester: int,
) -> tuple[list[CourseRow], list[WarningRow]]: ...
```
- 로드: `pd.read_csv(csv_path, encoding="utf-8-sig", header=0, dtype=str, keep_default_na=False)`. (기존 docstring의 `pd.read_html`(xls)에서 변경 — CSV는 헤더 행 존재, 데이터는 1행부터.)
- **28열 → `CourseRow` 위치 매핑.** 정확한 col→field 매핑은 구현 시 실제 헤더(이미 4파일 동일 확인)와 `app/parsers/course_xls.py.bak`(이전 xls 매핑 구현)을 참조해 확정한다. `year`/`semester`는 인자로 받아 채움(데이터 col0/col1과 교차검증 가능).
- 기존 헬퍼 유지 (시그니처 동일):
  - `_resolve_multi_sections(rows)` — 같은 course_id 여러 분반 → 첫 분반 채택, 불일치 시 `multi_section` warning.
  - `_classify_course_type(course_id, credit)` — `dummy`(course_id가 'DUM')/`special`(credit None, 비-DUM)/`regular`.
  - `_classify_is_general(department)` — `department == '전인교육원'` → 1.
  - `_flag_to_int(value)` — `'O'`→1, 빈값/NaN→0.
- 산출: 분반 통합 후 unique course_id 기준 `CourseRow` 리스트 + `WarningRow` 리스트. `linked_majors_parsed`는 None(remarks_parser가 빌드 후속 단계에서 채움).
- **테스트**: 기존 `tests/unit/parsers/test_course_loader.py`의 11개 skip 케이스를 un-skip + 구현(course_type 분류 4종, is_general 2종, flag_to_int 3종, multi_section 2종). xls→csv 함수명/스모크 케이스명 갱신.

## 3. `prereq_parser` (AND/OR 트리) — 스텁 구현

```python
def parse_prerequisites(
    course_id: str, description_raw: str | None,
) -> tuple[dict | None, list[WarningRow]]: ...   # dict = PrereqRow 입력
```
- `_extract_prereq_section(text)` — '선수과목' 키워드 이후 섹션 추출(없으면 None).
- `_tokenize(text)` — 과목코드(정규식 `[A-Z]{2,5}\d{3,4}[A-Z]?`) | `또는`/`or` | `,` | `(` | `)`.
- `_build_tree(tokens)` — 콤마=AND, `또는`/`or`=OR, 괄호=OR 그룹. 트리 JSON: leaf `{"type":"course","code":...}`, `{"type":"and","children":[...]}`, `{"type":"or","children":[...]}`. 괄호 비대칭 등은 `ValueError`.
- 반환: `PrereqRow`용 dict `{course_id, prereq_raw, prereq_tree_json}` 또는 None + warnings(매칭 실패·괄호 비대칭).
- **테스트**: 기존 `test_prereq_parser.py`의 9개 skip 케이스 un-skip + 구현(no-keyword, single, AND, OR 한/영, OR-group-in-paren 전/후, trailing alpha, 괄호비대칭 warning, regex no-match warning).

## 4. `build_course_db` 오케스트레이터 — 스텁 구현

`python scripts/build_course_db.py [--raw-dir DIR] [--db PATH]`. 오프라인 1회성(API 경로에서 호출 금지).

흐름:
1. `schema.sql` 실행 → 6테이블 DROP→CREATE. `PRAGMA foreign_keys = ON`.
2. `data/raw/개설교과목정보_*.csv`를 **연도-학기 오름차순** 정렬(파일명 `_YYYY-S`에서 year/semester 파싱).
3. **Phase 1 (학기별)**: 각 파일 → `load_courses_from_csv` → 각 `CourseRow`를 `courses`에 `INSERT OR REPLACE`(오름차순이라 최신이 덮어씀=latest-wins) + `course_offerings`에 `(course_id, year, semester)` INSERT. warning 수집.
4. **Phase 2 (최종 courses 1회)**: 확정된 각 course에 대해
   - `remarks_parser` → `UPDATE courses.linked_majors_parsed`
   - `prereq_parser`(description_raw) → `course_prerequisites` INSERT
   - `alias_parser`(description_raw + remarks_raw) → `course_aliases` INSERT
   - `restriction_parser`(restrictions_raw) → `course_restrictions` INSERT
   - 모든 warning 수집.
5. 수집한 warning 전부 `parse_warnings`에 INSERT.
6. `data/processed/s_compass_courses.db` 출력 + 요약 출력(테이블별 행수).

> Phase 2를 학기마다 반복하지 않는 이유: courses가 이미 latest-wins로 유일하므로, prereq/alias/restriction을 최종 1회만 돌려 중복 INSERT를 막는다.

## 5. 테스트

- **유닛**: `course_loader`(11) + `prereq_parser`(9) skip 케이스 un-skip + 구현(TDD).
- **통합** (`tests/integration/test_build_course_db.py`, 신규): 4개 실 CSV로 빌드 → ① `courses` 행수 = 고유 course_id 수(≈1,807), ② `course_offerings`에 다학기 중복 반영(≥ courses 행수, 중복 과목은 2+행), ③ 6테이블 모두 존재·채워짐, ④ FK 무결성(offerings/prereq/alias/restriction의 course_id가 courses에 존재). 실데이터 의존이라 integration 영역.

## 6. 범위 밖
- 추천 엔진의 학기 필터 *사용*(이 빌드는 데이터만 준비), 강의계획서 PDF 파싱(A3), 엔진/카드, `core/`(prereq_eval·alias_resolver·dept_normalizer) 평가 로직.

## 7. 문서 / 산출물
- `schema.sql` + `DATA_SCHEMA.md`에 `course_offerings` 추가, "6테이블"로 갱신.
- `OPEN_QUESTIONS.md`: 다학기 저장 결정(course_offerings) 기록 — "결정 완료"에 한 줄 추가.
- `s_compass_courses.db`는 gitignore(`data/processed/*`) — **커밋 안 함**. 코드·스키마·테스트만 커밋.

## 변경/구현 대상 파일 요약

| 파일 | 작업 |
|---|---|
| `app/db/schema.sql` | `course_offerings` 테이블 + DROP 순서 + 인덱스 추가 |
| `app/schemas/rows.py` | `OfferingRow` 추가 |
| `app/parsers/course_loader.py` | 스텁 → 구현 (CSV 로드 + 헬퍼) |
| `app/parsers/prereq_parser.py` | 스텁 → 구현 (AND/OR 트리) |
| `scripts/build_course_db.py` | 스텁 → 구현 (오케스트레이터) |
| `tests/unit/parsers/test_course_loader.py` | 11개 skip un-skip + csv 반영 |
| `tests/unit/parsers/test_prereq_parser.py` | 9개 skip un-skip |
| `tests/integration/test_build_course_db.py` | 신규 통합 테스트 |
| `docs/DATA_SCHEMA.md`, `docs/OPEN_QUESTIONS.md` | 갱신 |
