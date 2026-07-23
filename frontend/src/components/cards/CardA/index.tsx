// 카드 A — 추천 과목 (가로 2칸 결합, 전공/교양 2단). "왜 이 과목인가?" / "과목 더 보기".
// 이수구분(성격) 필터: 체크 없으면 기본 상위 4+4, 체크 시 후보 풀에서 해당 구분만 상위 4씩.

import { useMemo, useState } from "react";

import type { CardA as CardAData, RecommendedCourse } from "../../../types/api";
import RecItem from "./RecItem";

const TOP_N = 4;
const CAT_ORDER = ["전공입문", "전공필수", "전공선택", "학부공통", "교양", "자유선택"];

interface Props {
  data: CardAData;
  onOpenWhy: () => void;
  onOpenMore: () => void;
}

// 상위 목록 + 후보 목록(각각 점수순) 순서 유지 합집합 — 필터로 상위가 비면 후보에서 채운다.
function mergeRanked(top: RecommendedCourse[], candidates: RecommendedCourse[]): RecommendedCourse[] {
  const seen = new Set(top.map((c) => c.course_id));
  return [...top, ...candidates.filter((c) => !seen.has(c.course_id))];
}

export default function CardA({ data, onOpenWhy, onOpenMore }: Props) {
  const [checked, setChecked] = useState<string[]>([]);

  const available = useMemo(() => {
    const all = new Set(
      [...data.major, ...data.general, ...data.candidates].flatMap((c) => c.categories ?? []),
    );
    return CAT_ORDER.filter((c) => all.has(c));
  }, [data]);

  const pass = (c: RecommendedCourse) =>
    checked.length === 0 || (c.categories ?? []).some((cat) => checked.includes(cat));

  const majorList = mergeRanked(data.major, data.candidates.filter((c) => c.kind === "major"))
    .filter(pass)
    .slice(0, TOP_N);
  const generalList = mergeRanked(data.general, data.candidates.filter((c) => c.kind === "free"))
    .filter(pass)
    .slice(0, TOP_N);

  const toggle = (cat: string) =>
    setChecked((s) => (s.includes(cat) ? s.filter((c) => c !== cat) : [...s, cat]));

  return (
    <div className="card card-wide">
      <div className="card-header">
        <div className="card-title">추천 과목</div>
        <div className="card-meta">
          다음 학기 · 2026-2<br />
          <span className="engine-tag">하이브리드 추천 모델 · 교양은 트랙 필터 적용</span>
        </div>
      </div>

      {available.length > 0 && (
        <div className="rec-filter check-row">
          <span className="rec-filter-label">이수구분</span>
          {available.map((cat) => (
            <label key={cat} className="chk">
              <input type="checkbox" checked={checked.includes(cat)} onChange={() => toggle(cat)} />
              <span className="box" />
              <span className="label">{cat}</span>
            </label>
          ))}
        </div>
      )}

      <div className="rec-split">
        <div>
          <div className="rec-col-title">
            전공 추천 <span className="col-tag">MAJOR</span>
          </div>
          <div className="rec-list">
            {majorList.map((c) => (
              <RecItem key={c.course_id} course={c} />
            ))}
            {majorList.length === 0 && <div className="rec-empty">선택한 이수구분의 추천 과목 없음</div>}
          </div>
        </div>
        <div>
          <div className="rec-col-title">
            교양 추천 <span className="col-tag">LIBERAL</span>
          </div>
          <div className="rec-list">
            {generalList.map((c) => (
              <RecItem key={c.course_id} course={c} />
            ))}
            {generalList.length === 0 && <div className="rec-empty">선택한 이수구분의 추천 과목 없음</div>}
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
