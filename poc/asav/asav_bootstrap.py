#!/usr/bin/env python3
"""ASAv へコンソール経由で初期 config を投入する (day0 代替・BL-038)。

lab yaml の FW01 configuration を読み、パスワードを ASA ポリシー(8字以上)に
置換してから configure terminal で1行ずつ流し込む。ERROR 行は収集して報告。
"""
import pexpect

def _cml_creds(repo):
    """CML 認証は gitignore 済みの group_vars/all/local.yml から読む(ハードコード禁止)。"""
    import yaml as _y
    import os as _os
    d = _y.safe_load(open(_os.path.join(repo, "group_vars", "all", "local.yml")))
    return d["cml_host"], d["cml_username"], d["cml_password"]

CML_HOST, CML_USER, CML_PASS = _cml_creds("/home/suzuki/ansible/CCNP01")
import re
import sys
import time

import yaml

LAB_YAML = "/home/suzuki/ansible/CCNP01/poc/asav/poc-asav-lab.yaml"
ASA_PW = "CCNPccnp"

doc = yaml.safe_load(open(LAB_YAML))
fw = next(n for n in doc["nodes"] if n["id"] == "FW01")
cfg = fw["configuration"]
if isinstance(cfg, list):
    cfg = cfg[0]["content"]
cfg = cfg.replace("enable password CCNP\n", f"enable password {ASA_PW}\n")
cfg = cfg.replace("username SUZUKI password CCNP privilege 15",
                  f"username SUZUKI password {ASA_PW} privilege 15")
lines = [l for l in cfg.splitlines() if l.strip() and l.strip() != "!"]

c = pexpect.spawn(
    f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {CML_USER}@{CML_HOST}",
    encoding="utf-8", codec_errors="replace", timeout=30)
c.expect("assword:")
c.sendline(CML_PASS)
c.expect("consoles>")
c.sendline("open /POC-ASAV/FW01/0")
c.expect("Escape character")
time.sleep(2)
c.send("end\r")
time.sleep(1)
c.send("\r")

# priv exec へ (初回 enable ウィザード対応)
reached = False
for _ in range(15):
    idx = c.expect([r"Enter  Password:", r"Repeat Password:", r"Passwords do not match",
                    r"(\r\n|\r|\n)[\w-]+(\([\w./-]+\))?> ", r"(\r\n|\r|\n)[\w-]+(\([\w./-]+\))?# ",
                    r"assword:", pexpect.TIMEOUT], timeout=12)
    if idx in (0, 1):
        time.sleep(0.5)
        c.send(ASA_PW + "\r")
    elif idx == 3:
        c.send("enable\r")
    elif idx == 4:
        reached = True
        break
    elif idx == 5:
        c.send(ASA_PW + "\r")
    elif idx == 6:
        c.send("\r")
if not reached:
    print("[FAIL] priv exec に到達できず")
    sys.exit(1)
print(f"[OK] priv exec。config {len(lines)} 行を投入")

errors = []
c.send("configure terminal\r")
c.expect(r"\(config\)# ", timeout=10)
for ln in lines:
    c.send(ln + "\r")
    c.expect(r"(?:\(config[^)]*\))?# ", timeout=15)
    out = c.before or ""
    for m in re.findall(r"(ERROR|WARNING|INFO)[:%].*", out):
        errors.append(f"{ln}  ->  {m}")
c.send("end\r")
c.expect(r"# ", timeout=10)
c.send("write memory\r")
c.expect(r"\[OK\]", timeout=30)
c.expect(r"# ", timeout=10)
print("[OK] write memory 完了")
if errors:
    print("\n== 投入時の ERROR/WARNING ==")
    for e in errors:
        print(" ", e)
else:
    print("エラー無し")
c.close()
