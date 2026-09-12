#!/usr/bin/env python3
"""IPv6 自動アドレッシング TS 生成器（BL-149・ENARSI 4.x IPv6 DHCP/SLAAC）。

設計= problems/_drafts/V6ADDR-TS.design.md / 追加 PoC= poc/v6addr/README.md（全項目実機済）。
土台トポロジは ENARSI-DHCPV6-01（4 IOL・点対点）を値ランダム化。

コア発想（GEN-RTCTL と同型）: **要件抽選で正解のアーキテクチャ（＝ラボの顔）が変わる**。
2つの LAN それぞれに「方式世界」を割り当て（相異なる2つ）、その世界に応じて
サーバプール／RA フラグ／クライアント設定の“正しい形”が変わる。故障はその健全形へ
1点注入する（--faults 2 は別レイヤから2つ）。

方式世界（P1）:
  W_SO … SLAAC + stateless DHCPv6（O フラグ）: アドレスは自動生成・DNS はサーバ配布
  W_M  … 純 stateful（M フラグ + no-autoconfig）: アドレスはサーバ管理・自動生成は禁止
  W_MA … stateful + SLAAC 併存（M フラグ・A フラグ ON）: 管理アドレスと自動生成が同居

盤面（固定・4 IOL・点対点）:
  RT01(DHCPv6 サーバ, Lo0) ──core── RT02(GW/リレー) ──LAN-A── CLA
                                              └────────LAN-B── CLB
  RT01 Et0/0 = bare `ipv6 dhcp server`（automatic・2 プール集約）。

★実機知見（poc/v6addr/README.md・iol-xe 17.15）:
  ・ra_suppress は `suppress all` 固定（素 suppress は RS 応答が生き故障が出にくい）。
    解錠は `no ... suppress all`（`no ipv6 nd ra suppress` では消えない）。
  ・ra_lifetime_zero=GUA は付くがデフォルト経路だけ消える。
  ・非 /64=RA に載るが SLAAC アドレス生成されず（完全サイレント）。
  ・acl は「明示 permit + deny 546/547」でないと RA も全断（＝IPv6 ACL の暗黙 permit は
    NS/NA のみで RS/RA は対象外）。この性質を正面から使うのが BL-160 の acl_blocks_ra
    （端末の入力フィルタに LL 発の許可行が無く RA が落ちる・層跨ぎ）。
  ・server_return_route_missing=割当は成立し到達性だけ片方向で死ぬ。
  ・採点主力= client `show ipv6 routers`（M/O/pref/lifetime/prefix/DNS 一括）
    ＋ `show ipv6 dhcp interface`（Address State OPEN / Configuration parameters）。

出力: problems/GEN-V6ADDR-<seed>/{problem.yml, initial/*.cfg.j2, task.md, grading.yml,
      solution/{fault.json, fix.json}}
使い方: gen_v6addr_ts.py --repo . --seed <int> [--board a|rogue|pd|fhs] [--fault <name>] [--faults 1|2]
board=fhs(BL-146)= ioll2 アクセス SW の RA Guard/DHCPv6 Guard TS（telnet 採点・PoC= poc/fhs/README.md）。
採点は DHCP 交換+RA 周期のラグを吸収するため max_attempts=8 settle_delay=15 を推奨。
"""
import argparse
import json
import os
import random

import yaml

# ---- 故障カタログ（レイヤ→故障） ------------------------------------------
LAYERS = {
    "ra": ["ra_suppress", "ra_lifetime_zero", "o_flag_missing",
           "a_not_suppressed", "nd_prefix_wrong_len", "rdnss_missing"],
    "server": ["server_attach_missing", "link_address_missing",
               "pool_prefix_mismatch", "dns_option_missing",
               "server_named_wrong_pool"],
    "relay": ["relay_missing", "relay_wrong_dest"],
    "client": ["ipv6_enable_missing", "client_default_missing",
               "client_static_default_missing"],
    "data": ["server_return_route_missing"],
    # BL-160: 端末側の入力フィルタ（IPv6 ACL）が制御トラフィックを巻き込む層跨ぎ故障。
    "filter": ["acl_blocks_ra"],
}
FAULTS = [f for fs in LAYERS.values() for f in fs]
LAYER_OF = {f: L for L, fs in LAYERS.items() for f in fs}

DIFFICULTY = {
    "ra_suppress": 3, "ra_lifetime_zero": 4, "o_flag_missing": 3,
    "a_not_suppressed": 4, "nd_prefix_wrong_len": 5, "rdnss_missing": 3,
    "server_attach_missing": 3, "link_address_missing": 4,
    "pool_prefix_mismatch": 4, "dns_option_missing": 3,
    "server_named_wrong_pool": 4, "relay_missing": 3, "relay_wrong_dest": 4,
    "ipv6_enable_missing": 5, "client_default_missing": 4,
    "client_static_default_missing": 5, "server_return_route_missing": 5,
    "acl_blocks_ra": 5,
}

# 世界（方式）。P2 で W_S（純 SLAAC+RDNSS）と W_MP（RA 抑止ポリシー）を追加。
WORLDS = ["W_SO", "W_M", "W_MA", "W_S", "W_MP"]
WORLD_LABEL = {
    "W_SO": "SLAAC + stateless DHCPv6（O フラグ）",
    "W_M": "純 stateful DHCPv6（M フラグ・自動生成アドレス禁止）",
    "W_MA": "stateful DHCPv6 + SLAAC 併存（M フラグ・自動生成も可）",
    "W_S": "純 SLAAC（DNS は RA の DNS オプションで配布・DHCPv6 不使用）",
    "W_MP": "RA 抑止ポリシー（stateful アドレス + 静的既定ゲートウェイ・RA は停止）",
}

# 各故障が対象にできる世界（None= 世界に依らずどの LAN でも／サーバ全体）。
SLAAC_WORLDS = {"W_SO", "W_MA", "W_S"}       # SLAAC で GUA を作る世界
STATEFUL_WORLDS = {"W_M", "W_MA", "W_MP"}    # ipv6 address dhcp を使う世界
RA_DEFAULT_WORLDS = {"W_SO", "W_M", "W_MA", "W_S"}   # 既定経路が RA 由来（W_MP は静的）
DHCPV6_WORLDS = {"W_SO", "W_M", "W_MA", "W_MP"}       # DHCPv6/リレーを使う世界（W_S 除く）
FAULT_WORLDS = {
    # ra_suppress は SLAAC 主体世界のみ（stateful は explicit dhcp client が
    # アドレスを取得してしまい「LL のみ」症状が出ない＝チケットが盤面と矛盾する。
    # PoC 実測に基づく制限）。stateful での「既定経路だけ死ぬ」は ra_lifetime_zero が担当。
    "ra_suppress": {"W_SO", "W_S"},
    "ra_lifetime_zero": RA_DEFAULT_WORLDS,
    "o_flag_missing": {"W_SO"},
    "a_not_suppressed": {"W_M"},
    "nd_prefix_wrong_len": SLAAC_WORLDS,
    "rdnss_missing": {"W_S"},
    "link_address_missing": {"W_SO"},
    "pool_prefix_mismatch": STATEFUL_WORLDS,
    "dns_option_missing": DHCPV6_WORLDS,
    "relay_missing": DHCPV6_WORLDS,
    "relay_wrong_dest": DHCPV6_WORLDS,
    # ipv6_enable_missing は W_MP 限定。W_M/W_MA は autoconfig default が LL を
    # 生成するため ipv6 enable を消しても無症状（PoC 罠#1）。W_MP は純 dhcp で有効。
    "ipv6_enable_missing": {"W_MP"},
    "client_default_missing": {"W_M", "W_MA"},
    "client_static_default_missing": {"W_MP"},
    # acl_blocks_ra: RA が「アドレスの供給源」である世界に限定（W_S=純 SLAAC /
    # W_SO=SLAAC+stateless）。stateful 世界では症状が DHCPv6 側に寄り、
    # 要件文の「フィルタ方針」と症状の対応が鈍るため対象外（PoC #7 の裏取りに基づく）。
    "acl_blocks_ra": {"W_S", "W_SO"},
}
# サーバ全体に効く（LAN を選ばない）故障。
GLOBAL_FAULTS = {"server_attach_missing", "server_named_wrong_pool",
                 "server_return_route_missing"}

# L5 異物系（board=rogue 専用。多アクセス LAN-B に ROG を同居させる）。
# dad_conflict は実機で非決定（DAD は「後から DAD した側が負ける」 boot レースで、
# 非管理スイッチの起動ブラックアウトも絡み CLB を確実に victim にできない＝2026-08-31
# 実測でこの seed は ROG が [DUP] になり CLB が健全のまま）→ 既定 pick から除外・保留。
# render/fix コードは残置（--fault dad_conflict で強制生成のみ・決定化は将来課題）。
L5_FAULTS = ["rogue_ra"]
L5_ALL = ["rogue_ra", "dad_conflict"]
L5_DIFFICULTY = {"rogue_ra": 4, "dad_conflict": 5}


def rand_values(rnd):
    site = rnd.randint(0x10, 0xfe)
    s = f"{site:x}"
    dom = rnd.choice(["ccnp.local", "corp.example", "lab.internal",
                      "acme.test", "example.net"])
    v = {
        "site": s,
        "core": f"2001:DB8:{s}:12",       # RT01-RT02 コア /64
        "lanA": f"2001:DB8:{s}:A",        # LAN-A /64
        "lanB": f"2001:DB8:{s}:B",        # LAN-B /64
        "slo": f"2001:DB8:{s}:1::1",      # サーバ Lo0 /128（データ宛先）
        "dns": f"2001:DB8:{s}:1::53",     # DHCPv6 で配る DNS サーバ
        "dom": dom,
    }
    # 2 LAN の世界を相異なる2つ抽選（順序も seed で）。
    wa, wb = rnd.sample(WORLDS, 2)
    v["lans"] = [
        {"name": "A", "pfx": v["lanA"], "world": wa,
         "gw_slot": 1, "client": "CLA", "pool": "POOL-A"},
        {"name": "B", "pfx": v["lanB"], "world": wb,
         "gw_slot": 2, "client": "CLB", "pool": "POOL-B"},
    ]
    return v


def pick_faults(rnd, n, forced, v):
    """(fault, target_lan_name or None) を n 個。target は世界適合する LAN を抽選。"""
    n_dhcpv6 = sum(1 for lan in v["lans"] if lan["world"] in DHCPV6_WORLDS)

    def applicable(f):
        if f == "server_named_wrong_pool":
            # 1 プールに named 固定して他 LAN を落とす故障 → DHCPv6 LAN が 2 つ要る。
            return [None] if n_dhcpv6 >= 2 else []
        if f in GLOBAL_FAULTS:
            return [None]
        worlds = FAULT_WORLDS.get(f, set(WORLDS))
        return [lan["name"] for lan in v["lans"] if lan["world"] in worlds]

    def clash(f, t, picks):
        """BL-160: acl_blocks_ra は端末の入力フィルタが RA も DHCPv6 応答も
        GW からの応答も一律に落とすため、**同じ LAN の他故障**や**サーバ全体に
        効く故障**とはチケット文が両立しない（相手の「アドレスは取得できている」
        「GW へは到達できる」が偽になる）。→ LAN をまたぐ組合せのみ許す。"""
        for g, gt in picks:
            if f != g and "acl_blocks_ra" in (f, g):
                if t is None or gt is None or t == gt:
                    return True
        return False

    def free(f, picks):
        return [t for t in applicable(f) if not clash(f, t, picks)]

    if forced:
        tgts = applicable(forced)
        if not tgts:
            import sys
            worlds = ", ".join(f"LAN-{l['name']}={l['world']}" for l in v["lans"])
            sys.exit(f"[gen_v6addr] --fault {forced} はこの seed の世界({worlds})に"
                     f"適用できません（適用世界: {sorted(FAULT_WORLDS.get(forced, set(WORLDS)))}）。"
                     "別 seed を選ぶか --fault を外してください。")
        picks = [(forced, rnd.choice(tgts))]
        if n == 2:
            pool = [f for f in FAULTS
                    if LAYER_OF[f] != LAYER_OF[forced] and free(f, picks)]
            if pool:
                g = rnd.choice(pool)
                picks.append((g, rnd.choice(free(g, picks))))
        return picks
    # 無指定: 適用可能な故障からレイヤをまたいで n 個。
    layers = [L for L in LAYERS
              if any(applicable(f) for f in LAYERS[L])]
    order = rnd.sample(layers, k=len(layers))
    picks = []
    for L in order:
        if len(picks) >= n:
            break
        cand = [f for f in LAYERS[L] if free(f, picks)]
        if not cand:
            continue
        f = rnd.choice(cand)
        picks.append((f, rnd.choice(free(f, picks))))
    return picks


def has(faults, name, lan_name=None):
    """故障 name が（指定 LAN を）対象に含むか。"""
    for f, tgt in faults:
        if f == name and (lan_name is None or tgt is None or tgt == lan_name):
            return True
    return False


# ---- レンダリング ----------------------------------------------------------
def render_rt01(v, faults):
    """DHCPv6 サーバ。links[0]=RT02。"""
    L = ["! RT01 初期状態 (DHCPv6 サーバ・先般 IPv6 自動アドレッシングの導入/変更作業を実施した直後)",
         "ipv6 unicast-routing", "ipv6 cef", "!",
         "interface Loopback0",
         f" ipv6 address {v['slo']}/128", "!"]
    # プール（世界ごとに選択キーが変わる。W_S は DHCPv6 不使用＝プール無し）
    for lan in v["lans"]:
        w, pfx, name = lan["world"], lan["pfx"], lan["name"]
        if w == "W_S":
            continue
        L.append(f"ipv6 dhcp pool {lan['pool']}")
        if w == "W_SO":
            if not has(faults, "link_address_missing", name):
                L.append(f" link-address {pfx}::/64")
        else:  # stateful (W_M/W_MA/W_MP)
            if has(faults, "pool_prefix_mismatch", name):
                L.append(f" address prefix 2001:DB8:{v['site']}:DEAD::/64")
            else:
                L.append(f" address prefix {pfx}::/64")
        if not has(faults, "dns_option_missing", name):
            L.append(f" dns-server {v['dns']}")
        L.append(f" domain-name {v['dom']}")
        L.append("!")
    # サーバ結線 IF（automatic bind）
    L += [f"interface {{{{ links[0] }}}}",
          " description === to RT02 (core) ===",
          f" ipv6 address {v['core']}::1/64", " no shutdown"]
    if has(faults, "server_named_wrong_pool"):
        # automatic であるべき所を named 固定（その 1 プールしか応答せず他 LAN が全滅）。
        # 実在する DHCPv6 プール（最初の DHCPv6 LAN）に固定する。
        named = next(l["pool"] for l in v["lans"] if l["world"] in DHCPV6_WORLDS)
        L.append(f" ipv6 dhcp server {named}")
    elif not has(faults, "server_attach_missing"):
        L.append(" ipv6 dhcp server")
    L.append("!")
    # LAN 宛の戻り経路（server_return_route_missing で該当 LAN を欠落）
    for lan in v["lans"]:
        if not has(faults, "server_return_route_missing", lan["name"]):
            L.append(f"ipv6 route {lan['pfx']}::/64 {v['core']}::2")
    L.append("!")
    return L


def ra_lines(v, lan, faults):
    """RT02 の LAN IF に載る RA/リレー行（世界＋故障で変化）。"""
    w, pfx, name = lan["world"], lan["pfx"], lan["name"]
    L = []
    # --- W_MP: RA 抑止ポリシー世界（RA を意図的に停止・relay は残す） ---
    if w == "W_MP":
        # RA 停止＋stateful /128 では on-link プレフィクスが無く、グローバル next-hop の
        # 静的既定は解決できない → 決定的な LL(FE80::1) を GW に置き、端末は
        # 「ipv6 route ::/0 <if> FE80::1」で到達する（実機確認済み・poc 相当）。
        L.append(" ipv6 address FE80::1 link-local")
        if has(faults, "relay_wrong_dest", name):
            L.append(f" ipv6 dhcp relay destination 2001:DB8:{v['site']}:1::FEED")
        elif not has(faults, "relay_missing", name):
            L.append(f" ipv6 dhcp relay destination {v['core']}::1")
        L.append(" ipv6 nd ra suppress all")   # ポリシー（故障ではない）
        return L
    # --- W_S: 純 SLAAC + RDNSS（DHCPv6/リレー無し・DNS は RA オプション） ---
    if w == "W_S":
        if not has(faults, "rdnss_missing", name):
            L.append(f" ipv6 nd ra dns server {v['dns']}")
        if has(faults, "nd_prefix_wrong_len", name):
            L += [f" ipv6 nd prefix {pfx}::/64 no-advertise",
                  f" ipv6 nd prefix {pfx}::/72 2592000 604800"]
        if has(faults, "ra_suppress", name):
            L.append(" ipv6 nd ra suppress all")
        if has(faults, "ra_lifetime_zero", name):
            L.append(" ipv6 nd ra lifetime 0")
        return L
    # --- W_SO / W_M / W_MA ---
    if has(faults, "relay_wrong_dest", name):
        L.append(f" ipv6 dhcp relay destination 2001:DB8:{v['site']}:1::FEED")
    elif not has(faults, "relay_missing", name):
        L.append(f" ipv6 dhcp relay destination {v['core']}::1")
    if w == "W_SO":
        if not has(faults, "o_flag_missing", name):
            L.append(" ipv6 nd other-config-flag")
    else:
        L.append(" ipv6 nd managed-config-flag")
    if has(faults, "nd_prefix_wrong_len", name):
        L += [f" ipv6 nd prefix {pfx}::/64 no-advertise",
              f" ipv6 nd prefix {pfx}::/72 2592000 604800"]
    elif w == "W_M" and not has(faults, "a_not_suppressed", name):
        L.append(f" ipv6 nd prefix {pfx}::/64 2592000 604800 no-autoconfig")
    if has(faults, "ra_suppress", name):
        L.append(" ipv6 nd ra suppress all")
    if has(faults, "ra_lifetime_zero", name):
        L.append(" ipv6 nd ra lifetime 0")
    return L


def render_rt02(v, faults):
    """GW/リレー。links[0]=RT01, links[1]=LAN-A, links[2]=LAN-B。"""
    L = ["! RT02 初期状態 (デフォルトゲートウェイ / DHCPv6 リレー)",
         "ipv6 unicast-routing", "ipv6 cef", "!",
         f"interface {{{{ links[0] }}}}",
         " description === to RT01 (core) ===",
         f" ipv6 address {v['core']}::2/64", " no shutdown", "!"]
    for lan in v["lans"]:
        L += [f"interface {{{{ links[{lan['gw_slot']}] }}}}",
              f" description === LAN-{lan['name']} ({WORLD_LABEL[lan['world']]}) ===",
              f" ipv6 address {lan['pfx']}::1/64", " no shutdown"]
        L += ra_lines(v, lan, faults)
        L.append("!")
    # サーバ Lo0 への戻り（クライアントの実疎通宛先）
    L += [f"ipv6 route 2001:DB8:{v['site']}:1::/64 {v['core']}::1", "!"]
    return L


def srv_seg(v):
    """サーバ・セグメント（Lo0/DNS が属する /64）。端末の入力フィルタの許可対象。"""
    return f"2001:DB8:{v['site']}:1"


def acl_name(lan):
    return f"FILTER-{lan['name']}"


def acl_lines(v, lan, faults):
    """BL-160: 端末の入力フィルタ（方針）。健全形は
        permit ipv6 FE80::/10 any      ← RA/リレー応答など LL 発の制御トラフィック
        permit ipv6 <サーバ /64> any   ← 方針そのもの（利用者トラフィック）
    acl_blocks_ra は 1 行目（LL 許可）を欠落させる。IPv6 ACL の暗黙 permit は
    NS/NA のみで RS/RA は対象外（poc/v6addr/README.md #7 実測）＝ RA が落ち、
    SLAAC でグローバルアドレスが生成されない。"""
    if not has(faults, "acl_blocks_ra", lan["name"]):
        return []
    return [f"ipv6 access-list {acl_name(lan)}",
            f" permit ipv6 {srv_seg(v)}::/64 any", "!"]


def render_client(v, lan, faults):
    """クライアント（IOL ルータをホスト役）。links[0]=RT02。"""
    w, name = lan["world"], lan["name"]
    L = [f"! {lan['client']} 初期状態 (LAN-{name} クライアント端末・{WORLD_LABEL[w]})",
         "ipv6 unicast-routing", "ipv6 cef", "!"]
    L += acl_lines(v, lan, faults)
    L += [f"interface {{{{ links[0] }}}}",
          f" description === to RT02 (LAN-{name}) ===", " no shutdown"]
    if has(faults, "acl_blocks_ra", name):
        L.append(f" ipv6 traffic-filter {acl_name(lan)} in")
    if w in ("W_SO", "W_S"):
        L.append(" ipv6 address autoconfig default")
        L.append("!")
    elif w == "W_MP":
        # RA 停止ポリシー: アドレスは explicit dhcp・既定は静的（RA 由来を使えない）
        if not has(faults, "ipv6_enable_missing", name):
            L.append(" ipv6 enable")
        L.append(" ipv6 address dhcp")
        L.append("!")
        if not has(faults, "client_static_default_missing", name):
            # LL next-hop + 出力 IF（グローバル next-hop は /128 では解決不可）
            L.append("ipv6 route ::/0 {{ links[0] }} FE80::1")
            L.append("!")
    else:  # W_M / W_MA
        if not has(faults, "ipv6_enable_missing", name):
            L.append(" ipv6 enable")
        L.append(" ipv6 address dhcp")
        if not has(faults, "client_default_missing", name):
            L.append(" ipv6 address autoconfig default")
        L.append("!")
    return L


# ---- 修正（fix.json） ------------------------------------------------------
def build_fix(v, faults):
    N = {"match": "none"}
    fixes = []
    for lan in v["lans"]:
        w, pfx, name, pool = lan["world"], lan["pfx"], lan["name"], lan["pool"]
        gwif = f"{{{{ links[{lan['gw_slot']}] }}}}"
        if has(faults, "link_address_missing", name):
            fixes.append({"node": "RT01", "parents": f"ipv6 dhcp pool {pool}",
                          "lines": [f"link-address {pfx}::/64"], **N})
        if has(faults, "pool_prefix_mismatch", name):
            fixes.append({"node": "RT01", "parents": f"ipv6 dhcp pool {pool}",
                          "lines": [f"no address prefix 2001:DB8:{v['site']}:DEAD::/64",
                                    f"address prefix {pfx}::/64"], **N})
        if has(faults, "dns_option_missing", name):
            fixes.append({"node": "RT01", "parents": f"ipv6 dhcp pool {pool}",
                          "lines": [f"dns-server {v['dns']}"], **N})
        if has(faults, "server_return_route_missing", name):
            fixes.append({"node": "RT01",
                          "lines": [f"ipv6 route {pfx}::/64 {v['core']}::2"], **N})
        # RT02 側
        if has(faults, "relay_missing", name):
            fixes.append({"node": "RT02", "parents": f"interface {gwif}",
                          "lines": [f"ipv6 dhcp relay destination {v['core']}::1"], **N})
        if has(faults, "relay_wrong_dest", name):
            fixes.append({"node": "RT02", "parents": f"interface {gwif}",
                          "lines": [f"no ipv6 dhcp relay destination 2001:DB8:{v['site']}:1::FEED",
                                    f"ipv6 dhcp relay destination {v['core']}::1"], **N})
        if has(faults, "o_flag_missing", name):
            fixes.append({"node": "RT02", "parents": f"interface {gwif}",
                          "lines": ["ipv6 nd other-config-flag"], **N})
        if has(faults, "a_not_suppressed", name):
            fixes.append({"node": "RT02", "parents": f"interface {gwif}",
                          "lines": [f"ipv6 nd prefix {pfx}::/64 2592000 604800 no-autoconfig"], **N})
        if has(faults, "nd_prefix_wrong_len", name):
            fixes.append({"node": "RT02", "parents": f"interface {gwif}",
                          "lines": [f"no ipv6 nd prefix {pfx}::/72 2592000 604800",
                                    f"no ipv6 nd prefix {pfx}::/64 no-advertise"], **N})
        if has(faults, "rdnss_missing", name):
            fixes.append({"node": "RT02", "parents": f"interface {gwif}",
                          "lines": [f"ipv6 nd ra dns server {v['dns']}"], **N})
        if has(faults, "ra_suppress", name):
            fixes.append({"node": "RT02", "parents": f"interface {gwif}",
                          "lines": ["no ipv6 nd ra suppress all"], **N})
        if has(faults, "ra_lifetime_zero", name):
            fixes.append({"node": "RT02", "parents": f"interface {gwif}",
                          "lines": ["no ipv6 nd ra lifetime 0"], **N})
        # クライアント側
        cif = "{{ links[0] }}"
        if has(faults, "ipv6_enable_missing", name):
            fixes.append({"node": lan["client"], "parents": f"interface {cif}",
                          "lines": ["ipv6 enable"], **N})
        if has(faults, "client_default_missing", name):
            fixes.append({"node": lan["client"], "parents": f"interface {cif}",
                          "lines": ["ipv6 address autoconfig default"], **N})
        if has(faults, "client_static_default_missing", name):
            fixes.append({"node": lan["client"],
                          "lines": ["ipv6 route ::/0 {{ links[0] }} FE80::1"], **N})
        if has(faults, "acl_blocks_ra", name):
            # 方針(サーバ /64 の許可)は残したまま、LL 発の制御トラフィックを許可する
            # 1 行を足すのが模範解。フィルタ自体の削除・全面許可は過剰解（監査で降格）。
            fixes.append({"node": lan["client"],
                          "parents": f"ipv6 access-list {acl_name(lan)}",
                          "lines": ["permit ipv6 FE80::/10 any"], **N})
    # サーバ全体
    if has(faults, "server_named_wrong_pool"):
        named = next(l["pool"] for l in v["lans"] if l["world"] in DHCPV6_WORLDS)
        fixes.append({"node": "RT01", "parents": "interface {{ links[0] }}",
                      "lines": [f"no ipv6 dhcp server {named}", "ipv6 dhcp server"], **N})
    elif has(faults, "server_attach_missing"):
        fixes.append({"node": "RT01", "parents": "interface {{ links[0] }}",
                      "lines": ["ipv6 dhcp server"], **N})
    return fixes


# ---- 症状文（チケット） ----------------------------------------------------
def symptom(v, f, tgt):
    lan = next((l for l in v["lans"] if l["name"] == tgt), None)
    ln = f"LAN-{tgt}" if tgt else "各 LAN"
    T = {
        "ra_suppress":
            f"{ln} の端末が、IPv6 アドレスもデフォルトゲートウェイも取得できず、"
            "リンクローカルアドレスのみの状態です。端末を再起動しても改善しません。",
        "ra_lifetime_zero":
            f"{ln} の端末は IPv6 アドレスと DNS を取得できていますが、"
            "同一 LAN の外にある宛先（サーバ等）へまったく到達できません。",
        "o_flag_missing":
            f"{ln} の端末は IPv6 アドレスを自動生成できていますが、"
            "DNS などの構成情報がサーバから配布されていません。",
        "a_not_suppressed":
            f"{ln} では自動生成アドレスを許可しない方針ですが、端末に自動生成された"
            "アドレスが付与されており、構成監査の指摘を受けています。",
        "nd_prefix_wrong_len":
            f"{ln} の端末が IPv6 アドレスを自動生成できず、リンクローカルのみの状態です。"
            "ルータからの通知（RA）自体は届いているように見えます。",
        "server_attach_missing":
            "監視/変更作業の完了後から、どの LAN の端末もサーバからの構成"
            "（アドレスや DNS）を受け取れなくなっています。",
        "link_address_missing":
            f"{ln} の端末は自動生成アドレスは持っていますが、DNS 情報が配布されて"
            "いません。他の LAN では DNS の配布は正常です。",
        "pool_prefix_mismatch":
            f"{ln} の端末が、サーバ管理のアドレスを取得できていません。"
            "サーバの割り当て記録（binding）にも該当エントリがありません。",
        "dns_option_missing":
            f"{ln} の端末はアドレスを取得できていますが、DNS 情報が配布されていません。",
        "server_named_wrong_pool":
            "一部の LAN でだけサーバからの構成が受け取れ、別の LAN では"
            "アドレスや DNS がまったく配布されていません。",
        "relay_missing":
            f"{ln} の端末が、サーバから配布されるはずの構成を受け取れていません。"
            "同一 LAN 内のルータ（ゲートウェイ）へは到達できます。",
        "relay_wrong_dest":
            f"{ln} の端末が、サーバから配布されるはずの構成を受け取れていません。",
        "ipv6_enable_missing":
            f"{ln} の端末が、サーバ管理のアドレスを取得できていません。"
            "設定を確認すると、アドレス取得の指定自体は入っているように見えます。",
        "client_default_missing":
            f"{ln} の端末は正しいアドレスを取得できていますが、"
            "同一 LAN の外の宛先へ到達できません。",
        "server_return_route_missing":
            f"{ln} の端末は正しいアドレスを取得できています（サーバの割り当て記録"
            "にも載っています）が、サーバへの通信が確立できません。",
        "rdnss_missing":
            f"{ln} の端末は IPv6 アドレスを自動生成できていますが、"
            "DNS 情報を受け取れていません。",
        "acl_blocks_ra":
            f"{ln} の端末が、IPv6 アドレスを自動生成できず、リンクローカルアドレス"
            "のみの状態です。端末を再起動しても改善しません。ゲートウェイ側では、"
            "この LAN 向けの設定は先般の作業で変更していないとの申告があります。",
        "client_static_default_missing":
            f"{ln} ではセキュリティ方針によりルータ広告（RA）を停止しています。"
            "端末はアドレスを取得できていますが、同一 LAN の外にある宛先へ"
            "まったく到達できません。",
    }
    return T[f]


# ---- 採点（挙動ベース・世界ごと） ------------------------------------------
def rx(s):
    return s.replace(".", r"\.").replace(":", r"\:")


def eui64_re(pfx):
    # SLAAC(EUI-64) = <pfx>:....:A8BB:CCFF:FE.. （IOL の MAC 由来）
    return rf"{rx(pfx)}:[0-9A-Fa-f:]*[Aa]8[Bb][Bb]:CCFF:FE"


def lan_checks(v, lan, faults=None):
    """1 LAN の世界に応じた挙動チェック群を返す（faults= フィルタ方針の監査用）。"""
    w, pfx, name = lan["world"], lan["pfx"], lan["name"]
    cl, cif = lan["client"], "Ethernet0/0"
    gwif = f"Ethernet0/{lan['gw_slot']}"
    dns_re, dom_re = rx(v["dns"]), rx(v["dom"])
    checks = []
    if w in SLAAC_WORLDS:
        checks.append({
            "name": f"LAN-{name}: 端末が SLAAC でグローバルアドレスを自動生成 (EUI-64)",
            "node": cl, "command": f"show ipv6 interface brief {cif}",
            "raw": [{"regex": eui64_re(pfx)}], "points": 12})
    if w in STATEFUL_WORLDS:
        checks.append({
            "name": f"LAN-{name}: 端末がサーバ管理アドレスを取得し OPEN",
            "node": cl, "command": f"show ipv6 dhcp interface {cif}",
            "raw": [{"regex": r"Address State is OPEN"},
                    {"regex": rf"Address\s*:\s*{rx(pfx)}:"}], "points": 12})
        checks.append({
            "name": f"LAN-{name}: サーバの binding に IA_NA 割当が存在",
            "node": "RT01", "command": "show ipv6 dhcp binding",
            "raw": [{"regex": rf"Address\s*:\s*{rx(pfx)}:"}], "points": 6})
    if w == "W_M":
        # 「自動生成の抑止」は GW の広告(no-autoconfig)で採点する。クライアント側の
        # EUI-64 有無で採点すると、修正(no-autoconfig 追加)後も既存 SLAAC アドレスが
        # valid lifetime の間 残留し（バウンスしない限り消えない）誤 FAIL になるため。
        checks.append({
            "name": f"LAN-{name}: GW が自動生成を抑止 (RA prefix no-autoconfig)",
            "node": "RT02", "command": f"show running-config interface {gwif}",
            "raw": [{"regex": r"ipv6 nd prefix \S+ .*no-autoconfig"}], "points": 6})
    if w == "W_MA":
        checks.append({
            "name": f"LAN-{name}: 管理アドレスと自動生成アドレスが併存",
            "node": cl, "command": f"show ipv6 interface brief {cif}",
            "raw": [{"regex": eui64_re(pfx)}], "points": 6})
    if w == "W_MP":
        # 反転世界: RA は方針で停止したまま（再有効化＝過剰解）を担保する監査。
        checks.append({
            "name": f"LAN-{name}: RA が方針どおり停止されている (RT02・過剰解の防止)",
            "node": "RT02", "command": f"show ipv6 interface {gwif}",
            "raw": [{"regex": r"RAs are suppressed \(all\)"}], "points": 6})
        checks.append({
            "name": f"LAN-{name}: 端末が静的既定ゲートウェイを保持",
            "node": cl, "command": "show running-config | include ^ipv6 route",
            "raw": [{"regex": r"(?m)^ipv6 route ::/0 \S+ FE80::1\s*$"}], "points": 6})
    # DNS 配布: W_S は RA の DNS オプション(show ipv6 routers)、他は DHCPv6(dhcp interface)。
    if w == "W_S":
        checks.append({
            "name": f"LAN-{name}: DNS サーバが RA(DNS オプション)で配布されている",
            "node": cl, "command": "show ipv6 routers",
            "raw": [{"regex": rf"DNS server\s+{dns_re}"}], "points": 8})
    else:
        checks.append({
            "name": f"LAN-{name}: DNS/ドメインがサーバから配布されている",
            "node": cl, "command": f"show ipv6 dhcp interface {cif}",
            "raw": [{"regex": rf"DNS server\s*:\s*{dns_re}"},
                    {"regex": rf"Domain name\s*:\s*{dom_re}"}], "points": 8})
    # BL-160: 入力フィルタ方針の LAN は「方針を維持したまま是正したか」を監査する
    # （フィルタの取り外し・全面許可への置換＝過剰解を降格させる）。
    if has(faults or [], "acl_blocks_ra", name):
        an = acl_name(lan)
        checks.append({
            "name": f"LAN-{name}: 端末の入力フィルタが適用されたまま維持されている"
                    "（過剰解の防止）",
            "node": cl, "command": f"show running-config interface {cif}",
            "raw": [{"regex": rf"ipv6 traffic-filter {an} in"}], "points": 8})
        checks.append({
            "name": f"LAN-{name}: フィルタ方針（サーバ・セグメントのみ許可）が"
                    "維持されている",
            "node": cl, "command": f"show ipv6 access-list {an}",
            "raw": [{"regex": rf"permit ipv6 {rx(srv_seg(v))}\:\:/64 any"},
                    {"not_regex": r"permit ipv6 any any"}], "points": 8})
    # 実疎通（サーバ Lo0）: 既定経路が RA 由来でも静的でも到達すれば OK。
    gw_kind = "静的既定" if w == "W_MP" else "既定"
    checks.append({
        "name": f"LAN-{name}: 端末が{gw_kind}経路を持ちサーバ Lo0 へ実疎通",
        "node": cl,
        "command": f"ping {v['slo']} source {cif} repeat 6",
        "raw": [{"regex": r"Success rate is (100|8[3-9]|9[0-9]) percent"}],
        "points": 8})
    return checks


def build_grading(v, prob_id, faults=None):
    checks = []
    for lan in v["lans"]:
        checks += lan_checks(v, lan, faults)
    # IOS は IPv6 を大文字表示するが生成側は小文字 hex → 全 regex を大小無視化。
    for c in checks:
        for cond in c.get("raw", []):
            for k in ("regex", "not_regex"):
                if k in cond and not cond[k].startswith("(?i)"):
                    cond[k] = "(?i)" + cond[k]
    # 合計を 100 に正規化（世界の組合せでチェック数が変わるため）。端数は末尾で調整。
    raw_total = sum(c["points"] for c in checks)
    acc = 0
    for c in checks[:-1]:
        c["points"] = round(c["points"] * 100 / raw_total)
        acc += c["points"]
    checks[-1]["points"] = 100 - acc
    return {"problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"}, "checks": checks}


# ---- task.md ---------------------------------------------------------------
def world_req(lan):
    w, name = lan["world"], lan["name"]
    reqs = {
        "W_SO": (f"LAN-{name} の端末は、**IPv6 アドレスを自動生成**し（ルータ広告に基づく）、"
                 f"**DNS などの構成情報は中央の DHCPv6 サーバから取得**する。"),
        "W_M": (f"LAN-{name} の端末は、**IPv6 アドレスを中央の DHCPv6 サーバから取得**する"
                f"（サーバ管理）。**自動生成されたアドレスを併存させてはならない。**"),
        "W_MA": (f"LAN-{name} の端末は、**IPv6 アドレスを中央の DHCPv6 サーバから取得**する"
                 f"（サーバ管理）。自動生成されたアドレスが併存してもよい。"),
        "W_S": (f"LAN-{name} の端末は、**IPv6 アドレスを自動生成**し（ルータ広告に基づく）、"
                f"**DNS サーバはルータ広告で受け取る**。この LAN では DHCPv6 を使用しない。"),
        "W_MP": (f"LAN-{name} では、**セキュリティ方針によりルータ広告（RA）を停止**する。"
                 f"端末は **IPv6 アドレスを中央の DHCPv6 サーバから取得**し（サーバ管理）、"
                 f"**既定ゲートウェイは静的に設定**する。**RA を有効化してはならない。**"),
    }
    return reqs[w]


def filter_req(v, lan):
    """BL-160: 入力フィルタ方針を持つ LAN の追加要件。
    「利用者トラフィック」と限定することで、制御メッセージの許可が方針違反に
    ならないようにしてある（＝ 正解が一意に補完でき、かつ機構は明かさない）。"""
    return (f"また、LAN-{lan['name']} の端末では、**入力方向のトラフィック・"
            f"フィルタ**により、**利用者トラフィックは、サーバ・セグメント"
            f"（`{srv_seg(v)}::/64`）から発信されたもののみを許可**する。"
            f"**このフィルタを取り外したり、すべての通信を許可する形に"
            f"置き換えたりしてはならない。**")


def build_task(v, prob_id, faults, diff):
    tickets = "\n".join(
        f"> {i + 1}. {symptom(v, f, tgt)}" for i, (f, tgt) in enumerate(faults)) \
        if len(faults) > 1 else f"> {symptom(v, faults[0][0], faults[0][1])}"
    reqs = "\n".join(
        f"{i + 1}. {world_req(lan)}"
        + (" " + filter_req(v, lan)
           if has(faults, "acl_blocks_ra", lan["name"]) else "")
        for i, lan in enumerate(v["lans"]))
    la, lb = v["lans"][0], v["lans"][1]
    return f"""# 問題 {prob_id} : IPv6 自動アドレッシング 適合トラブルシュート（難易度{diff}）

## シナリオ

あなたは、ある企業のネットワーク管理者です。この会社では、2つの利用者 LAN
（LAN-A / LAN-B）に対して IPv6 アドレスの自動割り当てを導入しています。中央の
ルータ **RT01** が DHCPv6 サーバ、**RT02** が各 LAN のデフォルトゲートウェイ兼
DHCPv6 リレーを担い、端末（CLA / CLB）はゲートウェイ越しにアドレスや構成情報を
取得します。

先般、この IPv6 自動アドレッシングに関する導入・変更作業が実施されました。その後、
下記の障害報告が提出されています。**下記の「LAN 要件」に完全に準拠するよう**、
構成を調査し、是正してください。

## LAN 要件

{reqs}

- いずれの LAN でも、端末は取得した既定ゲートウェイ経由で **RT01 の Loopback0
  （`{v['slo']}`・DNS サーバと同一筐体上のサービス）へ到達**できること。
- 配布する **DNS サーバは `{v['dns']}`** とする（DHCPv6 を使う LAN では併せて
  **ドメイン名 `{v['dom']}`** も配布する）。

> 補足: IPv6 では既定ゲートウェイ（デフォルトルート）は DHCPv6 では配布されません。
> 通常はルータ広告（RA）に基づいて取得しますが、RA を停止している LAN では
> 静的に設定する必要があります。

## 障害報告

{tickets}

## トポロジ

```
   RT01 (DHCPv6 サーバ, Lo0={v['slo']})
     │ {v['core']}::/64  (core)
   RT02 (GW / DHCPv6 リレー)
     ├─ {la['pfx']}::/64  LAN-{la['name']} ── {la['client']}
     └─ {lb['pfx']}::/64  LAN-{lb['name']} ── {lb['client']}
```

- コア/各 LAN の /64 で、RT01/RT02 側は `::1`、LAN 側ゲートウェイ（RT02）は `::1` です。
- RT01 は 1 つの結線で 2 つの LAN 分の DHCPv6 要求を処理します（サーバは各 LAN の
  プールを、要求の到来元に基づいて自動選択します）。

## 遵守事項

- 変更してよいのは **RT01・RT02・{la['client']}・{lb['client']}** です
  （すべて自社管理）。ただし各機器の**インタフェースの IPv6 アドレスと Loopback0 は
  変更しないこと**。アドレッシング/経路の土台は健全です。
- 原因の種類・箇所・数は開示されません。LAN 要件と実機の状態を突き合わせて
  差分を特定してください。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）または CML コンソール。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} \\
  -e max_attempts=8 -e settle_delay=15 --vault-password-file <(printf 'CCNP\\n')
```
> 採点では、各 LAN 要件（アドレスの取得方式・DNS 配布・自動生成の可否）と、
> `{v['slo']}` への実疎通を確認します。DHCP 交換や RA 周期のため、収束に数分かかる
> ことがあります。
"""


# ============================================================================
# board=rogue（P4・L5 異物系）: 多アクセス LAN-B に ROG を同居させる 5 IOL 盤面。
#   RT01(サーバ) ─ RT02(GW/リレー) ─[SWB]─ CLB(client) / ROG(未認可機)
#   LAN-A は健全な通常世界、LAN-B は W_SO 固定（SLAAC+O）。故障は ROG/CLB のみ。
# ============================================================================
def rogue_values(rnd):
    v = rand_values(rnd)
    la_world = rnd.choice([w for w in WORLDS if w != "W_SO"])  # LAN-A は対比の通常世界
    v["lans"] = [
        {"name": "A", "pfx": v["lanA"], "world": la_world,
         "gw_slot": 1, "client": "CLA", "pool": "POOL-A"},
        {"name": "B", "pfx": v["lanB"], "world": "W_SO",
         "gw_slot": 2, "client": "CLB", "pool": "POOL-B", "multiaccess": True},
    ]
    v["bad"] = f"2001:DB8:{v['site']}:BAD"      # rogue が広告する偽 /64
    return v


def render_rog(v, fault):
    """LAN-B の未認可機 ROG（links[0]=SWB 経由で LAN-B）。"""
    lanB = v["lans"][1]["pfx"]
    L = ["! ROG 初期状態 (LAN-B に接続された社内機器・先般の作業で設定が変更された)",
         "ipv6 unicast-routing", "ipv6 cef", "!",
         "interface {{ links[0] }}",
         " description === to LAN-B (SWB) ===", " no shutdown"]
    if fault == "rogue_ra":
        # 偽 prefix + 高優先の偽デフォルトを広告（正規 GW=Medium を上書き）
        L += [f" ipv6 address {v['bad']}::1/64",
              " ipv6 nd router-preference High"]
    elif fault == "dad_conflict":
        # ::99 を静的に先取り（即時=CLB の SLAAC 派生 ::99 より先に確立）
        L.append(f" ipv6 address {lanB}::99/64")
    L.append("!")
    return L


def render_clb_rogue(v, fault):
    """board=rogue の CLB（LAN-B=W_SO クライアント・dad_conflict 時のみ手動 LL）。"""
    lan = v["lans"][1]
    L = render_client(v, lan, [])          # 健全な W_SO クライアント
    if fault == "dad_conflict":
        # 手動 LL ::99 → SLAAC 派生 GUA が prefix::99 になり ROG の静的 ::99 と重複
        L = L[:-1] + [" ipv6 address FE80::99 link-local", "!"]
    return L


def rogue_symptom(v, fault):
    if fault == "rogue_ra":
        return ("LAN-B の端末が、社外（`{slo}`）へ到達できません。LAN-B の端末には、"
                "想定していないプレフィックスの IPv6 アドレスが付与されています。"
                ).format(slo=v["slo"])
    return ("LAN-B のある端末が、グローバル IPv6 アドレスを取得できていません"
            "（重複アドレスが検出されています）。")


def rogue_fix(v, fault):
    N = {"match": "none"}
    if fault == "rogue_ra":
        # ROG を無効化（IF shut→最終 RA lifetime 0 で偽デフォルトが速やかに消える）
        return [{"node": "ROG", "parents": "interface {{ links[0] }}",
                 "lines": ["shutdown"], **N}]
    # dad_conflict: CLB の手動 LL を除去→EUI-64 の一意 GUA に戻る
    return [{"node": "CLB", "parents": "interface {{ links[0] }}",
             "lines": ["no ipv6 address FE80::99 link-local"], **N}]


def rogue_grading(v, prob_id, fault):
    checks = []
    checks += lan_checks(v, v["lans"][0])          # LAN-A: 通常世界（健全）
    checks += lan_checks(v, v["lans"][1])          # LAN-B: W_SO（EUI-64/DNS/ping）
    cif = "Ethernet0/0"
    if fault == "rogue_ra":
        checks.append({
            "name": "LAN-B: 未認可の高優先ルータ広告が排除されている (正規 GW のみ)",
            "node": "CLB", "command": "show ipv6 routers",
            "raw": [{"not_regex": r"Preference=High"}], "points": 12})
    else:  # dad_conflict
        checks.append({
            "name": "LAN-B: 端末のアドレスが重複(DUPLICATE)状態でない",
            "node": "CLB", "command": f"show ipv6 interface {cif}",
            "raw": [{"not_regex": r"DUPLICATE"}], "points": 12})
    for c in checks:
        for cond in c.get("raw", []):
            for k in ("regex", "not_regex"):
                if k in cond and not cond[k].startswith("(?i)"):
                    cond[k] = "(?i)" + cond[k]
    raw_total = sum(c["points"] for c in checks)
    acc = 0
    for c in checks[:-1]:
        c["points"] = round(c["points"] * 100 / raw_total)
        acc += c["points"]
    checks[-1]["points"] = 100 - acc
    return {"problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"}, "checks": checks}


def rogue_task(v, prob_id, fault, diff):
    la = v["lans"][0]
    return f"""# 問題 {prob_id} : IPv6 自動アドレッシング 適合トラブルシュート（難易度{diff}）

## シナリオ

あなたは、ある企業のネットワーク管理者です。中央のルータ **RT01** が DHCPv6 サーバ、
**RT02** が各 LAN のデフォルトゲートウェイ兼 DHCPv6 リレーを担います。**LAN-B は
複数の機器が接続する共有セグメント**で、利用者端末 **CLB** のほか、社内機器 **ROG**
も接続されています。

先般の作業の後、下記の障害報告が提出されています。**下記の「LAN 要件」に完全に準拠
するよう**、構成を調査し、是正してください。

## LAN 要件

1. {world_req(la)}
2. LAN-B の端末は、**IPv6 アドレスを自動生成**し（正規ゲートウェイ RT02 のルータ広告に
   基づく）、**DNS などの構成情報は中央の DHCPv6 サーバから取得**する。
3. LAN-B では、**正規のゲートウェイ以外がルータ広告やアドレスの供給源になってはならない**。

- いずれの LAN でも、端末は取得した既定ゲートウェイ経由で **RT01 の Loopback0
  （`{v['slo']}`）へ到達**できること。
- 配布する **DNS サーバは `{v['dns']}`**、DHCPv6 を使う LAN ではドメイン名 `{v['dom']}` も配布する。

## 障害報告

> {rogue_symptom(v, fault)}

## トポロジ

```
   RT01 (DHCPv6 サーバ, Lo0={v['slo']})
     │ {v['core']}::/64  (core)
   RT02 (GW / DHCPv6 リレー)
     ├─ {la['pfx']}::/64  LAN-A ── CLA
     └─ {v['lanB']}::/64  LAN-B ──[SW]── CLB（端末） / ROG（社内機器）
```

## 遵守事項

- 変更してよいのは **RT01・RT02・CLA・CLB・ROG** です（すべて自社管理）。ただし各機器の
  **インタフェースの IPv6 アドレスと Loopback0 は変更しないこと**。アドレッシング/経路の
  土台は健全です。
- 原因の種類・箇所・数は開示されません。LAN 要件と実機の状態を突き合わせて差分を特定して
  ください。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）または CML コンソール。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} \\
  -e max_attempts=8 -e settle_delay=15 --vault-password-file <(printf 'CCNP\\n')
```
> 採点では、各 LAN 要件と `{v['slo']}` への実疎通、および LAN-B の供給源の正当性を確認します。
"""


# ============================================================================
# board=pd（P3・Prefix Delegation）: CPE を RT01 直結にして相談事項2点を回避。
#   RT01(サーバ+委任) ─i0─ RT02(GW/リレー) ─ CLA(LAN-A=W_SO)
#              └─i1─(直結PD)─ RT03(CPE) ─ HST(配下ホスト・SLAAC)
#   PD は named 必須(automatic は IA_PD 無応答=BL-034 PoC)＝RT01 i1 に named・
#   i0 は LAN-A 用 automatic ＝別 IF なので両立する。
# ============================================================================
PD_FAULTS = ["pd_automatic_trap", "pd_pool_missing", "pd_client_missing",
             "pd_general_prefix_missing"]
PD_DIFFICULTY = {"pd_automatic_trap": 5, "pd_pool_missing": 4,
                 "pd_client_missing": 4, "pd_general_prefix_missing": 5}


def pd_values(rnd):
    v = rand_values(rnd)
    h = rnd.choice("cdef")                        # 委任 /48 の 3hextet 目
    v["pdwan"] = f"2001:DB8:{v['site']}:13"       # RT01-RT03 直結 /64
    v["deleg_pool"] = f"2001:DB8:{h}000::/40 48"  # 委任元 local pool（/40→/48 委任）
    v["deleg48"] = f"2001:DB8:{h}000"             # 委任される /48（先頭）
    v["hstpfx"] = f"2001:DB8:{h}000:1"            # CPE 配下 LAN（DELEG 0:0:0:1::/64）
    # LAN-A は W_SO 固定（対比の健全 LAN）。
    v["lans"] = [{"name": "A", "pfx": v["lanA"], "world": "W_SO",
                  "gw_slot": 1, "client": "CLA", "pool": "POOL-A"}]
    return v


def render_rt01_pd(v, fault):
    la = v["lans"][0]
    L = ["! RT01 初期状態 (DHCPv6 サーバ + プレフィックス委任サーバ)",
         "ipv6 unicast-routing", "ipv6 cef", "!",
         "interface Loopback0", f" ipv6 address {v['slo']}/128", "!",
         # LAN-A (W_SO: stateless) プール
         f"ipv6 dhcp pool {la['pool']}",
         f" link-address {la['pfx']}::/64",
         f" dns-server {v['dns']}", f" domain-name {v['dom']}", "!",
         # PD 委任
         f"ipv6 local pool DELEG {v['deleg_pool']}",
         "ipv6 dhcp pool POOL-PD"]
    if "pd_pool_missing" != fault:
        L.append(" prefix-delegation pool DELEG")
    L += [f" dns-server {v['dns']}", f" domain-name {v['dom']}", "!",
          "interface {{ links[0] }}",
          " description === to RT02 (core・LAN-A relay) ===",
          f" ipv6 address {v['core']}::1/64", " no shutdown",
          " ipv6 dhcp server", "!",          # automatic（LAN-A 用）
          "interface {{ links[1] }}",
          " description === to RT03 (CPE・prefix delegation) ===",
          f" ipv6 address {v['pdwan']}::1/64", " no shutdown"]
    # PD 用 named binding（pd_automatic_trap 時は bare=automatic に）
    L.append(" ipv6 dhcp server" if fault == "pd_automatic_trap"
             else " ipv6 dhcp server POOL-PD")
    L += ["!", f"ipv6 route {la['pfx']}::/64 {v['core']}::2", "!"]
    return L


def render_rt02_pd(v):
    la = v["lans"][0]
    return ["! RT02 初期状態 (LAN-A のデフォルトゲートウェイ / DHCPv6 リレー)",
            "ipv6 unicast-routing", "ipv6 cef", "!",
            "interface {{ links[0] }}",
            " description === to RT01 (core) ===",
            f" ipv6 address {v['core']}::2/64", " no shutdown", "!",
            "interface {{ links[1] }}",
            f" description === LAN-A ({WORLD_LABEL['W_SO']}) ===",
            f" ipv6 address {la['pfx']}::1/64", " no shutdown",
            f" ipv6 dhcp relay destination {v['core']}::1",
            " ipv6 nd other-config-flag", "!",
            f"ipv6 route 2001:DB8:{v['site']}:1::/64 {v['core']}::1", "!"]


def render_cpe(v, fault):
    """RT03 = CPE（PD クライアント）。links[0]=WAN(RT01), links[1]=LAN(HST)。"""
    L = ["! RT03 初期状態 (CPE・上流から委任プレフィックスを受け配下へ配布)",
         "ipv6 unicast-routing", "ipv6 cef", "!",
         "interface {{ links[0] }}",
         " description === WAN to RT01 (prefix delegation) ===",
         " ipv6 enable",
         f" ipv6 address {v['pdwan']}::2/64"]
    if fault != "pd_client_missing":
        L.append(" ipv6 dhcp client pd DELEG")     # 委任要求→general-prefix DELEG
    L += [" no shutdown", "!",
          "interface {{ links[1] }}",
          " description === LAN to HST (配下・SLAAC) ==="]
    if fault != "pd_general_prefix_missing":
        L.append(" ipv6 address DELEG 0:0:0:1::1/64")  # 委任 /48 から /64 派生
    L += [" no shutdown", "!",
          f"ipv6 route ::/0 {v['pdwan']}::1", "!"]     # 上流デフォルト
    return L


def render_hst(v):
    return ["! HST 初期状態 (CPE 配下の社内ホスト・SLAAC)",
            "ipv6 unicast-routing", "ipv6 cef", "!",
            "interface {{ links[0] }}",
            " description === to RT03 (CPE LAN) ===", " no shutdown",
            " ipv6 address autoconfig default", "!"]


def pd_symptom(v, fault):
    T = {
        "pd_automatic_trap":
            "配下 LAN（HST 側）の端末が IPv6 アドレスを取得できていません。CPE（RT03）は"
            "上流から委任プレフィックスを受け取れていないようです。",
        "pd_pool_missing":
            "CPE（RT03）が上流から委任プレフィックスを受け取れず、配下 LAN の端末が"
            "アドレスを取得できていません。",
        "pd_client_missing":
            "配下 LAN の端末がアドレスを取得できていません。CPE（RT03）は上流へ委任要求を"
            "行っていないように見えます。",
        "pd_general_prefix_missing":
            "CPE（RT03）は上流から委任プレフィックスを受け取れていますが、配下 LAN の端末に"
            "アドレスが供給されていません。",
    }
    return T[fault]


def pd_fix(v, fault):
    N = {"match": "none"}
    if fault == "pd_automatic_trap":
        return [{"node": "RT01", "parents": "interface {{ links[1] }}",
                 "lines": ["no ipv6 dhcp server", "ipv6 dhcp server POOL-PD"], **N}]
    if fault == "pd_pool_missing":
        return [{"node": "RT01", "parents": "ipv6 dhcp pool POOL-PD",
                 "lines": ["prefix-delegation pool DELEG"], **N}]
    if fault == "pd_client_missing":
        return [{"node": "RT03", "parents": "interface {{ links[0] }}",
                 "lines": ["ipv6 dhcp client pd DELEG"], **N}]
    return [{"node": "RT03", "parents": "interface {{ links[1] }}",
             "lines": ["ipv6 address DELEG 0:0:0:1::1/64"], **N}]


def pd_grading(v, prob_id, fault):
    checks = list(lan_checks(v, v["lans"][0]))     # LAN-A（W_SO）
    d48, hp = rx(v["deleg48"]), rx(v["hstpfx"])
    checks += [
        {"name": "PD: サーバの binding に委任プレフィックス(IA_PD)が存在",
         "node": "RT01", "command": "show ipv6 dhcp binding",
         "raw": [{"regex": rf"IA.?PD"}, {"regex": rf"{d48}::"}], "points": 12},
        {"name": "CPE: 委任プレフィックスを DHCP PD で取得している",
         "node": "RT03", "command": "show ipv6 general-prefix",
         "raw": [{"regex": r"acquired via DHCP PD"}, {"regex": rf"{d48}::"}],
         "points": 12},
        {"name": "配下ホスト: 委任 /64 から SLAAC アドレスを生成",
         "node": "HST", "command": "show ipv6 interface brief Ethernet0/0",
         "raw": [{"regex": rf"{hp}:[0-9A-Fa-f:]*[Aa]8[Bb][Bb]:CCFF:FE"}],
         "points": 12},
        {"name": "配下ホスト: サーバ Lo0 へ実疎通(委任経路の自動インストール)",
         "node": "HST", "command": f"ping {v['slo']} source Ethernet0/0 repeat 6",
         "raw": [{"regex": r"Success rate is (100|8[3-9]|9[0-9]) percent"}],
         "points": 12},
    ]
    for c in checks:
        for cond in c.get("raw", []):
            for k in ("regex", "not_regex"):
                if k in cond and not cond[k].startswith("(?i)"):
                    cond[k] = "(?i)" + cond[k]
    raw_total = sum(c["points"] for c in checks)
    acc = 0
    for c in checks[:-1]:
        c["points"] = round(c["points"] * 100 / raw_total)
        acc += c["points"]
    checks[-1]["points"] = 100 - acc
    return {"problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"}, "checks": checks}


def pd_task(v, prob_id, fault, diff):
    la = v["lans"][0]
    return f"""# 問題 {prob_id} : IPv6 プレフィックス委任 適合トラブルシュート（難易度{diff}）

## シナリオ

あなたは、ある企業のネットワーク管理者です。中央の **RT01** は DHCPv6 サーバ兼
**プレフィックス委任（PD）サーバ**で、拠点の CPE ルータ **RT03** に対して IPv6
プレフィックスを委任します。RT03 は受け取ったプレフィックスから配下 LAN 用の /64 を
派生させ、配下ホスト **HST** はそこから SLAAC でアドレスを自動生成します。別途、
**RT02** 配下の **LAN-A**（端末 CLA）も収容しています。

先般の作業の後、下記の障害報告が提出されています。**下記の要件に完全に準拠するよう**、
構成を調査し、是正してください。

## 要件

1. {world_req(la)}
2. **CPE（RT03）は上流 RT01 からプレフィックス委任を受け**、配下 LAN 用の /64 を
   派生させる。配下ホスト **HST** は、その /64 から **IPv6 アドレスを自動生成**する。
3. HST は、CPE 経由で **RT01 の Loopback0（`{v['slo']}`）へ到達**できること。

## トポロジ

```
   RT01 (DHCPv6/PD サーバ, Lo0={v['slo']})
     ├─ {v['core']}::/64  ── RT02 (GW/リレー) ── {la['pfx']}::/64  LAN-A ── CLA
     └─ {v['pdwan']}::/64  ── RT03 (CPE) ── (委任 /64) ── HST
```

- RT01 は LAN-A 向けには通常の DHCPv6 サーバ、RT03 向けにはプレフィックス委任サーバ
  として動作します（両者は別インタフェース）。
- 配布する **DNS サーバは `{v['dns']}`**、ドメイン名は `{v['dom']}` です。

## 遵守事項

- 変更してよいのは **RT01・RT02・CLA・RT03・HST** です（すべて自社管理）。ただし各機器の
  **インタフェースの IPv6 アドレスと Loopback0 は変更しないこと**（委任プレフィックスから
  派生するアドレスはこの限りではありません）。
- 原因の種類・箇所・数は開示されません。要件と実機の状態を突き合わせて差分を特定して
  ください。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）または CML コンソール。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} \\
  -e max_attempts=8 -e settle_delay=15 --vault-password-file <(printf 'CCNP\\n')
```
> 採点では、委任プレフィックスの取得（サーバ binding / CPE の general-prefix）、配下
> ホストのアドレス生成、`{v['slo']}` への実疎通を確認します。
"""


def gen_pd(a, rnd):
    v = pd_values(rnd)
    fault = a.fault if a.fault in PD_FAULTS else rnd.choice(PD_FAULTS)
    diff = PD_DIFFICULTY[fault]
    prob_id = f"GEN-V6ADDR-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {
        "id": prob_id,
        "title": f"IPv6 プレフィックス委任 適合トラブルシュート (seed={a.seed})",
        "exam": "ENARSI",
        "topics": ["ipv6", "dhcpv6", "prefix-delegation", "slaac",
                   "troubleshooting", "generated"],
        "difficulty": diff, "topology": "generated",
        "target_nodes": ["RT01", "RT02", "CLA", "RT03", "HST"],
        "points": 100, "access": "ssh", "bringup_data_ifs": True,
        "lab": {"links": [
            {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
            {"a": "RT02", "a_if": 1, "b": "CLA", "b_if": 0},
            {"a": "RT01", "a_if": 1, "b": "RT03", "b_if": 0},
            {"a": "RT03", "a_if": 1, "b": "HST", "b_if": 0}],
            "positions": {"RT01": [-320, 0], "RT02": [0, -160],
                          "CLA": [320, -160], "RT03": [0, 160],
                          "HST": [320, 160]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_ts.py --board pd) seed={a.seed} "
                f"fault={fault} deleg={v['deleg48']}::/48\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    renderers = {
        "RT01": render_rt01_pd(v, fault),
        "RT02": render_rt02_pd(v),
        "CLA": render_client(v, v["lans"][0], []),
        "RT03": render_cpe(v, fault),
        "HST": render_hst(v),
    }
    for node, lines in renderers.items():
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    grading = pd_grading(v, prob_id, fault)
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_ts.py --board pd) seed={a.seed} fault={fault}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    meta = {"board": "pd", "fault": fault, "difficulty": diff,
            "site": v["site"], "deleg48": v["deleg48"], "hstpfx": v["hstpfx"],
            "pdwan": v["pdwan"], "slo": v["slo"], "dns": v["dns"], "dom": v["dom"]}
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": pd_fix(v, fault)}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(pd_task(v, prob_id, fault, diff))
    print(f"wrote problems/{prob_id} : board=pd fault={fault} diff={diff} "
          f"deleg={v['deleg48']}::/48 site={v['site']}")


def gen_rogue(a, rnd):
    v = rogue_values(rnd)
    fault = a.fault if a.fault in L5_ALL else rnd.choice(L5_FAULTS)
    diff = L5_DIFFICULTY[fault]
    prob_id = f"GEN-V6ADDR-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {
        "id": prob_id,
        "title": f"IPv6 自動アドレッシング 適合トラブルシュート (seed={a.seed})",
        "exam": "ENARSI",
        "topics": ["ipv6", "slaac", "ra", "first-hop-security", "troubleshooting",
                   "generated"],
        "difficulty": diff, "topology": "generated",
        "target_nodes": ["RT01", "RT02", "CLA", "CLB", "ROG"],
        "points": 100, "access": "ssh", "bringup_data_ifs": True,
        "lab": {"switches": ["SWB"], "links": [
            {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
            {"a": "RT02", "a_if": 1, "b": "CLA", "b_if": 0},
            {"a": "RT02", "a_if": 2, "b": "SWB", "b_if": 0},
            {"a": "CLB", "a_if": 0, "b": "SWB", "b_if": 1},
            {"a": "ROG", "a_if": 0, "b": "SWB", "b_if": 2}],
            "positions": {"RT01": [-320, -140], "RT02": [0, 0],
                          "CLA": [320, -200], "CLB": [340, 120],
                          "ROG": [340, 260]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_ts.py --board rogue) seed={a.seed} "
                f"fault={fault} worlds=A:{v['lans'][0]['world']},B:W_SO\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    renderers = {
        "RT01": render_rt01(v, []),
        "RT02": render_rt02(v, []),
        "CLA": render_client(v, v["lans"][0], []),
        "CLB": render_clb_rogue(v, fault),
        "ROG": render_rog(v, fault),
    }
    for node, lines in renderers.items():
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    grading = rogue_grading(v, prob_id, fault)
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_ts.py --board rogue) seed={a.seed} fault={fault}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    meta = {"board": "rogue", "fault": fault, "difficulty": diff,
            "worlds": {"A": v["lans"][0]["world"], "B": "W_SO"},
            "site": v["site"], "lanB": v["lanB"], "bad": v["bad"],
            "slo": v["slo"], "dns": v["dns"], "dom": v["dom"]}
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": rogue_fix(v, fault)}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(rogue_task(v, prob_id, fault, diff))
    print(f"wrote problems/{prob_id} : board=rogue fault={fault} diff={diff} "
          f"worlds=A:{v['lans'][0]['world']},B:W_SO site={v['site']}")


# ============================================================================
# board=fhs（BL-146・IPv6 First-Hop Security）: board=rogue の SWB を ioll2 管理スイッチ
# （採点対象）に置換。ROG は「他部署管理・触れない」制約で、解法を SWB の FHS
# （RA Guard / DHCPv6 Guard）に強制する。PoC= poc/fhs/README.md（ioll2-xe 17.15 実機）。
#   RT01(サーバ) ─ RT02(GW/リレー) ─Et0/0[SWB]Et0/1─ CLB(client) / Et0/2─ ROG(不正 RA+DHCPv6)
#   採点は telnet（ioll2 は SSH 不可）。IOL ルータは vty に telnet を追加して同経路に乗せる。
# ============================================================================
FHS_FAULTS = ["fhs_absent", "fhs_vlan_overblock", "fhs_role_swapped",
              "fhs_dhcpguard_wrong_port", "fhs_pref_cap_low", "fhs_prefix_match_wrong"]
FHS_DIFFICULTY = {"fhs_absent": 4, "fhs_vlan_overblock": 5, "fhs_role_swapped": 4,
                  "fhs_dhcpguard_wrong_port": 4, "fhs_pref_cap_low": 5,
                  "fhs_prefix_match_wrong": 5}
TELNET_VTY = ["line vty 0 4", " transport input ssh telnet", "!"]


def fhs_values(rnd):
    v = rogue_values(rnd)
    v["evil_dns"] = f"2001:DB8:{v['site']}:BAD::53"
    v["evil_dom"] = rnd.choice(["evil.example", "guest.local", "test-lab.internal"])
    v["vlan"] = rnd.choice([10, 20, 30, 100, 110, 200])
    v["pol_ra"] = rnd.choice(["RAG-ACCESS", "HOSTS", "NO-RA", "EDGE-RA"])
    v["pol_dh"] = rnd.choice(["DHG-ACCESS", "CLIENTS", "NO-DHCP", "EDGE-DHCP"])
    return v


def render_rog_fhs(v):
    """ROG は常に不正 RA(High・偽 /64)+不正 stateless DHCPv6 を出す（他部署機器・変更不可）。"""
    return ["! ROG 初期状態 (LAN-B に接続された他部署管理の機器・自社からは変更不可)",
            "ipv6 unicast-routing", "ipv6 cef", "!",
            "ipv6 dhcp pool GUEST",
            f" dns-server {v['evil_dns']}", f" domain-name {v['evil_dom']}", "!",
            "interface {{ links[0] }}",
            " description === to LAN-B (SWB) ===",
            f" ipv6 address {v['bad']}::1/64",
            " ipv6 nd other-config-flag",
            " ipv6 nd router-preference High",
            # 短寿命 RA（interval 30 / lifetime 120 / prefix valid 180 preferred 90）:
            # ガード適用後に端末の残留（偽 default・偽 GUA）が数分で自然消滅し採点が収束する。
            " ipv6 nd ra interval 30",
            " ipv6 nd ra lifetime 120",
            f" ipv6 nd prefix {v['bad']}::/64 180 90",
            " ipv6 dhcp server GUEST",
            " no shutdown", "!"] + TELNET_VTY


def render_swb_fhs(v, fault):
    """SWB(ioll2)。links[0]=RT02(GW) / links[1]=CLB / links[2]=ROG。全て VLAN vlan のアクセス。"""
    vl, ra, dh = v["vlan"], v["pol_ra"], v["pol_dh"]
    L = ["! SWB 初期状態 (LAN-B アクセススイッチ・先般 IPv6 FHS の導入作業を実施した直後)",
         f"vlan {vl}", " name LAN-B", "!"]
    ports = [("{{ links[0] }}", "to RT02 (LAN-B GW)"), ("{{ links[1] }}", "to CLB (host)"),
             ("{{ links[2] }}", "to ROG (other-dept device)")]
    # ---- ポリシー定義 ----
    pol = []
    if fault != "fhs_absent":
        if fault == "fhs_pref_cap_low":
            pol += [f"ipv6 nd raguard policy {ra}", " device-role router",
                    " router-preference maximum low", "!"]
        elif fault == "fhs_prefix_match_wrong":
            # 正規 /64 を許可するつもりの PL が LAN-A の /64 を指している
            pol += [f"ipv6 prefix-list RA-OK seq 10 permit {v['lanA']}::/64", "!",
                    f"ipv6 nd raguard policy {ra}", " device-role router",
                    " match ra prefix-list RA-OK", "!"]
        else:
            pol += [f"ipv6 nd raguard policy {ra}", " device-role host", "!"]
        pol += ["ipv6 nd raguard policy UPLINK", " device-role router", "!",
                f"ipv6 dhcp guard policy {dh}", " device-role client", "!",
                "ipv6 dhcp guard policy DHCP-SRV", " device-role server", "!"]
    L += pol
    # ---- attach（故障ごとの配置）----
    att = {p: [] for p, _ in ports}        # port → attach lines
    vlan_att = []
    gw, cl, rg = ports[0][0], ports[1][0], ports[2][0]
    if fault == "fhs_absent":
        pass
    elif fault == "fhs_vlan_overblock":
        vlan_att += [f" ipv6 nd raguard attach-policy {ra}"]
        att[gw] += [" ipv6 dhcp guard attach-policy DHCP-SRV"]
        att[cl] += [f" ipv6 dhcp guard attach-policy {dh}"]
        att[rg] += [f" ipv6 dhcp guard attach-policy {dh}"]
    elif fault == "fhs_role_swapped":
        att[gw] += [f" ipv6 nd raguard attach-policy {ra}", " ipv6 dhcp guard attach-policy DHCP-SRV"]
        att[cl] += [f" ipv6 nd raguard attach-policy {ra}", f" ipv6 dhcp guard attach-policy {dh}"]
        att[rg] += [" ipv6 nd raguard attach-policy UPLINK", f" ipv6 dhcp guard attach-policy {dh}"]
    elif fault == "fhs_dhcpguard_wrong_port":
        att[gw] += [" ipv6 nd raguard attach-policy UPLINK", f" ipv6 dhcp guard attach-policy {dh}"]
        att[cl] += [f" ipv6 nd raguard attach-policy {ra}", f" ipv6 dhcp guard attach-policy {dh}"]
        att[rg] += [f" ipv6 nd raguard attach-policy {ra}"]
    elif fault in ("fhs_pref_cap_low", "fhs_prefix_match_wrong"):
        vlan_att += [f" ipv6 nd raguard attach-policy {ra}"]
        att[gw] += [" ipv6 dhcp guard attach-policy DHCP-SRV"]
        att[cl] += [f" ipv6 dhcp guard attach-policy {dh}"]
        att[rg] += [f" ipv6 dhcp guard attach-policy {dh}"]
    if vlan_att:
        L += [f"vlan configuration {vl}"] + vlan_att + ["!"]
    for p, desc in ports:
        L += [f"interface {p}", f" description === {desc} ===", " switchport",
              " switchport mode access", f" switchport access vlan {vl}"] + att[p] + [" no shutdown", "!"]
    return L


def fhs_symptom(v, fault):
    if fault == "fhs_absent":
        return ("LAN-B の端末が、社外（`{slo}`）へ到達できません。端末には想定していない"
                "プレフィックスの IPv6 アドレスが付与され、DNS サーバも想定外のものが"
                "設定されています。").format(slo=v["slo"])
    if fault == "fhs_role_swapped":
        # DHCPv6 Guard は正しく配置されているため DNS は正規（実測: broken 68 で DNS check PASS）
        return ("LAN-B の端末が、社外（`{slo}`）へ到達できません。端末には正規のプレフィックス"
                "のアドレスが付与されておらず、想定していないプレフィックスのアドレスだけが"
                "付与されています。").format(slo=v["slo"])
    if fault == "fhs_dhcpguard_wrong_port":
        return ("LAN-B の端末は社外（`{slo}`）へ到達できますが、端末に配布された DNS サーバ"
                "とドメイン名が社内標準と異なっています。").format(slo=v["slo"])
    return ("LAN-B の端末が、グローバル IPv6 アドレスを取得できず、既定ゲートウェイも"
            "持っていません（リンクローカルアドレスのみ）。SWB の FHS 導入後から発生しています。")


def fhs_fix(v, fault):
    """模範修正（SWB のみ・ROG 無改変）。fix_console.py 形式 {node: {config: [...]}} も併記。"""
    ra, dh, vl = v["pol_ra"], v["pol_dh"], v["vlan"]
    gw, cl, rg = "Ethernet0/0", "Ethernet0/1", "Ethernet0/2"
    if fault == "fhs_absent":
        cfg = [f"ipv6 nd raguard policy {ra}", " device-role host",
               "ipv6 nd raguard policy UPLINK", " device-role router",
               f"ipv6 dhcp guard policy {dh}", " device-role client",
               "ipv6 dhcp guard policy DHCP-SRV", " device-role server",
               f"interface {gw}", " ipv6 nd raguard attach-policy UPLINK",
               " ipv6 dhcp guard attach-policy DHCP-SRV",
               f"interface {cl}", f" ipv6 nd raguard attach-policy {ra}",
               f" ipv6 dhcp guard attach-policy {dh}",
               f"interface {rg}", f" ipv6 nd raguard attach-policy {ra}",
               f" ipv6 dhcp guard attach-policy {dh}"]
    elif fault == "fhs_vlan_overblock":
        # VLAN 全体の host ポリシーはそのまま、GW ポートだけ router role を port attach（ポート>VLAN）
        cfg = [f"interface {gw}", " ipv6 nd raguard attach-policy UPLINK"]
    elif fault == "fhs_role_swapped":
        cfg = [f"interface {gw}", " ipv6 nd raguard attach-policy UPLINK",
               f"interface {rg}", f" ipv6 nd raguard attach-policy {ra}"]
    elif fault == "fhs_dhcpguard_wrong_port":
        cfg = [f"interface {gw}", " ipv6 dhcp guard attach-policy DHCP-SRV",
               f"interface {rg}", f" ipv6 dhcp guard attach-policy {dh}"]
    elif fault == "fhs_pref_cap_low":
        cfg = [f"ipv6 nd raguard policy {ra}", " router-preference maximum medium"]
    else:  # fhs_prefix_match_wrong
        # `no ipv6 prefix-list RA-OK seq 10`(prefix 省略)は IOS で受理されず、同 seq への別 prefix
        # 追加も拒否される(実測)→ 誤エントリを完全形で削除して正しい /64 を入れる
        cfg = [f"no ipv6 prefix-list RA-OK seq 10 permit {v['lanA']}::/64",
               f"ipv6 prefix-list RA-OK seq 10 permit {v['lanB']}::/64"]
    return {"console": {"SWB": {"config": cfg}}, "fixes": [{"node": "SWB", "lines": cfg,
                                                              "match": "none"}]}


def fhs_grading(v, prob_id, fault):
    lanB = v["lans"][1]
    checks = []
    checks += lan_checks(v, v["lans"][0])          # LAN-A: 通常世界（健全）
    checks += lan_checks(v, lanB)                  # LAN-B: W_SO（EUI-64/DNS/ping）
    checks.append({
        "name": "LAN-B: 未認可の高優先ルータ広告が端末に届いていない (正規 GW のみ)",
        "node": "CLB", "command": "show ipv6 routers",
        "raw": [{"not_regex": r"Preference=High"},
                {"regex": r"Preference=Medium"}], "points": 10})
    checks.append({
        "name": "LAN-B: 端末に偽プレフィックスのアドレスが無い",
        "node": "CLB", "command": "show ipv6 interface brief Ethernet0/0",
        "raw": [{"not_regex": rx(v["bad"]) + ":"}], "points": 6})
    checks.append({
        "name": "SWB: RA Guard が有効 (ポリシーが適用されている)",
        "node": "SWB", "command": "show device-tracking policies",
        "raw": [{"regex": r"(?m)^.+\s(PORT|VLAN)\s+\S+\s+RA guard"}], "points": 6})
    checks.append({
        "name": "SWB: DHCPv6 Guard が有効 (ポリシーが適用されている)",
        "node": "SWB", "command": "show device-tracking policies",
        "raw": [{"regex": r"(?m)^.+\s(PORT|VLAN)\s+\S+\s+DHCP Guard"}], "points": 6})
    checks.append({
        "name": "SWB: ROG 接続ポートが稼働中 (ポート閉塞による解決は不可)",
        "node": "SWB", "command": "show interfaces status",
        "raw": [{"regex": r"(?m)^Et0/2\s+.*\sconnected\s"}], "points": 6})
    checks.append({
        "name": "ROG: 他部署機器が無改変 (RA 設定と IF が初期状態のまま)",
        "node": "ROG", "command": "show running-config interface Ethernet0/0",
        "raw": [{"regex": r"ipv6 nd router-preference High"},
                {"regex": r"ipv6 dhcp server GUEST"},
                {"not_regex": r"(?m)^\s*shutdown"},
                {"not_regex": r"ra suppress"}], "points": 6})
    for c in checks:
        for cond in c.get("raw", []):
            for k in ("regex", "not_regex"):
                if k in cond and not cond[k].startswith("(?i)"):
                    cond[k] = "(?i)" + cond[k]
    raw_total = sum(c["points"] for c in checks)
    acc = 0
    for c in checks[:-1]:
        c["points"] = round(c["points"] * 100 / raw_total)
        acc += c["points"]
    checks[-1]["points"] = 100 - acc
    return {"problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"}, "checks": checks}


def fhs_task(v, prob_id, fault, diff):
    la = v["lans"][0]
    return f"""# 問題 {prob_id} : IPv6 自動アドレッシング 適合トラブルシュート／First-Hop Security（難易度{diff}）

## シナリオ

あなたは、ある企業のネットワーク管理者です。中央のルータ **RT01** が DHCPv6 サーバ、
**RT02** が各 LAN のデフォルトゲートウェイ兼 DHCPv6 リレーを担います。**LAN-B は
アクセススイッチ SWB を介した共有セグメント**で、利用者端末 **CLB** のほか、**他部署が
管理する機器 ROG** も接続されています。ROG は他部署の業務に使用中であり、あなたの
部署には設定変更の権限がありません。また、ROG の接続ポートを閉塞することも業務上
認められていません。

先般、LAN-B のアクセススイッチ SWB に対して IPv6 First-Hop Security の導入作業が
行われた後、下記の障害報告が提出されています。**下記の「LAN 要件」に完全に準拠
するよう**、構成を調査し、是正してください。

## LAN 要件

1. {world_req(la)}
2. LAN-B の端末は、**IPv6 アドレスを自動生成**し（正規ゲートウェイ RT02 のルータ広告に
   基づく）、**DNS などの構成情報は中央の DHCPv6 サーバから取得**する。
3. LAN-B では、**正規のゲートウェイ RT02 以外のルータ広告および DHCPv6 応答が端末に
   届いてはならない**。この保護は **アクセススイッチ SWB で実施**し、ROG 以外の機器が
   別のアクセスポートに接続された場合にも有効であること。

- いずれの LAN でも、端末は取得した既定ゲートウェイ経由で **RT01 の Loopback0
  （`{v['slo']}`）へ到達**できること。
- 配布する **DNS サーバは `{v['dns']}`**、DHCPv6 を使う LAN ではドメイン名 `{v['dom']}` も配布する。

## 障害報告

> {fhs_symptom(v, fault)}

## トポロジ

```
   RT01 (DHCPv6 サーバ, Lo0={v['slo']})
     │ {v['core']}::/64  (core)
   RT02 (GW / DHCPv6 リレー)
     ├─ {la['pfx']}::/64  LAN-A ── CLA
     └─ {v['lanB']}::/64  LAN-B ── Et0/0 [SWB] Et0/1 ── CLB（端末）
                                         Et0/2 ── ROG（他部署機器）
```
SWB のアクセスポートはすべて VLAN {v['vlan']}（LAN-B）です。

## 遵守事項

- 変更してよいのは **RT01・RT02・CLA・CLB・SWB** です。**ROG は変更禁止**（他部署管理）、
  **SWB のポートを shutdown することも禁止**です。各機器の **インタフェースの IPv6 アドレス
  と Loopback0 は変更しないこと**。アドレッシング/経路の土台は健全です。
- 原因の種類・箇所・数は開示されません。LAN 要件と実機の状態を突き合わせて差分を特定して
  ください。
- 端末 CLB は、是正後に IPv6 の状態を再取得させる目的で **インタフェースの shutdown /
  no shutdown を行ってよい**（端末のアドレス設定そのものを変更してはならない）。
  DHCPv6 で取得した構成情報は端末側に長時間キャッシュされることに注意。

## アクセス・採点

telnet/SSH `SUZUKI / CCNP`（mgmt は割当順・**SWB は telnet のみ**）または CML コンソール。
```
scripts/lab.sh grade {prob_id}
```
> 採点では、各 LAN 要件と `{v['slo']}` への実疎通、LAN-B の供給源の正当性、SWB の保護機能の
> 有効性、および ROG・ポートの無改変を確認します。
"""


def gen_fhs(a, rnd):
    v = fhs_values(rnd)
    fault = a.fault if a.fault in FHS_FAULTS else rnd.choice(FHS_FAULTS)
    diff = FHS_DIFFICULTY[fault]
    prob_id = f"GEN-V6ADDR-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {
        "id": prob_id,
        "title": f"IPv6 自動アドレッシング TS / First-Hop Security (seed={a.seed})",
        "exam": "ENARSI",
        "topics": ["ipv6", "slaac", "ra", "first-hop-security", "ra-guard", "dhcpv6-guard",
                   "troubleshooting", "generated"],
        "difficulty": diff, "topology": "generated",
        "target_nodes": ["RT01", "RT02", "CLA", "CLB", "ROG", "SWB"],
        "points": 100, "access": "telnet", "bringup_data_ifs": True,
        # SWB(ioll2) は SSH 不可＝SSH 経路の bringup から除外（スイッチポートは day0 で up）
        "bringup_nodes": ["RT01", "RT02", "CLA", "CLB", "ROG"],
        "lab": {"links": [
            {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
            {"a": "RT02", "a_if": 1, "b": "CLA", "b_if": 0},
            {"a": "RT02", "a_if": 2, "b": "SWB", "b_if": 0},
            {"a": "CLB", "a_if": 0, "b": "SWB", "b_if": 1},
            {"a": "ROG", "a_if": 0, "b": "SWB", "b_if": 2}],
            "positions": {"RT01": [-320, -140], "RT02": [0, 0], "SWB": [200, 160],
                          "CLA": [320, -200], "CLB": [400, 80], "ROG": [400, 260]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_ts.py --board fhs) seed={a.seed} "
                f"fault={fault} worlds=A:{v['lans'][0]['world']},B:W_SO\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    renderers = {
        "RT01": render_rt01(v, []) + TELNET_VTY,
        "RT02": render_rt02(v, []) + TELNET_VTY,
        "CLA": render_client(v, v["lans"][0], []) + TELNET_VTY,
        "CLB": render_client(v, v["lans"][1], []) + TELNET_VTY,
        "ROG": render_rog_fhs(v),
        "SWB": render_swb_fhs(v, fault),
    }
    for node, lines in renderers.items():
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    grading = fhs_grading(v, prob_id, fault)
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_ts.py --board fhs) seed={a.seed} fault={fault}\n"
                "# telnet 収集(SWB=ioll2)。挙動採点+SWB の FHS 有効性+ROG/ポート無改変監査。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    meta = {"board": "fhs", "fault": fault, "difficulty": diff,
            "worlds": {"A": v["lans"][0]["world"], "B": "W_SO"},
            "site": v["site"], "lanB": v["lanB"], "bad": v["bad"], "vlan": v["vlan"],
            "pol_ra": v["pol_ra"], "pol_dh": v["pol_dh"],
            "slo": v["slo"], "dns": v["dns"], "dom": v["dom"],
            "evil_dns": v["evil_dns"], "evil_dom": v["evil_dom"]}
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    fx = fhs_fix(v, fault)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fx["fixes"]}, f, ensure_ascii=False, indent=2)
    # SWB は SSH 不可 → 自己検品は fix_console.yml(CML コンソール)で投入する形式も出力
    with open(f"{pdir}/solution/fix_console.json", "w", encoding="utf-8") as f:
        json.dump(fx["console"], f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(fhs_task(v, prob_id, fault, diff))
    print(f"wrote problems/{prob_id} : board=fhs fault={fault} diff={diff} "
          f"worlds=A:{v['lans'][0]['world']},B:W_SO site={v['site']} vlan={v['vlan']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--board", choices=["a", "rogue", "pd", "fhs"], default="a",
                    help="a=2 LAN 点対点(既定) / rogue=多アクセス LAN-B+ROG(L5) / "
                         "pd=Prefix Delegation スパー(CPE 直結) / "
                         "fhs=ioll2 アクセスSW の RA Guard/DHCPv6 Guard(BL-146・telnet 採点)")
    ap.add_argument("--fault", choices=FAULTS + L5_ALL + PD_FAULTS + FHS_FAULTS, default=None)
    ap.add_argument("--faults", type=int, choices=[1, 2], default=1)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    if a.board == "rogue":
        gen_rogue(a, rnd)
        return
    if a.board == "pd":
        gen_pd(a, rnd)
        return
    if a.board == "fhs":
        gen_fhs(a, rnd)
        return
    v = rand_values(rnd)
    faults = pick_faults(rnd, a.faults, a.fault, v)
    diff = min(max(DIFFICULTY[f] for f, _ in faults) +
               (1 if len(faults) == 2 else 0), 5)

    prob_id = f"GEN-V6ADDR-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    flabel = ",".join(f"{n}@{t or 'all'}" for n, t in faults)

    problem = {
        "id": prob_id,
        "title": f"IPv6 自動アドレッシング 適合トラブルシュート (seed={a.seed})",
        "exam": "ENARSI",
        "topics": ["ipv6", "dhcpv6", "slaac", "ra", "troubleshooting", "generated"],
        "difficulty": diff, "topology": "generated",
        "target_nodes": ["RT01", "RT02", "CLA", "CLB"],
        "points": 100, "access": "ssh", "bringup_data_ifs": True,
        "lab": {"links": [
            {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
            {"a": "RT02", "a_if": 1, "b": "CLA", "b_if": 0},
            {"a": "RT02", "a_if": 2, "b": "CLB", "b_if": 0}],
            "positions": {"RT01": [-320, -140], "RT02": [0, 0],
                          "CLA": [320, -160], "CLB": [320, 160]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_ts.py) seed={a.seed} "
                f"faults={flabel} "
                f"worlds=A:{v['lans'][0]['world']},B:{v['lans'][1]['world']}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    renderers = {
        "RT01": render_rt01(v, faults),
        "RT02": render_rt02(v, faults),
        "CLA": render_client(v, v["lans"][0], faults),
        "CLB": render_client(v, v["lans"][1], faults),
    }
    for node, lines in renderers.items():
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    grading = build_grading(v, prob_id, faults)
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_ts.py) seed={a.seed} "
                f"faults={','.join(n for n, _ in faults)}\n"
                "# 挙動ベース(世界ごと)。SLAAC=EUI-64 有無 / stateful=Address State OPEN+binding\n"
                "# / DNS=show ipv6 dhcp interface / 実疎通=ping Lo0。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    meta = {"faults": [{"fault": n, "target": t} for n, t in faults],
            "difficulty": diff,
            "worlds": {"A": v["lans"][0]["world"], "B": v["lans"][1]["world"]},
            "site": v["site"], "core": v["core"], "lanA": v["lanA"],
            "lanB": v["lanB"], "slo": v["slo"], "dns": v["dns"], "dom": v["dom"]}
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": build_fix(v, faults)}, f, ensure_ascii=False, indent=2)

    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(build_task(v, prob_id, faults, diff))
    print(f"wrote problems/{prob_id} : faults={flabel} "
          f"diff={diff} worlds=A:{v['lans'][0]['world']},B:{v['lans'][1]['world']} "
          f"site={v['site']}")


if __name__ == "__main__":
    main()
