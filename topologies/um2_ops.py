#!/usr/bin/env python3
"""UM2-BUILD-01 運用 CLI (BL-042)。

  build     … スケルトン lab を CML に import + start（据付ノードのみ設定済み）
  grade     … grading.yml を記載順に console 収集して grade.py で採点(100点)
  solve     … ★検証/模範解答提示用: golden(poc/um2/poc-um2-lab.yaml) を
               受講者ノード6台へ console 投入（L3SW/LB=IOS push, FW=bootstrap）
  status    … ノード状態
  destroy   … ラボ削除

収集は全ノード CML コンソール（MGMT/リース不要）。alpine は root シェル。
IOS/ASA 認証: SUZUKI/CCNPccnp（ASA 初回 enable ウィザードも処理）。
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
    import os as _os
    d = _y.safe_load(open(_os.path.join(repo, "group_vars", "all", "local.yml")))
    return d["cml_host"], d["cml_username"], d["cml_password"]
PROBLEM = "UM2-BUILD-01"
TITLE = "UM2-BUILD-01"
SKELETON = os.path.join(REPO, "problems", PROBLEM, "lab-skeleton.yaml")
GOLDEN = os.path.join(REPO, "poc", "um2", "poc-um2-lab.yaml")
GEN_DIR = os.path.join(REPO, "topologies", "_generated", PROBLEM)
PY = os.path.join(REPO, ".venv", "bin", "python3")

CML_HOST, CML_USER, CML_PASS = _cml_creds(REPO)
NODE_PW = "CCNPccnp"
ALPINE = {"USER-PC", "DMZ-SV"}
ASA = {"FW1", "FW2"}
STUDENT_IOS = ["L3SW1", "L3SW2", "LB1", "LB2"]

P_NET = r"(\r\n|\r|\n)([\w/-]+)(\([\w./-]+\))?([>#]) ?"
P_ALP = r"(\r\n|\r|\n)[\w-]+:[^\r\n]*# ?"


def cml():
    from virl2_client import ClientLibrary
    return ClientLibrary(f"https://{CML_HOST}", CML_USER, CML_PASS, ssl_verify=False)


def find_lab(client):
    for lab in client.all_labs():
        if lab.title == TITLE:
            return lab
    return None


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
        c.send("\r")
        for _ in range(10):
            idx = c.expect([r"login:", P_ALP, pexpect.TIMEOUT], timeout=12)
            if idx == 0:
                c.send("root\r")
            elif idx == 1:
                return c, P_ALP
            else:
                c.send("\r")
        raise RuntimeError(f"{node}: alpine シェル不達")
    c.send("end\r")
    time.sleep(1)
    c.send("\r")
    for _ in range(15):
        idx = c.expect([r"Enter  Password:", r"Repeat Password:", r"Passwords do not match",
                        P_NET, r"assword:", r"initial configuration dialog", pexpect.TIMEOUT],
                       timeout=15)
        if idx in (0, 1):
            time.sleep(0.5)
            c.send(NODE_PW + "\r")
        elif idx == 2:
            continue
        elif idx == 3:
            if c.match.group(4) == "#":
                return c, P_NET
            c.send("enable\r")
        elif idx == 4:
            c.send(NODE_PW + "\r")
        elif idx == 5:
            c.send("no\r")
        else:
            c.send("\r")
    raise RuntimeError(f"{node}: priv exec 不達")


def _drain(c):
    time.sleep(1)
    try:
        while True:
            c.read_nonblocking(size=4096, timeout=1)
    except Exception:
        pass


def run_on(c, P, node, cmd, timeout=90):
    """1コマンド実行して出力を返す（エコー再同期つき）。"""
    c.send(cmd + "\r")
    out = ""
    for _ in range(5):
        c.expect(P, timeout=timeout)
        out = c.before or ""
        if cmd.split()[0] in out:
            break
    return out


def push_config(node, lines, save=True):
    """IOS ノードへ config を1行ずつ投入。"""
    c, P = console(node)
    _drain(c)
    errors = []
    c.send("configure terminal\r")
    c.expect(r"\(config\)#", timeout=15)
    for ln in lines:
        c.send(ln + "\r")
        c.expect(r"(?:\(config[^)]*\))?# ?", timeout=60)
        for m in re.findall(r"% ?(?:Invalid|Incomplete|Ambiguous).*", c.before or ""):
            errors.append(f"{ln}  ->  {m}")
    c.send("end\r")
    c.expect(P, timeout=15)
    if save:
        c.send("write memory\r")
        c.expect(r"\[OK\]|# ?", timeout=60)
    c.close()
    return errors


def asa_bootstrap(node, cfg):
    lines = [l for l in cfg.splitlines() if l.strip() and l.strip() != "!"]
    c, P = console(node)
    print(f"[solve {node}] {len(lines)} 行投入")
    errors = []
    c.send("configure terminal\r")
    c.expect(r"\(config\)# ", timeout=10)
    for ln in lines:
        c.send(ln + "\r")
        c.expect(r"(?:\(config[^)]*\))?# ", timeout=60)
        for m in re.findall(r"(?:ERROR|WARNING)[:%].*", c.before or ""):
            errors.append(f"{ln}  ->  {m}")
    c.send("end\r")
    c.expect(r"# ", timeout=15)
    c.send("write memory\r")
    c.expect(r"\[OK\]|# ", timeout=60)
    c.close()
    for e in errors:
        print("  ", e)


# ---------------------------------------------------------------- verbs

def cmd_build(_):
    client = cml()
    lab = find_lab(client)
    if lab is None:
        lab = client.import_lab_from_path(SKELETON, title=TITLE)
        print(f"[build] imported: {lab.id}")
    lab.start(wait=False)
    deadline = time.time() + 720
    while time.time() < deadline:
        states = {n.label: n.state for n in lab.nodes()}
        print(states, flush=True)
        if all(s == "BOOTED" for s in states.values()):
            print("[build] 完了。受講者へ task.md を提示してください"
                  "（FW は工場出荷状態・IOS はホスト名+ログインのみ設定済み）")
            return
        time.sleep(20)
    sys.exit("[build] boot TIMEOUT")


def cmd_solve(_):
    """模範解答を受講者ノードへ投入（検証用）。"""
    doc = yaml.safe_load(open(GOLDEN))
    cfg = {n["id"]: (n["configuration"][0]["content"]
                     if isinstance(n["configuration"], list) else n["configuration"])
           for n in doc["nodes"]}
    for node in STUDENT_IOS:
        lines = [l for l in cfg[node].splitlines() if l.strip() and l.strip() != "!"]
        print(f"[solve {node}] {len(lines)} 行投入")
        errs = push_config(node, lines)
        for e in errs:
            print("  ", e)
    asa_bootstrap("FW1", cfg["FW1"])
    asa_bootstrap("FW2", cfg["FW2"])
    print("[solve] 完了。フェールオーバー同期(約1分)と HSRP 収束後に grade を実行")


def cmd_grade(a):
    grading = yaml.safe_load(open(os.path.join(REPO, "problems", PROBLEM, "grading.yml")))
    checks = grading["checks"]
    sessions = {}
    try:
        for chk in checks:
            node = chk["node"]
            if node not in sessions:
                try:
                    c, P = console(node)
                    _drain(c)
                    if node not in ALPINE:
                        run_on(c, P, node,
                               "terminal pager 0" if node in ASA else "terminal length 0",
                               timeout=15)
                    sessions[node] = (c, P)
                except Exception as e:
                    sessions[node] = None
                    print(f"[grade] {node}: console 接続失敗 {e}")
            sess = sessions[node]
            if sess is None:
                chk["stdout"] = "(console connect error)"
                continue
            c, P = sess
            try:
                chk["stdout"] = run_on(c, P, node, chk["command"])
            except Exception as e:
                chk["stdout"] = f"(execute error: {e})"
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
    client = cml()
    lab = find_lab(client)
    if lab is None:
        print("(CML にラボ無し)")
        return
    for n in lab.nodes():
        print(f"  {n.label:9s} {n.state}")


def cmd_destroy(_):
    client = cml()
    lab = find_lab(client)
    if lab:
        lab.stop()
        lab.wipe()
        lab.remove()
        print("[destroy] lab removed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="verb", required=True)
    sub.add_parser("build")
    sub.add_parser("solve")
    pg = sub.add_parser("grade")
    pg.add_argument("--gate", action="store_true")
    sub.add_parser("status")
    sub.add_parser("destroy")
    a = ap.parse_args()
    {"build": cmd_build, "solve": cmd_solve, "grade": cmd_grade,
     "status": cmd_status, "destroy": cmd_destroy}[a.verb](a)


if __name__ == "__main__":
    main()
