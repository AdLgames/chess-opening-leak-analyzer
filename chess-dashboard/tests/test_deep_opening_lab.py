"""Deep route replay and personal review against the real chess API.

Only report/account fixtures are synthetic; moves, legality and contexts use Python chess.
"""

import json
import math
import re
from pathlib import Path
import chess
import pytest
from chessopening.summary import summarise
from chessopening.analyze import REPORT_FIELDS
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[2]
INDEX = json.loads(
    (ROOT / "chess-dashboard/public/app/opening-lines/index.json").read_text()
)
LONGEST = max(INDEX["lines"], key=lambda r: r["plies"])
BOOKMARK = "learning:v2:opening-lines-v1:bookmark:"
LAB = "learning:v2:decision-lab-v1:"


def ready(page, url, view="today"):
    page.goto(url + "/app/#" + view)
    page.wait_for_function("window.PlayerLab && Auth.state.ready")
    expect(page.locator("#libBoard")).to_have_attribute("aria-busy", "false")


def open_line(page, identifier=None):
    page.evaluate("(id)=>DeepLines.open(id)", identifier or LONGEST["id"])
    expect(page.locator("#branchesPane")).to_be_visible()
    expect(page.locator("#deepBoardPanel")).to_have_attribute("aria-busy", "false")


def assert_board(page, b):
    actual = page.locator("#libBoard .cb-sq").evaluate_all(
        "els=>Object.fromEntries(els.map(e=>[e.dataset.square,e.querySelector('.cb-piece').dataset.piece]).filter(([,p])=>p))"
    )
    assert actual == {
        chess.square_name(sq): piece.symbol() for sq, piece in b.piece_map().items()
    }
    if not page.evaluate("Training.active()"):
        assert page.evaluate("Study.snapshot().pos.fen") == b.fen()


def report():
    b = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"]:
        b.push_san(san)
    row = {
        **{k: "" for k in REPORT_FIELDS},
        "flag": "blunder",
        "cost": "1.4",
        "lost_points": "1.4",
        "your_score_pct": "0",
        "db_move_score_pct": "33",
        "db_position_score_pct": "50",
        "move_number": "4",
        "ply": "7",
        "fen": b.fen(),
        "your_move": "Nxe5",
        "your_games": "3",
        "player_color": "white",
        "eco": "C50",
        "opening": "Italian Game",
        "eval_drop_pawns": "1.4",
        "engine_best_1": "O-O",
        "variation_line": "e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5",
    }
    return {
        "rows": [row],
        "tree": [],
        "player": "Player",
        "summary": summarise(
            [row], {"games": 3, "nodes": 12, "repeated": 4, "tree_rows": 4}
        ),
        "gameIds": ["https://lichess.org/abcdefgh"],
        "source": "upload",
        "demo": False,
    }


def seed_report(page, data=None):
    page.evaluate("(data)=>Store.lastReport.save(data)", data or report())
    page.reload()
    page.wait_for_function("window.PlayerLab && Auth.state.ready")
    expect(page.locator("#libBoard")).to_have_attribute("aria-busy", "false")
    page.evaluate("App.go('progress')")


def expand(page):
    page.locator('[data-decision-row="0"]>summary').click()
    expect(page.locator('[data-decision-board="0"]')).to_be_visible()


def test_catalogue_is_lazy_complete_searchable_and_paginated(page, app_url):
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    ready(page, app_url)
    assert not any("/opening-lines/" in r for r in requests)
    page.evaluate("App.go('lines')")
    expect(page.locator("#deepScope")).to_contain_text(
        "3,865 matching routes of 3,865 · 500 ECO codes"
    )
    assert page.locator(".deep-route-list>li").count() == 30
    page.locator("[data-deep=more]").click()
    expect(page.locator(".deep-route-list>li")).to_have_count(60)
    page.locator("#deepQuery").fill("Sicilian Najdorf")
    expect(page.locator("#deepScope")).to_contain_text("33 matching routes")
    page.locator("#deepQuery").fill("B90")
    expect(page.locator(".deep-route-list>li")).not_to_have_count(30)
    assert all(v == "B90" for v in page.locator(".deep-eco").all_text_contents())
    page.locator("#deepQuery").fill("1.e4 e5 2.Nf3 Nc6")
    expect(page.locator("#deepScope")).not_to_contain_text("0 matching routes")
    page.locator("#deepFirst").select_option("d4")
    expect(page.locator("#deepScope")).to_contain_text("0 matching routes")
    assert (
        "not every possible continuation" in page.locator(".deep-source").inner_text()
    )


def test_every_ply_of_longest_route_has_the_exact_board_and_can_branch(page, app_url):
    ready(page, app_url, "lines")
    open_line(page)
    pack = json.loads(
        (
            ROOT / f'chess-dashboard/public/app/opening-lines/{LONGEST["eco"]}.json'
        ).read_text()
    )
    route = next(l for l in pack["lines"] if l["id"] == LONGEST["id"])
    b = chess.Board()
    assert_board(page, b)
    for i, uci in enumerate(route["uci"]):
        page.locator("[data-deep=next]").click()
        b.push_uci(uci)
        page.wait_for_function("(fen)=>Study.snapshot().pos.fen===fen", arg=b.fen())
        expect(page.locator("#deepBoardPanel")).to_have_attribute("aria-busy", "false")
        assert_board(page, b)
        if i == 0:
            expect(page.locator("#boardCompanion")).to_have_attribute(
                "data-reaction", "book"
            )
    expect(page.locator("[data-deep=next]")).to_be_disabled()
    assert page.locator("[data-deep-play]").count() == b.legal_moves.count()
    page.locator("[data-deep=back]").click()
    b.pop()
    page.wait_for_function("(fen)=>Study.snapshot().pos.fen===fen", arg=b.fen())
    page.locator("#libForward").click()
    b.push_uci(route["uci"][-1])
    page.wait_for_function("(fen)=>Study.snapshot().pos.fen===fen", arg=b.fen())
    assert_board(page, b)
    page.locator("[data-deep=restart]").click()
    page.wait_for_function("Study.snapshot().history.length===0")
    expect(page.locator("#deepBoardPanel")).to_have_attribute("aria-busy", "false")
    assert page.locator("[data-deep-play]").count() == 20
    # Choose a non-reference first move; the route remains recoverable.
    alternate = next(m for m in chess.Board().legal_moves if m.uci() != route["uci"][0])
    button = page.locator('[data-deep-play="' + alternate.uci() + '"]')
    button.evaluate("el=>{const d=el.closest('details');if(d)d.open=true}")
    button.click()
    expect(page.locator("#deepBoardPanel")).to_contain_text("your own continuation")
    expect(page.locator("[data-deep=next]")).to_be_disabled()
    assert page.evaluate("Study.snapshot().future.length") == 0


def test_saved_routes_survive_reload_and_removal_is_versioned(page, app_url):
    ready(page, app_url, "lines")
    expect(page.locator(".deep-route-list")).to_be_visible()
    id = page.locator("[data-deep-save]").first.get_attribute("data-deep-save")
    page.locator(f'[data-deep-save="{id}"]').click()
    page.reload()
    page.wait_for_function("window.DeepLines && Auth.state.ready")
    page.locator("#deepSavedOnly").check()
    expect(page.locator(".deep-route-list>li")).to_have_count(1)
    page.locator("[data-deep-save]").click()
    expect(page.locator("#deepScope")).to_contain_text("0 matching routes")
    value = page.evaluate("(key)=>Store.prefs.get(key)", BOOKMARK + id)
    assert value["deleted"] and value["updated"] > 0
    page.reload()
    expect(page.locator(".deep-route-list")).to_be_visible()
    page.locator("#deepSavedOnly").check()
    expect(page.locator("#deepScope")).to_contain_text("0 matching routes")


def test_fork_filter_and_keyboard_navigation_reach_deep_lines(page, app_url):
    ready(page, app_url)
    page.locator("#movesTab").focus()
    page.keyboard.press("ArrowRight")
    expect(page.locator("#branchesTab")).to_be_focused()
    expect(page.locator("#deepBoardPanel")).to_have_attribute("aria-busy", "false")
    assert page.locator("[data-deep-play]").count() == 20
    page.locator('[data-deep-fork="e2e4"]').click()
    expect(page.locator("#deepScope")).to_contain_text("Named routes through e4")
    page.locator("[data-deep=clear]").click()
    expect(page.locator("#deepScope")).to_contain_text("3,865 matching routes")


def test_failed_pack_does_not_replace_board_and_autoplay_stops_on_navigation(
    page, app_url
):
    ready(page, app_url, "lines")
    before = page.evaluate("Study.snapshot().pos.fen")
    page.route(
        "**/opening-lines/" + LONGEST["eco"] + ".json",
        lambda r: r.fulfill(status=503, json={}),
    )
    page.evaluate("(id)=>DeepLines.open(id)", LONGEST["id"])
    expect(page.locator("#deepCatalogueStatus")).to_contain_text("could not load")
    assert page.evaluate("Study.snapshot().pos.fen") == before
    page.unroute("**/opening-lines/" + LONGEST["eco"] + ".json")
    open_line(page)
    page.locator("[data-deep=autoplay]").click()
    page.wait_for_function("Study.snapshot().history.length>=1")
    page.evaluate("App.go('progress')")
    frozen = page.evaluate("Study.snapshot().history.length")
    page.wait_for_timeout(1850)
    assert page.evaluate("Study.snapshot().history.length") == frozen


def test_reflections_focus_and_old_report_work_without_invented_clocks(page, app_url):
    ready(page, app_url, "progress")
    seed_report(page)
    expand(page)
    expect(page.locator(".decision-facts")).to_contain_text("can legally play Nxe5")
    page.locator(".decision-sources>summary").click()
    expect(page.locator(".decision-sources")).to_contain_text(
        "no detailed source or clock"
    )
    page.locator("#decisionGoal").select_option("threats")
    page.locator("#decisionPreferences button").click()
    page.locator("#decisionReason0").select_option("threat")
    page.locator("#decisionNote0").fill("Check their captures before my next move.")
    page.locator("[data-decision-reflection] button[type=submit]").click()
    expect(page.locator(".decision-status")).to_have_text("Reflection saved.")
    expect(page.locator("#decisionPatternSummary")).to_contain_text("1 of 1")
    page.reload()
    page.wait_for_function("Auth.state.ready")
    expand(page)
    expect(page.locator("#decisionReason0")).to_have_value("threat")
    expect(page.locator("#decisionNote0")).to_have_value(
        "Check their captures before my next move."
    )
    assert page.evaluate("App.reportContext().gameIds") == [
        "https://lichess.org/abcdefgh"
    ]
    page.locator("[data-decision-clear]").click()
    expect(page.locator("#decisionReason0")).to_have_value("")
    removed = page.evaluate(
        '(root)=>Object.entries(Store.prefs.all()).find(([k])=>k.startsWith(root+"reflection:"))[1]',
        LAB,
    )
    assert removed["deleted"] and removed["updated"]
    page.evaluate("App.go('today')")
    expect(page.locator("#playerFocus")).to_contain_text("Notice threats before moving")


def test_decision_review_draws_verified_capture_then_practises_legal_response(
    page, app_url
):
    ready(page, app_url, "progress")
    data = report()
    seed_report(page, data)
    expand(page)
    page.locator("[data-decision-board]").click()
    expect(page.locator("#libBoard .cb-head")).to_have_count(1)
    after = chess.Board(data["rows"][0]["fen"])
    after.push_san("Nxe5")
    assert_board(page, after)
    expect(page.locator("#boardCompanion")).to_contain_text(
        "legally captures your knight"
    )
    expect(page.locator("#libBoard .cb-circle[data-square=e5]")).to_be_visible()
    page.evaluate("App.go('progress')")
    expand(page)
    page.locator("[data-decision-practice]").click()
    expect(page.locator("[data-training=hint]")).to_be_visible()
    expect(page.locator("#playerFocus")).to_be_hidden()
    assert_board(page, chess.Board(data["rows"][0]["fen"]))
    page.locator("#libBoard [data-square=e1]").click()
    page.locator("#libBoard [data-square=g1]").click()
    expect(page.locator("[data-training=next]")).to_be_visible()


def test_fresh_source_evidence_is_bounded_escaped_and_sample_reflections_separate(
    page, app_url
):
    ready(page, app_url, "progress")
    data = report()
    row = data["rows"][0]
    response = page.request.get(
        app_url + "/api/decision-context",
        params={
            "fen": row["fen"],
            "played": row["your_move"],
            "best": row["engine_best_1"],
        },
    )
    assert response.ok
    facts = response.json()
    data["summary"]["decision_evidence"] = {
        "decisions": [
            {
                "key": " ".join(row["fen"].split()[:4]) + "|Nxe5",
                "context": facts,
                "uniqueSourceGames": 1,
                "sourceDecisions": 1,
                "clockSamples": 1,
                "under60Seconds": 1,
                "sources": [
                    {
                        "game": "javascript:alert(1)",
                        "date": "<script>bad</script>",
                        "ply": 7,
                        "clockAfter": 40,
                        "spent": 6,
                        "spentSource": "pgn-emt",
                    }
                ],
            }
        ]
    }
    seed_report(page, data)
    expand(page)
    page.locator(".decision-sources>summary").click()
    expect(page.locator(".decision-sources")).to_contain_text("1/1 recorded clocks")
    expect(page.locator(".decision-sources")).to_contain_text("0:40")
    assert page.locator(".decision-sources a,.decision-sources script").count() == 0
    page.locator("#decisionReason0").select_option("clock")
    page.locator("[data-decision-reflection] button[type=submit]").click()
    data["demo"] = True
    data["source"] = "sample"
    seed_report(page, data)
    expand(page)
    expect(page.locator("#decisionReason0")).to_have_value("")
    expect(page.locator("#playerLab")).to_contain_text("not your playing profile")
    assert (
        page.request.get(
            app_url + "/api/decision-context",
            params={"fen": chess.STARTING_FEN, "played": "e5"},
        ).status
        == 400
    )


@pytest.mark.parametrize("orientation", ["white", "black"])
def test_arrowheads_are_filled_directional_shapes_independent_of_hidden_boards(
    page, app_url, orientation
):
    ready(page, app_url)
    arrows = [
        {"from": "d4", "to": to, "kind": "best"}
        for to in ["d8", "h8", "h4", "h1", "d1", "a1", "a4", "a8"]
    ] + [{"from": "g1", "via": "g3", "to": "f3", "kind": "played"}]
    info = page.evaluate(
        """({orientation,arrows})=>{
      const hidden=document.createElement('div');hidden.hidden=true;document.body.prepend(hidden);
      const ghost=new LeakBoard.Board(hidden);ghost.setPosition(LeakBoard.START_FEN,{arrows});
      const host=document.createElement('div');host.style.cssText='position:fixed;inset:100px auto auto 200px;width:500px;z-index:1000';document.body.append(host);
      const board=new LeakBoard.Board(host,{orientation});board.setPosition('8/8/8/8/8/8/8/8 w - - 0 1',{arrows});
      return [...host.querySelectorAll('.cb-arrow-group')].map(g=>({from:g.dataset.from,to:g.dataset.to,d:g.querySelector('.cb-head').getAttribute('d'),fill:getComputedStyle(g.querySelector('.cb-head')).fill,bbox:{width:g.querySelector('.cb-head').getBBox().width,height:g.querySelector('.cb-head').getBBox().height},marker:g.querySelector('[marker-end]')!==null}));
    }""",
        {"orientation": orientation, "arrows": arrows},
    )
    assert len(info) == 9

    def center(sq):
        f = ord(sq[0]) - 97
        r = int(sq[1]) - 1
        return (
            (f if orientation == "white" else 7 - f) * 10 + 5,
            (7 - r if orientation == "white" else r) * 10 + 5,
        )

    for arrow in info:
        assert arrow["fill"] not in ("none", "rgba(0, 0, 0, 0)") and not arrow["marker"]
        assert arrow["bbox"]["width"] > 0 and arrow["bbox"]["height"] > 0
        nums = [
            float(n) for n in re.findall(r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?", arrow["d"])
        ]
        tip = nums[:2]
        end = center(arrow["to"])
        assert math.dist(tip, end) == pytest.approx(0.8)
        base = ((nums[2] + nums[4]) / 2, (nums[3] + nums[5]) / 2)
        origin = center("g3" if arrow["from"] == "g1" else arrow["from"])
        assert (tip[0] - base[0]) * (end[0] - origin[0]) + (tip[1] - base[1]) * (
            end[1] - origin[1]
        ) > 0
    assert page.locator(".cb-arrow[marker-end]").count() == 0


def test_account_delivery_preserves_bookmark_and_reflection_tombstones(page, app_url):
    from test_plans_v4 import account

    account(page)
    page.route(
        "**/api/state/pref", lambda r: r.fulfill(status=503, json={"error": "offline"})
    )
    ready(page, app_url, "lines")
    expect(page.locator(".deep-route-list")).to_be_visible()
    id = page.locator("[data-deep-save]").first.get_attribute("data-deep-save")
    page.locator(f'[data-deep-save="{id}"]').click()
    page.locator(f'[data-deep-save="{id}"]').click()
    page.wait_for_function(
        '(key)=>Store.sync.pending("v4-owner")[key]?.value?.deleted', arg=BOOKMARK + id
    )
    page.evaluate("App.go('progress')")
    seed_report(page)
    expand(page)
    page.locator("#decisionReason0").select_option("forgot")
    page.locator("[data-decision-reflection] button[type=submit]").click()
    page.evaluate("App.go('progress')")
    expand(page)
    page.locator("[data-decision-clear]").click()
    page.wait_for_function(
        '(root)=>Object.entries(Store.sync.pending("v4-owner")).some(([k,v])=>k.startsWith(root+"reflection:")&&v.value.deleted)',
        arg=LAB,
    )
    page.reload()
    page.wait_for_function("Auth.state.ready")
    pending = page.evaluate('Store.sync.pending("v4-owner")')
    assert pending[BOOKMARK + id]["value"]["deleted"]
    assert any(
        k.startswith(LAB + "reflection:") and v["value"]["deleted"]
        for k, v in pending.items()
    )
    snapshot = page.evaluate("Store.snapshot()")
    assert snapshot["prefs"][BOOKMARK + id]["deleted"]


def test_delayed_route_cannot_steal_navigation_or_an_active_lesson(page, app_url):
    ready(page, app_url, "lines")
    pack_path = ROOT / f'chess-dashboard/public/app/opening-lines/{LONGEST["eco"]}.json'
    pending = []
    page.route(
        "**/opening-lines/" + LONGEST["eco"] + ".json",
        lambda route: pending.append(route),
    )
    page.evaluate("(id)=>{window.pendingDeep=DeepLines.open(id);}", LONGEST["id"])
    page.wait_for_timeout(100)
    assert pending
    page.evaluate("App.go('progress')")
    pending.pop().fulfill(json=json.loads(pack_path.read_text()))
    page.evaluate("()=>window.pendingDeep")
    assert page.evaluate("App.currentView()") == "progress"
    assert page.evaluate("DeepLines.info()") is None
    page.unroute("**/opening-lines/" + LONGEST["eco"] + ".json")
    open_line(page)
    # Hold a position request while a new plan takes ownership of the board.
    held = []
    page.route("**/api/position?*", lambda route: held.append(route))
    page.locator("[data-deep=next]").click()
    page.evaluate("App.go('explore')")
    page.locator("#planExplore [data-plan=start]").click()
    page.locator("[data-plan=frame-next]").click()
    page.locator("[data-plan=try]").click()
    expected = page.evaluate("Plans.info()")
    for route in held:
        route.fulfill(response=route.fetch())
    page.unroute("**/api/position?*")
    page.wait_for_timeout(150)
    assert page.evaluate("Plans.active()")
    assert page.evaluate("Plans.info().id") == expected["id"]
    expect(page.locator("[data-plan=hint]")).to_be_visible()
