# S-Compass Frontend

Vite + React 18 + TypeScript + Tailwind.

- 진입점: `src/main.tsx` → `App.tsx` → `pages/Dashboard.tsx`
- API 클라이언트: `src/lib/api.ts` (백엔드 `POST /analyze` 호출)
- 타입: `src/types/api.ts` ← 백엔드 `backend/app/schemas/`와 동기화 필요
- 디자인 토큰: `src/styles/tokens.ts` (Tailwind theme.extend에 등록)
- 프로토타입 원본: `legacy/` (빌드 제외, 참조용)

## 개발 실행 (예정)

```
npm install
npm run dev
```

## 빌드

```
npm run build
```

## 디자인 원칙

- 흰색 배경 + 서강 빨강(#B8242C) 포인트만.
- 의미 색상 유지: 강추=녹색, 대학원=보라, 위험=황색.
- 그라데이션/드롭섀도/블러 금지.
- PC 우선 (4×4 그리드 활용), 모바일 1열 스택.
