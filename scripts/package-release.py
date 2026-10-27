#!/usr/bin/env python3
"""Create a deterministic source archive from an immutable, validated Git tag."""

import argparse
import gzip
import hashlib
from pathlib import Path
import re
import subprocess


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def package(root: Path, tag: str, destination: Path) -> Path:
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError("Release tag must be vX.Y.Z")
    commit = git(root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}").decode().strip()
    version = git(root, "show", f"{commit}:VERSION").decode().strip()
    if tag != "v" + version:
        raise ValueError("Release tag does not match its committed VERSION")
    archive_name = f"watchdog-{version}.tar.gz"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / archive_name
    manifest = destination / "SHA256SUMS"
    if archive.exists() or manifest.exists():
        raise FileExistsError("Refusing to replace existing release artifacts")
    data = git(root, "archive", "--format=tar", f"--prefix=watchdog-{version}/", commit)
    with archive.open("xb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
            compressed.write(data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with manifest.open("x", encoding="utf-8", newline="\n") as output:
        output.write(f"{digest}  {archive_name}\n")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        archive = package(root, args.tag, args.output_dir.resolve())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Release packaging failed: {error}\n")
    print(f"Created {archive.name} and SHA256SUMS from {args.tag}")


if __name__ == "__main__":
    main()
