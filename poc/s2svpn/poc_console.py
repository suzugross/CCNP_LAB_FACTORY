#!/usr/bin/env python3
"""BL-063 PoC 用コンソールドライバ（IOS/IOL＋alpine 両対応・pexpect 直叩き）。

CML のコンソールサーバ(ssh)経由で 1 ノードに接続して実行する。MGMT/SSH 不要。

使い方:
  poc_console.py --node HQ  --exec "show ip nat translations;;show crypto ipsec sa"
  poc_console.py --node HQ  --config "interface Tunnel0\n ip address ..."
  poc_console.py --node H-B1 --sh "ping -c 3 198.51.100.80;;wget -qO- http://198.51.100.80/"
コマンド区切りは ';;'。--config は改行区切り(configure terminal 配下)。
"""
import argparse
import os
import sys
import time

import pexpect
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TITLE = "POC-S2SVPN"
ALPINE = {"SRV", "H-HQ", "H-B1"}

P_NET = r"(\r\n|\r|\n)([\w/-]+)(\([\w./-]+\))?([>#]) ?"
P_ALP = r"(\r\n|\r|\n)[\w-]+:[^\r\n]*[#$] ?"


def _creds():
    c = yaml.safe_load(open(os.path.join(REPO, "group_vars", "all", "local.yml")))
    return c["cml_host"], c["cml_username"], c["cml_password"]


def _open(node):
    host, user, pw = _creds()
    c = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {user}@{host}",
        encoding="utf-8", codec_errors="replace", timeout=30)
    c.expect("assword:")
    c.sendline(pw)
    c.expect("consoles>")
    c.sendline(f"open /{TITLE}/{node}/0")
    c.expect("Escape character")
    time.sleep(2)
    return c


def console(node):
    c = _open(node)
    if node in ALPINE:
        c.send("\r")
        for _ in range(10):
            idx = c.expect([r"login:", r"assword:", P_ALP, pexpect.TIMEOUT], timeout=12)
            if idx == 0:
                c.send("root\r")
            elif idx == 1:
                c.send("cisco\r")
            elif idx == 2:
                return c, P_ALP
            else:
                c.send("\r")
        raise RuntimeError(f"{node}: alpine シェル不達")
    c.send("\r")
    for _ in range(15):
        idx = c.expect([P_NET, r"assword:", r"sername:", r"initial configuration dialog",
                        pexpect.TIMEOUT], timeout=15)
        if idx == 0:
            if c.match.group(4) == "#":
                return c, P_NET
            c.send("enable\r")
        elif idx == 1:
            c.send("CCNP\r")
        elif idx == 2:
            c.send("SUZUKI\r")
        elif idx == 3:
            c.send("no\r")
        else:
            c.send("\r")
    raise RuntimeError(f"{node}: priv exec 不達")


def _drain(c):
    time.sleep(0.5)
    try:
        while True:
            c.read_nonblocking(size=4096, timeout=1)
    except Exception:
        pass


def run(c, prompt, cmd, timeout):
    _drain(c)
    c.send(cmd + "\r")
    out = []
    while True:
        idx = c.expect([prompt, r" --More-- ", pexpect.TIMEOUT], timeout=timeout)
        out.append(c.before or "")
        if idx == 0:
            break
        if idx == 1:
            c.send(" ")
        else:
            break
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    ap.add_argument("--exec", dest="exec_cmds", default=None)
    ap.add_argument("--config", dest="config_lines", default=None)
    ap.add_argument("--sh", dest="sh_cmds", default=None)
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    c, prompt = console(args.node)
    try:
        if args.config_lines:
            lines = args.config_lines.replace("\\n", "\n").split("\n")
            run(c, prompt, "configure terminal", args.timeout)
            for ln in lines:
                if ln.strip():
                    print(run(c, prompt, ln.rstrip(), args.timeout), end="")
            print(run(c, prompt, "end", args.timeout))
        for blob, label in ((args.exec_cmds, "exec"), (args.sh_cmds, "sh")):
            if blob:
                for cmd in blob.split(";;"):
                    print(f"===== [{args.node}] {cmd.strip()} =====")
                    print(run(c, prompt, cmd.strip(), args.timeout))
    finally:
        c.close(force=True)


if __name__ == "__main__":
    main()
