#!/usr/bin/env python3
"""PoC 用: CML のコンソール経由で IOS XR にコマンドを流して出力を表示する(BL-246)。

usage: xrcon.py <問題ID> <ノード> [--wait 秒] [--raw] 'cmd1' 'cmd2' ...
  --wait  プロンプト(またはログイン要求)が出るまで待つ上限(既定 30)。起動待ちの計測にも使う。
  設定モードに入る行(configure …)や commit もそのまま流せる。各行の後は次のプロンプトまで待つ。
接続情報は group_vars/all/local.yml、機器のログインは環境変数 NODE_USER / NODE_PASS。
"""
import hashlib, os, re, sys, time
import pexpect, yaml

PROMPT = r"RP/\d+/RP\d+/CPU\d+:[\w.\-]+(?:\([\w\-/. ]+\))?#"


def main():
    args = sys.argv[1:]
    wait, raw = 30, False
    if "--wait" in args:
        i = args.index("--wait"); wait = int(args[i + 1]); del args[i:i + 2]
    if "--raw" in args:
        args.remove("--raw"); raw = True
    prob, node, cmds = args[0], args[1], args[2:]
    c = yaml.safe_load(open("group_vars/all/local.yml"))
    title = "CCNP-LAB-" + hashlib.md5(prob.encode()).hexdigest()[:8]
    user, pw = os.environ.get("XR_USER") or os.environ["NODE_USER"], os.environ.get("XR_PASS") or os.environ["NODE_PASS"]
    s = pexpect.spawn(
        "ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
        f"{c['cml_username']}@{c['cml_host']} open /{title}/{node}/0",
        timeout=30, encoding="utf-8", codec_errors="replace")
    s.expect("[Pp]assword:"); s.sendline(c["cml_password"])
    s.expect("Escape character")
    t0 = time.time()
    while True:
        s.send("\r")
        i = s.expect([PROMPT, r"Username:", pexpect.TIMEOUT], timeout=5)
        if i == 0:
            break
        if i == 1:
            s.sendline(user); s.expect("Password:"); s.sendline(pw)
            s.expect(PROMPT, timeout=30); break
        if time.time() - t0 > wait:
            print(f"(no prompt after {wait}s) tail={s.before[-300:]!r}"); return 1
    print(f"# prompt after {time.time() - t0:.0f}s")
    s.sendline("terminal length 0"); s.expect(PROMPT)
    for cmd in cmds:
        if cmd.startswith("sleep "):              # 待ち(自動ロールバックの観察など)
            time.sleep(float(cmd.split()[1])); print(f"### {cmd}\n"); continue
        if cmd.endswith("?"):                     # ヘルプ: 改行せずに打ち、出たら行を消す
            s.send(cmd); s.expect(PROMPT, timeout=30)
            print(f"### {cmd}\n{re.sub(chr(13), '', s.before).strip()}\n")
            s.send("\x15"); time.sleep(0.5)
            s.sendline(""); s.expect(PROMPT, timeout=30); continue
        s.sendline(cmd)
        i = s.expect([PROMPT, r"\[(?:no|cancel)\]:\s*$"], timeout=180)
        if i == 1:                                # 確認を求められたら yes
            print(f"(confirm asked: {s.before.strip().splitlines()[-1]!r} -> yes)")
            s.sendline("yes"); s.expect(PROMPT, timeout=300)
        out = s.before if raw else re.sub(r"\r", "", s.before)
        print(f"### {cmd}\n{out.strip()}\n")
    s.close(force=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
