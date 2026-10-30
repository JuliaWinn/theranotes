"""Read-only checks of the deployed SEO artifact on the production domain."""

import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.parser import Parser
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from seo import ORIGIN
from validate_seo import Page

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def response(path, method="GET"):
    # Cloudflare rejects the default Python HTTP client (1010). Use the ordinary
    # system curl client, with TLS verification and all edge protections unchanged.
    with tempfile.NamedTemporaryFile() as header_file:
        command = [
            "curl",
            "--silent",
            "--show-error",
            "--max-time",
            "30",
            "--dump-header",
            header_file.name,
        ]
        if method == "HEAD":
            command.append("--head")
        command.append(ORIGIN + path)
        body = subprocess.run(command, check=True, capture_output=True).stdout
        blocks = Path(header_file.name).read_text().strip().split("\n\n")
    lines = blocks[-1].split("\n")
    status = int(lines[0].split()[1])
    headers = Parser().parsestr("\n".join(lines[1:]))
    return status, body, headers


def fetch(path, method="GET"):
    status, body, headers = response(path, method)
    if status >= 400:
        raise HTTPError(ORIGIN + path, status, "HTTP check failed", headers, BytesIO(body))
    assert status == 200, (path, status)
    return body, headers


def run():
    sitemap, headers = fetch("/sitemap.xml")
    assert "noindex" not in headers.get("X-Robots-Tag", "")
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text for node in ET.fromstring(sitemap).findall("s:url/s:loc", namespace)]
    expected = [
        node.text for node in ET.parse(DIST / "sitemap.xml").findall("s:url/s:loc", namespace)
    ]
    assert urls == expected

    def verify_page(url):
        assert url.startswith(ORIGIN + "/")
        path = urlsplit(url).path
        body, headers = fetch(path)
        live = Page(body.decode())
        local = Page((DIST / path.lstrip("/") / "index.html").read_text())
        assert live.canonicals == [url], (path, "canonical")
        assert "noindex" not in headers.get("X-Robots-Tag", "") + live.meta.get("robots", ""), path
        assert live.title == local.title and live.meta == local.meta, (path, "metadata")
        assert live.schemas == local.schemas and live.bodies == local.bodies, (path, "content")
        return path

    with ThreadPoolExecutor(max_workers=6) as pool:
        checked = list(pool.map(verify_page, urls))

    robots, _ = fetch("/robots.txt")
    robots = robots.decode()
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in robots
    assert "Disallow: /\n" not in robots
    try:
        fetch("/this-page-does-not-exist-seo-verification")
        raise AssertionError("Missing page did not return 404")
    except HTTPError as error:
        assert error.code == 404

    for path, target in [
        ("/reader.html", "/"),
        ("/reader", "/"),
        ("/texts/c053/", "/texts/c052/"),
        ("/texts/c001", "/texts/c001/"),
    ]:
        status, _, headers = response(path)
        assert status in (301, 308), (path, status)
        assert headers["Location"] in (target, ORIGIN + target), (path, headers["Location"])

    assets = [p for p in (DIST / "assets").iterdir() if p.is_file()]
    for asset in assets:
        remote, _ = fetch("/assets/" + asset.name)
        assert sha256(remote).digest() == sha256(asset.read_bytes()).digest(), (
            "Asset mismatch",
            asset.name,
        )
    archive_js = next(p for p in assets if p.name.startswith("archive.") and p.suffix == ".js")
    reader_js = next(p for p in assets if p.name.startswith("reader.") and p.suffix == ".js")
    for asset in (archive_js, reader_js):
        source = asset.read_text()
        assert "https://theranotes.goatcounter.com/count" in source
        assert "location.hostname !== 'theranotes.juliawinn.com'" in source
    assert "recordReaderView(location.pathname, document.title)" in archive_js.read_text()
    for path in [
        "/exhibits/5387I.pdf",
        "/exhibits/pages/5387I-001.webp",
        "/exhibits/emails/EMAIL-1675.pdf",
        "/data/email-assets/EMAIL-1675-plots-1-2.webp",
    ]:
        fetch(path, method="HEAD")
    result = {
        "verified_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
        "origin": ORIGIN,
        "canonical_pages_checked": len(checked),
        "asset_checksums_checked": len(assets),
        "results": [
            "All page metadata and transcript bodies match the approved local build",
            "Sitemap and robots reference verified",
            "True 404 and permanent redirects verified",
            "Original source PDF and image URLs return success",
            "GoatCounter integration retained on homepage and archive pages",
        ],
        "search_engine_submissions": "not performed",
    }
    (ROOT / "docs/seo-live-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
