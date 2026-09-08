# Development, validation and deployment

## Get the right baseline

Fetch branches and current `main`; inspect recent diffs before editing. At the
documentation audit, Firebase bootstrap was already merged into `main` and the
only existing branch was `main`. This fact must be rechecked for future work.
Never replace current source with an older HTML attached to a conversation.

For a legacy branch without `src/`, recover its exact deployed document:

```sh
python tools/recover_source.py --root /path/to/old-checkout --output /tmp/old-skystudee.html
```

The output must not already exist. Recovery is read-only to the repository and
uses the loader's count, not a guessed count from an old conversation. Preserve
this baseline for a diff or comment-only semantic comparison.

## Run and build

Requirements: Python 3.10+ and Node 20+ for maintenance checks; no npm runtime
bundle is required by the app. The only Node dev dependency is pinned Acorn for
JS parsing/contract checks. Python browser tests require Playwright and Chromium.

```sh
npm ci
python tools/build.py --check
npm run check
python -m unittest discover -s tests -p 'test_*.py'
python -m http.server 8080
```

Open `/` to test the generated loader, or `/src/skystudee.html` for direct authoring.
Use a disposable browser profile for development; test app paths on the same
origin can share localStorage. Don't accidentally replace real study data or
upload synthetic data to the owner's cloud account.

After changing `src/skystudee.html` or `src/loader.html`:

```sh
python tools/build.py --version descriptive-unique-release
python tools/build.py --check
```

The builder creates one gzip stream with empty filename/fixed mtime, base64-encodes
it and splits at 9,792 ASCII characters. It regenerates `index.html` and records
source, loader-template, loader and ordered part hashes in `build-manifest.json`.
A comment-only build does **not** change `APP_VERSION` or `CLOUD_SCHEMA_VERSION`.

`--check` reconstructs the stored chunks and compares them byte-for-byte to source,
verifies all hashes/lengths, checks exact loader template/version/count and rejects
missing/extra generated parts. It does not recompress for comparison: zlib
versions can emit different valid compressed bytes. Fixed headers reduce irrelevant
diffs but do not promise universal cross-platform compressor byte identity.

## Comments-only validation

```sh
node tests/source_contracts.cjs --baseline /tmp/old-skystudee.html
```

The parser compares executable ASTs after removing source-location/raw-literal
metadata. This preserves actual string/template values and catches accidental
changes to the copied AI prompt or Firebase config. Styles are also compared
without comments. Named top-level functions require adjacent JSDoc, static DOM
IDs must be unique and `getElementById` references must resolve.

For the documentation pass, also compare parsed HTML shape ignoring comments and
whitespace-only separators, and render original/annotated versions with identical
synthetic state, seeded randomness and frozen Date. A pixel comparison is useful
for detecting a comment inserted where it changes CSS/markup rather than merely
assuming comments can never affect behavior.

## Browser smoke tests

```sh
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python tests/browser_smoke.py
# Optional old-source comparison:
python tests/browser_smoke.py --baseline /tmp/old-skystudee.html
```

Set `SKYSTUDEE_CHROMIUM` to a locally installed Chromium executable when needed.
Screenshots/test results go to `test-results/` (ignored by Git). Tests use synthetic
profiles and a stubbed Firebase module API, not real sign-in or live user data.
They exercise Library startup, old Brain rename, multi-deck ownership/undo,
active-set deletion repair, modal shortcut blocking, organization/import gates,
UID-isolated storage, immutable generation publication, transactional revisions,
additive evidence merging, and failed-write dirty retention. Mocks establish client
control flow, not production Firebase Auth, quotas, or deployed Security Rules.

For a release changing UI or runtime, add focused checks beyond this smoke suite:
short/large phones, landscape, 1440x900, ultrawide/5K2K; real taps versus keyboard;
all answer modes/directions; flip interruptions; zero/one/many facts; cold completion;
imports of 120+ cards; backup/load with old/custom/removed decks; class merge/delete;
set membership changes; unavailable/quota-limited storage; SDK/network failure.
Real iOS Safari/Google popup and emulator Security Rules checks are separate from
headless Chromium emulation.

## Release procedure

Commit editable source, relevant docs/tests, complete generated assets, manifest
and loader together. Do not commit only some chunks: the base64 stream cannot
survive mixed releases. Never check in live profile JSON, private screenshots,
credentials or temporary update payloads. Public starter deck files are allowed.

The permanent validation workflow is read-only: build integrity, structural and
browser tests. It does not rewrite source or auto-push generated changes. Check
its result on the exact candidate commit. Review concurrent branches/main, merge
without force-pushing over someone else's work, then verify Pages built that
commit and the live loader points at the intended manifest version/count.

A local pass, a pushed commit, and a deployed Pages build are different evidence.
State which one is confirmed. GitHub Actions commits made with its own token have
trigger restrictions; do not assume a self-writing temporary workflow proves
Pages republished afterward. Prefer a normal reviewed merge and verify the Pages
run. See GitHub's [workflow trigger documentation](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow).

The snapshot/annotation workflow used to establish these docs is temporary and
not part of routine development. Future agents now have actual source and a
reproducible checked build path, so they need not repeat staging-patch workflows.
