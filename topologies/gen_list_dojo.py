#!/usr/bin/env python3
"""リスト道場生成器（BL-012/013/014・DOJO-LISTS.design.md）。

TS/構築問と毛色を変えた「ドリル(型稽古)」問題。1出題 = K個(既定10)の小課題で、
各課題は「指定名(番号)のリストを1本書くだけ」。採点は模範解答との
**意味的突き合わせ**（何を通し何を落とすかの一致・書き方の自由は認める）。

共通の骨格:
  トポロジ: TARGET(RT01, AS65001) --eBGP-- FEEDER(RT02, AS65099) の2台(IOL)。
  ★battery(被験経路群)は道場ごとに固定・ランダム化は要件側のみ → day0/実機挙動が
    seed 不変で、実機検証1サイクルで以後の全 seed を信頼できる。
  採点: 各課題 = 1チェック(all-or-nothing)。期待に入る prefix は regex、
        入らない prefix は not_regex を battery 全件分生成。
  ★classful 境界ちょうどの prefix（10.0.0.0/8, 198.18.0.0/24 等）は `show ip bgp`
    で /len が省略されるため、regex は `(/8)?` の両対応で生成する。
  生成時セルフチェック: 各課題で「要件の真偽述語で battery を分類した集合」と
  「模範解答を意味評価器で battery に適用した集合」の一致を assert
  （要件文・模範解答・期待集合の三者矛盾を生成時に検出）。--selfcheck N で
  seed 1..N × 全 tier を一括検品（ファイル出力なし）。

--dojo prefix（Phase1・BL-012・実機フルサイクル済 2026-07-12）:
  FEEDER が固定 battery 36経路を広告（35 Null0+network ＋ default-originate）。
  学習者は RT01 で PL-1〜PL-K を定義するだけ（適用不要）。
  確認 = 採点コマンド = `show ip bgp prefix-list PL-x`（read-only・clear不要）。
  SEQ 課題（挿入稽古）のみ形式チェック: `show ip prefix-list PL-x` の seq 行 regex。

--dojo aspath（Phase2・BL-013）:
  FEEDER と RT01 の間に**並列 eBGP 4セッション**（直結 = 素の AS65099、
  ループバック間×3 = `local-as 65010/65020/65030 no-prepend replace-as` で
  セッション単位に送信元ASを偽装）。セッションごとの outbound route-map の
  `set as-path prepend` で中間/起源 AS を合成し、多彩な AS_PATH の battery
  19経路を1台で作る。`^$` 用に RT01 自身のローカル経路2本も battery に含む。
  学習者は RT01 で `ip as-path access-list <課題番号>` を定義するだけ。
  確認 = 採点コマンド = `show ip bgp filter-list <n>`（read-only）。
  素振りには `show ip bgp regexp <re>` も使える。

--dojo acl（Phase3・BL-014）:
  TARGET(RT01) ＋ TGEN(RT02, multi-loopback)。TGEN は自己確認専用
  （IF に仮適用→source ping→ヒットカウンタで体感。採点はカウンタ非依存）。
  学習者は RT01 で指定番号/名前の ACL を定義（APPLY 課題のみ IF 適用まで）。
  採点 = `show access-lists <ID>` を収集し topologies/acl_model.py が
  **テストパケットベクタ battery 26本**を first-match＋暗黙deny で意味評価
  （grade.py の新チェック種 `acl_vectors:`・書き方の自由は認め分類の一致で判定）。
  ODD 課題（非連続ワイルドカード名物）と APPLY 課題のみ raw 形式チェック併設。

出力: problems/GEN-DOJO-<DOJO>-<seed>/
  {problem.yml, initial/*.cfg.j2, task.md, grading.yml, solution.json,
   solution/{solution.md, catalog.json}}
solution.json は solve_generated.yml の filters 形式
（パック直下・blocks ネスト必須 = Phase1 実機で確定した互換仕様）。

使い方: gen_list_dojo.py --repo . --dojo {prefix,aspath} --seed N
        [--count K] [--tier {1,2,mix}] / --selfcheck N
"""
import argparse
import ipaddress
import json
import os
import random
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acl_model  # noqa: E402

LINK_NET = "10.1.12"      # RT01=.1 / RT02=.2 (/30)
AS_TGT, AS_FEED = 65001, 65099
LO = {"RT01": "1.1.1.1", "RT02": "2.2.2.2"}
DIFFICULTY = {"1": 2, "2": 4, "mix": 3}


def net(p):
    return ipaddress.ip_network(p)


# ===========================================================================
# prefix 道場: battery と意味評価器
# ===========================================================================
# 固定 battery（変更時は実機再検証が必要）
#   - 10.1.0.0/16 はリンク採番(10.1.12.0/30)と衝突するため使わない
#   - 同一ネットワークアドレスで classful 長と別長の併存は可（regex 両対応で判別可能）
PREFIX_BATTERY = [
    "10.0.0.0/8",
    "10.10.0.0/16", "10.10.0.0/24", "10.10.1.0/24", "10.10.2.0/24",
    "10.10.1.128/25", "10.10.2.192/26", "10.10.3.0/25",
    "10.10.4.0/27", "10.10.4.32/28", "10.10.4.64/30", "10.10.9.1/32",
    "10.20.0.0/16", "10.20.5.0/24", "10.20.5.64/26", "10.99.99.99/32",
    "172.20.0.0/16", "172.20.0.0/19", "172.20.32.0/19", "172.20.64.0/20",
    "172.20.80.0/22", "172.20.84.0/24", "172.20.84.128/26",
    "172.21.0.0/16", "172.21.128.0/17",
    "192.168.100.0/24", "192.168.101.0/24", "192.168.100.128/25",
    "192.168.101.64/26", "192.168.102.0/23", "192.168.104.0/22",
    "203.0.113.7/32", "203.0.113.64/27",
    "198.51.100.0/25", "198.51.100.128/25",
    "0.0.0.0/0",
]


def entry_matches(entry, route):
    """prefix-list 1エントリのマッチ判定。entry=(action, prefix, ge, le)。"""
    _, epfx, ge, le = entry
    en, rl = net(epfx), route.prefixlen
    shift = 32 - en.prefixlen
    if (int(route.network_address) >> shift) != (int(en.network_address) >> shift):
        return False
    if ge is None and le is None:
        return rl == en.prefixlen
    lo = ge if ge is not None else en.prefixlen
    hi = le if le is not None else 32
    return lo <= rl <= hi


def eval_plist(entries, route):
    """first-match・暗黙deny の prefix-list 意味評価。"""
    for e in entries:
        if entry_matches(e, route):
            return e[0] == "permit"
    return False


def plist_line(name, seq, entry):
    action, pfx, ge, le = entry
    s = f"ip prefix-list {name} seq {seq} {action} {pfx}"
    if ge is not None:
        s += f" ge {ge}"
    if le is not None:
        s += f" le {le}"
    return s


# ===========================================================================
# aspath 道場: battery と意味評価器
# ===========================================================================
# 並列セッション定義（RT02 は local-as no-prepend replace-as でセッション単位に偽装）
#   nbr = RT01 から見たネイバーIP（=RT02 側の送信元）
ASPATH_SESSIONS = {
    "S0": {"as": 65099, "nbr": f"{LINK_NET}.2", "rt02_lo": None, "rt01_lo": None},
    "S1": {"as": 65010, "nbr": "203.0.113.201",
           "rt02_lo": ("Loopback1", "203.0.113.201"),
           "rt01_lo": ("Loopback1", "203.0.113.101")},
    "S2": {"as": 65020, "nbr": "203.0.113.202",
           "rt02_lo": ("Loopback2", "203.0.113.202"),
           "rt01_lo": ("Loopback2", "203.0.113.102")},
    "S3": {"as": 65030, "nbr": "203.0.113.203",
           "rt02_lo": ("Loopback3", "203.0.113.203"),
           "rt01_lo": ("Loopback3", "203.0.113.103")},
}

# 固定 battery: (prefix, AS_PATH, session)。path[0] は必ずセッションAS。
# session=None は RT01 自身のローカル経路（^$ 用・AS_PATH 空）。
# 198.18/198.19 の /24 は classful 境界（表示で /24 省略）→ regex 両対応で吸収。
ASPATH_BATTERY = [
    ("198.18.0.0/24",   [65099],                "S0"),
    ("198.18.1.0/24",   [65099, 65100],         "S0"),
    ("198.18.2.0/24",   [65099, 65100, 65300],  "S0"),
    ("198.18.3.0/24",   [65099, 65200],         "S0"),
    ("198.18.4.0/24",   [65099, 65300],         "S0"),
    ("198.18.10.0/24",  [65010],                "S1"),
    ("198.18.11.0/24",  [65010, 65100],         "S1"),
    ("198.18.12.0/24",  [65010, 65200, 65300],  "S1"),
    ("198.18.13.0/24",  [65010, 65010, 65010],  "S1"),   # prepend 検出用
    ("198.18.14.0/24",  [65010, 65300],         "S1"),
    ("198.19.20.0/24",  [65020],                "S2"),
    ("198.19.21.0/24",  [65020, 65100, 65200],  "S2"),
    ("198.19.22.0/24",  [65020, 65300],         "S2"),
    ("198.19.23.0/24",  [65020, 65100],         "S2"),
    ("100.64.30.0/24",  [65030],                "S3"),
    ("100.64.31.0/24",  [65030, 65200],         "S3"),
    ("100.64.32.0/24",  [65030, 65100, 65300],  "S3"),
    ("100.64.33.0/24",  [65030, 65200, 65100],  "S3"),
    ("100.64.34.0/24",  [65030, 65030, 65030],  "S3"),   # prepend 検出用(2本目)
    ("10.255.1.0/24",   [],                     None),
    ("10.255.2.0/24",   [],                     None),
]


def cisco_aspath_rx_to_py(rx):
    """Cisco AS-path regex → Python regex（`_` = 行頭/行末/空白）。
    battery のパス文字列は空白区切りなので confed 用の ,{}() は考慮不要。"""
    return rx.replace("_", "(?:^|$| )")


def eval_aspath_acl(entries, path):
    """as-path access-list の意味評価（first-match・暗黙deny）。
    entries=[(action, cisco_rx)], path=AS番号リスト。"""
    s = " ".join(str(a) for a in path)
    for action, rx in entries:
        if re.search(cisco_aspath_rx_to_py(rx), s):
            return action == "permit"
    return False


# ===========================================================================
# acl 道場: アドレス・ベクタ battery・意味評価器（= acl_model を共用）
# ===========================================================================
# 固定アドレス空間（TGEN のループバックにもなる）
A10, A99 = "10.30.1.10", "10.30.1.99"           # LAN-A (10.30.1.0/24)
B20 = "10.30.2.20"                               # LAN-B (10.30.2.0/24)
WEB, DNS = "172.22.5.10", "172.22.5.20"          # SRV (172.22.5.0/24)
EXTH = "203.0.113.50"                            # 外部ホスト
O1, O2, O3, O4 = "10.40.1.5", "10.40.2.5", "10.40.3.5", "10.40.4.5"
ACL_TGEN_LOOPS = [A10, A99, B20, WEB, DNS, EXTH, O1, O2, O3, O4]


def _v(vid, proto, src, dst, sport=None, dport=None, est=False, itype=None):
    v = {"id": vid, "proto": proto, "src": src, "dst": dst}
    if sport is not None:
        v["sport"] = sport
    if dport is not None:
        v["dport"] = dport
    if est:
        v["established"] = True
    if itype is not None:
        v["icmp_type"] = itype
    return v


# 固定ベクタ battery（変更時は各テンプレの permit/deny 分布と実機再検証が必要）
ACL_VECTORS = [
    _v("v01", "tcp", A10, WEB, 34567, 80),
    _v("v02", "tcp", A99, WEB, 34568, 443),
    _v("v03", "tcp", B20, WEB, 41000, 80),
    _v("v04", "tcp", EXTH, B20, 52000, 23),
    _v("v05", "tcp", A10, B20, 23456, 23),
    _v("v06", "tcp", EXTH, A10, 80, 33000, est=True),
    _v("v07", "tcp", EXTH, A10, 443, 33001),
    _v("v08", "udp", DNS, A10, 53, 5353),
    _v("v09", "udp", A10, DNS, 5354, 53),
    _v("v10", "udp", EXTH, A10, 123, 123),
    _v("v11", "icmp", A10, WEB, itype=8),
    _v("v12", "icmp", WEB, A10, itype=0),
    _v("v13", "icmp", EXTH, B20, itype=8),
    _v("v14", "tcp", O1, WEB, 40000, 80),
    _v("v15", "tcp", O2, WEB, 40001, 80),
    _v("v16", "tcp", O3, WEB, 40002, 8080),
    _v("v17", "tcp", O4, WEB, 40003, 8041),
    _v("v18", "tcp", B20, WEB, 45000, 8000),
    _v("v19", "tcp", A10, WEB, 45001, 8081),
    _v("v20", "udp", DNS, B20, 50000, 69),
    _v("v21", "tcp", A10, B20, 52222, 22),
    _v("v22", "udp", A99, B20, 52223, 514),
    _v("v23", "icmp", DNS, A10, itype=3),
    _v("v24", "tcp", B20, EXTH, 56000, 80),
    _v("v25", "tcp", EXTH, B20, 443, 51000, est=True),
    _v("v26", "udp", A10, B20, 5555, 53),
]


def in_net(ip, cidr):
    return ipaddress.ip_address(ip) in net(cidr)


def ae(action, proto=None, src="any", sport=None, dst="any", dport=None,
       est=False, itype=None):
    """模範解答エントリ（acl_model.evaluate 互換の構造）を作る。
    src/dst: "any" | ("host", ip) | (net, wildcard)。sport/dport: (op, 値...)"""
    def spec(a):
        if a == "any":
            return 0, 0xFFFFFFFF
        if a[0] == "host":
            return acl_model._ip(a[1]), 0
        return acl_model._ip(a[0]), acl_model._ip(a[1])
    s, sw = spec(src)
    d, dw = spec(dst)
    return {"seq": 0, "action": action, "proto": proto,
            "src": s, "src_wild": sw, "sport": _pspec(sport),
            "dst": d, "dst_wild": dw, "dport": _pspec(dport),
            "established": est, "icmp_type": itype}


def _pspec(p):
    return None if p is None else (p[0], list(p[1:]))


def _addr_str(base, wild):
    ip = ".".join(str((base >> s) & 255) for s in (24, 16, 8, 0))
    if wild == 0xFFFFFFFF:
        return "any"
    if wild == 0:
        return f"host {ip}"
    w = ".".join(str((wild >> s) & 255) for s in (24, 16, 8, 0))
    return f"{ip} {w}"


def acl_cli(entry):
    """模範解答エントリ → CLI 本文（access-list 番号や named の行内容）。"""
    parts = [entry["action"]]
    if entry["proto"] is None:                    # 標準 ACL
        parts.append(_addr_str(entry["src"], entry["src_wild"]))
        return " ".join(parts)
    parts.append(entry["proto"])
    parts.append(_addr_str(entry["src"], entry["src_wild"]))
    if entry["sport"]:
        parts.append(entry["sport"][0] + " " +
                     " ".join(str(x) for x in entry["sport"][1]))
    parts.append(_addr_str(entry["dst"], entry["dst_wild"]))
    if entry["dport"]:
        parts.append(entry["dport"][0] + " " +
                     " ".join(str(x) for x in entry["dport"][1]))
    if entry["established"]:
        parts.append("established")
    if entry["icmp_type"] is not None:
        parts.append(str(entry["icmp_type"]))
    return " ".join(parts)


def build_instances_acl(rnd):
    pool = {}

    def add(i):
        pool.setdefault(i["template"], []).append(i)

    # kind: std_num(10+k) / ext_num(100+k) / named_std / named_ext (DOJO-k)
    # --- STD_NET: 標準・送信元サブネット --------------------------------
    for cidr, label in [("10.30.1.0/24", "LAN-A"), ("10.30.2.0/24", "LAN-B"),
                        ("172.22.5.0/24", "SRV セグメント")]:
        n = net(cidr)
        add(inst("STD_NET", 1, f"標準: 送信元 {cidr} のみ",
                 f"送信元が **{label} (`{cidr}`)** の通信のみを許可せよ。"
                 "他の送信元はすべて拒否すること。",
                 [ae("permit", src=(str(n.network_address),
                                    str(n.hostmask)))],
                 lambda v, c=cidr: in_net(v["src"], c),
                 acl_kind="std_num"))

    # --- STD_HOSTDENY: 標準・ホスト除外＋全許可 --------------------------
    for h in [A99, B20, EXTH]:
        add(inst("STD_HOSTDENY", 1, f"標準: ホスト {h} を拒否",
                 f"送信元ホスト `{h}` からの通信を**拒否**し、"
                 "それ以外の送信元はすべて許可せよ。",
                 [ae("deny", src=("host", h)), ae("permit")],
                 lambda v, h=h: v["src"] != h,
                 acl_kind="std_num"))

    # --- NAMED_STD: named 標準 -------------------------------------------
    for cidr in ["10.40.0.0/16", "203.0.113.0/24"]:
        n = net(cidr)
        add(inst("NAMED_STD", 1, f"named標準: 送信元 {cidr} のみ",
                 f"**named の標準 ACL** で、送信元が `{cidr}` の通信のみを"
                 "許可せよ。他はすべて拒否すること。",
                 [ae("permit", src=(str(n.network_address), str(n.hostmask)))],
                 lambda v, c=cidr: in_net(v["src"], c),
                 acl_kind="named_std"))

    # --- EXT_HTTP: 拡張・プロトコル/ポート限定許可 ------------------------
    add(inst("EXT_HTTP", 1, "拡張: LAN-A→WEB の HTTP のみ",
             f"`10.30.1.0/24` から Web サーバ `{WEB}` への **HTTP (tcp/80)** "
             "のみを許可せよ。他の通信はすべて拒否すること。",
             [ae("permit", "tcp", ("10.30.1.0", "0.0.0.255"),
                 dst=("host", WEB), dport=("eq", 80))],
             lambda v: (v["proto"] == "tcp" and in_net(v["src"], "10.30.1.0/24")
                        and v["dst"] == WEB and v.get("dport") == 80),
             acl_kind="ext_num"))
    add(inst("EXT_HTTP", 1, "拡張: LAN-B→WEB の HTTP のみ",
             f"`10.30.2.0/24` から Web サーバ `{WEB}` への **HTTP (tcp/80)** "
             "のみを許可せよ。他の通信はすべて拒否すること。",
             [ae("permit", "tcp", ("10.30.2.0", "0.0.0.255"),
                 dst=("host", WEB), dport=("eq", 80))],
             lambda v: (v["proto"] == "tcp" and in_net(v["src"], "10.30.2.0/24")
                        and v["dst"] == WEB and v.get("dport") == 80),
             acl_kind="ext_num"))
    add(inst("EXT_HTTP", 1, "拡張: any→DNS の DNS クエリのみ",
             f"任意の送信元から DNS サーバ `{DNS}` への **DNS クエリ (udp/53)** "
             "のみを許可せよ。他の通信はすべて拒否すること。",
             [ae("permit", "udp", dst=("host", DNS), dport=("eq", 53))],
             lambda v: (v["proto"] == "udp" and v["dst"] == DNS
                        and v.get("dport") == 53),
             acl_kind="ext_num"))

    # --- NAMED_EXT_BLOCK: named 拡張・ブロック＋全許可 --------------------
    add(inst("NAMED_EXT_BLOCK", 1, "named拡張: LAN-B宛 Telnet 遮断",
             "どこからであれ `10.30.2.0/24` 宛の **Telnet (tcp/23)** を拒否し、"
             "それ以外の通信はすべて許可せよ。",
             [ae("deny", "tcp", dst=("10.30.2.0", "0.0.0.255"),
                 dport=("eq", 23)), ae("permit", "ip")],
             lambda v: not (v["proto"] == "tcp" and in_net(v["dst"], "10.30.2.0/24")
                            and v.get("dport") == 23),
             acl_kind="named_ext"))
    add(inst("NAMED_EXT_BLOCK", 1, "named拡張: LAN-A→LAN-B の SSH 遮断",
             "`10.30.1.0/24` から `10.30.2.0/24` への **SSH (tcp/22)** を拒否し、"
             "それ以外の通信はすべて許可せよ。",
             [ae("deny", "tcp", ("10.30.1.0", "0.0.0.255"),
                 dst=("10.30.2.0", "0.0.0.255"), dport=("eq", 22)),
              ae("permit", "ip")],
             lambda v: not (v["proto"] == "tcp"
                            and in_net(v["src"], "10.30.1.0/24")
                            and in_net(v["dst"], "10.30.2.0/24")
                            and v.get("dport") == 22),
             acl_kind="named_ext"))

    # --- EST: established（応答のみ許可） ---------------------------------
    for cidr, label in [("10.30.1.0/24", "LAN-A"), ("10.30.2.0/24", "LAN-B")]:
        n = net(cidr)
        add(inst("EST", 2, f"named拡張: {label} 宛は応答TCPのみ",
                 f"**{label} (`{cidr}`) 宛**に通せるのは、内側から確立済みの "
                 "TCP セッションの**応答パケットのみ**とせよ（新規接続は不可）。"
                 "それ以外の通信はすべて拒否すること。",
                 [ae("permit", "tcp", dst=(str(n.network_address),
                                           str(n.hostmask)), est=True)],
                 lambda v, c=cidr: (v["proto"] == "tcp" and in_net(v["dst"], c)
                                    and v.get("established", False)),
                 acl_kind="named_ext"))

    # --- ICMP: タイプ指定 --------------------------------------------------
    add(inst("ICMP", 2, "拡張: ICMP echo のみ拒否",
             "**ICMP echo（ping 要求）だけを拒否**し、それ以外の通信"
             "（echo-reply や他の ICMP タイプを含む）はすべて許可せよ。",
             [ae("deny", "icmp", itype=8), ae("permit", "ip")],
             lambda v: not (v["proto"] == "icmp" and v.get("icmp_type") == 8),
             acl_kind="ext_num"))
    add(inst("ICMP", 2, f"拡張: {EXTH} からの ICMP を拒否",
             f"`{EXTH}` からの **ICMP をすべて拒否**し、それ以外の通信は"
             "すべて許可せよ。",
             [ae("deny", "icmp", ("host", EXTH)), ae("permit", "ip")],
             lambda v: not (v["proto"] == "icmp" and v["src"] == EXTH),
             acl_kind="ext_num"))

    # --- RANGE: ポート範囲 --------------------------------------------------
    for lo, hi in [(8000, 8080), (440, 450)]:
        add(inst("RANGE", 2, f"拡張: WEB への tcp {lo}-{hi} のみ",
                 f"任意の送信元から `{WEB}` への **tcp {lo}〜{hi}** のみを"
                 "許可せよ。他の通信はすべて拒否すること。",
                 [ae("permit", "tcp", dst=("host", WEB),
                     dport=("range", lo, hi))],
                 lambda v, lo=lo, hi=hi: (v["proto"] == "tcp" and v["dst"] == WEB
                                          and v.get("dport") is not None
                                          and lo <= v["dport"] <= hi),
                 acl_kind="ext_num"))

    # --- ODD: 非連続ワイルドカード（名物・1行形式チェック併設） -------------
    for base, parity in [("10.40.1.0", "奇数"), ("10.40.0.0", "偶数")]:
        add(inst("ODD", 2, f"標準: 第3オクテット{parity}のみ（1行）",
                 f"`10.40.0.0/16` 配下のうち、**第3オクテットが{parity}**の /24 "
                 "に属する送信元のみを許可せよ。**エントリは1行**で書くこと。",
                 [ae("permit", src=(base, "0.0.254.255"))],
                 lambda v, p=parity: (in_net(v["src"], "10.40.0.0/16")
                                      and (int(v["src"].split(".")[2]) % 2 == 1)
                                      == (p == "奇数")),
                 acl_kind="std_num",
                 form_raw=[{"regex": base.replace(".", r"\.")
                            + r", wildcard bits 0\.0\.254\.255"}]))

    # --- NEQ ---------------------------------------------------------------
    add(inst("NEQ", 2, "named拡張: LAN-B宛 UDP は DNS 以外拒否",
             "`10.30.2.0/24` 宛の **UDP のうち宛先ポート 53 以外**を拒否し、"
             "それ以外の通信はすべて許可せよ。",
             [ae("deny", "udp", dst=("10.30.2.0", "0.0.0.255"),
                 dport=("neq", 53)), ae("permit", "ip")],
             lambda v: not (v["proto"] == "udp" and in_net(v["dst"], "10.30.2.0/24")
                            and v.get("dport") != 53),
             acl_kind="named_ext"))

    # --- APPLY: 定義＋IF 適用（2チェック分割） ------------------------------
    add(inst("APPLY", 2, "named拡張: TFTP遮断を定義し E0/0 in に適用",
             f"どこからであれホスト `{B20}` 宛の **TFTP (udp/69)** を拒否し"
             "他をすべて許可する ACL を定義したうえで、**Ethernet0/0 に着信 "
             "(in) 方向で適用**せよ。",
             [ae("deny", "udp", dst=("host", B20), dport=("eq", 69)),
              ae("permit", "ip")],
             lambda v: not (v["proto"] == "udp" and v["dst"] == B20
                            and v.get("dport") == 69),
             acl_kind="named_ext", apply_if="Ethernet0/0"))
    return pool


# ===========================================================================
# show ip bgp 表示 regex（classful 境界の /len 省略・列超過折返しに両対応）
# ===========================================================================
def natural_len(n):
    o = int(str(n.network_address).split(".")[0])
    return 8 if o < 128 else (16 if o < 192 else 24)


def disp_rx(pfx):
    n = net(pfx)
    esc = str(n.network_address).replace(".", r"\.")
    if n.prefixlen == 0 or n.prefixlen == natural_len(n):
        return f"{esc}(/{n.prefixlen})?"
    return f"{esc}/{n.prefixlen}"


def bgp_line_rx(pfx):
    """`show ip bgp ...` の経路行 regex。後方境界は \\s（列超過の折返し=改行も吸収）。"""
    return rf"(?m)^\s?\*>?i?\s+{disp_rx(pfx)}\s"


# ===========================================================================
# 課題テンプレート（要件文・模範解答・真偽述語の三点セット）
# ===========================================================================
def within(route, anchor):
    a = net(anchor)
    return (route.prefixlen >= a.prefixlen
            and entry_matches(("permit", anchor, a.prefixlen, 32), route))


def inst(template, tier, label, text, entries, predicate, **extra):
    d = {"template": template, "tier": tier, "label": label,
         "text": text, "entries": entries, "predicate": predicate}
    d.update(extra)
    return d


def build_instances_prefix(rnd):
    pool = {}

    def add(i):
        pool.setdefault(i["template"], []).append(i)

    # --- EXACT: 完全一致（/L ちょうど ≠ 配下全部、の理解） -----------------
    for a in ["10.0.0.0/8", "10.10.0.0/16", "172.20.0.0/16",
              "192.168.100.0/24", "10.10.1.0/24", "172.20.80.0/22"]:
        add(inst("EXACT", 1, f"{a} の完全一致のみ",
                 f"経路 `{a}` **そのもの**だけを許可せよ。その配下のより長い"
                 "（細かい）経路や、それ以外の経路は一切許可しないこと。",
                 [("permit", a, None, None)],
                 lambda r, a=a: r == net(a)))

    # --- LE: 長さ上限（アンカー自身を含む） --------------------------------
    for a, x in [("10.0.0.0/8", 24), ("172.20.0.0/16", 20),
                 ("10.10.0.0/16", 25), ("192.168.100.0/22", 24)]:
        add(inst("LE", 1, f"{a} 内の /{x} 以下",
                 f"`{a}` の範囲に含まれる経路のうち、プレフィックス長が"
                 f" **/{x} 以下**のものをすべて許可せよ"
                 "（範囲の集約経路そのものが存在する場合はそれも含む）。"
                 "それ以外は許可しないこと。",
                 [("permit", a, None, x)],
                 lambda r, a=a, x=x: within(r, a) and r.prefixlen <= x))

    # --- GE: 長さ下限（/32 まで） ------------------------------------------
    for a, x in [("10.10.0.0/16", 25), ("10.0.0.0/8", 30),
                 ("172.20.0.0/16", 22), ("192.168.100.0/22", 25)]:
        add(inst("GE", 1, f"{a} 内の /{x} 以上",
                 f"`{a}` の範囲に含まれる経路のうち、プレフィックス長が"
                 f" **/{x} 以上**のもの（/32 まで）をすべて許可せよ。"
                 "それ以外は許可しないこと。",
                 [("permit", a, x, None)],
                 lambda r, a=a, x=x: within(r, a) and r.prefixlen >= x))

    # --- BAND: 長さ帯域 -----------------------------------------------------
    for a, g, l in [("10.0.0.0/8", 24, 26), ("172.20.0.0/16", 19, 22),
                    ("10.10.0.0/16", 26, 28), ("192.168.96.0/19", 23, 24)]:
        assert g > net(a).prefixlen
        add(inst("BAND", 2, f"{a} 内の /{g}〜/{l}",
                 f"`{a}` の範囲に含まれる経路のうち、プレフィックス長が"
                 f" **/{g} 以上 /{l} 以下**のものをすべて許可せよ。"
                 "帯域外の長さ（範囲の集約経路そのものを含む）は許可しないこと。",
                 [("permit", a, g, l)],
                 lambda r, a=a, g=g, l=l: within(r, a) and g <= r.prefixlen <= l))

    # --- DEFAULT / ANY: 対比ペア -------------------------------------------
    add(inst("DEFAULT", 1, "デフォルトルートのみ",
             "デフォルトルート（`0.0.0.0/0`）**のみ**を許可せよ。"
             "他の経路は一切許可しないこと。",
             [("permit", "0.0.0.0/0", None, None)],
             lambda r: r == net("0.0.0.0/0")))
    add(inst("ANY", 1, "全経路（デフォルト含む）",
             "BGP テーブル上に存在しうる**すべての経路**"
             "（デフォルトルートを含む・プレフィックス長を問わない）を許可せよ。",
             [("permit", "0.0.0.0/0", None, 32)],
             lambda r: True))

    # --- HOSTBLOCK: /32 全拒否＋他全許可（deny+permit の順序） --------------
    add(inst("HOSTBLOCK", 2, "/32 全拒否＋他は全許可",
             "**ホスト経路（/32）をすべて拒否**し、それ以外のすべての経路"
             "（デフォルトルートを含む）を許可せよ。",
             [("deny", "0.0.0.0/0", 32, None), ("permit", "0.0.0.0/0", None, 31)],
             lambda r: r.prefixlen != 32))

    # --- FIX24: ge 24 le 24（配下の /24 固定） ------------------------------
    for a in ["10.10.0.0/16", "10.0.0.0/8", "192.168.100.0/22"]:
        add(inst("FIX24", 2, f"{a} 内の /24 のみ",
                 f"`{a}` の範囲に含まれる **ちょうど /24** の経路だけを"
                 f"すべて許可せよ（範囲の集約経路そのものや、/24 より長い経路は不可）。",
                 [("permit", a, 24, 24)],
                 lambda r, a=a: within(r, a) and r.prefixlen == 24))

    # --- EXCEPT: 例外 deny を先頭に置く順序稽古 -----------------------------
    add(inst("EXCEPT", 2, "10.10.0.0/16 内の /24（例外1件）",
             "`10.10.0.0/16` の範囲に含まれる **ちょうど /24** の経路をすべて許可せよ。"
             "ただし `10.10.2.0/24` は**例外として拒否**すること。",
             [("deny", "10.10.2.0/24", None, None),
              ("permit", "10.10.0.0/16", 24, 24)],
             lambda r: (within(r, "10.10.0.0/16") and r.prefixlen == 24
                        and r != net("10.10.2.0/24"))))
    add(inst("EXCEPT", 2, "172.20.0.0/16 内の /22 以下（例外1件）",
             "`172.20.0.0/16` の範囲に含まれる、プレフィックス長 **/22 以下**の経路"
             "（範囲の集約経路そのものを含む）をすべて許可せよ。"
             "ただし `172.20.32.0/19` は**例外として拒否**すること。",
             [("deny", "172.20.32.0/19", None, None),
              ("permit", "172.20.0.0/16", None, 22)],
             lambda r: (within(r, "172.20.0.0/16") and r.prefixlen <= 22
                        and r != net("172.20.32.0/19"))))
    add(inst("EXCEPT", 2, "全経路許可（例外1件）",
             "すべての経路（デフォルトルートを含む）を許可せよ。"
             "ただし `10.99.99.99/32` は**例外として拒否**すること。",
             [("deny", "10.99.99.99/32", None, None),
              ("permit", "0.0.0.0/0", None, 32)],
             lambda r: r != net("10.99.99.99/32")))

    # --- SEQ: 挿入稽古（形式チェック課題・意味採点でなく seq 行 regex） -----
    p1, p2, p3 = rnd.sample([p for p in PREFIX_BATTERY if p != "0.0.0.0/0"], 3)
    add(inst("SEQ", 2, "seq 指定の行挿入",
             f"このリストは**定義済み**である（`seq 10 permit {p1}` と"
             f" `seq 30 permit {p2}` の2行）。既存の2行の**間**の `seq 20` に、"
             f"経路 `{p3}` そのもの（完全一致）を許可する行を**追加**せよ。"
             "既存行の削除・変更・リストの再作成や再採番は禁止。",
             [("permit", p1, None, None), ("permit", p3, None, None),
              ("permit", p2, None, None)],
             lambda r, p1=p1, p2=p2, p3=p3: r in (net(p1), net(p2), net(p3)),
             seq_params={"p1": p1, "p2": p2, "p3": p3}))
    return pool


def build_instances_aspath(rnd):
    pool = {}

    def add(i):
        pool.setdefault(i["template"], []).append(i)

    # --- A_LOCAL: ^$（自AS生成のみ） ----------------------------------------
    add(inst("A_LOCAL", 1, "ローカル生成（AS_PATH 空）のみ",
             "RT01 **自身が生成**した経路（AS_PATH が空の経路）のみを許可せよ。"
             "外部から受信した経路は一切許可しないこと。",
             [("permit", "^$")],
             lambda p: not p))

    # --- A_ORIGINDIRECT: ^X$ ------------------------------------------------
    for x in [65010, 65020, 65030, 65099]:
        add(inst("A_ORIGINDIRECT", 1, f"隣接 AS{x} 起源の直接受信のみ",
                 f"隣接 AS **{x}** から直接受信し、かつ **AS {x} 自身が起源**である"
                 "経路（AS_PATH に他の AS が一切現れない）のみを許可せよ。",
                 [("permit", f"^{x}$")],
                 lambda p, x=x: p == [x]))

    # --- A_VIA: _X_ ---------------------------------------------------------
    for x in [65100, 65200, 65300]:
        add(inst("A_VIA", 1, f"AS{x} 経由の全経路",
                 f"AS_PATH のどこかに **AS {x} を含む**経路（位置を問わない）を"
                 "すべて許可せよ。それ以外は許可しないこと。",
                 [("permit", f"_{x}_")],
                 lambda p, x=x: x in p))

    # --- A_FROMNBR: ^X_ -----------------------------------------------------
    for x in [65010, 65020, 65030, 65099]:
        add(inst("A_FROMNBR", 1, f"隣接 AS{x} から受信した全経路",
                 f"**隣接 AS {x} から受信した**経路（AS_PATH の先頭が {x}）を"
                 "すべて許可せよ（起源がどの AS かは問わない）。",
                 [("permit", f"^{x}_")],
                 lambda p, x=x: bool(p) and p[0] == x))

    # --- A_ORIGIN: _X$ ------------------------------------------------------
    for x in [65300, 65100, 65200]:
        add(inst("A_ORIGIN", 1, f"AS{x} 起源の全経路",
                 f"**AS {x} が起源**（AS_PATH の末尾が {x}）の経路をすべて許可せよ。"
                 "経由しているだけの経路は許可しないこと。",
                 [("permit", f"_{x}$")],
                 lambda p, x=x: bool(p) and p[-1] == x))

    # --- A_EITHER: _(X|Y)$（選択） ------------------------------------------
    for x, y in [(65100, 65200), (65200, 65300), (65100, 65300)]:
        add(inst("A_EITHER", 2, f"起源が AS{x} または AS{y}",
                 f"起源が **AS {x} または AS {y}** のいずれかである経路を"
                 "すべて許可せよ。それ以外は許可しないこと。",
                 [("permit", f"_({x}|{y})$")],
                 lambda p, x=x, y=y: bool(p) and p[-1] in (x, y)))

    # --- A_PREPEND: ^X(_X)+$（プリペンド検出） ------------------------------
    for x in [65010, 65030]:
        add(inst("A_PREPEND", 2, f"AS{x} のプリペンド経路のみ",
                 f"隣接 AS **{x}** が **AS パスプリペンド**を行って広告している経路"
                 f"（AS_PATH が {x} の**2回以上**の繰り返しだけで構成される）のみを"
                 f"許可せよ。プリペンド無しで AS {x} から直接受信している経路は"
                 "含めないこと。",
                 [("permit", f"^{x}(_{x})+$")],
                 lambda p, x=x: len(p) >= 2 and set(p) == {x}))

    # --- A_VIANOTORIGIN: deny _X$ + permit _X_（経由するが起源でない） ------
    for x in [65200, 65100]:
        add(inst("A_VIANOTORIGIN", 2, f"AS{x} を経由するが起源ではない",
                 f"**AS {x} を経由するが、AS {x} が起源ではない**経路のみを"
                 "許可せよ（トランジットとしてのみ {X} を通った経路の抽出）。"
                 .replace("{X}", str(x)),
                 [("deny", f"_{x}$"), ("permit", f"_{x}_")],
                 lambda p, x=x: x in p and p[-1] != x))

    # --- A_NOTFROM: deny ^X_ + permit .*（除外＋全許可の順序稽古） ----------
    for x in [65010, 65020, 65030]:
        add(inst("A_NOTFROM", 2, f"隣接 AS{x} 受信分を除く全経路",
                 f"**隣接 AS {x} から受信した経路を除く**、すべての経路"
                 "（RT01 自身が生成した経路を含む）を許可せよ。",
                 [("deny", f"^{x}_"), ("permit", ".*")],
                 lambda p, x=x: not (bool(p) and p[0] == x)))
    return pool


MANDATORY = {
    "prefix": {"mix": ["EXACT", "LE", "GE", "BAND", "FIX24", "SEQ"],
               "1": ["EXACT", "LE", "GE", "DEFAULT", "ANY"],
               "2": ["BAND", "FIX24", "EXCEPT", "SEQ"]},
    "aspath": {"mix": ["A_LOCAL", "A_ORIGINDIRECT", "A_VIA", "A_FROMNBR",
                       "A_ORIGIN", "A_VIANOTORIGIN"],
               "1": ["A_LOCAL", "A_ORIGINDIRECT", "A_VIA", "A_FROMNBR", "A_ORIGIN"],
               "2": ["A_EITHER", "A_PREPEND", "A_VIANOTORIGIN", "A_NOTFROM"]},
    "acl": {"mix": ["STD_NET", "EXT_HTTP", "NAMED_EXT_BLOCK", "EST", "ODD", "APPLY"],
            "1": ["STD_NET", "STD_HOSTDENY", "NAMED_STD", "EXT_HTTP",
                  "NAMED_EXT_BLOCK"],
            "2": ["EST", "ICMP", "RANGE", "ODD", "NEQ", "APPLY"]},
}

BUILDERS = {"prefix": build_instances_prefix, "aspath": build_instances_aspath,
            "acl": build_instances_acl}


def select_tasks(rnd, pool, count, tier, dojo):
    """テンプレ多様性を保って K 課題を選ぶ（必修テンプレ→残りを抽選）。"""
    cap = 2 if tier == "mix" else 3
    chosen = []
    for t in MANDATORY[dojo][tier]:
        chosen.append(rnd.choice(pool[t]))
    rest = [i for insts in pool.values() for i in insts
            if i not in chosen and (tier == "mix" or i["tier"] == int(tier))]
    rnd.shuffle(rest)
    for i in rest:
        if len(chosen) >= count:
            break
        if sum(1 for c in chosen if c["template"] == i["template"]) < cap:
            chosen.append(i)
    if len(chosen) < count:
        raise SystemExit(f"課題プール不足: {len(chosen)} < {count} (dojo={dojo} tier={tier})")
    chosen = chosen[:count]
    # 学習曲線: tier1 → tier2 の順、同 tier 内は seed シャッフル
    rnd.shuffle(chosen)
    chosen.sort(key=lambda i: i["tier"])
    return chosen


# ===========================================================================
# 期待集合＋セルフチェック（要件述語 vs 意味評価器の二重検証）
# ===========================================================================
def expected_sets(dojo, instance):
    if dojo == "prefix":
        keys = PREFIX_BATTERY
        by_pred = {p for p in keys if instance["predicate"](net(p))}
        by_list = {p for p in keys if eval_plist(instance["entries"], net(p))}
        allow_full = instance["template"] == "ANY"
    elif dojo == "aspath":
        keys = [b[0] for b in ASPATH_BATTERY]
        by_pred = {p for p, path, _ in ASPATH_BATTERY if instance["predicate"](path)}
        by_list = {p for p, path, _ in ASPATH_BATTERY
                   if eval_aspath_acl(instance["entries"], path)}
        # ★aspath は「全許可」課題を作らない（ACL未定義の filter-list が
        #   全表示になっても、除外集合が必ず非空なら誤PASSしない）
        allow_full = False
    else:  # acl: ベクタ battery を「要件述語」vs「acl_model 評価」で二重分類
        keys = [v["id"] for v in ACL_VECTORS]
        by_pred = {v["id"] for v in ACL_VECTORS if instance["predicate"](v)}
        by_list = {v["id"] for v in ACL_VECTORS
                   if acl_model.evaluate(instance["entries"], v)}
        allow_full = False
    assert by_pred == by_list, (
        f"要件述語と模範解答が不一致: {instance['label']}\n"
        f"  述語のみ: {sorted(by_pred - by_list)}\n  解答のみ: {sorted(by_list - by_pred)}")
    assert by_pred, f"期待集合が空: {instance['label']}"
    if not allow_full:
        assert by_pred != set(keys), f"除外集合が空: {instance['label']}"
    return (sorted(by_pred, key=keys.index),
            sorted(set(keys) - by_pred, key=keys.index))


def task_ident(dojo, k, instance):
    """課題 k の被定義リストの識別子（名前/番号）。"""
    if dojo == "prefix":
        return f"PL-{k}"
    if dojo == "aspath":
        return str(k)
    kind = instance["acl_kind"]
    if kind == "std_num":
        return str(10 + k)
    if kind == "ext_num":
        return str(100 + k)
    return f"DOJO-{k}"


def build_checks(dojo, k, ident, instance, points, expected, excluded):
    """課題 k の採点チェック（通常1・APPLY 課題のみ2）を返す。"""
    if dojo == "prefix" and instance["template"] == "SEQ":
        sp = instance["seq_params"]
        rx = {p: p.replace(".", r"\.") for p in sp.values()}
        return [{"name": f"課題{k}: {instance['label']} ({ident})",
                 "node": "RT01", "command": f"show ip prefix-list {ident}",
                 "raw": [{"regex": rf"{ident}: 3 entries"},
                         {"regex": rf"(?m)^\s*seq 10 permit {rx[sp['p1']]}\s*$"},
                         {"regex": rf"(?m)^\s*seq 20 permit {rx[sp['p3']]}\s*$"},
                         {"regex": rf"(?m)^\s*seq 30 permit {rx[sp['p2']]}\s*$"}],
                 "points": points}]
    if dojo == "acl":
        exp = set(expected)
        vectors = [{**v, "expect": "permit" if v["id"] in exp else "deny"}
                   for v in ACL_VECTORS]
        main = {"name": f"課題{k}: {instance['label']} (ACL {ident})",
                "node": "RT01", "command": f"show access-lists {ident}",
                "acl_vectors": {"acl": ident, "vectors": vectors}}
        if instance.get("form_raw"):
            main["raw"] = instance["form_raw"]
        apply_if = instance.get("apply_if")
        if not apply_if:
            main["points"] = points
            return [main]
        main["points"] = points // 2
        return [main,
                {"name": f"課題{k}: {instance['label']}（{apply_if} in 適用）",
                 "node": "RT01", "command": f"show ip interface {apply_if}",
                 "raw": [{"regex":
                          rf"(?m)^\s*Inbound\s+access list is {ident}\s*$"}],
                 "points": points - points // 2}]
    raw = ([{"regex": bgp_line_rx(p)} for p in expected]
           + [{"not_regex": bgp_line_rx(p)} for p in excluded])
    cmd = (f"show ip bgp prefix-list {ident}" if dojo == "prefix"
           else f"show ip bgp filter-list {ident}")
    label_id = ident if dojo == "prefix" else f"as-path ACL {ident}"
    return [{"name": f"課題{k}: {instance['label']} ({label_id})",
             "node": "RT01", "command": cmd, "raw": raw, "points": points}]


# ===========================================================================
# day0 initial（道場別）
# ===========================================================================
def render_rt01_prefix(preload_lines):
    L = ["! RT01 (TARGET) 初期構成 — prefix-list 道場",
         "interface Loopback0", f" ip address {LO['RT01']} 255.255.255.255", "!",
         "interface {{ links[0] }}",
         " description === to RT02 (FEEDER, AS65099) ===",
         f" ip address {LINK_NET}.1 255.255.255.252", " no shutdown", "!",
         f"router bgp {AS_TGT}",
         f" bgp router-id {LO['RT01']}",
         " bgp log-neighbor-changes",
         " no bgp default ipv4-unicast",
         f" neighbor {LINK_NET}.2 remote-as {AS_FEED}",
         " address-family ipv4",
         f"  neighbor {LINK_NET}.2 activate",
         " exit-address-family", "!"]
    if preload_lines:
        L += ["! SEQ 課題用の定義済みリスト（変更・再採番禁止）"] + preload_lines + ["!"]
    return L


def render_rt02_prefix():
    L = ["! RT02 (FEEDER, AS65099) — battery 広告装置（変更禁止）",
         "interface Loopback0", f" ip address {LO['RT02']} 255.255.255.255", "!",
         "interface {{ links[0] }}",
         " description === to RT01 (TARGET, AS65001) ===",
         f" ip address {LINK_NET}.2 255.255.255.252", " no shutdown", "!"]
    nets = [p for p in PREFIX_BATTERY if p != "0.0.0.0/0"]
    for p in nets:
        n = net(p)
        L.append(f"ip route {n.network_address} {n.netmask} Null0")
    L += ["!", f"router bgp {AS_FEED}",
          f" bgp router-id {LO['RT02']}",
          " bgp log-neighbor-changes",
          " no bgp default ipv4-unicast",
          f" neighbor {LINK_NET}.1 remote-as {AS_TGT}",
          " address-family ipv4",
          f"  neighbor {LINK_NET}.1 activate",
          f"  neighbor {LINK_NET}.1 default-originate"]
    for p in nets:
        n = net(p)
        L.append(f"  network {n.network_address} mask {n.netmask}")
    L += [" exit-address-family", "!"]
    return L


def _aspath_locals():
    return [b for b in ASPATH_BATTERY if b[2] is None]


def _aspath_feeds(sess=None):
    return [b for b in ASPATH_BATTERY
            if b[2] is not None and (sess is None or b[2] == sess)]


def render_rt01_aspath():
    L = ["! RT01 (TARGET) 初期構成 — as-path 道場",
         "interface Loopback0", f" ip address {LO['RT01']} 255.255.255.255", "!"]
    for s in ["S1", "S2", "S3"]:
        lo_name, lo_ip = ASPATH_SESSIONS[s]["rt01_lo"]
        L += [f"interface {lo_name}",
              f" description === eBGP peering source (to {ASPATH_SESSIONS[s]['as']}) ===",
              f" ip address {lo_ip} 255.255.255.255", "!"]
    L += ["interface {{ links[0] }}",
          " description === to RT02 (FEEDER) ===",
          f" ip address {LINK_NET}.1 255.255.255.252", " no shutdown", "!"]
    for s in ["S1", "S2", "S3"]:
        L.append(f"ip route {ASPATH_SESSIONS[s]['rt02_lo'][1]} 255.255.255.255 "
                 f"{LINK_NET}.2")
    for p, _, _ in _aspath_locals():
        n = net(p)
        L.append(f"ip route {n.network_address} {n.netmask} Null0")
    L += ["!", f"router bgp {AS_TGT}",
          f" bgp router-id {LO['RT01']}",
          " bgp log-neighbor-changes",
          " no bgp default ipv4-unicast"]
    for s in ["S0", "S1", "S2", "S3"]:
        info = ASPATH_SESSIONS[s]
        L.append(f" neighbor {info['nbr']} remote-as {info['as']}")
        if info["rt01_lo"]:
            L += [f" neighbor {info['nbr']} update-source {info['rt01_lo'][0]}",
                  f" neighbor {info['nbr']} ebgp-multihop 2"]
    L.append(" address-family ipv4")
    for s in ["S0", "S1", "S2", "S3"]:
        L.append(f"  neighbor {ASPATH_SESSIONS[s]['nbr']} activate")
    for p, _, _ in _aspath_locals():
        n = net(p)
        L.append(f"  network {n.network_address} mask {n.netmask}")
    L += [" exit-address-family", "!"]
    return L


def render_rt02_aspath():
    L = ["! RT02 (FEEDER, AS65099) — AS_PATH 合成 battery 広告装置（変更禁止）",
         "interface Loopback0", f" ip address {LO['RT02']} 255.255.255.255", "!"]
    for s in ["S1", "S2", "S3"]:
        lo_name, lo_ip = ASPATH_SESSIONS[s]["rt02_lo"]
        L += [f"interface {lo_name}",
              f" description === session source as AS{ASPATH_SESSIONS[s]['as']} ===",
              f" ip address {lo_ip} 255.255.255.255", "!"]
    L += ["interface {{ links[0] }}",
          " description === to RT01 (TARGET, AS65001) ===",
          f" ip address {LINK_NET}.2 255.255.255.252", " no shutdown", "!"]
    for s in ["S1", "S2", "S3"]:
        L.append(f"ip route {ASPATH_SESSIONS[s]['rt01_lo'][1]} 255.255.255.255 "
                 f"{LINK_NET}.1")
    for p, _, _ in _aspath_feeds():
        n = net(p)
        L.append(f"ip route {n.network_address} {n.netmask} Null0")
    L.append("!")
    # セッション別 outbound route-map: 担当 battery のみ許可＋prepend 合成
    #（他セッションの battery / RT01 から受けた経路の折返しは暗黙denyで遮断）
    for s in ["S0", "S1", "S2", "S3"]:
        seq = 10
        for p, path, _ in _aspath_feeds(s):
            tag = f"B{p.replace('.', '-').replace('/', '-')}"
            L.append(f"ip prefix-list PFX-{s}-{tag} seq 5 permit {p}")
            L.append(f"route-map RM-{s} permit {seq}")
            L.append(f" match ip address prefix-list PFX-{s}-{tag}")
            prepend = path[1:]
            if prepend:
                L.append(f" set as-path prepend {' '.join(str(a) for a in prepend)}")
            L.append("!")
            seq += 10
    L += [f"router bgp {AS_FEED}",
          f" bgp router-id {LO['RT02']}",
          " bgp log-neighbor-changes",
          " no bgp default ipv4-unicast"]
    for s in ["S0", "S1", "S2", "S3"]:
        info = ASPATH_SESSIONS[s]
        peer = (f"{LINK_NET}.1" if not info["rt02_lo"]
                else ASPATH_SESSIONS[s]["rt01_lo"][1])
        L.append(f" neighbor {peer} remote-as {AS_TGT}")
        if info["rt02_lo"]:
            L += [f" neighbor {peer} update-source {info['rt02_lo'][0]}",
                  f" neighbor {peer} ebgp-multihop 2",
                  f" neighbor {peer} local-as {info['as']} no-prepend replace-as"]
    L.append(" address-family ipv4")
    for s in ["S0", "S1", "S2", "S3"]:
        info = ASPATH_SESSIONS[s]
        peer = (f"{LINK_NET}.1" if not info["rt02_lo"]
                else ASPATH_SESSIONS[s]["rt01_lo"][1])
        L += [f"  neighbor {peer} activate",
              f"  neighbor {peer} route-map RM-{s} out"]
    for p, _, _ in _aspath_feeds():
        n = net(p)
        L.append(f"  network {n.network_address} mask {n.netmask}")
    L += [" exit-address-family", "!"]
    return L


def render_rt01_acl():
    L = ["! RT01 (TARGET) 初期構成 — ACL 道場",
         "interface Loopback0", f" ip address {LO['RT01']} 255.255.255.255", "!",
         "interface {{ links[0] }}",
         " description === to RT02 (TGEN) ===",
         f" ip address {LINK_NET}.1 255.255.255.252", " no shutdown", "!"]
    for ip in ACL_TGEN_LOOPS:
        L.append(f"ip route {ip} 255.255.255.255 {LINK_NET}.2")
    L.append("!")
    return L


def render_rt02_acl():
    L = ["! RT02 (TGEN) — 素振り用トラフィック発生装置（変更禁止）",
         "interface Loopback0", f" ip address {LO['RT02']} 255.255.255.255", "!"]
    for i, ip in enumerate(ACL_TGEN_LOOPS, 1):
        L += [f"interface Loopback{i}",
              f" description === test source {ip} ===",
              f" ip address {ip} 255.255.255.255", "!"]
    L += ["interface {{ links[0] }}",
          " description === to RT01 (TARGET) ===",
          f" ip address {LINK_NET}.2 255.255.255.252", " no shutdown", "!",
          f"ip route 0.0.0.0 0.0.0.0 {LINK_NET}.1", "!"]
    return L


# ===========================================================================
# 生成本体（write=False でセルフチェックのみ）
# ===========================================================================
def generate(dojo, seed, count, tier):
    rnd = random.Random(seed)
    pool = BUILDERS[dojo](rnd)
    tasks = select_tasks(rnd, pool, count, tier, dojo)
    base, rem = divmod(100, count)

    catalog, checks, preload = [], [], []
    global_lines, blocks = [], []          # solve 用（blocks = parents 付き）
    for idx, instance in enumerate(tasks, 1):
        points = base + (rem if idx == count else 0)
        expected, excluded = expected_sets(dojo, instance)
        ident = task_ident(dojo, idx, instance)
        checks += build_checks(dojo, idx, ident, instance, points,
                               expected, excluded)
        if dojo == "prefix":
            if instance["template"] == "SEQ":
                sp = instance["seq_params"]
                preload += [plist_line(ident, 10, ("permit", sp["p1"], None, None)),
                            plist_line(ident, 30, ("permit", sp["p2"], None, None))]
                lines = [plist_line(ident, 20, ("permit", sp["p3"], None, None))]
            else:
                lines = [plist_line(ident, (i + 1) * 5, e)
                         for i, e in enumerate(instance["entries"])]
            global_lines += lines
        elif dojo == "aspath":
            lines = [f"ip as-path access-list {ident} {action} {rx}"
                     for action, rx in instance["entries"]]
            global_lines += lines
        else:
            kind = instance["acl_kind"]
            for i, e in enumerate(instance["entries"]):
                e["seq"] = (i + 1) * 10        # セルフチェック評価順の明示
            if kind in ("std_num", "ext_num"):
                lines = [f"access-list {ident} {acl_cli(e)}"
                         for e in instance["entries"]]
                global_lines += lines
            else:
                parents = ("ip access-list standard " + ident
                           if kind == "named_std"
                           else "ip access-list extended " + ident)
                body = [acl_cli(e) for e in instance["entries"]]
                blocks.append({"parents": parents, "lines": body})
                lines = [parents] + [" " + b for b in body]
            if instance.get("apply_if"):
                blocks.append({"parents": f"interface {instance['apply_if']}",
                               "lines": [f"ip access-group {ident} in"]})
                lines += [f"interface {instance['apply_if']}",
                          f" ip access-group {ident} in"]
        catalog.append({"task": idx, "list": ident,
                        "template": instance["template"],
                        "tier": instance["tier"], "label": instance["label"],
                        "requirement": instance["text"],
                        "solution_lines": lines,
                        "expected": expected, "excluded": excluded})
    if global_lines:
        blocks.insert(0, {"parents": None, "lines": global_lines})
    return {"tasks": tasks, "catalog": catalog, "checks": checks,
            "sol_blocks": blocks, "preload": preload}


def prereq_checks(dojo):
    """(前提) 0点チェック: battery 受信の診断用。"""
    link_rx = rf"{LINK_NET.replace('.', chr(92) + '.')}\.2"
    if dojo == "prefix":
        n = len(PREFIX_BATTERY)
        return [{"name": f"(前提) RT02 から battery {n}経路を受信済み（0点・診断用）",
                 "node": "RT01", "command": "show ip bgp summary",
                 "raw": [{"regex": rf"(?m)^{link_rx}\s+4\s+{AS_FEED}\s.*\s{n}\s*$"}],
                 "points": 0}]
    if dojo == "aspath":
        raw = []
        for s in ["S0", "S1", "S2", "S3"]:
            info = ASPATH_SESSIONS[s]
            nbr_rx = info["nbr"].replace(".", r"\.")
            cnt = len(_aspath_feeds(s))
            raw.append({"regex": rf"(?m)^{nbr_rx}\s+4\s+{info['as']}\s.*\s{cnt}\s*$"})
        return [{"name": "(前提) FEEDER 4セッション確立・battery 受信済み（0点・診断用）",
                 "node": "RT01", "command": "show ip bgp summary",
                 "raw": raw, "points": 0}]
    return [{"name": "(前提) TGEN 疎通（0点・診断用）",
             "node": "RT01", "command": f"ping {LINK_NET}.2 repeat 5",
             "raw": [{"regex": "Success rate is [1-9]"}], "points": 0}]


TASKMD = {
    "prefix": {
        "title": "ip prefix-list 道場",
        "listname": "リスト名",
        "intro": """上流ルータ **RT02 (AS65099)** が多数の経路（テスト用 battery）を eBGP で広告している。
あなたは **RT01 (AS65001)** 上で、下記 {count} 個の小課題それぞれについて
**指定された名前の ip prefix-list を1本定義する**。それだけの問題である。

- prefix-list は**定義するだけ**でよい（ネイバーへの適用は不要）。
- 採点は書き方（seq 番号・同義表現）ではなく「**何を通し、何を落とすか**」の
  意味的一致で行う（1課題 = {pts}点・部分点なし）。
- seed を変えて繰り返し生成できる。体で覚えるまで反復すること。

```
  RT01 (TARGET, AS65001)  Lo0=1.1.1.1
    | E0/0  {link}.1
    | E0/0  {link}.2
  RT02 (FEEDER, AS65099)  Lo0=2.2.2.2  ← battery 広告装置(変更禁止)
```""",
        "practice": """- 広告されている battery 全体: `show ip bgp`
- 自分のリストの効果を**その場で確認**: `show ip bgp prefix-list PL-x`
  （read-only。BGP テーブルへの適用表示であり、セッションに影響しない。
  `clear ip bgp` は不要）
- 定義内容の確認: `show ip prefix-list`""",
        "rules": """1. **RT02 (FEEDER) の設定変更は禁止**（show による状態確認は可）。
2. RT01 の **BGP・インタフェース・ルーティング設定の変更は禁止**
   （作業は ip prefix-list の定義のみ）。
3. 定義済みリストがある課題では、**既存行の削除・変更・再採番は禁止**。
4. リスト名は課題の指定どおり（`PL-1`〜`PL-{count}`）。大文字小文字も一致させること。""",
    },
    "aspath": {
        "title": "as-path access-list 道場",
        "listname": "リスト番号",
        "intro": """上流ルータ **RT02 (FEEDER)** はテスト用の経路発生装置で、RT01 との間に
**並列の eBGP セッションを4本**張り、それぞれ別の隣接 AS
（**AS65099 / AS65010 / AS65020 / AS65030**）として振る舞いながら、
多彩な **AS_PATH** を持つ経路群（battery）を広告している。
パス上には中継/起源 AS として **AS65100 / AS65200 / AS65300** が現れる。
また RT01 自身もローカル経路（AS_PATH 空）を2本 BGP に注入している。

あなたは **RT01 (AS65001)** 上で、下記 {count} 個の小課題それぞれについて
**指定された番号の ip as-path access-list を1本定義する**。それだけの問題である。

- as-path access-list は**定義するだけ**でよい（ネイバーへの適用は不要）。
- 採点は正規表現の書き方ではなく「**どの経路を通し、どの経路を落とすか**」の
  意味的一致で行う（1課題 = {pts}点・部分点なし）。

```
  RT01 (TARGET, AS65001)  Lo0=1.1.1.1  ＋ローカル経路×2 (AS_PATH 空)
    ||||  ← 並列 eBGP×4 (直結 + loopback間×3)
  RT02 (FEEDER)  ← AS65099/65010/65020/65030 として battery 広告(変更禁止)
```""",
        "practice": """- battery 全体と AS_PATH の観察: `show ip bgp`（Path 列を読む）
- 自分のリストの効果を**その場で確認**: `show ip bgp filter-list <番号>`
  （read-only。BGP テーブルへの適用表示であり、セッションに影響しない）
- 正規表現の素振り（リストを定義せず試せる）: `show ip bgp regexp <正規表現>`""",
        "rules": """1. **RT02 (FEEDER) の設定変更は禁止**（show による状態確認は可）。
2. RT01 の **BGP・インタフェース・ルーティング設定の変更は禁止**
   （作業は ip as-path access-list の定義のみ）。
3. リスト番号は課題の指定どおり（`1`〜`{count}`）に一致させること。""",
    },
    "acl": {
        "title": "ACL 道場",
        "listname": "ACL 番号/名前",
        "intro": """ルータ **RT01 (TARGET)** の先に、テスト用ホスト群を模した **RT02 (TGEN)** が
接続されている。TGEN は以下のテスト送信元アドレスをループバックとして持つ
（LAN-A=`10.30.1.0/24` / LAN-B=`10.30.2.0/24` / サーバ=`172.22.5.0/24` /
外部=`203.0.113.0/24` / 検証用=`10.40.0.0/16`）:

| 役割 | アドレス |
|------|---------|
| LAN-A ホスト | 10.30.1.10, 10.30.1.99 |
| LAN-B ホスト | 10.30.2.20 |
| Web / DNS サーバ | 172.22.5.10 / 172.22.5.20 |
| 外部ホスト | 203.0.113.50 |
| 検証用 (10.40.x.5) | x = 1, 2, 3, 4 |

あなたは **RT01** 上で、下記 {count} 個の小課題それぞれについて
**指定された番号/名前・種別の ACL を1本定義する**（IF への適用を求める課題は
その旨明記される。それ以外は**定義のみ**でよい）。

- 採点は書き方（seq・host/any の表記・ポート名か番号か）ではなく、
  **テストパケット群を何が通り何が落ちるか**の意味的一致で行う
  （1課題 = {pts}点・部分点なし。採点は `show access-lists` の内容評価で、
  ヒットカウンタや実トラフィックには依存しない）。

```
  RT01 (TARGET)  Lo0=1.1.1.1
    | E0/0  {link}.1
    | E0/0  {link}.2
  RT02 (TGEN)  Lo0=2.2.2.2  ← テスト送信元ループバック×10(変更禁止)
```""",
        "practice": """- 定義内容の確認 = 採点対象: `show access-lists`（種別・seq・正規化表記が見える）
- 体感したい場合は ACL を RT01 の IF（例: E0/0 in）へ**仮適用**し、RT02 から
  `ping 1.1.1.1 source <テスト送信元>` → `show access-lists` の **matches
  カウンタ**で確認できる（ping で試せるのは ICMP の課題のみ。仮適用は
  採点に影響しないが、確認後は外しておくのが行儀）。""",
        "rules": """1. **RT02 (TGEN) の設定変更は禁止**（show・ping の実行は可）。
2. RT01 は **ACL の定義（と、適用を求める課題での適用）以外の設定変更禁止**
   （インタフェース IP・ルーティングに触らない）。
3. ACL の番号/名前・種別（標準/拡張・番号付き/named）は課題の指定に**厳密に一致**させること。""",
    },
}


def write_problem(repo, dojo, seed, count, tier, gen):
    prob_id = f"GEN-DOJO-{dojo.upper()}-{seed}"
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    t = TASKMD[dojo]

    problem = {"id": prob_id,
               "title": f"{t['title']} (seed={seed}, {count}課題)",
               "exam": "ENCOR" if dojo == "acl" else "ENARSI",
               "topics": [dojo, "acl" if dojo == "acl" else "bgp",
                          "filtering", "dojo", "generated"],
               "difficulty": DIFFICULTY[tier], "topology": "generated",
               "target_nodes": ["RT01", "RT02"], "points": 100, "access": "ssh",
               "lab": {"links": [{"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0}],
                       "positions": {"RT01": [-150, 0], "RT02": [150, 0]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_list_dojo.py) dojo={dojo} seed={seed} "
                f"count={count} tier={tier}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    if dojo == "prefix":
        rt01, rt02 = render_rt01_prefix(gen["preload"]), render_rt02_prefix()
    elif dojo == "aspath":
        rt01, rt02 = render_rt01_aspath(), render_rt02_aspath()
    else:
        rt01, rt02 = render_rt01_acl(), render_rt02_acl()
    with open(f"{pdir}/initial/RT01.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(rt01) + "\n")
    with open(f"{pdir}/initial/RT02.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(rt02) + "\n")

    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"},
               "checks": prereq_checks(dojo) + gen["checks"]}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_list_dojo.py) dojo={dojo} seed={seed}\n"
                "# 1課題=1チェック(all-or-nothing)。期待/除外 regex は battery 全件から決定的に生成。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    rows = "\n".join(
        f"### 課題{c['task']} — {t['listname']} `{c['list']}`\n\n> {c['requirement']}\n"
        for c in gen["catalog"])
    task = f"""# 問題 {prob_id} : {t['title']}（{count}本ノック・難易度{DIFFICULTY[tier]}）

## この問題について（型稽古）

{t['intro'].format(count=count, pts=100 // count, link=LINK_NET)}

## 素振り（自己確認）のしかた

{t['practice']}

## 課題（{t['listname']}は厳密に一致させること）

{rows}
## 遵守事項

{t['rules'].replace('{count}', str(count))}

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。CML コンソールでも可。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)

    # solution.json は solve_generated.yml が読むためパック直下（blocks ネスト必須）
    with open(f"{pdir}/solution.json", "w", encoding="utf-8") as f:
        json.dump({"nodes": {},
                   "filters": [{"node": "RT01", "blocks": gen["sol_blocks"]}]},
                  f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/catalog.json", "w", encoding="utf-8") as f:
        json.dump(gen["catalog"], f, ensure_ascii=False, indent=2)

    md = [f"# {prob_id} 模範解答", "",
          "採点は意味的一致（同値な書き方は他にもある）。以下は最小の模範例。", ""]
    for c in gen["catalog"]:
        md += [f"## 課題{c['task']} `{c['list']}` — {c['label']}", "",
               "```", *c["solution_lines"], "```", "",
               f"- 通す ({len(c['expected'])}): " + ", ".join(c["expected"]),
               f"- 落とす ({len(c['excluded'])}): " + ", ".join(c["excluded"]), ""]
    with open(f"{pdir}/solution/solution.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"wrote problems/{prob_id} : count={count} tier={tier} "
          f"templates={[c['template'] for c in gen['catalog']]}")


def validate_batteries():
    nets = [net(p) for p in PREFIX_BATTERY]
    assert len(set(nets)) == len(nets) == 36
    keys = [b[0] for b in ASPATH_BATTERY]
    assert len(set(keys)) == len(keys) == 21
    for p, path, sess in ASPATH_BATTERY:
        net(p)  # strict 妥当性
        if sess is None:
            assert path == []
        else:
            assert path and path[0] == ASPATH_SESSIONS[sess]["as"], \
                f"{p}: path 先頭がセッションASでない"
    vids = [v["id"] for v in ACL_VECTORS]
    assert len(set(vids)) == len(vids) == 26
    for v in ACL_VECTORS:
        assert v["proto"] in ("tcp", "udp", "icmp")
        if v["proto"] in ("tcp", "udp"):
            assert v.get("sport") and v.get("dport")
        else:
            assert v.get("icmp_type") is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--dojo", choices=["prefix", "aspath", "acl"], default="prefix")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--tier", choices=["1", "2", "mix"], default="mix")
    ap.add_argument("--selfcheck", type=int, metavar="N",
                    help="seed 1..N を全 dojo×tier で生成検品（ファイル出力なし）")
    a = ap.parse_args()
    validate_batteries()

    if a.selfcheck:
        for seed in range(1, a.selfcheck + 1):
            for dojo in ["prefix", "aspath", "acl"]:
                for tier in ["1", "2", "mix"]:
                    generate(dojo, seed, a.count, tier)
        print(f"selfcheck OK: seeds 1..{a.selfcheck} × dojo(prefix,aspath,acl) "
              f"× tier(1,2,mix) × count={a.count}")
        return
    if a.seed is None:
        raise SystemExit("--seed が必要（または --selfcheck N）")
    write_problem(a.repo, a.dojo, a.seed, a.count, a.tier,
                  generate(a.dojo, a.seed, a.count, a.tier))


if __name__ == "__main__":
    main()
