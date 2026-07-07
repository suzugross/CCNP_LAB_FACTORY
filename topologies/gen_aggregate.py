#!/usr/bin/env python3
"""ひねり生成器 v2: 経路集約（マルチエリア OSPF / 設計課題系）。

ABR・area0 バックボーン・area1 の役割分担を持つ **マルチエリア OSPF ツリー**を生成し、
「全到達性を作る」ことに加えて **ABR で area1 の Loopback 群を 1 本の集約経路にまとめる**
（エリア間集約 = `area X range`）設計課題を出題する。手段は受験者が選ぶが、採点は効果のみ
（area0 バックボーンが個別 /32 ではなく単一集約経路だけを学習している）で判定する。

学習ポイント: `area range` は ABR で**個別 Type-3 LSA を抑止し単一サマリ LSA を生成**する。
→ area0 からは個別 /32 が消え、集約経路 1 本（O IA）になる。

ツリーなので任意 2 ノード間の経路は一意で nexthop を確定計算できる
（gen_topology の build_tree / first_hop_map を再利用）。

出力は完結した problem ディレクトリ problems/GEN-AGG-<seed>/ なので、既存パイプライン
（build_topology → lab_up → grade）と solve_generated.yml（OSPF Play）がそのまま使える
（集約・network 文はすべて router ospf 配下なので filters 拡張は不要）。

使い方:
  gen_aggregate.py --repo <repo> --seed <int> [--n0 <area0 routers 2-3>] [--n1 <area1 routers 2-3>]
"""
import argparse
import json
import os
import random

import yaml

from gen_topology import build_tree, first_hop_map


def _to_int(ip):
    a, b, c, d = (int(x) for x in ip.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


def _to_ip(n):
    return ".".join(str((n >> s) & 0xFF) for s in (24, 16, 8, 0))


def minimal_aggregate(ips):
    """与えた /32 群を覆う最小プレフィックスを返す: (network, prefixlen, mask_dotted)。"""
    vals = [_to_int(ip) for ip in ips]
    diff = 0
    for v in vals:
        diff |= (v ^ vals[0])
    prefixlen = 32 - diff.bit_length()           # 共通プレフィックスのビット長
    mask = (0xFFFFFFFF << (32 - prefixlen)) & 0xFFFFFFFF if prefixlen else 0
    net = vals[0] & mask
    return _to_ip(net), prefixlen, _to_ip(mask)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n0", type=int, default=2, help="area0 ルータ数(ABR含む) 2-3")
    ap.add_argument("--n1", type=int, default=3, help="area1 ルータ数 2-3")
    a = ap.parse_args()
    if not (2 <= a.n0 <= 3 and 2 <= a.n1 <= 3 and a.n0 + a.n1 <= 6):
        raise SystemExit("n0,n1 は各 2..3 かつ合計 ≤6")

    rnd = random.Random(a.seed)
    pid = 1
    n = a.n0 + a.n1
    routers = [f"RT{i:02d}" for i in range(1, n + 1)]
    area0 = routers[:a.n0]
    area1 = routers[a.n0:]

    # ---- バックボーン(area0)ツリー ＋ ABR 選定 ----
    bb_edges = build_tree(rnd, area0)            # area0 内のツリー
    deg = {r: 0 for r in area0}
    for (x, y) in bb_edges:
        deg[x] += 1
        deg[y] += 1
    abr = min(area0, key=lambda r: (deg[r], r))  # 最も次数が空いている area0 ルータを ABR に

    # ---- area1 チェーンを ABR にぶら下げる ----
    a1_chain = [abr] + area1                       # abr - area1[0] - area1[1] - ...
    a1_edges = [(a1_chain[i], a1_chain[i + 1]) for i in range(len(a1_chain) - 1)]

    # area 付きエッジ一覧（backbone=0 / area1チェーン=1）
    edge_area = {}
    for e in bb_edges:
        edge_area[e] = 0
    for e in a1_edges:
        edge_area[e] = 1
    all_edges = bb_edges + a1_edges

    # ---- Loopback 割当 ----
    lo, lo_area = {}, {}
    # area0: n.n.n.n /32（10除外・重複なし。集約ブロック 172.* とは無関係）
    used_lo = set()
    for r in area0:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used_lo:
                used_lo.add(k)
                lo[r] = f"{k}.{k}.{k}.{k}"
                lo_area[r] = 0
                break
    # area1: 連続空間 172.B.j.1 /32（集約が一意に決まる）
    B = rnd.randint(16, 31)
    for j, r in enumerate(area1):
        lo[r] = f"172.{B}.{j}.1"
        lo_area[r] = 1
    summ_net, summ_len, summ_mask = minimal_aggregate([lo[r] for r in area1])

    # ---- 各エッジに /30 セグメント "10.x.y"（mgmt 10.1.10 回避・重複なし）----
    used_seg = set()
    slot = {r: 0 for r in routers}
    link_recs = []     # dict(a,a_if,a_ip,b,b_if,b_ip,seg,area)
    for (x, y) in all_edges:
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in used_seg:
                used_seg.add((p, q))
                seg = f"10.{p}.{q}"
                break
        link_recs.append({"a": x, "a_if": slot[x], "a_ip": f"{seg}.1",
                          "b": y, "b_if": slot[y], "b_ip": f"{seg}.2",
                          "seg": seg, "area": edge_area[(x, y)]})
        slot[x] += 1
        slot[y] += 1

    # ---- 隣接表・自IF情報・対向IP ----
    adj = {r: [] for r in routers}
    ifaces = {r: [] for r in routers}       # [(slot, my_ip, seg, area)]
    nbr_ip_on_link = {}
    for r in link_recs:
        adj[r["a"]].append(r["b"])
        adj[r["b"]].append(r["a"])
        ifaces[r["a"]].append((r["a_if"], r["a_ip"], r["seg"], r["area"]))
        ifaces[r["b"]].append((r["b_if"], r["b_ip"], r["seg"], r["area"]))
        nbr_ip_on_link[(r["a"], r["b"])] = r["b_ip"]
        nbr_ip_on_link[(r["b"], r["a"])] = r["a_ip"]

    # ---- nexthop（ツリー＝一意）----
    nexthop = {}
    for R in routers:
        fh = first_hop_map(adj, R)
        for T in routers:
            if T != R:
                nexthop[(R, T)] = nbr_ip_on_link[(R, fh[T])]
    # 集約経路の nexthop（A0pure → ABR 方向。area1 は全て ABR の先＝同じ最初のホップ）
    summ_nexthop = {R: nexthop[(R, abr)] for R in area0 if R != abr}

    a0pure = [r for r in area0 if r != abr]

    # ---- 出力ディレクトリ ----
    prob_id = f"GEN-AGG-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)

    # problem.yml
    problem = {
        "id": prob_id,
        "title": f"OSPF エリア間集約 (multiarea, n0={a.n0} n1={a.n1}, seed={a.seed})",
        "exam": "ENCOR", "topics": ["ospf", "multiarea", "summarization", "generated"],
        "difficulty": 3, "topology": "generated",
        "target_nodes": routers, "points": 100,
        "lab": {"links": [{"a": r["a"], "a_if": r["a_if"],
                           "b": r["b"], "b_if": r["b_if"]} for r in link_recs]},
    }
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_aggregate.py) seed={a.seed} ABR={abr} "
                f"area1={','.join(area1)} summary={summ_net}/{summ_len}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    # initial/<R>.cfg.j2 : Loopback + 各リンク IP（OSPF は受験者）
    for R in routers:
        lines = [f"! 自動生成 初期状態 {R} (seed={a.seed})",
                 "interface Loopback0",
                 f" ip address {lo[R]} 255.255.255.255", "!"]
        for (s, ip, seg, _ar) in sorted(ifaces[R]):
            lines += [f"interface {{{{ links[{s}] }}}}",
                      f" ip address {ip} 255.255.255.252", " no shutdown", "!"]
        with open(f"{pdir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # ---- grading.yml ----
    checks = []
    for R in routers:
        for T in routers:
            if T == R:
                continue
            if R in a0pure and T in area1:
                continue   # 集約対象方向：個別到達性は出さない（下で集約存在＋個別不在）
            checks.append({
                "name": f"{R}: {lo[T]}/32 を OSPF 経路で学習 (via {nexthop[(R, T)]})",
                "node": R, "command": "show ip route ospf",
                "parser": "show ip route",
                "find": "vrf.*.address_family.*.routes.*",
                "match": {"route": f"{lo[T]}/32", "source_protocol": "ospf",
                          "next_hop.next_hop_list.*.next_hop": nexthop[(R, T)]},
            })
    # 集約存在（A0pure 毎）＋ 個別不在（A0pure × area1）
    for R in a0pure:
        checks.append({
            "name": f"{R}: 集約経路 {summ_net}/{summ_len} を学習 (O IA, via {summ_nexthop[R]})",
            "node": R, "command": "show ip route ospf",
            "parser": "show ip route",
            "find": "vrf.*.address_family.*.routes.*",
            "match": {"route": f"{summ_net}/{summ_len}", "source_protocol": "ospf",
                      "next_hop.next_hop_list.*.next_hop": summ_nexthop[R]},
        })
        for T in area1:
            # show ip route <lo> は最長一致で集約 /22 を返す。「個別 /32 が無く集約に解決する」を判定:
            # 出力に <lo>/32 が現れず、かつ集約プレフィックスが現れる（=集約で抑止された証拠）。
            checks.append({
                "name": f"{R}: 個別 {lo[T]}/32 が無く集約 {summ_net}/{summ_len} に解決（集約で抑止）",
                "node": R, "command": f"show ip route {lo[T]}",
                "raw": [{"not_contains": f"{lo[T]}/32"},
                        {"contains": f"{summ_net}/{summ_len}"}],
            })
    # 配点を均等割り（端数は先頭に +1）
    nc = len(checks)
    base = 100 // nc
    rem = 100 - base * nc
    for i, c in enumerate(checks):
        c["points"] = base + (1 if i < rem else 0)

    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_aggregate.py) seed={a.seed} "
                f"ABR={abr} 集約 {summ_net}/{summ_len} を area0 へ\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    # ---- solution.json : マルチエリア network 文 ＋ ABR の area range ----
    sol = {"pid": pid, "nodes": {}}
    for R in routers:
        nets = [f"network {lo[R]} 0.0.0.0 area {lo_area[R]}"]
        for (_s, _ip, seg, ar) in sorted(ifaces[R]):
            nets.append(f"network {seg}.0 0.0.0.3 area {ar}")
        if R == abr:
            nets.append(f"area 1 range {summ_net} {summ_mask}")
        sol["nodes"][R] = nets
    with open(f"{pdir}/solution.json", "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=2)

    # ---- task.md（エリア構成と集約spec を提示。コマンド名/置き場所は伏せる）----
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 問題 {prob_id} : OSPF エリア間集約（自動生成・マルチエリア）\n\n")
        f.write("各ルータ間リンクと Loopback には IP 設定済み。\n\n")
        f.write("## エリア設計\n")
        f.write(f"- **area 0（バックボーン）**: {', '.join(area0)}\n")
        f.write(f"- **area 1**: {', '.join(area1)}\n")
        f.write(f"- **ABR（area0/area1 の境界）**: {abr}\n")
        f.write("- 各ルータの Loopback と各リンクを、上記の所属エリアで OSPF プロセス "
                f"{pid} に参加させること（{abr} の area1 側リンクのみ area 1、他は area 0）。\n\n")
        f.write("## 要件\n")
        f.write("1. すべてのルータが他の全ルータの Loopback に到達できること。\n")
        f.write(f"2. ただし **area 0 のバックボーン**からは、area 1 の各 Loopback を"
                f"**個別経路ではなく単一の集約経路 `{summ_net}/{summ_len}` として**見えるようにすること。\n")
        f.write(f"   - area 0 のルータに area 1 の個別 /32（例 `{lo[area1[0]]}/32`）が現れてはならない。\n")
        f.write(f"   - {abr} および area 1 内では個別経路を保持していてよい。\n\n")
        f.write("## ループバック\n")
        for R in routers:
            f.write(f"- {R}: {lo[R]}/32  ({'area1' if lo_area[R] else 'area0'})\n")
        f.write("\n## リンク\n")
        for r in link_recs:
            f.write(f"- {r['a']}({r['a_ip']}) — {r['b']}({r['b_ip']})  "
                    f"[{r['seg']}.0/30, area {r['area']}]\n")
        f.write(f"\n## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    print(f"wrote problem {prob_id}: n0={a.n0} n1={a.n1}, ABR={abr}, "
          f"area1={','.join(area1)}, 集約={summ_net}/{summ_len} ({summ_mask})")
    print("  links:", ", ".join(f"{r['a']}-{r['b']}(a{r['area']})" for r in link_recs))


if __name__ == "__main__":
    main()
