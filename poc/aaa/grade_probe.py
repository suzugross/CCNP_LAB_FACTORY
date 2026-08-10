#!/usr/bin/env python3
"""BL-101 P2 PoC-2: **ラボ構築問 GEN-AAAGRP の採点機構**を実測する(2026-08-09)。

P0 は「AAA がどう壊れるか」を測った。P2 で要るのはその手前の別の問題=
**3 フェーズ挙動採点(正常 / 片系断 / 全断)を `grade.yml` の枠内で回せるか**。
設計見直しで洗い出した 3 つの未解決点を、推測のまま実装に持ち込まないために測る。

  G1  **SRV → ルータの SSH**。`_grade_attempt.yml` は exec=ios を全件先に回してから
      exec=shell を回すので、「サーバを止めてからルータを見る」順序はチェックの並びでは
      作れない。→ 破壊フェーズは **1 本の shell チェック内で完結**させるほかない。
      その中からルータを観測する唯一の手段が Ubuntu→IOL の ssh。**どのオプションが要るか**。
  G2  **SRV01 → SRV02 の SSH**。全断フェーズは 2 台同時に止める必要がある。
  G3  ★**deadtime の残留**。P0 実測= `deadtime 5` はちょうど 300 秒・
      `clear aaa counters servers all` では解除されない。採点は最大 10 回再試行されるので、
      全断フェーズの直後に次の試行が走ると**サーバを戻してもまだ DEAD 扱い**で
      正常フェーズが落ち、永久に収束しない恐れがある。
      → **サーバ復旧後に RADIUS 認証が再び通るまでの実時間**を deadtime 別に測る。
  G4  破壊フェーズ 1 本の**所要時間**(採点の現実的な待ち時間の見積り)。

使い方: grade_probe.py [G1 G2 G3 G4]   (無指定=全部)
出力  : poc/aaa/results-grade.md
"""
import re
import subprocess
import sys
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-grade.md"

ADMIN, ADMIN_PW = "SUZUKI", "CCNP"
RAD_USER, RAD_PW = "noc-taro", "Noc-1234"            # RADIUS のみ (priv-lvl=15)
LOCAL_ONLY, LOCAL_ONLY_PW = "emg-admin", "Emg-1234"  # local のみ (priv 15)
GRP = "RADGRP"

# ルータのインバンド側アドレス(サーバから見た宛先)。MGMT に依存しない経路で測る=
# 本番の採点も学習網の中で完結させたいため。
INBAND = {"RT01": "10.99.1.1", "RT02": "10.1.12.2"}

LOG = []


def say(s=""):
    print(s, flush=True)
    LOG.append(s)


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


class Router:
    """paramiko で対話シェルを張る(こちら側の制御用。観測対象ではない)。"""

    def __init__(self, ip):
        self.ip = ip
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
        self.ip = ip
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


# --- G1: SRV01 から IOL ルータへ ssh できるか ---------------------------------

SSH_VARIANTS = [
    ("bare", ""),
    ("legacy-hostkey", "-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"),
    ("legacy-kex", "-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa "
                   "-o KexAlgorithms=+diffie-hellman-group14-sha1"),
    ("legacy-all", "-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa "
                   "-o KexAlgorithms=+diffie-hellman-group14-sha1 "
                   "-o Ciphers=+aes128-cbc -o MACs=+hmac-sha1"),
]
SSH_COMMON = ("-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
              "-o ConnectTimeout=30 -o LogLevel=ERROR")


def ssh_cmd(user, pw, host, remote, extra=""):
    return (f"sshpass -p '{pw}' ssh {SSH_COMMON} {extra} "
            f"-o NumberOfPasswordPrompts=1 {user}@{host} '{remote}' 2>&1")


def case_G1(ctx):
    """Ubuntu(SRV01) → IOL(RT01/RT02) の ssh。要るオプションを特定する。"""
    s1 = ctx["s1"]
    say("### G1 — SRV01 → ルータの SSH")
    say()
    ins = s1.run("which sshpass || (sudo -n apt-get install -y -qq sshpass >/dev/null 2>&1; "
                 "which sshpass)")
    say(f"- sshpass: `{ins.strip() or '(導入失敗)'}`")
    if not ins.strip():
        say("- ★sshpass が入らない → 別手段(baked key)へ切り替えが必要")
        return
    say()
    say("| 宛先 | オプション | 結果 |")
    say("|---|---|---|")
    ok_opt = None
    for rt, ip in INBAND.items():
        for name, extra in SSH_VARIANTS:
            t0 = time.time()
            out = s1.run(ssh_cmd(ADMIN, ADMIN_PW, ip, "show privilege", extra), timeout=120)
            dt = time.time() - t0
            first = " / ".join(x.strip() for x in out.splitlines() if x.strip())[:110]
            hit = "Current privilege level" in out
            say(f"| {rt}({ip}) | {name} | {'✅' if hit else '❌'} {dt:.1f}s `{first}` |")
            if hit:
                if ok_opt is None:
                    ok_opt = (name, extra)
                break
    ctx["ssh_opt"] = ok_opt
    say()
    say(f"- **採用オプション**: `{ok_opt[0]}` = `{ok_opt[1] or '(素の ssh で可)'}`"
        if ok_opt else "- ★どのオプションでも通らない")
    say()


# --- G2: SRV01 → SRV02 -------------------------------------------------------

def case_G2(ctx):
    s1, h = ctx["s1"], ctx["hosts"]
    say("### G2 — SRV01 → SRV02 の SSH(全断フェーズで対向を止める)")
    say()
    out = s1.run(ssh_cmd(ADMIN, ADMIN_PW, h["SRV02"], "systemctl is-active freeradius"),
                 timeout=90)
    say(f"- MGMT 経由 `{h['SRV02']}`: `{out.strip()[:120]}`")
    # インバンド側でも到達できるか(学習網だけで完結させたい場合の確認)
    out2 = s1.run(ssh_cmd(ADMIN, ADMIN_PW, "10.99.2.2", "systemctl is-active freeradius"),
                  timeout=90)
    say(f"- インバンド `10.99.2.2`: `{out2.strip()[:120]}`")
    say()


# --- G3: deadtime の残留 -----------------------------------------------------

def rt_login(s1, ip, user, pw, extra):
    """SRV01 から ルータへ実ログインし、(成否, 権限, 秒) を返す。"""
    t0 = time.time()
    out = s1.run(ssh_cmd(user, pw, ip, "show privilege", extra), timeout=180)
    dt = time.time() - t0
    m = re.search(r"privilege level is (\d+)", out)
    return (m is not None, int(m.group(1)) if m else None, dt, out.strip()[:120])


def poll_radius_back(s1, ip, extra, limit=360, step=10):
    """サーバ復旧後、RADIUS 利用者で入れるようになるまでの秒数を測る。"""
    t0 = time.time()
    while time.time() - t0 < limit:
        ok, priv, _dt, _o = rt_login(s1, ip, RAD_USER, RAD_PW, extra)
        if ok:
            return time.time() - t0, priv
        time.sleep(step)
    return None, None


def case_G3(ctx):
    s1, s2 = ctx["s1"], ctx["s2"]
    extra = (ctx.get("ssh_opt") or ("bare", ""))[1]
    ip = INBAND["RT02"]          # 1ホップ先=本番の採点対象に近い位置
    r2 = ctx["r2"]
    say("### G3 — ★全断フェーズのあと RADIUS が使えるようになるまで(deadtime 別)")
    say()
    say("| deadtime | ①正常 | ②片系断(SRV01停止) | ③全断: local | ③全断: RADIUS利用者 "
        "| ④復旧後に RADIUS が戻るまで |")
    say("|---|---|---|---|---|---|")
    for dt_min, label in [(5, "5(P0 基線)"), (1, "1"), (None, "無し")]:
        # deadtime を設定
        if dt_min is None:
            r2.conf([f"aaa group server radius {GRP}", "no deadtime", "exit"])
        else:
            r2.conf([f"aaa group server radius {GRP}", f"deadtime {dt_min}", "exit"])
        s1.start(); s2.start()
        time.sleep(5)
        # 直前の DEAD 残りを流し切る(前ケースの影響を持ち込まない)
        r2.send("clear aaa counters servers all")
        back0, _ = poll_radius_back(s1, ip, extra, limit=360, step=15)
        if back0 is None:
            say(f"| {label} | ★開始時点で RADIUS が戻らず(前ケースの DEAD 残留) | - | - | - | - |")
            continue

        ok1, p1, t1, _ = rt_login(s1, ip, RAD_USER, RAD_PW, extra)
        c1 = f"{'✅' if ok1 else '❌'} priv={p1} {t1:.1f}s"

        s1.stop()
        ok2, p2, t2, _ = rt_login(s1, ip, RAD_USER, RAD_PW, extra)
        c2 = f"{'✅' if ok2 else '❌'} priv={p2} {t2:.1f}s"

        s2.stop()
        ok3, p3, t3, _ = rt_login(s1, ip, LOCAL_ONLY, LOCAL_ONLY_PW, extra)
        c3 = f"{'✅' if ok3 else '❌'} priv={p3} {t3:.1f}s"
        ok4, _p4, t4, o4 = rt_login(s1, ip, RAD_USER, RAD_PW, extra)
        c4 = f"{'❌(想定)' if not ok4 else '✅(想定外)'} {t4:.1f}s `{o4[:40]}`"

        s1.start(); s2.start()
        back, pb = poll_radius_back(s1, ip, extra, limit=400, step=10)
        c5 = (f"**{back:.0f}s** (priv={pb})" if back is not None
              else "★400s 待っても戻らない")
        say(f"| {label} | {c1} | {c2} | {c3} | {c4} | {c5} |")
    # 基線へ戻す
    r2.conf([f"aaa group server radius {GRP}", "deadtime 5", "exit"])
    s1.start(); s2.start()
    say()


# --- G4: 破壊フェーズ 1 本の所要 ---------------------------------------------

def case_G4(ctx):
    s1, s2 = ctx["s1"], ctx["s2"]
    extra = (ctx.get("ssh_opt") or ("bare", ""))[1]
    ip = INBAND["RT02"]
    say("### G4 — 破壊フェーズを 1 本の shell チェックにまとめた場合の所要")
    say()
    t0 = time.time()
    s1.stop()
    a = rt_login(s1, ip, RAD_USER, RAD_PW, extra)
    s2.stop()
    b = rt_login(s1, ip, LOCAL_ONLY, LOCAL_ONLY_PW, extra)
    s1.start(); s2.start()
    total = time.time() - t0
    say(f"- 片系断ログイン {a[2]:.1f}s / 全断ローカルログイン {b[2]:.1f}s / "
        f"停止・起動込みの合計 **{total:.0f}s**")
    say()


CASES = [("G1", case_G1), ("G2", case_G2), ("G3", case_G3), ("G4", case_G4)]


def main():
    want = [a.upper() for a in sys.argv[1:]] or [c[0] for c in CASES]
    h = hosts()
    ctx = {"hosts": h}
    ctx["s1"] = Server(h["SRV01"])
    ctx["s2"] = Server(h["SRV02"])
    ctx["r2"] = Router(h["RT02"])
    say(f"# BL-101 P2 PoC-2 — 採点機構の実測 ({time.strftime('%Y-%m-%d %H:%M')})")
    say()
    try:
        for name, fn in CASES:
            if name in want:
                fn(ctx)
    finally:
        try:
            ctx["s1"].start(); ctx["s2"].start()
        except Exception:
            pass
        for k in ("s1", "s2", "r2"):
            try:
                ctx[k].close()
            except Exception:
                pass
        OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
        print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
