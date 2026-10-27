#!/usr/bin/env python3
"""PoC: IOS から相手の TCP 22 番へ telnet し、SSH のバナー(SSH-2.0)が返るかで「TCP が通り抜けるか」を見る。
usage: tcpprobe.py <ios-mgmt-host> <宛先> [送信元 IF] [vrf 名]
出力の最後の行= TCP-OK(バナーあり)/ TCP-NG(バナーなし)。資格情報は環境変数 NODE_USER/NODE_PASS(poc/xr/env.sh)。
XRd がラベルなしで通り抜ける TCP/UDP の L4 チェックサムを壊す件(design §14.1)の確かめ用。"""
import os
import sys
import time

import paramiko

host, dst = sys.argv[1], sys.argv[2]
src = sys.argv[3] if len(sys.argv) > 3 else ""
vrf = sys.argv[4] if len(sys.argv) > 4 else ""
cmd = f"telnet {dst} 22" + (f" /vrf {vrf}" if vrf else "") + (f" /source-interface {src}" if src else "")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=os.environ["NODE_USER"], password=os.environ["NODE_PASS"],
          look_for_keys=False, allow_agent=False, timeout=15)
sh = c.invoke_shell(width=200, height=200)
time.sleep(2)
while sh.recv_ready():
    sh.recv(65535)
sh.send(cmd + "\n")
buf, t0 = "", time.time()
while time.time() - t0 < 15 and "SSH-2.0" not in buf:
    if sh.recv_ready():
        buf += sh.recv(65535).decode("utf-8", "replace")
    else:
        time.sleep(0.2)
c.close()  # セッションごと閉じれば telnet も終わる
print(f"$ {cmd}")
print(buf.replace("\r", "").strip())
print("TCP-OK" if "SSH-2.0" in buf else "TCP-NG")
