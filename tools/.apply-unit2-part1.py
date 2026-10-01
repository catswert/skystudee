from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "skystudee.html"
DECK_PATH = ROOT / "decks" / "ap-psychology-unit-2-part-1-cognition.studydeck.json"

deck = json.loads(DECK_PATH.read_text(encoding="utf-8"))
cards = deck["cards"]
assert len(cards) == 122
assert deck["deckId"] == "ap_psych:unit_2_part_1_cognition"
assert deck["unitName"] == "Unit 2"
assert len({c["id"] for c in cards}) == 122
assert all(c["front"].strip() and c["back"].strip() for c in cards)
assert all(not c["back"].rstrip().endswith((".", "!", "?")) for c in cards)
assert all(len(re.findall(r"\b[\w’'-]+\b", c["back"])) <= 14 for c in cards)

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)

source = SRC.read_text(encoding="utf-8")
source = replace_once(source, "const APP_VERSION = 12;", "const APP_VERSION = 13;", "schema version")

catalog_marker = "    // CATALOG DATA: internal templates/aliases, not user instances. Unit names are intentionally absent from the global class catalog.\n"
cards_json = json.dumps(cards, ensure_ascii=False, separators=(",", ":"))
unit2_block = f'''    // ==========================================================
    // PRELOADED UNIT 2 PART 1 — COGNITION
    // ==========================================================
    // Removable AP Psychology Unit 2 Part 1 preload sourced from the teacher-provided
    // Perception, Memory, and Thinking & Intelligence presentations.
    const COGNITION_PART1_DECK_ID = "ap_psych:unit_2_part_1_cognition";
    const COGNITION_PART1_DECK_NAME = "Unit 2 — Part 1 — AP Psychology — Perception, Cognition, Memory & Intelligence";
    // UNIT 2 PART 1 CONTENT: keep decks/ap-psychology-unit-2-part-1-cognition.studydeck.json synchronized deliberately.
    const COGNITION_PART1_CARDS = {cards_json};

'''
if "const COGNITION_PART1_DECK_ID" not in source:
    source = replace_once(source, catalog_marker, unit2_block + catalog_marker, "unit2 constants")

class_old = '''        } else if (seedBundled && deck.id === SENSATION_DECK_ID && !deck.classId) {
          deck.classId = findOrCreateCatalogClass(target, "ap_psychology")?.id || null;
        } else if (suggestUnclassified && !deck.classId) {'''
class_new = '''        } else if (seedBundled && deck.id === SENSATION_DECK_ID && !deck.classId) {
          deck.classId = findOrCreateCatalogClass(target, "ap_psychology")?.id || null;
        } else if (seedBundled && deck.id === COGNITION_PART1_DECK_ID && !deck.classId) {
          deck.classId = findOrCreateCatalogClass(target, "ap_psychology")?.id || null;
        } else if (suggestUnclassified && !deck.classId) {'''
source = replace_once(source, class_old, class_new, "organization class placement")

unit_old = '''        } else if (seedBundled && deck.id === SENSATION_DECK_ID) {
          const psych = findClassByCatalog(target, "ap_psychology");
          if (!deck.unitId && psych && deck.classId === psych.id) deck.unitId = findOrCreateUnit(target, psych.id, "Unit 1")?.id || null;
        }

        if (!Number.isFinite(Number(deck.order))) deck.order = 0;'''
unit_new = '''        } else if (seedBundled && deck.id === SENSATION_DECK_ID) {
          const psych = findClassByCatalog(target, "ap_psychology");
          if (!deck.unitId && psych && deck.classId === psych.id) deck.unitId = findOrCreateUnit(target, psych.id, "Unit 1")?.id || null;
        } else if (seedBundled && deck.id === COGNITION_PART1_DECK_ID) {
          const psych = findClassByCatalog(target, "ap_psychology");
          if (!deck.unitId && psych && deck.classId === psych.id) deck.unitId = findOrCreateUnit(target, psych.id, "Unit 2")?.id || null;
        }

        if (!Number.isFinite(Number(deck.order))) deck.order = 0;'''
source = replace_once(source, unit_old, unit_new, "organization unit placement")

source = replace_once(
    source,
    '''     * Create a fresh local profile with German, Research Methods, and Sensation, plus explicit
     * initial organization. Brain seeding is separate; do not use this as a substitute for a
     * recoverable user's saved state.''',
    '''     * Create a fresh local profile with German, Research Methods, Unit 1, and Unit 2 Part 1,
     * plus explicit initial organization. Brain seeding is separate; do not use this as a
     * substitute for a recoverable user's saved state.''',
    "default state docs"
)

default_old = '''      const sensation = createDeckRecord({
        id: SENSATION_DECK_ID,
        name: SENSATION_DECK_NAME,
        cards: SENSATION_CARDS,
        preloaded: true
      });
      sensation.settings.mode = "memory";

      const state = {'''
default_new = '''      const sensation = createDeckRecord({
        id: SENSATION_DECK_ID,
        name: SENSATION_DECK_NAME,
        cards: SENSATION_CARDS,
        preloaded: true
      });
      sensation.settings.mode = "memory";
      const cognitionPart1 = createDeckRecord({
        id: COGNITION_PART1_DECK_ID,
        name: COGNITION_PART1_DECK_NAME,
        cards: COGNITION_PART1_CARDS,
        preloaded: true
      });
      cognitionPart1.settings.mode = "memory";

      const state = {'''
source = replace_once(source, default_old, default_new, "default unit2 deck")

map_old = '''          [BUILTIN_DECK_ID]: builtin,
          [PSYCH_DECK_ID]: psychology,
          [SENSATION_DECK_ID]: sensation
        }'''
map_new = '''          [BUILTIN_DECK_ID]: builtin,
          [PSYCH_DECK_ID]: psychology,
          [SENSATION_DECK_ID]: sensation,
          [COGNITION_PART1_DECK_ID]: cognitionPart1
        }'''
source = replace_once(source, map_old, map_new, "default deck map")

seed_marker = '''    /**
     * Expand an existing removable Sensation preload with States of Consciousness for schema 12.'''
seed_func = '''    /**
     * Add the removable Unit 2 Part 1 Cognition preload to profiles saved before schema 13.
     * Place it once under AP Psychology / Unit 2; later deletion remains authoritative.
     */
    function seedCognitionPart1DeckForUpgrade(target, savedVersion) {
      const version = Number(savedVersion || 0);
      if (version >= 13 || target.decks[COGNITION_PART1_DECK_ID]) return;
      const psych = findOrCreateCatalogClass(target, "ap_psychology");
      const unit = psych ? findOrCreateUnit(target, psych.id, "Unit 2") : null;
      const unitDecks = unit
        ? Object.fromEntries(Object.entries(target.decks || {}).filter(([, deck]) => deck.unitId === unit.id))
        : {};
      const deck = createDeckRecord({
        id: COGNITION_PART1_DECK_ID,
        name: COGNITION_PART1_DECK_NAME,
        cards: COGNITION_PART1_CARDS,
        preloaded: true,
        classId: psych?.id || null,
        unitId: unit?.id || null,
        order: nextOrder(unitDecks)
      });
      deck.settings.mode = "memory";
      target.decks[COGNITION_PART1_DECK_ID] = deck;
    }

'''
if "function seedCognitionPart1DeckForUpgrade" not in source:
    source = replace_once(source, seed_marker, seed_func + seed_marker, "unit2 seed function")

merge_old = '''      seedSensationDeckForUpgrade(target, saved.version);
      upgradeSensationDeckForConsciousness(target, saved.version);
      ensureOrganizationState(target, {'''
merge_new = '''      seedSensationDeckForUpgrade(target, saved.version);
      upgradeSensationDeckForConsciousness(target, saved.version);
      seedCognitionPart1DeckForUpgrade(target, saved.version);
      ensureOrganizationState(target, {'''
source = replace_once(source, merge_old, merge_new, "unit2 migration call")

SRC.write_text(source, encoding="utf-8")

# Existing Unit 1 test follows the current app schema while retaining its v12 expansion assertions.
sensation_test = ROOT / "tests" / "test_sensation_deck.py"
st = sensation_test.read_text(encoding="utf-8")
st = replace_once(st, 'self.assertIn("const APP_VERSION = 12;", source)', 'self.assertIn("const APP_VERSION = 13;", source)', "sensation schema assertion")
sensation_test.write_text(st, encoding="utf-8")

# New content/seed contract test.
(ROOT / "tests" / "test_cognition_part1_deck.py").write_text(r'''from __future__ import annotations

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
''', encoding="utf-8")

# Browser regression: fresh placement, upgrade seeding, and deletion persistence.
browser = ROOT / "tests" / "browser_smoke.py"
b = browser.read_text(encoding="utf-8")
b = replace_once(
    b,
    "page.evaluate('!firebaseAuthReady && Object.keys(appState.decks).length===4')",
    "page.evaluate('!firebaseAuthReady && Object.keys(appState.decks).length===5')",
    "fresh deck count"
)
unit1_check = '''        check('combined Unit 1 deck is bundled in AP Psychology Unit 1',page.evaluate("""() => {
          const deck=appState.decks[SENSATION_DECK_ID];
          const cls=appState.classes[deck?.classId];
          const unit=appState.units[deck?.unitId];
          return deck?.preloaded===true && deck.cards.length===105 &&
            cls?.catalogId==='ap_psychology' && unit?.name==='Unit 1';
        }"""))
'''
unit2_check = unit1_check + '''        check('Unit 2 Part 1 is bundled in AP Psychology Unit 2',page.evaluate("""() => {
          const deck=appState.decks[COGNITION_PART1_DECK_ID];
          const cls=appState.classes[deck?.classId];
          const unit=appState.units[deck?.unitId];
          return deck?.preloaded===true && deck.cards.length===122 &&
            cls?.catalogId==='ap_psychology' && unit?.name==='Unit 2';
        }"""))
'''
b = replace_once(b, unit1_check, unit2_check, "fresh unit2 browser check")

after_unit1 = '''        check('deleted Unit 1 preload stays deleted after migration',not after_delete_errors and after_delete.evaluate('!appState.decks[SENSATION_DECK_ID]'))

        # Synthetic colliding card IDs in separate real decks must not merge evidence.
'''
after_unit2 = '''        check('deleted Unit 1 preload stays deleted after migration',not after_delete_errors and after_delete.evaluate('!appState.decks[SENSATION_DECK_ID]'))

        pre_unit2 = page.evaluate('plainJson(appState)')
        pre_unit2['version'] = 12
        pre_unit2['decks'].pop('ap_psych:unit_2_part_1_cognition', None)
        unit2_upgraded, unit2_upgraded_errors = new_page(saved=pre_unit2)
        check('v12 profile receives Unit 2 Part 1 once',not unit2_upgraded_errors and unit2_upgraded.evaluate("""() => {
          const deck=appState.decks[COGNITION_PART1_DECK_ID];
          return deck?.preloaded===true && deck.cards.length===122 &&
            appState.units[deck.unitId]?.name==='Unit 2';
        }"""))
        unit2_upgraded.evaluate("delete appState.decks[COGNITION_PART1_DECK_ID];persistState({includeSession:false})")
        deleted_unit2 = unit2_upgraded.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')
        after_unit2_delete, after_unit2_delete_errors = new_page(saved=deleted_unit2)
        check('deleted Unit 2 Part 1 preload stays deleted after v13',not after_unit2_delete_errors and after_unit2_delete.evaluate('!appState.decks[COGNITION_PART1_DECK_ID]'))

        # Synthetic colliding card IDs in separate real decks must not merge evidence.
'''
b = replace_once(b, after_unit1, after_unit2, "unit2 browser migration")
browser.write_text(b, encoding="utf-8")

# Documentation.
readme = ROOT / "README.md"
r = readme.read_text(encoding="utf-8")
r = replace_once(
    r,
    "publishing implementation. Bundled study material now includes AP Psychology Unit 1\nBrain and a combined Sensation/States of Consciousness deck alongside Research Methods and the protected German fallback.",
    "publishing implementation. Bundled study material now includes AP Psychology Unit 1\nBrain and Sensation/States decks plus Unit 2 Part 1 (Perception, Cognition, Memory & Intelligence), alongside Research Methods and the protected German fallback.",
    "README bundled decks"
)
r = replace_once(r, "uses local schema\n`12` and cloud schema", "uses local schema\n`13` and cloud schema", "README schema")
readme.write_text(r, encoding="utf-8")

agents = ROOT / "AGENTS.md"
a = agents.read_text(encoding="utf-8")
a = replace_once(
    a,
    "  not automatically fetched or seeded. Keep Brain/Sensation exports synchronized\n  with their embedded arrays. See [deck maintenance](docs/DECKS.md).",
    "  not automatically fetched or seeded. Keep Brain/Sensation/Unit 2 Part 1 exports\n  synchronized with their embedded arrays. See [deck maintenance](docs/DECKS.md).",
    "AGENTS bundled exports"
)
agents.write_text(a, encoding="utf-8")

decks_doc = ROOT / "docs" / "DECKS.md"
d = decks_doc.read_text(encoding="utf-8")
row = "| Unit 1 — AP Psychology — Biological Bases of Behavior: Sensation & States of Consciousness | `ap_psych:unit_1_sensation` | AP Psychology / Unit 1 | 105 cards; pre-v11 seed plus pre-v12 content expansion; removable afterward |\n"
new_row = row + "| Unit 2 — Part 1 — AP Psychology — Perception, Cognition, Memory & Intelligence | `ap_psych:unit_2_part_1_cognition` | AP Psychology / Unit 2 | 122 cards; pre-v13 upgrade seed; removable afterward |\n"
d = replace_once(d, row, new_row, "DECKS starter row")
d = replace_once(
    d,
    "SENSATION_BASE_CARDS`, `CONSCIOUSNESS_CARDS`, and `SENSATION_CARDS` are what the app uses.",
    "SENSATION_BASE_CARDS`, `CONSCIOUSNESS_CARDS`, `SENSATION_CARDS`, and `COGNITION_PART1_CARDS` are what the app uses.",
    "DECKS arrays"
)
d = replace_once(
    d,
    "States of Consciousness IDs while preserving progress, custom names, and deletion.",
    "States of Consciousness IDs while preserving progress, custom names, and deletion. Unit 2 Part 1 is independently seeded only for pre-v13 profiles, so later deletion remains authoritative.",
    "DECKS migration note"
)
decks_doc.write_text(d, encoding="utf-8")

data_doc = ROOT / "docs" / "DATA_AND_MIGRATIONS.md"
dd = data_doc.read_text(encoding="utf-8")
dd = replace_once(dd, "| `APP_VERSION = 12` | Local profile schema/migration version |", "| `APP_VERSION = 13` | Local profile schema/migration version |", "DATA schema")
dd = replace_once(
    dd,
    "Fresh defaults include German, Research Methods, and the combined Sensation/States of\nConsciousness deck. Brain is separately",
    "Fresh defaults include German, Research Methods, the combined Sensation/States of\nConsciousness deck, and Unit 2 Part 1. Brain is separately",
    "DATA fresh defaults"
)
dd = replace_once(
    dd,
    "Research Methods, and AP Psychology/Unit 1\nfor both Brain and the combined deck.",
    "Research Methods, AP Psychology/Unit 1 for Brain and the combined deck, and AP Psychology/Unit 2 for Unit 2 Part 1.",
    "DATA placements"
)
dd = replace_once(
    dd,
    "card IDs when that deck still exists, preserving evidence, organization, custom titles,\nand an earlier deliberate deletion.",
    "card IDs when that deck still exists, preserving evidence, organization, custom titles,\nand an earlier deliberate deletion. Version 13 seeds Unit 2 Part 1 once for older profiles; deleting it afterward remains authoritative.",
    "DATA migration"
)
data_doc.write_text(dd, encoding="utf-8")
