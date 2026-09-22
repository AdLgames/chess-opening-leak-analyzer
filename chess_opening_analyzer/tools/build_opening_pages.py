#!/usr/bin/env python3
"""Generate one page per opening the book can actually say something about.

    python tools/build_opening_pages.py --out ../chess-dashboard/public

The site is one tool and one front page, which can rank for a handful of terms
and no more. The book already holds what a player searching "why do I keep
losing the French Advance" wants: how the position scores, which replies people
choose, and which of those choices quietly do worse than the main line.

The threshold is the whole design. Emitting a page for every one of the 3,800
named openings would mean hundreds of pages built on a dozen games each —
mass-produced pages with nothing to say, which is what search engines penalise
and what a reader resents. A page is only written when the book has enough
games behind the position to make its numbers mean something, so the count
rises as the book grows rather than being padded to look bigger.
"""
from __future__ import annotations

import argparse
import csv
import html
import os
import re
import sqlite3
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)

# The paths are spelled out rather than imported. Importing `chessopening`
# pulls in the engine module and so python-chess, and this tool runs as part of
# the deployment's build command, where only the standard library is there.
DEFAULT_DB = os.path.join(PKG, "chessopening", "data", "openings.sqlite")
ECO_TSV = os.path.join(PKG, "chessopening", "data", "eco.tsv")
SITE = "https://chessleaklab.co.uk"

#: Minimum games behind a position before it gets a page of its own.
MIN_GAMES = 400
#: A reply needs this many games before it is worth naming in the table.
MIN_REPLY_GAMES = 25
#: And a page needs this many nameable replies to be worth writing at all.
MIN_REPLIES = 3
#: How far below the position's own score a reply has to sit before it is
#: called out. Three points is roughly the noise floor at these sample sizes.
UNDER_BY = 0.03


@dataclass
class Reply:
    san: str
    games: int
    share: float
    score: float
    under: bool


@dataclass
class Opening:
    eco: str
    name: str
    moves: str          # "1. e4 e6 2. d4 d5 3. e5"
    slug: str
    mover: str          # whose move it is in this position
    games: int
    score: float
    replies: list[Reply] = field(default_factory=list)

    @property
    def worst(self) -> Reply | None:
        """The most-played reply that does worse than the position as a whole."""
        under = [r for r in self.replies if r.under]
        return max(under, key=lambda r: r.games) if under else None


def slugify(eco: str, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{base}-{eco.lower()}"[:90]


def read_eco() -> list[tuple[str, str, str]]:
    with open(ECO_TSV, encoding="utf-8") as fh:
        return [(r["eco"], r["name"], r["pgn"]) for r in csv.DictReader(fh, delimiter="\t")]


def collect(db_path: str) -> list[Opening]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    banded = "band" in [r[1] for r in con.execute("PRAGMA table_info(moves)")]

    # The book's own `openings` table already maps each named line to the
    # position it reaches — build_local_db did that replay when it was built.
    # Joining on (eco, name) to recover the moves keeps this tool free of
    # python-chess, which matters: it runs as part of the deployment's build
    # command, where the analyser's dependencies are not installed.
    moves_for = {(eco, name): pgn for eco, name, pgn in read_eco()}

    out: dict[str, Opening] = {}
    for row in con.execute("SELECT pos, eco, name FROM openings"):
        pos, eco, name = row["pos"], row["eco"], row["name"]
        pgn_moves = moves_for.get((eco, name))
        if not pgn_moves:
            continue
        # Whose move it is, straight from the EPD's side-to-move field.
        parts = pos.split()
        mover = "white" if len(parts) > 1 and parts[1] == "w" else "black"
        rows = con.execute(
            "SELECT san, white, draws, black FROM moves WHERE pos = ?"
            + (" AND band = 'all'" if banded else ""), (pos,)).fetchall()
        total = sum(r["white"] + r["draws"] + r["black"] for r in rows)
        if total < MIN_GAMES:
            continue

        def scored(row) -> float:
            n = row["white"] + row["draws"] + row["black"]
            wins = row["white"] if mover == "white" else row["black"]
            return (wins + 0.5 * row["draws"]) / n if n else 0.0

        baseline = sum(
            (r["white"] if mover == "white" else r["black"]) + 0.5 * r["draws"] for r in rows
        ) / total
        replies = [
            Reply(r["san"], r["white"] + r["draws"] + r["black"],
                  (r["white"] + r["draws"] + r["black"]) / total, scored(r),
                  scored(r) < baseline - UNDER_BY)
            for r in rows if r["white"] + r["draws"] + r["black"] >= MIN_REPLY_GAMES
        ]
        if len(replies) < MIN_REPLIES:
            continue
        replies.sort(key=lambda r: -r.games)

        opening = Opening(eco=eco, name=name, moves=pgn_moves.strip(),
                          slug=slugify(eco, name), mover=mover, games=total,
                          score=baseline, replies=replies)
        # eco.tsv names several lines into the same position. Keep the shortest
        # name: that is the canonical one and the one people search for. The
        # longest is some deep sub-variation nobody types into a search box.
        prior = out.get(pos)
        if prior is None or len(opening.name) < len(prior.name):
            out[pos] = opening
    con.close()

    # Two different positions can carry the same ECO and name — a transposition,
    # or a name that covers a family. They would land on the same URL, so one
    # page silently overwrote the other and the sitemap listed it twice. Keep
    # the position with more games behind it: two pages under one name would be
    # competing with each other for the same search anyway.
    best: dict[str, Opening] = {}
    for opening in out.values():
        rival = best.get(opening.slug)
        if rival is None or opening.games > rival.games:
            best[opening.slug] = opening
    return sorted(best.values(), key=lambda o: -o.games)


# ------------------------------------------------------------------ rendering
def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def sentence(o: Opening) -> str:
    """The finding, in a line, for the meta description and the page lead."""
    side = "White" if o.mover == "white" else "Black"
    worst = o.worst
    if not worst:
        return (f"{side} scores {pct(o.score)} here across {o.games:,} club games, and no "
                "common reply does noticeably worse than the rest.")
    gap = o.score - worst.score
    return (f"{side} scores {pct(o.score)} here across {o.games:,} club games — but the "
            f"{pct(worst.share)} who answer {worst.san} score {pct(worst.score)}, "
            f"{100 * gap:.0f} points worse.")


def page(o: Opening, siblings: list[Opening]) -> str:
    side = "White" if o.mover == "white" else "Black"
    lead = sentence(o)
    # Google shows about sixty characters. The name has to survive; the framing
    # is what gets dropped when it does not fit.
    stem = f"{o.name} ({o.eco})"
    title = f"{stem}: what club players get wrong"
    if len(title) > 60:
        title = f"{stem}: common mistakes"
    if len(title) > 60:
        title = stem[:60].rstrip(" ,:-")
    meta = lead if len(lead) <= 155 else lead[:152].rsplit(" ", 1)[0] + "…"

    rows = "".join(
        f"""        <tr class="{'is-under' if r.under else ''}">
          <td class="mono">{esc(r.san)}</td>
          <td class="num">{r.games:,}</td>
          <td class="num">{pct(r.share)}</td>
          <td class="num">{pct(r.score)}</td>
          <td>{'below the line' if r.under else 'holds up'}</td>
        </tr>\n"""
        for r in o.replies[:12])

    related = "".join(
        f'<li><a href="/openings/{s.slug}/">{esc(s.name)}</a> <span class="muted">'
        f'{s.eco}</span></li>' for s in siblings[:6])

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#F8FAFC" />
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(meta)}" />
    <link rel="canonical" href="{SITE}/openings/{o.slug}/" />
    <link rel="stylesheet" href="/landing.css" />
    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="Opening Leak Lab" />
    <meta property="og:title" content="{esc(title)}" />
    <meta property="og:description" content="{esc(meta)}" />
    <meta property="og:url" content="{SITE}/openings/{o.slug}/" />
  </head>
  <body>
    <header class="site-head">
      <a class="wordmark" href="/">
        <span class="wordmark-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span>Opening Leak Lab</span>
      </a>
      <nav class="site-nav" aria-label="Sections">
        <a href="/openings/">All openings</a>
        <a class="nav-cta" href="/app/">Run my report</a>
      </nav>
    </header>

    <main class="doc-body shell">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="/">Home</a> › <a href="/openings/">Openings</a> ›
        <span>{esc(o.name)}</span>
      </nav>

      <h1>{esc(o.name)}</h1>
      <p class="doc-eco"><span class="eco">{esc(o.eco)}</span>
        <span class="mono">{esc(o.moves)}</span></p>
      <p class="doc-lead">{esc(lead)}</p>

      <h2>What {side} actually plays here</h2>
      <p>Across {o.games:,} games from a Lichess-derived book of club play,
        {side} scores {pct(o.score)} in this position. These are the replies
        people choose, and how each one works out.</p>
      <table class="doc-table">
        <thead><tr><th>Reply</th><th class="num">Games</th><th class="num">Share</th>
          <th class="num">{side} scores</th><th>Verdict</th></tr></thead>
        <tbody>
{rows}        </tbody>
      </table>
      <p class="muted small">"Below the line" means the reply scores at least three
        points worse than the position does overall. Replies played fewer than
        {MIN_REPLY_GAMES} times are left out: the sample is too small to read.</p>

      <h2>Is this costing you anything?</h2>
      <p>A table of averages cannot tell you whether <em>you</em> go wrong here — only
        your own games can. Opening Leak Lab reads your Chess.com or Lichess archive,
        finds the decisions you repeat, and checks each one against this book and a
        bundled Stockfish.</p>
      <p><a class="btn-solid" href="/app/">Analyse my games</a></p>

      {f'<h2>Related openings</h2><ul class="doc-links">{related}</ul>' if related else ''}
    </main>

    <footer class="site-foot">
      <div class="shell">
        <span>Opening statistics from a Lichess-derived book of club games (CC0).</span>
        <span><a href="/">Opening Leak Lab</a> · <a href="/app/">Run a report</a></span>
      </div>
    </footer>
  </body>
</html>
"""


def index_page(openings: list[Opening]) -> str:
    title = "Chess openings by the numbers | Opening Leak Lab"
    meta = (f"How {len(openings)} openings actually score in club play, and which "
            "popular replies quietly do worse than the main line.")
    groups: dict[str, list[Opening]] = {}
    for o in openings:
        groups.setdefault(o.eco[0], []).append(o)
    blocks = ""
    for letter in sorted(groups):
        items = "".join(
            f'<li><a href="/openings/{o.slug}/">{esc(o.name)}</a> '
            f'<span class="muted">{o.eco} · {o.games:,} games</span></li>'
            for o in sorted(groups[letter], key=lambda o: o.name))
        blocks += f'<section><h2>ECO {letter}</h2><ul class="doc-links">{items}</ul></section>'

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#F8FAFC" />
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(meta)}" />
    <link rel="canonical" href="{SITE}/openings/" />
    <link rel="stylesheet" href="/landing.css" />
  </head>
  <body>
    <header class="site-head">
      <a class="wordmark" href="/">
        <span class="wordmark-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span>Opening Leak Lab</span>
      </a>
      <nav class="site-nav" aria-label="Sections">
        <a class="nav-cta" href="/app/">Run my report</a>
      </nav>
    </header>
    <main class="doc-body shell">
      <h1>Openings by the numbers</h1>
      <p class="doc-lead">{esc(meta)} Only positions with at least
        {MIN_GAMES:,} games behind them are listed — below that the numbers are noise.</p>
      {blocks}
    </main>
    <footer class="site-foot">
      <div class="shell">
        <span>Opening statistics from a Lichess-derived book of club games (CC0).</span>
        <span><a href="/">Opening Leak Lab</a> · <a href="/app/">Run a report</a></span>
      </div>
    </footer>
  </body>
</html>
"""


def sitemap(openings: list[Opening]) -> str:
    urls = [(f"{SITE}/", "weekly", "1.0"), (f"{SITE}/app/", "weekly", "0.8"),
            (f"{SITE}/openings/", "weekly", "0.7")]
    urls += [(f"{SITE}/openings/{o.slug}/", "monthly", "0.6") for o in openings]
    body = "".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{pri}</priority>\n  </url>\n" for loc, freq, pri in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}</urlset>\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(PKG), "chess-dashboard", "public"))
    ap.add_argument("--min-games", type=int, default=MIN_GAMES)
    args = ap.parse_args()

    globals()["MIN_GAMES"] = args.min_games   # the tool's one knob
    openings = collect(args.db)
    if not openings:
        print("no opening has enough games behind it — is the book a Git LFS pointer?")
        return 1

    root = os.path.join(args.out, "openings")
    os.makedirs(root, exist_ok=True)
    by_eco: dict[str, list[Opening]] = {}
    for o in openings:
        by_eco.setdefault(o.eco, []).append(o)

    for o in openings:
        siblings = [s for s in by_eco.get(o.eco, []) if s.slug != o.slug]
        folder = os.path.join(root, o.slug)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(page(o, siblings))

    with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_page(openings))
    with open(os.path.join(args.out, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(sitemap(openings))

    named = sum(1 for o in openings if o.worst)
    print(f"{len(openings)} opening pages -> {root}")
    print(f"  {named} have a reply that measurably underperforms; "
          f"{len(openings) - named} report no outlier")
    print(f"  sitemap lists {len(openings) + 3} URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
