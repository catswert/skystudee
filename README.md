# SkyStudee

A local-first flashcard study app, statically hosted on
[GitHub Pages](https://catswert.github.io/skystudee/). It offers adaptive Memory and
Cram modes, finite Cold Tests, typed recall/autocomplete, class/unit organization,
combined-deck study sets, local backups, and a phone-specific interface.

**Cloud status:** Google sign-in selects a UID-isolated local profile. After the user
enables sync, revisioned immutable Firestore generations automatically reconcile durable
decks, organization, settings, and learning evidence between devices. Open-card/session
position remains device-local. See [Firebase behavior and limits](docs/FIREBASE.md).
A curated Deck Shop has been discussed but has no current tab, catalog, install, or
publishing implementation. Bundled study material now includes AP Psychology Unit 1
Brain and Sensation decks alongside Research Methods and the protected German fallback.

## Start here

| Goal | Read |
| --- | --- |
| Work on this repository as an agent | [AGENTS.md](AGENTS.md) |
| Understand the source and study engine | [Architecture](docs/ARCHITECTURE.md) |
| Change persisted fields/migrations | [Data and migrations](docs/DATA_AND_MIGRATIONS.md) |
| Maintain Auth/cloud snapshot code | [Firebase](docs/FIREBASE.md) |
| Add/update bundled or imported decks | [Decks and future Shop](docs/DECKS.md) |
| Run/build/test/deploy | [Development](docs/DEVELOPMENT.md) |
| Avoid inherited implementation traps | [Known limits](docs/KNOWN_LIMITS.md) |

## Repository map

```text
src/skystudee.html       editable app; function, CSS, HTML and event documentation
src/loader.html          editable boot template
tools/build.py          reproducible-header static packaging and read-only checks
tools/recover_source.py read-only recovery of a pre-source branch
index.html              generated Pages loader
assets/mobile-build-*   generated ordered base64 pieces of one gzip stream
build-manifest.json     source/loader/part integrity hashes and build identity
decks/                  public deck exports/reference files, not private backups
tests/                  structural, packaging and mocked-browser checks
docs/                   maintenance guides
```

Run locally using a throwaway browser profile (do not upload synthetic test data
to your real cloud account):

```sh
python tools/build.py --check
python -m http.server 8080
# Open http://localhost:8080/ to exercise the generated loader.
# Open http://localhost:8080/src/skystudee.html to inspect source directly.
```

The source document still contains everything needed for local study. Firebase
loads separately/asynchronously and can fail without disabling local studying.
Auth on a test origin requires Firebase's authorized-domain setup; ordinary local
study does not. Export a private backup before experiments on real study data.

## Documentation baseline

The source was originally recovered from `main` commit
`93c20c86725d819f03c073213bf5b7a05f2cf64f`, whose loader was
`firebase-bootstrap-v13-20260904`. The current implementation uses local schema
`11` and cloud schema `2`. Future changes should update these guides rather than
treating the original recovery snapshot as an eternal description.
