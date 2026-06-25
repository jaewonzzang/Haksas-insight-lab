// 공용 브랜드 헤더 (입력 화면 / 대시보드 공유). 로고 + Saint+ 타이틀.

import type { ReactNode } from "react";

interface Props {
  subtitle: string;
  right?: ReactNode;
}

export default function BrandHeader({ subtitle, right }: Props) {
  return (
    <div className="header">
      <div className="header-left">
        <img className="brand-logo" src="/logo_sogang.png" alt="서강대학교" />
        <div className="title-divider" />
        <div className="title-block">
          <h1 className="title">Saint+</h1>
          <div className="subtitle">{subtitle}</div>
        </div>
      </div>
      {right && <div className="header-right">{right}</div>}
    </div>
  );
}
