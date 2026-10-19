"""Build original, bounded Italian plan scenarios with complete legal input positions.

Regenerate with python chess_opening_analyzer/tools/build_italian_plans.py.
Chess content, branching replies and alternatives are covered by release tests.
"""
import json,sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / 'chess_opening_analyzer'))
import chess
from chessopening.board import position_payload
scenes=[
 dict(id='king-first',title='Give your king a home',tag='They develop quietly',line='e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6',prompt='White to move. Get your king safe before opening the centre.',idea='The centre is still closed. You can tuck your king away before you decide how to challenge it.',hint='Your king and h1 rook can make one move together.',answers=[('O-O','O-O','Your king leaves the centre and your rook comes towards the action. You have kept the central pawn tension for later.')],arrows=[('e1','g1'),('h1','f1')],circles=['e1','g1'],wrong={},takeaway='Get the king safe before you choose a central break.'),
 dict(id='prepare-break',title='Build the break',tag='They hold the centre',line='e4 e5 Nf3 Nc6 Bc4 Bc5 O-O Nf6 d3 d6',prompt='White to move. Support the centre before committing to d4.',idea='Your king is safe, but d4 still needs support. You can support that square with a pawn, or support e4 with a rook first.',hint='Try c3 to support d4, or bring the f1 rook behind e4.',answers=[('c3','O-O','c3 puts another pawn behind d4. After a later exchange on d4, the c-pawn can help you rebuild the centre.'),('Re1','O-O','Re1 supports your e4 pawn. This is a useful first step too; you can prepare c3 and choose the right moment for d4.')],arrows=[('c2','c3'),('c3','d4'),('f1','e1')],circles=['d4','e4'],wrong={'d4':{'reply':'exd4','text':'After d4, Black can take with ...exd4. There is no pawn on c3 ready to recapture on d4. Prepare the centre first in this exercise.'}},takeaway='Prepare d4 with c3; Re1 can support e4 first. The position decides the order.'),
 dict(id='answer-strike',title='Their threat comes first',tag='They strike with …d5',line='e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d5',prompt='White to move. Black has challenged the centre. Remove the pawn that attacks your bishop.',idea='The pawn on d5 attacks your bishop on c4 as well as your pawn on e4. This is a concrete threat, so your quiet development plan must wait.',hint='Your e4 pawn can capture the pawn on d5.',answers=[('exd5','Nxd5','exd5 removes the pawn attacking your bishop. After ...Nxd5, reassess the new centre rather than replaying a fixed sequence.')],arrows=[('d5','c4'),('d5','e4'),('e4','d5')],circles=['d5','c4'],wrong={'O-O':{'reply':'dxc4','text':'Castling is legal, but ...dxc4 takes your bishop. Black’s new threat needs attention before your usual development plan.'}},takeaway='When a central pawn attacks your bishop, answer the threat before continuing your routine.'),
 dict(id='fresh-break',title='A new position. Your decision.',tag='Fresh-position challenge',line='e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 O-O d6',prompt='White to move. Your king is safe and c3 is in place. Play the central pawn break those preparations support.',idea='',hint='The d-pawn can move two squares. The c3 pawn supports its destination.',answers=[('d4','exd4','d4 uses the preparation: your king is safe and c3 supports the break. After ...exd4, cxd4 can rebuild your centre.')],arrows=[('d2','d4'),('c3','d4')],circles=['d4'],wrong={},takeaway='The same idea can use a different move order: check king safety, pawn support and the opponent’s threats.',challenge=True),
]
def pos(b, interactive=False):
 p=position_payload(fen=b.fen())
 if not interactive:return {'fen':p['fen'],'turn':p['turn'],'legal':[]}
 return {k:p[k] for k in ['fen','turn','legal','check','checkmate','stalemate','insufficient_material']}
out=[]
for s in scenes:
 b=chess.Board();line=s.pop('line').split()
 for san in line:b.push_san(san)
 s['line']=line;s['position']=pos(b,True);s['answers']=[dict(uci=b.parse_san(san).uci(),san=san,why=why,reply=reply) for san,reply,why in s['answers']]
 for a in s['answers']:
  after=b.copy();after.push_uci(a['uci']);a['after']=pos(after);after.push_san(a['reply']);a['response']=pos(after)
 for san,item in s['wrong'].items():
  after=b.copy();after.push_san(san);after.push_san(item['reply']);item['position']=pos(after)
 s['arrows']=[dict(**{'from':a,'to':z},kind='idea') for a,z in s['arrows']]
 s['circles']=[dict(square=sq,kind='idea') for sq in s['circles']]
 out.append(s)
content=dict(id='italian-plans-v1',version=1,title='When the book ends',subtitle='Italian Game · White',promise='A safe king. A prepared centre. A plan that can change.',scenes=out,frames=[dict(title='Make room for a plan',text='You know the opening moves. Now look at what the position needs: king safety, support for the centre, and your opponent’s latest threat.',scene='king-first',arrows=out[0]['arrows'],circles=out[0]['circles']),dict(title='Build it. Then check it.',text='c3 can support d4, and a rook on e1 can support e4. These are preparations, not a command to play d4 in every Italian position. A new threat can change your plan.',scene='prepare-break',arrows=out[1]['arrows'],circles=out[1]['circles'])],verification=dict(engine='Stockfish 17.1',depth=17,scope='Accepted teaching moves checked against engine alternatives; tactical replies and every packed transition checked with python-chess. Engine evaluation is not a claim of learning effectiveness.'))
(ROOT / 'chess-dashboard/public/app/italian-plans.js').write_text('/* Original Italian decision scenarios. Generated legal positions; see docs/v4-italian-plans-review.md. */\nwindow.ItalianPlans = '+json.dumps(content,indent=2)+';\n')
