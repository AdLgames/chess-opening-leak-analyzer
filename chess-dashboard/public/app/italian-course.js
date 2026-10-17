/* Original pilot curriculum. See docs/italian-v2-review.md for scope and validation. */
window.ItalianCourse = {
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
      "why": "1.e4 controls d5 and f5 and frees the bishop on f1."
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
      "why": "Nf3 develops towards the centre, attacks e5 and clears g1 for castling."
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
      "why": "Bc4 develops actively and keeps the way clear for kingside castling."
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
      "why": "c3 supports d4. We will play d3 first, castle and develop before deciding when to break."
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
      "why": "d3 supports e4 and opens c1–d2–e3. An immediate d4 leads to a different, sharper line."
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
      "why": "Castling moves the king away from the centre and brings the rook towards the e-file."
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
      "why": "Re1 reinforces e4 and makes room for the route Nb1–d2–f1–g3."
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
      "why": "d3 protects e4 and keeps the position in the quieter Italian family."
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
      "why": "O-O secures the king. We can follow with c3 and Re1 if Black also castles."
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
      "why": "c3 prepares d4. After …d6 and Re1 we reach the same position as our first chapter."
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
      "why": "Nxf7 attacks the queen on d8 and rook on h8. Black can accept the sacrifice with …Kxf7, which brings the king into the open."
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
      "why": "Qf3+ checks along the f-file and attacks d5 along the diagonal f3–e4–d5."
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
      "why": "Nc3 develops and attacks d5. White has attacking compensation for the sacrificed knight; this is a sharp position, not a forced win."
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
      "why": "Bb3 keeps the diagonal b3–c4–d5–e6–f7. Watch for …b5 and choose the central break carefully."
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
      "why": "Nbd2 develops without blocking the c-pawn. From d2 the knight can head to f1 and g3."
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
      "why": "Nf1 prepares Ng3, where the knight can support the centre and look towards f5 and h5."
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
      "why": "Ng3 puts the knight near f5 and h5. Keep watching Black’s counterplay and prepare d4 when your pieces support it."
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
    }
  ]
};
