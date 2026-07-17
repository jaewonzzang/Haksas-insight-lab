"""card_c — 코호트 필터·라벨·기타 묶음·표기 규칙."""

from app.adapters.alumni_types import AlumniRecord, Major
from app.cards import card_c
from app.schemas.input import StudentInput


def _alum(aid, dept, extras):
    majors = [Major(label=dept, role="primary", credits=70.0)]
    for i, label in enumerate(extras):
        majors.append(Major(label=label, role=("double", "triple")[i], credits=40.0))
    return AlumniRecord(alumni_id=aid, department=dept, majors=majors)


STUDENT = StudentInput(student_id="S1", department="지식융합미디어학부")

# 코호트(합집합 매칭) 6명: 단일 3, 컴퓨터공학 2, 경영학 1 / 비코호트 1명
ALUMNI = (
    [_alum(f"s{i}", "아트&테크놀로지학과", []) for i in range(3)]
    + [_alum(f"c{i}", "신문방송학과", ["컴퓨터공학"]) for i in range(2)]
    + [_alum("b1", "미디어&엔터테인먼트학과", ["경영학"])]
    + [_alum("x1", "화학과", ["심리학"])]  # 코호트 밖 — 제외돼야 함
)


def test_cohort_filter_and_entries():
    card = card_c.build(STUDENT, ALUMNI)
    assert card.cohort_label == "지식융합미디어학부 · 졸업생 6명"
    top = card.entries[0]
    assert top.label == "단일전공 유지"
    assert top.tag == "최다"
    assert top.count == 3
    assert top.share_percent == 50
    assert top.bar_percent == 100
    assert "평균 이수 학점" in top.detail_label
    second = card.entries[1]
    assert second.label == "컴퓨터공학 (다전공)"
    assert second.tag is None
    assert "평균 추가 이수 학점" in second.detail_label
    assert card.baseline_note.startswith("추가전공은")


def test_fallback_to_all_when_no_cohort():
    student = StudentInput(student_id="S2", department="화학과")
    card = card_c.build(student, ALUMNI[:1])  # 아트&테크만 → 화학과 코호트 없음
    assert card.cohort_label == "전체 졸업생 1명"


def test_other_bucket_dim():
    alumni = ALUMNI[:6] + [
        _alum("e1", "신문방송학과", ["심리학"]),
        _alum("e2", "신문방송학과", ["데이터사이언스"]),
    ]
    card = card_c.build(STUDENT, alumni)
    other = card.entries[-1]
    assert other.dim is True
    # 실측: 그룹 5종(단일3·컴공2·경영1·데사1·심리1) → 동수(1) 사전순으로
    # 상위 4위 = 단일·컴공·경영학·데이터사이언스, rest = [심리학] 1그룹.
    assert other.label == "기타 경로 1건"
    assert other.count == 1
    assert other.credits.major1 is None


def test_empty_alumni():
    card = card_c.build(STUDENT, [])
    assert card.entries == []


def test_enrolled_students_excluded_from_pathway_distribution():
    """재학생은 다전공 선택 전이라 "단일전공 유지"로 잡혀 분포를 깎는다 (A17).

    실측: 경제학과 다전공률 21%(재학생 포함) → 43%(이력 완결자만).
    """
    student = StudentInput(student_id="S4", department="화학과")
    grad = _alum("g1", "화학과", ["경영학"])
    grad.history_complete = True
    enrolled = _alum("e1", "화학과", [])  # 1학년 — 아직 다전공 전
    enrolled.history_complete = False
    card = card_c.build(student, [grad, enrolled])
    assert card.cohort_label == "화학과 · 졸업생 1명"
    assert card.entries[0].label == "경영학 (다전공)"


def test_unknown_completion_passes_filter():
    """mock 은 history_complete 가 없다(None) — 데모가 깨지면 안 된다."""
    student = StudentInput(student_id="S5", department="화학과")
    rec = _alum("m1", "화학과", [])
    assert rec.history_complete is None
    assert card_c.build(student, [rec]).cohort_label == "화학과 · 졸업생 1명"


def test_cohort_matches_across_department_spelling():
    """수강내역 "X전공" 졸업생이 "X학과" 학생 코호트에 들어와야 한다 (2026-07-17).

    실데이터는 소속을 아트&테크놀로지전공/학과 두 표기로 적어 완전일치로는
    코호트가 쪼개졌다 (14,942명 중 5,036명 미매칭).
    """
    student = StudentInput(student_id="S3", department="아트&테크놀로지학과")
    alumni = [
        _alum("a1", "아트&테크놀로지학과", []),
        _alum("a2", "아트&테크놀로지전공", []),  # 같은 학과, 다른 표기
        _alum("x1", "화학과", []),  # 다른 학과 — 섞이면 안 됨
    ]
    card = card_c.build(student, alumni)
    assert card.cohort_label == "아트&테크놀로지학과 · 졸업생 2명"
