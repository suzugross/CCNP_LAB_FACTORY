#!/usr/bin/env python3
"""EEM の無い機器(IOL-L2)に telnet で入り、SSH の鍵を作る(BL-246 XR トラック M11 追補・XRT-12 の SW1)。

baseline は SSH の鍵を EEM で起動後に作るが、IOL-L2 には EEM が無く、applet ごと捨てられて SSH が開かない
(2026-11-01 実測= `show ip ssh` が `SSH Disabled`・running-config に applet が無い)。採点の `exec: local`
(login_probe.py)は SSH で入るので、そういう機器だけ構築の最後に鍵を作る。problem.yml に次を書いた問題が対象:

  ssh_keygen_telnet: [SW1]

  telnet_keygen.py --repo <リポ> --problem <ID>

既に `SSH Enabled` なら何もしない。資格情報は環境変数 NODE_USER / NODE_PASS。管理 IF の telnet(baseline で許可済み)を使う。
"""
import argparse
import os
import re
import sys
import time

import pexpect
import yaml

PROMPT = r"\r?\n[\w.\-]+(?:\([\w\-/. ]+\))?[#>]\s*$"


def run(ip, user, pw, wait=600):
    t0 = time.time()
    while True:
        try:
            c = pexpect.spawn(f"telnet {ip}", timeout=60, encoding="utf-8", codec_errors="ignore")
            c.expect([r"[Uu]sername:", r"[Ll]ogin:"])
            break
        except Exception:
            if time.time() - t0 >= wait:
                raise
            time.sleep(15)
    c.sendline(user)
    c.expect(r"[Pp]assword:")
    c.sendline(pw)
    c.expect(PROMPT)

    def cmd(line, timeout=60):
        c.sendline(line)
        c.expect(PROMPT, timeout=timeout)
        return c.before

    cmd("terminal length 0")
    if re.search(r"SSH Enabled", cmd("show ip ssh")):
        c.sendline("exit")
        return "already enabled"
    cmd("configure terminal")
    cmd("crypto key generate rsa modulus 2048", timeout=180)
    cmd("end")
    out = cmd("show ip ssh")
    c.sendline("exit")
    return "enabled" if "SSH Enabled" in out else "FAILED: " + out.strip()[-200:]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--problem", required=True)
    a = ap.parse_args()
    pmeta = yaml.safe_load(open(os.path.join(a.repo, "problems", a.problem, "problem.yml"), encoding="utf-8"))
    nodes = pmeta.get("ssh_keygen_telnet") or []
    mgmt = yaml.safe_load(open(os.path.join(a.repo, "topologies/_generated", a.problem, "mgmt_map.yml"), encoding="utf-8"))
    bad = 0
    for n in nodes:
        try:
            res = run(str(mgmt[n]), os.environ["NODE_USER"], os.environ["NODE_PASS"])
        except Exception as e:
            res = f"FAILED: {type(e).__name__}: {e}"
        print(f"[{n}] ssh {res}")
        bad += res.startswith("FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
