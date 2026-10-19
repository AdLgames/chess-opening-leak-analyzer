"""Shared static public-site presentation; standard-library-only at deploy time."""
import html
import json
import os
import re

SITE = 'https://chessleaklab.co.uk'
NAME = 'Opening Leak Lab'
PUBLIC_PATHS = ['/', '/learn/', '/coaches/', '/guides/',
                '/learn/italian-game/', '/learn/caro-kann/', '/learn/queens-gambit-declined/',
                '/guides/italian-game-for-beginners/', '/guides/caro-kann-plans/',
                '/guides/remember-chess-openings/', '/about/', '/contact/', '/privacy/']


def esc(value):
    return html.escape(str(value), quote=True)


def json_script(data):
    return json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')


def head(title, description, path, *, extra_schema=None, preview=False, noindex=False):
    graph = [{'@type': 'Organization', '@id': SITE + '/#organization', 'name': NAME,
              'url': SITE + '/', 'logo': SITE + '/assets/brand/mark.svg',
              'sameAs': ['https://github.com/AdLgames/chess-opening-leak-analyzer']}]
    if path == '/':
        graph.append({'@type': 'WebSite', '@id': SITE + '/#website', 'name': NAME,
                      'url': SITE + '/', 'inLanguage': 'en-GB', 'publisher': {'@id': SITE + '/#organization'}})
    graph.extend(extra_schema or [])
    token = os.environ.get('LEAKLAB_GOOGLE_SITE_VERIFICATION', '').strip()
    if token and not re.fullmatch(r'[A-Za-z0-9_-]{10,200}', token):
        raise ValueError('LEAKLAB_GOOGLE_SITE_VERIFICATION must contain the token, not an HTML tag.')
    verify = f'<meta name="google-site-verification" content="{esc(token)}" />' if token else ''
    noindex = noindex or os.environ.get('VERCEL_ENV') in ('preview', 'development')
    robots = 'noindex, follow' if noindex else 'index, follow, max-image-preview:large'
    return f'''<head>
<meta charset="utf-8" /><script>document.documentElement.classList.add("js")</script><meta name="viewport" content="width=device-width,initial-scale=1" />
<meta name="theme-color" content="#173D32" /><title>{esc(title)}</title>
<meta name="description" content="{esc(description)}" /><meta name="robots" content="{robots}" />
<link rel="canonical" href="{SITE}{path}" />{verify}
<meta property="og:type" content="{'article' if '/guides/' in path and path != '/guides/' else 'website'}" />
<meta property="og:site_name" content="{NAME}" /><meta property="og:locale" content="en_GB" />
<meta property="og:url" content="{SITE}{path}" /><meta property="og:title" content="{esc(title)}" />
<meta property="og:description" content="{esc(description)}" /><meta property="og:image" content="{SITE}/assets/brand/social.png" />
<meta property="og:image:width" content="1200" /><meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="Opening Leak Lab — learn chess openings on the board with illustrated study guides" />
<meta name="twitter:card" content="summary_large_image" /><meta name="twitter:title" content="{esc(title)}" />
<meta name="twitter:description" content="{esc(description)}" /><meta name="twitter:image" content="{SITE}/assets/brand/social.png" />
<link rel="icon" href="/assets/brand/mark.svg" type="image/svg+xml" />
<link rel="preload" href="/vendor/fonts/inter-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin />
<link rel="stylesheet" href="/vendor/fonts.css" /><link rel="stylesheet" href="/landing.css" />
<link rel="stylesheet" href="/public-site.css" />{'<link rel="stylesheet" href="/companion.css" />' if preview else ''}
<script type="application/ld+json">{json_script({'@context':'https://schema.org','@graph':graph})}</script>
<script defer src="/site-config.js"></script><script defer src="/metrics.js"></script><script defer src="/public-site.js"></script>
</head>'''


def header(current=''):
    links = [('/learn/', 'Courses'), ('/guides/', 'Opening guides'), ('/coaches/', 'Meet your guides'), ('/openings/', 'Database')]
    nav = ''
    for href, label in links:
        active = ' aria-current="page"' if current == href else ''
        nav += f'<a href="{href}"{active}>{label}</a>'
    return f'''<a class="skip" href="#main">Skip to content</a><header class="site-head shell">
<a class="wordmark" href="/" aria-label="Opening Leak Lab home"><img src="/assets/brand/mark.svg" width="42" height="42" alt="" /><span>Opening <span class="brand-second">Leak Lab</span><small class="brand-motto">GOOD PLANS. GOOD COMPANY.</small></span></a>
<button class="nav-toggle" id="navToggle" aria-expanded="false" aria-controls="publicNav">Menu <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg></button>
<nav id="publicNav" aria-label="Main navigation"><div class="public-menu-intro"><span class="coach-art" data-coach="maya" aria-hidden="true"></span><div><strong>Make yourself at home.</strong><span>Your next good move is waiting.</span></div></div>{nav}<a class="nav-join" href="/app/?connect=lichess#progress/games">Bring my games</a><a class="nav-open" href="/app/">Open workspace →</a></nav></header>'''


def account_banner():
    return '''<section class="public-connect shell" aria-labelledby="publicConnectTitle"><div class="public-connect-copy"><span class="eyebrow">YOUR GAMES. YOUR NEXT GOOD MOVE.</span><h2 id="publicConnectTitle">Make this your<br /><em>chess corner.</em></h2><p>Create an account, bring in your games and find the opening decisions worth practising.</p><div class="public-connect-actions"><a class="button primary" href="/app/?connect=lichess#progress/games">Bring my Lichess games →</a><a class="button outline" href="/app/?connect=chesscom#progress/games">Bring my Chess.com games →</a></div><small>Lichess supports sign-in. Chess.com games are imported by public username. No chess-site password needed.</small></div><span class="coach-art public-connect-coach" data-coach="maya" aria-hidden="true"></span></section>'''


def footer():
    return '''<footer class="site-foot shell">
<a class="wordmark" href="/"><img src="/assets/brand/mark.svg" width="32" height="32" alt="" /><span>Opening Leak Lab</span></a>
<p>A little understanding. A better next move.</p>
<nav aria-label="Footer"><a href="/about/">About &amp; sources</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy &amp; your data</a><a href="/guides/">Learning guides</a><a href="/assets/brand/wordmark.svg" download>Download logo</a><a href="/app/">Your workspace →</a></nav>
<small>Independent chess learning · Lichess-derived opening data (CC0) · Stockfish (GPLv3)</small>
</footer>'''


def crumbs(items):
    links = '<a href="/">Home</a>'
    schema = [{'@type':'ListItem','position':1,'name':'Home','item':SITE+'/'}]
    for i, (label, path) in enumerate(items, 2):
        links += f'<span aria-hidden="true">/</span><a href="{path}">{esc(label)}</a>'
        schema.append({'@type':'ListItem','position':i,'name':label,'item':SITE+path})
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb">{links}</nav>', {'@type':'BreadcrumbList','itemListElement':schema}


def scripts(preview=False):
    if not preview:
        return ''
    return '''<script defer src="/app/store.js"></script><script defer src="/app/board.js"></script>
<script defer src="/public-courses.js"></script><script defer src="/lesson-previews.js"></script>
<script defer src="/companion.js"></script><script defer src="/landing.js"></script>'''


def preview_board(opening='italian', tabs=False):
    tab_html = '''<div class="demo-tabs" role="group" aria-label="Try an opening"><button data-preview="italian" aria-pressed="true">Italian</button><button data-preview="caro" aria-pressed="false">Caro-Kann</button><button data-preview="queens" aria-pressed="false">Queen’s Gambit</button></div>''' if tabs else ''
    return f'''<div class="demo-stage" id="try"><div class="board-top"><span><i class="live-dot"></i> Your first idea. Try it.</span><span id="demoSide">{'White' if opening == 'italian' else 'Black'} to move</span></div>{tab_html}
<div class="board-stage"><div id="previewCompanion" hidden></div><div id="previewBoard" class="preview-board" aria-label="Interactive opening lesson"><img src="/assets/positions/preview-{opening}.svg" width="640" height="640" fetchpriority="high" alt="{'Italian Game before Bc4' if opening == 'italian' else 'Caro–Kann before …d5' if opening == 'caro' else 'Queen’s Gambit Declined before …e6'}. The text below explains the move." /></div></div>
<div class="demo-coaching"><span class="coach-art demo-coach" data-coach="maya" aria-hidden="true"></span><div><span class="eyebrow" id="demoCoachName">Maya · Your study guide</span><h2 id="demoPrompt">{'Bring your bishop into the game.' if opening == 'italian' else 'Build your centre with …d5.' if opening == 'caro' else 'Give your centre some support.'}</h2><p id="demoFeedback" role="status" aria-live="polite">{'Try Bc4: the bishop develops and points towards f7.' if opening == 'italian' else 'Try …d5: the c6 pawn supports the central challenge.' if opening == 'caro' else 'Try …e6: the e-pawn supports d5.'}</p><div class="demo-actions"><button id="demoHint" class="text-button">A little hint →</button><button id="demoReset" class="text-button">Start again ↺</button><a id="demoContinue" href="/app/?opening={opening}&amp;chapter=essentials#today" hidden>Keep learning →</a></div><noscript><p>Board interaction needs JavaScript. You can read the explanation and guides without it.</p></noscript></div></div></div>'''
