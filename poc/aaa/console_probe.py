#!/usr/bin/env python3
"""BL-101 P0 追試: **コンソール(line con 0)の認証挙動**を実測する。

紙面 shape=aaa の要件世界 `console_survives`(サーバ全断でも console からは入れること)を
観測可能にするために必要な事実を採る。vty で確定済みの規則が console にも同じく効くのか、
console 専用の方式リストを当てたときにどうなるのかを、実機で確かめる。

使い方: console_probe.py            (全ケース)
"""
import os
import re
import sys
import time
from pathlib import Path

import paramiko
import yaml
from pyats.topology import loader
from virl2_client import ClientLibrary

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-console.md"

CML = os.environ.get("CML_HOST", "10.1.10.10")
CML_USER = os.environ.get("CML_USER", "admin")
CML_PASS = os.environ.get("CML_PASS", "CCNP")
ADMIN, ADMIN_PW = "SUZUKI", "CCNP"
LOCAL_ONLY, LOCAL_ONLY_PW = "emg-admin", "Emg-1234"
RAD_USER, RAD_PW = "noc-taro", "Noc-1234"


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


def lab_title():
    y = yaml.safe_load((GEN / "lab.yaml").read_text())
    return (y.get("lab") or {}).get("title") or os.environ.get("LAB_TITLE", "")


class Router:
    """設定投入は SSH(制御セッション)で行う。console は観測専用に使う。"""

    def __init__(self, ip):
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                         allow_agent=False, timeout=40)
        self.sh = self.cli.invoke_shell(width=511)
        self._expect()
        self.send("terminal length 0")

    def _expect(self, timeout=120):
        t0, buf = time.time(), ""
        while time.time() - t0 < timeout:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
                lines = buf.splitlines()
                if lines and re.search(r"[\w.\-]+(\([\w\-]+\))?#\s*$", lines[-1]):
                    return buf
            else:
                time.sleep(0.05)
        return buf

    def send(self, cmd):
        self.sh.send(cmd + "\n")
        return self._expect()

    def conf(self, lines):
        self.send("configure terminal")
        for ln in lines:
            self.send(ln)
        self.send("end")

    def show(self, cmd):
        out = self.send(cmd)
        return "\n".join(out.splitlines()[1:-1]).strip()

    def close(self):
        try:
            self.cli.close()
        except Exception:
            pass


def console_login(testbed, node, user, pw):
    """★コンソールで実際にログインを試し、可否と権限レベルを返す。

    pyATS は接続時に testbed の credentials でログインするので、
    「その資格情報で console に入れるか」がそのまま接続成否になる。
    """
    dev = testbed.devices[node]
    dev.credentials["default"] = {"username": user, "password": pw}
    dev.credentials["enable"] = {"password": ADMIN_PW}
    try:
        dev.connect(via="a", log_stdout=False, learn_hostname=False,
                    connection_timeout=60)
    except Exception as ex:
        # ★接続失敗時も必ず切る。切らずに抜けると CML 側のコンソールセッションが
        #   残り、**次のケースがログインできなくなる**(2026-08-08 X9 で発覚。
        #   X9a/X9b の LOGIN_FAIL はこの取りこぼしが原因の可能性が高い)。
        try:
            dev.disconnect()
        except Exception:
            pass
        return "LOGIN_FAIL", f"{type(ex).__name__}"
    try:
        out = dev.execute("show privilege", timeout=40)
        m = re.search(r"privilege level is (\d+)", out or "")
        return "OK", f"priv={m.group(1) if m else '?'}"
    except Exception as ex:
        return "EXEC_FAIL", f"{type(ex).__name__}"
    finally:
        try:
            dev.configure("logging console")
        except Exception:
            pass
        try:
            dev.sendline("exit")
        except Exception:
            pass
        try:
            dev.disconnect()
        except Exception:
            pass


def main():
    h = hosts()
    cl = ClientLibrary(f"https://{CML}", CML_USER, CML_PASS, ssl_verify=False)
    title = lab_title()
    labs = [x for x in cl.all_labs() if x.title == title] if title else \
        [x for x in cl.all_labs() if "_POC-AAA" in (x.notes or "") or x.title]
    lab = None
    for cand in labs:
        if {n.label for n in cand.nodes()} >= {"RT01", "RT02", "SRV01", "SRV02"}:
            lab = cand
            break
    if lab is None:
        sys.exit("_POC-AAA のラボが CML に見つかりません")
    tb = yaml.safe_load(lab.get_pyats_testbed())
    for name, dev in (tb.get("devices") or {}).items():
        creds = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            creds["default"] = {"username": CML_USER, "password": CML_PASS}
    testbed = loader.load(tb)
    node = [n for n in testbed.devices if n.startswith("RT02")][0]

    rt = Router(h["RT02"])
    srv = []
    for ip in (h["SRV01"], h["SRV02"]):
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(ip, username=ADMIN, password=ADMIN_PW, look_for_keys=False,
                  allow_agent=False, timeout=30)
        srv.append(c)

    def svc(action):
        for c in srv:
            i, o, e = c.exec_command(f"sudo -n systemctl {action} freeradius",
                                     timeout=60)
            o.read()
        time.sleep(3)

    rows = []
    try:
        # C1: 基線(console に専用リスト無し = default が効く) × サーバ生存
        rows.append(("C1 console: default(group+local) / サーバ生存 / local のみの利用者",
                     *console_login(testbed, node, LOCAL_ONLY, LOCAL_ONLY_PW)))
        rows.append(("C1 console: 同上 / RADIUS 台帳の利用者",
                     *console_login(testbed, node, RAD_USER, RAD_PW)))
        # C2: サーバ全断 → console は local へ落ちるか
        svc("stop")
        rows.append(("C2 console: default(group+local) / **サーバ全断** / local のみ",
                     *console_login(testbed, node, LOCAL_ONLY, LOCAL_ONLY_PW)))
        svc("start")
        # C3: console 専用リスト(local)を当てる × サーバ生存
        rt.conf(["aaa authentication login CONSOLE local",
                 "line con 0", " login authentication CONSOLE", "exit"])
        rows.append(("C3 console: 専用リスト CONSOLE=local / サーバ生存 / local のみ",
                     *console_login(testbed, node, LOCAL_ONLY, LOCAL_ONLY_PW)))
        rows.append(("C3 console: 同上 / RADIUS のみの利用者",
                     *console_login(testbed, node, RAD_USER, RAD_PW)))
        # C4: 専用リストのまま全断 → console は生存するか(= console_survives の核心)
        svc("stop")
        rows.append(("C4 console: 専用リスト CONSOLE=local / **サーバ全断** / local のみ",
                     *console_login(testbed, node, LOCAL_ONLY, LOCAL_ONLY_PW)))
        svc("start")
        # C5: 未定義リストを console に当てる(vty の E15 と同じ規則か)
        rt.conf(["line con 0", " login authentication NOEXIST", "exit"])
        rows.append(("C5 console: **未定義リスト**参照 / サーバ生存 / local のみ",
                     *console_login(testbed, node, LOCAL_ONLY, LOCAL_ONLY_PW)))
        rows.append(("C5 console: 同上 / RADIUS 台帳の利用者",
                     *console_login(testbed, node, RAD_USER, RAD_PW)))
        cfg = rt.show("show running-config | section line con")
    finally:
        rt.conf(["line con 0", " no login authentication NOEXIST", "exit"])
        rt.conf(["no aaa authentication login CONSOLE local"])
        svc("start")
        rt.close()
        for c in srv:
            c.close()

    md = ["# BL-101 P0 追試 — コンソール(line con 0)の認証挙動", "",
          "自動生成: poc/aaa/console_probe.py。対象= _POC-AAA の RT02。", "",
          "| ケース | 結果 | 詳細 |", "|---|---|---|"]
    for label, res, detail in rows:
        md.append(f"| {label} | **{res}** | {detail} |")
    md += ["", "最終の `line con` 構成(後始末後):", "```", cfg, "```"]
    OUT.write_text("\n".join(md))
    print("\n".join(f"{r[1]:12s} {r[0]}  ({r[2]})" for r in rows))
    print(f"\n書き出し: {OUT}")


if __name__ == "__main__":
    main()
