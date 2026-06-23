"""U6: caption-cassette refresh tooling."""

from __future__ import annotations

import json

import pytest

from knowledge.evals import caption_cache, run
from knowledge.evals.eval_def import DeterministicCheckRef, EvalCase, SeededInsight


def _png(path, color, size=(16, 16)):
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="PNG")


def _caption_case(case_dir):
    return EvalCase.model_validate(
        dict(
            id="img_case",
            component="ingestion",
            caption_model="m/vlm",
            source_dir=str(case_dir),
            seeded_insight=SeededInsight(via_image_ingestor=["assets"]),
            deterministic_checks=[DeterministicCheckRef(name="x", ref="mod:fn")],
        )
    )


def _two_distinct_assets(case_dir):
    from PIL import Image, ImageDraw

    assets = case_dir / "fixture" / "assets"
    assets.mkdir(parents=True)
    for i, name in enumerate(("a.png", "b.png")):
        img = Image.new("RGB", (32, 32), (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([2 + i * 6, 2, 12 + i * 6, 14], fill=(0, 0, 0))
        d.line([0, i * 9, 32, (i * 3) % 32], fill=(0, 0, 0), width=2)
        img.save(assets / name)


def test_refresh_records_one_caption_per_canonical(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(run, "CAPTION_CACHE_DIR", tmp_path / "captions")
    monkeypatch.setattr(caption_cache, "CAPTION_CACHE_DIR", tmp_path / "captions")

    calls = {"n": 0}

    def fake_complete(messages, model):
        calls["n"] += 1
        return f"caption {calls['n']}"

    # patch the captioner's default completion seam so no network is touched
    monkeypatch.setattr(
        "knowledge.injestion.image.captioner._default_complete", fake_complete
    )

    case_dir = tmp_path / "case"
    _two_distinct_assets(case_dir)
    rc = caption_cache.refresh(cases=[_caption_case(case_dir)])

    assert rc == 0
    cassette = tmp_path / "captions" / "m_vlm.json"
    assert cassette.exists()
    data = json.loads(cassette.read_text(encoding="utf-8"))
    assert len(data) == 2  # two distinct canonical images
    assert calls["n"] == 2


def test_refresh_without_key_errors(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert caption_cache.refresh(cases=[]) == 1


def test_refresh_no_caption_cases_is_noop(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    assert caption_cache.refresh(cases=[]) == 0
