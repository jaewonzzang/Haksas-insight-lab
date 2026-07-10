// 학생 A 이수 과목 (사용자 실제 수강 목록, 중복 제거 34과목).
// id = 실 DB course_id (2026-07-10 s_compass_courses.db 실측 매핑).
// - 동일 과목명 다중 id는 CSE(컴퓨터공학과) 개설 우선.
// - 알바트로스세미나 = 학생 A 소속 분반 COR1021(지식융합미디어).
// - 군이러닝 2건(T12·T13)은 DB 부재 — placeholder 유지, 백엔드가 무시.

export interface TakenCourse {
  id: string;
  name: string;
}

export const takenCourses: TakenCourse[] = [
  { id: "COR1012", name: "인문사회글쓰기" },
  { id: "HFS2002", name: "신학적인간학" },
  { id: "AAT3019", name: "Data Visualization" },
  { id: "CSE3030", name: "컴퓨터시스템개론" },
  { id: "CSE3080", name: "자료구조" },
  { id: "CSE4010", name: "컴퓨터아키텍쳐" },
  { id: "CSE4175", name: "컴퓨터네트워크" },
  { id: "ETS2001", name: "현대세계와윤리문제" },
  { id: "AAT2004", name: "Intro to Creative Computing" },
  { id: "COR1010", name: "기초인공지능프로그래밍" },
  { id: "MAS2003", name: "한류" },
  { id: "T12", name: "군이러닝취득교과목I" },
  { id: "T13", name: "군이러닝취득교과목II" },
  { id: "COR1007", name: "성찰과성장" },
  { id: "CSE3006", name: "이산구조" },
  { id: "CSE3015", name: "디지털회로개론" },
  { id: "CSE3040", name: "JAVA언어" },
  { id: "MAS1004", name: "Data&AI" },
  { id: "MAS2008", name: "Fundamentals of Programming and Problem Solving" },
  { id: "STS2008", name: "고급응용C프로그래밍" },
  { id: "COR1021", name: "알바트로스세미나" },
  { id: "GKS3002", name: "Intro to Korea thru Literature and Film" },
  { id: "HSS3001", name: "인간과인성" },
  { id: "PUB2005", name: "법과현대사회" },
  { id: "SHS2002", name: "한국과세계" },
  { id: "ETS2003", name: "철학산책" },
  { id: "LED3015", name: "자기브랜드리더십" },
  { id: "MAS2002", name: "전략커뮤니케이션" },
  { id: "STS2002", name: "생명과환경" },
  { id: "STS2004", name: "대학수학" },
  { id: "COR1003", name: "영어글로벌의사소통I" },
  { id: "MAS1001", name: "지식융합미디어입문" },
  { id: "MAS1002", name: "Creativity & Visual Expression" },
  { id: "GKS1001", name: "Critical Thinking for Social Inquiry" },
];
