"""Entry point: ``python -m eva_core`` runs the dev server."""

from __future__ import annotations

import uvicorn

from eva_core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "eva_core.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
