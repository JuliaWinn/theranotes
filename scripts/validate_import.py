"""Regression checks for source coverage and the published reader dataset."""

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from sources import load_sources

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / "data" / name).read_text())


def run():
    m = read("messages.json")
    rows = [source for message in m for source in message["sources"]]
    c = read("conversations.json")
    a = read("page-review.json")
    public_sources = {source["id"]: source for source in load_sources()}
    report = read("import-report.json")
    manifest = json.loads((ROOT / "exhibits/manifest.json").read_text())
    source_files = {s["exhibit"]: s for s in manifest["files"]}
    assert len(m) == len({x["record"] for x in m}) == report["distinct_records"]
    assert len({r["source_id"] for r in rows}) == len(rows), "Repeated source row"
    page_counts = Counter((r["exhibit"], r["page"]) for r in rows)
    assert all(page_counts[(page["exhibit"], page["page"])] == page["extracted_rows"] for page in a)
    with (ROOT / "data/page-review.csv").open() as stream:
        csv_audit = list(csv.DictReader(stream))
    assert len(csv_audit) == len(a)
    for raw, page in zip(csv_audit, a):
        assert raw["exhibit"] == page["exhibit"]
        assert all(int(raw[key]) == page[key] for key in ("page", "visual_rows", "extracted_rows"))
    assert sum(len(x["sources"]) for x in m) == len(rows) == report["source_rows"]
    assert sorted(i for x in c for i in x["messages"]) == list(range(len(m)))
    assert len(a) == sum(s["pages"] for s in manifest["files"]) == report["pages_reviewed"]
    assert all(x["reviewed"] and x["visual_rows"] == x["extracted_rows"] for x in a)
    assert {(x["exhibit"], x["page"]) for x in a} == {
        (s["exhibit"], p) for s in manifest["files"] for p in range(1, s["pages"] + 1)
    }
    assert all(
        re.fullmatch(
            r"(?:Holmes_(?:MacBook(?:Air|Pro)_Skype|iPhone_iMessage-MMS-SMS)_\d{6}|DOJ_THER-\d+_\d{3})",
            x["record"],
        )
        for x in m
    )
    assert m == sorted(m, key=lambda x: (x["datetime_iso"], x["record"]))
    assert sum("5387B" in x["exhibits"] for x in m) == 293
    for group in c:
        assert group["title"] and group["description"] and isinstance(group["tags"], list)
        assert group["title"] != "Newly recovered exchange", group["id"]
        for i, j in zip(group["messages"], group["messages"][1:]):
            assert (
                datetime.fromisoformat(m[j]["datetime_iso"])
                - datetime.fromisoformat(m[i]["datetime_iso"])
            ).total_seconds() < 10800
    for left, right in zip(c, c[1:]):
        assert (
            datetime.fromisoformat(right["start"]) - datetime.fromisoformat(left["end"])
        ).total_seconds() >= 10800
    discovery = read("discovery.json")
    themes = {t["id"] for t in discovery["themes"]}
    assert len(themes) == len(discovery["themes"]) == 7
    assert all(set(group["tags"]) <= themes for group in c)
    incidents = discovery["incidents"]
    assert len({i["id"] for i in incidents}) == len(incidents)
    by_record = {msg["record"]: (n, msg) for n, msg in enumerate(m)}
    by_conversation = {group["id"]: group for group in c}
    for incident in incidents:
        assert re.fullmatch("[a-z0-9-]+", incident["id"])
        index, msg = by_record[incident["record"]]
        assert incident["quote"] and incident["quote"] in msg["text"]
        assert index in by_conversation[incident["conversation"]]["messages"]
        ids = [incident["conversation"], *incident["related"]]
        assert len(ids) == len(set(ids)) and all(id in by_conversation for id in ids)
        assert incident["title"] and incident["description"] and set(incident["tags"]) <= themes
        assert incident.get("heat") in (1, 2, 3), incident["id"]
    assert all(any(t in i["tags"] for i in incidents) for t in themes)
    highlights = read("highlights.json")
    assert len({(h["type"], h["id"]) for h in highlights}) == len(highlights)
    incident_ids = {i["id"] for i in incidents}
    email_ids = {e["id"] for e in read("emails.json")["threads"]}
    for highlight in highlights:
        assert highlight["type"] in {"incident", "email"}
        assert highlight["id"] in (incident_ids if highlight["type"] == "incident" else email_ids)
        assert isinstance(highlight.get("after", 1), int) and 0 <= highlight.get("after", 1) <= 2
    print(
        f"PASS: {len(highlights)} featured exchanges resolve to reviewed message or email sources; preview spans stay contiguous."
    )
    for msg in m:
        assert msg["sender"] and msg["recipient"] and (not msg["uncertain"] or msg["notes"])
        for source in msg["sources"]:
            item = source_files[source["exhibit"]]
            assert 1 <= source["page"] <= item["pages"]
            assert source["exhibit"] in public_sources
            assert public_sources[source["exhibit"]]["pages"] == item["pages"]
    assert report["conversations"] == len(c)
    assert all(v in (1, 2, 3) for v in discovery.get("email_heat", {}).values())
    assert all(
        target in by_conversation for target in discovery.get("conversation_aliases", {}).values()
    )
    if (ROOT / "data/emails.json").exists():
        emails = read("emails.json")
        threads = emails["threads"]
        assert len({t["id"] for t in threads}) == len(threads)
        assert set(discovery.get("email_heat", {})) == {t["id"] for t in threads}
        for thread in threads:
            assert thread["title"] and thread["summary"] and thread["messages"]
            assert set(thread["themes"]) <= themes
            assert thread["quote"] and any(
                thread["quote"] in item["text"] for item in thread["messages"]
            )
            sources = {s["id"]: s for s in thread["sources"]}
            for message in thread["messages"]:
                assert message["text"] or message.get("editorial_note")
                assert message["sender"] and message["datetime_raw"]
                assert set(message["source_pages"]) <= set(sources[message["source_id"]]["pages"])
            for source in sources.values():
                assert (ROOT / source["local_file"]).is_file()
            for message in thread["messages"]:
                for figure in message.get("embedded_figures", []):
                    assert (ROOT / figure["local_file"]).is_file()
        print(
            f"PASS: {len(threads)} email exchanges; full bodies, source pages, quote anchors, figures."
        )
    omitted = [msg for msg in m if msg["record"] == "Holmes_iPhone_iMessage-MMS-SMS_043153"]
    assert len(omitted) == 1 and "[BANK PIN OMITTED]" in omitted[0]["text"]
    print(
        f"PASS: {len(m):,} unique records; {len(rows):,} source rows; {len(a)} reviewed pages; all source rows accounted for; chronological ordering; complete conversation coverage; three-hour boundaries; local sources."
    )
    print(
        f"PASS: {len(themes)} themes; {len(incidents)} incidents; all quotes exact; all passage and related-conversation links resolve; discovery references resolve."
    )


if __name__ == "__main__":
    run()
