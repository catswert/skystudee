from __future__ import annotations
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DevelopmentDeckTests(unittest.TestCase):
    def test_embedded_export_and_content(self):
        source=(ROOT/"src/skystudee.html").read_text()
        export=json.loads((ROOT/"decks/ap-psychology-unit-3-development-and-learning.studydeck.json").read_text())
        embedded=re.search(r"const DEVELOPMENT_CARDS = (\[.*?\]);\n",source,re.S)
        self.assertIsNotNone(embedded)
        self.assertEqual(json.loads(embedded.group(1)),export["cards"])
        self.assertEqual(export["format"],"StudyCardsDeck")
        self.assertEqual(export["version"],1)
        self.assertEqual(export["deckId"],"ap_psych:unit_3_development_and_learning")
        self.assertEqual(export["unitName"],"Unit 3")
        cards=export["cards"]
        self.assertEqual(len(cards),117)
        self.assertEqual(len({c["id"] for c in cards}),len(cards))
        self.assertTrue(all(c["front"].strip() and c["back"].strip() and "|" not in c["id"] for c in cards))
        self.assertTrue(all(len(re.findall(r"[\w’'-]+",c["back"]))<=14 for c in cards))
        fronts={c["front"] for c in cards}
        for term in ("Object Permanence","Zone of Proximal Development","Ainsworth’s Strange Situation","Identity Achievement","Kohlberg’s Moral Development Theory"):
            self.assertIn(term,fronts)
    def test_schema_migration(self):
        s=(ROOT/"src/skystudee.html").read_text()
        self.assertIn("const APP_VERSION = 14;",s)
        self.assertIn("function seedDevelopmentDeckForUpgrade",s)
        self.assertIn("version >= 14 || target.decks[DEVELOPMENT_DECK_ID]",s)
        self.assertIn('findOrCreateUnit(target, psych.id, "Unit 3")',s)
        self.assertIn("seedDevelopmentDeckForUpgrade(target, saved.version);",s)
if __name__=="__main__":unittest.main()
