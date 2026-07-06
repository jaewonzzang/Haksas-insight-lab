// 백엔드 호출 클라이언트. fetch 기반.
// 타입은 src/types/api.ts 에서 가져온다 (backend schemas와 동기화 필요).

import { mockDashboard } from "../mock/dashboard.fixture";
import type { DashboardResponse, StudentInput } from "../types/api";

const BASE_URL = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

// mock 토글: VITE_USE_MOCK 명시 시 그 값, 아니면 dev=mock / prod=real.
// 백엔드 /analyze 준비되면 VITE_USE_MOCK=false 로 끄면 됨 (재배선 불필요).
const USE_MOCK = import.meta.env.VITE_USE_MOCK
  ? import.meta.env.VITE_USE_MOCK === "true"
  : import.meta.env.DEV;

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
