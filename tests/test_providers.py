from __future__ import annotations

from types import SimpleNamespace

import pytest

from eva_core.providers import (
    AnthropicProvider,
    ChatMessage,
    GeminiProvider,
    OpenAIProvider,
    ProviderError,
    XAIProvider,
)


def _openai_style_response(text: str):
    return SimpleNamespace(
        id="resp_1",
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
    )


def test_availability_reflects_keys(all_keys_settings, no_keys_settings):
    assert OpenAIProvider(all_keys_settings).is_available() is True
    assert OpenAIProvider(no_keys_settings).is_available() is False


def test_unavailable_provider_raises(no_keys_settings):
    provider = OpenAIProvider(no_keys_settings)
    with pytest.raises(ProviderError):
        provider.complete([ChatMessage(role="user", content="hi")])


def test_openai_complete(monkeypatch, all_keys_settings):
    provider = OpenAIProvider(all_keys_settings)
    captured = {}

    class FakeClient:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                def create(**kwargs):
                    captured.update(kwargs)
                    return _openai_style_response("hello from openai")

    monkeypatch.setattr(provider, "_client", lambda: FakeClient())
    result = provider.complete([ChatMessage(role="user", content="hi")])
    assert result.content == "hello from openai"
    assert result.provider == "openai"
    assert captured["model"] == "gpt-4o-mini"
    assert captured["messages"] == [{"role": "user", "content": "hi"}]


def test_xai_uses_grok_model(monkeypatch, all_keys_settings):
    provider = XAIProvider(all_keys_settings)
    captured = {}

    class FakeClient:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                def create(**kwargs):
                    captured.update(kwargs)
                    return _openai_style_response("yo from grok")

    monkeypatch.setattr(provider, "_client", lambda: FakeClient())
    result = provider.complete([ChatMessage(role="user", content="hi")])
    assert result.content == "yo from grok"
    assert captured["model"] == "grok-4.3"


def test_anthropic_splits_system(monkeypatch, all_keys_settings):
    provider = AnthropicProvider(all_keys_settings)
    captured = {}

    class FakeMessages:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                id="msg_1",
                content=[SimpleNamespace(type="text", text="claude says hi")],
            )

    monkeypatch.setattr(provider, "_client", lambda: SimpleNamespace(messages=FakeMessages()))
    result = provider.complete(
        [
            ChatMessage(role="system", content="be terse"),
            ChatMessage(role="user", content="hi"),
        ]
    )
    assert result.content == "claude says hi"
    assert captured["system"] == "be terse"
    assert captured["messages"] == [{"role": "user", "content": "hi"}]


def test_gemini_complete(monkeypatch, all_keys_settings):
    provider = GeminiProvider(all_keys_settings)
    captured = {}

    class FakeModels:
        @staticmethod
        def generate_content(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="gemini reply")

    monkeypatch.setattr(provider, "_client", lambda: SimpleNamespace(models=FakeModels()))
    result = provider.complete([ChatMessage(role="user", content="hi")])
    assert result.content == "gemini reply"
    assert captured["model"] == "gemini-1.5-flash"
