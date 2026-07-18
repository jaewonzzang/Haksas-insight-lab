// 데모 프로필 A~D. 각 프로필이 학생 데이터(전공/학년/평점) + 이수과목 + 분석 결과를 보유.
// 학생 A = 현재 내 정보 (김재원 · 1전공 아트&테크놀로지 · 2전공 컴퓨터공학 · 3학년 · 평점 3.24).
// 학생 B~D = 실데이터 기반 (2026-07-18 A4 주입): 2차 수령분의 실제 학생 3명 이력.
//   B 경제+경영 다전공 4학년 · C 심리 단일전공 2학년 재학 · D 경영+컴공+데이터사이언스 3전공 4학년.
//   gpa 는 수강내역에 성적이 없어 null(— 표시). dashboard 는 헤더·프로필 카드용 —
//   카드 내용은 실모드에서 POST /analyze 가 채운다 (mock 모드에선 B~D 카드 빈 화면).

import type { DashboardResponse } from "../types/api";
import { mockDashboard } from "./dashboard.fixture";
import { takenCourses, takenCoursesB, takenCoursesC, takenCoursesD } from "./takenCourses.fixture";
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

function emptyDashboard(name: string, department = "—", year = "—", earnedCredits = 0): DashboardResponse {
  return {
    profile: {
      name,
      department,
      year,
      analysis_date: "—",
      report_semester: "2026-1학기",
      next_semester: "2026-2",
    },
    kpi: { earned_credits: earnedCredits, gpa: null, gpa_scale: 4.3, similar_alumni_n: 0 },
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
  {
    id: "B",
    label: "학생 B",
    available: true,
    primaryMajor: "경제학과",
    extraMajors: ["경영학부(경영학전공)"],
    year: 4,
    gpa: null,
    takenCourses: takenCoursesB,
    dashboard: emptyDashboard("학생 B", "경제학", "4학년", 114),
  },
  {
    id: "C",
    label: "학생 C",
    available: true,
    primaryMajor: "심리학과",
    extraMajors: [],
    year: 2,
    gpa: null,
    takenCourses: takenCoursesC,
    dashboard: emptyDashboard("학생 C", "심리학", "2학년", 54),
  },
  {
    id: "D",
    label: "학생 D",
    available: true,
    primaryMajor: "경영학부(경영학전공)",
    extraMajors: ["컴퓨터공학과", "경영 데이터사이언스"],
    year: 4,
    gpa: null,
    takenCourses: takenCoursesD,
    dashboard: emptyDashboard("학생 D", "경영학", "4학년", 123),
  },
];
