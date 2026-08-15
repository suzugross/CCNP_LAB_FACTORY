#!/usr/bin/env python3
"""問題パックの配信サーバ — BL-099。

`packs/` を静的配信しつつ、問題ページの解答欄から `解答.md` へ書き戻すための
小さな API を持つ。VSCode Remote-SSH のポート転送越しに、Windows 側のブラウザから
そのまま解答を書き込めるようにするのが目的。

  GET  /_api/sheet?pack=<PACK-ID>&no=<N>   … 該当セクションの本文を返す
  POST /_api/sheet?pack=<PACK-ID>&no=<N>   … 本文で該当セクションを差し替える

設計上の約束:
  - **127.0.0.1 のみに bind**(既定)。外に開かない。
  - 書き込み先は `packs/<PACK-ID>/解答.md` **だけ**。pack 名は書式を検査し、
    解決後のパスが packs/ 配下に収まることも確認する。
  - 書き込みは**該当セクションの差し替えのみ**。ファイル全体を送らせない
    (複数タブ・VSCode との同時編集で他の問の解答を消さないため)。
  - 保存は一時ファイル + rename の原子的置換。

使い方: scripts/pack.sh serve [PORT]
"""

import argparse
import datetime
import os
import re
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pack                                        # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK_RE = re.compile(r"^PACK-[A-Za-z0-9_.-]{1,64}$")
SHEET = "解答.md"


def sheet_path(packs_root, pack_id):
    """packs/<PACK-ID>/解答.md の実パス。範囲外・書式違反は None。"""
    if not PACK_RE.match(pack_id or ""):
        return None
    path = os.path.abspath(os.path.join(packs_root, pack_id, SHEET))
    root = os.path.abspath(packs_root)
    if os.path.commonpath([root, path]) != root:
        return None
    return path if os.path.exists(path) else None


def split_sections(text):
    """解答.md を [(no, 本文), ...] に分ける(本文は見出し行を含む)。"""
    out, cur, head = [], [], None
    for line in text.split("\n"):
        m = gen_pack.HDR.match(line)
        if m:
            if head is not None:
                out.append((head, "\n".join(cur)))
            head, cur = int(m.group(1)), [line]
        elif head is None:
            out.append((0, line))          # 前書き(見出しの前)は no=0 として保持
        else:
            cur.append(line)
    if head is not None:
        out.append((head, "\n".join(cur)))
    return out


def get_section(text, no):
    for n, body in split_sections(text):
        if n == no:
            return body
    return None


def replace_section(text, no, new_body):
    """no 番のセクションだけを差し替える。他の問には触らない。"""
    parts, out, hit = split_sections(text), [], False
    for n, body in parts:
        if n == no:
            out.append(new_body.rstrip("\n"))
            hit = True
        elif n == 0:
            out.append(body)
        else:
            out.append(body.rstrip("\n"))
    if not hit:
        return None
    # 前書き(no=0)は行単位なので join の仕方を合わせる
    lead = [b for n, b in parts if n == 0]
    secs = [o for (n, _b), o in zip(parts, out) if n != 0]
    return "\n".join(lead).rstrip("\n") + "\n\n" + "\n\n".join(secs) + "\n"


def atomic_write(path, text):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".sheet-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class Handler(SimpleHTTPRequestHandler):
    packs_root = os.path.join(REPO, "packs")

    def _json(self, code, msg):
        body = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _target(self):
        q = parse_qs(urlparse(self.path).query)
        pack = (q.get("pack") or [""])[0]
        try:
            no = int((q.get("no") or ["0"])[0])
        except ValueError:
            return None, None
        return sheet_path(self.packs_root, pack), no

    def do_GET(self):
        if urlparse(self.path).path == "/_api/sheet":
            path, no = self._target()
            if not path:
                return self._json(404, "pack が見つかりません")
            with open(path, encoding="utf-8") as fh:
                sec = get_section(fh.read(), no)
            if sec is None:
                return self._json(404, f"Q{no} のセクションがありません")
            self.audit("load", parse_qs(urlparse(self.path).query).get(
                "pack", [""])[0], no)
            return self._json(200, sec)
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if urlparse(self.path).path != "/_api/sheet":
            return self._json(404, "not found")
        path, no = self._target()
        if not path:
            return self._json(404, "pack が見つかりません")
        n = int(self.headers.get("Content-Length") or 0)
        if n > 64 * 1024:
            return self._json(413, "本文が大きすぎます")
        body = self.rfile.read(n).decode("utf-8", "replace")
        if not gen_pack.HDR.match(body.split("\n")[0]):
            return self._json(400, "セクション見出しが不正です")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        merged = replace_section(text, no, body)
        if merged is None:
            return self._json(404, f"Q{no} のセクションがありません")
        atomic_write(path, merged)
        m = re.search(r"^[ \t]*(解答|メモ):[ \t]*(.*)$", body, re.M)
        self.audit("save", parse_qs(urlparse(self.path).query).get("pack", [""])[0],
                   no, f"{m.group(1)}={m.group(2).strip()[:60]}" if m else "")
        return self._json(200, "ok")

    def log_message(self, fmt, *args):        # 標準のアクセスログは出さない(静かに動かす)
        pass

    def audit(self, action, pack, no, detail=""):
        """解答の読み書きを監査ログに残す。

        ★「保存が効いていたのか、解答し直したから残っていたのか」を後から
          判別できるようにするため(2026-08-12 ユーザ指摘。当時は記録が無く
          判定不能だった)。**ユーザフォルダには置かず**リポの _state/ に書く。
        """
        try:
            d = os.path.join(REPO, "topologies", "_state")
            os.makedirs(d, exist_ok=True)
            stamp = datetime.datetime.now().isoformat(timespec="seconds")
            line = f"{stamp}\t{action}\t{pack}\tQ{no}\t{detail}".rstrip()
            with open(os.path.join(d, "pack-answers.log"), "a",
                      encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass                            # 監査ログの失敗で解答保存を壊さない


def main():
    ap = argparse.ArgumentParser(description="問題パックの配信＋解答書き戻しサーバ")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--bind", default="127.0.0.1")
    a = ap.parse_args()
    root = os.path.join(os.path.abspath(a.repo), "packs")
    os.makedirs(root, exist_ok=True)
    Handler.packs_root = root

    def factory(*args, **kw):
        return Handler(*args, directory=root, **kw)

    srv = ThreadingHTTPServer((a.bind, a.port), factory)
    print(f"packs/ を http://{a.bind}:{a.port}/ で配信中（Ctrl-C で停止）")
    print("解答は各問のページ下部の解答欄に書くと 解答.md に保存されます")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました")


if __name__ == "__main__":
    main()
