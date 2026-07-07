#!/usr/bin/env python3
"""CML コンソール経由で機器(IOSv 等 SSH/network_cli 不可ノード)から show 出力を
収集し、grade.py 用の grade_input.json を生成する。

SSH(network_cli)が使えない IOSv 向けの収集層。判定ロジック(grade.py の Genie 構造化)は
共通で、ここは「生テキストを集める」役だけを担う。collect_telnet.py の console 版。

仕組み: virl2_client で対象ラボを title で特定 → lab.get_pyats_testbed() で
pyATS testbed(YAML)を取得 → terminal_server / ノードの認証情報を実値に差し替えて
loader.load → 各ノードに via='a'(ターミナルサーバ proxy のコンソール)で接続し
commands を順に execute(raw) → {cmd: 出力} を集める。

使い方:
  collect_console.py CHECKS.json OUT.json
    CHECKS.json : grade.yml が出力する checks 配列(各要素に node/command 等)
    OUT.json    : grade.py に渡す grade_input.json(各 check に stdout を付与)

環境変数:
  CML_HOST    : CML の URL またはホスト(例 https://10.1.10.10 / 10.1.10.10)
  CML_USER    : CML ログインユーザ(= ターミナルサーバ認証)
  CML_PASS    : CML ログインパスワード
  CML_VERIFY  : 証明書検証(true/false。既定 false)
  LAB_TITLE   : 対象ラボの title(例 CCNP-LAB-xxxxxxxx)
  NODE_USER   : 機器ローカルユーザ(コンソールログイン)
  NODE_PASS   : 機器ローカルパスワード
  NODE_ENABLE : enable パスワード(省略時 NODE_PASS を使用)
"""
import json
import os
import sys

import yaml
from virl2_client import ClientLibrary
from pyats.topology import loader


def _patch_testbed(tb_yaml, cml_user, cml_pass, node_user, node_pass, node_enable):
    """CML 生成 testbed の認証情報を実値へ差し替える。
    terminal_server(=コンソールの踏み台)は CML 認証、各ノードは機器ローカル認証。"""
    tb = yaml.safe_load(tb_yaml)
    for name, dev in (tb.get("devices") or {}).items():
        creds = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            creds["default"] = {"username": cml_user, "password": cml_pass}
        else:
            creds["default"] = {"username": node_user, "password": node_pass}
            creds["enable"] = {"password": node_enable}
    return tb


def collect(dev, commands, timeout=90):
    """1 ノードにコンソール接続し、commands を順に実行して {cmd: 出力} を返す。"""
    out = {}
    dev.connect(via="a", log_stdout=False, learn_hostname=True)
    try:
        dev.enable()
        for cmd in commands:
            try:
                out[cmd] = dev.execute(cmd, timeout=timeout)
            except Exception as e:  # 個別コマンド失敗は空扱い(採点側で FAIL)
                out[cmd] = f"(console execute error: {e})"
    finally:
        try:
            dev.disconnect()
        except Exception:
            pass
    return out


def main():
    checks = json.load(open(sys.argv[1], encoding="utf-8"))

    cml_host = os.environ["CML_HOST"]
    cml_user = os.environ["CML_USER"]
    cml_pass = os.environ["CML_PASS"]
    lab_title = os.environ["LAB_TITLE"]
    node_user = os.environ["NODE_USER"]
    node_pass = os.environ["NODE_PASS"]
    node_enable = os.environ.get("NODE_ENABLE") or node_pass
    verify = os.environ.get("CML_VERIFY", "false").strip().lower() in ("1", "true", "yes")

    url = cml_host if cml_host.startswith("http") else f"https://{cml_host}"
    cl = ClientLibrary(url, cml_user, cml_pass, ssl_verify=verify)
    labs = [l for l in cl.all_labs() if l.title == lab_title]
    if not labs:
        sys.exit(f"[collect_console] lab '{lab_title}' が CML({url}) に見つかりません")
    lab = labs[0]

    tb_dict = _patch_testbed(lab.get_pyats_testbed(), cml_user, cml_pass,
                             node_user, node_pass, node_enable)
    testbed = loader.load(tb_dict)

    # ノード単位で必要コマンドをまとめ、1 セッションで収集
    by_node = {}
    for chk in checks:
        by_node.setdefault(chk["node"], set()).add(chk["command"])

    captured = {}
    for node, cmds in by_node.items():
        dev = testbed.devices.get(node)
        if dev is None:
            captured[node] = {c: f"(node '{node}' not in testbed)" for c in cmds}
            continue
        try:
            captured[node] = collect(dev, sorted(cmds))
        except Exception as e:  # 接続失敗はそのノードの全コマンドを空扱い
            captured[node] = {c: f"(console connect error: {e})" for c in cmds}

    for chk in checks:
        chk["stdout"] = captured.get(chk["node"], {}).get(chk["command"], "")

    json.dump(checks, open(sys.argv[2], "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"collected {len(checks)} checks from {len(by_node)} node(s) via console")


if __name__ == "__main__":
    main()
