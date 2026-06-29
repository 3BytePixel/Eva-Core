"""Chat provider implementations and registry."""

from __future__ import annotations

from eva_core.config import Settings
from eva_core.providers.anthropic_provider import AnthropicProvider
from eva_core.providers.base import ChatMessage, ChatProvider, ChatResult, ProviderError
from eva_core.providers.gemini_provider import GeminiProvider
from eva_core.providers.openai_provider import OpenAIProvider
from eva_core.providers.xai_provider import XAIProvider

__all__ = [
    "ChatMessage",
    "ChatProvider",
    "ChatResult",
    "ProviderError",
    "build_providers",
    "AnthropicProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "XAIProvider",
]


def build_providers(settings: Settings) -> dict[str, ChatProvider]:
    """Instantiate every known provider, keyed by short name."""
    return {
        "openai": OpenAIProvider(settings),
        "xai": XAIProvider(settings),
        "gemini": GeminiProvider(settings),
        "claude": AnthropicProvider(settings),
    }
