"""Content + perceptual hashing and near-duplicate clustering for assets.

Two hashes, two jobs:

- ``content_hash`` (sha256 of canonical PNG bytes) — *exact* identity. Drives
  idempotent reconcile (skip unchanged files) and exact-dup collapse.
- ``perceptual_hash`` (pHash) — *near* identity. Drives variant grouping: a PSD
  and its exported PNG, ``@2x`` variants, and recolors hash close together.

Clustering is by **connected components** over a similarity graph (edge =
Hamming distance ≤ threshold), not transitive equivalence classes. The
near-duplicate relation is non-transitive — A~B and B~C does not imply A~C — so
we link by edges and let components form naturally through shared neighbors.
"""

from __future__ import annotations

import hashlib
import io

# pHash Hamming-distance threshold (64-bit hash). Conservative default; tune
# against a real dump (see plan Open Questions).
DEFAULT_THRESHOLD = 8


def content_hash(png_bytes: bytes) -> str:
    """Exact content identity: sha256 hex of the canonical PNG bytes."""
    return hashlib.sha256(png_bytes).hexdigest()


def perceptual_hash(png_bytes: bytes):
    """Perceptual (pHash) of the canonical PNG. Returns an ``imagehash.ImageHash``."""
    import imagehash
    from PIL import Image

    with Image.open(io.BytesIO(png_bytes)) as img:
        return imagehash.phash(img)


def cluster(hashes: list, *, threshold: int = DEFAULT_THRESHOLD) -> list[list[int]]:
    """Group indices into connected components by perceptual-hash proximity.

    ``hashes`` is a list of ``imagehash.ImageHash`` (subtraction = Hamming
    distance). Returns a list of clusters, each a sorted list of indices into
    ``hashes``. Components are connected via edges (distance ≤ threshold), so
    chains link without requiring all-pairs similarity.
    """
    n = len(hashes)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i in range(n):
        for j in range(i + 1, n):
            if (hashes[i] - hashes[j]) <= threshold:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [sorted(members) for members in groups.values()]
