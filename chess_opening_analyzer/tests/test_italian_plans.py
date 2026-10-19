"""The V4 decisions teach legal, sound choices and concrete board relationships."""
import json
from pathlib import Path
import chess
import chess.engine
import pytest
from chessopening.engine import find_engine

SOURCE = Path(__file__).resolve().parents[2] / 'chess-dashboard/public/app/italian-plans.js'
DATA = json.loads(SOURCE.read_text().split('window.ItalianPlans = ')[1].rstrip(';\n'))
SCENES = {s['id']: s for s in DATA['scenes']}


def test_all_input_moves_and_branches_are_complete_and_legal():
    assert len(SCENES) == 4
    for scene in SCENES.values():
        board = chess.Board()
        for san in scene['line']:
            board.push_san(san)
        assert board.fen() == scene['position']['fen'] and board.turn == chess.WHITE
        assert {m.uci() for m in board.legal_moves} == {m['uci'] for m in scene['position']['legal']}
        for move in scene['position']['legal']:
            after = board.copy()
            legal = after.parse_uci(move['uci'])
            assert after.san(legal) == move['san']
            after.push(legal)
            assert after.fen() == move['fen_after']
        for answer in scene['answers']:
            after = board.copy()
            after.push_san(answer['san'])
            assert after.fen() == answer['after']['fen']
            after.push_san(answer['reply'])
            assert after.fen() == answer['response']['fen']
        for san, wrong in scene['wrong'].items():
            after = board.copy()
            after.push_san(san)
            after.push_san(wrong['reply'])
            assert after.fen() == wrong['position']['fen']


def test_explanations_have_the_claimed_support_and_threats():
    castle = chess.Board(SCENES['king-first']['answers'][0]['after']['fen'])
    assert castle.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)
    assert castle.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)
    prepare = SCENES['prepare-break']
    pawn = chess.Board(next(a for a in prepare['answers'] if a['san'] == 'c3')['after']['fen'])
    assert chess.D4 in pawn.attacks(chess.C3)
    rook = chess.Board(next(a for a in prepare['answers'] if a['san'] == 'Re1')['after']['fen'])
    assert chess.E4 in rook.attacks(chess.E1)
    strike = chess.Board(SCENES['answer-strike']['position']['fen'])
    assert {chess.C4, chess.E4}.issubset(strike.attacks(chess.D5))
    lost = chess.Board(SCENES['answer-strike']['wrong']['O-O']['position']['fen'])
    assert lost.piece_at(chess.C4) == chess.Piece(chess.PAWN, chess.BLACK)
    assert len(lost.pieces(chess.BISHOP, chess.WHITE)) == 1


def test_held_out_challenge_is_a_distinct_position_requiring_adaptation():
    challenge = SCENES['fresh-break']
    assert challenge['challenge']
    assert not challenge['idea']
    assert challenge['position']['fen'].split(' ')[:4] not in [s['position']['fen'].split(' ')[:4] for s in DATA['scenes'][:-1]]
    assert all(f['scene'] != challenge['id'] for f in DATA['frames'])
    after = chess.Board(challenge['answers'][0]['response']['fen'])
    after.push_san('cxd4')
    assert after.piece_at(chess.D4) == chess.Piece(chess.PAWN, chess.WHITE)


@pytest.mark.parametrize('scene', DATA['scenes'], ids=lambda s:s['id'])
def test_accepted_teaching_moves_are_sound_engine_alternatives(scene):
    board = chess.Board(scene['position']['fen'])
    with chess.engine.SimpleEngine.popen_uci(find_engine()) as engine:
        best = engine.analyse(board, chess.engine.Limit(depth=16))['score'].white().score(mate_score=10000)
        for answer in scene['answers']:
            score = engine.analyse(board, chess.engine.Limit(depth=16), root_moves=[chess.Move.from_uci(answer['uci'])])['score'].white().score(mate_score=10000)
            assert best - score <= 70, (scene['id'], answer['san'], best, score)
