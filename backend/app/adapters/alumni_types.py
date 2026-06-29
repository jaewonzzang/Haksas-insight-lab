"""졸업생 데이터 내부 표준 레코드(canonical frame).

API 계약(schemas/)이 아니라 백엔드 데이터 계층의 내부 표현이다.
실데이터 컬럼/규모 미상 → 코어(alumni_id, department) 외 전부 Optional.
실 컬럼 매핑은 adapters/real_alumni.py 한 곳으로 흡수.
잠정 명세 — 실 입력 데이터 확정 시 수정될 수 있음.
스펙: docs/superpowers/specs/2026-06-29-alumni-data-frame-design.md
"""

from typing import Literal

from pydantic import BaseModel


class Major(BaseModel):
    label: str
    role: Literal["primary", "double", "triple", "minor"] | None = None
    credits: float | None = None


class Enrollment(BaseModel):
    course_id: str
    year_taken: int | None = None
    term_taken: int | None = None


class Career(BaseModel):
    type: Literal["job", "grad", "other"] | None = None
    label: str | None = None


class AlumniRecord(BaseModel):
    alumni_id: str
    department: str
    majors: list[Major] = []
    enrollment: list[Enrollment] = []
    career: Career | None = None
