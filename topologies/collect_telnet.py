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
import shlex
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


SSH_OPTS = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"


def run_shell(ip, user, pw, cmd, timeout=180):
    """Linux ノード(exec: shell)で 1 コマンドを ssh 実行し、stdout+stderr を返す。
    ssh 方式の採点(_grade_attempt.yml の ansible.builtin.shell)と同じく sudo なし・
    失敗コマンドの出力もそのまま採点に回す。"""
    c = pexpect.spawn(f"ssh {SSH_OPTS} {user}@{ip} {shlex.quote(cmd)}", timeout=timeout,
                      encoding="utf-8", codec_errors="ignore")
    try:
        c.expect("[Pp]assword:")
        c.sendline(pw)
        c.expect(pexpect.EOF)
        return (c.before or "").replace("\r\n", "\n").strip("\n")
    except (pexpect.EOF, pexpect.TIMEOUT) as exc:
        return f"[collect_telnet] ssh 失敗: {type(exc).__name__}"
    finally:
        c.close()


def main():
    checks = json.load(open(sys.argv[1], encoding="utf-8"))
    user, pw = os.environ["CCNP_USER"], os.environ["CCNP_PASS"]
    expected_labid = os.environ.get("LAB_ID")  # 期待するラボ指紋(無ければ照合しない)

    # ★BL-225: exec: shell のチェック(Linux 端末での疎通試験等)は ssh で 1 コマンドずつ実行する
    #   (telnet 収集の問題でも Linux ノードを採点できるように。IOS のチェックは従来どおり)。
    captured_sh = {}
    sh_hosts = {}
    for chk in checks:
        if chk.get("exec") == "shell":
            sh_hosts[chk["node"]] = chk["ansible_host"]
    for node, ip in sh_hosts.items():
        if expected_labid:
            fp = run_shell(ip, user, pw, "cat /etc/ccnp-lab-id", timeout=60)
            if "CCNP-LAB-" in fp and expected_labid not in fp:
                sys.exit(f"[collect_telnet] ★誤ラボ検知: {node}({ip}) の labid が期待 "
                         f"{expected_labid} と不一致。採点を中止")
        captured_sh[node] = {}
    for chk in checks:
        if chk.get("exec") == "shell":
            captured_sh[chk["node"]][chk["command"]] = run_shell(
                chk["ansible_host"], user, pw, chk["command"])

    # ノード単位で必要コマンドをまとめ、1 セッションで収集
    by_node, by_console = {}, {}
    for chk in checks:
        if chk.get("exec") == "shell":
            continue
        if chk.get("via") == "console":
            # ★BL-225: 管理 IF を持たないノード（problem.yml の console_nodes）は CML コンソールで収集
            by_console.setdefault(chk["node"], set()).add(chk["command"])
            continue
        key = (chk["node"], chk["ansible_host"])
        by_node.setdefault(key, set()).add(chk["command"])

    captured = {}
    for (node, ip), cmds in by_node.items():
        captured[node] = collect(ip, user, pw, sorted(cmds),
                                 expected_labid=expected_labid)
    if by_console:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import collect_console
        captured.update(collect_console.collect_nodes(by_console, lab_title=expected_labid))

    for chk in checks:
        src = captured_sh if chk.get("exec") == "shell" else captured
        chk["stdout"] = src.get(chk["node"], {}).get(chk["command"], "")

    json.dump(checks, open(sys.argv[2], "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"collected {len(checks)} checks from {len(by_node)} node(s) via telnet")


if __name__ == "__main__":
    main()
