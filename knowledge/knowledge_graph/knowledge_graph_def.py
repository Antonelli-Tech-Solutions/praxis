"""Shapes for the knowledge store (stored facts + search results)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Fact(BaseModel):
    """A stored unit of knowledge with its metadata.

    The persisted form of an :class:`~knowledge.injestion.injestion_def.Insight`
    plus storage bookkeeping. ``embedding`` is optional so a fact can exist
    before/without a vector (e.g. exact-dedup paths).
    """

    id: str
    text: str
    source: str | None = None
    confidence: float = 1.0
    scope: str | None = None
    category: str | None = None
    observation_count: int = 1
    embedding: list[float] | None = None
    flags: list[str] = Field(default_factory=list)  # e.g. ["contradiction:<id>"]


class SearchHit(BaseModel):
    """A fact returned by ``SearchableGraph.search`` with its relevance score."""

    fact: Fact
    score: float = 0.0


class Contradiction(BaseModel):
    """A detected contradiction between a newly-written fact and an existing one.

    Surfaced for human review (the elevation surface) — the dashboard's
    Contradictions tab consumes these pairs.
    """

    flagged: Fact  # the newer fact whose write tripped the conflict check
    conflicting: Fact  # the existing fact it appears to contradict
