"""졸업생 데이터 추상 인터페이스.

실 데이터 vs mock 의 교체점. 호출부(엔진/카드)는 이 Protocol 만 의존한다.
"""

from typing import Protocol


class AlumniSource(Protocol):
    def list_by_department(self, department: str) -> list[dict]: ...
    def all(self) -> list[dict]: ...
