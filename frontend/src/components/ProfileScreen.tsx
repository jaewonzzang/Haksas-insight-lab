// 데모 프로필 선택 화면 (page 1). 프로필별 요약 카드 (학생 A만 실데이터, B~D는 빈 공간).

import type { DemoProfile } from "../mock/profiles.fixture";
import BrandHeader from "./BrandHeader";

interface Props {
  profiles: DemoProfile[];
  onSelect: (profile: DemoProfile) => void;
}

export default function ProfileScreen({ profiles, onSelect }: Props) {
  return (
    <div className="page">
      <BrandHeader subtitle="데모 프로필 선택 · 2026-1학기" />
      <p className="profile-hint">분석할 학생 프로필을 선택하세요.</p>
      <div className="profile-grid">
        {profiles.map((p) => (
          <div key={p.id} className="profile-card" onClick={() => onSelect(p)}>
            <div className="profile-card-name">{p.label}</div>
            <div className="profile-card-row">
              <span className="k">학과</span>
              <span className="v">{p.available ? p.dashboard.profile.department : "—"}</span>
            </div>
            <div className="profile-card-row">
              <span className="k">학년</span>
              <span className="v">{p.available ? p.dashboard.profile.year : "—"}</span>
            </div>
            <div className="profile-card-row">
              <span className="k">이수 학점</span>
              <span className="v">{p.available ? `${p.dashboard.kpi.earned_credits}학점` : "—"}</span>
            </div>
            <div className="profile-card-row">
              <span className="k">이수 과목</span>
              <span className="v">{p.available ? `${p.takenCourses.length}과목` : "—"}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
