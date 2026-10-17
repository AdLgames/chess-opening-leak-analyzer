/* Original opening study notes. Legal lines are checked by the release tests.
   These are study references, not accredited courses or graded lessons. */
window.OpeningGuides = [
  {
    "id": "italian",
    "name": "Italian Game",
    "eco": "C50",
    "side": "white",
    "line": [
      "e4",
      "e5",
      "Nf3",
      "Nc6",
      "Bc4"
    ],
    "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "idea": "The bishop on c4 targets f7. White develops quickly and keeps the option of building a centre with c3 and d4.",
    "plan": "Castle before opening the centre. In quieter lines, d3 supports e4 while the b1 knight develops through d2.",
    "branches": [
      {
        "name": "Two Knights Defence",
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
        "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 1 5"
      },
      {
        "name": "Giuoco Piano",
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
        "fen": "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQK2R w KQkq - 0 6"
      }
    ]
  },
  {
    "id": "ruy",
    "name": "Ruy Lopez",
    "eco": "C60",
    "side": "white",
    "line": [
      "e4",
      "e5",
      "Nf3",
      "Nc6",
      "Bb5"
    ],
    "fen": "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "idea": "Bb5 puts pressure on the knight defending e5. The pressure matters more than immediately winning a pawn.",
    "plan": "After …a6 and Ba4, castle and support the centre with Re1. Prepare c3 and d4 when development allows.",
    "branches": [
      {
        "name": "Morphy Defence",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bb5",
          "a6",
          "Ba4",
          "Nf6",
          "O-O",
          "Be7"
        ],
        "fen": "r1bqk2r/1pppbppp/p1n2n2/4p3/B3P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 4 6"
      },
      {
        "name": "Berlin Defence",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "Bb5",
          "Nf6",
          "O-O",
          "Nxe4",
          "d4"
        ],
        "fen": "r1bqkb1r/pppp1ppp/2n5/1B2p3/3Pn3/5N2/PPP2PPP/RNBQ1RK1 b kq - 0 5"
      }
    ]
  },
  {
    "id": "scotch",
    "name": "Scotch Game",
    "eco": "C45",
    "side": "white",
    "line": [
      "e4",
      "e5",
      "Nf3",
      "Nc6",
      "d4",
      "exd4",
      "Nxd4"
    ],
    "fen": "r1bqkbnr/pppp1ppp/2n5/8/3NP3/8/PPP2PPP/RNBQKB1R b KQkq - 0 4",
    "idea": "White opens the centre early and develops the knight to d4. Both sides get active piece play.",
    "plan": "Develop the queenside pieces and castle. Watch attacks on the d4 knight before choosing where to put your bishop.",
    "branches": [
      {
        "name": "Classical Variation",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "d4",
          "exd4",
          "Nxd4",
          "Bc5",
          "Be3",
          "Qf6"
        ],
        "fen": "r1b1k1nr/pppp1ppp/2n2q2/2b5/3NP3/4B3/PPP2PPP/RN1QKB1R w KQkq - 3 6"
      },
      {
        "name": "Schmidt Variation",
        "line": [
          "e4",
          "e5",
          "Nf3",
          "Nc6",
          "d4",
          "exd4",
          "Nxd4",
          "Nf6",
          "Nc3",
          "Bb4"
        ],
        "fen": "r1bqk2r/pppp1ppp/2n2n2/8/1b1NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 3 6"
      }
    ]
  },
  {
    "id": "vienna",
    "name": "Vienna Game",
    "eco": "C25",
    "side": "white",
    "line": [
      "e4",
      "e5",
      "Nc3"
    ],
    "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/2N5/PPPP1PPP/R1BQKBNR b KQkq - 1 2",
    "idea": "Nc3 supports e4 without deciding the kingside knight’s square. White can develop quietly or challenge with f4.",
    "plan": "In gambit lines, develop rapidly rather than spending tempi protecting every pawn. Keep your king’s safety in view.",
    "branches": [
      {
        "name": "Vienna Gambit",
        "line": [
          "e4",
          "e5",
          "Nc3",
          "Nf6",
          "f4",
          "d5",
          "fxe5",
          "Nxe4"
        ],
        "fen": "rnbqkb1r/ppp2ppp/8/3pP3/4n3/2N5/PPPP2PP/R1BQKBNR w KQkq - 0 5"
      },
      {
        "name": "Quiet development",
        "line": [
          "e4",
          "e5",
          "Nc3",
          "Nc6",
          "Bc4",
          "Nf6",
          "d3",
          "Bc5"
        ],
        "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2NP4/PPP2PPP/R1BQK1NR w KQkq - 1 5"
      }
    ]
  },
  {
    "id": "london",
    "name": "London System",
    "eco": "D02",
    "side": "white",
    "line": [
      "d4",
      "d5",
      "Nf3",
      "Nf6",
      "Bf4"
    ],
    "fen": "rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/5N2/PPP1PPPP/RN1QKB1R b KQkq - 3 3",
    "idea": "White develops the dark-squared bishop before closing the diagonal with e3. The usual setup is compact and flexible.",
    "plan": "Support d4 with e3 and c3, develop the other bishop and castle. React to …c5; the setup is not a reason to ignore the centre.",
    "branches": [
      {
        "name": "Classical setup",
        "line": [
          "d4",
          "d5",
          "Nf3",
          "Nf6",
          "Bf4",
          "e6",
          "e3",
          "Bd6",
          "Bg3"
        ],
        "fen": "rnbqk2r/ppp2ppp/3bpn2/3p4/3P4/4PNB1/PPP2PPP/RN1QKB1R b KQkq - 2 5"
      },
      {
        "name": "Early …c5",
        "line": [
          "d4",
          "d5",
          "Nf3",
          "Nf6",
          "Bf4",
          "c5",
          "e3",
          "Nc6",
          "c3"
        ],
        "fen": "r1bqkb1r/pp2pppp/2n2n2/2pp4/3P1B2/2P1PN2/PP3PPP/RN1QKB1R b KQkq - 0 5"
      }
    ]
  },
  {
    "id": "qg",
    "name": "Queen’s Gambit",
    "eco": "D06",
    "side": "white",
    "line": [
      "d4",
      "d5",
      "c4"
    ],
    "fen": "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq - 0 2",
    "idea": "The c-pawn challenges Black’s central d5 pawn. White tries to build a broad centre or develop with more space.",
    "plan": "Develop behind the central pawns. If Black takes c4, prioritise the centre and development before recovering the pawn.",
    "branches": [
      {
        "name": "Declined",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "Bg5",
          "Be7"
        ],
        "fen": "rnbqk2r/ppp1bppp/4pn2/3p2B1/2PP4/2N5/PP2PPPP/R2QKBNR w KQkq - 4 5"
      },
      {
        "name": "Accepted",
        "line": [
          "d4",
          "d5",
          "c4",
          "dxc4",
          "Nf3",
          "Nf6",
          "e3",
          "e6",
          "Bxc4"
        ],
        "fen": "rnbqkb1r/ppp2ppp/4pn2/8/2BP4/4PN2/PP3PPP/RNBQK2R b KQkq - 0 5"
      }
    ]
  },
  {
    "id": "english",
    "name": "English Opening",
    "eco": "A10",
    "side": "white",
    "line": [
      "c4"
    ],
    "fen": "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1",
    "idea": "White controls d5 from the flank. The centre can stay flexible while the kingside bishop develops on g2.",
    "plan": "Use Nc3 and g3 to put pressure on the centre. Decide on d4 or d3 in response to Black’s setup.",
    "branches": [
      {
        "name": "Symmetrical English",
        "line": [
          "c4",
          "c5",
          "Nc3",
          "Nc6",
          "g3",
          "g6",
          "Bg2",
          "Bg7"
        ],
        "fen": "r1bqk1nr/pp1pppbp/2n3p1/2p5/2P5/2N3P1/PP1PPPBP/R1BQK1NR w KQkq - 2 5"
      },
      {
        "name": "Reversed Sicilian",
        "line": [
          "c4",
          "e5",
          "Nc3",
          "Nf6",
          "g3",
          "d5",
          "cxd5",
          "Nxd5"
        ],
        "fen": "rnbqkb1r/ppp2ppp/8/3np3/8/2N3P1/PP1PPP1P/R1BQKBNR w KQkq - 0 5"
      }
    ]
  },
  {
    "id": "reti",
    "name": "Réti Opening",
    "eco": "A09",
    "side": "white",
    "line": [
      "Nf3",
      "d5",
      "c4"
    ],
    "fen": "rnbqkbnr/ppp1pppp/8/3p4/2P5/5N2/PP1PPPPP/RNBQKB1R b KQkq - 0 2",
    "idea": "White challenges the centre with pieces and a flank pawn rather than immediately occupying it with d4.",
    "plan": "Develop with g3 and Bg2. Watch for chances to undermine d5 or transpose into a queen’s pawn opening.",
    "branches": [
      {
        "name": "Kingside fianchetto",
        "line": [
          "Nf3",
          "d5",
          "c4",
          "e6",
          "g3",
          "Nf6",
          "Bg2",
          "Be7"
        ],
        "fen": "rnbqk2r/ppp1bppp/4pn2/3p4/2P5/5NP1/PP1PPPBP/RNBQK2R w KQkq - 3 5"
      },
      {
        "name": "Advance Variation",
        "line": [
          "Nf3",
          "d5",
          "c4",
          "d4",
          "b4",
          "Nf6",
          "Bb2"
        ],
        "fen": "rnbqkb1r/ppp1pppp/5n2/8/1PPp4/5N2/PB1PPPPP/RN1QKB1R b KQkq - 2 4"
      }
    ]
  },
  {
    "id": "caro",
    "name": "Caro-Kann Defence",
    "eco": "B10",
    "side": "black",
    "line": [
      "e4",
      "c6",
      "d4",
      "d5"
    ],
    "fen": "rnbqkbnr/pp2pppp/2p5/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3",
    "idea": "…c6 supports …d5 so Black can challenge e4. The light-squared bishop often develops before …e6 closes its diagonal.",
    "plan": "Resolve the central tension, develop the bishop actively and bring the kingside pieces out. Look for the freeing break …c5.",
    "branches": [
      {
        "name": "Advance Variation",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "e5",
          "Bf5",
          "Nf3",
          "e6"
        ],
        "fen": "rn1qkbnr/pp3ppp/2p1p3/3pPb2/3P4/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 5"
      },
      {
        "name": "Classical Variation",
        "line": [
          "e4",
          "c6",
          "d4",
          "d5",
          "Nc3",
          "dxe4",
          "Nxe4",
          "Bf5"
        ],
        "fen": "rn1qkbnr/pp2pppp/2p5/5b2/3PN3/8/PPP2PPP/R1BQKBNR w KQkq - 1 5"
      }
    ]
  },
  {
    "id": "sicilian",
    "name": "Sicilian Defence",
    "eco": "B20",
    "side": "black",
    "line": [
      "e4",
      "c5"
    ],
    "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    "idea": "Black attacks d4 from the flank and creates an asymmetrical pawn structure. An open c-file often becomes useful.",
    "plan": "Develop before launching a queenside attack. White’s central space can support fast kingside play, so tempi matter.",
    "branches": [
      {
        "name": "Open Sicilian",
        "line": [
          "e4",
          "c5",
          "Nf3",
          "d6",
          "d4",
          "cxd4",
          "Nxd4",
          "Nf6",
          "Nc3"
        ],
        "fen": "rnbqkb1r/pp2pppp/3p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R b KQkq - 2 5"
      },
      {
        "name": "Alapin Variation",
        "line": [
          "e4",
          "c5",
          "c3",
          "d5",
          "exd5",
          "Qxd5",
          "d4"
        ],
        "fen": "rnb1kbnr/pp2pppp/8/2pq4/3P4/2P5/PP3PPP/RNBQKBNR b KQkq - 0 4"
      }
    ]
  },
  {
    "id": "najdorf",
    "name": "Sicilian Najdorf",
    "eco": "B90",
    "side": "black",
    "line": [
      "e4",
      "c5",
      "Nf3",
      "d6",
      "d4",
      "cxd4",
      "Nxd4",
      "Nf6",
      "Nc3",
      "a6"
    ],
    "fen": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
    "idea": "…a6 controls b5 and keeps options for …e5 or …e6. Black accepts less space in return for an unbalanced position.",
    "plan": "Finish development and choose a central structure. The …b5 break is useful only when the centre and king are secure enough.",
    "branches": [
      {
        "name": "English Attack setup",
        "line": [
          "e4",
          "c5",
          "Nf3",
          "d6",
          "d4",
          "cxd4",
          "Nxd4",
          "Nf6",
          "Nc3",
          "a6",
          "Be3",
          "e5",
          "Nb3"
        ],
        "fen": "rnbqkb1r/1p3ppp/p2p1n2/4p3/4P3/1NN1B3/PPP2PPP/R2QKB1R b KQkq - 1 7"
      },
      {
        "name": "Classical development",
        "line": [
          "e4",
          "c5",
          "Nf3",
          "d6",
          "d4",
          "cxd4",
          "Nxd4",
          "Nf6",
          "Nc3",
          "a6",
          "Be2",
          "e5",
          "Nb3"
        ],
        "fen": "rnbqkb1r/1p3ppp/p2p1n2/4p3/4P3/1NN5/PPP1BPPP/R1BQK2R b KQkq - 1 7"
      }
    ]
  },
  {
    "id": "dragon",
    "name": "Sicilian Dragon",
    "eco": "B70",
    "side": "black",
    "line": [
      "e4",
      "c5",
      "Nf3",
      "d6",
      "d4",
      "cxd4",
      "Nxd4",
      "Nf6",
      "Nc3",
      "g6"
    ],
    "fen": "rnbqkb1r/pp2pp1p/3p1np1/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
    "idea": "The bishop on g7 will influence the long diagonal. Black often plays against White’s queenside while White attacks the king.",
    "plan": "Develop the bishop, castle and look for central counterplay with …d5. Do not rely only on a flank attack.",
    "branches": [
      {
        "name": "Yugoslav Attack setup",
        "line": [
          "e4",
          "c5",
          "Nf3",
          "d6",
          "d4",
          "cxd4",
          "Nxd4",
          "Nf6",
          "Nc3",
          "g6",
          "Be3",
          "Bg7",
          "f3",
          "O-O"
        ],
        "fen": "rnbq1rk1/pp2ppbp/3p1np1/8/3NP3/2N1BP2/PPP3PP/R2QKB1R w KQ - 1 8"
      },
      {
        "name": "Classical Variation",
        "line": [
          "e4",
          "c5",
          "Nf3",
          "d6",
          "d4",
          "cxd4",
          "Nxd4",
          "Nf6",
          "Nc3",
          "g6",
          "Be2",
          "Bg7",
          "O-O"
        ],
        "fen": "rnbqk2r/pp2ppbp/3p1np1/8/3NP3/2N5/PPP1BPPP/R1BQ1RK1 b kq - 3 7"
      }
    ]
  },
  {
    "id": "kan",
    "name": "Sicilian Kan",
    "eco": "B41",
    "side": "black",
    "line": [
      "e4",
      "c5",
      "Nf3",
      "e6",
      "d4",
      "cxd4",
      "Nxd4",
      "a6"
    ],
    "fen": "rnbqkbnr/1p1p1ppp/p3p3/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 0 5",
    "idea": "Black delays committing the queenside knight and prevents Nb5. The flexible …e6 structure leaves several development choices.",
    "plan": "Develop with …Qc7 and …Nf6 when appropriate. Keep an eye on the d5 break and avoid falling behind in development.",
    "branches": [
      {
        "name": "Maróczy setup",
        "line": [
          "e4",
          "c5",
          "Nf3",
          "e6",
          "d4",
          "cxd4",
          "Nxd4",
          "a6",
          "c4",
          "Nf6",
          "Nc3"
        ],
        "fen": "rnbqkb1r/1p1p1ppp/p3pn2/8/2PNP3/2N5/PP3PPP/R1BQKB1R b KQkq - 2 6"
      },
      {
        "name": "Natural development",
        "line": [
          "e4",
          "c5",
          "Nf3",
          "e6",
          "d4",
          "cxd4",
          "Nxd4",
          "a6",
          "Nc3",
          "Qc7",
          "Bd3"
        ],
        "fen": "rnb1kbnr/1pqp1ppp/p3p3/8/3NP3/2NB4/PPP2PPP/R1BQK2R b KQkq - 3 6"
      }
    ]
  },
  {
    "id": "french",
    "name": "French Defence",
    "eco": "C00",
    "side": "black",
    "line": [
      "e4",
      "e6",
      "d4",
      "d5"
    ],
    "fen": "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3",
    "idea": "Black challenges e4 with …d5. Closed centres often give Black play against the base of White’s pawn chain on d4.",
    "plan": "Use …c5 to attack d4 and develop actively. Plan how the light-squared bishop will enter the game.",
    "branches": [
      {
        "name": "Advance Variation",
        "line": [
          "e4",
          "e6",
          "d4",
          "d5",
          "e5",
          "c5",
          "c3",
          "Nc6",
          "Nf3"
        ],
        "fen": "r1bqkbnr/pp3ppp/2n1p3/2ppP3/3P4/2P2N2/PP3PPP/RNBQKB1R b KQkq - 2 5"
      },
      {
        "name": "Winawer Variation",
        "line": [
          "e4",
          "e6",
          "d4",
          "d5",
          "Nc3",
          "Bb4",
          "e5",
          "c5",
          "a3"
        ],
        "fen": "rnbqk1nr/pp3ppp/4p3/2ppP3/1b1P4/P1N5/1PP2PPP/R1BQKBNR b KQkq - 0 5"
      }
    ]
  },
  {
    "id": "scandinavian",
    "name": "Scandinavian Defence",
    "eco": "B01",
    "side": "black",
    "line": [
      "e4",
      "d5",
      "exd5",
      "Qxd5",
      "Nc3",
      "Qa5"
    ],
    "fen": "rnb1kbnr/ppp1pppp/8/q7/8/2N5/PPPP1PPP/R1BQKBNR w KQkq - 2 4",
    "idea": "Black challenges the centre immediately. The queen moves again after Nc3, while White gains time for development.",
    "plan": "Build a compact position with …c6 and …Nf6. Avoid letting the queen become a repeated target.",
    "branches": [
      {
        "name": "Solid development",
        "line": [
          "e4",
          "d5",
          "exd5",
          "Qxd5",
          "Nc3",
          "Qa5",
          "d4",
          "c6",
          "Nf3",
          "Nf6"
        ],
        "fen": "rnb1kb1r/pp2pppp/2p2n2/q7/3P4/2N2N2/PPP2PPP/R1BQKB1R w KQkq - 2 6"
      },
      {
        "name": "Modern …Nf6",
        "line": [
          "e4",
          "d5",
          "exd5",
          "Nf6",
          "d4",
          "Nxd5",
          "Nf3"
        ],
        "fen": "rnbqkb1r/ppp1pppp/8/3n4/3P4/5N2/PPP2PPP/RNBQKB1R b KQkq - 1 4"
      }
    ]
  },
  {
    "id": "pirc",
    "name": "Pirc Defence",
    "eco": "B07",
    "side": "black",
    "line": [
      "e4",
      "d6",
      "d4",
      "Nf6",
      "Nc3",
      "g6"
    ],
    "fen": "rnbqkb1r/ppp1pp1p/3p1np1/8/3PP3/2N5/PPP2PPP/R1BQKBNR w KQkq - 0 4",
    "idea": "Black allows White a broad centre, then prepares to challenge it with pieces and pawn breaks.",
    "plan": "Develop with …Bg7 and castle. Choose between …e5 and …c5 based on White’s setup.",
    "branches": [
      {
        "name": "Classical setup",
        "line": [
          "e4",
          "d6",
          "d4",
          "Nf6",
          "Nc3",
          "g6",
          "Nf3",
          "Bg7",
          "Be2",
          "O-O"
        ],
        "fen": "rnbq1rk1/ppp1ppbp/3p1np1/8/3PP3/2N2N2/PPP1BPPP/R1BQK2R w KQ - 4 6"
      },
      {
        "name": "Austrian Attack",
        "line": [
          "e4",
          "d6",
          "d4",
          "Nf6",
          "Nc3",
          "g6",
          "f4",
          "Bg7",
          "Nf3"
        ],
        "fen": "rnbqk2r/ppp1ppbp/3p1np1/8/3PPP2/2N2N2/PPP3PP/R1BQKB1R b KQkq - 2 5"
      }
    ]
  },
  {
    "id": "queens",
    "name": "Queen’s Gambit Declined",
    "eco": "D30",
    "side": "black",
    "line": [
      "d4",
      "d5",
      "c4",
      "e6"
    ],
    "fen": "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3",
    "idea": "…e6 supports d5 and maintains a strong central foothold. The main development challenge is the light-squared bishop.",
    "plan": "Develop the kingside and castle. Look for …c5 or …e5 to free the position when your pieces are ready.",
    "branches": [
      {
        "name": "Orthodox development",
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
          "O-O"
        ],
        "fen": "rnbq1rk1/ppp1bppp/4pn2/3p2B1/2PP4/2N1P3/PP3PPP/R2QKBNR w KQ - 1 6"
      },
      {
        "name": "Exchange Variation",
        "line": [
          "d4",
          "d5",
          "c4",
          "e6",
          "Nc3",
          "Nf6",
          "cxd5",
          "exd5",
          "Bg5"
        ],
        "fen": "rnbqkb1r/ppp2ppp/5n2/3p2B1/3P4/2N5/PP2PPPP/R2QKBNR b KQkq - 1 5"
      }
    ]
  },
  {
    "id": "slav",
    "name": "Slav Defence",
    "eco": "D10",
    "side": "black",
    "line": [
      "d4",
      "d5",
      "c4",
      "c6"
    ],
    "fen": "rnbqkbnr/pp2pppp/2p5/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3",
    "idea": "…c6 supports d5 without blocking the c8 bishop. Black can develop that bishop before playing …e6.",
    "plan": "Develop the knights and watch the tension on c4 and d5. Only hold an extra c4 pawn if your development allows it.",
    "branches": [
      {
        "name": "Main line",
        "line": [
          "d4",
          "d5",
          "c4",
          "c6",
          "Nf3",
          "Nf6",
          "Nc3",
          "dxc4",
          "a4",
          "Bf5"
        ],
        "fen": "rn1qkb1r/pp2pppp/2p2n2/5b2/P1pP4/2N2N2/1P2PPPP/R1BQKB1R w KQkq - 1 6"
      },
      {
        "name": "Exchange Slav",
        "line": [
          "d4",
          "d5",
          "c4",
          "c6",
          "cxd5",
          "cxd5",
          "Nc3",
          "Nf6",
          "Bf4"
        ],
        "fen": "rnbqkb1r/pp2pppp/5n2/3p4/3P1B2/2N5/PP2PPPP/R2QKBNR b KQkq - 3 5"
      }
    ]
  },
  {
    "id": "nimzo",
    "name": "Nimzo-Indian Defence",
    "eco": "E20",
    "side": "black",
    "line": [
      "d4",
      "Nf6",
      "c4",
      "e6",
      "Nc3",
      "Bb4"
    ],
    "fen": "rnbqk2r/pppp1ppp/4pn2/8/1bPP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 2 4",
    "idea": "Bb4 pins the knight and restricts e4. Black can trade the bishop to damage White’s pawn structure, but gives up the bishop pair.",
    "plan": "Pressure the centre with …d5 or …c5. Judge the bishop-for-knight trade by the resulting structure, not by habit.",
    "branches": [
      {
        "name": "Rubinstein Variation",
        "line": [
          "d4",
          "Nf6",
          "c4",
          "e6",
          "Nc3",
          "Bb4",
          "e3",
          "O-O",
          "Bd3",
          "d5"
        ],
        "fen": "rnbq1rk1/ppp2ppp/4pn2/3p4/1bPP4/2NBP3/PP3PPP/R1BQK1NR w KQ - 0 6"
      },
      {
        "name": "Classical Variation",
        "line": [
          "d4",
          "Nf6",
          "c4",
          "e6",
          "Nc3",
          "Bb4",
          "Qc2",
          "O-O",
          "a3",
          "Bxc3+",
          "Qxc3"
        ],
        "fen": "rnbq1rk1/pppp1ppp/4pn2/8/2PP4/P1Q5/1P2PPPP/R1B1KBNR b KQ - 0 6"
      }
    ]
  },
  {
    "id": "kings",
    "name": "King’s Indian Defence",
    "eco": "E60",
    "side": "black",
    "line": [
      "d4",
      "Nf6",
      "c4",
      "g6",
      "Nc3",
      "Bg7",
      "e4",
      "d6"
    ],
    "fen": "rnbqk2r/ppp1ppbp/3p1np1/8/2PPP3/2N5/PP3PPP/R1BQKBNR w KQkq - 0 5",
    "idea": "Black allows a large centre and prepares to challenge it with …e5 or …c5. The g7 bishop is central to the counterplay.",
    "plan": "Castle and strike at the centre. If the centre closes, choose a flank plan that matches the pawn structure.",
    "branches": [
      {
        "name": "Classical Variation",
        "line": [
          "d4",
          "Nf6",
          "c4",
          "g6",
          "Nc3",
          "Bg7",
          "e4",
          "d6",
          "Nf3",
          "O-O",
          "Be2",
          "e5"
        ],
        "fen": "rnbq1rk1/ppp2pbp/3p1np1/4p3/2PPP3/2N2N2/PP2BPPP/R1BQK2R w KQ - 0 7"
      },
      {
        "name": "Sämisch Variation",
        "line": [
          "d4",
          "Nf6",
          "c4",
          "g6",
          "Nc3",
          "Bg7",
          "e4",
          "d6",
          "f3",
          "O-O",
          "Be3"
        ],
        "fen": "rnbq1rk1/ppp1ppbp/3p1np1/8/2PPP3/2N1BP2/PP4PP/R2QKBNR b KQ - 2 6"
      }
    ]
  }
];
