"""Copy the explicit public file list into a new, reviewable directory."""

import argparse
import shutil
from pathlib import Path

from sources import ROOT, load_sources


def public_files(root=ROOT):
    names = [
        line.strip()
        for line in (root / "repository-files.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate entry in repository-files.txt")
    for name in names:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != name:
            raise ValueError(f"Invalid public path: {name}")
        target = root / path
        if not target.is_file() or target.is_symlink() or target.resolve() != root.resolve() / path:
            raise ValueError(f"Missing file or symlink in public selection: {name}")
    for source in load_sources(root):
        if source["file"] not in names:
            raise ValueError(f"Public selection is missing source {source['id']}")
    return names


def ignore_rules(names):
    parents = {
        parent.as_posix() for name in names for parent in Path(name).parents if parent != Path(".")
    }
    return (
        "# Generated from repository-files.txt by scripts/export_repository.py --refresh-ignore.\n"
        "# Only reviewed files are eligible for Git; research, caches and backups stay local.\n*\n"
        + "".join(f"!/{parent}/\n" for parent in sorted(parents, key=lambda p: (p.count("/"), p)))
        + "".join(f"!/{name}\n" for name in sorted(names))
    )


def export(output, root=ROOT):
    names = public_files(root)
    if (root / ".gitignore").read_text() != ignore_rules(names):
        raise ValueError("Refresh .gitignore after changing repository-files.txt")
    # Never replace an existing checkout, directory, or user file.
    output.mkdir(parents=True, exist_ok=False)
    for name in names:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    size = sum((root / name).stat().st_size for name in names)
    print(f"Exported {len(names)} reviewed files ({size / 1024**2:.1f} MiB) to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--output", type=Path, help="New directory to create; existing paths are refused"
    )
    mode.add_argument("--refresh-ignore", action="store_true")
    args = parser.parse_args()
    if args.refresh_ignore:
        (ROOT / ".gitignore").write_text(ignore_rules(public_files()))
    else:
        export(args.output.resolve())


if __name__ == "__main__":
    main()
