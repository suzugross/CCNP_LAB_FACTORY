#!/usr/bin/env python3
"""BGP リング TS 生成器（BL-093: 4台リング×AS配置抽選・AS設計/ポリシー層）。

物理リング4台固定の上で **AS配置(layout)** と **シナリオ(shape)** を seed 抽選し、
`GEN-BGPRING-<seed>` を生成する（IDから型が割れない・gen_redist_field 方式）。
配管層(セッション/activate/IGP連鎖)は gen_bgp_complex_ts の縄張りとし、本生成器は
セッション健全を前提に AS設計・ポリシー層の TS を出す。

■ layout（shape が決める）
  four_as       : 全台別AS                → no_transit / path_select / stale
  split_company : 対角2台=自社同一AS+ISP×2 → isp_exchange
  one_as        : 全台同一AS(iBGPフルメッシュ×OSPF) → ibgp_ring

■ shape カタログ（--shape で強制可・既定は seed 抽選）
  isp_exchange : ISP越し自社AS経路交換不能。variant=allowas_full/allowas_partial/
                 override_partial(ISP側as-override残骸で片側だけ通る)
  no_transit   : 自社ASが2ISP間のトランジットに使われている→遮断。
                 --solution aspath(filter-list ^$強制)/routemap(route-map out強制)
  path_select  : 対角ペアの双方向経路指定。fwd=LP系(欠落/誤適用/weight残骸) or
                 MED系(異AS間MED非比較→always-compare-med) × ret=prepend系
  stale        : 監査是正形。実害残骸(weight/裏LP)＋無害残骸(allowas-in/as-override)の
                 混在を全撤去(★PoC実測: as-override/allowas-inは素の4ASリングで不発)
  ibgp_ring    : 全iBGP。mesh欠落(全Established・対角のみ欠け)/network欠落/OSPF Lo欠落

■ PoC 由来の設計規則（poc/bgp-ring/README.md 2026-08-05）
  - 対角プレフィックスのAS長タイは oldest 勝ちで非決定的
    → eBGP系 layout は全機 `bgp bestpath compare-routerid` を焼き、RID(Lo0)で決定化
  - inbound ポリシー付替えの fix は `clear ip bgp * in`(ハード) を exec で付ける
  - `bgp always-compare-med` は clear 不要(15秒自動再計算)
  - BGPプロセスは day0 で最初から構成する(作り直しの update-delay 120s を踏まない)

出力: problems/GEN-BGPRING-<seed>/ (problem.yml / initial/*.cfg.j2 / grading.yml /
      task.md / solution/{fault,fix,decoys}.json+README.md)
使い方: gen_bgp_ring_ts.py --repo . --seed <int> [--shape S] [--faults N]
        [--variant V] [--solution aspath|routemap] [--decoys K] / [--selftest]
"""
import argparse
import json
import os
import random

import yaml

ROUTERS = ["RT01", "RT02", "RT03", "RT04"]
NEXT = {"RT01": "RT02", "RT02": "RT03", "RT03": "RT04", "RT04": "RT01"}
PREV = {v: k for k, v in NEXT.items()}
DIAG = {"RT01": "RT03", "RT03": "RT01", "RT02": "RT04", "RT04": "RT02"}
LINKS = [("RT01", "RT02"), ("RT02", "RT03"), ("RT03", "RT04"), ("RT04", "RT01")]
SLOTS = {"RT01": {"RT02": 0, "RT04": 1}, "RT02": {"RT01": 0, "RT03": 1},
         "RT03": {"RT02": 0, "RT04": 1}, "RT04": {"RT03": 0, "RT01": 1}}
SHAPES = ["isp_exchange", "no_transit", "path_select", "stale", "ibgp_ring"]
SHAPE_W = [25, 20, 25, 15, 15]


# ---------------------------------------------------------------- 盤面モデル
class Board:
    """seed から決まる盤面（アドレス・AS・役割）。shape 関数が読み書きする。"""

    def __init__(self, rnd, shape):
        self.rnd = rnd
        self.shape = shape
        self.layout = {"isp_exchange": "split_company", "ibgp_ring": "one_as"}.get(
            shape, "four_as")
        # リンク網 10.p.q.0/30（一意）
        segs, used = {}, set()
        for pair in LINKS:
            while True:
                p, q = rnd.randint(0, 254), rnd.randint(0, 254)
                if (p, q) not in used:
                    used.add((p, q)); segs[pair] = f"10.{p}.{q}"; break
        self.segs = segs
        # Lo0 = k.k.k.k（RID）/ Lo1 = 172.16.x.0/24
        ks = rnd.sample(range(1, 100), 4)
        self.k = dict(zip(ROUTERS, ks))
        xs = rnd.sample(range(1, 251), 4)
        self.px = dict(zip(ROUTERS, xs))
        # AS 配置
        self.asn = {}
        if self.layout == "four_as":
            vals = rnd.sample(range(64512, 65535), 4)
            self.asn = dict(zip(ROUTERS, vals))
        elif self.layout == "one_as":
            v = rnd.randint(64512, 65534)
            self.asn = {r: v for r in ROUTERS}
        else:  # split_company: 対角ペアを自社に
            self.company = list(rnd.choice([("RT01", "RT03"), ("RT02", "RT04")]))
            vals = rnd.sample(range(64512, 65535), 3)
            co, i1, i2 = vals
            for r in ROUTERS:
                self.asn[r] = co if r in self.company else (
                    i1 if r == NEXT[self.company[0]] else i2)

    # --- アドレスヘルパ ---
    def lo0(self, r):
        return f"{self.k[r]}.{self.k[r]}.{self.k[r]}.{self.k[r]}"

    def prefix(self, r):
        return f"172.16.{self.px[r]}.0"

    def lo1(self, r):
        return f"172.16.{self.px[r]}.1"

    def link_of(self, x, y):
        for pair in LINKS:
            if set(pair) == {x, y}:
                return pair
        raise KeyError((x, y))

    def ip(self, me, peer):
        pair = self.link_of(me, peer)
        seg = self.segs[pair]
        return f"{seg}.1" if pair[0] == me else f"{seg}.2"

    def swap_rid(self, lower, higher):
        """lower の RID < higher の RID を保証（compare-routerid のタイ決定化）。"""
        if self.k[lower] > self.k[higher]:
            self.k[lower], self.k[higher] = self.k[higher], self.k[lower]


# ---------------------------------------------------------------- config 描画
def base_config(b, r, extra_session, extra_af, extra_global):
    """1台分の initial/*.cfg.j2 本文。extra_* は shape が注入する行のリスト。"""
    L = [f"! {r}", "interface Loopback0",
         f" ip address {b.lo0(r)} 255.255.255.255", "!",
         "interface Loopback1",
         f" ip address {b.lo1(r)} 255.255.255.0", "!"]
    for peer in (NEXT[r], PREV[r]):
        slot = SLOTS[r][peer]
        L += [f"interface {{{{ links[{slot}] }}}}",
              f" ip address {b.ip(r, peer)} 255.255.255.252",
              " no shutdown", "!"]
    if b.layout == "one_as":
        L += ["router ospf 1", f" router-id {b.lo0(r)}"]
        for peer in (NEXT[r], PREV[r]):
            seg = b.segs[b.link_of(r, peer)]
            L.append(f" network {seg}.0 0.0.0.3 area 0")
        L += [f" network {b.lo0(r)} 0.0.0.0 area 0", "!"]
    B = [f"router bgp {b.asn[r]}", f" bgp router-id {b.lo0(r)}",
         " bgp log-neighbor-changes", " no bgp default ipv4-unicast"]
    if b.layout != "one_as":
        B.append(" bgp bestpath compare-routerid")   # PoC: タイ決定化(必須)
    if b.layout == "one_as":
        for peer in ROUTERS:
            if peer == r:
                continue
            B += [f" neighbor {b.lo0(peer)} remote-as {b.asn[peer]}",
                  f" neighbor {b.lo0(peer)} update-source Loopback0"]
    else:
        for peer in (NEXT[r], PREV[r]):
            B.append(f" neighbor {b.ip(peer, r)} remote-as {b.asn[peer]}")
    B += [f" {x}" for x in extra_session.get(r, [])]
    B.append(" address-family ipv4 unicast")
    B.append(f"  network {b.prefix(r)} mask 255.255.255.0")
    if b.layout == "one_as":
        for peer in ROUTERS:
            if peer != r:
                B.append(f"  neighbor {b.lo0(peer)} activate")
    else:
        for peer in (NEXT[r], PREV[r]):
            B.append(f"  neighbor {b.ip(peer, r)} activate")
    B += [f"  {x}" for x in extra_af.get(r, [])]
    B.append(" exit-address-family")
    L += B + ["!"]
    L += extra_global.get(r, [])
    return L


def bgp_sec(b, r):
    return f"show run | section router bgp"


def af_parents(b, r):
    return [f"router bgp {b.asn[r]}", "address-family ipv4 unicast"]


# ---------------------------------------------------------------- 各 shape
# 各 shape 関数は dict を返す:
#   session/af/glob: {router: [lines]}（initial への注入）
#   fixes: fix.json エントリ列 / faults: 記録 / checks: grading checks
#   task: {situation, requirements[], constraints[], title, diff}
def shape_isp_exchange(b, a):
    rnd = b.rnd
    S1, S2 = b.company
    I1, I2 = NEXT[S1], PREV[S1]
    co, as1, as2 = b.asn[S1], b.asn[I1], b.asn[I2]
    variant = a.variant or rnd.choices(
        ["allowas_full", "allowas_partial", "override_partial"], [40, 30, 30])[0]
    session, af, glob = {}, {}, {}
    pre = []          # 既に入っている allowas-in（partial 変種）
    if variant == "allowas_partial":
        pre = [(S1, I1)]
        af[S1] = [f"neighbor {b.ip(I1, S1)} allowas-in"]
    if variant == "override_partial":
        af[I1] = [f"neighbor {b.ip(S2, I1)} as-override"]
    # ---- fix: 自社4方向 allowas-in（既存分は除く）＋override は残骸撤去
    fixes, need = [], []
    for site in (S1, S2):
        for isp in (I1, I2):
            if (site, isp) not in pre:
                need.append((site, isp))
    for site in (S1, S2):
        lines = [f"neighbor {b.ip(isp, site)} allowas-in"
                 for (s, isp) in need if s == site]
        if lines:
            fixes.append({"node": site, "parents": af_parents(b, site),
                          "lines": lines, "match": "none"})
    if variant == "override_partial":
        fixes.append({"node": I1, "parents": af_parents(b, I1),
                      "lines": [f"no neighbor {b.ip(S2, I1)} as-override"],
                      "match": "none"})
        fixes.append({"node": I1, "exec": ["clear ip bgp * out"]})
    for site in (S1, S2):
        fixes.append({"node": site, "exec": ["clear ip bgp * in"]})
    # ---- checks
    checks = []
    for me, other in ((S1, S2), (S2, S1)):
        checks.append({
            "name": f"{me}: 対向拠点網 {b.prefix(other)}/24 を両事業者経由の2経路で保持",
            "node": me, "command": f"show ip bgp {b.prefix(other)}",
            "raw": [{"regex": r"Paths: \(2 available"},
                    {"contains": f"{as1} {co}"}, {"contains": f"{as2} {co}"},
                    {"not_regex": rf"{as1} +{as1}\b"}], "points": 20})
    if variant == "override_partial":
        checks.append({
            "name": f"{I1}: 顧客向け経路広告のAS書換オプションが撤去されている",
            "node": I1, "command": bgp_sec(b, I1),
            "raw": [{"contains": f"router bgp {as2 if I1==PREV[S1] else as1}"},
                    {"not_contains": "as-override"}], "points": 10})
    else:
        checks.append({
            "name": f"{S1}: 事業者との両セッションが Established (拠点側)",
            "node": S1, "command": "show ip bgp summary",
            "raw": [{"regex": rf"(?m)^{b.ip(I1, S1)}\s+4\s+{as1}\s.*\s\d+\s*$"},
                    {"regex": rf"(?m)^{b.ip(I2, S1)}\s+4\s+{as2}\s.*\s\d+\s*$"}],
            "points": 10})
    task = {
        "title": "拠点間の経路交換の回復",
        "situation": (
            f"あなたの会社は、2つの拠点({S1} および {S2})を、運用しています。"
            f"それぞれの拠点は、2つの通信事業者({I1} および {I2})のそれぞれと、"
            "eBGP によって、接続されています。拠点のネットワークは、対向の拠点へ、"
            "事業者の網を経由して、広告されることが、意図されています。\n"
            "現在、拠点の間の通信が、確立できない、ということが、報告されています。"
            + ("なお、一方の拠点においては、過去の保守作業に由来するところの構成が、"
               "残存している可能性が、あります。" if variant != "allowas_full" else "")),
        "requirements": [
            f"それぞれの拠点が、対向拠点のネットワーク"
            f"(`{b.prefix(S2)}/24` / `{b.prefix(S1)}/24`)へ、到達することができること。",
            "対向拠点への経路が、**両方の事業者を経由するところの、2つの経路**として、"
            "保持されていること(片系の障害に、備えるため)。",
            "経路の AS パスが、実際に経由するところの AS を、正しく反映していること。",
        ],
        "constraints": [
            "お客様のASに対する経路広告の内容に関するものを除き、事業者装置"
            f"({I1} / {I2})の構成は、変更されてはなりません。",
            "スタティック・ルートの追加、および、既存のアドレス設計の変更は、"
            "許可されていません。",
        ],
        "diff": 5 if variant != "allowas_full" else 4,
    }
    return {"session": session, "af": af, "glob": glob, "fixes": fixes,
            "faults": [f"isp_exchange:{variant}"], "checks": checks,
            "task": task, "meta": {"variant": variant, "company": b.company,
                                   "isp": [I1, I2]}}


def shape_no_transit(b, a):
    rnd = b.rnd
    C = rnd.choice(ROUTERS)
    I1, I2, D = NEXT[C], PREV[C], DIAG[C]
    b.swap_rid(C, D)     # ISP の対角タイ(via C vs via D)を via C に固定=トランジット発生
    solution = a.solution or rnd.choice(["aspath", "routemap"])
    session, af, glob = {}, {}, {}
    # ---- fix
    fixes = []
    if solution == "aspath":
        fixes.append({"node": C, "lines": ["ip as-path access-list 10 permit ^$"],
                      "match": "none"})
        fixes.append({"node": C, "parents": af_parents(b, C),
                      "lines": [f"neighbor {b.ip(I1, C)} filter-list 10 out",
                                f"neighbor {b.ip(I2, C)} filter-list 10 out"],
                      "match": "none"})
    else:
        fixes.append({"node": C, "lines": [
            f"ip prefix-list PL-LOCAL-EXPORT permit {b.prefix(C)}/24",
            "route-map RM-EXPORT permit 10",
            " match ip address prefix-list PL-LOCAL-EXPORT"], "match": "none"})
        fixes.append({"node": C, "parents": af_parents(b, C),
                      "lines": [f"neighbor {b.ip(I1, C)} route-map RM-EXPORT out",
                                f"neighbor {b.ip(I2, C)} route-map RM-EXPORT out"],
                      "match": "none"})
    fixes.append({"node": C, "exec": ["clear ip bgp * soft out"]})
    # ---- checks
    asC, asD = b.asn[C], b.asn[D]
    checks = []
    for isp, other in ((I1, I2), (I2, I1)):
        checks.append({
            "name": f"{isp}: 他事業者網 {b.prefix(other)}/24 への経路が {C} を経由しない",
            "node": isp, "command": f"show ip bgp {b.prefix(other)}",
            "raw": [{"contains": f"{asD} {b.asn[other]}"},
                    {"not_contains": f"{asC} {b.asn[other]}"}], "points": 20})
        checks.append({
            "name": f"{isp}: 自社網 {b.prefix(C)}/24 の広告は維持されている",
            "node": isp, "command": f"show ip bgp {b.prefix(C)}",
            "raw": [{"regex": rf"{asC}\b"}], "points": 5})
    checks.append({
        "name": f"{C}: 事業者への広告が自社の経路のみである",
        "node": C, "command": f"show ip bgp neighbors {b.ip(I1, C)} advertised-routes",
        "raw": [{"contains": "Total number of prefixes 1"},
                {"contains": b.prefix(C)}], "points": 10})
    if solution == "aspath":
        checks.append({
            "name": f"{C}: 監査: フィルタは AS パスのフィルタ・リストで実装されている",
            "node": C, "command": bgp_sec(b, C),
            "raw": [{"regex": rf"neighbor {b.ip(I1, C)} filter-list \d+ out"},
                    {"regex": rf"neighbor {b.ip(I2, C)} filter-list \d+ out"},
                    {"not_regex": r"neighbor \S+ route-map \S+ out"}], "points": 10})
        audit_req = ("この制御は、AS パスに基づくところの、フィルタ・リストによって、"
                     "実装されること。プレフィックスを個別に列挙するところの手法は、"
                     "承認されていません。")
    else:
        checks.append({
            "name": f"{C}: 監査: フィルタは route-map で実装されている",
            "node": C, "command": bgp_sec(b, C),
            "raw": [{"regex": rf"neighbor {b.ip(I1, C)} route-map \S+ out"},
                    {"regex": rf"neighbor {b.ip(I2, C)} route-map \S+ out"},
                    {"not_regex": r"filter-list"}], "points": 10})
        audit_req = ("この制御は、route-map によって、実装されること。"
                     "フィルタ・リスト(as-path filter-list)の使用は、承認されていません。")
    task = {
        "title": "トランジット トラフィックの排除",
        "situation": (
            f"あなたの会社のルータ({C})は、2つの通信事業者({I1} および {I2})に、"
            "eBGP によって、接続されています。"
            "回線の使用率の監視において、あなたの会社のものではないところの"
            "トラフィックが、あなたの回線を通過している、ということが、検出されました。"
            "これは、意図された動作ではありません。"),
        "requirements": [
            f"他の組織の間のトラフィックが、あなたの会社のAS({C})を、"
            "経由してはなりません。",
            f"あなたの会社のネットワーク(`{b.prefix(C)}/24`)の、両事業者への広告は、"
            "維持されていること。",
            audit_req,
            "すべてのネットワークへの到達性が、維持されていること。",
        ],
        "constraints": [
            f"構成の変更は、あなたの会社の管理下にあるところのデバイスにおいてのみ、"
            "許可されています。",
            "BGP セッションの削除、および、スタティック・ルートの追加は、"
            "許可されていません。",
        ],
        "diff": 4,
    }
    return {"session": session, "af": af, "glob": glob, "fixes": fixes,
            "faults": [f"no_transit:{solution}"], "checks": checks,
            "task": task, "meta": {"company": C, "isp": [I1, I2], "far": D,
                                   "solution": solution}}


def _pathsel_board(b, rnd):
    """path_select/stale 共通の盤面役割: 対角ペア A-B と、主(P)/副(S)の隣接。"""
    A = rnd.choice(ROUTERS)
    Bx = DIAG[A]
    P = rnd.choice([NEXT[A], PREV[A]])
    S = PREV[A] if P == NEXT[A] else NEXT[A]
    b.swap_rid(S, P)   # タイ発生時(制御欠落)は副(S)側が勝つ=症状を決定化
    return A, Bx, P, S


def _lp_block(b, Bx):
    return [f"ip prefix-list PL-DIAG permit {b.prefix(Bx)}/24",
            "route-map RM-LP-IN permit 10",
            " match ip address prefix-list PL-DIAG",
            " set local-preference 200",
            "route-map RM-LP-IN permit 20", "!"]


def _prepend_block(b, A):
    return [f"ip prefix-list PL-SELF permit {b.prefix(A)}/24",
            "route-map RM-PREPEND-OUT permit 10",
            " match ip address prefix-list PL-SELF",
            f" set as-path prepend {b.asn[A]} {b.asn[A]}",
            "route-map RM-PREPEND-OUT permit 20", "!"]


def shape_path_select(b, a):
    rnd = b.rnd
    A, Bx, P, S = _pathsel_board(b, rnd)
    fwd_mech = rnd.choice(["lp", "med"])
    pool_fwd = (["lp_missing", "lp_wrong_nbr", "weight_stale"] if fwd_mech == "lp"
                else ["med_acm_missing"])
    pool_ret = ["prepend_missing", "prepend_wrong_nbr"]
    n = max(1, min(a.faults, 2))
    if n == 1:
        faults = [rnd.choice(pool_fwd + pool_ret)]
    else:
        faults = [rnd.choice(pool_fwd), rnd.choice(pool_ret)]
    has = set(faults)

    # ---- 盤面組み立て（ブロック単位・故障で丸ごと落とす/差し替える）
    session, af, glob = {}, {}, {}
    fixes = []
    if fwd_mech == "lp":
        if "lp_missing" not in has:
            glob.setdefault(A, []).extend(_lp_block(b, Bx))
            nbr = S if "lp_wrong_nbr" in has else P
            af.setdefault(A, []).append(
                f"neighbor {b.ip(nbr, A)} route-map RM-LP-IN in")
        if "weight_stale" in has:
            af.setdefault(A, []).append(f"neighbor {b.ip(S, A)} weight 40000")
    else:
        for nd, med in ((P, 50), (S, 200)):
            glob.setdefault(nd, []).extend(
                ["route-map RM-MED-OUT permit 10", f" set metric {med}", "!"])
            af.setdefault(nd, []).append(
                f"neighbor {b.ip(A, nd)} route-map RM-MED-OUT out")
        if "med_acm_missing" not in has:
            session.setdefault(A, []).append("bgp always-compare-med")
    if "prepend_missing" not in has:
        glob.setdefault(A, []).extend(_prepend_block(b, A))
        nbr = P if "prepend_wrong_nbr" in has else S
        af.setdefault(A, []).append(
            f"neighbor {b.ip(nbr, A)} route-map RM-PREPEND-OUT out")

    # ---- fix
    for ft in faults:
        if ft == "lp_missing":
            fixes += [{"node": A, "lines": _lp_block(b, Bx)[:-1], "match": "none"},
                      {"node": A, "parents": af_parents(b, A),
                       "lines": [f"neighbor {b.ip(P, A)} route-map RM-LP-IN in"],
                       "match": "none"},
                      {"node": A, "exec": ["clear ip bgp * in"]}]
        elif ft == "lp_wrong_nbr":
            fixes += [{"node": A, "parents": af_parents(b, A),
                       "lines": [f"no neighbor {b.ip(S, A)} route-map RM-LP-IN in",
                                 f"neighbor {b.ip(P, A)} route-map RM-LP-IN in"],
                       "match": "none"},
                      {"node": A, "exec": ["clear ip bgp * in"]}]
        elif ft == "weight_stale":
            fixes += [{"node": A, "parents": af_parents(b, A),
                       "lines": [f"no neighbor {b.ip(S, A)} weight 40000"],
                       "match": "none"},
                      {"node": A, "exec": ["clear ip bgp * in"]}]
        elif ft == "med_acm_missing":
            fixes += [{"node": A, "parents": [f"router bgp {b.asn[A]}"],
                       "lines": ["bgp always-compare-med"], "match": "none"}]
        elif ft == "prepend_missing":
            fixes += [{"node": A, "lines": _prepend_block(b, A)[:-1],
                       "match": "none"},
                      {"node": A, "parents": af_parents(b, A),
                       "lines": [
                           f"neighbor {b.ip(S, A)} route-map RM-PREPEND-OUT out"],
                       "match": "none"},
                      {"node": A, "exec": ["clear ip bgp * soft out"]}]
        elif ft == "prepend_wrong_nbr":
            fixes += [{"node": A, "parents": af_parents(b, A),
                       "lines": [
                           f"no neighbor {b.ip(P, A)} route-map RM-PREPEND-OUT out",
                           f"neighbor {b.ip(S, A)} route-map RM-PREPEND-OUT out"],
                       "match": "none"},
                      {"node": A, "exec": ["clear ip bgp * soft out"]}]
    # ---- checks（両方向とも P 経由・S を使わない）
    checks = [
        {"name": f"{A}: {b.prefix(Bx)}/24 への転送が主経路({P})を経由する",
         "node": A, "command": f"show ip route {b.prefix(Bx)}",
         "raw": [{"contains": b.ip(P, A)}, {"not_contains": b.ip(S, A)}],
         "points": 25},
        {"name": f"{Bx}: {b.prefix(A)}/24 への転送が主経路({P})を経由する",
         "node": Bx, "command": f"show ip route {b.prefix(A)}",
         "raw": [{"contains": b.ip(P, Bx)}, {"not_contains": b.ip(S, Bx)}],
         "points": 25},
        {"name": f"{A}: 近隣単位の weight が使用されていない(監査)",
         "node": A, "command": bgp_sec(b, A),
         "raw": [{"contains": f"router bgp {b.asn[A]}"},
                 {"not_regex": r"neighbor \S+ weight \d+"}], "points": 10},
    ]
    if fwd_mech == "med":
        req_fwd = (f"2つの中継AS({P} / {S})の優先順位は、事業者間の合意に基づき、"
                   "**MED 属性によって、表現されています**。この合意が、"
                   "経路選択において、尊重されていること。")
    else:
        req_fwd = (f"{A} と {Bx} の間のトラフィックは、双方向において、"
                   f"主契約の中継AS({P})を、経由すること。{S} は、予備であり、"
                   "主系の障害時にのみ、使用されること。")
    task = {
        "title": "経路選択ポリシーの復旧",
        "situation": (
            f"4つの組織のルータが、リング状に、相互接続されています。"
            f"{A} と {Bx} の間のトラフィックの経路について、契約に基づくところの"
            "ポリシーが、定義されています。しかしながら、直近の監視レポートに"
            "おいて、トラフィックが、意図されていないところの経路を、通過している、"
            "ということが、示されています。"
            "なお、昨夜、機器のリプレースに伴うところの、設定の restore 作業が、"
            "実施されています。"),
        "requirements": [
            req_fwd,
            (f"{A} と {Bx} の間のトラフィックは、双方向において、同一の中継AS"
             f"({P})を、経由すること。" if fwd_mech == "med" else
             "経路制御は、文書化されたポリシー(route-map)によって、実装されて"
             "いること。近隣単位の weight は、使用されていないこと。"),
            "すべてのネットワークへの到達性が、維持されていること。",
        ],
        "constraints": [
            "BGP セッションの削除、および、スタティック・ルートの追加は、"
            "許可されていません。",
            "対象外であるところのトラフィックの経路に、影響を与えるところの変更は、"
            "最小限に、とどめること。",
        ],
        "diff": 4 if len(faults) == 1 else 5,
    }
    return {"session": session, "af": af, "glob": glob, "fixes": fixes,
            "faults": [f"path_select:{f}" for f in faults], "checks": checks,
            "task": task,
            "meta": {"A": A, "B": Bx, "P": P, "S": S, "fwd_mech": fwd_mech}}


def shape_stale(b, a):
    rnd = b.rnd
    A, Bx, P, S = _pathsel_board(b, rnd)
    # 健全設計(lp 形)をフル実装した上に残骸を載せる
    session, af, glob = {}, {A: []}, {A: []}
    glob[A].extend(_lp_block(b, Bx))
    af[A].append(f"neighbor {b.ip(P, A)} route-map RM-LP-IN in")
    glob[A].extend(_prepend_block(b, A))
    af[A].append(f"neighbor {b.ip(S, A)} route-map RM-PREPEND-OUT out")
    harmful = rnd.choice(["weight", "lp_rm"])
    harmless = rnd.choice(["allowas_in", "as_override"])
    fixes, faults = [], [f"stale:{harmful}", f"stale:{harmless}"]
    if harmful == "weight":
        af.setdefault(A, []).append(f"neighbor {b.ip(S, A)} weight 40000")
        fixes.append({"node": A, "parents": af_parents(b, A),
                      "lines": [f"no neighbor {b.ip(S, A)} weight 40000"],
                      "match": "none"})
    else:  # lp_rm: 文書化されていない裏 route-map が設計を上書き
        glob.setdefault(A, []).extend([
            "route-map RM-OLD-POLICY permit 10",
            f" match ip address prefix-list PL-DIAG",
            " set local-preference 300",
            "route-map RM-OLD-POLICY permit 20", "!"])
        af.setdefault(A, []).append(
            f"neighbor {b.ip(S, A)} route-map RM-OLD-POLICY in")
        fixes.append({"node": A, "parents": af_parents(b, A),
                      "lines": [f"no neighbor {b.ip(S, A)} route-map RM-OLD-POLICY in"],
                      "match": "none"})
        fixes.append({"node": A, "lines": ["no route-map RM-OLD-POLICY"],
                      "match": "none"})
    # 無害残骸はランダムな他ルータの eBGP 近隣へ
    others = [r for r in ROUTERS if r != A]
    X = rnd.choice(others)
    peerX = rnd.choice([NEXT[X], PREV[X]])
    kw = "allowas-in" if harmless == "allowas_in" else "as-override"
    af.setdefault(X, []).append(f"neighbor {b.ip(peerX, X)} {kw}")
    fixes.append({"node": X, "parents": af_parents(b, X),
                  "lines": [f"no neighbor {b.ip(peerX, X)} {kw}"], "match": "none"})
    fixes.append({"node": A, "exec": ["clear ip bgp * in"]})
    fixes.append({"node": X, "exec": ["clear ip bgp * soft"]})
    checks = [
        {"name": f"{A}: {b.prefix(Bx)}/24 への転送が設計どおり主経路({P})を経由する",
         "node": A, "command": f"show ip route {b.prefix(Bx)}",
         "raw": [{"contains": b.ip(P, A)}, {"not_contains": b.ip(S, A)}],
         "points": 20},
        {"name": f"{Bx}: {b.prefix(A)}/24 への転送が設計どおり主経路({P})を経由する",
         "node": Bx, "command": f"show ip route {b.prefix(A)}",
         "raw": [{"contains": b.ip(P, Bx)}, {"not_contains": b.ip(S, Bx)}],
         "points": 15},
        {"name": f"{A}: 監査: 文書化されていない経路制御構成が存在しない",
         "node": A, "command": bgp_sec(b, A),
         "raw": [{"contains": f"router bgp {b.asn[A]}"},
                 {"not_regex": r"neighbor \S+ weight \d+"},
                 {"not_contains": "RM-OLD-POLICY"}], "points": 15},
        {"name": f"{X}: 監査: 近隣単位のAS例外オプションが存在しない",
         "node": X, "command": bgp_sec(b, X),
         "raw": [{"contains": f"router bgp {b.asn[X]}"},
                 {"not_contains": "allowas-in"},
                 {"not_contains": "as-override"}], "points": 15},
        {"name": f"{A}: 文書化された route-map が維持されている(絞りすぎ検出)",
         "node": A, "command": "show route-map RM-LP-IN",
         "raw": [{"contains": "local-preference 200"}], "points": 5},
    ]
    task = {
        "title": "構成監査の是正",
        "situation": (
            "定期の構成監査において、設計文書に記載されていないところの、"
            "経路制御に関する構成が、複数のデバイスにおいて、検出されました。"
            "これらは、過去の移行作業において使用され、その後、撤去されなかった"
            "ものである、と、考えられています。また、監視レポートにおいて、"
            f"{A} と {Bx} の間のトラフィックが、設計と異なるところの経路を、"
            "通過している、ということが、示されています。"),
        "requirements": [
            f"{A} と {Bx} の間のトラフィックは、双方向において、設計文書のとおり、"
            f"主契約の中継AS({P})を、経由すること。",
            "設計文書に記載されていないところの、経路制御に関する構成は、"
            "すべて、撤去されること。",
            "設計文書に記載されているところの構成(route-map **RM-LP-IN** / "
            "**RM-PREPEND-OUT** と、その適用)は、変更されてはなりません。",
            "すべてのネットワークへの到達性が、維持されていること。",
        ],
        "constraints": [
            "撤去の対象は、実際の転送に影響を与えているかどうかに、かかわらず、"
            "設計文書との差分の、すべてです。",
            "BGP セッションの削除、および、スタティック・ルートの追加は、"
            "許可されていません。",
        ],
        "diff": 4,
    }
    return {"session": session, "af": af, "glob": glob, "fixes": fixes,
            "faults": faults, "checks": checks, "task": task,
            "meta": {"A": A, "B": Bx, "P": P, "S": S,
                     "harmful": harmful, "harmless": harmless, "audit_node": X}}


def shape_ibgp_ring(b, a):
    rnd = b.rnd
    pool = ["mesh_missing", "network_missing", "ospf_lo_missing"]
    n = max(1, min(a.faults, 2))
    faults = rnd.sample(pool, n)
    session, af, glob = {}, {}, {}
    fixes = []
    suppress_nbr, suppress_net, suppress_ospf = set(), set(), set()
    meta = {}
    if "mesh_missing" in faults:
        X = rnd.choice(ROUTERS)
        Y = rnd.choice([r for r in ROUTERS if r != X])
        suppress_nbr = {(X, Y), (Y, X)}
        meta["mesh_missing"] = [X, Y]
        for me, peer in ((X, Y), (Y, X)):
            fixes.append({"node": me, "parents": [f"router bgp {b.asn[me]}"],
                          "lines": [
                              f"neighbor {b.lo0(peer)} remote-as {b.asn[peer]}",
                              f"neighbor {b.lo0(peer)} update-source Loopback0"],
                          "match": "none"})
            fixes.append({"node": me, "parents": af_parents(b, me),
                          "lines": [f"neighbor {b.lo0(peer)} activate"],
                          "match": "none"})
    if "network_missing" in faults:
        cands = [r for r in ROUTERS if r not in meta.get("mesh_missing", [])]
        Z = rnd.choice(cands)
        suppress_net = {Z}
        meta["network_missing"] = Z
        fixes.append({"node": Z, "parents": af_parents(b, Z),
                      "lines": [f"network {b.prefix(Z)} mask 255.255.255.0"],
                      "match": "none"})
    if "ospf_lo_missing" in faults:
        cands = [r for r in ROUTERS
                 if r not in meta.get("mesh_missing", [])
                 and r != meta.get("network_missing")]
        W = rnd.choice(cands)
        suppress_ospf = {W}
        meta["ospf_lo_missing"] = W
        fixes.append({"node": W, "parents": ["router ospf 1"],
                      "lines": [f"network {b.lo0(W)} 0.0.0.0 area 0"],
                      "match": "none"})
    meta["suppress"] = {"nbr": sorted(f"{x}-{y}" for (x, y) in suppress_nbr),
                       "net": sorted(suppress_net), "ospf": sorted(suppress_ospf)}
    checks = []
    for r in ROUTERS:
        conds = [{"contains": b.prefix(o)} for o in ROUTERS if o != r]
        checks.append({"name": f"{r}: 全拠点網が BGP テーブルに存在する",
                       "node": r, "command": "show ip bgp",
                       "raw": conds, "points": 12})
    checks.append({"name": "RT01: iBGP フルメッシュ3近隣が Established",
                   "node": "RT01", "command": "show ip bgp summary",
                   "raw": [{"regex": rf"(?m)^{b.lo0(o)}\s+4\s+{b.asn[o]}\s.*\s\d+\s*$"}
                           for o in ROUTERS if o != "RT01"], "points": 11})
    checks.append({"name": "RT03: iBGP フルメッシュ3近隣が Established",
                   "node": "RT03", "command": "show ip bgp summary",
                   "raw": [{"regex": rf"(?m)^{b.lo0(o)}\s+4\s+{b.asn[o]}\s.*\s\d+\s*$"}
                           for o in ROUTERS if o != "RT03"], "points": 11})
    # ★netmodel は next-hop→所有者の直マップで辿るため iBGP の Lo0 next-hop を
    #   解決できない(unknown_nh)。one_as は invariant を使わず実効 ping で採点する。
    for me, other in (("RT01", "RT03"), ("RT02", "RT04")):
        checks.append({"name": f"{me}: 対角拠点網への実効到達性(ping)",
                       "node": me,
                       "command": f"ping {b.lo1(other)} source Loopback1",
                       "raw": [{"contains": "Success rate is 100 percent"}],
                       "points": 15})
    task = {
        "title": "AS 内部の経路配布の回復",
        "situation": (
            "あなたの会社の 4 台のルータは、単一の AS に属しており、リング状の"
            "物理接続の上で、OSPF によって、内部の到達性が、提供されています。"
            "拠点のネットワークは、iBGP によって、配布されることが、意図されて"
            "います。現在、一部の拠点のネットワークへ、到達することができない、"
            "ということが、報告されています。なお、障害の報告に先立って、"
            "機器のリプレースに伴うところの、設定の restore 作業が、実施されて"
            "います。"),
        "requirements": [
            "すべてのルータが、すべての拠点のネットワーク"
            f"({', '.join('`%s/24`' % b.prefix(r) for r in ROUTERS)})を、"
            "BGP によって、学習していること。",
            "iBGP の設計(Loopback0 による、フル・メッシュのピアリング)が、"
            "維持されていること。ルート・リフレクタの導入は、承認されていません。",
            "IGP(OSPF)の設計が、維持されていること。",
        ],
        "constraints": [
            "拠点のネットワークを、OSPF に、含めることは、許可されていません。",
            "スタティック・ルート、および、再配送の追加は、許可されていません。",
        ],
        "diff": 4 if n == 1 else 5,
    }
    return {"session": session, "af": af, "glob": glob, "fixes": fixes,
            "faults": [f"ibgp_ring:{f}" for f in faults], "checks": checks,
            "task": task, "meta": meta, "no_invariants": True,
            "suppress": {"nbr": suppress_nbr, "net": suppress_net,
                         "ospf": suppress_ospf}}


SHAPE_FN = {"isp_exchange": shape_isp_exchange, "no_transit": shape_no_transit,
            "path_select": shape_path_select, "stale": shape_stale,
            "ibgp_ring": shape_ibgp_ring}


# ---------------------------------------------------------------- 囮
def make_decoys(rnd, k):
    decoys = []
    kinds = ["unused_route_map", "unused_prefix_list", "legacy_comment"]
    for _ in range(k):
        dt = rnd.choice(kinds); R = rnd.choice(ROUTERS)
        if dt == "unused_route_map":
            lines = ["route-map RM-MAINT-2019 deny 10", " set metric 100", "!"]
        elif dt == "unused_prefix_list":
            lines = [f"ip prefix-list PL-ARCHIVE seq 5 permit "
                     f"192.0.2.{rnd.randint(0, 255)}/32", "!"]
        else:
            lines = ["! NOTE: legacy policy retained for audit (2019 migration)"]
        decoys.append({"type": dt, "node": R, "lines": lines})
    return decoys


# ---------------------------------------------------------------- 出力
def build(a, rnd=None, quiet=False):
    rnd = rnd or random.Random(a.seed)
    shape = a.shape or rnd.choices(SHAPES, SHAPE_W)[0]
    b = Board(rnd, shape)
    r = SHAPE_FN[shape](b, a)
    decoys = make_decoys(rnd, a.decoys)
    for d in decoys:
        r["glob"].setdefault(d["node"], []).extend(d["lines"])

    # one_as の欠落系: base_config が生成する行を後段フィルタで抑止する
    sup = r.get("suppress", {"nbr": set(), "net": set(), "ospf": set()})
    cfgs = {}
    for R in ROUTERS:
        lines = base_config(b, R, r["session"], r["af"], r["glob"])
        out = []
        for ln in lines:
            drop = False
            for (x, y) in sup["nbr"]:
                if R == x and f"neighbor {b.lo0(y)} " in ln:
                    drop = True
            if R in sup["net"] and ln.strip() == \
                    f"network {b.prefix(R)} mask 255.255.255.0":
                drop = True
            if R in sup["ospf"] and ln.strip() == \
                    f"network {b.lo0(R)} 0.0.0.0 area 0":
                drop = True
            if not drop:
                out.append(ln)
        cfgs[R] = out

    checks = r["checks"]
    pts_checks = sum(c["points"] for c in checks)
    if r.get("no_invariants"):
        invariants = []
        assert pts_checks == 100, f"points!=100: checks={pts_checks} shape={shape}"
    else:
        inv_total = 100 - pts_checks
        reach_pts = max(0, inv_total - 10)
        invariants = [{"type": "reachability_all", "name": "全拠点網への到達性",
                       "points": reach_pts},
                      {"type": "loop_free", "name": "転送ループ不在", "points": 10}]
        assert pts_checks + reach_pts + 10 == 100, \
            f"points!=100: checks={pts_checks} shape={shape}"

    prob_id = f"GEN-BGPRING-{a.seed}"
    model = {"loopbacks": {x: b.lo1(x) for x in ROUTERS},
             "links": [{"a": p[0], "a_ip": f"{b.segs[p]}.1",
                        "b": p[1], "b_ip": f"{b.segs[p]}.2"} for p in LINKS]}
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "model": model,
               "invariants": invariants, "checks": checks}
    problem = {"id": prob_id,
               "title": f"BGP リング運用チケット (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["bgp", "policy", "troubleshooting", "generated"],
               "difficulty": r["task"]["diff"], "topology": "generated",
               "target_nodes": ROUTERS, "points": 100, "access": "ssh",
               "lab": {"links": [
                   {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "RT03", "b_if": 0},
                   {"a": "RT03", "a_if": 1, "b": "RT04", "b_if": 0},
                   {"a": "RT04", "a_if": 1, "b": "RT01", "b_if": 1}],
                   "positions": {"RT01": [-400, -300], "RT02": [400, -300],
                                 "RT03": [400, 100], "RT04": [-400, 100]}}}

    task_lines = [
        f"# 障害対応 {prob_id} : {r['task']['title']}（難易度{r['task']['diff']}）",
        "",
        "## 状況", "", r["task"]["situation"], "",
        "## トポロジ（物理）", "",
        "```",
        "  RT01 ──── RT02",
        "   │          │",
        "  RT04 ──── RT03",
        "```",
        "リンク一覧(接続・アドレス):", "```"]
    for p in LINKS:
        x, y = p
        task_lines.append(
            f"  {x}:E0/{SLOTS[x][y]}(.1) ── {y}:E0/{SLOTS[y][x]}(.2)"
            f"   {b.segs[p]}.0/30")
    task_lines += ["```", "",
                   "各ルータの Loopback1 が、拠点のネットワーク(/24)です。"
                   "論理構成(AS 番号・ピアリングの詳細)は、示されていません。"
                   "機器において、確認してください。", "",
                   "## 要件", ""]
    for i, req in enumerate(r["task"]["requirements"], 1):
        task_lines.append(f"{i}. {req}")
    task_lines += ["", "## 遵守事項", ""]
    for i, c in enumerate(r["task"]["constraints"], 1):
        task_lines.append(f"{i}. {c}")
    task_lines += [
        "", "## アクセス・採点", "",
        "SSH で各機にログイン（`SUZUKI / CCNP`・mgmt IP は出題時に提示）。", "",
        "```",
        f"ansible-playbook playbooks/grade.yml -e problem={prob_id} "
        "--vault-password-file <(printf 'CCNP\\n')",
        "```", ""]

    if quiet:
        return {"shape": shape, "board": b, "result": r, "checks": checks,
                "cfgs": cfgs}

    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_ring_ts.py) seed={a.seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for R in ROUTERS:
        with open(f"{pdir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(cfgs[R]) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_ring_ts.py) seed={a.seed}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write("\n".join(task_lines))
    json.dump({"shape": shape, "layout": b.layout, "faults": r["faults"],
               "meta": r["meta"],
               "values": {"asn": b.asn, "lo0": {x: b.lo0(x) for x in ROUTERS},
                          "prefix": {x: b.prefix(x) for x in ROUTERS},
                          "segs": {f"{p[0]}-{p[1]}": b.segs[p] for p in LINKS}}},
              open(f"{pdir}/solution/fault.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"fixes": r["fixes"]},
              open(f"{pdir}/solution/fix.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"decoys": decoys},
              open(f"{pdir}/solution/decoys.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/README.md", "w", encoding="utf-8") as f:
        f.write(f"# 採点者専用 ({prob_id})\n\n"
                f"- shape: **{shape}** / layout: {b.layout}\n"
                f"- faults: {r['faults']}\n- meta: {r['meta']}\n"
                f"- AS: {b.asn}\n- prefix: "
                f"{ {x: b.prefix(x) for x in ROUTERS} }\n"
                f"- 囮: {[(d['type'], d['node']) for d in decoys]}\n\n"
                "fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。\n")
    print(f"wrote {prob_id}: shape={shape} layout={b.layout} "
          f"faults={r['faults']} 難易度={r['task']['diff']}")
    return {"shape": shape, "board": b, "result": r, "checks": checks}


# ---------------------------------------------------------------- selftest
def selftest(a):
    """盤面の機械検証（実機なし）: 全shape×多seedで生成し整合性を確認する。"""
    import copy
    fails = 0
    for shape in SHAPES:
        for seed in range(1000, 1000 + a.selftest):
            for nf in (1, 2):
                aa = copy.copy(a)
                aa.seed, aa.shape, aa.faults = seed, shape, nf
                aa.variant, aa.solution = None, None
                rnd = random.Random(seed * 7 + nf)
                try:
                    out = build(aa, rnd=rnd, quiet=True)
                    r, b = out["result"], out["board"]
                    # 1) 採点は100点構成(buildでassert済) 2) fixノードは実在
                    for fx in r["fixes"]:
                        assert fx["node"] in ROUTERS
                    # 3) checksのnode実在・regexコンパイル可
                    import re
                    for c in out["checks"]:
                        assert c["node"] in ROUTERS
                        for cond in c["raw"]:
                            for kk, vv in cond.items():
                                if "regex" in kk:
                                    re.compile(vv)
                    # 4) 故障が最低1つ・fixが空でない
                    assert r["faults"] and r["fixes"]
                    # 4b) config構造: route-map/prefix-list等の外に孤児の
                    #     " match"/" set" 行が残っていない(ブロック崩れ検出)
                    for R, lines in out["cfgs"].items():
                        parent = ""
                        for ln in lines:
                            if not ln.startswith(" "):
                                parent = ln
                            elif ln.startswith((" match", " set")):
                                assert parent.startswith("route-map"), \
                                    f"{R}: orphan '{ln}' after '{parent}'"
                    # 5) split_company: 会社ASが2台で一致
                    if b.layout == "split_company":
                        cs = [x for x in ROUTERS
                              if b.asn[x] == b.asn[b.company[0]]]
                        assert sorted(cs) == sorted(b.company)
                except AssertionError as e:
                    fails += 1
                    print(f"FAIL shape={shape} seed={seed} faults={nf}: {e}")
    print(f"selftest: {'OK' if fails == 0 else f'{fails} FAILURES'} "
          f"({len(SHAPES)}shape×{a.selftest}seed×2)")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--shape", choices=SHAPES)
    ap.add_argument("--faults", type=int, default=1)
    ap.add_argument("--variant")           # isp_exchange 用
    ap.add_argument("--solution", choices=["aspath", "routemap"])  # no_transit 用
    ap.add_argument("--decoys", type=int, default=1)
    ap.add_argument("--selftest", type=int, default=0,
                    help="実機なし機械検証（shape毎のseed数）")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(1 if selftest(a) else 0)
    if a.seed is None:
        ap.error("--seed が必要です（--selftest 時を除く）")
    build(a)


if __name__ == "__main__":
    main()
