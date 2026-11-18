from __future__ import annotations
import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "decks/ap-psychology-unit-3-learning.studydeck.json"


class LearningDeckTests(unittest.TestCase):
    def test_embedded_export_matches_and_covers_slide_terms(self):
        source = (ROOT / "src/skystudee.html").read_text()
        export = json.loads(EXPORT.read_text())
        embedded = re.search(r"const LEARNING_CARDS = (\[.*?\]);\n", source, re.S)
        self.assertIsNotNone(embedded)
        self.assertEqual(json.loads(embedded.group(1)), export["cards"])
        self.assertEqual(export["deckId"], "ap_psych:unit_3_learning")
        self.assertEqual(export["unitName"], "Unit 3")
        cards = export["cards"]
        self.assertEqual(len(cards), 54)
        self.assertEqual(len({c["id"] for c in cards}), len(cards))
        self.assertTrue(all(c["front"].strip() and c["back"].strip() and "|" not in c["id"] for c in cards))
        self.assertTrue(all(len(re.findall(r"[\w’'-]+", c["back"])) <= 14 for c in cards))
        fronts = {c["front"] for c in cards}
        for term in ("Classical Conditioning", "Spontaneous Recovery", "Negative Reinforcement",
                     "Variable-Ratio Schedule (VR)", "Learned Helplessness", "Latent Learning",
                     "Albert Bandura’s Bobo Doll Experiment"):
            self.assertIn(term, fronts)

    def test_schema_16_seeds_once_into_unit_3(self):
        s = (ROOT / "src/skystudee.html").read_text()
        self.assertIn("const APP_VERSION = 16;", s)
        self.assertIn("function seedLearningDeckForUpgrade", s)
        self.assertIn("seedLearningDeckForUpgrade(target, saved.version);", s)
        self.assertIn('bundledUnit(target, psych.id, "Unit 3")', s)


if __name__ == "__main__":
    unittest.main()
