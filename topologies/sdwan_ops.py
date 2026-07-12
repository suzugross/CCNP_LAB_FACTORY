#!/usr/bin/env python3
"""FGT-SDWAN-01 運用 CLI (BL-046)。

  build     … 受講者向け初期化: FGT の SD-WAN/WAN 設定を CLI で巻き戻す
              (★fgt1 は wipe 禁止=eval ライセンス消失。据付ノードは無傷)
  grade     … 3段階採点(100点): 平常チェック → WAN1劣化注入して効果チェック
              → 復旧してフェイルバックチェック
  solve     … ★検証用: poc/fortigate/golden-sdwan-fgt.cfg を console 投入
  inject    … WAN1 劣化を手動注入 (latency250ms/loss3%・体感デモ用)
  restore   … 劣化解除
  status    … ノード状態＋ライセンス
  stop      … ラボ停止 (destroy は提供しない: wipe でライセンス消失のため)

前提: CML に共用ラボ "FGT-LAB" が存在し fgt1 が eval ライセンス済み
(BL-047 で FGT-SDWAN-01 から改名・SW2/dmz1 追加。SW2 は L2 透過で本問無影響)。
(取得手順= problems/_drafts/FGT-SDWAN.design.md / メモリ ccnp-fortigate)。
FGT ログイン: admin/CCNPccnp。alpine=root。IOS(ISP/INET)=SUZUKI/CCNPccnp。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

import pexpect
import urllib3
import yaml

urllib3.disable_warnings()

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cml_creds(repo):
    """CML 認証は gitignore 済みの group_vars/all/local.yml から読む(ハードコード禁止)。"""
    import yaml as _y
    d = _y.safe_load(open(os.path.join(repo, "group_vars", "all", "local.yml")))
    return d["cml_host"], d["cml_username"], d["cml_password"]


CML_HOST, CML_USER, CML_PASS = _cml_creds(REPO)
PROBLEM = "FGT-SDWAN-01"   # 問題ID (grading.yml / _generated の場所)
TITLE = "FGT-LAB"          # CML 共用ラボ名 (BL-047 で改名・FGT問題シリーズ共用)
GOLDEN_CFG = os.path.join(REPO, "poc", "fortigate", "golden-sdwan-fgt.cfg")
GEN_DIR = os.path.join(REPO, "topologies", "_generated", PROBLEM)
PY = os.path.join(REPO, ".venv", "bin", "python3")

FGT = "fgt1"
ALPINE = {"pcA", "pcB", "dmz1", "pcC"}
P_FG = r"[\w-]+ (\(\S+\) )?# "
P_ALP = r"(\r\n|\r|\n)[\w-]+:[^\r\n]*[#$] ?"
P_IOS = r"(\r\n|\r|\n)([\w/-]+)(\([\w./-]+\))?([>#]) ?"

# 受講者初期化: 模範解答の逆順(参照制約: policy→vip/address→route→service→hc→members→IF)。
# ★FGT-LAB 共用リセット: SD-WAN 問(本問)と FGT-FW-BASIC-01 の両方の設定を消す
#   (fgtbasic_ops.py からも import される。存在しない delete は fgt_push が注意扱い=冪等)
UNBUILD = [
    "config firewall policy", "delete 1", "delete 2", "delete 3", "end",
    "config firewall vip", "delete DMZ-SRV-HTTP", "end",
    "config firewall address", "delete LAN-NET", "delete DMZ-SRV", "end",
    "config router static", "delete 1", "end",
    "config system sdwan",
    "config service", "delete 1", "end",
    "config health-check", "delete SLASRV", "end",
    "config members", "delete 1", "delete 2", "end",
    "set status disable", "end",
    "config system interface",
    "edit port1", "set ip 0.0.0.0 0.0.0.0", "unset allowaccess",
    "unset alias", "set role undefined", "next",
    "edit port2", "set ip 0.0.0.0 0.0.0.0", "unset allowaccess",
    "unset alias", "set role undefined", "next", "end",
]

INJECT = dict(bandwidth=10000, latency=250, jitter=10, loss=3.0)


def cml():
    from virl2_client import ClientLibrary
    return ClientLibrary(f"https://{CML_HOST}", CML_USER, CML_PASS, ssl_verify=False)


def find_lab(client):
    for lab in client.all_labs():
        if lab.title == TITLE:
            return lab
    return None


def wan1_link(lab):
    return next(l for l in lab.links()
                if {l.node_a.label, l.node_b.label} == {FGT, "ISP1"})


def _open(node):
    c = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {CML_USER}@{CML_HOST}",
        encoding="utf-8", codec_errors="replace", timeout=30)
    c.expect("assword:")
    c.sendline(CML_PASS)
    c.expect("consoles>")
    c.sendline(f"open /{TITLE}/{node}/0")
    c.expect("Escape character")
    time.sleep(2)
    return c


def console(node):
    c = _open(node)
    if node in ALPINE:
        # ★受講者が ping 等を流しっぱなしのことがある(task.md の観察指示どおり)
        #   → Ctrl-C で止めてからプロンプトを取りに行く
        c.send("\x03")
        time.sleep(1)
        c.send("\r")
        for _ in range(10):
            idx = c.expect([r"login:", P_ALP, pexpect.TIMEOUT], timeout=12)
            if idx == 0:
                c.send("root\r")
            elif idx == 1:
                return c, P_ALP
            else:
                c.send("\x03")
                time.sleep(1)
                c.send("\r")
        raise RuntimeError(f"{node}: alpine シェル不達")
    if node == FGT:
        c.send("\r")
        for _ in range(12):
            idx = c.expect([r"login:", r"Password:", P_FG, pexpect.TIMEOUT], timeout=20)
            if idx == 0:
                c.send("admin\r")
            elif idx == 1:
                c.send("CCNPccnp\r")
            elif idx == 2:
                return c, P_FG
            else:
                c.send("\r")
        raise RuntimeError(f"{node}: FGT プロンプト不達(60秒ロックアウトの可能性)")
    # IOS (ISP1/ISP2/INET/RBR)。RBR は line con login local → Username: が出る
    c.send("end\r")
    time.sleep(1)
    c.send("\r")
    for _ in range(12):
        idx = c.expect([P_IOS, r"assword:", r"sername:", pexpect.TIMEOUT],
                       timeout=15)
        if idx == 0:
            if c.match.group(4) == "#":
                return c, P_IOS
            c.send("enable\r")
        elif idx == 1:
            c.send("CCNPccnp\r")
        elif idx == 2:
            c.send("SUZUKI\r")
        else:
            c.send("\r")
    raise RuntimeError(f"{node}: priv exec 不達")


def run_on(c, P, cmd, timeout=60):
    c.send(cmd + "\r")
    out = ""
    for _ in range(5):
        i = c.expect([P, r"--More--", pexpect.TIMEOUT], timeout=timeout)
        out += c.before or ""
        if i == 1:
            c.send(" ")
            continue
        if cmd.split()[0] in out:
            break
    return out


def fgt_push(lines, label):
    """FGT へ設定行を投入。エラー行を返す。"""
    c, P = console(FGT)
    errors = []
    for ln in lines:
        out = run_on(c, P, ln, timeout=30)
        for m in re.findall(r"(?:Command fail|error|Unknown action)[^\r\n]*", out):
            # delete 対象が無い等は初期化では正常(冪等) — 記録のみ
            errors.append(f"{ln}  ->  {m}")
    c.close()
    print(f"[{label}] {len(lines)} 行投入 (注意 {len(errors)} 件)")
    return errors


# ---------------------------------------------------------------- verbs

def cmd_build(_):
    client = cml()
    lab = find_lab(client)
    if lab is None:
        sys.exit(f"[build] lab '{TITLE}' が CML に無い。復旧手順は README.md"
                 "(トポロジ=fgt-sdwan-lab.yaml import + eval 再アクティベーション)")
    for n in lab.nodes():
        if n.state != "BOOTED":
            n.start(wait=True)
    errs = fgt_push(UNBUILD, "build/unbuild")
    for e in errs:
        print("  ", e)
    # ライセンス健全性
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
    print("[solve] 完了。SLA 安定まで約30秒待って grade を実行")


def _collect(checks, stage, sessions):
    for chk in checks:
        if chk.get("stage", "normal") != stage:
            continue
        node = chk["node"]
        if node not in sessions:
            try:
                c, P = console(node)
                if node == FGT:
                    run_on(c, P, "config system console", timeout=10)
                    run_on(c, P, "set output standard", timeout=10)
                    run_on(c, P, "end", timeout=10)
                sessions[node] = (c, P)
            except Exception as e:
                sessions[node] = None
                print(f"[grade] {node}: console 失敗 {e}")
        sess = sessions[node]
        if sess is None:
            chk["stdout"] = "(console connect error)"
            continue
        try:
            chk["stdout"] = run_on(*sess, chk["command"], timeout=90)
        except Exception as e:
            chk["stdout"] = f"(execute error: {e})"


def cmd_grade(a):
    grading = yaml.safe_load(open(os.path.join(REPO, "problems", PROBLEM, "grading.yml")))
    checks = grading["checks"]
    client = cml()
    lab = find_lab(client)
    link = wan1_link(lab)
    sessions = {}
    try:
        print("[grade 1/3] 平常時チェック")
        _collect(checks, "normal", sessions)
        if any(c.get("stage") == "degraded" for c in checks):
            print(f"[grade 2/3] WAN1 劣化注入 ({INJECT}) → 35秒待機")
            link.set_condition(**INJECT)
            time.sleep(35)
            _collect(checks, "degraded", sessions)
            print("[grade 3/3] 劣化解除 → フェイルバック待ち(loss移動窓)")
            link.remove_condition()
            # E3 はフェイルバック完了までリトライ(最大4分)
            e3 = [c for c in checks if c.get("stage") == "restored"]
            deadline = time.time() + 240
            while True:
                time.sleep(45)
                _collect(checks, "restored", sessions)
                ok = all(re.search(r"1: Seq_num\(1 port1", c.get("stdout", ""))
                         for c in e3) if e3 else True
                if ok or time.time() > deadline:
                    break
                print("  … フェイルバック未完了・再試行")
    finally:
        try:
            link.remove_condition()
        except Exception:
            pass
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


def cmd_inject(_):
    client = cml()
    wan1_link(find_lab(client)).set_condition(**INJECT)
    print(f"[inject] WAN1 に {INJECT} を注入。restore で解除")


def cmd_restore(_):
    client = cml()
    wan1_link(find_lab(client)).remove_condition()
    print("[restore] 劣化解除(フェイルバックは loss 移動窓クリア後・1〜3分)")


def cmd_status(_):
    client = cml()
    lab = find_lab(client)
    if lab is None:
        print("(CML にラボ無し)")
        return
    for n in lab.nodes():
        print(f"  {n.label:10s} {n.state}")
    try:
        c, P = console(FGT)
        out = run_on(c, P, "get system status | grep -i license")
        c.close()
        print(" ", [l.strip() for l in out.splitlines() if "License" in l])
    except Exception as e:
        print("  (license 確認失敗)", e)


def cmd_stop(_):
    client = cml()
    lab = find_lab(client)
    if lab:
        lab.stop()
        print("[stop] 停止のみ(削除しない: fgt1 のライセンス保全)。再開は build")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)
    for v in ("build", "solve", "inject", "restore", "status", "stop"):
        sub.add_parser(v)
    pg = sub.add_parser("grade")
    pg.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    {"build": cmd_build, "solve": cmd_solve, "grade": cmd_grade,
     "inject": cmd_inject, "restore": cmd_restore,
     "status": cmd_status, "stop": cmd_stop}[a.verb](a)


if __name__ == "__main__":
    main()
