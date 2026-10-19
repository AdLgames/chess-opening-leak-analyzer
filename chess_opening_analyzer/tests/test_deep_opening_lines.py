"""Pinned source coverage, legal replay and exact-position fork integrity."""

from pathlib import Path
import csv
import hashlib
import json
import chess
import pytest
from tools.build_opening_lines import build, shard, SOURCE, OUT


def test_entire_pinned_source_rebuilds_exactly_and_every_fork_replays(tmp_path):
    info = build(out=tmp_path)
    assert info["count"] == 3865 and info["ecoCodes"] == 500
    assert info["maxPlies"] == 36 and info["positions"] == 7983
    assert {l["eco"] for l in info["lines"]} == {
        f"{letter}{n:02d}" for letter in "ABCDE" for n in range(100)
    }
    assert {p.name for p in tmp_path.iterdir()} == {p.name for p in OUT.iterdir()}
    for p in tmp_path.iterdir():
        assert p.read_bytes() == (OUT / p.name).read_bytes(), p.name
    forks = {
        k: v
        for p in tmp_path.glob("forks-*.json")
        for k, v in json.loads(p.read_text()).items()
    }
    ids = {l["id"] for l in info["lines"]}
    endpoints = {}
    encounters = {}
    for p in tmp_path.glob("[ABCDE][0-9][0-9].json"):
        for line in json.loads(p.read_text())["lines"]:
            b = chess.Board()
            assert len(line["san"]) == len(line["uci"])
            for san, uci in zip(line["san"], line["uci"]):
                move = b.parse_san(san)
                assert move.uci() == uci
                node = forks[b.epd()]
                branch = next(m for m in node["moves"] if m["uci"] == uci)
                assert line["id"] in branch["routes"]
                assert branch["san"] == b.san(move)
                encounters.setdefault(b.epd(), set()).add(
                    tuple(m.uci() for m in b.move_stack)
                )
                b.push(move)
            assert line["id"] in forks[b.epd()]["names"]
            endpoints[line["id"]] = b.epd()
    assert set(endpoints) == ids
    # Real move-order transpositions have merged, not just duplicate SAN prefixes.
    assert sum(len(paths) > 1 for paths in encounters.values()) > 100
    for epd, node in forks.items():
        assert epd in json.loads((tmp_path / f"forks-{shard(epd)}.json").read_text())
        b = chess.Board(epd)
        assert len({m["uci"] for m in node["moves"]}) == len(node["moves"])
        for m in node["moves"]:
            assert b.parse_san(m["san"]).uci() == m["uci"]
            assert set(m["routes"]) <= ids


def test_source_manifest_rejects_unverified_changes(tmp_path):
    import shutil

    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    (source / "a.tsv").write_text((source / "a.tsv").read_text() + "\n")
    with pytest.raises(AssertionError):
        build(source, tmp_path / "out")


@pytest.mark.parametrize("banded", [False, True])
def test_book_keeps_all_replies_and_full_frequency_denominator(tmp_path, banded):
    import sqlite3
    from chessopening.localdb import LocalOpeningDatabase, SCHEMA

    path = tmp_path / "book.sqlite"
    con = sqlite3.connect(path)
    if banded:
        con.executescript(SCHEMA)
    else:
        con.executescript(
            "CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE openings(pos TEXT PRIMARY KEY,eco TEXT,name TEXT); CREATE TABLE moves(pos TEXT,uci TEXT,san TEXT,white INT,draws INT,black INT,rating_sum INT);"
        )
    # Kiwipete has more than 40 legal replies, including castling.
    b = chess.Board(
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    )
    moves = list(b.legal_moves)
    assert len(moves) > 40
    for i, m in enumerate(moves):
        if banded:
            con.execute(
                "INSERT INTO moves VALUES(?,?,?,?,?,?,?,?)",
                (b.epd(), m.uci(), "all", b.san(m), i + 1, 1, 1, 0),
            )
        else:
            con.execute(
                "INSERT INTO moves VALUES(?,?,?,?,?,?,?)",
                (b.epd(), m.uci(), b.san(m), i + 1, 1, 1, 0),
            )
    con.commit()
    con.close()
    db = LocalOpeningDatabase(str(path))
    try:
        stats = db.lookup_epd(b.epd())
        assert len(stats.moves) == len(moves)
        assert stats.games == sum(i + 3 for i in range(len(moves)))
    finally:
        db.close()
