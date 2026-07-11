#!/usr/bin/env python3
"""ASA/IOS コンソールにコマンドを流す最小ツール (BL-038 PoC 用)。

usage: asav_console.py <NODE> "cmd1" "cmd2" ...
NODE=FW01 は ASA 扱い(ウィザード/enable/pager 処理)、他は IOS 扱い。
"""
import pexpect

def _cml_creds(repo):
    """CML 認証は gitignore 済みの group_vars/all/local.yml から読む(ハードコード禁止)。"""
    import yaml as _y
    import os as _os
    d = _y.safe_load(open(_os.path.join(repo, "group_vars", "all", "local.yml")))
    return d["cml_host"], d["cml_username"], d["cml_password"]

CML_HOST, CML_USER, CML_PASS = _cml_creds("/home/suzuki/ansible/CCNP01")
import sys
import time

NODE = sys.argv[1]
CMDS = sys.argv[2:]
ASA_PW = "CCNPccnp"

c = pexpect.spawn(
    f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {CML_USER}@{CML_HOST}",
    encoding="utf-8", codec_errors="replace", timeout=30)
c.expect("assword:")
c.sendline(CML_PASS)
c.expect("consoles>")
c.sendline(f"open /POC-ASAV/{NODE}/0")
c.expect("Escape character")
time.sleep(2)
c.send("end\r")
time.sleep(1)
c.send("\r")

PROMPTS = [r"Enter  Password:", r"Repeat Password:", r"Passwords do not match",
           r"(\r\n|\r|\n)([\w-]+)(\([\w./-]+\))?> ", r"(\r\n|\r|\n)([\w-]+)(\([\w./-]+\))?# ",
           r"[Uu]sername:", r"assword:", pexpect.TIMEOUT]
reached = False
for step in range(15):
    idx = c.expect(PROMPTS, timeout=12)
    if idx in (0, 1):
        time.sleep(0.5)
        c.send(ASA_PW + "\r")
    elif idx == 2:
        continue
    elif idx == 3:
        c.send("enable\r")
    elif idx == 4:
        reached = True
        break
    elif idx == 5:
        c.send("SUZUKI\r")
    elif idx == 6:
        c.send(ASA_PW if NODE == "FW01" else "CCNP")
        c.send("\r")
    else:
        c.send("\r")
if not reached:
    print("[FAIL] could not reach priv exec")
    sys.exit(1)

c.logfile_read = sys.stdout
c.send(("terminal pager 0" if NODE == "FW01" else "terminal length 0") + "\r")
c.expect(r"(\r\n|\r|\n)[\w-]+(\([\w./-]+\))?# ", timeout=10)
for cmd in CMDS:
    c.send(cmd + "\r")
    c.expect(r"(\r\n|\r|\n)[\w-]+(\([\w./-]+\))?# ", timeout=60)
print("\n--- done ---")
c.close()
