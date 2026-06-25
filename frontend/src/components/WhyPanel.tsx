// "왜?" 사이드 패널 — 과목별 추천 요소 기여도 분해 (mockup 데이터). 실제 출처는 OPEN_QUESTIONS A13.

import { scoreClass } from "../lib/courseDisplay";
import type { FactorKind, RecommendedCourse } from "../types/api";

function fillClass(kind: FactorKind): string {
  return kind === "na" ? "" : `contrib-${kind}`;
}

function kindLabel(course: RecommendedCourse): string {
  if (course.kind === "major") return "전공";
  return course.area_label ? `교양·${course.area_label}` : "교양";
}

function WhySection({ course }: { course: RecommendedCourse }) {
  return (
    <div className="why-section">
      <div className="why-course-head">
        <div className="why-course-name">
          {course.course_name} ({kindLabel(course)})
        </div>
        <div className={`why-course-score ${scoreClass(course.grade)}`}>
          {course.score_percent}
          <span className="pct">%</span>
        </div>
      </div>
      <div className="factor-list">
        {course.factors.map((f) => (
          <div key={f.label} className="factor">
            <div className="factor-label">{f.label}</div>
            <div className="factor-bar">
              <div className={`factor-fill ${fillClass(f.kind)}`} style={{ width: `${f.weight_percent}%` }} />
            </div>
            <div className="factor-val">{f.contribution}</div>
          </div>
        ))}
      </div>
      <div className="why-summary">
        <span className="label">한 줄 요약</span>
        {course.why_summary}
      </div>
    </div>
  );
}

interface Props {
  open: boolean;
  onClose: () => void;
  courses: RecommendedCourse[];
}

export default function WhyPanel({ open, onClose, courses }: Props) {
  const items = courses
    .filter((c) => c.factors.length > 0)
    .sort((a, b) => b.score_percent - a.score_percent);

  return (
    <>
      <div className={`panel-overlay${open ? " open" : ""}`} onClick={onClose} />
      <aside className={`side-panel${open ? " open" : ""}`}>
        <div className="panel-header">
          <div className="panel-title-block">
            <div className="panel-eyebrow">추천 사유</div>
            <h2 className="panel-title">왜 이 과목들이 추천되었는가</h2>
            <div className="panel-sub">하이브리드 추천 모델 · 6개 요소 가중 합 · 이수한 트랙은 자동 제외</div>
          </div>
          <button type="button" className="panel-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="panel-body">
          {items.map((c) => (
            <WhySection key={c.course_id} course={c} />
          ))}
        </div>
      </aside>
    </>
  );
}
