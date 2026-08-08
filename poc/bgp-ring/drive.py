#!/usr/bin/env python3
"""BL-093 PoC driver: _POC-BGPRING の IOL 4台へ SSH で show/config を流す薄いヘルパ。

使い方:
  drive.py show RT01 "show ip bgp" ["show ip route bgp" ...]
  drive.py conf RT02 "router bgp 65002" "address-family ipv4 unicast" ...
  drive.py all "show ip bgp | begin Network"          # 4台一斉 show
mgmt IP は topologies/_generated/_POC-BGPRING/mgmt_map.yml から読む。
"""
import sys, time, re
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-BGPRING"
USER, PW = "SUZUKI", "CCNP"
NODES = ["RT01", "RT02", "RT03", "RT04"]


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


def session(ip):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(ip, username=USER, password=PW, look_for_keys=False,
                allow_agent=False, timeout=20)
    sh = cli.invoke_shell(width=511)
    _expect(sh, r"[>#]\s*$")
    sh.send("terminal length 0\n")
    _expect(sh, r"#\s*$")
    return cli, sh


def _expect(sh, pat, timeout=30):
    buf, t0 = "", time.time()
    while time.time() - t0 < timeout:
        if sh.recv_ready():
            buf += sh.recv(65535).decode("utf-8", "replace")
            if re.search(pat, buf.splitlines()[-1] if buf.splitlines() else ""):
                return buf
        else:
            time.sleep(0.1)
    raise TimeoutError(f"prompt timeout; tail={buf[-300:]!r}")


def run(sh, cmd, timeout=60):
    sh.send(cmd + "\n")
    out = _expect(sh, r"(?:\(config[^)]*\))?#\s*$", timeout)
    lines = out.replace("\r", "").splitlines()
    return "\n".join(lines[1:-1] if len(lines) > 1 else lines)


def do(node, cmds, config=False):
    ip = hosts()[node]
    cli, sh = session(ip)
    print(f"===== {node} ({ip}) =====")
    try:
        if config:
            run(sh, "configure terminal")
            for c in cmds:
                r = run(sh, c)
                if r.strip():
                    print(r)
            run(sh, "end")
            print("[config applied]")
        else:
            for c in cmds:
                print(f"--- {c} ---")
                print(run(sh, c))
    finally:
        cli.close()


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "all":
        for n in NODES:
            do(n, sys.argv[2:])
    else:
        do(sys.argv[2], sys.argv[3:], config=(mode == "conf"))
