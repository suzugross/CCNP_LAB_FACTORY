#!/usr/bin/env python3
"""BL-112 PoC: BGP ベストパス紙面ファミリ(shape=bgpbest)の前提挙動スイープ。

設計メモ= problems/_drafts/BGPBEST-PAPER.design.md §8。
CML に POC-BGPBEST(IOL 6台)を作成し、コンソール直駆動で RT01(視点)の
経路候補を組み替えて決定リストの各段を単離観測する。
mgmt/SSH は使わない(CVAC 罠回避・poc/acl の型を踏襲)。

トポロジ(全 eBGP/iBGP の視点は RT01=AS65100):
      RT02(AS65200) --e0/1-- RT05(AS65100)      同一プレフィックス
     /  e0/0                  |e0/0             198.51.100.0/24 を
  RT01 --e0/1-- RT03(AS65200)-e0/1- RT06        RT02/RT03/RT04 が起源広告
     \\  e0/2                  (AS65100)
      RT04(AS65300)           RT05/RT06 は iBGP(Lo0 ピア+next-hop-self)
  RT01-RT05 は OSPF cost10 / RT01-RT06 は cost100(段8=IGP metric 用)
  eBGP 区間(10.0.25.0/24, 10.0.36.0/24)は OSPF に載せない(B15=inaccessible 用)

観測軸(design §8): B1 表書式 / B2 detail 書式 / B3 weight / B4 LP(+iBGP伝播) /
  B5 自機起源32768 / B7 origin / B8 MED同一AS / B10 MED欠落=0・missing-as-worst /
  B11 eBGP>iBGP / B12 IGP metric(+コスト入替の反応時間) / B13 oldest→compare-routerid /
  B15 next-hop-self 欠落=inaccessible / B16 LP を eBGP へ set out した実挙動

使い方: probe.py [チェック名...] (無指定=全部)。結果は results-raw.md へ追記。
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
LAB_TITLE = "POC-BGPBEST"
NODES = ["RT01", "RT02", "RT03", "RT04", "RT05", "RT06"]
PFX = "198.51.100.0"

# 張るリンク: (ノードA, Aのslot, ノードB, Bのslot)。slot→IF名は e{s//4}/{s%4}
LINKS = [("RT01", 0, "RT02", 0), ("RT01", 1, "RT03", 0), ("RT01", 2, "RT04", 0),
         ("RT01", 3, "RT05", 0), ("RT01", 4, "RT06", 0),
         ("RT05", 1, "RT02", 1), ("RT06", 1, "RT03", 1)]

E = {"RT02": "10.0.12.2", "RT03": "10.0.13.3", "RT04": "10.0.14.4",
     "RT05": "5.5.5.5", "RT06": "6.6.6.6"}          # RT01 から見た neighbor

BASE = {
    "RT01": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.12.1 255.255.255.0",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.13.1 255.255.255.0",
        "no shutdown", "exit",
        "interface Ethernet0/2", "ip address 10.0.14.1 255.255.255.0",
        "no shutdown", "exit",
        "interface Ethernet0/3", "ip address 10.0.15.1 255.255.255.0",
        "ip ospf cost 10", "no shutdown", "exit",
        "interface Ethernet1/0", "ip address 10.0.16.1 255.255.255.0",
        "ip ospf cost 100", "no shutdown", "exit",
        "interface Loopback0", "ip address 1.1.1.1 255.255.255.255", "exit",
        "router ospf 1", "router-id 1.1.1.1",
        "network 10.0.15.0 0.0.0.255 area 0", "network 10.0.16.0 0.0.0.255 area 0",
        "network 1.1.1.1 0.0.0.0 area 0", "exit",
        "router bgp 65100", "bgp router-id 1.1.1.1", "bgp log-neighbor-changes",
        "neighbor 10.0.12.2 remote-as 65200",
        "neighbor 10.0.13.3 remote-as 65200",
        "neighbor 10.0.14.4 remote-as 65300",
        "neighbor 5.5.5.5 remote-as 65100",
        "neighbor 5.5.5.5 update-source Loopback0",
        "neighbor 6.6.6.6 remote-as 65100",
        "neighbor 6.6.6.6 update-source Loopback0",
        "address-family ipv4",
        "neighbor 10.0.12.2 activate", "neighbor 10.0.13.3 activate",
        "neighbor 10.0.14.4 activate",
        "neighbor 5.5.5.5 activate", "neighbor 6.6.6.6 activate",
        "exit-address-family", "exit",
        "logging buffered 64000 informational", "no logging console",
    ],
    "RT02": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.12.2 255.255.255.0",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.25.2 255.255.255.0",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 2.2.2.2 255.255.255.255", "exit",
        "interface Loopback100", "ip address 198.51.100.2 255.255.255.0", "exit",
        "router bgp 65200", "bgp router-id 2.2.2.2",
        "neighbor 10.0.12.1 remote-as 65100",
        "neighbor 10.0.25.5 remote-as 65100",
        "address-family ipv4",
        "network 198.51.100.0 mask 255.255.255.0",
        "neighbor 10.0.12.1 activate", "neighbor 10.0.25.5 activate",
        "exit-address-family", "exit",
        "no logging console",
    ],
    "RT03": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.13.3 255.255.255.0",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.36.3 255.255.255.0",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 3.3.3.3 255.255.255.255", "exit",
        "interface Loopback100", "ip address 198.51.100.3 255.255.255.0", "exit",
        "router bgp 65200", "bgp router-id 3.3.3.3",
        "neighbor 10.0.13.1 remote-as 65100",
        "neighbor 10.0.36.6 remote-as 65100",
        "address-family ipv4",
        "network 198.51.100.0 mask 255.255.255.0",
        "neighbor 10.0.13.1 activate", "neighbor 10.0.36.6 activate",
        "exit-address-family", "exit",
        "no logging console",
    ],
    "RT04": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.14.4 255.255.255.0",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 4.4.4.4 255.255.255.255", "exit",
        "interface Loopback100", "ip address 198.51.100.4 255.255.255.0", "exit",
        "router bgp 65300", "bgp router-id 4.4.4.4",
        "neighbor 10.0.14.1 remote-as 65100",
        "address-family ipv4",
        "network 198.51.100.0 mask 255.255.255.0",
        "neighbor 10.0.14.1 activate",
        "exit-address-family", "exit",
        "no logging console",
    ],
    "RT05": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.15.5 255.255.255.0",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.25.5 255.255.255.0",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 5.5.5.5 255.255.255.255", "exit",
        "router ospf 1", "router-id 5.5.5.5",
        "network 10.0.15.0 0.0.0.255 area 0", "network 5.5.5.5 0.0.0.0 area 0",
        "exit",
        "router bgp 65100", "bgp router-id 5.5.5.5",
        "neighbor 1.1.1.1 remote-as 65100",
        "neighbor 1.1.1.1 update-source Loopback0",
        "neighbor 10.0.25.2 remote-as 65200",
        "address-family ipv4",
        "neighbor 1.1.1.1 activate", "neighbor 1.1.1.1 next-hop-self",
        "neighbor 10.0.25.2 activate",
        "exit-address-family", "exit",
        "no logging console",
    ],
    "RT06": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.16.6 255.255.255.0",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.36.6 255.255.255.0",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 6.6.6.6 255.255.255.255", "exit",
        "router ospf 1", "router-id 6.6.6.6",
        "network 10.0.16.0 0.0.0.255 area 0", "network 6.6.6.6 0.0.0.0 area 0",
        "exit",
        "router bgp 65100", "bgp router-id 6.6.6.6",
        "neighbor 1.1.1.1 remote-as 65100",
        "neighbor 1.1.1.1 update-source Loopback0",
        "neighbor 10.0.36.3 remote-as 65200",
        "address-family ipv4",
        "neighbor 1.1.1.1 activate", "neighbor 1.1.1.1 next-hop-self",
        "neighbor 10.0.36.3 activate",
        "exit-address-family", "exit",
        "no logging console",
    ],
}


# ---------------- CML / コンソール(poc/acl/sweep.py の型) ----------------
def _ifname(slot):
    return f"Ethernet{slot // 4}/{slot % 4}"


def _iface(lab, label, slot):
    """slot 指定で IF を引く。無ければ作る(IOL は張った分しか実装されない)。"""
    name = _ifname(slot)
    node = lab.get_node_by_label(label)
    for attempt in range(4):
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
    pos = {"RT01": (0, 0), "RT02": (-200, -140), "RT03": (-200, 140),
           "RT04": (0, 260), "RT05": (220, -140), "RT06": (220, 140)}
    have = {n.label for n in lab.nodes()}
    for label in NODES:
        if label in have:
            continue
        n = lab.create_node(label, "iol-xe", *pos[label],
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


def connect_all(lab, required=("RT01",)):
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
    out = dev.configure(lines, error_pattern=[], timeout=120)
    text = out if isinstance(out, str) else "\n".join(
        v for v in out.values() if isinstance(v, str))
    errs = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("%")]
    for e in errs:
        print(f"    ! {e}")
        if log is not None:
            log.append(f"- CLI応答: `{e}`")
    return errs


def sh(dev, cmd):
    return dev.execute(cmd, timeout=120)


def block(log, title, text):
    log.append(f"\n{title}:\n```\n{text.strip()}\n```")


def wait(pred, timeout=180, every=5, label=""):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return time.time() - t0
        time.sleep(every)
    print(f"    [!] wait timeout: {label}")
    return -1


# ---------------- BGP 観測ヘルパ ----------------
def push_base(devs):
    """毎回全ノードに投入(全行冪等)。途中中断の再開に強い(acl PoC の教訓)。"""
    for label in NODES:
        if label not in devs:
            print(f"[i] {label}: 未接続のため base 投入をスキップ")
            continue
        print(f"[i] {label}: base 設定を投入")
        conf(devs[label], BASE[label])


SUM_RX = re.compile(r"^(\d+\.\d+\.\d+\.\d+)\s+4\s+\d+.*\s(\S+)\s*$", re.M)


def up_neighbors(dev):
    """Established(最終列が数値=PfxRcd)な neighbor の集合。"""
    out = sh(dev, "show ip bgp summary")
    return {m.group(1) for m in SUM_RX.finditer(out) if m.group(2).isdigit()}


def n_paths(dev, pfx=PFX):
    m = re.search(r"Paths: \((\d+) available", sh(dev, f"show ip bgp {pfx}"))
    return int(m.group(1)) if m else 0


def rt01_shut(devs, targets, on):
    """RT01 側で neighbor shutdown を出し入れする。targets=ノード名リスト。"""
    lines = ["router bgp 65100"]
    for t in targets:
        lines.append(("" if on else "no ") + f"neighbor {E[t]} shutdown")
    lines.append("exit")
    conf(devs["RT01"], lines)


def only_neighbors(devs, keep, log=None, npaths=None):
    """RT01 の BGP 隣接を keep だけ残して他を shutdown し、収束を待つ。

    ★セッション確立だけでは経路が出揃わない(初回 b1 で実測: PfxRcd=0 のまま
    表を採ってしまった)。経路数(detail の `Paths: (N available`)まで待つ。
    """
    others = [n for n in E if n not in keep]
    rt01_shut(devs, others, True)
    rt01_shut(devs, keep, False)
    want = {E[k] for k in keep}
    dt = wait(lambda: up_neighbors(devs["RT01"]) == want,
              timeout=240, label=f"only {keep}")
    n = len(keep) if npaths is None else npaths
    dt2 = wait(lambda: n_paths(devs["RT01"]) == n, timeout=120,
               label=f"{n} paths")
    print(f"    [i] neighbors={sorted(keep)} 収束 {dt:.0f}s / 経路 {n} 本 {dt2:.0f}s")
    if log is not None:
        log.append(f"- 隣接を {sorted(keep)} に限定(収束 {dt:.0f}s・経路{n}本)")
    time.sleep(5)


def best_from(dev, pfx=PFX):
    """detail から best 経路の from(ピアIP)を返す。

    ★失敗録③(README): `", best" in line` だけだと `Paths: (5 available,
    best #4...)` の見出しに先に一致して常に None を返す。Origin 行に限定し、
    nh 行の `(metric N)`/`(inaccessible)` も許容する(probe2 と同じ修正)。
    """
    out = sh(dev, f"show ip bgp {pfx}")
    frm = None
    for line in out.splitlines():
        m = re.search(r"^\s+\S+(?: \(\S+ ?\d*\))? from (\S+) \(", line)
        if m:
            frm = m.group(1)
        if "Origin" in line and ", best" in line:
            return frm, out
    return None, out


def soft_out(dev, nbr_ip):
    sh(dev, f"clear ip bgp {nbr_ip} soft out")


# ---------------- 各チェック ----------------
def b1_baseline(devs, log):
    """B1/B2: 全5経路の表と detail の byte 書式を取る。"""
    log.append("\n## B1/B2: 基線(5経路)の表・detail 書式")
    rt = devs["RT01"]
    block(log, "RT01 show ip bgp", sh(rt, "show ip bgp"))
    block(log, f"RT01 show ip bgp {PFX}", sh(rt, f"show ip bgp {PFX}"))
    block(log, "RT01 show ip bgp summary", sh(rt, "show ip bgp summary"))
    # bestpath 理由の専用 show があるかも確認(無ければ % 応答が残る)
    block(log, f"RT01 show ip bgp {PFX} bestpath(有無の確認)",
          sh(rt, f"show ip bgp {PFX} bestpath"))


def b3_weight(devs, log):
    """B3: weight 最大が全段に先行。表の Weight 列表示も取る。"""
    log.append("\n## B3: neighbor weight 40000(RT03 向け)が最優先")
    rt = devs["RT01"]
    conf(rt, ["router bgp 65100", "address-family ipv4",
              f"neighbor {E['RT03']} weight 40000",
              "exit-address-family", "exit"])
    sh(rt, f"clear ip bgp {E['RT03']} soft in")
    wait(lambda: best_from(rt)[0] == E["RT03"], timeout=60, label="weight best")
    frm, out = best_from(rt)
    log.append(f"- best from = `{frm}` (期待= {E['RT03']})")
    block(log, "RT01 show ip bgp (Weight 40000 行あり)", sh(rt, "show ip bgp"))
    block(log, f"RT01 show ip bgp {PFX}", out)
    conf(rt, ["router bgp 65100", "address-family ipv4",
              f"no neighbor {E['RT03']} weight 40000",
              "exit-address-family", "exit"])
    sh(rt, f"clear ip bgp {E['RT03']} soft in")
    time.sleep(3)


def b4_lp(devs, log):
    """B4: LP 200 は AS-PATH 長より強い(+iBGP ピアへの伝播も見る)。"""
    log.append("\n## B4: LOCAL_PREF 200 > AS-PATH 長(+iBGP 伝播)")
    rt = devs["RT01"]
    # RT04 は prepend で最長にしておく(それでも LP で勝つことを見る)
    conf(devs["RT04"], [
        "route-map RM-PREPEND-OUT permit 10",
        "set as-path prepend 65300 65300", "exit",
        "router bgp 65300", "address-family ipv4",
        "neighbor 10.0.14.1 route-map RM-PREPEND-OUT out",
        "exit-address-family", "exit"])
    soft_out(devs["RT04"], "10.0.14.1")
    conf(rt, ["route-map RM-LP-IN permit 10", "set local-preference 200", "exit",
              "router bgp 65100", "address-family ipv4",
              f"neighbor {E['RT04']} route-map RM-LP-IN in",
              "exit-address-family", "exit"])
    sh(rt, f"clear ip bgp {E['RT04']} soft in")
    wait(lambda: best_from(rt)[0] == E["RT04"], timeout=60, label="lp best")
    frm, out = best_from(rt)
    log.append(f"- best from = `{frm}` (期待= {E['RT04']}・path 最長なのに LP で勝つ)")
    block(log, "RT01 show ip bgp (LocPrf 200 行あり)", sh(rt, "show ip bgp"))
    block(log, f"RT01 show ip bgp {PFX}", out)
    # iBGP ピア(RT05)から見える LP(RT01 が広告した best の LocPrf=200 のはず)
    if "RT05" in devs:
        block(log, f"RT05 show ip bgp {PFX} (RT01 経由の LP 伝播)",
              sh(devs["RT05"], f"show ip bgp {PFX}"))
    conf(rt, ["router bgp 65100", "address-family ipv4",
              f"no neighbor {E['RT04']} route-map RM-LP-IN in",
              "exit-address-family", "exit", "no route-map RM-LP-IN"])
    conf(devs["RT04"], ["router bgp 65300", "address-family ipv4",
                        "no neighbor 10.0.14.1 route-map RM-PREPEND-OUT out",
                        "exit-address-family", "exit",
                        "no route-map RM-PREPEND-OUT"])
    soft_out(devs["RT04"], "10.0.14.1")
    sh(rt, f"clear ip bgp {E['RT04']} soft in")
    time.sleep(3)


def b5_local(devs, log):
    """B5: 自機起源の行(weight 32768・Next Hop 0.0.0.0)の表示。"""
    log.append("\n## B5: 自機起源 = weight 32768 行の表示")
    rt = devs["RT01"]
    conf(rt, ["ip route 203.0.113.0 255.255.255.0 Null0",
              "router bgp 65100", "address-family ipv4",
              "network 203.0.113.0 mask 255.255.255.0",
              "exit-address-family", "exit"])
    wait(lambda: "203.0.113.0" in sh(rt, "show ip bgp | include 203.0.113"),
         timeout=30, label="local net")
    block(log, "RT01 show ip bgp (203.0.113.0/24 = 自機起源)", sh(rt, "show ip bgp"))
    block(log, "RT01 show ip bgp 203.0.113.0", sh(rt, "show ip bgp 203.0.113.0"))
    conf(rt, ["router bgp 65100", "address-family ipv4",
              "no network 203.0.113.0 mask 255.255.255.0",
              "exit-address-family", "exit",
              "no ip route 203.0.113.0 255.255.255.0 Null0"])
    time.sleep(2)


def b16_lp_ebgp(devs, log):
    """B16: eBGP ピアへ set local-preference out した時の実挙動。"""
    log.append("\n## B16: LP を eBGP ピア向け out に set(送られるか?)")
    rt = devs["RT01"]
    errs = conf(devs["RT02"], [
        "route-map RM-LP-OUT permit 10", "set local-preference 300", "exit",
        "router bgp 65200", "address-family ipv4",
        "neighbor 10.0.12.1 route-map RM-LP-OUT out",
        "exit-address-family", "exit"], log)
    soft_out(devs["RT02"], "10.0.12.1")
    time.sleep(10)
    _, out = best_from(rt)
    block(log, f"RT01 show ip bgp {PFX} (RT02 経路の localpref 表示に注目)", out)
    log.append("- ↑ RT02(10.0.12.2) からの経路の localpref が 100(既定)のままなら"
               "「eBGP には送られない」が確定")
    conf(devs["RT02"], ["router bgp 65200", "address-family ipv4",
                        "no neighbor 10.0.12.1 route-map RM-LP-OUT out",
                        "exit-address-family", "exit", "no route-map RM-LP-OUT"])
    soft_out(devs["RT02"], "10.0.12.1")
    time.sleep(3)


def b7_origin(devs, log):
    """B7: origin i vs ? (AS長同一・RT02/RT03 の 2経路だけにして単離)。"""
    log.append("\n## B7: origin IGP vs incomplete の決着")
    rt = devs["RT01"]
    only_neighbors(devs, ["RT02", "RT03"], log)
    # RT03 を redistribute static 起源(origin ?)へ切替
    conf(devs["RT03"], [
        "ip route 198.51.100.0 255.255.255.0 Null0",
        "router bgp 65200", "address-family ipv4",
        "no network 198.51.100.0 mask 255.255.255.0",
        "redistribute static",
        "exit-address-family", "exit"])
    soft_out(devs["RT03"], "10.0.13.1")
    wait(lambda: "?" in sh(rt, f"show ip bgp {PFX}"), timeout=60,
         label="origin ? 反映")
    frm, out = best_from(rt)
    log.append(f"- best from = `{frm}` (期待= {E['RT02']}・origin i が ? に勝つ)")
    block(log, f"RT01 show ip bgp {PFX} (i vs ?)", out)
    block(log, "RT01 show ip bgp (Path 列の i/? 表示)", sh(rt, "show ip bgp"))
    # 復旧
    conf(devs["RT03"], [
        "router bgp 65200", "address-family ipv4",
        "no redistribute static",
        "network 198.51.100.0 mask 255.255.255.0",
        "exit-address-family", "exit",
        "no ip route 198.51.100.0 255.255.255.0 Null0"])
    soft_out(devs["RT03"], "10.0.13.1")
    time.sleep(3)


def b8_med(devs, log):
    """B8: MED 同一隣接AS(65200×2)で比較され小さい方が勝つ。"""
    log.append("\n## B8: MED(同一隣接AS)= 小さい方が勝つ・入替で反転")
    rt = devs["RT01"]
    only_neighbors(devs, ["RT02", "RT03"], log)
    for nd, med in (("RT02", 50), ("RT03", 200)):
        conf(devs[nd], [
            "route-map RM-MED-OUT permit 10", f"set metric {med}", "exit",
            "router bgp 65200", "address-family ipv4",
            f"neighbor {'10.0.12.1' if nd == 'RT02' else '10.0.13.1'} "
            "route-map RM-MED-OUT out",
            "exit-address-family", "exit"])
    soft_out(devs["RT02"], "10.0.12.1")
    soft_out(devs["RT03"], "10.0.13.1")
    wait(lambda: best_from(rt)[0] == E["RT02"], timeout=60, label="med50 best")
    frm, out = best_from(rt)
    log.append(f"- MED 50(RT02) vs 200(RT03): best from = `{frm}` (期待= {E['RT02']})")
    block(log, "RT01 show ip bgp (Metric 列 50/200)", sh(rt, "show ip bgp"))
    block(log, f"RT01 show ip bgp {PFX}", out)
    # 入替(RT02 を 300 へ)→ 反転するはず
    conf(devs["RT02"], ["route-map RM-MED-OUT permit 10", "set metric 300", "exit"])
    soft_out(devs["RT02"], "10.0.12.1")
    dt = wait(lambda: best_from(rt)[0] == E["RT03"], timeout=90, label="med flip")
    log.append(f"- RT02 の MED を 300 へ → best が RT03 に反転(所要 {dt:.0f}s)")
    block(log, f"RT01 show ip bgp {PFX} (反転後)", best_from(rt)[1])


def b10_med_missing(devs, log):
    """B10: MED 欠落=0 扱い / missing-as-worst で反転。b8 の直後に呼ぶ。"""
    log.append("\n## B10: MED 欠落の既定値(=0)と missing-as-worst")
    rt = devs["RT01"]
    # RT02 の MED を外す(欠落)。RT03 は 200 のまま
    conf(devs["RT02"], ["router bgp 65200", "address-family ipv4",
                        "no neighbor 10.0.12.1 route-map RM-MED-OUT out",
                        "exit-address-family", "exit", "no route-map RM-MED-OUT"])
    soft_out(devs["RT02"], "10.0.12.1")
    wait(lambda: best_from(rt)[0] == E["RT02"], timeout=90, label="missing=0")
    frm, out = best_from(rt)
    log.append(f"- MED 欠落(RT02) vs 200(RT03): best from = `{frm}` "
               f"(期待= {E['RT02']}・欠落は 0 扱い)")
    block(log, "RT01 show ip bgp (RT02 行の Metric 列が空欄か 0 か)",
          sh(rt, "show ip bgp"))
    block(log, f"RT01 show ip bgp {PFX} (欠落側 detail の metric 表示)", out)
    # missing-as-worst → RT03(200) が勝つはず
    conf(rt, ["router bgp 65100", "bgp bestpath med missing-as-worst", "exit"])
    dt = wait(lambda: best_from(rt)[0] == E["RT03"], timeout=90,
              label="missing-as-worst")
    log.append(f"- `bgp bestpath med missing-as-worst` 投入 → best が RT03 へ"
               f"(clear 無しで反転するか: 所要 {dt:.0f}s)")
    block(log, f"RT01 show ip bgp {PFX} (worst 扱い後)", best_from(rt)[1])
    conf(rt, ["router bgp 65100", "no bgp bestpath med missing-as-worst", "exit"])
    # RT03 の MED も外して素へ
    conf(devs["RT03"], ["router bgp 65200", "address-family ipv4",
                        "no neighbor 10.0.13.1 route-map RM-MED-OUT out",
                        "exit-address-family", "exit", "no route-map RM-MED-OUT"])
    soft_out(devs["RT03"], "10.0.13.1")
    time.sleep(5)


def b13_oldest_rid(devs, log):
    """B13: 全段タイ→oldest 勝ち(flapで入替)→compare-routerid で RID 決着。"""
    log.append("\n## B13: oldest 勝ち → bgp bestpath compare-routerid")
    rt = devs["RT01"]
    only_neighbors(devs, ["RT02", "RT03"], log)
    frm0, out0 = best_from(rt)
    log.append(f"- 素の 2経路(全属性タイ)の best from = `{frm0}`")
    block(log, f"RT01 show ip bgp {PFX} (タイ状態)", out0)
    # best 側を flap → もう一方が oldest になり best が入れ替わって固定するはず
    flap = "RT02" if frm0 == E["RT02"] else "RT03"
    other = "RT03" if flap == "RT02" else "RT02"
    rt01_shut(devs, [flap], True)
    wait(lambda: best_from(rt)[0] == E[other], timeout=60, label="flap down")
    rt01_shut(devs, [flap], False)
    wait(lambda: E[flap] in up_neighbors(rt), timeout=120, label="flap up")
    wait(lambda: n_paths(rt) == 2, timeout=90, label="flap 2 paths")
    time.sleep(10)
    frm1, out1 = best_from(rt)
    log.append(f"- {flap} を flap → 再確立後の best from = `{frm1}` "
               f"(期待= `{E[other]}` のまま = oldest 勝ちの実証)")
    block(log, f"RT01 show ip bgp {PFX} (flap 後)", out1)
    # compare-routerid → RID 最小(RT02=2.2.2.2)で決定化
    conf(rt, ["router bgp 65100", "bgp bestpath compare-routerid", "exit"])
    dt = wait(lambda: best_from(rt)[0] == E["RT02"], timeout=90,
              label="compare-routerid")
    frm2, out2 = best_from(rt)
    log.append(f"- `bgp bestpath compare-routerid` 投入 → best from = `{frm2}` "
               f"(期待= {E['RT02']}=RID 2.2.2.2 < 3.3.3.3。clear 無し所要 {dt:.0f}s)")
    block(log, f"RT01 show ip bgp {PFX} (compare-routerid 後)", out2)
    conf(rt, ["router bgp 65100", "no bgp bestpath compare-routerid", "exit"])


def b11_ebgp(devs, log):
    """B11: eBGP > iBGP(AS長・origin を揃えて単離)。"""
    log.append("\n## B11: eBGP > iBGP")
    rt = devs["RT01"]
    only_neighbors(devs, ["RT04", "RT05"], log)
    # RT04(eBGP, 65300) vs RT05(iBGP, 65200 学習・nh-self)。AS長1で同一・origin i
    wait(lambda: best_from(rt)[0] is not None, timeout=60, label="paths")
    frm, out = best_from(rt)
    log.append(f"- best from = `{frm}` (期待= {E['RT04']}・eBGP が iBGP に勝つ)")
    block(log, "RT01 show ip bgp (iBGP 行の i マーカーと LocPrf 100)",
          sh(rt, "show ip bgp"))
    block(log, f"RT01 show ip bgp {PFX}", out)
    # 裏取り: eBGP 側を落とすと iBGP が best になる
    rt01_shut(devs, ["RT04"], True)
    wait(lambda: best_from(rt)[0] == E["RT05"], timeout=60, label="iBGP fallback")
    block(log, f"RT01 show ip bgp {PFX} (eBGP 断後= iBGP best)", best_from(rt)[1])
    rt01_shut(devs, ["RT04"], False)


def b12_igp(devs, log):
    """B12: iBGP 2経路は next-hop への IGP metric で決着。コスト入替で反転。"""
    log.append("\n## B12: IGP metric to next-hop(detail の `(metric N)`)")
    rt = devs["RT01"]
    only_neighbors(devs, ["RT05", "RT06"], log)
    wait(lambda: best_from(rt)[0] == E["RT05"], timeout=90, label="igp base")
    frm, out = best_from(rt)
    log.append(f"- cost 10(→RT05) vs 100(→RT06): best from = `{frm}` "
               f"(期待= {E['RT05']})")
    block(log, f"RT01 show ip bgp {PFX} (`(metric N)` 表示)", out)
    # コスト入替 → RT06 へ反転するはず。反応時間も測る(scanner/NHT)
    t0 = time.time()
    conf(rt, ["interface Ethernet0/3", "ip ospf cost 100", "exit",
              "interface Ethernet1/0", "ip ospf cost 10", "exit"])
    dt = wait(lambda: best_from(rt)[0] == E["RT06"], timeout=180, every=5,
              label="igp flip")
    log.append(f"- コスト入替 → best が RT06 へ反転(所要 {dt:.0f}s・"
               f"clear 無し=NHT/scanner の反応時間)")
    block(log, f"RT01 show ip bgp {PFX} (反転後)", best_from(rt)[1])
    conf(rt, ["interface Ethernet0/3", "ip ospf cost 10", "exit",
              "interface Ethernet1/0", "ip ospf cost 100", "exit"])
    time.sleep(5)


def b15_inaccessible(devs, log):
    """B15: next-hop-self 欠落 → inaccessible の実表示。"""
    log.append("\n## B15: next-hop 解決不能(inaccessible)の実表示")
    rt = devs["RT01"]
    only_neighbors(devs, ["RT04", "RT05"], log)
    conf(devs["RT05"], ["router bgp 65100", "address-family ipv4",
                        "no neighbor 1.1.1.1 next-hop-self",
                        "exit-address-family", "exit"])
    sh(devs["RT05"], "clear ip bgp 1.1.1.1 soft out")
    wait(lambda: "inaccessible" in sh(rt, f"show ip bgp {PFX}"),
         timeout=90, label="inaccessible")
    block(log, "RT01 show ip bgp (無効経路の行マーカー)", sh(rt, "show ip bgp"))
    block(log, f"RT01 show ip bgp {PFX} (inaccessible 表示)",
          sh(rt, f"show ip bgp {PFX}"))
    log.append("- ↑ 属性がどれだけ良くても候補から外れることの実表示")
    conf(devs["RT05"], ["router bgp 65100", "address-family ipv4",
                        "neighbor 1.1.1.1 next-hop-self",
                        "exit-address-family", "exit"])
    sh(devs["RT05"], "clear ip bgp 1.1.1.1 soft out")
    time.sleep(3)


def restore_all(devs, log):
    """基線へ戻す(全隣接 no shutdown)。"""
    rt01_shut(devs, list(E), False)
    dt = wait(lambda: up_neighbors(devs["RT01"]) == set(E.values()),
              timeout=240, label="restore")
    log.append(f"\n## 復元: 全隣接 no shutdown(収束 {dt:.0f}s)")
    block(log, "RT01 show ip bgp (最終基線)", sh(devs["RT01"], "show ip bgp"))


CHECKS = [("b1", b1_baseline), ("b3", b3_weight), ("b4", b4_lp),
          ("b5", b5_local), ("b16", b16_lp_ebgp),
          ("b7", b7_origin), ("b8", b8_med), ("b10", b10_med_missing),
          ("b13", b13_oldest_rid), ("b11", b11_ebgp), ("b12", b12_igp),
          ("b15", b15_inaccessible), ("restore", restore_all)]


def main():
    want = [a.lower() for a in sys.argv[1:]]
    todo = [(n, f) for n, f in CHECKS if not want or n in want]
    client = ClientLibrary(CML[0], CML[1], CML[2], ssl_verify=False)
    lab = ensure_lab(client)
    devs = connect_all(lab, required=tuple(NODES))
    push_base(devs)
    # 基線: 5隣接 Established+経路が出るまで待つ
    dt = wait(lambda: up_neighbors(devs["RT01"]) == set(E.values()),
              timeout=300, label="baseline established")
    dt2 = wait(lambda: n_paths(devs["RT01"]) >= 5, timeout=180,
               label="baseline 5 paths")
    print(f"[i] 基線確立 {dt:.0f}s / 5経路 {dt2:.0f}s")
    time.sleep(10)
    log = [f"\n---\n# probe 実行 {time.strftime('%Y-%m-%d %H:%M')} "
           f"(checks={[n for n, _ in todo]})"]
    for name, fn in todo:
        print(f"[i] ==== {name} ====")
        try:
            fn(devs, log)
        except Exception as e:
            print(f"    [!] {name}: {type(e).__name__}: {e}")
            log.append(f"\n## {name}: ★実行エラー {type(e).__name__}: {e}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write("\n".join(log) + "\n")
    print(f"[i] 結果を {OUT} に追記した")


if __name__ == "__main__":
    main()
