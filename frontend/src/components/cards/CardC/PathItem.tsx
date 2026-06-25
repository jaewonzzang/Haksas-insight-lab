// 다전공 경로 1행. 클릭 시 평균 추가 이수 학점 펼침 (아코디언).

import type { PathwayEntry } from "../../../types/api";

function CreditCell({ label, value }: { label: string; value: number | null }) {
  return (
    <div className={`credit-cell${value == null ? " dim" : ""}`}>
      <div className="credit-label">{label}</div>
      <div className="credit-value">
        {value == null ? (
          "—"
        ) : (
          <>
            {value}
            <span className="unit">학점</span>
          </>
        )}
      </div>
    </div>
  );
}

interface Props {
  entry: PathwayEntry;
  expanded: boolean;
  onToggle: () => void;
}

export default function PathItem({ entry, expanded, onToggle }: Props) {
  return (
    <div className={`path-item${expanded ? " expanded" : ""}`} onClick={onToggle}>
      <div className="path-row">
        <div className="path-name-wrap">
          <span className="path-name" style={entry.dim ? { color: "var(--text-sub)" } : undefined}>
            {entry.label}
          </span>
          {entry.tag && <span className="path-tag">{entry.tag}</span>}
        </div>
        <div className="path-stat">
          <span className="pct">{entry.share_percent}%</span>
          {entry.count}명
        </div>
      </div>
      <div className="path-bar">
        <div
          className="path-bar-fill"
          style={{ width: `${entry.bar_percent}%`, opacity: entry.dim ? 0.5 : undefined }}
        />
      </div>
      {!entry.dim && (
        <div className="path-detail">
          <div className="path-detail-inner">
            <div className="path-detail-label">{entry.detail_label}</div>
            <div className="credit-grid">
              <CreditCell label="1전공" value={entry.credits.major1} />
              <CreditCell label="2전공" value={entry.credits.major2} />
              <CreditCell label="3전공" value={entry.credits.major3} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
