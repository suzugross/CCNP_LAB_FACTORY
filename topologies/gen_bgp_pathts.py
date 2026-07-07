#!/usr/bin/env python3
"""BGP 経路選択トラブルシュート生成器（デュアルホーム / 「届くが経路が違う」を採点）。

冗長（ダイヤモンド）トポロジで、到達性ではなく **path selection** を問う。
正しい状態では RT01↔RT04 のトラフィックは PRIMARY(RT02) 経由・BACKUP(RT03) は予備。
故障は local-preference / AS-path prepend の欠落・誤適用で、到達はするが予備(RT03)に
寄ってしまう。採点は gen_pathctrl と同型の raw（PRIMARY向き next-hop 有・BACKUP向き無）。

トポロジ（固定・4 ノード / 4 AS / 各次数2の閉路）:
  RT01(AS-A) ─┬─ RT02(AS-B PRIMARY) ─┬─ RT04(AS-D, prefix 起源)
              └─ RT03(AS-C BACKUP)  ─┘
  全 eBGP・全ルータが network で自 Loopback を起源広告。
  - 往き(RT01→RT04Lo): RT01 が neighbor RT02 inbound route-map で local-preference 200。
  - 帰り(RT04→RT01Lo): RT03 が neighbor RT04 outbound route-map で as-path prepend（自AS×2）。
  BGP は MP-BGP(address-family ipv4 unicast)書式。route-map 適用は AF 配下。

故障カタログ（経路選択層）:
  fwd_lp_missing       : RT01 の LP 設定が無い→往きが ECMP/予備
  fwd_lp_wrong_nbr     : LP200 を RT03(予備)に適用→往きが予備
  fwd_routemap_unapplied: route-map は定義済だが neighbor に未適用→往きが ECMP
  ret_prepend_missing  : RT03 の prepend 無し→帰りが ECMP/予備
  ret_prepend_wrong_nbr: prepend を誤った neighbor(RT01)に適用→帰りが ECMP

出力: problems/GEN-BGPPATH-<seed>/（OSPF版TS同様 solution/ に答えを隔離）

使い方: gen_bgp_pathts.py --repo . --seed <int> [--faults N] [--decoys K]
"""
import argparse
import json
import os
import random

import yaml


FAULTS = ["fwd_lp_missing", "fwd_lp_wrong_nbr", "fwd_routemap_unapplied",
          "ret_prepend_missing", "ret_prepend_wrong_nbr"]


def rand_values(rnd):
    asn, used = {}, set()
    for r in ("RT01", "RT02", "RT03", "RT04"):     # 4 AS すべて別
        while True:
            v = rnd.randint(64512, 65534)
            if v not in used:
                used.add(v); asn[r] = v; break
    lo, usedlo = {}, set()
    for r in ("RT01", "RT02", "RT03", "RT04"):
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in usedlo:
                usedlo.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    # 予備(RT03)の router-id を主(RT02)より低くする。bgp bestpath compare-routerid と
    # 併せ、優先制御が無いと既定で RT03(予備)が選ばれる＝故障(制御欠落/誤適用)を決定的にする。
    if int(lo["RT03"].split(".")[0]) > int(lo["RT02"].split(".")[0]):
        lo["RT02"], lo["RT03"] = lo["RT03"], lo["RT02"]
    seg, usedseg = {}, set()
    for name in ("12", "13", "24", "34"):
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
    kinds = ["ghost_neighbor", "unused_route_map", "comment"]
    nodes = ["RT01", "RT02", "RT03", "RT04"]
    while len(decoys) < k and attempts < 200:
        attempts += 1
        dt = rnd.choice(kinds); R = rnd.choice(nodes)
        if dt == "ghost_neighbor":
            ip = f"192.0.2.{rnd.randint(1, 254)}"
            decoys.append({"type": dt, "node": R, "where": "session",
                           "lines": [f"neighbor {ip} remote-as 65000"]})
        elif dt == "unused_route_map":
            decoys.append({"type": dt, "node": R, "where": "global",
                           "lines": ["route-map DECOY-OLD permit 10", " set metric 50"]})
        else:
            decoys.append({"type": dt, "node": R, "where": "session",
                           "lines": ["! legacy policy note - review later"]})
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
    asn, lo, seg = rand_values(rnd)
    faults = select_faults(rnd, a.faults)
    decoys = select_decoys(rnd, a.decoys)
    has = set(faults)

    # リンク両端 IP（a=.1 / b=.2）。slot: RT01:0→RT02,1→RT03 / RT02:0→RT01,1→RT04 /
    #                                  RT03:0→RT01,1→RT04 / RT04:0→RT02,1→RT03
    ip = {"RT01-RT02": (f"{seg['12']}.1", f"{seg['12']}.2"),
          "RT01-RT03": (f"{seg['13']}.1", f"{seg['13']}.2"),
          "RT02-RT04": (f"{seg['24']}.1", f"{seg['24']}.2"),
          "RT03-RT04": (f"{seg['34']}.1", f"{seg['34']}.2")}
    # 各ルータの (slot, 自IP, 対向, 対向IP, 対向AS)
    intf = {
        "RT01": [(0, ip["RT01-RT02"][0], "RT02", ip["RT01-RT02"][1], asn["RT02"]),
                 (1, ip["RT01-RT03"][0], "RT03", ip["RT01-RT03"][1], asn["RT03"])],
        "RT02": [(0, ip["RT01-RT02"][1], "RT01", ip["RT01-RT02"][0], asn["RT01"]),
                 (1, ip["RT02-RT04"][0], "RT04", ip["RT02-RT04"][1], asn["RT04"])],
        "RT03": [(0, ip["RT01-RT03"][1], "RT01", ip["RT01-RT03"][0], asn["RT01"]),
                 (1, ip["RT03-RT04"][0], "RT04", ip["RT03-RT04"][1], asn["RT04"])],
        "RT04": [(0, ip["RT02-RT04"][1], "RT02", ip["RT02-RT04"][0], asn["RT02"]),
                 (1, ip["RT03-RT04"][1], "RT03", ip["RT03-RT04"][0], asn["RT03"])],
    }

    # path-control の状態（健全→故障で変化）
    rt01_primary_defined = True
    rt01_rmin = {"RT02": "PRIMARY", "RT03": None}
    rt03_backup_defined = True
    rt03_rmout = {"RT04": "BACKUP", "RT01": None}
    if "fwd_lp_missing" in has:
        rt01_primary_defined = False; rt01_rmin["RT02"] = None
    if "fwd_routemap_unapplied" in has:
        rt01_rmin["RT02"] = None                     # 定義はある・未適用
    if "fwd_lp_wrong_nbr" in has:
        rt01_rmin["RT02"] = None; rt01_rmin["RT03"] = "PRIMARY"
    if "ret_prepend_missing" in has:
        rt03_backup_defined = False; rt03_rmout["RT04"] = None
    if "ret_prepend_wrong_nbr" in has:
        rt03_rmout["RT04"] = None; rt03_rmout["RT01"] = "BACKUP"

    sess_decoy, glob_decoy = {}, {}
    for d in decoys:
        (sess_decoy if d["where"] == "session" else glob_decoy).setdefault(d["node"], []).extend(d["lines"])

    def render(R):
        L = [f"! {R} (AS {asn[R]})", "interface Loopback0",
             f" ip address {lo[R]} 255.255.255.255", "!"]
        for (s, myip, nb, nbip, nbas) in intf[R]:
            L += [f"interface {{{{ links[{s}] }}}}", f" ip address {myip} 255.255.255.252",
                  " no shutdown", "!"]
        B = [f"router bgp {asn[R]}", f" bgp router-id {lo[R]}", " no bgp default ipv4-unicast",
             " bgp bestpath compare-routerid"]
        for (s, myip, nb, nbip, nbas) in intf[R]:
            B.append(f" neighbor {nbip} remote-as {nbas}")
        B += [f" {x}" for x in sess_decoy.get(R, [])]
        B.append(" address-family ipv4 unicast")
        for (s, myip, nb, nbip, nbas) in intf[R]:
            B.append(f"  neighbor {nbip} activate")
            if R == "RT01" and rt01_rmin.get(nb):
                B.append(f"  neighbor {nbip} route-map {rt01_rmin[nb]} in")
            if R == "RT03" and rt03_rmout.get(nb):
                B.append(f"  neighbor {nbip} route-map {rt03_rmout[nb]} out")
        B.append(f"  network {lo[R]} mask 255.255.255.255")
        B.append(" exit-address-family")
        L += B + ["!"]
        # route-map 定義（グローバル）
        if R == "RT01" and rt01_primary_defined:
            L += ["route-map PRIMARY permit 10", " set local-preference 200", "!"]
        if R == "RT03" and rt03_backup_defined:
            L += ["route-map BACKUP permit 10", f" set as-path prepend {asn['RT03']} {asn['RT03']}", "!"]
        L += glob_decoy.get(R, [])
        return L

    cfgs = {R: render(R) for R in routers}

    # ---- 故障 → 修正 ----
    def af(R):
        return [f"router bgp {asn[R]}", "address-family ipv4 unicast"]
    nh = {"RT02_at_RT01": ip["RT01-RT02"][1], "RT03_at_RT01": ip["RT01-RT03"][1],
          "RT01_at_RT03": ip["RT01-RT03"][0], "RT04_at_RT03": ip["RT03-RT04"][1]}

    def fault_fix(ft):
        if ft == "fwd_lp_missing":
            return [{"node": "RT01", "parents": None,
                     "lines": ["route-map PRIMARY permit 10", " set local-preference 200"]},
                    {"node": "RT01", "parents": af("RT01"),
                     "lines": [f"neighbor {nh['RT02_at_RT01']} route-map PRIMARY in"]}]
        if ft == "fwd_routemap_unapplied":
            return [{"node": "RT01", "parents": af("RT01"),
                     "lines": [f"neighbor {nh['RT02_at_RT01']} route-map PRIMARY in"]}]
        if ft == "fwd_lp_wrong_nbr":
            return [{"node": "RT01", "parents": af("RT01"),
                     "lines": [f"no neighbor {nh['RT03_at_RT01']} route-map PRIMARY in",
                               f"neighbor {nh['RT02_at_RT01']} route-map PRIMARY in"]}]
        if ft == "ret_prepend_missing":
            return [{"node": "RT03", "parents": None,
                     "lines": ["route-map BACKUP permit 10",
                               f" set as-path prepend {asn['RT03']} {asn['RT03']}"]},
                    {"node": "RT03", "parents": af("RT03"),
                     "lines": [f"neighbor {nh['RT04_at_RT03']} route-map BACKUP out"]}]
        # ret_prepend_wrong_nbr
        return [{"node": "RT03", "parents": af("RT03"),
                 "lines": [f"no neighbor {nh['RT01_at_RT03']} route-map BACKUP out",
                           f"neighbor {nh['RT04_at_RT03']} route-map BACKUP out"]}]

    fixes = []
    for ft in faults:
        for fx in fault_fix(ft):
            if fx["parents"] is None:
                fx = {"node": fx["node"], "lines": fx["lines"]}   # global（parents 省略）
            fixes.append(fx)
    diff = min(5, 4 + (1 if len(faults) > 1 else 0) + (1 if decoys else 0))

    # ---- 出力 ----
    prob_id = f"GEN-BGPPATH-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id, "title": f"BGP 経路選択TS (dual-home, seed={a.seed})",
               "exam": "ENARSI", "topics": ["bgp", "path-selection", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": routers, "points": 100, "access": "ssh",
               "lab": {"links": [{"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                                 {"a": "RT01", "a_if": 1, "b": "RT03", "b_if": 0},
                                 {"a": "RT02", "a_if": 1, "b": "RT04", "b_if": 0},
                                 {"a": "RT03", "a_if": 1, "b": "RT04", "b_if": 1}],
                       "positions": {"RT01": [-480, -200], "RT02": [0, -380],
                                     "RT03": [0, -20], "RT04": [480, -200]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_pathts.py) seed={a.seed} faults={len(faults)}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for R in routers:
        with open(f"{pdir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(cfgs[R]) + "\n")

    model = {"loopbacks": {r: lo[r] for r in routers},
             "links": [{"a": "RT01", "a_ip": ip["RT01-RT02"][0], "b": "RT02", "b_ip": ip["RT01-RT02"][1]},
                       {"a": "RT01", "a_ip": ip["RT01-RT03"][0], "b": "RT03", "b_ip": ip["RT01-RT03"][1]},
                       {"a": "RT02", "a_ip": ip["RT02-RT04"][0], "b": "RT04", "b_ip": ip["RT02-RT04"][1]},
                       {"a": "RT03", "a_ip": ip["RT03-RT04"][0], "b": "RT04", "b_ip": ip["RT03-RT04"][1]}]}
    checks = [
        {"name": f"往き: RT01→{lo['RT04']} は PRIMARY(RT02)経由（予備RT03を使わない）",
         "node": "RT01", "command": f"show ip route {lo['RT04']}",
         "raw": [{"contains": ip["RT01-RT02"][1]}, {"not_contains": ip["RT01-RT03"][1]}], "points": 25},
        {"name": f"帰り: RT04→{lo['RT01']} は PRIMARY(RT02)経由（予備RT03を使わない）",
         "node": "RT04", "command": f"show ip route {lo['RT01']}",
         "raw": [{"contains": ip["RT02-RT04"][0]}, {"not_contains": ip["RT03-RT04"][0]}], "points": 25},
    ]
    for (X, peer, label) in [("RT01", ip["RT01-RT02"][1], "eBGP RT01-RT02"),
                             ("RT01", ip["RT01-RT03"][1], "eBGP RT01-RT03"),
                             ("RT04", ip["RT02-RT04"][0], "eBGP RT02-RT04"),
                             ("RT04", ip["RT03-RT04"][0], "eBGP RT03-RT04")]:
        checks.append({"name": f"{label}: Established", "node": X,
                       "command": f"show ip bgp neighbors {peer}",
                       "raw": [{"regex": "BGP state += +Established"}], "points": 5})
    grading = {"problem": prob_id, "total_points": 100, "defaults": {"genie_os": "iosxe"},
               "model": model,
               "invariants": [{"type": "reachability_all", "name": "全Loopback到達", "points": 20},
                              {"type": "loop_free", "name": "転送ループ不在", "points": 10}],
               "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_pathts.py) seed={a.seed}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    json.dump({"count": len(faults), "faults": faults,
               "values": {"asn": asn, "lo": lo, "seg": seg}},
              open(f"{pdir}/solution/fault.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"fixes": fixes}, open(f"{pdir}/solution/fix.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"decoys": decoys}, open(f"{pdir}/solution/decoys.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/README.md", "w", encoding="utf-8") as f:
        f.write("# 採点者専用\n\n" + f"- AS:{asn}\n- Lo:{lo}\n- 故障:{faults}\n"
                + f"- おとり:{[(d['type'], d['node']) for d in decoys]}\n")

    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 障害対応 {prob_id} : BGP 経路選択（デュアルホーム / 4 ルータ）\n\n")
        f.write("## 状況\nRT01(AS-A) は RT02(AS-B) と RT03(AS-C) の 2 経路で RT04(AS-D) に接続する"
                "デュアルホーム構成（全 eBGP・MP-BGP 書式）。\n\n")
        f.write("## ポリシー（あるべき姿）\n"
                f"- **RT01 ↔ RT04（`{lo['RT04']}` / `{lo['RT01']}`）のトラフィックは PRIMARY=RT02 経由**。"
                "RT03 は **バックアップ**（RT02 障害時のみ使用）。\n"
                "- 到達性自体は保たれているが、**現在は意図した PRIMARY 経路を通っていない**との報告。\n\n")
        f.write("## 構成台帳\n| ルータ | AS | Loopback |\n|---|---|---|\n")
        for r in routers:
            f.write(f"| {r} | {asn[r]} | `{lo[r]}/32` |\n")
        f.write("\n※ どの属性(local-preference / AS-path 等)で制御すべきか、誤りの場所/種類/件数は非公開。"
                "`show ip bgp {0}` / `show ip route {0}` で **best-path とその理由** を確認して切り分けること。\n".format(lo['RT04']))
        f.write("\n## 完了条件\n往き(RT01→RT04Lo)・帰り(RT04→RT01Lo) とも **RT02 経由（単一経路）** で、"
                "全 Loopback への到達性は維持されていること。\n\n")
        f.write(f"## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    print(f"wrote {prob_id}: faults={len(faults)} {faults}, decoys={len(decoys)}, "
          f"AS={[asn[r] for r in routers]}, 難易度={diff}")


if __name__ == "__main__":
    main()
