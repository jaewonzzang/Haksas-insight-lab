// 단일 추천 항목 (전공/교양 공통). 추천도% + 과목명/과목코드 + 등급 뱃지.
// 사유 문구는 표시하지 않는다 (2026-07-12 사용자 요청 — 코드만 표기).
// 강의계획서 PDF 링크는 백엔드가 파일 실재 시에만 채움 — 없으면 미표시.

import { BASE_URL } from "../../../lib/api";
import { badgeClass, scoreClass } from "../../../lib/courseDisplay";
import type { RecommendedCourse } from "../../../types/api";

interface Props {
  course: RecommendedCourse;
}

export default function RecItem({ course }: Props) {
  return (
    <div className="rec-item">
      <div className={`rec-score ${scoreClass(course.grade)}`}>
        {course.score_percent}
        <span className="pct">%</span>
      </div>
      <div>
        <div className="rec-name">{course.course_name}</div>
        <div className="rec-reason">
          {course.course_id}
          {course.syllabus_url && (
            <a
              className="rec-pdf"
              href={`${BASE_URL}${course.syllabus_url}`}
              target="_blank"
              rel="noreferrer"
              title="강의계획서 PDF"
            >
              계획서
            </a>
          )}
        </div>
      </div>
      <div className={`badge ${badgeClass(course.grade)}`}>{course.grade}</div>
    </div>
  );
}
