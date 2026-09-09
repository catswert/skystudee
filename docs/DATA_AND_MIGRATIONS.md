# Durable data, identities and migrations

Source of truth: state/migration, persistence, evidence, organization, and Firebase
sections of [`src/skystudee.html`](../src/skystudee.html).

## Independent version numbers

| Value | Meaning |
| --- | --- |
| `APP_VERSION = 11` | Local profile schema/migration version |
| `CLOUD_SCHEMA_VERSION = 2` | Revisioned immutable-generation sync |
| `StudyCardsDeck.version = 1` | Interchange content format |
| `build-manifest.json.version` | Static deployment/cache identity |
| `FIREBASE_SDK_VERSION = "12.18.0"` | Pinned runtime dependency |

A documentation-only release changes only the build identity. Do not bump local
schema just to make a release number look newer; migrations compare those values.

## Storage keys

- `study_cards_multideck_engine_v5`: signed-out guest profile.
- `skystudee_account_state_v1:<uid>`: complete local profile for one Firebase UID.
- `skystudee_sync_meta_v2:<uid>`: accepted revision/generation, dirty bit and merge base.
- `skystudee_active_account_uid_v1`: startup account selector verified against Firebase Auth.
- `skystudee_sync_device_id_v1`: browser writer label, not authentication.
- `skystudee_pre_local_restore_v2:<uid-or-guest>`: one automatic local recovery copy.
- `study_cards_memory_engine_v4`: legacy guest migration source.
- `skystudee_seed_biological_bases_brain_v1[:uid]`: guest/account Brain seed marker.
- `skystudee_pre_cloud_restore_v1`: retained legacy schema-v1 recovery slot.

## Profile and record shapes

```text
appState
  version, userName, createdAt, lastSavedAt, activeDeckId
  classes[id] -> {id, catalogId|null, name, familyId, order}
  units[id]   -> {id, classId, name, order}
  decks[id]   -> realDeck
  studySet    -> {active, deckIds[], settings, sessionState|null}

realDeck
  id, name, builtin, preloaded, classId|null, unitId|null, order
  createdAt, updatedAt
  cards[] -> {id, front, back}
  settings -> {mode, direction, answerMode, autocomplete, coldShuffle, deadline}
  facts[cardId|direction] -> evidence
  lifetime, dailyEvidence, dailyGoals, coldTests[], sessionState|null

evidence
  alpha, beta, directCorrect, directWrong, transferredEvidence
  typedCorrect, typedWrong, selfCorrect, selfWrong, autocompleteCorrect
  lastReviewedAt|null, lastResult|null
```

`normalizeDeckRecord` reconstructs the fields it knows. Unknown new fields can be
lost on load, undo, import update or cloud load unless deliberately added to this
normalizer and other boundaries. `ensureDeckMemory` fills missing fields for both
current directions; it retains evidence for removed cards so a future stable-ID
return can reconnect it. Review timestamps are data, not identities.

New cards with no stable import ID can get a hash based on content. Editing that
content changes the generated ID, which makes the evidence look unrelated. Use
explicit semantic IDs in maintained decks. Reserved delimiters `|` and `::` serve
directional and pooled keys; do not introduce another encoding casually.

## One-time placement versus everyday repair

Fresh defaults include German, Research Methods, and Sensation. Brain is separately
seeded. Known startup placements are German/Needs unit, AP Psychology/Unit 0 for
Research Methods, and AP Psychology/Unit 1 for both Brain and Sensation. Units are
not otherwise a global course catalog.

Research Methods is added to older saves only for versions below 6. Sensation is added
once to profiles below version 11 and placed in AP Psychology / Unit 1; after that,
a user deletion remains authoritative. Organization seeding/suggestions are enabled
for the pre-7 organization migration; regular `ensureOrganizationState` calls just
repair/normalize references. Brain uses its separate account-scoped seed flag. A
unit/class removal in current schema must survive save, reload and backup/cloud
normalization. Do not turn `ensure*` into “always restore canonical placement.”

The old Brain title is renamed only when it is exactly the old canonical string.
It preserves the deck ID and does not override deliberate user names. The rename
must not call `persistState()` before `activeDeckId` and `session` exist. The
normal final-startup save writes it later.

## Resume/undo are not durable learning evidence

Serialized session state includes mode/start time, counters, `unique` array,
transient runtime weights, recent pairs, served count, typing state, Cold Test
queue/results, and `currentFactKey` plus the legacy unqualified ID. Undo history
is intentionally not serialized. Deserialization upgrades legacy keys using the
owning deck as namespace and rejects missing current keys or too-old snapshots.

`restoreSessionSnapshot` can mutate runtime before a later validation fails;
callers must build a fresh context after false. `clearSessionState` followed by a
normal include-session save would recreate a completed snapshot, hence the
`includeSession:false` path at Cold Test completion.

## Safe operation matrix

| Operation | Identity/evidence behavior |
| --- | --- |
| Rename/reorder class, unit, deck | Same IDs; no mastery change |
| Move deck | Same real deck; organization pointers/order change |
| Merge classes/units | Decks remain distinct; same-name destination units can combine |
| Delete unit | Decks preserved, unit pointer cleared -> Needs unit |
| Delete class | Decks preserved -> Unsorted / Needs unit |
| Delete real deck | Confirmed removal of that deck and its progress; German is protected |
| Update imported deck with same ID | Replace active card content, preserve matching-ID evidence |
| Import copy | New real-deck ID and independent evidence |
| Study set | No synthetic deck; grade original owners |
| Load backup/cloud | Explicit replacement after normalization, not evidence reconciliation |

Numeric order is explicit. Old equal values are normalized among peers before
swapping neighbors. Do not alphabetize after the user reorders.

## Migration checklist for a future schema change

Define the added fields and defaults; update constructors, normalizers and all
serialization boundaries. Add a version-gated pure-data migration. It must be
idempotent and safe before runtime/DOM setup. Keep original storage keys/IDs.
Test fresh data, a pre-feature profile, deliberate deletion/move, old session
keys, custom class family, and the old Brain title. Verify backup -> normalize ->
reload and cloud snapshot -> normalize -> reload without fabricated evidence.

Exported backups and local snapshots are private. Store only synthetic fixtures
in Git. A backup's outer format is `StudyCardsMultiDeckBackup` with `state`; the
pre-cloud recovery wrapper is not that interchange format. To recover deliberately,
inspect/export the wrapper's `state` using a safe local process—do not paste private
state into a public issue or assume the existing backup picker understands it.
