#!/usr/bin/env python3
"""PoC: CML のリンクでパケットを捕まえる(BL-261)。2 台を結ぶリンクを探して捕獲を始める/止めて pcap を保存する。
usage: cml_cap.py <PROBLEM_ID> <NODE_A> <NODE_B> start [bpf]   |   cml_cap.py <PROBLEM_ID> <NODE_A> <NODE_B> stop <out.pcap>"""
import hashlib, sys, time, warnings, yaml
warnings.filterwarnings("ignore")
from virl2_client import ClientLibrary

pid, a, b, op = sys.argv[1:5]
c = yaml.safe_load(open("group_vars/all/local.yml"))
cl = ClientLibrary(f"https://{c['cml_host']}", c["cml_username"], c["cml_password"], ssl_verify=False)
title = "CCNP-LAB-" + hashlib.md5(pid.encode()).hexdigest()[:8]
lab = next(l for l in cl.all_labs() if l.title == title)
link = next(k for k in lab.links() if {k.node_a.label, k.node_b.label} == {a, b})
if op == "start":
    bpf = sys.argv[5] if len(sys.argv) > 5 else None
    try: link.stop_capture()
    except Exception: pass
    print(link.start_capture(maxpackets=2000, maxtime=600, bpfilter=bpf))
else:
    # ★virl2_client 2.10 の download_capture はリンクの ID で取りに行き、CML 2.8 では 404 になる → 捕獲のキーで取る(/pcap/<key>)
    key = (link.capture_status().get("config") or {}).get("link_capture_key")
    try: link.stop_capture()
    except Exception as e: print("stop:", e)
    time.sleep(2)
    r = cl._session.get(f"pcap/{key}")
    open(sys.argv[5], "wb").write(r.content); print("saved", sys.argv[5], r.status_code, len(r.content))
