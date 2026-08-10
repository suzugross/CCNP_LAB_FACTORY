#!/usr/bin/env python3
"""BL-108 の決着: **`aaa group server radius` の `timeout`/`retransmit` は何なのか**(2026-08-10)。

GEN-AAAGRP の初出題で受験者が踏んだ罠(→ poc/aaa/README.md §19.8)。
グループ配下に書くと**受理されるのに名前付きサーバへ効かない**ように見えた。
文献調査では Cisco はこの 2 値を**グローバル/サーバ個別**でしか documented しておらず、
グループ submode に出てくるのは `server-private` の行内オプションのみ。

残っていた未確定を 2 つとも取る。

  H) **パーサのヘルプ**に出るか。`config-sg-radius` で `?` を打つ。
     出る = 仕様(ただし名前付きサーバには効かない可能性) / 出ない = 隠し・事故寄り。
  F) **機能試験**。グローバルを消し、グループ配下だけに `timeout 2 / retransmit 1` を置いて
     片系断のログイン所要を測る。
       - 4 秒前後  → グループの値が効いている
       - 20 秒前後 → 効いておらず **IOS 既定(timeout 5 × 4 試行)** に落ちている

使い方: grouptimer_probe.py
出力  : poc/aaa/results-grouptimer.md
"""
import re
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-grouptimer.md"

ADMIN, ADMIN_PW = "SUZUKI", "CCNP"
RAD_USER, RAD_PW = "noc-taro", "Noc-1234"
GRP = "RADGRP"
RT = "10.1.12.2"
SSHO = ("-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
        "-o ConnectTimeout=20 -o LogLevel=ERROR -o NumberOfPasswordPrompts=1 "
        "-o ServerAliveInterval=5 -o ServerAliveCountMax=8")
PROMPT = re.compile(r"[\w.\-]+(\([\w\-]+\))?[#>]\s*$")

LOG = []


def say(s=""):
    print(s, flush=True)
    LOG.append(s)


class Router:
    def __init__(self, ip):
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=60, auth_timeout=150)
        self.sh = self.cli.invoke_shell(width=511)
        self._expect()
        self.send("terminal length 0")

    def _expect(self, t=60):
        t0, buf = time.time(), ""
        while time.time() - t0 < t:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
                ls = buf.splitlines()
                if ls and PROMPT.search(ls[-1]):
                    return buf
            else:
                time.sleep(0.1)
        return buf

    def send(self, cmd, t=60):
        self.sh.send(cmd + "\n")
        return self._expect(t)

    def raw(self, keys, wait=3.0):
        """`?` のように改行を伴わない入力を打ち、届いたものを集める。"""
        self.sh.send(keys)
        t0, buf = time.time(), ""
        while time.time() - t0 < wait:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
                t0 = time.time()
            else:
                time.sleep(0.1)
        return buf

    def body(self, cmd):
        return [l.rstrip() for l in self.send(cmd).splitlines()[1:]
                if l.strip() and not PROMPT.search(l)]

    def close(self):
        try:
            self.cli.close()
        except Exception:
            pass


class Server:
    def __init__(self, ip):
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=60)

    def run(self, cmd, t=180):
        _, o, e = self.cli.exec_command(cmd, timeout=t)
        return (o.read().decode() + e.read().decode()).strip()

    def stop(self):
        return self.run("sudo -n systemctl stop freeradius")

    def start(self):
        self.run("sudo -n systemctl start freeradius")
        return self.run("systemctl is-active freeradius")

    def login(self):
        t0 = time.time()
        out = self.run(f"timeout 60 sshpass -p '{RAD_PW}' ssh {SSHO} "
                       f"{RAD_USER}@{RT} 'show privilege' 2>&1")
        return ("privilege level is 15" in out), time.time() - t0

    def close(self):
        try:
            self.cli.close()
        except Exception:
            pass


def main():
    h = yaml.safe_load((GEN / "mgmt_map.yml").read_text())
    s1, s2, r = Server(h["SRV01"]), Server(h["SRV02"]), Router(h["RT02"])
    say(f"# BL-108 決着 — グループ配下の timeout/retransmit ({time.strftime('%Y-%m-%d %H:%M')})")
    say()
    try:
        # ---------------- H) パーサのヘルプ --------------------------------
        say("## H. `config-sg-radius` のヘルプに出るか")
        say()
        r.send("configure terminal")
        r.send("aaa group server radius ZZPROBE")
        helptxt = r.raw("?", 4.0)
        r.raw("\x15")                      # Ctrl-U で入力行を消す
        clean = [l.rstrip() for l in helptxt.splitlines()
                 if l.strip() and not l.strip().startswith("ZZPROBE")]
        say("```")
        for l in clean:
            say(l)
        say("```")
        hit = [l for l in clean if re.match(r"\s*(timeout|retransmit)\b", l)]
        say()
        say(f"- `timeout` / `retransmit` の行: "
            f"{'**出る** → ' + ' / '.join(x.strip() for x in hit) if hit else '**出ない**'}")
        for q in ("timeout ?", "retransmit ?"):
            out = r.raw(q, 3.0)
            r.raw("\x15")
            say(f"- `{q}` → `{' '.join(out.split())[:120]}`")
        r.send("")
        r.send("exit")
        r.send("no aaa group server radius ZZPROBE")
        r.send("end")
        say()

        # ---------------- F) 機能試験 --------------------------------------
        say("## F. グループ配下だけに置いたときの実所要(片系断)")
        say()
        say("| 置き場所 | 構成 | 1回目 | 2回目 | 期待 |")
        say("|---|---|---|---|---|")
        cases = [
            ("グローバル", ["radius-server timeout 2", "radius-server retransmit 1",
                            f"aaa group server radius {GRP}", "no timeout",
                            "no retransmit", "exit"], "2×2=**4 秒**"),
            ("グループ配下のみ", ["no radius-server timeout", "no radius-server retransmit",
                                  f"aaa group server radius {GRP}", "timeout 2",
                                  "retransmit 1", "exit"],
             "効けば 4 秒 / 効かなければ既定 5×4=**20 秒**"),
        ]
        for label, cfg, exp in cases:
            s1.start(); s2.start(); time.sleep(4)
            r.send("configure terminal")
            for c in cfg:
                r.send(c)
            r.send("end")
            r.send("clear aaa counters servers all")
            shown = " / ".join(r.body("show running-config | include ^radius-server (timeout|retransmit)")
                               or ["(グローバルは空)"])
            s1.login()
            s1.stop()
            _, d1 = s1.login()
            _, d2 = s1.login()
            s1.start()
            say(f"| {label} | `{shown}` | {d1:.1f}s | {d2:.1f}s | {exp} |")
        # 基線へ
        r.send("configure terminal")
        for c in [f"aaa group server radius {GRP}", "no timeout", "no retransmit", "exit",
                  "radius-server timeout 3", "radius-server retransmit 1"]:
            r.send(c)
        r.send("end")
    finally:
        try:
            s1.start(); s2.start()
        except Exception:
            pass
        for c in (s1, s2, r):
            try:
                c.close()
            except Exception:
                pass
        say()
        OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
        print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
