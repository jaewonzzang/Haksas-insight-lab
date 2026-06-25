// 헤더 우측 "개요 PDF 다운로드". 브라우저 인쇄(→ PDF로 저장) 트리거.
// 인쇄 전용 스타일은 mockup.css의 @media print (버튼/패널 숨김, 경로 상세 펼침).

export default function PdfExportButton() {
  return (
    <button type="button" className="pdf-btn" onClick={() => window.print()}>
      개요 PDF 다운로드
    </button>
  );
}
