// 이수 현황: 과목 성격별 학점 카운트 (전공별 + 교양/자유선택). 참고용 — 졸업요건 판정 아님.
// credit_summary 는 백엔드가 전공 순서대로 정렬해 보낸다 → 연속 항목을 전공으로 그룹핑.

import type { CategoryCredit } from "../types/api";

interface Props {
  items?: CategoryCredit[];
}

export default function CreditSummary({ items }: Props) {
  if (!items || items.length === 0) return null;

  const groups: { major: string; cats: CategoryCredit[] }[] = [];
  for (const it of items) {
    const label = it.major ?? "교양·자유선택";
    const last = groups[groups.length - 1];
    if (last && last.major === label) last.cats.push(it);
    else groups.push({ major: label, cats: [it] });
  }

  return (
    <div className="credit-summary">
      <div className="credit-summary-title">이수 현황 · 과목 성격별 학점</div>
      <div className="credit-summary-groups">
        {groups.map((g) => (
          <div key={g.major} className="credit-group">
            <span className="credit-group-major">{g.major}</span>
            {g.cats.map((c) => (
              <span key={c.category} className="credit-pill">
                {c.category} <b>{c.credits}</b>학점 <em>· {c.course_count}과목</em>
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
