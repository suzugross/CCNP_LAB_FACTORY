#!/usr/bin/env python3
"""トポロジ生成器（パラメータ化 Stage 2 v1）。

ランダムな *ツリー型* トポロジ（N ルータ・最大次数3）の OSPF シングルエリア到達性問題を
丸ごと生成する。ツリーは任意 2 ノード間の経路が一意なので、各宛先ループバックへの
ネクストホップを Python で確定計算でき、採点が正確になる（ECMP の曖昧さが無い）。

出力は完結した problem ディレクトリ problems/GEN-OSPF-<seed>/ なので、既存パイプライン
（build_topology → lab_up → grade）がそのまま使える。模範解答 solution.json も出力する。

使い方:
  gen_topology.py --repo <repo> --seed <int> [--n <routers 3-6>]
"""
import argparse
import json
import os
import random
from collections import deque

import yaml


def build_tree(rnd, routers):
    """最大次数3のランダムツリー。edges=[(a,b)] を返す。"""
    deg = {r: 0 for r in routers}
    edges = []
    for i in range(1, len(routers)):
        cands = [routers[j] for j in range(i) if deg[routers[j]] < 3]
        a = rnd.choice(cands)
        b = routers[i]
        edges.append((a, b))
        deg[a] += 1
        deg[b] += 1
    return edges


def first_hop_map(adj, root):
    """root から各ノードへの「最初のホップ(rootの隣接)」を BFS で求める。"""
    fh = {}
    q = deque()
    for nb in adj[root]:
        fh[nb] = nb
        q.append(nb)
    seen = {root} | set(adj[root])
    while q:
        cur = q.popleft()
        for nb in adj[cur]:
            if nb not in seen:
                seen.add(nb)
                fh[nb] = fh[cur]      # cur 経由＝cur と同じ最初のホップ
                q.append(nb)
    return fh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--grade-mode", choices=["pairs", "invariant"], default="pairs",
                    help="pairs=従来のペア毎 nexthop 採点 / invariant=大域不変条件採点(軸1)")
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
    link_recs = []   # dict(a,a_if,a_ip,b,b_if,b_ip,seg)
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

    # 隣接表 adj[r] = [neighbor...]  と  各ルータの自IF情報
    adj = {r: [] for r in routers}
    ifaces = {r: [] for r in routers}        # [(slot, my_ip, seg)]
    nbr_ip_on_link = {}                       # (r, neighbor) -> neighbor's ip
    for rec in link_recs:
        adj[rec["a"]].append(rec["b"])
        adj[rec["b"]].append(rec["a"])
        ifaces[rec["a"]].append((rec["a_if"], rec["a_ip"], rec["seg"]))
        ifaces[rec["b"]].append((rec["b_if"], rec["b_ip"], rec["seg"]))
        nbr_ip_on_link[(rec["a"], rec["b"])] = rec["b_ip"]
        nbr_ip_on_link[(rec["b"], rec["a"])] = rec["a_ip"]

    # 各ルータ R から各他ループバック T へのネクストホップ（ツリー＝一意）
    nexthop = {}   # (R, T) -> ip
    for R in routers:
        fh = first_hop_map(adj, R)
        for T in routers:
            if T != R:
                nexthop[(R, T)] = nbr_ip_on_link[(R, fh[T])]

    # ---- 出力ディレクトリ ----
    pid_dir = f"{a.repo}/problems/GEN-OSPF-{a.seed}"
    os.makedirs(f"{pid_dir}/initial", exist_ok=True)
    prob_id = f"GEN-OSPF-{a.seed}"

    # problem.yml
    problem = {
        "id": prob_id,
        "title": f"自動生成 OSPF 到達性 (tree, n={a.n}, seed={a.seed})",
        "exam": "ENCOR", "topics": ["ospf", "igp", "generated"],
        "difficulty": 2, "topology": "generated",
        "target_nodes": routers, "points": 100,
        "lab": {"links": [{"a": r["a"], "a_if": r["a_if"],
                           "b": r["b"], "b_if": r["b_if"]} for r in link_recs]},
    }
    with open(f"{pid_dir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_topology.py) seed={a.seed} n={a.n} shape=tree\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    # initial/<R>.cfg.j2 : ループバック + 各リンク IP（OSPF は受験者）
    for R in routers:
        lines = [f"! 自動生成 初期状態 {R} (seed={a.seed})",
                 "interface Loopback0",
                 f" ip address {lo[R]} 255.255.255.255", "!"]
        for (s, ip, seg) in sorted(ifaces[R]):
            lines += [f"interface {{{{ links[{s}] }}}}",
                      f" ip address {ip} 255.255.255.252", " no shutdown", "!"]
        with open(f"{pid_dir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # トポロジモデル（軸1 グレーダ用 / next-hop IP → ノード解決と最短ホップ算出）
    model = {
        "loopbacks": {R: lo[R] for R in routers},
        "links": [{"a": r["a"], "a_ip": r["a_ip"],
                   "b": r["b"], "b_ip": r["b_ip"]} for r in link_recs],
    }

    if a.grade_mode == "invariant":
        # 大域不変条件採点（軸1）: 全ノードの RIB を突き合わせ、到達性/ループ不在/
        # 最短性をネットワーク全体で判定。ツリーは経路一意なので最適性も成立。
        grading = {
            "problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"},
            "model": model,
            "invariants": [
                {"type": "reachability_all", "name": "全ルータ間 Loopback 到達性", "points": 40},
                {"type": "loop_free", "name": "転送ループ不在", "points": 30},
                {"type": "optimal", "name": "最短経路で転送（コスト等価）", "points": 30},
            ],
        }
    else:
        # grading.yml : 各ルータが各他ループバックを正しいネクストホップで学習
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
    with open(f"{pid_dir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_topology.py) seed={a.seed} grade_mode={a.grade_mode}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    # solution.json : 各ルータの OSPF network 文（自己検品・auto-solve 用）
    sol = {"pid": pid, "area": area, "nodes": {}}
    for R in routers:
        nets = [f"network {lo[R]} 0.0.0.0 area {area}"]
        for (_s, _ip, seg) in ifaces[R]:
            nets.append(f"network {seg}.0 0.0.0.3 area {area}")
        sol["nodes"][R] = nets
    with open(f"{pid_dir}/solution.json", "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=2)

    # task.md
    with open(f"{pid_dir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 問題 {prob_id} : OSPF 到達性（自動生成・tree・{a.n}台）\n\n")
        f.write("各ルータ間リンクと Loopback には IP 設定済み。OSPF プロセス "
                f"{pid} / エリア {area} を全ルータ・全リンク・全 Loopback で構成し、"
                "すべてのルータが他の全ルータの Loopback に到達できるようにせよ。\n\n")
        f.write("## ループバック\n")
        for R in routers:
            f.write(f"- {R}: {lo[R]}/32\n")
        f.write("\n## リンク\n")
        for r in link_recs:
            f.write(f"- {r['a']}({r['a_ip']}) — {r['b']}({r['b_ip']})  [{r['seg']}.0/30]\n")
        f.write(f"\n## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    print(f"wrote problem {prob_id}: {a.n} routers, {len(edges)} links (tree)")
    print("  links:", ", ".join(f"{r['a']}-{r['b']}" for r in link_recs))


if __name__ == "__main__":
    main()
