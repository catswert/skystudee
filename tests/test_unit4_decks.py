from __future__ import annotations
import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECKS = {
    "SOCIAL_PSYCH_CARDS": ("ap-psychology-unit-4-social-psychology.studydeck.json",
                           "ap_psych:unit_4_social_psychology", 73,
                           ("Fundamental Attribution Error", "Bystander Effect", "Cognitive Dissonance",
                            "Elaboration Likelihood Model", "Stanley Milgram’s Obedience Experiment")),
    "PERSONALITY_CARDS": ("ap-psychology-unit-4-motivation-emotion-personality.studydeck.json",
                          "ap_psych:unit_4_motivation_emotion_personality", 81,
                          ("Yerkes-Dodson Law", "Schachter-Singer Two-Factor Theory", "Reaction Formation",
                           "Reciprocal Determinism", "Big Five Theory")),
}


class Unit4DeckTests(unittest.TestCase):
    def test_embedded_exports_match_and_cards_are_concise(self):
        source = (ROOT / "src/skystudee.html").read_text()
        for const, (filename, deck_id, count, terms) in DECKS.items():
            with self.subTest(deck=deck_id):
                export = json.loads((ROOT / "decks" / filename).read_text())
                embedded = re.search(rf"const {const} = (\[.*?\]);\n", source, re.S)
                self.assertIsNotNone(embedded)
                self.assertEqual(json.loads(embedded.group(1)), export["cards"])
                self.assertEqual(export["format"], "StudyCardsDeck")
                self.assertEqual(export["version"], 1)
                self.assertEqual(export["deckId"], deck_id)
                self.assertEqual(export["unitName"], "Unit 4")
                cards = export["cards"]
                self.assertEqual(len(cards), count)
                self.assertEqual(len({c["id"] for c in cards}), len(cards))
                self.assertTrue(all(c["front"].strip() and c["back"].strip() and "|" not in c["id"] for c in cards))
                self.assertTrue(all(len(re.findall(r"[\w’'-]+", c["back"])) <= 14 for c in cards))
                fronts = {c["front"] for c in cards}
                for term in terms:
                    self.assertIn(term, fronts)

    def test_schema_15_migration_and_german_retirement(self):
        s = (ROOT / "src/skystudee.html").read_text()
        self.assertIn("const APP_VERSION = 15;", s)
        self.assertIn("function seedUnit4DecksForUpgrade", s)
        self.assertIn("seedUnit4DecksForUpgrade(target, saved.version);", s)
        self.assertIn('findOrCreateUnit(target, psych.id, "Unit 4")', s)
        self.assertIn('const RETIRED_GERMAN_DECK_ID = "builtin:german-perfect:v1";', s)
        self.assertNotIn("BUILTIN_CARDS", s)
        self.assertNotIn("ensureBuiltInDeck", s)
        self.assertNotIn("Verben im Perfekt", s)


if __name__ == "__main__":
    unittest.main()
