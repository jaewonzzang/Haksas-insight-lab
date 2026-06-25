// KPI 스트립: 이수 학점 / 평점평균 / 유사 졸업생 표본 수.

import type { KpiStrip as KpiData } from "../types/api";

interface Props {
  kpi: KpiData;
}

export default function KpiStrip({ kpi }: Props) {
  return (
    <div className="kpi-row">
      <div className="kpi">
        <div className="kpi-label">이수 학점</div>
        <div className="kpi-value">
          {kpi.earned_credits}
          <span className="total"> 학점</span>
        </div>
      </div>
      <div className="kpi">
        <div className="kpi-label">평점평균</div>
        <div className="kpi-value">
          {kpi.gpa != null ? kpi.gpa.toFixed(2) : "—"}
          <span className="total"> / {kpi.gpa_scale}</span>
        </div>
      </div>
      <div className="kpi">
        <div className="kpi-label">유사 졸업생 표본</div>
        <div className="kpi-value">
          {kpi.similar_alumni_n}
          <span className="unit">명</span>
        </div>
      </div>
    </div>
  );
}
