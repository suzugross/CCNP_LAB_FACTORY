#!/usr/bin/env python3
"""gen_chain_ts.py — 12台・連鎖故障トラブルシュート生成器（方向性(2)）。

設計書: problems/_drafts/GEN-CHAINTS.design.md
核: 連鎖テンプレートを手書きせず、1本のターゲットフロー(West端末⇄East網)に対し
依存レイヤ L1(IGP隣接)→L2(BGP制御)→L3(経路/ポリシー)→L4(戻り) から1故障ずつ
経路上に配置する。下位レイヤの故障が上位の症状を隠すため連鎖が構造から生まれる。

トポロジ(12台・全ルータ次数<=3・IOL):
  West OSPF area1: RT10(端末LAN 172.20.0-1.0/24) - RT11 - [RT01=ABR]
  コア AS65001 OSPF area0 + iBGP: RR=RT03/RT04, client=RT01/02/05/06/07/09,
    非client観測点=RT12(両RR直結)。RT01がWest経路をOSPF→BGP再配送(community :100)
  East EIGRP AS65100: 境界ペア RT07/RT09(コア側=OSPF+iBGP / East側=EIGRP)が
    EIGRP⇄BGP 2点相互再配送(B2E: tag 65001 / E2B: deny tag 65001 + community :200)。
    RT08(East LAN 172.21.0-1.0/24)
  配線: 10-11,11-01 / 01-03,01-04,03-05,04-06,05-02,06-02,03-12,04-12 /
        02-07,06-09 / 07-08,09-08,07-09

CLI:
  gen_chain_ts.py --repo . --seed N [--chain-depth {0,2,3,4}]
    depth0=ベースライン(故障なし・トポロジ検証用) / 既定3(L1+L2+L3) / 4=+L4 / 2=L2+L3
出力: problems/GEN-CHAIN-<seed>/ (problem.yml, initial/*.cfg.j2, task.md,
      grading.yml, solution/{fault.json,fix.json,solution.md})

採点(100点): 端点間到達性30 + 大域不変条件30(loop_free/OSPFドメイン到達) +
             設計適合25(反射/冗長再配送/タグ/static残置禁止) + プロトコル健全15
教訓の適用: show ip route のエントリ行マッチ / route-map set community は追記
マージ(修正は no set community→再設定) / neighbor削除は配下設定を道連れ /
ポリシー変更後は clear ip bgp * soft を fix に併投。
"""
import argparse
import json
import os
import random

import yaml

AS_CORE = 65001
AS_EIGRP = 65100
COMM_W = f"{AS_CORE}:100"
COMM_E = f"{AS_CORE}:200"
TAG_LOOP = str(AS_CORE)          # B2E で付ける IGP タグ（E2B の deny 対象）
W_LAN = ["172.20.0", "172.20.1"]
E_LAN = ["172.21.0", "172.21.1"]

NODES = [f"RT{n:02d}" for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)]
RRS = ["RT03", "RT04"]
CLIENTS = ["RT01", "RT02", "RT05", "RT06", "RT07", "RT09"]
NONCLIENT = "RT12"
BGP_NODES = RRS + CLIENTS + [NONCLIENT]
E_BOUNDARY = ["RT07", "RT09"]
EIGRP_NODES = ["RT07", "RT08", "RT09"]

# CML表示座標（ドメイン/役割ベースの正準配置。円形フォールバックを使わない）:
# West左列 → RT01(ABR) → RRを上下段・RT12を両RR中間の観測位置 → client収束(RT02)
# → East境界ペア(RT07/09) → RT08(Server LAN)右端。x が West→East の流れに一致。
POSITIONS = {
    "RT10": [-1000, 0], "RT11": [-800, 0], "RT01": [-600, 0],
    "RT03": [-350, -150], "RT04": [-350, 150], "RT12": [-350, 0],
    "RT05": [-100, -150], "RT06": [-100, 150],
    "RT02": [100, 0],
    "RT07": [350, -110], "RT09": [350, 150],
    "RT08": [600, 20],
}

# (a, b, kind)  kind: a1=West OSPF area1 / a0=コア area0 / e=East EIGRP
LINKS = [
    ("RT10", "RT11", "a1"), ("RT11", "RT01", "a1"),
    ("RT01", "RT03", "a0"), ("RT01", "RT04", "a0"),
    ("RT03", "RT05", "a0"), ("RT04", "RT06", "a0"),
    ("RT05", "RT02", "a0"), ("RT06", "RT02", "a0"),
    ("RT03", "RT12", "a0"), ("RT04", "RT12", "a0"),
    ("RT02", "RT07", "a0"), ("RT06", "RT09", "a0"),
    ("RT07", "RT08", "e"), ("RT09", "RT08", "e"), ("RT07", "RT09", "e"),
]


# ----------------------------------------------------------------------------
# モデル構築
# ----------------------------------------------------------------------------
def build_model(seed, ibgp="rr", igp="oe"):
    rnd = random.Random(seed)
    m = {"seed": seed, "ibgp": ibgp, "igp": igp, "lo": {}, "links": [],
         "slot": {}, "faults": []}

    used = set()
    for n in NODES:
        while True:
            x = rnd.randint(1, 99)
            if x != 10 and x not in used:
                used.add(x)
                m["lo"][n] = f"{x}.{x}.{x}.{x}"
                break

    segs = set()
    slot_count = {n: 0 for n in NODES}
    for a, b, kind in LINKS:
        while True:
            if kind == "e":
                net = f"172.30.{rnd.randint(0, 254)}.{rnd.choice([0, 4, 8, 12])}"
                key = net
            else:
                x, y = rnd.randint(0, 254), rnd.randint(0, 254)
                if (x, y) == (1, 10):
                    continue
                net = f"10.{x}.{y}.0"
                key = (x, y)
            if key in segs:
                continue
            segs.add(key)
            break
        base = net.rsplit(".", 1)
        a_ip = f"{base[0]}.{int(base[1]) + 1}"
        b_ip = f"{base[0]}.{int(base[1]) + 2}"
        m["links"].append({"a": a, "b": b, "kind": kind, "net": net,
                           "a_ip": a_ip, "b_ip": b_ip,
                           "a_if": slot_count[a], "b_if": slot_count[b]})
        slot_count[a] += 1
        slot_count[b] += 1
    assert all(v <= 3 for v in slot_count.values())
    return m


def links_of(m, n):
    out = []
    for lk in m["links"]:
        if lk["a"] == n:
            out.append((lk["b_if"] and lk or lk, lk["a_if"], lk["a_ip"], lk))
        elif lk["b"] == n:
            out.append((lk, lk["b_if"], lk["b_ip"], lk))
    return [(slot, ip, lk) for (_x, slot, ip, lk) in out]


def peer_ip(lk, n):
    return lk["b_ip"] if lk["a"] == n else lk["a_ip"]


# ----------------------------------------------------------------------------
# 故障カタログ（レイヤ別）。各項目: inject(m)=モデルに旗を立てる / fix=fixes配列
# render 側が m["faults"] の旗を見て設定を欠落/改変する。
# ----------------------------------------------------------------------------
def rr_phys_ip(m, rr):
    """RT01-RR 直結リンクの RR 側 IP（wrong_neighbor_ip 故障用・rrモード）。"""
    for lk in m["links"]:
        if {lk["a"], lk["b"]} == {"RT01", rr}:
            return peer_ip(lk, "RT01")
    raise KeyError(rr)


def any_phys_ip(m, node):
    """node の(Loでない)物理IPを1つ返す（fullmesh の wrong_neighbor_ip 用）。"""
    for lk in m["links"]:
        if lk["a"] == node:
            return lk["a_ip"]
        if lk["b"] == node:
            return lk["b_ip"]
    raise KeyError(node)


def crit_peers(m):
    """West↔East 伝搬の急所となる RT01 のピア集合。
    rr: 両RR（反射の入口） / fullmesh: 両East境界（反射が無いため直結が生命線）"""
    return RRS if m["ibgp"] == "rr" else E_BOUNDARY


def west_links(m, n):
    """n の West ドメイン側リンク(kind=a1)。"""
    return [(s, ip, lk) for s, ip, lk in links_of(m, n) if lk["kind"] == "a1"]


def healthy_west_eigrp_block(m, n):
    """swapモードの West ノード n の設計通り EIGRP ブロック（fix 用）。"""
    lines = [f"network {lk['net']} 0.0.0.3" for _s, _ip, lk in west_links(m, n)]
    lines.append(f"network {m['lo'][n]} 0.0.0.0")
    if n == "RT10":
        lines += [f"network {lan}.0 0.0.0.255" for lan in W_LAN]
    if n == "RT01":
        lines += [f"redistribute bgp {AS_CORE} route-map RM-B2E-W",
                  "default-metric 100000 100 255 1 1500"]
    lines.append("no auto-summary")
    return lines


def west_access_link(m):
    return next(lk for lk in m["links"] if {lk["a"], lk["b"]} == {"RT11", "RT01"})


def _fx(node, lines, parents=None):
    d = {"node": node, "lines": lines}
    if parents:
        d["parents"] = parents
    return d


def catalog(m):
    lk = west_access_link(m)
    rt01_if = f"links[{lk['a_if'] if lk['a'] == 'RT01' else lk['b_if']}]"
    C = {}

    if m["igp"] == "eo":
        # swap: West は EIGRP → L1 は EIGRP 隣接系(area/mtu は EIGRP に無効)
        wa = west_access_link(m)
        rt01_slot = wa["a_if"] if wa["a"] == "RT01" else wa["b_if"]
        C["L1"] = [
            ("l1_eigrp_as_mismatch_west",
             "RT11 の EIGRP が AS 65101 で設定(正: 65100。West全滅)",
             {"kind": "w_eigrp_as", "victim": "RT11"},
             [_fx("RT11", ["no router eigrp 65101"]),
              _fx("RT11", healthy_west_eigrp_block(m, "RT11"),
                  [f"router eigrp {AS_EIGRP}"])]),
            ("l1_eigrp_auth_west",
             "RT11 側 West アクセスIF のみ EIGRP MD5 認証が有効(RT01側は無し)",
             {"kind": "w_eigrp_auth"},
             [_fx("RT11", [f"no ip authentication mode eigrp {AS_EIGRP} md5",
                           f"no ip authentication key-chain eigrp {AS_EIGRP} KC-W"],
                  None),   # parents は emit で IF 名補完
              _fx("RT11", ["no key chain KC-W"])]),
            ("l1_eigrp_passive_west",
             "RT01 の West アクセスIF が EIGRP passive (隣接不成立)",
             {"kind": "w_eigrp_passive"},
             [_fx("RT01", [f"no passive-interface Ethernet{rt01_slot // 4}/{rt01_slot % 4}"],
                  [f"router eigrp {AS_EIGRP}"])]),
        ]
    else:
        C["L1"] = [
        ("l1_area_mismatch",
         "RT01 の West アクセスIF が area 2 で設定されている(正: area 1)",
         {"kind": "area", "net": lk["net"]},
         [_fx("RT01", [f"no network {lk['net']} 0.0.0.3 area 2",
                       f"network {lk['net']} 0.0.0.3 area 1"], ["router ospf 1"])]),
        ("l1_ospf_auth",
         "RT11 側 West アクセスIF のみ OSPF MD5 認証が有効(RT01側は無し)",
         {"kind": "auth"},
         [_fx("RT11", ["no ip ospf authentication message-digest",
                       "no ip ospf message-digest-key 1 md5 CHAIN"],
              None)]),  # parents は render 時に IF 名確定後に補完
        ("l1_mtu_mismatch",
         "RT01 側 West アクセスIF に ip mtu 1400 (EXSTART 固着)",
         {"kind": "mtu"},
         [_fx("RT01", ["no ip mtu 1400"], None)]),
    ]

    CP = crit_peers(m)      # rr: RRS / fullmesh: E_BOUNDARY（伝搬の急所ピア）
    C["L2"] = []
    if m["ibgp"] == "rr":
        # ★client旗は1つ外しても壊れない(client経路は全員へ/非client経路もclientへ
        #   反射される)。壊れるのは「非client→非client」だけ。West発(RT01)と
        #   East境界(RT07/09)を同時に非client化して初めて West→East が途絶する
        #   (実機で1victim版が無効なことを確認済→3victim版に設計変更)。
        C["L2"].append(("l2_rr_client_break",
         "両RRで RT01/RT07/RT09 の route-reflector-client が外されている"
         "(非client同士は反射されず West↔East の経路交換が途絶)",
         {"kind": "rrclient", "victims": ["RT01", "RT07", "RT09"]},
         [_fx(rr, [f"neighbor {m['lo'][v]} route-reflector-client"
                   for v in ("RT01", "RT07", "RT09")],
              [f"router bgp {AS_CORE}", "address-family ipv4"]) for rr in RRS] +
         [{"node": rr, "exec": ["clear ip bgp * soft"]} for rr in RRS]))
    else:
        # fullmesh: 反射が無いため RT01↔両East境界 の直結セッションが West↔East の生命線
        C["L2"].append(("l2_mesh_session_missing",
         "RT01 に両East境界(RT07/RT09)への iBGP ピア定義が無い"
         "(fullmesh に反射は無く直結が生命線→West↔East の経路交換が途絶)",
         {"kind": "meshsess", "victim": "RT01"},
         [_fx("RT01",
              sum([[f"neighbor {m['lo'][b]} remote-as {AS_CORE}",
                    f"neighbor {m['lo'][b]} update-source Loopback0"]
                   for b in E_BOUNDARY], []),
              [f"router bgp {AS_CORE}"]),
          _fx("RT01",
              sum([[f"neighbor {m['lo'][b]} activate",
                    f"neighbor {m['lo'][b]} send-community"] for b in E_BOUNDARY], []),
              [f"router bgp {AS_CORE}", "address-family ipv4"]),
          {"node": "RT01", "exec": ["clear ip bgp * soft"]}]))

    def wrong_ip_of(peer):
        return rr_phys_ip(m, peer) if m["ibgp"] == "rr" else any_phys_ip(m, peer)
    C["L2"] += [
        # ★update-source片側欠落は故障にならない(RR側からのTCP接続で成立する。
        #   実機で確認済=100点のまま) → 双方向で不一致になる neighbor IP 誤りに差替え
        ("l2_wrong_neighbor_ip",
         f"RT01 の{'RR' if m['ibgp'] == 'rr' else 'East境界'}ピアが Loopback でなく"
         "物理リンクIPを指している(双方向とも neighbor 不一致でセッション不成立)",
         {"kind": "wrongneigh", "victim": "RT01", "excl": "rt01sess"},
         [_fx("RT01",
              [f"no neighbor {wrong_ip_of(cp)}" for cp in CP] +
              sum([[f"neighbor {m['lo'][cp]} remote-as {AS_CORE}",
                    f"neighbor {m['lo'][cp]} update-source Loopback0"]
                   for cp in CP], []),
              [f"router bgp {AS_CORE}"]),
          _fx("RT01",
              sum([[f"neighbor {m['lo'][cp]} activate",
                    f"neighbor {m['lo'][cp]} send-community"] for cp in CP], []),
              [f"router bgp {AS_CORE}", "address-family ipv4"]),
          {"node": "RT01", "exec": ["clear ip bgp * soft"]}]),
        # bgp_complex_ts で実機検証済みのパターンを移植（MD5不一致はTCP層で遮断
        #   =双方向で確実に落ちる。iBGP Loピアでも有効）
        ("l2_password_mismatch",
         f"RT01 の急所ピア({'/'.join(CP)})にだけ MD5 パスワード(相手側は無し→セッション不成立)",
         {"kind": "bgppass", "victim": "RT01", "excl": "rt01sess"},
         [_fx("RT01", [f"no neighbor {m['lo'][cp]} password BADAUTH" for cp in CP],
              [f"router bgp {AS_CORE}"])]),
        # ★fixは設定除去だけでは Idle(PfxCt) が解けない→hard clear 併投が必須
        #   (bgp_complex_ts Tier1 の実機教訓)
        ("l2_max_prefix_low",
         f"RT01 の急所ピア({'/'.join(CP)})に maximum-prefix 2 (経路超過で Idle(PfxCt) 固着)",
         {"kind": "maxpfx", "victim": "RT01", "excl": "rt01sess"},
         [_fx("RT01", [f"no neighbor {m['lo'][cp]} maximum-prefix 2" for cp in CP],
              [f"router bgp {AS_CORE}", "address-family ipv4"]),
          {"node": "RT01", "exec": [f"clear ip bgp {m['lo'][cp]}" for cp in CP]}]),
        # ★fix は activate だけでなく send-community も復元(day0 render は activate
        #   skip 時に send-community 行も落とすため。rr では全経路がRR経由なので
        #   これが欠けると West community が全域で消える。3002 実機で発見)
        ("l2_activate_missing",
         f"RT01 の急所ピア({'/'.join(CP)})が address-family ipv4 で activate されていない"
         "(セッションUPなのに経路ゼロ)",
         {"kind": "activate", "victim": "RT01", "excl": "rt01sess"},
         [_fx("RT01", sum([[f"neighbor {m['lo'][cp]} activate",
                            f"neighbor {m['lo'][cp]} send-community"] for cp in CP], []),
              [f"router bgp {AS_CORE}", "address-family ipv4"])]),
    ]

    C["L3"] = [
        # ★当初の tag_deny_leak(deny tag欠落→ループ)は E2B のホワイトリストが
        #   還流を止めるため実効なし(実機確認済)。IOS 既定動作を突く故障に差替え。
        ("l3_redist_internal_missing",
         "両境界の BGP に bgp redistribute-internal が無い"
         "(IOS既定=iBGP経路はIGPへ再配送されない→East に West の戻り経路が皆無)",
         {"kind": "b2einternal"},
         [_fx(b, ["bgp redistribute-internal"],
              [f"router bgp {AS_CORE}", "address-family ipv4"]) for b in E_BOUNDARY] +
         [{"node": b, "exec": ["clear ip bgp * soft"]} for b in E_BOUNDARY]),
        ("l3_e2b_filter_gone",
         "両境界の PL-EAST から 172.21.1.0/24 が漏れている(East LAN2 が BGP に乗らない)",
         {"kind": "e2bfilter"},
         [_fx(b, ["ip prefix-list PL-EAST seq 10 permit 172.21.1.0/24"])
          for b in E_BOUNDARY] +
         [{"node": b, "exec": ["clear ip bgp * soft"]} for b in E_BOUNDARY]),
    ]
    if m["igp"] == "eo":
        # swap: East は OSPF2 → OSPF 再配送の古典罠2種
        C["L3"] += [
            ("l3_subnets_missing",
             "両境界の BGP→OSPF2 再配送に subnets が無い"
             "(クラスフル境界以外が全て落ちる→East に West の戻り経路なし)",
             {"kind": "b2osubnets"},
             [_fx(b, [f"redistribute bgp {AS_CORE} subnets route-map RM-B2E"],
                  ["router ospf 2"]) for b in E_BOUNDARY]),
            ("l3_nhset_missing",
             "両境界の E2B route-map に set ip next-hop(自Lo0) が無い"
             "(NH=172.30.x はコアで解決不能→RRで no best・East経路が配られない)",
             {"kind": "nhset"},
             [_fx(b, [f"set ip next-hop {m['lo'][b]}"],
                  ["route-map RM-E2B permit 10"]) for b in E_BOUNDARY] +
             [{"node": b, "exec": ["clear ip bgp * soft"]} for b in E_BOUNDARY]),
        ]
    else:
        C["L3"] += [
            ("l3_b2e_metric_missing",
             "両境界の EIGRP に default-metric が無い(BGP→EIGRP 再配送が経路を注入しない=戻り不在)",
             {"kind": "b2emetric"},
             [_fx(b, ["default-metric 100000 100 255 1 1500"],
                  [f"router eigrp {AS_EIGRP}"]) for b in E_BOUNDARY]),
            # 開発中に実機で発見した現象の武器化: 境界のEIGRP側リンクがOSPFに無いと
            #   E2B経路のNHが解決できず RRで "inaccessible→no best"=Eastが丸ごと消える
            ("l3_nh_passive_missing",
             "両境界の EIGRP側リンク(172.30.x)が OSPF に広告されていない"
             "(E2B経路の BGP next-hop が解決不能→RRで no best・East経路が配られない)",
             {"kind": "nhpassive"},
             [_fx(b, [f"passive-interface Ethernet{s // 4}/{s % 4}" for s, _ip, lk in
                      links_of(m, b) if lk["kind"] == "e"] +
                     [f"network {lk['net']} 0.0.0.3 area 0" for _s, _ip, lk in
                      links_of(m, b) if lk["kind"] == "e"],
                  ["router ospf 1"]) for b in E_BOUNDARY]),
        ]

    # L4 のモード追随: sendcomm は rr=両RRピア / fullmesh=全ピア(全ピアに無いと
    # RT12 が直結で community を受け取れてしまい故障が実効しない)。
    # retdlist の親は oe=EIGRP / eo=OSPF2(OSPF の distribute-list in は RIB 抑止として実効)
    def sc_targets(b):
        return RRS if m["ibgp"] == "rr" else [x for x in BGP_NODES if x != b]
    ret_proto, ret_parent = (("EIGRP", f"router eigrp {AS_EIGRP}") if m["igp"] == "oe"
                             else ("OSPF2", "router ospf 2"))
    C["L4"] = [
        ("l4_static_shadow",
         "RT08 に誤った static (172.20.0.0/25 → Null0) が残置され West LAN1 の戻りを黒穴化",
         {"kind": "staticshadow"},
         [_fx("RT08", ["no ip route 172.20.0.0 255.255.255.128 Null0"])]),
        ("l4_send_community_missing",
         "両境界の iBGP ピアに send-community が無い(到達性は無傷だが運用タグが消える設計逸脱)",
         {"kind": "sendcomm"},
         [_fx(b, [f"neighbor {m['lo'][r]} send-community" for r in sc_targets(b)],
              [f"router bgp {AS_CORE}", "address-family ipv4"]) for b in E_BOUNDARY] +
         [{"node": b, "exec": ["clear ip bgp * soft"]} for b in E_BOUNDARY]),
        ("l4_return_dlist",
         f"RT08 の {ret_proto} で West LAN1 を distribute-list が遮断(行きOK・戻りNG)",
         {"kind": "retdlist"},
         [_fx("RT08", ["no distribute-list prefix BLOCK-W in"],
              [ret_parent])]),
    ]
    # ※l4_b2e_oneside_missing(片側B2E欠落→RIB乗っ取り)は実機検証の結果**不採用**:
    #   境界間直結IGPリンクがある本トポロジでは West 経路の還流により健全構成でも
    #   常に片側境界が D EX/O E2 に固着(bistableラチェット)し、「両境界BGP保持」が
    #   採点不変条件として成立しない(2026-07-08 LOOPPOC+GEN-CHAIN-2000/3002 実機)。
    #   詳細は設計書「真の再配送ループ検証」節。
    return C, rt01_if


# おとり: 定義だけで未適用/無害だが、diff読みで「怪しく見える」設定群。
# ★絶対条件: 経路・隣接・採点に一切影響しないこと（適用系コマンド禁止）
DECOYS = [
    ("dc_legacy_acl", "RT05",
     ["access-list 199 remark ### LEGACY BLOCK ticket NOC-4711 (keep until 2025Q4) ###",
      "access-list 199 deny ip 172.20.0.0 0.0.1.255 any",
      "access-list 199 permit ip any any"]),
    ("dc_unused_rmap", "RT06",
     ["ip prefix-list OLD-BLOCK seq 5 permit 172.21.0.0/16 le 24",
      "route-map LEGACY-POLICY deny 10",
      " match ip address prefix-list OLD-BLOCK",
      "route-map LEGACY-POLICY permit 20"]),
    ("dc_quarantine_pl", "RT02",
     ["ip prefix-list QUARANTINE seq 5 deny 0.0.0.0/0 le 32"]),
    ("dc_scary_neigh_desc", "RT02",
     ["router bgp 65001",
      " neighbor {rr1} description !! FLAPPING? under investigation NOC-1123 !!"]),
    ("dc_snmp_note", "RT11",
     ["snmp-server location MAINTENANCE-WINDOW-PENDING (change CHG-2077)"]),
]


def healthy_eigrp_block(m, b):
    """境界 b の設計通り EIGRP ブロック（分岐故障 eigrp_as_mismatch の fix 用）。"""
    lines = []
    for _s, _ip, lk in links_of(m, b):
        if lk["kind"] == "e":
            lines.append(f"network {lk['net']} 0.0.0.3")
    lines += [f"redistribute bgp {AS_CORE} route-map RM-B2E",
              "default-metric 100000 100 255 1 1500", "no auto-summary"]
    return lines


def branch_catalog(m):
    """分岐連鎖: 冗長境界ペアの各片方を「別種の方法で」丸ごと殺す故障。
    片方を直すと到達性は全回復するが冗長性チェックは落ちたまま
    ＝「疎通OK≠復旧完了」を突く。"""
    def bgppass(b):
        return ("br_bgp_password",
                f"{b} の両RRピアにだけ MD5 パスワード(セッション確立不能={b}系統がBGPから消える)",
                {"kind": f"brpass_{b}", "victim": b},
                [_fx(b, [f"no neighbor {m['lo'][rr]} password BADAUTH" for rr in RRS],
                     [f"router bgp {AS_CORE}"])])
    def eigrp_as(b):
        return ("br_eigrp_as_mismatch",
                f"{b} の EIGRP が AS 65101 で設定(正: {AS_EIGRP}。隣接不成立={b}系統がEIGRPから消える)",
                {"kind": f"breigrp_{b}", "victim": b},
                [_fx(b, ["no router eigrp 65101"]),
                 _fx(b, healthy_eigrp_block(m, b), [f"router eigrp {AS_EIGRP}"])])
    def ospf2_area(b):
        # swap(eo)用: OSPF の process 番号は hello に乗らないため process 誤りでは
        # 隣接が切れない。area 不一致なら hello 段で拒否= b 系統が確実に全滅する
        e_nets = [lk["net"] for _s, _ip, lk in links_of(m, b) if lk["kind"] == "e"]
        return ("br_ospf2_area_mismatch",
                f"{b} の East リンクが OSPF2 で area 2 に設定(正: area 0。"
                f"hello の area 不一致で隣接不成立={b}系統がOSPF2から消える)",
                {"kind": f"brospf2_{b}", "victim": b},
                [_fx(b, sum([[f"no network {net} 0.0.0.3 area 2",
                              f"network {net} 0.0.0.3 area 0"] for net in e_nets], []),
                     ["router ospf 2"])])
    return {"bgppass": bgppass, "eigrp_as": eigrp_as, "ospf2_area": ospf2_area}


def inject(m, depth, rnd, decoys=0, width=1, branch=False):
    """レイヤごとに width 個の故障を seed 選択して旗を立てる。
    深さ: 2=L2,L3 / 3=+L1 / 4=+L4
    width: 同一レイヤの故障数(1|2)。排他グループ(flag.excl)は同時選択しない
    branch: True なら L3 枠を「分岐連鎖」(冗長境界ペアへ別種の故障を1つずつ)で置換。
            片方修復で到達性は全回復するが冗長性が欠けたまま＝復旧完了の定義を問う
    decoys: 無害なおとり設定を N 個散布（故障とは独立・修正不要）"""
    C, _ = catalog(m)
    layers = {2: ["L2", "L3"], 3: ["L1", "L2", "L3"],
              4: ["L1", "L2", "L3", "L4"]}.get(depth, [])
    for layer in layers:
        if branch and layer == "L3":
            assert m["ibgp"] == "rr", \
                "--branch-fault は rr モード限定(v1)。fullmesh では境界のbrpassが" \
                "他ピア経由で迂回され実効しないため(要・全ピア殺し版の設計)"
            bc = branch_catalog(m)
            kinds = ["bgppass",
                     "eigrp_as" if m["igp"] == "oe" else "ospf2_area"]
            rnd.shuffle(kinds)   # どちらの境界にどちらの殺し方を当てるかも seed 変動
            for b, k in zip(E_BOUNDARY, kinds):
                fid, desc, flag, fixes = bc[k](b)
                m["faults"].append({"layer": "L3b", "id": fid, "desc": desc,
                                    "flag": flag, "fixes": fixes})
            continue
        pool = list(C[layer])
        rnd.shuffle(pool)
        used_excl, taken = set(), 0
        for fid, desc, flag, fixes in pool:
            if taken >= width:
                break
            ex = flag.get("excl")
            if ex and ex in used_excl:
                continue
            if ex:
                used_excl.add(ex)
            m["faults"].append({"layer": layer, "id": fid, "desc": desc,
                                "flag": flag, "fixes": fixes})
            taken += 1
    m["decoys"] = rnd.sample(DECOYS, min(decoys, len(DECOYS))) if decoys else []


def flags(m):
    return {f["flag"]["kind"]: f["flag"] for f in m["faults"]}


# ----------------------------------------------------------------------------
# render: ノード設定
# ----------------------------------------------------------------------------
def render_node(m, n):
    F = flags(m)
    lo = m["lo"][n]
    L = []
    L.append(f"! GEN-CHAIN-{m['seed']} 初期 ({n}) — 連鎖故障TS(12台)。設計書は task.md")
    L.append("interface Loopback0")
    L.append(f" ip address {lo} 255.255.255.255")
    L.append("!")
    if n == "RT10":
        for i, lan in enumerate(W_LAN):
            L += [f"interface Loopback{10 + i}",
                  " description === West User LAN ==="]
            L.append(f" ip address {lan}.1 255.255.255.0")
            if m["igp"] == "oe":
                # OSPF は Loopback を /32 で広告する→ /24 のまま流す(PL-WEST 前提)
                L.append(" ip ospf network point-to-point")
            L.append("!")
    if n == "RT08":
        for i, lan in enumerate(E_LAN):
            L += [f"interface Loopback{10 + i}",
                  " description === East Server LAN ==="]
            L.append(f" ip address {lan}.1 255.255.255.0")
            if m["igp"] == "eo":
                # East が OSPF2 の場合も /32 罠を回避
                L.append(" ip ospf network point-to-point")
            L.append("!")

    # 物理IF
    for slot, ip, lk in sorted(links_of(m, n), key=lambda t: t[0]):
        other = lk["b"] if lk["a"] == n else lk["a"]
        L.append(f"interface {{{{ links[{slot}] }}}}")
        L.append(f" description === to {other} ===")
        L.append(f" ip address {ip} 255.255.255.252")
        if F.get("mtu") and n == "RT01" and other == "RT11":
            L.append(" ip mtu 1400")
        if F.get("auth") and n == "RT11" and other == "RT01":
            L.append(" ip ospf authentication message-digest")
            L.append(" ip ospf message-digest-key 1 md5 CHAIN")
        if F.get("w_eigrp_auth") and n == "RT11" and other == "RT01":
            L.append(f" ip authentication mode eigrp {AS_EIGRP} md5")
            L.append(f" ip authentication key-chain eigrp {AS_EIGRP} KC-W")
        L.append(" no shutdown")
        L.append("!")

    # OSPF（West/コア）
    # base: 境界(RT07/09)の EIGRP側リンクは OSPF area0 へ passive で広告する。
    # E2B 再配送経路の BGP next-hop(172.30.x) をコア全域で解決可能にするため
    # （無いと RR で "inaccessible → no best" となり反射されない。実機で確認済）。
    # swap: 172.30 リンクは OSPF2 でアクティブ＝ospf1 に入れられない(IFは1プロセス)
    # → NH解決は E2B route-map の set ip next-hop(自Lo0) で行う。
    ospf_nets, passive_slots = [], []
    for slot, ip, lk in links_of(m, n):
        if lk["kind"] == "e":
            if (m["igp"] == "oe" and n in E_BOUNDARY
                    and not F.get("nhpassive")):
                ospf_nets.append((lk["net"], "0"))
                passive_slots.append(slot)
            continue
        if lk["kind"] == "a1" and m["igp"] == "eo":
            continue   # swap: West リンクは EIGRP ドメイン
        area = "1" if lk["kind"] == "a1" else "0"
        if F.get("area") and n == "RT01" and lk["net"] == F["area"]["net"]:
            area = "2"
        ospf_nets.append((lk["net"], area))
    if n in ("RT10", "RT11"):
        lo_area = "1" if m["igp"] == "oe" else None   # swap: West Lo は EIGRP
    elif n == "RT08":
        lo_area = None
    else:
        lo_area = "0"
    if ospf_nets or lo_area:
        L.append("router ospf 1")
        L.append(f" router-id {lo}")
        # area1 は totally stubby: West は RT01 経由のデフォルトで East へ到達する
        # （BGP を知らない West ドメインへの経路供給を ABR のデフォルト注入で行う設計）
        if n == "RT01" and m["igp"] == "oe":
            L.append(" area 1 stub no-summary")
            # West LAN の IA 広告を止める: OSPF(AD110) が iBGP(AD200) に勝つと
            # 境界で RIB-failure → B2E 再配送不発になる(実機で確認済)。
            # これにより「West LAN の伝搬は BGP が唯一の経路」= BGP層が実効を持つ
            L.append(" area 1 range 172.20.0.0 255.255.254.0 not-advertise")
        if n in ("RT10", "RT11") and m["igp"] == "oe":
            L.append(" area 1 stub")
        if lo_area:
            L.append(f" network {lo} 0.0.0.0 area {lo_area}")
        if n == "RT10":
            for lan in W_LAN:
                L.append(f" network {lan}.0 0.0.0.255 area 1")
        for slot in passive_slots:
            L.append(f" passive-interface {{{{ links[{slot}] }}}}")
        for net, area in ospf_nets:
            L.append(f" network {net} 0.0.0.3 area {area}")
        L.append("!")

    # East ドメイン IGP（base: EIGRP / swap: OSPF プロセス2）
    if m["igp"] == "oe" and n in EIGRP_NODES:
        eigrp_as = "65101" if F.get(f"breigrp_{n}") else str(AS_EIGRP)
        L.append(f"router eigrp {eigrp_as}")
        for slot, ip, lk in links_of(m, n):
            if lk["kind"] == "e":
                L.append(f" network {lk['net']} 0.0.0.3")
        if n == "RT08":
            L.append(f" network {lo} 0.0.0.0")
            for lan in E_LAN:
                L.append(f" network {lan}.0 0.0.0.255")
            if F.get("retdlist"):
                L.append(" distribute-list prefix BLOCK-W in")
        if n in E_BOUNDARY:
            L.append(f" redistribute bgp {AS_CORE} route-map RM-B2E")
            if not F.get("b2emetric"):
                L.append(" default-metric 100000 100 255 1 1500")
        L.append(" no auto-summary")
        L.append("!")
    if m["igp"] == "eo" and n in EIGRP_NODES:
        L.append("router ospf 2")
        # 同一ルータ内の別OSPFプロセスは RID 重複不可 → ospf2 は Lo0 の第4オクテットを
        # 2.x.x.x 側に振った専用 RID を使う（設定値であり実在アドレス不要）
        L.append(f" router-id 2.{lo.split('.')[1]}.{lo.split('.')[2]}.{lo.split('.')[3]}")
        e_area = "2" if F.get(f"brospf2_{n}") else "0"
        for slot, ip, lk in links_of(m, n):
            if lk["kind"] == "e":
                L.append(f" network {lk['net']} 0.0.0.3 area {e_area}")
        if n == "RT08":
            L.append(f" network {lo} 0.0.0.0 area 0")
            for lan in E_LAN:
                L.append(f" network {lan}.0 0.0.0.255 area 0")
            if F.get("retdlist"):
                L.append(" distribute-list prefix BLOCK-W in")
        if n in E_BOUNDARY:
            sub = "" if F.get("b2osubnets") else " subnets"
            L.append(f" redistribute bgp {AS_CORE}{sub} route-map RM-B2E")
        L.append("!")
    # West ドメイン IGP（swap: EIGRP。RT10/RT11/RT01 の West 側）
    if m["igp"] == "eo" and n in ("RT10", "RT11", "RT01"):
        w_as = "65101" if (F.get("w_eigrp_as")
                           and n == F["w_eigrp_as"]["victim"]) else str(AS_EIGRP)
        L.append(f"router eigrp {w_as}")
        if F.get("w_eigrp_passive") and n == "RT01":
            for s, _ip, lk in west_links(m, n):
                L.append(f" passive-interface Ethernet{s // 4}/{s % 4}")
        for _s, _ip, lk in west_links(m, n):
            L.append(f" network {lk['net']} 0.0.0.3")
        if n != "RT01":
            L.append(f" network {lo} 0.0.0.0")
        if n == "RT10":
            for lan in W_LAN:
                L.append(f" network {lan}.0 0.0.0.255")
        if n == "RT01":
            L.append(f" redistribute bgp {AS_CORE} route-map RM-B2E-W")
            L.append(" default-metric 100000 100 255 1 1500")
        L.append(" no auto-summary")
        L.append("!")

    # 再配送ポリシー
    if n == "RT01":
        L.append("ip prefix-list PL-WEST seq 5 permit 172.20.0.0/23 ge 24 le 24")
        if m["igp"] == "eo":
            # swap: West Lo0 群は EIGRP のみ→BGP で運ぶ(baseはIAで見えるため不要)
            L.append(f"ip prefix-list PL-WEST seq 10 permit {m['lo']['RT10']}/32")
            L.append(f"ip prefix-list PL-WEST seq 15 permit {m['lo']['RT11']}/32")
            L += ["route-map RM-W2B deny 5",
                  f" match tag {TAG_LOOP}"]
        L += ["route-map RM-W2B permit 10",
              " match ip address prefix-list PL-WEST",
              f" set community {COMM_W}"]
        if m["igp"] == "eo":
            # NH解決の自己完結化(swap): W2B 経路の NH を自Lo0 に
            L.append(f" set ip next-hop {lo}")
            L += ["route-map RM-B2E-W permit 10",
                  f" set tag {TAG_LOOP}"]
        L.append("!")
    if n in E_BOUNDARY:
        L.append("ip prefix-list PL-EAST seq 5 permit 172.21.0.0/24")
        if not F.get("e2bfilter"):
            L.append("ip prefix-list PL-EAST seq 10 permit 172.21.1.0/24")
        L.append(f"ip prefix-list PL-EAST seq 15 permit {m['lo']['RT08']}/32")
        if not (F.get("tagleak") and n == F["tagleak"]["victim"]):
            L += ["route-map RM-E2B deny 5",
                  f" match tag {TAG_LOOP}"]
        L += ["route-map RM-E2B permit 10",
              " match ip address prefix-list PL-EAST",
              f" set community {COMM_E}"]
        if m["igp"] == "eo" and not F.get("nhset"):
            # NH解決の自己完結化(swap): E2B 経路の NH を自Lo0 に
            # (172.30 は OSPF2 アクティブ=ospf1 へ passive 広告できないため)
            L.append(f" set ip next-hop {lo}")
        L += ["route-map RM-B2E permit 10",
              f" set tag {TAG_LOOP}", "!"]
    if n == "RT11" and F.get("w_eigrp_auth"):
        L += ["key chain KC-W",
              " key 1",
              "  key-string CHAIN", "!"]
    if n == "RT08" and F.get("retdlist"):
        L += ["ip prefix-list BLOCK-W seq 5 deny 172.20.0.0/24",
              "ip prefix-list BLOCK-W seq 10 permit 0.0.0.0/0 le 32", "!"]
    if n == "RT08" and F.get("staticshadow"):
        L += ["ip route 172.20.0.0 255.255.255.128 Null0", "!"]

    # BGP（AF方式・conventions.md 規約）
    if n in BGP_NODES:
        if m["ibgp"] == "fullmesh":
            peers = [x for x in BGP_NODES if x != n]
            if F.get("meshsess") and n == F["meshsess"]["victim"]:
                peers = [x for x in peers if x not in E_BOUNDARY]
            if F.get("meshsess") and n in E_BOUNDARY:
                pass  # 境界側は正しく定義済み(片側定義欠落=RT01側だけの故障)
        elif n in RRS:
            peers = [p for p in CLIENTS] + [r for r in RRS if r != n] + [NONCLIENT]
        else:
            peers = list(RRS)
        L.append(f"router bgp {AS_CORE}")
        L.append(f" bgp router-id {lo}")
        L.append(" bgp log-neighbor-changes")
        L.append(" no bgp default ipv4-unicast")
        def peer_addr(p):
            if (F.get("wrongneigh") and n == F["wrongneigh"]["victim"]
                    and p in set(crit_peers(m))):
                # 故障: Lo でなく物理IP
                return rr_phys_ip(m, p) if m["ibgp"] == "rr" else any_phys_ip(m, p)
            return m["lo"][p]
        for p in peers:
            pa = peer_addr(p)
            L.append(f" neighbor {pa} remote-as {AS_CORE}")
            if pa == m["lo"][p]:
                L.append(f" neighbor {pa} update-source Loopback0")
            cp_set = set(crit_peers(m))
            if (F.get("bgppass") and n == F["bgppass"]["victim"] and p in cp_set):
                L.append(f" neighbor {pa} password BADAUTH")
            if F.get(f"brpass_{n}") and p in RRS:
                L.append(f" neighbor {pa} password BADAUTH")
        L.append(" address-family ipv4")
        for p in peers:
            skip_act = (F.get("activate") and n == F["activate"]["victim"]
                        and p in set(crit_peers(m)))
            if skip_act:
                continue
            pa = peer_addr(p)
            L.append(f"  neighbor {pa} activate")
            skip_sc = (F.get("sendcomm") and n in E_BOUNDARY
                       and (m["ibgp"] != "rr" or p in RRS))
            if not skip_sc:
                L.append(f"  neighbor {pa} send-community")
            if (F.get("maxpfx") and n == F["maxpfx"]["victim"]
                    and p in set(crit_peers(m))):
                L.append(f"  neighbor {pa} maximum-prefix 2")
            if m["ibgp"] == "rr" and n in RRS and p in CLIENTS:
                broken = (F.get("rrclient") and p in F["rrclient"]["victims"])
                if not broken:
                    L.append(f"  neighbor {m['lo'][p]} route-reflector-client")
        if n == "RT01":
            if m["igp"] == "oe":
                L.append("  redistribute ospf 1 route-map RM-W2B")
            else:
                L.append(f"  redistribute eigrp {AS_EIGRP} route-map RM-W2B")
                # 故障 b2einternal は「両境界」限定(fixも境界のみ)。RT01 は常に健全
                L.append("  bgp redistribute-internal")
        if n in E_BOUNDARY:
            if m["igp"] == "oe":
                L.append(f"  redistribute eigrp {AS_EIGRP} route-map RM-E2B")
            else:
                L.append("  redistribute ospf 2 route-map RM-E2B")
            # IOS 既定は iBGP→IGP 再配送禁止。West 経路(iBGP)を IGP へ流すために
            # 明示が必要（ループはタグ+deny で防止する設計とセット。実機で確認済）
            if not F.get("b2einternal"):
                L.append("  bgp redistribute-internal")
        L.append(" exit-address-family")
        L.append("!")

    # おとり（無害・未適用）
    for did, dn, lines in m.get("decoys", []):
        if dn == n:
            L += [ln.format(rr1=m["lo"]["RT03"]) for ln in lines] + ["!"]
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------
# render: 問題ファイル一式
# ----------------------------------------------------------------------------
def emit(m, repo, depth):
    pid = f"GEN-CHAIN-{m['seed']}"
    pdir = os.path.join(repo, "problems", pid)
    os.makedirs(os.path.join(pdir, "initial"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "solution"), exist_ok=True)

    # problem.yml
    prob = {
        "id": pid,
        "title": (f"連鎖故障TS 12台 "
                  f"({'OSPF' if m['igp'] == 'oe' else 'EIGRP'}×iBGP-"
                  f"{'RR' if m['ibgp'] == 'rr' else 'fullmesh'}×"
                  f"{'EIGRP' if m['igp'] == 'oe' else 'OSPF2'}相互再配送, "
                  f"depth={depth}, seed={m['seed']})"),
        "exam": "ENARSI",
        "topics": ["ospf", "bgp", "route-reflector", "eigrp", "redistribution",
                   "chain-troubleshooting", "generated"],
        "difficulty": 5,
        "topology": "generated",
        "target_nodes": NODES,
        "points": 100,
        "access": "ssh",
        "ibgp": m["ibgp"],
        "igp_layout": "ospf-eigrp" if m["igp"] == "oe" else "eigrp-ospf",
        "lab": {"positions": POSITIONS,
                "links": [{"a": lk["a"], "a_if": lk["a_if"],
                           "b": lk["b"], "b_if": lk["b_if"]} for lk in m["links"]]},
    }
    with open(os.path.join(pdir, "problem.yml"), "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_chain_ts.py) seed={m['seed']} depth={depth}\n")
        yaml.safe_dump(prob, f, allow_unicode=True, sort_keys=False)

    # initial（auth 故障の fix に IF 名 parents を補完してから）
    for n in NODES:
        with open(os.path.join(pdir, "initial", f"{n}.cfg.j2"), "w",
                  encoding="utf-8") as f:
            f.write(render_node(m, n))
    lk = west_access_link(m)
    for fault in m["faults"]:
        for fx in fault["fixes"]:
            if fx.get("parents") is None and fx["node"] in ("RT11", "RT01") \
               and fault["id"] in ("l1_ospf_auth", "l1_mtu_mismatch",
                                   "l1_eigrp_auth_west"):
                slot = lk["a_if"] if fx["node"] == lk["a"] else lk["b_if"]
                fx["parents"] = [f"interface Ethernet{slot // 4}/{slot % 4}"]

    write_grading(m, pdir, pid)
    write_task(m, pdir, pid, depth)

    with open(os.path.join(pdir, "solution", "fault.json"), "w",
              encoding="utf-8") as f:
        json.dump({"chain": [{k: v for k, v in fa.items() if k != "fixes"}
                             for fa in m["faults"]],
                   "decoys": [{"id": d[0], "node": d[1]}
                              for d in m.get("decoys", [])]},
                  f, ensure_ascii=False, indent=1)
    fixes = []
    for fa in m["faults"]:
        fixes += fa["fixes"]
    with open(os.path.join(pdir, "solution", "fix.json"), "w",
              encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=1)
    write_solution_md(m, pdir, pid)
    return pdir


def write_grading(m, pdir, pid):
    lo = m["lo"]
    if m["igp"] == "oe":
        ospf_dom = ["RT10", "RT11", "RT01", "RT03", "RT04", "RT05", "RT06",
                    "RT12", "RT02", "RT07", "RT09"]
    else:
        # swap: West(RT10/11)の Lo0 は EIGRP→BGP 経由でしか見えないため対象外
        ospf_dom = ["RT01", "RT03", "RT04", "RT05", "RT06",
                    "RT12", "RT02", "RT07", "RT09"]
    pairs = [[a, b] for a in ospf_dom for b in ospf_dom if a != b]
    g = {
        "problem": pid,
        "total_points": 100,
        "defaults": {"genie_os": "iosxe"},
        "model": {
            "loopbacks": {n: lo[n] for n in NODES},
            "links": [{"a": lk["a"], "a_ip": lk["a_ip"],
                       "b": lk["b"], "b_ip": lk["b_ip"]} for lk in m["links"]],
        },
        "invariants": [
            {"type": "loop_free", "name": "転送ループ無し(全ペア・再配送還流の検出)",
             "points": 15},
            {"type": "reachability_all", "name": "OSPFドメイン内 Loopback 全到達",
             "points": 15, "pairs": pairs},
        ],
        "checks": [],
    }
    ck = g["checks"]

    def add(name, node, command, points, raw=None, parser=None, find=None,
            match=None):
        c = {"name": name, "node": node, "command": command, "points": points}
        if raw:
            c["raw"] = raw
        if parser:
            c["parser"] = parser
            c["find"] = find
            c["match"] = match
        ck.append(c)

    # --- 端点間到達性 30 ---
    add("RT10: West LAN1 発 → East LAN1 (172.21.0.1) 到達", "RT10",
        "ping 172.21.0.1 source Loopback10 repeat 5", 8,
        raw=[{"regex": "Success rate is [1-9]"}])
    add("RT10: West LAN2 発 → East LAN2 (172.21.1.1) 到達", "RT10",
        "ping 172.21.1.1 source Loopback11 repeat 5", 8,
        raw=[{"regex": "Success rate is [1-9]"}])
    add("RT08: East LAN1 発 → West LAN1 (172.20.0.1) 到達（戻り経路）", "RT08",
        "ping 172.20.0.1 source Loopback10 repeat 5", 8,
        raw=[{"regex": "Success rate is [1-9]"}])
    # ttl 上限必須: 故障状態(ブラックホール/ループ)で 30 ホップ全滅すると
    # CLI 応答待ちで採点自体が死ぬ(実機で確認済)。10 ホップで十分に East に届く。
    add("RT10: East への traceroute が East境界リンク(172.30.x)を経由", "RT10",
        "traceroute 172.21.0.1 source Loopback10 numeric timeout 1 probe 1 ttl 1 10", 6,
        raw=[{"regex": r"172\.30\."}])

    # --- 設計適合 25 ---
    # RT12 は rr では非client(反射の観測点=Originator/Cluster属性を要求)、
    # fullmesh では対等ピア(属性なし=community と経路存在のみ)。
    # East/West 両方を見る（片方だけだと rr_client_break 系の盲点になる。実機で確認済）
    if m["ibgp"] == "rr":
        add(f"RT12(非client観測点): East LAN1 経路が反射で届き community {COMM_E} 付き",
            "RT12", "show ip bgp 172.21.0.0", 4,
            raw=[{"regex": COMM_E}, {"regex": "(Originator|Cluster)"}])
        add(f"RT12(非client観測点): West LAN1 経路が反射で届き community {COMM_W} 付き",
            "RT12", "show ip bgp 172.20.0.0", 3,
            raw=[{"regex": COMM_W}, {"regex": "(Originator|Cluster)"}])
    else:
        add(f"RT12(観測点): East LAN1 経路が届き community {COMM_E} 付き",
            "RT12", "show ip bgp 172.21.0.0", 4, raw=[{"regex": COMM_E}])
        add(f"RT12(観測点): West LAN1 経路が届き community {COMM_W} 付き",
            "RT12", "show ip bgp 172.20.0.0", 3, raw=[{"regex": COMM_W}])
    add("RT03(RR1): East LAN1 を両境界(RT07/RT09)から受信（2点再配送の冗長）",
        "RT03", "show ip bgp 172.21.0.0", 6,
        raw=[{"contains": lo["RT07"]}, {"contains": lo["RT09"]}])
    if m["igp"] == "oe":
        add(f"RT08: West LAN1 の EIGRP外部経路に管理タグ {TAG_LOOP}（B2E再配送の設計適合）",
            "RT08", "show ip eigrp topology 172.20.0.0/24", 6,
            raw=[{"regex": f"tag is {TAG_LOOP}"}])
    else:
        add(f"RT08: West LAN1 が OSPF2 外部経路で管理タグ {TAG_LOOP} 付き（B2O再配送の設計適合）",
            "RT08", "show ip route 172.20.0.0 255.255.255.0", 6,
            raw=[{"regex": "ospf 2"}, {"regex": f"[Tt]ag {TAG_LOOP}"}])
    # ※「境界が West 経路を BGP で保持」チェックは実機検証の結果不採用(健全構成でも
    #   境界間直結リンク経由の還流で片側が必ず D EX/O E2 固着=不変条件にならない)
    add("RT08: static 残置なし（暫定対処の残置禁止）", "RT08",
        "show ip route static", 6, raw=[{"not_regex": "(?m)^S"}])

    # --- プロトコル健全性 15 ---
    # FULL を明示要求: EXSTART固着(MTU不一致等)でも neighbor 表示自体は残るため
    # contains では素通りする（採点盲点）
    def _full(neigh_lo):
        return {"regex": rf"(?m)^{neigh_lo.replace('.', chr(92) + '.')}\s+\d+\s+FULL"}
    if m["igp"] == "oe":
        add("RT01: OSPF 隣接 FULL (RT11/RT03/RT04)", "RT01", "show ip ospf neighbor", 5,
            raw=[_full(lo["RT11"]), _full(lo["RT03"]), _full(lo["RT04"])])
    else:
        add("RT01: OSPF 隣接 FULL (RT03/RT04)", "RT01", "show ip ospf neighbor", 3,
            raw=[_full(lo["RT03"]), _full(lo["RT04"])])
    if m["ibgp"] == "rr":
        add("RT03(RR1): iBGP セッション成立 (RT01/RT07/RT12 が Established)", "RT03",
            "show ip bgp summary", 5,
            raw=[{"regex": rf"(?m)^{lo['RT01'].replace('.', chr(92) + '.')}\s.*\d$"},
                 {"regex": rf"(?m)^{lo['RT07'].replace('.', chr(92) + '.')}\s.*\d$"},
                 {"regex": rf"(?m)^{lo['RT12'].replace('.', chr(92) + '.')}\s.*\d$"}])
    else:
        # fullmesh の生命線は RT01↔両East境界の直結セッション。RT01 側で直接確認
        # (9500 実機サイクルで判明した採点盲点の解消)
        add("RT01: iBGP セッション成立 (RT07/RT09/RT12 が Established)", "RT01",
            "show ip bgp summary", 5,
            raw=[{"regex": rf"(?m)^{lo['RT07'].replace('.', chr(92) + '.')}\s.*\d$"},
                 {"regex": rf"(?m)^{lo['RT09'].replace('.', chr(92) + '.')}\s.*\d$"},
                 {"regex": rf"(?m)^{lo['RT12'].replace('.', chr(92) + '.')}\s.*\d$"}])
    east_ips = []
    for lk in m["links"]:
        if lk["kind"] == "e" and "RT08" in (lk["a"], lk["b"]):
            east_ips.append(peer_ip(lk, "RT08"))
    if m["igp"] == "oe":
        add("RT08: EIGRP 隣接 2 本 (RT07/RT09)", "RT08", "show ip eigrp neighbors", 5,
            raw=[{"contains": ip} for ip in east_ips])
    else:
        # swap: East は OSPF2 (RIDは 2.x.x.x 系) / West の EIGRP 隣接は RT01 側で確認
        w_ip = next(peer_ip(lk, "RT01") for lk in m["links"]
                    if lk["kind"] == "a1" and "RT01" in (lk["a"], lk["b"]))
        add("RT08: OSPF2 隣接 FULL 2本 (RT07/RT09)", "RT08", "show ip ospf neighbor", 4,
            raw=[{"regex": r"(?m)^2\." + lo["RT07"].split(".", 1)[1].replace(".", r"\.")
                           + r"\s+\d+\s+FULL"},
                 {"regex": r"(?m)^2\." + lo["RT09"].split(".", 1)[1].replace(".", r"\.")
                           + r"\s+\d+\s+FULL"}])
        add("RT01: West EIGRP 隣接 (RT11)", "RT01", "show ip eigrp neighbors", 3,
            raw=[{"contains": w_ip}])

    total = sum(c["points"] for c in ck) + sum(i["points"] for i in g["invariants"])
    assert total == 100, f"points={total}"
    with open(os.path.join(pdir, "grading.yml"), "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_chain_ts.py) seed={m['seed']}\n")
        yaml.safe_dump(g, f, allow_unicode=True, sort_keys=False, width=200)


def write_task(m, pdir, pid, depth):
    lo = m["lo"]
    if m["ibgp"] == "rr":
        ibgp_text = ("RR は RT03/RT04 の2台（クラスタ冗長）。client は\n"
                     "   RT01/RT02/RT05/RT06/RT07/RT09。RT12 は **非client** として両RRとピア。")
    else:
        ibgp_text = ("**フルメッシュ**（RRなし・BGP話者9台が全対全でピア。"
                     "RT03/RT04/RT12 も対等な一般ノード）。")
    if m["igp"] == "oe":
        west_text = ("**OSPF**: area0=コア（RT01-07,09,12 の該当リンク・Lo0）、area1=West\n"
                     "   （RT10/RT11・User LAN 172.20.0.0/24, 172.20.1.0/24）。RT01 が ABR。")
        w3_text = ("User LAN(172.20.0.0/24, 172.20.1.0/24)は RT01 が OSPF→BGP 再配送し\n"
                   f"   community **{COMM_W}** を付与。RT01 は同 LAN を **area1 の範囲集約で\n"
                   "   not-advertise**（IA として流さない）＝ **User LAN の伝搬は BGP が唯一の経路**。")
        e4_text = (f"RT07/RT09 の2点で EIGRP⇄BGP 相互再配送（冗長）。\n"
                   f"   EIGRP→BGP は Server LAN(172.21.0.0/24, 172.21.1.0/24)と RT08 Lo0 に\n"
                   f"   community **{COMM_E}** を付与。BGP→EIGRP はタグ **{TAG_LOOP}** を付け、\n"
                   f"   EIGRP→BGP 側でそのタグを **deny**（再配送ループ防止）。境界の EIGRP側リンク\n"
                   "   (172.30.x/30) は **OSPF area0 へ passive で広告**（BGP next-hop の解決性確保）。")
    else:
        west_text = ("**IGP**: コア=OSPF area0（RT01-07,09,12）。West=**EIGRP AS65100**\n"
                     "   （RT10/RT11・User LAN 172.20.0.0/24, 172.20.1.0/24。RT01 が単一境界）。\n"
                     "   East=**OSPF プロセス2**（RT07/RT08/RT09。RT07/09 が二重境界）。")
        w3_text = ("User LAN と RT10/RT11 の Lo0 は RT01 が EIGRP→BGP 再配送し\n"
                   f"   community **{COMM_W}** を付与（**West の伝搬は BGP が唯一の経路**）。\n"
                   f"   BGP→EIGRP はタグ **{TAG_LOOP}**＋EIGRP→BGP 側で deny（還流防止）。\n"
                   "   再配送経路の next-hop は **自Lo0 に set**（解決性の自己完結）。")
        e4_text = (f"RT07/RT09 の2点で OSPF2⇄BGP 相互再配送（冗長）。\n"
                   f"   OSPF2→BGP は Server LAN と RT08 Lo0 に community **{COMM_E}** を付与し\n"
                   f"   **next-hop を自Lo0 に set**。BGP→OSPF2 は **subnets**＋タグ **{TAG_LOOP}**、\n"
                   f"   OSPF2→BGP 側でタグを **deny**（再配送ループ防止）。")
    t = f"""# 問題 {pid} : ネットワーク全域トラブルシュート（連鎖故障・12台）

## 状況
本社(West)のユーザー LAN から、データセンター(East)のサーバ LAN への通信が
**完全に不通**になっている。前任者が複数の変更を行った直後から障害が続いており、
**故障は1つとは限らない**。また、**ある問題を直すと初めて次の症状が観測できる**
可能性がある。設計書（下記）へ完全復旧させよ。

```
 West {'OSPF area1  ' if m['igp'] == 'oe' else 'EIGRP 65100'}      コア AS{AS_CORE} (OSPF area0 + iBGP)       East {'EIGRP ' + str(AS_EIGRP) if m['igp'] == 'oe' else 'OSPF proc2'}
 RT10 ─ RT11 ─ RT01 ─┬─ RT03{'(RR1)' if m['ibgp'] == 'rr' else '     '} ─ RT05 ─┬─ RT02 ─ RT07 ─┬─ RT08
(User LAN)     {'(ABR)' if m['igp'] == 'oe' else '(境W)'}  └─ RT04{'(RR2)' if m['ibgp'] == 'rr' else '     '} ─ RT06 ─┴─(RT06─RT09)───┴─(RT07─RT09)
                          └RT12(観測点)┘                    (Server LAN)
```

## 設計書（=復旧目標。これ以外の情報は与えられない）
1. {west_text}
2. **iBGP AS{AS_CORE}**: {ibgp_text}
   全ピアリングは Loopback0 間・**AF方式**（`no bgp default ipv4-unicast` ＋
   `address-family ipv4` で activate / send-community）。
3. **West経路**: {w3_text}
4. **East経路**: {e4_text}
5. **健全性**: User LAN ⇄ Server LAN が両方向到達・転送ループ無し・
   static による暫定対処は禁止（残置は減点）。

## ルータ台帳
| ノード | Lo0 | 役割 |
|--------|-----|------|
""" + "\n".join(
        f"| {n} | {lo[n]}/32 | " + {
            "RT01": ("境界W (ABR・OSPF→BGP)" if m["igp"] == "oe"
                     else "境界W (EIGRP⇄BGP)"),
            "RT02": "コア" + (" client" if m["ibgp"] == "rr" else ""),
            "RT03": ("RR1" if m["ibgp"] == "rr" else "コア"),
            "RT04": ("RR2" if m["ibgp"] == "rr" else "コア"),
            "RT05": "コア" + (" client" if m["ibgp"] == "rr" else ""),
            "RT06": "コア" + (" client" if m["ibgp"] == "rr" else ""),
            "RT07": ("境界E1 (EIGRP⇄BGP)" if m["igp"] == "oe"
                     else "境界E1 (OSPF2⇄BGP)"),
            "RT08": "East内部 (Server LAN)",
            "RT09": ("境界E2 (EIGRP⇄BGP)" if m["igp"] == "oe"
                     else "境界E2 (OSPF2⇄BGP)"),
            "RT10": "West端末 (User LAN)", "RT11": "Westアグリゲーション",
            "RT12": ("観測点 (非client)" if m["ibgp"] == "rr" else "コア (観測点)")}[n]
        + " |" for n in NODES) + f"""

## 制約
- 設計書にある構成要素の**削除・置換えは禁止**（例: RR を経由しない直接ピア追加、
  static での迂回、再配送の一本化）。修復のみで復旧させること。
- BGP 設定は**AF方式**（社内標準）。
- ポリシー変更を既存セッションへ反映させる操作は各自で行うこと。

## アクセス
SSH `SUZUKI / CCNP`（管理IPは出題時に提示）。CML コンソールでも可。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem={pid} --vault-password-file <(printf 'CCNP\\n')
```
採点は途中実行可能。修復が進むほど部分点が増える（どのレイヤまで直ったかの
進捗確認に使ってよい）。
"""
    with open(os.path.join(pdir, "task.md"), "w", encoding="utf-8") as f:
        f.write(t)


def write_solution_md(m, pdir, pid):
    lines = [f"# {pid} 解答（採点者用）", "",
             f"連鎖: {' → '.join(fa['layer'] + ':' + fa['id'] for fa in m['faults']) or '(baseline・故障なし)'}",
             ""]
    for fa in m["faults"]:
        lines.append(f"## {fa['layer']}: {fa['id']}")
        lines.append(fa["desc"])
        lines.append("")
    if m.get("decoys"):
        lines.append("## おとり（無害・修正不要）")
        for did, dn, _ in m["decoys"]:
            lines.append(f"- {dn}: {did}（未適用/無影響の残骸。削除しなくても減点なし）")
        lines.append("")
    lines.append("修復は solution/fix.json（fix_generated.yml で投入可）。")
    lines.append("下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。")
    with open(os.path.join(pdir, "solution", "solution.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--chain-depth", type=int, default=3, choices=[0, 2, 3, 4])
    ap.add_argument("--decoys", type=int, default=2,
                    help="無害なおとり設定の数(0で無効。既定2)")
    ap.add_argument("--faults-per-layer", type=int, default=1, choices=[1, 2],
                    help="同一レイヤの故障数(2=症状の重ね合わせ)")
    ap.add_argument("--branch-fault", action="store_true",
                    help="L3枠を分岐連鎖(冗長境界に別種の故障×2)に置換(rrモード限定)")
    ap.add_argument("--ibgp", choices=["rr", "fullmesh"], default="rr",
                    help="iBGP構造軸: RRクラスタ | フルメッシュ(9台全対全)")
    ap.add_argument("--igp-layout", choices=["ospf-eigrp", "eigrp-ospf"],
                    default="ospf-eigrp",
                    help="IGP入替軸: West-OSPF/East-EIGRP(base) | West-EIGRP/East-OSPF2")
    a = ap.parse_args()

    igp = "oe" if a.igp_layout == "ospf-eigrp" else "eo"
    # v2(2026-07-07): fullmesh×eigrp-ospf / branch×eigrp-ospf は baseline 実機検証済み解禁。
    # fullmesh×branch のみ構造的に不成立(brpass が他ピア経由で迂回)のため恒久ブロック
    if a.branch_fault and a.ibgp != "rr":
        ap.error("--branch-fault は rr モード限定"
                 "(fullmesh では境界のRRピアpasswordが他ピア経由で迂回され実効しない)")
    m = build_model(a.seed, ibgp=a.ibgp, igp=igp)
    rnd = random.Random(a.seed + 991)
    inject(m, a.chain_depth, rnd, decoys=a.decoys,
           width=a.faults_per_layer, branch=a.branch_fault)
    pdir = emit(m, a.repo, a.chain_depth)
    print(f"generated: {pdir}")
    for fa in m["faults"]:
        print(f"  {fa['layer']}: {fa['id']} — {fa['desc']}")
    if not m["faults"]:
        print("  (baseline: 故障なし)")
    for did, dn, _ in m.get("decoys", []):
        print(f"  decoy: {did} @ {dn}")


if __name__ == "__main__":
    main()
