"""Self-tests: run with `python -m pytest tests -q` (or `python tests/test_pipeline.py`).

The Explorer responses used here are SYNTHETIC fixtures, written into the on-disk cache
so the pipeline can be exercised in --offline mode without hitting the Lichess API.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.analyze import analyze, build_nodes  # noqa: E402
from chessopening.engine import EngineAnalyzer, bundled_engine, find_engine  # noqa: E402
from chessopening.localdb import LocalOpeningDatabase, epd_after  # noqa: E402
from chessopening.explorer import OpeningExplorer  # noqa: E402
from chessopening.pgn_loader import detect_main_player, find_pgn_files, load_games  # noqa: E402

PGN_DIR = os.path.join(ROOT, "sample_pgns")
PLAYER = "SamplePlayer"


def _engine_or_skip() -> str:
    try:
        return find_engine()
    except FileNotFoundError:
        pytest.skip("Stockfish binary not available")


def test_bundled_engine_is_present_and_speaks_uci():
    path = bundled_engine()
    if not path:
        pytest.skip("no bundled engine - run tools/install_stockfish.py")
    out = subprocess.run([path], input="uci\nquit\n", capture_output=True, text=True, timeout=30).stdout
    assert "id name Stockfish" in out
    assert "uciok" in out
    assert find_engine() == path  # bundled copy wins over PATH


# ---------------- PGN layer ----------------
def test_pgn_discovery_and_player_detection():
    files = find_pgn_files(PGN_DIR)
    assert files, "sample PGNs missing - run tools/make_sample_pgns.py"
    assert detect_main_player(files) == PLAYER


def test_only_player_moves_are_recorded_and_depth_is_capped():
    games = list(load_games(PGN_DIR, PLAYER, max_moves=5))
    assert games
    for g in games:
        assert g.player_color in ("white", "black")
        for rec in g.plies:
            assert rec.ply <= 10
            expect_white_to_move = rec.player_color == "white"
            assert (" w " in rec.fen_before) is expect_white_to_move
        # scores follow the result from the player's point of view
        if g.result == "1-0":
            assert g.player_score == (1.0 if g.player_color == "white" else 0.0)


# ---------------- Explorer layer ----------------
FIXTURE = {  # synthetic: position after 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5
    "white": 4000, "draws": 1000, "black": 5000,
    "opening": {"eco": "C50", "name": "Italian Game: Giuoco Piano"},
    "moves": [
        {"uci": "e1g1", "san": "O-O", "white": 3000, "draws": 800, "black": 2200, "averageRating": 1750},
        {"uci": "c2c3", "san": "c3", "white": 1500, "draws": 400, "black": 1100, "averageRating": 1760},
        {"uci": "f3e5", "san": "Nxe5", "white": 200, "draws": 40, "black": 760, "averageRating": 1700},
    ],
}


def test_explorer_score_and_popularity_math():
    stats = OpeningExplorer.parse(FIXTURE)
    assert stats.eco == "C50"
    assert stats.games == 10000
    assert stats.score_for("white") == pytest.approx(0.45)
    nxe5 = stats.move("f3e5")
    assert nxe5 is not None and nxe5.games == 1000
    assert nxe5.score_for("white") == pytest.approx(0.22)
    assert stats.popularity("f3e5") == pytest.approx(1000 / 10000, abs=1e-6)
    assert stats.best_by_score("white")[0].san == "O-O"


def test_explorer_offline_mode_returns_empty_without_network():
    ex = OpeningExplorer(cache_dir="/tmp/explorer-cache-test", offline=True)
    assert ex.lookup("e2e4").games == 0
    assert ex.stats["api_calls"] == 0


# ---------------- Engine layer ----------------
def test_engine_detects_a_piece_losing_opening_move():
    path = _engine_or_skip()
    fen = "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
    with EngineAnalyzer(path, depth=12, multipv=3) as eng:
        ev = eng.evaluate_move(fen, "f3e5")  # 4.Nxe5?? Nxe5 wins a piece for Black
        assert ev.played_san == "Nxe5"
        assert ev.eval_drop_pawns > 0.8
        assert ev.played_rank is None or ev.played_rank > 1
        assert len(ev.alternatives) == 3
        assert ev.best_cp > ev.played_cp


def test_engine_accepts_a_good_move_without_flagging_it():
    path = _engine_or_skip()
    fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
    with EngineAnalyzer(path, depth=12, multipv=2) as eng:
        ev = eng.evaluate_move(fen, "g1f3")  # 2.Nf3
        assert ev.eval_drop_pawns < 0.5


# ---------------- Local database layer ----------------
def test_local_db_build_lookup_and_naming(tmp_path):
    """Build a small local database out of the sample PGNs and query it."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from build_local_db import build  # noqa: PLC0415

    db_path = str(tmp_path / "mini.sqlite")
    info = build(
        find_pgn_files(PGN_DIR),
        db_path,
        max_moves=10,
        speeds=None,
        min_move_games=1,
        offline_eco=True,   # use the vendored eco.tsv, no network
    )
    assert info["games"] > 50 and info["positions"] > 10

    db = LocalOpeningDatabase(db_path)
    assert db.total_games() == info["games"]
    stats = db.lookup("e2e4,e7e5,g1f3,b8c6,f1c4,f8c5")   # Italian, Giuoco Piano
    assert stats.games > 0
    nxe5 = stats.move("f3e5")
    assert nxe5 is not None and nxe5.san == "Nxe5"
    assert 0.0 <= nxe5.score_for("white") <= 1.0
    assert stats.popularity("f3e5") is not None
    if stats.eco:  # ECO naming comes from the vendored table when present
        assert stats.eco.startswith("C")
    assert db.lookup("e2e4,e7e5,d1h5,g8f6,h5f7").games == 0  # unseen position
    db.close()


def test_epd_after_matches_pushed_board():
    import chess

    board = chess.Board()
    for uci in ("e2e4", "c7c5", "g1f3"):
        board.push(chess.Move.from_uci(uci))
    assert epd_after("e2e4,c7c5,g1f3") == board.epd()
    assert epd_after("") == chess.Board().epd()


# ---------------- End to end ----------------
def _seed_cache(cache_dir: str) -> None:
    """Write the synthetic Explorer response for the Italian position into the cache."""
    ex = OpeningExplorer(cache_dir=os.path.join(cache_dir, "explorer"))
    play = "e2e4,e7e5,g1f3,b8c6,f1c4,f8c5"
    path = ex._cache_path(ex._params(play))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(FIXTURE, fh)


def test_end_to_end_report_flags_winrate_decline_and_eval_drop(tmp_path):
    out = str(tmp_path / "out")
    cache = str(tmp_path / "cache")
    _seed_cache(cache)
    result = analyze(
        pgn_dir=PGN_DIR,
        player=PLAYER,
        out_dir=out,
        engine_path=_engine_or_skip(),
        depth=12,
        multipv=3,
        min_games=3,
        max_moves=15,
        offline=True,
        cache_dir=cache,
        log=lambda *a: None,
    )
    assert result["games"] > 50
    import csv

    rows = list(csv.DictReader(open(result["report"], encoding="utf-8")))
    assert rows, "expected at least one flagged row"
    # header contract
    for col in ("fen", "variation_line", "eval_drop_pawns", "engine_best_1", "score_gap_vs_db_pct"):
        assert col in rows[0]
    # the seeded Italian position: 4.Nxe5 scores 22% in the fixture, sample player scores ~11%
    italian = [r for r in rows if r["variation_line"].endswith("Bc4 Bc5 Nxe5")]
    assert italian, "Nxe5 decision missing from report"
    row = italian[0]
    assert "EVAL_DROP" in row["flag"]
    assert "WINRATE_DECLINE" in row["flag"]
    assert row["eco"] == "C50"
    assert float(row["eval_drop_pawns"]) > 0.8
    assert float(row["score_gap_vs_db_pct"]) < 0
    assert row["engine_best_1"] and row["engine_best_1_cp"]
    # rows are ordered by priority
    priorities = [float(r["priority"]) for r in rows]
    assert priorities == sorted(priorities, reverse=True)
    assert os.path.exists(result["summary"])


def test_end_to_end_against_bundled_local_db(tmp_path):
    """Full offline run: bundled SQLite database + bundled engine, no network at all."""
    from chessopening.localdb import DEFAULT_DB

    if not os.path.exists(DEFAULT_DB):
        pytest.skip("no bundled opening database - run tools/build_local_db.py")
    out = str(tmp_path / "local-out")
    result = analyze(
        pgn_dir=PGN_DIR,
        player=PLAYER,
        out_dir=out,
        engine_path=_engine_or_skip(),
        depth=10,
        multipv=3,
        min_games=3,
        db="local",
        min_db_games=20,
        cache_dir=str(tmp_path / "cache"),
        log=lambda *a: None,
    )
    import csv

    rows = list(csv.DictReader(open(result["report"], encoding="utf-8")))
    assert rows
    with_db = [r for r in rows if r["db_position_games"]]
    assert with_db, "local database produced no baselines"
    r = with_db[0]
    assert int(r["db_position_games"]) >= 20
    assert 0.0 <= float(r["db_position_score_pct"]) <= 100.0
    assert r["score_gap_vs_db_pct"]


def test_cli_runs_offline_without_engine(tmp_path):
    out = str(tmp_path / "cli-out")
    proc = subprocess.run(
        [sys.executable, "-m", "chessopening", "--pgn-dir", PGN_DIR, "--out-dir", out,
         "--db", "lichess", "--offline", "--no-engine", "--min-games", "5"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Auto-detected player: SamplePlayer" in proc.stdout
    assert os.path.exists(os.path.join(out, "variation_summary.csv"))
    shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([os.path.abspath(__file__), "-q"]))
