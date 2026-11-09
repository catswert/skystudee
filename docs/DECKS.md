# Deck content, catalog maintenance, and the future Shop

## Recommended interchange contract

A `.studydeck.json` file is strict JSON, not a slideshow and not a private backup:

```json
{
  "format": "StudyCardsDeck",
  "version": 1,
  "deckId": "example:biology_cells",
  "name": "Cell Structures",
  "classCatalogId": "biology",
  "className": "Biology",
  "unitName": "Unit 1",
  "cards": [
    {"id": "nucleus", "front": "Nucleus", "back": "Contains the cell's genetic material."}
  ]
}
```

The example illustrates structure, not replacement content for a user's notes.
`classCatalogId`, `className`, `unitName` are optional hints. The unit must still be
explicitly chosen/typed when importing a new deck. Do not infer course numbering.
Native generators should always emit `format`/`version` exactly as above, unique
semantic IDs, nonempty front/back strings and no comments/trailing commas/code
fences. The actual legacy importer is more permissive: object-with-cards or card
arrays, CSV/TSV (optional recognized header) and supported alias fields. It does
not strictly enforce every native-format marker/version; do not confuse the
recommended generator contract with complete schema enforcement.

Follow `parseDeckFile` -> `normalizeImportedDeck` -> `showImportPreview` ->
`resolveImportOrganization` -> `importNewDeck`/`updateExistingDeck`. Invalid and
duplicate rows are counted. The preview shows all accepted rows in a scrollable
region; footer controls remain accessible. Use the source code for exact accepted
column aliases rather than expanding them silently in generators.

The AI prompt is a literal string, `AI_DECK_CREATION_PROMPT`. Its ending is
`I will upload the topic soon, confirm your understanding`. Do not add documentation
comments inside the string or JSON example; that changes what the clipboard
button copies. A structural test compares template literals in comment-only work.

## Update versus copy

Preserve `deckId` and logical card IDs for updates. Name/unit are not identity.
`updateExistingDeck` retains matching fact evidence and the existing local deck
name. New cards get fresh memory; removed-card evidence remains stored. Generated
content-hash IDs are a fallback, not ideal for maintained revisions. Import as
Copy intentionally creates a new real-deck ID and independent progress.

`exportDeck` exports content, identity and optional organization hints plus an
export timestamp. It does not export mastery. `exportBackup` is different: it
contains private complete appState. Never publish a backup as educational content.

## Starter decks: bundled lifecycle policies

| Deck | ID | Initial placement | Behavior |
| --- | --- | --- | --- |
| AP Psychology Unit 0 — Research Methods | `ap_psych:unit_0_research_methods` | AP Psychology / Unit 0 | 76-card default; pre-v6 upgrade seed; removable afterward |
| Unit 1 — AP Psychology — Biological Bases of Behavior: The Brain | `ap_psych:biological_bases_brain` | AP Psychology / Unit 1 | 95 cards; browser one-time seed flag; removable afterward |
| Unit 1 — AP Psychology — Biological Bases of Behavior: Sensation & States of Consciousness | `ap_psych:unit_1_sensation` | AP Psychology / Unit 1 | 105 cards; pre-v11 seed plus pre-v12 content expansion; removable afterward |
| Unit 2 — Part 1 — AP Psychology — Perception, Cognition, Memory & Intelligence | `ap_psych:unit_2_part_1_cognition` | AP Psychology / Unit 2 | 122 cards; pre-v13 upgrade seed; removable afterward |
| Unit 3 — AP Psychology — Development and Learning | `ap_psych:unit_3_development_and_learning` | AP Psychology / Unit 3 | 117 cards; pre-v14 upgrade seed; removable afterward |
| Unit 4 — AP Psychology — Social Psychology | `ap_psych:unit_4_social_psychology` | AP Psychology / Unit 4 | 73 cards; pre-v15 upgrade seed; removable afterward |
| Unit 4 — AP Psychology — Motivation, Emotion & Personality | `ap_psych:unit_4_motivation_emotion_personality` | AP Psychology / Unit 4 | 81 cards; pre-v15 upgrade seed; removable afterward |

The German deck (`builtin:german-perfect:v1`, formerly a forced, undeletable fallback) was
retired in schema 15. `ensureLibraryDecks` strips that ID on every load, restore, save and cloud
merge, including copies re-sent by older clients, and an import using that ID becomes a copy.
There is no forced fallback deck any more: the last remaining deck cannot be deleted, and a
snapshot that would leave zero decks receives the fresh-profile starter decks.

Counts are the current bundled-content snapshot. Update this table when content
changes. Arrays `PSYCH_CARDS`, `BRAIN_CARDS`, `SENSATION_BASE_CARDS`,
`CONSCIOUSNESS_CARDS`, `SENSATION_CARDS`, `COGNITION_PART1_CARDS`, `DEVELOPMENT_CARDS`,
`SOCIAL_PSYCH_CARDS` and `PERSONALITY_CARDS` are what the app uses. The matching files in `decks/` are public
references/exports; editing only a JSON file does **not** update the starter deck
in the running app.

To add a new preload, make it removable (there is no forced-fallback concept any more).
Prefer explicit one-time seeding with a version/marker and tests for deletion,
existing-ID preservation, migrations and cloud restore. Define the class catalog
association and only a user-approved initial unit. Add content in the embedded
source and a corresponding public export when useful. Keep every identity stable,
ensure both-direction evidence initialization, and avoid rewriting custom local
organization each launch. Editing embedded content will not automatically update
already seeded removable deck copies; schema 12 therefore appends only missing
States of Consciousness IDs while preserving progress, custom names, and deletion. Unit 2 Part 1 is independently seeded only for pre-v13 profiles, so later deletion remains authoritative. Unit 3 is independently seeded only for pre-v14 profiles; later deletion remains authoritative. Both Unit 4 decks are seeded only for pre-v15 profiles (`seedUnit4DecksForUpgrade`); deleting either afterward is authoritative.

The Library and deck picker show a shortened name (`displayDeckName`) that drops `" — "`
segments repeating the deck's class or unit, so "Unit 4 — AP Psychology — Social Psychology"
under AP Psychology / Unit 4 shows as "Social Psychology". The stored name is unchanged.

## Class catalog updates

`SUBJECT_FAMILIES` contains 12 current internal families. `CLASS_CATALOG` contains
recognizable course templates and aliases; user class instances are separate.
Add a unique catalog ID, valid familyId, display name and intentional aliases.
`CLASS_CATALOG_BY_ID` is derived automatically. Recognition samples the deck name
and first 28 cards; score is a heuristic, not a certainty. Only classes with study
material appear in Library, not the whole baked catalog. Do not invent aliases
in documentation that are absent from the array. Test ambiguous AP/non-AP names.
The catalog is a maintained snapshot, not an automatically refreshed statewide
course database.

## Curated Deck Shop: agreed direction, NOT implemented

There is currently no Shop tab, `shop/` directory, public install function, shop
version metadata, or user publishing endpoint. Do not tell the owner that adding
a JSON file today makes it appear in a Shop.

The intended future design separates private Firebase profiles from a public,
owner-curated GitHub catalog, e.g. `shop/catalog.json` and `shop/decks/<shopId>.json`.
Users would preview and **copy** a selected public snapshot into their real
library, then choose organization. Only the owner/repository publisher could add
to the public list. User edits would never mutate the public copy.

Before implementing that contract, define stable public shopId + content version,
validation, deduplicated install/update behavior, and deliberate handling of local
edits/mastery. These fields are proposed, not current import guarantees. Keep shop
content-only JSON separate from private snapshots. Administrative access to a
user's Firestore data is not automatic consent to republish it: obtain permission,
check content rights, remove UID/email/real-name metadata unless explicitly
approved, remove all learning state/private notes, and review the actual card
text for personal details. Publish attribution only by deliberate choice.
