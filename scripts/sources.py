"""Load the reviewed public PDF selection; never fall back to research originals."""

import json
import re
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_sources(root=ROOT):
    sources = json.loads((root / "exhibits/reader-sources.json").read_text())["sources"]
    seen = set()
    for source in sources:
        identifier = source["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier) or identifier in seen:
            raise ValueError(f"Invalid or duplicate source ID: {identifier}")
        seen.add(identifier)
        path = (root / source["file"]).resolve()
        if not path.is_relative_to((root / "exhibits").resolve()) or not path.is_file():
            raise ValueError(f"Missing public PDF: {source['file']}")
        if sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"Public PDF checksum changed: {source['file']}")
        if source["pages"] < 1 or source["render_dpi"] not in (200, 300):
            raise ValueError(f"Invalid rendering settings for {identifier}")
    return sources
