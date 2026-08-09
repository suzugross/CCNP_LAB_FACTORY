#!/usr/bin/env python3
"""BL-103 ② 追加実測(X11): **コンソールでの権限レベルを、昇格なしで測る**。

背景: 既存のコンソール測定([console_probe.py](console_probe.py))は pyATS を使っており、
接続時に **unicon が自動で enable へ昇格する**。そのため `show privilege` は常に 15 を返し、
**ログイン直後の権限レベルは測れていなかった**(C1〜C5 の priv 値は信用できない)。

X5/X6 で「コンソールの認可は `aaa authorization console` が無ければ実行されない」ことは
確定したが、**そのとき権限レベルが何になるか**は未測定のまま残っていた。
authz が実行されないなら AVPair の `shell:priv-lvl` は適用されないはずで、
RADIUS 利用者は priv 1 に落ちるのではないか — これを確かめる。

方法: CML の端末サーバへ SSH し `open /<lab>/<node>/0` でコンソールに入り、
**素のソケットでログインを打つ**(自動昇格が入らない)。

使い方: CML_USER=... CML_PASS=... console_raw.py
"""
import os
import re
import sys
import time
from pathlib import Path

import paramiko
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ext_probe import (ADMIN, ADMIN_PW, GRP, LOCAL_ONLY, LOCAL_ONLY_PW,  # noqa: E402
                       RAD_USER, RAD_PW, Router, hosts)

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-AAA"
OUT = Path(__file__).resolve().parent / "results-ext.md"

CML = os.environ.get("CML_HOST", "10.1.10.10")
CML_USER = os.environ.get("CML_USER", "admin")
CML_PASS = os.environ.get("CML_PASS", "CCNP")
NODE_PATH = None            # 実行時に lab.yaml から決める


def lab_title():
    y = yaml.safe_load((GEN / "lab.yaml").read_text())
    return (y.get("lab") or {}).get("title") or ""


class Console:
    """CML 端末サーバ経由の**素の**コンソール。自動昇格は一切しない。"""

    def __init__(self, path):
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(CML, username=CML_USER, password=CML_PASS,
                         look_for_keys=False, allow_agent=False, timeout=40)
        self.sh = self.cli.invoke_shell(width=200)
        time.sleep(2.0)
        self._read()
        self.sh.send(f"open {path}\n")
        time.sleep(3.0)
        self.buf = self._read()

    def _read(self, sec=1.0):
        t0, out = time.time(), ""
        while time.time() - t0 < sec:
            if self.sh.recv_ready():
                out += self.sh.recv(65535).decode("utf-8", "replace")
                t0 = time.time()          # 届いている間は待つ
            else:
                time.sleep(0.1)
        return out

    def send(self, s, wait=2.0):
        self.sh.send(s + "\r")
        return self._read(wait)

    def logout(self):
        """既にログイン済みなら抜けて、ログインプロンプトへ戻す。"""
        buf = self.send("", 2.0)
        for _ in range(4):
            if re.search(r"[\w.\-]+(\([\w\-]+\))?[#>]\s*$", buf.strip()):
                buf = self.send("exit", 3.0)
            else:
                break
        return buf

    def login(self, user, pw, wait=25.0):
        """ログインを打ち、**昇格せずに** `show privilege` を読む。"""
        self.logout()
        buf = self.send("", 2.0)
        t0 = time.time()
        while "sername" not in buf and time.time() - t0 < 20:
            buf += self.send("", 2.0)
        if "sername" not in buf:
            return "NO_PROMPT", buf[-200:]
        buf = self.send(user, 3.0)
        t0 = time.time()
        while "assword" not in buf and time.time() - t0 < 15:
            buf += self._read(2.0)
        if "assword" not in buf:
            return "NO_PWPROMPT", buf[-200:]
        self.sh.send(pw + "\r")
        buf = self._read(wait)            # ★全断だと 12s 以上待つ
        if "Authorization failed" in buf or "not authorized" in buf.lower():
            return "EXEC_DENIED", ""
        if re.search(r"(% Authentication failed|% Login invalid|% Access denied)", buf):
            return "AUTH_FAIL", ""
        if not re.search(r"[\w.\-]+[#>]", buf):
            return "NO_EXEC", buf[-200:]
        prompt_hash = bool(re.search(r"[\w.\-]+#", buf))
        out = self.send("show privilege", 4.0)
        m = re.search(r"privilege level is (\d+)", out)
        priv = m.group(1) if m else ("15" if prompt_hash else "?")
        self.send("exit", 2.0)
        return "OK", f"priv={priv} (プロンプト={'#' if prompt_hash else '>'})"

    def close(self):
        try:
            self.logout()
        except Exception:
            pass
        try:
            self.cli.close()
        except Exception:
            pass


def main():
    title = lab_title()
    path = f"/{title}/RT02/0"
    h = hosts()
    rt = Router(h["RT02"])
    rows = []

    def probe(tag, user, pw):
        con = Console(path)
        try:
            res, det = con.login(user, pw)
        except Exception as ex:
            res, det = "ERROR", f"{type(ex).__name__}: {ex}"
        finally:
            con.close()
        rows.append((tag, f"{res} {det}"))
        print(f"    {tag}: {res} {det}", flush=True)

    x12 = "--x12" in sys.argv
    try:
        if not x12:
            # 既定(= `aaa authorization console` 無し)。認可は console では実行されない。
            rt.conf(["no aaa authorization console"])
            print("--- X11a/b: `aaa authorization console` 無し", flush=True)
            probe("X11a ★RADIUS 台帳の利用者(AVPair priv-lvl=15)", RAD_USER, RAD_PW)
            probe("X11b local の利用者(username privilege 15)", LOCAL_ONLY, LOCAL_ONLY_PW)

            rt.conf(["aaa authorization console"])
            print("--- X11c/d: `aaa authorization console` 有り", flush=True)
            probe("X11c ★RADIUS 台帳の利用者(AVPair priv-lvl=15)", RAD_USER, RAD_PW)
            probe("X11d local の利用者(username privilege 15)", LOCAL_ONLY, LOCAL_ONLY_PW)
        else:
            # ★生成器が実際に描いている健全構成(コンソール専用リスト)で測る。
            #   local 認証で入った利用者の権限レベルが、認可が実行されない場合に
            #   `username ... privilege 15` から来るのか priv 1 になるのかを確かめる。
            rt.conf(["aaa authentication login CONSOLE local",
                     "aaa authorization exec CONSOLE local",
                     "line con 0", " login authentication CONSOLE",
                     " authorization exec CONSOLE", "exit",
                     "no aaa authorization console"])
            print("--- X12a: 専用リスト＋`aaa authorization console` 無し", flush=True)
            probe("X12a ★local の利用者(username privilege 15)・認可は不実行",
                  LOCAL_ONLY, LOCAL_ONLY_PW)
            rt.conf(["aaa authorization console"])
            print("--- X12b: 専用リスト＋`aaa authorization console` 有り", flush=True)
            probe("X12b local の利用者(username privilege 15)・認可が実行される",
                  LOCAL_ONLY, LOCAL_ONLY_PW)
    finally:
        try:
            rt.conf(["no aaa authorization console"])
            if x12:
                rt.conf(["line con 0", " no authorization exec CONSOLE",
                         " no login authentication CONSOLE", "exit",
                         "no aaa authorization exec CONSOLE",
                         "no aaa authentication login CONSOLE"])
        except Exception:
            pass
        rt.close()

    head = ("## X12 — ★コンソール専用リストでの権限レベル(認可の実行有無)"
            if x12 else "## X11 — ★コンソールの権限レベル(自動昇格なしで実測)")
    md = ["", head,
          "",
          "pyATS を使わず CML 端末サーバ経由の素のコンソールで測る"
          "(unicon の自動 enable 昇格を排除)。対象= RT02。", "",
          "| 対象 | 結果 |", "|---|---|"]
    for tag, res in rows:
        md.append(f"| {tag} | {res} |")
    md.append("")
    OUT.write_text(OUT.read_text() + "\n".join(md) + "\n")
    print(f"\n追記: {OUT}")


if __name__ == "__main__":
    main()
