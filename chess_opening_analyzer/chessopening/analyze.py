"""Aggregate PGN opening decisions, cross-reference Lichess stats, add engine verdicts, write CSVs."""
from __future__ import annotations

import chess
import csv
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field

from .engine import EngineAnalyzer, PositionEval
from .evalstore import DEFAULT_EVALS, open_store
from .explorer import BOOK_PRIOR_GAMES, OpeningExplorer, PositionStats, Z_CONFIDENCE, score_interval
from .localdb import DEFAULT_DB, LocalOpeningDatabase
from .bands import ALL, band_for, label as band_label
from .marks import (DEFAULT_STATE, apply_gap_decisions, filter_flags, load_gap_decisions,
                    load_marks)
from .pgn_loader import GameSummary, PlyRecord, load_games
from .repertoire import (COVERAGE_FIELDS, best_reply, build_tree, find_gaps,
                         tree_totals)


@dataclass
class Node:
    """All games in which the player reached one position and chose one move."""

    epd: str
    fen: str
    played_uci: str
    played_san: str
    player_color: str
    ply: int
    move_number: int
    line_san: str
    line_uci: str
    eco: str = ""
    opening: str = ""
    wins: int = 0
    draws: int = 0
    losses: int = 0
    games: list[str] = field(default_factory=list)

    @property
    def n(self) -> int:
        return self.wins + self.draws + self.losses

    @property
    def score(self) -> float:
        return (self.wins + 0.5 * self.draws) / self.n if self.n else 0.0

    def add(self, rec: PlyRecord) -> None:
        if rec.player_score == 1.0:
            self.wins += 1
        elif rec.player_score == 0.5:
            self.draws += 1
        else:
            self.losses += 1
        if len(self.games) < 8:
            self.games.append(rec.game_id)


REPORT_FIELDS = [
    "priority",
    "flag",
    "eco",
    "opening",
    "variation_line",
    "move_number",
    "ply",
    "player_color",
    "your_move",
    "your_move_uci",
    "fen",
    "your_games",
    "your_wins",
    "your_draws",
    "your_losses",
    "your_score_pct",
    "your_score_lo_pct",
    "your_score_hi_pct",
    "confidence",
    "category",
    "category_label",
    "committed",
    "explanation",
    "consequence",
    "refutation",
    "baseline_pct",
    "baseline_source",
    "baseline_games",
    # Which population the comparison actually used. Named per row because a thin position
    # widens back toward everybody, so it is not always the player's own band.
    "baseline_band",
    "db_move_games",
    "db_move_score_pct",
    "db_move_popularity_pct",
    "db_position_games",
    "db_position_score_pct",
    "score_gap_vs_db_pct",
    "lost_points",
    "lost_points_conservative",
    "eval_before_cp",
    "eval_after_cp",
    "eval_drop_pawns",
    "engine_rank_of_your_move",
    "engine_best_1",
    # The move the drill teaches, so the review schedule can name it. Only the first
    # alternative needs it; the others are read by people, not machines.
    "engine_best_1_uci",
    "engine_best_1_cp",
    "engine_best_1_db_score_pct",
    "engine_best_2",
    "engine_best_2_cp",
    "engine_best_2_db_score_pct",
    "engine_best_3",
    "engine_best_3_cp",
    "engine_best_3_db_score_pct",
    "sample_games",
]


def build_nodes(
    pgn_dir: str,
    player: str,
    max_moves: int = 15,
    color: str = "both",
    max_games: int | None = None,
) -> tuple[dict[tuple[str, str], Node], list[GameSummary]]:
    """Fold the player's games into one Node per (position, move played).

    `max_games` stops after that many of the player's games — used by the hosted
    deployment to keep a run inside its time budget.
    """
    nodes: dict[tuple[str, str], Node] = {}
    games: list[GameSummary] = []
    for game in load_games(pgn_dir, player, max_moves=max_moves, color=color):
        games.append(game)
        for rec in game.plies:
            key = (rec.epd_before, rec.uci)
            node = nodes.get(key)
            if node is None:
                node = nodes[key] = Node(
                    epd=rec.epd_before,
                    fen=rec.fen_before,
                    played_uci=rec.uci,
                    played_san=rec.san,
                    player_color=rec.player_color,
                    ply=rec.ply,
                    move_number=rec.move_number,
                    line_san=rec.line_san,
                    line_uci=rec.line_uci,
                    eco=rec.eco,
                    opening=rec.opening,
                )
            node.add(rec)
        if max_games is not None and len(games) >= max_games:
            break
    return nodes, games


def _pct(x: float | None) -> str:
    return "" if x is None else f"{100 * x:.1f}"


def flags_winrate_decline(
    score_hi: float, baseline: float | None, gap: float | None, threshold: float
) -> bool:
    """Whether a repeated decision really is scoring below the book.

    Two conditions, not one: the observed gap must be wide enough to matter, *and* the
    player must still be behind at the generous end of their own confidence interval. The
    second is what stops a three-game sample from reading as a crisis.
    """
    if gap is None or baseline is None:
        return False
    return gap <= -threshold and score_hi < baseline


def _round_pct(fraction: float) -> int:
    """A fraction as a whole percentage, rounding halves up.

    Python's `round` rounds halves to even, so 62.5% becomes 62 while the browser's
    `Math.round` makes it 63 — the same figure disagreeing with itself on one screen.
    """
    return int(100 * fraction + 0.5)


# Four kinds of problem, because they need four different responses. An objective mistake is
# a fact about the position and wants the correct move learned. A practical weakness is a
# fact about the player's results and may want a different line altogether. A knowledge gap
# wants preparation for something that has not happened yet. And a finding on thin evidence
# wants nothing except another month of games.
CATEGORIES = {
    "objective": ("Loses ground", "The move itself is the problem: it hands over material or the advantage."),
    "practical": ("Not working for you", "Playable, but your results with it are well below what the position is worth."),
    "knowledge": ("Unfamiliar", "A position you will meet but have barely played."),
    "unproven": ("Worth watching", "Too few games so far to be sure this is real."),
}


def classify(flags: list[str], confidence: str, eval_drop_pawns: float, threshold: float) -> str:
    """Which of the four kinds of problem this finding is.

    An engine drop outranks everything, including a thin sample: whether a move throws away
    a piece is a property of the position, not of how many times it has been played. The
    win-rate flags are the opposite — they are claims about the player's results, so on thin
    evidence they are downgraded to `unproven` rather than asserted.
    """
    if eval_drop_pawns >= threshold:
        return "objective"
    if confidence == "low":
        return "unproven"
    if "WINRATE_DECLINE" in flags:
        return "practical"
    return "practical" if "OFFBEAT_MOVE" in flags else "unproven"


def describe_consequence(fen: str, played_uci: str, refutation_uci: str) -> str:
    """What the opponent's reply actually wins, in words.

    "The engine prefers Bc4" tells a club player nothing. "Black replies Nxe5, winning a
    piece" tells them what they missed, and it is derivable from the two moves themselves.
    """
    if not refutation_uci:
        return ""
    try:
        board = chess.Board(fen)
        mover = board.turn
        before = _material(board, mover)
        played = chess.Move.from_uci(played_uci)
        # push() does not check legality, so a bad move would otherwise produce a
        # confident sentence about a position that cannot happen.
        if played not in board.legal_moves:
            return ""
        board.push(played)
        reply_move = chess.Move.from_uci(refutation_uci)
        if reply_move not in board.legal_moves:
            return ""
        reply_san = board.san(reply_move)
        board.push(reply_move)
        lost = before - _material(board, mover)
    except (ValueError, AssertionError, IndexError):
        return ""

    side = "Black" if mover == chess.WHITE else "White"
    # Bands named the way a player would say it. "A piece" starts at 200 so that winning a
    # knight for a pawn — the commonest opening disaster there is — reads as a piece rather
    # than being mistaken for the exchange, which is specifically rook for minor.
    for cost, name in ((800, "the queen"), (400, "a rook"), (200, "a piece"),
                       (140, "the exchange"), (60, "a pawn")):
        if lost >= cost:
            return f"{side} replies {reply_san}, winning {name}."
    return f"{side} replies {reply_san}, and the position turns against you."


def _material(board: chess.Board, color: chess.Color) -> int:
    """Material in centipawns from `color`'s point of view."""
    values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
              chess.ROOK: 500, chess.QUEEN: 900}
    total = 0
    for piece_type, value in values.items():
        total += value * len(board.pieces(piece_type, color))
        total -= value * len(board.pieces(piece_type, not color))
    return total


def confidence_label(your_games: int, baseline_games: int, baseline_source: str) -> str:
    """How much weight the reader should put on this row's comparison.

    Two things can be thin: how often the player made the decision, and how well the book
    knows the position. The weaker of the two decides.
    """
    if your_games >= 15 and baseline_source == "move" and baseline_games >= 500:
        return "high"
    if your_games < 6 or baseline_games < 100:
        return "low"
    return "medium"


def explain(
    node: Node,
    baseline: float | None,
    baseline_source: str,
    baseline_games: int,
    ev: PositionEval | None,
    best_san: str,
    confidence: str,
    committed: bool = False,
) -> str:
    """One plain sentence saying what is wrong, for a reader who does not know what a
    centipawn is. Built from figures already computed, so the CLI, the API and both
    dashboards can share the same wording."""
    move_label = f"{node.move_number}{'.' if node.player_color == 'white' else '...'}{node.played_san}"
    times = "once" if node.n == 1 else f"{node.n} times"
    parts = [f"You played {move_label} {times} and scored {_round_pct(node.score)}%"]

    if baseline is not None:
        peers = (
            f"players at this level score {_round_pct(baseline)}% with it"
            if baseline_source == "move"
            else f"the position is worth {_round_pct(baseline)}% on average"
        )
        parts.append(f", where {peers}")
        shed = (baseline - node.score) * node.n
        if shed > 0.5:
            parts.append(f" — about {shed:.1f} points of results given away")
    parts.append(".")

    # What actually goes wrong, rather than which move an engine happens to prefer.
    consequence = describe_consequence(node.fen, node.played_uci, ev.refutation_uci if ev else "")
    if consequence:
        parts.append(f" {consequence}")
    if best_san:
        instead = f" {best_san} keeps the position in hand"
        if ev is not None and ev.eval_drop_pawns > 0:
            parts.append(f"{instead} — {ev.eval_drop_pawns:.1f} pawns better than what you played.")
        else:
            parts.append(f"{instead}.")
    elif ev is not None and ev.eval_drop_pawns > 0:
        parts.append(f" The engine rates it {ev.eval_drop_pawns:.1f} pawns worse than the best move here.")

    if confidence == "low":
        parts.append(" Based on few games so far, so treat it as a hint rather than a verdict.")
    if committed:
        # They have already chosen this line. Say why it is still here rather than
        # repeating an argument they have settled.
        parts.append(" This is your chosen move, and it is only listed because the position "
                     "itself goes wrong here — not because others prefer something else.")
    return "".join(parts)


def analyze(
    pgn_dir: str,
    player: str,
    out_dir: str,
    engine_path: str | None = None,
    depth: int = 18,
    movetime_ms: int | None = None,
    multipv: int = 3,
    threads: int = 2,
    max_moves: int = 15,
    color: str = "both",
    min_games: int = 3,
    min_ply: int = 2,
    eval_drop_threshold: float = 0.8,
    score_gap_threshold: float = 0.06,
    min_db_move_games: int = 30,
    book_prior_games: int = BOOK_PRIOR_GAMES,
    confidence_z: float = Z_CONFIDENCE,
    no_evals: bool = False,
    eval_store_path: str = DEFAULT_EVALS,
    marks_path: str = DEFAULT_STATE,
    no_marks: bool = False,
    coverage_off: bool = False,
    coverage_min_reach: float = 0.02,
    db: str = "lichess",
    local_db_path: str = DEFAULT_DB,
    min_db_games: int = 0,
    speeds: str = "blitz,rapid,classical",
    ratings: str = "1600,1800,2000",
    offline: bool = False,
    no_engine: bool = False,
    max_games: int | None = None,
    engine_budget_s: float | None = None,
    cache_dir: str | None = None,
    log=print,
) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    cache_dir = cache_dir or os.path.join(out_dir, ".cache")
    notes: list[str] = []
    nodes, games = build_nodes(pgn_dir, player, max_moves=max_moves, color=color,
                              max_games=max_games)
    if max_games is not None and len(games) >= max_games:
        notes.append(f"stopped after the first {max_games} games")
    log(f"Parsed {len(games)} games for '{player}' -> {len(nodes)} distinct opening decisions")
    if not games:
        raise SystemExit(f"No games found for player '{player}' in {pgn_dir}")

    repeated = {k: n for k, n in nodes.items() if n.n >= min_games and n.ply >= min_ply}
    log(f"{len(repeated)} decisions were repeated at least {min_games} time(s) from ply {min_ply} on")

    # ---- Opening database cross-reference (local SQLite or Lichess Explorer) ----
    explorer: LocalOpeningDatabase | OpeningExplorer
    if db == "local":
        explorer = LocalOpeningDatabase(local_db_path, min_position_games=min_db_games)
        log(f"Opening database: {explorer.description}")
    else:
        explorer = OpeningExplorer(
            cache_dir=os.path.join(cache_dir, "explorer"),
            db=db,
            speeds=speeds,
            ratings=ratings,
            offline=offline,
        )
    # Compare the player against players of their own strength, when the book can. The
    # median of their own games is the right centre: a mean is dragged around by the odd
    # game against somebody far stronger, and a provisional rating early in an archive.
    ratings_seen = sorted(g.player_rating for g in games if g.player_rating)
    player_rating = ratings_seen[len(ratings_seen) // 2] if ratings_seen else None
    player_band = band_for(player_rating)
    banded = db == "local" and getattr(explorer, "has_bands", False) and player_band != ALL
    if banded:
        log(f"Your rating reads as about {player_rating}, so you are being compared against "
            f"{band_label(player_band)} rather than everybody")
    elif db == "local" and player_band != ALL:
        log("This opening book has no rating bands, so the comparison is against all "
            "ratings together. Rebuilding it adds them.")

    pos_stats: dict[str, PositionStats] = {}
    for i, node in enumerate(repeated.values(), start=1):
        parent = ",".join(node.line_uci.split(",")[:-1])  # position BEFORE the player's move
        if node.epd not in pos_stats:
            pos_stats[node.epd] = (explorer.lookup(parent, band=player_band) if banded
                                   else explorer.lookup(parent))
        if i % 25 == 0:
            log(f"  opening db: {i}/{len(repeated)} positions looked up")
    if db == "local":
        log(f"Local database: {explorer.stats['db_hits']} positions matched, "
            f"{explorer.stats['db_misses']} not found")
    else:
        log(f"Explorer: {explorer.stats['api_calls']} API calls, {explorer.stats['cache_hits']} cache hits, "
            f"{explorer.stats['errors']} errors")

    # ---- Engine pass ----
    # Precomputed evaluations first: opening positions are the most analysed positions there
    # are, so a public dataset answers most of this at depths worth far more than anything
    # affordable on demand. The engine only handles what is left.
    evals: dict[tuple[str, str], PositionEval] = {}
    store = open_store(eval_store_path) if not no_evals else None
    if store is not None:
        for key, node in repeated.items():
            found = store.evaluate_move(node.fen, node.played_uci)
            if found is not None:
                evals[key] = found
        deepest = max((e.depth for e in evals.values()), default=0)
        log(f"Precomputed evaluations: {len(evals)}/{len(repeated)} positions answered from "
            f"{os.path.basename(store.path)}, deepest {deepest} ply")
        store.close()

    remaining = {k: n for k, n in repeated.items() if k not in evals}
    if not no_engine and remaining:
        with EngineAnalyzer(
            engine_path=engine_path,
            depth=depth,
            movetime_ms=movetime_ms,
            multipv=multipv,
            threads=threads,
            cache_path=os.path.join(cache_dir, "engine_evals.json"),
        ) as eng:
            log(f"Engine: {eng.engine_path} (depth {depth}, MultiPV {multipv}) "
                f"for the remaining {len(remaining)} positions")
            engine_started = time.monotonic()
            for i, (key, node) in enumerate(remaining.items(), start=1):
                if engine_budget_s is not None and time.monotonic() - engine_started > engine_budget_s:
                    skipped = len(remaining) - i + 1
                    notes.append(f"engine budget of {engine_budget_s:g}s reached: "
                                 f"{skipped} of {len(remaining)} positions judged on statistics only")
                    log(f"  engine budget reached, skipping {skipped} positions")
                    break
                evals[key] = eng.evaluate_move(node.fen, node.played_uci)
                if i % 20 == 0:
                    log(f"  engine: {i}/{len(remaining)} positions")
                    eng.flush()

    # ---- Rows ----
    # What the player has already decided about these positions. A choice they have made
    # deliberately should not be re-argued every run.
    marks = {} if no_marks else load_marks(marks_path)
    if marks:
        log(f"Repertoire decisions on file: {len(marks)}")
    suppressed = 0
    rows: list[dict] = []
    for key, node in repeated.items():
        stats = pos_stats.get(node.epd)
        if stats is not None and stats.games == 0:
            stats = None  # position unknown to the database: leave its columns blank
        mv = stats.move(node.played_uci) if stats else None
        db_move_score = mv.score_for(node.player_color) if mv else None
        db_pos_score = stats.score_for(node.player_color) if stats else None

        # The comparison the player is held to. A book move needs a real sample behind it
        # before its own record counts, and is shrunk toward the position average even then.
        base = (
            stats.baseline_for(
                node.played_uci,
                node.player_color,
                min_move_games=min_db_move_games,
                prior_games=book_prior_games,
            )
            if stats
            else None
        )
        baseline, baseline_source, baseline_games = base if base else (None, "", 0)
        gap = (node.score - baseline) if baseline is not None else None
        ev = evals.get(key)

        # The player's own record is a small sample too. `your_hi` is the generous end of it.
        # Node counts are already from the player's point of view, so they need no colour
        # mapping — "white" here just means "score the first column".
        interval = score_interval(node.wins, node.draws, node.losses, "white", z=confidence_z)
        _, your_lo, your_hi = interval if interval else (node.score, node.score, node.score)

        flags = []
        if flags_winrate_decline(your_hi, baseline, gap, score_gap_threshold):
            flags.append("WINRATE_DECLINE")
        if ev and ev.eval_drop_pawns >= eval_drop_threshold:
            flags.append("EVAL_DROP")
        if mv and stats:
            pop = stats.popularity(node.played_uci)
            if pop is not None and pop < 0.02 and (gap is None or gap < 0):
                flags.append("OFFBEAT_MOVE")
        if not flags:
            continue

        mark = marks.get((node.epd, node.player_color))
        surviving = filter_flags(flags, mark, node.played_uci)
        if surviving is None:
            suppressed += 1
            continue
        committed = mark is not None and mark.uci == node.played_uci and mark.decision == "committed"
        flags = surviving

        lost_points = round(-gap * node.n, 2) if gap is not None and gap < 0 else 0.0
        # What is lost even on the most generous reading of the player's record. Ranking on
        # this rather than the observed figure sinks thin evidence without hiding it.
        lost_conservative = (
            round(max(0.0, baseline - your_hi) * node.n, 2) if baseline is not None else 0.0
        )
        priority = round(lost_conservative + (ev.eval_drop_pawns * node.n * 0.25 if ev else 0.0), 2)

        alt_cells: dict[str, str] = {}
        for i in range(3):
            alt = ev.alternatives[i] if ev and i < len(ev.alternatives) else None
            alt_db = stats.move(alt.uci) if (alt and stats) else None
            alt_cells[f"engine_best_{i+1}"] = alt.san if alt else ""
            if i == 0:
                alt_cells["engine_best_1_uci"] = alt.uci if alt else ""
            alt_cells[f"engine_best_{i+1}_cp"] = alt.cp if alt else ""
            alt_cells[f"engine_best_{i+1}_db_score_pct"] = (
                _pct(alt_db.score_for(node.player_color)) if alt_db else ""
            )

        confidence = confidence_label(node.n, baseline_games, baseline_source)
        category = classify(flags, confidence, ev.eval_drop_pawns if ev else 0.0,
                            eval_drop_threshold)
        consequence = describe_consequence(
            node.fen, node.played_uci, ev.refutation_uci if ev else ""
        )
        explanation = explain(
            node, baseline, baseline_source, baseline_games, ev,
            alt_cells.get("engine_best_1", ""), confidence, committed=committed,
        )

        rows.append({
            "priority": priority,
            "flag": "+".join(flags),
            "eco": (stats.eco if stats and stats.eco else node.eco),
            "opening": (stats.name if stats and stats.name else node.opening),
            "variation_line": node.line_san,
            "move_number": node.move_number,
            "ply": node.ply,
            "player_color": node.player_color,
            "your_move": node.played_san,
            "your_move_uci": node.played_uci,
            "fen": node.fen,
            "your_games": node.n,
            "your_wins": node.wins,
            "your_draws": node.draws,
            "your_losses": node.losses,
            "your_score_pct": _pct(node.score),
            "your_score_lo_pct": _pct(your_lo),
            "your_score_hi_pct": _pct(your_hi),
            "confidence": confidence,
            "category": category,
            "category_label": CATEGORIES[category][0],
            "committed": "yes" if committed else "",
            "explanation": explanation,
            "consequence": consequence,
            "refutation": ev.refutation_san if ev else "",
            "baseline_pct": _pct(baseline),
            "baseline_source": baseline_source,
            "baseline_games": baseline_games or "",
            "baseline_band": stats.band if stats else "",
            "db_move_games": mv.games if mv else "",
            "db_move_score_pct": _pct(db_move_score),
            "db_move_popularity_pct": _pct(stats.popularity(node.played_uci)) if stats else "",
            "db_position_games": stats.games if stats else "",
            "db_position_score_pct": _pct(db_pos_score),
            "score_gap_vs_db_pct": ("" if gap is None else f"{100 * gap:+.1f}"),
            "lost_points": lost_points,
            "lost_points_conservative": lost_conservative,
            "eval_before_cp": ev.best_cp if ev else "",
            "eval_after_cp": ev.played_cp if ev else "",
            "eval_drop_pawns": ev.eval_drop_pawns if ev else "",
            "engine_rank_of_your_move": (ev.played_rank if ev and ev.played_rank else (">%d" % multipv) if ev else ""),
            "sample_games": "; ".join(node.games),
            **alt_cells,
        })

    rows.sort(key=lambda r: (-float(r["priority"]), r["ply"]))
    report_path = os.path.join(out_dir, "opening_leaks.csv")
    with open(report_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=REPORT_FIELDS)
        w.writeheader()
        w.writerows(rows)

    # ---- Variation rollup ----
    roll: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    for node in nodes.values():
        k = (node.eco, node.opening or "(unknown)")
        roll[k][0] += node.wins
        roll[k][1] += node.draws
        roll[k][2] += node.losses
    summary_path = os.path.join(out_dir, "variation_summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["eco", "opening", "decisions", "wins", "draws", "losses", "score_pct"])
        for (eco, opening), (win, draw, loss) in sorted(
            roll.items(), key=lambda kv: -(sum(kv[1]))
        ):
            n = win + draw + loss
            w.writerow([eco, opening, n, win, draw, loss, f"{100 * (win + 0.5 * draw) / n:.1f}"])

    if suppressed:
        log(f"{suppressed} finding(s) held back by your own repertoire decisions")
    log(f"Wrote {len(rows)} flagged rows -> {report_path}")
    log(f"Wrote variation rollup -> {summary_path}")

    # ---- Coverage: likely replies the player has barely met ----
    # Needs a book that can be walked position by position, which the local database can do
    # and the online Explorer cannot without a request per node.
    coverage: list[dict] = []
    if db == "local" and not coverage_off:
        for side in (["white", "black"] if color == "both" else [color]):
            found = find_gaps(explorer, nodes, side, max_plies=max_moves * 2,
                              min_reach=coverage_min_reach)
            coverage.extend(found)
            log(f"Coverage ({side}): {len(found)} likely replies you have barely faced")
        coverage.sort(key=lambda g: (-g["reach_pct"], g["times_faced"]))
        # Each gap carries the move the player should meet it with, so "Practice" has
        # something to grade against — a position they have never faced has no move of
        # their own to compare. Looked up here, once, rather than per click.
        for gap in coverage:
            answer = best_reply(explorer.lookup_epd(" ".join(gap["fen"].split()[:4])),
                                gap["player_color"])
            if answer:
                gap["answer_uci"] = answer["uci"]
                gap["answer_san"] = answer["san"]
                gap["answer_score_pct"] = answer["score_pct"]
                gap["answer_games"] = answer["games"]
        # The player's own decisions are a view over the ranking, not a change to it: the
        # walk keeps producing the honest list and this drops what they have dismissed.
        before = len(coverage)
        coverage = apply_gap_decisions(coverage, {} if no_marks else load_gap_decisions(marks_path))
        if before != len(coverage):
            log(f"Coverage: {before - len(coverage)} gaps hidden by your own decisions")
        coverage_path = os.path.join(out_dir, "repertoire_coverage.csv")
        with open(coverage_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COVERAGE_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(coverage)
        log(f"Wrote coverage report -> {coverage_path}")

    # ---- The repertoire as a picture ----
    # Every decision already carries the line that reached it, so the tree is the trie of
    # those lines. Marks and flags colour it in.
    flagged = {(r["fen"], r["your_move_uci"]) for r in rows}
    leak_keys = {(node.epd, node.played_uci) for node in repeated.values()
                 if (node.fen, node.played_uci) in flagged}
    tree = {
        side: build_tree(nodes, side, leak_keys=leak_keys, marks=marks, gaps=coverage)
        for side in (["white", "black"] if color == "both" else [color])
    }
    totals = {side: tree_totals(branch) for side, branch in tree.items()}
    for side, counts in totals.items():
        if counts["strong"] or counts["weak"]:
            log(f"Repertoire as {side}: {counts['strong']} strong, {counts['weak']} weak, "
                f"{counts['committed']} committed, {counts['gaps']} gaps")

    return {
        "tree": tree,
        "tree_totals": totals,
        "coverage": coverage,
        "games": len(games),
        "nodes": len(nodes),
        "repeated": len(repeated),
        "rows": len(rows),
        "report": report_path,
        "summary": summary_path,
        "explorer_stats": explorer.stats,
        "suppressed_by_marks": suppressed,
        # Who the player was actually measured against, so the dashboard can say it plainly
        # rather than leaving "the book scores 54%" to mean whatever the reader assumes.
        "player_rating": player_rating,
        "player_band": player_band if banded else ALL,
        "player_band_label": band_label(player_band if banded else ALL),
        "book_has_bands": bool(banded),
        "notes": notes,
    }
