#!/usr/bin/env python3
"""POC-MPLSHS 用 SSH プローブ。usage: probe.py <host> <cmd> [<cmd>...]
各コマンドを invoke_shell で順次実行し、プロンプト区切りで出力を表示する。
config 投入は 'conf t' から 'end' までを1引数ずつ渡せばよい。
"""
import sys, time, re
import paramiko

HOST = sys.argv[1]
CMDS = sys.argv[2:]

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, username="SUZUKI", password="CCNP", look_for_keys=False,
            allow_agent=False, timeout=15)
sh = cli.invoke_shell(width=511)
sh.settimeout(30)

PROMPT = re.compile(r"[\w.-]+(\(config[^)]*\))?[#>]\s*$")

def read_until_prompt(deadline=25):
    buf = ""
    t0 = time.time()
    while time.time() - t0 < deadline:
        if sh.recv_ready():
            buf += sh.recv(65535).decode("utf-8", "replace")
            if PROMPT.search(buf.rsplit("\n", 1)[-1]):
                break
        else:
            time.sleep(0.1)
    return buf

read_until_prompt(8)
sh.send("terminal length 0\n")
read_until_prompt(8)

for cmd in CMDS:
    sh.send(cmd + "\n")
    time.sleep(0.3)
    out = read_until_prompt()
    print(f"===[{HOST}] {cmd}===")
    print(out)

cli.close()
