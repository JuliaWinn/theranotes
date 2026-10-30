"""Build a temporary public export without research files or cached page images."""

import subprocess
import sys
import tempfile
from pathlib import Path

from export_repository import export


def main():
    with tempfile.TemporaryDirectory(prefix="theranotes-clean-build-") as work:
        checkout = Path(work) / "repository"
        export(checkout)
        subprocess.run([sys.executable, "scripts/build_site.py"], cwd=checkout, check=True)
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=checkout, check=True
        )
        subprocess.run(
            [
                "node",
                "--test",
                *sorted(
                    str(p.relative_to(checkout)) for p in (checkout / "tests").glob("*.test.cjs")
                ),
            ],
            cwd=checkout,
            check=True,
        )
        print(
            "PASS: public files alone build and pass source, transcript, SEO and analytics checks."
        )


if __name__ == "__main__":
    main()
