"""Google GenAI (Gemini) chat provider using the google-genai SDK."""

from __future__ import annotations

from eva_core.config import Settings
from eva_core.providers.base import ChatMessage, ChatProvider, ChatResult, ProviderError


class GeminiProvider(ChatProvider):
    name = "gemini"
    label = "Google GenAI (Gemini)"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings.gemini_model)
        self._api_key = settings.gemini_api_key

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _client(self):
        from google import genai

        return genai.Client(api_key=self._api_key)

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResult:
        if not self.is_available():
            raise ProviderError("Gemini API key is not configured (set GEMINI_API_KEY).")

        from google.genai import types

        model = model or self.model
        system, convo = self._split_system(messages)

        # Gemini uses "model" for assistant turns and a list of typed contents.
        contents = [
            types.Content(
                role="model" if m.role == "assistant" else "user",
                parts=[types.Part.from_text(text=m.content)],
            )
            for m in convo
        ]
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system,
        )
        client = self._client()
        resp = client.models.generate_content(model=model, contents=contents, config=config)
        return ChatResult(
            provider=self.name,
            model=model,
            content=resp.text or "",
            raw={},
        )
