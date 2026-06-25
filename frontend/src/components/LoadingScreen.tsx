// 흰 로딩 화면: 중앙 스피너 + "분석 중".

export default function LoadingScreen() {
  return (
    <div className="loading-screen">
      <div className="loading-spinner" />
      <div className="loading-text">분석 중</div>
    </div>
  );
}
