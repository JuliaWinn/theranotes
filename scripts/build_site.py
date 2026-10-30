"""Package the reader and its public sources for Cloudflare Pages."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from build_archive import build_archive
from build_reader import build_reader
from sources import load_sources

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def run():
    for script in ("validate_import.py", "build_source_pages.py"):
        subprocess.run([sys.executable, str(ROOT / "scripts" / script)], check=True)
    # Rebuild this generated directory so stale files cannot enter a deployment.
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    emails = json.loads((ROOT / "data/emails.json").read_text())
    sources = load_sources()
    files = {"exhibits/manifest.json": "exhibits/manifest.json"}
    for source in sources:
        files[source["file"]] = source["file"]
        for page in range(1, source["pages"] + 1):
            asset = f"{source['image_prefix']}{page:03}.webp"
            files[asset] = asset
    for thread in emails.get("threads", []):
        for message in thread["messages"]:
            for figure in message.get("embedded_figures", []):
                asset = figure["local_file"]
                original = (ROOT / asset).resolve()
                if (
                    not original.is_relative_to(ROOT / "data/email-assets")
                    or not original.is_file()
                ):
                    raise ValueError(f"Unexpected email figure path: {asset}")
                files[asset] = asset
    files.update(
        {
            f"data/{name}": f"data/{name}"
            for name in (
                "messages.json",
                "conversations.json",
                "discovery.json",
                "import-report.json",
                "page-review.csv",
                "emails.json",
            )
        }
    )
    for relative, original in files.items():
        source, destination = ROOT / original, DIST / relative
        if source.stat().st_size > 25 * 1024 * 1024:
            raise ValueError(f"Asset exceeds Cloudflare file limit: {relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    build_reader(DIST, sources)
    build_archive(DIST, sources)
    (DIST / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "/exhibits/*.pdf\n  Cache-Control: public, max-age=86400\n"
        "/assets/*\n  Cache-Control: public, max-age=86400\n"
        "/data/*\n  X-Robots-Tag: noindex\n"
        "https://:project.pages.dev/*\n  X-Robots-Tag: noindex\n"
        "https://:version.:project.pages.dev/*\n  X-Robots-Tag: noindex\n"
    )
    (DIST / "404.html").write_text("""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page not found | Theranotes</title><meta name="robots" content="noindex">
<body style="font:18px/1.5 system-ui;max-width:36rem;margin:12vh auto;padding:24px">
<h1>That page isn't in the archive.</h1><p><a href="/">Return to Theranotes →</a></p><p><a href="/texts/">Browse text messages</a> · <a href="/emails/">Read trial emails</a></p></body></html>
""")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_seo.py")], check=True)
    assets = [p for p in DIST.rglob("*") if p.is_file()]
    print(
        f"Packaged {len(assets)} files ({sum(p.stat().st_size for p in assets) / 1024 / 1024:.1f} MiB) in {DIST}"
    )


if __name__ == "__main__":
    run()
