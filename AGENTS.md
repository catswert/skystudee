# SkyStudee: instructions for future coding agents

Read this file first, then [architecture](docs/ARCHITECTURE.md), the relevant
feature guide, and [known limits](docs/KNOWN_LIMITS.md). Inspect the current
branch and `main` before editing. Conversation summaries and old downloaded HTML
are not authoritative source. Firebase work is already present in the source
underlying `firebase-bootstrap-v13-20260904`.

## Authoring and build boundary

- Edit **`src/skystudee.html`**: the readable, commented application source.
  It deliberately remains one HTML document with CSS and a classic script.
- Edit **`src/loader.html`** only for boot/loading changes.
- **`index.html`, `assets/mobile-build-*`, `build-manifest.json` are generated.**
  Never hand-edit/base64-patch individual chunks. Rebuild and commit the entire
  generated set with the source in one change.
- Public `decks/*.studydeck.json` files are exports/reference content. They are
  not automatically fetched or seeded. See [deck maintenance](docs/DECKS.md).
- This documentation pass added source/build tooling without a runtime refactor.
  Keep routine fixes narrow; do not replace the monolith or redesign the UI merely
  to implement a small requested change.

## Non-negotiable data and behavior invariants

1. **Preserve IDs and storage keys.** Renaming a class, unit, deck or card display
   text must not casually regenerate identities or erase evidence. Local state
   is at `study_cards_multideck_engine_v5` despite newer schema/build numbers.
2. **A study set is not a deck.** It stores real deck IDs/settings/runtime only.
   A grade resolves `deckForFact(fact)`; write memory at that deck's
   `facts[fact.id]`. Use `factKey`/`pairKey` for combined-session namespaces.
3. **Priority is not mastery.** Mastery derives from evidence; age/deadlines affect
   selection, not passive alpha/beta decay. Delayed flips must not be counted as
   slow/wrong answers. Temporary rests are measured in served cards.
4. **Directions are separate facts.** Positive sibling transfer is currently
   10%; it is not another direct review or proof of recall.
5. **Organization is user-owned.** Catalog detection suggests classes, never
   decides new-import units. Unit 0 is legitimate. Migrations must not recreate
   classes/units after deliberate moves/deletions. Container deletion preserves
   decks/progress; deleting an individual deck is a different confirmed action.
6. **Startup order matters.** Early load/seed/rename code runs before runtime and
   DOM initialization. Never call `persistState()` there. An earlier violation
   caused `Cannot access 'activeDeckId' before initialization`, inert buttons,
   and “Memory not loaded” only for legacy profiles.
7. **Keep Library as home**, even with one deck. Choosing a normal deck enters
   Memory. Preserve the separate phone layout and desktop layout, 104 ms input
   guard/520 ms flip, and old-answer/new-prompt handoff.
8. **No surprise cloud overwrite/publication.** Current Firebase is Google
   sign-in plus explicit first snapshot upload/load, not continuous sync. Local
   `persistState()` never uploads. Sign-out leaves local data in this build.
   Read [Firebase](docs/FIREBASE.md) before changing any of these semantics.
9. **Never commit private data/credentials.** Web Firebase config is intentional;
   service-account keys, OAuth client secrets, user backups, tokens, emails and
   private learning histories are not. Tests use synthetic profiles and mocked
   SDK calls. Do not inspect live user data just to test a code change.
10. **Document what exists, not what was proposed.** Shop, continuous synchronization,
    conflict merging and account-isolated local caches are not implemented.
    Keep proposed designs labeled as such.

## Required development loop

```sh
npm ci
python tools/build.py --check
npm run check
python -m unittest discover -s tests -p 'test_*.py'
# After editing source (choose a NEW deployment label):
python tools/build.py --version descriptive-release-label
python tools/build.py --check
python tests/browser_smoke.py
```

Browser prerequisites/commands are in [development](docs/DEVELOPMENT.md). For a
comment-only pass, also run `node tests/source_contracts.cjs --baseline <old.html>`
and compare the parsed HTML shape and representative screenshots. New functions
need useful JSDoc explaining ownership, mutation, side effects, failure paths and
call ordering, not a comment that repeats the function's name.

Before merging, fetch current `main` and reconcile other branches. Do not restore
an older full HTML blob over newer Firebase work. Check an actual old saved
profile, fresh/one-deck startup, taps/keys, combined-deck grading/undo, organization,
imports and small/wide viewports for relevant changes. Syntax checks alone do not
prove that an action button is bound or that startup succeeds. Report which
checks ran, and distinguish mocked tests from real Google login/rules tests.

Update the documentation when contracts change. Keep `docs/KNOWN_LIMITS.md`
current; finding a pre-existing issue in a documentation task is not permission
to silently change its behavior. Never use clearing site data as the default fix.
