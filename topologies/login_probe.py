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
  login_probe.py <ID> xr-adj-since <NODE> '<regex>'
      IOS XR の NODE で、変更の差分(`show configuration commit changes <ID>`)が regex に一致する
      コミットのうち最新のものを探し、その時刻以降に `show isis adjacency-log` に記録された隣接の状態変化を数える。
      `== CHANGE COMMIT <ID> at <時刻>`(見つからなければ `== CHANGE NOT FOUND`)・`== ADJ EVENTS SINCE CHANGE: n`、
      0 件なら `== ADJ STABLE` を出す。「作業中に隣接を落とさない」を状態で見るときに使う
      (例: XRT-05 M4-8= NET の付け替え。1 コミットで入れ替えると全隣接が張り直されて記録が残る)。
  共通: --pre 'NODE:cmd' / --post 'NODE:cmd' … Linux ノードで前後にコマンドを実行する(--post は必ず実行)。
        サーバを止めた状態のログインを見るときに使う(採点は再試行されるので、--post で必ず元に戻す)。
        --pre-cli 'NODE:line;;line' / --post-cli 'NODE:line;;line' … IOS/IOS XR の CLI に前後で行を流す
        (`;;` で区切る。--post-cli は必ず実行)。採点のあいだだけ相手役に変化を起こすときに使う
        (例: XRT-04 M4-4= RT02 に一時的なループバックを足し、XR01 の漏らしが範囲で書かれているかを見る)。
        --settle N … 前段(--pre / --pre-cli)の後、本体の前に N 秒待つ(経路の伝搬待ち)。
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


def run_cli(pid, spec, user, pw):
    node, rest = spec.split(":", 1)
    lines = [ln for ln in rest.split(";;") if ln.strip()]
    try:
        c = connect(mgmt_ip(pid, node), user, pw)
        sh = Shell(c)
        for ln in lines:
            sh.send(ln, timeout=60)
        c.close()
        print(f"== CLI {node}: {len(lines)} lines")
    except Exception as e:  # 失敗も出力に残す(採点はそのチェックが落ちるだけ)
        print(f"== CLI {node} FAILED: {type(e).__name__}: {e}")


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


MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def do_xr_adj_since(pid, node, pattern, user, pw):
    """変更を入れた最新のコミットの時刻以降に、IS-IS の隣接の状態変化が記録されていないかを数える。"""
    import datetime
    c = connect(mgmt_ip(pid, node), user, pw)
    sh = Shell(c)
    lst = sh.send("show configuration commit list detail", timeout=60)  # 件数の上限はその時点のコミット数(超えると入力エラー)
    commits = re.findall(r"CommitId:\s+(\d+)[\s\S]*?Time:\s+\w+\s+(\w+)\s+(\d+)\s+(\d+):(\d+):(\d+)\s+(\d{4})", lst)
    found = None
    for cid, mon, day, hh, mm, ss, year in commits:  # 新しい順に並んでいる
        diff = sh.send(f"show configuration commit changes {cid}", timeout=60)
        if re.search(pattern, diff, re.M):
            found = (cid, datetime.datetime(int(year), MONTHS[mon], int(day), int(hh), int(mm), int(ss)))
            break
    if not found:
        print("== CHANGE NOT FOUND")
        c.close()
        return
    cid, t0 = found
    print(f"== CHANGE COMMIT {cid} at {t0:%Y-%m-%d %H:%M:%S}")
    log = sh.send("show isis adjacency-log", timeout=60)
    c.close()
    date, events = None, []
    for ln in log.splitlines():
        m = re.match(r"--- \w+ (\w+) (\d+) (\d{4}) ---", ln.strip())
        if m:
            date = (int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
            continue
        m = re.match(r"(\d+):(\d+):(\d+)\.\d+\s+(\S+)\s+(\S+)\s+(\S+ -> \S+)", ln)
        if m and date:
            t = datetime.datetime(*date, int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if t >= t0:
                events.append(ln.strip())
    for e in events:
        print(f"   {e}")
    print(f"== ADJ EVENTS SINCE CHANGE: {len(events)}")
    if not events:
        print("== ADJ STABLE")


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
    pre, post, pre_cli, post_cli = [], [], [], []
    while "--pre-cli" in a:
        pre_cli.append(opt("--pre-cli"))
    while "--post-cli" in a:
        post_cli.append(opt("--post-cli"))
    while "--pre" in a:
        pre.append(opt("--pre"))
    while "--post" in a:
        post.append(opt("--post"))
    settle = int(opt("--settle", "0"))
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
        for s in pre_cli:
            run_cli(pid, s, lab_user, lab_pw)
        if settle:
            time.sleep(settle)
        if mode == "ssh":
            do_ssh(pid, a[2], user or lab_user, pw or lab_pw, lines)
        elif mode == "telnet":
            do_telnet(pid, a[2], a[3], source, user, pw, lab_user, lab_pw)
        elif mode == "xr-adj-since":
            do_xr_adj_since(pid, a[2], a[3], user or lab_user, pw or lab_pw)
        else:
            sys.exit(f"unknown mode {mode}")
    finally:
        for s in post_cli:
            run_cli(pid, s, lab_user, lab_pw)
        for s in post:
            run_linux(pid, s, lab_user, lab_pw)
        if wait_node:
            wait_tacacs(pid, wait_node, lab_user, lab_pw)


if __name__ == "__main__":
    main()
