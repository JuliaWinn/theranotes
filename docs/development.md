# Development

## Build inputs

The build reads `data/conversations.json` as the reviewed conversation index. Conversation IDs are stable: changing a title must not renumber URLs. The historical OCR pipeline, downloaded research archive, prompts, intermediate drafts, and local deployment records are not build inputs.

`exhibits/reader-sources.json` names only selected public copies. Each entry records its SHA-256 checksum, page count, source URL, rendering resolution, and any editorial omission. A missing or changed PDF stops the build. For the one edited exhibit, the selected file is the redacted public PDF; there is no fallback to the research original or a temporary image.

The image cache uses the public PDF checksum, page count, Poppler version, Pillow version, resolution, and encoding settings. It lives in `.cache/`; generated page images live in `exhibits/pages/`. Both can be regenerated.

## Browser code

`reader-data.js` initializes the reviewed dataset and shared indexes. `analytics.js` defines production-only GoatCounter tracking. `discovery.js` handles the homepage feed, search state, and legacy fragment redirects. `reader.js` renders search results and browse dialogs, binds controls, and starts the homepage.

The build combines those files in that order and writes content-hashed assets. It does not extract CSS or JavaScript from a generated HTML file. `reader.html` is the HTML template; `reader.css` is its stylesheet. Archive pages use `archive.css` and `archive.js`.

Normal navigation opens static exchange pages. Legacy links such as `/#conversation-c001` still redirect to `/texts/c001/`. Keep this compatibility when changing navigation.

## Editing and validation

Activate `.venv` before using the npm scripts that run Python or Ruff. `npm run format` formats maintained source files; transcript JSON is deliberately excluded from formatters.

`npm test` checks public-copy rendering, missing/changed source handling, cache invalidation, and GoatCounter host restrictions and page counting. `npm run check` validates reviewed data and source coverage. `npm run build` runs that check, renders public PDFs, creates HTML and assets, and validates the resulting site.

Use `npm run check:clean` before a release. CI runs the same public-file build and checks on Linux. It has read-only repository permissions and no deployment step.

## Preparing a repository snapshot

`repository-files.txt` is the explicit public selection. To add a maintained file, add its path there and run:

```sh
python scripts/export_repository.py --refresh-ignore
```

The generated `.gitignore` excludes everything else. Export into a new directory for review:

```sh
python scripts/export_repository.py --output /tmp/theranotes-public-review
```

The exporter refuses an existing destination and checks the selected public PDF hashes. It does not initialize Git, create a GitHub repository, push, or deploy. Keep private research material outside this selection.

## Deployment

The existing hosting target is the Cloudflare Pages project `theranos-text-reader`, serving `https://theranotes.juliawinn.com/`. `npm run deploy` publishes the current `dist/` artifact. Build and review it first, and obtain Julia's explicit approval for that exact artifact before running the deploy command. This project has no automatic deployment workflow.

`python scripts/check_seo_http.py` checks a local Pages preview. `python scripts/verify_live_seo.py` compares the public site with the current local build; run it only after an approved deployment. Local cleanup does not imply the live site has changed.
