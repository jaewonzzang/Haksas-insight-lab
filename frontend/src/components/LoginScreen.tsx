// SAINT 로그인 화면 (page 0). 데모 진입 훅 — 서강대 통합 로그인 모사.
// 실제 인증 없음: 더미 학번/비밀번호 프리필, 로그인 → 짧은 전환 후 프로필 선택으로.

import { useState, type FormEvent } from "react";

interface Props {
  onLogin: () => void;
}

export default function LoginScreen({ onLogin }: Props) {
  const [submitting, setSubmitting] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setTimeout(onLogin, 700); // 로그인 전환 연출 (데모 녹화용). 실제 인증 아님.
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={handleSubmit}>
        <img className="login-logo" src="/logo_sogang.png" alt="서강대학교" />
        <h1 className="login-title">SAINT</h1>
        <div className="login-sub">서강대학교 통합정보시스템</div>
        <label className="login-field">
          <span className="login-label">학번</span>
          <input className="login-input" type="text" defaultValue="20211234" autoComplete="off" />
        </label>
        <label className="login-field">
          <span className="login-label">비밀번호</span>
          <input className="login-input" type="password" defaultValue="demo1234" autoComplete="off" />
        </label>
        <button type="submit" className="analyze-btn login-btn" disabled={submitting}>
          {submitting ? <span className="login-btn-spinner" /> : "로그인"}
        </button>
        <div className="login-foot">Saint+ · 학업 분석 데모</div>
      </form>
    </div>
  );
}
