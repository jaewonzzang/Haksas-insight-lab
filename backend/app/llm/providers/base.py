"""LLM 공급자 공통 인터페이스 (Protocol).

모든 공급자는 동일 시그니처의 complete(messages, **opts) -> str 을 구현한다.
"""

from typing import Protocol


class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str, **opts) -> str: ...
