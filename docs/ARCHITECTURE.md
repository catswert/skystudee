# Architecture and execution map

This guide describes the inspected implementation, not an idealized sync system.
The canonical code is [`src/skystudee.html`](../src/skystudee.html). Search for the
function names below instead of relying on line numbers, which move with edits.
Every top-level named function has an adjacent maintenance comment.

## Layers and boundaries

The public site serves a tiny loader plus numbered static build pieces. The
pieces collectively encode **one** gzip stream. `index.html` fetches them in
parallel, concatenates in numeric order, base64-decodes, decompresses with
`DecompressionStream('gzip')`, then writes the full app document. The string
`mobile-build` is historical: these assets include **both** desktop and mobile UI.
They are not a separate mobile app, encrypted user data, or separately loadable
modules.

The full document contains a single themed stylesheet, static view/dialog DOM,
embedded public starter decks/catalog, and one classic JavaScript script. Its
module-like sections remain in that script; the documentation pass did not
split lexical scopes or move initialization. Firebase ESM modules are imported
asynchronously near the end. No app server, service worker, framework routing,
or runtime fetch of `decks/*.json` is currently involved.

## Startup: preserve the order

1. Constants, embedded data and hoisted helpers become available.
2. `loadAppState()` probes/loads/normalizes local data, or runs the old single-deck
   migration. `seedBrainDeckOnce()` can perform narrowly scoped direct storage
   writes; `ensureOrganizationState()` repairs organization.
3. The old canonical Brain display name is corrected **in memory only**. Runtime
   variables including `activeDeckId`, `studySetActive`, `mode`, `session`, and
   DOM references are not all initialized yet. Do not call the ordinary saver.
4. Runtime declarations, DOM bindings, functions and event handlers are installed.
5. Final STARTUP ensures memory, restores a recent session or prepares one,
   persists locally, renders and shows **Library**, even for a single deck.
   Onboarding overlays it only when the local profile name is missing.
6. `initFirebaseAuth()` starts after local initialization. Missing network or
   SDK failure must not stop local study. It does not upload a profile on login.

Library-first describes the visible home, not a lack of prepared study runtime.
`showStudyView()` reveals that context. `switchDeck()` explicitly chooses Memory
for an individual deck and only resumes that deck's Memory snapshot. A study-set
selection follows its separate start/resume path.

## Three different notions of state

**Durable local state** is `appState`: classes, units, real decks, learned evidence,
settings, daily evidence/goals, test history and resumable context. `persistState`
normalizes and serializes it to one stable key. It is not a Firestore adapter.

**Runtime** is `session` plus current/rendered fact, motion tokens, timers and UI
state. Resume snapshots convert Sets to arrays and deliberately omit recursive
undo history. Standard resume age is 8 hours; Cold Test resume age is 36 hours.
A stored fact that is no longer in the current pool prevents a valid resume.

**Cloud/account state** uses independent `firebase*` variables and explicit
snapshot functions. Signing in does not change local `userName`; signing out does
not erase local `appState`. See [Firebase](FIREBASE.md) before designing account
switching or continuous synchronization.

## Fact ownership: the most important boundary

A card expands into two directional views carrying its real `deckId`:

```text
card.id = "hippocampus"
fact.id = "hippocampus|front"             persistent key inside one deck
factKey = "deck-id::hippocampus|front"    combined-session lookup/queue key
pairKey = "deck-id::hippocampus"          shared cooldown for the two directions
```

`activeDeck()` is a real-deck **anchor**, not necessarily the owner of the current
card when a set is running. Use `deckForFact(fact)`, then `deck.facts[fact.id]`.
`studyDecks()` resolves the selected real decks, `activeFacts()` expands them, and
`getEligibleFacts()` filters the configured direction. `siblingFact()` retains
the owner ID when resolving the reverse direction.

The study-set object holds deck IDs, set settings and a session snapshot only.
It must never gain its own cards/mastery. Multiple decks may legitimately use the
same card ID. Pending picker checkboxes are a separate Set; cancelling the menu
must not mutate the running set. Selecting a normal deck exits combined mode.

## From user action to evidence

Self grade follows `gradeSelf -> saveUndoPoint -> recordSessionResult ->
recordPersistentResult -> recordDailyEvidence`, then advances. The durable update
always targets the real deck. `Later`/`skipCurrent` changes queue/runtime without
recording a grade; `restoreUndoPoint` restores the snapshotted owner deck and
session. Undo is a local snapshot operation, not a concurrency-safe inverse cloud
event. Its stack is capped at 80 and is not restored after reload.

Typed recall follows `submitTypedAnswer`, grades once, reveals feedback, then
`continueAfterTyped` advances without a second grade. Vocabulary is drawn from
the current fact's source deck/direction. Suggestions are prefix-filtered from
one shuffled order. Enter accepts the first visible suggestion when enabled,
otherwise submits input. `normalizeAnswer` lowercases/trims/collapses whitespace;
it does not remove accents or make arbitrary spelling mistakes equivalent.

All visible arrow actions have click handlers as well as keyboard routes.
Left/right grade; up defers; down undoes; Space reveals/continues. X and Enter are
not self-grade aliases. Enter retains onboarding, typed submission and other
context-specific roles.

## Mastery versus scheduling

The current mastery estimate is `100 * alpha / (alpha + beta)` with prior
`alpha=beta=2`. The 50% prior is uncertainty, not earned proficiency. Direct
correct/incorrect evidence adjusts alpha/beta with weights for mode and typed
assistance. A correct answer also adds 10% positive evidence to the sibling;
that does not increment its direct-attempt counter or review timestamp. Failure
has no corresponding sibling transfer in this build.

`knowledgeMetrics` uses 65% mean mastery and 35% twentieth percentile, so weak
facts matter. It is independent from normalized draw probabilities.

`displayPriority` calculates the positive weighting shown on screen.
`adaptivePriority` adds temporary cooldown/recent-pair suppression; the displayed
number is not the actual probability of the next draw. Both Cram and Memory use
stored mastery and session boosts. Memory additionally uses evidence age and the
**source deck's deadline**. Cram omits these time/deadline factors, but does not
ignore historical evidence altogether despite older brief UI copy.

Misses rest for 4–7 served-card steps before receiving elevated priority. Known
answers reduce the session miss boost; skips defer for three steps. No elapsed
reading/response time is used as evidence. Passive absence never decays stored
alpha/beta. The weighted selector has an exhaustion fallback, so a one-pair pool
cannot uphold an absolute no-repeat promise.

Memory's daily goal combines knowledge progress and direct sampling, keyed by
local date/direction/deadline. Status is informational: not/mostly/complete does
not block studying. The goal is hidden for combined sets rather than pretending
they are a real deck. Session `unique` counts **shown** facts; daily evidence
counts **answered** facts—do not silently swap these denominators.

Cold Test builds a finite namespaced queue. Once completed,
`finishColdTest()` shows combined totals but writes each real deck's subset to
that deck's own test history. A combined session does not create a merged deck
or pooled durable mastery.

## Organization and import boundaries

Global `SUBJECT_FAMILIES` and `CLASS_CATALOG` are recognition templates. User class
instances have stable IDs, a possibly null catalog association, explicit family
and order; units belong to exactly one class. Decks reference both. Family
assignment can override the catalog default. New units are never inferred from
course conventions or imported `unitName` hints.

`renderDeckManager` renders used classes/units/decks and bound actions;
`openOrganization`/`saveOrganization` share mode-specific form state. `Move` and
container merges change organization, not content/evidence identity. Container
delete uses Unsorted/Needs unit. Migrations are explicitly gated so deletes/moves
do not get undone on the next save.

`parseDeckFile` and `normalizeImportedDeck` sanitize the imported file;
`showImportPreview` shows all accepted rows in a bounded scrolling region.
`resolveImportOrganization` validates the explicit destination before import.
The buttons' disabled state is convenience, not the only validation boundary.
See [Decks](DECKS.md) for stable update/copy behavior and accepted formats.

## Presentation and motion invariants

There is one stylesheet: desktop defaults, narrow/short/large-screen adjustments,
then phone overrides. Phone detection currently uses both viewport and screen
width <=960; it is not OS detection and may include small tablets. Phone layout
uses a bottom navigation bar, compact header and Options sheet. Keep the desktop
layout unchanged when repairing phone-only problems.

The rotating element owns a square border. Its DOM front means the current
**prompt**, and back means **answer**, even when studying original back-to-front.
`renderCurrentFact` protects old text during handoff. The flip is 520 ms, but input
locks for 104 ms. Tokens cancel stale motion callbacks; rapid actions capture the
computed transform before reversing. The edge-on swap is timer-based, not a
measured `transitionend`, so slower-frame interruption tests remain important.

Mobile text fit first selects a length class then measures available height and
shrinks in bounded steps (minimum 12px). This is a best-effort fit, not a guarantee
for arbitrary paragraphs/accessibility zoom. Import/set scroll bodies keep footer
actions outside the scroll region. Hidden compatibility DOM nodes still have
references—do not remove them solely because they are currently invisible.

## Function map for feature changes

| Area | Start with |
| --- | --- |
| Startup/migration | `loadAppState`, `mergeAppState`, `ensureOrganizationState`, final STARTUP |
| Local save/restore | `persistState`, `serializeSessionData`, `restoreSessionSnapshot` |
| Durable grading | `recordPersistentResult`, `recordDailyEvidence`, `siblingFact` |
| Probability/recency | `displayPriority`, `adaptivePriority`, `weightedRandomFact` |
| Flip/text/typing | `renderCurrentFact`, `animateSameCardToSide`, `updateCardTextFits`, `submitTypedAnswer` |
| Combined study | `factKey`, `deckForFact`, `startStudySetFromPicker`, `finishColdTest` |
| Organization | `openOrganization`, `saveOrganization`, `mergeClasses`, `mergeUnits`, `renderDeckManager` |
| Import/export | `parseDeckFile`, `normalizeImportedDeck`, `updateExistingDeck`, `exportDeck` |
| Cloud | `initFirebaseAuth`, `refreshFirebaseCloudStatus`, `uploadLocalStateToCloud`, `loadCloudStateOntoDevice` |

Keep the exact source comments synchronized with changes to these contracts.
