"""The instant public lessons teach real course moves and expose all legal moves."""
import json
from pathlib import Path
import chess

APP=Path(__file__).resolve().parents[2]/'chess-dashboard/public'


def test_offline_previews_match_courses_and_replay_legally():
    previews=json.loads((APP/'lesson-previews.js').read_text().split('window.LessonPreviews = ',1)[1].rstrip(';\n'))
    courses=json.loads((APP/'app/opening-courses.js').read_text().split('window.OpeningCourses = ',1)[1].rstrip(';\n'))
    assert {p['id'] for p in previews} == {c['opening'] for c in courses}
    for preview in previews:
        course=next(c for c in courses if c['opening']==preview['id'])
        board=chess.Board(preview['position']['fen'])
        assert ('white' if board.turn else 'black') == preview['side'] == course['side']
        legal=preview['position']['legal']
        assert {m['uci'] for m in legal} == {m.uci() for m in board.legal_moves}
        for move in legal:
            probe=board.copy();probe.push_uci(move['uci'])
            assert probe.fen() == move['fen_after']
        answer=chess.Move.from_uci(preview['answer'])
        assert board.san(answer) == preview['move']
        board.push(answer)
        assert board.fen() == preview['after']['fen']
        assert any(c['fen']==preview['position']['fen'] and c['uci']==preview['answer'] and c['idea']==preview['idea'] for c in course['cards'])
