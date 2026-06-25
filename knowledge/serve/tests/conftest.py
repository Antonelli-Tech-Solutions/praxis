"""Shared test fixtures for the serve package.

Offline tests run with PRAXIS_AUTH_DISABLED=1 so the ``current_user`` dependency
returns a fixed dev principal instead of verifying a real Cognito JWT (see
auth.py). Set at import time so it covers module-level app construction too.
"""

from __future__ import annotations

import os

os.environ.setdefault("PRAXIS_AUTH_DISABLED", "1")

# Never export traces from the test suite: create_app() calls setup_tracing(),
# and a developer .env may point PHOENIX_COLLECTOR_ENDPOINT at the LIVE Phoenix —
# tests must not pollute prod observability (nor pay the export retry latency).
# Set empty (not popped): app.py runs load_dotenv() at import, which would
# re-add a popped key from .env; an existing empty value is left untouched
# (override=False) and makes setup_tracing() a no-op.
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = ""

import pytest


@pytest.fixture
def unique_org(request):
    # Unique per test node so reruns and parallel tenants never collide.
    return "test_" + request.node.name
