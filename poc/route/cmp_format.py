#!/usr/bin/env python3
"""BL-271 PoC: 記録した実機の show ip route(logs/all-*.log)と route_model.show_ip_route を行ごとに比べる(オフライン)。
  cmp_format.py logs/all-2.log
"""
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive  # noqa: E402
rm = drive.rm


def real_tables(log):
    """{(case, R): text}(Codes の凡例の後ろ・空行を除く)"""
    out, case, cur, buf = {}, None, None, []
    for line in Path(log).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^======== (\w+):", line)
        if m:
            case = m.group(1)
            continue
        m = re.match(r"^### (R\d): show ip route$", line)
        if m:
            cur, buf = (case, m.group(1)), []
            continue
        if cur and line.startswith("### ") or (cur and line.startswith("######## ")):
            out[cur] = buf
            cur = None
            continue
        if cur is not None:
            buf.append(line)
    res = {}
    for k, lines in out.items():
        i = next((n for n, l in enumerate(lines) if l.startswith("Gateway of last resort")), 0)
        res[k] = [l.rstrip() for l in lines[i:] if l.strip()]
    return res


def main():
    nw, ix = drive.board()
    real = real_tables(sys.argv[1])
    ndiff = 0
    for (case, r), lines in sorted(real.items()):
        c = drive.CASES.get(case)
        if not c:
            continue
        t = rm.tables(ix, c["cfg"], c.get("down", ()))
        txt = rm.show_ip_route(t[r], codes=False)
        txt = txt.replace("GigabitEthernet0/0", "Ethernet0/0").replace("GigabitEthernet0/1", "Ethernet0/1") \
                 .replace("GigabitEthernet0/2", "Ethernet0/2").replace("GigabitEthernet0/3", "Ethernet1/0")
        mod = [l.rstrip() for l in txt.splitlines() if l.strip()]
        if mod != lines:
            ndiff += 1
            print(f"==== {case} {r}")
            for d in difflib.unified_diff(lines, mod, "実機", "計算器", lineterm="", n=0):
                print(d)
    print(f"書式の違い: {ndiff} 件 / {len(real)} 表")


if __name__ == "__main__":
    main()
