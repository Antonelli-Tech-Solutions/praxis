"""Run the candidate API: uv run python -m knowledge.serve"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PRAXIS_API_PORT", "8000"))
    uvicorn.run("knowledge.serve.app:app", host="127.0.0.1", port=port, log_level="info")
