#!/usr/bin/env python3
"""ラボ起動前プリフライト — 割当 MGMT IP の生存確認(IP 衝突の物理検知)。

リース台帳(mgmt_alloc.py)にバグや手動操作の抜けがあっても、起動前に
「割当予定の IP に既に誰かが応答する」ことを検知して import を止める防御層。

ロジック:
  1. CML に自ラボ(--lab-title)が既に存在 → 再up(応答IPは自分のもの) → OK で終了
  2. 存在しない(新規 import) → mgmt_map の全 IP へ ping(-c1 -W1)。
     1つでも応答があれば「そのIPは使用中=台帳と実態がズレている」ので rc=1 で停止。

使い方(lab_up.yml から呼ばれる):
  CML_USER=.. CML_PASSWORD=.. lab_preflight.py --host <CML> --lab-title CCNP-LAB-xxx \
      --mgmt-map topologies/_generated/<id>/mgmt_map.yml
緊急回避: lab_up に -e force_up=true でこのチェックをスキップできる。
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import yaml


def ping_alive(ip):
    r = subprocess.run(["ping", "-c", "1", "-W", "1", ip],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ip if r.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--lab-title", required=True)
    ap.add_argument("--mgmt-map", required=True)
    a = ap.parse_args()

    from virl2_client import ClientLibrary
    url = a.host if a.host.startswith("http") else f"https://{a.host}"
    verify = os.environ.get("CML_VERIFY", "false").strip().lower() in ("1", "true", "yes")
    cl = ClientLibrary(url, os.environ["CML_USER"], os.environ["CML_PASSWORD"],
                       ssl_verify=verify)
    if any(l.title == a.lab_title for l in cl.all_labs()):
        print(f"[preflight] 自ラボ {a.lab_title} が CML に既存(再up) → IP 生存確認をスキップ")
        return

    mm = yaml.safe_load(open(a.mgmt_map, encoding="utf-8"))
    ips = sorted(set(mm.values()))
    with ThreadPoolExecutor(max_workers=len(ips)) as ex:
        alive = sorted(filter(None, ex.map(ping_alive, ips)))
    if alive:
        by_ip = {ip: n for n, ip in mm.items()}
        detail = ", ".join(f"{ip}({by_ip.get(ip, '?')})" for ip in alive)
        sys.exit(f"[preflight] ★IP衝突検知: 割当予定の MGMT IP が既に応答しています: {detail}\n"
                 f"  台帳と実態がズレています(teardown 漏れ/旧方式ラボ稼働中/手動操作)。\n"
                 f"  → mgmt_alloc.py status / gc で突合し、使用中ラボを特定してください。\n"
                 f"  （原因確認済みで強行する場合のみ -e force_up=true）")
    print(f"[preflight] OK: 割当 {len(ips)} IP はすべて未使用({a.lab_title} 新規起動可)")


if __name__ == "__main__":
    main()
