"""Run the candidate API: uv run python -m knowledge.serve"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("PRAXIS_API_PORT", "8000")))
    host = os.getenv("PRAXIS_API_HOST", "127.0.0.1")
    uvicorn.run("knowledge.serve.app:app", host=host, port=port, log_level="info")
