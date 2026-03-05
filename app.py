"""Compatibility entrypoint for platforms that run `python3 /app/app.py`."""

from __future__ import annotations

import os

import uvicorn

from app.main import app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port)
