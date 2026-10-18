"""Branded navigation, verified book feedback and deliberate provider handoffs."""
import json
from urllib.parse import parse_qs, urlparse
import chess
import pytest
from playwright.sync_api import expect
from chessopening.board import position_payload


def ready(page,app_url,route='today'):
 page.goto(app_url+'/app/#'+route)
 page.wait_for_function('Auth.state.ready && window.Clubhouse')
 expect(page.locator('#libBoard')).to_have_attribute('aria-busy','false')


def play(page,uci):
 page.locator(f'#libBoard .cb-sq[data-square={uci[:2]}]').click()
 page.locator(f'#libBoard .cb-sq[data-square={uci[2:4]}]').click()
 expect(page.locator('#libBoard')).to_have_attribute('aria-busy','false')


def account(page,user=None,methods=None):
 page.route('**/api/auth/me',lambda r:r.fulfill(json={'database':True,'user':user,'methods':methods or {'email':True,'lichess':True}}))
 page.route('**/api/state',lambda r:r.fulfill(json={'runs':[],'repertoire':[],'drills':{},'prefs':{}}))


@pytest.mark.parametrize('coach',['maya','theo','inez'])
def test_book_moves_get_positive_factual_reactions_for_both_colours_without_learning_credit(page,app_url,coach):
 ready(page,app_url);page.locator('#openLearningProfile').click();page.select_option('#learningProfile [name=guide]',coach);page.locator('#learningProfile [type=submit]').click()
 play(page,'e2e4');expect(page.locator('#boardCompanion')).to_have_attribute('data-reaction','book')
 expect(page.locator('#boardCompanion .companion-task')).to_contain_text('e4 is a book move')
 expect(page.locator('#boardCompanion .companion-task')).to_contain_text('controls d5 and f5')
 first=page.locator('#boardCompanion .companion-quip').inner_text()
 play(page,'e7e5');expect(page.locator('#boardCompanion .companion-task')).to_contain_text('e5 is a book move')
 assert page.evaluate('LearningStore.summary(ItalianCourse.cards).attempts')==[]
 assert page.evaluate('LearningStore.records()')=={}
 page.locator('#libBack').click();expect(page.locator('#boardCompanion')).to_have_attribute('data-reaction','explore')
 page.locator('#libForward').click();expect(page.locator('#boardCompanion')).to_have_attribute('data-reaction','explore')
 assert first


@pytest.mark.parametrize('recorded_before',[True,False])
def test_book_classification_comes_from_the_exact_pre_move_row_not_the_next_position(page,app_url,recorded_before):
 def positions(route):
  q=parse_qs(urlparse(route.request.url).query);board=chess.Board(q.get('fen',[chess.STARTING_FEN])[0])
  for uci in q.get('moves',[''])[0].split(','):
   if uci:board.push_uci(uci)
  for san in q.get('san',[''])[0].split():board.push_san(san)
  payload=position_payload(fen=board.fen())
  source=recorded_before if board.turn==chess.WHITE else not recorded_before
  payload['book']={'total':4242,'score':50,'moves':[{'uci':'e2e4' if source else 'g1f3','san':'e4' if source else 'Nf3','games':4242,'share':100,'score':50}]}
  route.fulfill(json=payload)
 page.route('**/api/position?**',positions);ready(page,app_url);play(page,'e2e4')
 expect(page.locator('#boardCompanion')).to_have_attribute('data-reaction','book' if recorded_before else 'exploreMove')
 text=page.locator('#boardCompanion .companion-task').inner_text()
 assert ('4,242' in text)==recorded_before
 if not recorded_before:assert 'not make it a mistake' in text


def test_failed_move_does_not_trigger_book_praise_or_change_the_line(page,app_url):
 ready(page,app_url);page.route('**/api/position?*moves=e2e4*',lambda r:r.abort())
 play(page,'e2e4');expect(page.locator('#exploreError')).to_be_visible()
 expect(page.locator('#boardCompanion')).to_have_attribute('data-reaction','explore')
 assert page.locator('#libLine .ply').count()==0


@pytest.mark.parametrize('provider',['lichess','chesscom'])
def test_banner_selects_provider_without_starting_analysis_and_auth_redirect_keeps_the_intent(page,app_url,provider):
 account(page);ready(page,app_url)
 requests=[];page.on('request',lambda r:requests.append(r.url))
 expect(page.locator('#accountInvite')).to_be_visible()
 page.locator(f'#accountInvite [data-connect-provider={provider}]').click()
 expect(page.locator('#importWelcome')).to_be_visible()
 expect(page.locator(f'#providerSeg [data-provider={provider}]')).to_have_attribute('aria-checked','true')
 expect(page.locator('#authGate')).to_be_visible()
 expect(page.locator('#gateSlot')).to_be_hidden()
 redirect=parse_qs(urlparse(page.locator('#authGate .auth-lichess').get_attribute('href')).query)['redirect'][0]
 assert f'connect={provider}' in redirect and redirect.endswith('#progress/games')
 assert not any('/api/analy' in r for r in requests)
 if provider=='chesscom':
  expect(page.locator('#importWelcome')).to_contain_text('public games by Chess.com username')
  assert page.locator('a[href*="auth/chesscom"]').count()==0


def test_public_username_survives_email_signin_handoff_without_an_automatic_run(page,app_url):
 account(page);sent=[]
 page.route('**/api/auth/email/request',lambda r:(sent.append(r.request.post_data_json),r.fulfill(json={'ok':True})))
 page.goto(app_url+'/app/?connect=chesscom&user=Test_player#progress/games')
 expect(page.locator('#importWelcomeTitle')).to_contain_text('Chess.com')
 page.locator('#authGate #authEmail').fill('player@example.test');page.locator('#authGate #authEmailBtn').click()
 expect(page.locator('#authGate')).to_contain_text('Check your email')
 assert len(sent)==1
 redirect=sent[0]['redirect'];query=parse_qs(urlparse(redirect).query)
 assert query=={'connect':['chesscom'],'user':['Test_player']}
 assert urlparse(redirect).fragment=='progress/games'


def test_lichess_signin_return_prefills_linked_username_and_waits_for_user_to_run(page,app_url):
 account(page,{'id':'test-owner','name':'Player','accounts':[{'provider':'lichess','username':'Linked_player'}]})
 requests=[];page.on('request',lambda r:requests.append(r.url))
 page.goto(app_url+'/app/?connect=lichess#progress/games')
 expect(page.locator('#importWelcome')).to_be_visible();expect(page.locator('#optUser')).to_have_value('Linked_player')
 expect(page.locator('#gateSlot')).to_be_visible();expect(page.locator('#runBtn')).to_be_enabled()
 assert not any('/api/analy' in r for r in requests)


@pytest.mark.parametrize('width,height',[(360,800),(390,844),(768,1024),(1440,1000)])
def test_themed_header_drawer_and_tools_work_at_every_width(page,app_url,width,height):
 page.set_viewport_size({'width':width,'height':height});ready(page,app_url)
 assert page.locator('.header').bounding_box()['height']<=58
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 if width<=860:
  page.locator('#menuBtn').click();expect(page.locator('#sidebar')).to_have_attribute('role','dialog')
  expect(page.locator('#drawerClose')).to_be_focused()
  page.keyboard.press('Shift+Tab');expect(page.locator('.rail-welcome button')).to_be_focused()
  page.keyboard.press('Tab');expect(page.locator('#drawerClose')).to_be_focused()
  assert page.locator('#main').evaluate('(e)=>e.inert')
  page.keyboard.press('Escape');expect(page.locator('#menuBtn')).to_be_focused()
  assert not page.locator('#main').evaluate('(e)=>e.inert')
 page.locator('.workspace-tools > summary').click();expect(page.locator('.workspace-tools > .menu-body')).to_be_visible()
 page.keyboard.press('Escape');expect(page.locator('.workspace-tools > .menu-body')).to_be_hidden()
 page.locator('#openLearningProfile').click();expect(page.locator('#learningProfile')).to_be_visible()


def test_public_banner_and_signup_link_preserve_chesscom_choice_and_username(page,app_url):
 page.goto(app_url+'/');page.locator('#platform [data-provider=chesscom]').click();page.locator('#user').fill('Test_player')
 link=page.locator('#startConnect').get_attribute('href');assert parse_qs(urlparse(link).query)=={'connect':['chesscom'],'user':['Test_player']}
 expect(page.locator('#analyse')).to_contain_text('No chess-site password')
 page.goto(app_url+'/learn/italian-game/');expect(page.locator('.public-connect')).to_be_visible()
 assert page.locator('.public-connect a[href*="connect=chesscom"]').count()==1


def test_header_signin_keeps_the_selected_import_and_native_dialog_escape_restores_focus(page,app_url):
 account(page);page.goto(app_url+'/app/?connect=chesscom&user=Test_player#progress/games')
 expect(page.locator('#importWelcome')).to_be_visible();page.locator('#signInBtn').click()
 expect(page.locator('#authDialog')).to_be_visible()
 redirect=parse_qs(urlparse(page.locator('#authDialog .auth-lichess').get_attribute('href')).query)['redirect'][0]
 assert parse_qs(urlparse(redirect).query)=={'connect':['chesscom'],'user':['Test_player']}
 page.keyboard.press('Escape');expect(page.locator('#authDialog')).to_be_hidden()
 page.locator('.workspace-tools>summary').click();page.locator('#workspaceHelp').click()
 expect(page.locator('#dataDialog')).to_be_visible();page.keyboard.press('Escape')
 expect(page.locator('#dataDialog')).to_be_hidden();expect(page.locator('#workspaceHelp')).to_be_focused()


def test_invitation_respects_training_and_does_not_nag_people_with_imported_games(page,app_url):
 ready(page,app_url);expect(page.locator('#accountInvite')).to_be_visible()
 page.locator('[data-course-chapter=essentials]').click();expect(page.locator('[data-training=hint]')).to_be_enabled()
 expect(page.locator('#accountInvite')).to_be_hidden()
 page.locator('[data-training=pause]').click();expect(page.locator('#accountInvite')).to_be_visible()
 page.evaluate('Store.runs.record({id:"my-games",at:Date.now(),player:"Player",games:20});Clubhouse.render()')
 expect(page.locator('#accountInvite')).to_be_hidden()


@pytest.mark.parametrize('signed_out',[False,True])
def test_import_from_an_existing_report_keeps_the_report_and_waits_for_user(page,app_url,signed_out):
 if signed_out:account(page)
 page.goto(app_url+'/app/?demo=1')
 expect(page.locator('#report')).to_be_visible(timeout=30000)
 before=page.locator('#leakBody').inner_text()
 requests=[];page.on('request',lambda r:requests.append(r.url))
 page.evaluate("App.openImport('chesscom',{user:'Test_player'})")
 expect(page.locator('#report')).to_be_visible()
 if signed_out:
  expect(page.locator('#authDialog')).to_be_visible()
  redirect=parse_qs(urlparse(page.locator('#authDialog .auth-lichess').get_attribute('href')).query)['redirect'][0]
  assert parse_qs(urlparse(redirect).query)=={'connect':['chesscom'],'user':['Test_player']}
 else:
  expect(page.locator('#runDialog')).to_be_visible()
  expect(page.locator('#optUser')).to_be_focused()
  expect(page.locator('#panelAccount')).to_be_visible()
  expect(page.locator('#optUser')).to_have_value('Test_player')
 page.keyboard.press('Escape')
 expect(page.locator('#report')).to_be_visible()
 assert page.locator('#leakBody').inner_text()==before
 assert not any('/api/analy' in r for r in requests)
