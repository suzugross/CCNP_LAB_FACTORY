#!/usr/bin/env python3
"""ひねり生成器 v1: ルートフィルタ（パラメータ化 Stage 2 / 設計課題系）。

ランダムなツリー型 OSPF トポロジ（最大次数3）に対し、「全到達性を作る」ことに加えて
**特定ルータ RT_f が特定の宛先 Loopback (RT_d/32) だけを自身のルーティングテーブルに
載せない**という設計課題を出題する。手段（prefix-list + distribute-list in / route-map 等）は
受験者が選ぶ。採点は効果（=その経路だけが不在・他は到達可）のみで判定する。

学習ポイント: OSPF の distribute-list in は **ローカル RIB install のみ**を抑止し LSA の
フラッディングは止めない → 下流ルータは RT_d を学習し続ける、という核心を体得させる。

ツリーは任意 2 ノード間の経路が一意なので nexthop を確定計算でき採点が正確（gen_topology と同様）。
出力は完結した problem ディレクトリ problems/GEN-TWIST-<seed>/ なので既存パイプライン
（build_topology → lab_up → grade）と solve_generated.yml（filters 対応版）がそのまま使える。

使い方:
  gen_twist.py --repo <repo> --seed <int> [--n <routers 3-6>]
"""
import argparse
import json
import os
import random

import yaml

from gen_topology import build_tree, first_hop_map


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, default=4)
    a = ap.parse_args()
    if not (3 <= a.n <= 6):
        raise SystemExit("n は 3..6")

    rnd = random.Random(a.seed)
    pid, area = 1, 0
    routers = [f"RT{i:02d}" for i in range(1, a.n + 1)]
    edges = build_tree(rnd, routers)

    # ループバック（n.n.n.n /32, 10除外・重複なし）
    used_lo, lo = set(), {}
    for r in routers:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used_lo:
                used_lo.add(k)
                lo[r] = f"{k}.{k}.{k}.{k}"
                break

    # 各エッジに /30 セグメント "10.x.y"（mgmt 10.1.10 回避・重複なし）。a=.1 / b=.2
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
        rec = {"a": x, "a_if": slot[x], "a_ip": f"{seg}.1",
               "b": y, "b_if": slot[y], "b_ip": f"{seg}.2", "seg": seg}
        slot[x] += 1
        slot[y] += 1
        link_recs.append(rec)

    # 隣接表と各ルータの自IF情報
    adj = {r: [] for r in routers}
    ifaces = {r: [] for r in routers}        # [(slot, my_ip, seg)]
    nbr_ip_on_link = {}                        # (r, neighbor) -> neighbor's ip
    for rec in link_recs:
        adj[rec["a"]].append(rec["b"])
        adj[rec["b"]].append(rec["a"])
        ifaces[rec["a"]].append((rec["a_if"], rec["a_ip"], rec["seg"]))
        ifaces[rec["b"]].append((rec["b_if"], rec["b_ip"], rec["seg"]))
        nbr_ip_on_link[(rec["a"], rec["b"])] = rec["b_ip"]
        nbr_ip_on_link[(rec["b"], rec["a"])] = rec["a_ip"]

    # 各ルータ R から各他ループバック T へのネクストホップ（ツリー＝一意）
    nexthop = {}
    for R in routers:
        fh = first_hop_map(adj, R)
        for T in routers:
            if T != R:
                nexthop[(R, T)] = nbr_ip_on_link[(R, fh[T])]

    # ---- ひねり: フィルタ実施ルータ RT_f と 遮断対象 RT_d を選ぶ ----
    rt_f = rnd.choice(routers)
    rt_d = rnd.choice([r for r in routers if r != rt_f])

    # ---- 出力ディレクトリ ----
    prob_id = f"GEN-TWIST-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)

    # problem.yml
    problem = {
        "id": prob_id,
        "title": f"OSPF ルートフィルタ (tree, n={a.n}, seed={a.seed})",
        "exam": "ENARSI", "topics": ["ospf", "route-filtering", "generated"],
        "difficulty": 3, "topology": "generated",
        "target_nodes": routers, "points": 100,
        "lab": {"links": [{"a": r["a"], "a_if": r["a_if"],
                           "b": r["b"], "b_if": r["b_if"]} for r in link_recs]},
    }
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_twist.py) seed={a.seed} n={a.n} shape=tree "
                f"filter={rt_f}!->{lo[rt_d]}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    # initial/<R>.cfg.j2 : ループバック + 各リンク IP（OSPF は受験者）
    for R in routers:
        lines = [f"! 自動生成 初期状態 {R} (seed={a.seed})",
                 "interface Loopback0",
                 f" ip address {lo[R]} 255.255.255.255", "!"]
        for (s, ip, seg) in sorted(ifaces[R]):
            lines += [f"interface {{{{ links[{s}] }}}}",
                      f" ip address {ip} 255.255.255.252", " no shutdown", "!"]
        with open(f"{pdir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # grading.yml : 全ペア到達性。ただし (RT_f -> RT_d) だけは「不在」を要求。
    n_checks = a.n * (a.n - 1)
    base_pts = 100 // n_checks
    rem = 100 - base_pts * n_checks
    checks = []
    idx = 0
    for R in routers:
        for T in routers:
            if T == R:
                continue
            pts = base_pts + (1 if idx < rem else 0)
            idx += 1
            if R == rt_f and T == rt_d:
                # ひねり: RT_f は RT_d の Loopback を RIB に持たないこと（不在 = raw 判定）
                checks.append({
                    "name": f"{R}: {lo[T]}/32 を RIB に持たない（フィルタ済み）",
                    "node": R, "command": f"show ip route {lo[T]}",
                    "raw": [{"regex": "not in table"}],
                    "points": pts,
                })
            else:
                checks.append({
                    "name": f"{R}: {lo[T]}/32 を OSPF 経路で学習 (via {nexthop[(R, T)]})",
                    "node": R, "command": "show ip route ospf",
                    "parser": "show ip route",
                    "find": "vrf.*.address_family.*.routes.*",
                    "match": {"route": f"{lo[T]}/32", "source_protocol": "ospf",
                              "next_hop.next_hop_list.*.next_hop": nexthop[(R, T)]},
                    "points": pts,
                })
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_twist.py) seed={a.seed} "
                f"filter: {rt_f} は {lo[rt_d]}/32 を不在にする\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    # solution.json : OSPF network 文（gen_topology と同形）＋ filters（フィルタ解答）
    sol = {"pid": pid, "area": area, "nodes": {}, "filters": []}
    for R in routers:
        nets = [f"network {lo[R]} 0.0.0.0 area {area}"]
        for (_s, _ip, seg) in ifaces[R]:
            nets.append(f"network {seg}.0 0.0.0.3 area {area}")
        sol["nodes"][R] = nets
    sol["filters"].append({
        "node": rt_f,
        "blocks": [
            {"parents": None,
             "lines": [f"ip prefix-list TWIST-BLOCK seq 5 deny {lo[rt_d]}/32",
                       "ip prefix-list TWIST-BLOCK seq 10 permit 0.0.0.0/0 le 32"]},
            {"parents": f"router ospf {pid}",
             "lines": ["distribute-list prefix TWIST-BLOCK in"]},
        ],
    })
    with open(f"{pdir}/solution.json", "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=2)

    # task.md（目的のみ・手段は明示しない＝ヒント控えめ方針）
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 問題 {prob_id} : OSPF ルートフィルタ（自動生成・tree・{a.n}台）\n\n")
        f.write("各ルータ間リンクと Loopback には IP 設定済み。\n\n")
        f.write("## 要件\n")
        f.write(f"1. OSPF プロセス {pid} / エリア {area} を全ルータ・全リンク・全 Loopback で構成し、"
                "すべてのルータが他の全ルータの Loopback に到達できるようにせよ。\n")
        f.write(f"2. ただし **{rt_f}** は **{rt_d} の Loopback (`{lo[rt_d]}/32`)** を"
                f"自身のルーティングテーブルに**保持しないこと**。\n")
        f.write(f"   - 他の全ルータは `{lo[rt_d]}/32` へ到達できること。\n")
        f.write(f"   - {rt_f} 自身も、{rt_d} 以外の全 Loopback へは到達できること。\n\n")
        f.write("## ループバック\n")
        for R in routers:
            f.write(f"- {R}: {lo[R]}/32\n")
        f.write("\n## リンク\n")
        for r in link_recs:
            f.write(f"- {r['a']}({r['a_ip']}) — {r['b']}({r['b_ip']})  [{r['seg']}.0/30]\n")
        f.write(f"\n## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    print(f"wrote problem {prob_id}: {a.n} routers, {len(edges)} links (tree), "
          f"filter: {rt_f} は {rt_d}({lo[rt_d]}/32) を不在にする")
    print("  links:", ", ".join(f"{r['a']}-{r['b']}" for r in link_recs))


if __name__ == "__main__":
    main()
