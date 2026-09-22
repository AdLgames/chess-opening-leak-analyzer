"""The generated opening pages: enough data to be worth a page, and no duplicates.

Programmatic pages earn their place or become the thing search engines call
scaled content abuse. Two properties decide that, and both are testable: every
page is built on a sample large enough for its numbers to mean something, and
no two pages compete for the same URL or the same name.

Runs on the standard library, like the generator itself — it is a build step,
not part of the analyser.
"""
from __future__ import annotations

import html
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_opening_pages as gen  # noqa: E402


def book(path, openings, moves):
    """A miniature book: (eco, name, pos) plus (pos, san, w/d/l) rows."""
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE openings (pos TEXT, eco TEXT, name TEXT);
        CREATE TABLE moves (pos TEXT, uci TEXT, san TEXT, white INT, draws INT,
                            black INT, rating_sum INT);
    """)
    con.executemany("INSERT INTO openings VALUES (?, ?, ?)", openings)
    con.executemany("INSERT INTO moves VALUES (?, ?, ?, ?, ?, ?, 1700)", moves)
    con.commit(); con.close()
    return str(path)


WHITE_TO_MOVE = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"
ALSO_WHITE = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -"


def test_a_thin_position_gets_no_page(tmp_path, monkeypatch):
    """Below the threshold the numbers are noise, and a page would be filler."""
    monkeypatch.setattr(gen, "read_eco", lambda: [("C20", "King's Pawn Game", "1. e4")])
    path = book(tmp_path / "thin.sqlite",
                [(WHITE_TO_MOVE, "C20", "King's Pawn Game")],
                [(WHITE_TO_MOVE, "e2e4", "e4", 30, 10, 30),
                 (WHITE_TO_MOVE, "d2d4", "d4", 20, 5, 20),
                 (WHITE_TO_MOVE, "g1f3", "Nf3", 10, 5, 10)])
    assert gen.collect(path) == []


def test_a_well_sampled_position_gets_one(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "read_eco", lambda: [("C20", "King's Pawn Game", "1. e4")])
    path = book(tmp_path / "ok.sqlite",
                [(WHITE_TO_MOVE, "C20", "King's Pawn Game")],
                [(WHITE_TO_MOVE, "e2e4", "e4", 200, 50, 150),
                 (WHITE_TO_MOVE, "d2d4", "d4", 100, 40, 100),
                 (WHITE_TO_MOVE, "g1f3", "Nf3", 20, 10, 90)])
    found = gen.collect(path)
    assert len(found) == 1
    assert found[0].games == 760 and found[0].mover == "white"
    worst = found[0].worst
    assert worst is not None and worst.san == "Nf3", "the losing reply was not identified"


def test_replies_too_rare_to_read_are_left_out(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "read_eco", lambda: [("C20", "King's Pawn Game", "1. e4")])
    path = book(tmp_path / "rare.sqlite",
                [(WHITE_TO_MOVE, "C20", "King's Pawn Game")],
                [(WHITE_TO_MOVE, "e2e4", "e4", 200, 50, 150),
                 (WHITE_TO_MOVE, "d2d4", "d4", 100, 40, 100),
                 (WHITE_TO_MOVE, "g1f3", "Nf3", 20, 10, 90),
                 (WHITE_TO_MOVE, "b1c3", "Nc3", 1, 0, 1)])
    assert "Nc3" not in [r.san for r in gen.collect(path)[0].replies]


def test_two_positions_never_share_a_url(tmp_path, monkeypatch):
    """The same ECO and name can name two positions. One page, not one overwriting
    the other and a sitemap listing it twice."""
    monkeypatch.setattr(gen, "read_eco", lambda: [("C20", "King's Pawn Game", "1. e4")])
    path = book(tmp_path / "dupe.sqlite",
                [(WHITE_TO_MOVE, "C20", "King's Pawn Game"),
                 (ALSO_WHITE, "C20", "King's Pawn Game")],
                [(WHITE_TO_MOVE, "e2e4", "e4", 200, 50, 150),
                 (WHITE_TO_MOVE, "d2d4", "d4", 100, 40, 100),
                 (WHITE_TO_MOVE, "g1f3", "Nf3", 40, 10, 40),
                 (ALSO_WHITE, "e2e4", "e4", 900, 50, 150),
                 (ALSO_WHITE, "d2d4", "d4", 100, 40, 100),
                 (ALSO_WHITE, "g1f3", "Nf3", 40, 10, 40)])
    found = gen.collect(path)
    assert len({o.slug for o in found}) == len(found)
    assert len(found) == 1
    assert found[0].games == 1430, "the busier of the two positions should win"


def test_the_page_says_what_the_numbers_are(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "read_eco", lambda: [("C20", "King's Pawn Game", "1. e4")])
    path = book(tmp_path / "page.sqlite",
                [(WHITE_TO_MOVE, "C20", "King's Pawn Game")],
                [(WHITE_TO_MOVE, "e2e4", "e4", 200, 50, 150),
                 (WHITE_TO_MOVE, "d2d4", "d4", 100, 40, 100),
                 (WHITE_TO_MOVE, "g1f3", "Nf3", 20, 10, 90)])
    o = gen.collect(path)[0]
    markup = gen.page(o, [])
    assert "1. e4" in markup
    assert "760" in markup.replace(",", "")
    assert 'href="/app/"' in markup, "every page has to lead somewhere"
    assert 'rel="canonical"' in markup

    title = html.unescape(re.search(r"<title>(.*?)</title>", markup).group(1))
    desc = html.unescape(re.search(r'name="description" content="(.*?)"', markup).group(1))
    assert len(title) <= 60, f"{len(title)}: {title}"
    assert len(desc) <= 155, f"{len(desc)}: {desc}"


def test_the_sitemap_lists_every_page_once(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "read_eco", lambda: [("C20", "King's Pawn Game", "1. e4")])
    path = book(tmp_path / "map.sqlite",
                [(WHITE_TO_MOVE, "C20", "King's Pawn Game")],
                [(WHITE_TO_MOVE, "e2e4", "e4", 200, 50, 150),
                 (WHITE_TO_MOVE, "d2d4", "d4", 100, 40, 100),
                 (WHITE_TO_MOVE, "g1f3", "Nf3", 20, 10, 90)])
    found = gen.collect(path)
    xml = gen.sitemap(found)
    locs = re.findall(r"<loc>(.*?)</loc>", xml)
    assert len(locs) == len(set(locs))
    assert f"{gen.SITE}/openings/{found[0].slug}/" in locs
    assert f"{gen.SITE}/" in locs and f"{gen.SITE}/app/" in locs
