"""AnthropicProvider — Haiku 구조화 통역 1콜 + 키 스위치 팩토리.

키 부재 스위치는 get_provider()가 판정 (스펙: 새 config 플래그 없음).
W6는 get_provider()를 호출해 translate_card_*에 주입만 한다.
"""

import anthropic
from pydantic import BaseModel

from app import config
from app.llm.providers.base import Provider


class AnthropicProvider:
    MODEL = "claude-haiku-4-5"

    def __init__(self, api_key: str, timeout: float = 8.0):
        self._client = anthropic.Anthropic(
            api_key=api_key, timeout=timeout, max_retries=1
        )

    def translate(
        self, system: str, user: str, schema: type[BaseModel]
    ) -> BaseModel | None:
        try:
            resp = self._client.messages.parse(
                model=self.MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
            return resp.parsed_output
        except Exception:
            return None  # 모든 실패 → 폴백 신호


def get_provider() -> Provider | None:
    if not config.ANTHROPIC_API_KEY:
        return None
    return AnthropicProvider(config.ANTHROPIC_API_KEY)
