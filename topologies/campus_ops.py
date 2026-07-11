#!/usr/bin/env python3
"""CAMPUS-TS-01 運用 CLI (BL-040)。指示書 DoD の1コマンド往復を提供する。

  build              … リース確保 → golden 生成 → CML import+start → ASA bootstrap
  inject <fault>     … fault を注入（差分ノードのみ day0 差し替え + wipe + 再起動）
  reset              … golden へ戻す（同上）
  grade [--gate]     … grading.yml を収集(console+ssh混成)して grade.py で採点
  status             … ノード状態と現在の fault
  destroy            … ラボ削除 + リース解放

前提知見: ASAv は day0 不発 → console bootstrap（poc/asav/README.md）。
IOS/ASA の収集は collect_console.py（クレデンシャルは本問で CCNPccnp に統一）、
Linux(svr1/cli*) は SSH(paramiko) で exec: shell を収集する。
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_campus_lab as gen  # noqa: E402

PROBLEM = gen.PROBLEM
TITLE = gen.LAB_TITLE
GEN_DIR = os.path.join(REPO, "topologies", "_generated", PROBLEM)
PY = os.path.join(REPO, ".venv", "bin", "python3")

CML_HOST, CML_USER, CML_PASS = _cml_creds(REPO)
NODE_USER, NODE_PASS = "SUZUKI", "CCNPccnp"   # IOS/ASA 統一（本問規約）
LINUX_USER, LINUX_PASS = "suzuki", "CCNP"
CISCO_NODES = {"core1", "core2", "dist1", "dist2", "acc1", "acc2", "asa1"}


def cml():
    from virl2_client import ClientLibrary
    return ClientLibrary(f"https://{CML_HOST}", CML_USER, CML_PASS, ssl_verify=False)


def find_lab(client):
    for lab in client.all_labs():
        if lab.title == TITLE:
            return lab
    return None


def run_gen(fault):
    subprocess.run([PY, os.path.join(REPO, "topologies", "gen_campus_lab.py"),
                    "--repo", REPO, "--fault", fault], check=True)


def load_state():
    p = os.path.join(GEN_DIR, "state.json")
    return json.load(open(p)) if os.path.exists(p) else {"fault": "none"}


# ---------------------------------------------------------------- console

def console(node, timeout=30):
    """CML console → priv exec。ASA 初回 enable ウィザード(8字)も処理。"""
    c = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {CML_USER}@{CML_HOST}",
        encoding="utf-8", codec_errors="replace", timeout=timeout)
    c.expect("assword:")
    c.sendline(CML_PASS)
    c.expect("consoles>")
    c.sendline(f"open /{TITLE}/{node}/0")
    c.expect("Escape character")
    time.sleep(2)
    c.send("end\r")
    time.sleep(1)
    c.send("\r")
    P = r"(\r\n|\r|\n)([\w-]+)(\([\w./-]+\))?([>#]) ?"
    for _ in range(15):
        idx = c.expect([r"Enter  Password:", r"Repeat Password:", r"Passwords do not match",
                        P, r"assword:", r"initial configuration dialog", pexpect.TIMEOUT],
                       timeout=15)
        if idx in (0, 1):
            time.sleep(0.5)
            c.send(NODE_PASS + "\r")
        elif idx == 2:
            continue
        elif idx == 3:
            if c.match.group(4) == "#":
                return c, P
            c.send("enable\r")
        elif idx == 4:
            c.send(NODE_PASS + "\r")
        elif idx == 5:
            c.send("no\r")
        else:
            c.send("\r")
    raise RuntimeError(f"{node}: priv exec に到達できず")


def asa_bootstrap():
    """lab.yaml の asa1 正準 config を console 投入して保存。"""
    doc = yaml.safe_load(open(os.path.join(GEN_DIR, "lab.yaml")))
    node = next(n for n in doc["nodes"] if n["id"] == "asa1")
    cfg = node["configuration"]
    if isinstance(cfg, list):
        cfg = cfg[0]["content"]
    lines = [l for l in cfg.splitlines() if l.strip() and l.strip() != "!"]
    c, P = console("asa1")
    print(f"[asa_bootstrap] priv exec OK。{len(lines)} 行投入")
    errors = []
    c.send("configure terminal\r")
    c.expect(r"\(config\)# ", timeout=10)
    for ln in lines:
        c.send(ln + "\r")
        c.expect(r"(?:\(config[^)]*\))?# ", timeout=15)
        for m in re.findall(r"(?:ERROR|WARNING)[:%].*", c.before or ""):
            errors.append(f"{ln}  ->  {m}")
    c.send("end\r")
    c.expect(r"# ", timeout=10)
    c.send("write memory\r")
    c.expect(r"\[OK\]", timeout=30)
    c.close()
    print("[asa_bootstrap] write memory 完了" + ("" if not errors else f" / 警告 {len(errors)} 件"))
    for e in errors:
        print("  ", e)


def wait_booted(lab, labels=None, timeout=720):
    deadline = time.time() + timeout
    while time.time() < deadline:
        states = {n.label: n.state for n in lab.nodes()}
        tgt = {k: v for k, v in states.items() if (labels is None or k in labels)}
        print(tgt, flush=True)
        if all(v == "BOOTED" for v in tgt.values()):
            return True
        time.sleep(20)
    return False


# ---------------------------------------------------------------- verbs

def cmd_build(_):
    os.makedirs(GEN_DIR, exist_ok=True)
    subprocess.run([PY, os.path.join(REPO, "topologies", "mgmt_alloc.py"),
                    "allocate", "--repo", REPO, "--problem", PROBLEM,
                    "--nodes", ",".join(gen.NODES),
                    "--out", os.path.join(GEN_DIR, "mgmt_map.yml")], check=True)
    run_gen("none")
    client = cml()
    lab = find_lab(client)
    if lab is None:
        lab = client.import_lab_from_path(os.path.join(GEN_DIR, "lab.yaml"), title=TITLE)
        print(f"[build] imported: {lab.id}")
    lab.start(wait=False)
    print("[build] start requested → BOOTED 待ち")
    if not wait_booted(lab):
        sys.exit("[build] boot TIMEOUT")
    asa_bootstrap()
    print("[build] 完了。OSPF/HSRP/cloud-init 収束後に grade を実行してください"
          "（svr1 の apt は数分かかる）")


def _replace_nodes(fault_new):
    """day0 差し替え方式の注入/解除。差分ノードのみ wipe+再起動。"""
    prev = load_state().get("fault", "none")
    nodes_prev = set(gen.FAULT_NODES.get(prev, []))
    run_gen(fault_new)
    nodes_new = set(gen.FAULT_NODES.get(fault_new, []))
    targets = sorted(nodes_prev | nodes_new)
    if not targets:
        print("[inject] 差分ノード無し（golden→golden）")
        return
    doc = yaml.safe_load(open(os.path.join(GEN_DIR, "lab.yaml")))
    cfg_by_label = {n["id"]: n["configuration"] for n in doc["nodes"]}
    client = cml()
    lab = find_lab(client)
    if lab is None:
        sys.exit("[inject] ラボが CML にありません（先に build）")
    for label in targets:
        node = next(n for n in lab.nodes() if n.label == label)
        print(f"[inject] {label}: stop → wipe → config 差し替え → start")
        node.stop(wait=True)
        node.wipe()
        node.configuration = cfg_by_label[label]
        node.start(wait=False)
    if not wait_booted(lab, labels=set(targets)):
        sys.exit("[inject] boot TIMEOUT")
    if "asa1" in targets:
        asa_bootstrap()
    print(f"[inject] fault={fault_new} 反映完了（対象: {', '.join(targets)}）。"
          "OSPF/HSRP 収束に 1〜2 分見てください")


def cmd_inject(a):
    if a.fault not in gen.FAULTS:
        sys.exit(f"unknown fault: {a.fault}（{'/'.join(gen.FAULTS)}）")
    _replace_nodes(a.fault)


def cmd_reset(_):
    _replace_nodes("none")


def _ssh_shell(host, command, timeout=120):
    import paramiko
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(host, username=LINUX_USER, password=LINUX_PASS,
                timeout=15, banner_timeout=30, auth_timeout=30,
                look_for_keys=False, allow_agent=False)
    try:
        _, out, err = cli.exec_command(command, timeout=timeout)
        return out.read().decode(errors="replace") + err.read().decode(errors="replace")
    finally:
        cli.close()


def cmd_grade(a):
    grading = yaml.safe_load(open(os.path.join(REPO, "problems", PROBLEM, "grading.yml")))
    checks = grading["checks"]
    mgmt = yaml.safe_load(open(os.path.join(GEN_DIR, "mgmt_map.yml")))

    cisco_checks = [c for c in checks if c.get("exec") != "shell" and c["node"] != "asa1"]
    asa_checks = [c for c in checks if c.get("exec") != "shell" and c["node"] == "asa1"]
    shell_checks = [c for c in checks if c.get("exec") == "shell"]

    # 0) ASA: unicon は ASA コンソールの非UTF8バイトで Decode failure になるため
    #    pexpect(codec_errors=replace) の自前コンソールで収集する
    if asa_checks:
        c, P = console("asa1")
        c.send("terminal pager 0\r")
        c.expect(P, timeout=10)
        for chk in asa_checks:
            c.send(chk["command"] + "\r")
            out = ""
            for _ in range(5):
                c.expect(P, timeout=60)
                out = c.before or ""
                if chk["command"].split()[0] in out:
                    break
            chk["stdout"] = out
        c.close()

    # 1) IOS: collect_console.py（testbed 経由・unicon）
    if cisco_checks:
        cj = os.path.join(GEN_DIR, "checks_console.json")
        oj = os.path.join(GEN_DIR, "out_console.json")
        json.dump(cisco_checks, open(cj, "w"), ensure_ascii=False)
        env = dict(os.environ,
                   CML_HOST=CML_HOST, CML_USER=CML_USER, CML_PASS=CML_PASS,
                   CML_VERIFY="false", LAB_TITLE=TITLE,
                   NODE_USER=NODE_USER, NODE_PASS=NODE_PASS, NODE_ENABLE=NODE_PASS)
        subprocess.run([PY, os.path.join(REPO, "topologies", "collect_console.py"),
                        cj, oj], check=True, env=env)
        cisco_checks = json.load(open(oj))

    # 2) Linux: SSH で shell 実行
    for chk in shell_checks:
        host = mgmt[chk["node"]]
        try:
            chk["stdout"] = _ssh_shell(host, chk["command"])
        except Exception as e:
            chk["stdout"] = f"(ssh error: {e})"

    # 元の順序でマージ
    merged, ci, si, ai = [], iter(cisco_checks), iter(shell_checks), iter(asa_checks)
    for c in checks:
        if c.get("exec") == "shell":
            merged.append(next(si))
        elif c["node"] == "asa1":
            merged.append(next(ai))
        else:
            merged.append(next(ci))
    gi = os.path.join(GEN_DIR, "grade_input.json")
    json.dump(merged, open(gi, "w"), ensure_ascii=False, indent=1)

    argv = [PY, os.path.join(REPO, "topologies", "grade.py"), gi]
    if a.gate:
        argv.append("--gate")
    rc = subprocess.run(argv).returncode
    sys.exit(rc)


def cmd_status(_):
    client = cml()
    lab = find_lab(client)
    st = load_state()
    print(f"problem={PROBLEM} fault={st.get('fault')}")
    if lab is None:
        print("(CML にラボ無し)")
        return
    for n in lab.nodes():
        print(f"  {n.label:8s} {n.state}")


def cmd_destroy(_):
    client = cml()
    lab = find_lab(client)
    if lab:
        lab.stop()
        lab.wipe()
        lab.remove()
        print("[destroy] lab removed")
    subprocess.run([PY, os.path.join(REPO, "topologies", "mgmt_alloc.py"),
                    "release", "--repo", REPO, "--problem", PROBLEM], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="verb", required=True)
    sub.add_parser("build")
    pi = sub.add_parser("inject")
    pi.add_argument("fault")
    sub.add_parser("reset")
    pg = sub.add_parser("grade")
    pg.add_argument("--gate", action="store_true")
    sub.add_parser("status")
    sub.add_parser("destroy")
    a = ap.parse_args()
    {"build": cmd_build, "inject": cmd_inject, "reset": cmd_reset,
     "grade": cmd_grade, "status": cmd_status, "destroy": cmd_destroy}[a.verb](a)


if __name__ == "__main__":
    main()
