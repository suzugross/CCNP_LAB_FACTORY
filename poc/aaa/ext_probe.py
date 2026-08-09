#!/usr/bin/env python3
"""BL-101 P0 追試3: **紙面拡張候補の裏取り**(2026-08-08)。

拡張検討で「そう動くはず」と推測した 3 点を、推測のまま作問に載せないために実測する。

  X1/X2 `if-authenticated` — 認可の 3 番目の方式。認証さえ通っていれば exec を許すが、
        **属性(priv-lvl)は降ってこない**のではないか? → 権限レベルを実測する。
  X4    **ACL による RADIUS 遮断** — 経路上/自機の ACL で udp 1812 を落とすと、
        サーバ停止・ポート違いと**機器側の症状が同一**になるのか。ACL カウンタが
        「要求は出ていったが落とされた」の唯一の読み取り口になるのかを見る。
  X5/X6 **`aaa authorization console`** — `line con 0` に `authorization exec` を
        当てても、グローバルの `aaa authorization console` が無ければ効かない
        (= コンソールの認可は既定で無効)という定説の確認。★現行モデルは
        コンソールにも認可を適用しているため、真なら紙面の観測表に誤りが混じる。

使い方: ext_probe.py [X1 X2 X4 X4b X5 X6]   (無指定=全部)
"""
import os
import re
import sys
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-ext.md"

ADMIN, ADMIN_PW = "SUZUKI", "CCNP"
RAD_USER, RAD_PW = "noc-taro", "Noc-1234"          # RADIUS のみ priv-lvl=15
RAD_LOW, RAD_LOW_PW = "helpdesk", "Desk-1234"      # RADIUS のみ priv-lvl=1
LOCAL_ONLY, LOCAL_ONLY_PW = "emg-admin", "Emg-1234"  # local のみ(priv 15)
GRP = "RADGRP"


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


class Router:
    def __init__(self, ip):
        self.ip = ip
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=40)
        self.sh = self.cli.invoke_shell(width=511)
        self._expect()
        self.send("terminal length 0")
        self.send("terminal monitor")    # ★他セッションのログインで出る debug をここで観る

    def drain(self, sec):
        """プロンプトを待たずに、指定秒だけ届いたものを集める(debug 採取用)。"""
        t0, buf = time.time(), ""
        while time.time() - t0 < sec:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
            else:
                time.sleep(0.1)
        return buf

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

    def send(self, cmd):
        self.sh.send(cmd + "\n")
        return self._expect()

    def conf(self, lines):
        self.send("configure terminal")
        for ln in lines:
            self.send(ln)
        self.send("end")

    def show(self, cmd):
        out = self.send(cmd)
        return "\n".join(out.splitlines()[1:-1]).strip()

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

    def run(self, cmd):
        _, o, e = self.cli.exec_command(cmd, timeout=90)
        return (o.read().decode() + e.read().decode()).strip()

    def close(self):
        try:
            self.cli.close()
        except Exception:
            pass


def login(ip, user, pw, timeout=60):
    """実ログイン。戻り= (結果, 詳細)"""
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
        return "ERROR", f"{type(ex).__name__} ({time.time() - t0:.1f}s)"
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
        denied = "Authorization failed" in buf or "not authorized" in buf.lower()
        return ("EXEC_DENIED" if denied else "OK"), f"priv={priv} ({el:.1f}s)"
    except Exception as ex:
        return "SHELL_FAIL", f"{type(ex).__name__}"
    finally:
        c.close()


def test_aaa(rt, user, pw):
    t0 = time.time()
    out = rt.send(f"test aaa group {GRP} {user} {pw} legacy")
    el = time.time() - t0
    body = "\n".join(l for l in out.splitlines()
                     if l.strip() and not l.strip().startswith("test aaa")
                     and not re.match(r"^\S+#\s*$", l.strip()))
    return body.strip(), el


def ensure_up(rt, limit=340):
    t0 = time.time()
    while time.time() - t0 < limit:
        if "DEAD" not in rt.show("show aaa servers | include State:"):
            return
        time.sleep(15)


# ---------------------------------------------------------------- ケース

def case_X1(ctx):
    """if-authenticated: サーバ健全。属性は降ってくるのか。"""
    rt, ip = ctx["rt"], ctx["ip"]
    rt.conf([f"aaa authorization exec default group {GRP} if-authenticated"])
    rows = []
    for u, p, tag in [(RAD_USER, RAD_PW, "RADIUS priv-lvl=15"),
                      (RAD_LOW, RAD_LOW_PW, "RADIUS priv-lvl=1")]:
        r, det = login(ip, u, p)
        rows.append((f"{u} ({tag})", "サーバ健全", f"{r} {det}"))
    rt.conf([f"aaa authorization exec default group {GRP} local"])
    return {"table": rows}


def case_X2(ctx):
    """★if-authenticated: サーバ全断。認証は local へ落ち、認可は if-authenticated。
    このとき権限レベルは何になるのか(= local の username privilege が効くのか)。"""
    rt, ip, svc = ctx["rt"], ctx["ip"], ctx["svc"]
    rt.conf([f"aaa authorization exec default group {GRP} if-authenticated"])
    svc("stop")
    rows = []
    r, det = login(ip, LOCAL_ONLY, LOCAL_ONLY_PW)
    rows.append((f"{LOCAL_ONLY} (local priv 15)", "サーバ全断", f"{r} {det}"))
    r, det = login(ip, ADMIN, ADMIN_PW)
    rows.append((f"{ADMIN} (local priv 15)", "サーバ全断", f"{r} {det}"))
    svc("start")
    rt.conf([f"aaa authorization exec default group {GRP} local"])
    return {"table": rows}


def case_X2b(ctx):
    """対照: 認可が `group local` のときの全断(= 既知 E9 の再確認)。"""
    rt, ip, svc = ctx["rt"], ctx["ip"], ctx["svc"]
    svc("stop")
    r, det = login(ip, LOCAL_ONLY, LOCAL_ONLY_PW)
    svc("start")
    return {"table": [(f"{LOCAL_ONLY} (local priv 15)", "サーバ全断・認可= group local",
                       f"{r} {det}")]}


ACL_OUT = ["ip access-list extended BLOCK-RAD",
           " deny   udp any any eq 1812",
           " deny   udp any any eq 1912",
           " permit ip any any",
           "exit",
           "interface Ethernet0/0",
           " ip access-group BLOCK-RAD out",
           "exit"]
ACL_OUT_UNDO = ["interface Ethernet0/0", " no ip access-group BLOCK-RAD out",
                "exit", "no ip access-list extended BLOCK-RAD"]

ACL_IN = ["ip access-list extended BLOCK-RAD-IN",
          " deny   udp any eq 1812 any",
          " deny   udp any eq 1912 any",
          " permit ip any any",
          "exit",
          "interface Ethernet0/0",
          " ip access-group BLOCK-RAD-IN in",
          "exit"]
ACL_IN_UNDO = ["interface Ethernet0/0", " no ip access-group BLOCK-RAD-IN in",
               "exit", "no ip access-list extended BLOCK-RAD-IN"]


def case_X4(ctx):
    """★ACL で要求を出さない(outbound で落とす)。症状はサーバ停止と同じか。"""
    rt, ip = ctx["rt"], ctx["ip"]
    rt.conf(ACL_OUT)
    body, el = test_aaa(rt, RAD_USER, RAD_PW)
    r, det = login(ip, LOCAL_ONLY, LOCAL_ONLY_PW)
    acl = rt.show("show ip access-lists BLOCK-RAD")
    srvs = rt.show("show aaa servers | include host|State:")
    rt.conf(ACL_OUT_UNDO)
    return {"table": [("test aaa", body.replace("\n", " / "), f"{el:.1f}s"),
                      (f"{LOCAL_ONLY} 実ログイン", f"{r} {det}", "")],
            "acl": acl, "aaa_servers": srvs}


def case_X4b(ctx):
    """★ACL で応答だけを落とす(inbound)。要求は届いている = サーバ側は受理済み。"""
    rt, ip = ctx["rt"], ctx["ip"]
    rt.conf(ACL_IN)
    body, el = test_aaa(rt, RAD_USER, RAD_PW)
    acl = rt.show("show ip access-lists BLOCK-RAD-IN")
    rt.conf(ACL_IN_UNDO)
    return {"table": [("test aaa", body.replace("\n", " / "), f"{el:.1f}s")],
            "acl": acl}


# ---- コンソール認可(pyATS 経由) -------------------------------------------

def _console(ctx, user, pw):
    from console_probe import console_login
    return console_login(ctx["testbed"], "RT02", user, pw)


def case_X5(ctx):
    """★`aaa authorization console` **無し**で `line con 0` に認可を当てる。

    認可リスト CON-AZ= `group RADGRP` のみ(フォールバック無し)＋サーバ全断。
    vty ならこれは EXEC 拒否になる(E5)。コンソールでも拒否されるなら
    「コンソールにも認可が効いている」、入れるなら「効いていない」。
    """
    rt, svc = ctx["rt"], ctx["svc"]
    rt.conf(["aaa authentication login CON-AU local",
             f"aaa authorization exec CON-AZ group {GRP}",
             "line con 0", " login authentication CON-AU",
             " authorization exec CON-AZ", "exit"])
    svc("stop")
    res, det = _console(ctx, LOCAL_ONLY, LOCAL_ONLY_PW)
    svc("start")
    return {"table": [("console: 認可= group のみ・全断・`aaa authorization console` **無し**",
                       f"{res} {det}", "")]}


def case_X6(ctx):
    """★同じ状態に `aaa authorization console` を足す。ここで拒否に変われば定説どおり。"""
    rt, svc = ctx["rt"], ctx["svc"]
    rt.conf(["aaa authorization console"])
    svc("stop")
    res, det = _console(ctx, LOCAL_ONLY, LOCAL_ONLY_PW)
    svc("start")
    rt.conf(["no aaa authorization console",
             "line con 0", " no authorization exec CON-AZ",
             " no login authentication CON-AU", "exit",
             "no aaa authorization exec CON-AZ",
             "no aaa authentication login CON-AU"])
    return {"table": [("console: 同じ状態＋`aaa authorization console` **有り**",
                       f"{res} {det}", "")]}


# ---- ★方式リスト層の debug(X7/X8) -----------------------------------------
# 既存の採取は `test aaa group` で撃っており、**方式リストを通らずグループへ直接
# 問い合わせる**ため `AAA/AUTHEN/START ... Method=` の行が1行も出ていなかった
# (results-debug.md に AAA/AUTHEN の出現 0 件)。ここでは**実ログイン**と**実 enable**を
# debug 下で行い、メソッドの遍歴(Method= / status = PASS|FAIL|ERROR)を採る。

AUTHEN_DEBUGS = ["debug aaa authentication", "debug aaa authorization"]
KEEP = re.compile(r"(AAA/|RADIUS[:(]|TAC\+:|% Auth|% Error|% Access)")


def _clean(buf):
    out = []
    for ln in buf.splitlines():
        ln = ln.rstrip()
        if not ln or not KEEP.search(ln):
            continue
        if "undebug" in ln or "All possible debugging" in ln:
            continue
        out.append(ln)
    return "\n".join(out)


def capture_during(rt, fn, extra=10, debugs=None):
    """debug を張った状態で fn() を実行し、その間に出た行を集める。"""
    for dbg in (debugs or AUTHEN_DEBUGS):
        rt.send(dbg)
    rt.drain(1)
    res = fn()
    buf = rt.drain(extra)
    rt.send("undebug all")
    rt.drain(1)
    return res, _clean(buf)


def enable_via_ssh(ip, user, pw, en_pw, timeout=60):
    """priv 1 で入って `enable` を打つ。戻り= (結果, 詳細)"""
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect(ip, username=user, password=pw, look_for_keys=False,
                  allow_agent=False, timeout=timeout, auth_timeout=timeout,
                  banner_timeout=timeout)
    except Exception as ex:
        return "LOGIN_FAIL", type(ex).__name__
    try:
        sh = c.invoke_shell(width=511)
        time.sleep(2.0)
        sh.recv(65535)
        sh.send("enable\n")
        time.sleep(2.0)
        buf = sh.recv(65535).decode("utf-8", "replace")
        if "assword" in buf:
            sh.send(en_pw + "\n")
            time.sleep(3.0)
            buf += sh.recv(65535).decode("utf-8", "replace")
        sh.send("show privilege\n")
        time.sleep(2.5)
        buf += sh.recv(65535).decode("utf-8", "replace")
        m = re.search(r"privilege level is (\d+)", buf)
        priv = m.group(1) if m else "?"
        bad = ("% Error in authentication" in buf or "Access denied" in buf
               or "% Bad" in buf)
        st = "ENABLE_FAIL" if (bad or priv in ("?", "1")) else "OK"
        return st, f"priv={priv}"
    except Exception as ex:
        return "SHELL_FAIL", type(ex).__name__
    finally:
        c.close()


def case_X7(ctx):
    """★実ログイン時の方式リスト層 debug。`Method=` の遍歴と status を採る。

    ここが「Reject は後段へ落ちない / 無応答のときだけ落ちる」が
    **debug の字面として現れる**層(紙面 authread 形の素材)。
    """
    rt, ip, svc = ctx["rt"], ctx["ip"], ctx["svc"]
    caps = []

    def run(tag, user, pw):
        res, buf = capture_during(rt, lambda: login(ip, user, pw), extra=12)
        caps.append((tag, f"{res[0]} {res[1]}", buf))

    run("X7a 健全 / RADIUS 台帳の利用者", RAD_USER, RAD_PW)
    run("X7b ★健全 / local のみの利用者(サーバは Reject を返す)",
        LOCAL_ONLY, LOCAL_ONLY_PW)
    svc("stop")
    run("X7c ★全断 / local のみの利用者", LOCAL_ONLY, LOCAL_ONLY_PW)
    run("X7d 全断 / RADIUS のみの利用者", RAD_USER, RAD_PW)
    svc("start")
    return {"caps": caps}


def case_X8(ctx):
    """★実 `enable` 時の方式リスト層 debug(3層目)。

    X8c= サーバ生存で Reject → **enable secret へ落ちない**(E16b の debug)。
    X8e= 全断で ERROR → `Method=ENABLE` → パスワード誤り → FAIL
         (提示された他社題材と同じ結末を RADIUS で再現できるか)。
    """
    rt, ip, svc = ctx["rt"], ctx["ip"], ctx["svc"]
    caps = []

    def run(tag, en_pw):
        res, buf = capture_during(
            rt, lambda: enable_via_ssh(ip, RAD_LOW, RAD_LOW_PW, en_pw), extra=12)
        caps.append((tag, f"{res[0]} {res[1]}", buf))

    run("X8a 既定(enable secret)・正しいパスワード", ADMIN_PW)
    run("X8b 既定(enable secret)・誤ったパスワード", "WrongEnable")
    rt.conf([f"aaa authentication enable default group {GRP} enable"])
    run("X8c ★サーバ生存 / group→enable ・正しいパスワード", ADMIN_PW)
    svc("stop")
    run("X8d ★全断 / group→enable ・正しいパスワード", ADMIN_PW)
    run("X8e ★全断 / group→enable ・誤ったパスワード", "WrongEnable")
    svc("start")
    rt.conf([f"no aaa authentication enable default"])
    return {"caps": caps}


LOW_LOCAL, LOW_LOCAL_PW = "lowlocal", "Low-1234"   # ★local かつ priv 1(X10 用)


def case_X10(ctx):
    """★★Ping-t 型の再現: method1 が**到達できず** → method2(enable) へ落ちる。

    X8d/X8e が空振りした理由= 全断時は RADIUS のみの利用者(helpdesk)が
    **そもそもログインできない**ため enable まで到達しない。
    → **local かつ priv 1** の利用者を用意し、全断でも入れるようにして測り直す。
    """
    rt, ip, svc = ctx["rt"], ctx["ip"], ctx["svc"]
    caps = []
    rt.conf([f"username {LOW_LOCAL} privilege 1 secret {LOW_LOCAL_PW}",
             f"aaa authentication enable default group {GRP} enable"])

    def run(tag, en_pw):
        res, buf = capture_during(
            rt, lambda: enable_via_ssh(ip, LOW_LOCAL, LOW_LOCAL_PW, en_pw),
            extra=14)
        caps.append((tag, f"{res[0]} {res[1]}", buf))

    run("X10a 健全 / group→enable ・正しい enable secret(参考)", ADMIN_PW)
    svc("stop")
    run("X10b ★全断 / group→enable ・正しい enable secret", ADMIN_PW)
    run("X10c ★★全断 / group→enable ・誤ったパスワード(他社題材と同型)",
        "WrongEnable")
    svc("start")
    rt.conf(["no aaa authentication enable default",
             f"no username {LOW_LOCAL}"])
    return {"caps": caps}


def case_X9(ctx):
    """★コンソール(キャラクタモード)ログインの方式リスト遍歴。

    X7 で判明= **SSH ログインでは `Method=` の遍歴が debug に出ない**
    (`AAA/AUTHEN/LOGIN: Pick method list 'default'` までしか出ない)。
    コンソールなら出るのか(= 紙面 authread 形をログイン層でも作れるか)を見る。
    """
    rt, svc = ctx["rt"], ctx["svc"]
    caps = []

    def run(tag, user, pw):
        # ★debug をコンソールへ流すと pyATS のログインが乱れる。観測は SSH 側の
        #   `terminal monitor` で行うので、コンソール出力は止めてから測る
        #   (console_probe の後始末が `logging console` を戻すため毎回入れる)。
        rt.conf(["no logging console"])
        res, buf = capture_during(rt, lambda: _console(ctx, user, pw), extra=14)
        caps.append((tag, f"{res[0]} {res[1]}", buf))

    run("X9a 健全 / RADIUS 台帳の利用者", RAD_USER, RAD_PW)
    run("X9b ★健全 / local のみの利用者(サーバは Reject)", LOCAL_ONLY, LOCAL_ONLY_PW)
    svc("stop")
    run("X9c ★全断 / local のみの利用者", LOCAL_ONLY, LOCAL_ONLY_PW)
    svc("start")
    return {"caps": caps}


CASES = [("X1", "if-authenticated / サーバ健全 — 属性は降ってくるか", case_X1),
         ("X2", "★if-authenticated / サーバ全断 — 権限レベルは何になるか", case_X2),
         ("X2b", "対照: 認可= group local / サーバ全断", case_X2b),
         ("X4", "★ACL で要求を落とす(out) — 症状はサーバ停止と同じか", case_X4),
         ("X4b", "★ACL で応答だけ落とす(in) — 要求は届いている", case_X4b),
         ("X5", "★コンソール認可 — グローバル無しでは効かないのか", case_X5),
         ("X6", "★同上＋`aaa authorization console`", case_X6),
         ("X7", "★★実ログイン時の方式リスト層 debug(Method= の遍歴)", case_X7),
         ("X8", "★★実 enable 時の方式リスト層 debug(3層目)", case_X8),
         ("X9", "★コンソール login の方式リスト遍歴(SSH では出ない)", case_X9),
         ("X10", "★★到達不能→enable へ落ちる 3層目の全景", case_X10)]


def main():
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    h = hosts()
    rt = Router(h["RT02"])
    s1, s2 = Server(h["SRV01"]), Server(h["SRV02"])

    def svc(action, which=("s1", "s2")):
        for name in which:
            (s1 if name == "s1" else s2).run(f"sudo -n systemctl {action} freeradius")
        time.sleep(3)

    ctx = {"rt": rt, "ip": h["RT02"], "svc": svc, "testbed": None}

    if not want or any(c in want for c in ("X5", "X6", "X9")):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import console_probe as cp
        from pyats.topology import loader
        from virl2_client import ClientLibrary
        cl = ClientLibrary(f"https://{os.environ.get('CML_HOST', '10.1.10.10')}",
                           os.environ.get("CML_USER", "admin"),
                           os.environ.get("CML_PASS", "CCNP"), ssl_verify=False)
        title = cp.lab_title()
        lab = None
        for cand in cl.all_labs():
            if cand.title == title and \
                    {n.label for n in cand.nodes()} >= {"RT01", "RT02"}:
                lab = cand
                break
        if lab is None:
            sys.exit("_POC-AAA のラボが CML に見つかりません")
        tb = yaml.safe_load(lab.get_pyats_testbed())
        for name, dev in (tb.get("devices") or {}).items():
            creds = dev.setdefault("credentials", {})
            if dev.get("type") == "terminal_server" or name == "terminal_server":
                creds["default"] = {"username": os.environ.get("CML_USER", "admin"),
                                    "password": os.environ.get("CML_PASS", "CCNP")}
        ctx["testbed"] = loader.load(tb)

    results = []
    try:
        for key, desc, fn in CASES:
            if want and key not in want:
                continue
            print(f"--- {key}: {desc}", flush=True)
            ensure_up(rt)
            t0 = time.time()
            try:
                out = fn(ctx)
            except Exception as ex:
                out = {"table": [("(ERROR)", f"{type(ex).__name__}: {ex}", "")]}
            results.append((key, desc, out, time.time() - t0))
            print(f"    done {time.time() - t0:.0f}s", flush=True)
    finally:
        try:
            svc("start")
        except Exception:
            pass
        rt.close(); s1.close(); s2.close()

    md = ["# BL-101 P0 追試3 — 紙面拡張候補の裏取り", "",
          "自動生成: poc/aaa/ext_probe.py。対象= _POC-AAA の RT02。", ""]
    for key, desc, out, el in results:
        md.append(f"## {key} — {desc}  ({el:.0f}s)\n")
        if out.get("table"):
            md.append("| 対象 | 条件 | 結果 |")
            md.append("|---|---|---|")
            for row in out["table"]:
                md.append("| " + " | ".join(str(x) for x in row) + " |")
            md.append("")
        for tag, res, buf in out.get("caps", []):
            md.append(f"### {tag} → **{res}**\n")
            md.append("```\n" + (buf or "(debug 出力なし)") + "\n```\n")
        for k in ("acl", "aaa_servers"):
            if out.get(k):
                md.append(f"`{k}`:\n\n```\n{out[k]}\n```\n")
    if OUT.exists() and any(a in ("--append",) for a in sys.argv):
        OUT.write_text(OUT.read_text() + "\n" + "\n".join(md[4:]))
    else:
        OUT.write_text("\n".join(md))
    print(f"\n書き出し: {OUT}")


if __name__ == "__main__":
    main()
