#!/usr/bin/env python3
"""相互再配送(OSPF⇄EIGRP)トラブルシュート生成器（群3/Phase F）。

正準トポロジ(値を seed ランダム化・ENARSI-REDIST-LOOP-01 を踏襲):
  OSPF area0 = {RT01(内部), RT02, RT03(境界)}
  EIGRP AS   = {RT02, RT03(境界), RT04(内部)}
  境界 RT02/RT03 が相互再配送。EIGRP 外部 AD=95(<OSPF110) を固定(会社ポリシー)。
  links: RT01-RT02(OSPF) / RT01-RT03(OSPF) / RT02-RT03(EIGRP境界間) / RT02-RT04(EIGRP) / RT03-RT04(EIGRP)

健全な相互再配送は「双方向 redistribute ＋ タグで自ドメイン発を識別し境界 EIGRP inbound で遮断」
(SET_TAG/BLOCK_TAG)＝最短かつループ無し。初期 config は **故障1種を注入した状態**。

故障カタログ(--fault, 既定 seed ランダム):
  no_tag             : 双方向再配送はあるがタグ/フィルタ無し→OSPF発をEIGRP外部(95)で拾い次善(遠回り)。
  missing_o2e        : OSPF→EIGRP 再配送欠落→EIGRP域(RT04)がOSPF Loopback未学習(不到達)。
  missing_e2o        : EIGRP→OSPF 再配送欠落→OSPF域(RT01)がEIGRP Loopback未学習(不到達)。
  missing_seed_metric: OSPF→EIGRP に seed metric 無し→無限大で未注入(EIGRP域がOSPF未学習)。

採点(netmodel 大域不変条件): reachability_all / loop_free / optimal(ドメイン内宛先) ＋ 方向別 raw(D EX/O E2)。
出力: problems/GEN-REDIST-<seed>/ {problem.yml, initial/*.cfg.j2, grading.yml,
       solution/{fault.json,fix.json}}。fix.json は fix_generated.yml 互換。
使い方: gen_redist_mutual_ts.py --repo . --seed <int> [--fault <name>]
"""
import argparse
import json
import os
import random

import yaml

BOUNDARIES = ["RT02", "RT03"]
TAG = 110                       # OSPF発経路に付けるタグ
METRIC = "100000 100 255 1 1500"
FAULTS = ["no_tag", "missing_o2e", "missing_e2o", "missing_seed_metric"]
DIFFICULTY = {"no_tag": 5, "missing_o2e": 4, "missing_e2o": 4, "missing_seed_metric": 5}


def rand_values(rnd):
    used = set()
    lo = {}
    for r in ["RT01", "RT02", "RT03", "RT04"]:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    useg = set()
    seg = {}
    for name in ["12", "13", "23", "24", "34"]:
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in useg:
                useg.add((p, q)); seg[name] = f"10.{p}.{q}"; break
    return lo, seg, rnd.randint(64512, 65534), 1


# ---- 境界の再配送ブロック（初期=故障注入状態） ----
def boundary_blocks(fault, AS):
    """(global_lines, ospf_lines, eigrp_lines) を返す（初期 config 用）。"""
    rmaps = ["route-map SET_TAG permit 10", f" set tag {TAG}",
             "route-map BLOCK_TAG deny 10", f" match tag {TAG}",
             "route-map BLOCK_TAG permit 20"]
    o2e_ok = [f"redistribute ospf 1 metric {METRIC} route-map SET_TAG",
              "distribute-list route-map BLOCK_TAG in"]
    e2o = ["redistribute eigrp {AS} subnets".format(AS=AS)]
    if fault == "no_tag":               # タグ/フィルタ無し（双方向はある）
        return [], e2o, [f"redistribute ospf 1 metric {METRIC}"]
    if fault == "missing_o2e":          # OSPF→EIGRP 欠落
        return [], e2o, []
    if fault == "missing_e2o":          # EIGRP→OSPF 欠落
        return rmaps, [], o2e_ok
    if fault == "missing_seed_metric":  # seed metric 欠落
        return rmaps, e2o, ["redistribute ospf 1 route-map SET_TAG",
                            "distribute-list route-map BLOCK_TAG in"]
    raise SystemExit(f"unknown fault {fault}")


def boundary_fix(fault, node, AS):
    """故障を健全(双方向＋タグ＋seed metric)へ是正する fix エントリ列。"""
    # route-map は複数行・順序維持。global 定義をまとめて1エントリに（parents 省略=global）。
    rmap_def = {"node": node, "lines": [
        "route-map SET_TAG permit 10", f" set tag {TAG}",
        "route-map BLOCK_TAG deny 10", f" match tag {TAG}",
        "route-map BLOCK_TAG permit 20"]}
    eigrp_correct = {"node": node, "parents": f"router eigrp {AS}",
                     "lines": ["no redistribute ospf 1",
                               f"redistribute ospf 1 metric {METRIC} route-map SET_TAG",
                               "distribute-list route-map BLOCK_TAG in"]}
    if fault == "no_tag":
        return [rmap_def, eigrp_correct]
    if fault == "missing_o2e":
        return [rmap_def,
                {"node": node, "parents": f"router eigrp {AS}",
                 "lines": [f"redistribute ospf 1 metric {METRIC} route-map SET_TAG",
                           "distribute-list route-map BLOCK_TAG in"]}]
    if fault == "missing_e2o":
        return [{"node": node, "parents": "router ospf 1",
                 "lines": [f"redistribute eigrp {AS} subnets"]}]
    if fault == "missing_seed_metric":
        return [{"node": node, "parents": f"router eigrp {AS}",
                 "lines": ["no redistribute ospf 1",
                           f"redistribute ospf 1 metric {METRIC} route-map SET_TAG"]}]
    return []


def render(node, lo, seg, AS, pid, fault):
    L = [f"! {node} 初期構成 (相互再配送TS・故障注入済)",
         "interface Loopback0", f" ip address {lo[node]} 255.255.255.255", "!"]
    # IF とルーティング定義はノード役割ごと
    if node == "RT01":                  # OSPF 内部
        for s, sg in [(0, seg["12"]), (1, seg["13"])]:
            L += [f"interface {{{{ links[{s}] }}}}", f" ip address {sg}.1 255.255.255.252",
                  " no shutdown", "!"]
        L += [f"router ospf {pid}", f" network {lo[node]} 0.0.0.0 area 0",
              f" network {seg['12']}.0 0.0.0.3 area 0",
              f" network {seg['13']}.0 0.0.0.3 area 0", "!"]
        return L
    if node == "RT04":                  # EIGRP 内部
        for s, sg in [(0, seg["24"]), (1, seg["34"])]:
            L += [f"interface {{{{ links[{s}] }}}}", f" ip address {sg}.2 255.255.255.252",
                  " no shutdown", "!"]
        L += [f"router eigrp {AS}", f" network {lo[node]} 0.0.0.0",
              f" network {seg['24']}.0 0.0.0.3", f" network {seg['34']}.0 0.0.0.3",
              " no auto-summary", "!"]
        return L
    # 境界 RT02/RT03
    gl, ospf_extra, eigrp_extra = boundary_blocks(fault, AS)
    if node == "RT02":
        ifs = [(0, f"{seg['12']}.2"), (1, f"{seg['23']}.1"), (2, f"{seg['24']}.1")]
        ospf_net = [f" network {lo[node]} 0.0.0.0 area 0", f" network {seg['12']}.0 0.0.0.3 area 0"]
        eigrp_net = [f" network {seg['23']}.0 0.0.0.3", f" network {seg['24']}.0 0.0.0.3"]
    else:  # RT03
        ifs = [(0, f"{seg['13']}.2"), (1, f"{seg['23']}.2"), (2, f"{seg['34']}.1")]
        ospf_net = [f" network {lo[node]} 0.0.0.0 area 0", f" network {seg['13']}.0 0.0.0.3 area 0"]
        eigrp_net = [f" network {seg['23']}.0 0.0.0.3", f" network {seg['34']}.0 0.0.0.3"]
    for s, ip in ifs:
        L += [f"interface {{{{ links[{s}] }}}}", f" ip address {ip} 255.255.255.252",
              " no shutdown", "!"]
    L += [f"router ospf {pid}"] + ospf_net + [f" {x}" for x in ospf_extra] + ["!"]
    L += [f"router eigrp {AS}"] + eigrp_net + [" no auto-summary", " distance eigrp 90 95"] \
        + [f" {x}" for x in eigrp_extra] + ["!"]
    if gl:                              # route-map(global)
        L += gl + ["!"]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    lo, seg, AS, pid = rand_values(rnd)
    fault = a.fault or rnd.choice(FAULTS)
    nodes = ["RT01", "RT02", "RT03", "RT04"]

    prob_id = f"GEN-REDIST-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"相互再配送 OSPF⇄EIGRP トラブルシュート (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["redistribution", "ospf", "eigrp", "troubleshooting", "generated"],
               "difficulty": DIFFICULTY[fault], "topology": "generated",
               "target_nodes": nodes, "points": 100, "access": "ssh",
               "lab": {"links": [
                   {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                   {"a": "RT01", "a_if": 1, "b": "RT03", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "RT03", "b_if": 1},
                   {"a": "RT02", "a_if": 2, "b": "RT04", "b_if": 0},
                   {"a": "RT03", "a_if": 2, "b": "RT04", "b_if": 1}],
                       "positions": {"RT01": [-480, -200], "RT02": [0, -380],
                                     "RT03": [0, -20], "RT04": [480, -200]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_mutual_ts.py) seed={a.seed} fault={fault}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    for n in nodes:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render(n, lo, seg, AS, pid, fault)) + "\n")

    # ---- 採点(netmodel model + invariants + 方向別 raw) ----
    model = {"loopbacks": {n: lo[n] for n in nodes},
             "links": [
                 {"a": "RT01", "a_ip": f"{seg['12']}.1", "b": "RT02", "b_ip": f"{seg['12']}.2"},
                 {"a": "RT01", "a_ip": f"{seg['13']}.1", "b": "RT03", "b_ip": f"{seg['13']}.2"},
                 {"a": "RT02", "a_ip": f"{seg['23']}.1", "b": "RT03", "b_ip": f"{seg['23']}.2"},
                 {"a": "RT02", "a_ip": f"{seg['24']}.1", "b": "RT04", "b_ip": f"{seg['24']}.2"},
                 {"a": "RT03", "a_ip": f"{seg['34']}.1", "b": "RT04", "b_ip": f"{seg['34']}.2"}]}
    rx01 = lo["RT01"].replace(".", r"\.")
    rx04 = lo["RT04"].replace(".", r"\.")
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "model": model,
               "invariants": [
                   {"type": "reachability_all", "name": "全ルータ間 Loopback 到達性", "points": 30},
                   {"type": "optimal", "name": "ドメイン内宛先(RT01/RT04)への最短転送(再配送由来の次善が無い)",
                    "points": 40,
                    "pairs": [["RT02", "RT01"], ["RT03", "RT01"], ["RT04", "RT01"],
                              ["RT01", "RT04"], ["RT02", "RT04"], ["RT03", "RT04"]]},
                   {"type": "loop_free", "name": "転送ループ無し", "points": 10}],
               "checks": [
                   {"name": f"RT04: {lo['RT01']}/32 を EIGRP外部(D EX)で学習(OSPF→EIGRP再配送)",
                    "node": "RT04", "command": "show ip route eigrp",
                    "raw": [{"regex": rf"D EX\s+{rx01}"}], "points": 10},
                   {"name": f"RT01: {lo['RT04']}/32 を OSPF外部(O E2)で学習(EIGRP→OSPF再配送)",
                    "node": "RT01", "command": "show ip route ospf",
                    "raw": [{"regex": rf"O E2\s+{rx04}"}], "points": 10}]}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_mutual_ts.py) seed={a.seed} fault={fault}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    fixes = [fx for n in BOUNDARIES for fx in boundary_fix(fault, n, AS)]
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"fault": fault, "as": AS, "loopbacks": lo}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)

    # ---- 症状ベース task.md ----
    sym = {"no_tag": f"一部の宛先へ**遠回り(次善経路)**になっている疑い（直結があるのに相手ドメイン経由）。",
           "missing_o2e": f"EIGRP側(RT04)から OSPF側の Loopback (`{lo['RT01']}`)へ到達できない。",
           "missing_e2o": f"OSPF側(RT01)から EIGRP側の Loopback (`{lo['RT04']}`)へ到達できない。",
           "missing_seed_metric": f"EIGRP側(RT04)から OSPF側の Loopback (`{lo['RT01']}`)へ到達できない。"}[fault]
    ledger = "\n".join(f"| {n} | `{lo[n]}/32` | {'OSPF' if n in ('RT01',) else 'EIGRP' if n=='RT04' else 'OSPF/EIGRP境界'} |" for n in nodes)
    task = f"""# 問題 {prob_id} : 相互再配送 OSPF⇄EIGRP トラブルシュート（難易度{DIFFICULTY[fault]}）

## 状況
OSPF ドメインと EIGRP ドメインを **境界2台(RT02,RT03)** が相互再配送している。
**会社ポリシーで EIGRP の AD は internal 90 / external 95 に固定(変更不可)**。
全ルータが全 Loopback へ**最短かつループ無し**で到達する状態へ復旧してください。

## トラブルチケット（代表症状）
> **{sym}**

## ルータ / Loopback / 役割
| ルータ | Loopback0 | ドメイン |
|--------|-----------|----------|
{ledger}

## 到達目標
- 全ルータ間で全 Loopback に到達（reachability）。
- **再配送由来の次善経路・ループが無い**（ドメイン内宛先 RT01/RT04 へ最短）。
- 原因の種類・場所は伏せています。`show ip route [ospf|eigrp]` / `show ip protocols` /
  `show route-map` などで切り分け。AD は変更不可（タグ/フィルタで制御）。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : fault={fault} AS={AS} diff={DIFFICULTY[fault]}")


if __name__ == "__main__":
    main()
