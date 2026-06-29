"""Anthropic Claude chat provider (Messages API)."""

from __future__ import annotations

from eva_core.config import Settings
from eva_core.providers.base import ChatMessage, ChatProvider, ChatResult, ProviderError


class AnthropicProvider(ChatProvider):
    name = "claude"
    label = "Anthropic Claude"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings.anthropic_model)
        self._api_key = settings.anthropic_api_key

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _client(self):
        from anthropic import Anthropic

        return Anthropic(api_key=self._api_key)

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResult:
        if not self.is_available():
            raise ProviderError("Anthropic API key is not configured (set ANTHROPIC_API_KEY).")

        model = model or self.model
        system, convo = self._split_system(messages)
        client = self._client()
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in convo],
        }
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)

        # Concatenate any text blocks in the response.
        parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
        return ChatResult(
            provider=self.name,
            model=model,
            content="".join(parts),
            raw={"id": getattr(resp, "id", None)},
        )
