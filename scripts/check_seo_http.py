"""Optional HTTP checks against the local Cloudflare Pages emulator."""

import argparse
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


def run(base):
    base = base.rstrip("/")

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args):
            return None

    for path, target in [
        ("/reader", "/"),
        ("/reader.html", "/"),
        ("/texts/c053/", "/texts/c052/"),
        ("/texts/c001", "/texts/c001/"),
    ]:
        try:
            build_opener(NoRedirect).open(base + path, timeout=10)
            raise AssertionError(("Expected permanent redirect", path))
        except HTTPError as error:
            assert error.code in (301, 308), (path, error.code)
            assert error.headers["Location"] in (target, base + target), (
                path,
                error.headers["Location"],
            )

    checks = [
        ("/", 200),
        ("/texts/c001/", 200),
        ("/emails/email-1675/", 200),
        ("/topics/warning-signs/", 200),
        ("/sitemap.xml", 200),
        ("/robots.txt", 200),
        ("/this-page-does-not-exist", 404),
        ("/reader.html", 200),
        ("/texts/c053/", 200),
    ]
    for path, expected in checks:
        try:
            with urlopen(base + path, timeout=10) as response:
                status, url = response.status, response.url
        except HTTPError as error:
            status, url = error.code, error.url
        assert status == expected, (path, status)
        if path == "/texts/c053/":
            assert url.endswith("/texts/c052/")
        if path == "/reader.html":
            assert url == base + "/"
        print(path, status, url.removeprefix(base))
    for host in [
        "theranos-text-reader.pages.dev",
        "abc.theranos-text-reader.pages.dev",
        "theranotes.juliawinn.com",
    ]:
        with urlopen(
            Request(base + "/texts/c001/", headers={"Host": host}), timeout=10
        ) as response:
            robots = response.headers.get("X-Robots-Tag")
            assert ("noindex" in (robots or "")) == host.endswith(".pages.dev"), (host, robots)
            print(host, "X-Robots-Tag:", robots)
    print("PASS: HTTP status codes, legacy path redirects and preview-host indexing headers.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8788")
    run(parser.parse_args().base_url)
