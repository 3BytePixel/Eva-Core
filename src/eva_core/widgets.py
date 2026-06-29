"""MCP App (UI widget) support for the Eva-Core MCP server.

An *MCP App* is a normal MCP server that also serves interactive HTML rendered
inline by hosts that implement the apps surface (claude.ai, Claude Desktop).
A widget is two registrations that travel together:

* a **resource** at a ``ui://`` URI whose body is the widget HTML, served with
  the ``text/html;profile=mcp-app`` mime type so the host renders it in a
  sandboxed iframe instead of displaying the source; and
* a **tool** that carries ``_meta["ui/resourceUri"]`` pointing at that resource.
  The tool handler still returns plain JSON/text — the host pipes that return
  value into the iframe via the widget's ``ontoolresult`` event.

Hosts without the apps surface simply ignore the ``_meta.ui`` hints and show the
tool's text content, so every widget degrades gracefully to data.

The iframe sandbox CSP blocks CDN script fetches, so the ext-apps browser
runtime (the ``App`` class the widget talks to the host with) must be *inlined*
into each widget. We vendor the raw ESM bundle at
``web/widgets/ext-apps-bundle.js`` (from ``@modelcontextprotocol/ext-apps``
v1.7.4, the ``app-with-deps`` entry) and rewrite its trailing ``export{...}``
into a ``globalThis.ExtApps`` assignment at load time — the same transform the
skill's TypeScript scaffold performs with ``require.resolve``.

To refresh the bundle: ``npm i @modelcontextprotocol/ext-apps`` and copy
``dist/src/app-with-deps.js`` over the vendored file.
"""

from __future__ import annotations

import re
from functools import cache, lru_cache
from pathlib import Path

from fastmcp import FastMCP

# Mime type that tells an apps-capable host "render this as an interactive
# iframe", not "show me the HTML source". Matches RESOURCE_MIME_TYPE /
# ext-apps' `p` constant.
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"

# The flat _meta key the host actually reads to find a tool's widget. The
# ext-apps `registerAppTool` helper writes BOTH this and the nested
# `ui.resourceUri`; we mirror that so either lookup path resolves.
RESOURCE_URI_META_KEY = "ui/resourceUri"

_WIDGETS_DIR = Path(__file__).resolve().parent / "web" / "widgets"
_BUNDLE_FILE = _WIDGETS_DIR / "ext-apps-bundle.js"
_BUNDLE_PLACEHOLDER = "/*__EXT_APPS_BUNDLE__*/"

# Each widget: tool that renders it -> the ui:// resource URI + HTML file.
PROVIDER_DASHBOARD_URI = "ui://widgets/provider-dashboard.html"
TTS_PLAYER_URI = "ui://widgets/tts-player.html"


def ui_tool_meta(resource_uri: str) -> dict:
    """`_meta` payload that attaches a widget to a tool.

    Sets both the flat ``ui/resourceUri`` key (canonical, host-read) and the
    nested ``ui.resourceUri`` form, exactly like ext-apps' ``registerAppTool``.
    """
    return {
        RESOURCE_URI_META_KEY: resource_uri,
        "ui": {"resourceUri": resource_uri},
    }


def ui_app_only_meta() -> dict:
    """`_meta` that hides a tool from the model but keeps it callable by widgets.

    Used for helper tools a widget calls via ``app.callServerTool`` (e.g.
    fetching heavy audio bytes on demand) that Claude should never invoke.
    """
    return {"ui": {"visibility": ["app"]}}


def _bundle_as_global(bundle: str) -> str:
    """Rewrite the ext-apps ESM bundle's ``export{...}`` into ``globalThis.ExtApps``.

    The minified footer looks like ``export{aN as App,bN as foo,...};`` — we map
    each ``local as exported`` pair to ``exported:local`` so the widget can do
    ``const { App } = globalThis.ExtApps;`` with no module loader.
    """
    match = re.search(r"export\{([^}]+)\};?\s*$", bundle)
    if match is None:  # pragma: no cover - guards against a bad/old bundle
        raise RuntimeError(
            "Could not find the trailing export{...} in the ext-apps bundle; "
            "the vendored file may be corrupt or built differently."
        )
    pairs = []
    for part in match.group(1).split(","):
        names = part.split(" as ")
        local = names[0].strip()
        exported = names[1].strip() if len(names) > 1 else local
        pairs.append(f"{exported}:{local}")
    return bundle[: match.start()] + "globalThis.ExtApps={" + ",".join(pairs) + "};"


@lru_cache(maxsize=1)
def _ext_apps_global() -> str:
    return _bundle_as_global(_BUNDLE_FILE.read_text(encoding="utf-8"))


@cache
def _widget_html(filename: str) -> str:
    """Load a widget HTML file with the ext-apps runtime inlined."""
    raw = (_WIDGETS_DIR / filename).read_text(encoding="utf-8")
    if _BUNDLE_PLACEHOLDER not in raw:  # pragma: no cover
        raise RuntimeError(f"{filename} is missing the {_BUNDLE_PLACEHOLDER} placeholder.")
    # Single replace; avoid str.replace treating the bundle as a regex/backref.
    return raw.replace(_BUNDLE_PLACEHOLDER, _ext_apps_global(), 1)


def register_widgets(mcp: FastMCP) -> None:
    """Register the widget ``ui://`` resources on ``mcp``.

    Tools opt into a widget by setting ``_meta`` via :func:`ui_tool_meta`; this
    only wires up the resources that serve the HTML.
    """

    @mcp.resource(
        PROVIDER_DASHBOARD_URI,
        name="Provider Dashboard",
        mime_type=RESOURCE_MIME_TYPE,
    )
    def provider_dashboard() -> str:
        return _widget_html("provider-dashboard.html")

    @mcp.resource(
        TTS_PLAYER_URI,
        name="TTS Audio Player",
        mime_type=RESOURCE_MIME_TYPE,
    )
    def tts_player() -> str:
        return _widget_html("tts-player.html")
