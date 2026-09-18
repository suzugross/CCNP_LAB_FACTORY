#!/usr/bin/env python3
"""紙面 知識・読解ファミリ(ospfdbg / dhcp6 / eigrpkb / svc 追加 kind / dmvpn 構文)の PoC 採取。

盤面 POC-KB = IOL(iol-xe) 4 台の直列。コンソール駆動のみ(MGMT なし・ホスト側の相手も不要)。

    RT01 e0/0 --10.0.12.0/24-- e0/0 RT02 e0/1 --10.0.23.0/24-- e0/1 RT03 e0/0 --10.0.34.0/24-- e0/0 RT04
    Lo0 1.1.1.1                   Lo0 2.2.2.2                    Lo0 3.3.3.3                    Lo0 4.4.4.4

使い方: sweep.py build | P0 P1 ... P6 | all | teardown        結果は results-raw.md へ追記。
  P0: 基線(IF/ping)  P1: `?` ヘルプ採取  P2: debug ip packet  P3: OSPF 隣接 debug 指紋
  P4: BFD ネゴ  P5: DHCPv6 モード/原因  P6: EIGRP auto-summary 境界(全台を再アドレス=最後に実行)
"""
import os
import re
import sys
import time
import traceback
from pathlib import Path

import urllib3
import yaml
from virl2_client import ClientLibrary
from pyats.topology import loader
from unicon.eal.dialogs import Dialog, Statement

urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "results-raw.md"
LAB_TITLE = "POC-KB"
NODES = ["RT01", "RT02", "RT03", "RT04"]
USER, PW = "SUZUKI", "CCNP"

COMMON = [
    "no ip domain lookup", "ip cef",
    f"username {USER} privilege 15 secret {PW}",
    "service timestamps debug datetime msec", "service timestamps log datetime msec",
    "no logging console", "logging buffered 1000000 debugging",
    "line con 0", "exec-timeout 0 0", "logging synchronous", "exit",
    "file prompt quiet",
]
BASE = {
    "RT01": ["interface Loopback0", "ip address 1.1.1.1 255.255.255.255", "exit",
             "interface Ethernet0/0", "ip address 10.0.12.1 255.255.255.0", "no shutdown", "exit",
             "ip route 0.0.0.0 0.0.0.0 10.0.12.2"],
    "RT02": ["interface Loopback0", "ip address 2.2.2.2 255.255.255.255", "exit",
             "interface Ethernet0/0", "ip address 10.0.12.2 255.255.255.0", "no shutdown", "exit",
             "interface Ethernet0/1", "ip address 10.0.23.2 255.255.255.0", "no shutdown", "exit",
             "ip route 10.0.34.0 255.255.255.0 10.0.23.3"],
    "RT03": ["interface Loopback0", "ip address 3.3.3.3 255.255.255.255", "exit",
             "interface Ethernet0/1", "ip address 10.0.23.3 255.255.255.0", "no shutdown", "exit",
             "interface Ethernet0/0", "ip address 10.0.34.3 255.255.255.0", "no shutdown", "exit",
             "ip route 10.0.12.0 255.255.255.0 10.0.23.2"],
    "RT04": ["interface Loopback0", "ip address 4.4.4.4 255.255.255.255", "exit",
             "interface Ethernet0/0", "ip address 10.0.34.4 255.255.255.0", "no shutdown", "exit",
             "ip route 0.0.0.0 0.0.0.0 10.0.34.3"],
}
LINKS = [("RT01", "Ethernet0/0", "RT02", "Ethernet0/0"),
         ("RT02", "Ethernet0/1", "RT03", "Ethernet0/1"),
         ("RT03", "Ethernet0/0", "RT04", "Ethernet0/0")]

LOG = []


# =========================================================================
# 記録
# =========================================================================
def block(title, text, lang=""):
    LOG.append(f"\n**{title}**\n\n```{lang}\n{(text or '').rstrip()}\n```\n")
    print(f"  [rec] {title} ({len(text or '')} bytes)", flush=True)


def note(text):
    LOG.append(f"\n- {text}\n")
    print(f"  [note] {text}", flush=True)


def flush(section):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(f"\n## {section}  ({time.strftime('%Y-%m-%d %H:%M')})\n")
        f.write("".join(LOG))
    LOG.clear()


# =========================================================================
# CML
# =========================================================================
def client():
    c = yaml.safe_load(open(REPO / "group_vars" / "all" / "local.yml"))
    return ClientLibrary(f"https://{c['cml_host']}", c["cml_username"], c["cml_password"],
                         ssl_verify=False), c


def _iface(lab, label, ifname):
    for _ in range(6):
        node = lab.get_node_by_label(label)
        for i in node.interfaces():
            if i.label == ifname:
                return i
        lab.sync(topology_only=True)
        time.sleep(1)
    raise RuntimeError(f"{label} に {ifname} が見つからない")


def day0(label):
    return "\n".join([f"hostname {label}"] + COMMON + BASE[label]) + "\n"


def ensure_lab(cl):
    labs = cl.find_labs_by_title(LAB_TITLE)
    if labs:
        lab = labs[0]
        print(f"[i] 既存ラボ {LAB_TITLE} ({lab.state()})")
    else:
        print(f"[i] ラボ {LAB_TITLE} を新規作成")
        lab = cl.create_lab(LAB_TITLE)
    have = {n.label for n in lab.nodes()}
    for i, label in enumerate(NODES):
        if label not in have:
            n = lab.create_node(label, "iol-xe", -300 + 200 * i, 0, populate_interfaces=True)
            n.configuration = day0(label)
    lab.sync(topology_only=True)
    for a, aif, b, bif in LINKS:
        ia, ib = _iface(lab, a, aif), _iface(lab, b, bif)
        if ia.connected or ib.connected:
            continue
        print(f"[i] link {a} {aif} <-> {b} {bif}")
        lab.create_link(ia, ib)
    if lab.state() != "STARTED":
        print("[i] lab start...")
        lab.start(wait=True)
    for n in lab.nodes():
        print(f"    {n.label}: {n.state}")
    return lab


def get_lab(cl):
    labs = cl.find_labs_by_title(LAB_TITLE)
    if not labs:
        sys.exit(f"ラボ {LAB_TITLE} が無い(build を先に)")
    return labs[0]


def connect_all(lab, creds, labels=NODES):
    tb = yaml.safe_load(lab.get_pyats_testbed())
    for name, dev in (tb.get("devices") or {}).items():
        c = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            c["default"] = {"username": creds["cml_username"], "password": creds["cml_password"]}
        else:
            c["default"] = {"username": USER, "password": PW}
            c["enable"] = {"password": PW}
    testbed = loader.load(tb)
    devs = {}
    for label in labels:
        dev = testbed.devices[label]
        for attempt in range(1, 13):
            try:
                dev.connect(via="a", log_stdout=False, learn_hostname=True, connection_timeout=120)
                dev.enable()
                dev.execute("terminal length 0")
                dev.execute("terminal width 220")
                devs[label] = dev
                break
            except Exception as e:
                print(f"    {label}: connect attempt {attempt} failed ({type(e).__name__}: {str(e)[:80]})")
                try:
                    dev.disconnect()
                except Exception:
                    pass
                time.sleep(15)
        else:
            raise RuntimeError(f"{label}: console 接続不能")
    return devs


DIALOG = Dialog([
    Statement(pattern=r"\[yes/no\]:?\s*$", action="sendline(yes)", loop_continue=True, continue_timer=False),
    Statement(pattern=r"\[confirm\]\s*$", action="sendline()", loop_continue=True, continue_timer=False),
    Statement(pattern=r"\[no\]:?\s*$", action="sendline(Y)", loop_continue=True, continue_timer=False),
])


def conf(dev, lines, title=None):
    if isinstance(lines, str):
        lines = [l for l in lines.split("\n") if l.strip()]
    out = dev.configure(lines, error_pattern=[], timeout=180, reply=DIALOG)
    text = out if isinstance(out, str) else "\n".join(v for v in out.values() if isinstance(v, str))
    errs = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("%")]
    if title:
        block(title, "\n".join(lines) + ("\n---\n" + "\n".join(errs) if errs else "\n---\n(応答なし)"))
    for e in errs:
        print(f"    ! {dev.name}: {e}")
    return text


def sh(dev, cmd, title=None, timeout=120):
    out = dev.execute(cmd, timeout=timeout, reply=DIALOG, error_pattern=[])
    if title:
        block(f"{title} — {dev.name}# {cmd}", out)
    return out


def ping(dev, dst, source=None, repeat=3, title=None):
    cmd = f"ping {dst} repeat {repeat}"
    if source:
        cmd += f" source {source}"
    out = sh(dev, cmd, timeout=90)
    m = re.search(r"Success rate is (\d+) percent", out)
    rate = int(m.group(1)) if m else -1
    if title:
        block(f"{title} — {dev.name}# {cmd} → {rate}%", out)
    return rate, out


def wait_for(fn, timeout=300, step=10, what="条件"):
    t0 = time.time()
    info = None
    while time.time() - t0 < timeout:
        ok, info = fn()
        if ok:
            return time.time() - t0, info
        print(f"    待ち {time.time()-t0:.0f}s: {what}", flush=True)
        time.sleep(step)
    return None, info


def clear_log(dev):
    sh(dev, "clear logging")


def logtail(dev, title, include=None, maxlines=260):
    out = sh(dev, "show logging", timeout=180)
    lines = out.splitlines()
    # ヘッダ(設定表示)を落として本文だけ
    body = []
    started = False
    for ln in lines:
        if not started and re.match(r"^\*?[A-Z][a-z]{2} +\d+ ", ln.strip()):
            started = True
        if started:
            body.append(ln)
    if include:
        body = [ln for ln in body if re.search(include, ln)]
    if len(body) > maxlines:
        body = body[:maxlines // 2] + [f"... ({len(body) - maxlines} lines omitted) ..."] + body[-maxlines // 2:]
    block(f"{title} — {dev.name} show logging", "\n".join(body))
    return "\n".join(body)


# ---- `?` ヘルプ採取(unicon の spawn を直接叩く) ----------------------------
def help_capture(dev, mode_lines, query, title=None):
    """configure terminal → mode_lines で潜って '<query>?' のヘルプを取り end で戻る。"""
    sp = dev.spawn

    def xp(pat, t=25):
        sp.expect([pat], timeout=t)
        return sp.match.match_output

    sp.sendline("configure terminal")
    xp(r"\(config\)#\s*$")
    for l in mode_lines:
        sp.sendline(l)
        xp(r"\(config[^)]*\)#\s*$")
    sp.send(query + "?")
    # IOS はヘルプの後にプロンプト＋入力途中のコマンドを再表示する(末尾空白の有無は版で揺れる)
    out = xp(r"\)#" + re.escape(query.rstrip()) + r" ?\s*$")
    sp.send("\x15")           # Ctrl-U: 行消去
    sp.sendline("")
    xp(r"\(config[^)]*\)#\s*$", 10)
    sp.sendline("end")
    xp(r"[\w\-]+#\s*$", 10)
    # 先頭のエコー行を落とす
    out = out.replace("\r", "")
    if title:
        block(f"{title} — {dev.name}: {' / '.join(mode_lines) or '(config)'} : {query}?", out)
    return out


# =========================================================================
# P0 基線
# =========================================================================
def P0(devs):
    for n in NODES:
        d = devs[n]
        ipb = sh(d, "show ip interface brief")
        if "administratively down" in ipb:
            note(f"{n}: admin-down IF あり(CVAC 罠)→ no shutdown を投入")
            for m in re.finditer(r"^(Ethernet\S+)\s+\S+\s+YES.*administratively down", ipb, re.M):
                conf(d, [f"interface {m.group(1)}", "no shutdown"])
            ipb = sh(d, "show ip interface brief")
        block(f"P0 基線 — {n} show ip interface brief", ipb)
        block(f"P0 — {n} show version | include Software|uptime", sh(d, "show version | include Software|uptime"))
    time.sleep(3)
    ping(devs["RT01"], "10.0.34.4", repeat=3, title="P0 疎通 RT01→RT04(static 連鎖)")
    ping(devs["RT04"], "10.0.12.1", repeat=3, title="P0 疎通 RT04→RT01")
    flush("P0 基線")


# =========================================================================
# P1 `?` ヘルプ採取
# =========================================================================
def P1(devs):
    d = devs["RT01"]
    # --- EIGRP named mode ---
    hc(d, ["router eigrp NAMED"], "", "P1 eigrp named: (config-router)")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 100"], "",
                 "P1 eigrp named: (config-router-af)")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 100", "af-interface default"], "",
                 "P1 eigrp named: (config-router-af-interface)")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 100", "topology base"], "",
                 "P1 eigrp named: (config-router-af-topology)")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 100"], "eigrp ",
                 "P1 eigrp named af: eigrp ?")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 100", "af-interface default"],
                 "authentication ", "P1 eigrp named af-interface: authentication ?")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 100", "topology base"],
                 "redistribute ", "P1 eigrp named af-topology: redistribute ?")
    # classic for equivalence
    hc(d, ["router eigrp 100"], "", "P1 eigrp classic: (config-router)")
    hc(d, ["interface Ethernet0/0"], "ip hello-interval ", "P1 classic IF: ip hello-interval ?")
    hc(d, ["interface Ethernet0/0"], "ip authentication ", "P1 classic IF: ip authentication ?")
    conf(d, ["no router eigrp NAMED", "no router eigrp 100"])
    # --- NHRP / tunnel ---
    for q in ["ip nhrp ", "ip nhrp registration ", "ip nhrp map ", "ip nhrp map multicast ", "ip nhrp nhs ",
              "ip nhrp nhs 10.0.0.1 ", "ip nhrp nhs 10.0.0.1 nbma 192.0.2.1 ", "ip nhrp holdtime ", "ip nhrp authentication ",
              "ip nhrp shortcut ", "ip nhrp redirect ", "ip nhrp network-id ", "tunnel mode ", "tunnel mode gre ",
              "tunnel key ", "tunnel protection ", "tunnel protection ipsec profile PROF "]:
        hc(d, ["interface Tunnel0"], q, "P1 nhrp/tunnel")
    conf(d, ["no interface Tunnel0"])
    # --- crypto の有無 ---
    for q in ["crypto ", "crypto ipsec ", "crypto isakmp "]:
        hc(d, [], q, "P1 crypto 有無")
    # --- precedence / dscp ---
    for q in ["set ip precedence ", "set ip dscp ", "set ip tos ", "set ", "set precedence ", "set dscp "]:
        hc(d, ["route-map RM-POC permit 10"], q, "P1 route-map set")
    conf(d, ["route-map RM-POC permit 10", "set ip precedence priority", "set ip dscp af31", "exit"])
    block("P1 show route-map(precedence/dscp の表示形)", sh(d, "show route-map RM-POC"))
    conf(d, ["no route-map RM-POC"])
    # --- BFD ---
    for mode, q in [(["bfd-template single-hop T-POC"], "interval "), (["bfd-template single-hop T-POC"], "interval min-tx 100 "),
                    (["bfd-template single-hop T-POC"], "interval min-tx 100 min-rx 100 "),
                    (["interface Ethernet0/0"], "bfd "), (["interface Ethernet0/0"], "bfd interval 100 "),
                    (["interface Ethernet0/0"], "bfd interval 100 min_rx 100 "),
                    (["interface Ethernet0/0"], "ip ospf bfd "), (["router ospf 99"], "bfd ")]:
        hc(d, mode, q, "P1 bfd")
    conf(d, ["no bfd-template single-hop T-POC", "no router ospf 99"])
    flush("P1 `?` ヘルプ採取")


def _recover(dev):
    sp = dev.spawn
    for _ in range(2):
        try:
            sp.send("\x15")
            sp.sendline("end")
            sp.expect([r"[\w\-]+#\s*$"], timeout=10)
            break
        except Exception:
            pass
    try:
        dev.execute("show clock", timeout=20)   # unicon の状態を enable に同期
    except Exception:
        pass


def hc(dev, mode_lines, query, title):
    """help_capture の失敗耐性版: 失敗しても記録して復帰する。"""
    try:
        return help_capture(dev, mode_lines, query, title)
    except Exception as e:
        note(f"help_capture 失敗 {mode_lines} {query!r}: {type(e).__name__}: {str(e)[:120]}")
        _recover(dev)
        return None


# =========================================================================
# P2 debug ip packet
# =========================================================================
def P2(devs):
    r1, r2 = devs["RT01"], devs["RT02"]
    conf(r2, ["access-list 199 permit ip host 10.0.12.1 any", "access-list 199 permit ip any host 10.0.12.1",
              "access-list 199 permit ip host 10.0.12.2 any", "access-list 199 permit ip any host 10.0.12.2"])

    def run(title, setup_fn, ping_dev, dst, detail=False, teardown_fn=None):
        if setup_fn:
            setup_fn()
        clear_log(r2)
        sh(r2, f"debug ip packet 199{' detail' if detail else ''}")
        rate, _ = ping(ping_dev, dst, repeat=2)
        time.sleep(3)
        sh(r2, "undebug all")
        note(f"{title}: ping {ping_dev.name}→{dst} = {rate}%")
        logtail(r2, title, include=r"IP:|ICMP")
        if teardown_fn:
            teardown_fn()

    run("P2a forus(自ルータ宛を受信)", None, r1, "10.0.12.2")
    run("P2b transit(中継 forward)", None, r1, "10.0.23.3")
    run("P2c local 発(自ルータ発)", None, r2, "10.0.12.1")
    run("P2d unroutable(経路なし)", None, r1, "172.31.99.1")
    run("P2e access denied(inbound ACL で拒否)",
        lambda: conf(r2, ["ip access-list extended BLOCK-POC", "deny icmp host 10.0.12.1 host 10.0.23.3", "permit ip any any", "exit",
                          "interface Ethernet0/0", "ip access-group BLOCK-POC in"]),
        r1, "10.0.23.3",
        teardown_fn=lambda: conf(r2, ["interface Ethernet0/0", "no ip access-group BLOCK-POC in", "exit", "no ip access-list extended BLOCK-POC"]))
    run("P2f encapsulation failed(next-hop が ARP 応答しない)",
        lambda: conf(r2, ["ip route 172.31.100.0 255.255.255.0 10.0.23.99"]),
        r1, "172.31.100.1",
        teardown_fn=lambda: conf(r2, ["no ip route 172.31.100.0 255.255.255.0 10.0.23.99"]))
    run("P2g detail(forus・ICMP type/code)", None, r1, "10.0.12.2", detail=True)
    run("P2h detail(transit)", None, r1, "10.0.23.3", detail=True)
    conf(r2, ["no access-list 199"])
    flush("P2 debug ip packet")



# =========================================================================
# P1b classic EIGRP の `?`(named の AS と衝突しない番号で) / P2x プロセススイッチ変種
# =========================================================================
def P1b(devs):
    d = devs["RT01"]
    conf(d, ["no router eigrp NAMED"])
    hc(d, ["router eigrp 200"], "", "P1b eigrp classic: (config-router)")
    hc(d, ["router eigrp 200"], "passive-interface ", "P1b eigrp classic: passive-interface ?")
    hc(d, ["interface Ethernet0/0"], "ip summary-address ", "P1b classic IF: ip summary-address ?")
    hc(d, ["interface Ethernet0/0"], "ip hello-interval eigrp 200 ", "P1b classic IF: ip hello-interval eigrp 200 ?")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 300", "af-interface Ethernet0/0"],
       "summary-address ", "P1b named af-interface: summary-address ?")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 300", "topology base"],
       "distance ", "P1b named af-topology: distance ?")
    hc(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 300"],
       "network ", "P1b named af: network ?")
    conf(d, ["no router eigrp 200", "no router eigrp NAMED"])
    flush("P1b classic/named 追加採取")


def P2x(devs):
    r1, r2 = devs["RT01"], devs["RT02"]
    conf(r2, ["access-list 199 permit ip host 10.0.12.1 any", "access-list 199 permit ip any host 10.0.12.1",
              "interface Ethernet0/0", "no ip route-cache", "exit", "interface Ethernet0/1", "no ip route-cache"])
    note("P2x: RT02 の Et0/0・Et0/1 で no ip route-cache(プロセススイッチ化)")

    def run(title, setup_fn, ping_dev, dst, detail=False, teardown_fn=None):
        if setup_fn:
            setup_fn()
        clear_log(r2)
        sh(r2, f"debug ip packet 199{' detail' if detail else ''}")
        rate, _ = ping(ping_dev, dst, repeat=2)
        time.sleep(3)
        sh(r2, "undebug all")
        note(f"{title}: ping {ping_dev.name}→{dst} = {rate}%")
        logtail(r2, title, include=r"IP:|ICMP")
        if teardown_fn:
            teardown_fn()

    run("P2x-b transit forward(no ip route-cache)", None, r1, "10.0.23.3")
    run("P2x-f encapsulation failed(no ip route-cache・next-hop が ARP 応答しない)",
        lambda: conf(r2, ["ip route 172.31.100.0 255.255.255.0 10.0.23.99"]),
        r1, "172.31.100.1",
        teardown_fn=lambda: conf(r2, ["no ip route 172.31.100.0 255.255.255.0 10.0.23.99"]))
    run("P2x-h detail transit(no ip route-cache)", None, r1, "10.0.23.3", detail=True)
    run("P2x-d unroutable(no ip route-cache)", None, r1, "172.31.99.1")
    conf(r2, ["interface Ethernet0/0", "ip route-cache", "exit", "interface Ethernet0/1", "ip route-cache", "exit", "no access-list 199"])
    flush("P2x debug ip packet(プロセススイッチ)")


def P1c(devs):
    d = devs["RT01"]
    # MQC の DSCP/precedence キーワード
    hc(d, ["policy-map PM-POC", "class class-default"], "set dscp ", "P1c MQC: set dscp ?")
    hc(d, ["policy-map PM-POC", "class class-default"], "set precedence ", "P1c MQC: set precedence ?")
    hc(d, ["policy-map PM-POC", "class class-default"], "set ip dscp ", "P1c MQC: set ip dscp ?")
    conf(d, ["policy-map PM-POC", "class class-default", "set dscp af31", "exit", "exit"])
    block("P1c show policy-map PM-POC(dscp の表示形)", sh(d, "show policy-map PM-POC"))
    conf(d, ["no policy-map PM-POC"])
    # 数値で入れた precedence の表示形
    conf(d, ["route-map RM-POC2 permit 10", "set ip precedence 1", "set ip tos 8", "exit"])
    block("P1c show route-map RM-POC2(数値指定の表示形)", sh(d, "show route-map RM-POC2"))
    block("P1c show run | section route-map RM-POC2", sh(d, "show running-config | section route-map RM-POC2"))
    conf(d, ["no route-map RM-POC2"])
    # named の af / af-topology で重複する語の弁別
    AF = ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 300"]
    hc(d, AF, "metric ", "P1c named af: metric ?")
    hc(d, AF + ["topology base"], "metric ", "P1c named af-topology: metric ?")
    hc(d, AF, "timers ", "P1c named af: timers ?")
    hc(d, AF + ["topology base"], "timers ", "P1c named af-topology: timers ?")
    hc(d, AF, "eigrp stub ", "P1c named af: eigrp stub ?")
    hc(d, AF + ["af-interface Ethernet0/0"], "", "P1c named af-interface Ethernet0/0: ?")
    hc(d, AF + ["af-interface Ethernet0/0"], "authentication mode ", "P1c named af-interface: authentication mode ?")
    hc(d, AF + ["topology base"], "variance ", "P1c named af-topology: variance ?")
    conf(d, ["no router eigrp NAMED"])
    flush("P1c MQC/named 追加採取")

# =========================================================================
# P3 OSPF 隣接 debug 指紋
# =========================================================================
OSPF_BASE = {
    "RT01": ["router ospf 1", "router-id 1.1.1.1", "network 10.0.12.0 0.0.0.255 area 0", "exit"],
    "RT02": ["router ospf 1", "router-id 2.2.2.2", "network 10.0.12.0 0.0.0.255 area 0", "exit"],
}


def _nbr(dev):
    return sh(dev, "show ip ospf neighbor")


def _wait_full(devs, timeout=120):
    def chk():
        a, b = _nbr(devs["RT01"]), _nbr(devs["RT02"])
        return ("FULL" in a and "FULL" in b), (a + "\n" + b)
    return wait_for(chk, timeout=timeout, step=10, what="OSPF FULL")


def _dbg_on(dev, extra=()):
    for c in ("debug ip ospf adj", "debug ip ospf hello", "debug ip ospf events") + tuple(extra):
        sh(dev, c)


def _dbg_off(dev):
    sh(dev, "undebug all")


def _ospf_reset(devs):
    for n in ("RT01", "RT02"):
        sh(devs[n], "clear ip ospf process")


def P3(devs):
    r1, r2 = devs["RT01"], devs["RT02"]
    for n in ("RT01", "RT02"):
        conf(devs[n], OSPF_BASE[n])
    t, info = _wait_full(devs)
    block("P3 基線 OSPF FULL", f"{t}s\n{info}")

    def variant(title, apply, wait_s=75, reset=True, restore=None, include=r"OSPF|ospf", extra_show=()):
        note(f"--- {title} ---")
        clear_log(r1); clear_log(r2)
        _dbg_on(r1); _dbg_on(r2)
        apply()
        if reset:
            _ospf_reset(devs)
        time.sleep(wait_s)
        block(f"{title} — RT01 show ip ospf neighbor", _nbr(r1))
        block(f"{title} — RT02 show ip ospf neighbor", _nbr(r2))
        for dev, cmd in extra_show:
            block(f"{title} — {dev.name}# {cmd}", sh(dev, cmd))
        _dbg_off(r1); _dbg_off(r2)
        logtail(r1, title + " [RT01]", include=include)
        logtail(r2, title + " [RT02]", include=include)
        if restore:
            restore()
        _ospf_reset(devs)
        t, info = _wait_full(devs)
        note(f"{title}: 復旧 FULL = {t}s")
        if t is None:
            block(f"{title} 復旧失敗 neighbor", info)

    # (a) MTU 不一致: RT02 が小さい
    variant("P3a mtu(RT02 ip mtu 1400 = 小さい側)",
            lambda: conf(r2, ["interface Ethernet0/0", "ip mtu 1400"]), wait_s=170,
            restore=lambda: conf(r2, ["interface Ethernet0/0", "no ip mtu"]))
    # (a2) mtu-ignore を小さい側だけ
    variant("P3a2 mtu + mtu-ignore を RT02(小さい側)だけ",
            lambda: conf(r2, ["interface Ethernet0/0", "ip mtu 1400", "ip ospf mtu-ignore"]), wait_s=60,
            restore=lambda: conf(r2, ["interface Ethernet0/0", "no ip mtu", "no ip ospf mtu-ignore"]))
    # (a3) mtu-ignore を大きい側だけ
    variant("P3a3 mtu + mtu-ignore を RT01(大きい側)だけ",
            lambda: (conf(r2, ["interface Ethernet0/0", "ip mtu 1400"]), conf(r1, ["interface Ethernet0/0", "ip ospf mtu-ignore"])),
            wait_s=60,
            restore=lambda: (conf(r2, ["interface Ethernet0/0", "no ip mtu"]), conf(r1, ["interface Ethernet0/0", "no ip ospf mtu-ignore"])))
    # (b) hello 不一致
    variant("P3b hello(RT02 hello-interval 5)",
            lambda: conf(r2, ["interface Ethernet0/0", "ip ospf hello-interval 5"]), wait_s=50, reset=False,
            restore=lambda: conf(r2, ["interface Ethernet0/0", "no ip ospf hello-interval"]))
    # (c) area 不一致
    variant("P3c area(RT02 を area 1)",
            lambda: conf(r2, ["router ospf 1", "no network 10.0.12.0 0.0.0.255 area 0", "network 10.0.12.0 0.0.0.255 area 1"]),
            wait_s=50, reset=False,
            restore=lambda: conf(r2, ["router ospf 1", "no network 10.0.12.0 0.0.0.255 area 1", "network 10.0.12.0 0.0.0.255 area 0"]))
    # (d) auth type 不一致(RT02 のみ MD5)
    variant("P3d auth_type(RT02 のみ message-digest)",
            lambda: conf(r2, ["interface Ethernet0/0", "ip ospf authentication message-digest", "ip ospf message-digest-key 1 md5 POCKEY"]),
            wait_s=50, reset=False,
            restore=lambda: conf(r2, ["interface Ethernet0/0", "no ip ospf authentication", "no ip ospf message-digest-key 1"]))
    # (e) auth key 不一致(両側 MD5・鍵違い) / 鍵ID違い
    variant("P3e auth_key(両側 MD5・鍵文字列違い)",
            lambda: (conf(r1, ["interface Ethernet0/0", "ip ospf authentication message-digest", "ip ospf message-digest-key 1 md5 POCKEY"]),
                     conf(r2, ["interface Ethernet0/0", "ip ospf authentication message-digest", "ip ospf message-digest-key 1 md5 WRONGKEY"])),
            wait_s=50, reset=False,
            restore=lambda: (conf(r1, ["interface Ethernet0/0", "no ip ospf authentication", "no ip ospf message-digest-key 1"]),
                             conf(r2, ["interface Ethernet0/0", "no ip ospf authentication", "no ip ospf message-digest-key 1"])))
    variant("P3e2 auth_keyid(両側 MD5・鍵ID違い 1 vs 2)",
            lambda: (conf(r1, ["interface Ethernet0/0", "ip ospf authentication message-digest", "ip ospf message-digest-key 1 md5 POCKEY"]),
                     conf(r2, ["interface Ethernet0/0", "ip ospf authentication message-digest", "ip ospf message-digest-key 2 md5 POCKEY"])),
            wait_s=50, reset=False,
            restore=lambda: (conf(r1, ["interface Ethernet0/0", "no ip ospf authentication", "no ip ospf message-digest-key 1"]),
                             conf(r2, ["interface Ethernet0/0", "no ip ospf authentication", "no ip ospf message-digest-key 2"])))
    # (f) network type 不一致(RT02 p2p)
    variant("P3f nettype(RT02 point-to-point・RT01 broadcast)",
            lambda: conf(r2, ["interface Ethernet0/0", "ip ospf network point-to-point"]), wait_s=60,
            restore=lambda: conf(r2, ["interface Ethernet0/0", "no ip ospf network"]),
            extra_show=((r1, "show ip route ospf"), (r2, "show ip route ospf"), (r1, "show ip ospf interface Ethernet0/0 | include Network Type|Neighbor|State"),
                        (r2, "show ip ospf interface Ethernet0/0 | include Network Type|Neighbor|State")))
    # (g) priority 0 同士
    variant("P3g prio0(両側 priority 0)",
            lambda: (conf(r1, ["interface Ethernet0/0", "ip ospf priority 0"]), conf(r2, ["interface Ethernet0/0", "ip ospf priority 0"])),
            wait_s=60,
            restore=lambda: (conf(r1, ["interface Ethernet0/0", "no ip ospf priority"]), conf(r2, ["interface Ethernet0/0", "no ip ospf priority"])))
    # (h) stub E-bit 不一致(area 1 に移して RT02 だけ stub)
    variant("P3h stub(両側 area 1・RT02 だけ area 1 stub)",
            lambda: (conf(r1, ["router ospf 1", "no network 10.0.12.0 0.0.0.255 area 0", "network 10.0.12.0 0.0.0.255 area 1"]),
                     conf(r2, ["router ospf 1", "no network 10.0.12.0 0.0.0.255 area 0", "network 10.0.12.0 0.0.0.255 area 1", "area 1 stub"])),
            wait_s=50, reset=False,
            restore=lambda: (conf(r1, ["router ospf 1", "no network 10.0.12.0 0.0.0.255 area 1", "network 10.0.12.0 0.0.0.255 area 0"]),
                             conf(r2, ["router ospf 1", "no area 1 stub", "no network 10.0.12.0 0.0.0.255 area 1", "network 10.0.12.0 0.0.0.255 area 0"])))
    # (i) passive(RT02)
    variant("P3i passive(RT02 passive-interface Ethernet0/0)",
            lambda: conf(r2, ["router ospf 1", "passive-interface Ethernet0/0"]), wait_s=60, reset=False,
            restore=lambda: conf(r2, ["router ospf 1", "no passive-interface Ethernet0/0"]))
    # (j) RID 重複
    variant("P3j dup_rid(RT02 router-id 1.1.1.1)",
            lambda: conf(r2, ["router ospf 1", "router-id 1.1.1.1"]), wait_s=60,
            restore=lambda: conf(r2, ["router ospf 1", "router-id 2.2.2.2"]), include=r"OSPF|ospf")
    # (k) 片方向(RT02 が OSPF を受信できない)
    variant("P3k unidir(RT02 inbound ACL で OSPF(89) を拒否)",
            lambda: conf(r2, ["ip access-list extended NO-OSPF-IN", "deny ospf any any", "permit ip any any", "exit",
                              "interface Ethernet0/0", "ip access-group NO-OSPF-IN in"]), wait_s=60,
            restore=lambda: conf(r2, ["interface Ethernet0/0", "no ip access-group NO-OSPF-IN in", "exit", "no ip access-list extended NO-OSPF-IN"]))
    for n in ("RT01", "RT02"):
        conf(devs[n], ["no router ospf 1"])
    flush("P3 OSPF 隣接 debug 指紋")



def P3h2(devs):
    """stub(E-bit)不一致の再測: clear 付き・長め wait で最終隣接を確定する。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    for n in ("RT01", "RT02"):
        conf(devs[n], OSPF_BASE[n])
    t, info = _wait_full(devs)
    block("P3h2 基線 OSPF FULL", f"{t}s\n{info}")
    clear_log(r1); clear_log(r2)
    _dbg_on(r1); _dbg_on(r2)
    conf(r1, ["router ospf 1", "no network 10.0.12.0 0.0.0.255 area 0", "network 10.0.12.0 0.0.0.255 area 1"])
    conf(r2, ["router ospf 1", "no network 10.0.12.0 0.0.0.255 area 0", "network 10.0.12.0 0.0.0.255 area 1", "area 1 stub"])
    _ospf_reset(devs)
    # dead(40s)を必ず跨ぐよう長めに待つ
    time.sleep(75)
    block("P3h2 stub 不一致(clear 後) — RT01 show ip ospf neighbor", _nbr(r1))
    block("P3h2 stub 不一致(clear 後) — RT02 show ip ospf neighbor", _nbr(r2))
    _dbg_off(r1); _dbg_off(r2)
    logtail(r1, "P3h2 [RT01]", include=r"OSPF|ospf|Stub|option")
    logtail(r2, "P3h2 [RT02]", include=r"OSPF|ospf|Stub|option")
    # restore
    conf(r1, ["router ospf 1", "no network 10.0.12.0 0.0.0.255 area 1", "network 10.0.12.0 0.0.0.255 area 0"])
    conf(r2, ["router ospf 1", "no area 1 stub", "no network 10.0.12.0 0.0.0.255 area 1", "network 10.0.12.0 0.0.0.255 area 0"])
    _ospf_reset(devs)
    t, info = _wait_full(devs)
    note(f"P3h2 復旧 FULL = {t}s")
    for n in ("RT01", "RT02"):
        conf(devs[n], ["no router ospf 1"])
    flush("P3h2 stub 再測")


def P3h3(devs):
    """stub(E-bit)不一致の再測(P6 後のアドレス 172.16.12.0/24 で・clear 付き・長め wait)。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    base = {"RT01": ["router ospf 1", "router-id 1.1.1.1", "network 172.16.12.0 0.0.0.255 area 1", "exit"],
            "RT02": ["router ospf 1", "router-id 2.2.2.2", "network 172.16.12.0 0.0.0.255 area 1", "exit"]}
    for n in ("RT01", "RT02"):
        conf(devs[n], base[n])
    t, info = _wait_full(devs)
    block("P3h3 基線 OSPF FULL(area 1・両側 non-stub)", f"{t}s\n{info}")
    clear_log(r1); clear_log(r2)
    _dbg_on(r1); _dbg_on(r2)
    conf(r2, ["router ospf 1", "area 1 stub"])
    _ospf_reset(devs)
    time.sleep(75)
    block("P3h3 stub 不一致(RT02 だけ area 1 stub・clear 後 75s) — RT01 show ip ospf neighbor", _nbr(r1))
    block("P3h3 stub 不一致 — RT02 show ip ospf neighbor", _nbr(r2))
    _dbg_off(r1); _dbg_off(r2)
    logtail(r1, "P3h3 [RT01]", include=r"OSPF|ospf|Stub|option")
    logtail(r2, "P3h3 [RT02]", include=r"OSPF|ospf|Stub|option")
    # 両側 stub にすると FULL に戻るか(対照)
    conf(r1, ["router ospf 1", "area 1 stub"])
    _ospf_reset(devs)
    t, info = _wait_full(devs)
    block(f"P3h3 対照: 両側 area 1 stub → FULL = {t}s", info)
    for n in ("RT01", "RT02"):
        conf(devs[n], ["no router ospf 1"])
    flush("P3h3 stub 再測(正しいアドレス)")


def P3a4(devs):
    """R2a 再確認: mtu-ignore は小さい MTU 側で解決するか(側と順序を入れ替えて 4 回)。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    for n in ("RT01", "RT02"):
        conf(devs[n], OSPF_BASE[n])
    t, info = _wait_full(devs)
    block("P3a4 基線 FULL", f"{t}s\n{info}")

    def trial(title, small, ignore_on, wait_s=70):
        big = r1 if small is r2 else r2
        conf(small, ["interface Ethernet0/0", "ip mtu 1400"])
        for dev in ignore_on:
            conf(dev, ["interface Ethernet0/0", "ip ospf mtu-ignore"])
        _ospf_reset(devs)
        time.sleep(wait_s)
        a, b = _nbr(r1), _nbr(r2)
        full = ("FULL" in a and "FULL" in b)
        block(f"{title} → FULL={full}", a + "\n" + b)
        for dev in (r1, r2):
            conf(dev, ["interface Ethernet0/0", "no ip mtu", "no ip ospf mtu-ignore"])
        _ospf_reset(devs)
        _wait_full(devs, timeout=90)
        return full

    res = {}
    res["small=RT02 ignore=RT02(小)"] = trial("P3a4-1 小=RT02・ignore 小側だけ", r2, [r2])
    res["small=RT02 ignore=RT01(大)"] = trial("P3a4-2 小=RT02・ignore 大側だけ", r2, [r1])
    res["small=RT01 ignore=RT01(小)"] = trial("P3a4-3 小=RT01・ignore 小側だけ", r1, [r1])
    res["small=RT01 ignore=RT02(大)"] = trial("P3a4-4 小=RT01・ignore 大側だけ", r1, [r2])
    res["small=RT02 ignore=両側"] = trial("P3a4-5 小=RT02・ignore 両側", r2, [r1, r2])
    note("P3a4 まとめ: " + " / ".join(f"{k}: {'FULL' if v else 'NOT FULL'}" for k, v in res.items()))
    for n in ("RT01", "RT02"):
        conf(devs[n], ["no router ospf 1"])
    flush("P3a4 mtu-ignore の側(R2a 再確認)")

# =========================================================================
# P4 BFD ネゴ
# =========================================================================
def P4(devs):
    r3, r4 = devs["RT03"], devs["RT04"]
    conf(r3, ["router ospf 1", "router-id 3.3.3.3", "network 10.0.34.0 0.0.0.255 area 0", "bfd all-interfaces", "exit",
              "interface Ethernet0/0", "bfd interval 100 min_rx 100 multiplier 3"])
    conf(r4, ["router ospf 1", "router-id 4.4.4.4", "network 10.0.34.0 0.0.0.255 area 0", "bfd all-interfaces", "exit",
              "interface Ethernet0/0", "bfd interval 300 min_rx 200 multiplier 5"])
    def up():
        a = sh(r3, "show bfd neighbors")
        return ("Up" in a), a
    t, info = wait_for(up, timeout=120, step=10, what="BFD Up")
    block(f"P4a BFD 非対称(RT03 tx100/rx100/m3・RT04 tx300/rx200/m5) Up={t}s", info)
    block("P4a — RT03 show bfd neighbors details", sh(r3, "show bfd neighbors details"))
    block("P4a — RT04 show bfd neighbors details", sh(r4, "show bfd neighbors details"))
    block("P4a — RT03 show ip ospf interface Ethernet0/0 | include BFD|Hello", sh(r3, "show ip ospf interface Ethernet0/0 | include BFD|Hello"))
    # template 形(RT03 側だけ template)
    conf(r3, ["interface Ethernet0/0", "no bfd interval 100 min_rx 100 multiplier 3", "exit",
              "bfd-template single-hop T-POC", "interval min-tx 50 min-rx 50 multiplier 4", "exit",
              "interface Ethernet0/0", "bfd template T-POC"])
    time.sleep(25)
    block("P4b template(RT03 min-tx50/min-rx50/m4 template・RT04 据置) — RT03 details", sh(r3, "show bfd neighbors details"))
    block("P4b — RT04 details", sh(r4, "show bfd neighbors details"))
    block("P4b — RT03 show bfd summary", sh(r3, "show bfd summary"))
    # echo 無効の見え方
    conf(r3, ["interface Ethernet0/0", "no bfd echo"])
    time.sleep(20)
    block("P4c no bfd echo(RT03) — RT03 details", sh(r3, "show bfd neighbors details"))
    conf(r3, ["interface Ethernet0/0", "bfd echo", "no bfd template T-POC", "exit", "no bfd-template single-hop T-POC", "no router ospf 1"])
    conf(r4, ["interface Ethernet0/0", "no bfd interval 300 min_rx 200 multiplier 5", "exit", "no router ospf 1"])
    flush("P4 BFD ネゴ")


# =========================================================================
# P5 DHCPv6
# =========================================================================
def _bounce(dev, ifname="Ethernet0/0"):
    conf(dev, [f"interface {ifname}", "shutdown"])
    time.sleep(3)
    conf(dev, [f"interface {ifname}", "no shutdown"])


def _v6show(r3, r4, title):
    time.sleep(25)
    block(f"{title} — RT04 show ipv6 interface brief", sh(r4, "show ipv6 interface brief"))
    block(f"{title} — RT04 show ipv6 dhcp interface Ethernet0/0", sh(r4, "show ipv6 dhcp interface Ethernet0/0"))
    block(f"{title} — RT04 show ipv6 routers", sh(r4, "show ipv6 routers"))
    block(f"{title} — RT04 show hosts | include Default|Name", sh(r4, "show hosts | include Default|Name"))
    block(f"{title} — RT03 show ipv6 dhcp binding", sh(r3, "show ipv6 dhcp binding"))
    block(f"{title} — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast", sh(r3, "show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast"))


def P5(devs):
    r3, r4 = devs["RT03"], devs["RT04"]
    # stateless
    conf(r3, ["ipv6 unicast-routing", "ipv6 dhcp pool P6", "dns-server 2001:4860:4860::8888", "domain-name example.net", "exit",
              "interface Ethernet0/0", "ipv6 address 2001:DB8:34::3/64", "ipv6 dhcp server P6", "ipv6 nd other-config-flag"])
    conf(r4, ["interface Ethernet0/0", "ipv6 address autoconfig"])
    _bounce(r4)
    _v6show(r3, r4, "P5a stateless(O flag + autoconfig)")
    # cause c4: O flag だが server 未 attach
    conf(r3, ["interface Ethernet0/0", "no ipv6 dhcp server P6"])
    _bounce(r4)
    _v6show(r3, r4, "P5c4 O flag だが ipv6 dhcp server 未attach")
    conf(r3, ["interface Ethernet0/0", "ipv6 dhcp server P6"])
    # cause c1: no ipv6 unicast-routing
    conf(r3, ["no ipv6 unicast-routing"])
    _bounce(r4)
    _v6show(r3, r4, "P5c1 no ipv6 unicast-routing(RA 送出側)")
    conf(r3, ["ipv6 unicast-routing"])
    # cause c2: ra suppress
    conf(r3, ["interface Ethernet0/0", "ipv6 nd ra suppress all"])
    _bounce(r4)
    _v6show(r3, r4, "P5c2 ipv6 nd ra suppress all")
    conf(r3, ["interface Ethernet0/0", "no ipv6 nd ra suppress all"])
    # cause c5: IPv6 ACL(host 許可のみ)が RA を落とす(BL-160 の紙面化)
    conf(r4, ["ipv6 access-list ACL-POC", "permit ipv6 host 2001:DB8:34::3 any", "exit",
              "interface Ethernet0/0", "ipv6 traffic-filter ACL-POC in"])
    _bounce(r4)
    _v6show(r3, r4, "P5c5 IPv6 ACL(GUA host のみ許可)が LL 送信元の RA を落とす")
    block("P5c5 — RT04 show ipv6 access-list", sh(r4, "show ipv6 access-list"))
    conf(r4, ["interface Ethernet0/0", "no ipv6 traffic-filter ACL-POC in", "exit", "no ipv6 access-list ACL-POC"])
    # stateful
    conf(r3, ["ipv6 dhcp pool P6", "address prefix 2001:DB8:34::/64 lifetime infinite infinite", "exit",
              "interface Ethernet0/0", "ipv6 nd managed-config-flag", "ipv6 nd prefix 2001:DB8:34::/64 2592000 604800 no-autoconfig"])
    conf(r4, ["interface Ethernet0/0", "no ipv6 address autoconfig", "ipv6 enable", "ipv6 address dhcp"])
    _bounce(r4)
    _v6show(r3, r4, "P5b stateful(M flag + address prefix + no-autoconfig / client ipv6 address dhcp)")
    # cause c3: M flag だが pool に address prefix が無い
    conf(r3, ["ipv6 dhcp pool P6", "no address prefix 2001:DB8:34::/64"])
    sh(r4, "clear ipv6 dhcp client Ethernet0/0")
    _bounce(r4)
    _v6show(r3, r4, "P5c3 M flag だが pool に address prefix 無し")
    # cause c6: ipv6 address dhcp に ipv6 enable 無し(既知罠の再確認)
    conf(r3, ["ipv6 dhcp pool P6", "address prefix 2001:DB8:34::/64 lifetime infinite infinite"])
    conf(r4, ["interface Ethernet0/0", "no ipv6 address dhcp", "no ipv6 enable", "ipv6 address dhcp"])
    _bounce(r4)
    _v6show(r3, r4, "P5c6 ipv6 address dhcp のみ(ipv6 enable 無し)")
    # cleanup
    conf(r4, ["interface Ethernet0/0", "no ipv6 address dhcp", "no ipv6 enable", "no ipv6 address autoconfig"])
    conf(r3, ["interface Ethernet0/0", "no ipv6 dhcp server P6", "no ipv6 nd managed-config-flag", "no ipv6 nd other-config-flag",
              "no ipv6 nd prefix 2001:DB8:34::/64", "no ipv6 address 2001:DB8:34::3/64", "exit", "no ipv6 dhcp pool P6"])
    flush("P5 DHCPv6")


# =========================================================================
# P6 EIGRP auto-summary 境界(全台を再アドレス)
# =========================================================================
def P6(devs):
    r1, r2, r3, r4 = (devs[n] for n in NODES)
    for n in NODES:
        conf(devs[n], ["no router ospf 1"])
    conf(r1, ["no ip route 0.0.0.0 0.0.0.0 10.0.12.2", "interface Loopback0", "ip address 172.16.11.1 255.255.255.0", "exit",
              "interface Ethernet0/0", "ip address 172.16.12.1 255.255.255.0"])
    conf(r2, ["no ip route 10.0.34.0 255.255.255.0 10.0.23.3", "interface Ethernet0/0", "ip address 172.16.12.2 255.255.255.0", "exit",
              "interface Ethernet0/1", "ip address 172.17.23.2 255.255.255.0"])
    conf(r3, ["no ip route 10.0.12.0 255.255.255.0 10.0.23.2", "interface Ethernet0/1", "ip address 172.17.23.3 255.255.255.0", "exit",
              "interface Ethernet0/0", "ip address 172.16.34.3 255.255.255.0"])
    conf(r4, ["no ip route 0.0.0.0 0.0.0.0 10.0.34.3", "interface Loopback0", "ip address 172.16.41.4 255.255.255.0", "exit",
              "interface Ethernet0/0", "ip address 172.16.34.4 255.255.255.0"])
    for n in NODES:
        conf(devs[n], ["router eigrp 1", "network 172.16.0.0", "network 172.17.0.0", "auto-summary", "exit"])
    time.sleep(30)
    block("P6 show run | section router eigrp (RT02)", sh(r2, "show running-config | section router eigrp"))

    def snap(title):
        for d in (r1, r2, r3, r4):
            block(f"{title} — {d.name} show ip route eigrp", sh(d, "show ip route eigrp"))
        block(f"{title} — RT01 show ip route 172.16.41.4", sh(r1, "show ip route 172.16.41.4"))
        ping(r1, "172.16.41.4", source="172.16.11.1", repeat=3, title=f"{title} ping RT01(172.16.11.1)→172.16.41.4")
        ping(r4, "172.16.11.1", source="172.16.41.4", repeat=3, title=f"{title} ping RT04(172.16.41.4)→172.16.11.1")

    snap("P6a 全台 auto-summary(壊れた基線)")
    conf(r1, ["router eigrp 1", "no auto-summary"])
    time.sleep(20)
    snap("P6b 非境界 RT01 だけ no auto-summary(効かないはず)")
    conf(r1, ["router eigrp 1", "auto-summary"])
    conf(r2, ["router eigrp 1", "no auto-summary"])
    time.sleep(20)
    snap("P6c 境界 RT02 だけ no auto-summary(片側)")
    conf(r3, ["router eigrp 1", "no auto-summary"])
    time.sleep(20)
    snap("P6d 境界 RT02+RT03 no auto-summary(両側)")
    flush("P6 EIGRP auto-summary 境界")


# =========================================================================
# P7 DMVPN show 指紋(hub=RT02・spoke=RT01/RT03/RT04・tunnel source=Lo0・IKEv2 PSK・Phase3)
#   underlay は static /32(Lo 宛)。overlay 10.255.0.0/24・LAN=Loopback1 192.168.N.0/24・EIGRP 100
# =========================================================================
OV = "10.255.0"
TIP = {"RT01": f"{OV}.1", "RT02": f"{OV}.2", "RT03": f"{OV}.3", "RT04": f"{OV}.4"}
LO = {"RT01": "1.1.1.1", "RT02": "2.2.2.2", "RT03": "3.3.3.3", "RT04": "4.4.4.4"}
LAN = {n: f"192.168.{i + 1}.1" for i, n in enumerate(NODES)}
NHRP_KEY, TKEY, NETID, PSK, ASN = "DMVPNKEY", 100, 1, "Ss2026#Poc", 100
DMVPN_INC = r"NHRP|CRYPTO|IKEV2|IPSEC|TUN|DMVPN|DUAL"


def _crypto():
    return ["crypto ikev2 proposal PROP-POC", "encryption aes-cbc-256", "integrity sha256", "group 14", "exit",
            "crypto ikev2 policy POL-POC", "proposal PROP-POC", "exit",
            "crypto ikev2 keyring KR-POC", "peer ANY", "address 0.0.0.0 0.0.0.0", f"pre-shared-key {PSK}", "exit", "exit",
            "crypto ikev2 profile IKEV2-POC", "match identity remote address 0.0.0.0", "authentication remote pre-share",
            "authentication local pre-share", "keyring local KR-POC", "exit",
            "crypto ipsec transform-set TS-POC esp-aes 256 esp-sha256-hmac", "mode transport", "exit",
            "crypto ipsec profile IPSEC-POC", "set transform-set TS-POC", "set ikev2-profile IKEV2-POC", "exit"]


def _tun_hub():
    return ["interface Tunnel0", f"ip address {TIP['RT02']} 255.255.255.0", "no ip redirects", "ip mtu 1400",
            "ip tcp adjust-mss 1360", f"ip nhrp authentication {NHRP_KEY}", "ip nhrp map multicast dynamic",
            f"ip nhrp network-id {NETID}", "ip nhrp redirect", f"no ip split-horizon eigrp {ASN}",
            "tunnel source Loopback0", "tunnel mode gre multipoint", f"tunnel key {TKEY}",
            "tunnel protection ipsec profile IPSEC-POC", "exit"]


def _tun_spoke(n):
    return ["interface Tunnel0", f"ip address {TIP[n]} 255.255.255.0", "no ip redirects", "ip mtu 1400",
            "ip tcp adjust-mss 1360", f"ip nhrp authentication {NHRP_KEY}", f"ip nhrp network-id {NETID}",
            f"ip nhrp nhs {TIP['RT02']} nbma {LO['RT02']} multicast", "ip nhrp shortcut",
            "tunnel source Loopback0", "tunnel mode gre multipoint", f"tunnel key {TKEY}",
            "tunnel protection ipsec profile IPSEC-POC", "exit"]


def _dmvpn_up(hub, tip):
    o = sh(hub, "show dmvpn")
    return bool(re.search(re.escape(tip) + r"\s+UP", o)), o


def P7(devs):
    r1, r2, r3, r4 = (devs[n] for n in NODES)
    hub, spokes = r2, [r1, r3, r4]
    # ---- underlay: Lo 宛 static ＋ LAN loopback ----
    conf(r2, ["ip route 1.1.1.1 255.255.255.255 10.0.12.1", "ip route 3.3.3.3 255.255.255.255 10.0.23.3",
              "ip route 4.4.4.4 255.255.255.255 10.0.23.3"])
    conf(r3, ["ip route 2.2.2.2 255.255.255.255 10.0.23.2", "ip route 1.1.1.1 255.255.255.255 10.0.23.2",
              "ip route 4.4.4.4 255.255.255.255 10.0.34.4"])
    for n in NODES:
        conf(devs[n], ["interface Loopback1", f"ip address {LAN[n]} 255.255.255.0", "exit"])
    for s in spokes:
        ping(s, LO["RT02"], source=LO[s.name], title=f"P7-0 underlay {s.name} Lo0→hub Lo0")
    ping(r1, LO["RT04"], source=LO["RT01"], title="P7-0 underlay RT01 Lo0→RT04 Lo0")
    # ---- crypto / tunnel / EIGRP ----
    for n in NODES:
        conf(devs[n], _crypto(), title=f"P7-0 crypto {n}")
    conf(hub, _tun_hub(), title="P7-0 hub(RT02) Tunnel0")
    for s in spokes:
        conf(s, _tun_spoke(s.name), title=f"P7-0 spoke {s.name} Tunnel0")
    for i, n in enumerate(NODES):
        conf(devs[n], [f"router eigrp {ASN}", f"network {OV}.0 0.0.0.255", f"network 192.168.{i + 1}.0 0.0.0.255", "exit"])

    def up3():
        o = sh(hub, "show dmvpn")
        return len(re.findall(r"\bUP\b", o)) >= 3, o
    t, info = wait_for(up3, timeout=300, step=15, what="hub 3 spoke UP")
    block(f"P7a 基線 hub show dmvpn (3 UP after {t}s)", info)
    for c in ["show dmvpn detail", "show ip nhrp", "show ip nhrp brief", "show ip nhrp detail", "show ip nhrp multicast",
              "show ip nhrp nhs detail", "show crypto ikev2 sa", "show crypto ipsec sa | include peer|encaps|decaps|in use",
              "show crypto socket", "show running-config interface Tunnel0", "show ip eigrp neighbors",
              "show ip route eigrp", "show ip interface brief | include Tunnel|Loopback"]:
        block("P7a 基線 hub", sh(hub, c))
    # spoke 基線(shortcut 前)
    def rt():
        o = sh(r1, "show ip route eigrp")
        return "192.168.4.0" in o, o
    t, info = wait_for(rt, timeout=120, step=10, what="RT01 に 192.168.4.0 (EIGRP)")
    block(f"P7a 基線 RT01 show ip route eigrp (192.168.4.0 after {t}s)", info)
    for c in ["show dmvpn", "show dmvpn detail", "show ip nhrp", "show ip nhrp nhs detail", "show ip nhrp nhs",
              "show running-config interface Tunnel0", "show ip eigrp neighbors", "show ip route 192.168.4.1",
              "show ip nhrp shortcut", "show ip route next-hop-override", "show crypto ikev2 sa"]:
        block("P7a 基線 RT01(shortcut 前)", sh(r1, c))
    block("P7a 基線 RT01 traceroute 192.168.4.1 (shortcut 前)", sh(r1, "traceroute 192.168.4.1 source 192.168.1.1 numeric timeout 2 probe 1", timeout=120))
    # ---- spoke 間通信 → shortcut 後 ----
    ping(r1, LAN["RT04"], source=LAN["RT01"], repeat=5, title="P7a RT01 LAN→RT04 LAN (Phase3 トリガ)")
    time.sleep(8)
    ping(r1, LAN["RT04"], source=LAN["RT01"], repeat=5, title="P7a RT01 LAN→RT04 LAN (2 回目)")
    block("P7a RT01 traceroute 192.168.4.1 (shortcut 後)", sh(r1, "traceroute 192.168.4.1 source 192.168.1.1 numeric timeout 2 probe 1", timeout=120))
    for c in ["show dmvpn", "show dmvpn detail", "show ip nhrp", "show ip nhrp detail", "show ip nhrp shortcut",
              "show ip route next-hop-override", "show ip route 192.168.4.1", "show ip cef 192.168.4.1",
              "show crypto ikev2 sa", "show crypto ipsec sa | include peer|encaps|decaps|in use", "show ip nhrp traffic"]:
        block("P7a RT01(shortcut 後)", sh(r1, c))
    for c in ["show dmvpn", "show ip nhrp", "show ip route next-hop-override"]:
        block("P7a RT04(shortcut 後)", sh(r4, c))
    for c in ["show dmvpn", "show ip nhrp", "show ip nhrp traffic"]:
        block("P7a hub(shortcut 後)", sh(hub, c))

    # ---- 故障注入(victim=RT03) ----
    for d in (hub, r3):
        sh(d, "debug nhrp error")
        sh(d, "debug nhrp rate")
    sh(r3, "debug crypto ikev2 error")

    def trial(title, apply, restore, wait_s=60, extra=(), ping_s2s=True):
        clear_log(hub); clear_log(r3)
        conf(r3, apply, title=f"{title} 注入(RT03)")
        sh(hub, f"clear ip nhrp {TIP['RT03']}")
        _bounce(r3, "Tunnel0")
        time.sleep(wait_s)
        for c in ["show dmvpn", "show ip nhrp", "show crypto ikev2 sa", "show ip eigrp neighbors"]:
            block(f"{title} — hub", sh(hub, c))
        for c in ["show dmvpn", "show ip nhrp", "show ip nhrp nhs detail", "show crypto ikev2 sa",
                  "show crypto ipsec sa | include peer|encaps|decaps", "show ip eigrp neighbors", "show ip route eigrp",
                  "show ip nhrp traffic", "show interface Tunnel0 | include line protocol|Tunnel|packets"] + list(extra):
            block(f"{title} — RT03", sh(r3, c))
        ping(r3, LAN["RT02"], source=LAN["RT03"], repeat=3, title=f"{title} ping RT03 LAN→hub LAN")
        if ping_s2s:
            ping(r3, LAN["RT01"], source=LAN["RT03"], repeat=5, title=f"{title} ping RT03 LAN→RT01 LAN(spoke間)")
            block(f"{title} — RT03 show dmvpn (spoke間 ping 後)", sh(r3, "show dmvpn"))
        logtail(hub, f"{title} hub", include=DMVPN_INC)
        logtail(r3, f"{title} RT03", include=DMVPN_INC)
        conf(r3, restore, title=f"{title} 復旧(RT03)")
        sh(hub, f"clear ip nhrp {TIP['RT03']}")
        _bounce(r3, "Tunnel0")
        t, _ = wait_for(lambda: _dmvpn_up(hub, TIP["RT03"]), timeout=180, step=15, what="RT03 再 UP")
        note(f"{title} 復旧後 RT03 UP= {t}s")

    trial("P7b network-id 不一致(RT03=99・他=1)",
          ["interface Tunnel0", "ip nhrp network-id 99", "exit"],
          ["interface Tunnel0", f"ip nhrp network-id {NETID}", "exit"],
          extra=["show ip nhrp | include network|Tunnel", "show running-config interface Tunnel0"])
    trial("P7c NHRP authentication 不一致(RT03=WRONGKY1)",
          ["interface Tunnel0", "ip nhrp authentication WRONGKY1", "exit"],
          ["interface Tunnel0", f"ip nhrp authentication {NHRP_KEY}", "exit"])
    trial("P7d tunnel key 不一致(RT03=101・他=100)",
          ["interface Tunnel0", "tunnel key 101", "exit"],
          ["interface Tunnel0", f"tunnel key {TKEY}", "exit"])
    trial("P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正)",
          ["interface Tunnel0", f"no ip nhrp nhs {TIP['RT02']} nbma {LO['RT02']} multicast",
           f"ip nhrp nhs {OV}.22 nbma {LO['RT02']} multicast", "exit"],
          ["interface Tunnel0", f"no ip nhrp nhs {OV}.22 nbma {LO['RT02']} multicast",
           f"ip nhrp nhs {TIP['RT02']} nbma {LO['RT02']} multicast", "exit"],
          extra=["show ip nhrp nhs"])
    trial("P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0)",
          ["interface Tunnel0", f"no ip nhrp nhs {TIP['RT02']} nbma {LO['RT02']} multicast",
           f"ip nhrp nhs {TIP['RT02']} nbma 10.0.23.2 multicast", "exit"],
          ["interface Tunnel0", f"no ip nhrp nhs {TIP['RT02']} nbma 10.0.23.2 multicast",
           f"ip nhrp nhs {TIP['RT02']} nbma {LO['RT02']} multicast", "exit"],
          extra=["show ip nhrp nhs"])
    for d in (hub, r3):
        sh(d, "undebug all")

    # ---- P7f shared: hub に同一 source・同一 profile の Tunnel1 ----
    clear_log(hub)
    conf(hub, ["interface Tunnel1", "ip address 10.254.0.2 255.255.255.0", "tunnel source Loopback0",
               "tunnel mode gre multipoint", "tunnel key 200", "tunnel protection ipsec profile IPSEC-POC", "exit"],
         title="P7f-1 hub Tunnel1 同一 source・同一 profile・shared 無し")
    time.sleep(20)
    for c in ["show ip interface brief | include Tunnel", "show crypto socket", "show dmvpn", "show crypto ipsec profile",
              "show running-config interface Tunnel1", "show running-config interface Tunnel0"]:
        block("P7f-1 hub", sh(hub, c))
    ping(r1, LAN["RT02"], source=LAN["RT01"], repeat=3, title="P7f-1 ping RT01 LAN→hub LAN(Tunnel0 生存?)")
    logtail(hub, "P7f-1 hub", include=DMVPN_INC)
    clear_log(hub)
    conf(hub, ["interface Tunnel1", "tunnel protection ipsec profile IPSEC-POC shared", "exit"],
         title="P7f-2 hub Tunnel1 に shared")
    time.sleep(15)
    for c in ["show ip interface brief | include Tunnel", "show crypto socket", "show running-config interface Tunnel1"]:
        block("P7f-2 hub", sh(hub, c))
    logtail(hub, "P7f-2 hub", include=DMVPN_INC)
    clear_log(hub)
    conf(hub, ["interface Tunnel0", "tunnel protection ipsec profile IPSEC-POC shared", "exit"],
         title="P7f-3 hub Tunnel0 にも shared")
    time.sleep(30)
    for c in ["show ip interface brief | include Tunnel", "show crypto socket", "show dmvpn", "show crypto ikev2 sa",
              "show running-config interface Tunnel0"]:
        block("P7f-3 hub", sh(hub, c))
    ping(r1, LAN["RT02"], source=LAN["RT01"], repeat=3, title="P7f-3 ping RT01 LAN→hub LAN")
    logtail(hub, "P7f-3 hub", include=DMVPN_INC)
    conf(hub, ["no interface Tunnel1", "interface Tunnel0", "tunnel protection ipsec profile IPSEC-POC", "exit"],
         title="P7f-4 hub Tunnel1 削除・Tunnel0 の shared 解除")
    time.sleep(30)
    t, info = wait_for(up3, timeout=180, step=15, what="hub 3 spoke UP(shared 後片付け)")
    block(f"P7f-4 hub show dmvpn (3 UP after {t}s)", info)

    # ---- P7g map multicast dynamic の既定/表示(IOL) ----
    block("P7g-0 hub show run int Tunnel0 | include nhrp", sh(hub, "show running-config interface Tunnel0 | include nhrp"))
    block("P7g-0 RT01 show run int Tunnel0 | include nhrp", sh(r1, "show running-config interface Tunnel0 | include nhrp"))
    conf(hub, ["interface Tunnel0", "no ip nhrp map multicast dynamic", "exit"], title="P7g-1 hub no ip nhrp map multicast dynamic")
    sh(hub, f"clear ip nhrp {TIP['RT01']}")
    _bounce(r1, "Tunnel0")
    time.sleep(60)
    for c in ["show running-config interface Tunnel0 | include nhrp", "show ip nhrp multicast", "show ip eigrp neighbors", "show dmvpn"]:
        block("P7g-1 hub", sh(hub, c))
    for c in ["show ip eigrp neighbors", "show ip route eigrp", "show dmvpn"]:
        block("P7g-1 RT01", sh(r1, c))
    logtail(r1, "P7g-1 RT01", include=DMVPN_INC)
    conf(hub, ["interface Tunnel0", "ip nhrp map multicast dynamic", "exit"], title="P7g-2 hub 復旧")
    sh(hub, f"clear ip nhrp {TIP['RT01']}")
    _bounce(r1, "Tunnel0")
    time.sleep(45)
    block("P7g-2 hub show ip nhrp multicast", sh(hub, "show ip nhrp multicast"))
    block("P7g-2 hub show ip eigrp neighbors", sh(hub, "show ip eigrp neighbors"))
    flush("P7 DMVPN show 指紋(IOL crypto)")


# =========================================================================
# P7x 再測: P7f(shared)は「tunnel protection の変更で Tunnel0 が自動 shutdown」され P7f-4 の復旧で
#   no shutdown を打っていなかった → hub を直し、shared をコンソール全文で採り直し、P7g も健全な hub で再測
# =========================================================================
def _conf_full(dev, lines, title):
    out = dev.configure(lines, error_pattern=[], timeout=180, reply=DIALOG)
    text = out if isinstance(out, str) else "\n".join(v for v in out.values() if isinstance(v, str))
    block(title, "\n".join(lines) + "\n---\n" + text.strip())
    return text


def P7x(devs):
    r1, r2, r3, r4 = (devs[n] for n in NODES)
    hub = r2
    conf(hub, ["interface Tunnel0", "no shutdown", "exit"])

    def up3():
        o = sh(hub, "show dmvpn")
        return len(re.findall(r"\bUP\b", o)) >= 3, o
    t, info = wait_for(up3, timeout=240, step=15, what="hub 3 spoke UP(復旧)")
    block(f"P7x-0 hub 復旧 show dmvpn (3 UP after {t}s)", info)
    # ---- shared 再測(全文採取) ----
    _conf_full(hub, ["interface Tunnel1", "ip address 10.254.0.2 255.255.255.0", "tunnel source Loopback0",
                     "tunnel mode gre multipoint", "tunnel key 200", "tunnel protection ipsec profile IPSEC-POC", "exit"],
               "P7x-f1 hub Tunnel1(同一 source・同一 profile・shared 無し) — console 全文")
    block("P7x-f1 hub show run int Tunnel1", sh(hub, "show running-config interface Tunnel1"))
    _conf_full(hub, ["interface Tunnel1", "tunnel protection ipsec profile IPSEC-POC shared", "exit"],
               "P7x-f2 hub Tunnel1 に shared(Tunnel0 は shared 無し) — console 全文")
    block("P7x-f2 hub show run int Tunnel1", sh(hub, "show running-config interface Tunnel1"))
    _conf_full(hub, ["interface Tunnel0", "tunnel protection ipsec profile IPSEC-POC shared", "exit"],
               "P7x-f3 hub Tunnel0 に shared — console 全文(自動 shutdown の警告)")
    conf(hub, ["interface Tunnel0", "no shutdown", "exit"])
    t, info = wait_for(up3, timeout=240, step=15, what="hub 3 spoke UP(Tunnel0 shared)")
    block(f"P7x-f3 hub show dmvpn (Tunnel0 shared・3 UP after {t}s)", info)
    block("P7x-f3 hub show crypto socket", sh(hub, "show crypto socket"))
    block("P7x-f3 hub show run int Tunnel1", sh(hub, "show running-config interface Tunnel1"))
    _conf_full(hub, ["interface Tunnel1", "tunnel protection ipsec profile IPSEC-POC shared", "exit"],
               "P7x-f4 hub Tunnel1 に shared(Tunnel0 も shared) — console 全文")
    time.sleep(10)
    block("P7x-f4 hub show run int Tunnel1", sh(hub, "show running-config interface Tunnel1"))
    block("P7x-f4 hub show crypto socket", sh(hub, "show crypto socket"))
    block("P7x-f4 hub show ip interface brief | include Tunnel", sh(hub, "show ip interface brief | include Tunnel"))
    ping(r1, LAN["RT02"], source=LAN["RT01"], repeat=3, title="P7x-f4 ping RT01 LAN→hub LAN(両 Tunnel shared)")
    _conf_full(hub, ["interface Tunnel1", "tunnel protection ipsec profile IPSEC-POC", "exit"],
               "P7x-f5 hub Tunnel1 を shared 無しに戻す(Tunnel0 は shared) — console 全文")
    block("P7x-f5 hub show run int Tunnel1", sh(hub, "show running-config interface Tunnel1"))
    # 別 profile(同じ transform)を Tunnel1 に(shared 無し)= 同一 source でも profile が違えば?
    conf(hub, ["crypto ipsec profile IPSEC-POC2", "set transform-set TS-POC", "set ikev2-profile IKEV2-POC", "exit"])
    _conf_full(hub, ["interface Tunnel1", "tunnel protection ipsec profile IPSEC-POC2", "exit"],
               "P7x-f6 hub Tunnel1 に別 profile IPSEC-POC2(shared 無し) — console 全文")
    block("P7x-f6 hub show run int Tunnel1", sh(hub, "show running-config interface Tunnel1"))
    block("P7x-f6 hub show crypto socket", sh(hub, "show crypto socket"))
    # 後片付け
    _conf_full(hub, ["no interface Tunnel1", "interface Tunnel0", "tunnel protection ipsec profile IPSEC-POC", "no shutdown", "exit",
                     "no crypto ipsec profile IPSEC-POC2"], "P7x-f7 hub 後片付け(Tunnel1 削除・Tunnel0 shared 解除) — console 全文")
    time.sleep(5)
    conf(hub, ["interface Tunnel0", "no shutdown", "exit"])
    t, info = wait_for(up3, timeout=240, step=15, what="hub 3 spoke UP(後片付け)")
    block(f"P7x-f7 hub show dmvpn (3 UP after {t}s)", info)
    # ---- P7g 再測 ----
    conf(hub, ["interface Tunnel0", "no ip nhrp map multicast dynamic", "exit"], title="P7x-g1 hub no ip nhrp map multicast dynamic")
    sh(hub, f"clear ip nhrp {TIP['RT01']}")
    _bounce(r1, "Tunnel0")
    time.sleep(75)
    for c in ["show running-config interface Tunnel0 | include nhrp", "show ip nhrp multicast", "show ip eigrp neighbors", "show dmvpn"]:
        block(f"P7x-g1 hub {c}", sh(hub, c))
    for c in ["show ip eigrp neighbors", "show ip route eigrp | include D ", "show dmvpn"]:
        block(f"P7x-g1 RT01 {c}", sh(r1, c))
    ping(r1, LAN["RT02"], source=LAN["RT01"], repeat=3, title="P7x-g1 ping RT01 LAN→hub LAN")
    logtail(r1, "P7x-g1 RT01", include=r"DUAL|NHRP|DMVPN")
    logtail(hub, "P7x-g1 hub", include=r"DUAL|NHRP|DMVPN")
    conf(hub, ["interface Tunnel0", "ip nhrp map multicast dynamic", "exit"], title="P7x-g2 hub 復旧")
    sh(hub, f"clear ip nhrp {TIP['RT01']}")
    _bounce(r1, "Tunnel0")
    time.sleep(60)
    block("P7x-g2 hub show ip nhrp multicast", sh(hub, "show ip nhrp multicast"))
    block("P7x-g2 hub show ip eigrp neighbors", sh(hub, "show ip eigrp neighbors"))
    block("P7x-g2 RT01 show ip eigrp neighbors", sh(r1, "show ip eigrp neighbors"))
    flush("P7x shared 再測＋P7g 再測")


# =========================================================================
# P9 LDP DU 表示(RT01-RT02 の物理リンク)＋ AD 同値(RT03-RT04: OSPF/EIGRP vs static の AD tie)
#   P7 の後に同じ盤面で実行(DMVPN は温存・物理リンク側だけを使う)
# =========================================================================
def P9(devs):
    r1, r2, r3, r4 = (devs[n] for n in NODES)
    # ---- P9a LDP ----
    for d in (r1, r2):
        conf(d, ["mpls label protocol ldp", "mpls ldp router-id Loopback0 force", "interface Ethernet0/0", "mpls ip", "exit"],
             title=f"P9a LDP 有効化 {d.name}")
    def ldp():
        o = sh(r1, "show mpls ldp neighbor")
        return "Oper" in o, o
    t, info = wait_for(ldp, timeout=120, step=10, what="LDP Oper")
    block(f"P9a RT01 show mpls ldp neighbor (Oper after {t}s)", info)
    for c in ["show mpls ldp neighbor detail", "show mpls ldp parameters", "show mpls ldp discovery detail",
              "show mpls interfaces detail", "show mpls ldp bindings", "show mpls forwarding-table",
              "show mpls ip binding", "show mpls ldp neighbor | include Downstream|Upstream|distribution"]:
        block("P9a RT01", sh(r1, c))
    block("P9a RT02 show mpls ldp neighbor", sh(r2, "show mpls ldp neighbor"))
    block("P9a RT02 show mpls ldp bindings", sh(r2, "show mpls ldp bindings"))
    # ---- P9b AD tie: RT03 Lo9 172.31.3.3/32 を OSPF で RT04 へ・RT04 に static(AD 可変) ----
    conf(r3, ["interface Loopback9", "ip address 172.31.3.3 255.255.255.255", "exit",
              "router ospf 9", "router-id 3.3.3.9", "network 10.0.34.0 0.0.0.255 area 0", "network 172.31.3.3 0.0.0.0 area 0", "exit"])
    conf(r4, ["router ospf 9", "router-id 4.4.4.9", "network 10.0.34.0 0.0.0.255 area 0", "exit"])
    def ospf_rt():
        o = sh(r4, "show ip route 172.31.3.3")
        return "ospf" in o.lower() or "O " in o, o
    t, info = wait_for(ospf_rt, timeout=120, step=10, what="RT04 に O 172.31.3.3")
    block(f"P9b-0 RT04 show ip route 172.31.3.3 (OSPF のみ・after {t}s)", info)
    for ad, label in [(110, "static AD110 = OSPF 110(同値)"), (109, "static AD109 < 110"), (111, "static AD111 > 110")]:
        conf(r4, [f"ip route 172.31.3.3 255.255.255.255 10.0.34.3 {ad}"], title=f"P9b {label} 投入")
        time.sleep(5)
        block(f"P9b {label} — RT04 show ip route 172.31.3.3", sh(r4, "show ip route 172.31.3.3"))
        block(f"P9b {label} — RT04 show ip route | include 172.31.3.3", sh(r4, "show ip route | include 172.31.3.3"))
        block(f"P9b {label} — RT04 show ip route static", sh(r4, "show ip route static"))
        block(f"P9b {label} — RT04 show ip ospf rib 172.31.3.3", sh(r4, "show ip ospf rib 172.31.3.3"))
        if ad == 110:
            sh(r4, "clear ip route *")
            time.sleep(8)
            block(f"P9b {label} — clear ip route * 後 RT04 show ip route 172.31.3.3", sh(r4, "show ip route 172.31.3.3"))
            # OSPF を一度外して戻す(後から来た側が勝つか)
            conf(r4, ["router ospf 9", "shutdown", "exit"])
            time.sleep(5)
            block(f"P9b {label} — OSPF shutdown 中 RT04 show ip route 172.31.3.3", sh(r4, "show ip route 172.31.3.3"))
            conf(r4, ["router ospf 9", "no shutdown", "exit"])
            time.sleep(40)
            block(f"P9b {label} — OSPF 復帰後 RT04 show ip route 172.31.3.3", sh(r4, "show ip route 172.31.3.3"))
        conf(r4, [f"no ip route 172.31.3.3 255.255.255.255 10.0.34.3 {ad}"])
    # EIGRP 90 との同値(AS 200・物理リンクのみ)
    conf(r3, ["no router ospf 9", "router eigrp 200", "network 10.0.34.0 0.0.0.255", "network 172.31.3.3 0.0.0.0", "exit"])
    conf(r4, ["no router ospf 9", "router eigrp 200", "network 10.0.34.0 0.0.0.255", "exit"])
    def eigrp_rt():
        o = sh(r4, "show ip route 172.31.3.3")
        return "eigrp" in o.lower(), o
    t, info = wait_for(eigrp_rt, timeout=120, step=10, what="RT04 に D 172.31.3.3")
    block(f"P9b-e0 RT04 show ip route 172.31.3.3 (EIGRP のみ・after {t}s)", info)
    conf(r4, ["ip route 172.31.3.3 255.255.255.255 10.0.34.3 90"], title="P9b-e static AD90 = EIGRP 90(同値) 投入")
    time.sleep(5)
    block("P9b-e static AD90 — RT04 show ip route 172.31.3.3", sh(r4, "show ip route 172.31.3.3"))
    block("P9b-e static AD90 — RT04 show ip route | include 172.31.3.3", sh(r4, "show ip route | include 172.31.3.3"))
    sh(r4, "clear ip route *")
    time.sleep(8)
    block("P9b-e static AD90 — clear 後 RT04 show ip route 172.31.3.3", sh(r4, "show ip route 172.31.3.3"))
    conf(r4, ["no ip route 172.31.3.3 255.255.255.255 10.0.34.3 90", "no router eigrp 200"])
    conf(r3, ["no router eigrp 200", "no interface Loopback9"])
    for d in (r1, r2):
        conf(d, ["interface Ethernet0/0", "no mpls ip", "exit", "no mpls ldp router-id Loopback0 force"])
    flush("P9 LDP DU 表示・AD 同値")


# =========================================================================
def teardown(cl):
    for lab in cl.find_labs_by_title(LAB_TITLE):
        print(f"[i] {lab.title}: stop/wipe/remove")
        try:
            lab.stop(wait=True)
        except Exception as e:
            print(f"    stop: {e}")
        try:
            lab.wipe(wait=True)
        except Exception as e:
            print(f"    wipe: {e}")
        lab.remove()
    print("[i] teardown 完了")


STEPS = {"P0": P0, "P1": P1, "P1b": P1b, "P1c": P1c, "P2": P2, "P2x": P2x, "P3": P3, "P3h2": P3h2, "P3h3": P3h3, "P3a4": P3a4, "P4": P4, "P5": P5, "P6": P6, "P7": P7, "P7x": P7x, "P9": P9}


def main():
    args = sys.argv[1:] or ["all"]
    cl, creds = client()
    if args == ["teardown"]:
        teardown(cl)
        return
    if args[0] == "build":
        lab = ensure_lab(cl)
        args = args[1:]
        if not args:
            return
    lab = get_lab(cl)
    steps = list(STEPS) if args == ["all"] else args
    devs = connect_all(lab, creds)
    for s in steps:
        print(f"\n===== {s} =====", flush=True)
        try:
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
