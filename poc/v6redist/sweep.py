#!/usr/bin/env python3
"""BL-098 PoC: OSPFv3 ⇄ EIGRPv6 相互再配送のエッジ挙動スイープ。

_POC-V6REDIST (C1-RA-RT-C-RB-C2) に SSH し、主に RT-C の設定を組み替えながら
両ドメインのクライアント/中継が受け取る経路と到達性を観測する。
各シナリオは 基線→delta 適用→収束待ち→観測→revert。

使い方: sweep.py [シナリオ名...]   (無指定=全部)
        sweep.py --list
"""
import re
import sys
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-V6REDIST"
OUT = Path(__file__).resolve().parent / "results-raw.md"
USER, PW = "SUZUKI", "CCNP"

# 基線の関心プレフィクス
P_C1LAN = "2001:DB8:2:1::/64"      # C1 の LAN (OSPF 側)
P_C2LAN = "2001:DB8:1A:A::/64"     # C2 の LAN (EIGRP 側)
P_OTRAN = "2001:DB8:1:1::/64"      # RT-C--RA トランジット (OSPF 側)
P_ETRAN = "2001:DB8:A:A::/64"      # RT-C--RB トランジット (EIGRP 側)
C1_ADDR = "2001:DB8:2:1::2"
C2_ADDR = "2001:DB8:1A:A::2"


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


def session(ip):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(ip, username=USER, password=PW, look_for_keys=False,
                allow_agent=False, timeout=30)
    sh = cli.invoke_shell(width=511)
    _expect(sh, r"[>#]\s*$")
    sh.send("terminal length 0\n")
    _expect(sh, r"#\s*$")
    return cli, sh


def _expect(sh, pat, timeout=60):
    buf, t0 = "", time.time()
    while time.time() - t0 < timeout:
        if sh.recv_ready():
            buf += sh.recv(65535).decode("utf-8", "replace")
            last = buf.splitlines()[-1] if buf.splitlines() else ""
            if re.search(pat, last):
                return buf
        else:
            time.sleep(0.1)
    raise TimeoutError(f"prompt timeout; tail={buf[-400:]!r}")


def run(sh, cmd, timeout=90):
    sh.send(cmd + "\n")
    out = _expect(sh, r"(?:\(config[^)]*\))?#\s*$", timeout)
    lines = out.replace("\r", "").splitlines()
    return "\n".join(lines[1:-1] if len(lines) > 1 else lines)


def conf(sh, lines):
    run(sh, "configure terminal")
    for ln in lines:
        run(sh, ln)
    run(sh, "end")


# ---------------------------------------------------------------- 観測

ROUTE_RE = re.compile(
    r"^(C|L|S|D|EX|O|OI|OE1|OE2|ON1|ON2|B|R)\s+(\S+)\s+\[(\d+)/(\d+)\]", re.M)


def routes(sh):
    """show ipv6 route → {prefix: (code, ad, metric)}"""
    txt = run(sh, "show ipv6 route")
    out = {}
    for m in ROUTE_RE.finditer(txt):
        code, pfx, ad, met = m.groups()
        out[pfx] = (code, int(ad), int(met))
    return out


def fmt(rt, pfxs):
    parts = []
    for p in pfxs:
        v = rt.get(p)
        parts.append(f"{p}={'—' if v is None else f'{v[0]} [{v[1]}/{v[2]}]'}")
    return " / ".join(parts)


def ping(sh, dst, src=None, repeat=3):
    cmd = f"ping {dst} repeat {repeat}"
    if src:
        cmd += f" source {src}"
    txt = run(sh, cmd, timeout=90)
    if "No valid route" in txt:
        return "NOROUTE"
    m = re.search(r"Success rate is (\d+) percent", txt)
    return f"{m.group(1)}%" if m else "?"


def observe(S, note=""):
    """全ノードの関心経路と C1↔C2 到達性を1行にまとめる。

    ★`RT-C redist` 行は必ず出す: `redistribute` は再発行でマージされるため、
    「意図した delta が本当に効いているか」は running-config で確認しないと誤読する
    (実測 2026-08-08: route-map 節なしで再発行しても route-map は外れない)。
    """
    rec = {}
    rec["RT-C redist"] = " ; ".join(
        l.strip() for l in run(
            S["RT-C"],
            "show running-config | include ^ *redistribute|^ *default-metric"
        ).splitlines() if l.strip())
    rec["C1"] = fmt(routes(S["C1"]), [P_C2LAN, P_ETRAN, "::/0"])
    rec["RA"] = fmt(routes(S["RA"]), [P_C2LAN, P_ETRAN, "::/0"])
    rec["RB"] = fmt(routes(S["RB"]), [P_C1LAN, P_OTRAN, "::/0"])
    rec["C2"] = fmt(routes(S["C2"]), [P_C1LAN, P_OTRAN, "::/0"])
    # ★source を付けない: 付けると「経路なし」が単なるタイムアウト表示に化けるため
    #   (実測 2026-08-08: no source→`% No valid route`, source 指定→`..`)
    rec["ping C1->C2"] = ping(S["C1"], C2_ADDR)
    rec["ping C2->C1"] = ping(S["C2"], C1_ADDR)
    return rec


def emit(name, title, delta, rec, extra=None):
    lines = [f"### {name} — {title}", ""]
    if delta:
        lines += ["適用 delta:", "```"] + delta + ["```", ""]
    lines.append("| 観測点 | 値 |")
    lines.append("|---|---|")
    for k, v in rec.items():
        lines.append(f"| {k} | `{v}` |")
    if extra:
        lines += ["", "補足:", "```", extra.strip(), "```"]
    lines.append("")
    with OUT.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---------------------------------------------------------------- 基線

BASE_RTC = [
    "router eigrp NAMED",
    " address-family ipv6 unicast autonomous-system 5400",
    "  af-interface Ethernet0/0",
    "   shutdown",
    "  exit-af-interface",
    "  topology base",
    "   redistribute ospf 544 match internal metric 10000 100 255 1 1500"
    " route-map OMAP01 include-connected",
    "  exit-af-topology",
    " exit-address-family",
    "exit",
    "router ospfv3 544",
    " address-family ipv6 unicast",
    "  redistribute eigrp 5400 route-map EMAP01 include-connected",
    " exit-address-family",
    "exit",
    "no ipv6 prefix-list E5400",
    "no ipv6 prefix-list O544",
    "ipv6 prefix-list E5400 seq 5 permit 2001:DB8:A:A::/64",
    "ipv6 prefix-list O544 seq 5 permit 2001:DB8:1:1::/64",
    "no route-map OMAP01",
    "no route-map EMAP01",
    "route-map OMAP01 permit 10",
    " match ipv6 address prefix-list O544",
    "exit",
    "route-map EMAP01 permit 10",
    " match ipv6 address prefix-list E5400",
    "exit",
]

# 基線に戻すために「まず消す」もの(シナリオが足したものを取り除く)
CLEAN_RTC = [
    "no router eigrp NAMED",
    "no router ospfv3 544",
    "no ipv6 route ::/0 Null0",
    "no route-map GHOST",
]

BASE_OTHERS = {
    "RA": ["router ospfv3 544", " address-family ipv6 unicast",
           "  no redistribute static", " exit-address-family", "exit",
           "no ipv6 route 2001:DB8:9:9::/64 Null0",
           "no ipv6 route 2001:DB8:1A:A::/64 2001:DB8:1:1::1"],
    "RB": ["no ipv6 route 2001:DB8:2:1::/64 2001:DB8:A:A::1"],
    "C1": ["no ipv6 route ::/0 2001:DB8:2:1::1"],
    "C2": ["no ipv6 route ::/0 2001:DB8:1A:A::1"],
}


def restore(S):
    """RT-C を素にしてから基線を焼き直す。他ノードも足し物を除去。

    ★`no router ospfv3 544` は **インタフェースの `ipv6 ospf 544 area 0` も道連れに消す**
    (実測 2026-08-08)。プロセス再作成のあとに IF 側を明示で焼き直すこと。
    """
    conf(S["RT-C"], CLEAN_RTC)
    conf(S["RT-C"], ["router eigrp NAMED",
                     " address-family ipv6 unicast autonomous-system 5400",
                     "  eigrp router-id 1.1.1.1",
                     " exit-address-family", "exit",
                     "router ospfv3 544", " router-id 2.2.2.2", "exit",
                     "interface Ethernet0/0",
                     " ipv6 ospf 544 area 0",
                     "exit"])
    conf(S["RT-C"], BASE_RTC)
    for n, lines in BASE_OTHERS.items():
        conf(S[n], lines)
    settle(S)


def clear_ospf(sh):
    """`clear ipv6 ospf process` は [yes/no] 確認を出す。確認に応答してから戻る。"""
    sh.send("clear ipv6 ospf process\n")
    time.sleep(1.5)
    sh.send("y\n")
    _expect(sh, r"#\s*$", 60)


def settle(S, secs=30):
    """再配送/隣接の収束待ち。EIGRP・OSPF 双方を clear して待つ。"""
    run(S["RT-C"], "clear ipv6 eigrp neighbors", timeout=30)
    clear_ospf(S["RT-C"])
    time.sleep(secs)


# ---------------------------------------------------------------- シナリオ

# ユーザラボ「IPv6redistribute01」実測との突き合わせ用(2026-08-08 read-only probe)
USER_LAB = {
    "C1": {P_C2LAN: None, P_ETRAN: ("OE2", 110, 20)},
    "RA": {P_C2LAN: None, P_ETRAN: ("OE2", 110, 20)},
    "RB": {P_C1LAN: None, P_OTRAN: ("EX", 170, 1536000)},
    "C2": {P_C1LAN: None, P_OTRAN: ("EX", 170, 2048000)},
}


def s_base(S):
    restore(S)
    diffs = []
    for node, want in USER_LAB.items():
        got = routes(S[node])
        for pfx, exp in want.items():
            if got.get(pfx) != exp:
                diffs.append(f"{node} {pfx}: want={exp} got={got.get(pfx)}")
    p1, p2 = ping(S["C1"], C2_ADDR), ping(S["C2"], C1_ADDR)
    for lbl, v in (("C1->C2", p1), ("C2->C1", p2)):
        if v != "NOROUTE":
            diffs.append(f"ping {lbl}: want=NOROUTE got={v}")
    verdict = "✅ ユーザラボ実測と完全一致" if not diffs else \
        "❌ 不一致:\n  " + "\n  ".join(diffs)
    extra = verdict + "\n\n" + run(S["RT-C"], "show ipv6 eigrp topology") + "\n" + \
        run(S["RT-C"], "show ipv6 ospf database | begin Type-5")
    emit("B0", "基線(ユーザラボ複製) — 双方向とも route-map でトランジットのみ通過",
         [], observe(S), extra)
    print(verdict)


def s_e1_rmap_off(S):
    """E1: 両方向の route-map を外す(metric はそのまま)。"""
    restore(S)
    d = ["router eigrp NAMED",
         " address-family ipv6 unicast autonomous-system 5400",
         "  topology base",
         "   no redistribute ospf 544",
         "   redistribute ospf 544 match internal metric 10000 100 255 1 1500"
         " include-connected",
         "  exit-af-topology", " exit-address-family", "exit",
         "router ospfv3 544", " address-family ipv6 unicast",
         "  no redistribute eigrp 5400",
         "  redistribute eigrp 5400 include-connected",
         " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    emit("E1", "route-map を両方向とも外す(metric 維持・★no を前置)", d, observe(S))


def s_e2_pl_add(S):
    """E2: prefix-list に客先 LAN を追記(トランジットは残す)。"""
    restore(S)
    d = [f"ipv6 prefix-list O544 seq 10 permit {P_C1LAN}",
         f"ipv6 prefix-list E5400 seq 10 permit {P_C2LAN}"]
    conf(S["RT-C"], d)
    settle(S)
    emit("E2", "prefix-list に客先 LAN を追記(トランジットも残る)", d, observe(S))


def s_e3_pl_replace(S):
    """E3: prefix-list を客先 LAN のみに置換(トランジットを隠す)。
    ★include-connected 由来の経路に route-map が効くかの決定実験。"""
    restore(S)
    d = ["no ipv6 prefix-list O544", "no ipv6 prefix-list E5400",
         f"ipv6 prefix-list O544 seq 5 permit {P_C1LAN}",
         f"ipv6 prefix-list E5400 seq 5 permit {P_C2LAN}"]
    conf(S["RT-C"], d)
    settle(S)
    emit("E3", "★prefix-list を客先LANのみに置換 — include-connected は route-map に従うか",
         d, observe(S))


def s_e4_no_incl(S):
    """E4: include-connected を外す(prefix-list は基線=トランジット許可のまま)。"""
    restore(S)
    d = ["router eigrp NAMED",
         " address-family ipv6 unicast autonomous-system 5400",
         "  topology base",
         "   no redistribute ospf 544",
         "   redistribute ospf 544 match internal metric 10000 100 255 1 1500"
         " route-map OMAP01",
         "  exit-af-topology", " exit-address-family", "exit",
         "router ospfv3 544", " address-family ipv6 unicast",
         "  no redistribute eigrp 5400",
         "  redistribute eigrp 5400 route-map EMAP01",
         " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    emit("E4", "include-connected を外す(prefix-list は基線のまま)", d, observe(S))


def s_e5_no_metric(S):
    """E5: ★EIGRP 側 redistribute から metric を落とす(route-map は全開)。"""
    restore(S)
    d = ["router eigrp NAMED",
         " address-family ipv6 unicast autonomous-system 5400",
         "  topology base",
         "   no redistribute ospf 544",
         "   redistribute ospf 544 include-connected",
         "  exit-af-topology", " exit-address-family", "exit",
         "router ospfv3 544", " address-family ipv6 unicast",
         "  redistribute eigrp 5400 include-connected",
         " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    extra = run(S["RT-C"], "show ipv6 protocols | section eigrp")
    emit("E5", "★EIGRP 側 redistribute の metric 省略(route-map なし)", d,
         observe(S), extra)


def s_e6_default_metric(S):
    """E6: metric 省略 + topology base の default-metric で救えるか。"""
    restore(S)
    d = ["router eigrp NAMED",
         " address-family ipv6 unicast autonomous-system 5400",
         "  topology base",
         "   no redistribute ospf 544",
         "   default-metric 10000 100 255 1 1500",
         "   redistribute ospf 544 include-connected",
         "  exit-af-topology", " exit-address-family", "exit",
         "router ospfv3 544", " address-family ipv6 unicast",
         "  redistribute eigrp 5400 include-connected",
         " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    emit("E6", "metric 省略 + default-metric で補う", d, observe(S))


def s_e7_pl_undef(S):
    """E7: 参照 prefix-list を未定義にする(route-map は在る)。"""
    restore(S)
    d = ["no ipv6 prefix-list O544", "no ipv6 prefix-list E5400"]
    conf(S["RT-C"], d)
    settle(S)
    emit("E7", "★参照 prefix-list を未定義に(route-map は在る) — 全許可か全拒否か",
         d, observe(S))


def s_e8_rmap_undef(S):
    """E8: 存在しない route-map を参照させる。"""
    restore(S)
    d = ["router eigrp NAMED",
         " address-family ipv6 unicast autonomous-system 5400",
         "  topology base",
         "   no redistribute ospf 544",
         "   redistribute ospf 544 match internal metric 10000 100 255 1 1500"
         " route-map GHOST include-connected",
         "  exit-af-topology", " exit-address-family", "exit",
         "router ospfv3 544", " address-family ipv6 unicast",
         "  no redistribute eigrp 5400",
         "  redistribute eigrp 5400 route-map GHOST include-connected",
         " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    emit("E8", "★未定義 route-map を参照 — 全拒否か全許可か", d, observe(S))


def s_e9_afif_up(S):
    """E9: EIGRP の af-interface E0/0 shutdown を解除。"""
    restore(S)
    d = ["router eigrp NAMED",
         " address-family ipv6 unicast autonomous-system 5400",
         "  af-interface Ethernet0/0",
         "   no shutdown",
         "  exit-af-interface", " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    emit("E9", "EIGRP af-interface E0/0 の shutdown 解除 — 1:1::/64 は D(内部)になるか",
         d, observe(S))


def s_e10_match_ext(S):
    """E10: OSPF 側に外部経路を作り、match internal / internal external を比較。"""
    restore(S)
    # RA に static → OSPF へ再配送(RT-C から見て OE2 になる)
    d_ra = ["ipv6 route 2001:DB8:9:9::/64 Null0",
            "router ospfv3 544", " address-family ipv6 unicast",
            "  redistribute static", " exit-address-family", "exit"]
    conf(S["RA"], d_ra)
    # 通すために prefix-list も広げる
    d = ["ipv6 prefix-list O544 seq 20 permit 2001:DB8:9:9::/64"]
    conf(S["RT-C"], d)
    settle(S)
    rec1 = {"RT-C 9:9::/64": fmt(routes(S["RT-C"]), ["2001:DB8:9:9::/64"]),
            "RB 9:9::/64": fmt(routes(S["RB"]), ["2001:DB8:9:9::/64"])}
    d2 = ["router eigrp NAMED",
          " address-family ipv6 unicast autonomous-system 5400",
          "  topology base",
          "   no redistribute ospf 544",
          "   redistribute ospf 544 match internal external"
          " metric 10000 100 255 1 1500 route-map OMAP01 include-connected",
          "  exit-af-topology", " exit-address-family", "exit"]
    conf(S["RT-C"], d2)
    settle(S)
    rec1["→ match internal external 後 RB 9:9::/64"] = fmt(
        routes(S["RB"]), ["2001:DB8:9:9::/64"])
    emit("E10", "★match internal は OSPF 外部(OE2)を落とすか", d_ra + d + d2, rec1)


def s_e11_default_ospf(S):
    """E11: OSPFv3 default-information originate (always 有無)。"""
    restore(S)
    d = ["router ospfv3 544", " address-family ipv6 unicast",
         "  default-information originate", " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    rec = {"C1 ::/0 (always なし)": fmt(routes(S["C1"]), ["::/0"])}
    d2 = ["router ospfv3 544", " address-family ipv6 unicast",
          "  default-information originate always",
          " exit-address-family", "exit"]
    conf(S["RT-C"], d2)
    settle(S)
    rec["C1 ::/0 (always あり)"] = fmt(routes(S["C1"]), ["::/0"])
    rec["RA ::/0"] = fmt(routes(S["RA"]), ["::/0"])
    rec["ping C1->C2"] = ping(S["C1"], C2_ADDR)
    emit("E11", "★OSPFv3 default-information originate の always 要否", d + d2, rec)


def s_e12_default_eigrp(S):
    """E12: EIGRP 側にデフォルトを配る(summary-address ::/0)。"""
    restore(S)
    d = ["router ospfv3 544", " address-family ipv6 unicast",
         "  default-information originate always",
         " exit-address-family", "exit",
         "router eigrp NAMED",
         " address-family ipv6 unicast autonomous-system 5400",
         "  af-interface Ethernet0/1",
         "   summary-address ::/0",
         "  exit-af-interface", " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    rec = observe(S)
    rec["RT-C ::/0"] = fmt(routes(S["RT-C"]), ["::/0"])
    rec["RT-C C1LAN"] = fmt(routes(S["RT-C"]), [P_C1LAN])
    emit("E12", "★EIGRP af-interface summary-address ::/0 でデフォルト配布"
         "(+OSPF 側 default originate always)", d, rec)


def s_e13_static_mid(S):
    """E13: RA/RB に静的だけ置く(IGP へ再配送しない) — C1/C2 には届かない筈。"""
    restore(S)
    d_ra = [f"ipv6 route {P_C2LAN} 2001:DB8:1:1::1"]
    d_rb = [f"ipv6 route {P_C1LAN} 2001:DB8:A:A::1"]
    conf(S["RA"], d_ra)
    conf(S["RB"], d_rb)
    settle(S)
    rec = observe(S)
    rec["RA C2LAN"] = fmt(routes(S["RA"]), [P_C2LAN])
    rec["RB C1LAN"] = fmt(routes(S["RB"]), [P_C1LAN])
    emit("E13", "★RA/RB に静的のみ(再配送なし) — 中継は知るがクライアントは知らない",
         d_ra + d_rb, rec)


def s_e14_static_client(S):
    """E14: E13 に加えて C1/C2 にデフォルトを置く(最小の静的解)。"""
    restore(S)
    conf(S["RA"], [f"ipv6 route {P_C2LAN} 2001:DB8:1:1::1"])
    conf(S["RB"], [f"ipv6 route {P_C1LAN} 2001:DB8:A:A::1"])
    d_c1 = ["ipv6 route ::/0 2001:DB8:2:1::1"]
    d_c2 = ["ipv6 route ::/0 2001:DB8:1A:A::1"]
    conf(S["C1"], d_c1)
    conf(S["C2"], d_c2)
    settle(S)
    emit("E14", "RA/RB 静的 + C1/C2 デフォルト(フィルタ無改変の静的解)",
         d_c1 + d_c2, observe(S))


def s_e15_metric_type(S):
    """E15: OSPF 側 metric-type 1 / metric 指定。"""
    restore(S)
    d = ["ipv6 prefix-list E5400 seq 10 permit " + P_C2LAN,
         "router ospfv3 544", " address-family ipv6 unicast",
         "  no redistribute eigrp 5400",
         "  redistribute eigrp 5400 metric 500 metric-type 1"
         " route-map EMAP01 include-connected",
         " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    rec = {"C1": fmt(routes(S["C1"]), [P_C2LAN, P_ETRAN]),
           "RA": fmt(routes(S["RA"]), [P_C2LAN, P_ETRAN])}
    emit("E15", "OSPF 側 metric-type 1 + metric 500", d, rec)


def s_e16_merge_trap(S):
    """E16: ★`redistribute` 再発行のマージ挙動 — route-map は外れない。"""
    restore(S)
    before = observe(S)["RT-C redist"]
    d = ["router eigrp NAMED",
         " address-family ipv6 unicast autonomous-system 5400",
         "  topology base",
         "   redistribute ospf 544 match internal metric 10000 100 255 1 1500"
         " include-connected",
         "  exit-af-topology", " exit-address-family", "exit",
         "router ospfv3 544", " address-family ipv6 unicast",
         "  redistribute eigrp 5400 include-connected",
         " exit-address-family", "exit"]
    conf(S["RT-C"], d)
    settle(S)
    rec = observe(S)
    rec["(参考) delta 適用前の redist 行"] = before
    emit("E16", "★route-map 節を書かずに redistribute を再発行(no を前置しない)"
         " — 外れるか", d, rec)


SCEN = {
    "base": (s_base, "基線"),
    "e16": (s_e16_merge_trap, "★redistribute 再発行のマージ罠"),
    "e1": (s_e1_rmap_off, "route-map 外し"),
    "e2": (s_e2_pl_add, "prefix-list 追記"),
    "e3": (s_e3_pl_replace, "★prefix-list 置換=include-connected と route-map"),
    "e4": (s_e4_no_incl, "include-connected 外し"),
    "e5": (s_e5_no_metric, "★EIGRP metric 省略"),
    "e6": (s_e6_default_metric, "default-metric"),
    "e7": (s_e7_pl_undef, "★参照 prefix-list 未定義"),
    "e8": (s_e8_rmap_undef, "★未定義 route-map 参照"),
    "e9": (s_e9_afif_up, "af-interface shutdown 解除"),
    "e10": (s_e10_match_ext, "★match internal と外部経路"),
    "e11": (s_e11_default_ospf, "★default-information originate always"),
    "e12": (s_e12_default_eigrp, "★EIGRP ::/0 summary-address"),
    "e13": (s_e13_static_mid, "★中継のみ静的"),
    "e14": (s_e14_static_client, "静的+クライアントデフォルト"),
    "e15": (s_e15_metric_type, "metric-type 1"),
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--list" in sys.argv:
        for k, (_, t) in SCEN.items():
            print(f"{k:6} {t}")
        return
    want = args or list(SCEN)
    h = hosts()
    S, clis = {}, []
    for name, ip in h.items():
        cli, sh = session(ip)
        S[name] = sh
        clis.append(cli)
    try:
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## sweep run ({', '.join(want)})\n\n")
        for k in want:
            fn, title = SCEN[k]
            print(f"\n===== {k}: {title} =====")
            fn(S)
        print("\n== 基線へ復帰 ==")
        restore(S)
    finally:
        for c in clis:
            c.close()


if __name__ == "__main__":
    main()
