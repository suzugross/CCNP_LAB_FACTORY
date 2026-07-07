#!/usr/bin/env python3
"""相互再配送(RIP⇄OSPF)ルーティングループ・トラブルシュート生成器。

正準トポロジ(6台・値を seed ランダム化):
  RT06 --- RT01 --- RT02 --- RT04
             |                 |
             +------ RT03 --- RT05
  RIP v2 = {RT06(支社・プレフィックス源), RT01, RT02, RT03(境界)}
  OSPF a0 = {RT02, RT03(境界), RT04, RT05}
  境界 RT02/RT03 が相互再配送(二点相互再配送)。支社網 10.0.0.0/24, 10.0.1.0/24 は
  RT06 が広告 = RT01 は **RIP 学習**(直結でない)なのがループ成立の鍵。

ループのメカニズム(seed_loop):
  1. RT02 が RIP→OSPF 再配送 → LSA5 が OSPF 域へ。
  2. もう片方の境界(例 RT03)は O E2(AD110) < RIP(AD120) で **フィードバック経路を優先**
     → RT05 向きに転送(第1層: AD 問題)。
  3. RT03 が OSPF→RIP を seed metric 1 で再配送 → RT01 は支社網をネイティブ
     [120/1](RT06) とフィードバック [120/1](RT03) の **同値 ECMP** で保持
     (第2層: シードメトリック問題)。
  4. RT03 分岐に載ったトラフィックは RT01→RT03→RT05→RT04→RT02→RT01→… の定常ループ。

健全形(模範解): タグ両方向(RIP発=120/OSPF発=110)＋逆方向 deny ＋ seed metric 5 ＋
`distance ospf external 180`(境界の E2 優先を抑止=最短経路の回復)。タグだけでは
遠回りが残り、distance だけでも全不変条件は満たせる(いずれも合格=結果ベース採点)。

故障カタログ(--fault, 既定 seed ランダム):
  seed_loop          : タグ無し＋OSPF→RIP seed=1 → RT01 で ECMP 同値タイ→**定常転送ループ**。
  wrong_tag_filter   : タグ実装済みだが deny の match tag 番号 typo(100)＋seed=1 → ループ。
  fb_suboptimal      : タグ無し(seed=5) → ループは無いが片境界が遠回り＋フィードバック広告。
  half_fix           : 対策(distance)が RT02 のみ → RT03 だけ遠回り(前任者の中途半端対策)。
  stale_filter       : RT02 の RIP out に残骸 distribute-list(deny any) → 片系依存・遠回り。
  missing_seed_metric: OSPF→RIP に metric 無し(無限大) → RIP 域から OSPF 側不到達。
  missing_r2o        : RIP→OSPF 再配送欠落 → OSPF 域から RIP 側不到達。
  ※「subnets 欠落」故障は IOL(XE系)では subnets が既定動作(config でも省略表示)のため
    成立しない(実機確認済)。R→O 欠落に差し替えた。

採点: netmodel 大域不変条件 reachability_all(30)/optimal(25,境界Lo宛除外)/loop_free(15)
  ＋checks: LSA5 が両境界発(10)/RT01 が OSPF 側 Lo を両境界 via で保持(10)/static 不在(5+5)。
出力: problems/GEN-REDISTRO-<seed>/ {problem.yml, initial/*.cfg.j2, grading.yml, task.md,
       solution/{fault.json,fix.json}}。fix.json は fix_generated.yml 互換。
使い方: gen_redist_ripospf_ts.py --repo . --seed <int> [--fault <name>]
"""
import argparse
import json
import os
import random

import yaml

BOUNDARIES = ["RT02", "RT03"]
TAG_RIP, TAG_OSPF = 120, 110    # 発ドメイン識別タグ(AD 値と揃える)
SEED_OK = 5                     # OSPF→RIP の健全 seed metric
FAULTS = ["seed_loop", "wrong_tag_filter", "fb_suboptimal", "half_fix",
          "stale_filter", "missing_seed_metric", "missing_r2o"]
DIFFICULTY = {"seed_loop": 5, "wrong_tag_filter": 5, "fb_suboptimal": 4,
              "half_fix": 4, "stale_filter": 4,
              "missing_seed_metric": 4, "missing_r2o": 3}
NODES = ["RT01", "RT02", "RT03", "RT04", "RT05", "RT06"]
BRANCH = ["10.0.0", "10.0.1"]   # 支社網(RT06 Lo0/Lo1) 10.0.x.1/24 固定


def rand_values(rnd):
    """loopbacks(RT01..05) / RIP側リンク(10.p.q.0/30) / OSPF側リンク(172.16.n.0/30)。"""
    used, lo = set(), {}
    for r in ["RT01", "RT02", "RT03", "RT04", "RT05"]:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    useg, rseg = set(), {}
    for name in ["16", "12", "13"]:
        while True:
            p, q = rnd.randint(1, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in useg:   # mgmt 10.1.10 回避
                useg.add((p, q)); rseg[name] = f"10.{p}.{q}"; break
    uo, oseg = set(), {}
    for name in ["24", "45", "35"]:
        while True:
            n = rnd.randint(0, 254)
            if n not in uo:
                uo.add(n); oseg[name] = f"172.16.{n}"; break
    return lo, rseg, oseg


# ---- 境界の再配送ブロック（初期=故障注入状態） ----
def _rmaps(o2r_deny_tag):
    return ["route-map RIP2OSPF deny 10", f" match tag {TAG_OSPF}",
            "route-map RIP2OSPF permit 20", f" set tag {TAG_RIP}",
            "route-map OSPF2RIP deny 10", f" match tag {o2r_deny_tag}",
            "route-map OSPF2RIP permit 20", f" set tag {TAG_OSPF}"]


RMAPS_OK = _rmaps(TAG_RIP)
OSPF_OK = ["redistribute rip subnets route-map RIP2OSPF", "distance ospf external 180"]
RIP_OK = [f"redistribute ospf 1 metric {SEED_OK} route-map OSPF2RIP"]


def boundary_blocks(fault, node):
    """(global_lines, ospf_lines, rip_lines) を返す（初期 config 用）。"""
    if fault == "seed_loop":            # タグ無し＋seed=1 → RT01 同値 ECMP → ループ
        return [], ["redistribute rip subnets"], ["redistribute ospf 1 metric 1"]
    if fault == "wrong_tag_filter":     # deny の tag 番号 typo → フィードバック素通り
        return (_rmaps(100), ["redistribute rip subnets route-map RIP2OSPF"],
                ["redistribute ospf 1 metric 1 route-map OSPF2RIP"])
    if fault == "fb_suboptimal":        # タグ/AD 対策なし(seed は常識値)
        return [], ["redistribute rip subnets"], [f"redistribute ospf 1 metric {SEED_OK}"]
    if fault == "half_fix":             # 対策が RT02 のみ
        if node == "RT02":
            return RMAPS_OK, OSPF_OK, RIP_OK
        return RMAPS_OK, ["redistribute rip subnets route-map RIP2OSPF"], RIP_OK
    if fault == "stale_filter":         # RT02 の RIP out に残骸フィルタ
        if node == "RT02":
            return (RMAPS_OK + ["access-list 10 deny any"], OSPF_OK,
                    RIP_OK + ["distribute-list 10 out"])
        return RMAPS_OK, OSPF_OK, RIP_OK
    if fault == "missing_seed_metric":  # seed metric 欠落(無限大)
        return RMAPS_OK, OSPF_OK, ["redistribute ospf 1 route-map OSPF2RIP"]
    if fault == "missing_r2o":          # RIP→OSPF 再配送欠落
        return RMAPS_OK, ["distance ospf external 180"], RIP_OK
    raise SystemExit(f"unknown fault {fault}")


def boundary_fix(fault, node):
    """故障を健全形へ是正する fix エントリ列(fix_generated.yml 互換)。"""
    rmap_def = {"node": node, "lines": list(RMAPS_OK)}
    ospf_full = {"node": node, "parents": "router ospf 1",
                 "lines": ["no redistribute rip"] + OSPF_OK}
    rip_full = {"node": node, "parents": "router rip",
                "lines": ["no redistribute ospf 1"] + RIP_OK}
    if fault in ("seed_loop", "fb_suboptimal"):
        return [rmap_def, ospf_full, rip_full]
    if fault == "wrong_tag_filter":
        return [{"node": node, "parents": "route-map OSPF2RIP deny 10",
                 "lines": ["no match tag 100", f"match tag {TAG_RIP}"]},
                {"node": node, "parents": "router ospf 1",
                 "lines": ["distance ospf external 180"]}, rip_full]
    if fault == "half_fix":
        if node == "RT03":
            return [{"node": node, "parents": "router ospf 1",
                     "lines": ["distance ospf external 180"]}]
        return []
    if fault == "stale_filter":
        if node == "RT02":
            return [{"node": node, "parents": "router rip",
                     "lines": ["no distribute-list 10 out"]},
                    {"node": node, "lines": ["no access-list 10"]}]
        return []
    if fault == "missing_seed_metric":
        return [rip_full]
    if fault == "missing_r2o":
        return [{"node": node, "parents": "router ospf 1",
                 "lines": ["redistribute rip subnets route-map RIP2OSPF"]}]
    return []


def render(node, lo, rseg, oseg, fault):
    L = [f"! {node} 初期構成 (相互再配送 RIP⇄OSPF TS・故障注入済)"]
    if node == "RT06":                  # RIP 内部(支社・プレフィックス源)
        for i, net in enumerate(BRANCH):
            L += [f"interface Loopback{i}", f" ip address {net}.1 255.255.255.0", "!"]
        L += [f"interface {{{{ links[0] }}}}", f" ip address {rseg['16']}.2 255.255.255.252",
              " no shutdown", "!",
              "router rip", " version 2", " network 10.0.0.0", " no auto-summary", "!"]
        return L
    L += ["interface Loopback0", f" ip address {lo[node]} 255.255.255.255", "!"]
    if node == "RT01":                  # RIP 内部(ハブ)
        for s, sg in [(0, rseg["16"]), (1, rseg["12"]), (2, rseg["13"])]:
            L += [f"interface {{{{ links[{s}] }}}}", f" ip address {sg}.1 255.255.255.252",
                  " no shutdown", "!"]
        L += ["router rip", " version 2", " network 10.0.0.0",
              f" network {lo[node].split('.')[0]}.0.0.0", " no auto-summary", "!"]
        return L
    if node in ("RT04", "RT05"):        # OSPF 内部
        segs = [(0, f"{oseg['24']}.2"), (1, f"{oseg['45']}.1")] if node == "RT04" \
            else [(0, f"{oseg['45']}.2"), (1, f"{oseg['35']}.2")]
        nets = ["24", "45"] if node == "RT04" else ["45", "35"]
        for s, ip in segs:
            L += [f"interface {{{{ links[{s}] }}}}", f" ip address {ip} 255.255.255.252",
                  " no shutdown", "!"]
        L += ["router ospf 1", f" router-id {lo[node]}",
              f" network {lo[node]} 0.0.0.0 area 0"] \
            + [f" network {oseg[n]}.0 0.0.0.3 area 0" for n in nets] + ["!"]
        return L
    # 境界 RT02/RT03（Loopback は両プロトコルへ: RIP 直行と OSPF intra の双方で最短提供）
    rs, os_ = ("12", "24") if node == "RT02" else ("13", "35")
    ifs = [(0, f"{rseg[rs]}.2"), (1, f"{oseg[os_]}.1")]
    gl, ospf_extra, rip_extra = boundary_blocks(fault, node)
    for s, ip in ifs:
        L += [f"interface {{{{ links[{s}] }}}}", f" ip address {ip} 255.255.255.252",
              " no shutdown", "!"]
    L += ["router ospf 1", f" router-id {lo[node]}",
          f" network {lo[node]} 0.0.0.0 area 0",
          f" network {oseg[os_]}.0 0.0.0.3 area 0"] \
        + [f" {x}" for x in ospf_extra] + ["!"]
    L += ["router rip", " version 2", " network 10.0.0.0",
          f" network {lo[node].split('.')[0]}.0.0.0", " no auto-summary"] \
        + [f" {x}" for x in rip_extra] + ["!"]
    if gl:                              # route-map / ACL (global)
        L += gl + ["!"]
    return L


def build_model(lo, rseg, oseg):
    """netmodel 用トポロジモデル(RT06 の代表 Loopback = 10.0.0.1)。"""
    lbs = {n: lo[n] for n in NODES if n != "RT06"}
    lbs["RT06"] = f"{BRANCH[0]}.1"
    return {"loopbacks": lbs, "links": [
        {"a": "RT06", "a_ip": f"{rseg['16']}.2", "b": "RT01", "b_ip": f"{rseg['16']}.1"},
        {"a": "RT01", "a_ip": f"{rseg['12']}.1", "b": "RT02", "b_ip": f"{rseg['12']}.2"},
        {"a": "RT01", "a_ip": f"{rseg['13']}.1", "b": "RT03", "b_ip": f"{rseg['13']}.2"},
        {"a": "RT02", "a_ip": f"{oseg['24']}.1", "b": "RT04", "b_ip": f"{oseg['24']}.2"},
        {"a": "RT04", "a_ip": f"{oseg['45']}.1", "b": "RT05", "b_ip": f"{oseg['45']}.2"},
        {"a": "RT03", "a_ip": f"{oseg['35']}.1", "b": "RT05", "b_ip": f"{oseg['35']}.2"}]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    lo, rseg, oseg = rand_values(rnd)
    fault = a.fault or rnd.choice(FAULTS)

    prob_id = f"GEN-REDISTRO-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"相互再配送 RIP⇄OSPF ルーティングループTS (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["redistribution", "rip", "ospf", "routing-loop",
                          "troubleshooting", "generated"],
               "difficulty": DIFFICULTY[fault], "topology": "generated",
               "target_nodes": NODES, "points": 100, "access": "ssh",
               "lab": {"links": [
                   {"a": "RT06", "a_if": 0, "b": "RT01", "b_if": 0},
                   {"a": "RT01", "a_if": 1, "b": "RT02", "b_if": 0},
                   {"a": "RT01", "a_if": 2, "b": "RT03", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "RT04", "b_if": 0},
                   {"a": "RT04", "a_if": 1, "b": "RT05", "b_if": 0},
                   {"a": "RT03", "a_if": 1, "b": "RT05", "b_if": 1}],
                       "positions": {"RT06": [-840, -200], "RT01": [-480, -200],
                                     "RT02": [-80, -380], "RT03": [-80, -20],
                                     "RT04": [400, -380], "RT05": [400, -20]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_ripospf_ts.py) seed={a.seed} fault={fault}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    for n in NODES:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render(n, lo, rseg, oseg, fault)) + "\n")

    # ---- 採点(netmodel 不変条件 + 設計維持 checks) ----
    model = build_model(lo, rseg, oseg)
    # 最適性: 境界(RT02/RT03) Loopback 宛は AD 由来の許容遠回りがあるため除外
    opt_pairs = [[R, T] for T in ["RT06", "RT01", "RT04", "RT05"]
                 for R in NODES if R != T]
    def _rx(ip):
        return ip.replace(".", r"\.")
    rx = {k: _rx(v) for k, v in lo.items()}
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "model": model,
               "invariants": [
                   {"type": "reachability_all", "name": "全ルータ間 Loopback 到達性",
                    "points": 30},
                   {"type": "optimal",
                    "name": "最短転送(再配送由来の遠回りが無い・境界Lo宛は除外)",
                    "points": 25, "pairs": opt_pairs},
                   {"type": "loop_free", "name": "転送ループ無し", "points": 15}],
               "checks": [
                   {"name": "OSPF: RIP 側経路の LSA5 を両境界(RT02/RT03)が生成"
                            "(相互再配送の冗長維持)",
                    "node": "RT04", "command": "show ip ospf database external",
                    "raw": [{"regex": rf"Advertising Router:\s+{rx['RT02']}"},
                            {"regex": rf"Advertising Router:\s+{rx['RT03']}"}],
                    "points": 10},
                   {"name": f"RT01: OSPF 側 Loopback({lo['RT04']}) を両境界経由の"
                            "等コストで保持(OSPF→RIP 再配送の対称性)",
                    "node": "RT01", "command": f"show ip route {lo['RT04']}",
                    "raw": [{"regex": _rx(f"{rseg['12']}.2")},
                            {"regex": _rx(f"{rseg['13']}.2")}],
                    "points": 10},
                   {"name": "RT05: 静的経路なし(暫定対処の残置禁止)",
                    "node": "RT05", "command": "show ip route static",
                    "raw": [{"not_regex": r"(?m)^S"}], "points": 5},
                   {"name": "RT01: 静的経路なし(暫定対処の残置禁止)",
                    "node": "RT01", "command": "show ip route static",
                    "raw": [{"not_regex": r"(?m)^S"}], "points": 5}]}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_ripospf_ts.py) seed={a.seed} fault={fault}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    fixes = [fx for n in BOUNDARIES for fx in boundary_fix(fault, n)]
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"fault": fault, "loopbacks": lo, "rip_segs": rseg,
                   "ospf_segs": oseg}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)

    # ---- 症状ベース task.md（原因は伏せる） ----
    sym = {
        "seed_loop": "支社網 `10.0.0.0/24` / `10.0.1.0/24` 宛の通信が**一部のルータから"
                     "届かない**(traceroute が堂々巡いになり TTL 超過)。届く宛先と届かない"
                     "宛先が混在するとの申告あり。",
        "wrong_tag_filter": "以前ループ対策を実装済みのはずだが、支社網宛の通信が"
                            "**ループしている**(TTL 超過)との申告あり。",
        "fb_suboptimal": "全宛先に到達はするが、一部ルータから支社網・RT01 宛の経路が"
                         "**異常に遠回り**(隣接しているのに 4〜5 ホップ)になっている。",
        "half_fix": "以前ループ障害が発生し対策を実施したはずだが、**片方の境界からの経路が"
                    "まだ遠回り**のままだと報告されている。",
        "stale_filter": "到達性はあるが、RT01 から本社側への経路が**片系に偏っており**、"
                        "設計どおりの冗長構成になっていない。",
        "missing_seed_metric": "支社側(RT06/RT01)から本社側(RT04/RT05 など)の Loopback へ"
                               "**到達できない**。",
        "missing_r2o": "本社側(RT04/RT05)から支社網・RT01 の Loopback へ"
                       "**到達できない**。"}[fault]
    roles = {"RT06": ("支社網 10.0.0.1/24, 10.0.1.1/24", "RIP"),
             "RT01": (f"{lo['RT01']}/32", "RIP"),
             "RT02": (f"{lo['RT02']}/32", "RIP/OSPF 境界"),
             "RT03": (f"{lo['RT03']}/32", "RIP/OSPF 境界"),
             "RT04": (f"{lo['RT04']}/32", "OSPF"),
             "RT05": (f"{lo['RT05']}/32", "OSPF")}
    ledger = "\n".join(f"| {n} | `{roles[n][0]}` | {roles[n][1]} |" for n in
                       ["RT06", "RT01", "RT02", "RT03", "RT04", "RT05"])
    task = f"""# 問題 {prob_id} : 相互再配送 RIP⇄OSPF トラブルシュート（難易度{DIFFICULTY[fault]}）

## 状況
支社(RIP v2)と本社コア(OSPF area 0)を **境界2台(RT02, RT03)** が接続し、
どちらの境界が落ちても通信が継続できるよう **二点相互再配送** で設計されている。
支社網 `10.0.0.0/24` / `10.0.1.0/24` は RT06 が RIP で広告している。

```
RT06 --- RT01 --- RT02 --- RT04
           |                 |
           +------ RT03 --- RT05
   (RIP v2)     (境界)     (OSPF a0)
```

## トラブルチケット（代表症状）
> **{sym}**

## ルータ / Loopback / 役割
| ルータ | Loopback | ドメイン |
|--------|----------|----------|
{ledger}

## 到達目標
- 全ルータが全 Loopback へ**到達**できること。
- **転送ループが無く**、経路が**最短**であること（境界 RT02/RT03 の Loopback 宛のみ
  AD 由来の遠回りを許容）。
- **相互再配送を両境界で維持**すること（片側の再配送を削除して「解決」するのは不可。
  両境界の再配送は対称=等価に保つこと）。

## 制約
- RIP/OSPF のプロトコル配置（どのルータ・リンクがどちらのドメインか）は変更不可。
- 静的経路・デフォルトルートの追加による回避は不可。

## 進め方のヒント（控えめ）
`show ip route` / `show ip protocols` / `show ip ospf database` / `traceroute` で
経路の学習元・実際の転送パスを突き合わせて切り分けること。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜16）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : fault={fault} diff={DIFFICULTY[fault]}")


if __name__ == "__main__":
    main()
