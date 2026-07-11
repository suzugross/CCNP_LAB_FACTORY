#!/usr/bin/env python3
"""BL-041 ASAv HA + ワンアーム PoC ツール (POC-ASAHA)。

usage:
  ha_tools.py up | wait | down
  ha_tools.py bootstrap <fw1|fw2>   … yaml の configuration を console 投入
  ha_tools.py cmd <NODE> "c1" ...   … console 実行 (fw*=ASA, 他=IOS/IOL)
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
YAML_PATH = f"{REPO}/poc/asa-ha/poc-asaha-lab.yaml"
TITLE = "POC-ASAHA"
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
    is_asa = node.startswith("fw")
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
    # ★HA 同期後は fw1/fw2 とも hostname=fwha になる → ホスト名可変でматッチ
    P = r"(\r\n|\r|\n)([\w-]+)(\([\w./-]+\))?([>#]) ?"
    for _ in range(15):
        idx = c.expect([r"Enter  Password:", r"Repeat Password:", r"Passwords do not match",
                        P, r"assword:", r"initial configuration dialog", pexpect.TIMEOUT],
                       timeout=15)
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


def run_cmds(node, cmds, timeout=90):
    c, P = console(node)
    time.sleep(1)
    try:
        while True:
            c.read_nonblocking(size=4096, timeout=1)
    except Exception:
        pass
    c.logfile_read = sys.stdout
    pager = "terminal pager 0" if node.startswith("fw") else "terminal length 0"
    for cmd in [pager] + list(cmds):
        c.send(cmd + "\r")
        for _ in range(5):
            c.expect(P, timeout=timeout)
            if cmd.split()[0] in (c.before or ""):
                break
    c.close()


def bootstrap(node):
    doc = yaml.safe_load(open(YAML_PATH))
    nd = next(n for n in doc["nodes"] if n["id"] == node)
    cfg = nd["configuration"]
    if isinstance(cfg, list):
        cfg = cfg[0]["content"]
    lines = [l for l in cfg.splitlines() if l.strip() and l.strip() != "!"]
    c, P = console(node)
    print(f"[bootstrap {node}] priv exec OK。{len(lines)} 行投入")
    errors = []
    c.send("configure terminal\r")
    c.expect(r"\(config\)# ", timeout=10)
    for ln in lines:
        c.send(ln + "\r")
        # `failover` 有効化直後は複製等で時間がかかることがある
        c.expect(r"(?:\(config[^)]*\))?# ", timeout=60)
        for m in re.findall(r"(?:ERROR|WARNING)[:%].*", c.before or ""):
            errors.append(f"{ln}  ->  {m}")
    c.send("end\r")
    c.expect(r"# ", timeout=15)
    c.send("write memory\r")
    c.expect(r"\[OK\]|# ", timeout=60)
    c.close()
    print(f"[bootstrap {node}] 完了" + ("" if not errors else f" / ERROR・WARNING {len(errors)} 件"))
    for e in errors:
        print("  ", e)


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
    bootstrap(sys.argv[2])
elif cmd == "cmd":
    run_cmds(sys.argv[2], sys.argv[3:])
