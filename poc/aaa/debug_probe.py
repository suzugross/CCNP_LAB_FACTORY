#!/usr/bin/env python3
"""BL-101 P0 追試2: **ルータ側 debug の出力**で故障種が区別できるかを実測する。

背景(2026-08-08 ユーザ指摘): 紙面 evidence 形の正解を「認証サーバの radius.log」に
置いていたが、**サーバログで何が読めるかは ENARSI の学習範囲に無い**ため、
`show aaa servers` との差を解答者が判断できず**設問として成立しない**。
→ 機器側(IOS)の出力だけで切り分けられるかを測り直す。

測るもの: `debug radius authentication` / `debug aaa authentication` /
          `debug aaa authorization` の出力を、故障種ごとに採取する。

使い方: debug_probe.py [ケース名...]
"""
import re
import sys
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-debug.md"

ADMIN, ADMIN_PW = "SUZUKI", "CCNP"
RAD_USER, RAD_PW = "noc-taro", "Noc-1234"
LOCAL_ONLY, LOCAL_ONLY_PW = "emg-admin", "Emg-1234"
GRP = "RADGRP"

DEBUGS = ["debug radius authentication", "debug aaa authentication",
          "debug aaa authorization"]


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


class Router:
    def __init__(self, ip):
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=40)
        self.sh = self.cli.invoke_shell(width=511)
        self._expect()
        self.send("terminal length 0")
        self.send("terminal monitor")        # ★debug をこのセッションへ出す

    def _expect(self, timeout=120):
        t0, buf = time.time(), ""
        while time.time() - t0 < timeout:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
                lines = buf.splitlines()
                if lines and re.search(r"[\w.\-]+(\([\w\-]+\))?#\s*$", lines[-1]):
                    return buf
            else:
                time.sleep(0.05)
        return buf

    def drain(self, sec):
        t0, buf = time.time(), ""
        while time.time() - t0 < sec:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
            else:
                time.sleep(0.1)
        return buf

    def send(self, cmd):
        self.sh.send(cmd + "\n")
        return self._expect()

    def conf(self, lines):
        self.send("configure terminal")
        for ln in lines:
            self.send(ln)
        self.send("end")

    def close(self):
        try:
            self.send("undebug all")
            self.send("terminal no monitor")
        except Exception:
            pass
        try:
            self.cli.close()
        except Exception:
            pass


class Server:
    def __init__(self, ip):
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=40)

    def run(self, cmd):
        _, o, e = self.cli.exec_command(cmd, timeout=90)
        return (o.read().decode() + e.read().decode()).strip()

    def close(self):
        try:
            self.cli.close()
        except Exception:
            pass


def ensure_up(rt, limit=340):
    t0 = time.time()
    while time.time() - t0 < limit:
        out = rt.send("show aaa servers | include State:")
        if "DEAD" not in out:
            return
        time.sleep(15)


def capture(rt, user, pw, extra=25):
    """debug を張った状態で test aaa を撃ち、出力を採る。"""
    for d in DEBUGS:
        rt.send(d)
    rt.sh.send(f"test aaa group {GRP} {user} {pw} legacy\n")
    buf = rt._expect(timeout=90)
    buf += rt.drain(extra)                # ★debug 行は遅れて出るので追い drain
    rt.send("undebug all")
    lines = []
    for ln in buf.splitlines():
        ln = ln.rstrip()
        if not ln or ln.startswith("test aaa") or re.match(r"^\S+#\s*$", ln):
            continue
        if "undebug" in ln or "All possible debugging" in ln:
            continue
        lines.append(ln)
    return "\n".join(lines)


def main():
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    h = hosts()
    rt = Router(h["RT02"])
    s1, s2 = Server(h["SRV01"]), Server(h["SRV02"])

    def svc(action, which=("s1", "s2")):
        for name in which:
            (s1 if name == "s1" else s2).run(
                f"sudo -n systemctl {action} freeradius")
        time.sleep(3)

    cases = []

    def case(key, desc, fn):
        cases.append((key, desc, fn))

    case("D0", "基線: 正常に受理される", lambda: capture(rt, RAD_USER, RAD_PW))

    def d1():
        return capture(rt, LOCAL_ONLY, LOCAL_ONLY_PW)
    case("D1", "user_not_registered: サーバが拒否を返す", d1)

    def d2():
        rt.conf([f"radius server RAD1", " key WrongKey-9999", "exit",
                 f"radius server RAD2", " key WrongKey-9999", "exit"])
        time.sleep(2)
        out = capture(rt, RAD_USER, RAD_PW, extra=40)
        rt.conf([f"radius server RAD1", " key Poc-Rad-1111", "exit",
                 f"radius server RAD2", " key Poc-Rad-1111", "exit"])
        return out
    case("D2", "★key_mismatch: 共有鍵が違う", d2)

    def d3():
        rt.conf(["no ip radius source-interface Loopback0"])
        time.sleep(2)
        out = capture(rt, RAD_USER, RAD_PW, extra=40)
        rt.conf(["ip radius source-interface Loopback0"])
        return out
    case("D3", "★src_iface_missing: 送信元が許可外", d3)

    def d4():
        rt.conf(["radius server RAD2",
                 " address ipv4 10.99.2.2 auth-port 1812 acct-port 1813", "exit"])
        svc("stop", ("s1",))
        out = capture(rt, RAD_USER, RAD_PW, extra=40)
        rt.conf(["radius server RAD2",
                 " address ipv4 10.99.2.2 auth-port 1912 acct-port 1913", "exit"])
        svc("start", ("s1",))
        return out
    case("D4", "port_mismatch: 待受ポート違い(RAD1 停止)", d4)

    def d5():
        svc("stop")
        out = capture(rt, RAD_USER, RAD_PW, extra=40)
        svc("start")
        return out
    case("D5", "全断: サーバが両方落ちている", d5)

    results = []
    try:
        for key, desc, fn in cases:
            if want and key not in want:
                continue
            print(f"--- {key}: {desc}", flush=True)
            ensure_up(rt)
            t0 = time.time()
            try:
                out = fn()
            except Exception as ex:
                out = f"(ERROR {type(ex).__name__}: {ex})"
            results.append((key, desc, out, time.time() - t0))
            print(f"    done {time.time() - t0:.0f}s", flush=True)
    finally:
        try:
            svc("start")
        except Exception:
            pass
        rt.close(); s1.close(); s2.close()

    md = ["# BL-101 P0 追試2 — ルータ側 debug の出力", "",
          "自動生成: poc/aaa/debug_probe.py。対象= _POC-AAA の RT02。",
          "採取した debug= `debug radius authentication` / `debug aaa authentication` /",
          "`debug aaa authorization`。", ""]
    for key, desc, out, el in results:
        md.append(f"## {key} — {desc}  ({el:.0f}s)\n")
        md.append("```\n" + (out or "(出力なし)") + "\n```\n")
    OUT.write_text("\n".join(md))
    print(f"\n書き出し: {OUT}")


if __name__ == "__main__":
    main()
