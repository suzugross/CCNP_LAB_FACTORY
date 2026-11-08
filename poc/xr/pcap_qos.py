#!/usr/bin/env python3
"""PoC(BL-246 M12): pcap の ICMP を 1 行ずつ「ラベル/TC(EXP)の積み方・DSCP・送信元>宛て・種類」で出す(scapy なし)。
usage: pcap_qos.py <file.pcap> [最大行数]"""
import struct, sys

DSCP = {0: "BE", 46: "EF", 10: "AF11", 12: "AF12", 14: "AF13", 18: "AF21", 26: "AF31", 34: "AF41", 48: "CS6", 56: "CS7",
        8: "CS1", 16: "CS2", 24: "CS3", 32: "CS4", 40: "CS5"}


def ip4(b):
    return ".".join(str(x) for x in b)


def main(path, limit):
    d = open(path, "rb").read()
    if len(d) < 24:
        print("(空)"); return
    end = "<" if d[:4] in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
    off, n = 24, 0
    while off + 16 <= len(d) and n < limit:
        _, _, incl, _ = struct.unpack(end + "IIII", d[off:off + 16]); off += 16
        p = d[off:off + incl]; off += incl
        et, i = struct.unpack("!H", p[12:14])[0], 14
        while et == 0x8100:
            et, i = struct.unpack("!H", p[i + 2:i + 4])[0], i + 4
        labels = []
        if et == 0x8847:
            while True:
                w = struct.unpack("!I", p[i:i + 4])[0]; i += 4
                labels.append(f"{w >> 12}/tc{(w >> 9) & 7}/ttl{w & 255}")
                if w & 0x100:
                    break
            if p[i] >> 4 != 4:
                continue
        elif et != 0x0800:
            continue
        ihl, tos, proto = (p[i] & 15) * 4, p[i + 1], p[i + 9]
        if proto != 1:
            continue
        typ = {8: "req", 0: "rep", 11: "ttl-exc", 3: "unreach"}.get(p[i + ihl], str(p[i + ihl]))
        ttl = p[i + 8]
        ds = tos >> 2
        stack = " | ".join(labels) if labels else "(ラベルなし)"
        print(f"{stack:44s} DSCP {DSCP.get(ds, ds)}(tos 0x{tos:02x}) ttl{ttl:<3d} {ip4(p[i + 12:i + 16])}>{ip4(p[i + 16:i + 20])} {typ}")
        n += 1


main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40)
