"""Compile a bounded, CC0 Lichess pack into offline legal chess scenes.

The source FEN precedes the opponent's first move. Keep stable source IDs;
never infer a solution from a motif tag. Pack data is loaded per theme.
"""
import json
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'chess-dashboard/public/app'
THEMES = [
 ('forks','Forks','Two threats, one move','A fork attacks two targets at once. Look for checks and attacks on valuable pieces.','Spot the double attack','Forcing moves first'),
 ('pins','Pins','Find the piece that cannot leave','A pinned piece shields something more valuable. An absolute pin to the king prevents moves that expose check.','Find the pinned defender','Put pressure on a pin'),
 ('hanging','Loose pieces','Collect what is unprotected','Look for an undefended piece. Before capturing, check your king’s safety and the opponent’s reply.','Spot an undefended piece','Count attackers and defenders'),
 ('discovered','Discovered attacks','Move one piece, reveal another','Moving a piece can uncover an attack from a bishop, rook or queen behind it. Check both pieces’ threats.','Uncover a line','Two threats from one move'),
 ('backrank','Back-rank mates','Watch the king’s escape squares','A king behind its own pawns may have no escape from a rook or queen along the back rank. Check every escape square.','A trapped king','Find the entry square'),
 ('mates','Basic mates','Leave the king nowhere to go','Checkmate means the king is in check and there is no legal escape, capture or block. Examine every defence.','Find a mate in one','Cover the escape squares'),
]

def legal(board):
 return [{'uci':m.uci(),'from':chess.square_name(m.from_square),'to':chess.square_name(m.to_square),'san':board.san(m),'promotion':chess.piece_symbol(m.promotion) if m.promotion else None} for m in board.legal_moves]

def compile_row(row):
 b=chess.Board(row['FEN']); assert b.is_valid(),row['PuzzleId']
 moves=row['Moves'].split(); first=b.parse_uci(moves[0]); b.push(first)
 fen=b.fen(); scenes=[]
 for uci in moves[1:]:
  m=b.parse_uci(uci)
  accepted=[uci]
  if len(moves)==2:
   mates=[]
   for candidate in b.legal_moves:
    trial=b.copy();trial.push(candidate)
    if trial.is_checkmate():mates.append(candidate.uci())
   if mates:accepted=mates
  ends={}
  if len(moves)==2:
   for answer in accepted:
    trial=b.copy();trial.push_uci(answer);ends[answer]=trial.fen()
  scenes.append({'fen':b.fen(),'legal':legal(b),'answer':uci,'accepted':accepted,'ends':ends,'san':b.san(m)})
  b.push(m)
 scenes.append({'fen':b.fen(),'legal':[]})
 return {'id':row['PuzzleId'],'version':1,'theme':row['theme'],'fen':fen,'side':'white' if chess.Board(fen).turn else 'black','rating':int(row['Rating']),'source':f'https://lichess.org/training/{row["PuzzleId"]}','scenes':scenes}

def build():
 rows=json.loads((ROOT/'chess_opening_analyzer/content/puzzles-v1.json').read_text())
 packs={t[0]:[] for t in THEMES}
 for row in rows:packs[row['theme']].append(compile_row(row))
 lessons=[]
 for theme,label,tagline,idea,*titles in THEMES:
  for i,title in enumerate(titles):
   puzzle=packs[theme][i]; scene=puzzle['scenes'][0]; m=chess.Move.from_uci(scene['answer']);board=chess.Board(scene['fen']);piece=board.piece_at(m.from_square)
   origin=chess.square_name(m.from_square);target=chess.square_name(m.to_square)
   board.push(m)
   enemies=[sq for sq in board.attacks(m.to_square) if board.piece_at(sq) and board.piece_at(sq).color!=piece.color]
   targets=sorted(enemies,key=lambda sq:board.piece_at(sq).piece_type,reverse=True)[:2]
   arrow={'from':origin,'to':target,'kind':'best'}
   if piece.piece_type==chess.KNIGHT:arrow['via']=origin[0]+target[1]
   lessons.append({'id':theme+'-'+str(i+1),'theme':theme,'title':title,'idea':idea,'puzzle':puzzle['id'],'question':f'Find the {chess.piece_name(piece.piece_type)} on {origin}. Select its square to begin.','square':origin,'frames':[
    {'fen':scene['fen'],'text':f'{scene["san"]} moves the {chess.piece_name(piece.piece_type)} from {origin} to {target}. This is a legal move in the position.','arrows':[arrow],'circles':[{'square':origin,'kind':'book'},{'square':target,'kind':'best'}]},
    {'fen':board.fen(),'text':('The moving piece now attacks enemy pieces on '+', '.join(chess.square_name(sq) for sq in targets)+'. ' if targets else '')+('This position is checkmate: there is no legal defence.' if board.is_checkmate() else 'Follow the puzzle continuation to see the opponent’s reply. Geometric attacks and legal captures are different, especially with pinned pieces.'),'arrows':[{'from':target,'to':chess.square_name(sq),'kind':'book'} for sq in targets],'circles':[{'square':chess.square_name(sq),'kind':'book'} for sq in targets]}
   ]})
 manifest={'version':1,'themes':[{'id':t[0],'title':t[1],'tagline':t[2],'idea':t[3],'count':len(packs[t[0]])} for t in THEMES],'puzzles':[{k:p[k] for k in ('id','theme','rating','side','fen')} for pack in packs.values() for p in pack],'lessons':lessons}
 for theme,pack in packs.items():(PUBLIC/f'puzzle-packs/{theme}.json').write_text(json.dumps(pack,separators=(',',':'))+'\n')
 (PUBLIC/'puzzle-catalog.js').write_text('/* Lichess puzzle positions: CC0. Teaching notes: original. */\nwindow.PuzzleCatalog = '+json.dumps(manifest,separators=(',',':'))+';\n')
 return manifest,packs

if __name__=='__main__':
 manifest,packs=build();print(f'{len(manifest["puzzles"])} puzzles, {len(manifest["lessons"])} micro-lessons; legal moves compiled in six lazy-loaded packs')
