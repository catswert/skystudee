from __future__ import annotations
import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECKS = {
    "POETRY_MOVEMENTS_CARDS": ("english-poetry-movements-and-poets.studydeck.json", "english:poetry_movements", 85,
                               ("Poetry movements in order, oldest first", "Movement after Modernists", "John Donne", "Sylvia Plath")),
    "POETRY_POEMS_CARDS": ("english-poetry-poems.studydeck.json", "english:poetry_poems", 38,
                           ("“When I Have Fears That I May Cease to Be”", "“Thirteen Ways of Looking at a Blackbird”", "“Her Kind”")),
}


class PoetryDeckTests(unittest.TestCase):
    def test_embedded_exports_match(self):
        source = (ROOT / "src/skystudee.html").read_text()
        for const, (filename, deck_id, count, fronts) in DECKS.items():
            with self.subTest(deck=deck_id):
                export = json.loads((ROOT / "decks" / filename).read_text())
                embedded = re.search(rf"const {const} = (\[.*?\]);\n", source, re.S)
                self.assertIsNotNone(embedded)
                self.assertEqual(json.loads(embedded.group(1)), export["cards"])
                self.assertEqual(export["deckId"], deck_id)
                self.assertEqual(export["unitName"], "Poetry")
                cards = export["cards"]
                self.assertEqual(len(cards), count)
                self.assertEqual(len({c["id"] for c in cards}), len(cards))
                self.assertEqual(len({c["front"].lower() for c in cards}), len(cards))
                self.assertTrue(all(c["front"].strip() and c["back"].strip() and "|" not in c["id"] for c in cards))
                for front in fronts:
                    self.assertIn(front, {c["front"] for c in cards})

    def test_movement_order_chain_is_consistent(self):
        cards = {c["front"]: c["back"] for c in json.loads((ROOT / "decks" / DECKS["POETRY_MOVEMENTS_CARDS"][0]).read_text())["cards"]}
        order = [part.strip() for part in cards["Poetry movements in order, oldest first"].split(",")]
        self.assertEqual(len(order), 7)
        for earlier, later in zip(order, order[1:]):
            self.assertTrue(cards[f"Movement after {earlier}"].startswith(later), (earlier, later))
        initials = re.search(r"\((.*)\)", cards["Mnemonic for the movement order"]).group(1).split("-")
        self.assertEqual(initials, [name[0] for name in order])

    def test_schema_17_seed(self):
        s = (ROOT / "src/skystudee.html").read_text()
        self.assertIn("const APP_VERSION = 17;", s)
        self.assertIn("function seedPoetryDecksForUpgrade", s)
        self.assertIn("seedPoetryDecksForUpgrade(target, saved.version);", s)
        self.assertIn('bundledUnit(target, english.id, "Poetry")', s)


if __name__ == "__main__":
    unittest.main()
