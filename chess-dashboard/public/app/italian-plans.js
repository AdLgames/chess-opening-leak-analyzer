/* Original Italian decision scenarios. Generated legal positions; see docs/v4-italian-plans-review.md. */
window.ItalianPlans = {
  "id": "italian-plans-v1",
  "version": 1,
  "title": "When the book ends",
  "subtitle": "Italian Game \u00b7 White",
  "promise": "A safe king. A prepared centre. A plan that can change.",
  "scenes": [
    {
      "id": "king-first",
      "title": "Give your king a home",
      "tag": "They develop quietly",
      "prompt": "White to move. Get your king safe before opening the centre.",
      "idea": "The centre is still closed. You can tuck your king away before you decide how to challenge it.",
      "hint": "Your king and h1 rook can make one move together.",
      "answers": [
        {
          "uci": "e1g1",
          "san": "O-O",
          "why": "Your king leaves the centre and your rook comes towards the action. You have kept the central pawn tension for later.",
          "reply": "O-O",
          "after": {
            "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 b kq - 1 6",
            "turn": "black",
            "legal": []
          },
          "response": {
            "fen": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 w - - 2 7",
            "turn": "white",
            "legal": []
          }
        }
      ],
      "arrows": [
        {
          "from": "e1",
          "to": "g1",
          "kind": "idea"
        },
        {
          "from": "h1",
          "to": "f1",
          "kind": "idea"
        }
      ],
      "circles": [
        {
          "square": "e1",
          "kind": "idea"
        },
        {
          "square": "g1",
          "kind": "idea"
        }
      ],
      "wrong": {},
      "takeaway": "Get the king safe before you choose a central break.",
      "line": [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bc4",
        "Bc5",
        "c3",
        "Nf6",
        "d3",
        "d6"
      ],
      "position": {
        "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQK2R w KQkq - 0 6",
        "turn": "white",
        "legal": [
          {
            "uci": "c4a6",
            "san": "Ba6",
            "from": "c4",
            "to": "a6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/B1np1n2/2b1p3/4P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4b3",
            "san": "Bb3",
            "from": "c4",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/4P3/1BPP1N2/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4b5",
            "san": "Bb5",
            "from": "c4",
            "to": "b5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/1Bb1p3/4P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1d2",
            "san": "Bd2",
            "from": "c1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP1B1PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4d5",
            "san": "Bd5",
            "from": "c4",
            "to": "d5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2bBp3/4P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1e3",
            "san": "Be3",
            "from": "c1",
            "to": "e3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PPBN2/PP3PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4e6",
            "san": "Be6",
            "from": "c4",
            "to": "e6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2npBn2/2b1p3/4P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1f4",
            "san": "Bf4",
            "from": "c1",
            "to": "f4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1PB2/2PP1N2/PP3PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1g5",
            "san": "Bg5",
            "from": "c1",
            "to": "g5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p1B1/2B1P3/2PP1N2/PP3PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1h6",
            "san": "Bh6",
            "from": "c1",
            "to": "h6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n1B/2b1p3/2B1P3/2PP1N2/PP3PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4f7",
            "san": "Bxf7+",
            "from": "c4",
            "to": "f7",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2Bpp/2np1n2/2b1p3/4P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 0 6",
            "check": true,
            "mate": false,
            "capture": true
          },
          {
            "uci": "e1d2",
            "san": "Kd2",
            "from": "e1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP1K1PPP/RNBQ3R b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "e1e2",
            "san": "Ke2",
            "from": "e1",
            "to": "e2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP2KPPP/RNBQ3R b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "e1f1",
            "san": "Kf1",
            "from": "e1",
            "to": "f1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1K1R b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b1a3",
            "san": "Na3",
            "from": "b1",
            "to": "a3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/N1PP1N2/PP3PPP/R1BQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b1d2",
            "san": "Nbd2",
            "from": "b1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP1N1PPP/R1BQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3d4",
            "san": "Nd4",
            "from": "f3",
            "to": "d4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BNP3/2PP4/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3d2",
            "san": "Nfd2",
            "from": "f3",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP4/PP1N1PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3g1",
            "san": "Ng1",
            "from": "f3",
            "to": "g1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP4/PP3PPP/RNBQK1NR b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3g5",
            "san": "Ng5",
            "from": "f3",
            "to": "g5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p1N1/2B1P3/2PP4/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3h4",
            "san": "Nh4",
            "from": "f3",
            "to": "h4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P2N/2PP4/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3e5",
            "san": "Nxe5",
            "from": "f3",
            "to": "e5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1N3/2B1P3/2PP4/PP3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": true
          },
          {
            "uci": "e1g1",
            "san": "O-O",
            "from": "e1",
            "to": "g1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1a4",
            "san": "Qa4",
            "from": "d1",
            "to": "a4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/Q1B1P3/2PP1N2/PP3PPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1b3",
            "san": "Qb3",
            "from": "d1",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/1QPP1N2/PP3PPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1c2",
            "san": "Qc2",
            "from": "d1",
            "to": "c2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PPQ2PPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1d2",
            "san": "Qd2",
            "from": "d1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP1Q1PPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1e2",
            "san": "Qe2",
            "from": "d1",
            "to": "e2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP2QPPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h1f1",
            "san": "Rf1",
            "from": "h1",
            "to": "f1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQKR2 b Qkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h1g1",
            "san": "Rg1",
            "from": "h1",
            "to": "g1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQK1R1 b Qkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "a2a3",
            "san": "a3",
            "from": "a2",
            "to": "a3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/P1PP1N2/1P3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "a2a4",
            "san": "a4",
            "from": "a2",
            "to": "a4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/P1B1P3/2PP1N2/1P3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b2b3",
            "san": "b3",
            "from": "b2",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/1PPP1N2/P4PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b2b4",
            "san": "b4",
            "from": "b2",
            "to": "b4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/1PB1P3/2PP1N2/P4PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d3d4",
            "san": "d4",
            "from": "d3",
            "to": "d4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "g2g3",
            "san": "g3",
            "from": "g2",
            "to": "g3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1NP1/PP3P1P/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "g2g4",
            "san": "g4",
            "from": "g2",
            "to": "g4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P1P1/2PP1N2/PP3P1P/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h2h3",
            "san": "h3",
            "from": "h2",
            "to": "h3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N1P/PP3PP1/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h2h4",
            "san": "h4",
            "from": "h2",
            "to": "h4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P2P/2PP1N2/PP3PP1/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          }
        ],
        "check": false,
        "checkmate": false,
        "stalemate": false,
        "insufficient_material": false
      }
    },
    {
      "id": "prepare-break",
      "title": "Build the break",
      "tag": "They hold the centre",
      "prompt": "White to move. Support the centre before committing to d4.",
      "idea": "Your king is safe, but d4 still needs support. You can support that square with a pawn, or support e4 with a rook first.",
      "hint": "Try c3 to support d4, or bring the f1 rook behind e4.",
      "answers": [
        {
          "uci": "c2c3",
          "san": "c3",
          "why": "c3 puts another pawn behind d4. After a later exchange on d4, the c-pawn can help you rebuild the centre.",
          "reply": "O-O",
          "after": {
            "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 b kq - 0 6",
            "turn": "black",
            "legal": []
          },
          "response": {
            "fen": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 w - - 1 7",
            "turn": "white",
            "legal": []
          }
        },
        {
          "uci": "f1e1",
          "san": "Re1",
          "why": "Re1 supports your e4 pawn. This is a useful first step too; you can prepare c3 and choose the right moment for d4.",
          "reply": "O-O",
          "after": {
            "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQR1K1 b kq - 1 6",
            "turn": "black",
            "legal": []
          },
          "response": {
            "fen": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQR1K1 w - - 2 7",
            "turn": "white",
            "legal": []
          }
        }
      ],
      "arrows": [
        {
          "from": "c2",
          "to": "c3",
          "kind": "idea"
        },
        {
          "from": "c3",
          "to": "d4",
          "kind": "idea"
        },
        {
          "from": "f1",
          "to": "e1",
          "kind": "idea"
        }
      ],
      "circles": [
        {
          "square": "d4",
          "kind": "idea"
        },
        {
          "square": "e4",
          "kind": "idea"
        }
      ],
      "wrong": {
        "d4": {
          "reply": "exd4",
          "text": "After d4, Black can take with ...exd4. There is no pawn on c3 ready to recapture on d4. Prepare the centre first in this exercise.",
          "position": {
            "fen": "r1bqk2r/ppp2ppp/2np1n2/2b5/2BpP3/5N2/PPP2PPP/RNBQ1RK1 w kq - 0 7",
            "turn": "white",
            "legal": []
          }
        }
      },
      "takeaway": "Prepare d4 with c3; Re1 can support e4 first. The position decides the order.",
      "line": [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bc4",
        "Bc5",
        "O-O",
        "Nf6",
        "d3",
        "d6"
      ],
      "position": {
        "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQ1RK1 w kq - 0 6",
        "turn": "white",
        "legal": [
          {
            "uci": "c4a6",
            "san": "Ba6",
            "from": "c4",
            "to": "a6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/B1np1n2/2b1p3/4P3/3P1N2/PPP2PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4b3",
            "san": "Bb3",
            "from": "c4",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/4P3/1B1P1N2/PPP2PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4b5",
            "san": "Bb5",
            "from": "c4",
            "to": "b5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/1Bb1p3/4P3/3P1N2/PPP2PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1d2",
            "san": "Bd2",
            "from": "c1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPPB1PPP/RN1Q1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4d5",
            "san": "Bd5",
            "from": "c4",
            "to": "d5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2bBp3/4P3/3P1N2/PPP2PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1e3",
            "san": "Be3",
            "from": "c1",
            "to": "e3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3PBN2/PPP2PPP/RN1Q1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4e6",
            "san": "Be6",
            "from": "c4",
            "to": "e6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2npBn2/2b1p3/4P3/3P1N2/PPP2PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1f4",
            "san": "Bf4",
            "from": "c1",
            "to": "f4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1PB2/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1g5",
            "san": "Bg5",
            "from": "c1",
            "to": "g5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p1B1/2B1P3/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1h6",
            "san": "Bh6",
            "from": "c1",
            "to": "h6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n1B/2b1p3/2B1P3/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4f7",
            "san": "Bxf7+",
            "from": "c4",
            "to": "f7",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2Bpp/2np1n2/2b1p3/4P3/3P1N2/PPP2PPP/RNBQ1RK1 b kq - 0 6",
            "check": true,
            "mate": false,
            "capture": true
          },
          {
            "uci": "g1h1",
            "san": "Kh1",
            "from": "g1",
            "to": "h1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQ1R1K b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b1a3",
            "san": "Na3",
            "from": "b1",
            "to": "a3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/N2P1N2/PPP2PPP/R1BQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b1d2",
            "san": "Nbd2",
            "from": "b1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPPN1PPP/R1BQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b1c3",
            "san": "Nc3",
            "from": "b1",
            "to": "c3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3d4",
            "san": "Nd4",
            "from": "f3",
            "to": "d4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BNP3/3P4/PPP2PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3e1",
            "san": "Ne1",
            "from": "f3",
            "to": "e1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P4/PPP2PPP/RNBQNRK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3d2",
            "san": "Nfd2",
            "from": "f3",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P4/PPPN1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3g5",
            "san": "Ng5",
            "from": "f3",
            "to": "g5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p1N1/2B1P3/3P4/PPP2PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3h4",
            "san": "Nh4",
            "from": "f3",
            "to": "h4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P2N/3P4/PPP2PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3e5",
            "san": "Nxe5",
            "from": "f3",
            "to": "e5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1N3/2B1P3/3P4/PPP2PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": true
          },
          {
            "uci": "d1d2",
            "san": "Qd2",
            "from": "d1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPPQ1PPP/RNB2RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1e1",
            "san": "Qe1",
            "from": "d1",
            "to": "e1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNB1QRK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1e2",
            "san": "Qe2",
            "from": "d1",
            "to": "e2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP1QPPP/RNB2RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f1e1",
            "san": "Re1",
            "from": "f1",
            "to": "e1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQR1K1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "a2a3",
            "san": "a3",
            "from": "a2",
            "to": "a3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/P2P1N2/1PP2PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "a2a4",
            "san": "a4",
            "from": "a2",
            "to": "a4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/P1B1P3/3P1N2/1PP2PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b2b3",
            "san": "b3",
            "from": "b2",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/1P1P1N2/P1P2PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b2b4",
            "san": "b4",
            "from": "b2",
            "to": "b4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/1PB1P3/3P1N2/P1P2PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c2c3",
            "san": "c3",
            "from": "c2",
            "to": "c3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d3d4",
            "san": "d4",
            "from": "d3",
            "to": "d4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/5N2/PPP2PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "g2g3",
            "san": "g3",
            "from": "g2",
            "to": "g3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1NP1/PPP2P1P/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "g2g4",
            "san": "g4",
            "from": "g2",
            "to": "g4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P1P1/3P1N2/PPP2P1P/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h2h3",
            "san": "h3",
            "from": "h2",
            "to": "h3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/3P1N1P/PPP2PP1/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h2h4",
            "san": "h4",
            "from": "h2",
            "to": "h4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P2P/3P1N2/PPP2PP1/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          }
        ],
        "check": false,
        "checkmate": false,
        "stalemate": false,
        "insufficient_material": false
      }
    },
    {
      "id": "answer-strike",
      "title": "Their threat comes first",
      "tag": "They strike with \u2026d5",
      "prompt": "White to move. Black has challenged the centre. Remove the pawn that attacks your bishop.",
      "idea": "The pawn on d5 attacks your bishop on c4 as well as your pawn on e4. This is a concrete threat, so your quiet development plan must wait.",
      "hint": "Your e4 pawn can capture the pawn on d5.",
      "answers": [
        {
          "uci": "e4d5",
          "san": "exd5",
          "why": "exd5 removes the pawn attacking your bishop. After ...Nxd5, reassess the new centre rather than replaying a fixed sequence.",
          "reply": "Nxd5",
          "after": {
            "fen": "r1bqk2r/ppp2ppp/2n2n2/2bPp3/2B5/2PP1N2/PP3PPP/RNBQK2R b KQkq - 0 6",
            "turn": "black",
            "legal": []
          },
          "response": {
            "fen": "r1bqk2r/ppp2ppp/2n5/2bnp3/2B5/2PP1N2/PP3PPP/RNBQK2R w KQkq - 0 7",
            "turn": "white",
            "legal": []
          }
        }
      ],
      "arrows": [
        {
          "from": "d5",
          "to": "c4",
          "kind": "idea"
        },
        {
          "from": "d5",
          "to": "e4",
          "kind": "idea"
        },
        {
          "from": "e4",
          "to": "d5",
          "kind": "idea"
        }
      ],
      "circles": [
        {
          "square": "d5",
          "kind": "idea"
        },
        {
          "square": "c4",
          "kind": "idea"
        }
      ],
      "wrong": {
        "O-O": {
          "reply": "dxc4",
          "text": "Castling is legal, but ...dxc4 takes your bishop. Black\u2019s new threat needs attention before your usual development plan.",
          "position": {
            "fen": "r1bqk2r/ppp2ppp/2n2n2/2b1p3/2p1P3/2PP1N2/PP3PPP/RNBQ1RK1 w kq - 0 7",
            "turn": "white",
            "legal": []
          }
        }
      },
      "takeaway": "When a central pawn attacks your bishop, answer the threat before continuing your routine.",
      "line": [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bc4",
        "Bc5",
        "c3",
        "Nf6",
        "d3",
        "d5"
      ],
      "position": {
        "fen": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP3PPP/RNBQK2R w KQkq - 0 6",
        "turn": "white",
        "legal": [
          {
            "uci": "c4a6",
            "san": "Ba6",
            "from": "c4",
            "to": "a6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/B1n2n2/2bpp3/4P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4b3",
            "san": "Bb3",
            "from": "c4",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/4P3/1BPP1N2/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4b5",
            "san": "Bb5",
            "from": "c4",
            "to": "b5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/1Bbpp3/4P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1d2",
            "san": "Bd2",
            "from": "c1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP1B1PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1e3",
            "san": "Be3",
            "from": "c1",
            "to": "e3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PPBN2/PP3PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1f4",
            "san": "Bf4",
            "from": "c1",
            "to": "f4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1PB2/2PP1N2/PP3PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1g5",
            "san": "Bg5",
            "from": "c1",
            "to": "g5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp1B1/2B1P3/2PP1N2/PP3PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c1h6",
            "san": "Bh6",
            "from": "c1",
            "to": "h6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n1B/2bpp3/2B1P3/2PP1N2/PP3PPP/RN1QK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4d5",
            "san": "Bxd5",
            "from": "c4",
            "to": "d5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bBp3/4P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": true
          },
          {
            "uci": "e1d2",
            "san": "Kd2",
            "from": "e1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP1K1PPP/RNBQ3R b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "e1e2",
            "san": "Ke2",
            "from": "e1",
            "to": "e2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP2KPPP/RNBQ3R b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "e1f1",
            "san": "Kf1",
            "from": "e1",
            "to": "f1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP3PPP/RNBQ1K1R b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b1a3",
            "san": "Na3",
            "from": "b1",
            "to": "a3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/N1PP1N2/PP3PPP/R1BQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b1d2",
            "san": "Nbd2",
            "from": "b1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP1N1PPP/R1BQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3d4",
            "san": "Nd4",
            "from": "f3",
            "to": "d4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2BNP3/2PP4/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3d2",
            "san": "Nfd2",
            "from": "f3",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP4/PP1N1PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3g1",
            "san": "Ng1",
            "from": "f3",
            "to": "g1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP4/PP3PPP/RNBQK1NR b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3g5",
            "san": "Ng5",
            "from": "f3",
            "to": "g5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp1N1/2B1P3/2PP4/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3h4",
            "san": "Nh4",
            "from": "f3",
            "to": "h4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P2N/2PP4/PP3PPP/RNBQK2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3e5",
            "san": "Nxe5",
            "from": "f3",
            "to": "e5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpN3/2B1P3/2PP4/PP3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": true
          },
          {
            "uci": "e1g1",
            "san": "O-O",
            "from": "e1",
            "to": "g1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1a4",
            "san": "Qa4",
            "from": "d1",
            "to": "a4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/Q1B1P3/2PP1N2/PP3PPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1b3",
            "san": "Qb3",
            "from": "d1",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/1QPP1N2/PP3PPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1c2",
            "san": "Qc2",
            "from": "d1",
            "to": "c2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PPQ2PPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1d2",
            "san": "Qd2",
            "from": "d1",
            "to": "d2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP1Q1PPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1e2",
            "san": "Qe2",
            "from": "d1",
            "to": "e2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP2QPPP/RNB1K2R b KQkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h1f1",
            "san": "Rf1",
            "from": "h1",
            "to": "f1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP3PPP/RNBQKR2 b Qkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h1g1",
            "san": "Rg1",
            "from": "h1",
            "to": "g1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N2/PP3PPP/RNBQK1R1 b Qkq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "a2a3",
            "san": "a3",
            "from": "a2",
            "to": "a3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/P1PP1N2/1P3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "a2a4",
            "san": "a4",
            "from": "a2",
            "to": "a4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/P1B1P3/2PP1N2/1P3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b2b3",
            "san": "b3",
            "from": "b2",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/1PPP1N2/P4PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b2b4",
            "san": "b4",
            "from": "b2",
            "to": "b4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/1PB1P3/2PP1N2/P4PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d3d4",
            "san": "d4",
            "from": "d3",
            "to": "d4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2BPP3/2P2N2/PP3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "e4d5",
            "san": "exd5",
            "from": "e4",
            "to": "d5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bPp3/2B5/2PP1N2/PP3PPP/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": true
          },
          {
            "uci": "g2g3",
            "san": "g3",
            "from": "g2",
            "to": "g3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1NP1/PP3P1P/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "g2g4",
            "san": "g4",
            "from": "g2",
            "to": "g4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P1P1/2PP1N2/PP3P1P/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h2h3",
            "san": "h3",
            "from": "h2",
            "to": "h3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P3/2PP1N1P/PP3PP1/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h2h4",
            "san": "h4",
            "from": "h2",
            "to": "h4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2B1P2P/2PP1N2/PP3PP1/RNBQK2R b KQkq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          }
        ],
        "check": false,
        "checkmate": false,
        "stalemate": false,
        "insufficient_material": false
      }
    },
    {
      "id": "fresh-break",
      "title": "A new position. Your decision.",
      "tag": "Fresh-position challenge",
      "prompt": "White to move. Your king is safe and c3 is in place. Play the central pawn break those preparations support.",
      "idea": "",
      "hint": "The d-pawn can move two squares. The c3 pawn supports its destination.",
      "answers": [
        {
          "uci": "d2d4",
          "san": "d4",
          "why": "d4 uses the preparation: your king is safe and c3 supports the break. After ...exd4, cxd4 can rebuild your centre.",
          "reply": "exd4",
          "after": {
            "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6",
            "turn": "black",
            "legal": []
          },
          "response": {
            "fen": "r1bqk2r/ppp2ppp/2np1n2/2b5/2BpP3/2P2N2/PP3PPP/RNBQ1RK1 w kq - 0 7",
            "turn": "white",
            "legal": []
          }
        }
      ],
      "arrows": [
        {
          "from": "d2",
          "to": "d4",
          "kind": "idea"
        },
        {
          "from": "c3",
          "to": "d4",
          "kind": "idea"
        }
      ],
      "circles": [
        {
          "square": "d4",
          "kind": "idea"
        }
      ],
      "wrong": {},
      "takeaway": "The same idea can use a different move order: check king safety, pawn support and the opponent\u2019s threats.",
      "challenge": true,
      "line": [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bc4",
        "Bc5",
        "c3",
        "Nf6",
        "O-O",
        "d6"
      ],
      "position": {
        "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P2N2/PP1P1PPP/RNBQ1RK1 w kq - 0 6",
        "turn": "white",
        "legal": [
          {
            "uci": "c4a6",
            "san": "Ba6",
            "from": "c4",
            "to": "a6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/B1np1n2/2b1p3/4P3/2P2N2/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4b3",
            "san": "Bb3",
            "from": "c4",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/4P3/1BP2N2/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4b5",
            "san": "Bb5",
            "from": "c4",
            "to": "b5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/1Bb1p3/4P3/2P2N2/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4d3",
            "san": "Bd3",
            "from": "c4",
            "to": "d3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/4P3/2PB1N2/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4d5",
            "san": "Bd5",
            "from": "c4",
            "to": "d5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2bBp3/4P3/2P2N2/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4e2",
            "san": "Be2",
            "from": "c4",
            "to": "e2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/4P3/2P2N2/PP1PBPPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4e6",
            "san": "Be6",
            "from": "c4",
            "to": "e6",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2npBn2/2b1p3/4P3/2P2N2/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "c4f7",
            "san": "Bxf7+",
            "from": "c4",
            "to": "f7",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2Bpp/2np1n2/2b1p3/4P3/2P2N2/PP1P1PPP/RNBQ1RK1 b kq - 0 6",
            "check": true,
            "mate": false,
            "capture": true
          },
          {
            "uci": "g1h1",
            "san": "Kh1",
            "from": "g1",
            "to": "h1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P2N2/PP1P1PPP/RNBQ1R1K b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b1a3",
            "san": "Na3",
            "from": "b1",
            "to": "a3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/N1P2N2/PP1P1PPP/R1BQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3d4",
            "san": "Nd4",
            "from": "f3",
            "to": "d4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BNP3/2P5/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3e1",
            "san": "Ne1",
            "from": "f3",
            "to": "e1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P5/PP1P1PPP/RNBQNRK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3g5",
            "san": "Ng5",
            "from": "f3",
            "to": "g5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p1N1/2B1P3/2P5/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3h4",
            "san": "Nh4",
            "from": "f3",
            "to": "h4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P2N/2P5/PP1P1PPP/RNBQ1RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f3e5",
            "san": "Nxe5",
            "from": "f3",
            "to": "e5",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1N3/2B1P3/2P5/PP1P1PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": true
          },
          {
            "uci": "d1a4",
            "san": "Qa4",
            "from": "d1",
            "to": "a4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/Q1B1P3/2P2N2/PP1P1PPP/RNB2RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1b3",
            "san": "Qb3",
            "from": "d1",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/1QP2N2/PP1P1PPP/RNB2RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1c2",
            "san": "Qc2",
            "from": "d1",
            "to": "c2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P2N2/PPQP1PPP/RNB2RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1e1",
            "san": "Qe1",
            "from": "d1",
            "to": "e1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P2N2/PP1P1PPP/RNB1QRK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d1e2",
            "san": "Qe2",
            "from": "d1",
            "to": "e2",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P2N2/PP1PQPPP/RNB2RK1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "f1e1",
            "san": "Re1",
            "from": "f1",
            "to": "e1",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P2N2/PP1P1PPP/RNBQR1K1 b kq - 1 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "a2a3",
            "san": "a3",
            "from": "a2",
            "to": "a3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/P1P2N2/1P1P1PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "a2a4",
            "san": "a4",
            "from": "a2",
            "to": "a4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/P1B1P3/2P2N2/1P1P1PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b2b3",
            "san": "b3",
            "from": "b2",
            "to": "b3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/1PP2N2/P2P1PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "b2b4",
            "san": "b4",
            "from": "b2",
            "to": "b4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/1PB1P3/2P2N2/P2P1PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d2d3",
            "san": "d3",
            "from": "d2",
            "to": "d3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "d2d4",
            "san": "d4",
            "from": "d2",
            "to": "d4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "g2g3",
            "san": "g3",
            "from": "g2",
            "to": "g3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P2NP1/PP1P1P1P/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "g2g4",
            "san": "g4",
            "from": "g2",
            "to": "g4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P1P1/2P2N2/PP1P1P1P/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h2h3",
            "san": "h3",
            "from": "h2",
            "to": "h3",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2P2N1P/PP1P1PP1/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          },
          {
            "uci": "h2h4",
            "san": "h4",
            "from": "h2",
            "to": "h4",
            "promotion": null,
            "fen_after": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P2P/2P2N2/PP1P1PP1/RNBQ1RK1 b kq - 0 6",
            "check": false,
            "mate": false,
            "capture": false
          }
        ],
        "check": false,
        "checkmate": false,
        "stalemate": false,
        "insufficient_material": false
      }
    }
  ],
  "frames": [
    {
      "title": "Make room for a plan",
      "text": "You know the opening moves. Now look at what the position needs: king safety, support for the centre, and your opponent\u2019s latest threat.",
      "scene": "king-first",
      "arrows": [
        {
          "from": "e1",
          "to": "g1",
          "kind": "idea"
        },
        {
          "from": "h1",
          "to": "f1",
          "kind": "idea"
        }
      ],
      "circles": [
        {
          "square": "e1",
          "kind": "idea"
        },
        {
          "square": "g1",
          "kind": "idea"
        }
      ]
    },
    {
      "title": "Build it. Then check it.",
      "text": "c3 can support d4, and a rook on e1 can support e4. These are preparations, not a command to play d4 in every Italian position. A new threat can change your plan.",
      "scene": "prepare-break",
      "arrows": [
        {
          "from": "c2",
          "to": "c3",
          "kind": "idea"
        },
        {
          "from": "c3",
          "to": "d4",
          "kind": "idea"
        },
        {
          "from": "f1",
          "to": "e1",
          "kind": "idea"
        }
      ],
      "circles": [
        {
          "square": "d4",
          "kind": "idea"
        },
        {
          "square": "e4",
          "kind": "idea"
        }
      ]
    }
  ],
  "verification": {
    "engine": "Stockfish 17.1",
    "depth": 17,
    "scope": "Accepted teaching moves checked against engine alternatives; tactical replies and every packed transition checked with python-chess. Engine evaluation is not a claim of learning effectiveness."
  }
};
