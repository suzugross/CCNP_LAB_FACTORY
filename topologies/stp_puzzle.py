#!/usr/bin/env python3
"""STP パズル(BL-268)— ポータルで遊ぶ「図の上でポートの役割と状態を埋める」ゲームのサーバ側。

盤面はステージ × level から seed を決めて作り、正解は stp_model(実機と照合済みの計算器)で出す。
画面(games/stp/index.html)には盤面・正解・解説をまとめて渡し、答え合わせはページの中で行う
(厳密さは要らない・反応を速くする。ユーザ決定)。サーバに残すのは進み具合だけ。

  ステージの名前とチュートリアル(日英)… games/stp/stages.yml
  進み具合(git 除外)……………………… topologies/_state/stp_puzzle.json(リセットできる)
  配信……………………………………………… pack_server.py の /_stp/(画面)と /_api/stp/*(下の api())

  python3 topologies/stp_puzzle.py selftest    … 全ステージ × 多数の seed で盤面の条件・解説・決定性を検査
  python3 topologies/stp_puzzle.py show 3 4    … ステージ 3 の level 4 の盤面と正解を表示

ステージ 1〜6 は既存の PoC(poc/stp/README.md 第2回・第3回)と stp_model で裏どり済み。
7〜9(MST・Backup ポート・ガード)は PoC の後に足す(READY に入れるまで画面では「準備中」)。
設計= problems/_drafts/STP-PUZZLE.design.md。ランダム モード(BL-269)は seed を乱数にするだけで足せる。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stp_model as sm                                  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.join(REPO, "games", "stp")
STATE = os.path.join(REPO, "topologies", "_state", "stp_puzzle.json")
LEVELS = 5
READY = [1, 2, 3, 4, 5, 6]

OUIS = ["0019.e8", "001a.a1", "5c50.15", "7c21.0e", "0023.04", "a0cf.5b"]
SPEED_TXT = {"10G": "10G", "1G": "1G", "100M": "100M"}


# ==========================================================================
# 部品
# ==========================================================================
def _mac(rnd, used):
    while True:
        m = f"{rnd.choice(OUIS)}{rnd.randint(0x10, 0xff):02x}.{rnd.randint(0x1000, 0xffff):04x}"
        if m not in used:
            used.add(m)
            return m


def _cat(sp, n):
    """Catalyst 9300 風の IF 名と port 番号(Gi1/0/n = n・Te1/1/n = 48 + n)。100M は Gi を速度 100 で使う。"""
    if sp == "10G":
        return {"name": f"Te1/1/{n}", "num": 48 + n}
    return {"name": f"Gi1/0/{n}", "num": n}


def _gv(i):
    """IOSvL2 の IF 名(Gi0/0 = 1 … Gi1/0 = 5)= ラボ GEN-STP の盤面と同じ。"""
    return {"name": f"Gi{i // 4}/{i % 4}", "num": i + 1}


# 形= (座標, 辺)。座標は幅 400 の SVG の上の箱の中心。辺の重複は並行リンク。
_SQ = [(85, 62), (315, 62), (315, 272), (85, 272)]
_TRI = [(200, 58), (70, 252), (330, 252)]


def _ring(n):
    import math
    return [(round(200 + 145 * math.cos(-math.pi / 2 + 2 * math.pi * i / n)),
             round(207 + 145 * math.sin(-math.pi / 2 + 2 * math.pi * i / n))) for i in range(n)]


SHAPES = {
    "tri": (_TRI, [(0, 1), (0, 2), (1, 2)]),
    "tripar": (_TRI, [(0, 1), (0, 2), (1, 2), (1, 2)]),
    "par": (_TRI, [(0, 1), (0, 1), (0, 2), (1, 2)]),
    "sq": (_SQ, [(0, 1), (1, 2), (2, 3), (3, 0)]),
    "sqd": (_SQ, [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]),
    "diamond": ([(200, 55), (80, 197), (320, 197), (200, 339)], [(0, 1), (0, 2), (1, 3), (2, 3)]),
    "mesh4": (_SQ, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]),
    "ladder": ([(100, 60), (100, 207), (100, 354), (300, 60), (300, 207), (300, 354)],      # 縦 2 本のレール＋横木 3 本
               [(0, 1), (1, 2), (3, 4), (4, 5), (0, 3), (1, 4), (2, 5)]),
    "bowtie": ([(70, 70), (70, 335), (200, 202), (330, 70), (330, 335)],
               [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 2)]),
    "tridual": ([(200, 55), (200, 320), (338, 188), (62, 188)], [(0, 1), (0, 2), (1, 2), (3, 0), (3, 1)]),
    "ring5c": (_ring(5), [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)]),        # 弦は生成時に足す
    "ring6c": (_ring(6), [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]),
}


def _wire(rnd, names, edges, speeds, gap=0):
    """辺に IF を割り当てる。スイッチごとに番号を混ぜる(Gi1/0/1 がいつも同じ向きにならない)。gap= 空き番号の数。"""
    need = {s: {"g": 0, "t": 0} for s in names}
    for (i, j), sp in zip(edges, speeds):
        k = "t" if sp == "10G" else "g"
        need[names[i]][k] += 1
        need[names[j]][k] += 1
    pool = {s: {k: rnd.sample(range(1, need[s][k] + 1 + gap), need[s][k]) for k in "gt"} for s in names}
    links = []
    for (i, j), sp in zip(edges, speeds):
        k = "t" if sp == "10G" else "g"
        a, b = names[i], names[j]
        links.append((a, _cat(sp, pool[a][k].pop()), b, _cat(sp, pool[b][k].pop()), sp))
    return links


def _board(shape, names, pos, links, sw, prio, method="short", vlans=(10,), cost_ovr=None, port_prio=None,
           hosts=None, show_cost=False, sysid=False, roles=None):
    return {"shape": shape, "names": list(names), "pos": dict(pos), "links": links, "sw": sw,
            "prio": prio, "method": method, "vlans": list(vlans), "cost_ovr": cost_ovr or {},
            "port_prio": port_prio or {}, "hosts": hosts or [], "show_cost": show_cost, "sysid": sysid,
            "roles": roles or {}}


def _topo(b, v):
    sw = {s: {"prio": b["prio"][v][s], "mac": b["sw"][s]["mac"]} for s in b["names"]}
    return sm.Topo(sw, b["links"], b["method"], b["port_prio"].get(v, {}), b["cost_ovr"].get(v, {}), v).solve()


def _decider_rp(t, s):
    """ルート ポートを決めた比較= cost / sbid / spid / opid と、候補の並び。"""
    cands = []
    for ifc, n, nif, sp in t.ports(s):
        own = t.pcost(s, ifc, sp)
        cands.append(((t.rpc[n] + own, t.bid(n), t.pid(n, nif), t.pid(s, ifc)), ifc, n, nif, own))
    cands.sort(key=lambda c: c[0])
    if len(cands) < 2:
        return "only", cands
    a, b = cands[0][0], cands[1][0]
    return ("cost" if a[0] != b[0] else "sbid" if a[1] != b[1] else "spid" if a[2] != b[2] else "opid"), cands


def _decider_dp(t, a, ia, b, ib):
    va = (t.rpc[a], t.bid(a), t.pid(a, ia))
    vb = (t.rpc[b], t.bid(b), t.pid(b, ib))
    return "cost" if va[0] != vb[0] else "bid" if va[1] != vb[1] else "pid"


def _tiebreaks(t):
    """コストの差でなく ID の比較で決まった判定(ルート ポート・指定ポート)の数。"""
    n = sum(1 for s in t.sw if s != t.root and _decider_rp(t, s)[0] in ("sbid", "spid", "opid"))
    n += sum(1 for a, ia, b, ib, _sp in t.links if a != t.root and b != t.root and _decider_dp(t, a, ia, b, ib) != "cost")
    return n


def _alts(t):
    return sum(1 for r in t.role.values() if r == "Altn")


# ==========================================================================
# ステージごとの生成
# ==========================================================================
def _prios_one_low(rnd, names, low=None):
    p = {s: 32768 for s in names}
    p[rnd.choice(names)] = low or rnd.choice([4096, 8192, 16384, 24576, 28672])
    return p


def gen_s1(rnd, level):
    """Root Bridge: 3 台の三角形・全 1G。1〜2= priority で決まる / 3= 全員既定(MAC)/ 4= 低い 2 台が同値 / 5= 混在。"""
    names = ["SW1", "SW2", "SW3"]
    pos, edges = SHAPES["tri"]
    used = set()
    sw = {s: {"mac": _mac(rnd, used)} for s in names}
    if level in (1, 2):
        p = _prios_one_low(rnd, names)
    elif level == 3:
        p = {s: 32768 for s in names}
    elif level == 4:
        v = rnd.choice([24576, 28672, 16384])
        lo = rnd.sample(names, 2)
        p = {s: (v if s in lo else 32768) for s in names}
    else:
        p = {s: rnd.choice([4096, 24576, 28672, 32768, 32768, 36864]) for s in names}
    links = _wire(rnd, names, edges, ["1G"] * 3)
    return _board("tri", names, dict(zip(names, pos)), links, sw, {10: p})


def gen_s2(rnd, level):
    """Path Cost: 速度が混在。少なくとも 1 台が「ルートとの直結」より回り道を選ぶ盤面だけ。1〜2 はリンクにコストも書く。"""
    shape = "tri" if level <= 3 else rnd.choice(["sq", "sqd"])
    pos, edges = SHAPES[shape]
    n = len(pos)
    names = [f"SW{i + 1}" for i in range(n)]
    used = set()
    sw = {s: {"mac": _mac(rnd, used)} for s in names}
    p = {s: rnd.choice([4096, 8192, 24576, 28672, 32768, 32768]) for s in names}
    speeds = [rnd.choice(["100M", "1G", "1G", "10G"]) for _ in edges]
    links = _wire(rnd, names, edges, speeds)
    return _board(shape, names, dict(zip(names, pos)), links, sw, {10: p}, show_cost=level <= 2)


def _detour(t):
    """ルートと直結しているのに、直結でない側をルート ポートにしたスイッチがあるか。"""
    for s in t.sw:
        if s == t.root:
            continue
        direct = [ifc["name"] for ifc, n, _ni, _sp in t.ports(s) if n == t.root]
        if direct and t.rp[s] not in direct:
            return True
    return False


def gen_s3(rnd, level):
    """Tie-Breakers: 1〜2= ひし形(同コスト→送信元 BID)/ 3= 並行リンク(送信元ポート ID)/
    4= 並行リンク＋上流の port-priority(逆転)/ 5= 並行リンク＋下流の port-priority(効かない)と上流の両方を抽選。"""
    used = set()
    if level <= 2:
        shape = "diamond"
        pos, edges = SHAPES[shape]
        names = ["SW1", "SW2", "SW3", "SW4"]
        sw = {s: {"mac": _mac(rnd, used)} for s in names}
        top = rnd.choice([4096, 8192, 24576])
        mid = [32768, 32768] if level == 1 else rnd.sample([28672, 32768, 36864], 2)
        p = {"SW1": top, "SW2": mid[0], "SW3": mid[1], "SW4": rnd.choice([32768, 36864, 40960])}
        links = _wire(rnd, names, edges, ["1G"] * 4)
        return _board(shape, names, dict(zip(names, pos)), links, sw, {10: p})
    shape = "par"
    pos, edges = SHAPES[shape]
    names = ["SW1", "SW2", "SW3"]
    sw = {s: {"mac": _mac(rnd, used)} for s in names}
    p = {"SW1": rnd.choice([4096, 8192, 24576]), "SW2": rnd.choice([28672, 32768]), "SW3": rnd.choice([32768, 36864])}
    links = _wire(rnd, names, edges, ["1G"] * 4, gap=rnd.randint(0, 2))
    pp = {}
    par = [ln for ln in links if {ln[0], ln[2]} == {"SW1", "SW2"}]
    if level >= 4:
        # 上流(SW1 側)の番号の大きい方を下げて逆転させる
        up = max(par, key=lambda ln: (ln[1] if ln[0] == "SW1" else ln[3])["num"])
        ifc = up[1] if up[0] == "SW1" else up[3]
        pp[("SW1", ifc["name"])] = rnd.choice([16, 32, 64, 96])
    if level == 5:
        dn = rnd.choice(par)
        ifc = dn[3] if dn[2] == "SW2" else dn[1]
        pp[("SW2", ifc["name"])] = rnd.choice([16, 32, 64])
        if rnd.random() < 0.5:
            pp.pop(next(k for k in pp if k[0] == "SW1"))
    return _board(shape, names, dict(zip(names, pos)), links, sw, {10: p}, port_prio={10: pp})


S4_SHAPES = ["ring5c", "ring6c", "mesh4", "ladder", "bowtie", "tridual", "sqd"]


def gen_s4(rnd, level):
    """Tuning: 4〜6 台。コストの手設定 1〜2 か所(どれかが結果を変える)・3 以降は long 方式が混ざる。"""
    shape = rnd.choice(S4_SHAPES)
    pos, edges = SHAPES[shape]
    edges = list(edges)
    n = len(pos)
    if shape in ("ring5c", "ring6c"):
        i = rnd.randrange(n)
        edges.append((i, (i + rnd.choice(range(2, n - 1))) % n))
    names = [f"SW{i + 1}" for i in range(n)]
    used = set()
    sw = {s: {"mac": _mac(rnd, used)} for s in names}
    p = {s: rnd.choice([4096, 8192, 24576, 28672, 32768, 32768, 32768, 36864]) for s in names}
    speeds = [rnd.choice(["1G", "1G", "1G", "10G"]) for _ in edges]
    method = "long" if level >= 3 and rnd.random() < 0.6 else "short"
    links = _wire(rnd, names, edges, speeds, gap=rnd.randint(0, 2))
    co = {}
    for _ in range(1 if level <= 2 else rnd.choice([1, 2])):
        a, ia, b, ib, _sp = rnd.choice(links)
        x, ifc = rnd.choice([(a, ia), (b, ib)])
        co[(x, ifc["name"])] = rnd.choice([30000, 50000, 100000] if method == "long" else [6, 10, 20, 30])
    return _board(shape, names, dict(zip(names, pos)), links, sw, {10: p}, method=method, cost_ovr={10: co})


def gen_s5(rnd, level):
    """Per-VLAN: 1 つの盤面に VLAN 2 つ。VLAN ごとにルートが別。4 以降は VLAN ごとの cost 設定が入る。"""
    shape = rnd.choice(["tri", "sq", "sqd"] if level <= 2 else ["sqd", "tridual", "mesh4", "diamond"])
    pos, edges = SHAPES[shape]
    n = len(pos)
    names = [f"SW{i + 1}" for i in range(n)]
    used = set()
    sw = {s: {"mac": _mac(rnd, used)} for s in names}
    va, vb = rnd.choice([(10, 20), (10, 30), (100, 200), (110, 120)])
    if level <= 3:
        a, b = rnd.sample(names, 2)
        pa = {s: 32768 for s in names}
        pb = dict(pa)
        pa[a], pa[b] = 24576, 28672
        pb[a], pb[b] = 28672, 24576
    else:
        pa = {s: rnd.choice([4096, 24576, 28672, 32768, 32768]) for s in names}
        pb = {s: rnd.choice([4096, 24576, 28672, 32768, 32768]) for s in names}
    speeds = [rnd.choice(["1G", "1G", "10G"]) for _ in edges]
    links = _wire(rnd, names, edges, speeds)
    co = {}
    if level >= 4:
        a, ia, b, ib, sp = rnd.choice(links)
        x, ifc = rnd.choice([(a, ia), (b, ib)])
        co[rnd.choice([va, vb])] = {(x, ifc["name"]): rnd.choice([10, 20, 30])}
    return _board(shape, names, dict(zip(names, pos)), links, sw, {va: pa, vb: pb}, vlans=(va, vb),
                  cost_ovr=co, sysid=True)


def _campus(board):
    if board == "3tier":
        import gen_stp_3tier as g3
        layers = [g3.CORE, g3.DIST, g3.ACC]
        pos = {"SW01": (100, 60), "SW02": (300, 60), "SW03": (100, 207), "SW04": (300, 207),
               "SW05": (100, 354), "SW06": (300, 354)}
        roles = {"SW01": "Core", "SW02": "Core", "SW03": "Distribution", "SW04": "Distribution",
                 "SW05": "Access", "SW06": "Access"}
        pools = [[24576, 28672, 32768], [28672, 32768, 36864], [32768, 32768, 36864]]
        muts = {"acc_link": ("add", ("SW05", 2, "SW06", 2)), "no_dsdl": ("del", ("SW03", 2, "SW04", 2))}
        return list(g3.LINKS), layers, pos, roles, pools, muts
    import gen_stp as g2
    layers = [g2.DS, g2.AS]
    pos = {"SW01": (100, 65), "SW02": (300, 65), "SW03": (100, 270), "SW04": (300, 270)}
    roles = {"SW01": "Distribution", "SW02": "Distribution", "SW03": "Access", "SW04": "Access"}
    pools = [[24576, 28672, 32768], [32768, 32768, 36864]]
    muts = {"acc_link": ("add", ("SW03", 2, "SW04", 2)), "one_dsdl": ("del", ("SW01", 1, "SW02", 1))}
    return list(g2.LINKS), layers, pos, roles, pools, muts


def gen_s6(rnd, level):
    """Campus: ラボ GEN-STP の 2 層/3 層の配線(IOSvL2 の IF 名)＋アクセスの端末(エッジ)。
    1= 2 層・設計どおり / 2= 2 層・自由 / 3= 2 層・崩し / 4= 3 層・設計どおり / 5= 3 層・自由＋崩し。"""
    board = "2tier" if level <= 3 else "3tier"
    raw, layers, pos, roles, pools, muts = _campus(board)
    if level in (3, 5):
        how, arg = muts[rnd.choice(sorted(muts))]
        raw.remove(arg) if how == "del" else raw.append(arg)
    names = [x for layer in layers for x in layer]
    used = set()
    sw = {s: {"mac": _mac(rnd, used)} for s in names}
    design = level in (1, 4)
    p = {}
    for li, layer in enumerate(layers):
        for x in layer:
            p[x] = rnd.choice(pools[li]) if design else rnd.choice([4096, 8192, 24576, 28672, 32768, 32768, 36864])
    method = rnd.choice(["short", "long"])
    links = [(a, _gv(ia), c, _gv(ic), "1G") for a, ia, c, ic in raw]
    co = {}
    if not design and rnd.random() < 0.6:
        a, ia, c, ic, _sp = rnd.choice(links)
        x, ifc = rnd.choice([(a, ia), (c, ic)])
        co[(x, ifc["name"])] = rnd.choice([30000, 50000] if method == "long" else [6, 10, 19])
    hosts = []
    for i, x in enumerate(layers[-1]):
        hx, hy = pos[x]
        hosts.append({"name": f"PC{i + 1}", "sw": x, "if": _gv(5), "x": hx, "y": hy + 92})
    return _board(board, names, pos, links, sw, {10: p}, method=method, cost_ovr={10: co}, hosts=hosts, roles=roles)


GEN = {1: gen_s1, 2: gen_s2, 3: gen_s3, 4: gen_s4, 5: gen_s5, 6: gen_s6}


def valid(stage, level, b):
    """盤面が破綻していないか(満たせば None・満たさなければ理由)。"""
    ts = {}
    for v in b["vlans"]:
        try:
            ts[v] = _topo(b, v)
        except ValueError as e:
            return str(e)
    for v, t in ts.items():
        if _alts(t) != len(b["links"]) - (len(b["names"]) - 1):
            return "代替の数が合わない"
    t = ts[b["vlans"][0]]
    if 2 * len(b["links"]) > 20:
        return "ポートが 20 を超える"
    if stage == 2 and not _detour(t):
        return "回り道を選ぶスイッチが無い"
    if stage == 3:
        if level <= 2:
            if t.root != "SW1" or _decider_rp(t, "SW4")[0] != "sbid":
                return "SW4 が送信元 BID で決まらない"
        else:
            if t.root != "SW1":
                return "SW1 がルートでない"
            want = "spid"
            if _decider_rp(t, "SW2")[0] != want:
                return "SW2 のルート ポートが送信元ポート ID で決まらない"
            if level >= 4 and any(k[0] == "SW1" for k in b["port_prio"].get(10, {})):
                b0 = dict(b, port_prio={})
                if _topo(b0, 10).rp["SW2"] == t.rp["SW2"]:
                    return "上流の port-priority が結果を変えていない"
    if stage == 4:
        if _alts(t) < 2:
            return "代替が 2 未満"
        b0 = dict(b, cost_ovr={})
        if _topo(b0, 10).role == t.role:
            return "コストの手設定が結果を変えていない"
    if stage == 5:
        va, vb = b["vlans"]
        if ts[va].root == ts[vb].root:
            return "VLAN でルートが同じ"
        if ts[va].role == ts[vb].role:
            return "VLAN で役割が同じ"
    if stage == 6 and _alts(t) < 2:
        return "代替が 2 未満"
    return None


def seed_of(stage, level, variant=0):
    h = hashlib.sha1(f"stp-puzzle/{stage}/{level}/{variant}".encode()).hexdigest()
    return int(h[:12], 16)


def make(stage, level, seed=None):
    """(盤面, {vlan: Topo})。seed= None ならステージ × level で決まる値(いつ開いても同じ盤面)。"""
    rnd = random.Random(seed_of(stage, level) if seed is None else seed)
    for _ in range(400):
        b = GEN[stage](rnd, level)
        if valid(stage, level, b) is None:
            return b, {v: _topo(b, v) for v in b["vlans"]}
    raise ValueError(f"ステージ {stage} level {level} の盤面が作れない")


# ==========================================================================
# 解説(日英)
# ==========================================================================
def _bid_txt(b, v, s):
    p = b["prio"][v][s]
    ext = f" ({p + v})" if b["sysid"] else ""
    return f"{p}{ext} · {b['sw'][s]['mac']}"


def explain(b, t, v):
    """{"en": [節], "ja": [節]}。節= {"h": 見出し, "lines": [行(**太字**・`code` を使う)]}。"""
    en, ja = [], []
    # ① ルート ブリッジ
    order = sorted(b["names"], key=t.bid)
    low = b["prio"][v][order[0]]
    tie = sum(1 for s in b["names"] if b["prio"][v][s] == low) > 1
    rows = [f"{'**' + s + '**' if s == t.root else s} — {_bid_txt(b, v, s)}" for s in order]
    en.append({"h": "① Root bridge", "lines": ["Lowest bridge ID wins: priority first, then MAC address."]
               + (["Shown in brackets: the priority as `show spanning-tree` prints it (priority + VLAN ID)."] if b["sysid"] else [])
               + rows + [f"Priority ties at {low}, so the lower MAC wins: **{t.root}**." if tie
                         else f"Decided by priority: **{t.root}**."]})
    ja.append({"h": "① ルート ブリッジ", "lines": ["ブリッジ ID が最も小さいスイッチがルート ブリッジです。先にプライオリティ、同じなら MAC アドレスを比べます。"]
               + (["かっこ内は `show spanning-tree` の表示(プライオリティ + VLAN ID)です。"] if b["sysid"] else [])
               + rows + [f"プライオリティが {low} で並ぶので、MAC アドレスの小さい **{t.root}** です。" if tie
                         else f"プライオリティで決まり、**{t.root}** です。"]})
    # ② ルート ポート
    le = ["Each other switch picks the port with the lowest root path cost (its own receiving port's cost + the neighbor's root path cost). "
          "On a tie: lower sender bridge ID, then lower sender port ID."]
    lj = ["ルート ブリッジ以外の各スイッチは、ルート パス コスト(自分の受信ポートのコスト + 隣のルート パス コスト)が最小のポートを選びます。"
          "同じなら送信元のブリッジ ID、次に送信元のポート ID が小さい方です。"]
    for s in b["names"]:
        if s == t.root:
            continue
        how, cands = _decider_rp(t, s)
        pe, pj = [], []
        for vec, ifc, n, nif, own in cands:
            calc = f"{own}" if t.rpc[n] == 0 else f"{t.rpc[n]} + {own} = {vec[0]}"
            src = f"{n} {nif['name']} · {_pid(t, n, nif)}" if how == "spid" else n     # ポート ID で決まる時は送信元のポートも
            pe.append(f"{ifc['name']} = {calc} (from {src})")
            pj.append(f"{ifc['name']} = {calc}({src} から)")
        best = cands[0]
        why_e = {"cost": "lowest cost", "only": "only path",
                 "sbid": f"same cost; sender {best[2]} has the lower bridge ID",
                 "spid": f"same cost and sender; sender port ID {_pid(t, best[2], best[3])} < {_pid(t, cands[1][2], cands[1][3])}",
                 "opid": "same cost, sender and sender port; lower own port ID"}[how]
        why_j = {"cost": "コストが最小", "only": "経路が 1 つだけ",
                 "sbid": f"コストが同じで、送信元 {best[2]} のブリッジ ID が小さい",
                 "spid": f"コストも送信元も同じで、送信元のポート ID が小さい: {_pid(t, best[2], best[3])} < {_pid(t, cands[1][2], cands[1][3])}",
                 "opid": "コスト・送信元・送信元のポートが同じで、自分のポート ID が小さい"}[how]
        le.append(f"**{s}**: " + " · ".join(pe) + f" → **{best[1]['name']}** ({why_e})")
        lj.append(f"**{s}**: " + " · ".join(pj) + f" → **{best[1]['name']}**({why_j})")
    en.append({"h": "② Root port of each switch", "lines": le})
    ja.append({"h": "② 各スイッチのルート ポート", "lines": lj})
    # ③ 指定ポート
    le = [f"Every port on the root bridge ({t.root}) is designated. On each other link, the end whose switch has the lower root path cost is designated; on a tie, the lower bridge ID."]
    lj = [f"ルート ブリッジ({t.root})のポートはすべて指定ポートです。それ以外のリンクでは、ルート パス コストが小さいスイッチの端が指定ポートになります。同じならブリッジ ID の小さい方です。"]
    for a, ia, c, ic, _sp in b["links"]:
        if t.root in (a, c):
            continue
        how = _decider_dp(t, a, ia, c, ic)
        d = (a, ia) if t.role[(a, ia["name"])] == "Desg" else (c, ic)
        head = f"{a} {ia['name']} — {c} {ic['name']}: {a} {t.rpc[a]} vs {c} {t.rpc[c]}"
        le.append(f"{head} → **{d[0]} {d[1]['name']}** ({'lower cost' if how == 'cost' else 'same cost; lower bridge ID'})")
        lj.append(f"{head} → **{d[0]} {d[1]['name']}**({'コストが小さい' if how == 'cost' else 'コストが同じで、ブリッジ ID が小さい'})")
    if len(le) == 1:
        le.append("(Every link here touches the root bridge.)")
        lj.append("(この盤面のリンクはすべてルート ブリッジにつながっています。)")
    en.append({"h": "③ Designated port on each link", "lines": le})
    ja.append({"h": "③ 各リンクの指定ポート", "lines": lj})
    # ④ 残り
    alts = [f"{s} {ifn}" for (s, ifn), r in sorted(t.role.items(), key=lambda kv: (b["names"].index(kv[0][0]), kv[0][1])) if r == "Altn"]
    L, N = len(b["links"]), len(b["names"])
    le = [f"Ports that are neither root nor designated become **alternate** ports: " + ", ".join(alts) + ".",
          f"Check: {L} links − ({N} switches − 1) = {L - N + 1} alternate port{'s' if L - N + 1 != 1 else ''}.",
          "Root and designated ports forward (**FWD**). Alternate ports discard frames (Cisco shows **BLK**)."]
    lj = ["ルート ポートにも指定ポートにもならなかったポートが**代替ポート**です: " + "、".join(alts) + "。",
          f"検算: リンク {L} 本 −(スイッチ {N} 台 − 1)= 代替ポート {L - N + 1} 個。",
          "ルート ポートと指定ポートはフォワーディング(**FWD**)。代替ポートはフレームを捨てます(Cisco の表示は **BLK**)。"]
    if b["hosts"]:
        le.append("Ports to PCs (PortFast edge) are designated and forwarding: " + ", ".join(f"{h['sw']} {h['if']['name']}" for h in b["hosts"]) + ".")
        lj.append("PC へのポート(PortFast のエッジ ポート)は指定ポートでフォワーディング: " + "、".join(f"{h['sw']} {h['if']['name']}" for h in b["hosts"]) + "。")
    en.append({"h": "④ The rest: alternate", "lines": le})
    ja.append({"h": "④ 残りは代替ポート", "lines": lj})
    return {"en": en, "ja": ja}


def _pid(t, s, ifc):
    pr, num = t.pid(s, ifc)
    return f"{pr}.{num}"


# ==========================================================================
# 画面へ渡す形
# ==========================================================================
def payload(b, ts, stage=None, level=None, seed=None):
    v0 = b["vlans"][0]
    t0 = ts[v0]
    ports = []
    for li, (a, ia, c, ic, sp) in enumerate(b["links"]):
        for s, ifc, n, nif in ((a, ia, c, ic), (c, ic, a, ia)):
            ports.append({"key": f"{s}|{ifc['name']}", "sw": s, "if": ifc["name"], "num": ifc["num"], "link": li,
                          "peer": n, "peer_if": nif["name"],
                          "cost": {str(v): ts[v].pcost(s, ifc, sp) for v in b["vlans"]},
                          "prio": {str(v): b["port_prio"].get(v, {}).get((s, ifc["name"]), 128) for v in b["vlans"]}})
    for h in b["hosts"]:
        ports.append({"key": f"{h['sw']}|{h['if']['name']}", "sw": h["sw"], "if": h["if"]["name"], "num": h["if"]["num"],
                      "link": None, "host": h["name"], "peer": h["name"], "peer_if": "",
                      "cost": {str(v): sm.COST[b["method"]]["1G"] for v in b["vlans"]},
                      "prio": {str(v): 128 for v in b["vlans"]}})
    # 並行リンク= 同じ 2 台を結ぶ 2 本目以降に向きの印(図で左右へずらす)
    seen = {}
    links = []
    for li, (a, ia, c, ic, sp) in enumerate(b["links"]):
        k = frozenset((a, c))
        seen.setdefault(k, []).append(li)
    for li, (a, ia, c, ic, sp) in enumerate(b["links"]):
        grp = seen[frozenset((a, c))]
        off = 0 if len(grp) == 1 else (-1 if grp.index(li) == 0 else 1)
        links.append({"a": a, "ia": ia["name"], "b": c, "ib": ic["name"], "speed": sp, "off": off,
                      "cost": sm.COST[b["method"]][sp] if b["show_cost"] else None})
    config = []
    for v in b["vlans"]:
        for (s, ifn), val in sorted(b["cost_ovr"].get(v, {}).items()):
            config.append({"sw": s, "if": ifn, "vlan": v, "kind": "cost", "val": val,
                           "cli": [f"interface {ifn}", f" spanning-tree vlan {v} cost {val}"]})
        for (s, ifn), val in sorted(b["port_prio"].get(v, {}).items()):
            config.append({"sw": s, "if": ifn, "vlan": v, "kind": "prio", "val": val,
                           "cli": [f"interface {ifn}", f" spanning-tree vlan {v} port-priority {val}"]})
    sol, exp = {}, {}
    for v, t in ts.items():
        pr = {f"{s}|{ifn}": [r, "BLK" if r == "Altn" else "FWD"] for (s, ifn), r in t.role.items()}
        for h in b["hosts"]:
            pr[f"{h['sw']}|{h['if']['name']}"] = ["Desg", "FWD"]
        sol[str(v)] = {"root": t.root, "ports": pr}
        exp[str(v)] = explain(b, t, v)
    h = max(y for _x, y in b["pos"].values())
    if b["hosts"]:
        h = max(h, max(x["y"] for x in b["hosts"]))
    return {"stage": stage, "level": level, "seed": seed, "shape": b["shape"], "method": b["method"],
            "vlans": b["vlans"], "sysid": b["sysid"], "height": h + 52,
            "switches": [{"name": s, "x": b["pos"][s][0], "y": b["pos"][s][1], "mac": b["sw"][s]["mac"],
                          "role": b["roles"].get(s, ""),
                          "prio": {str(v): b["prio"][v][s] for v in b["vlans"]}} for s in b["names"]],
            "links": links, "hosts": [{"name": x["name"], "sw": x["sw"], "if": x["if"]["name"], "x": x["x"], "y": x["y"]}
                                      for x in b["hosts"]],
            "ports": ports, "config": config, "cost_table": sm.COST[b["method"]],
            "roles": ["Root", "Desg", "Altn"], "states": ["FWD", "BLK"],
            "solution": sol, "explain": exp}


def puzzle(stage, level, seed=None):
    """seed= None はステージ × level で決まる盤面。数を渡すと別の盤面(画面の試験と、将来のランダム モード BL-269)。"""
    if stage not in READY or not 1 <= level <= LEVELS:
        raise ValueError("そのステージは遊べません")
    b, ts = make(stage, level, seed)
    return payload(b, ts, stage, level, seed_of(stage, level) if seed is None else seed)


# チュートリアルの小さな例(解いた状態で見せる)。値はすべて固定。
def _fixed(names, shape, prios, macs, speeds, ports, pp=None):
    pos, edges = SHAPES[shape]
    sw = {s: {"mac": m} for s, m in zip(names, macs)}
    links = []
    for (i, j), sp, (na, nb) in zip(edges, speeds, ports):
        links.append((names[i], _cat(sp, na), names[j], _cat(sp, nb), sp))
    return _board(shape, names, dict(zip(names, pos)), links, sw, {10: dict(zip(names, prios))},
                  port_prio={10: pp or {}}, show_cost=True)


EXAMPLES = {
    "ex_tri": lambda: _fixed(["SW1", "SW2", "SW3"], "tri", [24576, 32768, 32768],
                             ["001a.a1c0.1000", "0019.e811.2000", "5c50.15a2.3000"], ["1G"] * 3, [(1, 1), (2, 1), (2, 2)]),
    "ex_cost": lambda: _fixed(["SW1", "SW2", "SW3"], "tri", [24576, 32768, 32768],
                              ["001a.a1c0.1000", "0019.e811.2000", "5c50.15a2.3000"], ["1G", "100M", "1G"],
                              [(1, 1), (2, 1), (2, 2)]),
    "ex_par": lambda: _fixed(["SW1", "SW2", "SW3"], "par", [24576, 32768, 36864],
                             ["001a.a1c0.1000", "0019.e811.2000", "5c50.15a2.3000"], ["1G"] * 4,
                             [(1, 1), (2, 2), (3, 1), (3, 2)], pp={("SW1", "Gi1/0/2"): 64}),
}


def example(name):
    b = EXAMPLES[name]()
    return payload(b, {v: _topo(b, v) for v in b["vlans"]})


# ==========================================================================
# ステージ定義と進み具合
# ==========================================================================
def load_stages():
    import yaml
    with open(os.path.join(GAME_DIR, "stages.yml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)["stages"]


def load_state(path=STATE):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
        if isinstance(st, dict) and isinstance(st.get("stages"), dict):
            return st
    except (OSError, ValueError):
        pass
    return {"v": 1, "stages": {}}


def save_state(st, path=STATE):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".stp-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _cleared(st, sid):
    lv = st["stages"].get(str(sid), {}).get("levels", {})
    return sum(1 for x in lv.values() if x.get("cleared"))


def overview(path=STATE):
    """画面のホームに出すもの= ステージ(名前・チュートリアル・鍵・星)。"""
    st = load_state(path)
    out = []
    prev_done = True
    for s in load_stages():
        sid = s["id"]
        rec = st["stages"].get(str(sid), {})
        lv = rec.get("levels", {})
        ready = sid in READY
        unlocked = ready and prev_done
        out.append({"id": sid, "title": s["title"], "sub": s["sub"], "cards": s.get("cards", []),
                    "ready": ready, "unlocked": unlocked, "seen": bool(rec.get("seen")), "levels": LEVELS,
                    "progress": {k: {"stars": v.get("stars", 0), "revealed": v.get("revealed", False)}
                                 for k, v in lv.items() if v.get("cleared")}})
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
    save_state(st, path)


def mark_seen(stage, path=STATE):
    st = load_state(path)
    st["stages"].setdefault(str(stage), {})["seen"] = _now()
    save_state(st, path)


def reset(stage=None, path=STATE):
    st = load_state(path)
    if stage is None:
        st = {"v": 1, "stages": {}, "reset_at": _now()}
    else:
        st["stages"].pop(str(stage), None)
    save_state(st, path)


def summary(path=STATE):
    """ポータルの 1 行に出す (クリア数, 全問, 星, 星の最大)。"""
    st = load_state(path)
    clear = sum(_cleared(st, s) for s in READY)
    stars = sum(v.get("stars", 0) for s in READY for v in st["stages"].get(str(s), {}).get("levels", {}).values())
    return clear, len(READY) * LEVELS, stars, len(READY) * LEVELS * 3


# ==========================================================================
# API(pack_server から呼ぶ)
# ==========================================================================
def api(method, path, query, body, state_path=STATE):
    """(HTTP コード, JSON にする値)。path= /_api/stp/ より後ろ。"""
    try:
        if method == "GET" and path == "state":
            return 200, overview(state_path)
        if method == "GET" and path == "puzzle":
            sd = query.get("seed", [""])[0]
            return 200, puzzle(int(query.get("stage", ["0"])[0]), int(query.get("level", ["0"])[0]),
                               int(sd) if sd.isdigit() else None)
        if method == "POST":
            data = json.loads(body or b"{}")
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
def selftest(n=150):
    ng = 0

    def bad(msg):
        nonlocal ng
        ng += 1
        if ng <= 30:
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
        example(e)
    # 盤面の生成: 多数の seed で作れること・条件・解説・正解の形
    for stage in READY:
        for level in range(1, LEVELS + 1):
            fails = 0
            for i in range(n):
                try:
                    b, ts = make(stage, level, seed=i * 7919 + level)
                except ValueError:
                    fails += 1
                    continue
                p = payload(b, ts)
                keys = {x["key"] for x in p["ports"]}
                if len(keys) != len(p["ports"]):
                    bad(f"s{stage} l{level} seed{i} ポートの重複")
                for v, sol in p["solution"].items():
                    if set(sol["ports"]) != keys:
                        bad(f"s{stage} l{level} 正解のポートが盤面と違う")
                    roots = [k for k, (r, _st) in sol["ports"].items() if r == "Root"]
                    if len(roots) != len(b["names"]) - 1:
                        bad(f"s{stage} l{level} ルート ポートの数")
                    for lang in ("en", "ja"):
                        if len(p["explain"][v][lang]) != 4:
                            bad(f"s{stage} l{level} 解説の節")
                if stage == 1 and level == 3 and len({b["prio"][10][s] for s in b["names"]}) != 1:
                    bad("s1 l3 は全員既定のはず")
            if fails > n // 10:
                bad(f"s{stage} l{level} 作れない seed が {fails}/{n}")
            # 決定性: 同じステージ・level は同じ盤面
            if json.dumps(puzzle(stage, level), sort_keys=True) != json.dumps(puzzle(stage, level), sort_keys=True):
                bad(f"s{stage} l{level} が決定的でない")
    # 生成の手応え: ステージ 3 の level 5 で下流の port-priority が効かない例が出ること、など
    seen5 = set()
    for i in range(200):
        b, ts = make(3, 5, seed=i)
        seen5.add(tuple(sorted(k[0] for k in b["port_prio"][10])))
    if ("SW2",) not in seen5:
        bad("s3 l5 で下流だけの port-priority が出ない")
    # 進み具合の保存とリセット
    tmp = os.path.join(tempfile.mkdtemp(), "st.json")
    record(1, 1, 3, False, tmp)
    record(1, 1, 2, False, tmp)
    st = load_state(tmp)
    if st["stages"]["1"]["levels"]["1"]["stars"] != 3:
        bad("星は最高を残す")
    for lv in range(2, LEVELS + 1):
        record(1, lv, 0, True, tmp)
    ov = overview(tmp)
    if not ov["stages"][1]["unlocked"]:
        bad("ステージ 1 を全部クリアしたらステージ 2 が開く")
    if ov["stages"][2]["unlocked"]:
        bad("ステージ 3 は開かないはず")
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
    print(f"[stp_puzzle selftest] NG {ng}")
    return ng


def show(stage, level):
    b, ts = make(stage, level)
    for v, t in ts.items():
        print(f"== stage {stage} level {level} VLAN {v} shape={b['shape']} method={b['method']} root={t.root}")
        for s in b["names"]:
            print(f"  {s} prio {b['prio'][v][s]} mac {b['sw'][s]['mac']}")
        for a, ia, c, ic, sp in b["links"]:
            print(f"  {a} {ia['name']:<9} {t.role[(a, ia['name'])]} — {t.role[(c, ic['name'])]} {c} {ic['name']:<9} {sp}")
        for k, val in b["cost_ovr"].get(v, {}).items():
            print(f"  cost {k} {val}")
        for k, val in b["port_prio"].get(v, {}).items():
            print(f"  port-priority {k} {val}")
        for sec in explain(b, t, v)["ja"]:
            print("  #", sec["h"])
            for ln in sec["lines"]:
                print("    ", ln)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show(int(sys.argv[2]), int(sys.argv[3]))
    else:
        raise SystemExit(selftest())
