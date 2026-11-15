#!/usr/bin/env python3
"""probe — TCP でつないでみて、どう返ってきたかを 1 語で出す(Junos トラック J2 の盤面・BL-275)。

  probe <宛先> <ポート> [-s <送信元>] [-w <秒>]

  open         つながった(相手が受け付けた)
  refused      相手の機器までは届いたが、そのポートで待つプログラムが無い(RST が返った)= 途中では捨てられていない
  timeout      <秒>(既定 3)待っても何も返らない= 途中で黙って捨てられた
  unreachable  ICMP の到達不能が返った(途中のルータが reject した・経路が無い など)

NET1・SRV1・FRR1 のシェルで使える(/usr/local/bin/probe)。採点も同じ道具で確かめる。
"""
import argparse
import errno
import socket
import time

ap = argparse.ArgumentParser(prog="probe", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("dst")
ap.add_argument("port", type=int)
ap.add_argument("-s", "--src", help="送信元のアドレス(機器が持つアドレスのどれか)")
ap.add_argument("-w", "--wait", type=float, default=3.0, help="待つ秒数(既定 3)")
a = ap.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(a.wait)
if a.src:
    s.bind((a.src, 0))
t0 = time.time()
try:
    s.connect((a.dst, a.port))
    word = "open"
except socket.timeout:
    word = "timeout"
except ConnectionRefusedError:
    word = "refused"
except OSError as e:
    word = f"unreachable ({e.strerror})" if e.errno in (errno.EHOSTUNREACH, errno.ENETUNREACH) else f"error ({e.strerror})"
finally:
    s.close()
src = f" from {a.src}" if a.src else ""
print(f"{word}  tcp {a.dst}:{a.port}{src}  {time.time() - t0:.2f}s")
