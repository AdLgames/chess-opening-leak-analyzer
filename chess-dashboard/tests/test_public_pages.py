"""The public brand pages lead to usable lessons without touching learning records."""
import pytest
import re
from playwright.sync_api import expect


@pytest.mark.parametrize('width',[360,390,1440])
@pytest.mark.parametrize('path',['/','/learn/','/coaches/'])
def test_public_pages_fit_phone_and_desktop_without_missing_assets(page,app_url,width,path):
    page.set_viewport_size({'width':width,'height':900})
    failed=[]
    page.on('response',lambda r:failed.append(r.url) if r.status>=400 and '/_vercel/' not in r.url else None)
    page.goto(app_url+path)
    expect(page.locator('h1')).to_be_visible()
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    assert page.locator('main').count() == 1
    assert not failed


@pytest.mark.parametrize('opening,move,side',[('italian','f1c4','White'),('caro','d7d5','Black'),('queens','e7e6','Black')])
def test_preview_plays_both_sides_without_a_network_or_recall_credit(page,app_url,opening,move,side):
    page.route('**/api/**',lambda r:r.abort())
    page.goto(app_url+'/')
    page.evaluate('Store.prefs.set("learning:v2:italian-v1:sentinel",{keep:true})')
    before=page.evaluate('Store.prefs.all()')
    page.locator(f'[data-preview="{opening}"]').click()
    expect(page.locator('#demoSide')).to_have_text(side+' to move')
    page.locator(f'#previewBoard [data-square="{move[:2]}"]').click()
    page.locator(f'#previewBoard [data-square="{move[2:]}"]').click()
    expect(page.locator('#demoPrompt')).to_contain_text('That’s the idea')
    expect(page.locator('#demoContinue')).to_have_attribute('href',f'/app/?opening={opening}#today')
    assert page.evaluate('Store.prefs.all()') == before
    page.locator('#demoReset').click()
    expect(page.locator('#demoSide')).to_have_text(side+' to move')


def test_preview_gives_a_hint_and_accepts_a_retry_after_a_legal_alternative(page,app_url):
    page.goto(app_url+'/')
    page.locator('#previewBoard [data-square="f1"]').click()
    page.locator('#previewBoard [data-square="b5"]').click()
    expect(page.locator('#demoFeedback')).to_contain_text('Bb5 is legal')
    page.locator('#demoHint').click()
    expect(page.locator('#previewBoard .cb-arrow')).to_be_visible()
    page.locator('#previewBoard [data-square="f1"]').click()
    page.locator('#previewBoard [data-square="c4"]').click()
    expect(page.locator('#demoContinue')).to_be_visible()


def test_preview_supports_keyboard_moves(page,app_url):
    page.goto(app_url+'/')
    start=page.locator('#previewBoard [data-square="f1"]')
    start.focus();start.press('Enter');start.press('ArrowLeft');start.press('ArrowLeft');start.press('ArrowLeft')
    target=page.locator('#previewBoard [data-square="c1"]')
    target.press('ArrowUp')
    page.locator('#previewBoard [data-square="c2"]').press('ArrowUp')
    page.locator('#previewBoard [data-square="c3"]').press('ArrowUp')
    page.locator('#previewBoard [data-square="c4"]').press('Enter')
    expect(page.locator('#demoPrompt')).to_contain_text('That’s the idea')


def test_course_filters_report_real_counts(page,app_url):
    page.goto(app_url+'/learn/')
    page.locator('#courseFilter [data-side="black"]').click()
    expect(page.locator('.course-row:visible')).to_have_count(2)
    expect(page.locator('#courseCount')).to_have_text('2 guided courses · 10 chapters · 33 training positions')
    page.locator('#courseFilter [data-side="white"]').click()
    expect(page.locator('.course-row:visible')).to_have_count(1)
    expect(page.locator('#courseCount')).to_have_text('1 guided course · 7 chapters · 26 training positions')


@pytest.mark.parametrize('opening,title',[('italian','Italian'),('caro','Caro'),('queens','Queen')])
def test_public_course_links_open_the_selected_course(page,app_url,opening,title):
    page.goto(app_url+'/learn/')
    page.locator(f'a[href="/app/?opening={opening}#today"]').click()
    expect(page.locator('#openingGuideTitle')).to_contain_text(title,timeout=15000)
    expect(page.locator('#libBoard')).to_have_attribute('aria-busy','false')
    expect(page.locator('#italianCourse')).to_be_visible()
    expect(page).to_have_url(re.compile(r'/app/#today$'))


def test_selected_character_follows_the_player_into_lessons_and_can_change(page,app_url):
    page.goto(app_url+'/coaches/')
    page.locator('[data-choose-coach="inez"]').click()
    expect(page.locator('#coachChoiceStatus')).to_contain_text('Inez is selected')
    page.reload()
    expect(page.locator('[data-choose-coach="inez"]')).to_have_attribute('aria-pressed','true')
    page.locator('.coach-welcome a').click()
    page.locator('[data-opening="italian"]').click()
    page.locator('[data-course-chapter="essentials"]').click()
    expect(page.locator('.coach-name').first).to_contain_text('Inez')
    expect(page.locator('.coach-portrait').first).to_have_attribute('data-coach','inez')
    page.locator('#trainingCoach').select_option('theo')
    expect(page.locator('.coach-name').first).to_contain_text('Theo')
    page.reload()
    expect(page.locator('#studyCoach')).to_have_value('theo')
    page.locator('[data-training="resume"]').click()
    expect(page.locator('.coach-name').first).to_contain_text('Theo')


def test_mobile_navigation_opens_and_closes_with_escape(page,app_url):
    page.set_viewport_size({'width':390,'height':844})
    page.goto(app_url+'/')
    expect(page.locator('#publicNav')).to_be_hidden()
    page.locator('#navToggle').click()
    expect(page.locator('#publicNav')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#publicNav')).to_be_hidden()
    expect(page.locator('#navToggle')).to_be_focused()


def test_username_handoff_preserves_provider_and_encoded_username(page,app_url):
    page.goto(app_url+'/')
    page.locator('[data-provider="chesscom"]').click()
    page.locator('#user').fill('Test_player')
    with page.expect_request(lambda r:'/app/?provider=chesscom&user=Test_player&run=1' in r.url):
        page.locator('#start [type="submit"]').click()


def test_public_pages_still_work_when_storage_is_blocked(page,app_url):
    page.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}})")
    page.goto(app_url+'/coaches/')
    page.locator('[data-choose-coach="theo"]').click()
    expect(page.locator('#welcomeName')).to_contain_text('Theo')
    page.goto(app_url+'/')
    page.locator('#demoHint').click()
    expect(page.locator('#previewBoard .cb-arrow')).to_be_visible()
