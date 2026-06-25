// 카드 C — 학과 선배들의 다전공 경로 (아코디언) + 학칙 발췌.

import { useState } from "react";

import type { CardC as CardCData } from "../../../types/api";
import PathItem from "./PathItem";

interface Props {
  data: CardCData;
}

export default function CardC({ data }: Props) {
  const [expanded, setExpanded] = useState<string | null>(data.entries[0]?.id ?? null);

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">학과 선배들의 다전공 경로</div>
        <div className="card-meta">
          {data.cohort_label}
          <br />
          <span className="engine-tag">경로 분포 분석 (관찰값)</span>
        </div>
      </div>

      <div className="path-list">
        {data.entries.map((e) => (
          <PathItem
            key={e.id}
            entry={e}
            expanded={expanded === e.id}
            onToggle={() => setExpanded(expanded === e.id ? null : e.id)}
          />
        ))}
      </div>

      <div className="baseline-box">
        <strong>학칙 발췌</strong> · {data.baseline_note}
      </div>
    </div>
  );
}
