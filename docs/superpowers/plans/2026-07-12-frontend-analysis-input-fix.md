# W6.5-F: 분석용 학과 입력 분리(버그 수정) + 복수전공 전송 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실모드에서 전공 추천이 통째로 비는 버그 수정. 원인: `buildStudentInput`이 헤더 **표시용** 문자열(`"아트&테크놀로지"`)을 분석용 `department`로 전송 → 백엔드 학과 매칭 0건 → 전공 풀 빈 목록. 분석용 학과 원문(`"지식융합미디어학부"`)을 별도 필드로 분리하고, 복수전공(`extra_majors: ["컴퓨터공학과"]`)도 함께 전송한다.

**Architecture:** `DemoProfile`에 분석용 필드 2개(`analysisDepartment`, `extraMajors`) 추가 — 헤더 표시는 기존 `dashboard.profile.department`("아트&테크놀로지") 유지, 분석 입력만 원문 사용. `useAnalysis`의 실모드 헤더 병합에 `department`도 포함해 백엔드 에코("지식융합미디어학부")가 헤더 표시를 덮지 않게 한다. 계약 필드 `extra_majors`는 백엔드(W6.5-B, 병행 작업 중)와 이름 고정.

**Tech Stack:** Vite + React + TS. 검증 = `npm run build`.

## Global Constraints

- 모든 명령은 `frontend/`에서 실행.
- 수정 허용: `src/types/api.ts`(StudentInput에 `extra_majors` 1필드 추가만), `src/mock/profiles.fixture.ts`, `src/lib/useAnalysis.ts`, 이 플랜 체크박스. **`backend/`, `docs/`, 그 외 프론트 파일 수정 금지.**
- 계약 필드명 고정: **`extra_majors: string[]`** (백엔드 `schemas/input.py`와 동일 — 변경 금지).
- 워킹트리 기존 미커밋 변경(EOL 노이즈)은 add/commit/checkout 금지.
- backend 에이전트 병행 중 — `index.lock` 충돌 시 몇 초 후 재시도. 명시적 `git add`, push 금지, 커밋 메시지 끝 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: types/api.ts 계약 미러

**Files:**
- Modify: `frontend/src/types/api.ts`

- [x] **Step 1: StudentInput에 필드 추가**

`StudentInput` 인터페이스에 (기존 필드 순서 유지, `department` 다음 줄):

```typescript
  /** 복수전공 학과/학부 원문 목록 (기본 []) */
  extra_majors: string[];
```

- [x] **Step 2: Commit**

`npm run build`가 이 시점엔 실패한다(빌드는 Task 2 후) — 타입 추가만 커밋:

```bash
git add src/types/api.ts
git commit -m "feat: StudentInput.extra_majors 계약 미러 (backend schemas/input.py 동기화)"
```

(참고: `buildStudentInput`이 아직 이 필드를 안 채워 tsc가 Task 2 전까지 실패하므로, Task 1·2를 한 커밋으로 합쳐도 된다 — 그 경우 커밋 메시지는 Task 2 것을 쓰고 보고에 명시.)

---

### Task 2: 분석용 학과/복수전공 분리 + 헤더 병합 보강

**Files:**
- Modify: `frontend/src/mock/profiles.fixture.ts`
- Modify: `frontend/src/lib/useAnalysis.ts`

- [x] **Step 1: DemoProfile 확장**

`profiles.fixture.ts`의 인터페이스에 필드 추가:

```typescript
export interface DemoProfile {
  id: string;
  label: string;
  available: boolean; // 데이터 준비 여부 (A만 true)
  analysisDepartment: string; // 분석용 학과/학부 원문 (백엔드 dept_normalizer 키) — 헤더 표시용과 별개
  extraMajors: string[]; // 복수전공 학과 원문
  takenCourses: TakenCourse[]; // 이수과목 데이터 공간
  dashboard: DashboardResponse; // 분석 결과 (헤더 개인정보 포함)
}
```

`profiles` 배열 갱신:

```typescript
export const profiles: DemoProfile[] = [
  {
    id: "A",
    label: "학생 A",
    available: true,
    analysisDepartment: "지식융합미디어학부",
    extraMajors: ["컴퓨터공학과"],
    takenCourses,
    dashboard: mockDashboard,
  },
  { id: "B", label: "학생 B", available: false, analysisDepartment: "", extraMajors: [], takenCourses: [], dashboard: emptyDashboard("학생 B") },
  { id: "C", label: "학생 C", available: false, analysisDepartment: "", extraMajors: [], takenCourses: [], dashboard: emptyDashboard("학생 C") },
  { id: "D", label: "학생 D", available: false, analysisDepartment: "", extraMajors: [], takenCourses: [], dashboard: emptyDashboard("학생 D") },
];
```

- [x] **Step 2: buildStudentInput + 헤더 병합 수정**

`useAnalysis.ts`의 `buildStudentInput`:

```typescript
// 데모 프로필 + 입력 폼 → POST /analyze 요청 본문.
// department는 분석용 원문(analysisDepartment) — 헤더 표시 문자열과 분리 (2026-07-12 버그 수정).
export function buildStudentInput(profile: DemoProfile, form: AnalysisForm): StudentInput {
  return {
    student_id: profile.id,
    department: profile.analysisDepartment,
    extra_majors: profile.extraMajors,
    taken_course_ids: profile.takenCourses.map((c) => c.id),
    interest_career: form.interest_career,
    consider_multimajor: form.consider_multimajor,
  };
}
```

`run()`의 병합 블록에 `department` 추가 (백엔드가 분석용 원문을 에코하므로 표시용으로 되돌림):

```typescript
        const merged: DashboardResponse = {
          ...result,
          profile: {
            ...result.profile,
            name: selected.dashboard.profile.name,
            department: selected.dashboard.profile.department,
            year: selected.dashboard.profile.year,
          },
        };
```

- [x] **Step 3: 빌드 확인**

Run: `npm run build`
Expected: 성공 (tsc 포함). 실패 시 타입 에러 지점 확인 — `DemoProfile` 사용처(`ProfileScreen` 등)가 새 필드를 요구하지 않는지 grep.

- [x] **Step 4: Commit + 플랜 체크박스**

```bash
git add src/mock/profiles.fixture.ts src/lib/useAnalysis.ts
git commit -m "fix: 분석용 학과 원문 분리 — 표시용 문자열 전송으로 전공 풀이 비던 버그"
git add ../docs/superpowers/plans/2026-07-12-frontend-analysis-input-fix.md
git commit -m "docs: W6.5-F 플랜 체크박스 갱신"
```

완료 보고: ① 커밋 해시, ② `npm run build` 결과, ③ 플랜 이탈 사항.
