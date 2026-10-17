"""Teaching overlays match real legal moves and geometric attacks on each board."""
import importlib.util
import json
from pathlib import Path
import chess

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'chess-dashboard/public/app'
COURSES=json.loads((APP/'opening-courses.js').read_text().split('window.OpeningCourses = ',1)[1].rstrip(';\n'))
SCENES=json.loads((APP/'visual-lessons.js').read_text().split('window.VisualLessons = ',1)[1].rstrip(';\n'))


def test_all_59_lessons_show_the_actual_move_and_attacked_squares():
    assert len(SCENES)==59
    for course in COURSES:
        for card in course['cards']:
            frames=SCENES[f'{course["id"]}/{card["id"]}']
            assert len(frames)==3
            assert frames[0]['fen']==card['fen']
            assert frames[1]['fen']==frames[2]['fen']==card['afterFen']
            move=chess.Move.from_uci(card['uci'])
            assert frames[0]['arrows'][0]['from']==chess.square_name(move.from_square)
            assert frames[0]['arrows'][0]['to']==chess.square_name(move.to_square)
            for frame in frames[1:]:
                board=chess.Board(frame['fen']); source=chess.parse_square(frame['source'])
                attacked=set(board.attacks(source))
                assert all(chess.parse_square(c['square']) in attacked for c in frame['circles'])
                for arrow in frame['arrows']:
                    assert chess.parse_square(arrow['from'])==source
                    assert chess.parse_square(arrow['to']) in attacked
                    if 'via' in arrow:
                        assert board.piece_type_at(source)==chess.KNIGHT
                        assert chess.square_file(chess.parse_square(arrow['via']))==chess.square_file(source)
            assert card['why'] in frames[-1]['text']


def test_diagram_compiler_is_reproducible_and_castling_moves_both_pieces():
    spec=importlib.util.spec_from_file_location('visual_compiler',ROOT/'chess_opening_analyzer/tools/build_visual_lessons.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.build()==SCENES
    for course in COURSES:
        for card in course['cards']:
            board=chess.Board(card['fen']);move=board.parse_san(card['move'])
            if board.is_castling(move):
                arrows=SCENES[f'{course["id"]}/{card["id"]}'][0]['arrows']
                assert len(arrows)==2
                assert board.piece_type_at(chess.parse_square(arrows[1]['from']))==chess.ROOK
                board.push(move)
                assert board.piece_type_at(chess.parse_square(arrows[1]['to']))==chess.ROOK
