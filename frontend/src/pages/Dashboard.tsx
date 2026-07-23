// 대시보드 화면. 헤더 + KPI + 카드 A/C/D + 사이드패널 2개 + 모달.
// 패널/모달 open 상태와 body 스크롤 락, Esc 닫기를 소유.

import { useEffect, useState } from "react";

import BrandHeader from "../components/BrandHeader";
import ClusterPanel from "../components/ClusterPanel";
import CreditSummary from "../components/CreditSummary";
import KpiStrip from "../components/KpiStrip";
import MoreModal from "../components/MoreModal";
import PdfExportButton from "../components/PdfExportButton";
import WhyPanel from "../components/WhyPanel";
import CardA from "../components/cards/CardA";
import CardC from "../components/cards/CardC";
import CardD from "../components/cards/CardD";
import type { DashboardResponse } from "../types/api";

interface Props {
  data: DashboardResponse;
  onReset: () => void;
}

export default function Dashboard({ data, onReset }: Props) {
  const [panel, setPanel] = useState<"why" | "cluster" | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const anyOpen = panel !== null || modalOpen;

  useEffect(() => {
    document.body.classList.toggle("locked", anyOpen);
    return () => document.body.classList.remove("locked");
  }, [anyOpen]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPanel(null);
        setModalOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const { profile, kpi, card_a, card_c, card_d, cluster, credit_summary } = data;

  return (
    <div className="page">
      <BrandHeader
        subtitle={`학업 분석 리포트 · ${profile.report_semester}`}
        right={
          <>
            <button type="button" className="pdf-btn" onClick={onReset}>
              ← 처음으로
            </button>
            <PdfExportButton />
            <div className="user-info">
              <strong>{profile.name}</strong> · {profile.department}
              <br />
              {profile.year} · 분석일 {profile.analysis_date}
            </div>
          </>
        }
      />

      <KpiStrip kpi={kpi} />
      <CreditSummary items={credit_summary} />

      <div className="grid">
        <CardA data={card_a} onOpenWhy={() => setPanel("why")} onOpenMore={() => setModalOpen(true)} />
        <CardC data={card_c} />
        <CardD data={card_d} onOpenCluster={() => setPanel("cluster")} />
      </div>

      <WhyPanel
        open={panel === "why"}
        onClose={() => setPanel(null)}
        courses={[...card_a.major, ...card_a.general]}
      />
      <ClusterPanel open={panel === "cluster"} onClose={() => setPanel(null)} data={cluster} />
      <MoreModal open={modalOpen} onClose={() => setModalOpen(false)} candidates={card_a.candidates} />
    </div>
  );
}
