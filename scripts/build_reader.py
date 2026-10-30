"""Build the homepage and optional search/discovery assets from reviewed data."""

import json
from pathlib import Path

from seo import HOME_DESCRIPTION, HOME_TITLE, archive_nav, home_fallback, metadata

from assets import write_asset

ROOT = Path(__file__).resolve().parents[1]


def build_reader(dist, sources):
    def read(name):
        return json.loads((ROOT / "data" / (name + ".json")).read_text())

    messages, conversations, emails, discovery, highlights = [
        read(name) for name in ("messages", "conversations", "emails", "discovery", "highlights")
    ]
    data = {
        "messages": messages,
        "conversations": conversations,
        "report": read("import-report"),
        "emails": emails,
        "source_manifest": [
            {k: v for k, v in s.items() if k not in ("sha256", "render_dpi")} for s in sources
        ],
        "highlights": highlights,
        **discovery,
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    src = ROOT / "src"
    css_path = write_asset(dist, "reader.css", (src / "reader.css").read_text())
    data_path = write_asset(dist, "transcript.json", payload)
    # Shared data is initialized first; reader.js binds the DOM after discovery
    # and analytics have been defined. No HTML is parsed to recover source code.
    runtime = "\n".join(
        (src / name).read_text()
        for name in ("reader-data.js", "analytics.js", "discovery.js", "reader.js")
    )
    runtime_path = write_asset(dist, "reader.js", runtime)
    loader = (
        (src / "loader.js")
        .read_text()
        .replace("TRANSCRIPT_URL", data_path)
        .replace("READER_URL", runtime_path)
    )
    loader_path = write_asset(dist, "reader-loader.js", loader)
    html = (src / "reader.html").read_text()
    replacements = {
        "<!-- SEO_HEAD -->": metadata(HOME_TITLE, HOME_DESCRIPTION, "/"),
        "<!-- READER_ASSETS -->": f'<link rel="stylesheet" href="{css_path}"><script src="{loader_path}" defer></script>',
        "<!-- ARCHIVE_NAV -->": archive_nav(),
        "<!-- HOME_CONTENT -->": home_fallback(
            messages, conversations, emails, discovery, highlights
        ),
    }
    for marker, content in replacements.items():
        if html.count(marker) != 1:
            raise ValueError(f"Expected one template marker: {marker}")
        html = html.replace(marker, content)
    (dist / "index.html").write_text(html)
    (dist / "reader.html").write_text(html)
