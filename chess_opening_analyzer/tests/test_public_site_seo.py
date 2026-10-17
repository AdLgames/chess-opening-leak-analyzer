"""Release invariants for static content, discoverability and truthful diagrams."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'chess_opening_analyzer/tools'))
import build_public_site as site
import build_opening_pages as openings
from public_site import PUBLIC_PATHS, SITE
from public_content import COURSES, GUIDES
from build_public_diagrams import diagrams


class Page(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def attrs(self, tag, **matching):
        return [a for t,a in self.tags if t == tag and all(a.get(k)==v for k,v in matching.items())]


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp('public-site')/'public'
    shutil.copytree(ROOT/'chess-dashboard/public', out)
    site.build(out)
    return out


def test_every_public_destination_has_crawlable_content_and_consistent_metadata(built):
    titles = []
    descriptions = []
    for path in PUBLIC_PATHS:
        markup = (built/path.strip('/')/'index.html').read_text()
        parsed = Page(markup)
        assert len(parsed.attrs('h1')) == 1, path
        assert len(parsed.attrs('main', id='main')) == 1, path
        assert parsed.attrs('link', rel='canonical') == [{'rel':'canonical','href':SITE+path}]
        assert 'noindex' not in parsed.attrs('meta', name='robots')[0]['content']
        assert parsed.attrs('meta', property='og:url')[0]['content'] == SITE+path
        assert parsed.attrs('meta', property='og:image')[0]['content'].endswith('/assets/brand/social.png')
        assert parsed.attrs('meta', name='twitter:card')[0]['content'] == 'summary_large_image'
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',markup,re.S)[1])
        assert graph['@context'] == 'https://schema.org'
        assert not any('aggregateRating' in node for node in graph['@graph'])
        titles.append(re.search('<title>(.*?)</title>',markup,re.S)[1])
        descriptions.append(parsed.attrs('meta',name='description')[0]['content'])
    assert len(set(titles)) == len(titles)
    assert len(set(descriptions)) == len(descriptions)


def test_course_curriculum_and_article_schema_match_the_visible_content(built):
    catalog = site.read_courses(built)
    for info in COURSES:
        course = next(c for c in catalog if c['opening'] == info['opening'])
        markup = (built/'learn'/info['slug']/'index.html').read_text()
        parsed = Page(markup)
        for chapter in course['chapters']:
            assert any(f"chapter={chapter['id']}" in a.get('href','') for a in parsed.attrs('a'))
            assert chapter['title'] in markup
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',markup,re.S)[1])['@graph']
        assert any(n['@type']=='Course' and n['isAccessibleForFree'] for n in graph)
    for guide in GUIDES:
        markup = (built/'guides'/guide['slug']/'index.html').read_text()
        words = re.sub('<[^>]+>', ' ', ' '.join(s[2] for s in guide['sections'])).split()
        assert len(words)>600, (guide['slug'],len(words))
        assert '"@type": "Article"' in markup
        assert '/assets/positions/'+guide['slug']+'.svg' in markup


def test_internal_public_links_fragments_and_assets_resolve(built):
    for path in PUBLIC_PATHS:
        parsed = Page((built/path.strip('/')/'index.html').read_text())
        for tag, attr in parsed.tags:
            url = attr.get('href') if tag in ('a','link') else attr.get('src') if tag in ('img','script') else None
            if not url or url.startswith(('https:','http:','mailto:')) or url.startswith('/openings/'):
                continue  # opening book pages have their own generator and data thresholds
            if url.startswith('#'):
                assert any(a.get('id')==url[1:] for _,a in parsed.tags), (path,url)
                continue
            clean = url.split('?')[0].split('#')[0]
            target = built/clean.lstrip('/')
            assert target.exists(), (path,url)


def test_sitemap_excludes_private_workspaces_and_recovers_noindex_pages(built):
    xml = openings.sitemap([])
    locs = [n.text for n in ET.fromstring(xml).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    assert len(locs)==len(set(locs))
    assert set(locs)=={SITE+p for p in PUBLIC_PATHS+['/openings/']}
    assert '/app/' not in xml and '/404.html' not in xml
    assert 'noindex' in Page((built/'app/index.html').read_text()).attrs('meta',name='robots')[0]['content']
    assert 'noindex' in Page((built/'404.html').read_text()).attrs('meta',name='robots')[0]['content']
    assert 'Disallow: /app/' not in (built/'robots.txt').read_text()
    config = json.loads((ROOT/'vercel/vercel.json').read_text())
    assert any(row['source']=='/app/:path*' and row['headers'][0]['value']=='noindex, follow' for row in config['headers'])


def test_diagrams_reproduce_from_legal_positions_and_build_is_idempotent(built):
    for name, svg in diagrams():
        assert (built/'assets/positions'/(name+'.svg')).read_text() == svg
    before = {p:p.read_bytes() for p in built.rglob('*.html')}
    site.build(built)
    assert all(p.read_bytes()==data for p,data in before.items())


def test_operator_verification_and_analytics_are_validated_and_opt_in(monkeypatch):
    monkeypatch.delenv('LEAKLAB_GOOGLE_SITE_VERIFICATION',raising=False)
    assert 'google-site-verification' not in site.head('Title','Description','/')
    monkeypatch.setenv('LEAKLAB_GOOGLE_SITE_VERIFICATION','real_console_token_123456')
    assert 'content="real_console_token_123456"' in site.head('Title','Description','/')
    monkeypatch.setenv('VERCEL_ENV','preview')
    assert 'noindex, follow' in site.head('Title','Description','/')
    monkeypatch.setenv('LEAKLAB_GOOGLE_SITE_VERIFICATION','"><script>bad</script>')
    with pytest.raises(ValueError): site.head('Title','Description','/')
    app = (ROOT/'chess-dashboard/public/app/index.html').read_text()
    assert '/_vercel/insights/script.js' not in app
    config = (ROOT/'chess-dashboard/public/site-config.js').read_text()
    assert '"analyticsDomain": ""' in config
