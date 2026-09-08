#!/usr/bin/env python3
"""Read-only recovery for old branches which contain only a loader and chunks.

Write to a NEW output path. Never run this over the documented canonical source
without comparing it first: the historical branch may predate Firebase/features.
"""
from __future__ import annotations
import argparse
import base64
import gzip
import hashlib
from pathlib import Path
import re


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    loader = (args.root / "index.html").read_text(encoding="utf-8")
    match = re.search(r"Array\.from\(\{\s*length\s*:\s*(\d+)", loader)
    if not match:
        raise SystemExit("Cannot find the deployed loader's chunk count")
    encoded = b"".join((args.root / f"assets/mobile-build-{i:02d}").read_bytes().strip()
                       for i in range(1, int(match.group(1)) + 1))
    data = gzip.decompress(base64.b64decode(encoded, validate=True))
    data.decode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as output:  # Never overwrite an existing source.
        output.write(data)
    print(f"Recovered {len(data)} bytes; SHA256 {hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
