#!/usr/bin/env python3
"""PoC 用の小さなパケットの観察(J2・BL-275)。FRR のコンテナに tcpdump が無いので AF_PACKET で読む。
  python3 sniff.py <IF> <秒>   → ICMP は type/code、TCP はポートとフラグを 1 行ずつ出す(BGP の 179 番と ARP は出さない)"""
import socket
import struct
import sys
import time

ifname, secs = sys.argv[1], float(sys.argv[2])
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
s.bind((ifname, 0))
s.settimeout(0.5)
end = time.time() + secs
FL = "FSRPAUEC"
while time.time() < end:
    try:
        pkt = s.recv(65535)
    except socket.timeout:
        continue
    if struct.unpack("!H", pkt[12:14])[0] != 0x0800:
        continue
    ip = pkt[14:]
    ihl = (ip[0] & 15) * 4
    proto, src, dst = ip[9], socket.inet_ntoa(ip[12:16]), socket.inet_ntoa(ip[16:20])
    l4 = ip[ihl:]
    t = time.strftime("%H:%M:%S")
    if proto == 1:
        print(f"{t} ICMP {src} > {dst} type={l4[0]} code={l4[1]}", flush=True)
    elif proto == 6:
        sp, dp = struct.unpack("!HH", l4[:4])
        if 179 in (sp, dp):
            continue
        fl = "".join(c for i, c in enumerate(FL) if l4[13] >> i & 1)
        print(f"{t} TCP {src}:{sp} > {dst}:{dp} [{fl}]", flush=True)
