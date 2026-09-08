#!/usr/bin/env python3
"""Synthetic, offline browser checks; no real Google/Firestore user data.

The actual source is loaded with set_content so tests work in network-restricted
runtimes too. Storage is a deterministic in-memory shim. Firestore is stubbed at
its module API boundary. For cloud-load assertions ONLY, location.reload in a
copy of the function is replaced with a sentinel so the test can inspect writes.
This does not test real Auth/Rules or a browser navigating the production loader.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
KEY = "study_cards_multideck_engine_v5"
OUT = ROOT / "test-results"

STORAGE = r"""(initial => {
  window.__store = {...initial}; window.__storageWrites = [];
  Object.defineProperty(window, 'localStorage', {configurable:true, value:{
    getItem:k=>Object.prototype.hasOwnProperty.call(__store,k)?__store[k]:null,
    setItem:(k,v)=>{__storageWrites.push(k); __store[k]=String(v)},
    removeItem:k=>{delete __store[k]}, clear:()=>{window.__store={}}
  }});
  const NativeDate=Date, fixed=Date.parse('2026-09-07T18:00:00Z');
  window.Date=class extends NativeDate {
    constructor(...args){super(...(args.length?args:[fixed]));}
    static now(){return fixed;}
  };
  let seed=731;
  Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
})"""

CLOUD = r"""() => {
  window.__cloud={docs:{},writes:[], failWrite:null};
  firebaseUser={uid:'synthetic-uid',email:'test@example.invalid',displayName:'Synthetic'};
  firebaseApp={}; firebaseDb={}; firebaseAuth={}; firebaseAuthReady=true;
  firebaseAuthError=''; firebaseCloudBusy=false;
  const ref=(...args)=>({path:args.map(x=>typeof x==='string'?x:(x.path||'')).filter(Boolean).join('/')});
  const snap=r=>({ref:r,id:r.path.split('/').pop(),exists:()=>r.path in __cloud.docs,data:()=>__cloud.docs[r.path]});
  firebaseFirestoreApi={
    doc:ref, collection:ref, serverTimestamp:()=>new Date().toISOString(),
    getDoc:async r=>snap(r),
    getDocs:async r=>{const docs=Object.keys(__cloud.docs).filter(k=>k.startsWith(r.path+'/')&&k.slice(r.path.length+1).indexOf('/')<0).map(k=>snap({path:k}));return {docs,forEach:fn=>docs.forEach(fn)}},
    setDoc:async(r,data)=>{if(__cloud.failWrite&&r.path.includes(__cloud.failWrite))throw new Error('synthetic failure');__cloud.writes.push(['set',r.path]);__cloud.docs[r.path]=JSON.parse(JSON.stringify(data));},
    deleteDoc:async r=>{__cloud.writes.push(['delete',r.path]);delete __cloud.docs[r.path];}
  };
  firebaseAuthApi={signOut:async()=>{firebaseUser=null;firebaseCloudStatus='idle';renderFirebaseAccount();}};
  firebaseCloudStatus='empty'; renderFirebaseAccount();
}"""


def run(source: str, baseline: str | None) -> dict:
    """Exercise the actual app functions and bound UI against synthetic data."""
    OUT.mkdir(exist_ok=True)
    report = {"checks": [], "screenshots": [], "liveFirebaseTested": False}
    with sync_playwright() as pw:
        options = {"headless": True}
        if os.environ.get("SKYSTUDEE_CHROMIUM"):
            options["executable_path"] = os.environ["SKYSTUDEE_CHROMIUM"]
        browser = pw.chromium.launch(**options)
        contexts = []

        def new_page(html=source, saved=None, width=1440, height=900):
            context = browser.new_context(viewport={"width":width,"height":height},
                                          screen={"width":width,"height":height},
                                          is_mobile=width<961,has_touch=width<961,device_scale_factor=1)
            contexts.append(context)
            context.route("**/*", lambda route: route.abort())  # Never reach production Firebase.
            page = context.new_page(); errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())
            page.evaluate(STORAGE, {KEY:json.dumps(saved)} if saved else {})
            page.set_content(html, wait_until="load")
            page.wait_for_function("firebaseAuthInitPromise === null")
            if page.locator('#onboardingOverlay').is_visible():
                page.locator('#nameInput').fill('Synthetic')
                page.locator('#startBtn').click()
            return page, errors

        def check(label, condition):
            if not condition:
                raise AssertionError(label)
            report["checks"].append(label)
            print("PASS", label)

        page, errors = new_page()
        check('fresh Library home',page.locator('#decksView').is_visible())
        check('local studying available with SDK blocked',page.evaluate('!firebaseAuthReady && Object.keys(appState.decks).length===3'))
        saved = page.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')
        saved['decks']['ap_psych:biological_bases_brain']['name']='AP Psychology — Biological Bases of Behavior: The Brain'
        legacy, legacy_errors = new_page(saved=saved)
        check('legacy Brain migration loads without TDZ error',not legacy_errors and legacy.locator('#decksView').is_visible())
        check('legacy rename persisted',legacy.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY)).decks[BRAIN_DECK_ID].name===BRAIN_DECK_NAME'))

        # Synthetic colliding card IDs in separate real decks must not merge evidence.
        page.evaluate(r"""() => {
          for(const [id,name] of [['test:a','Synthetic A'],['test:b','Synthetic B']]){
            appState.decks[id]=createDeckRecord({id,name,cards:[{id:'shared',front:name,back:'Answer'}]});
          }
          appState.studySet={...defaultStudySetState(),active:true,deckIds:['test:a','test:b']};
          studySetActive=true;activeDeckId='test:a';appState.activeDeckId='test:a';
          startMode('memory');showStudyView();
          currentFact=getFactById('shared|front','test:b');renderCurrentFact({forceImmediate:true});
        }""")
        page.locator('#rightBtn').click(); page.wait_for_timeout(150)
        check('pooled grade writes real owner only',page.evaluate("appState.decks['test:b'].facts['shared|front'].directCorrect===1 && appState.decks['test:a'].facts['shared|front'].directCorrect===0"))
        page.locator('#undoBtn').click(); page.wait_for_timeout(150)
        check('pooled Undo restores source evidence',page.evaluate("appState.decks['test:b'].facts['shared|front'].directCorrect===0"))
        page.locator('#skipBtn').click(); page.wait_for_timeout(150)
        check('Later does not grade',page.evaluate("appState.decks['test:a'].lifetime.answers+appState.decks['test:b'].lifetime.answers===0"))
        page.keyboard.press('x');page.keyboard.press('Enter')
        check('X/Enter not global self-grade shortcuts',page.evaluate('session.answers===0'))

        page.evaluate("showDecksView();openOrganization('editClass',findClassByCatalog(appState,'ap_psychology').id)")
        page.select_option('#orgFamilySelect','science');page.locator('#saveOrganizationBtn').click()
        check('class family override survives normalization',page.evaluate("ensureOrganizationState(appState);findClassByCatalog(appState,'ap_psychology').familyId==='science'"))
        page.evaluate("deleteUnit(appState.decks[PSYCH_DECK_ID].unitId);ensureOrganizationState(appState)")
        check('deleted Unit 0 not recreated',page.evaluate('appState.decks[PSYCH_DECK_ID].unitId===null'))

        page.evaluate(r"""() => {
          const cards=Array.from({length:120},(_,i)=>({id:'term_'+i,front:'Term '+i,back:'Definition '+i}));
          showImportPreview(parseDeckFile(JSON.stringify({format:'StudyCardsDeck',version:1,deckId:'test:import',name:'Test',classCatalogId:'ap_psychology',cards}),{name:'test.studydeck.json'}));
        }""")
        check('new import requires explicit unit',page.locator('#confirmImportBtn').is_disabled() and page.locator('#importUnitInput').input_value()=='')
        page.locator('#importUnitInput').fill('User-defined unit')
        check('unit enables import',not page.locator('#confirmImportBtn').is_disabled())
        check('all 120 preview rows exist',page.locator('.import-preview-row').count()==120)
        page.evaluate('importPreviewOverlay.classList.remove("show")')

        page.evaluate(CLOUD)
        page.evaluate('refreshFirebaseCloudStatus()')
        check('missing cloud manifest => empty',page.evaluate("firebaseCloudStatus==='empty'"))
        page.evaluate('uploadLocalStateToCloud()')
        check('completed marker written last',page.evaluate("__cloud.writes.at(-1)[1]==='users/synthetic-uid' && __cloud.docs['users/synthetic-uid'].snapshotComplete===true"))
        prior = page.evaluate('__cloud.writes.length')
        page.evaluate('persistState()')
        check('local save does not auto-upload',page.evaluate('__cloud.writes.length')==prior)
        page.evaluate('uploadLocalStateToCloud()')
        check('ready cloud disallows another bootstrap upload',page.evaluate('__cloud.writes.length')==prior)
        # Execute a function COPY with navigation replaced, not modified app source.
        page.evaluate(r"""async () => {
          const testLoad=eval('('+loadCloudStateOntoDevice.toString().replace('location.reload();','window.__reloaded=true;')+')');
          await testLoad();
        }""")
        check('cloud load writes recovery before replacement',page.evaluate("__reloaded===true && __storageWrites.lastIndexOf(PRE_CLOUD_RESTORE_KEY)<__storageWrites.lastIndexOf(STORAGE_KEY) && !!JSON.parse(localStorage.getItem(PRE_CLOUD_RESTORE_KEY)).state"))
        page.evaluate('firebaseCloudBusy=false;signOutGoogle()')
        check('sign-out leaves local library',page.evaluate('firebaseUser===null && !!localStorage.getItem(STORAGE_KEY)'))
        page.evaluate(CLOUD)
        page.evaluate("__cloud.failWrite='/decks/';uploadLocalStateToCloud()")
        check('failed initial deck write does not mark ready',page.evaluate("firebaseCloudStatus==='error' && !__cloud.docs['users/synthetic-uid']"))
        check('no uncaught app errors in smoke scenarios',not errors)

        # Compare representative actual browser renders, without contacting SDKs.
        for width,height in [(1440,900),(393,852)]:
            for state in ['library','study','account']:
                images = []
                for name,html in [('annotated',source)]+([('baseline',baseline)] if baseline else []):
                    p,errs = new_page(html=html,width=width,height=height)
                    if state=='study':
                        p.evaluate('switchDeck(PSYCH_DECK_ID);currentFact=getFactById("psychology|front",PSYCH_DECK_ID);renderCurrentFact({forceImmediate:true})')
                    if state=='account':
                        p.evaluate(CLOUD);p.evaluate('openFirebaseAccount()')
                    p.wait_for_timeout(200)
                    check(f'{name} {state} {width} no horizontal overflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                    check(f'{name} {state} {width} no uncaught error',not errs)
                    filename=f'{width}-{state}-{name}.png'
                    image=p.screenshot(path=str(OUT/filename),full_page=False)
                    report['screenshots'].append(filename);images.append(image)
                if baseline:
                    check(f'{state} {width} pixel-identical',images[0]==images[1])
        for context in contexts:
            context.close()
        browser.close()
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path)
    args=parser.parse_args()
    report=run((ROOT/'src/skystudee.html').read_text(),args.baseline.read_text() if args.baseline else None)
    print(f"PASS {len(report['checks'])} checks; screenshots in {OUT}")
