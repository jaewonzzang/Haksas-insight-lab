"""학생 입력 Pydantic 모델 (POST /analyze 요청).

SAINT 연계 시 자동 채워지는 필드 + 사용자가 직접 선택하는 필드의 통합.
실제 필드 목록은 UI 입력 폼 + 학사 시스템 명세 확정 후 잠금.
"""

from pydantic import BaseModel, Field


class StudentInput(BaseModel):
    student_id: str = Field(..., description="학번")
    department: str = Field(..., description="학과/학부 원문 그대로")
    extra_majors: list[str] = Field(
        default_factory=list, description="복수전공 학과/학부 원문 목록"
    )
    taken_course_ids: list[str] = Field(default_factory=list, description="이수 완료 과목 ID")
    interest_career: str | None = Field(None, description="관심 진로 (드롭다운)")
    consider_multimajor: bool = Field(False, description="다전공 고려 여부")
    # TODO: 공통선택 교양 4영역 체크, 자유선택 9영역 관심,
    #       팀플/S·U/출석 비중 선호 — UI 폼 확정 후 추가
