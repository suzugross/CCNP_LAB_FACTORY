#!/usr/bin/env python3
"""Junos の PoC の打鍵台本を、containerlab のノードの対話セッションで流して記録する(BL-275・Junos トラックの実測用)。

  .venv/bin/python poc/junos/jpoc.py <問題 ID> <台本> <記録>

台本は 1 行 1 動作:
  NODE[:名前] コマンド     そのノードのセッション(名前ごとに別の SSH セッション。省略時は NODE)へ 1 行打ち、プロンプトを待つ
  !sleep 秒                待つ
  # …                      注釈(記録にもそのまま残す)
セッションは最初に使った時に開く(ログインの表示も記録に入る)。プロンプトの待ちは Junos の「> 」「# 」・FRR の「# 」。
接続は lab_console.py のワークスペースと同じ(szk-cl01 を踏み台に SSH・FRR は docker exec の vtysh)。
"""
import asyncio
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "topologies"))
import lab_console as lc  # noqa: E402

# 「Exit with uncommitted changes? [yes,no] (yes) 」のような問いもプロンプトとして待つ(台本で yes / no を打つ)
PROMPT = re.compile(rb"(?:[>#%] |\]\s*\r?\n[^\r\n]*[#>] |\[yes,no\] \(\w+\) )$")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class Sess:
    def __init__(self, conns, proc):
        self.conns, self.proc, self.buf = conns, proc, b""

    async def read_until_prompt(self, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                chunk = await asyncio.wait_for(self.proc.stdout.read(65536), timeout=0.5)
            except asyncio.TimeoutError:
                chunk = b""
            if chunk:
                self.buf += chunk
            # 出力が止まってプロンプトで終わっていれば戻る(---(more)--- は出ない= SSH の端末は 200 行)
            if not chunk and PROMPT.search(self.buf[-200:].rstrip(b"\x00")):
                break
        out, self.buf = self.buf, b""
        return out


async def main(pid, script, logpath):
    cb = lc.Clab(lc.REPO)
    pm, spec, live = await cb.fetch(pid)
    _model, info = lc.clab_model(pm, spec, live)
    sessions = {}
    log = open(logpath, "w", encoding="utf-8")

    def w(s):
        log.write(s)
        log.flush()

    w(f"# jpoc {pid} {os.path.basename(script)} {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    for raw in open(script, encoding="utf-8"):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("#"):
            w(line + "\n")
            continue
        if line.startswith("!sleep"):
            sec = float(line.split()[1])
            w(f"\n## (sleep {sec:g}s)\n")
            await asyncio.sleep(sec)
            continue
        key, _, cmd = line.partition(" ")
        node = key.split(":")[0]
        if key not in sessions:
            conns, proc = await cb.open(info[node], 200, 200)
            sessions[key] = Sess(conns, proc)
            banner = await sessions[key].read_until_prompt(25)
            w(f"\n## [{key}] (open)\n" + ANSI.sub("", banner.decode("utf-8", "replace")))
        s = sessions[key]
        s.proc.stdin.write((cmd + "\r").encode())
        out = await s.read_until_prompt(120)
        w(f"\n## [{key}] {cmd}\n" + ANSI.sub("", out.decode("utf-8", "replace")).replace("\r", ""))
    for s in sessions.values():
        for c in s.conns:
            c.close()
    log.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    asyncio.run(main(*sys.argv[1:]))
