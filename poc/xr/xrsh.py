#!/usr/bin/env python3
"""PoC: 管理 IF 経由の SSH で XR/IOS に行を流す。usage: xrsh.py <host> [-u user -p pass] 'line' ...
既定の資格情報は環境変数 NODE_USER/NODE_PASS。各行の後はプロンプト(# か >)まで待つ。"""
import os, re, sys, time
import paramiko

args = sys.argv[1:]
user, pw = os.environ.get("NODE_USER"), os.environ.get("NODE_PASS")
if "-u" in args:
    i = args.index("-u"); user = args[i + 1]; del args[i:i + 2]
if "-p" in args:
    i = args.index("-p"); pw = args[i + 1]; del args[i:i + 2]
host, lines = args[0], args[1:]
PROMPT = re.compile(r"(\n|^)[\w/.:\-()]+[#>]\s*$")
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(host, username=user, password=pw, look_for_keys=False, allow_agent=False, timeout=15)
except Exception as e:
    print(f"!! connect failed: {type(e).__name__}: {e}"); sys.exit(2)
sh = c.invoke_shell(width=250, height=1000)


def read(timeout=60):
    buf, t0 = "", time.time()
    while time.time() - t0 < timeout:
        if sh.recv_ready():
            buf += sh.recv(65535).decode("utf-8", "replace")
            if PROMPT.search(buf.replace("\r", "")) or re.search(r"\[(cancel|no|yes)\]:\s*$", buf):
                time.sleep(0.3)
                if not sh.recv_ready():
                    return buf
        else:
            time.sleep(0.1)
    return buf + "\n!! timeout"


read(20)
sh.send("terminal length 0\n"); read(10)
for ln in lines:
    sh.send(ln + "\n")
    print(read(120).replace("\r", ""), flush=True)
c.close()
