# 프론트 analyze 배선 (입력 폼 → StudentInput → api.analyze) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 입력 화면의 실제 선택값(관심 진로·다전공)을 `StudentInput`으로 조립해 `api.analyze()` 경유로 대시보드를 받도록 배선한다. mock 토글(`VITE_USE_MOCK`)은 유지 — 백엔드 `/analyze` 준비 시 env 전환만으로 실 API 연동.

**Architecture:** `useAnalysis` 훅이 하드코딩된 `selected.dashboard` 대신 `analyze(buildStudentInput(profile, form), mockOverride)`를 호출. mock 경로는 프로필별 대시보드를 override로 유지해 데모 동작 불변. 실패 시 `error` phase + `ErrorScreen`.

**Tech Stack:** Vite + React 18 + TypeScript + Tailwind. 테스트 러너 없음 → 검증은 `npm run build`(tsc 포함) + dev 서버 확인.

## Global Constraints

- 모든 명령은 `frontend/` 디렉토리에서 실행.
- **계약 변경 금지:** `src/types/api.ts`의 `StudentInput`(5필드)·`DashboardResponse`는 수정하지 않는다 (백엔드가 Wave 2에서 미러 예정).
- `backend/` 및 `docs/` 수정 금지.
- 디자인 원칙 (frontend/README.md): 흰 배경 + 서강 빨강(#B8242C) 포인트만, 그라데이션/드롭섀도/블러 금지. 기존 클래스(`page`, `input-panel`, `analyze-btn`, `pdf-btn` 등) 재사용.
- mock 모드 기본 동작(프로필 A 선택 → 기존 대시보드 표시) 회귀 없음.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task F1: InputScreen 폼 값 전달

**Files:**
- Modify: `frontend/src/lib/useAnalysis.ts` (`AnalysisForm` 타입 export 추가만 — run 변경은 F2)
- Modify: `frontend/src/components/InputScreen.tsx`

**Interfaces:**
- Produces: `AnalysisForm { interest_career: string | null; consider_multimajor: boolean }` (useAnalysis.ts에서 export). `InputScreen`의 `onSubmit: (form: AnalysisForm) => void`. F2가 소비.

- [x] **Step 1: AnalysisForm 타입 추가**

`useAnalysis.ts` 상단(기존 `Phase` 타입 근처)에:

```ts
// 입력 화면에서 수집하는 분석 조건. StudentInput의 사용자 선택 필드에 대응.
export interface AnalysisForm {
  interest_career: string | null; // "미정"은 null
  consider_multimajor: boolean;
}
```

- [x] **Step 2: InputScreen이 form을 넘기도록 변경**

`InputScreen.tsx`:

```ts
import type { AnalysisForm } from "../lib/useAnalysis";

interface Props {
  onSubmit: (form: AnalysisForm) => void;
  onBack: () => void;
}
```

`handleSubmit` 교체:

```ts
function handleSubmit(e: FormEvent) {
  e.preventDefault();
  onSubmit({
    interest_career: career === "미정" ? null : career,
    consider_multimajor: multimajor === "yes",
  });
}
```

(체크박스 영역들은 기존 주석대로 UI 수집용 로컬 상태 유지 — `StudentInput` 계약에 없으므로 전송하지 않는다.)

- [x] **Step 3: 빌드 확인**

Run: `npm run build`
Expected: exit 0. (`run: () => Promise<void>`는 `(form) => void` 자리에 대입 가능하므로 App.tsx 수정 없이 통과.)

- [x] **Step 4: Commit**

```bash
git add src/lib/useAnalysis.ts src/components/InputScreen.tsx
git commit -m "feat(front): 입력 폼 값(관심 진로·다전공)을 AnalysisForm으로 전달"
```

---

### Task F2: buildStudentInput + api.analyze 경유

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/useAnalysis.ts`

**Interfaces:**
- Consumes: `AnalysisForm`(F1), `DemoProfile`(mock/profiles.fixture — `id`, `takenCourses`, `dashboard.profile.department`), `StudentInput`(types/api.ts).
- Produces: `analyze(input: StudentInput, mockOverride?: DashboardResponse)`, `buildStudentInput(profile: DemoProfile, form: AnalysisForm): StudentInput`, `useAnalysis().run(form: AnalysisForm)`.

- [x] **Step 1: api.analyze에 mockOverride 추가**

`api.ts`의 `analyze` 교체 (mock 경로가 프로필별 대시보드를 유지하기 위한 주입점):

```ts
export async function analyze(
  input: StudentInput,
  mockOverride?: DashboardResponse,
): Promise<DashboardResponse> {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 1200)); // 로딩 화면 노출용
    return mockOverride ?? mockDashboard;
  }
  const res = await fetch(`${BASE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    throw new Error(`analyze failed: ${res.status}`);
  }
  return res.json();
}
```

- [x] **Step 2: useAnalysis 배선**

`useAnalysis.ts`를 다음 형태로 변경 (파일 상단 주석의 "실제 백엔드 연동은 추후" 문구를 현행화):

```ts
import { useCallback, useState } from "react";

import { analyze } from "./api";
import type { DemoProfile } from "../mock/profiles.fixture";
import type { DashboardResponse, StudentInput } from "../types/api";

export type Phase = "profile" | "input" | "loading" | "dashboard";

export interface AnalysisForm {
  interest_career: string | null; // "미정"은 null
  consider_multimajor: boolean;
}

// 데모 프로필 + 입력 폼 → POST /analyze 요청 본문.
export function buildStudentInput(profile: DemoProfile, form: AnalysisForm): StudentInput {
  return {
    student_id: profile.id,
    department: profile.dashboard.profile.department,
    taken_course_ids: profile.takenCourses.map((c) => c.id),
    interest_career: form.interest_career,
    consider_multimajor: form.consider_multimajor,
  };
}

export interface UseAnalysis {
  phase: Phase;
  data: DashboardResponse | null;
  selectProfile: (profile: DemoProfile) => void;
  run: (form: AnalysisForm) => Promise<void>;
  reset: () => void;
}

export function useAnalysis(): UseAnalysis {
  const [phase, setPhase] = useState<Phase>("profile");
  const [selected, setSelected] = useState<DemoProfile | null>(null);
  const [data, setData] = useState<DashboardResponse | null>(null);

  const selectProfile = useCallback((profile: DemoProfile) => {
    setSelected(profile);
    setPhase("input");
  }, []);

  const run = useCallback(
    async (form: AnalysisForm) => {
      if (!selected) return;
      setPhase("loading");
      const result = await analyze(buildStudentInput(selected, form), selected.dashboard);
      setData(result);
      setPhase("dashboard");
    },
    [selected],
  );

  const reset = useCallback(() => {
    setPhase("profile");
    setSelected(null);
    setData(null);
  }, []);

  return { phase, data, selectProfile, run, reset };
}
```

(기존 `setTimeout` 1200ms는 api.ts mock 경로에 이미 있으므로 훅에서 제거.)

- [x] **Step 3: 빌드 + mock 동작 확인**

Run: `npm run build`
Expected: exit 0.

Run: `npm run dev` 기동 → 컴파일 에러 없음 확인 후 종료 (UI 클릭 검증은 사용자 몫으로 완료 보고에 명시).

- [x] **Step 4: Commit**

```bash
git add src/lib/api.ts src/lib/useAnalysis.ts
git commit -m "feat(front): useAnalysis가 buildStudentInput + api.analyze 경유 (mock 토글 유지)"
```

---

### Task F3: 분석 실패 에러 화면

**Files:**
- Create: `frontend/src/components/ErrorScreen.tsx`
- Modify: `frontend/src/lib/useAnalysis.ts`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: F2의 `run`.
- Produces: `Phase`에 `"error"` 추가, `useAnalysis()`에 `error: string | null`·`backToInput: () => void` 추가, `ErrorScreen({ message, onRetry, onReset })`.

- [ ] **Step 1: 훅에 error phase 추가**

`useAnalysis.ts` 변경점:

```ts
export type Phase = "profile" | "input" | "loading" | "dashboard" | "error";
```

`UseAnalysis`에 `error: string | null;`과 `backToInput: () => void;` 추가. 훅 본문:

```ts
const [error, setError] = useState<string | null>(null);

const run = useCallback(
  async (form: AnalysisForm) => {
    if (!selected) return;
    setPhase("loading");
    try {
      const result = await analyze(buildStudentInput(selected, form), selected.dashboard);
      setData(result);
      setPhase("dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  },
  [selected],
);

const backToInput = useCallback(() => {
  setError(null);
  setPhase("input");
}, []);
```

`reset`에도 `setError(null)` 추가. 반환 객체에 `error`, `backToInput` 포함.

- [ ] **Step 2: ErrorScreen 컴포넌트**

`src/components/ErrorScreen.tsx` 생성 (BrandHeader props가 `right` 필수라면 생략 가능하도록 실제 시그니처 확인 후 맞출 것):

```tsx
// 분석 실패 화면. 재시도는 입력 화면으로 복귀.

import BrandHeader from "./BrandHeader";

interface Props {
  message: string;
  onRetry: () => void;
  onReset: () => void;
}

export default function ErrorScreen({ message, onRetry, onReset }: Props) {
  return (
    <div className="page">
      <BrandHeader subtitle="분석 실패" />
      <div className="input-panel">
        <div className="input-body">
          <p>분석 요청에 실패했습니다: {message}</p>
          <p>백엔드 서버 상태를 확인하거나 다시 시도해 주세요.</p>
        </div>
      </div>
      <div className="input-actions">
        <button type="button" className="analyze-btn" onClick={onRetry}>
          다시 입력
        </button>
        <button type="button" className="pdf-btn" onClick={onReset}>
          처음으로
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: App 배선**

`App.tsx`:

```tsx
import ErrorScreen from "./components/ErrorScreen";
// ...
const { phase, data, error, selectProfile, run, reset, backToInput } = useAnalysis();

if (phase === "error")
  return <ErrorScreen message={error ?? "알 수 없는 오류"} onRetry={backToInput} onReset={reset} />;
```

- [ ] **Step 4: 빌드 확인**

Run: `npm run build`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add src/components/ErrorScreen.tsx src/lib/useAnalysis.ts src/App.tsx
git commit -m "feat(front): 분석 실패 에러 화면 + 입력 복귀"
```

---

## 완료 기준

- `npm run build` 성공 (tsc 에러 0).
- mock 모드(기본 dev): 프로필 A → 입력 → 분석 → 기존 대시보드 그대로 표시 (회귀 없음, 코드 경로는 `analyze()` 경유로 변경됨).
- `VITE_USE_MOCK=false` + 백엔드 미기동 시: 에러 화면 표시 → "다시 입력"으로 복귀 (백엔드 준비 전이므로 이 경로가 정상).
- 완료 보고에 수동 UI 확인이 필요한 항목을 명시할 것.
