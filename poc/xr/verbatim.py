#!/usr/bin/env python3
"""learn.yml の模範解を逐語で XR に流す(E2E 用)。usage: verbatim.py <問題 ID> <XR の管理 IP> [課題 id …](既定= 全部)
各課題の solution.en の先頭から `end` の行までを、字下げを含めてそのまま 1 行ずつ送る。
出力= 課題ごとに「<id> <行数> lines problems: [エラーの出た行]」。資格情報は NODE_USER/NODE_PASS(poc/xr/env.sh)。"""
import os
import subprocess
import sys

import yaml

pid, host, *want = sys.argv[1:]
repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
learn = yaml.safe_load(open(f"{repo}/problems/{pid}/learn.yml", encoding="utf-8"))
for st in learn["steps"]:
    if want and st["id"] not in want:
        continue
    lines = []
    for ln in st["solution"]["en"].splitlines():
        lines.append(ln)
        if ln.strip() == "end":
            break
    out = subprocess.run([f"{repo}/.venv/bin/python", f"{repo}/poc/xr/xrsh.py", host, *lines],
                         capture_output=True, text=True).stdout
    bad = [l for l in out.splitlines() if l.startswith("%") or "Invalid input" in l or "failed" in l.lower()]
    print(st["id"], len(lines), "lines problems:", bad)
