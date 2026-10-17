"""Character reactions stay playful, accessible and separate from chess/recall state."""
import pytest
import re
from playwright.sync_api import expect
from test_training import ready, answer


@pytest.mark.parametrize('guide,name',[('maya','Maya'),('theo','Theo'),('inez','Inez')])
def test_each_guide_has_a_voice_and_can_be_poked_without_changing_the_board(page,app_url,guide,name):
    page.goto(app_url+'/')
    page.evaluate('(id)=>{Store.prefs.set("studyCoach",id);BoardCompanion.refresh()}',guide)
    expect(page.locator('#previewCompanion .companion-byline')).to_have_text(name)
    before=page.locator('#previewCompanion .companion-quip').inner_text()
    fen=page.locator('#previewBoard').evaluate('(el)=>el.innerHTML')
    prefs=page.evaluate('Store.prefs.all()')
    person=page.locator('#previewCompanion .companion-person')
    person.focus();person.press('Enter')
    assert page.locator('#previewCompanion .companion-quip').inner_text() != before
    assert page.locator('#previewBoard').evaluate('(el)=>el.innerHTML') == fen
    assert page.evaluate('Store.prefs.all()') == prefs


def test_preview_reactions_follow_retry_hint_and_success_without_recording_recall(page,app_url):
    page.goto(app_url+'/')
    prefs=page.evaluate('Store.prefs.all()')
    play_board=page.locator('#previewBoard')
    play_board.locator('[data-square="f1"]').click();play_board.locator('[data-square="b5"]').click()
    expect(page.locator('#previewCompanion')).to_have_attribute('data-reaction','retry')
    expect(page.locator('#demoFeedback')).to_contain_text('Bb5 is legal')
    page.locator('#demoHint').click()
    expect(page.locator('#previewCompanion')).to_have_attribute('data-reaction','hinted')
    play_board.locator('[data-square="f1"]').click();play_board.locator('[data-square="c4"]').click()
    expect(page.locator('#previewCompanion')).to_have_attribute('data-reaction','solved')
    expect(page.locator('#demoContinue')).to_be_visible()
    assert page.evaluate('Store.prefs.all()') == prefs


def test_quiet_mode_is_reversible_persistent_and_keeps_focus_out_of_hidden_content(page,app_url):
    page.goto(app_url+'/')
    page.locator('#previewCompanion .companion-dismiss').click()
    expect(page.locator('#previewCompanion .companion-show')).to_be_focused()
    expect(page.locator('#previewCompanion .companion-scene')).to_be_hidden()
    page.reload()
    expect(page.locator('#previewCompanion .companion-scene')).to_be_hidden()
    page.locator('#previewCompanion .companion-show').click()
    expect(page.locator('#previewCompanion .companion-person')).to_be_focused()
    expect(page.locator('#previewCompanion .companion-scene')).to_be_visible()
    page.goto(app_url+'/app/')
    expect(page.locator('#boardCompanion .companion-person')).to_be_visible()


@pytest.mark.parametrize('opening,course',[('italian','italian-v1'),('caro','caro-v1')])
def test_lesson_reactions_distinguish_independent_moves_from_assisted_practice(page,app_url,opening,course):
    ready(page,app_url)
    if opening!='italian':
        page.evaluate('App.go("explore")');page.locator(f'[data-opening="{opening}"]').click()
    page.locator('[data-course-chapter="essentials"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    cards=page.evaluate('(id)=>OpeningCourses.find(c=>c.id===id).cards',course)
    answer(page,cards[0])
    expect(page.locator('#boardCompanion')).to_have_attribute('data-reaction','solved')
    page.locator('[data-training="next"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    page.locator('[data-training="hint"]').click()
    expect(page.locator('#boardCompanion')).to_have_attribute('data-reaction','hinted')
    answer(page,cards[1])
    expect(page.locator('#boardCompanion')).to_have_attribute('data-reaction','assisted')
    assert page.evaluate('(id)=>LearningStore.forCourse(id).summary(OpeningCourses.find(c=>c.id===id).cards).attempts.length',course)==0


@pytest.mark.parametrize('width,height',[(360,800),(390,844),(768,1024),(1440,1000)])
def test_characters_and_clouds_never_cover_squares_and_phone_actions_stay_visible(page,app_url,width,height):
    page.set_viewport_size({'width':width,'height':height})
    for path,host,board in [('/','#previewCompanion','#previewBoard'),('/app/','#boardCompanion','#libBoard')]:
        page.goto(app_url+path)
        if path=='/app/':
            expect(page.locator('#libBoard')).to_have_attribute('aria-busy','false')
            page.locator('[data-course-chapter="essentials"]').click()
            expect(page.locator('[data-training="hint"]')).to_be_enabled()
        for part in ['.companion-person','.companion-cloud']:
            actor=page.locator(host+' '+part).bounding_box()
            target=page.locator(board).bounding_box()
            assert actor['y']+actor['height'] <= target['y']+.1
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        if path=='/app/' and width<=390:
            button=page.locator('[data-training="hint"]').bounding_box()
            assert button['y']+button['height']<=height-62


def test_character_can_change_mid_lesson_and_hide_portrait_keeps_the_instruction_visible(page,app_url):
    ready(page,app_url)
    page.locator('[data-course-chapter="essentials"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    prompt=page.locator('#trainingBoardPrompt').text_content()
    expect(page.locator('#boardCompanion .companion-task')).to_have_text(prompt)
    page.locator('#trainingCoach').select_option('inez')
    expect(page.locator('#boardCompanion .companion-byline')).to_have_text('Inez')
    page.locator('[data-training="toggle-coach"]').click()
    expect(page.locator('#boardCompanion')).to_be_hidden()
    expect(page.locator('#trainingBoardPrompt')).not_to_have_class(re.compile(r'\bcompanion-prompt\b'))
    expect(page.locator('#trainingBoardPrompt')).to_be_visible()
    page.locator('[data-training="toggle-coach"]').click()
    expect(page.locator('#boardCompanion .companion-byline')).to_have_text('Inez')


def test_quiet_mode_does_not_change_learning_state_and_survives_a_resume(page,app_url):
    ready(page,app_url)
    page.locator('[data-course-chapter="essentials"]').click()
    expect(page.locator('[data-training="hint"]')).to_be_enabled()
    before=page.evaluate('Object.fromEntries(Object.entries(Store.prefs.all()).filter(([k])=>k.startsWith("learning:")))')
    page.locator('#boardCompanion .companion-dismiss').click()
    expect(page.locator('#trainingBoardPrompt')).to_be_visible()
    after=page.evaluate('Object.fromEntries(Object.entries(Store.prefs.all()).filter(([k])=>k.startsWith("learning:")))')
    assert before==after
    page.reload();page.locator('[data-training="resume"]').click()
    expect(page.locator('#boardCompanion .companion-show')).to_be_visible()
    expect(page.locator('#boardCompanion .companion-scene')).to_be_hidden()
    page.locator('#boardCompanion .companion-show').click()
    expect(page.locator('#boardCompanion .companion-task')).to_have_text(page.locator('#trainingBoardPrompt').text_content())


def test_reduced_motion_disables_the_character_reaction_animation(page,app_url):
    page.emulate_media(reduced_motion='reduce')
    page.goto(app_url+'/')
    page.locator('#previewCompanion .companion-person').click()
    assert page.locator('#previewCompanion .companion-person').evaluate('(el)=>getComputedStyle(el).animationName')=='none'
