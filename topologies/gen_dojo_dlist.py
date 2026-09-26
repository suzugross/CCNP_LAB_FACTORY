#!/usr/bin/env python3
"""distribute-list 道場(BL-215)= ACL(標準/拡張直接/拡張 route-map 経由)・prefix-list の意味の違いを実機で体感する。

盤面(IOL 6 台・EIGRP):
    RT04 ── RT02 ──e0/0── RT01(被験) ──e0/1── RT03
                          │ e0/2      │ e1/0
                         RT05        RT06
  経路(battery)は各ルータの `ip route … Null0` ＋ `redistribute static`(同アドレス異長を 1 台に置ける)。
  第 2 オクテット A(RT02/RT03 の重なり集合)・B(RT04)・C(RT05)・D(RT06)を seed で抽選。

第 1 部(観察の提出・32 点): 与えられた 4 つのフィルタを RT01 の `router eigrp` 直下に 1 つずつ掛けて観察し、
  残った経路を prefix-list PRED-1〜4 に「1 経路 1 行・ge/le なし」で書く。期待集合は下の意味論モデルで計算。
第 2 部(本番・64 点): IF ごとに方式指定のタスク(効果 12 ＋ 方式 4)。最終状態に全体の distribute-list を残さない(4 点)。

意味論(PoC 実測= poc/dlist/README.md・poc/acl/README.md §3・§4):
  標準 ACL= 網アドレスだけ(長さは見ない) / 拡張 ACL を直接指定= src は広告してきた隣接・dst は網アドレス(長さは見ない) /
  route-map 経由の拡張 ACL= src は網アドレス・dst はマスク / prefix-list= アドレスと長さ(ge/le)。
  全体と IF 単位の distribute-list は両方効く(AND)。同じ IF に in のフィルタは 1 つだけ。反映は clear 不要・約 10 秒。

使い方: gen_dojo_dlist.py --repo . --seed <int> [--selftest]
"""
import argparse
import json
import os
import random

import yaml

NODES = ["RT01", "RT02", "RT03", "RT04", "RT05", "RT06"]
# RT01 から見た隣接の IP(広告元)
NBR = {"RT02": "10.0.12.2", "RT03": "10.0.13.3", "RT05": "10.0.15.5", "RT06": "10.0.16.6"}
ORIGIN_IP = {"RT04": "10.0.24.4"}
IFACE = {"RT02": "Ethernet0/0", "RT03": "Ethernet0/1", "RT05": "Ethernet0/2", "RT06": "Ethernet1/0"}


# ---------------------------------------------------------------- 値・battery
def rand_values(rnd):
    octs = rnd.sample(range(20, 240), 4)
    return {"A": octs[0], "B": octs[1], "C": octs[2], "D": octs[3], "asn": rnd.randint(100, 899)}


def battery(v):
    A, B, C, D = v["A"], v["B"], v["C"], v["D"]
    return {
        "RT02": [f"10.{A}.0.0/24", f"10.{A}.0.0/26", f"10.{A}.0.0/22", f"10.{A}.0.16/28",
                 f"10.{A}.1.0/24", f"10.{A}.2.0/24", f"10.{A}.3.0/24", f"10.{A}.2.128/25"],
        "RT03": [f"10.{A}.0.0/24", f"10.{A}.0.0/28", f"10.{A}.2.0/24", f"10.{A}.9.0/24",
                 f"10.{A}.8.0/23", f"10.{A}.9.128/25"],
        "RT04": [f"10.{B}.0.0/24", f"10.{B}.0.0/28", f"10.{B}.1.0/24"],
        "RT05": [f"10.{C}.0.0/24", f"10.{C}.0.0/26", f"10.{C}.1.0/24", f"10.{C}.2.0/24",
                 f"10.{C}.2.64/26", f"10.{C}.3.0/24"],
        "RT06": [f"10.{D}.0.0/24", f"10.{D}.0.0/25", f"10.{D}.0.0/23", f"10.{D}.1.0/24",
                 f"10.{D}.0.128/25"],
    }


def routes_at_rt01(v):
    """RT01 が学習する経路 [(prefix, 広告元の隣接 IP)]。RT04 の経路は RT02 が広告する。"""
    b = battery(v)
    out = []
    for r in ("RT02", "RT03", "RT05", "RT06"):
        out += [(p, NBR[r]) for p in b[r]]
    out += [(p, NBR["RT02"]) for p in b["RT04"]]
    return out


def prefixes(v):
    return sorted({p for p, _ in routes_at_rt01(v)}, key=_pkey)


def _pkey(p):
    a, l = p.split("/")
    return tuple(int(x) for x in a.split(".")) + (int(l),)


# ---------------------------------------------------------------- 意味論モデル
def ip(s):
    a, b, c, d = (int(x) for x in s.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


def mask(bits):
    m = (0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF
    return ".".join(str((m >> s) & 255) for s in (24, 16, 8, 0))


def wmatch(base, wild, x):
    return (ip(x) ^ ip(base)) & ~ip(wild) & 0xFFFFFFFF == 0


def _spec(tok, i):
    """ACL のアドレス指定 any / host A / A W を (base, wild, 次) に。"""
    if tok[i] == "any":
        return "0.0.0.0", "255.255.255.255", i + 1
    if tok[i] == "host":
        return tok[i + 1], "0.0.0.0", i + 2
    return tok[i], tok[i + 1], i + 2


def eval_std(lines, net):
    """標準 ACL(`permit A [W]` の列)= 網アドレスだけを見る。"""
    for ln in lines:
        t = ln.split()
        act, a = t[0], t[1]
        w = t[2] if len(t) > 2 else "0.0.0.0"
        if wmatch(a, w, net):
            return act == "permit"
    return False


def eval_ext(lines, src, dst):
    """拡張 ACL(`permit ip S SW D DW` の列)。直接指定なら src=隣接・dst=網、route-map 経由なら src=網・dst=マスク。"""
    for ln in lines:
        t = ln.split()
        act = t[0]
        s, sw, i = _spec(t, 2)
        d, dw, _ = _spec(t, i)
        if wmatch(s, sw, src) and wmatch(d, dw, dst):
            return act == "permit"
    return False


def eval_pl(lines, net, ln_):
    """prefix-list(`permit N/L [ge x] [le y]` の列)。"""
    for line in lines:
        t = line.split()
        act, pfx = t[0], t[1]
        a, L = pfx.split("/")
        L = int(L)
        ge = int(t[t.index("ge") + 1]) if "ge" in t else None
        le = int(t[t.index("le") + 1]) if "le" in t else None
        lo = ge if ge is not None else L
        hi = le if le is not None else (32 if ge is not None else L)
        if (ip(net) >> (32 - L) if L else 0) == (ip(a) >> (32 - L) if L else 0) and lo <= ln_ <= hi:
            return act == "permit"
    return False


def passes(flt, prefix, nbr):
    """flt= {"kind": std|ext|rm|pl, "acl": [...], "rm": [(action, acl_lines)]}"""
    net, L = prefix.split("/")
    L = int(L)
    k = flt["kind"]
    if k == "std":
        return eval_std(flt["acl"], net)
    if k == "ext":
        return eval_ext(flt["acl"], nbr, net)
    if k == "pl":
        return eval_pl(flt["acl"], net, L)
    if k == "rm":
        for action, acl in flt["rm"]:
            if acl is None or eval_ext(acl, net, mask(L)):
                return action == "permit"
        return False
    raise ValueError(k)


def surviving(v, flt, only_nbr=None):
    """フィルタを通った経路(prefix の集合)。only_nbr= その隣接から来た経路にだけ適用(IF 単位)。"""
    keep = set()
    for p, n in routes_at_rt01(v):
        if only_nbr and n != only_nbr:
            keep.add(p)
            continue
        if passes(flt, p, n):
            keep.add(p)
    return keep


# ---------------------------------------------------------------- 第 1 部(観察)
def obs_pool(v):
    A, B = v["A"], v["B"]
    return {
        "std_host": {"kind": "std", "name": "10", "acl": [f"permit 10.{A}.0.0"], "group": "std",
                     "cfg": [f"access-list 10 permit 10.{A}.0.0"], "dl": "distribute-list 10 in"},
        "std_noncontig": {"kind": "std", "name": "11", "acl": [f"permit 10.{A}.0.0 0.0.2.255"], "group": "std",
                          "cfg": [f"access-list 11 permit 10.{A}.0.0 0.0.2.255"], "dl": "distribute-list 11 in"},
        "ext_dst_net": {"kind": "ext", "name": "110", "acl": [f"permit ip any host 10.{A}.0.0"], "group": "ext",
                        "cfg": [f"access-list 110 permit ip any host 10.{A}.0.0"], "dl": "distribute-list 110 in"},
        "ext_src_net": {"kind": "ext", "name": "111", "acl": [f"permit ip host 10.{A}.0.0 any"], "group": "ext",
                        "cfg": [f"access-list 111 permit ip host 10.{A}.0.0 any"], "dl": "distribute-list 111 in"},
        "ext_src_nbr": {"kind": "ext", "name": "112", "acl": [f"permit ip host {NBR['RT03']} any"], "group": "ext",
                        "cfg": [f"access-list 112 permit ip host {NBR['RT03']} any"], "dl": "distribute-list 112 in"},
        "ext_src_origin": {"kind": "ext", "name": "113", "acl": [f"permit ip host {ORIGIN_IP['RT04']} any"],
                           "group": "ext", "cfg": [f"access-list 113 permit ip host {ORIGIN_IP['RT04']} any"],
                           "dl": "distribute-list 113 in"},
        "ext_nbr_net": {"kind": "ext", "name": "114", "acl": [f"permit ip host {NBR['RT02']} host 10.{B}.0.0"],
                        "group": "ext", "cfg": [f"access-list 114 permit ip host {NBR['RT02']} host 10.{B}.0.0"],
                        "dl": "distribute-list 114 in"},
        "rm_exact": {"kind": "rm", "rm": [("permit", [f"permit ip host 10.{A}.0.0 host 255.255.255.0"])],
                     "group": "rm",
                     "cfg": [f"access-list 120 permit ip host 10.{A}.0.0 host 255.255.255.0",
                             "route-map RM-OBS-120 permit 10", " match ip address 120"],
                     "dl": "distribute-list route-map RM-OBS-120 in"},
        "rm_range": {"kind": "rm", "rm": [("permit", [f"permit ip 10.{A}.0.0 0.0.255.255 255.255.255.0 0.0.0.255"])],
                     "group": "rm",
                     "cfg": [f"access-list 121 permit ip 10.{A}.0.0 0.0.255.255 255.255.255.0 0.0.0.255",
                             "route-map RM-OBS-121 permit 10", " match ip address 121"],
                     "dl": "distribute-list route-map RM-OBS-121 in"},
    }


def draw_obs(rnd, v):
    pool = obs_pool(v)
    while True:
        keys = rnd.sample(sorted(pool), 4)
        groups = {pool[k]["group"] for k in keys}
        if {"std", "ext", "rm"} <= groups:
            return [(k, pool[k]) for k in keys]


# ---------------------------------------------------------------- 第 2 部(本番)
def draw_tasks(rnd, v):
    A, B, C, D = v["A"], v["B"], v["C"], v["D"]
    t = {}
    # T1: e0/0(RT02 ＋ 奥の RT04)・拡張 ACL を直接指定(番号 150)
    if rnd.random() < 0.5:
        t["T1"] = {"nbr": "RT02", "var": "drop_origin_all", "method": "ext", "acl_no": 150,
                   "req": f"RT04 が作成したところの経路(`10.{B}.0.0/16` の範囲)は、受け取らないこと。それ以外の経路は、受け取ること",
                   "model": {"kind": "ext", "acl": [f"deny ip any 10.{B}.0.0 0.0.255.255", "permit ip any any"]}}
    else:
        t["T1"] = {"nbr": "RT02", "var": "drop_origin_net", "method": "ext", "acl_no": 150,
                   "req": f"RT04 が作成したところの経路のうち、ネットワーク アドレスが `10.{B}.0.0` のもの(プレフィックスの長さを問わない)だけを、受け取らないこと。それ以外の経路は、受け取ること",
                   "model": {"kind": "ext", "acl": [f"deny ip any host 10.{B}.0.0", "permit ip any any"]}}
    # T2: e0/1(RT03)・prefix-list(名前 PL-RT03)
    if rnd.random() < 0.5:
        t["T2"] = {"nbr": "RT03", "var": "len24_only", "method": "pl", "pl_name": "PL-RT03",
                   "req": "プレフィックスの長さが /24 であるところの経路だけを、受け取ること",
                   "model": {"kind": "pl", "acl": ["permit 0.0.0.0/0 ge 24 le 24"]}}
    else:
        t["T2"] = {"nbr": "RT03", "var": "len_le24", "method": "pl", "pl_name": "PL-RT03",
                   "req": "プレフィックスの長さが /24 以下であるところの経路だけを、受け取ること",
                   "model": {"kind": "pl", "acl": ["permit 0.0.0.0/0 le 24"]}}
    # T3: e0/2(RT05)・標準 ACL 1 行(番号 45)
    if rnd.random() < 0.5:
        t["T3"] = {"nbr": "RT05", "var": "c0_c2", "method": "std", "acl_no": 45,
                   "req": f"ネットワーク アドレスが `10.{C}.0.x` または `10.{C}.2.x` であるところの経路(プレフィックスの長さを問わない)だけを、受け取ること",
                   "model": {"kind": "std", "acl": [f"permit 10.{C}.0.0 0.0.2.255"]}}
    else:
        t["T3"] = {"nbr": "RT05", "var": "c1_c3", "method": "std", "acl_no": 45,
                   "req": f"ネットワーク アドレスが `10.{C}.1.x` または `10.{C}.3.x` であるところの経路(プレフィックスの長さを問わない)だけを、受け取ること",
                   "model": {"kind": "std", "acl": [f"permit 10.{C}.1.0 0.0.2.255"]}}
    # T4: e1/0(RT06)・route-map 経由の拡張 ACL(route-map RM-RT06・ACL 160)・prefix-list 禁止
    if rnd.random() < 0.5:
        t["T4"] = {"nbr": "RT06", "var": "drop_exact24", "method": "rm", "rm_name": "RM-RT06", "acl_no": 160,
                   "req": f"`10.{D}.0.0/24` の経路だけを、受け取らないこと。同じネットワーク アドレスを持つところの、プレフィックスの長さが異なる経路は、受け取ること",
                   "model": {"kind": "rm", "rm": [("deny", [f"permit ip host 10.{D}.0.0 host 255.255.255.0"]),
                                                  ("permit", None)]},
                   "acl_lines": [f"permit ip host 10.{D}.0.0 host 255.255.255.0"]}
    else:
        t["T4"] = {"nbr": "RT06", "var": "drop_ge25", "method": "rm", "rm_name": "RM-RT06", "acl_no": 160,
                   "req": "プレフィックスの長さが /25 以上であるところの経路は、受け取らないこと。それより短い経路は、受け取ること",
                   "model": {"kind": "rm", "rm": [("deny", ["permit ip any 255.255.255.128 0.0.0.127"]),
                                                  ("permit", None)]},
                   "acl_lines": ["permit ip any 255.255.255.128 0.0.0.127"]}
    return t


# ---------------------------------------------------------------- 構成
def render(n, v):
    b = battery(v)
    asn = v["asn"]
    if n == "RT01":
        return ["! RT01(被験)",
                "interface {{ links[0] }}", " description === to RT02 ===", " ip address 10.0.12.1 255.255.255.0", " no shutdown", "!",
                "interface {{ links[1] }}", " description === to RT03 ===", " ip address 10.0.13.1 255.255.255.0", " no shutdown", "!",
                "interface {{ links[2] }}", " description === to RT05 ===", " ip address 10.0.15.1 255.255.255.0", " no shutdown", "!",
                "interface {{ links[4] }}", " description === to RT06 ===", " ip address 10.0.16.1 255.255.255.0", " no shutdown", "!",
                f"router eigrp {asn}", " eigrp router-id 1.1.1.1",
                " network 10.0.12.0 0.0.0.255", " network 10.0.13.0 0.0.0.255",
                " network 10.0.15.0 0.0.0.255", " network 10.0.16.0 0.0.0.255", "!"]
    ifs = {"RT02": [("links[0]", "10.0.12.2", "to RT01"), ("links[1]", "10.0.24.2", "to RT04")],
           "RT03": [("links[0]", "10.0.13.3", "to RT01")],
           "RT04": [("links[0]", "10.0.24.4", "to RT02")],
           "RT05": [("links[0]", "10.0.15.5", "to RT01")],
           "RT06": [("links[0]", "10.0.16.6", "to RT01")]}[n]
    L = [f"! {n}(経路の提供元・変更禁止)"]
    for li, addr, desc in ifs:
        L += [f"interface {{{{ {li} }}}}", f" description === {desc} ===",
              f" ip address {addr} 255.255.255.0", " no shutdown", "!"]
    for p in b[n]:
        a, l = p.split("/")
        L.append(f"ip route {a} {mask(int(l))} Null0")
    L += ["!", f"router eigrp {asn}", f" eigrp router-id {n[-1]}.{n[-1]}.{n[-1]}.{n[-1]}"]
    L += [f" network {addr.rsplit('.', 1)[0]}.0 0.0.0.255" for _, addr, _ in ifs]
    L += [" redistribute static metric 10000 100 255 1 1500", "!"]
    return L


# ---------------------------------------------------------------- 採点
def _rx(p):
    return p.replace(".", r"\.")


def grading(prob_id, v, obs, tasks):
    allp = prefixes(v)
    checks = []
    # 第 1 部: PRED-k の中身= 期待集合(1 経路 1 行)。空なら deny 0.0.0.0/0 le 32
    for k, (key, f) in enumerate(obs, 1):
        exp = sorted(surviving(v, f), key=_pkey)
        raw = []
        if exp:
            raw += [{"regex": rf"(?m)permit {_rx(p)}$"} for p in exp]
        else:
            raw += [{"regex": r"(?m)deny 0\.0\.0\.0/0 le 32$"}]
        raw += [{"not_regex": rf"(?m)permit {_rx(p)}$"} for p in allp if p not in exp]
        raw += [{"not_regex": r"(?m)permit \S+ (ge|le) "}]
        checks.append({"name": f"第 1 部 PRED-{k}: 観察の提出({f['dl']} で残る経路)", "node": "RT01",
                       "command": f"show ip prefix-list PRED-{k}", "raw": raw, "points": 8})
    # 第 2 部: 効果(経路の有無)＋方式の指紋
    for tk, t in sorted(tasks.items()):
        nbr_ip = NBR[t["nbr"]]
        keep = surviving(v, t["model"], only_nbr=nbr_ip)
        mine = sorted({p for p, n in routes_at_rt01(v) if n == nbr_ip}, key=_pkey)
        raw = []
        for p in mine:
            if any(q == p and n != nbr_ip for q, n in routes_at_rt01(v)):
                # 別の隣接からも来る prefix(10.A.0.0/24・2.0/24)は経路表の有無では判定できない
                # → この隣接経由の next-hop があるかどうかで見る(下の show ip route <prefix>)
                continue
            raw.append({"regex" if p in keep else "not_regex": rf"(?m)^D EX\s+{_rx(p)} "})
        checks.append({"name": f"第 2 部 {tk}({IFACE[t['nbr']]}・{t['nbr']}): 経路の有無が要件どおり",
                       "node": "RT01", "command": "show ip route eigrp", "raw": raw, "points": 12})
        ifn = IFACE[t["nbr"]]
        if t["method"] == "ext":
            fp = [{"regex": rf"(?m)^ distribute-list {t['acl_no']} in {ifn}$"}]
        elif t["method"] == "pl":
            fp = [{"regex": rf"(?m)^ distribute-list prefix {t['pl_name']} in {ifn}$"}]
        elif t["method"] == "std":
            fp = [{"regex": rf"(?m)^ distribute-list {t['acl_no']} in {ifn}$"}]
        else:
            fp = [{"regex": rf"(?m)^ distribute-list route-map {t['rm_name']} in {ifn}$"}]
        checks.append({"name": f"第 2 部 {tk}: 指定の方式で {ifn} の in に適用", "node": "RT01",
                       "command": "show running-config | section router eigrp", "raw": fp,
                       "points": 4 if t["method"] not in ("std", "rm") else 2})
        if t["method"] == "std":
            checks.append({"name": f"第 2 部 {tk}: 標準 ACL {t['acl_no']} は 1 行", "node": "RT01",
                           "command": f"show ip access-lists {t['acl_no']}",
                           "raw": [{"regex": rf"Standard IP access list {t['acl_no']}"},
                                   {"not_regex": r"(?m)^\s+\d+ (permit|deny).*\n\s+\d+ (permit|deny)"}],
                           "points": 2})
        if t["method"] == "rm":
            checks.append({"name": f"第 2 部 {tk}: route-map {t['rm_name']} は拡張 ACL {t['acl_no']} で照合(prefix-list なし)",
                           "node": "RT01", "command": f"show route-map {t['rm_name']}",
                           "raw": [{"contains": f"route-map {t['rm_name']}"},
                                   {"regex": rf"ip address \(access-lists\): {t['acl_no']}"},
                                   {"not_contains": "prefix-lists"}],
                           "points": 2})
    # 別の隣接からも来る prefix の next-hop(RT02 経由・RT03 経由の有無)
    for p in (f"10.{v['A']}.0.0/24", f"10.{v['A']}.2.0/24"):
        a_, l_ = p.split("/")
        raw = []
        for tk, r in (("T1", "RT02"), ("T2", "RT03")):
            ok = p in surviving(v, tasks[tk]["model"], only_nbr=NBR[r])
            # ★詳細表示(show ip route <prefix>)の next-hop は「10.0.12.2, from 10.0.12.2, … via Ethernet0/0」の形
            #   (「via <IP>」は一覧表示だけ)
            raw.append({"contains" if ok else "not_contains": f"{NBR[r]}, from {NBR[r]}"})
        checks.append({"name": f"第 2 部 T1/T2: {p} を RT02・RT03 のどちらから受け取っているか",
                       "node": "RT01", "command": f"show ip route {a_} {mask(int(l_))}", "raw": raw, "points": 0})
    checks.append({"name": "最終状態に全体(インターフェイス指定なし)の distribute-list を残していない", "node": "RT01",
                   "command": "show running-config | section router eigrp",
                   "raw": [{"not_regex": r"(?m)^ distribute-list (prefix |route-map )?\S+ in$"}], "points": 4})
    assert sum(c["points"] for c in checks) == 100, sum(c["points"] for c in checks)
    return {"problem": prob_id, "total_points": 100, "defaults": {"genie_os": "iosxe"}, "checks": checks}


# ---------------------------------------------------------------- 模範解
def fix_entries(v, obs, tasks):
    asn = v["asn"]
    fixes = []
    for k, (key, f) in enumerate(obs, 1):
        exp = sorted(surviving(v, f), key=_pkey)
        lines = ([f"ip prefix-list PRED-{k} seq {5 * (i + 1)} permit {p}" for i, p in enumerate(exp)]
                 or [f"ip prefix-list PRED-{k} seq 5 deny 0.0.0.0/0 le 32"])
        fixes.append({"node": "RT01", "lines": lines, "match": "none"})
    g, R = [], []
    for tk, t in sorted(tasks.items()):
        ifn = IFACE[t["nbr"]]
        if t["method"] in ("ext", "std"):
            g += [f"access-list {t['acl_no']} {x}" for x in t["model"]["acl"]]
            R.append(f"distribute-list {t['acl_no']} in {ifn}")
        elif t["method"] == "pl":
            g += [f"ip prefix-list {t['pl_name']} seq {5 * (i + 1)} {x}" for i, x in enumerate(t["model"]["acl"])]
            R.append(f"distribute-list prefix {t['pl_name']} in {ifn}")
        else:
            g += [f"access-list {t['acl_no']} {x}" for x in t["acl_lines"]]
            fixes.append({"node": "RT01", "lines": g, "match": "none"})
            g = []
            fixes.append({"node": "RT01", "parents": [f"route-map {t['rm_name']} deny 10"],
                          "lines": [f"match ip address {t['acl_no']}"], "match": "none"})
            fixes.append({"node": "RT01", "parents": [f"route-map {t['rm_name']} permit 20"],
                          "lines": ["description pass the rest"], "match": "none"})
            R.append(f"distribute-list route-map {t['rm_name']} in {ifn}")
    if g:
        fixes.append({"node": "RT01", "lines": g, "match": "none"})
    fixes.append({"node": "RT01", "parents": [f"router eigrp {asn}"], "lines": R, "match": "none"})
    return fixes


# ---------------------------------------------------------------- 問題文
def task_md(prob_id, v, obs, tasks):
    A, B, C, D = v["A"], v["B"], v["C"], v["D"]
    steps = []
    for k, (key, f) in enumerate(obs, 1):
        cfg = "\n".join(f["cfg"])
        steps.append(f"""**観察 {k}**: 次のものを定義し、`router eigrp {v['asn']}` の直下で `{f['dl']}` を適用する。

```
{cfg}
```
""")
    tl = []
    for tk, t in sorted(tasks.items()):
        ifn = IFACE[t["nbr"]]
        if t["method"] == "ext":
            m = f"拡張アクセス リスト **{t['acl_no']}** を、distribute-list として**直接**指定すること。route-map および prefix-list は、使用してはなりません。"
        elif t["method"] == "pl":
            m = f"prefix-list **{t['pl_name']}** を使用すること。"
        elif t["method"] == "std":
            m = f"標準アクセス リスト **{t['acl_no']}** を使用し、エントリは **1 行**で構成されなければなりません。"
        else:
            m = (f"route-map **{t['rm_name']}** を使用し、その照合には拡張アクセス リスト **{t['acl_no']}** を用いること。"
                 "prefix-list は、使用してはなりません。")
        tl.append(f"### {tk}: {t['nbr']} から受け取る経路({ifn} の着信)\n\n{t['req']}。\n\n**方式**: {m}\n")
    return f"""# 問題 {prob_id} : distribute-list 道場

## シナリオ

RT01 は、4 台の隣接ルータから EIGRP AS {v['asn']} によって経路を受け取っています。あなたのタスクは、第 1 部において、
フィルタの種類ごとに**どの経路が残るのか**を観察して提出し、第 2 部において、指定された方式によって受け取る経路を制御することです。
作業は、**RT01 の上だけ**で行います。

```
    RT04 ── RT02 ──e0/0── RT01 ──e0/1── RT03
                          │e0/2   │e1/0
                         RT05    RT06
```

| リンク | ネットワーク | RT01 側 | 隣接の IP |
|---|---|---|---|
| RT01 ⇔ RT02 | 10.0.12.0/24 | Ethernet0/0 (.1) | 10.0.12.2 |
| RT01 ⇔ RT03 | 10.0.13.0/24 | Ethernet0/1 (.1) | 10.0.13.3 |
| RT01 ⇔ RT05 | 10.0.15.0/24 | Ethernet0/2 (.1) | 10.0.15.5 |
| RT01 ⇔ RT06 | 10.0.16.0/24 | Ethernet1/0 (.1) | 10.0.16.6 |
| RT02 ⇔ RT04 | 10.0.24.0/24 | — | RT04 = 10.0.24.4 |

RT04 が作成した経路は、RT02 を経由して RT01 へ届きます。隣接ルータの構成を変更してはなりません。

## 道場の心得(distribute-list の読み方)

distribute-list に渡したアクセス リストは、**参照のしかたによって、同じ書式でも意味が変わります**。

| 書き方 | 前半(src)が指すもの | 後半(dst)が指すもの | 長さで絞れるか |
|---|---|---|---|
| 標準 ACL を直接 `distribute-list 10 in` | ネットワーク アドレス(src だけ) | — | できない |
| 拡張 ACL を直接 `distribute-list 150 in` | **経路を広告してきた隣接ルータ**のアドレス | **ネットワーク アドレス** | できない |
| 拡張 ACL を route-map 経由 `distribute-list route-map RM in` ＋ `match ip address 150` | **ネットワーク アドレス** | **サブネット マスク** | できる |
| prefix-list `distribute-list prefix PL in` | ネットワーク アドレスとプレフィックス長を別々に指定(`ge`・`le`) | | できる |

- **ワイルドカードは「アドレスの範囲(ビットの一致)」であって、プレフィックス長の指定ではありません。**
  `permit 10.1.0.0 0.0.0.255` は「ネットワーク アドレスが 10.1.0.0〜10.1.0.255 のもの」に当たり、
  10.1.0.0/24 にも 10.1.0.0/28 にも 10.1.0.128/25 にも当たります。連続しないワイルドカード
  (例 `0.0.2.255`)は、とびとびの集合(0.x と 2.x)に当たります。
- 拡張 ACL を直接指定したときの「広告してきた隣接」は、**直接アップデートを送ってきた隣のルータ**です。
  その経路を作ったルータではありません(奥のルータの経路は、手前の隣接が広告してきたものとして見えます)。
- route-map 経由では、dst 側に**マスクの値**を書きます。`host 255.255.255.0` は「/24 ちょうど」、
  `255.255.255.0 0.0.0.255` は「マスクが 255.255.255.x = /24〜/32」です。
- **全体(`distribute-list … in`)とインターフェイス単位(`distribute-list … in <IF>`)は、両方効きます(AND)。**
- 1 つのインターフェイスに付けられる着信の distribute-list は 1 つだけです。
- 確かめ方: `show ip route eigrp`(残った経路)・`show access-lists`(経路 1 本×隣接ごとに 1 件ずつカウンタが増える)・
  `show ip protocols`(どこに何が掛かっているか)。

## 第 1 部: 観察の提出

次の 4 つのフィルタを、**1 つずつ**適用して観察します(**第 2 部より先に**行うこと。インターフェイス単位の
distribute-list が掛かっていると、全体の distribute-list と**両方**が効くため、観察の結果が変わります)。それぞれについて:

1. 適用する前に、どの経路が RT01 の経路表に残るかを**予想**する。
2. 適用し、10〜20 秒待ってから `show ip route eigrp` で確かめる(`show access-lists` のカウンタも見ること)。
3. 残った経路を、prefix-list **PRED-k** に **1 経路 1 行**(`ge`・`le` を使わない)で書く。
   リンクのネットワーク(10.0.x.x)は書かない。1 つも残らない場合は `deny 0.0.0.0/0 le 32` の 1 行だけにする。
4. 次の観察の前に、その distribute-list を `no` で外す。

{chr(10).join(steps)}
## 第 2 部: 本番

次のタスクを、それぞれ指定されたインターフェイスの着信(`distribute-list … in <インターフェイス>`)として実装します。
第 1 部で使った distribute-list(インターフェイスの指定が無いもの)は、最終状態に残してはなりません。

{chr(10).join(tl)}
## 注意

- 設定の反映は `clear` 不要で、約 10 秒かかります。反映時にはログに `… is resync: route configuration changed` が出ます。
- 1 つのインターフェイスに着信の distribute-list は 1 つしか設定できません(2 つ目は拒否されます)。方式を変えるときは、先に `no` で外します。
- `show ip protocols` で、どのインターフェイスにどのフィルタが掛かっているかを確認できます。

## アクセス・採点

SSH で RT01 にログイン(`SUZUKI / CCNP`・mgmt IP は出題時に提示)。
```
scripts/lab.sh grade {prob_id}
```
"""


# ---------------------------------------------------------------- 出力
def build(seed):
    rnd = random.Random(seed)
    v = rand_values(rnd)
    obs = draw_obs(rnd, v)
    tasks = draw_tasks(rnd, v)
    return v, obs, tasks


def write(repo, seed):
    v, obs, tasks = build(seed)
    prob_id = f"GEN-DOJO-DLIST-{seed}"
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id, "title": f"distribute-list 道場 (seed={seed})", "exam": "ENARSI",
               "topics": ["distribute-list", "acl", "prefix-list", "route-map", "eigrp", "dojo", "generated"],
               "difficulty": 4, "topology": "generated", "image_family": "iol",
               "target_nodes": NODES, "points": 100, "access": "ssh",
               "lab": {"links": [
                   {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                   {"a": "RT01", "a_if": 1, "b": "RT03", "b_if": 0},
                   {"a": "RT01", "a_if": 2, "b": "RT05", "b_if": 0},
                   {"a": "RT01", "a_if": 4, "b": "RT06", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "RT04", "b_if": 0}],
                   "positions": {"RT01": [0, 0], "RT02": [-300, 0], "RT04": [-600, 0], "RT03": [300, 0],
                                 "RT05": [-150, 250], "RT06": [150, 250]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dojo_dlist.py) seed={seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for n in NODES:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render(n, v)) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dojo_dlist.py) seed={seed}\n")
        yaml.safe_dump(grading(prob_id, v, obs, tasks), f, sort_keys=False, allow_unicode=True)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task_md(prob_id, v, obs, tasks))
    json.dump({"fixes": fix_entries(v, obs, tasks)}, open(f"{pdir}/solution/fix.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(f"{pdir}/solution/README.md", "w", encoding="utf-8") as f:
        f.write(f"# 採点者専用 ({prob_id})\n\n## 第 1 部の期待集合\n\n")
        for k, (key, fl) in enumerate(obs, 1):
            exp = sorted(surviving(v, fl), key=_pkey)
            f.write(f"- PRED-{k} `{fl['dl']}`({key}): {', '.join(exp) or '(なし)'}\n")
        f.write("\n## 第 2 部\n\n")
        for tk, t in sorted(tasks.items()):
            keep = surviving(v, t["model"], only_nbr=NBR[t["nbr"]])
            mine = sorted({p for p, n in routes_at_rt01(v) if n == NBR[t["nbr"]]}, key=_pkey)
            f.write(f"- {tk}({t['var']}): 残す= {', '.join(p for p in mine if p in keep)} / "
                    f"落とす= {', '.join(p for p in mine if p not in keep)}\n")
        f.write("\n模範解= solution/fix.json(RT01 のみ)。\n")
    print(f"wrote {prob_id}: obs={[k for k, _ in obs]} tasks={ {k: t['var'] for k, t in tasks.items()} }")


def selftest():
    n = 0
    for seed in range(300):
        v, obs, tasks = build(seed)
        allp = prefixes(v)
        assert len(allp) == 26, len(allp)
        # 第 1 部: 観察ごとの期待が互いに区別できる(同じ集合ばかりにならない)
        sets = [frozenset(surviving(v, f)) for _, f in obs]
        assert len(set(sets)) >= 3, (seed, [k for k, _ in obs])
        # 第 2 部: どのタスクも「全部残す」「全部落とす」にならない
        for tk, t in tasks.items():
            nb = NBR[t["nbr"]]
            mine = {p for p, x in routes_at_rt01(v) if x == nb}
            keep = surviving(v, t["model"], only_nbr=nb) & mine
            assert 0 < len(keep) < len(mine), (seed, tk, t["var"], keep)
        g = grading("X", v, obs, tasks)
        assert sum(c["points"] for c in g["checks"]) == 100
        n += 1
    # 意味論の固定値(PoC と同じ battery で D1a〜D4b を再現)
    v = {"A": 50, "B": 60, "C": 70, "D": 80, "asn": 100}
    pool = obs_pool(v)
    only_a = lambda s: sorted((p for p in s if p.startswith("10.50.") or p.startswith("10.60.")), key=_pkey)
    assert only_a(surviving(v, pool["std_host"])) == ["10.50.0.0/22", "10.50.0.0/24", "10.50.0.0/26", "10.50.0.0/28"]
    assert only_a(surviving(v, pool["ext_src_net"])) == []
    assert only_a(surviving(v, pool["ext_src_origin"])) == []
    assert only_a(surviving(v, pool["ext_nbr_net"])) == ["10.60.0.0/24", "10.60.0.0/28"]
    assert only_a(surviving(v, pool["rm_exact"])) == ["10.50.0.0/24"]
    assert "10.50.0.0/22" not in surviving(v, pool["rm_range"]) and "10.50.0.0/28" in surviving(v, pool["rm_range"])
    print(f"selftest OK: {n} seeds + PoC 固定値")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if a.seed is None:
        a.seed = random.randint(10000, 99999)
    write(a.repo, a.seed)


if __name__ == "__main__":
    main()
