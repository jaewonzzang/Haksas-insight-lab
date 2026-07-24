"""졸업생 데이터 내부 표준 레코드(canonical frame).

API 계약(schemas/)이 아니라 백엔드 데이터 계층의 내부 표현이다.
실데이터 컬럼/규모 미상 → 코어(alumni_id, department) 외 전부 Optional.
실 컬럼 매핑은 adapters/real_alumni.py 한 곳으로 흡수.
잠정 명세 — 실 입력 데이터 확정 시 수정될 수 있음.
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
    # 이수 이력이 데이터 창 안에서 끝났는가(= 졸업 추정). 재학 중이면 False.
    # 다전공 선택 전인 재학생이 섞이면 카드 C 경로 분포가 왜곡된다 (A17).
    # None = 미상(mock) → 필터 통과. 판정은 어댑터/빌드 스크립트 책임.
    history_complete: bool | None = None
