#!/usr/bin/env python3
"""IOSv(CVAC) 問題の「IPなしIF」を CVAC 最終パス完了後に console 経由で no shut する。

背景(2026-08-03 実測):
  IOSv の day0 適用(CVAC)は2パスで走り、最終パスが「ip address を持たない IF」を
  強制 shutdown する(起動数分後に LINK-5-CHANGED admin down)。day0 に no shutdown を
  書いても、EEM で起動後に打っても(CVAC と CLI セッションが衝突して後続 config が
  食われるレースあり)、SSH で早打ちしても戻される。
  → 本スクリプトは CVAC 完了マーカー(%CVAC-4-CONFIG_DONE)を待ってから
    no shut し、up を検証する。dot1q サブIF親トランク等の bringup 用。

★完了待ちは REST(コンソールログ API)で行い、完了までコンソールに一切触らない。
  CVAC は config を「コンソール経由」で適用するため、待ちのために console へ
  接続して show を打つと、セッション操作が適用ストリームに割り込み day0 の
  一部(VRF AF の中身等)が散発的に欠損する(2026-08-03 実測・EEM衝突と同型)。

使い方:
  cvac_bringup.py <NODE1,NODE2,...> <IF1,IF2,...>
環境変数: CML_HOST / CML_USER / CML_PASS / LAB_TITLE / NODE_USER / NODE_PASS
  (collect_console.py / fix_console.py と同一)
"""
import os
import re
import sys
import time

from virl2_client import ClientLibrary
from pyats.topology import loader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_console import _patch_testbed, restore_console  # noqa: E402

WAIT_TRIES = 40   # 15s x 40 = 最大10分
WAIT_SLEEP = 15


def main():
    nodes = sys.argv[1].split(",")
    ifs = sys.argv[2].split(",")
    host = os.environ["CML_HOST"]
    if not host.startswith("http"):
        host = "https://" + host
    c = ClientLibrary(host, os.environ["CML_USER"], os.environ["CML_PASS"], ssl_verify=False)
    labs = c.find_labs_by_title(os.environ["LAB_TITLE"])
    if not labs:
        raise SystemExit(f"lab not found: {os.environ['LAB_TITLE']}")
    lab = labs[0]
    tb = _patch_testbed(lab.get_pyats_testbed(),
                        os.environ["CML_USER"], os.environ["CML_PASS"],
                        os.environ["NODE_USER"], os.environ["NODE_PASS"],
                        os.environ.get("NODE_ENABLE", os.environ["NODE_PASS"]))
    testbed = loader.load(tb)
    cml_nodes = {n.label: n for n in lab.nodes()}
    rc = 0
    for name in nodes:
        # 1) CVAC 最終パス完了待ち: REST のコンソールログのみで判定
        #    (完了前に console へ接続しない=day0 適用ストリームを汚さない)
        done = False
        for i in range(WAIT_TRIES):
            try:
                log = cml_nodes[name].console_logs(0) or ""
            except Exception as e:
                raise SystemExit(f"[cvac_bringup] {name}: コンソールログ API 失敗: {e}")
            if "CVAC-4-CONFIG_DONE" in log:
                done = True
                break
            time.sleep(WAIT_SLEEP)
        if not done:
            print(f"[cvac_bringup] {name}: CVAC 完了マーカー未検出(打ち切り)")
            rc = 1
            continue
        dev = testbed.devices[name]
        dev.connect(via="a", log_stdout=False, connection_timeout=120, learn_hostname=True)
        try:
            dev.enable()
            # 2) no shutdown(そのノードに存在する IF だけ。ifs はノード横断の
            #    ユニオン指定なので、無い IF はスキップ=エラーにしない)
            brief = dev.execute("show ip interface brief")
            targets = [i for i in ifs if re.search(rf"^{re.escape(i)}\s", brief, re.M)]
            skipped = [i for i in ifs if i not in targets]
            if skipped:
                print(f"[cvac_bringup] {name}: {','.join(skipped)} は存在しないためスキップ")
            lines = []
            for ifname in targets:
                lines += [f"interface {ifname}", " no shutdown"]
            if lines:
                dev.configure("\n".join(lines))
            # 3) up 検証
            time.sleep(3)
            brief = dev.execute("show ip interface brief")
            for ifname in targets:
                m = re.search(rf"^{re.escape(ifname)}\s+\S+.*$", brief, re.M)
                if not m or "administratively down" in m.group(0):
                    print(f"[cvac_bringup] {name}: {ifname} が up になりません: {m.group(0) if m else '(行なし)'}")
                    rc = 1
                else:
                    print(f"[cvac_bringup] {name}: {ifname} up 確認")
        finally:
            restore_console(dev)
            try:
                dev.disconnect()
            except Exception:
                pass
    sys.exit(rc)


if __name__ == "__main__":
    main()
