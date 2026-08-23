#!/usr/bin/env python3
"""BL-136(b): bgpdbg 変種追加の debug 実出力採取(既存 BL-085 PoC の続編)。

_POC-BGPDBG2(IOL 2台: RT01 --10.0.12.0/30-- RT02・Lo0=1.1.1.1/2.2.2.2・
相互 Lo へ static)をコンソール直駆動で回し、追加変種候補の指紋を byte で採る。

  b1 password_mismatch : iBGP Lo ピア(両側 update-source 健全)で MD5 鍵不一致
                         → %TCP-6-BADAUTH の出方・summary の状態
  b2 remote_as_wrong   : eBGP(65001-65002)で片側の remote-as が 65003
                         → OPEN 交換後 NOTIFICATION 2/2 (Bad AS) の出方
  b3 nbr_shutdown      : iBGP 健全構成に片側 `neighbor x shutdown` 残骸
                         → Idle (Admin) と Cease 通知の出方

各チェックで `debug ip bgp` + `show ip bgp summary` + logging バッファを採取。
結果は results-probe2.md へ追記。使い方: probe2.py [b1 b2 b3]
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

OUT = Path(__file__).resolve().parent / "results-probe2.md"
CML = ("https://10.1.10.10", "SUZUKI", "suzugross")
LAB_TITLE = "_POC-BGPDBG2"
NODES = ["RT01", "RT02"]
LINKS = [("RT01", 0, "RT02", 0)]
POS = {"RT01": (-200, 0), "RT02": (200, 0)}

BASE = {
    "RT01": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.12.1 255.255.255.252",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 1.1.1.1 255.255.255.255", "exit",
        "ip route 2.2.2.2 255.255.255.255 10.0.12.2",
        "logging buffered 200000", "no logging console",
    ],
    "RT02": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.12.2 255.255.255.252",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 2.2.2.2 255.255.255.255", "exit",
        "ip route 1.1.1.1 255.255.255.255 10.0.12.1",
        "logging buffered 200000", "no logging console",
    ],
}


def _ifname(slot):
    return f"Ethernet{slot // 4}/{slot % 4}"


def _iface(lab, label, slot):
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
        if not (ia.connected or ib.connected):
            lab.create_link(ia, ib)
    if lab.state() != "STARTED":
        print("[i] lab start...")
        lab.start(wait=True)
    return lab


def connect_all(lab):
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
                print(f"    {label}: attempt {attempt} ({type(e).__name__})")
                try:
                    dev.disconnect()
                except Exception:
                    pass
                time.sleep(8)
        else:
            raise RuntimeError(f"{label}: console 接続不能")
    return devs


def conf(dev, lines):
    out = dev.configure(lines, error_pattern=[], timeout=120)
    text = out if isinstance(out, str) else "\n".join(
        v for v in out.values() if isinstance(v, str))
    for ln in text.splitlines():
        if ln.strip().startswith("%"):
            print(f"    ! {ln.strip()}")
    return text


def sh(dev, cmd):
    return dev.execute(cmd, timeout=120)


def block(log, title, text):
    log.append(f"\n{title}:\n```\n{text.strip()}\n```")


def reset_bgp(devs):
    for r in NODES:
        conf(devs[r], ["no router bgp 65001", "no router bgp 65002"])
    time.sleep(3)


def arm_debug(devs):
    for r in NODES:
        d = devs[r]
        # ★clear logging は [confirm] プロンプトでコンソールがずれる(初回実測)。
        #   バッファサイズの付け直しはプロンプト無しでバッファが空になるので代用。
        conf(d, ["logging buffered 4096", "logging buffered 200000"])
        d.execute("debug ip bgp")


def harvest(devs, log, label, wait_s=40):
    time.sleep(wait_s)
    for r in NODES:
        d = devs[r]
        d.execute("undebug all")
        summ = sh(d, "show ip bgp summary")
        block(log, f"{label}: {r} `show ip bgp summary`", summ)
        raw = sh(d, "show logging | include BGP|TCP|NOTIF")
        block(log, f"{label}: {r} logging(debug 抜粋)", raw[-4500:])


def b1(devs, log):
    """iBGP Lo ピア(update-source 両側健全)で MD5 password 不一致。"""
    reset_bgp(devs)
    conf(devs["RT01"], ["router bgp 65001",
                        "neighbor 2.2.2.2 remote-as 65001",
                        "neighbor 2.2.2.2 update-source Loopback0",
                        "neighbor 2.2.2.2 password S3CRET-A", "exit"])
    conf(devs["RT02"], ["router bgp 65001",
                        "neighbor 1.1.1.1 remote-as 65001",
                        "neighbor 1.1.1.1 update-source Loopback0",
                        "neighbor 1.1.1.1 password S3CRET-B", "exit"])
    arm_debug(devs)
    harvest(devs, log, "b1 password_mismatch")
    # 片側だけ password(もう片側は無し)も採る=不一致と指紋が違うか
    conf(devs["RT02"], ["router bgp 65001",
                        "no neighbor 1.1.1.1 password", "exit"])
    arm_debug(devs)
    harvest(devs, log, "b1b password_oneside", wait_s=30)


def b2(devs, log):
    """eBGP で remote-as 誤り(OPEN 後 NOTIFICATION 2/2 Bad AS)。"""
    reset_bgp(devs)
    conf(devs["RT01"], ["router bgp 65001",
                        "neighbor 10.0.12.2 remote-as 65003", "exit"])   # 誤り
    conf(devs["RT02"], ["router bgp 65002",
                        "neighbor 10.0.12.1 remote-as 65001", "exit"])
    arm_debug(devs)
    harvest(devs, log, "b2 remote_as_wrong", wait_s=45)


def b3(devs, log):
    """iBGP 健全構成に片側 neighbor shutdown 残骸。"""
    reset_bgp(devs)
    conf(devs["RT01"], ["router bgp 65001",
                        "neighbor 2.2.2.2 remote-as 65001",
                        "neighbor 2.2.2.2 update-source Loopback0",
                        "neighbor 2.2.2.2 shutdown", "exit"])            # 残骸
    conf(devs["RT02"], ["router bgp 65001",
                        "neighbor 1.1.1.1 remote-as 65001",
                        "neighbor 1.1.1.1 update-source Loopback0", "exit"])
    arm_debug(devs)
    harvest(devs, log, "b3 nbr_shutdown", wait_s=35)


CHECKS = {"b1": b1, "b2": b2, "b3": b3}


def main():
    names = [a for a in sys.argv[1:] if a in CHECKS] or list(CHECKS)
    client = ClientLibrary(CML[0], CML[1], CML[2], ssl_verify=False)
    lab = ensure_lab(client)
    devs = connect_all(lab)
    for label in NODES:
        conf(devs[label], BASE[label])
    stamp = time.strftime("%Y-%m-%d %H:%M")
    results = [f"\n\n# probe2 run {stamp} ({' '.join(names)})"]
    for name in names:
        print(f"[i] ==== {name} ====")
        log = [f"\n## {name}"]
        try:
            CHECKS[name](devs, log)
        except Exception as e:
            log.append(f"- ★探針が例外で中断: {type(e).__name__}: {e}")
            print(f"    [!] {name}: {type(e).__name__}: {e}")
        results += log
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write("\n".join(results) + "\n")
    print(f"[i] 結果を {OUT} へ追記した")


if __name__ == "__main__":
    main()
