// "과목 더 보기" 풀스크린 모달 — 후보 전체 + 구분/뱃지/정렬 필터.

import { useState } from "react";

import { badgeClass, badgeKey, scoreClass } from "../lib/courseDisplay";
import type { CourseKind, RecommendedCourse } from "../types/api";

type KindFilter = "all" | CourseKind;
type BadgeFilter = "all" | "strong" | "consider" | "hold";
type SortKey = "score" | "credit";

const KIND_PILLS: { value: KindFilter; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "major", label: "전공" },
  { value: "common", label: "공통선택" },
  { value: "free", label: "자유선택" },
];
const BADGE_PILLS: { value: BadgeFilter; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "strong", label: "강추" },
  { value: "consider", label: "고려" },
  { value: "hold", label: "유보" },
];
const SORT_PILLS: { value: SortKey; label: string }[] = [
  { value: "score", label: "추천도순" },
  { value: "credit", label: "학점순" },
];

function Pills<T extends string>({
  label,
  value,
  set,
  pills,
}: {
  label: string;
  value: T;
  set: (v: T) => void;
  pills: { value: T; label: string }[];
}) {
  return (
    <div className="filter-group">
      <span className="filter-label">{label}</span>
      {pills.map((p) => (
        <button
          key={p.value}
          type="button"
          className={`filter-pill${value === p.value ? " active" : ""}`}
          onClick={() => set(p.value)}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

interface Props {
  open: boolean;
  onClose: () => void;
  candidates: RecommendedCourse[];
}

export default function MoreModal({ open, onClose, candidates }: Props) {
  const [kind, setKind] = useState<KindFilter>("all");
  const [badge, setBadge] = useState<BadgeFilter>("all");
  const [sort, setSort] = useState<SortKey>("score");

  const rows = candidates
    .filter((c) => kind === "all" || c.kind === kind)
    .filter((c) => badge === "all" || badgeKey(c.grade) === badge)
    .slice()
    .sort((a, b) =>
      sort === "credit" ? (b.credit ?? 0) - (a.credit ?? 0) : b.score_percent - a.score_percent,
    );

  return (
    <div
      className={`modal-overlay${open ? " open" : ""}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title-block">
            <div className="modal-eyebrow">2026-2학기 개설 과목</div>
            <h2 className="modal-title">추천 과목 후보 전체</h2>
            <div className="modal-sub">개설 예정 47개 과목 · 추천도 60% 이상 표시 · 이수한 영역 자동 제외</div>
          </div>
          <button type="button" className="panel-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-toolbar">
          <Pills label="구분" value={kind} set={setKind} pills={KIND_PILLS} />
          <div className="filter-divider" />
          <Pills label="뱃지" value={badge} set={setBadge} pills={BADGE_PILLS} />
          <div className="filter-divider" />
          <Pills label="정렬" value={sort} set={setSort} pills={SORT_PILLS} />
        </div>

        <div className="modal-body">
          <table className="courses-table">
            <thead>
              <tr>
                <th className="center" style={{ width: 80 }}>
                  추천도
                </th>
                <th>과목명</th>
                <th className="center">구분</th>
                <th className="center">학점</th>
                <th className="center">뱃지</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.course_id}>
                  <td className="center">
                    <span className={`score-cell ${scoreClass(c.grade)}`} style={{ fontSize: 15, fontWeight: 700 }}>
                      {c.score_percent}%
                    </span>
                  </td>
                  <td>
                    <div className="course-row-name">{c.course_name}</div>
                    <div className="course-row-code">
                      {c.course_id}
                      {c.area_label ? ` · ${c.area_label}` : ""}
                    </div>
                  </td>
                  <td className="center">{c.kind_label}</td>
                  <td className="right">{c.credit}</td>
                  <td className="center">
                    <span className={`badge ${badgeClass(c.grade)}`}>{c.grade}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
