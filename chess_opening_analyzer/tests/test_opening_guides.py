"""Every opening preview and continuation is an actual legal chess position."""
import json
from pathlib import Path

import chess

SOURCE = Path(__file__).resolve().parents[2] / 'chess-dashboard/public/app/opening-guides.js'
GUIDES = json.loads(SOURCE.read_text().split('window.OpeningGuides = ', 1)[1].rstrip(';\n'))


def test_library_has_distinct_openings_and_legal_previews():
    assert len(GUIDES) == len({guide['id'] for guide in GUIDES}) == 20
    assert {guide['side'] for guide in GUIDES} == {'white', 'black'}
    for guide in GUIDES:
        board = chess.Board()
        for san in guide['line']:
            board.push_san(san)
        assert board.fen() == guide['fen'], guide['name']
        assert guide['idea'] and guide['plan']


def test_every_advertised_continuation_replays_to_its_preview():
    for guide in GUIDES:
        assert len(guide['branches']) == 2
        for branch in guide['branches']:
            board = chess.Board()
            for san in branch['line']:
                board.push_san(san)
            assert board.fen() == branch['fen'], (guide['name'], branch['name'])
