"""One-time, assertion-guarded comment pass; no application statements are changed."""
from pathlib import Path
import re, textwrap, hashlib

# Every entry was checked against the deployed firebase-bootstrap-v13 source.
# This mapping is used only to insert comments, not to generate runtime code.
NOTES = "\n".join(p.read_text(encoding="utf-8").strip() for p in sorted(Path(".maintenance").glob("comments-*.tsv")))


def annotate(source: str) -> str:
    mapping={}
    for line in NOTES.strip().splitlines():
        name, note=line.split('|',1)
        assert name not in mapping, name
        mapping[name]=note
    definitions=re.findall(r'^    (?:async )?function (\w+)\(',source,re.M)
    assert set(definitions)==set(mapping), (set(definitions)-set(mapping),set(mapping)-set(definitions))
    def doc(match):
        name=match.group(1)
        body='\n'.join('     * '+line for line in textwrap.wrap(mapping[name],width=94,break_long_words=False,break_on_hyphens=False))
        return f'    /**\n{body}\n     */\n'+match.group(0)
    source=re.sub(r'^    (?:async )?function (\w+)\([^\n]*',doc,source,flags=re.M)
    def before(anchor,note,kind='js'):
        nonlocal source
        assert source.count(anchor)>=1,anchor
        if kind=='html': comment='  <!-- '+note+' -->\n'
        elif kind=='css': comment='    /* '+note+' */\n'
        else: comment='    // '+note+'\n'
        source=source.replace(anchor,comment+anchor,1)
    before('  <style id="instrumentRedesign">',
           'MAINTENANCE: src/skystudee.html is the editable source. Read AGENTS.md and docs/ARCHITECTURE.md before changing storage, study sets, or Firebase. Rebuild with tools/build.py; never edit base64 assets directly.', 'html')
    css={
        '    :root {':'THEME / SIZING: one stylesheet owns desktop defaults and later phone overrides. Keep specificity/order deliberate; do not restore the deleted legacy theme.',
        '    .hidden, [hidden]':'VISIBILITY CONTRACT: JS toggles hidden/show and view classes. Retained hidden compatibility nodes must not be removed without auditing every DOM reference.',
        '    .topbar {':'SHELL / NAVIGATION: desktop columns become a compact phone header and fixed bottom navigation in the phone query below.',
        '    .memory-chip {':'LOCAL SAVE INDICATOR: separate from Firebase identity/cloud snapshot state. Do not relabel this chip Synced.',
        '    .account-btn {':'ACCOUNT: these controls describe Google identity and manual snapshots only; no live synchronization animation should be inferred.',
        '    .cloud-panel {':'CLOUD PANEL: explicit user transfer actions stay reachable independently of card controls.',
        '    .page-view, #studyShell {':'PAGE VISIBILITY: Library-first startup uses showDecksView after initializing a resumable study context.',
        '    .study-toolbar {':'STUDY SETTINGS: source-deck settings or study-set settings are selected by activeSettings; phone secondary controls move to a sheet.',
        '    .goal-card {':'DAILY GOAL: informational status only, hidden in combined sessions. Do not introduce a completion gate here.',
        '    .card-stage {':'CARD GEOMETRY: stage owns viewport height; rotating card owns the hard border. Its two faces hide their backfaces.',
        '    .card-text {':'CONTENT FIT: text stays complete. Phone length tiers and measured shrinking are applied by updateCardTextFits; desktop sizing must stay unchanged.',
        '    .typed-area {':'TYPED RECALL: normalized prefix suggestions retain a randomized order, not an alphabetical or model-ranked order.',
        '    .actions {':'SELF GRADE: visible button handlers and arrow keys share functions. Keep semantic symbols separate from grey keyboard hints; X/Enter are not self-grade shortcuts.',
        '    .summary {':'COLD TEST SUMMARY: finite-queue result view; adaptive modes continue indefinitely.',
        '    .stats-view, .decks-view {':'SECONDARY PAGES: knowledge/lifetime are real-deck statistics even when session counts describe a multi-deck set.',
        '    .stats-table-wrap {':'TABLES: preserve desktop semantics; phone rules restyle rows to avoid an unreadable wide table.',
        '    .library-filters {':'ORGANIZATION: family/class filters only display classes with content; separate dialogs expose unused catalog options and custom classes.',
        '    .class-group {':'LIBRARY TREE: class/unit/deck wrappers own presentation, not copied study records. Changing indentation must not change ownership.',
        '    .import-organization {':'IMPORT GATE: classes can be suggested; units must be explicitly selected/typed. Inputs must remain outside the card-preview scrolling body.',
        '    .study-set-launch {':'STUDY SET PICKER: a selection of real deck IDs, not a synthetic deck. Footer remains outside the bounded tree scroll area.',
        '    .overlay {':'DIALOG LAYER: bounded viewport layout plus independent scrolling prevents footer actions being pushed below long imports.',
        '    .import-preview-list {':'LONG IMPORTS: show all accepted rows with scrolling and sticky labels; never truncate the actual preview to a fixed card count.',
        '    @media (max-height: 820px)':'SHORT DESKTOP WINDOWS: adapt vertical room without triggering phone information architecture.',
        '    @media (max-width: 1100px)':'NARROW LAYOUT: ordinary desktop header wrapping is separate from the phone-only device-width query.',
        '    @media (max-width: 960px) and (max-device-width: 960px) {':'PHONE OVERRIDES: paired with isPhoneUI (viewport and screen <=960). This legacy device-width test can include small tablets; do not describe it as OS detection.',
    }
    for anchor,note in css.items(): before(anchor,note,'css')
    html={
        '  <main class="app">':'APPLICATION SHELL: local studying must initialize and remain usable even if Firebase cannot load.',
        '    <section id="studyShell"':'STUDY CONTEXT: a current fact always retains its source deck ID. Front/back DOM faces mean prompt/answer, not original storage-side identity.',
        '    <section id="statsView"':'STATISTICS: verify source-deck versus combined-session labels when adding metrics.',
        '    <section id="decksView"':'LIBRARY HOME: classes and units are user-owned organization records. New imports require a unit; bundled initial placements are migration-only.',
        '  <div id="accountOverlay"':'ACCOUNT DIALOG: current Firebase feature is explicit first upload/load. No automatic sync or Shop publication action exists.',
        '  <div id="onboardingOverlay"':'LOCAL ONBOARDING: preserve separately from Google sign-in; a missing name can indicate unavailable/missing local storage.',
        '  <div id="importPreviewOverlay"':'IMPORT PREVIEW: render content safely, validate class/unit, and keep footer reachable for long files.',
        '  <div id="studySetOverlay"':'STUDY SET SELECTION: pending checkboxes can be cancelled without editing the active selection or evidence.',
        '  <div id="organizationOverlay"':'ORGANIZATION MODAL: create/edit/merge/move modes share this form. Update both openOrganization and saveOrganization when adding modes.',
        '<script>':'RUNTIME ORDER: constants/migration -> state -> DOM refs -> function/event wiring -> STARTUP -> async Firebase. Function declarations may be hoisted, but let/const state is not initialized early.',
    }
    for anchor,note in html.items():
        if anchor not in source:
            # Older section elements use a div, preserving the exact deployed markup.
            anchor=anchor.replace('<section','<div')
        before(anchor,note,'html')
    blocks={
        '    const BUILTIN_DECK_ID =':'BUNDLED GERMAN: forced fallback. Content edits require stable card IDs; new imports with this ID may only create a copy.',
        '    const PSYCH_DECK_ID =':'RESEARCH METHODS: seeded for fresh/pre-v6 profiles. Keep its Unit 0 identity separate from the Brain Unit 1 deck.',
        '    const BRAIN_CARDS =':'BRAIN CONTENT: this embedded array is what startup seeds. decks/biological-bases-brain.studydeck.json is a public export/reference, not a runtime fetch; update both deliberately.',
        '    const SUBJECT_FAMILIES =':'CATALOG DATA: internal templates/aliases, not user instances. Unit names are intentionally absent from the global class catalog.',
        '    const APP_VERSION =':'VERSION BOUNDARIES: APP_VERSION is local schema, CLOUD_SCHEMA_VERSION is snapshot shape, and build-manifest.version is deployment identity. A comment-only release changes only the last.',
        '    const FIREBASE_CONFIG =':'PUBLIC WEB CONFIG only. Never add service-account/private/OAuth-secret credentials. Actual database access is enforced by Firebase Auth and externally published Security Rules.',
        '    let storageAvailable =':'RUNTIME STATE: local profile and Firebase identity are currently separate. Signing out does not clear local decks; continuous synchronization is not implemented.',
        '    let appState = loadAppState();':'EARLY INITIALIZATION: called before activeDeckId, session and DOM refs exist. Do not call persistState here; the old Brain-name migration previously crashed legacy browsers that way.',
        '    const CARD_FLIP_MS =':'TIMING CONTRACT: 520ms visual rotation, 104ms input guard. Tokens invalidate stale timers/rAF callbacks; rest scheduling uses servedCount, not these wall-clock milliseconds.',
        '    const AI_DECK_CREATION_PROMPT =':'LITERAL PROMPT CONTENT: do not insert JS comments inside this template string. Its strict JSON example has no comments, and the required closing sentence is part of the copied prompt.',
        '    const UNSORTED_CLASS_ID =':'CONTAINER DELETION fallback: deleting a class/unit must not delete its decks or learning histories. Individual deck deletion is a separate destructive operation.',
        '    accountBtn.addEventListener':'EVENT WIRING: buttons must invoke the same guarded actions as keyboard routes. Keep account/bootstrap transfers explicit; no grade handler calls Firestore.',
        '    subjectFamilyFilter.addEventListener':'ORGANIZATION EVENTS: changing presentation filters does not mutate ownership. Dialog saves/import confirmation are the mutation boundaries.',
        '    studySetBtn.addEventListener':'SET EVENTS: pending selection is separate from persisted membership. Cancel/close must not commit checkboxes.',
        '    wrongBtn.addEventListener':'ACTION BINDINGS: do not rely on desktop keyboard routes alone; mobile requires these direct click/tap handlers for all four controls.',
        '    resetMemoryBtn.addEventListener':'DESTRUCTIVE LOCAL RESET: intentionally requires two confirmations. It does not delete Firebase cloud snapshots or sign the user out.',
        '    document.addEventListener("keydown", event => {':'KEYBOARD ROUTER: preserve context/typing guards, arrows for grading/later/undo, Space for reveal/next and Enter for typed submission only. Known modal exclusions are limited; see docs/KNOWN_LIMITS.md before extending this handler.',
        '    ensureBuiltInDeck(appState);\n    for (const deck':'FINAL STARTUP: all runtime state/DOM refs now exist. Normalize -> resume/create runtime -> save -> render -> Library home -> onboarding -> Firebase. Preserve order for legacy profiles.',
        '    initFirebaseAuth();':'ASYNC NETWORK BOUNDARY: this runs after local UI startup; auth/cloud failures must not disable local study or trigger automatic upload/overwrite.',
    }
    for anchor,note in blocks.items(): before(anchor,note)
    # Correct obsolete comments without altering user-facing strings or logic.
    source=source.replace('// PRIORITY / SCHEDULING (ONLY ACTIVE DECK PARTICIPATES)', '// PRIORITY / SCHEDULING (SELECTED REAL DECK POOL)')
    source=source.replace('// Hard no-repeat, including reverse direction of same card.', '// Suppress the most recent real card, including its reverse direction;\n      // weightedRandomFact has an exhausted-pool fallback (see docs/KNOWN_LIMITS.md).')
    source=source.replace('// The answer can never flash because content changes only at 90 degrees.', '// The intended safe swap is edge-on. This is a timer-based handoff,\n      // not a measured transition-end assertion; test slow-frame interruptions.')
    return source

if __name__=='__main__':
    import sys
    original=Path(sys.argv[1]).read_text()
    annotated=annotate(original)
    target=Path(sys.argv[2]);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(annotated)
    print(f'Annotated {len(re.findall(r"^    (?:async )?function ",original,re.M))} functions; {len(annotated.encode())} bytes')
