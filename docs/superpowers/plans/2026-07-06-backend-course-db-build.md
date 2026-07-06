# course DB 빌드 (4학기 CSV → s_compass_courses.db) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4개 학기(2024-2, 2025-1, 2025-2, 2026-1) 개설교과목 CSV를 1단계 산출물 `data/processed/s_compass_courses.db`(6테이블)로 빌드한다.

**Architecture:** 스펙 `docs/superpowers/specs/2026-06-30-course-db-build-design.md` 준수. `course_offerings` 테이블 신설(다학기 저장), `course_loader`(CSV)·`prereq_parser` 스텁 구현, `build_course_db` 오케스트레이터(Phase 1 학기별 적재 latest-wins → Phase 2 최종 courses 1회 파싱). 기존 파서 3종(`parse_aliases`/`parse_linked_majors`/`parse_restrictions`)은 그대로 조합만 한다.

**Tech Stack:** Python 3.12 + uv, pandas(CSV), raw sqlite3, pytest.

## Global Constraints

- 모든 명령은 `backend/` 디렉토리에서 실행 (`uv run ...`).
- 오프라인 1회성 빌드 — API 코드 경로에서 호출 금지, 런타임 재생성 금지 (CLAUDE.md).
- DB는 원문 보존. 파서/로더 로직에 자연어·평가 로직 금지 (`core/`는 이 플랜 범위 밖).
- CSV: `data/raw/개설교과목정보_{2024-2,2025-1,2025-2,2026-1}.csv`, 28열·헤더 4파일 동일·utf-8-sig.
- 실제 CSV 헤더(확인 완료): `학년도,학기,소속,학과,과목번호,분반,과목명,학점,수업시간/강의실,시간,교수진,수강생수,영어강의,중국어강의,승인과목,CU과목,HUSS과목,탐구공동체(CI)과목,홀짝구분,국제학생,Honors과목,공학인증,시험일자,수강대상,권장학년,수강신청 참조사항,과목 설명,비고`
- `data/processed/*.db`는 커밋 금지(gitignore). 코드·스키마·테스트·문서만 커밋.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- `frontend/` 및 `docs/API_SPEC.md` 수정 금지. docs 수정은 Task 6에 명시된 파일만.

---

### Task 1: `course_offerings` 스키마 + `OfferingRow`

**Files:**
- Modify: `backend/app/db/schema.sql`
- Modify: `backend/app/schemas/rows.py`
- Modify: `backend/app/schemas/__init__.py` (re-export 목록에 `OfferingRow` 추가 — 기존 export 패턴 확인 후 동일 스타일)

**Interfaces:**
- Produces: `OfferingRow(course_id: str, year: int, semester: Literal[1, 2])` — Task 4가 INSERT 직전 검증에 사용. 6테이블 스키마 — Task 5 통합 테스트가 검증.

- [x] **Step 1: schema.sql에 DROP + CREATE + 인덱스 추가**

DROP 블록 맨 위(기존 `DROP TABLE IF EXISTS course_restrictions;` 위)에 추가:

```sql
DROP TABLE IF EXISTS course_offerings;
```

`courses` CREATE 블록 바로 다음에 추가:

```sql
-- ============================================================
-- course_offerings : 학기별 개설 여부 (최소 컬럼, 다학기 저장)
--   courses 는 latest-wins 메타데이터 1행, 개설 이력은 여기에.
--   학기별 학점/분반 변동은 추적하지 않음 (YAGNI).
-- ============================================================
CREATE TABLE course_offerings (
    course_id  TEXT    NOT NULL,
    year       INTEGER NOT NULL,
    semester   INTEGER NOT NULL CHECK (semester IN (1, 2)),
    PRIMARY KEY (course_id, year, semester),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);
```

인덱스 블록에 추가:

```sql
CREATE INDEX idx_offerings_year_sem ON course_offerings(year, semester);
```

파일 헤더의 `-- 최종 갱신:` 날짜를 `2026-07-06`으로 갱신하고, "1단계 검토 후 추가 결정" 목록에 한 줄 추가: `--   course_offerings 신설 (4학기 다학기 저장, 2026-07-06).`

- [x] **Step 2: rows.py에 OfferingRow 추가**

`CourseRow` 클래스 뒤에 추가 (모듈 docstring의 "5테이블"은 "6테이블"로 갱신):

```python
class OfferingRow(BaseModel):
    """course_offerings 테이블 행."""

    model_config = ConfigDict(extra='forbid')

    course_id: str
    year: int = Field(..., ge=2000)
    semester: Literal[1, 2]
```

`app/schemas/__init__.py`의 re-export에 `OfferingRow` 추가.

- [x] **Step 3: 기존 테스트 회귀 확인**

Run: `uv run pytest tests/unit -q`
Expected: 기존 통과 테스트 전부 PASS (17개 수준), skip 다수 — 실패 0.

- [x] **Step 4: Commit**

```bash
git add app/db/schema.sql app/schemas/rows.py app/schemas/__init__.py
git commit -m "feat: course_offerings 테이블 + OfferingRow 추가 (다학기 저장)"
```

---

### Task 2: `course_loader` CSV 구현 (TDD)

**Files:**
- Modify: `backend/app/parsers/course_loader.py` (스텁 → 구현, `load_courses_from_xls` → `load_courses_from_csv` 개명)
- Test: `backend/tests/unit/parsers/test_course_loader.py` (11개 skip un-skip + smoke 케이스명 xls→csv 갱신)

**Interfaces:**
- Consumes: `CourseRow`, `WarningRow` (`app.schemas`).
- Produces: `load_courses_from_csv(csv_path: str, year: int, semester: int) -> tuple[list[CourseRow], list[WarningRow]]` — Task 4가 호출. `_resolve_multi_sections`는 컬럼 매핑 후 필드 dict 리스트(값은 str)를 받는다.

- [x] **Step 1: 테스트 11개 un-skip 작성**

`test_course_loader.py`에서 각 테스트의 `pytest.skip(...)`을 아래 본문으로 교체(기존 docstring 유지). 파일 상단에 헬퍼 추가:

```python
def _row(course_id="CSE1010", credit="3", **over):
    row = {
        "course_id": course_id,
        "course_name": "자료구조",
        "department": "컴퓨터공학과",
        "credit": credit,
        "target_year_raw": "전학년",
        "recommended_year_raw": "2-3학년",
        "is_english": "O",
        "is_cu": "",
        "is_huss": "",
        "is_ci": "",
        "is_honors": "",
        "restrictions_raw": "",
        "description_raw": "",
        "remarks_raw": "",
    }
    row.update(over)
    return row
```

테스트 본문:

```python
def test_classify_course_type_dummy():
    assert course_loader._classify_course_type("DUMEX01", None) == "dummy"

def test_classify_course_type_special():
    assert course_loader._classify_course_type("AII1001", None) == "special"

def test_classify_course_type_regular_normal():
    assert course_loader._classify_course_type("CSE1010", 3.0) == "regular"

def test_classify_course_type_regular_credit_none_not_special():
    assert course_loader._classify_course_type("ABC9999", None) == "special"

def test_classify_is_general_yes():
    assert course_loader._classify_is_general("전인교육원") == 1

def test_classify_is_general_no():
    assert course_loader._classify_is_general("컴퓨터공학과") == 0

def test_flag_to_int_o():
    assert course_loader._flag_to_int("O") == 1

def test_flag_to_int_empty():
    assert course_loader._flag_to_int("") == 0

def test_flag_to_int_nan():
    assert course_loader._flag_to_int(float("nan")) == 0

def test_resolve_multi_sections_consistent():
    unique, warnings = course_loader._resolve_multi_sections([_row(), _row(), _row()])
    assert len(unique) == 1
    assert warnings == []

def test_resolve_multi_sections_inconsistent_credit():
    unique, warnings = course_loader._resolve_multi_sections([_row(credit="3"), _row(credit="2")])
    assert len(unique) == 1
    assert unique[0]["credit"] == "3"
    assert len(warnings) == 1
    assert warnings[0].field == "multi_section"
    assert warnings[0].severity == "warning"
```

smoke 케이스는 `test_load_courses_from_csv_smoke`로 개명, skip 유지(integration 영역).

- [x] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/parsers/test_course_loader.py -v`
Expected: 11개 FAIL (NotImplementedError), smoke 1개 SKIP.

- [x] **Step 3: 구현**

`course_loader.py` 전체를 다음으로 교체(모듈 docstring은 기존 내용을 CSV 기준으로 갱신 — xls/read_html 언급 제거):

```python
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.schemas import CourseRow, WarningRow

# CSV 헤더(4개 파일 동일 확인) → CourseRow 필드 매핑. 미사용 컬럼은 버린다.
_FIELD_BY_COL: Dict[str, str] = {
    "학과": "department",
    "과목번호": "course_id",
    "과목명": "course_name",
    "학점": "credit",
    "수강대상": "target_year_raw",
    "권장학년": "recommended_year_raw",
    "영어강의": "is_english",
    "CU과목": "is_cu",
    "HUSS과목": "is_huss",
    "탐구공동체(CI)과목": "is_ci",
    "Honors과목": "is_honors",
    "수강신청 참조사항": "restrictions_raw",
    "과목 설명": "description_raw",
    "비고": "remarks_raw",
}


def load_courses_from_csv(
    csv_path: str,
    year: int,
    semester: int,
) -> Tuple[List[CourseRow], List[WarningRow]]:
    df = pd.read_csv(
        csv_path, encoding="utf-8-sig", header=0, dtype=str, keep_default_na=False
    )
    missing = set(_FIELD_BY_COL) - set(df.columns)
    if missing:
        raise ValueError(f"컬럼 구조가 예상과 다름 — 누락: {sorted(missing)}")

    mapped = [
        {field: str(rec[col]).strip() for col, field in _FIELD_BY_COL.items()}
        for rec in df.to_dict(orient="records")
    ]
    unique_rows, warnings = _resolve_multi_sections(mapped)

    courses: List[CourseRow] = []
    for row in unique_rows:
        credit = float(row["credit"]) if row["credit"] else None
        courses.append(
            CourseRow(
                course_id=row["course_id"],
                course_name=row["course_name"],
                department=row["department"],
                credit=credit,
                year=year,
                semester=semester,
                target_year_raw=row["target_year_raw"] or None,
                recommended_year_raw=row["recommended_year_raw"] or None,
                is_english=_flag_to_int(row["is_english"]),
                is_cu=_flag_to_int(row["is_cu"]),
                is_huss=_flag_to_int(row["is_huss"]),
                is_ci=_flag_to_int(row["is_ci"]),
                is_honors=_flag_to_int(row["is_honors"]),
                course_type=_classify_course_type(row["course_id"], credit),
                is_general=_classify_is_general(row["department"]),
                description_raw=row["description_raw"] or None,
                restrictions_raw=row["restrictions_raw"] or None,
                remarks_raw=row["remarks_raw"] or None,
                linked_majors_parsed=None,
            )
        )
    return courses, warnings


def _resolve_multi_sections(
    rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[WarningRow]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    warnings: List[WarningRow] = []
    for row in rows:
        first = by_id.get(row["course_id"])
        if first is None:
            by_id[row["course_id"]] = row
            continue
        diff = [k for k in first if k != "course_id" and first[k] != row[k]]
        if diff:
            warnings.append(
                WarningRow(
                    course_id=row["course_id"],
                    field="multi_section",
                    severity="warning",
                    issue=f"분반 간 값 불일치: {', '.join(sorted(diff))}",
                    raw_text=None,
                )
            )
    return list(by_id.values()), warnings


def _classify_course_type(course_id: str, credit: Optional[float]) -> str:
    if course_id.startswith("DUM"):
        return "dummy"
    if credit is None:
        return "special"
    return "regular"


def _classify_is_general(department: str) -> int:
    return 1 if department == "전인교육원" else 0


def _flag_to_int(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.strip() == "O" else 0
    return 0
```

각 함수의 기존 docstring(Args/Returns)은 유지·갱신해서 붙인다.

- [x] **Step 4: 통과 확인**

Run: `uv run pytest tests/unit/parsers/test_course_loader.py -v`
Expected: 11 PASS, 1 SKIP.

- [x] **Step 5: 매핑 검증 (수강신청 참조사항 = restrictions_raw 확인)**

Run:
```bash
uv run python -c "import pandas as pd; df = pd.read_csv('data/raw/개설교과목정보_2026-1.csv', encoding='utf-8-sig', dtype=str, keep_default_na=False); s = df['수강신청 참조사항']; print(s[s != ''].head(10).to_list())"
```
Expected: 학과별 수강제한 문구(예: '...학과 수강불가/수강가능' 류)가 보임 → `restriction_parser` 4패턴 대상 원문 맞음. 다른 성격의 텍스트만 보이면 STOP — 매핑 재검토 후 보고.

- [x] **Step 6: Commit**

```bash
git add app/parsers/course_loader.py tests/unit/parsers/test_course_loader.py
git commit -m "feat: course_loader CSV 구현 (분반 통합·분류·플래그)"
```

---

### Task 3: `prereq_parser` AND/OR 트리 구현 (TDD)

**Files:**
- Modify: `backend/app/parsers/prereq_parser.py`
- Test: `backend/tests/unit/parsers/test_prereq_parser.py` (10개 skip 전부 un-skip)

**Interfaces:**
- Produces: `parse_prerequisites(course_id: str, description_raw: Optional[str]) -> tuple[Optional[dict], list[WarningRow]]` — dict 키는 `{course_id, prereq_raw, prereq_tree_json}`. Task 4가 호출.

- [x] **Step 1: 테스트 10개 un-skip 작성**

각 테스트의 `pytest.skip(...)`을 교체. 트리 검증은 `json.loads(record["prereq_tree_json"])` 후 비교. 파일 상단에 `import json` 추가:

```python
def test_no_prereq_keyword():
    record, warnings = prereq_parser.parse_prerequisites(
        "CSE2000", "이 과목은 선형대수의 응용을 다룬다."
    )
    assert record is None
    assert warnings == []

def test_single_course():
    record, _ = prereq_parser.parse_prerequisites("CSE2000", "선수과목: CSE1010")
    assert json.loads(record["prereq_tree_json"]) == {"type": "course", "code": "CSE1010"}

def test_and_two_courses():
    record, _ = prereq_parser.parse_prerequisites("CSE2000", "선수과목: CSE1010, CSE1020")
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "and",
        "children": [
            {"type": "course", "code": "CSE1010"},
            {"type": "course", "code": "CSE1020"},
        ],
    }

def test_or_two_courses_korean():
    record, _ = prereq_parser.parse_prerequisites("CSE2000", "선수과목: CSE1010 또는 CSE1020")
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "or",
        "children": [
            {"type": "course", "code": "CSE1010"},
            {"type": "course", "code": "CSE1020"},
        ],
    }

def test_or_two_courses_english():
    record, _ = prereq_parser.parse_prerequisites("CSE2000", "선수과목: CSE1010 or CSE1020")
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "or",
        "children": [
            {"type": "course", "code": "CSE1010"},
            {"type": "course", "code": "CSE1020"},
        ],
    }

def test_or_group_in_paren_then_and():
    record, _ = prereq_parser.parse_prerequisites(
        "CSE2000", "선수과목: (CSE1010 또는 CSE1020), MAT2001"
    )
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "and",
        "children": [
            {"type": "or", "children": [
                {"type": "course", "code": "CSE1010"},
                {"type": "course", "code": "CSE1020"},
            ]},
            {"type": "course", "code": "MAT2001"},
        ],
    }

def test_trailing_alpha():
    record, _ = prereq_parser.parse_prerequisites("LING2001", "선수과목: LING1001A")
    assert json.loads(record["prereq_tree_json"]) == {"type": "course", "code": "LING1001A"}

def test_unbalanced_paren_warning():
    record, warnings = prereq_parser.parse_prerequisites(
        "CSE2000", "선수과목: (CSE1010, MAT2001"
    )
    assert record is None
    assert len(warnings) == 1
    assert warnings[0].severity == "error"

def test_regex_no_match_warning():
    record, warnings = prereq_parser.parse_prerequisites(
        "CSE2000", "선수과목: 자료구조와 알고리즘"
    )
    assert record is None
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"

def test_or_group_in_paren_after_and():
    record, _ = prereq_parser.parse_prerequisites(
        "ECO3000", "선수과목: ECO2001, ECO2003(또는 STS2005 또는 STS2006)"
    )
    assert json.loads(record["prereq_tree_json"]) == {
        "type": "and",
        "children": [
            {"type": "course", "code": "ECO2001"},
            {"type": "or", "children": [
                {"type": "course", "code": "ECO2003"},
                {"type": "course", "code": "STS2005"},
                {"type": "course", "code": "STS2006"},
            ]},
        ],
    }
```

- [x] **Step 2: 실패 확인**

Run: `uv run pytest tests/unit/parsers/test_prereq_parser.py -v`
Expected: 10개 FAIL (NotImplementedError).

- [x] **Step 3: 구현**

`prereq_parser.py` 구현(기존 모듈/함수 docstring 유지, import에 `json`, `re` 추가):

```python
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas import WarningRow

_KEYWORD = "선수과목"
_CODE_RE = re.compile(r"[A-Z]{2,5}\d{3,4}[A-Z]?")
_TOKEN_RE = re.compile(r"[A-Z]{2,5}\d{3,4}[A-Z]?|또는|\bor\b|,|\(|\)")
_OR_WORDS = {"또는", "or"}


def parse_prerequisites(
    course_id: str,
    description_raw: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], List[WarningRow]]:
    if not description_raw:
        return None, []
    section = _extract_prereq_section(description_raw)
    if section is None:
        return None, []
    tokens = _tokenize(section)
    if not any(_CODE_RE.fullmatch(t) for t in tokens):
        return None, [
            WarningRow(
                course_id=course_id,
                field="prerequisites",
                severity="warning",
                issue="선수과목 키워드 존재하나 과목 코드 매칭 0건",
                raw_text=section,
            )
        ]
    try:
        tree = _build_tree(tokens)
    except ValueError as exc:
        return None, [
            WarningRow(
                course_id=course_id,
                field="prerequisites",
                severity="error",
                issue=str(exc),
                raw_text=section,
            )
        ]
    record = {
        "course_id": course_id,
        "prereq_raw": section,
        "prereq_tree_json": json.dumps(tree, ensure_ascii=False),
    }
    return record, []


def _extract_prereq_section(text: str) -> Optional[str]:
    idx = text.find(_KEYWORD)
    if idx == -1:
        return None
    return text[idx:]


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text)


def _build_tree(tokens: List[str]) -> Dict[str, Any]:
    segments = _split_top_level(tokens)
    children = [_parse_segment(seg) for seg in segments if seg]
    if not children:
        raise ValueError("파싱 가능한 선수과목 토큰 없음")
    if len(children) == 1:
        return children[0]
    return {"type": "and", "children": children}


def _split_top_level(tokens: List[str]) -> List[List[str]]:
    """괄호 깊이 0의 콤마로 분할. 괄호 비대칭이면 ValueError."""
    segments: List[List[str]] = []
    current: List[str] = []
    depth = 0
    for tok in tokens:
        if tok == "(":
            depth += 1
        elif tok == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("괄호 비대칭: 닫는 괄호 초과")
        if tok == "," and depth == 0:
            segments.append(current)
            current = []
        else:
            current.append(tok)
    if depth != 0:
        raise ValueError("괄호 비대칭: 여는 괄호 미닫힘")
    segments.append(current)
    return segments


def _collect_group(tokens: List[str], i: int) -> Tuple[List[str], int]:
    """tokens[i] == '(' 전제. 매칭 ')'까지 내부 토큰과 다음 인덱스 반환."""
    depth = 1
    j = i + 1
    while j < len(tokens):
        if tokens[j] == "(":
            depth += 1
        elif tokens[j] == ")":
            depth -= 1
            if depth == 0:
                return tokens[i + 1 : j], j + 1
        j += 1
    raise ValueError("괄호 비대칭: 여는 괄호 미닫힘")


def _parse_segment(tokens: List[str]) -> Dict[str, Any]:
    """콤마 없는 구간 파싱. '또는'/'or' 연결 → OR.

    'B(또는 C ...)' 처럼 괄호 내용이 OR 접속사로 시작하면
    직전 노드를 OR 그룹의 첫 원소로 끌어들인다 (테스트 케이스 기준).
    """
    items: List[Dict[str, Any]] = []
    or_seen = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _OR_WORDS:
            or_seen = True
            i += 1
        elif tok == "(":
            inner, i = _collect_group(tokens, i)
            if inner and inner[0] in _OR_WORDS and items:
                prev = items.pop()
                group = _parse_segment(inner)
                members = (
                    group["children"] if group.get("type") == "or" else [group]
                )
                items.append({"type": "or", "children": [prev, *members]})
            else:
                items.append(_parse_segment(inner))
        elif tok == ")":
            raise ValueError("괄호 비대칭: 닫는 괄호 초과")
        else:
            items.append({"type": "course", "code": tok})
            i += 1
    if not items:
        raise ValueError("빈 괄호 그룹")
    if or_seen and len(items) > 1:
        return {"type": "or", "children": items}
    if len(items) == 1:
        return items[0]
    return {"type": "and", "children": items}
```

- [x] **Step 4: 통과 확인**

Run: `uv run pytest tests/unit/parsers/test_prereq_parser.py -v`
Expected: 10 PASS.

- [x] **Step 5: 전체 유닛 회귀**

Run: `uv run pytest tests/unit -q`
Expected: 실패 0.

- [x] **Step 6: Commit**

```bash
git add app/parsers/prereq_parser.py tests/unit/parsers/test_prereq_parser.py
git commit -m "feat: prereq_parser AND/OR 트리 구현"
```

---

### Task 4: `build_course_db` 오케스트레이터

**Files:**
- Modify: `backend/scripts/build_course_db.py` (스텁 → 구현)

**Interfaces:**
- Consumes: `load_courses_from_csv`(Task 2), `parse_prerequisites`(Task 3), `parse_aliases(new_course_id, source_text)`, `parse_linked_majors(course_id, remarks_raw)`, `parse_restrictions(course_id, restrictions_raw)`, `OfferingRow`(Task 1), `config.RAW_DIR`/`config.DB_PATH`/`config.BASE_DIR`.
- Produces: `data/processed/s_compass_courses.db` (6테이블) + 테이블별 행수 요약 출력.

- [x] **Step 1: 구현**

`scripts/build_course_db.py` 전체 교체(모듈 docstring은 기존 유지하되 xls→CSV·6테이블·usage 갱신):

```python
import argparse
import re
import sqlite3
from pathlib import Path

from app import config
from app.parsers.alias_parser import parse_aliases
from app.parsers.course_loader import load_courses_from_csv
from app.parsers.prereq_parser import parse_prerequisites
from app.parsers.remarks_parser import parse_linked_majors
from app.parsers.restriction_parser import parse_restrictions
from app.schemas import CourseRow, OfferingRow, WarningRow

SCHEMA_PATH = config.BASE_DIR / "app" / "db" / "schema.sql"
TABLES = (
    "courses", "course_offerings", "course_prerequisites",
    "course_aliases", "course_restrictions", "parse_warnings",
)
_CSV_NAME_RE = re.compile(r"개설교과목정보_(\d{4})-([12])\.csv$")

_COURSE_FIELDS = list(CourseRow.model_fields)
_INSERT_COURSE = (
    f"INSERT OR REPLACE INTO courses ({', '.join(_COURSE_FIELDS)}) "
    f"VALUES ({', '.join(':' + f for f in _COURSE_FIELDS)})"
)


def _find_csvs(raw_dir: Path) -> list[tuple[int, int, Path]]:
    """파일명에서 (year, semester) 파싱 후 연도-학기 오름차순 정렬."""
    found = []
    for path in raw_dir.glob("개설교과목정보_*.csv"):
        m = _CSV_NAME_RE.search(path.name)
        if m:
            found.append((int(m.group(1)), int(m.group(2)), path))
    return sorted(found)


def main() -> None:
    parser = argparse.ArgumentParser(description="4학기 CSV → s_compass_courses.db")
    parser.add_argument("--raw-dir", type=Path, default=config.RAW_DIR)
    parser.add_argument("--db", type=Path, default=config.DB_PATH)
    args = parser.parse_args()

    csvs = _find_csvs(args.raw_dir)
    if not csvs:
        raise SystemExit(f"개설교과목정보_*.csv 없음: {args.raw_dir}")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(args.db)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    warnings: list[WarningRow] = []

    # Phase 1 — 학기별 적재. 오름차순이라 최신 학기가 덮어씀 = latest-wins.
    for year, semester, path in csvs:
        courses, load_warnings = load_courses_from_csv(str(path), year, semester)
        warnings.extend(load_warnings)
        for course in courses:
            con.execute(_INSERT_COURSE, course.model_dump())
            offering = OfferingRow(course_id=course.course_id, year=year, semester=semester)
            con.execute(
                "INSERT INTO course_offerings (course_id, year, semester) "
                "VALUES (:course_id, :year, :semester)",
                offering.model_dump(),
            )
        print(f"{path.name}: courses {len(courses)}건 적재")

    # Phase 2 — 확정된 courses 1회 순회 (학기 반복 시 중복 INSERT 되므로 금지).
    final_rows = con.execute(
        "SELECT course_id, description_raw, restrictions_raw, remarks_raw FROM courses"
    ).fetchall()
    for course_id, description_raw, restrictions_raw, remarks_raw in final_rows:
        linked_json, w = parse_linked_majors(course_id, remarks_raw)
        warnings.extend(w)
        if linked_json is not None:
            con.execute(
                "UPDATE courses SET linked_majors_parsed = ? WHERE course_id = ?",
                (linked_json, course_id),
            )

        prereq_record, w = parse_prerequisites(course_id, description_raw)
        warnings.extend(w)
        if prereq_record is not None:
            con.execute(
                "INSERT INTO course_prerequisites "
                "(course_id, prereq_raw, prereq_tree_json) "
                "VALUES (:course_id, :prereq_raw, :prereq_tree_json)",
                prereq_record,
            )

        for source_text in (description_raw, remarks_raw):
            aliases, w = parse_aliases(course_id, source_text)
            warnings.extend(w)
            for alias in aliases:
                con.execute(
                    "INSERT INTO course_aliases "
                    "(new_course_id, old_course_id, old_course_name, "
                    "source_type, condition_raw, raw_text) "
                    "VALUES (:new_course_id, :old_course_id, :old_course_name, "
                    ":source_type, :condition_raw, :raw_text)",
                    alias.model_dump(),
                )

        restrictions, w = parse_restrictions(course_id, restrictions_raw)
        warnings.extend(w)
        for restriction in restrictions:
            con.execute(
                "INSERT INTO course_restrictions "
                "(course_id, target_dept, status, raw_text) "
                "VALUES (:course_id, :target_dept, :status, :raw_text)",
                restriction.model_dump(),
            )

    for warning in warnings:
        con.execute(
            "INSERT INTO parse_warnings (course_id, field, severity, issue, raw_text) "
            "VALUES (:course_id, :field, :severity, :issue, :raw_text)",
            warning.model_dump(),
        )

    con.commit()

    print(f"\n빌드 완료: {args.db}")
    for table in TABLES:
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n}행")
    con.close()


if __name__ == "__main__":
    main()
```

- [x] **Step 2: 실제 빌드 실행**

Run: `uv run python scripts/build_course_db.py`
Expected: 4개 CSV 각각 적재 로그 + `빌드 완료` + 6테이블 행수 출력. `courses` ≈ 1,807, `course_offerings` > `courses`. 예외 발생 시(예: 학점 컬럼 비수치 문자열) 원인 파악 후 최소 수정 — 원인·수정 내용을 완료 보고에 포함.

- [x] **Step 3: Commit**

```bash
git add scripts/build_course_db.py
git commit -m "feat: build_course_db 오케스트레이터 구현 (4학기 CSV, 6테이블)"
```

---

### Task 5: 통합 테스트

**Files:**
- Create: `backend/tests/integration/test_build_course_db.py`

**Interfaces:**
- Consumes: 실 CSV 4개(`data/raw/`), `scripts/build_course_db.py` CLI.

- [x] **Step 1: 통합 테스트 작성**

```python
"""4개 실 CSV → s_compass_courses.db 빌드 통합 검증 (스펙 §5).

실데이터(data/raw) 의존. 파일 없으면 skip.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BACKEND_DIR / "data" / "raw"
EXPECTED_CSVS = [
    "개설교과목정보_2024-2.csv",
    "개설교과목정보_2025-1.csv",
    "개설교과목정보_2025-2.csv",
    "개설교과목정보_2026-1.csv",
]
TABLES = [
    "courses", "course_offerings", "course_prerequisites",
    "course_aliases", "course_restrictions", "parse_warnings",
]


@pytest.fixture(scope="module")
def built_db(tmp_path_factory):
    if not all((RAW_DIR / name).exists() for name in EXPECTED_CSVS):
        pytest.skip("data/raw 실 CSV 4개 필요")
    db_path = tmp_path_factory.mktemp("build") / "s_compass_courses.db"
    subprocess.run(
        [sys.executable, str(BACKEND_DIR / "scripts" / "build_course_db.py"),
         "--db", str(db_path)],
        check=True,
        cwd=BACKEND_DIR,
    )
    con = sqlite3.connect(db_path)
    yield con
    con.close()


def test_courses_unique_course_id(built_db):
    """① courses 행수 = 고유 course_id 수 (≈1,807)."""
    n_courses = built_db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    n_ids = built_db.execute(
        "SELECT COUNT(DISTINCT course_id) FROM course_offerings"
    ).fetchone()[0]
    assert n_courses == n_ids
    assert 1500 <= n_courses <= 2200


def test_offerings_reflect_multi_semester(built_db):
    """② 다학기 중복 반영 — 2개 학기 이상 과목 다수(분석상 1,039개)."""
    n_courses = built_db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    n_offerings = built_db.execute(
        "SELECT COUNT(*) FROM course_offerings"
    ).fetchone()[0]
    assert n_offerings > n_courses
    multi = built_db.execute(
        "SELECT COUNT(*) FROM (SELECT course_id FROM course_offerings "
        "GROUP BY course_id HAVING COUNT(*) >= 2)"
    ).fetchone()[0]
    assert multi >= 900


def test_all_six_tables_populated(built_db):
    """③ 6테이블 모두 존재·채워짐."""
    for table in TABLES:
        n = built_db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert n > 0, table


def test_fk_integrity(built_db):
    """④ offerings/prereq/alias/restriction 의 course_id 가 courses 에 존재."""
    for table in ("course_offerings", "course_prerequisites", "course_restrictions"):
        orphans = built_db.execute(
            f"SELECT COUNT(*) FROM {table} t "
            "LEFT JOIN courses c ON c.course_id = t.course_id "
            "WHERE c.course_id IS NULL"
        ).fetchone()[0]
        assert orphans == 0, table
    orphans = built_db.execute(
        "SELECT COUNT(*) FROM course_aliases a "
        "LEFT JOIN courses c ON c.course_id = a.new_course_id "
        "WHERE c.course_id IS NULL"
    ).fetchone()[0]
    assert orphans == 0
```

- [x] **Step 2: 실행**

Run: `uv run pytest tests/integration/test_build_course_db.py -v`
Expected: 4 PASS (수 분 소요 가능). 실패 시 원인 규명 — 기대 범위가 실데이터와 다르면 실측값 기준으로 상수 조정하고 근거를 완료 보고에 기록.

- [x] **Step 3: 전체 테스트**

Run: `uv run pytest tests/unit tests/integration -q`
Expected: 실패 0.

- [x] **Step 4: Commit**

```bash
git add tests/integration/test_build_course_db.py
git commit -m "test: course DB 빌드 통합 테스트 (4학기 실 CSV)"
```

---

### Task 6: 문서 갱신

**Files:**
- Modify: `docs/DATA_SCHEMA.md` — `course_offerings` 섹션 추가(위 DDL 그대로), "5테이블" 표기를 "6테이블"로.
- Modify: `docs/OPEN_QUESTIONS.md` — "결정 완료" 섹션에 한 줄 추가: `- **다학기 저장** → course_offerings 테이블 신설 (courses 는 latest-wins 1행, 개설 이력 분리). 6테이블.`
- Modify: `docs/ARCHITECTURE.md` — "1단계 산출물 스키마" 섹션의 "5테이블"을 "6테이블"로, 목록에 `course_offerings — 학기별 개설 이력` 한 줄 추가.
- Modify: `backend/README.md` — "5테이블 + 인덱스"를 "6테이블 + 인덱스"로, 빌드 명령의 "(예정)" 제거 + 입력을 4학기 CSV로 갱신.

**Interfaces:** 없음 (문서만).

- [x] **Step 1: 위 4개 파일 갱신** (스키마 변경에서 파생된 표기만 수정 — 그 외 내용 변경 금지)

- [x] **Step 2: Commit**

```bash
git add docs/DATA_SCHEMA.md docs/OPEN_QUESTIONS.md docs/ARCHITECTURE.md backend/README.md
git commit -m "docs: course_offerings 반영 — 6테이블 갱신 + 다학기 저장 결정 기록"
```

---

## 완료 기준

- `uv run pytest tests/unit tests/integration` 전체 통과 (skip 제외 실패 0).
- `uv run python scripts/build_course_db.py` 성공, `courses` ≈ 1,807행, `course_offerings` ≥ 2,800행 수준.
- `data/processed/s_compass_courses.db` 미커밋 확인 (`git status`에 안 나옴 — gitignore).
