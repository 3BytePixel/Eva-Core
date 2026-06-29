# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Note: there is a `CLAUDE.md` one directory up (`../CLAUDE.md`) describing an
> `eva_router_mcp` project. It does **not** match this repository's layout — this
> repo is `eva_core`. Trust this file and the code over the parent one.

## What this is

Eva-Core is a unified **chat + speech** backend. A single facade talks to four
LLM providers (OpenAI, x.ai/Grok, Google Gemini, Anthropic Claude) plus Azure
Speech (TTS/STT), and that one facade is exposed through **two independent
surfaces**: a FastAPI HTTP service (with a small web chat UI) and an MCP server.

## Commands

The Python package lives under `src/` (src layout) and must be installed
editable. Tests, providers, and speech are all mocked, so the full suite runs
offline with no API keys.

```bash
pip install -e ".[dev]"          # dev deps: pytest, ruff, httpx, fastmcp
pip install -e ".[mcp]"          # runtime-only MCP extra (fastmcp)

pytest                           # full suite (offline; providers mocked)
pytest tests/test_mcp_server.py  # one file
pytest tests/test_mcp_server.py::test_widget_tools_declare_ui_resources  # one test
pytest -k widget                 # by name substring

ruff check .                     # lint (config in [tool.ruff], line-length 100)

python -m eva_core               # FastAPI dev server, uvicorn --reload, :8000
eva-core-mcp                     # MCP server, stdio transport (= python -m eva_core.mcp_server)
```

`pytest-asyncio` runs in `asyncio_mode = "auto"` — async test functions need no
decorator.

### This machine's environment (Windows)

- `uv` and `gh` are **not** on PATH here despite what docs may imply; use `pip`
  for deps and the GitHub REST API (with the token from `git credential fill`)
  for PRs.
- The git worktree has no `.venv`; the working interpreter is
  `X:\Eva-Core\.venv\Scripts\python.exe`. Run it with `PYTHONPATH` set to this
  repo's `src/` if the package isn't installed into that venv.

## Architecture

**One facade, two surfaces.** [`EvaCore`](src/eva_core/service.py) is the single
point that owns the provider registry and the speech client. Both
[`create_app()`](src/eva_core/app.py) (FastAPI) and
[`build_mcp()`](src/eva_core/mcp_server.py) (MCP) are thin adapters over it and
each accept an optional `core` argument for dependency injection in tests. **Add
real capability to `service.py` / providers — never duplicate logic in the two
adapters.** The HTTP and MCP layers should only translate transport ↔ facade.

**Providers are a registry behind one ABC.** Every provider subclasses
[`ChatProvider`](src/eva_core/providers/base.py) (`name`, `label`,
`is_available()`, `complete()`). [`build_providers()`](src/eva_core/providers/__init__.py)
instantiates all four keyed by short name (`openai`, `xai`, `gemini`, `claude`).
x.ai reuses the OpenAI-compatible client path. The shared `ChatMessage` /
`ChatResult` dataclasses and `ProviderError` in `base.py` are the cross-module
contract — don't redefine them elsewhere. To add a provider: implement the ABC,
register it in `build_providers`, add its settings fields to `Settings`.

**Credential-gating is the core invariant.** Every credential in
[`Settings`](src/eva_core/config.py) is optional, so the server always boots. A
provider reports `available: false` (and its tool/endpoint returns a clear
error) when its key is missing, rather than crashing at startup. Tests rely on
this: [`conftest.py`](tests/conftest.py) supplies `all_keys_settings` /
`no_keys_settings` fixtures and mocks the SDK calls, so nothing hits the network.

**`get_settings()` is a cached module global.** `.env` is read once per process;
restart the server after changing it. Tests construct `Settings(...)` directly
to bypass the cache.

## MCP widgets (MCP Apps)

`list_providers` and `text_to_speech` ship inline UI rendered by hosts that
implement the MCP apps surface (claude.ai, Claude Desktop). Wiring is in
[`widgets.py`](src/eva_core/widgets.py); the HTML is in
[`src/eva_core/web/widgets/`](src/eva_core/web/widgets/). Key facts a future
change must respect:

- A widget = a `ui://` **resource** (served with mime `text/html;profile=mcp-app`)
  + a **tool** whose `_meta` points at it. The host reads the **flat**
  `_meta["ui/resourceUri"]` key; the nested `ui.resourceUri` is convenience.
  `ui_tool_meta()` sets both. Tool handlers still return plain JSON — hosts
  without the apps surface use that, so behavior degrades gracefully.
- `get_audio_data` is an **app-only helper** (`_meta.ui.visibility == ["app"]`,
  hidden from the model) that the TTS player calls to fetch WAV bytes on demand,
  keeping audio out of the conversation.
- `ext-apps-bundle.js` is the vendored `@modelcontextprotocol/ext-apps` browser
  runtime, inlined into each widget at load (its trailing `export{...}` rewritten
  to `globalThis.ExtApps`) because the iframe CSP blocks CDN fetches. Refresh
  with `npm i @modelcontextprotocol/ext-apps` and copy `dist/src/app-with-deps.js`.
- Widgets render in claude.ai / Claude Desktop, **not** the Claude Code terminal.

## Configuration

All settings come from env vars or `.env` (see [`.env.example`](.env.example)).
Model defaults and credential names live in [`config.py`](src/eva_core/config.py).
MCP transport is env-driven: `EVA_MCP_TRANSPORT` (`stdio` default, or `http`/`sse`)
plus `EVA_MCP_HOST` / `EVA_MCP_PORT` / `EVA_MCP_PATH`.

## playwright-scraper/

A separate, self-contained Node/TypeScript subproject (pnpm) — not part of the
Python package or its tests. Treat it as its own project with its own README.
