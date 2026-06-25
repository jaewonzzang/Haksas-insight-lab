// 디자인 토큰. 프로토타입(frontend/legacy/)에서 추출.
// Tailwind 설정은 이 토큰을 theme.extend 에 등록.

export const colors = {
  // 브랜드
  sogangRed: "#B8242C", // SAINT 메인 포인트
  white: "#FFFFFF",
  textPrimary: "#1A1A1A",
  textMuted: "#6B7280",
  border: "#E5E7EB",
  surface: "#F9FAFB",

  // 의미 색상 (사용자 결정 — 임의 변경 금지)
  rec강추: "#16A34A", // 녹색
  graduate: "#7C3AED", // 보라 (대학원)
  warning: "#F59E0B", // 황색 (위험/유보)
} as const;

export const spacing = {
  xs: "0.25rem",
  sm: "0.5rem",
  md: "1rem",
  lg: "1.5rem",
  xl: "2rem",
} as const;

export const typography = {
  fontSans:
    '"Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif',
  // 크기 토큰은 프로토타입 측정값 확정 후 추가
} as const;

export const badge = {
  강추: { bg: colors.rec강추, fg: colors.white },
  고려: { bg: colors.warning, fg: colors.white },
  유보: { bg: colors.border, fg: colors.textPrimary },
} as const;
