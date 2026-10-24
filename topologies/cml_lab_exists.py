#!/usr/bin/env python3
"""問題のラボが CML にまだあるかを確かめる(lab.sh teardown が撤去に失敗したときに使う)。

usage: cml_lab_exists.py --repo <リポ> --problem <ID>
  ラボの名前は topologies/_generated/<ID>/lab.yaml の lab.title。接続情報は group_vars/all/local.yml。
  終了コード= 0: ある(状態を表示)/ 1: 無い / 2: 確かめられない(CML に届かない など)/ 3: 生成物が無くラボの名前が分からない。
"""
import argparse
import os
import sys
import warnings

import yaml

warnings.filterwarnings("ignore")

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--problem", required=True)
a = ap.parse_args()
gen = os.path.join(a.repo, "topologies", "_generated", a.problem, "lab.yaml")
if not os.path.exists(gen):
    print(f"!! no generated lab.yaml for {a.problem}: the lab title is unknown")
    sys.exit(3)
try:
    title = yaml.safe_load(open(gen))["lab"]["title"]
    cfg = yaml.safe_load(open(os.path.join(a.repo, "group_vars", "all", "local.yml")))
    from virl2_client import ClientLibrary
    cl = ClientLibrary(f"https://{cfg['cml_host']}", cfg["cml_username"], cfg["cml_password"], ssl_verify=False)
    labs = [lb for lb in cl.all_labs(show_all=True) if lb.title == title]
except Exception as e:  # 確かめられない= 呼び出し側は安全側(止める)に倒す
    print(f"!! cannot check the CML lab of {a.problem}: {type(e).__name__}: {e}")
    sys.exit(2)
if labs:
    print(f"== CML lab {title} of {a.problem} still exists: {labs[0].state()}")
    sys.exit(0)
print(f"== CML lab {title} of {a.problem} is gone")
sys.exit(1)
