#!/usr/bin/env python3
"""PoC: telnet で IOL-L2 などの SSH 不可の機器に行を流す(設定モードも可)。各行の後は次のプロンプト(…# か …>)まで待つ。
usage: swsh.py <host> 'line' ...   資格情報は環境変数 NODE_USER/NODE_PASS(poc/xr/env.sh)。"""
import os
import sys

import pexpect

host, lines = sys.argv[1], sys.argv[2:]
PROMPT = r"\r?\n[\w.\-]+(?:\([\w\-/. ]+\))?[#>]\s*$"
c = pexpect.spawn(f"telnet {host}", timeout=60, encoding="utf-8", codec_errors="ignore")
c.expect([r"[Uu]sername:", r"[Ll]ogin:"]); c.sendline(os.environ["NODE_USER"])
c.expect(r"[Pp]assword:"); c.sendline(os.environ["NODE_PASS"])
c.expect(PROMPT)
c.sendline("terminal length 0"); c.expect(PROMPT)
for ln in lines:
    c.sendline(ln)
    c.expect(PROMPT)
    print(ln + c.before.split("\n", 1)[-1] if "\n" in c.before else ln)
    print(c.after.strip())
c.sendline("exit")
