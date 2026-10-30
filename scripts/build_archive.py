"""Generate the crawlable archive from the same reviewed records as the reader."""

import json
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from html import escape as e
from pathlib import Path

from seo import ORIGIN, SEARCH_TITLES, archive_nav, email_path, metadata, text_path, topic_path

from assets import write_asset

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "src"


def date(value):
    return (
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        .strftime("%B %d, %Y")
        .replace(" 0", " ")
    )


def dates(start, end):
    return date(start) + (" – " + date(end) if start[:10] != end[:10] else "")


def excerpt(value, limit=165):
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1].rsplit(" ", 1)[0] + "…"


def build_archive(dist, sources):
    def load(name):
        return json.loads((ROOT / "data" / (name + ".json")).read_text())

    messages, conversations, emails, discovery = [
        load(n) for n in ("messages", "conversations", "emails", "discovery")
    ]
    threads = sorted(emails["threads"], key=lambda t: (t["date_start"], t["id"]))
    themes = {t["id"]: t for t in discovery["themes"]}
    source_map = {s["id"]: s for s in sources}
    (dist / "assets").mkdir(exist_ok=True)
    css_path = write_asset(dist, "archive.css", (SCRIPTS / "archive.css").read_text())
    js_path = write_asset(
        dist,
        "archive.js",
        (SCRIPTS / "analytics.js").read_text() + "\n" + (SCRIPTS / "archive.js").read_text(),
    )
    urls = ["/"]

    def page(path, title, description, body, crumbs, kind="WebPage", key=""):
        breadcrumb = (
            '<nav class="breadcrumbs" aria-label="Breadcrumb">'
            + " / ".join(
                f'<a href="{link}">{e(name)}</a>'
                if i < len(crumbs) - 1
                else f'<span aria-current="page">{e(name)}</span>'
                for i, (name, link) in enumerate(crumbs)
            )
            + "</nav>"
        )
        html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{metadata(title, description, path, kind, crumbs)}
<link rel="stylesheet" href="{css_path}"><script src="{js_path}" defer></script></head>
<body data-reading-key="{e(key)}"><a class="skip" href="#content">Skip to content</a>
<header class="site-bar"><div class="bar-inner"><a class="brand" href="/">theranotes</a><a class="search-link" href="/#search">Search the texts ↗</a></div></header>
<main id="content">{archive_nav()}{breadcrumb}{body}</main>
<footer class="site-footer">{archive_nav()}<p>An independent reading archive of public Theranos court exhibits. Titles and summaries are editorial; transcripts preserve the source text. This is a selection, not a complete message history.</p></footer></body></html>'''
        target = dist / path.lstrip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html)
        urls.append(path)

    def tags(ids):
        return (
            '<nav class="topics" aria-label="Related topics">'
            + "".join(f'<a href="{topic_path(t)}">{e(themes[t]["label"])}</a>' for t in ids)
            + "</nav>"
        )

    def cards(items, email=False, heading=3):
        result = []
        for item in items:
            path = email_path(item["id"]) if email else text_path(item["id"])
            start, end = (
                (item["date_start"], item["date_end"]) if email else (item["start"], item["end"])
            )
            noun = "email" if email else "text"
            count = f"{len(item['messages'])} {noun}" + ("s" if len(item["messages"]) != 1 else "")
            result.append(
                f'<li><p class="eyebrow">{dates(start, end)} · {count}</p>'
                f'<h{heading}><a href="{path}">{e(item["title"])}</a></h{heading}>'
                f"<p>{e(item['summary'] if email else item['description'])}</p></li>"
            )
        return '<ul class="collection">' + "".join(result) + "</ul>"

    def pdf_link(source_id, pages):
        source = source_map[source_id]
        return " · ".join(
            f'<a href="/{e(source["file"])}#page={p}">{e(source["label"])} · p. {p}</a>'
            for p in pages
        )

    def source_list(ids):
        return (
            '<ul class="source-list">'
            + "".join(
                f'<li><a href="/{e(source_map[i]["file"])}">{e(source_map[i]["label"])} — PDF</a> · '
                f'<a href="{e(source_map[i]["source_url"], quote=True)}">Court source</a>'
                f"<small>{source_map[i]['pages']} PDF pages. {e(source_map[i].get('public_copy_note', ''))}</small></li>"
                for i in ids
            )
            + "</ul>"
        )

    share = '<div class="share"><button class="copy-link" data-copy-link hidden>Copy page link</button><span data-copy-status role="status" aria-live="polite"></span></div>'

    for n, c in enumerate(conversations):
        path = text_path(c["id"])
        rows = []
        for i in c["messages"]:
            m = messages[i]
            ident = "record-" + m["record"]
            refs = " · ".join(
                pdf_link(s["exhibit"], [s["page"]]) + f" · {e(s['bates'])}" for s in m["sources"]
            )
            note = (
                f'<p class="reading-note">Reading note: {e(" ".join(m["notes"]))}</p>'
                if m["uncertain"]
                else ""
            )
            rows.append(
                f'<li class="message {"holmes" if m["sender"] == "Elizabeth Holmes" else "balwani"}" id="{e(ident)}">'
                f'<div class="message-head"><strong>{e(m["sender"])}</strong><time datetime="{e(m["datetime_iso"])}">{e(m["datetime_raw"])} · presumed UTC</time></div>'
                f'<p class="message-body">{e(m["text"] or "[No message text printed]")}</p>{note}'
                f"<details><summary>Source &amp; record details</summary><p>To: {e(m['recipient'] or '[Not printed]')}</p>"
                f"<p>{refs}</p><p>{e(m['record'])}</p>"
                + (f"<p>Attachments: {e(m['attachments'])}</p>" if m["attachments"] else "")
                + f'<a href="#{e(ident)}">Link to this message</a></details></li>'
            )
        neighbors = []
        for label, j in [("Previous exchange", n - 1), ("Next exchange", n + 1)]:
            if 0 <= j < len(conversations):
                other = conversations[j]
                neighbors.append(
                    f'<a href="{text_path(other["id"])}"><small>{label}</small>{e(other["title"])}</a>'
                )
        body = (
            f'<p class="eyebrow">Holmes–Balwani text messages · {dates(c["start"], c["end"])}</p>'
            f'<h1>{e(c["title"])}</h1><p class="lede">{e(c["description"])}</p>{tags(c["tags"])}'
            f'<p class="scope">{len(c["messages"])} {"message" if len(c["messages"]) == 1 else "messages"} from selected court exhibits. Gaps may remain. <a href="/about/">Sources &amp; reading notes</a>.</p>{share}'
            f'<ol class="message-list">{"".join(rows)}</ol><h2>Original court exhibits</h2>{source_list(c["sources"])}'
            f'<nav class="next" aria-label="Adjacent conversations">{"".join(neighbors)}</nav>'
        )
        page(
            path,
            SEARCH_TITLES.get(c["id"], f"{c['title']} | Theranotes"),
            excerpt(
                f"Elizabeth Holmes and Sunny Balwani texts, {dates(c['start'], c['end'])}. {c['description']}"
            ),
            body,
            [("Theranotes", "/"), ("Text messages", "/texts/"), (c["title"], path)],
            key="conversation:" + c["id"],
        )

    for t in threads:
        path = email_path(t["id"])
        rows = []
        for m in t["messages"]:
            figures = []
            for f in m.get("embedded_figures", []):
                from PIL import Image

                with Image.open(ROOT / f["local_file"]) as image:
                    width, height = image.size
                figures.append(
                    f'<figure><img src="/{e(f["local_file"])}" alt="{e(f["caption"], quote=True)}" width="{width}" height="{height}" loading="lazy"><figcaption>{e(f["caption"])}</figcaption></figure>'
                )
            envelope = [
                m["datetime_raw"]
                + (" · timezone not stated" if m["timezone_status"] == "not stated" else ""),
                "To: " + (", ".join(m.get("to", [])) or "[Not printed]"),
                "Subject: " + (m.get("subject") or t.get("subject") or "[Not printed]"),
            ]
            if m.get("cc"):
                envelope.append("Cc: " + ", ".join(m["cc"]))
            if m.get("attachments"):
                envelope.append("Attachments named in source: " + ", ".join(m["attachments"]))
            notes = [m["editorial_note"]] if m.get("editorial_note") else []
            if m.get("uncertain"):
                notes.append(
                    "Reading note: "
                    + (
                        " ".join(m.get("notes", []))
                        or "Consult the source for this uncertain reading."
                    )
                )
            rows.append(
                f'<li><article class="email" id="{e(m["id"])}"><h2>{e(m["sender"])}</h2><div class="envelope">'
                + "".join(f"<p>{e(line)}</p>" for line in envelope)
                + "</div>"
                + f'<div class="email-body">{e(m["text"])}</div>'
                + "".join(figures)
                + "".join(f'<p class="scope">{e(note)}</p>' for note in notes)
                + f"<details><summary>Original source pages</summary>{pdf_link(m['source_id'], m['source_pages'])}"
                f' · <a href="#{e(m["id"])}">Link to this email</a></details></article></li>'
            )
        body = (
            f'<p class="eyebrow">Theranos trial emails · {dates(t["date_start"], t["date_end"])}</p><h1>{e(t["title"])}</h1>'
            f'<p class="lede">{e(t["summary"])}</p><p class="muted">{e(" · ".join(t["participants"]))}</p>{tags(t["themes"])}'
            f'<p class="scope">{len(t["messages"])} {"email" if len(t["messages"]) == 1 else "emails"}, oldest first. This is the exchange visible in the cited exhibit; attachments are included only when expressly stated.</p>'
            + "".join(f'<p class="scope">{e(note)}</p>' for note in t.get("notes", []))
            + share
            + '<ol class="email-list">'
            + "".join(rows)
            + "</ol>"
            + f"<h2>Original court exhibits</h2>{source_list([s['id'] for s in t['sources']])}"
            + f"<details><summary>About this transcription</summary><p>{e(emails['scope_note'])}</p></details>"
            + "<h2>Related email exchanges</h2>"
            + cards(
                [x for x in threads if x["id"] != t["id"] and set(x["themes"]) & set(t["themes"])][
                    :3
                ],
                True,
            )
        )
        page(
            path,
            SEARCH_TITLES.get(t["id"], f"{t['title']} | Theranotes"),
            excerpt(t["summary"]),
            body,
            [("Theranotes", "/"), ("Trial emails", "/emails/"), (t["title"], path)],
            key="email:" + t["id"],
        )

    years = defaultdict(list)
    for c in conversations:
        years[c["start"][:4]].append(c)
    body = (
        "<h1>Elizabeth Holmes and Sunny Balwani text messages</h1>"
        f'<p class="lede">Browse {len(messages):,} text records in {len(conversations)} conversations from public Theranos court exhibits, '
        f"{date(conversations[0]['start'])} through {date(conversations[-1]['end'])}. Each exchange includes the transcript and links to the original evidence.</p>"
        '<nav class="year-nav" aria-label="Jump to year">'
        + "".join(f'<a href="#year-{y}">{y}</a>' for y in years)
        + "</nav>"
        + "".join(
            f'<section id="year-{y}"><h2>{y}</h2>{cards(items)}</section>'
            for y, items in years.items()
        )
    )
    page(
        "/texts/",
        "Elizabeth Holmes & Sunny Balwani Text Message Archive | Theranotes",
        f"Browse {len(messages):,} Elizabeth Holmes and Sunny Balwani text records by date, with full conversations, original Theranos court exhibits, and source citations.",
        body,
        [("Theranotes", "/"), ("Text messages", "/texts/")],
        "CollectionPage",
    )
    page(
        "/emails/",
        "Theranos Trial Emails & Original Exhibits | Theranotes",
        "Read selected Theranos trial emails about investors, demonstrations, lab concerns, Tyler Shultz, and the press. Full exchanges with original court exhibits.",
        f'<h1>Theranos trial emails</h1><p class="lede">{len(threads)} selected exchanges from public court exhibits: investor questions, demonstrations, lab concerns, and the press.</p>'
        f'<details class="scope"><summary>About this email selection</summary><p>{e(emails["scope_note"])}</p></details>{cards(threads, True, heading=2)}',
        [("Theranotes", "/"), ("Trial emails", "/emails/")],
        "CollectionPage",
    )
    topic_cards = []
    for ident, topic in themes.items():
        path = topic_path(ident)
        texts = [c for c in conversations if ident in c["tags"]]
        mail = [t for t in threads if ident in t["themes"]]
        body = (
            f'<p class="eyebrow">Theranos texts &amp; emails by topic</p><h1>{e(topic["label"])}</h1>'
            f'<p class="lede">{e(topic["description"])}</p><p class="scope">An editorial guide to {len(texts)} text conversations and {len(mail)} email exchanges. '
            "Each entry opens the full exchange included in its cited source.</p>"
            + ("<h2>Email exchanges</h2>" + cards(mail, True) if mail else "")
            + "<h2>Text conversations</h2>"
            + cards(texts)
        )
        page(
            path,
            f"{topic['label']}: Theranos Texts & Emails | Theranotes",
            excerpt(
                f"{topic['description']} Read the relevant Elizabeth Holmes and Sunny Balwani texts and Theranos trial emails, with original sources."
            ),
            body,
            [("Theranotes", "/"), ("Topics", "/topics/"), (topic["label"], path)],
            "CollectionPage",
        )
        topic_cards.append(
            f'<li><h2><a href="{path}">{e(topic["label"])}</a></h2><p>{e(topic["description"])}</p><p>{len(texts)} conversations · {len(mail)} email exchanges</p></li>'
        )
    page(
        "/topics/",
        "Explore Theranos Texts & Emails by Topic | Theranotes",
        "Explore Theranos court exhibits by topic: warning signs, love and power, personal messages, the press, regulators, lab operations, and money.",
        '<h1>Explore the archive by topic</h1><p class="lede">Follow a subject across the texts and emails. These editorial groupings are a way into the evidence.</p><ul class="collection">'
        + "".join(topic_cards)
        + "</ul>",
        [("Theranotes", "/"), ("Topics", "/topics/")],
        "CollectionPage",
    )
    page(
        "/about/",
        "About Theranotes: Sources & Transcription Method",
        "Learn how Theranotes transcribes public Theranos court exhibits, preserves source citations, marks uncertain readings, and explains gaps in the record.",
        '<h1>About Theranotes &amp; its sources</h1><p class="lede">An independent reading archive of Elizabeth Holmes and Sunny Balwani texts and selected Theranos emails, drawn from public court exhibits.</p>'
        "<h2>What is included</h2>"
        f"<p>{len(messages):,} distinct text records across {len(conversations)} conversations, plus {len(threads)} selected email exchanges. "
        "The texts combine Trial Exhibits 5387A–I and additional public docket exhibits from <i>United States v. Holmes</i> and <i>United States v. Balwani</i>.</p>"
        "<p>These sources contain excerpts of iPhone and Skype records, not a complete message history. A gap is not evidence that no messages were exchanged. The emails are a curated selection, not a complete mailbox.</p>"
        "<h2>How to read the transcripts</h2><p>Spelling and typos are retained. Redactions and blank-message markers are identified in the text. Uncertain readings carry notes alongside the affected message. Check the cited PDF for the original.</p>"
        "<p>Text timestamps are copied as printed and presumed UTC; no local-time conversion is applied. Email timestamps retain the printed timezone where stated, and no timezone is inferred where it is missing.</p>"
        "<p>A new text conversation begins after a gap of three hours or more. Titles, summaries, and topic tags are editorial navigation aids, separate from the source text. Tags apply to an exchange as a whole.</p>"
        "<p>Repeated record IDs across exhibits appear once, with every source retained. Different IDs with identical text remain separate. Where scans overlap, the clearer checked transcription is used.</p>"
        f"<h2>Email selection and transcription</h2><p>{e(emails['scope_note'])}</p>"
        "<h2>Citing an exchange</h2><p>Use the conversation or email page URL, its date, and the source exhibit and page number. Each message also has a permanent link under its source details. Page titles may be revised; the identifiers in the URLs stay stable.</p>"
        "<h2>Original evidence</h2>"
        + source_list(source_map)
        + '<h2>Download the reviewed data</h2><ul><li><a href="/data/messages.json">Text transcript JSON</a></li><li><a href="/data/emails.json">Email transcript JSON</a></li><li><a href="/data/page-review.csv">Page-by-page row audit</a></li><li><a href="/exhibits/manifest.json">Text source URLs and checksums</a></li></ul>',
        [("Theranotes", "/"), ("About & sources", "/about/")],
        "AboutPage",
    )

    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    sitemap = ET.Element(f"{{{namespace}}}urlset")
    for path in urls:
        url = ET.SubElement(sitemap, f"{{{namespace}}}url")
        ET.SubElement(url, f"{{{namespace}}}loc").text = ORIGIN + path
    # No invented lastmod dates: a rebuild does not mean the underlying content changed.
    ET.indent(sitemap)
    ET.ElementTree(sitemap).write(dist / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (dist / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n")
    redirects = ["/reader / 301", "/reader.html / 301"]
    for old, new in discovery.get("conversation_aliases", {}).items():
        redirects.extend(
            [f"/texts/{old} {text_path(new)} 301", f"{text_path(old)} {text_path(new)} 301"]
        )
    (dist / "_redirects").write_text("\n".join(redirects) + "\n")
    for asset in ("favicon.svg", "social-card.png"):
        shutil.copyfile(ROOT / "assets" / asset, dist / "assets" / asset)
    print(
        f"Generated {len(urls)} canonical HTML pages and sitemap entries; optional reader assets are cached separately."
    )
