"""MCP server exposing Eva-Core's chat + speech capabilities as tools.

This wraps the in-process :class:`~eva_core.service.EvaCore` facade with a
`FastMCP <https://github.com/jlowin/fastmcp>`_ server so MCP hosts (Claude
Desktop, Claude Code, etc.) can call the same unified backends the HTTP API
exposes.

Design (see ``build-mcp-server`` skill):

* **Deployment** — local stdio server by default (the host launches it and
  talks over stdin/stdout). HTTP transport is available via env vars for
  remote/shared use.
* **Tool pattern** — one tool per action; the surface is small (four tools).
* **Auth** — none at the MCP layer for local stdio. The underlying providers
  read their own credentials from the environment, exactly like the HTTP API,
  and report ``available: false`` when a key is missing.

Run it with ``eva-core-mcp`` (console script) or ``python -m eva_core.mcp_server``.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from eva_core import __version__
from eva_core.providers import ChatMessage, ProviderError
from eva_core.service import EvaCore
from eva_core.speech import SpeechError

INSTRUCTIONS = """\
Eva-Core exposes a unified chat interface across OpenAI, x.ai (Grok), Google
Gemini and Anthropic Claude, plus Azure text-to-speech and speech-to-text.

Call `list_providers` first to discover which backends are configured before
calling `chat`, `text_to_speech` or `speech_to_text`.
"""


class ChatTurn(BaseModel):
    """A single message in a conversation."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(description="The message text.")


def build_mcp(core: EvaCore | None = None) -> FastMCP:
    """Build a :class:`FastMCP` server bound to an :class:`EvaCore` instance.

    Accepting an optional ``core`` mirrors :func:`eva_core.app.create_app` and
    makes the server easy to test with a stubbed facade.
    """

    core = core or EvaCore()
    mcp: FastMCP = FastMCP(name=f"Eva-Core v{__version__}", instructions=INSTRUCTIONS)

    @mcp.tool
    def list_providers() -> dict:
        """List chat providers and speech support with their availability.

        A backend is only ``available`` when its credentials are configured.
        Use this to pick a ``provider`` for `chat` or to check whether speech
        tools will work before calling them.
        """
        return core.status()

    @mcp.tool
    def chat(
        provider: Annotated[
            str,
            Field(description="Provider id: one of 'openai', 'xai', 'gemini', 'claude'."),
        ],
        messages: Annotated[
            list[ChatTurn],
            Field(description="Conversation so far, in order. Roles: system, user, assistant."),
        ],
        model: Annotated[
            str | None,
            Field(description="Override the provider's default model. Optional."),
        ] = None,
        temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.7,
        max_tokens: Annotated[int, Field(ge=1, le=32768)] = 1024,
    ) -> dict:
        """Run a chat completion against one of the configured providers.

        Returns the assistant reply along with the provider and model that
        produced it.
        """
        if not messages:
            raise ToolError("`messages` must contain at least one message.")
        convo = [ChatMessage(role=m.role, content=m.content) for m in messages]
        try:
            result = core.chat(
                provider,
                convo,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ProviderError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:  # surface upstream SDK/network errors cleanly
            raise ToolError(f"Provider call failed: {exc}") from exc
        return {"provider": result.provider, "model": result.model, "content": result.content}

    @mcp.tool
    def text_to_speech(
        text: Annotated[str, Field(description="Text to synthesize.")],
        output_path: Annotated[
            str | None,
            Field(description="Where to write the WAV file. A temp file is used if omitted."),
        ] = None,
        voice: Annotated[
            str | None,
            Field(description="Azure voice name. Defaults to the configured voice."),
        ] = None,
    ) -> dict:
        """Synthesize ``text`` to speech with Azure and write a WAV file.

        Audio is written to disk (not returned inline) so large clips don't
        bloat the conversation. Returns the file path and byte count.
        """
        if not text.strip():
            raise ToolError("`text` must not be empty.")
        try:
            audio = core.speech.text_to_speech(text, voice=voice)
        except SpeechError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            raise ToolError(f"TTS failed: {exc}") from exc

        if output_path:
            path = Path(output_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            fd, tmp_name = tempfile.mkstemp(prefix="eva-tts-", suffix=".wav")
            os.close(fd)
            path = Path(tmp_name)
        path.write_bytes(audio)
        return {"path": str(path), "bytes": len(audio), "content_type": "audio/wav"}

    @mcp.tool
    def speech_to_text(
        audio_path: Annotated[str, Field(description="Path to a WAV file to transcribe.")],
    ) -> dict:
        """Transcribe a WAV file at ``audio_path`` to text using Azure."""
        path = Path(audio_path).expanduser()
        if not path.is_file():
            raise ToolError(f"Audio file not found: {path}")
        try:
            text = core.speech.speech_to_text(path.read_bytes())
        except SpeechError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            raise ToolError(f"STT failed: {exc}") from exc
        return {"text": text}

    return mcp


mcp = build_mcp()


def main() -> None:
    """Console entry point. Transport is configurable via environment.

    * ``EVA_MCP_TRANSPORT`` — ``stdio`` (default), ``http``, ``sse``.
    * ``EVA_MCP_HOST`` / ``EVA_MCP_PORT`` — bind address for HTTP/SSE
      (defaults ``127.0.0.1:8001``).
    * ``EVA_MCP_PATH`` — HTTP path (default ``/mcp``).
    """
    transport = os.getenv("EVA_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
        return
    mcp.run(
        transport=transport,
        host=os.getenv("EVA_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("EVA_MCP_PORT", "8001")),
        path=os.getenv("EVA_MCP_PATH", "/mcp"),
    )


if __name__ == "__main__":
    main()
