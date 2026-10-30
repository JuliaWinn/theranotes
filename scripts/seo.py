"""Shared URLs and metadata for the reader and the static archive.

Identifiers, rather than editorial titles, keep cited URLs stable when notes change.
"""

import json
from datetime import datetime
from html import escape

ORIGIN = "https://theranotes.juliawinn.com"
HOME_TITLE = "Elizabeth Holmes & Sunny Balwani Text Messages | Theranotes"
HOME_DESCRIPTION = (
    "Read Elizabeth Holmes and Sunny Balwani text messages and selected "
    "Theranos emails from public court exhibits, with transcripts and original sources."
)
TOPIC_SLUGS = {
    "alarm": "warning-signs",
    "power": "love-and-power",
    "personal": "personal",
    "press": "press",
    "regulators": "regulators",
    "ops": "inside-the-lab",
    "money": "money",
}
# Search-facing titles for a few established entry points. Visible editorial titles
# and source transcripts stay unchanged; these IDs are stable across rebuilds.
SEARCH_TITLES = {
    "c063": "Sunny Balwani “I Have Molded You” Texts | Theranotes",
    "c065": "Elizabeth Holmes “Breeze in Desert” Texts | Theranotes",
    "c078": "Sunny Balwani “Responsible for Everything” Texts | Theranotes",
    "email-1675": "Tyler Shultz Emails to Elizabeth Holmes & Resignation | Theranotes",
    "email-0871": "Theranos Minilab Demo Emails | Theranotes",
    "email-5704": "Elizabeth Holmes Emails Rupert Murdoch About the WSJ | Theranotes",
}


def text_path(identifier):
    return f"/texts/{identifier}/"


def email_path(identifier):
    return f"/emails/{identifier}/"


def topic_path(identifier):
    return f"/topics/{TOPIC_SLUGS[identifier]}/"


def json_ld(value):
    return (
        '<script type="application/ld+json">'
        + json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
        + "</script>"
    )


def metadata(title, description, path, kind="WebPage", breadcrumbs=None):
    url = ORIGIN + path
    schema = [
        {
            "@type": kind,
            "@id": url + "#page",
            "url": url,
            "name": title,
            "description": description,
            "inLanguage": "en",
            "isPartOf": {"@id": ORIGIN + "/#website"},
            "about": [
                {"@type": "Person", "name": "Elizabeth Holmes"},
                {"@type": "Person", "name": "Ramesh “Sunny” Balwani"},
                {"@type": "Organization", "name": "Theranos"},
            ],
        }
    ]
    if path == "/":
        schema.append(
            {
                "@type": "WebSite",
                "@id": ORIGIN + "/#website",
                "name": "Theranotes",
                "alternateName": "Theranotes — Theranos texts and emails",
                "url": ORIGIN + "/",
                "description": HOME_DESCRIPTION,
                "inLanguage": "en",
            }
        )
    if breadcrumbs:
        schema.append(
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": n, "name": name, "item": ORIGIN + link}
                    for n, (name, link) in enumerate(breadcrumbs, 1)
                ],
            }
        )
    e = escape
    return f'''<title>{e(title)}</title>
<meta name="description" content="{e(description, quote=True)}">
<link rel="canonical" href="{e(url)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:site_name" content="Theranotes">
<meta property="og:type" content="website">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{e(title, quote=True)}">
<meta property="og:description" content="{e(description, quote=True)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{ORIGIN}/assets/social-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Theranotes — Inside Theranos, in their own words. Text messages, emails, and original court exhibits.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title, quote=True)}">
<meta name="twitter:description" content="{e(description, quote=True)}">
<meta name="twitter:image" content="{ORIGIN}/assets/social-card.png">
<meta name="twitter:image:alt" content="Theranotes — Inside Theranos, in their own words.">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{json_ld({"@context": "https://schema.org", "@graph": schema})}'''


def archive_nav():
    return (
        '<nav class="archive-nav" aria-label="Archive">'
        '<a href="/texts/">All texts</a><a href="/emails/">Emails</a>'
        '<a href="/topics/">Topics</a><a href="/about/">About &amp; sources</a></nav>'
    )


def home_fallback(messages, conversations, emails, discovery, highlights):
    """Useful initial HTML for everyone, enhanced by the interactive discovery feed."""
    by_incident = {i["id"]: i for i in discovery["incidents"]}
    by_email = {t["id"]: t for t in emails["threads"]}
    by_conversation = {c["id"]: c for c in conversations}
    by_record = {m["record"]: i for i, m in enumerate(messages)}
    chips = (
        '<nav class="home-filters" aria-label="Highlight topics"><a class="selected" href="/topics/">Top moments</a>'
        + "".join(
            f'<a href="{topic_path(t["id"])}">{escape(t["label"])}</a>' for t in discovery["themes"]
        )
        + "</nav>"
    )
    intro = (
        '<div class="home-intro"><h1 class="framing">The real texts between '
        "<b>Elizabeth Holmes</b> and <b>Sunny Balwani</b>, from the evidence at their fraud trials.</h1>"
        f'<a class="search-pill" href="/texts/"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><span>Browse {len(messages):,} texts</span><small>By date &amp; topic</small></a>{chips}</div>'
    )
    cards = []
    for n, item in enumerate(highlights):
        email = item["type"] == "email"
        source = by_email[item["id"]] if email else by_incident[item["id"]]
        path = email_path(source["id"]) if email else text_path(source["conversation"])
        title = item.get("title", source["title"])
        setup = item.get("setup", source.get("summary", source.get("description", "")))
        if n == 0 and not email:
            c = by_conversation[source["conversation"]]
            at = c["messages"].index(by_record[source["record"]])
            indices, size = [], 0
            for i in c["messages"][at : at + 1 + item.get("after", 1)]:
                if indices and size + len(messages[i]["text"]) > 520:
                    break
                indices.append(i)
                size += len(messages[i]["text"])
            preview = []
            previous = None
            for i in indices:
                m = messages[i]
                first = previous != m["sender"]
                name = f'<div class="name">{escape(m["sender"])}</div>' if first else ""
                preview.append(
                    f'<div class="row {"e" if m["sender"] == "Elizabeth Holmes" else "s"}{" first" if first else ""}">{name}<div class="bubble">{escape(m["text"])}</div></div>'
                )
                previous = m["sender"]
            when = (
                datetime.fromisoformat(messages[indices[0]]["datetime_iso"].replace("Z", "+00:00"))
                .strftime("%b %d, %Y")
                .replace(" 0", " ")
            )
            cards.append(
                f'<article class="highlight-card featured"><div class="highlight-eyebrow"><span>Start here</span><time>{when}</time></div>'
                f'<h2>{escape(title)}</h2><p class="highlight-setup">{escape(setup)}</p>'
                '<div class="peek-transcript" aria-label="Conversation excerpt">'
                + "".join(preview)
                + "</div>"
                f'<a class="conversation-action" href="{path}#record-{escape(source["record"])}">Read the full exchange <span aria-hidden="true">→</span></a>'
                f'<p class="peek-count">{len(c["messages"])} messages in the available exchange</p></article>'
            )
            continue
        cards.append(
            f'<article class="highlight-card"><h2><a href="{path}">{escape(title)}</a></h2>'
            f"<p>{escape(setup)}</p><blockquote>{escape(source['quote'])}</blockquote>"
            f'<a class="jump-link" href="{path}">Read the full exchange →</a></article>'
        )
    return intro + "".join(cards)
