"""Per-opening profiles: how this player does in each opening, and where it breaks.

The leak table answers "which moves cost me points". This answers the question
underneath it — "which openings am I bad at, and at what point do I go wrong" —
by folding the same run into one profile per opening family per colour:

* the player's own record in it, against what the book scores from the same
  positions,
* the move number their line stops holding, and the spread of where the leaks
  land,
* the answers to play instead, from the engine when the run had one and from the
  book otherwise.

Openings are grouped by *family* — "Sicilian Defense: Alapin, Barmen" counts as
Sicilian Defense — because a repertoire hole is a thing you have against a whole
opening, not against one leaf of the ECO tree. White and Black are kept apart:
meeting the Sicilian is a different skill from playing it.

Like traps.py this is a pure fold over data the pipeline has already produced,
so it needs neither an engine nor python-chess.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable, Iterable, Sequence

#: Book moves thinner than this are not worth recommending.
MIN_BOOK_GAMES = 20


def family(name: str) -> str:
    """The opening family: everything before the first variation marker."""
    head = str(name or "").split(":")[0].split(",")[0].strip()
    return head or "Unclassified"


def epd_of(fen: str) -> str:
    """The position key the rest of the pipeline uses: FEN without the clocks."""
    return " ".join(str(fen or "").split()[:4])


def _f(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _best_book_move(stats: Any, colour: str, exclude: str = "") -> tuple[str, float | None, int]:
    """The book's best-scoring move from a position, ignoring thin ones."""
    best: tuple[str, float | None, int] = ("", None, 0)
    for move in getattr(stats, "moves", []) or []:
        if move.san == exclude or move.games < MIN_BOOK_GAMES:
            continue
        score = move.score_for(colour)
        if score is None:
            continue
        if best[1] is None or score > best[1]:
            best = (move.san, score, move.games)
    return best


def _name_game(game: Any, name_for: Callable[[str], tuple[str, str] | None] | None) -> tuple[str, str]:
    """(eco, name) for a game: the deepest position the book can name, else its headers."""
    if name_for is not None:
        for rec in reversed(list(getattr(game, "plies", []) or [])):
            named = name_for(rec.epd_before)
            if named and named[1]:
                return named
    return (getattr(game, "eco", "") or "", getattr(game, "opening", "") or "")


def build_profiles(
    *,
    nodes: Iterable[Any],
    games: Iterable[Any],
    rows: Sequence[dict[str, Any]],
    pos_stats: dict[str, Any] | None = None,
    name_for: Callable[[str], tuple[str, str] | None] | None = None,
    traps: Sequence[dict[str, Any]] = (),
    limit: int = 40,
) -> dict[str, Any]:
    """One profile per (colour, opening family), plus the run-wide break-point spread."""
    pos_stats = pos_stats or {}
    profiles: dict[tuple[str, str], dict[str, Any]] = {}

    def profile(colour: str, name: str) -> dict[str, Any]:
        key = (colour, family(name))
        if key not in profiles:
            profiles[key] = {
                "key": f"{colour}:{family(name)}", "colour": colour, "family": family(name),
                "eco": "", "games": 0, "wins": 0, "draws": 0, "losses": 0,
                "score_pct": None, "book_score_pct": None, "gap_pct": None,
                "cost": 0.0, "leaks": [], "breaks": [], "first_break": None,
                "variants": Counter(), "_ecos": Counter(),
                "_book": [0.0, 0], "traps": [],
            }
        return profiles[key]

    # ---- the record: whole games, by the opening they actually reached
    for game in games:
        eco, name = _name_game(game, name_for)
        prof = profile(getattr(game, "player_color", ""), name)
        prof["games"] += 1
        if name:
            prof["variants"][name] += 1
        if eco:
            prof["_ecos"][eco] += 1
        score = _f(getattr(game, "player_score", None))
        if score == 1.0:
            prof["wins"] += 1
        elif score == 0.5:
            prof["draws"] += 1
        else:
            prof["losses"] += 1

    # ---- what the book scores from the positions this player keeps reaching
    for node in nodes:
        stats = pos_stats.get(getattr(node, "epd", ""))
        if stats is None or not getattr(stats, "games", 0):
            continue
        name = stats.name or getattr(node, "opening", "")
        prof = profile(getattr(node, "player_color", ""), name)
        expected = stats.score_for(node.player_color)
        if expected is not None:
            prof["_book"][0] += expected * node.n
            prof["_book"][1] += node.n

    # ---- the leaks, and what to play instead
    breaks: dict[int, dict[str, int]] = defaultdict(lambda: {"leaks": 0, "games": 0})
    for row in rows:
        colour = row.get("player_color", "")
        prof = profile(colour, row.get("opening") or row.get("eco") or "")
        stats = pos_stats.get(epd_of(row.get("fen", "")))
        instead = row.get("engine_best_1") or ""
        source = "engine" if instead else ""
        book_score = _f(row.get("engine_best_1_db_score_pct"))
        if not instead and stats is not None:
            instead, score, _n = _best_book_move(stats, colour, exclude=row.get("your_move", ""))
            source = "book" if instead else ""
            book_score = None if score is None else round(score * 100, 1)
        move_number = int(_f(row.get("move_number")) or 0)
        your_games = int(_f(row.get("your_games")) or 0)
        prof["cost"] += _f(row.get("cost")) or 0.0
        prof["leaks"].append({
            "move_number": move_number,
            "ply": int(_f(row.get("ply")) or 0),
            "your_move": row.get("your_move", ""),
            "line": row.get("variation_line", ""),
            "fen": row.get("fen", ""),
            "flag": row.get("flag", ""),
            "cost": _f(row.get("cost")) or 0.0,
            "games": your_games,
            "score_pct": _f(row.get("your_score_pct")),
            "book_score_pct": _f(row.get("db_move_score_pct")),
            "play_instead": instead,
            "instead_source": source,
            "instead_score_pct": book_score,
        })
        if move_number:
            breaks[move_number]["leaks"] += 1
            breaks[move_number]["games"] += your_games

    # ---- traps land on the profile of the opening they belong to
    for trap in traps:
        prof = profile(trap.get("victim", ""), trap.get("opening") or trap.get("name", ""))
        prof["traps"].append(trap.get("key"))

    out: list[dict[str, Any]] = []
    for prof in profiles.values():
        played, decided = prof["wins"] + prof["draws"] + prof["losses"], prof["_book"][1]
        prof["score_pct"] = round(100 * (prof["wins"] + 0.5 * prof["draws"]) / played, 1) if played else None
        prof["book_score_pct"] = round(100 * prof["_book"][0] / decided, 1) if decided else None
        if prof["score_pct"] is not None and prof["book_score_pct"] is not None:
            prof["gap_pct"] = round(prof["score_pct"] - prof["book_score_pct"], 1)
        prof["leaks"].sort(key=lambda leak: -leak["cost"])
        prof["cost"] = round(prof["cost"], 2)
        prof["first_break"] = min((leak["move_number"] for leak in prof["leaks"] if leak["move_number"]), default=None)
        spread: dict[int, int] = defaultdict(int)
        for leak in prof["leaks"]:
            spread[leak["move_number"]] += leak["games"]
        prof["breaks"] = [{"move_number": mv, "games": n} for mv, n in sorted(spread.items())]
        prof["name"] = prof["variants"].most_common(1)[0][0] if prof["variants"] else prof["family"]
        prof["eco"] = prof["_ecos"].most_common(1)[0][0] if prof["_ecos"] else ""
        prof.pop("variants")
        prof.pop("_ecos")
        prof.pop("_book")
        out.append(prof)

    # Openings worth showing: ones actually played, or ones that produced findings.
    out = [p for p in out if p["games"] or p["leaks"]]
    out.sort(key=lambda p: (-p["cost"], -(p["games"] or 0)))
    return {
        "openings": out[:limit],
        "break_moves": [{"move_number": mv, **counts} for mv, counts in sorted(breaks.items())],
        # only openings with enough games to mean something, worst first
        "worst_against": [p["key"] for p in sorted(out, key=_trouble) if _trouble(p)[0] < 0][:6],
    }


def _trouble(profile: dict[str, Any]) -> tuple[float, float]:
    """Rank for "gives you the most trouble": how far below the book, then how often."""
    gap = profile.get("gap_pct")
    games = profile.get("games") or 0
    if gap is None or games < 3:
        return (0.0, 0.0)          # not enough evidence to call it a weakness
    return (min(0.0, gap) * games, -profile.get("cost", 0.0))
