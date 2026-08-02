#!/usr/bin/env python3
"""稼働中の CML ラボを読み取り専用でダンプする(BL-080 分野拡張の参考資料取り用)。

ラボの stop / wipe / extract は一切しない。
  1. title 部分一致でラボを特定し、ノード・リンク・IF を一覧化
  2. 各ノードの stored config(インポート/前回extract時点のもの)を記録
  3. コンソール経由で show running-config を採取(ログイン不要コンソールにも対応)

環境変数: CML_HOST/CML_USER/CML_PASS/CML_VERIFY/LAB_TITLE/NODE_USER/NODE_PASS/
          NODE_ENABLE/OUT_FILE
"""
import os
import sys

import yaml
from virl2_client import ClientLibrary
from pyats.topology import loader


def main():
    host = os.environ["CML_HOST"]
    url = host if host.startswith("http") else f"https://{host}"
    verify = os.environ.get("CML_VERIFY", "false").strip().lower() in ("1", "true")
    cl = ClientLibrary(url, os.environ["CML_USER"], os.environ["CML_PASS"],
                       ssl_verify=verify)
    want = os.environ["LAB_TITLE"]
    labs = [l for l in cl.all_labs() if want in l.title]
    if not labs:
        sys.exit(f"lab title に「{want}」を含むラボが見つかりません: "
                 f"{[l.title for l in cl.all_labs()]}")
    lab = labs[0]
    out = [f"# LAB DUMP: {lab.title} (state={lab.state()})", ""]

    out.append("## nodes")
    for n in lab.nodes():
        out.append(f"- {n.label} ({n.node_definition}) state={n.state}")
    out.append("")
    out.append("## links")
    for lk in lab.links():
        a, b = lk.interface_a, lk.interface_b
        out.append(f"- {a.node.label}:{a.label} -- {b.node.label}:{b.label}")
    out.append("")

    out.append("## stored configs (import/前回extract時点。手打ち分は反映されていない可能性)")
    for n in lab.nodes():
        out.append(f"### {n.label} (stored)")
        out.append("```")
        out.append((n.configuration or "(なし)").strip())
        out.append("```")
    out.append("")

    # コンソールで running-config を採取(失敗ノードはスキップ)
    tb = yaml.safe_load(lab.get_pyats_testbed())
    for name, dev in (tb.get("devices") or {}).items():
        creds = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            creds["default"] = {"username": os.environ["CML_USER"],
                                "password": os.environ["CML_PASS"]}
        else:
            creds["default"] = {"username": os.environ.get("NODE_USER", ""),
                                "password": os.environ.get("NODE_PASS", "")}
            creds["enable"] = {"password": os.environ.get(
                "NODE_ENABLE", os.environ.get("NODE_PASS", ""))}
    testbed = loader.load(tb)
    out.append("## running-configs (console)")
    for n in lab.nodes():
        if n.node_definition in ("external_connector", "unmanaged_switch"):
            continue
        dev = testbed.devices.get(n.label)
        if dev is None:
            continue
        out.append(f"### {n.label} (running)")
        out.append("```")
        try:
            dev.connect(via="a", log_stdout=False, learn_hostname=True,
                        connection_timeout=60)
            dev.enable()
            out.append(dev.execute("show running-config", timeout=90).strip())
            dev.disconnect()
        except Exception as e:
            out.append(f"(console 収集失敗: {e})")
        out.append("```")

    with open(os.environ["OUT_FILE"], "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"dumped -> {os.environ['OUT_FILE']}")


if __name__ == "__main__":
    main()
