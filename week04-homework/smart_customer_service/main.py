"""Entry point for the smart customer service FastAPI app."""
from __future__ import annotations

import uvicorn

from .app import create_app
from .config import get_settings


def main():
    app = create_app()
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()