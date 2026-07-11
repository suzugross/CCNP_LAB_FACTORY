#!/usr/bin/env python3
"""CAMPUS-TS-01: 3層キャンパスLAN 障害演習ラボの生成器 (BL-040)。

faults トグル → 全ノードの day0 config ＋ CML ラボ YAML を生成する。
設計の一次ソース: problems/_drafts/CAMPUS-TS.design.md
Phase 0 実機知見: poc/campus/README.md（ip mtu 統一・ingress unreachables 等）
ASAv 制約: poc/asav/README.md（day0 不発→bootstrap・パスワード8字・ACL実IP）

トポロジ (11 VM + MGMTSW/SRVSW/EXTC):
  core1/core2(iosv,OSPF) - dist1/dist2(iosvl2,SVI/HSRP/STP) - acc1/acc2(iosvl2,L2)
  asa1(asav: outside=core1側/inside=サーバ網) svr1(BIND9+ISC DHCP+nginx)
  cli10@acc1(VLAN10) cli30@acc2(VLAN30) cli40@acc2(VLAN40)
  サーバ網 10.20.0.0/24 = SRVSW に asa1-inside / core2バックドア(cost1000) / svr1

faults (同時に 1 つのみ true / 全 false = golden):
  trunk_allowed_mismatch : acc2 両アップリンクの allowed vlan から 40 を除外
  ospf_mtu_mismatch      : core1 Gi0/1(dist1向け) ip mtu 1400→1300
  dhcp_relay_gap         : dist2 SVI30 の ip helper-address 削除
  asa_asymmetric_drop    : core2 バックドア ip ospf cost 1000→5
  pmtud_blackhole        : core1 adjust-mss 削除 + Gi0/3 no ip unreachables

usage:
  gen_campus_lab.py --repo . [--fault <name>] [--mgmt-map FILE]
    → topologies/_generated/CAMPUS-TS-01/{lab.yaml, day0/<node>.cfg, state.json}
"""
import argparse
import json
import os
import sys

import yaml

PROBLEM = "CAMPUS-TS-01"
LAB_TITLE = "CAMPUS-TS-01"

FAULTS = ["trunk_allowed_mismatch", "ospf_mtu_mismatch", "dhcp_relay_gap",
          "asa_asymmetric_drop", "pmtud_blackhole"]

NODES = ["core1", "core2", "dist1", "dist2", "acc1", "acc2",
         "asa1", "svr1", "cli10", "cli30", "cli40"]

# fault → day0 が変わるノード（inject/reset 時の差し替え対象）
FAULT_NODES = {
    "trunk_allowed_mismatch": ["acc2"],
    "ospf_mtu_mismatch": ["core1"],
    "dhcp_relay_gap": ["dist2"],
    "asa_asymmetric_drop": ["core2"],
    "pmtud_blackhole": ["core1"],
}

MGMT_MASK = "255.255.255.192"
MGMT_PLEN = 26
MGMT_GW = "10.1.10.30"
MGMT_DNS = ["8.8.8.8", "8.8.4.4"]

VLANS = {10: "USERS-A", 20: "USERS-B", 30: "GUEST", 40: "IOT"}
SVR_IP = "10.20.0.10"


def ios_common(host, mgmt_ip, mgmt_if):
    # ★本問は ASA(パスワード8字以上必須)との収集クレデンシャル統一のため
    #   IOS 側も CCNPccnp を使う（リポ標準 CCNP と異なる点に注意・task.md に明記）
    return f"""hostname {host}
no ip domain lookup
ip cef
!
enable secret CCNPccnp
username SUZUKI privilege 15 secret CCNPccnp
!
vrf definition MGMT
 rd 65001:1
 address-family ipv4
 exit-address-family
!
interface {mgmt_if}
 description === MGMT (Ansible) ===
 vrf forwarding MGMT
 ip address {mgmt_ip} {MGMT_MASK}
 no shutdown
!"""


def ios_tail():
    return """!
line con 0
 exec-timeout 0 0
 logging synchronous
line vty 0 4
 exec-timeout 0 0
 login local
 transport input ssh
"""


def cfg_core1(f, mgmt):
    mtu_d1 = "1300" if f["ospf_mtu_mismatch"] else "1400"
    mss = "" if f["pmtud_blackhole"] else "\n ip tcp adjust-mss 1360"
    unreach = "\n no ip unreachables" if f["pmtud_blackhole"] else ""
    return f"""{ios_common('core1', mgmt['core1'], 'GigabitEthernet0/4')}
interface Loopback0
 ip address 1.1.1.1 255.255.255.255
!
interface GigabitEthernet0/0
 description === to core2 (p2p) ===
 ip address 10.254.0.1 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 no shutdown
!
interface GigabitEthernet0/1
 description === to dist1 (p2p / legacy transport MTU1400) ===
 ip address 10.254.1.1 255.255.255.252
 ip mtu {mtu_d1}{mss}
 ip ospf network point-to-point
 ip ospf cost 10
 no shutdown
!
interface GigabitEthernet0/2
 description === to dist2 (p2p / legacy transport MTU1400) ===
 ip address 10.254.2.1 255.255.255.252
 ip mtu 1400{mss}
 ip ospf network point-to-point
 ip ospf cost 10
 no shutdown
!
interface GigabitEthernet0/3
 description === to asa1 outside ==={unreach}
 ip address 10.254.3.1 255.255.255.252
 ip ospf cost 10
 no shutdown
!
router ospf 1
 router-id 1.1.1.1
 network 10.254.0.0 0.0.0.3 area 0
 network 10.254.1.0 0.0.0.3 area 0
 network 10.254.2.0 0.0.0.3 area 0
 network 10.254.3.0 0.0.0.3 area 0
 network 1.1.1.1 0.0.0.0 area 0
{ios_tail()}"""


def cfg_core2(f, mgmt):
    # ★バックドアは golden では shutdown（connected 経路が居ると core2 経由の
    #   transit が常に ASA を短絡してしまう＝F2 の副作用として実機で確認 2026-07-10）
    backdoor_cost = "5" if f["asa_asymmetric_drop"] else "1000"
    backdoor_admin = "no shutdown" if f["asa_asymmetric_drop"] else "shutdown"
    return f"""{ios_common('core2', mgmt['core2'], 'GigabitEthernet0/4')}
interface Loopback0
 ip address 2.2.2.2 255.255.255.255
!
interface GigabitEthernet0/0
 description === to core1 (p2p) ===
 ip address 10.254.0.2 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 no shutdown
!
interface GigabitEthernet0/1
 description === to dist1 (p2p) ===
 ip address 10.254.4.1 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 no shutdown
!
interface GigabitEthernet0/2
 description === to dist2 (p2p) ===
 ip address 10.254.5.1 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 no shutdown
!
interface GigabitEthernet0/3
 description === server segment backup (kept shutdown in normal ops) ===
 ip address 10.20.0.3 255.255.255.0
 ip ospf cost {backdoor_cost}
 {backdoor_admin}
!
router ospf 1
 router-id 2.2.2.2
 passive-interface GigabitEthernet0/3
 network 10.254.0.0 0.0.0.3 area 0
 network 10.254.4.0 0.0.0.3 area 0
 network 10.254.5.0 0.0.0.3 area 0
 network 10.20.0.0 0.0.0.255 area 0
 network 2.2.2.2 0.0.0.0 area 0
{ios_tail()}"""


def cfg_dist(n, f, mgmt):
    """dist1 / dist2 (iosvl2)"""
    is1 = n == "dist1"
    rid = "3.3.3.3" if is1 else "4.4.4.4"
    ip_c1 = "10.254.1.2" if is1 else "10.254.2.2"   # core1 向け (MTU1400区間)
    ip_c2 = "10.254.4.2" if is1 else "10.254.5.2"   # core2 向け
    net_c1 = "10.254.1.0" if is1 else "10.254.2.0"
    net_c2 = "10.254.4.0" if is1 else "10.254.5.0"
    # STP/HSRP: VLAN10/30 → dist1 / VLAN20/40 → dist2
    my_vlans = [10, 30] if is1 else [20, 40]
    svis = []
    for v in sorted(VLANS):
        octet = "2" if is1 else "3"
        prio = 110 if v in my_vlans else 100
        helper = f"\n ip helper-address {SVR_IP}"
        if v == 30 and n == "dist2" and f["dhcp_relay_gap"]:
            helper = ""
        svis.append(f"""interface Vlan{v}
 ip address 10.10.{v}.{octet} 255.255.255.0{helper}
 standby {v} ip 10.10.{v}.1
 standby {v} priority {prio}
 standby {v} preempt
 no shutdown
!""")
    stp = (f"spanning-tree vlan {my_vlans[0]},{my_vlans[1]} priority 4096\n"
           f"spanning-tree vlan {[v for v in VLANS if v not in my_vlans][0]},"
           f"{[v for v in VLANS if v not in my_vlans][1]} priority 8192")
    return f"""hostname {n}
no ip domain lookup
ip routing
ip cef
!
enable secret CCNPccnp
username SUZUKI privilege 15 secret CCNPccnp
!
vtp mode transparent
!
vlan 10
 name USERS-A
vlan 20
 name USERS-B
vlan 30
 name GUEST
vlan 40
 name IOT
!
{stp}
!
interface GigabitEthernet3/3
 description === MGMT (Ansible) ===
 no switchport
 ip address {mgmt[n]} {MGMT_MASK}
 no shutdown
!
interface Loopback0
 ip address {rid} 255.255.255.255
!
interface GigabitEthernet0/0
 description === to core1 (p2p routed / legacy transport MTU1400) ===
 no switchport
 ip address {ip_c1} 255.255.255.252
 ip mtu 1400
 ip ospf network point-to-point
 ip ospf cost 10
 no shutdown
!
interface GigabitEthernet0/1
 description === to core2 (p2p routed) ===
 no switchport
 ip address {ip_c2} 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 no shutdown
!
interface GigabitEthernet0/2
 description === to {'dist2' if is1 else 'dist1'} trunk ===
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30,40
 no shutdown
!
interface GigabitEthernet1/0
 description === to acc1 trunk ===
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30,40
 no shutdown
!
interface GigabitEthernet1/1
 description === to acc2 trunk ===
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30,40
 no shutdown
!
{chr(10).join(svis)}
router ospf 1
 router-id {rid}
 passive-interface default
 no passive-interface GigabitEthernet0/0
 no passive-interface GigabitEthernet0/1
 network {net_c1} 0.0.0.3 area 0
 network {net_c2} 0.0.0.3 area 0
 network 10.10.0.0 0.0.255.255 area 0
 network {rid} 0.0.0.0 area 0
{ios_tail()}"""


def cfg_acc(n, f, mgmt):
    """acc1 / acc2 (iosvl2, 純L2)"""
    allowed = "10,20,30,40"
    if n == "acc2" and f["trunk_allowed_mismatch"]:
        allowed = "10,20,30"   # VLAN40 の add 忘れを再現
    access_ports = (
        """interface GigabitEthernet1/0
 description === cli10 (VLAN10) ===
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
!""" if n == "acc1" else
        """interface GigabitEthernet1/0
 description === cli30 (VLAN30) ===
 switchport mode access
 switchport access vlan 30
 spanning-tree portfast
 no shutdown
!
interface GigabitEthernet1/1
 description === cli40 (VLAN40) ===
 switchport mode access
 switchport access vlan 40
 spanning-tree portfast
 no shutdown
!""")
    return f"""hostname {n}
no ip domain lookup
!
enable secret CCNPccnp
username SUZUKI privilege 15 secret CCNPccnp
!
vtp mode transparent
!
vlan 10
 name USERS-A
vlan 20
 name USERS-B
vlan 30
 name GUEST
vlan 40
 name IOT
!
interface GigabitEthernet3/3
 description === MGMT (Ansible) ===
 no switchport
 ip address {mgmt[n]} {MGMT_MASK}
 no shutdown
!
interface GigabitEthernet0/0
 description === to dist1 trunk ===
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan {allowed}
 no shutdown
!
interface GigabitEthernet0/1
 description === to dist2 trunk ===
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan {allowed}
 no shutdown
!
{access_ports}
line con 0
 exec-timeout 0 0
 logging synchronous
line vty 0 4
 exec-timeout 0 0
 login local
 transport input ssh
"""


def cfg_asa1(f, mgmt):
    """asa1 (asav)。day0 は不発 → campus_ops.py bootstrap がこれを console 投入。"""
    return f"""hostname asa1
enable password CCNPccnp
username SUZUKI password CCNPccnp privilege 15
!
interface Management0/0
 management-only
 nameif management
 security-level 100
 ip address {mgmt['asa1']} {MGMT_MASK}
 no shutdown
!
interface GigabitEthernet0/0
 nameif outside
 security-level 0
 ip address 10.254.3.2 255.255.255.252
 ospf cost 10
 no shutdown
!
interface GigabitEthernet0/1
 nameif inside
 security-level 100
 ip address 10.20.0.1 255.255.255.0
 ospf cost 10
 no shutdown
!
router ospf 1
 router-id 5.5.5.5
 network 10.254.3.0 255.255.255.252 area 0
 network 10.20.0.0 255.255.255.0 area 0
!
access-list OUTSIDE_IN extended permit icmp any 10.20.0.0 255.255.255.0
access-list OUTSIDE_IN extended permit udp any host {SVR_IP} eq domain
access-list OUTSIDE_IN extended permit tcp any host {SVR_IP} eq domain
access-list OUTSIDE_IN extended permit tcp any host {SVR_IP} eq www
access-list OUTSIDE_IN extended permit udp any host {SVR_IP} eq bootps
access-group OUTSIDE_IN in interface outside
!
icmp permit any outside
icmp permit any inside
!
aaa authentication ssh console LOCAL
aaa authorization exec LOCAL auto-enable
ssh 10.1.10.0 255.255.255.192 management
"""


def svr1_user_data(mgmt):
    zone = f"""$TTL 300
@ IN SOA svr1.lab.local. admin.lab.local. ( 1 3600 900 604800 300 )
@ IN NS svr1.lab.local.
svr1 IN A {SVR_IP}
www  IN CNAME svr1
"""
    dhcpd = f"""option domain-name "lab.local";
option domain-name-servers {SVR_IP};
default-lease-time 600;
max-lease-time 7200;
authoritative;
subnet 10.20.0.0 netmask 255.255.255.0 {{ }}
""" + "".join(
        f"""subnet 10.10.{v}.0 netmask 255.255.255.0 {{
  range 10.10.{v}.100 10.10.{v}.199;
  option routers 10.10.{v}.1;
}}
""" for v in sorted(VLANS))
    named_local = """zone "lab.local" {
  type master;
  file "/etc/bind/db.lab.local";
};
"""
    named_opts = f"""options {{
  directory "/var/cache/bind";
  recursion yes;
  allow-query {{ any; }};
  listen-on {{ 127.0.0.1; {SVR_IP}; }};
  forwarders {{ 8.8.8.8; }};
  dnssec-validation no;
}};
"""
    return f"""#cloud-config
hostname: svr1
manage_etc_hosts: true
system_info:
  default_user:
    name: suzuki
password: CCNP
chpasswd: {{ expire: false }}
ssh_pwauth: true
package_update: true
packages:
  - bind9
  - isc-dhcp-server
  - nginx
write_files:
  - path: /etc/bind/named.conf.options
    content: |
{_indent(named_opts, 6)}
  - path: /etc/bind/named.conf.local
    content: |
{_indent(named_local, 6)}
  - path: /etc/bind/db.lab.local
    content: |
{_indent(zone, 6)}
  - path: /etc/dhcp/dhcpd.conf
    content: |
{_indent(dhcpd, 6)}
  - path: /etc/default/isc-dhcp-server
    content: |
      INTERFACESv4="ens3"
      INTERFACESv6=""
runcmd:
  - head -c 204800 /dev/urandom > /var/www/html/big.bin
  - echo "CAMPUS-TS svr1 OK" > /var/www/html/index.html
  - systemctl restart named || systemctl restart bind9
  - systemctl restart isc-dhcp-server
  - systemctl restart nginx
  - date -Is > /var/tmp/campus_cloudinit_done
"""


def _indent(text, n):
    pad = " " * n
    return "\n".join(pad + l for l in text.splitlines())


def svr1_net(mgmt):
    return f"""#network-config
network:
  version: 2
  ethernets:
    ens2:
      addresses: [{mgmt['svr1']}/{MGMT_PLEN}]
      routes:
        - to: default
          via: {MGMT_GW}
      nameservers:
        addresses: {json.dumps(MGMT_DNS)}
    ens3:
      addresses: [{SVR_IP}/24]
      routes:
        - to: 10.10.0.0/16
          via: 10.20.0.1
        - to: 10.254.0.0/16
          via: 10.20.0.1
"""


def cli_user_data(name):
    return f"""#cloud-config
hostname: {name}
manage_etc_hosts: true
system_info:
  default_user:
    name: suzuki
password: CCNP
chpasswd: {{ expire: false }}
ssh_pwauth: true
package_update: true
packages:
  - curl
  - dnsutils
runcmd:
  - date -Is > /var/tmp/campus_cloudinit_done
"""


def cli_net(name, vlan, mgmt):
    gw = f"10.10.{vlan}.1"
    return f"""#network-config
network:
  version: 2
  ethernets:
    ens2:
      addresses: [{mgmt[name]}/{MGMT_PLEN}]
      routes:
        - to: default
          via: {MGMT_GW}
      nameservers:
        addresses: {json.dumps(MGMT_DNS)}
    ens3:
      dhcp4: true
      dhcp4-overrides:
        use-routes: false
      routes:
        - to: 10.20.0.0/24
          via: {gw}
        - to: 10.10.0.0/16
          via: {gw}
        - to: 10.254.0.0/16
          via: {gw}
"""


# ---- CML ラボ YAML 組み立て ------------------------------------------------

IOSVL2_SLOTS = {0: "GigabitEthernet0/0", 1: "GigabitEthernet0/1",
                2: "GigabitEthernet0/2", 3: "GigabitEthernet0/3",
                4: "GigabitEthernet1/0", 5: "GigabitEthernet1/1",
                15: "GigabitEthernet3/3"}


def _ifaces(node, slots, labels):
    return [{"id": f"{node}-i{s}", "label": labels[s], "type": "physical",
             "slot": s} for s in slots]


def build_lab(faults, mgmt):
    f = {k: (faults.get(k) or False) for k in FAULTS}
    cfgs = {
        "core1": cfg_core1(f, mgmt),
        "core2": cfg_core2(f, mgmt),
        "dist1": cfg_dist("dist1", f, mgmt),
        "dist2": cfg_dist("dist2", f, mgmt),
        "acc1": cfg_acc("acc1", f, mgmt),
        "acc2": cfg_acc("acc2", f, mgmt),
        "asa1": cfg_asa1(f, mgmt),
    }
    iosv_lbl = {i: f"GigabitEthernet0/{i}" for i in range(5)}
    nodes = []
    pos = {"core1": (-100, -300), "core2": (200, -300), "dist1": (-250, -100),
           "dist2": (350, -100), "acc1": (-250, 100), "acc2": (350, 100),
           "asa1": (500, -450), "svr1": (700, -300), "cli10": (-250, 280),
           "cli30": (250, 280), "cli40": (450, 280),
           "MGMTSW": (50, 450), "SRVSW": (700, -150), "EXTC": (50, 600)}

    for n in ("core1", "core2"):
        nodes.append({"id": n, "label": n, "node_definition": "iosv",
                      "image_definition": "iosv-159-3-m9",
                      "configuration": cfgs[n],
                      "x": pos[n][0], "y": pos[n][1], "tags": ["routers"],
                      "interfaces": _ifaces(n, [0, 1, 2, 3, 4], iosv_lbl)})
    for n in ("dist1", "dist2"):
        nodes.append({"id": n, "label": n, "node_definition": "iosvl2",
                      "image_definition": "iosvl2-2020",
                      "configuration": cfgs[n],
                      "x": pos[n][0], "y": pos[n][1], "tags": ["switches"],
                      "interfaces": _ifaces(n, [0, 1, 2, 4, 5, 15], IOSVL2_SLOTS)})
    for n in ("acc1", "acc2"):
        nodes.append({"id": n, "label": n, "node_definition": "iosvl2",
                      "image_definition": "iosvl2-2020",
                      "configuration": cfgs[n],
                      "x": pos[n][0], "y": pos[n][1], "tags": ["switches"],
                      "interfaces": _ifaces(n, [0, 1, 4, 5, 15], IOSVL2_SLOTS)})
    # asa1: day0 不発だが正準 config として保持(campus_ops bootstrap が投入)
    nodes.append({"id": "asa1", "label": "asa1", "node_definition": "asav",
                  "image_definition": "asav-9-22-1-1", "ram": 2048,
                  "configuration": [{"name": "day0-config", "content": cfgs["asa1"]}],
                  "x": pos["asa1"][0], "y": pos["asa1"][1], "tags": ["firewalls"],
                  "interfaces": [
                      {"id": "asa1-i0", "label": "Management0/0", "type": "physical", "slot": 0},
                      {"id": "asa1-i1", "label": "GigabitEthernet0/0", "type": "physical", "slot": 1},
                      {"id": "asa1-i2", "label": "GigabitEthernet0/1", "type": "physical", "slot": 2}]})
    # linux
    lin = {"svr1": (svr1_user_data(mgmt), svr1_net(mgmt)),
           "cli10": (cli_user_data("cli10"), cli_net("cli10", 10, mgmt)),
           "cli30": (cli_user_data("cli30"), cli_net("cli30", 30, mgmt)),
           "cli40": (cli_user_data("cli40"), cli_net("cli40", 40, mgmt))}
    for n, (ud, nc) in lin.items():
        nodes.append({"id": n, "label": n, "node_definition": "ubuntu",
                      "image_definition": "ubuntu-24-04-20241004", "ram": 2048,
                      "configuration": [{"name": "user-data", "content": ud},
                                        {"name": "network-config", "content": nc}],
                      "x": pos[n][0], "y": pos[n][1], "tags": ["servers"],
                      "interfaces": [
                          {"id": f"{n}-i0", "label": "ens2", "type": "physical", "slot": 0},
                          {"id": f"{n}-i1", "label": "ens3", "type": "physical", "slot": 1}]})
    # 補助
    nodes.append({"id": "MGMTSW", "label": "MGMT-SW", "node_definition": "unmanaged_switch",
                  "image_definition": None, "configuration": "",
                  "x": pos["MGMTSW"][0], "y": pos["MGMTSW"][1], "tags": [],
                  "interfaces": [{"id": f"MGMTSW-i{i}", "label": f"port{i}",
                                  "type": "physical", "slot": i} for i in range(12)]})
    nodes.append({"id": "SRVSW", "label": "SRV-SW", "node_definition": "unmanaged_switch",
                  "image_definition": None, "configuration": "",
                  "x": pos["SRVSW"][0], "y": pos["SRVSW"][1], "tags": [],
                  "interfaces": [{"id": f"SRVSW-i{i}", "label": f"port{i}",
                                  "type": "physical", "slot": i} for i in range(4)]})
    nodes.append({"id": "EXTC", "label": "to-MGMT-net", "node_definition": "external_connector",
                  "image_definition": None, "configuration": "System Bridge",
                  "x": pos["EXTC"][0], "y": pos["EXTC"][1], "tags": [],
                  "interfaces": [{"id": "EXTC-i0", "label": "port", "type": "physical", "slot": 0}]})

    data_links = [
        ("core1", 0, "core2", 0), ("core1", 1, "dist1", 0), ("core1", 2, "dist2", 0),
        ("core1", 3, "asa1", 1), ("core2", 1, "dist1", 1), ("core2", 2, "dist2", 1),
        ("dist1", 2, "dist2", 2), ("dist1", 4, "acc1", 0), ("dist1", 5, "acc2", 0),
        ("dist2", 4, "acc1", 1), ("dist2", 5, "acc2", 1),
        ("acc1", 4, "cli10", 1), ("acc2", 4, "cli30", 1), ("acc2", 5, "cli40", 1),
        ("asa1", 2, "SRVSW", 0), ("core2", 3, "SRVSW", 1), ("svr1", 1, "SRVSW", 2),
    ]
    mgmt_links = [("core1", 4), ("core2", 4), ("dist1", 15), ("dist2", 15),
                  ("acc1", 15), ("acc2", 15), ("asa1", 0), ("svr1", 0),
                  ("cli10", 0), ("cli30", 0), ("cli40", 0)]
    links = []
    for i, (a, ai, b, bi) in enumerate(data_links):
        links.append({"id": f"l{i}", "n1": a, "i1": f"{a}-i{ai}",
                      "n2": b, "i2": f"{b}-i{bi}", "conditioning": {},
                      "label": f"{a}<->{b}"})
    for j, (a, ai) in enumerate(mgmt_links):
        links.append({"id": f"m{j}", "n1": a, "i1": f"{a}-i{ai}",
                      "n2": "MGMTSW", "i2": f"MGMTSW-i{j}", "conditioning": {},
                      "label": f"{a}-mgmt"})
    links.append({"id": "mup", "n1": "MGMTSW", "i1": "MGMTSW-i11",
                  "n2": "EXTC", "i2": "EXTC-i0", "conditioning": {},
                  "label": "mgmt-uplink"})

    import base64
    lease = {"ccnp_lease": {"p64": base64.b64encode(PROBLEM.encode()).decode(),
                            "nodes": mgmt}}
    active = [k for k, v in f.items() if v]
    lab = {
        "lab": {
            "title": LAB_TITLE,
            "description": json.dumps(lease),
            "notes": f"CAMPUS-TS-01 (BL-040) fault={active[0] if active else 'none(golden)'}",
            "version": "0.3.0",
        },
        "nodes": nodes,
        "links": links,
        "annotations": [],
        "smart_annotations": [],
    }
    return lab, cfgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--fault", default="none",
                    help=f"none | {' | '.join(FAULTS)}")
    ap.add_argument("--mgmt-map", default=None,
                    help="mgmt_map.yml (無指定は _generated/<ID>/mgmt_map.yml)")
    a = ap.parse_args()
    if a.fault != "none" and a.fault not in FAULTS:
        sys.exit(f"unknown fault: {a.fault}")

    out = os.path.join(a.repo, "topologies", "_generated", PROBLEM)
    os.makedirs(os.path.join(out, "day0"), exist_ok=True)
    mm_path = a.mgmt_map or os.path.join(out, "mgmt_map.yml")
    mm = yaml.safe_load(open(mm_path))
    mgmt = mm["mgmt_map"] if "mgmt_map" in mm else mm

    faults = {k: (k == a.fault) for k in FAULTS}
    lab, cfgs = build_lab(faults, mgmt)

    lab_path = os.path.join(out, "lab.yaml")
    with open(lab_path, "w") as fp:
        yaml.safe_dump(lab, fp, sort_keys=False, allow_unicode=True, width=10000)
    for n, c in cfgs.items():
        open(os.path.join(out, "day0", f"{n}.cfg"), "w").write(c)
    state = {"problem": PROBLEM, "fault": a.fault,
             "fault_nodes": FAULT_NODES.get(a.fault, [])}
    json.dump(state, open(os.path.join(out, "state.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"[gen_campus_lab] fault={a.fault} → {lab_path}")


if __name__ == "__main__":
    main()
