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

★v2(BL-242・2026-10-11): **中継点でフィルタすると、その先のルータからの通信が落ちる**。
  v1 は採点が経路表の有無だけを見ていたので、RT_f が RT_d への中継点の盤面では、要件
  「他の全ルータは RT_d の Loopback へ到達できる」を満たさないまま満点になっていた
  (GEN-TWIST-11599 で実測= RT_f の先のルータから ping 0/3)。v2 は盤面を残し、到達性を
  **能動 ping で採点**する。中継点の盤面では、RT_f が /32 を持たないまま転送できる手段
  (模範解= RT_d の `default-information originate always`)を受験者が自分で見つける。
  問題文は手段を言わない。葉の盤面(フィルタだけで足りる)と問題文は同一で、seed で混ざる
  (`--transit auto`= 中継点が多め・yes/no で固定)。

  採点(基線 0 点になるよう、不在・監査は「OSPF が動いている」ことと複合):
    不在 20 = RT_f の `show ip route` に RT_d の /32 が無く、他の Loopback は OSPF で在る
    経路 30 = それ以外の全ペアが OSPF の /32 を正しいネクストホップで学習
    到達 30 = RT_f・RT_d 以外の各ルータから Lo0 送信元で RT_d の Loopback へ ping
    監査 20 = 各ルータにスタティックルート・PBR が無い(問題文の制約)。RT_f に 10・残りで 10
              (RT_f のスタティックのデフォルトは到達の検査を全部通すので、ここで 90 へ落とす)

  裏どり(論点ごと):
    - distribute-list in は LSDB を変えず自機の経路表だけを落とす= 公式(OSPF の経路フィルタの
      解説)・解説サイトで確認／実機(IOL)= RT_f の先のルータは /32 を持ち続けるが ping は 0/3。
    - RT_d の `default-information originate always` で RT_f は O*E2 0.0.0.0/0 だけで転送し、
      全ルータから ping 3/3・未知宛先は RT_d で !H(ループなし)= 実機。always は自機に
      デフォルトが無くても生成する= 公式・解説サイト。
    - デフォルトの起点を RT_f から見て RT_d と逆側に置くと RT_f⇔隣でループ(ping 0/3)= 実機。
    - 出口 IF 指定のスタティックのデフォルトでも通る(代理 ARP)= 実機 → 制約で禁止し監査する。
    - `show ip route <addr>` はデフォルトだけなら `% Network not in table`、包含する /24 が
      あるとその経路を表示する= 実機 → 不在の判定はテーブル表示に /32 が無いことで見る。
    - 問題集は未参照(この題材の保存分を探していない)。

使い方:
  gen_twist.py --repo <repo> --seed <int> [--n <routers 3-6>] [--transit auto|yes|no]
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
    ap.add_argument("--transit", choices=["auto", "yes", "no"], default="auto",
                    help="RT_f を RT_d への中継点にするか(auto= 中継点が多めの抽選)")
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
    # ★v2: ツリーなので「RT_f が葉でない」= RT_f を通らないと RT_d へ届かないルータがいる(中継点)。
    #   中継点の盤面はフィルタだけでは到達性が欠ける(docstring)。auto は葉を引いた時に 6 割で引き直す。
    inner = [r for r in routers if len(adj[r]) >= 2]
    leaves = [r for r in routers if len(adj[r]) == 1]
    want = a.transit
    if want == "auto":
        want = "yes" if rt_f in leaves and rnd.random() < 0.6 else "keep"
    if want == "yes" and rt_f not in inner:
        rt_f = rnd.choice(inner)
        rt_d = rnd.choice([r for r in routers if r != rt_f])
    elif want == "no" and rt_f not in leaves:
        rt_f = rnd.choice(leaves)
        rt_d = rnd.choice([r for r in routers if r != rt_f])
    transit = rt_f in inner

    # ---- 出力ディレクトリ ----
    prob_id = f"GEN-TWIST-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)

    # problem.yml
    problem = {
        "id": prob_id,
        "title": f"OSPF ルートフィルタ (tree, n={a.n}, seed={a.seed})",
        "exam": "ENARSI", "topics": ["ospf", "route-filtering", "generated"],
        "difficulty": 4, "topology": "generated",
        "target_nodes": routers, "points": 100,
        "lab": {"links": [{"a": r["a"], "a_if": r["a_if"],
                           "b": r["b"], "b_if": r["b_if"]} for r in link_recs]},
    }
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_twist.py v2) seed={a.seed} n={a.n} shape=tree "
                f"filter={rt_f}!->{lo[rt_d]} transit={'yes' if transit else 'no'}\n")
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

    # grading.yml (v2・配点は docstring): 不在 20 / 経路 30 / 到達 30 / 監査 20
    def split(total, k):
        base, rem = divmod(total, k)
        return [base + (1 if i < rem else 0) for i in range(k)]

    def esc(ip):
        return ip.replace(".", "\\.")

    checks = []
    # 不在: テーブル表示に RT_d の /32 が無い。基線(OSPF なし)で通らないよう、他の Loopback の
    #       OSPF 経路が在ることと複合。`show ip route <addr>` は包含経路があると不在にならない。
    #       前後を数字・ドットで区切る(10.2.2.2 の中の 2.2.2.2 に当てない)。
    witness = next(r for r in routers if r not in (rt_f, rt_d))
    checks.append({
        "name": f"{rt_f}: {lo[rt_d]}/32 をルーティングテーブルに持たない",
        "node": rt_f, "command": "show ip route",
        "raw": [{"regex": rf"O\s+{esc(lo[witness])} \["},
                {"not_regex": rf"(?<![\d.]){esc(lo[rt_d])}(?![\d.])"}],
        "points": 20,
    })
    pairs = [(R, T) for R in routers for T in routers
             if T != R and not (R == rt_f and T == rt_d)]
    for (R, T), pts in zip(pairs, split(30, len(pairs))):
        checks.append({
            "name": f"{R}: {lo[T]}/32 を OSPF 経路で学習 (via {nexthop[(R, T)]})",
            "node": R, "command": "show ip route ospf",
            "parser": "show ip route",
            "find": "vrf.*.address_family.*.routes.*",
            "match": {"route": f"{lo[T]}/32", "source_protocol": "ospf",
                      "next_hop.next_hop_list.*.next_hop": nexthop[(R, T)]},
            "points": pts,
        })
    # 到達: RT_f 以外の全ルータから RT_d の Loopback へ(送信元は自機の Loopback0= 戻りも経路で運ぶ)
    pingers = [r for r in routers if r not in (rt_f, rt_d)]
    for R, pts in zip(pingers, split(30, len(pingers))):
        checks.append({
            "name": f"{R}: {rt_d} の Loopback ({lo[rt_d]}) へ到達",
            "node": R, "command": f"ping {lo[rt_d]} source Loopback0 repeat 5",
            "raw": [{"regex": "Success rate is [1-9]"}],
            "points": pts,
        })
    # 監査: 制約(スタティックルート・PBR の禁止)。基線で通らないよう OSPF の構成と複合。
    rest = [r for r in routers if r != rt_f]
    for R, pts in zip([rt_f] + rest, [10] + split(10, len(rest))):
        checks.append({
            "name": f"{R}: スタティックルート・PBR を使っていない",
            "node": R, "command": "show running-config",
            "raw": [{"regex": rf"(?m)^router ospf {pid}\b"},
                    {"not_regex": r"(?m)^ip route \d"},
                    {"not_regex": r"ip policy route-map|ip local policy"}],
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
    if transit:
        # 中継点の盤面: RT_f が /32 を持たないまま転送できるよう、RT_d がデフォルトを出す
        sol["filters"].append({
            "node": rt_d,
            "blocks": [{"parents": f"router ospf {pid}",
                        "lines": ["default-information originate always"]}],
        })
    with open(f"{pdir}/solution.json", "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=2)

    # task.md（目的のみ・手段は明示しない＝ヒント控えめ方針）
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 問題 {prob_id} : OSPF ルートフィルタ（自動生成・tree・{a.n}台）\n\n")
        f.write("各ルータ間リンクと Loopback には IP 設定済み。\n\n")
        f.write("## 要件\n")
        f.write(f"1. OSPF プロセス {pid} / エリア {area} を全ルータ・全リンク・全 Loopback で構成し、"
                "すべてのルータが他の全ルータの Loopback に到達できるようにしなさい。\n")
        f.write(f"2. ただし **{rt_f}** は、**{rt_d} の Loopback (`{lo[rt_d]}/32`)** の経路を"
                "自身のルーティングテーブルに**保持してはなりません**。\n")
        f.write(f"3. 要件 2 が満たされた状態で、{rt_f} 以外のすべてのルータは、自身の Loopback0 を送信元として "
                f"`{lo[rt_d]}` へ到達できなければなりません。\n")
        f.write(f"4. {rt_f} 自身も、{rt_d} 以外のすべての Loopback へ到達できなければなりません。\n\n")
        f.write("## 制約\n")
        f.write("- スタティックルートを使用してはなりません(すべてのルータ)。\n")
        f.write("- ポリシーベース ルーティングを使用してはなりません。\n")
        f.write("- 設定済みの IP アドレスは、変更されてはなりません。\n\n")
        f.write("## ループバック\n")
        for R in routers:
            f.write(f"- {R}: {lo[R]}/32\n")
        f.write("\n## リンク\n")
        for r in link_recs:
            f.write(f"- {r['a']}({r['a_ip']}) — {r['b']}({r['b_ip']})  [{r['seg']}.0/30]\n")
        f.write(f"\n## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    print(f"wrote problem {prob_id}: {a.n} routers, {len(edges)} links (tree), "
          f"filter: {rt_f} は {rt_d}({lo[rt_d]}/32) を不在にする "
          f"(transit={'yes' if transit else 'no'})")
    print("  links:", ", ".join(f"{r['a']}-{r['b']}" for r in link_recs))


if __name__ == "__main__":
    main()
