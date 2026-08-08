#!/usr/bin/env python3
"""console 問題(IOSv 等 SSH不可ノード)へ fix.json を CML コンソール経由で投入する。

collect_console.py の姉妹ツール(収集でなく設定投入)。自己検品・解答開示用。
fix.json 形式: {"<node>": {"config": ["<config行>", ...], "exec": ["<execコマンド>", ...]}}
  config はコンフィグモード直列(インデントで階層)、exec は clear 等。

使い方:
  fix_console.py FIX.json
環境変数: CML_HOST / CML_USER / CML_PASS / LAB_TITLE / NODE_USER / NODE_PASS
  (collect_console.py と同一)
"""
import json
import os
import sys

from virl2_client import ClientLibrary
from pyats.topology import loader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_console import _patch_testbed, restore_console  # noqa: E402


def main():
    fix_path = sys.argv[1]
    fix = json.load(open(fix_path))
    host = os.environ["CML_HOST"]
    if not host.startswith("http"):
        host = "https://" + host
    c = ClientLibrary(host, os.environ["CML_USER"], os.environ["CML_PASS"], ssl_verify=False)
    labs = c.find_labs_by_title(os.environ["LAB_TITLE"])
    if not labs:
        raise SystemExit(f"lab not found: {os.environ['LAB_TITLE']}")
    tb = _patch_testbed(labs[0].get_pyats_testbed(),
                        os.environ["CML_USER"], os.environ["CML_PASS"],
                        os.environ["NODE_USER"], os.environ["NODE_PASS"],
                        os.environ.get("NODE_ENABLE", os.environ["NODE_PASS"]))
    testbed = loader.load(tb)
    for name, item in fix.items():
        dev = testbed.devices[name]
        dev.connect(via="a", log_stdout=False, connection_timeout=120, learn_hostname=True)
        cfg = item.get("config") or []
        if cfg:
            dev.configure("\n".join(cfg))
        for cmd in item.get("exec") or []:
            dev.execute(cmd)
        restore_console(dev)
        dev.disconnect()
        print(f"[fix_console] {name}: config {len(cfg)}行 / exec {len(item.get('exec') or [])}件 投入")
    print("[fix_console] done")


if __name__ == "__main__":
    main()
