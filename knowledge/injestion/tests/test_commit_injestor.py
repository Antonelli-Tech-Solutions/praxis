"""U2: offline tests for CommitIngestor — one structured LLM call -> Insight[].

Drives a scripted fake Llm (deterministic, no network). Covers R1 (structured
distill -> typed insights with source/scope/category) and R2 (durable-only;
churn ignored), plus the precision-first drop-malformed behavior.
"""

from __future__ import annotations

import json
from typing import Callable

from knowledge.injestion.injestor_variants.commit_injestor import CommitIngestor
from knowledge.knowledge_graph.knowledge_graph_variants.in_memory_graph import InMemoryGraph
from knowledge.llm.llm_def import ChatMessage
from knowledge.llm.parent_llm import Llm


class FakeLlm(Llm):
    """Returns a canned reply (or one computed from the prompt); records calls."""

    def __init__(self, reply: str | Callable[[str], str]) -> None:
        self.reply = reply
        self.calls: list[tuple[list[ChatMessage], dict | None]] = []

    def complete(self, messages, *, temperature=0.0, max_tokens=1024, response_format=None):
        self.calls.append((messages, response_format))
        prompt = messages[-1].content
        return self.reply(prompt) if callable(self.reply) else self.reply


def _ingestor(reply):
    return CommitIngestor(InMemoryGraph(), FakeLlm(reply))


def test_two_insights_with_source_scope_category():
    # Covers R1: a structured two-insight reply -> two typed Insights, one LLM call.
    reply = json.dumps({"insights": [
        {"text": "Import knowledge lazily inside a yoyo step.",
         "scope": "module:migrations", "category": "gotcha"},
        {"text": "Keep UMAP n_neighbors low to avoid one mega-cluster.",
         "scope": "file:knowledge/knowledge_graph/clustering.py", "category": "decision"},
    ]})
    ing = _ingestor(reply)

    insights = ing.synthesis("UNIT: git/pr:48\nTITLE: ...", source="git/pr:48")

    assert len(insights) == 2
    assert [i.raw_text for i in insights] == [
        "Import knowledge lazily inside a yoyo step.",
        "Keep UMAP n_neighbors low to avoid one mega-cluster.",
    ]
    assert all(i.source == "git/pr:48" for i in insights)
    assert insights[0].scope == "module:migrations" and insights[0].category == "gotcha"
    assert insights[1].category == "decision"
    # Exactly one structured call (response_format passed).
    assert len(ing.llm.calls) == 1
    assert ing.llm.calls[0][1] is not None


def test_churn_yields_no_insights_but_gotcha_does():
    # Covers R2: a version-bump/rename unit distills to []; a documented gotcha -> an insight.
    # Key on a token that appears only in the unit input, never in the distill prompt.
    def reply(prompt: str) -> str:
        unit_input = prompt.split("UNIT INPUT:", 1)[-1]
        if "GOTCHA-DOC" in unit_input:
            return json.dumps({"insights": [
                {"text": "yoyo execs migrations with repo root off sys.path.",
                 "scope": "repo", "category": "gotcha"}]})
        return json.dumps({"insights": []})

    ing = _ingestor(reply)

    assert ing.synthesis("BODY: bump deps to 2.0", source="git/pr:1") == []
    out = ing.synthesis("BODY: GOTCHA-DOC document the yoyo import gotcha", source="git/pr:2")
    assert len(out) == 1 and out[0].category == "gotcha"


def test_malformed_entry_dropped_siblings_survive():
    # Edge: an entry missing `text` is dropped; the well-formed sibling survives, no raise.
    reply = json.dumps({"insights": [
        {"scope": "repo", "category": "gotcha"},  # malformed: no text
        {"text": "Real durable fact.", "scope": "repo", "category": "convention"},
    ]})
    ing = _ingestor(reply)

    out = ing.synthesis("doc", source="git/pr:3")

    assert [i.raw_text for i in out] == ["Real durable fact."]


def test_empty_response_yields_empty_not_crash():
    # Edge: an empty/whitespace reply -> [], not an exception.
    assert _ingestor("   ").synthesis("doc", source="git/pr:4") == []
    assert _ingestor("not json at all").synthesis("doc", source="git/pr:5") == []
