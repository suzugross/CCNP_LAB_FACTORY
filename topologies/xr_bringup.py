#!/usr/bin/env python3
"""IOS XR ノードへコンソールから設定を入れる(BL-246)。主な用途は**コミット履歴の仕込み**。

初期設定(day0)は通常どおり CML が起動時に入れる(ノード定義 iosxrv9000 の設定ファイルが
`editable: true` であることが前提。false だとラボ YAML の configuration も API での差し替えも
無言で捨てられ、定義の既定設定= ユーザ cisco/admin/lab・全 IF shutdown で起動する・2026-10-12 実測)。
ただし day0 は 1 回のコミットとしてしか入らないので、「いつ・どの変更が入ったか」を履歴から
読ませる課題には、起動後に変更を複数回に分けてコミットする必要がある。それをここでやる。

  1. コンソールのログイン要求を待って入る(起動直後は出るまで時間がかかる)
  2. --day0 の時だけ: day0(<gen>/day0/<node>.cfg)を流して `commit replace`(定義が編集不可の環境の救済)
  3. <problem>/initial/<node>.commits.yml のコミット列を上から順に入れる
  4. SSH のホスト鍵が無ければ生成する(24.3.1 は起動時に自動生成されるので通常は何もしない)

usage: xr_bringup.py --repo R --problem P [--nodes XR01,XR02] [--wait 900] [--day0]
環境変数: NODE_USER / NODE_PASS(day0 が作るユーザ)。CML の接続は group_vars/all/local.yml
(CML_HOST / CML_USER / CML_PASS で上書き可)。対象は problem.yml の node_image_families が iosxr のノード。

<node>.commits.yml の形(上から順に 1 コミットずつ):
  - label: ospf-tuning          # 任意。履歴に残る名前
    comment: "change request 1"  # 任意
    lines: |
      router ospf 1
       area 0
        interface GigabitEthernet0/0/0/0
         cost 50

実測(2026-10-12・24.3.1): コンソールは 10KB の一括貼り付けを流量制御なしで取りこぼさない。
"""
import argparse
import hashlib
import os
import re
import sys
import time

import pexpect
import yaml

PROMPT = r"RP/\d+/RP\d+/CPU\d+:[\w.\-]+(?:\([\w\-/. ]+\))?#"
DEFAULT_LOGIN = ("cisco", "cisco")        # ノード定義の既定設定が作るユーザ


def lab_title(problem):
    return "CCNP-LAB-" + hashlib.md5(problem.encode()).hexdigest()[:8]


def load_cml(repo):
    c = yaml.safe_load(open(os.path.join(repo, "group_vars/all/local.yml"), encoding="utf-8")) or {}
    return (os.environ.get("CML_HOST") or c["cml_host"],
            os.environ.get("CML_USER") or c["cml_username"],
            os.environ.get("CML_PASS") or c["cml_password"])


def open_console(cml, title, node):
    host, user, pw = cml
    s = pexpect.spawn(
        "ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
        f"{user}@{host} open /{title}/{node}/0",
        timeout=30, encoding="utf-8", codec_errors="replace")
    s.expect("[Pp]assword:")
    s.sendline(pw)
    s.expect("Escape character")
    if os.environ.get("XR_BRINGUP_LOG"):            # 調査用: コンソールの受信を丸ごと残す
        s.logfile_read = open(os.environ["XR_BRINGUP_LOG"], "a", encoding="utf-8")
    return s


def login(s, creds, wait):
    """ログイン要求かプロンプトが出るまで待って入る。creds は (user, pass) の候補を順に試す。"""
    t0 = time.time()
    tried = 0
    while True:
        s.send("\r")
        i = s.expect([PROMPT, r"Username:", pexpect.TIMEOUT], timeout=8)
        if i == 0:
            return time.time() - t0
        if i == 1:
            if tried >= len(creds) * 2:
                raise RuntimeError("login failed with every known credential")
            user, pw = creds[tried % len(creds)]
            tried += 1
            s.send(user + "\r")
            s.expect("Password:", timeout=15)
            s.send(pw + "\r")
            if s.expect([PROMPT, r"Username:", pexpect.TIMEOUT], timeout=40) == 0:
                return time.time() - t0
            continue
        if time.time() - t0 > wait:
            raise RuntimeError(f"no login prompt after {wait}s: {s.before[-200:]!r}")


def run(s, cmd, timeout=120):
    s.sendline(cmd)
    s.expect(PROMPT, timeout=timeout)
    return s.before.replace("\r", "")


def config_lines(text):
    """設定テキスト → 流す行。コメント行(! 始まり)・空行・end は落とす。"""
    out = []
    for ln in text.splitlines():
        t = ln.strip()
        if not t or t.startswith("!") or t == "end":
            continue
        out.append(ln.rstrip())
    return out


def push(s, lines, commit, errors, what):
    """設定モードで lines を流し、commit の行で確定する。行ごとの構文エラーと確定の失敗を errors に積む。"""
    run(s, "configure terminal")
    for n, ln in enumerate(lines):
        # 字下げの無い行は最上位の設定。直前のサブモードに居たままだと、その中の項目として解釈される
        # (例: OSPF の area の中で `interface Loopback101` を打つと OSPF の IF になる・2026-10-15 実発)。
        if n and not ln[:1].isspace():
            run(s, "root")
        out = run(s, ln)
        if "% " in out:
            errors.append(f"{what}: {ln.strip()!r} -> {out.strip().splitlines()[-1]}")
    # 起動直後は初期設定の適用(ZTP)がまだ動いていて、確定が一時的に失敗することがある(2026-10-12 実発)。
    # 編集中の設定は失敗しても残るので、少し待って確定だけをやり直す。
    for attempt in range(4):
        s.sendline(commit)
        i = s.expect([r"\[no\]:", PROMPT], timeout=180)
        if i == 0:
            s.sendline("yes")
            s.expect(PROMPT, timeout=300)
        out = s.before
        if "Failed to commit" not in out and "% " not in out and "inconsistent" not in out:
            run(s, "end")
            return True
        last = out.replace("\r", "").strip()
        time.sleep(15)
    failed = run(s, "show configuration failed")
    errors.append(f"{what}: commit failed\n{last}\n{failed.strip()}")
    run(s, "abort")
    return False


def clear_inconsistency(s, node, wait=600):
    """設定モードに入れるまで待ち、XRd の設定不一致の警報があれば解除する。
    - 起動直後は初期設定の適用中で、configure terminal が「proceed in configuration mode? [no]:」と
      聞いてくる(XRd はログイン要求が数秒で出るので、ここで待つ必要がある・2026-10-18 実測 26.1.1)。
    - XRd は first-boot.cfg を入れた後「running と保存設定が不一致」の警報を上げ、解除するまで一切コミットを
      受け付けない(拒否されても設定モードのまま残る)。設定は保ったまま解除できる。"""
    t0 = time.time()
    while True:
        s.sendline("configure terminal")
        i = s.expect([r"\[no\]:", PROMPT], timeout=60)
        probe = s.before
        if i == 0:
            s.sendline("no")
            s.expect(PROMPT, timeout=60)
            if time.time() - t0 > wait:
                raise RuntimeError(f"system configuration still in progress after {wait}s")
            time.sleep(10)
            continue
        run(s, "abort")
        break
    if "inconsistent" in probe:
        run(s, "clear configuration inconsistency", timeout=300)
        print(f"[{node}] cleared configuration inconsistency")


def bring_up(a, cml, node):
    title = lab_title(a.problem)
    gen = os.path.join(a.repo, "topologies/_generated", a.problem)
    day0 = open(os.path.join(gen, "day0", f"{node}.cfg"), encoding="utf-8").read() if a.day0 else ""
    extra_path = os.path.join(a.repo, "problems", a.problem, "initial", f"{node}.commits.yml")
    extra = yaml.safe_load(open(extra_path, encoding="utf-8")) if os.path.exists(extra_path) else []
    me = (os.environ["NODE_USER"], os.environ["NODE_PASS"])
    errors = []

    s = open_console(cml, title, node)
    waited = login(s, [me, DEFAULT_LOGIN], a.wait)
    print(f"[{node}] console ready after {waited:.0f}s")
    run(s, "terminal length 0")
    clear_inconsistency(s, node)
    if extra and not a.day0:
        # 起動直後は初期設定の適用(ZTP)の最後のコミットがまだ残っていることがある。少し待って、履歴の順が混ざらないようにする
        time.sleep(a.settle)
    if a.day0:
        ok = push(s, config_lines(day0), "commit replace", errors, "day0")
        print(f"[{node}] day0 {'committed' if ok else 'FAILED'}")
    for n, c in enumerate(extra or [], 1):
        cmd = "commit"
        if c.get("label"):
            cmd += f" label {c['label']}"
        if c.get("comment"):
            cmd += f" comment {c['comment']}"
        ok2 = push(s, config_lines(c["lines"]), cmd, errors, f"commit#{n}")
        print(f"[{node}] commit#{n} {c.get('label', '')} {'ok' if ok2 else 'FAILED'}")
    s.close(force=True)

    # day0 がユーザを入れ替えたので入り直す(入れなければ day0 が効いていない)
    s = open_console(cml, title, node)
    login(s, [me], 60)
    run(s, "terminal length 0")
    keys = run(s, "show crypto key mypubkey rsa")
    if "Key label" not in keys:
        s.sendline("crypto key generate rsa")
        i = s.expect([r"\[2048\]:", r"\[yes/no\]:", PROMPT], timeout=60)
        if i == 1:                              # 既にある → 置き換えない
            s.sendline("no")
            s.expect(PROMPT, timeout=60)
        elif i == 0:
            s.sendline("2048")
            s.expect(PROMPT, timeout=180)
        print(f"[{node}] ssh host key generated")
    print(f"[{node}] commits:\n" + run(s, "show configuration commit list").strip())
    s.close(force=True)
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--nodes", help="対象ノード(既定= problem.yml の node_image_families が iosxr のもの)")
    ap.add_argument("--wait", type=int, default=900, help="コンソールのログイン要求を待つ上限(秒)")
    ap.add_argument("--settle", type=int, default=25, help="コミット列を入れ始める前の待ち(秒)")
    ap.add_argument("--day0", action="store_true",
                    help="day0 もコンソールから commit replace で入れる(ノード定義が編集不可の環境の救済)")
    a = ap.parse_args()
    pmeta = yaml.safe_load(open(os.path.join(a.repo, "problems", a.problem, "problem.yml"), encoding="utf-8"))
    fams = pmeta.get("node_image_families") or {}
    nodes = a.nodes.split(",") if a.nodes else [n for n in pmeta["target_nodes"] if fams.get(n) == "iosxr"]
    if not nodes:
        print("no IOS XR nodes")
        return 0
    cml = load_cml(a.repo)
    bad = []
    for node in nodes:
        try:
            bad += bring_up(a, cml, node)
        except Exception as e:                  # 1 台の失敗で残りを止めない
            bad.append(f"{node}: {e}")
    for b in bad:
        print("ERROR " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
