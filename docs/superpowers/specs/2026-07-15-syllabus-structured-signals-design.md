# 강의계획서 구조화 신호 재설계 — 개요 경계 + 발표 신호

**목표:** 강의계획서에서 자유서술 개요를 과다 저장하지 않고, 실제 추천에 쓰는 구조화 신호만 보관한다. 발표 유무를 신규 활성 선호 신호로 추가한다.

**배경:** 현재 `course_syllabi.overview_text`가 개요 종료 경계를 못 만나면 문서 끝까지 캡처(LLA1020 9,618자). 발표 데이터는 파서가 이미 뽑지만(`evaluation.presentation`, `course_format` 발표 %) 저장·사용하지 않는다.

## 확정 결정 (브레인스토밍 Q&A)

1. **개요**: 폐기하지 않고 **짧게 보관** — 경계 수정 + 하드 캡. "콘텐츠 유사도" 신호 입력으로 계속 사용.
2. **발표**: **활성 선호 신호로 추가** — "발표 있는 과목 선호"(팀플과 같은 원함 방향). "사용자 선호 매칭" 신호에 반영.
3. **발표 저장값**: **성적 발표 배점 비율 `presentation_ratio` (0~1)** — 출석과 동일한 실수 형태.

## 스키마 변경 — `course_syllabi`

```
현재: (course_id, overview_text, team_project, attendance_ratio, source_file)
변경: (course_id, overview_text, team_project, attendance_ratio, presentation_ratio, source_file)
```

- `overview_text`: 값 자체를 짧게 저장(파서에서 바운드).
- `presentation_ratio REAL`: 신규. 성적 발표 배점 / 100 (0~1).
- 선수과목은 별도 `course_prerequisites` 테이블 — 여기 미포함.
- gitignore 산출물 DB → 스키마 갱신 후 재파싱·재병합(마이그레이션 불필요).

## 파서 변경 — `backend/scripts/syllabus_parser.py`

**1. `extract_overview` 바운드** — 과다캡처 차단.
- 추출 후 **하드 캡 500자**로 잘라 반환(종료 경계 미매칭 시 안전망). 종료 패턴 자체는 유지.
- 기준: 캡 길이는 개요 1~2문단을 담기 충분하되 다음 섹션 유입을 막는 값.

**2. `presentation_ratio` 산출** — `parse_syllabus` 출력 dict에 추가.
- `presentation_ratio = round(evaluation.get("presentation", 0) / 100, 2)` (성적 발표 배점 비율).
- 발표 배점이 없으면 0.0. (수업방법 표의 발표 %는 보조 지표라 이번 범위에선 미사용 — 성적 배점이 "발표로 평가받는가"의 명확한 지표.)

## 신호 변경

**`backend/app/engines/recommender/preference.py`**
- `_presentation(ratio: float) -> float`: `ratio >= 0.20 → 100`, `ratio > 0 → 50`, `else → 0`. (팀플·출석 티어와 동형.)
- `score(prefer_team_project, prefer_low_attendance, prefer_presentation, attrs_by_id)`: `prefer_presentation` 파라미터 추가. 가드(`if not (...)`)와 파트 평균에 발표 포함. `attrs`에서 `a["presentation_ratio"]` 사용.

**`backend/app/cards/card_a.py`**
- `preference.score(student.prefer_team_project, student.prefer_low_attendance, student.prefer_presentation, pool_attrs)`.

## 입력 계약

**`backend/app/schemas/input.py`**: `prefer_presentation: bool = False` 추가 (설명: 발표 있는 과목 선호 — 선호 매칭 요인).

**프론트**
- `frontend/src/types/api.ts`: `StudentInput`에 `prefer_presentation: boolean`.
- `frontend/src/components/InputScreen.tsx`: PREFS 체크박스 1개 추가.
- `frontend/src/lib/useAnalysis.ts`: `buildStudentInput`에 `prefer_presentation` 전달.

## 병합 — `backend/scripts/build_syllabus_prereqs.py`

- `merge_syllabus_attrs`의 DDL(`_SYLLABI_DDL`)에 `presentation_ratio REAL` 추가.
- `INSERT OR REPLACE` 컬럼·값에 `presentation_ratio` 추가: `round(float(rec.get("presentation_ratio") or 0.0), 2)`.

## 쿼리 — `backend/app/db/queries/course_queries.py`

- `syllabus_attrs`는 `SELECT *`라 신규 컬럼 자동 포함 — 변경 없음.

## 재빌드 절차

1. `schema.sql`의 `course_syllabi` DDL에 `presentation_ratio` 추가.
2. 재파싱: `syllabus_parser.py --input_dir raw/syllabi/extracted --output processed/syllabi_parsed.json`.
3. course_syllabi 재생성(DROP 후) + 재병합: `build_syllabus_prereqs.py --input processed/syllabi_parsed.json`.

## 테스트

- `preference.py`: 발표 티어(0/0.1/0.2/0.3) + 다중 선호 평균 단위 테스트 (`tests/unit/test_preference.py` 신규 또는 확장).
- 파서: `extract_overview` 길이 캡 단위 테스트(과다 입력 → ≤500자).
- 회귀: 기존 `test_scoring`·card_a 스모크 통과.

## 범위 밖 (YAGNI)

- 수업방법 표 발표 %(시간 비중) 통합, 발표 기피/양방향 선택, S/U 선호 활성화.
