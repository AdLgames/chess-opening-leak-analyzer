"""Aggregate PGN opening decisions, cross-reference Lichess stats, add engine verdicts, write CSVs."""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass, field

from .engine import EngineAnalyzer, PositionEval
from .explorer import OpeningExplorer, PositionStats
from .localdb import DEFAULT_DB, LocalOpeningDatabase
from .pgn_loader import GameSummary, PlyRecord, load_games


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
    "fen",
    "your_games",
    "your_wins",
    "your_draws",
    "your_losses",
    "your_score_pct",
    "db_move_games",
    "db_move_score_pct",
    "db_move_popularity_pct",
    "db_position_games",
    "db_position_score_pct",
    "score_gap_vs_db_pct",
    "lost_points",
    "eval_before_cp",
    "eval_after_cp",
    "eval_drop_pawns",
    "engine_rank_of_your_move",
    "engine_best_1",
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
) -> tuple[dict[tuple[str, str], Node], list[GameSummary]]:
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
    return nodes, games


def _pct(x: float | None) -> str:
    return "" if x is None else f"{100 * x:.1f}"


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
    db: str = "lichess",
    local_db_path: str = DEFAULT_DB,
    min_db_games: int = 0,
    speeds: str = "blitz,rapid,classical",
    ratings: str = "1600,1800,2000",
    offline: bool = False,
    no_engine: bool = False,
    cache_dir: str | None = None,
    log=print,
) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    cache_dir = cache_dir or os.path.join(out_dir, ".cache")
    nodes, games = build_nodes(pgn_dir, player, max_moves=max_moves, color=color)
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
    pos_stats: dict[str, PositionStats] = {}
    for i, node in enumerate(repeated.values(), start=1):
        parent = ",".join(node.line_uci.split(",")[:-1])  # position BEFORE the player's move
        if node.epd not in pos_stats:
            pos_stats[node.epd] = explorer.lookup(parent)
        if i % 25 == 0:
            log(f"  opening db: {i}/{len(repeated)} positions looked up")
    if db == "local":
        log(f"Local database: {explorer.stats['db_hits']} positions matched, "
            f"{explorer.stats['db_misses']} not found")
    else:
        log(f"Explorer: {explorer.stats['api_calls']} API calls, {explorer.stats['cache_hits']} cache hits, "
            f"{explorer.stats['errors']} errors")

    # ---- Engine pass ----
    evals: dict[tuple[str, str], PositionEval] = {}
    if not no_engine:
        with EngineAnalyzer(
            engine_path=engine_path,
            depth=depth,
            movetime_ms=movetime_ms,
            multipv=multipv,
            threads=threads,
            cache_path=os.path.join(cache_dir, "engine_evals.json"),
        ) as eng:
            log(f"Engine: {eng.engine_path} (depth {depth}, MultiPV {multipv})")
            for i, (key, node) in enumerate(repeated.items(), start=1):
                evals[key] = eng.evaluate_move(node.fen, node.played_uci)
                if i % 20 == 0:
                    log(f"  engine: {i}/{len(repeated)} positions")
                    eng.flush()

    # ---- Rows ----
    rows: list[dict] = []
    for key, node in repeated.items():
        stats = pos_stats.get(node.epd)
        if stats is not None and stats.games == 0:
            stats = None  # position unknown to the database: leave its columns blank
        mv = stats.move(node.played_uci) if stats else None
        db_move_score = mv.score_for(node.player_color) if mv else None
        db_pos_score = stats.score_for(node.player_color) if stats else None
        baseline = db_move_score if db_move_score is not None else db_pos_score
        gap = (node.score - baseline) if baseline is not None else None
        ev = evals.get(key)

        flags = []
        if gap is not None and gap <= -score_gap_threshold:
            flags.append("WINRATE_DECLINE")
        if ev and ev.eval_drop_pawns >= eval_drop_threshold:
            flags.append("EVAL_DROP")
        if mv and stats:
            pop = stats.popularity(node.played_uci)
            if pop is not None and pop < 0.02 and (gap is None or gap < 0):
                flags.append("OFFBEAT_MOVE")
        if not flags:
            continue

        lost_points = round(-gap * node.n, 2) if gap is not None and gap < 0 else 0.0
        priority = round(lost_points + (ev.eval_drop_pawns * node.n * 0.25 if ev else 0.0), 2)

        alt_cells: dict[str, str] = {}
        for i in range(3):
            alt = ev.alternatives[i] if ev and i < len(ev.alternatives) else None
            alt_db = stats.move(alt.uci) if (alt and stats) else None
            alt_cells[f"engine_best_{i+1}"] = alt.san if alt else ""
            alt_cells[f"engine_best_{i+1}_cp"] = alt.cp if alt else ""
            alt_cells[f"engine_best_{i+1}_db_score_pct"] = (
                _pct(alt_db.score_for(node.player_color)) if alt_db else ""
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
            "fen": node.fen,
            "your_games": node.n,
            "your_wins": node.wins,
            "your_draws": node.draws,
            "your_losses": node.losses,
            "your_score_pct": _pct(node.score),
            "db_move_games": mv.games if mv else "",
            "db_move_score_pct": _pct(db_move_score),
            "db_move_popularity_pct": _pct(stats.popularity(node.played_uci)) if stats else "",
            "db_position_games": stats.games if stats else "",
            "db_position_score_pct": _pct(db_pos_score),
            "score_gap_vs_db_pct": ("" if gap is None else f"{100 * gap:+.1f}"),
            "lost_points": lost_points,
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

    log(f"Wrote {len(rows)} flagged rows -> {report_path}")
    log(f"Wrote variation rollup -> {summary_path}")
    return {
        "games": len(games),
        "nodes": len(nodes),
        "repeated": len(repeated),
        "rows": len(rows),
        "report": report_path,
        "summary": summary_path,
        "explorer_stats": explorer.stats,
    }
