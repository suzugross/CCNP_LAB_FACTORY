#!/usr/bin/env python3
"""PoC 用の CLI 操作器(BL-225・エンタープライズ構築ラボ)。poc/mcast/mcli.py を元に、
IOS(ssh/telnet)に加えて Linux ノード(m: linux)のシェル実行に対応させたもの。

  CCNP_USER=.. CCNP_PASS=.. ecli.py HOSTS.json STEPS.yml
    HOSTS.json : {"RT01": {"ip": "10.1.10.x", "m": "ssh"}, "PC01": {"ip": "...", "m": "linux"}}
    STEPS.yml  : - {node: RT01, conf: [...], show: [...], wait: 秒}   IOS
                 - {node: PC01, sh: [...]}                           Linux(1 行ずつ `sudo bash -c`)
                 - {sleep: 秒} / - {note: 見出し}
出力は標準出力に「### 時刻 node: cmd」見出し付きで流す(poc/enterprise/logs/ に保存する想定)。
"""
import json
import os
import re
import shlex
import sys
import time

import pexpect
import yaml

PROMPT = re.compile(r"\r?\n([A-Z][A-Z0-9-]*(?:\([\w-]+\))?#)")
SSH = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"


def login(ip, user, pw, method="ssh"):
    if method == "ssh":
        c = pexpect.spawn(f"{SSH} {user}@{ip}", timeout=90, encoding="utf-8", codec_errors="ignore")
        c.expect("[Pp]assword:")
        c.sendline(pw)
    else:
        c = pexpect.spawn(f"telnet {ip}", timeout=90, encoding="utf-8", codec_errors="ignore")
        c.expect(["Username:", "login:"])
        c.sendline(user)
        c.expect("Password:")
        c.sendline(pw)
    c.expect([r">", r"#"])
    if c.after.strip().endswith(">"):
        c.sendline("enable")
        if c.expect(["Password:", r"#"]) == 0:
            c.sendline(pw)
            c.expect(r"#")
    c.sendline("terminal length 0")
    c.expect(PROMPT)
    c.sendline("terminal width 200")
    c.expect(PROMPT)
    return c


def run(c, cmd):
    c.sendline(cmd)
    buf = ""
    while c.expect([PROMPT, r"\[confirm\]"]) == 1:
        buf += c.before + c.after
        c.sendline("")
    lines = (buf + c.before).splitlines()
    if lines and cmd.strip() in lines[0]:
        lines = lines[1:]
    return "\n".join(lines).strip("\r\n")


def linux(ip, user, pw, cmd, timeout=120):
    """1 コマンドを ssh で実行(sudo)。出力と終了コードを返す。"""
    remote = f"echo {shlex.quote(pw)} | sudo -S -p '' bash -c {shlex.quote(cmd)}; echo __RC=$?"
    c = pexpect.spawn(f"{SSH} {user}@{ip} {shlex.quote(remote)}", timeout=timeout,
                      encoding="utf-8", codec_errors="ignore")
    c.expect("[Pp]assword:")
    c.sendline(pw)
    c.expect(pexpect.EOF)
    return c.before.strip("\r\n")


def main():
    hosts = json.load(open(sys.argv[1]))
    steps = yaml.safe_load(open(sys.argv[2]))
    user, pw = os.environ["CCNP_USER"], os.environ["CCNP_PASS"]
    sess = {}
    for st in steps:
        if "sleep" in st:
            print(f"### sleep {st['sleep']}", flush=True)
            time.sleep(st["sleep"])
            continue
        if "note" in st:
            print(f"\n======== {st['note']} ========", flush=True)
            if len(st) == 1:
                continue
        n = st["node"]
        h = hosts[n]
        if h.get("m") == "linux":
            for cmd in st.get("sh", []):
                print(f"### {time.strftime('%H:%M:%S')} {n}$ {cmd}\n{linux(h['ip'], user, pw, cmd, st.get('timeout', 120))}",
                      flush=True)
            if st.get("wait"):
                time.sleep(st["wait"])
            continue
        if n not in sess:
            for i in range(8):
                try:
                    sess[n] = login(h["ip"], user, pw, h.get("m", "ssh"))
                    break
                except (pexpect.EOF, pexpect.TIMEOUT):
                    print(f"### {n}: login retry {i + 1}", flush=True)
                    time.sleep(15)
            else:
                sys.exit(f"login failed: {n}")
        c = sess[n]
        if st.get("conf"):
            out = [run(c, "configure terminal")]
            for line in st["conf"]:
                out.append(run(c, line))
            out.append(run(c, "end"))
            txt = "\n".join(o for o in out if o.strip())
            print(f"### {time.strftime('%H:%M:%S')} {n}: conf {st['conf']}\n{txt}", flush=True)
        if st.get("wait"):
            time.sleep(st["wait"])
        for cmd in st.get("show", []):
            print(f"### {time.strftime('%H:%M:%S')} {n}: {cmd}\n{run(c, cmd)}", flush=True)
    for c in sess.values():
        try:
            c.sendline("exit")
            c.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
