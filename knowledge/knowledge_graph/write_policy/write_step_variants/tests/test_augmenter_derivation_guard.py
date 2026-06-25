"""Unit tests for the Augmenter's no-merge guards (Fix 1, gap H5).

These run offline: a fake judge stands in for the live ``AugmentJudge`` LLM, so
the tests exercise the *decision logic* (when the Augmenter refuses to fold a
write into a candidate) without a Postgres DSN or an OpenRouter key.

Two guards are asserted:
  1. a write carrying ``derived_from`` is a declared derivation, never an augment
     target (else the distinct node + its derived_from edge are lost);
  2. a write never merges across distinct ``category`` values (a "learning" must
     not be folded into a "requirement").
And the positive path: a same-category, non-derived additive note still merges.
"""

from __future__ import annotations

from knowledge.knowledge_graph.knowledge_graph_def import Fact, SearchHit
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants.augmenter import Augmenter


class _AlwaysMergeJudge:
    """Stub judge that would always merge — so any no-op is the guard, not the judge."""

    def merged_text(self, new_text: str, existing_text: str) -> str:
        return f"{existing_text} + {new_text}"


def _hit(fid: str, text: str, category: str | None = None) -> SearchHit:
    return SearchHit(fact=Fact(id=fid, text=text, category=category), score=0.9)


def _decision(text: str, *, category: str | None = None, derived_from=None) -> WriteDecision:
    d = WriteDecision(text=text)
    d.category = category
    d.derived_from = list(derived_from or [])
    return d


def test_derived_from_write_is_exempt_from_merge():
    aug = Augmenter(judge=_AlwaysMergeJudge())
    decision = _decision(
        "Daily completion implemented in completion.py",
        category="learning",
        derived_from=["req1"],
    )
    decision.candidates = [_hit("req1", "Daily completion requirement", category="requirement")]
    aug.apply(decision)
    # Declared derivation: stays an add, never folds into its source.
    assert decision.action == "add"
    assert decision.update_target_id is None


def test_distinct_category_is_not_merged():
    aug = Augmenter(judge=_AlwaysMergeJudge())
    decision = _decision("a learning about X", category="learning")
    decision.candidates = [_hit("r1", "a requirement about X", category="requirement")]
    aug.apply(decision)
    assert decision.action == "add"
    assert decision.update_target_id is None


def test_same_category_additive_note_still_merges():
    # Regression guard for augment_additive_merge: genuinely additive same-kind
    # notes must still fold together.
    aug = Augmenter(judge=_AlwaysMergeJudge())
    decision = _decision("likes cheese pizza", category="preference")
    decision.candidates = [_hit("p1", "loves chicken pizza", category="preference")]
    aug.apply(decision)
    assert decision.action == "augment"
    assert decision.update_target_id == "p1"
    assert decision.augment_text


def test_unset_categories_still_merge():
    aug = Augmenter(judge=_AlwaysMergeJudge())
    decision = _decision("likes cheese pizza", category=None)
    decision.candidates = [_hit("p1", "loves chicken pizza", category=None)]
    aug.apply(decision)
    assert decision.action == "augment"
    assert decision.update_target_id == "p1"
