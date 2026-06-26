"""Derived-write guard for the Augmenter (and Deduper same-lesson merge).

A write carrying a non-empty ``derived_from`` declares a NEW fact built on a source
(a learning derived from the requirement it implements). It must stay its own distinct
node carrying the derivation edge — never be folded back into the source by the
Mem0-style additive Augmenter (or the Deduper's same-lesson merge).

These drive the in-memory pipeline offline:

* ``recall_floor=-1.0`` forces the source into the shared recall set despite the
  ``FakeEmbedder``'s ~0 cosine (so the Augmenter's judge is actually consulted);
* an always-"merge yes" ``AugmentJudge`` stands in for the real precision judge —
  without the guard it would fold the derived note into its source, so a green test
  proves the ``derived`` flag is what keeps them distinct. A non-derived additive
  write through the SAME pipeline still merges (the additive path is unchanged).
"""

from __future__ import annotations

from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph
from knowledge.knowledge_graph.write_policy.write_step_variants.augment_judge import (
    AugmentJudge,
)
from knowledge.knowledge_graph.write_policy.write_step_variants.augmenter import Augmenter
from knowledge.llm.llm_variants.fake_llm import FakeLlm

# The judge would fold every candidate without the guard.
_MERGE_YES = '{"merge": true, "merged_text": "merged survivor"}'


def _graph():
    judge = AugmentJudge(llm=FakeLlm(default=_MERGE_YES))
    # recall_floor=-1.0: force the hash-embedded source into the recall set so the
    # Augmenter's (always-yes) judge is actually consulted.
    return VectorGraph(policy=[Augmenter(judge=judge)], recall_floor=-1.0)


def _active(g):
    return [f for f in g.facts if f.state == "active"]


def test_derived_write_not_merged_into_source():
    # A learning derived_from the requirement it implements must stay a distinct fact,
    # even though the always-yes Augmenter would otherwise fold it into the source.
    g = _graph()
    req = g.write("Daily completion requires the rep and all three ratings.", state="active")
    g.write(
        "Daily completion is implemented in completion_status(); checklist ignored.",
        state="active",
        derived_from=[req.added_fact_id or "req"],
    )
    assert len(_active(g)) == 2  # derived learning kept distinct, not augmented away


def test_non_derived_additive_write_still_merges():
    # Same pipeline, no derived_from: the additive Augmenter still merges (one fact),
    # proving the guard is keyed on derived_from presence, not a blanket no-merge.
    g = _graph()
    g.write("The user likes cheese pizza.", state="active")
    g.write("The user loves chicken pizza.", state="active")
    assert len(_active(g)) == 1  # additive merge path unchanged
