#!/usr/bin/env python3
"""BL-169 紙面 MPLS ファミリの PoC(M1〜M9・M14): ENARSI-MPLS-L3VPN-02 を provision した上で走らせる。

- 基線 = 02 の解答(PE-CE OSPF＋相互再配送)を PE に投入して VPN を通す。
- 各実験は投入→待ち→採取→復旧。生ログは results-raw.md(節ごと)。
- 接続は SSH(paramiko・SUZUKI/CCNP)。IOL の mgmt は topologies/_state/mgmt_leases.json。
"""
import json
import os
import sys
import time

import paramiko

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LEASES = json.load(open(os.path.join(REPO, "topologies/_state/mgmt_leases.json")))
NODES = LEASES["leases"]["ENARSI-MPLS-L3VPN-02"]["nodes"]
OUT = os.path.join(HERE, "results-raw.md")
LOG = []


def block(title, node, cmd, out):
    LOG.append(f"\n### {title} — {node}# {cmd}\n\n```\n{out.rstrip()}\n```\n")
    print(f"  [{node}] {cmd} ({len(out)} bytes)", flush=True)


class Dev:
    def __init__(self, name):
        self.name = name
        self.c = paramiko.SSHClient()
        self.c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.c.connect(NODES[name], username="SUZUKI", password="CCNP",
                       look_for_keys=False, allow_agent=False, timeout=20)
        self.sh = self.c.invoke_shell()
        time.sleep(1)
        self.sh.send("terminal length 0\nterminal width 200\n")
        time.sleep(1)
        self._drain()

    def _drain(self):
        buf = b""
        while self.sh.recv_ready():
            buf += self.sh.recv(65535)
            time.sleep(0.2)
        return buf.decode(errors="replace")

    def show(self, cmd, wait=2.5, title=None):
        self.sh.send(cmd + "\n")
        time.sleep(wait)
        out = self._drain()
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
        out = self._drain()
        if title:
            block(title, self.name, "conf t: " + " / ".join(lines), out)
        return out

    def close(self):
        self.c.close()


def main():
    t0 = time.time()
    LOG.append("# BL-169 PoC 生ログ(ENARSI-MPLS-L3VPN-02・IOL・" + time.strftime("%Y-%m-%d %H:%M") + ")\n")
    pe1, p, pe2 = Dev("RT01"), Dev("RT02"), Dev("RT03")
    ce1 = Dev("RT04")

    # ---- 基線: 02 の解答(PE-CE OSPF＋相互再配送) ----
    LOG.append("\n## 0. 基線(02 解答の投入)\n")
    for pe, nets in ((pe1, ("192.168.1.0", "192.168.11.0")), (pe2, ("192.168.2.0", "192.168.12.0"))):
        pe.conf(["router ospf 10 vrf CUST_A", f"network {nets[0]} 0.0.0.3 area 0", "redistribute bgp 65000 subnets", "exit",
                 "router ospf 20 vrf CUST_B", f"network {nets[1]} 0.0.0.3 area 0", "redistribute bgp 65000 subnets", "exit",
                 "router bgp 65000", "address-family ipv4 vrf CUST_A", "redistribute ospf 10", "redistribute connected", "exit-address-family",
                 "address-family ipv4 vrf CUST_B", "redistribute ospf 20", "redistribute connected", "exit-address-family", "exit"],
                title="基線投入")
    time.sleep(90)
    pe1.show("show ip route vrf CUST_A", title="基線確認")
    ce1.show("ping 172.16.2.1 source 172.16.1.1 repeat 5", wait=8, title="基線確認(CE1→CE2)")

    # ---- M1〜M3, M6: 読解用の表示(byte 写し) ----
    LOG.append("\n## M1 LFIB / M2 LDP / M3 traceroute / M6 VPNv4・VRF 表\n")
    for dev in (pe1, p, pe2):
        dev.show("show mpls forwarding-table", title="M1")
    pe1.show("show mpls ldp bindings", title="M2")
    pe1.show("show mpls ldp neighbor", title="M2")
    pe1.show("show mpls ldp discovery", title="M2")
    pe1.show("show mpls ldp discovery detail", title="M2")
    pe1.show("show mpls interfaces", title="M2")
    p.show("show mpls ldp neighbor", title="M2")
    pe1.show("traceroute vrf CUST_A 172.16.2.1 source 192.168.1.2 numeric timeout 1", wait=10, title="M3")
    pe1.show("show bgp vpnv4 unicast all", title="M6")
    pe1.show("show bgp vpnv4 unicast all summary", title="M6")
    pe1.show("show bgp vpnv4 unicast rd 65000:100 172.16.2.0/24", title="M6")
    pe1.show("show ip route vrf CUST_A", title="M6")
    pe1.show("show ip route vrf CUST_B", title="M6")
    pe1.show("show vrf", title="M6")
    pe1.show("show vrf detail CUST_A", title="M6")
    pe1.show("show running-config | section vrf definition", title="M6")
    pe1.show("show running-config | section router bgp", title="M6")
    pe2.show("show bgp vpnv4 unicast all", title="M6")

    # ---- M4: LSP の穴(P の PE2 向け IF で LDP を落とす) ----
    LOG.append("\n## M4 LSP の穴(RT02 Et0/1 no mpls ip)\n")
    p.conf(["interface Ethernet0/1", "no mpls ip"], title="M4 投入")
    time.sleep(35)
    pe1.show("show mpls forwarding-table", title="M4")
    pe1.show("show mpls ldp neighbor", title="M4")
    pe1.show("show ip route vrf CUST_A | include 172.16.2", title="M4")
    pe1.show("ping vrf CUST_A 172.16.2.1 source 192.168.1.2 repeat 3", wait=8, title="M4")
    pe1.show("show ip route 3.3.3.3", title="M4")
    p.show("show mpls ldp neighbor", title="M4")
    p.show("show mpls forwarding-table", title="M4")
    p.show("show mpls interfaces", title="M4")
    pe2.show("show mpls ldp neighbor", title="M4")
    p.conf(["interface Ethernet0/1", "mpls ip"], title="M4 復旧")
    time.sleep(35)
    pe1.show("ping vrf CUST_A 172.16.2.1 source 192.168.1.2 repeat 3", wait=8, title="M4 復旧確認")

    # ---- M5: LDP router-id(transport address)が到達不能 ----
    LOG.append("\n## M5 LDP router-id を未広告の Loopback9 に(transport address 不達)\n")
    pe1.conf(["interface Loopback9", "ip address 10.99.1.1 255.255.255.255", "exit", "mpls ldp router-id Loopback9 force"], title="M5 投入")
    time.sleep(45)
    pe1.show("show mpls ldp neighbor", title="M5")
    pe1.show("show mpls ldp discovery", title="M5")
    pe1.show("show mpls ldp discovery detail", title="M5")
    p.show("show mpls ldp neighbor", title="M5")
    p.show("show mpls ldp discovery detail", title="M5")
    pe1.show("ping vrf CUST_A 172.16.2.1 source 192.168.1.2 repeat 3", wait=8, title="M5")
    pe1.conf(["mpls ldp router-id Loopback0 force", "no interface Loopback9"], title="M5 復旧")
    time.sleep(45)
    pe1.show("show mpls ldp neighbor | include Peer|TCP", title="M5 復旧確認")

    # ---- M7: RT import の取り違え(PE2 の CUST_A) ----
    LOG.append("\n## M7 RT import 取り違え(RT03 CUST_A import 65000:100→65000:555)\n")
    pe2.conf(["vrf definition CUST_A", "address-family ipv4", "no route-target import 65000:100", "route-target import 65000:555", "exit-address-family", "exit"], title="M7 投入")
    time.sleep(75)
    pe2.show("show ip route vrf CUST_A", title="M7")
    pe2.show("show bgp vpnv4 unicast all", title="M7")
    pe2.show("show bgp vpnv4 unicast vrf CUST_A", title="M7")
    pe2.show("show bgp vpnv4 unicast all summary", title="M7")
    pe1.show("show ip route vrf CUST_A | include 172.16.2", title="M7 (PE1 側は不変か)")
    pe1.show("show bgp vpnv4 unicast all", title="M7 (PE1 側)")
    pe2.conf(["vrf definition CUST_A", "address-family ipv4", "no route-target import 65000:555", "route-target import 65000:100", "exit-address-family", "exit"], title="M7 復旧")
    time.sleep(70)
    pe2.show("show ip route vrf CUST_A | include 172.16.1", title="M7 復旧確認")

    # ---- M8: 同一 PE で 2 VRF に同じ RD ----
    LOG.append("\n## M8 同一 PE で CUST_B の RD を CUST_A と同じ 65000:100 に\n")
    out = pe1.conf(["vrf definition CUST_B", "rd 65000:100", "exit"], title="M8 投入(応答)")
    time.sleep(5)
    pe1.show("show vrf", title="M8")
    pe1.show("show ip interface brief | include Ethernet0/2", title="M8")
    pe1.show("show running-config | section vrf definition CUST_B", title="M8")
    pe1.conf(["vrf definition CUST_B", "rd 65000:200", "exit"], title="M8 復旧(応答)")
    time.sleep(5)
    pe1.show("show ip interface brief | include Ethernet0/2", title="M8 復旧確認")
    ib = pe1.show("show ip interface brief | include Ethernet0/2")
    if "192.168.11.2" not in ib:
        pe1.conf(["interface Ethernet0/2", "vrf forwarding CUST_B", "ip address 192.168.11.2 255.255.255.252"], title="M8 IP 再投入")
        time.sleep(5)
        pe1.show("show ip interface brief | include Ethernet0/2", title="M8 IP 再投入確認")

    # ---- M9: send-community extended / activate の欠落 ----
    LOG.append("\n## M9a vpnv4 ネイバーの send-community extended を外す(PE1)\n")
    pe1.conf(["router bgp 65000", "address-family vpnv4", "no neighbor 3.3.3.3 send-community extended", "exit-address-family", "exit"], title="M9a 投入")
    time.sleep(75)
    pe1.show("show running-config | section address-family vpnv4", title="M9a")
    pe2.show("show bgp vpnv4 unicast all summary", title="M9a")
    pe2.show("show ip route vrf CUST_A", title="M9a")
    pe2.show("show bgp vpnv4 unicast all", title="M9a")
    pe1.conf(["router bgp 65000", "address-family vpnv4", "neighbor 3.3.3.3 send-community extended", "exit-address-family", "exit"], title="M9a 復旧")
    time.sleep(70)
    pe2.show("show ip route vrf CUST_A | include 172.16.1", title="M9a 復旧確認")
    LOG.append("\n## M9b vpnv4 ネイバーの activate を外す(PE1)\n")
    pe1.conf(["router bgp 65000", "address-family vpnv4", "no neighbor 3.3.3.3 activate", "exit-address-family", "exit"], title="M9b 投入")
    time.sleep(25)
    pe1.show("show running-config | section address-family vpnv4", title="M9b")
    pe1.show("show bgp vpnv4 unicast all summary", title="M9b")
    pe2.show("show bgp vpnv4 unicast all summary", title="M9b")
    pe2.show("show ip route vrf CUST_A", title="M9b")
    pe1.conf(["router bgp 65000", "address-family vpnv4", "neighbor 3.3.3.3 activate", "neighbor 3.3.3.3 send-community extended", "exit-address-family", "exit"], title="M9b 復旧")
    time.sleep(70)
    pe1.show("show running-config | section address-family vpnv4", title="M9b 復旧確認")
    pe2.show("show ip route vrf CUST_A | include 172.16.1", title="M9b 復旧確認")

    # ---- M14: LDP autoconfig の受理 ----
    LOG.append("\n## M14 mpls ldp autoconfig(OSPF で受理・EIGRP で不可)\n")
    p.conf(["router ospf 1", "mpls ldp autoconfig", "exit"], title="M14 OSPF")
    time.sleep(3)
    p.show("show mpls interfaces", title="M14")
    p.show("show running-config | section router ospf", title="M14")
    p.conf(["router ospf 1", "no mpls ldp autoconfig", "exit"], title="M14 OSPF 復旧")
    p.conf(["router eigrp 99", "mpls ldp autoconfig", "exit", "no router eigrp 99"], title="M14 EIGRP(応答)")

    # ---- 最終基線確認 ----
    LOG.append("\n## 最終基線確認\n")
    time.sleep(20)
    ce1.show("ping 172.16.2.1 source 172.16.1.1 repeat 5", wait=8, title="最終")
    pe1.show("show mpls ldp neighbor | include Peer", title="最終")
    for d in (pe1, p, pe2, ce1):
        d.close()
    LOG.append(f"\n(所要 {int(time.time() - t0)} 秒)\n")
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
