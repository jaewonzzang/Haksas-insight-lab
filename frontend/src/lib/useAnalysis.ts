// 화면 흐름 상태머신: 프로필 선택 → 입력 → 로딩 → 대시보드.
// 선택한 프로필의 데이터(헤더 개인정보 포함)를 대시보드에 주입.
// 분석은 lib/api.analyze 경유 — mock 모드는 프로필별 대시보드를 override로 유지.

import { useCallback, useState } from "react";

import { analyze } from "./api";
import type { DemoProfile } from "../mock/profiles.fixture";
import type { DashboardResponse, StudentInput } from "../types/api";

export type Phase = "profile" | "input" | "loading" | "dashboard" | "error";

// 입력 화면에서 수집하는 분석 조건. StudentInput의 사용자 선택 필드에 대응.
export interface AnalysisForm {
  interest_career: string | null; // "미정"은 null
  consider_multimajor: boolean;
}

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

export interface UseAnalysis {
  phase: Phase;
  data: DashboardResponse | null;
  error: string | null;
  selectProfile: (profile: DemoProfile) => void;
  run: (form: AnalysisForm) => Promise<void>;
  reset: () => void;
  backToInput: () => void;
}

export function useAnalysis(): UseAnalysis {
  const [phase, setPhase] = useState<Phase>("profile");
  const [selected, setSelected] = useState<DemoProfile | null>(null);
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectProfile = useCallback((profile: DemoProfile) => {
    setSelected(profile);
    setPhase("input");
  }, []);

  const run = useCallback(
    async (form: AnalysisForm) => {
      if (!selected) return;
      setPhase("loading");
      try {
        const result = await analyze(buildStudentInput(selected, form), selected.dashboard);
        // 실모드에서 백엔드는 name/year를 모른다(SAINT 연계 전) — 데모 헤더를 병합.
        // mock 모드에서는 동일 값이라 no-op.
        const merged: DashboardResponse = {
          ...result,
          profile: {
            ...result.profile,
            name: selected.dashboard.profile.name,
            department: selected.dashboard.profile.department,
            year: selected.dashboard.profile.year,
          },
        };
        setData(merged);
        setPhase("dashboard");
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setPhase("error");
      }
    },
    [selected],
  );

  const reset = useCallback(() => {
    setPhase("profile");
    setSelected(null);
    setData(null);
    setError(null);
  }, []);

  const backToInput = useCallback(() => {
    setError(null);
    setPhase("input");
  }, []);

  return { phase, data, error, selectProfile, run, reset, backToInput };
}
