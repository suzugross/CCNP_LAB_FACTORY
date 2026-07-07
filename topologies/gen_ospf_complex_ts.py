#!/usr/bin/env python3
"""OSPF 複合トラブルシュート生成器（Phase B: マルチエリア＋冗長）。

正準トポロジ（値・故障を seed ランダム化）:
  area 0 (backbone・冗長ダイヤモンド):  s - a - d(ABR) / s - b - d
  area 1 (stub 化可能チェーン)       :  d(ABR) - e - f
役割 s/a/b/d/e/f は物理 RTxx へ seed でシャッフル割当。

冗長ダイヤモンドは「明示コストで厳密最適路（s→d は a 経由）」を健全状態に作り込む
（ECMP を作らない＝タイブレーク非決定の轍を踏まない）。単一 ABR(d) でエリア間経路を一意化。

故障カタログ（--faults N 個を非干渉に注入）:
  -- 単一リンクの隣接断（任意リンク）--
  shutdown / mtu_mismatch / hello_mismatch / dead_interval_mismatch /
  auth_mismatch(IF単位MD5片側) / router_id_collision(隣接2機が同一RID) / wrong_area / passive_interface
  -- 対象機の全リンク断（area 単位）--
  area_auth_mismatch
  -- 経路を局所的に落とす --
  missing_loopback
  -- マルチエリア/冗長 特有（Phase B 新規）--
  stub_flag_mismatch : area 1 の葉(f)に片側だけ `area 1 stub`→E-bit不一致でリンク断（単一）
  cost_suboptimal    : ダイヤモンド最適側に過大コスト→s→d が遠回り（届くが経路違い）

採点:
  全ペア「Loopback を RIB に学習 ＋ 正確な next-hop」（next-hop は cost 対応 Dijkstra ＋
  単一 ABR で算出）。ただし cost_suboptimal の制御ペア(s→d)だけ raw（a 向き有り/b 向き無し）で
  ECMP すり抜けを防ぐ。N 個すべて直すまで 100 にならない（連鎖マスキング）。

拡張の布石: エリアは一般マップ・router-id 全機明示（将来の virtual-link）・採点はプラガブル
  （将来 netmodel invariants で再配送）・node/area/アドレスのオフセット引数（将来の合体出題）。

出力: problems/GEN-OSPFX-<seed>/ {problem.yml, initial/*.cfg.j2, grading.yml,
       solution/{fault.json,fix.json,impact.json}}（solution は採点者専用）。
fix.json は {"fixes":[{node,parents,lines} | {node,exec:[{command,prompt,answer}]}]}（fix_generated.yml 互換）。
使い方: gen_ospf_complex_ts.py --repo . --seed <int> [--faults N] [--decoys K]
"""
import argparse
import json
import os
import random

import yaml

# 論理役割と正準リンク（role_a, role_b, area）
ROLES = ["s", "a", "b", "d", "e", "f"]
TOPO = [("s", "a", 0), ("a", "d", 0), ("s", "b", 0), ("b", "d", 0),
        ("d", "e", 1), ("e", "f", 1)]
ABR = "d"

# コスト定数（明示値は既定コストを必ず上回るよう大きく取る＝既定値に依存しない決定性）
COST_PREFER = 1000      # 健全: s→b 向きに付与（a 経由を厳密最適に）
COST_BREAK = 2000       # 故障 cost_suboptimal: s→a 向きに付与（b 経由へ flip）

FAULT_DIFFICULTY = {
    "shutdown": 3, "wrong_area": 3, "missing_loopback": 3, "passive_interface": 4,
    "mtu_mismatch": 4, "hello_mismatch": 4, "dead_interval_mismatch": 4,
    "auth_mismatch": 4, "router_id_collision": 5, "area_auth_mismatch": 5,
    "stub_flag_mismatch": 5, "cost_suboptimal": 5,
    "vl_missing": 5, "vl_wrong_endpoint": 5, "vl_auth_mismatch": 5,
    "redist_missing": 4, "redist_filtered": 5,
    "distribute_list_in": 4, "require_filter": 5,
    "acl_block_ospf": 4,
}
# 外部static再配送(--redist static)で ASBR が注入する外部プレフィクス(Null0)
EXT_PREFIXES = [("198.51.100.0", "255.255.255.0", "198.51.100.0/24", r"198\.51\.100\.0"),
                ("203.0.113.0", "255.255.255.0", "203.0.113.0/24", r"203\.0\.113\.0")]
# 単一リンクの隣接断（iff 経由で IF/ospf 描画・broken に当該リンク1本）
LINK_FAULTS = ["shutdown", "wrong_area", "passive_interface", "mtu_mismatch",
               "hello_mismatch", "dead_interval_mismatch", "auth_mismatch",
               "router_id_collision", "acl_block_ospf"]
WHOLE_ROUTER_FAULTS = ["area_auth_mismatch"]   # 対象機の全リンク断
# 局所(その機のRIBのみ)に経路を落とす故障。LSAは流れるので冗長でもマスクされない＝任意ノード可。
DEST_FAULTS = ["missing_loopback", "distribute_list_in"]
# area1 の葉リンク専用 / ダイヤモンド専用 / vlink シナリオ専用(ABR d-e 間の仮想リンク)
STUB_FAULTS = ["stub_flag_mismatch"]
COST_FAULTS = ["cost_suboptimal"]
VL_FAULTS = ["vl_missing", "vl_wrong_endpoint", "vl_auth_mismatch"]
REDIST_FAULTS = ["redist_missing", "redist_filtered"]   # --redist static 時のみ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=1)
    ap.add_argument("--decoys", type=int, default=0)
    # --- 合体出題の布石: オフセット引数（既定は従来どおり）---
    ap.add_argument("--node-base", type=int, default=1, help="RT 番号の開始（既定 1=RT01..）")
    ap.add_argument("--pid", type=int, default=1)
    ap.add_argument("--area-stub", type=int, default=1, help="非backbone(stub化可能)エリア番号")
    ap.add_argument("--ospf-style", choices=["network", "interface", "mixed"], default="mixed",
                    help="OSPF有効化の書き方: network文 / interfaceモード / 混在(既定)")
    ap.add_argument("--scenario", choices=["stub", "vlink"], default="stub",
                    help="stub=area1スタブチェーン(既定) / vlink=area2不連続+仮想リンク")
    ap.add_argument("--area2", type=int, default=2, help="vlink: 不連続エリア番号")
    ap.add_argument("--redist", choices=["none", "static"], default="none",
                    help="static=ASBRが外部static(Null0)をOSPFへ再配送(O E2)＋再配送故障を有効化")
    ap.add_argument("--require-filter", action="store_true",
                    help="ポリシー課題: ある機が特定Loopbackを学習しないよう受験者がフィルタを追加")
    a = ap.parse_args()
    if a.faults < 1:
        raise SystemExit("--faults は 1 以上")

    rnd = random.Random(a.seed)
    pid, area0, area1, area2 = a.pid, 0, a.area_stub, a.area2
    scenario = a.scenario

    def larea(ra, rb):                       # 論理リンク(役割ペア)→エリア
        if {ra, rb} == {"d", "e"}:
            return area1
        if {ra, rb} == {"e", "f"}:
            return area1 if scenario == "stub" else area2
        return area0

    # 役割→物理ノード（seed シャッフル・node_base オフセット）
    phys = [f"RT{i:02d}" for i in range(a.node_base, a.node_base + len(ROLES))]
    rnd.shuffle(phys)
    R = dict(zip(ROLES, phys))           # role -> RTxx
    role = {v: k for k, v in R.items()}  # RTxx -> role
    routers = [R[r] for r in ROLES]

    # Loopback（採点ターゲット）/ router-id = Loopback
    used, lo = set(), {}
    for r in routers:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    rid = dict(lo)   # 健全 router-id

    # Loopback のエリア（scenario 依存: vlink は f=area2, e=area1）
    lo_area_of = {}
    for r in routers:
        rl = role[r]
        lo_area_of[r] = (area0 if rl in ("s", "a", "b", "d")
                         else area1 if rl == "e"
                         else (area1 if scenario == "stub" else area2))

    # 物理リンク（role リンク→RTxx・/30・slot・area）
    used_seg = set(); slot = {r: 0 for r in routers}; links = []
    for (ra, rb, _ar) in TOPO:
        ar = larea(ra, rb)
        x, y = R[ra], R[rb]
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in used_seg:
                used_seg.add((p, q)); seg = f"10.{p}.{q}"; break
        links.append({"a": x, "a_if": slot[x], "a_ip": f"{seg}.1",
                      "b": y, "b_if": slot[y], "b_ip": f"{seg}.2",
                      "seg": seg, "area": ar})
        slot[x] += 1; slot[y] += 1

    # 隣接・IF 索引・対向IP
    ifaces = {r: [] for r in routers}     # (slot, my_ip, seg, neighbor, area)
    nbr_ip = {}                            # (me, nb) -> nb の IP（next-hop 採点用）
    area_of_link = {}
    for lk in links:
        ifaces[lk["a"]].append((lk["a_if"], lk["a_ip"], lk["seg"], lk["b"], lk["area"]))
        ifaces[lk["b"]].append((lk["b_if"], lk["b_ip"], lk["seg"], lk["a"], lk["area"]))
        nbr_ip[(lk["a"], lk["b"])] = lk["b_ip"]
        nbr_ip[(lk["b"], lk["a"])] = lk["a_ip"]
        area_of_link[frozenset({lk["a"], lk["b"]})] = lk["area"]

    # 健全コスト（ダイヤモンド: s→b 向きに COST_PREFER → a 経由が厳密最適。
    # これにより s は b 直結リンクも遠回り扱いになり、健全では b 向き next-hop を一切使わない＝
    # cost_suboptimal の raw 採点 not_contains(b向き) が健全で誤検知しない）。
    explicit_cost = {}                     # (node, slot) -> cost を初期configに描く
    explicit_cost[(R["s"], _slot_to(ifaces, R["s"], R["b"]))] = COST_PREFER

    # OSPF 有効化の書き方（ルータ単位・mixed は seed でランダム混在）
    if a.ospf_style == "mixed":
        style_of = {r: rnd.choice(["network", "interface"]) for r in routers}
    else:
        style_of = {r: a.ospf_style for r in routers}

    # critical(bridge)リンク＝e/f を端点に含むリンク（area1チェーン）。ダイヤモンドは冗長なので除外。
    critical_edges = {frozenset({R[x], R[y]}) for (x, y, ar) in TOPO
                      if x in ("e", "f") or y in ("e", "f")}

    # 再配送(外部static)ディメンション: ASBR を area0 内部(a/b)から選ぶ（Type-5を全域へ）
    redist_on = (a.redist == "static")
    asbr = rnd.choice([R["a"], R["b"]]) if redist_on else None

    # ---- 故障選択（非干渉・多重・scenario/redist でカタログ切替）----
    faults = select_faults(rnd, a.faults, routers, ifaces, role, area_of_link, R,
                           critical_edges, scenario, redist_on, asbr)
    if not faults:
        raise SystemExit("故障を配置できなかった（--faults 過大）")

    # VL 故障の補完情報（peer router-id / 誤 router-id）を付与
    for f in faults:
        if f["type"] in VL_FAULTS:
            peer = R["e"] if f["node"] == R["d"] else R["d"]
            f["peer_rid"] = lo[peer]; f["area"] = area1
            if f["type"] == "vl_wrong_endpoint":
                f["wrong_rid"] = lo[R["s"]]    # 非ABR(s)のrid＝VL上がらない

    # 再配送: ASBR の global(static Null0 + 任意route-map) / ospf(redistribute) 行を構築
    redist_fault = next((f for f in faults if f["type"] in REDIST_FAULTS), None)
    ext_blocked = EXT_PREFIXES[1] if (redist_fault and redist_fault["type"] == "redist_filtered") else None
    redist_global_of, redist_ospf_of = {}, {}
    if redist_on:
        g = [f"ip route {net} {mask} Null0" for (net, mask, cidr, rx) in EXT_PREFIXES]
        if ext_blocked:                          # redist_filtered: route-map で1本deny
            g += [f"ip prefix-list EXT-BLOCK seq 5 permit {ext_blocked[2]}",
                  "route-map REDIST-EXT deny 10",
                  " match ip address prefix-list EXT-BLOCK",
                  "route-map REDIST-EXT permit 20"]
        redist_global_of[asbr] = g
        if redist_fault and redist_fault["type"] == "redist_missing":
            redist_ospf_of[asbr] = []            # redistribute 欠落
        elif ext_blocked:
            redist_ospf_of[asbr] = ["redistribute static subnets route-map REDIST-EXT"]
        else:
            redist_ospf_of[asbr] = ["redistribute static subnets"]

    # distribute-list in 事故: victim の RIB から dst の Loopback を抑止（描画用マップ）
    dlin_lo_of = {f["node"]: f"{lo[f['dst']]}/32" for f in faults if f["type"] == "distribute_list_in"}

    # 要件フィルタ(--require-filter): 擬似故障として1件追加（初期configには出さない＝受験者が追加）
    req_filter = None
    if a.require_filter:
        avoid = {f["node"] for f in faults if f["type"] in ("distribute_list_in",)}
        cand_v = [r for r in routers if r not in avoid]
        rfv = rnd.choice(cand_v)
        rfd = rnd.choice([r for r in routers if r != rfv])
        req_filter = (rfv, rfd)
        faults.append({"type": "require_filter", "node": rfv, "dst": rfd,
                       "difficulty": FAULT_DIFFICULTY["require_filter"]})

    # 故障インデックス
    iff = {(f["node"], f["slot"]): f["type"] for f in faults if "slot" in f
           and f["type"] in LINK_FAULTS}
    rid_override = {f["node"]: lo[f["neighbor"]]
                    for f in faults if f["type"] == "router_id_collision"}
    area_auth_victims = {f["node"] for f in faults if f["type"] == "area_auth_mismatch"}
    noloop = {f["node"] for f in faults if f["type"] == "missing_loopback"}
    stub_leaf = {f["node"] for f in faults if f["type"] == "stub_flag_mismatch"}
    cost_fault = [f for f in faults if f["type"] == "cost_suboptimal"]

    # ---- broken リンク集合（実効到達性＝代表症状の算出用）----
    broken = set()
    for f in faults:
        if f["type"] in LINK_FAULTS:
            broken.add(frozenset({f["node"], f["neighbor"]}))
    for v in area_auth_victims:
        for (s, ip, seg, nb, ar) in ifaces[v]:
            if nb in area_auth_victims:
                continue
            broken.add(frozenset({v, nb}))
    for leaf in stub_leaf:                 # stub フラグ片側→葉リンク断
        for (s, ip, seg, nb, ar) in ifaces[leaf]:
            broken.add(frozenset({leaf, nb}))

    # ---- VL 健全/故障の描画行（vlink: d,e に area1 virtual-link）----
    vl_peer = {R["d"]: lo[R["e"]], R["e"]: lo[R["d"]]} if scenario == "vlink" else {}
    vl_fault = {f["node"]: f for f in faults if f["type"] in VL_FAULTS}
    vl_line_of = {}                       # 各ABRの VL 設定行(list・複数行可)
    for r in routers:
        if r not in vl_peer:
            vl_line_of[r] = []
            continue
        peer = vl_peer[r]
        fa = vl_fault.get(r)
        if fa and fa["type"] == "vl_missing":
            vl_line_of[r] = []
        elif fa and fa["type"] == "vl_wrong_endpoint":
            vl_line_of[r] = [f"area {area1} virtual-link {fa['wrong_rid']}"]
        elif fa and fa["type"] == "vl_auth_mismatch":     # 片端だけVLにMD5認証→不一致でVL断
            vl_line_of[r] = [f"area {area1} virtual-link {peer}",
                             f"area {area1} virtual-link {peer} authentication message-digest",
                             f"area {area1} virtual-link {peer} message-digest-key 1 md5 CCNP"]
        else:
            vl_line_of[r] = [f"area {area1} virtual-link {peer}"]

    # ---- 実効到達性（症状＝失敗ペア）----
    failing = compute_failing(routers, ifaces, broken, noloop)
    # distribute-list in: victim の RIB に dst が入らない（局所抑止・接続性モデルでは出ない）
    for f in faults:
        if f["type"] == "distribute_list_in":
            failing.append((f["node"], f["dst"]))
    failing = sorted(set(failing))
    # VL 故障: area2(f) と backbone(area0: s,a,b,d) が相互不到達（VL無で不連続area未到達）
    if vl_fault:
        fnode = R["f"]
        for x in (R["s"], R["a"], R["b"], R["d"]):
            failing += [(x, fnode), (fnode, x)]
        failing = sorted(set(failing))
    rep = sorted(failing)[0] if failing else (routers[0], routers[1])

    # ---- config 描画 ----
    def router_cfg(Rn):
        return render_router(Rn, role, ifaces, lo, rid_override, pid, area0, area1,
                             iff, area_auth_victims, noloop, stub_leaf, cost_fault,
                             explicit_cost, style_of[Rn], lo_area_of[Rn], vl_line_of[Rn],
                             redist_ospf_of.get(Rn), redist_global_of.get(Rn),
                             dlin_lo_of.get(Rn))

    # ---- fix ----
    fixes = [fx for f in faults
             for fx in fault_fix(f, ifaces, lo, pid, area0, area1, R, style_of, lo_area_of)]

    diff = min(5, max(f["difficulty"] for f in faults) + (1 if len(faults) > 1 else 0))

    # ---- 出力 ----
    prob_id = f"GEN-OSPFX-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"OSPF 複合TS マルチエリア+冗長 (seed={a.seed})",
               "exam": "ENARSI", "topics": ["ospf", "multi-area", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": routers, "points": 100, "access": "ssh",
               "lab": {"links": [{"a": lk["a"], "a_if": lk["a_if"],
                                  "b": lk["b"], "b_if": lk["b_if"]} for lk in links],
                       # CMLキャンバス座標(役割ベースの正準配置。見た目のみ)
                       "positions": {R[rl]: list(xy) for rl, xy in {
                           "s": (-500, -360), "a": (-700, -180), "b": (-300, -180),
                           "d": (-500, 0), "e": (-240, 0), "f": (20, 0)}.items()}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_ospf_complex_ts.py) seed={a.seed} faults={len(faults)}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    for Rn in routers:
        with open(f"{pdir}/initial/{Rn}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(router_cfg(Rn)) + "\n")

    checks = build_checks(routers, lo, role, ifaces, nbr_ip, R, cost_fault,
                          asbr if redist_on else None, req_filter)
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_ospf_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump({"problem": prob_id, "total_points": 100,
                        "defaults": {"genie_os": "iosxe"}, "checks": checks},
                       f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(faults), "faults": faults,
                   "roles": {role[r]: r for r in routers}}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/impact.json", "w", encoding="utf-8") as f:
        json.dump({"reported_symptom": {"src": rep[0], "dst": rep[1],
                                        "dst_loopback": f"{lo[rep[1]]}/32"},
                   "fault_count": len(faults),
                   "roles": {r: role[r] for r in routers},
                   "failing_pairs": [{"src": s, "dst": t} for (s, t) in sorted(failing)]},
                  f, ensure_ascii=False, indent=2)
    # ---- 症状ベース task.md（受験者向け・原因/トポロジ/件数は伏せる）----
    ledger = "\n".join(f"| {r} | `{lo[r]}/32` |" for r in routers)
    # チケット: 到達不能ペアがあればそれを、無ければ（cost等で到達は保たれる場合）最適経路の逸脱を提示
    if failing:
        ticket = f"> **{rep[0]} から {rep[1]} の Loopback (`{lo[rep[1]]}`) へ到達できない。**"
    elif redist_fault:
        ticket = (f"> **外部ネットワーク `{EXT_PREFIXES[0][2]}` 等への経路が OSPF に学習されていない"
                  "（外部経路が見えない）。**")
    else:
        ticket = ("> **到達性は保たれているが、主経路ポリシーに沿っていない"
                  "（最適経路の逸脱）疑いがある。**")
    # cost_suboptimal がある時だけ「最適経路の基準（ポリシー）」を明示（基準が無いと最適性は判定不能）
    policy = ""
    if cost_fault:
        s_, d_, a_, b_ = R["s"], R["d"], R["a"], R["b"]
        policy = (f"\n## ルーティングポリシー（最適経路の基準）\n"
                  f"- **{s_} から {d_}(`{lo[d_]}`) 宛のトラフィックは {a_} 経由を主経路**とする"
                  f"（{b_} 経由は予備・平常時は使わない）。\n"
                  f"- 現状はこのポリシーどおりに流れていない可能性がある。到達するだけでなく"
                  f"**主経路に沿っているか**も是正対象。\n")
    # 再配送ありなら外部ネットワーク台帳を提示（無いと受験者が外部経路の存在/復旧目標を知り得ない）
    ext_block = ""
    if redist_on:
        rows = "\n".join(f"| `{cidr}` |" for (net, mask, cidr, rx) in EXT_PREFIXES)
        ext_block = ("\n## 外部ネットワーク（OSPF へ再配送されるべき）\n"
                     "| 外部プレフィクス |\n|---|\n" + rows + "\n"
                     "- これらは外部から OSPF へ**再配送**され、全ルータで **`O E2`** として"
                     "学習されているべき。\n"
                     "- 現状、一部または全部が学習されていない可能性がある"
                     "（再配送の設定・フィルタを確認）。\n")
    # 要件フィルタ: ポリシーで特定経路を“持たせない”課題（受験者がフィルタを追加）
    reqf_block = ""
    if req_filter:
        rfv, rfd = req_filter
        reqf_block = ("\n## ルートフィルタ要件（ポリシー）\n"
                      f"- セキュリティ方針により、**{rfv} は {rfd} の Loopback "
                      f"(`{lo[rfd]}/32`) を経路表に持ってはならない**。\n"
                      f"- ただし {rfv} は **他のすべての Loopback には到達**できること"
                      f"（{rfd} 宛だけを {rfv} のRIBから除外）。他ルータの到達性は変えない。\n"
                      "- 適切なルートフィルタ（例: prefix-list ＋ distribute-list in 等）を**追加**して実現する。\n")
    task = f"""# 問題 {prob_id} : OSPF トラブルシュート（マルチエリア・難易度{diff}）

## 状況
OSPF で構成された社内ネットワークで **到達性障害** が報告されています。あなたは保守担当として
原因を切り分け、**全ルータが全ルータの Loopback へ相互到達できる**状態へ復旧してください。

## トラブルチケット（代表症状・1件）
{ticket}

これは検知された不具合の一例です。**原因は1か所とは限りません**。他にも影響が出ている可能性があります。

## ルータ / Loopback 台帳
| ルータ | Loopback0 |
|--------|-----------|
{ledger}
{policy}{ext_block}{reqf_block}
## 到達目標
- 全ルータが上記すべての Loopback を学習し、相互に ping 到達できること。
- （外部ネットワークがある場合）それらが全ルータで `O E2` として学習されていること。
- トポロジ構成（リンク／エリア配置）・障害の種類・場所・件数は伏せてあります。
  `show ip ospf neighbor` / `show ip ospf interface` / `show ip route` / `show ip ospf` などで切り分けてください。
- 設定変更が即座に反映されない場合があります（変更しただけでは隣接が戻らないケースに注意）。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。CML コンソールでも可。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
※ 採点は全ペアの Loopback 到達（学習＋経路）を確認します。最適経路（コスト設計）も評価対象です。
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)

    print(f"wrote problems/{prob_id} : {len(routers)} nodes, {len(faults)} faults, "
          f"diff={diff}, faults={[f['type'] for f in faults]}")


def _slot_to(ifaces, node, neighbor):
    for (s, ip, seg, nb, ar) in ifaces[node]:
        if nb == neighbor:
            return s
    return None


def select_faults(rnd, n, routers, ifaces, role, area_of_link, R, critical_edges, scenario,
                  redist_on=False, asbr=None):
    """非干渉に n 個。場所制約:
    - 単一リンク断(LINK_FAULTS)は critical(bridge)リンクのみ＝冗長で隠れない
      （ダイヤモンドの冗長リンクを切っても代替経路で到達するため到達性採点で検出不能）。
    - stub=area1葉リンク(e-f, stubシナリオのみ) / vl=ABR d/e(vlinkシナリオのみ) /
      cost=ダイヤモンド a経由 / area_auth・missing_loopback=任意ノード。"""
    faults, used_if, used_edge, used_loop, used_vl = [], set(), set(), set(), set()
    used_dist = set()
    used_redist = False
    leaf = R["f"]; abr = R["d"]
    scen_extra = STUB_FAULTS if scenario == "stub" else VL_FAULTS
    catalog = LINK_FAULTS + WHOLE_ROUTER_FAULTS + DEST_FAULTS + scen_extra + COST_FAULTS
    if redist_on:
        catalog = catalog + REDIST_FAULTS
    attempts = 0
    while len(faults) < n and attempts < 600:
        attempts += 1
        ftype = rnd.choice(catalog)
        if ftype in REDIST_FAULTS:
            # 再配送故障は ASBR に1つまで（ASBR の全IFを占有せず、redistribute だけ壊す）
            if used_redist or asbr is None:
                continue
            used_redist = True
            faults.append({"type": ftype, "node": asbr,
                           "difficulty": FAULT_DIFFICULTY[ftype]})
        elif ftype in VL_FAULTS:
            # 仮想リンク故障は ABR(d/e) のいずれかに（1機まで）
            node = rnd.choice([R["d"], R["e"]])
            if node in used_vl:
                continue
            used_vl.add(node)
            faults.append({"type": ftype, "node": node,
                           "difficulty": FAULT_DIFFICULTY[ftype]})
        elif ftype in COST_FAULTS:
            # ダイヤモンド a 経由（s→a の出力IF）に過大コスト
            s, sa = R["s"], _slot_to(ifaces, R["s"], R["a"])
            if (s, sa) in used_if or any(f["type"] == "cost_suboptimal" for f in faults):
                continue
            used_if.add((s, sa))
            faults.append({"type": ftype, "node": s, "slot": sa,
                           "neighbor": R["a"], "difficulty": FAULT_DIFFICULTY[ftype]})
        elif ftype in STUB_FAULTS:
            # area1 の葉 f に片側 stub（f-e リンク断）
            es = _slot_to(ifaces, leaf, R["e"])
            if (leaf, es) in used_if or frozenset({leaf, R["e"]}) in used_edge:
                continue
            used_if.add((leaf, es)); used_edge.add(frozenset({leaf, R["e"]}))
            faults.append({"type": ftype, "node": leaf, "slot": es,
                           "neighbor": R["e"], "difficulty": FAULT_DIFFICULTY[ftype]})
        elif ftype in WHOLE_ROUTER_FAULTS:
            fr = rnd.choice(routers)
            slots_fr = [s for (s, ip, seg, nb, ar) in ifaces[fr]]
            edges_fr = [frozenset({fr, nb}) for (s, ip, seg, nb, ar) in ifaces[fr]]
            if any((fr, s) in used_if for s in slots_fr) or any(e in used_edge for e in edges_fr):
                continue
            for s in slots_fr:
                used_if.add((fr, s))
            for e in edges_fr:
                used_edge.add(e)
            faults.append({"type": ftype, "node": fr, "difficulty": FAULT_DIFFICULTY[ftype]})
        elif ftype in LINK_FAULTS:
            # critical(bridge)リンクの端点のみ（冗長リンクは切っても隠れる＝検出不能なので除外）
            cands = [(r, s, ip, seg, nb, ar)
                     for r in routers
                     for (s, ip, seg, nb, ar) in ifaces[r]
                     if frozenset({r, nb}) in critical_edges
                     and (r, s) not in used_if and frozenset({r, nb}) not in used_edge]
            if not cands:
                continue
            fr, s, ip, seg, nb, ar = rnd.choice(cands)
            used_if.add((fr, s)); used_edge.add(frozenset({fr, nb}))
            faults.append({"type": ftype, "node": fr, "slot": s, "ip": ip, "seg": seg,
                           "neighbor": nb, "iol_if": f"Ethernet0/{s}",
                           "area": ar, "difficulty": FAULT_DIFFICULTY[ftype]})
        elif ftype == "missing_loopback":
            fr = rnd.choice(routers)
            if fr in used_loop:
                continue
            used_loop.add(fr)
            faults.append({"type": ftype, "node": fr, "difficulty": FAULT_DIFFICULTY[ftype]})
        else:  # distribute_list_in（局所RIB抑止・任意ノード）
            fr = rnd.choice(routers)
            if fr in used_dist:                       # distribute-list in はプロセスに1つ
                continue
            dst = rnd.choice([r for r in routers if r != fr])
            used_dist.add(fr)
            faults.append({"type": ftype, "node": fr, "dst": dst,
                           "difficulty": FAULT_DIFFICULTY[ftype]})
    return faults


def compute_failing(routers, ifaces, broken, noloop):
    adj = {r: set() for r in routers}
    for u in routers:
        for (s, ip, seg, nb, ar) in ifaces[u]:
            if frozenset({u, nb}) not in broken:
                adj[u].add(nb)
    failing = []
    for s in routers:
        seen = {s}; stack = [s]
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if y not in seen:
                    seen.add(y); stack.append(y)
        for t in routers:
            if t != s and not (t in seen and t not in noloop):
                failing.append((s, t))
    return failing


def render_router(Rn, role, ifaces, lo, rid_override, pid, area0, area1,
                  iff, area_auth_victims, noloop, stub_leaf, cost_fault,
                  explicit_cost, style, lo_area, vl_line,
                  redist_ospf=None, redist_global=None, dlin_lo=None):
    """OSPF 有効化を style で切替: 'network'=network 文 / 'interface'=`ip ospf <pid> area`。
    wrong_area / missing_loopback は style 対応。他故障(IF/プロセス)は style 非依存。
    vl_line: vlink シナリオで ABR(d/e) に置く `area N virtual-link X`（None=なし/欠落故障）。
    redist_ospf/redist_global: ASBR の `redistribute ...`(ospf配下) と static/route-map(global)。"""
    cf_if = {(f["node"], f["slot"]) for f in cost_fault}
    lines = [f"! {Rn} (role={role[Rn]}, ospf={style}) 初期構成",
             "interface Loopback0", f" ip address {lo[Rn]} 255.255.255.255"]
    if style == "interface" and Rn not in noloop:     # interfaceモード: Lo を OSPF へ
        lines.append(f" ip ospf {pid} area {lo_area}")
    lines.append("!")
    for (s, ip, seg, nb, ar) in sorted(ifaces[Rn]):
        ft = iff.get((Rn, s))
        lines.append(f"interface {{{{ links[{s}] }}}}")
        lines.append(f" ip address {ip} 255.255.255.252")
        if ft == "mtu_mismatch":
            lines.append(" ip mtu 1400")
        if ft == "hello_mismatch":
            lines.append(" ip ospf hello-interval 5")
        if ft == "dead_interval_mismatch":
            lines.append(" ip ospf dead-interval 60")
        if ft == "auth_mismatch":
            lines.append(" ip ospf authentication message-digest")
            lines.append(" ip ospf message-digest-key 1 md5 CCNP")
        if Rn in area_auth_victims:
            lines.append(" ip ospf message-digest-key 1 md5 CCNP")
        if (Rn, s) in explicit_cost:                 # 健全の明示コスト
            lines.append(f" ip ospf cost {explicit_cost[(Rn, s)]}")
        if (Rn, s) in cf_if:                          # cost_suboptimal 故障
            lines.append(f" ip ospf cost {COST_BREAK}")
        if ft == "acl_block_ospf":                    # inbound ACL が OSPF(89)を遮断→隣接断
            lines.append(" ip access-group ACL-BLOCK-OSPF in")
        if style == "interface":                      # interfaceモード: IF を OSPF へ
            put_area = (area1 if ar == area0 else area0) if ft == "wrong_area" else ar
            lines.append(f" ip ospf {pid} area {put_area}")
        lines.append(" shutdown" if ft == "shutdown" else " no shutdown")
        lines.append("!")
    ospf = [f"router ospf {pid}", f" router-id {rid_override.get(Rn, lo[Rn])}"]
    if vl_line:                                       # vlink: ABR(d/e) の仮想リンク(複数行可)
        ospf += [f" {l}" for l in vl_line]
    if Rn in area_auth_victims:                       # 被害機の各IFが属するエリアに認証要求（全隣接断）
        for av in sorted({ar for (s, ip, seg, nb, ar) in ifaces[Rn]}):
            ospf.append(f" area {av} authentication message-digest")
    if style == "network":                            # networkモード: network 文で有効化
        if Rn not in noloop:
            ospf.append(f" network {lo[Rn]} 0.0.0.0 area {lo_area}")
        for (s, ip, seg, nb, ar) in sorted(ifaces[Rn]):
            ft = iff.get((Rn, s))
            put_area = (area1 if ar == area0 else area0) if ft == "wrong_area" else ar
            ospf.append(f" network {seg}.0 0.0.0.3 area {put_area}")
    for (s, ip, seg, nb, ar) in sorted(ifaces[Rn]):   # passive は方式非依存(プロセス配下)
        if iff.get((Rn, s)) == "passive_interface":
            ospf.append(f" passive-interface {{{{ links[{s}] }}}}")
    if Rn in stub_leaf:                               # 片側だけ stub（E-bit 不一致）
        ospf.append(f" area {area1} stub")
    if redist_ospf:                                   # ASBR: redistribute ...（再配送故障で省略/route-map）
        ospf += [f" {l}" for l in redist_ospf]
    if dlin_lo:                                       # distribute-list in 事故: 局所RIB抑止
        ospf.append(" distribute-list prefix DL-BLOCK in")
    lines += ospf + ["!"]
    if redist_global:                                 # ASBR: 外部static(Null0)＋route-map(global)
        lines += redist_global + ["!"]
    if dlin_lo:                                       # distribute-list in 用 prefix-list(global)
        lines += [f"ip prefix-list DL-BLOCK seq 5 deny {dlin_lo}",
                  "ip prefix-list DL-BLOCK seq 100 permit 0.0.0.0/0 le 32", "!"]
    if any(iff.get((Rn, s)) == "acl_block_ospf" for (s, ip, seg, nb, ar) in ifaces[Rn]):
        lines += ["ip access-list extended ACL-BLOCK-OSPF",   # icmpのみ許可＝暗黙denyでOSPF遮断
                  " permit icmp any any", "!"]
    return lines


def fault_fix(f, ifaces, lo, pid, area0, area1, R, style_of, lo_area_of):
    ft, Rn = f["type"], f["node"]
    style = style_of[Rn]
    if ft == "shutdown":
        return [{"node": Rn, "parents": f"interface {f['iol_if']}", "lines": ["no shutdown"]}]
    if ft == "mtu_mismatch":
        return [{"node": Rn, "parents": f"interface {f['iol_if']}", "lines": ["no ip mtu 1400"]}]
    if ft == "hello_mismatch":
        return [{"node": Rn, "parents": f"interface {f['iol_if']}",
                 "lines": ["no ip ospf hello-interval"]}]
    if ft == "dead_interval_mismatch":
        return [{"node": Rn, "parents": f"interface {f['iol_if']}",
                 "lines": ["no ip ospf dead-interval"]}]
    if ft == "auth_mismatch":
        return [{"node": Rn, "parents": f"interface {f['iol_if']}",
                 "lines": ["no ip ospf authentication message-digest",
                           "no ip ospf message-digest-key 1"]}]
    if ft == "acl_block_ospf":                        # 誤 inbound ACL を IF から外す
        return [{"node": Rn, "parents": f"interface {f['iol_if']}",
                 "lines": ["no ip access-group ACL-BLOCK-OSPF in"]}]
    if ft == "passive_interface":
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": [f"no passive-interface {f['iol_if']}"]}]
    if ft == "wrong_area":
        wrong = area1 if f["area"] == area0 else area0
        if style == "interface":                      # IFモード: 正エリアで上書き
            return [{"node": Rn, "parents": f"interface Ethernet0/{f['slot']}",
                     "lines": [f"ip ospf {pid} area {f['area']}"]}]
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": [f"no network {f['seg']}.0 0.0.0.3 area {wrong}",
                           f"network {f['seg']}.0 0.0.0.3 area {f['area']}"]}]
    if ft == "router_id_collision":
        return [{"node": Rn, "parents": f"router ospf {pid}", "lines": [f"router-id {lo[Rn]}"]},
                {"node": Rn, "exec": [{"command": "clear ip ospf process",
                                       "prompt": "Reset ALL OSPF processes", "answer": "yes"}]}]
    if ft == "area_auth_mismatch":
        fl = []
        for av in sorted({ar for (s, ip, seg, nb, ar) in ifaces[Rn]}):
            fl.append({"node": Rn, "parents": f"router ospf {pid}",
                       "lines": [f"no area {av} authentication message-digest"]})
        for (s, ip, seg, nb, ar) in ifaces[Rn]:
            fl.append({"node": Rn, "parents": f"interface Ethernet0/{s}",
                       "lines": ["no ip ospf message-digest-key 1"]})
        return fl
    if ft == "stub_flag_mismatch":
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": [f"no area {area1} stub"]}]
    if ft == "cost_suboptimal":
        return [{"node": Rn, "parents": f"interface Ethernet0/{f['slot']}",
                 "lines": ["no ip ospf cost"]}]
    if ft == "vl_missing":                            # 欠落していた VL を投入
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": [f"area {f['area']} virtual-link {f['peer_rid']}"]}]
    if ft == "vl_wrong_endpoint":                     # 誤RIDを除去し正RIDで再投入
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": [f"no area {f['area']} virtual-link {f['wrong_rid']}",
                           f"area {f['area']} virtual-link {f['peer_rid']}"]}]
    if ft == "vl_auth_mismatch":                      # VLの認証を外して対向(plain)と一致させる
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": [f"no area {f['area']} virtual-link {f['peer_rid']} message-digest-key 1",
                           f"no area {f['area']} virtual-link {f['peer_rid']} authentication message-digest"]}]
    if ft == "redist_missing":                        # 欠落していた再配送を投入
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": ["redistribute static subnets"]}]
    if ft == "redist_filtered":                       # route-map付き再配送を除去しクリーン再投入
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": ["no redistribute static",
                           "redistribute static subnets"]}]
    if ft == "distribute_list_in":                    # 誤った in フィルタを撤去
        return [{"node": Rn, "parents": f"router ospf {pid}",
                 "lines": ["no distribute-list prefix DL-BLOCK in"]}]
    if ft == "require_filter":                        # 模範解答=ポリシー充足のためフィルタを追加
        return [{"node": Rn,                          # parents 省略=グローバル config
                 "lines": [f"ip prefix-list POLICY-IN seq 5 deny {lo[f['dst']]}/32",
                           "ip prefix-list POLICY-IN seq 100 permit 0.0.0.0/0 le 32"]},
                {"node": Rn, "parents": f"router ospf {pid}",
                 "lines": ["distribute-list prefix POLICY-IN in"]}]
    # missing_loopback（style 対応）
    lo_area = lo_area_of[Rn]
    if style == "interface":
        return [{"node": Rn, "parents": "interface Loopback0",
                 "lines": [f"ip ospf {pid} area {lo_area}"]}]
    return [{"node": Rn, "parents": f"router ospf {pid}",
             "lines": [f"network {lo[Rn]} 0.0.0.0 area {lo_area}"]}]


def build_checks(routers, lo, role, ifaces, nbr_ip, R, cost_fault, asbr=None, req_filter=None):
    """公平な採点: 一般ペア=到達性のみ（Loopback を OSPF で学習）。
    cost_suboptimal がある時だけ、ポリシー明示済みの s→d を raw（a 向き有り/b 向き無し）で最適性採点。
    再配送(asbr 指定時)は ASBR 以外の各機が各外部prefを O E2 で学習するかを raw 判定。
    req_filter=(rfv,rfd) は要件フィルタ: rfv が rfd/32 を RIB に持たない（not_contains）を採点。"""
    s_node, d_node = R["s"], R["d"]
    has_cost = bool(cost_fault)
    a_ip = nbr_ip[(s_node, R["a"])]    # s の主経路(a 向き)
    b_ip = nbr_ip[(s_node, R["b"])]    # 予備(b 向き)
    pairs = [(x, y) for x in routers for y in routers if x != y]
    # 外部prefチェック（ASBR以外 × 各外部pref）
    ext_targets = ([(x, ep) for x in routers if x != asbr for ep in EXT_PREFIXES]
                   if asbr else [])
    total = len(pairs) + len(ext_targets)
    base = 100 // total; rem = 100 - base * total
    checks, idx = [], 0
    for (x, y) in pairs:
        pts = base + (1 if idx < rem else 0); idx += 1
        if req_filter and (x, y) == req_filter:
            checks.append({"name": f"{x}: {lo[y]}/32 を RIB に持たない＝ポリシーフィルタ充足",
                           "node": x, "command": "show ip route ospf",
                           "raw": [{"not_regex": rf"{lo[y].replace('.', chr(92)+'.')}/32"}],
                           "points": pts})
        elif has_cost and x == s_node and y == d_node:
            checks.append({"name": f"{x}: {lo[y]}/32 へ主経路({R['a']} 経由・予備{R['b']}でない)＝ポリシー準拠",
                           "node": x, "command": "show ip route ospf",
                           "raw": [{"regex": a_ip.replace(".", r"\.")},
                                   {"not_regex": b_ip.replace(".", r"\.")}],
                           "points": pts})
        else:
            checks.append({"name": f"{x}: {lo[y]}/32 を OSPF で学習(到達)",
                           "node": x, "command": "show ip route ospf",
                           "parser": "show ip route",
                           "find": "vrf.*.address_family.*.routes.*",
                           "match": {"route": f"{lo[y]}/32", "source_protocol": "ospf"},
                           "points": pts})
    for (x, ep) in ext_targets:
        pts = base + (1 if idx < rem else 0); idx += 1
        net, mask, cidr, rx = ep
        checks.append({"name": f"{x}: 外部 {cidr} を O E2 で学習(再配送)",
                       "node": x, "command": "show ip route ospf",
                       "raw": [{"regex": rf"O E2 +{rx}"}],
                       "points": pts})
    return checks


if __name__ == "__main__":
    main()
