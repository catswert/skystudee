# Firebase: implemented bootstrap, not continuous sync

Verified against the source from main commit
`93c20c86725d819f03c073213bf5b7a05f2cf64f`. Firebase was already in `main` at this
inspection; no separate Firebase branch was present. This guide describes code,
not the private Firebase Console's current configuration or deployed rules.

## Present and absent

Implemented: Google popup sign-in, Auth persistence request, account dialog,
cloud-status check, explicit **first** upload, and explicit load onto this device
with a local recovery copy. All of these coexist with local/offline studying.

Not implemented: realtime listeners (`onSnapshot`), background uploads from
`persistState`, two-device conflict reconciliation, periodic snapshots, refresh
of a completed cloud copy from later local reviews, UID-isolated local study
caches, explicit persistent Firestore offline cache, account deletion, public
Shop storage or publication. Do not label the current status “Synced.”

## SDK and identity boundary

`initFirebaseAuth()` runs after local startup, dynamically imports pinned
Firebase `12.18.0` app/auth modules from `www.gstatic.com`, then Firestore. Firestore
failure leaves Auth available; both failing leaves local study available. The
code calls `setPersistence(...browserLocalPersistence)` with a fallback warning.
`signInWithGoogle()` uses `GoogleAuthProvider` and `signInWithPopup` in response to
a user action. `onAuthStateChanged` starts a status check, not a library download.

The web configuration identifies project `skystudee` and is intentionally public.
It is not an Admin credential. Never add service-account JSON, private keys,
OAuth client secrets or unrelated paid API credentials. Firebase's own guidance
separates public project identification from authorization via rules/IAM, and
recommends appropriate API restrictions:
[Firebase API keys](https://firebase.google.com/docs/projects/api-keys).

The intended client rule is authenticated ownership under `/users/{uid}`. The
current client never needs permission to read another UID or list all users.
Validate actual rules separately, preferably in the emulator; the fact that code
constructs a UID path is not authorization. A repository read cannot verify Console
settings. Do not “fix” permission errors with public read/write rules.
[Rules conditions](https://firebase.google.com/docs/firestore/security/rules-conditions).

On GitHub Pages, authorized hostname is `catswert.github.io`, not the URL path.
Popup cancellation, blockers, unauthorized-domain and network errors have specific
UI messages. Tests here stub the SDK rather than prove a real login or rules.
Changing to redirect sign-in requires new cross-browser testing and the official
[redirect guidance](https://firebase.google.com/docs/auth/web/redirect-best-practices).

## Cloud format v1

```text
/users/{uid}
  cloudSchemaVersion: 1
  snapshotComplete: true
  appVersion: <local schema>
  deckCount
  sourceLastSavedAt
  updatedAt: serverTimestamp

/users/{uid}/state/core
  cloudSchemaVersion: 1
  state: <appState without decks>
  updatedAt: serverTimestamp

/users/{uid}/decks/{encodedDeckId}
  cloudSchemaVersion: 1
  deck: <complete realDeck JSON>
```

`cloudDeckDocId` is `d_` plus base64url of the UTF-8 deck ID (without padding).
The payload's original `deck.id` remains unchanged. Class/unit/settings/selection
metadata lives in core. Each full deck—including learning state, daily history
and resume snapshot—lives in one deck document. The chosen 900,000-byte JSON
preflight is conservative but is not the exact Firestore serialized size or a
chunking scheme. Large decks are rejected, not silently split.

## Status transitions and actions

`refreshFirebaseCloudStatus` reads only the root manifest. No root -> `empty`;
matching schema plus `snapshotComplete:true` -> `ready`; another root ->
`incomplete`; read/SDK failure -> `error`. `idle`/`checking` are transient.
The result is discarded if the signed-in UID changed during that read. Root
status alone does not validate the core or all decks.

`uploadLocalStateToCloud` is available only for **empty/incomplete**, never ready.
After confirmation it saves locally, snapshots core/decks and performs all size
checks before cloud changes. It then deletes any earlier bootstrap deck documents,
writes real decks sequentially, writes core, and writes the completed root marker
last. It updates UI status to ready. This does not keep later study changes synced.
Errors surface in the account panel; checking/retrying can reveal the incomplete
bootstrap again.

`loadCloudStateOntoDevice` is available only for ready and requires confirmation
and usable local storage. It saves current local data, reads root/core/decks,
checks basic shape/completeness/nonempty decks, normalizes using `mergeAppState`,
and writes a `{savedAt,state}` recovery snapshot to `PRE_CLOUD_RESTORE_KEY` before
replacing `STORAGE_KEY`. It marks Brain seeding handled then reloads into Library.
It replaces this browser, not merges devices. The recovery slot is a single prior
copy, not a versioned recovery UI.

`signOutGoogle` clears Auth identity but deliberately leaves local study data.
Someone using the same browser profile can still see those local decks. Existing
code should not be described as isolated per-account local storage.

## Concurrency and reliability limits

The first snapshot uses sequential documents, not a transaction, generation ID,
lease or compare-and-swap. A marker written last reduces incomplete-first-upload
risk, but does not make two simultaneous uploads/loads atomic. Two clients can
both observe empty, interleave deletion/writes, and conflict. The load path does
not assert every document's version/generation or exact deckCount agreement.
UI busy flags are per tab, not database locks. Preserve this code during a
comment-only task; fix it through a separately specified sync design and tests.

True synchronization will need account-isolated caches, explicit first-connection
choices, independent revisions/event IDs, conflict and deletion semantics,
idempotent review writes/undo, batching/size limits, listener teardown, and
migrations. Merely putting Firestore writes into `persistState()` would risk
whole-profile overwrite, duplicate evidence and cross-account exposure. Stable
local IDs help but are not themselves a conflict algorithm.

## Safe test matrix

Use synthetic profiles and mocked SDKs or a Firebase emulator, never live user
records for routine automated tests. Cover SDK unavailable, Auth success with
Firestore unavailable, popup cancellation, unauthenticated/other-UID denial,
empty/ready/incomplete/error statuses, size rejection before writes, failed deck
write without a new completion marker, root-last ordering, recovery-before-replace,
no automatic cloud write after grading, and sign-out leaving local state as
currently documented. Real authorized-domain/popup/mobile behavior and published
Security Rules still require a separate intentional integration test.
