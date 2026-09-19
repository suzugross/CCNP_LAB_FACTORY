#!/usr/bin/env python3
"""P8: IPv6 source-guard / prefix-guard / destination-guard の ioll2-xe 実測(BL-146 紙面・BL-176 残)。

盤面 POC-FHS(poc/fhs/poc-fhs-lab.yaml): SWB(ioll2-xe・VLAN10) / RT02(GW 2001:DB8:33:B::/64・O flag) / CLB(autoconfig) / ROG(不正 RA)。
    SWB Et0/0=RT02  Et0/1=CLB  Et0/2=ROG
コンソール駆動のみ。結果は results-p8.md へ追記。  使い方: p8_guards.py [P8]
"""
import os
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "paper-kb"))
import sweep  # noqa: E402  (POC-KB 用ハーネスのヘルパーを流用)
from sweep import conf, sh, block, note, flush, ping, wait_for, logtail  # noqa: E402

TITLE = os.environ.get("P8_TITLE", "POC-FHS")
SWIF = os.environ.get("P8_SWIFS", "Ethernet0/0,Ethernet0/1,Ethernet0/2").split(",")   # SWB の RT02/CLB/ROG 向けポート
NODES = ["SWB", "RT02", "CLB", "ROG"]
sweep.OUT = HERE / ("results-p8.md" if TITLE == "POC-FHS" else f"results-p8-{TITLE.lower()}.md")
GW = "2001:DB8:33:B::1"
ACL = ["ipv6 access-list CNT",
       "sequence 10 permit icmp 2001:DB8:98::/64 any", "sequence 20 permit icmp 2001:DB8:99::/64 any",
       "sequence 30 permit icmp 2001:DB8:33:B::/64 any", "sequence 40 permit icmp any any",
       "sequence 50 permit ipv6 any any", "exit"]


def clb_gua(clb):
    o = sh(clb, "show ipv6 interface brief Ethernet0/0")
    m = re.search(r"(2001:DB8:33:B:[0-9A-F:]+)", o, re.I)
    return (m.group(1) if m else None), o


def pings(clb, tag, rt02):
    sh(rt02, "clear ipv6 access-list CNT")
    r_a, _ = ping(clb, GW, repeat=5, title=f"{tag} (a) CLB 既定送信元(SLAAC GUA)→GW")
    r_b, _ = ping(clb, GW, source="2001:DB8:98::1", repeat=5, title=f"{tag} (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW")
    r_c, _ = ping(clb, GW, source="2001:DB8:99::1", repeat=5, title=f"{tag} (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW")
    block(f"{tag} RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)", sh(rt02, "show ipv6 access-list CNT"))
    note(f"{tag} ping 成功率 a={r_a}% b={r_b}% c={r_c}%")


def P8(devs):
    swb, rt02, clb, rog = (devs[n] for n in NODES)
    # ---- 0 基線: CVAC で admin-down の IF を上げ、RA guard(ROG 遮断)＋device-tracking を入れる ----
    for d in (rt02, clb, rog):
        conf(d, ["interface Ethernet0/0", "no shutdown", "exit"])
    conf(swb, ["ipv6 nd raguard policy HOST", "device-role host", "exit",
               "ipv6 nd raguard policy ROUTER", "device-role router", "exit",
               "device-tracking policy TRACK", "exit",
               "vlan configuration 10", "device-tracking attach-policy TRACK", "exit",
               f"interface {SWIF[0]}", "ipv6 nd raguard attach-policy ROUTER", "exit",
               f"interface {SWIF[1]}", "ipv6 nd raguard attach-policy HOST", "exit",
               f"interface {SWIF[2]}", "ipv6 nd raguard attach-policy HOST", "exit"], title="P8-0 SWB RA guard + device-tracking")
    conf(rt02, ACL + ["interface Ethernet0/0", "ipv6 traffic-filter CNT in", "exit"], title="P8-0 RT02 受信カウンタ ACL")
    block("P8-0 SWB show version | include Software|IOS", sh(swb, "show version | include Software|IOS"))
    block("P8-0 SWB CLI 有無(ipv6 snooping/nd inspection/source-guard/destination-guard)", conf(swb, ["ipv6 snooping policy SNOOP", "exit", "ipv6 nd inspection policy NDI", "exit", "ipv6 source-guard policy PROBE", "exit", "ipv6 destination-guard policy PROBE", "exit", "device-tracking policy PROBE", "exit"]))
    sweep._bounce(clb, "Ethernet0/0")

    def gua():
        g, o = clb_gua(clb)
        return g is not None, o
    t, info = wait_for(gua, timeout=240, step=15, what="CLB に 2001:DB8:33:B:: GUA")
    block(f"P8-0 CLB show ipv6 interface brief (GUA after {t}s)", info)
    block("P8-0 CLB show ipv6 routers", sh(clb, "show ipv6 routers"))
    conf(clb, ["interface Loopback0", "ipv6 address 2001:DB8:99::1/64", "exit",
               "interface Ethernet0/0", "ipv6 address 2001:DB8:98::1/64", "exit"], title="P8-0 CLB 範囲外アドレス追加(Et0/0=98::1 / Lo0=99::1)")
    time.sleep(15)
    block("P8-0 SWB show device-tracking database", sh(swb, "show device-tracking database"))
    block("P8-0 SWB show device-tracking database details", sh(swb, "show device-tracking database details"))
    block("P8-0 SWB show device-tracking policies", sh(swb, "show device-tracking policies"))
    for c in ["show ipv6 source-guard policy ?", "show device-tracking database prefix", "show device-tracking database mac",
              "show ipv6 destination-guard policy ?"]:
        pass
    pings(clb, "P8-0 ガード無し", rt02)

    # ---- 1 source-guard(既定= validate address) を CLB ポートへ ----
    conf(swb, ["ipv6 source-guard policy SG", "exit", f"interface {SWIF[1]}", "ipv6 source-guard attach-policy SG", "exit"],
         title="P8-1 SWB source-guard SG(既定) → Et0/1")
    time.sleep(10)
    block("P8-1 SWB show ipv6 source-guard policy SG", sh(swb, "show ipv6 source-guard policy SG"))
    block("P8-1 SWB show device-tracking policies", sh(swb, "show device-tracking policies"))
    sh(swb, "clear device-tracking counters")
    pings(clb, "P8-1 source-guard(address)", rt02)
    block("P8-1 SWB show device-tracking counters interface Ethernet0/1", sh(swb, f"show device-tracking counters interface {SWIF[1]}"))
    block("P8-1 SWB show device-tracking database", sh(swb, "show device-tracking database"))
    logtail(swb, "P8-1 SWB", include=r"SISF|GUARD|IPV6|TRACK")

    # ---- 2 prefix-guard(validate prefix) ----
    conf(swb, [f"interface {SWIF[1]}", "no ipv6 source-guard attach-policy SG", "exit",
               "ipv6 source-guard policy PG", "validate prefix", "exit",
               f"interface {SWIF[1]}", "ipv6 source-guard attach-policy PG", "exit"], title="P8-2 SWB PG(validate prefix) → Et0/1")
    time.sleep(10)
    block("P8-2 SWB show ipv6 source-guard policy PG", sh(swb, "show ipv6 source-guard policy PG"))
    block("P8-2 SWB show run | section source-guard", sh(swb, "show running-config | section source-guard"))
    sh(swb, "clear device-tracking counters")
    pings(clb, "P8-2 prefix-guard(validate prefix)", rt02)
    block("P8-2 SWB show device-tracking counters interface Ethernet0/1", sh(swb, f"show device-tracking counters interface {SWIF[1]}"))
    block("P8-2 SWB show device-tracking database", sh(swb, "show device-tracking database"))
    logtail(swb, "P8-2 SWB", include=r"SISF|GUARD|IPV6|TRACK")
    # validate address も足した形(address AND prefix)
    conf(swb, ["ipv6 source-guard policy PG", "validate address", "exit"], title="P8-2b PG に validate address 追加")
    time.sleep(8)
    block("P8-2b SWB show ipv6 source-guard policy PG", sh(swb, "show ipv6 source-guard policy PG"))
    sh(swb, "clear device-tracking counters")
    pings(clb, "P8-2b prefix+address", rt02)
    block("P8-2b SWB show device-tracking counters interface Ethernet0/1", sh(swb, f"show device-tracking counters interface {SWIF[1]}"))
    conf(swb, [f"interface {SWIF[1]}", "no ipv6 source-guard attach-policy PG", "exit"])

    # ---- 3 destination-guard(ルータ側ポート Et0/0)・RT02 は静的 ND で未知宛先へデータを送る ----
    block("P8-3 SWB destination-guard CLI 有無", conf(swb, ["ipv6 destination-guard policy DG", "enforcement always", "exit"]))
    block("P8-3 SWB show run | section destination-guard", sh(swb, "show running-config | section destination-guard"))
    conf(rt02, ["ipv6 neighbor 2001:DB8:33:B::DEAD Ethernet0/0 aabb.cc00.0dea"], title="P8-3 RT02 未知宛先の静的 ND")
    g, _ = clb_gua(clb)
    ping(rt02, g, repeat=5, title=f"P8-3 DG 無し RT02→CLB {g}(表にある宛先)")
    ping(rt02, "2001:DB8:33:B::DEAD", repeat=3, title="P8-3 DG 無し RT02→::DEAD(表に無い宛先・静的 ND)")
    txt = conf(swb, [f"interface {SWIF[0]}", "ipv6 destination-guard attach-policy DG", "exit"], title="P8-3 SWB DG → ルータ側ポート")
    if "%" in txt:
        conf(swb, ["vlan configuration 10", "ipv6 destination-guard attach-policy DG", "exit"], title="P8-3 SWB DG → vlan configuration 10(代替)")
    time.sleep(8)
    block("P8-3 SWB show ipv6 destination-guard policy DG", sh(swb, "show ipv6 destination-guard policy DG"))
    block("P8-3 SWB show device-tracking policies", sh(swb, "show device-tracking policies"))
    sh(swb, "clear device-tracking counters")
    ping(rt02, g, repeat=5, title=f"P8-3 DG あり RT02→CLB {g}(表にある宛先)")
    ping(rt02, "2001:DB8:33:B::DEAD", repeat=3, title="P8-3 DG あり RT02→::DEAD(表に無い宛先)")
    block(f"P8-3 SWB show device-tracking counters interface {SWIF[0]}", sh(swb, f"show device-tracking counters interface {SWIF[0]}"))
    block("P8-3 SWB show device-tracking counters vlan 10", sh(swb, "show device-tracking counters vlan 10"))
    logtail(swb, "P8-3 SWB", include=r"SISF|GUARD|IPV6|TRACK")
    # 後片付け(盤面は温存)
    conf(rt02, ["no ipv6 neighbor 2001:DB8:33:B::DEAD Ethernet0/0 aabb.cc00.0dea"])
    flush("P8 source/prefix/destination guard(ioll2-xe 17.15.1)")


# ==========================================================================
# 旧 CLI(IOSvL2 15.2 系: ipv6 snooping / device-tracking policy 無し)向けの P8
#   P8_LEGACY=1 で選択。各モードは 1 conf() ずつ・失敗しても続行(exit で config を抜ける事故を避ける)
# ==========================================================================
def safe_conf(dev, lines, title):
    try:
        return conf(dev, lines, title=title)
    except Exception as e:
        block(title + " (EXCEPTION)", f"{type(e).__name__}: {str(e)[:300]}")
        for c in ("end", "end"):
            try:
                dev.execute(c, timeout=20)
            except Exception:
                pass
        return ""


def safe_sh(dev, cmd, title):
    try:
        block(title, sh(dev, cmd))
    except Exception as e:
        block(title + " (EXCEPTION)", f"{type(e).__name__}: {str(e)[:300]}")


def P8L(devs):
    swb, rt02, clb, rog = (devs[n] for n in NODES)
    P0, P1, P2 = SWIF
    for d in (rt02, clb, rog):
        conf(d, ["interface Ethernet0/0", "no shutdown", "exit"])
    block("P8L-0 SWB show version", sh(swb, "show version | include Software|IOS"))
    safe_conf(swb, ["ipv6 nd raguard policy HOST", "device-role host"], "P8L-0 raguard policy HOST")
    safe_conf(swb, ["ipv6 nd raguard policy ROUTER", "device-role router"], "P8L-0 raguard policy ROUTER")
    safe_conf(swb, ["ipv6 snooping policy SNOOP", "security-level guard", "tracking enable"], "P8L-0 snooping policy SNOOP")
    safe_conf(swb, ["vlan configuration 10", "ipv6 snooping attach-policy SNOOP"], "P8L-0 vlan 10 に snooping attach")
    safe_conf(swb, [f"interface {P0}", "ipv6 nd raguard attach-policy ROUTER"], f"P8L-0 {P0} raguard ROUTER")
    safe_conf(swb, [f"interface {P1}", "ipv6 nd raguard attach-policy HOST"], f"P8L-0 {P1} raguard HOST")
    safe_conf(swb, [f"interface {P2}", "ipv6 nd raguard attach-policy HOST"], f"P8L-0 {P2} raguard HOST")
    conf(rt02, ACL + ["interface Ethernet0/0", "ipv6 traffic-filter CNT in", "exit"], title="P8L-0 RT02 受信カウンタ ACL")
    sweep._bounce(clb, "Ethernet0/0")

    def gua():
        g, o = clb_gua(clb)
        return g is not None, o
    t, info = wait_for(gua, timeout=240, step=15, what="CLB に 2001:DB8:33:B:: GUA")
    block(f"P8L-0 CLB show ipv6 interface brief (GUA after {t}s)", info)
    block("P8L-0 CLB show ipv6 routers", sh(clb, "show ipv6 routers"))
    conf(clb, ["interface Loopback0", "ipv6 address 2001:DB8:99::1/64", "exit",
               "interface Ethernet0/0", "ipv6 address 2001:DB8:98::1/64", "exit"], title="P8L-0 CLB 範囲外アドレス追加(Et0/0=98::1 / Lo0=99::1)")
    time.sleep(15)
    for c in ["show ipv6 snooping policies", "show ipv6 neighbors binding", "show ipv6 snooping features",
              f"show ipv6 snooping counters interface {P1}", "show ipv6 nd raguard policy HOST"]:
        safe_sh(swb, c, f"P8L-0 SWB {c}")
    pings(clb, "P8L-0 ガード無し", rt02)

    # ---- source-guard(既定) ----
    safe_conf(swb, ["ipv6 source-guard policy SG"], "P8L-1 source-guard policy SG")
    safe_conf(swb, [f"interface {P1}", "ipv6 source-guard attach-policy SG"], f"P8L-1 {P1} に SG attach")
    time.sleep(10)
    for c in ["show ipv6 source-guard policy SG", "show ipv6 snooping policies", f"show running-config interface {P1}"]:
        safe_sh(swb, c, f"P8L-1 SWB {c}")
    pings(clb, "P8L-1 source-guard(address)", rt02)
    for c in [f"show ipv6 snooping counters interface {P1}", "show ipv6 neighbors binding"]:
        safe_sh(swb, c, f"P8L-1 SWB {c}")
    logtail(swb, "P8L-1 SWB", include=r"SISF|GUARD|IPV6|SNOOP")

    # ---- prefix-guard ----
    safe_conf(swb, [f"interface {P1}", "no ipv6 source-guard attach-policy SG"], f"P8L-2 {P1} SG detach")
    safe_conf(swb, ["ipv6 source-guard policy PG", "validate prefix"], "P8L-2 source-guard policy PG(validate prefix)")
    safe_conf(swb, [f"interface {P1}", "ipv6 source-guard attach-policy PG"], f"P8L-2 {P1} に PG attach")
    time.sleep(10)
    safe_sh(swb, "show ipv6 source-guard policy PG", "P8L-2 SWB show ipv6 source-guard policy PG")
    pings(clb, "P8L-2 prefix-guard(validate prefix)", rt02)
    safe_sh(swb, f"show ipv6 snooping counters interface {P1}", f"P8L-2 SWB show ipv6 snooping counters interface {P1}")
    safe_conf(swb, ["ipv6 source-guard policy PG", "validate address"], "P8L-2b PG に validate address 追加")
    time.sleep(8)
    pings(clb, "P8L-2b prefix+address", rt02)
    safe_conf(swb, [f"interface {P1}", "no ipv6 source-guard attach-policy PG"], f"P8L-2 {P1} PG detach")

    # ---- destination-guard ----
    safe_conf(swb, ["ipv6 destination-guard policy DG", "enforcement always"], "P8L-3 destination-guard policy DG")
    conf(rt02, ["ipv6 neighbor 2001:DB8:33:B::DEAD Ethernet0/0 aabb.cc00.0dea"], title="P8L-3 RT02 未知宛先の静的 ND")
    g, _ = clb_gua(clb)
    ping(rt02, g, repeat=5, title=f"P8L-3 DG 無し RT02→CLB {g}")
    ping(rt02, "2001:DB8:33:B::DEAD", repeat=3, title="P8L-3 DG 無し RT02→::DEAD")
    safe_conf(swb, [f"interface {P0}", "ipv6 destination-guard attach-policy DG"], f"P8L-3 {P0} に DG attach")
    safe_conf(swb, ["vlan configuration 10", "ipv6 destination-guard attach-policy DG"], "P8L-3 vlan 10 に DG attach(代替)")
    time.sleep(8)
    safe_sh(swb, "show ipv6 destination-guard policy DG", "P8L-3 SWB show ipv6 destination-guard policy DG")
    ping(rt02, g, repeat=5, title=f"P8L-3 DG あり RT02→CLB {g}")
    ping(rt02, "2001:DB8:33:B::DEAD", repeat=3, title="P8L-3 DG あり RT02→::DEAD")
    for c in [f"show ipv6 snooping counters interface {P0}", "show ipv6 snooping counters vlan 10"]:
        safe_sh(swb, c, f"P8L-3 SWB {c}")
    logtail(swb, "P8L-3 SWB", include=r"SISF|GUARD|IPV6|SNOOP")
    conf(rt02, ["no ipv6 neighbor 2001:DB8:33:B::DEAD Ethernet0/0 aabb.cc00.0dea"])
    flush(f"P8L source/prefix/destination guard(旧 CLI・{TITLE})")


def main():
    cl, creds = sweep.client()
    labs = cl.find_labs_by_title(TITLE)
    if not labs:
        sys.exit(f"{TITLE} が無い(poc_ops.py import → start)")
    lab = labs[0]
    devs = sweep.connect_all(lab, creds, labels=NODES)
    try:
        (P8L if os.environ.get("P8_LEGACY") else P8)(devs)
    except Exception:
        tb = traceback.format_exc()
        print(tb)
        block("P8 EXCEPTION", tb)
        flush("P8 (失敗)")
    for d in devs.values():
        try:
            d.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
