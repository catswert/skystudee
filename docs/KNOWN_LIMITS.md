# Known limits and maintenance traps

These are implementation observations from the documentation audit, not changes
made in this release. They help future agents avoid repeating stronger claims
than the source supports. Treat the listed areas as regression-test targets.

## Account/cloud boundaries

- The repository cannot prove deployed Firestore rules, authorized domains, API restrictions, or quotas.
- Same-card text edits made concurrently are not collaborative editing; unresolved content conflicts prefer remote.
- Immutable generations are not garbage-collected yet; failed/conflicted publication can leave harmless orphan documents.
- Each whole deck/core document remains subject to the 900,000-byte JSON preflight.
- If browser quota prevents retaining a full common merge base, reconciliation uses conservative no-base behavior.
- The recovery slot is single-version per guest/account profile.

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
- Active deck deletion/update revalidates set membership, current fact, Cold queue, and undo history. New mutation paths must call the same reconciliation helper.
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
- The global keyboard router blocks every current modal. Any new overlay must be added to that guard.
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
