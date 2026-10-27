#!/usr/bin/env python3
"""learn.yml の模範解を逐語で XR に流す(E2E 用)。usage: verbatim.py <問題 ID> <XR の管理 IP> [課題 id …](既定= 全部)
各課題の solution.en の先頭から `end` の行までを、字下げを含めてそのまま 1 行ずつ送る。
模範解に「On XR02:」のような見出しの行があれば(学ぶ側が XR を 2 台以上設定する課題)、見出しごとに
`configure` 〜 `end` の塊をその機器へ送る(管理 IP は topologies/_generated/<ID>/mgmt_map.yml から引く。見出しの無い塊は引数の IP へ)。
出力= 課題ごと(塊ごと)に「<id>[@機器] <行数> lines problems: [エラーの出た行]」。資格情報は NODE_USER/NODE_PASS(poc/xr/env.sh)。"""
import os
import re
import subprocess
import sys

import yaml

pid, host, *want = sys.argv[1:]
repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
learn = yaml.safe_load(open(f"{repo}/problems/{pid}/learn.yml", encoding="utf-8"))
HEAD = re.compile(r"^On (XR\d+):\s*$")


def mgmt(dev):
    path = f"{repo}/topologies/_generated/{pid}/mgmt_map.yml"
    return str((yaml.safe_load(open(path, encoding="utf-8")) or {})[dev])


def blocks(sol):
    """[(機器 or None, 行の列)]。見出しが無ければ先頭から最初の end まで(従来どおり)。"""
    lines = sol.splitlines()
    if not any(HEAD.match(ln) for ln in lines):
        out = []
        for ln in lines:
            out.append(ln)
            if ln.strip() == "end":
                break
        return [(None, out)]
    res, dev, cur = [], None, None
    for ln in lines:
        if cur is None:
            m = HEAD.match(ln)
            if m:
                dev = m.group(1)
            elif ln.strip() == "configure":
                cur = [ln]
            continue
        cur.append(ln)
        if ln.strip() == "end":
            res.append((dev, cur))
            cur = None
    return res


for st in learn["steps"]:
    if want and st["id"] not in want:
        continue
    for dev, lines in blocks(st["solution"]["en"]):
        target = mgmt(dev) if dev else host
        out = subprocess.run([f"{repo}/.venv/bin/python", f"{repo}/poc/xr/xrsh.py", target, *lines],
                             capture_output=True, text=True).stdout
        bad = [l for l in out.splitlines() if l.startswith("%") or "Invalid input" in l or "failed" in l.lower()]
        print(st["id"] + (f"@{dev}" if dev else ""), len(lines), "lines problems:", bad)
