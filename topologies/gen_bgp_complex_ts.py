#!/usr/bin/env python3
"""BGP 複合トラブルシュート生成器（Phase 1: 到達性14故障・ENARSI〜CCIE級）。

既存 gen_bgp_troubleshoot / gen_bgp_pathts / gen_bgp_rrts の統合上位版。
7台・4AS・OSPFアンダーレイ・MP-BGP(AF書式必須)・RR/フルメッシュ切替・
Lo間eBGPマルチホップ・経路集約を1トポロジに集約し、レイヤ横断で故障を同時多発させる。

■ アーキテクチャ(3層分離・拡張/合体用の器):
  [1] build_model : 純データのベースラインモデル(routers/sessions/policies/prefixes)
  [2] FAULTS      : 故障=モデルへの変換(applicable/inject/fix)。1エントリ追加=1故障追加
  [3] render_*    : モデル→config/採点/task。underlay描画は将来 --underlay eigrp 差替可

■ 正準トポロジ(役割を物理RT01-07へseedシャッフル):
                 cust(AS65100: 172.16.0-2.0/24)
                ／eBGP        eBGP＼
  mhop ─eBGP─ bw ══ OSPF ══ hub ══ OSPF ══ be ─eBGP─ agg(AS65300: 172.31.0-3.0/24
  (AS65200      │          (RR)            │          →beで/22 summary-only集約)
   Lo間multihop)│           ║              │
   198.51.100.0/24          leaf(192.0.2.0/24起源・eBGPなし=観測点)
  AS65001 = hub/bw/be/leaf。iBGPは全てLo0ピア。--ibgp rr(既定)|fullmesh。

■ ベースライン設計書(task.mdに明記=復旧目標)＝seed毎に要件バリエーション:
  ・primary境界 = bw|be(戻りはprepend×2|3 or MED)
  ・出口制御方式 = lp_pref(primaryでLP150/200/300引き上げ)|lp_depref(backupでLP50/80
    引き下げ<100)|prepend_in(backupでinbound prepend×2|3) — 同じ「primary経由」を3手段で要求
  ・ext接続スワップ = (mhop=bw,agg=be)|(mhop=be,agg=bw) ※IOLはdata3スロットなので常に反対側
  ・運用タグ community 65001:X00 / MED値ペア もseedで変動
  bw/be は iBGP に next-hop-self。mhop側⇄mhop は Lo間 eBGP(multihop 2+static)。
  agg側が /22 summary-only 集約＋default-originate。
  全機 no bgp default ipv4-unicast + address-family ipv4 unicast(activate必須)。

■ Phase1 故障(到達性/設計逸脱で採点可能な14種):
  U: ospf_link_break / lo_not_in_ospf                       (連鎖: BGP症状×IGP原因)
  S: wrong_remote_as / wrong_neighbor_ip / neighbor_shutdown /
     missing_update_source / missing_ebgp_multihop / missing_static_to_peer_lo /
     acl_block_tcp179 / missing_af_activate / rr_reflect_break|mesh_session_missing
  N: missing_nexthop_self
  O: missing_network / wrong_network_mask / aggregate_missing / summary_only_missing

採点: 各機×主要prefixの `show ip route bgp` raw ＋ /22集約有・/24抑制(ガード付き)。
出力: problems/GEN-BGPCX-<seed>/。fix.json は fix_generated.yml 互換。
使い方: gen_bgp_complex_ts.py --repo . --seed <int> [--faults N] [--ibgp rr|fullmesh]
        [--primary auto|bw|be] [--mhop-side auto|bw|be]
        [--egress auto|lp_pref|lp_depref|prepend_in]  (auto=seedから決定)
        --faults 0 でベースライン(検証用・全チェックPASSであるべき)
"""
import argparse
import json
import os
import random

import yaml

import gen_snmpv3_ts as zgen   # --monitoring: ZBX01構築スクリプト/NOC標準SNMPv3を共通利用

CORE = ["hub", "bw", "be", "leaf"]
EXT_AS = {"cust": 65100, "mhop": 65200, "agg": 65300}
CORE_AS = 65001
ROLES = CORE + list(EXT_AS)
CORE_TOPO = [("hub", "bw"), ("hub", "be"), ("hub", "leaf")]
CORE_EDGES = {frozenset(e) for e in CORE_TOPO}

# 宛先プレフィクス(固定=設計書の安定性優先。seedはロール配置とアドレス断片のみ変える)
DEST = {
    "cust": [("Loopback1", "172.16.0.1", "172.16.0.0"),
             ("Loopback2", "172.16.1.1", "172.16.1.0"),
             ("Loopback3", "172.16.2.1", "172.16.2.0")],
    "mhop": [("Loopback1", "198.51.100.1", "198.51.100.0")],
    "agg":  [("Loopback1", "172.31.0.1", "172.31.0.0"),
             ("Loopback2", "172.31.1.1", "172.31.1.0"),
             ("Loopback3", "172.31.2.1", "172.31.2.0"),
             ("Loopback4", "172.31.3.1", "172.31.3.0")],
    "leaf": [("Loopback1", "192.0.2.1", "192.0.2.0")],
}
MASK24 = "255.255.255.0"
AGG_NET, AGG_MASK, AGG_RX = "172.31.0.0", "255.255.252.0", r"172\.31\.0\.0/22"
RM_LP, RM_PREPEND = "RM-LP-PRIMARY", "RM-PREPEND-BACKUP"
RM_LP_B, RM_PREP_IN = "RM-LP-BACKUP", "RM-PREPEND-IN"
RM_MED_P, RM_MED_B = "RM-MED-PRIMARY", "RM-MED-BACKUP"
RM_TAG = "RM-TAG-MHOP"
BGP_PASS = "CCNPBGP"
PL_ACC, PL_DENY = "PL-RM-ACC", "PL-DENY-IN"
ACL_BGP = "BLOCK-BGP"
MHOP_NET = "198.51.100.0"

FAULT_META = {  # type: (category, difficulty)
    "ospf_link_break": ("U", 5), "lo_not_in_ospf": ("U", 4),
    "wrong_remote_as": ("S", 3), "wrong_neighbor_ip": ("S", 3),
    "neighbor_shutdown": ("S", 3), "missing_update_source": ("S", 4),
    "missing_ebgp_multihop": ("S", 5), "missing_static_to_peer_lo": ("S", 4),
    "acl_block_tcp179": ("S", 4), "missing_af_activate": ("S", 5),
    "rr_reflect_break": ("S", 5), "mesh_session_missing": ("S", 4),
    "missing_nexthop_self": ("N", 5),
    "missing_network": ("O", 3), "wrong_network_mask": ("O", 3),
    "aggregate_missing": ("O", 4), "summary_only_missing": ("O", 4),
    # ---- Phase2: 経路選択層(届くが経路が違う)。--policy-faults M で注入 ----
    "rm_filter_accident": ("P", 4),   # bw の LP route-map に誤 deny 節→当該/24だけ出口が反転
    "distribute_list_in": ("P", 4),   # bw の neighbor prefix-list in 誤挿入(道具違いの同種)
    "lp_wrong_value": ("P", 5),       # LP 200→50(backup の既定100に負ける=全cust prefixが反転)
    "lp_wrong_neighbor": ("P", 5),    # LP route-map を mhop 側に誤適用(cust側から消える)
    "prepend_wrong_side": ("P", 5),   # prepend が be でなく bw に付く(戻りが反転)※prepend時
    "med_inverted": ("P", 5),         # bw の MED が大きい(戻りが反転)※med時
    "weight_override": ("P", 5),      # hub が be 隣接に weight 40000→LP設計を上書き(優先順位)
    # ---- Tier1 補完(BGP代表要素) ----
    "password_mismatch": ("S", 4),        # 片側のみ neighbor password→BADAUTH でセッション断
    "max_prefix_low": ("S", 5),           # maximum-prefix 2 誤設定→Idle(PfxCt)・復帰にclear要
    "default_originate_missing": ("O", 3),  # スタブAS(agg)への default-originate 欠落
    "community_no_export": ("P", 5),      # mhop経路のタグが no-export に→ASから出なくなる
    "send_community_missing": ("P", 4),   # bwのsend-community欠落→運用タグがコアに付かない
}
CAT_LIMIT = {"U": 1, "N": 1}          # カテゴリ同時数上限(RR/AGGは種別自体で1回)
POLICY_FAULTS = [k for k, v in FAULT_META.items() if v[0] == "P"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=3,
                    help="到達性系(U/S/N/O)の故障数。0=ベースライン")
    ap.add_argument("--policy-faults", type=int, default=0,
                    help="経路選択系(P)の故障数(Phase2)。合計= faults + policy_faults")
    ap.add_argument("--ibgp", choices=["rr", "fullmesh"], default="rr")
    ap.add_argument("--return-policy", choices=["prepend", "med"], default="prepend",
                    help="cust の戻り経路ポリシー(設計書に反映)")
    ap.add_argument("--primary", choices=["auto", "bw", "be"], default="auto",
                    help="cust の primary 境界(auto=seedから決定)")
    ap.add_argument("--mhop-side", choices=["auto", "bw", "be"], default="auto",
                    help="mhop(AS65200) の接続境界。agg は常に反対側(IOLスロット制約)")
    ap.add_argument("--egress", choices=["auto", "lp_pref", "lp_depref", "prepend_in"],
                    default="auto",
                    help="cust向け出口制御の方式(LP引上げ/LP引下げ/inbound prepend)")
    ap.add_argument("--monitoring", action="store_true",
                    help="Zabbix監視を合体: ZBX01をleafに接続し全機をSNMPv3監視"
                         "(ダッシュボード=切り分けの入口。採点は従来のBGP効果チェックのまま)")
    a = ap.parse_args()
    rnd = random.Random(a.seed)

    # ---- 要件バリエーション(設計書自体をseedで変動。CLIで個別固定も可) ----------
    # ※draw は常に同順で行い、CLI上書きは後から適用(seed再現性を崩さない)
    pri = rnd.choice(["bw", "be"])          # cust の primary 境界
    mside = rnd.choice(["bw", "be"])        # mhop の接続境界(agg は反対側)
    lp_pri = rnd.choice([150, 200, 300])    # primary inbound LP
    comm_tag = f"65001:{rnd.choice(range(100, 1000, 100))}"  # 運用タグ
    med_pri = rnd.choice([10, 20, 50])      # 戻りMED(primary側。backup=×10)
    prepend_n = rnd.choice([2, 3])          # 戻りprepend段数
    egress = rnd.choice(["lp_pref", "lp_depref", "prepend_in"])  # 出口制御方式
    lp_low = rnd.choice([50, 80])           # lp_depref 時の backup LP(<100)
    pin_n = rnd.choice([2, 3])              # prepend_in 時の inbound prepend 段数
    if a.primary != "auto":
        pri = a.primary
    if a.mhop_side != "auto":
        mside = a.mhop_side
    if a.egress != "auto":
        egress = a.egress
    bak = "be" if pri == "bw" else "bw"
    aside = "be" if mside == "bw" else "bw"
    med_bak = med_pri * 10

    # ---- [1] モデル構築 -----------------------------------------------------
    topo = CORE_TOPO + [("bw", "cust"), ("be", "cust"),
                        (mside, "mhop"), (aside, "agg")]
    phys = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(phys)
    R = dict(zip(ROLES, phys))
    role = {v: k for k, v in R.items()}
    routers = [R[r] for r in ROLES]
    as_of = {R[r]: (CORE_AS if r in CORE else EXT_AS[r]) for r in ROLES}

    used = set(); lo = {}
    for r in routers:
        while True:
            k = rnd.randint(1, 99)
            if k not in used:
                used.add(k); lo[r] = f"10.0.{k}.{k}"; break
    usedp = set(); pseg = {}
    for e in topo:
        while True:
            p = rnd.randint(101, 199)
            if p not in usedp:
                usedp.add(p); pseg[e] = f"10.{p}.{p}"; break

    slot = {r: 0 for r in routers}; links = []
    for (ra, rb) in topo:
        x, y = R[ra], R[rb]
        seg = pseg[(ra, rb)]
        links.append({"a": x, "a_if": slot[x], "a_ip": f"{seg}.1",
                      "b": y, "b_if": slot[y], "b_ip": f"{seg}.2",
                      "roles": (ra, rb)})
        slot[x] += 1; slot[y] += 1
    ifaces = {r: [] for r in routers}     # (slot, my_ip, nb)
    for lk in links:
        ifaces[lk["a"]].append((lk["a_if"], lk["a_ip"], lk["b"]))
        ifaces[lk["b"]].append((lk["b_if"], lk["b_ip"], lk["a"]))

    # ---- 監視合体(--monitoring): ZBX01 は leaf に接続(唯一データスロットに空き) ----
    # 監視対象: コア=Loopback0(OSPF) / 外部AS=サイト代表IP(BGP学習) → 故障種別が
    # 「コア赤(IGP/下層)」「サイト赤(BGP)」としてダッシュボードに写る。
    # links/ifaces には足さない(乱数列・故障選択のseed互換を保つ)。emission時のみ追加。
    MON_NET = zgen.POLLER_NET                    # 10.99.0 (/29, .1=leaf .2=ZBX01 .3=検証)
    zbx_leaf, zbx_slot = R["leaf"], slot[R["leaf"]]
    mon_ip = {r: (lo[r] if role[r] in CORE else DEST[role[r]][0][1]) for r in routers}

    def link_of(x, y):
        for lk in links:
            if {lk["a"], lk["b"]} == {x, y}:
                return lk
        raise KeyError

    def if_ip(x, y):
        lk = link_of(x, y)
        return (lk["a_ip"], lk["b_ip"]) if lk["a"] == x else (lk["b_ip"], lk["a_ip"])

    def if_slot(x, y):
        for (s, ip, nb) in ifaces[x]:
            if nb == y:
                return s
        raise KeyError

    # BGP セッション(モデル)。kind: ibgp / edirect / emhop
    sessions = []
    if a.ibgp == "rr":
        ipairs = [("hub", "bw"), ("hub", "be"), ("hub", "leaf")]
    else:
        ipairs = [(x, y) for i, x in enumerate(CORE) for y in CORE[i + 1:]]
    for (x, y) in ipairs:
        sessions.append({"kind": "ibgp", "x": R[x], "y": R[y],
                         "x_ip": lo[R[x]], "y_ip": lo[R[y]]})
    for (x, y) in [("bw", "cust"), ("be", "cust"), (aside, "agg")]:
        xi, yi = if_ip(R[x], R[y])
        sessions.append({"kind": "edirect", "x": R[x], "y": R[y],
                         "x_ip": xi, "y_ip": yi})
    sessions.append({"kind": "emhop", "x": R[mside], "y": R["mhop"],
                     "x_ip": lo[R[mside]], "y_ip": lo[R["mhop"]]})

    def sess_of(node):
        out = []
        for s in sessions:
            if s["x"] == node:
                out.append((s, s["y"], s["y_ip"]))
            elif s["y"] == node:
                out.append((s, s["x"], s["x_ip"]))
        return out

    def sid(s):
        return f"{s['x']}~{s['y']}"

    # ---- [2] 故障選択・注入(モデルへのマーク) --------------------------------
    # mut: 描画/修復が参照する変換マーク群
    mut = {"ospf_if_off": set(),        # (node, slot)
           "ospf_lo_off": set(),        # node
           "remote_as_wrong": {},       # (node, sid) -> wrong_as
           "neighbor_ip_wrong": {},     # (node, sid) -> wrong_ip
           "shutdown": set(),           # (node, sid)
           "no_upd_src": set(),         # (node, sid)
           "no_multihop": set(),        # (node, sid)
           "no_static": set(),          # node (mhopセッション当事者)
           "acl": set(),                # (node, slot)
           "no_activate": set(),        # (node, sid)
           "rr_break": False,
           "mesh_missing": None,        # sid
           "no_nhs": set(),             # node (bw|be)
           "net_missing": {},           # node -> (net, mask)
           "net_wrongmask": {},         # node -> (net, badmask, mask)
           "agg_missing": False, "summary_only_missing": False,
           # Phase2 (P) ※bw/be は変種の pri/bak/mside/aside に読み替え
           "rm_filter": None,           # 誤denyされる cust /24 (pri 上)
           "dlist_in": None,            # prefix-list in で消される cust /24 (pri 上)
           "lp_value": None,            # 誤ったLP値(正=lp_pri)
           "lp_on_mhop": False,         # LP route-map を mhop 側に誤適用(mside==pri時)
           "prepend_on_bw": False,      # prepend が pri 側に付く(bak 側に無い)
           "med_bw_value": None,        # pri の誤MED(正=med_pri)
           "weight_be": False,          # hub が bak 隣接に weight 40000
           # Tier1 補完
           "password": set(),           # (node, sid) 片側のみ password
           "maxpfx": set(),             # (node, sid) maximum-prefix 2
           "no_deforig": False,         # aside の default-originate 欠落
           "comm_no_export": False,     # RM-TAG が no-export を付ける(mside 上)
           "no_send_comm": False}       # mside の send-community 欠落

    faults = []
    used_node, used_sess, cat_count = set(), set(), {}
    simple_af = {R["leaf"], R["cust"], R["agg"], R["mhop"]}  # AF行がactivateのみの側

    # ---- Phase2: 経路選択故障を先に選ぶ(bw/be/hub を消費・到達性系は残りから) ----
    pol_pool = [p for p in POLICY_FAULTS
                if not (p == "prepend_wrong_side" and a.return_policy != "prepend")
                and not (p == "med_inverted" and a.return_policy != "med")
                # weight は fullmesh だと be が広告を止め実効が薄い(双安定知見)→rr限定
                and not (p == "weight_override" and a.ibgp != "rr")
                # LP誤適用先は「pri の LP map + 同居 mhop セッション」前提
                and not (p == "lp_wrong_neighbor"
                         and (mside != pri or egress != "lp_pref"))
                # 誤deny節は「pri側 map から漏れると出口反転」が成立する lp_pref 限定
                # (backup側 map から漏れても pri が勝ったまま=採点に現れない)
                and not (p == "rm_filter_accident" and egress != "lp_pref")
                # LP値故障は LP を使う方式のみ
                and not (p == "lp_wrong_value" and egress == "prepend_in")]
    pol_attempts = 0
    npol = 0
    lp_node = R[bak] if egress == "lp_depref" else R[pri]  # LP map の居場所
    while npol < a.policy_faults and pol_attempts < 200:
        pol_attempts += 1
        ft = rnd.choice(pol_pool)
        need = {"weight_override": [R["hub"]],
                "prepend_wrong_side": [R[pri], R[bak]],
                "community_no_export": [R[mside]],
                "send_community_missing": [R[mside]],
                "lp_wrong_value": [lp_node]}.get(ft, [R[pri]])
        if any(v in used_node for v in need):
            continue
        for v in need:
            used_node.add(v)
        f = {"type": ft, "node": need[0], "difficulty": FAULT_META[ft][1]}
        if ft == "rm_filter_accident":
            mut["rm_filter"] = rnd.choice(DEST["cust"])[2]
            f["prefix"] = mut["rm_filter"]
        elif ft == "distribute_list_in":
            mut["dlist_in"] = rnd.choice(DEST["cust"])[2]
            f["prefix"] = mut["dlist_in"]
        elif ft == "lp_wrong_value":
            # lp_pref: 100未満に下げて負けさせる / lp_depref: 100超に上げて勝たせる
            mut["lp_value"] = 150 if egress == "lp_depref" else 50
        elif ft == "lp_wrong_neighbor":
            mut["lp_on_mhop"] = True
        elif ft == "prepend_wrong_side":
            mut["prepend_on_bw"] = True
        elif ft == "med_inverted":
            mut["med_bw_value"] = med_bak * 2
        elif ft == "weight_override":
            mut["weight_be"] = True
        elif ft == "community_no_export":
            mut["comm_no_export"] = True
        elif ft == "send_community_missing":
            mut["no_send_comm"] = True
        faults.append(f)
        npol += 1

    def pick_sess(kinds, victim_pool=None):
        cands = []
        for s in sessions:
            if sid(s) in used_sess or s["kind"] not in kinds:
                continue
            for v in (s["x"], s["y"]):
                if v in used_node:
                    continue
                if victim_pool and v not in victim_pool:
                    continue
                cands.append((s, v))
        return rnd.choice(cands) if cands else None

    def commit_sess(s, v, ftype, extra=None):
        used_sess.add(sid(s)); used_node.add(v)
        f = {"type": ftype, "node": v, "session": sid(s),
             "peer": s["y"] if v == s["x"] else s["x"],
             "difficulty": FAULT_META[ftype][1]}
        if extra:
            f.update(extra)
        faults.append(f)
        return f

    catalog = [k for k in FAULT_META
               if FAULT_META[k][0] != "P"   # P系は --policy-faults 側で選ぶ
               and k != ("mesh_session_missing" if a.ibgp == "rr" else "rr_reflect_break")]
    attempts = 0
    while len(faults) < a.faults + npol and attempts < 1000:
        attempts += 1
        ft = rnd.choice(catalog)
        cat = FAULT_META[ft][0]
        if cat in CAT_LIMIT and cat_count.get(cat, 0) >= CAT_LIMIT[cat]:
            continue
        if ft == "ospf_link_break":
            edges = [lk for lk in links if frozenset(lk["roles"]) in CORE_EDGES
                     and lk["a"] not in used_node and lk["b"] not in used_node]
            if not edges:
                continue
            lk = rnd.choice(edges)
            v = rnd.choice([lk["a"], lk["b"]])
            s_ = if_slot(v, lk["b"] if v == lk["a"] else lk["a"])
            # コアはスター型なので、壊れたリンクで孤立するのは非hub側
            nonhub = lk["a"] if role[lk["a"]] != "hub" else lk["b"]
            mut["ospf_if_off"].add((v, s_))
            used_node.add(lk["a"]); used_node.add(lk["b"])
            faults.append({"type": ft, "node": v, "slot": s_,
                           "iol_if": f"Ethernet0/{s_}", "isolates": nonhub,
                           "difficulty": FAULT_META[ft][1]})
        elif ft == "lo_not_in_ospf":
            cands = [R[r] for r in CORE if R[r] not in used_node]
            if not cands:
                continue
            v = rnd.choice(cands); used_node.add(v)
            mut["ospf_lo_off"].add(v)
            faults.append({"type": ft, "node": v, "difficulty": FAULT_META[ft][1]})
        elif ft == "wrong_remote_as":
            pk = pick_sess({"ibgp", "edirect"})
            if not pk:
                continue
            s, v = pk
            peer = s["y"] if v == s["x"] else s["x"]
            wrong = as_of[peer] + 1
            f = commit_sess(s, v, ft, {"wrong_as": wrong})
            mut["remote_as_wrong"][(v, sid(s))] = wrong
        elif ft == "wrong_neighbor_ip":
            pk = pick_sess({"edirect"})
            if not pk:
                continue
            s, v = pk
            good = s["y_ip"] if v == s["x"] else s["x_ip"]
            wrong = good.rsplit(".", 1)[0] + ".6"
            commit_sess(s, v, ft, {"wrong_ip": wrong, "good_ip": good})
            mut["neighbor_ip_wrong"][(v, sid(s))] = wrong
        elif ft == "neighbor_shutdown":
            pk = pick_sess({"ibgp", "edirect", "emhop"})
            if not pk:
                continue
            s, v = pk
            commit_sess(s, v, ft)
            mut["shutdown"].add((v, sid(s)))
        elif ft == "missing_update_source":
            pk = pick_sess({"ibgp", "emhop"})
            if not pk:
                continue
            s, v = pk
            commit_sess(s, v, ft)
            mut["no_upd_src"].add((v, sid(s)))
        elif ft == "missing_ebgp_multihop":
            pk = pick_sess({"emhop"})
            if not pk:
                continue
            s, v = pk
            commit_sess(s, v, ft)
            mut["no_multihop"].add((v, sid(s)))
        elif ft == "missing_static_to_peer_lo":
            pk = pick_sess({"emhop"})
            if not pk:
                continue
            s, v = pk
            commit_sess(s, v, ft)
            mut["no_static"].add(v)
        elif ft == "acl_block_tcp179":
            pk = pick_sess({"edirect"})
            if not pk:
                continue
            s, v = pk
            peer = s["y"] if v == s["x"] else s["x"]
            sl = if_slot(v, peer)
            commit_sess(s, v, ft, {"slot": sl, "iol_if": f"Ethernet0/{sl}"})
            mut["acl"].add((v, sl))
        elif ft == "missing_af_activate":
            pk = pick_sess({"ibgp", "edirect", "emhop"}, victim_pool=simple_af)
            if not pk:
                continue
            s, v = pk
            commit_sess(s, v, ft)
            mut["no_activate"].add((v, sid(s)))
        elif ft == "password_mismatch":
            pk = pick_sess({"ibgp", "edirect", "emhop"})
            if not pk:
                continue
            s, v = pk
            commit_sess(s, v, ft)
            mut["password"].add((v, sid(s)))
        elif ft == "max_prefix_low":
            # 受信数が確実に閾値2を超えるセッション: bw←cust(3本) / be←agg(4本)
            cands = [(s, s["x"]) for s in sessions if s["kind"] == "edirect"
                     and role[s["y"]] in ("cust", "agg")
                     and sid(s) not in used_sess
                     and s["x"] not in used_node and s["y"] not in used_node]
            if not cands:
                continue
            s, v = rnd.choice(cands)
            commit_sess(s, v, ft)
            mut["maxpfx"].add((v, sid(s)))
        elif ft == "default_originate_missing":
            if mut["no_deforig"] or R[aside] in used_node:
                continue
            used_node.add(R[aside])
            mut["no_deforig"] = True
            faults.append({"type": ft, "node": R[aside],
                           "difficulty": FAULT_META[ft][1]})
        elif ft == "rr_reflect_break":
            if mut["rr_break"] or R["hub"] in used_node \
               or R["bw"] in used_node or R["be"] in used_node:
                continue
            mut["rr_break"] = True
            used_node.add(R["hub"])
            faults.append({"type": ft, "node": R["hub"],
                           "detail": "bw/be の route-reflector-client 欠落(非client同士は反射されない)",
                           "difficulty": FAULT_META[ft][1]})
        elif ft == "mesh_session_missing":
            cands = [s for s in sessions if s["kind"] == "ibgp"
                     and role[s["x"]] != "hub" and role[s["y"]] != "hub"
                     and sid(s) not in used_sess
                     and s["x"] not in used_node and s["y"] not in used_node]
            if not cands or mut["mesh_missing"]:
                continue
            s = rnd.choice(cands)
            used_sess.add(sid(s)); used_node.add(s["x"]); used_node.add(s["y"])
            mut["mesh_missing"] = sid(s)
            faults.append({"type": ft, "node": s["x"], "peer": s["y"],
                           "session": sid(s), "difficulty": FAULT_META[ft][1]})
        elif ft == "missing_nexthop_self":
            cands = [R[r] for r in ("bw", "be") if R[r] not in used_node]
            if not cands:
                continue
            v = rnd.choice(cands); used_node.add(v)
            mut["no_nhs"].add(v)
            faults.append({"type": ft, "node": v, "difficulty": FAULT_META[ft][1]})
        elif ft in ("missing_network", "wrong_network_mask"):
            cands = [R[r] for r in DEST if R[r] not in used_node]
            if not cands:
                continue
            v = rnd.choice(cands); used_node.add(v)
            ent = rnd.choice(DEST[role[v]])
            if ft == "missing_network":
                mut["net_missing"][v] = (ent[2], MASK24)
            else:
                mut["net_wrongmask"][v] = (ent[2], "255.255.254.0", MASK24)
            faults.append({"type": ft, "node": v, "prefix": ent[2],
                           "difficulty": FAULT_META[ft][1]})
        elif ft in ("aggregate_missing", "summary_only_missing"):
            if mut["agg_missing"] or mut["summary_only_missing"] \
               or R[aside] in used_node:
                continue
            used_node.add(R[aside])
            mut[ft] = True
            faults.append({"type": ft, "node": R[aside],
                           "difficulty": FAULT_META[ft][1]})
    if (a.faults + a.policy_faults) > 0 and not faults:
        raise SystemExit("故障を配置できなかった")

    # ---- 症状モデル(代表チケット選定用の簡易BGP伝播シミュレータ) --------------
    def sim_missing():
        up = {}
        iso = {f["isolates"] for f in faults if f["type"] == "ospf_link_break"}
        for s in sessions:
            ok = True
            if s["kind"] == "ibgp" and (s["x"] in iso or s["y"] in iso or
                                        s["x"] in mut["ospf_lo_off"] or
                                        s["y"] in mut["ospf_lo_off"]):
                ok = False
            if sid(s) == mut["mesh_missing"]:
                ok = False
            for v in (s["x"], s["y"]):
                k = (v, sid(s))
                if k in mut["remote_as_wrong"] or k in mut["neighbor_ip_wrong"] \
                   or k in mut["shutdown"] or k in mut["no_upd_src"] \
                   or k in mut["no_multihop"] or k in mut["password"] \
                   or k in mut["maxpfx"]:
                    ok = False
            if s["kind"] == "emhop" and (mut["no_static"] & {s["x"], s["y"]}):
                ok = False
            if any((v, if_slot(v, s["y"] if v == s["x"] else s["x"])) in mut["acl"]
                   for v in (s["x"], s["y"]) if s["kind"] == "edirect"):
                ok = False
            up[sid(s)] = ok
        blocked_af = {sid(s) for s in sessions
                      if any((v, sid(s)) in mut["no_activate"] for v in (s["x"], s["y"]))}
        # 起源(agg集約は後段)
        origin = {}
        for rl, ents in DEST.items():
            for (_, _, net) in ents:
                if mut["net_missing"].get(R[rl], ("",))[0] == net:
                    continue
                if mut["net_wrongmask"].get(R[rl], ("",))[0] == net:
                    continue
                origin.setdefault(R[rl], []).append(net)
        # tbl[r][net] = src ("orig"|"ebgp"|"ibgp") / from-peer 記録
        tbl = {r: {} for r in routers}
        frm = {r: {} for r in routers}
        for r, nets in origin.items():
            for n in nets:
                tbl[r][n] = "orig"
        agg_active = False
        for _ in range(12):
            # aside(集約元境界) の集約生成
            if not mut["agg_missing"] and any(n.startswith("172.31.") for n in tbl[R[aside]]):
                if "AGG22" not in tbl[R[aside]]:
                    tbl[R[aside]]["AGG22"] = "orig"; agg_active = True
            for s in sessions:
                if not up[sid(s)] or sid(s) in blocked_af:
                    continue
                for (src, dst) in ((s["x"], s["y"]), (s["y"], s["x"])):
                    for n, how in list(tbl[src].items()):
                        if how == "invalid":
                            continue
                        # summary-only: aside は /24 を広告しない(自表には保持)
                        if src == R[aside] and n.startswith("172.31.") and n != "AGG22" \
                           and not mut["agg_missing"] and not mut["summary_only_missing"]:
                            continue
                        # no-export誤付与: mhop経路はコアからeBGPへ出ない
                        if mut["comm_no_export"] and n == MHOP_NET \
                           and role[src] in ("hub", "bw", "be", "leaf") \
                           and s["kind"] != "ibgp":
                            continue
                        if how == "ibgp" and s["kind"] == "ibgp":
                            if a.ibgp == "fullmesh" or role[src] != "hub":
                                continue
                            fp = frm[src].get(n)
                            if mut["rr_break"] and fp in (R["bw"], R["be"]) \
                               and dst in (R["bw"], R["be"]):
                                continue
                        if n in tbl[dst]:
                            continue
                        val = "ebgp" if s["kind"] != "ibgp" else "ibgp"
                        if s["kind"] == "ibgp" and src in mut["no_nhs"] and how == "ebgp":
                            tbl[dst][n] = "invalid"
                            continue
                        tbl[dst][n] = val
                        frm[dst][n] = src
        allnets = [n for ents in DEST.values() for (_, _, n) in ents] + ["AGG22"]
        missing = []
        for r in routers:
            for n in allnets:
                if n == "AGG22" and role[r] == "agg":
                    continue
                own = any(n == net for (_, _, net) in DEST.get(role[r], []))
                if own:
                    continue
                if n.startswith("172.31.") and n != "AGG22":
                    continue     # /24到達は/22経由で担保(抑制対象なので欠落扱いにしない)
                if tbl[r].get(n) in (None, "invalid"):
                    missing.append((r, n))
        return missing

    missing = sim_missing() if faults else []
    fwd_pol = {"rm_filter_accident", "distribute_list_in", "lp_wrong_value",
               "lp_wrong_neighbor", "weight_override"}
    ret_pol = {"prepend_wrong_side", "med_inverted"}
    ftypes = {f["type"] for f in faults}
    if missing:
        rep = sorted(missing)[0]
        rep_txt = (f"**{rep[0]} から `{'172.31.0.0/22 (集約)' if rep[1] == 'AGG22' else rep[1] + '/24'}` "
                   f"へ到達できない。**")
    elif ftypes & fwd_pol:
        rep_txt = ("**AS65100(172.16.x)宛のトラフィックが、設計上の primary 側でなく "
                   "backup 側の境界を通っている（到達はする）。**")
    elif ftypes & ret_pol:
        rep_txt = ("**AS65100 からコア宛の戻りトラフィックが、設計上の primary 側でなく "
                   "backup 側から入ってくる（到達はする）。**")
    elif ftypes & {"aggregate_missing", "summary_only_missing"}:
        rep_txt = "**コアのルーティングテーブルが設計(集約)と異なる。**"
    elif "send_community_missing" in ftypes:
        rep_txt = (f"**AS65200 経路に付くはずの運用タグ({comm_tag})が"
                   "コアで確認できない。**")
    elif "default_originate_missing" in ftypes:
        rep_txt = "**AS65300 がデフォルトルートを受信していない（設計では配布される）。**"
    else:
        rep_txt = "**設計と異なる状態がある。**"

    # ---- [3] 描画: config ---------------------------------------------------
    def render(Rn):
        rl = role[Rn]
        L = [f"! {Rn} (role={rl}, AS={as_of[Rn]}) 初期構成"]
        if any((Rn, s_) in mut["acl"] for (s_, ip, nb) in ifaces[Rn]):
            L += [f"ip access-list extended {ACL_BGP}",
                  " deny tcp any any eq bgp", " deny tcp any eq bgp any",
                  " permit ip any any", "!"]
        L += ["interface Loopback0", f" ip address {lo[Rn]} 255.255.255.255"]
        if rl in CORE and Rn not in mut["ospf_lo_off"]:
            L.append(" ip ospf 1 area 0")
        L.append("!")
        for (name, ip, net) in DEST.get(rl, []):
            L += [f"interface {name}", f" ip address {ip} {MASK24}", "!"]
        for (s_, ip, nb) in sorted(ifaces[Rn]):
            L += [f"interface {{{{ links[{s_}] }}}}",
                  f" ip address {ip} 255.255.255.252"]
            if (Rn, s_) in mut["acl"]:
                L.append(f" ip access-group {ACL_BGP} in")
            if rl in CORE and role[nb] in CORE and (Rn, s_) not in mut["ospf_if_off"]:
                L.append(" ip ospf 1 area 0")
            L += [" no shutdown", "!"]
        # 監視合体: leaf のポーラ向き IF(/29)。OSPF area0 で網内へ広告
        if a.monitoring and Rn == zbx_leaf:
            L += [f"interface {{{{ links[{zbx_slot}] }}}}",
                  " description === to ZBX01(poller) ===",
                  f" ip address {MON_NET}.1 255.255.255.248",
                  " ip ospf 1 area 0", " no shutdown", "!"]
        # multihop 用 static
        if rl in (mside, "mhop"):
            peer = R["mhop"] if rl == mside else R[mside]
            if Rn not in mut["no_static"]:
                nh = if_ip(peer, Rn)[0]
                L.append(f"ip route {lo[peer]} 255.255.255.255 {nh}")
                L.append("!")
        if rl in CORE:
            L += ["router ospf 1", f" router-id {lo[Rn]}", "!"]
        # route-map / prefix-list（ポリシー層。Phase2 故障はここを歪める）
        prepend_str = " ".join([str(CORE_AS)] * prepend_n)
        pin_str = " ".join([str(EXT_AS["cust"])] * pin_n)
        if rl == pri:
            if egress == "lp_pref":
                if mut["rm_filter"]:
                    L += [f"ip prefix-list {PL_ACC} seq 5 permit {mut['rm_filter']}/24",
                          f"route-map {RM_LP} deny 5",
                          f" match ip address prefix-list {PL_ACC}"]
                L += [f"route-map {RM_LP} permit 10",
                      f" set local-preference {mut['lp_value'] or lp_pri}", "!"]
            if mut["dlist_in"]:
                L += [f"ip prefix-list {PL_DENY} seq 5 deny {mut['dlist_in']}/24",
                      f"ip prefix-list {PL_DENY} seq 10 permit 0.0.0.0/0 le 32", "!"]
            if a.return_policy == "med":
                L += [f"route-map {RM_MED_P} permit 10",
                      f" set metric {mut['med_bw_value'] or med_pri}", "!"]
            elif mut["prepend_on_bw"]:
                L += [f"route-map {RM_PREPEND} permit 10",
                      f" set as-path prepend {prepend_str}", "!"]
        if rl == mside:
            L += [f"route-map {RM_TAG} permit 10",
                  f" set community {'no-export' if mut['comm_no_export'] else comm_tag}",
                  "!"]
        if rl == bak:
            if egress == "lp_depref":
                L += [f"route-map {RM_LP_B} permit 10",
                      f" set local-preference {mut['lp_value'] or lp_low}", "!"]
            elif egress == "prepend_in":
                L += [f"route-map {RM_PREP_IN} permit 10",
                      f" set as-path prepend {pin_str}", "!"]
            if a.return_policy == "med":
                L += [f"route-map {RM_MED_B} permit 10",
                      f" set metric {med_bak}", "!"]
            elif not mut["prepend_on_bw"]:
                L += [f"route-map {RM_PREPEND} permit 10",
                      f" set as-path prepend {prepend_str}", "!"]
        # BGP
        L += [f"router bgp {as_of[Rn]}", f" bgp router-id {lo[Rn]}",
              " bgp log-neighbor-changes", " no bgp default ipv4-unicast"]
        af = [" address-family ipv4 unicast"]
        for (s, peer, pip) in sess_of(Rn):
            k = (Rn, sid(s))
            nip = mut["neighbor_ip_wrong"].get(k, pip)
            ras = mut["remote_as_wrong"].get(k, as_of[peer])
            L.append(f" neighbor {nip} remote-as {ras}")
            if s["kind"] in ("ibgp", "emhop") and k not in mut["no_upd_src"]:
                L.append(f" neighbor {nip} update-source Loopback0")
            if s["kind"] == "emhop" and k not in mut["no_multihop"]:
                L.append(f" neighbor {nip} ebgp-multihop 2")
            if k in mut["shutdown"]:
                L.append(f" neighbor {nip} shutdown")
            if k in mut["password"]:
                L.append(f" neighbor {nip} password {BGP_PASS}")
            if k not in mut["no_activate"]:
                af.append(f"  neighbor {nip} activate")
                if k in mut["maxpfx"]:
                    af.append(f"  neighbor {nip} maximum-prefix 2")
                # 運用タグ設計: コア iBGP は send-community(mside の欠落故障あり)
                if s["kind"] == "ibgp" and rl in CORE \
                   and not (rl == mside and mut["no_send_comm"]):
                    af.append(f"  neighbor {nip} send-community")
                if rl == mside and role[peer] == "mhop" and not mut["lp_on_mhop"]:
                    af.append(f"  neighbor {nip} route-map {RM_TAG} in")
                if rl == aside and role[peer] == "agg" and not mut["no_deforig"]:
                    af.append(f"  neighbor {nip} default-originate")
                if rl == "hub" and a.ibgp == "rr" and s["kind"] == "ibgp":
                    if not (mut["rr_break"] and peer in (R["bw"], R["be"])):
                        af.append(f"  neighbor {nip} route-reflector-client")
                if rl == "hub" and mut["weight_be"] and peer == R[bak]:
                    af.append(f"  neighbor {nip} weight 40000")
                if rl in ("bw", "be") and s["kind"] == "ibgp" and Rn not in mut["no_nhs"]:
                    af.append(f"  neighbor {nip} next-hop-self")
                if rl == pri and role[peer] == "cust":
                    if egress == "lp_pref" and not mut["lp_on_mhop"]:
                        af.append(f"  neighbor {nip} route-map {RM_LP} in")
                    if mut["dlist_in"]:
                        af.append(f"  neighbor {nip} prefix-list {PL_DENY} in")
                    if a.return_policy == "med":
                        af.append(f"  neighbor {nip} route-map {RM_MED_P} out")
                    elif mut["prepend_on_bw"]:
                        af.append(f"  neighbor {nip} route-map {RM_PREPEND} out")
                if rl == mside and role[peer] == "mhop" and mut["lp_on_mhop"]:
                    af.append(f"  neighbor {nip} route-map {RM_LP} in")
                if rl == bak and role[peer] == "cust":
                    if egress == "lp_depref":
                        af.append(f"  neighbor {nip} route-map {RM_LP_B} in")
                    elif egress == "prepend_in":
                        af.append(f"  neighbor {nip} route-map {RM_PREP_IN} in")
                    if a.return_policy == "med":
                        af.append(f"  neighbor {nip} route-map {RM_MED_B} out")
                    elif not mut["prepend_on_bw"]:
                        af.append(f"  neighbor {nip} route-map {RM_PREPEND} out")
        for (name, ip, net) in DEST.get(rl, []):
            if mut["net_missing"].get(Rn, ("",))[0] == net:
                continue
            m = MASK24
            if mut["net_wrongmask"].get(Rn, ("",))[0] == net:
                m = mut["net_wrongmask"][Rn][1]
            af.append(f"  network {net} mask {m}")
        if rl == aside and not mut["agg_missing"]:
            so = "" if mut["summary_only_missing"] else " summary-only"
            af.append(f"  aggregate-address {AGG_NET} {AGG_MASK}{so}")
        # 監視合体: ポーラ網を leaf が BGP 起源(外部ASからの SNMP 戻り経路)
        if a.monitoring and Rn == zbx_leaf:
            af.append(f"  network {MON_NET}.0 mask 255.255.255.248")
        L += af + [" exit-address-family", "!"]
        # 監視合体: 全機に NOC 標準 SNMPv3(監視は前提インフラ。故障注入の対象外)
        if a.monitoring:
            L += ["! --- SNMPv3 (NOC 監視標準) ---",
                  f"snmp-server view {zgen.V3_VIEW} iso included",
                  f"snmp-server group {zgen.V3_GROUP} v3 priv read {zgen.V3_VIEW}",
                  "snmp-server location CCNP-LAB",
                  zgen.user_line(), "!"]
        return L

    # ---- fix ----------------------------------------------------------------
    def rb(Rn):
        return f"router bgp {as_of[Rn]}"

    def rb_af(Rn):
        return [rb(Rn), "address-family ipv4 unicast"]

    def peer_ip_of(f):
        s = next(s for s in sessions if sid(s) == f["session"])
        return s["y_ip"] if f["node"] == s["x"] else s["x_ip"]

    def healthy_neighbor_lines(Rn, s, peer, pip):
        """設計(健全)状態での neighbor 行一式(global, af)。セッション再作成系の
        fix はこれで復元する — remote-as/activate だけ戻すとポリシー route-map や
        send-community/next-hop-self/default-originate が失われる(実機で発覚)。"""
        rl = role[Rn]
        g = [f"neighbor {pip} remote-as {as_of[peer]}"]
        if s["kind"] in ("ibgp", "emhop"):
            g.append(f"neighbor {pip} update-source Loopback0")
        if s["kind"] == "emhop":
            g.append(f"neighbor {pip} ebgp-multihop 2")
        af = [f"neighbor {pip} activate"]
        if s["kind"] == "ibgp" and rl in CORE:
            af.append(f"neighbor {pip} send-community")
        if rl == mside and role[peer] == "mhop":
            af.append(f"neighbor {pip} route-map {RM_TAG} in")
        if rl == aside and role[peer] == "agg":
            af.append(f"neighbor {pip} default-originate")
        if rl == "hub" and a.ibgp == "rr" and s["kind"] == "ibgp":
            af.append(f"neighbor {pip} route-reflector-client")
        if rl in ("bw", "be") and s["kind"] == "ibgp":
            af.append(f"neighbor {pip} next-hop-self")
        if rl == pri and role[peer] == "cust":
            if egress == "lp_pref":
                af.append(f"neighbor {pip} route-map {RM_LP} in")
            if a.return_policy == "med":
                af.append(f"neighbor {pip} route-map {RM_MED_P} out")
        if rl == bak and role[peer] == "cust":
            if egress == "lp_depref":
                af.append(f"neighbor {pip} route-map {RM_LP_B} in")
            elif egress == "prepend_in":
                af.append(f"neighbor {pip} route-map {RM_PREP_IN} in")
            if a.return_policy == "med":
                af.append(f"neighbor {pip} route-map {RM_MED_B} out")
            else:
                af.append(f"neighbor {pip} route-map {RM_PREPEND} out")
        return g, af

    def fault_fix(f):
        ft, Rn = f["type"], f["node"]
        if ft == "ospf_link_break":
            return [{"node": Rn, "parents": f"interface {f['iol_if']}",
                     "lines": ["ip ospf 1 area 0"]}]
        if ft == "lo_not_in_ospf":
            return [{"node": Rn, "parents": "interface Loopback0",
                     "lines": ["ip ospf 1 area 0"]}]
        if ft == "wrong_remote_as":
            return [{"node": Rn, "parents": rb(Rn),
                     "lines": [f"neighbor {peer_ip_of(f)} remote-as {as_of[f['peer']]}"]}]
        if ft == "wrong_neighbor_ip":
            s = next(s for s in sessions if sid(s) == f["session"])
            g, af = healthy_neighbor_lines(Rn, s, f["peer"], f["good_ip"])
            return [{"node": Rn, "parents": rb(Rn),
                     "lines": [f"no neighbor {f['wrong_ip']} remote-as {as_of[f['peer']]}"]
                              + g},
                    {"node": Rn, "parents": rb_af(Rn), "lines": af}]
        if ft == "neighbor_shutdown":
            return [{"node": Rn, "parents": rb(Rn),
                     "lines": [f"no neighbor {peer_ip_of(f)} shutdown"]}]
        if ft == "missing_update_source":
            return [{"node": Rn, "parents": rb(Rn),
                     "lines": [f"neighbor {peer_ip_of(f)} update-source Loopback0"]}]
        if ft == "missing_ebgp_multihop":
            return [{"node": Rn, "parents": rb(Rn),
                     "lines": [f"neighbor {peer_ip_of(f)} ebgp-multihop 2"]}]
        if ft == "missing_static_to_peer_lo":
            peer = f["peer"]
            nh = if_ip(peer, Rn)[0]
            return [{"node": Rn,
                     "lines": [f"ip route {lo[peer]} 255.255.255.255 {nh}"]}]
        if ft == "acl_block_tcp179":
            return [{"node": Rn, "parents": f"interface {f['iol_if']}",
                     "lines": [f"no ip access-group {ACL_BGP} in"]}]
        if ft == "missing_af_activate":
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"neighbor {peer_ip_of(f)} activate"]}]
        if ft == "rr_reflect_break":
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"neighbor {lo[R['bw']]} route-reflector-client",
                               f"neighbor {lo[R['be']]} route-reflector-client"]}]
        if ft == "mesh_session_missing":
            s = next(s for s in sessions if sid(s) == f["session"])
            out = []
            for (v, peer, pip) in ((s["x"], s["y"], s["y_ip"]),
                                   (s["y"], s["x"], s["x_ip"])):
                g, af = healthy_neighbor_lines(v, s, peer, pip)
                out.append({"node": v, "parents": rb(v), "lines": g})
                out.append({"node": v, "parents": rb_af(v), "lines": af})
            return out
        if ft == "missing_nexthop_self":
            lines = []
            for (s, peer, pip) in sess_of(Rn):
                if s["kind"] == "ibgp":
                    lines.append(f"neighbor {pip} next-hop-self")
            return [{"node": Rn, "parents": rb_af(Rn), "lines": lines}]
        if ft == "missing_network":
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"network {f['prefix']} mask {MASK24}"]}]
        if ft == "wrong_network_mask":
            bad = mut["net_wrongmask"][Rn][1]
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"no network {f['prefix']} mask {bad}",
                               f"network {f['prefix']} mask {MASK24}"]}]
        # ---- Phase2 (P): ポリシー変更は route-refresh が要る→ soft clear を併投 ----
        soft = {"node": Rn, "exec": ["clear ip bgp * soft"]}
        cust_ip_pri = if_ip(R["cust"], R[pri])[0]
        cust_ip_bak = if_ip(R["cust"], R[bak])[0]
        prepend_str = " ".join([str(CORE_AS)] * prepend_n)
        if ft == "rm_filter_accident":
            return [{"node": Rn, "lines": [f"no route-map {RM_LP} deny 5"]}, soft]
        if ft == "distribute_list_in":
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"no neighbor {cust_ip_pri} prefix-list {PL_DENY} in"]}, soft]
        if ft == "lp_wrong_value":
            if egress == "lp_depref":
                return [{"node": Rn, "parents": [f"route-map {RM_LP_B} permit 10"],
                         "lines": [f"set local-preference {lp_low}"]}, soft]
            return [{"node": Rn, "parents": [f"route-map {RM_LP} permit 10"],
                     "lines": [f"set local-preference {lp_pri}"]}, soft]
        if ft == "lp_wrong_neighbor":
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"no neighbor {lo[R['mhop']]} route-map {RM_LP} in",
                               f"neighbor {lo[R['mhop']]} route-map {RM_TAG} in",
                               f"neighbor {cust_ip_pri} route-map {RM_LP} in"]}, soft]
        if ft == "prepend_wrong_side":
            return [{"node": R[pri], "parents": rb_af(R[pri]),
                     "lines": [f"no neighbor {cust_ip_pri} route-map {RM_PREPEND} out"]},
                    {"node": R[bak], "parents": [f"route-map {RM_PREPEND} permit 10"],
                     "lines": [f"set as-path prepend {prepend_str}"]},
                    {"node": R[bak], "parents": rb_af(R[bak]),
                     "lines": [f"neighbor {cust_ip_bak} route-map {RM_PREPEND} out"]},
                    {"node": R[pri], "exec": ["clear ip bgp * soft"]},
                    {"node": R[bak], "exec": ["clear ip bgp * soft"]}]
        if ft == "med_inverted":
            return [{"node": Rn, "parents": [f"route-map {RM_MED_P} permit 10"],
                     "lines": [f"set metric {med_pri}"]}, soft]
        if ft == "weight_override":
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"no neighbor {lo[R[bak]]} weight 40000"]}, soft]
        if ft == "password_mismatch":
            return [{"node": Rn, "parents": rb(Rn),
                     "lines": [f"no neighbor {peer_ip_of(f)} password"]}]
        if ft == "max_prefix_low":
            # PfxCt 超過で落ちた peer は Idle 固着→設定除去後に hard clear が要る
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"no neighbor {peer_ip_of(f)} maximum-prefix 2"]},
                    {"node": Rn, "exec": [f"clear ip bgp {peer_ip_of(f)}"]}]
        if ft == "default_originate_missing":
            agg_ip = if_ip(R["agg"], R[aside])[0]
            return [{"node": Rn, "parents": rb_af(Rn),
                     "lines": [f"neighbor {agg_ip} default-originate"]}, soft]
        if ft == "community_no_export":
            # ★set community は追記マージされる→必ず no set community で消してから再設定
            return [{"node": Rn, "parents": [f"route-map {RM_TAG} permit 10"],
                     "lines": ["no set community", f"set community {comm_tag}"]}, soft]
        if ft == "send_community_missing":
            lines = [f"neighbor {pip} send-community"
                     for (s, peer, pip) in sess_of(Rn) if s["kind"] == "ibgp"]
            return [{"node": Rn, "parents": rb_af(Rn), "lines": lines}, soft]
        # aggregate_missing / summary_only_missing
        return [{"node": Rn, "parents": rb_af(Rn),
                 "lines": [f"aggregate-address {AGG_NET} {AGG_MASK} summary-only"]}]

    fixes = [fx for f in faults for fx in fault_fix(f)]

    # ---- 採点 ---------------------------------------------------------------
    # 注意: show ip route bgp は同一マスクのサブネット群を
    #   「<classful>/24 is subnetted」ヘッダ＋ suffix なしのエントリ行で表示する。
    #   ∴ /24 到達判定は「B 行のエントリ」(B␣<net>␣ or B␣<net>/mask)にマッチさせる。
    checks = []

    def rx(net):
        return r"B\*? +" + net.replace(".", r"\.") + r"[ /]"

    groups = []
    for rl, ents in DEST.items():
        for (_, _, net) in ents:
            if rl == "agg":
                continue                     # /24到達は/22で担保
            groups.append((rl, net))
    for r in routers:
        for (orl, net) in groups:
            if role[r] == orl:
                continue
            checks.append({"name": f"{r}: {net}/24 を BGP で学習(到達)",
                           "node": r, "command": "show ip route bgp",
                           "raw": [{"regex": rx(net)}], "points": 0})
        if role[r] != "agg":
            checks.append({"name": f"{r}: 集約 172.31.0.0/22 を保持(設計)",
                           "node": r, "command": "show ip route bgp",
                           "raw": [{"regex": AGG_RX}], "points": 0})
    for r in routers:
        if role[r] in ("agg", aside):
            continue                          # aside は自表に/24を持つ(正常)
        checks.append({"name": f"{r}: /24 詳細が漏れていない(summary-only 設計)",
                       "node": r, "command": "show ip route bgp",
                       "raw": [{"regex": AGG_RX},
                               {"not_regex": r"172\.31\.[0-3]\.0/24"}],
                       "points": 0})
    # 集約元は構成要素 /24×4 を BGP テーブルに保持していること
    # (wrong_network_mask/missing_network が agg prefix に当たった時の採点盲点封鎖。
    #  /22 は残り3本でも形成されるが、欠けた /24 宛は集約元の Null0 で破棄される)
    checks.append({"name": f"{R[aside]}: 集約の構成要素 /24×4 を BGP テーブルに保持(設計)",
                   "node": R[aside], "command": "show ip bgp | include 172.31.",
                   "raw": [{"regex": r"172\.31\.%d\.0/24" % i} for i in range(4)],
                   "points": 0})
    # ---- ポリシー適合(Phase2・ベースラインでも常時採点=設計書の一部) --------
    pol_checks = []
    eg_label = {"lp_pref": f"LP{lp_pri}",
                "lp_depref": f"backup LP{lp_low} 降格",
                "prepend_in": f"backup inbound prepend×{pin_n}"}[egress]
    for (_, _, net) in DEST["cust"]:
        pol_checks.append({
            "name": f"{R['hub']}: {net}/24 の出口が primary({R[pri]}) 経由(設計 {eg_label})",
            "node": R["hub"], "command": "show ip route bgp",
            "parser": "show ip route",
            "find": "vrf.*.address_family.*.routes.*",
            "match": {"route": f"{net}/24", "source_protocol": "bgp",
                      "next_hop.next_hop_list.*.next_hop": lo[R[pri]]},
            "points": 8})
    pol_checks.append({
        "name": f"{R['cust']}: 192.0.2.0/24 の戻りが primary({R[pri]}) 経由(設計)",
        "node": R["cust"], "command": "show ip route bgp",
        "parser": "show ip route",
        "find": "vrf.*.address_family.*.routes.*",
        "match": {"route": "192.0.2.0/24", "source_protocol": "bgp",
                  "next_hop.next_hop_list.*.next_hop": if_ip(R[pri], R["cust"])[0]},
        "points": 8})
    # Tier1 設計チェック: 運用タグ / スタブASへのデフォルト
    pol_checks.append({
        "name": f"{R['hub']}: {MHOP_NET}/24 に運用タグ {comm_tag} が付いている(設計)",
        "node": R["hub"], "command": f"show ip bgp {MHOP_NET}",
        "raw": [{"regex": comm_tag}], "points": 6})
    pol_checks.append({
        "name": f"{R['agg']}: デフォルトルートを BGP で受信({R[aside]} が default-originate)",
        "node": R["agg"], "command": "show ip route bgp",
        "raw": [{"regex": r"B\*? +0\.0\.0\.0"}], "points": 6})
    pol_total = sum(c["points"] for c in pol_checks)
    n = len(checks); base = (100 - pol_total) // n
    rem = (100 - pol_total) - base * n
    for i, c in enumerate(checks):
        c["points"] = base + (1 if i < rem else 0)
    checks += pol_checks

    # ---- 出力 ---------------------------------------------------------------
    diff = min(5, max((f["difficulty"] for f in faults), default=3)
               + (1 if len(faults) > 1 else 0))
    prob_id = f"GEN-BGPCX-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id,
               "title": f"BGP 複合TS ibgp={a.ibgp} (seed={a.seed})",
               "exam": "ENARSI", "topics": ["bgp", "ospf", "mp-bgp",
                                            "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": routers, "points": 100, "access": "ssh",
               "lab": {"links": [{"a": lk["a"], "a_if": lk["a_if"],
                                  "b": lk["b"], "b_if": lk["b_if"]}
                                 for lk in links],
                       # CMLキャンバス座標(役割ベースの正準配置。ext は接続境界の外側)
                       "positions": {R[rl]: list(xy) for rl, xy in {
                           "cust": (0, -460), "bw": (-280, -260), "be": (280, -260),
                           "mhop": (-560 if mside == "bw" else 560, -260),
                           "agg": (-560 if aside == "bw" else 560, -260),
                           "hub": (0, -120), "leaf": (0, 60)}.items()}}}
    if a.monitoring:
        problem["topics"] = problem["topics"] + ["monitoring", "zabbix"]
        problem["target_nodes"] = routers + ["ZBX01"]
        problem["node_image_families"] = {"ZBX01": "ubuntu"}
        problem["node_ram"] = {"ZBX01": 3072}
        problem["lab"]["links"].append(
            {"a": "ZBX01", "a_if": 1, "b": zbx_leaf, "b_if": zbx_slot})
        problem["lab"]["positions"]["ZBX01"] = [0, 240]
        problem["monitoring"] = {
            "server": "ZBX01", "web_port": zgen.ZBX_WEB_PORT, "group": "CCNP-LAB",
            "hosts": [{"host": r, "ip": mon_ip[r],
                       "snmpv3": {"user": zgen.V3_USER,
                                  "auth_protocol": "SHA",
                                  "auth_pass": zgen.V3_AUTH_PASS,
                                  "priv_protocol": "AES",
                                  "priv_pass": zgen.V3_PRIV_PASS},
                       "templates": ["Cisco IOS by SNMP"]} for r in routers]}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for Rn in routers:
        with open(f"{pdir}/initial/{Rn}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render(Rn)) + "\n")
    if a.monitoring:
        with open(f"{pdir}/initial/ZBX01.cfg.j2", "w", encoding="utf-8") as f:
            f.write("# server ノードは baseline_server.cfg.j2 が全て描画"
                    "（このスタブは連結対策の空ファイル）\n")
        with open(f"{pdir}/initial/ZBX01.sh.j2", "w", encoding="utf-8") as f:
            f.write(zgen.zbx_init_sh({"lo": mon_ip}))
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_bgp_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump({"problem": prob_id, "total_points": 100,
                        "defaults": {"genie_os": "iosxe"}, "checks": checks},
                       f, sort_keys=False, allow_unicode=True)
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(faults), "faults": faults,
                   "roles": {role[r]: r for r in routers},
                   "ibgp": a.ibgp,
                   "variant": {"primary": pri, "mhop_side": mside,
                               "agg_side": aside, "egress": egress,
                               "lp": lp_pri, "lp_low": lp_low, "pin_n": pin_n,
                               "tag": comm_tag, "med": [med_pri, med_bak],
                               "prepend_n": prepend_n,
                               "return_policy": a.return_policy}},
                  f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)

    ledger = "\n".join(
        f"| {r} | {role[r]} | AS{as_of[r]} | `{lo[r]}` | 10.1.10.{11 + i} |"
        for i, r in enumerate(routers))
    ibgp_ja = ("ルートリフレクタ（RR=中心ルータ・他はクライアント）" if a.ibgp == "rr"
               else "iBGP フルメッシュ")
    ret_ja = (f"backup({bak}) 側が outbound で **AS-path prepend ×{prepend_n}**"
              if a.return_policy == "prepend"
              else f"outbound **MED（{pri}={med_pri} / {bak}={med_bak}）** で {pri} を優先")
    side_ja = {"bw": "西側境界", "be": "東側境界"}
    eg_ja = {"lp_pref":
             f"コア→AS65100 は {pri} が inbound で **LP{lp_pri}** を適用して primary。",
             "lp_depref":
             f"コア→AS65100 は backup({bak}) が inbound で **LP{lp_low}（<100）** を適用して"
             f"降格し、{pri} を primary とする。",
             "prepend_in":
             f"コア→AS65100 は backup({bak}) が inbound で **AS-path prepend ×{pin_n}** を"
             f"適用し、{pri} を primary とする。"}[egress]
    mon_md = ""
    if a.monitoring:
        mon_rows = "\n".join(f"| {r} | `{mon_ip[r]}` |" for r in routers)
        mon_md = f"""
## 監視環境（切り分けの入口）
- NOC の Zabbix が全ルータを SNMPv3 でポーリングしている
  （ZBX01 は {zbx_leaf}(leaf) 接続・インバンド {MON_NET}.2）。
  **どのホストが赤いか＝障害範囲の第一ヒント**（コア赤とサイト赤で層が違う）。
- Zabbix Web UI: `http://<ZBX01のMGMT IP>:{zgen.ZBX_WEB_PORT}/`（`Admin` / `zabbix`）
- 監視対象（コア=Loopback0 / 外部AS=サイト代表IP）:

| ホスト | 監視対象IP |
|--------|-----------|
{mon_rows}

- ZBX01（監視サーバ）の設定は正しい。触るのはルータのみ。復旧後の緑化は〜1分。
"""
    task = f"""# 問題 {prob_id} : BGP 複合トラブルシュート（難易度{diff}）

## 状況
4AS 構成の BGP 網で障害・設計逸脱が発生。**下記の設計書どおり**に復旧してください。

## トラブルチケット（代表症状・1件）
> {rep_txt} 原因は1か所とは限りません。
{mon_md}
## 設計書（＝復旧目標。この状態が「正」）
- **AS{CORE_AS}（コア4台）**: OSPF area0 がアンダーレイ（Lo0＋内部リンク）。
  iBGP は **{ibgp_ja}**・**全セッション Loopback0 ピア（update-source）**。
- **AS65100** は 2 台の境界ルータにデュアルホーム。**primary＝{pri}（{side_ja[pri]}）**:
  {eg_ja}
  AS65100→コア（戻り）も {pri} から入る設計: {ret_ja}。
- **AS65200** は **{mside}（{side_ja[mside]}）** と **Loopback 間 eBGP（multihop）**。
  相互 Loopback へは static。
  **AS65200 経路にはコア入口({mside})で運用タグ community `{comm_tag}` を付与**し、
  コアの iBGP は **send-community** でタグを伝搬する（コアで確認できること）。
- **AS65300 の 172.31.0.0-3.0/24 ×4 は {aside}（{side_ja[aside]}）で `172.31.0.0/22` に
  summary-only 集約**し、他の全ルータには **/22 のみ**が見えること（/24 の漏れは設計違反。
  集約元は構成要素 /24×4 を BGP テーブルに保持していること）。
  **スタブの AS65300 へは {aside} がデフォルトルートも配布（default-originate）**。
- 境界ルータは iBGP へ **next-hop-self**。
- 全機 **MP-BGP 書式**（`no bgp default ipv4-unicast`＋`address-family ipv4 unicast` で
  **activate 必須**）。

## ルータ台帳（mgmt は割当順）
| ルータ | 役割 | AS | Loopback0 | mgmt(SSH) |
|--------|------|----|-----------|-----------|
{ledger}

役割: hub=コア中心 / bw・be=境界(西・東) / leaf=コア内部 / cust=AS65100 /
mhop=AS65200(multihop) / agg=AS65300(集約元)

宛先: cust=`172.16.0-2.0/24` / mhop=`198.51.100.0/24` / agg=`172.31.0.0/22`(集約) /
leaf=`192.0.2.0/24`

## 到達目標 / 切り分け
- 全ルータが上記宛先を `show ip route bgp` で学習し相互到達。集約は /22 のみ。
- 故障の種類・場所・件数は非公開。**BGP の症状でも根本原因が下層（OSPF/静的経路/ACL/
  トランスポート）のことがある**。
- 切り分け: `show ip bgp summary` / `show ip bgp` / `show ip bgp neighbors <ip>` /
  `show ip route bgp` / `show ip ospf neighbor` / `show ip route <prefix>`。
- 勘所: **Established なのに PfxRcd 0** は何を意味するか。**BGP テーブルに有るのに
  RIB に無い**経路は何が原因か。Idle/Active の違い。RR の反射規則
  （client→全員 / 非client→client のみ）。**ベストパス選択順（weight > LP >
  AS-path > MED…）** — 設計どおりの経路にならない時は上位の属性から疑う。
  **ポリシー（route-map/フィルタ/weight/コミュニティ）変更後は `clear ip bgp * soft`**。
  セッションが **Idle のまま復帰しない**時は理由（`show ip bgp neighbors` / log の
  %BGP-・%TCP- 行）を見る — 設定を直しても **clear が要る**落ち方がある。
  コミュニティには **well-known（no-export 等）** があり、付いた経路の広告範囲が変わる。

## アクセス・採点
SSH `SUZUKI / CCNP`。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : ibgp={a.ibgp} rp={a.return_policy} "
          f"variant=(pri={pri} mhop={mside} agg={aside} egress={egress} lp={lp_pri} "
          f"lp_low={lp_low} pin={pin_n} tag={comm_tag} "
          f"med={med_pri}/{med_bak} prepend={prepend_n}) "
          f"faults={[(f['type'], f['node']) for f in faults]} "
          f"roles={{{', '.join(f'{k}:{R[k]}' for k in ROLES)}}}")


if __name__ == "__main__":
    main()
