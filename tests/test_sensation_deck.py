from __future__ import annotations

import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SensationDeckTests(unittest.TestCase):
    def test_export_matches_embedded_preload(self) -> None:
        deck = json.loads((ROOT / "decks" / "ap-psychology-unit-1-sensation.studydeck.json").read_text(encoding="utf-8"))
        source = (ROOT / "src" / "skystudee.html").read_text(encoding="utf-8")
        match = re.search(r"const SENSATION_CARDS = (\[.*?\]);\n", source, re.S)
        self.assertIsNotNone(match)
        embedded = json.loads(match.group(1))

        self.assertEqual(deck["format"], "StudyCardsDeck")
        self.assertEqual(deck["version"], 1)
        self.assertEqual(deck["deckId"], "ap_psych:unit_1_sensation")
        self.assertEqual(deck["classCatalogId"], "ap_psychology")
        self.assertEqual(deck["unitName"], "Unit 1")
        self.assertEqual(deck["cards"], embedded)
        self.assertEqual(len(embedded), 70)

        ids = [card["id"] for card in embedded]
        pairs = [(card["front"].casefold(), card["back"].casefold()) for card in embedded]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertTrue(all(card["front"].strip() and card["back"].strip() for card in embedded))
        self.assertTrue(all("|" not in card["id"] for card in embedded))

    def test_versioned_removable_seed_contract(self) -> None:
        source = (ROOT / "src" / "skystudee.html").read_text(encoding="utf-8")
        self.assertIn("const APP_VERSION = 11;", source)
        self.assertIn("function seedSensationDeckForUpgrade", source)
        self.assertIn("version >= 11 || target.decks[SENSATION_DECK_ID]", source)
        self.assertIn('findOrCreateUnit(target, psych.id, "Unit 1")', source)
        self.assertIn("seedSensationDeckForUpgrade(target, saved.version);", source)


if __name__ == "__main__":
    unittest.main()
