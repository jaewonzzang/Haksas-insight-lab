# W8-F: 추가 선호 체크박스 → 백엔드 전송 배선 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 입력 화면의 "추가 선호" 체크박스 3개(팀플레이 선호·S/U 평가 선호·출석 비중 낮음 선호)가 UI 수집만 되고 버려지던 것을 `StudentInput`으로 전송한다 — 백엔드 W8-B(병행)가 이 값으로 "사용자 선호 매칭" 요인을 계산.

**계약 (백엔드와 필드명 고정):** `prefer_team_project: boolean`, `prefer_su_eval: boolean`, `prefer_low_attendance: boolean`.

## Global Constraints

- 모든 명령은 `frontend/`에서.
- 수정 허용: `src/types/api.ts`(3필드), `src/components/InputScreen.tsx`, `src/lib/useAnalysis.ts`, 이 플랜 체크박스. **`backend/`, `docs/`, 그 외 파일 금지.** 공통선택/자유선택 영역 체크박스는 이번 범위 밖 — 기존 `StaticChk` 그대로 둘 것.
- backend 에이전트 병행 중 — `index.lock` 충돌 시 몇 초 후 재시도. 기존 미커밋 EOL 노이즈(`frontend/legacy/mockup.html` 등) add 금지.
- 명시적 `git add`, push 금지, 커밋 메시지 끝 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: 선호 3필드 배선

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/lib/useAnalysis.ts`
- Modify: `frontend/src/components/InputScreen.tsx`

- [x] **Step 1: types/api.ts — StudentInput에 추가** (`year` 아래):

```typescript
  /** 팀플레이 선호 */
  prefer_team_project: boolean;
  /** S/U 평가 선호 — 백엔드 신호 재료 없음(전송만) */
  prefer_su_eval: boolean;
  /** 출석(참여도) 비중 낮음 선호 */
  prefer_low_attendance: boolean;
```

- [x] **Step 2: useAnalysis.ts — AnalysisForm 확장 + 전송**

`AnalysisForm`에 3필드 추가:

```typescript
export interface AnalysisForm {
  interest_career: string | null; // "미정"은 null
  consider_multimajor: boolean;
  prefer_team_project: boolean;
  prefer_su_eval: boolean;
  prefer_low_attendance: boolean;
}
```

`buildStudentInput` 반환 객체에 추가:

```typescript
    prefer_team_project: form.prefer_team_project,
    prefer_su_eval: form.prefer_su_eval,
    prefer_low_attendance: form.prefer_low_attendance,
```

- [x] **Step 3: InputScreen.tsx — PREFS를 controlled로**

`PREFS` 상수를 키 있는 구조로 교체:

```typescript
const PREFS = [
  { key: "prefer_team_project", label: "팀플레이 선호" },
  { key: "prefer_su_eval", label: "S/U 평가 선호" },
  { key: "prefer_low_attendance", label: "출석 비중 낮음 선호" },
] as const;
```

상태 추가 (기존 `career`/`multimajor` 옆):

```typescript
  const [prefs, setPrefs] = useState<Record<(typeof PREFS)[number]["key"], boolean>>({
    prefer_team_project: true,
    prefer_su_eval: true,
    prefer_low_attendance: true,
  }); // 기존 defaultChecked(전부 켬)와 동일한 초기값
```

렌더링에서 `StaticChk` → `PickChk`로 교체 (추가 선호 그룹만):

```tsx
                {PREFS.map((p) => (
                  <PickChk
                    key={p.key}
                    label={p.label}
                    checked={prefs[p.key]}
                    onChange={() => setPrefs((s) => ({ ...s, [p.key]: !s[p.key] }))}
                  />
                ))}
```

`handleSubmit`의 onSubmit 객체에 `...prefs` 병합:

```typescript
    onSubmit({
      interest_career: career === "미정" ? null : career,
      consider_multimajor: multimajor === "yes",
      ...prefs,
    });
```

- [x] **Step 4: 빌드 + Commit + 체크박스**

Run: `npm run build` — 성공 확인.

```bash
git add src/types/api.ts src/lib/useAnalysis.ts src/components/InputScreen.tsx
git commit -m "feat: 추가 선호 체크박스 3종을 StudentInput으로 전송 (선호 매칭 요인 입력)"
git add ../docs/superpowers/plans/2026-07-13-frontend-pref-wiring.md
git commit -m "docs: W8-F 플랜 체크박스 갱신"
```

완료 보고: ① 커밋 해시, ② 빌드 결과, ③ 플랜 이탈 사항.
