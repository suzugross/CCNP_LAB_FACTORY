#!/usr/bin/env python3
"""gen_mpls_ts.py — MPLS L3VPN 12台・トラブルシュート生成器。

ベース = ENARSI-MPLS-L3VPN-01/02 で実機検証済みの基礎技術のみ:
  OSPF(コア) / LDP / iBGP VPNv4 フルメッシュ(3PE) / VRF(RD/RT) /
  PE-CE OSPF(VRF別プロセス) / route-map+prefix-list 広告制御 / adjust-mss。
規模と故障の組合せで難度を作る(新規技術ゼロ)。

トポロジ(12台・全ノード次数<=3・IOL):
  PE1(RT01)-P1(RT04) / PE2(RT02)-P2(RT05) / PE3(RT03)-P3(RT06)
  Pコアは三角リング P1-P2-P3 (冗長。LSP穴あき故障 = IGP正常でVPNだけ死ぬ、が作れる)
  各PEに CUST_A / CUST_B の CE を1台ずつ収容:
    A1=RT07 B1=RT08 (PE1) / A2=RT09 B2=RT10 (PE2) / A3=RT11 B3=RT12 (PE3)
  CUST_A / CUST_B は同一 172.16.<site>.0/24 を重複使用 (A=.1 / B=.9)
  CE は Lo9 に機器管理 10.99.x.1/32 (VPNへ広告禁止 = route-map で遮断が設計仕様)

CLI:
  gen_mpls_ts.py --repo . --seed N [--faults {0,1,2,3}] [--decoys {0,1,2}]
    faults=0 はベースライン(故障なし。トポロジ/採点の実機検証用)
出力: problems/GEN-MPLSTS-<seed>/
  problem.yml / initial/*.cfg.j2 / task.md / grading.yml /
  solution/{fault.json, fix.json, solution.md, catalog.json}
  catalog.json = 全故障の breaks/fixes (実機での全故障サイクル検証用)

採点(100点・RD非依存の効果ベース):
  E2E 6ペア48 + 顧客間分離3 + 管理/32漏えい不在6 + CEのOSPF学習4 +
  LDP 9 + コアOSPF 6 + VPNv4セッション9 + PE-CE隣接6 + LSPラベル3 +
  P BGPフリー3 + static禁止3
教訓の適用: IOL day0 は IP無しIF の no shutdown 無効(全IF に IP を焼く) /
  VPNv4ネイバーは Genie 不可 → vpnv4 summary raw / RD は decoy になり得るため
  採点で RD 値を断言しない / vrf forwarding 復旧 fix は「vrf行→IP行」を別エントリに
  分割(ios_config は既存一致行を送らないため)。
"""
import argparse
import json
import os
import random

import yaml

AS = 65000
PES = ["RT01", "RT02", "RT03"]
PS = ["RT04", "RT05", "RT06"]
CES = ["RT07", "RT08", "RT09", "RT10", "RT11", "RT12"]
NODES = PES + PS + CES

# CE: (customer, site, 収容PE)
CEMAP = {"RT07": ("A", 1, "RT01"), "RT08": ("B", 1, "RT01"),
         "RT09": ("A", 2, "RT02"), "RT10": ("B", 2, "RT02"),
         "RT11": ("A", 3, "RT03"), "RT12": ("B", 3, "RT03")}
PE_OF_SITE = {1: "RT01", 2: "RT02", 3: "RT03"}
CUST = {"A": {"vrf": "CUST_A", "rd": f"{AS}:100", "rt": f"{AS}:100",
              "host": 1, "proc": 10},
        "B": {"vrf": "CUST_B", "rd": f"{AS}:200", "rt": f"{AS}:200",
              "host": 9, "proc": 20}}

# (a, b, kind)  kind: core=PEアップリンク / ring=Pリング / ce=PE-CE
LINKS = [
    ("RT01", "RT04", "core"), ("RT02", "RT05", "core"), ("RT03", "RT06", "core"),
    ("RT04", "RT05", "ring"), ("RT05", "RT06", "ring"), ("RT04", "RT06", "ring"),
    ("RT01", "RT07", "ce"), ("RT01", "RT08", "ce"),
    ("RT02", "RT09", "ce"), ("RT02", "RT10", "ce"),
    ("RT03", "RT11", "ce"), ("RT03", "RT12", "ce"),
]

# PEペアの IGP 最適経路が通る Pリンク (等コスト: PEx-Px-Py-PEy が唯一最短)
RING_OF_PAIR = {("RT01", "RT02"): ("RT04", "RT05"),
                ("RT02", "RT03"): ("RT05", "RT06"),
                ("RT01", "RT03"): ("RT04", "RT06")}

POSITIONS = {
    "RT07": [-650, -330], "RT08": [-650, -70], "RT01": [-430, -200],
    "RT04": [-180, -200], "RT05": [60, -340], "RT06": [60, -60],
    "RT02": [300, -340], "RT09": [520, -420], "RT10": [520, -260],
    "RT03": [300, -60], "RT11": [520, -140], "RT12": [520, 20],
}


# ----------------------------------------------------------------------------
# モデル構築
# ----------------------------------------------------------------------------
def build_model(seed, n_faults, n_decoys):
    rnd = random.Random(seed)
    m = {"seed": seed, "lo": {}, "lo9": {}, "links": [], "faults": [],
         "decoys": []}

    # コアノード Lo0 (x.x.x.x/32) と Lo9 (IGP外ローカル管理 10.255.x.1/32)
    used = set()
    for i, n in enumerate(PES + PS):
        while True:
            x = rnd.randint(1, 99)
            if x != 10 and x not in used:
                used.add(x)
                m["lo"][n] = f"{x}.{x}.{x}.{x}"
                break
        m["lo9"][n] = f"10.255.{i + 1}.1"

    # CE の OSPF router-id は固定 (7.7.7.7 .. 12.12.12.12) = 採点regexの安定化
    for n in CES:
        i = int(n[2:])
        m["lo"][n] = f"{i}.{i}.{i}.{i}"

    # リンク採番: core/ring=10.x.y.0/30, ce=192.168.k.0/30
    segs, ks = set(), set()
    slot_count = {n: 0 for n in NODES}
    for a, b, kind in LINKS:
        while True:
            if kind == "ce":
                k = rnd.randint(1, 254)
                if k in ks:
                    continue
                ks.add(k)
                net = f"192.168.{k}.0"
                break
            x, y = rnd.randint(0, 254), rnd.randint(0, 254)
            if (x, y) in segs or x == 255:
                continue
            segs.add((x, y))
            net = f"10.{x}.{y}.0"
            break
        base = net.rsplit(".", 1)[0]
        # ce リンクは CE=.1 / PE=.2 (01/02 と同じ向き)。core/ring は a=.1 / b=.2
        if kind == "ce":
            a_ip, b_ip = f"{base}.2", f"{base}.1"     # a=PE=.2, b=CE=.1
        else:
            a_ip, b_ip = f"{base}.1", f"{base}.2"
        m["links"].append({"a": a, "b": b, "kind": kind, "net": net,
                           "a_ip": a_ip, "b_ip": b_ip,
                           "a_if": slot_count[a], "b_if": slot_count[b]})
        slot_count[a] += 1
        slot_count[b] += 1
    assert all(v <= 3 for v in slot_count.values())

    # 顧客 LAN: site 1..3 に一意な第3オクテット (両顧客で同一 = 重複prefix)
    lan_octets = rnd.sample(range(1, 255), 3)
    m["lan"] = {s: lan_octets[s - 1] for s in (1, 2, 3)}
    # CE 機器管理 /32: 10.99.<u>.1
    us = rnd.sample(range(1, 255), 6)
    m["mgmt"] = {n: f"10.99.{us[i]}.1" for i, n in enumerate(CES)}

    inject(m, rnd, n_faults, n_decoys)
    return m


def link_of(m, a, b):
    for lk in m["links"]:
        if {lk["a"], lk["b"]} == {a, b}:
            return lk
    raise KeyError((a, b))


def side(lk, n):
    """(slot, ip) of node n on link lk."""
    return (lk["a_if"], lk["a_ip"]) if lk["a"] == n else (lk["b_if"], lk["b_ip"])


def ifname(slot):
    return f"Ethernet{slot // 4}/{slot % 4}"


def ce_of(cust, site):
    return next(n for n, (c, s, _pe) in CEMAP.items()
                if c == cust and s == site)


def lan_ip(m, cust, site):
    return f"172.16.{m['lan'][site]}.{CUST[cust]['host']}"


def lan_net(m, site):
    return f"172.16.{m['lan'][site]}.0"


# ----------------------------------------------------------------------------
# 故障カタログ。各故障: id/layer/desc/params + breaks(注入) + fixes(復旧)。
# breaks/fixes は fix_generated.yml 互換 ({node,parents?,lines} | {node,exec})。
# render 側は m["faults"] を見て initial に故障を焼き込む。
# ----------------------------------------------------------------------------
def _cfg(node, lines, parents=None):
    d = {"node": node, "lines": lines}
    if parents:
        d["parents"] = parents
    return d


def _clear_bgp(node):
    return {"node": node, "exec": ["clear ip bgp * soft"]}


def catalog(m, rnd):
    """全故障をこの seed のモデルに合わせて実体化して返す (選択は inject 側)。"""
    lo = m["lo"]
    faults = []

    def add(fid, layer, desc, params, breaks, fixes, symptom):
        faults.append({"id": fid, "layer": layer, "desc": desc,
                       "params": params, "breaks": breaks, "fixes": fixes,
                       "symptom": symptom})

    # ---- L1: コア IGP -------------------------------------------------------
    pe = rnd.choice(PES)
    site = next(s for s, p in PE_OF_SITE.items() if p == pe)
    uplk = next(lk for lk in m["links"]
                if lk["kind"] == "core" and pe in (lk["a"], lk["b"]))
    add("l1_pe_uplink_area", "L1",
        f"{pe} のコアアップリンクの OSPF が area 1 で設定 (正: area 0。隣接不成立)",
        {"victim": pe, "net": uplk["net"]},
        [_cfg(pe, [f"no network {uplk['net']} 0.0.0.3 area 0",
                   f"network {uplk['net']} 0.0.0.3 area 1"], ["router ospf 1"])],
        [_cfg(pe, [f"no network {uplk['net']} 0.0.0.3 area 1",
                   f"network {uplk['net']} 0.0.0.3 area 0"], ["router ospf 1"])],
        f"site{site} が両顧客とも全断 (コア隣接ダウン警報あり)")

    rlk = rnd.choice([lk for lk in m["links"] if lk["kind"] == "ring"])
    rvic = rnd.choice([rlk["a"], rlk["b"]])
    add("l1_ring_ospf_missing", "L1",
        f"{rvic} のリングIF({rlk['net']}/30)が OSPF に入っていない (冗長で救済され"
        "ユーザ影響なし = 片肺運転)",
        {"victim": rvic, "net": rlk["net"]},
        [_cfg(rvic, [f"no network {rlk['net']} 0.0.0.3 area 0"],
              ["router ospf 1"])],
        [_cfg(rvic, [f"network {rlk['net']} 0.0.0.3 area 0"],
              ["router ospf 1"])],
        f"監視: {rlk['a']}-{rlk['b']} 間の OSPF 隣接ダウン警報 (ユーザ影響の報告なし)")

    # ---- L2: LDP ------------------------------------------------------------
    (px, py), (pex, pey) = rnd.choice(
        [(("RT04", "RT05"), ("RT01", "RT02")),
         (("RT05", "RT06"), ("RT02", "RT03")),
         (("RT04", "RT06"), ("RT01", "RT03"))])
    rl = link_of(m, px, py)
    lvic = rnd.choice([px, py])
    lslot, _ = side(rl, lvic)
    sx = next(s for s, p in PE_OF_SITE.items() if p == pex)
    sy = next(s for s, p in PE_OF_SITE.items() if p == pey)
    add("l2_ldp_missing_ring", "L2",
        f"{lvic} の {ifname(lslot)}({px}-{py} リング) に mpls ip が無い"
        f" (IGP最適経路上の LSP 穴 → {pex}-{pey} 間の VPN のみブラックホール。"
        "IGP/ping は正常)",
        {"victim": lvic, "if": ifname(lslot)},
        [_cfg(lvic, ["no mpls ip"], [f"interface {ifname(lslot)}"])],
        [_cfg(lvic, ["mpls ip"], [f"interface {ifname(lslot)}"])],
        f"両顧客とも site{sx}↔site{sy} のみ不通 (他ペア正常・コア警報なし)")

    pv = rnd.choice(PS)
    pv_site = {"RT04": 1, "RT05": 2, "RT06": 3}[pv]
    add("l2_ldp_rid_unadvertised", "L2",
        f"{pv} の LDP router-id が IGP 外の Loopback9({m['lo9'][pv]}) を指す"
        " (トランスポートアドレス解決不能 → 全LDPセッション断。IGP は正常)",
        {"victim": pv},
        [_cfg(pv, ["mpls ldp router-id Loopback9 force"]),
         {"node": pv, "exec": ["clear mpls ldp neighbor *"]}],
        [_cfg(pv, ["mpls ldp router-id Loopback0 force"]),
         {"node": pv, "exec": ["clear mpls ldp neighbor *"]}],
        f"site{pv_site} 収容 PE 経由の VPN が全断 (PE 間 ping は正常)")

    # ---- L3: MP-BGP ---------------------------------------------------------
    bx, by = rnd.sample(PES, 2)
    by_up = next(lk for lk in m["links"]
                 if lk["kind"] == "core" and by in (lk["a"], lk["b"]))
    _slot, by_phys = side(by_up, by)
    bsx = next(s for s, p in PE_OF_SITE.items() if p == bx)
    bsy = next(s for s, p in PE_OF_SITE.items() if p == by)
    add("l3_wrong_neighbor_ip", "L3",
        f"{bx} の iBGP ピアが {by} の Loopback でなく物理IP({by_phys}) を指す"
        " (双方向とも不一致でセッション不成立)",
        {"victim": bx, "peer": by},
        [_cfg(bx, [f"no neighbor {lo[by]}",
                   f"neighbor {by_phys} remote-as {AS}"],
              [f"router bgp {AS}"]),
         _cfg(bx, [f"neighbor {by_phys} activate"],
              [f"router bgp {AS}", "address-family vpnv4"]),
         _clear_bgp(bx)],
        [_cfg(bx, [f"no neighbor {by_phys}",
                   f"neighbor {lo[by]} remote-as {AS}",
                   f"neighbor {lo[by]} update-source Loopback0"],
              [f"router bgp {AS}"]),
         _cfg(bx, [f"neighbor {lo[by]} activate"],
              [f"router bgp {AS}", "address-family vpnv4"]),
         _clear_bgp(bx)],
        f"両顧客とも site{bsx}↔site{bsy} のみ不通 (コア警報なし)")

    ax, ay = rnd.sample(PES, 2)
    asx = next(s for s, p in PE_OF_SITE.items() if p == ax)
    asy = next(s for s, p in PE_OF_SITE.items() if p == ay)
    add("l3_vpnv4_activate_missing", "L3",
        f"{ax} で {ay} が address-family vpnv4 で activate されていない",
        {"victim": ax, "peer": ay},
        [_cfg(ax, [f"no neighbor {lo[ay]} activate"],
              [f"router bgp {AS}", "address-family vpnv4"]),
         _clear_bgp(ax)],
        [_cfg(ax, [f"neighbor {lo[ay]} activate"],
              [f"router bgp {AS}", "address-family vpnv4"]),
         _clear_bgp(ax)],
        f"両顧客とも site{asx}↔site{asy} のみ不通")

    # ---- L4: VRF / RT -------------------------------------------------------
    rpe = rnd.choice(PES)
    rcust = rnd.choice(["A", "B"])
    rsite = next(s for s, p in PE_OF_SITE.items() if p == rpe)
    c = CUST[rcust]
    wrong_rt = f"{AS}:{c['rt'].split(':')[1]}1"     # 65000:1001 / 65000:2001
    add("l4_rt_export_wrong", "L4",
        f"{rpe} の VRF {c['vrf']} の route-target export が {wrong_rt}"
        f" (正: {c['rt']}。この site の経路がどの PE にも import されない)",
        {"victim": rpe, "cust": rcust},
        [_cfg(rpe, [f"no route-target export {c['rt']}",
                    f"route-target export {wrong_rt}"],
              [f"vrf definition {c['vrf']}", "address-family ipv4"]),
         _clear_bgp(rpe)],
        [_cfg(rpe, [f"no route-target export {wrong_rt}",
                    f"route-target export {c['rt']}"],
              [f"vrf definition {c['vrf']}", "address-family ipv4"]),
         _clear_bgp(rpe)],
        f"CUST_{rcust} の site{rsite} だけ孤立 (他顧客は正常)")

    ipe = rnd.choice(PES)
    icust = rnd.choice(["A", "B"])
    isite = next(s for s, p in PE_OF_SITE.items() if p == ipe)
    ic = CUST[icust]
    wrong_irt = f"{AS}:{ic['rt'].split(':')[1]}9"
    add("l4_rt_import_wrong", "L4",
        f"{ipe} の VRF {ic['vrf']} の route-target import が {wrong_irt}"
        f" (正: {ic['rt']}。この PE の VRF が対向経路を取り込めない)",
        {"victim": ipe, "cust": icust},
        [_cfg(ipe, [f"no route-target import {ic['rt']}",
                    f"route-target import {wrong_irt}"],
              [f"vrf definition {ic['vrf']}", "address-family ipv4"]),
         _clear_bgp(ipe)],
        [_cfg(ipe, [f"no route-target import {wrong_irt}",
                    f"route-target import {ic['rt']}"],
              [f"vrf definition {ic['vrf']}", "address-family ipv4"]),
         _clear_bgp(ipe)],
        f"CUST_{icust} の site{isite} から対向サイトへ出られない (他顧客は正常)")

    vpe = rnd.choice(PES)
    vcust = rnd.choice(["A", "B"])
    vsite = next(s for s, p in PE_OF_SITE.items() if p == vpe)
    vce = ce_of(vcust, vsite)
    vlk = link_of(m, vpe, vce)
    vslot, vip = side(vlk, vpe)
    other_vrf = CUST["B" if vcust == "A" else "A"]["vrf"]
    right_vrf = CUST[vcust]["vrf"]
    # ★fix は「vrf行」「IP行」を別エントリに分割 (vrf forwarding で IP が消えるが、
    #   ios_config は同一バッチを変更前 running と比較するため IP 行がスキップされる)
    add("l4_wrong_vrf_membership", "L4",
        f"{vpe} の {vce} 向けIF({ifname(vslot)}) が誤って VRF {other_vrf} に収容"
        f" (正: {right_vrf}。PE-CE OSPF 隣接不成立)",
        {"victim": vpe, "cust": vcust, "if": ifname(vslot)},
        [_cfg(vpe, [f"vrf forwarding {other_vrf}"],
              [f"interface {ifname(vslot)}"]),
         _cfg(vpe, [f"ip address {vip} 255.255.255.252"],
              [f"interface {ifname(vslot)}"])],
        [_cfg(vpe, [f"vrf forwarding {right_vrf}"],
              [f"interface {ifname(vslot)}"]),
         _cfg(vpe, [f"ip address {vip} 255.255.255.252"],
              [f"interface {ifname(vslot)}"])],
        f"CUST_{vcust} の site{vsite} が全断 (PE-CE の IGP 隣接ダウン)")

    # ---- L5: PE-CE 再配布 / 広告制御 ---------------------------------------
    dpe = rnd.choice(PES)
    dcust = rnd.choice(["A", "B"])
    dsite = next(s for s, p in PE_OF_SITE.items() if p == dpe)
    dproc = CUST[dcust]["proc"]
    # ★parents は "router ospf N vrf X" まで一致させる (N だけだと VRF 無しの
    #   グローバルプロセスが新規作成される)
    dvrf = CUST[dcust]["vrf"]
    add("l5_redist_bgp_missing", "L5",
        f"{dpe} の OSPF {dproc}(VRF {dvrf}) に"
        f" redistribute bgp が無い (対向経路が CE に届かない)",
        {"victim": dpe, "cust": dcust},
        [_cfg(dpe, [f"no redistribute bgp {AS}"],
              [f"router ospf {dproc} vrf {dvrf}"])],
        [_cfg(dpe, [f"redistribute bgp {AS} subnets"],
              [f"router ospf {dproc} vrf {dvrf}"])],
        f"CUST_{dcust} site{dsite} の CE に対向サイトの経路が無い (隣接は FULL)")

    spe = rnd.choice(PES)
    scust = rnd.choice(["A", "B"])
    ssite = next(s for s, p in PE_OF_SITE.items() if p == spe)
    sproc = CUST[scust]["proc"]
    add("l5_subnets_missing", "L5",
        f"{spe} の OSPF {sproc} の redistribute bgp {AS} に subnets が無い"
        " (クラスフル境界のみ再配布 = /24 が CE に落ちない)",
        {"victim": spe, "cust": scust},
        [_cfg(spe, [f"no redistribute bgp {AS}",
                    f"redistribute bgp {AS}"],
              [f"router ospf {sproc} vrf {CUST[scust]['vrf']}"])],
        [_cfg(spe, [f"redistribute bgp {AS} subnets"],
              [f"router ospf {sproc} vrf {CUST[scust]['vrf']}"])],
        f"CUST_{scust} site{ssite} で対向 /24 だけが CE に無い (隣接 FULL・設定は一見ある)")

    tpe = rnd.choice(PES)
    tsite = next(s for s, p in PE_OF_SITE.items() if p == tpe)
    add("l5_routemap_strict", "L5",
        f"{tpe} の prefix-list PL-CUST-LAN が le 23 (LAN /24 が VPNv4 に出ない)",
        {"victim": tpe},
        [_cfg(tpe, ["no ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 24",
                    "ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 23"]),
         _clear_bgp(tpe)],
        [_cfg(tpe, ["no ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 23",
                    "ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 24"]),
         _clear_bgp(tpe)],
        f"両顧客とも site{tsite} の LAN が対向から見えない (IGP/LDP/BGP 全て正常)")

    kpe = rnd.choice(PES)
    ksite = next(s for s, p in PE_OF_SITE.items() if p == kpe)
    add("l5_routemap_leak", "L5",
        f"{kpe} の PL-CUST-LAN に seq 10 permit 10.99.0.0/16 le 32 が混入"
        " (機器管理 /32 が VPN をまたいで漏えい)",
        {"victim": kpe},
        [_cfg(kpe, ["ip prefix-list PL-CUST-LAN seq 10 permit 10.99.0.0/16 le 32"]),
         _clear_bgp(kpe)],
        [_cfg(kpe, ["no ip prefix-list PL-CUST-LAN seq 10 permit 10.99.0.0/16 le 32"]),
         _clear_bgp(kpe)],
        f"監査指摘: site{ksite} 収容 CE の管理アドレスが対向サイトから見える (疎通は全て正常)")

    ape = rnd.choice(PES)
    acust = rnd.choice(["A", "B"])
    asite2 = next(s for s, p in PE_OF_SITE.items() if p == ape)
    aproc = CUST[acust]["proc"]
    alk = link_of(m, ape, ce_of(acust, asite2))
    add("l5_pece_area_mismatch", "L5",
        f"{ape} の OSPF {aproc} の PE-CE 収容が area 1 (正: area 0。隣接不成立)",
        {"victim": ape, "cust": acust},
        [_cfg(ape, [f"no network {alk['net']} 0.0.0.3 area 0",
                    f"network {alk['net']} 0.0.0.3 area 1"],
              [f"router ospf {aproc} vrf {CUST[acust]['vrf']}"])],
        [_cfg(ape, [f"no network {alk['net']} 0.0.0.3 area 1",
                    f"network {alk['net']} 0.0.0.3 area 0"],
              [f"router ospf {aproc} vrf {CUST[acust]['vrf']}"])],
        f"CUST_{acust} の site{asite2} が全断 (PE-CE の IGP 隣接ダウン)")

    return faults


DECOYS = [
    # (id, 説明生成, breaks, fixes=無し(無害))  ※採点は RD 値/経路パスを断言しない
    "decoy_rd_nonstandard",   # ある PE の VRF の RD が非標準値 (RD は一意化のみ=無害)
    "decoy_ring_cost",        # ある P のリング IF に ip ospf cost 100 (迂回するだけ=無害)
]


def make_decoy(m, rnd, did):
    if did == "decoy_rd_nonstandard":
        pe = rnd.choice(PES)
        cust = rnd.choice(["A", "B"])
        c = CUST[cust]
        odd_rd = f"{AS}:9{c['rd'].split(':')[1]}"
        return {"id": did, "node": pe,
                "desc": f"{pe} の VRF {c['vrf']} の RD が {odd_rd} (正規値 {c['rd']} と"
                        "不揃い。だが RD は一意化の札であって所属判断に関与しない=無害)",
                "params": {"cust": cust, "rd": odd_rd}}
    pv = rnd.choice(PS)
    rl = rnd.choice([lk for lk in m["links"]
                     if lk["kind"] == "ring" and pv in (lk["a"], lk["b"])])
    slot, _ = side(rl, pv)
    return {"id": did, "node": pv,
            "desc": f"{pv} の {ifname(slot)} に ip ospf cost 100 (最適経路が迂回する"
                    "だけで LDP は全リンクにあり無害)",
            "params": {"if": ifname(slot)},
            "breaks": [_cfg(pv, ["ip ospf cost 100"],
                            [f"interface {ifname(slot)}"])],
            }


def inject(m, rnd, n_faults, n_decoys):
    cat = catalog(m, rnd)
    if n_faults:
        layers = rnd.sample(["L1", "L2", "L3", "L4", "L5"], n_faults)
        for lay in layers:
            m["faults"].append(rnd.choice([f for f in cat if f["layer"] == lay]))
    m["decoys"] = [make_decoy(m, rnd, d)
                   for d in rnd.sample(DECOYS, min(n_decoys, len(DECOYS)))]
    m["catalog"] = cat


def fault(m, fid):
    return next((f for f in m["faults"] if f["id"] == fid), None)


def decoy(m, did):
    return next((d for d in m["decoys"] if d["id"] == did), None)


# ----------------------------------------------------------------------------
# レンダリング (initial/*.cfg.j2)。故障/decoy をここで焼き込む。
# ----------------------------------------------------------------------------
def node_links(m, n):
    return [(lk, *side(lk, n)) for lk in m["links"] if n in (lk["a"], lk["b"])]


def render_core_common(m, n, L):
    """Lo0/Lo9 とコア/リング IF (mpls ip 付き)。"""
    L.append("interface Loopback0")
    L.append(f" ip address {m['lo'][n]} 255.255.255.255")
    L.append("!")
    L.append("interface Loopback9")
    L.append(" description === local mgmt (IGP/LDP 対象外) ===")
    L.append(f" ip address {m['lo9'][n]} 255.255.255.255")
    L.append("!")
    f_ldp = fault(m, "l2_ldp_missing_ring")
    d_cost = decoy(m, "decoy_ring_cost")
    for lk, slot, ip in node_links(m, n):
        if lk["kind"] == "ce":
            continue
        peer = lk["b"] if lk["a"] == n else lk["a"]
        L.append(f"interface {{{{ links[{slot}] }}}}")
        L.append(f" description === to {peer} ({lk['net']}/30) ===")
        L.append(f" ip address {ip} 255.255.255.252")
        if not (f_ldp and f_ldp["params"]["victim"] == n
                and f_ldp["params"]["if"] == ifname(slot)):
            L.append(" mpls ip")
        if d_cost and d_cost["node"] == n and d_cost["params"]["if"] == ifname(slot):
            L.append(" ip ospf cost 100")
        L.append(" no shutdown")
        L.append("!")


def render_ospf1(m, n, L):
    f_area = fault(m, "l1_pe_uplink_area")
    f_ring = fault(m, "l1_ring_ospf_missing")
    L.append("router ospf 1")
    L.append(f" router-id {m['lo'][n]}")
    L.append(f" network {m['lo'][n]} 0.0.0.0 area 0")
    for lk, _slot, _ip in node_links(m, n):
        if lk["kind"] == "ce":
            continue
        if f_area and f_area["params"]["victim"] == n \
                and f_area["params"]["net"] == lk["net"]:
            L.append(f" network {lk['net']} 0.0.0.3 area 1")
            continue
        if f_ring and f_ring["params"]["victim"] == n \
                and f_ring["params"]["net"] == lk["net"]:
            continue
        L.append(f" network {lk['net']} 0.0.0.3 area 0")
    L.append("!")


def render_pe(m, n):
    L = [f"! GEN-MPLSTS-{m['seed']} 初期状態 ({n} = PE / 変更対象)"]
    lo = m["lo"]
    site = next(s for s, p in PE_OF_SITE.items() if p == n)
    f_rte = fault(m, "l4_rt_export_wrong")
    f_rti = fault(m, "l4_rt_import_wrong")
    f_vrf = fault(m, "l4_wrong_vrf_membership")
    f_red = fault(m, "l5_redist_bgp_missing")
    f_sub = fault(m, "l5_subnets_missing")
    f_str = fault(m, "l5_routemap_strict")
    f_lek = fault(m, "l5_routemap_leak")
    f_pce = fault(m, "l5_pece_area_mismatch")
    f_nbr = fault(m, "l3_wrong_neighbor_ip")
    f_act = fault(m, "l3_vpnv4_activate_missing")
    d_rd = decoy(m, "decoy_rd_nonstandard")

    # VRF 定義
    for cu in ("A", "B"):
        c = CUST[cu]
        rd = c["rd"]
        if d_rd and d_rd["node"] == n and d_rd["params"]["cust"] == cu:
            rd = d_rd["params"]["rd"]
        exp, imp = c["rt"], c["rt"]
        if f_rte and f_rte["params"]["victim"] == n and f_rte["params"]["cust"] == cu:
            exp = f"{AS}:{c['rt'].split(':')[1]}1"
        if f_rti and f_rti["params"]["victim"] == n and f_rti["params"]["cust"] == cu:
            imp = f"{AS}:{c['rt'].split(':')[1]}9"
        L += [f"vrf definition {c['vrf']}", f" rd {rd}", " address-family ipv4",
              f"  route-target export {exp}", f"  route-target import {imp}",
              " exit-address-family", "!"]

    render_core_common(m, n, L)

    # CE 向け IF (VRF 収容 + MSS)
    for cu in ("A", "B"):
        c = CUST[cu]
        ce = ce_of(cu, site)
        lk = link_of(m, n, ce)
        slot, ip = side(lk, n)
        vrf = c["vrf"]
        if f_vrf and f_vrf["params"]["victim"] == n and f_vrf["params"]["cust"] == cu:
            vrf = CUST["B" if cu == "A" else "A"]["vrf"]
        L += [f"interface {{{{ links[{slot}] }}}}",
              f" description === to {ce} CUST_{cu}-CE (site{site}, {lk['net']}/30) ===",
              f" vrf forwarding {vrf}",
              f" ip address {ip} 255.255.255.252",
              " ip tcp adjust-mss 1452",
              " no shutdown", "!"]

    L.append("mpls ldp router-id Loopback0 force")
    L.append("!")
    render_ospf1(m, n, L)

    # PE-CE OSPF (VRF 別プロセス)
    for cu in ("A", "B"):
        c = CUST[cu]
        ce = ce_of(cu, site)
        lk = link_of(m, n, ce)
        L.append(f"router ospf {c['proc']} vrf {c['vrf']}")
        L.append(f" router-id {lo[n]}")
        if f_red and f_red["params"]["victim"] == n and f_red["params"]["cust"] == cu:
            pass
        elif f_sub and f_sub["params"]["victim"] == n and f_sub["params"]["cust"] == cu:
            L.append(f" redistribute bgp {AS}")
        else:
            L.append(f" redistribute bgp {AS} subnets")
        area = "0"
        if f_pce and f_pce["params"]["victim"] == n and f_pce["params"]["cust"] == cu:
            area = "1"
        L.append(f" network {lk['net']} 0.0.0.3 area {area}")
        L.append("!")

    # 広告制御
    le = "23" if (f_str and f_str["params"]["victim"] == n) else "24"
    L.append(f"ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le {le}")
    if f_lek and f_lek["params"]["victim"] == n:
        L.append("ip prefix-list PL-CUST-LAN seq 10 permit 10.99.0.0/16 le 32")
    L += ["route-map RM-OSPF2VPN permit 10",
          " match ip address prefix-list PL-CUST-LAN", "!"]

    # BGP
    peers = [p for p in PES if p != n]
    L.append(f"router bgp {AS}")
    L.append(f" bgp router-id {lo[n]}")
    L.append(" no bgp default ipv4-unicast")
    for p in peers:
        if f_nbr and f_nbr["params"]["victim"] == n and f_nbr["params"]["peer"] == p:
            up = next(lk for lk in m["links"]
                      if lk["kind"] == "core" and p in (lk["a"], lk["b"]))
            _s, phys = side(up, p)
            L.append(f" neighbor {phys} remote-as {AS}")
        else:
            L.append(f" neighbor {lo[p]} remote-as {AS}")
            L.append(f" neighbor {lo[p]} update-source Loopback0")
    L.append(" address-family vpnv4")
    for p in peers:
        if f_nbr and f_nbr["params"]["victim"] == n and f_nbr["params"]["peer"] == p:
            up = next(lk for lk in m["links"]
                      if lk["kind"] == "core" and p in (lk["a"], lk["b"]))
            _s, phys = side(up, p)
            L.append(f"  neighbor {phys} activate")
        elif f_act and f_act["params"]["victim"] == n and f_act["params"]["peer"] == p:
            continue
        else:
            L.append(f"  neighbor {lo[p]} activate")
    L.append(" exit-address-family")
    for cu in ("A", "B"):
        c = CUST[cu]
        L += [f" address-family ipv4 vrf {c['vrf']}",
              f"  redistribute ospf {c['proc']} route-map RM-OSPF2VPN",
              " exit-address-family"]
    L.append("!")
    return "\n".join(L) + "\n"


def render_p(m, n):
    L = [f"! GEN-MPLSTS-{m['seed']} 初期状態 ({n} = P / 変更対象)"]
    render_core_common(m, n, L)
    f_rid = fault(m, "l2_ldp_rid_unadvertised")
    if f_rid and f_rid["params"]["victim"] == n:
        L.append("mpls ldp router-id Loopback9 force")
    else:
        L.append("mpls ldp router-id Loopback0 force")
    L.append("!")
    render_ospf1(m, n, L)
    return "\n".join(L) + "\n"


def render_ce(m, n):
    cu, site, pe = CEMAP[n]
    c = CUST[cu]
    lk = link_of(m, pe, n)
    slot, ip = side(lk, n)
    L = [f"! GEN-MPLSTS-{m['seed']} 初期状態 ({n} = CUST_{cu} site{site} CE / 変更不可)",
         "interface Loopback0",
         f" description === CUST_{cu} site{site} LAN ({lan_net(m, site)}/24) ===",
         f" ip address {lan_ip(m, cu, site)} 255.255.255.0",
         " ip ospf network point-to-point",
         "!",
         "interface Loopback9",
         " description === CE 機器管理 (VPN へ広告禁止) ===",
         f" ip address {m['mgmt'][n]} 255.255.255.255",
         "!",
         f"interface {{{{ links[{slot}] }}}}",
         f" description === to {pe} PE (site{site}, {lk['net']}/30) ===",
         f" ip address {ip} 255.255.255.252",
         " no shutdown",
         "!",
         "router ospf 1",
         f" router-id {m['lo'][n]}",
         f" network {lk['net']} 0.0.0.3 area 0",
         f" network {lan_net(m, site)} 0.0.0.255 area 0",
         f" network {m['mgmt'][n]} 0.0.0.0 area 0",
         "!"]
    return "\n".join(L) + "\n"


def render_node(m, n):
    if n in PES:
        return render_pe(m, n)
    if n in PS:
        return render_p(m, n)
    return render_ce(m, n)


# ----------------------------------------------------------------------------
# 採点 (100点・RD 非依存)
# ----------------------------------------------------------------------------
def _esc(ip):
    return ip.replace(".", r"\.")


def write_grading(m, pdir, pid):
    lo = m["lo"]
    g = {"problem": pid, "total_points": 100,
         "defaults": {"genie_os": "iosxe"}, "checks": []}
    ck = g["checks"]

    def add(name, node, command, points, raw):
        ck.append({"name": name, "node": node, "command": command,
                   "points": points, "raw": raw})

    # E2E 6ペア (各8点=48)
    for cu in ("A", "B"):
        for s1, s2 in ((1, 2), (1, 3), (2, 3)):
            src_ce = ce_of(cu, s1)
            add(f"{src_ce}(CUST_{cu} site{s1}): E2E {lan_ip(m, cu, s1)} → "
                f"site{s2} {lan_ip(m, cu, s2)}",
                src_ce,
                f"ping {lan_ip(m, cu, s2)} source {lan_ip(m, cu, s1)} repeat 5",
                8, [{"regex": "Success rate is [1-9]"}])

    # 顧客間分離 (3)
    add(f"{ce_of('A', 1)}(CUST_A site1): CUST_B のホスト {lan_ip(m, 'B', 2)} へは"
        "到達できない (顧客間分離)",
        ce_of("A", 1),
        f"ping {lan_ip(m, 'B', 2)} source {lan_ip(m, 'A', 1)} repeat 2",
        3, [{"regex": "Success rate is 0"}])

    # 管理 /32 が VPN をまたがない (6 CE × 1 = 6)。確認先 = 収容 PE 以外の PE
    for ce in CES:
        cu, site, pe = CEMAP[ce]
        rpe = next(p for p in PES if p != pe)
        add(f"{rpe}: VRF {CUST[cu]['vrf']} に {ce} の管理 {m['mgmt'][ce]}/32 が"
            "漏れていない",
            rpe,
            f"show ip route vrf {CUST[cu]['vrf']} {m['mgmt'][ce]} 255.255.255.255",
            1, [{"regex": "not in table"}])

    # CE が対向 LAN を OSPF で学習 (2×2=4)
    add(f"{ce_of('A', 1)}: 対向 site2 LAN {lan_net(m, 2)}/24 を OSPF で学習",
        ce_of("A", 1), f"show ip route {lan_net(m, 2)}",
        2, [{"regex": 'Known via "ospf 1"'}])
    add(f"{ce_of('B', 3)}: 対向 site1 LAN {lan_net(m, 1)}/24 を OSPF で学習",
        ce_of("B", 3), f"show ip route {lan_net(m, 1)}",
        2, [{"regex": 'Known via "ospf 1"'}])

    # LDP: PE⇔P (3×2=6) + Pリング相互 (3×1=3)
    pe_p = {"RT01": "RT04", "RT02": "RT05", "RT03": "RT06"}
    for pe, p in pe_p.items():
        add(f"{pe}: {p} との LDP セッションが Oper", pe,
            "show mpls ldp neighbor", 2,
            [{"regex": f"Peer LDP Ident: {_esc(lo[p])}:0"},
             {"regex": "State: Oper"}])
    for a, b in (("RT04", "RT05"), ("RT05", "RT06"), ("RT06", "RT04")):
        add(f"{a}: {b} との LDP ピアが存在", a, "show mpls ldp neighbor", 1,
            [{"regex": f"Peer LDP Ident: {_esc(lo[b])}:0"}])

    # コア OSPF FULL: PE-P (3×1) + リング (3×1)
    for pe, p in pe_p.items():
        add(f"{p}: OSPF 隣接 {pe}({lo[pe]}) が FULL", p, "show ip ospf neighbor",
            1, [{"regex": rf"{_esc(lo[pe])}\s+\d+\s+FULL"}])
    for a, b in (("RT04", "RT05"), ("RT05", "RT06"), ("RT06", "RT04")):
        add(f"{a}: OSPF 隣接 {b}({lo[b]}) が FULL", a, "show ip ospf neighbor",
            1, [{"regex": rf"{_esc(lo[b])}\s+\d+\s+FULL"}])

    # VPNv4 セッション (3セッション×3=9)。State/PfxRcd が数値 = Established
    for x, y in (("RT01", "RT02"), ("RT01", "RT03"), ("RT02", "RT03")):
        add(f"{x}: {y}({lo[y]}) との iBGP VPNv4 セッションが Established", x,
            "show bgp vpnv4 unicast all summary", 3,
            [{"regex": rf"{_esc(lo[y])}\s+4\s+{AS}(\s+\d+){{5}}\s+\S+\s+\d+"}])

    # PE-CE OSPF FULL (6×1=6)
    for ce in CES:
        cu, site, pe = CEMAP[ce]
        add(f"{pe}: VRF {CUST[cu]['vrf']} で {ce}({lo[ce]}) と OSPF 隣接 FULL",
            pe, "show ip ospf neighbor", 1,
            [{"regex": rf"{_esc(lo[ce])}\s+\d+\s+FULL"}])

    # LSP ラベル実在 (3)
    add(f"RT01: PE 間転送がラベルスイッチされている (→{lo['RT02']})", "RT01",
        f"traceroute {lo['RT02']} source {lo['RT01']} numeric timeout 1",
        3, [{"regex": "MPLS: Label"}])

    # 制約 (P BGPフリー 3×1 + static禁止 3×1)
    for p in PS:
        add(f"{p}(P): BGP を持たない", p,
            "show running-config | section router bgp", 1,
            [{"not_contains": "router bgp"}])
    for pe in PES:
        add(f"{pe}: 顧客 VRF にスタティックを使っていない", pe,
            "show running-config | include ip route vrf CUST", 1,
            [{"not_contains": "ip route vrf CUST"}])

    total = sum(c["points"] for c in ck)
    assert total == 100, f"points={total}"
    with open(os.path.join(pdir, "grading.yml"), "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_mpls_ts.py) seed={m['seed']}\n")
        yaml.safe_dump(g, f, allow_unicode=True, sort_keys=False, width=200)


# ----------------------------------------------------------------------------
# task.md / solution
# ----------------------------------------------------------------------------
def write_task(m, pdir, pid, n_faults):
    lan = m["lan"]
    rows = []
    for ce in CES:
        cu, site, pe = CEMAP[ce]
        lk = link_of(m, pe, ce)
        rows.append(f"| {ce} | CUST_{cu} site{site} | {pe} | {lk['net']}/30"
                    f" (CE=.1/PE=.2) | {lan_ip(m, cu, site)}/24 | {m['mgmt'][ce]}/32 |")
    core_rows = []
    for lk in m["links"]:
        if lk["kind"] != "ce":
            core_rows.append(f"| {lk['a']}–{lk['b']} | {lk['net']}/30"
                             f" ({lk['a']}=.1 / {lk['b']}=.2) |")
    lo_rows = [f"| {n} | {m['lo'][n]}/32 |" for n in PES + PS]

    if n_faults:
        symptoms = "\n".join(f"> - {f['symptom']}" for f in m["faults"])
        ticket = (f"## 障害チケット\n\n"
                  f"NOC に以下の申告・警報が届いている。**原因を特定し、下記の設計仕様"
                  f"どおりに復旧せよ。**\n\n{symptoms}\n\n"
                  "> 注: 複数の事象が同時に起きている可能性がある。下位レイヤの故障が"
                  "上位の症状を隠すことがあるため、切り分けは必ず下の層から。\n")
    else:
        ticket = ("## ベースライン\n\n故障は注入されていない（トポロジ/採点の検証用）。\n")

    body = f"""# 問題 {pid} : MPLS L3VPN 障害対応 12台（自動生成・難易度5）

## シナリオ
SP コア（PE×3 / P×3 三角リング）で顧客 2 社（CUST_A / CUST_B）へ L3VPN を提供中。
両顧客は**同一のプライベート帯 172.16.0.0/16 を重複使用**している。
CE は顧客管理機器（**変更禁止**）。あなたはコア側（PE/P）だけを操作できる。

{ticket}
```
 A-CE            +--------- SPコア ---------+            A-CE
 RT07 --\\        |         RT05(P2)         |        /-- RT09
         RT01(PE1)--RT04(P1)  |  \\           RT02(PE2)
 RT08 --/        |     |  \\  |   RT06(P3)---RT03(PE3)   \\-- RT10
 B-CE            |     +---\\-+--/    |      |            B-CE
                 +------------------ | -----+
                              RT11 --+-- RT12
                              (A-CE)     (B-CE)   ※正確な配線は下表参照
```

## 設計仕様（本来あるべき姿）
1. **コア IGP**: OSPF 1 / area 0（コアリンクと Lo0 のみ。Lo9 は IGP 対象外）。
2. **MPLS**: 全コアリンクで LDP。LDP ルータ ID = Loopback0 (force)。
3. **MP-BGP**: AS {AS}。PE 3台の Loopback0 間 **iBGP フルメッシュ**、VPNv4 AF のみ
   （AF 方式）。**P(RT04-06) は BGP を持たない**。
4. **VRF**（全 PE 共通）: CUST_A = RD {CUST["A"]["rd"]} / RT {CUST["A"]["rt"]}、
   CUST_B = RD {CUST["B"]["rd"]} / RT {CUST["B"]["rt"]}。
5. **PE-CE**: OSPF（PE 側プロセス CUST_A={CUST["A"]["proc"]} / CUST_B={CUST["B"]["proc"]},
   area 0, router-id=Lo0）。OSPF⇄BGP を相互再配布。
6. **広告制御**: VPNv4 へ出すのは 172.16.0.0/16 の LAN(/24) のみ
   （prefix-list PL-CUST-LAN + route-map RM-OSPF2VPN）。**機器管理 10.99.0.0/16 は
   VPN をまたいで広告しない**。
7. **MSS**: PE の CE 向け IF は ip tcp adjust-mss 1452。
8. スタティックルート禁止。CE（RT07-12）変更禁止。MGMT VRF / Ethernet0/3 に触れない。

## アドレス（この seed の値）
### コア Loopback0
| ノード | Lo0 |
|--------|-----|
{chr(10).join(lo_rows)}

### コアリンク
| リンク | セグメント |
|--------|-----------|
{chr(10).join(core_rows)}

### CE / 顧客
| CE | 顧客/サイト | 収容PE | PE-CE リンク | サイト LAN (Lo0) | 機器管理 (Lo9) |
|----|------------|--------|--------------|------------------|----------------|
{chr(10).join(rows)}

## 到達目標
- 各顧客の全サイトペア（site1↔2↔3）が E2E で疎通し、顧客間は分離。
- 機器管理 /32 は収容 PE まで（VPN をまたがない）。
- コア転送はラベルスイッチング。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem={pid} \\
  --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(os.path.join(pdir, "task.md"), "w", encoding="utf-8") as f:
        f.write(body)


def write_solution_md(m, pdir, pid):
    parts = [f"# 解答 : {pid}（自動生成）\n"]
    if not m["faults"]:
        parts.append("ベースライン（故障なし）。\n")
    for i, fa in enumerate(m["faults"], 1):
        fixes = "\n".join(
            f"  {fx.get('parents', ['(global)'])} -> {fx.get('lines', fx.get('exec'))}"
            for fx in fa["fixes"])
        parts.append(f"## 故障{i}: {fa['id']} ({fa['layer']})\n\n{fa['desc']}\n\n"
                     f"症状: {fa['symptom']}\n\n修正:\n```\n{fixes}\n```\n")
    if m["decoys"]:
        parts.append("## おとり（無害・修正不要）\n")
        for d in m["decoys"]:
            parts.append(f"- **{d['id']}** ({d['node']}): {d['desc']}\n")
    parts.append("\n復旧は `ansible-playbook playbooks/fix_generated.yml "
                 f"-e problem={pid}` でも投入可（自己検品用）。\n")
    with open(os.path.join(pdir, "solution", "solution.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(parts))


def emit(m, repo, n_faults):
    pid = f"GEN-MPLSTS-{m['seed']}"
    pdir = os.path.join(repo, "problems", pid)
    os.makedirs(os.path.join(pdir, "initial"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "solution"), exist_ok=True)

    prob = {
        "id": pid,
        "title": f"MPLS L3VPN 障害対応 12台 (3PE×Pリング×2顧客3サイト, "
                 f"faults={n_faults}, seed={m['seed']})",
        "exam": "ENARSI",
        "topics": ["mpls", "ldp", "l3vpn", "vpnv4", "mp-bgp", "vrf",
                   "route-target", "ospf", "pe-ce", "redistribution",
                   "troubleshooting", "generated"],
        "difficulty": 5,
        "topology": "generated",
        "image_family": "iol",
        "target_nodes": NODES,
        "points": 100,
        "access": "ssh",
        "lab": {"positions": POSITIONS,
                "links": [{"a": lk["a"], "a_if": lk["a_if"],
                           "b": lk["b"], "b_if": lk["b_if"]}
                          for lk in m["links"]]},
    }
    with open(os.path.join(pdir, "problem.yml"), "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_mpls_ts.py) seed={m['seed']} faults={n_faults}\n")
        yaml.safe_dump(prob, f, allow_unicode=True, sort_keys=False)

    for n in NODES:
        with open(os.path.join(pdir, "initial", f"{n}.cfg.j2"), "w",
                  encoding="utf-8") as f:
            f.write(render_node(m, n))

    write_grading(m, pdir, pid)
    write_task(m, pdir, pid, n_faults)
    write_solution_md(m, pdir, pid)

    with open(os.path.join(pdir, "solution", "fault.json"), "w",
              encoding="utf-8") as f:
        json.dump({"faults": [{k: v for k, v in fa.items()
                               if k not in ("breaks", "fixes")}
                              for fa in m["faults"]],
                   "decoys": [{"id": d["id"], "node": d["node"],
                               "desc": d["desc"]} for d in m["decoys"]]},
                  f, ensure_ascii=False, indent=1)
    fixes = []
    for fa in m["faults"]:
        fixes += fa["fixes"]
    with open(os.path.join(pdir, "solution", "fix.json"), "w",
              encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=1)
    # 実機検証用: 全故障の breaks/fixes (この seed のモデルで実体化済み)
    with open(os.path.join(pdir, "solution", "catalog.json"), "w",
              encoding="utf-8") as f:
        json.dump({"catalog": [{"id": fa["id"], "layer": fa["layer"],
                                "desc": fa["desc"], "symptom": fa["symptom"],
                                "breaks": fa["breaks"], "fixes": fa["fixes"]}
                               for fa in m["catalog"]]},
                  f, ensure_ascii=False, indent=1)
    return pdir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=2, choices=[0, 1, 2, 3],
                    help="注入する故障数 (0=ベースライン)。層をまたいで選択")
    ap.add_argument("--decoys", type=int, default=1, choices=[0, 1, 2],
                    help="おとり(無害な差分)の数")
    ap.add_argument("--pece", default="ospf", choices=["ospf"],
                    help="PE-CE 方式 (将来軸: static/ebgp)")
    args = ap.parse_args()

    m = build_model(args.seed, args.faults,
                    args.decoys if args.faults else 0)
    pdir = emit(m, args.repo, args.faults)
    print(f"generated: {pdir}")
    for fa in m["faults"]:
        print(f"  fault: [{fa['layer']}] {fa['id']} -> {fa['desc']}")
    for d in m["decoys"]:
        print(f"  decoy: {d['id']} ({d['node']})")


if __name__ == "__main__":
    main()
