"""schema.sql 6테이블과 1:1 대응하는 빌드 타임 행(row) 모델.

파서가 생성하는 단위. INSERT 직전 검증 역할.

API 응답 모델 (cards.py, input.py) 과 구분되는 빌드 타임 전용 모델.
"""

import json
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CourseRow(BaseModel):
    """courses 테이블 행."""

    model_config = ConfigDict(extra='forbid')

    course_id: str
    course_name: str
    department: str
    credit: Optional[float] = None
    year: int = Field(..., ge=2000)
    semester: Literal[1, 2]
    target_year_raw: Optional[str] = None
    recommended_year_raw: Optional[str] = None
    is_english: Literal[0, 1] = 0
    is_cu: Literal[0, 1] = 0
    is_huss: Literal[0, 1] = 0
    is_ci: Literal[0, 1] = 0
    is_honors: Literal[0, 1] = 0
    course_type: Literal['regular', 'special', 'dummy'] = 'regular'
    is_general: Literal[0, 1] = 0
    description_raw: Optional[str] = None
    restrictions_raw: Optional[str] = None
    remarks_raw: Optional[str] = None
    linked_majors_parsed: Optional[str] = None


class OfferingRow(BaseModel):
    """course_offerings 테이블 행."""

    model_config = ConfigDict(extra='forbid')

    course_id: str
    year: int = Field(..., ge=2000)
    semester: Literal[1, 2]


class PrereqRow(BaseModel):
    """course_prerequisites 테이블 행."""

    model_config = ConfigDict(extra='forbid')

    course_id: str
    prereq_raw: str
    prereq_tree_json: str

    @field_validator('prereq_tree_json')
    @classmethod
    def _validate_json(cls, v: str) -> str:
        try:
            json.loads(v)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f'prereq_tree_json is not valid JSON: {exc}'
            ) from exc
        return v


class AliasRow(BaseModel):
    """course_aliases 테이블 행 (id 제외)."""

    model_config = ConfigDict(extra='forbid')

    new_course_id: str
    old_course_id: Optional[str] = None
    old_course_name: Optional[str] = None
    source_type: Literal['old_code', 'replacement']
    condition_raw: Optional[str] = None
    raw_text: str


class RestrictionRow(BaseModel):
    """course_restrictions 테이블 행 (id 제외)."""

    model_config = ConfigDict(extra='forbid')

    course_id: str
    target_dept: str
    status: Literal[
        'allowed',
        'forbidden',
        'major_only_allowed',
        'major_only_forbidden',
    ]
    raw_text: str


class WarningRow(BaseModel):
    """parse_warnings 테이블 행 (id 제외).

    course_id 는 NULL 허용 (특정 과목 무관한 일반 경고).
    field 는 자유 토큰 (schema.sql 에서 CHECK 제거됨).
    """

    model_config = ConfigDict(extra='forbid')

    course_id: Optional[str] = None
    field: str
    severity: Literal['error', 'warning', 'info']
    issue: str
    raw_text: Optional[str] = None
