#!/usr/bin/env python3
"""BL-101 P2 PoC-2 追試2: **`dead-criteria` を入れれば deadtime は挙動で見えるか**(2026-08-09)。

追試1(results-deadtime.md)は仮説を否定した= `deadtime` を何分にしても、片系断のまま
連続ログインすると**毎回**タイムアウト分だけ待つ(6.3s→6.4s→6.4s)。P0 §5 の
「RAD1 は `show aaa servers` 上 UP のまま(DEAD 化しない)」と整合する。

理由の候補: **`radius-server dead-criteria` を満たさないとサーバは DEAD にならず、
DEAD にならなければ `deadtime` は出番が無い**。つまり `deadtime` だけ書いても
何も起きない ── これが本当なら、構築問の要件として一級品(書いたのに効かない)。

  D1  dead-criteria 無し + deadtime 1     … 追試1 の再確認(毎回待つ)
  D2  dead-criteria time 5 tries 1 + dt 1 … 1 回の失敗で DEAD 化するか
  D3  dead-criteria time 5 tries 2 + dt 1 … tries の効き
各ケースで 3 連続ログインの所要と、その間の `show aaa servers` の状態を採る。

使い方: deadcrit_probe.py
出力  : poc/aaa/results-deadcrit.md
"""
import re
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-deadcrit.md"

ADMIN, ADMIN_PW = "SUZUKI", "CCNP"
RAD_USER, RAD_PW = "noc-taro", "Noc-1234"
GRP = "RADGRP"
RT02_INBAND = "10.1.12.2"
SSH_COMMON = ("-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
              "-o ConnectTimeout=30 -o LogLevel=ERROR -o NumberOfPasswordPrompts=1")

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
        self.cli.connect(self.ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=60)
        self.sh = self.cli.invoke_shell(width=511)
        self._expect()
        self.sh.send("terminal length 0\n")
        self._expect()

    def _expect(self, timeout=120):
        t0, buf = time.time(), ""
        while time.time() - t0 < timeout:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
                lines = buf.splitlines()
                if lines and re.search(r"[\w.\-]+(\([\w\-]+\))?#\s*$", lines[-1]):
                    return buf
            else:
                time.sleep(0.15)
        return buf

    def send(self, cmd, timeout=120):
        """★セッションが落ちていたら張り直して再送(破壊フェーズを挟むと切れる実測あり)。"""
        try:
            self.sh.send(cmd + "\n")
        except Exception:
            self.close()
            self._open()
            self.sh.send(cmd + "\n")
        return self._expect(timeout)

    def conf(self, lines):
        self.send("configure terminal")
        for ln in lines:
            self.send(ln)
        return self.send("end")

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

    def run(self, cmd, timeout=180):
        _, o, e = self.cli.exec_command(cmd, timeout=timeout)
        return (o.read().decode() + e.read().decode()).strip()

    def stop(self):
        return self.run("sudo -n systemctl stop freeradius")

    def start(self):
        self.run("sudo -n systemctl start freeradius")
        return self.run("systemctl is-active freeradius")

    def close(self):
        try:
            self.cli.close()
        except Exception:
            pass


def login(s1):
    t0 = time.time()
    out = s1.run(f"sshpass -p '{RAD_PW}' ssh {SSH_COMMON} {RAD_USER}@{RT02_INBAND} "
                 f"'show privilege' 2>&1", timeout=180)
    dt = time.time() - t0
    return ("privilege level is 15" in out, dt)


def state(r2):
    """`show aaa servers` から各サーバの状態行だけを抜く。"""
    txt = r2.send("show aaa servers | include host|State")
    out = []
    host = None
    for ln in txt.splitlines():
        ln = ln.strip()
        m = re.search(r"host (\S+), auth-port (\d+)", ln)
        if m:
            host = f"{m.group(1)}:{m.group(2)}"
        elif ln.startswith("State") and host:
            out.append(f"{host}={ln.split(':', 1)[1].strip()[:24]}")
            host = None
    return " / ".join(out) if out else "(状態行なし)"


CASES = [
    ("D1", "dead-criteria 無し", ["no radius-server dead-criteria"]),
    ("D2", "time 5 tries 1", ["radius-server dead-criteria time 5 tries 1"]),
    ("D3", "time 5 tries 2", ["radius-server dead-criteria time 5 tries 2"]),
]


def main():
    h = yaml.safe_load((GEN / "mgmt_map.yml").read_text())
    s1, s2 = Server(h["SRV01"]), Server(h["SRV02"])
    r2 = Router(h["RT02"])
    say(f"# BL-101 P2 追試2 — dead-criteria と deadtime ({time.strftime('%Y-%m-%d %H:%M')})")
    say()
    say("片系断(SRV01 停止)のまま連続 3 回ログイン。`deadtime 1` は共通。")
    say()
    say("| dead-criteria | 1回目 | 2回目 | 3回目 | 1回目の後の show aaa servers |")
    say("|---|---|---|---|---|")
    try:
        for _tag, label, cfg in CASES:
            s1.start(); s2.start(); time.sleep(3)
            r2.conf([f"aaa group server radius {GRP}", "deadtime 1", "exit"] + cfg)
            login(s1)                       # UP へ戻す(前ケースの DEAD を流す)
            s1.stop()
            ok1, d1 = login(s1)
            st = state(r2)
            ok2, d2 = login(s1)
            ok3, d3 = login(s1)
            s1.start()
            say(f"| {label} | {'✅' if ok1 else '❌'}{d1:.1f}s | "
                f"{'✅' if ok2 else '❌'}{d2:.1f}s | {'✅' if ok3 else '❌'}{d3:.1f}s | "
                f"`{st}` |")
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
