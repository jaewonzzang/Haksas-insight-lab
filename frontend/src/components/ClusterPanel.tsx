// "유사 판정 근거" 사이드 패널 — 유사도 요소 + 공통 이수 과목 + 진로별 특징.

import type { CareerType, ClusterEvidence } from "../types/api";

const PATTERN_COLOR: Record<CareerType, string> = {
  grad: "var(--grad-school)",
  job: "var(--good)",
  other: "#888",
};

interface Props {
  open: boolean;
  onClose: () => void;
  data: ClusterEvidence;
}

export default function ClusterPanel({ open, onClose, data }: Props) {
  return (
    <>
      <div className={`panel-overlay${open ? " open" : ""}`} onClick={onClose} />
      <aside className={`side-panel${open ? " open" : ""}`}>
        <div className="panel-header">
          <div className="panel-title-block">
            <div className="panel-eyebrow">유사 판정 근거</div>
            <h2 className="panel-title">왜 이 27명이 유사 선배인가</h2>
            <div className="panel-sub">이수 과목 임베딩 기반 거리 산출 · 임계 거리 미만 졸업생만 표시</div>
          </div>
          <button type="button" className="panel-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="panel-body">
          <div className="why-section">
            <div className="why-course-head">
              <div className="why-course-name" style={{ fontSize: 14 }}>
                유사도 산정 요소
              </div>
            </div>
            <div className="factor-list">
              {data.factors.map((f) => (
                <div key={f.label} className="factor">
                  <div className="factor-label">{f.label}</div>
                  <div className="factor-bar">
                    <div className="factor-fill contrib-pos" style={{ width: `${f.percent}%` }} />
                  </div>
                  <div className="factor-val">{f.percent}%</div>
                </div>
              ))}
            </div>
          </div>

          <div className="why-section">
            <div className="why-course-head">
              <div className="why-course-name" style={{ fontSize: 14 }}>
                유사 선배 27명의 공통 이수 과목
              </div>
            </div>
            <div className="chip-row" style={{ marginTop: 4 }}>
              {data.common_courses.map((c) => (
                <div key={c.name} className="chip">
                  {c.name}
                  <span className="n">{c.n}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="why-section">
            <div className="why-course-head">
              <div className="why-course-name" style={{ fontSize: 14 }}>
                진로별 관찰된 특징
              </div>
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text)", lineHeight: 1.7 }}>
              {data.career_patterns.map((p, i) => (
                <div
                  key={p.label}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "80px 1fr",
                    gap: 10,
                    padding: "8px 0",
                    borderBottom:
                      i < data.career_patterns.length - 1 ? "1px solid var(--line-soft)" : undefined,
                  }}
                >
                  <div style={{ fontWeight: 700, color: PATTERN_COLOR[p.type] }}>{p.label}</div>
                  <div style={{ color: "var(--text-sub)" }}>{p.text}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="why-summary">
            <span className="label">한 줄 요약</span>
            {data.summary}
          </div>
        </div>
      </aside>
    </>
  );
}
