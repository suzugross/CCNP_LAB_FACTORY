#!/usr/bin/env python3
"""エンタープライズ拠点ネットワーク 構築問 生成器（BL-225・GEN-ENT・要件書駆動・難5）。

部門 VLAN／サーバ VLAN／MGMT VLAN を持つ拠点を、要件書どおりに白紙から組ませる。
インターネットは PPPoE 2 回線（ISP-A=RT01・ISP-B=RT02）で冗長、L2 は rapid-pvst、
L3SW⇔RT はトランジット VLAN、VLAN 間とインターネット境界は最小許可の ACL で制御、
DHCP はサーバ VLAN の IOS 専用機（DHCP01）＋リレー、名前解決は既設の社内 DNS。

  SRVINET(ISP DNS/Web/NTP は INET) ─ INET ─┬─ ISPA(BRAS) ── RT01 ─┐
                                           └─ ISPB(BRAS) ── RT02 ─┤ TRANSIT(/29・OSPF)
                                                     SW01 ═(LACP)═ SW02   (L3SW・HSRP・ACL・リレー)
                                              SW03(ASW01) SW04(ASW02) SW05(SRVSW)
                                         PC01〜PC03(業務3部門) PC04(情シス) PC05(来客) PC06(複合機)
                                                                SRV01(DNS) SRV02(APP) DHCP01

設計= problems/_drafts/ENTERPRISE-BUILD.design.md（§0 決定事項・§11/§12 PoC 反映）。
PoC= poc/enterprise/README.md。採点の組み方:
  - IOS は telnet 収集（ioll2 は SSH 不可）。Linux 端末は exec: shell（collect_telnet.py が ssh で実行）。
  - 端末には初期化時に **疎通プローブ** /usr/local/bin/ccnp-probe を焼き込む（試験内容は seed の値で生成）。
  - 回線切替の試験は grade.yml の外＝**採点前フック**（problem.yml pre_grade → ent_ops.py）で 1 回だけ。
  - ACL は要件書の **命名規約**で名前を固定し、acl_model（acl_vectors）で意味評価（許可しすぎの検出）。
使い方: gen_enterprise.py --repo . --seed <int> ／ gen_enterprise.py --selftest 300
"""
import argparse
import importlib.util
import json
import os
import random
import string
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))

ISP_DNS = "192.0.2.10"        # SRVINET（ISP の DNS・Web・大容量ファイル・回線監視の対象）
ISP_NTP = "192.0.2.1"         # INET（ntp master）
INET_DOM = "inet.example"
BIG_SIZE = 8 * 1024 * 1024
TELNET_VTY = ["line vty 0 4", " transport input ssh telnet", "!"]

DEPT_POOL = [("SALES", "営業"), ("DEV", "開発"), ("ACCT", "経理"), ("HR", "人事"),
             ("GA", "総務"), ("PLAN", "企画"), ("MFG", "製造")]
ACL_STYLES = [("ACL-{}-IN", "ACL-<名前>-IN"), ("{}_IN", "<名前>_IN"),
              ("IN-{}", "IN-<名前>"), ("FLT-{}", "FLT-<名前>")]
CORP_DOMS = ["corp.example", "intra.example", "hq.example", "office.example"]

# ノード配置（ioll2 の links 添字: 0..3=Et0/0..0/3・4=Et1/0・5=Et1/1 / IOL ルータ: 0..2=Et0/0..0/2）
L2IF = ["Ethernet0/0", "Ethernet0/1", "Ethernet0/2", "Ethernet0/3", "Ethernet1/0", "Ethernet1/1"]
ASW = {"SW03": {"label": "ASW01", "pcs": ["PC01", "PC02", "PC03"]},
       "SW04": {"label": "ASW02", "pcs": ["PC04", "PC05", "PC06"]},
       "SW05": {"label": "SRVSW", "pcs": ["SRV01", "SRV02", "DHCP01"]}}
LINUX = ["SRVINET", "SRV01", "SRV02", "PC01", "PC02", "PC03", "PC04", "PC05", "PC06"]
IOS_R = ["INET", "ISPA", "ISPB", "RT01", "RT02", "DHCP01"]
SWS = ["SW01", "SW02", "SW03", "SW04", "SW05"]


# =============================================================================
# 値の抽選
# =============================================================================
def rnd_pw(rnd, n=8):
    return "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(n))


def build_values(seed):
    rnd = random.Random(seed)
    v = {"seed": seed, "S": rnd.randint(16, 99)}
    S = v["S"]
    pool = list(range(10, 250, 10))
    rnd.shuffle(pool)
    vids = pool[:8]                      # 業務3 + 情シス + 来客 + 複合機 + サーバ + MGMT
    depts = rnd.sample(DEPT_POOL, 3)
    intra = rnd.randrange(3)             # イントラのみの部門
    v["depts"] = []
    for i, (tag, jp) in enumerate(depts):
        v["depts"].append({"tag": tag, "jp": jp, "vlan": vids[i], "pc": f"PC0{i + 1}",
                           "inet": i != intra})
    v["it"] = {"tag": "IT", "jp": "情シス", "vlan": vids[3], "pc": "PC04"}
    v["guest"] = {"tag": "GUEST", "jp": "来客", "vlan": vids[4], "pc": "PC05"}
    v["print"] = {"tag": "PRINT", "jp": "複合機", "vlan": vids[5], "pc": "PC06"}
    v["server"] = {"tag": "SERVER", "jp": "サーバ", "vlan": vids[6]}
    v["mgmt"] = {"tag": "MGMT", "jp": "機器管理", "vlan": vids[7]}
    v["transit"] = {"tag": "TRANSIT", "jp": "トランジット", "vlan": rnd.choice(range(900, 990, 10))}
    v["native"] = rnd.choice([555, 666, 777, 888])
    for seg in [*v["depts"], v["it"], v["guest"], v["print"], v["server"], v["mgmt"]]:
        seg["net"] = f"10.{S}.{seg['vlan']}"
    v["transit"]["net"] = f"10.{S}.255"
    # HSRP Active（＝STP root）の割り当て: VLAN 番号順に交互・開始側は seed
    segs = sorted([*v["depts"], v["it"], v["guest"], v["print"], v["server"], v["mgmt"]],
                  key=lambda s: s["vlan"])
    first = rnd.choice(["SW01", "SW02"])
    other = "SW02" if first == "SW01" else "SW01"
    for i, s in enumerate(segs):
        s["active"] = first if i % 2 == 0 else other
    v["transit"]["active"] = "SW01"
    # サーバ・端末の固定アドレス
    sv = v["server"]["net"]
    v["dns"], v["app"], v["dhcp"] = f"{sv}.10", f"{sv}.20", f"{sv}.30"
    v["prn_ip"] = f"{v['print']['net']}.50"
    v["prn_mac"] = "52:54:00:" + ":".join(f"{rnd.randint(0, 255):02x}" for _ in range(3))
    m = v["mgmt"]["net"]
    v["asw_ip"] = {"SW03": f"{m}.11", "SW04": f"{m}.12", "SW05": f"{m}.13"}
    t = v["transit"]["net"]
    v["tr"] = {"RT01": f"{t}.1", "RT02": f"{t}.2", "SW01": f"{t}.3", "SW02": f"{t}.4"}
    # 回線
    corp = rnd.choice(["hq", "corp", "office", "main"])
    v["isp"] = {
        "A": {"rt": "RT01", "bras": "ISPA", "pub": f"198.51.100.{rnd.randint(10, 99)}",
              "lo": "198.51.100.1", "link": "198.51.100.248", "user": f"{corp}{seed % 1000:03d}@isp-a.example",
              "pw": rnd_pw(rnd), "name": "ISP-A"},
        "B": {"rt": "RT02", "bras": "ISPB", "pub": f"203.0.113.{rnd.randint(10, 99)}",
              "lo": "203.0.113.1", "link": "203.0.113.248", "user": f"{corp}{seed % 1000:03d}@isp-b.example",
              "pw": rnd_pw(rnd), "name": "ISP-B"}}
    v["primary"] = rnd.choice(["A", "B"])
    v["backup"] = "B" if v["primary"] == "A" else "A"
    v["dom"] = rnd.choice(CORP_DOMS)
    v["print_ports"] = [9100] if rnd.random() < 0.5 else [9100, 631]
    style = rnd.choice(ACL_STYLES)
    v["acl_style"] = style[1]
    v["acl"] = {tag: style[0].format(tag) for tag in
                [d["tag"] for d in v["depts"]] + ["IT", "GUEST", "PRINT", "SERVER", "MGMT", "WAN", "LAN"]}
    v["ospf_pid"] = rnd.choice([1, 10, 100])
    v["probe_pc"] = next(d["pc"] for d in v["depts"] if d["inet"])
    return v


def segs_all(v):
    """HSRP/SVI を持つセグメント（トランジット以外）。"""
    return [*v["depts"], v["it"], v["guest"], v["print"], v["server"], v["mgmt"]]


def dhcp_segs(v):
    return [*v["depts"], v["it"], v["guest"], v["print"]]


def asw_vlans(v, sw):
    if sw == "SW03":
        return [d["vlan"] for d in v["depts"]] + [v["mgmt"]["vlan"]]
    if sw == "SW04":
        return [v["it"]["vlan"], v["guest"]["vlan"], v["print"]["vlan"], v["mgmt"]["vlan"]]
    return [v["server"]["vlan"], v["mgmt"]["vlan"]]


def core_vlans(v):
    return sorted([s["vlan"] for s in segs_all(v)] + [v["transit"]["vlan"]])


def port_vlan(v, sw, idx):
    """アクセスポート（links 添字 2..4）の所属 VLAN。"""
    if sw == "SW03":
        return v["depts"][idx - 2]["vlan"]
    if sw == "SW04":
        return [v["it"], v["guest"], v["print"]][idx - 2]["vlan"]
    return v["server"]["vlan"]


def vlan_list_str(vids):
    """IOS の `show interfaces trunk` 表記（連番はハイフンで圧縮）。"""
    vids = sorted(vids)
    out, i = [], 0
    while i < len(vids):
        j = i
        while j + 1 < len(vids) and vids[j + 1] == vids[j] + 1:
            j += 1
        out.append(str(vids[i]) if i == j else f"{vids[i]}-{vids[j]}")
        i = j + 1
    return ",".join(out)


def client_id(mac):
    h = "01" + mac.replace(":", "").lower()
    return ".".join(h[i:i + 4] for i in range(0, len(h), 4))


def wc(prefix_len):
    return {24: "0.0.0.255", 16: "0.0.255.255", 29: "0.0.0.7"}[prefix_len]


# =============================================================================
# 模範 ACL（1 つの定義から golden と selftest の両方を作る）
# =============================================================================
RFC1918_DENY = ["deny ip any 10.0.0.0 0.255.255.255", "deny ip any 172.16.0.0 0.15.255.255",
                "deny ip any 192.168.0.0 0.0.255.255"]
DHCP_HSRP = ["permit udp any eq bootpc any eq bootps", "permit udp any host 224.0.0.102 eq 1985"]


def n24(seg):
    return f"{seg['net']}.0 0.0.0.255"


def acl_bodies(v):
    """{ACL名: [エントリ本文...]}（L3SW 用 7 本＋RT 用 WAN/LAN。RT の LAN は RT ごとに NTP 宛先が違う）。"""
    S, A = v["S"], v["acl"]
    site = f"10.{S}.0.0 0.0.255.255"
    srv_permits = lambda net: [
        f"permit udp {net} host {v['dns']} eq domain", f"permit tcp {net} host {v['dns']} eq domain",
        f"permit tcp {net} host {v['app']} eq www", f"permit tcp {net} host {v['app']} eq 443",
        f"permit tcp {net} host {v['app']} eq 445",
        f"permit icmp {net} {n24(v['server'])} echo"] + [
        f"permit tcp {net} host {v['prn_ip']} eq {p}" for p in v["print_ports"]]
    out = {}
    for d in v["depts"]:
        net = n24(d)
        body = DHCP_HSRP + srv_permits(net) + [f"permit icmp {net} {n24(v['it'])} echo-reply"] + RFC1918_DENY
        if d["inet"]:
            body.append(f"permit ip {net} any")
        out[A[d["tag"]]] = body
    it = n24(v["it"])
    out[A["IT"]] = DHCP_HSRP + srv_permits(it) + [
        f"permit icmp {it} {n24(s)} echo" for s in [*v["depts"], v["print"], v["mgmt"]]] + [
        f"permit tcp {it} {n24(v['mgmt'])} eq telnet"] + RFC1918_DENY + [f"permit ip {it} any"]
    g = n24(v["guest"])
    out[A["GUEST"]] = DHCP_HSRP + [f"permit udp {g} host {ISP_DNS} eq domain"] + RFC1918_DENY + [
        f"permit tcp {g} any eq www", f"permit tcp {g} any eq 443"]
    p = n24(v["print"])
    out[A["PRINT"]] = DHCP_HSRP + [f"permit tcp {p} {site} established",
                                   f"permit icmp {p} {site} echo-reply"]
    s = n24(v["server"])
    out[A["SERVER"]] = [DHCP_HSRP[1], f"permit tcp {s} {site} established",
                        f"permit udp host {v['dns']} eq domain {site}",
                        f"permit icmp {s} {site} echo-reply",
                        f"permit udp host {v['dhcp']} eq bootps {site}",
                        f"permit udp host {v['dns']} host {ISP_DNS} eq domain",
                        f"permit tcp host {v['dns']} host {ISP_DNS} eq domain"]
    m = n24(v["mgmt"])
    out[A["MGMT"]] = [DHCP_HSRP[1], f"permit tcp {m} {it} established", f"permit icmp {m} {it} echo-reply",
                      f"permit udp {m} host {v['mgmt']['net']}.2 eq ntp",
                      f"permit udp {m} host {v['mgmt']['net']}.3 eq ntp"]
    out[A["WAN"]] = ["deny ip 10.0.0.0 0.255.255.255 any", "deny ip 172.16.0.0 0.15.255.255 any",
                     "deny ip 192.168.0.0 0.0.255.255 any", "deny ip 127.0.0.0 0.255.255.255 any",
                     "permit tcp any any established", f"permit udp host {ISP_DNS} eq domain any",
                     f"permit udp host {ISP_NTP} eq ntp any eq ntp", "permit icmp any any echo-reply",
                     "permit icmp any any unreachable", "permit icmp any any time-exceeded",
                     "deny ip any any"]
    return out


def lan_in_body(v, rt):
    g = n24(v["guest"])
    body = ["permit ospf any any",
            f"permit udp host {v['tr']['SW01']} host {v['tr'][rt]} eq ntp",
            f"permit udp host {v['tr']['SW02']} host {v['tr'][rt]} eq ntp",
            "deny tcp any any eq smtp", "deny tcp any any range 135 139",
            "deny udp any any range 137 139", "deny tcp any any eq 445",
            f"permit udp host {v['dns']} host {ISP_DNS} eq domain",
            f"permit tcp host {v['dns']} host {ISP_DNS} eq domain",
            f"permit udp {g} host {ISP_DNS} eq domain",
            "deny udp any any eq domain", "deny tcp any any eq domain",
            f"permit tcp {g} any eq www", f"permit tcp {g} any eq 443", f"deny ip {g} any"]
    body += [f"permit ip {n24(d)} any" for d in v["depts"] if d["inet"]]
    body += [f"permit ip {n24(v['it'])} any", "deny ip any any"]
    return body


# ---- 採点ベクタ（要件で結果が一意に決まるものだけ） ----------------------------------
def V(vid, proto, src, dst, expect, **kw):
    x = {"id": vid, "proto": proto, "src": src, "dst": dst, "expect": expect}
    x.update(kw)
    return x


def vectors(v):
    """{ACL の tag: [vector...]}（WAN/LAN は RT ごと: 'WAN:RT01' 等）。"""
    S = v["S"]
    host = lambda seg, n=100: f"{seg['net']}.{n}"
    out = {}
    other_inet = "198.51.100.77"
    common = lambda seg: [
        V("dhcp-bcast", "udp", "0.0.0.0", "255.255.255.255", "permit", sport=68, dport=67),
        V("dhcp-renew", "udp", host(seg), v["dhcp"], "permit", sport=68, dport=67),
        V("hsrp-sw01", "udp", f"{seg['net']}.2", "224.0.0.102", "permit", sport=1985, dport=1985),
        V("hsrp-sw02", "udp", f"{seg['net']}.3", "224.0.0.102", "permit", sport=1985, dport=1985)]
    for d in v["depts"]:
        h = host(d)
        peer = next(x for x in v["depts"] if x is not d)
        vec = common(d) + [
            V("dns-udp", "udp", h, v["dns"], "permit", sport=40000, dport=53),
            V("dns-tcp", "tcp", h, v["dns"], "permit", sport=40000, dport=53),
            V("app-www", "tcp", h, v["app"], "permit", sport=40000, dport=80),
            V("app-443", "tcp", h, v["app"], "permit", sport=40000, dport=443),
            V("app-445", "tcp", h, v["app"], "permit", sport=40000, dport=445),
            V("srv-ping", "icmp", h, v["app"], "permit", icmp_type=8),
            V("prn-9100", "tcp", h, v["prn_ip"], "permit", sport=40000, dport=9100),
            V("it-echo-reply", "icmp", h, host(v["it"]), "permit", icmp_type=0),
            V("app-3389", "tcp", h, v["app"], "deny", sport=40000, dport=3389),
            V("app-ssh", "tcp", h, v["app"], "deny", sport=40000, dport=22),
            V("dns-ssh", "tcp", h, v["dns"], "deny", sport=40000, dport=22),
            V("prn-www", "tcp", h, v["prn_ip"], "deny", sport=40000, dport=80),
            V("peer-ssh", "tcp", h, host(peer), "deny", sport=40000, dport=22),
            V("peer-ping", "icmp", h, host(peer), "deny", icmp_type=8),
            V("it-ping", "icmp", h, host(v["it"]), "deny", icmp_type=8),
            V("guest-ping", "icmp", h, host(v["guest"]), "deny", icmp_type=8),
            V("mgmt-telnet", "tcp", h, v["asw_ip"]["SW03"], "deny", sport=40000, dport=23),
            V("mgmt-ping", "icmp", h, v["asw_ip"]["SW03"], "deny", icmp_type=8),
            V("dhcp01-telnet", "tcp", h, v["dhcp"], "deny", sport=40000, dport=23),
            V("transit-ssh", "tcp", h, v["tr"]["RT01"], "deny", sport=40000, dport=22),
            V("inet-8080", "tcp", h, ISP_DNS, "permit" if d["inet"] else "deny", sport=40000, dport=8080),
            V("inet-www", "tcp", h, other_inet, "permit" if d["inet"] else "deny", sport=40000, dport=80)]
        out[d["tag"]] = vec
    h = host(v["it"])
    vec = common(v["it"]) + [
        V("dns-udp", "udp", h, v["dns"], "permit", sport=40000, dport=53),
        V("app-www", "tcp", h, v["app"], "permit", sport=40000, dport=80),
        V("prn-9100", "tcp", h, v["prn_ip"], "permit", sport=40000, dport=9100),
        V("prn-ping", "icmp", h, v["prn_ip"], "permit", icmp_type=8),
        V("mgmt-ping", "icmp", h, v["asw_ip"]["SW04"], "permit", icmp_type=8),
        V("mgmt-telnet", "tcp", h, v["asw_ip"]["SW04"], "permit", sport=40000, dport=23),
        V("mgmt-www", "tcp", h, v["asw_ip"]["SW04"], "deny", sport=40000, dport=80),
        V("mgmt-ssh", "tcp", h, v["asw_ip"]["SW04"], "deny", sport=40000, dport=22),
        V("guest-ping", "icmp", h, host(v["guest"]), "deny", icmp_type=8),
        V("app-3389", "tcp", h, v["app"], "deny", sport=40000, dport=3389),
        V("inet-8080", "tcp", h, ISP_DNS, "permit", sport=40000, dport=8080)]
    for d in v["depts"]:
        vec += [V(f"ping-{d['tag']}", "icmp", h, host(d), "permit", icmp_type=8),
                V(f"ssh-{d['tag']}", "tcp", h, host(d), "deny", sport=40000, dport=22)]
    out["IT"] = vec
    h = host(v["guest"])
    out["GUEST"] = common(v["guest"]) + [
        V("isp-dns", "udp", h, ISP_DNS, "permit", sport=40000, dport=53),
        V("inet-www", "tcp", h, other_inet, "permit", sport=40000, dport=80),
        V("inet-443", "tcp", h, other_inet, "permit", sport=40000, dport=443),
        V("corp-dns", "udp", h, v["dns"], "deny", sport=40000, dport=53),
        V("app-www", "tcp", h, v["app"], "deny", sport=40000, dport=80),
        V("prn-9100", "tcp", h, v["prn_ip"], "deny", sport=40000, dport=9100),
        V("dept-ping", "icmp", h, host(v["depts"][0]), "deny", icmp_type=8),
        V("mgmt-telnet", "tcp", h, v["asw_ip"]["SW04"], "deny", sport=40000, dport=23)]
    p = v["prn_ip"]
    dh = host(v["depts"][0])
    out["PRINT"] = common(v["print"]) + [
        V("print-reply", "tcp", p, dh, "permit", sport=9100, dport=40000, established=True),
        V("echo-reply-it", "icmp", p, host(v["it"]), "permit", icmp_type=0),
        V("new-to-dept", "tcp", p, dh, "deny", sport=40000, dport=22),
        V("ping-dept", "icmp", p, dh, "deny", icmp_type=8),
        V("to-dns", "udp", p, v["dns"], "deny", sport=40000, dport=53),
        V("to-inet", "tcp", p, ISP_DNS, "deny", sport=40000, dport=80)]
    sv = v["server"]
    out["SERVER"] = [
        V("hsrp-sw01", "udp", f"{sv['net']}.2", "224.0.0.102", "permit", sport=1985, dport=1985),
        V("hsrp-sw02", "udp", f"{sv['net']}.3", "224.0.0.102", "permit", sport=1985, dport=1985),
        V("app-reply", "tcp", v["app"], dh, "permit", sport=80, dport=40000, established=True),
        V("dns-reply", "udp", v["dns"], dh, "permit", sport=53, dport=40000),
        V("echo-reply", "icmp", v["app"], dh, "permit", icmp_type=0),
        V("relay-reply-sw01", "udp", v["dhcp"], f"{v['depts'][0]['net']}.2", "permit", sport=67, dport=67),
        V("relay-reply-sw02", "udp", v["dhcp"], f"{v['depts'][0]['net']}.3", "permit", sport=67, dport=67),
        V("renew-reply", "udp", v["dhcp"], dh, "permit", sport=67, dport=68),
        V("dns-forward", "udp", v["dns"], ISP_DNS, "permit", sport=40000, dport=53),
        V("app-new-to-dept", "tcp", v["app"], dh, "deny", sport=40000, dport=22),
        V("app-ping-dept", "icmp", v["app"], dh, "deny", icmp_type=8),
        V("app-inet", "tcp", v["app"], ISP_DNS, "deny", sport=40000, dport=80),
        V("app-inet-dns", "udp", v["app"], ISP_DNS, "deny", sport=40000, dport=53),
        V("dns-inet-www", "tcp", v["dns"], ISP_DNS, "deny", sport=40000, dport=80),
        V("app-mgmt", "tcp", v["app"], v["asw_ip"]["SW03"], "deny", sport=40000, dport=23)]
    a = v["asw_ip"]["SW03"]
    ih = host(v["it"])
    out["MGMT"] = [
        V("hsrp-sw01", "udp", f"{v['mgmt']['net']}.2", "224.0.0.102", "permit", sport=1985, dport=1985),
        V("hsrp-sw02", "udp", f"{v['mgmt']['net']}.3", "224.0.0.102", "permit", sport=1985, dport=1985),
        V("telnet-reply-it", "tcp", a, ih, "permit", sport=23, dport=40000, established=True),
        V("echo-reply-it", "icmp", a, ih, "permit", icmp_type=0),
        V("ntp-sw01", "udp", a, f"{v['mgmt']['net']}.2", "permit", sport=123, dport=123),
        V("ntp-sw02", "udp", a, f"{v['mgmt']['net']}.3", "permit", sport=123, dport=123),
        V("new-to-it", "tcp", a, ih, "deny", sport=40000, dport=22),
        V("new-to-dept", "tcp", a, dh, "deny", sport=40000, dport=22),
        V("to-inet", "tcp", a, ISP_DNS, "deny", sport=40000, dport=80)]
    for key in ("A", "B"):
        isp = v["isp"][key]
        rt, pub = isp["rt"], isp["pub"]
        out[f"WAN:{rt}"] = [
            V("tcp-return", "tcp", ISP_DNS, pub, "permit", sport=80, dport=40000, established=True),
            V("dns-return", "udp", ISP_DNS, pub, "permit", sport=53, dport=40000),
            V("ntp-return", "udp", ISP_NTP, pub, "permit", sport=123, dport=123),
            V("sla-echo-reply", "icmp", ISP_DNS, pub, "permit", icmp_type=0),
            V("unreachable", "icmp", "192.0.2.200", pub, "permit", icmp_type=3),
            V("time-exceeded", "icmp", "192.0.2.200", pub, "permit", icmp_type=11),
            V("ssh-in", "tcp", "192.0.2.66", pub, "deny", sport=40000, dport=22),
            V("telnet-in", "tcp", "192.0.2.66", pub, "deny", sport=40000, dport=23),
            V("www-in", "tcp", "192.0.2.66", pub, "deny", sport=40000, dport=80),
            V("ping-in", "icmp", "192.0.2.66", pub, "deny", icmp_type=8),
            V("dns-other-src", "udp", "192.0.2.66", pub, "deny", sport=53, dport=40000),
            V("spoof-10", "tcp", "10.1.2.3", pub, "deny", sport=80, dport=40000, established=True),
            V("spoof-172", "tcp", "172.16.5.5", pub, "deny", sport=80, dport=40000, established=True),
            V("spoof-192", "tcp", "192.168.1.1", pub, "deny", sport=80, dport=40000, established=True),
            V("spoof-127", "udp", "127.0.0.1", pub, "deny", sport=53, dport=40000)]
        g = host(v["guest"])
        inet_d = next(d for d in v["depts"] if d["inet"])
        intra_d = next(d for d in v["depts"] if not d["inet"])
        dh1 = host(inet_d)
        out[f"LAN:{rt}"] = [
            V("ospf", "ospf", v["tr"]["SW01"], "224.0.0.5", "permit"),
            V("ntp-sw01", "udp", v["tr"]["SW01"], v["tr"][rt], "permit", sport=123, dport=123),
            V("ntp-sw02", "udp", v["tr"]["SW02"], v["tr"][rt], "permit", sport=123, dport=123),
            V("dns-fwd-udp", "udp", v["dns"], ISP_DNS, "permit", sport=40000, dport=53),
            V("dns-fwd-tcp", "tcp", v["dns"], ISP_DNS, "permit", sport=40000, dport=53),
            V("guest-dns", "udp", g, ISP_DNS, "permit", sport=40000, dport=53),
            V("guest-www", "tcp", g, other_inet, "permit", sport=40000, dport=80),
            V("guest-443", "tcp", g, other_inet, "permit", sport=40000, dport=443),
            V("dept-8080", "tcp", dh1, ISP_DNS, "permit", sport=40000, dport=8080),
            V("dept-ping", "icmp", dh1, ISP_DNS, "permit", icmp_type=8),
            V("it-www", "tcp", host(v["it"]), other_inet, "permit", sport=40000, dport=80),
            V("dept-445", "tcp", dh1, ISP_DNS, "deny", sport=40000, dport=445),
            V("dept-smtp", "tcp", dh1, ISP_DNS, "deny", sport=40000, dport=25),
            V("dept-139", "tcp", dh1, ISP_DNS, "deny", sport=40000, dport=139),
            V("dept-137-udp", "udp", dh1, ISP_DNS, "deny", sport=40000, dport=137),
            V("it-445", "tcp", host(v["it"]), ISP_DNS, "deny", sport=40000, dport=445),
            V("dept-direct-dns", "udp", dh1, ISP_DNS, "deny", sport=40000, dport=53),
            V("dept-direct-dns-tcp", "tcp", dh1, ISP_DNS, "deny", sport=40000, dport=53),
            V("guest-8080", "tcp", g, ISP_DNS, "deny", sport=40000, dport=8080),
            V("guest-ping", "icmp", g, ISP_DNS, "deny", icmp_type=8),
            V("guest-other-dns", "udp", g, "192.0.2.66", "deny", sport=40000, dport=53),
            V("intra-www", "tcp", host(intra_d), other_inet, "deny", sport=40000, dport=80),
            V("app-www", "tcp", v["app"], other_inet, "deny", sport=40000, dport=80),
            V("dns-www", "tcp", v["dns"], other_inet, "deny", sport=40000, dport=80),
            V("prn-www", "tcp", v["prn_ip"], other_inet, "deny", sport=40000, dport=80),
            V("mgmt-www", "tcp", v["asw_ip"]["SW03"], other_inet, "deny", sport=40000, dport=80),
            V("spoof-src", "tcp", "10.200.1.1", other_inet, "deny", sport=40000, dport=80),
            V("spoof-172", "tcp", "172.16.1.1", other_inet, "deny", sport=40000, dport=80)]
    return out


# =============================================================================
# 初期状態（既設ノードの day0・Linux 初期化）
# =============================================================================
def init_inet(v):
    return ["! INET（インターネット中継・既設・変更不可）",
            "interface {{ links[0] }}", " description === to ISP-A ===",
            f" ip address {v['isp']['A']['link'][:-3]}250 255.255.255.252", " no shutdown", "!",
            "interface {{ links[1] }}", " description === to ISP-B ===",
            f" ip address {v['isp']['B']['link'][:-3]}250 255.255.255.252", " no shutdown", "!",
            "interface {{ links[2] }}", " description === INET segment (SRVINET) ===",
            f" ip address {ISP_NTP} 255.255.255.0", " ip access-group PMTU-BLACKHOLE out", " no shutdown", "!",
            f"ip route 198.51.100.0 255.255.255.0 {v['isp']['A']['link'][:-3]}249",
            f"ip route 203.0.113.0 255.255.255.0 {v['isp']['B']['link'][:-3]}249",
            "! インターネット上の PMTUD ブラックホール（packet-too-big を捨てる経路）",
            "ip access-list extended PMTU-BLACKHOLE", " deny icmp any any packet-too-big",
            " permit ip any any", "!", "ntp master 3", "!"] + TELNET_VTY


def init_bras(v, key):
    i = v["isp"][key]
    base = i["link"][:-3]
    return [f"! {i['name']} BRAS（PPPoE サーバ・既設・変更不可）",
            f"username {i['user']} password 0 {i['pw']}",
            f"ip local pool CUST-{key} {i['pub']} {i['pub']}",
            "bba-group pppoe global", " virtual-template 1", "!",
            "interface Loopback0", f" ip address {i['lo']} 255.255.255.255", "!",
            "interface Virtual-Template1", " ip unnumbered Loopback0",
            f" peer default ip address pool CUST-{key}", " ppp authentication chap", "!",
            "interface {{ links[0] }}", " description === to customer (PPPoE) ===", " no ip address",
            " pppoe enable group global", " no shutdown", "!",
            "interface {{ links[1] }}", " description === to INET ===",
            f" ip address {base}249 255.255.255.252", " no shutdown", "!",
            f"ip route 0.0.0.0 0.0.0.0 {base}250", "!"] + TELNET_VTY


def init_dhcp01(v):
    return ["! DHCP01（サーバ VLAN の DHCP 専用機・土台: IF アドレスと既定経路のみ。プールは未設定）",
            "interface {{ links[0] }}", " description === SERVER VLAN ===",
            f" ip address {v['dhcp']} 255.255.255.0", " no shutdown", "!",
            f"ip route 0.0.0.0 0.0.0.0 {v['server']['net']}.1", "!"] + TELNET_VTY


def init_blank_rt(name):
    return [f"! {name} 初期状態（白紙。IF は起動済み・IP アドレスなし）", "!"] + TELNET_VTY


def netplan_final(ens3):
    """初期化の最後に適用する netplan（ens2=管理のみ・既定経路なし／ens3=データ）。"""
    return ("rm -f /etc/netplan/50-cloud-init.yaml\n"
            "cat > /etc/netplan/60-ccnp.yaml <<NP\n"
            "network:\n  version: 2\n  ethernets:\n"
            "    ens2:\n      addresses: [{{ mgmt_ip }}/{{ mgmt_prefixlen }}]\n"
            f"    ens3:\n{ens3}NP\n"
            "chmod 600 /etc/netplan/60-ccnp.yaml\nnetplan apply\n")


SH_HEAD = """#!/bin/bash
# {title}（自動生成 gen_enterprise.py）
export DEBIAN_FRONTEND=noninteractive
log() {{ echo "[$(date -Is)] $*"; }}
echo "{{{{ ansible_user }}}} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-ccnp; chmod 440 /etc/sudoers.d/90-ccnp
for i in 1 2 3; do apt-get update -qq && apt-get install -y -qq {pkgs} && break; sleep 10; done
"""

LISTEN_UNIT = """cat > /etc/systemd/system/ccnp-listen@.service <<'UNIT'
[Unit]
Description=ccnp tcp listener %i
After=network-online.target
[Service]
ExecStart=/bin/nc -lk %i
Restart=always
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
"""


def listen(ports):
    return LISTEN_UNIT + "".join(f"systemctl enable --now ccnp-listen@{p}.service\n" for p in ports)


def pc_ens3():
    return ("      dhcp4: true\n      dhcp-identifier: mac\n")


def probe_script(tests, facts=True):
    """端末の疎通プローブ（採点が `sudo -n /usr/local/bin/ccnp-probe` で実行する）。"""
    lines = ["#!/bin/bash",
             "# GEN-ENT 採点用の疎通プローブ（自動生成）。出力= id=結果 の行",
             "ip route flush cache 2>/dev/null; resolvectl flush-caches 2>/dev/null",
             ". /var/tmp/ccnp-peers 2>/dev/null",
             't_tcp(){ nc -z -w3 "$2" "$3" >/dev/null 2>&1 && echo "$1=OPEN" || echo "$1=CLOSED"; }',
             't_icmp(){ ping -c2 -W2 -q "$2" >/dev/null 2>&1 && echo "$1=OK" || echo "$1=NG"; }',
             't_dns(){ r=$(dig +short +time=2 +tries=2 "$2" A 2>/dev/null | grep -E "^[0-9.]+$" | tail -1); '
             'echo "$1=${r:-NONE}"; }',
             't_dnsat(){ r=$(dig +short +time=2 +tries=1 @"$2" "$3" A 2>/dev/null | grep -E "^[0-9.]+$" | tail -1); '
             'echo "$1=${r:-NONE}"; }',
             't_http(){ r=$(curl -s -m5 "$2" 2>/dev/null | head -1); echo "$1=${r:-NONE}"; }',
             "t_big(){ s=$(curl -s -m25 -o /dev/null -w '%{size_download}' \"$2\" 2>/dev/null); "
             'echo "$1=${s:-0}"; }',
             "{"]
    for tid, kind, args in tests:
        lines.append(f"  t_{kind} {tid} " + " ".join(f'"{a}"' for a in args) + " &")
    lines += ["  wait", "} | sort"]
    if facts:
        lines += ['echo "addr=$(ip -4 -o addr show ens3 | awk \'{print $4}\' | head -1)"',
                  "L=$(ls /run/systemd/netif/leases/* 2>/dev/null | head -1)",
                  '[ -n "$L" ] && grep -E "^(ROUTER|DNS|DOMAINNAME)=" "$L"']
    return "\n".join(lines) + "\n"


def install_probe(tests, facts=True):
    return ("cat > /usr/local/bin/ccnp-probe <<'PROBE'\n" + probe_script(tests, facts) +
            "PROBE\nchmod 755 /usr/local/bin/ccnp-probe\n")


def sh_pc(v, pc, tests, title, extra=""):
    return (SH_HEAD.format(title=title, pkgs="dnsutils netcat-openbsd curl") + extra +
            install_probe(tests) + netplan_final(pc_ens3()) + 'log "DONE"\n')


def sh_srvinet(v):
    ens3 = ("      addresses: [" + ISP_DNS + "/24]\n      routes:\n"
            "        - to: 198.51.100.0/24\n          via: " + ISP_NTP + "\n"
            "        - to: 203.0.113.0/24\n          via: " + ISP_NTP + "\n")
    ext_tests = []
    for key in ("A", "B"):
        i = v["isp"][key]
        r = i["rt"].lower()
        ext_tests += [(f"{r}_ssh", "tcp", [i["pub"], 22]), (f"{r}_telnet", "tcp", [i["pub"], 23]),
                      (f"{r}_www", "tcp", [i["pub"], 80]), (f"{r}_ping", "icmp", [i["pub"]]),
                      (f"bras_{key.lower()}", "icmp", [i["lo"]])]
    body = (SH_HEAD.format(title="SRVINET: ISP DNS(dnsmasq)・Web(/ip・big.bin)・待受 25/443/445/8080",
                           pkgs="nginx dnsmasq netcat-openbsd dnsutils curl") +
            "cat > /etc/nginx/sites-available/default <<'NG'\n"
            "server {\n  listen 80 default_server;\n  root /var/www/html;\n"
            "  location = /ip { default_type text/plain; return 200 \"$remote_addr\\n\"; }\n}\nNG\n"
            f"dd if=/dev/urandom of=/var/www/html/big.bin bs=1M count={BIG_SIZE // 1048576} status=none\n"
            "systemctl restart nginx\n"
            "cat > /etc/dnsmasq.d/inet.conf <<'DM'\n"
            f"listen-address={ISP_DNS}\nbind-interfaces\nno-resolv\n"
            f"address=/www.{INET_DOM}/{ISP_DNS}\naddress=/mail.{INET_DOM}/{ISP_DNS}\nDM\n" +
            listen([25, 443, 445, 8080]) + install_probe(ext_tests, facts=False))
    # SRVINET は管理側の既定経路を残す（採点器・パッケージ取得用）。データ側は顧客ブロックへの経路だけ
    body += ("rm -f /etc/netplan/50-cloud-init.yaml\n"
             "cat > /etc/netplan/60-ccnp.yaml <<NP\n"
             "network:\n  version: 2\n  ethernets:\n"
             "    ens2:\n      addresses: [{{ mgmt_ip }}/{{ mgmt_prefixlen }}]\n"
             "      routes:\n        - to: default\n          via: {{ mgmt_gw }}\n"
             f"    ens3:\n{ens3}NP\n"
             "chmod 600 /etc/netplan/60-ccnp.yaml\nnetplan apply\nsystemctl restart dnsmasq\n"
             'log "DONE"\n')
    return body


def sh_dns(v):
    sv = v["server"]["net"]
    dom = v["dom"]
    rev = f"{v['S']}.10.in-addr.arpa"
    zone = (f"$TTL 300\n@ IN SOA dns.{dom}. admin.{dom}. (1 3600 600 86400 300)\n"
            f"@ IN NS dns.{dom}.\ndns IN A {v['dns']}\nportal IN A {v['app']}\n"
            f"files IN CNAME portal\nprn01 IN A {v['prn_ip']}\n")
    ens3 = (f"      addresses: [{v['dns']}/24]\n      routes:\n        - to: default\n"
            f"          via: {sv}.1\n")
    return (SH_HEAD.format(title="SRV01: 社内 DNS（BIND9・既設）", pkgs="bind9 dnsutils") +
            "cat > /etc/bind/named.conf.options <<'OPT'\n"
            "options {\n  directory \"/var/cache/bind\";\n"
            f"  listen-on {{ 127.0.0.1; {v['dns']}; }};\n  listen-on-v6 {{ none; }};\n"
            f"  allow-query {{ 127.0.0.1; 10.{v['S']}.0.0/16; }};\n"
            f"  allow-recursion {{ 127.0.0.1; 10.{v['S']}.0.0/16; }};\n"
            f"  forwarders {{ {ISP_DNS}; }};\n  forward only;\n  dnssec-validation no;\n}};\nOPT\n"
            "cat > /etc/bind/named.conf.local <<'LOC'\n"
            f"zone \"{dom}\" {{ type master; file \"/etc/bind/db.corp\"; }};\n"
            f"zone \"{rev}\" {{ type master; file \"/etc/bind/db.rev\"; }};\nLOC\n"
            f"cat > /etc/bind/db.corp <<'Z'\n{zone}Z\n"
            "cat > /etc/bind/db.rev <<'Z'\n"
            f"$TTL 300\n@ IN SOA dns.{dom}. admin.{dom}. (1 3600 600 86400 300)\n@ IN NS dns.{dom}.\n"
            f"{'.'.join(reversed(v['dns'].split('.')[2:]))} IN PTR dns.{dom}.\n"
            f"{'.'.join(reversed(v['app'].split('.')[2:]))} IN PTR portal.{dom}.\nZ\n" +
            netplan_final(ens3) + "systemctl restart named\n" + 'log "DONE"\n')


def sh_app(v):
    ens3 = (f"      addresses: [{v['app']}/24]\n      routes:\n        - to: default\n"
            f"          via: {v['server']['net']}.1\n")
    return (SH_HEAD.format(title="SRV02: 社内 Web/ファイル役（既設）・待受 80/443/445/3389",
                           pkgs="nginx netcat-openbsd dnsutils curl") +
            "echo 'portal OK' > /var/www/html/index.html\nsystemctl restart nginx\n" +
            listen([443, 445, 3389]) + netplan_final(ens3) + 'log "DONE"\n')


def sh_prn(v):
    return (SH_HEAD.format(title="PC06: 複合機（既設・DHCP・印刷ポート待受）", pkgs="netcat-openbsd") +
            listen(v["print_ports"] + [80]) + install_probe([], facts=True) +
            netplan_final(pc_ens3()) + 'log "DONE"\n')


# ---- 端末ごとのプローブ（id, kind, args, 期待） -----------------------------------
def pc_tests(v):
    """{PC: [(id, kind, args, expect_regex_value)]}（期待値は `id=` の右辺に一致させる正規表現）。"""
    pri = v["isp"][v["primary"]]["pub"]
    asw1 = v["asw_ip"]["SW03"]
    out = {}
    for i, d in enumerate(v["depts"]):
        peer = v["depts"][(i + 1) % 3]["pc"]
        t = [("dns_portal", "dns", [f"portal.{v['dom']}"], re_ip(v["app"])),
             ("dns_inet", "dns", [f"www.{INET_DOM}"], re_ip(ISP_DNS)),
             ("dns_direct", "dnsat", [ISP_DNS, f"www.{INET_DOM}"], "NONE"),
             ("app80", "tcp", [v["app"], 80], "OPEN"), ("app445", "tcp", [v["app"], 445], "OPEN"),
             ("app3389", "tcp", [v["app"], 3389], "CLOSED"), ("srv_ping", "icmp", [v["app"]], "OK"),
             ("prn", "tcp", [v["prn_ip"], 9100], "OPEN"),
             ("peer_ping", "icmp", [f"$IP_{peer}"], "NG"), ("peer_ssh", "tcp", [f"$IP_{peer}", 22], "CLOSED"),
             ("it_ping", "icmp", ["$IP_PC04"], "NG"),
             ("mgmt_ping", "icmp", [asw1], "NG"), ("mgmt_telnet", "tcp", [asw1, 23], "CLOSED")]
        if d["inet"]:
            t += [("inet_ip", "http", [f"http://{ISP_DNS}/ip"], re_ip(pri)),
                  ("inet8080", "tcp", [ISP_DNS, 8080], "OPEN"),
                  ("inet445", "tcp", [ISP_DNS, 445], "CLOSED"), ("inet25", "tcp", [ISP_DNS, 25], "CLOSED")]
        else:
            t += [("inet_ip", "http", [f"http://{ISP_DNS}/ip"], "NONE"),
                  ("inet8080", "tcp", [ISP_DNS, 8080], "CLOSED")]
        if d["pc"] == v["probe_pc"]:
            t.append(("big", "big", [f"http://{ISP_DNS}/big.bin"], str(BIG_SIZE)))
        out[d["pc"]] = t
    t = [("dns_portal", "dns", [f"portal.{v['dom']}"], re_ip(v["app"])),
         ("dns_inet", "dns", [f"www.{INET_DOM}"], re_ip(ISP_DNS)),
         ("app80", "tcp", [v["app"], 80], "OPEN"), ("prn", "tcp", [v["prn_ip"], 9100], "OPEN"),
         ("prn_ping", "icmp", [v["prn_ip"]], "OK"),
         ("guest_ping", "icmp", ["$IP_PC05"], "NG"),
         ("inet_ip", "http", [f"http://{ISP_DNS}/ip"], re_ip(pri))]
    for d in v["depts"]:
        t += [(f"ping_{d['pc'].lower()}", "icmp", [f"$IP_{d['pc']}"], "OK"),
              (f"ssh_{d['pc'].lower()}", "tcp", [f"$IP_{d['pc']}", 22], "CLOSED")]
    for sw in ("SW03", "SW04", "SW05"):
        t += [(f"mgmt_ping_{sw.lower()}", "icmp", [v["asw_ip"][sw]], "OK")]
    t += [("mgmt_telnet", "tcp", [asw1, 23], "OPEN")]
    out["PC04"] = t
    out["PC05"] = [("dns_inet", "dns", [f"www.{INET_DOM}"], re_ip(ISP_DNS)),
                   ("dns_corp_at", "dnsat", [v["dns"], f"portal.{v['dom']}"], "NONE"),
                   ("inet_ip", "http", [f"http://{ISP_DNS}/ip"], re_ip(pri)),
                   ("inet443", "tcp", [ISP_DNS, 443], "OPEN"), ("inet8080", "tcp", [ISP_DNS, 8080], "CLOSED"),
                   ("inet_ping", "icmp", [ISP_DNS], "NG"), ("app80", "tcp", [v["app"], 80], "CLOSED"),
                   ("dept_ping", "icmp", ["$IP_PC01"], "NG"), ("prn", "tcp", [v["prn_ip"], 9100], "CLOSED")]
    return out


def re_ip(ip):
    return ip.replace(".", r"\.")


def pc_sh(v):
    tests = pc_tests(v)
    out = {}
    for d in v["depts"]:
        title = f"{d['pc']}: {d['jp']}部の端末（既設・DHCP）"
        out[d["pc"]] = sh_pc(v, d["pc"], [(a, b, c) for a, b, c, _ in tests[d["pc"]]], title)
    out["PC04"] = sh_pc(v, "PC04", [(a, b, c) for a, b, c, _ in tests["PC04"]], "PC04: 情シスの端末（既設・DHCP）")
    out["PC05"] = sh_pc(v, "PC05", [(a, b, c) for a, b, c, _ in tests["PC05"]], "PC05: 来客用端末（既設・DHCP）")
    out["PC06"] = sh_prn(v)
    return out


# =============================================================================
# 模範解（golden: {node: [config 行]}。ent_ops.py solve が telnet で投入）
# =============================================================================
def acl_lines(name, body):
    return [f"ip access-list extended {name}"] + [f" {b}" for b in body]


def golden(v):
    S = v["S"]
    A = v["acl"]
    bodies = acl_bodies(v)
    g = {}
    # DHCP01（予約を先に作る＝動的リースより先。DHCP シリーズの既知の罠）
    L = []
    for s in dhcp_segs(v):
        L.append(f"ip dhcp excluded-address {s['net']}.1 {s['net']}.3")
    L += ["ip dhcp pool PRN01", f" host {v['prn_ip']} 255.255.255.0",
          f" client-identifier {client_id(v['prn_mac'])}", f" default-router {v['print']['net']}.1",
          f" dns-server {v['dns']}", f" domain-name {v['dom']}"]
    for s in dhcp_segs(v):
        L += [f"ip dhcp pool {s['tag']}", f" network {s['net']}.0 255.255.255.0",
              f" default-router {s['net']}.1"]
        if s is v["guest"]:
            L += [f" dns-server {ISP_DNS}", " lease 0 1"]
        else:
            L += [f" dns-server {v['dns']}", f" domain-name {v['dom']}"]
    g["DHCP01"] = L
    # アクセス SW
    for sw in ("SW03", "SW04", "SW05"):
        vl = asw_vlans(v, sw)
        L = []
        for x in sorted(set(vl + [v["native"]])):
            L += [f"vlan {x}"]
        for idx in (0, 1):
            L += [f"interface {L2IF[idx]}", " switchport trunk encapsulation dot1q", " switchport mode trunk",
                  f" switchport trunk native vlan {v['native']}",
                  f" switchport trunk allowed vlan {','.join(str(x) for x in sorted(vl))}", " no shutdown"]
        for idx in (2, 3, 4):
            L += [f"interface {L2IF[idx]}", " switchport mode access",
                  f" switchport access vlan {port_vlan(v, sw, idx)}", " spanning-tree portfast",
                  " spanning-tree bpduguard enable", " no shutdown"]
        L += [f"interface Vlan{v['mgmt']['vlan']}", f" ip address {v['asw_ip'][sw]} 255.255.255.0",
              " no shutdown", f"ip default-gateway {v['mgmt']['net']}.1",
              f"ntp server {v['mgmt']['net']}.2", f"ntp server {v['mgmt']['net']}.3"]
        g[sw] = L
    # L3SW
    for sw, me in (("SW01", 2), ("SW02", 3)):
        L = []
        allv = core_vlans(v)
        for x in sorted(set(allv + [v["native"]])):
            L.append(f"vlan {x}")
        pri = [s["vlan"] for s in segs_all(v) if s["active"] == sw]
        sec = [s["vlan"] for s in segs_all(v) if s["active"] != sw]
        if sw == "SW01":
            pri.append(v["transit"]["vlan"])
        else:
            sec.append(v["transit"]["vlan"])
        L += [f"spanning-tree vlan {','.join(str(x) for x in sorted(pri))} priority 24576",
              f"spanning-tree vlan {','.join(str(x) for x in sorted(sec))} priority 28672", "ip routing"]
        for idx in (0, 1):
            L += [f"interface {L2IF[idx]}", " channel-group 1 mode active", " no shutdown"]
        L += ["interface Port-channel1", " switchport trunk encapsulation dot1q", " switchport mode trunk",
              f" switchport trunk native vlan {v['native']}",
              f" switchport trunk allowed vlan {','.join(str(x) for x in allv)}", " no shutdown"]
        L += [f"interface {L2IF[2]}", " switchport mode access",
              f" switchport access vlan {v['transit']['vlan']}", " no shutdown"]
        for idx, asw in ((3, "SW03"), (4, "SW04"), (5, "SW05")):
            L += [f"interface {L2IF[idx]}", " switchport trunk encapsulation dot1q", " switchport mode trunk",
                  f" switchport trunk native vlan {v['native']}",
                  f" switchport trunk allowed vlan {','.join(str(x) for x in sorted(asw_vlans(v, asw)))}",
                  " no shutdown"]
        for s in segs_all(v):
            L += [f"interface Vlan{s['vlan']}", f" ip address {s['net']}.{me} 255.255.255.0",
                  " standby version 2", f" standby {s['vlan']} ip {s['net']}.1"]
            if s["active"] == sw:
                L.append(f" standby {s['vlan']} priority 110")
            L.append(f" standby {s['vlan']} preempt")
            if s in dhcp_segs(v):
                L.append(f" ip helper-address {v['dhcp']}")
            L += [f" ip access-group {A[s['tag']]} in", " no shutdown"]
        L += [f"interface Vlan{v['transit']['vlan']}", f" ip address {v['tr'][sw]} 255.255.255.248",
              " no shutdown",
              f"router ospf {v['ospf_pid']}", f" router-id {v['tr'][sw]}", " passive-interface default",
              f" no passive-interface Vlan{v['transit']['vlan']}", f" network 10.{S}.0.0 0.0.255.255 area 0",
              f"ntp server {v['tr']['RT01']}", f"ntp server {v['tr']['RT02']}"]
        for s in segs_all(v):
            L += acl_lines(A[s["tag"]], bodies[A[s["tag"]]])
        g[sw] = L
    # 境界 RT
    for key in ("A", "B"):
        i = v["isp"][key]
        rt = i["rt"]
        metric = 10 if key == v["primary"] else 100
        L = ["interface Ethernet0/0", f" ip address {v['tr'][rt]} 255.255.255.248", " ip nat inside",
             f" ip access-group {A['LAN']} in", " no shutdown",
             "interface Ethernet0/1", " no ip address", " pppoe enable group global",
             " pppoe-client dial-pool-number 1", " no shutdown",
             "interface Dialer1", " ip address negotiated", " ip nat outside", f" ip access-group {A['WAN']} in",
             " encapsulation ppp", " dialer pool 1", " ip tcp adjust-mss 1452",
             f" ppp chap hostname {i['user']}", f" ppp chap password 0 {i['pw']}",
             "ip access-list standard NAT-SRC"]
        L += [f" permit {d['net']}.0 0.0.0.255" for d in v["depts"] if d["inet"]]
        L += [f" permit {v['it']['net']}.0 0.0.0.255", f" permit {v['guest']['net']}.0 0.0.0.255",
              f" permit host {v['dns']}"]
        L += ["ip nat inside source list NAT-SRC interface Dialer1 overload",
              "ip sla 1", f" icmp-echo {ISP_DNS} source-interface Dialer1", " frequency 5",
              "ip sla schedule 1 life forever start-time now",
              "track 1 ip sla 1 reachability", " delay down 10 up 30",
              "ip route 0.0.0.0 0.0.0.0 Dialer1 track 1",
              f"ip route {ISP_DNS} 255.255.255.255 Dialer1",
              f"router ospf {v['ospf_pid']}", f" router-id {v['tr'][rt]}",
              f" network {v['transit']['net']}.0 0.0.0.7 area 0",
              f" default-information originate metric {metric} metric-type 1",
              f"ntp server {ISP_NTP}"]
        L += acl_lines(A["WAN"], bodies[A["WAN"]]) + acl_lines(A["LAN"], lan_in_body(v, rt))
        g[rt] = L
    return g


# =============================================================================
# 採点
# =============================================================================
def chk(name, node, command, raw, points, exec_=None):
    c = {"name": name, "node": node, "command": command, "raw": raw, "points": points}
    if exec_:
        c["exec"] = exec_
    return c


def probe_raw(pairs):
    return [{"regex": rf"(?m)^{k}={val}\s*$"} for k, val in pairs]




def normalize(C):
    """配点を合計 100 に正規化（最大剰余法・各チェック最低 1 点）。"""
    raw_total = sum(c["points"] for c in C)
    exact = [c["points"] * 100 / raw_total for c in C]
    pts = [max(1, int(x)) for x in exact]
    rem = 100 - sum(pts)
    order = sorted(range(len(C)), key=lambda i: exact[i] - int(exact[i]), reverse=True)
    k = 0
    while rem != 0:
        i = order[k % len(order)]
        if rem > 0:
            pts[i] += 1
            rem -= 1
        elif pts[i] > 1:
            pts[i] -= 1
            rem += 1
        k += 1
    for c, p in zip(C, pts):
        c["points"] = p


def grading(v, prob_id):
    A = v["acl"]
    P = "sudo -n /usr/local/bin/ccnp-probe"
    exp = {pc: {tid: e for tid, _, _, e in t} for pc, t in pc_tests(v).items()}
    pri = v["isp"][v["primary"]]["pub"]
    bak = v["isp"][v["backup"]]["pub"]
    vec = vectors(v)
    C = []
    # ---- A: PPPoE（10） ----
    for key in ("A", "B"):
        i = v["isp"][key]
        C.append(chk(f"{i['rt']}: {i['name']} と PPPoE を確立し Dialer1 に払い出しアドレス ({i['pub']})", i["rt"],
                     "show ip interface brief | include Dialer", [{"regex": rf"Dialer1\s+{re_ip(i['pub'])}\s+\S+\s+\S+\s+up\s+up"}],
                     5))
    # ---- B: 回線冗長（採点前フックの結果・15） ----
    fo, pp = "cat /var/tmp/ccnp-failover.txt", v["probe_pc"]
    C.append(chk("冗長: 平常時は主回線から出る (送信元 = 主回線のアドレス)", pp, fo,
                 [{"regex": rf"(?m)^BASE={re_ip(pri)}\s*$"}], 4, "shell"))
    C.append(chk("冗長: 主回線の ISP 網内障害 (PPPoE は維持) で予備回線へ切り替わる", pp, fo,
                 [{"regex": rf"(?m)^BASE={re_ip(pri)}\s*$"}, {"regex": rf"(?m)^FAIL={re_ip(bak)}\s*$"}], 6, "shell"))
    C.append(chk("冗長: 主回線の復旧後に主回線へ戻る", pp, fo,
                 [{"regex": rf"(?m)^FAIL={re_ip(bak)}\s*$"}, {"regex": rf"(?m)^BACK={re_ip(pri)}\s*$"}], 5, "shell"))
    # ---- C: DHCP（10） ----
    for s in dhcp_segs(v):
        pc = s["pc"]
        raw = [{"regex": rf"(?m)^addr={re_ip(s['net'])}\.\d+/24\s*$"},
               {"regex": rf"(?m)^ROUTER={re_ip(s['net'])}\.1\s*$"}]
        if s is v["guest"]:
            raw += [{"regex": rf"(?m)^DNS={re_ip(ISP_DNS)}\s*$"}, {"not_regex": r"(?m)^DOMAINNAME="}]
            nm = f"DHCP: 来客 ({pc}) = アドレス・既定 GW (仮想)・DNS=ISP の DNS・ドメイン名なし"
        elif s is v["print"]:
            raw[0] = {"regex": rf"(?m)^addr={re_ip(v['prn_ip'])}/24\s*$"}
            raw += [{"regex": rf"(?m)^DNS={re_ip(v['dns'])}\s*$"}]
            nm = f"DHCP: 複合機 ({pc}) = 予約アドレス {v['prn_ip']}・既定 GW (仮想)・DNS"
        else:
            raw += [{"regex": rf"(?m)^DNS={re_ip(v['dns'])}\s*$"},
                    {"regex": rf"(?m)^DOMAINNAME={re_ip(v['dom'])}\s*$"}]
            nm = f"DHCP: {s['jp']} ({pc}) = アドレス・既定 GW (仮想)・DNS=社内 DNS・ドメイン名"
        C.append(chk(nm, pc, P, raw, 1.4 if s is not v["print"] else 2, "shell"))
    C.append(chk("DHCP: 仮想アドレスと L3SW の実アドレスを配布対象から除外", "DHCP01",
                 "show running-config | include excluded-address",
                 [{"regex": rf"ip dhcp excluded-address {re_ip(s['net'])}\.1 {re_ip(s['net'])}\.(?:[3-9]|\d\d+)\b"}
                  for s in dhcp_segs(v)], 1))
    # ---- D/E/F: 端末からの疎通（プローブ・30） ----
    for d in v["depts"]:
        pc, e = d["pc"], exp[d["pc"]]
        C.append(chk(f"{d['jp']} ({pc}): 社内 DNS で社内名・外部名を解決でき、外部の DNS へは直接問い合わせない", pc, P,
                     probe_raw([("dns_portal", e["dns_portal"]), ("dns_inet", e["dns_inet"]),
                                ("dns_direct", "NONE")]), 2.5, "shell"))
        allow = [("app80", "OPEN"), ("app445", "OPEN"), ("srv_ping", "OK"), ("prn", "OPEN")]
        deny = [("app3389", "CLOSED"), ("peer_ping", "NG"), ("peer_ssh", "CLOSED"), ("it_ping", "NG"),
                ("mgmt_ping", "NG"), ("mgmt_telnet", "CLOSED")]
        if d["inet"]:
            allow += [("inet_ip", e["inet_ip"]), ("inet8080", "OPEN")]
            deny += [("inet445", "CLOSED"), ("inet25", "CLOSED")]
            lbl = "インターネット (主回線)"
        else:
            deny += [("inet_ip", "NONE"), ("inet8080", "CLOSED")]
            lbl = "イントラのみ"
        C.append(chk(f"{d['jp']} ({pc}): 許可された通信 (社内サーバ・複合機{'' if not d['inet'] else '・' + lbl})", pc, P,
                     probe_raw(allow), 3, "shell"))
        C.append(chk(f"{d['jp']} ({pc}): 遮断すべき通信 (他部門・情シス・機器管理・許可外サービス"
                     f"{'・危険ポート' if d['inet'] else '・インターネット'}) が通らない", pc, P,
                     probe_raw(deny + allow[:1]), 4, "shell"))
    e = exp["PC04"]
    C.append(chk("情シス (PC04): 名前解決・インターネット・全業務部門/複合機/機器管理 VLAN への ping と telnet", "PC04", P,
                 probe_raw([("dns_portal", e["dns_portal"]), ("dns_inet", e["dns_inet"]), ("inet_ip", e["inet_ip"]),
                            ("app80", "OPEN"), ("prn", "OPEN"), ("prn_ping", "OK"), ("mgmt_telnet", "OPEN")] +
                           [(f"ping_{d['pc'].lower()}", "OK") for d in v["depts"]] +
                           [(f"mgmt_ping_{sw.lower()}", "OK") for sw in ("SW03", "SW04", "SW05")]), 4, "shell"))
    C.append(chk("情シス (PC04): 業務部門へは ping 以外通らず、来客 VLAN とは通信しない", "PC04", P,
                 probe_raw([(f"ssh_{d['pc'].lower()}", "CLOSED") for d in v["depts"]] +
                           [("guest_ping", "NG"), (f"ping_{v['depts'][0]['pc'].lower()}", "OK")]), 2, "shell"))
    e = exp["PC05"]
    C.append(chk("来客 (PC05): ISP の DNS で名前解決し Web (HTTP/HTTPS) を利用できる", "PC05", P,
                 probe_raw([("dns_inet", e["dns_inet"]), ("inet_ip", e["inet_ip"]), ("inet443", "OPEN")]), 2.5, "shell"))
    C.append(chk("来客 (PC05): Web/DNS 以外のインターネット通信と、社内への通信が一切通らない", "PC05", P,
                 probe_raw([("inet8080", "CLOSED"), ("inet_ping", "NG"), ("app80", "CLOSED"), ("dns_corp_at", "NONE"),
                            ("dept_ping", "NG"), ("prn", "CLOSED"), ("inet443", "OPEN")]), 3, "shell"))
    # ---- G: 境界（10） ----
    C.append(chk("境界: インターネットから自社グローバルアドレスへの新規接続・ping に応答しない", pp, fo,
                 [{"regex": rf"(?m)^BASE=(?:{re_ip(pri)}|{re_ip(bak)})\s*$"}, {"regex": r"(?m)^EXT=CLOSED\s*$"}], 4, "shell"))
    C.append(chk("境界: 大きなファイルの TCP 転送がタイムアウトしない (PMTUD が効かない経路でも)", pp, P,
                 probe_raw([("big", str(BIG_SIZE))]), 6, "shell"))
    # ---- H: L2/L3（15） ----
    for sw in ("SW01", "SW02"):
        mine = [s for s in segs_all(v) if s["active"] == sw]
        C.append(chk(f"{sw}: 担当 VLAN で HSRP Active かつ STP ルートブリッジ", sw, "show standby brief",
                     [{"regex": rf"(?m)^Vl{s['vlan']}\s+{s['vlan']}\s+\d+\s+\S*\s*Active\s+local"} for s in mine], 1))
        roots = mine + ([v["transit"]] if sw == "SW01" else [])
        C.append(chk(f"{sw}: 担当 VLAN の STP ルートブリッジ", sw, "show spanning-tree root",
                     [{"regex": rf"(?m)^VLAN{s['vlan']:04d}\s+\d+\s+\S+\s+0\s+\d+\s+\d+\s+\d+\s*$"} for s in roots], 1))
        C.append(chk(f"{sw}: L3SW 間の 2 本を LACP で束ねている (Po1)", sw, "show etherchannel summary",
                     [{"regex": r"Po1\(SU\)\s+LACP\s+Et0/0\(P\)\s+Et0/1\(P\)"}], 0.8))
        tr = [("Po1", core_vlans(v))] + [(L2IF[i].replace("Ethernet", "Et"), asw_vlans(v, a))
                                         for i, a in ((3, "SW03"), (4, "SW04"), (5, "SW05"))]
        raw = []
        for port, vl in tr:
            raw += [{"regex": rf"(?m)^{port}\s+\S+\s+802\.1q\s+trunking\s+{v['native']}\b"},
                    {"regex": rf"(?m)Vlans allowed on trunk[\s\S]*?^{port}\s+{vlan_list_str(vl)}\s*$"}]
        C.append(chk(f"{sw}: トランクのネイティブ VLAN・許可 VLAN が要件どおり", sw, "show interfaces trunk", raw, 0.8))
        C.append(chk(f"{sw}: 利用者側の SVI では OSPF の hello を出さない", sw, "show ip protocols | section ospf",
                     [{"regex": rf"Passive Interface\(s\):[\s\S]*\bVlan{s['vlan']}\b"} for s in segs_all(v)], 0.6))
        C.append(chk(f"{sw}: NTP サーバとして RT を設定", sw, "show ntp associations",
                     [{"regex": rf"~{re_ip(v['transit']['net'])}\.[12]\s"}], 0.5))
    for sw in ("SW03", "SW04", "SW05"):
        vl = asw_vlans(v, sw)
        lab = ASW[sw]["label"]
        raw = []
        for port in ("Et0/0", "Et0/1"):
            raw += [{"regex": rf"(?m)^{port}\s+\S+\s+802\.1q\s+trunking\s+{v['native']}\b"},
                    {"regex": rf"(?m)Vlans allowed on trunk[\s\S]*?^{port}\s+{vlan_list_str(vl)}\s*$"}]
        C.append(chk(f"{sw} ({lab}): アップリンクのトランクが要件どおり", sw, "show interfaces trunk", raw, 0.6))
        raw = []
        for idx in (2, 3, 4):
            blk = rf"interface {L2IF[idx]}\s*\n(?:[ \t][^\n]*\n)*?"
            raw += [{"regex": blk + rf"[ \t]switchport access vlan {port_vlan(v, sw, idx)}\s*\n"},
                    {"regex": blk + r"[ \t]spanning-tree portfast"},
                    {"regex": blk + r"[ \t]spanning-tree bpduguard enable"}]
        C.append(chk(f"{sw} ({lab}): 端末側ポートの VLAN とエッジ保護 (PortFast + BPDU ガード)", sw,
                     "show running-config | section ^interface Ethernet", raw, 0.6))
        C.append(chk(f"{sw} ({lab}): NTP サーバとして L3SW (MGMT VLAN) を設定", sw, "show ntp associations",
                     [{"regex": rf"~{re_ip(v['mgmt']['net'])}\.[23]\s"}], 0.6))
    for key in ("A", "B"):
        rt = v["isp"][key]["rt"]
        C.append(chk(f"{rt}: L3SW 2 台と OSPF 隣接 (トランジット VLAN)", rt, "show ip ospf neighbor",
                     [{"regex": rf"FULL/\S*\s+\S+\s+{re_ip(v['tr']['SW01'])}\s"},
                      {"regex": rf"FULL/\S*\s+\S+\s+{re_ip(v['tr']['SW02'])}\s"}], 1))
        C.append(chk(f"{rt}: NTP サーバとして ISP の NTP を設定", rt, "show ntp associations",
                     [{"regex": rf"~{re_ip(ISP_NTP)}\s"}], 0.5))
    # ---- I: ACL（命名規約・適用位置・意味評価・15） ----
    for sw in ("SW01", "SW02"):
        C.append(chk(f"{sw}: 各 SVI の受信方向に命名規約どおりの ACL を適用", sw,
                     "show ip interface | include line protocol|Inbound  access list",
                     [{"regex": rf"(?m)^Vlan{s['vlan']} is up[^\n]*\n\s*Inbound\s+access list is {A[s['tag']]}\s*$"}
                      for s in segs_all(v)], 1))
        c = chk(f"{sw}: VLAN 間 ACL の許可/拒否が要件どおり (意味評価・{len(segs_all(v))} 本)", sw,
                "show ip access-lists", [], 3)
        del c["raw"]
        c["acl_vectors"] = {"acls": [{"acl": A[s["tag"]], "vectors": vec[s["tag"]]} for s in segs_all(v)]}
        C.append(c)
    for key in ("A", "B"):
        rt = v["isp"][key]["rt"]
        C.append(chk(f"{rt}: Dialer1 の受信方向に {A['WAN']}・Et0/0 の受信方向に {A['LAN']}", rt,
                     "show ip interface | include line protocol|Inbound  access list",
                     [{"regex": rf"(?m)^Dialer1 is up[^\n]*\n\s*Inbound\s+access list is {A['WAN']}\s*$"},
                      {"regex": rf"(?m)^Ethernet0/0 is up[^\n]*\n\s*Inbound\s+access list is {A['LAN']}\s*$"}], 1))
        c = chk(f"{rt}: 境界 ACL ({A['WAN']}/{A['LAN']}) の許可/拒否が要件どおり (意味評価)", rt,
                "show ip access-lists", [], 3)
        del c["raw"]
        c["acl_vectors"] = {"acls": [{"acl": A["WAN"], "vectors": vec[f"WAN:{rt}"]},
                                     {"acl": A["LAN"], "vectors": vec[f"LAN:{rt}"]}]}
        C.append(c)
    for c in C:
        if c["node"] in SWS:
            c["via"] = "console"
    normalize(C)
    return {"problem": prob_id, "total_points": 100, "defaults": {"genie_os": "iosxe"}, "checks": C}


# =============================================================================
# 要件書（task.md）
# =============================================================================
def task(v, prob_id):
    A = v["acl"]
    S = v["S"]
    pri, bak = v["isp"][v["primary"]], v["isp"][v["backup"]]
    rows = []
    for s in segs_all(v):
        role = {"IT": "情シス（管理者）", "GUEST": "来客", "PRINT": "複合機", "SERVER": "サーバ",
                "MGMT": "機器管理（スイッチの管理アドレス）"}.get(s["tag"], f"{s['jp']}部")
        inet = ("—" if s["tag"] in ("SERVER", "MGMT", "PRINT") else
                ("Web・DNS のみ" if s["tag"] == "GUEST" else ("◯" if s.get("inet", True) else "✕（イントラのみ）")))
        rows.append(f"| {s['vlan']} | {s['tag']} | {role} | `{s['net']}.0/24` | `.1` | {s['active']} | {inet} | `{A[s['tag']]}` |")
    rows.append(f"| {v['transit']['vlan']} | TRANSIT | L3SW⇔RT | `{v['transit']['net']}.0/29` | — | — | — | （ACL なし） |")
    vtable = "\n".join(rows)
    dpt = "・".join(f"{d['jp']}部（{d['pc']}）" for d in v["depts"])
    intra = next(d for d in v["depts"] if not d["inet"])
    pp = "・".join(f"TCP {p}" for p in v["print_ports"])
    asw_tbl = "\n".join(
        f"| {sw}（{ASW[sw]['label']}） | {', '.join(f'{L2IF[i]}→{n}' for i, n in zip((2, 3, 4), ASW[sw]['pcs']))} "
        f"| `{v['asw_ip'][sw]}` |" for sw in ("SW03", "SW04", "SW05"))
    mat = [f"| {d['jp']}部 | ✕ | DNS | Web・ファイル | 印刷 | ✕ | {'◯（危険ポートを除く）' if d['inet'] else '✕'} |"
           for d in v["depts"]]
    mat += ["| 情シス | ping のみ | DNS | Web・ファイル | 印刷・ping | ping・telnet | ◯（危険ポートを除く） |",
            "| 来客 | ✕ | ✕ | ✕ | ✕ | ✕ | Web（HTTP/HTTPS）と ISP の DNS のみ |",
            "| 複合機 | 戻りのみ | ✕ | ✕ | — | ✕ | ✕ |",
            "| サーバ | 戻りのみ | — | — | ✕ | ✕ | 社内 DNS サーバから ISP の DNS への問い合わせのみ |",
            "| 機器管理 | 情シスへの戻りのみ | ✕ | ✕ | ✕ | — | ✕ |"]
    matrix = "\n".join(mat)
    return f"""# 問題 {prob_id} : エンタープライズ拠点ネットワーク構築（要件書駆動・難易度5）

## シナリオ

あなたは、新設拠点のネットワーク構築を担当するネットワークエンジニアです。
拠点には {dpt}、情シス、来客用、複合機、サーバの各セグメントを設けます。
インターネットへは 2 つの ISP の PPPoE 回線で接続し、一方を主回線、他方を予備回線として運用します。
下記の **要件書** に従って、L3 スイッチ・アクセススイッチ・境界ルータ・DHCP サーバを構築してください。

ISP 側の機器、インターネット上のサーバ、社内サーバ（DNS・Web）、および各端末は **設置済み** です。
これらの設定を変更することはできません。端末は DHCP でアドレスを取得するよう設定されています。
要件書に記載のない事項は、要件を満たす範囲であなたが決めてよいものとします。
ログインユーザ・AAA・機器への管理アクセスの制限は、本件の範囲外とします。

## トポロジ

```
                 SRVINET (192.0.2.10: ISP の DNS / Web)
                     |  192.0.2.0/24
                   INET (192.0.2.1: ISP の NTP)
                  /                  \\
           ISPA (ISP-A)          ISPB (ISP-B)          ← PPPoE サーバ（設置済み）
              | PPPoE Et0/1          | PPPoE Et0/1
            RT01 ──────┐        ┌── RT02               ← 境界ルータ（構築対象）
              Et0/0    └─TRANSIT┘   Et0/0
                SW01 Et0/2          SW02 Et0/2         ← L3 スイッチ（構築対象）
                SW01 ═══ Et0/0・Et0/1 ═══ SW02
        Et0/3 → SW03（ASW01）  Et1/0 → SW04（ASW02）  Et1/1 → SW05（SRVSW）
          （SW03〜SW05 の Et0/0 は SW01、Et0/1 は SW02 へ接続）
```

| アクセススイッチ | 端末側ポート | 管理アドレス（MGMT VLAN） |
|---|---|---|
{asw_tbl}

- 端末: PC01〜PC03 = {dpt} / PC04 = 情シス / PC05 = 来客用端末 / PC06 = 複合機
- サーバ: SRV01 = 社内 DNS（`{v['dns']}`・設置済み）/ SRV02 = 社内 Web・ファイルサーバ（`{v['app']}`・設置済み）/
  DHCP01 = DHCP サーバ専用ルータ（`{v['dhcp']}`・IF アドレスと既定経路のみ設定済み。**DHCP の設定は構築対象**）
- 構築対象: **RT01・RT02・SW01〜SW05・DHCP01（DHCP 機能）**

## アドレス・VLAN 計画

各 VLAN の既定ゲートウェイは仮想アドレス `.1`、SW01 の実アドレスは `.2`、SW02 の実アドレスは `.3` とする。

| VLAN | 名前 | 用途 | サブネット | GW | 主系（Active/ルート） | インターネット | ACL 名 |
|---|---|---|---|---|---|---|---|
{vtable}

- TRANSIT: RT01 = `{v['tr']['RT01']}`、RT02 = `{v['tr']['RT02']}`、SW01 = `{v['tr']['SW01']}`、SW02 = `{v['tr']['SW02']}`（/29）
- トランクのネイティブ VLAN は **{v['native']}**（どのアクセスポートにも割り当てない）

## 支給情報

| 回線 | 接続ルータ | PPPoE 認証 ID | パスワード（CHAP） | 払い出しアドレス |
|---|---|---|---|---|
| ISP-A | RT01（Et0/1） | `{v['isp']['A']['user']}` | `{v['isp']['A']['pw']}` | IPCP で払い出し（固定） |
| ISP-B | RT02（Et0/1） | `{v['isp']['B']['user']}` | `{v['isp']['B']['pw']}` | IPCP で払い出し（固定） |

- **主回線は {pri['name']}（{pri['rt']}）、予備回線は {bak['name']}（{bak['rt']}）** とする。
- ISP の DNS サーバ: `{ISP_DNS}` ／ ISP の NTP サーバ: `{ISP_NTP}` ／ 回線の監視対象: `{ISP_DNS}`
- 社内ドメイン名: `{v['dom']}`（社内 DNS SRV01 が権威を持ち、社外の名前は ISP の DNS へ転送する設定済み）
- 社内 Web・ファイルサーバ（SRV02）の提供サービス: Web（TCP 80・443）、ファイル共有（TCP 445）
- 複合機（PC06）の MAC アドレス: `{v['prn_mac']}`（印刷は {pp}）

## 要件書

### 1. L2

1. 各スイッチに必要な VLAN を作成すること。L2 の冗長は **Rapid PVST+** で構成すること（スタックは使用しない）。
2. SW01 と SW02 の間の 2 本は、**LACP** で 1 本の論理リンク（Port-channel1）に束ねること。
3. スイッチ間はすべてトランクとし、各トランクで許可する VLAN は **そのリンクの先で必要な VLAN のみ** とすること。
   SW01—SW02 間は上表の全 VLAN（TRANSIT を含む）、L3 スイッチ—アクセススイッチ間は
   そのアクセススイッチ配下の VLAN と MGMT VLAN とする。
4. 各 VLAN の **STP ルートブリッジは、上表の「主系」の L3 スイッチ** とすること（TRANSIT は SW01）。
   もう一方の L3 スイッチを、その VLAN の第 2 候補とすること。
5. 端末・サーバ・DHCP01 を接続するポートは、リンクアップ後ただちに転送を開始し、
   BPDU を受信した場合はポートを停止すること。
6. アクセススイッチには MGMT VLAN の管理アドレス（上表）を設定し、他のサブネットと通信できるようにすること。

### 2. L3・ゲートウェイの冗長

1. 各 VLAN（TRANSIT を除く）の既定ゲートウェイは、SW01 と SW02 で **HSRP バージョン 2** により冗長化すること。
   **Active は上表の「主系」** とし、障害から復旧した場合は主系へ戻ること。
2. L3 スイッチと境界ルータは TRANSIT VLAN で接続し、経路は **OSPF（エリア 0）** で交換すること。
   利用者側の SVI（TRANSIT 以外）からは OSPF の hello を送信しないこと。
3. 既定経路は境界ルータから OSPF で広告すること。**主回線のルータの既定経路を優先**すること。

### 3. インターネット接続

1. RT01・RT02 は、それぞれの ISP と **PPPoE** で接続すること（インタフェースは **Dialer1**）。
2. インターネットへ出る通信は、**その回線の払い出しアドレス 1 つに変換（PAT）** すること。
   変換の対象は、インターネットを利用してよい VLAN・来客 VLAN・社内 DNS サーバのみとする。
3. 回線の監視対象（`{ISP_DNS}`）に到達できなくなった場合は、**PPPoE セッションが維持されていても**
   その回線の既定経路を取り下げ、予備回線へ切り替えること（通信断は 60 秒以内）。
   主回線が回復した場合は、主回線へ戻ること。
4. インターネット上には、ICMP（到達不能通知）を通さない経路が存在する。
   **大きなファイルの TCP 転送がタイムアウトしないこと。**

### 4. 通信要件

| 送信元＼宛先 | 他部門 | 社内 DNS | Web・ファイル | 複合機 | 機器管理 | インターネット |
|---|---|---|---|---|---|---|
{matrix}

- 社内サーバ（SRV01・SRV02・DHCP01）への ping は、業務部門と情シスから許可する。
- 「危険ポート」= TCP 25・135〜139・445、UDP 137〜139。インターネットへ送出しないこと。
- 業務部門と情シスは **社内 DNS のみ** を使用し、インターネットの DNS へ直接問い合わせないこと。
  来客 VLAN は **ISP の DNS のみ** を使用すること。
- 機器管理 VLAN のスイッチは、NTP で L3 スイッチ（MGMT VLAN の `.2`・`.3`）に同期する。
- 各 VLAN の DHCP（DHCP01）と、ゲートウェイの冗長（HSRP）が機能すること。

### 5. ACL の設計ルール

1. VLAN 間の通信制御は、**L3 スイッチの各 SVI の受信方向**に、送信元 VLAN ごとの拡張 ACL を
   適用して行うこと（SW01・SW02 とも同じ内容）。ACL 名は上表の「ACL 名」とする（命名規約 `{v['acl_style']}`）。
2. インターネットとの境界の制御は、境界ルータで次の 2 つの ACL により行うこと（RT01・RT02 とも）。
   - **`{A['WAN']}`**（Dialer1 の受信方向）: インターネットから受け入れるのは、社内から開始した TCP の戻り、
     ISP の DNS・NTP からの UDP の応答、ICMP のうちエコー応答・到達不能・時間超過のみとする。
     送信元が私設アドレス（RFC 1918）またはループバック（127.0.0.0/8）のパケットは受け入れない。
   - **`{A['LAN']}`**（Et0/0 の受信方向）: インターネットへ送出してよい送信元は、上表でインターネット可の VLAN・
     来客 VLAN・社内 DNS サーバ（DNS のみ）に限る。境界ルータの機能に必要な通信は妨げないこと。
3. ACL はすべて **必要な通信だけを許可** するものとし、それ以外は拒否すること。
   ステートフルなフィルタは使用しない（戻り通信は ACL の条件で許可する）。

### 6. DHCP

1. DHCP サーバは **DHCP01** とし、各 VLAN の要求は L3 スイッチが中継すること。
2. 配布対象: 業務部門・情シス・来客・複合機の各 VLAN。仮想アドレスと L3 スイッチの実アドレス（`.1`〜`.3`）は配布しないこと。
3. 配布する情報: 既定ゲートウェイ（仮想アドレス）、DNS サーバ（社内 DNS `{v['dns']}`）、ドメイン名（`{v['dom']}`）。
   **来客 VLAN** は DNS サーバを ISP の DNS（`{ISP_DNS}`）とし、ドメイン名は配布せず、リース期間は **1 時間** とすること。
4. 複合機（PC06）には、常に **`{v['prn_ip']}`** を割り当てること（上記の MAC アドレスで識別する）。

### 7. NTP

- RT01・RT02 は ISP の NTP サーバに、SW01・SW02 は RT01・RT02 に、アクセススイッチは L3 スイッチに同期すること。

### 8. 制約

- 設置済みの機器（INET・ISPA・ISPB・SRVINET・SRV01・SRV02・PC01〜PC06）は変更しない。DHCP01 の IF アドレスと既定経路も変更しない。
- ルータの管理用インタフェース（Et0/3）には触れないこと（採点用）。

## アクセス・採点

CML コンソール（`SUZUKI / CCNP`）。**スイッチには管理用インタフェースがないため、操作はコンソールのみ**。
ルータは telnet でも可（mgmt は割当順）。
```
scripts/lab.sh grade {prob_id}
```
> 採点では、端末からの実際の通信（名前解決・許可/遮断・大容量転送）、DHCP の取得内容、回線の切替と切り戻し、
> L2/L3 の状態、ACL の内容を確認します。採点の最初に **回線切替の試験（約 3 分）** を行います。
"""


# =============================================================================
# 書き出し・selftest
# =============================================================================
def lab_def(v):
    links = [
        {"a": "SW01", "a_if": 0, "b": "SW02", "b_if": 0}, {"a": "SW01", "a_if": 1, "b": "SW02", "b_if": 1},
        {"a": "SW01", "a_if": 2, "b": "RT01", "b_if": 0}, {"a": "SW02", "a_if": 2, "b": "RT02", "b_if": 0},
        {"a": "SW01", "a_if": 3, "b": "SW03", "b_if": 0}, {"a": "SW02", "a_if": 3, "b": "SW03", "b_if": 1},
        {"a": "SW01", "a_if": 4, "b": "SW04", "b_if": 0}, {"a": "SW02", "a_if": 4, "b": "SW04", "b_if": 1},
        {"a": "SW01", "a_if": 5, "b": "SW05", "b_if": 0}, {"a": "SW02", "a_if": 5, "b": "SW05", "b_if": 1},
        {"a": "RT01", "a_if": 1, "b": "ISPA", "b_if": 0}, {"a": "RT02", "a_if": 1, "b": "ISPB", "b_if": 0},
        {"a": "ISPA", "a_if": 1, "b": "INET", "b_if": 0}, {"a": "ISPB", "a_if": 1, "b": "INET", "b_if": 1},
        {"a": "INET", "a_if": 2, "b": "SRVINET", "b_if": 1}]
    for sw, info in ASW.items():
        for idx, n in zip((2, 3, 4), info["pcs"]):
            links.append({"a": sw, "a_if": idx, "b": n, "b_if": 0 if n == "DHCP01" else 1})
    pos = {"SRVINET": [300, -620], "INET": [0, -620], "ISPA": [-260, -480], "ISPB": [260, -480],
           "RT01": [-260, -340], "RT02": [260, -340], "SW01": [-260, -180], "SW02": [260, -180],
           "SW03": [-520, 0], "SW04": [0, 0], "SW05": [520, 0],
           "PC01": [-680, 180], "PC02": [-520, 180], "PC03": [-360, 180],
           "PC04": [-160, 180], "PC05": [0, 180], "PC06": [160, 180],
           "SRV01": [360, 180], "SRV02": [520, 180], "DHCP01": [680, 180]}
    return {"links": links, "positions": pos, "macs": {"PC06": {1: v["prn_mac"]}}}


def write_problem(repo, seed):
    v = build_values(seed)
    prob_id = f"GEN-ENT-{seed}"
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {
        "id": prob_id, "title": f"エンタープライズ拠点ネットワーク構築 (要件書駆動・seed={seed})",
        "exam": "ENCOR",
        "topics": ["vlan", "stp", "etherchannel", "hsrp", "ospf", "acl", "security", "nat", "pppoe",
                   "ip-sla", "dhcp", "dns", "ntp", "build", "generated"],
        "difficulty": 5, "topology": "generated",
        "target_nodes": IOS_R + SWS + LINUX, "points": 100, "access": "telnet",
        "bringup_data_ifs": True, "bringup_nodes": IOS_R,
        # スイッチは管理 IF/SVI を持たない（採点・模範解の投入は CML コンソール経由）
        "console_nodes": SWS,
        "node_image_families": {n: "ubuntu" for n in LINUX},
        "pre_grade": "topologies/ent_ops.py",
        "lab": lab_def(v)}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_enterprise.py) seed={seed} primary=ISP-{v['primary']} "
                f"intra={next(d['tag'] for d in v['depts'] if not d['inet'])}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    ios = {"INET": init_inet(v), "ISPA": init_bras(v, "A"), "ISPB": init_bras(v, "B"),
           "DHCP01": init_dhcp01(v), "RT01": init_blank_rt("RT01"), "RT02": init_blank_rt("RT02")}
    for sw in SWS:
        # 実機 Catalyst の既定（IP ルーティング無効）に合わせる。ioll2 の既定は有効なので明示的に切る。
        # 管理 IF を持たない（problem.yml の console_nodes）ので、SVI は業務用だけ＝実機と同じ構成。
        ios[sw] = [f"! {sw} 初期状態（白紙・実機の既定に合わせて IP ルーティング無効）", "no ip routing", "!"]
    for node, lines in ios.items():
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    shs = {"SRVINET": sh_srvinet(v), "SRV01": sh_dns(v), "SRV02": sh_app(v), **pc_sh(v)}
    for node in LINUX:
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("# server ノードは baseline_server.cfg.j2 が全て描画（このスタブは連結対策の空ファイル）\n")
        with open(f"{pdir}/initial/{node}.sh.j2", "w", encoding="utf-8") as f:
            f.write(shs[node])
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_enterprise.py) seed={seed}\n"
                "# telnet 収集(IOS)+ssh(Linux 端末のプローブ)。回線切替は採点前フック(ent_ops.py)の結果を読む。\n")
        yaml.safe_dump(grading(v, prob_id), f, sort_keys=False, allow_unicode=True)
    spec = {k: v[k] for k in ("seed", "S", "primary", "backup", "probe_pc", "dns", "app", "dhcp", "prn_ip",
                              "prn_mac", "dom", "asw_ip", "tr", "native", "acl")}
    spec["isp"] = {k: {"rt": x["rt"], "pub": x["pub"], "name": x["name"]} for k, x in v["isp"].items()}
    spec["pcs"] = {s["pc"]: s["tag"] for s in dhcp_segs(v)}
    with open(f"{pdir}/solution/spec.json", "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/golden.json", "w", encoding="utf-8") as f:
        json.dump(golden(v), f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task(v, prob_id))
    print(f"wrote problems/{prob_id} : primary=ISP-{v['primary']} S={v['S']} "
          f"depts={[d['tag'] + ('' if d['inet'] else '(intra)') for d in v['depts']]} acl={v['acl_style']}")
    return prob_id


def _acl_model():
    spec = importlib.util.spec_from_file_location("acl_model", os.path.join(HERE, "acl_model.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def selftest(n):
    am = _acl_model()
    bad = 0
    for seed in range(1, n + 1):
        v = build_values(seed)
        errs = []
        vids = [s["vlan"] for s in segs_all(v)] + [v["transit"]["vlan"], v["native"]]
        if len(set(vids)) != len(vids) or 999 in vids or 1 in vids:
            errs.append(f"VLAN 重複/予約 {vids}")
        bodies = acl_bodies(v)
        for key in ("A", "B"):
            bodies[f"LAN:{v['isp'][key]['rt']}"] = lan_in_body(v, v["isp"][key]["rt"])
        vec = vectors(v)
        for tag, vv in vec.items():
            if ":" in tag:
                kind, rt = tag.split(":")
                body = bodies[v["acl"]["WAN"]] if kind == "WAN" else bodies[f"LAN:{rt}"]
                name = v["acl"][kind]
            else:
                name = v["acl"][tag]
                body = bodies[name]
            text = f"Extended IP access list {name}\n" + "".join(
                f"    {10 * (i + 1)} {b}\n" for i, b in enumerate(body))
            ok, det = am.eval_acl_vectors({"acl": name, "vectors": vv}, text)
            if not ok:
                errs.append(f"{tag}: {det}")
        g = grading(v, f"GEN-ENT-{seed}")
        pts = [c["points"] for c in g["checks"]]
        if sum(pts) != 100 or min(pts) < 1:
            errs.append(f"配点 sum={sum(pts)} min={min(pts)}")
        gold = golden(v)
        for node in ("RT01", "RT02", "SW01", "SW02", "SW03", "SW04", "SW05", "DHCP01"):
            if node not in gold:
                errs.append(f"golden に {node} が無い")
        if errs:
            bad += 1
            if bad <= 5:
                print(f"seed {seed}: " + " / ".join(errs)[:600])
    print(f"selftest: {n} seeds, NG={bad}, checks={len(grading(build_values(1), 'x')['checks'])}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--selftest", type=int)
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if selftest(a.selftest) else 0)
    if a.seed is None:
        ap.error("--seed か --selftest が必要")
    write_problem(a.repo, a.seed)


if __name__ == "__main__":
    main()
