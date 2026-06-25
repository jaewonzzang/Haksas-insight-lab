# 프론트 배선 구조 (데이터 없이) — 설계

날짜: 2026-06-24 · 범위: `frontend/` · 백엔드 실데이터 없이 가능한 구조 우선.

## 목표

학사팀 실데이터 수령 전, 프론트가 **mock 데이터로 입력→대시보드 흐름을 끝까지** 도는 구조를 만든다.
시각 폴리시는 최소 (배선 우선). 백엔드 준비 시 재배선 없이 토글만으로 전환.

## 결정 (브레인스토밍 합의)

1. **범위** = 배선(구조) 우선. mock 레이어 + 상태 흐름 + 렌더 4상태 + 모든 컴포넌트 props 전환. 시각 최소.
2. **mock 공급** = `lib/api.ts` 토글. `analyze()`가 mock fixture 반환. 새 의존성 0. 기존 fetch 경로 보존.
   - 토글: `VITE_USE_MOCK` 명시 시 그 값, 아니면 dev=mock / prod=real (`import.meta.env.DEV`).
3. **진입 흐름** = InputForm이 `StudentInput` 수집 → `analyze()` 트리거 → 상태 → 카드 렌더.
4. **이수내역** = 텍스트 입력 ❌. 사용자 실제 수강 과목(34과목)을 예시 fixture로 사용, 처리 플로우(수집→제출) 유지, 추후 SAINT 실데이터로 교체.
5. **WhyPanel** = 카드 껍데기만, 내용 빈 공간으로 방치. 데이터 출처 미정 → `OPEN_QUESTIONS.md` A13 등록.

## 데이터 흐름

```
InputForm(onSubmit) → useDashboard.run(input)
  status: idle → loading → success | error
  data: DashboardResponse | null
Dashboard가 data.kpi / card_a / card_c / card_d 를 props 주입
```

## 파일

신규:
- `src/mock/takenCourses.fixture.ts` — 예시 이수 과목 34개 `{id,name}[]` (교체 대상)
- `src/mock/dashboard.fixture.ts` — `mockDashboard: DashboardResponse`
- `src/lib/useDashboard.ts` — 상태머신 훅 (렌더 없이 단위 검증 가능)

수정 (스텁 → 실제):
- `src/lib/api.ts` — mock 토글 추가 (fetch 경로 유지)
- `src/pages/Dashboard.tsx` — useDashboard 배선 + 렌더 4상태 분기
- `src/components/InputForm.tsx` — 폼 + 예시 이수내역 + onSubmit
- `src/components/KpiStrip.tsx` — `kpi` props
- `src/components/cards/CardA/*` — `data` props (MajorList/GeneralList/CourseItem/GradeBadge)
- `src/components/cards/CardC/*` — `data` props (PathwayRow)
- `src/components/cards/CardD/*` — `data` props (PatternSummary/ClusterBars)
- `src/components/WhyPanel.tsx` — 빈 카드 껍데기

범위 밖 (이번 단계 제외): MoreCoursesModal(후보 풀 데이터 필요 → null 유지), 차트 라이브러리, PDF 실제 export, 시각 폴리시, 단위 테스트(인프라 없음).

## 검증 기준

- `npm run build` (tsc) 통과 — props가 `types/api.ts` 계약과 타입 일치.
- dev 실행(mock on) → 폼 제출 → loading → fixture 기반 KPI+카드 A/C/D 렌더, WhyPanel은 빈 카드.
