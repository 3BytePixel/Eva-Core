"""FastAPI application exposing chat + speech endpoints and a web UI."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from eva_core import __version__
from eva_core.providers import ChatMessage, ProviderError
from eva_core.service import EvaCore
from eva_core.speech import SpeechError

WEB_DIR = Path(__file__).parent / "web"


class MessageIn(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    provider: str
    messages: list[MessageIn]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 1024


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None


def create_app(core: EvaCore | None = None) -> FastAPI:
    core = core or EvaCore()
    app = FastAPI(title="Eva-Core", version=__version__)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        index_file = WEB_DIR / "index.html"
        if index_file.exists():
            return index_file.read_text(encoding="utf-8")
        return "<h1>Eva-Core</h1><p>UI not found.</p>"

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/api/status")
    def status() -> dict:
        return core.status()

    @app.post("/api/chat")
    def chat(req: ChatRequest) -> JSONResponse:
        messages = [ChatMessage(role=m.role, content=m.content) for m in req.messages]
        try:
            result = core.chat(
                req.provider,
                messages,
                model=req.model,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            )
        except ProviderError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # surface upstream SDK/network errors cleanly
            raise HTTPException(status_code=502, detail=f"Provider call failed: {exc}") from exc
        return JSONResponse(
            {
                "provider": result.provider,
                "model": result.model,
                "content": result.content,
            }
        )

    @app.post("/api/speech/tts")
    def tts(req: TTSRequest) -> JSONResponse:
        try:
            audio = core.speech.text_to_speech(req.text, voice=req.voice)
        except SpeechError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc
        return JSONResponse(
            {"audio_base64": base64.b64encode(audio).decode("ascii"), "content_type": "audio/wav"}
        )

    @app.post("/api/speech/stt")
    async def stt(file: UploadFile) -> JSONResponse:
        data = await file.read()
        try:
            text = core.speech.speech_to_text(data)
        except SpeechError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"STT failed: {exc}") from exc
        return JSONResponse({"text": text})

    return app


app = create_app()
