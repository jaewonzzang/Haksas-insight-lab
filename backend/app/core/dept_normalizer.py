"""학부 ↔ 학과 합집합 정규화.

원칙: DB는 원문 그대로. 추천 풀 산출 시점에만 합집합 적용.
예: 지식융합미디어학부 학생 → 지식융합미디어대학(14) + 미디어&엔터테인먼트학과(39) +
    아트&테크놀로지학과(35) + 신문방송학과(43) 합집합 (4학기 DB 실측 2026-07-06).
"""

# 학부명 → 추천 풀 학과 합집합 (courses.department 원문, 4학기 DB 실측 확인 2026-07-06).
# A4(시연 학과 범위) 확정 시 항목 추가.
DEPT_UNIONS: dict[str, list[str]] = {
    "지식융합미디어학부": [
        "지식융합미디어대학",
        "미디어&엔터테인먼트학과",
        "아트&테크놀로지학과",
        "신문방송학과",
    ],
}


def candidate_departments(student_dept: str) -> list[str]:
    """합집합 매핑이 있으면 그 목록(복사본), 없으면 원문 단일 목록."""
    return list(DEPT_UNIONS.get(student_dept, [student_dept]))
