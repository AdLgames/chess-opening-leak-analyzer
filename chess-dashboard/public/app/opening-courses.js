/* Original teaching notes; historical game scores have separate source credits. */
window.OpeningCourses = [
  {
    "id": "italian-v1",
    "title": "Italian for White",
    "version": 1,
    "description": "Develop with purpose. Meet the Two Knights. Find the f7 tactic. Make a middlegame plan.",
    "cards": [
      {
        "id": "centre",
        "line": [],
        "move": "e4",
        "title": "Claim the centre",
        "prompt": "Give your king’s bishop room to develop.",
        "idea": "A central pawn claims space and opens a diagonal for your bishop.",
        "hint": "Move the king’s pawn two squares.",
        "why": "1.e4 controls d5 and f5 and frees the bishop on f1.",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "uci": "e2e4",
        "afterFen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
      },
      {
        "id": "knight",
        "line": [
          "e4",
          "e5"
        ],
        "move": "Nf3",
        "title": "Develop with a threat",
        "prompt": "Develop a knight and attack e5.",
        "idea": "Bring a piece towards the centre while asking Black to defend a pawn.",
        "hint": "The knight on g1 can attack e5.",
        "why": "Nf3 develops towards the centre, attacks e5 and clears g1 for castling.",
        "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        "uci": "g1f3",
        "afterFen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
      },
      {
        "id": "bishop",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6"
        ],
        "move": "Bc4",
        "title": "The Italian bishop",
        "prompt": "Aim your king’s bishop at f7.",
        "idea": "The Italian bishop looks towards f7, which initially has only the black king as a defender.",
        "hint": "Use the diagonal f1–e2–d3–c4.",
        "why": "Bc4 develops actively and keeps the way clear for kingside castling.",
        "mistakes": {
          "Nxe5": {
            "text": "The pawn on e5 is defended by the knight on c6. After Nxe5, …Nxe5 takes your knight. Develop the bishop before taking that pawn.",
            "line": [
              "Nxe5",
              "Nxe5"
            ]
          }
        },
        "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "uci": "f1c4",
        "afterFen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"
      },
      {
        "id": "c3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Bc5"
        ],
        "move": "c3",
        "title": "Prepare a central break",
        "prompt": "Prepare to support a future d4 advance.",
        "idea": "In this repertoire we prepare the centre before choosing when to open it.",
        "hint": "The c-pawn can support d4.",
        "why": "c3 supports d4. We will play d3 first, castle and develop before deciding when to break.",
        "fen": "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "uci": "c2c3",
        "afterFen": "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/2P2N2/PP1P1PPP/RNBQK2R b KQkq - 0 4"
      },
      {
        "id": "d3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Bc5",
          "c3",
          "Nf6"
        ],
        "move": "d3",
        "title": "Support e4",
        "prompt": "Support e4 and open the diagonal for your other bishop.",
        "idea": "Black’s knight attacks e4. A quiet pawn move supports the centre and frees the bishop on c1.",
        "hint": "Move the d-pawn one square.",
        "why": "d3 supports e4 and opens c1–d2–e3. An immediate d4 leads to a different, sharper line.",
        "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2P2N2/PP1P1PPP/RNBQK2R w KQkq - 1 5",
        "uci": "d2d3",
        "afterFen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 0 5"
      },
      {
        "id": "castle",
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
        "move": "O-O",
        "title": "Secure your king",
        "prompt": "Put your king to safety before starting an attack.",
        "idea": "Your king and rook are ready to castle. Complete king safety before moving more pawns.",
        "hint": "Move the king from e1 to g1.",
        "why": "Castling moves the king away from the centre and brings the rook towards the e-file.",
        "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQK2R w KQkq - 0 6",
        "uci": "e1g1",
        "afterFen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 b kq - 1 6"
      },
      {
        "id": "re1",
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
          "d6",
          "O-O",
          "O-O"
        ],
        "move": "Re1",
        "title": "Support the centre with a rook",
        "prompt": "Bring your rook behind the e4 pawn.",
        "idea": "Supporting e4 gives your other pieces more freedom. It also clears f1 for a later knight route.",
        "hint": "Use the rook on f1.",
        "why": "Re1 reinforces e4 and makes room for the route Nb1–d2–f1–g3.",
        "fen": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 w - - 2 7",
        "uci": "f1e1",
        "afterFen": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQR1K1 b - - 3 7"
      },
      {
        "id": "two-d3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nf6"
        ],
        "move": "d3",
        "title": "Meet the Two Knights",
        "prompt": "Choose our quiet response to the attack on e4.",
        "idea": "Against 3…Nf6 we support e4 immediately. The sharp 4.Ng5 is another opening choice, outside this main line.",
        "hint": "The d-pawn can defend e4.",
        "why": "d3 protects e4 and keeps the position in the quieter Italian family.",
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "uci": "d2d3",
        "afterFen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R b KQkq - 0 4"
      },
      {
        "id": "two-castle",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nf6",
          "d3",
          "Bc5"
        ],
        "move": "O-O",
        "title": "Keep development moving",
        "prompt": "Complete king safety against the Two Knights.",
        "idea": "Black has developed both knights. We can castle before building the centre further.",
        "hint": "The king belongs on g1.",
        "why": "O-O secures the king. We can follow with c3 and Re1 if Black also castles.",
        "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 1 5",
        "uci": "e1g1",
        "afterFen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQ1RK1 b kq - 2 5"
      },
      {
        "id": "two-c3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nf6",
          "d3",
          "Bc5",
          "O-O",
          "O-O"
        ],
        "move": "c3",
        "title": "Reach a familiar structure",
        "prompt": "Prepare d4 while keeping your centre intact.",
        "idea": "Move orders can differ while the same plans remain useful.",
        "hint": "Support d4 with the c-pawn.",
        "why": "c3 prepares d4. After …d6 and Re1 we reach the same position as our first chapter.",
        "fen": "r1bq1rk1/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQ1RK1 w - - 3 6",
        "uci": "c2c3",
        "afterFen": "r1bq1rk1/pppp1ppp/2n2n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 b - - 0 6"
      },
      {
        "id": "f7",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nf6",
          "Ng5",
          "d5",
          "exd5",
          "Nxd5"
        ],
        "move": "Nxf7",
        "title": "Spot the fork on f7",
        "prompt": "Find the knight capture that forks queen and rook.",
        "idea": "A tactical detour: this position arises after 4.Ng5 and 5…Nxd5. Our main repertoire still uses 4.d3; other black replies lead elsewhere.",
        "hint": "The knight on g5 can capture the pawn on f7.",
        "why": "Nxf7 attacks the queen on d8 and rook on h8. Black can accept the sacrifice with …Kxf7, which brings the king into the open.",
        "fen": "r1bqkb1r/ppp2ppp/2n5/3np1N1/2B5/8/PPPP1PPP/RNBQK2R w KQkq - 0 6",
        "uci": "g5f7",
        "afterFen": "r1bqkb1r/ppp2Npp/2n5/3np3/2B5/8/PPPP1PPP/RNBQK2R b KQkq - 0 6"
      },
      {
        "id": "qf3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nf6",
          "Ng5",
          "d5",
          "exd5",
          "Nxd5",
          "Nxf7",
          "Kxf7"
        ],
        "move": "Qf3+",
        "title": "Attack with tempo",
        "prompt": "Give check while attacking the knight on d5.",
        "idea": "After sacrificing material, bring another piece into the attack with a threat.",
        "hint": "The queen has a clear diagonal from d1 to f3.",
        "why": "Qf3+ checks along the f-file and attacks d5 along the diagonal f3–e4–d5.",
        "fen": "r1bq1b1r/ppp2kpp/2n5/3np3/2B5/8/PPPP1PPP/RNBQK2R w KQ - 0 7",
        "uci": "d1f3",
        "afterFen": "r1bq1b1r/ppp2kpp/2n5/3np3/2B5/5Q2/PPPP1PPP/RNB1K2R b KQ - 1 7"
      },
      {
        "id": "nc3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nf6",
          "Ng5",
          "d5",
          "exd5",
          "Nxd5",
          "Nxf7",
          "Kxf7",
          "Qf3+",
          "Ke6"
        ],
        "move": "Nc3",
        "title": "Bring another attacker",
        "prompt": "Develop your remaining knight with pressure on d5.",
        "idea": "Black has defended the knight with the king. Add another attacker instead of rushing a queen capture.",
        "hint": "The knight on b1 can reach c3.",
        "why": "Nc3 develops and attacks d5. White has attacking compensation for the sacrificed knight; this is a sharp position, not a forced win.",
        "fen": "r1bq1b1r/ppp3pp/2n1k3/3np3/2B5/5Q2/PPPP1PPP/RNB1K2R w KQ - 2 8",
        "uci": "b1c3",
        "afterFen": "r1bq1b1r/ppp3pp/2n1k3/3np3/2B5/2N2Q2/PPPP1PPP/R1B1K2R b KQ - 3 8"
      },
      {
        "id": "bb3",
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
          "d6",
          "O-O",
          "O-O",
          "Re1",
          "a6"
        ],
        "move": "Bb3",
        "title": "Keep the bishop’s diagonal",
        "prompt": "Retreat the Italian bishop while keeping pressure on f7.",
        "idea": "Black can gain space with …b5. Retreating now preserves the bishop on the same diagonal.",
        "hint": "Move the bishop from c4 one square towards your queenside.",
        "why": "Bb3 keeps the diagonal b3–c4–d5–e6–f7. Watch for …b5 and choose the central break carefully.",
        "fen": "r1bq1rk1/1pp2ppp/p1np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQR1K1 w - - 0 8",
        "uci": "c4b3",
        "afterFen": "r1bq1rk1/1pp2ppp/p1np1n2/2b1p3/4P3/1BPP1N2/PP3PPP/RNBQR1K1 b - - 1 8"
      },
      {
        "id": "nbd2",
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
          "d6",
          "O-O",
          "O-O",
          "Re1",
          "a6",
          "Bb3",
          "Ba7"
        ],
        "move": "Nbd2",
        "title": "Start the knight route",
        "prompt": "Develop the b1 knight towards d2, then f1.",
        "idea": "The c3 pawn occupies the knight’s usual square. The d2 route prepares a useful regrouping.",
        "hint": "Choose the knight on b1, not f3.",
        "why": "Nbd2 develops without blocking the c-pawn. From d2 the knight can head to f1 and g3.",
        "fen": "r1bq1rk1/bpp2ppp/p1np1n2/4p3/4P3/1BPP1N2/PP3PPP/RNBQR1K1 w - - 2 9",
        "uci": "b1d2",
        "afterFen": "r1bq1rk1/bpp2ppp/p1np1n2/4p3/4P3/1BPP1N2/PP1N1PPP/R1BQR1K1 b - - 3 9"
      },
      {
        "id": "nf1",
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
          "d6",
          "O-O",
          "O-O",
          "Re1",
          "a6",
          "Bb3",
          "Ba7",
          "Nbd2",
          "h6"
        ],
        "move": "Nf1",
        "title": "Regroup towards the kingside",
        "prompt": "Continue the d2 knight’s route towards g3.",
        "idea": "You do not need to attack immediately. Improve a piece while keeping the centre stable.",
        "hint": "The rook has already cleared f1.",
        "why": "Nf1 prepares Ng3, where the knight can support the centre and look towards f5 and h5.",
        "fen": "r1bq1rk1/bpp2pp1/p1np1n1p/4p3/4P3/1BPP1N2/PP1N1PPP/R1BQR1K1 w - - 0 10",
        "uci": "d2f1",
        "afterFen": "r1bq1rk1/bpp2pp1/p1np1n1p/4p3/4P3/1BPP1N2/PP3PPP/R1BQRNK1 b - - 1 10"
      },
      {
        "id": "ng3",
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
          "d6",
          "O-O",
          "O-O",
          "Re1",
          "a6",
          "Bb3",
          "Ba7",
          "Nbd2",
          "h6",
          "Nf1",
          "Re8"
        ],
        "move": "Ng3",
        "title": "Finish the regrouping",
        "prompt": "Complete the route and bring the knight to g3.",
        "idea": "A good opening leaves you with a plan. Here that plan is a piece improvement followed by a well-timed central break.",
        "hint": "Move the knight from f1 to g3.",
        "why": "Ng3 puts the knight near f5 and h5. Keep watching Black’s counterplay and prepare d4 when your pieces support it.",
        "fen": "r1bqr1k1/bpp2pp1/p1np1n1p/4p3/4P3/1BPP1N2/PP3PPP/R1BQRNK1 w - - 2 11",
        "uci": "f1g3",
        "afterFen": "r1bqr1k1/bpp2pp1/p1np1n1p/4p3/4P3/1BPP1NN1/PP3PPP/R1BQR1K1 b - - 3 11"
      },
      {
        "id": "early-knight",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nd4"
        ],
        "move": "Nxd4",
        "title": "Trade the advanced knight",
        "prompt": "Remove the knight that has jumped to d4.",
        "idea": "Black has moved the same knight twice. Trade it before chasing the e5 pawn.",
        "hint": "The knight on f3 can capture d4.",
        "why": "Nxd4 removes the advanced knight. After …exd4, castle and build your centre.",
        "fen": "r1bqkbnr/pppp1ppp/8/4p3/2BnP3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "uci": "f3d4",
        "afterFen": "r1bqkbnr/pppp1ppp/8/4p3/2BNP3/8/PPPP1PPP/RNBQK2R b KQkq - 0 4"
      },
      {
        "id": "early-castle",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nd4",
          "Nxd4",
          "exd4"
        ],
        "move": "O-O",
        "title": "Safety before pawn hunting",
        "prompt": "Secure your king after the knight trade.",
        "idea": "Black has a pawn on d4, but your king can reach safety before you challenge it.",
        "hint": "Move the king from e1 to g1.",
        "why": "O-O secures the king and activates the rook. The e5 pawn has already moved to d4; focus on development.",
        "fen": "r1bqkbnr/pppp1ppp/8/8/2BpP3/8/PPPP1PPP/RNBQK2R w KQkq - 0 5",
        "uci": "e1g1",
        "afterFen": "r1bqkbnr/pppp1ppp/8/8/2BpP3/8/PPPP1PPP/RNBQ1RK1 b kq - 1 5"
      },
      {
        "id": "early-d3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Nd4",
          "Nxd4",
          "exd4",
          "O-O",
          "Nf6"
        ],
        "move": "d3",
        "title": "Challenge the wedge",
        "prompt": "Support e4 and challenge the pawn on d4.",
        "idea": "A pawn in your half of the board is not a reason to panic. Build a centre that can undermine it.",
        "hint": "Move the d-pawn one square.",
        "why": "d3 supports e4 and attacks d4. You can develop the c1 bishop before deciding how to resolve the centre.",
        "fen": "r1bqkb1r/pppp1ppp/5n2/8/2BpP3/8/PPPP1PPP/RNBQ1RK1 w kq - 2 6",
        "uci": "d2d3",
        "afterFen": "r1bqkb1r/pppp1ppp/5n2/8/2BpP3/3P4/PPP2PPP/RNBQ1RK1 b kq - 0 6"
      },
      {
        "id": "hungarian-d4",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Be7"
        ],
        "move": "d4",
        "title": "Meet the Hungarian Defence",
        "prompt": "Take more central space while Black develops quietly.",
        "idea": "With the bishop on e7, Black puts less direct pressure on your centre.",
        "hint": "Advance the d-pawn two squares.",
        "why": "d4 contests the centre and opens the c1 bishop. If …exd4, recapture with the knight.",
        "fen": "r1bqk1nr/ppppbppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "uci": "d2d4",
        "afterFen": "r1bqk1nr/ppppbppp/2n5/4p3/2BPP3/5N2/PPP2PPP/RNBQK2R b KQkq - 0 4"
      },
      {
        "id": "hungarian-knight",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Be7",
          "d4",
          "exd4"
        ],
        "move": "Nxd4",
        "title": "Recapture with development",
        "prompt": "Recapture on d4 without bringing the queen out.",
        "idea": "Use an active piece to recover the pawn.",
        "hint": "The f3 knight can capture d4.",
        "why": "Nxd4 recovers the pawn and places a knight in the centre. Continue developing before starting an attack.",
        "fen": "r1bqk1nr/ppppbppp/2n5/8/2BpP3/5N2/PPP2PPP/RNBQK2R w KQkq - 0 5",
        "uci": "f3d4",
        "afterFen": "r1bqk1nr/ppppbppp/2n5/8/2BNP3/8/PPP2PPP/RNBQK2R b KQkq - 0 5"
      },
      {
        "id": "hungarian-nc3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Be7",
          "d4",
          "exd4",
          "Nxd4",
          "Nf6"
        ],
        "move": "Nc3",
        "title": "Defend e4 naturally",
        "prompt": "Develop a knight while defending e4.",
        "idea": "Black attacks your centre with …Nf6. Defend it with development.",
        "hint": "The knight on b1 has a useful central square.",
        "why": "Nc3 supports e4 and develops the last knight. Castling is a useful next step.",
        "fen": "r1bqk2r/ppppbppp/2n2n2/8/2BNP3/8/PPP2PPP/RNBQK2R w KQkq - 1 6",
        "uci": "b1c3",
        "afterFen": "r1bqk2r/ppppbppp/2n2n2/8/2BNP3/2N5/PPP2PPP/R1BQK2R b KQkq - 2 6"
      },
      {
        "id": "slow-d4",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Bc5",
          "c3",
          "d6"
        ],
        "move": "d4",
        "title": "Use the prepared break",
        "prompt": "Carry out the central break that c3 prepared.",
        "idea": "Black has supported e5 with …d6. Open the centre while your pieces are active.",
        "hint": "Push the d-pawn two squares.",
        "why": "d4 attacks the bishop on c5 and the e5 pawn. Against …exd4, cxd4 gives you a broad centre.",
        "fen": "r1bqk1nr/ppp2ppp/2np4/2b1p3/2B1P3/2P2N2/PP1P1PPP/RNBQK2R w KQkq - 0 5",
        "uci": "d2d4",
        "afterFen": "r1bqk1nr/ppp2ppp/2np4/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQK2R b KQkq - 0 5"
      },
      {
        "id": "slow-cxd4",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Bc5",
          "c3",
          "d6",
          "d4",
          "exd4"
        ],
        "move": "cxd4",
        "title": "Build a central pawn pair",
        "prompt": "Recapture on d4 with the supporting pawn.",
        "idea": "This is the point of c3: your c-pawn can replace the pawn exchanged on d4.",
        "hint": "Capture from c3 to d4.",
        "why": "cxd4 gives White pawns on d4 and e4. Develop the b1 knight and get the king safe.",
        "fen": "r1bqk1nr/ppp2ppp/2np4/2b5/2BpP3/2P2N2/PP3PPP/RNBQK2R w KQkq - 0 6",
        "uci": "c3d4",
        "afterFen": "r1bqk1nr/ppp2ppp/2np4/2b5/2BPP3/5N2/PP3PPP/RNBQK2R b KQkq - 0 6"
      },
      {
        "id": "slow-nc3",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bc4",
          "Bc5",
          "c3",
          "d6",
          "d4",
          "exd4",
          "cxd4",
          "Bb6"
        ],
        "move": "Nc3",
        "title": "Support the new centre",
        "prompt": "Develop the b1 knight behind your central pawns.",
        "idea": "The pawn has left c3, so your knight can use its natural square.",
        "hint": "Move the b1 knight to c3.",
        "why": "Nc3 reinforces e4 and controls d5. Your next priority is completing king safety.",
        "fen": "r1bqk1nr/ppp2ppp/1bnp4/8/2BPP3/5N2/PP3PPP/RNBQK2R w KQkq - 1 7",
        "uci": "b1c3",
        "afterFen": "r1bqk1nr/ppp2ppp/1bnp4/8/2BPP3/2N2N2/PP3PPP/R1BQK2R b KQkq - 2 7"
      }
    ],
    "chapters": [
      {
        "id": "essentials",
        "title": "Build your Italian",
        "subtitle": "Centre, development and king safety",
        "cards": [
          "centre",
          "knight",
          "bishop",
          "c3",
          "d3",
          "castle",
          "re1"
        ],
        "takeaway": "Support e4, castle, then bring the rook to e1. Prepare d4 when your pieces are ready.",
        "goal": "Keep your king safe and prepare a central break."
      },
      {
        "id": "two-knights",
        "title": "Meet the Two Knights",
        "subtitle": "A quiet answer to 3…Nf6",
        "cards": [
          "two-d3",
          "two-castle",
          "two-c3"
        ],
        "takeaway": "Answer …Nf6 with d3. Castle and prepare c3; familiar structures can arise through a different move order.",
        "goal": "Develop your queenside and support the centre."
      },
      {
        "id": "f7-tactic",
        "title": "Recognise the f7 tactic",
        "subtitle": "A sharp detour after 5…Nxd5",
        "cards": [
          "f7",
          "qf3",
          "nc3"
        ],
        "takeaway": "Against this specific …Nxd5 line, the fork on f7 and Qf3+ bring Black’s king into the open. This is a tactical detour, not our main repertoire.",
        "goal": "Bring pieces into the attack while watching checks against your own king."
      },
      {
        "id": "middlegame",
        "title": "Know what comes next",
        "subtitle": "The knight route to g3",
        "cards": [
          "bb3",
          "nbd2",
          "nf1",
          "ng3"
        ],
        "takeaway": "Keep the Italian bishop active. Route the b1 knight through d2 and f1 to g3, then look for a well-supported d4 break.",
        "goal": "Improve your pieces and choose the right moment for d4."
      },
      {
        "id": "early-deviation",
        "title": "Handle an early …Nd4",
        "subtitle": "Trade the knight and keep developing",
        "cards": [
          "early-knight",
          "early-castle",
          "early-d3"
        ],
        "takeaway": "Trade the advanced knight, castle and undermine the d4 pawn with d3.",
        "goal": "Develop calmly and challenge the pawn on d4.",
        "kind": "lesson"
      },
      {
        "id": "hungarian",
        "title": "Meet the Hungarian Defence",
        "subtitle": "Take space against 3…Be7",
        "cards": [
          "hungarian-d4",
          "hungarian-knight",
          "hungarian-nc3"
        ],
        "takeaway": "Use d4 to claim the centre, recapture with the knight and develop Nc3.",
        "goal": "Support the centre and complete king safety.",
        "kind": "lesson"
      },
      {
        "id": "central-break",
        "title": "Know when to play d4",
        "subtitle": "Against an early …d6",
        "cards": [
          "slow-d4",
          "slow-cxd4",
          "slow-nc3"
        ],
        "takeaway": "c3 prepares d4. After the central exchange, support your pawn pair with natural development.",
        "goal": "Protect the centre while completing development.",
        "kind": "lesson"
      }
    ],
    "opening": "italian",
    "side": "white",
    "eco": "C50",
    "scope": "Quiet Italian, selected common deviations and f7 tactics",
    "anchors": [
      [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bc4"
      ],
      [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bc4",
        "Bc5",
        "c3"
      ],
      [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bc4",
        "Nf6",
        "d3"
      ],
      [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bc4",
        "Bc5",
        "c3",
        "Nf6",
        "d3"
      ]
    ]
  },
  {
    "id": "caro-v1",
    "opening": "caro",
    "title": "Caro-Kann for Black",
    "side": "black",
    "eco": "B12",
    "version": 1,
    "scope": "1.e4 c6 2.d4 d5; Classical, Advance and Exchange starters",
    "cards": [
      {
        "id": "c6",
        "line": [
          "e4"
        ],
        "move": "c6",
        "title": "Prepare the central challenge",
        "prompt": "Prepare to challenge e4 with …d5.",
        "idea": "The Caro-Kann supports a central pawn advance with the c-pawn.",
        "hint": "Move the c-pawn one square.",
        "why": "…c6 supports …d5 while leaving the c8 bishop a route out before …e6.",
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "uci": "c7c6",
        "afterFen": "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
      },
      {
        "id": "d5",
        "line": [
          "e4",
          "c6",
          "d4"
        ],
        "move": "d5",
        "title": "Challenge White’s centre",
        "prompt": "Challenge the pawn on e4.",
        "idea": "White has occupied the centre with two pawns. Contest it now.",
        "hint": "Advance the d-pawn two squares.",
        "why": "…d5 attacks e4 and claims central space. White can advance, exchange or defend the e4 pawn.",
        "fen": "rnbqkbnr/pp1ppppp/2p5/8/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 2",
        "uci": "d7d5",
        "afterFen": "rnbqkbnr/pp2pppp/2p5/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3"
      },
      {
        "id": "classical-take",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "Nc3"
        ],
        "move": "dxe4",
        "title": "Resolve the central tension",
        "prompt": "Exchange the d-pawn for White’s e-pawn.",
        "idea": "Against Nc3 we choose the Classical structure.",
        "hint": "Capture the pawn on e4.",
        "why": "…dxe4 exchanges a central pawn. After Nxe4, develop the light-squared bishop before playing …e6.",
        "fen": "rnbqkbnr/pp2pppp/2p5/3p4/3PP3/2N5/PPP2PPP/R1BQKBNR b KQkq - 1 3",
        "uci": "d5e4",
        "afterFen": "rnbqkbnr/pp2pppp/2p5/8/3Pp3/2N5/PPP2PPP/R1BQKBNR w KQkq - 0 4"
      },
      {
        "id": "classical-bishop",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "Nc3",
          "dxe4",
          "Nxe4"
        ],
        "move": "Bf5",
        "title": "Get the bishop outside",
        "prompt": "Develop the c8 bishop with a threat to the knight.",
        "idea": "The pawn exchange has opened a diagonal for your bishop. Use it before closing the centre.",
        "hint": "The bishop can reach f5.",
        "why": "…Bf5 develops outside the future e6 pawn chain and attacks the knight on e4.",
        "fen": "rnbqkbnr/pp2pppp/2p5/8/3PN3/8/PPP2PPP/R1BQKBNR b KQkq - 0 4",
        "uci": "c8f5",
        "afterFen": "rn1qkbnr/pp2pppp/2p5/5b2/3PN3/8/PPP2PPP/R1BQKBNR w KQkq - 1 5"
      },
      {
        "id": "advance-bishop",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "e5"
        ],
        "move": "Bf5",
        "title": "Meet the Advance",
        "prompt": "Develop your light-squared bishop before …e6.",
        "idea": "White gains space with e5. Your bishop should leave c8 before you build the pawn chain.",
        "hint": "Use the diagonal to f5.",
        "why": "…Bf5 develops the bishop outside the chain. Prepare …e6 and a later …c5 break.",
        "fen": "rnbqkbnr/pp2pppp/2p5/3pP3/3P4/8/PPP2PPP/RNBQKBNR b KQkq - 0 3",
        "uci": "c8f5",
        "afterFen": "rn1qkbnr/pp2pppp/2p5/3pPb2/3P4/8/PPP2PPP/RNBQKBNR w KQkq - 1 4"
      },
      {
        "id": "advance-e6",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "e5",
          "Bf5",
          "Nf3"
        ],
        "move": "e6",
        "title": "Build a sound centre",
        "prompt": "Support d5 and open the dark-squared bishop.",
        "idea": "Your light-squared bishop is already active, so you can now play …e6.",
        "hint": "Move the e-pawn one square.",
        "why": "…e6 supports d5 and frees the f8 bishop. White has more space; challenge it with …c5 when ready.",
        "fen": "rn1qkbnr/pp2pppp/2p5/3pPb2/3P4/5N2/PPP2PPP/RNBQKB1R b KQkq - 2 4",
        "uci": "e7e6",
        "afterFen": "rn1qkbnr/pp3ppp/2p1p3/3pPb2/3P4/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 5"
      },
      {
        "id": "advance-c5",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "e5",
          "Bf5",
          "Nf3",
          "e6",
          "Be2"
        ],
        "move": "c5",
        "title": "Challenge the pawn chain",
        "prompt": "Attack the base of White’s pawn chain.",
        "idea": "A cramped position improves when you challenge the centre rather than wait.",
        "hint": "The c-pawn can advance to c5.",
        "why": "…c5 attacks d4, the base of the d4–e5 chain. Keep developing your knights and watch the d5 pawn.",
        "fen": "rn1qkbnr/pp3ppp/2p1p3/3pPb2/3P4/5N2/PPP1BPPP/RNBQK2R b KQkq - 1 5",
        "uci": "c6c5",
        "afterFen": "rn1qkbnr/pp3ppp/4p3/2ppPb2/3P4/5N2/PPP1BPPP/RNBQK2R w KQkq - 0 6"
      },
      {
        "id": "exchange-take",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "exd5"
        ],
        "move": "cxd5",
        "title": "Meet the Exchange",
        "prompt": "Recapture on d5 with the c-pawn.",
        "idea": "Recover the pawn and keep a central foothold.",
        "hint": "Capture from c6 to d5.",
        "why": "…cxd5 gives Black a pawn on d5 and opens the c-file for later rook activity.",
        "fen": "rnbqkbnr/pp2pppp/2p5/3P4/3P4/8/PPP2PPP/RNBQKBNR b KQkq - 0 3",
        "uci": "c6d5",
        "afterFen": "rnbqkbnr/pp2pppp/8/3p4/3P4/8/PPP2PPP/RNBQKBNR w KQkq - 0 4"
      },
      {
        "id": "exchange-knight",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "exd5",
          "cxd5",
          "Bd3"
        ],
        "move": "Nc6",
        "title": "Develop against the centre",
        "prompt": "Develop the b8 knight towards d4 and e5.",
        "idea": "The open c-file gives your knight a natural route to c6.",
        "hint": "Move the b8 knight to c6.",
        "why": "…Nc6 develops with pressure on d4 and control of e5. You still need king safety.",
        "fen": "rnbqkbnr/pp2pppp/8/3p4/3P4/3B4/PPP2PPP/RNBQK1NR b KQkq - 1 4",
        "uci": "b8c6",
        "afterFen": "r1bqkbnr/pp2pppp/2n5/3p4/3P4/3B4/PPP2PPP/RNBQK1NR w KQkq - 2 5"
      },
      {
        "id": "exchange-nf6",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "exd5",
          "cxd5",
          "Bd3",
          "Nc6",
          "c3"
        ],
        "move": "Nf6",
        "title": "Finish knight development",
        "prompt": "Develop the kingside knight towards the centre.",
        "idea": "White has supported d4. Develop rather than move the same piece again.",
        "hint": "The g8 knight belongs on f6.",
        "why": "…Nf6 controls e4 and d5. The c8 bishop can develop before …e6.",
        "fen": "r1bqkbnr/pp2pppp/2n5/3p4/3P4/2PB4/PP3PPP/RNBQK1NR b KQkq - 0 5",
        "uci": "g8f6",
        "afterFen": "r1bqkb1r/pp2pppp/2n2n2/3p4/3P4/2PB4/PP3PPP/RNBQK1NR w KQkq - 1 6"
      },
      {
        "id": "exchange-pin",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "exd5",
          "cxd5",
          "Bd3",
          "Nc6",
          "c3",
          "Nf6",
          "Nf3"
        ],
        "move": "Bg4",
        "title": "Develop with a pin",
        "prompt": "Pin the knight on f3 to White’s queen.",
        "idea": "An active bishop can make White’s central play less comfortable.",
        "hint": "Use the c8–g4 diagonal.",
        "why": "…Bg4 develops and pins Nf3 along the diagonal to the queen on d1. Complete development and castle next.",
        "fen": "r1bqkb1r/pp2pppp/2n2n2/3p4/3P4/2PB1N2/PP3PPP/RNBQK2R b KQkq - 2 6",
        "uci": "c8g4",
        "afterFen": "r2qkb1r/pp2pppp/2n2n2/3p4/3P2b1/2PB1N2/PP3PPP/RNBQK2R w KQkq - 3 7"
      },
      {
        "id": "bishop-retreat",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "Nc3",
          "dxe4",
          "Nxe4",
          "Bf5",
          "Ng3"
        ],
        "move": "Bg6",
        "title": "Keep the active bishop",
        "prompt": "Move the attacked bishop while keeping it outside the chain.",
        "idea": "The knight on g3 attacks f5. Preserve your bishop.",
        "hint": "Retreat to g6.",
        "why": "…Bg6 keeps the bishop active. Be ready for h4, which gains space and threatens h5.",
        "fen": "rn1qkbnr/pp2pppp/2p5/5b2/3P4/6N1/PPP2PPP/R1BQKBNR b KQkq - 2 5",
        "uci": "f5g6",
        "afterFen": "rn1qkbnr/pp2pppp/2p3b1/8/3P4/6N1/PPP2PPP/R1BQKBNR w KQkq - 3 6"
      },
      {
        "id": "bishop-window",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "Nc3",
          "dxe4",
          "Nxe4",
          "Bf5",
          "Ng3",
          "Bg6",
          "h4"
        ],
        "move": "h6",
        "title": "Make a retreat square",
        "prompt": "Give your bishop a retreat square on h7.",
        "idea": "White wants h5 to attack the bishop. Make room before it arrives.",
        "hint": "Move the h-pawn one square.",
        "why": "…h6 clears h7. If h5 follows, your bishop can retreat there instead of being trapped.",
        "fen": "rn1qkbnr/pp2pppp/2p3b1/8/3P3P/6N1/PPP2PP1/R1BQKBNR b KQkq - 0 6",
        "uci": "h7h6",
        "afterFen": "rn1qkbnr/pp2ppp1/2p3bp/8/3P3P/6N1/PPP2PP1/R1BQKBNR w KQkq - 0 7"
      },
      {
        "id": "bishop-h7",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "Nc3",
          "dxe4",
          "Nxe4",
          "Bf5",
          "Ng3",
          "Bg6",
          "h4",
          "h6",
          "h5"
        ],
        "move": "Bh7",
        "title": "Use the escape square",
        "prompt": "Retreat the attacked bishop to the square you prepared.",
        "idea": "White has gained space but your bishop has a safe route.",
        "hint": "Use h7.",
        "why": "…Bh7 saves the bishop. Continue with …Nd7, …Ngf6 and …e6 as the position allows.",
        "fen": "rn1qkbnr/pp2ppp1/2p3bp/7P/3P4/6N1/PPP2PP1/R1BQKBNR b KQkq - 0 7",
        "uci": "g6h7",
        "afterFen": "rn1qkbnr/pp2pppb/2p4p/7P/3P4/6N1/PPP2PP1/R1BQKBNR w KQkq - 1 8"
      },
      {
        "id": "loose-bishop",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "Bc4"
        ],
        "move": "dxc4",
        "title": "Spot the loose bishop",
        "prompt": "White’s bishop is attacked. Can you win material?",
        "idea": "Check what your central pawn attacks before following a memorised setup.",
        "hint": "The pawn on d5 attacks c4.",
        "why": "…dxc4 captures a bishop for a pawn. White may try to gain tempi against your king, so continue with careful development.",
        "fen": "rnbqkbnr/pp2pppp/2p5/3p4/2BPP3/8/PPP2PPP/RNBQK1NR b KQkq - 1 3",
        "uci": "d5c4",
        "afterFen": "rnbqkbnr/pp2pppp/2p5/8/2pPP3/8/PPP2PPP/RNBQK1NR w KQkq - 0 4"
      }
    ],
    "chapters": [
      {
        "id": "essentials",
        "title": "Build your Caro-Kann",
        "subtitle": "Challenge the centre and free the bishop",
        "cards": [
          "c6",
          "d5",
          "classical-take",
          "classical-bishop"
        ],
        "takeaway": "Challenge e4 with …d5 and develop the light-squared bishop before …e6.",
        "goal": "Develop your pieces and get your king safe.",
        "kind": "lesson"
      },
      {
        "id": "advance",
        "title": "Meet the Advance",
        "subtitle": "Bishop first, then …e6 and …c5",
        "cards": [
          "advance-bishop",
          "advance-e6",
          "advance-c5"
        ],
        "takeaway": "Get the bishop outside, support d5 and attack White’s pawn chain with …c5.",
        "goal": "Develop behind your central counterplay.",
        "kind": "lesson"
      },
      {
        "id": "exchange",
        "title": "Handle the Exchange",
        "subtitle": "Natural development and an active bishop",
        "cards": [
          "exchange-take",
          "exchange-knight",
          "exchange-nf6",
          "exchange-pin"
        ],
        "takeaway": "Recapture with the c-pawn, develop both knights and use the bishop actively.",
        "goal": "Finish development without losing control of d5.",
        "kind": "lesson"
      },
      {
        "id": "bishop-safety",
        "title": "Keep your bishop safe",
        "subtitle": "Understand the point of …h6",
        "cards": [
          "bishop-retreat",
          "bishop-window",
          "bishop-h7"
        ],
        "takeaway": "When Ng3 and h4 chase the bishop, …h6 creates the escape square h7.",
        "goal": "Develop the remaining pieces and watch the kingside.",
        "kind": "lesson"
      },
      {
        "id": "tactics",
        "title": "Look before you build",
        "subtitle": "Punish an undefended bishop",
        "cards": [
          "loose-bishop"
        ],
        "takeaway": "Check immediate threats and captures before playing your usual setup.",
        "goal": "Keep your extra material while developing safely.",
        "kind": "tactic"
      }
    ],
    "anchors": [
      [
        "e4",
        "c6",
        "d4",
        "d5"
      ],
      [
        "e4",
        "c6",
        "d4",
        "d5",
        "Nc3",
        "dxe4"
      ],
      [
        "e4",
        "c6",
        "d4",
        "d5",
        "e5",
        "Bf5"
      ],
      [
        "e4",
        "c6",
        "d4",
        "d5",
        "exd5",
        "cxd5"
      ]
    ]
  },
  {
    "id": "qgd-v1",
    "opening": "queens",
    "title": "Queen’s Gambit Declined for Black",
    "side": "black",
    "eco": "D30",
    "version": 1,
    "scope": "1.d4 d5 2.c4 e6; Orthodox and Exchange starters",
    "cards": [
      {
        "id": "d5",
        "line": [
          "d4"
        ],
        "move": "d5",
        "title": "Meet d4 in the centre",
        "prompt": "Claim central space against d4.",
        "idea": "A central pawn gives your pieces a stable starting point.",
        "hint": "Advance the d-pawn two squares.",
        "why": "…d5 controls e4 and meets White’s central space directly.",
        "fen": "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1",
        "uci": "d7d5",
        "afterFen": "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2"
      },
      {
        "id": "e6",
        "line": [
          "d4",
          "d5",
          "c4"
        ],
        "move": "e6",
        "title": "Support d5",
        "prompt": "Support your central pawn rather than taking c4.",
        "idea": "The Queen’s Gambit asks you to choose a central structure. We keep the pawn on d5.",
        "hint": "Move the e-pawn one square.",
        "why": "…e6 supports d5 and opens the f8 bishop. Your c8 bishop needs a later route into play.",
        "fen": "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq - 0 2",
        "uci": "e7e6",
        "afterFen": "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3"
      },
      {
        "id": "nf6",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3"
        ],
        "move": "Nf6",
        "title": "Develop a defender",
        "prompt": "Develop your king’s knight towards the centre.",
        "idea": "Use development to support your pawn structure.",
        "hint": "The g8 knight can reach f6.",
        "why": "…Nf6 develops and reinforces d5 while controlling e4.",
        "fen": "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR b KQkq - 1 3",
        "uci": "g8f6",
        "afterFen": "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 2 4"
      },
      {
        "id": "be7",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5"
        ],
        "move": "Be7",
        "title": "Break the pin safely",
        "prompt": "Prepare to castle and reduce the pressure on f6.",
        "idea": "White’s bishop pins your knight. A quiet developing move prepares king safety.",
        "hint": "Move the f8 bishop to e7.",
        "why": "…Be7 interposes the bishop on the diagonal to your queen and clears f8 for castling.",
        "fen": "rnbqkb1r/ppp2ppp/4pn2/3p2B1/2PP4/2N5/PP2PPPP/R2QKBNR b KQkq - 3 4",
        "uci": "f8e7",
        "afterFen": "rnbqk2r/ppp1bppp/4pn2/3p2B1/2PP4/2N5/PP2PPPP/R2QKBNR w KQkq - 4 5"
      },
      {
        "id": "castle",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Be7",
          "e3"
        ],
        "move": "O-O",
        "title": "Secure the king",
        "prompt": "Castle before opening the centre.",
        "idea": "Your kingside pieces have developed. Get the king to safety.",
        "hint": "Move the king from e8 to g8.",
        "why": "…O-O secures the king. Develop the b8 knight and prepare central counterplay.",
        "fen": "rnbqk2r/ppp1bppp/4pn2/3p2B1/2PP4/2N1P3/PP3PPP/R2QKBNR b KQkq - 0 5",
        "uci": "e8g8",
        "afterFen": "rnbq1rk1/ppp1bppp/4pn2/3p2B1/2PP4/2N1P3/PP3PPP/R2QKBNR w KQ - 1 6"
      },
      {
        "id": "exchange-take",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "cxd5"
        ],
        "move": "exd5",
        "title": "Meet the Exchange",
        "prompt": "Recapture on d5 with the e-pawn.",
        "idea": "The Exchange Variation changes the pawn structure, not your need to develop.",
        "hint": "Capture from e6 to d5.",
        "why": "…exd5 gives the Carlsbad structure. The c8 bishop now has an open diagonal.",
        "fen": "rnbqkb1r/ppp2ppp/4pn2/3P4/3P4/2N5/PP2PPPP/R1BQKBNR b KQkq - 0 4",
        "uci": "e6d5",
        "afterFen": "rnbqkb1r/ppp2ppp/5n2/3p4/3P4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 5"
      },
      {
        "id": "exchange-castle",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "cxd5",
          "exd5",
          "Bg5",
          "Be7",
          "e3"
        ],
        "move": "O-O",
        "title": "Keep the king safe",
        "prompt": "Complete king safety in the Exchange structure.",
        "idea": "Your bishop has developed and f8 is clear.",
        "hint": "Castle kingside.",
        "why": "…O-O secures the king before either side starts a pawn plan.",
        "fen": "rnbqk2r/ppp1bppp/5n2/3p2B1/3P4/2N1P3/PP3PPP/R2QKBNR b KQkq - 0 6",
        "uci": "e8g8",
        "afterFen": "rnbq1rk1/ppp1bppp/5n2/3p2B1/3P4/2N1P3/PP3PPP/R2QKBNR w KQ - 1 7"
      },
      {
        "id": "exchange-c6",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "cxd5",
          "exd5",
          "Bg5",
          "Be7",
          "e3",
          "O-O",
          "Bd3",
          "Nbd7",
          "Nf3"
        ],
        "move": "c6",
        "title": "Stabilise the centre",
        "prompt": "Support d5 with the c-pawn.",
        "idea": "White can build pressure on the centre. A compact structure gives your pieces time to coordinate.",
        "hint": "Move the c-pawn one square.",
        "why": "…c6 supports d5. Watch White’s queenside minority attack and look for active piece play.",
        "fen": "r1bq1rk1/pppnbppp/5n2/3p2B1/3P4/2NBPN2/PP3PPP/R2QK2R b KQ - 4 8",
        "uci": "c7c6",
        "afterFen": "r1bq1rk1/pp1nbppp/2p2n2/3p2B1/3P4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 9"
      },
      {
        "id": "orthodox-c6",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Be7",
          "e3",
          "O-O",
          "Nf3",
          "Nbd7",
          "Bd3"
        ],
        "move": "c6",
        "title": "Build the Orthodox structure",
        "prompt": "Support d5 before resolving the central tension.",
        "idea": "Your pieces are ready for a solid central structure.",
        "hint": "Move the c-pawn to c6.",
        "why": "…c6 reinforces d5. When White castles, …dxc4 can release the tension before a knight comes to d5.",
        "fen": "r1bq1rk1/pppnbppp/4pn2/3p2B1/2PP4/2NBPN2/PP3PPP/R2QK2R b KQ - 4 7",
        "uci": "c7c6",
        "afterFen": "r1bq1rk1/pp1nbppp/2p1pn2/3p2B1/2PP4/2NBPN2/PP3PPP/R2QK2R w KQ - 0 8"
      },
      {
        "id": "orthodox-take",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Be7",
          "e3",
          "O-O",
          "Nf3",
          "Nbd7",
          "Bd3",
          "c6",
          "O-O"
        ],
        "move": "dxc4",
        "title": "Release the tension",
        "prompt": "Exchange the d-pawn and make room for a knight on d5.",
        "idea": "White has completed king safety. You can now simplify the centre with a purpose.",
        "hint": "Capture the pawn on c4.",
        "why": "…dxc4 makes room for …Nd5 after Bxc4. This is a plan, not a reason to keep the extra pawn at all costs.",
        "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p2B1/2PP4/2NBPN2/PP3PPP/R2Q1RK1 b - - 1 8",
        "uci": "d5c4",
        "afterFen": "r1bq1rk1/pp1nbppp/2p1pn2/6B1/2pP4/2NBPN2/PP3PPP/R2Q1RK1 w - - 0 9"
      },
      {
        "id": "orthodox-nd5",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Be7",
          "e3",
          "O-O",
          "Nf3",
          "Nbd7",
          "Bd3",
          "c6",
          "O-O",
          "dxc4",
          "Bxc4"
        ],
        "move": "Nd5",
        "title": "Trade an active attacker",
        "prompt": "Challenge the bishop on g5 and occupy d5.",
        "idea": "A central knight can offer useful exchanges and reduce White’s pressure.",
        "hint": "Use the knight on f6.",
        "why": "…Nd5 places a knight in the centre and opens the diagonal towards the bishop on g5.",
        "fen": "r1bq1rk1/pp1nbppp/2p1pn2/6B1/2BP4/2N1PN2/PP3PPP/R2Q1RK1 b - - 0 9",
        "uci": "f6d5",
        "afterFen": "r1bq1rk1/pp1nbppp/2p1p3/3n2B1/2BP4/2N1PN2/PP3PPP/R2Q1RK1 w - - 1 10"
      },
      {
        "id": "orthodox-queen",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Be7",
          "e3",
          "O-O",
          "Nf3",
          "Nbd7",
          "Bd3",
          "c6",
          "O-O",
          "dxc4",
          "Bxc4",
          "Nd5",
          "Bxe7"
        ],
        "move": "Qxe7",
        "title": "Recapture and connect",
        "prompt": "Recover the bishop on e7 with your queen.",
        "idea": "Complete the exchange before looking for another plan.",
        "hint": "The queen on d8 can capture e7.",
        "why": "…Qxe7 recovers the bishop. Now look for the …e5 break to free your c8 bishop.",
        "fen": "r1bq1rk1/pp1nBppp/2p1p3/3n4/2BP4/2N1PN2/PP3PPP/R2Q1RK1 b - - 0 10",
        "uci": "d8e7",
        "afterFen": "r1b2rk1/pp1nqppp/2p1p3/3n4/2BP4/2N1PN2/PP3PPP/R2Q1RK1 w - - 0 11"
      },
      {
        "id": "break-trade",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Be7",
          "e3",
          "O-O",
          "Nf3",
          "Nbd7",
          "Bd3",
          "c6",
          "O-O",
          "dxc4",
          "Bxc4",
          "Nd5",
          "Bxe7",
          "Qxe7",
          "e4"
        ],
        "move": "Nxc3",
        "title": "Resolve the central contact",
        "prompt": "Exchange the d5 knight before opening the centre.",
        "idea": "White challenges your knight with e4. Choose a purposeful exchange.",
        "hint": "Capture the knight on c3.",
        "why": "…Nxc3 removes a defender of e4. After bxc3, challenge the centre with …e5.",
        "fen": "r1b2rk1/pp1nqppp/2p1p3/3n4/2BPP3/2N2N2/PP3PPP/R2Q1RK1 b - - 0 11",
        "uci": "d5c3",
        "afterFen": "r1b2rk1/pp1nqppp/2p1p3/8/2BPP3/2n2N2/PP3PPP/R2Q1RK1 w - - 0 12"
      },
      {
        "id": "break-e5",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Be7",
          "e3",
          "O-O",
          "Nf3",
          "Nbd7",
          "Bd3",
          "c6",
          "O-O",
          "dxc4",
          "Bxc4",
          "Nd5",
          "Bxe7",
          "Qxe7",
          "e4",
          "Nxc3",
          "bxc3"
        ],
        "move": "e5",
        "title": "Free the light-squared bishop",
        "prompt": "Carry out the central freeing break.",
        "idea": "Your c8 bishop needs an open diagonal. A central pawn break creates it.",
        "hint": "Advance the e-pawn two squares.",
        "why": "…e5 challenges d4 and frees the c8 bishop. Development and central play belong together.",
        "fen": "r1b2rk1/pp1nqppp/2p1p3/8/2BPP3/2P2N2/P4PPP/R2Q1RK1 b - - 0 12",
        "uci": "e6e5",
        "afterFen": "r1b2rk1/pp1nqppp/2p5/4p3/2BPP3/2P2N2/P4PPP/R2Q1RK1 w - - 0 13"
      },
      {
        "id": "elephant-knight",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Nbd7",
          "cxd5",
          "exd5",
          "Nxd5"
        ],
        "move": "Nxd5",
        "title": "Recognise the Elephant Trap",
        "prompt": "Can your pinned knight capture the knight on d5?",
        "idea": "This pin is to the queen, not the king. Check forcing replies before assuming the knight cannot move.",
        "hint": "There is a checking bishop move if White captures your queen.",
        "why": "…Nxd5 works because Bxd8 can be met by …Bb4+, recovering the queen with a material gain.",
        "fen": "r1bqkb1r/pppn1ppp/5n2/3N2B1/3P4/8/PP2PPPP/R2QKBNR b KQkq - 0 6",
        "uci": "f6d5",
        "afterFen": "r1bqkb1r/pppn1ppp/8/3n2B1/3P4/8/PP2PPPP/R2QKBNR w KQkq - 0 7"
      },
      {
        "id": "elephant-check",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Nbd7",
          "cxd5",
          "exd5",
          "Nxd5",
          "Nxd5",
          "Bxd8"
        ],
        "move": "Bb4+",
        "title": "Use the in-between check",
        "prompt": "Give check before recovering the bishop on d8.",
        "idea": "An intermediate check changes the order of captures.",
        "hint": "The f8 bishop can give check on b4.",
        "why": "…Bb4+ forces White to answer the check. After Qd2, …Bxd2+ wins the queen.",
        "fen": "r1bBkb1r/pppn1ppp/8/3n4/3P4/8/PP2PPPP/R2QKBNR b KQkq - 0 7",
        "uci": "f8b4",
        "afterFen": "r1bBk2r/pppn1ppp/8/3n4/1b1P4/8/PP2PPPP/R2QKBNR w KQkq - 1 8"
      },
      {
        "id": "elephant-queen",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Nbd7",
          "cxd5",
          "exd5",
          "Nxd5",
          "Nxd5",
          "Bxd8",
          "Bb4+",
          "Qd2"
        ],
        "move": "Bxd2+",
        "title": "Recover the queen with check",
        "prompt": "Capture the queen on d2.",
        "idea": "Finish the forcing sequence before counting the material.",
        "hint": "The bishop on b4 attacks d2.",
        "why": "…Bxd2+ wins White’s queen with check. After Kxd2, the king can recover the bishop on d8.",
        "fen": "r1bBk2r/pppn1ppp/8/3n4/1b1P4/8/PP1QPPPP/R3KBNR b KQkq - 2 8",
        "uci": "b4d2",
        "afterFen": "r1bBk2r/pppn1ppp/8/3n4/3P4/8/PP1bPPPP/R3KBNR w KQkq - 0 9"
      },
      {
        "id": "elephant-finish",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Nbd7",
          "cxd5",
          "exd5",
          "Nxd5",
          "Nxd5",
          "Bxd8",
          "Bb4+",
          "Qd2",
          "Bxd2+",
          "Kxd2"
        ],
        "move": "Kxd8",
        "title": "Count the result",
        "prompt": "Recover the bishop on d8.",
        "idea": "Both queens are gone. Complete the sequence and compare the remaining pieces.",
        "hint": "The king on e8 can capture d8.",
        "why": "…Kxd8 leaves Black an extra minor piece. A relative pin can sometimes be broken with a forcing tactic.",
        "fen": "r1bBk2r/pppn1ppp/8/3n4/3P4/8/PP1KPPPP/R4BNR b kq - 0 9",
        "uci": "e8d8",
        "afterFen": "r1bk3r/pppn1ppp/8/3n4/3P4/8/PP1KPPPP/R4BNR w - - 0 10"
      }
    ],
    "chapters": [
      {
        "id": "essentials",
        "title": "Build your QGD",
        "subtitle": "A central foothold and safe development",
        "cards": [
          "d5",
          "e6",
          "nf6",
          "be7",
          "castle"
        ],
        "takeaway": "Support d5, develop the kingside and castle before choosing a central break.",
        "goal": "Develop your queenside and keep the centre sound.",
        "kind": "lesson"
      },
      {
        "id": "exchange",
        "title": "Understand the Exchange",
        "subtitle": "The Carlsbad pawn structure",
        "cards": [
          "exchange-take",
          "exchange-castle",
          "exchange-c6"
        ],
        "takeaway": "Recapture with the e-pawn, secure the king and support d5.",
        "goal": "Find active piece play while watching White’s queenside plan.",
        "kind": "lesson"
      },
      {
        "id": "orthodox",
        "title": "Play the Orthodox plan",
        "subtitle": "Release tension and use d5",
        "cards": [
          "orthodox-c6",
          "orthodox-take",
          "orthodox-nd5",
          "orthodox-queen"
        ],
        "takeaway": "Support d5, exchange on c4 and centralise a knight to reduce White’s pressure.",
        "goal": "Complete development and prepare the freeing …e5 break.",
        "kind": "lesson"
      },
      {
        "id": "counterplay",
        "title": "Find your freeing break",
        "subtitle": "Open the c8 bishop’s diagonal",
        "cards": [
          "break-trade",
          "break-e5"
        ],
        "takeaway": "Exchange the challenged knight and use …e5 to free your light-squared bishop.",
        "goal": "Use your active pieces without weakening the king.",
        "kind": "lesson"
      },
      {
        "id": "elephant",
        "title": "Understand a relative pin",
        "subtitle": "The Elephant Trap, step by step",
        "cards": [
          "elephant-knight",
          "elephant-check",
          "elephant-queen",
          "elephant-finish"
        ],
        "takeaway": "A pin to the queen can be broken when a forcing check recovers material.",
        "goal": "Convert the extra piece with safe development.",
        "kind": "tactic"
      }
    ],
    "anchors": [
      [
        "d4",
        "d5",
        "c4",
        "e6"
      ],
      [
        "d4",
        "d5",
        "c4",
        "e6",
        "Nc3",
        "Nf6"
      ],
      [
        "d4",
        "d5",
        "c4",
        "e6",
        "Nc3",
        "Nf6",
        "Bg5",
        "Be7"
      ],
      [
        "d4",
        "d5",
        "c4",
        "e6",
        "Nc3",
        "Nf6",
        "cxd5",
        "exd5"
      ]
    ]
  }
];
