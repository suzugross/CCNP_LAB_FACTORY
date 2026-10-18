#!/usr/bin/env python3
"""IOS XR のノードを「構築直後」の設定へ戻す(学習モードのやり直し・BL-254)。

学習用のラボ(XRT-*)を作り直さずに最初から解き直すための道具。XR のコミット履歴を使う:
構築の最後にいまのコミット ID を戻り先として記録し、やり直す時はそこへ `rollback configuration to-exclude <ID>` する
(★`to <ID>` は「その回も含めて取り消す」= 1 つ戻りすぎる。2026-10-18 に修正)。
相手役の IOS・サーバは課題で変えない約束なので戻さない(戻すのは problem.yml で iosxr の機器だけ)。

  xr_reset.py --repo <リポ> --problem <ID> record [--nodes XR01,…] [--id <コミット ID>]
      いまの最新のコミット ID を topologies/_generated/<ID>/xr_baseline.yml に書く(lab_up.yml が構築の最後に呼ぶ)。
      --id は手で戻り先を決める時(記録の無い、前から動いているラボ)。
  xr_reset.py --repo <リポ> --problem <ID> reset [--nodes XR01,…]
      記録した ID へ戻す。ID が履歴に無い(作り直した後の古い記録など)時は何もせずに失敗する。

接続は管理 IF の SSH(採点と同じ経路)。コンソールは解答者が使っている同じ回線なので使わない。
資格情報は環境変数 NODE_USER / NODE_PASS(ansible の ansible_user / ansible_ssh_pass)。
★管理 IF の SSH を課題の設定で塞いでしまった時は戻せない(その時は作り直す)。
★XRd は初期設定(first-boot.cfg)がコミット履歴に残らず、構築直後の履歴が空(BL-250)。その時は戻り先を
  `first-boot` と記録し、やり直しは「履歴でいちばん古いコミットの手前」へ戻す(`rollback configuration to <最古の ID>`= その回も含めて取り消す)。
  XR が保持する履歴の件数を超えてコミットすると最古の分が消え、そこへは戻れなくなる(その時は作り直す)。
"""
import argparse
import os
import re
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from login_probe import Shell, connect  # noqa: E402



FIRST_BOOT = "first-boot"   # 構築直後の履歴が空(XRd)= 戻り先は最古のコミットの手前


def xr_nodes(repo, problem, only):
    pmeta = yaml.safe_load(open(os.path.join(repo, "problems", problem, "problem.yml"), encoding="utf-8"))
    fams = pmeta.get("node_image_families") or {}
    nodes = [n for n in pmeta["target_nodes"] if fams.get(n) == "iosxr"]
    return [n for n in nodes if n in only.split(",")] if only else nodes


def shell(repo, problem, node, wait=0):
    """管理 IF の SSH でつなぐ。wait 秒まで繋がるのを待つ(XRd は起動が速く、構築直後の記録の時点で SSH がまだ開いていない)。"""
    mgmt = yaml.safe_load(open(os.path.join(repo, "topologies/_generated", problem, "mgmt_map.yml"), encoding="utf-8"))
    t0 = time.time()
    while True:
        try:
            c = connect(mgmt[node], os.environ["NODE_USER"], os.environ["NODE_PASS"])
            return c, Shell(c)
        except Exception:
            if time.time() - t0 >= wait:
                raise
            time.sleep(10)


def commit_ids(sh):
    out = sh.send("show configuration commit list", timeout=60)
    return re.findall(r"^\s*\d+\s+(\d{10})\s", out, re.M), out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--nodes")
    ap.add_argument("--id", help="record: 戻り先のコミット ID を手で指定する")
    ap.add_argument("cmd", choices=["record", "reset"])
    a = ap.parse_args()
    path = os.path.join(a.repo, "topologies/_generated", a.problem, "xr_baseline.yml")
    nodes = xr_nodes(a.repo, a.problem, a.nodes)
    if not nodes:
        print("no IOS XR nodes")
        return 0
    bad = 0
    if a.cmd == "record":
        base = {}
        for node in nodes:
            try:
                c, sh = shell(a.repo, a.problem, node, wait=300)
                ids, out = commit_ids(sh)
                c.close()
            except Exception as e:
                print(f"ERROR {node}: {type(e).__name__}: {e}")
                bad += 1
                continue
            if a.id and a.id not in ids:
                print(f"ERROR {node}: commit {a.id} is not in the history")
                bad += 1
                continue
            base[node] = a.id or (ids[0] if ids else FIRST_BOOT)
            print(f"[{node}] baseline commit {base[node]}")
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(base, fh)
        return 1 if bad else 0

    try:
        base = yaml.safe_load(open(path, encoding="utf-8")) or {}
    except OSError:
        print(f"ERROR no baseline recorded ({os.path.relpath(path, a.repo)}). Rebuild the lab, or record one with --id")
        return 1
    for node in nodes:
        want = base.get(node)
        if not want:
            print(f"ERROR {node}: no baseline recorded")
            bad += 1
            continue
        try:
            c, sh = shell(a.repo, a.problem, node)
        except Exception as e:
            print(f"ERROR {node}: cannot log in over the management interface ({type(e).__name__}: {e}). Rebuild the lab")
            bad += 1
            continue
        try:
            ids, _ = commit_ids(sh)
            if want == FIRST_BOOT:
                if not ids:
                    print(f"[{node}] already at the baseline (first-boot)")
                    continue
                cmd, label = f"rollback configuration to {ids[-1]}", f"before {ids[-1]} (first-boot)"
            elif want not in ids:
                print(f"ERROR {node}: baseline commit {want} is not in the history (the lab was rebuilt?)")
                bad += 1
                continue
            elif ids[0] == want:
                print(f"[{node}] already at the baseline ({want})")
                continue
            else:
                cmd, label = f"rollback configuration to-exclude {want}", want
            out = sh.send(cmd, timeout=300,
                          until=r"(rolled back|[Ff]ailed|[Ee]rror|% ).*\n.*[#>]\s*$")
            ok = re.search(r"successfully rolled back|rolled back to", out, re.I) and not re.search(r"[Ff]ailed", out)
            print(f"[{node}] rollback to {label}: {'ok' if ok else 'FAILED'}")
            if not ok:
                print(out.strip()[-1500:])
                bad += 1
        finally:
            c.close()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
