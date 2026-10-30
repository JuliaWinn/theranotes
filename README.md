# Theranotes

A searchable reading archive of Elizabeth Holmes and Sunny Balwani's text messages and selected Theranos trial emails.

**[Read the archive](https://theranotes.juliawinn.com/)**

The collection contains 2,694 text records in 201 conversations and 11 email exchanges. Each exchange has a permanent URL, a readable transcript, and citations to the court exhibits. These are the records included in the selected exhibits, not a complete message history or mailbox.

## Run locally

You need Python 3.12 or newer, Node.js 24, and Poppler's `pdftoppm` command.

Install Poppler with `brew install poppler` on macOS or `sudo apt-get install poppler-utils` on Ubuntu/Debian, then:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci
npm run build
npm run preview
```

The first build renders the selected public PDFs into WebP page images. Later builds reuse a cache tied to the PDF checksum and rendering settings. No court downloads, credentials, or private research files are needed to build the site.

## How it works

- `data/` contains the reviewed transcripts, editorial groupings, and page-count audit.
- `exhibits/reader-sources.json` selects the 25 public PDFs, with checksums of the copies used by the build.
- `src/` contains the homepage HTML, CSS, and browser JavaScript.
- `scripts/` builds the site and checks source coverage, transcripts, metadata, and links.
- `dist/` is generated output. Individual exchanges are complete HTML; JavaScript adds homepage search, discovery, and optional controls.

GoatCounter remains the sole analytics integration. It runs only on `theranotes.juliawinn.com`; local previews and forks do not send visits to that account. Search terms and message fragments are not recorded.

The GoatCounter site code and collection URL in `src/analytics.js` are public browser configuration, as in [GoatCounter's installation instructions](https://www.goatcounter.com/help/start). They are not API credentials. No account password or API token is required to build or run the reader; keep any such credentials outside the repository.

## Checks

```sh
npm test
npm run check
npm run check:seo
npm run lint
npm run check:clean
```

`check:seo` reads the most recent build. `check:clean` copies the explicit public file list into a temporary directory and builds it without caches or research material.

See [development](docs/development.md), [source methodology](docs/sources.md), and [contributing](CONTRIBUTING.md). Original project code and documentation are available under the [MIT License](LICENSE). Court exhibits, quoted evidence, and other third-party material are excluded from this license; see [Software and evidence](docs/sources.md#software-and-evidence).
