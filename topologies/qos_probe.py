#!/usr/bin/env python3
"""採点機から QoS とデータプレーンの保護を数えて確かめる道具(BL-246 XR トラック M12)。

採点のチェックで `exec: local` を指定して使う(login_probe.py と同じく、行き先は管理 IF・資格情報は LAB_USER / LAB_PASS)。
「数を消す → 試験のトラフィックを流す → 待つ → 数える」を 1 回の実行でまとめ、数を 1 行ずつに整えて出す
(採点の正規表現は `== COUNT …` の行の数をそのまま照合する)。

使い方:
  qos_probe.py <ID> run [--clear 'NODE:line;;line']… [--echo NODE]… [--send 'NODE:line;;line']…
                        [--wait N] [--count 'NODE:IF:input|output']… [--show 'NODE:command']…
  順番= --echo の控え → --clear → --send(上から順に・ping の Success の行を出す)→ --wait 秒 → --count → --echo の増分 → --show。
    --clear  … 数を消す行(`clear counters` の確認は自動で答える)。
    --echo   … その機器(IOS)が受けた echo の数(`show ip traffic` の Rcvd の echo)の増分を `== ECHO <NODE> +n` で出す。
               送った ping が途中で落ちたか(uRPF・RTBH・ACL)を、宛ての機器に届いた数で見る(応答が戻らない偽装の送信元でも数えられる)。
    --send   … 試験のトラフィック(CE などの ping)。`== SEND <NODE>: <行> => <Success の行>` を出す。
    --wait   … ★IOS XR(XRv9000)の方策のカウンタは 10〜30 秒遅れて反映する(2026-11-07 実測)ので、XR を数える時は 30 秒ほど待つ。
    --count  … `show policy-map interface <IF> <向き>` を読み、クラスごとの数を `== COUNT <NODE> <クラス> <数>` で出す。
               IOS= Class-map の最初の「n packets」。IOS XR= Matched の数・ポリサの内訳は `<クラス>.conform/.exceed/.violate`・
               子の方策(`Policy P Class C`)は `<P>/<C>`。
    --show   … コマンドの出力をそのまま出す(`== SHOW <NODE>: <command>` の後に続ける)。
  共通: --pre-cli 'NODE:line;;line' / --post-cli 'NODE:line;;line'(login_probe.py と同じ。--post-cli は必ず実行)・--settle N(前段の後に待つ)。
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from login_probe import Shell, connect, mgmt_ip, run_cli  # noqa: E402


def session(pid, node, user, pw):
    return Shell(connect(mgmt_ip(pid, node), user, pw))


def lines_of(spec):
    node, rest = spec.split(":", 1)
    return node, [ln for ln in rest.split(";;") if ln.strip()]


def echo_count(pid, node, user, pw):
    try:
        sh = session(pid, node, user, pw)
        out = sh.send("show ip traffic", timeout=60)
        sh.sh.close()
    except Exception as e:
        print(f"== ECHO {node} FAILED: {type(e).__name__}: {e}")
        return None
    seen = False
    for ln in out.splitlines():
        if "Rcvd:" in ln:
            seen = True
        m = re.match(r"\s*(\d+) echo", ln)
        if seen and m:
            return int(m.group(1))
    return None


def run_lines(pid, spec, user, pw, tag):
    node, lines = lines_of(spec)
    try:
        sh = session(pid, node, user, pw)
        for ln in lines:
            out = sh.send(ln, timeout=180, until=r"\[confirm\]\s*$")
            if re.search(r"\[confirm\]\s*$", out):
                out += sh.send("", timeout=60)
            if tag == "SEND":
                m = re.search(r"Success rate is .*", out)
                print(f"== SEND {node}: {ln} => {m.group(0) if m else out.strip().splitlines()[-1:]}", flush=True)
        sh.sh.close()
        if tag != "SEND":
            print(f"== {tag} {node}: {len(lines)} lines")
    except Exception as e:  # 失敗も出力に残す(採点はそのチェックが落ちるだけ)
        print(f"== {tag} {node} FAILED: {type(e).__name__}: {e}")


def parse_policy(out):
    """show policy-map interface の出力からクラスごとの数を取り出す(IOS と IOS XR の両方)。"""
    res, cur = {}, None
    for ln in out.splitlines():
        m = re.match(r"\s*Class-map:\s+(\S+)", ln)                      # IOS
        if m:
            cur = m.group(1); res.setdefault(cur, None); continue
        m = re.match(r"\s*Policy\s+(\S+)\s+Class\s+(\S+)", ln)           # IOS XR の子の方策
        if m:
            cur = f"{m.group(1)}/{m.group(2)}"; res.setdefault(cur, None); continue
        m = re.match(r"\s*Class\s+(\S+)\s*$", ln)                        # IOS XR
        if m:
            cur = m.group(1); res.setdefault(cur, None); continue
        if cur is None:
            continue
        m = re.match(r"\s*(\d+) packets, \d+ bytes", ln)                 # IOS: 最初の行がクラスの数
        if m and res.get(cur) is None:
            res[cur] = int(m.group(1)); continue
        m = re.match(r"\s*Matched\s*:\s*(\d+)/", ln)                     # IOS XR
        if m:
            res[cur] = int(m.group(1)); continue
        m = re.match(r"\s*Policed\((conform|exceed|violate)\)\s*:\s*(\d+)/", ln)
        if m:
            res[f"{cur}.{m.group(1)}"] = int(m.group(2))
    return res


def count(pid, spec, user, pw):
    node, ifname, direction = spec.split(":")
    try:
        sh = session(pid, node, user, pw)
        out = sh.send(f"show policy-map interface {ifname} {direction}", timeout=60)
        sh.sh.close()
    except Exception as e:
        print(f"== COUNT {node} FAILED: {type(e).__name__}: {e}")
        return
    res = parse_policy(out)
    if not res:
        print(f"== COUNT {node} {ifname} {direction}: NO POLICY")
    for k, v in res.items():
        print(f"== COUNT {node} {k} {v if v is not None else 0}")


def show(pid, spec, user, pw):
    node, cmd = spec.split(":", 1)
    try:
        sh = session(pid, node, user, pw)
        out = sh.send(cmd, timeout=120)
        sh.sh.close()
        print(f"== SHOW {node}: {cmd}")
        print(out, flush=True)
    except Exception as e:
        print(f"== SHOW {node} FAILED: {type(e).__name__}: {e}")


def main():
    a = sys.argv[1:]

    def opts(name):
        vals = []
        while name in a:
            i = a.index(name)
            vals.append(a[i + 1])
            del a[i:i + 2]
        return vals

    user, pw = os.environ["LAB_USER"], os.environ["LAB_PASS"]
    pre_cli, post_cli = opts("--pre-cli"), opts("--post-cli")
    clears, echoes, sends = opts("--clear"), opts("--echo"), opts("--send")
    counts, shows = opts("--count"), opts("--show")
    wait = int((opts("--wait") or ["0"])[0])
    settle = int((opts("--settle") or ["0"])[0])
    pid, mode = a[0], a[1]
    if mode != "run":
        sys.exit(f"unknown mode {mode}")
    try:
        for s in pre_cli:
            run_cli(pid, s, user, pw)
        if settle:
            time.sleep(settle)
        base = {n: echo_count(pid, n, user, pw) for n in echoes}
        for s in clears:
            run_lines(pid, s, user, pw, "CLEAR")
        for s in sends:
            run_lines(pid, s, user, pw, "SEND")
        if wait:
            time.sleep(wait)
        for s in counts:
            count(pid, s, user, pw)
        for n in echoes:
            now = echo_count(pid, n, user, pw)
            if base[n] is None or now is None:
                print(f"== ECHO {n} UNKNOWN")
            else:
                print(f"== ECHO {n} +{now - base[n]}")
        for s in shows:
            show(pid, s, user, pw)
    finally:
        for s in post_cli:
            run_cli(pid, s, user, pw)


if __name__ == "__main__":
    main()
