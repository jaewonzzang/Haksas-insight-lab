"""AnthropicProvider 단위: 팩토리 스위치 + 실패 흡수. 실 API 호출 없음."""

from app import config
from app.llm.prompts import CardATranslation
from app.llm.providers import anthropic as provider_mod


def test_get_provider_none_without_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert provider_mod.get_provider() is None


def test_get_provider_with_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-test")
    p = provider_mod.get_provider()
    assert isinstance(p, provider_mod.AnthropicProvider)


def test_translate_absorbs_exceptions(monkeypatch):
    p = provider_mod.AnthropicProvider(api_key="sk-test")

    class Boom:
        class messages:
            @staticmethod
            def parse(**kwargs):
                raise RuntimeError("api down")

    monkeypatch.setattr(p, "_client", Boom)
    assert p.translate("sys", "user", CardATranslation) is None


def test_translate_returns_parsed_output(monkeypatch):
    p = provider_mod.AnthropicProvider(api_key="sk-test")
    expected = CardATranslation(items=[])

    class Resp:
        parsed_output = expected

    class Stub:
        class messages:
            @staticmethod
            def parse(**kwargs):
                assert kwargs["model"] == "claude-haiku-4-5"
                assert kwargs["output_format"] is CardATranslation
                return Resp

    monkeypatch.setattr(p, "_client", Stub)
    assert p.translate("sys", "user", CardATranslation) is expected
