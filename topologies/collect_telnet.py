#!/usr/bin/env python3
"""telnet で機器(SSH不可=EEM非対応の IOL L2 スイッチ等)から show 出力を収集し、
grade.py 用の grade_input.json を生成する。

SSH(network_cli)が使えないノード向けの収集層。判定ロジック(grade.py の Genie 構造化)は
共通で、ここは「生テキストを集める」役だけを担う。

使い方:
  CCNP_USER=.. CCNP_PASS=.. collect_telnet.py CHECKS.json OUT.json
    CHECKS.json : grade.yml が出力する checks 配列（各要素に node/command/ansible_host と
                  parser/find/match/raw/points 等を含む）
    OUT.json    : grade.py に渡す grade_input.json（各 check に stdout を付与して出力）
"""
import json
import os
import sys

import pexpect


def collect(ip, user, pw, commands, timeout=45, expected_labid=None):
    """1 ノードに telnet ログインし、commands を順に実行して {cmd: 出力} を返す。

    expected_labid が与えられたら、収集前にラボ指紋(alias exec labid)を照合し、
    別ラボの labid が返った場合は即中止する(誤ラボ採点の防止)。
    指紋なし(旧build)は警告のみで続行。"""
    out = {}
    c = pexpect.spawn(f"telnet {ip}", timeout=timeout, encoding="utf-8",
                      codec_errors="ignore")
    try:
        c.expect(["Username:", "login:"])
        c.sendline(user)
        c.expect("Password:")
        c.sendline(pw)
        # 特権15ユーザなら直接 '#'。'>' なら enable。
        c.expect([r">", r"#"])
        if c.after.strip().endswith(">"):
            c.sendline("enable")
            if c.expect(["Password:", r"#"]) == 0:
                c.sendline(pw)
                c.expect(r"#")
        # プロンプト文字列(例 "SW01#")を確定させる
        c.sendline("")
        c.expect(r"\r?\n(\S+#)")
        prompt = c.match.group(1)
        c.sendline("terminal length 0")
        c.expect_exact(prompt)
        if expected_labid:
            c.sendline("show running-config | include alias exec labid")
            c.expect_exact(prompt)
            fp = c.before
            if "CCNP-LAB-" in fp and expected_labid not in fp:
                sys.exit(f"[collect_telnet] ★誤ラボ検知: {ip} の labid が期待 "
                         f"{expected_labid} と不一致。MGMT IP が別ラボに当たって"
                         f"います(mgmt_alloc.py status / gc で突合)。採点を中止")
            if "CCNP-LAB-" not in fp:
                print(f"[collect_telnet] 指紋なし(旧build?): {ip} → 照合スキップ",
                      file=sys.stderr)
        for cmd in commands:
            c.sendline(cmd)
            c.expect_exact(prompt)
            lines = c.before.splitlines()
            # 先頭のエコーバック行(コマンド自身)を除去
            if lines and cmd.strip() in lines[0]:
                lines = lines[1:]
            out[cmd] = "\n".join(lines).strip("\r\n")
        c.sendline("exit")
    finally:
        try:
            c.close()
        except Exception:
            pass
    return out


def main():
    checks = json.load(open(sys.argv[1], encoding="utf-8"))
    user, pw = os.environ["CCNP_USER"], os.environ["CCNP_PASS"]

    # ノード単位で必要コマンドをまとめ、1 セッションで収集
    by_node = {}
    for chk in checks:
        key = (chk["node"], chk["ansible_host"])
        by_node.setdefault(key, set()).add(chk["command"])

    captured = {}
    expected_labid = os.environ.get("LAB_ID")  # 期待するラボ指紋(無ければ照合しない)
    for (node, ip), cmds in by_node.items():
        captured[node] = collect(ip, user, pw, sorted(cmds),
                                 expected_labid=expected_labid)

    for chk in checks:
        chk["stdout"] = captured.get(chk["node"], {}).get(chk["command"], "")

    json.dump(checks, open(sys.argv[2], "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"collected {len(checks)} checks from {len(by_node)} node(s) via telnet")


if __name__ == "__main__":
    main()
