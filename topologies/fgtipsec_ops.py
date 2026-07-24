#!/usr/bin/env python3
"""FGT-IPSEC-01 運用 CLI (BL-048)。

共用ラボ "FGT-LAB" 上で動く(console 基盤・共用リセットは sdwan_ops.py を共用)。

  build     … 受講者向け初期化: FGT の全問題設定を巻き戻し + FGT WAN 基盤を据付
              (port1 IP/デフォルトルート)・RBR の VPN 設定を撤去
              (★fgt1 は wipe 禁止=eval ライセンス消失)
  grade     … 採点(100点): 端末間疎通/IKEv2 SA/カウンタ/設定チェック(単段)
  solve     … ★検証用: golden-ipsec-{fgt,rbr}.cfg を console 投入
  status    … ノード状態＋ライセンス
  stop      … ラボ停止 (destroy は提供しない)

ログイン: FGT=admin/CCNPccnp・RBR=SUZUKI/CCNPccnp・alpine=root。
"""
import argparse
import json
import os
import subprocess
import sys
import time
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdwan_ops import (  # noqa: E402  共用ラボ FGT-LAB の console 基盤
    FGT, UNBUILD, _collect, cml, console, fgt_push, find_lab, run_on,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEM = "FGT-IPSEC-01"
GOLDEN_FGT = os.path.join(REPO, "poc", "fortigate", "golden-ipsec-fgt.cfg")
GOLDEN_RBR = os.path.join(REPO, "poc", "fortigate", "golden-ipsec-rbr.cfg")
GEN_DIR = os.path.join(REPO, "topologies", "_generated", PROBLEM)
PY = os.path.join(REPO, ".venv", "bin", "python3")

# FGT: IPsec 固有分の巻き戻し(共用 UNBUILD の後に実行。参照順: route→ph2→ph1→address)
FGT_UNBUILD_IPSEC = [
    "config router static", "delete 11", "end",
    "config vpn ipsec phase2-interface", "delete TO-RBR-P2", "end",
    "config vpn ipsec phase1-interface", "delete TO-RBR", "end",
    "config firewall address", "delete BR-NET", "end",
    # ★Phase 0 課題化(2026-07-23 ユーザ発案): port3(LAN兼管理)は据え付けず
    #   受講者が console から自己設定して GUI の足場を作る。他 FGT ラボの残骸が
    #   残ると Phase 0 が成立しないため、ここで確実に白紙化する(console 投入なので
    #   管理断の心配なし)。
    "config system interface",
    "edit port3", "unset ip", "unset allowaccess", "unset alias", "unset role", "next",
    "end",
]
# FGT: 本問の据付基盤(WAN IP + デフォルトルート。受講者スコープは VPN のみ)
FGT_BASE = [
    "config system interface",
    "edit port1", "set ip 203.0.113.2 255.255.255.252", "set alias WAN", "next",
    "end",
    "config router static",
    "edit 1", "set gateway 203.0.113.1", "set device port1", "next",
    "end",
]
# RBR: 受講者スコープ(crypto 一式 + Tunnel0 + VPN経路)の巻き戻し
RBR_UNBUILD = [
    "configure terminal",
    "no ip route 10.1.10.0 255.255.255.0 Tunnel0",
    "no interface Tunnel0",
    "no crypto ipsec profile IPSEC-PROF",
    "no crypto ipsec transform-set TS-DES esp-des esp-sha256-hmac",
    "no crypto ikev2 profile FGT-PROF",
    "no crypto ikev2 keyring FGT-KR",
    "no crypto ikev2 policy FGT-POL",
    "no crypto ikev2 proposal FGT-PROP",
    "end",
    "write memory",
]


def ios_push(node, lines, label):
    c, P = console(node)
    for ln in lines:
        out = run_on(c, P, ln, timeout=30)
        for l in out.splitlines():
            if l.strip().startswith("%") and "Invalid" in l or "Error" in l:
                print(f"  [{node}] {ln}  ->  {l.strip()}")
    c.close()
    print(f"[{label}] {node}: {len(lines)} 行投入")


def cmd_build(_):
    client = cml()
    lab = find_lab(client)
    if lab is None:
        sys.exit("[build] 共用ラボ 'FGT-LAB' が CML に無い。復旧手順は"
                 " problems/FGT-SDWAN-01/README.md 参照")
    for n in lab.nodes():
        if n.state != "BOOTED":
            n.start(wait=True)
    errs = fgt_push(UNBUILD + FGT_UNBUILD_IPSEC + FGT_BASE, "build/fgt")
    for e in errs:
        print("  ", e)
    ios_push("RBR", RBR_UNBUILD, "build/rbr")
    c, P = console(FGT)
    out = run_on(c, P, "get system status | grep -i license")
    c.close()
    if "Valid" not in out:
        print("★★ 警告: License が Valid でない — 出題前に要復旧(README)")
    print("[build] 完了。受講者へ task.md を提示"
          "(FGT: WAN 据付済み・★LAN(port3)は未設定=Phase 0 で受講者が console から自己設定 / "
          "GUI は Phase 0 完了後 https://10.1.10.11 admin/CCNPccnp / "
          "RBR: WAN/LAN 据付済み・console SUZUKI/CCNPccnp)")


def cmd_solve(_):
    lines = [l.strip() for l in open(GOLDEN_FGT)
             if l.strip() and not l.strip().startswith("#")]
    errs = fgt_push(lines, "solve/fgt")
    for e in errs:
        print("  ", e)
    lines = [l.strip() for l in open(GOLDEN_RBR)
             if l.strip() and not l.strip().startswith("!")]
    ios_push("RBR", lines, "solve/rbr")
    print("[solve] 完了。SA 確立まで30秒待って grade を実行")
    time.sleep(30)


def cmd_grade(a):
    grading = yaml.safe_load(open(os.path.join(REPO, "problems", PROBLEM, "grading.yml")))
    checks = grading["checks"]
    sessions = {}
    try:
        _collect(checks, "normal", sessions)
    finally:
        for s in sessions.values():
            if s:
                try:
                    s[0].close()
                except Exception:
                    pass
    os.makedirs(GEN_DIR, exist_ok=True)
    gi = os.path.join(GEN_DIR, "grade_input.json")
    json.dump(checks, open(gi, "w"), ensure_ascii=False, indent=1)
    argv = [PY, os.path.join(REPO, "topologies", "grade.py"), gi]
    if a.gate:
        argv.append("--gate")
    sys.exit(subprocess.run(argv).returncode)


def cmd_status(_):
    from sdwan_ops import cmd_status as _s
    _s(_)


def cmd_stop(_):
    from sdwan_ops import cmd_stop as _s
    _s(_)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)
    for v in ("build", "solve", "status", "stop"):
        sub.add_parser(v)
    pg = sub.add_parser("grade")
    pg.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    {"build": cmd_build, "solve": cmd_solve, "grade": cmd_grade,
     "status": cmd_status, "stop": cmd_stop}[a.verb](a)


if __name__ == "__main__":
    main()
