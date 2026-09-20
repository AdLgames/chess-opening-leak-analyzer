"""The trap catalogue and the scan over a player's games.

String work over SAN, so this runs without python-chess or an engine:
`python -m pytest tests -q` or `python tests/test_traps.py`.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.traps import Trap, load_traps, scan_games  # noqa: E402


@dataclass
class FakeGame:
    game_id: str
    player_color: str
    line_san: str


def test_catalogue_is_consistent():
    traps = load_traps()
    assert traps, "the catalogue should not be empty"
    for trap in traps:
        # the side to move after the line is the side the trap is aimed at
        expected = "white" if len(trap.line) % 2 == 0 else "black"
        assert trap.victim == expected, trap.key
        assert trap.instead not in trap.losing, f"{trap.key}: the way out cannot also lose"
        assert trap.move_number >= 1
    assert len({t.key for t in traps}) == len(traps), "trap keys must be unique"


def test_falling_for_scholars_mate_is_counted():
    games = [
        FakeGame('g1', 'black', 'e4 e5 Bc4 Nc6 Qh5 Nf6 Qxf7#'),
        FakeGame('g2', 'black', 'e4 e5 Bc4 Nc6 Qh5 g6 Qf3 Nf6'),
        FakeGame('g3', 'black', 'e4 e5 Bc4 Nc6 Qh5 Nf6 Qxf7#'),
    ]
    out = scan_games(games)
    scholars = next(t for t in out['traps'] if t['key'] == 'scholars_mate')
    assert scholars['met'] == 3 and scholars['fell'] == 2 and scholars['held'] == 1
    assert scholars['instead'] == 'g6'
    assert scholars['move_number'] == 3, "Black has to get move 3 right"
    assert out['fell'] == 2


def test_only_the_side_the_trap_aims_at_is_scanned():
    """The same moves, played by the other colour, are not this player's problem."""
    games = [FakeGame('g1', 'white', 'e4 e5 Bc4 Nc6 Qh5 Nf6 Qxf7#')]
    assert scan_games(games)['traps'] == []


def test_check_and_annotation_marks_do_not_break_matching():
    trap = Trap(key='k', name='n', eco='', opening='', line=('d4', 'e5', 'dxe5', 'Nc6', 'Nf3', 'Qe7'),
                victim='white', losing=('Bf4',), instead='Nc3', refutation='Qb4+', note='')
    games = [FakeGame('g1', 'white', 'd4 e5! dxe5 Nc6 Nf3 Qe7 Bf4?? Qb4+')]
    out = scan_games(games, [trap])
    assert out['traps'][0]['fell'] == 1


def test_a_game_that_stops_on_the_trap_line_never_asked_the_question():
    games = [FakeGame('g1', 'black', 'e4 e5 Bc4 Nc6 Qh5')]
    assert scan_games(games)['traps'] == []


def test_a_different_move_order_is_not_claimed_as_a_hit():
    """Prefix matching only: we never report a trap the player did not literally play into."""
    games = [FakeGame('g1', 'black', 'e4 e5 Qh5 Nc6 Bc4 Nf6')]
    assert scan_games(games)['traps'] == []


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print(f'ok {name}')
