#!/usr/bin/env python3
"""ひねり生成器 v3: 経路制御（冗長トポロジ / OSPF コストによるパス選択）。

**初の冗長(閉路)トポロジ生成器。** ダイヤモンド型の 4 ルータ網を生成する:

      RT_a
     /    \\
  RT_s      RT_d
     \\    /
      RT_b

RT_s から RT_d の Loopback へは「RT_a 経由」と「RT_b 経由」の 2 つの等ホップ経路があり、
既定（全リンク同コスト）では **ECMP**（両方が next-hop として入る）になる。
課題は「RT_s → RT_d を **RT_a 経由のみ** にする」こと。手段（OSPF コスト操作）は受験者が選ぶ。

採点（ECMP 安全）:
- 制御対象 (RT_s → RT_d) は raw で「RT_a 向き next-hop を含み、RT_b 向き next-hop を含まない」
  ＝単一経路化を判定（ECMP のままだと RT_b 向きが残り FAIL）。
- 他ペアはコスト操作で経路が動きうるので **到達性のみ**（next-hop 不問）で判定。

模範解答のコスト投入（`ip ospf cost` はインタフェース配下）は solution.json の `filters`
（汎用ブロック投入。フィルタ問題で solve_generated.yml に実装済）をそのまま流用する。

使い方:
  gen_pathctrl.py --repo <repo> --seed <int>
"""
import argparse
import json
import os
import random

import yaml


def iol_if(slot):
    """iol 物理IF名: Ethernet(slot//4)/(slot%4)。"""
    return f"Ethernet{slot // 4}/{slot % 4}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seed", type=int, required=True)
    a = ap.parse_args()

    rnd = random.Random(a.seed)
    pid, area = 1, 0

    # 物理ノード RT01..RT04 を役割 (s, a, b, d) にシャッフル割当（seed で見た目も変わる）
    phys = [f"RT{i:02d}" for i in range(1, 5)]
    rnd.shuffle(phys)
    rt_s, rt_a, rt_b, rt_d = phys
    routers = sorted(phys)

    # ダイヤモンド: (s,a)(s,b)(a,d)(b,d) の 4 リンク（閉路）
    edges = [(rt_s, rt_a), (rt_s, rt_b), (rt_a, rt_d), (rt_b, rt_d)]

    # ループバック（n.n.n.n /32, 10除外・重複なし）
    used_lo, lo = set(), {}
    for r in routers:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used_lo:
                used_lo.add(k)
                lo[r] = f"{k}.{k}.{k}.{k}"
                break

    # 各エッジに /30 セグメント "10.x.y"（mgmt 10.1.10 回避・重複なし）。a端=.1 / b端=.2
    used_seg = set()
    slot = {r: 0 for r in routers}
    link_recs = []
    for (x, y) in edges:
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in used_seg:
                used_seg.add((p, q))
                seg = f"10.{p}.{q}"
                break
        link_recs.append({"a": x, "a_if": slot[x], "a_ip": f"{seg}.1",
                          "b": y, "b_if": slot[y], "b_ip": f"{seg}.2", "seg": seg})
        slot[x] += 1
        slot[y] += 1

    # 自IF情報 と 対向IP（next-hop 算出用）
    ifaces = {r: [] for r in routers}      # [(slot, my_ip, seg)]
    nbr_ip = {}                             # (r, neighbor) -> neighbor ip
    slot_to_nbr = {}                        # (r, neighbor) -> my slot toward neighbor
    for r in link_recs:
        ifaces[r["a"]].append((r["a_if"], r["a_ip"], r["seg"]))
        ifaces[r["b"]].append((r["b_if"], r["b_ip"], r["seg"]))
        nbr_ip[(r["a"], r["b"])] = r["b_ip"]
        nbr_ip[(r["b"], r["a"])] = r["a_ip"]
        slot_to_nbr[(r["a"], r["b"])] = r["a_if"]
        slot_to_nbr[(r["b"], r["a"])] = r["b_if"]

    nh_s_to_a = nbr_ip[(rt_s, rt_a)]        # RT_s が RT_a 経由で使う next-hop
    nh_s_to_b = nbr_ip[(rt_s, rt_b)]        # RT_s が RT_b 経由で使う next-hop
    b_slot_to_d = slot_to_nbr[(rt_b, rt_d)]  # 模範解答でコストを上げる RT_b の IF

    # ---- 出力ディレクトリ ----
    prob_id = f"GEN-PATH-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)

    # problem.yml
    problem = {
        "id": prob_id,
        "title": f"OSPF 経路制御 (diamond, seed={a.seed})",
        "exam": "ENCOR", "topics": ["ospf", "path-selection", "cost", "generated"],
        "difficulty": 4, "topology": "generated",
        "target_nodes": routers, "points": 100,
        "lab": {"links": [{"a": r["a"], "a_if": r["a_if"],
                           "b": r["b"], "b_if": r["b_if"]} for r in link_recs]},
    }
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_pathctrl.py) seed={a.seed} "
                f"s={rt_s} a={rt_a} b={rt_b} d={rt_d} 要求: {rt_s}->{rt_d} は {rt_a} 経由\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    # initial/<R>.cfg.j2 : Loopback + 各リンク IP（OSPF は受験者）
    for R in routers:
        lines = [f"! 自動生成 初期状態 {R} (seed={a.seed})",
                 "interface Loopback0",
                 f" ip address {lo[R]} 255.255.255.255", "!"]
        for (s, ip, seg) in sorted(ifaces[R]):
            lines += [f"interface {{{{ links[{s}] }}}}",
                      f" ip address {ip} 255.255.255.252", " no shutdown", "!"]
        with open(f"{pdir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # ---- grading.yml ----
    # 制御対象 (s->d): 単一経路化を raw で判定（30点）。他ペア: 到達性のみ（70点を均等割り）。
    checks = []
    checks.append({
        "name": f"{rt_s}: {lo[rt_d]}/32 を {rt_a} 経由のみで学習 "
                f"(next-hop {nh_s_to_a} のみ・{nh_s_to_b} は不可)",
        "node": rt_s, "command": f"show ip route {lo[rt_d]}",
        "raw": [{"contains": nh_s_to_a}, {"not_contains": nh_s_to_b}],
        "points": 30,
    })
    reach = []
    for R in routers:
        for T in routers:
            if T == R or (R == rt_s and T == rt_d):
                continue   # (s->d) は制御チェックで判定済み
            reach.append((R, T))
    base = 70 // len(reach)
    rem = 70 - base * len(reach)
    for i, (R, T) in enumerate(reach):
        checks.append({
            "name": f"{R}: {lo[T]}/32 に到達（OSPF 経路で学習）",
            "node": R, "command": "show ip route ospf",
            "parser": "show ip route",
            "find": "vrf.*.address_family.*.routes.*",
            "match": {"route": f"{lo[T]}/32", "source_protocol": "ospf"},
            "points": base + (1 if i < rem else 0),
        })
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_pathctrl.py) seed={a.seed} "
                f"要求: {rt_s}->{rt_d} は {rt_a}({nh_s_to_a}) 経由のみ\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    # ---- solution.json : 単一エリア OSPF network 文 ＋ filters(RT_b の IF コスト) ----
    sol = {"pid": pid, "nodes": {}, "filters": []}
    for R in routers:
        nets = [f"network {lo[R]} 0.0.0.0 area {area}"]
        for (_s, _ip, seg) in sorted(ifaces[R]):
            nets.append(f"network {seg}.0 0.0.0.3 area {area}")
        sol["nodes"][R] = nets
    # RT_b の RT_d 向きインタフェースのコストを上げ、s->d を RT_a 経由に誘導
    sol["filters"].append({
        "node": rt_b,
        "blocks": [{"parents": f"interface {iol_if(b_slot_to_d)}",
                    "lines": ["ip ospf cost 1000"]}],
    })
    with open(f"{pdir}/solution.json", "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=2)

    # ---- task.md（経路要求のみ。コスト操作とは明示しない）----
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 問題 {prob_id} : OSPF 経路制御（自動生成・冗長トポロジ）\n\n")
        f.write("各ルータ間リンクと Loopback には IP 設定済み。\n\n")
        f.write("## トポロジ\n")
        f.write(f"`{rt_s}` から `{rt_d}` の Loopback へは **`{rt_a}` 経由** と "
                f"**`{rt_b}` 経由** の 2 つの経路がある（冗長構成）。\n\n")
        f.write("## 要件\n")
        f.write(f"1. OSPF プロセス {pid} / エリア {area} を全ルータ・全リンク・全 Loopback で構成し、"
                "すべてのルータが他の全ルータの Loopback に到達できるようにせよ。\n")
        f.write(f"2. ただし **`{rt_s}` が `{rt_d}` の Loopback (`{lo[rt_d]}/32`) へ転送するトラフィックは、"
                f"必ず `{rt_a}` 経由のみ** とすること（`{rt_b}` 経由は使わせない）。\n")
        f.write("   - 他ルータ間の到達性は維持すること。\n\n")
        f.write("## ループバック\n")
        for R in routers:
            f.write(f"- {R}: {lo[R]}/32\n")
        f.write("\n## リンク\n")
        for r in link_recs:
            f.write(f"- {r['a']}({r['a_ip']}) — {r['b']}({r['b_ip']})  [{r['seg']}.0/30]\n")
        f.write(f"\n## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    print(f"wrote problem {prob_id}: diamond s={rt_s} a={rt_a} b={rt_b} d={rt_d}, "
          f"要求 {rt_s}->{rt_d} via {rt_a}(nh {nh_s_to_a}), "
          f"模範解答コスト: {rt_b} {iol_if(b_slot_to_d)} ip ospf cost 1000")
    print("  links:", ", ".join(f"{r['a']}-{r['b']}" for r in link_recs))


if __name__ == "__main__":
    main()
