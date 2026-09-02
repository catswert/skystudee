from pathlib import Path
import json, re, gzip, base64, subprocess

source = Path('/tmp/skystudee.html')
s = source.read_text()
deck = json.loads(Path('decks/biological-bases-brain.studydeck.json').read_text())

if 'ap_psych:biological_bases_brain' not in s:
    cards_js = json.dumps(deck['cards'], ensure_ascii=False, separators=(',', ':'))
    lines = [
        '',
        '    // ==========================================================',
        '    // PRELOADED BIOLOGICAL BASES — THE BRAIN DECK',
        '    // ==========================================================',
        '    // Seeded once per browser profile. It is user-removable.',
        f'    const BRAIN_DECK_ID = {json.dumps(deck["deckId"])};',
        f'    const BRAIN_DECK_NAME = {json.dumps(deck["name"])};',
        f'    const BRAIN_CARDS = {cards_js};',
        '    const BRAIN_DECK_SEED_KEY = "skystudee_seed_biological_bases_brain_v1";',
        '',
        '    function seedBrainDeckOnce(target) {',
        '      if (!target || !target.decks) return false;',
        '      let alreadySeeded = false;',
        '      try { alreadySeeded = localStorage.getItem(BRAIN_DECK_SEED_KEY) === "1"; } catch (error) {}',
        '      if (alreadySeeded) return false;',
        '      if (!target.decks[BRAIN_DECK_ID]) {',
        '        const deck = createDeckRecord({',
        '          id: BRAIN_DECK_ID,',
        '          name: BRAIN_DECK_NAME,',
        '          cards: BRAIN_CARDS,',
        '          builtin: false',
        '        });',
        '        deck.settings.mode = "memory";',
        '        target.decks[BRAIN_DECK_ID] = deck;',
        '      }',
        '      try {',
        '        localStorage.setItem(BRAIN_DECK_SEED_KEY, "1");',
        '        localStorage.setItem(STORAGE_KEY, JSON.stringify(target));',
        '      } catch (error) {}',
        '      return true;',
        '    }',
        ''
    ]
    block = '\n'.join(lines)
    marker = re.search(r'\n\s*const APP_VERSION\s*=\s*\d+\s*;', s)
    if not marker:
        raise SystemExit('Could not find APP_VERSION insertion marker')
    s = s[:marker.start()] + '\n' + block + s[marker.start():]

    old = '    let appState = loadAppState();'
    if s.count(old) != 1:
        raise SystemExit(f'Expected one appState initializer, found {s.count(old)}')
    s = s.replace(old, old + '\n    seedBrainDeckOnce(appState);', 1)

source.write_text(s)

start = s.index('<script>') + 8
end = s.rindex('</script>')
Path('/tmp/skystudee.js').write_text(s[start:end])
subprocess.run(['node', '--check', '/tmp/skystudee.js'], check=True)

html = source.read_bytes()
encoded = base64.b64encode(gzip.compress(html, compresslevel=9, mtime=0)).decode()
parts = [encoded[i:i+9792] for i in range(0, len(encoded), 9792)]
assets = Path('assets')
for old in assets.glob('mobile-build-*'):
    old.unlink()
for i, part in enumerate(parts, 1):
    (assets / f'mobile-build-{i:02d}').write_text(part)

loader_path = Path('index.html')
loader = loader_path.read_text()
loader = re.sub(r"const version='[^']+';", "const version='brain-deck-20260901';", loader)
loader = re.sub(r'Array\.from\(\{length:\d+\}', f'Array.from({{length:{len(parts)}}}', loader)
loader_path.write_text(loader)
print(f'Integrated {len(deck["cards"])} cards into {len(parts)} build chunks.')
