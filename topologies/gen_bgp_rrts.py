#!/usr/bin/env python3
"""BGP Route Reflector / iBGP 伝播トラブルシュート生成器。

RR スター構成（RT02=RR / RT03・RT04=client・client 間は非ピア）。
- **Loopback0** = iBGP ピアリング用（OSPF に載せ next-hop 解決に使う・router-id）。
- **Loopback1** = テスト対象プレフィックス（**BGP のみで広告・IGP に載せない**）。
client の Loopback1 は反射でしか伝わらないので、route-reflector-client 欠落は
「全セッション Established・RR には経路有・next-hop も解決可なのに **client 同士(RT03↔RT04)
だけが互いの Loopback1 を学習できない**」という、到達性故障とも経路故障とも違う診断になる。
（反射経路は RR が next-hop を保持する→OSPF で peering Lo0 を解決できる設計が必須。）

トポロジ（固定・4 ノード・スター）:
  RT01(AS-a) ─eBGP─ RT02(RR, AS-b) ─iBGP(Lo0)─ RT03(client, AS-b)
                         └──────────iBGP(Lo0)─ RT04(client, AS-b)
  - AS-b 内 OSPF(Lo0+区間)・iBGP は Loopback0 ピア(update-source)・RT02 が next-hop-self。
  - RT01 は AS-a 単独で eBGP 直結ピア。テストは各ルータの Loopback1。
  - BGP は MP-BGP(address-family ipv4 unicast)書式。

故障カタログ:
  missing_rr_client        : RT02 の route-reflector-client 欠落→client 同士が相互到達不可（RR核心）
  missing_nexthop_self     : RT02 の next-hop-self 欠落→client が eBGP発(RT01)の next-hop 解決不可
  transit_ospf_break       : RT02-RT04 の OSPF 区間欠落→RT04 Lo0 不達→iBGP断/next-hop不達
  ibgp_missing_update_source: RT03 の iBGP update-source 欠落→RT03 の iBGP 断
  ibgp_wrong_remoteas      : RT04 の iBGP remote-as 誤り→RT04 の iBGP 断
  missing_network          : RT03 の network 欠落→RT03 Lo1 を起源広告しない
  ebgp_remoteas            : RT01-RT02 eBGP remote-as 誤り→RT01 Lo1 が AS-b に入らない

使い方: gen_bgp_rrts.py --repo . --seed <int> [--faults N] [--decoys K]
"""
import argparse
import json
import os
import random

import yaml


FAULTS = ["missing_rr_client", "missing_nexthop_self", "transit_ospf_break",
          "ibgp_missing_update_source", "ibgp_wrong_remoteas",
          "missing_network", "ebgp_remoteas"]
FAULT_DIFFICULTY = {f: 4 for f in FAULTS}
FAULT_DIFFICULTY["missing_rr_client"] = 5
FAULT_DIFFICULTY["missing_nexthop_self"] = 5


def rand_values(rnd):
    asn, used = {}, set()
    for r in ("RT01", "RT02"):
        while True:
            v = rnd.randint(64512, 65534)
            if v not in used:
                used.add(v); asn[r] = v; break
    asn["RT03"] = asn["RT04"] = asn["RT02"]
    lo, lo1, usedk = {}, {}, set()              # Lo0(peering) と Lo1(BGP) は全 8 個別値
    for d in (lo, lo1):
        for r in ("RT01", "RT02", "RT03", "RT04"):
            while True:
                k = rnd.randint(1, 99)
                if k != 10 and k not in usedk:
                    usedk.add(k); d[r] = f"{k}.{k}.{k}.{k}"; break
    seg, usedseg = {}, set()
    for name in ("12", "23", "24"):
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in usedseg:
                usedseg.add((p, q)); seg[name] = f"10.{p}.{q}"; break
    return asn, lo, lo1, seg


def select_faults(rnd, n):
    pool = list(FAULTS); rnd.shuffle(pool)
    return pool[:max(0, min(n, len(pool)))]


def select_decoys(rnd, k):
    decoys, attempts = [], 0
    kinds = ["ghost_neighbor", "unused_prefix_list", "comment"]
    nodes = ["RT01", "RT02", "RT03", "RT04"]
    while len(decoys) < k and attempts < 200:
        attempts += 1
        dt = rnd.choice(kinds); R = rnd.choice(nodes)
        if dt == "ghost_neighbor":
            ip = f"192.0.2.{rnd.randint(1, 254)}"
            decoys.append({"type": dt, "node": R, "where": "session",
                           "lines": [f"neighbor {ip} remote-as 65000"]})
        elif dt == "unused_prefix_list":
            decoys.append({"type": dt, "node": R, "where": "global",
                           "lines": ["ip prefix-list DECOY-LEGACY seq 5 permit 10.20.0.0/16 le 32"]})
        else:
            decoys.append({"type": dt, "node": R, "where": "session",
                           "lines": ["! legacy iBGP note - review later"]})
    return decoys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=1)
    ap.add_argument("--decoys", type=int, default=0)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    routers = ["RT01", "RT02", "RT03", "RT04"]
    asn, lo, lo1, seg = rand_values(rnd)
    faults = select_faults(rnd, a.faults)
    decoys = select_decoys(rnd, a.decoys)
    has = set(faults)

    ip12 = {"RT01": f"{seg['12']}.1", "RT02": f"{seg['12']}.2"}
    ip23 = {"RT02": f"{seg['23']}.1", "RT03": f"{seg['23']}.2"}
    ip24 = {"RT02": f"{seg['24']}.1", "RT04": f"{seg['24']}.2"}

    sess_decoy, glob_decoy = {}, {}
    for d in decoys:
        (sess_decoy if d["where"] == "session" else glob_decoy).setdefault(d["node"], []).extend(d["lines"])

    def af(R):
        return [f"router bgp {asn[R]}", "address-family ipv4 unicast"]

    def cfg_RT01():                                # AS-a edge（OSPF/Lo0 不要・eBGP 直結）
        L = [f"! RT01 (AS {asn['RT01']} / eBGP edge)",
             "interface Loopback1", f" ip address {lo1['RT01']} 255.255.255.255", "!",
             "interface {{ links[0] }}", f" ip address {ip12['RT01']} 255.255.255.252", " no shutdown", "!"]
        ras = asn["RT02"] + (1 if "ebgp_remoteas" in has else 0)
        B = [f"router bgp {asn['RT01']}", f" bgp router-id {lo1['RT01']}",
             " no bgp default ipv4-unicast", f" neighbor {ip12['RT02']} remote-as {ras}"]
        B += [f" {x}" for x in sess_decoy.get("RT01", [])]
        B += [" address-family ipv4 unicast", f"  neighbor {ip12['RT02']} activate",
              f"  network {lo1['RT01']} mask 255.255.255.255", " exit-address-family"]
        return L + B + ["!"] + glob_decoy.get("RT01", [])

    def cfg_RR():                                  # RT02
        R = "RT02"
        L = [f"! {R} (AS {asn[R]} / Route Reflector)",
             "interface Loopback0", f" ip address {lo[R]} 255.255.255.255", "!",
             "interface Loopback1", f" ip address {lo1[R]} 255.255.255.255", "!",
             "interface {{ links[0] }}", f" ip address {ip12['RT02']} 255.255.255.252", " no shutdown", "!",
             "interface {{ links[1] }}", f" ip address {ip23['RT02']} 255.255.255.252", " no shutdown", "!",
             "interface {{ links[2] }}", f" ip address {ip24['RT02']} 255.255.255.252", " no shutdown", "!"]
        o = ["router ospf 1", f" network {lo[R]} 0.0.0.0 area 0",
             f" network {seg['23']}.0 0.0.0.3 area 0"]
        if "transit_ospf_break" not in has:
            o.append(f" network {seg['24']}.0 0.0.0.3 area 0")
        L += o + ["!"]
        clients = ("RT03", "RT04")
        B = [f"router bgp {asn[R]}", f" bgp router-id {lo[R]}", " no bgp default ipv4-unicast",
             f" neighbor {ip12['RT01']} remote-as {asn['RT01']}"]
        for cl in clients:
            B += [f" neighbor {lo[cl]} remote-as {asn[R]}",
                  f" neighbor {lo[cl]} update-source Loopback0"]
        B += [f" {x}" for x in sess_decoy.get(R, [])]
        B.append(" address-family ipv4 unicast")
        B.append(f"  neighbor {ip12['RT01']} activate")
        for cl in clients:
            B.append(f"  neighbor {lo[cl]} activate")
            if "missing_nexthop_self" not in has:
                B.append(f"  neighbor {lo[cl]} next-hop-self")
            if "missing_rr_client" not in has:
                B.append(f"  neighbor {lo[cl]} route-reflector-client")
        B.append(f"  network {lo1[R]} mask 255.255.255.255")
        B.append(" exit-address-family")
        return L + B + ["!"] + glob_decoy.get(R, [])

    def cfg_client(R, myip, seg_n):
        L = [f"! {R} (AS {asn[R]} / RR client)",
             "interface Loopback0", f" ip address {lo[R]} 255.255.255.255", "!",
             "interface Loopback1", f" ip address {lo1[R]} 255.255.255.255", "!",
             "interface {{ links[0] }}", f" ip address {myip} 255.255.255.252", " no shutdown", "!",
             "router ospf 1", f" network {lo[R]} 0.0.0.0 area 0",
             f" network {seg[seg_n]}.0 0.0.0.3 area 0", "!"]
        ras = asn[R] + (1 if ("ibgp_wrong_remoteas" in has and R == "RT04") else 0)
        B = [f"router bgp {asn[R]}", f" bgp router-id {lo[R]}", " no bgp default ipv4-unicast",
             f" neighbor {lo['RT02']} remote-as {ras}"]
        if not ("ibgp_missing_update_source" in has and R == "RT03"):
            B.append(f" neighbor {lo['RT02']} update-source Loopback0")
        B += [f" {x}" for x in sess_decoy.get(R, [])]
        B += [" address-family ipv4 unicast", f"  neighbor {lo['RT02']} activate"]
        if not ("missing_network" in has and R == "RT03"):
            B.append(f"  network {lo1[R]} mask 255.255.255.255")
        B.append(" exit-address-family")
        return L + B + ["!"] + glob_decoy.get(R, [])

    cfgs = {"RT01": cfg_RT01(), "RT02": cfg_RR(),
            "RT03": cfg_client("RT03", ip23["RT03"], "23"),
            "RT04": cfg_client("RT04", ip24["RT04"], "24")}

    def fault_fix(ft):
        if ft == "missing_rr_client":
            return [{"node": "RT02", "parents": af("RT02"),
                     "lines": [f"neighbor {lo['RT03']} route-reflector-client",
                               f"neighbor {lo['RT04']} route-reflector-client"]}]
        if ft == "missing_nexthop_self":
            return [{"node": "RT02", "parents": af("RT02"),
                     "lines": [f"neighbor {lo['RT03']} next-hop-self",
                               f"neighbor {lo['RT04']} next-hop-self"]}]
        if ft == "transit_ospf_break":
            return [{"node": "RT02", "parents": "router ospf 1",
                     "lines": [f"network {seg['24']}.0 0.0.0.3 area 0"]}]
        if ft == "ibgp_missing_update_source":
            return [{"node": "RT03", "parents": f"router bgp {asn['RT03']}",
                     "lines": [f"neighbor {lo['RT02']} update-source Loopback0"]}]
        if ft == "ibgp_wrong_remoteas":
            return [{"node": "RT04", "parents": f"router bgp {asn['RT04']}",
                     "lines": [f"no neighbor {lo['RT02']} remote-as {asn['RT04'] + 1}",
                               f"neighbor {lo['RT02']} remote-as {asn['RT04']}",
                               f"neighbor {lo['RT02']} update-source Loopback0"]},
                    {"node": "RT04", "parents": af("RT04"),
                     "lines": [f"neighbor {lo['RT02']} activate"]}]
        if ft == "missing_network":
            return [{"node": "RT03", "parents": af("RT03"),
                     "lines": [f"network {lo1['RT03']} mask 255.255.255.255"]}]
        return [{"node": "RT01", "parents": f"router bgp {asn['RT01']}",
                 "lines": [f"no neighbor {ip12['RT02']} remote-as {asn['RT02'] + 1}",
                           f"neighbor {ip12['RT02']} remote-as {asn['RT02']}"]},
                {"node": "RT01", "parents": af("RT01"),
                 "lines": [f"neighbor {ip12['RT02']} activate"]}]

    fixes = [fx for ft in faults for fx in fault_fix(ft)]
    diff = (min(5, max((FAULT_DIFFICULTY[f] for f in faults), default=3))
            + (1 if len(faults) > 1 else 0) + (1 if decoys else 0)) if faults else 3
    diff = min(5, diff)

    prob_id = f"GEN-BGPRR-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id, "title": f"BGP Route Reflector TS (seed={a.seed})",
               "exam": "ENARSI", "topics": ["bgp", "route-reflector", "ibgp", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": routers, "points": 100, "access": "ssh",
               "lab": {"links": [{"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                                 {"a": "RT02", "a_if": 1, "b": "RT03", "b_if": 0},
                                 {"a": "RT02", "a_if": 2, "b": "RT04", "b_if": 0}],
                       "positions": {"RT01": [-480, -200], "RT02": [-160, -200],
                                     "RT03": [160, -350], "RT04": [160, -50]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_rrts.py) seed={a.seed} faults={len(faults)}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for R in routers:
        with open(f"{pdir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(cfgs[R]) + "\n")

    checks = []
    pairs = [(X, Y) for X in routers for Y in routers if X != Y]
    for (X, Y) in pairs:                            # テストは Loopback1（BGP 専用）
        checks.append({"name": f"{X}: {lo1[Y]}/32 を RIB に学習", "node": X,
                       "command": "show ip route", "parser": "show ip route",
                       "find": "vrf.*.address_family.*.routes.*",
                       "match": {"route": f"{lo1[Y]}/32"}, "points": 6})
    sess = [("RT01", ip12["RT02"], "eBGP RT01-RT02", 10),
            ("RT02", lo["RT03"], "iBGP RT02-RT03(client)", 9),
            ("RT02", lo["RT04"], "iBGP RT02-RT04(client)", 9)]
    for (X, peer, label, pts) in sess:
        checks.append({"name": f"{label}: Established", "node": X,
                       "command": f"show ip bgp neighbors {peer}",
                       "raw": [{"regex": "BGP state += +Established"}], "points": pts})
    grading = {"problem": prob_id, "total_points": 100, "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_rrts.py) seed={a.seed}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    sym = {"missing_rr_client": ("RT03", "RT04"), "ibgp_wrong_remoteas": ("RT03", "RT04"),
           "ibgp_missing_update_source": ("RT04", "RT03"), "missing_network": ("RT04", "RT03"),
           "missing_nexthop_self": ("RT03", "RT01"), "transit_ospf_break": ("RT03", "RT04"),
           "ebgp_remoteas": ("RT03", "RT01")}
    rep = sym.get(faults[0], ("RT03", "RT04")) if faults else ("RT03", "RT04")
    json.dump({"count": len(faults), "faults": faults,
               "values": {"asn": asn, "lo0": lo, "lo1": lo1, "seg": seg}},
              open(f"{pdir}/solution/fault.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"fixes": fixes}, open(f"{pdir}/solution/fix.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"decoys": decoys}, open(f"{pdir}/solution/decoys.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"reported_symptom": {"src": rep[0], "dst": rep[1], "dst_loopback": f"{lo1[rep[1]]}/32"},
               "fault_count": len(faults), "decoy_count": len(decoys)},
              open(f"{pdir}/solution/impact.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/README.md", "w", encoding="utf-8") as f:
        f.write("# 採点者専用\n\n" + f"- AS:{asn}\n- Lo0(peering/OSPF):{lo}\n- Lo1(BGP/test):{lo1}\n"
                + f"- 故障:{faults}\n- おとり:{[(d['type'], d['node']) for d in decoys]}\n")

    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 障害対応 {prob_id} : BGP Route Reflector / iBGP（4 ルータ）\n\n")
        f.write("## 状況\nAS-b(RT02/RT03/RT04) は iBGP を **Route Reflector(RT02)** で構成"
                "（RT03/RT04 は RT02 の client・client 同士は直接ピアしない・iBGP は Loopback0 ピア）。"
                "RT01(AS-a) と RT02 が eBGP。各ルータの **Loopback1 を BGP で広告**（Loopback0/区間は OSPF）。"
                "MP-BGP 書式。ある変更作業の後から到達性の不具合が報告されている。\n\n")
        f.write("## 受付チケット\n")
        f.write(f"> 「**{rep[0]}** から **{rep[1]}** の Loopback1 (`{lo1[rep[1]]}/32`) に到達できない」"
                "という申告がありました。\n>\n> 切り分けて原因を特定し、恒久的に復旧してください。"
                "原因は 1 か所とは限りません。\n\n")
        f.write("## 構成台帳\n| ルータ | AS | 役割 | Loopback1(BGP) |\n|---|---|---|---|\n")
        rolemap = {"RT01": "eBGP edge", "RT02": "Route Reflector", "RT03": "RR client", "RT04": "RR client"}
        for r in routers:
            f.write(f"| {r} | {asn[r]} | {rolemap[r]} | `{lo1[r]}/32` |\n")
        f.write("\n※ `show ip bgp summary`(セッション) / `show ip bgp <prefix>`(RR に来ているか・"
                "best か・next-hop accessible か) / `show ip route` で切り分けること。"
                "**セッションが全て Established・RR に経路が有っても、反射(reflection)が効かなければ "
                "client 同士は学習できない**。設定変更後は反射を反映するため `clear ip bgp *` が要る場合がある。\n")
        f.write("\n## 完了条件\nすべてのルータが、他の全ルータの Loopback1 を RIB に学習している状態。\n\n")
        f.write(f"## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    print(f"wrote {prob_id}: faults={len(faults)} {faults}, decoys={len(decoys)}, "
          f"AS={asn['RT01']}/{asn['RT02']}, 難易度={diff}")


if __name__ == "__main__":
    main()
