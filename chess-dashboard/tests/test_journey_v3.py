"""V3 learning loop and persistence, including real board keyboard/touch actions."""
import json
from pathlib import Path
import pytest
from playwright.sync_api import expect

PUBLIC=Path(__file__).resolve().parents[1]/'public/app'
CATALOG=json.loads((PUBLIC/'puzzle-catalog.js').read_text().split('window.PuzzleCatalog = ')[1].rstrip(';\n'))
PACKS={t['id']:json.loads((PUBLIC/f'puzzle-packs/{t["id"]}.json').read_text()) for t in CATALOG['themes']}
PUZZLES={p['id']:p for pack in PACKS.values() for p in pack}
ROOT='learning:v2:tactics-v1:'


def ready(page,app_url,route='explore/puzzles'):
 page.goto(app_url+'/app/#'+route)
 page.wait_for_function('window.App && window.Puzzles && window.Auth.state.ready')


def answer(page,uci,keyboard=False):
 a=page.locator(f'#puzzleBoard .cb-sq[data-square="{uci[:2]}"]');b=page.locator(f'#puzzleBoard .cb-sq[data-square="{uci[2:4]}"]')
 if keyboard:a.focus();a.press('Enter');b.focus();b.press('Enter')
 else:a.click();b.click()
 if len(uci)>4:page.locator(f'#puzzleBoard .cb-promo button[data-uci="{uci}"]').click()


def solve(page,keyboard=False):
 while True:
  session=page.evaluate('Puzzles.info()')
  if session.get('finished'):return session
  answer(page,PUZZLES[session['puzzle']]['scenes'][session['ply']]['answer'],keyboard)


def start(page,puzzle_id,**kwargs):
 page.evaluate('([id,options])=>Puzzles.start(id,options)',[puzzle_id,kwargs])
 expect(page.locator('#puzzleSession')).to_be_visible()


@pytest.mark.parametrize('theme',list(PACKS))
def test_each_micro_lesson_teaches_then_connects_to_a_new_puzzle(page,app_url,theme):
 ready(page,app_url,'explore/path')
 idea=next(l for l in CATALOG['lessons'] if l['theme']==theme)
 page.locator(f'.path-node[data-idea="{idea["id"]}"]').click()
 expect(page.locator('[data-puzzle-action="select-piece"]')).to_be_visible()
 page.locator('[data-puzzle-action="select-piece"]').click()
 expect(page.locator('#puzzleBoard .cb-arrow')).to_have_count(1)
 page.locator('[data-puzzle-action="frame-next"]').click()
 page.locator('[data-puzzle-action="try-idea"]').click()
 completed=solve(page,keyboard=True)
 assert completed['lesson']==idea['id']
 assert page.evaluate('(id)=>LearningStore.forCourse("patterns-v1").completed(id)',idea['id'])
 assert page.evaluate('LearningStore.forCourse("patterns-v1").summary(PuzzleCatalog.lessons).attempts')==[]
 page.locator('[data-related-theme]').click()
 page.wait_for_function('(previous)=>Puzzles.info()?.puzzle!==previous',arg=idea['puzzle'])
 assert page.evaluate('Puzzles.info().mode')=='puzzle'
 solve(page)
 expect(page.locator('#puzzleInstruction')).to_contain_text('Solved first time, without help')
 assert page.evaluate('Journey.achievements().length')==2
 page.reload();page.locator('[data-view=progress]:visible').first.click()
 expect(page.locator('.earned-milestones li')).to_have_count(2)
 assert page.evaluate('Journey.weekly().count')==1


@pytest.mark.parametrize('side',['white','black'])
def test_wrong_retry_hint_reload_and_exact_opponent_reply_resume(page,app_url,side):
 ready(page,app_url)
 puzzle=next(p for p in PUZZLES.values() if p['side']==side and len(p['scenes'])>=4)
 start(page,puzzle['id'])
 wrong=next(m for m in puzzle['scenes'][0]['legal'] if m['uci'] not in puzzle['scenes'][0]['accepted'])
 answer(page,wrong['uci']);expect(page.locator('#puzzleFeedback')).to_contain_text('legal, but')
 page.locator('[data-puzzle-action=hint]').click();page.locator('[data-puzzle-action=hint]').click()
 answer(page,puzzle['scenes'][0]['answer'])
 saved=page.evaluate('Puzzles.info()');assert saved['ply']==2 and saved['help']==2 and saved['misses']==1
 page.reload();page.locator('[data-puzzle-action=resume]').click()
 page.wait_for_function('Puzzles.info()?.ply===2')
 assert page.evaluate('Puzzles.info().played')==saved['played']
 assert page.locator('#puzzleBoard').get_attribute('data-orientation') in (None,side)
 solve(page)
 events=page.evaluate('(id)=>LearningStore.forCourse("tactics-v1").schedule(id).events',puzzle['id'])
 assert len(events)==1 and events[0]['outcome']=='hinted'
 page.reload();page.locator('[data-puzzle-queue=missed]').click();expect(page.locator('#puzzleSession')).to_be_visible()
 assert page.evaluate('Puzzles.info().puzzle')==puzzle['id']


def test_reveal_is_assisted_and_puzzle_remains_offline_after_pack_load(page,app_url):
 ready(page,app_url);puzzle=PACKS['forks'][2];start(page,puzzle['id'])
 page.route('**/api/position?**',lambda r:r.abort())
 page.context.set_offline(True)
 page.locator('[data-puzzle-action=reveal]').click()
 assert page.evaluate('(id)=>LearningStore.forCourse("tactics-v1").schedule(id).events[0].outcome',puzzle['id'])=='revealed'
 expect(page.locator('#puzzleInstruction')).to_contain_text('Solution explored with your guide')
 assert page.evaluate('Puzzles.info().played.length')==len(puzzle['scenes'])-1
 page.context.set_offline(False)


def test_alternative_mate_in_one_is_accepted_with_its_real_final_board(page,app_url):
 puzzle=next(p for p in PUZZLES.values() if len(p['scenes'][0]['accepted'])>1)
 ready(page,app_url);start(page,puzzle['id']);scene=puzzle['scenes'][0]
 alternate=next(a for a in scene['accepted'] if a!=scene['answer'])
 answer(page,alternate)
 assert page.evaluate('Puzzles.info().finished')
 assert page.evaluate('Puzzles.info().finalFen')==scene['ends'][alternate]
 expect(page.locator('#puzzleInstruction')).to_contain_text('Solved first time')


@pytest.mark.parametrize('width,height',[(360,800),(390,844),(768,1024),(1440,1000)])
def test_navigation_mobile_board_and_profile_are_usable(page,app_url,width,height):
 page.set_viewport_size({'width':width,'height':height});ready(page,app_url,'explore/path')
 assert page.locator('#nav [data-view]').count()==4
 expect(page.locator('.path-node')).to_have_count(12)
 page.locator('[data-journey=list]').click();expect(page.locator('.pattern-path')).to_have_class('pattern-path is-list')
 page.locator('#openLearningProfile').click()
 form=page.locator('#learningProfileForm');form.locator('[name=nickname]').fill('Alex');form.locator('[name=goal]').select_option('4');form.locator('[name=palette]').select_option('contrast');form.locator('[name=motion]').check();form.locator('[type=submit]').click()
 expect(page.locator('html')).to_have_attribute('data-board','contrast')
 expect(page.locator('html')).to_have_attribute('data-motion','reduce')
 assert page.evaluate('Journey.settings().nickname')=='Alex'
 page.locator('#exploreSections a[href="#explore/puzzles"]').click()
 page.locator('[data-puzzle-queue=daily]').click();expect(page.locator('#puzzleBoard')).to_be_visible()
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert page.evaluate('document.querySelector("main").scrollWidth<=document.querySelector("main").clientWidth')
 box=page.locator('#puzzleBoard').bounding_box()
 if width<400:assert box['width']>=width-30 and box['y']+box['height']<height-65
 page.locator('[data-puzzle-action=hint]').click()
 page.locator('[data-view=repertoire]:visible').first.click();expect(page.locator('#viewRepertoire')).to_be_visible()
 page.locator('[data-view=explore]:visible').first.click();expect(page.locator('#viewExplore')).to_be_visible()
 expect(page.locator('#exploreSections')).to_be_visible()


def test_week_boundaries_use_profile_timezone_and_rewards_never_duplicate(page,app_url):
 ready(page,app_url)
 page.evaluate('''() => {
 Store.prefs.set('learning:v2:journey-v3:preferences',{goal:3,timezone:'America/New_York',updated:1});
 LearningStore.forCourse('patterns-v1').complete('forks-1');
 for(let i=0;i<5;i++)Journey.achievements();
 }''')
 assert len(page.evaluate('Journey.achievements()'))==1
 # Sunday 23:30 in New York is already Monday in UTC, including autumn DST.
 week=page.evaluate('Journey.weekly(Date.parse("2026-11-02T04:30:00Z")).dates')
 assert week[0]=='2026-10-26' and week[-1]=='2026-11-01'
 assert page.evaluate('Journey.dateKey(Date.parse("2026-11-02T04:30:00Z"))')=='2026-11-01'


def mock_account(page,uid='alice',fail=False):
 remote={'runs':[],'drills':{},'repertoire':[],'prefs':{},'progress':{}}
 page.route('**/api/auth/me',lambda r:r.fulfill(json={'database':True,'user':{'id':uid,'name':uid},'methods':{}}))
 def state_response(route):
  if route.request.headers.get('x-account-owner')!=uid:
   route.fulfill(status=409,json={'detail':'Account changed'});return
  route.fulfill(json=remote)
 page.route('**/api/state',state_response)
 def importing(route):
  if route.request.headers.get('x-account-owner')!=uid:
   route.fulfill(status=409,json={'detail':'Account changed'});return
  for k,v in route.request.post_data_json.get('prefs',{}).items():remote['prefs'].setdefault(k,v)
  route.fulfill(json=remote)
 page.route('**/api/state/import',importing)
 def pref(route):
  if route.request.headers.get('x-account-owner')!=uid:
   route.fulfill(status=409,json={'detail':'Account changed'});return
  if fail:route.abort();return
  payload=route.request.post_data_json;remote['prefs'][payload['key']]=payload['value'];route.fulfill(json={'ok':True})
 page.route('**/api/state/pref',pref)
 return remote


def test_learning_outbox_survives_reload_coalesces_and_retries_without_duplicate_evidence(page,app_url):
 remote=mock_account(page,fail=True);ready(page,app_url)
 page.evaluate('''() => {
 const l=LearningStore.forCourse('tactics-v1');l.enrol('one');l.attempt('attempt-one','one','hinted','Nf3');
 const sessions=LearningStore.forCourse('puzzle-sessions-v1');
 sessions.saveSession({id:'test-checkpoint',mode:'puzzle',ply:0});
 sessions.saveSession({id:'test-checkpoint',mode:'puzzle',ply:2});
 }''')
 page.wait_for_function('Object.keys(Store.sync.pending("alice")).filter(k=>!k.startsWith("learning:v2:journey-v3:")).length===4')
 page.reload();page.wait_for_function('Auth.state.ready')
 assert page.evaluate('LearningStore.forCourse("puzzle-sessions-v1").session().ply')==2
 assert page.evaluate('Object.keys(Store.sync.pending("alice")).filter(k=>!k.startsWith("learning:v2:journey-v3:")).length')==4
 page.unroute('**/api/state/pref')
 def pref(route):
  payload=route.request.post_data_json;remote['prefs'][payload['key']]=payload['value'];route.fulfill(json={'ok':True})
 page.route('**/api/state/pref',pref)
 page.evaluate('Auth.flushLearning()');assert page.evaluate('Auth.pendingLearning()')==0
 page.reload();page.wait_for_function('Auth.state.ready')
 assert page.evaluate('LearningStore.forCourse("puzzle-sessions-v1").session().ply')==2
 assert len(page.evaluate('LearningStore.forCourse("tactics-v1").schedule("one").events'))==1


def test_pending_learning_never_crosses_account_boundary(page,app_url):
 mock_account(page,fail=True);ready(page,app_url)
 page.evaluate('LearningStore.forCourse("tactics-v1").attempt("private","one","independent","Nf3")')
 page.wait_for_function('Object.keys(Store.sync.pending("alice")).includes("learning:v2:tactics-v1:attempt:private")')
 page.unroute('**/api/auth/me');mock_account(page,uid='bob');page.reload();page.wait_for_function('Auth.state.ready')
 assert page.evaluate('Store.sync.owner()')=='bob'
 assert page.evaluate('LearningStore.forCourse("tactics-v1").records()')=={}
 assert page.evaluate('!!Store.sync.pending("alice")["learning:v2:tactics-v1:attempt:private"]')


def test_later_day_pattern_recall_and_milestone_are_real_and_idempotent(page,app_url):
 ready(page,app_url)
 idea=CATALOG['lessons'][0]
 page.evaluate('''(id)=>{const root='learning:v2:patterns-v1:';
 Store.prefs.set(root+'enrol:'+id,{at:Date.now()-2*86400000});
 LearningStore.forCourse('patterns-v1').complete(id);}''',idea['id'])
 page.locator('[data-puzzle-queue=patterns]').click()
 page.wait_for_function('Puzzles.info()?.mode==="recall"')
 solve(page,keyboard=True)
 assert page.evaluate('(id)=>LearningStore.forCourse("patterns-v1").schedule(id).streak',idea['id'])==1
 assert any(a['id']=='later-recall' for a in page.evaluate('Journey.achievements()'))
 before=page.evaluate('Journey.achievements()')
 page.reload();assert page.evaluate('Journey.achievements()')==before


def test_stale_tab_blocks_learning_before_it_touches_another_accounts_local_copy(page,app_url):
 mock_account(page,uid='alice');ready(page,app_url)
 page.unroute('**/api/auth/me');mock_account(page,uid='bob')
 page.evaluate('''()=>{Store.sync.own('bob');LearningStore.forCourse('tactics-v1').attempt('stale-tab','one','independent','Nf3');}''')
 page.wait_for_function('window.Auth?.state.ready && window.Auth.state.user?.id==="bob"')
 assert not page.evaluate('Store.prefs.get("learning:v2:tactics-v1:attempt:stale-tab")')


def test_completed_guided_revisits_count_as_work_but_reopening_recaps_does_not(page,app_url):
 ready(page,app_url)
 result=page.evaluate('''()=>{
 const l=LearningStore.forCourse('patterns-v1'), originalNow=Date.now;
 const completed=l.saveSession({id:'guided-revisit',mode:'lesson',stage:'recap',finished:true});
 const first=Journey.weekly().count;
 try {Date.now=()=>originalNow()+86400000;l.saveSession({...completed,completedAt:undefined});}
 finally{Date.now=originalNow;}
 return {first,count:Journey.weekly().count,saved:l.checkpoints()[0],at:completed.completedAt};
 }''')
 assert result['first']==result['count']==1
 assert result['saved']['completedAt']==result['at']


def test_content_update_restarts_the_same_lesson_without_erasing_earlier_attempts(page,app_url):
 ready(page,app_url)
 idea=CATALOG['lessons'][0];puzzle=PUZZLES[idea['puzzle']]
 # Seed a checkpoint from a previous content version and genuine older evidence.
 page.evaluate('''([puzzle,idea])=>{
 const l=LearningStore.forCourse('puzzle-sessions-v1');
 l.saveSession({id:'older-content',puzzle:puzzle.id,version:0,mode:'lesson',lesson:idea.id,queue:'theme',stage:'frame1',ply:0,help:0,misses:0,played:[]});
 LearningStore.forCourse('tactics-v1').attempt('past-attempt',puzzle.id,'hinted','');
 }''',[puzzle,idea])
 page.reload();page.locator('[data-puzzle-action=resume]').click()
 expect(page.locator('[data-puzzle-action=select-piece]')).to_be_visible()
 info=page.evaluate('Puzzles.info()')
 assert info['mode']=='lesson' and info['lesson']==idea['id'] and info['version']==1
 assert info['id']!='older-content'
 assert len(page.evaluate('(id)=>LearningStore.forCourse("tactics-v1").records()',puzzle['id']))==1
 expect(page.locator('#puzzleFeedback')).to_contain_text('earlier practice record is safe')


def test_pack_download_failure_can_retry_and_navigation_cancels_stale_presentation(page,app_url):
 ready(page,app_url)
 page.route('**/puzzle-packs/forks.json',lambda r:r.abort())
 page.locator('[data-puzzle-theme=forks]').click()
 expect(page.locator('#puzzleLibrary [role=alert]')).to_contain_text('fetch')
 page.unroute('**/puzzle-packs/forks.json')
 page.locator('[data-puzzle-action=retry-load]').click();expect(page.locator('#puzzleSession')).to_be_visible()
 # Hold a different pack while the user navigates away from its loading screen.
 pending=[];page.route('**/puzzle-packs/pins.json',lambda r:pending.append(r))
 page.evaluate('void Puzzles.start(PuzzleCatalog.puzzles.find(p=>p.theme==="pins").id)')
 page.wait_for_timeout(100)
 page.locator('#exploreSections a[href="#explore/path"]').click()
 assert pending
 pending[0].fulfill(json=PACKS['pins']);page.wait_for_timeout(100)
 expect(page.locator('#viewPath')).to_be_visible();expect(page.locator('#puzzleSession')).to_be_hidden()


def test_cleared_private_profile_boots_cleanly_after_signout_or_account_deletion(page,app_url):
 ready(page,app_url)
 page.locator('#openLearningProfile').click();page.locator('[name=nickname]').fill('Private name');page.locator('#learningProfileForm [type=submit]').click()
 assert page.evaluate('Journey.settings().nickname')=='Private name'
 page.evaluate('Store.forget()');page.reload();page.wait_for_function('Auth.state.ready && window.Journey')
 assert page.evaluate('Journey.settings().nickname')==''
 page.locator('#openLearningProfile').click();expect(page.locator('[name=nickname]')).to_have_value('')
