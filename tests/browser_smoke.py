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
  window.__cloud={docs:{},writes:[],listeners:[],failWrite:null};
  const pathOf=(...args)=>args.map(x=>typeof x==='string'?x:(x?.path||'')).filter(Boolean).join('/');
  const ref=(...args)=>({path:pathOf(...args)});
  const snap=r=>({
    ref:r,id:r.path.split('/').pop(),
    exists:()=>Object.prototype.hasOwnProperty.call(__cloud.docs,r.path),
    data:()=>__cloud.docs[r.path]
  });
  const notify=path=>{
    for(const listener of __cloud.listeners.slice()){
      if(listener.path===path) queueMicrotask(()=>listener.next(snap({path})));
    }
  };
  const directDocs=r=>Object.keys(__cloud.docs)
    .filter(k=>k.startsWith(r.path+'/')&&k.slice(r.path.length+1).indexOf('/')<0)
    .map(k=>snap({path:k}));
  const write=(kind,r,data)=>{
    if(__cloud.failWrite&&r.path.includes(__cloud.failWrite)){
      const error=new Error('synthetic failure');error.code='unavailable';throw error;
    }
    __cloud.writes.push([kind,r.path]);
    if(kind==='delete') delete __cloud.docs[r.path];
    else __cloud.docs[r.path]=JSON.parse(JSON.stringify(data));
    notify(r.path);
  };

  firebaseUser={uid:'synthetic-uid',email:'test@example.invalid',displayName:'Synthetic'};
  firebaseApp={}; firebaseDb={}; firebaseAuth={}; firebaseAuthReady=true;
  activeAccountUid=firebaseUser.uid;
  localStorage.setItem(ACTIVE_ACCOUNT_UID_KEY,activeAccountUid);
  localStorage.setItem(accountStorageKey(activeAccountUid),JSON.stringify(appState));
  firebaseFirestoreApi={
    doc:ref, collection:ref, serverTimestamp:()=>new Date().toISOString(),
    getDoc:async r=>snap(r),
    getDocs:async r=>{const docs=directDocs(r);return {docs,forEach:fn=>docs.forEach(fn)}},
    setDoc:async(r,data)=>write('set',r,data),
    deleteDoc:async r=>write('delete',r),
    onSnapshot:(r,next,error)=>{
      const listener={path:r.path,next,error};__cloud.listeners.push(listener);
      queueMicrotask(()=>next(snap(r)));
      return ()=>{__cloud.listeners=__cloud.listeners.filter(item=>item!==listener)};
    },
    runTransaction:async(db,fn)=>{
      const pending=[];
      const transaction={
        get:async r=>snap(r),
        set:(r,data)=>pending.push(['set',r,data]),
        delete:r=>pending.push(['delete',r,null])
      };
      const result=await fn(transaction);
      for(const [kind,r,data] of pending) write(kind,r,data);
      return result;
    }
  };
  firebaseAuthApi={signOut:async()=>{firebaseUser=null;firebaseCloudStatus='idle';renderFirebaseAccount();}};
  firebaseCloudStatus='idle';
  firebaseSyncRevision=0;firebaseSyncGenerationId='';firebaseSyncBaseState=null;firebaseSyncDirty=true;
  writeSyncMeta(activeAccountUid,{revision:0,generationId:'',dirty:true,baseState:null});
  renderFirebaseAccount();
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
        check('local studying available with SDK blocked',page.evaluate('!firebaseAuthReady && Object.keys(appState.decks).length===7'))
        check('fresh profile has no German deck',page.evaluate('!appState.decks[RETIRED_GERMAN_DECK_ID] && !!appState.decks[activeDeckId]'))
        check('both Unit 4 decks bundled under AP Psychology Unit 4',page.evaluate("""() => [SOCIAL_PSYCH_DECK_ID,PERSONALITY_DECK_ID].every(id => {
          const deck=appState.decks[id];
          return deck?.preloaded===true && deck.cards.length===(id===SOCIAL_PSYCH_DECK_ID?73:81) &&
            appState.classes[deck.classId]?.catalogId==='ap_psychology' &&
            appState.units[deck.unitId]?.name==='Unit 4';
        })"""))
        check('combined Unit 1 deck is bundled in AP Psychology Unit 1',page.evaluate("""() => {
          const deck=appState.decks[SENSATION_DECK_ID];
          const cls=appState.classes[deck?.classId];
          const unit=appState.units[deck?.unitId];
          return deck?.preloaded===true && deck.cards.length===105 &&
            cls?.catalogId==='ap_psychology' && unit?.name==='Unit 1';
        }"""))
        check('Unit 2 Part 1 is bundled in AP Psychology Unit 2',page.evaluate("""() => {
          const deck=appState.decks[COGNITION_PART1_DECK_ID];
          const cls=appState.classes[deck?.classId];
          const unit=appState.units[deck?.unitId];
          return deck?.preloaded===true && deck.cards.length===122 &&
            cls?.catalogId==='ap_psychology' && unit?.name==='Unit 2';
        }"""))
        check('Unit 3 Development deck preloaded in correct class/unit', page.evaluate("""() => {
          const deck=appState.decks[DEVELOPMENT_DECK_ID];
          return deck?.preloaded===true && deck.cards.length===117 &&
            appState.classes[deck.classId]?.catalogId==='ap_psychology' &&
            appState.units[deck.unitId]?.name==='Unit 3';
        }"""))
        saved = page.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')
        saved['decks']['ap_psych:biological_bases_brain']['name']='AP Psychology — Biological Bases of Behavior: The Brain'
        legacy, legacy_errors = new_page(saved=saved)
        check('legacy Brain migration loads without TDZ error',not legacy_errors and legacy.locator('#decksView').is_visible())
        check('legacy rename persisted',legacy.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY)).decks[BRAIN_DECK_ID].name===BRAIN_DECK_NAME'))

        pre_sensation = page.evaluate('plainJson(appState)')
        pre_sensation['version'] = 10
        pre_sensation['decks'].pop('ap_psych:unit_1_sensation', None)
        upgraded, upgraded_errors = new_page(saved=pre_sensation)
        check('pre-v11 profile receives complete Unit 1 deck once',not upgraded_errors and upgraded.evaluate("""() => {
          const deck=appState.decks[SENSATION_DECK_ID];
          return deck?.cards.length===105 && appState.units[deck.unitId]?.name==='Unit 1';
        }"""))

        pre_consciousness = page.evaluate('plainJson(appState)')
        pre_consciousness['version'] = 11
        state_ids = set(page.evaluate('CONSCIOUSNESS_CARDS.map(card => card.id)'))
        state_deck = pre_consciousness['decks']['ap_psych:unit_1_sensation']
        state_deck['cards'] = [card for card in state_deck['cards'] if card['id'] not in state_ids]
        state_deck['name'] = 'Unit 1 — AP Psychology — Biological Bases of Behavior: Sensation'
        state_deck['facts']['sensation|front']['alpha'] = 9
        expanded, expanded_errors = new_page(saved=pre_consciousness)
        check('v11 deck gains consciousness cards without losing progress',not expanded_errors and expanded.evaluate("""() => {
          const deck=appState.decks[SENSATION_DECK_ID];
          return deck.cards.length===105 &&
            deck.name===SENSATION_DECK_NAME &&
            deck.cards.some(card=>card.id==='circadian_rhythm') &&
            deck.cards.some(card=>card.id==='psychoactive_drugs') &&
            deck.facts['sensation|front'].alpha===9;
        }"""))

        upgraded.evaluate("delete appState.decks[SENSATION_DECK_ID];persistState({includeSession:false})")
        deleted_sensation = upgraded.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')
        after_delete, after_delete_errors = new_page(saved=deleted_sensation)
        check('deleted Unit 1 preload stays deleted after migration',not after_delete_errors and after_delete.evaluate('!appState.decks[SENSATION_DECK_ID]'))

        pre_unit2 = page.evaluate('plainJson(appState)')
        pre_unit2['version'] = 12
        pre_unit2['decks'].pop('ap_psych:unit_2_part_1_cognition', None)
        unit2_upgraded, unit2_upgraded_errors = new_page(saved=pre_unit2)
        check('v12 profile receives Unit 2 Part 1 once',not unit2_upgraded_errors and unit2_upgraded.evaluate("""() => {
          const deck=appState.decks[COGNITION_PART1_DECK_ID];
          return deck?.preloaded===true && deck.cards.length===122 &&
            appState.units[deck.unitId]?.name==='Unit 2';
        }"""))
        unit2_upgraded.evaluate("delete appState.decks[COGNITION_PART1_DECK_ID];persistState({includeSession:false})")
        deleted_unit2 = unit2_upgraded.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')
        after_unit2_delete, after_unit2_delete_errors = new_page(saved=deleted_unit2)
        check('deleted Unit 2 Part 1 preload stays deleted after v13',not after_unit2_delete_errors and after_unit2_delete.evaluate('!appState.decks[COGNITION_PART1_DECK_ID]'))

        pre_unit3 = page.evaluate('plainJson(appState)')
        pre_unit3['version'] = 13
        pre_unit3['decks'].pop('ap_psych:unit_3_development_and_learning', None)
        unit3_upgraded, unit3_errors = new_page(saved=pre_unit3)
        check('v13 profile receives Unit 3 without losing Unit 2', not unit3_errors and unit3_upgraded.evaluate("""() => {
          return appState.decks[DEVELOPMENT_DECK_ID]?.cards.length===117 &&
            !!appState.decks[COGNITION_PART1_DECK_ID];
        }"""))
        unit3_upgraded.evaluate("delete appState.decks[DEVELOPMENT_DECK_ID];persistState({includeSession:false})")
        deleted_unit3 = unit3_upgraded.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')
        deleted_unit3_page, unit3_delete_errors = new_page(saved=deleted_unit3)
        check('deleted Unit 3 not silently restored at schema 14', not unit3_delete_errors and deleted_unit3_page.evaluate('!appState.decks[DEVELOPMENT_DECK_ID]'))

        pre_unit4 = page.evaluate('plainJson(appState)')
        pre_unit4['version'] = 14
        pre_unit4['decks'].pop('ap_psych:unit_4_social_psychology', None)
        pre_unit4['decks'].pop('ap_psych:unit_4_motivation_emotion_personality', None)
        pre_unit4['decks']['builtin:german-perfect:v1'] = {'id':'builtin:german-perfect:v1','name':'German — Verben im Perfekt','builtin':True,
            'cards':[{'id':'machen','front':'machen','back':'hat gemacht'}],'facts':{}}
        pre_unit4['activeDeckId'] = 'builtin:german-perfect:v1'
        pre_unit4['studySet'] = {'active':True,'deckIds':['builtin:german-perfect:v1','ap_psych:unit_0_research_methods'],'settings':{},'sessionState':None}
        unit4_page, unit4_errors = new_page(saved=pre_unit4)
        check('v14 profile gains both Unit 4 decks and loses German', not unit4_errors and unit4_page.evaluate("""() =>
          !!appState.decks[SOCIAL_PSYCH_DECK_ID] && !!appState.decks[PERSONALITY_DECK_ID] &&
          !appState.decks[RETIRED_GERMAN_DECK_ID] && !!appState.decks[activeDeckId] &&
          !appState.studySet.deckIds.includes(RETIRED_GERMAN_DECK_ID) &&
          !JSON.parse(localStorage.getItem(STORAGE_KEY)).decks[RETIRED_GERMAN_DECK_ID]"""))
        unit4_page.evaluate("delete appState.decks[PERSONALITY_DECK_ID];persistState({includeSession:false})")
        deleted_unit4 = unit4_page.evaluate('JSON.parse(localStorage.getItem(STORAGE_KEY))')
        deleted_unit4_page, unit4_delete_errors = new_page(saved=deleted_unit4)
        check('deleted Unit 4 deck stays deleted at schema 15', not unit4_delete_errors and deleted_unit4_page.evaluate('!appState.decks[PERSONALITY_DECK_ID] && !!appState.decks[SOCIAL_PSYCH_DECK_ID]'))
        only_german = {'version':14,'userName':'Synthetic','decks':{'builtin:german-perfect:v1':pre_unit4['decks']['builtin:german-perfect:v1']},'activeDeckId':'builtin:german-perfect:v1'}
        only_german_page, only_german_errors = new_page(saved=only_german)
        check('German-only snapshot falls back to starter decks', not only_german_errors and only_german_page.evaluate('Object.keys(appState.decks).length>=7 && !!activeDeck() && !appState.decks[RETIRED_GERMAN_DECK_ID]'))
        last_deck = {'version':15,'userName':'Synthetic','decks':{'test:solo':{'id':'test:solo','name':'Solo','cards':[{'id':'a','front':'A','back':'B'}],'facts':{}}},'activeDeckId':'test:solo'}
        solo_page, solo_errors = new_page(saved=last_deck)
        solo_page.evaluate("for (const id of Object.keys(appState.decks)) if (id!=='test:solo') delete appState.decks[id]; deleteRealDeck('test:solo')")
        check('last remaining deck cannot be deleted', not solo_errors and solo_page.evaluate("!!appState.decks['test:solo'] && Object.keys(appState.decks).length===1"))

        # Duplicate classes/units (e.g. created independently on two synced devices) merge into one.
        dup = page.evaluate("plainJson(appState)")
        psych_id = page.evaluate("findClassByCatalog(appState,'ap_psychology').id")
        dup['classes']['class:ap_psychology:dupe'] = {'id':'class:ap_psychology:dupe','catalogId':None,'name':'AP  psychology','familyId':'history','order':99}
        dup['units']['unit:unit_4:dupe'] = {'id':'unit:unit_4:dupe','classId':'class:ap_psychology:dupe','name':'Unit 4','order':0}
        dup['units']['unit:unit_3:dupe'] = {'id':'unit:unit_3:dupe','classId':psych_id,'name':'unit 3','order':50}
        dup['decks']['ap_psych:unit_4_social_psychology']['classId'] = 'class:ap_psychology:dupe'
        dup['decks']['ap_psych:unit_4_social_psychology']['unitId'] = 'unit:unit_4:dupe'
        dup['decks']['ap_psych:unit_4_social_psychology']['facts']['social_psychology|front']['alpha'] = 7
        dup['decks']['ap_psych:unit_3_development_and_learning']['unitId'] = 'unit:unit_3:dupe'
        merged_page, merged_errors = new_page(saved=dup)
        check('duplicate AP Psychology classes and units merge into one', not merged_errors and merged_page.evaluate("""() => {
          const psych = Object.values(appState.classes).filter(c => normalizeLibraryText(c.name) === 'ap psychology');
          const names = Object.values(appState.units).filter(u => u.classId === psych[0]?.id).map(u => normalizeLibraryText(u.name));
          const social = appState.decks[SOCIAL_PSYCH_DECK_ID], dev = appState.decks[DEVELOPMENT_DECK_ID];
          return psych.length === 1 && psych[0].catalogId === 'ap_psychology' &&
            names.length === new Set(names).size &&
            social.classId === psych[0].id && appState.units[social.unitId]?.name === 'Unit 4' &&
            social.facts['social_psychology|front'].alpha === 7 &&
            dev.classId === psych[0].id && normalizeLibraryText(appState.units[dev.unitId]?.name) === 'unit 3' &&
            document.querySelectorAll('.class-group').length === Object.values(appState.classes).filter(c => usedClassIds().has(c.id)).length;
        }"""))
        lost_link = page.evaluate("plainJson(appState)")
        lost_link['version'] = 14
        for key in ('ap_psych:unit_4_social_psychology', 'ap_psych:unit_4_motivation_emotion_personality'): lost_link['decks'].pop(key, None)
        lost_link['units'] = {k:v for k,v in lost_link['units'].items() if v['name'] != 'Unit 4'}
        lost_link['classes'][psych_id]['catalogId'] = None
        lost_page, lost_errors = new_page(saved=lost_link)
        check('Unit 4 upgrade joins an AP Psychology class that lost its catalog link', not lost_errors and lost_page.evaluate(
          "appState.decks[SOCIAL_PSYCH_DECK_ID].classId===appState.decks[DEVELOPMENT_DECK_ID].classId && Object.values(appState.classes).filter(c=>normalizeLibraryText(c.name)==='ap psychology').length===1"))

        # ROUND SCHEDULER: coverage, new-first, bounded practice share, missed cards return.
        SIM = r"""(missEvery) => {
          const cards = Array.from({length:120},(_,i)=>({id:'c'+i,front:'Front '+i,back:'Back '+i}));
          appState.decks['sim:big'] = createDeckRecord({id:'sim:big',name:'Sim',cards});
          appState.decks['sim:big'].settings.direction = 'front';
          studySetActive=false; appState.studySet.active=false;
          activeDeckId='sim:big'; appState.activeDeckId='sim:big';
          mode='memory'; session=makeFreshSession('memory');
          const seen = new Set(); const missedAt = new Map(); const gaps = [];
          let draws = 0, practice = 0, newCount = 0;
          while (seen.size < 120 && draws < 2000) {
            const fact = weightedRandomFact('memory'); recordServed(fact); draws++;
            if (session.lastLane === 'practice') practice++;
            if (missedAt.has(fact.id)) { gaps.push(session.servedCount - missedAt.get(fact.id)); missedAt.delete(fact.id); }
            const isNew = factDirectAttempts(fact.id, appState.decks['sim:big']) === 0;
            seen.add(fact.id);
            let known = true;
            if (isNew) { newCount++; known = !(missEvery && newCount % missEvery === 0); }
            if (!known) missedAt.set(fact.id, session.servedCount);
            recordSessionResult(fact, known, {answerMode:'self'});
          }
          delete appState.decks['sim:big'];
          activeDeckId = fallbackDeckId(appState); appState.activeDeckId = activeDeckId;
          mode='memory'; session=makeFreshSession('memory'); currentFact=weightedRandomFact('memory'); recordServed(currentFact);
          return {draws, practice, returns: gaps.length, maxGap: gaps.length ? Math.max(...gaps) : 0,
                  meanGap: gaps.length ? gaps.reduce((a,b)=>a+b,0)/gaps.length : 0};
        }"""
        typical = page.evaluate(SIM, 3)   # misses one new card in three
        worst = page.evaluate(SIM, 1)     # misses every new card the first time
        print('scheduler typical', typical); print('scheduler worst', worst)
        coverage = page.evaluate(r"""() => {
          const cards = Array.from({length:40},(_,i)=>({id:'s'+i,front:'S '+i,back:'T '+i}));
          appState.decks['sim:small'] = createDeckRecord({id:'sim:small',name:'Small',cards});
          appState.decks['sim:small'].settings.direction='front';
          activeDeckId='sim:small'; appState.activeDeckId='sim:small'; mode='cram'; session=makeFreshSession('cram');
          const ids = [];
          for (let i=0;i<40;i++){ const f=weightedRandomFact('cram'); recordServed(f); ids.push(f.id); recordSessionResult(f,true,{answerMode:'self'}); }
          delete appState.decks['sim:small'];
          activeDeckId = fallbackDeckId(appState); appState.activeDeckId = activeDeckId;
          mode='memory'; session=makeFreshSession('memory'); currentFact=weightedRandomFact('memory'); recordServed(currentFact);
          return new Set(ids).size;
        }""")
        check('a round shows every card once before repeating', coverage == 40)
        # Each miss costs at most two practice draws, so N + 2*misses bounds full coverage.
        check('typical learner sees all 120 cards within 120 + 2 x 40 misses', typical['draws'] <= 200)
        check('typical misses return within 25 served cards', typical['returns'] >= 30 and typical['maxGap'] <= 25)
        check('worst case still sees all 120 cards within 260 draws', worst['draws'] <= 260)
        check('missed-card practice never exceeds half of draws', typical['practice'] <= typical['draws'] * .5 and worst['practice'] <= worst['draws'] * .5)

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
        page.evaluate("""() => {
          showStudyView(); accountOverlay.classList.add('show'); accountOverlay.setAttribute('aria-hidden','false');
          window.__beforeModalAnswers=session.answers;
        }""")
        page.keyboard.press('ArrowRight')
        check('account modal blocks study shortcuts',page.evaluate('session.answers===window.__beforeModalAnswers'))
        page.evaluate("""() => {
          accountOverlay.classList.remove('show'); accountOverlay.setAttribute('aria-hidden','true');
          appState.studySet={...defaultStudySetState(),active:true,deckIds:['test:a','test:b']};
          studySetActive=true;activeDeckId='test:a';appState.activeDeckId='test:a';
          mode='memory';session=makeFreshSession(mode);
          currentFact=getFactById('shared|front','test:b');recordServed(currentFact);
          delete appState.decks['test:b'];
          reconcileActiveContextAfterMutation({persist:false,render:false});
        }""")
        check('active set repairs deleted current owner',page.evaluate(
          "!!currentFact && !!appState.decks[currentFact.deckId] && !!getFactByKey(factKey(currentFact))"
        ))

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
        check('import preselects the existing class for a catalog match',page.evaluate("importClassSelect.value.startsWith('existing:')"))
        page.evaluate('importPreviewOverlay.classList.remove("show")')

        page.evaluate(CLOUD)
        page.evaluate('refreshFirebaseCloudStatus()')
        page.wait_for_function("firebaseCloudStatus === 'empty'")
        check('missing cloud root => sync disabled',page.evaluate("firebaseCloudStatus==='empty'"))
        check('account profile uses UID-isolated storage',page.evaluate(
          "currentStorageKey()===accountStorageKey('synthetic-uid')"
        ))

        page.evaluate('uploadLocalStateToCloud()')
        page.wait_for_function("firebaseCloudStatus === 'ready' && !firebaseCloudBusy")
        check('first sync publishes schema-3 generation',page.evaluate(
          "__cloud.docs['users/synthetic-uid'].cloudSchemaVersion===3 && "
          "__cloud.docs['users/synthetic-uid'].revision===1 && "
          "!!__cloud.docs['users/synthetic-uid'].activeGeneration"
        ))
        check('completed generation selected atomically',page.evaluate("""() => {
          const root=__cloud.docs['users/synthetic-uid'];
          const marker=__cloud.docs[`users/synthetic-uid/generations/${root.activeGeneration}`];
          return marker?.snapshotComplete===true && marker.deckCount===root.deckCount;
        }"""))

        # A schema-2 cloud written by a v14 client (with the retired German deck) is read, merged
        # without German, and republished as schema 3 at the next revision.
        page.evaluate("""() => {
          for (const doc of Object.values(__cloud.docs)) if (doc && doc.cloudSchemaVersion===3) doc.cloudSchemaVersion=2;
          const root=__cloud.docs['users/synthetic-uid'];
          __cloud.docs[`users/synthetic-uid/generations/${root.activeGeneration}/decks/german`] =
            {cloudSchemaVersion:2, deck:{id:RETIRED_GERMAN_DECK_ID,name:'German',builtin:true,cards:[{id:'m',front:'machen',back:'gemacht'}],facts:{}}};
          root.deckCount += 1;
        }""")
        schema2_revision = page.evaluate("__cloud.docs['users/synthetic-uid'].revision")
        page.evaluate('performFirebaseSync({force:true})')
        page.wait_for_function("firebaseCloudStatus !== 'checking' && !firebaseCloudBusy")
        check('schema-2 cloud upgrades to schema 3 without German',page.evaluate("""() => {
          const root=__cloud.docs['users/synthetic-uid'];
          const deckDocs=Object.entries(__cloud.docs).filter(([k])=>k.startsWith(`users/synthetic-uid/generations/${root.activeGeneration}/`));
          return firebaseCloudStatus==='ready' && root.cloudSchemaVersion===3 &&
            !deckDocs.some(([,d])=>d?.deck?.id===RETIRED_GERMAN_DECK_ID) && !appState.decks[RETIRED_GERMAN_DECK_ID];
        }""") and page.evaluate("__cloud.docs['users/synthetic-uid'].revision")==schema2_revision+1)

        prior_revision = page.evaluate("__cloud.docs['users/synthetic-uid'].revision")
        page.evaluate("""() => { appState.userName='Synthetic Updated'; persistState(); }""")
        check('local durable save marks account dirty',page.evaluate('firebaseSyncDirty===true'))
        page.evaluate('performFirebaseSync({force:true})')
        page.wait_for_function("firebaseCloudStatus === 'ready' && !firebaseCloudBusy && firebaseSyncDirty === false")
        check('dirty account publishes next revision',page.evaluate(
          "__cloud.docs['users/synthetic-uid'].revision"
        )==prior_revision+1)

        merge_result = page.evaluate("""() => {
          const base=cloudSnapshotState();
          const local=plainJson(base);const remote=plainJson(base);
          const id='psychology|front';
          local.decks[PSYCH_DECK_ID].facts[id].alpha+=1;
          local.decks[PSYCH_DECK_ID].facts[id].directCorrect+=1;
          remote.decks[PSYCH_DECK_ID].facts[id].alpha+=1;
          remote.decks[PSYCH_DECK_ID].facts[id].directCorrect+=1;
          const merged=mergeSyncedStates(base,local,remote);
          return {alpha:merged.decks[PSYCH_DECK_ID].facts[id].alpha,
                  correct:merged.decks[PSYCH_DECK_ID].facts[id].directCorrect,
                  baseAlpha:base.decks[PSYCH_DECK_ID].facts[id].alpha,
                  baseCorrect:base.decks[PSYCH_DECK_ID].facts[id].directCorrect};
        }""")
        check('concurrent review deltas merge additively',
              merge_result['alpha']==merge_result['baseAlpha']+2 and
              merge_result['correct']==merge_result['baseCorrect']+2)

        page.evaluate("saveLocalRecoverySnapshot('synthetic-test')")
        check('account-scoped recovery snapshot is written',page.evaluate(
          "!!JSON.parse(localStorage.getItem(recoveryStorageKey())).state"
        ))

        page.evaluate("""() => {
          __cloud.failWrite='/decks/';appState.userName='Unsynced after failure';persistState();
        }""")
        page.evaluate('performFirebaseSync({force:true})')
        page.wait_for_function("firebaseCloudStatus === 'error' && !firebaseCloudBusy")
        check('failed generation write keeps local dirty',page.evaluate('firebaseSyncDirty===true'))
        page.evaluate("__cloud.failWrite=null")
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
