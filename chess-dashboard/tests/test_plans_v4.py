"""V4 works through real touch/keyboard boards, resume, account queues and old flows."""
import json
from pathlib import Path
import pytest
import chess
from playwright.sync_api import expect

DATA=json.loads((Path(__file__).resolve().parents[1]/'public/app/italian-plans.js').read_text().split('window.ItalianPlans = ')[1].rstrip(';\n'))
SCENES={s['id']:s for s in DATA['scenes']}
ROOT='learning:v2:italian-plans-v1:'


def ready(page,app_url,route='today'):
    page.goto(app_url+'/app/#'+route)
    page.wait_for_function('window.Plans && Auth.state.ready')
    expect(page.locator('#libBoard')).to_have_attribute('aria-busy','false')


def start(page,app_url):
    ready(page,app_url,'explore')
    page.locator('#planExplore [data-plan=start]').click()
    expect(page.locator('#planTitle')).to_have_text('Make room for a plan')
    page.locator('[data-plan=frame-next]').click()
    page.locator('[data-plan=try]').click()


def play(page,uci,keyboard=False):
    a=page.locator(f'#libBoard .cb-sq[data-square={uci[:2]}]')
    b=page.locator(f'#libBoard .cb-sq[data-square={uci[2:4]}]')
    if keyboard:
        a.focus();a.press('Enter');b.focus();b.press('Enter')
    else:
        a.click();b.click()


def expect_board(page,fen):
    expected={chess.square_name(sq):piece.symbol() for sq,piece in chess.Board(fen).piece_map().items()}
    actual=page.locator('#libBoard .cb-sq').evaluate_all("els=>Object.fromEntries(els.map(e=>[e.dataset.square,e.querySelector('.cb-piece').dataset.piece]).filter(([,p])=>p))")
    assert actual==expected


def finish(page,alternate=False):
    while True:
        session=page.evaluate('Plans.info()')
        if session['finished']:return session
        scene=SCENES[session['queue'][session['index']]]
        answer=scene['answers'][-1 if alternate else 0]
        play(page,answer['uci'],True)
        expect_board(page,answer['after']['fen'])
        page.locator('[data-plan=response]').click()
        expect_board(page,answer['response']['fen'])
        page.locator('[data-plan=next]').click()


def account(page,user=None,prefs=None):
    user=user or {'id':'v4-owner','name':'Player','accounts':[]}
    page.route('**/api/auth/me',lambda r:r.fulfill(json={'database':True,'user':user,'methods':{'email':True,'lichess':True}}))
    page.route('**/api/state',lambda r:r.fulfill(json={'runs':[],'repertoire':[],'drills':{},'prefs':prefs or {}}))
    page.route('**/api/state/import',lambda r:r.fulfill(json={'runs':[],'repertoire':[],'drills':{},'prefs':r.request.post_data_json.get('prefs',{})}))


@pytest.mark.parametrize('alternate',[False,True])
def test_complete_plan_accepts_both_preparations_and_keeps_game_evidence_separate(page,app_url,alternate):
    start(page,app_url)
    session=finish(page,alternate)
    assert len(session['results'])==4 and all(r['outcome']=='independent' for r in session['results'])
    expect(page.locator('#trainingPanel')).to_contain_text('First try, without direct help')
    page.locator('#planReflection').select_option('threat')
    page.locator('[data-plan=save-focus]').click();page.locator('[data-plan=done]').click()
    page.locator('[data-view=repertoire]:visible').first.click()
    expect(page.locator('#planRepertoire')).to_contain_text('When a central pawn attacks your bishop')
    assert page.evaluate('Store.repertoire.all()')==[]
    page.locator('[data-view=progress]:visible').first.click()
    expect(page.locator('#planProgress')).to_contain_text('Not measured yet')
    assert page.evaluate('LearningStore.forCourse("italian-plans-v1").checkpoints()[0].reflection')=='threat'
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).attempts')==[]


def test_fresh_challenge_does_not_show_answers_and_help_survives_reload(page,app_url):
    start(page,app_url)
    for s in DATA['scenes'][:-1]:
        play(page,s['answers'][0]['uci']);page.locator('[data-plan=next]').click()
    expect(page.locator('#planTitle')).to_contain_text('Your decision')
    expect(page.locator('#libBoard .cb-arrow')).to_have_count(0)
    expect(page.locator('#libBoard .cb-circle')).to_have_count(0)
    page.locator('[data-plan=hint]').click()
    expect(page.locator('#libBoard .cb-arrow')).to_have_count(2)
    prior=page.evaluate('Plans.info()');page.reload()
    page.locator('#planToday [data-plan=resume]').click()
    assert page.evaluate('Plans.info().id')==prior['id']
    assert page.evaluate('Plans.info().helped')
    finish(page)
    expect(page.locator('#trainingPanel')).to_contain_text('Explored with help or another attempt')
    assert page.evaluate('Plans.info().results.at(-1).outcome')=='hinted'


def test_consequence_preserves_the_decision_and_counts_as_help(page,app_url):
    start(page,app_url)
    play(page,'e1g1');page.locator('[data-plan=next]').click()
    play(page,'d3d4');page.locator('[data-plan=why]').click()
    expect_board(page,SCENES['prepare-break']['wrong']['d4']['position']['fen'])
    page.reload();page.locator('#planToday [data-plan=resume]').click()
    expect(page.locator('#planFeedback')).to_contain_text('no pawn on c3')
    page.locator('[data-plan=back]').click();play(page,'c2c3')
    assert page.evaluate('Plans.info().results.at(-1).outcome')=='hinted'


def test_reveal_and_repeated_actions_never_create_independent_or_duplicate_results(page,app_url):
    start(page,app_url)
    page.locator('[data-plan=reveal]').click()
    first=page.evaluate('Plans.info()')
    page.evaluate("document.dispatchEvent(new CustomEvent('irrelevant'));Plans.render()")
    assert page.evaluate('Plans.info().results.length')==1
    records=page.evaluate('LearningStore.forCourse("italian-plans-v1").records()')
    attempts=[v for k,v in records.items() if ':attempt:' in k]
    assert len(attempts)==1 and attempts[0]['outcome']=='revealed'
    page.reload();page.locator('#planToday [data-plan=resume]').click()
    assert page.evaluate('Plans.info().answer')==first['answer']
    expect(page.locator('[data-plan=response]')).to_be_visible()


def test_offline_session_uses_verified_positions_and_preserves_previous_lessons_and_lines(page,app_url):
    ready(page,app_url)
    page.evaluate('Store.prefs.set("learning:v2:italian-v1:sentinel",{keep:true})')
    page.locator('[data-course-chapter=essentials]').click()
    prior=page.evaluate('Training.info().id')
    page.locator('[data-training=pause]').click()
    page.locator('#planToday [data-plan=start]').click()
    page.locator('[data-plan=frame-next]').click();page.locator('[data-plan=try]').click()
    page.route('**/api/position?**',lambda r:r.abort())
    page.context.set_offline(True)
    finish(page,True)
    assert page.evaluate('Store.prefs.get("learning:v2:italian-v1:sentinel").keep')
    assert page.evaluate('(id)=>LearningStore.checkpoints().some(c=>c.id===id && !c.finished)',prior)
    page.context.set_offline(False)


def test_leaving_training_or_starting_a_course_restores_one_board_controller(page,app_url):
    start(page,app_url)
    page.locator('[data-view=explore]:visible').first.click()
    assert not page.evaluate('Plans.active()')
    page.locator('[data-opening=caro]').click()
    page.locator('[data-course-chapter=essentials]').click()
    expect(page.locator('[data-training=hint]')).to_be_enabled()
    assert page.evaluate('Training.info().course')=='caro-v1'
    assert not page.evaluate('Plans.active()')


@pytest.mark.parametrize('change',['demo','side','fen','sample','drop'])
def test_personal_focus_rejects_unsupported_or_insufficient_report_evidence(page,app_url,change):
    ready(page,app_url)
    row={'fen':SCENES['answer-strike']['position']['fen'],'your_move':'O-O','your_games':4,'eval_drop_pawns':4.0,'player_color':'white'}
    ctx={'summary':{'games':20},'rows':[row],'demo':False}
    if change=='demo':ctx['demo']=True
    if change=='side':row['player_color']='black'
    if change=='fen':row['fen']=SCENES['fresh-break']['position']['fen']
    if change=='sample':row['your_games']=0
    if change=='drop':row.pop('eval_drop_pawns')
    assert page.evaluate('(ctx)=>Plans.matchFinding(ctx)',ctx) is None


def test_exact_personal_finding_starts_with_its_provenance_and_correct_scene(page,app_url):
    ready(page,app_url)
    ctx={'summary':{'games':20},'demo':False,'rows':[{'fen':SCENES['answer-strike']['position']['fen'],'your_move':'O-O','your_games':4,'eval_drop_pawns':4.0,'player_color':'white'}]}
    found=page.evaluate('(ctx)=>Plans.matchFinding(ctx)',ctx)
    assert found['scene']=='answer-strike' and found['games']==4
    page.evaluate('(ctx)=>{App.reportContext=()=>ctx;Plans.render()}',ctx)
    page.locator('#planToday [data-plan=finding]').click()
    expect(page.locator('#planFeedback')).to_contain_text('4 games at this exact position')
    page.locator('[data-plan=idea]').click();page.locator('[data-plan=frame-next]').click();page.locator('[data-plan=try]').click()
    expect(page.locator('#planTitle')).to_have_text('Their threat comes first')
    assert page.evaluate('Plans.info().source.demo') is False


@pytest.mark.parametrize('width,height',[(360,800),(390,844),(768,1024),(1440,1000)])
def test_phone_tablet_and_desktop_keep_board_navigation_and_controls_usable(page,app_url,width,height):
    page.set_viewport_size({'width':width,'height':height});start(page,app_url)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.locator('#nav [data-view]').count()==4
    assert page.locator('#planToday').is_hidden() and page.locator('#dailyInvite').is_hidden()
    box=page.locator('#libBoard').bounding_box()
    assert box['width']>=min(width-30,320)
    assert abs(box['width']-box['height'])<2
    if width<=860:
        page.locator('[data-plan=hint]').click()
        box=page.locator('#libBoard').bounding_box()
        assert box['y']>=50 and box['y']+box['height']<=page.locator('#tabbar').bounding_box()['y']
    play(page,'e1g1',True)
    expect(page.locator('[data-plan=response]')).to_be_enabled()
    page.locator('[data-plan=pause]').click()
    expect(page.locator('#libBoard')).to_have_attribute('aria-label','Explorer board')


def test_account_queue_keeps_the_new_checkpoint_and_assisted_outcome_across_reload(page,app_url):
    account(page)
    page.route('**/api/state/pref',lambda r:r.fulfill(status=503,json={'error':'offline'}))
    start(page,app_url);page.locator('[data-plan=hint]').click();play(page,'e1g1')
    page.wait_for_function('Object.keys(Store.sync.pending("v4-owner")).some(k=>k.startsWith("learning:v2:italian-plans-v1:attempt:"))')
    prior=page.evaluate('Plans.info().id')
    page.reload();page.locator('#planToday [data-plan=resume]').click()
    assert page.evaluate('Plans.info().id')==prior
    assert page.evaluate('Plans.info().results[0].outcome')=='hinted'
    assert page.evaluate('Object.keys(Store.sync.pending("v4-owner")).some(k=>k.startsWith("learning:v2:italian-plans-v1:checkpoint:"))')


def test_saved_focus_can_yield_to_the_existing_daily_routine(page,app_url):
    start(page,app_url);finish(page)
    page.locator('[data-plan=save-focus]').click();page.locator('[data-plan=done]').click()
    expect(page.locator('#dailyInvite')).to_be_hidden()
    page.locator('#planToday [data-plan=daily]').click()
    expect(page.locator('[data-training=visual-next]')).to_be_enabled()
    assert not page.evaluate('Plans.active()')
    page.locator('[data-training=pause]').click()
    expect(page.locator('#dailyInvite')).to_be_visible()
    assert page.evaluate('Store.prefs.get("learning:v2:italian-plans-v1:focus").home') is False
    assert len(page.evaluate('Plans.info().results'))==4


def test_revisit_memory_uses_real_prior_results_and_old_versions_remain_untouched(page,app_url):
    start(page,app_url);page.locator('[data-plan=hint]').click();finish(page)
    page.locator('[data-plan=done]').click()
    page.evaluate('LearningStore.forCourse("italian-plans-v1").saveSession({id:"other-content-version",mode:"plan",version:999,finished:false})')
    page.locator('#planToday [data-plan=start]').click()
    page.locator('[data-plan=frame-next]').click();page.locator('[data-plan=try]').click()
    expect(page.locator('.plan-memory')).to_contain_text('Last time you explored this with help')
    assert page.evaluate('LearningStore.forCourse("italian-plans-v1").checkpoints().find(c=>c.id==="other-content-version").version')==999


def test_blocked_storage_is_reported_without_breaking_the_session(page,app_url):
    page.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('disabled')}})")
    start(page,app_url);play(page,'e1g1')
    expect(page.locator('.training-storage')).to_contain_text('Progress stays in this tab only')
    assert page.evaluate('Plans.info().results.length')==1


@pytest.mark.parametrize('path',['/','/learn/italian-game/'])
def test_public_entry_starts_the_plan_without_signup_or_game_import(page,app_url,path):
    page.route('**/api/auth/me',lambda r:r.fulfill(json={'database':True,'user':None,'methods':{'email':True,'lichess':True}}))
    requests=[];page.on('request',lambda r:requests.append(r.url))
    page.goto(app_url+path)
    page.locator('a[href="/app/?plan=italian#today"]').first.click()
    expect(page.locator('#planTitle')).to_have_text('Make room for a plan')
    assert page.evaluate('Plans.active()')
    expect(page.locator('#authDialog')).to_be_hidden()
    assert not any('/api/analy' in url or '/auth/email/request' in url for url in requests)
