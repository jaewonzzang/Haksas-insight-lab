// 카드 D — 유사 선배의 진로 (인과 단정 X). 진로 분포 + 대학원 분야 + 패턴 + "유사 판정 근거".

import type { CardD as CardDData } from "../../../types/api";
import CareerRow from "./CareerRow";

interface Props {
  data: CardDData;
  onOpenCluster: () => void;
}

export default function CardD({ data, onOpenCluster }: Props) {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">유사 선배의 진로</div>
        <div className="card-meta">
          {data.similar_label}
          <br />
          <span className="engine-tag">이수경로 임베딩 기반 분포</span>
        </div>
      </div>

      <div className="career-list">
        {data.entries.map((e) => (
          <CareerRow key={e.cluster_label} entry={e} />
        ))}
      </div>

      <div className="career-sub">
        <div className="career-sub-title">{data.sub_title}</div>
        <div className="chip-row">
          {data.sub_chips.map((c) => (
            <div key={c.label} className="chip">
              {c.label}
              <span className="n">{c.n}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="pattern-box">
        <div className="pattern-label">관찰된 패턴</div>
        <div className="pattern-text">{data.pattern_summary}</div>
      </div>

      <div className="card-foot-actions">
        <button type="button" className="btn-why" onClick={onOpenCluster}>
          유사 판정 근거
        </button>
      </div>
    </div>
  );
}
