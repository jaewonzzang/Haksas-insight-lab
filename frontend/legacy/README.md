# Legacy 프로토타입 보존

단일 HTML + CSS + JS 파일로 작성된 기존 Netlify 프로토타입을 그대로 보존하는 폴더.

- 빌드 대상이 아님 (vite content 패턴에서 제외).
- 디자인·인터랙션 참조용. 색상·간격·뱃지 스타일 등 토큰은 `frontend/src/styles/tokens.ts`로 이미 추출되었다.
- 컴포넌트 단위로 React 포팅하는 작업은 `frontend/src/components/`에서 새로 작성한다 (직접 이식 X).

배포된 원본: https://iridescent-daifuku-63a665.netlify.app/
