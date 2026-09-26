#!/usr/bin/env python3
"""BL-208 DMVPN「壊滅スタート」PoC(IOL iol-xe・IKEv1・Phase 3・EIGRP)。

盤面 POC-DMVPNW = IOL 5 台。ISP(RT05)を中心にしたスター。ISP の Lo0 8.8.8.8 = インターネット。

    RT01(HUB)  e0/0 203.0.113.2/30  -- ISP e0/0 .1
    RT02(SP1)  e0/0 198.51.100.2/30 -- ISP e0/1 .1
    RT03(SP2)  e0/0 198.51.100.6/30 -- ISP e0/2 .5
    RT04(SP3)  e0/0 198.51.100.10/30-- ISP e0/3 .9
    LAN= Lo1 10.0.<n>.1/24(HUB n=0)  Tunnel0 172.16.0.<n>/24(HUB .1)

使い方: sweep.py build | P0 | W1 ... | F1 ... | P2 | P3 | teardown   結果は results-raw.md へ追記。
CML/コンソール操作は poc/paper-kb/sweep.py の関数を流用する(モジュール変数を差し替えて使う)。
"""
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "paper-kb"))
import sweep as kb  # noqa: E402

NODES = ["RT01", "RT02", "RT03", "RT04", "RT05"]
HUB, SPOKES, ISP = "RT01", ["RT02", "RT03", "RT04"], "RT05"
NBMA = {"RT01": "203.0.113.2", "RT02": "198.51.100.2", "RT03": "198.51.100.6",
        "RT04": "198.51.100.10"}
GW = {"RT01": "203.0.113.1", "RT02": "198.51.100.1", "RT03": "198.51.100.5",
      "RT04": "198.51.100.9"}
N = {"RT01": 0, "RT02": 2, "RT03": 3, "RT04": 4}
TIP = {k: f"172.16.0.{1 if k == HUB else v}" for k, v in N.items()}
PSK, NHKEY, NETID, TKEY, AS = "CCNPKEY1", "NHRPKEY", 100, 100, 100

CRYPTO = [
    "crypto isakmp policy 10", "encryption aes 256", "hash sha256",
    "authentication pre-share", "group 14", "exit",
    f"crypto isakmp key {PSK} address 0.0.0.0",
    "crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac", "mode transport", "exit",
    "crypto ipsec profile DMVPN-PROF", "set transform-set TS", "exit",
]


def base(label):
    if label == ISP:
        return ["interface Loopback0", "ip address 8.8.8.8 255.255.255.255", "exit",
                "interface Ethernet0/0", "ip address 203.0.113.1 255.255.255.252", "no shutdown", "exit",
                "interface Ethernet0/1", "ip address 198.51.100.1 255.255.255.252", "no shutdown", "exit",
                "interface Ethernet0/2", "ip address 198.51.100.5 255.255.255.252", "no shutdown", "exit",
                "interface Ethernet0/3", "ip address 198.51.100.9 255.255.255.252", "no shutdown", "exit"]
    n = N[label]
    L = ["interface Loopback1", f"ip address 10.0.{n}.1 255.255.255.0", "exit",
         "interface Ethernet0/0", f"ip address {NBMA[label]} 255.255.255.252", "no shutdown", "exit",
         f"ip route 0.0.0.0 0.0.0.0 {GW[label]}"] + CRYPTO
    return L + tunnel(label) + ["exit", f"router eigrp {AS}",
                                "network 172.16.0.0 0.0.0.255", "network 10.0.0.0 0.0.255.255", "exit"]


def tunnel(label):
    t = ["interface Tunnel0", f"ip address {TIP[label]} 255.255.255.0",
         "no ip redirects", "ip mtu 1400", "ip tcp adjust-mss 1360",
         f"ip nhrp authentication {NHKEY}", f"ip nhrp network-id {NETID}"]
    if label == HUB:
        t += ["ip nhrp map multicast dynamic", "ip nhrp redirect", f"no ip split-horizon eigrp {AS}"]
    else:
        t += [f"ip nhrp nhs {TIP[HUB]} nbma {NBMA[HUB]} multicast", "ip nhrp shortcut"]
    t += ["tunnel source Ethernet0/0", "tunnel mode gre multipoint", f"tunnel key {TKEY}",
          "tunnel protection ipsec profile DMVPN-PROF"]
    return t


kb.LAB_TITLE = "POC-DMVPNW"
kb.NODES = NODES
kb.OUT = HERE / "results-raw.md"
kb.BASE = {l: base(l) for l in NODES}
kb.LINKS = [(HUB, "Ethernet0/0", ISP, "Ethernet0/0"),
            ("RT02", "Ethernet0/0", ISP, "Ethernet0/1"),
            ("RT03", "Ethernet0/0", ISP, "Ethernet0/2"),
            ("RT04", "Ethernet0/0", ISP, "Ethernet0/3")]
block, note, flush, conf, sh, ping = kb.block, kb.note, kb.flush, kb.conf, kb.sh, kb.ping


# =========================================================================
def hub_up(devs):
    out = sh(devs[HUB], "show dmvpn")
    ups = [s for s in SPOKES if any(NBMA[s] in l and " UP " in l for l in out.splitlines())]
    return len(ups) == 3, out


def reset(devs, who=None, wait=True, title=None):
    """トンネルの bounce + SA/NHRP 消去(どのケースも同じ手順で「新しく張る」状態へ)。"""
    who = who or [HUB] + SPOKES
    for w in who:
        conf(devs[w], ["interface Tunnel0", "shutdown"])
    for w in who:
        sh(devs[w], "clear crypto session")
        sh(devs[w], "clear crypto isakmp")
        sh(devs[w], "clear ip nhrp")
    for w in who:
        conf(devs[w], ["interface Tunnel0", "no shutdown"])
    if wait:
        t, _ = kb.wait_for(lambda: hub_up(devs), timeout=240, step=15, what="hub で 3 spoke UP")
        note(f"{title or 'reset'}: 健全復帰 {'%.0fs' % t if t is not None else '★240s で復帰せず'}")
        return t


def obs(devs, tag, victim="RT02", extra=()):
    time.sleep(75)
    h, v = devs[HUB], devs[victim]
    sh(h, "show dmvpn", f"{tag} hub")
    sh(h, "show crypto isakmp sa", f"{tag} hub")
    sh(h, "show crypto ipsec sa | include peer|encaps|decaps|in use settings", f"{tag} hub")
    sh(h, "show ip interface brief | include Tunnel", f"{tag} hub")
    kb.logtail(h, f"{tag} hub log")
    sh(v, "show dmvpn", f"{tag} {victim}")
    sh(v, "show crypto isakmp sa", f"{tag} {victim}")
    sh(v, "show crypto ipsec sa | include peer|encaps|decaps|in use settings", f"{tag} {victim}")
    sh(v, "show ip nhrp nhs detail", f"{tag} {victim}")
    sh(v, "show ip interface brief | include Tunnel", f"{tag} {victim}")
    kb.logtail(v, f"{tag} {victim} log")
    for d, c in extra:
        sh(devs[d], c, f"{tag} {d}")


def case(devs, tag, desc, brk, fix, victim="RT02", extra=()):
    """brk/fix = [(node, lines)]。注入→全 bounce→観測→是正→全 bounce→健全確認。"""
    note(f"== {tag}: {desc}")
    for d in devs.values():
        kb.clear_log(d)
    for n, lines in brk:
        conf(devs[n], lines, f"{tag} 注入 {n}")
    reset(devs, wait=False)
    obs(devs, tag, victim, extra)
    for n, lines in fix:
        conf(devs[n], lines, f"{tag} 是正 {n}")
    reset(devs, title=f"{tag} 是正後")
    flush(f"{tag} {desc}")


# =========================================================================
def P0(devs):
    t = reset(devs, title="P0 基線")
    h = devs[HUB]
    sh(h, "show dmvpn", "P0 hub")
    sh(h, "show crypto isakmp sa", "P0 hub")
    sh(h, "show crypto ipsec sa | include peer|encaps|decaps|in use settings", "P0 hub")
    sh(h, "show ip eigrp neighbors", "P0 hub")
    s = devs["RT02"]
    ping(s, "10.0.3.1", source="Loopback1", repeat=5, title="P0 spoke→spoke")
    time.sleep(5)
    sh(s, "show dmvpn", "P0 RT02")
    sh(s, "show ip nhrp nhs detail", "P0 RT02")
    sh(s, "show ip route next-hop-override | begin Gateway", "P0 RT02")
    flush("P0 基線(IKEv1 Phase3)")


T = ["interface Tunnel0"]
WCASES = {
    "W1": ("hub の tunnel protection なし(profile は定義済み)",
           [(HUB, T + ["no tunnel protection ipsec profile DMVPN-PROF"])],
           [(HUB, T + ["tunnel protection ipsec profile DMVPN-PROF"])]),
    "W2": ("hub の ipsec profile も protection も無い(profile 未定義)",
           [(HUB, T + ["no tunnel protection ipsec profile DMVPN-PROF", "exit",
                       "no crypto ipsec profile DMVPN-PROF"])],
           [(HUB, ["crypto ipsec profile DMVPN-PROF", "set transform-set TS", "exit"]
             + T + ["tunnel protection ipsec profile DMVPN-PROF"])]),
    "W3": ("hub の ip nhrp network-id なし",
           [(HUB, T + [f"no ip nhrp network-id {NETID}"])],
           [(HUB, T + [f"ip nhrp network-id {NETID}"])]),
    "W4": ("hub の tunnel key なし(spoke は key あり)",
           [(HUB, T + [f"no tunnel key {TKEY}"])],
           [(HUB, T + [f"tunnel key {TKEY}"])]),
    "W5": ("hub が p2p GRE(tunnel mode gre ip + tunnel destination)",
           [(HUB, T + ["tunnel mode gre ip", f"tunnel destination {NBMA['RT02']}"])],
           [(HUB, T + ["no tunnel destination", "tunnel mode gre multipoint"])]),
    "W6": ("hub の ip nhrp map multicast dynamic なし",
           [(HUB, T + ["no ip nhrp map multicast dynamic"])],
           [(HUB, T + ["ip nhrp map multicast dynamic"])]),
    "W7": ("RT02 の crypto isakmp key なし",
           [("RT02", [f"no crypto isakmp key {PSK} address 0.0.0.0"])],
           [("RT02", [f"crypto isakmp key {PSK} address 0.0.0.0"])]),
    "W8": ("RT02 の tunnel protection なし(hub はあり)",
           [("RT02", T + ["no tunnel protection ipsec profile DMVPN-PROF"])],
           [("RT02", T + ["tunnel protection ipsec profile DMVPN-PROF"])]),
    "W9": ("RT02 の ip nhrp network-id なし",
           [("RT02", T + [f"no ip nhrp network-id {NETID}"])],
           [("RT02", T + [f"ip nhrp network-id {NETID}"])]),
    "W10": ("RT02 の tunnel key なし(hub はあり)",
            [("RT02", T + [f"no tunnel key {TKEY}"])],
            [("RT02", T + [f"tunnel key {TKEY}"])]),
}
FCASES = {
    "F1": ("RT02 の transform-set 不一致(esp-3des esp-sha-hmac)",
           [("RT02", ["crypto ipsec transform-set TS esp-3des esp-sha-hmac", "mode transport", "exit"])],
           [("RT02", ["crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac", "mode transport", "exit"])]),
    # ★F1 は IOL 17.15 が esp-3des を構文ごと拒否(% Invalid input)して不成立 → F1b で取り直す
    "F1b": ("RT02 の transform-set 不一致(esp-aes 128 esp-sha-hmac)",
            [("RT02", ["crypto ipsec transform-set TS esp-aes esp-sha-hmac", "mode transport", "exit"])],
            [("RT02", ["crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac", "mode transport", "exit"])]),
    "F2": ("hub の外側 IF で ESP だけ遮断(UDP 500 は許可)",
           [(HUB, ["ip access-list extended OUTSIDE-IN", "deny esp any any",
                   "permit ip any any", "exit", "interface Ethernet0/0",
                   "ip access-group OUTSIDE-IN in"])],
           [(HUB, ["interface Ethernet0/0", "no ip access-group OUTSIDE-IN in", "exit",
                   "no ip access-list extended OUTSIDE-IN"])]),
    "F3": ("RT02 の NHRP 認証不一致",
           [("RT02", T + ["ip nhrp authentication NHRPKEX"])],
           [("RT02", T + [f"ip nhrp authentication {NHKEY}"])]),
    "F4": ("RT02 の NHS トンネル IP 誤り(172.16.0.254)",
           [("RT02", T + [f"no ip nhrp nhs {TIP[HUB]} nbma {NBMA[HUB]} multicast",
                          f"ip nhrp nhs 172.16.0.254 nbma {NBMA[HUB]} multicast"])],
           [("RT02", T + [f"no ip nhrp nhs 172.16.0.254 nbma {NBMA[HUB]} multicast",
                          f"ip nhrp nhs {TIP[HUB]} nbma {NBMA[HUB]} multicast"])]),
    "F5": ("RT02 が nhs を持たず static map だけ(spoke に hub が static で見える)",
           [("RT02", T + [f"no ip nhrp nhs {TIP[HUB]} nbma {NBMA[HUB]} multicast",
                          f"ip nhrp map {TIP[HUB]} {NBMA[HUB]}",
                          f"ip nhrp map multicast {NBMA[HUB]}"])],
           [("RT02", T + [f"no ip nhrp map {TIP[HUB]} {NBMA[HUB]}",
                          f"no ip nhrp map multicast {NBMA[HUB]}",
                          f"ip nhrp nhs {TIP[HUB]} nbma {NBMA[HUB]} multicast"])]),
    "F6": ("hub の PFS 片側要求(set pfs group14)",
           [(HUB, ["crypto ipsec profile DMVPN-PROF", "set pfs group14", "exit"])],
           [(HUB, ["crypto ipsec profile DMVPN-PROF", "no set pfs", "exit"])]),
    "F7": ("hub の mode gre ip(tunnel destination なし)",
           [(HUB, T + ["tunnel mode gre ip"])],
           [(HUB, T + ["tunnel mode gre multipoint"])]),
    "F8": ("hub の transform-set が mode tunnel(spoke は transport)",
           [(HUB, ["crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac", "mode tunnel", "exit"])],
           [(HUB, ["crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac", "mode transport", "exit"])]),
}


def _run(table):
    def f(devs, key):
        desc, brk, fix = table[key]
        case(devs, key, desc, brk, fix)
    return f


def P5x(devs):
    """tunnel protection の追加・変更で Tunnel が自動 shutdown するか(IOL)。bounce しない。"""
    note("== P5x: protection 追加で自動 shutdown するか")
    h = devs[HUB]
    kb.clear_log(h)
    conf(h, T + ["no tunnel protection ipsec profile DMVPN-PROF"], "P5x 削除")
    sh(h, "show ip interface brief | include Tunnel", "P5x 削除直後")
    conf(h, T + ["tunnel protection ipsec profile DMVPN-PROF"], "P5x 再追加")
    time.sleep(5)
    sh(h, "show ip interface brief | include Tunnel", "P5x 再追加直後")
    kb.logtail(h, "P5x hub log")
    time.sleep(60)
    sh(h, "show dmvpn", "P5x 60s 後")
    conf(h, T + ["no shutdown"])
    reset(devs, title="P5x 後")
    flush("P5x protection 変更と自動 shutdown")


WRECK_ALL = [
    (HUB, T + ["no tunnel protection ipsec profile DMVPN-PROF", "exit",
               "no crypto ipsec profile DMVPN-PROF", "interface Tunnel0",
               f"no ip nhrp network-id {NETID}", f"no tunnel key {TKEY}",
               "no ip nhrp map multicast dynamic",
               "tunnel mode gre ip", f"tunnel destination {NBMA['RT02']}"]),
    ("RT02", [f"no crypto isakmp key {PSK} address 0.0.0.0"]),
    ("RT03", T + ["no tunnel protection ipsec profile DMVPN-PROF", "exit",
                  "no crypto ipsec profile DMVPN-PROF"]),
    ("RT04", T + [f"no tunnel key {TKEY}"]),
]
FIX_ALL = [
    (HUB, ["crypto ipsec profile DMVPN-PROF", "set transform-set TS", "exit",
           "interface Tunnel0", "no tunnel destination", "tunnel mode gre multipoint",
           f"tunnel key {TKEY}", f"ip nhrp network-id {NETID}",
           "ip nhrp map multicast dynamic",
           "tunnel protection ipsec profile DMVPN-PROF"]),
    ("RT02", [f"crypto isakmp key {PSK} address 0.0.0.0"]),
    ("RT03", ["crypto ipsec profile DMVPN-PROF", "set transform-set TS", "exit",
              "interface Tunnel0", "tunnel protection ipsec profile DMVPN-PROF"]),
    ("RT04", T + [f"tunnel key {TKEY}"]),
]


def P2(devs):
    """全部入り → bounce で新規状態 → 自然な順で是正(bounce しない)→ 登録されるまでの時間。"""
    note("== P2: 壊滅スタート → 是正(clear/bounce なし)")
    for n, lines in WRECK_ALL:
        conf(devs[n], lines, f"P2 注入 {n}")
    reset(devs, wait=False)
    time.sleep(60)
    sh(devs[HUB], "show dmvpn", "P2 壊滅 hub")
    for s in SPOKES:
        sh(devs[s], "show dmvpn", f"P2 壊滅 {s}")
    for n, lines in FIX_ALL:
        conf(devs[n], lines, f"P2 是正 {n}")
    # ★protection 変更後の自動 shutdown があれば no shut が要る→ここでは入れずに観測
    for w in [HUB] + SPOKES:
        sh(devs[w], "show ip interface brief | include Tunnel", f"P2 是正直後 {w}")
    t, out = kb.wait_for(lambda: hub_up(devs), timeout=300, step=20, what="是正後の自然登録")
    note(f"P2: 是正のみ(no shut なし)で 3 spoke UP まで {'%.0fs' % t if t is not None else '★300s 未達'}")
    block("P2 是正後 hub show dmvpn", out)
    if t is None:
        for w in [HUB] + SPOKES:
            conf(devs[w], T + ["no shutdown"])
        t, out = kb.wait_for(lambda: hub_up(devs), timeout=240, step=20, what="no shut 後")
        note(f"P2: no shutdown 追加で {'%.0fs' % t if t is not None else '★240s 未達'}")
        if t is None:
            reset(devs, title="P2 bounce+clear")
    flush("P2 壊滅スタート→是正")


def P3(devs):
    """フルトンネル: spoke の LAN → hub 折返し → hub NAT → インターネット(8.8.8.8)。"""
    note("== P3a: 素朴な構成(spoke の static default を消し hub から EIGRP で default を受ける・NBMA は host route)")
    h = devs[HUB]
    conf(h, ["ip access-list standard NAT-SRC", "permit 10.0.0.0 0.0.255.255", "exit",
             "ip nat inside source list NAT-SRC interface Ethernet0/0 overload",
             "interface Ethernet0/0", "ip nat outside", "exit",
             "interface Tunnel0", "ip nat inside", "exit",
             "interface Loopback1", "ip nat inside", "exit",
             "ip route 0.0.0.0 0.0.0.0 " + GW[HUB],
             f"router eigrp {AS}", "redistribute static metric 10000 100 255 1 1400", "exit"],
         "P3a hub")
    for s in SPOKES:
        conf(devs[s], [f"no ip route 0.0.0.0 0.0.0.0 {GW[s]}",
                       f"ip route {NBMA[HUB]} 255.255.255.255 {GW[s]}"], f"P3a {s}")
    time.sleep(40)
    s = devs["RT02"]
    sh(s, "show ip route 0.0.0.0", "P3a RT02")
    ping(s, "8.8.8.8", source="Loopback1", repeat=5, title="P3a RT02 LAN→internet")
    ping(s, "10.0.0.1", source="Loopback1", repeat=5, title="P3a RT02→hub LAN")
    ping(s, "10.0.3.1", source="Loopback1", repeat=5, title="P3a RT02→RT03 LAN(shortcut)")
    time.sleep(10)
    sh(s, "show dmvpn", "P3a RT02")
    sh(h, "show ip nat translations", "P3a hub")
    sh(h, "show dmvpn", "P3a hub")
    kb.logtail(s, "P3a RT02 log")
    flush("P3a フルトンネル(素朴)")

    note("== P3b: spoke 間 NBMA を underlay の静的経路で補う")
    for s_ in SPOKES:
        conf(devs[s_], ["ip route 198.51.100.0 255.255.255.0 " + GW[s_]], f"P3b {s_}")
    reset(devs, title="P3b")
    ping(s, "10.0.3.1", source="Loopback1", repeat=5, title="P3b RT02→RT03 LAN(shortcut)")
    time.sleep(10)
    ping(s, "10.0.3.1", source="Loopback1", repeat=5, title="P3b RT02→RT03 LAN 2回目")
    ping(s, "8.8.8.8", source="Loopback1", repeat=5, title="P3b RT02 LAN→internet")
    sh(s, "show dmvpn", "P3b RT02")
    flush("P3b フルトンネル(NBMA 静的経路)")


def P3r(devs):
    """P3 の後片付け(spoke の static default を戻す・hub の NAT/再配送を外す)。"""
    h = devs[HUB]
    conf(h, [f"router eigrp {AS}", "no redistribute static metric 10000 100 255 1 1400", "exit",
             "no ip nat inside source list NAT-SRC interface Ethernet0/0 overload",
             "interface Ethernet0/0", "no ip nat outside", "exit",
             "interface Tunnel0", "no ip nat inside", "exit",
             "interface Loopback1", "no ip nat inside", "exit"])
    for s in SPOKES:
        conf(devs[s], [f"ip route 0.0.0.0 0.0.0.0 {GW[s]}",
                       f"no ip route {NBMA[HUB]} 255.255.255.255 {GW[s]}",
                       f"no ip route 198.51.100.0 255.255.255.0 {GW[s]}"])
    reset(devs, title="P3r")
    flush("P3r 後片付け")


def _shortcut_probe(devs, tag):
    """RT02→RT03 LAN を 2 回 ping して、RT02 に DT エントリができるか・hub が redirect を送ったか。"""
    s, h = devs["RT02"], devs[HUB]
    sh(s, "clear ip nhrp shortcut")
    sh(h, "clear ip nhrp counters")
    ping(s, "10.0.3.1", source="Loopback1", repeat=10, title=f"{tag} RT02→RT03 LAN 1回目")
    time.sleep(5)
    ping(s, "10.0.3.1", source="Loopback1", repeat=10, title=f"{tag} RT02→RT03 LAN 2回目")
    out = sh(s, "show dmvpn", f"{tag} RT02")
    sh(s, "show ip route 10.0.3.0", f"{tag} RT02")
    sh(s, "show ip cef 10.0.3.1", f"{tag} RT02")
    sh(h, "show ip nhrp traffic", f"{tag} hub")
    sh(s, "show ip nhrp traffic", f"{tag} RT02")
    dt = "DT" in out
    note(f"{tag}: RT02 に直接トンネル(DT) {'あり' if dt else '★なし'}")
    return dt


def P3c(devs):
    """フルトンネルで shortcut ができない原因の切り分け(NAT inside on Tunnel / default via tunnel)。"""
    h = devs[HUB]
    reset(devs, title="P3c-0 基線")
    _shortcut_probe(devs, "P3c-0 基線(フルトンネル無し)")
    # ① hub の Tunnel0 に ip nat inside だけ入れる(spoke は static default のまま)
    conf(h, ["ip access-list standard NAT-SRC", "permit 10.0.0.0 0.0.255.255", "exit",
             "ip nat inside source list NAT-SRC interface Ethernet0/0 overload",
             "interface Ethernet0/0", "ip nat outside", "exit",
             "interface Tunnel0", "ip nat inside", "exit"], "P3c-1 hub NAT inside on Tunnel0")
    _shortcut_probe(devs, "P3c-1 NAT inside on Tunnel0 のみ")
    # ② NAT を外し、default だけトンネル経由(hub から EIGRP で 0/0・spoke は NBMA 経路を underlay へ)
    conf(h, ["interface Tunnel0", "no ip nat inside", "exit",
             "interface Ethernet0/0", "no ip nat outside", "exit",
             "no ip nat inside source list NAT-SRC interface Ethernet0/0 overload",
             "ip route 0.0.0.0 0.0.0.0 " + GW[HUB],
             f"router eigrp {AS}", "redistribute static metric 10000 100 255 1 1400", "exit"],
         "P3c-2 hub default を EIGRP へ")
    for s in SPOKES:
        conf(devs[s], [f"no ip route 0.0.0.0 0.0.0.0 {GW[s]}",
                       f"ip route {NBMA[HUB]} 255.255.255.255 {GW[s]}",
                       f"ip route 198.51.100.0 255.255.255.0 {GW[s]}"], f"P3c-2 {s}")
    time.sleep(30)
    _shortcut_probe(devs, "P3c-2 default via tunnel のみ(NAT なし)")
    # ③ 両方
    conf(h, ["interface Tunnel0", "ip nat inside", "exit",
             "interface Ethernet0/0", "ip nat outside", "exit",
             "ip nat inside source list NAT-SRC interface Ethernet0/0 overload"], "P3c-3 NAT 戻し")
    _shortcut_probe(devs, "P3c-3 両方")
    ping(devs["RT02"], "8.8.8.8", source="Loopback1", repeat=5, title="P3c-3 RT02→internet")
    flush("P3c フルトンネル時の shortcut 切り分け")


def P3d(devs):
    """素朴なフルトンネル: spoke は hub の NBMA への host route だけ・既定経路はトンネル経由(EIGRP)。
    他 spoke の NBMA は既定経路=トンネルへ再帰する。インターネット・spoke 間・shortcut を見る。"""
    h = devs[HUB]
    reset(devs, title="P3d-0")
    conf(h, ["ip access-list standard NAT-SRC", "permit 10.0.0.0 0.0.255.255", "exit",
             "ip nat inside source list NAT-SRC interface Ethernet0/0 overload",
             "interface Ethernet0/0", "ip nat outside", "exit",
             "interface Tunnel0", "ip nat inside", "exit",
             "ip route 0.0.0.0 0.0.0.0 " + GW[HUB],
             f"router eigrp {AS}", "redistribute static metric 10000 100 255 1 1400", "exit"],
         "P3d hub")
    for s in SPOKES:
        conf(devs[s], [f"no ip route 0.0.0.0 0.0.0.0 {GW[s]}",
                       f"ip route {NBMA[HUB]} 255.255.255.255 {GW[s]}"], f"P3d {s}")
    time.sleep(30)
    for d in devs.values():
        kb.clear_log(d)
    s = devs["RT02"]
    ping(s, "8.8.8.8", source="Loopback1", repeat=5, title="P3d RT02→internet")
    dt = _shortcut_probe(devs, "P3d 素朴")
    time.sleep(60)
    ping(s, "10.0.3.1", source="Loopback1", repeat=20, title="P3d 60 秒後 RT02→RT03 LAN")
    sh(s, "show dmvpn", "P3d 60 秒後 RT02")
    sh(s, "show ip route 198.51.100.6", "P3d RT02")
    sh(s, "show crypto isakmp sa", "P3d RT02")
    kb.logtail(s, "P3d RT02 log")
    kb.logtail(devs["RT03"], "P3d RT03 log")
    ping(s, "8.8.8.8", source="Loopback1", repeat=5, title="P3d 最後 RT02→internet")
    flush("P3d 素朴なフルトンネル(他 spoke の NBMA が既定経路=トンネルへ再帰)")


def P3e(devs):
    """P3d の状態で、spoke 間「直接」トンネルの外側パケットが実際にどこを通るか+大きいパケット。"""
    P3d(devs)
    s = devs["RT02"]
    sh(s, "show ip cef 198.51.100.6", "P3e RT02")
    sh(s, "show ip cef 198.51.100.6 detail", "P3e RT02")
    sh(s, "show crypto ipsec sa peer 198.51.100.6 | include encaps|decaps|local crypto|remote crypto|path mtu",
       "P3e RT02")
    h = devs[HUB]
    sh(h, "clear ip nat translation *")
    sh(h, "show interfaces Tunnel0 | include packets", "P3e hub 前")
    for size in (100, 1300, 1372, 1400):
        ping(s, "10.0.3.1", source="Loopback1", repeat=5, title=f"P3e RT02→RT03 LAN size {size} df",
             ) if False else None
        sh(s, f"ping 10.0.3.1 source Loopback1 repeat 5 size {size} df-bit", f"P3e RT02→RT03 size {size} df")
        sh(s, f"ping 8.8.8.8 source Loopback1 repeat 5 size {size} df-bit", f"P3e RT02→internet size {size} df")
    sh(h, "show interfaces Tunnel0 | include packets", "P3e hub 後")
    sh(h, "show ip nat translations", "P3e hub")
    flush("P3e 素朴フルトンネルの spoke 間外側経路と MTU")


def _acl_hits(dev, name, title):
    out = sh(dev, f"show ip access-lists {name}", title)
    return out


def Q1(devs):
    """BL-210 PoC: 外側 IF の out ACL は DMVPN の何を通す必要があるか(自機発 GRE/ESP/UDP500 のどれに当たるか)。"""
    h = devs[HUB]
    reset(devs, title="Q1-0")
    note("== Q1: EDGE-OUT(out 方向)に IKE/ESP/ICMP だけ permit → DMVPN が生きるか・どの行に hit するか")
    conf(h, ["ip access-list extended EDGE-OUT",
             f"10 permit udp host {NBMA[HUB]} any eq isakmp",
             f"20 permit udp host {NBMA[HUB]} any eq non500-isakmp",
             f"30 permit esp host {NBMA[HUB]} any",
             "40 permit icmp any any",
             "90 deny ip any any log", "exit",
             "interface Ethernet0/0", "ip access-group EDGE-OUT out"], "Q1 EDGE-OUT 適用")
    reset(devs, wait=False)
    time.sleep(60)
    sh(h, "show dmvpn", "Q1 hub(out ACL: gre 無し)")
    _acl_hits(h, "EDGE-OUT", "Q1 hit")
    kb.logtail(h, "Q1 hub log", include="IPACCESS|DMVPN|CRYPTO")
    # gre を足して比較
    conf(h, ["ip access-list extended EDGE-OUT", f"35 permit gre host {NBMA[HUB]} any"], "Q1 gre 追加")
    reset(devs, wait=False)
    time.sleep(60)
    sh(h, "show dmvpn", "Q1 hub(out ACL: gre あり)")
    _acl_hits(h, "EDGE-OUT", "Q1 hit(gre あり)")
    # 後片付け
    conf(h, ["interface Ethernet0/0", "no ip access-group EDGE-OUT out", "exit",
             "no ip access-list extended EDGE-OUT"])
    reset(devs, title="Q1 後")
    flush("Q1 out 方向 ACL と DMVPN")


def Q2(devs):
    """BL-210 PoC: seq が詰まった区間への挿入= resequence の挙動(カウンタ・表示)と、udp 4500 permit 無しが非故障か。"""
    h = devs[HUB]
    note("== Q2: 詰まった seq への挿入(resequence)・4500 無し")
    conf(h, ["ip access-list extended Q2WALL",
             "10 deny ip 10.0.0.0 0.255.255.255 any",
             "11 deny ip 192.168.0.0 0.0.255.255 any",
             "12 remark === VPN (SEC-TEAM) ===",
             f"13 permit udp any host {NBMA[HUB]} eq isakmp",
             f"14 permit udp any host {NBMA[HUB]} eq non500-isakmp",
             f"15 permit icmp any host {NBMA[HUB]} echo",
             f"16 deny ip any host {NBMA[HUB]} log",
             "17 deny ip any any log", "exit",
             "interface Ethernet0/0", "ip access-group Q2WALL in"],
         "Q2 詰まった wall(esp 無し・remark 込み)を in に適用")
    sh(h, "show running-config | section access-list extended Q2WALL", "Q2 run(remark の seq)")
    reset(devs, wait=False)
    time.sleep(75)
    sh(h, "show dmvpn", "Q2 esp 無し hub")
    sh(h, "show crypto isakmp sa", "Q2 esp 無し hub")
    _acl_hits(h, "Q2WALL", "Q2 esp 無し hit")
    kb.logtail(h, "Q2 hub log", include="IPACCESS")
    conf(h, ["ip access-list extended Q2WALL", f"15 permit esp any host {NBMA[HUB]}"], "Q2 埋まっている seq 15 に挿入(拒否されるはず)")
    _acl_hits(h, "Q2WALL", "Q2 seq 15 挿入の結果")
    conf(h, ["ip access-list resequence Q2WALL 10 10"], "Q2 resequence")
    _acl_hits(h, "Q2WALL", "Q2 resequence 後(カウンタ保持?)")
    sh(h, "show running-config | section access-list extended Q2WALL", "Q2 resequence 後 run(remark も renumber?)")
    conf(h, ["ip access-list extended Q2WALL", f"65 permit esp any host {NBMA[HUB]}"], "Q2 65 に esp 挿入(deny 70 の直前)")
    t, out = kb.wait_for(lambda: hub_up(devs), timeout=180, step=15, what="esp 挿入後の登録(bounce なし)")
    note(f"Q2: esp 挿入(resequence 後・bounce なし)で 3 spoke UP まで {'%.0fs' % t if t is not None else '★180s 未達'}")
    _acl_hits(h, "Q2WALL", "Q2 挿入後 hit")
    # 4500 を外す(NAT-T 不使用なら非故障のはず)
    conf(h, ["ip access-list extended Q2WALL", "no 50"], "Q2 4500 permit(seq 50)を外す")
    reset(devs, wait=False)
    t, out = kb.wait_for(lambda: hub_up(devs), timeout=180, step=15, what="4500 無しで登録")
    note(f"Q2: udp 4500 permit 無しで 3 spoke UP まで {'%.0fs' % t if t is not None else '★180s 未達= 4500 は必要'}")
    _acl_hits(h, "Q2WALL", "Q2 4500 無し hit")
    conf(h, ["interface Ethernet0/0", "no ip access-group Q2WALL in", "exit",
             "no ip access-list extended Q2WALL"])
    reset(devs, title="Q2 後")
    flush("Q2 resequence と 4500")


def Q2b(devs):
    """Q2 のやり直し: resequence 後は remark が消えエントリだけ 10 刻み → esp は deny(60) の前= 55 に挿入。
    bounce なしで登録されるか。その後 4500 permit を外して(reset あり)非故障か。"""
    h = devs[HUB]
    note("== Q2b: resequence 後の正しい位置(55)へ esp 挿入・4500 無し")
    conf(h, ["ip access-list extended Q2WALL",
             "10 deny ip 10.0.0.0 0.255.255.255 any", "11 deny ip 192.168.0.0 0.0.255.255 any",
             "12 remark === VPN (SEC-TEAM) ===",
             f"13 permit udp any host {NBMA[HUB]} eq isakmp", f"14 permit udp any host {NBMA[HUB]} eq non500-isakmp",
             f"15 permit icmp any host {NBMA[HUB]} echo", f"16 deny ip any host {NBMA[HUB]} log",
             "17 deny ip any any log", "exit",
             "interface Ethernet0/0", "ip access-group Q2WALL in"], "Q2b wall 適用")
    reset(devs, wait=False)
    time.sleep(60)
    sh(h, "show dmvpn", "Q2b esp 無し hub")
    conf(h, ["ip access-list resequence Q2WALL 10 10"], "Q2b resequence")
    conf(h, ["ip access-list extended Q2WALL", f"55 permit esp any host {NBMA[HUB]}"], "Q2b 55 に esp 挿入")
    t, out = kb.wait_for(lambda: hub_up(devs), timeout=180, step=15, what="esp 挿入後の登録(bounce なし)")
    note(f"Q2b: esp 挿入(resequence 後・正しい位置・bounce なし)で 3 spoke UP まで {'%.0fs' % t if t is not None else '★180s 未達'}")
    _acl_hits(h, "Q2WALL", "Q2b 挿入後 hit")
    conf(h, ["ip access-list extended Q2WALL", "no 40"], "Q2b 4500 permit(seq 40)を外す")
    reset(devs, wait=False)
    t, out = kb.wait_for(lambda: hub_up(devs), timeout=180, step=15, what="4500 無しで登録")
    note(f"Q2b: udp 4500 permit 無し(reset あり)で 3 spoke UP まで {'%.0fs' % t if t is not None else '★180s 未達= 4500 は必要'}")
    _acl_hits(h, "Q2WALL", "Q2b 4500 無し hit")
    conf(h, ["interface Ethernet0/0", "no ip access-group Q2WALL in", "exit", "no ip access-list extended Q2WALL"])
    reset(devs, title="Q2b 後")
    flush("Q2b resequence 後の挿入位置と 4500")


def Q3(devs):
    """BL-211 C2 PoC: 打ちづらい名前の受理と、大小違いの profile 参照(存在しない名前)の挙動。"""
    h = devs[HUB]
    note("== Q3: 打ちづらい名前の受理 / 大小違い参照")
    r = conf(h, ["crypto isakmp key pR3sh4red-K3y#7 address 10.99.99.99",
                 "no crypto isakmp key pR3sh4red-K3y#7 address 10.99.99.99",
                 "crypto ipsec transform-set Ts-aEs256_Sha2.v1 esp-aes 256 esp-sha256-hmac", "mode transport", "exit",
                 "crypto ipsec profile IPsec.Prof_DmVPN-1", "set transform-set Ts-aEs256_Sha2.v1", "exit",
                 "ip access-list extended Sec_Edge-IN.v2", "10 permit ip any any", "exit",
                 "interface Tunnel0", "ip nhrp authentication nH0rP-k1", f"ip nhrp authentication {NHKEY}"],
             "Q3 打ちづらい名前(受理されるか)")
    sh(h, "show run | include Ts-aEs|IPsec.Prof|Sec_Edge|nhrp auth", "Q3 run")
    # 大小違いの参照: 定義は DMVPN-PROF、参照を DMVPN-Prof に
    kb.clear_log(h)
    conf(h, ["interface Tunnel0", "tunnel protection ipsec profile DMVPN-Prof"], "Q3 大小違い参照(存在しない名前)")
    sh(h, "show run | section interface Tunnel0|crypto ipsec profile", "Q3 参照後 run")
    sh(h, "show crypto ipsec profile", "Q3 profile 一覧")
    sh(h, "show ip interface brief | include Tunnel", "Q3 Tunnel 状態")
    kb.logtail(h, "Q3 log")
    reset(devs, wait=False)
    time.sleep(60)
    sh(h, "show dmvpn", "Q3 大小違い参照 hub")
    sh(h, "show crypto isakmp sa", "Q3 hub")
    sh(h, "show crypto ipsec sa | include peer|encaps|decaps|in use", "Q3 hub")
    sh(devs["RT02"], "show dmvpn", "Q3 RT02")
    conf(h, ["interface Tunnel0", "tunnel protection ipsec profile DMVPN-PROF"], "Q3 是正")
    sh(h, "show run | section crypto ipsec profile", "Q3 是正後 profile(空の Prof が残る?)")
    conf(h, ["no crypto ipsec profile DMVPN-Prof", "no crypto ipsec profile IPsec.Prof_DmVPN-1",
             "no crypto ipsec transform-set Ts-aEs256_Sha2.v1", "no ip access-list extended Sec_Edge-IN.v2"], "Q3 掃除")
    reset(devs, title="Q3 後")
    flush("Q3 打ちづらい名前と大小違い参照")


STEPS = {"P0": P0, "P2": P2, "P3": P3, "P3r": P3r, "P5x": P5x, "P3c": P3c, "P3d": P3d, "P3e": P3e,
         "Q1": Q1, "Q2": Q2, "Q2b": Q2b, "Q3": Q3}


def main():
    args = sys.argv[1:] or ["P0"]
    cl, creds = kb.client()
    if args == ["teardown"]:
        lab = kb.get_lab(cl)
        lab.stop(wait=True)
        print("stopped")
        return
    if args[0] == "build":
        kb.ensure_lab(cl)
        args = args[1:]
        if not args:
            return
    lab = kb.get_lab(cl)
    devs = kb.connect_all(lab, creds, labels=NODES)
    for s in args:
        print(f"\n===== {s} =====", flush=True)
        try:
            if s in WCASES:
                _run(WCASES)(devs, s)
            elif s in FCASES:
                _run(FCASES)(devs, s)
            else:
                STEPS[s](devs)
        except Exception:
            tb = traceback.format_exc()
            print(tb)
            block(f"{s} EXCEPTION", tb)
            flush(f"{s} (失敗)")
    for d in devs.values():
        try:
            d.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
