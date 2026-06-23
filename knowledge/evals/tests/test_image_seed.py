"""U5: eval schema + harness wiring for image-asset seeding."""

from __future__ import annotations

import pytest

from knowledge.evals import run
from knowledge.evals.eval_def import DeterministicCheckRef, EvalCase, SeededInsight


def _png(path, color=(10, 20, 30), size=(8, 8)):
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="PNG")
    return path


def _case(**kw) -> EvalCase:
    base = dict(
        id="img_case",
        component="ingestion",
        deterministic_checks=[DeterministicCheckRef(name="x", ref="mod:fn")],
    )
    base.update(kw)
    return EvalCase.model_validate(base)


class SpyGraph:
    def __init__(self):
        self.writes = []

    def write(self, content, *, state="proposed"):
        self.writes.append((content, state))

    def read(self, context=None):
        return ""


def test_caption_model_requires_real_captions_capability():
    case = _case(caption_model="google/gemini-flash-1.5-8b")
    assert "real_captions" in run.case_needs(case)


def test_via_image_ingestor_requires_sandbox():
    case = _case(seeded_insight=SeededInsight(via_image_ingestor=["assets"]))
    assert "sandbox" in run.case_needs(case)


def test_caption_case_skips_offline_without_source(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(run, "CAPTION_CACHE_DIR", tmp_path / "empty_captions")
    case = _case(caption_model="m/vlm")
    unmet = run.unmet_needs(case, run.FakeRunner())
    assert "real_captions" in unmet  # no cassette, no key -> case would SKIP


def test_committed_cassette_advertises_capability(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cap_dir = tmp_path / "captions"
    cap_dir.mkdir()
    (cap_dir / "m_vlm.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(run, "CAPTION_CACHE_DIR", cap_dir)
    assert "real_captions" in run.harness_capabilities()


def test_seed_image_assets_writes_active_cards(tmp_path):
    case_dir = tmp_path / "case"
    _png(case_dir / "fixture" / "assets" / "mascot.png")
    _png(case_dir / "fixture" / "assets" / "bg.png", color=(200, 50, 50))
    case = _case(
        source_dir=str(case_dir),
        seeded_insight=SeededInsight(via_image_ingestor=["assets"]),
        # no caption_model -> deterministic-only cards, no caption source needed
    )
    graph = SpyGraph()
    run._seed_image_assets(case, graph)
    assert graph.writes, "expected image cards written"
    assert all(state == "active" for _, state in graph.writes)
    assert any("path=assets/" in content for content, _ in graph.writes)


def test_no_image_assets_is_noop(tmp_path):
    case = _case()  # no via_image_ingestor
    graph = SpyGraph()
    run._seed_image_assets(case, graph)
    assert graph.writes == []


def test_text_only_case_schema_unchanged():
    # existing-style case validates with the new optional fields defaulted
    case = _case(seeded_insight=SeededInsight(via_ingestor=["some text"]))
    assert case.caption_model is None
    assert case.seeded_insight.via_image_ingestor == []
