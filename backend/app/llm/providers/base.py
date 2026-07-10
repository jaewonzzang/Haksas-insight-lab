"""LLM Provider 프로토콜 — 구조화 통역 1콜, 실패는 None.

AnthropicProvider 외 공급자(마인드로직/GPT)는 A7 잔여 — 만들지 않음 (YAGNI).
"""

from typing import Protocol

from pydantic import BaseModel


class Provider(Protocol):
    def translate(
        self, system: str, user: str, schema: type[BaseModel]
    ) -> BaseModel | None:
        """구조화 통역 1콜. 실패(타임아웃·오류·파싱)면 None."""
        ...
