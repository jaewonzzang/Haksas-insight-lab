// 분석 실패 화면. 재시도는 입력 화면으로 복귀.

import BrandHeader from "./BrandHeader";

interface Props {
  message: string;
  onRetry: () => void;
  onReset: () => void;
}

export default function ErrorScreen({ message, onRetry, onReset }: Props) {
  return (
    <div className="page">
      <BrandHeader subtitle="분석 실패" />
      <div className="input-panel">
        <div className="input-body">
          <p>분석 요청에 실패했습니다: {message}</p>
          <p>백엔드 서버 상태를 확인하거나 다시 시도해 주세요.</p>
        </div>
      </div>
      <div className="input-actions">
        <button type="button" className="analyze-btn" onClick={onRetry}>
          다시 입력
        </button>
        <button type="button" className="pdf-btn" onClick={onReset}>
          처음으로
        </button>
      </div>
    </div>
  );
}
