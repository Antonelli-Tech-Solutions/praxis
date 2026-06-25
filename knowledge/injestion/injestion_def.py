"""Pydantic data models for the ingestion stage.

Centralizes the typed objects ingestion produces, mirroring ``eval_def.py`` for
the harness. The ``Ingestor`` contract lives in ``parent_injestor.py``.
"""

from __future__ import annotations

from pydantic import BaseModel


class Insight(BaseModel):
    """A single distilled unit of knowledge.

    ``raw_text`` is the only required field; the rest are additive metadata that
    richer ingestion fills in (and that the store/reader use for dedup,
    provenance, scope, and confidence). Defaults keep older callers and the
    existing eval cases valid.
    """

    raw_text: str
    source: str | None = None  # provenance: session/turn/file the insight came from
    confidence: float = 1.0  # 0..1; raised on repeated independent observation
    scope: str | None = None  # service / directory / "global"; supplied by the runner
    category: str | None = None  # e.g. error_fix | constraint | pattern | api_behavior
    observation_count: int = 1  # times this insight has been seen
    tabular: bool = False  # distilled from detected tabular/templated input; signals
    # the write path to flag the write so the deduper's slot-guard engages (sibling
    # rows of a table must not be silently merged — loss point B).
