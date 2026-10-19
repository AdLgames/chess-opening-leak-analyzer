"""Build the complete pinned CC0 opening catalogue and lazy position forks.

No network at build time. Every source row and every move is validated.
"""

from __future__ import annotations
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "chess_opening_analyzer/content/openings"
OUT = ROOT / "chess-dashboard/public/app/opening-lines"


def shard(key):
    value = 2166136261
    for char in key:
        value = ((value ^ ord(char)) * 16777619) & 0xFFFFFFFF
    return f"{value%64:02x}"


def build(source=SOURCE, out=OUT):
    manifest = json.loads((source / "source.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    index = []
    packs = defaultdict(list)
    nodes = {}
    ids = set()
    for letter in "abcde":
        path = source / f"{letter}.tsv"
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest()
            == manifest["files"][path.name]["sha256"]
        )
        for row in csv.DictReader(path.open(), delimiter="\t"):
            eco, name, pgn = row["eco"], row["name"], row["pgn"]
            board = chess.Board()
            sans = []
            ucis = []
            path_nodes = []
            for token in pgn.split():
                if token.rstrip(".").isdigit():
                    continue
                move = board.parse_san(token)
                before = board.epd()
                san = board.san(move)
                uci = move.uci()
                path_nodes.append((before, uci, san))
                sans.append(san)
                ucis.append(uci)
                board.push(move)
            identifier = hashlib.sha256(
                (eco + "|" + name + "|" + " ".join(ucis)).encode()
            ).hexdigest()[:16]
            assert identifier not in ids
            ids.add(identifier)
            index.append(
                {
                    "id": identifier,
                    "eco": eco,
                    "name": name,
                    "moves": " ".join(sans),
                    "plies": len(sans),
                    "first": sans[0],
                }
            )
            packs[eco].append(
                {"id": identifier, "name": name, "eco": eco, "san": sans, "uci": ucis}
            )
            for key, uci, san in path_nodes:
                node = nodes.setdefault(key, {"moves": {}, "names": []})
                branch = node["moves"].setdefault(
                    uci, {"uci": uci, "san": san, "routes": set()}
                )
                branch["routes"].add(identifier)
            nodes.setdefault(board.epd(), {"moves": {}, "names": []})["names"].append(
                identifier
            )
    shards = defaultdict(dict)
    for key, node in nodes.items():
        shards[shard(key)][key] = {
            "moves": [
                dict(uci=m["uci"], san=m["san"], routes=sorted(m["routes"]))
                for m in sorted(
                    node["moves"].values(), key=lambda m: (-len(m["routes"]), m["san"])
                )
            ],
            "names": sorted(node["names"]),
        }

    def write(name, value):
        (out / name).write_text(
            json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
        )

    for eco, lines in packs.items():
        write(f"{eco}.json", {"eco": eco, "lines": lines})
    for key, entries in shards.items():
        write(f"forks-{key}.json", entries)
    for n in range(64):
        if f"{n:02x}" not in shards:
            write(f"forks-{n:02x}.json", {})
    info = {
        "version": 1,
        "source": manifest,
        "count": len(index),
        "ecoCodes": len(packs),
        "positions": len(nodes),
        "maxPlies": max(r["plies"] for r in index),
        "lines": index,
    }
    write("index.json", info)
    print(
        f"{len(index)} named routes; {len(packs)} ECO codes; {info['positions']} positions; longest {info['maxPlies']} plies"
    )
    return info


if __name__ == "__main__":
    build()
