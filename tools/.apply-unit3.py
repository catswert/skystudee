from __future__ import annotations
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def replace_one(text, old, new, label):
    assert text.count(old)==1, f"{label}: found {text.count(old)}"
    return text.replace(old,new,1)
rows=[line.split("|",1) for line in (ROOT/"tools/.unit3-rows.txt").read_text().splitlines() if line.strip()]
assert len(rows)==117
cards=[]
for term,definition in rows:
    semantic_id=re.sub(r"[^a-z0-9]+","_",term.encode("ascii","ignore").decode().lower()).strip("_")
    cards.append(dict(id=semantic_id,front=term,back=definition))
assert len({c["id"] for c in cards})==len(cards)
assert all(c["back"] and len(re.findall(r"[\w’'-]+",c["back"]))<=14 and not c["back"].endswith((".","!","?")) for c in cards)
name="Unit 3 — AP Psychology — Development and Learning"
doc=dict(format="StudyCardsDeck",version=1,deckId="ap_psych:unit_3_development_and_learning",name=name,classCatalogId="ap_psychology",className="AP Psychology",unitName="Unit 3",cards=cards)
(ROOT/"decks/ap-psychology-unit-3-development-and-learning.studydeck.json").write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n")
p=ROOT/"src/skystudee.html"
s=p.read_text()
s=replace_one(s,"const APP_VERSION = 13;","const APP_VERSION = 14;","schema version")
marker="    // CATALOG DATA: internal templates/aliases, not user instances. Unit names are intentionally absent from the global class catalog."
intro='''    // ==========================================================
    // PRELOADED UNIT 3 — DEVELOPMENT AND LEARNING
    // ==========================================================
    // Removable AP Psychology preload from Development and Learning (Development Edition).
    // Keep the public export and embedded source equal; stable IDs retain study evidence.
    const DEVELOPMENT_DECK_ID = "ap_psych:unit_3_development_and_learning";
    const DEVELOPMENT_DECK_NAME = "Unit 3 — AP Psychology — Development and Learning";
    const DEVELOPMENT_CARDS = '''+json.dumps(cards,separators=(",",":"),ensure_ascii=False)+''';

'''
s=replace_one(s,marker,intro+marker,"constants")
s=replace_one(s,'''        } else if (seedBundled && deck.id === COGNITION_PART1_DECK_ID && !deck.classId) {
          deck.classId = findOrCreateCatalogClass(target, "ap_psychology")?.id || null;
        } else if (suggestUnclassified && !deck.classId) {''','''        } else if (seedBundled && deck.id === COGNITION_PART1_DECK_ID && !deck.classId) {
          deck.classId = findOrCreateCatalogClass(target, "ap_psychology")?.id || null;
        } else if (seedBundled && deck.id === DEVELOPMENT_DECK_ID && !deck.classId) {
          deck.classId = findOrCreateCatalogClass(target, "ap_psychology")?.id || null;
        } else if (suggestUnclassified && !deck.classId) {''',"class placement")
s=replace_one(s,'''        } else if (seedBundled && deck.id === COGNITION_PART1_DECK_ID) {
          const psych = findClassByCatalog(target, "ap_psychology");
          if (!deck.unitId && psych && deck.classId === psych.id) deck.unitId = findOrCreateUnit(target, psych.id, "Unit 2")?.id || null;
        }

        if (!Number.isFinite(Number(deck.order))) deck.order = 0;''','''        } else if (seedBundled && deck.id === COGNITION_PART1_DECK_ID) {
          const psych = findClassByCatalog(target, "ap_psychology");
          if (!deck.unitId && psych && deck.classId === psych.id) deck.unitId = findOrCreateUnit(target, psych.id, "Unit 2")?.id || null;
        } else if (seedBundled && deck.id === DEVELOPMENT_DECK_ID) {
          const psych = findClassByCatalog(target, "ap_psychology");
          if (!deck.unitId && psych && deck.classId === psych.id) deck.unitId = findOrCreateUnit(target, psych.id, "Unit 3")?.id || null;
        }

        if (!Number.isFinite(Number(deck.order))) deck.order = 0;''',"unit placement")
s=replace_one(s,"Create a fresh local profile with German, Research Methods, Unit 1, and Unit 2 Part 1,","Create a fresh local profile with German, Research Methods, Units 1, 2 Part 1, and 3,","fresh doc")
s=replace_one(s,'''      cognitionPart1.settings.mode = "memory";

      const state = {''','''      cognitionPart1.settings.mode = "memory";
      const development = createDeckRecord({
        id: DEVELOPMENT_DECK_ID,
        name: DEVELOPMENT_DECK_NAME,
        cards: DEVELOPMENT_CARDS,
        preloaded: true
      });
      development.settings.mode = "memory";

      const state = {''',"fresh record")
s=replace_one(s,'''          [SENSATION_DECK_ID]: sensation,
          [COGNITION_PART1_DECK_ID]: cognitionPart1''','''          [SENSATION_DECK_ID]: sensation,
          [COGNITION_PART1_DECK_ID]: cognitionPart1,
          [DEVELOPMENT_DECK_ID]: development''',"fresh map")
function='''    /**
     * Add the removable Unit 3 Development and Learning preload exactly once to older
     * saved profiles. Version 14+ deletion remains intentional, and existing IDs/evidence,
     * customized organization, and existing decks are never overwritten.
     */
    function seedDevelopmentDeckForUpgrade(target, savedVersion) {
      const version = Number(savedVersion || 0);
      if (version >= 14 || target.decks[DEVELOPMENT_DECK_ID]) return;
      const psych = findOrCreateCatalogClass(target, "ap_psychology");
      const unit = psych ? findOrCreateUnit(target, psych.id, "Unit 3") : null;
      const siblings = unit
        ? Object.fromEntries(Object.entries(target.decks || {}).filter(([, deck]) => deck.unitId === unit.id))
        : {};
      const deck = createDeckRecord({
        id: DEVELOPMENT_DECK_ID, name: DEVELOPMENT_DECK_NAME,
        cards: DEVELOPMENT_CARDS, preloaded: true,
        classId: psych?.id || null, unitId: unit?.id || null,
        order: nextOrder(siblings)
      });
      deck.settings.mode = "memory";
      target.decks[DEVELOPMENT_DECK_ID] = deck;
    }

'''
s=replace_one(s,'''    /**
     * Expand an existing removable Sensation preload with States of Consciousness for schema 12.''',function+'''    /**
     * Expand an existing removable Sensation preload with States of Consciousness for schema 12.''',"versioned seed")
s=replace_one(s,'''      seedCognitionPart1DeckForUpgrade(target, saved.version);
      ensureOrganizationState(target, {''','''      seedCognitionPart1DeckForUpgrade(target, saved.version);
      seedDevelopmentDeckForUpgrade(target, saved.version);
      ensureOrganizationState(target, {''',"migration")
p.write_text(s)
p=ROOT/"tests/test_sensation_deck.py"
p.write_text(replace_one(p.read_text(),'self.assertIn("const APP_VERSION = 13;", source)','self.assertIn("const APP_VERSION = 14;", source)',"sensation schema"))
p=ROOT/"tests/test_cognition_part1_deck.py"
p.write_text(replace_one(p.read_text(),'self.assertIn("const APP_VERSION = 13;", source)','self.assertIn("const APP_VERSION = 14;", source)',"previous test"))
test='''from __future__ import annotations
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DevelopmentDeckTests(unittest.TestCase):
    def test_embedded_export_and_content(self):
        source=(ROOT/"src/skystudee.html").read_text()
        export=json.loads((ROOT/"decks/ap-psychology-unit-3-development-and-learning.studydeck.json").read_text())
        embedded=re.search(r"const DEVELOPMENT_CARDS = (\\[.*?\\]);\\n",source,re.S)
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
        self.assertTrue(all(len(re.findall(r"[\\w’'-]+",c["back"]))<=14 for c in cards))
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
'''
(ROOT/"tests/test_development_deck.py").write_text(test)
p=ROOT/"tests/browser_smoke.py"; b=p.read_text()
b=replace_one(b,"page.evaluate('!firebaseAuthReady && Object.keys(appState.decks).length===5')","page.evaluate('!firebaseAuthReady && Object.keys(appState.decks).length===6')","browser count")
target='''        saved = page.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')'''
addition='''        check('Unit 3 Development deck preloaded in correct class/unit', page.evaluate("""() => {
          const deck=appState.decks[DEVELOPMENT_DECK_ID];
          return deck?.preloaded===true && deck.cards.length===117 &&
            appState.classes[deck.classId]?.catalogId==='ap_psychology' &&
            appState.units[deck.unitId]?.name==='Unit 3';
        }"""))
'''
b=replace_one(b,target,addition+target,"browser fresh unit3")
anchor='''        # Synthetic colliding card IDs in separate real decks must not merge evidence.'''
migr='''        pre_unit3 = page.evaluate('plainJson(appState)')
        pre_unit3['version'] = 13
        pre_unit3['decks'].pop('ap_psych:unit_3_development_and_learning', None)
        unit3_upgraded, unit3_errors = new_page(saved=pre_unit3)
        check('v13 profile receives Unit 3 without losing Unit 2', not unit3_errors and unit3_upgraded.evaluate("""() => {
          return appState.decks[DEVELOPMENT_DECK_ID]?.cards.length===117 &&
            !!appState.decks[COGNITION_PART1_DECK_ID];
        }"""))
        unit3_upgraded.evaluate("delete appState.decks[DEVELOPMENT_DECK_ID];persistState({includeSession:false})")
        deleted_unit3 = unit3_upgraded.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')
        deleted_unit3_page, unit3_delete_errors = new_page(saved=deleted_unit3)
        check('deleted Unit 3 not silently restored at schema 14', not unit3_delete_errors and deleted_unit3_page.evaluate('!appState.decks[DEVELOPMENT_DECK_ID]'))

'''
b=replace_one(b,anchor,migr+anchor,"browser Unit3 migration");p.write_text(b)
p=ROOT/"README.md"
r=p.read_text()
r=replace_one(r,"Unit 2 Part 1 (Perception, Cognition, Memory & Intelligence), alongside","Unit 2 Part 1 (Perception, Cognition, Memory & Intelligence), and Unit 3 (Development and Learning), alongside","README deck")
r=replace_one(r,"local schema\n`13`","local schema\n`14`","README schema")
p.write_text(r)
p=ROOT/"AGENTS.md";a=p.read_text()
a=replace_one(a,"Brain/Sensation/Unit 2 Part 1 exports","Brain/Sensation/Unit 2 Part 1/Unit 3 exports","AGENTS")
p.write_text(a)
p=ROOT/"docs/DECKS.md";d=p.read_text()
d=replace_one(d,"## Starter decks: four different lifecycle policies","## Starter decks: bundled lifecycle policies","DECKS heading")
row='| Unit 2 — Part 1 — AP Psychology — Perception, Cognition, Memory & Intelligence | `ap_psych:unit_2_part_1_cognition` | AP Psychology / Unit 2 | 122 cards; pre-v13 upgrade seed; removable afterward |'
d=replace_one(d,row,row+'\n| Unit 3 — AP Psychology — Development and Learning | `ap_psych:unit_3_development_and_learning` | AP Psychology / Unit 3 | 117 cards; pre-v14 upgrade seed; removable afterward |',"deck table")
d=replace_one(d,"`COGNITION_PART1_CARDS` are what the app uses","`COGNITION_PART1_CARDS` and `DEVELOPMENT_CARDS` are what the app uses","array docs")
d=replace_one(d,"so later deletion remains authoritative.","so later deletion remains authoritative. Unit 3 is independently seeded only for pre-v14 profiles; later deletion remains authoritative.","migration docs")
p.write_text(d)
p=ROOT/"docs/DATA_AND_MIGRATIONS.md";d=p.read_text()
d=replace_one(d,"`APP_VERSION = 13`","`APP_VERSION = 14`","DATA schema")
d=replace_one(d,"and Unit 2 Part 1. Brain","Unit 2 Part 1, and Unit 3. Brain","DATA defaults")
d=replace_one(d,"for Unit 2 Part 1. Units","for Unit 2 Part 1, and AP Psychology/Unit 3 for Development and Learning. Units","DATA placement")
d=replace_one(d,"deleting it afterward remains authoritative.","deleting it afterward remains authoritative. Version 14 adds Unit 3 once to older profiles, while preserving subsequent deletions.","DATA migration")
p.write_text(d)
print("Generated",len(cards),"Unit 3 cards and patched source/tests/docs")
