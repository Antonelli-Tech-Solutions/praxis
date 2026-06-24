"""U3: content/perceptual hashing + connected-component variant clustering."""

from __future__ import annotations

from knowledge.injestion.image import hashing
from knowledge.injestion.injestor_variants.image_injestor import ImageIngestor


def _drawn_png(path, seed, size=(32, 32)):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(img)
    x = (seed * 7) % (size[0] - 8)
    y = (seed * 11) % (size[1] - 8)
    d.rectangle([x, y, x + 8, y + 8], fill=(0, 0, 0))
    d.line([0, seed % size[1], size[0], (seed * 3) % size[1]], fill=(0, 0, 0), width=2)
    img.save(path, format="PNG")
    return path


class SpyGraph:
    def __init__(self):
        self.writes = []

    def write(self, content, *, state="proposed"):
        self.writes.append((content, state))

    def read(self, context=None):
        return ""


# --- cluster() unit: connected components, non-transitive ------------------ #
def test_cluster_connected_components_non_transitive():
    import imagehash

    # A~B (4 bits), B~C (4 bits), A≁C (8 bits). threshold=4 => one component via B.
    a = imagehash.hex_to_hash("0000000000000000")
    b = imagehash.hex_to_hash("000000000000000f")  # 4 bits from A
    c = imagehash.hex_to_hash("00000000000000ff")  # 4 from B, 8 from A
    assert (a - b) == 4 and (b - c) == 4 and (a - c) == 8
    clusters = hashing.cluster([a, b, c], threshold=4)
    assert clusters == [[0, 1, 2]]


def test_cluster_separates_distant_hashes():
    import imagehash

    a = imagehash.hex_to_hash("0000000000000000")
    far = imagehash.hex_to_hash("ffffffffffffffff")  # 64 bits away
    clusters = hashing.cluster([a, far], threshold=8)
    assert sorted(clusters) == [[0], [1]]


def test_content_hash_stable_and_distinct(tmp_path):
    from knowledge.injestion.image.normalize import normalize

    p1 = _drawn_png(tmp_path / "a.png", 1)
    p2 = _drawn_png(tmp_path / "b.png", 2)
    h1 = hashing.content_hash(normalize(p1).png_bytes)
    h1b = hashing.content_hash(normalize(p1).png_bytes)
    h2 = hashing.content_hash(normalize(p2).png_bytes)
    assert h1 == h1b and h1 != h2 and len(h1) == 64


# --- ingestor reconcile + collapse ----------------------------------------- #
def test_byte_identical_files_collapse_to_one_card(tmp_path):
    from PIL import Image

    img = Image.new("RGB", (32, 32), (255, 255, 255))
    img.save(tmp_path / "logo.png", format="PNG")
    img.save(tmp_path / "logo_copy.png", format="PNG")  # identical bytes
    insights = ImageIngestor(SpyGraph()).synthesis(str(tmp_path))
    assert len(insights) == 1
    # the non-canonical identical file is recorded as a variant
    assert "variants:" in insights[0].raw_text


def test_near_duplicate_resized_collapses_with_variant(tmp_path):
    from PIL import Image

    _drawn_png(tmp_path / "big.png", seed=5, size=(64, 64))
    # a true resize of the SAME image — different bytes, near-identical pHash
    with Image.open(tmp_path / "big.png") as im:
        im.resize((24, 24)).save(tmp_path / "small.png", format="PNG")
    insights = ImageIngestor(SpyGraph()).synthesis(str(tmp_path))
    assert len(insights) == 1
    card = insights[0].raw_text
    assert "path=assets/big.png" in card  # larger area picked canonical
    assert "small.png" in card  # variant listed


def test_idempotent_reconcile_skips_seen(tmp_path):
    _drawn_png(tmp_path / "a.png", 1)
    seen: set[str] = set()
    ing = ImageIngestor(SpyGraph(), seen_hashes=seen)
    first = ing.synthesis(str(tmp_path))
    assert len(first) == 1 and seen  # canonical hash now recorded in seen
    # re-run with the same populated seen-set: nothing new
    again = ImageIngestor(SpyGraph(), seen_hashes=seen).synthesis(str(tmp_path))
    assert again == []


def test_adding_one_file_emits_one_card(tmp_path):
    _drawn_png(tmp_path / "a.png", 1)
    seen: set[str] = set()
    ImageIngestor(SpyGraph(), seen_hashes=seen).synthesis(str(tmp_path))
    _drawn_png(tmp_path / "b.png", 2)  # new, perceptually distinct file
    added = ImageIngestor(SpyGraph(), seen_hashes=seen).synthesis(str(tmp_path))
    assert len(added) == 1
    assert "b.png" in added[0].source


def test_distinct_images_separate_cards(tmp_path):
    for i in range(3):
        _drawn_png(tmp_path / f"img{i}.png", seed=i * 13 + 1)
    insights = ImageIngestor(SpyGraph()).synthesis(str(tmp_path))
    assert len(insights) == 3
