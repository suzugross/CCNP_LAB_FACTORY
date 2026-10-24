#!/usr/bin/env python3
"""PoC: CML のリンクに障害を起こす(両端のポートは up のまま落とす= 黙った故障)。BL-246 M7。

usage: cml_link.py <PROBLEM_ID> <NODE_A> <NODE_B> {show|loss <pct>|clear|stop|start}
  loss 100 = そのリンクのパケットを全部捨てる(リンク条件)。clear で元に戻す。
  stop/start = リンクそのものを切る/つなぐ(端の機器がキャリア断を検知するかは機種次第)。
ラボは topologies/_generated/<ID>/lab.yaml の title で引く。接続情報は group_vars/all/local.yml。
"""
import sys
import warnings

import yaml

warnings.filterwarnings("ignore")
from virl2_client import ClientLibrary  # noqa: E402

pid, na, nb, op = sys.argv[1:5]
arg = sys.argv[5] if len(sys.argv) > 5 else None
title = yaml.safe_load(open(f"topologies/_generated/{pid}/lab.yaml"))["lab"]["title"]
c = yaml.safe_load(open("group_vars/all/local.yml"))
cl = ClientLibrary(f"https://{c['cml_host']}", c["cml_username"], c["cml_password"], ssl_verify=False)
labs = [lb for lb in cl.all_labs(show_all=True) if lb.title == title]
if not labs:
    sys.exit(f"!! lab not found: {title}")
lab = labs[0]
link = next((lk for lk in lab.links() if {lk.node_a.label, lk.node_b.label} == {na, nb}), None)
if link is None:
    sys.exit(f"!! link not found: {na}-{nb}")
if op == "loss":
    link.set_condition(loss=float(arg))
elif op == "clear":
    link.remove_condition()
elif op == "stop":
    link.stop()
elif op == "start":
    link.start()
print(f"{na}-{nb} state={link.state} condition={link.get_condition()}")
