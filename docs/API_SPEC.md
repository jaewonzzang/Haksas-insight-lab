# API Spec

> 단일 진실원: [`backend/app/schemas/`](../backend/app/schemas/). 이 문서는 사람용 요약이다.

## `POST /analyze`

학생 입력 1회 → 카드 A/C/D 통합 dashboard 응답.

### Request
`StudentInput` (`backend/app/schemas/input.py`)

| 필드 | 타입 | 비고 |
|---|---|---|
| `student_id` | string | 학번 |
| `department` | string | 학과/학부 원문 |
| `extra_majors` | string[] | 복수전공 학과/학부 원문 (기본 `[]`) |
| `taken_course_ids` | string[] | 이수 완료 과목 ID |
| `interest_career` | string \| null | 관심 진로 (드롭다운) |
| `consider_multimajor` | bool | 다전공 고려 여부 |

> 공통선택 4영역 / 자유선택 9영역 / 팀플·S·U·출석 비중 필드는 UI 폼 확정 후 추가 예정.

### Response
`DashboardResponse` (`backend/app/schemas/cards.py`)

```
{
  profile: { name, department, year, analysis_date, report_semester, next_semester },
  kpi: { earned_credits, gpa, gpa_scale, similar_alumni_n },
  card_a: { major: RecommendedCourse[], general: RecommendedCourse[], candidates: RecommendedCourse[] },
  card_c: { cohort_label, entries: PathwayEntry[], baseline_note },
  card_d: { similar_label, sample_size, entries: CareerEntry[], sub_title, sub_chips, pattern_summary },
  cluster: { factors, common_courses, career_patterns, summary }
}
```

각 타입 상세는 `cards.py` 참조.

## 기타 라우트 (디버그/내부)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/health` | liveness |
| `GET` | `/courses/{course_id}` | 디버그용 과목 단건 조회. 외부 노출 X. |

## 프론트 동기화

`frontend/src/types/api.ts` 가 위 schemas 의 미러. 변경 시 함께 갱신 (수동 또는 codegen — `OPEN_QUESTIONS.md` A12).

CORS: Vite dev 서버(localhost:5173) 허용 — app/main.py.
