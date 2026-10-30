"""Public derivatives must survive a fresh checkout and a stale render cache."""

import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_source_pages import render_source
from sources import load_sources


class PublicSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "exhibits/public").mkdir(parents=True)
        self.public = self.root / "exhibits/public/TEST.pdf"
        Image.new("RGB", (24, 24), "red").save(self.root / "exhibits/original.pdf")
        self.write_public("blue")

    def write_public(self, color):
        Image.new("RGB", (24, 24), color).save(self.public)
        self.source = {
            "id": "TEST",
            "file": "exhibits/public/TEST.pdf",
            "pages": 1,
            "render_dpi": 200,
            "sha256": sha256(self.public.read_bytes()).hexdigest(),
        }
        (self.root / "exhibits/reader-sources.json").write_text(
            json.dumps({"sources": [self.source]})
        )

    def rendered_pixel(self):
        with Image.open(self.root / "exhibits/pages/TEST-001.webp") as image:
            return image.getpixel((10, 10))

    def test_cold_build_uses_public_pdf_even_with_poisoned_research_caches(self):
        for directory in ("tmp/pages", "tmp/public-pages"):
            path = self.root / directory
            path.mkdir(parents=True)
            Image.new("RGB", (24, 24), "red").save(path / "TEST-001.png")
        render_source(load_sources(self.root)[0], self.root)
        red, _, blue = self.rendered_pixel()
        self.assertGreater(blue, 200)
        self.assertLess(red, 30)

    def test_missing_public_copy_never_falls_back_to_original(self):
        self.public.unlink()
        with self.assertRaisesRegex(ValueError, "Missing public PDF"):
            load_sources(self.root)

    def test_changed_pdf_requires_explicit_checksum_update(self):
        self.public.write_bytes(b"changed source")
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            load_sources(self.root)

    def test_cache_is_invalidated_when_reviewed_pdf_changes(self):
        render_source(load_sources(self.root)[0], self.root)
        self.write_public("lime")
        render_source(load_sources(self.root)[0], self.root)
        red, green, blue = self.rendered_pixel()
        self.assertGreater(green, 200)
        self.assertLess(max(red, blue), 30)


if __name__ == "__main__":
    unittest.main()
