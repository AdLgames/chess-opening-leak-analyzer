/* Bounded, authored decisions on the existing board. Practice is not game evidence. */
(function () {
  'use strict';
  const D = window.ItalianPlans, S = window.Store, LB = window.LeakBoard;
  const L = window.LearningStore.forCourse(D.id);
  const $ = id => document.getElementById(id), esc = LB.esc;
  const sceneById = id => D.scenes.find(s => s.id === id);
  let session = null, active = false, starting = false, closing = Promise.resolve();
  let owner = null, generation = 0, status = '', returnHeading = null;
  const scene = () => sceneById(session.queue[session.index]);
  const snapshot = () => session ? JSON.parse(JSON.stringify(session)) : null;
  const button = (id, text, primary = false, extra = '') => `<button type="button" class="btn ${primary ? 'btn-primary' : 'btn-ghost'}" data-plan="${id}" ${extra}>${text}</button>`;
  const account = () => window.Auth?.state.user?.id || null;
  const pending = () => L.checkpoints().find(s => !s.finished && s.mode === 'plan' && s.version === D.version);
  const focus = () => S.prefs.get(`learning:v2:${D.id}:focus`);
  const completed = () => L.checkpoints().filter(s => s.mode === 'plan' && s.finished && s.version === D.version);
  const save = () => L.saveSession(session);

  function matchFinding(context = window.App?.reportContext()) {
    if (!context || context.demo || !context.summary) return null;
    for (const row of context.rows || []) {
      const games=Number(row.your_games), drop=Number(row.eval_drop_pawns);
      if (row.player_color !== 'white' || !Number.isInteger(games) || games < 1 || !Number.isFinite(drop) || drop < 0.5) continue;
      const s = D.scenes.find(s => !s.challenge && S.positionKey(s.position.fen) === S.positionKey(row.fen));
      const played = s?.position.legal.find(m => m.san === row.your_move);
      if (!played || s.answers.some(a => a.uci === played.uci)) continue;
      return { scene: s.id, played: played.san, uci: played.uci, fen: s.position.fen,
        games: Number(row.your_games), drop: Number(row.eval_drop_pawns), demo: false };
    }
    return null;
  }
  function thumbnail() {
    const pieces = LB.parseFen(D.scenes[1].position.fen).board;
    return `<span class="plan-mini" aria-hidden="true">${Array.from({length:64}, (_,i) => {
      const file = 'abcdefgh'[i%8], rank = 8-Math.floor(i/8), sq = file+rank;
      return `<i class="${(i%8+rank)%2 ? 'light' : 'dark'}">${pieces[sq] ? LB.pieceSvg(pieces[sq]) : ''}</i>`;
    }).join('')}</span>`;
  }
  function render(view = window.App?.currentView()) {
    const waiting = pending(), saved = focus(), finding = matchFinding();
    const cta = waiting ? 'resume' : finding ? 'finding' : 'start';
    const label = waiting ? 'Resume your plan' : finding ? 'Work on this decision' : 'Try the Italian plan';
    for (const id of ['planToday','planExplore']) {
      const host = $(id);
      host.hidden = !!window.Training?.active();
      if (host.hidden) continue;
      host.innerHTML = `<div class="plan-feature">${thumbnail()}<div><span class="journey-eyebrow">WHEN THE BOOK ENDS · ITALIAN FOR WHITE</span><h2>${waiting ? 'Your next decision is waiting.' : 'They changed the move. Can you keep the plan?'}</h2><p>${finding ? `Your imported report flags ${esc(finding.played)} in this exact position in ${finding.games} ${finding.games === 1 ? 'game' : 'games'}. Explore the idea, then try a different position.` : 'Get your king safe. Build the centre. Adapt when they strike first.'}</p><div class="plan-feature-actions">${button(cta,label+' →',true,window.Auth?.state.ready ? '' : 'disabled')}<span>About 5 minutes · 3 situations + a fresh challenge</span></div></div></div>`;
    }
    const rep = $('planRepertoire');
    rep.hidden = !saved;
    if (saved) rep.innerHTML = `<div class="plan-saved"><span class="journey-eyebrow">YOUR ITALIAN PLAN</span><h2>A plan you can adapt.</h2><p>${esc(D.promise)}</p><ol>${D.scenes.filter(s=>!s.challenge).map(s=>`<li>${esc(s.takeaway)}</li>`).join('')}</ol><div class="plan-feature-actions">${button(waiting?'resume':'start',waiting?'Resume practice →':'Practise this plan →',true)}<a class="text-link" href="#explore">Explore other openings</a></div><p class="course-note">Your saved moves stay separate. This note records an idea, not mastery.</p></div>`;
    const progress = $('planProgress'), latest = completed()[0];
    progress.hidden = !latest && !waiting && !saved;
    if (!progress.hidden) {
      const challenge = latest?.results?.find(r=>sceneById(r.scene)?.challenge);
      const first = latest?.results?.filter(r=>r.outcome==='independent').length || 0;
      progress.innerHTML = `<div class="plan-record"><span class="journey-eyebrow">ITALIAN · FROM MOVES TO PLANS</span><h2>Your decisions, in context.</h2><dl><div><dt>Guided practice</dt><dd>${latest ? `${latest.results.filter(r=>!sceneById(r.scene)?.challenge).length} situations explored · ${first} of ${latest.results.length} decisions first try without direct help` : 'Session in progress'}</dd></div><div><dt>Fresh position</dt><dd>${challenge ? challenge.outcome==='independent' ? 'Answered first try, without a hint' : 'Explored with help or another attempt' : 'Not completed yet'}</dd></div><div><dt>In your games</dt><dd>Not measured yet</dd></div></dl><p class="course-note">Imported reports can suggest this focus. Practice results do not prove you used the idea in a later game. Tracking eligible decisions in new games is a later milestone.</p>${button(waiting?'resume':'start',waiting?'Resume your plan →':'Revisit the idea →')}</div>`;
    }
    if (view === 'today' && saved && saved.home!==false && !window.Training?.active()) {
      $('dailyInvite').hidden = true;
      document.documentElement.classList.remove('has-daily-invite');
      $('planToday').classList.add('is-focus');
      $('viewToday').insertBefore($('planToday'),$('todayBoardSlot').previousElementSibling);
      const actions = $('planToday').querySelector('.plan-feature-actions');
      actions.insertAdjacentHTML('beforeend',button('daily','Or start your daily session'));
    } else if (!active && $('planToday').classList.contains('is-focus')) {
      $('planToday').classList.remove('is-focus');
      $('todayBoardSlot').after($('planToday'));
    }
  }
  function history(s) {
    const prior = completed().flatMap(c=>c.results || []).find(r=>r.scene===s.id);
    return prior ? prior.outcome==='independent' ? 'Last time you found this decision without direct help. Can you recognise the idea again?' : 'Last time you explored this with help or another attempt. Take a fresh look.' : '';
  }
  function answer() { return scene()?.answers.find(a=>a.uci===session.answer); }
  function present() {
    let s = scene(), position, arrows = [], circles = [];
    if (session.phase === 'idea') {
      const frame = D.frames[session.frame];
      position = sceneById(frame.scene).position; arrows = frame.arrows; circles = frame.circles;
    } else if (session.phase === 'recap') position = D.scenes.at(-1).answers[0].response;
    else if (session.phase === 'solved') position = answer().after;
    else if (session.phase === 'response') position = answer().response;
    else if (session.phase === 'why') position = s.wrong[session.lastMove].position;
    else {
      position = s.position;
      if (session.helped) { arrows = s.arrows; circles = s.circles; }
      if (session.phase === 'finding') arrows = [{from:session.source.uci.slice(0,2),to:session.source.uci.slice(2,4),kind:'played'}];
    }
    window.Study.training.present(position, {enabled:session.phase==='solve',orientation:'white',arrows,circles,title:'Italian · When the book ends'});
  }
  function renderSession(focusTitle = false) {
    if (!active) return;
    const s = scene(), phase = session.phase, done = phase==='recap';
    let title = s?.title, text = '', prompt = s?.prompt || '', controls = '', event = 'learn';
    if (phase==='finding') {
      title = 'One decision from your games.';
      text = `Your report flags ${session.source.played} in ${session.source.games} ${session.source.games===1?'game':'games'} at this exact position, with an estimated evaluation drop of ${session.source.drop.toFixed(1)} pawns. Let’s look at the decision behind the move.`;
      prompt = `Your report: ${session.source.played}. White to move in the position before that move.`;
      controls = button('idea','Look at the idea →',true);
    } else if (phase==='idea') {
      const frame = D.frames[session.frame]; title = frame.title; text = frame.text; prompt = frame.title+'. Follow the marked squares and arrows.';
      controls = session.frame ? button('try','Try the first situation →',true) : button('frame-next','See the central idea →',true);
      if (session.frame) controls += button('frame-back','← Previous idea');
      event = 'explain';
    } else if (phase==='solve') {
      text = status || (session.helped ? s.hint : (s.challenge ? 'The move order has changed. Use what the position tells you. No direct answer is shown unless you ask.' : s.idea));
      controls = button('hint','Show the idea')+button('reveal','Show a move');
      if (s.wrong[session.lastMove]) controls += button('why','Show the consequence');
      event = status ? 'planRetry' : session.helped ? 'hinted' : 'plan';
    } else if (phase==='why') {
      text = s.wrong[session.lastMove].text;
      prompt = `After ${session.lastMove} ${s.wrong[session.lastMove].reply}. Look at the consequence.`;
      controls = button('back','Back to your decision →',true); event = 'explain';
    } else if (phase==='solved' || phase==='response') {
      text = answer().why; prompt = phase==='solved' ? `${answer().san} played. ${s.takeaway}` : `Black replies ${answer().reply}. ${s.takeaway}`;
      controls = (phase==='solved' ? button('response','See their reply →',true) : '')+button('next',session.index===session.queue.length-1?'See your recap →':'Next situation →',phase==='response');
      event = session.helped || session.explored || session.revealed ? 'assisted' : 'solved';
    } else if (done) {
      title = 'You have a plan. Keep it flexible.'; prompt = 'Practice complete. Look at the centre after Black’s reply.';
      text = 'A safe king, a supported centre, and a fresh check of their threat. Take those questions into your next Italian game.';
      controls = button('save-focus',focus()?'Plan saved in your repertoire':'Save my Italian plan →',true,focus()?'disabled':'')+button('done','Back to the board'); event = 'explain';
    }
    $('trainingBoardPrompt').textContent = prompt;
    const results = session.results || [], challenge = results.find(r=>sceneById(r.scene)?.challenge);
    const guided = results.filter(r=>!sceneById(r.scene)?.challenge);
    $('trainingPanel').className = 'plan-session';
    $('trainingPanel').innerHTML = `<div class="training-top"><span>${done?'YOUR ITALIAN RECAP':phase==='idea'?'LOOK AT THE IDEA':phase==='finding'?'FROM YOUR IMPORTED REPORT':s.challenge?'FRESH-POSITION CHALLENGE':esc(s.tag)}</span><span>${done?'4/4':phase==='idea'||phase==='finding'?'Start':`${session.index+1}/4`}</span></div><progress max="4" value="${done?4:session.index}" class="training-progress" aria-label="Italian plan session progress"></progress><h3 id="planTitle" tabindex="-1">${esc(title)}</h3><p class="plan-explanation" id="planFeedback" role="status">${esc(text)}</p>
      ${phase==='idea' ? `<p class="visual-legend">Read-only diagram. ${esc(D.frames[session.frame].arrows.map(a=>`Arrow ${a.from} to ${a.to}.`).join(' '))} Marked squares: ${esc(D.frames[session.frame].circles.map(c=>c.square).join(', '))}.</p>` : ''}
      ${phase==='solve' && history(s) ? `<p class="plan-memory">${esc(history(s))}</p>` : ''}
      ${done ? `<div class="plan-recap"><dl><div><dt>Situations explored</dt><dd>${guided.length} of 3</dd></div><div><dt>Fresh position</dt><dd>${challenge?.outcome==='independent'?'First try, without direct help':'Explored with help or another attempt'}</dd></div><div><dt>Used in your games</dt><dd>Not measured by this practice</dd></div></dl><label for="planReflection">What would help next time? <span>Optional</span></label><select id="planReflection"><option value="">Choose if useful</option>${[['line','Remembering the move order'],['threat','Checking their threat'],['plan','Knowing which plan fits'],['ready','Ready to try it in a game']].map(([v,t])=>`<option value="${v}" ${session.reflection===v?'selected':''}>${t}</option>`).join('')}</select><p class="course-note">This is your reflection, not an assessment of your thoughts. A practice score is not evidence of better results in games.</p></div>` : ''}
      <div class="training-actions">${controls}${!done?button('pause','Pause & exit'):''}</div><p class="training-storage">${L.durable()?'Your place is saved on this device.':'Device storage is unavailable. Progress stays in this tab only.'} ${window.Auth?.signedIn()?'Signed in for account backup.':''}</p><p class="plan-source">Guided practice for White · selected positions, not a complete Italian repertoire.</p>`;
    const coachPrompt = phase==='solve' && (status || session.helped) ? status || s.hint : prompt;
    window.Coach.onBoard({event,prompt:done?text:coachPrompt,key:`${session.id}:${session.index}:${phase}:${session.frame}`,seed:session.index});
    present();
    if (focusTitle) {
      $('planTitle').focus({preventScroll:true});
      if(matchMedia('(max-width:860px)').matches) { $('main').scrollTop=0;window.scrollTo(0,0); }
    }
  }
  async function start({fromFinding = false, resume = true} = {}) {
    if (starting || !window.Auth?.state.ready) return;
    const origin = window.App.currentView(), initialOwner = account(), token = ++generation;
    starting = true;
    try {
      await window.Training.pause();
      await closing;
      if (token!==generation || origin!==window.App.currentView() || initialOwner!==account()) return;
      const source = fromFinding ? matchFinding() : null;
      const prior = resume ? pending() : null;
      const ids = D.scenes.filter(s=>!s.challenge).map(s=>s.id);
      const queue = source ? [source.scene,...ids.filter(id=>id!==source.scene),D.scenes.at(-1).id] : [...ids,D.scenes.at(-1).id];
      session = prior || {id:L.uid(),mode:'plan',version:D.version,created:Date.now(),queue,index:0,frame:0,phase:source?'finding':'idea',source,results:[],helped:false,explored:0,answer:'',lastMove:'',revealed:false,finished:false};
      returnHeading = {title:$('openingGuideTitle').textContent,meta:$('guideMeta').textContent};
      owner = account(); active = true; status = '';
      save(); window.App.go('today'); window.Workspace.setPanel('study');
      $('openingGuideTitle').textContent = 'When the book ends'; $('guideMeta').textContent = D.subtitle;
      document.querySelector('.library-panel').classList.add('is-training','is-plan');
      $('trainingPanel').hidden = false; $('trainingBoardPrompt').hidden = false;
      $('libBoard').setAttribute('aria-label','Italian plan practice board'); $('libBoard').setAttribute('aria-describedby','trainingBoardPrompt');
      window.Study.training.begin(attempt);
      renderSession();
      if (matchMedia('(max-width:860px)').matches) $('libBoard').scrollIntoView({block:'nearest'});
    } finally { starting = false; }
  }
  function pause(keep = true) {
    if (!active) return closing;
    if (keep && owner===account()) save();
    active = false; status = ''; generation++;
    window.Coach.hideBoard();
    document.querySelector('.library-panel').classList.remove('is-training','is-plan');
    $('trainingPanel').hidden = true; $('trainingPanel').className = '';
    $('trainingBoardPrompt').hidden = true;
    $('libBoard').setAttribute('aria-label','Explorer board'); $('libBoard').removeAttribute('aria-describedby');
    closing = window.Study.training.end().finally(()=>{
      if (active || window.Training.active()) return;
      if (returnHeading) { $('openingGuideTitle').textContent=returnHeading.title; $('guideMeta').textContent=returnHeading.meta; }
      window.Workspace.refreshGuide(); window.Training.overview();
      window.DailySession.render(); window.Clubhouse.render(); render();
    });
    return closing;
  }
  function attempt(move, revealed = false) {
    if (!active || session.phase!=='solve' || owner!==account()) return;
    const s = scene(), chosen = s.answers.find(a=>a.uci===move.uci);
    if (!chosen) {
      session.explored++; session.lastMove=move.san;
      status = s.wrong[move.san]?.text || `${move.san} is legal. This exercise is looking for a different decision: ${s.prompt} Other legal choices are not automatically chess mistakes.`;
      save(); renderSession(); return;
    }
    session.answer=chosen.uci; session.revealed ||= revealed;
    const result = {scene:s.id,played:chosen.san,outcome:session.revealed?'revealed':session.helped?'hinted':session.explored?'missed':'independent',at:Date.now()};
    session.results.push(result); session.phase='solved';
    L.attempt(`${session.id}:${s.id}`,s.id,result.outcome,chosen.san);
    save(); status=''; renderSession(revealed);
  }
  function dispatch(action) {
    if (action==='start' || action==='resume') return start();
    if (action==='finding') return start({fromFinding:true});
    if (action==='daily') {
      if(focus()) S.prefs.set(`learning:v2:${D.id}:focus`,{...focus(),home:false,updated:Date.now()});
      window.DailySession.render();
      document.querySelector('#dailyInvite [data-daily=start],#dailyInvite [data-daily=resume]')?.click();
      return;
    }
    if (!active || owner!==account()) return;
    if (action==='pause' || action==='done') return pause();
    if (action==='idea') { session.phase='idea';session.frame=0; }
    if (action==='frame-next') session.frame=1;
    if (action==='frame-back') session.frame=0;
    if (action==='try') session.phase='solve';
    if (action==='hint' && session.phase==='solve') { session.helped=true;status=scene().hint; }
    if (action==='reveal' && session.phase==='solve') return attempt(scene().answers[0],true);
    if (action==='why' && scene().wrong[session.lastMove]) { session.phase='why';session.helped=true; }
    if (action==='back') { session.phase='solve';status='Take another look. The consequence you explored counts as help.'; }
    if (action==='response' && session.phase==='solved') session.phase='response';
    if (action==='next' && ['solved','response'].includes(session.phase)) {
      session.index++;
      if (session.index===session.queue.length) { session.phase='recap';session.finished=true; }
      else { session.phase='solve';session.helped=false;session.explored=0;session.answer='';session.lastMove='';session.revealed=false;status=''; }
    }
    if (action==='save-focus' && session.finished) S.prefs.set(`learning:v2:${D.id}:focus`,{id:D.id,session:session.id,home:true,at:Date.now(),updated:Date.now()});
    save(); renderSession(['frame-next','frame-back','try','next','back','response','hint','why'].includes(action));
  }
  document.addEventListener('click',event=>{
    const b = event.target.closest('[data-plan]');
    if (b && !b.disabled) Promise.resolve(dispatch(b.dataset.plan)).catch(()=>{
      if (active) { status='Your place is saved. Pause and resume to try again.';renderSession(); }
    });
  });
  document.addEventListener('change',event=>{
    if (event.target.id==='planReflection' && active && owner===account()) {session.reflection=event.target.value;save();}
  });
  window.addEventListener('chess:report',()=>{if(!active)render();});
  window.addEventListener('storage',event=>{if(event.key?.startsWith('leaklab:pref:learning:') && !active)render();});
  window.Auth?.onChange(()=>{if(active && owner!==account())pause(false);if(!active)render();});
  window.Plans = {render,start,pause,matchFinding,settled:()=>closing,active:()=>active,info:snapshot};
})();
