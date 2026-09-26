#!/usr/bin/env python3
"""GEN-STP の自己検品用 telnet 操作器(BL-076)。ioll2 は SSH 不可・collect_telnet は exec 専用なので、
config 投入はここで行う(poc/stp/stpcli.py の本番版。プロンプト regex は PoC 知見 3)。

  stp_ops.py fix  <ID>                     solution/fix.json の "fix" を投入(conf → exec)
  stp_ops.py conf <ID> <NODE> "<行>" ...    任意の config を投入(誤解法の検証用)
  stp_ops.py show <ID> <NODE> "<cmd>" ...   show を実行して表示
  stp_ops.py bringup <ID>                  IOSvL2 の起動後 Vlan999 SVI 固着を救済(gen_pack.bringup 相当)
管理 IP は topologies/_generated/<ID>/mgmt_map.yml、認証は group_vars/all/vault.yml(パスワード CCNP)。
"""
import json
import os
import re
import sys
import time

import pexpect
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT = re.compile(r"\r?\n(SW\d+(?:\([\w-]+\))?#)")


def creds():
    from ansible.parsing.vault import VaultLib, VaultSecret
    vl = VaultLib([("default", VaultSecret(b"CCNP"))])
    v = yaml.safe_load(vl.decrypt(open(os.path.join(REPO, "group_vars", "all", "vault.yml"), "rb").read()))
    return v["ansible_user"], v["ansible_ssh_pass"]


def hosts(pid):
    return yaml.safe_load(open(os.path.join(REPO, "topologies", "_generated", pid, "mgmt_map.yml")))


def login(ip, user, pw):
    for i in range(8):
        try:
            c = pexpect.spawn(f"telnet {ip}", timeout=60, encoding="utf-8", codec_errors="ignore")
            c.expect(["Username:", "login:"])
            c.sendline(user)
            c.expect("Password:")
            c.sendline(pw)
            c.expect([r">", r"#"])
            if c.after.strip().endswith(">"):
                c.sendline("enable")
                if c.expect(["Password:", r"#"]) == 0:
                    c.sendline(pw)
                    c.expect(r"#")
            for cmd in ("terminal length 0", "terminal width 200"):
                c.sendline(cmd)
                c.expect(PROMPT)
            return c
        except (pexpect.EOF, pexpect.TIMEOUT):
            time.sleep(15)
    raise SystemExit(f"login failed: {ip}")


def run(c, cmd):
    c.sendline(cmd)
    buf = ""
    while c.expect([PROMPT, r"\[confirm\]"]) == 1:
        buf += c.before + c.after
        c.sendline("")
    return (buf + c.before).strip("\r\n")


def conf(c, lines):
    out = [run(c, "configure terminal")] + [run(c, x) for x in lines] + [run(c, "end")]
    return "\n".join(o for o in out if o.strip())


def bounce_down_svis(pid, log=print):
    """★IOSvL2 は**データ VLAN の SVI も起動後 down で固着**する(2026-09-26 実測)。
    未接続のエッジポートが本当に down なので VLAN に up のアクセスポートが無く、trunk が
    forwarding でも SVI が上がらない(IOL は未接続でも connected 扱いなので起きない)。
    → telnet で down の Vlan(mgmt 以外)だけ shut/no shut する。gen_pack.bringup からも呼ぶ。"""
    user, pw = creds()
    for n, ip in sorted(hosts(pid).items()):
        try:
            c = login(ip, user, pw)
        except SystemExit:
            log(f"[bringup] {n}: telnet 不可(スキップ)")
            continue
        down = [v for v in re.findall(r"^(Vlan\d+)\s+\S+\s+\S+\s+\S+\s+down",
                                      run(c, "show ip interface brief | include Vlan"), re.M)
                if v != "Vlan999"]
        if down:
            conf(c, [x for v in down for x in (f"interface {v}", "shutdown", "no shutdown")])
            log(f"[bringup] {n}: SVI bounce {down}")
        else:
            log(f"[bringup] {n}: 上がっていない SVI は無し")


def main():
    op, pid = sys.argv[1], sys.argv[2]
    user, pw = creds()
    hm = hosts(pid)
    if op == "fix":
        fx = json.load(open(os.path.join(REPO, "problems", pid, "solution", "fix.json")))["fix"]
        sess = {n: login(hm[n], user, pw) for n in fx}
        for n, f in fx.items():          # conf を全機に入れてから exec(clear 系)
            if f["conf"]:
                print(f"### {n}: conf {f['conf']}\n{conf(sess[n], f['conf'])}")
        time.sleep(20)                   # 全台が新モードになってから clear(早すぎると移行状態が残る)
        for n, f in fx.items():
            for e in f["exec"]:
                print(f"### {n}: {e}\n{run(sess[n], e)}")
    elif op in ("conf", "show"):
        n = sys.argv[3]
        c = login(hm[n], user, pw)
        if op == "conf":
            print(conf(c, sys.argv[4:]))
        else:
            for cmd in sys.argv[4:]:
                print(f"### {n}: {cmd}\n{run(c, cmd)}")
    elif op == "bringup":
        # ①mgmt(Vlan999)の固着は gen_pack.bringup(console 経由の SVI bounce)に任せる
        sys.path.insert(0, os.path.join(REPO, "topologies"))
        import gen_pack
        gen_pack.bringup(REPO, pid, print)
        bounce_down_svis(pid, print)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
