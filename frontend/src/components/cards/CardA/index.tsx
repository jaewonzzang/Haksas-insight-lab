// 카드 A — 추천 과목 (가로 2칸 결합, 전공/교양 2단). "왜 이 과목인가?" / "과목 더 보기".

import type { CardA as CardAData } from "../../../types/api";
import RecItem from "./RecItem";

interface Props {
  data: CardAData;
  onOpenWhy: () => void;
  onOpenMore: () => void;
}

export default function CardA({ data, onOpenWhy, onOpenMore }: Props) {
  return (
    <div className="card card-wide">
      <div className="card-header">
        <div className="card-title">추천 과목</div>
        <div className="card-meta">
          다음 학기 · 2026-2<br />
          <span className="engine-tag">하이브리드 추천 모델 · 교양은 트랙 필터 적용</span>
        </div>
      </div>

      <div className="rec-split">
        <div>
          <div className="rec-col-title">
            전공 추천 <span className="col-tag">MAJOR</span>
          </div>
          <div className="rec-list">
            {data.major.map((c) => (
              <RecItem key={c.course_id} course={c} />
            ))}
          </div>
        </div>
        <div>
          <div className="rec-col-title">
            교양 추천 <span className="col-tag">LIBERAL</span>
          </div>
          <div className="rec-list">
            {data.general.map((c) => (
              <RecItem key={c.course_id} course={c} />
            ))}
          </div>
        </div>
      </div>

      <div className="card-actions">
        <button type="button" className="btn-outline" onClick={onOpenWhy}>
          왜 이 과목인가?
        </button>
        <button type="button" className="btn-outline" onClick={onOpenMore}>
          과목 더 보기
        </button>
      </div>
    </div>
  );
}
