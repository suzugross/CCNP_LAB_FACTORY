#!/usr/bin/env python3
"""DMVPN 完全版トラブルシュート生成器（BL-006・ENARSI-DMVPN-IPSEC-01 の反転）。

正準トポロジ(実機検証済みの ENARSI-DMVPN-IPSEC-01 と同一・IOSv・console採点):
  RT01(Hub/NHS) / RT02(Spoke1) / RT03(Spoke2) -- RT04(WAN transit・変更禁止)
  underlay 固定(10.0.14/24/34.0 の /30)。overlay Tunnel0 10.255.<K>.0/24。
  健全形 = Phase 3 (redirect/shortcut) + IKEv2 NGE (AES-GCM-256/SHA384/DH19)
  + wildcard keyring + ESP transport + EIGRP。day0 に故障1種を焼き込む。

★故障は day0 注入が原則(PoC 実証: NHRP 系は稼働中注入だと hub 旧キャッシュで
  動いて見える偽の非故障になる)。本生成器は initial cfg 焼き込みなので決定的。

故障カタログ(--fault, 既定 seed ランダム。症状は poc/dmvpn-ipsec/README.md で実機確定):
  u1_underlay_default_missing : victim spoke の default route 欠落。tunnel up/up の
                                まま IKE/NHRP 全滅(最下層が上位を全部隠す)。難3
  g1_spoke_p2p_gre       : victim spoke が p2p GRE + tunnel destination。hub 経由は
                           全部通るが直行だけ永久不成立(対向に IX 残骸)。難4
  g2_tunnel_key_mismatch : victim spoke の tunnel key 違い。IKEv2 READY のまま
                           show dmvpn が NHRP 固着(IKE/GRE の層切り分け)。難4
  n1_nhs_nbma_wrong      : victim spoke の NHS 静的マップ NBMA 誤り。登録先不達。難3
  n2_nhrp_auth_mismatch  : victim spoke の NHRP 認証キー違い(同長8字の写し間違い)。
                           hub が登録を黙殺する完全サイレント故障。難5
  i1_psk_mismatch        : victim spoke の PSK 違い。IKE 不成立→NHRP も上がらない。難3
  i2_transform_mismatch  : victim spoke の ESP スイート違い(CBC+HMAC)。IKEv2 SA は
                           READY・Child SA だけ失敗(IKE/IPsec の切り分け)。難4
  i3_keyring_perpeer     : 両 spoke の keyring を hub 限定に。hub-spoke 完全正常・
                           spoke間 ping も通る(永久ハブ折返し)が直行だけ IX+DX。難5
  i4_protection_missing  : victim spoke の tunnel protection 欠落。hub が平文 GRE を
                           破棄し当該 spoke のみ登録不可(対向 spoke は正常)。難3
  i6_mode_tunnel         : victim spoke の transform が mode tunnel。不通にならず
                           Tunnel mode で合意して動く=仕様違反を状態で検出。難4
  r1_split_horizon_on    : hub の split-horizon 有効(no ip split-horizon 欠落)。
                           隣接は全 UP・spoke 同士の経路だけ消える(最頻出)。難3
  p1_redirect_missing    : hub の ip nhrp redirect 欠落。全到達 OK だが永久ハブ経由
                           (動的エントリ不在・shortcut 空)。難4・実機実証済
  n4_multicast_map_tunnelip : victim spoke の map multicast をトンネルIPに誤記(旧来
                           3行構文)。登録/IKE は正常・EIGRP 隣接だけフラップ
                           (retry limit exceeded)。ユーザ実戦由来(2026-07-10)。難4
  r2_underlay_in_eigrp   : hub の EIGRP network がクラスフル 10.0.0.0 で underlay を
                           巻き込み広告→スポークが NBMA into tunnel の再帰学習で
                           トンネル周期断。ユーザ実戦由来(2026-07-10)。難4
  i7_profile_no_transform: victim spoke の ipsec profile に set transform-set が無い
                           (TS-GCM は正しく定義済み・参照だけ欠落)。暗黙デフォルト
                           TS(CBC/tunnel)にフォールバックし Child SA 交渉不成立。
                           i2 と症状同型・config 指紋違い(「定義と参照の分離」
                           ファミリ)。ユーザ発案(BL-089・2026-08-05)。難4
  i8_wrong_profile_referenced: victim spoke の tunnel protection が実在する別 profile
                           (IPSEC-LEGACY=CBC/tunnel のレガシー残骸)を参照。
                           Child SA 不成立。fix は参照の付け替え。難4

★IOSv 15.9 実機知見(2026-07-09 GEN-DMVPN-7801 で発見):
  - `ip nhrp authentication` は最大 8 文字。9 文字以上は day0 で黙って拒否され
    「故障が蒸発」する → 鍵は必ず 8 文字で生成。
  - `ip nhrp map multicast dynamic`(hub) と `ip nhrp shortcut`(spoke) は
    暗黙デフォルト(run 非表示・省略しても動く) → 故障候補 n3/p2 は非故障のため廃止。
    baseline には文書価値として明示行を残す。

採点 = ENARSI-DMVPN-IPSEC-01 で実機確立した 13 チェック(値差し替え)を修復判定に流用。
  能動 ping (sorted 順で show より先に走る) が直結誘発の 0点発射を兼ねる。

出力: problems/GEN-DMVPN-<seed>/ {problem.yml, initial/*.cfg.j2, task.md, grading.yml,
      solution/{fault.json, fix.json}}。fix.json は fix_generated.yml 互換
      (lines はコンフィグモード直列・exec で clear を投入)。
使い方: gen_dmvpn_ts.py --repo . --seed <int> [--fault <name>] [--faults 2]
--faults 2 (BL-091・2026-08-05): 1ルータ1故障で2箇所(hub+spoke または spoke×2)。
  i3/r2 は全域影響のため単独専用。チケットは中立文面2枚(相互矛盾クレームなし)＋
  「原因は1か所とは限らない」注記。難易度= max+1(上限5)。
  実機フルサイクル済= 31002(i1+i2 spoke×spoke 5→100)/31001(r1+n2 hub×spoke 35→100)。
"""
import argparse
import json
import os
import random

import yaml

FAULTS = ["u1_underlay_default_missing", "g1_spoke_p2p_gre", "g2_tunnel_key_mismatch",
          "n1_nhs_nbma_wrong", "n2_nhrp_auth_mismatch",
          "i1_psk_mismatch", "i2_transform_mismatch", "i3_keyring_perpeer",
          "i4_protection_missing", "i6_mode_tunnel", "r1_split_horizon_on",
          "p1_redirect_missing", "n4_multicast_map_tunnelip", "r2_underlay_in_eigrp",
          "i7_profile_no_transform", "i8_wrong_profile_referenced"]
DIFFICULTY = {"u1_underlay_default_missing": 3, "g1_spoke_p2p_gre": 4,
              "g2_tunnel_key_mismatch": 4, "n1_nhs_nbma_wrong": 3,
              "n2_nhrp_auth_mismatch": 5,
              "i1_psk_mismatch": 3, "i2_transform_mismatch": 4,
              "i3_keyring_perpeer": 5, "i4_protection_missing": 3,
              "i6_mode_tunnel": 4, "r1_split_horizon_on": 3,
              "p1_redirect_missing": 4, "n4_multicast_map_tunnelip": 4,
              "r2_underlay_in_eigrp": 4,
              "i7_profile_no_transform": 4, "i8_wrong_profile_referenced": 4}
# hub 起因(victim 選択なし) / 両 spoke 起因
HUB_FAULTS = {"r1_split_horizon_on", "p1_redirect_missing", "r2_underlay_in_eigrp"}
BOTH_SPOKE_FAULTS = {"i3_keyring_perpeer"}

NBMA = {"RT01": "10.0.14.1", "RT02": "10.0.24.1", "RT03": "10.0.34.1"}
GW = {"RT01": "10.0.14.2", "RT02": "10.0.24.2", "RT03": "10.0.34.2"}
LO = {"RT01": "1.1.1.1", "RT02": "2.2.2.2", "RT03": "3.3.3.3"}
TIP_OCT = {"RT01": 1, "RT02": 2, "RT03": 3}      # overlay 第4オクテット


def rand_values(rnd):
    """overlay/AS/key 群を seed から決める(underlay と Lo は正準固定)。"""
    # ★ip nhrp authentication は最大 8 文字(超過は day0 で黙って拒否される・実機実証)
    words = ["HONSHA", "SECNET", "WANSEC", "OVLNET", "BRANCH", "CRYPTD"]
    return {
        "ov": f"10.255.{rnd.randint(0, 254)}",          # overlay /24
        "asn": rnd.randint(100, 899),                    # EIGRP AS
        "tkey": rnd.randint(100, 899),                   # GRE tunnel key
        "netid": rnd.randint(1, 99),                     # NHRP network-id
        "nhrp_key": f"{rnd.choice(words)}{rnd.randint(10, 99)}",
        "psk": f"Ss2026#Gen{rnd.randint(1000, 9999)}",
    }


def tip(v, node):
    return f"{v['ov']}.{TIP_OCT[node]}"


def wrong_key(v):
    """n2 用: 正キーと同長 8 文字の「写し間違い」キー(末尾2桁スワップ)。
    ★9文字以上は IOS が受理しないので X 付加方式は使えない(実機実証)。"""
    k = v["nhrp_key"]
    d = k[-2:]
    return k[:-2] + (d[::-1] if d != d[::-1] else f"{(int(d) + 13) % 100:02d}")


def crypto_lines(v, node, faults, victims):
    """IKEv2/IPsec ブロック(故障注入込み)。全拠点共通の骨格。
    faults=故障名list / victims=故障名→犯人ノード(hub系は RT01)。"""
    def hit(f):
        return victims.get(f) == node
    psk = v["psk"]
    if hit("i1_psk_mismatch"):
        psk = psk + "X"                                   # 1文字違い
    if "i3_keyring_perpeer" in faults and node != "RT01":
        addr = f"address {NBMA['RT01']} 255.255.255.255"  # hub 限定(wildcard 潰し)
    else:
        addr = "address 0.0.0.0 0.0.0.0"
    if hit("i2_transform_mismatch"):
        ts = "crypto ipsec transform-set TS-GCM esp-aes 256 esp-sha256-hmac"
    else:
        ts = "crypto ipsec transform-set TS-GCM esp-gcm 256"
    mode = " mode tunnel" if hit("i6_mode_tunnel") else " mode transport"
    # i7: profile の set transform-set 参照だけ欠落(TS-GCM 定義は正しく残す)。
    #     暗黙デフォルトTSへフォールバック→Child SA 交渉不成立(BL-089・要は
    #     「定義はあるのに参照が無い」ファミリ)
    prof = ["crypto ipsec profile IPSEC-DMVPN"]
    if not hit("i7_profile_no_transform"):
        prof.append(" set transform-set TS-GCM")
    prof += [" set pfs group19", " set ikev2-profile IKEV2-DMVPN", "!"]
    # i8: 実在するレガシー profile(CBC/tunnel)を victim にだけ残置(残骸デコイ兼
    #     誤参照先)。IKEv2 profile は共用=IKE 層は健全で Child SA だけ落ちる
    legacy = []
    if hit("i8_wrong_profile_referenced"):
        legacy = ["crypto ipsec transform-set TS-LEGACY esp-aes esp-sha-hmac", "!",
                  "crypto ipsec profile IPSEC-LEGACY",
                  " set transform-set TS-LEGACY",
                  " set ikev2-profile IKEV2-DMVPN", "!"]
    return ["crypto ikev2 proposal PROP-NGE",
            " encryption aes-gcm-256", " prf sha384", " group 19", "!",
            "crypto ikev2 policy POL-NGE", " proposal PROP-NGE", "!",
            "crypto ikev2 keyring KR-DMVPN", " peer ANY", f"  {addr}",
            f"  pre-shared-key {psk}", "!",
            "crypto ikev2 profile IKEV2-DMVPN",
            " match identity remote address 0.0.0.0",
            " authentication remote pre-share", " authentication local pre-share",
            " keyring local KR-DMVPN", " dpd 30 5 on-demand", "!",
            ts, mode, "!"] + prof + legacy


def render_hub(v, faults):
    L = ["! RT01 初期構成 (Hub/NHS・DMVPN TS: 昨日まで正常稼働していた既設網)",
         "interface Loopback0", f" ip address {LO['RT01']} 255.255.255.255", "!",
         "interface {{ links[0] }}",
         " description === underlay to RT04 (WAN transit) ===",
         f" ip address {NBMA['RT01']} 255.255.255.252", " no shutdown", "!",
         f"ip route 0.0.0.0 0.0.0.0 {GW['RT01']}", "!"]
    L += crypto_lines(v, "RT01", faults, victims={})
    t = ["interface Tunnel0",
         f" ip address {tip(v, 'RT01')} 255.255.255.0",
         " no ip redirects", " ip mtu 1400", " ip tcp adjust-mss 1360",
         f" ip nhrp authentication {v['nhrp_key']}"]
    # ★IOSv15.9では map multicast dynamic は暗黙デフォルト(run 非表示)。明示は文書価値
    t.append(" ip nhrp map multicast dynamic")
    t.append(f" ip nhrp network-id {v['netid']}")
    if "p1_redirect_missing" not in faults:
        t.append(" ip nhrp redirect")
    if "r1_split_horizon_on" not in faults:
        t.append(f" no ip split-horizon eigrp {v['asn']}")
    t += [" tunnel source {{ links[0] }}", " tunnel mode gre multipoint",
          f" tunnel key {v['tkey']}",
          " tunnel protection ipsec profile IPSEC-DMVPN", "!"]
    L += t
    if "r2_underlay_in_eigrp" in faults:
        # 「トンネル区間だけ広告したかった」のにクラスフル指定で underlay まで巻き込む
        L += [f"router eigrp {v['asn']}",
              f" network {LO['RT01']} 0.0.0.0",
              " network 10.0.0.0", "!"]
    else:
        L += [f"router eigrp {v['asn']}",
              f" network {LO['RT01']} 0.0.0.0",
              f" network {v['ov']}.0 0.0.0.255", "!"]
    return L


def render_spoke(node, v, faults, victims):
    def hit(f):
        return victims.get(f) == node
    L = [f"! {node} 初期構成 (Spoke・DMVPN TS: 昨日まで正常稼働していた既設網)",
         "interface Loopback0", f" ip address {LO[node]} 255.255.255.255", "!",
         "interface {{ links[0] }}",
         " description === underlay to RT04 (WAN transit) ===",
         f" ip address {NBMA[node]} 255.255.255.252", " no shutdown", "!"]
    if not hit("u1_underlay_default_missing"):
        L += [f"ip route 0.0.0.0 0.0.0.0 {GW[node]}", "!"]
    L += crypto_lines(v, node, faults, victims)
    t = ["interface Tunnel0",
         f" ip address {tip(v, node)} 255.255.255.0",
         " no ip redirects", " ip mtu 1400", " ip tcp adjust-mss 1360"]
    if hit("n2_nhrp_auth_mismatch"):
        t.append(f" ip nhrp authentication {wrong_key(v)}")
    else:
        t.append(f" ip nhrp authentication {v['nhrp_key']}")
    t.append(f" ip nhrp network-id {v['netid']}")
    if hit("n1_nhs_nbma_wrong"):
        # NBMA を WAN 側ゲートウェイ(=RT04 の IF)に誤記 — ありがちな写し間違い
        t.append(f" ip nhrp nhs {tip(v, 'RT01')} nbma {GW[node]} multicast")
    elif hit("n4_multicast_map_tunnelip"):
        # 旧来3行構文で restore し、multicast の複製先を NBMA でなくトンネルIPに誤記。
        # ユニキャスト(登録/IKE)は全部動き、multicast(EIGRP hello)だけ運ばれない
        t.append(f" ip nhrp map {tip(v, 'RT01')} {NBMA['RT01']}")
        t.append(f" ip nhrp map multicast {tip(v, 'RT01')}")
        t.append(f" ip nhrp nhs {tip(v, 'RT01')}")
    else:
        t.append(f" ip nhrp nhs {tip(v, 'RT01')} nbma {NBMA['RT01']} multicast")
    # ★IOSv15.9では shortcut も暗黙デフォルト(run 非表示)。明示は文書価値
    t.append(" ip nhrp shortcut")
    t.append(" tunnel source {{ links[0] }}")
    if hit("g1_spoke_p2p_gre"):
        t += [f" tunnel destination {NBMA['RT01']}"]      # p2p GRE (mode gre ip 既定)
    else:
        t.append(" tunnel mode gre multipoint")
    if hit("g2_tunnel_key_mismatch"):
        t.append(f" tunnel key {v['tkey'] + 1}")
    else:
        t.append(f" tunnel key {v['tkey']}")
    if not hit("i4_protection_missing"):
        prof = ("IPSEC-LEGACY" if hit("i8_wrong_profile_referenced")
                else "IPSEC-DMVPN")
        t.append(f" tunnel protection ipsec profile {prof}")
    t.append("!")
    L += t
    L += [f"router eigrp {v['asn']}",
          f" network {LO[node]} 0.0.0.0",
          f" network {v['ov']}.0 0.0.0.255", "!"]
    return L


def render_wan():
    return ["! RT04 初期構成 (WAN/NBMA トランジット) ★変更禁止★",
            "interface {{ links[0] }}",
            " description === underlay to RT01 (Hub) ===",
            " ip address 10.0.14.2 255.255.255.252", " no shutdown", "!",
            "interface {{ links[1] }}",
            " description === underlay to RT02 (Spoke1) ===",
            " ip address 10.0.24.2 255.255.255.252", " no shutdown", "!",
            "interface {{ links[2] }}",
            " description === underlay to RT03 (Spoke2) ===",
            " ip address 10.0.34.2 255.255.255.252", " no shutdown", "!"]


def build_fix(fault, v, victim):
    """故障を健全へ是正する fix エントリ列(fix_generated.yml 互換・console 投入可)。
    crypto 系は clear crypto session / NHRP 系は clear ip nhrp を exec で添える。"""
    clear_crypto = {"node": victim, "exec": [{"command": "clear crypto session"}]}
    clear_nhrp = {"node": victim, "exec": [{"command": "clear ip nhrp"}]}
    if fault == "u1_underlay_default_missing":
        return [{"node": victim, "lines": [f"ip route 0.0.0.0 0.0.0.0 {GW[victim]}"]}]
    if fault == "g1_spoke_p2p_gre":
        return [{"node": victim, "lines": ["interface Tunnel0", "no tunnel destination",
                                           "tunnel mode gre multipoint"]}, clear_crypto]
    if fault == "g2_tunnel_key_mismatch":
        return [{"node": victim, "lines": ["interface Tunnel0",
                                           f"tunnel key {v['tkey']}"]}, clear_crypto]
    if fault == "n1_nhs_nbma_wrong":
        return [{"node": victim, "lines": [
            "interface Tunnel0",
            f"no ip nhrp nhs {tip(v, 'RT01')} nbma {GW[victim]} multicast",
            f"ip nhrp nhs {tip(v, 'RT01')} nbma {NBMA['RT01']} multicast"]}, clear_nhrp]
    if fault == "n2_nhrp_auth_mismatch":
        return [{"node": victim, "lines": ["interface Tunnel0",
                                           f"ip nhrp authentication {v['nhrp_key']}"]},
                clear_nhrp]
    if fault == "i1_psk_mismatch":
        return [{"node": victim, "lines": ["crypto ikev2 keyring KR-DMVPN", "peer ANY",
                                           f"pre-shared-key {v['psk']}"]}, clear_crypto]
    if fault in ("i2_transform_mismatch", "i6_mode_tunnel"):
        return [{"node": victim, "lines": ["crypto ipsec transform-set TS-GCM esp-gcm 256",
                                           "mode transport"]}, clear_crypto]
    if fault == "i3_keyring_perpeer":
        return [{"node": n, "lines": ["crypto ikev2 keyring KR-DMVPN", "peer ANY",
                                      "address 0.0.0.0 0.0.0.0"]}
                for n in ("RT02", "RT03")]
    if fault == "i4_protection_missing":
        return [{"node": victim, "lines": [
            "interface Tunnel0", "tunnel protection ipsec profile IPSEC-DMVPN"]}]
    # i7/i8: profile 内容/参照の変更は clear crypto session では反映されず
    # IKE 固着が続く(2026-08-05 実機実証: 21007 で 11分固着→bounce で即 READY)。
    # Tunnel0 shut/no shut をfixに含める
    bounce = [{"node": victim, "lines": ["interface Tunnel0", "shutdown"]},
              {"node": victim, "lines": ["interface Tunnel0", "no shutdown"]}]
    if fault == "i7_profile_no_transform":
        return [{"node": victim, "lines": ["crypto ipsec profile IPSEC-DMVPN",
                                           "set transform-set TS-GCM"]}] + bounce
    if fault == "i8_wrong_profile_referenced":
        # 最小手=参照の付け替え(レガシー定義の残置は採点対象外・解説で言及)
        return [{"node": victim, "lines": [
            "interface Tunnel0",
            "tunnel protection ipsec profile IPSEC-DMVPN"]}] + bounce
    if fault == "n4_multicast_map_tunnelip":
        return [{"node": victim, "lines": [
            "interface Tunnel0",
            f"no ip nhrp map multicast {tip(v, 'RT01')}",
            f"ip nhrp map multicast {NBMA['RT01']}"]}, clear_nhrp]
    if fault == "r2_underlay_in_eigrp":
        return [{"node": "RT01", "lines": [
            f"router eigrp {v['asn']}",
            "no network 10.0.0.0",
            f"network {v['ov']}.0 0.0.0.255"]}]
    if fault == "r1_split_horizon_on":
        return [{"node": "RT01", "lines": ["interface Tunnel0",
                                           f"no ip split-horizon eigrp {v['asn']}"]}]
    if fault == "p1_redirect_missing":
        return [{"node": "RT01", "lines": ["interface Tunnel0", "ip nhrp redirect"]}]
    raise SystemExit(f"unknown fault {fault}")


def build_grading(prob_id, v):
    """ENARSI-DMVPN-IPSEC-01 で実機確立した 13 チェック(値差し替え)。"""
    ov = v["ov"].replace(".", r"\.")
    h, s1, s2 = (tip(v, n).replace(".", r"\.") for n in ("RT01", "RT02", "RT03"))
    return {"problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"},
            "checks": [
        {"name": "RT01(Hub): 両スポークが登録され DMVPN セッションが UP",
         "node": "RT01", "command": "show dmvpn",
         "raw": [{"contains": "Type:Hub"},
                 {"regex": rf"10\.0\.24\.1\s+{s1}\s+UP\s+\S+\s+D(T[12])?(?!\w)"},
                 {"regex": rf"10\.0\.34\.1\s+{s2}\s+UP\s+\S+\s+D(T[12])?(?!\w)"}], "points": 10},
        {"name": "RT01(Hub): 両スポークとの IKEv2 SA が READY",
         "node": "RT01", "command": "show crypto ikev2 sa",
         "raw": [{"regex": r"10\.0\.24\.1/500\s+\S+\s+READY"},
                 {"regex": r"10\.0\.34\.1/500\s+\S+\s+READY"}], "points": 10},
        {"name": "RT01(Hub): IKEv2 SA が AES-GCM-256 / PRF SHA384 / DH19 / PSK",
         "node": "RT01", "command": "show crypto ikev2 sa",
         "raw": [{"regex": "Encr: AES-GCM, keysize: 256"}, {"regex": "PRF: SHA384"},
                 {"regex": "DH Grp:19"}, {"regex": "Auth sign: PSK"}], "points": 10},
        {"name": "RT01(Hub): ESP が transport mode / esp-gcm で暗号化カウンタが加算",
         "node": "RT01", "command": "show crypto ipsec sa",
         "raw": [{"regex": "transform: esp-gcm"},
                 {"regex": r"in use settings =\{Transport,"},
                 {"not_contains": "={Tunnel,"},
                 {"regex": "#pkts encaps: [1-9]"},
                 {"regex": "#pkts decaps: [1-9]"}], "points": 10},
        {"name": f"RT02(Spoke1): {LO['RT03']}/32 の next-hop がハブ({tip(v, 'RT01')})のまま",
         "node": "RT02", "command": "show ip route", "parser": "show ip route",
         "find": "vrf.*.address_family.*.routes.*",
         "match": {"route": f"{LO['RT03']}/32", "source_protocol": "eigrp",
                   "next_hop.next_hop_list.*.next_hop": tip(v, "RT01"),
                   "next_hop.next_hop_list.*.outgoing_interface": "Tunnel0"},
         "points": 10},
        {"name": f"RT03(Spoke2): {LO['RT02']}/32 の next-hop がハブ({tip(v, 'RT01')})のまま",
         "node": "RT03", "command": "show ip route", "parser": "show ip route",
         "find": "vrf.*.address_family.*.routes.*",
         "match": {"route": f"{LO['RT02']}/32", "source_protocol": "eigrp",
                   "next_hop.next_hop_list.*.next_hop": tip(v, "RT01"),
                   "next_hop.next_hop_list.*.outgoing_interface": "Tunnel0"},
         "points": 5},
        {"name": "RT02(Spoke1): スポーク間疎通 (能動・直結誘発)",
         "node": "RT02", "command": f"ping {LO['RT03']} source Loopback0 repeat 5",
         "raw": [{"regex": "Success rate is [1-9]"}], "points": 5},
        {"name": "RT03(Spoke2): スポーク間疎通 (能動・直結誘発)",
         "node": "RT03", "command": f"ping {LO['RT02']} source Loopback0 repeat 5",
         "raw": [{"regex": "Success rate is [1-9]"}], "points": 5},
        {"name": "RT02(Spoke1): スポーク2への動的(直結)トンネルが UP",
         "node": "RT02", "command": "show dmvpn",
         "raw": [{"regex": rf"10\.0\.34\.1\s+{s2}\s+UP\s+\S+\s+D(T[12])?(?!\w)"}], "points": 10},
        {"name": "RT03(Spoke2): スポーク1への動的(直結)トンネルが UP",
         "node": "RT03", "command": "show dmvpn",
         "raw": [{"regex": rf"10\.0\.24\.1\s+{s1}\s+UP\s+\S+\s+D(T[12])?(?!\w)"}], "points": 5},
        {"name": "RT02(Spoke1): スポーク間の IKEv2 SA が動的に確立 (直行暗号の証明1)",
         "node": "RT02", "command": "show crypto ikev2 sa",
         "raw": [{"regex": r"10\.0\.34\.1/500\s+\S+\s+READY"}], "points": 10},
        {"name": "RT02(Spoke1): スポーク間 IPsec SA で暗号化カウンタ加算 (直行暗号の証明2)",
         "node": "RT02", "command": "show crypto ipsec sa peer 10.0.34.1",
         "raw": [{"regex": r"in use settings =\{Transport,"},
                 {"regex": "#pkts encaps: [1-9]"}], "points": 5},
        {"name": f"RT01: Tunnel0 が mGRE+key{v['tkey']}+protection+MTU1400+MSS1360",
         "node": "RT01", "command": "show running-config interface Tunnel0",
         "raw": [{"contains": "ip mtu 1400"}, {"contains": "ip tcp adjust-mss 1360"},
                 {"contains": "tunnel mode gre multipoint"},
                 {"contains": f"tunnel key {v['tkey']}"},
                 {"regex": r"tunnel protection ipsec profile \S+"},
                 {"contains": f"ip nhrp authentication {v['nhrp_key']}"}],
         "points": 5}]}


SYMPTOM = {
    # 全断系(登録不可): 同一症状に見えて原因層が違う=切り分けの本体
    "u1_underlay_default_missing": "all_down",
    "g2_tunnel_key_mismatch": "all_down",
    "n1_nhs_nbma_wrong": "all_down",
    "n2_nhrp_auth_mismatch": "all_down",
    "i1_psk_mismatch": "all_down",
    "i2_transform_mismatch": "all_down",
    "i4_protection_missing": "all_down",
    "i7_profile_no_transform": "all_down",
    "i8_wrong_profile_referenced": "all_down",
    # ルーティングだけ死ぬ系
    "r1_split_horizon_on": "spoke_routes_gone",
    "n4_multicast_map_tunnelip": "eigrp_unstable",
    "r2_underlay_in_eigrp": "flap_all",
    # 通るのに要件不達系
    "g1_spoke_p2p_gre": "no_direct",
    "i3_keyring_perpeer": "no_direct",
    "p1_redirect_missing": "no_direct",
    # 監査指摘系
    "i6_mode_tunnel": "audit_mode",
}


def symptom_text(fault, victim):
    vname = {"RT02": "支店1 (RT02)", "RT03": "支店2 (RT03)"}.get(victim, "")
    kind = SYMPTOM[fault]
    if kind == "all_down":
        return (f"今朝から **{vname} が全断**している（本社へも他支店へも一切届かない）。"
                "もう一方の支店は正常に稼働している。昨夜、各拠点で機器リプレース後の"
                "設定restore作業が行われた。")
    if kind == "spoke_routes_gone":
        return ("**本社⇔支店は正常**だが、**支店1⇔支店2 の通信だけが不能**になっている。"
                "昨夜、本社ルータで設定restore作業が行われた。")
    if kind == "eigrp_unstable":
        return (f"今朝から **{vname} が不通**になっている。監視によると {vname} の"
                "**ルーティング隣接がアップとダウンを周期的に繰り返している**。"
                "VPN トンネルの登録状態は正常に見えるとの一次報告がある。"
                "昨夜、各拠点で機器リプレース後の設定restore作業が行われた。")
    if kind == "flap_all":
        return ("今朝から**全拠点間の通信が数十秒〜数分おきに切れたり戻ったりを"
                "繰り返している**。監視には VPN トンネルの UP/DOWN が周期的に記録"
                "されている。昨夜、本社ルータで設定restore作業が行われた。")
    if kind == "no_direct":
        return ("全拠点間の疎通は正常。しかし月次のセキュリティ監査で「**支店間の"
                "トラフィックが本社を経由し続けており、要件『支店間は直接かつ暗号化"
                "された経路で通信』を満たしていない**」と指摘された。")
    if kind == "audit_mode":
        return ("全拠点間の疎通は正常。しかし月次のセキュリティ監査で「**IPsec の"
                "カプセル化モードが設定仕様書と異なる状態で稼働している**」と指摘された。")
    raise SystemExit(fault)


def neutral_ticket(fault, victim):
    """--faults 2 用の中立チケット文面。solo 用 symptom_text と違い
    「もう一方の支店は正常」等の相互矛盾し得るクレームを書かない
    (症状域重複時のチケット矛盾を避ける=EGVRF 4276 の運営反省の継承)。"""
    vname = {"RT02": "支店1 (RT02)", "RT03": "支店2 (RT03)"}.get(victim, "")
    kind = SYMPTOM[fault]
    if kind == "all_down":
        return f"{vname} との通信が、確立できない、という申告がある。"
    if kind == "spoke_routes_gone":
        return ("支店間の通信が成立しない、という申告がある"
                "(本社との通信は可能とのこと)。")
    if kind == "eigrp_unstable":
        return (f"{vname} のルーティング隣接が、アップとダウンを周期的に"
                "繰り返している、と監視が記録している。")
    if kind == "no_direct":
        if victim:
            return (f"{vname} 発着の支店間トラフィックだけが、直接トンネルに"
                    "移行せずハブ経由のまま、と監視が指摘している。")
        return ("支店間トラフィックが、直接トンネルに移行せず"
                "ハブ経由のまま折り返している、と監視が指摘している。")
    if kind == "audit_mode":
        return (f"セキュリティ監査から、{vname} の暗号化転送の方式が、"
                "仕様と異なる、という指摘があった。")
    return f"{vname} に関する障害が報告されている。"


def build_task(prob_id, v, ticket_md, d):
    return f"""# 問題 {prob_id} : DMVPN (Phase 3 + IKEv2) トラブルシュート（難易度{d}）

## 状況

本社 (RT01) をハブ、支店1 (RT02)・支店2 (RT03) をスポークとする **DMVPN**
（IPsec 暗号化つき・Phase 3）が稼働している。RT04 は事業者の WAN 網（**変更禁止**）。
**昨日までは全拠点が正常に通信でき、支店間はオンデマンドの直接暗号化トンネルで
通信していた。** 本日、下記のトラブルチケットが発行された。原因を切り分けて
**設定仕様書どおりの状態へ復旧**せよ。

```
   RT01 (Hub/NHS, Lo0={LO['RT01']})
     |
   RT04 (WAN transit・変更禁止)
   /  \\
RT02    RT03 (Spokes, Lo0={LO['RT02']}/{LO['RT03']})
```

## トラブルチケット

{ticket_md}

## 設定仕様書（正常時にあるべき姿・この値が正）

| 項目 | 指定値 |
|------|--------|
| トンネル | 全拠点 `Tunnel0` 1本のみ（mGRE）・overlay **`{v['ov']}.0/24`**（ハブ`.1`/支店1`.2`/支店2`.3`） |
| GRE キー | **{v['tkey']}** / NHRP network-id **{v['netid']}** / NHRP 認証 **`{v['nhrp_key']}`** |
| フェーズ | **Phase 3**（経路はハブ向きのまま・支店間トラフィックは直接暗号化トンネルで疎通） |
| MTU / MSS | ip mtu **1400** / tcp adjust-mss **1360** |
| IKE | **IKEv2**・AES-GCM-256 / PRF SHA-384 / DH 19・PSK 全拠点共通 **`{v['psk']}`** ・DPD 30/5 on-demand |
| IPsec | ESP **AES-GCM-256**・**transport mode**・PFS group19 |
| ルーティング | EIGRP **AS {v['asn']}**（トンネル区間＋各 Loopback0） |

## 遵守事項

1. RT04（WAN 網）と underlay（物理IF の IP・/30）は変更禁止。
2. 仕様書の値・方式へ**復旧**すること（暗号の撤去や別方式への置換による「復旧」は不可）。
3. スポーク間専用トンネルの追加は禁止（`Tunnel0` 1本のみ）。
4. 原因の種類・場所は伏せている。`show dmvpn` / `show crypto ikev2 sa` /
   `show crypto ipsec sa` / `show ip nhrp nhs detail` / `show ip eigrp neighbors`
   などで**状態から**切り分けること。

## アクセス・採点

CML コンソールで各機にログイン（`SUZUKI / CCNP`）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
> 採点はコンソール収集（`access: console`）。支店間の直結は採点時に能動 ping で誘発される。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    ap.add_argument("--faults", type=int, default=1, choices=[1, 2],
                    help="故障数。2=1ルータ1故障で2箇所(BL-091・i3/r2は単独専用)")
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    v = rand_values(rnd)
    # BL-091: 全域影響の i3/r2 は複合に混ぜない(症状が他故障を覆い隠す)
    COMBO_EXCLUDED = BOTH_SPOKE_FAULTS | {"r2_underlay_in_eigrp"}
    if a.faults == 1:
        faults = [a.fault or rnd.choice(FAULTS)]
    else:
        if a.fault and a.fault in COMBO_EXCLUDED:
            raise SystemExit(f"--fault {a.fault} は --faults 2 では使えません(単独専用)")
        pool = [f for f in FAULTS if f not in COMBO_EXCLUDED]
        first = a.fault or rnd.choice(pool)
        second_pool = [f for f in pool if f != first]
        if first in HUB_FAULTS:      # hub 故障は最大1(犯人所有者を被らせない)
            second_pool = [f for f in second_pool if f not in HUB_FAULTS]
        faults = [first, rnd.choice(second_pool)]
    # 犯人割当: hub系=RT01 / spoke系=重複しないスポーク / i3(solo)=両スポーク代表RT02
    victims = {}
    sp = ["RT02", "RT03"]
    rnd.shuffle(sp)
    si = 0
    for f in faults:
        if f in HUB_FAULTS:
            victims[f] = "RT01"
        elif f in BOTH_SPOKE_FAULTS:
            victims[f] = "RT02"   # fix/exec の代表ノード(注入は両 spoke)
        else:
            victims[f] = sp[si]
            si += 1
    fault = faults[0]                       # 後方互換(fault.json の旧キー用)
    victim = victims.get(fault)

    prob_id = f"GEN-DMVPN-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"DMVPN Phase3+IKEv2 トラブルシュート (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["dmvpn", "nhrp", "ipsec", "ikev2", "troubleshooting", "generated"],
               "difficulty": (DIFFICULTY[faults[0]] if len(faults) == 1 else
                              min(max(DIFFICULTY[f] for f in faults) + 1, 5)),
               "topology": "generated",
               "image_family": "iosv",
               "target_nodes": ["RT01", "RT02", "RT03", "RT04"],
               "points": 100, "access": "console",
               "lab": {"links": [
                   {"a": "RT01", "a_if": 0, "b": "RT04", "b_if": 0},
                   {"a": "RT02", "a_if": 0, "b": "RT04", "b_if": 1},
                   {"a": "RT03", "a_if": 0, "b": "RT04", "b_if": 2}]}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dmvpn_ts.py) seed={a.seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/initial/RT01.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_hub(v, faults)) + "\n")
    for n in ("RT02", "RT03"):
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_spoke(n, v, faults, victims)) + "\n")
    with open(f"{pdir}/initial/RT04.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_wan()) + "\n")

    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dmvpn_ts.py) seed={a.seed}\n"
                "# 修復判定 = ENARSI-DMVPN-IPSEC-01 実機確立の 13 チェック(値差し替え)。\n"
                "# ping(sorted で show より先に実行) が直結誘発の発射を兼ねる。\n")
        yaml.safe_dump(grading := build_grading(prob_id, v), f,
                       sort_keys=False, allow_unicode=True)
    assert sum(c["points"] for c in grading["checks"]) == 100

    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"faults": faults, "victims": victims,
                   "fault": fault, "victim": victim, "values": v},
                  f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": sum((build_fix(f2, v, victims[f2]) for f2 in faults), [])},
                  f, ensure_ascii=False, indent=2)

    if len(faults) == 1:
        ticket_md = f"> {symptom_text(fault, victim)}"
    else:
        tk = [neutral_ticket(f2, victims[f2]) for f2 in faults]
        rnd.shuffle(tk)
        ticket_md = "\n".join(f"> {i + 1}. {t}" for i, t in enumerate(tk))
        ticket_md += ("\n\n> ※昨夜、各拠点で機器リプレース後の設定restore作業が"
                      "行われた。**原因は 1 か所とは限らない。**")
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(build_task(prob_id, v, ticket_md, problem["difficulty"]))
    print(f"wrote problems/{prob_id} : faults={faults} victims={victims} "
          f"ov={v['ov']}.0/24 as={v['asn']} diff={problem['difficulty']}")


if __name__ == "__main__":
    main()
