#!/usr/bin/env python3
"""BL-127 PoC: 経路選好紙面ファミリ(shape=pref)の前提挙動+書式スイープ。

設計メモ= problems/_drafts/PREF-PAPER.design.md §7。
CML に _POC-PREF(IOL 10台)を作成し、コンソール直駆動で
  OSPF ブロック(RO1〜RO5・型優先/E1E2/forward metric)と
  EIGRP ブロック(RE1〜RE5・FD/RD/FC/variance)
を単離観測する。mgmt/SSH は使わない(CVAC 罠回避・poc/bgpbest の型を踏襲)。

■ OSPF ブロック(観測点= RO1・全 area 0 側)
    RO2(ASBR/intra源) --e0/0[cost10]-- RO1 --e0/1[cost10]-- RO3(ABR) --area2-- RO4
                                        |e0/2[cost100]
                                       RO5(ASBR)
  10.98.8.0/24 = RO2 の Lo98(area0・cost500) と RO4 の Lo98(area2・cost1) の両方
                 → RO1 では intra(510) vs inter(21) が同時に見える
  10.97.7.0/24 = RO2 が E1 metric100 / RO5 が E2 metric10 で再配送 → 型優先
  10.96.6.0/24 = 両者 E2 metric20 → forward metric(10 vs 100)で決着

■ EIGRP ブロック(観測点= RE1・AS100)
    RE2 --e0/1[dly100]-- RE5(Lo99=10.99.9.0/24)
   /e0/0[dly100]          |
  RE1 --e0/1[dly300]-- RE3 --e0/1[dly100]--+
   \\e0/2[dly100]-- RE4 --e0/1[dly400]-----+
  metric = 256*(10^7/10000 + Σdelay(10us単位)) ・ Lo99 の delay=500 が全経路共通
    via RE2: RD=409600 FD=435200 (successor)
    via RE3: RD=409600 FD=486400 (FS・FD比 1.12)
    via RE4: RD=486400 FD=512000 (RD>FD_succ → FC 不成立)
  ★E2 探針で RE4 側 delay を 200 に落とし **RD==FD_succ ちょうど**を作る
    → 等号が FS になるかを実測(モデルの核)。

使い方: probe.py [チェック名...] (無指定=全部)。
  チェック名: o1 o2 o3 o4 o5 o6 o7 e1 e2 e3 e4
結果は results-raw.md へ追記。
"""
import re
import sys
import time
from pathlib import Path

import urllib3
import yaml
from virl2_client import ClientLibrary
from pyats.topology import loader

urllib3.disable_warnings()

OUT = Path(__file__).resolve().parent / "results-raw.md"
CML = ("https://10.1.10.10", "SUZUKI", "suzugross")
LAB_TITLE = "_POC-PREF"

OSPF_NODES = ["RO1", "RO2", "RO3", "RO4", "RO5"]
# ★RE6 は E2E(e2e.py)で 4 経路盤面(fs_allthat)を再現するために追加した
EIGRP_NODES = ["RE1", "RE2", "RE3", "RE4", "RE5", "RE6"]
NODES = OSPF_NODES + EIGRP_NODES

# 張るリンク: (ノードA, Aのslot, ノードB, Bのslot)。slot→IF名は e{s//4}/{s%4}
LINKS = [("RO1", 0, "RO2", 0), ("RO1", 1, "RO3", 0), ("RO1", 2, "RO5", 0),
         ("RO3", 1, "RO4", 0),
         ("RE1", 0, "RE2", 0), ("RE1", 1, "RE3", 0), ("RE1", 2, "RE4", 0),
         ("RE2", 1, "RE5", 0), ("RE3", 1, "RE5", 1), ("RE4", 1, "RE5", 2),
         ("RE1", 3, "RE6", 0), ("RE6", 1, "RE5", 3)]

P98 = "10.98.8.0"      # intra vs inter
P97 = "10.97.7.0"      # E1 vs E2
P96 = "10.96.6.0"      # E2 vs E2 (forward metric)
P95 = "10.95.5.0"      # NSSA N2 (o7)
P94 = "10.94.4.0"      # NSSA N1 (o7)
P99 = "10.99.9.0"      # EIGRP 宛先

BASE = {
    # ---------------- OSPF ブロック ----------------
    "RO1": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.10.12.1 255.255.255.0",
        "ip ospf cost 10", "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.10.13.1 255.255.255.0",
        "ip ospf cost 10", "no shutdown", "exit",
        "interface Ethernet0/2", "ip address 10.10.15.1 255.255.255.0",
        "ip ospf cost 100", "no shutdown", "exit",
        "interface Loopback0", "ip address 1.1.1.1 255.255.255.255", "exit",
        "router ospf 1", "router-id 1.1.1.1",
        "network 10.10.12.0 0.0.0.255 area 0",
        "network 10.10.13.0 0.0.0.255 area 0",
        "network 10.10.15.0 0.0.0.255 area 0",
        "network 1.1.1.1 0.0.0.0 area 0", "exit",
        "no logging console",
    ],
    "RO2": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.10.12.2 255.255.255.0",
        "ip ospf cost 10", "no shutdown", "exit",
        "interface Loopback0", "ip address 2.2.2.2 255.255.255.255", "exit",
        "interface Loopback98", "ip address 10.98.8.1 255.255.255.0",
        "ip ospf network point-to-point", "ip ospf cost 500", "exit",
        "ip route 10.97.7.0 255.255.255.0 Null0",
        "ip route 10.96.6.0 255.255.255.0 Null0",
        "ip prefix-list PL97 permit 10.97.7.0/24",
        "ip prefix-list PL96 permit 10.96.6.0/24",
        "route-map RM-RD permit 10", "match ip address prefix-list PL97",
        "set metric 100", "set metric-type type-1", "exit",
        "route-map RM-RD permit 20", "match ip address prefix-list PL96",
        "set metric 20", "set metric-type type-2", "exit",
        "router ospf 1", "router-id 2.2.2.2",
        "network 10.10.12.0 0.0.0.255 area 0",
        "network 2.2.2.2 0.0.0.0 area 0",
        "network 10.98.8.0 0.0.0.255 area 0",
        "redistribute static subnets route-map RM-RD", "exit",
        "no logging console",
    ],
    "RO3": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.10.13.3 255.255.255.0",
        "ip ospf cost 10", "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.10.34.3 255.255.255.0",
        "ip ospf cost 10", "no shutdown", "exit",
        "interface Loopback0", "ip address 3.3.3.3 255.255.255.255", "exit",
        "router ospf 1", "router-id 3.3.3.3",
        "network 10.10.13.0 0.0.0.255 area 0",
        "network 3.3.3.3 0.0.0.0 area 0",
        "network 10.10.34.0 0.0.0.255 area 2", "exit",
        "no logging console",
    ],
    "RO4": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.10.34.4 255.255.255.0",
        "ip ospf cost 10", "no shutdown", "exit",
        "interface Loopback0", "ip address 4.4.4.4 255.255.255.255", "exit",
        "interface Loopback98", "ip address 10.98.8.1 255.255.255.0",
        "ip ospf network point-to-point", "ip ospf cost 1", "exit",
        "ip route 10.95.5.0 255.255.255.0 Null0",
        "ip route 10.94.4.0 255.255.255.0 Null0",
        "ip prefix-list PL95 permit 10.95.5.0/24",
        "ip prefix-list PL94 permit 10.94.4.0/24",
        "route-map RM-N permit 10", "match ip address prefix-list PL95",
        "set metric 20", "set metric-type type-2", "exit",
        "route-map RM-N permit 20", "match ip address prefix-list PL94",
        "set metric 30", "set metric-type type-1", "exit",
        "router ospf 1", "router-id 4.4.4.4",
        "network 10.10.34.0 0.0.0.255 area 2",
        "network 4.4.4.4 0.0.0.0 area 2",
        "network 10.98.8.0 0.0.0.255 area 2", "exit",
        "no logging console",
    ],
    "RO5": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.10.15.5 255.255.255.0",
        "ip ospf cost 100", "no shutdown", "exit",
        "interface Loopback0", "ip address 5.5.5.5 255.255.255.255", "exit",
        "ip route 10.97.7.0 255.255.255.0 Null0",
        "ip route 10.96.6.0 255.255.255.0 Null0",
        "ip prefix-list PL97 permit 10.97.7.0/24",
        "ip prefix-list PL96 permit 10.96.6.0/24",
        "route-map RM-RD permit 10", "match ip address prefix-list PL97",
        "set metric 10", "set metric-type type-2", "exit",
        "route-map RM-RD permit 20", "match ip address prefix-list PL96",
        "set metric 20", "set metric-type type-2", "exit",
        "router ospf 1", "router-id 5.5.5.5",
        "network 10.10.15.0 0.0.0.255 area 0",
        "network 5.5.5.5 0.0.0.0 area 0",
        "redistribute static subnets route-map RM-RD", "exit",
        "no logging console",
    ],
    # ---------------- EIGRP ブロック ----------------
    "RE1": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.20.12.1 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.20.13.1 255.255.255.0",
        "delay 300", "no shutdown", "exit",
        "interface Ethernet0/2", "ip address 10.20.14.1 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/3", "ip address 10.20.16.1 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Loopback0", "ip address 11.11.11.11 255.255.255.255", "exit",
        "router eigrp 100", "eigrp router-id 11.11.11.11",
        "network 10.20.0.0 0.0.255.255", "network 11.11.11.11 0.0.0.0",
        "no auto-summary", "exit",
        "no logging console",
    ],
    "RE2": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.20.12.2 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.20.25.2 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Loopback0", "ip address 22.22.22.22 255.255.255.255", "exit",
        "router eigrp 100", "eigrp router-id 22.22.22.22",
        "network 10.20.0.0 0.0.255.255", "network 22.22.22.22 0.0.0.0",
        "no auto-summary", "exit",
        "no logging console",
    ],
    "RE3": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.20.13.3 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.20.35.3 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Loopback0", "ip address 33.33.33.33 255.255.255.255", "exit",
        "router eigrp 100", "eigrp router-id 33.33.33.33",
        "network 10.20.0.0 0.0.255.255", "network 33.33.33.33 0.0.0.0",
        "no auto-summary", "exit",
        "no logging console",
    ],
    "RE4": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.20.14.4 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.20.45.4 255.255.255.0",
        "delay 400", "no shutdown", "exit",
        "interface Loopback0", "ip address 44.44.44.44 255.255.255.255", "exit",
        "router eigrp 100", "eigrp router-id 44.44.44.44",
        "network 10.20.0.0 0.0.255.255", "network 44.44.44.44 0.0.0.0",
        "no auto-summary", "exit",
        "no logging console",
    ],
    "RE6": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.20.16.6 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.20.65.6 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Loopback0", "ip address 66.66.66.66 255.255.255.255", "exit",
        "router eigrp 100", "eigrp router-id 66.66.66.66",
        "network 10.20.0.0 0.0.255.255", "network 66.66.66.66 0.0.0.0",
        "no auto-summary", "exit",
        "no logging console",
    ],
    "RE5": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.20.25.5 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.20.35.5 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/2", "ip address 10.20.45.5 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Ethernet0/3", "ip address 10.20.65.5 255.255.255.0",
        "delay 100", "no shutdown", "exit",
        "interface Loopback0", "ip address 55.55.55.55 255.255.255.255", "exit",
        "interface Loopback99", "ip address 10.99.9.1 255.255.255.0", "exit",
        "router eigrp 100", "eigrp router-id 55.55.55.55",
        "network 10.20.0.0 0.0.255.255", "network 55.55.55.55 0.0.0.0",
        "network 10.99.9.0 0.0.0.255",
        "no auto-summary", "exit",
        "no logging console",
    ],
}

POS = {"RO1": (0, -260), "RO2": (-220, -380), "RO3": (220, -380),
       "RO4": (420, -260), "RO5": (0, -80),
       "RE1": (0, 160), "RE2": (-320, 60), "RE3": (-100, 60),
       "RE4": (120, 60), "RE6": (340, 60), "RE5": (0, 320)}


# ---------------- CML / コンソール(poc/bgpbest の型) ----------------
def _ifname(slot):
    return f"Ethernet{slot // 4}/{slot % 4}"


def _iface(lab, label, slot):
    """slot 指定で IF を引く。無ければ作る(IOL は張った分しか実装されない)。"""
    name = _ifname(slot)
    node = lab.get_node_by_label(label)
    for _ in range(4):
        for i in node.interfaces():
            if i.label == name:
                return i
        try:
            node.create_interface(slot=slot, wait=True)
        except Exception as e:
            print(f"    create_interface({label},{slot}): {type(e).__name__}")
        lab.sync(topology_only=True)
        time.sleep(1)
    raise RuntimeError(f"{label} に {name} が作れない")


def ensure_lab(client):
    labs = client.find_labs_by_title(LAB_TITLE)
    if labs:
        lab = labs[0]
        print(f"[i] 既存ラボ {LAB_TITLE} ({lab.state()})")
    else:
        print(f"[i] ラボ {LAB_TITLE} を新規作成")
        lab = client.create_lab(LAB_TITLE)
    have = {n.label for n in lab.nodes()}
    for label in NODES:
        if label in have:
            continue
        n = lab.create_node(label, "iol-xe", *POS[label],
                            populate_interfaces=True)
        n.configuration = f"hostname {label}\nno ip domain lookup\n"
    lab.sync(topology_only=True)
    for a, aslot, b, bslot in LINKS:
        ia, ib = _iface(lab, a, aslot), _iface(lab, b, bslot)
        if ia.connected or ib.connected:
            continue
        print(f"[i] link {a} {_ifname(aslot)} <-> {b} {_ifname(bslot)}")
        lab.create_link(ia, ib)
    if lab.state() != "STARTED":
        print("[i] lab start...")
        lab.start(wait=True)
    for n in lab.nodes():
        print(f"    {n.label}: {n.state}")
    return lab


def connect_all(lab, required=("RO1", "RE1")):
    tb = yaml.safe_load(lab.get_pyats_testbed())
    for name, dev in (tb.get("devices") or {}).items():
        creds = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            creds["default"] = {"username": CML[1], "password": CML[2]}
        else:
            creds["default"] = {"username": "cisco", "password": "cisco"}
            creds["enable"] = {"password": "cisco"}
    testbed = loader.load(tb)
    devs = {}
    for label in NODES:
        dev = testbed.devices[label]
        for attempt in range(1, 4):
            try:
                dev.connect(via="a", log_stdout=False, learn_hostname=True,
                            connection_timeout=120)
                dev.enable()
                dev.execute("terminal length 0")
                devs[label] = dev
                break
            except Exception as e:
                print(f"    {label}: connect attempt {attempt} failed "
                      f"({type(e).__name__})")
                try:
                    dev.disconnect()
                except Exception:
                    pass
                time.sleep(8)
        else:
            if label in required:
                raise RuntimeError(f"{label}: console 接続不能(必須ノード)")
            print(f"    [!] {label}: console 接続不能")
    return devs


def conf(dev, lines, log=None):
    out = dev.configure(lines, error_pattern=[], timeout=180)
    text = out if isinstance(out, str) else "\n".join(
        v for v in out.values() if isinstance(v, str))
    errs = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("%")]
    for e in errs:
        print(f"    ! {e}")
        if log is not None:
            log.append(f"- CLI応答: `{e}`")
    return errs


def sh(dev, cmd):
    return dev.execute(cmd, timeout=180)


def block(log, title, text):
    log.append(f"\n{title}:\n```\n{text.strip()}\n```")


def wait(pred, timeout=240, every=5, label=""):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if pred():
                return round(time.time() - t0, 1)
        except Exception as e:
            print(f"    wait({label}): {type(e).__name__}")
        time.sleep(every)
    print(f"    [!] wait timeout: {label}")
    return -1


def push_base(devs):
    """毎回全ノードに投入(全行冪等)。途中中断の再開に強い。"""
    for label in NODES:
        if label not in devs:
            print(f"[i] {label}: 未接続のため base 投入をスキップ")
            continue
        print(f"[i] {label}: base 設定を投入")
        conf(devs[label], BASE[label])


def re1_delay(devs, iface, val):
    conf(devs["RE1"], [f"interface {iface}", f"delay {val}", "exit"])


def re_far_delay(devs, node, iface, val):
    conf(devs[node], [f"interface {iface}", f"delay {val}", "exit"])


def variance(devs, v):
    lines = ["router eigrp 100"]
    lines.append("no variance" if v is None else f"variance {v}")
    lines.append("exit")
    conf(devs["RE1"], lines)


def route_seen(dev, pfx):
    out = sh(dev, f"show ip route {pfx}")
    return "not in table" not in out and "Network not in table" not in out


def n_links(dev, pfx=P99):
    """all-links に出ている当該プレフィックスの via 本数(Connected 除く)。

    ★初回計測の失敗録: 隣接が上がりきる前に採取すると経路が 2 本しか出ない
    (RE4 が最後に上がる)。all-links の本数で収束を待つこと。
    """
    out = sh(dev, "show ip eigrp topology all-links")
    m = re.search(rf"^P {re.escape(pfx)}/24,.*?(?=^P |\Z)", out, re.M | re.S)
    return len(re.findall(r"^\s+via \d", m.group(0), re.M)) if m else 0


# ---------------- 探針 ----------------
def o1(devs, log):
    """書式採取: 各型の表行 + detail ブロック。"""
    d = devs["RO1"]
    wait(lambda: route_seen(d, P98) and route_seen(d, P97) and route_seen(d, P96),
         label="RO1 に3プレフィックスが載る")
    block(log, "RO1 `show ip route ospf`", sh(d, "show ip route ospf"))
    for p, tag in ((P98, "intra vs inter"), (P97, "E1 vs E2"),
                   (P96, "E2 vs E2")):
        block(log, f"RO1 `show ip route {p}` ({tag})", sh(d, f"show ip route {p}"))


def o2(devs, log):
    """intra > inter: コスト 510 の O が コスト 21 の O IA に勝つ。"""
    d = devs["RO1"]
    out = sh(d, f"show ip route {P98}")
    block(log, f"O2 RO1 `show ip route {P98}`", out)
    block(log, "O2 RO1 `show ip ospf database summary 10.98.8.0`",
          sh(d, "show ip ospf database summary 10.98.8.0"))
    m = re.search(r'Known via "ospf 1", distance (\d+), metric (\d+)', out)
    log.append(f"- **判定**: metric={m.group(2) if m else '?'} / "
               f"表示型= {'inter area' if 'inter area' in out else 'intra(型記載なし)'}"
               f" → intra が勝てば metric 510 のはず")


def o3(devs, log):
    """E1 > E2: E1(110) が E2(10) に勝つ。"""
    d = devs["RO1"]
    out = sh(d, f"show ip route {P97}")
    block(log, f"O3 RO1 `show ip route {P97}`", out)
    log.append(f"- **判定**: `type extern 1` かつ metric 110 なら型優先+累積の実証")


def o4(devs, log):
    """E2 同値 → forward metric。"""
    d = devs["RO1"]
    out = sh(d, f"show ip route {P96}")
    block(log, f"O4 RO1 `show ip route {P96}`", out)
    log.append("- **判定**: via 10.10.12.2(RO2)・forward metric 10 なら実証"
               "(RO5 側は forward metric 100)")


def o5(devs, log):
    """E1 の累積を ASBR 側コストの変更で追試(RO1 の e0/0 cost 10→60)。"""
    d = devs["RO1"]
    conf(d, ["interface Ethernet0/0", "ip ospf cost 60", "exit"])
    time.sleep(15)
    out = sh(d, f"show ip route {P97}")
    block(log, "O5 RO1 e0/0 cost 60 後 `show ip route 10.97.7.0`", out)
    log.append("- **判定**: E1 metric が 110→160 に動けば累積(外部100+内部60)")
    out2 = sh(d, f"show ip route {P96}")
    block(log, "O5 同条件 `show ip route 10.96.6.0` (E2)", out2)
    log.append("- **判定**: E2 の metric は 20 のまま・forward metric だけ 10→60 "
               "(それでも RO5 の 100 より小さいので勝者不変)")
    conf(d, ["interface Ethernet0/0", "ip ospf cost 10", "exit"])
    time.sleep(15)


def o6(devs, log):
    """LSA 断片の書式採取。"""
    d = devs["RO1"]
    block(log, "O6 RO1 `show ip ospf database external 10.97.7.0`",
          sh(d, "show ip ospf database external 10.97.7.0"))
    block(log, "O6 RO1 `show ip ospf database external 10.96.6.0`",
          sh(d, "show ip ospf database external 10.96.6.0"))
    block(log, "O6 RO1 `show ip ospf database`", sh(d, "show ip ospf database"))
    block(log, "O6 RO1 `show ip ospf border-routers`",
          sh(d, "show ip ospf border-routers"))


def o7(devs, log):
    """NSSA: area2 を NSSA 化し RO3(ABR)から O N1/O N2 を採取。"""
    conf(devs["RO3"], ["router ospf 1", "area 2 nssa", "exit"])
    conf(devs["RO4"], ["router ospf 1", "area 2 nssa",
                       "redistribute static subnets route-map RM-N", "exit"])
    d3 = devs["RO3"]
    wait(lambda: route_seen(d3, P95), label="RO3 に N2 が載る")
    block(log, "O7 RO3 `show ip route ospf` (area2=NSSA)",
          sh(d3, "show ip route ospf"))
    block(log, f"O7 RO3 `show ip route {P95}` (N2)", sh(d3, f"show ip route {P95}"))
    block(log, f"O7 RO3 `show ip route {P94}` (N1)", sh(d3, f"show ip route {P94}"))
    block(log, "O7 RO3 `show ip ospf database nssa-external 10.95.5.0`",
          sh(d3, "show ip ospf database nssa-external 10.95.5.0"))
    block(log, "O7 RO1 `show ip route ospf` (翻訳後 area0 側)",
          sh(devs["RO1"], "show ip route ospf"))


def e1(devs, log):
    """書式採取: topology / all-links / route detail。"""
    d = devs["RE1"]
    wait(lambda: n_links(d, P99) >= 3, label="RE1 の all-links に3経路")
    block(log, "E1 RE1 `show ip eigrp topology`", sh(d, "show ip eigrp topology"))
    block(log, f"E1 RE1 `show ip eigrp topology {P99} 255.255.255.0`",
          sh(d, f"show ip eigrp topology {P99} 255.255.255.0"))
    block(log, "E1 RE1 `show ip eigrp topology all-links`",
          sh(d, "show ip eigrp topology all-links"))
    block(log, f"E1 RE1 `show ip route {P99}`", sh(d, f"show ip route {P99}"))
    block(log, "E1 RE1 `show ip eigrp neighbors`",
          sh(d, "show ip eigrp neighbors"))
    log.append("- **期待値**: via RE2 FD=435200(successor) / via RE3 RD=409600 "
               "FD=486400(FS) / via RE4 RD=486400 FD=512000(FC不成立)")


def e2(devs, log):
    """★RD == FD(successor) ちょうどの経路が FS になるか。"""
    d = devs["RE1"]
    re_far_delay(devs, "RE4", "Ethernet0/1", 200)   # RD_C = 435200 = FD_A
    time.sleep(20)
    wait(lambda: n_links(d, P99) >= 3, label="E2 収束(3経路)")
    block(log, "E2 RE4 e0/1 delay 200 後 `show ip eigrp topology all-links`",
          sh(d, "show ip eigrp topology all-links"))
    block(log, f"E2 `show ip eigrp topology {P99} 255.255.255.0`",
          sh(d, f"show ip eigrp topology {P99} 255.255.255.0"))
    variance(devs, 4)
    time.sleep(20)
    out = sh(d, f"show ip route {P99}")
    block(log, "E2 variance 4 で `show ip route 10.99.9.0`", out)
    log.append("- **判定**: RD(435200) == FD_succ(435200) の RE4 経路が "
               "**乗らなければ FC は厳密不等号**(モデルの核)。"
               "乗ってしまうなら等号可としてモデルを直す")
    variance(devs, None)
    re_far_delay(devs, "RE4", "Ethernet0/1", 400)
    time.sleep(20)


def e3(devs, log):
    """variance 2 = FS のみ乗る(非 FC は乗らない)。"""
    d = devs["RE1"]
    wait(lambda: n_links(d, P99) >= 3, label="E3 開始前の収束(3経路)")
    variance(devs, 2)
    time.sleep(20)
    block(log, "E3 variance 2 `show ip route 10.99.9.0`",
          sh(d, f"show ip route {P99}"))
    block(log, "E3 variance 2 `show ip eigrp topology`",
          sh(d, "show ip eigrp topology"))
    log.append("- **判定**: via RE2(FD 435200)+via RE3(FD 486400)の2本のみ・"
               "RE4(非FC)は倍率 2 でも乗らない")
    variance(devs, None)
    time.sleep(15)


def e4(devs, log):
    """倍率境界: FS だが FD が範囲外 → 乗らない。"""
    d = devs["RE1"]
    re1_delay(devs, "Ethernet0/1", 2000)    # FD_B = 921600 (比 2.117)
    time.sleep(20)
    block(log, "E4 RE1 e0/1 delay 2000 `show ip eigrp topology all-links`",
          sh(d, "show ip eigrp topology all-links"))
    variance(devs, 2)
    time.sleep(20)
    block(log, "E4 variance 2 `show ip route 10.99.9.0`",
          sh(d, f"show ip route {P99}"))
    log.append("- **判定**: FS(RD 409600 < 435200)だが FD 921600 > 2×435200 → 乗らない")
    variance(devs, 3)
    time.sleep(20)
    block(log, "E4 variance 3 `show ip route 10.99.9.0`",
          sh(d, f"show ip route {P99}"))
    log.append("- **判定**: 倍率 3 で乗る(921600 <= 3×435200=1305600)")
    variance(devs, None)
    re1_delay(devs, "Ethernet0/1", 300)
    time.sleep(15)


CHECKS = {"o1": o1, "o2": o2, "o3": o3, "o4": o4, "o5": o5, "o6": o6, "o7": o7,
          "e1": e1, "e2": e2, "e3": e3, "e4": e4}


def main():
    want = [a.lower() for a in sys.argv[1:]] or list(CHECKS)
    bad = [w for w in want if w not in CHECKS]
    if bad:
        raise SystemExit(f"不明なチェック: {bad} (選択肢: {list(CHECKS)})")
    client = ClientLibrary(CML[0], CML[1], CML[2], ssl_verify=False)
    lab = ensure_lab(client)
    print("[i] console 接続...")
    devs = connect_all(lab)
    push_base(devs)
    log = [f"\n\n# 実行 {time.strftime('%Y-%m-%d %H:%M:%S')} — checks={want}"]
    for name in want:
        print(f"[i] === {name} ===")
        log.append(f"\n## {name}")
        try:
            CHECKS[name](devs, log)
        except Exception as e:
            print(f"    [!] {name} 失敗: {type(e).__name__}: {e}")
            log.append(f"- **失敗**: {type(e).__name__}: {e}")
        OUT.write_text((OUT.read_text() if OUT.exists() else "") +
                       "\n".join(log) + "\n")
        log = []
    print(f"[i] 結果: {OUT}")


if __name__ == "__main__":
    main()
