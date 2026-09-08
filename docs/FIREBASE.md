# Firebase account isolation and live synchronization

SkyStudee remains static and local-first. Google sign-in selects an account-specific
browser profile; after the user explicitly enables sync, Firestore automatically
reconciles durable study data between devices. Firebase/network failure never stops
local studying.

## Local account boundary

- `study_cards_multideck_engine_v5`: signed-out guest profile.
- `skystudee_account_state_v1:<uid>`: complete local profile for one Firebase UID.
- `skystudee_sync_meta_v2:<uid>`: accepted revision/generation, dirty bit and merge base.
- `skystudee_active_account_uid_v1`: startup account selector, later verified by Firebase Auth.
- `skystudee_sync_device_id_v1`: browser writer label, not authentication.
- `skystudee_pre_local_restore_v2:<uid-or-guest>`: one automatic recovery copy.

Sign-out saves the account cache, clears only the active selector, and reloads the
untouched guest profile. Account caches and Firestore data are not deleted.

## What synchronizes

Classes, units, decks/cards, deck settings, mastery/evidence, daily evidence/goals,
lifetime totals, Cold Test history, and study-set membership/settings synchronize.
The currently open page/deck/card, animation state, undo history, and resumable
session snapshots stay device-local.

## Cloud schema v2

`/users/{uid}` is a small transactional pointer with `activeGeneration` and integer
`revision`. A writer first creates a complete immutable generation under
`/users/{uid}/generations/{generationId}` with `state/core` and one document per
real deck. Only then does a Firestore transaction compare the expected root revision
and advance the pointer. Readers therefore see an old complete generation or a new
complete generation, never a mixed partial upload.

Revision conflicts cause the client to fetch the newest generation, three-way merge
against its last accepted base, and retry. Evidence/counter deltas add from the
common base; Cold Test histories union; stable-ID card/organization/settings changes
use three-way change detection. Concurrent delete-versus-edit keeps the edited
record. Unresolved concurrent edits to the same card text prefer remote; this is not
a collaborative deck editor.

Completed cloud schema v1 snapshots are recognized as `legacy`. `Merge & upgrade`
conservatively merges the old snapshot with the UID-local profile and publishes v2.
With no common base, evidence uses maxima rather than addition to avoid counting the
same old history twice.

## Security rules

`firestore.rules` contains owner-only access for `/users/{uid}` and every nested
subdocument. The repository cannot prove those rules are currently deployed. Publish
and test them separately with Firebase tooling; never solve permission errors by
making the database public. The web Firebase config in source is project identity,
not an Admin secret.

## Limits

Each whole deck/core document must stay under the conservative 900,000-byte JSON
preflight. Immutable generations are not garbage-collected yet, so a failed or
revision-conflicted publication can leave harmless unreferenced documents. If
browser quota prevents storing a full merge base, reconciliation falls back to the
more conservative no-base behavior. Automated tests mock transactions/listeners and
do not prove production Auth domains, quotas, or deployed Security Rules.
