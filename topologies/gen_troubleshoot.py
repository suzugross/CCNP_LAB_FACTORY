#!/usr/bin/env python3
"""トラブルシュート問題 生成器（Stage 2: 故障注入・リアル版／多重故障対応）。

ランダムなツリー型 OSPF トポロジに「正しい設定」を入れたうえで、現実的な故障を
**1 つ以上**仕込んだ初期 config を生成する。出題は **症状ベース**（受験者には
トラブルチケット＝代表的な到達不可ペアだけを提示し、トポロジ詳細・故障の種類/場所/個数は伏せる）。
採点は gen_topology と同じ全ペア到達性（健全状態に戻れば 100 点）。

`--faults N`（既定 1）で同時注入する独立故障の数を指定する。N 個の故障は
**互いに非干渉**（同一 IF・同一リンク・同一 Loopback/フィルタ対象を重複させない）に選ぶ。
全ペア到達採点なので、**N 個すべて直すまで 100 点にならない**（部分修正＝部分点）。
分断の先に局所故障があると、リンク復旧まで症状が見えない＝自然なマスキングになる。

`--stacked K`（既定 0）: **同一リンクに 2 故障を積み重ねた "逐次解明" ペア**を K 組仕込む。
片端に「隣接を形成させない故障（shutdown/wrong_area/auth 等）」、対向に mtu_mismatch を置く。
一方を直すと隣接が DOWN→EXSTART まで進むが、もう一方でまだ FULL にならない＝実機の障害対応そのもの。
両端を直さないとリンクが上がらない（採点上もそのリンク復旧まで未達）。

`--decoys K`（既定 0）: **おとり（レッドへリング）**を K 個仕込む。壊れていないが怪しく見える
設定（高コスト/未適用ACL/未参照prefix-list/Null0スタティック/passive loopback/装飾的description）。
到達性には一切影響しない（BFS で確認）ので採点に無害だが、本物の故障との切り分け力を要求する。
solution/decoys.json に記録（受験者には見せない・修正不要）。

故障タイプ（13 種）:
  -- リンク隣接を壊す（その先が到達不可＝分断・単一リンク）--
  shutdown / missing_link_network / wrong_area / passive_interface /
  mask_mismatch / mtu_mismatch / hello_mismatch / dead_interval_mismatch /
  auth_mismatch(IF単位MD5片側) / router_id_collision(隣接2機が同一RID)
  -- 対象機の全リンクを壊す（area単位故障・マルチリンク）--
  area_auth_mismatch  : あるルータで area 認証を有効化（全 OSPF IF に効く＝全隣接断）
  -- 経路を局所的に落とす --
  missing_loopback    : あるルータの Loopback network 文を削除（その lo へ全員到達不可）
  distribute_list_in  : あるルータで prefix-list + distribute-list in（その 1 経路だけ RIB 不採用）

注: router_id_collision は router-id がプロセス再起動まで反映されないため、修正後に
  `clear ip ospf process` が必要（受験者に気付かせる＝task では明かさない）。fix.json は
  exec エントリ {node,exec:[...]} でクリアを流す（fix_generated.yml が config 投入後に実行）。
  認証は IF 単位(auth_mismatch)と area 単位(area_auth_mismatch)が混在し得る＝両表記の読み分けを要求。

出力: problems/GEN-TS-<seed>/
  problem.yml / initial/*.cfg.j2 / grading.yml / task.md（症状ベース・答え無し）
  solution/{fault.json,fix.json,impact.json}（採点者専用・受験者には見せない）
fix.json は {"fixes":[{node,parents,lines},...]}（playbooks/fix_generated.yml が読む。
iol の物理 IF 名 Ethernet0/<slot> 前提）。

使い方: gen_troubleshoot.py --repo . --seed <int> [--n 3-6] [--faults N]
"""
import argparse
import json
import os
import random
from collections import deque

import yaml

from gen_topology import build_tree, first_hop_map


# 故障タイプ → 難易度（見えやすい=3 / 切り分けが要る=4）
FAULT_DIFFICULTY = {
    "shutdown": 3, "missing_link_network": 3, "wrong_area": 3, "missing_loopback": 3,
    "passive_interface": 4, "mask_mismatch": 4, "mtu_mismatch": 4,
    "hello_mismatch": 4, "auth_mismatch": 4, "distribute_list_in": 4,
    "dead_interval_mismatch": 4, "router_id_collision": 5, "area_auth_mismatch": 5,
}
# 単一リンクの隣接を壊す故障（iff 経由でIF/ospf描画・broken に当該リンク1本を追加）
LINK_FAULTS = ["shutdown", "missing_link_network", "wrong_area", "passive_interface",
               "mask_mismatch", "mtu_mismatch", "hello_mismatch", "auth_mismatch",
               "dead_interval_mismatch", "router_id_collision"]
# 対象機の全リンクを壊す故障（area 認証は全 OSPF IF に効く＝マルチリンク）
WHOLE_ROUTER_FAULTS = ["area_auth_mismatch"]
DEST_FAULTS = ["missing_loopback", "distribute_list_in"]


def reachable_from(routers, edges, src):
    """edges（無向リンク集合）上で src から到達可能なルータ集合。"""
    adj = {r: [] for r in routers}
    for (u, v) in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = {src}
    q = deque([src])
    while q:
        c = q.popleft()
        for nb in adj[c]:
            if nb not in seen:
                seen.add(nb)
                q.append(nb)
    return seen


# 隣接そのものを成立させない故障（積み重ねの「一段目」に使う）。mtu_mismatch は
# 隣接が EXSTART まで進んでから止まる＝二段目に使い「逐次解明」の段差を作る。
NO_NEIGHBOR_FAULTS = ["shutdown", "wrong_area", "passive_interface",
                      "mask_mismatch", "hello_mismatch", "auth_mismatch",
                      "dead_interval_mismatch", "router_id_collision"]


def _link_fault(ftype, node, slot, ip, seg, nb, stack=None):
    f = {"type": ftype, "node": node, "slot": slot, "ip": ip, "seg": seg,
         "neighbor": nb, "iol_if": f"Ethernet0/{slot}",
         "difficulty": FAULT_DIFFICULTY[ftype]}
    if stack is not None:
        f["stack"] = stack
    return f


def select_faults(rnd, n, n_stacked, routers, ifaces, lo, link_recs):
    """非干渉な独立故障 n 個 ＋ 同一リンクに積み重ねたペア n_stacked 組を選ぶ。
    非干渉条件: 同一 (router,slot) IF を二重使用しない / 同一リンクに別故障を重ねない /
    同一ルータに missing_loopback・distribute_list_in を二重に置かない。
    積み重ねペアは link を占有し、片端=NO_NEIGHBOR系・対向=mtu_mismatch。"""
    faults = []
    used_if, used_edge, used_loop, used_dist = set(), set(), set(), set()

    # --- 積み重ねペア（逐次解明）を先に配置 ---
    for g in range(n_stacked):
        cands = [lr for lr in link_recs
                 if frozenset({lr["a"], lr["b"]}) not in used_edge
                 and (lr["a"], lr["a_if"]) not in used_if
                 and (lr["b"], lr["b_if"]) not in used_if]
        if not cands:
            break
        lr = rnd.choice(cands)
        used_edge.add(frozenset({lr["a"], lr["b"]}))
        used_if.add((lr["a"], lr["a_if"]))
        used_if.add((lr["b"], lr["b_if"]))
        ft_a = rnd.choice(NO_NEIGHBOR_FAULTS)
        faults.append(_link_fault(ft_a, lr["a"], lr["a_if"], lr["a_ip"],
                                  lr["seg"], lr["b"], stack=g + 1))
        faults.append(_link_fault("mtu_mismatch", lr["b"], lr["b_if"], lr["b_ip"],
                                  lr["seg"], lr["a"], stack=g + 1))

    # --- 独立故障 ---
    attempts = 0
    while sum(1 for f in faults if "stack" not in f) < n and attempts < 400:
        attempts += 1
        ftype = rnd.choice(LINK_FAULTS + DEST_FAULTS + WHOLE_ROUTER_FAULTS)
        fr = rnd.choice(routers)
        if ftype in WHOLE_ROUTER_FAULTS:
            # area 認証は対象機の全 OSPF IF に効く → 全 incident リンク/slot を占有（非干渉）
            slots_fr = [s for (s, ip, seg, nb) in ifaces[fr]]
            edges_fr = [frozenset({fr, nb}) for (s, ip, seg, nb) in ifaces[fr]]
            if any((fr, s) in used_if for s in slots_fr) \
               or any(e in used_edge for e in edges_fr):
                continue
            for s in slots_fr:
                used_if.add((fr, s))
            for e in edges_fr:
                used_edge.add(e)
            faults.append({"type": ftype, "node": fr,
                           "difficulty": FAULT_DIFFICULTY[ftype]})
        elif ftype in LINK_FAULTS:
            cands = [(s, ip, seg, nb) for (s, ip, seg, nb) in ifaces[fr]
                     if (fr, s) not in used_if
                     and frozenset({fr, nb}) not in used_edge]
            if not cands:
                continue
            s, ip, seg, nb = rnd.choice(cands)
            used_if.add((fr, s))
            used_edge.add(frozenset({fr, nb}))
            faults.append(_link_fault(ftype, fr, s, ip, seg, nb))
        elif ftype == "missing_loopback":
            if fr in used_loop:
                continue
            used_loop.add(fr)
            faults.append({"type": ftype, "node": fr,
                           "difficulty": FAULT_DIFFICULTY[ftype]})
        else:  # distribute_list_in
            if fr in used_dist:
                continue
            dst = rnd.choice([r for r in routers if r != fr])
            used_dist.add(fr)
            faults.append({"type": ftype, "node": fr, "dst": dst,
                           "dst_loopback": lo[dst],
                           "difficulty": FAULT_DIFFICULTY[ftype]})
    return faults, used_if


def select_decoys(rnd, k, routers, ifaces, used_if):
    """到達性に無害な「おとり」を k 個選ぶ。where: if|ospf|global。
    interface 系（高コスト/装飾description）は故障IFを避けて健全IFに置く。"""
    decoys, attempts = [], 0
    kinds = ["ospf_cost", "description", "passive_loopback",
             "null_static", "unused_acl", "unused_prefix"]
    while len(decoys) < k and attempts < 300:
        attempts += 1
        dt = rnd.choice(kinds)
        R = rnd.choice(routers)
        if dt in ("ospf_cost", "description"):
            cands = [s for (s, ip, seg, nb) in ifaces[R] if (R, s) not in used_if]
            if not cands:
                continue
            s = rnd.choice(cands)
            line = "ip ospf cost 500" if dt == "ospf_cost" \
                else "description *** legacy link - review later ***"
            decoys.append({"type": dt, "node": R, "where": "if", "slot": s, "lines": [line]})
        elif dt == "passive_loopback":
            decoys.append({"type": dt, "node": R, "where": "ospf",
                           "lines": ["passive-interface Loopback0"]})
        elif dt == "null_static":
            decoys.append({"type": dt, "node": R, "where": "global",
                           "lines": ["ip route 192.0.2.0 255.255.255.0 Null0"]})
        elif dt == "unused_acl":
            decoys.append({"type": dt, "node": R, "where": "global",
                           "lines": ["ip access-list standard DECOY-OLD",
                                     " permit 10.10.10.10"]})
        else:  # unused_prefix
            decoys.append({"type": dt, "node": R, "where": "global",
                           "lines": ["ip prefix-list DECOY-LEGACY seq 5 permit 10.20.0.0/16 le 32"]})
    return decoys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--faults", type=int, default=1,
                    help="同時注入する独立故障の数（既定 1）")
    ap.add_argument("--stacked", type=int, default=0,
                    help="同一リンクに積み重ねる逐次解明ペアの組数（既定 0）")
    ap.add_argument("--decoys", type=int, default=0,
                    help="おとり（レッドへリング）の数（既定 0）")
    a = ap.parse_args()
    if not (3 <= a.n <= 6):
        raise SystemExit("n は 3..6")
    if a.faults < 0 or a.stacked < 0 or a.decoys < 0:
        raise SystemExit("--faults/--stacked/--decoys は 0 以上")
    if a.faults + a.stacked < 1:
        raise SystemExit("故障が 0（--faults と --stacked の合計が 1 以上必要）")

    rnd = random.Random(a.seed)
    pid, area = 1, 0
    routers = [f"RT{i:02d}" for i in range(1, a.n + 1)]
    edges = build_tree(rnd, routers)

    used_lo, lo = set(), {}
    for r in routers:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used_lo:
                used_lo.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break

    used_seg = set(); slot = {r: 0 for r in routers}; link_recs = []
    for (x, y) in edges:
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in used_seg:
                used_seg.add((p, q)); seg = f"10.{p}.{q}"; break
        link_recs.append({"a": x, "a_if": slot[x], "a_ip": f"{seg}.1",
                          "b": y, "b_if": slot[y], "b_ip": f"{seg}.2", "seg": seg})
        slot[x] += 1; slot[y] += 1

    adj = {r: [] for r in routers}
    ifaces = {r: [] for r in routers}           # (slot, my_ip, seg, neighbor)
    nbr_ip_on_link = {}
    for r in link_recs:
        adj[r["a"]].append(r["b"]); adj[r["b"]].append(r["a"])
        ifaces[r["a"]].append((r["a_if"], r["a_ip"], r["seg"], r["b"]))
        ifaces[r["b"]].append((r["b_if"], r["b_ip"], r["seg"], r["a"]))
        nbr_ip_on_link[(r["a"], r["b"])] = r["b_ip"]
        nbr_ip_on_link[(r["b"], r["a"])] = r["a_ip"]

    # 健全状態のネクストホップ（採点は常にこの理想状態を要求・故障とは独立）
    nexthop = {}
    for R in routers:
        fh = first_hop_map(adj, R)
        for T in routers:
            if T != R:
                nexthop[(R, T)] = nbr_ip_on_link[(R, fh[T])]

    all_edges = {(r["a"], r["b"]) for r in link_recs}

    # ---- 故障の選択（多重・積み重ね対応・非干渉）＋ おとり ----
    faults, used_if_sel = select_faults(rnd, a.faults, a.stacked,
                                        routers, ifaces, lo, link_recs)
    if not faults:
        raise SystemExit("故障を配置できなかった（トポロジに対し --faults/--stacked が大きすぎる可能性）")
    decoys = select_decoys(rnd, a.decoys, routers, ifaces, used_if_sel)
    decoy_if = {}
    decoy_ospf = {}
    decoy_global = {}
    for d in decoys:
        if d["where"] == "if":
            decoy_if.setdefault((d["node"], d["slot"]), []).extend(d["lines"])
        elif d["where"] == "ospf":
            decoy_ospf.setdefault(d["node"], []).extend(d["lines"])
        else:
            decoy_global.setdefault(d["node"], []).extend(d["lines"])

    # 故障の索引（config 描画・実効到達性の算出用）
    iff = {(f["node"], f["slot"]): f["type"] for f in faults if f["type"] in LINK_FAULTS}
    noloop = {f["node"] for f in faults if f["type"] == "missing_loopback"}
    # router-id 衝突: 被害機の router-id を隣接機のものに合わせる（描画用）
    rid_override = {f["node"]: lo[f["neighbor"]]
                    for f in faults if f["type"] == "router_id_collision"}
    # area 認証被害機（全 OSPF IF に効く＝全 incident リンクが断）
    area_auth_victims = {f["node"] for f in faults if f["type"] == "area_auth_mismatch"}
    distmap = {}
    for f in faults:
        if f["type"] == "distribute_list_in":
            distmap.setdefault(f["node"], []).append(f["dst"])
    broken = {frozenset({f["node"], f["neighbor"]})
              for f in faults if f["type"] in LINK_FAULTS}
    for v in area_auth_victims:                       # area 認証=対象機の全リンク断
        for (s, ip, seg, nb) in ifaces[v]:
            if nb in area_auth_victims:               # 両端が area 認証＋同一鍵 → 隣接は成立（断にしない）
                continue
            broken.add(frozenset({v, nb}))

    # ---- 実効トポロジ（症状＝失敗ペアの算出）----
    eff_edges = {(x, y) for (x, y) in all_edges if frozenset({x, y}) not in broken}

    def originated(t):
        return t not in noloop

    def filtered(s, t):
        return (s, t) in {(n, d) for n, ds in distmap.items() for d in ds}

    failing = []
    for s in routers:
        comp = reachable_from(routers, eff_edges, s)
        for t in routers:
            if t == s:
                continue
            if not ((t in comp) and originated(t) and not filtered(s, t)):
                failing.append((s, t))

    # ---- 代表チケット（受験者に見せる症状＝失敗ペアの 1 件）----
    rep_src, rep_dst = sorted(failing)[0]

    # ---- config 描画（全故障を反映、答えは匂わせない）----
    def router_cfg(R):
        lines = [f"! {R} 初期構成 (seed={a.seed})",
                 "interface Loopback0",
                 f" ip address {lo[R]} 255.255.255.255", "!"]
        for (s, ip, seg, nb) in sorted(ifaces[R]):
            ft = iff.get((R, s))
            mask = "255.255.255.248" if ft == "mask_mismatch" else "255.255.255.252"
            lines.append(f"interface {{{{ links[{s}] }}}}")
            lines.append(f" ip address {ip} {mask}")
            if ft == "mtu_mismatch":
                lines.append(" ip mtu 1400")
            if ft == "hello_mismatch":
                lines.append(" ip ospf hello-interval 5")
            if ft == "dead_interval_mismatch":
                lines.append(" ip ospf dead-interval 60")
            if ft == "auth_mismatch":
                lines.append(" ip ospf authentication message-digest")
                lines.append(" ip ospf message-digest-key 1 md5 CCNP")
            if R in area_auth_victims:        # area 認証被害機: 全 IF に MD5 鍵（対向に鍵なし→全断）
                lines.append(" ip ospf message-digest-key 1 md5 CCNP")
            lines.append(" shutdown" if ft == "shutdown" else " no shutdown")
            for dl in decoy_if.get((R, s), []):          # おとり（IF 系・無害）
                lines.append(f" {dl}")
            lines.append("!")
        ospf = [f"router ospf {pid}", f" router-id {rid_override.get(R, lo[R])}"]
        if R in area_auth_victims:            # area 単位認証を有効化（全 OSPF IF に要求）
            ospf.append(f" area {area} authentication message-digest")
        if originated(R):
            ospf.append(f" network {lo[R]} 0.0.0.0 area {area}")
        for (s, ip, seg, nb) in sorted(ifaces[R]):
            ft = iff.get((R, s))
            if ft == "missing_link_network":
                continue
            if ft == "wrong_area":
                ospf.append(f" network {seg}.0 0.0.0.3 area 1")
                continue
            ospf.append(f" network {seg}.0 0.0.0.3 area {area}")
        for (s, ip, seg, nb) in sorted(ifaces[R]):
            if iff.get((R, s)) == "passive_interface":
                ospf.append(f" passive-interface {{{{ links[{s}] }}}}")
        if R in distmap:
            ospf.append(" distribute-list prefix TS-BLOCK in")
        for dl in decoy_ospf.get(R, []):                 # おとり（OSPF 系・無害）
            ospf.append(f" {dl}")
        lines += ospf + ["!"]
        if R in distmap:
            seqn = 5
            for d in distmap[R]:
                lines.append(f"ip prefix-list TS-BLOCK seq {seqn} deny {lo[d]}/32")
                seqn += 1
            lines.append("ip prefix-list TS-BLOCK seq 100 permit 0.0.0.0/0 le 32")
            lines.append("!")
        for dl in decoy_global.get(R, []):               # おとり（グローバル系・無害）
            lines.append(dl)
        if decoy_global.get(R):
            lines.append("!")
        return lines

    # ---- 故障ごとの fix（必ずリストで返す。1 故障が複数 fix エントリを持つことがある）----
    def fault_fix(f):
        ft, R = f["type"], f["node"]
        if ft == "shutdown":
            return [{"node": R, "parents": f"interface {f['iol_if']}", "lines": ["no shutdown"]}]
        if ft == "missing_link_network":
            return [{"node": R, "parents": f"router ospf {pid}",
                     "lines": [f"network {f['seg']}.0 0.0.0.3 area {area}"]}]
        if ft == "wrong_area":
            return [{"node": R, "parents": f"router ospf {pid}",
                     "lines": [f"no network {f['seg']}.0 0.0.0.3 area 1",
                               f"network {f['seg']}.0 0.0.0.3 area {area}"]}]
        if ft == "passive_interface":
            return [{"node": R, "parents": f"router ospf {pid}",
                     "lines": [f"no passive-interface {f['iol_if']}"]}]
        if ft == "mask_mismatch":
            return [{"node": R, "parents": f"interface {f['iol_if']}",
                     "lines": [f"ip address {f['ip']} 255.255.255.252"]}]
        if ft == "mtu_mismatch":
            return [{"node": R, "parents": f"interface {f['iol_if']}", "lines": ["no ip mtu 1400"]}]
        if ft == "hello_mismatch":
            return [{"node": R, "parents": f"interface {f['iol_if']}",
                     "lines": ["no ip ospf hello-interval"]}]
        if ft == "dead_interval_mismatch":
            return [{"node": R, "parents": f"interface {f['iol_if']}",
                     "lines": ["no ip ospf dead-interval"]}]
        if ft == "auth_mismatch":
            return [{"node": R, "parents": f"interface {f['iol_if']}",
                     "lines": ["no ip ospf authentication message-digest",
                               "no ip ospf message-digest-key 1"]}]
        if ft == "router_id_collision":
            # router-id を自分のものに戻す → プロセス再起動まで反映されないので clear を流す
            # （clear ip ospf process は確認プロンプトが出る → prompt/answer で yes を返す）
            return [{"node": R, "parents": f"router ospf {pid}",
                     "lines": [f"router-id {lo[R]}"]},
                    {"node": R, "exec": [{"command": "clear ip ospf process",
                                          "prompt": "Reset ALL OSPF processes",
                                          "answer": "yes"}]}]
        if ft == "area_auth_mismatch":
            fl = [{"node": R, "parents": f"router ospf {pid}",
                   "lines": [f"no area {area} authentication message-digest"]}]
            for (s, ip, seg, nb) in ifaces[R]:           # 全 IF の鍵を撤去
                fl.append({"node": R, "parents": f"interface Ethernet0/{s}",
                           "lines": ["no ip ospf message-digest-key 1"]})
            return fl
        if ft == "missing_loopback":
            return [{"node": R, "parents": f"router ospf {pid}",
                     "lines": [f"network {lo[R]} 0.0.0.0 area {area}"]}]
        # distribute_list_in
        return [{"node": R, "parents": f"router ospf {pid}",
                 "lines": ["no distribute-list prefix TS-BLOCK in"]}]

    fixes = [fx for f in faults for fx in fault_fix(f)]
    diff = min(5, max(f["difficulty"] for f in faults)
               + (1 if len(faults) > 1 else 0)
               + (1 if (a.stacked > 0 or decoys) else 0))

    # ---- 出力 ----
    prob_id = f"GEN-TS-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"OSPF トラブルシュート (seed={a.seed}, n={a.n})",
               "exam": "ENARSI", "topics": ["ospf", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": routers, "points": 100,
               "lab": {"links": [{"a": r["a"], "a_if": r["a_if"],
                                  "b": r["b"], "b_if": r["b_if"]} for r in link_recs]}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_troubleshoot.py) seed={a.seed} faults={len(faults)}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    for R in routers:
        with open(f"{pdir}/initial/{R}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(router_cfg(R)) + "\n")

    n_checks = a.n * (a.n - 1)
    base = 100 // n_checks
    rem = 100 - base * n_checks
    checks, idx = [], 0
    for R in routers:
        for T in routers:
            if T == R:
                continue
            checks.append({"name": f"{R}: {lo[T]}/32 に到達 (via {nexthop[(R, T)]})",
                           "node": R, "command": "show ip route ospf",
                           "parser": "show ip route",
                           "find": "vrf.*.address_family.*.routes.*",
                           "match": {"route": f"{lo[T]}/32", "source_protocol": "ospf",
                                     "next_hop.next_hop_list.*.next_hop": nexthop[(R, T)]},
                           "points": base + (1 if idx < rem else 0)})
            idx += 1
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_troubleshoot.py) seed={a.seed}\n")
        yaml.safe_dump({"problem": prob_id, "total_points": 100,
                        "defaults": {"genie_os": "iosxe"}, "checks": checks},
                       f, sort_keys=False, allow_unicode=True)

    # 採点者専用（受験者には見せない）
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(faults), "faults": faults}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/impact.json", "w", encoding="utf-8") as f:
        json.dump({"reported_symptom": {"src": rep_src, "dst": rep_dst,
                                        "dst_loopback": f"{lo[rep_dst]}/32"},
                   "fault_count": len(faults), "stacked_pairs": a.stacked,
                   "decoy_count": len(decoys),
                   "affected_routes": len(failing),
                   "failing_pairs": [{"src": s, "dst": t} for (s, t) in failing]},
                  f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/decoys.json", "w", encoding="utf-8") as f:
        json.dump({"decoys": decoys}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/README.md", "w", encoding="utf-8") as f:
        f.write("# 採点者専用（受験者に見せないこと）\n\n"
                f"- 故障数: {len(faults)}（積み重ねペア {a.stacked} 組を含む）\n"
                + "".join(f"  - {f['type']} @ {f['node']}"
                          + (f" if=Ethernet0/{f['slot']}" if 'slot' in f else "")
                          + (f" dst={f['dst']}" if 'dst' in f else "")
                          + (f"  [stack#{f['stack']}]" if 'stack' in f else "") + "\n"
                          for f in faults)
                + f"- おとり: {len(decoys)} 個（到達性に無害・修正不要）\n"
                + "".join(f"  - {d['type']} @ {d['node']}\n" for d in decoys)
                + "- fix.json   : 模範修正リスト（playbooks/fix_generated.yml が読む。おとりは含まない）\n"
                "- impact.json: 申告症状と影響範囲（全失敗ペア）\n"
                "- decoys.json: おとり一覧\n")

    # 症状ベースの task.md（トポロジ詳細・故障は伏せる）
    multi = len(faults) > 1
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 障害対応 {prob_id} : OSPF 到達性（{a.n} 台バックボーン）\n\n")
        f.write("## 状況\n")
        f.write(f"OSPF（プロセス {pid} / エリア {area}）で構成された {a.n} 台のルータ網。"
                "ある変更作業の後から到達性の不具合が報告されている。\n\n")
        f.write("## 受付チケット\n")
        f.write(f"> 「**{rep_src}** から **{rep_dst}** の Loopback (`{lo[rep_dst]}/32`) に到達できない」"
                "という申告がありました。\n>\n"
                "> 切り分けて原因を特定し、恒久的に復旧してください。"
                + ("原因は 1 か所とは限りません。\n\n" if multi
                   else "なお他にも影響が出ている可能性があります。\n\n"))
        f.write("## 構成台帳（Loopback）\n")
        for R in routers:
            f.write(f"- {R}: `{lo[R]}/32`\n")
        f.write("\n※ 区間アドレスや原因の場所・種類・件数は記載していない。"
                "各装置にログインし、`show ip ospf neighbor` / `show ip route` / "
                "`show ip ospf interface` 等で実機の状態から切り分けること。\n")
        f.write("\n## 完了条件\n")
        f.write("すべてのルータが、他の全ルータの Loopback を OSPF 経路として学習している状態。\n\n")
        f.write(f"## 採点\n```\nansible-playbook playbooks/grade.yml "
                f"-e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n```\n")

    summary = ", ".join(f"{f['type']}@{f['node']}"
                        + (f"(stack#{f['stack']})" if 'stack' in f else "") for f in faults)
    print(f"wrote problem {prob_id}: n={a.n}, faults={len(faults)} [{summary}], "
          f"stacked={a.stacked}, decoys={len(decoys)}, "
          f"症状={rep_src}→{rep_dst}({lo[rep_dst]}), 影響={len(failing)}経路, 難易度={diff}")


if __name__ == "__main__":
    main()
