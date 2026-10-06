#!/usr/bin/env python3
"""ラボのワークスペース — ブラウザ 1 画面でラボを解く(BL-234)。

画面: 左半分= タスク／トポロジ(タブ切替)、右半分= 機器コンソール(機器ごとのタブ)。

  ブラウザ(xterm.js) ⇄ WebSocket ⇄ この中継 ⇄ SSH ⇄ CML コンソールサーバ ⇄ ノードのシリアル

動かし方は 2 通り:

  パック常駐(既定)   lab_console.py --repo <リポ> [--port 8897] [--pack-port 8899] [--bind 127.0.0.1]
      `scripts/pack.sh serve` が配信サーバと一緒に起動する。入口はパックのラボページ下端の帯の
      「Open lab workspace」(= 配信サーバの /_lab → ここの /lab?pack=<PACK-ID>&no=<N>)。
      左のタスクはパックの問題ページそのもの(解答欄・ストップウォッチもそのまま使える)。
  単発               lab_console.py --lab <CML のラボ題名> [--task <Task.md>]
      1 ラボに固定して開く(入口は /)。パックを介さない出題や動作確認に使う。

  GET /lab?pack=&no=   … 画面(パック常駐)          GET /       … 画面(単発)
  GET /api/topo        … トポロジ(CML API の座標・リンクから起こした SVG とノード一覧)
  GET /toponotes       … 問題文の盤面の節(トポロジ／構成図)。Topology タブで結線図の下に出す
  GET /ws/console?node=<ラベル>   … そのノードのコンソール(バイト列をそのまま流す)
  GET /task            … タスク(単発のみ。--task の Markdown を問題用紙と同じ体裁で HTML 化)

設計上の約束:
  - **繋げるラボはサーバ側でしか決まらない**。パック常駐ではパックの manifest のラボ項目から
    ラボ題名を導き(問題 ID → CCNP-LAB-<md5 先頭 8 桁>)、単発では --lab の 1 本だけ。
    クライアントからラボ題名は受け取らない。ノード名は CML API の一覧と突き合わせる。
  - コンソールサーバには `open …` を **exec で渡す**。コンソールを抜けると SSH ごと終わるので、
    コンソールサーバのプロンプト(他ラボへ移れる)には降りられない。
  - この中継は CML の認証を肩代わりする。bind の既定は 127.0.0.1。
  - WebSocket は Origin を検査する(別サイトのページからこの中継へ繋がせない)。
  - 機器へは何も打たない(接続時に改行すら送らない)。出題状態を変えるのは受験者の打鍵だけ。
  - コンソールは同じノードへの全接続で共有される(CML の仕様)。採点のコンソール経路とも共有。
  - 問題文の盤面の節は Task タブに出さず Topology タブへ移す(結線図と重複するため)。節には
    アドレス・AS など結線図に無い情報が載るので、消さずに置き場所だけ変える。切り分けは
    render_html.split_topology。パックでは gen_pack が書いた q<N>.ws.html / q<N>.topo.html を使う。

実測の根拠と PoC の記録は poc/webconsole/README.md。
接続情報は group_vars/all/local.yml(環境変数 CML_HOST / CML_USER / CML_PASS で上書き可)。
"""
import argparse
import asyncio
import hashlib
import html
import json
import math
import os
import re
import signal
import sys
from collections import defaultdict, namedtuple
from urllib.parse import urlparse

import aiohttp
import asyncssh
import yaml
from aiohttp import web

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_pack                                        # noqa: E402
import render_html                                     # noqa: E402

ASSETS = os.path.join(HERE, "assets")
PACK_RE = re.compile(r"^PACK-[A-Za-z0-9_.-]{1,64}$")

INFRA = {"external_connector", "unmanaged_switch"}      # コンソールを持たない(箱だけ描く)
ROUTERS = {"iol-xe", "iosv", "csr1000v", "cat8000v", "iosxrv9000", "cat-sdwan-edge"}
SWITCHES = {"ioll2-xe", "iosvl2", "nxosv9000", "cat9000v-q200", "cat9000v-uadp", "vjunos-switch"}
FIREWALLS = {"asav", "fortigate"}
# 貼り付けの流量制御。シリアルコンソールは一度に流し込むと取りこぼす
#   実測(IOL・200 行 9.7KB): 1 フレーム一括= 約 40 行で崩れる／行ごとに 3〜30ms 空ける= 200/200 行
PASTE_MIN = 64          # これを超える入力は貼り付けとみなす(打鍵は 1〜数バイト)
PASTE_GAP = 0.01        # 行間の待ち(秒)
IF_ABBR = (("TenGigabitEthernet", "Te"), ("GigabitEthernet", "Gi"), ("FastEthernet", "Fa"),
           ("Ethernet", "Et"), ("Loopback", "Lo"), ("Management", "Mg"))

# 繋ぐ先: CML のラボ題名・左のタスクの URL・画面の見出し・盤面の節のページ(パックの q<N>.topo.html。無ければ None)
Target = namedtuple("Target", "title task_src caption notes")


def lab_title(problem_id):
    """問題 ID → CML のラボ題名(gen_cml_lab.py・lab_up.yml と同じ規則)。"""
    return "CCNP-LAB-" + hashlib.md5(problem_id.encode()).hexdigest()[:8]


# --------------------------------------------------------------------------
# CML API
# --------------------------------------------------------------------------
class Cml:
    def __init__(self, host, user, password):
        self.host = host.replace("https://", "").rstrip("/")
        self.user, self.password = user, password
        self.base = f"https://{self.host}/api/v0"

    async def _get(self, sess, path, **params):
        async with sess.get(self.base + path, params=params, ssl=False) as r:
            r.raise_for_status()
            return await r.json()

    async def fetch(self, title):
        """題名のラボの (lab_id, topology, 要素状態) を返す。無ければ None。"""
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.post(self.base + "/authenticate", ssl=False,
                                 json={"username": self.user, "password": self.password}) as r:
                r.raise_for_status()
                token = await r.json()
            sess.headers["Authorization"] = f"Bearer {token}"
            ids = await self._get(sess, "/labs", show_all="true")
            labs = await asyncio.gather(*(self._get(sess, f"/labs/{i}") for i in ids))
            hit = [d for d in labs if d.get("lab_title") == title]
            if not hit:
                return None
            lab_id = hit[0]["id"]
            topo, state = await asyncio.gather(
                self._get(sess, f"/labs/{lab_id}/topology", exclude_configurations="true"),
                self._get(sess, f"/labs/{lab_id}/lab_element_state"))
            return lab_id, topo, state


# --------------------------------------------------------------------------
# トポロジ: CML の座標・リンク → 画面用のモデル → SVG
#   図は目で写さず API から機械的に起こす(配線の写し間違いを構造的に防ぐ)。
# --------------------------------------------------------------------------
def abbr_if(name):
    for long, short in IF_ABBR:
        if name.startswith(long):
            return short + name[len(long):]
    return name


def kind_of(ndef):
    if ndef in ROUTERS:
        return "rt"
    if ndef in SWITCHES:
        return "sw"
    if ndef in FIREWALLS:
        return "fw"
    if ndef in INFRA:
        return "infra"
    return "host"


def build_model(topo, state):
    """管理網の部品(MGMT-SW とそこにしか繋がらない外部接続)を除いたノード／リンクの一覧。"""
    nodes = {n["id"]: n for n in topo["nodes"]}
    if_label = {i["id"]: i["label"] for n in topo["nodes"] for i in n["interfaces"]}
    adj = defaultdict(set)
    for lk in topo["links"]:
        adj[lk["node_a"]].add(lk["node_b"])
        adj[lk["node_b"]].add(lk["node_a"])
    hidden = {nid for nid, n in nodes.items() if n["label"] == "MGMT-SW"}
    hidden |= {nid for nid, n in nodes.items()
               if n["node_definition"] == "external_connector" and adj[nid] and adj[nid] <= hidden}
    out_nodes = []
    for nid, n in nodes.items():
        if nid in hidden:
            continue
        ndef = n["node_definition"]
        out_nodes.append({"label": n["label"], "def": ndef, "kind": kind_of(ndef),
                          "x": n["x"], "y": n["y"],
                          "state": (state.get("nodes") or {}).get(nid, ""),
                          "console": ndef not in INFRA})
    out_links = []
    for lk in topo["links"]:
        if lk["node_a"] in hidden or lk["node_b"] in hidden or lk["node_a"] == lk["node_b"]:
            continue
        out_links.append({"a": nodes[lk["node_a"]]["label"], "b": nodes[lk["node_b"]]["label"],
                          "a_if": abbr_if(if_label.get(lk["interface_a"], "")),
                          "b_if": abbr_if(if_label.get(lk["interface_b"], ""))})
    return {"nodes": out_nodes, "links": out_links}


def _clip(b, x2, y2):
    """箱 b の中心から (x2,y2) へ向かう線が、b の縁を出る点。"""
    dx, dy = x2 - b["cx"], y2 - b["cy"]
    if dx == 0 and dy == 0:
        return b["cx"], b["cy"]
    hw, hh = b["w"] / 2 + 2, b["h"] / 2 + 2
    s = min(hw / abs(dx) if dx else math.inf, hh / abs(dy) if dy else math.inf)
    return b["cx"] + dx * s, b["cy"] + dy * s


def _overlaps(r, rects):
    return any(r[0] < q[2] and q[0] < r[2] and r[1] < q[3] and q[1] < r[3] for q in rects)


def topo_svg(model, gap=190):
    """最も近い 2 ノードの間隔が gap 前後になるよう CML の座標を縮尺し、SVG にする。"""
    ns = model["nodes"]
    if not ns:
        return "<p>(no nodes)</p>"
    dists = [math.hypot(a["x"] - b["x"], a["y"] - b["y"])
             for i, a in enumerate(ns) for b in ns[i + 1:]]
    dmin = min([d for d in dists if d > 0], default=gap)
    s = min(1.6, max(0.4, gap / dmin))
    boxes = {}
    for n in ns:
        boxes[n["label"]] = {"cx": n["x"] * s, "cy": n["y"] * s, "h": 36,
                             "w": max(64, len(n["label"]) * 9 + 26), "n": n}
    lines, ends = [], []
    pairs = defaultdict(list)                 # 同じ 2 ノード間の並行リンクは垂直方向へずらす
    for lk in model["links"]:
        pairs[tuple(sorted((lk["a"], lk["b"])))].append(lk)
    for (pa, _pb), lks in pairs.items():
        for i, lk in enumerate(lks):
            ba, bb = boxes[lk["a"]], boxes[lk["b"]]
            dx, dy = bb["cx"] - ba["cx"], bb["cy"] - ba["cy"]
            ln = math.hypot(dx, dy) or 1
            sign = 1 if lk["a"] == pa else -1          # 向きが逆のリンクでも同じ側へずらす
            off = (i - (len(lks) - 1) / 2) * 15 * sign
            ox, oy = -dy / ln * off, dx / ln * off
            x1, y1 = _clip(ba, bb["cx"] + ox * 4, bb["cy"] + oy * 4)
            x2, y2 = _clip(bb, ba["cx"] + ox * 4, ba["cy"] + oy * 4)
            x1, y1, x2, y2 = x1 + ox, y1 + oy, x2 + ox, y2 + oy
            lines.append(f'<line class="tl" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
            seg = math.hypot(x2 - x1, y2 - y1) or 1
            ux, uy = (x2 - x1) / seg, (y2 - y1) / seg
            for text, bx, by, d in ((lk["a_if"], x1, y1, 1), (lk["b_if"], x2, y2, -1)):
                if text:
                    ends.append((text, bx, by, ux * d, uy * d, seg))
    # IF 名のラベル: 箱の縁からラベルが出きる距離に置き、箱や他のラベルと重なるなら線に沿って先へ送る。
    # 線の半分(自分側)は越えない。置き場が無ければ最初の位置に戻す(重なりは残るが配線は読める)
    taken = [(b["cx"] - b["w"] / 2 - 2, b["cy"] - b["h"] / 2 - 2,
              b["cx"] + b["w"] / 2 + 2, b["cy"] + b["h"] / 2 + 2) for b in boxes.values()]
    labels = []
    for text, bx, by, ux, uy, seg in ends:
        w = len(text) * 6.6 + 8
        t0 = min(7 + abs(ux) * w / 2 + abs(uy) * 9, seg * 0.46)
        t, rect = t0, None
        while t <= seg * 0.46 + 0.01:
            x, y = bx + ux * t, by + uy * t
            r = (x - w / 2, y - 8, x + w / 2, y + 8)
            if not _overlaps(r, taken):
                rect = r
                break
            t += 5
        if rect is None:
            x, y = bx + ux * t0, by + uy * t0
            rect = (x - w / 2, y - 8, x + w / 2, y + 8)
        taken.append(rect)
        labels.append((x, y, w, text))
    parts = lines
    for x, y, w, text in labels:              # ラベルは線より前面・白抜き
        parts.append(f'<rect class="tlb" x="{x - w / 2:.1f}" y="{y - 8:.1f}" width="{w:.1f}" height="16" rx="3"/>')
        parts.append(f'<text class="tlt" x="{x:.1f}" y="{y + 4:.1f}">{html.escape(text)}</text>')
    for label, b in boxes.items():            # ノードは最前面
        n = b["n"]
        cls = f'nd k-{n["kind"]}' + (" has-con" if n["console"] else "")
        attr = f' data-node="{html.escape(label)}" tabindex="0" role="button"' if n["console"] else ""
        up = "up" if n["state"] == "BOOTED" else "down"
        parts.append(
            f'<g class="{cls}"{attr}><title>{html.escape(n["def"])} — {html.escape(n["state"] or "?")}</title>'
            f'<rect x="{b["cx"] - b["w"] / 2:.1f}" y="{b["cy"] - b["h"] / 2:.1f}" width="{b["w"]}" '
            f'height="{b["h"]}" rx="{18 if n["kind"] in ("host", "infra") else 5}"/>'
            f'<text class="tn" x="{b["cx"]:.1f}" y="{b["cy"] + 5:.1f}">{html.escape(label)}</text>'
            + (f'<circle class="st {up}" cx="{b["cx"] + b["w"] / 2 - 8:.1f}" cy="{b["cy"] - b["h"] / 2 + 8:.1f}" r="3.2"/>'
               if n["console"] else "") + "</g>")
    m = 46
    x0 = min(b["cx"] - b["w"] / 2 for b in boxes.values()) - m
    y0 = min(b["cy"] - b["h"] / 2 for b in boxes.values()) - m
    x1 = max(b["cx"] + b["w"] / 2 for b in boxes.values()) + m
    y1 = max(b["cy"] + b["h"] / 2 for b in boxes.values()) + m
    return (f'<svg viewBox="{x0:.0f} {y0:.0f} {x1 - x0:.0f} {y1 - y0:.0f}" '
            f'style="max-width:{(x1 - x0) * 1.5:.0f}px" role="img">\n' + "\n".join(parts) + "\n</svg>")


# --------------------------------------------------------------------------
# 繋ぐ先の解決
# --------------------------------------------------------------------------
def resolve(app, request):
    """リクエスト → Target。繋いでよいラボはここでしか決まらない(無効なら None)。"""
    if app["fixed"]:
        return app["fixed"]
    pack, no = request.query.get("pack", ""), request.query.get("no", "")
    if not PACK_RE.match(pack) or not no.isdigit():
        return None
    pdir = os.path.join(app["packs"], pack)
    if not os.path.exists(os.path.join(pdir, "manifest.yml")):
        return None
    it = next((i for i in gen_pack.read_manifest(pdir)["items"]
               if i["no"] == int(no) and i.get("kind") == "lab" and i.get("ref")), None)
    if it is None:
        return None
    host = request.url.host or "localhost"
    if ":" in host:                           # IPv6 リテラル
        host = f"[{host}]"
    # ワークスペース用の別版(gen_pack.write_workspace_pages)があればそれを使う:
    #   q<N>.ws.html= 左枠の問題ページ(盤面の節を除く)／q<N>.topo.html= 盤面の節(ある問題だけ)
    n = int(no)
    notes = os.path.join(pdir, f"q{n}.topo.html")
    page = f"q{n}.ws.html" if os.path.exists(os.path.join(pdir, f"q{n}.ws.html")) else f"q{n}.html"
    return Target(lab_title(it["ref"]),
                  f"{request.scheme}://{host}:{app['pack_port']}/{pack}/{page}",
                  f"{pack} · Q{n}", notes if os.path.exists(notes) else None)


async def load_topo(app, title):
    """CML からラボを読み直し、そのラボで接続を許すノード名の集合も更新する。"""
    got = await app["cml"].fetch(title)
    if got is None:
        app["nodes"].pop(title, None)
        return None
    _lab_id, topo, state = got
    model = build_model(topo, state)
    app["nodes"][title] = {n["label"] for n in model["nodes"] if n["console"]}
    return model


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
async def h_page(request):
    tgt = resolve(request.app, request)
    if tgt is None:
        return web.Response(status=404, content_type="text/html", text=(
            "<p>No such lab. Open a lab page of a pack and use <b>Open lab workspace</b>.</p>"))
    page = (PAGE.replace("@@CAPTION@@", html.escape(tgt.caption))
            .replace("@@TASK_SRC@@", html.escape(tgt.task_src, quote=True))
            .replace("@@PAPER@@", render_html.PAPER).replace("@@PANEL@@", render_html.PANEL))
    return web.Response(text=page, content_type="text/html", headers={"Cache-Control": "no-store"})


async def h_root(request):
    if request.app["fixed"]:
        return await h_page(request)
    return web.Response(content_type="text/html", text=(
        "<p>Lab workspace server. Open a lab page of a pack and use <b>Open lab workspace</b>.</p>"))


def _single_task(app):
    """単発: --task の Markdown を (盤面の節を除いた本文, 盤面の節) に分けて返す。"""
    if not app["task"]:
        return "*(no task file — start with `--task <Task.md>`)*", ""
    with open(app["task"], encoding="utf-8") as fh:
        return render_html.split_topology(fh.read())


async def h_task(request):
    if not request.app["fixed"]:
        return web.Response(status=404, text="not found")
    rest, _topo = _single_task(request.app)
    return web.Response(text=render_html.render(rest, title=request.app["fixed"].caption),
                        content_type="text/html")


def _has_notes(app, tgt):
    return bool(_single_task(app)[1]) if app["fixed"] else tgt.notes is not None


async def h_toponotes(request):
    """問題文の盤面の節だけのページ。Topology タブが結線図の下に枠で読み込む。"""
    app = request.app
    tgt = resolve(app, request)
    if tgt is None or not _has_notes(app, tgt):
        return web.Response(status=404, text="no topology section")
    if app["fixed"]:
        text = render_html.render(_single_task(app)[1], title=f"{tgt.caption} — Topology")
    else:
        with open(tgt.notes, encoding="utf-8") as fh:
            text = fh.read()
    return web.Response(text=text, content_type="text/html", headers={"Cache-Control": "no-store"})


async def h_topo(request):
    tgt = resolve(request.app, request)
    if tgt is None:
        return web.json_response({"error": "no such lab"}, status=404)
    notes = _has_notes(request.app, tgt)      # 結線図が出せない時も、問題文の盤面の節は読めるようにする
    try:
        model = await load_topo(request.app, tgt.title)
    except Exception as e:
        return web.json_response({"error": f"CML API: {e}", "notes": notes}, status=502)
    if model is None:
        return web.json_response(
            {"error": "This lab is not running on CML (not deployed yet, or already torn down).",
             "notes": notes}, status=404)
    nodes = [{k: n[k] for k in ("label", "def", "kind", "state", "console")} for n in model["nodes"]]
    return web.json_response({"nodes": nodes, "svg": topo_svg(model), "notes": notes})


def _same_origin(request):
    origin = request.headers.get("Origin")
    return origin is None or urlparse(origin).netloc == request.headers.get("Host")


async def h_console(request):
    app = request.app
    if not _same_origin(request):
        return web.Response(status=403, text="cross-origin")
    tgt = resolve(app, request)
    if tgt is None:
        return web.Response(status=404, text="no such lab")
    node = request.query.get("node", "")
    if node not in app["nodes"].get(tgt.title, ()):
        try:
            await load_topo(app, tgt.title)   # 画面より先に WS が来た時・ノードが増えた時
        except Exception:
            pass
    if node not in app["nodes"].get(tgt.title, ()):
        return web.Response(status=404, text="unknown node")
    try:
        cols = min(400, max(20, int(request.query.get("cols", 80))))
        rows = min(200, max(5, int(request.query.get("rows", 24))))
    except ValueError:
        cols, rows = 80, 24

    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=1 << 20)
    await ws.prepare(request)
    cml = app["cml"]
    conn = None
    try:
        conn = await asyncssh.connect(cml.host, username=cml.user, password=cml.password,
                                      known_hosts=None, client_keys=None,
                                      keepalive_interval=30, connect_timeout=15)
        proc = await conn.create_process(f"open /{tgt.title}/{node}/0", encoding=None,
                                         term_type="xterm-256color", term_size=(cols, rows))
    except Exception as e:
        await ws.send_str(f"[bridge] cannot reach the console server: {e}")
        await ws.close()
        if conn:
            conn.close()
        return ws

    async def ssh_to_ws():
        while True:
            data = await proc.stdout.read(65536)
            if not data:
                break
            await ws.send_bytes(data)

    async def ws_to_ssh():
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                if len(msg.data) <= PASTE_MIN:
                    proc.stdin.write(msg.data)
                else:                                     # 貼り付け: 行ごとに間を空けて流す
                    for line in msg.data.splitlines(keepends=True):
                        proc.stdin.write(line)
                        await asyncio.sleep(PASTE_GAP)
            elif msg.type == aiohttp.WSMsgType.TEXT:      # 制御(今は端末サイズだけ)
                try:
                    c, r = json.loads(msg.data)["resize"]
                    proc.change_terminal_size(int(c), int(r))
                except Exception:
                    pass
            else:
                break

    tasks = [asyncio.ensure_future(ssh_to_ws()), asyncio.ensure_future(ws_to_ssh())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        conn.close()
        if not ws.closed:
            await ws.close(message=b"console closed")
    return ws


def load_cml():
    v = {}
    path = os.path.join(REPO, "group_vars", "all", "local.yml")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            v = yaml.safe_load(fh) or {}
    return Cml(os.environ.get("CML_HOST") or v["cml_host"],
               os.environ.get("CML_USER") or v["cml_username"],
               os.environ.get("CML_PASS") or v["cml_password"])


async def _follow_parent(app):
    """起動した親(配信サーバ)が居なくなったら自分も終わる。親の落ち方(Ctrl-C・kill・異常終了)を問わない。

    親の PID は起動した側から受け取る。自分で os.getppid() を読むと、親が先に落ちていた時
    (配信サーバがポート使用中で即終了した等)に、付け替わった先を親と見なして居残る(2026-10-06 実発)。
    """
    parent = app["with_parent"]

    async def watch():
        while os.getppid() == parent:
            await asyncio.sleep(2)
        os.kill(os.getpid(), signal.SIGTERM)      # run_app が受けて通常の終了処理をする

    app["parent_watch"] = asyncio.ensure_future(watch())


def make_app(repo=REPO, pack_port=8899, lab=None, task=None, with_parent=None):
    """lab を渡すと単発(そのラボに固定)、渡さなければパック常駐。"""
    app = web.Application()
    if with_parent:
        app["with_parent"] = with_parent
        app.on_startup.append(_follow_parent)
    app["fixed"] = Target(lab, "task", lab, None) if lab else None
    app["task"] = task
    app["packs"] = os.path.join(os.path.abspath(repo), "packs")
    app["pack_port"] = pack_port
    app["cml"] = load_cml()
    app["nodes"] = {}                         # ラボ題名 → コンソールを開いてよいノード名の集合
    app.router.add_get("/", h_root)
    app.router.add_get("/lab", h_page)
    app.router.add_get("/task", h_task)
    app.router.add_get("/api/topo", h_topo)
    app.router.add_get("/toponotes", h_toponotes)
    app.router.add_get("/ws/console", h_console)
    for name in ("xterm.js", "xterm.css", "addon-fit.js"):
        app.router.add_get(f"/vendor/{name}",
                           lambda _r, p=os.path.join(ASSETS, name): web.FileResponse(p))
    return app


# --------------------------------------------------------------------------
# 画面
# --------------------------------------------------------------------------
PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@@CAPTION@@ — Lab</title>
<link rel="stylesheet" href="vendor/xterm.css">
<style>
:root{ color-scheme: light; --line:#c3cad4; --ink:#1c2430; --mute:#5b6676; --accent:#0b5cad; --term:#0c0f14;
       --paper:@@PAPER@@; --panel:@@PANEL@@; }   /* 紙の色は問題ページと同じ値(render_html.PAPER / PANEL) */
html,body{ height:100%; margin:0; }
body{ font:14px/1.45 system-ui,"Segoe UI","Yu Gothic UI",sans-serif; color:var(--ink); background:var(--paper);
      display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); height:100vh; overflow:hidden; }
.half{ display:flex; flex-direction:column; min-width:0; min-height:0; }
.half + .half{ border-left:1px solid var(--line); }
.tabs{ display:flex; align-items:stretch; gap:0; background:#dfe2e7; border-bottom:1px solid var(--line);
       overflow-x:auto; flex:none; }
.tabs button{ font:inherit; font-weight:600; color:var(--mute); background:none; border:0;
              border-right:1px solid var(--line); padding:8px 14px; cursor:pointer; white-space:nowrap;
              display:flex; align-items:center; gap:7px; }
.tabs button:hover{ color:var(--ink); background:#d5d9df; }
.tabs button.on{ color:var(--ink); background:var(--paper); box-shadow:inset 0 -2px 0 var(--accent); }
.tabs .lab{ margin-left:auto; padding:8px 12px; color:var(--mute); font-size:12px; white-space:nowrap; align-self:center; }
.dot{ width:8px; height:8px; border-radius:50%; background:#c3cad6; flex:none; }
.dot.connecting{ background:#e0a100; } .dot.on{ background:#1f9d55; } .dot.off{ background:#c9382f; }
.pane{ flex:1; min-height:0; position:relative; }
.pane > *{ position:absolute; inset:0; }
[hidden]{ display:none !important; }   /* #topo の display:flex に負けないように */
iframe{ border:0; width:100%; height:100%; background:var(--paper); }
#topo{ overflow:auto; padding:14px; box-sizing:border-box; display:flex; flex-direction:column; gap:8px; }
#topo svg{ width:100%; height:auto; margin:0 auto; display:block; flex:none; }   /* 下に盤面の節が付いても縮めない */
#topo .hint{ color:var(--mute); font-size:12px; margin:0; }
#topo .err{ color:#8a3b12; margin:0; }
#toponotes{ flex:none; height:0; border-top:1px solid var(--line); margin-top:6px; }
#terms{ background:var(--term); }
.term{ padding:6px 4px 4px 8px; box-sizing:border-box; }
#empty{ color:#9aa5b5; display:grid; place-items:center; text-align:center; padding:24px; }
/* トポロジ */
.tl{ stroke:#5b6676; stroke-width:1.6; }
.tlb{ fill:var(--panel); stroke:#cdd3dc; stroke-width:.8; }
.tlt{ font:11px ui-monospace,Consolas,Menlo,monospace; fill:#3b4656; text-anchor:middle; }
.tn{ font:600 14px system-ui,"Segoe UI",sans-serif; fill:var(--ink); text-anchor:middle; pointer-events:none; }
.nd rect{ fill:#f7f8fa; stroke:#2f3b4a; stroke-width:1.6; }
.nd.k-sw rect{ fill:#e9f3ed; } .nd.k-fw rect{ fill:#f7ebe6; }
.nd.k-host rect{ fill:var(--panel); stroke:#5a6472; } .nd.k-infra rect{ fill:#f1efe8; stroke:#9a8e6c; stroke-dasharray:4 3; }
.nd.has-con{ cursor:pointer; outline:none; }
.nd.has-con:hover rect, .nd.has-con:focus-visible rect{ stroke:var(--accent); stroke-width:2.4; }
.nd.cur rect{ stroke:var(--accent); stroke-width:3; }
.st{ fill:#c3cad6; } .st.up{ fill:#1f9d55; }
</style>
</head>
<body>
<section class="half" id="left">
  <nav class="tabs" id="ltabs">
    <button data-tab="task" class="on">Task</button>
    <button data-tab="topo">Topology</button>
    <span class="lab">@@CAPTION@@</span>
  </nav>
  <div class="pane">
    <iframe id="task" src="@@TASK_SRC@@" title="Task"></iframe>
    <div id="topo" hidden></div>
  </div>
</section>
<section class="half" id="right">
  <nav class="tabs" id="ctabs"></nav>
  <div class="pane" id="terms">
    <div id="empty">Select a device tab, or click a node in the topology, to open its console.</div>
  </div>
</section>
<script src="vendor/xterm.js"></script>
<script src="vendor/addon-fit.js"></script>
<script>
"use strict";
const $ = s => document.querySelector(s);
const enc = new TextEncoder();
const Q = location.search.length > 1 ? location.search.slice(1) + '&' : '';   // どのラボかはサーバが決める
const sessions = {};            // ラベル → {label, el, btn, dot, term, fit, ws}
let active = null;

// ---- 左: タスク／トポロジ ----
let notesPending = false;        // 問題文の盤面の節(Topology タブを初めて開いた時に読み込む)
function leftTab(name){
  for (const b of $('#ltabs').querySelectorAll('button')) b.classList.toggle('on', b.dataset.tab === name);
  $('#task').hidden = name !== 'task';
  $('#topo').hidden = name !== 'topo';
  if (name === 'topo' && notesPending){ notesPending = false; addNotes(); }
}
// 結線図の下に、問題文の盤面の節を枠で出す。枠の高さは中身に合わせる(スクロールは Topology タブ 1 本にする)。
// 隠れた枠の中では図(Mermaid)の寸法が取れないので、タブが見えてから読み込む
function addNotes(){
  const f = document.createElement('iframe');
  f.id = 'toponotes'; f.title = 'Topology notes'; f.src = 'toponotes?' + Q;
  f.addEventListener('load', () => {
    const doc = f.contentDocument;
    const fit = () => { f.style.height = doc.documentElement.offsetHeight + 'px'; };
    fit();
    new ResizeObserver(fit).observe(doc.documentElement);
  });
  $('#topo').appendChild(f);
}
$('#ltabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b) leftTab(b.dataset.tab); });

async function loadTopo(){
  const r = await fetch('api/topo?' + Q);
  const t = await r.json();
  if (t.error){
    const p = document.createElement('p'); p.className = 'err'; p.textContent = t.error;
    $('#topo').replaceChildren(p); $('#empty').textContent = t.error;
  } else {
    $('#topo').innerHTML = t.svg + '<p class="hint">Click a device to open its console.</p>';
    for (const n of t.nodes) if (n.console && !sessions[n.label]) addTab(n.label);
    markCurrent();
  }
  if (t.notes){ if ($('#topo').hidden) notesPending = true; else addNotes(); }
}
function nodeOf(e){ const g = e.target.closest('[data-node]'); return g ? g.dataset.node : null; }
$('#topo').addEventListener('click', e => { const n = nodeOf(e); if (n) openConsole(n); });
$('#topo').addEventListener('keydown', e => {
  const n = nodeOf(e); if (n && (e.key === 'Enter' || e.key === ' ')){ e.preventDefault(); openConsole(n); }
});
function markCurrent(){
  for (const g of $('#topo').querySelectorAll('[data-node]')) g.classList.toggle('cur', g.dataset.node === active);
}

// ---- 右: コンソール ----
function addTab(label){
  const btn = document.createElement('button');
  const dot = document.createElement('span'); dot.className = 'dot';
  btn.append(dot, document.createTextNode(label));
  btn.addEventListener('click', () => openConsole(label));
  $('#ctabs').appendChild(btn);
  sessions[label] = {label, btn, dot, el:null, term:null, fit:null, ws:null};
}
function setState(s, st){ s.dot.className = 'dot ' + st; }
// IOS のコンソールは 80 桁で折り返す。幅が足りない画面では 80 桁入るまで字を小さくする
function fitTerm(s){
  for (const size of [14, 13, 12, 11]){
    if (s.term.options.fontSize !== size) s.term.options.fontSize = size;
    s.fit.fit();
    if (s.term.cols >= 80) break;
  }
}

function show(label){
  active = label;
  $('#empty').hidden = true;
  for (const s of Object.values(sessions)){
    s.btn.classList.toggle('on', s.label === label);
    if (s.el) s.el.hidden = s.label !== label;
  }
  markCurrent();
}

function openConsole(label){
  const s = sessions[label];
  if (!s) return;
  if (!s.term){                           // 端末は初めて開いた時に作る(全機器へ一斉には繋がない)
    s.el = document.createElement('div'); s.el.className = 'term';
    $('#terms').appendChild(s.el);
    show(label);                          // 見える状態にしてから open する(隠れた要素では寸法が取れない)
    s.term = new Terminal({
      fontSize:14, fontFamily:'Consolas,"Cascadia Mono",Menlo,"DejaVu Sans Mono",monospace',
      cursorBlink:true, scrollback:20000,
      theme:{background:'#0c0f14', foreground:'#d8dee9', cursor:'#d8dee9', selectionBackground:'#3b5b85'}
    });
    s.fit = new FitAddon.FitAddon();
    s.term.loadAddon(s.fit);
    s.term.open(s.el);
    fitTerm(s);
    s.term.onData(d => {
      if (s.ws && s.ws.readyState === WebSocket.OPEN) s.ws.send(enc.encode(d));
      else if (d === '\r' && (!s.ws || s.ws.readyState === WebSocket.CLOSED)) connect(s);
    });
    s.term.onResize(({cols, rows}) => {
      if (s.ws && s.ws.readyState === WebSocket.OPEN) s.ws.send(JSON.stringify({resize:[cols, rows]}));
    });
    // Ctrl+C は選択があればコピー(無ければ ^C を機器へ)。Ctrl+V はブラウザの貼り付けに任せる
    s.term.attachCustomKeyEventHandler(e => {
      if (e.type !== 'keydown' || !e.ctrlKey || e.altKey) return true;
      const k = e.key.toLowerCase();
      if (k === 'c' && !e.shiftKey && s.term.hasSelection()) return false;
      if (k === 'v') return false;
      return true;
    });
    connect(s);
  } else {
    show(label);
    fitTerm(s);
  }
  s.term.focus();
}

function connect(s){
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const base = location.pathname.replace(/[^/]*$/, '');
  const ws = new WebSocket(`${proto}://${location.host}${base}ws/console?${Q}node=${encodeURIComponent(s.label)}`
                           + `&cols=${s.term.cols}&rows=${s.term.rows}`);
  ws.binaryType = 'arraybuffer';
  s.ws = ws;
  setState(s, 'connecting');
  ws.onopen = () => setState(s, 'on');
  ws.onmessage = e => {
    if (typeof e.data === 'string') s.term.write('\r\n\x1b[33m' + e.data + '\x1b[0m\r\n');
    else s.term.write(new Uint8Array(e.data));
  };
  ws.onclose = () => {
    if (s.ws !== ws) return;
    setState(s, 'off');
    s.term.write('\r\n\x1b[33m[disconnected — press Enter to reconnect]\x1b[0m\r\n');
  };
}

new ResizeObserver(() => {
  const s = sessions[active];
  if (s && s.fit) requestAnimationFrame(() => fitTerm(s));
}).observe($('#terms'));

// Ctrl+W(IOS では単語削除)はブラウザがタブを閉じる。接続中は閉じる前に確認を出す。
// ただし左枠のナビ(Contents・Q 番号)からの移動は意図したものなので確認しない
let leaving = false;
window.addEventListener('beforeunload', e => {
  if (!leaving && Object.values(sessions).some(s => s.ws && s.ws.readyState === WebSocket.OPEN)){
    e.preventDefault(); e.returnValue = '';
  }
});
// 左枠の問題ページのナビが押されたら、画面ごとその行き先へ移る(render_html の NAV_JS が知らせてくる)。
// 枠の中だけで移動させると、Task だけ替わって Topology とコンソールが前の問題のまま残る。
// 受けるのは左枠からの合図だけ・行き先は左枠と同じ配信サーバの中だけ
window.addEventListener('message', ev => {
  const frame = $('#task');
  if (ev.source !== frame.contentWindow || !ev.data || typeof ev.data.ccnpNav !== 'string') return;
  let to;
  try { to = new URL(ev.data.ccnpNav); } catch (_e) { return; }
  if (to.origin !== new URL(frame.src, location.href).origin) return;
  leaving = true;
  location.href = to.href;
});

loadTopo();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--port", type=int, default=8897)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--pack-port", type=int, default=8899,
                    help="パック配信サーバのポート(左のタスクはそこの問題ページを読む)")
    ap.add_argument("--lab", help="単発: この CML ラボ題名に固定する")
    ap.add_argument("--task", help="単発: 左のタブに出すタスクの Markdown")
    ap.add_argument("--with-parent", type=int, metavar="PID",
                    help="この PID の親プロセスが終わったら自分も終わる(pack.sh serve が自分の PID を渡す)")
    a = ap.parse_args()
    if a.task and not os.path.exists(a.task):
        sys.exit(f"--task {a.task} がありません")
    mode = f"単発 lab={a.lab}" if a.lab else "パック常駐"
    ready = f"ラボのワークスペース({mode})を http://{a.bind}:{a.port}/ で待ち受け中"
    try:
        web.run_app(make_app(a.repo, a.pack_port, a.lab, a.task, a.with_parent),
                    host=a.bind, port=a.port,
                    print=lambda *_: print(ready, flush=True))     # 待ち受けに成功してから出す
    except OSError as e:                          # ポート使用中など。長いトレースを出さず 1 行で終わる
        sys.exit(f"ラボのワークスペースを起動できません(ポート {a.port}): {e.strerror or e}")
    if a.with_parent and os.getppid() != a.with_parent:
        print("配信サーバが終了したので、ラボのワークスペースも終了しました", flush=True)


if __name__ == "__main__":
    main()
