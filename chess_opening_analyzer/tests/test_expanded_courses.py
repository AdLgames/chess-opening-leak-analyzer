"""Every lesson, teaching continuation and historical score replays legally."""
import json
from pathlib import Path

import chess

APP = Path(__file__).resolve().parents[2] / 'chess-dashboard/public/app'
COURSES = json.loads((APP/'opening-courses.js').read_text().split('window.OpeningCourses = ',1)[1].rstrip(';\n'))
GAMES = json.loads((APP/'model-games.js').read_text().split('window.ModelGames = ',1)[1].rstrip(';\n'))


def test_course_catalog_has_legal_positions_for_both_colours():
    assert [(c['id'],len(c['cards'])) for c in COURSES] == [('italian-v1',26),('caro-v1',15),('qgd-v1',18)]
    for course in COURSES:
        cards = {c['id']:c for c in course['cards']}
        assert len(cards) == len(course['cards'])
        assert {key for chapter in course['chapters'] for key in chapter['cards']} == set(cards)
        for card in cards.values():
            board = chess.Board()
            for move in card['line']: board.push_san(move)
            assert board.fen() == card['fen']
            assert ('white' if board.turn else 'black') == course['side']
            move = board.parse_san(card['move'])
            assert move.uci() == card['uci']
            board.push(move)
            assert board.fen() == card['afterFen']
            assert board.is_valid() and not board.is_game_over()
            for wrong, feedback in card.get('mistakes',{}).items():
                probe = chess.Board(card['fen'])
                assert feedback['line'][0] == wrong
                for token in feedback['line']: probe.push_san(token)
        assert len(course['anchors']) == 4
        for line in course['anchors']:
            board = chess.Board()
            for move in line: board.push_san(move)
            assert ('white' if board.turn else 'black') != course['side']


def test_original_italian_keys_and_content_remain_compatible():
    old = json.loads((APP/'italian-course.js').read_text().split('window.ItalianCourse = ',1)[1].rstrip(';\n'))
    new = COURSES[0]
    assert new['id'] == old['id']
    for original, expanded in zip(old['cards'],new['cards']):
        for key,value in original.items(): assert expanded[key] == value
    for original,expanded in zip(old['chapters'],new['chapters']): assert original == expanded


def test_historical_games_are_complete_and_annotations_are_at_real_positions():
    assert {g['course'] for g in GAMES} == {c['id'] for c in COURSES}
    for game in GAMES:
        board = chess.Board()
        for move in game['moves']: board.push_san(move)
        assert board.is_valid()
        assert game['result'] in ('1-0','0-1')
        if board.is_game_over(): assert board.result() == game['result']
        assert game['notes'][0]['ply'] == 0
        assert game['notes'][-1]['ply'] == len(game['moves'])
        assert all(0 <= n['ply'] <= len(game['moves']) and n['text'] for n in game['notes'])
        assert game['source'].startswith('https://')


def test_elephant_trap_leaves_black_an_extra_minor_piece():
    card = next(c for c in COURSES[2]['cards'] if c['id']=='elephant-finish')
    board = chess.Board(card['afterFen'])
    assert not board.queens
    black = sum(len(board.pieces(p,chess.BLACK)) for p in (chess.KNIGHT,chess.BISHOP))
    white = sum(len(board.pieces(p,chess.WHITE)) for p in (chess.KNIGHT,chess.BISHOP))
    assert black == white + 1
