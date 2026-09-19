#!/usr/bin/env python3
"""DHCPv6/SLAAC モード 紙面ファミリ (BL-178) — gen_paper_mcq.py の shape=dhcp6 素材。

設計= 非公開側の計画メモ(2026-09-18) §3 A3 / 実出力の正典= poc/paper-kb/results-raw.md P5(iol-xe 17.15.1)。
kinds:
  mode    (瞬発) 3 モード(SLAAC / ステートレス DHCPv6 / ステートフル DHCPv6)×穴の位置を抽選し、
          サーバ側【1】・クライアント側【2】の組合せ(select)・追加すべき 2 行(select2)・client の show の読解(read)。
  trouble (思考) GUA または DNS が取れない 6 原因(unicast-routing 欠落 / RA suppress / IPv6 ACL が LL 送信元の RA を落とす /
          M flag なのにプールにプレフィックス無し(SOLICIT 固着) / ipv6 enable 無し(LL すら無い) / O flag なのに server 未 attach
          (INFORMATION-REQUEST 固着))を、client/server の show の組合せで一意に割る cause/fix/read。
★実測(P5): stateless の DNS 取得は bounce 直後は INFORMATION-REQUEST (5) 進行中 → exhibit は取得後の形。
  M+O 両方設定時は `Hosts use DHCP to obtain routable addresses.` と `… other configuration.` の両方が出る。
"""
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KINDS = ["mode", "trouble"]
SPEED_KINDS = ["mode"]
THINK_KINDS = ["trouble"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {"mode": {"select", "select2", "read"}, "trouble": {"cause", "fix", "read"}}
DIFF = {"mode": 2, "trouble": 4}
MODES = ["slaac", "stateless", "stateful"]
MODE_JA = {"slaac": "SLAAC(ステートレス自動設定・DHCPv6 なし)", "stateless": "ステートレス DHCPv6", "stateful": "ステートフル DHCPv6"}
CAUSES = ["no_unicast_routing", "ra_suppress", "acl_ll", "m_no_prefix", "no_ipv6_enable", "o_no_server"]


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


NAMES = [("RA", "RB"), ("R1", "R2"), ("GW1", "HOST-R"), ("RT01", "RT02")]
DNS_POOL = ["2001:4860:4860::8888", "2001:DB8:53::53", "2001:4860:4860::8844", "2001:DB8:1:53::10"]
DOMAINS = ["example.net", "corp.example.com", "lab.example.org"]


def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    d["srv"], d["cli"] = rnd.choice(NAMES)
    d["ifl"] = rnd.choice(["GigabitEthernet0/0", "Ethernet0/0", "GigabitEthernet0/1"])
    d["pfx"] = rnd.choice(["2001:DB8:34::", "2001:DB8:1::", "2001:DB8:AB:10::", "2001:DB8:100::"])
    d["dns"], d["domain"] = rnd.choice(DNS_POOL), rnd.choice(DOMAINS)
    d["pool"] = rnd.choice(["POOL-IPv6", "V6POOL", "LAN-V6", "DHCP6-A"])
    d["mac_s"], d["mac_c"] = "A8BB:CCFF:FE01:5800", rnd.choice(["A8BB:CCFF:FE01:5A00", "0C2A:11FF:FE3B:9C01", "5254:00FF:FE12:3456"])
    d["ll_s"], d["ll_c"] = f"FE80::{d['mac_s']}", f"FE80::{d['mac_c']}"
    d["iid"] = rnd.choice(["1C:580:9531:D6A3", "6C0F:1A2B:3C4D:5E6F", "48A2:9F0:1C33:7B10"])
    if kind == "mode":
        d["mode"] = rnd.choice(MODES)
    else:
        d["cause"] = rnd.choice(CAUSES)
        d["mode"] = {"m_no_prefix": "stateful", "no_ipv6_enable": "stateful", "o_no_server": "stateless"}.get(d["cause"], rnd.choice(["stateless", "slaac"]))
    return d


# ==========================================================================
# 構成と show の描画(実測書式)
# ==========================================================================
def server_cfg(d, mode, cause=None, blank=None):
    L = []
    if cause != "no_unicast_routing":
        L.append("ipv6 unicast-routing")
    if mode in ("stateless", "stateful"):
        L.append(f"ipv6 dhcp pool {d['pool']}")
        if mode == "stateful" and cause != "m_no_prefix":
            L.append(f" address prefix {d['pfx']}/64 lifetime infinite infinite")
        L.append(f" dns-server {d['dns']}")
        L.append(f" domain-name {d['domain']}")
        L.append("!")
    L.append(f"interface {d['ifl']}")
    L.append(f" ipv6 address {d['pfx']}1/64")
    if mode in ("stateless", "stateful") and cause != "o_no_server":
        L.append(f" ipv6 dhcp server {d['pool']}")
    if blank == "flag":
        L.append(" 【1】")
    else:
        if mode == "stateful":
            L.append(" ipv6 nd managed-config-flag")
            L.append(f" ipv6 nd prefix {d['pfx']}/64 2592000 604800 no-autoconfig")
        if mode in ("stateless", "stateful"):
            L.append(" ipv6 nd other-config-flag")
    if cause == "ra_suppress":
        L.append(" ipv6 nd ra suppress all")
    L.append(" no shutdown")
    return "\n".join(L)


def client_cfg(d, mode, cause=None, blank=None):
    L = [f"interface {d['ifl']}"]
    if cause == "acl_ll":
        L = [f"ipv6 access-list ACL-{d['cli']}", f" permit ipv6 host {d['pfx']}1 any", "!"] + L
        L.append(f" ipv6 traffic-filter ACL-{d['cli']} in")
    if blank == "addr":
        L.append(" 【2】")
    else:
        if mode == "stateful":
            if cause != "no_ipv6_enable":
                L.append(" ipv6 enable")
            L.append(" ipv6 address dhcp")
        else:
            L.append(" ipv6 address autoconfig")
    L.append(" no shutdown")
    return "\n".join(L)


def cli_brief(d, gua):
    """gua: 'slaac' | 'dhcp' | 'll' | 'none'"""
    L = [f"{d['cli']}# show ipv6 interface brief", f"{d['ifl']:<22} [up/up]"]
    if gua == "none":
        return "\n".join(L)
    L.append(f"    {d['ll_c']}")
    if gua == "slaac":
        L.append(f"    {d['pfx']}{d['mac_c']}")
    elif gua == "dhcp":
        L.append(f"    {d['pfx']}{d['iid']}")
    return "\n".join(L)


def cli_dhcp_if(d, kind):
    """kind: 'stateless_done' | 'stateless_pending' | 'stateful_open' | 'solicit' | 'idle'"""
    L = [f"{d['cli']}# show ipv6 dhcp interface {d['ifl']}", f"{d['ifl']} is in client mode"]
    srv = ["  List of known servers:", f"    Reachable via address: {d['ll_s']}", "    DUID: 00030001AABBCC015800", "    Preference: 0",
           "    Configuration parameters:"]
    tail = ["  Prefix Rapid-Commit: disabled", "  Address Rapid-Commit: disabled"]
    if kind == "stateless_done":
        L += ["  Prefix State is IDLE (0)", "  Information refresh timer expires in 23:59:42", "  Address State is IDLE"]
        L += srv + [f"      DNS server: {d['dns']}", f"      Domain name: {d['domain']}", "      Information refresh time: 0"] + tail
    elif kind == "stateless_pending":
        L += ["  Prefix State is INFORMATION-REQUEST (5)", "  Information refresh timer expires in 00:00:10", "  Address State is IDLE"] + tail
    elif kind == "stateful_open":
        L += ["  Prefix State is IDLE", "  Address State is OPEN", "  Renew for address will be sent in 11:59:40"]
        L += srv + ["      IA NA: IA ID 0x00020001, T1 43200, T2 69120", f"        Address: {d['pfx']}{d['iid']}/128",
                    "                preferred lifetime INFINITY, valid lifetime INFINITY",
                    f"      DNS server: {d['dns']}", f"      Domain name: {d['domain']}", "      Information refresh time: 0"] + tail
    elif kind == "solicit":
        L += ["  Prefix State is IDLE", "  Address State is SOLICIT (5)", "  Retransmission timer expires in 00:00:10"] + tail
    else:
        L += ["  Prefix State is IDLE", "  Address State is IDLE"] + tail
    return "\n".join(L)


def cli_routers(d, present, autoconfig=True):
    L = [f"{d['cli']}# show ipv6 routers"]
    if not present:
        return "\n".join(L)
    L += [f"Router {d['ll_s']} on {d['ifl']}, last update 0 min",
          "  Hops 64, Lifetime 1800 sec, AddrFlag=0, OtherFlag=0, MTU=1500",
          "  HomeAgentFlag=0, Preference=Medium",
          "  Reachable time 0 (unspecified), Retransmit time 0 (unspecified)",
          f"  Prefix {d['pfx']}/64 onlink{' autoconfig' if autoconfig else ''}",
          "    Valid lifetime 2592000, preferred lifetime 604800"]
    return "\n".join(L)


def srv_if_lines(d, mode, cause=None):
    L = [f"{d['srv']}# show ipv6 interface {d['ifl']} | include ND|Hosts"]
    L.append("  ND DAD is enabled, number of DAD attempts: 1")
    if cause == "no_unicast_routing":
        return "\n".join(L)
    if cause == "ra_suppress":
        L.append("  ND RAs are suppressed (all)")
    else:
        L.append("  ND router advertisements are sent every 200 seconds")
        L.append("  ND router advertisements live for 1800 seconds")
    if mode == "stateful":
        L.append("  Hosts use DHCP to obtain routable addresses.")
    else:
        L.append("  Hosts use stateless autoconfig for addresses.")
    if mode in ("stateless", "stateful"):
        L.append("  Hosts use DHCP to obtain other configuration.")
    return "\n".join(L)


def srv_binding(d, present):
    L = [f"{d['srv']}# show ipv6 dhcp binding"]
    if present:
        L += [f"Client: {d['ll_c']} ", f"  DUID: 00030001{d['mac_c'].replace(':', '')[:16]}", "  Username : unassigned", "  VRF : default",
              "  IA NA: IA ID 0x00020001, T1 43200, T2 69120", f"    Address: {d['pfx']}{d['iid']}",
              "            preferred lifetime INFINITY, , valid lifetime INFINITY,"]
    return "\n".join(L)


# ==========================================================================
# mode kind
# ==========================================================================
FLAG_LINE = {"slaac": "(フラグの設定なし)", "stateless": "ipv6 nd other-config-flag",
             "stateful": "ipv6 nd managed-config-flag"}
CLIENT_LINE = {"slaac": "ipv6 address autoconfig", "stateless": "ipv6 address autoconfig", "stateful": "ipv6 address dhcp"}


def _mode_exhibit(d):
    mode = d["mode"]
    s = server_cfg(d, mode, blank="flag")
    c = client_cfg(d, mode, blank="addr")
    return f"{d['srv']}# show running-config | section ipv6|interface {d['ifl']}\n{s}\n\n{d['cli']}# show running-config | section interface {d['ifl']}\n{c}"


def build_choices_select(d, rnd):
    mode = d["mode"]
    want = (FLAG_LINE[mode], CLIENT_LINE[mode])
    combos = []
    for m in MODES:
        for c in ("ipv6 address autoconfig", "ipv6 address dhcp"):
            combos.append((FLAG_LINE[m], c))
    combos.append(("ipv6 address autoconfig", "ipv6 nd other-config-flag"))   # 側の取り違え
    combos.append(("ipv6 address dhcp", "ipv6 nd managed-config-flag"))
    combos = [x for x in combos if x != want]
    picks = [want] + rnd.sample(combos, 3)
    rnd.shuffle(picks)
    c = []
    for f, cl in picks:
        text = f"【1】{f}　【2】{cl}"
        if (f, cl) == want:
            c.append((text, True, ""))
        else:
            c.append((text, False, _combo_why(d, f, cl)))
    return c


def _combo_why(d, f, cl):
    mode = d["mode"]
    if f.startswith("ipv6 address"):
        return "【1】はサーバ側(RA を送るルータ)の行であり、ipv6 address autoconfig / dhcp はクライアント側の行である。"
    if cl.startswith("ipv6 nd"):
        return "【2】はクライアント側の行であり、ipv6 nd のフラグは RA を送るサーバ側の行である。"
    if mode == "stateful":
        if cl == "ipv6 address autoconfig":
            return "プールに address prefix があり M フラグでアドレスを配る構成なので、クライアントは ipv6 address dhcp で取得する。"
        return "アドレスを DHCPv6 で配るには M フラグ(managed-config-flag)が要る。"
    if mode == "stateless":
        if cl == "ipv6 address dhcp":
            return "プールに address prefix が無く、アドレスは SLAAC で作る構成なので、クライアントは ipv6 address autoconfig である。"
        return "DNS などの情報だけを DHCPv6 から取らせるには O フラグ(other-config-flag)を立てる。M フラグを立てるとアドレスも DHCPv6 に求める。"
    # slaac
    if cl == "ipv6 address dhcp":
        return "DHCPv6 のプールが無い構成であり、クライアントは SLAAC(ipv6 address autoconfig)でアドレスを作る。"
    return "DHCPv6 を使わない構成では、M/O フラグは立てない。"


def build_choices_select2(d, rnd):
    mode = d["mode"]
    want = [FLAG_LINE[mode], CLIENT_LINE[mode]]
    if mode == "slaac":
        raise ValueError("slaac は select2 を持たない(追加行が 1 つ)")
    pool = ["ipv6 nd managed-config-flag", "ipv6 nd other-config-flag", "ipv6 address autoconfig", "ipv6 address dhcp",
            f"ipv6 dhcp relay destination {d['ll_s']}", "ipv6 nd ra suppress all"]
    others = [x for x in pool if x not in want]
    picks = want + rnd.sample(others, 3)
    rnd.shuffle(picks)
    c = []
    for p in picks:
        if p in want:
            c.append((p, True, ""))
        else:
            c.append((p, False, _line_why(d, p)))
    return c


def _line_why(d, p):
    mode = d["mode"]
    if p == "ipv6 nd managed-config-flag":
        return "M フラグはアドレスを DHCPv6 で配る構成のもの。この構成のプールには address prefix が無い。"
    if p == "ipv6 nd other-config-flag":
        return "O フラグだけではアドレスは配られない。この構成はプールの address prefix でアドレスを配る。"
    if p == "ipv6 address autoconfig":
        return "この構成はアドレスを DHCPv6 で配る(no-autoconfig 付き)ので、クライアントは ipv6 address dhcp である。"
    if p == "ipv6 address dhcp":
        return "この構成はアドレスを SLAAC で作る(プールに address prefix が無い)ので、クライアントは ipv6 address autoconfig である。"
    if p.startswith("ipv6 dhcp relay"):
        return "サーバはクライアントと同じリンクにあり、リレーは不要である。"
    if p.startswith("ipv6 nd ra suppress"):
        return "RA を止めるとフラグもプレフィックスも届かなくなる。"
    return ""


def _mode_read_exhibit(d):
    mode = d["mode"]
    if mode == "stateful":
        return "\n\n".join([cli_brief(d, "dhcp"), cli_dhcp_if(d, "stateful_open"), cli_routers(d, True, autoconfig=False)])
    if mode == "stateless":
        return "\n\n".join([cli_brief(d, "slaac"), cli_dhcp_if(d, "stateless_done"), cli_routers(d, True, autoconfig=True)])
    return "\n\n".join([cli_brief(d, "slaac"), cli_routers(d, True, autoconfig=True)])


def build_choices_read(d, rnd):
    if d["kind"] == "trouble":
        return _trouble_read(d, rnd)
    mode = d["mode"]
    cli = d["cli"]
    P = [
        (f"{cli} のグローバル ユニキャスト アドレスは、SLAAC(RA のプレフィックスと EUI-64)で生成されたものである。", mode != "stateful",
         "アドレスは DHCPv6 の IA NA で割り当てられた /128 であり(Address State is OPEN)、EUI-64 の形ではない。"),
        (f"{cli} のグローバル ユニキャスト アドレスは、DHCPv6 サーバから割り当てられたものである。", mode == "stateful",
         "アドレスの後半は EUI-64(MAC 由来)であり、DHCPv6 の IA NA は無い。"),
        (f"{cli} は DNS サーバのアドレスを DHCPv6 で取得している。", mode != "slaac",
         "DHCPv6 の情報(DNS server / Domain name)は取得していない。"),
        (f"RA を送るルータでは M フラグ(managed-config-flag)が設定されている。", mode == "stateful",
         "M フラグがあればアドレスは DHCPv6 で割り当てられる(IA NA)。この出力では SLAAC のアドレスである。"),
        (f"RA を送るルータでは O フラグ(other-config-flag)が設定されている。", mode != "slaac",
         "O フラグがあればクライアントは DHCPv6 から DNS などを取得する。この出力にはその情報が無い。"),
        (f"RA のプレフィックスは autoconfig フラグ(A)が立っていない。", mode == "stateful",
         "show ipv6 routers の Prefix 行に autoconfig が付いており、A フラグは立っている。"),
        (f"{cli} はステートフル DHCPv6 でアドレスと DNS を取得している。", mode == "stateful", "アドレスは SLAAC であり、ステートフルではない。"),
        (f"RA のプレフィックスには autoconfig フラグ(A)が立っている。", mode != "stateful", "show ipv6 routers の Prefix 行に autoconfig が無く、A フラグは立っていない。"),
        (f"{cli} のグローバル ユニキャスト アドレスのインターフェイス ID は、MAC アドレスから生成されている。", mode != "stateful", "アドレスは DHCPv6 で割り当てられた /128 であり、MAC 由来(EUI-64)ではない。"),
        (f"DHCPv6 サーバは {cli} にアドレスを割り当てていない。", mode != "stateful", "IA NA でアドレスが割り当てられている(Address State is OPEN)。"),
    ]
    trues = [(t, w) for t, ok, w in P if ok]
    falses = [(t, w) for t, ok, w in P if not ok]
    if not trues or len(falses) < 3:
        raise ValueError("mode read: 肢が組めない")
    t, _ = rnd.choice(trues)
    c = [(t, True, "")]
    for f, w in rnd.sample(falses, 3):
        c.append((f, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# trouble kind
# ==========================================================================
CAUSE_TEXT = {
    "no_unicast_routing": "{srv} で ipv6 unicast-routing が有効になっておらず、RA が送信されていない。",
    "ra_suppress": "{srv} の {ifl} で RA の送信が抑止されている。",
    "acl_ll": "{cli} の {ifl} に着信で適用された IPv6 アクセス リストが、リンクローカル アドレスを送信元とする RA を破棄している。",
    "m_no_prefix": "{srv} は M フラグでアドレスの取得を DHCPv6 に求めているが、プールに割り当てるプレフィックス(address prefix)が無い。",
    "no_ipv6_enable": "{cli} の {ifl} に ipv6 enable が無く、リンクローカル アドレスが無いので DHCPv6 の SOLICIT を送信できない。",
    "o_no_server": "{srv} は O フラグで情報の取得を DHCPv6 に求めているが、{ifl} に DHCPv6 サーバ(プール)が関連付けられていない。",
}
SYMPTOM = {
    "no_unicast_routing": "{cli} の {ifl} にはリンクローカル アドレスしか付いていません。",
    "ra_suppress": "{cli} の {ifl} にはリンクローカル アドレスしか付いていません。",
    "acl_ll": "{cli} の {ifl} にはリンクローカル アドレスしか付いていません。",
    "m_no_prefix": "{cli} の {ifl} にはリンクローカル アドレスしか付かず、グローバル ユニキャスト アドレスを取得できません。",
    "no_ipv6_enable": "{cli} の {ifl} には IPv6 アドレスがまったく付いていません。",
    "o_no_server": "{cli} はグローバル ユニキャスト アドレスを取得していますが、DNS サーバのアドレスとドメイン名を取得できません。",
}


def _trouble_exhibit(d):
    c, mode = d["cause"], d["mode"]
    blocks = [f"{d['srv']}# show running-config | section ipv6|interface {d['ifl']}\n{server_cfg(d, mode, cause=c)}",
              f"{d['cli']}# show running-config | section ipv6|interface {d['ifl']}\n{client_cfg(d, mode, cause=c)}"]
    if c in ("no_unicast_routing", "ra_suppress", "acl_ll"):
        blocks += [cli_brief(d, "ll"), cli_routers(d, False)]
        if mode == "stateless":
            blocks.append(cli_dhcp_if(d, "idle"))
    elif c == "m_no_prefix":
        blocks += [cli_brief(d, "ll"), cli_dhcp_if(d, "solicit"), cli_routers(d, True, autoconfig=False), srv_binding(d, False)]
    elif c == "no_ipv6_enable":
        blocks += [cli_brief(d, "none"), cli_dhcp_if(d, "idle"), srv_binding(d, False)]
    elif c == "o_no_server":
        blocks += [cli_brief(d, "slaac"), cli_dhcp_if(d, "stateless_pending"), cli_routers(d, True, autoconfig=True)]
    blocks.append(srv_if_lines(d, mode, cause=c))
    return "\n\n".join(blocks)


def build_choices_cause(d, rnd):
    c0 = d["cause"]
    fmt = dict(srv=d["srv"], cli=d["cli"], ifl=d["ifl"])
    c = [(CAUSE_TEXT[c0].format(**fmt), True, "")]
    for k in rnd.sample([x for x in CAUSES if x != c0], 3):
        c.append((CAUSE_TEXT[k].format(**fmt), False, _cause_why(d, k)))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _cause_why(d, k):
    fmt = dict(srv=d["srv"], cli=d["cli"], ifl=d["ifl"])
    return {
        "no_unicast_routing": "{srv} の構成に ipv6 unicast-routing があり、show ipv6 interface にも RA の送信間隔が表示されている。",
        "ra_suppress": "{srv} の {ifl} に ra suppress は無く、show ipv6 interface にも suppressed の表示は無い。",
        "acl_ll": "{cli} の {ifl} に IPv6 のアクセス リストは適用されていない。",
        "m_no_prefix": "M フラグとプレフィックスの組合せの問題なら、クライアントは Address State is SOLICIT で止まる。この出力とは合わない。",
        "no_ipv6_enable": "ipv6 enable が無ければリンクローカル アドレスも付かない。この出力にはリンクローカル アドレスがある。",
        "o_no_server": "O フラグと server 未関連付けの問題なら、Prefix State は INFORMATION-REQUEST で止まる。この出力とは合わない。",
    }[k].format(**fmt)


FIX_MENU = {
    "no_unicast_routing": [("{srv}(config)# ipv6 unicast-routing", True, ""),
                           ("{srv}(config-if)# ipv6 nd other-config-flag", False, "フラグを立てても RA そのものが送信されない。"),
                           ("{cli}(config-if)# ipv6 address dhcp", False, "RA が来ない状況では M フラグも届かず、アドレスは配られない(プールにもプレフィックスが無い)。"),
                           ("{cli}(config-if)# ipv6 enable", False, "リンクローカル アドレスは既に付いており、足りないのは RA である。")],
    "ra_suppress": [("{srv}(config-if)# no ipv6 nd ra suppress all", True, ""),
                    ("{srv}(config)# ipv6 unicast-routing", False, "ipv6 unicast-routing は既に有効である。"),
                    ("{cli}(config-if)# ipv6 address autoconfig default", False, "RA が来なければ default を付けても変わらない。"),
                    ("{srv}(config-if)# ipv6 nd managed-config-flag", False, "RA が抑止されたままではフラグも届かない。")],
    "acl_ll": [("{cli}(config-ipv6-acl)# permit icmp any any router-advertisement", True, ""),
               ("{cli}(config-ipv6-acl)# permit ipv6 host {pfx}1 any", False, "同じ行が既にあり、RA の送信元(リンクローカル)には一致しない。"),
               ("{srv}(config-if)# ipv6 nd other-config-flag", False, "RA がクライアントで破棄されている状況は変わらない。"),
               ("{cli}(config-if)# ipv6 traffic-filter ACL-{cli} out", False, "方向を out に変えても、着信の RA を許可する行が無いことは変わらない。")],
    "m_no_prefix": [("{srv}(config-dhcpv6)# address prefix {pfx}/64 lifetime infinite infinite", True, ""),
                    ("{srv}(config-if)# ipv6 nd other-config-flag", False, "O フラグは既にあり、足りないのはアドレスの割り当て元である。"),
                    ("{cli}(config-if)# ipv6 address autoconfig", False, "RA のプレフィックスは no-autoconfig であり、SLAAC ではアドレスが作れない。"),
                    ("{srv}(config)# ipv6 dhcp relay destination {ll_c}", False, "サーバは同じリンクにあり、リレーは関係ない。")],
    "no_ipv6_enable": [("{cli}(config-if)# ipv6 enable", True, ""),
                       ("{cli}(config-if)# ipv6 address autoconfig", False, "RA のプレフィックスは no-autoconfig であり、SLAAC ではアドレスが作れない。"),
                       ("{srv}(config-if)# ipv6 nd managed-config-flag", False, "M フラグは既にある。クライアントがそもそも SOLICIT を送れない。"),
                       ("{srv}(config-dhcpv6)# address prefix {pfx}/64", False, "プールには既にプレフィックスがある。")],
    "o_no_server": [("{srv}(config-if)# ipv6 dhcp server {pool}", True, ""),
                    ("{srv}(config-if)# ipv6 nd managed-config-flag", False, "M フラグを立ててもサーバが関連付けられていなければ応答は無い(しかもアドレスは SLAAC で足りている)。"),
                    ("{cli}(config-if)# ipv6 address dhcp", False, "情報要求(INFORMATION-REQUEST)は既に送っており、応答が無いのが問題である。"),
                    ("{srv}(config-dhcpv6)# address prefix {pfx}/64", False, "アドレスは SLAAC で取得済みであり、足りないのは情報の応答である。")],
}


def build_choices_fix(d, rnd):
    fmt = dict(srv=d["srv"], cli=d["cli"], ifl=d["ifl"], pfx=d["pfx"], pool=d["pool"], ll_c=d["ll_c"])
    c = [(t.format(**fmt), ok, w.format(**fmt)) for t, ok, w in FIX_MENU[d["cause"]]]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _trouble_read(d, rnd):
    c0, mode = d["cause"], d["mode"]
    cli, srv = d["cli"], d["srv"]
    ra_ok = c0 not in ("no_unicast_routing", "ra_suppress", "acl_ll")
    P = [
        (f"{cli} は {srv} からの RA を受信している。", ra_ok, "show ipv6 routers に何も無く、RA は受信していない。"),
        (f"{cli} は {srv} からの RA を受信していない。", not ra_ok, "show ipv6 routers にルータが載っており、RA は受信している。"),
        (f"{cli} は DHCPv6 の SOLICIT を送信したが、ADVERTISE を受け取れていない。", c0 == "m_no_prefix", "Address State は SOLICIT ではない。"),
        (f"{cli} は DHCPv6 の情報要求(INFORMATION-REQUEST)を送信したが、応答を受け取れていない。", c0 == "o_no_server", "Prefix State は INFORMATION-REQUEST ではない。"),
        (f"{cli} の {d['ifl']} にはリンクローカル アドレスが付いていない。", c0 == "no_ipv6_enable", "show ipv6 interface brief にリンクローカル アドレスが表示されている。"),
        (f"{srv} は RA を送信している。", c0 not in ("no_unicast_routing", "ra_suppress"), "show ipv6 interface に RA の送信間隔の行が無い(または suppressed)。"),
        (f"{srv} の DHCPv6 プールにはアドレスの割り当て範囲が無い。", mode in ("stateless", "slaac") or c0 == "m_no_prefix", "プールに address prefix がある。"),
    ]
    trues = [(t, w) for t, ok, w in P if ok]
    falses = [(t, w) for t, ok, w in P if not ok]
    if not trues or len(falses) < 3:
        raise ValueError("trouble read: 肢が組めない")
    t, _ = rnd.choice(trues)
    c = [(t, True, "")]
    for f, w in rnd.sample(falses, 3):
        c.append((f, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_allthat(d, rnd):
    raise ValueError("dhcp6 に allthat は無い")


def build_match(d, rnd):
    raise ValueError("dhcp6 に match は無い")


# ==========================================================================
# Markdown
# ==========================================================================
CORE = {
    "mode": ("M フラグ= アドレスを DHCPv6 で取らせる(client は ipv6 address dhcp・ipv6 enable 必須・純粋にするなら prefix に no-autoconfig)。"
             "O フラグ= DNS などの情報だけ DHCPv6(client は ipv6 address autoconfig・プールに address prefix は要らない)。"
             "フラグ無し= SLAAC のみ。フラグは RA を送るルータ側、address autoconfig/dhcp はクライアント側。"
             "client の show ipv6 dhcp interface: ステートレス完了= Prefix State IDLE＋DNS/Domain、ステートフル= Address State OPEN＋IA NA /128。"),
    "trouble": ("GUA が付かない原因は show の組合せで割れる: server に RA 行なし= ipv6 unicast-routing 欠落 / ND RAs are suppressed= ra suppress / "
                "client の traffic-filter が LL 送信元の RA を落とす(host GUA 許可だけでは足りない) / Address State SOLICIT 固着= M なのにプールに prefix 無し / "
                "LL すら無い= ipv6 enable 無し(SOLICIT を送れないサイレント) / Prefix State INFORMATION-REQUEST 固着= O なのに server 未関連付け。"),
}
TITLES = {"mode": "IPv6 アドレスの自動設定(SLAAC/DHCPv6)", "trouble": "IPv6 アドレス自動設定のトラブルシューティング"}



def _mmid(name):
    """Mermaid のノード ID(英数字以外は _ に。表示名は label 側に持つ・BL-187)。"""
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", str(name))


def _dhcp6_mermaid(d):
    srv, cli = d["srv"], d["cli"]
    return "\n".join([
        "```mermaid", "graph LR",
        f'  {_mmid(srv)}["{srv}<br/>{d["ifl"]}<br/>RA / DHCPv6"]',
        f'  {_mmid(cli)}["{cli}<br/>{d["ifl"]}"]',
        f'  {_mmid(srv)} ---|"{d["pfx"]}/64"| {_mmid(cli)}',
        "```"])

def question_body(d, choices, form):
    if d["kind"] == "mode":
        if form == "read":
            before = f"{d['cli']} で次の出力が得られました。\n\n```\n{_mode_read_exhibit(d)}\n```"
            ask = "この出力から分かることとして、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
        else:
            intro = {"slaac": f"{d['srv']} は RA を送信し、{d['cli']} は RA のプレフィックスからアドレスを自動生成します。DHCPv6 は使用しません。",
                     "stateless": f"{d['srv']} は DHCPv6 サーバとして DNS サーバとドメイン名だけを配布し、{d['cli']} はアドレスを RA のプレフィックスから自動生成します。",
                     "stateful": f"{d['srv']} は DHCPv6 サーバとしてアドレスと DNS サーバ・ドメイン名を配布し、{d['cli']} はアドレスを DHCPv6 で取得します。"}[d["mode"]]
            before = f"{_dhcp6_mermaid(d)}\n\n{intro}\n\n```\n{_mode_exhibit(d)}\n```"
            if form == "select":
                ask = "【1】と【2】に当てはまるコマンドの組合せとして正しいものは、次のうちどれですか。(1つを選択してください)"
            else:
                ask = "【1】と【2】に当てはまるコマンドを、次のうちから 2 つ選択してください。"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    fmt = dict(srv=d["srv"], cli=d["cli"], ifl=d["ifl"])
    intro = {"stateful": f"{d['srv']} は DHCPv6 サーバとしてアドレスと DNS サーバ・ドメイン名を配布し、{d['cli']} はアドレスを DHCPv6 で取得する設計です。",
             "stateless": f"{d['srv']} は DHCPv6 サーバとして DNS サーバとドメイン名だけを配布し、{d['cli']} はアドレスを RA のプレフィックスから自動生成する設計です。",
             "slaac": f"{d['cli']} は {d['srv']} が送る RA のプレフィックスからアドレスを自動生成する設計です。"}[d["mode"]]
    before = f"{_dhcp6_mermaid(d)}\n\n{intro}\n\n```\n{_trouble_exhibit(d)}\n```\n\n{SYMPTOM[d['cause']].format(**fmt)}"
    if form == "cause":
        ask = "この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
    elif form == "fix":
        ask = "設計どおりに動作させるために追加する構成として最も適切なものは、次のうちどれですか。(1つを選択してください)"
    else:
        ask = "これらの出力から分かることとして、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
    ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    return before, ask, ch_md, ""


def answer_body(d, choices, form):
    keys = [k for k, (t, ok, w) in zip("ABCDEFG", choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip("ABCDEFG", choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[d["kind"]]]
    lines += ["", f"- 仕込み: mode=`{d['mode']}`" + (f" cause=`{d['cause']}`" if d["kind"] == "trouble" else ""),
              "- 実出力の正典: poc/paper-kb/results-raw.md P5(iol-xe 17.15.1)"]
    return "\n".join(lines)


def pick_count(form, choices):
    return 2 if form == "select2" else 1


def selftest(seeds=40):
    import random as _r
    import re as _re
    ng = n = 0
    bad = {}
    builders = {"select": build_choices_select, "select2": build_choices_select2, "read": build_choices_read,
                "cause": build_choices_cause, "fix": build_choices_fix}
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = draw(rnd, kind, None, form)
                    try:
                        choices = builders[form](d, rnd)
                    except ValueError as e:
                        if "slaac は select2" in str(e):
                            continue
                        raise
                    n_true = sum(1 for x in choices if x[1])
                    assert n_true == (2 if form == "select2" else 1), f"{form} 正解数 {n_true}"
                    texts = [x[0] for x in choices]
                    assert len(set(texts)) == len(texts), "選択肢の重複"
                    assert not any(_re.search(r"(ため|ので)[、。]", t) for t in texts), "肢に因果"
                    before, ask, ch_md, _ = question_body(d, choices, form)
                    assert "```" in before
                    assert "## 正解" in answer_body(d, choices, form)
                except (AssertionError, ValueError, KeyError) as exc:
                    ng += 1
                    bad.setdefault((kind, form), [0, repr(exc)])[0] += 1
    for (k, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{f}: {cnt} 件 (例: {ex})")
    print(f"[gen_paper_dhcp6 selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
