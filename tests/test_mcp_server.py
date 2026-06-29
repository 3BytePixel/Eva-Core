from __future__ import annotations

import wave

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from eva_core.mcp_server import build_mcp
from eva_core.providers import ChatMessage, ChatResult
from eva_core.service import EvaCore


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
    assert names == {"list_providers", "chat", "text_to_speech", "speech_to_text"}


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
