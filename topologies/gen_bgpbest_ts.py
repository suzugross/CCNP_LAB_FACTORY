#!/usr/bin/env python3
"""GEN-BGPBEST: BGP ベストパス運用基準 適合ラボ (BL-115・紙面 shape=bgpbest の両刀)。

トポロジ(6× IOL・SSH 採点・PoC=poc/bgpbest と同一の幾何):
      RT02(ISP-A #1) --- RT05(境界)     RT01= 視点(自社AS)
     /                    |             RT02/RT03= ISP-A(同一AS・2リンク+境界経由)
  RT01 --- RT03(ISP-A #2)-RT06(境界)    RT04= ISP-B
     \\                                  RT05/RT06= iBGP 境界(Loピア・OSPF)
      RT04(ISP-B)

運用基準(task.md に常設・build/TS 共通):
  R1 宛先 P の経路選択は、全事業者横並びの MED 合意に従う(→ acm)
  R2 戻り(own_prefix)の優先は、リンク別 MED= a1:10 / a2:200 / 境界:300 で表現
  R3 経路選択は決定的であること(→ compare-routerid)
  R4 境界経由の経路が、常に有効な候補であること(→ next-hop-self)
  R5 監査: 経路単位の weight / LOCAL_PREF の上書き禁止

TS モード(既定)= 健全基線から故障 1 種を注入(--fault 指定可):
  acm_missing / crid_missing / nh_no_self / weight_remote / lp_ebgp / med_swapped
  (前4種+lp_ebgp は紙面 shape=bgpbest と故障種名を共有。挙動は全て実測済=
   poc/bgpbest/README.md B13/B15/B16・poc/bgp-ring P4)
build モード(--mode build)= 自社側ポリシーを白紙にし要件書だけ渡す(採点は共通)。

使い方: gen_bgpbest_ts.py --repo . --seed <int> [--mode ts|build] [--fault <kind>]
"""
import argparse
import json
import os
import random

import yaml

ROUTERS = ["RT01", "RT02", "RT03", "RT04", "RT05", "RT06"]
OWN = ("RT01", "RT05", "RT06")
FAULTS = ["acm_missing", "crid_missing", "nh_no_self",
          "weight_remote", "lp_ebgp", "med_swapped"]

# (node, slot) ⇔ (node, slot)。mgmt_slot=3 は空ける(iol 規約)
LINKS = [("RT01", 0, "RT02", 0), ("RT01", 1, "RT03", 0),
         ("RT01", 2, "RT04", 0), ("RT01", 4, "RT05", 0),
         ("RT01", 5, "RT06", 0), ("RT05", 1, "RT02", 1),
         ("RT06", 1, "RT03", 1)]
SEG = {("RT01", "RT02"): 12, ("RT01", "RT03"): 13, ("RT01", "RT04"): 14,
       ("RT01", "RT05"): 15, ("RT01", "RT06"): 16,
       ("RT05", "RT02"): 25, ("RT06", "RT03"): 36}
PREFIX_POOL = ["198.51.100.0", "203.0.113.0", "192.0.2.0", "100.64.24.0"]
OWN_POOL = ["172.29.40.0", "172.31.208.0", "172.20.77.0"]


class Board:
    def __init__(self, rnd):
        self.o2 = rnd.randint(20, 99)
        self.as_own = rnd.choice([64900, 65010, 65020, 65050])
        self.as_a = rnd.choice([64520, 65201, 65310])
        self.as_b = rnd.choice([64611, 65402, 65520])
        self.p = rnd.choice(PREFIX_POOL)               # 宛先 P(ISP 側起源)
        picks = rnd.sample(PREFIX_POOL, 3)
        self.p = picks[0]
        self.p2 = picks[1]                             # タイ用 P2(ISP-A の2台起源)
        self.own = rnd.choice(OWN_POOL)                # 自社広告(戻り採点)
        # MED 値(P): ISP-B が最安= acm があるときだけ勝つ
        self.med_p = {"RT02": rnd.choice([50, 60]), "RT03": rnd.choice([120, 140]),
                      "RT04": rnd.choice([10, 20])}
        self.med_p2 = 100                              # P2 は同値=タイ
        self.med_ret = {"a1": 10, "a2": 200, "bk": 300}

    def lo0(self, r):
        k = int(r[2:])
        return f"{k}.{k}.{k}.{k}"

    def seg(self, x, y):
        return f"10.{self.o2}.{SEG[(x, y)]}"

    def ip(self, me, other):
        # 若番ノード=.1 / 対向=.2 ではなく、RT 番号を第4オクテットに使う
        return f"{self.seg(*self._pair(me, other))}.{int(me[2:])}"

    def _pair(self, x, y):
        return (x, y) if (x, y) in SEG else (y, x)

    def asn(self, r):
        if r in OWN:
            return self.as_own
        return self.as_b if r == "RT04" else self.as_a


# ---------------------------------------------------------------- config
def cfg_rt01(b, mode, fault):
    a1, a2, a4 = b.ip("RT02", "RT01"), b.ip("RT03", "RT01"), b.ip("RT04", "RT01")
    L = ["! RT01 (自社・視点)",
         "interface Loopback0",
         f" ip address {b.lo0('RT01')} 255.255.255.255", "!",
         "interface Loopback1",
         f" ip address {b.own.rsplit('.', 1)[0]}.1 255.255.255.0", "!"]
    for peer, slot in (("RT02", 0), ("RT03", 1), ("RT04", 2),
                       ("RT05", 4), ("RT06", 5)):
        L += [f"interface {{{{ links[{slot}] }}}}",
              f" ip address {b.ip('RT01', peer)} 255.255.255.0"]
        if peer == "RT05":
            L.append(" ip ospf cost 10")
        if peer == "RT06":
            L.append(" ip ospf cost 100")
        L += [" no shutdown", "!"]
    L += ["router ospf 1", f" router-id {b.lo0('RT01')}",
          f" network {b.seg('RT01', 'RT05')}.0 0.0.0.255 area 0",
          f" network {b.seg('RT01', 'RT06')}.0 0.0.0.255 area 0",
          f" network {b.lo0('RT01')} 0.0.0.0 area 0", "!"]
    B = [f"router bgp {b.as_own}", f" bgp router-id {b.lo0('RT01')}",
         " bgp log-neighbor-changes"]
    policy = mode != "build"
    if policy and fault != "acm_missing":
        B.append(" bgp always-compare-med")
    if policy and fault != "crid_missing":
        B.append(" bgp bestpath compare-routerid")
    B += [f" neighbor {b.lo0('RT05')} remote-as {b.as_own}",
          f" neighbor {b.lo0('RT05')} update-source Loopback0",
          f" neighbor {b.lo0('RT06')} remote-as {b.as_own}",
          f" neighbor {b.lo0('RT06')} update-source Loopback0",
          f" neighbor {a1} remote-as {b.as_a}",
          f" neighbor {a2} remote-as {b.as_a}",
          f" neighbor {a4} remote-as {b.as_b}",
          " address-family ipv4",
          f"  network {b.own} mask 255.255.255.0",
          f"  neighbor {b.lo0('RT05')} activate",
          f"  neighbor {b.lo0('RT06')} activate"]
    if policy:
        B += [f"  neighbor {b.lo0('RT05')} next-hop-self",
              f"  neighbor {b.lo0('RT06')} next-hop-self"]
    B += [f"  neighbor {a1} activate", f"  neighbor {a2} activate",
          f"  neighbor {a4} activate"]
    if policy:
        rm_a, rm_b = "RM-MED-A1", "RM-MED-A2"
        if fault == "med_swapped":
            rm_a, rm_b = rm_b, rm_a                     # 適用先を取り違え
        B += [f"  neighbor {a1} route-map {rm_a} out",
              f"  neighbor {a2} route-map {rm_b} out"]
    B += [" exit-address-family", "!"]
    L += B
    if policy:
        if fault == "lp_ebgp":
            # ★誤り: MED でなく LOCAL_PREF を out に set(送られない=B16)
            L += ["route-map RM-MED-A1 permit 10", " set local-preference 300",
                  "!",
                  "route-map RM-MED-A2 permit 10", " set local-preference 100",
                  "!"]
        else:
            L += ["route-map RM-MED-A1 permit 10",
                  f" set metric {b.med_ret['a1']}", "!",
                  "route-map RM-MED-A2 permit 10",
                  f" set metric {b.med_ret['a2']}", "!"]
    return L


def cfg_border(b, r, mode, fault):
    """RT05/RT06(自社境界)。"""
    isp = "RT02" if r == "RT05" else "RT03"
    up_slot = 0                                          # →RT01
    isp_slot = 1
    L = [f"! {r} (自社・境界)",
         "interface Loopback0",
         f" ip address {b.lo0(r)} 255.255.255.255", "!",
         f"interface {{{{ links[{up_slot}] }}}}",
         f" ip address {b.ip(r, 'RT01')} 255.255.255.0", " no shutdown", "!",
         f"interface {{{{ links[{isp_slot}] }}}}",
         f" ip address {b.ip(r, isp)} 255.255.255.0", " no shutdown", "!",
         "router ospf 1", f" router-id {b.lo0(r)}",
         f" network {b.seg('RT01', r)}.0 0.0.0.255 area 0",
         f" network {b.lo0(r)} 0.0.0.0 area 0", "!"]
    policy = mode != "build"
    B = [f"router bgp {b.as_own}", f" bgp router-id {b.lo0(r)}",
         " bgp log-neighbor-changes"]
    if policy:
        B += [" bgp always-compare-med", " bgp bestpath compare-routerid"]
    B += [f" neighbor {b.lo0('RT01')} remote-as {b.as_own}",
          f" neighbor {b.lo0('RT01')} update-source Loopback0",
          f" neighbor {b.ip(isp, r)} remote-as {b.as_a}",
          " address-family ipv4",
          f"  neighbor {b.lo0('RT01')} activate"]
    if policy and not (fault == "nh_no_self" and r == "RT05"):
        B.append(f"  neighbor {b.lo0('RT01')} next-hop-self")
    B.append(f"  neighbor {b.ip(isp, r)} activate")
    if policy:
        B.append(f"  neighbor {b.ip(isp, r)} route-map RM-MED-BK out")
        if fault == "weight_remote" and r == "RT05":
            # ★誤り: 「P を ISP-A 経由に固定したい」と境界に weight(伝播しない)
            B.append(f"  neighbor {b.ip(isp, r)} weight 40000")
    B += [" exit-address-family", "!"]
    L += B
    if policy:
        L += ["route-map RM-MED-BK permit 10",
              f" set metric {b.med_ret['bk']}", "!"]
    return L


def cfg_isp(b, r):
    """RT02/RT03/RT04(事業者側・出題対象外=固定完成品)。"""
    own_med = b.med_p[r]
    L = [f"! {r} (事業者側・変更禁止)",
         "interface Loopback0",
         f" ip address {b.lo0(r)} 255.255.255.255", "!",
         "interface Loopback100",
         f" ip address {b.p.rsplit('.', 1)[0]}.{int(r[2:])} 255.255.255.0", "!"]
    if r in ("RT02", "RT03"):
        L += ["interface Loopback101",
              f" ip address {b.p2.rsplit('.', 1)[0]}.{int(r[2:])} "
              "255.255.255.0", "!"]
    peers = [("RT01", 0)]
    if r == "RT02":
        peers.append(("RT05", 1))
    elif r == "RT03":
        peers.append(("RT06", 1))
    for peer, slot in peers:
        L += [f"interface {{{{ links[{slot}] }}}}",
              f" ip address {b.ip(r, peer)} 255.255.255.0", " no shutdown", "!"]
    B = [f"router bgp {b.asn(r)}", f" bgp router-id {b.lo0(r)}",
         " bgp log-neighbor-changes",
         " bgp bestpath compare-routerid"]
    for peer, _ in peers:
        B.append(f" neighbor {b.ip(peer, r)} remote-as {b.as_own}")
    B += [" address-family ipv4",
          f"  network {b.p} mask 255.255.255.0"]
    if r in ("RT02", "RT03"):
        B.append(f"  network {b.p2} mask 255.255.255.0")
    for peer, _ in peers:
        B += [f"  neighbor {b.ip(peer, r)} activate",
              f"  neighbor {b.ip(peer, r)} route-map RM-ISP-OUT out"]
    B += [" exit-address-family", "!"]
    L += B
    # P には合意 MED・P2 には同値 MED(タイ用)
    L += [f"ip prefix-list PL-P seq 5 permit {b.p}/24",
          f"ip prefix-list PL-P2 seq 5 permit {b.p2}/24",
          "route-map RM-ISP-OUT permit 10",
          " match ip address prefix-list PL-P",
          f" set metric {own_med}", "!",
          "route-map RM-ISP-OUT permit 20",
          " match ip address prefix-list PL-P2",
          f" set metric {b.med_p2}", "!",
          "route-map RM-ISP-OUT permit 30", "!"]
    return L


# ---------------------------------------------------------------- 採点
def make_checks(b):
    """採点(合計100)。best の判定は `show ip bgp <pfx> bestpath`(実測 B1 で
    確認済みのサブコマンド= best のブロックだけを出す)を使う。
    ★DOTALL の横断 regex(`nh .*?, best`)は別ブロックの best を拾い偽合格に
    なり得るため使わない。受信値の判定は「from 行→ Origin 行」の行ペアで縛る。"""
    a1 = b.ip("RT02", "RT01")
    a4 = b.ip("RT04", "RT01")
    p_ping = f"{b.p.rsplit('.', 1)[0]}.4"

    def frm(ip):
        return f"from {ip} ("

    def pair_rx(from_ip, med):
        return (r"(?m)from " + from_ip.replace(".", r"\.")
                + r" \(.*\)\n      Origin \w+, metric " + str(med) + r",")

    return [
        {"name": f"RT01: {b.p}/24 のベストが MED 合意(最安= ISP-B)に従う",
         "node": "RT01", "command": f"show ip bgp {b.p} bestpath",
         "raw": [{"contains": frm(a4)}], "points": 20},
        {"name": f"RT05: {b.p}/24 の転送が合意(RT01 経由)に従う",
         "node": "RT05", "command": f"show ip bgp {b.p} bestpath",
         "raw": [{"contains": frm(b.lo0("RT01"))}], "points": 10},
        {"name": f"RT02: 戻り({b.own}/24)が直結リンク優先"
                 f"(MED {b.med_ret['a1']})",
         "node": "RT02", "command": f"show ip bgp {b.own} bestpath",
         "raw": [{"contains": frm(b.ip("RT01", "RT02"))},
                 {"contains": f"metric {b.med_ret['a1']},"}], "points": 15},
        {"name": f"RT03: 戻り({b.own}/24)の合意値(MED {b.med_ret['a2']})を受信",
         "node": "RT03", "command": f"show ip bgp {b.own}",
         "raw": [{"regex": pair_rx(b.ip("RT01", "RT03"), b.med_ret["a2"])}],
         "points": 10},
        {"name": f"RT02: 境界経由の戻りが劣後(MED {b.med_ret['bk']})で"
                 "広告されている",
         "node": "RT02", "command": f"show ip bgp {b.own}",
         "raw": [{"regex": pair_rx(b.ip("RT05", "RT02"), b.med_ret["bk"])}],
         "points": 5},
        {"name": f"RT01: {b.p2}/24(全属性タイ)が決定的に選出される(RID 最小)",
         "node": "RT01", "command": f"show ip bgp {b.p2} bestpath",
         "raw": [{"contains": frm(a1)}], "points": 10},
        # ★境界が RT01 へ広告し返すのは「境界自身の eBGP が勝つ」P2 だけ
        #   (P は境界のベストが RT01 経由= iBGP 学習となり、スプリット
        #   ホライズンで RT01 へは出ない。初回実機検証 90001 で検出)。
        {"name": f"RT01: 境界(RT05)経由の {b.p2}/24 が有効な候補である",
         "node": "RT01", "command": f"show ip bgp {b.p2}",
         "raw": [{"contains": f"from {b.lo0('RT05')}"},
                 {"not_contains": "(inaccessible)"}], "points": 10},
        {"name": "監査: MED 合意と決定化のノブが存在する(RT01)",
         "node": "RT01", "command": "show run | section router bgp",
         "raw": [{"contains": "bgp always-compare-med"},
                 {"contains": "bgp bestpath compare-routerid"}], "points": 5},
        {"name": "監査: 経路単位の weight / LOCAL_PREF 上書きが存在しない(RT01)",
         "node": "RT01", "command": "show run | include weight|local-preference",
         "raw": [{"not_regex": r"neighbor \S+ weight \d+"},
                 {"not_regex": r"set local-preference"}], "points": 5},
        {"name": "監査: 経路単位の weight 上書きが存在しない(RT05)",
         "node": "RT05", "command": "show run | include weight",
         "raw": [{"not_regex": r"neighbor \S+ weight \d+"}], "points": 5},
        {"name": f"回帰: RT01 から {b.p}/24 への到達性",
         "node": "RT01",
         "command": f"ping {p_ping} source Loopback1 repeat 3",
         "raw": [{"regex": r"Success rate is [1-9][0-9]* percent"}],
         "points": 5},
    ]


def make_fix(b, fault):
    a1 = b.ip("RT02", "RT01")
    a2 = b.ip("RT03", "RT01")
    af = [f"router bgp {b.as_own}", "address-family ipv4"]
    if fault == "acm_missing":
        return [{"node": "RT01", "lines": ["bgp always-compare-med"],
                 "parents": [f"router bgp {b.as_own}"], "match": "none"}]
    if fault == "crid_missing":
        return [{"node": "RT01", "lines": ["bgp bestpath compare-routerid"],
                 "parents": [f"router bgp {b.as_own}"], "match": "none"}]
    if fault == "nh_no_self":
        return [{"node": "RT05", "parents": af,
                 "lines": [f"neighbor {b.lo0('RT01')} next-hop-self"],
                 "match": "none"},
                {"node": "RT05", "exec": ["clear ip bgp * soft out"]}]
    if fault == "weight_remote":
        isp = b.ip("RT02", "RT05")
        return [{"node": "RT05", "parents": af,
                 "lines": [f"no neighbor {isp} weight 40000"], "match": "none"},
                {"node": "RT05", "exec": ["clear ip bgp * soft in"]}]
    if fault == "lp_ebgp":
        # ★route-map ごとに parents を分ける。1 エントリに同一文字列
        #   (`no set local-preference`)を 2 回入れると ios_config が重複行を
        #   畳み、2 枚目の set local-preference が残る(実機検証 90005 で検出=
        #   fix 後 95 点・監査が正しく残骸を検出した)。
        return [{"node": "RT01", "parents": ["route-map RM-MED-A1 permit 10"],
                 "lines": ["no set local-preference",
                           f"set metric {b.med_ret['a1']}"], "match": "none"},
                {"node": "RT01", "parents": ["route-map RM-MED-A2 permit 10"],
                 "lines": ["no set local-preference",
                           f"set metric {b.med_ret['a2']}"], "match": "none"},
                {"node": "RT01", "exec": ["clear ip bgp * soft out"]}]
    if fault == "med_swapped":
        return [{"node": "RT01", "parents": af,
                 "lines": [f"neighbor {a1} route-map RM-MED-A1 out",
                           f"neighbor {a2} route-map RM-MED-A2 out"],
                 "match": "none"},
                {"node": "RT01", "exec": ["clear ip bgp * soft out"]}]
    raise KeyError(fault)


def make_solve(b):
    """build モードの模範解答(健全ポリシー一式)。"""
    a1, a2 = b.ip("RT02", "RT01"), b.ip("RT03", "RT01")
    fixes = [{"node": "RT01",
              "lines": ["route-map RM-MED-A1 permit 10",
                        f" set metric {b.med_ret['a1']}",
                        "route-map RM-MED-A2 permit 10",
                        f" set metric {b.med_ret['a2']}"], "match": "none"},
             {"node": "RT01", "parents": [f"router bgp {b.as_own}"],
              "lines": ["bgp always-compare-med",
                        "bgp bestpath compare-routerid"], "match": "none"},
             {"node": "RT01", "parents": [f"router bgp {b.as_own}",
                                          "address-family ipv4"],
              "lines": [f"neighbor {b.lo0('RT05')} next-hop-self",
                        f"neighbor {b.lo0('RT06')} next-hop-self",
                        f"neighbor {a1} route-map RM-MED-A1 out",
                        f"neighbor {a2} route-map RM-MED-A2 out"],
              "match": "none"}]
    for r in ("RT05", "RT06"):
        isp = "RT02" if r == "RT05" else "RT03"
        fixes += [{"node": r,
                   "lines": ["route-map RM-MED-BK permit 10",
                             f" set metric {b.med_ret['bk']}"],
                   "match": "none"},
                  {"node": r, "parents": [f"router bgp {b.as_own}"],
                   "lines": ["bgp always-compare-med",
                             "bgp bestpath compare-routerid"], "match": "none"},
                  {"node": r, "parents": [f"router bgp {b.as_own}",
                                          "address-family ipv4"],
                   "lines": [f"neighbor {b.lo0('RT01')} next-hop-self",
                             f"neighbor {b.ip(isp, r)} route-map RM-MED-BK out"],
                   "match": "none"}]
    fixes.append({"node": "RT01", "exec": ["clear ip bgp * soft"]})
    fixes.append({"node": "RT05", "exec": ["clear ip bgp * soft"]})
    fixes.append({"node": "RT06", "exec": ["clear ip bgp * soft"]})
    return fixes


# ---------------------------------------------------------------- task.md
TICKETS = {
    "acm_missing": "宛先ネットワークへの転送が、事業者との費用合意と異なる回線へ、"
                   "出ている、という指摘を、経理部門から、受けています。",
    "crid_missing": "機器の再起動や、セッションの断のたびに、一部の宛先の経路が、"
                    "入れ替わる、という報告が、あります。構成は、変更されていません。",
    "nh_no_self": "主回線の障害を想定した机上の検証において、境界ルーター経由の"
                  "経路が、切り替わりの候補に、なっていない、ということが、"
                  "判明しています。",
    "weight_remote": "特定の宛先の転送を、優先の事業者へ固定する作業が、昨日、"
                     "実施されました。しかしながら、一部のルータにおいて、"
                     "転送が、合意と異なる回線へ、出ています。",
    "lp_ebgp": "戻りのトラフィックの優先を、事業者と合意した値で、広告する作業が、"
               "実施されました。しかしながら、事業者から、合意された値が、"
               "広告に現れていない、という指摘を、受けています。",
    "med_swapped": "事業者から、2 本のリンクの優先値が、合意と逆に広告されている、"
                   "という指摘を、受けています。",
}


def task_md(b, prob_id, mode, fault):
    L = [f"# {'構築' if mode == 'build' else '障害対応'} {prob_id} : "
         f"BGP 経路選択の運用基準(難易度4)", "",
         "## 状況", ""]
    if mode == "build":
        L.append("自社(AS {})は、2 つの事業者に、マルチホーム接続されています。"
                 "BGP セッションと経路交換は、確立済みですが、経路選択の"
                 "ポリシーは、未投入です。下記の運用基準を、満たしてください。"
                 .format(b.as_own))
    else:
        L.append(TICKETS[fault])
        L.append("")
        L.append("自社のルータは RT01(コア)・RT05・RT06(境界)です。"
                 "下記の運用基準が、合意されています。基準からの逸脱を特定し、"
                 "是正してください。")
    L += ["", "## トポロジ", "", "```",
          f"      RT02({b.as_a}) ---- RT05",
          "     /                    |",
          f"  RT01 --- RT03({b.as_a})-+--RT06",
          "     \\          (RT06はRT03へ)",
          f"      RT04({b.as_b})",
          "```", "",
          f"- 宛先 {b.p}/24 は、各事業者が、広告しています。",
          f"- 宛先 {b.p2}/24 は、AS {b.as_a} の 2 台が、広告しています。",
          f"- 自社は {b.own}/24 (RT01 Loopback1) を、広告しています。",
          f"- RT01-RT05 / RT01-RT06 は、OSPF(プロセス 1・エリア 0)です。",
          "", "## 運用基準", "",
          f"1. 宛先 {b.p}/24 の経路選択は、**全事業者を横並びにした MED の"
          "合意**に、従うこと(値が最小の事業者を、使用する)。",
          f"2. 戻りのトラフィック({b.own}/24 の広告)の優先は、リンク別の MED で、"
          f"表現すること= RT02 直結リンク: **{b.med_ret['a1']}** / RT03 直結"
          f"リンク: **{b.med_ret['a2']}** / 境界経由: **{b.med_ret['bk']}**。",
          "3. 経路選択は、**決定的**であること(受信の順序や、セッションの断続に、"
          "依存しないこと)。",
          "4. 境界ルーター経由の経路が、**常に有効な候補**であること。",
          "5. 監査: 経路単位の weight、および、LOCAL_PREF の上書きは、"
          "使用しないこと。",
          "", "## 遵守事項", "",
          "1. 事業者側のルータ(RT02 / RT03 / RT04)の設定は、変更してはならない。",
          "2. BGP セッションの削除、および、スタティック・ルートの追加は、"
          "許可されていない。",
          "3. 設定変更の反映に、`clear ip bgp * soft` の実行は、許可されている。",
          "", "## アクセス・採点", "",
          "SSH で各機にログイン(`SUZUKI / CCNP`・mgmt IP は出題時に提示)。", "",
          "```",
          f"ansible-playbook playbooks/grade.yml -e problem={prob_id} "
          "--vault-password-file <(printf 'CCNP\\n')",
          "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- 出力
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--mode", choices=["ts", "build"], default="ts")
    ap.add_argument("--fault", choices=FAULTS, default=None)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    b = Board(rnd)
    fault = None
    if a.mode == "ts":
        fault = a.fault or rnd.choice(FAULTS)

    cfgs = {"RT01": cfg_rt01(b, a.mode, fault),
            "RT05": cfg_border(b, "RT05", a.mode, fault),
            "RT06": cfg_border(b, "RT06", a.mode, fault),
            "RT02": cfg_isp(b, "RT02"), "RT03": cfg_isp(b, "RT03"),
            "RT04": cfg_isp(b, "RT04")}
    checks = make_checks(b)
    assert sum(c["points"] for c in checks) == 100

    prob_id = f"GEN-BGPBEST-{a.seed}"
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"},
               "invariants": [], "checks": checks}
    problem = {"id": prob_id,
               "title": f"BGP 経路選択の運用基準 (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["bgp", "path-selection", "best-path", "generated"],
               "difficulty": 4, "topology": "generated",
               "target_nodes": ROUTERS, "points": 100, "access": "ssh",
               "lab": {"links": [{"a": x, "a_if": xs, "b": y, "b_if": ys}
                                 for x, xs, y, ys in LINKS],
                       "positions": {"RT01": [0, 0], "RT02": [-350, -220],
                                     "RT03": [-350, 220], "RT04": [0, 350],
                                     "RT05": [350, -220], "RT06": [350, 220]}}}

    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgpbest_ts.py) seed={a.seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for r in ROUTERS:
        with open(f"{pdir}/initial/{r}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(cfgs[r]) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgpbest_ts.py) seed={a.seed}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task_md(b, prob_id, a.mode, fault))
    fixes = make_solve(b) if a.mode == "build" else make_fix(b, fault)
    json.dump({"fixes": fixes},
              open(f"{pdir}/solution/fix.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"mode": a.mode, "fault": fault,
               "values": {"as_own": b.as_own, "as_a": b.as_a, "as_b": b.as_b,
                          "p": b.p, "p2": b.p2, "own": b.own, "o2": b.o2,
                          "med_p": b.med_p}},
              open(f"{pdir}/solution/fault.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/README.md", "w", encoding="utf-8") as f:
        f.write(f"# 採点者専用 ({prob_id})\n\n"
                f"- mode: **{a.mode}** / fault: **{fault}**\n"
                f"- AS: 自社={b.as_own} ISP-A={b.as_a} ISP-B={b.as_b}\n"
                f"- P={b.p}/24(MED {b.med_p}) P2={b.p2}/24(タイ) "
                f"own={b.own}/24(戻り {b.med_ret})\n"
                f"- 紙面 shape=bgpbest と故障種名を共有(BL-115)。"
                f"実測根拠= poc/bgpbest/README.md\n"
                f"- ★crid_missing の broken 時、P2 の nh チェックは oldest 依存で"
                f"揺れる(監査 5 点は決定的に落ちる)\n"
                f"- fix は solution/fix.json(fix_generated.yml で投入)\n")
    print(f"wrote {prob_id}: mode={a.mode} fault={fault} "
          f"P={b.p} P2={b.p2} own={b.own}")


if __name__ == "__main__":
    main()
