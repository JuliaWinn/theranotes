"""Render source previews from checksum-verified public PDFs."""

import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from PIL import __version__ as pillow_version
from sources import ROOT, load_sources


def render_source(source, root=ROOT):
    """A cache entry belongs to one public PDF and one rendering configuration."""
    identifier = source["id"]
    names = [f"{identifier}-{page:03}.webp" for page in range(1, source["pages"] + 1)]
    output = root / "exhibits/pages"
    output.mkdir(parents=True, exist_ok=True)
    cache = root / ".cache/source-pages"
    cache.mkdir(parents=True, exist_ok=True)
    stamp = cache / f"{identifier}.json"
    version = subprocess.run(
        ["pdftoppm", "-v"], capture_output=True, check=True, text=True
    ).stderr.splitlines()[0]
    settings = {
        "sha256": source["sha256"],
        "dpi": source["render_dpi"],
        "pages": source["pages"],
        "pillow": pillow_version,
        "poppler": version,
        "webp_quality": 90,
        "webp_method": 4,
    }
    if stamp.exists() and json.loads(stamp.read_text()) == settings:
        if all((output / name).is_file() for name in names):
            return
    # Only renders of the verified public copy enter this directory. The old
    # tmp/pages and tmp/public-pages research overrides are never consulted.
    with tempfile.TemporaryDirectory(prefix=identifier + "-", dir=cache) as work:
        prefix = Path(work) / identifier
        subprocess.run(
            [
                "pdftoppm",
                "-r",
                str(source["render_dpi"]),
                "-png",
                str(root / source["file"]),
                str(prefix),
            ],
            check=True,
            capture_output=True,
        )
        pages = sorted(Path(work).glob("*.png"))
        numbers = {int(page.stem.rsplit("-", 1)[1]) for page in pages}
        if numbers != set(range(1, source["pages"] + 1)):
            raise ValueError(f"Unexpected rendered page count for {identifier}")
        for page in pages:
            number = int(page.stem.rsplit("-", 1)[1])
            target = output / f"{identifier}-{number:03}.webp"
            with Image.open(page) as image:
                image.convert("RGB").save(target, "WEBP", quality=90, method=4)
    stamp.write_text(json.dumps(settings, sort_keys=True) + "\n")


def run():
    sources = load_sources()
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(render_source, sources))
    print(f"Prepared {sum(s['pages'] for s in sources)} pages from verified public PDFs")


if __name__ == "__main__":
    run()
