"""Board facts are reproducible; clock provenance and user causes stay distinct."""

import json
import chess
import pytest
from chessopening.decision_evidence import decision_context, build_decision_evidence
from chessopening.pgn_loader import load_games
from chessopening.board import BoardError


def board(line):
    b = chess.Board()
    for san in line.split():
        b.push_san(san)
    return b


def test_legal_captures_are_context_not_claims_of_winning_material():
    b = board("e4 e5 Nf3 Nc6 Bc4 Bc5")
    c = decision_context(b.fen(), "Nxe5", "O-O")
    assert c["playedUci"] == "f3e5"
    assert "central-king" in c["tags"] and "alternative-castles" in c["tags"]
    assert c["alternative"]["uci"] == "e1g1"
    assert any(x["san"] == "Nxe5" and x["square"] == "e5" for x in c["captures"])
    assert "requires further analysis" in " ".join(f["text"] for f in c["facts"])
    after = chess.Board(c["after"])
    for capture in c["captures"]:
        next_board = after.copy()
        next_board.push_san(capture["san"])
        assert capture["fen"] == next_board.fen()
    assert "psychological" in c["scope"]


def test_check_context_and_invalid_moves():
    b = board("e4 e5 Nf3 Nc6 Bb5 d6 Bxc6+ bxc6 Nxe5 dxe5 Qh5 g6 Qxe5+")
    assert "in-check" in decision_context(b.fen(), "Be7")["tags"]
    assert decision_context(chess.STARTING_FEN, "e4", "Qh9")["alternative"] is None
    with pytest.raises(BoardError):
        decision_context(chess.STARTING_FEN, "e5")
    with pytest.raises(BoardError):
        decision_context("broken", "e4")


def game(tmp_path, player="Alice", time_control="300+2", moves=None):
    p = tmp_path / "clock.pgn"
    p.write_text(f"""[Site "https://lichess.org/abcdefgh"]
[White "Alice"]
[Black "Bob"]
[Date "2026.10.18"]
[Result "1-0"]
[TimeControl "{time_control}"]

{moves or '1. e4 {[%clk 0:05:01]} e5 {[%clk 0:04:50]} 2. Nf3 {[%clk 0:04:55]} Nc6 {[%clk 0:04:40]} 3. Bc4 {[%emt 0:00:06] [%clk 0:00:40]} Bc5 1-0'}
""")
    return list(load_games(str(p), player))[0]


@pytest.mark.parametrize("player,elapsed", [("Alice", 8), ("Bob", 12)])
def test_clock_difference_uses_same_players_previous_clock_and_increment(
    tmp_path, player, elapsed
):
    g = game(tmp_path, player)
    assert g.plies[0].spent_seconds is None
    assert g.plies[1].spent_seconds == elapsed
    assert g.plies[1].spent_source == "clock-difference"
    if player == "Alice":
        assert g.plies[2].spent_source == "pgn-emt" and g.plies[2].spent_seconds == 6


@pytest.mark.parametrize("tc", ["?", "40/7200:3600", "-"])
def test_unknown_or_staged_time_control_has_no_invented_elapsed(tmp_path, tc):
    g = game(tmp_path, time_control=tc)
    assert g.plies[1].clock_after == 295 and g.plies[1].spent_seconds is None
    assert g.plies[2].spent_seconds == 6


def test_missing_clock_breaks_baseline_and_increasing_clock_has_no_negative_time(
    tmp_path,
):
    g = game(
        tmp_path,
        moves="1. e4 {[%clk 0:05:00]} e5 2. Nf3 Nc6 3. Bc4 {[%clk 0:04:40]} Bc5 4. d3 {[%clk 0:05:00]} d6 1-0",
    )
    assert all(r.spent_seconds is None for r in g.plies)


def test_source_counts_are_deduplicated_and_do_not_require_clock_data(tmp_path):
    g = game(tmp_path)
    rec = g.plies[-1]
    row = {
        "fen": rec.fen_before,
        "your_move": rec.san,
        "your_games": "3",
        "engine_best_1": "Bc4",
    }
    # Same imported game twice must not manufacture extra clock observations.
    data = build_decision_evidence([row], [g, g])
    d = data["decisions"][0]
    assert (
        d["reportedOccurrences"] == 3
        and d["uniqueSourceGames"] == d["sourceDecisions"] == 1
    )
    assert d["clockSamples"] == d["under60Seconds"] == 1
    assert d["sources"][0]["spentSource"] == "pgn-emt"
    assert "not combined" in data["scope"]
    fresh = build_decision_evidence([row])
    assert fresh["decisions"][0]["clockSamples"] == 0
    assert (
        build_decision_evidence([{"fen": "bad", "your_move": "e4"}])["includedRows"]
        == 0
    )
    json.dumps(data, allow_nan=False)


def test_generic_site_does_not_merge_separate_games_and_link_is_preserved(tmp_path):
    p = tmp_path / "games.pgn"
    body = '[Site "Chess.com"]\n[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n'
    p.write_text(
        body
        + "\n"
        + body
        + "\n"
        + body.replace(
            '[Site "Chess.com"]',
            '[Site "Chess.com"]\n[Link "https://www.chess.com/game/live/123456789"]',
        )
    )
    games = list(load_games(str(p), "Alice"))
    assert len({g.game_id for g in games}) == 3
    assert games[2].game_id == "https://www.chess.com/game/live/123456789"
    rec = games[0].plies[0]
    data = build_decision_evidence(
        [{"fen": rec.fen_before, "your_move": "e4", "your_games": 3}], games
    )
    assert data["decisions"][0]["uniqueSourceGames"] == 3


def test_en_passant_capture_uses_the_actual_captured_pawn_square():
    # A direct black pawn on d4 has an en-passant reply to White's e2-e4.
    b = chess.Board("4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1")
    c = decision_context(b.fen(), "e4")
    cap = next(x for x in c["captures"] if x["uci"] == "d4e3")
    assert cap["square"] == "e4" and cap["to"] == "e3" and cap["piece"] == "pawn"
    after = chess.Board(c["after"])
    after.push_uci("d4e3")
    assert after.fen() == cap["fen"] and after.piece_at(chess.E4) is None
