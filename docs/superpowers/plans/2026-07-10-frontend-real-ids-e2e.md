# W6-F: 이수과목 실 course_id 매핑 + 실모드 헤더 병합 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학생 A 이수과목 픽스처의 placeholder id(T01~)를 실 DB `course_id`로 교체하고(34개 중 32개 매핑 — 2026-07-10 DB 실측), 실모드(`VITE_USE_MOCK=false`)에서 백엔드 응답에 데모 헤더(이름·학년)를 병합해 대시보드 헤더가 깨지지 않게 한다.

**Architecture:** 백엔드는 `profile.name`을 `"학생 {student_id}"` placeholder로, `year`를 `"—"`로 채운다(SAINT 연계 전 — W6-B 확정). 프론트 `useAnalysis.run()`이 응답 위에 선택 프로필의 name/year만 덮어쓴다 — mock 모드에서는 같은 값이라 no-op. 매핑 규칙(실측 근거): 동일 과목명이 여러 학과 id로 존재하면 CSE 변형 우선(컴공 개설 — mock 코호트와 정합, AIE/CSE는 alias 미연결 확인됨), 알바트로스세미나는 학생 A 소속 분반 `COR1021(지식융합미디어)`, 군이러닝 2건은 DB에 없어 placeholder 유지(백엔드가 무해하게 무시).

**Tech Stack:** Vite + React + TS. 테스트 러너 없음 — 검증은 `npm run build`(tsc 포함) + mock 모드 회귀.

## Global Constraints

- 모든 명령은 `frontend/` 디렉토리에서 실행.
- 수정 허용: `frontend/src/mock/takenCourses.fixture.ts`, `frontend/src/lib/useAnalysis.ts`, 이 플랜 파일의 체크박스만. **`backend/`, `docs/`, `types/api.ts` 수정 금지.**
- 워킹트리의 기존 미커밋 변경(`frontend/legacy/mockup.html` 등 EOL 노이즈)은 add/commit/checkout 금지.
- 커밋은 자기 변경 파일만 명시적 `git add`. push 금지. `index.lock` 충돌 시 몇 초 후 재시도(backend 에이전트 병행 중). 커밋 메시지 끝 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: takenCourses.fixture.ts 실 course_id 교체

**Files:**
- Modify: `frontend/src/mock/takenCourses.fixture.ts`

**Interfaces:**
- Produces: `takenCourses: TakenCourse[]` — id가 실 DB course_id (`buildStudentInput`이 그대로 `taken_course_ids`로 전송). 구조(`{id, name}`)와 export는 불변.

- [x] **Step 1: 배열 교체**

파일 전체를 아래로 교체 (인터페이스·export 이름 유지, 주석 갱신):

```typescript
// 학생 A 이수 과목 (사용자 실제 수강 목록, 중복 제거 34과목).
// id = 실 DB course_id (2026-07-10 s_compass_courses.db 실측 매핑).
// - 동일 과목명 다중 id는 CSE(컴퓨터공학과) 개설 우선.
// - 알바트로스세미나 = 학생 A 소속 분반 COR1021(지식융합미디어).
// - 군이러닝 2건(T12·T13)은 DB 부재 — placeholder 유지, 백엔드가 무시.

export interface TakenCourse {
  id: string;
  name: string;
}

export const takenCourses: TakenCourse[] = [
  { id: "COR1012", name: "인문사회글쓰기" },
  { id: "HFS2002", name: "신학적인간학" },
  { id: "AAT3019", name: "Data Visualization" },
  { id: "CSE3030", name: "컴퓨터시스템개론" },
  { id: "CSE3080", name: "자료구조" },
  { id: "CSE4010", name: "컴퓨터아키텍쳐" },
  { id: "CSE4175", name: "컴퓨터네트워크" },
  { id: "ETS2001", name: "현대세계와윤리문제" },
  { id: "AAT2004", name: "Intro to Creative Computing" },
  { id: "COR1010", name: "기초인공지능프로그래밍" },
  { id: "MAS2003", name: "한류" },
  { id: "T12", name: "군이러닝취득교과목I" },
  { id: "T13", name: "군이러닝취득교과목II" },
  { id: "COR1007", name: "성찰과성장" },
  { id: "CSE3006", name: "이산구조" },
  { id: "CSE3015", name: "디지털회로개론" },
  { id: "CSE3040", name: "JAVA언어" },
  { id: "MAS1004", name: "Data&AI" },
  { id: "MAS2008", name: "Fundamentals of Programming and Problem Solving" },
  { id: "STS2008", name: "고급응용C프로그래밍" },
  { id: "COR1021", name: "알바트로스세미나" },
  { id: "GKS3002", name: "Intro to Korea thru Literature and Film" },
  { id: "HSS3001", name: "인간과인성" },
  { id: "PUB2005", name: "법과현대사회" },
  { id: "SHS2002", name: "한국과세계" },
  { id: "ETS2003", name: "철학산책" },
  { id: "LED3015", name: "자기브랜드리더십" },
  { id: "MAS2002", name: "전략커뮤니케이션" },
  { id: "STS2002", name: "생명과환경" },
  { id: "STS2004", name: "대학수학" },
  { id: "COR1003", name: "영어글로벌의사소통I" },
  { id: "MAS1001", name: "지식융합미디어입문" },
  { id: "MAS1002", name: "Creativity & Visual Expression" },
  { id: "GKS1001", name: "Critical Thinking for Social Inquiry" },
];
```

(T19였던 "Fundamentals of Programming and Problem(Solving)"은 DB 원문 표기 "… Problem Solving"으로 교정 — 매핑 근거를 표기와 일치시키기 위함.)

- [x] **Step 2: 참조 지점 회귀 확인**

Run: `npm run build`
Expected: 성공 (id 문자열만 바뀌므로 타입 영향 없음). `takenCourses`를 참조하는 코드(`profiles.fixture.ts`, `useAnalysis.buildStudentInput`, 입력 화면 표시)가 id 형식을 가정하지 않는지 grep으로 확인: `grep -rn "T0\|T1[0-9]" src/` — 픽스처 외 참조가 나오면 보고 후 중단.

- [x] **Step 3: Commit**

```bash
git add src/mock/takenCourses.fixture.ts
git commit -m "feat: 학생 A 이수과목 픽스처 실 course_id 매핑 (32/34, CSE 우선·COR1021)"
```

---

### Task 2: 실모드 헤더 병합 (useAnalysis)

**Files:**
- Modify: `frontend/src/lib/useAnalysis.ts` (`run` 콜백만)

**Interfaces:**
- Consumes: 백엔드 `DashboardResponse.profile`(name = placeholder, year = "—"), `DemoProfile.dashboard.profile`(데모 실명·학년).
- Produces: 대시보드에 주입되는 `data.profile`이 실모드에서도 데모 헤더를 유지.

- [x] **Step 1: run() 병합 수정**

`useAnalysis.ts`의 `run` 내부, `analyze` 호출 직후를 다음으로 교체:

```typescript
const result = await analyze(buildStudentInput(selected, form), selected.dashboard);
// 실모드에서 백엔드는 name/year를 모른다(SAINT 연계 전) — 데모 헤더를 병합.
// mock 모드에서는 동일 값이라 no-op.
const merged: DashboardResponse = {
  ...result,
  profile: {
    ...result.profile,
    name: selected.dashboard.profile.name,
    year: selected.dashboard.profile.year,
  },
};
setData(merged);
```

- [x] **Step 2: 빌드 + mock 모드 회귀**

Run: `npm run build` — 성공.
Run: `npm run dev` 를 잠깐 띄워 mock 모드(기본)에서 프로필 A → 분석 → 대시보드 헤더(이름·학과·학년)가 기존과 동일한지 확인 후 종료. (UI 자동화 없음 — dev 서버가 뜨고 콘솔 에러 없이 컴파일되는 것까지 확인하면 충분, 렌더 확인은 메인 세션 E2E에서 재검.)

- [x] **Step 3: Commit + 플랜 체크박스 갱신**

```bash
git add src/lib/useAnalysis.ts
git commit -m "feat: 실모드 대시보드 헤더에 데모 프로필 name/year 병합"
git add ../docs/superpowers/plans/2026-07-10-frontend-real-ids-e2e.md
git commit -m "docs: W6-F 플랜 체크박스 갱신"
```

완료 보고: ① 커밋 해시, ② `npm run build` 결과, ③ 픽스처 외 placeholder id 참조 grep 결과, ④ 플랜 이탈 사항.
