#!/usr/bin/env python3
"""Catalyst 8000V のライセンスの段階(boot level)を上げて再起動する(BL-246 XR トラック M11 追補)。

8000V は既定の段階(`show version` の `License Level:` が空欄)では MPLS のコマンド自体が無い。
`license boot level <段階>` を設定して保存し、再起動すると使えるようになる(登録は不要・2026-11-01 実測)。
problem.yml に次を書いた問題だけが対象(lab_up.yml が構築の最後に呼ぶ):

  xe_license_boot:
    level: network-advantage addon dna-advantage
    nodes: [XE1, XE2, XE3]

  xe_license.py --repo <リポ> --problem <ID> [--nodes XE1,…]

各ノードを並行に処理する: 管理 IF の SSH が開くのを待つ → 段階がそろっていれば何もしない → そろっていなければ
設定(day0 に同じ行があれば済んでいる)・保存・再起動 → SSH が戻るのを待って段階を確かめる。
再起動の後、day0 の設定のうち段階が上がるまで受け付けられなかった行(mpls ip など)が効いているかを数え、
欠けていれば day0(topologies/_generated/<ID>/day0/<NODE>.cfg)を設定モードで流し直して保存する。
接続は管理 IF の SSH(採点と同じ経路)。資格情報は環境変数 NODE_USER / NODE_PASS。
"""
import argparse
import os
import re
import sys
import threading
import time

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from login_probe import Shell, connect  # noqa: E402

LOCK = threading.Lock()


def log(node, msg):
    with LOCK:
        print(f"[{node}] {msg}", flush=True)


def login(host, wait):
    """SSH が開いて CLI が使えるまで待つ(wait 秒まで)。"""
    t0 = time.time()
    while True:
        try:
            c = connect(host, os.environ["NODE_USER"], os.environ["NODE_PASS"])
            sh = Shell(c)
            return c, sh
        except Exception:
            if time.time() - t0 >= wait:
                raise
            time.sleep(15)


def levels(sh):
    out = sh.send("show version | include License Level", timeout=60)
    base = re.search(r"^License Level:\s*(\S*)", out, re.M)
    addon = re.search(r"^Addon License Level:\s*(\S*)", out, re.M)
    return (base.group(1) if base else ""), (addon.group(1) if addon else "")


def want_levels(level):
    w = level.split()
    return w[0], (w[w.index("addon") + 1] if "addon" in w else "")


def day0_lines(repo, problem, node):
    path = os.path.join(repo, "topologies/_generated", problem, "day0", f"{node}.cfg")
    return [ln.rstrip() for ln in open(path, encoding="utf-8")
            if ln.strip() and not ln.lstrip().startswith("!")]


def missing_mpls(sh, d0):
    """day0 の `mpls ip`(IF の下)の数と、いまの running-config の数を比べる。"""
    want = sum(1 for ln in d0 if ln.strip() == "mpls ip")
    out = sh.send("show running-config | include ^ mpls ip$", timeout=60)
    have = len(re.findall(r"^ mpls ip\s*$", out, re.M))
    return want, have


def reload(sh):
    out = sh.send("reload", timeout=30)
    if re.search(r"Save\?|\[yes/no\]", out):
        out += sh.send("no", timeout=30)
    if "[confirm]" in out:
        sh.sh.send("\n")
        time.sleep(5)


def handle(repo, problem, node, host, level, res):
    wb, wa = want_levels(level)
    try:
        c, sh = login(host, wait=1500)
        b, a = levels(sh)
        if (b, a) == (wb, wa):
            log(node, f"license level already {b} / {a}")
        else:
            log(node, f"license level '{b}' / '{a}' -> {level}: write and reload")
            for ln in ("configure terminal", f"license boot level {level}", "end"):
                sh.send(ln, timeout=60)
            out = sh.send("write memory", timeout=120)
            if "[OK]" not in out:
                log(node, "WARNING write memory did not answer [OK]")
            reload(sh)
            try:
                c.close()
            except Exception:
                pass
            time.sleep(90)              # 落ちきる前に古いセッションに当たらないように
            c, sh = login(host, wait=1500)
            b, a = levels(sh)
            if (b, a) != (wb, wa):
                log(node, f"ERROR license level is '{b}' / '{a}' after the reload")
                res[node] = False
                return
            log(node, f"license level now {b} / {a}")
        d0 = day0_lines(repo, problem, node)
        want, have = missing_mpls(sh, d0)
        if have < want:
            log(node, f"day0 lines missing after the reload (mpls ip {have}/{want}): applying day0 again")
            sh.send("configure terminal", timeout=60)
            for ln in d0:
                sh.send(ln, timeout=60)
            sh.send("end", timeout=60)
            sh.send("write memory", timeout=120)
            want, have = missing_mpls(sh, d0)
        log(node, f"mpls ip on {have}/{want} interfaces")
        res[node] = have >= want
        c.close()
    except Exception as e:
        log(node, f"ERROR {type(e).__name__}: {e}")
        res[node] = False


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--nodes")
    a = ap.parse_args()
    pmeta = yaml.safe_load(open(os.path.join(a.repo, "problems", a.problem, "problem.yml"), encoding="utf-8"))
    spec = pmeta.get("xe_license_boot") or {}
    nodes = spec.get("nodes") or []
    if a.nodes:
        nodes = [n for n in nodes if n in a.nodes.split(",")]
    if not nodes:
        print("no xe_license_boot nodes")
        return 0
    mgmt = yaml.safe_load(open(os.path.join(a.repo, "topologies/_generated", a.problem, "mgmt_map.yml"), encoding="utf-8"))
    res, th = {}, []
    for n in nodes:
        t = threading.Thread(target=handle, args=(a.repo, a.problem, n, str(mgmt[n]), spec["level"], res))
        t.start()
        th.append(t)
    for t in th:
        t.join()
    bad = [n for n in nodes if not res.get(n)]
    print("xe_license: " + ("all ok" if not bad else f"FAILED {','.join(bad)}"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
