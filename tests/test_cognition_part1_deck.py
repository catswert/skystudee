from __future__ import annotations

import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CognitionPart1DeckTests(unittest.TestCase):
    def test_export_matches_embedded_preload(self) -> None:
        deck = json.loads((ROOT / "decks" / "ap-psychology-unit-2-part-1-cognition.studydeck.json").read_text(encoding="utf-8"))
        source = (ROOT / "src" / "skystudee.html").read_text(encoding="utf-8")
        match = re.search(r"const COGNITION_PART1_CARDS = (\[.*?\]);\n", source, re.S)
        self.assertIsNotNone(match)
        embedded = json.loads(match.group(1))

        self.assertEqual(deck["format"], "StudyCardsDeck")
        self.assertEqual(deck["version"], 1)
        self.assertEqual(deck["deckId"], "ap_psych:unit_2_part_1_cognition")
        self.assertEqual(deck["classCatalogId"], "ap_psychology")
        self.assertEqual(deck["unitName"], "Unit 2")
        self.assertEqual(deck["cards"], embedded)
        self.assertEqual(len(embedded), 122)

        ids = [card["id"] for card in embedded]
        fronts = {card["front"] for card in embedded}
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all("|" not in card["id"] for card in embedded))
        self.assertTrue(all(card["front"].strip() and card["back"].strip() for card in embedded))
        self.assertTrue(all(not card["back"].rstrip().endswith((".", "!", "?")) for card in embedded))
        self.assertTrue(all(len(re.findall(r"\b[\w’'-]+\b", card["back"])) <= 14 for card in embedded))
        for required in ("Perception", "Working Memory", "Metacognition", "Intelligence", "Growth Mindset"):
            self.assertIn(required, fronts)

    def test_versioned_removable_seed_contract(self) -> None:
        source = (ROOT / "src" / "skystudee.html").read_text(encoding="utf-8")
        self.assertIn("const APP_VERSION = 13;", source)
        self.assertIn("function seedCognitionPart1DeckForUpgrade", source)
        self.assertIn("version >= 13 || target.decks[COGNITION_PART1_DECK_ID]", source)
        self.assertIn('findOrCreateUnit(target, psych.id, "Unit 2")', source)
        self.assertIn("seedCognitionPart1DeckForUpgrade(target, saved.version);", source)


if __name__ == "__main__":
    unittest.main()
