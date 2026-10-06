#!/usr/bin/env python3
"""PoC 用の使い捨てラボを CML に作る／消す — BL-234。

  mklab.py up     … POC-WEBCONSOLE(IOL ルータ 2 + IOL L2 スイッチ 1 の三角形)を作って起動
  mklab.py down   … 止めて消す

管理網には繋がない(コンソールだけで触る)。問題・ノルマ・出題履歴には一切関わらない。
接続情報は group_vars/all/local.yml(環境変数 CML_HOST / CML_USER / CML_PASS で上書き可)。
"""
import os
import sys

import yaml
from virl2_client import ClientLibrary

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TITLE = "POC-WEBCONSOLE"

BASE = """hostname {name}
no ip domain lookup
line con 0
 exec-timeout 0 0
 logging synchronous
"""
NODES = {
    #  名前: (定義, x, y, 追加 config)
    "R1": ("iol-xe", -220, -120, """interface Ethernet0/0
 ip address 10.0.12.1 255.255.255.0
 no shutdown
interface Ethernet0/1
 ip address 10.0.100.1 255.255.255.0
 no shutdown
"""),
    "R2": ("iol-xe", 220, -120, """interface Ethernet0/0
 ip address 10.0.12.2 255.255.255.0
 no shutdown
interface Ethernet0/1
 ip address 10.0.100.2 255.255.255.0
 no shutdown
"""),
    "SW1": ("ioll2-xe", 0, 120, ""),
}
LINKS = [("R1", 0, "R2", 0),        # (ノード, スロット) の対。IOL はスロット n = Ethernet<n//4>/<n%4>
         ("R1", 1, "SW1", 0),
         ("R2", 1, "SW1", 1)]


def client():
    v = yaml.safe_load(open(os.path.join(REPO, "group_vars", "all", "local.yml")))
    host = os.environ.get("CML_HOST") or v["cml_host"]
    url = host if host.startswith("http") else f"https://{host}"
    return ClientLibrary(url, os.environ.get("CML_USER") or v["cml_username"],
                         os.environ.get("CML_PASS") or v["cml_password"], ssl_verify=False)


def find(cl):
    return [lab for lab in cl.all_labs(show_all=True) if lab.title == TITLE]


def up(cl):
    if find(cl):
        sys.exit(f"{TITLE} は既にあります(作り直すなら先に down)")
    lab = cl.create_lab(TITLE)
    nodes = {}
    for name, (ndef, x, y, extra) in NODES.items():
        nodes[name] = lab.create_node(name, ndef, x, y,
                                      configuration=BASE.format(name=name) + extra + "end\n")
    # IF は使うスロットまでだけ作る(populate_interfaces は 32 本作るうえ、直後はラベルで引けない)
    ifs = {}
    for name, node in nodes.items():
        top = max([s for a, s, _, _ in LINKS if a == name] + [s for _, _, b, s in LINKS if b == name])
        node.create_interface(slot=top, wait=True)
        ifs[name] = {i.slot: i for i in node.interfaces() if i.slot is not None}
    for a, sa, b, sb in LINKS:
        lab.create_link(ifs[a][sa], ifs[b][sb])
    lab.start(wait=True)
    print(f"{TITLE} 起動: " + ", ".join(f"{n.label}={n.state}" for n in lab.nodes()))


def down(cl):
    labs = find(cl)
    if not labs:
        print(f"{TITLE} はありません")
    for lab in labs:
        lab.stop(wait=True)
        lab.wipe(wait=True)
        lab.remove()
        print(f"{TITLE} を削除しました")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("up", "down"):
        sys.exit(__doc__)
    {"up": up, "down": down}[cmd](client())
