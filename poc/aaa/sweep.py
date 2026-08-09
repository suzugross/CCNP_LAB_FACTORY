#!/usr/bin/env python3
"""BL-101 P0 PoC: IOS AAA(RADIUS) のエッジ挙動スイープ。

_POC-AAA (SRV01/SRV02 ── RT01 ── RT02) に SSH し、主に RT02 の AAA を組み替えながら
「test aaa の応答」「実ログインの可否と priv」「サーバ側ログ」を観測する。
各シナリオは 基線 → delta 適用 → 観測 → revert。

★安全設計(締め出し対策):
  - 制御セッションは**張りっぱなし**にして、その中で delta 適用と revert を行う。
    IOS は AAA 設定変更で確立済みセッションを切らないので、認証を壊しても操作を続けられる。
  - **ログイン挙動は別コネクション**(host からの新規 SSH)で測る。失敗しても制御系に影響しない。
  - delta は原則 RT02 のみ。RT01 は健全なまま残す(比較対照＋最後の逃げ道)。

使い方: sweep.py [ケース名...]   (無指定=全部)
        sweep.py --list
"""
import re
import sys
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-raw.md"

ADMIN, ADMIN_PW = "SUZUKI", "CCNP"          # 自動化(local + RADIUS 台帳の両方に居る)
RAD_USER, RAD_PW = "noc-taro", "Noc-1234"   # RADIUS のみ (priv-lvl=15)
RAD_LOW, RAD_LOW_PW = "helpdesk", "Desk-1234"  # RADIUS のみ (priv-lvl=1)
LOCAL_ONLY, LOCAL_ONLY_PW = "emg-admin", "Emg-1234"  # ★local のみ (RADIUS 台帳に無い)


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


# ---------------------------------------------------------------- 低レベル

class Router:
    def __init__(self, ip):
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=40)
        self.sh = self.cli.invoke_shell(width=511)
        self._drain(2.0)
        self.send("terminal length 0")

    def _drain(self, sec):
        t0, buf = time.time(), ""
        while time.time() - t0 < sec:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
            else:
                time.sleep(0.1)
        return buf

    def _expect(self, timeout=120):
        """★プロンプト(#)が返るまで待つ。固定 sleep だと遅い応答(test aaa の
        タイムアウト系)を取りこぼし、次コマンドの出力とバッファが混線する
        (2026-08-08 に実測値が全滅した原因)。"""
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

    def send(self, cmd, wait=None):
        self.sh.send(cmd + "\n")
        return self._expect()

    def show(self, cmd, wait=None):
        out = self.send(cmd)
        return "\n".join(out.splitlines()[1:-1]).strip()

    def conf(self, lines, wait=1.2):
        self.send("configure terminal", wait)
        for ln in lines:
            self.send(ln, wait)
        self.send("end", wait)

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
                         allow_agent=False, timeout=40)

    def run(self, cmd, timeout=90):
        _, o, e = self.cli.exec_command(cmd, timeout=timeout)
        return (o.read().decode() + e.read().decode()).strip()

    def mark(self):
        """ログの現在行数を記録(この後の差分だけ読むため)"""
        n = self.run("sudo -n wc -l < /var/log/freeradius/radius.log 2>/dev/null || echo 0")
        try:
            return int(n.strip().split()[0])
        except Exception:
            return 0

    def since(self, n, maxlines=8):
        return self.run(f"sudo -n tail -n +{n + 1} /var/log/freeradius/radius.log "
                        f"2>/dev/null | tail -{maxlines}")

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


# ---------------------------------------------------------------- 観測プリミティブ

def ensure_up(rt, limit=340):
    """★ケース間の独立性: 前ケースで DEAD になったサーバが残ると次ケースの結果が壊れる。
    deadtime は実測 300s ちょうどで自然回復する(E13)。全サーバ UP まで待つ。"""
    t0 = time.time()
    while time.time() - t0 < limit:
        out = rt.show("show aaa servers | include State:", wait=4)
        if "DEAD" not in out:
            return f"{time.time() - t0:.0f}s"
        time.sleep(15)
    return f"TIMEOUT({limit}s)"


def test_aaa(rt, user, pw, group="RADGRP"):
    """test aaa の応答文言と所要秒数。★紙面 trace 形の 3 値はここから採る。"""
    t0 = time.time()
    out = rt.show(f"test aaa group {group} {user} {pw} legacy")
    el = time.time() - t0
    body = "\n".join(l for l in out.splitlines()
                     if l.strip() and not l.strip().startswith("test aaa")
                     and not re.match(r"^\S+#\s*$", l.strip()))
    return body.strip(), el


def login(ip, user, pw, timeout=45):
    """別コネクションでの実ログイン。戻り= (結果, priv or 詳細)"""
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    t0 = time.time()
    try:
        c.connect(ip, username=user, password=pw, look_for_keys=False,
                  allow_agent=False, timeout=timeout, auth_timeout=timeout,
                  banner_timeout=timeout)
    except paramiko.AuthenticationException:
        return "AUTH_FAIL", f"{time.time() - t0:.1f}s"
    except Exception as ex:
        return "ERROR", f"{type(ex).__name__}: {ex} ({time.time() - t0:.1f}s)"
    el = time.time() - t0
    try:
        sh = c.invoke_shell(width=511)
        time.sleep(2.0)
        buf = sh.recv(65535).decode("utf-8", "replace")
        sh.send("show privilege\n")
        time.sleep(2.0)
        buf += sh.recv(65535).decode("utf-8", "replace")
        m = re.search(r"privilege level is (\d+)", buf)
        priv = m.group(1) if m else "?"
        # exec が拒否られた場合の痕跡も拾う
        denied = "Authorization failed" in buf or "not authorized" in buf.lower()
        return ("EXEC_DENIED" if denied else "OK"), f"priv={priv} ({el:.1f}s)"
    except Exception as ex:
        return "SHELL_FAIL", f"{type(ex).__name__}: {ex}"
    finally:
        c.close()


# ---------------------------------------------------------------- ケース定義

def case_B0(ctx):
    """基線: 全て健全。以降の比較基準。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    rows = []
    for u, p, tag in [(RAD_USER, RAD_PW, "RADIUS priv15"),
                      (RAD_LOW, RAD_LOW_PW, "RADIUS priv1"),
                      (LOCAL_ONLY, LOCAL_ONLY_PW, "local のみ")]:
        body, el = test_aaa(rt, u, p)
        r, d = login(ip, u, p)
        rows.append((f"{u} ({tag})", body, f"{el:.1f}s", f"{r} {d}"))
    return {"table": rows,
            "aaa_servers": rt.show("show aaa servers | include host|State:", wait=5)}


def case_E1(ctx):
    """user_not_registered: local には居るが RADIUS 台帳に無いユーザ。
    ★核心= Reject は local へフォールバックしない。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    m1, m2 = ctx["s1"].mark(), ctx["s2"].mark()
    body, el = test_aaa(rt, LOCAL_ONLY, LOCAL_ONLY_PW)
    r, d = login(ip, LOCAL_ONLY, LOCAL_ONLY_PW)
    return {"table": [(f"{LOCAL_ONLY} (local のみ・サーバ生存)", body, f"{el:.1f}s", f"{r} {d}")],
            "srv01_log": ctx["s1"].since(m1), "srv02_log": ctx["s2"].since(m2)}


def case_E2(ctx):
    """key_mismatch: 共有キー不一致 → サーバは無言破棄 → timeout。
    ★E1 と違い local へ落ちる(= ERROR 扱い)はず。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    m1, m2 = ctx["s1"].mark(), ctx["s2"].mark()
    rt.conf(["radius server RAD1", " key WrongKey-9999", "exit",
             "radius server RAD2", " key WrongKey-9999", "exit"])
    time.sleep(2)
    body, el = test_aaa(rt, RAD_USER, RAD_PW)
    r1, d1 = login(ip, LOCAL_ONLY, LOCAL_ONLY_PW)     # local へ落ちるか
    r2, d2 = login(ip, RAD_USER, RAD_PW)              # RADIUS のみのユーザは?
    logs = (ctx["s1"].since(m1), ctx["s2"].since(m2))
    rt.conf(["radius server RAD1", " key Poc-Rad-1111", "exit",
             "radius server RAD2", " key Poc-Rad-1111", "exit"])
    return {"table": [(f"test aaa {RAD_USER}", body, f"{el:.1f}s", ""),
                      (f"login {LOCAL_ONLY} (local のみ)", "", "", f"{r1} {d1}"),
                      (f"login {RAD_USER} (RADIUS のみ)", "", "", f"{r2} {d2}")],
            "srv01_log": logs[0], "srv02_log": logs[1]}


def case_E3(ctx):
    """src_iface_missing: source-interface を外す → 送信元が egress IF になり
    clients 未登録 → 無言破棄。★E2 と機器側で区別できるかが本題。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    m1, m2 = ctx["s1"].mark(), ctx["s2"].mark()
    rt.conf(["no ip radius source-interface Loopback0"])
    time.sleep(2)
    body, el = test_aaa(rt, RAD_USER, RAD_PW)
    r1, d1 = login(ip, LOCAL_ONLY, LOCAL_ONLY_PW)
    logs = (ctx["s1"].since(m1), ctx["s2"].since(m2))
    srv = rt.show("show aaa servers | include host|State:", wait=5)
    rt.conf(["ip radius source-interface Loopback0"])
    return {"table": [(f"test aaa {RAD_USER}", body, f"{el:.1f}s", ""),
                      (f"login {LOCAL_ONLY} (local のみ)", "", "", f"{r1} {d1}")],
            "aaa_servers": srv, "srv01_log": logs[0], "srv02_log": logs[1]}


def case_E4(ctx):
    """no_authz_exec: 認可を外す → 認証は通るが priv は?"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    rt.conf(["no aaa authorization exec default group RADGRP local"])
    time.sleep(1)
    rows = []
    for u, p in [(RAD_USER, RAD_PW), (RAD_LOW, RAD_LOW_PW)]:
        r, d = login(ip, u, p)
        rows.append((f"login {u}", "", "", f"{r} {d}"))
    rt.conf(["aaa authorization exec default group RADGRP local"])
    return {"table": rows}


def case_E5(ctx):
    """authz_no_fallback: 認可に local を持たせず全断 → exec はどうなるか。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    rt.conf(["aaa authorization exec default group RADGRP"])
    ctx["s1"].stop(); ctx["s2"].stop()
    time.sleep(3)
    rows = []
    for u, p, tag in [(LOCAL_ONLY, LOCAL_ONLY_PW, "local のみ"),
                      (ADMIN, ADMIN_PW, "local + RADIUS")]:
        r, d = login(ip, u, p)
        rows.append((f"login {u} ({tag})", "", "", f"{r} {d}"))
    ctx["s1"].start(); ctx["s2"].start()
    time.sleep(3)
    rt.conf(["aaa authorization exec default group RADGRP local"])
    return {"table": rows}


def case_E6(ctx):
    """list_not_applied: 名前付きリストを作って VTY に適用し忘れ → default が効く。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    rt.conf(["aaa authentication login default local",
             "aaa authentication login MYLIST group RADGRP local"])
    time.sleep(1)
    rows = []
    for u, p, tag in [(RAD_USER, RAD_PW, "RADIUS のみ"),
                      (LOCAL_ONLY, LOCAL_ONLY_PW, "local のみ")]:
        r, d = login(ip, u, p)
        rows.append((f"login {u} ({tag})", "", "", f"{r} {d}"))
    ln = rt.show("show running-config | section line vty", wait=4)
    rt.conf(["no aaa authentication login MYLIST",
             "aaa authentication login default group RADGRP local"])
    return {"table": rows, "line_vty": ln}


def case_E8(ctx):
    """片系断: SRV01 停止 → RAD2(非標準ポート) で継続するか・遅延は。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    ctx["s1"].stop()
    time.sleep(3)
    body, el = test_aaa(rt, RAD_USER, RAD_PW)
    r, d = login(ip, RAD_USER, RAD_PW)
    srv = rt.show("show aaa servers | include host|State:", wait=5)
    body2, el2 = test_aaa(rt, RAD_USER, RAD_PW)     # deadtime 後の2回目
    ctx["s1"].start()
    time.sleep(3)
    return {"table": [("1回目 test aaa", body, f"{el:.1f}s", ""),
                      (f"login {RAD_USER}", "", "", f"{r} {d}"),
                      ("2回目 test aaa (deadtime 後)", body2, f"{el2:.1f}s", "")],
            "aaa_servers": srv}


def case_E9(ctx):
    """全断: local フォールバックの成立と遅延。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    ctx["s1"].stop(); ctx["s2"].stop()
    time.sleep(3)
    body, el = test_aaa(rt, RAD_USER, RAD_PW)
    rows = [("test aaa (全断)", body, f"{el:.1f}s", "")]
    for u, p, tag in [(LOCAL_ONLY, LOCAL_ONLY_PW, "local のみ"),
                      (RAD_USER, RAD_PW, "RADIUS のみ")]:
        r, d = login(ip, u, p)
        rows.append((f"login {u} ({tag})", "", "", f"{r} {d}"))
    ctx["s1"].start(); ctx["s2"].start()
    time.sleep(3)
    return {"table": rows}


def case_E10(ctx):
    """port_mismatch: RAD2 の auth-port を標準に取り違え + SRV01 停止で RAD2 を強制。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    m2 = ctx["s2"].mark()
    rt.conf(["radius server RAD2", " address ipv4 10.99.2.2 auth-port 1812 acct-port 1813", "exit"])
    ctx["s1"].stop()
    time.sleep(3)
    body, el = test_aaa(rt, RAD_USER, RAD_PW)
    r, d = login(ip, LOCAL_ONLY, LOCAL_ONLY_PW)
    srv = rt.show("show aaa servers | include host|State:", wait=5)
    log = ctx["s2"].since(m2)
    rt.conf(["radius server RAD2", " address ipv4 10.99.2.2 auth-port 1912 acct-port 1913", "exit"])
    ctx["s1"].start()
    time.sleep(3)
    return {"table": [("test aaa (RAD2 ポート誤り・RAD1 停止)", body, f"{el:.1f}s", ""),
                      (f"login {LOCAL_ONLY}", "", "", f"{r} {d}")],
            "aaa_servers": srv, "srv02_log": log}


def case_E11(ctx):
    """priv-lvl AVPair: 15 と 1 の授受(認可あり)。"""
    ip = ctx["ip2"]
    rows = []
    for u, p, tag in [(RAD_USER, RAD_PW, "shell:priv-lvl=15"),
                      (RAD_LOW, RAD_LOW_PW, "shell:priv-lvl=1")]:
        r, d = login(ip, u, p)
        rows.append((f"login {u} ({tag})", "", "", f"{r} {d}"))
    return {"table": rows}


def case_E12(ctx):
    """Reject 時の挙動: 誤パスワード。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    m1 = ctx["s1"].mark()
    body, el = test_aaa(rt, RAD_USER, "WrongPassword")
    r, d = login(ip, RAD_USER, "WrongPassword")
    return {"table": [("test aaa (誤パスワード)", body, f"{el:.1f}s", ""),
                      (f"login {RAD_USER} (誤パスワード)", "", "", f"{r} {d}")],
            "srv01_log": ctx["s1"].since(m1)}


def case_E3B(ctx):
    """E3 の対照: RT01(サーバ直結)で source-interface を外すと送信元は 10.99.1.1。
    直結でも clients 未登録なら同じく無言破棄になるかを確認。"""
    rt, ip = ctx["rt1"], ctx["ip1"]
    m1 = ctx["s1"].mark()
    rt.conf(["no ip radius source-interface Loopback0"])
    time.sleep(2)
    body, el = test_aaa(rt, RAD_USER, RAD_PW)
    log = ctx["s1"].since(m1)
    rt.conf(["ip radius source-interface Loopback0"])
    return {"table": [("RT01 test aaa (source-interface 無し)", body, f"{el:.1f}s", "")],
            "srv01_log": log}


def login_enable(ip, user, pw, enpw, timeout=45):
    """priv 1 でログイン → enable 昇格を試す。戻り= (結果, 詳細)"""
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect(ip, username=user, password=pw, look_for_keys=False,
                  allow_agent=False, timeout=timeout, auth_timeout=timeout,
                  banner_timeout=timeout)
    except paramiko.AuthenticationException:
        return "AUTH_FAIL", ""
    except Exception as ex:
        return "ERROR", f"{type(ex).__name__}"
    try:
        sh = c.invoke_shell(width=511)
        time.sleep(2.0)
        buf = sh.recv(65535).decode("utf-8", "replace")
        sh.send("show privilege\n")
        time.sleep(1.5)
        buf += sh.recv(65535).decode("utf-8", "replace")
        before = re.search(r"privilege level is (\d+)", buf)
        t0 = time.time()
        sh.send("enable\n")
        time.sleep(2.0)
        b2 = sh.recv(65535).decode("utf-8", "replace")
        if "assword" in b2:
            sh.send(enpw + "\n")
            time.sleep(4.0)
            b2 += sh.recv(65535).decode("utf-8", "replace")
        el = time.time() - t0
        sh.send("show privilege\n")
        time.sleep(2.0)
        b2 += sh.recv(65535).decode("utf-8", "replace")
        after = re.findall(r"privilege level is (\d+)", b2)
        msg = [l.strip() for l in b2.splitlines()
               if re.search(r"(Denied|denied|fail|Fail|%)", l)]
        res = "ENABLE_OK" if after and after[-1] == "15" else "ENABLE_FAIL"
        return res, (f"priv {before.group(1) if before else '?'}→"
                     f"{after[-1] if after else '?'} ({el:.1f}s) {' / '.join(msg[:2])}")
    except Exception as ex:
        return "SHELL_FAIL", f"{type(ex).__name__}: {ex}"
    finally:
        c.close()


def case_E15(ctx):
    """★list_undefined: line に**未定義の名前付きリスト**を指定したらどうなるか。
    リポの蓄積(prefix-list 未定義=全許可 / route-map 未定義=全拒否)と繋がる論点。
    ※制御セッションは張ったまま revert する(締め出し対策)。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    rt.conf(["line vty 0 4", " login authentication NOEXIST", "exit"])
    time.sleep(2)
    rows = []
    for u, p, tag in [(ADMIN, ADMIN_PW, "local+RADIUS"),
                      (RAD_USER, RAD_PW, "RADIUS のみ"),
                      (LOCAL_ONLY, LOCAL_ONLY_PW, "local のみ")]:
        r, d = login(ip, u, p)
        rows.append((f"login {u} ({tag})", "", "", f"{r} {d}"))
    cfg = rt.show("show running-config | section line vty")
    rt.conf(["line vty 0 4", " no login authentication NOEXIST", "exit"])
    time.sleep(2)
    r, d = login(ip, RAD_USER, RAD_PW)
    rows.append(("(revert 後) login noc-taro", "", "", f"{r} {d}"))
    return {"table": rows, "line_vty": cfg}


def case_E15B(ctx):
    """authorization 側の未定義リスト参照。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    rt.conf(["line vty 0 4", " authorization exec NOEXIST2", "exit"])
    time.sleep(2)
    rows = []
    for u, p, tag in [(RAD_USER, RAD_PW, "RADIUS のみ"),
                      (ADMIN, ADMIN_PW, "local+RADIUS")]:
        r, d = login(ip, u, p)
        rows.append((f"login {u} ({tag})", "", "", f"{r} {d}"))
    cfg = rt.show("show running-config | section line vty")
    rt.conf(["line vty 0 4", " no authorization exec NOEXIST2", "exit"])
    return {"table": rows, "line_vty": cfg}


def case_E16(ctx):
    """★enable 認証: priv 1 で入った後 enable に上がれるか。
    (a) 既定(enable secret) (b) group RADGRP を噛ませた場合。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    rows = []
    r, d = login_enable(ip, RAD_LOW, RAD_LOW_PW, ADMIN_PW)
    rows.append(("(a) 既定: helpdesk(priv1) → enable secret", "", "", f"{r} {d}"))
    rt.conf(["aaa authentication enable default group RADGRP enable"])
    time.sleep(2)
    r, d = login_enable(ip, RAD_LOW, RAD_LOW_PW, ADMIN_PW)
    rows.append(("(b) enable 認証を RADIUS 経由に: 同上", "", "", f"{r} {d}"))
    m1 = ctx["s1"].mark()
    time.sleep(1)
    log = ctx["s1"].since(m1)
    rt.conf(["no aaa authentication enable default group RADGRP enable"])
    return {"table": rows, "srv01_log": log}


def case_E17(ctx):
    """★accounting: exec の start-stop がサーバに残るか・記録の形。"""
    rt, ip = ctx["rt2"], ctx["ip2"]
    s1 = ctx["s1"]
    before = s1.run("sudo -n ls -1 /var/log/freeradius/radacct/ 2>/dev/null | head -5")
    rt.conf(["aaa accounting exec default start-stop group RADGRP"])
    time.sleep(2)
    r, d = login(ip, RAD_USER, RAD_PW)
    time.sleep(4)
    detail = s1.run("sudo -n find /var/log/freeradius/radacct/ -type f 2>/dev/null | head -3")
    body = s1.run("sudo -n find /var/log/freeradius/radacct/ -type f 2>/dev/null "
                  "| head -1 | xargs -r sudo -n tail -25")
    acct = rt.show("show aaa servers | include Accounting|acct-port|host")
    # commands accounting は RADIUS で受理されるか(TACACS+ 前提の機能)
    cmdacct = rt.send("configure terminal")
    cmdacct += rt.send("aaa accounting commands 15 default start-stop group RADGRP")
    rt.send("end")
    rt.conf(["no aaa accounting commands 15 default start-stop group RADGRP",
             "no aaa accounting exec default start-stop group RADGRP"])
    return {"table": [(f"login {RAD_USER}(accounting 有効)", "", "", f"{r} {d}"),
                      ("radacct 配下(前)", before or "(なし)", "", ""),
                      ("radacct 配下(後)", detail or "(なし)", "", "")],
            "acct_record": body, "aaa_servers": acct,
            "cmd_acct": "\n".join(l for l in cmdacct.splitlines()
                                  if "%" in l or "accounting commands" in l)}


CASES = [
    ("B0", "基線(全て健全)", case_B0),
    ("E1", "user_not_registered — Reject は local へ落ちない", case_E1),
    ("E2", "key_mismatch — 無言破棄→timeout→local へ", case_E2),
    ("E3", "src_iface_missing (RT02/1ホップ)", case_E3),
    ("E3B", "src_iface_missing (RT01/直結) 対照", case_E3B),
    ("E4", "no_authz_exec — priv はどうなるか", case_E4),
    ("E5", "authz_no_fallback × 全断", case_E5),
    ("E6", "list_not_applied — default が効く", case_E6),
    ("E8", "片系断(SRV01 停止)", case_E8),
    ("E9", "全断 — local フォールバック", case_E9),
    ("E10", "port_mismatch (非標準ポート取り違え)", case_E10),
    ("E11", "priv-lvl AVPair 15/1", case_E11),
    ("E12", "Reject(誤パスワード)の挙動", case_E12),
    ("E15", "★list_undefined — 未定義リストを line に指定", case_E15),
    ("E15B", "authorization 側の未定義リスト参照", case_E15B),
    ("E16", "★enable 認証(既定 / RADIUS 経由)", case_E16),
    ("E17", "★accounting exec start-stop", case_E17),
]


def main():
    args = sys.argv[1:]
    if "--list" in args:
        for k, d, _ in CASES:
            print(f"{k:5s} {d}")
        return
    want = [a for a in args if not a.startswith("-")]
    h = hosts()
    ctx = {"ip1": h["RT01"], "ip2": h["RT02"]}
    ctx["rt1"] = Router(h["RT01"])
    ctx["rt2"] = Router(h["RT02"])
    ctx["s1"] = Server(h["SRV01"])
    ctx["s2"] = Server(h["SRV02"])
    out = []
    try:
        for key, desc, fn in CASES:
            if want and key not in want:
                continue
            print(f"--- {key}: {desc}", flush=True)
            t0 = time.time()
            try:
                w1, w2 = ensure_up(ctx["rt1"]), ensure_up(ctx["rt2"])
                print(f"    (前提: 全サーバ UP 待ち RT01={w1} RT02={w2})", flush=True)
                res = fn(ctx)
                res["precond"] = f"全サーバ UP 待ち RT01={w1} RT02={w2}"
            except Exception as ex:
                res = {"error": f"{type(ex).__name__}: {ex}"}
            out.append((key, desc, res, time.time() - t0))
            print(f"    done {time.time() - t0:.0f}s", flush=True)
    finally:
        # ★どのケースで落ちてもサーバは必ず戻す(採点/次ケースの前提)
        try:
            ctx["s1"].start(); ctx["s2"].start()
        except Exception:
            pass
        for k in ("rt1", "rt2", "s1", "s2"):
            try:
                ctx[k].close()
            except Exception:
                pass

    md = ["# BL-101 P0 PoC 生ログ — IOS AAA(RADIUS) エッジ挙動", "",
          "自動生成: poc/aaa/sweep.py。盤面= _POC-AAA。delta は原則 RT02 に適用。", ""]
    for key, desc, res, el in out:
        md.append(f"## {key} — {desc}  ({el:.0f}s)\n")
        if "error" in res:
            md.append(f"**ERROR**: {res['error']}\n")
        for row in res.get("table", []):
            md.append(f"- **{row[0]}**")
            if row[1]:
                md.append(f"  - test aaa: `{row[1].splitlines()[-1] if row[1] else ''}`")
                md.append("    ```\n    " + "\n    ".join(row[1].splitlines()) + "\n    ```")
            if row[2]:
                md.append(f"  - 所要: {row[2]}")
            if row[3]:
                md.append(f"  - login: {row[3]}")
        for k, label in [("aaa_servers", "show aaa servers"),
                         ("line_vty", "line vty"),
                         ("srv01_log", "SRV01 radius.log"),
                         ("srv02_log", "SRV02 radius.log")]:
            if res.get(k):
                md.append(f"\n**{label}**\n```\n{res[k]}\n```")
        md.append("")
    OUT.write_text("\n".join(md))
    print(f"\n書き出し: {OUT}")


if __name__ == "__main__":
    main()
