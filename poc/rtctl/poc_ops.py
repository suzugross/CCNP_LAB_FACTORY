#!/usr/bin/env python3
"""BL-141 PoC ラボ(POC-RTCTL)の import/start/state/stop/delete。

コンソール収集は poc/redist-mp-loop/poc_console.py を --title POC-RTCTL で流用する。
"""
import argparse
import os
import sys

import yaml
from virl2_client import ClientLibrary

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TITLE = "POC-RTCTL"
LAB_YAML = os.path.join(HERE, "poc-rtctl-iol-lab.yaml")


def client():
    c = yaml.safe_load(open(os.path.join(REPO, "group_vars", "all", "local.yml")))
    return ClientLibrary(f"https://{c['cml_host']}", c["cml_username"], c["cml_password"],
                         ssl_verify=False)


def find(cl):
    return next((l for l in cl.all_labs() if l.title == TITLE), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["import", "start", "state", "stop", "wipe", "delete", "labs"])
    args = ap.parse_args()
    cl = client()

    if args.cmd == "labs":
        for l in cl.all_labs():
            print(f"{l.title}: {l.state()} ({len(l.nodes())} nodes)")
        return

    if args.cmd == "import":
        if find(cl):
            sys.exit(f"lab '{TITLE}' already exists — delete first")
        lab = cl.import_lab(open(LAB_YAML).read(), title=TITLE)
        print(f"imported: {lab.id} ({len(lab.nodes())} nodes)")
        return

    lab = find(cl)
    if not lab:
        sys.exit(f"lab '{TITLE}' not found")
    if args.cmd == "start":
        lab.start(wait=True)
        print("started")
    elif args.cmd == "state":
        print(lab.state())
        for n in lab.nodes():
            print(f"  {n.label}: {n.state}")
    elif args.cmd == "stop":
        lab.stop(wait=True)
        print("stopped")
    elif args.cmd == "wipe":
        lab.stop(wait=True)
        lab.wipe(wait=True)
        print("wiped")
    elif args.cmd == "delete":
        lab.stop(wait=True)
        lab.wipe(wait=True)
        lab.remove()
        print("deleted")


if __name__ == "__main__":
    main()
