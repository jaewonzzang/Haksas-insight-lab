"""졸업생 데이터 추상 인터페이스.

실 데이터 vs mock 의 교체점. 호출부(엔진/카드)는 이 Protocol 만 의존한다.
반환은 내부 표준 레코드 AlumniRecord (adapters/alumni_types.py).
"""

from typing import Protocol

from app.adapters.alumni_types import AlumniRecord


class AlumniSource(Protocol):
    def list_by_department(self, department: str) -> list[AlumniRecord]: ...
    def all(self) -> list[AlumniRecord]: ...
