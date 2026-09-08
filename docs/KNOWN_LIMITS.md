# Known limits and maintenance traps

These are implementation observations from the documentation audit, not changes
made in this release. They help future agents avoid repeating stronger claims
than the source supports. Treat the listed areas as regression-test targets.

## Account/cloud boundaries (high priority for future sync work)

- Current cloud feature is a first snapshot, not continuous synchronization.
  Completed-cloud state does not expose upload of later local changes.
- Local study data is one browser profile, not isolated per Firebase UID.
  Sign-out does not remove local decks, history or the recovery slot.
- Upload uses sequential delete/write operations and a last completion marker,
  not generation-isolated atomic publication or concurrent-client arbitration.
  Two tabs/devices can observe the same empty profile and conflict.
- Root `ready` checks only the manifest. Load performs limited shape checks, not
  exact deck-count/generation/schema validation for every document.
- One whole deck must fit under the JSON-size preflight. It has not been split
  into per-card/review documents, and JSON bytes are only an estimate of storage
  serialization overhead.
- The pre-cloud recovery slot is overwritten on later restores and has no
  purpose-built recovery UI. Local storage failure still needs careful recovery.
- This repository does not prove what rules, authorized domains, API restrictions
  or quotas are currently configured in the private Firebase Console.

## Study/context boundaries

- No-repeat suppression has an exhausted-pool fallback. A single real card has
  no alternative; `weightedRandomFact` can return the first fact when all weights
  are withheld. Do not promise an unconditional no-repeat property.
- `constrainedPairShuffle` has a 10,000-iteration bound, so extraordinarily large
  Cold Test pools need explicit handling/tests before claiming every fact fits.
- Cram still uses stored mastery. Its brief older description is not a precise
  claim that history never affects its weights; it omits time/deadline factors.
- Autocomplete-on currently marks typed grading as assisted even if no suggestion
  was selected. Session unique counts shown facts, not only attempts.
- Study-set start requests Memory, but resuming an unchanged set can restore its
  saved mode through the generic resume helper. Combined-session statistics also
  coexist with real-anchor-deck knowledge/lifetime statistics.
- Deck deletion/update/import while a set or snapshot is active deserves stale
  pool/queue tests. Normalizing membership does not alone prove all currentFact,
  cooldown and undo references remain valid after arbitrary edits.
- Undo restores snapshots, not inverse review events. It cannot safely merge
  concurrently changed evidence without a separate future design.

## Organization, import and interface edges

- Used-only Library filtering may hide a legacy deck with no recognized/valid
  classId. Such a record is not necessarily deleted; inspect preserved state.
- Empty class records are intentionally absent from the Library tree. Some empty
  management paths are reachable through selection dialogs rather than the tree;
  don't claim a comprehensive standalone class-manager view exists.
- Import is permissive rather than a strict schema validator. Stored-card
  normalization and import deduplication are not identical. Adding arbitrary
  metadata requires updating normalizers so it survives reload/undo/restore.
- Phone detection uses a legacy screen-width condition, not device OS. Small
  tablets may match; desktop emulation alone is not a real iPhone Safari test.
- Text fitting has a 12px minimum and bounded retries; extremely long text and
  accessibility zoom are not guaranteed to fit.
- Card swaps are timer-based. Test slow-frame/rAF interruptions before claiming
  content can never be exposed during transition.
- Global keyboard exclusions name only some overlays. Organization, study-set
  and account dialogs are not all explicitly covered by the global shortcut
  router; buttons and focused inputs can expose context conflicts.
- The loader catches fetch/decode failures, but runtime failures in the injected
  script are separate. “Memory not loaded” plus inert buttons can mean an early
  exception, not erased storage. Never recommend clearing storage first.

## Historical regressions to keep covered

The legacy Brain-name migration called `persistState` before runtime initialization,
throwing a temporal-dead-zone ReferenceError in old profiles while fresh browsers
worked. That was fixed; keep the migration delayed-save invariant. Later/Undo
once lacked click handlers despite keyboard support. Duplicate legacy CSS leaked
light-theme styles into the redesign. None of these should be reintroduced by
removing apparently redundant DOM references, adding a second global theme, or
only testing one happy-path browser.
