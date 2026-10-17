"""Daily plans and visual teaching use real course, account and Stockfish flows."""
import chess
import chess.engine
import pytest
from playwright.sync_api import expect
from chessopening.engine import find_engine
from test_training import ready,answer,play


def start_daily(page,app_url,focus='italian-v1'):
    ready(page,app_url)
    page.locator('#dailySettings > summary').click()
    page.locator('#dailyFocus').select_option(focus)
    page.locator('[data-daily="start"]').click()
    expect(page.locator('[data-training="visual-next"]')).to_be_enabled()


def exit_visual(page):
    page.locator('[data-training="visual-close"]').first.click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()


@pytest.mark.parametrize('minutes,cap,new_count',[(5,3,1),(10,6,2),(15,10,3)])
def test_planner_uses_real_due_positions_and_an_honest_size_budget(page,app_url,minutes,cap,new_count):
    ready(page,app_url)
    page.evaluate('''()=>{
      Store.prefs.set('dailyFocus','caro-v1');
      OpeningCourses[0].cards.slice(0,12).forEach((c,i)=>Store.prefs.set('learning:v2:italian-v1:enrol:'+c.id,{at:Date.now()-3*86400000+i*1000}));
    }''')
    plan=page.evaluate('(minutes)=>DailySession.build(minutes)',minutes)
    assert plan['reviews']==cap and plan['newPositions']==new_count
    assert plan['steps'][0]['queue']==page.evaluate('(n)=>OpeningCourses[0].cards.slice(0,n).map(c=>c.id)',cap)
    assert plan['steps'][-1]['mode']=='play' and plan['focus']=='caro-v1'
    assert plan['steps'][-2]['queue']==page.evaluate('(n)=>OpeningCourses[1].cards.slice(0,n).map(c=>c.id)',new_count)


@pytest.mark.parametrize('focus',['italian-v1','caro-v1','qgd-v1'])
def test_new_session_diagram_resumes_exactly_then_returns_to_the_exercise(page,app_url,focus):
    start_daily(page,app_url,focus)
    assert page.locator('#libBoard .cb-circle').count()>0
    page.locator('[data-training="visual-next"]').click()
    expect(page.locator('#trainingTitle')).to_have_text('See the board control')
    expect(page.locator('[data-training="visual-next"]')).to_be_enabled()
    page.reload();page.locator('[data-daily="resume"]').click()
    expect(page.locator('#trainingTitle')).to_have_text('See the board control')
    expect(page.locator('[data-training="visual-next"]')).to_be_enabled()
    exit_visual(page)
    assert page.locator('#libBoard .cb-circle').count()==0
    session=page.evaluate('Training.info()')
    card=page.evaluate('(s)=>OpeningCourses.find(c=>c.id===s.course).cards.find(c=>c.id===s.queue[0])',session)
    answer(page,card)
    page.locator('[data-training="next"]').click()
    expect(page.locator('[data-daily="advance"]')).to_contain_text('Practical challenge')
    assert page.evaluate('(id)=>LearningStore.forCourse(id).completed("essentials")',focus) is False


def test_visual_hint_in_recall_is_assisted_and_cannot_award_credit_while_browsing(page,app_url):
    ready(page,app_url)
    page.evaluate("Store.prefs.set('learning:v2:italian-v1:enrol:knight',{at:Date.now()-2*86400000})")
    page.locator('[data-daily="start"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    page.locator('[data-training="visual"]').click()
    expect(page.locator('#trainingTitle')).to_have_text('Follow the move')
    assert page.locator('#libBoard .cb-arrow').first.get_attribute('d').count('L')==2
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).attempts.length')==0
    exit_visual(page)
    card=page.evaluate('ItalianCourse.cards.find(c=>c.id==="knight")')
    answer(page,card)
    summary=page.evaluate('LearningStore.summary(ItalianCourse.cards)')
    assert summary['independent']==0 and len(summary['attempts'])==1
    assert summary['attempts'][0]['outcome']=='hinted'


def test_daily_session_completes_with_real_five_move_stockfish_play_and_true_recap(page,app_url):
    start_daily(page,app_url)
    exit_visual(page)
    card=page.evaluate('OpeningCourses[0].cards[0]')
    answer(page,card);page.locator('[data-training="next"]').click();page.locator('[data-daily="advance"]').click()
    page.wait_for_function('Training.info().mode==="play" && document.querySelector("#libTurn").textContent==="White to move"')
    with chess.engine.SimpleEngine.popen_uci(find_engine()) as engine:
        for i in range(5):
            session=page.evaluate('Training.info()');board=chess.Board(card['afterFen'])
            for uci in session['playMoves']:board.push_uci(uci)
            assert board.turn==chess.WHITE
            play(page,engine.play(board,chess.engine.Limit(depth=4)).move)
            page.wait_for_function('(n)=>{const s=Training.info();return s.playerMoves===n && (s.finished || document.querySelector("#libTurn").textContent==="White to move")}',arg=i+1)
    expect(page.locator('[data-daily="advance"]')).to_contain_text('recap')
    page.locator('[data-daily="advance"]').click()
    expect(page.locator('.daily-recap')).to_contain_text('5 practical moves played against Stockfish')
    expect(page.locator('.daily-recap')).to_contain_text('1 position studied')
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).practical')==1
    page.locator('[data-daily="done"]').click()
    page.locator('[data-daily="recap"]').click()
    expect(page.locator('.daily-recap')).to_contain_text('5 practical moves')
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).practical')==1


def test_finishing_early_preserves_attempts_and_does_not_invent_completed_tasks(page,app_url):
    ready(page,app_url)
    page.evaluate("Store.prefs.set('learning:v2:italian-v1:enrol:centre',{at:Date.now()-2*86400000})")
    page.locator('[data-daily="start"]').click();expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page,page.evaluate('ItalianCourse.cards[0]'))
    page.locator('[data-daily="finish"]').click()
    expect(page.locator('.daily-recap')).to_contain_text('You finished early')
    expect(page.locator('.daily-recap')).to_contain_text('1 review answer')
    expect(page.locator('.daily-recap')).to_contain_text('0 practical moves')
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).independent')==1
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).practical')==0


def test_unavailable_engine_allows_an_honest_early_recap(page,app_url):
    start_daily(page,app_url);exit_visual(page)
    answer(page,page.evaluate('ItalianCourse.cards[0]'));page.locator('[data-training="next"]').click()
    page.route('**/api/engine',lambda r:r.fulfill(status=503,json={'detail':'Engine unavailable'}))
    page.locator('[data-daily="advance"]').click()
    expect(page.locator('#trainingPanel')).to_contain_text('Engine unavailable')
    page.locator('[data-daily="finish"]').click()
    expect(page.locator('.daily-recap')).to_contain_text('0 practical moves')
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).practical')==0


@pytest.mark.parametrize('width,height',[(360,800),(390,844),(1440,1000)])
def test_today_invitation_and_teaching_board_fit_the_available_layout(page,app_url,width,height):
    page.set_viewport_size({'width':width,'height':height});ready(page,app_url)
    button=page.locator('[data-daily="start"]').bounding_box()
    assert button['y']+button['height']<height-62
    if width==1440:
        board=page.locator('#libBoard').bounding_box();assert board['width']>600 and board['y']+board['height']<height
    page.locator('[data-daily="start"]').click()
    expect(page.locator('[data-training="visual-next"]')).to_be_enabled()
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    if width<=390:
        next_button=page.locator('[data-training="visual-next"]').bounding_box()
        assert next_button['y']+next_button['height']<=height-62


def test_mixed_course_reviews_resume_without_duplicate_credit_then_start_the_chosen_idea(page,app_url):
    ready(page,app_url)
    page.locator('#dailySettings > summary').click()
    page.locator('#dailyFocus').select_option('qgd-v1')
    page.evaluate('''()=>{
      [0,1].forEach((i)=>{const c=OpeningCourses[i];Store.prefs.set('learning:v2:'+c.id+':enrol:'+c.cards[0].id,{at:Date.now()-(3-i)*86400000});});
    }''')
    page.locator('[data-daily="start"]').click();expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page,page.evaluate('OpeningCourses[0].cards[0]'))
    page.reload();page.locator('[data-daily="resume"]').click()
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).independent')==1
    page.locator('[data-training="next"]').click();page.locator('[data-daily="advance"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    assert page.evaluate('Training.info().course')=='caro-v1'
    assert page.locator('#libBoard .cb-sq').first.get_attribute('data-square')=='h1'
    answer(page,page.evaluate('OpeningCourses[1].cards[0]'))
    page.locator('[data-training="next"]').click();page.locator('[data-daily="advance"]').click()
    expect(page.locator('[data-training="visual-next"]')).to_be_enabled()
    assert page.evaluate('Training.info().course')=='qgd-v1'
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).independent')==1


def test_daily_work_does_not_overwrite_an_existing_manual_lesson_checkpoint(page,app_url):
    ready(page,app_url)
    page.locator('[data-course-chapter="essentials"]').click();expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page,page.evaluate('ItalianCourse.cards[0]'));page.locator('[data-training="next"]').click();expect(page.locator('[data-training="hint"]')).to_be_enabled()
    original=page.evaluate('Training.info()')
    page.locator('[data-training="pause"]').click();page.locator('[data-daily="start"]').click()
    expect(page.locator('[data-training="visual-next"]')).to_be_enabled()
    page.locator('[data-training="pause"]').click();page.locator('[data-course-chapter="essentials"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    current=page.evaluate('Training.info()')
    assert current['id']==original['id'] and current['index']==original['index']
    assert not current.get('daily')


def test_black_teaching_circles_use_the_flipped_coordinates(page,app_url):
    start_daily(page,app_url,'caro-v1')
    page.locator('[data-training="visual-next"]').click()
    expect(page.locator('[data-training="visual-next"]')).to_be_enabled()
    circle=page.locator('#libBoard .cb-circle[data-square="d5"]')
    expect(circle).to_have_attribute('cx','45');expect(circle).to_have_attribute('cy','45')


def test_italian_tactic_shows_both_fork_targets_without_changing_the_learning_record(page,app_url):
    ready(page,app_url)
    card=page.evaluate('ItalianCourse.cards.find(c=>c.move==="Nxf7")')
    page.evaluate('(id)=>Training.focus("italian-v1",id)',card['id'])
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    page.locator('[data-training="visual"]').click()
    for i in range(2):
        expect(page.locator('[data-training="visual-next"]')).to_be_enabled();page.locator('[data-training="visual-next"]').click()
    expect(page.locator('#trainingTitle')).to_have_text('Two targets, one knight')
    expect(page.locator('#libBoard .cb-circle[data-square="d8"]')).to_be_visible()
    expect(page.locator('#libBoard .cb-circle[data-square="h8"]')).to_be_visible()
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).schedules.length')==0
