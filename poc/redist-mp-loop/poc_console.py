#!/usr/bin/env python3
"""BL-058 PoC 用の汎用コンソールドライバ。

CML のターミナルサーバ経由(pyATS testbed via='a')で 1 ノードに接続し、
show 実行(--exec)または設定投入(--config)を行う。MGMT/SSH 不要。

使い方:
  poc_console.py --title POC-REDIST26308 --node RA --exec "show ip route;;traceroute 192.168.1.6 ttl 1 12"
  poc_console.py --title POC-REDIST26308 --node RB --config "ip access-list ...\n..."
コマンド区切りは ';;'。--config は改行区切りの config 行(configure terminal 配下)。
"""
import argparse
import os
import sys

import yaml
from virl2_client import ClientLibrary
from pyats.topology import loader

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_device(title, node):
    c = yaml.safe_load(open(os.path.join(REPO, "group_vars", "all", "local.yml")))
    cl = ClientLibrary(f"https://{c['cml_host']}", c["cml_username"], c["cml_password"],
                       ssl_verify=False)
    lab = next(l for l in cl.all_labs() if l.title == title)
    tb = yaml.safe_load(lab.get_pyats_testbed())
    for name, dev in (tb.get("devices") or {}).items():
        creds = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            creds["default"] = {"username": c["cml_username"], "password": c["cml_password"]}
        else:
            creds["default"] = {"username": "SUZUKI", "password": "CCNP"}
            creds["enable"] = {"password": "CCNP"}
    testbed = loader.load(yaml.dump(tb))
    return testbed.devices[node]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--node", required=True)
    ap.add_argument("--exec", dest="exec_cmds", default=None)
    ap.add_argument("--config", dest="config_lines", default=None)
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    dev = get_device(args.title, args.node)
    dev.connect(via="a", log_stdout=False, learn_hostname=True,
                connection_timeout=90, mit=False)
    try:
        dev.enable()
        if args.config_lines:
            lines = args.config_lines.replace("\\n", "\n")
            out = dev.configure(lines, timeout=args.timeout)
            print(f"===== [{args.node}] configure =====")
            print(out)
        if args.exec_cmds:
            for cmd in args.exec_cmds.split(";;"):
                cmd = cmd.strip()
                if not cmd:
                    continue
                print(f"===== [{args.node}] {cmd} =====")
                try:
                    print(dev.execute(cmd, timeout=args.timeout))
                except Exception as e:
                    print(f"!! ERROR: {e}")
    finally:
        try:
            dev.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
