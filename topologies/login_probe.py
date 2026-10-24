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
        --post-settle N … 後段(--post-cli / --post / リンクの復旧)の後に N 秒待つ。採点で故障を起こしたチェックの後、
        隣接や束が戻るのを待ってから次のチェックへ進ませる(XRT-06 M7)。
        --fail-link A:B … CML のリンク A-B にリンク条件 loss 100 を入れ、終わったら必ず外す(両端のポートは up のまま
        パケットだけ消える= 黙った故障)。ping-loss では --fail-at 秒後に入れ、それ以外の方式では前段で入れる。

  login_probe.py <ID> ping-loss <FROM> <DST> <SRC> [--count N] [--fail-link A:B --fail-at S]
      FROM(IOS)で `show ip route DST` を出してから `ping DST source SRC repeat N timeout 1` を流し、途中で故障を入れる。
      落ちた ping は 1 秒待つので、連続した欠落の数 ≒ 止まった秒数。`== FAULT DURING PING`(ping の途中で故障が入った)・
      `== PING SENT n LOST m`・`== LONGEST GAP g` を出す(XRT-06 M7-4= BFD で 1 秒以内に切り替わるか)。
  login_probe.py <ID> log-delta <NODE[,NODE…]> '<regex>'
      前段(--pre-cli など)より前に各 NODE の `show logging` から regex に合う行を控え、前段と --settle の後に
      もう一度取って、新しく出た行を数える。`== NEW MATCHES <NODE>: n`、全部 0 なら `== NO NEW MATCHES`
      (XRT-06 M7-5= XR01 で IS-IS を再起動しても相手に ADJCHANGE が出ないか)。
  login_probe.py <ID> watch <NODE> '<command>' [--samples N --interval S]
      先に NODE へログインしておき、それから前段(--pre-cli)を流して、すぐに command を N 回(S 秒おき)取る。
      `== SAMPLE i at +t s` に続けて出力を出す(XRT-06 M7-5= BGP を再起動した直後に相手が経路を保持しているか)。
"""
import os
import re
import sys
import threading
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


def cml_link(pid, a, b, loss):
    """CML のリンク a-b にリンク条件(パケットの廃棄率 loss %)を入れる。loss=None で外す。"""
    import warnings
    warnings.filterwarnings("ignore")
    from virl2_client import ClientLibrary
    title = yaml.safe_load(open(f"{REPO}/topologies/_generated/{pid}/lab.yaml"))["lab"]["title"]
    cfg = yaml.safe_load(open(f"{REPO}/group_vars/all/local.yml"))
    cl = ClientLibrary(f"https://{cfg['cml_host']}", cfg["cml_username"], cfg["cml_password"], ssl_verify=False)
    lab = next(lb for lb in cl.all_labs(show_all=True) if lb.title == title)
    link = next(lk for lk in lab.links() if {lk.node_a.label, lk.node_b.label} == {a, b})
    if loss is None:
        link.remove_condition()
    else:
        link.set_condition(loss=float(loss))
    print(f"== LINK {a}-{b} {'loss ' + str(loss) if loss is not None else 'clear'}", flush=True)


def do_ping_loss(pid, frm, dst, src, count, fail_link, fail_at, user, pw):
    c = connect(mgmt_ip(pid, frm), user, pw)
    sh = Shell(c)
    print(sh.send(f"show ip route {dst}", timeout=30), flush=True)
    t0, mark = time.time(), {}
    if fail_link:
        def inject():
            time.sleep(fail_at)
            try:
                cml_link(pid, fail_link[0], fail_link[1], 100)
                mark["t"] = time.time() - t0
            except Exception as e:  # 失敗も出力に残す(採点はそのチェックが落ちるだけ)
                print(f"== LINK FAILED: {type(e).__name__}: {e}", flush=True)
        th = threading.Thread(target=inject, daemon=True)
        th.start()
    sh.sh.send(f"ping {dst} source {src} repeat {count} timeout 1\n")
    out = sh.read(timeout=900)
    t_end = time.time() - t0
    c.close()
    body = "".join(ln.strip() for ln in out.splitlines() if re.fullmatch(r"[!.UQMA&?]+", ln.strip() or "x"))
    gaps = [len(m.group(0)) for m in re.finditer(r"[^!]+", body)]
    rate = next((ln for ln in out.splitlines() if "Success rate" in ln), "(no summary)")
    print(rate)
    if "t" in mark:
        print(f"== FAULT APPLIED at +{mark['t']:.1f}s, ping ended at +{t_end:.1f}s")
        if mark["t"] < t_end:
            print("== FAULT DURING PING")
    print(f"== PING SENT {len(body)} LOST {len(body) - body.count('!')} GAPS {gaps}")
    print(f"== LONGEST GAP {max(gaps, default=0)}")


def log_lines(pid, node, pattern, user, pw):
    c = connect(mgmt_ip(pid, node), user, pw)
    sh = Shell(c)
    out = sh.send("show logging", timeout=60)
    c.close()
    return [ln.strip() for ln in out.splitlines() if re.search(pattern, ln)]


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
    post_settle = int(opt("--post-settle", "0"))
    fail_link = opt("--fail-link")
    fail_link = fail_link.split(":") if fail_link else None
    fail_at = float(opt("--fail-at", "3"))
    count = int(opt("--count", "15000"))
    samples, interval = int(opt("--samples", "6")), float(opt("--interval", "1"))
    user, pw, source = opt("--user"), opt("--pass"), opt("--source")
    wait_node = opt("--wait-tacacs")
    lines = []
    if "--" in a:
        i = a.index("--")
        lines = a[i + 1:]
        a = a[:i]
    pid, mode = a[0], a[1]

    def front():
        for s in pre:
            run_linux(pid, s, lab_user, lab_pw)
        for s in pre_cli:
            run_cli(pid, s, lab_user, lab_pw)
        if fail_link and mode != "ping-loss":
            cml_link(pid, fail_link[0], fail_link[1], 100)
        if settle:
            time.sleep(settle)
    try:
        if mode == "log-delta":
            nodes, pattern = a[2].split(","), a[3]
            base = {n: set(log_lines(pid, n, pattern, lab_user, lab_pw)) for n in nodes}
            front()
            total = 0
            for n in nodes:
                new = [ln for ln in log_lines(pid, n, pattern, lab_user, lab_pw) if ln not in base[n]]
                for ln in new:
                    print(f"   {n}: {ln}")
                print(f"== NEW MATCHES {n}: {len(new)}")
                total += len(new)
            if not total:
                print("== NO NEW MATCHES")
            return
        if mode == "watch":
            c = connect(mgmt_ip(pid, a[2]), user or lab_user, pw or lab_pw)
            sh = Shell(c)
            front()
            t0 = time.time()
            for i in range(samples):
                out = sh.send(a[3], timeout=30)
                print(f"== SAMPLE {i + 1} at +{time.time() - t0:.1f}s")
                print(out, flush=True)
                time.sleep(interval)
            c.close()
            return
        front()
        if mode == "ping-loss":
            do_ping_loss(pid, a[2], a[3], a[4], count, fail_link, fail_at, user or lab_user, pw or lab_pw)
        elif mode == "ssh":
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
        if fail_link:
            try:
                cml_link(pid, fail_link[0], fail_link[1], None)
            except Exception as e:
                print(f"== LINK CLEAR FAILED: {type(e).__name__}: {e}")
        if wait_node:
            wait_tacacs(pid, wait_node, lab_user, lab_pw)
        if post_settle:
            time.sleep(post_settle)


if __name__ == "__main__":
    main()
