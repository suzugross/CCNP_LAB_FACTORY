#!/usr/bin/env python3
"""BL-170 紙面 Services 即答形ファミリの PoC(S1〜S11)。

設計= problems/_drafts/PAPER-SVC.design.md §6。IOL 2 台(RT01=DUT・RT02=補助: NTP master /
TFTP 相手)＋管理ブリッジ(System Bridge)で、このホスト(10.1.10.6)を SSH/SNMP/syslog/SCP/FTP/TFTP の
相手にする。**駆動はコンソール(pyats/unicon・CML terminal server)**= SSH を壊す実験に耐える。

トポロジ(POC-SVC):
    host(10.1.10.6) == System Bridge == MGMT-SW == e0/3 RT01(10.1.10.45)   RT01 e0/0 --10.99.12.0/24-- e0/0 RT02
                                                == e0/3 RT02(10.1.10.46)

使い方: sweep.py build | S1 S2 ... | all | teardown      結果は results-raw.md へ追記。
"""
import asyncio
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import urllib3
import yaml
from virl2_client import ClientLibrary
from pyats.topology import loader
from unicon.eal.dialogs import Dialog, Statement

urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
OUT = HERE / "results-raw.md"
CML = ("https://10.1.10.10", "SUZUKI", "suzugross")
LAB_TITLE = "POC-SVC"
HOST_IP = "10.1.10.6"
RT01_MGMT, RT02_MGMT = "10.1.10.45", "10.1.10.46"
NODES = ["RT01", "RT02"]
USER, PW = "SUZUKI", "CCNP"

BASE = {
    "RT01": [
        "no ip domain lookup", "ip domain name ccnp.local", "ip cef",
        f"username {USER} privilege 15 secret {PW}",
        "interface Loopback0", "ip address 1.1.1.1 255.255.255.255", "exit",
        "interface Ethernet0/0", "description === to RT02 ===", "ip address 10.99.12.1 255.255.255.0", "no shutdown", "exit",
        "interface Ethernet0/1", "description === spare (log generator) ===", "no shutdown", "exit",
        "interface Ethernet0/3", "description === MGMT ===", f"ip address {RT01_MGMT} 255.255.255.192", "no shutdown", "exit",
        "line con 0", "exec-timeout 0 0", "logging synchronous", "exit",
        "line vty 0 4", "login local", "transport input ssh", "exit",
        "file prompt quiet",
    ],
    "RT02": [
        "no ip domain lookup", "ip cef",
        "interface Loopback0", "ip address 2.2.2.2 255.255.255.255", "exit",
        "interface Ethernet0/0", "description === to RT01 ===", "ip address 10.99.12.2 255.255.255.0", "no shutdown", "exit",
        "interface Ethernet0/3", "description === MGMT ===", f"ip address {RT02_MGMT} 255.255.255.192", "no shutdown", "exit",
        "ip route 1.1.1.1 255.255.255.255 10.99.12.1",
        "line con 0", "exec-timeout 0 0", "logging synchronous", "exit",
        "file prompt quiet",
    ],
}

LOG = []
LAB = None


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
# CML ラボ
# =========================================================================
def _iface(lab, label, ifname):
    for _ in range(4):
        node = lab.get_node_by_label(label)
        for i in node.interfaces():
            if i.label == ifname:
                return i
        lab.sync(topology_only=True)
        time.sleep(1)
    raise RuntimeError(f"{label} に {ifname} が見つからない")


def ensure_lab(client):
    labs = client.find_labs_by_title(LAB_TITLE)
    if labs:
        lab = labs[0]
        print(f"[i] 既存ラボ {LAB_TITLE} ({lab.state()})")
    else:
        print(f"[i] ラボ {LAB_TITLE} を新規作成")
        lab = client.create_lab(LAB_TITLE)
    have = {n.label for n in lab.nodes()}
    if "RT01" not in have:
        n = lab.create_node("RT01", "iol-xe", -150, 0, populate_interfaces=True)
        n.configuration = "hostname RT01\nno ip domain lookup\n"
    if "RT02" not in have:
        n = lab.create_node("RT02", "iol-xe", 150, 0, populate_interfaces=True)
        n.configuration = "hostname RT02\nno ip domain lookup\n"
    if "MGMT-SW" not in have:
        lab.create_node("MGMT-SW", "unmanaged_switch", 0, 200, populate_interfaces=True)
    if "to-MGMT-net" not in have:
        n = lab.create_node("to-MGMT-net", "external_connector", 250, 200, populate_interfaces=True)
        n.configuration = "System Bridge"
    lab.sync(topology_only=True)
    links = [("RT01", "Ethernet0/0", "RT02", "Ethernet0/0"),
             ("RT01", "Ethernet0/3", "MGMT-SW", "port0"),
             ("RT02", "Ethernet0/3", "MGMT-SW", "port1"),
             ("MGMT-SW", "port2", "to-MGMT-net", "port")]
    for a, aif, b, bif in links:
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


def connect_all(lab, required=("RT01", "RT02")):
    tb = yaml.safe_load(lab.get_pyats_testbed())
    for name, dev in (tb.get("devices") or {}).items():
        creds = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            creds["default"] = {"username": CML[1], "password": CML[2]}
        else:
            creds["default"] = {"username": USER, "password": PW}
            creds["enable"] = {"password": os.environ.get("SWEEP_ENABLE_PW", PW)}
    testbed = loader.load(tb)
    devs = {}
    for label in NODES:
        dev = testbed.devices[label]
        for attempt in range(1, 7):
            try:
                dev.connect(via="a", log_stdout=False, learn_hostname=True,
                            connection_timeout=120)
                dev.enable()
                dev.execute("terminal length 0")
                dev.execute("terminal width 200")
                devs[label] = dev
                break
            except Exception as e:
                print(f"    {label}: connect attempt {attempt} failed ({type(e).__name__}: {e})")
                try:
                    dev.disconnect()
                except Exception:
                    pass
                time.sleep(10)
        else:
            if label in required:
                raise RuntimeError(f"{label}: console 接続不能(必須)")
    return devs


DIALOG = Dialog([
    Statement(pattern=r"\[yes/no\]:?\s*$", action="sendline(yes)", loop_continue=True, continue_timer=False),
    Statement(pattern=r"\[confirm\]\s*$", action="sendline()", loop_continue=True, continue_timer=False),
    Statement(pattern=r"\[no\]:?\s*$", action="sendline(Y)", loop_continue=True, continue_timer=False),
    Statement(pattern=r"\?\s*$", action="sendline()", loop_continue=True, continue_timer=False),
])


def conf(dev, lines, title=None):
    out = dev.configure(lines, error_pattern=[], timeout=180, reply=DIALOG)
    text = out if isinstance(out, str) else "\n".join(v for v in out.values() if isinstance(v, str))
    errs = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("%")]
    if title:
        block(title, "\n".join(lines) + ("\n---\n" + "\n".join(errs) if errs else "\n---\n(応答なし)"))
    for e in errs:
        print(f"    ! {e}")
    return text


def sh(dev, cmd, title=None, timeout=120):
    out = dev.execute(cmd, timeout=timeout, reply=DIALOG, error_pattern=[])
    if title:
        block(f"{title} — {dev.name}# {cmd}", out)
    return out


def ping(dev, dst, source=None, repeat=3):
    cmd = f"ping {dst} repeat {repeat}"
    if source:
        cmd += f" source {source}"
    out = sh(dev, cmd, timeout=60)
    m = re.search(r"Success rate is (\d+) percent", out)
    return (int(m.group(1)) if m else -1), out


def wait_for(fn, timeout=300, step=15, what="条件"):
    t0 = time.time()
    while time.time() - t0 < timeout:
        ok, info = fn()
        if ok:
            return time.time() - t0, info
        print(f"    待ち {time.time()-t0:.0f}s: {what}", flush=True)
        time.sleep(step)
    return None, info


# =========================================================================
# ホスト側の相手(SSH / SNMP / UDP 受信 / TFTP / FTP / SCP)
# =========================================================================
SSH_LEGACY = ["-o", "HostKeyAlgorithms=+ssh-rsa", "-o", "PubkeyAcceptedAlgorithms=+ssh-rsa",
              "-o", "KexAlgorithms=+diffie-hellman-group14-sha1,diffie-hellman-group-exchange-sha1,diffie-hellman-group1-sha1"]
SSH_COMMON = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=8",
              "-o", "LogLevel=VERBOSE"]


def ssh_probe(host=RT01_MGMT, user=USER, legacy=True):
    """OpenSSH で接続段階まで(BatchMode=鍵なしなので認証は必ず失敗)。ハンドシェイクの可否と理由を返す。"""
    cmd = ["ssh", "-v", "-o", "BatchMode=yes"] + SSH_COMMON + (SSH_LEGACY if legacy else []) + [f"{user}@{host}", "show ip ssh"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        err = r.stderr
    except subprocess.TimeoutExpired as e:
        err = (e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "") + "\n(timeout)"
    keep = [ln for ln in err.splitlines()
            if re.search(r"Invalid key|too small|no matching|Permission denied|Connection closed|Connection refused|"
                         r"Connection timed out|kex_exchange|Authentications that can continue|Server host key|"
                         r"kex: algorithm|kex: host key algorithm|Bad server host key|Unable to negotiate|"
                         r"Remote protocol version|refused|reset by peer|banner|exchange_identification", ln)]
    return "\n".join(keep[-8:]) or err[-600:]


def ssh_login(host=RT01_MGMT, user=USER, pw=PW, cmds=("show ip ssh",), wait=3.0):
    """paramiko で実際にログインしてコマンドを打つ。戻り= (ok, text)。"""
    import paramiko
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect(host, username=user, password=pw, look_for_keys=False, allow_agent=False, timeout=12,
                  banner_timeout=20, auth_timeout=20)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    try:
        shl = c.invoke_shell()
        time.sleep(1.5)
        shl.send("terminal length 0\n")
        time.sleep(1)
        buf = b""
        for cmd in cmds:
            shl.send(cmd + "\n")
            time.sleep(wait)
            while shl.recv_ready():
                buf += shl.recv(65535)
                time.sleep(0.2)
        return True, buf.decode(errors="replace")
    finally:
        c.close()


class UdpSink:
    """UDP 受信(syslog 5514 / trap 1162 など)。"""
    def __init__(self, port):
        self.port = port
        self.got = []
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(("", port))
        self.s.settimeout(0.5)
        self.run = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self.run:
            try:
                data, addr = self.s.recvfrom(65535)
                self.got.append((time.time(), addr[0], data))
            except socket.timeout:
                continue
            except OSError:
                break

    def take(self):
        g, self.got = self.got, []
        return g

    def close(self):
        self.run = False
        self.s.close()


def snmp_get(auth, oid="1.3.6.1.2.1.1.5.0", host=RT01_MGMT, timeout=3, retries=0):
    from pysnmp.hlapi.v3arch.asyncio import SnmpEngine, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, get_cmd

    async def go():
        eng = SnmpEngine()
        try:
            tgt = await UdpTransportTarget.create((host, 161), timeout=timeout, retries=retries)
            ei, es, ix, vb = await get_cmd(eng, auth, tgt, ContextData(), ObjectType(ObjectIdentity(oid)))
        finally:
            eng.close_dispatcher()
        if ei:
            return f"errorIndication: {ei}"
        if es:
            return f"errorStatus: {es.prettyPrint()} at {ix}"
        return " / ".join(f"{a.prettyPrint()} = {b.prettyPrint()}" for a, b in vb)
    return asyncio.run(go())


def snmp_set(auth, value, oid="1.3.6.1.2.1.1.4.0", host=RT01_MGMT, timeout=3, retries=0):
    from pysnmp.hlapi.v3arch.asyncio import SnmpEngine, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, set_cmd
    from pysnmp.proto.rfc1902 import OctetString

    async def go():
        eng = SnmpEngine()
        try:
            tgt = await UdpTransportTarget.create((host, 161), timeout=timeout, retries=retries)
            ei, es, ix, vb = await set_cmd(eng, auth, tgt, ContextData(), ObjectType(ObjectIdentity(oid), OctetString(value)))
        finally:
            eng.close_dispatcher()
        if ei:
            return f"errorIndication: {ei}"
        if es:
            return f"errorStatus: {es.prettyPrint()} at {ix}"
        return " / ".join(f"{a.prettyPrint()} = {b.prettyPrint()}" for a, b in vb)
    return asyncio.run(go())


def v2c(comm):
    from pysnmp.hlapi.v3arch.asyncio import CommunityData
    return CommunityData(comm, mpModel=1)


def v3(user, auth=None, priv=None, authproto="sha", privproto="aes"):
    from pysnmp.hlapi.v3arch.asyncio import (UsmUserData, usmHMACSHAAuthProtocol, usmHMACMD5AuthProtocol,
                                             usmAesCfb128Protocol, usmDESPrivProtocol)
    kw = {}
    if auth:
        kw["authKey"] = auth
        kw["authProtocol"] = usmHMACSHAAuthProtocol if authproto == "sha" else usmHMACMD5AuthProtocol
    if priv:
        kw["privKey"] = priv
        kw["privProtocol"] = usmAesCfb128Protocol if privproto == "aes" else usmDESPrivProtocol
    return UsmUserData(user, **kw)


def tftp_get(host, fname, timeout=8):
    import tftpy
    dst = HERE / "_tmp_tftp.bin"
    try:
        c = tftpy.TftpClient(host, 69)
        c.download(fname, str(dst), timeout=timeout)
        n = dst.stat().st_size
        dst.unlink(missing_ok=True)
        return f"OK {n} bytes"
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def ftp_server(port=2121, user="ftpu", pw="ftpp"):
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import FTPServer
    d = HERE / "_ftproot"
    d.mkdir(exist_ok=True)
    auth = DummyAuthorizer()
    auth.add_user(user, pw, str(d), perm="elradfmwMT")
    h = FTPHandler
    h.authorizer = auth
    srv = FTPServer(("0.0.0.0", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, d


def scp_pull(host, remote="running-config", user=USER, pw=PW):
    ask = HERE / "_askpass.sh"
    ask.write_text(f"#!/bin/sh\necho {pw}\n")
    ask.chmod(0o755)
    dst = HERE / "_scp_pull.txt"
    dst.unlink(missing_ok=True)
    env = dict(os.environ, SSH_ASKPASS=str(ask), SSH_ASKPASS_REQUIRE="force", DISPLAY=":0")
    cmd = ["scp", "-O", "-v"] + SSH_COMMON + SSH_LEGACY + [f"{user}@{host}:{remote}", str(dst)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    except subprocess.TimeoutExpired:
        return "timeout", ""
    keep = [ln for ln in r.stderr.splitlines()
            if re.search(r"Permission denied|Connection closed|lost connection|scp:|Sending command|Authenticated|"
                         r"exit status|subsystem|Authentication succeeded|refused|Sink|Fetching", ln)]
    body = dst.read_text(errors="replace") if dst.exists() else ""
    return f"rc={r.returncode}\n" + "\n".join(keep[-8:]), body


def scp_push(host, local, remote, user=USER, pw=PW):
    ask = HERE / "_askpass.sh"
    ask.write_text(f"#!/bin/sh\necho {pw}\n")
    ask.chmod(0o755)
    env = dict(os.environ, SSH_ASKPASS=str(ask), SSH_ASKPASS_REQUIRE="force", DISPLAY=":0")
    cmd = ["scp", "-O", "-v"] + SSH_COMMON + SSH_LEGACY + [str(local), f"{user}@{host}:{remote}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    except subprocess.TimeoutExpired:
        return "timeout"
    keep = [ln for ln in r.stderr.splitlines()
            if re.search(r"Permission denied|Connection closed|lost connection|scp:|Sending command|exit status|refused", ln)]
    return f"rc={r.returncode}\n" + "\n".join(keep[-8:])


def tcp_probe(host, port, timeout=4):
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(3)
            try:
                data = s.recv(200)
            except socket.timeout:
                data = b""
            return f"open: {data[:120]!r}"
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def send_log(dev, level, text):
    """IOS の send log で任意の severity のメッセージを作る(可否は S3 で確かめる)。"""
    return sh(dev, f"send log {level} {text}")


def flap(dev, ifname="Ethernet0/1"):
    conf(dev, [f"interface {ifname}", "shutdown"])
    time.sleep(2)
    conf(dev, [f"interface {ifname}", "no shutdown"])
    time.sleep(3)


# =========================================================================
# チェック本体
# =========================================================================
def S1(devs):
    """SSH: 鍵なし/鍵長/version の受理・show ip ssh・クライアント側の結果。"""
    r1 = devs["RT01"]
    sh(r1, "show ip ssh", "S1-0 鍵なしの状態")
    sh(r1, "show running-config | section line vty", "S1-0 vty(基線)")
    conf(r1, ["ip ssh version 2"], "S1-1 鍵なしで ip ssh version 2")
    sh(r1, "show ip ssh", "S1-1 その後の show ip ssh")
    sh(r1, "show running-config | include ip ssh", "S1-1 running-config の ip ssh 行")
    block("S1-1 ホストから ssh(鍵なし)", ssh_probe())
    conf(r1, ["no ip ssh version 2"])
    for bits in (512, 768, 1024, 2048):
        conf(r1, ["crypto key zeroize rsa"])
        conf(r1, [f"crypto key generate rsa modulus {bits}"], f"S1-2 crypto key generate rsa modulus {bits}")
        time.sleep(3)
        sh(r1, "show ip ssh", f"S1-2 [{bits}] show ip ssh (version 未指定)")
        sh(r1, "show crypto key mypubkey rsa | include Key name|Key type|Usage|bits|Storage", f"S1-2 [{bits}] mypubkey rsa")
        conf(r1, ["ip ssh version 2"], f"S1-2 [{bits}] ip ssh version 2")
        sh(r1, "show ip ssh", f"S1-2 [{bits}] show ip ssh (version 2 投入後)")
        sh(r1, "show running-config | include ip ssh", f"S1-2 [{bits}] running-config の ip ssh 行")
        block(f"S1-2 [{bits}] OpenSSH 接続段階(legacy alg 許可)", ssh_probe())
        block(f"S1-2 [{bits}] OpenSSH 接続段階(既定 alg)", ssh_probe(legacy=False))
        ok, txt = ssh_login(cmds=("show ip ssh",))
        block(f"S1-2 [{bits}] paramiko ログイン → {'OK' if ok else 'NG'}", txt)
        conf(r1, ["no ip ssh version 2"])
    # 2048 のまま: version 1 / time-out / retries
    conf(r1, ["ip ssh version 1"], "S1-3 ip ssh version 1 (2048 鍵)")
    sh(r1, "show ip ssh", "S1-3 show ip ssh")
    conf(r1, ["no ip ssh version 1", "ip ssh version 2", "ip ssh time-out 60", "ip ssh authentication-retries 2"],
         "S1-4 time-out 60 / retries 2")
    sh(r1, "show ip ssh", "S1-4 show ip ssh")
    sh(r1, "show running-config | include ip ssh", "S1-4 running-config")
    conf(r1, ["no ip ssh time-out", "no ip ssh authentication-retries"])
    flush("S1 SSH 鍵長/version/show ip ssh")


def S2(devs):
    """vty: transport input の既定・login/login local・access-class(未定義 ACL 含む)。"""
    r1 = devs["RT01"]
    conf(r1, ["line vty 0 4", "default transport input"], "S2-1 vty transport input を既定へ")
    sh(r1, "show running-config | section line vty", "S2-1 running-config(既定の transport)")
    sh(r1, "show line vty 0 | include transport|Allowed", "S2-1 show line vty 0 (Allowed transports)")
    block("S2-1 ホストから telnet(23) 既定", tcp_probe(RT01_MGMT, 23))
    conf(r1, ["line vty 0 4", "transport input ssh"])
    sh(r1, "show line vty 0 | include transport|Allowed", "S2-1 transport input ssh の show line")
    block("S2-1 ホストから telnet(23) ssh 限定後", tcp_probe(RT01_MGMT, 23))
    conf(r1, ["line vty 0 4", "transport input telnet"])
    block("S2-1 transport input telnet のとき ssh", ssh_probe())
    conf(r1, ["line vty 0 4", "transport input ssh"])
    # login の種類
    conf(r1, ["line vty 0 4", "login", "password vtypass"], "S2-2 login(line password) で SSH")
    ok, txt = ssh_login(pw="vtypass", cmds=("show users",))
    block(f"S2-2 login+password: user {USER}/vtypass → {'OK' if ok else 'NG'}", txt[-400:] if ok else txt)
    ok, txt = ssh_login(user="nobody", pw="vtypass", cmds=("show users",))
    block(f"S2-2 login+password: user nobody/vtypass → {'OK' if ok else 'NG'}", txt[-400:] if ok else txt)
    ok, txt = ssh_login(pw=PW, cmds=("show users",))
    block(f"S2-2 login+password: user {USER}/{PW}(username の secret) → {'OK' if ok else 'NG'}", txt[-300:] if ok else txt)
    conf(r1, ["line vty 0 4", "no password", "login"], "S2-2 login だが password なし")
    ok, txt = ssh_login(cmds=("show users",))
    block(f"S2-2 login/password なし → {'OK' if ok else 'NG'}", txt[-300:] if ok else txt)
    sh(r1, "show logging | include SSH|SEC_LOGIN|LOGIN", "S2-2 ログ(SSH/LOGIN)")
    conf(r1, ["line vty 0 4", "no login"], "S2-2 no login")
    ok, txt = ssh_login(cmds=("show users",))
    block(f"S2-2 no login → {'OK' if ok else 'NG'}", txt[-300:] if ok else txt)
    conf(r1, ["line vty 0 4", "login local"])
    ok, txt = ssh_login(user="nouser", pw="x", cmds=("show users",))
    block(f"S2-2 login local + 未定義ユーザ → {'OK' if ok else 'NG'}", txt[-300:] if ok else txt)
    sh(r1, "show logging | include SSH|SEC_LOGIN|LOGIN", "S2-2 ログ(SSH/LOGIN) その2")
    # access-class
    conf(r1, ["access-list 10 permit 10.1.10.99", "line vty 0 4", "access-class 10 in"], "S2-3 access-class 10 in (ホスト不許可)")
    block("S2-3 ホストから ssh(ACL 不許可)", ssh_probe())
    block("S2-3 ホストから tcp 22", tcp_probe(RT01_MGMT, 22))
    sh(r1, "show access-lists 10", "S2-3 ACL カウンタ")
    conf(r1, ["line vty 0 4", "access-class 55 in"], "S2-3 access-class 55 in (ACL 55 未定義)")
    ok, txt = ssh_login(cmds=("show users",))
    block(f"S2-3 未定義 ACL の access-class → ssh {'OK' if ok else 'NG'}", txt[-300:] if ok else txt)
    conf(r1, ["access-list 10 permit 10.1.10.6", "line vty 0 4", "access-class 10 in"])
    ok, txt = ssh_login(cmds=("show users",))
    block(f"S2-3 ACL 10 permit ホスト → ssh {'OK' if ok else 'NG'}", txt[-300:] if ok else txt)
    sh(r1, "show access-lists 10", "S2-3 ACL カウンタ(許可後)")
    conf(r1, ["line vty 0 4", "no access-class 10 in", "no access-list 10"])
    # exec-timeout / absolute? 省略。vty の数
    sh(r1, "show line | include VTY|vty", "S2-4 vty の本数")
    flush("S2 vty transport/login/access-class")


def S3(devs):
    """logging: 既定レベル・send log・trap/buffered の絞り・monitor/terminal monitor。"""
    r1 = devs["RT01"]
    clear_vty(r1)
    conf(r1, ["no logging host 10.1.10.6", "logging trap informational", "logging buffered debugging"])
    sh(r1, "clear logging")
    out = sh(r1, "show logging", "S3-0 show logging(基線・全文)")
    sh(r1, "show running-config | include logging|service timestamps|service sequence", "S3-0 running-config の logging 行")
    out = send_log(r1, 4, "SVC-TEST-WARN")
    block("S3-1 send log 4 SVC-TEST-WARN の応答", out)
    out = send_log(r1, 6, "SVC-TEST-INFO")
    block("S3-1 send log 6 SVC-TEST-INFO の応答", out)
    sh(r1, "show logging | include SVC-TEST", "S3-1 buffer に入った send log")
    sink = UdpSink(5514)
    conf(r1, [f"logging host {HOST_IP} transport udp port 5514", "logging trap warnings"], "S3-2 logging host + trap warnings")
    time.sleep(2)
    sink.take()
    send_log(r1, 3, "SVC-ERR3")
    send_log(r1, 4, "SVC-WARN4")
    send_log(r1, 5, "SVC-NOTE5")
    send_log(r1, 6, "SVC-INFO6")
    flap(r1)
    time.sleep(3)
    got = sink.take()
    block("S3-2 ホストが受信した syslog(trap warnings)", "\n".join(d.decode(errors="replace").rstrip() for _, _, d in got))
    sh(r1, "show logging | include Trap|Logging to|Buffer|Console|Monitor", "S3-2 show logging の宛先行")
    sh(r1, "show logging | include SVC-|UPDOWN|CHANGED", "S3-2 buffer の中身")
    conf(r1, ["logging trap informational"])
    sink.take()
    send_log(r1, 6, "SVC-INFO6b")
    send_log(r1, 7, "SVC-DEBUG7b")
    time.sleep(3)
    got = sink.take()
    block("S3-2 trap informational(既定)で受信", "\n".join(d.decode(errors="replace").rstrip() for _, _, d in got))
    conf(r1, ["logging buffered warnings"], "S3-3 logging buffered warnings")
    sh(r1, "clear logging")
    send_log(r1, 3, "SVC-ERR3c")
    send_log(r1, 5, "SVC-NOTE5c")
    flap(r1)
    sh(r1, "show logging", "S3-3 buffered warnings のときの show logging(全文)")
    conf(r1, ["logging buffered debugging"])
    # monitor / terminal monitor(SSH セッション側)
    clear_vty(r1)
    import paramiko
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(RT01_MGMT, username=USER, password=PW, look_for_keys=False, allow_agent=False, timeout=12)
    shl = c.invoke_shell()
    time.sleep(1.5)
    shl.send("terminal length 0\n")
    time.sleep(1)

    def drain():
        buf = b""
        time.sleep(4)
        while shl.recv_ready():
            buf += shl.recv(65535)
            time.sleep(0.2)
        return buf.decode(errors="replace")
    drain()
    send_log(r1, 3, "SVC-ERR3-NOTM")
    block("S3-4 SSH セッション(terminal monitor なし)に届いたもの", drain())
    shl.send("terminal monitor\n")
    drain()
    send_log(r1, 3, "SVC-ERR3-TM")
    send_log(r1, 6, "SVC-INFO6-TM")
    block("S3-4 terminal monitor 後に届いたもの(monitor level 既定)", drain())
    conf(r1, ["logging monitor warnings"], "S3-4 logging monitor warnings")
    drain()
    send_log(r1, 3, "SVC-ERR3-TM2")
    send_log(r1, 5, "SVC-NOTE5-TM2")
    block("S3-4 monitor warnings 後に届いたもの", drain())
    c.close()
    conf(r1, ["logging monitor debugging"])
    conf(r1, ["no logging console"], "S3-5 no logging console")
    sh(r1, "show logging | include Console", "S3-5 show logging の Console 行")
    conf(r1, ["logging console"])
    conf(r1, ["logging origin-id hostname"], "S3-6 logging origin-id hostname")
    sink.take()
    send_log(r1, 4, "SVC-ORIGIN")
    time.sleep(3)
    got = sink.take()
    block("S3-6 origin-id hostname で受信", "\n".join(d.decode(errors="replace").rstrip() for _, _, d in got))
    conf(r1, ["no logging origin-id", "logging source-interface Loopback0"], "S3-6 logging source-interface Loopback0(ホストへ経路なし)")
    sink.take()
    send_log(r1, 4, "SVC-SRCLO")
    time.sleep(3)
    got = sink.take()
    block("S3-6 source Lo0(戻り経路なし)で受信", "\n".join(f"from {a}: " + d.decode(errors='replace').rstrip() for _, a, d in got) or "(受信なし)")
    conf(r1, ["no logging source-interface"])
    sink.close()
    flush("S3 logging 既定/絞り/monitor")


def S4(devs):
    """service timestamps の各形。"""
    r1 = devs["RT01"]
    sh(r1, "show clock", "S4-0 show clock(NTP 未同期)")
    sh(r1, "show clock detail", "S4-0 show clock detail")
    variants = [
        ("基線", None),
        ("datetime", ["service timestamps log datetime"]),
        ("datetime msec", ["service timestamps log datetime msec"]),
        ("datetime msec localtime show-timezone (clock timezone JST 9)", ["clock timezone JST 9", "service timestamps log datetime msec localtime show-timezone"]),
        ("datetime year", ["service timestamps log datetime year"]),
        ("datetime localtime (timezone JST)", ["service timestamps log datetime localtime"]),
        ("uptime", ["service timestamps log uptime"]),
        ("no service timestamps log", ["no service timestamps log"]),
        ("service sequence-numbers + datetime msec", ["service sequence-numbers", "service timestamps log datetime msec"]),
    ]
    for name, lines in variants:
        if lines:
            conf(r1, lines)
        sh(r1, "show running-config | include service timestamps|service sequence|clock timezone", f"S4 [{name}] running-config")
        send_log(r1, 4, f"SVC-TS-{name.split()[0]}")
        sh(r1, "show logging | include SVC-TS", f"S4 [{name}] buffer の該当行")
    conf(r1, ["no service sequence-numbers", "no clock timezone", "service timestamps log datetime msec",
              "service timestamps debug datetime msec"])
    sh(r1, "show running-config | include service timestamps", "S4 復旧後")
    flush("S4 service timestamps")


def S5(devs):
    """debug condition interface の効き方。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    conf(r1, ["no logging console", "logging buffered 100000 debugging"])
    sh(r1, "clear logging")
    conf(r1, ["ip route 10.1.10.0 255.255.255.192 Ethernet0/3"])   # 念のため(直結)
    sh(r1, "debug condition interface Ethernet0/0", "S5-1 debug condition interface Ethernet0/0")
    sh(r1, "show debug condition", "S5-1 show debug condition")
    sh(r1, "debug ip icmp", "S5-1 debug ip icmp")
    sh(r1, "debug ip packet", "S5-1 debug ip packet")
    sh(r1, "show debugging", "S5-1 show debugging")
    ping(r2, "10.99.12.1", repeat=2)
    subprocess.run(["ping", "-c", "2", "-W", "2", RT01_MGMT], capture_output=True)
    time.sleep(2)
    sh(r1, "show logging | include ICMP|IP:", "S5-1 条件あり: RT02→e0/0 とホスト→e0/3 の ping のデバッグ出力")
    sh(r1, "clear logging")
    sh(r1, "no debug condition interface Ethernet0/0", "S5-2 条件解除")
    sh(r1, "show debug condition", "S5-2 show debug condition")
    ping(r2, "10.99.12.1", repeat=2)
    subprocess.run(["ping", "-c", "2", "-W", "2", RT01_MGMT], capture_output=True)
    time.sleep(2)
    sh(r1, "show logging | include ICMP|IP:", "S5-2 条件なし: 同じ 2 経路の ping")
    sh(r1, "undebug all")
    sh(r1, "clear logging")
    conf(r1, ["logging console", "logging buffered 8192 debugging", "no ip route 10.1.10.0 255.255.255.192 Ethernet0/3"])
    flush("S5 debug condition interface")


def _ntp_state(r1):
    st = sh(r1, "show ntp status")
    return ("Clock is synchronized" in st), st


def _assoc_detail(r1):
    return sh(r1, "show ntp associations detail | include configured|authenticated|sane|valid|stratum|our_master|reject|candidate|sys.peer", timeout=30)


def S6(devs):
    """NTP: master 既定 stratum・認証の各状態の指紋(全同期は待たず、associations detail の
    フラグ= configured/authenticated/sane/valid/reject を短時間で採る)。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    conf(r1, ["no ntp"])
    conf(r2, ["no ntp"])
    conf(r2, ["ntp master 5"], "S6-1 RT02 ntp master 5")
    time.sleep(8)
    sh(r2, "show ntp status", "S6-1 RT02 show ntp status(master 5・stratum)")
    conf(r2, ["no ntp master", "ntp master"], "S6-1b RT02 ntp master(引数なし=既定 stratum)")
    time.sleep(8)
    sh(r2, "show ntp status | include stratum|synchronized|reference", "S6-1b RT02 既定 stratum")
    sh(r2, "show running-config | include ntp", "S6-1b RT02 running-config(ntp master は stratum を省略表示するか)")
    # 認証なしの素の同期(フラグ確認のみ)
    conf(r1, ["ntp server 10.99.12.2"], "S6-2 RT01 ntp server(認証なし)")
    time.sleep(75)
    sh(r1, "show ntp associations", "S6-2 associations(認証なし・75秒)")
    _assoc_detail(r1)
    sh(r1, "show ntp status | include synchronized|stratum|reference", "S6-2 status(認証なし)")
    # 認証: RT02 に鍵・trusted・authenticate
    conf(r2, ["ntp authentication-key 1 md5 NTPKEY1", "ntp trusted-key 1", "ntp authenticate"], "S6-3 RT02 認証構成")
    states = [
        ("a: 鍵定義のみ・server key 1・authenticate なし・trusted なし",
         ["no ntp server 10.99.12.2", "no ntp authenticate", "no ntp trusted-key 1",
          "ntp authentication-key 1 md5 NTPKEY1", "ntp server 10.99.12.2 key 1"]),
        ("b: + ntp authenticate(trusted-key なし)",
         ["ntp authenticate"]),
        ("c: + ntp trusted-key 1(完全)",
         ["ntp trusted-key 1"]),
        ("d: 鍵不一致(RT01 の鍵1=WRONGKEY)",
         ["no ntp server 10.99.12.2", "no ntp authentication-key 1",
          "ntp authentication-key 1 md5 WRONGKEY", "ntp server 10.99.12.2 key 1"]),
        ("e: 鍵一致だが server 行に key 指定なし",
         ["no ntp server 10.99.12.2", "no ntp authentication-key 1",
          "ntp authentication-key 1 md5 NTPKEY1", "ntp server 10.99.12.2"]),
    ]
    for name, lines in states:
        conf(r1, lines, f"S6-3 RT01 [{name}]")
        sh(r1, "show running-config | include ntp", f"S6-3 [{name}] running-config")
        time.sleep(80)
        sh(r1, "show ntp associations", f"S6-3 [{name}] associations")
        _assoc_detail(r1)
        sh(r1, "show ntp status | include synchronized|stratum", f"S6-3 [{name}] status")
    # source interface + master stratum を継ぐか
    conf(r1, ["no ntp server 10.99.12.2", "ntp authentication-key 1 md5 NTPKEY1", "ntp authenticate", "ntp trusted-key 1",
              "ntp server 10.99.12.2 key 1", "ntp source Loopback0"], "S6-4 RT01 完全な認証 + source Loopback0")
    time.sleep(90)
    sh(r1, "show ntp associations", "S6-4 associations(source Lo0・90秒)")
    _assoc_detail(r1)
    sh(r1, "show ntp status | include synchronized|stratum|reference", "S6-4 status(stratum を master+1 で継ぐか)")
    sh(r2, "show ntp associations", "S6-4 RT02 側 associations(RT01 が client として見えるか)")
    conf(r1, ["no ntp"])
    conf(r2, ["no ntp"])
    flush("S6 NTP(認証フラグ指紋・全同期は待たない)")

def S8(devs):
    """archive / log config / hidekeys / configure replace。"""
    r1 = devs["RT01"]
    sh(r1, "show archive", "S8-0 show archive(未構成)")
    sh(r1, "show archive log config all", "S8-0 show archive log config all(未構成)")
    sh(r1, "copy running-config flash:manual.cfg", "S8-0 手動バックアップ")
    conf(r1, ["interface Loopback55", "ip address 55.55.55.55 255.255.255.255"])
    sh(r1, "configure replace flash:manual.cfg force", "S8-1 archive 未構成で configure replace")
    sh(r1, "show running-config | include Loopback55", "S8-1 Loopback55 は残っているか")
    conf(r1, ["archive", "path flash:RT01-bk", "write-memory", "time-period 1440"], "S8-2 archive path/write-memory/time-period")
    sh(r1, "show archive", "S8-2 show archive(保存前)")
    sh(r1, "write memory", "S8-2 write memory")
    time.sleep(2)
    sh(r1, "show archive", "S8-2 show archive(write 後)")
    sh(r1, "archive config", "S8-2 archive config(手動)")
    sh(r1, "show archive", "S8-2 show archive(手動後)")
    sh(r1, "dir flash: | include RT01-bk|manual", "S8-2 dir")
    conf(r1, ["archive", "log config", "logging enable"], "S8-3 log config / logging enable (hidekeys なし)")
    conf(r1, ["username test1 secret S3cretPW", "snmp-server community SECRETCOMM RO", "ntp authentication-key 5 md5 NTPKEY5",
              "enable secret En4bleS3c"])
    sh(r1, "show archive log config all", "S8-3 hidekeys なし")
    conf(r1, ["archive", "log config", "hidekeys"], "S8-3 hidekeys")
    conf(r1, ["username test2 secret S3cretPW2", "snmp-server community SECRETCOMM2 RO", "ntp authentication-key 6 md5 NTPKEY6"])
    sh(r1, "show archive log config all", "S8-3 hidekeys あり")
    conf(r1, ["archive", "log config", "notify syslog"], "S8-3 notify syslog")
    conf(r1, ["interface Loopback56", "ip address 56.56.56.56 255.255.255.255"])
    sh(r1, "show logging | include PARSER|CONFIG", "S8-3 notify syslog の出方")
    conf(r1, ["no username test1", "no username test2", "no snmp-server community SECRETCOMM", "no snmp-server community SECRETCOMM2",
              "no ntp authentication-key 5", "no ntp authentication-key 6", "no enable secret", "no interface Loopback56"])
    sh(r1, "show running-config | section archive", "S8-4 running-config の archive 節")
    sh(r1, "show archive config differences flash:manual.cfg", "S8-4 config differences(手動バックアップ vs 現在)")
    conf(r1, ["archive", "no log config", "no path flash:RT01-bk", "no write-memory", "no time-period 1440"])
    flush("S8 archive")


def S9(devs):
    """CEF: show ip cef の各エントリ・glean/drop・no ip cef。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    ping(r1, "10.99.12.2")
    sh(r1, "show ip cef", "S9-0 show ip cef(全体)")
    sh(r1, "show ip cef 10.99.12.2/32 detail", "S9-0 show ip cef 10.99.12.2/32 detail(隣接解決済)")
    sh(r1, "show ip cef 10.99.12.0/24 detail", "S9-0 show ip cef 10.99.12.0/24 detail(attached)")
    sh(r1, "show ip cef 10.99.12.1/32 detail", "S9-0 receive")
    sh(r1, "show ip cef adjacency glean", "S9-0 adjacency glean")
    sh(r1, "show ip cef adjacency drop", "S9-0 adjacency drop")
    sh(r1, "show adjacency Ethernet0/0 detail", "S9-0 show adjacency detail")
    sh(r1, "show ip cef exact-route 10.1.10.6 10.99.12.2", "S9-0 exact-route")
    conf(r1, ["ip route 172.16.0.0 255.255.0.0 10.99.12.9", "ip route 172.17.0.0 255.255.0.0 Null0", "ip route 172.18.0.0 255.255.0.0 Ethernet0/0"],
         "S9-1 静的(未解決 next-hop / Null0 / IF 指定)")
    time.sleep(2)
    sh(r1, "show ip cef 172.16.0.0/16 detail", "S9-1 next-hop 未解決(10.99.12.9)")
    sh(r1, "show ip cef 172.16.5.5 detail", "S9-1 172.16.5.5 の longest match")
    sh(r1, "show ip cef 172.17.0.0/16 detail", "S9-1 Null0")
    sh(r1, "show ip cef 172.18.0.0/16 detail", "S9-1 IF 指定(glean)")
    sh(r1, "show ip cef adjacency glean", "S9-1 adjacency glean(静的後)")
    sh(r1, "show ip cef adjacency drop", "S9-1 adjacency drop(静的後)")
    sh(r1, "show ip cef", "S9-1 show ip cef(静的後)")
    sh(r1, "show ip cef 9.9.9.9", "S9-1 経路なし宛先")
    sh(r1, "show ip route 172.16.0.0", "S9-1 RIB 側")
    conf(r1, ["no ip cef"], "S9-2 no ip cef")
    sh(r1, "show ip cef", "S9-2 show ip cef")
    sh(r1, "show ip interface Ethernet0/0 | include switching|CEF", "S9-2 show ip interface の switching 行")
    sh(r1, "show cef state | include CEF|enabled|disabled", "S9-2 show cef state")
    ok, _ = ping(r1, "10.99.12.2")
    note(f"S9-2 no ip cef でも ping 10.99.12.2 = {ok}%")
    conf(r1, ["ip cef"])
    conf(r1, ["interface Ethernet0/0", "no ip route-cache cef"], "S9-3 interface で no ip route-cache cef")
    sh(r1, "show ip interface Ethernet0/0 | include switching|CEF", "S9-3 show ip interface")
    sh(r1, "show running-config interface Ethernet0/0", "S9-3 running-config")
    conf(r1, ["interface Ethernet0/0", "ip route-cache cef"])
    conf(r1, ["interface Ethernet0/0", "no ip route-cache"], "S9-3b no ip route-cache(process switching)")
    sh(r1, "show ip interface Ethernet0/0 | include switching|CEF", "S9-3b show ip interface")
    conf(r1, ["interface Ethernet0/0", "ip route-cache"])
    sh(r1, "show ip interface Ethernet0/0 | include switching|CEF", "S9-3c 復旧後")
    conf(r1, ["no ip route 172.16.0.0 255.255.0.0 10.99.12.9", "no ip route 172.17.0.0 255.255.0.0 Null0", "no ip route 172.18.0.0 255.255.0.0 Ethernet0/0"])
    flush("S9 CEF")


def S10(devs):
    """copy: tftp-server / URL 書式 / ftp(ip ftp username) / scp サーバ(AAA 要件)。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    sh(r1, "copy running-config flash:RT01.cfg", "S10-0 copy running-config flash:RT01.cfg")
    conf(r1, ["tftp-server flash:RT01.cfg", "tftp-server flash:RT01.cfg alias rt01-alias.cfg"], "S10-1 tftp-server")
    block("S10-1 ホストの tftp クライアントで RT01.cfg", tftp_get(RT01_MGMT, "RT01.cfg"))
    block("S10-1 ホストの tftp クライアントで alias", tftp_get(RT01_MGMT, "rt01-alias.cfg"))
    block("S10-1 ホストの tftp クライアントで未公開ファイル(manual.cfg)", tftp_get(RT01_MGMT, "manual.cfg"))
    sh(r2, "copy tftp://10.99.12.1/RT01.cfg null:", "S10-1 RT02 から copy tftp://10.99.12.1/RT01.cfg null:")
    sh(r2, "copy tftp://10.99.12.1/nothere.cfg null:", "S10-1 RT02 から存在しないファイル")
    sh(r1, "copy running-config tftp://10.1.10.6/RT01.cfg", "S10-2 TFTP サーバが無い宛先へ copy(タイムアウト)", timeout=200)
    sh(r1, "copy running-config tftp:10.1.10.6/RT01.cfg", "S10-2 URL 書式誤り(// 無し)", timeout=200)
    srv, d = ftp_server()
    time.sleep(1)
    sh(r1, "copy running-config ftp://ftpu:ftpp@10.1.10.6:2121/RT01-ftp1.cfg", "S10-3 ftp URL にユーザ:パスワードとポート", timeout=120)
    conf(r1, ["ip ftp username ftpu", "ip ftp password ftpp"], "S10-3 ip ftp username/password")
    sh(r1, "copy running-config ftp://10.1.10.6:2121/RT01-ftp2.cfg", "S10-3 ip ftp username/password + URL", timeout=120)
    conf(r1, ["ip ftp password WRONG"])
    sh(r1, "copy running-config ftp://10.1.10.6:2121/RT01-ftp3.cfg", "S10-3 パスワード誤り", timeout=120)
    conf(r1, ["ip ftp password ftpp", "ip ftp passive"])
    sh(r1, "copy running-config ftp://10.1.10.6:2121/RT01-ftp4.cfg", "S10-3 ip ftp passive", timeout=120)
    block("S10-3 FTP サーバ側に届いたファイル", "\n".join(f"{p.name} {p.stat().st_size} bytes" for p in sorted(d.iterdir())))
    sh(r1, "copy ftp://10.1.10.6:2121/RT01-ftp2.cfg null:", "S10-3 FTP から取得", timeout=120)
    srv.close_all()
    conf(r1, ["no ip ftp username", "no ip ftp password", "no ip ftp passive"])
    # SCP サーバ
    conf(r1, ["ip scp server enable"], "S10-4 ip scp server enable(AAA なし・login local)")
    res, body = scp_pull(RT01_MGMT)
    block("S10-4 ホストから scp 取得(AAA なし)", res + "\n---\n" + body[:300])
    conf(r1, ["aaa new-model", "aaa authentication login CON none", "aaa authentication login default local",
              "line con 0", "login authentication CON"], "S10-4 aaa new-model + authentication login default local")
    res, body = scp_pull(RT01_MGMT)
    block("S10-4 scp(authentication のみ・authorization exec なし)", res + "\n---\n" + body[:300])
    conf(r1, ["aaa authorization exec default local"], "S10-4 + aaa authorization exec default local")
    res, body = scp_pull(RT01_MGMT)
    block("S10-4 scp(authorization exec あり)", res + "\n---\n" + body[:300])
    local = HERE / "_push.txt"
    local.write_text("hello from host\n")
    block("S10-4 scp でホスト→flash:pushed.txt", scp_push(RT01_MGMT, local, "flash:pushed.txt"))
    sh(r1, "dir flash: | include pushed", "S10-4 dir")
    sh(r1, "show running-config | include scp|aaa", "S10-4 running-config")
    conf(r1, ["no aaa authorization exec default local", "no aaa authentication login default local", "line con 0", "no login authentication CON",
              "exit", "no aaa authentication login CON none", "no aaa new-model", "no ip scp server enable",
              "no tftp-server flash:RT01.cfg", "no tftp-server flash:RT01.cfg alias rt01-alias.cfg"])
    sh(r1, "delete /force flash:pushed.txt")
    flush("S10 copy/tftp/ftp/scp")


def S11(devs):
    """SNMP: community/ACL/RO への set・v3 のエラー指紋・host/traps/informs・enable traps。"""
    r1 = devs["RT01"]
    conf(r1, ["access-list 10 permit 10.1.10.99",
              "snmp-server community PUBRO RO", "snmp-server community PRIVRW RW 10", "snmp-server community UNDEF RO 55",
              "snmp-server location POC-SVC", "snmp-server contact noc@example.com"], "S11-1 community 3 種")
    block("S11-1 get sysName / PUBRO(RO・ACL なし)", snmp_get(v2c("PUBRO")))
    block("S11-1 get / PRIVRW(RW・ACL 10 はホスト不許可)", snmp_get(v2c("PRIVRW")))
    block("S11-1 get / UNDEF(RO・ACL 55 未定義)", snmp_get(v2c("UNDEF")))
    block("S11-1 get / WRONG(未定義 community)", snmp_get(v2c("WRONG")))
    block("S11-1 set sysContact / PUBRO(RO)", snmp_set(v2c("PUBRO"), "set-by-ro"))
    conf(r1, ["access-list 10 permit 10.1.10.6"])
    block("S11-1 set sysContact / PRIVRW(RW・ACL 許可後)", snmp_set(v2c("PRIVRW"), "set-by-rw"))
    block("S11-1 get sysContact / PUBRO(set の反映確認)", snmp_get(v2c("PUBRO"), oid="1.3.6.1.2.1.1.4.0"))
    sh(r1, "show snmp | include SNMP packets|Bad|Unknown|Illegal|Encoding|Number of requested|Set-request|Get-request|Get-next|Response", "S11-1 show snmp カウンタ")
    sh(r1, "show logging | include SNMP", "S11-1 ログ(SNMP)")
    sh(r1, "show access-lists 10", "S11-1 ACL 10 カウンタ")
    sh(r1, "show snmp community", "S11-1 show snmp community")
    # view
    conf(r1, ["snmp-server view V-SYS iso included", "snmp-server view V-SYS system excluded", "snmp-server community VIEWED RO view V-SYS"],
         "S11-2 view で system を excluded")
    block("S11-2 get sysName / VIEWED(system excluded)", snmp_get(v2c("VIEWED")))
    block("S11-2 get ifNumber / VIEWED", snmp_get(v2c("VIEWED"), oid="1.3.6.1.2.1.2.1.0"))
    # v3
    conf(r1, ["snmp-server group G3PRIV v3 priv", "snmp-server group G3AUTH v3 auth",
              "snmp-server user u3 G3PRIV v3 auth sha AUTHPASS01 priv aes 128 PRIVPASS01",
              "snmp-server user u3a G3PRIV v3 auth sha AUTHPASS01",
              "snmp-server user u3md5 G3AUTH v3 auth md5 AUTHPASS01"], "S11-3 v3 group/user")
    sh(r1, "show snmp user", "S11-3 show snmp user")
    sh(r1, "show snmp group | begin G3", "S11-3 show snmp group")
    sh(r1, "show running-config | include snmp-server", "S11-3 running-config の snmp-server 行(user は載らない)")
    block("S11-3 v3 u3 authPriv 正しい", snmp_get(v3("u3", "AUTHPASS01", "PRIVPASS01")))
    block("S11-3 v3 u3 auth パスワード誤り", snmp_get(v3("u3", "WRONGPASS01", "PRIVPASS01")))
    block("S11-3 v3 u3 priv パスワード誤り", snmp_get(v3("u3", "AUTHPASS01", "WRONGPASS01")))
    block("S11-3 v3 u3 authNoPriv で要求(group は priv)", snmp_get(v3("u3", "AUTHPASS01")))
    block("S11-3 v3 u3a(auth のみのユーザ・group priv) authNoPriv", snmp_get(v3("u3a", "AUTHPASS01")))
    block("S11-3 v3 未定義ユーザ", snmp_get(v3("nouser", "AUTHPASS01", "PRIVPASS01")))
    block("S11-3 v3 u3md5 を sha で", snmp_get(v3("u3md5", "AUTHPASS01", authproto="sha")))
    block("S11-3 v3 u3md5 を md5 で(group auth)", snmp_get(v3("u3md5", "AUTHPASS01", authproto="md5")))
    sh(r1, "show snmp | include Unknown|Bad|Illegal|Unsupported|digest|time window|engine", "S11-3 show snmp の v3 系カウンタ")
    sh(r1, "show snmp engineID", "S11-3 show snmp engineID")
    # host / traps / informs
    conf(r1, ["snmp-server host 10.1.10.6 PUBRO"], "S11-4 snmp-server host(version 未指定)")
    sh(r1, "show running-config | include snmp-server host", "S11-4 running-config")
    sh(r1, "show snmp host", "S11-4 show snmp host")
    conf(r1, ["snmp-server host 10.1.10.6 informs version 1 PUBRO"], "S11-4 informs version 1")
    conf(r1, ["no snmp-server host 10.1.10.6 PUBRO",
              "snmp-server host 10.1.10.6 version 2c PUBRO udp-port 1162",
              "snmp-server host 10.1.10.6 informs version 2c PUBRO udp-port 1163"], "S11-4 traps(1162) と informs(1163)")
    sh(r1, "show snmp host", "S11-4 show snmp host(2 行)")
    sink = UdpSink(1162)
    sh(r1, "show running-config | include snmp-server enable", "S11-5 enable traps(未設定)")
    flap(r1)
    time.sleep(3)
    note(f"S11-5 enable traps 無しの linkDown/Up: trap 受信 {len(sink.take())} 個")
    conf(r1, ["snmp-server enable traps"], "S11-5 snmp-server enable traps(引数なし)")
    out = sh(r1, "show running-config | include snmp-server enable traps")
    n = len([ln for ln in out.splitlines() if "snmp-server enable traps" in ln])
    note(f"S11-5 引数なし enable traps → running-config に {n} 行")
    block("S11-5 running-config の enable traps 行(先頭 15 行)", "\n".join(out.splitlines()[:15]))
    flap(r1)
    time.sleep(4)
    got = sink.take()
    note(f"S11-5 enable traps 後の linkDown/Up: trap 受信 {len(got)} 個")
    time.sleep(40)
    sh(r1, "show snmp inform", "S11-5 show snmp inform(受信側なし・再送中)")
    sh(r1, "show snmp | include Inform|Trap|SNMP.*sent|Notification", "S11-5 show snmp の通知カウンタ")
    time.sleep(60)
    sh(r1, "show snmp inform", "S11-5 show snmp inform(100 秒後)")
    sink.close()
    conf(r1, ["no snmp-server enable traps", "no snmp-server host 10.1.10.6 version 2c PUBRO udp-port 1162",
              "no snmp-server host 10.1.10.6 informs version 2c PUBRO udp-port 1163",
              "no snmp-server community PUBRO", "no snmp-server community PRIVRW", "no snmp-server community UNDEF",
              "no snmp-server community VIEWED", "no snmp-server view V-SYS iso included", "no snmp-server view V-SYS system excluded",
              "no snmp-server user u3 G3PRIV v3", "no snmp-server user u3a G3PRIV v3", "no snmp-server user u3md5 G3AUTH v3",
              "no snmp-server group G3PRIV v3 priv", "no snmp-server group G3AUTH v3 auth", "no access-list 10"])
    flush("S11 SNMP")


def clear_vty(dev):
    """認証失敗で残った SSH セッションを落とす(vty 5 本が埋まると Connection refused になる罠・S2 で実発)。"""
    for i in range(5):
        dev.execute(f"clear line vty {i}", reply=DIALOG, error_pattern=[], timeout=30)
    time.sleep(1)
    return sh(dev, "show users")


def ssh_interactive(host=RT01_MGMT, user=USER, pw=PW, cmd="show users"):
    """OpenSSH を pexpect で対話(keyboard-interactive の Password: プロンプトに答える)。"""
    import pexpect
    args = SSH_COMMON + SSH_LEGACY + [f"{user}@{host}", cmd]
    child = pexpect.spawn("ssh", args, timeout=20, encoding="utf-8")
    log = []
    try:
        for _ in range(4):
            i = child.expect([r"(?i)password:", r"Permission denied", pexpect.EOF, pexpect.TIMEOUT])
            log.append((child.before or "")[-300:] + (child.after if isinstance(child.after, str) else ""))
            if i == 0:
                child.sendline(pw)
            elif i == 1:
                child.expect(pexpect.EOF)
                log.append(child.before or "")
                break
            else:
                break
    finally:
        child.close()
    return f"exit={child.exitstatus}\n" + "\n".join(x.strip() for x in log if x.strip())


def S2b(devs):
    """S2 の再測(vty 枯渇の影響を除く): login の種類・access-class(未定義 ACL 含む)・セッション残留時間。"""
    r1 = devs["RT01"]
    sh(r1, "show users", "S2b-0 再測前の show users")
    sh(r1, "show ssh", "S2b-0 show ssh")
    block("S2b-0 clear line vty 0-4 後", clear_vty(r1))
    conf(r1, ["line vty 0 4", "login local", "transport input ssh", "no access-class 10 in", "no access-class 55 in"])
    ok, txt = ssh_login(cmds=("show users",))
    block(f"S2b-1 対照: login local + {USER} → {'OK' if ok else 'NG'}", txt[-500:] if ok else txt)
    clear_vty(r1)
    conf(r1, ["line vty 0 4", "password vtypass", "login"], "S2b-2 login + password vtypass")
    sh(r1, "show running-config | section line vty", "S2b-2 running-config")
    block("S2b-2 OpenSSH 対話(SUZUKI / vtypass)", ssh_interactive(pw="vtypass"))
    block("S2b-2 OpenSSH 対話(anyone / vtypass)", ssh_interactive(user="anyone", pw="vtypass"))
    ok, txt = ssh_login(pw="vtypass", cmds=("show users",))
    block(f"S2b-2 paramiko {USER}/vtypass → {'OK' if ok else 'NG'}", txt[-500:] if ok else txt)
    sh(r1, "show logging | include SSH2_USERAUTH|SEC_LOGIN", "S2b-2 ログ")
    sh(r1, "show users", "S2b-2 show users(失敗セッションの残留)")
    sh(r1, "show ssh", "S2b-2 show ssh")
    clear_vty(r1)
    sh(r1, "clear logging")
    conf(r1, ["line vty 0 4", "no login"], "S2b-3 no login")
    block("S2b-3 OpenSSH 対話(no login)", ssh_interactive())
    sh(r1, "show logging | include SSH|SEC_LOGIN", "S2b-3 ログ")
    clear_vty(r1)
    sh(r1, "clear logging")
    conf(r1, ["line vty 0 4", "login local", "no password"])
    block("S2b-4 login local + 未定義ユーザ nouser", ssh_interactive(user="nouser", pw="x"))
    ok, txt = ssh_login(user="nouser", pw="x", cmds=("show users",))
    block(f"S2b-4 paramiko nouser → {'OK' if ok else 'NG'}", txt)
    ok, txt = ssh_login(pw="WRONGPW", cmds=("show users",))
    block(f"S2b-4 paramiko {USER}/誤パスワード → {'OK' if ok else 'NG'}", txt)
    sh(r1, "show logging | include SSH|SEC_LOGIN", "S2b-4 ログ(失敗の指紋)")
    out = sh(r1, "show users", "S2b-4 show users(失敗直後)")
    sh(r1, "show ssh", "S2b-4 show ssh(失敗直後)")
    t0 = time.time()
    t, info = wait_for(lambda: (("vty" not in sh(r1, "show users").lower()) and True, None), timeout=200, step=20, what="失敗セッションの解放")
    note(f"S2b-4 失敗セッションが vty から消えるまで {int(time.time()-t0)} 秒(上限 200)")
    sh(r1, "show users", "S2b-4 show users(解放後)")
    # access-class
    clear_vty(r1)
    sh(r1, "clear logging")
    conf(r1, ["access-list 10 permit 10.1.10.99", "line vty 0 4", "access-class 10 in"], "S2b-5 access-class 10 in(ホスト不許可)")
    block("S2b-5 OpenSSH 接続段階", ssh_probe())
    block("S2b-5 tcp 22", tcp_probe(RT01_MGMT, 22))
    sh(r1, "show access-lists 10", "S2b-5 ACL カウンタ")
    sh(r1, "show logging | include SEC|SSH|ACCESS", "S2b-5 ログ")
    conf(r1, ["no access-list 10", "access-list 10 deny 10.1.10.6 log", "access-list 10 permit any"], "S2b-5b deny log 明示")
    block("S2b-5b OpenSSH 接続段階", ssh_probe())
    time.sleep(3)
    sh(r1, "show access-lists 10", "S2b-5b ACL カウンタ")
    sh(r1, "show logging | include SEC|IPACCESS", "S2b-5b ログ")
    conf(r1, ["line vty 0 4", "access-class 55 in"], "S2b-6 access-class 55 in(ACL 55 未定義)")
    sh(r1, "show running-config | section line vty", "S2b-6 running-config")
    ok, txt = ssh_login(cmds=("show users",))
    block(f"S2b-6 未定義 ACL → ssh {'OK' if ok else 'NG'}", txt[-500:] if ok else txt)
    clear_vty(r1)
    conf(r1, ["no access-list 10", "access-list 10 permit 10.1.10.6", "line vty 0 4", "access-class 10 in"], "S2b-7 ACL 10 permit ホスト")
    ok, txt = ssh_login(cmds=("show users",))
    block(f"S2b-7 permit ホスト → ssh {'OK' if ok else 'NG'}", txt[-500:] if ok else txt)
    sh(r1, "show access-lists 10", "S2b-7 ACL カウンタ")
    clear_vty(r1)
    conf(r1, ["line vty 0 4", "no access-class 10 in", "no access-list 10"])
    flush("S2b vty 再測(login 種類/access-class/セッション残留)")


def S8b(devs):
    """S8 の再測(console 同期ずれの影響を除く・1 行ずつ投入): archive path/write-memory/time-period・
    configure replace(archive 無しでも可か)・log config の hidekeys 既定・notify syslog。"""
    r1 = devs["RT01"]
    conf(r1, ["no logging console"])
    conf(r1, ["no archive"])
    sh(r1, "show archive", "S8b-0 show archive(未構成)")
    sh(r1, "show archive log config all", "S8b-0 log config(未構成)")
    sh(r1, "copy running-config flash:manual2.cfg", "S8b-0 手動バックアップ manual2.cfg")
    time.sleep(2)
    conf(r1, ["interface Loopback57", "ip address 57.57.57.57 255.255.255.255"])
    sh(r1, "show running-config | include Loopback57", "S8b-1 Loopback57 追加後")
    out = sh(r1, "configure replace flash:manual2.cfg list force", "S8b-1 archive 未構成で configure replace list force", timeout=120)
    time.sleep(3)
    sh(r1, "show running-config | include Loopback57", "S8b-1 replace 後の Loopback57")
    conf(r1, ["interface Loopback58", "ip address 58.58.58.58 255.255.255.255"])
    sh(r1, "configure replace flash:manual2.cfg", "S8b-1b force 無し(確認プロンプトに Y)", timeout=120)
    time.sleep(3)
    sh(r1, "show running-config | include Loopback58", "S8b-1b replace 後の Loopback58")
    for lines in (["archive"], ["archive", "path flash:RT01-bk"], ["archive", "write-memory"],
                  ["archive", "time-period 1440"], ["archive", "maximum 5"]):
        conf(r1, lines, f"S8b-2 投入: {' / '.join(lines)}")
    sh(r1, "show running-config | section archive", "S8b-2 running-config の archive 節")
    sh(r1, "show archive", "S8b-2 show archive(保存前)")
    sh(r1, "write memory")
    time.sleep(4)
    sh(r1, "show archive", "S8b-2 show archive(write memory 後)")
    sh(r1, "archive config", "S8b-2 archive config(手動)")
    time.sleep(3)
    out = sh(r1, "show archive", "S8b-2 show archive(手動後)")
    sh(r1, "dir flash: | include RT01-bk", "S8b-2 dir flash:")
    latest = None
    for ln in out.splitlines():
        if "Most Recent" in ln:
            latest = ln.split()[1] if ln.split() else None
    note(f"S8b-2 最新アーカイブ = {latest}")
    conf(r1, ["interface Loopback59", "ip address 59.59.59.59 255.255.255.255"])
    sh(r1, "show archive config differences", "S8b-3 show archive config differences(最新 vs 現在)")
    if latest:
        sh(r1, f"configure replace {latest} force", "S8b-3 最新アーカイブへ configure replace force", timeout=120)
        time.sleep(3)
        sh(r1, "show running-config | include Loopback59", "S8b-3 replace 後の Loopback59")
    sh(r1, "show archive config rollback timer", "S8b-3 rollback timer")
    conf(r1, ["archive", "log config", "logging enable"], "S8b-4 log config / logging enable")
    sh(r1, "show running-config | section archive", "S8b-4 running-config(hidekeys は既定か)")
    conf(r1, ["username test3 secret S3cretPW3", "snmp-server community SECRETCOMM3 RO", "enable secret En4bleS3c3"])
    sh(r1, "show archive log config all", "S8b-4 既定(hidekeys 行なし)での表示")
    conf(r1, ["archive", "log config", "no hidekeys"], "S8b-4 no hidekeys")
    sh(r1, "show running-config | section archive", "S8b-4 running-config(no hidekeys 後)")
    conf(r1, ["username test4 secret S3cretPW4", "snmp-server community SECRETCOMM4 RO", "ntp authentication-key 7 md5 NTPKEY7"])
    sh(r1, "show archive log config all", "S8b-4 no hidekeys での表示")
    conf(r1, ["archive", "log config", "hidekeys"])
    conf(r1, ["archive", "log config", "notify syslog"], "S8b-5 notify syslog")
    sh(r1, "clear logging")
    conf(r1, ["interface Loopback60", "ip address 60.60.60.60 255.255.255.255", "description test"])
    sh(r1, "show logging | include PARSER|CONFIG", "S8b-5 notify syslog の出方")
    sh(r1, "show archive log config statistics", "S8b-5 statistics")
    conf(r1, ["no username test3", "no username test4", "no snmp-server community SECRETCOMM3", "no snmp-server community SECRETCOMM4",
              "no ntp authentication-key 7", "no enable secret", "no interface Loopback60", "no archive", "logging console"])
    sh(r1, "delete /force flash:manual2.cfg")
    flush("S8b archive 再測")


def S9b(devs):
    """S9 の要点再測(console lag を避け 1 コマンドずつ): no ip cef の効き・detail の flags・
    未解決 next-hop / Null0 / glean。"""
    r1 = devs["RT01"]
    conf(r1, ["no logging console", "ip cef", "interface Ethernet0/0", "ip route-cache cef", "exit"])
    ping(r1, "10.99.12.2")
    sh(r1, "show ip cef 10.99.12.2/32 detail", "S9b-0 detail: 隣接解決済(attached)")
    sh(r1, "show ip cef 10.99.12.1/32 detail", "S9b-0 detail: receive(self)")
    sh(r1, "show ip cef 10.99.12.0/24 detail", "S9b-0 detail: attached/connected")
    conf(r1, ["ip route 172.16.0.0 255.255.0.0 10.99.12.9", "ip route 172.17.0.0 255.255.0.0 Null0",
              "ip route 172.18.0.0 255.255.0.0 Ethernet0/0"])
    time.sleep(2)
    sh(r1, "show ip cef 172.16.0.0/16 detail", "S9b-1 未解決 next-hop(recursive)")
    sh(r1, "show ip cef 172.17.0.0/16 detail", "S9b-1 Null0")
    sh(r1, "show ip cef 172.18.0.0/16 detail", "S9b-1 IF 指定(glean)")
    sh(r1, "show ip cef adjacency glean", "S9b-1 adjacency glean")
    sh(r1, "show ip cef adjacency drop", "S9b-1 adjacency drop")
    conf(r1, ["no ip cef"])
    time.sleep(2)
    sh(r1, "show ip cef", "S9b-2 no ip cef 後の show ip cef")
    sh(r1, "show ip interface Ethernet0/0 | include CEF|switching|route-cache", "S9b-2 show ip interface")
    ok, _ = ping(r1, "10.99.12.2")
    note(f"S9b-2 no ip cef でも ping = {ok}%")
    conf(r1, ["ip cef"])
    sh(r1, "show ip interface Ethernet0/0 | include CEF|switching|route-cache", "S9b-2 ip cef 復旧後")
    conf(r1, ["interface Ethernet0/0", "no ip route-cache cef"])
    sh(r1, "show ip interface Ethernet0/0 | include CEF|switching|route-cache", "S9b-3 IF で no ip route-cache cef")
    conf(r1, ["interface Ethernet0/0", "ip route-cache cef"])
    conf(r1, ["no ip route 172.16.0.0 255.255.0.0 10.99.12.9", "no ip route 172.17.0.0 255.255.0.0 Null0",
              "no ip route 172.18.0.0 255.255.0.0 Ethernet0/0", "logging console"])
    flush("S9b CEF 再測")


def S10b(devs):
    """S10 の要点再測: flash: への copy(file prompt quiet)・tftp-server の公開/非公開。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    conf(r1, ["no logging console", "file prompt quiet"])
    sh(r1, "copy running-config flash:RT01.cfg", "S10b-0 copy running-config flash:RT01.cfg(quiet)")
    time.sleep(2)
    sh(r1, "dir flash: | include RT01.cfg|manual", "S10b-0 dir flash:")
    conf(r1, ["tftp-server flash:RT01.cfg"], "S10b-1 tftp-server flash:RT01.cfg")
    sh(r1, "show running-config | include tftp-server", "S10b-1 running-config")
    time.sleep(1)
    block("S10b-1 ホスト tftp で公開ファイル RT01.cfg", tftp_get(RT01_MGMT, "RT01.cfg"))
    block("S10b-1 ホスト tftp で非公開ファイル nvram:startup-config", tftp_get(RT01_MGMT, "nvram:startup-config"))
    sh(r2, "copy tftp://10.99.12.1/RT01.cfg null:", "S10b-1 RT02 から公開ファイル取得", timeout=90)
    sh(r2, "copy tftp://10.99.12.1/RT99.cfg null:", "S10b-1 RT02 から非公開/存在しないファイル", timeout=90)
    conf(r1, ["no tftp-server flash:RT01.cfg"])
    sh(r1, "delete /force flash:RT01.cfg")
    flush("S10b copy/tftp 再測")


def S2c(devs):
    """S2 の要点再測(paramiko のみ・vty をこまめに clear): login 方式と access-class の
    未定義 ACL の挙動。paramiko は認証成功/失敗を明確に返すので pexpect の無限リトライを避ける。"""
    r1 = devs["RT01"]
    clear_vty(r1)
    conf(r1, ["no access-list 10", "line vty 0 4", "no access-class 10 in", "no access-class 55 in",
              "login local", "no password", "transport input ssh"])
    def try_ssh(user, pw, tag):
        ok, txt = ssh_login(user=user, pw=pw, cmds=("show users",))
        note(f"{tag}: user={user} pw={pw} → {'ログイン成功' if ok else 'ログイン失敗(' + txt.split(':')[0] + ')'}")
        clear_vty(r1)
        return ok
    # login local
    try_ssh(USER, PW, "S2c-1 login local + 正ユーザ")
    try_ssh(USER, "WRONGPW", "S2c-1 login local + 誤パスワード")
    try_ssh("ghost", "x", "S2c-1 login local + 未定義ユーザ")
    # login (line password)
    conf(r1, ["line vty 0 4", "password linepw", "login"], "S2c-2 login(line password)")
    sh(r1, "show running-config | section line vty", "S2c-2 running-config")
    try_ssh(USER, "linepw", "S2c-2 login + username/linepw")
    try_ssh("anyuser", "linepw", "S2c-2 login + 任意ユーザ/linepw")
    try_ssh(USER, PW, "S2c-2 login + username/username-secret")
    # no login
    conf(r1, ["line vty 0 4", "no login", "no password"], "S2c-3 no login")
    try_ssh(USER, "", "S2c-3 no login + 空パスワード")
    try_ssh(USER, "anything", "S2c-3 no login + 任意パスワード")
    # aaa new-model + login default local
    conf(r1, ["line vty 0 4", "login local"])
    # access-class: 未定義 ACL
    conf(r1, ["line vty 0 4", "access-class 55 in"], "S2c-4 access-class 55 in(ACL 55 未定義)")
    sh(r1, "show running-config | section line vty", "S2c-4 running-config")
    ok = try_ssh(USER, PW, "S2c-4 未定義 ACL の access-class")
    note(f"S2c-4 → 未定義 ACL の access-class は {'許可(permit all)' if ok else '拒否(deny all)'}")
    # access-class: 定義済み・送信元不許可
    conf(r1, ["access-list 55 permit 10.1.10.99", "line vty 0 4", "access-class 55 in"], "S2c-5 ACL 55 = permit 10.1.10.99 のみ")
    sh(r1, "show access-lists 55", "S2c-5 ACL 55")
    ok = try_ssh(USER, PW, "S2c-5 送信元不許可(暗黙 deny)")
    note(f"S2c-5 → ホスト(.6)は暗黙 deny で {'許可' if ok else '拒否'}")
    sh(r1, "show access-lists 55", "S2c-5 ACL 55 カウンタ(暗黙 deny の可視性)")
    # access-class: 定義済み・送信元許可
    conf(r1, ["access-list 55 permit 10.1.10.6", "line vty 0 4", "access-class 55 in"], "S2c-6 ACL 55 に permit host 追加")
    ok = try_ssh(USER, PW, "S2c-6 送信元許可")
    sh(r1, "show access-lists 55", "S2c-6 ACL 55 カウンタ")
    conf(r1, ["line vty 0 4", "no access-class 55 in", "no access-list 55"])
    flush("S2c vty 再測(paramiko・login 方式/未定義 access-class)")


def help_of(dev, cmd, mode="config"):
    """IOS の '?' ヘルプを生で採る(unicon の execute は部分コマンド付きプロンプトで詰まるため
    transmit/receive で読み、Ctrl-U で行を消す)。best-effort。"""
    try:
        if mode == "config":
            dev.execute("configure terminal", reply=DIALOG, error_pattern=[])
        dev.transmit(cmd + "?")
        time.sleep(2.0)
        dev.receive(r".+", timeout=3)
        out = dev.receive_buffer()
        dev.transmit("\x15")          # Ctrl-U: 行をクリア
        time.sleep(0.5)
        dev.receive(r".+", timeout=2)
        dev.receive_buffer()
        if mode == "config":
            dev.execute("end", reply=DIALOG, error_pattern=[])
        return out
    except Exception as e:
        try:
            dev.transmit("\x15")
            time.sleep(0.5)
            dev.execute("end", reply=DIALOG, error_pattern=[])
        except Exception:
            pass
        return f"(help_of failed: {type(e).__name__}: {e})"


def S12(devs):
    """「定説と違う」2 点の深掘り(対照付き): 鍵長の受理範囲・SSHv1・既定値の直接確認
    (show running-config all)・hidekeys が既定で伏せる対象の範囲。"""
    r1 = devs["RT01"]
    conf(r1, ["no logging console"])
    sh(r1, "show version | include Software|Version|IOS", "S12-0 ソフトウェア版")
    # CSDL compliance shield(FN-72511 の回避策)の有無
    sh(r1, "show running-config all | include compliance", "S12-0 running-config all の compliance 行")
    block("S12-0 crypto engine compliance ? (ヘルプ)", help_of(r1, "crypto engine compliance "))
    sh(r1, "show crypto engine compliance shield", "S12-0 show crypto engine compliance shield")
    # --- 鍵長の受理範囲 ---
    block("S12-1 crypto key generate rsa modulus ? (ヘルプ)", help_of(r1, "crypto key generate rsa modulus "))
    block("S12-1 crypto key generate rsa ? (ヘルプ)", help_of(r1, "crypto key generate rsa "))
    block("S12-1 ip ssh version ? (ヘルプ)", help_of(r1, "ip ssh version "))
    block("S12-1 crypto key generate ec keysize ? (ヘルプ)", help_of(r1, "crypto key generate ec keysize "))
    for bits in (1536, 2048, 3072, 4096):
        conf(r1, ["crypto key zeroize rsa"])
        conf(r1, [f"crypto key generate rsa modulus {bits}"], f"S12-2 modulus {bits}")
        sh(r1, "show crypto key mypubkey rsa | include Key name|bits", f"S12-2 [{bits}] mypubkey")
    conf(r1, ["crypto key zeroize rsa"])
    conf(r1, ["crypto key generate rsa general-keys modulus 1024"], "S12-2 general-keys modulus 1024 (別構文)")
    conf(r1, ["crypto key generate rsa general-keys modulus 2048 label SSHKEY"], "S12-2 general-keys modulus 2048 label SSHKEY")
    sh(r1, "show crypto key mypubkey rsa | include Key name|bits", "S12-2 mypubkey(label 付き)")
    sh(r1, "show ip ssh | include SSH|Minimum|Modulus|SECSH", "S12-2 show ip ssh 抜粋")
    # EC 鍵だけで SSH が上がるか
    conf(r1, ["crypto key zeroize rsa"])
    sh(r1, "show ip ssh | include SSH|Please", "S12-3 RSA 消去後")
    conf(r1, ["crypto key generate ec keysize 256 label ECKEY"], "S12-3 EC 鍵(256)生成")
    sh(r1, "show ip ssh | include SSH|Please|SECSH", "S12-3 EC 鍵だけの show ip ssh")
    ok, txt = ssh_login(cmds=("show ip ssh | include SSH",))
    block(f"S12-3 EC 鍵だけで paramiko ログイン → {'OK' if ok else 'NG'}", txt[-300:] if ok else txt)
    conf(r1, ["crypto key generate rsa modulus 2048"])
    # --- 既定値の直接確認: show running-config all ---
    sh(r1, "show running-config all | include ip ssh", "S12-4 running-config all の ip ssh 行(既定値込み)")
    sh(r1, "show running-config all | section archive", "S12-4 running-config all の archive 節(既定値込み・archive 未構成)")
    conf(r1, ["archive", "log config", "logging enable"])
    sh(r1, "show running-config all | section archive", "S12-4 running-config all の archive 節(log config 構成後)")
    sh(r1, "show running-config | section archive", "S12-4 running-config(既定は省略)")
    block("S12-4 archive log config ? (ヘルプ)", help_of(r1, "archive\rlog config\r"))
    # --- hidekeys が伏せる対象(既定=ON) ---
    secrets = [
        "username hk1 password 0 PlainPW1", "username hk2 secret Secret2",
        "enable password PlainEn3", "enable secret SecretEn4",
        "snmp-server community COMM5 RO", "ntp authentication-key 6 md5 NTPKEY6",
        "key chain KC7", "key 1", "key-string KS7", "exit", "exit",
        "tacacs server T8", "address ipv4 192.0.2.8", "key TKEY8", "exit",
        "radius server R9", "address ipv4 192.0.2.9 auth-port 1812 acct-port 1813", "key RKEY9", "exit",
        "crypto isakmp key IKEKEY10 address 192.0.2.10",
        "ip ftp password FTPPW11",
        "line vty 0 4", "password VTYPW12", "login local", "exit",
        "interface Loopback61", "ip address 61.61.61.61 255.255.255.255", "ip ospf message-digest-key 1 md5 OSPFKEY13", "exit",
        "router bgp 65000", "neighbor 192.0.2.14 remote-as 65001", "neighbor 192.0.2.14 password BGPPW14", "exit",
        "ip ssh authentication-retries 2",
    ]
    conf(r1, secrets, "S12-5 秘密を含むコマンド一式(既定=hidekeys)")
    sh(r1, "show archive log config all", "S12-5 既定(hidekeys)での記録")
    conf(r1, ["archive", "log config", "no hidekeys"], "S12-5 no hidekeys")
    secrets2 = [x.replace("1", "1b").replace("2", "2b") if ("PW" in x or "KEY" in x or "Secret" in x or "COMM" in x or "KS" in x) else x for x in secrets]
    conf(r1, secrets2, "S12-5 同じ一式(no hidekeys)")
    sh(r1, "show archive log config all", "S12-5 no hidekeys での記録")
    conf(r1, ["archive", "log config", "hidekeys"])
    sh(r1, "show running-config | section archive", "S12-5 hidekeys を明示した後の running-config(既定なら省略される)")
    # 後始末
    conf(r1, ["no username hk1", "no username hk2", "no enable password", "no enable secret",
              "no snmp-server community COMM5", "no ntp authentication-key 6", "no key chain KC7",
              "no tacacs server T8", "no radius server R9", "no crypto isakmp key IKEKEY10 address 192.0.2.10",
              "no ip ftp password", "line vty 0 4", "no password", "exit",
              "no interface Loopback61", "no router bgp 65000", "no ip ssh authentication-retries", "no archive",
              "logging console"])
    flush("S12 定説と違う 2 点の深掘り(鍵長/SSHv1/既定値/hidekeys の範囲)")


def S12b(devs):
    """S12 の後半(help_of 抜き): EC 鍵のみでの SSH・show running-config all による既定値・hidekeys の伏字範囲。"""
    r1 = devs["RT01"]
    conf(r1, ["no logging console"])
    conf(r1, ["crypto key zeroize rsa"])
    sh(r1, "show ip ssh | include SSH|Please", "S12b-3 RSA 消去後")
    conf(r1, ["crypto key generate ec keysize 256 label ECKEY"], "S12b-3 EC 鍵(256)生成")
    time.sleep(2)
    sh(r1, "show ip ssh | include SSH|Please|SECSH", "S12b-3 EC 鍵だけの show ip ssh")
    ok, txt = ssh_login(cmds=("show ip ssh | include SSH",))
    block(f"S12b-3 EC 鍵だけで paramiko ログイン → {'OK' if ok else 'NG'}", txt[-300:] if ok else txt)
    conf(r1, ["crypto key generate rsa modulus 2048"])
    time.sleep(2)
    sh(r1, "show running-config all | include ip ssh", "S12b-4 running-config all の ip ssh 行(既定値込み)")
    sh(r1, "show running-config all | section archive", "S12b-4 running-config all の archive 節(archive 未構成)")
    conf(r1, ["archive", "log config", "logging enable"])
    sh(r1, "show running-config all | section archive", "S12b-4 running-config all の archive 節(log config 構成後)")
    sh(r1, "show running-config | section archive", "S12b-4 running-config(既定は省略される)")
    secrets = [
        "username hk1 password 0 PlainPW1", "username hk2 secret Secret2",
        "enable password PlainEn3", "enable secret SecretEn4",
        "snmp-server community COMM5 RO", "ntp authentication-key 6 md5 NTPKEY6",
        "key chain KC7", "key 1", "key-string KS7", "exit", "exit",
        "tacacs server T8", "address ipv4 192.0.2.8", "key TKEY8", "exit",
        "radius server R9", "address ipv4 192.0.2.9 auth-port 1812 acct-port 1813", "key RKEY9", "exit",
        "crypto isakmp key IKEKEY10 address 192.0.2.10",
        "ip ftp password FTPPW11",
        "line vty 0 4", "password VTYPW12", "login local", "exit",
        "interface Loopback61", "ip address 61.61.61.61 255.255.255.255", "ip ospf message-digest-key 1 md5 OSPFKEY13", "exit",
        "router bgp 65000", "neighbor 192.0.2.14 remote-as 65001", "neighbor 192.0.2.14 password BGPPW14", "exit",
        "ip ssh authentication-retries 2",
    ]
    conf(r1, secrets, "S12b-5 秘密を含むコマンド一式(既定=hidekeys)")
    sh(r1, "show archive log config all", "S12b-5 既定(hidekeys)での記録")
    conf(r1, ["archive", "log config", "no hidekeys"], "S12b-5 no hidekeys")
    sh(r1, "clear archive log config")
    secrets2 = [x.replace("PW1", "PWb1").replace("Secret2", "SecretB2").replace("En3", "EnB3").replace("En4", "EnB4")
                .replace("COMM5", "COMMB5").replace("KEY6", "KEYB6").replace("KS7", "KSB7").replace("KEY8", "KEYB8")
                .replace("KEY9", "KEYB9").replace("KEY10", "KEYB10").replace("PW11", "PWB11").replace("PW12", "PWB12")
                .replace("KEY13", "KEYB13").replace("PW14", "PWB14") for x in secrets]
    conf(r1, secrets2, "S12b-5 同じ一式(no hidekeys)")
    sh(r1, "show archive log config all", "S12b-5 no hidekeys での記録")
    conf(r1, ["archive", "log config", "hidekeys"])
    sh(r1, "show running-config | section archive", "S12b-5 hidekeys を明示した後の running-config(既定なら省略される)")
    conf(r1, ["no username hk1", "no username hk2", "no enable password", "no enable secret",
              "no snmp-server community COMM5", "no snmp-server community COMMB5", "no ntp authentication-key 6",
              "no key chain KC7", "no tacacs server T8", "no radius server R9",
              "no crypto isakmp key IKEKEY10 address 192.0.2.10", "no crypto isakmp key IKEKEYB10 address 192.0.2.10",
              "no ip ftp password", "line vty 0 4", "no password", "exit",
              "no interface Loopback61", "no router bgp 65000", "no ip ssh authentication-retries", "no archive"])
    flush("S12b 定説と違う 2 点の深掘り(EC 鍵/既定値の直読み/hidekeys の範囲)")


def S12c(devs):
    """対照: CSDL compliance shield を無効化して再起動すると 1024 ビット RSA が通るか(FN-72511 の回避策)。"""
    r1 = devs["RT01"]
    conf(r1, ["crypto engine compliance shield disable"], "S12c-1 crypto engine compliance shield disable")
    sh(r1, "show running-config | include compliance", "S12c-1 running-config")
    sh(r1, "write memory", "S12c-1 write memory")
    time.sleep(3)
    try:
        r1.disconnect()
    except Exception:
        pass
    node = LAB.get_node_by_label("RT01")
    print("[i] RT01 stop/start via CML API ...", flush=True)
    node.stop(wait=True)
    node.start(wait=True)
    time.sleep(90)
    devs2 = connect_all(LAB, required=("RT01",))
    r1 = devs2["RT01"]
    devs["RT01"] = r1
    conf(r1, ["no logging console"])
    sh(r1, "show version | include uptime", "S12c-2 再起動後の uptime")
    sh(r1, "show running-config all | include compliance", "S12c-2 running-config all の compliance 行(再起動後)")
    conf(r1, ["crypto key zeroize rsa"])
    for bits in (512, 768, 1024):
        conf(r1, [f"crypto key generate rsa modulus {bits}"], f"S12c-3 shield 無効で modulus {bits}")
        sh(r1, "show crypto key mypubkey rsa | include Key name|bits", f"S12c-3 [{bits}] mypubkey")
        sh(r1, "show ip ssh | include SSH|Please|Minimum|Modulus", f"S12c-3 [{bits}] show ip ssh")
        ok, txt = ssh_login(cmds=("show ip ssh | include SSH",))
        block(f"S12c-3 [{bits}] paramiko ログイン → {'OK' if ok else 'NG'}", txt[-200:] if ok else txt)
        block(f"S12c-3 [{bits}] OpenSSH 接続段階", ssh_probe())
        conf(r1, ["crypto key zeroize rsa"])
    conf(r1, ["ip ssh version 1"], "S12c-4 shield 無効で ip ssh version 1")
    sh(r1, "show running-config all | include ip ssh", "S12c-4 running-config all の ip ssh 行(shield 無効)")
    conf(r1, ["no crypto engine compliance shield disable", "crypto key generate rsa modulus 2048"], "S12c-5 復旧")
    sh(r1, "write memory")
    flush("S12c 対照: compliance shield 無効化+再起動で弱い RSA 鍵が通るか")


def _try_conf(dev, lines, title):
    try:
        conf(dev, lines, title)
    except Exception as e:
        note(f"{title}: 投入で例外 {type(e).__name__}: {e}")
        try:
            dev.execute("end", reply=DIALOG, error_pattern=[])
        except Exception:
            pass


def S12d(devs):
    """(a) 無垢の RT02 で config logger / hidekeys の既定を直読み
       (b) RT01 で hidekeys が伏せる対象の範囲(小分け投入)"""
    r1, r2 = devs["RT01"], devs["RT02"]
    # (a) RT02: archive を一度も触っていない対照
    sh(r2, "show archive", "S12d-a RT02 show archive(無垢)")
    sh(r2, "show archive log config all", "S12d-a RT02 show archive log config all(無垢)")
    sh(r2, "show running-config | section archive", "S12d-a RT02 running-config の archive 節(無垢)")
    sh(r2, "show running-config all | section archive", "S12d-a RT02 running-config all の archive 節(無垢)")
    conf(r2, ["username probe1 secret Pr0be1", "snmp-server community PROBE2 RO"])
    sh(r2, "show archive log config all", "S12d-a RT02 何も構成せずに変更後の show archive log config all")
    conf(r2, ["archive", "log config", "logging enable"], "S12d-a RT02 logging enable を明示")
    conf(r2, ["username probe3 secret Pr0be3"])
    sh(r2, "show archive log config all", "S12d-a RT02 logging enable 明示後")
    sh(r2, "show running-config | section archive", "S12d-a RT02 running-config(明示後)")
    conf(r2, ["no username probe1", "no username probe3", "no snmp-server community PROBE2", "no archive"])
    # (b) RT01: hidekeys の範囲
    conf(r1, ["no logging console", "archive", "log config", "logging enable", "hidekeys"])
    sh(r1, "clear archive log config")
    groups = [
        (["username hk1 password 0 PlainPW1", "username hk2 secret Secret2"], "username password/secret"),
        (["enable password PlainEn3"], "enable password"),
        (["enable secret SecretEn4"], "enable secret"),
        (["snmp-server community COMM5 RO"], "snmp community"),
        (["ntp authentication-key 6 md5 NTPKEY6"], "ntp key"),
        (["key chain KC7", "key 1", "key-string KS7"], "key chain key-string"),
        (["tacacs server T8", "address ipv4 192.0.2.8", "key TKEY8"], "tacacs key"),
        (["radius server R9", "address ipv4 192.0.2.9 auth-port 1812 acct-port 1813", "key RKEY9"], "radius key"),
        (["crypto isakmp key IKEKEY10 address 192.0.2.10"], "isakmp key"),
        (["ip ftp password FTPPW11"], "ip ftp password"),
        (["line vty 0 4", "password VTYPW12"], "line password"),
        (["interface Loopback61", "ip address 61.61.61.61 255.255.255.255", "ip ospf message-digest-key 1 md5 OSPFKEY13"], "ospf md5"),
        (["router bgp 65000", "neighbor 192.0.2.14 remote-as 65001", "neighbor 192.0.2.14 password BGPPW14"], "bgp password"),
        (["ip ssh authentication-retries 2"], "(対照・秘密なし)"),
    ]
    for lines, name in groups:
        _try_conf(r1, lines, f"S12d-b [{name}] hidekeys")
    sh(r1, "show archive log config all", "S12d-b hidekeys(既定)での記録")
    conf(r1, ["archive", "log config", "no hidekeys"])
    sh(r1, "clear archive log config")
    for lines, name in groups:
        lines2 = [x.replace("PW1", "PWb1").replace("Secret2", "SecretB2").replace("En3", "EnB3").replace("En4", "EnB4")
                  .replace("COMM5", "COMMB5").replace("KEY6", "KEYB6").replace("KS7", "KSB7").replace("KEY8", "KEYB8")
                  .replace("KEY9", "KEYB9").replace("KEY10", "KEYB10").replace("PW11", "PWB11").replace("PW12", "PWB12")
                  .replace("KEY13", "KEYB13").replace("PW14", "PWB14").replace("retries 2", "retries 3") for x in lines]
        _try_conf(r1, lines2, f"S12d-b [{name}] no hidekeys")
    sh(r1, "show archive log config all", "S12d-b no hidekeys での記録")
    conf(r1, ["archive", "log config", "hidekeys"])
    sh(r1, "show running-config | section archive", "S12d-b hidekeys 明示後の running-config")
    _try_conf(r1, ["no username hk1", "no username hk2", "no enable password", "no enable secret",
                   "no snmp-server community COMM5", "no snmp-server community COMMB5", "no ntp authentication-key 6",
                   "no key chain KC7", "no tacacs server T8", "no radius server R9",
                   "no crypto isakmp key IKEKEY10 address 192.0.2.10", "no crypto isakmp key IKEKEYB10 address 192.0.2.10",
                   "no ip ftp password", "line vty 0 4", "no password", "exit",
                   "no interface Loopback61", "no router bgp 65000", "no ip ssh authentication-retries", "no archive"], "S12d 後始末")
    flush("S12d 無垢の対照(RT02)と hidekeys の伏字範囲(RT01)")


def S12e(devs):
    """S12c の再起動後の部分(shield 無効の状態で弱い RSA 鍵・SSHv1 が通るか)。"""
    r1 = devs["RT01"]
    conf(r1, ["no logging console", "no enable secret", "no enable password"])   # S12b の残骸(再起動前に保存されていた)
    sh(r1, "show version | include uptime", "S12e-2 再起動後の uptime")
    sh(r1, "show running-config all | include compliance", "S12e-2 running-config all の compliance 行(再起動後)")
    conf(r1, ["crypto key zeroize rsa"])
    for bits in (512, 768, 1024):
        conf(r1, [f"crypto key generate rsa modulus {bits}"], f"S12e-3 shield 無効で modulus {bits}")
        time.sleep(2)
        sh(r1, "show crypto key mypubkey rsa | include Key name|bits", f"S12e-3 [{bits}] mypubkey")
        sh(r1, "show ip ssh | include SSH|Please|Minimum|Modulus", f"S12e-3 [{bits}] show ip ssh")
        ok, txt = ssh_login(cmds=("show ip ssh | include SSH",))
        block(f"S12e-3 [{bits}] paramiko ログイン → {'OK' if ok else 'NG'}", txt[-200:] if ok else txt)
        block(f"S12e-3 [{bits}] OpenSSH 接続段階", ssh_probe())
        clear_vty(r1)
        conf(r1, ["crypto key zeroize rsa"])
    conf(r1, ["ip ssh version 1"], "S12e-4 shield 無効で ip ssh version 1")
    sh(r1, "show running-config all | include ip ssh version|ip ssh dh", "S12e-4 running-config all の version/dh 行(shield 無効)")
    conf(r1, ["ip ssh dh min size 1024"], "S12e-4 ip ssh dh min size 1024 (shield 無効)")
    sh(r1, "show ip ssh | include Minimum", "S12e-4 show ip ssh の Minimum 行")
    conf(r1, ["no ip ssh dh min size", "no crypto engine compliance shield disable", "crypto key generate rsa modulus 2048"], "S12e-5 復旧")
    sh(r1, "write memory")
    flush("S12e 対照: compliance shield 無効(再起動後)で弱い RSA 鍵/SSHv1 が通るか")


def S12f(devs):
    """残りの小確認: RT02(no archive 後)の running-config all 表示・RT01 の startup-config の shield 行。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    sh(r2, "show archive log config all", "S12f RT02 show archive log config all(no archive 後)")
    sh(r2, "show running-config all | section archive", "S12f RT02 running-config all の archive 節(no archive 後)")
    conf(r2, ["archive", "log config", "no logging enable"])
    sh(r2, "show running-config all | section archive", "S12f RT02 running-config all(archive あり・logging enable 明示 off)")
    conf(r2, ["no archive"])
    sh(r1, "show startup-config | include compliance", "S12f RT01 startup-config の compliance 行")
    sh(r1, "show running-config | include compliance", "S12f RT01 running-config の compliance 行")
    conf(r1, ["crypto engine compliance shield disable"], "S12f RT01 再投入")
    sh(r1, "show running-config | include compliance", "S12f RT01 再投入後")
    sh(r1, "show logging | include ompliance|shield|CSDL", "S12f RT01 ログ(compliance)")
    conf(r1, ["no crypto engine compliance shield disable"])
    flush("S12f 小確認")


CHECKS = {"S1": S1, "S2": S2, "S2b": S2b, "S2c": S2c, "S3b": S3, "S8b": S8b, "S9b": S9b, "S10b": S10b, "S12": S12, "S12b": S12b, "S12c": S12c, "S12d": S12d, "S12e": S12e, "S12f": S12f, "S3": S3, "S4": S4, "S5": S5, "S6": S6, "S8": S8, "S9": S9, "S10": S10, "S11": S11}


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: sweep.py build | " + " ".join(CHECKS) + " | all | teardown")
        return
    client = ClientLibrary(CML[0], CML[1], CML[2], ssl_verify=False)
    if args == ["teardown"]:
        for lab in client.find_labs_by_title(LAB_TITLE):
            print(f"[i] stop/wipe/remove {LAB_TITLE}")
            lab.stop(wait=True)
            lab.wipe(wait=True)
            lab.remove()
        return
    lab = ensure_lab(client)
    global LAB
    LAB = lab
    devs = connect_all(lab)
    if args == ["build"]:
        for label in NODES:
            print(f"[i] {label}: base 投入")
            conf(devs[label], BASE[label])
        time.sleep(5)
        print("[i] host→RT01 mgmt ping:", subprocess.run(["ping", "-c", "2", "-W", "2", RT01_MGMT], capture_output=True).returncode)
        print("[i] host→RT02 mgmt ping:", subprocess.run(["ping", "-c", "2", "-W", "2", RT02_MGMT], capture_output=True).returncode)
        print("[i] RT01→RT02:", ping(devs["RT01"], "10.99.12.2")[0], "%")
        return
    names = list(CHECKS) if args == ["all"] else args
    for name in names:
        print(f"\n===== {name} =====", flush=True)
        try:
            CHECKS[name](devs)
        except Exception as e:
            import traceback
            note(f"{name} 例外: {type(e).__name__}: {e}")
            traceback.print_exc()
            flush(f"{name} (例外で中断)")
    for d in devs.values():
        try:
            d.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
