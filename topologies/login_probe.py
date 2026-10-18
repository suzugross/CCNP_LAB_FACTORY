#!/usr/bin/env python3
"""採点機から実際にログインして挙動を確かめる道具(BL-246 XR トラック M2)。

採点のチェックで `exec: local` を指定すると、`_grade_attempt.yml` がこれを採点機(localhost)で実行し、
出力をそのまま採点に回す。行き先は管理 IF(`topologies/_generated/<ID>/mgmt_map.yml`)。
ラボの資格情報は環境変数 LAB_USER / LAB_PASS(採点のタスクが渡す)。

使い方:
  login_probe.py <ID> ssh <NODE> [--user U --pass P] -- 'line' ...
      指定ユーザで SSH し、行を順に流す(configure も可。最後は abort で抜ける)。
      先頭に `== LOGIN OK as U` か `== LOGIN FAILED as U: …` を出す。
  login_probe.py <ID> telnet <FROM> <DST> [--source IF] [--user U --pass P]
      FROM(IOS)にラボの資格情報で入り、そこから DST へ Telnet する。
      `== TELNET PROMPT`(ログイン要求が出た)/ `== TELNET REFUSED` / `== TELNET TIMEOUT` を出す。
      --user があればログインまで進め、`== TELNET LOGIN OK` か `== TELNET LOGIN FAILED` を足す。
  共通: --pre 'NODE:cmd' / --post 'NODE:cmd' … Linux ノードで前後にコマンドを実行する(--post は必ず実行)。
        サーバを止めた状態のログインを見るときに使う(採点は再試行されるので、--post で必ず元に戻す)。
        --wait-tacacs NODE … --post の後、NODE(IOS XR)の `show tacacs` から status=down が消えるまで待つ(最大 120 秒)。
        ★XR は応答しなかった TACACS+ サーバを保留(on-hold・status=down)にし、サーバが戻っても約 25 秒は使わない
        (24.3.1 実測)。待たないと、続くチェックのログインがローカルに落ちて誤って失敗する。
"""
import os
import re
import sys
import time

import paramiko
import yaml

PROMPT = re.compile(r"(?:^|\n)[\w/.:\-()]+[#>]\s*$")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def mgmt_ip(pid, node):
    m = yaml.safe_load(open(f"{REPO}/topologies/_generated/{pid}/mgmt_map.yml"))
    return m[node]


def connect(host, user, pw):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username=user, password=pw, look_for_keys=False, allow_agent=False,
              timeout=15, auth_timeout=30, banner_timeout=30)
    return c


class Shell:
    def __init__(self, client):
        self.sh = client.invoke_shell(width=250, height=1000)
        self.read(20)
        self.send("terminal length 0")

    def read(self, timeout=60, until=None):
        buf, t0 = "", time.time()
        while time.time() - t0 < timeout:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
                flat = buf.replace("\r", "")
                if (until and re.search(until, flat)) or PROMPT.search(flat) \
                        or re.search(r"(\[(cancel|no|yes)\]:|\[confirm\])\s*$", flat):
                    time.sleep(0.3)
                    if not self.sh.recv_ready():
                        return flat
            else:
                time.sleep(0.1)
        return buf.replace("\r", "") + "\n!! timeout"

    def send(self, line, timeout=60, until=None):
        self.sh.send(line + "\n")
        return self.read(timeout, until)


def run_linux(pid, spec, user, pw):
    node, cmd = spec.split(":", 1)
    try:
        c = connect(mgmt_ip(pid, node), user, pw)
        _, out, err = c.exec_command(cmd, timeout=60)
        rc = out.channel.recv_exit_status()
        c.close()
        print(f"== RUN {node} rc={rc}: {cmd}")
    except Exception as e:  # 失敗も出力に残す(採点はそのチェックが落ちるだけ)
        print(f"== RUN {node} FAILED: {cmd}: {type(e).__name__}: {e}")


def wait_tacacs(pid, node, user, pw, limit=120):
    t0 = time.time()
    while time.time() - t0 < limit:
        try:
            c = connect(mgmt_ip(pid, node), user, pw)
            sh = Shell(c)
            out = sh.send("show tacacs", timeout=30)
            c.close()
            if "status=down" not in out:
                print(f"== TACACS UP on {node} after {int(time.time() - t0)}s")
                return
        except Exception:
            pass
        time.sleep(5)
    print(f"== TACACS STILL DOWN on {node} after {limit}s")


def do_ssh(pid, node, user, pw, lines):
    try:
        c = connect(mgmt_ip(pid, node), user, pw)
    except Exception as e:
        print(f"== LOGIN FAILED as {user}: {type(e).__name__}: {e}")
        return
    print(f"== LOGIN OK as {user}")
    sh = Shell(c)
    in_config = False
    for ln in lines:
        out = sh.send(ln, timeout=120)
        print(out, flush=True)
        if ln.strip().startswith("conf"):
            in_config = True
    if in_config:
        sh.send("abort")  # 未コミットの行を残さない(コミット済みのものは戻さない)
    c.close()


def do_telnet(pid, frm, dst, source, user, pw, lab_user, lab_pw):
    c = connect(mgmt_ip(pid, frm), lab_user, lab_pw)
    sh = Shell(c)
    cmd = f"telnet {dst}" + (f" /source-interface {source}" if source else "")
    out = sh.send(cmd, timeout=20, until=r"(Username:|[Ll]ogin:|refused|timed out|Destination unreachable|closed)")
    print(out)
    if re.search(r"Username:|[Ll]ogin:", out):
        print("== TELNET PROMPT")
        if user:
            out = sh.send(user, timeout=20, until=r"[Pp]assword:")
            out = sh.send(pw, timeout=40, until=r"(#\s*$|>\s*$|failed|[Ii]nvalid|Username:)")
            print(out)
            ok = re.search(r"[#>]\s*$", out.strip() + "\n".strip()) and not re.search(r"failed|[Ii]nvalid", out)
            print("== TELNET LOGIN OK" if ok else "== TELNET LOGIN FAILED")
            if ok:
                sh.send("exit", timeout=15)
    elif re.search(r"refused", out):
        print("== TELNET REFUSED")
    else:
        print("== TELNET TIMEOUT")
    # 張りっぱなしなら切る(Ctrl-Shift-6 x → disconnect)
    sh.sh.send("\x1e")
    time.sleep(0.5)
    sh.sh.send("x")
    sh.send("disconnect", timeout=10, until=r"confirm|\[")
    sh.send("", timeout=10)
    c.close()


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        if name in a:
            i = a.index(name)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return default

    lab_user, lab_pw = os.environ["LAB_USER"], os.environ["LAB_PASS"]
    pre, post = [], []
    while "--pre" in a:
        pre.append(opt("--pre"))
    while "--post" in a:
        post.append(opt("--post"))
    user, pw, source = opt("--user"), opt("--pass"), opt("--source")
    wait_node = opt("--wait-tacacs")
    lines = []
    if "--" in a:
        i = a.index("--")
        lines = a[i + 1:]
        a = a[:i]
    pid, mode = a[0], a[1]
    try:
        for s in pre:
            run_linux(pid, s, lab_user, lab_pw)
        if mode == "ssh":
            do_ssh(pid, a[2], user or lab_user, pw or lab_pw, lines)
        elif mode == "telnet":
            do_telnet(pid, a[2], a[3], source, user, pw, lab_user, lab_pw)
        else:
            sys.exit(f"unknown mode {mode}")
    finally:
        for s in post:
            run_linux(pid, s, lab_user, lab_pw)
        if wait_node:
            wait_tacacs(pid, wait_node, lab_user, lab_pw)


if __name__ == "__main__":
    main()
