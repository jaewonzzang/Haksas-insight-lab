// 데모 프로필 A~D. 각 프로필이 이수과목 데이터 공간 + 분석 결과(헤더 개인정보 포함)를 보유.
// 학생 A = 현재 내 정보(김재원 · 지식융합미디어학부) + 이수 34과목 + 전체 분석.
// 학생 B~D = 빈 데이터 공간 (이수과목/분석 결과 추후 입력).

import type { DashboardResponse } from "../types/api";
import { mockDashboard } from "./dashboard.fixture";
import { takenCourses } from "./takenCourses.fixture";
import type { TakenCourse } from "./takenCourses.fixture";

export interface DemoProfile {
  id: string;
  label: string;
  available: boolean; // 데이터 준비 여부 (A만 true)
  takenCourses: TakenCourse[]; // 이수과목 데이터 공간
  dashboard: DashboardResponse; // 분석 결과 (헤더 개인정보 포함)
}

function emptyDashboard(name: string): DashboardResponse {
  return {
    profile: {
      name,
      department: "—",
      year: "—",
      analysis_date: "—",
      report_semester: "2026-1학기",
      next_semester: "2026-2",
    },
    kpi: { earned_credits: 0, gpa: null, gpa_scale: 4.3, similar_alumni_n: 0 },
    card_a: { major: [], general: [], candidates: [] },
    card_c: { cohort_label: "—", entries: [], baseline_note: "" },
    card_d: { similar_label: "—", sample_size: 0, entries: [], sub_title: "", sub_chips: [], pattern_summary: "" },
    cluster: { factors: [], common_courses: [], career_patterns: [], summary: "" },
  };
}

export const profiles: DemoProfile[] = [
  { id: "A", label: "학생 A", available: true, takenCourses, dashboard: mockDashboard },
  { id: "B", label: "학생 B", available: false, takenCourses: [], dashboard: emptyDashboard("학생 B") },
  { id: "C", label: "학생 C", available: false, takenCourses: [], dashboard: emptyDashboard("학생 C") },
  { id: "D", label: "학생 D", available: false, takenCourses: [], dashboard: emptyDashboard("학생 D") },
];
