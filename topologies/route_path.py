#!/usr/bin/env python3
"""ルーティング経路づくり(BL-271)— 経路を足して、お題のルータを通すゲームのサーバ側。

STP 経路づくり(stp_path.py・BL-270)の L3 版。盤面とお題(「PC1 → SRV1 の通信を R1 → R2 → R4 の順に通す」)が先にあり、
解く側がインターフェース(ステージ 1)と static route(ステージ 2 から)を変えて、パケットの通り道を組み立てる。
経路の計算は route_model(IOS の決まりどおりの計算器)だけで行う。画面は変えるたびに eval を呼ぶ。

  ステージの名前とチュートリアル(日英)… games/route-path/stages.yml
  進み具合(git 除外)……………………… topologies/_state/route_path.json(リセットできる)
  配信……………………………………………… pack_server.py の /_route_path/(画面)と /_api/route_path/*(下の api())

  python3 topologies/route_path.py selftest [N]   … 全ステージの生成・最少手数(総当たりと照合)・判定・API・保存
  python3 topologies/route_path.py show 2 3       … ステージ 2 の level 3 の盤面・お題・最少の解

手数= 変更した設定の行数(`ip route`・`no ip route`・`ip address`・`no shutdown` など。`interface …` の行は数えない)。
最少手数: ステージ 1(インターフェースだけ)は総当たり。ステージ 2 からは、ルータごとに「変更の組 → 転送の判断」の表を作り、
お題を満たす道の組み合わせごとに各ルータの最少の行数を足して最小を取る(設計 §7)。
盤面に出すものはステージごとに増える(SHOW_FROM)。隠すのは表示だけで、計算はいつも全部。
設計= problems/_drafts/ROUTE-PATH.design.md。
"""
from __future__ import annotations

import functools
import hashlib
import ipaddress
import itertools
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_model as rm                                # noqa: E402
import stp_puzzle as sp                                 # noqa: E402  (進み具合の保存の部品だけ使う)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.join(REPO, "games", "route-path")
STATE = os.path.join(REPO, "topologies", "_state", "route_path.json")
LEVELS = 5
READY = [1, 2, 3, 4, 5]
STATE_V = 1

# 盤面に出すもの(設計 §6・§11)。値= そのステージから出る
SHOW_FROM = {"ifs": 1, "hostip": 1, "linkip": 2, "codes": 2, "back": 3, "internet": 4,
             "sites": 5, "lock": 5, "range": 5, "ad": 7, "fail": 7, "lo": 8, "showip": 8}
# 変えられるもの(ステージ → つまみ)
KNOBS = {1: {"if"}, 2: {"add"}, 3: {"add"}, 4: {"add", "del", "default"},
         5: {"add", "del", "default", "len"}, 6: {"add", "del", "default", "len"},
         7: {"add", "del", "default", "len", "ad"}}
AD_PRESETS = [1, 5, 10, 200, 250]


def show_of(stage):
    return sorted(k for k, v in SHOW_FROM.items() if v <= stage)


def new_of(stage):
    return sorted(k for k, v in SHOW_FROM.items() if v == stage)


# ==========================================================================
# 盤面の型(座標は手で決める・設計 §3「見本で決めた描き方」)
#   routers: 名前 → (x, y, 名前の札の向き l/r/t/b)
#   lans:    (ルータ, k, (x, y, w, h))  … LAN の札の箱
#   links:   (a, b, 札の位置(0〜1), 札を線から離す量)
#   sites:   ルータ → (x, y, w, h, 名前の位置 top/bottom)(ステージ 5 から見せる)
# ==========================================================================
W = 400
# ISP とのリンク: 100.64.0.0/10(RFC 6598・ISP とお客さまの間で使う共有アドレス)。203.0.113.0/24 は Internet の宛先に使う
ISP_LINKS = {("ISP", "R1"): "100.64.0.0/30", ("ISP", "R2"): "100.64.0.4/30", ("ISP", "R3"): "100.64.0.0/30"}
TPL = {
    "one2": {"routers": {"R1": (200, 172, "r")}, "links": [],
             "lans": [("R1", 1, (124, 22, 152, 62)), ("R1", 2, (124, 262, 152, 62))], "h": 340},
    "one3": {"routers": {"R1": (200, 192, "r")}, "links": [],
             "lans": [("R1", 1, (24, 22, 152, 62)), ("R1", 2, (224, 22, 152, 62)), ("R1", 3, (124, 290, 152, 62))],
             "h": 368},
    "line2": {"routers": {"R1": (100, 152, "l"), "R2": (300, 152, "r")}, "links": [("R1", "R2", .5, 0)],
              "lans": [("R1", 1, (24, 22, 152, 62)), ("R2", 1, (224, 22, 152, 62))], "h": 196},
    "line3": {"routers": {"R1": (70, 150, "b"), "R2": (200, 150, "b"), "R3": (330, 150, "b")},
              "links": [("R1", "R2", .5, 14), ("R2", "R3", .5, 14)],
              "lans": [("R1", 1, (8, 22, 124, 62)), ("R2", 1, (138, 22, 124, 62)), ("R3", 1, (268, 22, 124, 62))],
              "h": 196},
    "tri": {"routers": {"R2": (200, 150, "r"), "R1": (90, 290, "l"), "R3": (310, 290, "r")},
            "links": [("R1", "R2", .5, 0), ("R2", "R3", .5, 0), ("R1", "R3", .5, 0)],
            "lans": [("R2", 1, (124, 22, 152, 62)), ("R1", 1, (14, 330, 152, 62)), ("R3", 1, (234, 330, 152, 62))],
            "h": 404},
    "sq": {"routers": {"R1": (100, 140, "l"), "R2": (300, 140, "r"), "R3": (100, 280, "l"), "R4": (300, 280, "r")},
           "links": [("R1", "R2", .5, 0), ("R1", "R3", .5, 0), ("R2", "R4", .5, 0), ("R3", "R4", .5, 0)],
           "lans": [("R1", 1, (24, 30, 152, 62)), ("R2", 1, (224, 30, 152, 62)),
                    ("R3", 1, (24, 316, 152, 62)), ("R4", 1, (224, 316, 152, 62))],
           "sites": {"R1": (8, 8, 184, 112, "top"), "R2": (208, 8, 184, 112, "top"),
                     "R3": (8, 300, 184, 112, "bottom"), "R4": (208, 300, 184, 112, "bottom")},
           "h": 420},
    "house": {"routers": {"ISP": (200, 134, "r"), "R3": (200, 240, "l"), "R1": (90, 318, "l"), "R2": (310, 318, "r")},
              "links": [("ISP", "R3", .5, 0), ("R3", "R1", .5, 0), ("R3", "R2", .5, 0), ("R1", "R2", .5, 0)],
              "lans": [("R1", 1, (24, 358, 152, 62)), ("R2", 1, (224, 358, 152, 62))],
              "cloud": (200, 50, 330, 92), "fixed": ["ISP"],
              "sites": {"R1": (8, 342, 184, 112, "bottom"), "R2": (208, 342, 184, 112, "bottom")},
              "h": 462},
    "sqi": {"routers": {"ISP": (200, 132, "r"), "R1": (100, 216, "l"), "R2": (300, 216, "r"),
                        "R3": (100, 352, "l"), "R4": (300, 352, "r")},
            "links": [("ISP", "R1", .5, 0), ("ISP", "R2", .5, 0), ("R1", "R2", .5, 0), ("R1", "R3", .5, 0),
                      ("R2", "R4", .5, 0), ("R3", "R4", .5, 0)],
            "lans": [("R3", 1, (24, 390, 152, 62)), ("R4", 1, (224, 390, 152, 62))],
            "cloud": (200, 50, 330, 92), "fixed": ["ISP"],
            "sites": {"R3": (8, 374, 184, 112, "bottom"), "R4": (208, 374, 184, 112, "bottom")},
            "h": 494},
}
TPL["sqx"] = dict(TPL["sq"], links=TPL["sq"]["links"] + [("R2", "R3", .5, 0)])
# ステージ 5(ロンゲストマッチ): ひし形。上の R1 に PC1 の拠点、下の R4 の拠点に LAN 2 つ(/16 が拠点全体を指すのを見せる・設計 §17)
TPL["dia"] = {"routers": {"R1": (200, 150, "r"), "R2": (90, 244, "l"), "R3": (310, 244, "r"), "R4": (200, 330, "r")},
              "links": [("R1", "R2", .5, 0), ("R1", "R3", .5, 0), ("R2", "R4", .5, 0), ("R3", "R4", .5, 0)],
              "lans": [("R1", 1, (124, 30, 152, 62)), ("R4", 1, (24, 374, 152, 62)), ("R4", 2, (224, 374, 152, 62))],
              "sites": {"R1": (108, 8, 184, 112, "top"), "R4": (8, 358, 384, 112, "bottom")},
              "h": 480}
TPL["diax"] = dict(TPL["dia"], links=TPL["dia"]["links"] + [("R2", "R3", .5, 0)])
# 長さを選べるステージ(len)で書ける長さ= オクテットの切れ目だけ(ほかの長さは集約のステージ 6 で開く・設計 §17)。
# この決まりの中なら、宛先 IP x を含む長さ L の宛先は x を L で切ったものしかないので、最少手数の探索は「お題の宛先 IP × 長さ」で尽くせる
LENS = (0, 8, 16, 24, 32)
# Internet の宛先: 別々のネットワークに 3 台(文書用のアドレス RFC 5737)。1 つずつ書くと手数の上限を超え、デフォルト ルートで
# まとめて指すのが答えになる(2026-11-12 ユーザ提案・設計 §16)
INTERNET = [("Internet", "198.51.100.0/24", "WEB", "198.51.100.10"),
            ("Internet-2", "192.0.2.0/24", "DNS", "192.0.2.53"),
            ("Internet-3", "203.0.113.0/24", "MAIL", "203.0.113.25")]
INET_HOSTS = [x[2] for x in INTERNET]


LINK_BASES = ["10.0.0.0", "192.168.0.0", "172.31.0.0", "10.0.1.0"]      # 札が長くなりすぎない桁(対角線の札と重ならない)


def _link_blocks(rnd, n):
    """バラバラのリンクのアドレス: 1 つの /24 の中から /30 を n 個、順番と位置を乱数で選ぶ。[(prefix, 小さい方の IP, 大きい方の IP)]"""
    base = int(ipaddress.ip_address(rnd.choice(LINK_BASES)))
    out = []
    for sl in rnd.sample(range(1, 63), n):
        net_ = base + sl * 4
        out.append(("%s/30" % ipaddress.ip_address(net_), str(ipaddress.ip_address(net_ + 1)), str(ipaddress.ip_address(net_ + 2))))
    return out


def _build(tpl_name, lan_hosts, rnd=None, irregular=False):
    """型と端末の割り当て {(ルータ, k): [端末]} から盤面(route_model の nw＋座標)を作る。
    irregular= リンクのアドレスを 172.16.XY の決まりにせず、盤面ごとに違う /30 にする(どちらの端が小さい方かも乱数)。"""
    T = TPL[tpl_name]
    fixed = set(T.get("fixed", []))
    routers = [{"name": n, "site": rm.rnum(n) if n not in fixed else 0, "fixed": n in fixed} for n in T["routers"]]
    links = []
    blocks = _link_blocks(rnd, sum(1 for a, b, _, _ in T["links"] if "ISP" not in (a, b))) if irregular and rnd else []
    for a, b, _, _ in T["links"]:
        lk = {"a": a, "b": b}
        if blocks and "ISP" not in (a, b):
            p_, lo, hi = blocks.pop()
            lk.update(prefix=p_, ipa=lo, ipb=hi) if rnd.random() < .5 else lk.update(prefix=p_, ipa=hi, ipb=lo)
        elif a == "ISP" or b == "ISP":
            other = b if a == "ISP" else a
            p = ISP_LINKS[("ISP", other)]
            base = int(rm.net(p).network_address)
            lk.update(prefix=p)
            if a == "ISP":
                lk.update(ipa=str(ipaddress.ip_address(base + 1)), ipb=str(ipaddress.ip_address(base + 2)))
            else:
                lk.update(ipa=str(ipaddress.ip_address(base + 2)), ipb=str(ipaddress.ip_address(base + 1)))
        links.append(lk)
    lans = []
    for r, k, box in T["lans"]:
        lans.append({"router": r, "k": k, "hosts": lan_hosts.get((r, k), [])})
    if "ISP" in T["routers"]:
        for j, (lid, pfx, hn, hip) in enumerate(INTERNET):
            lans.insert(j, {"router": "ISP", "k": j + 1, "id": lid, "prefix": pfx,
                            "hosts": [{"name": hn, "kind": "srv", "ip": hip}]})
    nw = rm.build_net(routers, links, lans)
    # 座標
    for n, (x, y, lab) in T["routers"].items():
        nw["routers"][n].update(x=x, y=y, lab=lab)
    boxes = {(r, k): box for r, k, box in T["lans"]}
    for ln in nw["lans"]:
        if ln["id"].startswith("Internet"):
            cx, cy, w, h = T["cloud"]
            j = [x[0] for x in INTERNET].index(ln["id"])
            ln.update(cloud=True, box=[cx - w / 2, cy - h / 2, w, h], slot=j, nslot=len(INTERNET))
        else:
            k = int(ln["id"].split("-")[1])
            ln["box"] = list(boxes[(ln["router"], k)])
            ln["site"] = nw["routers"][ln["router"]]["site"]
    for i, (a, b, mid, off) in enumerate(T["links"]):
        nw["links"][i].update(mid=mid, off=off)
    nw["sites"] = [{"router": r, "site": nw["routers"][r]["site"], "box": list(v[:4]), "lab": v[4]}
                   for r, v in T.get("sites", {}).items()]
    nw["height"] = T["h"]
    nw["tpl"] = tpl_name
    return nw


# ==========================================================================
# 設定(cfg)と手数
#   cfg = {"r": {ルータ: [{"p","nh","ad",("lock")}]}, "i": {ルータ: {IF: {"ip": "a.b.c.d/n" か None, "shut": bool}}}}
# ==========================================================================
def _if_state(b, cfg, r, name):
    o = cfg["i"].get(r, {}).get(name)
    i = b["ix"].iface(r, name)
    if o is None:
        return ("%s/%d" % (i["ip"], i["plen"]), False)
    return (o.get("ip", "%s/%d" % (i["ip"], i["plen"])), bool(o.get("shut")))


def cli(b, cfg):
    """初期の設定 → cfg の差分を IOS のコマンドで。[{"r", "lines": [...], "n": 手数}]"""
    out = {}
    for r in b["nw"]["routers"]:
        lines, n = [], 0
        for i in b["nw"]["routers"][r]["ifs"]:
            a = _if_state(b, b["init"], r, i["name"])
            c = _if_state(b, cfg, r, i["name"])
            if a == c:
                continue
            lines.append("interface " + i["name"])
            if a[0] != c[0]:
                if c[0]:
                    q = ipaddress.ip_interface(c[0])
                    lines.append(" ip address %s %s" % (q.ip, q.network.netmask))
                else:
                    lines.append(" no ip address")
                n += 1
            if a[1] != c[1]:
                lines.append(" shutdown" if c[1] else " no shutdown")
                n += 1
        for _, line in rm.diff({r: b["init"]["r"].get(r, [])}, {r: cfg["r"].get(r, [])}):
            lines.append(line)
            n += 1
        if lines:
            out[r] = {"r": r, "lines": lines, "n": n}
    return [out[r] for r in sorted(out, key=lambda x: (rm.rnum(x), x))]


def moves_of(b, cfg):
    return sum(x["n"] for x in cli(b, cfg))


def _copy(cfg):
    return json.loads(json.dumps(cfg))


# ==========================================================================
# お題と判定
#   req = {"t": "reach"|"path"|"via"|"same", "src": 端末, "dst": 端末, "path": [...], "via": R, "of": 何番目のお題(same)}
# ==========================================================================
def _flows_of(b):
    """お題に出てくる流れ [(src_ip, dst_ip, 障害の組)] (重複なし・順序は決まる)。"""
    out = []
    for q in b["reqs"]:
        f = (b["ix"].ip_of(q["src"]), b["ix"].ip_of(q["dst"]), tuple(q.get("down", ())))
        if f not in out:
            out.append(f)
    return out


def _run(b, cfg):
    """cfg での全部の流れの道。{(src, dst, down): [道 …]}・{down: tables}"""
    tabs = {}
    res = {}
    for f in _flows_of(b):
        dn = f[2]
        if dn not in tabs:
            tabs[dn] = rm.tables(b["ix"], cfg["r"], dn, cfg["i"])
        res[f] = rm.trace(b["ix"], tabs[dn], f[0], f[1])
    if () not in tabs:
        tabs[()] = rm.tables(b["ix"], cfg["r"], (), cfg["i"])
    return res, tabs


def _req_ok(b, q, paths, allp):
    if not paths or any(p["end"] != "deliver" for p in paths):
        return False
    if q["t"] == "reach":
        return True
    if len(paths) != 1:
        return False
    hops = paths[0]["hops"]
    if q["t"] == "path":
        return hops == q["path"]
    if q["t"] == "via":
        return q["via"] in hops
    if q["t"] == "same":
        o = b["reqs"][q["of"]]
        op = allp[(b["ix"].ip_of(o["src"]), b["ix"].ip_of(o["dst"]), tuple(o.get("down", ())))]
        return len(op) == 1 and op[0]["end"] == "deliver" and hops == list(reversed(op[0]["hops"]))
    return False


def check(b, cfg):
    allp, tabs = _run(b, cfg)
    out = []
    for q in b["reqs"]:
        f = (b["ix"].ip_of(q["src"]), b["ix"].ip_of(q["dst"]), tuple(q.get("down", ())))
        out.append({"ok": _req_ok(b, q, allp[f], allp), "now": allp[f]})
    return out, allp, tabs


def sat(b, cfg):
    return all(x["ok"] for x in check(b, cfg)[0])


# ==========================================================================
# 最少手数
# ==========================================================================
def _norm(d):
    if d[0] == "fwd":
        return ("fwd", tuple(d[1]))
    return (d[0],)


def _apply(init, combo):
    """初期の static の一覧に変更の組を当てる。combo の要素: ("del", i) / ("ad", i, v) / ("add", p, nh, ad)"""
    out = []
    dels = {op[1] for op in combo if op[0] == "del"}
    ads = {op[1]: op[2] for op in combo if op[0] == "ad"}
    for i, s in enumerate(init):
        if i in dels:
            continue
        s2 = dict(s)
        if i in ads:
            s2["ad"] = ads[i]
        out.append(s2)
    for op in combo:
        if op[0] == "add":
            out.append({"p": op[1], "nh": op[2], "ad": op[3]})
    return out


def _ad_reps(existing):
    """AD の候補を、同じ宛先のほかの経路との大小関係ごとに 1 つずつ(探索用の代表)。"""
    E = sorted(set(existing) | {1})
    seen, out = set(), []
    for v in AD_PRESETS:
        sig = tuple((v > e) - (v < e) for e in E)
        if sig not in seen:
            seen.add(sig)
            out.append(v)
    return out


def _router_ops(b, r, keys):
    init = b["init"]["r"].get(r, [])
    kn = b["knobs"]
    ops = []
    for i, s in enumerate(init):
        if s.get("lock"):
            continue
        if "del" in kn:
            ops.append(("del", i))
        if "ad" in kn:
            others = [int(x.get("ad", 1)) for j, x in enumerate(init) if j != i and x["p"] == s["p"]]
            for v in _ad_reps(others):
                if v != int(s.get("ad", 1)):
                    ops.append(("ad", i, v))
    have = {(rm.net(s["p"]), s["nh"]) for s in init}
    dsts = [rm.addr(k[0]) for k in keys]
    for pp in _add_dsts(b, r, keys):
        P = rm.net(pp)
        if not any(a in P for a in dsts):
            continue
        ex = [int(s.get("ad", 1)) for s in init if rm.net(s["p"]) == P]
        ads = _ad_reps(ex) if "ad" in kn else [1]
        for nh in b["nh"][r]:
            if (P, nh["ip"]) in have:
                continue
            for ad in ads:
                ops.append(("add", pp, nh["ip"], ad))
    return ops


FULL_CANDS = False                      # True = 下の間引きをしない(selftest で、間引いても最少手数が変わらないことを確かめる)


def _add_dsts(b, r, keys):
    """足す経路の宛先の候補。長さを選べないステージは地図の LAN(とデフォルト)のチップ。
    長さを選べるステージ(len)は、お題の宛先 IP を LENS の長さで切ったもの全部(そのルータの connected と同じものは除く)。"""
    if "len" not in b["knobs"]:
        return [c["p"] for c in b["chips"]]
    conn = [rm.net("%s/%d" % (i["ip"], i["plen"])) for i in b["nw"]["routers"][r]["ifs"]]
    ips = sorted({ip for ip, _ in keys})
    # そのルータに初めからある行(connected と static)の長さ。お題の宛先 IP ごと
    have = conn + [rm.net(s["p"]) for s in b["init"]["r"].get(r, [])]
    lens = {ip: sorted({P.prefixlen for P in have if rm.addr(ip) in P}) for ip in ips}
    # 同じ宛先 IP の組を覆い、初めからある行に対する長さの順位も同じ宛先は、どの組み合わせでも判断が同じ(ほかに足す行の
    # 長さは、覆う組が違えば覆う範囲で大小が決まり、この間に入らない)。代表だけを試す。代表は見慣れた形から(答えの一例に出る)
    seen, out = set(), []
    for ip in ips:
        for L in (24, 16, 32, 0, 8):
            if L == 0 and "default" not in b["knobs"]:
                continue
            P = ipaddress.ip_network("%s/%d" % (ip, L), strict=False)
            if P in conn:
                continue
            cov = tuple(k for k in ips if rm.addr(k) in P)
            sig = (cov, tuple(tuple((L > e) - (L < e) for e in lens[k]) for k in cov)) if not FULL_CANDS else str(P)
            if sig in seen:
                continue
            seen.add(sig)
            out.append(str(P))
    pref = (24, 16, 32, 0, 8)
    return sorted(out, key=lambda p: pref.index(rm.net(p).prefixlen))     # 同じ手数の答えは見慣れた長さのほうを先に見つける


def _compatible(combo):
    seen = set()
    for op in combo:
        k = ("e", op[1]) if op[0] in ("del", "ad") else ("a", op[1], op[2])
        if k in seen:
            return False
        seen.add(k)
        # 同じ宛先・同じ AD の行を 2 本足すと等コスト(道が分かれる)になるだけ。お題の判断(次は 1 台)に合わないので試さない
        if op[0] == "add":
            k2 = ("s", op[1], op[3])
            if k2 in seen:
                return False
            seen.add(k2)
    return True


def _router_vecs(b, r, keys, effs, kmax=3):
    """ルータ r の「転送の判断の組 → (最少の行数, 変更の組)」。keys= [(宛先 IP, 障害の組)]。"""
    ix = b["ix"]
    init = b["init"]["r"].get(r, [])
    ops = [] if b["nw"]["routers"][r].get("fixed") else _router_ops(b, r, keys)
    if len(ops) <= 14:
        kmax = max(kmax, 4)
    vecs = {}
    for k in range(0, kmax + 1):
        for combo in itertools.combinations(ops, k):
            if not _compatible(combo):
                continue
            routes = _apply(init, combo)
            tb = {}
            vec = []
            for dst, dn in keys:
                if dn not in tb:
                    tb[dn] = rm.rib(ix, r, routes, dn, effs[dn])
                vec.append(_norm(rm.decide(ix, tb[dn], r, dst)))
            vec = tuple(vec)
            if vec not in vecs:
                vecs[vec] = (k, combo)
    return vecs


def _simple_paths(adj, s, t, limit=200):
    out = []

    def dfs(u, path):
        if len(out) >= limit:
            return
        if u == t:
            out.append(path)
            return
        for v in adj[u]:
            if v not in path:
                dfs(v, path + [v])
    dfs(s, [s])
    return out


def _alts(b, q, effs, fwd_choice=None):
    """お題 1 つを満たす道の候補。各候補= {(ルータ, 鍵): 判断}。鍵= (宛先 IP, 障害の組)。"""
    ix = b["ix"]
    dn = tuple(q.get("down", ()))
    src, dst = ix.ip_of(q["src"]), ix.ip_of(q["dst"])
    fh = rm.first_hop(ix, effs[dn], src, dst)
    if fh[0] != "gw":
        return []
    t = ix.host[dst][2]
    adj = {r: [] for r in b["nw"]["routers"]}
    for k, lk in enumerate(b["nw"]["links"]):
        if k in dn:
            continue
        adj[lk["a"]].append(lk["b"])
        adj[lk["b"]].append(lk["a"])
    if q["t"] == "path":
        paths = [q["path"]]
    elif q["t"] == "same":
        paths = [list(reversed(fwd_choice))] if fwd_choice else []
    else:
        paths = _simple_paths(adj, fh[1], t)
        if q["t"] == "via":
            paths = [p for p in paths if q["via"] in p]
    key = (dst, dn)
    out = []
    for p in paths:
        if p[0] != fh[1] or p[-1] != t:
            continue
        need = {}
        for a, c in zip(p, p[1:]):
            need[(a, key)] = ("fwd", (c,))
        need[(p[-1], key)] = ("deliver",)
        out.append((p, need))
    return out


def solve(b):
    """最少手数と、その解の cfg。解けなければ (None, None)。"""
    if "if" in b["knobs"]:
        return _solve_ifs(b)
    ix = b["ix"]
    flows = _flows_of(b)
    keys = sorted({(f[1], f[2]) for f in flows})
    effs = {f[2]: rm.Eff(ix, b["init"]["i"], f[2]) for f in flows}
    effs.setdefault((), rm.Eff(ix, b["init"]["i"], ()))
    vecs = {r: _router_vecs(b, r, keys, effs) for r in b["nw"]["routers"]}
    kidx = {k: i for i, k in enumerate(keys)}
    cache = {}

    def rcost(r, need):
        ck = (r, tuple(sorted(need.items())))
        if ck in cache:
            return cache[ck]
        best = None
        for vec, (c, combo) in vecs[r].items():
            if best is not None and c >= best[0]:
                continue
            if all(vec[kidx[k]] == d for k, d in need.items()):
                best = (c, combo)
        cache[ck] = best
        return best

    best = [None, None]
    reqs = b["reqs"]

    def rec(i, need, chosen):
        # 下限: 今の要求で各ルータに要る最少の行数の和
        per = {}
        for (r, k), d in need.items():
            per.setdefault(r, {})[k] = d
        total = 0
        for r, nd in per.items():
            rc = rcost(r, nd)
            if rc is None:
                return
            total += rc[0]
        if best[0] is not None and total >= best[0]:
            return
        if i == len(reqs):
            best[0] = total
            best[1] = {r: rcost(r, nd)[1] for r, nd in per.items()}
            return
        q = reqs[i]
        fc = chosen[q["of"]] if q["t"] == "same" else None
        for p, nd in _alts(b, q, effs, fc):
            merged = dict(need)
            okm = True
            for k, d in nd.items():
                if k in merged and merged[k] != d:
                    okm = False
                    break
                merged[k] = d
            if okm:
                rec(i + 1, merged, chosen + [p])

    rec(0, {}, [])
    if best[0] is None:
        return None, None
    sol = _copy(b["init"])
    for r, combo in best[1].items():
        if combo:
            sol["r"][r] = _apply(b["init"]["r"].get(r, []), combo)
    return best[0], sol


def _if_options(b, r, name):
    """インターフェースに付けられる IP の候補(画面の選択肢と同じ)。"""
    return b["ifopt"][r][name]


def _solve_ifs(b):
    """ステージ 1: インターフェースの設定を総当たり(IP の候補 × shutdown の有無)。"""
    r = "R1"
    names = [i["name"] for i in b["nw"]["routers"][r]["ifs"]]
    choices = []
    for n in names:
        opts = [o["ip"] for o in _if_options(b, r, n)] + [None]
        choices.append([(ip, sh) for ip in opts for sh in (False, True)])
    best = (None, None)
    for combo in itertools.product(*choices):
        cfg = _copy(b["init"])
        cfg["i"] = {r: {n: {"ip": ip, "shut": sh} for n, (ip, sh) in zip(names, combo)}}
        if rm.overlaps(b["ix"], cfg["i"], r):
            continue
        mv = moves_of(b, cfg)
        if best[0] is not None and mv >= best[0]:
            continue
        if sat(b, cfg):
            best = (mv, cfg)
    return best


# ==========================================================================
# 生成
# ==========================================================================
def _seed_rnd(stage, level, seed):
    return random.Random(seed * 1000003 + stage * 101 + level)


def map_assist(stage, level):
    """経路の穴埋めで、地図の札を押すと欄に入るか(設計 §14)。リンクのアドレスが 172.16.XY の決まりの間(ステージ 2 の Lv 1・2)だけ。"""
    return stage == 2 and (level or 0) <= 2


def bad_nh(ip):
    """IOS が next-hop として受け付けない IP なら、その応答の文(PoC input_form #7〜9・#15〜16)。受け付けるなら None。"""
    a = rm.addr(ip)
    if int(a) == 0:
        return "%Invalid next hop, looping back to the network"
    if a.is_loopback or a.is_multicast or int(a) >= int(rm.addr("240.0.0.0")):
        return "%Invalid next hop address"
    return None


def irregular_links(stage, level):
    """リンクのアドレスをバラバラにするか(設計 §12)。ステージ 2 の Lv 1・2 だけは 172.16.XY の決まり。"""
    return stage >= 3 or (stage == 2 and (level or 0) >= 3)


def _base(stage, tpl, lan_hosts, rnd=None, level=None):
    nw = _build(tpl, lan_hosts, rnd, irregular_links(stage, level) and rnd is not None)
    ix = rm.Index(nw)
    b = {"stage": stage, "nw": nw, "ix": ix, "knobs": set(KNOBS.get(stage, KNOBS[7])),
         "init": {"r": {}, "i": {}}, "reqs": []}
    # 宛先のチップ(画面の候補と同じ。最少手数の探索もこれだけを使う)
    chips = []
    for ln in nw["lans"]:
        # Internet の 3 つも書ける宛先(1 つずつ書くと手数の上限を超える= デフォルトで指すのが答え・設計 §16)
        chips.append({"p": ln["prefix"], "kind": "lan", "site": ln.get("site", 0), "lan": ln["id"]})
    if "default" in b["knobs"]:
        chips.append({"p": "0.0.0.0/0", "kind": "default", "site": 0})
    b["chips"] = chips
    b["nh"] = {r: [{"ip": ip, "peer": peer} for peer, _, ip, _ in sorted(ix.neighbors[r], key=lambda x: rm.rnum(x[0]))]
               for r in nw["routers"]}
    return b


def _cap_nodef(b):
    """デフォルト ルートを足さずに解く最少手数(Internet を 1 つずつ書く解)より 1 少ない所に上限を置く(設計 §16)。
    デフォルトなしでも最少手数で解ける盤面は None(デフォルトの学びにならない)。"""
    if b is None:
        return None
    b2 = dict(b, chips=[c for c in b["chips"] if c["kind"] != "default"])
    mv, _ = solve(b2)
    if mv is not None and mv <= b["par"]:
        return None
    b["nodef"] = mv
    if mv is not None:
        b["budget"] = min(b["budget"], mv - 1)
    return b


def _finish(b, lo, hi, plus=2):
    """初期がお題を満たさず、最少手数が [lo, hi] に入れば盤面を仕上げる。だめなら None。"""
    if sat(b, b["init"]):
        return None
    mv, sol = solve(b)
    if mv is None or not lo <= mv <= hi:
        return None
    b["par"] = mv
    b["sol"] = sol
    b["budget"] = mv + plus
    return b


def _gen_s1(rnd, level):
    """ステージ 1: connected(ルータ 1 台)。SRV1 側(と送る側)のインターフェースの不具合を直す。"""
    three = level >= 3
    tpl = "one3" if three else "one2"
    ks = [1, 2, 3] if three else [1, 2]
    rnd.shuffle(ks)
    ksrc, kdst = ks[0], ks[1]
    lh = {("R1", ksrc): [{"name": "PC1"}], ("R1", kdst): [{"name": "SRV1", "kind": "srv"}]}
    if three:
        lh[("R1", ks[2])] = [{"name": "PC3"}]
    b = _base(1, tpl, lh, rnd, level)
    nw = b["nw"]
    ifn = {int(ln["id"].split("-")[1]): ln["if"] for ln in nw["lans"]}
    # 付けられる IP の候補: 自分の LAN の .1 と .254・使われていないサブネット・ほかの LAN(重なるので選べない)
    b["ifopt"] = {"R1": {}}
    for k, n in ifn.items():
        opts = [{"ip": "10.1.%d.1/24" % k}, {"ip": "10.1.%d.254/24" % k}, {"ip": "10.1.%d.1/24" % (k + 4)}]
        if level >= 4:
            other = next(x for x in ks if x != k)
            opts.append({"ip": "10.1.%d.1/24" % other})
        b["ifopt"]["R1"][n] = opts
    ifs = {}
    if level == 1:
        ifs[ifn[kdst]] = {"shut": True}
    elif level == 2:
        ifs[ifn[kdst]] = {"ip": None}
    elif level == 3:
        ifs[ifn[ksrc]] = {"shut": True}
        ifs[ifn[kdst]] = {"ip": None}
        ifs[ifn[ks[2]]] = {"shut": True}                    # PC3 の側は関係ない(直さなくてよい)
    elif level == 4:
        ifs[ifn[kdst]] = {"ip": "10.1.%d.1/24" % (kdst + 4), "shut": rnd.random() < .5}
    else:
        ifs[ifn[ksrc]] = {"ip": "10.1.%d.254/24" % ksrc}
        ifs[ifn[kdst]] = rnd.choice([{"shut": True}, {"ip": None}])
    full = {}
    for n, o in ifs.items():
        i = b["ix"].iface("R1", n)
        full[n] = {"ip": o.get("ip", "%s/%d" % (i["ip"], i["plen"])), "shut": bool(o.get("shut"))}
    b["init"]["i"] = {"R1": full}
    b["reqs"] = [{"t": "reach", "src": "PC1", "dst": "SRV1"}]
    return _finish(b, 1, 2, plus=3 if level <= 2 else 2)


def _pick_sq(rnd, diag):
    """四角の盤面で、PC1 と SRV1 を向かい合う角に置く(向きは乱数)。"""
    pairs = [("R1", "R4"), ("R4", "R1"), ("R2", "R3"), ("R3", "R2")] if not diag else [("R1", "R4"), ("R4", "R1")]
    return rnd.choice(pairs)


def _gen_s2(rnd, level):
    """ステージ 2: static の入口(片道)。"""
    if level == 1:
        a, z = rnd.choice([("R1", "R2"), ("R2", "R1")])
        b = _base(2, "line2", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
        b["reqs"] = [{"t": "reach", "src": "PC1", "dst": "SRV1"}]
        return _finish(b, 1, 1, 3)
    if level == 2:
        a, z = rnd.choice([("R1", "R3"), ("R3", "R1")])
        b = _base(2, "line3", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
        b["reqs"] = [{"t": "reach", "src": "PC1", "dst": "SRV1"}]
        return _finish(b, 2, 2, 3)
    if level == 3:
        a, z = rnd.choice([("R1", "R3"), ("R3", "R1")])
        b = _base(2, "tri", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
        b["reqs"] = [{"t": "via", "src": "PC1", "dst": "SRV1", "via": "R2"}]
        return _finish(b, 2, 2)
    diag = level == 5
    a, z = _pick_sq(rnd, diag)
    b = _base(2, "sqx" if diag else "sq", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
    adj = _adj(b)
    paths = [p for p in _simple_paths(adj, a, z) if len(p) == (4 if diag else 3)]
    b["reqs"] = [{"t": "path", "src": "PC1", "dst": "SRV1", "path": rnd.choice(paths)}]
    return _finish(b, 2, 3)


def _adj(b):
    adj = {r: [] for r in b["nw"]["routers"]}
    for lk in b["nw"]["links"]:
        adj[lk["a"]].append(lk["b"])
        adj[lk["b"]].append(lk["a"])
    return adj


def _gen_s3(rnd, level):
    """ステージ 3: 行きと帰り。"""
    if level == 1:
        a, z = rnd.choice([("R1", "R2"), ("R2", "R1")])
        b = _base(3, "line2", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
        b["reqs"] = [{"t": "reach", "src": "PC1", "dst": "SRV1"}, {"t": "reach", "src": "SRV1", "dst": "PC1"}]
        return _finish(b, 2, 2, 3)
    if level == 2:
        a, z = rnd.choice([("R1", "R3"), ("R3", "R1")])
        b = _base(3, "tri", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
        b["reqs"] = [{"t": "via", "src": "PC1", "dst": "SRV1", "via": "R2"},
                     {"t": "reach", "src": "SRV1", "dst": "PC1"}]
        return _finish(b, 3, 3, 3)
    if level == 3:
        a, z = rnd.choice([("R1", "R3"), ("R3", "R1")])
        b = _base(3, "line3", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
        b["reqs"] = [{"t": "reach", "src": "PC1", "dst": "SRV1"}, {"t": "reach", "src": "SRV1", "dst": "PC1"}]
        return _finish(b, 4, 4)
    diag = level == 5
    a, z = _pick_sq(rnd, diag)
    b = _base(3, "sqx" if diag else "sq", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
    adj = _adj(b)
    paths = [p for p in _simple_paths(adj, a, z) if len(p) == 3]
    fwd = rnd.choice(paths)
    if diag:
        # 行きは対角線を使わない道・戻りは対角線を使う 3 区間の道(片道ずつ違う道)
        back = [p for p in _simple_paths(adj, z, a) if len(p) == 4]
        b["reqs"] = [{"t": "path", "src": "PC1", "dst": "SRV1", "path": fwd},
                     {"t": "path", "src": "SRV1", "dst": "PC1", "path": rnd.choice(back)}]
        # 中のルータに、片方向だけ先に入っている経路(手数を 4〜5 に収める)
        mid = fwd[1]
        nh = next(x["ip"] for x in b["nh"][mid] if x["peer"] == fwd[2])
        b["init"]["r"][mid] = [{"p": _lan_of(b, "SRV1"), "nh": nh, "ad": 1}]
        return _finish(b, 4, 5)
    b["reqs"] = [{"t": "path", "src": "PC1", "dst": "SRV1", "path": fwd},
                 {"t": "same", "src": "SRV1", "dst": "PC1", "of": 0}]
    return _finish(b, 4, 4)


def _lan_of(b, host):
    ip = b["ix"].ip_of(host)
    return b["ix"].lan_of[b["ix"].host[ip][1]]["prefix"]


def _isp_routes(b, toward):
    """ISP(触れない)の経路: 10.0.0.0/8 をこちらの toward へ返す(NAT は省く)。"""
    nh = next(x["ip"] for x in b["nh"]["ISP"] if x["peer"] == toward)
    return [{"p": "10.0.0.0/8", "nh": nh, "ad": 1, "lock": "isp"}]


def _rand_init(rnd, b, routers, p_def=.5, p_lan=.4):
    """初期の経路を乱数で置く(デフォルトと LAN 宛て)。"""
    lans = [ln["prefix"] for ln in b["nw"]["lans"] if not ln.get("cloud")]
    for r in routers:
        lst = []
        if rnd.random() < p_def:
            lst.append({"p": "0.0.0.0/0", "nh": rnd.choice(b["nh"][r])["ip"], "ad": 1})
        for p in lans:
            if any(ln["prefix"] == p and ln["router"] == r for ln in b["nw"]["lans"]):
                continue
            if rnd.random() < p_lan:
                lst.append({"p": p, "nh": rnd.choice(b["nh"][r])["ip"], "ad": 1})
        if lst:
            b["init"]["r"][r] = lst


def _inet_reqs(src="PC1"):
    """Internet の 3 台へ届ける(画面では 1 行にまとめる= grp)＋ WEB からの戻り(戻りの道はどの台からでも同じなので 1 本)。"""
    return [{"t": "reach", "src": src, "dst": h, "grp": "inet"} for h in INET_HOSTS] + \
           [{"t": "reach", "src": "WEB", "dst": src}]


def _gen_s4(rnd, level):
    """ステージ 4: デフォルトルート(Internet と触れない ISP)。初めからある経路を消せる。"""
    if level <= 3:
        a = rnd.choice(["R1", "R2"])
        b = _base(4, "house", {(a, 1): [{"name": "PC1"}]}, rnd, level)
        b["init"]["r"]["ISP"] = _isp_routes(b, "R3")
        b["reqs"] = _inet_reqs()
        if level == 1:
            # R3 は済み(デフォルトと戻り)。PC1 側のルータにデフォルトが無い
            nh3 = next(x["ip"] for x in b["nh"]["R3"] if x["peer"] == "ISP")
            nha = next(x["ip"] for x in b["nh"]["R3"] if x["peer"] == a)
            b["init"]["r"]["R3"] = [{"p": "0.0.0.0/0", "nh": nh3, "ad": 1}, {"p": _lan_of(b, "PC1"), "nh": nha, "ad": 1}]
            return _cap_nodef(_finish(b, 1, 1, 3))
        if level == 2:
            nh3 = next(x["ip"] for x in b["nh"]["R3"] if x["peer"] == "ISP")
            b["init"]["r"]["R3"] = [{"p": "0.0.0.0/0", "nh": nh3, "ad": 1}]
            return _cap_nodef(_finish(b, 2, 2, 3))
        # level 3: デフォルトどうしの向け合い(ループ)を直す
        nha = next(x["ip"] for x in b["nh"]["R3"] if x["peer"] == a)
        nh_a3 = next(x["ip"] for x in b["nh"][a] if x["peer"] == "R3")
        b["init"]["r"]["R3"] = [{"p": "0.0.0.0/0", "nh": nha, "ad": 1}, {"p": _lan_of(b, "PC1"), "nh": nha, "ad": 1}]
        b["init"]["r"][a] = [{"p": "0.0.0.0/0", "nh": nh_a3, "ad": 1}]
        return _cap_nodef(_finish(b, 2, 2))
    # level 4〜5: 四角＋Internet。PC1 ↔ WEB と PC1 ↔ SRV1
    a, z = rnd.choice([("R3", "R4"), ("R4", "R3")])
    b = _base(4, "sqi", {(a, 1): [{"name": "PC1"}], (z, 1): [{"name": "SRV1", "kind": "srv"}]}, rnd, level)
    b["init"]["r"]["ISP"] = _isp_routes(b, rnd.choice(["R1", "R2"]))
    b["reqs"] = _inet_reqs()
    if level == 5:
        b["reqs"] += [{"t": "reach", "src": "PC1", "dst": "SRV1"}, {"t": "reach", "src": "SRV1", "dst": "PC1"}]
    _rand_init(rnd, b, ["R1", "R2", "R3", "R4"], .6, .35)
    return _cap_nodef(_finish(b, 2, 3 if level == 4 else 4))


def _nh(b, r, peer):
    return next(x["ip"] for x in b["nh"][r] if x["peer"] == peer)


def _pool5(b):
    """ステージ 5 の乱数の経路に使う宛先: デフォルト・拠点の /16・LAN の /24・端末の /32。"""
    out = ["0.0.0.0/0"] + ["10.%d.0.0/16" % s["site"] for s in b["nw"]["sites"]]
    for ln in b["nw"]["lans"]:
        if ln.get("cloud"):
            continue
        out.append(ln["prefix"])
        out += [h["ip"] + "/32" for h in ln["hosts"]]
    return out


def _rand_init5(rnd, b, routers, p):
    """初期の経路を乱数で足す(長さはいろいろ)。そのルータの connected と同じ宛先・もうある宛先は置かない。"""
    pool = _pool5(b)
    for r in routers:
        conn = {str(rm.net("%s/%d" % (i["ip"], i["plen"]))) for i in b["nw"]["routers"][r]["ifs"]}
        lst = b["init"]["r"].setdefault(r, [])
        have = {s["p"] for s in lst}
        for pf in pool:
            if pf not in conn and pf not in have and rnd.random() < p:
                lst.append({"p": pf, "nh": rnd.choice(b["nh"][r])["ip"], "ad": 1})
        if not lst:
            del b["init"]["r"][r]


def _uses_override(b):
    """最少の解が、🔒 の行より長い行(🔒 の行の中の一部)を足して通信の一部を横取りし返しているか(ステージ 5 の学び)。"""
    for r, lst in b["sol"]["r"].items():
        init = b["init"]["r"].get(r, [])
        locked = [rm.net(s["p"]) for s in init if s.get("lock")]
        ikeys = {rm.key_of(s) for s in init}
        for s in lst:
            if rm.key_of(s) in ikeys:
                continue
            P = rm.net(s["p"])
            if any(P != Q and P.subnet_of(Q) for Q in locked):
                return True
    return False


def _gen_s5(rnd, level):
    """ステージ 5: ロンゲストマッチ(ひし形・拠点 4 に LAN 2 つ)。x= 🔒 の行が向いている側、y= お題の道の側。"""
    x, y = rnd.choice([("R2", "R3"), ("R3", "R2")])
    lh = {("R1", 1): [{"name": "PC1"}]}
    if level == 2:
        lh[("R4", 1)] = [{"name": "SRV1", "kind": "srv"}, {"name": "SRV2", "kind": "srv"}]
        lh[("R4", 2)] = [{"name": "SRV3", "kind": "srv"}]
    else:
        lh[("R4", 1)] = [{"name": "SRV1", "kind": "srv"}]
        lh[("R4", 2)] = [{"name": "SRV2", "kind": "srv"}]
    b = _base(5, "diax" if level == 5 else "dia", lh, rnd, level)
    I = b["init"]["r"]
    site4, site1, lan_pc = "10.4.0.0/16", "10.1.0.0/16", _lan_of(b, "PC1")
    if level <= 3:
        # 真ん中の 2 台は拠点 4 へ・拠点 1 へ戻す経路を持っている
        for m in ("R2", "R3"):
            I[m] = [{"p": site4, "nh": _nh(b, m, "R4"), "ad": 1}, {"p": site1 if level == 3 else lan_pc, "nh": _nh(b, m, "R1"), "ad": 1}]
        go = {"t": "path", "src": "PC1", "dst": "SRV1", "path": ["R1", y, "R4"]}
        if level == 1:
            # 🔒 /16 が拠点 4 を丸ごと x へ。SRV1 の LAN だけ y を通す → /24 を足す
            I["R1"] = [{"p": site4, "nh": _nh(b, "R1", x), "ad": 1, "lock": "lpm"}]
            I["R4"] = [{"p": lan_pc, "nh": _nh(b, "R4", x), "ad": 1}]
            b["reqs"] = [go, {"t": "reach", "src": "SRV1", "dst": "PC1"}]
            return _finish(b, 1, 1, 3)
        if level == 2:
            # 🔒 /24 が SRV1 の LAN を x へ。同じ /24 を y へ足すと道が 2 つに分かれる → SRV1 の /32 を足す(SRV2 は今のまま x)
            I["R1"] = [{"p": _lan_of(b, "SRV1"), "nh": _nh(b, "R1", x), "ad": 1, "lock": "lpm"},
                       {"p": site4, "nh": _nh(b, "R1", x), "ad": 1}]
            I["R4"] = [{"p": site1, "nh": _nh(b, "R4", x), "ad": 1}]
            b["reqs"] = [go, {"t": "via", "src": "PC1", "dst": "SRV2", "via": x}, {"t": "reach", "src": "SRV1", "dst": "PC1"}]
            return _finish(b, 1, 1, 3)
        # level 3: 残っていた PC1 の /32 が、つながっている LAN(/24)にも勝って戻りを x へ送る(x は R1 へ返す)→ ループ。消す
        I["R1"] = [{"p": site4, "nh": _nh(b, "R1", x), "ad": 1, "lock": "lpm"},
                   {"p": b["ix"].ip_of("PC1") + "/32", "nh": _nh(b, "R1", x), "ad": 1}]
        I["R4"] = [{"p": site1, "nh": _nh(b, "R4", y), "ad": 1}]
        b["reqs"] = [go, {"t": "same", "src": "SRV1", "dst": "PC1", "of": 0}]
        return _finish(b, 2, 2)
    # level 4〜5: 乱数の経路(長さいろいろ)＋ 🔒。SRV1 は y の道・SRV2 は x の道、どちらも戻りも届く
    I["R1"] = [{"p": site4, "nh": _nh(b, "R1", x), "ad": 1, "lock": "lpm"}]
    if level == 5:
        # もう 1 本の 🔒: 真ん中か R4 に、長い行(/24 か /32)
        m = rnd.choice([x, y, "R4"])
        tgt = rnd.choice([_lan_of(b, "SRV1"), _lan_of(b, "SRV2"), b["ix"].ip_of("SRV1") + "/32", lan_pc])
        I[m] = [{"p": tgt, "nh": rnd.choice(b["nh"][m])["ip"], "ad": 1, "lock": "lpm"}]
    _rand_init5(rnd, b, ["R1", "R2", "R3", "R4"], .12 if level == 4 else .15)
    adj = _adj(b)
    if level == 4:
        p1, p2 = ["R1", y, "R4"], ["R1", x, "R4"]
    else:
        p1 = rnd.choice([p for p in _simple_paths(adj, "R1", "R4") if y in p])
        p2 = rnd.choice([p for p in _simple_paths(adj, "R1", "R4") if x in p and p != p1])
    b["reqs"] = [{"t": "path", "src": "PC1", "dst": "SRV1", "path": p1}, {"t": "path", "src": "PC1", "dst": "SRV2", "path": p2},
                 {"t": "reach", "src": "SRV1", "dst": "PC1"}, {"t": "reach", "src": "SRV2", "dst": "PC1"}]
    if level == 5:
        b["reqs"][2] = {"t": "same", "src": "SRV1", "dst": "PC1", "of": 0}
    b = _finish(b, 2, 4) if level == 4 else _finish(b, 3, 5)
    return b if b and _uses_override(b) else None


GEN = {1: _gen_s1, 2: _gen_s2, 3: _gen_s3, 4: _gen_s4, 5: _gen_s5}


def seed_of(stage, level):
    return int(hashlib.sha1(("route-%d-%d" % (stage, level)).encode()).hexdigest()[:6], 16)


@functools.lru_cache(maxsize=256)
def make(stage, level, seed=None):
    if stage not in GEN or not 1 <= level <= LEVELS:
        raise ValueError("そのステージ・レベルはありません")
    s0 = seed_of(stage, level) if seed is None else int(seed)
    for k in range(400):
        b = GEN[stage](_seed_rnd(stage, level, s0 + k * 7919), level)
        if b is not None:
            b.update(level=level, seed=s0)
            return b
    raise RuntimeError("盤面を作れませんでした: stage %d level %d seed %s" % (stage, level, s0))


# ==========================================================================
# 画面とのやり取り
# ==========================================================================
def cfg_json(b, cfg):
    return {"r": {r: [dict(s) for s in v] for r, v in cfg["r"].items() if v},
            "i": {r: {n: dict(o) for n, o in v.items()} for r, v in cfg["i"].items() if v}}


DST_RULE_MSG = {"notLan": "このステージで書ける宛先は地図の LAN だけです: %s",
                "noDef": "このステージではデフォルト ルートを書けません: %s",
                "lenRule": "このステージで書ける長さは /8・/16・/24・/32 と 0.0.0.0/0 だけです: %s",
                "noHostIn": "中に端末のいない宛先は書けません: %s"}


def dst_rule(b, p, chips=None):
    """ゲームの決まりで書けない宛先なら理由の鍵(画面の fe と同じ)。書けるなら None。
    長さを選べるステージ(len)より前は地図の LAN とデフォルトだけ。len からは長さが LENS で、中に端末がいる範囲(設計 §17)。
    端末のいない範囲(リンクの /32 など)を除くのは、next-hop の解決を横取りする手(探索の外)を出さないため。"""
    if chips is None:
        chips = {c["p"] for c in b["chips"]}
    P = rm.net(p)
    if P.prefixlen == 0:
        return None if "default" in b["knobs"] else "noDef"
    if "len" not in b["knobs"]:
        return None if p in chips else "notLan"
    if P.prefixlen not in LENS:
        return "lenRule"
    if not any(rm.addr(h) in P for h in b["ix"].host):
        return "noHostIn"
    return None


def cfg_parse(b, obj):
    """画面から来た設定を確かめて cfg にする。触れない経路・ルータ・候補にない値は断る。"""
    nw = b["nw"]
    cfg = {"r": {}, "i": {}}
    chips = {c["p"] for c in b["chips"]}
    for r, lst in (obj.get("r") or {}).items():
        if r not in nw["routers"]:
            raise ValueError("ルータが不正です: %s" % r)
        out = []
        for s in lst:
            try:
                p = str(ipaddress.ip_network(s["p"]))       # ホスト部が 0 でない宛先は IOS も断る(%Inconsistent address and mask)
            except ValueError:
                raise ValueError("%%Inconsistent address and mask: %s" % s["p"])
            nh = s.get("nh", "Null0")
            ad = int(s.get("ad", 1))
            if not 1 <= ad <= 255:
                raise ValueError("AD が不正です")
            item = {"p": p, "nh": nh, "ad": ad}
            if s.get("lock"):
                item["lock"] = s["lock"]
            out.append(item)
        cfg["r"][r] = out
    for r in nw["routers"]:
        init = b["init"]["r"].get(r, [])
        cur = cfg["r"].get(r, [])
        locked = [s for s in init if s.get("lock") or nw["routers"][r].get("fixed")]
        for s in locked:
            if not any(rm.key_of(s) == rm.key_of(x) and int(s.get("ad", 1)) == int(x.get("ad", 1)) for x in cur):
                raise ValueError("触れない経路は変えられません: %s %s" % (r, s["p"]))
        if nw["routers"][r].get("fixed") and len(cur) != len(init):
            raise ValueError("触れないルータです: %s" % r)
        ikeys = {rm.key_of(s) for s in init}
        # 次の行き先は、IOS が受け付ける IP ならどれでもよい(隣でない IP・持ち主のいない IP は IOS どおり表に入らないか、
        # 入っても先へ送れないだけ)。自分の IP と特別なアドレスは IOS が受け付けない(PoC nh_choice・input_form)
        own = {i["ip"] for i in nw["routers"][r]["ifs"]}
        for s in cur:
            if rm.key_of(s) in ikeys:
                continue
            if "add" not in b["knobs"]:
                raise ValueError("このステージでは経路を足せません")
            if s["nh"] == "Null0":
                if "null0" not in b["knobs"]:
                    raise ValueError("このステージでは Null0 を使えません")
            else:
                try:
                    rm.addr(s["nh"])
                except ValueError:
                    raise ValueError("next-hop が不正です: %s" % s["nh"])
                if s["nh"] in own:
                    raise ValueError("自分の IP は次の行き先にできません: %s" % s["nh"])
                if bad_nh(s["nh"]):
                    raise ValueError("%s: %s" % (bad_nh(s["nh"]), s["nh"]))
            # 宛先のゲームの決まり(IOS は受け付ける。最少手数の探索と同じ範囲にそろえる)
            why = dst_rule(b, s["p"], chips)
            if why:
                raise ValueError(DST_RULE_MSG[why] % s["p"])
        if "del" not in b["knobs"]:
            for s in init:
                if not any(rm.key_of(s) == rm.key_of(x) for x in cur):
                    raise ValueError("このステージでは初めからある経路を消せません")
        keys = [rm.key_of(s) for s in cur]
        if len(keys) != len(set(keys)):
            raise ValueError("同じ経路が 2 つあります")
    for r, ifs in (obj.get("i") or {}).items():
        if r not in nw["routers"]:
            raise ValueError("ルータが不正です: %s" % r)
        for n, o in ifs.items():
            b["ix"].iface(r, n)
            ip = o.get("ip")
            if "if" not in b["knobs"]:
                if (ip, bool(o.get("shut"))) != _if_state(b, b["init"], r, n):
                    raise ValueError("このステージではインターフェースを変えられません")
            elif ip is not None and ip not in [x["ip"] for x in b["ifopt"][r][n]]:
                raise ValueError("候補にない IP です: %s" % ip)
            cfg["i"].setdefault(r, {})[n] = {"ip": ip, "shut": bool(o.get("shut"))}
        if "if" in b["knobs"] and rm.overlaps(b["ix"], cfg["i"], r):
            raise ValueError("サブネットが重なっています")
    return cfg


def stars_of(b, moves):
    if moves <= b["par"]:
        return 3
    if moves <= b["par"] + 1:
        return 2
    return 1


def _table_json(t):
    rows = []
    for x in t["rows"]:
        rows.append({"p": x["p"], "code": x["code"], "ad": x["ad"], "out": x["out"],
                     "via": [{"nh": v} for v in x["via"]],
                     "res": [{"nh": a, "out": o, "peer": p} for a, o, p in x["res"]], "rid": x["rid"]})
    return {"rows": rows, "skipped": t["skipped"]}


def evaluate(b, cfg, want_explain=False):
    res, allp, tabs = check(b, cfg)
    mv = moves_of(b, cfg)
    ok = all(x["ok"] for x in res) and mv <= b["budget"]
    eff = tabs[()][next(iter(tabs[()]))]["eff"]
    out = {"moves": mv, "ok": ok, "stars": stars_of(b, mv) if ok else 0,
           "reqs": [{"ok": x["ok"], "now": x["now"]} for x in res],
           "tables": {r: _table_json(t) for r, t in tabs[()].items()},
           "ifs": {r: {n: {"ip": (v["ip"] + "/%d" % v["plen"]) if v["ip"] else None, "up": v["up"], "shut": v["shut"]}
                       for (rr, n), v in eff.ifs.items() if rr == r} for r in b["nw"]["routers"]},
           "cli": cli(b, cfg)}
    if ok or want_explain:
        if mv > b["par"]:
            out["best"] = {"moves": b["par"], "cli": cli(b, b["sol"])}
    return out


def payload(b, stage=None, level=None, seed=None):
    nw = b["nw"]
    st = b["stage"]
    routers = [{"name": n, "x": r["x"], "y": r["y"], "lab": r["lab"], "fixed": r["fixed"], "site": r["site"],
                "ifs": [{"name": i["name"], "ip": i["ip"], "plen": i["plen"], "to": i["to"], "link": i["link"]}
                        for i in r["ifs"]]}
               for n, r in nw["routers"].items()]
    return {"stage": st, "level": b["level"], "seed": b["seed"], "tpl": nw["tpl"], "height": nw["height"],
            "routers": routers, "links": nw["links"], "lans": nw["lans"], "sites": nw["sites"],
            "reqs": b["reqs"], "init": cfg_json(b, b["init"]), "knobs": sorted(b["knobs"]),
            "chips": b["chips"], "nh": b["nh"], "ifopt": b.get("ifopt", {}), "ad_presets": AD_PRESETS,
            "assist": map_assist(st, b["level"]),
            "par": b["par"], "budget": b["budget"], "show": show_of(st), "new": new_of(st),
            "eval": evaluate(b, b["init"])}


def puzzle(stage, level, seed=None):
    b = make(stage, level, seed)
    return payload(b)


# ==========================================================================
# ステージ定義と進み具合(保存の形は STP のゲームと同じ)
# ==========================================================================
def load_stages():
    import yaml
    with open(os.path.join(GAME_DIR, "stages.yml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _cleared(st, sid):
    return sum(1 for x in st["stages"].get(str(sid), {}).get("levels", {}).values() if x.get("cleared"))


def load_state(path=STATE):
    return sp.load_state(path)


def overview(path=STATE):
    st = load_state(path)
    y = load_stages()
    out, prev_done = [], True
    for s in y["stages"]:
        sid = s["id"]
        rec = st["stages"].get(str(sid), {})
        ready = sid in READY
        out.append({"id": sid, "ed": s.get("ed", "static"), "title": s["title"], "sub": s["sub"],
                    "cards": s.get("cards", []), "show": show_of(sid), "new": new_of(sid),
                    "ready": ready, "unlocked": ready and prev_done, "seen": bool(rec.get("seen")), "levels": LEVELS,
                    "progress": {k: {"stars": v.get("stars", 0), "revealed": v.get("revealed", False)}
                                 for k, v in rec.get("levels", {}).items() if v.get("cleared")}})
        prev_done = ready and _cleared(st, sid) >= LEVELS
    ex = sorted({c["example"] for s in out for c in s["cards"] if c.get("example")})
    return {"editions": y.get("editions", []), "stages": out, "examples": {e: example(e) for e in ex}}


def record(stage, level, stars, revealed, path=STATE):
    st = load_state(path)
    rec = st["stages"].setdefault(str(stage), {}).setdefault("levels", {})
    old = rec.get(str(level), {})
    rec[str(level)] = {"cleared": True, "stars": max(int(stars), old.get("stars", 0)),
                       "revealed": bool(revealed) and not old.get("cleared"),
                       "tries": old.get("tries", 0) + 1, "at": sp._now()}
    sp.save_state(st, path)


def mark_seen(stage, path=STATE):
    st = load_state(path)
    st["stages"].setdefault(str(stage), {})["seen"] = sp._now()
    sp.save_state(st, path)


def reset(stage=None, path=STATE):
    st = load_state(path)
    if stage is None:
        st = {"v": STATE_V, "stages": {}, "reset_at": sp._now()}
    else:
        st["stages"].pop(str(stage), None)
    sp.save_state(st, path)


def summary(path=STATE):
    st = load_state(path)
    clear = sum(_cleared(st, s) for s in READY)
    stars = sum(v.get("stars", 0) for s in READY for v in st["stages"].get(str(s), {}).get("levels", {}).values())
    return clear, len(READY) * LEVELS, stars, len(READY) * LEVELS * 3


# チュートリアルの例の盤面(stages.yml の example で名前を指す)。向きを固定した盤面を手で組む。
def _ex_board(stage, tpl, lh, reqs, init_r=None, init_i=None, cfg_r=None, cfg_i=None, ifopt=False):
    b = _base(stage, tpl, lh)
    b["reqs"] = reqs
    b["init"] = {"r": init_r or {}, "i": init_i or {}}
    if ifopt:
        b["ifopt"] = {"R1": {ln["if"]: [{"ip": "%s/24" % ln["gw"]}] for ln in b["nw"]["lans"]}}
    b.update(level=1, seed=0, par=0, budget=0)
    b["sol"] = b["init"]
    pl = payload(b)
    cfg = {"r": cfg_r if cfg_r is not None else (init_r or {}), "i": cfg_i if cfg_i is not None else (init_i or {})}
    pl["cfg"] = cfg_json(b, cfg)
    pl["eval"] = evaluate(b, cfg)
    return pl


def _ex_one(gw254=False):
    lh = {("R1", 1): [{"name": "PC1"}], ("R1", 2): [{"name": "SRV1", "kind": "srv"}]}
    ii = {"R1": {"Gi0/0": {"ip": "10.1.1.254/24", "shut": False}}} if gw254 else {}
    return _ex_board(1, "one2", lh, [{"t": "reach", "src": "PC1", "dst": "SRV1"}], init_i=ii, ifopt=True)


def _ex_line2(mode):
    lh = {("R1", 1): [{"name": "PC1"}], ("R2", 1): [{"name": "SRV1", "kind": "srv"}]}
    go = {"t": "reach", "src": "PC1", "dst": "SRV1"}
    back = {"t": "reach", "src": "SRV1", "dst": "PC1"}
    r_go = {"R1": [{"p": "10.2.1.0/24", "nh": "172.16.12.2", "ad": 1}]}
    r_both = {"R1": r_go["R1"], "R2": [{"p": "10.1.1.0/24", "nh": "172.16.12.1", "ad": 1}]}
    if mode == "drop":
        return _ex_board(2, "line2", lh, [go])
    if mode == "go":
        return _ex_board(2, "line2", lh, [go], cfg_r=r_go)
    if mode == "oneway":
        return _ex_board(3, "line2", lh, [go, back], cfg_r=r_go)
    return _ex_board(3, "line2", lh, [go, back], cfg_r=r_both)


def _ex_house(mode):
    lh = {("R1", 1): [{"name": "PC1"}]}
    b = _base(4, "house", lh)
    isp = _isp_routes(b, "R3")
    reqs = _inet_reqs() if mode == "ok" else [{"t": "reach", "src": "PC1", "dst": "WEB"}, {"t": "reach", "src": "WEB", "dst": "PC1"}]
    r3_back = {"p": "10.1.1.0/24", "nh": "172.16.13.1", "ad": 1}
    if mode == "loop":
        r = {"ISP": isp, "R1": [{"p": "0.0.0.0/0", "nh": "172.16.13.2", "ad": 1}],
             "R3": [{"p": "0.0.0.0/0", "nh": "172.16.13.1", "ad": 1}, r3_back]}
    else:
        r = {"ISP": isp, "R1": [{"p": "0.0.0.0/0", "nh": "172.16.13.2", "ad": 1}],
             "R3": [{"p": "0.0.0.0/0", "nh": "100.64.0.1", "ad": 1}, r3_back]}
    return _ex_board(4, "house", lh, reqs, init_r=r)


def _ex_dia(mode):
    """ステージ 5 の例(ひし形・リンクは 172.16.XY: R1–R2 .12・R1–R3 .13・R2–R4 .24・R3–R4 .34。若い番号の側が .1)。"""
    lh = {("R1", 1): [{"name": "PC1"}], ("R4", 1): [{"name": "SRV1", "kind": "srv"}], ("R4", 2): [{"name": "SRV2", "kind": "srv"}]}
    mid = {"R2": [{"p": "10.4.0.0/16", "nh": "172.16.24.2", "ad": 1}, {"p": "10.1.0.0/16", "nh": "172.16.12.1", "ad": 1}],
           "R3": [{"p": "10.4.0.0/16", "nh": "172.16.34.2", "ad": 1}, {"p": "10.1.0.0/16", "nh": "172.16.13.1", "ad": 1}],
           "R4": [{"p": "10.1.0.0/16", "nh": "172.16.24.1", "ad": 1}]}
    to_srv = [{"t": "reach", "src": "PC1", "dst": "SRV1"}, {"t": "reach", "src": "PC1", "dst": "SRV2"}]
    if mode == "lpm":
        # 🔒 /16 は拠点 4 を丸ごと R2 へ。SRV1 の LAN の /24 を R3 へ足すと、SRV1 だけ R3 を通る
        r1 = [{"p": "10.4.0.0/16", "nh": "172.16.12.2", "ad": 1, "lock": "lpm"}]
        return _ex_board(5, "dia", lh, to_srv, init_r=dict(mid, R1=r1),
                         cfg_r=dict(mid, R1=r1 + [{"p": "10.4.1.0/24", "nh": "172.16.13.2", "ad": 1}]))
    if mode == "ecmp":
        # 🔒 /24 と同じ /24(管理距離も同じ)を R3 へ足すと、両方とも表に入って道が 2 つに分かれる
        r1 = [{"p": "10.4.1.0/24", "nh": "172.16.12.2", "ad": 1, "lock": "lpm"}, {"p": "10.4.0.0/16", "nh": "172.16.12.2", "ad": 1}]
        return _ex_board(5, "dia", lh, to_srv[:1], init_r=dict(mid, R1=r1),
                         cfg_r=dict(mid, R1=r1 + [{"p": "10.4.1.0/24", "nh": "172.16.13.2", "ad": 1}]))
    # conn: 残っていた PC1 の /32 が connected の /24 に勝ち、戻りを R2 へ送る(R2 は R1 へ返す)→ ループ
    r1 = [{"p": "10.4.0.0/16", "nh": "172.16.12.2", "ad": 1}, {"p": "10.1.1.10/32", "nh": "172.16.12.2", "ad": 1}]
    return _ex_board(5, "dia", lh, [to_srv[0], {"t": "reach", "src": "SRV1", "dst": "PC1"}], init_r=dict(mid, R1=r1))


EXAMPLES = {
    "ex_one": lambda: _ex_one(),
    "ex_one_gw": lambda: _ex_one(True),
    "ex_line2_drop": lambda: _ex_line2("drop"),
    "ex_line2_go": lambda: _ex_line2("go"),
    "ex_line2_oneway": lambda: _ex_line2("oneway"),
    "ex_line2_both": lambda: _ex_line2("both"),
    "ex_house_loop": lambda: _ex_house("loop"),
    "ex_house_ok": lambda: _ex_house("ok"),
    "ex_dia_lpm": lambda: _ex_dia("lpm"),
    "ex_dia_ecmp": lambda: _ex_dia("ecmp"),
    "ex_dia_conn": lambda: _ex_dia("conn"),
}


def example(name):
    return EXAMPLES[name]() if name in EXAMPLES else None


# ==========================================================================
# API(pack_server から呼ぶ)
# ==========================================================================
def _board_of(data):
    stage, level = int(data["stage"]), int(data["level"])
    sd = data.get("seed")
    seed = None if sd in (None, "") or int(sd) == seed_of(stage, level) else int(sd)
    return make(stage, level, seed)


def api(method, path, query, body, state_path=STATE):
    """(HTTP コード, JSON にする値)。path= /_api/route_path/ より後ろ。"""
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
            if stage is not None and int(stage) not in [s["id"] for s in load_stages()["stages"]]:
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
    """ルータを分けない総当たり(小さい盤面の照合用)。maxd 手まで。"""
    ix = b["ix"]
    flows = _flows_of(b)
    keys = sorted({(f[1], f[2]) for f in flows})
    allops = []
    for r in b["nw"]["routers"]:
        if b["nw"]["routers"][r].get("fixed"):
            continue
        for op in _router_ops(b, r, keys):
            allops.append((r, op))
    for d in range(0, maxd + 1):
        for combo in itertools.combinations(allops, d):
            per = {}
            for r, op in combo:
                per.setdefault(r, []).append(op)
            if not all(_compatible(v) for v in per.values()):
                continue
            cfg = _copy(b["init"])
            for r, ops in per.items():
                cfg["r"][r] = _apply(b["init"]["r"].get(r, []), ops)
            if sat(b, cfg):
                return d
    return None


def selftest(n=6):
    global FULL_CANDS
    import time
    ng = []

    def bad(m):
        ng.append(m)
        print("NG:", m)
    t0 = time.time()
    worst = 0
    for st in READY:
        for lv in range(1, LEVELS + 1):
            for k in range(n):
                seed = None if k == 0 else 1000 + k
                t1 = time.time()
                try:
                    b = make(st, lv, seed)
                except Exception as e:                      # noqa: BLE001
                    bad("生成 %d-%d seed %s: %s" % (st, lv, seed, e))
                    continue
                worst = max(worst, time.time() - t1)
                tag = "%d-%d#%s" % (st, lv, seed)
                if sat(b, b["init"]):
                    bad(tag + " 初期でお題を満たしている")
                if not sat(b, b["sol"]):
                    bad(tag + " 解がお題を満たさない")
                if moves_of(b, b["sol"]) != b["par"]:
                    bad(tag + " 解の手数 %d ≠ 最少 %d" % (moves_of(b, b["sol"]), b["par"]))
                ev = evaluate(b, cfg_parse(b, cfg_json(b, b["sol"])))
                if not ev["ok"] or ev["stars"] != 3:
                    bad(tag + " 解を送り直して ok にならない")
                ev0 = evaluate(b, cfg_parse(b, cfg_json(b, b["init"])))
                if ev0["ok"]:
                    bad(tag + " 初期で ok")
                js = json.loads(json.dumps(payload(b), ensure_ascii=False))
                if js["par"] != b["par"]:
                    bad(tag + " JSON の往復")
                # 小さい盤面は総当たりと照合(ステージ 2 から。長さを選べるステージは候補が多いので 2 手まで)
                if st >= 2 and k < 2 and b["par"] <= (2 if "len" in b["knobs"] else 3):
                    bm = _brute_min(b, b["par"])
                    if bm != b["par"]:
                        bad(tag + " 総当たり %s ≠ 最少 %d" % (bm, b["par"]))
                # 長さを選べるステージ: 宛先の候補を間引かずに解き直しても最少手数が同じ
                if "len" in b["knobs"] and k < 3:
                    FULL_CANDS = True
                    try:
                        mv_full, _ = solve(b)
                    finally:
                        FULL_CANDS = False
                    if mv_full != b["par"]:
                        bad(tag + " 間引かない候補で %s ≠ 最少 %d" % (mv_full, b["par"]))
    # 決定性
    a = payload(make(2, 4, 77))
    make.cache_clear()
    if json.dumps(payload(make(2, 4, 77)), sort_keys=True) != json.dumps(a, sort_keys=True):
        bad("同じ seed で同じ盤面にならない")
    # 不正な設定を断る
    b = make(4, 3)
    try:
        cfg_parse(b, {"r": {"ISP": []}})
        bad("ISP の経路を消せてしまう")
    except ValueError:
        pass
    b2 = make(2, 1)
    try:
        cfg_parse(b2, {"r": {"R1": [{"p": "8.8.8.0/24", "nh": b2["nh"]["R1"][0]["ip"]}]}})
        bad("候補にない宛先を足せてしまう")
    except ValueError:
        pass
    # 穴埋めの受け付け(設計 §14): IOS が断るものは断り、IOS が受け付けるものは受け付けて計算器どおりに扱う
    lan2 = next(c["p"] for c in b2["chips"] if not any(ln["prefix"] == c["p"] and ln["router"] == "R1" for ln in b2["nw"]["lans"]))
    own1 = next(i["ip"] for i in b2["nw"]["routers"]["R1"]["ifs"] if i["link"] is not None)
    for nh, why in ((own1, "自分の IP"), ("0.0.0.0", "0.0.0.0"), ("127.0.0.1", "127/8"), ("224.0.0.1", "マルチキャスト"),
                    ("255.255.255.255", "全 1")):
        try:
            cfg_parse(b2, {"r": {"R1": [{"p": lan2, "nh": nh}]}})
            bad("next-hop %s(%s)を足せてしまう" % (nh, why))
        except ValueError:
            pass
    try:
        cfg_parse(b2, {"r": {"R1": [{"p": lan2.replace(".0/", ".1/"), "nh": b2["nh"]["R1"][0]["ip"]}]}})
        bad("ホスト部が 0 でない宛先を足せてしまう")
    except ValueError:
        pass
    try:
        cfg_parse(b2, {"r": {"R1": [{"p": "0.0.0.0/0", "nh": b2["nh"]["R1"][0]["ip"]}]}})
        bad("ステージ 2 でデフォルトを足せてしまう")
    except ValueError:
        pass
    nb = b2["nh"]["R1"][0]["ip"]
    bcast = str(rm.addr(nb) + (1 if int(rm.addr(nb)) % 4 == 2 else 2))
    ev = evaluate(b2, cfg_parse(b2, {"r": {"R1": [{"p": lan2, "nh": nb, "ad": 255}]}}))
    if ev["ok"] or not any(k["why"] == "ad255" for k in ev["tables"]["R1"]["skipped"]):
        bad("AD 255 の経路が表に入る")
    ev = evaluate(b2, cfg_parse(b2, {"r": {"R1": [{"p": lan2, "nh": bcast}]}}))
    if ev["ok"] or not any(x["p"] == lan2 for x in ev["tables"]["R1"]["rows"]):
        bad("持ち主のいない IP(%s)の経路の扱い" % bcast)
    # ステージ 5: 書ける宛先の決まり(長さはオクテットの切れ目・中に端末がいる範囲)とロンゲストマッチ
    b5 = make(5, 2)
    nb5 = b5["nh"]["R1"][0]["ip"]
    srv1 = b5["ix"].ip_of("SRV1")
    link = b5["nw"]["links"][0]
    for pf, want in (("10.4.0.0/16", None), (srv1 + "/32", None), ("10.0.0.0/8", None), ("0.0.0.0/0", None),
                     ("10.4.1.0/25", "lenRule"), (link["prefix"], "lenRule"), (link["ipb"] + "/32", "noHostIn"),
                     ("10.2.0.0/16", "noHostIn")):
        got = dst_rule(b5, pf)
        if got != want:
            bad("ステージ 5 の宛先 %s: %s(期待 %s)" % (pf, got, want))
    y5 = b5["reqs"][0]["path"][1]
    lan1 = _lan_of(b5, "SRV1")
    c5 = _copy(b5["init"])
    c5["r"]["R1"] = c5["r"]["R1"] + [{"p": lan1, "nh": _nh(b5, "R1", y5), "ad": 1}]
    res5 = check(b5, c5)[0]
    if len(res5[0]["now"]) != 2:
        bad("🔒 と同じ /24 を足しても道が 2 つに分かれない")
    c5["r"]["R1"][-1] = {"p": srv1 + "/32", "nh": _nh(b5, "R1", y5), "ad": 1}
    if not sat(b5, c5):
        bad("/32 を足してもステージ 5 Lv 2 が開通しない")
    b53 = make(5, 3)
    t53 = rm.tables(b53["ix"], b53["init"]["r"])
    d53 = rm.decide(b53["ix"], t53["R1"], "R1", b53["ix"].ip_of("PC1"))
    if d53[0] != "fwd":
        bad("/32 が connected の /24 に勝たない(ステージ 5 Lv 3)")
    b1 = make(1, 4)
    try:
        n0 = b1["nw"]["routers"]["R1"]["ifs"][0]["name"]
        other = [x for x in b1["ifopt"]["R1"][n0] if x["ip"].startswith("10.1.") and
                 any(ln["prefix"] == str(rm.net(x["ip"])) and ln["if"] != n0 for ln in b1["nw"]["lans"])]
        if other:
            cfg_parse(b1, {"i": {"R1": {n0: {"ip": other[0]["ip"], "shut": False}}}})
            bad("重なる IP を付けられてしまう")
    except ValueError:
        pass
    # 進み具合
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.json")
        record(1, 1, 3, False, p)
        record(1, 1, 2, False, p)
        if load_state(p)["stages"]["1"]["levels"]["1"]["stars"] != 3:
            bad("記録の星が下がった")
        reset(1, p)
        if "1" in load_state(p)["stages"]:
            bad("リセット")
    print("route_path selftest: %d 盤面・最も遅い生成 %.2f 秒・全体 %.1f 秒・NG %d"
          % (len(READY) * LEVELS * n, worst, time.time() - t0, len(ng)))
    return not ng


def show(stage, level, seed=None):
    b = make(stage, level, seed)
    print("stage %d level %d seed %s tpl %s  最少 %d 手・上限 %d" % (stage, level, b["seed"], b["nw"]["tpl"], b["par"], b["budget"]))
    for q in b["reqs"]:
        print("  お題:", q)
    for r, lst in b["init"]["r"].items():
        for s in lst:
            print("  初期 %s: %s%s" % (r, rm.route_cli(s), "  🔒" if s.get("lock") else ""))
    for r, v in b["init"]["i"].items():
        print("  初期 IF %s: %s" % (r, v))
    for x in cli(b, b["sol"]):
        for line in x["lines"]:
            print("  解 %s: %s" % (x["r"], line))
    res, allp, _ = check(b, b["init"])
    for x in res:
        print("  今:", [(p["hops"], p["end"]) for p in x["now"]])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest(int(sys.argv[2]) if len(sys.argv) > 2 else 6) else 1)
    if len(sys.argv) > 3 and sys.argv[1] == "show":
        show(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else None)
        sys.exit(0)
    print(__doc__)
