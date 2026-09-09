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
        base_match = re.search(r"const SENSATION_BASE_CARDS = (\[.*?\]);\n", source, re.S)
        states_match = re.search(r"const CONSCIOUSNESS_CARDS = (\[.*?\]);\n", source, re.S)
        self.assertIsNotNone(base_match)
        self.assertIsNotNone(states_match)
        base_cards = json.loads(base_match.group(1))
        states_cards = json.loads(states_match.group(1))
        embedded = base_cards + states_cards

        self.assertEqual(deck["format"], "StudyCardsDeck")
        self.assertEqual(deck["version"], 1)
        self.assertEqual(deck["deckId"], "ap_psych:unit_1_sensation")
        self.assertEqual(deck["classCatalogId"], "ap_psychology")
        self.assertEqual(deck["unitName"], "Unit 1")
        self.assertEqual(deck["cards"], embedded)
        self.assertEqual(len(base_cards), 70)
        self.assertEqual(len(states_cards), 35)
        self.assertEqual(len(embedded), 105)

        ids = [card["id"] for card in embedded]
        pairs = [(card["front"].casefold(), card["back"].casefold()) for card in embedded]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertTrue(all(card["front"].strip() and card["back"].strip() for card in embedded))
        self.assertTrue(all("|" not in card["id"] for card in embedded))
        self.assertTrue(all(not card["back"].rstrip().endswith((".", "!", "?")) for card in states_cards))
        self.assertTrue(all(len(re.findall(r"\b[\w'-]+\b", card["back"])) <= 14 for card in states_cards))

    def test_versioned_expansion_contract(self) -> None:
        source = (ROOT / "src" / "skystudee.html").read_text(encoding="utf-8")
        self.assertIn("const APP_VERSION = 12;", source)
        self.assertIn("function seedSensationDeckForUpgrade", source)
        self.assertIn("version >= 11 || target.decks[SENSATION_DECK_ID]", source)
        self.assertIn("function upgradeSensationDeckForConsciousness", source)
        self.assertIn("if (version >= 12) return;", source)
        self.assertIn("if (!deck) return;", source)
        self.assertIn("upgradeSensationDeckForConsciousness(target, saved.version);", source)


if __name__ == "__main__":
    unittest.main()
