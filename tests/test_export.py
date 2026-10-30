"""Check that preparing a public copy cannot include arbitrary paths or overwrite work."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from export_repository import ROOT, export, public_files


class PublicExportTests(unittest.TestCase):
    def test_rejects_parent_paths(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            (root / "repository-files.txt").write_text("../outside.txt\n")
            with self.assertRaisesRegex(ValueError, "Invalid public path"):
                public_files(root)

    def test_existing_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as work:
            output = Path(work)
            marker = output / "user-work.txt"
            marker.write_text("keep me")
            with self.assertRaises(FileExistsError):
                export(output)
            self.assertEqual(marker.read_text(), "keep me")
            self.assertEqual(list(output.iterdir()), [marker])

    def test_git_selection_matches_reviewed_files(self):
        with tempfile.TemporaryDirectory() as work:
            subprocess.run(["git", "init", "--quiet", work], check=True)
            output = subprocess.check_output(
                [
                    "git",
                    "--git-dir=" + work + "/.git",
                    "--work-tree=" + str(ROOT),
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                ],
                text=True,
            )
            self.assertEqual(set(output.splitlines()), set(public_files()))


if __name__ == "__main__":
    unittest.main()
