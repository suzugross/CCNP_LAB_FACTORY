#!/usr/bin/env python3
"""BL-105 の前提2件の裏取り: **`show aaa servers` はいつ DEAD になるか**(2026-08-10)。

紙面 `shape=aaa` の `aaa_servers_block()` は「到達不能なら DEAD」と描いている。
しかし P0 §5 は「片系断で RAD1 は **UP のまま**」と記録しており、両者は矛盾する。
BL-105(故障種 `deadtime_only`)を作る前に、ここを確定させる。

測ること:
  A) `radius-server dead-criteria` **無し** ＋ SRV01 停止 → 連続ログインの所要と
     `show aaa servers` の State の推移。DEAD になるか、%RADIUS-4-RADIUS_DEAD は出るか。
  B) `dead-criteria time 5 tries 1` **有り** ＋ 同条件 → 同上。
  C) 健全時(両系生存)の `show running-config | include dead-criteria` が空であること
     = 「既定では入っていない」ことの一次証拠。

  ★State はログインの **1 回ごと**に採る(前回の追試は 1 回目の後しか見ておらず、
    DEAD への遷移を取り逃していた)。

使い方: deadstate_probe.py
出力  : poc/aaa/results-deadstate.md
"""
import re
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-deadstate.md"

ADMIN, ADMIN_PW = "SUZUKI", "CCNP"
RAD_USER, RAD_PW = "noc-taro", "Noc-1234"
GRP = "RADGRP"
RT = "10.1.12.2"                      # RT02 のインバンド
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
        self.ip = ip
        self._open()

    def _open(self):
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(self.ip, username=ADMIN, password=ADMIN_PW,
                         look_for_keys=False, allow_agent=False,
                         timeout=60, auth_timeout=150, banner_timeout=90)
        self.sh = self.cli.invoke_shell(width=511)
        self._expect()
        self.sh.send("terminal length 0\n")
        self._expect()

    def _expect(self, t=90):
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

    def send(self, cmd, t=90):
        try:
            self.sh.send(cmd + "\n")
        except Exception:
            self.close(); self._open(); self.sh.send(cmd + "\n")
        return self._expect(t)

    def conf(self, lines):
        self.send("configure terminal")
        for ln in lines:
            self.send(ln)
        return self.send("end")

    def body(self, cmd):
        out = self.send(cmd)
        return [l.rstrip() for l in out.splitlines()[1:]
                if l.strip() and not PROMPT.search(l)]

    def state(self):
        """各サーバの State 行だけを 1 行にまとめる。"""
        rows, host = [], None
        for ln in self.body("show aaa servers | include host|State"):
            m = re.search(r"host (\S+),", ln)
            if m:
                host = m.group(1).rstrip(",")
            elif "State:" in ln and host:
                st = ln.split("State:", 1)[1].strip()
                rows.append(f"{host}={st.split(',')[0]}")
                host = None
        return " / ".join(rows) if rows else "(取得できず)"

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
        """SRV01 から RT02 へ実ログイン。(成否, 秒) を返す。"""
        t0 = time.time()
        out = self.run(f"timeout 45 sshpass -p '{RAD_PW}' ssh {SSHO} "
                       f"{RAD_USER}@{RT} 'show privilege' 2>&1")
        return ("privilege level is 15" in out), time.time() - t0

    def close(self):
        try:
            self.cli.close()
        except Exception:
            pass


CASES = [("A", "dead-criteria 無し", ["no radius-server dead-criteria"]),
         ("B", "dead-criteria time 5 tries 1",
          ["radius-server dead-criteria time 5 tries 1"])]


def main():
    h = yaml.safe_load((GEN / "mgmt_map.yml").read_text())
    s1, s2 = Server(h["SRV01"]), Server(h["SRV02"])
    r2 = Router(h["RT02"])
    say(f"# BL-105 前提の裏取り — show aaa servers の DEAD 条件 "
        f"({time.strftime('%Y-%m-%d %H:%M')})")
    say()
    try:
        # --- C) 既定では dead-criteria が入っていないこと -------------------
        r2.conf(["no radius-server dead-criteria"])
        say("## C. 既定の構成に `dead-criteria` は入っているか")
        say()
        line = r2.body("show running-config | include dead-criteria")
        say(f"- `show running-config | include dead-criteria` → "
            f"`{line[0] if line else '(出力なし)'}`")
        say("- → **既定では入らない**。健全な盤面に持たせるには明示設定が要る。")
        say()

        # --- A/B) 片系断での State 推移 -------------------------------------
        say("## A/B. 片系断(SRV01 停止)で連続ログインしたときの State 推移")
        say()
        say("| dead-criteria | 直前 | 1回目 | 2回目 | 3回目 | 4回目 | RADIUS_DEAD ログ |")
        say("|---|---|---|---|---|---|---|")
        for _tag, label, cfg in CASES:
            s1.start(); s2.start(); time.sleep(4)
            r2.conf([f"aaa group server radius {GRP}", "deadtime 1", "exit"] + cfg)
            r2.send("clear logging")
            s1.login()                       # UP へ戻す
            time.sleep(2)
            before = r2.state()
            s1.stop()
            cells = []
            for _ in range(4):
                ok, sec = s1.login()
                cells.append(f"{'✅' if ok else '❌'}{sec:.1f}s<br/>{r2.state()}")
            dead = r2.body("show logging | include RADIUS_DEAD")
            s1.start()
            say(f"| {label} | {before} | " + " | ".join(cells) + " | "
                + (f"`{dead[-1].strip()[:60]}`" if dead else "(出ず)") + " |")
        r2.conf(["no radius-server dead-criteria",
                 f"aaa group server radius {GRP}", "deadtime 5", "exit"])
    finally:
        try:
            s1.start(); s2.start()
        except Exception:
            pass
        for c in (s1, s2, r2):
            try:
                c.close()
            except Exception:
                pass
        say()
        OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
        print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
