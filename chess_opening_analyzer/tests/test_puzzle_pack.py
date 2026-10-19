"""Source interpretation, compiled move legality and authored teaching diagrams."""
import importlib.util
import json
from pathlib import Path
import chess

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('puzzle_builder',ROOT/'chess_opening_analyzer/tools/build_puzzles.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
PUBLIC=ROOT/'chess-dashboard/public/app'

def test_curated_pack_source_and_every_compiled_transition():
 rows=json.loads((ROOT/'chess_opening_analyzer/content/puzzles-v1.json').read_text())
 assert len(rows)==len({r['PuzzleId'] for r in rows})==150
 assert {r['theme'] for r in rows}=={t[0] for t in builder.THEMES}
 assert {chess.Board(r['FEN']).turn for r in rows}=={True,False}
 for theme,*_ in builder.THEMES:
  pack=json.loads((PUBLIC/f'puzzle-packs/{theme}.json').read_text())
  source=[r for r in rows if r['theme']==theme]
  assert len(pack)==25
  assert pack==[builder.compile_row(r) for r in source]
  for row,puzzle in zip(source,pack):
   board=chess.Board(row['FEN']);board.push_uci(row['Moves'].split()[0])
   assert puzzle['fen']==board.fen()  # FIRST move is the opponent's setup.
   assert (puzzle['side']=='white')==board.turn
   for i,scene in enumerate(puzzle['scenes'][:-1]):
    assert scene['fen']==board.fen()
    assert {m['uci'] for m in scene['legal']}=={m.uci() for m in board.legal_moves}
    assert scene['answer'] in scene['accepted']
    for move in scene['legal']:
     assert board.san(chess.Move.from_uci(move['uci']))==move['san']
    if len(puzzle['scenes'])==2:
     mates=[]
     for m in board.legal_moves:
      trial=board.copy();trial.push(m)
      if trial.is_checkmate():mates.append(m.uci())
     if mates:assert set(scene['accepted'])==set(mates)
     for uci,fen in scene['ends'].items():
      trial=board.copy();trial.push_uci(uci);assert trial.fen()==fen
    board.push_uci(scene['answer'])
   assert puzzle['scenes'][-1]['fen']==board.fen()

def test_twelve_lessons_reference_real_positions_and_factual_frames():
 data=json.loads((PUBLIC/'puzzle-catalog.js').read_text().split('window.PuzzleCatalog = ')[1].rstrip(';\n'))
 assert len(data['lessons'])==12
 assert len({l['id'] for l in data['lessons']})==12
 for lesson in data['lessons']:
  pack=json.loads((PUBLIC/f'puzzle-packs/{lesson["theme"]}.json').read_text())
  puzzle=next(p for p in pack if p['id']==lesson['puzzle'])
  board=chess.Board(puzzle['fen']);move=chess.Move.from_uci(puzzle['scenes'][0]['answer'])
  assert lesson['square']==chess.square_name(move.from_square)
  assert lesson['frames'][0]['fen']==board.fen()
  assert lesson['frames'][0]['arrows'][0]['from']==lesson['square']
  board.push(move);assert lesson['frames'][1]['fen']==board.fen()
  for arrow in lesson['frames'][1]['arrows']:
   assert chess.parse_square(arrow['to']) in board.attacks(chess.parse_square(arrow['from']))
