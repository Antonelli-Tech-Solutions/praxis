"""Smoke test for the claims-backfill migration's pure helpers.

Exercises the DB-free core (``compute_contradiction_edges`` / ``edges_match``)
against a fixture so the re-evaluation logic is covered without a live Postgres.
The DB plumbing is left to the orchestrator's integration run.
"""

from __future__ import annotations

from knowledge.knowledge_graph.knowledge_graph_def import Claim
from knowledge.knowledge_graph.write_policy.write_step_variants.claim_conflict_detector import (
    ClaimConflictDetector,
)
from migrations.m2026_06_24_claims_backfill import (
    compute_contradiction_edges,
    edges_match,
    normalized_pair,
)


def _detector() -> ClaimConflictDetector:
    # No value judge: numeric clashes are deterministic, fuzzy ones suppress.
    return ClaimConflictDetector(judge=None)


def _year(fid_subject_value):
    fid, subject, value = fid_subject_value
    return Claim(subject=subject, attribute="invention year", value=value, functional=True)


def test_numeric_functional_clash_is_an_edge():
    fact_claims = {
        "a": [_year(("a", "voltaic pile", "1799"))],
        "b": [_year(("b", "voltaic pile", "1800"))],
        "c": [_year(("c", "voltaic pile", "1801"))],
    }
    edges = compute_contradiction_edges(fact_claims, _detector())
    # All three compete on the same functional slot with distinct years.
    assert edges == {
        normalized_pair("a", "b"),
        normalized_pair("a", "c"),
        normalized_pair("b", "c"),
    }


def test_distinct_subjects_do_not_conflict():
    fact_claims = {
        "a": [Claim(subject="galvani", attribute="discovery", value="animal electricity", functional=True)],
        "b": [Claim(subject="volta", attribute="discovery", value="electric battery", functional=True)],
    }
    assert compute_contradiction_edges(fact_claims, _detector()) == set()


def test_multivalued_attribute_never_conflicts():
    fact_claims = {
        "a": [Claim(subject="volta", attribute="discovery", value="battery", functional=False)],
        "b": [Claim(subject="volta", attribute="discovery", value="methane", functional=False)],
    }
    assert compute_contradiction_edges(fact_claims, _detector()) == set()


def test_fuzzy_values_suppress_without_a_judge():
    # Non-numeric differing values + no gray-zone judge -> precision-first suppress.
    fact_claims = {
        "a": [Claim(subject="pile", attribute="description", value="first electric battery", functional=True)],
        "b": [Claim(subject="pile", attribute="description", value="early electric battery", functional=True)],
    }
    assert compute_contradiction_edges(fact_claims, _detector()) == set()


def test_facts_with_no_claims_are_skipped():
    fact_claims = {"a": [], "b": [_year(("b", "voltaic pile", "1800"))]}
    assert compute_contradiction_edges(fact_claims, _detector()) == set()


def test_edges_match_is_a_pure_set_diff():
    stored = {normalized_pair("a", "b"), normalized_pair("c", "d")}  # one real, one stale FP
    computed = {normalized_pair("a", "b"), normalized_pair("e", "f")}  # keep one, add one
    to_add, to_remove = edges_match(stored, computed)
    assert to_add == {normalized_pair("e", "f")}
    assert to_remove == {normalized_pair("c", "d")}


def test_reevaluation_is_idempotent():
    # Recomputing against an already-reconciled set yields an empty diff.
    fact_claims = {
        "a": [_year(("a", "voltaic pile", "1799"))],
        "b": [_year(("b", "voltaic pile", "1800"))],
    }
    computed = compute_contradiction_edges(fact_claims, _detector())
    to_add, to_remove = edges_match(computed, computed)
    assert to_add == set() and to_remove == set()


def test_normalized_pair_is_undirected():
    assert normalized_pair("b", "a") == normalized_pair("a", "b")
