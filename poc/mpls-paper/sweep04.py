#!/usr/bin/env python3
"""BL-169 PoC M10/M11(PE-CE eBGP: as-override / allowas-in の指紋)。ENARSI-MPLS-L3VPN-04 を provision して走らせる。

04 の初期状態= 01 完成形コア＋CE は eBGP 設定済(CUST_A: RT04=AS65101/RT05=AS65102、CUST_B: RT06/RT07=AS65200)。
PE 側の neighbor は未構成なので、ここで投入する(route-map は本 PoC の主題外なので付けない)。
"""
import json
import os
import time

import paramiko

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
NODES = json.load(open(os.path.join(REPO, "topologies/_state/mgmt_leases.json")))["leases"]["ENARSI-MPLS-L3VPN-04"]["nodes"]
OUT = os.path.join(HERE, "results-raw-04.md")
LOG = []


def block(title, node, cmd, out):
    LOG.append(f"\n### {title} — {node}# {cmd}\n\n```\n{out.rstrip()}\n```\n")
    print(f"  [{node}] {cmd} ({len(out)} bytes)", flush=True)


class Dev:
    def __init__(self, name):
        self.name = name
        self.c = paramiko.SSHClient()
        self.c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.c.connect(NODES[name], username="SUZUKI", password="CCNP", look_for_keys=False, allow_agent=False, timeout=20)
        self.sh = self.c.invoke_shell()
        time.sleep(1)
        self.sh.send("terminal length 0\nterminal width 200\n")
        time.sleep(1)
        self.drain()

    def drain(self):
        buf = b""
        while self.sh.recv_ready():
            buf += self.sh.recv(65535)
            time.sleep(0.2)
        return buf.decode(errors="replace")

    def show(self, cmd, wait=2.5, title=None):
        self.sh.send(cmd + "\n")
        time.sleep(wait)
        out = self.drain()
        lines = out.splitlines()
        body = "\n".join(lines[1:-1]) if len(lines) > 2 else out
        if title:
            block(title, self.name, cmd, body)
        return body

    def conf(self, lines, title=None, wait=1.0):
        self.sh.send("configure terminal\n")
        time.sleep(0.8)
        for ln in lines:
            self.sh.send(ln + "\n")
            time.sleep(wait)
        self.sh.send("end\n")
        time.sleep(1.5)
        out = self.drain()
        if title:
            block(title, self.name, "conf t: " + " / ".join(lines), out)
        return out

    def close(self):
        self.c.close()


def main():
    LOG.append("# BL-169 PoC 生ログ(ENARSI-MPLS-L3VPN-04・PE-CE eBGP・" + time.strftime("%Y-%m-%d %H:%M") + ")\n")
    pe1, pe2 = Dev("RT01"), Dev("RT03")
    a1, b1, b2 = Dev("RT04"), Dev("RT06"), Dev("RT07")
    LOG.append("\n## 0. 基線(PE 側 eBGP ネイバーを as-override 無しで投入)\n")
    pe1.conf(["router bgp 65000", "address-family ipv4 vrf CUST_A", "neighbor 192.168.1.1 remote-as 65101", "neighbor 192.168.1.1 activate", "exit-address-family",
              "address-family ipv4 vrf CUST_B", "neighbor 192.168.11.1 remote-as 65200", "neighbor 192.168.11.1 activate", "exit-address-family", "exit"], title="基線投入")
    pe2.conf(["router bgp 65000", "address-family ipv4 vrf CUST_A", "neighbor 192.168.2.1 remote-as 65102", "neighbor 192.168.2.1 activate", "exit-address-family",
              "address-family ipv4 vrf CUST_B", "neighbor 192.168.12.1 remote-as 65200", "neighbor 192.168.12.1 activate", "exit-address-family", "exit"], title="基線投入")
    time.sleep(75)
    LOG.append("\n## M10a as-override 無し: CUST_A(サイト毎 AS)は届き、CUST_B(同一 AS)は CE が捨てる\n")
    pe1.show("show bgp vpnv4 unicast all summary", title="M10a")
    pe1.show("show bgp vpnv4 unicast vrf CUST_B", title="M10a")
    pe1.show("show bgp vpnv4 unicast vrf CUST_B neighbors 192.168.11.1 advertised-routes", title="M10a")
    a1.show("show ip bgp", title="M10a (CUST_A CE)")
    a1.show("show ip bgp 172.16.2.0", title="M10a (CUST_A CE)")
    b1.show("show ip bgp", title="M10a (CUST_B CE)")
    b1.show("show ip bgp summary", title="M10a (CUST_B CE)")
    b1.show("show ip route bgp", title="M10a (CUST_B CE)")
    # DENIED 指紋: CE でデバッグを有効にし、PE から soft out で再広告させる
    b1.show("terminal monitor", wait=1)
    b1.show("debug ip bgp updates in", wait=1, title="M10a debug on")
    pe1.show("clear bgp vpnv4 unicast vrf CUST_B 192.168.11.1 soft out", wait=6, title="M10a 再広告")
    time.sleep(4)
    out = b1.drain()
    block("M10a DENIED 指紋(debug ip bgp updates in)", "RT06", "(debug 出力)", out)
    b1.show("undebug all", wait=1)
    b1.show("terminal no monitor", wait=1)
    LOG.append("\n## M10b as-override を PE に投入\n")
    pe1.conf(["router bgp 65000", "address-family ipv4 vrf CUST_B", "neighbor 192.168.11.1 as-override", "exit-address-family", "exit"], title="M10b 投入")
    pe2.conf(["router bgp 65000", "address-family ipv4 vrf CUST_B", "neighbor 192.168.12.1 as-override", "exit-address-family", "exit"], title="M10b 投入")
    time.sleep(40)
    b1.show("show ip bgp", title="M10b (CUST_B CE)")
    b1.show("show ip bgp 172.16.2.0", title="M10b (CUST_B CE)")
    b1.show("show ip route bgp", title="M10b (CUST_B CE)")
    b1.show("ping 172.16.2.9 source 172.16.1.9 repeat 3", wait=8, title="M10b")
    pe1.show("show bgp vpnv4 unicast vrf CUST_B neighbors 192.168.11.1 advertised-routes", title="M10b")
    pe1.show("show running-config | section address-family ipv4 vrf CUST_B", title="M10b")
    LOG.append("\n## M11 as-override を外し、CE 側に allowas-in\n")
    pe1.conf(["router bgp 65000", "address-family ipv4 vrf CUST_B", "no neighbor 192.168.11.1 as-override", "exit-address-family", "exit"], title="M11 as-override 解除")
    pe2.conf(["router bgp 65000", "address-family ipv4 vrf CUST_B", "no neighbor 192.168.12.1 as-override", "exit-address-family", "exit"], title="M11 as-override 解除")
    time.sleep(40)
    b1.show("show ip bgp", title="M11 (解除後・CE)")
    b1.conf(["router bgp 65200", "address-family ipv4", "neighbor 192.168.11.2 allowas-in", "exit-address-family", "exit"], title="M11 allowas-in 投入(CE1)")
    b2.conf(["router bgp 65200", "address-family ipv4", "neighbor 192.168.12.2 allowas-in", "exit-address-family", "exit"], title="M11 allowas-in 投入(CE2)")
    time.sleep(40)
    b1.show("show ip bgp", title="M11 (allowas-in 後・CE)")
    b1.show("show ip bgp 172.16.2.0", title="M11 (allowas-in 後・CE)")
    b1.show("ping 172.16.2.9 source 172.16.1.9 repeat 3", wait=8, title="M11")
    b1.show("show running-config | section router bgp", title="M11")
    # 復旧
    b1.conf(["router bgp 65200", "address-family ipv4", "no neighbor 192.168.11.2 allowas-in", "exit-address-family", "exit"], title="M11 復旧(CE1)")
    b2.conf(["router bgp 65200", "address-family ipv4", "no neighbor 192.168.12.2 allowas-in", "exit-address-family", "exit"], title="M11 復旧(CE2)")
    for d in (pe1, pe2, a1, b1, b2):
        d.close()
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG))
    print("wrote", OUT)


if __name__ == "__main__":
    try:
        main()
    finally:
        if LOG and not os.path.exists(OUT):
            with open(OUT, "w", encoding="utf-8") as fh:
                fh.write("\n".join(LOG))
