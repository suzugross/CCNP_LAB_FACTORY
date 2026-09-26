#!/usr/bin/env python3
"""DMVPN「壊滅スタート」トラブルシュート生成器(BL-208)。

本試験所感(2026-09-21)の再現: hub の `show dmvpn` が初回から空で、hub と一部の spoke に
欠落・誤りが散在し、見えている欠落を全部埋めても **ISAKMP は QM_IDLE なのに登録されない**
最後の 1 層が残る。既存 gen_dmvpn_ts.py(IKEv2・IOSv・最大 2 故障)とは別物。

盤面(IOL iol-xe 5 台・SSH 採点):
    RT01(HUB) e0/0 203.0.113.2/30   ── RT05(ISP) e0/0 .1
    RT02(SP1) e0/0 198.51.100.2/30  ── RT05 e0/1 .1
    RT03(SP2) e0/0 198.51.100.6/30  ── RT05 e0/2 .5
    RT04(SP3) e0/0 198.51.100.10/30 ── RT05 e1/0 .9
    RT05 は変更禁止(事業者網)。Lo0 8.8.8.8 = インターネット上のホスト。
    各拠点 LAN = Loopback1 10.<X>.<n>.0/24。overlay = Tunnel0 <OV>.0/24。
健全形 = IKEv1(isakmp policy AES256/SHA256/PSK/DH14・key address 0.0.0.0)
       + ESP AES256/SHA256 transport + Phase 3(redirect/shortcut) + EIGRP。

実機知見の正典 = poc/dmvpn-wreck/README.md。設計 = problems/_drafts/DMVPN-WRECK.design.md。
使い方: gen_dmvpn_wreck.py --repo . --seed <int> [--selftest]
"""
import argparse
import json
import os
import random

import yaml

import hardmode

HUB, SPOKES, ISP = "RT01", ["RT02", "RT03", "RT04"], "RT05"
ROUTERS = [HUB] + SPOKES + [ISP]
NBMA = {"RT01": "203.0.113.2", "RT02": "198.51.100.2", "RT03": "198.51.100.6",
        "RT04": "198.51.100.10"}
GW = {"RT01": "203.0.113.1", "RT02": "198.51.100.1", "RT03": "198.51.100.5",
      "RT04": "198.51.100.9"}
NUM = {"RT01": 0, "RT02": 2, "RT03": 3, "RT04": 4}
SITE = {"RT01": "本社", "RT02": "支店1", "RT03": "支店2", "RT04": "支店3"}
PROF, TS, ACL = "DMVPN-PROF", "TS-DMVPN", "EDGE-IN"       # 既定の名前(hard names で v に上書き)

# ---------------------------------------------------------------- 欠落カタログ
# id: (対象, 説明)。対象= hub / spoke。説明は solution 用(問題文には出さない)。
WRECK = {
    "h_prof":   ("hub", "ipsec profile 未定義(→ tunnel protection も無い)"),
    "h_prot":   ("hub", "tunnel protection 欠落(profile は定義済み)"),
    "h_netid":  ("hub", "ip nhrp network-id 欠落(NHRP が有効にならない)"),
    "h_tkey":   ("hub", "tunnel key 欠落(spoke は key あり)"),
    "h_p2p":    ("hub", "tunnel mode gre ip + tunnel destination(p2p GRE)"),
    "h_mcast":  ("hub", "ip nhrp map multicast dynamic 欠落"),
    "s_isakmp": ("spoke", "crypto isakmp key 欠落"),
    "s_prof":   ("spoke", "ipsec profile 未定義(→ tunnel protection も無い)"),
    "s_prot":   ("spoke", "tunnel protection 欠落(profile は定義済み)"),
    "s_netid":  ("spoke", "ip nhrp network-id 欠落"),
    "s_tkey":   ("spoke", "tunnel key 欠落"),
    # C7(--hard df): 仕様の MTU/MSS が無い(機能は外側断片化で救済される= 症状なし・仕様監査で見つける)
    "s_mtu":    ("spoke", "ip mtu 1400 / ip tcp adjust-mss 1360 欠落(症状なし・仕様との差分)"),
}
EXCLUSIVE = [{"h_prof", "h_prot"}, {"s_prof", "s_prot"}]

# 最後の 1 層(見えている欠落を全部埋めても ISAKMP QM_IDLE・hub の show dmvpn 空が残る)。
# ★PoC(poc/dmvpn-wreck・IOL 17.15・IKEv1)で成立を実測したものだけ。hub 側 or 全 spoke に入れる
#   (hub に 1 台も上がらない状態にするため)。値: (説明, 排他となる欠落 id, spoke の State 指紋)
FINAL = {
    "f_nhs_static": ("全 spoke が旧来 3 行構文で nhs の行だけ欠落(map/map multicast はある)。"
                     "spoke に hub が static で見えるが登録要求を送らない", set(), "NHRP"),
    "f_tkey_typo":  ("hub の tunnel key の値が仕様と違う(写し間違い)。ログに痕跡なし",
                     {"h_tkey"}, "NHRP"),
    "f_esp_acl":    ("hub の外側 ACL EDGE-IN に permit esp が無い(UDP 500/4500 は許可)。"
                     "hub の encaps/decaps が両方 0", set(), "NHRP"),
    "f_pfs":        ("hub の ipsec profile にだけ set pfs group14(仕様は PFS なし)。"
                     "Phase 2 不成立", {"h_prof"}, "IPSEC"),
    "f_mode_tunnel": ("hub の transform-set が mode tunnel(仕様は transport)。"
                      "IOL・IKEv1 では Phase 2 不成立(IOSv・IKEv2 の合意して動く挙動とは違う)",
                      set(), "IPSEC"),
    "f_auth_typo":  ("hub の NHRP 認証文字列が仕様と違う。hub に wrong authentication string のログ",
                     set(), "NHRP"),
    # ★BL-210 スーパーハード(--hard acl_wall)専用: 通常の抽選には入らない
    "f_acl_wall":   ("hub 外側のうんざり ACL(40〜70 行)に ESP の欠陥(BL-210・hardmode.edge_wall)。"
                     "既存行を消さず正しい位置に 1 行挿入するのが正解", set(), "NHRP"),
}
HARD_COMPONENTS = ("acl_wall", "names", "decoys", "noise", "ticket", "df")   # C1 / C2 / C3 / C5 / C6 / C7


def rand_values(rnd):
    words = ["HONSHA", "SECNET", "WANSEC", "OVLNET", "BRANCH", "CRYPTD", "NHRPKY"]
    return {
        "ov": f"172.{rnd.randint(16, 31)}.{rnd.randint(0, 254)}",
        "lanx": rnd.randint(20, 99),
        "asn": rnd.randint(100, 899),
        "tkey": rnd.randint(100, 9999),
        "netid": rnd.randint(1, 999),
        "nhrp_key": f"{rnd.choice(words)}{rnd.randint(10, 99)}",   # ★8 文字以内
        # ★既定は打ちやすい(大文字英数のみ)。大小混在・記号・紛らわしい字はスーパーハードの
        #   コンポーネント(BL-211 hostile_names)で入れる= 本試験の「打ちづらい識別子」は opt-in
        #   ★乱数の消費回数は旧形式(randint 1 回)と同じにして、E2E 済 seed の配置を変えない
        "psk": (lambda n: f"{['VPNKEY', 'WANKEY', 'SECKEY', 'HUBKEY'][n % 4]}{n}")(rnd.randint(1000, 9999)),
        "prof": PROF, "ts": TS, "acl": ACL,
    }


def typo(k):
    """同じ長さの写し間違い(末尾 2 文字の入れ替え・同じなら 1 文字差し替え)。"""
    a, b = k[-2], k[-1]
    return k[:-2] + (b + a if a != b else a + ("7" if b != "7" else "3"))


def tip(v, n):
    return f"{v['ov']}.{1 if n == HUB else NUM[n]}"


def lan(v, n):
    return f"10.{v['lanx']}.{NUM[n]}"


# 切り分けの手がかり(PoC 実測・poc/dmvpn-wreck/README.md)。採点後の解説用(solution/README.md)。
FINGERPRINT = {
    "h_prof": "hub に ISAKMP SA が 1 本も無い・spoke の State= IKE",
    "h_prot": "hub に ISAKMP SA が 1 本も無い・spoke の State= IKE",
    "h_netid": "ISAKMP QM_IDLE・hub の ESP は decaps だけ増え encaps 0・spoke の State= NHRP・"
               "hub ログ %DMVPN-5-NHRP_NETID_UNCONFIGURED",
    "h_tkey": "ISAKMP QM_IDLE・hub の ESP は decaps だけ増え encaps 0・spoke の State= NHRP・ログに痕跡なし",
    "h_p2p": "hub の show dmvpn に tunnel destination の相手だけが UP(never)・他は上がらない",
    "h_mcast": "登録は成立する。EIGRP の隣接が spoke 側で張れない(ルーティング層の欠落)",
    "s_isakmp": "その spoke だけ ISAKMP SA が無い・State= IKE",
    "s_prof": "hub ログ %CRYPTO-4-RECVD_PKT_NOT_IPSEC … src_addr=<その spoke> prot=47(約 1 分おき)・State= NHRP",
    "s_prot": "hub ログ %CRYPTO-4-RECVD_PKT_NOT_IPSEC … src_addr=<その spoke> prot=47(約 1 分おき)・State= NHRP",
    "s_netid": "その spoke の show dmvpn 自体が空・show ip nhrp nhs detail も空・ISAKMP SA も無い",
    "s_tkey": "その spoke だけ ISAKMP QM_IDLE・hub の該当 SA は decaps のみ・State= NHRP・痕跡なし",
    "s_mtu": "症状なし(1400B DF の ping も外側の断片化で通る)。`show run interface Tunnel0` の仕様突き合わせだけで見つける",
    "f_nhs_static": "spoke に hub が正しい IP で `NHRP never S`・show ip nhrp nhs detail が空(登録要求を送っていない)・"
                    "hub は Type:Unknown で UNKNOWN … IKE never IX・hub ログ NHRP Encap Error … (7)",
    "f_tkey_typo": "ISAKMP QM_IDLE・hub の ESP は decaps だけ・spoke の State= NHRP・ログに痕跡なし(値の突き合わせのみ)",
    "f_esp_acl": "ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・EDGE-IN の deny カウンタが増える",
    "f_pfs": "ISAKMP QM_IDLE・IPsec SA が 1 つも無い・spoke の State= IPSEC・ログなし",
    "f_mode_tunnel": "ISAKMP QM_IDLE・IPsec SA が 1 つも無い・spoke の State= IPSEC・ログなし"
                     "(IOSv・IKEv2 では合意して動いたが IOL・IKEv1 では不成立)",
    "f_auth_typo": "hub ログ %DMVPN-3-DMVPN_NHRP_ERROR … wrong authentication string … (11)・hub に UNKNOWN … IX",
    "f_acl_wall": "ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・"
                  "hub ログ %SEC-6-IPACCESSLOGNP: list EDGE-IN denied 50 <spoke> -> <hub>(欠陥の種類によらず同じ)",
}


# ---------------------------------------------------------------- 構成描画
def crypto(v, broken, final=None, hub=False):
    L = ["crypto isakmp policy 10", " encryption aes 256", " hash sha256",
         " authentication pre-share", " group 14", "!"]
    if "s_isakmp" not in broken:
        L += [f"crypto isakmp key {v['psk']} address 0.0.0.0", "!"]
    mode = " mode tunnel" if (hub and final == "f_mode_tunnel") else " mode transport"
    L += [f"crypto ipsec transform-set {v['ts']} esp-aes 256 esp-sha256-hmac", mode, "!"]
    if not ({"h_prof", "s_prof"} & broken):
        L += [f"crypto ipsec profile {v['prof']}", f" set transform-set {v['ts']}"]
        if hub and final == "f_pfs":
            L.append(" set pfs group14")
        L.append("!")
    return L


def edge_acl(v, final):
    """hub の外側の保護(常設)。f_esp_acl では permit esp が無い。"""
    L = [f"ip access-list extended {v['acl']}",
         f" permit udp any host {NBMA[HUB]} eq isakmp",
         f" permit udp any host {NBMA[HUB]} eq non500-isakmp"]
    if final != "f_esp_acl":
        L.append(f" permit esp any host {NBMA[HUB]}")
    L += [" permit icmp any any", " deny   ip any any", "!"]
    return L


def render(n, v, broken, final=None, walls=None):
    """1 台分の initial/*.cfg.j2。broken= そのノードに入れる欠落 id の集合。walls= {node: Wall}(hard)。"""
    if n == ISP:
        return ["! RT05 (ISP) ★変更禁止★",
                "interface Loopback0", " ip address 8.8.8.8 255.255.255.255", "!",
                "interface {{ links[0] }}", " description === to HQ ===",
                " ip address 203.0.113.1 255.255.255.252", " no shutdown", "!",
                "interface {{ links[1] }}", " description === to BRANCH1 ===",
                " ip address 198.51.100.1 255.255.255.252", " no shutdown", "!",
                "interface {{ links[2] }}", " description === to BRANCH2 ===",
                " ip address 198.51.100.5 255.255.255.252", " no shutdown", "!",
                "interface {{ links[4] }}", " description === to BRANCH3 ===",
                " ip address 198.51.100.9 255.255.255.252", " no shutdown", "!"]
    hub = n == HUB
    L = [f"! {n} ({SITE[n]})",
         "interface Loopback1", f" ip address {lan(v, n)}.1 255.255.255.0", "!"]
    wall = (walls or {}).get(n)
    if wall:
        L += hardmode.wall_cfg(wall)
    elif hub:
        L += edge_acl(v, final)
    L += ["interface {{ links[0] }}", " description === to ISP ===",
          f" ip address {NBMA[n]} 255.255.255.252"]
    if wall:
        L.append(hardmode.wall_apply(wall))
    elif hub:
        L.append(f" ip access-group {v['acl']} in")
    L += [" no shutdown", "!", f"ip route 0.0.0.0 0.0.0.0 {GW[n]}", "!"]
    L += crypto(v, broken, final, hub)
    if v.get("decoys"):
        L += v["decoys"]
    if v.get("noise"):
        L += v["noise"][n]
    t = ["interface Tunnel0", f" ip address {tip(v, n)} 255.255.255.0", " no ip redirects"]
    if "s_mtu" not in broken:
        t += [" ip mtu 1400", " ip tcp adjust-mss 1360"]
    t += [
         f" ip nhrp authentication {typo(v['nhrp_key']) if hub and final == 'f_auth_typo' else v['nhrp_key']}"]
    if not ({"h_netid", "s_netid"} & broken):
        t.append(f" ip nhrp network-id {v['netid']}")
    if n == HUB:
        # ★IOL は map multicast dynamic が既定 ON(外すには no 形を明示する)
        t.append(" no ip nhrp map multicast dynamic" if "h_mcast" in broken
                 else " ip nhrp map multicast dynamic")
        t += [" ip nhrp redirect", f" no ip split-horizon eigrp {v['asn']}"]
    else:
        if final == "f_nhs_static":
            # 旧来 3 行構文から nhs の行だけ抜けた形(spoke に hub が static で見える)
            t += [f" ip nhrp map {tip(v, HUB)} {NBMA[HUB]}",
                  f" ip nhrp map multicast {NBMA[HUB]}"]
        else:
            t.append(f" ip nhrp nhs {tip(v, HUB)} nbma {NBMA[HUB]} multicast")
        t.append(" ip nhrp shortcut")
    t.append(" tunnel source {{ links[0] }}")
    if "h_p2p" in broken:
        t.append(f" tunnel destination {v['p2p_dst']}")      # mode は gre ip(既定)
    else:
        t.append(" tunnel mode gre multipoint")
    if not ({"h_tkey", "s_tkey"} & broken):
        key = v["tkey_typo"] if (hub and final == "f_tkey_typo") else v["tkey"]
        t.append(f" tunnel key {key}")
    if not ({"h_prof", "h_prot", "s_prof", "s_prot"} & broken):
        t.append(f" tunnel protection ipsec profile {v['prof']}")
    # ★eigrp router-id を明示(C5 ノイズの Loopback が最大 IP になって RID を奪い、全拠点で RID 重複→経路が
    #   捨てられる事故を E2E で発見)。仕様= RID はトンネル IP
    L += t + ["!", f"router eigrp {v['asn']}", f" eigrp router-id {tip(v, n)}",
              f" network {v['ov']}.0 0.0.0.255",
              f" network {lan(v, n)}.0 0.0.0.255", "!"]
    return L


TU = ["interface Tunnel0"]


def _e(parents, lines):
    """fix_generated.yml 形式のエントリ(parents 無し=グローバル)。match none= diff せず無条件投入。"""
    e = {"lines": lines, "match": "none"}
    if parents:
        e["parents"] = parents
    return e


def fix_lines(item, v, n):
    """欠落 1 件の是正 → fix エントリのリスト。"""
    prof = [_e([f"crypto ipsec profile {v['prof']}"], [f"set transform-set {v['ts']}"])]
    prot = [_e(TU, [f"tunnel protection ipsec profile {v['prof']}", "no shutdown"])]
    return {
        "h_prof": prof + prot, "s_prof": prof + prot,
        "h_prot": prot, "s_prot": prot,
        "h_netid": [_e(TU, [f"ip nhrp network-id {v['netid']}"])],
        "s_netid": [_e(TU, [f"ip nhrp network-id {v['netid']}"])],
        "h_tkey": [_e(TU, [f"tunnel key {v['tkey']}"])],
        "s_tkey": [_e(TU, [f"tunnel key {v['tkey']}"])],
        "h_p2p": [_e(TU, ["no tunnel destination", "tunnel mode gre multipoint"])],
        "h_mcast": [_e(TU, ["ip nhrp map multicast dynamic"])],
        "s_isakmp": [_e(None, [f"crypto isakmp key {v['psk']} address 0.0.0.0"])],
        "s_mtu": [_e(TU, ["ip mtu 1400", "ip tcp adjust-mss 1360"])],
    }[item]


def final_fixes(final, v):
    if final == "f_nhs_static":
        return [dict(_e(TU, [f"ip nhrp nhs {tip(v, HUB)}"]), node=s) for s in SPOKES]
    e = {
        "f_tkey_typo": [_e(TU, [f"tunnel key {v['tkey']}"])],
        "f_esp_acl": [_e([f"ip access-list extended {v['acl']}"],
                         [f"15 permit esp any host {NBMA[HUB]}"])],
        "f_pfs": [_e([f"crypto ipsec profile {v['prof']}"], ["no set pfs"])],
        "f_mode_tunnel": [_e([f"crypto ipsec transform-set {v['ts']} esp-aes 256 esp-sha256-hmac"],
                             ["mode transport"])],
        "f_auth_typo": [_e(TU, [f"ip nhrp authentication {v['nhrp_key']}"])],
    }[final]
    return [dict(x, node=HUB) for x in e]


def false_memo(rnd, place):
    """C6(BL-211): 前任者の引き継ぎメモ。3 項目のうち 1 つだけ事実と違う(盤面から確定できる)。
    戻り値= (行のリスト, 偽の項目の index, 根拠)。"""
    broken_spokes = [s_ for s_ in SPOKES if place.get(s_)]
    ok_claims = [
        (f"{ISP} 側(事業者)のフィルタは、事業者に確認済み(問題なし)", None),
        ("各拠点の外側のアドレスと既定のルートは、仕様どおり投入済み", None),
        ("IKE のポリシーは、全拠点で同じ値を投入済み", None),
    ]
    false_cands = []
    for s_ in broken_spokes:
        false_cands.append((f"{SITE[s_]}({s_})の Tunnel0 と暗号の設定は、完了して確認済み",
                            f"{s_} には欠落 {sorted(place[s_])} がある"))
    if "h_p2p" in place[HUB]:
        false_cands.append((f"{HUB} の Tunnel0 は、mGRE(multipoint)として投入済み",
                            "hub の Tunnel0 は tunnel destination 付きの p2p GRE のまま"))
    if {"h_prof", "h_prot"} & place[HUB]:
        false_cands.append((f"{HUB} のトンネル保護(tunnel protection)は、投入済み", "hub に tunnel protection が無い"))
    if not false_cands:
        false_cands.append((f"{HUB} の Tunnel0 の NHRP の設定は、仕様どおり投入済み", "hub の Tunnel0 に欠落がある"))
    f_text, why = rnd.choice(false_cands)
    claims = rnd.sample(ok_claims, 2) + [(f_text, why)]
    rnd.shuffle(claims)
    idx = [i for i, c in enumerate(claims) if c[1]][0]
    return [c[0] for c in claims], idx, why


def decoy_lines(rnd, v):
    """C3(BL-211): 使われていない似た名前のオブジェクト(全拠点共通)。1 つは本物と等価・1 つは方式違い。
    参照は本物の名前だけ(仕様書に名前あり)。囮を消しても消さなくてもよい。"""
    p1, p2 = hardmode.similar_names(rnd, v["prof"], 2)
    t1, = hardmode.similar_names(rnd, v["ts"], 1)
    a1, = hardmode.similar_names(rnd, v["acl"], 1)
    return [f"crypto ipsec transform-set {t1} esp-aes esp-sha-hmac", " mode tunnel", "!",
            f"crypto ipsec profile {p1}", f" set transform-set {t1}", " set pfs group14", "!",
            f"crypto ipsec profile {p2}", f" set transform-set {v['ts']}",
            " set security-association lifetime seconds 3600", "!",
            f"ip access-list extended {a1}", " permit udp any any eq isakmp", " permit esp any any",
            " permit gre any any", " permit icmp any any", " permit ip any any", "!"]


# ---------------------------------------------------------------- 抽選
def draw(rnd):
    """欠落の配置 {node: set(id)}。hub 3〜4・spoke 各 1〜2・合計 6〜8。
    ★少なくとも 1 台の spoke は isakmp key 欠落、少なくとも 1 台の spoke は無傷でない。"""
    hub_pool = [k for k, (t, _) in WRECK.items() if t == "hub"]
    sp_pool = [k for k, (t, _) in WRECK.items() if t == "spoke" and k != "s_mtu"]
    while True:
        place = {HUB: set(rnd.sample(hub_pool, rnd.randint(3, 4)))}
        for s in SPOKES:
            place[s] = set(rnd.sample(sp_pool, rnd.randint(1, 2)))
        if any(len(ex & place[n]) > 1 for n in place for ex in EXCLUSIVE):
            continue
        if not any("s_isakmp" in place[s] for s in SPOKES):
            continue
        # 全 spoke が同じ欠落だけ、という単調な盤面は避ける
        if len({frozenset(place[s]) for s in SPOKES}) < 2:
            continue
        total = sum(len(x) for x in place.values())
        if 6 <= total <= 8:
            return place


# ---------------------------------------------------------------- 採点
def grading(prob_id, v, walls=None):
    esc = lambda s: s.replace(".", r"\.")
    up = lambda s: {"regex": rf"{esc(NBMA[s])}\s+{esc(tip(v, s))}\s+UP\s+\S+\s+D(?!\w)"}
    checks = [
        {"name": "RT01(HUB): 3 拠点の spoke が登録され UP", "node": HUB,
         "command": "show dmvpn", "raw": [{"contains": "Type:Hub"}] + [up(s) for s in SPOKES],
         "points": 20 if walls else 25},
        {"name": "RT01(HUB): 3 拠点との ISAKMP SA が QM_IDLE", "node": HUB,
         "command": "show crypto isakmp sa",
         "raw": [{"regex": rf"{esc(NBMA[HUB])}\s+{esc(NBMA[s])}\s+QM_IDLE"} for s in SPOKES],
         "points": 10},
        {"name": "RT01(HUB): ESP が transport で暗号化・復号カウンタが加算", "node": HUB,
         "command": "show crypto ipsec sa",
         "raw": [{"regex": r"in use settings =\{Transport,"}, {"not_contains": "={Tunnel,"},
                 {"regex": "#pkts encaps: [1-9]"}, {"regex": "#pkts decaps: [1-9]"}],
         "points": 7 if walls else 10},
        {"name": "RT01(HUB): EIGRP 隣接が 3 拠点と確立", "node": HUB,
         "command": "show ip eigrp neighbors",
         # ★Q Cnt 0 まで見る(未登録でも hub は hello を受けて表に載せる= Q 1・RTO 5000 の片側隣接。E2E で発見)
         "raw": [{"regex": rf"{esc(tip(v, s))}\s+Tu0\s+\d+\s+\S+\s+\d+\s+\d+\s+0\s+\d+"}
                 for s in SPOKES], "points": 10},
        {"name": "RT02(支店1): 支店2 の LAN へ到達(能動・直結誘発)", "node": "RT02",
         "command": f"ping {lan(v, 'RT03')}.1 source Loopback1 repeat 5",
         "raw": [{"regex": "Success rate is [1-9]"}], "points": 5},
        {"name": "RT03(支店2): 支店3 の LAN へ到達(能動・直結誘発)", "node": "RT03",
         "command": f"ping {lan(v, 'RT04')}.1 source Loopback1 repeat 5",
         "raw": [{"regex": "Success rate is [1-9]"}], "points": 5},
        {"name": "RT04(支店3): 本社の LAN へ到達", "node": "RT04",
         "command": f"ping {lan(v, HUB)}.1 source Loopback1 repeat 5",
         "raw": [{"regex": "Success rate is [1-9]"}], "points": 5},
        {"name": "RT02(支店1): 支店2 への直接トンネル(Phase 3 shortcut)が UP", "node": "RT02",
         "command": "show dmvpn",
         "raw": [{"regex": rf"{esc(NBMA['RT03'])}\s+{esc(tip(v, 'RT03'))}\s+UP\s+\S+\s+DT"}],
         "points": 10},
        {"name": "RT01(HUB): Tunnel0 が仕様どおり(mGRE・key・network-id・protection)",
         "node": HUB, "command": "show running-config interface Tunnel0",
         "raw": [{"contains": "tunnel mode gre multipoint"},
                 {"not_contains": "tunnel destination"},
                 {"contains": "ip mtu 1400"}, {"contains": "ip tcp adjust-mss 1360"},
                 {"contains": f"tunnel key {v['tkey']}"},
                 {"contains": f"ip nhrp network-id {v['netid']}"},
                 {"contains": f"tunnel protection ipsec profile {v['prof']}"},
                 {"not_contains": "no ip nhrp map multicast dynamic"}],
         "points": 8},
        {"name": f"RT01(HUB): 外側の保護 {v['acl']} が適用されたまま・不要な通信は拒否", "node": HUB,
         "command": "show running-config interface Ethernet0/0",
         "raw": [{"contains": f"ip access-group {v['acl']} in"}], "points": 2},
    ]
    for s, pts in zip(SPOKES, (4, 3, 3)):
        checks.append(
            {"name": f"{s}({SITE[s]}): Tunnel0 が仕様どおり(key・network-id・protection)",
             "node": s, "command": "show running-config interface Tunnel0",
             "raw": [{"contains": f"tunnel key {v['tkey']}"},
                     {"contains": "ip mtu 1400"}, {"contains": "ip tcp adjust-mss 1360"},
                     {"contains": f"ip nhrp network-id {v['netid']}"},
                     {"contains": f"tunnel protection ipsec profile {v['prof']}"}],
             "points": pts})
    if walls:
        checks.append(hardmode.wall_check(
            walls[HUB], HUB, 8, name=f"RT01(HUB): {v['acl']} が保全され(削除・置換なし)、必要な通信だけが追加で許可されている"))
    assert sum(c["points"] for c in checks) == 100
    return {"problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"}, "checks": checks}


# ---------------------------------------------------------------- 問題文
def task_md(prob_id, v, walls=None):
    edge_row = (hardmode.wall_task_row(walls[HUB], spokes_too=len(walls) > 1) if walls else
                f"| 本社の外側の保護 | 外側のインターフェイスの着信に、アクセス リスト `{v['acl']}`(IKE・IPsec・ICMP のみを許可)を適用 |")
    rows = "\n".join(f"| {SITE[n]} | {n} | `{NBMA[n]}` | `{tip(v, n)}` | `{lan(v, n)}.0/24` |"
                     for n in [HUB] + SPOKES)
    memo = ""
    if v.get("ticket"):
        lines_, _, _ = v["ticket"]
        memo = ("## 前任者の引き継ぎメモ\n\n"
                + "\n".join(f"- {x}" for x in lines_)
                + "\n\n> メモは前任者の記憶によるものであり、正確であるとは限りません。\n\n")
    return f"""# 問題 {prob_id}

## シナリオ

本社の {HUB} をハブとし、3 つの支店のルータをスポークとするところの DMVPN が、新規に導入されている途中です。導入を担当していた前任者が構成を途中まで投入したところで、作業は引き継がれました。{HUB} において `show dmvpn` が実行されたところ、スポークは 1 つも表示されていません。{ISP} は事業者のルータであり、あなたの管理の外にあります。

あなたのタスクは、下記の設定仕様書のとおりにすべての拠点が DMVPN によって接続され、そして、支店の間の通信が、ハブを経由することなく、直接に暗号化されたトンネルによって行われることを、確実にすることです。

```
            RT05 (ISP) ─ Lo0 8.8.8.8
      ┌────────┼────────┬────────┐
    RT01      RT02     RT03     RT04
   (本社)    (支店1)  (支店2)  (支店3)
```

| 拠点 | ルータ | 外側のアドレス(NBMA) | トンネルのアドレス | LAN(Loopback1) |
|---|---|---|---|---|
{rows}

{memo}## 設定仕様書

| 項目 | 指定値 |
|---|---|
| トンネル | 全拠点 `Tunnel0` 1 本(mGRE)・`{v['ov']}.0/24`・送信元は ISP の側のインターフェイス |
| GRE の key | {v['tkey']} |
| NHRP | network-id {v['netid']}・認証 `{v['nhrp_key']}`・Phase 3(ハブ= redirect / スポーク= shortcut) |
| IKE | IKEv1・AES 256 / SHA-256 / DH group 14・事前共有鍵 `{v['psk']}`(全拠点共通・相手のアドレスを限定しない) |
| IPsec | ESP AES 256 / SHA-256 HMAC・transport mode・PFS なし・ipsec profile によるトンネルの保護 |
| 名前 | transform-set `{v['ts']}`・ipsec profile `{v['prof']}`(すべての拠点で同一の名前) |
{edge_row}
| MTU / MSS | ip mtu 1400 / ip tcp adjust-mss 1360 |
| ルーティング | EIGRP AS {v['asn']}(トンネルのネットワーク + 各拠点の LAN) |

## 遵守事項

1. {ISP} の構成は、変更することができません。各ルータの外側のインターフェイスのアドレスおよび既定のルートは、変更されてはなりません。本社の外側の保護は、取り外されてはなりません。
2. 仕様書の値および方式によって、構成されなければなりません。暗号化の撤去、または、別の方式への置き換えによる接続は、認められていません。
3. スポークの間の専用のトンネルを追加してはなりません。

## アクセス・採点

SSH で各機にログイン(`SUZUKI / CCNP`・mgmt IP は出題時に提示)。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""


# ---------------------------------------------------------------- main
def build(seed, hard=()):
    rnd = random.Random(seed)
    v = rand_values(rnd)
    place = draw(rnd)
    if "names" in hard:
        v.update(hardmode.hostile_names(random.Random(seed ^ 0xC2)))     # C2: 別系列の乱数
    if "decoys" in hard:
        v["decoys"] = decoy_lines(random.Random(seed ^ 0xC3), v)           # C3
    if "noise" in hard:
        r5 = random.Random(seed ^ 0xC5)
        v["noise"] = {n: hardmode.noise_lines(r5, node_idx=i) for i, n in enumerate([HUB] + SPOKES)}   # C5
    if "df" in hard:
        r7 = random.Random(seed ^ 0xC7)
        for s_ in r7.sample(SPOKES, r7.randint(1, 2)):                     # C7: 1〜2 spoke の MTU/MSS 欠落
            place[s_].add("s_mtu")
    if "ticket" in hard:
        v["ticket"] = false_memo(random.Random(seed ^ 0xC6), place)         # C6
    v["p2p_dst"] = NBMA[rnd.choice(SPOKES)]
    v["tkey_typo"] = int(str(v["tkey"])[::-1]) if str(v["tkey"]) != str(v["tkey"])[::-1] \
        else v["tkey"] + 10
    final = rnd.choice([f for f in sorted(FINAL) if f != "f_acl_wall"
                        and not (FINAL[f][1] & place[HUB])])
    walls = None
    if "acl_wall" in hard:
        # ★壁は別系列の乱数(同じ seed の通常版と欠落配置が同じ= 比較・再演がしやすい)
        r2 = random.Random(seed ^ 0xAC1)
        final = "f_acl_wall"
        w_in = hardmode.edge_wall(r2, name=v["acl"], protect_ip=NBMA[HUB], gw_ip=GW[HUB],
                                  peers=[NBMA[s_] for s_ in SPOKES], target=("esp", None),
                                  needs=(("udp", 500), ("udp", 4500)))
        walls = {HUB: w_in}
        if w_in.side == "both":
            # ★IOL は out 側 ACL が ARP を壊す(hardmode.py 冒頭)→ 囮は全 spoke の外側 in
            for s_ in SPOKES:
                walls[s_] = hardmode.spoke_wall(
                    r2, name=v["acl"], protect_ip=NBMA[s_], gw_ip=GW[s_],
                    peers=[NBMA[x] for x in [HUB] + SPOKES if x != s_])
    cfgs = {n: render(n, v, place.get(n, set()), final, walls) for n in ROUTERS}
    fixes = []
    for n in [HUB] + SPOKES:
        for item in sorted(place.get(n, set())):
            fixes += [dict(e, node=n) for e in fix_lines(item, v, n)]
    fixes += hardmode.wall_fix(walls[HUB], HUB) if walls else final_fixes(final, v)
    # 保険(PoC P2: 是正だけで 41 秒で登録される。bounce/clear は無くても採点に影響しない)
    for n in [HUB] + SPOKES:
        fixes.append(dict(_e(TU, ["no shutdown"]), node=n))
        fixes.append({"node": n, "exec": ["clear crypto session", "clear ip nhrp"]})
    return v, place, final, cfgs, fixes, walls


def write(repo, seed, hard=()):
    v, place, final, cfgs, fixes, walls = build(seed, hard)
    hard = tuple(hard)
    prob_id = f"GEN-DMVPNW-{seed}"
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id, "title": f"DMVPN 引き継ぎ構築トラブルシュート (seed={seed})",
               "exam": "ENARSI",
               "topics": ["dmvpn", "nhrp", "ipsec", "ikev1", "troubleshooting", "generated"],
               "difficulty": 5 + len(hard), "topology": "generated", "image_family": "iol",
               "target_nodes": ROUTERS, "points": 100, "access": "ssh",
               "lab": {"links": [
                   {"a": HUB, "a_if": 0, "b": ISP, "b_if": 0},
                   {"a": "RT02", "a_if": 0, "b": ISP, "b_if": 1},
                   {"a": "RT03", "a_if": 0, "b": ISP, "b_if": 2},
                   {"a": "RT04", "a_if": 0, "b": ISP, "b_if": 4}],
                   "positions": {"RT05": [0, -250], "RT01": [-450, 100], "RT02": [-150, 100],
                                 "RT03": [150, 100], "RT04": [450, 100]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dmvpn_wreck.py) seed={seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for n in ROUTERS:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(cfgs[n]) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dmvpn_wreck.py) seed={seed}\n")
        yaml.safe_dump(grading(prob_id, v, walls), f, sort_keys=False, allow_unicode=True)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task_md(prob_id, v, walls))
    json.dump({"place": {n: sorted(x) for n, x in place.items()}, "final": final,
               "hard": list(hard),
               "wall": ({"defect": walls[HUB].defect, "gaps": walls[HUB].gaps, "side": walls[HUB].side,
                         "n_entries": walls[HUB].n_entries} if walls else None),
               "values": v}, open(f"{pdir}/solution/fault.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"fixes": fixes}, open(f"{pdir}/solution/fix.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/README.md", "w", encoding="utf-8") as f:
        f.write(f"# 採点者専用 ({prob_id})\n\n")
        for n in [HUB] + SPOKES:
            for item in sorted(place.get(n, set())):
                f.write(f"- {n}: `{item}` — {WRECK[item][1]}\n  - 見え方: {FINGERPRINT[item]}\n")
        f.write(f"- 最後の 1 層: `{final}` — {FINAL[final][0]}(spoke の State= {FINAL[final][2]})\n"
                f"  - 見え方: {FINGERPRINT[final]}\n"
                + ("".join(hardmode.wall_readme(w) for w in walls.values()) if walls else "")
                + (f"- C2 打ちづらい名前: profile `{v['prof']}` / transform-set `{v['ts']}` / ACL `{v['acl']}` / "
                   f"PSK `{v['psk']}` / NHRP `{v['nhrp_key']}`(すべて仕様書に明記・大小区別あり)\n" if "names" in hard else "")
                + ("- C3 囮: 似た名前の未使用 profile 2(1 つは mode tunnel+PFS・1 つは本物と等価)・transform-set 1・"
                   "ACL 1(permit any)。参照を囮に付け替えると仕様の名前チェックで落ちる\n" if "decoys" in hard else "")
                + ("- C5 ノイズ: 各拠点に無害な設定 120 行前後(LEGACY Loopback・QoS・Null0 静的・未使用 ACL/route-map/IP SLA)\n"
                   if "noise" in hard else "")
                + (f"- C6 メモ: 偽の項目= {v['ticket'][1] + 1} 番目「{v['ticket'][0][v['ticket'][1]]}」({v['ticket'][2]})\n"
                   if v.get("ticket") else "")
                + ("- C7 df: MTU/MSS 欠落の spoke= " + ", ".join(s_ for s_ in SPOKES if "s_mtu" in place[s_])
                   + "(症状なし・仕様監査)\n" if "df" in hard else "")
                + "\n"
                "## 切り分けの軸(解説用)\n\n"
                "- spoke の State: IKE= Phase 1 未成立 / IPSEC= Phase 2 未成立 / NHRP= 暗号は通過・NHRP 段階\n"
                "- NHRP 段階は hub の `show crypto ipsec sa`: decaps だけ増える= hub が受けて返事をしない"
                "(network-id・key・auth・nhs)/ 両方 0= ESP が届いていない(ACL)\n"
                "- `show ip nhrp nhs detail` が空= spoke が登録要求を送っていない(nhs 行の欠落)\n"
                "- ★IOL の罠(本問の初期状態では起きない): 稼働中の hub で network-id を外して付け直すと "
                "`ip nhrp redirect` が表示されたまま無効になり、Phase 3 の直接トンネルだけができない。"
                "`ip nhrp redirect` を再入力すれば直る\n\n"
                "fix は solution/fix.json(最後の no shutdown + clear は保険。PoC P2= 是正だけで 41 秒で登録)。\n")
    print(f"wrote {prob_id}: place={ {n: sorted(x) for n, x in place.items()} } final={final}")


def selftest():
    n, finals = 0, {}
    hw = {}
    for seed in range(200):
        v, place, final, cfgs, fixes, walls = build(seed, ("acl_wall",))
        assert final == "f_acl_wall" and walls and walls[HUB].n_entries >= 40
        hub = "\n".join(cfgs[HUB])
        assert "ip access-list extended EDGE-IN" in hub and "ip access-group EDGE-IN in" in hub
        assert "EDGE-OUT" not in hub
        for s_ in SPOKES:
            assert ("ip access-list extended EDGE-IN" in "\n".join(cfgs[s_])) == (walls[HUB].side == "both")
        assert any("resequence" in l for f_ in fixes for l in f_.get("lines", [])) == (walls[HUB].gaps == "packed")
        g = grading("X", v, walls)
        assert any("acl_vectors" in c for c in g["checks"])
        # 通常版と欠落配置が同じ
        assert build(seed)[1] == place
        hw[walls[HUB].defect] = hw.get(walls[HUB].defect, 0) + 1
    for seed in range(100):
        v, place, final, cfgs, fixes, walls = build(seed, HARD_COMPONENTS)
        assert any("s_mtu" in place[s_] for s_ in SPOKES) and v.get("ticket") and v.get("noise")
        for s_ in SPOKES:
            c = "\n".join(cfgs[s_])
            assert ("ip mtu 1400" in c) == ("s_mtu" not in place[s_]), seed
            assert "interface Loopback100" in c
        assert len(v["ticket"][0]) == 3
    for seed in range(150):
        v, place, final, cfgs, fixes, walls = build(seed, ("acl_wall", "names", "decoys"))
        hub = "\n".join(cfgs[HUB])
        assert v["prof"] != PROF and (f"crypto ipsec profile {v['prof']}" in hub or "h_prof" in place[HUB]), seed
        assert f"ip access-list extended {v['acl']}" in hub and v["acl"] != ACL, seed
        assert hub.count("crypto ipsec profile ") >= 2, seed          # 囮 2(+本物・h_prof なら無い)
        assert v["prof"] not in [l.split()[-1] for l in v["decoys"] if l.startswith("crypto ipsec profile")]
        assert len(v["nhrp_key"]) == 8
        assert build(seed)[1] == place
    for seed in range(500):
        v, place, final, cfgs, fixes, walls = build(seed)
        tot = sum(len(x) for x in place.values())
        assert 6 <= tot <= 8, (seed, place)
        assert any("s_isakmp" in place[s] for s in SPOKES)
        hub = "\n".join(cfgs[HUB])
        assert ("tunnel destination" in hub) == ("h_p2p" in place[HUB])
        for s in SPOKES:
            c = "\n".join(cfgs[s])
            assert ("crypto isakmp key" in c) == ("s_isakmp" not in place[s]), seed
        assert not (FINAL[final][1] & place[HUB]), (seed, final)
        if final == "f_nhs_static":
            assert all("ip nhrp nhs" not in "\n".join(cfgs[s_]) for s_ in SPOKES)
        if final == "f_esp_acl":
            assert "permit esp" not in hub
        else:
            assert "permit esp" in hub
        finals[final] = finals.get(final, 0) + 1
        n += 1
    print(f"selftest OK: {n} seeds / final 分布 {finals} / hard acl_wall 欠陥分布 {hw} / names+decoys 150")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--hard", default="",
                    help="スーパーハード部品(カンマ区切り): acl_wall= hub 外側のうんざり ACL(BL-210) / "
                         "names= 打ちづらい名前(C2) / decoys= 囮の類似名オブジェクト(C3) / noise= 設定ノイズ(C5) / "
                         "ticket= 不正確な引き継ぎメモ(C6) / df= MTU/MSS 欠落(C7・仕様監査)。all= 全部")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if a.seed is None:
        a.seed = random.randint(10000, 99999)
    hard = tuple(x for x in a.hard.split(",") if x)
    if hard == ("all",):
        hard = HARD_COMPONENTS
    for x in hard:
        if x not in HARD_COMPONENTS:
            raise SystemExit(f"未知の --hard 部品: {x}(候補= {HARD_COMPONENTS})")
    write(a.repo, a.seed, hard)


if __name__ == "__main__":
    main()
