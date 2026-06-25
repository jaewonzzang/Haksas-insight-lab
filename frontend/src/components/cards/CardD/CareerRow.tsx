// 진로 분포 1행 (수평 바). 인과 단정 없이 관찰값 분포만.

import type { CareerEntry, CareerType } from "../../../types/api";

const FILL: Record<CareerType, string> = {
  job: "c-job",
  grad: "c-grad",
  other: "c-other",
};

interface Props {
  entry: CareerEntry;
}

export default function CareerRow({ entry }: Props) {
  return (
    <div className="career-row">
      <div>
        <div className="career-name">{entry.cluster_label}</div>
        <div className="career-bar">
          <div className={`career-bar-fill ${FILL[entry.type]}`} style={{ width: `${entry.share_percent}%` }} />
        </div>
      </div>
      <div className="career-stat">
        <span className="num">{entry.count}명</span> · {entry.share_percent}%
      </div>
    </div>
  );
}
