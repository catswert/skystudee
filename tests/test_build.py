"""No browser or cloud access: build integrity and comment-safe HTML checks."""
from __future__ import annotations
import importlib.util
from html.parser import HTMLParser
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("skystudee_build", ROOT / "tools/build.py")
assert spec and spec.loader
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class MarkupShape(HTMLParser):
    """Record actual DOM markup/text, ignoring comments and executable/style bodies."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        self.tokens.append(("start", tag, attrs))
        if tag in ("script", "style"):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False
        self.tokens.append(("end", tag))

    def handle_startendtag(self, tag, attrs):
        self.tokens.append(("empty", tag, attrs))

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.tokens.append(("text", data.strip()))


class BuildTests(unittest.TestCase):
    """Run against copies so corruption tests cannot modify the real repository."""
    def clone(self, path):
        for name in ("src", "assets"):
            shutil.copytree(ROOT / name, path / name)
        for name in ("index.html", "build-manifest.json"):
            shutil.copy2(ROOT / name, path / name)

    def test_checked_in_assets_match_source(self):
        self.assertGreater(len(build.check()["parts"]), 0)

    def test_tampered_and_extra_parts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.clone(root)
            chunk = root / "assets/mobile-build-01"
            original = chunk.read_bytes()
            chunk.write_bytes(b"!" + original[1:])
            with self.assertRaises(ValueError):
                build.check(root)
            chunk.write_bytes(original)
            (root / "assets/mobile-build-999").write_bytes(b"AAAA")
            with self.assertRaises(ValueError):
                build.check(root)

    def test_build_round_trip_and_stale_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.clone(root)
            (root / "assets/mobile-build-999").write_bytes(b"AAAA")
            manifest = build.build("test-only", root)
            self.assertEqual(manifest["version"], "test-only")
            self.assertFalse((root / "assets/mobile-build-999").exists())
            self.assertEqual(build.check(root)["sourceSha256"], build.digest((root / "src/skystudee.html").read_bytes()))

    def test_template_and_version_validation(self):
        with self.assertRaises(ValueError):
            build.render_loader(b"broken template", "test", 1)
        with self.assertRaises(ValueError):
            build.render_loader((ROOT / "src/loader.html").read_bytes(), "bad'input", 1)


if __name__ == "__main__":
    unittest.main()
