"""Real browser + real local chess API, served together on an isolated port."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'chess_opening_analyzer'))


def unused_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture(scope='session')
def app_url():
    port = unused_port()
    # A release run performs many sessions in minutes. Rate-limit policy has its
    # own unit tests; isolated browser journeys must not exhaust the hourly budget.
    env = {**os.environ, 'LEAKLAB_READS_PER_MINUTE': '10000', 'LEAKLAB_ANALYZE_PER_HOUR': '10000', 'PYTHONPATH': str(ROOT / 'chess-dashboard')}
    command = (
        'from api_server import app; '
        'from fastapi.staticfiles import StaticFiles; '
        f'app.mount("/", StaticFiles(directory={str(ROOT / "chess-dashboard/public")!r}, html=True)); '
        f'import uvicorn; uvicorn.run(app, host="127.0.0.1", port={port}, log_level="error")'
    )
    proc = subprocess.Popen([sys.executable, '-c', command], env=env, cwd=ROOT)
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if proc.poll() is not None:
                pytest.fail('Local application server did not start')
            try:
                urllib.request.urlopen(url + '/api/health', timeout=.2)
                break
            except OSError:
                time.sleep(.1)
        else:
            pytest.fail('Local application server did not become ready')
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope='session')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        options = {'args': ['--no-sandbox']}
        if os.environ.get('LEAKLAB_CHROMIUM'):
            options['executable_path'] = os.environ['LEAKLAB_CHROMIUM']
        browser = p.chromium.launch(**options)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce', has_touch=True)
    page = context.new_page()
    page.set_default_timeout(10000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    yield page
    assert errors == [], f'Uncaught browser errors: {errors}'
    context.close()
