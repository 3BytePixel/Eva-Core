# AGENTS.md

## Project

Eva-Core is a FastAPI service exposing a unified chat API across OpenAI, x.ai
(Grok), Google GenAI (Gemini), and Anthropic Claude, plus Azure Cognitive
Services Speech (TTS/STT). Source lives under `src/eva_core/`; tests under
`tests/`. Standard commands are documented in `README.md`.

## Cursor Cloud specific instructions

- Python venv requires the `python3.12-venv` apt package (installed during
  setup). Dependencies install via `pip install -e ".[dev]"` (see the update
  script); always activate `.venv` first: `source .venv/bin/activate`.
- Run the dev server with `python -m eva_core` (uvicorn with `--reload`). It
  binds `HOST`/`PORT` (defaults `0.0.0.0:8000`). Override with env vars, e.g.
  `HOST=127.0.0.1 PORT=8000 python -m eva_core`.
- Providers/speech are **credential-gated**: with no API keys the server still
  boots and `/api/status` reports each backend as `available: false`. Tests run
  fully offline because every provider SDK call is mocked — no keys needed for
  `pytest`.
- To exercise the real chat path without paid keys, point the OpenAI provider at
  a local OpenAI-compatible mock: set `OPENAI_API_KEY=sk-test` and
  `OPENAI_BASE_URL=http://127.0.0.1:<port>/v1`. The x.ai provider is also
  OpenAI-compatible (`XAI_BASE_URL` defaults to `https://api.x.ai/v1`).
- Real provider/speech calls need secrets: `OPENAI_API_KEY`, `XAI_API_KEY`,
  `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_SPEECH_KEY` +
  `AZURE_SPEECH_REGION`. Put them in `.env` (gitignored) or the environment.
