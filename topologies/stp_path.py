#!/usr/bin/env python3
"""STP 経路づくり(BL-270)— お題の経路になるよう設定を組み替えるゲームのサーバ側。

STP パズル(stp_puzzle.py・BL-268)の逆向き。盤面とお題(「PC1 → SRV1 はこの経路を通る」)が先にあり、
解く側が Bridge Priority・リンク速度・Port Cost・Port Priority を変えて、STP の木を組み替える。
STP の計算は stp_model(実機と照合済みの計算器)だけで行う。画面はつまみを変えるたびに eval を呼ぶ
(JS に計算器を持たせない)。

  ステージの名前とチュートリアル(日英)… games/stp-path/stages.yml
  進み具合(git 除外)……………………… topologies/_state/stp_path.json(リセットできる)
  配信……………………………………………… pack_server.py の /_stp_path/(画面)と /_api/stp_path/*(下の api())

  python3 topologies/stp_path.py selftest      … 全ステージの生成・最少手数(総当たりと照合)・判定・API・保存
  python3 topologies/stp_path.py show 3 2      … ステージ 3 の level 2 の盤面・お題・最少の解

盤面に出すものはステージごとに増える(SHOW_FROM)。隠すのは表示だけで、計算はいつも全部。

数値の決まり(ユーザ決定・設計 §1): 用語と値は本物。MAC は数字だけ(0000.0000.00NN)。パス コストはショート法。
最少手数: 2 手までを総当たりで確かめる。生成器が k 手(k ≤ 3)で作った盤面に k−1 手以下の解が無ければ最少は k。
設計= problems/_drafts/STP-PATH.design.md。
"""
from __future__ import annotations

import datetime
import functools
import hashlib
import itertools
import json
import math
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stp_model as sm                                  # noqa: E402
import stp_puzzle as sp                                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.join(REPO, "games", "stp-path")
STATE = os.path.join(REPO, "topologies", "_state", "stp_path.json")
LEVELS = 5
READY = [1, 2, 3, 4, 5, 6, 7, 8]
S_ROLES, S_ENGINEER, S_VLAN, S_CAMPUS = 2, 6, 7, 8          # 生成の作りが違うステージ

# 盤面に出すもの(設計 §10・2026-11-11 ユーザ指示「最初は最小限、順に出す」)。値= 初めて出すステージ。
# 隠すのは表示だけで、計算はいつも STP の決まりをすべて回す。まだ出していない値で答えが決まる盤面は出さない(selftest で検査)。
#   bid= スイッチの箱(名前・プライオリティ・MAC)と★と止まったリンク(破線)  ports= ポートの印(R/D/A・FWD/BLK)
#   rpc= 箱の RPC  speed= リンクの速度とコスト  pcost= 手で決めたポート コスト  portid= ポート名とポート ID
SHOW_FROM = {"bid": 1, "ports": 2, "rpc": 2, "speed": 3, "pcost": 4, "portid": 5}
STATE_V = 2                                                 # 2= ステージ 2(ポートの役割)を挟んだ後の番号


def show_of(stage):
    return [k for k, s in SHOW_FROM.items() if stage is None or stage >= s]


def new_of(stage):
    return [k for k, s in SHOW_FROM.items() if s == stage and s > 1]

METHOD = "short"
SPEEDS = ["100M", "1G", "10G"]                          # マルチギガ ポートで選べる速度(10M は使わない)
SPEED_CLI = {"100M": "100", "1G": "1000", "10G": "10000"}
COSTS = [1, 2, 4, 10, 19, 30, 50, 100]                  # Port Cost のプリセット(本物の範囲の一部)
PRIOS = list(range(0, 61441, 4096))                     # Bridge Priority(本物の範囲)
PPRIOS = list(range(0, 241, 16))                        # Port Priority(本物の範囲)
DEF_PRIO, DEF_PPRIO = 32768, 128
KINDS = ["prio", "speed", "cost", "pprio"]

W = 400                                                 # 図の幅(画面の SVG と同じ)
BW, BH = 112, 50                                        # スイッチの箱(画面と同じ)
HW, HH = 28, 13                                         # 端末の箱の半分


# ==========================================================================
# 盤面の部品
# ==========================================================================
SHAPES = dict(sp.SHAPES)
SHAPES["sqpar"] = (sp._SQ, [(0, 1), (0, 1), (1, 2), (2, 3), (3, 0)])     # 上の辺が並行リンク
# 横に並ぶ箱どうしは間を 118 ほど空ける(両端のポートの印＋速度の表示= 押す場所が入る幅)。STP パズルの形より横に広い
# 5 台は「家の形」(屋根の頂点＋四角)。5 角形＋弦は弦が隣の辺とほぼ同じ向きに出て印が重なるので使わない
_HOUSE = [(200, 60), (85, 205), (315, 205), (85, 372), (315, 372)]
SHAPES["house"] = (_HOUSE, [(0, 1), (0, 2), (1, 2), (1, 3), (2, 4), (3, 4)])        # 屋根の下に梁
SHAPES["house2"] = (_HOUSE, [(0, 1), (0, 2), (1, 3), (2, 4), (3, 4), (1, 4)])       # 四角に対角線
SHAPES["ladder"] = ([(85, 60), (85, 207), (85, 354), (315, 60), (315, 207), (315, 354)],
                    [(0, 1), (1, 2), (3, 4), (4, 5), (0, 3), (1, 4), (2, 5)])
CAMPUS_POS = {"2tier": {"SW01": (85, 65), "SW02": (315, 65), "SW03": (85, 270), "SW04": (315, 270)},
              "3tier": {"SW01": (85, 60), "SW02": (315, 60), "SW03": (85, 207), "SW04": (315, 207),
                        "SW05": (85, 354), "SW06": (315, 354)}}


def _te(n):
    """Catalyst 9300 のマルチギガ ポート風(100M/1G/10G を speed で選ぶ)。port 番号 = n。"""
    return {"name": f"Te1/0/{n}", "num": n}


def _wire(rnd, names, edges, gap=0):
    need = {s: 0 for s in names}
    for i, j in edges:
        need[names[i]] += 1
        need[names[j]] += 1
    pool = {s: rnd.sample(range(1, need[s] + 1 + gap), need[s]) for s in names}
    return [(names[i], _te(pool[names[i]].pop()), names[j], _te(pool[names[j]].pop())) for i, j in edges]


def _macs(rnd, names):
    """数字だけの MAC(0000.0000.00NN)。スイッチ名の順とは無関係に振る。"""
    nn = rnd.sample(range(1, 60), len(names))
    return {s: {"mac": f"0000.0000.{n:04d}"} for s, n in zip(names, nn)}


def _shape(rnd, shape):
    pos, edges = SHAPES[shape]
    edges = list(edges)
    if shape in ("ring5c", "ring6c"):
        n = len(pos)
        i = rnd.randrange(n)
        edges.append((i, (i + rnd.choice(range(2, n - 1))) % n))
    return list(pos), edges


def _rect_hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _seg_hits_rect(x1, y1, x2, y2, r, step=3.0):
    n = max(1, int(math.hypot(x2 - x1, y2 - y1) / step))
    for i in range(n + 1):
        x, y = x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n
        if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
            return True
    return False


def _seg_cross(p1, p2, q1, q2):
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (o(p1, p2, q1) * o(p1, p2, q2) < 0) and (o(q1, q2, p1) * o(q1, q2, p2) < 0)


def _mark(cx, cy, ux, uy, L):
    """画面の geom() の place() と同じ: 箱の中心から向き u に進み、箱から 15 以上離れた最初の点(ポートの印の位置)。"""
    d = 0
    while d < L / 2:
        px, py = cx + ux * d, cy + uy * d
        if math.hypot(max(abs(px - cx) - BW / 2, 0), max(abs(py - cy) - BH / 2, 0)) >= 15:
            break
        d += 1
    return cx + ux * d, cy + uy * d


def _place_hosts(pos, links, hosts):
    """端末の置き場所を、箱・線・他の端末・ポートの印にぶつからない所から選ぶ。戻り値= ぶつかりの点数(0 が理想)。"""
    rs = {s: (x - BW / 2 - 6, y - BH / 2 - 6, x + BW / 2 + 6, y + BH / 2 + 6) for s, (x, y) in pos.items()}
    segs = [(pos[a], pos[c]) for a, _ia, c, _ic in links]
    marks = []                                      # リンクの両端の印(並行リンクのずれは無視)
    for (ax, ay), (bx, by) in segs:
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        marks += [_mark(ax, ay, ux, uy, L), _mark(bx, by, -ux, -uy, L)]
    cy = sum(y for _x, y in pos.values()) / len(pos)
    placed, bad = [], 0
    for h in hosts:
        sx, sy = pos[h["sw"]]
        up = sy <= cy
        cands = [(0, -82), (0, 82), (-38, -84), (38, -84), (-38, 84), (38, 84), (-70, -78), (70, -78), (-70, 78), (70, 78)]
        cands.sort(key=lambda d: (0 if (d[1] < 0) == up else 1, abs(d[0])))
        best = None
        for dx, dy in cands:
            hx, hy = sx + dx, sy + dy
            r = (hx - HW - 4, hy - HH - 4, hx + HW + 4, hy + HH + 4)
            sc = 0
            if r[0] < 2 or r[2] > W - 2:
                sc += 100
            for s, q in rs.items():
                if _rect_hit(r, q):
                    sc += 50
                if s != h["sw"] and _seg_hits_rect(sx, sy, hx, hy, q):
                    sc += 20
            for q in placed:
                if _rect_hit(r, q):
                    sc += 50
                if _seg_hits_rect(sx, sy, hx, hy, q):
                    sc += 20
            L = math.hypot(dx, dy)
            mx, my = _mark(sx, sy, dx / L, dy / L, L)
            for qx, qy in marks:
                if math.hypot(mx - qx, my - qy) < 30:
                    sc += 20
            ang = math.atan2(dy, dx)
            for p1, p2 in segs:
                if _seg_hits_rect(p1[0], p1[1], p2[0], p2[1], r):
                    sc += 20
                if (sx, sy) in (p1, p2):
                    o = p2 if p1 == (sx, sy) else p1
                    d = abs((math.atan2(o[1] - sy, o[0] - sx) - ang + math.pi) % (2 * math.pi) - math.pi)
                    if d < 0.55:
                        sc += 10
                elif _seg_cross((sx, sy), (hx, hy), p1, p2):
                    sc += 10
            if best is None or sc < best[0]:
                best = (sc, hx, hy, r)
        h["x"], h["y"] = best[1], best[2]
        placed.append(best[3])
        L = math.hypot(best[1] - sx, best[2] - sy)
        marks.append(_mark(sx, sy, (best[1] - sx) / L, (best[2] - sy) / L, L))
        bad += best[0]
    return bad


def _new_cfg(names, vlans, nlinks):
    return {"prio": {v: {s: DEF_PRIO for s in names} for v in vlans}, "speed": ["1G"] * nlinks,
            "cost": {v: {} for v in vlans}, "pprio": {v: {} for v in vlans}}


def _copy(cfg):
    return {"prio": {v: dict(d) for v, d in cfg["prio"].items()}, "speed": list(cfg["speed"]),
            "cost": {v: dict(d) for v, d in cfg["cost"].items()}, "pprio": {v: dict(d) for v, d in cfg["pprio"].items()}}


def _board(shape, names, pos, links, init, knobs, vlans, flows, rnd, roles=None, limit=None, host_sw=None):
    """flows= [(src 端末, dst 端末, vlan)]。host_sw= {端末: スイッチ}。端末は Te1/0/1x のアクセス ポート(PortFast)。"""
    hosts, used = [], {}
    for name in sorted({x for f in flows for x in f[:2]}, key=lambda n: (n[:2] != "PC", n)):
        s = host_sw[name]
        n = 10 + rnd.randrange(0, 12)
        while n in used.setdefault(s, set()):
            n += 1
        used[s].add(n)
        v = next(f[2] for f in flows if name in f[:2])
        hosts.append({"name": name, "kind": "pc" if name.startswith("PC") else "srv", "sw": s, "if": _te(n), "vlan": v})
    pos = {s: tuple(p) for s, p in zip(names, pos)} if not isinstance(pos, dict) else dict(pos)
    return {"shape": shape, "names": list(names), "pos": pos, "sw": _macs(rnd, names), "links": links,
            "vlans": list(vlans), "init": init, "knobs": list(knobs), "hosts": hosts, "flows": list(flows),
            "roles": roles or {}, "limit": dict(limit or {}), "reqs": [], "par": None, "budget": None, "sol": None}


def _finish_layout(b):
    """端末を置き、上にはみ出す分だけ全体を下げる。戻り値= ぶつかりの点数。"""
    bad = _place_hosts(b["pos"], b["links"], b["hosts"])
    top = min([y - HH for h in b["hosts"] for y in [h["y"]]] + [y - BH / 2 for _x, y in b["pos"].values()])
    dy = max(0, 14 - top)
    if dy:
        b["pos"] = {s: (x, y + dy) for s, (x, y) in b["pos"].items()}
        for h in b["hosts"]:
            h["y"] += dy
    b["height"] = int(max([h["y"] + HH for h in b["hosts"]] + [y + BH / 2 for _x, y in b["pos"].values()]) + 34)
    return bad


# ==========================================================================
# 計算(stp_model)とお題の判定
# ==========================================================================
def host_sw(b, name):
    return next(h["sw"] for h in b["hosts"] if h["name"] == name)


def topo(b, cfg, v):
    sw = {s: {"prio": cfg["prio"][v][s], "mac": b["sw"][s]["mac"]} for s in b["names"]}
    links = [(a, ia, c, ic, cfg["speed"][li]) for li, (a, ia, c, ic) in enumerate(b["links"])]
    return sm.Topo(sw, links, METHOD, cfg["pprio"][v], cfg["cost"][v], v).solve()


def route(t, src, dst):
    """木の上の経路= (スイッチの列, リンク番号の列)。"""
    adj = {s: [] for s in t.sw}
    for li, (a, ia, c, ic, _sp) in enumerate(t.links):
        if t.role[(a, ia["name"])] != "Altn" and t.role[(c, ic["name"])] != "Altn":
            adj[a].append((c, li))
            adj[c].append((a, li))
    prev = {src: None}
    q = [src]
    while q:
        x = q.pop(0)
        for y, li in adj[x]:
            if y not in prev:
                prev[y] = (x, li)
                q.append(y)
    sws, lis = [dst], []
    while prev[sws[-1]] is not None:
        x, li = prev[sws[-1]]
        lis.append(li)
        sws.append(x)
    return sws[::-1], lis[::-1]


def limit_ok(b, cfg):
    return all(sum(1 for x in cfg["speed"] if x == k) <= n for k, n in b["limit"].items())


def check(b, cfg, vlans=None, ts=None):
    """お題ごとの {ok, …}。vlans を渡すとその VLAN のお題だけ(探索で使う)。"""
    ts = dict(ts or {})
    out = []
    for r in b["reqs"]:
        v = r["vlan"]
        if vlans is not None and v not in vlans:
            continue
        if v not in ts:
            ts[v] = topo(b, cfg, v)
        t = ts[v]
        if r["kind"] == "root":
            out.append({"ok": t.root == r["sw"], "root": t.root})
            continue
        sws, lis = route(t, host_sw(b, r["src"]), host_sw(b, r["dst"]))
        ok = lis == r["links"] if r["kind"] == "path" else r["via"] in sws[1:-1]
        out.append({"ok": ok, "sws": sws, "links": lis})
    return out, ts


def sat(b, cfg, vlans=None):
    if not limit_ok(b, cfg):
        return False
    res, _ts = check(b, cfg, vlans)
    return all(r["ok"] for r in res)


def diff(b, cfg):
    """初期状態から変わったつまみ。手数 = この数(リンク速度は両端で 1 手)。"""
    init, out = b["init"], []
    for v in b["vlans"]:
        for s in b["names"]:
            if cfg["prio"][v][s] != init["prio"][v][s]:
                out.append(("prio", v, s))
        for k in sorted(set(cfg["cost"][v]) | set(init["cost"][v])):
            if cfg["cost"][v].get(k) != init["cost"][v].get(k):
                out.append(("cost", v, k))
        for k in sorted(set(cfg["pprio"][v]) | set(init["pprio"][v])):
            if cfg["pprio"][v].get(k, DEF_PPRIO) != init["pprio"][v].get(k, DEF_PPRIO):
                out.append(("pprio", v, k))
    for li, x in enumerate(cfg["speed"]):
        if x != init["speed"][li]:
            out.append(("speed", li))
    return out


# ==========================================================================
# 最少手数(総当たり)
# ==========================================================================
def _ports(b):
    return [(a, ia["name"]) for a, ia, _c, _ic in b["links"]] + [(c, ic["name"]) for _a, _ia, c, ic in b["links"]]


def _par_groups(b):
    """並行リンクのポート= {(sw, if): [(同じ相手へ向かう他のポート)]}。Port Priority が効くのはここだけ
    (ポート ID の比較は送信元 BID が同じ= 同じスイッチから来た BPDU どうし、で起きる)。"""
    out = {}
    for a, ia, c, ic in b["links"]:
        for s, ifc, n in ((a, ia, c), (c, ic, a)):
            sib = [(s, x["name"], x["num"]) for a2, x, c2, _y in b["links"] if a2 == s and c2 == n and x["name"] != ifc["name"]]
            sib += [(s, y["name"], y["num"]) for a2, _x, c2, y in b["links"] if c2 == s and a2 == n and y["name"] != ifc["name"]]
            if sib:
                out[(s, ifc["name"])] = (ifc["num"], sib)
    return out


def _reps(values, sig, prefer_high):
    """値を sig の同じ組に分け、組ごとに 2 つまで代表を残す(2 つのつまみが同じ組に入る場合の大小も表せる)。"""
    groups = {}
    for x in values:
        groups.setdefault(sig(x), []).append(x)
    out = []
    for g in groups.values():
        g = sorted(g, reverse=prefer_high(g))
        out += g[:2]
    return sorted(out)


def options(b, vlans=None):
    """探索で試すつまみと候補値(初期値は除く)。値は結果が変わりうる組の代表に縮める(総当たりの正しさは保つ)。"""
    init, vs, out = b["init"], vlans or b["vlans"], []
    if "prio" in b["knobs"]:
        for v in vs:
            for s in b["names"]:
                others = sorted({init["prio"][v][x] for x in b["names"] if x != s})
                dom = _reps(PRIOS, lambda x: tuple((x > o) - (x < o) for o in others),
                            lambda g: g[0] < max(others))                # 他より下の組は上端寄り(24576・28672 など)
                out.append((("prio", v, s), [x for x in dom if x != init["prio"][v][s]]))
    if "speed" in b["knobs"] and vlans is None:
        for li in range(len(b["links"])):
            out.append((("speed", li), [x for x in SPEEDS if x != init["speed"][li]]))
    if "cost" in b["knobs"]:
        for v in vs:
            for k in _ports(b):
                out.append((("cost", v, k), [x for x in [None] + COSTS if x != init["cost"][v].get(k)]))
    if "pprio" in b["knobs"]:
        groups = _par_groups(b)
        for v in vs:
            for k, (num, sib) in groups.items():
                sv = [(init["pprio"][v].get((s, n), DEF_PPRIO), nn) for s, n, nn in sib]
                dom = _reps(PPRIOS, lambda x: tuple(((x, num) > o) - ((x, num) < o) for o in sv), lambda g: g[0] < DEF_PPRIO)
                out.append((("pprio", v, k), [x for x in dom if x != init["pprio"][v].get(k, DEF_PPRIO)]))
    return out


def setk(cfg, kn, val):
    kind = kn[0]
    if kind == "prio":
        cfg["prio"][kn[1]][kn[2]] = val
    elif kind == "speed":
        cfg["speed"][kn[1]] = val
    elif kind == "cost":
        if val is None:
            cfg["cost"][kn[1]].pop(kn[2], None)
        else:
            cfg["cost"][kn[1]][kn[2]] = val
    else:
        if val == DEF_PPRIO:
            cfg["pprio"][kn[1]].pop(kn[2], None)
        else:
            cfg["pprio"][kn[1]][kn[2]] = val


def search(b, maxd, vlans=None):
    """maxd 手以下でお題を満たす最小の手数と解。無ければ (None, None)。"""
    init = b["init"]
    if sat(b, init, vlans):
        return 0, init
    opts = options(b, vlans)
    for d in range(1, maxd + 1):
        for combo in itertools.combinations(opts, d):
            for vals in itertools.product(*[o[1] for o in combo]):
                cfg = _copy(init)
                for (kn, _dom), val in zip(combo, vals):
                    setk(cfg, kn, val)
                if sat(b, cfg, vlans):
                    return d, cfg
    return None, None


# ==========================================================================
# ステージ(土台= 盤面・初期設定・使えるつまみ・端末)
# ==========================================================================
def _hosts_on(rnd, names, n):
    return rnd.sample(names, n)


def base_s1(rnd, level):
    """Root Bridge: Bridge Priority だけ。全 1G。どの level も 1 手(ルートを選ぶだけ)。
    1〜2= 三角形 / 3〜4= 四角 / 5= 四角＋斜めの線で、1 台のプライオリティが最初から低い(それより下げる)。"""
    shape = rnd.choice([["tri"], ["tri"], ["sq", "diamond"], ["sq", "diamond"], ["sqd", "tridual"]][level - 1])
    pos, edges = _shape(rnd, shape)
    names = [f"SW{i + 1}" for i in range(len(pos))]
    links = _wire(rnd, names, edges)
    init = _new_cfg(names, [1], len(links))
    if level == 5:
        init["prio"][1][rnd.choice(names)] = rnd.choice([28672, 24576])
    a, c = _hosts_on(rnd, names, 2)
    return _board(shape, names, pos, links, init, ["prio"], [1], [("PC1", "SRV1", 1)], rnd, host_sw={"PC1": a, "SRV1": c})


def base_s2(rnd, level):
    """Port Roles: Bridge Priority だけ・全 1G(盤面にポートの印と RPC が出る)。
    1〜3= ルートは動かさず、同点の決着(隣のブリッジ ID)で経路を変える / 4〜5= 2 手(ルートも動かしてよい)。"""
    shape = rnd.choice([["sq", "diamond"], ["sq", "diamond"], ["sqd", "tridual", "house2"], ["sq", "sqd"],
                        ["sqd", "tridual", "house"]][level - 1])
    pos, edges = _shape(rnd, shape)
    names = [f"SW{i + 1}" for i in range(len(pos))]
    links = _wire(rnd, names, edges)
    init = _new_cfg(names, [1], len(links))
    if level <= 3:
        init["prio"][1][rnd.choice(names)] = rnd.choice([4096, 24576])
    elif level == 5:
        init["prio"][1][rnd.choice(names)] = rnd.choice([28672, 24576])
    a, c = _hosts_on(rnd, names, 2)
    return _board(shape, names, pos, links, init, ["prio"], [1], [("PC1", "SRV1", 1)], rnd, host_sw={"PC1": a, "SRV1": c})


def _one_low(rnd, init, names, v=1):
    init["prio"][v][rnd.choice(names)] = rnd.choice([4096, 24576, 28672])


def base_s3(rnd, level):
    """Cable Speed: リンク速度だけ。ルートは固定(1 台だけ低い priority)。4〜5 は 10G の在庫に上限。"""
    shape = rnd.choice([["sq"], ["sq", "diamond"], ["sqd", "diamond"], ["sqd", "tridual"], ["tridual", "mesh4", "sqd"]][level - 1])
    pos, edges = _shape(rnd, shape)
    names = [f"SW{i + 1}" for i in range(len(pos))]
    links = _wire(rnd, names, edges)
    init = _new_cfg(names, [1], len(links))
    _one_low(rnd, init, names)
    if level >= 3:
        init["speed"] = [rnd.choice(["1G", "1G", "1G", "10G", "100M"]) for _ in links]
    limit = {"10G": sum(1 for x in init["speed"] if x == "10G") + 1} if level >= 4 else None
    a, c = _hosts_on(rnd, names, 2)
    return _board(shape, names, pos, links, init, ["speed"], [1], [("PC1", "SRV1", 1)], rnd, limit=limit,
                  host_sw={"PC1": a, "SRV1": c})


def base_s4(rnd, level):
    """Port Cost: spanning-tree cost だけ。速度は混在。ルートは固定。"""
    shape = rnd.choice([["sq"], ["diamond", "sq"], ["sqd", "diamond"], ["tridual", "sqd"], ["house2", "bowtie"]][level - 1])
    pos, edges = _shape(rnd, shape)
    names = [f"SW{i + 1}" for i in range(len(pos))]
    links = _wire(rnd, names, edges, gap=rnd.randint(0, 1))
    init = _new_cfg(names, [1], len(links))
    _one_low(rnd, init, names)
    init["speed"] = [rnd.choice(["1G", "1G", "10G"]) for _ in links]
    a, c = _hosts_on(rnd, names, 2)
    return _board(shape, names, pos, links, init, ["cost"], [1], [("PC1", "SRV1", 1)], rnd, host_sw={"PC1": a, "SRV1": c})


def base_s5(rnd, level):
    """Tie-Breakers: Port Priority(4〜5 は Bridge Priority も)。並行リンクのどちらの線を通るか。"""
    shape = ["par", "par", "sqpar", "par", "sqpar"][level - 1]
    pos, edges = _shape(rnd, shape)
    names = [f"SW{i + 1}" for i in range(len(pos))]
    links = _wire(rnd, names, edges, gap=rnd.randint(0, 2))
    init = _new_cfg(names, [1], len(links))
    if level <= 3:
        init["prio"][1]["SW1"] = rnd.choice([4096, 24576])          # ルートは並行リンクの片側
    pair = ["SW1", "SW2"]
    if level in (1, 4):
        a, c = pair if rnd.random() < 0.5 else pair[::-1]
    else:
        a, c = rnd.sample(names, 2)
    knobs = ["pprio"] if level <= 3 else ["pprio", "prio"]
    return _board(shape, names, pos, links, init, knobs, [1], [("PC1", "SRV1", 1)], rnd, host_sw={"PC1": a, "SRV1": c})


def base_s6(rnd, level):
    """Engineer: 全部のつまみ・お題 2 本(PC1 → SRV1・PC2 → SRV1)・手数の上限が厳しい。"""
    shape = rnd.choice([["sqd", "tridual"], ["bowtie", "sqd"], ["house", "bowtie"], ["ladder", "house2"], ["ladder", "house", "house2"]][level - 1])
    pos, edges = _shape(rnd, shape)
    names = [f"SW{i + 1}" for i in range(len(pos))]
    links = _wire(rnd, names, edges, gap=rnd.randint(0, 1))
    init = _new_cfg(names, [1], len(links))
    if rnd.random() < 0.5:
        _one_low(rnd, init, names)
    init["speed"] = [rnd.choice(["1G", "1G", "1G", "10G"]) for _ in links]
    p1, p2, s1 = _hosts_on(rnd, names, 3)
    return _board(shape, names, pos, links, init, KINDS, [1], [("PC1", "SRV1", 1), ("PC2", "SRV1", 1)], rnd,
                  host_sw={"PC1": p1, "PC2": p2, "SRV1": s1})


def base_s7(rnd, level):
    """Load Sharing: VLAN 10・20。VLAN ごとの Bridge Priority と Port Cost(速度は全 VLAN に効くので使わない)。"""
    shape = rnd.choice([["sq"], ["sqd", "tridual"], ["mesh4", "sqd"], ["sqd", "tridual"], ["mesh4", "tridual"]][level - 1])
    pos, edges = _shape(rnd, shape)
    names = [f"SW{i + 1}" for i in range(len(pos))]
    links = _wire(rnd, names, edges)
    vlans = [10, 20]
    init = _new_cfg(names, vlans, len(links))
    if level <= 2:
        # アクセス側(PC)と反対側(サーバ)を対角に置く= 2 本の道で分け合える
        i = rnd.randrange(len(names))
        a = names[i]
        far = [s for s in names if s != a and all(not ({x, y} == {a, s}) for x, _ix, y, _iy in links)]
        c = rnd.choice(far or [s for s in names if s != a])
        hs = {"PC1": a, "PC2": a, "SRV1": c, "SRV2": c}
    else:
        a, c, d, e = [rnd.choice(names) for _ in range(4)]
        hs = {"PC1": a, "SRV1": c, "PC2": d, "SRV2": e}
    return _board(shape, names, pos, links, init, ["prio", "cost"], vlans, [("PC1", "SRV1", 10), ("PC2", "SRV2", 20)],
                  rnd, host_sw=hs)


def base_s8(rnd, level):
    """Campus: ラボの 2 層/3 層の配線。全部のつまみ。お題= ルート ブリッジの指定＋経路 2 本。"""
    board = "2tier" if level <= 2 else "3tier"
    raw, layers, _pos, roles, _pools, _muts = sp._campus(board)
    pos = CAMPUS_POS[board]
    names = [x for layer in layers for x in layer]
    links = [(a, _te(ia + 1), c, _te(ic + 1)) for a, ia, c, ic in raw]
    init = _new_cfg(names, [1], len(links))
    top, acc = layers[0], layers[-1]
    p1, p2 = acc if rnd.random() < 0.5 else acc[::-1]
    s1 = rnd.choice(top)
    b = _board(board, names, pos, links, init, KINDS, [1], [("PC1", "SRV1", 1), ("PC2", "SRV1", 1)], rnd,
               roles=roles, host_sw={"PC1": p1, "PC2": p2, "SRV1": s1})
    b["layers"] = layers
    return b


BASE = {1: base_s1, 2: base_s2, 3: base_s3, 4: base_s4, 5: base_s5, 6: base_s6, 7: base_s7, 8: base_s8}

# level ごとの作り方: k= 生成で変えるつまみの数(VLAN ごとの時は VLAN ごと)・par= 受け入れる最少手数・kind= お題の種類
# plain= 目標の経路が同点の決着に頼らない(ステージ 1 はルートを選ぶだけで解ける)・keep= ルートは動かさない(お題にも出す)
SPEC = {
    1: [dict(k=1, par=(1, 1), kind="via", plain=True), dict(k=1, par=(1, 1), kind="path", plain=True),
        dict(k=1, par=(1, 1), kind="via", plain=True), dict(k=1, par=(1, 1), kind="path", plain=True),
        dict(k=1, par=(1, 1), kind="path", plain=True)],
    2: [dict(k=1, par=(1, 1), kind="path", keep=True, root=True), dict(k=1, par=(1, 1), kind="path", keep=True, root=True),
        dict(k=1, par=(1, 1), kind="path", keep=True, root=True), dict(k=2, par=(2, 2), kind="path"),
        dict(k=2, par=(2, 2), kind="path")],
    3: [dict(k=1, par=(1, 1), kind="path"), dict(k=1, par=(1, 1), kind="path"), dict(k=2, par=(2, 2), kind="path"),
        dict(k=2, par=(2, 2), kind="path"), dict(k=3, par=(2, 3), kind="path")],
    4: [dict(k=1, par=(1, 1), kind="path"), dict(k=1, par=(1, 1), kind="path"), dict(k=2, par=(2, 2), kind="path"),
        dict(k=2, par=(2, 2), kind="path"), dict(k=2, par=(2, 2), kind="path")],
    5: [dict(k=1, par=(1, 1), kind="path"), dict(k=1, par=(1, 1), kind="path"), dict(k=1, par=(1, 1), kind="path"),
        dict(k=2, par=(2, 2), kind="path"), dict(k=2, par=(2, 2), kind="path")],
    6: [dict(k=2, par=(1, 2), kind="path"), dict(k=2, par=(2, 2), kind="path"), dict(k=2, par=(2, 2), kind="path"),
        dict(k=3, par=(2, 3), kind="path"), dict(k=3, par=(2, 3), kind="path")],
    # ステージ 7 の k= VLAN ごとの (ルートの付け替え 1 ＋ 追加の変更)。ルートは VLAN ごとに別のスイッチ
    7: [dict(k=(1, 1), par=(1, 1), kind="path"), dict(k=(1, 1), par=(2, 2), kind="path"), dict(k=(1, 1), par=(2, 2), kind="path"),
        dict(k=(2, 1), par=(2, 3), kind="path"), dict(k=(2, 2), par=(3, 4), kind="path")],
    8: [dict(k=2, par=(1, 2), kind="path", root=True), dict(k=2, par=(2, 2), kind="path", root=True),
        dict(k=2, par=(2, 2), kind="path", root=True), dict(k=3, par=(2, 3), kind="path", root=True),
        dict(k=3, par=(3, 3), kind="path", root=True)],
}


def _tied(t, s):
    """s のルート ポートが同点の決着で決まったか(RPC が最小になる受信の候補が 2 つ以上)。"""
    cand = []
    for a, ia, c, ic, spd in t.links:
        for me, mi, n in ((a, ia, c), (c, ic, a)):
            if me == s:
                cand.append(t.rpc[n] + t.pcost(s, mi, spd))
    return cand.count(min(cand)) > 1


def _route_tied(b, cfg, v, src, dst):
    """src → dst の経路が同点の決着に頼るか= 経路の上のスイッチ(いちばんルート寄りの 1 台を除く)のルート ポートに同点がある。"""
    t = topo(b, cfg, v)
    sws, _lis = route(t, host_sw(b, src), host_sw(b, dst))
    top = min(sws, key=lambda x: t.rpc[x])
    return any(_tied(t, x) for x in sws if x != top)


def _mutate_keep(rnd, b, k):
    """ルートはそのままで、ほかのスイッチのプライオリティを k 台変える(ルートより大きい値だけ)= 変わるのは同点の決着だけ。"""
    init = b["init"]
    r = topo(b, init, 1).root
    cfg = _copy(init)
    for s in rnd.sample([x for x in b["names"] if x != r], k):
        vals = [x for x in [8192, 16384, 24576, 28672, 36864, 40960, 49152, 61440]
                if x > init["prio"][1][r] and x != init["prio"][1][s]]
        cfg["prio"][1][s] = rnd.choice(vals)
    return cfg


def _mutate(rnd, b, k, vlans=None, start=None):
    """初期状態(start があればそこ)から k 個のつまみを変えた目標(在庫の上限は守る)。値は本物の範囲から選ぶ。"""
    opts = options(b, vlans)
    if start is not None:
        moved = set(diff(b, start))
        opts = [o for o in opts if o[0] not in moved]
    for _ in range(50):
        cfg = _copy(start if start is not None else b["init"])
        for kn, dom in rnd.sample(opts, min(k, len(opts))):
            if kn[0] == "prio":
                vals = [x for x in [0, 4096, 8192, 16384, 24576, 28672, 36864, 40960, 61440] if x != b["init"]["prio"][kn[1]][kn[2]]]
            elif kn[0] == "pprio":
                vals = [x for x in [32, 64, 96, 112, 144, 160, 192, 224] if x != b["init"]["pprio"][kn[1]].get(kn[2], DEF_PPRIO)]
            else:
                vals = dom
            setk(cfg, kn, rnd.choice(vals))
        if limit_ok(b, cfg):
            return cfg
    return None


def _routes(b, cfg):
    return [route(topo(b, cfg, v), host_sw(b, a), host_sw(b, c))[1] for a, c, v in b["flows"]]


def _mutate_steps(rnd, b, k):
    """1 手ずつ積む目標: どの手も、その時点のどれかの流れの経路を実際に変える(空振りの手を入れない)。"""
    cfg = _copy(b["init"])
    was = _routes(b, cfg)
    for _ in range(k):
        for _try in range(30):
            m = _mutate(rnd, b, 1, start=cfg)
            if m is None:
                return None
            now = _routes(b, m)
            if now != was:
                cfg, was = m, now
                break
        else:
            return None
    return cfg


def _mutate_campus(rnd, b, k):
    """キャンパス: 上の層の 1 台を root primary 相当(24576)に。もう 1 台を secondary 相当(28672)にすることがある。残りは他のつまみ。"""
    cfg = _copy(b["init"])
    top = b["layers"][0]
    r = rnd.choice(top)
    cfg["prio"][1][r] = 24576
    used = 1
    if k >= 2 and rnd.random() < 0.5:
        cfg["prio"][1][rnd.choice([s for s in top if s != r])] = 28672
        used += 1
    opts = [o for o in options(b) if o[0][0] != "prio"]
    for kn, dom in rnd.sample(opts, k - used):
        setk(cfg, kn, rnd.choice(dom))
    return cfg


def _reqs_from(b, tgt, spec, rnd):
    """目標の木からお題を作る。初期の木と同じになる流れは、他の流れが変わる時だけ残す。"""
    reqs = []
    changed = False
    for src, dst, v in b["flows"]:
        ti, tt = topo(b, b["init"], v), topo(b, tgt, v)
        si, li = route(ti, host_sw(b, src), host_sw(b, dst))
        st, lt = route(tt, host_sw(b, src), host_sw(b, dst))
        if lt != li:
            changed = True
        if spec["kind"] == "via":
            cand = [s for s in st[1:-1] if s not in si]
            if not cand:
                return None
            reqs.append({"kind": "via", "vlan": v, "src": src, "dst": dst, "via": rnd.choice(cand)})
        else:
            reqs.append({"kind": "path", "vlan": v, "src": src, "dst": dst, "links": lt, "sws": st})
    if not changed:
        return None
    if spec.get("root"):
        v = b["vlans"][0]
        r = topo(b, tgt, v).root
        reqs.insert(0, {"kind": "root", "vlan": v, "sw": r, "keep": r == topo(b, b["init"], v).root})
    return reqs


def _attempt(stage, level, rnd):
    spec = SPEC[stage][level - 1]
    b = BASE[stage](rnd, level)
    if _finish_layout(b) > 0:
        return None
    b["stage"] = stage
    if stage == S_VLAN:
        # VLAN ごとに独立(使えるつまみは VLAN ごと)= 最少手数は VLAN ごとの和
        # 負荷分散の定番= VLAN ごとに別のスイッチをルートにする(root primary 相当の 24576)＋level 4〜5 は追加の変更
        tgt = _copy(b["init"])
        for v, s in zip(b["vlans"], rnd.sample(b["names"], 2)):
            tgt["prio"][v][s] = 24576
        for (src, dst, v), kv in zip(b["flows"], spec["k"]):
            if kv > 1:
                # 追加の変更は、その VLAN の経路を実際に変えるものだけ(空振りを避ける)
                was = route(topo(b, tgt, v), host_sw(b, src), host_sw(b, dst))[1]
                for _ in range(20):
                    m = _mutate(rnd, b, kv - 1, [v], start=tgt)
                    if m is not None and route(topo(b, m, v), host_sw(b, src), host_sw(b, dst))[1] != was:
                        break
                else:
                    return None
                tgt["prio"][v], tgt["cost"][v] = m["prio"][v], m["cost"][v]
        b["reqs"] = _reqs_from(b, tgt, spec, rnd)
        if not b["reqs"]:
            return None
        if level <= 2 and b["reqs"][0]["sws"] == b["reqs"][1]["sws"]:
            return None                                  # 分け合えていない
        par, sol = 0, _copy(b["init"])
        for v, kv in zip(b["vlans"], spec["k"]):
            d, c = search(b, min(kv - 1, 2), [v])
            if d is None:
                d, c = kv, tgt
            par += d
            sol["prio"][v], sol["cost"][v] = c["prio"][v], c["cost"][v]
    else:
        k = spec["k"]
        # 目標の作り方は 2 通りを半々: 1 手ごとに経路が変わる積み方(空振りが無い)と、でたらめに k か所
        # (途中の手が経路を変えない形= ルートを替えてから同点の決着を変える、などはこちらでしか出ない)
        if stage == S_CAMPUS:
            tgt = _mutate_campus(rnd, b, k)
        elif spec.get("keep"):
            tgt = _mutate_keep(rnd, b, k)
        else:
            tgt = _mutate_steps(rnd, b, k) if rnd.random() < 0.5 else _mutate(rnd, b, k)
        if tgt is None:
            return None
        if spec.get("plain") and any(_route_tied(b, tgt, v, a, c) for a, c, v in b["flows"]):
            return None
        b["reqs"] = _reqs_from(b, tgt, spec, rnd)
        if not b["reqs"]:
            return None
        if sat(b, b["init"]):
            return None
        d, sol = search(b, min(k - 1, 2))
        par = d if d is not None else k
        if d is None:
            sol = tgt
    if not (spec["par"][0] <= par <= spec["par"][1]) or not sat(b, sol):
        return None
    b["par"], b["sol"] = par, sol
    b["budget"] = par + (1 if stage == S_ENGINEER else 3 if level <= 2 else 2)
    return b


def seed_of(stage, level):
    return int(hashlib.sha1(f"stp-path/{stage}/{level}".encode()).hexdigest()[:12], 16)


@functools.lru_cache(maxsize=96)
def make(stage, level, seed=None):
    """盤面(お題・最少手数・解の一例つき)。seed= None ならステージ × level で決まる(いつ開いても同じ)。"""
    if stage not in READY or not 1 <= level <= LEVELS:
        raise ValueError("そのステージは遊べません")
    rnd = random.Random(seed_of(stage, level) if seed is None else seed)
    for _ in range(600):
        b = _attempt(stage, level, rnd)
        if b is not None:
            return b
    raise ValueError(f"ステージ {stage} level {level} の盤面が作れない")


# ==========================================================================
# 設定の JSON ⇔ 内部の形
# ==========================================================================
def _key(k):
    return f"{k[0]}|{k[1]}"


def cfg_json(b, cfg):
    return {"prio": {str(v): dict(cfg["prio"][v]) for v in b["vlans"]}, "speed": list(cfg["speed"]),
            "cost": {str(v): {_key(k): x for k, x in sorted(cfg["cost"][v].items())} for v in b["vlans"]},
            "pprio": {str(v): {_key(k): x for k, x in sorted(cfg["pprio"][v].items())} for v in b["vlans"]}}


def cfg_parse(b, obj):
    """画面から来た設定を検査して内部の形に。範囲外・未知のポート・開放されていないつまみの変更は ValueError。"""
    ports = set(_ports(b))
    cfg = _new_cfg(b["names"], b["vlans"], len(b["links"]))
    for v in b["vlans"]:
        pv = obj["prio"][str(v)]
        for s in b["names"]:
            x = int(pv[s])
            if x not in PRIOS:
                raise ValueError("priority は 0〜61440 の 4096 刻みです")
            cfg["prio"][v][s] = x
        for kind, dom in (("cost", COSTS), ("pprio", PPRIOS)):
            for ks, x in (obj.get(kind, {}).get(str(v)) or {}).items():
                k = tuple(ks.split("|", 1))
                if k not in ports or int(x) not in dom:
                    raise ValueError(f"{kind} の値かポートが不正です")
                if kind == "pprio" and int(x) == DEF_PPRIO:
                    continue
                cfg[kind][v][k] = int(x)
    spd = list(obj["speed"])
    if len(spd) != len(b["links"]) or any(x not in SPEEDS for x in spd):
        raise ValueError("speed が不正です")
    cfg["speed"] = spd
    for kn in diff(b, cfg):
        if kn[0] not in b["knobs"]:
            raise ValueError("このステージでは変えられない設定です")
    return cfg


# ==========================================================================
# 評価(画面がつまみを変えるたびに呼ぶ)
# ==========================================================================
def cli(b, cfg):
    """初期状態から変えた設定を IOS のコマンドで。[{sw, lines}]。"""
    init = b["init"]
    glob, ifs = {}, {}
    for kn in diff(b, cfg):
        if kn[0] == "prio":
            _k, v, s = kn
            glob.setdefault(s, []).append(f"spanning-tree vlan {v} priority {cfg['prio'][v][s]}")
        elif kn[0] == "speed":
            a, ia, c, ic = b["links"][kn[1]]
            for s, ifc in ((a, ia), (c, ic)):
                ifs.setdefault((s, ifc["num"], ifc["name"]), []).append(f" speed {SPEED_CLI[cfg['speed'][kn[1]]]}")
        elif kn[0] == "cost":
            _k, v, (s, ifn) = kn
            x = cfg["cost"][v].get((s, ifn))
            num = int(ifn.rsplit("/", 1)[1])
            ifs.setdefault((s, num, ifn), []).append(f" spanning-tree vlan {v} cost {x}" if x is not None
                                                     else f" no spanning-tree vlan {v} cost")
        else:
            _k, v, (s, ifn) = kn
            x = cfg["pprio"][v].get((s, ifn), DEF_PPRIO)
            num = int(ifn.rsplit("/", 1)[1])
            ifs.setdefault((s, num, ifn), []).append(f" spanning-tree vlan {v} port-priority {x}")
    del init
    out = []
    for s in b["names"]:
        lines = list(glob.get(s, []))
        for (s2, _num, ifn), ls in sorted(ifs.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            if s2 == s:
                lines += [f"interface {ifn}"] + ls
        if lines:
            out.append({"sw": s, "lines": lines})
    return out


def _explain(b, cfg, ts):
    """解説(押すと開く)。ポートの印をまだ見せないステージは ① ルート ブリッジの節だけ(盤面に出ていない話はしない)。"""
    full = "ports" in show_of(b.get("stage"))
    out = {}
    for v, t in ts.items():
        bx = {"names": b["names"], "prio": {v: cfg["prio"][v]}, "sw": b["sw"], "sysid": True, "links": t.links,
              "hosts": [{"sw": h["sw"], "if": h["if"]} for h in b["hosts"] if h["vlan"] == v]}
        ex = sp.explain(bx, t, v)
        out[str(v)] = ex if full else {lg: secs[:1] for lg, secs in ex.items()}
    return out


def stars_of(b, moves):
    if moves <= b["par"]:
        return 3
    if moves <= b["par"] + 1:
        return 2
    return 1


def evaluate(b, cfg, want_explain=False):
    ts = {v: topo(b, cfg, v) for v in b["vlans"]}
    res, _ = check(b, cfg, ts=ts)
    mv = len(diff(b, cfg))
    lok = limit_ok(b, cfg)
    ok = all(r["ok"] for r in res) and lok and mv <= b["budget"]
    vl = {}
    for v, t in ts.items():
        ports, cost, pid = {}, {}, {}
        for a, ia, c, ic, spd in t.links:
            for s, ifc in ((a, ia), (c, ic)):
                k = f"{s}|{ifc['name']}"
                r = t.role[(s, ifc["name"])]
                ports[k] = [r, "BLK" if r == "Altn" else "FWD"]
                cost[k] = t.pcost(s, ifc, spd)
                pid[k] = sp._pid(t, s, ifc)
        for h in b["hosts"]:
            k = f"{h['sw']}|{h['if']['name']}"
            ports[k] = ["Desg", "FWD"]
            pid[k] = f"{DEF_PPRIO}.{h['if']['num']}"
        rp = {s: t.rp.get(s) for s in b["names"]}
        vl[str(v)] = {"root": t.root, "rpc": dict(t.rpc), "rp": rp, "ports": ports, "cost": cost, "pid": pid,
                      "bid": {s: cfg["prio"][v][s] + v for s in b["names"]}}
    out = {"moves": mv, "limit_ok": lok, "ok": ok, "stars": stars_of(b, mv) if ok else 0,
           "reqs": res, "vlans": vl, "cli": cli(b, cfg)}
    if ok or want_explain:
        out["explain"] = _explain(b, cfg, ts)
        if mv > b["par"]:
            out["best"] = {"moves": b["par"], "cli": cli(b, b["sol"])}
    return out


# ==========================================================================
# 画面へ渡す形
# ==========================================================================
def payload(b, stage=None, level=None, seed=None):
    ports = []
    for li, (a, ia, c, ic) in enumerate(b["links"]):
        for s, ifc, n, nif in ((a, ia, c, ic), (c, ic, a, ia)):
            ports.append({"key": f"{s}|{ifc['name']}", "sw": s, "if": ifc["name"], "num": ifc["num"], "link": li,
                          "peer": n, "peer_if": nif["name"], "par": (s, ifc["name"]) in _par_groups(b)})
    for h in b["hosts"]:
        ports.append({"key": f"{h['sw']}|{h['if']['name']}", "sw": h["sw"], "if": h["if"]["name"], "num": h["if"]["num"],
                      "link": None, "host": h["name"], "peer": h["name"], "peer_if": "", "par": False})
    seen, links = {}, []
    for li, (a, ia, c, ic) in enumerate(b["links"]):
        seen.setdefault(frozenset((a, c)), []).append(li)
    for li, (a, ia, c, ic) in enumerate(b["links"]):
        grp = seen[frozenset((a, c))]
        off = 0 if len(grp) == 1 else (-1 if grp.index(li) == 0 else 1)
        links.append({"a": a, "ia": ia["name"], "b": c, "ib": ic["name"], "off": off})
    reqs = []
    for r in b["reqs"]:
        x = dict(r)
        x["vlan"] = r["vlan"]
        reqs.append(x)
    return {"stage": stage, "level": level, "seed": seed, "show": show_of(stage), "new": new_of(stage),
            "shape": b["shape"], "vlans": b["vlans"], "height": b["height"],
            "knobs": b["knobs"], "limit": b["limit"], "par": b["par"], "budget": b["budget"],
            "switches": [{"name": s, "x": b["pos"][s][0], "y": b["pos"][s][1], "mac": b["sw"][s]["mac"],
                          "role": b["roles"].get(s, "")} for s in b["names"]],
            "links": links, "ports": ports,
            "hosts": [{"name": h["name"], "kind": h["kind"], "sw": h["sw"], "if": h["if"]["name"], "x": h["x"], "y": h["y"],
                       "vlan": h["vlan"]} for h in b["hosts"]],
            "init": cfg_json(b, b["init"]), "reqs": reqs,
            "domains": {"prio": PRIOS, "pprio": PPRIOS, "speed": SPEEDS, "cost": COSTS},
            "cost_table": sm.COST[METHOD], "eval": evaluate(b, b["init"])}


def puzzle(stage, level, seed=None):
    b = make(stage, level, seed)
    return payload(b, stage, level, seed_of(stage, level) if seed is None else seed)


# チュートリアルの小さな例(値はすべて固定)。お題= 今の経路(帯と点が重なる)。
def _example(shape, prios, macs, speeds, ports, hosts, pp=None, cost=None):
    pos, edges = SHAPES[shape]
    names = [f"SW{i + 1}" for i in range(len(pos))]
    links = [(names[i], _te(na), names[j], _te(nb)) for (i, j), (na, nb) in zip(edges, ports)]
    init = _new_cfg(names, [1], len(links))
    init["prio"][1] = dict(zip(names, prios))
    init["speed"] = list(speeds)
    for k, x in (pp or {}).items():
        init["pprio"][1][k] = x
    for k, x in (cost or {}).items():
        init["cost"][1][k] = x
    rnd = random.Random(1)
    b = _board(shape, names, pos, links, init, [], [1], [("PC1", "SRV1", 1)], rnd, host_sw=hosts)
    b["sw"] = {s: {"mac": m} for s, m in zip(names, macs)}
    _finish_layout(b)
    t = topo(b, init, 1)
    sws, lis = route(t, hosts["PC1"], hosts["SRV1"])
    b["reqs"] = [{"kind": "path", "vlan": 1, "src": "PC1", "dst": "SRV1", "links": lis, "sws": sws}]
    b["par"], b["budget"], b["sol"] = 0, 0, init
    return b


EXAMPLES = {
    # 3 台とも既定の priority → MAC の最も小さい SW2 がルート。SW1 と SW3 の直結は止まり、SW2 を回る
    "ex_tree": lambda: _example("tri", [32768] * 3, ["0000.0000.0031", "0000.0000.0012", "0000.0000.0027"],
                                ["1G"] * 3, [(1, 1), (2, 1), (2, 2)], {"PC1": "SW1", "SRV1": "SW3"}),
    # ex_tree の SW1 を 24576 に下げた形: SW1 がルート。今度は SW2–SW3 が止まり、PC1 → SRV1 は直結
    "ex_tree_low": lambda: _example("tri", [24576, 32768, 32768], ["0000.0000.0031", "0000.0000.0012", "0000.0000.0027"],
                                    ["1G"] * 3, [(1, 1), (2, 1), (2, 2)], {"PC1": "SW1", "SRV1": "SW3"}),
    # 四角・ルート SW1(24576)。向かいの SW3 は SW2 経由も SW4 経由も 8 で同点 → 隣のブリッジ ID が小さい SW4(MAC 12)経由
    "ex_tie": lambda: _example("sq", [24576, 32768, 32768, 32768],
                               ["0000.0000.0031", "0000.0000.0027", "0000.0000.0045", "0000.0000.0012"],
                               ["1G"] * 4, [(1, 1), (2, 1), (2, 1), (2, 2)], {"PC1": "SW3", "SRV1": "SW1"}),
    # 四角・ルート SW1。SW3 は SW2 経由(4+4)と SW4 経由(19+4)を比べる
    "ex_cost": lambda: _example("sq", [24576, 32768, 32768, 32768],
                                ["0000.0000.0031", "0000.0000.0012", "0000.0000.0027", "0000.0000.0008"],
                                ["1G", "1G", "100M", "1G"], [(1, 1), (2, 1), (2, 1), (2, 2)], {"PC1": "SW3", "SRV1": "SW1"}),
    # ex_cost の SW3–SW4 を 10G に: SW4 経由 4+2=6 < SW2 経由 8 → SW3 のルート ポートは SW4 側へ
    "ex_cost10": lambda: _example("sq", [24576, 32768, 32768, 32768],
                                  ["0000.0000.0031", "0000.0000.0012", "0000.0000.0027", "0000.0000.0008"],
                                  ["1G", "1G", "10G", "1G"], [(1, 1), (2, 1), (2, 1), (2, 2)], {"PC1": "SW3", "SRV1": "SW1"}),
    # ex_tie の SW3 Te1/0/2(SW4 側)に cost 10: SW4 経由 4+10=14 > SW2 経由 8 → SW3 は SW2 側へ。SW4 は何も変わらない
    "ex_pcost": lambda: _example("sq", [24576, 32768, 32768, 32768],
                                 ["0000.0000.0031", "0000.0000.0027", "0000.0000.0045", "0000.0000.0012"],
                                 ["1G"] * 4, [(1, 1), (2, 1), (2, 1), (2, 2)], {"PC1": "SW3", "SRV1": "SW1"},
                                 cost={("SW3", "Te1/0/2"): 10}),
    # 並行リンク: SW2 のルート ポートは、上流 SW1 のポート ID(port-priority)で決まる
    "ex_pprio": lambda: _example("par", [24576, 32768, 32768], ["0000.0000.0031", "0000.0000.0012", "0000.0000.0027"],
                                 ["1G"] * 4, [(1, 1), (2, 2), (3, 1), (3, 2)], {"PC1": "SW2", "SRV1": "SW1"},
                                 pp={("SW1", "Te1/0/2"): 64}),
}


def example(name):
    b = EXAMPLES[name]()
    return payload(b)


# ==========================================================================
# ステージ定義と進み具合(保存の形は STP パズルと同じ)
# ==========================================================================
def load_stages():
    import yaml
    with open(os.path.join(GAME_DIR, "stages.yml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)["stages"]


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _cleared(st, sid):
    return sum(1 for x in st["stages"].get(str(sid), {}).get("levels", {}).values() if x.get("cleared"))


def load_state(path=STATE):
    """進み具合。v1(ステージ 2 を挟む前)の記録は、2 以降の番号を 1 つずつ後ろへずらして読む(ファイルも書き直す)。"""
    st = sp.load_state(path)
    if st.get("v", 1) < STATE_V:
        st["stages"] = {str(int(k) + 1 if int(k) >= S_ROLES else int(k)): x for k, x in st["stages"].items()}
        st["v"] = STATE_V
        if os.path.exists(path):
            sp.save_state(st, path)
    return st


def overview(path=STATE):
    st = load_state(path)
    out, prev_done = [], True
    for s in load_stages():
        sid = s["id"]
        rec = st["stages"].get(str(sid), {})
        ready = sid in READY
        out.append({"id": sid, "title": s["title"], "sub": s["sub"], "cards": s.get("cards", []),
                    "show": show_of(sid), "new": new_of(sid),
                    "ready": ready, "unlocked": ready and prev_done, "seen": bool(rec.get("seen")), "levels": LEVELS,
                    "progress": {k: {"stars": v.get("stars", 0), "revealed": v.get("revealed", False)}
                                 for k, v in rec.get("levels", {}).items() if v.get("cleared")}})
        prev_done = ready and _cleared(st, sid) >= LEVELS
    ex = sorted({c["example"] for s in out for c in s["cards"] if c.get("example")})
    return {"stages": out, "examples": {e: example(e) for e in ex}}


def record(stage, level, stars, revealed, path=STATE):
    st = load_state(path)
    rec = st["stages"].setdefault(str(stage), {}).setdefault("levels", {})
    old = rec.get(str(level), {})
    rec[str(level)] = {"cleared": True, "stars": max(int(stars), old.get("stars", 0)),
                       "revealed": bool(revealed) and not old.get("cleared"),
                       "tries": old.get("tries", 0) + 1, "at": _now()}
    sp.save_state(st, path)


def mark_seen(stage, path=STATE):
    st = load_state(path)
    st["stages"].setdefault(str(stage), {})["seen"] = _now()
    sp.save_state(st, path)


def reset(stage=None, path=STATE):
    st = load_state(path)
    if stage is None:
        st = {"v": STATE_V, "stages": {}, "reset_at": _now()}
    else:
        st["stages"].pop(str(stage), None)
    sp.save_state(st, path)


def summary(path=STATE):
    st = load_state(path)
    clear = sum(_cleared(st, s) for s in READY)
    stars = sum(v.get("stars", 0) for s in READY for v in st["stages"].get(str(s), {}).get("levels", {}).values())
    return clear, len(READY) * LEVELS, stars, len(READY) * LEVELS * 3


# ==========================================================================
# API(pack_server から呼ぶ)
# ==========================================================================
def _board_of(data):
    stage, level = int(data["stage"]), int(data["level"])
    sd = data.get("seed")
    seed = None if sd in (None, "") or int(sd) == seed_of(stage, level) else int(sd)
    return make(stage, level, seed)


def api(method, path, query, body, state_path=STATE):
    """(HTTP コード, JSON にする値)。path= /_api/stp_path/ より後ろ。"""
    try:
        if method == "GET" and path == "state":
            return 200, overview(state_path)
        if method == "GET" and path == "puzzle":
            sd = query.get("seed", [""])[0]
            return 200, puzzle(int(query.get("stage", ["0"])[0]), int(query.get("level", ["0"])[0]),
                               int(sd) if sd.isdigit() else None)
        if method == "POST":
            data = json.loads(body or b"{}")
            if path == "eval":
                b = _board_of(data)
                if data.get("reveal"):
                    out = evaluate(b, b["sol"], True)
                    out["cfg"] = cfg_json(b, b["sol"])
                    return 200, out
                return 200, evaluate(b, cfg_parse(b, data["cfg"]), bool(data.get("explain")))
            stage = data.get("stage")
            if stage is not None and int(stage) not in [s["id"] for s in load_stages()]:
                return 400, {"error": "stage が不正です"}
            if path == "result":
                lv = int(data["level"])
                if int(stage) not in READY or not 1 <= lv <= LEVELS:
                    return 400, {"error": "そのステージ・レベルは記録できません"}
                record(int(stage), lv, max(0, min(3, int(data.get("stars", 0)))), data.get("revealed"), state_path)
                return 200, {"ok": True}
            if path == "seen":
                mark_seen(int(stage), state_path)
                return 200, {"ok": True}
            if path == "reset":
                reset(None if stage is None else int(stage), state_path)
                return 200, {"ok": True}
        return 404, {"error": "not found"}
    except (ValueError, KeyError, TypeError) as e:
        return 400, {"error": str(e)}


# ==========================================================================
# selftest / show
# ==========================================================================
def _brute_min(b, maxd):
    """全域の値で総当たり(代表値に縮めた探索の検算用)。maxd 手以下の解があればその手数。"""
    init = b["init"]
    full = []
    for kn, _dom in options(b):
        if kn[0] == "prio":
            full.append((kn, [x for x in PRIOS if x != init["prio"][kn[1]][kn[2]]]))
        elif kn[0] == "pprio":
            full.append((kn, [x for x in PPRIOS if x != init["pprio"][kn[1]].get(kn[2], DEF_PPRIO)]))
        else:
            full.append((kn, _dom))
    if "pprio" in b["knobs"]:          # 並行リンク以外の Port Priority も入れて「効かない」ことを確かめる
        grp = _par_groups(b)
        for k in _ports(b):
            if k not in grp:
                full.append((("pprio", 1, k), [64]))
    for d in range(1, maxd + 1):
        for combo in itertools.combinations(full, d):
            for vals in itertools.product(*[o[1] for o in combo]):
                cfg = _copy(init)
                for (kn, _dom), val in zip(combo, vals):
                    setk(cfg, kn, val)
                if sat(b, cfg):
                    return d
    return None


def selftest(n=12):
    import time
    ng = 0

    def bad(msg):
        nonlocal ng
        ng += 1
        if ng <= 40:
            print("  NG", msg)

    stages = load_stages()
    ids = [s["id"] for s in stages]
    if ids != sorted(ids) or not set(READY) <= set(ids):
        bad(f"stages.yml の id {ids}")
    for s in stages:
        for k in ("title", "sub"):
            if not all(s.get(k, {}).get(x) for x in ("en", "ja")):
                bad(f"stage {s['id']} {k} の日英")
        if s["id"] in READY and not s.get("cards"):
            bad(f"stage {s['id']} にチュートリアルが無い")
        for c in s.get("cards", []):
            if not all(c.get(f, {}).get(x) for f in ("title", "body") for x in ("en", "ja")):
                bad(f"stage {s['id']} のカードの日英")
            if c.get("example") and c["example"] not in EXAMPLES:
                bad(f"例 {c['example']} が無い")
    for e in EXAMPLES:
        p = example(e)
        if not p["eval"]["ok"]:
            bad(f"例 {e} のお題が今の経路と合わない")
    # チュートリアルの札(notes): 指す先が例の盤面にあり、書いた役割が計算と合い、そのステージで見せているものを指す
    for st in stages:
        shw = show_of(st["id"])
        for c in st.get("cards", []):
            tag = f"stage {st['id']} 「{c['title']['ja']}」"
            notes, focus = c.get("notes") or [], c.get("focus")
            if (notes or focus is not None) and not c.get("example"):
                bad(f"{tag}: 札や focus があるのに例が無い")
                continue
            if not c.get("example"):
                continue
            p = example(c["example"])
            V = p["eval"]["vlans"][str(p["vlans"][0])]
            if focus is not None and (not set(focus) <= {"Root", "Desg", "Altn"} or "ports" not in shw):
                bad(f"{tag}: focus {focus}")
            for nt0 in notes:
                if not (nt0.get("en") and nt0.get("ja")):
                    bad(f"{tag}: 札の日英")
            # at はリストでもよい(同じ理由が当てはまる物すべて)。1 つずつ検算する
            for nt in [dict(x, at=a) for x in notes for a in (x["at"] if isinstance(x.get("at"), list) else [x.get("at", "")])]:
                kind, _, key = nt["at"].partition(":")
                if kind == "port":
                    if key not in V["ports"] or "ports" not in shw:
                        bad(f"{tag}: 札 {nt['at']} のポートが無いか、まだ見せていない")
                    elif nt.get("role") and V["ports"][key][0] != nt["role"]:
                        bad(f"{tag}: 札 {nt['at']} の役割 {nt['role']} が計算 {V['ports'][key][0]} と違う")
                elif kind == "sw":
                    if key not in [x["name"] for x in p["switches"]]:
                        bad(f"{tag}: 札 {nt['at']} のスイッチが無い")
                    if nt.get("root") is not None and (V["root"] == key) != nt["root"]:
                        bad(f"{tag}: 札 {nt['at']} のルートの有無が計算と違う")
                    if nt.get("rpc") is not None and V["rpc"][key] != nt["rpc"]:
                        bad(f"{tag}: 札 {nt['at']} の RPC {nt['rpc']} が計算 {V['rpc'][key]} と違う")
                elif kind == "host":
                    if key not in [h["name"] for h in p["hosts"]]:
                        bad(f"{tag}: 札 {nt['at']} の端末が無い")
                elif kind == "link":
                    a, _, b2 = key.partition("-")
                    li = [i for i, l in enumerate(p["links"]) if {l["a"], l["b"]} == {a, b2}]
                    if len(li) != 1:
                        bad(f"{tag}: 札 {nt['at']} のリンクが 1 本に決まらない")
                    elif nt.get("blocked") is not None:
                        l = p["links"][li[0]]
                        off = "Altn" in (V["ports"][f"{l['a']}|{l['ia']}"][0], V["ports"][f"{l['b']}|{l['ib']}"][0])
                        if off != nt["blocked"]:
                            bad(f"{tag}: 札 {nt['at']} の止まる/止まらないが計算と違う")
                else:
                    bad(f"{tag}: 札の指す先 {nt.get('at')}")
    # 例の中身(チュートリアルの説明と合うこと)
    ex = EXAMPLES["ex_tree"]()
    if topo(ex, ex["init"], 1).root != "SW2" or ex["reqs"][0]["sws"] != ["SW1", "SW2", "SW3"]:
        bad("ex_tree の木")
    ex = EXAMPLES["ex_tie"]()
    t = topo(ex, ex["init"], 1)
    if t.root != "SW1" or ex["reqs"][0]["sws"] != ["SW3", "SW4", "SW1"] or not _tied(t, "SW3"):
        bad("ex_tie の木(SW3 は同点で SW4 経由)")
    ex = EXAMPLES["ex_pprio"]()
    t = topo(ex, ex["init"], 1)
    if t.rp["SW2"] != next(ic["name"] for a, ia, c, ic in ex["links"] if a == "SW1" and ia["name"] == "Te1/0/2"):
        bad("ex_pprio: SW2 のルート ポートが SW1 Te1/0/2 の先でない")
    tm = {}
    for stage in READY:
        for level in range(1, LEVELS + 1):
            t0 = time.time()
            for i in range(n):
                seed = None if i == 0 else i * 7919 + level
                try:
                    b = make(stage, level, seed)
                except ValueError as e:
                    bad(f"s{stage} l{level} seed{seed} {e}")
                    continue
                tag = f"s{stage} l{level} seed{seed}"
                if sat(b, b["init"]):
                    bad(f"{tag} 初期状態でお題を満たす")
                if not sat(b, b["sol"]) or len(diff(b, b["sol"])) != b["par"]:
                    bad(f"{tag} 解の手数 {len(diff(b, b['sol']))} が最少 {b['par']} と違う")
                if not limit_ok(b, b["sol"]):
                    bad(f"{tag} 解が在庫を超える")
                for kn in diff(b, b["sol"]):
                    if kn[0] not in b["knobs"]:
                        bad(f"{tag} 解が開放されていないつまみを使う")
                spec = SPEC[stage][level - 1]
                lo, hi = spec["par"]
                if not lo <= b["par"] <= hi:
                    bad(f"{tag} 最少手数 {b['par']} が範囲外")
                # まだ見せていない値で答えが決まらないこと(設計 §10)
                shw = show_of(stage)
                if "portid" not in shw and _par_groups(b):
                    bad(f"{tag} ポート ID を見せる前に並行リンク")
                if "speed" not in shw and len(set(b["init"]["speed"]) | set(b["sol"]["speed"])) != 1:
                    bad(f"{tag} 速度を見せる前に速度が混ざる")
                if "pcost" not in shw and any(b["init"]["cost"][v] or b["sol"]["cost"][v] for v in b["vlans"]):
                    bad(f"{tag} ポート コストを見せる前に手で決めたコスト")
                if spec.get("plain") and any(_route_tied(b, b["sol"], v, a, c) for a, c, v in b["flows"]):
                    bad(f"{tag} 答えの経路が同点の決着に頼る")
                if spec.get("keep"):
                    v0 = b["vlans"][0]
                    if topo(b, b["sol"], v0).root != topo(b, b["init"], v0).root or not b["reqs"][0].get("keep"):
                        bad(f"{tag} ルートを動かさない問でルートが動く")
                ev = evaluate(b, b["sol"])
                if not ev["ok"] or ev["stars"] != 3 or "explain" not in ev:
                    bad(f"{tag} 解の評価")
                p = payload(b, stage, level, seed)
                js = cfg_parse(b, p["init"])
                if diff(b, js):
                    bad(f"{tag} 初期設定の JSON が往復しない")
                if diff(b, cfg_parse(b, cfg_json(b, b["sol"]))) != diff(b, b["sol"]):
                    bad(f"{tag} 解の JSON が往復しない")
                if p["eval"]["ok"]:
                    bad(f"{tag} 初期の評価が ok")
                keys = {x["key"] for x in p["ports"]}
                if len(keys) != len(p["ports"]):
                    bad(f"{tag} ポートの重複")
                for v, x in p["eval"]["vlans"].items():
                    if set(x["ports"]) != keys:
                        bad(f"{tag} 評価のポートが盤面と違う")
                for h in p["hosts"]:
                    if not (HW <= h["x"] <= W - HW) or h["y"] - HH < 0 or h["y"] + HH > p["height"]:
                        bad(f"{tag} 端末 {h['name']} が図の外")
                # 総当たりの検算(小さい盤面だけ・全域の値で par−1 手以下の解が無い)
                if stage in (1, 2, 3, 5) and i < 4 and b["par"] >= 2:
                    if _brute_min(b, b["par"] - 1) is not None:
                        bad(f"{tag} 全域の総当たりでより少ない解がある")
                if stage in (4, 6, 8) and i < 2 and b["par"] >= 2:
                    if _brute_min(b, 1) is not None:
                        bad(f"{tag} 全域の値で 1 手の解がある")
            tm[(stage, level)] = (time.time() - t0) / n
            # 決定性
            if json.dumps(puzzle(stage, level), sort_keys=True) != json.dumps(puzzle(stage, level), sort_keys=True):
                bad(f"s{stage} l{level} が決定的でない")
    slow = sorted(tm.items(), key=lambda kv: -kv[1])[:3]
    print("  生成の平均(遅い順): " + ", ".join(f"s{s}l{l} {x:.2f}s" for (s, l), x in slow))
    # 判定: Port Priority は下流(受信側)では効かない・上流で効く(実機 M4 と同じ向き)
    b = make(5, 1)
    pair = [(a, ia, c, ic) for a, ia, c, ic in b["links"] if {a, c} == {"SW1", "SW2"}]
    t = topo(b, b["init"], 1)
    if t.root == "SW1":
        cfg = _copy(b["init"])
        for a, ia, c, ic in pair:
            down = (c, ic["name"]) if c == "SW2" else (a, ia["name"])
            cfg["pprio"][1][down] = 0
        if topo(b, cfg, 1).rp["SW2"] != t.rp["SW2"]:
            bad("下流の port-priority で SW2 のルート ポートが変わった")
    # 不正な設定を断る
    b = make(1, 1)
    good = cfg_json(b, b["init"])
    for mutate, why in ((lambda c: c["prio"]["1"].update({"SW1": 1000}), "4096 刻みでない priority"),
                        (lambda c: c["speed"].__setitem__(0, "40G"), "未知の速度"),
                        (lambda c: c["cost"]["1"].update({"SW1|Te1/0/9": 4}), "無いポート"),
                        (lambda c: c["speed"].__setitem__(0, "10G"), "開放されていないつまみ")):
        c = json.loads(json.dumps(good))
        mutate(c)
        code, _o = api("POST", "eval", {}, json.dumps({"stage": 1, "level": 1, "cfg": c}).encode())
        if code != 400:
            bad(f"{why}を断らない")
    code, o = api("POST", "eval", {}, json.dumps({"stage": 1, "level": 1, "reveal": True}).encode())
    if code != 200 or not o["ok"] or o["stars"] != 3:
        bad("答えを見る")
    # 手数の上限を超えたら ok にしない
    b = make(S_ENGINEER, 2)
    over = _copy(b["sol"])
    extra = [kn for kn, dom in options(b) if kn not in diff(b, over)]
    for kn in extra[: b["budget"]]:
        dom = dict(options(b))[kn]
        setk(over, kn, dom[0])
    if len(diff(b, over)) > b["budget"] and evaluate(b, over)["ok"]:
        bad("上限を超えても ok")
    # 進み具合
    tmp = os.path.join(tempfile.mkdtemp(), "st.json")
    # 旧い番号(v1)の記録は 2 以降を 1 つ後ろへ
    sp.save_state({"v": 1, "stages": {"1": {"seen": "x"}, "2": {"seen": "y"}, "5": {"seen": "z"}}}, tmp)
    if sorted(load_state(tmp)["stages"]) != ["1", "3", "6"] or sp.load_state(tmp).get("v") != STATE_V:
        bad("v1 の記録の番号ずらし")
    if sorted(load_state(tmp)["stages"]) != ["1", "3", "6"]:
        bad("番号ずらしが 2 回効く")
    os.unlink(tmp)
    record(1, 1, 3, False, tmp)
    record(1, 1, 2, False, tmp)
    if load_state(tmp)["stages"]["1"]["levels"]["1"]["stars"] != 3:
        bad("星は最高を残す")
    for lv in range(2, LEVELS + 1):
        record(1, lv, 0, True, tmp)
    ov = overview(tmp)
    if not ov["stages"][1]["unlocked"] or ov["stages"][2]["unlocked"]:
        bad("鍵の開き方")
    mark_seen(2, tmp)
    reset(1, tmp)
    st = load_state(tmp)
    if "1" in st["stages"] or "2" not in st["stages"]:
        bad("ステージだけのリセット")
    reset(None, tmp)
    if load_state(tmp)["stages"]:
        bad("全体のリセット")
    code, _ = api("POST", "result", {}, json.dumps({"stage": 9, "level": 1}).encode(), tmp)
    if code != 400:
        bad("準備中のステージの記録を断る")
    print(f"[stp_path selftest] NG {ng}")
    return ng


def show(stage, level, seed=None):
    b = make(stage, level, seed)
    print(f"== stage {stage} level {level} shape={b['shape']} knobs={b['knobs']} par={b['par']} budget={b['budget']} limit={b['limit']}")
    for v in b["vlans"]:
        t = topo(b, b["init"], v)
        print(f"  VLAN {v} root={t.root}")
        for s in b["names"]:
            print(f"    {s} prio {b['init']['prio'][v][s]} mac {b['sw'][s]['mac']} rpc {t.rpc[s]}")
    for li, (a, ia, c, ic) in enumerate(b["links"]):
        print(f"  L{li} {a} {ia['name']} — {c} {ic['name']} {b['init']['speed'][li]}")
    for h in b["hosts"]:
        print(f"  {h['name']} @ {h['sw']} {h['if']['name']} VLAN {h['vlan']}")
    for r in b["reqs"]:
        print("  お題", r)
    for c in cli(b, b["sol"]):
        print(f"  解 {c['sw']}: " + " / ".join(c["lines"]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else None)
    else:
        raise SystemExit(selftest(int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "selftest" else 12))
