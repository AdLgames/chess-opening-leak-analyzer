"""Release journeys for the foundation milestone; chess endpoints are not mocked."""
import io
import json
import re

import pytest
import chess
import chess.pgn
from playwright.sync_api import expect

START = chess.STARTING_FEN


def ready(page, app_url, route='today'):
    page.goto(f'{app_url}/app/#{route}')
    expect(page.locator('#libBoard')).to_have_attribute('aria-busy', 'false')


def choose(page, opening='italian'):
    page.locator(f'#exploreOpenings [data-opening="{opening}"]').click()
    expect(page.locator('#libBoard')).to_have_attribute('aria-busy', 'false')


def save(page, name='My Italian', side='white', note='Castle, then challenge the centre.'):
    page.locator('#openSaveLine').click()
    page.locator('#saveLineName').fill(name)
    page.locator('#saveLineSide').select_option(side)
    page.locator('#saveLineNote').fill(note)
    page.locator('#saveExplorerLine').click()
    expect(page.locator('#saveLineStatus')).to_contain_text('Saved on this device')


def test_guest_explore_save_reload_and_reopen(page, app_url):
    ready(page, app_url)
    expect(page.locator('#todayStart')).to_have_text(re.compile('Explore openings'))
    page.locator('#todayStart').click()
    choose(page)
    expect(page.locator('#libLine')).to_contain_text('Bc4')
    expect(page.locator('#libTurn')).to_have_text('Black to move')
    page.get_by_role('button', name='Play Bc5', exact=True).click()
    expect(page.locator('#libLine')).to_contain_text('Bc5')
    page.locator('#libBack').click()
    expect(page.locator('#libTurn')).to_have_text('Black to move')
    assert 'Bc5' not in page.locator('#libLine').inner_text()
    save(page)
    page.locator('#saveLineStatus a').click()
    expect(page.locator('#savedLineCards')).to_contain_text('My Italian')
    page.reload()
    expect(page.locator('#savedLineCards')).to_contain_text('Castle, then challenge the centre.')
    page.locator('#savedLineCards [data-entry]').click()
    expect(page.locator('#libLine')).to_contain_text('Bc4')
    expect(page.locator('#libBack')).to_be_enabled()
    assert page.evaluate('Store.lastReport.load()') is None


def test_both_sides_and_pgn_export_preserve_legal_move_orders(page, app_url):
    ready(page, app_url, 'explore')
    choose(page)
    page.get_by_role('button', name='Play Bc5', exact=True).click()
    expect(page.locator('#libLine')).to_contain_text('Bc5')
    save(page, name='White choice')
    page.locator('#saveLineClose').click()
    choose(page, 'caro')
    save(page, name='Black choice', side='black')
    entries = page.evaluate('Store.repertoire.committed()')
    assert {e['color'] for e in entries} == {'white', 'black'}
    assert entries[1]['answer'] == 'd5'
    assert entries[1]['line'] == ['e4', 'c6', 'd4']
    exported = io.StringIO(page.evaluate('Repertoire.pgn("Tester")'))
    for _ in range(2):
        game = chess.pgn.read_game(exported)
        assert game and not game.errors
        assert len(list(game.mainline_moves())) == (6 if _ == 0 else 4)


@pytest.mark.parametrize('width,height', [(360,800), (390,844), (768,1024), (1440,1000)])
def test_four_destinations_fit_and_history_works(page, app_url, width, height):
    page.set_viewport_size({'width':width,'height':height})
    ready(page, app_url)
    nav = '#tabbar' if width <= 860 else '#nav'
    assert page.locator(f'{nav} a:visible').all_text_contents() == ['Today','Explore','Repertoire','Progress']
    if width == 360:
        box = page.locator('#todayStart').bounding_box()
        assert box['y'] + box['height'] < height - 68
    for view in ['explore','repertoire','progress']:
        page.locator(f'{nav} [data-view="{view}"]').click()
        expect(page.locator('#viewTitle')).to_have_text(view.title())
        expect(page.locator(f'{nav} [data-view="{view}"]')).to_have_attribute('aria-current','page')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.evaluate('document.querySelector("main").scrollWidth <= document.querySelector("main").clientWidth')
    page.go_back()
    expect(page.locator('#viewTitle')).to_have_text('Repertoire')
    page.go_back()
    expect(page.locator('#viewTitle')).to_have_text('Explore')
    page.go_forward()
    expect(page.locator('#viewTitle')).to_have_text('Repertoire')
    page.reload()
    expect(page.locator('#viewTitle')).to_have_text('Repertoire')


def test_legacy_data_and_account_adoption_survive_upgrade(page, app_url):
    old_entry = {'key':'legacy','position':'legacy','fen':START,'color':'white','answer':'e4','status':'committed','line':[],'games':12,'source':'prep','decidedAt':1234}
    old_drills = {'legacy':{'key':'legacy','right':3,'wrong':2,'due':123456,'last':1234,'streak':1}}
    old_run = {'id':'old','at':1234,'games':10,'coverage':50,'keys':[]}
    payload = {'repertoire':[old_entry],'drills':old_drills,'runs':[old_run]}
    page.add_init_script(f'''if (!localStorage.getItem('seeded')) {{
      for (const [key, value] of Object.entries({json.dumps(payload)})) localStorage.setItem('leaklab:'+key, JSON.stringify(value));
      localStorage.setItem('seeded','1');
    }}''')
    ready(page, app_url, 'repertoire')
    snapshot = page.evaluate('Store.snapshot()')
    for key, value in payload.items(): assert snapshot[key] == value
    backup = page.evaluate('JSON.parse(localStorage.getItem("leaklab:backup:v0"))')
    for key, value in payload.items(): assert backup[key] == value
    page.reload()
    assert page.evaluate('JSON.parse(localStorage.getItem("leaklab:backup:v0")).at') == backup['at']
    page.evaluate('(remote) => Store.adopt(remote)', {**payload,'prefs':{'theme':'light'}})
    assert page.evaluate('Store.snapshot().drills') == old_drills
    page.reload()
    expect(page.locator('#savedLineCards')).to_contain_text('e4')


def test_account_gate_does_not_block_opening_exploration(page, app_url):
    page.route('**/api/auth/me',lambda route:route.fulfill(json={'database':True,'user':None,'methods':{'email':True,'lichess':False}}))
    ready(page, app_url, 'explore')
    choose(page)
    save(page)
    assert page.evaluate('Auth.required()') is True
    expect(page.locator('#saveLineStatus')).to_contain_text('Saved on this device')


def test_keyboard_book_moves_tap_board_and_flip(page, app_url):
    ready(page, app_url, 'explore')
    first = page.get_by_role('button',name='Play e4',exact=True)
    first.focus()
    page.keyboard.press('Enter')
    expect(page.locator('#libTurn')).to_have_text('Black to move')
    # Tap-to-select and tap-to-move on the existing accessible board.
    page.locator('#libBoard [data-square="e7"]').click()
    page.locator('#libBoard [data-square="e5"]').click()
    expect(page.locator('#libLine')).to_contain_text('e5')
    page.locator('#libFlip').click()
    assert page.locator('#libBoard .cb-sq').first.get_attribute('data-square') == 'h1'


def test_failed_move_keeps_history_and_can_retry(page, app_url):
    ready(page, app_url, 'explore')
    before = page.locator('#libLine').inner_text()
    page.route('**/api/position?*moves=*',lambda route:route.abort())
    page.get_by_role('button',name='Play e4',exact=True).click()
    expect(page.locator('#exploreError')).to_be_visible()
    assert page.locator('#libLine').inner_text() == before
    page.unroute('**/api/position?*moves=*')
    page.get_by_role('button',name='Play e4',exact=True).click()
    expect(page.locator('#libLine')).to_contain_text('e4')
    expect(page.locator('#exploreError')).to_be_hidden()


def test_position_entry_empty_book_and_fen_export(page, app_url):
    ready(page, app_url, 'explore')
    page.locator('.position-tools > summary').click()
    page.locator('#explorePositionInput').fill('1. e4 e5 2. Nf3 Nc6')
    page.get_by_role('button',name='Show on board').click()
    expect(page.locator('#libLine')).to_contain_text('Nc6')
    page.locator('#explorePositionInput').fill('nonsense')
    page.get_by_role('button',name='Show on board').click()
    expect(page.locator('#explorePositionError')).to_contain_text('Could not open')
    expect(page.locator('#libLine')).to_contain_text('Nc6')
    position = '8/8/8/8/8/4k3/8/4K2R w K - 0 30'
    page.locator('#explorePositionInput').fill(position)
    page.get_by_role('button',name='Show on board').click()
    expect(page.locator('#libStats')).to_contain_text('Outside the book')
    page.locator('#libBoard [data-square="h1"]').click()
    page.locator('#libBoard [data-square="h2"]').click()
    expect(page.locator('#libLine')).to_contain_text('Rh2')
    save(page,name='Rook ending')
    game = chess.pgn.read_game(io.StringIO(page.evaluate('Repertoire.pgn()')))
    assert game and not game.errors and game.headers['FEN'] == position
    page.locator('#saveLineStatus a').click()
    page.locator('#savedLineCards [data-entry]').click()
    expect(page.locator('#libLine')).to_contain_text('Rh2')


def test_analysis_demo_drills_exports_and_contextual_return(page, app_url):
    ready(page, app_url, 'dashboard')
    expect(page.locator('#viewTitle')).to_have_text('Game analysis')
    page.locator('#sampleBtn').click()
    expect(page.locator('#report')).to_be_visible(timeout=30000)
    expect(page.locator('#leakBody tr').first).to_be_visible()
    page.locator('#leakBody tr').first.click()
    expect(page.locator('#viewTitle')).to_have_text('Practice & review')
    expect(page.locator('#trainingExit')).to_have_text('← Back to Game analysis')
    page.locator('#clinicMode [data-mode="drill"]').click()
    expect(page.locator('#practiceBody')).to_be_visible()
    expect(page.locator('#drillBoard .cb-sq')).to_have_count(64)
    page.locator('#clinicMode [data-mode="study"]').click()
    expect(page.locator('#fixPanel')).to_be_visible()
    page.locator('#trainingExit').click()
    expect(page.locator('#viewTitle')).to_have_text('Game analysis')
    page.locator('#exportMenu summary').click()
    with page.expect_download() as download:
        page.locator('#exportCsv').click()
    assert download.value.suggested_filename.endswith('.csv')
    page.locator('#nav [data-view="progress"]').click()
    expect(page.locator('#progressEvidence')).to_contain_text('Your preparation')


def test_quota_failure_is_honest_and_keeps_tab_copy(page, app_url):
    ready(page, app_url,'explore')
    page.evaluate('() => { Storage.prototype.setItem = function() { throw new DOMException("Quota exceeded", "QuotaExceededError"); }; }')
    choose(page)
    page.locator('#openSaveLine').click()
    page.locator('#saveLineName').fill('Kept in memory')
    page.locator('#saveExplorerLine').click()
    expect(page.locator('#saveLineStatus')).to_contain_text('Kept in this tab only')
    assert page.evaluate('Store.repertoire.committed()[0].name') == 'Kept in memory'



def test_phone_touch_board_and_promotion_selection(page, app_url):
    page.set_viewport_size({'width':360, 'height':800})
    ready(page, app_url, 'explore')
    choose(page, 'caro')
    assert page.locator('#libBoard .cb-sq').first.get_attribute('data-square') == 'h1'
    for square in ['e4', 'd5']:
        target = page.locator(f'#libBoard [data-square="{square}"]')
        target.scroll_into_view_if_needed()
        bounds = target.bounding_box()
        page.touchscreen.tap(bounds['x'] + bounds['width']/2, bounds['y'] + bounds['height']/2)
    expect(page.locator('#libLine')).to_contain_text('exd5')
    bounds = page.locator('#libBoard').bounding_box()
    assert bounds['width'] <= 360
    page.locator('.position-tools > summary').click()
    page.locator('#explorePositionInput').fill('8/P7/8/8/8/8/8/K6k w - - 0 1')
    page.get_by_role('button', name='Show on board').click()
    expect(page.locator('#libTurn')).to_have_text('White to move')
    page.locator('#libBoard [data-square="a7"]').click()
    page.locator('#libBoard [data-square="a8"]').click()
    expect(page.locator('#libBoard .cb-promo')).to_be_visible()
    page.locator('#libBoard [data-uci="a7a8n"]').click()
    expect(page.locator('#libLine')).to_contain_text('a8=N')
