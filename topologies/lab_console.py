#!/usr/bin/env python3
"""ラボのワークスペース — ブラウザ 1 画面でラボを解く(BL-234)。

画面: 上= タスク／トポロジ(タブ切替)、下= 機器コンソール(機器ごとのタブ)。左右に並べる形へも切り替えられる。
      画面下端に目次・問番号の帯(パック常駐の時)。境目はドラッグで動かせる。

  ブラウザ(xterm.js) ⇄ WebSocket ⇄ この中継 ⇄ SSH ⇄ CML コンソールサーバ ⇄ ノードのシリアル

動かし方は 2 通り:

  パック常駐(既定)   lab_console.py --repo <リポ> [--port 8897] [--pack-port 8899] [--bind 127.0.0.1]
      `scripts/pack.sh serve` が配信サーバと一緒に起動する。入口はパックのラボページ下端の帯の
      「Open lab workspace」(= 配信サーバの /_lab → ここの /lab?pack=<PACK-ID>&no=<N>)。
      左のタスクはパックの問題ページそのもの(解答欄・ストップウォッチもそのまま使える)。
  単発               lab_console.py --lab <CML のラボ題名> [--task <Task.md>]
      1 ラボに固定して開く(入口は /)。パックを介さない出題や動作確認に使う。
  学習モード         lab_console.py --learn <問題 ID>
      単発の一種。ラボと課題文は問題 ID から決まり(lab/<ID>/Task.md・問題.md)、左に Steps タブが増える。
      課題ごとに 確認(中間チェックを 1 回)・段階式ヒント・模範解(通過後かヒント全開後)。problems/<ID>/learn.yml が中身。

  GET /lab?pack=&no=   … 画面(パック常駐)          GET /       … 画面(単発)
  GET /api/topo        … トポロジ(CML API の座標・リンクから起こした SVG とノード一覧)
  GET /toponotes       … 問題文の盤面の節(トポロジ／構成図)。Topology タブで結線図の下に出す
  GET /ws/console?node=<ラベル>   … そのノードのコンソール(バイト列をそのまま流す)
  GET /task            … タスク(単発のみ。--task の Markdown を問題用紙と同じ体裁で HTML 化)
  GET /api/learn       … 学習モード(単発に --learn <問題 ID>。BL-246)= Steps タブの中身。POST /api/learn/hint・/api/learn/check
                         POST /api/learn/reset= やり直し(XR を構築直後のコミットへ戻し、記録を退避・BL-254)

設計上の約束:
  - **繋げるラボはサーバ側でしか決まらない**。パック常駐ではパックの manifest のラボ項目から
    ラボ題名を導き(問題 ID → CCNP-LAB-<md5 先頭 8 桁>)、単発では --lab の 1 本だけ。
    クライアントからラボ題名は受け取らない。ノード名は CML API の一覧と突き合わせる。
  - コンソールサーバには `open …` を **exec で渡す**。コンソールを抜けると SSH ごと終わるので、
    コンソールサーバのプロンプト(他ラボへ移れる)には降りられない。
  - この中継は CML の認証を肩代わりする。bind の既定は 127.0.0.1。
  - WebSocket は Origin を検査する(別サイトのページからこの中継へ繋がせない)。
  - 機器へは何も打たない(接続時に改行すら送らない)。出題状態を変えるのは受験者の打鍵だけ。
  - コンソールの入出力は records/console/<問題 ID>/<ノード>.jsonl に記録する(BL-243。--no-record で止める)。
    採点後に過程(手数・切り分けの順)を振り返るための材料で、採点には使わない。機器側には何も仕込まない。
    1 行= {"t": UNIX 秒, "c": 接続 ID, "d": "open"/"in"/"out"/"close", "b": バイト列(latin-1 で 1 バイト 1 文字)}。
    "in" は受験者の打鍵だけ(採点のコンソール経路の入力は通らない)。"out" は機器の出力で、同じノードを複数の
    タブで開けば接続ごとに重複し、採点が同時に走ればその出力も混ざる。打鍵にはパスワードも含まれるので
    置き場は git 管理外・ファイルは 0600。記録に失敗してもコンソールは止めない。
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
import tempfile
import time
import uuid
from collections import ChainMap, defaultdict, namedtuple
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
ROUTERS = {"iol-xe", "iosv", "csr1000v", "cat8000v", "iosxrv9000", "xrd", "cat-sdwan-edge"}
SWITCHES = {"ioll2-xe", "iosvl2", "nxosv9000", "cat9000v-q200", "cat9000v-uadp", "vjunos-switch"}
FIREWALLS = {"asav", "fortigate"}
# 貼り付けの流量制御。シリアルコンソールは一度に流し込むと取りこぼす
#   実測(IOL・200 行 9.7KB): 1 フレーム一括= 約 40 行で崩れる／行ごとに 3〜30ms 空ける= 200/200 行
PASTE_MIN = 64          # これを超える入力は貼り付けとみなす(打鍵は 1〜数バイト)
PASTE_GAP = 0.01        # 行間の待ち(秒)
IF_ABBR = (("TenGigabitEthernet", "Te"), ("GigabitEthernet", "Gi"), ("FastEthernet", "Fa"),
           ("Ethernet", "Et"), ("Loopback", "Lo"), ("Management", "Mg"))

# 繋ぐ先: CML のラボ題名・タスクの URL・画面の見出し・盤面の節のページ(パックの q<N>.topo.html。無ければ None)・
#         画面下端の帯に出すリンク [(表示, 行き先, 今ここか)](単発では空)
#         操作記録のフォルダ名(パックでは問題 ID・単発ではラボ題名)
Target = namedtuple("Target", "title task_src caption notes nav rec")


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
LEARN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def _view(request):
    """リクエストから見た app。パック常駐で `?learn=<問題 ID>` が付いていれば、そのラボに固定した単発と同じ見え方を
    重ねて返す(ポータルの教材から開く学習モード・BL-247)。それ以外は app そのもの。
    問題 ID は書式を検査し、problems/<ID>/learn.yml がある問題だけを通す(繋ぐラボはここでしか決まらない)。"""
    app = request.app
    if app["fixed"]:
        return app
    lid = request.query.get("learn", "")
    if not LEARN_RE.match(lid) or not os.path.exists(os.path.join(app["repo"], "problems", lid, "learn.yml")):
        return app
    task = None
    for cand in ("Task.md", "問題.md"):                 # lab.sh provision が置く作業コピー(英語版が既定)
        path = os.path.join(app["repo"], "lab", lid, cand)
        if os.path.exists(path):
            task = path
            break
    host = request.url.host or "localhost"
    if ":" in host:
        host = f"[{host}]"
    nav = [("‹ Portal", f"{request.scheme}://{host}:{app['pack_port']}/", False), (lid, "", True)]
    tgt = Target(lab_title(lid), "task?learn=" + lid, lid, None, nav, lid)
    return ChainMap({"fixed": tgt, "task": task, "learn": lid}, app)


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
    items = gen_pack.read_manifest(pdir)["items"]
    it = next((i for i in items
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
    base = f"{request.scheme}://{host}:{app['pack_port']}/{pack}/"
    # 画面下端の帯: 目次と各問。ラボはこのワークスペースの中で開き、紙面は配信サーバの問題ページへ出る
    nav = [("‹ Packs", f"{request.scheme}://{host}:{app['pack_port']}/", False),   # パック一覧へ戻る
           ("Contents", base + "index.html", False)]
    for i in items:
        built_lab = i.get("kind") == "lab" and i.get("ref") and i.get("src")
        nav.append((f"Q{i['no']}", f"lab?pack={pack}&no={i['no']}" if built_lab else base + f"q{i['no']}.html",
                    i["no"] == n))
    return Target(lab_title(it["ref"]), base + page, f"{pack} · Q{n}",
                  notes if os.path.exists(notes) else None, nav, it["ref"])


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
    tgt = resolve(_view(request), request)
    if tgt is None:
        return web.Response(status=404, content_type="text/html", text=(
            "<p>No such lab. Open a lab page of a pack and use <b>Open lab workspace</b>.</p>"))
    nav = '<span class="dotsep">·</span>'.join(
        f'<span class="cur">{html.escape(label)}</span>' if cur else
        f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        for label, href, cur in tgt.nav)
    page = (PAGE.replace("@@CAPTION@@", html.escape(tgt.caption))
            .replace("@@TASK_SRC@@", html.escape(tgt.task_src, quote=True))
            .replace("@@NAV@@", nav)
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


# 単発: 英語版 Task.md と日本語版 問題.md が同じフォルダに並んでいれば(lab.sh と出題者が置く形)、2 版で出す
_PAIR = {"Task.md": ("en", "ja", "問題.md"), "問題.md": ("ja", "en", "Task.md")}


def _single_alt(app):
    """単発: 切替先の版を (既定の言語, 切替先の言語, 本文, 盤面の節) で返す。相方のファイルが無ければ None。"""
    if not app["task"]:
        return None
    d, name = os.path.split(os.path.abspath(app["task"]))
    pair = _PAIR.get(name)
    if not pair or not os.path.exists(os.path.join(d, pair[2])):
        return None
    with open(os.path.join(d, pair[2]), encoding="utf-8") as fh:
        full = fh.read()
    with open(app["task"], encoding="utf-8") as fh:
        rest, topo = render_html.split_topology(full, like=fh.read())
    if not _single_task(app)[1]:              # 既定の版に盤面の節が無い= 切替先も全文のまま Task に出す
        rest, topo = full, ""
    return pair[0], pair[1], rest, topo


def _alt_kw(app, part):
    """render_html.render へ渡す 2 版ぶんの引数(part= 2: 本文 / 3: 盤面の節)。切替先が無ければ空。"""
    alt = _single_alt(app)
    if not alt or not alt[part]:
        return {}
    return {"lang": alt[0], "alt_lang": alt[1], "alt_md": alt[part]}


async def h_task(request):
    app = _view(request)
    if not app["fixed"]:
        return web.Response(status=404, text="not found")
    rest, _topo = _single_task(app)
    return web.Response(text=render_html.render(rest, title=app["fixed"].caption,
                                                **_alt_kw(app, 2)),
                        content_type="text/html")


def _has_notes(app, tgt):
    return bool(_single_task(app)[1]) if app["fixed"] else tgt.notes is not None


async def h_toponotes(request):
    """問題文の盤面の節だけのページ。Topology タブが結線図の下に枠で読み込む。"""
    app = _view(request)
    tgt = resolve(app, request)
    if tgt is None or not _has_notes(app, tgt):
        return web.Response(status=404, text="no topology section")
    if app["fixed"]:
        text = render_html.render(_single_task(app)[1], title=f"{tgt.caption} — Topology",
                                  **_alt_kw(app, 3))
    else:
        with open(tgt.notes, encoding="utf-8") as fh:
            text = fh.read()
    return web.Response(text=text, content_type="text/html", headers={"Cache-Control": "no-store"})


async def h_topo(request):
    app = _view(request)
    tgt = resolve(app, request)
    if tgt is None:
        return web.json_response({"error": "no such lab"}, status=404)
    notes = _has_notes(app, tgt)              # 結線図が出せない時も、問題文の盤面の節は読めるようにする
    try:
        model = await load_topo(app, tgt.title)
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


class Recorder:
    """コンソール 1 接続ぶんの入出力を追記する(BL-243)。書式はモジュール冒頭の「設計上の約束」。

    記録は振り返りの材料であって、コンソールの動作に必須ではない。開けない・書けない時は黙って止める。
    """

    def __init__(self, root, key, node):
        self.fh, self.conn = None, uuid.uuid4().hex[:8]
        if not root:
            return
        safe = lambda s: re.sub(r"[^A-Za-z0-9_.-]", "_", s) or "_"   # noqa: E731
        try:
            d = os.path.join(root, safe(key))
            os.makedirs(d, exist_ok=True)
            fd = os.open(os.path.join(d, safe(node) + ".jsonl"),
                         os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            self.fh = os.fdopen(fd, "a", encoding="ascii", buffering=1)
        except OSError:
            self.fh = None

    def write(self, kind, data=b""):
        if self.fh is None:
            return
        try:
            self.fh.write(json.dumps({"t": round(time.time(), 3), "c": self.conn, "d": kind,
                                      "b": data.decode("latin-1")}) + "\n")
        except (OSError, ValueError):
            self.close()

    def close(self):
        if self.fh is not None:
            try:
                self.fh.close()
            except OSError:
                pass
            self.fh = None


async def h_console(request):
    app = _view(request)
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

    rec = Recorder(app["record"], tgt.rec, node)
    rec.write("open")

    async def ssh_to_ws():
        while True:
            data = await proc.stdout.read(65536)
            if not data:
                break
            rec.write("out", data)
            await ws.send_bytes(data)

    async def ws_to_ssh():
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                rec.write("in", msg.data)
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
        rec.write("close")
        rec.close()
        conn.close()
        if not ws.closed:
            await ws.close(message=b"console closed")
    return ws


# --------------------------------------------------------------------------
# 学習モード(BL-246): 課題ごとの確認・段階式ヒント・通過後の模範解
# --------------------------------------------------------------------------
#   単発で `--learn <問題 ID>` を付けると、左に Steps タブが出る。中身は problems/<ID>/learn.yml:
#     steps:
#       - id: m0t1
#         title: {en: "...", ja: "..."}
#         check: m0t1              # 中間チェック problems/<ID>/grading.m0t1.yml(無ければ確認ボタンなし)
#         hints: [{en: "...", ja: "..."}, ...]     # 上から順に 1 段ずつ開く
#         solution: {en: "...", ja: "..."}         # 確認を通過するか、ヒントを全部開いた後に見せる
#         read: [20-m2-management-plane#s1]        # この課題の背景の節(BL-252)。「ページ#節」(節= 読み物の data-sec)
#     reading: xr                  # Reading タブに出す読み物(reading/<key>/)。無ければ Reading タブは出ない
#   ヒントの本文と模範解はサーバが持ち、開いた分だけ返す(ページの中に先に入れない)。
#   開封と確認の結果は records/learn/<問題 ID>.jsonl に残す(ノルマには数えない)。
#   確認は既存の採点(grade.yml の checkpoint)を 1 回だけ回す。同時に 1 本(コンソールでなく管理 IF 経由)。
def _learn_load(app):
    with open(os.path.join(app["repo"], "problems", app["learn"], "learn.yml"), encoding="utf-8") as fh:
        return (yaml.safe_load(fh) or {}).get("steps") or []


def _learn_log_path(app):
    return os.path.join(app["repo"], "records", "learn", app["learn"] + ".jsonl")


def _learn_events(app):
    try:
        with open(_learn_log_path(app), encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh if ln.strip()]
    except FileNotFoundError:
        return []


def _learn_log(app, **ev):
    path = _learn_log_path(app)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(ev, t=int(time.time())), ensure_ascii=False) + "\n")


def _learn_view(app):
    """画面へ渡す状態。ヒントは開いた段まで、模範解は 通過済み か ヒント全開 の時だけ入れる。"""
    opened, passed, last = defaultdict(int), set(), {}
    for ev in _learn_events(app):
        if ev.get("ev") == "hint":
            opened[ev["step"]] = max(opened[ev["step"]], ev["level"])
        elif ev.get("ev") == "check":
            last[ev["step"]] = {"ok": ev["ok"], "lines": ev.get("lines", []), "t": ev["t"]}
            if ev["ok"]:
                passed.add(ev["step"])
    out = []
    for st in _learn_load(app):
        sid, hints = st["id"], st.get("hints") or []
        n = min(opened[sid], len(hints))
        done = sid in passed
        show_sol = bool(st.get("solution")) and (done or (hints and n >= len(hints)) or not st.get("check"))
        out.append({"id": sid, "title": st.get("title") or {}, "check": bool(st.get("check")),
                    "hints_total": len(hints), "hints": hints[:n], "passed": done,
                    "last": last.get(sid), "solution": st.get("solution") if show_sol else None,
                    "has_solution": bool(st.get("solution"))})
    return out


_TASK_HEAD = re.compile(r"^### (?:Task|課題) M(\d+)-(\d+)\b.*$", re.M)
_UNIT_HEAD = re.compile(r"^## (M(\d+)\b.*)$", re.M)


def _learn_texts(app):
    """課題カード(BL-255)に入れる課題文。問題文(lab/<ID>/Task.md と 問題.md)を見出しで切り分けて HTML にする。
      rules: 冒頭(題名の下の前置きと「## 単元」以外の節。盤面の節は Topology タブにあるので除く)
      units: {"m2": {title, intro}}  … 「## M2 …」の見出しと、最初の課題までの前置き
      tasks: {"m2t1": 本文}         … 「### Task M2-1」「### 課題 M2-1」から次の見出しまで(見出しの行は除く)
    値はどれも {言語: HTML}。課題 ID は learn.yml の規約(M2-1 → m2t1)。"""
    files = {}
    if app["task"]:
        alt = _single_alt(app)
        d, name = os.path.split(os.path.abspath(app["task"]))
        own = _PAIR.get(name, ("en",))[0]
        files[own] = app["task"]
        if alt:
            files[alt[1]] = os.path.join(d, _PAIR[name][2])
    out = {"rules": {}, "units": {}, "tasks": {}}
    html_ = lambda md: render_html.md_to_body(md, allow_html=True)[0] if md.strip() else ""
    for lang, path in files.items():
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        parts = re.split(r"(?m)^(?=## )", text)
        head = re.sub(r"(?m)^# .*\n?", "", parts[0], count=1)
        rules = [head]
        for part in parts[1:]:
            um = _UNIT_HEAD.match(part)
            if not um:
                if not re.match(r"## (Topology|トポロジ)", part):
                    rules.append(part)
                continue
            uid = f"m{um.group(2)}"
            body = part[um.end():]
            first = _TASK_HEAD.search(body)
            u = out["units"].setdefault(uid, {"title": {}, "intro": {}})
            u["title"][lang] = um.group(1).strip()
            u["intro"][lang] = html_(body[:first.start()] if first else body)
            heads = list(_TASK_HEAD.finditer(body))
            for k, m in enumerate(heads):
                end = heads[k + 1].start() if k + 1 < len(heads) else len(body)
                out["tasks"].setdefault(f"m{m.group(1)}t{m.group(2)}", {})[lang] = html_(body[m.end():end])
        out["rules"][lang] = html_("\n".join(rules))
    return out


def _learn_reading(app, request):
    """Reading タブ(BL-252)。learn.yml の reading:(本の key)と各課題の read:(「ページ#節」)を、
    パック配信サーバの読み物の URL と見出しの文字に解く。見出しは読み物の出力 reading/<key>/book.json から。
    (None, {}, {}) = 読み物なし。3 つ目は課題ごとの「やってみる」の一覧。"""
    with open(os.path.join(app["repo"], "problems", app["learn"], "learn.yml"), encoding="utf-8") as fh:
        spec = yaml.safe_load(fh) or {}
    key = spec.get("reading")
    if not key or not LEARN_RE.match(str(key)):
        return None, {}, {}
    try:
        with open(os.path.join(app["repo"], "reading", key, "book.json"), encoding="utf-8") as fh:
            book = json.load(fh)
    except (OSError, ValueError):
        return None, {}, {}
    host = request.url.host or "localhost"
    if ":" in host:
        host = f"[{host}]"
    base = f"{request.scheme}://{host}:{app['pack_port']}/_read/{key}/"
    secs, titles = book.get("sections") or {}, book.get("page_titles") or {}
    tries = book.get("tries") or {}
    refs, step_tries = {}, {}
    for st in spec.get("steps") or []:
        out, tout, seen = [], [], set()
        for ref in st.get("read") or []:
            page, _, sec = str(ref).partition("#")
            page = page if page.endswith(".html") else page + ".html"
            if page not in titles:
                continue
            out.append({"href": base + page + (f"#{sec}" if sec else ""),
                        "page": titles[page], "sec": (secs.get(page) or {}).get(sec) or {}})
            # その節(h2 を指していれば配下の h3 も)にある「やってみる」。課題カードのボタンから小窓で出す
            for k, items in (tries.get(page) or {}).items():
                if sec and k != sec and not k.startswith(sec + "-"):
                    continue
                for n, item in enumerate(items):
                    if (page, k, n) in seen:
                        continue
                    seen.add((page, k, n))
                    tout.append({"href": base + page + f"#{k}", "page": titles[page],
                                 "sec": (secs.get(page) or {}).get(k) or {},
                                 "html": {lang: _abs_links(h, base) for lang, h in item.items()}})
        refs[st["id"]] = out
        step_tries[st["id"]] = tout
    return {"href": base + "index.html", "base": base}, refs, step_tries


def _abs_links(fragment, base):
    """読み物の中の相対リンク(同じ本の別ページ)を、ワークスペースから開ける絶対 URL にする。"""
    return re.sub(r'(href|src)="(?![a-z]+:|/|#)([^"]+)"', lambda m: f'{m.group(1)}="{base}{m.group(2)}"', fragment)


async def h_learn_readstamp(request):
    """Reading タブが、開いている読み物のページがビルドし直されたかを知るための更新時刻(2026-10-24)。
    同じページの別の節へは枠を読み直さずに送るので、これが無いと開いたままの古いページが表示され続ける。"""
    app = _view(request)
    page = request.query.get("page", "")
    if not app["learn"] or not re.fullmatch(r"[\w.-]+\.html", page):
        return web.json_response({"mtime": 0})
    with open(os.path.join(app["repo"], "problems", app["learn"], "learn.yml"), encoding="utf-8") as fh:
        key = (yaml.safe_load(fh) or {}).get("reading")
    if not key or not LEARN_RE.match(str(key)):
        return web.json_response({"mtime": 0})
    try:
        mt = os.stat(os.path.join(app["repo"], "reading", key, page)).st_mtime
    except OSError:
        mt = 0
    return web.json_response({"mtime": mt}, headers={"Cache-Control": "no-store"})


async def h_learn(request):
    app = _view(request)
    if not app["learn"]:
        return web.json_response({"enabled": False})
    reading, refs, tries = _learn_reading(app, request)
    texts = _learn_texts(app)
    steps = _learn_view(app)
    for v in steps:
        v["read"] = refs.get(v["id"], [])
        v["tries"] = tries.get(v["id"], [])
        v["task"] = texts["tasks"].get(v["id"], {})
        m = re.match(r"(m\d+)t", v["id"])
        v["unit"] = m.group(1) if m else ""
    return web.json_response({"enabled": True, "steps": steps, "reading": reading,
                              "rules": texts["rules"], "units": texts["units"]},
                             headers={"Cache-Control": "no-store"})


async def h_learn_hint(request):
    app = _view(request)
    if not app["learn"] or not _same_origin(request):
        return web.Response(status=403, text="forbidden")
    sid = (await request.json()).get("step")
    st = next((x for x in _learn_load(app) if x["id"] == sid), None)
    if st is None:
        return web.Response(status=404, text="no such step")
    cur = next((v["hints"] for v in _learn_view(app) if v["id"] == sid), [])
    if len(cur) < len(st.get("hints") or []):
        _learn_log(app, ev="hint", step=sid, level=len(cur) + 1)
    return web.json_response({"enabled": True, "steps": _learn_view(app)})


_REPORT_LINE = re.compile(r"^\s*-?\s*'?\s*(\[(?:PASS|FAIL)\].*?|未充足:.*?|合計:.*?)'?\s*$")


async def h_learn_check(request):
    app = _view(request)
    if not app["learn"] or not _same_origin(request):
        return web.Response(status=403, text="forbidden")
    sid = (await request.json()).get("step")
    st = next((x for x in _learn_load(app) if x["id"] == sid), None)
    if st is None or not st.get("check"):
        return web.Response(status=404, text="no such check")
    name = str(st["check"])
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return web.Response(status=400, text="bad check name")
    if app["learn_lock"].locked():
        return web.json_response({"busy": True})
    async with app["learn_lock"]:
        repo = app["repo"]
        # vault のパスワード(lab.sh と同じ規約の値)は、プロセス置換の代わりに一時ファイルで渡して終わったら消す
        fd, vault = tempfile.mkstemp(prefix="ccnp-learn-")
        os.write(fd, b"CCNP\n")
        os.close(fd)
        proc = await asyncio.create_subprocess_exec(
            os.path.join(repo, ".venv/bin/ansible-playbook"), os.path.join(repo, "playbooks/grade.yml"),
            "-e", f"problem={app['learn']}", "-e", f"checkpoint={name}", "-e", "max_attempts=1",
            "--vault-password-file", vault,
            cwd=repo, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        try:
            raw, _ = await asyncio.wait_for(proc.communicate(), timeout=240)
        except asyncio.TimeoutError:
            proc.kill()
            return web.json_response({"error": "check timed out"})
        finally:
            os.unlink(vault)
        text = raw.decode("utf-8", "replace")
        # 最終結果の節だけを読む(途中の試行の表示と重ならないように)
        tail = text[text.rfind("TASK [最終結果]"):] if "TASK [最終結果]" in text else text
        lines = [m.group(1).strip() for m in map(_REPORT_LINE.match, tail.splitlines()) if m]
        # 画面は英語が基本なので、採点の表示から日本語の飾りを落とす(配点・合計は出さない= 通ったかどうかだけ)
        lines = [re.sub(r"^(\[(?:PASS|FAIL)\]) \(\+\s*\d+ 点\) ", r"\1 ", ln).replace("未充足(raw):", "unmet:").replace("未充足:", "unmet:")
                 for ln in lines if not ln.startswith("合計:")]
        ok = "全チェック PASS で収束" in text
        if not lines:
            lines = ["(no result — the check could not run; see the server log)"]
            print(text[-1500:], flush=True)
        _learn_log(app, ev="check", step=sid, ok=ok, lines=lines)
    return web.json_response({"enabled": True, "steps": _learn_view(app)})


async def h_learn_reset(request):
    """やり直し(BL-254)。IOS XR の機器を構築直後のコミットへ戻し(playbooks/xr_reset.yml)、学習モードの記録を退避して初期化する。
    戻せなかった時は記録に触らない(機器と表示が食い違わないように)。"""
    app = _view(request)
    if not app["learn"] or not _same_origin(request):
        return web.Response(status=403, text="forbidden")
    if app["learn_lock"].locked():
        return web.json_response({"busy": True})
    async with app["learn_lock"]:
        repo = app["repo"]
        fd, vault = tempfile.mkstemp(prefix="ccnp-learn-")
        os.write(fd, b"CCNP\n")
        os.close(fd)
        proc = await asyncio.create_subprocess_exec(
            os.path.join(repo, ".venv/bin/ansible-playbook"), os.path.join(repo, "playbooks/xr_reset.yml"),
            "-e", f"problem={app['learn']}", "--vault-password-file", vault,
            cwd=repo, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        try:
            raw, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()
            return web.json_response({"error": "reset timed out"})
        finally:
            os.unlink(vault)
        text = raw.decode("utf-8", "replace")
        if proc.returncode != 0:
            print(text[-2000:], flush=True)
            msgs = re.findall(r'"(ERROR [^"]+)"', text)
            return web.json_response({"error": "The lab could not be reset. " + (" / ".join(msgs) or "See the server log.")})
        log = _learn_log_path(app)
        if os.path.exists(log):
            os.replace(log, log[:-len(".jsonl")] + time.strftime(".%Y%m%d-%H%M%S") + ".jsonl.bak")
    return web.json_response({"enabled": True, "steps": _learn_view(app), "reset": True})


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


def make_app(repo=REPO, pack_port=8899, lab=None, task=None, with_parent=None, record=True, learn=None):
    """lab を渡すと単発(そのラボに固定)、渡さなければパック常駐。"""
    app = web.Application()
    if with_parent:
        app["with_parent"] = with_parent
        app.on_startup.append(_follow_parent)
    app["fixed"] = Target(lab, "task", learn or lab, None, [], learn or lab) if lab else None
    app["task"] = task
    app["repo"] = os.path.abspath(repo)
    app["learn"] = learn                      # 学習モードの問題 ID(単発のみ)
    app["learn_lock"] = asyncio.Lock()
    app["packs"] = os.path.join(os.path.abspath(repo), "packs")
    app["pack_port"] = pack_port
    # コンソールの操作記録の置き場(BL-243)。None = 記録しない
    app["record"] = os.path.join(os.path.abspath(repo), "records", "console") if record else None
    app["cml"] = load_cml()
    app["nodes"] = {}                         # ラボ題名 → コンソールを開いてよいノード名の集合
    app.router.add_get("/", h_root)
    app.router.add_get("/lab", h_page)
    app.router.add_get("/task", h_task)
    app.router.add_get("/api/topo", h_topo)
    app.router.add_get("/toponotes", h_toponotes)
    app.router.add_get("/ws/console", h_console)
    app.router.add_get("/api/learn", h_learn)
    app.router.add_post("/api/learn/hint", h_learn_hint)
    app.router.add_post("/api/learn/check", h_learn_check)
    app.router.add_post("/api/learn/reset", h_learn_reset)
    app.router.add_get("/api/learn/readstamp", h_learn_readstamp)
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
      display:flex; flex-direction:column; height:100vh; overflow:hidden; }
/* 並べ方: 既定は上下(上= Task/Topology・下= コンソール)。body.side で左右。境目はドラッグで動かす・ダブルクリックで既定へ */
#ws{ flex:1; min-height:0; display:grid; grid-template-columns:minmax(0,1fr);
     grid-template-rows:minmax(0,var(--split-v,45%)) 7px minmax(0,1fr); }
body.side #ws{ grid-template-rows:minmax(0,1fr); grid-template-columns:minmax(0,var(--split,50%)) 7px minmax(0,1fr); }
.half{ display:flex; flex-direction:column; min-width:0; min-height:0; }
#split{ background:#cfd4db; cursor:row-resize; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
body.side #split{ cursor:col-resize; border:0; border-left:1px solid var(--line); border-right:1px solid var(--line); }
#split:hover, body.dragging #split{ background:var(--accent); }
#dragshield{ position:fixed; inset:0; z-index:50; cursor:row-resize; }   /* ドラッグ中、枠(iframe)に操作を取られない覆い */
body.side #dragshield{ cursor:col-resize; }
/* 画面下端の帯: 目次・問番号(問題ページのナビ帯と同じ役目)。コンソールや Task のタブから離して置く */
#foot{ flex:none; display:flex; align-items:center; gap:.9rem; padding:5px 14px; font-size:13px;
       border-top:1px solid #000; background:var(--paper); white-space:nowrap; overflow-x:auto; }
#foot a{ color:#0645ad; } #foot .cur, #foot .dotsep{ color:#555; } #foot .sp{ flex:1; }
#foot button{ font:inherit; font-size:12px; color:var(--mute); background:none; border:1px solid var(--line);
              border-radius:4px; padding:2px 8px; cursor:pointer; }
#foot button:hover{ color:var(--ink); background:#dfe2e7; }
#foot .fz{ display:flex; align-items:center; gap:5px; font-size:12px; color:var(--mute); }
#foot #fsize{ min-width:2.6em; text-align:center; font-variant-numeric:tabular-nums; }
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
/* 学習モードの Steps タブ(BL-246): 課題ごとの確認・段階式ヒント・模範解 */
#steps{ overflow:auto; padding:12px 16px; box-sizing:border-box; }
#steps .note{ color:var(--mute); font-size:12px; margin:0 0 10px; }
#steps h2.unit{ font-size:15px; margin:18px 0 8px; padding:0 0 4px; border-bottom:2px solid var(--line); }
#steps .ttext{ font-size:13px; line-height:1.6; margin:4px 0 8px; }
#steps .ttext p{ margin:6px 0; } #steps .ttext ul, #steps .ttext ol{ margin:6px 0; padding-left:20px; } #steps .ttext li{ margin:3px 0; }
#steps .ttext code{ font-family:ui-monospace,Consolas,Menlo,monospace; font-size:12px; background:#eef0f3; padding:0 3px; border-radius:3px; }
#steps .ttext pre{ background:#eef0f3; padding:6px 8px; overflow:auto; }
#steps .ttext table{ border-collapse:collapse; font-size:12px; } #steps .ttext th, #steps .ttext td{ border:1px solid var(--line); padding:2px 6px; }
#steps .ttext h2{ font-size:13.5px; margin:10px 0 4px; }
#steps .unitintro{ color:var(--ink); }
#steps details.rules{ border:1px solid var(--line); border-radius:6px; background:var(--panel); margin:0 0 10px; padding:6px 12px; }
#steps details.rules summary{ cursor:pointer; font-weight:600; font-size:13px; }
.stepsbar{ display:flex; gap:12px; align-items:flex-start; margin:0 0 10px; }
.stepsbar .note{ flex:1; margin:0; }
.stepsbar .reset{ flex:none; font:inherit; font-size:12px; border:1px solid #c9a3a0; border-radius:4px; background:#fff;
                  color:#8a2b22; padding:3px 10px; cursor:pointer; }
.stepsbar .reset:hover:not(:disabled){ background:#fbefee; } .stepsbar .reset:disabled{ opacity:.5; cursor:default; }
.step{ border:1px solid var(--line); border-radius:6px; background:var(--panel); margin:0 0 10px; padding:9px 12px; }
.step h3{ margin:0 0 6px; font-size:14px; display:flex; align-items:center; gap:8px; }
.step h3 .badge{ font-size:11px; font-weight:600; border-radius:10px; padding:1px 8px; background:#dfe2e7; color:var(--mute); }
.step.ok h3 .badge{ background:#d6eedd; color:#17643a; } .step.ng h3 .badge{ background:#f6ddd9; color:#8a2b22; }
.step .row{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.step button{ font:inherit; font-size:12px; border:1px solid var(--line); border-radius:4px; background:#fff;
              padding:3px 10px; cursor:pointer; color:var(--ink); }
.step button:hover:not(:disabled){ background:#eef1f5; } .step button:disabled{ opacity:.5; cursor:default; }
.step button.go{ border-color:var(--accent); color:var(--accent); font-weight:600; }
.step .res, .step .hint, .step .sol{ margin:8px 0 0; font-size:12.5px; }
.step .res div{ font-family:ui-monospace,Consolas,Menlo,monospace; white-space:pre-wrap; }
.step .res .p{ color:#17643a; } .step .res .f{ color:#8a2b22; } .step .res .u{ color:var(--mute); padding-left:1.5em; }
.step .hint, .step .sol{ border-left:3px solid #c9a227; padding:3px 0 3px 9px; white-space:pre-wrap; }
.step .sol{ border-left-color:#1f9d55; font-family:ui-monospace,Consolas,Menlo,monospace; }
.step .read{ margin:7px 0 0; font-size:12.5px; display:flex; gap:4px 12px; flex-wrap:wrap; align-items:baseline; }
.step .read .lbl{ display:inline; }
.step .read a{ color:var(--accent); text-decoration:none; cursor:pointer; } .step .read a:hover{ text-decoration:underline; }
.step.flash{ box-shadow:0 0 0 2px var(--accent); transition:box-shadow .3s; }
.step .lbl{ font-weight:600; color:var(--mute); font-size:11px; display:block; font-family:system-ui,sans-serif; }
.step button.try{ border-color:#3f8f4f; color:#2f6f3c; }
/* 「やってみる」の小窓(2026-10-24): 課題カードのボタンで開く。モーダルにしない= 開いたままコンソールに打てる。
   見出しをつかんで動かす・最小化・閉じる。位置は端末ごとに覚える(localStorage) */
#trypanel{ position:fixed; z-index:40; width:min(440px, calc(100vw - 24px)); max-height:min(70vh, 640px);
           display:flex; flex-direction:column; background:#fff; border:1px solid #3f8f4f; border-radius:6px;
           box-shadow:0 8px 28px rgba(0,0,0,.25); font-size:13px; }
#trypanel .tph{ flex:none; display:flex; align-items:center; gap:8px; padding:6px 8px 6px 12px; background:#eef8ef;
                border-bottom:1px solid #cfe5d3; border-radius:6px 6px 0 0; cursor:move; user-select:none; touch-action:none; }
#trypanel .tph b{ flex:1; color:#2f6f3c; font-size:13px; }
#trypanel .tph button{ font:inherit; font-size:12px; border:1px solid #cfe5d3; background:#fff; border-radius:4px;
                       padding:1px 8px; cursor:pointer; color:var(--ink); }
#trypanel .tpb{ overflow:auto; padding:8px 14px 12px; line-height:1.6; }
#trypanel.min .tpb{ display:none; }
#trypanel .tpi + .tpi{ border-top:1px solid var(--line); margin-top:10px; padding-top:6px; }
#trypanel .tps{ font-size:11.5px; color:var(--mute); margin:2px 0 4px; }
#trypanel .tps a{ color:var(--accent); cursor:pointer; }
#trypanel p{ margin:6px 0; } #trypanel ol, #trypanel ul{ margin:6px 0; padding-left:20px; } #trypanel li{ margin:4px 0; }
#trypanel code{ font-family:ui-monospace,Consolas,Menlo,monospace; font-size:12px; background:#eef0f3; padding:0 3px; border-radius:3px; }
#trypanel pre{ background:#eef0f3; padding:6px 8px; overflow:auto; }
#terms{ background:var(--term); }
/* 余白は .term に持たせ、端末は余白なしの .xt に開く。fit(桁・行の計算)は端末の親の寸法を読むので、
   親に余白があるとその分だけ広く見積もり、右端の桁と最下行が隠れる(2026-10-07 実発) */
.term{ padding:6px 4px 4px 8px; box-sizing:border-box; }
.term .xt{ width:100%; height:100%; }
.xterm .xterm-viewport{ scrollbar-width:thin; scrollbar-color:#3a4250 var(--term); }
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
<div id="ws">
<section class="half" id="left">
  <nav class="tabs" id="ltabs">
    <button data-tab="task" class="on">Task</button>
    <button data-tab="topo">Topology</button>
    <button data-tab="steps" id="stepsbtn" hidden>Steps</button>
    <button data-tab="read" id="readbtn" hidden>Reading</button>
    <span class="lab">@@CAPTION@@</span>
  </nav>
  <div class="pane">
    <iframe id="task" src="@@TASK_SRC@@" title="Task"></iframe>
    <div id="topo" hidden></div>
    <div id="steps" hidden></div>
    <iframe id="reading" title="Reading" hidden></iframe>
  </div>
</section>
<div id="split" title="Drag to resize · double-click to reset"></div>
<section class="half" id="right">
  <nav class="tabs" id="ctabs"></nav>
  <div class="pane" id="terms">
    <div id="empty">Select a device tab, or click a node in the topology, to open its console.</div>
  </div>
</section>
</div>
<footer id="foot">@@NAV@@<span class="sp"></span>
  <span class="fz">Console text
    <button type="button" id="fminus" title="Smaller console text">A−</button><span id="fsize" title="Double-click: default size"></span><button type="button" id="fplus" title="Larger console text">A+</button>
  </span>
  <button type="button" id="lang" hidden title="Switch the task text between English and Japanese"></button>
  <button type="button" id="layout"></button></footer>
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
  $('#steps').hidden = name !== 'steps';
  $('#reading').hidden = name !== 'read';
  if (name === 'read' && !$('#reading').getAttribute('src') && learnReading) openReading(defaultReading(), false);
  else if (name === 'read') refreshReading();
  if (name === 'topo' && notesPending){ notesPending = false; addNotes(); }
}
// 結線図の下に、問題文の盤面の節を枠で出す。枠の高さは中身に合わせる(スクロールは Topology タブ 1 本にする)。
// 隠れた枠の中では図(Mermaid)の寸法が取れないので、タブが見えてから読み込む
function addNotes(){
  const f = document.createElement('iframe');
  f.id = 'toponotes'; f.title = 'Topology notes'; f.src = 'toponotes?' + Q;
  f.addEventListener('load', () => {
    const doc = f.contentDocument;
    doc.documentElement.style.overflow = 'hidden';      // スクロールは Topology タブ側の 1 本だけにする
    let last = -1;
    const fit = () => {
      const h = Math.ceil(Math.max(doc.documentElement.getBoundingClientRect().height, doc.body.scrollHeight)) + 8;
      if (h !== last){ last = h; f.style.height = h + 'px'; }
    };
    fit();
    new ResizeObserver(fit).observe(doc.body);
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
// コンソールの字の大きさ。既定は 10px(2026-10-07 ユーザ指示)。画面下端の A− / A+ で変えた大きさは覚えておく
const FONT_DEFAULT = 10;
let fontPref = FONT_DEFAULT;
try { const v = parseInt(localStorage.getItem('ccnp-ws-font'), 10); if (v >= 7 && v <= 22) fontPref = v; } catch (_e) {}
function fitTerm(s){
  if (s.term.options.fontSize !== fontPref) s.term.options.fontSize = fontPref;
  s.fit.fit();
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
    const xt = document.createElement('div'); xt.className = 'xt'; s.el.appendChild(xt);
    $('#terms').appendChild(s.el);
    show(label);                          // 見える状態にしてから open する(隠れた要素では寸法が取れない)
    s.term = new Terminal({
      fontSize:fontPref, fontFamily:'Consolas,"Cascadia Mono",Menlo,"DejaVu Sans Mono",monospace',
      cursorBlink:true, scrollback:20000,
      theme:{background:'#0c0f14', foreground:'#d8dee9', cursor:'#d8dee9', selectionBackground:'#3b5b85'}
    });
    s.fit = new FitAddon.FitAddon();
    s.term.loadAddon(s.fit);
    s.term.open(xt);
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

// ---- 並べ方(上下／左右)と境目のドラッグ。どちらも覚えておく ----
//   既定は上下(上= Task/Topology・下= コンソール)。コンソールが画面の幅いっぱいになり、IOS の広い表が折り返さない
(function(){
  const bar = $('#split'), ws = $('#ws'), btn = $('#layout');
  const K = {layout: 'ccnp-ws-layout', stack: 'ccnp-ws-split-v', side: 'ccnp-ws-split'};
  const DEF = {stack: 45, side: 50};
  const get = k => { try { return localStorage.getItem(k); } catch (_e) { return null; } };
  const put = (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (_e) {} };
  let mode = get(K.layout) === 'side' ? 'side' : 'stack';
  function setSplit(pct){ ws.style.setProperty(mode === 'side' ? '--split' : '--split-v', pct + '%'); }
  function apply(){
    document.body.classList.toggle('side', mode === 'side');
    btn.textContent = mode === 'side' ? '⇅ Top and bottom' : '⇆ Side by side';
    const v = parseFloat(get(K[mode]));
    setSplit(v >= 20 && v <= 80 ? v : DEF[mode]);
  }
  apply();
  btn.addEventListener('click', () => { mode = mode === 'side' ? 'stack' : 'side'; put(K.layout, mode); apply(); });
  bar.addEventListener('pointerdown', e => {
    e.preventDefault();
    // 押している間のポインタ操作は境目が受け取る。これが無いと、枠(iframe)や端末の上へ出た瞬間に操作を取られる
    bar.setPointerCapture(e.pointerId);
    const x0 = e.clientX, y0 = e.clientY;
    let shield = null, pct = null;
    const move = ev => {
      if (!shield){                         // 覆いは動かし始めてから被せる(被せたままだとダブルクリックが境目に届かない)
        if (Math.abs(ev.clientX - x0) < 3 && Math.abs(ev.clientY - y0) < 3) return;
        shield = document.createElement('div'); shield.id = 'dragshield';
        document.body.appendChild(shield); document.body.classList.add('dragging');
      }
      const r = ws.getBoundingClientRect();
      const at = mode === 'side' ? (ev.clientX - r.left) / r.width : (ev.clientY - r.top) / r.height;
      pct = Math.min(80, Math.max(20, at * 100)); setSplit(pct);
    };
    const up = () => {
      if (shield) shield.remove();
      document.body.classList.remove('dragging');
      bar.removeEventListener('pointermove', move);
      bar.removeEventListener('pointerup', up); bar.removeEventListener('pointercancel', up);
      try { bar.releasePointerCapture(e.pointerId); } catch (_e) {}
      if (pct !== null) put(K[mode], pct.toFixed(1));
    };
    bar.addEventListener('pointermove', move);
    bar.addEventListener('pointerup', up); bar.addEventListener('pointercancel', up);
  });
  bar.addEventListener('dblclick', () => { put(K[mode], null); setSplit(DEF[mode]); });
})();

// ---- コンソールの字の大きさ(A− / A+。大きさの表示をダブルクリックすると既定へ戻る) ----
(function(){
  function apply(){
    $('#fsize').textContent = fontPref + 'px';
    const s = sessions[active];
    if (s && s.term){ fitTerm(s); s.term.focus(); }      // 他のタブの端末は、表に出した時に合わせ直す
  }
  function step(d){
    fontPref = Math.min(22, Math.max(7, fontPref + d));
    try { localStorage.setItem('ccnp-ws-font', String(fontPref)); } catch (_e) {}
    apply();
  }
  $('#fminus').addEventListener('click', () => step(-1));
  $('#fplus').addEventListener('click', () => step(+1));
  $('#fsize').addEventListener('dblclick', () => {
    fontPref = FONT_DEFAULT;
    try { localStorage.removeItem('ccnp-ws-font'); } catch (_e) {}
    apply();
  });
  apply();
})();

// 画面下端の帯(Contents・問番号)からの移動は意図したものなので、離脱確認を出さない。別タブで開く操作は除く
$('#foot').addEventListener('click', e => {
  if (e.target.closest('a') && !e.ctrlKey && !e.metaKey && !e.shiftKey && !e.altKey && e.button === 0) leaving = true;
});

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

// ---- 問題文の日本語⇔英語(BL-236 (c)) ----
//   Task と Topology の盤面の節は別々の枠なので、切替はこの帯のボタンで受けて両方の枠へ知らせる。
//   2 版を持つページ(render_html の LANG_JS)は、読み込まれると自分の言語を知らせてくる。選んだ言語を覚えるのは
//   問題ページの側(紙面のページと同じ置き場)なので、ここでは Task の枠が知らせてきた言語に合わせる。
//   1 版しか無い問題のページは何も知らせてこないので、ボタンは出ない。
(function(){
  const btn = $('#lang'), NAME = {en: 'English', ja: '日本語'};
  let lang = null;
  const frames = () => [$('#task'), $('#toponotes'), $('#reading')].filter(Boolean);
  const tell = f => { try { f.contentWindow.postMessage({ccnpLang: lang, ccnpHost: true}, '*'); } catch (_e) {} };
  function paint(){ btn.hidden = false; btn.textContent = NAME[lang === 'en' ? 'ja' : 'en'];
                    window.ccnpLang = lang; window.dispatchEvent(new Event('ccnp-lang')); }
  window.addEventListener('message', ev => {
    const f = frames().find(x => x.contentWindow === ev.source);
    const d = ev.data;
    if (!f || !d || !d.ccnpLangs || (d.lang !== 'en' && d.lang !== 'ja')) return;
    if (f.id === 'task' || lang === null) lang = d.lang;       // Task の枠が正。盤面の節の枠はそれに従う
    paint();
    frames().forEach(tell);
  });
  btn.addEventListener('click', () => {
    if (lang === null) return;
    lang = lang === 'en' ? 'ja' : 'en';
    paint();
    frames().forEach(tell);
  });
  // Task の枠がこの画面の準備より先に読み終わっていると、知らせを受け損ねる。こちらからも一度たずねる
  try { $('#task').contentWindow.postMessage({ccnpLangAsk: true}, '*'); } catch (_e) {}
})();

// ---- 学習モード(BL-246): Steps タブ ----
//   課題ごとに 確認(中間チェックを 1 回回す)・ヒント(1 段ずつ)・模範解(通過後かヒント全開後)。
//   本文はサーバが開いた分だけ返す。言語は問題文の切替に合わせる(1 版しか無ければ英語)。
let learnSteps = null, learnBusy = null, learnReading = null, learnRead = {};
// 課題カード(BL-255): 課題文・単元の見出し・冒頭の約束。最初の読み込みで受け取って持っておく(確認・ヒントの応答には入らない)
let learnTask = {}, learnUnit = {}, learnUnits = {}, learnRules = null, rulesOpen = false;
let learnTries = {}, tryOpen = null;          // 課題ごとの「やってみる」・小窓に出している課題
function learnLang(){ return window.ccnpLang === 'ja' ? 'ja' : 'en'; }
function tr(o){ if (!o) return ''; if (typeof o === 'string') return o; return o[learnLang()] || o.en || o.ja || ''; }
const LT = {en: {check:'Check', checking:'Checking…', hint:'Hint', sol:'Reference solution', pass:'passed', fail:'not yet',
                 none:'self-check', read:'Read:', rules:'Ground rules', note:'Each Check reads the live state of the devices (about 15 seconds). Leave configuration mode before you press it. Hints open one level at a time and are logged.',
                 busy:'Another check is still running.', reset:'Start over', resetting:'Resetting…',
                 resetq:'Start the whole lab over?\n\nXR01 is rolled back to the configuration it had right after the lab was built (your changes are discarded), and every task here returns to not yet checked, with no hints opened.',
                 resetdone:'The lab is back at its starting state.',
                 tryit:'Try it', trytitle:'Try it', tryread:'Open in Reading', close:'Close', mini:'Minimise', restore:'Expand'},
            ja: {check:'確認', checking:'確認中…', hint:'ヒント', sol:'模範解', pass:'通過', fail:'未充足',
                 none:'自己確認', read:'読み物:', rules:'進め方の約束', note:'確認は機器のいまの状態を読みます(約 15 秒)。設定モードを抜けてから押してください。ヒントは 1 段ずつ開き、開いた段数は記録されます。',
                 busy:'別の確認がまだ実行中です。', reset:'最初からやり直す', resetting:'戻しています…',
                 resetq:'ラボ全体を最初からやり直しますか？\n\nXR01 をラボを作った直後の設定へ戻し(あなたの変更は消えます)、ここの課題もすべて未確認・ヒント未開封に戻します。',
                 resetdone:'ラボを最初の状態に戻しました。',
                 tryit:'やってみる', trytitle:'やってみる', tryread:'読み物で開く', close:'閉じる', mini:'たたむ', restore:'広げる'}};
function el(tag, cls, text){ const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
// ---- 「やってみる」の小窓 ----
function tryPanel(){
  let p = $('#trypanel');
  if (p) return p;
  p = el('div'); p.id = 'trypanel'; p.hidden = true;
  const h = el('div', 'tph'), t = el('b'), mn = el('button', 'mn'), cl = el('button', 'cl');
  h.append(t, mn, cl); p.append(h, el('div', 'tpb'));
  mn.addEventListener('click', () => { p.classList.toggle('min'); paintTry(); savePos(); });
  cl.addEventListener('click', () => { tryOpen = null; p.hidden = true; });
  let drag = null;                           // 見出しをつかんで動かす(枠や端末の上に出ても離さない= pointer capture)
  h.addEventListener('pointerdown', e => {
    if (e.target.closest('button')) return;
    const r = p.getBoundingClientRect(); drag = {dx: e.clientX - r.left, dy: e.clientY - r.top};
    h.setPointerCapture(e.pointerId);
  });
  h.addEventListener('pointermove', e => { if (drag) placeTry(e.clientX - drag.dx, e.clientY - drag.dy); });
  h.addEventListener('pointerup', e => { if (drag){ drag = null; h.releasePointerCapture(e.pointerId); savePos(); } });
  document.body.append(p);
  let pos = null;
  try { pos = JSON.parse(localStorage.getItem('ccnp.trypos') || 'null'); } catch (_e) {}
  if (pos && typeof pos.x === 'number'){ placeTry(pos.x, pos.y); if (pos.min) p.classList.add('min'); }
  else placeTry(window.innerWidth - Math.min(440, window.innerWidth - 24) - 16, 56);
  return p;
}
function placeTry(x, y){
  const p = $('#trypanel'), w = p.offsetWidth || 440;
  p.style.left = Math.max(4, Math.min(x, window.innerWidth - Math.min(w, 120))) + 'px';
  p.style.top = Math.max(4, Math.min(y, window.innerHeight - 40)) + 'px';
}
function savePos(){
  const p = $('#trypanel'); if (!p) return;
  try { localStorage.setItem('ccnp.trypos', JSON.stringify({x: p.offsetLeft, y: p.offsetTop, min: p.classList.contains('min')})); } catch (_e) {}
}
function openTry(id){
  tryOpen = id; const p = tryPanel(); p.classList.remove('min'); p.hidden = false; paintTry(); savePos();
}
function paintTry(){
  const p = $('#trypanel');
  if (!p || p.hidden || !tryOpen) return;
  const T = LT[learnLang()], st = (learnSteps || []).find(x => x.id === tryOpen);
  p.querySelector('.tph b').textContent = T.trytitle + (st ? ' — ' + tr(st.title).split(/\s{2,}/)[0] : '');
  p.querySelector('.mn').textContent = p.classList.contains('min') ? T.restore : T.mini;
  p.querySelector('.cl').textContent = T.close;
  const body = p.querySelector('.tpb'); body.replaceChildren();
  for (const t of learnTries[tryOpen] || []){
    const it = el('div', 'tpi'), src = el('div', 'tps');
    src.append(document.createTextNode((tr(t.sec) || tr(t.page)) + ' · '));
    const a = el('a', null, T.tryread); a.href = t.href;
    a.addEventListener('click', e => { if (e.ctrlKey || e.metaKey || e.shiftKey || e.button) return; e.preventDefault(); openReading(t.href, true); });
    src.append(a);
    const c = el('div'); c.innerHTML = tr(t.html);
    it.append(src, c); body.append(it);
  }
}
window.addEventListener('ccnp-lang', paintTry);
window.addEventListener('resize', () => { const p = $('#trypanel'); if (p && !p.hidden) placeTry(p.offsetLeft, p.offsetTop); });
function paintSteps(){
  if (!learnSteps) return;
  const T = LT[learnLang()], root = $('#steps');
  const top = el('div', 'stepsbar'); top.append(el('p', 'note', T.note));
  const rb = el('button', 'reset', learnBusy === '*reset' ? T.resetting : T.reset);
  rb.disabled = learnBusy !== null;
  rb.addEventListener('click', learnReset);
  top.append(rb);
  root.replaceChildren(top);
  if (learnRules && tr(learnRules)){        // 冒頭の約束(問題文の前置き・Ground rules)。既定は畳む
    const dt = el('details', 'rules'); dt.open = rulesOpen;
    dt.addEventListener('toggle', () => { rulesOpen = dt.open; });
    dt.append(el('summary', null, T.rules));
    const b = el('div', 'ttext'); b.innerHTML = tr(learnRules); dt.append(b);
    root.append(dt);
  }
  let unit = null;
  for (const st of learnSteps){
    const u = learnUnit[st.id];
    if (u && u !== unit && learnUnits[u]){  // 単元が替わるところに単元の見出しと前置き
      unit = u;
      root.append(el('h2', 'unit', tr(learnUnits[u].title)));
      const intro = tr(learnUnits[u].intro);
      if (intro){ const d = el('div', 'ttext unitintro'); d.innerHTML = intro; root.append(d); }
    }
    const box = el('div', 'step' + (st.passed ? ' ok' : (st.last && !st.last.ok ? ' ng' : '')));
    box.id = 'step-' + st.id;
    const h = el('h3', null, tr(st.title));
    h.append(el('span', 'badge', st.passed ? T.pass : (st.check ? (st.last ? T.fail : '—') : T.none)));
    box.append(h);
    const tt = tr(learnTask[st.id]);
    if (tt){ const d = el('div', 'ttext'); d.innerHTML = tt; box.append(d); }
    const row = el('div', 'row');
    if (st.check){
      const b = el('button', 'go', learnBusy === st.id ? T.checking : T.check);
      b.disabled = learnBusy !== null;
      b.addEventListener('click', () => learnPost('check', st.id));
      row.append(b);
    }
    if (st.hints_total){
      const b = el('button', null, T.hint + ' ' + Math.min(st.hints.length + 1, st.hints_total) + '/' + st.hints_total);
      b.disabled = st.hints.length >= st.hints_total || learnBusy !== null;
      b.addEventListener('click', () => learnPost('hint', st.id));
      row.append(b);
    }
    if ((learnTries[st.id] || []).length){   // 読み物の「やってみる」(その課題の read: の節にあるもの)を小窓で
      const b = el('button', 'try', T.tryit);
      b.addEventListener('click', () => openTry(st.id));
      row.append(b);
    }
    box.append(row);
    const reads = learnRead[st.id] || [];
    if (reads.length){                      // この課題の背景の節(BL-252)。押すと Reading タブがその節で開く
      const r = el('div', 'read'); r.append(el('span', 'lbl', T.read));
      for (const rd of reads){
        const a = el('a', null, (tr(rd.sec) || tr(rd.page)) + ' ');
        a.href = rd.href; a.title = tr(rd.page);
        a.addEventListener('click', e => {
          if (e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;     // 別タブで開く操作はそのまま
          e.preventDefault(); openReading(rd.href, true);
        });
        r.append(a);
      }
      box.append(r);
    }
    if (st.last){
      const r = el('div', 'res');
      for (const ln of st.last.lines)
        r.append(el('div', ln.startsWith('[PASS]') ? 'p' : ln.startsWith('[FAIL]') ? 'f' : 'u', ln));
      box.append(r);
    }
    st.hints.forEach((hh, i) => { const d = el('div', 'hint'); d.append(el('span', 'lbl', T.hint + ' ' + (i + 1)), document.createTextNode(tr(hh))); box.append(d); });
    if (st.solution){ const d = el('div', 'sol'); d.append(el('span', 'lbl', T.sol), document.createTextNode(tr(st.solution))); box.append(d); }
    root.append(box);
  }
}
async function learnReset(){
  const T = LT[learnLang()];
  if (!confirm(T.resetq)) return;
  learnBusy = '*reset'; paintSteps();
  try {
    const r = await fetch('api/learn/reset?' + Q, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
    const d = await r.json();
    if (d.busy) alert(T.busy);
    if (d.error) alert(d.error);
    if (d.steps) learnSteps = d.steps;
    if (d.reset){ learnBusy = null; paintSteps(); $('#steps').scrollTop = 0; alert(T.resetdone); return; }
  } catch (e) { alert(String(e)); }
  learnBusy = null; paintSteps();
}
async function learnPost(kind, id){
  if (kind === 'check'){ learnBusy = id; paintSteps(); }
  try {
    const r = await fetch('api/learn/' + kind + '?' + Q, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({step: id})});
    const d = await r.json();
    if (d.busy) alert(LT[learnLang()].busy);
    if (d.error) alert(d.error);
    if (d.steps) learnSteps = d.steps;
  } catch (e) { alert(String(e)); }
  learnBusy = null; paintSteps();
}
(async function(){
  try {
    const d = await (await fetch('api/learn?' + Q)).json();
    if (!d.enabled) return;
    learnSteps = d.steps;
    for (const st of d.steps){ learnRead[st.id] = st.read || []; learnTask[st.id] = st.task || {}; learnUnit[st.id] = st.unit || '';
                               learnTries[st.id] = st.tries || []; }
    learnUnits = d.units || {}; learnRules = d.rules || null;
    if (d.reading){ learnReading = d.reading; $('#readbtn').hidden = false; }
    // 課題カード(BL-255): 課題文はこのタブに入るので Task タブは出さない。Task の枠は読み込んだまま残す
    // (問題文の日英切替は、その枠が知らせてくる言語に合わせる作りのため)
    if (Object.keys(learnTask).some(k => tr(learnTask[k]))){
      $('#ltabs [data-tab="task"]').hidden = true; $('#stepsbtn').textContent = 'Tasks';
      $('#ltabs').prepend($('#stepsbtn'));                    // 先頭のタブにする(Tasks / Topology / Reading)
    }
    $('#stepsbtn').hidden = false; paintSteps();
    const m = /^#step=([\w-]+)$/.exec(location.hash);       // 読み物の実践ページから来た時(/_learn?id=…&step=…)
    if (m) gotoStep(m[1]); else if ($('#ltabs [data-tab="task"]').hidden) leftTab('steps');
  } catch (_e) {}
})();
// ---- 読み物(BL-252): Reading タブ ----
//   中身はパック配信サーバの読み物(/_read/<key>/…)。Steps の各課題の「読み物」リンクがその節で開く。
//   同じページの別の節へは枠を読み直さず合図(ccnpGoto)で送る。言語は問題文の切替に従う(frames() に入っている)。
//   読み物の実践ページの「ワークスペースで開く」は、枠の中では合図(ccnpStep)になり、ここで Steps のその課題を開く。
function defaultReading(){
  const st = (learnSteps || []).find(x => !x.passed && (learnRead[x.id] || []).length);
  return st ? learnRead[st.id][0].href : learnReading.href;
}
// 読み物をビルドし直した後も古いページを出し続けないよう、ページの更新時刻を覚えておき、変わっていたら読み直す(2026-10-24)。
// 読み直す時は ?v=<更新時刻> を付ける(同じ URL では節の移動だけになり読み直されないため)。
const readStamp = {};
const pageOf = u => u ? new URL(u, location.href).pathname.split('/').pop() : '';
async function pageStamp(href){
  try { const d = await (await fetch('api/learn/readstamp?' + Q + '&page=' + encodeURIComponent(pageOf(href)), {cache: 'no-store'})).json();
        return d.mtime || 0; } catch (_e) { return 0; }
}
function withStamp(href, mt){
  const u = new URL(href, location.href); u.searchParams.set('v', String(Math.floor(mt))); return u.toString();
}
async function openReading(href, show){
  const f = $('#reading'), cur = f.getAttribute('src');
  const strip = u => u ? u.replace(/[?#].*$/, '') : '';
  const mt = await pageStamp(href);
  if (cur && strip(cur) === strip(href) && f.contentWindow && readStamp[pageOf(href)] === mt){
    const sec = (href.split('#')[1] || '');
    try { f.contentWindow.postMessage({ccnpGoto: sec}, new URL(href).origin); } catch (_e) {}
  } else {
    readStamp[pageOf(href)] = mt; f.setAttribute('src', withStamp(href, mt));
  }
  if (show) leftTab('read');                  // 開く先を決めてから切り替える(切替時の読み直し確認と競合させない)
}
async function refreshReading(){              // Reading タブを開いた時: いまのページがビルドし直されていれば読み直す
  const f = $('#reading'), cur = f.getAttribute('src');
  if (!cur) return;
  const mt = await pageStamp(cur);
  if (mt && readStamp[pageOf(cur)] !== mt){
    let sec = '';
    try { sec = (f.contentWindow.location.hash || '').slice(1); } catch (_e) {}
    readStamp[pageOf(cur)] = mt;
    f.setAttribute('src', withStamp(cur.replace(/#.*$/, ''), mt) + (sec ? '#' + sec : ''));
  }
}
function gotoStep(id){
  leftTab('steps');
  const box = document.getElementById('step-' + id);
  if (!box) return;
  box.scrollIntoView({block: 'start', behavior: 'smooth'});
  box.classList.add('flash'); setTimeout(() => box.classList.remove('flash'), 1600);
}
window.addEventListener('message', ev => {
  const f = $('#reading');
  if (ev.source !== f.contentWindow || !ev.data || typeof ev.data.ccnpStep !== 'string') return;
  const lid = new URLSearchParams(location.search).get('learn');
  if (ev.data.ccnpLab && lid && ev.data.ccnpLab !== lid){       // 別のラボの課題= そのラボのワークスペースへ移る
    leaving = true; location.href = new URL(f.getAttribute('src')).origin + '/_learn?id=' + encodeURIComponent(ev.data.ccnpLab)
      + (ev.data.ccnpStep ? '&step=' + encodeURIComponent(ev.data.ccnpStep) : ''); return;
  }
  if (ev.data.ccnpStep) gotoStep(ev.data.ccnpStep); else leftTab('steps');
});
window.addEventListener('ccnp-lang', paintSteps);

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
    ap.add_argument("--learn", metavar="問題ID",
                    help="単発: 学習モード(Steps タブ= 課題ごとの確認・段階式ヒント)。--lab / --task を省くと問題 ID から決める")
    ap.add_argument("--with-parent", type=int, metavar="PID",
                    help="この PID の親プロセスが終わったら自分も終わる(pack.sh serve が自分の PID を渡す)")
    ap.add_argument("--no-record", action="store_true",
                    help="コンソールの操作記録(records/console/)を書かない")
    a = ap.parse_args()
    if a.learn:
        if not os.path.exists(os.path.join(a.repo, "problems", a.learn, "learn.yml")):
            sys.exit(f"problems/{a.learn}/learn.yml がありません")
        a.lab = a.lab or lab_title(a.learn)
        if not a.task:                            # lab.sh provision が置く作業コピー(英語版が既定・無ければ日本語版)
            for cand in ("Task.md", "問題.md"):
                path = os.path.join(a.repo, "lab", a.learn, cand)
                if os.path.exists(path):
                    a.task = path
                    break
    if a.task and not os.path.exists(a.task):
        sys.exit(f"--task {a.task} がありません")
    mode = f"単発 lab={a.lab}" if a.lab else "パック常駐"
    ready = f"ラボのワークスペース({mode})を http://{a.bind}:{a.port}/ で待ち受け中"
    try:
        web.run_app(make_app(a.repo, a.pack_port, a.lab, a.task, a.with_parent, not a.no_record, a.learn),
                    host=a.bind, port=a.port,
                    print=lambda *_: print(ready, flush=True))     # 待ち受けに成功してから出す
    except OSError as e:                          # ポート使用中など。長いトレースを出さず 1 行で終わる
        sys.exit(f"ラボのワークスペースを起動できません(ポート {a.port}): {e.strerror or e}")
    if a.with_parent and os.getppid() != a.with_parent:
        print("配信サーバが終了したので、ラボのワークスペースも終了しました", flush=True)


if __name__ == "__main__":
    main()
