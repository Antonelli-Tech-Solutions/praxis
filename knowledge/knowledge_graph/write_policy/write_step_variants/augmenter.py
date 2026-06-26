"""Mem0-style UPDATE/merge (augment): fold a related-but-additive note into an existing fact.

The gap the Deduper + ClaimConflictDetector path leaves open: two notes that are
neither the *same lesson* (Deduper skips them) nor a *contradiction*
(ClaimConflictDetector finds no incompatible functional-slot clash), but are
clearly about the same thing and *additive* — "likes cheese pizza" + "loves
chicken pizza". Mem0's reconciliation would UPDATE the existing memory into one
merged fact ("likes cheese and chicken pizza") rather than keeping two rows or
flagging a false contradiction.

The :class:`Augmenter` runs right after the Deduper (so exact/same-lesson dups are
already collapsed) and before the structural conflict detector (so a genuine
clash is still flagged, not silently merged). For each recalled candidate that is
related but not identical, it asks an :class:`AugmentJudge` whether the new note
should be *merged into* that existing fact and, if so, for the synthesized merged
text. On yes it sets ``action="augment"`` with ``update_target_id`` (the existing
fact to rewrite) and ``augment_text`` (the merged survivor text); the store's
``_augment`` rewrites that fact's text (re-embeds), bumps observation_count, and
keeps a single fact.

Determinism + graceful degradation mirror ``Deduper``/``MergeJudge``:
- a ``VerdictCassette`` replays committed verdicts offline (loud-miss on a stale one);
- with a live ``llm`` and no cassette, it computes directly (production path);
- with neither, ``merged_text`` returns ``None`` — the step is a no-op (the write
  falls through to add/conflict exactly as before).
"""

from __future__ import annotations

from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision
from knowledge.knowledge_graph.write_policy.write_step_variants.augment_judge import (
    AugmentJudge,
)
from knowledge.knowledge_graph.write_policy.write_step_variants.deduper import (
    TABULAR_FLAG,
)
from knowledge.knowledge_graph.write_policy.write_step_variants.semantic_conflict_detector import (
    SemanticConflictJudge,
)


class Augmenter(WriteStep):
    """Fold a related-but-additive note into an existing fact (Mem0 UPDATE op)."""

    consumes_candidates = True

    def __init__(
        self,
        judge: AugmentJudge | None = None,
        conflict_judge: SemanticConflictJudge | None = None,
    ) -> None:
        self.judge = judge
        # Contradiction-precedence guard. The Augmenter runs BEFORE the conflict
        # detectors, so without this an additive merge can silently fold a newcomer
        # into an incumbent the conflict path would have flagged -- blending two
        # CONTRADICTORY facts and defeating ``on_conflict="surface"`` (the planning
        # loop's self-consistency mechanism). When set, the judge vetoes any proposed
        # merge whose two facts logically contradict, so the write falls through to a
        # plain add and the downstream detectors flag the pair instead. Only consulted
        # on a merge the AugmentJudge already approved, so it adds no LLM calls (and no
        # offline cassette entries) for the common no-merge path.
        self.conflict_judge = conflict_judge

    def apply(self, decision: WriteDecision) -> None:
        # Skip if a prior step already decided this write (exact/same-lesson dup),
        # or there's nothing to merge into, or no judge to decide.
        if decision.dropped or decision.action != "add":
            return
        # A derived write (non-empty derived_from) explicitly declares a NEW fact built
        # on a source: it must land as its own distinct node carrying the derivation
        # edge, never folded back into the source. Never additively merge it away.
        if decision.derived:
            return
        if not decision.candidates or self.judge is None:
            return
        # A write that declares derived_from is an explicit NEW fact built on its
        # sources (gap H5: a learning derived from a requirement), not a duplicate.
        # Folding it into another fact would destroy the distinct node and its
        # derived_from edge, so a declared derivation is never an augment target.
        if decision.derived_from:
            return
        # A tabular-flagged write is a deterministic, atomic row linearized one-per-row
        # from structured/templated input. The Deduper's slot-guard keeps such rows
        # distinct from each OTHER, but the Augmenter's broader semantic recall can still
        # fold a row into a pre-existing NON-tabular incumbent that merely shares its
        # subject (e.g. a "team_day: date, resolved via the 3AM boundary" row blended into
        # a prose rule about that boundary). A structured row must stay its own fact, so
        # never additively merge a tabular write away.
        if TABULAR_FLAG in decision.flags:
            return
        # The Deduper's slot-guard already ruled these candidates distinct (different
        # functional slot) or conflicting (same slot, different value); never fold an
        # additive merge into them, or we'd reintroduce the silent over-merge the guard
        # blocked one stage earlier.
        no_merge = set(decision.no_merge_ids)
        for hit in decision.candidates:
            if hit.fact.id in no_merge:
                continue
            # An exact dup would have been collapsed by the Deduper already; skip it
            # defensively so the judge never merges a fact into its own twin.
            if hit.fact.text.strip() == decision.text.strip():
                continue
            # Never merge across distinct category values: a "learning" must not be
            # folded into a "requirement". Only merge when categories match (or are
            # both unset), so an additive note still merges into its same-kind peer.
            hit_category = getattr(hit.fact, "category", None)
            if (
                decision.category is not None
                and hit_category is not None
                and decision.category != hit_category
            ):
                continue
            merged = self.judge.merged_text(decision.text, hit.fact.text)
            if merged and merged.strip():
                # Contradiction precedence: never fold a newcomer into an incumbent it
                # logically contradicts -- that would blend a self-contradictory fact and
                # rob the downstream detectors of a pair to flag. Veto the merge and let
                # the write fall through to a plain add (precision-first: a None/uncertain
                # verdict, or no judge, does NOT block the merge).
                if self.conflict_judge is not None:
                    try:
                        contradicts = self.conflict_judge.contradicts(
                            decision.text, hit.fact.text
                        )
                    except Exception:
                        contradicts = None
                    if contradicts:
                        continue
                decision.action = "augment"
                decision.update_target_id = hit.fact.id
                decision.augment_text = merged.strip()
                return
