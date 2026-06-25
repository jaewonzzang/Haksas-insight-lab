// 학생 이수 과목 예시 데이터 (사용자 실제 수강 목록, 중복 제거 34과목).
// ⚠️ 예시/임시: 추후 SAINT 연동 실데이터로 교체. id는 placeholder.
// taken_course_ids 처리 플로우 유지를 위해 {id, name} 구조 사용.

export interface TakenCourse {
  id: string;
  name: string;
}

export const takenCourses: TakenCourse[] = [
  { id: "T01", name: "인문사회글쓰기" },
  { id: "T02", name: "신학적인간학" },
  { id: "T03", name: "Data Visualization" },
  { id: "T04", name: "컴퓨터시스템개론" },
  { id: "T05", name: "자료구조" },
  { id: "T06", name: "컴퓨터아키텍쳐" },
  { id: "T07", name: "컴퓨터네트워크" },
  { id: "T08", name: "현대세계와윤리문제" },
  { id: "T09", name: "Intro to Creative Computing" },
  { id: "T10", name: "기초인공지능프로그래밍" },
  { id: "T11", name: "한류" },
  { id: "T12", name: "군이러닝취득교과목I" },
  { id: "T13", name: "군이러닝취득교과목II" },
  { id: "T14", name: "성찰과성장" },
  { id: "T15", name: "이산구조" },
  { id: "T16", name: "디지털회로개론" },
  { id: "T17", name: "JAVA언어" },
  { id: "T18", name: "Data&AI" },
  { id: "T19", name: "Fundamentals of Programming and Problem(Solving)" },
  { id: "T20", name: "고급응용C프로그래밍" },
  { id: "T21", name: "알바트로스세미나" },
  { id: "T22", name: "Intro to Korea thru Literature and Film" },
  { id: "T23", name: "인간과인성" },
  { id: "T24", name: "법과현대사회" },
  { id: "T25", name: "한국과세계" },
  { id: "T26", name: "철학산책" },
  { id: "T27", name: "자기브랜드리더십" },
  { id: "T28", name: "전략커뮤니케이션" },
  { id: "T29", name: "생명과환경" },
  { id: "T30", name: "대학수학" },
  { id: "T31", name: "영어글로벌의사소통I" },
  { id: "T32", name: "지식융합미디어입문" },
  { id: "T33", name: "Creativity & Visual Expression" },
  { id: "T34", name: "Critical Thinking for Social Inquiry" },
];
