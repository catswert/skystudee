#!/usr/bin/env python3
"""Build/check the existing static loader format without modifying app semantics.

Author source in src/skystudee.html, not assets/mobile-build-*. A normal build
writes the whole generated set; commit it together. --check is read-only and
validates recorded bytes, rather than requiring the same zlib version everywhere.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHUNK_CHARS = 9792  # Historical ASCII transport boundary, not a gzip block size.
CHUNK_RE = re.compile(r"mobile-build-\d+$")


def digest(data: bytes) -> str:
    """Return a content integrity hash (unrelated to card/deck identity hashes)."""
    return hashlib.sha256(data).hexdigest()


def render_loader(template: bytes, version: str, count: int) -> bytes:
    """Fill only explicit build placeholders; reject unsafe/accidental substitutions."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", version):
        raise ValueError("Use a nonempty alphanumeric/dot/dash/underscore version")
    text = template.decode("utf-8")
    for placeholder in ("__BUILD_VERSION__", "__BUILD_COUNT__"):
        if text.count(placeholder) != 1:
            raise ValueError(f"Loader template must contain {placeholder} exactly once")
    return text.replace("__BUILD_VERSION__", version).replace("__BUILD_COUNT__", str(count)).encode("utf-8")


def existing_parts(root: Path) -> set[str]:
    """Find only the generated chunk names; do not touch unrelated assets."""
    return {f"assets/{p.name}" for p in (root / "assets").glob("mobile-build-*") if CHUNK_RE.fullmatch(p.name)}


def check(root: Path = ROOT) -> dict:
    """Check source, template, loader, every ordered part and reconstructed bytes."""
    manifest = json.loads((root / "build-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "SkyStudeeStaticBuild" or manifest.get("formatVersion") != 1:
        raise ValueError("Unknown build manifest format")
    source = (root / "src/skystudee.html").read_bytes()
    template = (root / "src/loader.html").read_bytes()
    parts = manifest["parts"]
    if not parts or manifest["chunkChars"] != CHUNK_CHARS:
        raise ValueError("Invalid chunk specification")
    expected_names = [f"assets/mobile-build-{i:02d}" for i in range(1, len(parts) + 1)]
    if [part["path"] for part in parts] != expected_names or existing_parts(root) != set(expected_names):
        raise ValueError("Missing, extra, or out-of-order generated parts")
    encoded = []
    for index, part in enumerate(parts):
        data = (root / part["path"]).read_bytes()
        expected_length = CHUNK_CHARS if index < len(parts) - 1 else part["bytes"]
        if not 0 < len(data) <= CHUNK_CHARS or len(data) != expected_length:
            raise ValueError(f"Bad part length: {part['path']}")
        if digest(data) != part["sha256"] or len(data) != part["bytes"]:
            raise ValueError(f"Part hash/length mismatch: {part['path']}")
        encoded.append(data)
    reconstructed = gzip.decompress(base64.b64decode(b"".join(encoded), validate=True))
    if reconstructed != source or digest(source) != manifest["sourceSha256"] or len(source) != manifest["sourceBytes"]:
        raise ValueError("Generated assets do not match src/skystudee.html")
    loader = render_loader(template, manifest["version"], len(parts))
    if loader != (root / "index.html").read_bytes() or digest(loader) != manifest["loaderSha256"]:
        raise ValueError("Generated loader does not match its template/version/count")
    if digest(template) != manifest["loaderTemplateSha256"]:
        raise ValueError("Loader template changed without rebuilding")
    return manifest


def build(version: str, root: Path = ROOT) -> dict:
    """Prepare all bytes before writing; a repository commit publishes the set atomically."""
    source = (root / "src/skystudee.html").read_bytes()
    source.decode("utf-8")  # Fail early rather than deploying an invalid text file.
    template = (root / "src/loader.html").read_bytes()
    buffer = io.BytesIO()
    # Filename/mtime are removed for stable headers; zlib versions can still vary.
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=0, compresslevel=9) as stream:
        stream.write(source)
    encoded = base64.b64encode(buffer.getvalue())
    data_parts = [encoded[i:i + CHUNK_CHARS] for i in range(0, len(encoded), CHUNK_CHARS)]
    if gzip.decompress(base64.b64decode(encoded, validate=True)) != source:
        raise ValueError("Compression round trip failed")
    loader = render_loader(template, version, len(data_parts))
    manifest = {
        "format": "SkyStudeeStaticBuild", "formatVersion": 1, "version": version,
        "sourceSha256": digest(source), "sourceBytes": len(source),
        "loaderTemplateSha256": digest(template), "loaderSha256": digest(loader),
        "chunkChars": CHUNK_CHARS,
        "parts": [{"path": f"assets/mobile-build-{i:02d}", "bytes": len(data), "sha256": digest(data)}
                  for i, data in enumerate(data_parts, 1)],
    }
    outputs = {part["path"]: data for part, data in zip(manifest["parts"], data_parts)}
    outputs["index.html"] = loader
    outputs["build-manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    # Stage files on the same filesystem before replacing. This is not a live
    # deploy: commit all outputs together and let Pages publish the artifact.
    with tempfile.TemporaryDirectory(prefix=".skystudee-build-", dir=root) as temp:
        stage = Path(temp)
        for rel, data in outputs.items():
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for rel in outputs:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (stage / rel).replace(root / rel)
    for rel in existing_parts(root) - {p["path"] for p in manifest["parts"]}:
        (root / rel).unlink()
    return check(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only integrity/source check")
    parser.add_argument("--version", help="Required for a build; unique deployment label")
    args = parser.parse_args()
    if args.check and args.version:
        parser.error("--check and --version cannot be combined")
    if not args.check and not args.version:
        parser.error("Supply --version for a build, or --check to validate")
    try:
        manifest = check() if args.check else build(args.version)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Build check failed: {error}", file=sys.stderr)
        return 1
    print(f"OK {manifest['version']} | {len(manifest['parts'])} parts | source {manifest['sourceSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
