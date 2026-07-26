#!/usr/bin/env python3
"""GEN-S2SVPN 生成器 (BL-063): 実務想定・複数拠点 IPsec VPN 設計構築問。

要件書(task.md)だけを渡して VPN 方式(DMVPN/sVTI/crypto map)の選定から演習者に
委ねる設計構築問。採点は解法非依存の効果ベース(topologies/s2svpn_ops.py grade)。

seed 軸:
  A. トンネルポリシー   : 支店ごとに full(本社経由集約) / split(ローカルブレイクアウト)
  B. 支店間通信ポリシー : allow_all / deny_all / icmp_only / http_only
  C. 公開サーバ         : 本社 Web(H-HQ) を HQ 公開IP:8080 で静的NAT公開する/しない
  D. 社内アドレス帯     : 10.x / 172.16-23.x / 192.168.x から抽選

トポロジ(8ノード・コンソールのみ・MGMTリース不使用):
  H-HQ(alpine) - HQ(IOSv)  - 203.0.113.0/30 -+
  H-B1(alpine) - BR1(IOSv) - 203.0.113.4/30 -+- INET(IOL,変更禁止) - SRV(alpine 198.51.100.80)
  H-B2(alpine) - BR2(IOSv) - 203.0.113.8/30 -+

使い方:
  python3 topologies/gen_s2svpn.py --seed 4126            # problems/GEN-S2SVPN-4126/ を生成
  python3 topologies/gen_s2svpn.py --seed 4126 --show     # 軸の抽選結果だけ表示
運用:
  python3 topologies/s2svpn_ops.py build|solve|grade|teardown --problem GEN-S2SVPN-<seed>
"""
import argparse
import hashlib
import json
import os
import random

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PUB = {
    "HQ":  {"net": "203.0.113.0",  "inet": "203.0.113.1", "rtr": "203.0.113.2"},
    "BR1": {"net": "203.0.113.4",  "inet": "203.0.113.5", "rtr": "203.0.113.6"},
    "BR2": {"net": "203.0.113.8",  "inet": "203.0.113.9", "rtr": "203.0.113.10"},
    "BR3": {"net": "203.0.113.12", "inet": "203.0.113.13", "rtr": "203.0.113.14"},
    "BR4": {"net": "203.0.113.16", "inet": "203.0.113.17", "rtr": "203.0.113.18"},
}
SRV_IP, SRV_GW = "198.51.100.80", "198.51.100.1"
OVL = {"BR1": ("10.254.254.1", "10.254.254.2"),   # (HQ側, BR側) /30
       "BR2": ("10.254.254.5", "10.254.254.6"),
       "BR3": ("10.254.254.9", "10.254.254.10"),
       "BR4": ("10.254.254.13", "10.254.254.14")}
PSK = "Ss2026#S2sVpn"
BIGBIN = 204800  # /www/big.bin のバイト数(MTU/MSS 効果採点)

B2B_LABEL = {
    "allow_all": "支店間の相互通信を全面的に許可する",
    "deny_all": "支店間の直接通信は情報分離ポリシーにより全て遮断する(各支店と本社の間は通信可)",
    "icmp_only": "支店間は死活監視(ICMP)のみ許可し、その他の通信は遮断する",
    "http_only": "支店間は業務Web(TCP/80)のみ許可し、その他の通信(ICMPを含む)は遮断する",
}


def pick_axes(seed):
    rng = random.Random(seed)
    tun = {"BR1": rng.choice(["full", "split"]), "BR2": rng.choice(["full", "split"])}
    b2b = rng.choice(["allow_all", "deny_all", "icmp_only", "http_only"])
    pubsrv = rng.choice([True, False])
    scheme = rng.choice(["10", "172", "192"])
    if scheme == "10":
        r = rng.randint(20, 99)
        lan = {"HQ": f"10.{r}.10", "BR1": f"10.{r}.21", "BR2": f"10.{r}.22"}
    elif scheme == "172":
        o = rng.randint(16, 23)
        lan = {"HQ": f"172.{o}.10", "BR1": f"172.{o}.21", "BR2": f"172.{o}.22"}
    else:
        octs = rng.sample(range(10, 250), 3)
        lan = {"HQ": f"192.168.{octs[0]}", "BR1": f"192.168.{octs[1]}",
               "BR2": f"192.168.{octs[2]}"}
    return {"tun": tun, "b2b": b2b, "pubsrv": pubsrv, "lan": lan}


# ----------------------------------------------------------------------------
# day0 configs
# ----------------------------------------------------------------------------
def cfg_inet(ax):
    pubs = {s: PUB[s]["rtr"] for s in ("HQ", "BR1", "BR2")}
    return f"""hostname INET
!
ip domain name ccnp.local
ip cef
no ip http server
no ip http secure-server
!
enable secret CCNP
username SUZUKI privilege 15 secret CCNP
!
ip access-list extended JUDGE-SRV
 permit ip host {pubs['HQ']} host {SRV_IP}
 permit ip host {pubs['BR1']} host {SRV_IP}
 permit ip host {pubs['BR2']} host {SRV_IP}
 deny   ip 10.0.0.0 0.255.255.255 any
 deny   ip 172.16.0.0 0.15.255.255 any
 deny   ip 192.168.0.0 0.0.255.255 any
 permit ip any any
!
ip access-list extended CATCH-LEAK
 deny   ip 10.0.0.0 0.255.255.255 any
 deny   ip 172.16.0.0 0.15.255.255 any
 deny   ip 192.168.0.0 0.0.255.255 any
 deny   ip any 10.0.0.0 0.255.255.255
 deny   ip any 172.16.0.0 0.15.255.255
 deny   ip any 192.168.0.0 0.0.255.255
 permit ip any any
!
interface Ethernet0/0
 description === to HQ (public) ===
 ip address {PUB['HQ']['inet']} 255.255.255.252
 ip access-group CATCH-LEAK in
 no shutdown
!
interface Ethernet0/1
 description === to BR1 (public) ===
 ip address {PUB['BR1']['inet']} 255.255.255.252
 ip access-group CATCH-LEAK in
 no shutdown
!
interface Ethernet0/2
 description === to BR2 (public) ===
 ip address {PUB['BR2']['inet']} 255.255.255.252
 ip access-group CATCH-LEAK in
 no shutdown
!
interface Ethernet0/3
 description === SRV segment (public) ===
 ip address {SRV_GW} 255.255.255.0
 ip access-group JUDGE-SRV out
 no shutdown
!
line con 0
 exec-timeout 0 0
 logging synchronous
 privilege level 15
"""


def cfg_edge(site, ax):
    lan = ax["lan"][site]
    return f"""hostname {site}
!
ip domain name ccnp.local
ip cef
no ip http server
no ip http secure-server
!
enable secret CCNP
username SUZUKI privilege 15 secret CCNP
!
interface GigabitEthernet0/0
 description === WAN to INET (GW {PUB[site]['inet']}) ===
 ip address {PUB[site]['rtr']} 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/1
 description === {site} LAN ===
 ip address {lan}.1 255.255.255.0
 no shutdown
!
line con 0
 exec-timeout 0 0
 logging synchronous
 privilege level 15
"""


def cfg_host(name, ip, gw):
    return f"""#!/bin/sh
ip addr add {ip}/24 dev eth0
ip link set eth0 up
ip route add default via {gw}
mkdir -p /www
echo "{name}-OK" > /www/index.html
dd if=/dev/zero of=/www/big.bin bs=1024 count={BIGBIN // 1024} 2>/dev/null
httpd -p 80 -h /www
"""


# ----------------------------------------------------------------------------
# lab.yaml
# ----------------------------------------------------------------------------
def build_lab_yaml(pid, title, ax):
    def node(nid, ndef, x, y, ifs, cfg, image=None, tags=None):
        d = {"id": nid, "label": nid, "node_definition": ndef, "x": x, "y": y,
             "interfaces": ifs, "configuration": cfg}
        if image:
            d["image_definition"] = image
        if tags:
            d["tags"] = tags
        return d

    def eth(nid, n, pfx):
        return [{"id": f"{nid}-i{k}", "label": f"{pfx}{k // 4}/{k % 4}",
                 "type": "physical", "slot": k} for k in range(n)]

    def one(nid):
        return [{"id": f"{nid}-i0", "slot": 0, "label": "eth0", "type": "physical"}]

    lanip = {s: f"{ax['lan'][s]}.101" for s in ("HQ", "BR1", "BR2")}
    langw = {s: f"{ax['lan'][s]}.1" for s in ("HQ", "BR1", "BR2")}
    nodes = [
        node("INET", "iol-xe", 0, -160, eth("INET", 4, "Ethernet"),
             cfg_inet(ax), image="iol-xe-17-15-01", tags=["routers"]),
        node("HQ", "iosv", -280, 40, eth("HQ", 2, "GigabitEthernet"),
             cfg_edge("HQ", ax), image="iosv-159-3-m9", tags=["routers"]),
        node("BR1", "iosv", 0, 120, eth("BR1", 2, "GigabitEthernet"),
             cfg_edge("BR1", ax), image="iosv-159-3-m9", tags=["routers"]),
        node("BR2", "iosv", 280, 40, eth("BR2", 2, "GigabitEthernet"),
             cfg_edge("BR2", ax), image="iosv-159-3-m9", tags=["routers"]),
        node("SRV", "alpine", 0, -320, one("SRV"), cfg_host("SRV", SRV_IP, SRV_GW)),
        node("H-HQ", "alpine", -280, 200, one("H-HQ"),
             cfg_host("H-HQ", lanip["HQ"], langw["HQ"])),
        node("H-B1", "alpine", 0, 280, one("H-B1"),
             cfg_host("H-B1", lanip["BR1"], langw["BR1"])),
        node("H-B2", "alpine", 280, 200, one("H-B2"),
             cfg_host("H-B2", lanip["BR2"], langw["BR2"])),
    ]
    links = [
        {"id": "l0", "n1": "INET", "i1": "INET-i0", "n2": "HQ", "i2": "HQ-i0"},
        {"id": "l1", "n1": "INET", "i1": "INET-i1", "n2": "BR1", "i2": "BR1-i0"},
        {"id": "l2", "n1": "INET", "i1": "INET-i2", "n2": "BR2", "i2": "BR2-i0"},
        {"id": "l3", "n1": "INET", "i1": "INET-i3", "n2": "SRV", "i2": "SRV-i0"},
        {"id": "l4", "n1": "HQ", "i1": "HQ-i1", "n2": "H-HQ", "i2": "H-HQ-i0"},
        {"id": "l5", "n1": "BR1", "i1": "BR1-i1", "n2": "H-B1", "i2": "H-B1-i0"},
        {"id": "l6", "n1": "BR2", "i1": "BR2-i1", "n2": "H-B2", "i2": "H-B2-i0"},
    ]
    return {"lab": {"title": title,
                    "description": "",
                    "notes": f"自動生成 (gen_s2svpn.py) {pid}。運用は topologies/s2svpn_ops.py。",
                    "version": "0.3.0"},
            "nodes": nodes, "links": links}


# ----------------------------------------------------------------------------
# 模範解答 (svti = ハブ&スポーク sVTI / cmap = crypto map ※全支店 split の seed のみ)
# ----------------------------------------------------------------------------
def _crypto_base(peers):
    lines = ["crypto isakmp policy 10", " encryption aes 256", " hash sha256",
             " authentication pre-share", " group 14"]
    lines += [f"crypto isakmp key {PSK} address {p}" for p in peers]
    lines += ["crypto ipsec transform-set TS-AES esp-aes 256 esp-sha256-hmac",
              " mode tunnel"]
    return lines


def _b2b_acl(name, own, other, policy):
    """HQ の Tunnel in / (cmap では BR の LAN in) に置く支店間ポリシー ACL。
    own/other = 24bit プレフィックス文字列("10.34.21" 等)。"""
    a = [f"ip access-list extended {name}"]
    o1, o2 = f"{own}.0 0.0.0.255", f"{other}.0 0.0.0.255"
    if policy == "icmp_only":
        a.append(f" permit icmp {o1} {o2}")
    elif policy == "http_only":
        a.append(f" permit tcp {o1} {o2} eq www")
        a.append(f" permit tcp {o1} eq www {o2}")
    if policy != "allow_all":
        a.append(f" deny   ip {o1} {o2}")
    a.append(" permit ip any any")
    return a


def solve_svti(ax):
    lan, tun, b2b = ax["lan"], ax["tun"], ax["b2b"]
    hq, b1, b2 = lan["HQ"], lan["BR1"], lan["BR2"]
    cfg = {}

    # --- HQ (hub) ---
    c = _crypto_base([PUB["BR1"]["rtr"], PUB["BR2"]["rtr"]])
    c += ["crypto ipsec profile IPSEC-VTI", " set transform-set TS-AES"]
    for i, br in enumerate(("BR1", "BR2"), start=1):
        c += [f"interface Tunnel{i}",
              f" description === to {br} ===",
              f" ip address {OVL[br][0]} 255.255.255.252",
              " ip mtu 1400", " ip tcp adjust-mss 1360",
              " tunnel source GigabitEthernet0/0",
              f" tunnel destination {PUB[br]['rtr']}",
              " tunnel mode ipsec ipv4",
              " tunnel protection ipsec profile IPSEC-VTI"]
        if tun[br] == "full":
            c += [f"interface Tunnel{i}", " ip nat inside"]
    c += [f"ip route 0.0.0.0 0.0.0.0 {PUB['HQ']['inet']}",
          f"ip route {b1}.0 255.255.255.0 Tunnel1",
          f"ip route {b2}.0 255.255.255.0 Tunnel2"]
    # NAPT(自LAN + full支店LAN)
    c += ["ip access-list extended NAT-EXT",
          f" deny   ip {hq}.0 0.0.0.255 {b1}.0 0.0.0.255",
          f" deny   ip {hq}.0 0.0.0.255 {b2}.0 0.0.0.255",
          f" permit ip {hq}.0 0.0.0.255 any"]
    for br, b in (("BR1", b1), ("BR2", b2)):
        if tun[br] == "full":
            c += [f" permit ip {b}.0 0.0.0.255 any"]
    c += ["ip nat inside source list NAT-EXT interface GigabitEthernet0/0 overload",
          "interface GigabitEthernet0/0", " ip nat outside",
          "interface GigabitEthernet0/1", " ip nat inside"]
    if ax["pubsrv"]:
        c += [f"ip nat inside source static tcp {hq}.101 80 "
              "interface GigabitEthernet0/0 8080"]
    # 支店間ポリシー(ハブで一元管理・暗号化ドメイン内で破棄=INETへ漏らさない)
    if b2b != "allow_all":
        c += _b2b_acl("B2B-T1-IN", b1, b2, b2b)
        c += _b2b_acl("B2B-T2-IN", b2, b1, b2b)
        c += ["interface Tunnel1", " ip access-group B2B-T1-IN in",
              "interface Tunnel2", " ip access-group B2B-T2-IN in"]
    cfg["HQ"] = c

    # --- 支店 ---
    for br, other in (("BR1", "BR2"), ("BR2", "BR1")):
        own, oth = lan[br], lan[other]
        c = _crypto_base([PUB["HQ"]["rtr"]])
        c += ["crypto ipsec profile IPSEC-VTI", " set transform-set TS-AES",
              "interface Tunnel0",
              f" ip address {OVL[br][1]} 255.255.255.252",
              " ip mtu 1400", " ip tcp adjust-mss 1360",
              " tunnel source GigabitEthernet0/0",
              f" tunnel destination {PUB['HQ']['rtr']}",
              " tunnel mode ipsec ipv4",
              " tunnel protection ipsec profile IPSEC-VTI"]
        if tun[br] == "split":
            c += [f"ip route 0.0.0.0 0.0.0.0 {PUB[br]['inet']}",
                  f"ip route {hq}.0 255.255.255.0 Tunnel0",
                  f"ip route {oth}.0 255.255.255.0 Tunnel0",
                  "ip access-list extended NAT-EXT",
                  f" deny   ip {own}.0 0.0.0.255 {hq}.0 0.0.0.255",
                  f" deny   ip {own}.0 0.0.0.255 {oth}.0 0.0.0.255",
                  f" permit ip {own}.0 0.0.0.255 any",
                  "ip nat inside source list NAT-EXT "
                  "interface GigabitEthernet0/0 overload",
                  "interface GigabitEthernet0/0", " ip nat outside",
                  "interface GigabitEthernet0/1", " ip nat inside"]
        else:  # full: default をトンネルへ・ピア/32 だけ ISP 経由・ローカル NAT なし
            c += [f"ip route {PUB['HQ']['rtr']} 255.255.255.255 {PUB[br]['inet']}",
                  "ip route 0.0.0.0 0.0.0.0 Tunnel0"]
        cfg[br] = c
    return cfg


def solve_cmap(ax):
    """crypto map 版(別解クロス検証用)。全支店 split の seed のみ生成。
    支店間ポリシーは各支店 LAN-in ACL で施行(平文流出をエッジで止める)。"""
    if "full" in ax["tun"].values():
        return None
    lan, b2b = ax["lan"], ax["b2b"]
    hq, b1, b2 = lan["HQ"], lan["BR1"], lan["BR2"]

    def cross(src, dst):
        """b2b ポリシーに応じた crypto ACL 追加行(src→dst 方向に流れる支店間フロー)。"""
        s, d = f"{src}.0 0.0.0.255", f"{dst}.0 0.0.0.255"
        if b2b == "allow_all":
            return [f" permit ip {s} {d}"]
        if b2b == "icmp_only":
            return [f" permit icmp {s} {d}"]
        if b2b == "http_only":
            return [f" permit tcp {s} {d} eq www", f" permit tcp {s} eq www {d}"]
        return []  # deny_all

    cfg = {}
    # --- HQ: 2 エントリの crypto map。支店間フローはハブで折り返す(cross を双方に併記) ---
    c = _crypto_base([PUB["BR1"]["rtr"], PUB["BR2"]["rtr"]])
    c += ["ip access-list extended CR-B1",
          f" permit ip {hq}.0 0.0.0.255 {b1}.0 0.0.0.255"] + cross(b2, b1) + [
          "ip access-list extended CR-B2",
          f" permit ip {hq}.0 0.0.0.255 {b2}.0 0.0.0.255"] + cross(b1, b2) + [
          "crypto map CMAP 10 ipsec-isakmp",
          f" set peer {PUB['BR1']['rtr']}", " set transform-set TS-AES",
          " match address CR-B1",
          "crypto map CMAP 20 ipsec-isakmp",
          f" set peer {PUB['BR2']['rtr']}", " set transform-set TS-AES",
          " match address CR-B2",
          f"ip route 0.0.0.0 0.0.0.0 {PUB['HQ']['inet']}",
          "ip access-list extended NAT-EXT",
          f" deny   ip {hq}.0 0.0.0.255 {b1}.0 0.0.0.255",
          f" deny   ip {hq}.0 0.0.0.255 {b2}.0 0.0.0.255",
          f" permit ip {hq}.0 0.0.0.255 any",
          "ip nat inside source list NAT-EXT interface GigabitEthernet0/0 overload",
          "interface GigabitEthernet0/0", " ip nat outside", " crypto map CMAP",
          "interface GigabitEthernet0/1", " ip nat inside", " ip tcp adjust-mss 1360"]
    if ax["pubsrv"]:
        # ★crypto map では interface 形の静的PATが VPN 宛の :80 応答まで先取りして
        #   crypto ACL 不一致→平文漏れになる(実機 8808 で 84 点に降格を実証)。
        #   route-map 条件付き静的NATで VPN 宛を変換除外する(inbound :8080 変換は維持)。
        c += ["ip access-list extended NAT-STATIC-RM",
              f" deny   ip host {hq}.101 {b1}.0 0.0.0.255",
              f" deny   ip host {hq}.101 {b2}.0 0.0.0.255",
              f" permit ip host {hq}.101 any",
              "route-map RM-STATIC permit 10",
              " match ip address NAT-STATIC-RM",
              f"ip nat inside source static tcp {hq}.101 80 "
              f"{PUB['HQ']['rtr']} 8080 route-map RM-STATIC extendable"]
    cfg["HQ"] = c

    for br, own, oth in (("BR1", b1, b2), ("BR2", b2, b1)):
        c = _crypto_base([PUB["HQ"]["rtr"]])
        c += ["ip access-list extended CR-HQ",
              f" permit ip {own}.0 0.0.0.255 {hq}.0 0.0.0.255"] + cross(own, oth) + [
              "crypto map CMAP 10 ipsec-isakmp",
              f" set peer {PUB['HQ']['rtr']}", " set transform-set TS-AES",
              " match address CR-HQ",
              f"ip route 0.0.0.0 0.0.0.0 {PUB[br]['inet']}",
              "ip access-list extended NAT-EXT",
              f" deny   ip {own}.0 0.0.0.255 {hq}.0 0.0.0.255",
              f" deny   ip {own}.0 0.0.0.255 {oth}.0 0.0.0.255",
              f" permit ip {own}.0 0.0.0.255 any",
              "ip nat inside source list NAT-EXT "
              "interface GigabitEthernet0/0 overload",
              "interface GigabitEthernet0/0", " ip nat outside", " crypto map CMAP",
              "interface GigabitEthernet0/1", " ip nat inside",
              " ip tcp adjust-mss 1360"]
        # 遮断分の平文流出をエッジ(LAN in)で止める
        if b2b != "allow_all":
            c += _b2b_acl("B2B-LAN-IN", own, oth, b2b)
            c += ["interface GigabitEthernet0/1", " ip access-group B2B-LAN-IN in"]
        cfg[br] = c
    return cfg


# ----------------------------------------------------------------------------
# task.md (要件書)
# ----------------------------------------------------------------------------
def build_task(pid, ax):
    lan, tun, b2b = ax["lan"], ax["tun"], ax["b2b"]
    tun_txt = []
    for br, jp in (("BR1", "支店1"), ("BR2", "支店2")):
        if tun[br] == "full":
            tun_txt.append(
                f"- **{jp}({br})**: セキュリティ監査要件により、インターネット向け通信は"
                f"**必ず本社を経由**させ、本社の回線から出ること。"
                f"{jp}の回線からインターネットへ直接出てはならない。")
        else:
            tun_txt.append(
                f"- **{jp}({br})**: インターネット向け通信は**自拠点の回線から直接**出る"
                f"こと(ローカルブレイクアウト)。本社回線へ集約してはならない。")
    pubsrv_req = ""
    if ax["pubsrv"]:
        pubsrv_req = f"""
### R5. 本社Webサーバの公開
本社の社内Webサーバ(H-HQ, {lan['HQ']}.101, TCP/80)を、インターネット側から
**本社の公開IP({PUB['HQ']['rtr']}) の TCP/8080** でアクセスできるように公開すること。
"""
    return f"""# {pid}: 拠点間VPN導入プロジェクト — 設計・構築依頼書

あなたはネットワークインテグレータのエンジニアである。顧客(3拠点の企業)から
以下の依頼書を受領した。**要件を満たす方式の選定・設計・実装はすべて任されている。**

## 1. 現状構成

各拠点はそれぞれ ISP 回線(固定グローバルIP)でインターネットに接続できる契約だが、
ルータはアドレス設定のみの初期状態である。**INET(ISP網)・SRV(インターネット上の
Webサーバ)・各拠点のPC(H-*)は顧客管理外のため設定変更禁止**(採点装置を兼ねる)。

| 拠点 | ルータ | WAN(公開IP) | ISP GW | LAN | PC |
|------|--------|-------------|--------|-----|----|
| 本社 | HQ (IOSv) | {PUB['HQ']['rtr']}/30 | {PUB['HQ']['inet']} | {lan['HQ']}.0/24 (Gi0/1 = .1) | H-HQ = {lan['HQ']}.101 |
| 支店1 | BR1 (IOSv) | {PUB['BR1']['rtr']}/30 | {PUB['BR1']['inet']} | {lan['BR1']}.0/24 (Gi0/1 = .1) | H-B1 = {lan['BR1']}.101 |
| 支店2 | BR2 (IOSv) | {PUB['BR2']['rtr']}/30 | {PUB['BR2']['inet']} | {lan['BR2']}.0/24 (Gi0/1 = .1) | H-B2 = {lan['BR2']}.101 |

インターネット上の検証用Webサーバ: **SRV = http://{SRV_IP}/** (トップページと /big.bin)。
各PCも TCP/80 で自ホスト名のページを返す(疎通確認に利用してよい)。

## 2. 要件

### R1. インターネット接続 (NAPT)
インターネットへ出る通信は、出口となる拠点の**公開IPへの NAPT(PAT)** を用いること。
社内(プライベート)アドレスのパケットを ISP 網へ**平文のまま流出させないこと**
(遮断ポリシーで破棄するトラフィックを含む)。

### R2. 拠点間VPN
本社と各支店の間を **IPsec で暗号化された VPN** で接続し、本社LAN⇔各支店LANの
相互通信を可能にすること。方式(トポロジ・プロトコル・トンネル種別)は**提案者の判断**
とするが、暗号化は AES 系を用いること。

### R3. 支店のインターネットアクセス方針
{chr(10).join(tun_txt)}

### R4. 支店間の通信ポリシー
{B2B_LABEL[b2b]}こと。
{pubsrv_req}
### R{6 if ax['pubsrv'] else 5}. アプリケーション伝送品質
すべての許可された経路(拠点間・インターネット)で、Webの**大きなファイル転送
(SRV および各PCの /big.bin, 200KB)が安定して完了**すること。

### R{7 if ax['pubsrv'] else 6}. 設計レポート
作業フォルダに `report.yaml` を作成し、以下を記載すること(採点対象):

```yaml
vpn_technology: "<採用した方式: 例 DMVPN / sVTI full-mesh / sVTI hub-and-spoke / crypto map>"
topology: "<トンネル構成の概要>"
reason: "<その方式を選定した理由。将来の拠点追加の観点を含めること>"
```

## 3. 制約・注意

- INET / SRV / H-HQ / H-B1 / H-B2 は**変更禁止**。HQ/BR1/BR2 のみ設定してよい。
- 各ルータの既存インタフェース IP は変更しないこと。
- 採点は疎通・カウンタ等の**効果ベース**で行う(方式には依存しない)。
- 収束後に採点すること。採点は `s2svpn_ops.py grade` が行う。

*(自動生成: gen_s2svpn.py seed={pid.split('-')[-1]})*
"""


# ----------------------------------------------------------------------------
# Day2 運用シナリオパック (BL-064): チケット3本 (支店追加/full→split移行/サブネット重複)
# ----------------------------------------------------------------------------
def pick_axes_day2(seed):
    """base 軸に Day2 用の強制と抽選を加える。"""
    ax = pick_axes(seed)
    rng = random.Random(seed * 7 + 3)
    ax["pubsrv"] = False                      # D2 は公開サーバ要素を外して運用課題に集中
    if "full" not in ax["tun"].values():      # チケット#2(移行)には full 支店が必須
        ax["tun"][rng.choice(["BR1", "BR2"])] = "full"
    migrate = rng.choice([b for b in ("BR1", "BR2") if ax["tun"][b] == "full"])

    # BR3(新支店): 方式抽選・LAN は base 3拠点と衝突しない第3オクテット
    hq = ax["lan"]["HQ"]
    if hq.startswith("10.") or hq.startswith("172."):
        base = hq.rsplit(".", 1)[0]
        br3_lan = f"{base}.23"
    else:
        used = {int(v.split(".")[2]) for v in ax["lan"].values()}
        oct3 = next(o for o in rng.sample(range(10, 250), 20) if o not in used)
        br3_lan = f"192.168.{oct3}"
    br3_policy = rng.choice(["full", "split"])
    # 仕様書の食い違い(2〜3項目)。truth は実機側。
    wrong = rng.sample(["psk", "lan", "wan_ip"], rng.choice([2, 3]))
    o3 = int(br3_lan.split(".")[2])
    spec_lan = br3_lan.rsplit(".", 1)[0] + f".{o3 + 10 if o3 + 10 < 250 else o3 - 10}"
    disc = {
        "items": sorted(wrong),
        "spec": {
            "psk": "Ss2025#S2sVpn" if "psk" in wrong else PSK,
            "lan": spec_lan if "lan" in wrong else br3_lan,
            "wan_ip": "203.0.113.22" if "wan_ip" in wrong else PUB["BR3"]["rtr"],
        },
        "truth": {"psk": PSK, "lan": br3_lan, "wan_ip": PUB["BR3"]["rtr"]},
    }

    # BR4(吸収拠点): 既存支店の LAN と完全重複。エイリアスは全 LAN 方式と衝突しない 172.28.x
    overlap_of = rng.choice(["BR1", "BR2"])
    alias = f"172.28.{rng.randint(1, 254)}"
    ax["day2"] = {
        "migrate_target": migrate,
        "br3": {"policy": br3_policy, "lan": br3_lan, "disc": disc},
        "br4": {"overlap_of": overlap_of, "lan": ax["lan"][overlap_of],
                "alias": alias, "host_oct": "102"},
    }
    return ax


def cfg_inet_day2(ax):
    """D2 版 INET: 6 IF(BR3/BR4 追加)・JUDGE は 5 拠点の公開IP行。"""
    lines = ["hostname INET", "!", "ip domain name ccnp.local", "ip cef",
             "no ip http server", "no ip http secure-server", "!",
             "enable secret CCNP", "username SUZUKI privilege 15 secret CCNP", "!",
             "ip access-list extended JUDGE-SRV"]
    for s in ("HQ", "BR1", "BR2", "BR3", "BR4"):
        lines.append(f" permit ip host {PUB[s]['rtr']} host {SRV_IP}")
    lines += [" deny   ip 10.0.0.0 0.255.255.255 any",
              " deny   ip 172.16.0.0 0.15.255.255 any",
              " deny   ip 192.168.0.0 0.0.255.255 any",
              " permit ip any any", "!",
              "ip access-list extended CATCH-LEAK",
              " deny   ip 10.0.0.0 0.255.255.255 any",
              " deny   ip 172.16.0.0 0.15.255.255 any",
              " deny   ip 192.168.0.0 0.0.255.255 any",
              " deny   ip any 10.0.0.0 0.255.255.255",
              " deny   ip any 172.16.0.0 0.15.255.255",
              " deny   ip any 192.168.0.0 0.0.255.255",
              " permit ip any any", "!"]
    wan = [("Ethernet0/0", "HQ"), ("Ethernet0/1", "BR1"), ("Ethernet0/2", "BR2"),
           ("Ethernet1/0", "BR3"), ("Ethernet1/1", "BR4")]
    for ifname, site in wan:
        lines += [f"interface {ifname}",
                  f" description === to {site} (public) ===",
                  f" ip address {PUB[site]['inet']} 255.255.255.252",
                  " ip access-group CATCH-LEAK in", " no shutdown", "!"]
    lines += ["interface Ethernet0/3",
              " description === SRV segment (public) ===",
              f" ip address {SRV_GW} 255.255.255.0",
              " ip access-group JUDGE-SRV out", " no shutdown", "!",
              "line con 0", " exec-timeout 0 0", " logging synchronous",
              " privilege level 15"]
    return "\n".join(lines) + "\n"


def cfg_br3_bare():
    """BR3: 配線済み・未設定(ホスト名とコンソールのみ)。"""
    return """hostname BR3
!
ip domain name ccnp.local
ip cef
no ip http server
no ip http secure-server
!
enable secret CCNP
username SUZUKI privilege 15 secret CCNP
!
line con 0
 exec-timeout 0 0
 logging synchronous
 privilege level 15
"""


def cfg_br4_naive(ax):
    """BR4: 吸収拠点の担当が見様見真似で入れた素朴設定(day0 焼込み)。
    トンネルは張れるが、LAN が既存支店と完全重複しており通信不成立。NAT なし。"""
    d2 = ax["day2"]["br4"]
    lan, hq_lan = d2["lan"], ax["lan"]["HQ"]
    return f"""hostname BR4
!
ip domain name ccnp.local
ip cef
no ip http server
no ip http secure-server
!
enable secret CCNP
username SUZUKI privilege 15 secret CCNP
!
interface GigabitEthernet0/0
 description === WAN to INET (GW {PUB['BR4']['inet']}) ===
 ip address {PUB['BR4']['rtr']} 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/1
 description === BR4 LAN (absorbed site) ===
 ip address {lan}.1 255.255.255.0
 no shutdown
!
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
crypto isakmp key {PSK} address {PUB['HQ']['rtr']}
crypto ipsec transform-set TS-AES esp-aes 256 esp-sha256-hmac
 mode tunnel
crypto ipsec profile IPSEC-VTI
 set transform-set TS-AES
interface Tunnel0
 ip address {OVL['BR4'][1]} 255.255.255.252
 tunnel source GigabitEthernet0/0
 tunnel destination {PUB['HQ']['rtr']}
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-VTI
!
ip route 0.0.0.0 0.0.0.0 {PUB['BR4']['inet']}
ip route {hq_lan}.0 255.255.255.0 Tunnel0
!
line con 0
 exec-timeout 0 0
 logging synchronous
 privilege level 15
"""


def build_lab_yaml_day2(pid, title, ax):
    """base 8台 + BR3/H-B3 + BR4/H-B4 の 12台。INET は D2 版(6IF)。"""
    lab = build_lab_yaml(pid, title, ax)
    lab["lab"]["notes"] = f"自動生成 (gen_s2svpn.py --day2) {pid}。運用は topologies/s2svpn_ops.py。"
    d2 = ax["day2"]
    for n in lab["nodes"]:
        if n["id"] == "INET":
            n["configuration"] = cfg_inet_day2(ax)
            n["interfaces"] = [
                {"id": f"INET-i{k}", "label": f"Ethernet{k // 4}/{k % 4}",
                 "type": "physical", "slot": k} for k in range(6)]
    def one(nid):
        return [{"id": f"{nid}-i0", "slot": 0, "label": "eth0", "type": "physical"}]
    def eth2(nid):
        return [{"id": f"{nid}-i{k}", "label": f"GigabitEthernet0/{k}",
                 "type": "physical", "slot": k} for k in range(2)]
    br3_lan, br4 = d2["br3"]["lan"], d2["br4"]
    lab["nodes"] += [
        {"id": "BR3", "label": "BR3", "node_definition": "iosv",
         "image_definition": "iosv-159-3-m9", "x": -480, "y": 40,
         "tags": ["routers"], "interfaces": eth2("BR3"),
         "configuration": cfg_br3_bare()},
        {"id": "H-B3", "label": "H-B3", "node_definition": "alpine",
         "x": -480, "y": 200, "interfaces": one("H-B3"),
         "configuration": cfg_host("H-B3", f"{br3_lan}.101", f"{br3_lan}.1")},
        {"id": "BR4", "label": "BR4", "node_definition": "iosv",
         "image_definition": "iosv-159-3-m9", "x": 480, "y": 40,
         "tags": ["routers"], "interfaces": eth2("BR4"),
         "configuration": cfg_br4_naive(ax)},
        {"id": "H-B4", "label": "H-B4", "node_definition": "alpine",
         "x": 480, "y": 200, "interfaces": one("H-B4"),
         "configuration": cfg_host("H-B4", f"{br4['lan']}.{br4['host_oct']}",
                                   f"{br4['lan']}.1")},
    ]
    lab["links"] += [
        {"id": "l7", "n1": "INET", "i1": "INET-i4", "n2": "BR3", "i2": "BR3-i0"},
        {"id": "l8", "n1": "INET", "i1": "INET-i5", "n2": "BR4", "i2": "BR4-i0"},
        {"id": "l9", "n1": "BR3", "i1": "BR3-i1", "n2": "H-B3", "i2": "H-B3-i0"},
        {"id": "l10", "n1": "BR4", "i1": "BR4-i1", "n2": "H-B4", "i2": "H-B4-i0"},
    ]
    return lab


def day2_init(ax):
    """day2init: 吸収拠点担当が HQ 側に入れた「トンネルだけ」の設定
    (base solve 後に投入。BR4 宛の経路は無し=戻りは既存支店へ吸われる)。"""
    return {"HQ": [
        f"crypto isakmp key {PSK} address {PUB['BR4']['rtr']}",
        "interface Tunnel4",
        f" ip address {OVL['BR4'][0]} 255.255.255.252",
        " tunnel source GigabitEthernet0/0",
        f" tunnel destination {PUB['BR4']['rtr']}",
        " tunnel mode ipsec ipv4",
        " tunnel protection ipsec profile IPSEC-VTI",
    ]}


def solve_t1(ax):
    """チケット#1: BR3 追加(実機=truth に従う)。"""
    d = ax["day2"]["br3"]
    lan, hq_lan, policy = d["lan"], ax["lan"]["HQ"], d["policy"]
    br3 = [
        "interface GigabitEthernet0/0",
        f" ip address {PUB['BR3']['rtr']} 255.255.255.252", " no shutdown",
        "interface GigabitEthernet0/1",
        f" ip address {lan}.1 255.255.255.0", " no shutdown",
    ] + _crypto_base([PUB["HQ"]["rtr"]]) + [
        "crypto ipsec profile IPSEC-VTI", " set transform-set TS-AES",
        "interface Tunnel0",
        f" ip address {OVL['BR3'][1]} 255.255.255.252",
        " ip mtu 1400", " ip tcp adjust-mss 1360",
        " tunnel source GigabitEthernet0/0",
        f" tunnel destination {PUB['HQ']['rtr']}",
        " tunnel mode ipsec ipv4",
        " tunnel protection ipsec profile IPSEC-VTI"]
    if policy == "split":
        br3 += [f"ip route 0.0.0.0 0.0.0.0 {PUB['BR3']['inet']}",
                f"ip route {hq_lan}.0 255.255.255.0 Tunnel0",
                "ip access-list extended NAT-DYN",
                f" deny   ip {lan}.0 0.0.0.255 {hq_lan}.0 0.0.0.255",
                f" permit ip {lan}.0 0.0.0.255 any",
                "ip nat inside source list NAT-DYN interface GigabitEthernet0/0 overload",
                "interface GigabitEthernet0/0", " ip nat outside",
                "interface GigabitEthernet0/1", " ip nat inside"]
    else:
        br3 += [f"ip route {PUB['HQ']['rtr']} 255.255.255.255 {PUB['BR3']['inet']}",
                "ip route 0.0.0.0 0.0.0.0 Tunnel0"]
    hq = [f"crypto isakmp key {PSK} address {PUB['BR3']['rtr']}",
          "interface Tunnel3",
          f" ip address {OVL['BR3'][0]} 255.255.255.252",
          " ip mtu 1400", " ip tcp adjust-mss 1360",
          " tunnel source GigabitEthernet0/0",
          f" tunnel destination {PUB['BR3']['rtr']}",
          " tunnel mode ipsec ipv4",
          " tunnel protection ipsec profile IPSEC-VTI",
          f"ip route {lan}.0 255.255.255.0 Tunnel3"]
    if policy == "full":
        hq += ["interface Tunnel3", " ip nat inside",
               "ip access-list extended NAT-EXT",
               f" permit ip {lan}.0 0.0.0.255 any"]
    return {"BR3": br3, "HQ": hq}


def solve_t2(ax):
    """チケット#2: full 支店をローカルブレイクアウト(split)へ移行。"""
    br = ax["day2"]["migrate_target"]
    other = "BR2" if br == "BR1" else "BR1"
    own, hq_lan, oth = ax["lan"][br], ax["lan"]["HQ"], ax["lan"][other]
    cfg = {br: [
        "no ip route 0.0.0.0 0.0.0.0 Tunnel0",
        f"ip route 0.0.0.0 0.0.0.0 {PUB[br]['inet']}",
        f"ip route {hq_lan}.0 255.255.255.0 Tunnel0",
        f"ip route {oth}.0 255.255.255.0 Tunnel0",
        "ip access-list extended NAT-DYN",
        f" deny   ip {own}.0 0.0.0.255 {hq_lan}.0 0.0.0.255",
        f" deny   ip {own}.0 0.0.0.255 {oth}.0 0.0.0.255",
        f" permit ip {own}.0 0.0.0.255 any",
        "ip nat inside source list NAT-DYN interface GigabitEthernet0/0 overload",
        "interface GigabitEthernet0/0", " ip nat outside",
        "interface GigabitEthernet0/1", " ip nat inside",
    ]}
    # HQ 側の残骸掃除(集約 NAT の対象から外す・ヘアピン用 nat inside を撤去)
    tun_no = "1" if br == "BR1" else "2"
    cfg["HQ"] = [f"interface Tunnel{tun_no}", " no ip nat inside",
                 "ip access-list extended NAT-EXT",
                 f" no permit ip {own}.0 0.0.0.255 any"]
    return cfg


def solve_t3(ax):
    """チケット#3: 吸収拠点(BR4)のサブネット重複を NAT overlapping で解消。
    ★PoC 知見: static network+route-map は非対応 → ホスト単位 static+route-map。
    Tunnel を nat outside にした時点で動的 PAT の VPN 宛 deny が必須(sVTI でも)。"""
    d = ax["day2"]["br4"]
    lan, alias, hq_lan = d["lan"], d["alias"], ax["lan"]["HQ"]
    h = d["host_oct"]
    br4 = ["interface Tunnel0", " ip mtu 1400", " ip tcp adjust-mss 1360",
           " ip nat outside",
           "ip access-list extended OVL-RM",
           f" permit ip {lan}.0 0.0.0.255 {hq_lan}.0 0.0.0.255",
           "route-map RM-OVL permit 10",
           " match ip address OVL-RM",
           f"ip nat inside source static {lan}.{h} {alias}.{h} route-map RM-OVL",
           "ip access-list extended NAT-DYN",
           f" deny   ip {lan}.0 0.0.0.255 {hq_lan}.0 0.0.0.255",
           f" permit ip {lan}.0 0.0.0.255 any",
           "ip nat inside source list NAT-DYN interface GigabitEthernet0/0 overload",
           "interface GigabitEthernet0/0", " ip nat outside",
           "interface GigabitEthernet0/1", " ip nat inside"]
    hq = [f"ip route {alias}.0 255.255.255.0 Tunnel4"]
    return {"BR4": br4, "HQ": hq}


def build_spec_br3(ax):
    """チケット#1 添付の開設仕様書(seed で食い違いを注入済み)。"""
    d = ax["day2"]["br3"]
    spec = d["disc"]["spec"]
    policy_txt = ("インターネット向け通信は本社経由で集約(本社の回線から出る)"
                  if d["policy"] == "full" else
                  "インターネット向け通信は自拠点回線から直接(ローカルブレイクアウト)")
    return f"""# 新支店(BR3)開設仕様書 — 設備管理部発行 (改訂2版)

| 項目 | 値 |
|------|----|
| ルータ | BR3 (IOSv・ラック搭載/結線済み) |
| WAN 回線 | {spec['wan_ip']}/30 (ISP GW は同 /30 の対向) |
| LAN | {spec['lan']}.0/24 (Gi0/1 = .1) |
| 現地PC | 資産管理部管理・変更不可 (.101/24, GW .1) |
| VPN 方式 | 既存構成(本社ハブ)に準拠・AES 系 |
| 事前共有鍵 | {spec['psk']} |
| インターネット方針 | {policy_txt} |

- 注意: 本仕様書は開設準備期の資料である。現地工事後の変更が反映されていない
  可能性があるため、**実機・現地実態と食い違う場合は実機を正**とし、
  完了報告(report_d2.yaml)に食い違い内容を記載すること。
"""


def build_task_day2(pid, ax):
    d2 = ax["day2"]
    mig = d2["migrate_target"]
    mig_jp = "支店1" if mig == "BR1" else "支店2"
    ov = d2["br4"]["overlap_of"]
    return f"""# {pid}: 拠点間VPN 運用週間 — 障害・作業チケット3本

あなたは {pid.replace('-D2', '')} で構築した 3 拠点 VPN 網の運用を引き継いだ。
前任者の構成資料: 本社(HQ)ハブの sVTI hub-and-spoke・支店間ポリシーはハブで制御。
現在は**正常稼働中**である。以下のチケットを**番号順に**処理せよ。

> 共通制約: INET / SRV / H-* (全拠点PC) は変更禁止。採点は各チケット完了時に
> `s2svpn_ops.py grade --ticket tN` で行う(効果ベース・既存拠点への影響も採点対象)。

---

## チケット #1 〔新支店開設〕 優先度: 中

設備管理部より: 新支店の開通作業を依頼する。ルータ BR3 は結線済み・未設定。
添付の**開設仕様書 (spec_br3.md) どおり**に開通させること。現地PC(H-B3)は
資産管理部の管理品につき設定変更不可。完了後、仕様書と現地実態に食い違いが
あった場合は `report_d2.yaml` の `t1_discrepancies` に報告すること。

```yaml
# report_d2.yaml (作業フォルダに置く)
t1_discrepancies:            # 食い違いが無ければ空リスト
  - item: <psk|lan|wan_ip|transform|tunnel_policy のいずれか>
    spec: "<仕様書の値>"
    actual: "<実機・実態の値>"
```

## チケット #2 〔体感速度の苦情〕 優先度: 高

{mig_jp}({mig}) のユーザ複数名より「先週からインターネットが遅い」と苦情。
調査の結果、開通当初からの本社経由集約が原因と判明した。経営会議で
{mig_jp} の**ローカルブレイクアウト化**が承認されたため、切り替えを実施せよ。
**他拠点の通信・支店間ポリシーに影響を出さないこと。**

## チケット #3 〔吸収拠点の接続不良〕 優先度: 高

先月吸収した営業所(BR4)を、現地の担当者が本社 VPN へ接続しようとしたが
「トンネルは張れたようだが、**よくわからないがうまくいかない**」との報告。
現地 LAN のアドレス変更は移設済みの検査装置の都合で**不可**。
本社と相互通信できるようにし、インターネットも現地回線から直接出られるように
すること(本社側ルータの設定変更は通常の作業申請range内で可)。

---
*(自動生成: gen_s2svpn.py --day2 seed={pid.split('-')[2]})*
"""


def gen_day2(seed, repo):
    import yaml
    pid = f"GEN-S2SVPN-{seed}-D2"
    ax = pick_axes_day2(seed)
    title = "CCNP-LAB-" + hashlib.md5(pid.encode()).hexdigest()[:8]
    out = os.path.join(repo, "problems", pid)
    os.makedirs(os.path.join(out, "solution"), exist_ok=True)

    with open(os.path.join(out, "lab.yaml"), "w") as f:
        yaml.dump(build_lab_yaml_day2(pid, title, ax), f, allow_unicode=True,
                  sort_keys=False, width=100)
    with open(os.path.join(out, "task.md"), "w") as f:
        f.write(build_task_day2(pid, ax))
    with open(os.path.join(out, "spec_br3.md"), "w") as f:
        f.write(build_spec_br3(ax))
    with open(os.path.join(out, "problem.yml"), "w") as f:
        f.write(f"""# 自動生成 (gen_s2svpn.py --day2) {pid}
# ★運用: s2svpn_ops.py build → solve --mode base → day2init → (受講者作業) → grade --ticket t1|t2|t3
id: {pid}
title: 拠点間VPN 運用週間 — Day2チケット3本 (seed={seed})
exam: ENARSI
topics: [ipsec, vpn-ops, nat-overlap, brownfield, generated]
difficulty: 5
topology: "problems/{pid}/lab.yaml (12台: IOSv×5 + IOL INET + alpine×6)"
target_nodes: [HQ, BR1, BR2, BR3, BR4]
fixed_nodes: [INET, SRV, H-HQ, H-B1, H-B2, H-B3, H-B4]
points: 300   # 100点×3チケット
access: console
notes: |
  BL-063 の Day2 続編(BL-064)。base(svti)を ops が自動投入した「稼働中の本番」に
  運用チケットを順に処理する。#1 支店追加(仕様書×実機の食い違い=seed注入) /
  #2 full→split 移行 / #3 サブネット完全重複×NAT overlapping(曖昧チケット)。
  軸: {ax['tun']} b2b={ax['b2b']} migrate={ax['day2']['migrate_target']} br3={ax['day2']['br3']['policy']}/{ax['day2']['br3']['lan']} br4→{ax['day2']['br4']['overlap_of']} alias={ax['day2']['br4']['alias']} disc={ax['day2']['br3']['disc']['items']}
""")

    params = {
        "id": pid, "title": title, "axes": ax,
        "pub": PUB, "srv": {"ip": SRV_IP, "gw": SRV_GW},
        "lan_hosts": {"HQ": f"{ax['lan']['HQ']}.101",
                      "BR1": f"{ax['lan']['BR1']}.101",
                      "BR2": f"{ax['lan']['BR2']}.101",
                      "BR3": f"{ax['day2']['br3']['lan']}.101",
                      "BR4": f"{ax['day2']['br4']['lan']}.{ax['day2']['br4']['host_oct']}"},
        "judge_seq": {"HQ": 10, "BR1": 20, "BR2": 30, "BR3": 40, "BR4": 50},
        "bigbin": BIGBIN,
        "alpine": ["SRV", "H-HQ", "H-B1", "H-B2", "H-B3", "H-B4"],
        "day2": ax["day2"],
    }
    with open(os.path.join(out, "params.json"), "w") as f:
        json.dump(params, f, ensure_ascii=False, indent=2)

    sols = {"base": solve_svti(ax), "t1": solve_t1(ax), "t2": solve_t2(ax),
            "t3": solve_t3(ax)}
    for mode, cfgs in sols.items():
        with open(os.path.join(out, "solution", f"solve_{mode}.json"), "w") as f:
            json.dump(cfgs, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out, "solution", "day2init.json"), "w") as f:
        json.dump(day2_init(ax), f, ensure_ascii=False, indent=2)

    print(f"generated: problems/{pid}/ (Day2)")
    print(f"  base: tun={ax['tun']} b2b={ax['b2b']}")
    print(f"  t1: BR3 {ax['day2']['br3']['policy']} lan={ax['day2']['br3']['lan']} "
          f"disc={ax['day2']['br3']['disc']['items']}")
    print(f"  t2: migrate {ax['day2']['migrate_target']} → split")
    print(f"  t3: BR4 overlaps {ax['day2']['br4']['overlap_of']} "
          f"({ax['day2']['br4']['lan']}.0/24) alias={ax['day2']['br4']['alias']}.0/24")


# ----------------------------------------------------------------------------
def build_problem_yml(pid, ax, title):
    tunj = ",".join(f"{k}={v}" for k, v in ax["tun"].items())
    return f"""# 自動生成 (gen_s2svpn.py) {pid}
# ★専用運用ツール: python3 topologies/s2svpn_ops.py build|status|solve|grade|teardown --problem {pid}
id: {pid}
title: 拠点間VPN導入プロジェクト 設計・構築 (seed={pid.split('-')[-1]})
exam: ENARSI
topics: [ipsec, vpn-design, napt, split-tunnel, full-tunnel, generated]
difficulty: 4
topology: "problems/{pid}/lab.yaml (8台一体型: IOSv×3 + IOL INET + alpine×4)"
target_nodes: [HQ, BR1, BR2]
fixed_nodes: [INET, SRV, H-HQ, H-B1, H-B2]
points: 100
access: console
notes: |
  要件書だけ渡して VPN 方式選定から委ねる設計構築問(BL-063)。
  採点は s2svpn_ops.py grade の逐次効果ベース(解法非依存)。
  軸: tunnel={tunj} / b2b={ax['b2b']} / pubsrv={ax['pubsrv']} / lab title={title}
  コンソールのみ(MGMTリース不使用)。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--show", action="store_true", help="軸の抽選結果のみ表示")
    ap.add_argument("--day2", action="store_true",
                    help="Day2 運用シナリオパック(チケット3本)を生成 (BL-064)")
    ap.add_argument("--repo", default=REPO)
    args = ap.parse_args()

    if args.day2 and not args.show:
        gen_day2(args.seed, args.repo)
        return
    pid = f"GEN-S2SVPN-{args.seed}" + ("-D2" if args.day2 else "")
    ax = pick_axes_day2(args.seed) if args.day2 else pick_axes(args.seed)
    title = "CCNP-LAB-" + hashlib.md5(pid.encode()).hexdigest()[:8]
    if args.show:
        print(json.dumps({"id": pid, "title": title, **ax},
                         ensure_ascii=False, indent=2))
        return

    import yaml
    out = os.path.join(args.repo, "problems", pid)
    os.makedirs(os.path.join(out, "solution"), exist_ok=True)

    with open(os.path.join(out, "lab.yaml"), "w") as f:
        yaml.dump(build_lab_yaml(pid, title, ax), f, allow_unicode=True,
                  sort_keys=False, default_style=None, width=100)
    with open(os.path.join(out, "task.md"), "w") as f:
        f.write(build_task(pid, ax))
    with open(os.path.join(out, "problem.yml"), "w") as f:
        f.write(build_problem_yml(pid, ax, title))

    params = {
        "id": pid, "title": title, "axes": ax,
        "pub": PUB, "srv": {"ip": SRV_IP, "gw": SRV_GW},
        "lan_hosts": {s: f"{ax['lan'][s]}.101" for s in ("HQ", "BR1", "BR2")},
        "bigbin": BIGBIN,
        "alpine": ["SRV", "H-HQ", "H-B1", "H-B2"],
    }
    with open(os.path.join(out, "params.json"), "w") as f:
        json.dump(params, f, ensure_ascii=False, indent=2)

    sols = {"svti": solve_svti(ax)}
    cm = solve_cmap(ax)
    if cm:
        sols["cmap"] = cm
    for mode, cfgs in sols.items():
        with open(os.path.join(out, "solution", f"solve_{mode}.json"), "w") as f:
            json.dump(cfgs, f, ensure_ascii=False, indent=2)

    print(f"generated: problems/{pid}/")
    print(f"  axes: tun={ax['tun']} b2b={ax['b2b']} pubsrv={ax['pubsrv']} lan={ax['lan']}")
    print(f"  lab title: {title} / solutions: {', '.join(sols)}")


if __name__ == "__main__":
    main()
