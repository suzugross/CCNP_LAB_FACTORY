#!/usr/bin/env python3
"""FGT-FW-BASIC-01 運用 CLI (BL-047)。

共用ラボ "FGT-LAB" 上で動く(console 基盤・共用リセット UNBUILD は sdwan_ops.py を共用)。

  build     … 受講者向け初期化: SD-WAN/BASIC 両方の設定を巻き戻す
              (★fgt1 は wipe 禁止=eval ライセンス消失。port3=LAN兼管理は据付)
  grade     … 採点(100点): 疎通/VIP/暗黙deny/設定チェック(単段・劣化注入なし)
  solve     … ★検証用: poc/fortigate/golden-basic-fgt.cfg を console 投入
  status    … ノード状態＋ライセンス
  stop      … ラボ停止 (destroy は提供しない)

FGT ログイン: admin/CCNPccnp。alpine(pcA/pcB/dmz1)=root。IOS=SUZUKI/CCNPccnp。
"""
import argparse
import json
import os
import subprocess
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdwan_ops import (  # noqa: E402  共用ラボ FGT-LAB の console 基盤
    FGT, UNBUILD, _collect, cml, console, fgt_push, find_lab, run_on,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEM = "FGT-FW-BASIC-01"
GOLDEN_CFG = os.path.join(REPO, "poc", "fortigate", "golden-basic-fgt.cfg")
GEN_DIR = os.path.join(REPO, "topologies", "_generated", PROBLEM)
PY = os.path.join(REPO, ".venv", "bin", "python3")


def cmd_build(_):
    client = cml()
    lab = find_lab(client)
    if lab is None:
        sys.exit("[build] 共用ラボ 'FGT-LAB' が CML に無い。復旧手順は"
                 " problems/FGT-SDWAN-01/README.md 参照")
    for n in lab.nodes():
        if n.state != "BOOTED":
            n.start(wait=True)
    errs = fgt_push(UNBUILD, "build/unbuild")
    for e in errs:
        print("  ", e)
    c, P = console(FGT)
    out = run_on(c, P, "get system status | grep -i license")
    c.close()
    if "Valid" not in out:
        print("★★ 警告: License が Valid でない — 出題前に要復旧(README)")
    print("[build] 完了。受講者へ task.md を提示"
          "(FGT: port3管理のみ設定済み・GUI https://10.1.10.11 admin/CCNPccnp)")


def cmd_solve(_):
    lines = [l.strip() for l in open(GOLDEN_CFG)
             if l.strip() and not l.strip().startswith("#")]
    errs = fgt_push(lines, "solve")
    for e in errs:
        print("  ", e)
    print("[solve] 完了。grade を実行可能")


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
