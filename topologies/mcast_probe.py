#!/usr/bin/env python3
"""採点機からマルチキャストの配信を確かめる道具(BL-257 XR トラック M14)。

採点のチェックで `exec: local` を指定して使う(login_probe.py と同じく、行き先は管理 IF・資格情報は LAB_USER / LAB_PASS)。
「受信者のホスト役に参加の行を入れる → 待つ → 慣らしの数発 → 送信元から送る → 返事を返したホストごとに数える → show →
参加の行を外す」を 1 回の実行でまとめる(採点の正規表現は `== REPLY …` の行の数をそのまま照合する)。

★確認ごとに、範囲の中から乱数でグループを選ぶ(--group)。健全な時に参加させたグループの Join の名残(最大 210 秒)や
  下流のルータの (S,G) の Join にまぎれて、壊れていても届いてしまうのを避けるため(design §31.5 の教訓)。

使い方:
  mcast_probe.py <ID> run [--group NAME=PREFIX]… [--pre-cli 'NODE:line;;line']… [--settle N]
                          [--warm 'NODE:ping …']… [--send 'NODE:ping …']… [--from ADDR]… [--wait N]
                          [--show 'NODE:command']… [--rporder 'NODE:RANGE']… [--post-cli 'NODE:line;;line']…
  順番= --group → --pre-cli → --settle 秒 → --warm → --send(上から順に)→ --wait 秒 → --show → --rporder → --post-cli(必ず)。
    --group   … NAME=PREFIX(例 G=239.16.0.0/16・G6=FF0E::16:0/112)。範囲の中のアドレスを乱数で選び、ほかの引数の {NAME} に入れる。
                `== GROUP NAME <アドレス>` を出す。IPv4 は最後のオクテットに 0 と 255 を選ばない。
    --pre-cli … ホスト役(IOS)の参加の行など(`;;` で区切る)。--post-cli は外す行(失敗しても必ず実行)。
    --warm    … 慣らしの送信(木を作らせる。数えない)。
    --send    … 送信元のホスト役の ping。`== SEND <NODE>: <行> => <Success の行>` と、返事を返したアドレスごとに
                `== REPLY <NODE> <アドレス> <n>`(n= 返事のあった要求の数)。--from に挙げたアドレスは 0 でも出す。
                IPv6 のマルチキャストの ping が聞く「Output Interface:」には --oif(既定 Ethernet0/0)で答える。
    --show    … コマンドの出力をそのまま出す(`== SHOW <NODE>: <command>` の後に続ける)。
    --rporder … NODE の Group-to-RP の対応表(XR= show pim rp mapping・IOS= show ip pim rp mapping)から、RANGE を BSR で
                学んだ候補 RP を priority の小さい順に並べて `== RPORDER <NODE> <RANGE> a,b,c` を出す(同点は `=` でつなぐ・
                無ければ none)。候補の選ばれ方(小さい方が勝つ)を、数を比べずに正規表現で見るため。
"""
import ipaddress
import os
import random
import re
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from login_probe import REPO, Shell, connect, mgmt_ip  # noqa: E402


def session(pid, node, user, pw):
    return Shell(connect(mgmt_ip(pid, node), user, pw))


def is_xr(pid, node):
    try:
        meta = yaml.safe_load(open(os.path.join(REPO, "problems", pid, "problem.yml"), encoding="utf-8"))
    except OSError:
        return False
    return (meta.get("node_image_families") or {}).get(node) == "iosxr"


def pick(prefix):
    net = ipaddress.ip_network(prefix, strict=False)
    for _ in range(1000):
        host = random.randrange(1, net.num_addresses - 1) if net.num_addresses > 2 else 0
        addr = net[host]
        if net.version == 4 and (int(addr) & 0xFF) in (0, 255):
            continue
        return addr.compressed
    raise ValueError(f"no address in {prefix}")


def subst(text, groups):
    for k, v in groups.items():
        text = text.replace("{" + k + "}", v)
    return text


def norm(addr):
    try:
        return ipaddress.ip_address(addr).compressed
    except ValueError:
        return addr.lower()


def run_lines(pid, spec, user, pw, tag):
    node, rest = spec.split(":", 1)
    lines = [ln for ln in rest.split(";;") if ln.strip()]
    try:
        sh = session(pid, node, user, pw)
        for ln in lines:
            sh.send(ln, timeout=60)
        sh.sh.close()
        print(f"== {tag} {node}: {len(lines)} lines", flush=True)
    except Exception as e:  # 失敗も出力に残す(採点はそのチェックが落ちるだけ)
        print(f"== {tag} {node} FAILED: {type(e).__name__}: {e}", flush=True)


def ping(pid, spec, user, pw, oif, count_from=None, report=True):
    node, line = spec.split(":", 1)
    try:
        sh = session(pid, node, user, pw)
        out = sh.send(line, timeout=180, until=r"Output Interface:\s*$")
        if re.search(r"Output Interface:\s*$", out):
            out += sh.send(oif, timeout=180)
        sh.sh.close()
    except Exception as e:
        print(f"== SEND {node} FAILED: {type(e).__name__}: {e}", flush=True)
        return
    if not report:
        print(f"== WARM {node}: {line}", flush=True)
        return
    m = re.search(r"Success rate is .*", out)
    print(f"== SEND {node}: {line} => {m.group(0) if m else out.strip().splitlines()[-1:]}", flush=True)
    seen = {}
    for req, addr in re.findall(r"Reply to request (\d+) (?:received )?from ([0-9A-Fa-f.:]+)", out):
        seen.setdefault(norm(addr), set()).add(req)
    for addr in (count_from or []):
        seen.setdefault(norm(addr), set())
    for addr in sorted(seen):
        print(f"== REPLY {node} {addr} {len(seen[addr])}", flush=True)


def show(pid, spec, user, pw):
    node, cmd = spec.split(":", 1)
    try:
        sh = session(pid, node, user, pw)
        out = sh.send(cmd, timeout=120)
        sh.sh.close()
    except Exception as e:
        print(f"== SHOW {node} FAILED: {type(e).__name__}: {e}", flush=True)
        return
    print(f"== SHOW {node}: {cmd}")
    print(out.strip(), flush=True)


def rp_mapping(out):
    """Group-to-RP の対応表(XR と IOS)から (グループ, RP, 学び方, priority) を取り出す。"""
    rows, grp, rp = [], None, None
    for ln in out.splitlines():
        m = re.match(r"\s*Group\(s\)\s+(\S+)", ln)
        if m:
            grp, rp = m.group(1).rstrip(","), None
            continue
        m = re.match(r"\s*RP\s+([0-9A-Fa-f.:]+)", ln)
        if m:
            rp = norm(m.group(1))
            continue
        m = re.search(r"Info source:.*?via (\w+)(?:.*?priority (\d+))?", ln)
        if m and grp and rp:
            rows.append((grp, rp, m.group(1), int(m.group(2)) if m.group(2) else None))
    return rows


def rporder(pid, spec, user, pw):
    node, rng = spec.split(":", 1)
    cmd = "show pim rp mapping" if is_xr(pid, node) else "show ip pim rp mapping"
    try:
        sh = session(pid, node, user, pw)
        out = sh.send(cmd, timeout=120)
        sh.sh.close()
    except Exception as e:
        print(f"== RPORDER {node} FAILED: {type(e).__name__}: {e}", flush=True)
        return
    want = ipaddress.ip_network(rng, strict=False)
    cands = {}
    for grp, rp, via, prio in rp_mapping(out):
        try:
            g = ipaddress.ip_network(grp, strict=False)
        except ValueError:
            continue
        if g == want and via in ("bsr", "bootstrap") and prio is not None:
            cands[rp] = prio
    if not cands:
        print(f"== RPORDER {node} {rng} none", flush=True)
        return
    parts = []
    for prio in sorted(set(cands.values())):
        parts.append("=".join(sorted(rp for rp, p in cands.items() if p == prio)))
    print(f"== RPORDER {node} {rng} {','.join(parts)}", flush=True)


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[1] != "run":
        print(__doc__)
        return 2
    pid = args[0]
    user = os.environ.get("LAB_USER") or os.environ["NODE_USER"]
    pw = os.environ.get("LAB_PASS") or os.environ["NODE_PASS"]

    def opts(name):
        return [args[i + 1] for i, a in enumerate(args) if a == name and i + 1 < len(args)]

    def opt(name, default=None):
        v = opts(name)
        return v[-1] if v else default

    groups = {}
    for spec in opts("--group"):
        name, prefix = spec.split("=", 1)
        groups[name] = pick(prefix)
        print(f"== GROUP {name} {groups[name]}", flush=True)
    oif = opt("--oif", "Ethernet0/0")
    count_from = [subst(a, groups) for a in opts("--from")]
    try:
        for spec in opts("--pre-cli"):
            run_lines(pid, subst(spec, groups), user, pw, "PRE")
        time.sleep(float(opt("--settle", "10")))
        for spec in opts("--warm"):
            ping(pid, subst(spec, groups), user, pw, oif, report=False)
        if opts("--warm"):
            time.sleep(3)
        for spec in opts("--send"):
            ping(pid, subst(spec, groups), user, pw, oif, count_from)
        time.sleep(float(opt("--wait", "0")))
        for spec in opts("--show"):
            show(pid, subst(spec, groups), user, pw)
        for spec in opts("--rporder"):
            rporder(pid, subst(spec, groups), user, pw)
    finally:
        for spec in opts("--post-cli"):
            run_lines(pid, subst(spec, groups), user, pw, "POST")
    return 0


if __name__ == "__main__":
    sys.exit(main())
