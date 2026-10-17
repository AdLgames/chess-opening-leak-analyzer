"""The expanded learning loop: both sides, explanations, model games and real data."""
import chess
import chess.engine
import pytest
from playwright.sync_api import expect

from chessopening.engine import find_engine
from test_training import ready, answer, play


def choose_course(page, course_id):
    course = page.evaluate('(id) => OpeningCourses.find(c => c.id === id)',course_id)
    page.evaluate('App.go("explore")')
    page.locator(f'[data-opening="{course["opening"]}"]').click()
    expect(page.locator('#italianCourse')).to_contain_text(course['title'].upper())
    return course


def complete_chapter(page, course, chapter_id):
    chapter = next(c for c in course['chapters'] if c['id']==chapter_id)
    cards = {c['id']:c for c in course['cards']}
    page.locator(f'[data-course-chapter="{chapter_id}"]').click()
    for i,key in enumerate(chapter['cards']):
        expect(page.locator('[data-training="hint"]')).to_be_enabled()
        answer(page,cards[key])
        page.locator('[data-training="next"]').click()
    expect(page.locator('#trainingTitle')).to_have_text('Chapter studied')
    return chapter


@pytest.mark.parametrize('course_id,chapter_id',[
    ('italian-v1','early-deviation'),('italian-v1','hungarian'),('italian-v1','central-break'),
    ('caro-v1','essentials'),('caro-v1','advance'),('caro-v1','exchange'),('caro-v1','bishop-safety'),('caro-v1','tactics'),
    ('qgd-v1','essentials'),('qgd-v1','exchange'),('qgd-v1','orthodox'),('qgd-v1','counterplay'),('qgd-v1','elephant'),
])
def test_every_new_chapter_can_be_learned_and_saved(page,app_url,course_id,chapter_id):
    ready(page,app_url)
    course = choose_course(page,course_id)
    chapter = complete_chapter(page,course,chapter_id)
    stats = page.evaluate('(c) => LearningStore.forCourse(c.id).summary(c.cards)',course)
    assert len(stats['schedules']) == len(chapter['cards'])
    assert stats['attempts'] == []
    page.locator('[data-training="save-line"]').click()
    expect(page.locator('#trainingFeedback')).to_contain_text('Saved on this device')
    assert page.evaluate('Store.repertoire.committed()[0].color') == course['side']
    page.locator('[data-training="recall-chapter"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    expect(page.locator('#libTurn')).to_have_text(course['side'].capitalize()+' to move')
    assert page.locator('#libBoard .cb-sq').first.get_attribute('data-square') == ('h1' if course['side']=='black' else 'a8')


def test_authored_coach_explains_and_demonstrates_a_concrete_mistake_without_engine(page,app_url):
    ready(page,app_url)
    page.locator('[data-course-chapter="essentials"]').click()
    cards = page.evaluate('ItalianCourse.cards')
    for card in cards[:2]:
        expect(page.locator('[data-training="hint"]')).to_be_enabled()
        answer(page,card);page.locator('[data-training="next"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    page.route('**/api/engine',lambda r:r.abort())
    play(page,chess.Move.from_uci('f3e5'))
    expect(page.locator('#trainingFeedback')).to_contain_text('defended by the knight on c6')
    expect(page.locator('.coach-portrait')).to_be_visible()
    page.locator('[data-training="show-why"]').click()
    expect(page.locator('.coach-evidence')).to_have_text('Course continuation')
    page.locator('[data-training="demonstrate"]').click()
    expect(page.locator('[data-training="back-task"]')).to_be_enabled()
    assert 'black knight' in page.locator('#libBoard [data-square="e5"]').get_attribute('aria-label').lower()
    page.locator('[data-training="back-task"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page,cards[2])
    page.locator('[data-training="toggle-coach"]').click()
    expect(page.locator('.coach-portrait')).to_be_hidden()
    page.reload()
    page.locator('[data-training="resume"]').click()
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    expect(page.locator('.coach-portrait')).to_be_hidden()


@pytest.mark.parametrize('course_id',['italian-v1','caro-v1','qgd-v1'])
def test_model_game_replays_key_ideas_and_resumes_without_recall_credit(page,app_url,course_id):
    ready(page,app_url)
    course = choose_course(page,course_id)
    game = page.evaluate('(id)=>ModelGames.find(g=>g.course===id)',course_id)
    page.locator(f'[data-model-game="{game["id"]}"]').click()
    expect(page.locator('[data-training="game-key"]')).to_be_enabled()
    page.locator('[data-training="game-key"]').click()
    expect(page.locator('[data-training="game-key"]')).to_be_enabled()
    expect(page.locator('#trainingFeedback')).to_contain_text(game['notes'][1]['text'])
    index = page.evaluate('(id)=>LearningStore.forCourse(id).session().index',course_id)
    assert index == game['notes'][1]['ply']
    page.reload()
    if course_id=='italian-v1': page.locator('[data-training="resume"]').click()
    else: page.locator(f'[data-resume-course="{course_id}"]').click()
    expect(page.locator('[data-training="game-key"]')).to_be_enabled()
    assert page.evaluate('(id)=>LearningStore.forCourse(id).session().index',course_id) == index
    assert page.evaluate('(c)=>LearningStore.forCourse(c.id).summary(c.cards).attempts',course) == []
    expect(page.locator('.model-source')).to_have_attribute('href',game['source'])


def test_scoped_book_gaps_become_real_prepared_responses(page,app_url):
    ready(page,app_url)
    page.evaluate('App.go("repertoire")')
    page.locator('#scanGaps').click()
    expect(page.locator('.gap-summary')).to_be_visible()
    expect(page.locator('#gapResults')).to_contain_text('0 of')
    first = page.locator('[data-gap-learn]').first
    expect(first).to_be_visible()
    first.click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    session = page.evaluate('LearningStore.session()')
    card = page.evaluate('(id)=>OpeningCourses[0].cards.find(c=>c.id===id)',session['queue'][0])
    answer(page,card)
    page.locator('[data-training="save-choice"]').click()
    expect(page.locator('#trainingFeedback')).to_contain_text('prepared response')
    page.evaluate('App.go("repertoire")')
    page.locator('#scanGaps').click()
    expect(page.locator('.gap-summary')).to_contain_text('1 of')
    assert len(page.evaluate('Store.repertoire.committed()')) == 1


def test_sample_report_findings_become_saved_and_reviewable_exercises(page,app_url):
    ready(page,app_url)
    page.evaluate('App.go("dashboard")')
    page.locator('#sampleBtn').click()
    expect(page.locator('#report')).to_be_visible(timeout=30000)
    page.evaluate('App.go("progress")')
    expect(page.locator('#personalTraining')).to_contain_text('Sample game exercises')
    button = page.locator('#personalTraining [data-personal-finding]').first
    expect(button).to_be_visible()
    button.click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    expect(page.locator('#trainingPanel')).to_contain_text('sample report')
    course = page.evaluate('Preparation.personalCourse()')
    card = course['cards'][0]
    board = chess.Board(card['startFen'])
    play(page,board.parse_san(card['move']))
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    page.locator('[data-training="next"]').click()
    page.locator('[data-training="recall-chapter"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    play(page,board.parse_san(card['move']))
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    stats = page.evaluate('(c)=>LearningStore.forCourse(c.id).summary(c.cards)',course)
    assert stats['independent'] == 1
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).attempts.length') == 0
    page.reload()
    assert page.evaluate('Preparation.personalCourse().cards[0].id') == card['id']


def test_black_session_resume_and_five_moves_use_correct_side(page,app_url):
    ready(page,app_url)
    course = choose_course(page,'caro-v1')
    chapter = complete_chapter(page,course,'essentials')
    page.locator('[data-training="play"]').click()
    page.wait_for_function('LearningStore.forCourse("caro-v1").session()?.playMoves.length===1')
    page.reload()
    page.locator('[data-resume-course="caro-v1"]').click()
    page.wait_for_function('document.querySelector("#libTurn").textContent==="Black to move"')
    expect(page.locator('#trainingPanel')).to_contain_text('Stockfish')
    last = next(c for c in course['cards'] if c['id']==chapter['cards'][-1])
    with chess.engine.SimpleEngine.popen_uci(find_engine()) as engine:
        for i in range(5):
            current = page.evaluate('LearningStore.forCourse("caro-v1").checkpoints().find(s=>s.mode==="play")')
            board = chess.Board()
            for san in last['line']+[last['move']]: board.push_san(san)
            for uci in current['playMoves']: board.push_uci(uci)
            assert board.turn == chess.BLACK
            play(page,engine.play(board,chess.engine.Limit(depth=6)).move)
            page.wait_for_function('(n)=>LearningStore.forCourse("caro-v1").checkpoints().find(s=>s.mode==="play").playMoves.length===n',arg=(i+1)*2+1)
    expect(page.locator('#trainingTitle')).to_have_text('Position played')
    assert page.evaluate('(c)=>LearningStore.forCourse(c.id).summary(c.cards).practical',course) == 1


def test_green_board_and_wood_preference_survive_reload(page,app_url):
    ready(page,app_url)
    expect(page.locator('html')).to_have_attribute('data-board','green')
    page.locator('.board-tools > summary').click()
    page.locator('#boardPalette').select_option('wood')
    page.reload()
    expect(page.locator('html')).to_have_attribute('data-board','wood')


def test_coach_distinguishes_a_sound_alternative_using_the_real_engine(page,app_url):
    ready(page,app_url)
    page.locator('[data-course-chapter="essentials"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    play(page,chess.Move.from_uci('d2d4'))
    page.locator('[data-training="show-why"]').click()
    expect(page.locator('.coach-evidence')).to_have_text('Stockfish · depth 12',timeout=30000)
    expect(page.locator('#trainingFeedback')).to_contain_text('close to the engine’s preferred move')
    page.locator('[data-training="demonstrate"]').click()
    expect(page.locator('[data-training="back-task"]')).to_be_enabled()


def test_unavailable_coach_engine_keeps_the_lesson_usable(page,app_url):
    ready(page,app_url)
    page.locator('[data-course-chapter="essentials"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    play(page,chess.Move.from_uci('d2d4'))
    page.route('**/api/engine',lambda r:r.fulfill(status=503,json={'detail':'Engine unavailable'}))
    page.locator('[data-training="show-why"]').click()
    expect(page.locator('#trainingFeedback')).to_contain_text('could not verify')
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page,page.evaluate('ItalianCourse.cards[0]'))
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).independent') == 0


def test_unavailable_book_does_not_invent_coverage(page,app_url):
    ready(page,app_url)
    def no_book(route):
        response = route.fetch()
        data = response.json();data['book'] = None
        route.fulfill(json=data)
    page.route('**/api/position?san=*',no_book)
    page.evaluate('App.go("repertoire")')
    page.locator('#scanGaps').click()
    expect(page.locator('#gapResults')).to_contain_text('No opening-book data')
    assert page.evaluate('Store.repertoire.committed()') == []


def test_invalid_report_answer_is_rejected_without_saving_an_exercise(page,app_url):
    ready(page,app_url)
    page.evaluate('App.go("progress")')
    page.evaluate('''(fen)=>window.dispatchEvent(new CustomEvent('chess:report',{detail:{demo:false,rows:[{
      fen,player_color:'white',engine_best_1:'Qz9',your_move:'e4',your_games:4,opening:'Invalid report'}]}}))''',chess.STARTING_FEN)
    page.locator('#personalTraining [data-personal-finding]').click()
    expect(page.locator('#personalTrainingStatus')).to_contain_text('not legal')
    assert page.evaluate('Preparation.personalCourse()') is None


@pytest.mark.parametrize('width,height',[(360,800),(390,844)])
def test_reference_style_review_summary_keeps_continue_above_mobile_navigation(page,app_url,width,height):
    page.set_viewport_size({'width':width,'height':height})
    ready(page,app_url)
    course = choose_course(page,'caro-v1')
    chapter = complete_chapter(page,course,'tactics')
    page.locator('[data-training="recall-chapter"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    card = next(c for c in course['cards'] if c['id']==chapter['cards'][0])
    answer(page,card)
    page.locator('[data-training="next"]').click()
    expect(page.locator('.review-summary')).to_contain_text('100% first attempt recall')
    expect(page.locator('.review-summary')).to_contain_text('in 1 day')
    box = page.locator('[data-training="done"]').bounding_box()
    assert box['y'] + box['height'] <= height - 62


def test_same_position_in_sample_and_personal_reports_keeps_distinct_sources(page,app_url):
    ready(page,app_url)
    page.evaluate('App.go("dashboard")');page.locator('#sampleBtn').click()
    expect(page.locator('#report')).to_be_visible(timeout=30000)
    page.evaluate('App.go("progress")')
    page.locator('#personalTraining [data-personal-finding]').first.click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    first = page.evaluate('Preparation.personalCourse().cards[0]')
    board = chess.Board(first['startFen']);play(page,board.parse_san(first['move']))
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    page.locator('[data-training="pause"]').click()
    page.evaluate('App.go("progress")')
    page.evaluate('window.dispatchEvent(new CustomEvent("chess:report",{detail:{...App.reportContext(),demo:false}}))')
    page.locator('#personalTraining [data-personal-finding]').first.click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    cards = page.evaluate('Preparation.personalCourse().cards')
    assert len(cards) == 2 and cards[0]['id'] != cards[1]['id']
    assert {c['report']['demo'] for c in cards} == {False,True}
    assert page.evaluate('(id)=>!!LearningStore.forCourse("personal-v1").schedule(id)',first['id'])


def test_coach_explains_checkmate_without_reporting_a_fictitious_pawn_loss(page,app_url):
    ready(page,app_url)
    text = page.evaluate('''async()=>{
      const pos=await LeakBoard.position(null,null,['f3','e5']);
      const move=pos.legal.find(m=>m.san==='g4');
      return (await Coach.explain(pos,move,null)).text;
    }''')
    assert 'Qh4#' in text and 'checkmate' in text
    assert 'pawns compared' not in text


def test_concurrent_book_positions_and_searches_keep_correct_results(page,app_url):
    ready(page,app_url)
    results = page.evaluate('''async()=>{
      const paths=['/api/position?san=e4%20e5','/api/position?san=d4%20d5',
        '/api/position?san=e4%20c6','/api/openings?q=Italian'];
      return Promise.all(Array.from({length:12},()=>paths).flat().map(async(path)=>{
        const response=await fetch(path);
        return {path,status:response.status,data:await response.json()};
      }));
    }''')
    for result in results:
        assert result['status'] == 200
        if '/position?' in result['path']:
            assert result['data']['book'] is not None
            assert result['data']['turn'] == 'white'
            assert result['data']['legal']
        else:
            assert result['data']['results']
