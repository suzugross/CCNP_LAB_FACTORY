#!/usr/bin/env python3
"""BL-101 P2 PoC-2 追試: **deadtime を「挙動」で採点できるか**(2026-08-09)。

G3 で「復旧後は即座に戻る」ことが分かり、採点の収束リスクは消えた。
残るのは要件側の問題= `deadtime` を **config の正規表現ではなく挙動で**採点したい。

仮説: 片系断のとき、**1 回目のログインは全タイムアウトを食う**が、
      そこでそのサーバが dead 記録されるので **2 回目は即座に通る**。
      `deadtime` が 0(無効)なら 2 回目も 1 回目と同じだけ待つはず。
→ これが成り立てば「2 回目が速い」= deadtime が効いている の証明になり、
   要件「応答しなくなったサーバは一定時間、問い合わせ先から外すこと」を
   挙動で採点できる。

使い方: deadtime_probe.py
出力  : poc/aaa/results-deadtime.md
"""
import re
import sys
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-deadtime.md"

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
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=60)
        self.sh = self.cli.invoke_shell(width=511)
        self._expect()
        self.send("terminal length 0")

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


def login(s1, user, pw):
    t0 = time.time()
    out = s1.run(f"sshpass -p '{pw}' ssh {SSH_COMMON} {user}@{RT02_INBAND} "
                 f"'show privilege' 2>&1", timeout=180)
    dt = time.time() - t0
    m = re.search(r"privilege level is (\d+)", out)
    return (m is not None, dt)


def main():
    h = yaml.safe_load((GEN / "mgmt_map.yml").read_text())
    s1, s2 = Server(h["SRV01"]), Server(h["SRV02"])
    r2 = None
    say(f"# BL-101 P2 追試 — deadtime の挙動採点 ({time.strftime('%Y-%m-%d %H:%M')})")
    say()
    say("片系断(SRV01 停止)のまま**連続 3 回**ログインし、所要秒の推移を見る。")
    say()
    say("| deadtime | 1回目 | 2回目 | 3回目 | 判定 |")
    say("|---|---|---|---|---|")
    try:
        for dt_cfg, label in [("deadtime 1", "1"), ("no deadtime", "無し(既定0)"),
                              ("deadtime 5", "5")]:
            s1.start(); s2.start(); time.sleep(3)
            # ★制御セッションはケースごとに張り直す(前回の追試で、破壊フェーズを挟むと
            #   長寿命の vty セッションが落ちて "Socket is closed" になった)
            if r2 is not None:
                r2.close()
            r2 = Router(h["RT02"])
            r2.conf([f"aaa group server radius {GRP}", dt_cfg, "exit"])
            r2.send("clear aaa counters servers all")
            ok0, _ = login(s1, RAD_USER, RAD_PW)          # 復帰確認(dead 記録を流す)
            s1.stop()
            ts = []
            for _ in range(3):
                ok, t = login(s1, RAD_USER, RAD_PW)
                ts.append(f"{'✅' if ok else '❌'}{t:.1f}s")
            s1.start()
            verdict = "★2回目以降が速い= dead 記録が効いている" \
                if float(ts[1][1:-1]) < float(ts[0][1:-1]) / 2 else "差が出ない"
            say(f"| {label} | {ts[0]} | {ts[1]} | {ts[2]} | {verdict} |")
        if r2 is not None:
            r2.conf([f"aaa group server radius {GRP}", "deadtime 5", "exit"])
    finally:
        try:
            s1.start(); s2.start()
        except Exception:
            pass
        for c in (s1, s2, r2):
            if c is None:
                continue
            try:
                c.close()
            except Exception:
                pass
        say()
        OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
        print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
