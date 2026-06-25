// 추천 등급 → mockup CSS 클래스 매핑 (점수색/뱃지).

import type { RecommendationGrade } from "../types/api";

export function scoreClass(grade: RecommendationGrade): string {
  return grade === "강추" ? "s-high" : grade === "고려" ? "s-mid" : "s-low";
}

export function badgeClass(grade: RecommendationGrade): string {
  return grade === "강추" ? "b-strong" : grade === "고려" ? "b-consider" : "b-hold";
}

// "과목 더 보기" 모달 뱃지 필터 값 ↔ 등급
export function badgeKey(grade: RecommendationGrade): "strong" | "consider" | "hold" {
  return grade === "강추" ? "strong" : grade === "고려" ? "consider" : "hold";
}
