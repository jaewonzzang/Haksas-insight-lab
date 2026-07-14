// 입력 화면 (page 2). mockup 체크박스 패널 + "분석" 버튼.
// 영역/선호 체크박스는 UI 수집용. 이수과목은 선택한 프로필 데이터에서 옴(여기서 안 받음).

import { useState, type FormEvent } from "react";

import BrandHeader from "./BrandHeader";
import type { AnalysisForm } from "../lib/useAnalysis";

interface Props {
  onSubmit: (form: AnalysisForm) => void;
  onBack: () => void;
}

const COMMON_AREAS = [
  { label: "① 인간과 신앙", on: true },
  { label: "② 인간과 사상", on: true },
  { label: "③ 인간과 사회", on: true },
  { label: "④ 인간과 과학 & AI", on: false },
];
const FREE_AREAS = [
  { label: "봉사·리더십", on: false },
  { label: "과학·기술 & AI", on: true },
  { label: "언어·문화", on: true },
  { label: "고전·문학", on: false },
  { label: "예술·체육", on: true },
  { label: "신앙의 이해", on: false },
  { label: "사회·인간", on: true },
  { label: "윤리·사상", on: false },
  { label: "문명·역사", on: false },
];
const PREFS = [
  { key: "prefer_team_project", label: "팀플레이 선호" },
  { key: "prefer_su_eval", label: "S/U 평가 선호" },
  { key: "prefer_low_attendance", label: "출석 비중 낮음 선호" },
  { key: "prefer_presentation", label: "발표 있는 과목 선호" },
] as const;
const CAREERS = ["대학원", "취업", "미정"] as const;

function StaticChk({ label, defaultChecked }: { label: string; defaultChecked?: boolean }) {
  return (
    <label className="chk">
      <input type="checkbox" defaultChecked={defaultChecked} />
      <span className="box" />
      <span className="label">{label}</span>
    </label>
  );
}

function PickChk({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="chk">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="box" />
      <span className="label">{label}</span>
    </label>
  );
}

export default function InputScreen({ onSubmit, onBack }: Props) {
  const [career, setCareer] = useState<(typeof CAREERS)[number]>("대학원");
  const [multimajor, setMultimajor] = useState<"yes" | "no">("yes");
  const [prefs, setPrefs] = useState<Record<(typeof PREFS)[number]["key"], boolean>>({
    prefer_team_project: true,
    prefer_su_eval: true,
    prefer_low_attendance: true,
    prefer_presentation: true,
  }); // 기존 defaultChecked(전부 켬)와 동일한 초기값

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit({
      interest_career: career === "미정" ? null : career,
      consider_multimajor: multimajor === "yes",
      ...prefs,
    });
  }

  return (
    <div className="page">
      <BrandHeader
        subtitle="학업 분석 입력 · 2026-1학기"
        right={
          <button type="button" className="pdf-btn" onClick={onBack}>
            ← 프로필
          </button>
        }
      />
      <form onSubmit={handleSubmit}>
        <div className="input-panel">
          <div className="input-head">
            <div className="input-title">분석 입력값</div>
          </div>
          <div className="input-body">
            <div className="input-group">
              <div className="input-group-label">공통선택 이수 영역 (이수한 영역만 체크)</div>
              <div className="check-row">
                {COMMON_AREAS.map((a) => (
                  <StaticChk key={a.label} label={a.label} defaultChecked={a.on} />
                ))}
              </div>
              <div className="chk-note">이수한 영역은 추천에서 자동 제외됩니다.</div>
            </div>

            <div className="input-group">
              <div className="input-group-label">자유선택 관심 영역 (희망 영역 체크)</div>
              <div className="check-row">
                {FREE_AREAS.map((a) => (
                  <StaticChk key={a.label} label={a.label} defaultChecked={a.on} />
                ))}
              </div>
            </div>

            <div className="input-group">
              <div className="input-group-label">추가 선호</div>
              <div className="check-row">
                {PREFS.map((p) => (
                  <PickChk
                    key={p.key}
                    label={p.label}
                    checked={prefs[p.key]}
                    onChange={() => setPrefs((s) => ({ ...s, [p.key]: !s[p.key] }))}
                  />
                ))}
              </div>
              <div className="input-group-label" style={{ marginTop: 14 }}>
                관심 진로
              </div>
              <div className="check-row">
                {CAREERS.map((c) => (
                  <PickChk key={c} label={c} checked={career === c} onChange={() => setCareer(c)} />
                ))}
              </div>
              <div className="input-group-label" style={{ marginTop: 14 }}>
                다전공 고려
              </div>
              <div className="check-row">
                <PickChk label="예" checked={multimajor === "yes"} onChange={() => setMultimajor("yes")} />
                <PickChk label="아니오" checked={multimajor === "no"} onChange={() => setMultimajor("no")} />
              </div>
            </div>
          </div>
        </div>

        <div className="input-actions">
          <button type="submit" className="analyze-btn">
            분석
          </button>
        </div>
      </form>
    </div>
  );
}
