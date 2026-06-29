from __future__ import annotations

import pytest

from eva_core.config import Settings


@pytest.fixture
def all_keys_settings() -> Settings:
    """Settings with every provider/credential populated."""
    return Settings(
        openai_api_key="sk-test-openai",
        xai_api_key="xai-test",
        gemini_api_key="gem-test",
        anthropic_api_key="ant-test",
        azure_speech_key="azure-test",
        azure_speech_region="eastus",
    )


@pytest.fixture
def no_keys_settings() -> Settings:
    """Settings with no credentials configured."""
    return Settings(
        _env_file=None,
        openai_api_key=None,
        xai_api_key=None,
        gemini_api_key=None,
        anthropic_api_key=None,
        azure_speech_key=None,
        azure_speech_region=None,
    )
