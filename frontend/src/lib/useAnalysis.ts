// 화면 흐름 상태머신: 프로필 선택 → 입력 → 로딩 → 대시보드.
// 선택한 프로필의 데이터(헤더 개인정보 포함)를 대시보드에 주입.
// 실제 백엔드 연동(lib/api.analyze)은 추후 — 데모는 프로필별 하드코딩 데이터 사용.

import { useCallback, useState } from "react";

import type { DemoProfile } from "../mock/profiles.fixture";
import type { DashboardResponse } from "../types/api";

export type Phase = "profile" | "input" | "loading" | "dashboard";

export interface UseAnalysis {
  phase: Phase;
  data: DashboardResponse | null;
  selectProfile: (profile: DemoProfile) => void;
  run: () => Promise<void>;
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

  const run = useCallback(async () => {
    if (!selected) return;
    setPhase("loading");
    await new Promise((resolve) => setTimeout(resolve, 1200)); // 로딩 화면 노출용
    setData(selected.dashboard);
    setPhase("dashboard");
  }, [selected]);

  const reset = useCallback(() => {
    setPhase("profile");
    setSelected(null);
    setData(null);
  }, []);

  return { phase, data, selectProfile, run, reset };
}
