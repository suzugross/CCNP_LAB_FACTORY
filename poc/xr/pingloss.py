#!/usr/bin/env python3
"""PoC: IOS から連続 ping を打ち、欠落の数で切り替え時間を測る。BL-246 M7。

usage: pingloss.py <IOS 管理 IP> <宛先> <送信元 IF/IP> [回数=20000]
  `ping <宛先> source <送信元> repeat <回数> timeout 1` を流す。返ってきた ping は数 ms で次へ進み、
  落ちた ping は 1 秒待つので、欠落の数 ≒ 止まっていた秒数(分解能 1 秒)。
  出力= 先頭と末尾の時刻・記号の内訳(! . U など)・最長の連続欠落・Success rate の行。
資格情報は環境変数 NODE_USER/NODE_PASS(poc/xr/env.sh)。
"""
import os
import re
import sys
import time

import paramiko

host, dst, src = sys.argv[1:4]
count = int(sys.argv[4]) if len(sys.argv) > 4 else 20000
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=os.environ["NODE_USER"], password=os.environ["NODE_PASS"],
          look_for_keys=False, allow_agent=False, timeout=15)
sh = c.invoke_shell(width=250, height=1000)
PROMPT = re.compile(r"\n[\w\-]+[#>]\s*$")


def read(timeout):
    buf, t0 = "", time.time()
    while time.time() - t0 < timeout:
        if sh.recv_ready():
            buf += sh.recv(65535).decode("utf-8", "replace")
            if PROMPT.search(buf.replace("\r", "")):
                return buf
        else:
            time.sleep(0.05)
    return buf + "\n!! timeout"


read(10)
sh.send("terminal length 0\n")
read(10)
t0 = time.time()
print(f"== start {time.strftime('%T')} ping {dst} source {src} repeat {count} timeout 1", flush=True)
sh.send(f"ping {dst} source {src} repeat {count} timeout 1\n")
out = read(1800).replace("\r", "")
t1 = time.time()
body = "".join(ln for ln in out.splitlines() if re.fullmatch(r"[!.UQMA&?]+", ln.strip() or "x"))
runs = [len(m.group(0)) for m in re.finditer(r"[^!]+", body)]
kinds = {k: body.count(k) for k in sorted(set(body))}
rate = next((ln for ln in out.splitlines() if "Success rate" in ln), "(no summary)")
print(f"== end {time.strftime('%T')} elapsed {t1 - t0:.1f}s symbols {kinds} longest_gap {max(runs, default=0)} gaps {runs}")
print(rate)
c.close()
