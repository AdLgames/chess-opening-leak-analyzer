"""Pilot curriculum positions, scoped chapters and tactical claims."""
import json
from pathlib import Path

import chess

SOURCE = Path(__file__).resolve().parents[2] / 'chess-dashboard/public/app/italian-course.js'
COURSE = json.loads(SOURCE.read_text().split('window.ItalianCourse = ', 1)[1].rstrip(';\n'))
CARDS = {card['id']:card for card in COURSE['cards']}


def position(card):
    board = chess.Board()
    for san in card['line']:
        board.push_san(san)
    return board


def test_every_lesson_and_practical_start_is_legal():
    assert len(CARDS) == len(COURSE['cards']) == 17
    assert len(COURSE['chapters']) == 4
    for card in CARDS.values():
        board = position(card)
        assert board.turn == chess.WHITE
        assert card['idea'] and card['hint'] and card['why']
        board.push_san(card['move'])
        assert board.is_valid() and not board.is_game_over()
    used = [key for chapter in COURSE['chapters'] for key in chapter['cards']]
    assert set(used) == set(CARDS)
    assert len(used) == len(set(used))


def test_two_knights_and_main_line_share_the_claimed_structure():
    main = position(CARDS['re1'])
    alternate = position(CARDS['two-c3'])
    alternate.push_san('c3')
    alternate.push_san('d6')
    assert main.epd() == alternate.epd()


def test_f7_fork_and_follow_up_threats_are_real():
    board = position(CARDS['f7'])
    board.push_san('Nxf7')
    assert {chess.D8, chess.H8}.issubset(board.attacks(chess.F7))
    board = position(CARDS['qf3'])
    board.push_san('Qf3+')
    assert board.is_check()
    assert chess.D5 in board.attacks(chess.F3)
    board = position(CARDS['nc3'])
    board.push_san('Nc3')
    assert chess.D5 in board.attacks(chess.C3)
