// 백엔드 schemas 와 동기화. 변경 시 backend/app/schemas/{input,cards}.py 와 함께 갱신.
// codegen 자동화 여부는 OPEN_QUESTIONS (A12).
// 응답 타입은 legacy/mockup.html UI가 요구하는 형태로 확장됨 — 백엔드 카드 미구현 상태라 추후 미러.

export type RecommendationGrade = "강추" | "고려" | "유보";

// ===== 입력 (백엔드 계약: 5필드 고정) =====
// mockup 체크박스(공통선택/자유선택/추가선호 영역)는 InputScreen 로컬 UI 상태로만 수집.
// taken_course_ids = 들은 과목 → 추천에서 제외하는 기준.
export interface StudentInput {
  student_id: string;
  department: string;
  /** 복수전공 학과/학부 원문 목록 (기본 []) */
  extra_majors: string[];
  /** 학년 1~4. null이면 수강학년 필터·학년 적합도 생략 */
  year: number | null;
  taken_course_ids: string[];
  interest_career?: string | null;
  consider_multimajor: boolean;
}

// ===== 헤더 프로필 =====
export interface StudentProfile {
  name: string;
  department: string;
  year: string;
  analysis_date: string;
  report_semester: string; // 헤더 subtitle, 예: "2026-1학기"
  next_semester: string; // 추천 대상 학기, 예: "2026-2"
}

// ===== KPI =====
export interface KpiStrip {
  earned_credits: number;
  gpa: number | null;
  gpa_scale: number;
  similar_alumni_n: number;
}

// ===== 카드 A: 추천 과목 =====
export type CourseKind = "major" | "common" | "free"; // 전공 / 공통선택 / 자유선택
export type FactorKind = "pos" | "neg" | "mid" | "na"; // why-panel 기여도 색

export interface RecommendationFactor {
  label: string;
  weight_percent: number; // 막대 폭 0~100
  contribution: string; // "+26", "−18", "N/A"
  kind: FactorKind;
}

export interface RecommendedCourse {
  course_id: string; // 과목코드, 예: CSE3013
  course_name: string;
  credit: number | null;
  grade: RecommendationGrade;
  score_percent: number;
  reason_short: string;
  kind: CourseKind;
  kind_label: string; // 모달 구분 표기, 예: "전공선택" / "교양"
  area_label?: string | null; // 예: "공통선택 ④" / "자유선택 (언어·문화)"
  factors: RecommendationFactor[]; // why-panel 기여도 분해
  why_summary: string; // why-panel 한 줄 요약
}

export interface CardA {
  major: RecommendedCourse[];
  general: RecommendedCourse[];
  candidates: RecommendedCourse[]; // "과목 더 보기" 모달 전체 목록
}

// ===== 카드 C: 다전공 경로 =====
export interface PathwayCredits {
  major1: number | null;
  major2: number | null;
  major3: number | null;
}

export interface PathwayEntry {
  id: string;
  label: string;
  tag?: string | null; // 예: "최다"
  count: number;
  share_percent: number;
  bar_percent: number; // 막대 폭 (최다 대비 상대값)
  detail_label: string;
  credits: PathwayCredits;
  dim?: boolean; // 기타 경로 (상세 없음)
}

export interface CardC {
  cohort_label: string; // 예: "지식융합미디어 · 졸업생 184명"
  entries: PathwayEntry[];
  baseline_note: string; // 학칙 발췌
}

// ===== 카드 D: 유사 선배 진로 =====
export type CareerType = "job" | "grad" | "other";

export interface CareerEntry {
  cluster_label: string;
  type: CareerType;
  count: number;
  share_percent: number;
}

export interface CareerSubChip {
  label: string;
  n: number;
}

export interface CardD {
  similar_label: string; // 예: "유사 경로 27명"
  sample_size: number;
  entries: CareerEntry[];
  sub_title: string;
  sub_chips: CareerSubChip[];
  pattern_summary: string;
}

// ===== 유사 판정 근거 (cluster 패널) =====
export interface SimilarityFactor {
  label: string;
  percent: number;
}

export interface CommonCourse {
  name: string;
  n: number;
}

export interface CareerPattern {
  label: string;
  type: CareerType;
  text: string;
}

export interface ClusterEvidence {
  factors: SimilarityFactor[];
  common_courses: CommonCourse[];
  career_patterns: CareerPattern[];
  summary: string;
}

// ===== 대시보드 응답 =====
export interface DashboardResponse {
  profile: StudentProfile;
  kpi: KpiStrip;
  card_a: CardA;
  card_c: CardC;
  card_d: CardD;
  cluster: ClusterEvidence;
}
