"""Normalize any supported visual asset to a canonical PNG + metadata.

Every supported raster type is decoded and re-encoded to a single canonical
form (PNG, RGBA) so everything downstream — hashing, dedup, captioning — runs
one uniform path regardless of the source format. PSDs are special only here:
their layer-name tree and embedded preview are extracted via ``psd-tools``
without a full pixel rasterize where a thumbnail is available.

``normalize`` is total and never raises on a bad asset: unknown types, corrupt
bytes, and unreadable files return ``None`` with a logged note, so a single bad
file in a dump never aborts ingestion.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Raster formats Pillow decodes directly. PSDs go through psd-tools instead.
_RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
_PSD_SUFFIXES = {".psd", ".psb"}


@dataclass
class NormalizedAsset:
    """A source asset reduced to a uniform canonical form.

    ``png_bytes`` is the canonical RGBA PNG encoding (the single representation
    everything downstream hashes/captions). ``dims`` is ``(width, height)``.
    ``layer_names`` is non-empty only for layered sources (PSD) — designer layer
    names are free, human-authored description.
    """

    png_bytes: bytes
    dims: tuple[int, int]
    layer_names: list[str] = field(default_factory=list)


def _encode_png(img) -> bytes:
    """Re-encode a Pillow image to canonical RGBA PNG bytes."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _normalize_raster(path: Path) -> NormalizedAsset | None:
    from PIL import Image

    with Image.open(path) as img:
        img.load()
        dims = (img.width, img.height)
        return NormalizedAsset(png_bytes=_encode_png(img), dims=dims)


def _layer_names(psd) -> list[str]:
    """Collect named layers (and groups) in document order, skipping the root.

    Smart-object pixels are unsupported by psd-tools, but their *names* are still
    readable here — only the rasterized content is skipped (we never composite a
    smart object), so the name still contributes free signal.
    """
    names: list[str] = []
    for layer in psd.descendants():
        name = (getattr(layer, "name", None) or "").strip()
        if name:
            names.append(name)
    return names


def _normalize_psd(path: Path) -> NormalizedAsset | None:
    from psd_tools import PSDImage

    psd = PSDImage.open(path)
    names = _layer_names(psd)
    # Prefer the embedded composite preview (no per-layer rasterize) when present;
    # fall back to a composite only if the file has no thumbnail.
    preview = psd.thumbnail() if hasattr(psd, "thumbnail") else None
    if preview is None:
        preview = psd.composite()
    if preview is None:
        logger.warning("normalize: PSD %s has no renderable preview; skipping", path.name)
        return None
    return NormalizedAsset(
        png_bytes=_encode_png(preview),
        dims=(preview.width, preview.height),
        layer_names=names,
    )


def normalize(path: Path | str) -> NormalizedAsset | None:
    """Return the canonical form of ``path``, or ``None`` if unsupported/unreadable.

    Never raises: a bad or unsupported asset is logged and dropped so one file
    cannot abort a whole dump.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    try:
        if suffix in _RASTER_SUFFIXES:
            return _normalize_raster(path)
        if suffix in _PSD_SUFFIXES:
            return _normalize_psd(path)
    except Exception as exc:  # noqa: BLE001 - totality is the contract here
        logger.warning("normalize: failed to read %s (%s); skipping", path.name, exc)
        return None
    logger.info("normalize: unsupported file type %s; skipping", path.name)
    return None
