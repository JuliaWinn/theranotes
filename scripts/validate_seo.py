"""Check the actual deploy artifact: metadata, crawl graph, assets and transcript parity."""

import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from seo import HOME_TITLE, ORIGIN, email_path, text_path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.links, self.assets, self.meta, self.canonicals, self.ids = [], [], {}, [], set()
        self.title, self.schemas, self.bodies = "", [], []
        self._title, self._schema, self._body_depth = False, None, 0
        self._body = ""
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in ("img", "script") and a.get("src"):
            self.assets.append(a["src"])
        if tag == "link":
            if a.get("rel") == "canonical":
                self.canonicals.append(a["href"])
            elif a.get("href"):
                self.assets.append(a["href"])
        if tag == "meta":
            self.meta[a.get("name", a.get("property"))] = a.get("content")
        if tag == "title":
            self._title = True
        if tag == "script" and a.get("type") == "application/ld+json":
            self._schema = ""
        if self._body_depth:
            self._body_depth += 1
        elif a.get("class") in ("message-body", "email-body"):
            self._body_depth = 1
            self._body = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False
        if tag == "script" and self._schema is not None:
            self.schemas.append(json.loads(self._schema))
            self._schema = None
        if self._body_depth:
            self._body_depth -= 1
            if not self._body_depth:
                self.bodies.append(self._body)

    def handle_data(self, data):
        if self._title:
            self.title += data
        if self._schema is not None:
            self._schema += data
        if self._body_depth:
            self._body += data


def run():
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [n.text for n in ET.parse(DIST / "sitemap.xml").findall("s:url/s:loc", ns)]
    assert len(urls) == len(set(urls)), "Duplicate sitemap entries"
    assert all(
        url.startswith(ORIGIN + "/") and not urlsplit(url).fragment and not urlsplit(url).query
        for url in urls
    )
    paths = [urlsplit(u).path for u in urls]
    pages = {p: Page((DIST / p.lstrip("/") / "index.html").read_text()) for p in paths}
    titles = set()
    descriptions = set()
    edges = {}
    for path, p in pages.items():
        assert p.canonicals == [ORIGIN + path], (path, "canonical")
        assert p.title and p.title not in titles, (path, "duplicate/missing title")
        titles.add(p.title)
        description = p.meta.get("description")
        assert description and description not in descriptions, (
            path,
            "duplicate/missing description",
        )
        descriptions.add(description)
        assert p.meta["og:title"] == p.title and p.meta["og:description"] == description
        assert p.meta["og:url"] == ORIGIN + path
        assert p.meta["og:image"] == ORIGIN + "/assets/social-card.png"
        assert "noindex" not in p.meta.get("robots", "")
        assert p.meta["twitter:card"] == "summary_large_image"
        assert p.schemas and p.schemas[0]["@context"] == "https://schema.org"
        graph = p.schemas[0]["@graph"]
        assert graph[0]["url"] == ORIGIN + path
        if path != "/":
            crumbs = next(x for x in graph if x["@type"] == "BreadcrumbList")["itemListElement"]
            assert crumbs[-1]["item"] == ORIGIN + path
            assert [x["position"] for x in crumbs] == list(range(1, len(crumbs) + 1))
        edges[path] = []
        for link in p.links + p.assets:
            parsed = urlsplit(urljoin(ORIGIN + path, link))
            if parsed.netloc and parsed.netloc != urlsplit(ORIGIN).netloc:
                continue
            target = unquote(parsed.path) or path
            assert target.startswith("/"), (path, "relative link", link)
            if target in pages:
                edges[path].append(target)
                if parsed.fragment and target != "/":
                    assert unquote(parsed.fragment) in pages[target].ids, (
                        path,
                        "missing anchor",
                        link,
                    )
            else:
                assert (DIST / target.lstrip("/")).is_file(), (path, "missing asset", link)
        html = (DIST / path.lstrip("/") / "index.html").read_text()
        assert "<!-- SEO_HEAD -->" not in html and "<!-- HOME_CONTENT -->" not in html
        if path != "/":
            assert len(re.findall(r"<h1[\s>]", html)) == 1, path
    visited, pending = set(), ["/"]
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        pending.extend(edges[path])
    assert visited == set(paths), ("Orphaned pages", set(paths) - visited)
    assert pages["/"].title == HOME_TITLE
    assert len((DIST / "index.html").read_bytes()) < 40000, (
        "Homepage should not inline the entire archive"
    )
    messages = json.loads((ROOT / "data/messages.json").read_text())
    conversations = json.loads((ROOT / "data/conversations.json").read_text())
    threads = json.loads((ROOT / "data/emails.json").read_text())["threads"]
    for c in conversations:
        p = pages[text_path(c["id"])]
        assert p.bodies == [
            messages[i]["text"] or "[No message text printed]" for i in c["messages"]
        ], ("Text changed", c["id"])
        assert all("record-" + messages[i]["record"] in p.ids for i in c["messages"])
        assert all(
            any(f"#page={s['page']}" in link for link in p.links)
            for i in c["messages"]
            for s in messages[i]["sources"]
        )
    for t in threads:
        assert pages[email_path(t["id"])].bodies == [m["text"] for m in t["messages"]], (
            "Email changed",
            t["id"],
        )
    payloads = list((DIST / "assets").glob("transcript.*.json"))
    assert len(payloads) == 1
    embedded = json.loads(payloads[0].read_text())
    for key, name in [
        ("messages", "messages"),
        ("conversations", "conversations"),
        ("emails", "emails"),
        ("highlights", "highlights"),
        ("report", "import-report"),
    ]:
        assert embedded[key] == json.loads((ROOT / "data" / (name + ".json")).read_text()), (
            "Reader data differs",
            key,
        )
    for key, value in json.loads((ROOT / "data/discovery.json").read_text()).items():
        assert embedded[key] == value
    expected = 5 + len(conversations) + len(threads) + 7
    assert len(pages) == expected
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in (DIST / "robots.txt").read_text()
    assert "Disallow: /" not in (DIST / "robots.txt").read_text()
    assert "noindex" in Page((DIST / "404.html").read_text()).meta["robots"]
    # Internal IDs/paths stay stable even when editorial titles are revised.
    aliases = json.loads((ROOT / "data/discovery.json").read_text())["conversation_aliases"]
    redirects = (DIST / "_redirects").read_text()
    for old, new in aliases.items():
        assert f"{text_path(old)} {text_path(new)} 301" in redirects
    for script in (DIST / "assets").glob("*.js"):
        import subprocess

        subprocess.run(["node", "--check", str(script)], check=True, capture_output=True)
    print(
        f"PASS: {len(pages)} crawlable canonical pages; unique metadata; structured data; no orphan pages or broken local links/assets/anchors."
    )
    print(
        f"PASS: all {len(messages):,} text records and {sum(len(t['messages']) for t in threads)} email bodies match reviewed data exactly; message anchors and legacy aliases resolve; JavaScript parses."
    )


if __name__ == "__main__":
    run()
