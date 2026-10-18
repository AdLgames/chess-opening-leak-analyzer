"""Public reading, free lessons, safe hand-off and optional measurement."""
import json
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect
from test_training import ready, answer

PATHS = ['/learn/italian-game/', '/learn/caro-kann/', '/learn/queens-gambit-declined/',
         '/guides/', '/guides/italian-game-for-beginners/', '/guides/caro-kann-plans/',
         '/guides/remember-chess-openings/', '/about/', '/contact/', '/privacy/', '/404.html']


@pytest.mark.parametrize('width',[360,1440])
@pytest.mark.parametrize('path',PATHS)
def test_new_public_destinations_have_readable_mobile_layouts_and_no_missing_assets(page,app_url,width,path):
    page.set_viewport_size({'width':width,'height':900})
    failures=[]
    page.on('response',lambda r:failures.append(r.url) if r.status>=400 and not r.url.endswith('/404.html') else None)
    page.goto(app_url+path)
    expect(page.locator('h1')).to_be_visible()
    assert page.locator('h1').count()==1
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    assert not failures
    expect(page.locator('footer a[href="/privacy/"]')).to_be_visible()


@pytest.mark.parametrize('path,opening,uci',[
    ('/learn/italian-game/','italian','f1c4'),
    ('/learn/caro-kann/','caro','d7d5'),
    ('/learn/queens-gambit-declined/','queens','e7e6'),
])
def test_each_free_course_example_works_offline_then_opens_the_actual_first_chapter(page,app_url,path,opening,uci):
    page.goto(app_url+path)
    page.evaluate('Store.prefs.set("learning:v2:italian-v1:sentinel",{keep:true})')
    before=page.evaluate('Store.prefs.all()')
    page.route('**/api/**',lambda r:r.abort())
    page.locator(f'#previewBoard [data-square="{uci[:2]}"]').click()
    page.locator(f'#previewBoard [data-square="{uci[2:]}"]').click()
    expect(page.locator('#demoPrompt')).to_contain_text('That’s the idea')
    assert page.evaluate('Store.prefs.all()')==before
    expect(page.locator('#demoContinue')).to_have_attribute('href',f'/app/?opening={opening}&chapter=essentials#today')
    page.unroute('**/api/**')
    page.locator('#demoContinue').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled(timeout=15000)
    session=page.evaluate('Training.info()')
    assert session['chapter']=='essentials' and session['mode']=='learn'
    assert page.evaluate('(s)=>OpeningCourses.find(c=>c.id===s.course).opening',session)==opening
    assert page.evaluate('Store.prefs.get("learning:v2:italian-v1:sentinel")')=={'keep':True}


@pytest.mark.parametrize('path',['/learn/italian-game/','/guides/italian-game-for-beginners/','/guides/caro-kann-plans/','/guides/remember-chess-openings/'])
def test_public_learning_content_is_usable_without_javascript(browser,app_url,path):
    context=browser.new_context(java_script_enabled=False,viewport={'width':360,'height':800})
    p=context.new_page()
    p.goto(app_url+path)
    expect(p.locator('#publicNav a[href="/learn/"]')).to_be_visible()
    expect(p.locator('h1')).to_be_visible()
    expect(p.locator('#previewBoard img')).to_be_visible()
    if '/guides/' in path:
        expect(p.locator('.guide-prose')).to_be_visible()
        assert len(p.locator('.guide-prose').inner_text().split())>600
    context.close()


def test_public_chapter_deep_link_resumes_existing_work_instead_of_resetting_it(page,app_url):
    ready(page,app_url)
    page.locator('[data-course-chapter="essentials"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    answer(page,page.evaluate('ItalianCourse.cards[0]'))
    page.locator('[data-training="next"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    saved=page.evaluate('Training.info()')
    page.goto(app_url+'/learn/italian-game/')
    page.locator('.public-chapters a').first.click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    resumed=page.evaluate('Training.info()')
    assert resumed['id']==saved['id'] and resumed['index']==saved['index']


def test_invalid_chapter_link_keeps_the_selected_opening_available(page,app_url):
    page.goto(app_url+'/app/?opening=caro&chapter=not-a-chapter#today')
    expect(page.locator('#openingGuideTitle')).to_contain_text('Caro',timeout=15000)
    assert page.evaluate('Training.active()') is False


def test_missing_page_returns_a_real_404_with_a_useful_recovery(page,app_url):
    response=page.goto(app_url+'/this-opening-page-does-not-exist/')
    assert response.status==404
    expect(page.locator('h1')).to_contain_text('This line ends here')
    expect(page.locator('main a[href="/learn/"]')).to_be_visible()


@pytest.mark.parametrize('path',['/openings/','/openings/italian-game-c50/'])
def test_database_uses_the_public_navigation_and_a_working_mobile_table(page,app_url,path):
    page.set_viewport_size({'width':360,'height':800})
    page.goto(app_url+path)
    expect(page.locator('h1')).to_be_visible()
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.locator('#navToggle').click()
    expect(page.locator('#publicNav a[href="/guides/"]')).to_be_visible()
    if path!='/openings/':
        expect(page.locator('.database-course-link a')).to_have_attribute('href','/learn/italian-game/')
        expect(page.locator('.doc-table')).to_be_visible()


def proxy_production(page,app_url,*,configured=True):
    def serve(route):
        url=urlsplit(route.request.url)
        if url.path=='/site-config.js':
            route.fulfill(content_type='application/javascript',body='window.LeakSiteConfig='+json.dumps({'analyticsDomain':'chessleaklab.co.uk' if configured else ''})+';')
        else:
            response=page.request.get(app_url+url.path)
            route.fulfill(response=response)
    page.route('https://chessleaklab.co.uk/**',serve)


def test_optional_counts_default_off_and_coarse_hooks_do_not_touch_learning_data(page,app_url):
    proxy_production(page,app_url)
    sent=[]
    page.route('https://plausible.io/api/event',lambda r:(sent.append(r.request.post_data_json),r.fulfill(status=202,body='ok')))
    page.add_init_script('window.metricsSeen=[];addEventListener("leaklab:metric",e=>metricsSeen.push(e.detail));')
    page.goto('https://chessleaklab.co.uk/learn/italian-game/?user=private_name')
    before=page.evaluate('Store.prefs.all()')
    for _ in range(2):
        page.locator('#previewBoard [data-square="f1"]').click();page.locator('#previewBoard [data-square="c4"]').click()
        expect(page.locator('#demoContinue')).to_be_visible()
        page.locator('#demoReset').click()
    assert not sent
    assert page.evaluate('metricsSeen.filter(e=>e.name==="Preview completed").length')==1
    assert page.evaluate('Store.prefs.all()')==before


def test_allowed_counts_strip_private_queries_payloads_and_account_identifiers(page,app_url):
    proxy_production(page,app_url)
    page.add_init_script('localStorage.setItem("leaklab:measurement","allow")')
    sent=[]
    def capture(route):
        sent.append(route.request.post_data_json)
        assert not route.request.headers.get('referer')
        route.fulfill(status=202,body='ok')
    page.route('https://plausible.io/api/event',capture)
    page.goto('https://chessleaklab.co.uk/learn/italian-game/?user=private_name&token=secret#private')
    with page.expect_response(lambda r:r.url=="https://plausible.io/api/event" and r.request.post_data_json["name"]=="Training completed"):
        page.evaluate('LeakMetrics.track("Training completed",{course:"italian",mode:"learn",surface:"workspace",email:"secret@email",fen:"private",user:"private_name"},"private-session-id")')
    result=next(e for e in sent if e['name']=='Training completed')
    assert result=={'name':'Training completed','domain':'chessleaklab.co.uk','url':'https://chessleaklab.co.uk/learn/italian-game/','props':{'course':'italian','mode':'learn','surface':'workspace'}}
    assert all('private' not in json.dumps(e) and 'secret' not in json.dumps(e) for e in sent)


def test_measurement_can_be_allowed_and_revoked_on_the_privacy_page(page,app_url):
    proxy_production(page,app_url)
    sent=[]
    page.route('https://plausible.io/api/event',lambda r:(sent.append(r.request.post_data_json),r.fulfill(status=202,body='ok')))
    page.goto('https://chessleaklab.co.uk/privacy/')
    page.locator('[data-measurement="allow"]').click()
    expect(page.locator('#measurementStatus')).to_contain_text('You allow')
    with page.expect_request('https://plausible.io/api/event'):
        page.evaluate('LeakMetrics.track("Training started",{mode:"learn"})')
    page.locator('[data-measurement="deny"]').click()
    expect(page.locator('#measurementStatus')).to_contain_text('are off')
    count=len(sent)
    page.evaluate('LeakMetrics.track("Training completed",{mode:"learn"})')
    assert len(sent)==count


@pytest.mark.parametrize('protection',['gpc','dnt'])
def test_browser_privacy_protection_overrides_optional_measurement_consent(page,app_url,protection):
    proxy_production(page,app_url)
    prop='globalPrivacyControl' if protection=='gpc' else 'doNotTrack'
    value='true' if protection=='gpc' else '"1"'
    page.add_init_script(f'localStorage.setItem("leaklab:measurement","allow");Object.defineProperty(navigator,"{prop}",{{get:()=>{value}}})')
    sent=[]
    page.route('https://plausible.io/api/event',lambda r:(sent.append(r.request.post_data_json),r.fulfill(status=202,body='ok')))
    page.goto('https://chessleaklab.co.uk/privacy/')
    page.locator('[data-measurement="allow"]').click()
    expect(page.locator('#measurementStatus')).to_contain_text('browser requests privacy')
    assert not sent
