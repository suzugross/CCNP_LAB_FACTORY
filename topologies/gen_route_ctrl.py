#!/usr/bin/env python3
"""GEN-RTCTL — 純粋経路制御(条件付きリスト作成・適用)構築問の生成器(難易度4・BL-141/BL-143)。

設計= problems/_drafts/RTCTL-DOJO.design.md(§11=v2) / 実機PoC= poc/rtctl/README.md
(v1 2026-08-23 全通過・v2 追加PoC 同日全通過)。

正準盤面(5 IOL・固定):
        RT04 (経路源: battery Lo群)
        /            \\
     RT02            RT03      ← 同一 EIGRP AS100 の並列フィード(RT01 で完全 ECMP)
        \\            /
         RT01 (主戦場・唯一の作業対象)
          |
         RT05 (OSPF 1 Area0・Lo群は ip ospf network point-to-point)

★v2(BL-143): 「固定6Task骨格+値抽選」が同一パック複数本で露呈したユーザ指摘への改修。
  - タスクプール化: 各スロットの実現手段を抽選
      T-excl:  {番号ACL DL / named ACL DL / prefix-list DL}(deny禁止は共通)
      T-pref:  {2経路互い違い / 群寄せ+1本だけ例外} × {offset-list縛り/自由}
      T-e2o:   {1行prefix-list×route-map / OSPF側プロトコル指定DL(out eigrp 100)}
      T-o2e:   {EIGRP側プロトコル指定DL(route-map禁止) / route-map指定(DL禁止) / 手段自由}
      T-add:   ACL追記(o2e が ACL 系のとき) / 効果のみ(自由のとき)
  - ★PL集合形(pl_shape)抽選: 「4連続/24→/22 ge 24 le 24」の暗記を無効化。
      quad24(4連続=正準/22) / pair24(先頭2本だけ=/23・残り2本は/22内デコイ) /
      mixed_len(/24+/25+/26混在=/22 ge 24 le 26) / longer_only(/25・/26のみ=ge 25) /
      exact(/22経路そのもの+隣接/22のデコイ)。全形で/22外の同/16デコイ/24常設。
  - 骨格抽選: T-pref(p=0.8)/T-add(p=0.75)の有無 + 独立タスクの順序シャッフル。
    配点は settle で常に合計100へ整合。
  - 制約文言の粒度も手段抽選に追随(番号指定/名前指定/手段のみ/自由)。

★採点実装の要(実測):
  - 経路詳細ビューは via <IF名>(via <IP> は現れない)。next-hop IP は素の contains。
  - RT05 の外部経路: 対象集合のマスクが均一なら行に /len 無し・混在なら全行 /len 付き。
  - offset-list のリスト部は named ACL 可 → regex は \\S+。数値終端 regex は (?!\\d)。
  - offset は RD にも加算 → offset < FD-RD(=25600) を生成器が保証(FS維持=即時切替)。
  - topology 表 `1 Successor` で素の ECMP(2 Successors)を弾く。

出力: problems/GEN-RTCTL-<seed>/
使い方: gen_route_ctrl.py --repo . --seed <int> [--force k=v,k=v]
        gen_route_ctrl.py --selfcheck N   (seed 1..N を無出力で検品・分布表示)
--force は検証専用(抽選結果を上書き。乱数列は消費済みのため他の値は不変):
  pl_shape/excl_method/excl_pol=permit_only|deny_based/e2o_method/o2e_method/
  t2_variant/t2_mode=bind|free/with_t2=0|1/with_t5=0|1/eigrp_as=N/ospf_pid=N
"""
import argparse
import ipaddress
import os
import random
import json

import yaml

NODES = ["RT01", "RT02", "RT03", "RT04", "RT05"]
IF_TO_RT02 = "Ethernet0/0"   # RT01 slot0
IF_TO_RT03 = "Ethernet0/1"   # RT01 slot1
IF_TO_RT05 = "Ethernet0/2"   # RT01 slot2
NH = {"RT02": "10.1.12.2", "RT03": "10.1.13.2"}
FS_MARGIN = 25600            # 実測 FD-RD。offset はこれ未満を保証

PL_SHAPES = ["quad24", "pair24", "mixed_len", "longer_only", "exact"]
EXCL_METHODS = ["acl_num", "acl_named", "pl_dl"]
E2O_METHODS = ["rm_pl", "rm_pl", "rm_pl", "ospf_dl_out", "ospf_dl_out"]
O2E_METHODS = ["proto_dl", "proto_dl", "rm", "rm", "free"]
T2_VARIANTS = ["two_opposite", "group_exception"]

ACL_NAMES = ["FILTER-CORE-IN", "CORP-IN-FILTER", "INBOUND-EDGE", "BRANCH-IN-ACL"]
PLDL_NAMES = ["PL-FEED-IN", "PL-CORE-IN", "PL-EDGE-IN", "PL-UPLINK-IN"]
PL_NAMES = ["PL-CORE-NETS", "PL-TOKYO-LAN", "PL-DC-BLOCK", "PL-BRANCH24"]
RM_NAMES = ["RM-E2O", "RM-REDIST-OUT", "RM-TO-OSPF", "RM-CORE-EXPORT"]
RM2_NAMES = ["RM-O2E", "RM-FROM-OSPF", "RM-OSPF-IMPORT"]
METRICS = ["10000 1000 255 1 1500", "1000000 1 255 1 1500",
           "100000 100 255 1 1500", "50000 200 255 1 1500"]
OFFSETS = [1000, 2000, 3000, 4000, 5000]


# ==========================================================================
# 抽選
# ==========================================================================

def _pick(rnd, pool, force, key):
    val = rnd.choice(pool)
    return force.get(key, val)


def rand_values(rnd, force=None):
    force = force or {}
    v = {}
    # --- A 群(PL 集合形) ---
    v["pl_shape"] = _pick(rnd, PL_SHAPES, force, "pl_shape")
    v["a"] = rnd.randint(16, 31)
    k = rnd.randrange(0, 61)                 # /22 整列ブロック(隣接ブロックの余地を残す)
    b0 = k * 4
    v["b0"] = b0
    sh = v["pl_shape"]
    if sh in ("quad24", "pair24"):
        mem = [(b0, 24), (b0 + 1, 24), (b0 + 2, 24), (b0 + 3, 24)]
        target = mem if sh == "quad24" else mem[:2]
        canon = (f"172.{v['a']}.{b0}.0/22 ge 24 le 24" if sh == "quad24"
                 else f"172.{v['a']}.{b0}.0/23 ge 24 le 24")
    elif sh in ("mixed_len", "longer_only"):
        mem = [(b0, 24), (b0 + 1, 25), (b0 + 2, 26), (b0 + 3, 24)]
        target = mem if sh == "mixed_len" else mem[1:3]
        canon = (f"172.{v['a']}.{b0}.0/22 ge 24 le 26" if sh == "mixed_len"
                 else f"172.{v['a']}.{b0}.0/22 ge 25")
    else:                                    # exact
        b1 = b0 + 4 if b0 + 4 <= 248 else b0 - 4
        mem = [(b0, 22), (b1, 24), (b1 + 1, 24)]
        target = mem[:1]
        canon = f"172.{v['a']}.{b0}.0/22"
    used_blocks = {m[0] // 4 for m in mem}
    db = rnd.choice([x * 4 for x in range(0, 62) if x not in used_blocks])
    v["a_members"] = mem                     # [(第3オクテット, プレフィクス長), ...]
    v["a_decoy"] = (db, 24)
    v["a_target"] = target
    v["pl_canonical"] = canon
    # --- B 群(飛び地3) ---
    octs = [o for o in list(range(2, 10)) + list(range(20, 60))]
    v["gb"] = rnd.choice(octs)
    p1 = rnd.randint(1, 80)
    p2 = p1 + rnd.randint(2, 8)
    p3 = p2 + rnd.randint(2, 8)
    v["bs"] = [p1, p2, p3]
    # --- C 群(除外対象) ---
    v["c1"], v["c2"] = rnd.sample(range(1, 255), 2)
    v["c_nets"] = [f"192.168.{v['c1']}.0", f"192.168.{v['c2']}.0"]
    # --- D 群+デコイ(OSPF 側) ---
    v["gd"] = rnd.choice([o for o in octs if o != v["gb"]])
    d1 = rnd.randint(1, 80)
    d2 = d1 + rnd.randint(2, 8)
    d3 = d2 + rnd.randint(2, 8)
    v["ds"] = [d1, d2, d3]
    rnd.shuffle(v["ds"])
    v["d_nets"] = [f"10.{v['gd']}.{d}.0" for d in v["ds"]]
    v["q"] = rnd.choice([x for x in range(16, 32) if x != v["a"]])
    v["decoy_net"] = f"172.{v['q']}.100.0"
    # --- T-excl ---
    v["excl_feed"] = rnd.choice(["RT02", "RT03"])
    v["excl_if"] = IF_TO_RT02 if v["excl_feed"] == "RT02" else IF_TO_RT03
    v["other_if"] = IF_TO_RT03 if v["excl_feed"] == "RT02" else IF_TO_RT02
    v["excl_nh"] = NH[v["excl_feed"]]
    v["other_nh"] = NH["RT03" if v["excl_feed"] == "RT02" else "RT02"]
    v["trap_net"] = "10.1.24.0" if v["excl_feed"] == "RT02" else "10.1.34.0"
    v["excl_method"] = _pick(rnd, EXCL_METHODS, force, "excl_method")
    v["excl_name"] = rnd.choice(ACL_NAMES)
    v["excl_pl"] = rnd.choice(PLDL_NAMES)
    # --- T-pref ---
    with_t2 = rnd.random() < 0.8
    v["with_t2"] = bool(int(force.get("with_t2", with_t2)))
    v["t2_variant"] = _pick(rnd, T2_VARIANTS, force, "t2_variant")
    v["t2_mode"] = _pick(rnd, ["bind", "free"], force, "t2_mode")
    v["ra"], v["rb"] = rnd.sample(v["bs"], 2)      # two_opposite 用
    ra_side = rnd.choice(["RT02", "RT03"])
    v["ra_pref_if"] = IF_TO_RT02 if ra_side == "RT02" else IF_TO_RT03
    v["rb_pref_if"] = IF_TO_RT03 if ra_side == "RT02" else IF_TO_RT02
    v["exc"] = rnd.choice(v["bs"])                 # group_exception 用
    main_side = rnd.choice(["RT02", "RT03"])
    v["main_if"] = IF_TO_RT02 if main_side == "RT02" else IF_TO_RT03
    v["main_feed"] = main_side
    v["exc_if"] = IF_TO_RT03 if main_side == "RT02" else IF_TO_RT02
    v["exc_feed"] = "RT03" if main_side == "RT02" else "RT02"
    v["offset"] = rnd.choice(OFFSETS)
    # --- T-e2o / T-o2e / T-add ---
    v["e2o_method"] = _pick(rnd, E2O_METHODS, force, "e2o_method")
    v["o2e_method"] = _pick(rnd, O2E_METHODS, force, "o2e_method")
    with_t5 = rnd.random() < 0.75
    v["with_t5"] = bool(int(force.get("with_t5", with_t5)))
    v["pl"] = rnd.choice(PL_NAMES)
    v["rm"] = rnd.choice(RM_NAMES)
    v["rm2"] = rnd.choice(RM2_NAMES)
    v["acl1"], v["oa"], v["ob"], v["acl3"] = rnd.sample(range(5, 50), 4)
    v["acl2"] = rnd.randint(50, 99)
    v["metric"] = rnd.choice(METRICS)
    # --- 骨格(順序) ---
    indep = ["t1", "t3", "t4"] + (["t2"] if v["with_t2"] else [])
    rnd.shuffle(indep)
    order = []
    for s in indep:
        order.append(s)
        if s == "t4" and v["with_t5"]:
            order.append("t5")
    order.append("t6")
    v["order"] = order
    v["no"] = {s: i + 1 for i, s in enumerate(order)}
    # --- v3(BL-151): 末尾追加の抽選(既存 seed の先行乱数列を変えない) ---
    # 制約極性: permit_only=対象外を列挙 permit(閉鎖型) / deny_based=対象を deny+包括 permit(開放型)
    v["excl_pol"] = _pick(rnd, ["permit_only", "deny_based"], force, "excl_pol")
    v["eigrp_as"] = int(force.get("eigrp_as", rnd.randint(1, 65535)))
    v["ospf_pid"] = int(force.get("ospf_pid", rnd.randint(1, 99)))
    return v


def _a_net(v, third):
    return f"172.{v['a']}.{third}.0"


def _pl_matches(canon, net, plen):
    """canonical 1行 prefix-list の意味評価(selfcheck 用)。"""
    parts = canon.split()
    base = ipaddress.ip_network(parts[0])
    ge = le = None
    if "ge" in parts:
        ge = int(parts[parts.index("ge") + 1])
    if "le" in parts:
        le = int(parts[parts.index("le") + 1])
    n = ipaddress.ip_network(f"{net}/{plen}")
    if not (n.subnet_of(base) if n.prefixlen >= base.prefixlen else False):
        return False
    lo = ge if ge is not None else (base.prefixlen if le is None else base.prefixlen)
    hi = le if le is not None else (32 if ge is not None else base.prefixlen)
    return lo <= plen <= hi


def selfcheck_values(v):
    nets = []
    for third, plen in v["a_members"] + [v["a_decoy"]]:
        nets.append(f"{_a_net(v, third)}/{plen}")
    nets += [f"10.{v['gb']}.{p}.0/24" for p in v["bs"]]
    nets += [f"{n}/24" for n in v["c_nets"] + v["d_nets"]]
    nets += [f"{v['decoy_net']}/24", "10.1.10.0/26",
             "10.1.12.0/30", "10.1.13.0/30", "10.1.15.0/30",
             "10.1.24.0/30", "10.1.34.0/30"]
    nets += [f"{i}.{i}.{i}.{i}/32" for i in range(1, 6)]
    objs = [ipaddress.ip_network(n) for n in nets]
    for i, x in enumerate(objs):
        for y in objs[i + 1:]:
            assert not x.overlaps(y), f"overlap {x} {y}"
    # canonical PL の意味 = target 集合と一致(デコイ含む全 battery で検査)
    for third, plen in v["a_members"] + [v["a_decoy"]]:
        want = (third, plen) in v["a_target"]
        got = _pl_matches(v["pl_canonical"], _a_net(v, third), plen)
        assert want == got, f"PL semantics {v['pl_shape']} {third}/{plen}"
    assert v["offset"] < FS_MARGIN
    assert len({v["acl1"], v["acl2"], v["oa"], v["ob"], v["acl3"]}) == 5
    assert v["ra"] != v["rb"] and v["ra_pref_if"] != v["rb_pref_if"]
    assert v["order"][-1] == "t6"
    assert v["excl_pol"] in ("permit_only", "deny_based")
    assert 1 <= v["eigrp_as"] <= 65535 and 1 <= v["ospf_pid"] <= 99
    if v["with_t5"]:
        assert v["order"].index("t5") == v["order"].index("t4") + 1


# ==========================================================================
# 初期構成(基線: IP+基本ルーティングのみ)
# ==========================================================================

def _mask(plen):
    return str(ipaddress.ip_network(f"0.0.0.0/{plen}").netmask)


def _iface(name, desc, ip, mask="255.255.255.252"):
    return [f"interface {name}", f" description === {desc} ===",
            f" ip address {ip} {mask}", " no shutdown"]


def initial_cfg(node, v):
    n = int(node[2:])
    lo0 = f"{n}.{n}.{n}.{n}"
    out = ["! ============================================================",
           f"! {node} — 基線(IP+基本ルーティング)は構築済み。",
           "! リスト・再配送は未投入(作問仕様)。",
           "! ============================================================",
           "interface Loopback0",
           f" ip address {lo0} 255.255.255.255"]
    eigrp_nets, ospf_nets = [], []
    if node == "RT01":
        out += _iface(IF_TO_RT02, "to RT02 (EIGRP)", "10.1.12.1")
        out += _iface(IF_TO_RT03, "to RT03 (EIGRP)", "10.1.13.1")
        out += _iface(IF_TO_RT05, "to RT05 (OSPF)", "10.1.15.1")
        eigrp_nets = ["10.1.12.0 0.0.0.3", "10.1.13.0 0.0.0.3"]
        ospf_nets = ["10.1.15.0 0.0.0.3"]
    elif node == "RT02":
        out += _iface("Ethernet0/0", "to RT01 (EIGRP)", "10.1.12.2")
        out += _iface("Ethernet0/1", "to RT04 (EIGRP)", "10.1.24.1")
        eigrp_nets = ["10.1.12.0 0.0.0.3", "10.1.24.0 0.0.0.3"]
    elif node == "RT03":
        out += _iface("Ethernet0/0", "to RT01 (EIGRP)", "10.1.13.2")
        out += _iface("Ethernet0/1", "to RT04 (EIGRP)", "10.1.34.1")
        eigrp_nets = ["10.1.13.0 0.0.0.3", "10.1.34.0 0.0.0.3"]
    elif node == "RT04":
        out += _iface("Ethernet0/0", "to RT02 (EIGRP)", "10.1.24.2")
        out += _iface("Ethernet0/1", "to RT03 (EIGRP)", "10.1.34.2")
        lo_no = 1
        for third, plen in v["a_members"] + [v["a_decoy"]]:
            out += [f"interface Loopback{lo_no}",
                    f" ip address {_a_net(v, third)[:-1]}1 {_mask(plen)}"]
            lo_no += 1
        for i, p in enumerate(v["bs"]):
            out += [f"interface Loopback{11 + i}",
                    f" ip address 10.{v['gb']}.{p}.1 255.255.255.0"]
        for i, net in enumerate(v["c_nets"]):
            out += [f"interface Loopback{21 + i}",
                    f" ip address {net[:-1]}1 255.255.255.0"]
        eigrp_nets = (["10.1.24.0 0.0.0.3", "10.1.34.0 0.0.0.3",
                       f"172.{v['a']}.0.0 0.0.255.255"]
                      + [f"10.{v['gb']}.{p}.0 0.0.0.255" for p in v["bs"]]
                      + [f"{n} 0.0.0.255" for n in v["c_nets"]])
    elif node == "RT05":
        out += _iface("Ethernet0/0", "to RT01 (OSPF)", "10.1.15.2")
        for i, net in enumerate(v["d_nets"]):
            out += [f"interface Loopback{1 + i}",
                    f" ip address {net[:-1]}1 255.255.255.0",
                    " ip ospf network point-to-point"]
        out += ["interface Loopback9",
                f" ip address {v['decoy_net'][:-1]}1 255.255.255.0",
                " ip ospf network point-to-point"]
        ospf_nets = (["10.1.15.0 0.0.0.3"]
                     + [f"{n} 0.0.0.255" for n in v["d_nets"] + [v["decoy_net"]]])
    if eigrp_nets:
        out += ["!", f"router eigrp {v['eigrp_as']}", f" eigrp router-id {lo0}"]
        out += [f" network {n}" for n in eigrp_nets]
        out += [" no auto-summary"]
    if ospf_nets:
        out += ["!", f"router ospf {v['ospf_pid']}", f" router-id {lo0}"]
        out += [f" network {n} area 0" for n in ospf_nets]
    return "\n".join(out) + "\n"


# ==========================================================================
# 採点
# ==========================================================================

def _excl_list_id(v):
    return {"acl_num": str(v["acl1"]), "acl_named": v["excl_name"],
            "pl_dl": v["excl_pl"]}[v["excl_method"]]


def _t1_checks(v, no):
    lid = _excl_list_id(v)
    dl_kw = "prefix " if v["excl_method"] == "pl_dl" else ""
    guard = _a_net(v, v["a_decoy"][0])
    checks = [
        {"name": f"T{no}: {v['c_nets'][0]}/24 が {v['excl_feed']} から学習されていない",
         "node": "RT01", "command": f"show ip route {v['c_nets'][0]}",
         "raw": [{"contains": v["other_nh"]},
                 {"not_contains": v["excl_nh"]}], "points": 4},
        {"name": f"T{no}: {v['c_nets'][1]}/24 が {v['excl_feed']} から学習されていない",
         "node": "RT01", "command": f"show ip route {v['c_nets'][1]}",
         "raw": [{"contains": v["other_nh"]},
                 {"not_contains": v["excl_nh"]}], "points": 4},
        {"name": f"T{no}: 巻き添えなし — {v['trap_net']}/30 が {v['excl_feed']} 直行のまま",
         "node": "RT01", "command": f"show ip route {v['trap_net']} 255.255.255.252",
         "raw": [{"contains": v["excl_nh"]},
                 {"not_contains": v["other_nh"]}], "points": 6},
        {"name": f"T{no}: 巻き添えなし — {guard}/24 の ECMP(両フィード)が維持されている",
         "node": "RT01", "command": f"show ip route {guard}",
         "raw": [{"contains": v["excl_nh"]}, {"contains": v["other_nh"]}], "points": 3},
        {"name": f"T{no}: 制約 — 指定リスト {lid} の distribute-list を "
                 f"{v['excl_if']} の in に適用",
         "node": "RT01", "command": "show running-config | section router eigrp",
         "raw": [{"regex": rf"distribute-list {dl_kw}{lid} in {v['excl_if']}"}],
         "points": 4},
    ]
    c1_rx = v["c_nets"][0].replace(".", r"\.")
    c2_rx = v["c_nets"][1].replace(".", r"\.")
    if v["excl_pol"] == "permit_only":
        if v["excl_method"] == "pl_dl":
            checks.append(
                {"name": f"T{no}: 制約 — prefix-list {lid} に deny エントリが無い",
                 "node": "RT01", "command": f"show ip prefix-list {lid}",
                 "raw": [{"contains": "permit"},
                         {"not_regex": r"(?m)^\s+seq \d+ deny "}], "points": 4})
        else:
            checks.append(
                {"name": f"T{no}: 制約 — リスト {lid} に deny エントリが無い(permit 列挙)",
                 "node": "RT01", "command": f"show access-lists {lid}",
                 "raw": [{"contains": "permit"},
                         {"not_regex": r"(?m)^\s*\d+ deny "}], "points": 4})
    else:                                     # deny_based(v3): deny 指定+包括 permit
        if v["excl_method"] == "pl_dl":
            checks.append(
                {"name": f"T{no}: 制約 — prefix-list {lid} は deny 指定+包括 permit"
                         "(個別の permit なし)",
                 "node": "RT01", "command": f"show ip prefix-list {lid}",
                 "raw": [{"regex": rf"deny {c1_rx}/24"},
                         {"regex": rf"deny {c2_rx}/24"},
                         {"regex": r"permit 0\.0\.0\.0/0"},
                         {"not_regex": r"(?m)^\s+seq \d+ permit (?!0\.0\.0\.0/0)"}],
                 "points": 4})
        else:
            checks.append(
                {"name": f"T{no}: 制約 — リスト {lid} は deny 指定+permit any"
                         "(個別の permit なし)",
                 "node": "RT01", "command": f"show access-lists {lid}",
                 "raw": [{"regex": rf"deny +{c1_rx}"},
                         {"regex": rf"deny +{c2_rx}"},
                         {"regex": r"(?m)^\s*\d+ permit any"},
                         {"not_regex": r"(?m)^\s*\d+ permit (?!any)"}], "points": 4})
    return checks


def _t2_checks(v, no):
    bind = v["t2_mode"] == "bind"
    eff = []
    if v["t2_variant"] == "two_opposite":
        pts = 5 if bind else 7
        for r, pref, anti in [(v["ra"], v["ra_pref_if"], v["rb_pref_if"]),
                              (v["rb"], v["rb_pref_if"], v["ra_pref_if"])]:
            eff.append(
                {"name": f"T{no}: 10.{v['gb']}.{r}.0/24 が {pref} 経由で転送される",
                 "node": "RT01", "command": f"show ip route 10.{v['gb']}.{r}.0",
                 "raw": [{"contains": f"via {pref}"}, {"not_contains": anti}],
                 "points": pts})
        topo_targets = [v["ra"], v["rb"]]
    else:                                     # group_exception
        mains = [p for p in v["bs"] if p != v["exc"]]
        mpts = 4 if bind else 5
        for r in mains:
            eff.append(
                {"name": f"T{no}: 10.{v['gb']}.{r}.0/24 が {v['main_if']} 経由で転送される",
                 "node": "RT01", "command": f"show ip route 10.{v['gb']}.{r}.0",
                 "raw": [{"contains": f"via {v['main_if']}"},
                         {"not_contains": v["exc_if"]}], "points": mpts})
        eff.append(
            {"name": f"T{no}: 例外 10.{v['gb']}.{v['exc']}.0/24 だけが "
                     f"{v['exc_if']} 経由で転送される",
             "node": "RT01", "command": f"show ip route 10.{v['gb']}.{v['exc']}.0",
             "raw": [{"contains": f"via {v['exc_if']}"},
                     {"not_contains": v["main_if"]}], "points": 5 if bind else 7},
        )
        topo_targets = [v["exc"]]
    for r in topo_targets:
        eff.append(
            {"name": f"T{no}: 10.{v['gb']}.{r}.0/24 の代替経路が topology table に"
                     "残っている(切替可能)",
             "node": "RT01", "command": f"show ip eigrp topology 10.{v['gb']}.{r}.0/24",
             "raw": [{"contains": "1 Successor"},
                     {"contains": "Ethernet0/0"}, {"contains": "Ethernet0/1"}],
             "points": 3})
    if bind:
        eff.append(
            {"name": f"T{no}: 制約 — 両インターフェイスの in 方向 offset-list で実現",
             "node": "RT01", "command": "show running-config | section router eigrp",
             # ★リスト部は \S+(named ACL 可)・数値終端は不要(後ろに IF 名が続く)
             "raw": [{"regex": r"offset-list \S+ in \d+ Ethernet0/0"},
                     {"regex": r"offset-list \S+ in \d+ Ethernet0/1"}], "points": 4})
    assert sum(c["points"] for c in eff) == 20, v["t2_variant"]
    return eff


def _t3_expected_regex(v):
    """RT05 の O E2 行 regex。対象集合のマスクが均一なら /len 無し・混在なら /len 付き。"""
    lens = {plen for _, plen in v["a_target"]}
    uniform = len(lens) == 1
    out = []
    for third, plen in v["a_target"]:
        p = rf"172\.{v['a']}\.{third}\.0"
        out.append(rf"(?m)^O E2 +{p} \[110/" if uniform
                   else rf"(?m)^O E2 +{p}/{plen} \[110/")
    return out


def _t3_checks(v, no):
    non_target = [(t, p) for t, p in v["a_members"] if (t, p) not in v["a_target"]]
    raws = ([{"regex": r} for r in _t3_expected_regex(v)]
            + [{"not_contains": _a_net(v, t)} for t, _ in non_target]
            + [{"not_contains": _a_net(v, v["a_decoy"][0])},
               {"not_regex": rf"10\.{v['gb']}\."},
               {"not_regex": r"192\.168\."},
               {"not_regex": r"10\.1\.(12|13|24|34)\."}])
    checks = [
        {"name": f"T{no}: RT05 の外部経路が指定の {len(v['a_target'])} 経路のみである",
         "node": "RT05", "command": "show ip route ospf",
         "raw": raws, "points": 9}]
    if v["e2o_method"] == "rm_pl":
        checks += [
            {"name": f"T{no}: 制約 — prefix-list {v['pl']} が 1 行である",
             "node": "RT01", "command": f"show ip prefix-list {v['pl']}",
             "raw": [{"regex": rf"ip prefix-list {v['pl']}: 1 entries"},
                     {"contains": "permit"}], "points": 4},
            {"name": f"T{no}: 制約 — 再配送が route-map {v['rm']} を参照している",
             "node": "RT01", "command": "show running-config | section router ospf",
             "raw": [{"regex": rf"redistribute eigrp {v['eigrp_as']} (subnets )?route-map {v['rm']}"}],
             "points": 4},
        ]
    else:                                     # ospf_dl_out
        checks.append(
            {"name": f"T{no}: 制約 — OSPF 側のプロトコル指定 distribute-list"
                     f"(ACL {v['acl3']})で実現(route-map 不使用)",
             "node": "RT01", "command": "show running-config | section router ospf",
             "raw": [{"regex": rf"distribute-list {v['acl3']} out eigrp {v['eigrp_as']}"},
                     {"regex": rf"redistribute eigrp {v['eigrp_as']}(?!\d)"},
                     {"not_regex": rf"redistribute eigrp {v['eigrp_as']}[^\n]*route-map"}],
             "points": 8})
    assert sum(c["points"] for c in checks) == 17
    return checks


def _t4_checks(v, no):
    eff = {"name": f"T{no}: RT04 が {v['d_nets'][0]}/24 と {v['d_nets'][1]}/24 のみ"
                   "外部学習(デコイ遮断)",
           "node": "RT04", "command": "show ip route eigrp",
           "raw": [{"regex": rf"(?m)^D EX +{v['d_nets'][0]}/24"},
                   {"regex": rf"(?m)^D EX +{v['d_nets'][1]}/24"},
                   {"not_contains": v["decoy_net"]},
                   {"not_contains": "10.1.15.0"}], "points": 6}
    m = v["metric"]
    if v["o2e_method"] == "proto_dl":
        fp = [{"name": f"T{no}: 制約 — ACL {v['acl2']} のプロトコル指定 distribute-list"
                       " と seed metric(route-map 不使用)",
               "node": "RT01", "command": "show running-config | section router eigrp",
               "raw": [{"regex": rf"distribute-list {v['acl2']} out ospf {v['ospf_pid']}"},
                       # seed metric は redistribute 行 / default-metric のどちらの形も可(BL-147)
                       {"regex": rf"(?:redistribute ospf {v['ospf_pid']} metric {m}(?!\d)"
                                 rf"|default-metric {m}(?!\d))"},
                       {"not_regex": rf"redistribute ospf {v['ospf_pid']}[^\n]*route-map"}],
               "points": 6}]
    elif v["o2e_method"] == "rm":
        fp = [{"name": f"T{no}: 制約 — route-map {v['rm2']} と seed metric"
                       "(distribute-list 不使用)",
               "node": "RT01", "command": "show running-config",
               # route-map 適用と seed metric を分離判定。metric は redistribute 行 /
               # default-metric / route-map 内 set metric のいずれの形も可(BL-147)
               "raw": [{"regex": rf"redistribute ospf {v['ospf_pid']}[^\n]*route-map {v['rm2']}(?!\S)"},
                       {"regex": rf"(?:redistribute ospf {v['ospf_pid']} metric {m}(?!\d)"
                                 rf"|default-metric {m}(?!\d)|set metric {m}(?!\d))"},
                       {"not_regex": r"distribute-list \S+ out ospf"}], "points": 4},
              {"name": f"T{no}: 制約 — route-map {v['rm2']} が ACL {v['acl2']} を参照",
               "node": "RT01", "command": "show running-config | section route-map",
               "raw": [{"regex": rf"route-map {v['rm2']} permit"},
                       {"regex": rf"match ip address {v['acl2']}(?!\d)"}], "points": 2}]
    else:                                     # free
        fp = [{"name": f"T{no}: 指定の seed metric が使用されている",
               "node": "RT01", "command": "show running-config",
               # 手段自由: redistribute 行 / default-metric / set metric の全形を受理(BL-147)
               "raw": [{"regex": rf"(?:redistribute ospf {v['ospf_pid']} metric {m}(?!\d)"
                                 rf"|default-metric {m}(?!\d)|set metric {m}(?!\d))"}],
               "points": 6}]
    checks = [eff] + fp
    assert sum(c["points"] for c in checks) == 12
    return checks


def _t5_checks(v, no):
    d3 = v["d_nets"][2]
    eff = {"name": f"T{no}: 追加要件 — {d3}/24 が EIGRP ドメインへ届いている",
           "node": "RT04", "command": f"show ip route {d3}",
           "raw": [{"contains": f'Known via "eigrp {v["eigrp_as"]}"'},
                   {"contains": "distance 170"}], "points": 4}
    if v["o2e_method"] == "free":
        eff["points"] = 8
        return [eff]
    return [eff,
            {"name": f"T{no}: ACL {v['acl2']} が 3 permit(deny なし)である",
             "node": "RT01", "command": f"show access-lists {v['acl2']}",
             "raw": ([{"contains": n} for n in v["d_nets"]]
                     + [{"not_regex": r"(?m)^\s*\d+ deny "}]), "points": 4}]


def _t6_checks(v, no):
    src_third = v["a_target"][0][0]
    return [
        {"name": f"T{no}: RT04 から {v['d_nets'][0][:-1]}1 への source 指定 ping が成功",
         "node": "RT04",
         "command": f"ping {v['d_nets'][0][:-1]}1 "
                    f"source 172.{v['a']}.{src_third}.1 repeat 5",
         "raw": [{"regex": r"Success rate is (80|100) percent"}], "points": 6}]


def build_checks(v):
    checks = [
        {"name": "基線維持: RT01 の EIGRP 隣接が両フィードと確立している", "node": "RT01",
         "command": "show ip eigrp neighbors",
         "raw": [{"contains": "10.1.12.2"}, {"contains": "10.1.13.2"}], "points": 2},
        {"name": "基線維持: RT01-RT05 の OSPF 隣接が FULL である", "node": "RT01",
         "command": "show ip ospf neighbor",
         "raw": [{"contains": "FULL"}, {"contains": "10.1.15.2"}], "points": 2},
    ]
    builders = {"t1": _t1_checks, "t2": _t2_checks, "t3": _t3_checks,
                "t4": _t4_checks, "t5": _t5_checks, "t6": _t6_checks}
    for slot in v["order"]:
        checks += builders[slot](v, v["no"][slot])
    for node in ["RT02", "RT03", "RT04", "RT05"]:
        checks.append(
            {"name": f"監査: {node} の構成が変更されていない", "node": node,
             "command": "show running-config | include distribute-list|offset-list"
                        "|route-map|redistribute",
             "raw": [{"not_regex": r"(distribute-list|offset-list|route-map|redistribute)"}],
             "points": 2})
    # 配点整合: タスク骨格が可変なので、常に settle で合計 100 に揃える
    total = sum(c["points"] for c in checks)
    assert total <= 100, total
    i = 0
    while total < 100:
        if checks[i]["points"] > 0:
            checks[i]["points"] += 1
            total += 1
        i = (i + 1) % len(checks)
    assert sum(c["points"] for c in checks) == 100
    return checks


# ==========================================================================
# 模範解答
# ==========================================================================

def build_fixes(v):
    fixes = []
    glines = []
    # --- T1 ---
    lid = _excl_list_id(v)
    if v["excl_pol"] == "permit_only":
        acl_body = ([f"permit 172.{v['a']}.0.0 0.0.255.255"]
                    + [f"permit 10.{v['gb']}.{p}.0 0.0.0.255" for p in v["bs"]]
                    + ["permit 10.1.24.0 0.0.0.3", "permit 10.1.34.0 0.0.0.3"])
        pl_body = [f"ip prefix-list {lid} seq 5 permit 10.0.0.0/8 le 32",
                   f"ip prefix-list {lid} seq 10 permit 172.{v['a']}.0.0/16 le 32"]
    else:                                     # deny_based(v3): deny 指定+包括 permit
        acl_body = ([f"deny {n} 0.0.0.255" for n in v["c_nets"]] + ["permit any"])
        pl_body = ([f"ip prefix-list {lid} seq {5 * (i + 1)} deny {n}/24"
                    for i, n in enumerate(v["c_nets"])]
                   + [f"ip prefix-list {lid} seq 15 permit 0.0.0.0/0 le 32"])
    if v["excl_method"] == "acl_num":
        glines += [f"access-list {lid} {ln}" for ln in acl_body]
        dl_line = f"distribute-list {lid} in {v['excl_if']}"
    elif v["excl_method"] == "acl_named":
        fixes.append({"node": "RT01", "parents": [f"ip access-list standard {lid}"],
                      "lines": acl_body})
        dl_line = f"distribute-list {lid} in {v['excl_if']}"
    else:                                     # pl_dl
        glines += pl_body
        dl_line = f"distribute-list prefix {lid} in {v['excl_if']}"
    # --- T2 ---
    offset_lines = []
    if v["with_t2"]:
        if v["t2_variant"] == "two_opposite":
            glines += [f"access-list {v['oa']} permit 10.{v['gb']}.{v['ra']}.0 0.0.0.255",
                       f"access-list {v['ob']} permit 10.{v['gb']}.{v['rb']}.0 0.0.0.255"]
            offset_lines = [
                f"offset-list {v['oa']} in {v['offset']} {v['rb_pref_if']}",
                f"offset-list {v['ob']} in {v['offset']} {v['ra_pref_if']}"]
        else:
            mains = [p for p in v["bs"] if p != v["exc"]]
            glines += [f"access-list {v['oa']} permit 10.{v['gb']}.{p}.0 0.0.0.255"
                       for p in mains]
            glines += [f"access-list {v['ob']} permit 10.{v['gb']}.{v['exc']}.0 0.0.0.255"]
            offset_lines = [
                f"offset-list {v['oa']} in {v['offset']} {v['exc_if']}",
                f"offset-list {v['ob']} in {v['offset']} {v['main_if']}"]
    # --- T3 ---
    ospf_lines = []
    if v["e2o_method"] == "rm_pl":
        glines += [f"ip prefix-list {v['pl']} seq 5 permit {v['pl_canonical']}"]
        fixes.append({"node": "RT01", "parents": [f"route-map {v['rm']} permit 10"],
                      "lines": [f"match ip address prefix-list {v['pl']}"]})
        ospf_lines = [f"redistribute eigrp {v['eigrp_as']} subnets route-map {v['rm']}"]
    else:
        # 標準ACLはネットワークアドレスに突き合わせる(ホスト一致で足りる・PoC実測)
        glines += [f"access-list {v['acl3']} permit {_a_net(v, t)}"
                   for t, _ in v["a_target"]]
        ospf_lines = [f"redistribute eigrp {v['eigrp_as']} subnets",
                      f"distribute-list {v['acl3']} out eigrp {v['eigrp_as']}"]
    # --- T4 ---
    glines += [f"access-list {v['acl2']} permit {v['d_nets'][0]} 0.0.0.255",
               f"access-list {v['acl2']} permit {v['d_nets'][1]} 0.0.0.255"]
    if v["o2e_method"] == "rm":
        fixes.append({"node": "RT01", "parents": [f"route-map {v['rm2']} permit 10"],
                      "lines": [f"match ip address {v['acl2']}"]})
        redist_line = (f"redistribute ospf {v['ospf_pid']} metric {v['metric']}"
                       f" route-map {v['rm2']}")
        o2e_extra = []
    else:                                     # proto_dl / free(モデル解は proto_dl 形)
        redist_line = f"redistribute ospf {v['ospf_pid']} metric {v['metric']}"
        o2e_extra = [f"distribute-list {v['acl2']} out ospf {v['ospf_pid']}"]

    if glines:
        fixes.insert(0, {"node": "RT01", "lines": glines})
    fixes.append({"node": "RT01", "parents": [f"router eigrp {v['eigrp_as']}"],
                  "lines": [dl_line] + offset_lines + [redist_line] + o2e_extra})
    fixes.append({"node": "RT01", "parents": [f"router ospf {v['ospf_pid']}"],
                  "lines": ospf_lines})
    if v["with_t5"]:
        fixes.append({"node": "RT01", "lines": [
            f"access-list {v['acl2']} permit {v['d_nets'][2]} 0.0.0.255"]})
    return fixes


# ==========================================================================
# task.md
# ==========================================================================

def _fmt_a_list(v, members):
    return "、".join(f"{_a_net(v, t)}/{p}" for t, p in members)


def _t1_text(v, no):
    lid = _excl_list_id(v)
    kind_txt = {
        "acl_num": f"番号付き標準アクセス・リスト **{lid}** を使用した distribute-list",
        "acl_named": f"**{lid}** という名前の標準アクセス・リストを使用した distribute-list",
        "pl_dl": f"**{lid}** という名前の prefix-list を使用した **distribute-list**",
    }[v["excl_method"]]
    list_word = "prefix-list" if v["excl_method"] == "pl_dl" else "アクセス・リスト"
    if v["excl_pol"] == "permit_only":
        pol_txt = (f"{list_word} に、**deny エントリを含めてはいけません**。")
    else:                                     # deny_based(v3)
        pol_txt = (f"除外の対象は、**deny エントリで指定**してください。それ以外の"
                   "すべてのルートは、**包括の permit** によって通過させる必要が"
                   "あります。通過させるルートを、**個別に列挙する permit エントリの"
                   "使用は、認められません**。")
    cons = f"この要件は、{kind_txt} で、実現される必要があります。{pol_txt}"
    other_feed = "RT03" if v["excl_feed"] == "RT02" else "RT02"
    return (f"### Task {no}\n\n"
            f"RT01 が {v['excl_feed']} から学習するルートから、{v['c_nets'][0]}/24 と "
            f"{v['c_nets'][1]}/24 を除外してください。{other_feed} から学習されるルート、"
            f"および、除外の対象ではないところのルートに、影響を与えてはいけません。\n\n"
            f"**制約**: {cons}\n")


def _t2_text(v, no):
    bind = ("\n\n**制約**: この要件は、offset-list を、該当するインターフェイスの "
            "**in 方向**に適用することによって、実現される必要があります。"
            if v["t2_mode"] == "bind" else "")
    if v["t2_variant"] == "two_opposite":
        ra_feed = "RT02" if v["ra_pref_if"] == IF_TO_RT02 else "RT03"
        rb_feed = "RT03" if ra_feed == "RT02" else "RT02"
        body = (f"RT01 のルーティング・テーブルで、10.{v['gb']}.{v['ra']}.0/24 への経路は"
                f"**{ra_feed} を経由**し、10.{v['gb']}.{v['rb']}.0/24 への経路は "
                f"**{rb_feed} を経由**する必要があります。")
    else:
        blist = "、".join(f"10.{v['gb']}.{p}.0/24" for p in v["bs"])
        body = (f"RT01 のルーティング・テーブルで、{blist} への経路は、すべて "
                f"**{v['main_feed']} を経由**する必要があります。ただし、"
                f"**10.{v['gb']}.{v['exc']}.0/24 だけ**は、**{v['exc_feed']} を経由**する"
                "必要があります。")
    return (f"### Task {no}\n\n{body}いずれかのリンクに障害が発生した場合には、"
            f"もう一方の経路が、使用される必要があります。{bind}\n")


def _t3_text(v, no):
    tl = _fmt_a_list(v, v["a_target"])
    if v["e2o_method"] == "rm_pl":
        cons = (f"フィルタリングには、**1 行の prefix-list**（名前: **{v['pl']}**）を"
                f"使用すること。route-map（名前: **{v['rm']}**）を使用できるのは、"
                "RT01 のみです。")
    else:
        cons = (f"このフィルタリングに、route-map を使用してはいけません。OSPF "
                f"プロセスにおける、**プロトコル指定の distribute-list**"
                f"（ACL 番号: **{v['acl3']}**）で実現される必要があります。")
    return (f"### Task {no}\n\n"
            f"RT05 のルーティング・テーブルに、{tl} の {len(v['a_target'])} つのルート"
            "だけが、外部ルートとして現れるようにしてください。再配送の設定も、"
            f"あなたが行います。\n\n**制約**: {cons}\n")


def _t4_text(v, no):
    cons = {
        "proto_dl": f"このフィルタリングに、route-map を使用してはいけません。EIGRP "
                    f"プロセスにおける、**プロトコル指定の distribute-list**"
                    f"（ACL 番号: **{v['acl2']}**）で実現される必要があります。",
        "rm": f"このフィルタリングは、**route-map**（名前: **{v['rm2']}**・ACL "
              f"**{v['acl2']}** を参照）で実現される必要があります。distribute-list を"
              "使用してはいけません。",
        "free": "実現の手段は、問いません。",
    }[v["o2e_method"]]
    return (f"### Task {no}\n\n"
            f"OSPF ドメインのルートのうち、**{v['d_nets'][0]}/24 と {v['d_nets'][1]}/24 "
            f"だけ**を、EIGRP ドメインへ再配送してください。シード・メトリックには "
            f"**{v['metric']}** を使用します。\n\n**制約**: {cons}\n")


def _t5_text(v, no):
    if v["o2e_method"] == "free":
        cons = "実現の手段は、問いません。"
    else:
        cons = (f"ACL **{v['acl2']}** の、既存のエントリを削除・再作成せずに、"
                "実現してください。")
    return (f"### Task {no}\n\n"
            f"追加の要件が、判明しました。**{v['d_nets'][2]}/24 も**、EIGRP ドメインへ"
            f"再配送される必要があります。\n\n**制約**: {cons}\n")


def _t6_text(v, no):
    src_third = v["a_target"][0][0]
    return (f"### Task {no}\n\n"
            f"RT04 から、送信元を **172.{v['a']}.{src_third}.1** として、"
            f"**{v['d_nets'][0][:-1]}1** への ping が成功することを、確認してください。\n")


def build_task(pid, v):
    texters = {"t1": _t1_text, "t2": _t2_text, "t3": _t3_text,
               "t4": _t4_text, "t5": _t5_text, "t6": _t6_text}
    tasks = "\n".join(texters[s](v, v["no"][s]) for s in v["order"])
    a_all = _fmt_a_list(v, v["a_members"] + [v["a_decoy"]])
    b_all = "、".join(f"10.{v['gb']}.{p}.0/24" for p in v["bs"])
    c_all = "、".join(f"{n}/24" for n in v["c_nets"])
    d_all = "、".join(f"{n}/24" for n in v["d_nets"])
    return f"""# 問題 {pid} : 選択的経路制御の実装（難易度4）

## シナリオ

あなたは、ある企業のネットワーク・エンジニアです。図に示されているところの
ネットワークは、すでに基本的なコンフィギュレーションが完了しており、EIGRP AS {v['eigrp_as']}
および OSPF プロセス {v['ospf_pid']} の隣接関係は、確立されています。再配送は、まだ設定されて
いません。あなたのタスクは、以下のタスクを、順番に完了することです。
いくつかのタスクには、使用できる手段に関する制約が、含まれています。

```
        RT04 ── 拠点網(Loopback 群)
        /            \\
     RT02            RT03        EIGRP AS {v['eigrp_as']}
        \\            /
         RT01 ─────── RT05       OSPF {v['ospf_pid']} Area 0(RT05 の Loopback 群)
```

## 構成（初期状態で投入済み・変更不可）

| リンク | ネットワーク | 備考 |
|---|---|---|
| RT01 - RT02 | 10.1.12.0/30 | RT01 側 = {IF_TO_RT02}（.1） |
| RT01 - RT03 | 10.1.13.0/30 | RT01 側 = {IF_TO_RT03}（.1） |
| RT01 - RT05 | 10.1.15.0/30 | RT01 側 = {IF_TO_RT05}（.1） |
| RT02 - RT04 | 10.1.24.0/30 | |
| RT03 - RT04 | 10.1.34.0/30 | |

RT04 が広告しているルート（EIGRP）:

- {a_all}
- {b_all}
- {c_all}

RT05 が広告しているルート（OSPF）:

- {d_all}、{v['decoy_net']}/24

## タスク

**すべての作業は、RT01 の上で行われる必要があります。** 他のデバイスの構成を
変更してはいけません（採点で検出されます）。

{tasks}
## 注意

- 設定の変更が、ルーティング・テーブルに反映されるまでに、**最大で 1〜2 分**を
  要することがあります（clear コマンドは、必要とされません）。
- データ・プレーン（インターフェイスの IP アドレス / network 文）を、変更しては
  いけません。

## アクセス・採点

SSH `SUZUKI / CCNP`。採点は、最終状態に対して、一括で行われます。

```
scripts/lab.sh grade {pid}
```
"""


def build_solution_md(pid, v):
    fixes_pretty = []
    for f in build_fixes(v):
        if f.get("parents"):
            fixes_pretty += f["parents"]
            fixes_pretty += [f" {ln}" for ln in f["lines"]]
        else:
            fixes_pretty += f["lines"]
    body = "\n".join(fixes_pretty)
    return f"""# {pid} 模範解答（採点者用）

抽選結果: pl_shape={v['pl_shape']} / excl={v['excl_method']}({v['excl_pol']}) / t2={'なし' if not v['with_t2'] else v['t2_variant'] + '/' + v['t2_mode']} /
e2o={v['e2o_method']} / o2e={v['o2e_method']} / t5={'あり' if v['with_t5'] else 'なし'} / 順序={v['order']} /
EIGRP AS {v['eigrp_as']} / OSPF pid {v['ospf_pid']}

投入は `solution/fix.json`（RT01 のみ）。全文:

```
{body}
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**(pol={v['excl_pol']}): permit_only 回=列挙にトランジット網
  (10.1.24.0/30・10.1.34.0/30)を含め忘れると {v['trap_net']}/30 が対向へ迂回。
  deny_based 回=包括 permit を書き忘れると暗黙 deny で当該フィードの全ルートが落ちる。
  ★設計対比: permit 列挙=閉鎖型(新規の正当経路を落とす)/deny+包括 permit=開放型
  (新規経路を通す)。どちらを要求されているかは要件文で判別する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの {v['offset']} は FS 維持圏内)。
- **T-e2o の正準 1 行**: `{v['pl_canonical']}`(pl_shape={v['pl_shape']})。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する({v['o2e_method']})。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
"""


# ==========================================================================
# 生成
# ==========================================================================

def build(repo, seed, force=None, write=True):
    rnd = random.Random(seed)
    v = rand_values(rnd, force)
    selfcheck_values(v)
    checks = build_checks(v)
    build_fixes(v)                            # 参照整合の検査を兼ねる
    if not write:
        return v

    pid = f"GEN-RTCTL-{seed}"
    pdir = f"{repo}/problems/{pid}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    for node in NODES:
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as fp:
            fp.write(initial_cfg(node, v))

    pmeta = {
        "id": pid,
        "title": f"選択的経路制御の実装 (seed={seed})",
        "exam": "ENARSI",
        "topics": ["routing", "redistribution", "filtering", "eigrp", "ospf",
                   "generated"],
        "difficulty": 4,
        "topology": "generated",
        "target_nodes": NODES,
        "points": 100,
        "access": "ssh",
        "image_family": "iol",
        "lab": {"links": [
            {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
            {"a": "RT01", "a_if": 1, "b": "RT03", "b_if": 0},
            {"a": "RT01", "a_if": 2, "b": "RT05", "b_if": 0},
            {"a": "RT02", "a_if": 1, "b": "RT04", "b_if": 0},
            {"a": "RT03", "a_if": 1, "b": "RT04", "b_if": 1},
        ], "positions": {"RT01": [0, 80], "RT02": [-200, -80], "RT03": [200, -80],
                         "RT04": [0, -250], "RT05": [0, 250]}},
    }
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fp:
        fp.write(f"# 自動生成 (gen_route_ctrl.py) seed={seed}\n")
        yaml.safe_dump(pmeta, fp, allow_unicode=True, sort_keys=False, width=4096)

    grading = {"problem": pid, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as fp:
        fp.write(f"# 自動生成 (gen_route_ctrl.py) seed={seed} "
                 f"shape={v['pl_shape']} excl={v['excl_method']}/{v['excl_pol']} "
                 f"e2o={v['e2o_method']} o2e={v['o2e_method']} "
                 f"as={v['eigrp_as']} pid={v['ospf_pid']}\n")
        yaml.safe_dump(grading, fp, allow_unicode=True, sort_keys=False, width=4096)

    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as fp:
        json.dump({"fixes": build_fixes(v)}, fp, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/solution.md", "w", encoding="utf-8") as fp:
        fp.write(build_solution_md(pid, v))
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as fp:
        fp.write(build_task(pid, v))

    print(f"generated {pid} (shape={v['pl_shape']} "
          f"excl={v['excl_method']}/{v['excl_pol']} "
          f"t2={'-' if not v['with_t2'] else v['t2_variant'] + '/' + v['t2_mode']} "
          f"e2o={v['e2o_method']} o2e={v['o2e_method']} "
          f"t5={'y' if v['with_t5'] else 'n'} order={v['order']} "
          f"as={v['eigrp_as']} pid={v['ospf_pid']})")
    print(f"  A=172.{v['a']} members={v['a_members']} decoy={v['a_decoy']} "
          f"target={v['a_target']}")
    print(f"  canonical-PL: {v['pl_canonical']}")
    print(f"  B=10.{v['gb']}.{v['bs']} C=192.168.[{v['c1']},{v['c2']}] "
          f"D=10.{v['gd']}.{v['ds']} decoy={v['decoy_net']}")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--force", default="",
                    help="検証専用: k=v,k=v で抽選結果を上書き")
    ap.add_argument("--selfcheck", type=int, default=0)
    a = ap.parse_args()
    force = dict(kv.split("=", 1) for kv in a.force.split(",") if "=" in kv)
    if a.selfcheck:
        dist = {}
        for s in range(1, a.selfcheck + 1):
            v = build(a.repo, s, write=False)
            for k in ("pl_shape", "excl_method", "e2o_method", "o2e_method",
                      "excl_pol"):
                dist.setdefault(k, {}).setdefault(v[k], 0)
                dist[k][v[k]] += 1
            key = "order"
            dist.setdefault(key, {}).setdefault("/".join(v["order"]), 0)
            dist[key]["/".join(v["order"])] += 1
        for k in ("pl_shape", "excl_method", "e2o_method", "o2e_method",
                  "excl_pol"):
            print(f"{k}: {dist[k]}")
        print(f"order patterns: {len(dist['order'])} 種")
        print(f"selfcheck OK: seeds 1..{a.selfcheck}")
        return
    if a.seed is None:
        ap.error("--seed か --selfcheck が必要")
    build(a.repo, a.seed, force=force)


if __name__ == "__main__":
    main()
