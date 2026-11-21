#!/usr/bin/env python3
"""PoC: pcap(libpcap 形式・Ethernet)の IPv4 を送信元→宛先・TTL で数える(BL-257 M6 追補の GTSM)。usage: pcap_ttl.py <file.pcap>"""
import collections, struct, sys
d = open(sys.argv[1], "rb").read()
le = d[:4] == b"\xd4\xc3\xb2\xa1"
E = "<" if le else ">"
off, cnt = 24, collections.Counter()
while off + 16 <= len(d):
    _, _, incl, _ = struct.unpack(E + "IIII", d[off:off + 16]); off += 16
    p = d[off:off + incl]; off += incl
    et = struct.unpack(">H", p[12:14])[0]; ip = 14
    if et == 0x8100:
        et = struct.unpack(">H", p[16:18])[0]; ip = 18
    if et != 0x0800:
        continue
    ttl, src, dst = p[ip + 8], ".".join(map(str, p[ip + 12:ip + 16])), ".".join(map(str, p[ip + 16:ip + 20]))
    cnt[(src, dst, ttl)] += 1
for (s, t, ttl), n in sorted(cnt.items()):
    print(f"{n:5d}  {s:>15} -> {t:<15} ttl {ttl}")
