"""A5: 추천 가중치 홀드아웃 평가·그리드 튜닝 (분석 도구 — 런타임 미사용).

각 학생의 **마지막 정규학기를 숨기고**, 이전 이력으로 StudentInput 을 구성해
추천 순위(card_a.collect → rank)가 숨긴 학기의 실제 수강을 얼마나 맞히는지 잰다.

설계:
  - 표본: 정규학기 4개+ 학생 중 시드(42) 셔플 상위 N명. 홀짝 인덱스로 tune/valid 이분.
  - 정답: 숨긴 학기 수강 과목(별칭 확장) ∩ 추천 풀. 풀 밖 과목(폐강 등)은 채점 대상 아님.
  - 지표: Recall@8(카드 노출 4+4), Recall@20(후보 캡), MRR. 순위 tie-break = (−점수, 과목ID).
  - 학년: 완료 정규학기 수 // 2 + 1 (cap 4) — enrollment_inference 원칙.
  - 누수 방지: 평가 대상 학생은 코호트(alumni)에서 제외(leave-one-out).
  - 그리드: 코호트·콘텐츠·학년 {0.05..0.40}. **선호 매칭 0.15 고정** — 졸업생 이력에
    선호 입력이 없어 튜닝 정답이 없다(신호 부재 시 재정규화로 평가에서 자동 제외).

한계 (해석 시 주의):
  - 정답은 "수강했다"까지 — 만족/도움 여부는 없다.
  - 타 학생의 미래(숨긴 시점 이후) 이력은 코호트에 남는다(시점 절단 아님).
  - 동계 계절학기(term=None)는 정렬상 2학기 앞에 놓여 taken 에 소수 혼입 가능
    (정답은 정규학기라 오염 없음).
  - 추천 풀은 현행 개설(course_offerings) 기준 — 과거 학기의 실제 개설과 다를 수 있다.

실행 (backend/):
  uv run python scripts/evaluate_recommender.py --sample 400          # baseline + 컷오프 버킷
  uv run python scripts/evaluate_recommender.py --sample 400 --grid   # 가중치 그리드
"""

import argparse
import json
import random
import sqlite3
import sys
import time
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.adapters.alumni_types import AlumniRecord, Enrollment
from app.cards import card_a
from app.core.alias_resolver import expand_taken
from app.db.queries import course_queries
from app.engines.recommender import weights
from app.schemas.input import StudentInput

SEED = 42
MIN_REGULAR_SEMESTERS = 4  # 이전 이력 3학기 + 숨긴 학기 1
GRID_VALUES = [round(0.05 * i, 2) for i in range(1, 9)]  # 0.05 ~ 0.40
PREF_LABEL, PREF_FIXED = "사용자 선호 매칭", 0.15


def _regular(items: list[Enrollment]) -> list[tuple[int, int]]:
    return sorted({(e.year_taken, e.term_taken) for e in items if e.term_taken})


def _key(year: int, term: int | None) -> tuple[int, float]:
    return (year, term if term is not None else 1.5)


def make_case(rec: AlumniRecord) -> tuple[StudentInput, int, set[str]] | None:
    sems = _regular(rec.enrollment)
    if len(sems) < MIN_REGULAR_SEMESTERS:
        return None
    hidden = sems[-1]
    truth = {e.course_id for e in rec.enrollment if (e.year_taken, e.term_taken) == hidden}
    taken = {e.course_id for e in rec.enrollment if _key(e.year_taken, e.term_taken) < _key(*hidden)}
    if not taken or not truth:
        return None
    student = StudentInput(
        student_id=rec.alumni_id,
        department=rec.department,
        extra_majors=[
            m.label for m in rec.majors
            if m.role in ("double", "triple") and m.label != rec.department
        ],
        year=min(4, (len(sems) - 1) // 2 + 1),
        taken_course_ids=sorted(taken),
    )
    return student, hidden[1], truth


def collect_cases(records: list[AlumniRecord], sample: int, con: sqlite3.Connection):
    aliases = [tuple(r) for r in course_queries.list_aliases(con)]
    eligible = [r for r in records if len(_regular(r.enrollment)) >= MIN_REGULAR_SEMESTERS]
    rng = random.Random(SEED)
    rng.shuffle(eligible)

    cases: list[tuple[card_a.Collected, set[str]]] = []
    skip_pool = skip_truth = 0
    for rec in eligible[:sample]:
        mc = make_case(rec)
        if mc is None:
            continue
        student, term, truth_raw = mc
        others = [a for a in records if a.alumni_id != rec.alumni_id]
        col = card_a.collect(student, con, others, target_semester=term)
        pool_ids = {r["course_id"] for r in (*col.major_pool, *col.general_pool)}
        if not pool_ids:
            skip_pool += 1
            continue
        truth = expand_taken(truth_raw, aliases) & pool_ids
        if not truth:
            skip_truth += 1
            continue
        cases.append((col, truth))
    print(f"적격 {len(eligible):,}명 중 표본 {min(sample, len(eligible))}명 → "
          f"케이스 {len(cases)} (스킵: 풀없음 {skip_pool}, 풀내정답없음 {skip_truth})")
    return cases


def evaluate(cases) -> tuple[float, float, float]:
    r8s, r20s, mrrs = [], [], []
    for col, truth in cases:
        scored = card_a.rank(col)
        ranked = sorted(scored, key=lambda cid: (-scored[cid].score_percent, cid))
        hits = [i for i, cid in enumerate(ranked) if cid in truth]
        r8s.append(sum(1 for i in hits if i < 8) / len(truth))
        r20s.append(sum(1 for i in hits if i < 20) / len(truth))
        mrrs.append(1 / (hits[0] + 1) if hits else 0.0)
    n = len(cases) or 1
    return sum(r8s) / n, sum(r20s) / n, sum(mrrs) / n


def set_weights(cohort: float, content: float, year: float) -> None:
    weights.FACTOR_WEIGHTS.clear()
    weights.FACTOR_WEIGHTS.update({
        "코호트 선호도": cohort,
        "콘텐츠 유사도": content,
        PREF_LABEL: PREF_FIXED,
        "학년 적합도": year,
    })


def bucket_report(cases) -> None:
    """등급 버킷별 적중률 P(실제 수강 | 등급) — 컷오프 캘리브레이션."""
    stats: dict[str, list[int]] = {"강추": [0, 0], "고려": [0, 0], "유보": [0, 0]}
    for col, truth in cases:
        for cid, sc in card_a.rank(col).items():
            stats[sc.grade][0] += 1
            stats[sc.grade][1] += cid in truth
    print("| 등급 | 후보 수 | 실제 수강 | 적중률 |")
    print("|---|---|---|---|")
    for grade, (n, hit) in stats.items():
        rate = f"{hit / n * 100:.1f}%" if n else "—"
        print(f"| {grade} | {n:,} | {hit:,} | {rate} |")


def run_grid(cases) -> None:
    tune, valid = cases[0::2], cases[1::2]
    print(f"tune {len(tune)} / valid {len(valid)} 케이스")

    baseline = dict(weights.FACTOR_WEIGHTS)
    results, seen = [], set()
    t0 = time.time()
    for c1, c2, c3 in product(GRID_VALUES, repeat=3):
        ratio = tuple(round(v / (c1 + c2 + c3), 3) for v in (c1, c2, c3))
        if ratio in seen:  # 재정규화로 비율 동치 구성은 결과 동일
            continue
        seen.add(ratio)
        set_weights(c1, c2, c3)
        results.append((evaluate(tune), (c1, c2, c3)))
    print(f"그리드 {len(results)} 구성, {time.time() - t0:.0f}s")

    results.sort(key=lambda x: (-x[0][0], -x[0][2], x[1]))
    print("\n| 구성 (코호트/콘텐츠/학년) | tune R@8 | tune R@20 | tune MRR | valid R@8 | valid R@20 | valid MRR |")
    print("|---|---|---|---|---|---|---|")
    rows = [(baseline["코호트 선호도"], baseline["콘텐츠 유사도"], baseline["학년 적합도"])]
    rows += [cfg for _, cfg in results[:10]]
    for i, (c1, c2, c3) in enumerate(rows):
        set_weights(c1, c2, c3)
        t = evaluate(tune)
        v = evaluate(valid)
        tag = " (baseline)" if i == 0 else ""
        print(f"| {c1}/{c2}/{c3}{tag} | {t[0]:.3f} | {t[1]:.3f} | {t[2]:.3f} "
              f"| {v[0]:.3f} | {v[1]:.3f} | {v[2]:.3f} |")

    weights.FACTOR_WEIGHTS.clear()
    weights.FACTOR_WEIGHTS.update(baseline)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔에서 —·표 문자 깨짐 방지
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=400)
    ap.add_argument("--grid", action="store_true")
    args = ap.parse_args()

    records = [
        AlumniRecord.model_validate(o)
        for o in json.loads(config.ALUMNI_REAL_PATH.read_text("utf-8"))
    ]
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        t0 = time.time()
        cases = collect_cases(records, args.sample, con)
        print(f"신호 수집 {time.time() - t0:.0f}s")
        if args.grid:
            run_grid(cases)
        else:
            r8, r20, mrr = evaluate(cases)
            print(f"\nbaseline (weights.py 현행): Recall@8 {r8:.3f} · Recall@20 {r20:.3f} · MRR {mrr:.3f}")
            print("\n[컷오프 버킷 — 전체 케이스]")
            bucket_report(cases)
    finally:
        con.close()


if __name__ == "__main__":
    main()
