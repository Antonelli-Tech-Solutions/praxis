"""U3: claim-keyed slot recall (in-memory VectorGraph path, no DB)."""

from knowledge.knowledge_graph.knowledge_graph_def import Claim
from knowledge.knowledge_graph.knowledge_graph_variants.vector_graph import VectorGraph
from knowledge.knowledge_graph.write_policy.parent_write_step import WriteStep
from knowledge.knowledge_graph.write_policy.write_policy_def import WriteDecision


class _MappedClaims(WriteStep):
    """Stand-in extractor: assigns claims by exact text match."""

    consumes_candidates = False

    def __init__(self, mapping: dict[str, list[Claim]]) -> None:
        self._mapping = mapping

    def apply(self, decision: WriteDecision) -> None:
        decision.claims = list(self._mapping.get(decision.text, []))


class _CaptureClaimCandidates(WriteStep):
    """Records the slot recall the store filled before this step ran."""

    consumes_claim_candidates = True

    def __init__(self) -> None:
        self.seen: list = []

    def apply(self, decision: WriteDecision) -> None:
        self.seen = list(decision.claim_candidates)


def _graph(mapping, capture):
    return VectorGraph(policy=[_MappedClaims(mapping), capture])


def test_same_functional_slot_is_recalled():
    cap = _CaptureClaimCandidates()
    mapping = {
        "pile invented 1801": [Claim(subject="voltaic pile", attribute="invention year",
                                     value="1801", functional=True)],
        "pile invented 1799": [Claim(subject="voltaic pile", attribute="invention year",
                                     value="1799", functional=True)],
    }
    g = _graph(mapping, cap)
    g.write("pile invented 1801", state="active")  # seed
    g.write("pile invented 1799", state="active")  # incoming, same slot
    assert len(cap.seen) == 1
    assert cap.seen[0].value == "1801"
    assert (cap.seen[0].subject, cap.seen[0].attribute) == ("voltaic pile", "invention year")


def test_non_functional_slot_is_not_recalled():
    cap = _CaptureClaimCandidates()
    mapping = {
        "volta discovered methane": [Claim(subject="volta", attribute="discovery",
                                           value="methane", functional=False)],
        "volta discovered series": [Claim(subject="volta", attribute="discovery",
                                          value="electrochemical series", functional=False)],
    }
    g = _graph(mapping, cap)
    g.write("volta discovered methane", state="active")
    g.write("volta discovered series", state="active")
    assert cap.seen == []  # multi-valued attribute never recalls a conflict


def test_different_slot_is_not_recalled():
    cap = _CaptureClaimCandidates()
    mapping = {
        "como 1774": [Claim(subject="como professorship", attribute="appointment year",
                            value="1774", functional=True)],
        "pavia 1779": [Claim(subject="pavia professorship", attribute="appointment year",
                             value="1779", functional=True)],
    }
    g = _graph(mapping, cap)
    g.write("como 1774", state="active")
    g.write("pavia 1779", state="active")
    assert cap.seen == []  # same attribute, different subject -> different slot
