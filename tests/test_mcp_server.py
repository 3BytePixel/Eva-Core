from __future__ import annotations

import wave

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from eva_core.mcp_server import build_mcp
from eva_core.providers import ChatMessage, ChatResult
from eva_core.service import EvaCore
from eva_core.widgets import (
    PROVIDER_DASHBOARD_URI,
    RESOURCE_MIME_TYPE,
    TTS_PLAYER_URI,
)


def _silent_wav(path) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000)


async def test_lists_expected_tools(all_keys_settings):
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
    # ``get_audio_data`` is registered for the TTS player widget; it carries
    # ``_meta.ui.visibility == ["app"]`` so apps-capable hosts hide it from the
    # model, but the server still exposes it for widget ``callServerTool`` use.
    assert names == {
        "list_providers",
        "chat",
        "text_to_speech",
        "speech_to_text",
        "get_audio_data",
    }


async def test_widget_tools_declare_ui_resources(all_keys_settings):
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        tools = {t.name: t for t in await client.list_tools()}
    # The host reads the flat ``ui/resourceUri`` key to pick a tool's widget.
    assert tools["list_providers"].meta["ui/resourceUri"] == PROVIDER_DASHBOARD_URI
    assert tools["text_to_speech"].meta["ui/resourceUri"] == TTS_PLAYER_URI
    assert tools["get_audio_data"].meta["ui"]["visibility"] == ["app"]


async def test_widget_resources_served_as_apps(all_keys_settings):
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        resources = {str(r.uri): r for r in await client.list_resources()}
        assert resources[PROVIDER_DASHBOARD_URI].mimeType == RESOURCE_MIME_TYPE
        assert resources[TTS_PLAYER_URI].mimeType == RESOURCE_MIME_TYPE
        # The served HTML must have the ext-apps runtime inlined (CSP blocks CDN).
        contents = await client.read_resource(PROVIDER_DASHBOARD_URI)
        html = contents[0].text
    assert "globalThis.ExtApps" in html
    assert "/*__EXT_APPS_BUNDLE__*/" not in html


async def test_get_audio_data_returns_base64(all_keys_settings, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"RIFFfakewavdata")
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        res = await client.call_tool("get_audio_data", {"path": str(wav)})
    import base64

    assert base64.b64decode(res.data["audio_base64"]) == b"RIFFfakewavdata"
    assert res.data["content_type"] == "audio/wav"


async def test_get_audio_data_missing_file_errors(all_keys_settings, tmp_path):
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="not found"):
            await client.call_tool("get_audio_data", {"path": str(tmp_path / "nope.wav")})


async def test_list_providers_reports_availability(no_keys_settings):
    mcp = build_mcp(EvaCore(no_keys_settings))
    async with Client(mcp) as client:
        res = await client.call_tool("list_providers", {})
    data = res.data
    assert {p["name"] for p in data["providers"]} == {"openai", "xai", "gemini", "claude"}
    assert all(p["available"] is False for p in data["providers"])
    assert data["speech"]["available"] is False


async def test_chat_tool_returns_reply(all_keys_settings):
    core = EvaCore(all_keys_settings)

    def fake_chat(provider, messages, **kwargs):
        assert all(isinstance(m, ChatMessage) for m in messages)
        assert kwargs["temperature"] == 0.2
        return ChatResult(provider=provider, model="stub-model", content="hi from stub")

    core.chat = fake_chat  # type: ignore[method-assign]
    mcp = build_mcp(core)
    async with Client(mcp) as client:
        res = await client.call_tool(
            "chat",
            {
                "provider": "openai",
                "messages": [{"role": "user", "content": "hello"}],
                "temperature": 0.2,
            },
        )
    assert res.data == {"provider": "openai", "model": "stub-model", "content": "hi from stub"}


async def test_chat_empty_messages_errors(all_keys_settings):
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="at least one message"):
            await client.call_tool("chat", {"provider": "openai", "messages": []})


async def test_chat_unknown_provider_errors(all_keys_settings):
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="Unknown provider"):
            await client.call_tool(
                "chat",
                {"provider": "nope", "messages": [{"role": "user", "content": "hi"}]},
            )


async def test_text_to_speech_writes_file(all_keys_settings, tmp_path):
    core = EvaCore(all_keys_settings)
    core.speech.text_to_speech = lambda text, voice=None: b"RIFFfakewavdata"  # type: ignore[method-assign]
    out = tmp_path / "out.wav"
    mcp = build_mcp(core)
    async with Client(mcp) as client:
        res = await client.call_tool(
            "text_to_speech", {"text": "hello world", "output_path": str(out)}
        )
    assert res.data["path"] == str(out)
    assert res.data["bytes"] == len(b"RIFFfakewavdata")
    assert out.read_bytes() == b"RIFFfakewavdata"


async def test_text_to_speech_empty_errors(all_keys_settings):
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="must not be empty"):
            await client.call_tool("text_to_speech", {"text": "   "})


async def test_speech_to_text_transcribes(all_keys_settings, tmp_path):
    core = EvaCore(all_keys_settings)
    captured = {}

    def fake_stt(audio_bytes: bytes) -> str:
        captured["len"] = len(audio_bytes)
        return "transcribed text"

    core.speech.speech_to_text = fake_stt  # type: ignore[method-assign]
    wav = tmp_path / "in.wav"
    _silent_wav(wav)
    mcp = build_mcp(core)
    async with Client(mcp) as client:
        res = await client.call_tool("speech_to_text", {"audio_path": str(wav)})
    assert res.data == {"text": "transcribed text"}
    assert captured["len"] > 0


async def test_speech_to_text_missing_file_errors(all_keys_settings, tmp_path):
    mcp = build_mcp(EvaCore(all_keys_settings))
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="not found"):
            await client.call_tool("speech_to_text", {"audio_path": str(tmp_path / "nope.wav")})
