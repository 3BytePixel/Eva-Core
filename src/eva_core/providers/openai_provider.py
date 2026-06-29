"""OpenAI chat provider (Chat Completions API)."""

from __future__ import annotations

from eva_core.config import Settings
from eva_core.providers.base import ChatMessage, ChatProvider, ChatResult, ProviderError


class OpenAIProvider(ChatProvider):
    name = "openai"
    label = "OpenAI"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings.openai_model)
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _client(self):
        from openai import OpenAI

        return OpenAI(api_key=self._api_key, base_url=self._base_url)

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResult:
        if not self.is_available():
            raise ProviderError("OpenAI API key is not configured (set OPENAI_API_KEY).")

        model = model or self.model
        client = self._client()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content or ""
        return ChatResult(
            provider=self.name,
            model=model,
            content=content,
            raw={"id": getattr(resp, "id", None)},
        )
