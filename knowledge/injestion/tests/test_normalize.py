"""U1: canonical-PNG normalization + PSD extraction."""

from __future__ import annotations

import io

import pytest

from knowledge.injestion.image import normalize as norm
from knowledge.injestion.image.normalize import NormalizedAsset, normalize


def _write_image(path, *, mode="RGB", size=(8, 6), fmt="PNG", color=(255, 0, 0)):
    from PIL import Image

    img = Image.new(mode, size, color)
    img.save(path, format=fmt)
    return path


def _is_png(data: bytes) -> bool:
    return data[:8] == b"\x89PNG\r\n\x1a\n"


def test_png_returns_canonical_png_and_dims(tmp_path):
    p = _write_image(tmp_path / "a.png", size=(8, 6))
    asset = normalize(p)
    assert isinstance(asset, NormalizedAsset)
    assert asset.dims == (8, 6)
    assert _is_png(asset.png_bytes)
    assert asset.layer_names == []


def test_jpg_reencoded_to_png_dims_preserved(tmp_path):
    p = _write_image(tmp_path / "b.jpg", fmt="JPEG", size=(10, 4))
    asset = normalize(p)
    assert asset is not None
    assert asset.dims == (10, 4)
    assert _is_png(asset.png_bytes)  # canonicalized away from JPEG


def test_palette_mode_normalized(tmp_path):
    p = _write_image(tmp_path / "c.gif", mode="P", fmt="GIF", size=(5, 5))
    asset = normalize(p)
    assert asset is not None
    assert _is_png(asset.png_bytes)


def test_unknown_type_returns_none(tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("not an image", encoding="utf-8")
    assert normalize(p) is None


def test_corrupt_image_returns_none(tmp_path):
    p = tmp_path / "broken.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n garbage not really a png")
    assert normalize(p) is None  # logged, not raised


class _FakeLayer:
    def __init__(self, name):
        self.name = name


class _FakePSD:
    """Stand-in for psd_tools.PSDImage with a thumbnail and named layers."""

    def __init__(self, names, thumb, composite_called):
        self._names = names
        self._thumb = thumb
        self._composite_called = composite_called
        self.width, self.height = thumb.size

    def descendants(self):
        return [_FakeLayer(n) for n in self._names]

    def thumbnail(self):
        return self._thumb

    def composite(self):  # should NOT be called when a thumbnail exists
        self._composite_called.append(True)
        return self._thumb


def test_psd_extracts_layer_names_and_prefers_thumbnail(tmp_path, monkeypatch):
    from PIL import Image

    thumb = Image.new("RGBA", (12, 9), (0, 0, 255, 255))
    composite_called: list[bool] = []
    fake = _FakePSD(["mascot_body", "bg_gradient_blue", "CTA"], thumb, composite_called)

    import psd_tools

    monkeypatch.setattr(psd_tools.PSDImage, "open", classmethod(lambda cls, p: fake))

    p = tmp_path / "art.psd"
    p.write_bytes(b"fake psd bytes")
    asset = normalize(p)

    assert asset is not None
    assert asset.dims == (12, 9)
    assert _is_png(asset.png_bytes)
    assert asset.layer_names == ["mascot_body", "bg_gradient_blue", "CTA"]
    assert composite_called == []  # thumbnail preferred, no full rasterize


def test_psd_read_failure_returns_none(tmp_path, monkeypatch):
    import psd_tools

    def _boom(cls, p):
        raise ValueError("unsupported psd feature")

    monkeypatch.setattr(psd_tools.PSDImage, "open", classmethod(_boom))
    p = tmp_path / "bad.psd"
    p.write_bytes(b"fake")
    assert normalize(p) is None
