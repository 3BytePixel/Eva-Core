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

## MCP server

Eva-Core also ships an [MCP](https://modelcontextprotocol.io/) server so hosts
like Claude Desktop and Claude Code can call the same backends as tools. It
runs in-process over the `EvaCore` facade and exposes one tool per action:

| Tool             | Description                                            |
| ---------------- | ------------------------------------------------------ |
| `list_providers` | Which providers / speech are configured and available  |
| `chat`           | Chat completion: `{provider, messages, model?, ...}`    |
| `text_to_speech` | Synthesize text to a WAV file (Azure)                   |
| `speech_to_text` | Transcribe a WAV file to text (Azure)                   |

Install the extra and run it (stdio transport by default):

```bash
pip install -e ".[mcp]"
eva-core-mcp                      # or: python -m eva_core.mcp_server
```

Register it with an MCP host (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "eva-core": {
      "command": "eva-core-mcp",
      "env": { "OPENAI_API_KEY": "sk-..." }
    }
  }
}
```

The same provider/speech credentials documented below apply; unconfigured
backends report `available: false` and their tools return a clear error.
For remote/shared use, set `EVA_MCP_TRANSPORT=http` (with optional
`EVA_MCP_HOST`, `EVA_MCP_PORT`, `EVA_MCP_PATH`).

### Interactive widgets (MCP Apps)

`list_providers` and `text_to_speech` ship inline UI that renders in hosts
implementing the MCP apps surface (claude.ai, Claude Desktop) — a provider
status dashboard with per-backend "Chat" buttons, and an audio player for
synthesized speech. Hosts without UI support ignore the hints and use the
tools' JSON, so the data path is unchanged.

The widgets live in [`src/eva_core/web/widgets/`](src/eva_core/web/widgets/)
and are wired up in [`widgets.py`](src/eva_core/widgets.py). The audio player
keeps WAV bytes out of the conversation by fetching them on demand from
`get_audio_data`, an app-only helper tool hidden from the model. The vendored
`ext-apps-bundle.js` is the [`@modelcontextprotocol/ext-apps`](https://github.com/modelcontextprotocol/ext-apps)
browser runtime, inlined into each widget because the iframe CSP blocks CDN
fetches; refresh it with `npm i @modelcontextprotocol/ext-apps` and copy
`dist/src/app-with-deps.js` over the vendored file.

## Configuration

All settings come from environment variables (or a `.env` file). See
[`.env.example`](.env.example) for the full list.

## Development

```bash
pytest          # unit tests (providers mocked — no network needed)
ruff check .    # lint
```
