"""Runtime configuration loaded from environment variables / .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Every credential is optional so the service can boot even when only a
    subset of providers are configured. Each provider reports itself as
    "available" only when its required credentials are present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    # x.ai (Grok) — OpenAI-compatible API
    xai_api_key: str | None = None
    xai_model: str = "grok-4.3"
    xai_base_url: str = "https://api.x.ai/v1"

    # Google GenAI (Gemini)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    # Anthropic Claude
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-latest"

    # Azure Cognitive Services Speech
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_speech_voice: str = "en-US-AvaMultilingualNeural"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
