"""카드 C 오케스트레이터: 코호트 → 다전공 분포 집계 → CardC.

라벨/문구는 결정론 조립 (W5 LLM 통역 대상 아님 — 카드 C는 정형 표기만).
"""

from app.adapters.alumni_types import AlumniRecord
from app.core.dept_normalizer import candidate_departments
from app.engines.pathway.distribution import PathwayGroup, aggregate
from app.schemas.cards import CardC, PathwayCredits, PathwayEntry
from app.schemas.input import StudentInput

TOP_GROUPS = 4

BASELINE_NOTE = (
    "추가전공은 주 전공을 포함하여 제3전공까지 이수할 수 있다 · "
    "연계전공·학생설계전공의 이수학점은 36학점 이상을 원칙으로 한다 · "
    "심화전공은 전공 60학점 이상 이수함을 원칙으로 한다 · "
    "다전공 이수로 전공간 이수과목이 중복된 경우 6학점 이내에서 중복 인정될 수 있으며, "
    "본인의 학점 인정 사항은 소속 학과 협의에 따른다."
)


def _label(group: PathwayGroup) -> str:
    if not group.extra_majors:
        return "단일전공 유지"
    if len(group.extra_majors) == 1:
        return f"{group.extra_majors[0]} (다전공)"
    return f"{' + '.join(group.extra_majors)} (3전공)"


def build(student: StudentInput, alumni: list[AlumniRecord]) -> CardC:
    depts = {student.department, *candidate_departments(student.department)}
    cohort = [r for r in alumni if r.department in depts]
    if cohort:
        cohort_label_prefix = student.department
    else:
        cohort = list(alumni)
        cohort_label_prefix = "전체"
    label = (
        f"{cohort_label_prefix} · 졸업생 {len(cohort)}명"
        if cohort_label_prefix != "전체"
        else f"전체 졸업생 {len(cohort)}명"
    )
    if not cohort:
        return CardC(cohort_label=label, entries=[], baseline_note=BASELINE_NOTE)

    groups = aggregate(cohort)
    total = len(cohort)
    max_count = groups[0].count
    top, rest = groups[:TOP_GROUPS], groups[TOP_GROUPS:]

    entries: list[PathwayEntry] = []
    for i, g in enumerate(top):
        detail_noun = "평균 이수 학점" if not g.extra_majors else "평균 추가 이수 학점"
        entries.append(
            PathwayEntry(
                id=f"p{i + 1}",
                label=_label(g),
                tag="최다" if i == 0 else None,
                count=g.count,
                share_percent=round(g.count / total * 100),
                bar_percent=round(g.count / max_count * 100),
                detail_label=f"이 경로 졸업생 {g.count}명의 {detail_noun}",
                credits=PathwayCredits(
                    major1=g.avg_primary_credits,
                    major2=g.avg_second_credits,
                    major3=g.avg_third_credits,
                ),
            )
        )
    if rest:
        rest_count = sum(g.count for g in rest)
        entries.append(
            PathwayEntry(
                id="other",
                label=f"기타 경로 {len(rest)}건",
                count=rest_count,
                share_percent=round(rest_count / total * 100),
                bar_percent=round(rest_count / max_count * 100),
                detail_label="",
                credits=PathwayCredits(major1=None, major2=None, major3=None),
                dim=True,
            )
        )
    return CardC(cohort_label=label, entries=entries, baseline_note=BASELINE_NOTE)
