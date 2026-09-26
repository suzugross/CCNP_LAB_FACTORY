#!/usr/bin/env python3
"""results-raw.md → ケースごとの要点表(hub 登録数・ISAKMP 状態・ESP カウンタ・spoke 状態・NHS 応答・Tunnel 状態)。"""
import re
from pathlib import Path

raw = (Path(__file__).resolve().parent / "results-raw.md").read_text(encoding="utf-8")
blocks = re.findall(r"\*\*(.+?)\*\*\n\n```\n(.*?)```", raw, re.S)


def get(tag, who, cmd):
    for title, body in blocks:
        if title.startswith(f"{tag} {who}") and cmd in title:
            return body
    return ""


print("| ケース | hub 登録(UP) | hub ISAKMP(RT02) | hub ESP enc/dec | RT02 dmvpn State | RT02 NHS req/repl | Tunnel(hub/RT02) | hub ログの特徴 |")
print("|---|---|---|---|---|---|---|---|")
tags = sorted({t.split()[0] for t, _ in blocks if re.match(r"^[WF]\d+b? ", t)},
              key=lambda s: (s[0], int(re.sub(r"\D", "", s)), s))
for tag in tags:
    d = get(tag, "hub", "show dmvpn")
    ups = len(re.findall(r"\sUP\s", d))
    peers = re.search(r"NHRP Peers:(\d+)", d)
    isa = get(tag, "hub", "isakmp sa")
    st = [l.split()[2] for l in isa.splitlines() if "198.51.100.2 " in l and len(l.split()) > 3]
    ips = get(tag, "hub", "ipsec sa")
    enc = re.findall(r"#pkts encaps: (\d+)", ips)
    dec = re.findall(r"#pkts decaps: (\d+)", ips)
    sd = get(tag, "RT02", "show dmvpn")
    sst = [l.split()[3] for l in sd.splitlines() if re.match(r"\s+\d+\s+\S+\s+\S+\s+\S+\s", l)]
    nhs = get(tag, "RT02", "nhs detail")
    m = re.search(r"req-sent (\d+).*?repl-recv (\d+)", nhs)
    tu = []
    for who in ("hub", "RT02"):
        b = get(tag, who, "interface brief")
        mm = re.search(r"Tunnel0\s+\S+\s+\S+\s+\S+\s+(.+?)\s{2,}(\S+)", b)
        tu.append(f"{mm.group(1).strip()}/{mm.group(2)}" if mm else "?")
    log = get(tag, "hub log", "show logging")
    feats = sorted({m2 for m2 in re.findall(r"%([A-Z0-9_]+-\d-[A-Z0-9_]+)", log)})
    print(f"| {tag} | {ups} (peers {peers.group(1) if peers else '-'}) | {','.join(st) or '-'} | "
          f"{'/'.join(enc[:3]) or '-'} ; {'/'.join(dec[:3]) or '-'} | {','.join(sst) or '-'} | "
          f"{m.group(1) + '/' + m.group(2) if m else '-'} | {' ; '.join(tu)} | {', '.join(feats)[:120]} |")
