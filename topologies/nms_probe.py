#!/usr/bin/env python3
"""NMS(Linux の収集役)の側から、機器が送ったもの・受け付けるものを確かめる採点の道具(BL-246 XR トラック M13)。

採点のチェックで `exec: local` を指定すると、`_grade_attempt.yml` がこれを採点機で実行し、出力をそのまま採点に回す。
行き先は管理 IF(`topologies/_generated/<ID>/mgmt_map.yml`)。資格情報は環境変数 LAB_USER / LAB_PASS。
接続・CLI の送り方は topologies/login_probe.py の部品を使う。

使い方:
  nms_probe.py <ID> linux <NODE> -- 'cmd' ...
      Linux ノードでコマンドを順に実行する(bash -lc)。各コマンドの前に `== CMD <n> rc=<rc>: <cmd>` を出す。
  nms_probe.py <ID> gnmi <CLIENT> <TARGET:PORT> [--cert DIR]
      CLIENT(Linux)から gnmic の capabilities を 3 通りで試す: 平文(--insecure)・TLS で証明書なし(--skip-verify)・
      TLS でクライアント証明書あり(DIR/client.pem・client.key。既定 DIR= ~/pki)。
      `== GNMI plain OK|FAIL`・`== GNMI tls-nocert OK|FAIL`・`== GNMI tls-cert OK|FAIL` を出す(FAIL は理由の 1 行つき)。
  nms_probe.py <ID> mdt <CLIENT> <FILE> --source NAME --sub SUB [--within S] [--iface IF] [--fresh W]
      telegraf の JSON の出力(FILE)の末尾から、tags.source=NAME・tags.subscription=SUB で直近 S 秒(既定 60)の行を数える。
      --fresh W を付けると、FILE の大きさを控えて W 秒待ち、その間に書き足された行だけを読む(確認を押す前に届いた行を数えない)。
      `== MDT RECENT n`・計測の名前ごとの数・IF の数(パケットの数のフィールドがあるか)`== MDT IF <IF> PACKETS yes|no` を出す。
  nms_probe.py <ID> flow <FROM> <SRC_IF> <DST> <COLLECTOR> <DIR> [--count N] [--wait S]
      FROM(IOS)から DST へ、乱数で選んだ大きさ(600〜899 バイト)で N 発(既定 37)の ping を送り、COLLECTOR の nfdump で
      DIR を読んで、その大きさ(1 パケットのバイト数)で SRC_IF のアドレス → DST のフローのパケット数を足す。
      大きさは DIR にまだ無い値から選び、読むのは確認を始めた後に書き終わったファイルだけ(前の確認のフローを数えない)。
      最大 S 秒(既定 150)まで 10 秒おきに読み直す。`== SENT n SIZE s FROM a`・`== FLOW PACKETS p`(見つからなければ 0)を出す。
  nms_probe.py <ID> netconf <CLIENT> <HOST> [--port P]
      CLIENT(Linux)の ncclient で HOST の NETCONF(既定 830)に入り、hello を受け取る。
      `== NETCONF OK capabilities=<n> candidate=yes|no` か `== NETCONF FAIL: <理由>` を出す。
  nms_probe.py <ID> xr-commit <NODE> '<regex>'
      IOS XR の NODE のコミット履歴(新しい順)から、変更の差分が regex に一致する最新のコミットを探し、
      `== COMMIT <ID> line=<Line> client=<Client>`(見つからなければ `== COMMIT NOT FOUND`)を出す。
      NETCONF で入れた変更は line=netconf・client=YANG Frame、gNMI は line=ems、CLI は line=vty…・client=CLI。
  nms_probe.py <ID> trap <NODE> <IF> <COLLECTOR> <LOG> [--wait S]
      COLLECTOR の LOG の行数を控え、NODE(IOS XR)の IF を shutdown → commit → no shutdown → commit し、S 秒(既定 15)待って
      新しく増えた行を出す。`== TRAPS linkDown=a linkUp=b`(IF の名前を含むものだけ数える)を出す。
"""
import os
import random
import re
import shlex
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from login_probe import Shell, connect, mgmt_ip  # noqa: E402


def lx(c, cmd, timeout=120):
    _, out, err = c.exec_command("bash -lc " + shlex.quote(cmd), timeout=timeout)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    return out.channel.recv_exit_status(), o, e


def do_linux(pid, node, user, pw, cmds):
    c = connect(mgmt_ip(pid, node), user, pw)
    for i, cmd in enumerate(cmds, 1):
        rc, o, e = lx(c, cmd)
        print(f"== CMD {i} rc={rc}: {cmd}")
        if o.strip():
            print(o.rstrip("\n"))
        if e.strip():
            print(e.rstrip("\n"))
    c.close()


def do_gnmi(pid, client, target, certdir, user, pw):
    c = connect(mgmt_ip(pid, client), user, pw)
    base = f"timeout 25 gnmic -a {target} -u {shlex.quote(user)} -p {shlex.quote(pw)} -e json_ietf"
    tries = [
        ("plain", f"{base} --insecure capabilities"),
        ("tls-nocert", f"{base} --skip-verify capabilities"),
        ("tls-cert", f"{base} --skip-verify --tls-cert {certdir}/client.pem --tls-key {certdir}/client.key capabilities"),
    ]
    for name, cmd in tries:
        rc, o, e = lx(c, cmd + " 2>&1 | head -3")
        text = (o + e).strip()
        if "gNMI version" in text:
            print(f"== GNMI {name} OK")
        else:
            why = next((ln for ln in text.splitlines() if "failed" in ln or "error" in ln), text.splitlines()[0] if text else "no output")
            why = re.sub(r"-p \S+", "-p ***", why)
            print(f"== GNMI {name} FAIL: {why[:220]}")
    c.close()


MDT_PY = r'''
import json, sys, time
f, src, sub, within, iface, offset = sys.argv[1:7]
now = time.time()
try:
    with open(f, "rb") as fh:
        off = int(offset)
        if off >= 0:
            fh.seek(0, 2)
            fh.seek(off if fh.tell() >= off else 0)
        lines = fh.read().decode("utf-8", "replace").splitlines()[-4000:]
except OSError as e:
    print(f"== MDT FILE ERROR {e}"); sys.exit(0)
n = 0; names = {}; pk = False
for ln in lines:
    try:
        d = json.loads(ln)
    except ValueError:
        continue
    t = d.get("tags", {})
    if t.get("source") != src or t.get("subscription") != sub or now - d.get("timestamp", 0) > float(within):
        continue
    n += 1
    names[d.get("name")] = names.get(d.get("name"), 0) + 1
    if iface in t.values() and any(("pkts" in k or "packets" in k) for k in d.get("fields", {})):
        pk = True
print(f"== MDT RECENT {n}")
for k, v in sorted(names.items()):
    print(f"   {k}: {v}")
print(f"== MDT IF {iface} PACKETS {'yes' if pk else 'no'}")
'''


def do_mdt(pid, client, path, source, sub, within, iface, fresh, user, pw):
    c = connect(mgmt_ip(pid, client), user, pw)
    offset = -1
    if fresh > 0:
        rc, o, e = lx(c, f"stat -c %s {shlex.quote(path)} 2>/dev/null || echo 0")
        offset = int((o.strip().splitlines() or ["0"])[-1] or 0)
        print(f"== MDT FRESH: reading what arrives in the next {fresh} s (from byte {offset})")
        time.sleep(fresh)
    rc, o, e = lx(c, "python3 -c " + shlex.quote(MDT_PY) + " " + " ".join(shlex.quote(x) for x in (path, source, sub, str(within), iface, str(offset))))
    print(o.rstrip("\n"))
    if e.strip():
        print(e.rstrip("\n"))
    c.close()


NC_PY = r'''
import sys
from ncclient import manager
host, port, user, pw = sys.argv[1:5]
try:
    m = manager.connect(host=host, port=int(port), username=user, password=pw, hostkey_verify=False,
                        look_for_keys=False, allow_agent=False, device_params={"name": "iosxr"}, timeout=30)
    caps = list(m.server_capabilities)
    cand = any(c.startswith("urn:ietf:params:netconf:capability:candidate") for c in caps)
    print(f"== NETCONF OK capabilities={len(caps)} candidate={'yes' if cand else 'no'}")
    m.close_session()
except Exception as e:
    print(f"== NETCONF FAIL: {type(e).__name__}: {str(e)[:200]}")
'''


def do_netconf(pid, client, host, port, user, pw):
    c = connect(mgmt_ip(pid, client), user, pw)
    rc, o, e = lx(c, "python3 -c " + shlex.quote(NC_PY) + " " + " ".join(shlex.quote(x) for x in (host, str(port), user, pw)), timeout=90)
    print((o.strip() or e.strip().splitlines()[-1] if (o.strip() or e.strip()) else "== NETCONF FAIL: no output"))
    c.close()


def do_flow(pid, frm, src_if, dst, collector, d, count, wait, user, pw):
    ios = connect(mgmt_ip(pid, frm), user, pw)
    sh = Shell(ios)
    addr = re.search(r"Internet address is (\d+\.\d+\.\d+\.\d+)", sh.send(f"show interfaces {src_if} | include Internet address"))
    src = addr.group(1) if addr else "0.0.0.0"
    c = connect(mgmt_ip(pid, collector), user, pw)
    rc, o, e = lx(c, "date +%s")
    t_start = int(o.strip() or 0)
    # 大きさは DIR にまだ無い値から選ぶ(前の確認のフローと取り違えない)
    for _ in range(20):
        size = random.randint(600, 899)
        rc, o, e = lx(c, f"nfdump -R {shlex.quote(d)} -q -o 'fmt:%pkt' "
                         f"{shlex.quote(f'src ip {src} and dst ip {dst} and bpp = {size}')} 2>/dev/null")
        if not re.search(r"^\s*\d+\s*$", o, re.M):
            break
    out = sh.send(f"ping {dst} source {src_if} repeat {count} size {size} timeout 1", timeout=120)
    ok = re.search(r"Success rate is (\d+) percent \((\d+)/(\d+)\)", out)
    ios.close()
    print(f"== SENT {count} SIZE {size} FROM {src}" + (f" (success {ok.group(2)}/{ok.group(3)})" if ok else " (no ping result)"))
    flt = f"src ip {src} and dst ip {dst} and bpp = {size}"
    # 確認を始めた後に書き終わったファイルだけを読む(nfcapd は 1 分ごとにファイルを閉じる)
    rd = (f"for f in $(find {shlex.quote(d)} -maxdepth 1 -type f -name 'nfcapd.[0-9]*' -newermt @{t_start} | sort); do "
          f"nfdump -r \"$f\" -q -o 'fmt:%pkt' {shlex.quote(flt)} 2>/dev/null; done; "
          f"find {shlex.quote(d)} -maxdepth 1 -type f -name 'nfcapd.[0-9]*' -newermt @{t_start} | wc -l")
    t0, pkts, nf = time.time(), 0, 0
    while True:
        rc, o, e = lx(c, rd)
        ls = o.strip().splitlines()
        nf = int(ls[-1]) if ls and ls[-1].strip().isdigit() else 0
        pkts = sum(int(x) for x in ls[:-1] if x.strip().isdigit())
        if pkts >= count or time.time() - t0 > wait:
            break
        time.sleep(10)
    print(f"== FLOW PACKETS {pkts} (filter: {flt}; files written after the check started: {nf}; waited {time.time() - t0:.0f}s)")
    c.close()


def do_trap(pid, node, ifname, collector, log, wait, user, pw):
    c = connect(mgmt_ip(pid, collector), user, pw)
    rc, o, e = lx(c, f"wc -l < {shlex.quote(log)}")
    base = int(o.strip() or 0)
    xr = connect(mgmt_ip(pid, node), user, pw)
    sh = Shell(xr)
    for ln in ("configure", f"interface {ifname}", "shutdown", "commit"):
        sh.send(ln, timeout=60)
    time.sleep(4)
    for ln in ("no shutdown", "commit", "end"):
        sh.send(ln, timeout=60)
    xr.close()
    time.sleep(wait)
    rc, o, e = lx(c, f"tail -n +{base + 1} {shlex.quote(log)} | tr -d '\\000'")
    c.close()
    text = o.strip()
    print(text[-3000:] if text else "(no new lines)")
    blocks = re.split(r"\n(?=\d{4}-\d\d-\d\d )", text) if text else []
    down = sum(1 for b in blocks if re.search(r"1\.3\.6\.1\.6\.3\.1\.1\.5\.3\b", b) and ifname in b)
    up = sum(1 for b in blocks if re.search(r"1\.3\.6\.1\.6\.3\.1\.1\.5\.4\b", b) and ifname in b)
    print(f"== TRAPS linkDown={down} linkUp={up}")


def do_xr_commit(pid, node, pattern, user, pw):
    xr = connect(mgmt_ip(pid, node), user, pw)
    sh = Shell(xr)
    out = sh.send("show configuration commit list", timeout=60)
    rows = re.findall(r"^\s*\d+\s+(\d{10})\s+(\S+)\s+(\S+)\s+(.+?)\s+\w{3} \w{3}\s+\d+ [\d:]+ \d{4}\s*$", out, re.M)
    found = None
    for cid, _user, line, client in rows[:25]:
        ch = sh.send(f"show configuration commit changes {cid}", timeout=60)
        if re.search(pattern, ch):
            found = (cid, line, client.strip())
            break
    xr.close()
    print(f"== COMMIT {found[0]} line={found[1]} client={found[2]}" if found else "== COMMIT NOT FOUND")


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        if name in a:
            i = a.index(name)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return default

    user, pw = os.environ["LAB_USER"], os.environ["LAB_PASS"]
    certdir = opt("--cert", "~/pki")
    within = opt("--within", "60")
    fresh = int(opt("--fresh", "0") or 0)
    iface = opt("--iface", "GigabitEthernet0/0/0/0")
    source, sub = opt("--source"), opt("--sub")
    count, wait = int(opt("--count", "37")), int(opt("--wait", "0") or 0)
    opt_port = opt("--port", "830")
    cmds = []
    if "--" in a:
        i = a.index("--")
        cmds, a = a[i + 1:], a[:i]
    pid, mode = a[0], a[1]
    if mode == "linux":
        do_linux(pid, a[2], user, pw, cmds)
    elif mode == "gnmi":
        do_gnmi(pid, a[2], a[3], certdir, user, pw)
    elif mode == "mdt":
        do_mdt(pid, a[2], a[3], source, sub, within, iface, fresh, user, pw)
    elif mode == "flow":
        do_flow(pid, a[2], a[3], a[4], a[5], a[6], count, wait or 150, user, pw)
    elif mode == "netconf":
        do_netconf(pid, a[2], a[3], opt_port, user, pw)
    elif mode == "xr-commit":
        do_xr_commit(pid, a[2], a[3], user, pw)
    elif mode == "trap":
        do_trap(pid, a[2], a[3], a[4], a[5], wait or 15, user, pw)
    else:
        sys.exit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
