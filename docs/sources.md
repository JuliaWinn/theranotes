# Sources and transcription

Theranotes transcribes selected public exhibits from *United States v. Holmes* and *United States v. Balwani*. The text collection combines Trial Exhibits 5387A–I and additional docket exhibits. Eleven selected email exchanges are included alongside the texts.

The transcripts retain spelling, typos, uncertainty notes, redactions, and blank-message markers. Record IDs repeated across exhibits appear once, with every source retained. Different IDs with identical text remain distinct records. Source rows are counted against the independently reviewed page audit in `data/page-review.json` and `data/page-review.csv`.

Text timestamps are copied as printed and presumed UTC. No local-time conversion is applied. Email timestamps retain the printed timezone where stated. A new text conversation begins after a gap of three hours or more. Titles, descriptions, highlights, and topic tags are editorial navigation aids, separate from the source text.

## Public copies and checksums

`exhibits/reader-sources.json` is the build's authoritative selection of public PDFs. Its checksums describe the exact distributed files. `exhibits/manifest.json` retains the earlier text-source inventory, including original-source provenance; its original-file checksum must not be confused with the checksum of an edited public copy.

One public reading copy, `exhibits/public/ECF-1072-3.pdf`, omits a bank PIN on PDF page 18. The omission is labelled editorially in the transcript and PDF; it is not a court redaction. The affected PDF page was rebuilt from pixels to avoid retaining the omitted text in a hidden text layer. The original research PDF, raw OCR, and original page render are excluded from the public repository selection.

The build renders page previews directly from these public PDFs. It cannot substitute a research original when a public copy is missing.

## Scope and corrections

The cited exhibits contain excerpts, not a complete private message history. A gap does not establish that no messages were exchanged. The email selection is not a complete mailbox. See the site’s [About & sources](https://theranotes.juliawinn.com/about/) page for the reading methodology and source links.

For a correction, cite the record ID, exhibit, and PDF page; include the proposed reading and the reason. Do not silently normalize quoted language or invent missing text. Preserve existing URL identifiers and editorial omission markers.

## Software and evidence

The [MIT License](../LICENSE) applies to original project code and documentation. Court PDFs, quoted messages, email text, source figures, and other third-party material are excluded from that license and retain their own provenance. The software license does not grant rights in third-party material. Dependencies retain their respective licenses.
