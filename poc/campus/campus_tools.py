#!/usr/bin/env python3
"""BL-040 Phase 0 プローブ用ツール (POC-CAMPUS0)。

usage:
  campus_tools.py up                    … import + start
  campus_tools.py wait                  … 全ノード BOOTED まで待つ
  campus_tools.py down                  … stop/wipe/remove
  campus_tools.py bootstrap             … FW01 に yaml の config を console 投入
  campus_tools.py cmd <NODE> "c1" "c2"  … console でコマンド実行 (IOS/ASA 自動判別)
"""
import re
import sys
import time

import pexpect
import urllib3
import yaml

urllib3.disable_warnings()

REPO = "/home/suzuki/ansible/CCNP01"

def _cml_creds(repo):
    """CML 認証は gitignore 済みの group_vars/all/local.yml から読む(ハードコード禁止)。"""
    import yaml as _y
    import os as _os
    d = _y.safe_load(open(_os.path.join(repo, "group_vars", "all", "local.yml")))
    return d["cml_host"], d["cml_username"], d["cml_password"]

CML_HOST, CML_USER, CML_PASS = _cml_creds(REPO)
YAML_PATH = f"{REPO}/poc/campus/poc-campus-phase0-lab.yaml"
TITLE = "POC-CAMPUS0"
ASA_NODES = {"FW01"}
ASA_PW = "CCNPccnp"
IOS_EN = "CCNP"


def cml():
    from virl2_client import ClientLibrary
    return ClientLibrary(f"https://{CML_HOST}", CML_USER, CML_PASS, ssl_verify=False)


def find_lab(client):
    for lab in client.all_labs():
        if lab.title == TITLE:
            return lab
    return None


def console(node):
    """CML コンソールへ接続し priv exec で返す。(spawn, prompt_regex)"""
    c = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {CML_USER}@{CML_HOST}",
        encoding="utf-8", codec_errors="replace", timeout=30)
    c.expect("assword:")
    c.sendline(CML_PASS)
    c.expect("consoles>")
    c.sendline(f"open /{TITLE}/{node}/0")
    c.expect("Escape character")
    time.sleep(2)
    c.send("end\r")
    time.sleep(1)
    c.send("\r")
    # ホスト名は day0 未適用の ASA では ciscoasa のままなので汎用にマッチ
    P = r"(\r\n|\r|\n)([\w-]+)(\([\w./-]+\))?([>#]) ?"
    is_asa = node in ASA_NODES
    for _ in range(15):
        idx = c.expect([r"Enter  Password:", r"Repeat Password:", r"Passwords do not match",
                        P, r"assword:", r"Would you like to enter the initial configuration",
                        pexpect.TIMEOUT], timeout=15)
        if idx in (0, 1):
            time.sleep(0.5)
            c.send(ASA_PW + "\r")
        elif idx == 2:
            continue
        elif idx == 3:
            if c.match.group(4) == "#":
                return c, P
            c.send("enable\r")
        elif idx == 4:
            c.send((ASA_PW if is_asa else IOS_EN) + "\r")
        elif idx == 5:
            c.send("no\r")
        else:
            c.send("\r")
    raise RuntimeError(f"{node}: priv exec に到達できず")


def run_cmds(node, cmds):
    c, P = console(node)
    # 残プロンプトを掃く(console()のリトライ\rで余剰プロンプトが積まれる)
    time.sleep(1)
    try:
        while True:
            c.read_nonblocking(size=4096, timeout=1)
    except Exception:
        pass
    c.logfile_read = sys.stdout
    pager = "terminal pager 0" if node in ASA_NODES else "terminal length 0"
    for cmd in [pager] + list(cmds):
        c.send(cmd + "\r")
        for _ in range(5):
            c.expect(P, timeout=90)
            if cmd.split()[0] in (c.before or ""):
                break
    c.close()


cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

if cmd == "up":
    client = cml()
    lab = find_lab(client)
    if lab is None:
        lab = client.import_lab_from_path(YAML_PATH, title=TITLE)
        print(f"imported: {lab.id}")
    lab.start(wait=False)
    print("start requested")
elif cmd == "wait":
    client = cml()
    lab = find_lab(client)
    deadline = time.time() + 720
    while time.time() < deadline:
        states = {n.label: n.state for n in lab.nodes()}
        print(states, flush=True)
        if all(s == "BOOTED" for s in states.values()):
            print("ALL BOOTED")
            sys.exit(0)
        time.sleep(20)
    print("TIMEOUT")
    sys.exit(2)
elif cmd == "down":
    client = cml()
    lab = find_lab(client)
    if lab:
        lab.stop()
        lab.wipe()
        lab.remove()
        print("lab removed")
elif cmd == "bootstrap":
    doc = yaml.safe_load(open(YAML_PATH))
    fw = next(n for n in doc["nodes"] if n["id"] == "FW01")
    cfg = fw["configuration"]
    if isinstance(cfg, list):
        cfg = cfg[0]["content"]
    lines = [l for l in cfg.splitlines() if l.strip() and l.strip() != "!"]
    c, P = console("FW01")
    print(f"[OK] priv exec。config {len(lines)} 行を投入")
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
    print("[OK] write memory 完了")
    if errors:
        print("== ERROR/WARNING ==")
        for e in errors:
            print(" ", e)
    else:
        print("エラー無し")
    c.close()
elif cmd == "cmd":
    run_cmds(sys.argv[2], sys.argv[3:])
