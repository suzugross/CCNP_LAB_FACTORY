#!/usr/bin/env python3
"""PoC: 管理 IF 経由の SSH で Linux ノード(Ubuntu)にコマンドを流す。1 引数 = 1 コマンド(bash -lc で実行)。
usage: lxsh.py <host> [-t 秒] [--put 手元:先 …] 'cmd' ...   資格情報は環境変数 NODE_USER/NODE_PASS(poc/xr/env.sh)。
`sudo` で始まるコマンドは sudo -S に置き換えてパスワードを渡す。コマンドごとに出力と終了コードを表示する。"""
import os
import shlex
import sys

import paramiko

args = sys.argv[1:]
timeout = 120
if "-t" in args:
    i = args.index("-t"); timeout = int(args[i + 1]); del args[i:i + 2]
puts = []
while "--put" in args:
    i = args.index("--put"); puts.append(args[i + 1].split(":", 1)); del args[i:i + 2]
host, cmds = args[0], args[1:]
user, pw = os.environ.get("NODE_USER"), os.environ.get("NODE_PASS")
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(host, username=user, password=pw, look_for_keys=False, allow_agent=False, timeout=15)
except Exception as e:
    print(f"!! connect failed: {type(e).__name__}: {e}"); sys.exit(2)
if puts:
    sf = c.open_sftp()
    for src, dst in puts:
        sf.put(src, dst); print(f"[put] {src} -> {dst}")
    sf.close()
for cmd in cmds:
    run = cmd
    sudo = cmd.startswith("sudo ")
    if sudo:
        run = "sudo -S -p '' bash -lc " + shlex.quote(cmd[5:])
    else:
        run = "bash -lc " + shlex.quote(cmd)
    shown = cmd.replace(pw, "***") if pw else cmd
    print("$ " + (shown.replace(user, "***") if user else shown))
    stdin, stdout, stderr = c.exec_command(run, timeout=timeout, get_pty=False)
    if sudo:
        stdin.write(pw + "\n"); stdin.flush()
    try:
        out = stdout.read().decode("utf-8", "replace"); err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
    except Exception as e:  # タイムアウトなど
        out, err, rc = "", f"{type(e).__name__}: {e}", -1
    if out:
        print(out.rstrip("\n"))
    if err.strip():
        print("[stderr] " + err.rstrip("\n"))
    print(f"[rc={rc}]")
c.close()
