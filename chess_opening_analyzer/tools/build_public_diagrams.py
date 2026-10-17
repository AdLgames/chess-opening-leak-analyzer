#!/usr/bin/env python3
"""Compile small static SVG boards so public explanations work without JavaScript."""
import json
from pathlib import Path
import chess
import chess.svg
from public_content import GUIDES

ROOT = Path(__file__).resolve().parents[2] / 'chess-dashboard/public'
COLORS = {'square light':'#a1bc89', 'square dark':'#518367', 'margin':'#173d32', 'coord light':'#173d32', 'coord dark':'#f5f2e8'}


def attributed(svg):
    notice = '<metadata>Board rendered with python-chess (GPL-3.0-or-later). Piece artwork by Colin M. L. Burnett (Cburnett), distributed through python-chess under GPL-3.0-or-later. Source: https://github.com/niklasf/python-chess/blob/master/chess/svg.py . Licence: https://chessleaklab.co.uk/assets/positions/COPYING.txt . This project adds board colours and teaching annotations.</metadata>'
    end = svg.index('>') + 1
    return svg[:end] + notice + svg[end:]


def diagrams():
    previews = json.loads((ROOT/'lesson-previews.js').read_text().split('window.LessonPreviews = ',1)[1].rstrip(';\n'))
    for preview in previews:
        yield 'preview-'+preview['id'], attributed(chess.svg.board(chess.Board(preview['position']['fen']), orientation=chess.WHITE if preview['side']=='white' else chess.BLACK, colors=COLORS, size=640))
    for guide in GUIDES:
        board = chess.Board()
        for san in guide['diagram']['moves']:
            board.push_san(san)
        arrows = [chess.svg.Arrow(chess.parse_square(a), chess.parse_square(b), color='#efcb7bdd') for a,b in guide['diagram']['arrows']]
        arrows += [chess.svg.Arrow(chess.parse_square(sq), chess.parse_square(sq), color='#efcb7bdd') for sq in guide['diagram']['circles']]
        yield guide['slug'], attributed(chess.svg.board(board, arrows=arrows, colors=COLORS, size=640))


if __name__ == '__main__':
    folder = ROOT/'assets/positions'
    folder.mkdir(exist_ok=True)
    for name, svg in diagrams():
        (folder/(name+'.svg')).write_text(svg)
    print('Six static board diagrams built from legal positions.')
