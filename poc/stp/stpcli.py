#!/usr/bin/env python3
"""STP PoC 用の telnet 操作器(BL-216)。config 投入と show 収集を 1 本の手順ファイルで回す。

  CCNP_USER=.. CCNP_PASS=.. stpcli.py HOSTS.json STEPS.yml
    HOSTS.json : {"SW01": "10.1.10.x", ...}
    STEPS.yml  : - {node: SW01, conf: [...], show: [...], wait: 秒}  (上から順に実行)
                 - {sleep: 秒}
出力は標準出力に「### node: cmd」見出し付きで流す(poc/stp/logs/ に tee する想定)。
config モードのプロンプトは `SW\\d+(\\([\\w-]+\\))?#`(poc/stp/README.md の知見 3)。
"""
import json
import os
import re
import sys
import time

import pexpect
import yaml

PROMPT = re.compile(r"\r?\n(SW\d+(?:\([\w-]+\))?#)")


def login(ip, user, pw):
    c = pexpect.spawn(f"telnet {ip}", timeout=60, encoding="utf-8", codec_errors="ignore")
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
        if n not in sess:
            for i in range(8):
                try:
                    sess[n] = login(hosts[n], user, pw)
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
            print(f"### {n}: conf {st['conf']}\n{txt}", flush=True)
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
