#!/usr/bin/env python3
"""採点機から BGP の運用機能を確かめる道具(BL-257 XR トラック M6 追補・XRT-17)。

採点のチェックで `exec: local` を指定して使う(login_probe.py と同じく、行き先は管理 IF・資格情報は LAB_USER / LAB_PASS)。
「設定を足す → 待つ → show → 故障を起こして途切れを測る/経路を揺らす → show → 足した設定を外す」を 1 回の実行でまとめる。

使い方:
  bgpops_probe.py <ID> run [--pre 'NODE:line;;line']… [--settle N] [--show 'NODE:command']…
                           [--failover 'CE:SRC:DST:XRNODE:IF'] [--recover N]
                           [--flap 'IOSNODE:PEER:PREFIX:N:GAP'] [--wait N] [--after 'NODE:command']…
                           [--post 'NODE:line;;line']… [--waitfor 'NODE|command|REGEX|秒']… [--postwait 'NODE|command|REGEX|秒']…
  順番= --pre → --settle 秒 → --waitfor → --show → --failover → --flap → --wait 秒 → --after → --post(必ず)→ --postwait。
    --waitfor/--postwait … command の出力が REGEX に合うまで 5 秒ごとに見る(上限の秒数まで)。`== WAITFOR <NODE> ok|timeout <秒>`。
                 決まった秒数を待つ代わり(BGP の張り直しや Idle (PfxCt) になるまでの時間は毎回ちがう・2026-11-21 の確認の教訓)。
    --pre/--post … 設定の行(`;;` で区切る)。XR は configure → 行 → commit → end、IOS は configure terminal → 行 → end。
                   `@` で始まる行は設定を抜けた後に実行モードで打つ(例 `@clear bgp 172.16.1.1`)。
    --show/--after … コマンドの出力をそのまま出す(`== SHOW <NODE>: <command>` の後に続ける)。
    --failover … CE(IOS)から DST へ IP SLA の udp-jitter(10 ms 間隔で 3000 発= 30 秒)を流し、3 秒後に XRNODE の IF を
                 shutdown して途切れを数え、測り終えたら no shutdown に戻す。DST には `ip sla responder` が要る。
                 `== FAILOVER PERIODS <p> MAXLEN <m> TAIL <t> VALID <0|1>`(m= いちばん長い途切れの発数= ×10 ms)。
                 ★XRd は CML のリンクの停止をキャリア断として検知しないため、リンクでなく IF の shutdown で起こす(design §32.3 #2)。
                 ★IOL の `Loss Source to Destination` は誤ることがあるので、途切れの長さ(Loss Period Length)を使う(#4)。
                 戻した後は --recover 秒(既定 60)待つ(IS-IS・LDP・BGP が戻るまで)。
    --flap … IOS の IOSNODE が PEER へ出す PREFIX を、出口の prefix-list の付け外しと soft out で N 回取り下げて戻す(間 GAP 秒)。
             ダンプニングの確認用(peer のリセットは揺れに数えないため)。終わったら prefix-list を外して消す。
"""
import os
import re
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from login_probe import REPO, Shell, connect, mgmt_ip  # noqa: E402


def is_xr(pid, node):
    try:
        meta = yaml.safe_load(open(os.path.join(REPO, "problems", pid, "problem.yml"), encoding="utf-8"))
    except OSError:
        return False
    return (meta.get("node_image_families") or {}).get(node) == "iosxr"


def session(pid, node, user, pw):
    return Shell(connect(mgmt_ip(pid, node), user, pw))


def apply(pid, spec, user, pw):
    node, _, body = spec.partition(":")
    lines = [ln for ln in body.split(";;") if ln.strip()]
    cfg = [ln for ln in lines if not ln.startswith("@")]
    ex = [ln[1:] for ln in lines if ln.startswith("@")]
    sh = session(pid, node, user, pw)
    out = ""
    if cfg:
        if is_xr(pid, node):
            for ln in ["configure"] + cfg + ["commit"]:
                out += sh.send(ln, timeout=60)
            out += sh.send("end", timeout=30)
            if re.search(r"\[(cancel|no|yes)\]:\s*$", out):  # コミットに失敗して end が確かめを求めた
                out += sh.send("no", timeout=30)
        else:
            for ln in ["configure terminal"] + cfg + ["end"]:
                out += sh.send(ln, timeout=60)
    for ln in ex:
        out += sh.send(ln, timeout=60)
    sh.sh.close()
    bad = [ln for ln in out.splitlines() if re.search(r"^%|% Invalid|% Incomplete|Failed to commit", ln)]
    print(f"== APPLY {node}: {len(cfg)} config / {len(ex)} exec" + (f"  !! {bad[0].strip()}" if bad else ""), flush=True)


def show(pid, spec, user, pw):
    node, _, cmd = spec.partition(":")
    sh = session(pid, node, user, pw)
    out = sh.send(cmd, timeout=90)
    sh.sh.close()
    print(f"== SHOW {node}: {cmd}")
    print(out.strip())


def failover(pid, spec, user, pw):
    ce, src, dst, xr, ifn = spec.split(":", 4)
    op = 77
    sh = session(pid, ce, user, pw)
    for ln in ["configure terminal", f"no ip sla {op}", f"ip sla {op}",
               f"udp-jitter {dst} 5000 source-ip {src} num-packets 3000 interval 10",
               "exit", f"ip sla schedule {op} life 120 start-time now", "end"]:
        sh.send(ln, timeout=30)
    time.sleep(3)
    apply(pid, f"{xr}:interface {ifn};;shutdown", user, pw)
    t_fault = time.time()
    time.sleep(30 + 8)
    out = sh.send(f"show ip sla statistics {op} details", timeout=30)
    apply(pid, f"{xr}:interface {ifn};;no shutdown", user, pw)
    for ln in ["configure terminal", f"no ip sla {op}", "end"]:
        sh.send(ln, timeout=30)
    sh.sh.close()
    per = re.search(r"Source to Destination Loss Periods Number:\s*(\d+)", out)
    plen = re.search(r"Source to Destination Loss Period Length Min/Max:\s*\d+/(\d+)", out)
    tail = re.search(r"Tail Drop:\s*(\d+)", out)
    valid = 0 if re.search(r"return code: No connection", out) or not per else 1
    print(f"== FAILOVER PERIODS {per.group(1) if per else -1} MAXLEN {plen.group(1) if plen else -1} "
          f"TAIL {tail.group(1) if tail else -1} VALID {valid}  (shutdown {xr} {ifn} after {t_fault:.0f})", flush=True)


def waitfor(pid, spec, user, pw):
    node, cmd, rx, limit = spec.split("|", 3)
    t0 = time.time()
    while True:
        sh = session(pid, node, user, pw)
        out = sh.send(cmd, timeout=60)
        sh.sh.close()
        if re.search(rx, out, re.M):
            print(f"== WAITFOR {node} ok {time.time() - t0:.0f}", flush=True)
            return
        if time.time() - t0 > int(limit):
            print(f"== WAITFOR {node} timeout {time.time() - t0:.0f}", flush=True)
            return
        time.sleep(5)


def flap(pid, spec, user, pw):
    node, peer, prefix, n, gap = spec.split(":")
    n, gap = int(n), int(gap)
    base = f"{node}:ip prefix-list PROBE-FLAP-DENY seq 5 deny {prefix};;ip prefix-list PROBE-FLAP-DENY seq 10 permit 0.0.0.0/0 le 32;;" \
           f"ip prefix-list PROBE-FLAP-ALL seq 5 permit 0.0.0.0/0 le 32"
    apply(pid, base, user, pw)
    for i in range(n):
        for pl in ("PROBE-FLAP-DENY", "PROBE-FLAP-ALL"):
            apply(pid, f"{node}:router bgp {asn(pid, node, user, pw)};;address-family ipv4;;neighbor {peer} prefix-list {pl} out;;"
                       f"@clear ip bgp {peer} soft out", user, pw)
            time.sleep(gap)
        print(f"== FLAP {i + 1}", flush=True)
    apply(pid, f"{node}:router bgp {asn(pid, node, user, pw)};;address-family ipv4;;no neighbor {peer} prefix-list PROBE-FLAP-ALL out;;"
               f"exit;;exit;;no ip prefix-list PROBE-FLAP-DENY;;no ip prefix-list PROBE-FLAP-ALL;;@clear ip bgp {peer} soft out", user, pw)


_ASN = {}


def asn(pid, node, user, pw):
    if node not in _ASN:
        sh = session(pid, node, user, pw)
        out = sh.send("show running-config | include ^router bgp", timeout=30)
        sh.sh.close()
        m = re.search(r"router bgp (\d+)", out)
        _ASN[node] = m.group(1) if m else "65100"
    return _ASN[node]


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[1] != "run":
        print(__doc__)
        sys.exit(2)
    pid = args[0]
    user, pw = os.environ.get("LAB_USER") or os.environ.get("NODE_USER"), os.environ.get("LAB_PASS") or os.environ.get("NODE_PASS")
    opts = {k: [] for k in ("--pre", "--show", "--after", "--post", "--waitfor", "--postwait")}
    single = {"--settle": "0", "--failover": None, "--recover": "60", "--flap": None, "--wait": "0"}
    i = 2
    while i < len(args):
        k = args[i]
        if k in opts:
            opts[k].append(args[i + 1])
        elif k in single:
            single[k] = args[i + 1]
        else:
            print(f"unknown option {k}")
            sys.exit(2)
        i += 2
    try:
        for s in opts["--pre"]:
            apply(pid, s, user, pw)
        time.sleep(int(single["--settle"]))
        for s in opts["--waitfor"]:
            waitfor(pid, s, user, pw)
        for s in opts["--show"]:
            show(pid, s, user, pw)
        if single["--failover"]:
            failover(pid, single["--failover"], user, pw)
            time.sleep(int(single["--recover"]))
        if single["--flap"]:
            flap(pid, single["--flap"], user, pw)
        time.sleep(int(single["--wait"]))
        for s in opts["--after"]:
            show(pid, s, user, pw)
    finally:
        for s in opts["--post"]:
            try:
                apply(pid, s, user, pw)
            except Exception as e:  # 片付けは続ける
                print(f"== POST FAILED {s.split(':')[0]}: {type(e).__name__}: {e}")
        for s in opts["--postwait"]:
            waitfor(pid, s, user, pw)


if __name__ == "__main__":
    main()
