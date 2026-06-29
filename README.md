# Eva-Core

A unified, multi-provider **chat + speech** API. Eva-Core talks to several LLM
providers behind one interface and adds voice via Azure Speech:

- **OpenAI** (Chat Completions)
- **x.ai (Grok)** — OpenAI-compatible API
- **Google GenAI (Gemini)**
- **Anthropic Claude** (Messages API)
- **Azure Cognitive Services Speech** — text-to-speech & speech-to-text

It ships as a [FastAPI](https://fastapi.tiangolo.com/) service with a small web
chat UI. Providers without configured credentials are reported as
*unavailable* — the server always boots, so you can start with just one key.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # add the API keys you have
python -m eva_core     # dev server with reload at http://localhost:8000
```

Open <http://localhost:8000> for the chat UI, or use the API directly.

## API

| Method | Path                | Description                                  |
| ------ | ------------------- | -------------------------------------------- |
| GET    | `/api/health`       | Liveness probe                               |
| GET    | `/api/status`       | Which providers / speech are configured      |
| POST   | `/api/chat`         | Chat completion: `{provider, messages}`      |
| POST   | `/api/speech/tts`   | Text-to-speech (Azure): `{text, voice?}`     |
| POST   | `/api/speech/stt`   | Speech-to-text (Azure): multipart WAV upload |

Example chat request:

```bash
curl -s localhost:8000/api/chat -H 'content-type: application/json' -d '{
  "provider": "openai",
  "messages": [{"role": "user", "content": "Say hello from Eva-Core"}]
}'
```

`provider` is one of `openai`, `xai`, `gemini`, `claude`.

## Configuration

All settings come from environment variables (or a `.env` file). See
[`.env.example`](.env.example) for the full list.

## Development

```bash
pytest          # unit tests (providers mocked — no network needed)
ruff check .    # lint
```
