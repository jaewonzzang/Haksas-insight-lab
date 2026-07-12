// 데모 프로필 A~D. 각 프로필이 학생 데이터(전공/학년/평점) + 이수과목 + 분석 결과를 보유.
// 학생 A = 현재 내 정보 (김재원 · 1전공 아트&테크놀로지 · 2전공 컴퓨터공학 · 3학년 · 평점 3.24).
// 학생 B~D = 빈 데이터 공간 (학생 데이터/이수과목 추후 입력).

import type { DashboardResponse } from "../types/api";
import { mockDashboard } from "./dashboard.fixture";
import { takenCourses } from "./takenCourses.fixture";
import type { TakenCourse } from "./takenCourses.fixture";

export interface DemoProfile {
  id: string;
  label: string;
  available: boolean; // 데이터 준비 여부 (A만 true)
  // --- 학생 데이터 (분석 입력용, DB 학과명 원문) ---
  primaryMajor: string; // 1전공
  extraMajors: string[]; // 2전공 이하
  year: number | null; // 학년 (수강학년 필터·학년 적합도 입력)
  gpa: number | null; // 평점 (4.3 만점) — 실모드 KPI에 병합 표시
  // --- 데이터 공간 ---
  takenCourses: TakenCourse[]; // 이수과목
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
  {
    id: "A",
    label: "학생 A",
    available: true,
    primaryMajor: "아트&테크놀로지학과",
    extraMajors: ["컴퓨터공학과"],
    year: 3,
    gpa: 3.24,
    takenCourses,
    dashboard: mockDashboard,
  },
  { id: "B", label: "학생 B", available: false, primaryMajor: "", extraMajors: [], year: null, gpa: null, takenCourses: [], dashboard: emptyDashboard("학생 B") },
  { id: "C", label: "학생 C", available: false, primaryMajor: "", extraMajors: [], year: null, gpa: null, takenCourses: [], dashboard: emptyDashboard("학생 C") },
  { id: "D", label: "학생 D", available: false, primaryMajor: "", extraMajors: [], year: null, gpa: null, takenCourses: [], dashboard: emptyDashboard("학생 D") },
];
