"""Italian learning journeys on the shared board and real chess/engine APIs."""
import io
import json
from datetime import datetime, timezone

import chess
import chess.engine
import chess.pgn
import pytest
from playwright.sync_api import expect

from chessopening.engine import find_engine

ROOT = 'learning:v2:italian-v1:'


def ready(page, app_url):
    page.goto(app_url + '/app/#today')
    expect(page.locator('#libBoard')).to_have_attribute('aria-busy', 'false')
    expect(page.locator('#italianCourse')).to_be_visible()


def task(page, chapter='essentials'):
    page.locator(f'[data-course-chapter="{chapter}"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()


def course(page):
    return page.evaluate('ItalianCourse')


def play(page, move):
    page.locator(f'#libBoard [data-square="{chess.square_name(move.from_square)}"]').click()
    page.locator(f'#libBoard [data-square="{chess.square_name(move.to_square)}"]').click()


def answer(page, card):
    board = chess.Board()
    for san in card['line']:
        board.push_san(san)
    play(page, board.parse_san(card['move']))
    expect(page.locator('[data-training="next"]')).to_be_enabled()


def complete(page, chapter='essentials'):
    content = course(page)
    cards = {c['id']: c for c in content['cards']}
    chosen = next(c for c in content['chapters'] if c['id'] == chapter)
    task(page, chapter)
    for i, key in enumerate(chosen['cards']):
        answer(page, cards[key])
        page.locator('[data-training="next"]').click()
        if i + 1 < len(chosen['cards']):
            expect(page.locator('[data-training="hint"]')).to_be_enabled()
    expect(page.locator('#trainingTitle')).to_have_text('Chapter studied')
    return content, chosen


@pytest.mark.parametrize('chapter', ['essentials','two-knights','f7-tactic','middlegame'])
def test_lessons_play_legal_moves_save_and_export_without_import(page, app_url, chapter):
    ready(page, app_url)
    content, chosen = complete(page, chapter)
    stats = page.evaluate('LearningStore.summary(ItalianCourse.cards)')
    assert len(stats['schedules']) == len(chosen['cards'])
    assert stats['attempts'] == []  # Guided learning is not independent recall.
    assert page.evaluate('(id) => LearningStore.completed(id)', chapter)
    page.locator('[data-training="save-line"]').click()
    expect(page.locator('#trainingFeedback')).to_contain_text('Saved on this device')
    entry = page.evaluate('Store.repertoire.committed()[0]')
    last = next(c for c in content['cards'] if c['id'] == chosen['cards'][-1])
    assert entry['explorePath'] == last['line'] + [last['move']]
    game = chess.pgn.read_game(io.StringIO(page.evaluate('Repertoire.pgn()')))
    assert game and not game.errors
    assert len(list(game.mainline_moves())) == len(entry['explorePath'])
    # Saving twice keeps the person's edits and notes.
    page.evaluate('''() => { const e=Store.repertoire.committed()[0];
      Store.repertoire.commitPrep({...e, move:e.answer, name:'My own name', notes:'Keep my note'}); }''')
    page.locator('[data-training="save-line"]').click()
    expect(page.locator('#trainingFeedback')).to_contain_text('name and notes have been kept')
    assert page.evaluate('Store.repertoire.committed()[0].notes') == 'Keep my note'
    page.locator('[data-training="done"]').click()
    page.reload()
    expect(page.locator('#italianCourse')).to_contain_text('Revisit')
    assert page.evaluate('Store.lastReport.load()') is None


def test_wrong_answer_and_hint_survive_reload_and_do_not_count_as_recall(page, app_url):
    ready(page, app_url)
    complete(page)
    page.locator('[data-training="recall-chapter"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    expect(page.locator('#trainingBoardPrompt')).to_have_text('White to move. Play the move you prepared.')
    expect(page.locator('#libLine')).to_be_hidden()
    expect(page.locator('.board-tools')).to_be_hidden()
    play(page, chess.Move.from_uci('d2d4'))
    expect(page.locator('#trainingFeedback')).to_contain_text('not automatically a chess mistake')
    page.reload()
    page.locator('[data-training="resume"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page, course(page)['cards'][0])
    stats = page.evaluate('LearningStore.summary(ItalianCourse.cards)')
    assert [e['outcome'] for e in stats['attempts']] == ['missed']
    assert stats['attempts'][0]['played'] == 'd4'
    # Reloading a solved question never awards it twice.
    page.reload()
    page.locator('[data-training="resume"]').click()
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    assert len(page.evaluate('LearningStore.summary(ItalianCourse.cards).attempts')) == 1
    page.locator('[data-training="next"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    page.locator('[data-training="hint"]').click()
    expect(page.locator('#libBoard .cb-arrow')).to_have_count(1)
    page.reload()
    page.locator('[data-training="resume"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    expect(page.locator('.training-clue')).to_contain_text('g1')
    answer(page, course(page)['cards'][1])
    stats = page.evaluate('LearningStore.summary(ItalianCourse.cards)')
    assert stats['independent'] == 0
    assert {e['outcome'] for e in stats['attempts']} == {'missed','hinted'}


def test_due_reviews_advance_schedule_early_practice_does_not(page, app_url):
    start = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    page.clock.install(time=start)
    ready(page, app_url)
    content, chosen = complete(page)
    cards = {c['id']: c for c in content['cards']}
    original_due = page.evaluate('LearningStore.schedule("centre").due')
    page.locator('[data-training="recall-chapter"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page, cards['centre'])
    assert page.evaluate('LearningStore.schedule("centre").due') == original_due
    page.locator('[data-training="pause"]').click()
    # Start a fresh all-chapter review after the cards become due.
    page.clock.set_system_time(datetime(2026, 10, 18, 13, tzinfo=timezone.utc))
    page.locator('#italianCourse [data-training="review"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    assert len(page.evaluate('LearningStore.session().queue')) == 6
    queue = page.evaluate('LearningStore.session().queue')
    for i, key in enumerate(queue):
        if i == 0:
            page.locator('[data-training="hint"]').click()
        elif i == 1:
            board = chess.Board()
            for san in cards[key]['line']: board.push_san(san)
            wrong = next(m for m in board.legal_moves if board.san(m) != cards[key]['move'])
            play(page, wrong)
            expect(page.locator('#trainingFeedback')).to_contain_text('Try again')
        elif i == 2:
            page.locator('[data-training="reveal"]').click()
            expect(page.locator('[data-training="next"]')).to_be_enabled()
        if i != 2:
            answer(page, cards[key])
        page.locator('[data-training="next"]').click()
        if i + 1 < len(queue): expect(page.locator('[data-training="hint"]')).to_be_enabled()
    expect(page.locator('#trainingTitle')).to_have_text('Practice complete')
    expect(page.locator('#trainingPanel')).to_contain_text('3 of 6 answered first time without help')
    stats = page.evaluate('LearningStore.summary(ItalianCourse.cards)')
    schedules = {s['card']:s for s in stats['schedules']}
    for i, interval in enumerate([4 * 3600000, 10 * 60000, 10 * 60000, 86400000]):
        s = schedules[queue[i]]
        assert s['due'] == s['events'][-1]['at'] + interval
    # Replaying an event with its stable ID cannot change the count or due date.
    event = schedules[queue[3]]['events'][0]
    page.evaluate('(e) => LearningStore.attempt(e.id,e.card,e.outcome,e.played)', event)
    assert page.evaluate('(id) => LearningStore.schedule(id).due', queue[3]) == schedules[queue[3]]['due']


def test_course_can_pause_change_opening_and_resume_without_losing_exploration(page, app_url):
    ready(page, app_url)
    task(page)
    answer(page, course(page)['cards'][0])
    page.locator('[data-training="next"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    page.locator('#nav [data-view="explore"]').click()
    page.locator('[data-opening="caro"]').click()
    expect(page.locator('#openingGuideTitle')).to_contain_text('Caro-Kann')
    expect(page.locator('#libLine')).to_contain_text('d5')
    expect(page.locator('#italianCourse')).to_contain_text('CARO-KANN FOR BLACK')
    page.locator('#nav [data-view="explore"]').click()
    page.locator('[data-opening="italian"]').click()
    page.locator('[data-training="resume"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    expect(page.locator('#trainingTitle')).to_have_text('Develop with a threat')
    answer(page, course(page)['cards'][1])


def test_failed_lesson_request_keeps_attempt_and_allows_retry(page, app_url):
    ready(page, app_url)
    task(page)
    page.route('**/api/position?fen=*', lambda r:r.abort())
    play(page, chess.Move.from_uci('e2e4'))
    expect(page.locator('#trainingPanel [role="alert"]')).to_contain_text('progress is saved')
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).schedules.length') == 0
    expect(page.locator('[data-training="pause"]')).to_be_enabled()
    page.unroute('**/api/position?fen=*')
    page.locator('[data-training="retry"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page, course(page)['cards'][0])
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).schedules.length') == 1


def test_two_misses_reveal_once_and_bound_retries(page, app_url):
    ready(page, app_url)
    complete(page)
    page.locator('[data-training="recall-chapter"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    for _ in range(2): play(page, chess.Move.from_uci('d2d4'))
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).attempts[0].outcome') == 'missed'
    expect(page.locator('#trainingFeedback')).to_contain_text('Answer shown')


def test_five_move_practical_session_uses_real_stockfish_and_resumes(page, app_url):
    ready(page, app_url)
    content, chosen = complete(page)
    last = next(c for c in content['cards'] if c['id'] == chosen['cards'][-1])
    page.locator('[data-training="play"]').click()
    page.wait_for_function('LearningStore.session()?.playMoves.length === 1')
    # Resume with precisely the same first engine reply.
    original = page.evaluate('LearningStore.session().playMoves')
    page.reload()
    page.locator('[data-training="resume"]').click()
    expect(page.locator('#trainingFeedback')).not_to_contain_text('choosing')
    page.wait_for_function('document.querySelector("#libTurn").textContent === "White to move" && document.querySelector("#trainingTitle").textContent === "Build your Italian"')
    assert page.evaluate('LearningStore.session().playMoves') == original
    with chess.engine.SimpleEngine.popen_uci(find_engine()) as engine:
        for i in range(5):
            current = page.evaluate('LearningStore.checkpoints().find(s => s.mode === "play")')
            board = chess.Board()
            for san in last['line'] + [last['move']]: board.push_san(san)
            for uci in current['playMoves']: board.push_uci(uci)
            assert board.turn == chess.WHITE
            move = engine.play(board, chess.engine.Limit(depth=6)).move
            play(page, move)
            page.wait_for_function('(n) => LearningStore.checkpoints().find(s => s.mode === "play").playMoves.length === n', arg=(i+1)*2+1)
    expect(page.locator('#trainingTitle')).to_have_text('Position played')
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).practical') == 1
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).attempts.length') == 0


def test_engine_failure_can_exit_or_retry_without_replaying_white_move(page, app_url):
    ready(page, app_url)
    complete(page)
    page.route('**/api/engine', lambda r:r.fulfill(status=503,json={'detail':'Engine unavailable'}))
    page.locator('[data-training="play"]').click()
    expect(page.locator('#trainingPanel [role="alert"]')).to_contain_text('Engine unavailable')
    expect(page.locator('[data-training="pause"]')).to_be_enabled()
    assert page.evaluate('LearningStore.session().playMoves') == []
    page.unroute('**/api/engine')
    page.locator('[data-training="retry"]').click()
    page.wait_for_function('LearningStore.session()?.playMoves.length === 1')
    expect(page.locator('#libTurn')).to_have_text('White to move')


def test_engine_failure_after_white_move_resumes_without_losing_or_duplicating_it(page, app_url):
    ready(page, app_url)
    content, chosen = complete(page)
    last = next(c for c in content['cards'] if c['id'] == chosen['cards'][-1])
    page.locator('[data-training="play"]').click()
    page.wait_for_function('LearningStore.session()?.playMoves.length === 1')
    state = page.evaluate('LearningStore.session()')
    board = chess.Board()
    for san in last['line'] + [last['move']]: board.push_san(san)
    for uci in state['playMoves']: board.push_uci(uci)
    page.route('**/api/engine', lambda r:r.fulfill(status=503,json={'detail':'Engine unavailable'}))
    play(page, next(iter(board.legal_moves)))
    expect(page.locator('#trainingPanel [role="alert"]')).to_contain_text('Engine unavailable')
    stored = page.evaluate('LearningStore.session()')
    assert stored['whiteMoves'] == 1 and len(stored['playMoves']) == 2
    page.locator('[data-training="pause"]').click()
    page.unroute('**/api/engine')
    page.locator('[data-training="resume"]').click()
    page.wait_for_function('LearningStore.session()?.playMoves.length === 3')
    restored = page.evaluate('LearningStore.session()')
    assert restored['playMoves'][:2] == stored['playMoves'] and restored['whiteMoves'] == 1


def test_guest_learning_joins_an_existing_account_without_replacing_its_work(page, app_url):
    ready(page, app_url)
    task(page)
    answer(page, course(page)['cards'][0])
    guest_id = page.evaluate('LearningStore.session().id')
    remote = {'runs':[], 'drills':{}, 'prefs':{ROOT+'checkpoint:other-device':{'id':'other-device',
        'mode':'learn','chapter':'essentials','queue':['centre'], 'index':0,'finished':True,'updated':1}},
        'repertoire':[{'key':'old-account-line','fen':chess.STARTING_FEN,'answer':'d4','line':[],
            'color':'white','status':'committed','decidedAt':1}], 'progress':{}}
    imports = []
    def import_state(route):
        data = route.request.post_data_json
        imports.append(data)
        for k,v in data.get('prefs',{}).items(): remote['prefs'].setdefault(k,v)
        route.fulfill(json=remote)
    page.route('**/api/auth/me',lambda r:r.fulfill(json={'database':True,
        'user':{'id':'test-account','name':'Tester'},'methods':{'email':False,'lichess':False}}))
    page.route('**/api/state',lambda r:r.fulfill(json=remote))
    page.route('**/api/state/import',import_state)
    page.reload()
    page.wait_for_function('Auth.signedIn() && Store.repertoire.committed().some(e=>e.key === "old-account-line")')
    expect(page.locator('[data-training="resume"]')).to_be_visible()
    assert imports and ROOT+'checkpoint:'+guest_id in imports[0]['prefs']
    checkpoints = page.evaluate('LearningStore.checkpoints()')
    assert {s['id'] for s in checkpoints} == {guest_id,'other-device'}
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).schedules.length') == 1


@pytest.mark.parametrize('width,height', [(360,800),(390,844),(768,1024),(1440,1000)])
def test_training_layout_is_board_first_and_controls_work(page, app_url, width, height):
    page.set_viewport_size({'width':width,'height':height})
    ready(page, app_url)
    task(page)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.evaluate('document.querySelector("main").scrollWidth <= document.querySelector("main").clientWidth')
    box = page.locator('#libBoard').bounding_box()
    if width <= 390:
        assert box['width'] >= width - 40
        assert box['y'] + box['height'] < height - 68
    expect(page.locator('#trainingPanel')).to_be_visible()
    if width <= 390:
        for action in ['hint','reveal','pause']:
            box = page.locator(f'[data-training="{action}"]').bounding_box()
            assert box['y'] + box['height'] <= height - 62
    if width <= 390:
        page.locator('#libBoard [data-square="e2"]').tap()
        page.locator('#libBoard [data-square="e4"]').tap()
    else:
        page.locator('#libBoard [data-square="e2"]').focus()
        page.keyboard.press('Enter')
        page.locator('#libBoard [data-square="e4"]').focus()
        page.keyboard.press('Enter')
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    if width <= 390:
        for action in ['next','pause']:
            box = page.locator(f'[data-training="{action}"]').bounding_box()
            assert box['y'] + box['height'] <= height - 62
    page.locator('[data-training="pause"]').click()
    expect(page.locator('.study-tabs')).to_be_visible()


def test_learning_storage_failure_is_honest_and_survives_in_tab(page, app_url):
    ready(page, app_url)
    page.evaluate('''() => { const set=Storage.prototype.setItem;
      Storage.prototype.setItem=function(k,v) { if(k.startsWith('leaklab:pref:learning:')) throw new DOMException('full','QuotaExceededError'); return set.call(this,k,v); }; }''')
    task(page)
    answer(page, course(page)['cards'][0])
    expect(page.locator('.training-storage')).to_contain_text('tab only')
    page.locator('[data-training="pause"]').click()
    page.locator('[data-training="resume"]').click()
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    assert any(k.startswith(ROOT+'enrol:') for k in page.evaluate('Store.snapshot().prefs'))


def test_learning_account_adoption_and_signout_keep_old_work_and_isolate_progress(page, app_url):
    ready(page, app_url)
    task(page)
    answer(page, course(page)['cards'][0])
    before = page.evaluate('Store.snapshot()')
    records = {k:v for k,v in before['prefs'].items() if k.startswith(ROOT)}
    page.evaluate('(remote) => Store.adopt(remote)', {**before, 'prefs':records})
    page.reload()
    page.locator('[data-training="resume"]').click()
    expect(page.locator('[data-training="next"]')).to_be_enabled()
    page.locator('[data-training="pause"]').click()
    page.evaluate('Store.forget()')
    page.reload()
    assert page.evaluate('LearningStore.summary(ItalianCourse.cards).schedules.length') == 0
    assert page.evaluate('LearningStore.session()') is None
