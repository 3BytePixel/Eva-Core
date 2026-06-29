"""Core service wiring providers + speech together."""

from __future__ import annotations

from eva_core.config import Settings, get_settings
from eva_core.providers import ChatMessage, ChatProvider, ChatResult, ProviderError, build_providers
from eva_core.speech import AzureSpeech


class EvaCore:
    """Facade that exposes chat + speech across all configured backends."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.providers: dict[str, ChatProvider] = build_providers(self.settings)
        self.speech = AzureSpeech(self.settings)

    def get_provider(self, name: str) -> ChatProvider:
        provider = self.providers.get(name)
        if provider is None:
            known = ", ".join(sorted(self.providers))
            raise ProviderError(f"Unknown provider '{name}'. Available: {known}.")
        return provider

    def chat(
        self,
        provider: str,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResult:
        return self.get_provider(provider).complete(
            messages, model=model, temperature=temperature, max_tokens=max_tokens
        )

    def status(self) -> dict:
        """Report which backends are configured/available."""
        return {
            "providers": [
                {
                    "name": p.name,
                    "label": p.label,
                    "model": p.model,
                    "available": p.is_available(),
                }
                for p in self.providers.values()
            ],
            "speech": {
                "available": self.speech.is_available(),
                "voice": self.settings.azure_speech_voice,
            },
        }
