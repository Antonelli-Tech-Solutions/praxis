"""Image-asset ingestion helpers.

Pure, dependency-light modules that turn a folder of visual assets (PNG, PSD,
…) into derived text cards for the knowledge graph. The pieces:

- :mod:`normalize` — any supported asset -> canonical PNG bytes + metadata.
- :mod:`hashing`   — content hash (exact dedup) + perceptual hash (variant clusters).
- :mod:`cards`     — deterministic card text from path / folder / layers / dims.
- :mod:`captioner` — optional VLM caption (text), cached by content hash.

The orchestration lives in
``knowledge.injestion.injestor_variants.image_injestor.ImageIngestor``.
"""
