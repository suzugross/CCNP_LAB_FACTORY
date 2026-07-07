#!/usr/bin/env python3
"""BGP トラブルシュート問題 生成器（MP-BGP / address-family 書式対応）。

正準「トランジット AS」トポロジ（値は seed でランダム化）に正しい BGP/OSPF を入れたうえで、
現実的な BGP 故障を注入した初期 config を生成する。出題は症状ベース。
採点は全 Loopback 到達＋セッション Established。

BGP は既定で **MP-BGP（IPv4 でも address-family）書式**で構成する:
  router bgp <as>
   no bgp default ipv4-unicast
   neighbor X remote-as Y           ! セッション設定（update-source/shutdown もここ）
   address-family ipv4 unicast
    neighbor X activate             ! AF 有効化（no bgp default ipv4-unicast 時は必須）
    neighbor X next-hop-self        ! AF ポリシー（prefix-list in もここ）
    network ... mask ...
   exit-address-family
`--style {mpbgp(既定)|classic|mixed}`。mixed は各ルータが seed で書式を選ぶ（混在）。

トポロジ（固定・4 ノード / 3 AS）:
  RT01(AS-a)─eBGP─RT02─iBGP(Lo)─RT03─eBGP─RT04(AS-c)   AS-b=RT02/RT03(OSPF+iBGP)

故障カタログ（幅広く）:
  セッション: ebgp_remoteas / ibgp_remoteas / missing_update_source / neighbor_shutdown /
              wrong_neighbor_ip / transit_ospf_break
  広告      : missing_network / wrong_network_mask / missing_nexthop_self
  受信      : inbound_prefix_filter
  MP-BGP    : missing_activate（address-family で neighbor activate 忘れ→セッションUPだが経路交換せず）

使い方: gen_bgp_troubleshoot.py --repo . --seed <int> [--faults N] [--decoys K] [--style mpbgp|classic|mixed]
"""
import argparse
import json
import os
import random

import yaml


FAULTS = ["ebgp_remoteas", "ibgp_remoteas", "missing_update_source",
          "neighbor_shutdown", "wrong_neighbor_ip", "transit_ospf_break",
          "missing_network", "wrong_network_mask", "missing_nexthop_self",
          "inbound_prefix_filter", "missing_activate"]
FAULT_DIFFICULTY = {f: 4 for f in FAULTS}
FAULT_DIFFICULTY["transit_ospf_break"] = 5
FAULT_DIFFICULTY["missing_nexthop_self"] = 5


def rand_values(rnd):
    asn, used = {}, set()
    for r in ("RT01", "RT02", "RT04"):
        while True:
            v = rnd.randint(64512, 65534)
            if v not in used:
                used.add(v); asn[r] = v; break
    asn["RT03"] = asn["RT02"]
    lo, usedlo = {}, set()
    for r in ("RT01", "RT02", "RT03", "RT04"):
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in usedlo:
                usedlo.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    seg, usedseg = {}, set()
    for name in ("12", "23", "34"):
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in usedseg:
                usedseg.add((p, q)); seg[name] = f"10.{p}.{q}"; break
    return asn, lo, seg


def select_faults(rnd, n):
    pool = list(FAULTS)
    rnd.shuffle(pool)
    return pool[:max(0, min(n, len(pool)))]


def select_decoys(rnd, k):
    decoys, attempts = [], 0
    kinds = ["ghost_neighbor", "unused_prefix_list", "comment", "unused_network"]
    nodes = ["RT01", "RT02", "RT03", "RT04"]
    while len(decoys) < k and attempts < 200:
        attempts += 1
        dt = rnd.choice(kinds)
        R = rnd.choice(nodes)
        if dt == "ghost_neighbor":          # TEST-NET-1（到達不能・Idle のまま=無害）
            ip = f"192.0.2.{rnd.randint(1, 254)}"
            decoys.append({"type": dt, "node": R, "where": "session",
                           "lines": [f"neighbor {ip} remote-as 65000"]})
        elif dt == "unused_prefix_list":
            decoys.append({"type": dt, "node": R, "where": "global",
                           "lines": ["ip prefix-list DECOY-LEGACY seq 5 permit 10.20.0.0/16 le 32"]})
        elif dt == "comment":
            decoys.append({"type": dt, "node": R, "where": "session",
                           "lines": ["! legacy peering note - review later"]})
        else:                                # 到達性に無関係な広告（AF）
            decoys.append({"type": dt, "node": R, "where": "af",
                           "lines": ["network 198.51.100.0 mask 255.255.255.0"]})
    return decoys


def nbr(ip, remote_as, ibgp=False, update_source=False, next_hop_self=False,
        activate=True, prefix_list_in=None, shutdown=False):
    return {"ip": ip, "remote_as": remote_as, "ibgp": ibgp,
            "update_source": update_source, "next_hop_self": next_hop_self,
            "activate": activate, "prefix_list_in": prefix_list_in, "shutdown": shutdown}


def render_bgp(asn, rid, style, neighbors, networks, sess_decoy, af_decoy):
    """style に応じて MP-BGP / classic の BGP config 行を返す。"""
    L = [f"router bgp {asn}", f" bgp router-id {rid}"]
    if style == "mpbgp":
        L.append(" no bgp default ipv4-unicast")
    # セッション設定（remote-as / update-source / shutdown）は両 style とも router bgp 直下
    for nb in neighbors:
        L.append(f" neighbor {nb['ip']} remote-as {nb['remote_as']}")
        if nb["update_source"]:
            L.append(f" neighbor {nb['ip']} update-source Loopback0")
        if nb["shutdown"]:
            L.append(f" neighbor {nb['ip']} shutdown")
    L += [f" {x}" for x in sess_decoy]
    if style == "mpbgp":
        L.append(" address-family ipv4 unicast")
        for nb in neighbors:
            if nb["activate"]:
                L.append(f"  neighbor {nb['ip']} activate")
            if nb["next_hop_self"]:
                L.append(f"  neighbor {nb['ip']} next-hop-self")
            if nb["prefix_list_in"]:
                L.append(f"  neighbor {nb['ip']} prefix-list {nb['prefix_list_in']} in")
        for (p, m) in networks:
            L.append(f"  network {p} mask {m}")
        L += [f"  {x}" for x in af_decoy]
        L.append(" exit-address-family")
    else:  # classic（neighbor は ipv4 自動有効・activate 不要）
        for nb in neighbors:
            if nb["next_hop_self"]:
                L.append(f" neighbor {nb['ip']} next-hop-self")
            if nb["prefix_list_in"]:
                L.append(f" neighbor {nb['ip']} prefix-list {nb['prefix_list_in']} in")
        for (p, m) in networks:
            L.append(f" network {p} mask {m}")
        L += [f" {x}" for x in af_decoy]
    return L


def bgp_parents(asn, style, level):
    """fix 用の parents。level: 'session'=router bgp直下 / 'af'=address-family配下。"""
    if level == "af" and style == "mpbgp":
        return [f"router bgp {asn}", "address-family ipv4 unicast"]
    return f"router bgp {asn}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=1)
    ap.add_argument("--decoys", type=int, default=0)
    ap.add_argument("--style", choices=["mpbgp", "classic", "mixed"], default="mpbgp")
    a = ap.parse_args()
    if a.faults < 0 or a.decoys < 0:
        raise SystemExit("--faults/--decoys は 0 以上")

    rnd = random.Random(a.seed)
    routers = ["RT01", "RT02", "RT03", "RT04"]
    asn, lo, seg = rand_values(rnd)
    faults = select_faults(rnd, a.faults)
    decoys = select_decoys(rnd, a.decoys)
    has = set(faults)

    # 各ルータの書式
    if a.style == "mixed":
        styles = {r: rnd.choice(["mpbgp", "classic"]) for r in routers}
    else:
        styles = {r: a.style for r in routers}
    if "missing_activate" in has:          # activate 故障は MP-BGP ルータでのみ意味を持つ
        styles["RT04"] = "mpbgp"

    ip12 = {"RT01": f"{seg['12']}.1", "RT02": f"{seg['12']}.2"}
    ip23 = {"RT02": f"{seg['23']}.1", "RT03": f"{seg['23']}.2"}
    ip34 = {"RT03": f"{seg['34']}.1", "RT04": f"{seg['34']}.2"}

    # ---- 健全な BGP スペック ----
    spec = {
        "RT01": {"neighbors": [nbr(ip12["RT02"], asn["RT02"])],
                 "networks": [(lo["RT01"], "255.255.255.255")]},
        "RT02": {"neighbors": [nbr(ip12["RT01"], asn["RT01"]),
                               nbr(lo["RT03"], asn["RT02"], ibgp=True,
                                   update_source=True, next_hop_self=True)],
                 "networks": [(lo["RT02"], "255.255.255.255")]},
        "RT03": {"neighbors": [nbr(ip34["RT04"], asn["RT04"]),
                               nbr(lo["RT02"], asn["RT02"], ibgp=True,
                                   update_source=True, next_hop_self=True)],
                 "networks": [(lo["RT03"], "255.255.255.255")]},
        "RT04": {"neighbors": [nbr(ip34["RT03"], asn["RT03"])],
                 "networks": [(lo["RT04"], "255.255.255.255")]},
    }
    blk_on_rt04 = False

    # ---- 故障注入（スペックを書き換え）----
    def n_of(R, ip):
        for x in spec[R]["neighbors"]:
            if x["ip"] == ip:
                return x
        return None
    if "ebgp_remoteas" in has:
        n_of("RT01", ip12["RT02"])["remote_as"] = asn["RT02"] + 1
    if "ibgp_remoteas" in has:
        n_of("RT02", lo["RT03"])["remote_as"] = asn["RT02"] + 1
    if "missing_update_source" in has:
        n_of("RT02", lo["RT03"])["update_source"] = False
    if "neighbor_shutdown" in has:
        n_of("RT01", ip12["RT02"])["shutdown"] = True
    if "wrong_neighbor_ip" in has:
        n_of("RT01", ip12["RT02"])["ip"] = f"{seg['12']}.9"
    if "missing_network" in has:
        spec["RT01"]["networks"] = []
    if "wrong_network_mask" in has:
        spec["RT01"]["networks"] = [(lo["RT01"], "255.255.255.0")]
    if "missing_nexthop_self" in has:
        n_of("RT02", lo["RT03"])["next_hop_self"] = False
    if "inbound_prefix_filter" in has:
        n_of("RT04", ip34["RT03"])["prefix_list_in"] = "BLK"
        blk_on_rt04 = True
    if "missing_activate" in has:
        n_of("RT04", ip34["RT03"])["activate"] = False

    # decoys 振り分け
    sess_decoy, af_decoy, glob_decoy = {}, {}, {}
    for d in decoys:
        tgt = {"session": sess_decoy, "af": af_decoy, "global": glob_decoy}[d["where"]]
        tgt.setdefault(d["node"], []).extend(d["lines"])

    # ---- 各ノードの config 組み立て ----
    def transit_ospf(R):
        o = ["router ospf 1", f" network {lo[R]} 0.0.0.0 area 0"]
        if not ("transit_ospf_break" in has and R == "RT02"):
            o.append(f" network {seg['23']}.0 0.0.0.3 area 0")
        return o + ["!"]

    cfgs = {}
    # 物理スロット: RT01:0→RT02 / RT02:0→RT01,1→RT03 / RT03:0→RT02,1→RT04 / RT04:0→RT03
    ipslot = {"RT01": [(0, ip12["RT01"])], "RT02": [(0, ip12["RT02"]), (1, ip23["RT02"])],
              "RT03": [(0, ip23["RT03"]), (1, ip34["RT03"])], "RT04": [(0, ip34["RT03"] and ip34["RT04"])]}
    ipslot["RT04"] = [(0, ip34["RT04"])]
    role = {"RT01": "AS-a edge", "RT02": "AS-b transit", "RT03": "AS-b transit", "RT04": "AS-c edge"}
    for R in routers:
        L = [f"! {R} (AS {asn[R]} / {role[R]} / BGP={styles[R]})",
             "interface Loopback0", f" ip address {lo[R]} 255.255.255.255", "!"]
        for (s, ip) in ipslot[R]:
            L += [f"interface {{{{ links[{s}] }}}}", f" ip address {ip} 255.255.255.252",
                  " no shutdown", "!"]
        if R in ("RT02", "RT03"):
            L += transit_ospf(R)
        L += render_bgp(asn[R], lo[R], styles[R], spec[R]["neighbors"], spec[R]["networks"],
                        sess_decoy.get(R, []), af_decoy.get(R, []))
        L += ["!"]
        if R == "RT04" and blk_on_rt04:
            L += [f"ip prefix-list BLK seq 5 deny {lo['RT01']}/32",
                  "ip prefix-list BLK seq 10 permit 0.0.0.0/0 le 32", "!"]
        L += glob_decoy.get(R, [])
        cfgs[R] = L

    # ---- 故障 → 修正（style に応じた parents）----
    def full_neighbor_fix(R, n):
        """neighbor を完全再投入する fix エントリ群（remote-as/ip 故障の堅牢な修正）。"""
        out = [{"node": R, "parents": bgp_parents(asn[R], styles[R], "session"),
                "lines": [f"neighbor {n['ip']} remote-as {n['remote_as']}"]
                + ([f"neighbor {n['ip']} update-source Loopback0"] if n["update_source"] else [])}]
        af = []
        if styles[R] == "mpbgp" and n["activate"]:
            af.append(f"neighbor {n['ip']} activate")
        if n["next_hop_self"]:
            af.append(f"neighbor {n['ip']} next-hop-self")
        if af:
            out.append({"node": R, "parents": bgp_parents(asn[R], styles[R], "af"), "lines": af})
        return out

    def fault_fix(ft):
        if ft == "transit_ospf_break":
            return [{"node": "RT02", "parents": "router ospf 1",
                     "lines": [f"network {seg['23']}.0 0.0.0.3 area 0"]}]
        if ft == "ebgp_remoteas":
            R, ip = "RT01", ip12["RT02"]
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "session"),
                     "lines": [f"no neighbor {ip} remote-as {asn['RT02'] + 1}"]}] \
                + full_neighbor_fix(R, nbr(ip, asn["RT02"], activate=True))
        if ft == "ibgp_remoteas":
            R, ip = "RT02", lo["RT03"]
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "session"),
                     "lines": [f"no neighbor {ip} remote-as {asn['RT02'] + 1}"]}] \
                + full_neighbor_fix(R, nbr(ip, asn["RT02"], ibgp=True, update_source=True,
                                           next_hop_self=True, activate=True))
        if ft == "wrong_neighbor_ip":
            R = "RT01"
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "session"),
                     "lines": [f"no neighbor {seg['12']}.9 remote-as {asn['RT02']}"]}] \
                + full_neighbor_fix(R, nbr(ip12["RT02"], asn["RT02"], activate=True))
        if ft == "missing_update_source":
            R = "RT02"
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "session"),
                     "lines": [f"neighbor {lo['RT03']} update-source Loopback0"]}]
        if ft == "neighbor_shutdown":
            R = "RT01"
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "session"),
                     "lines": [f"no neighbor {ip12['RT02']} shutdown"]}]
        if ft == "missing_network":
            R = "RT01"
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "af"),
                     "lines": [f"network {lo['RT01']} mask 255.255.255.255"]}]
        if ft == "wrong_network_mask":
            R = "RT01"
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "af"),
                     "lines": [f"no network {lo['RT01']} mask 255.255.255.0",
                               f"network {lo['RT01']} mask 255.255.255.255"]}]
        if ft == "missing_nexthop_self":
            R = "RT02"
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "af"),
                     "lines": [f"neighbor {lo['RT03']} next-hop-self"]}]
        if ft == "missing_activate":
            R = "RT04"
            return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "af"),
                     "lines": [f"neighbor {ip34['RT03']} activate"]}]
        # inbound_prefix_filter
        R = "RT04"
        return [{"node": R, "parents": bgp_parents(asn[R], styles[R], "af"),
                 "lines": [f"no neighbor {ip34['RT03']} prefix-list BLK in"]}]

    fixes = [fx for ft in faults for fx in fault_fix(ft)]
    diff = (min(5, max((FAULT_DIFFICULTY[f] for f in faults), default=3))
            + (1 if len(faults) > 1 else 0) + (1 if decoys else 0)) if faults else 3
    diff = min(5, diff)

    # ---- 出力 ----
    prob_id = f"GEN-BGPTS-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id,
               "title": f"BGP トラブルシュート (transit AS, {a.style}, seed={a.seed})",
               "exam": "ENARSI", "topics": ["bgp", "mp-bgp", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": routers, "points": 100, "access": "ssh",
               "lab": {"links": [{"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                                 {"a": "RT02", "a_if": 1, "b": "RT03", "b_if": 0},
                                 {"a": "RT03", "a_if": 1, "b": "RT04", "b_if": 0}],
                       "positions": {"RT01": [-480, -200], "RT02": [-160, -200],
                                     "RT03": [160, -200], "RT04": [480, -200]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_troubleshoot.py) seed={a.seed} style={a.style} faults={len(faults)}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for R in routers:
        with open(f"{pdir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(cfgs[R]) + "\n")

    model = {"loopbacks": {r: lo[r] for r in routers},
             "links": [{"a": "RT01", "a_ip": ip12["RT01"], "b": "RT02", "b_ip": ip12["RT02"]},
                       {"a": "RT02", "a_ip": ip23["RT02"], "b": "RT03", "b_ip": ip23["RT03"]},
                       {"a": "RT03", "a_ip": ip34["RT03"], "b": "RT04", "b_ip": ip34["RT04"]}]}
    checks = []
    pairs = [(X, Y) for X in routers for Y in routers if X != Y]
    pp = 60 // len(pairs)
    for (X, Y) in pairs:
        checks.append({"name": f"{X}: {lo[Y]}/32 を RIB に学習", "node": X,
                       "command": "show ip route", "parser": "show ip route",
                       "find": "vrf.*.address_family.*.routes.*",
                       "match": {"route": f"{lo[Y]}/32"}, "points": pp})
    for (X, peer, label) in [("RT01", ip12["RT02"], "eBGP RT01-RT02"),
                             ("RT02", lo["RT03"], "iBGP RT02-RT03"),
                             ("RT04", ip34["RT03"], "eBGP RT03-RT04")]:
        checks.append({"name": f"{label}: Established", "node": X,
                       "command": f"show ip bgp neighbors {peer}",
                       "raw": [{"regex": "BGP state += +Established"}], "points": 8})
    grading = {"problem": prob_id, "total_points": 100, "defaults": {"genie_os": "iosxe"},
               "model": model,
               "invariants": [{"type": "loop_free", "name": "転送ループ不在", "points": 16}],
               "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_troubleshoot.py) seed={a.seed}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    sym = {"missing_network": ("RT04", "RT01"), "wrong_network_mask": ("RT04", "RT01"),
           "ebgp_remoteas": ("RT04", "RT01"), "neighbor_shutdown": ("RT04", "RT01"),
           "wrong_neighbor_ip": ("RT04", "RT01"), "ibgp_remoteas": ("RT01", "RT04"),
           "missing_update_source": ("RT01", "RT04"), "transit_ospf_break": ("RT01", "RT04"),
           "missing_nexthop_self": ("RT04", "RT01"), "inbound_prefix_filter": ("RT04", "RT01"),
           "missing_activate": ("RT01", "RT04")}
    rep = sym.get(faults[0], ("RT01", "RT04")) if faults else ("RT01", "RT04")
    json.dump({"count": len(faults), "faults": faults, "style": a.style, "styles": styles,
               "values": {"asn": asn, "lo": lo, "seg": seg}},
              open(f"{pdir}/solution/fault.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"fixes": fixes}, open(f"{pdir}/solution/fix.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"decoys": decoys}, open(f"{pdir}/solution/decoys.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"reported_symptom": {"src": rep[0], "dst": rep[1], "dst_loopback": f"{lo[rep[1]]}/32"},
               "fault_count": len(faults), "decoy_count": len(decoys)},
              open(f"{pdir}/solution/impact.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/README.md", "w", encoding="utf-8") as f:
        f.write("# 採点者専用（受験者に見せないこと）\n\n"
                f"- style={a.style} / 各ルータ: {styles}\n- AS:{asn}\n- Lo:{lo}\n- seg:{seg}\n"
                f"- 故障数:{len(faults)}\n" + "".join(f"  - {ft}\n" for ft in faults)
                + f"- おとり:{len(decoys)}\n" + "".join(f"  - {d['type']}@{d['node']}\n" for d in decoys))

    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 障害対応 {prob_id} : BGP 到達性（トランジット AS / 4 ルータ）\n\n")
        f.write("## 状況\n3 つの AS をまたぐ BGP ネットワーク。AS-b(RT02/RT03) がトランジットで、"
                "内部は OSPF＋iBGP(Loopback ピア)で構成されている。"
                "BGP は **MP-BGP（`address-family ipv4 unicast`）書式**で組まれている"
                "（ルータにより従来書式と混在する場合がある）。"
                "ある変更作業の後から到達性の不具合が報告されている。\n\n")
        f.write("## 受付チケット\n")
        f.write(f"> 「**{rep[0]}** から **{rep[1]}** の Loopback (`{lo[rep[1]]}/32`) に到達できない」"
                "という申告がありました。\n>\n> 切り分けて原因を特定し、恒久的に復旧してください。"
                "原因は 1 か所とは限りません。\n\n")
        f.write("## 構成台帳\n| ルータ | AS | Loopback |\n|---|---|---|\n")
        for r in routers:
            f.write(f"| {r} | {asn[r]} | `{lo[r]}/32` |\n")
        f.write("\n- eBGP: RT01-RT02 / RT03-RT04　iBGP: RT02-RT03(Loopback)　OSPF: AS-b 内\n")
        f.write("\n※ `no bgp default ipv4-unicast` 構成では `address-family ipv4 unicast` 配下の "
                "`neighbor activate` や `network` も確認すること。区間アドレス・原因の場所/種類/件数は非公開。\n")
        f.write("\n## 完了条件\nすべてのルータが、他の全ルータの Loopback を RIB に学習している状態。\n\n")
        f.write(f"## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    print(f"wrote {prob_id}: style={a.style} {styles if a.style=='mixed' else ''}, "
          f"faults={len(faults)} {faults}, decoys={len(decoys)}, 難易度={diff}")


if __name__ == "__main__":
    main()
