#!/usr/bin/env python3
"""問題パックの配信サーバ — BL-099。

`packs/` を静的配信しつつ、問題ページの解答欄から `解答.md` へ書き戻すための
小さな API を持つ。VSCode Remote-SSH のポート転送越しに、Windows 側のブラウザから
そのまま解答を書き込めるようにするのが目的。

  GET  /_api/sheet?pack=<PACK-ID>&no=<N>   … 該当セクションの本文を返す
  POST /_api/sheet?pack=<PACK-ID>&no=<N>   … 本文で該当セクションを差し替える
  GET  /                                   … パック一覧(採点状態つき。pack_home.py)。素の一覧は /?raw=1
  GET  /_lab?pack=<PACK-ID>&no=<N>         … ラボのワークスペース(lab_console.py・別ポート)へ転送(BL-234)。
                                              問題ページにポート番号を焼き込まないための中継ぎ。
                                              ★ラボへのリンクは全部ここを通る(BL-236= 最初からワークスペース)。
                                              ワークスペースが無効・未起動なら単体の q<N>.html へ落とす。
  POST /_api/check?pack=<PACK-ID>&no=<N>   … 本文を保存したうえで正誤を返す(BL-212 答え合わせ)。
                                              応答= "ok|ng<TAB>内訳<TAB>正解" | "empty" | "nokey<TAB>理由"。
                                              内訳は組合せ/穴埋めだけ("①○ ②× …"・他は空)。
                                              正解は key_of の正規形("BD" / "①D・②A…")。
                                              ★2026-09-28 から正解も返す(ユーザ要望= 選択肢ごとの正誤を色分け)。
                                              押した時点で入力はロック済みなので初回解答の確定は崩れない。
                                              解説本文は従来どおり採点後の解説ページ。

設計上の約束:
  - bind は既定 127.0.0.1(このスクリプト単体)。★pack.sh serve は 2026-09-21 から **0.0.0.0** で起動する
    (ユーザ指示= Windows から http://10.1.10.6:8899/ で直接開く)。LAN(10.1.10.0/26)は自宅ラボ網。
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
import socket
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pack                                        # noqa: E402
import pack_home                                       # noqa: E402

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
    repo = REPO
    console_port = 0                # ラボのワークスペース(lab_console.py)のポート。0 = 無効
    console_probe = "127.0.0.1"     # 起動確認の接続先(自分の bind。0.0.0.0 ならループバック)

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
        u = urlparse(self.path)
        # トップ = パック一覧(採点状態つき・2026-09-27)。素の一覧は /?raw=1
        if u.path in ("/", "/index.html") and "raw" not in parse_qs(u.query):
            body = pack_home.build_home(self.packs_root, self.repo).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if u.path == "/_api/sheet":
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
        if u.path == "/_lab":
            return self._lab(parse_qs(u.query))
        return SimpleHTTPRequestHandler.do_GET(self)

    def _lab(self, q):
        """ラボのワークスペースへ転送する。相手が無効・未起動なら単体の問題ページへ落とす
        (ラボへのリンクは全部ここを通るので、行き止まりにしない)。"""
        pack = (q.get("pack") or [""])[0]
        no = (q.get("no") or [""])[0]
        if not PACK_RE.match(pack) or not no.isdigit():
            return self._json(400, "pack / no が不正です")
        up = bool(self.console_port)
        if up:
            try:
                socket.create_connection((self.console_probe, self.console_port), timeout=1).close()
            except OSError:
                up = False
        if up:
            host = (self.headers.get("Host") or "localhost").rsplit(":", 1)[0]
            where = f"http://{host}:{self.console_port}/lab?" + urlencode({"pack": pack, "no": no})
        else:
            where = f"/{pack}/q{int(no)}.html"
        self.send_response(302)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/_api/check":
            return self._check()
        if p != "/_api/sheet":
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

    def _check(self):
        """答え合わせ(BL-212): 本文を保存し、manifest の ref から正解キーを引いて正誤と正解を返す。"""
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
        atomic_write(path, merged)                 # 答え合わせした解答をそのまま確定として残す
        pack = parse_qs(urlparse(self.path).query).get("pack", [""])[0]
        man = gen_pack.read_manifest(os.path.dirname(path))
        it = next((i for i in man["items"] if i["no"] == no), None)
        if not it or it.get("kind") != "paper":
            return self._json(200, "nokey\t紙面ではありません")
        key, why = gen_pack.key_of(self.repo, it.get("ref", ""), it.get("key"))
        m = re.search(r"^[ \t]*解答:[ \t]*(.*)$", body, re.M)
        ans = m.group(1).strip() if m else ""
        if key is None:
            return self._json(200, "nokey\t" + (why or ""))
        parts = ""
        if gen_pack.is_match_key(key):
            given = gen_pack.match_of(ans)
            if not given:
                return self._json(200, "empty")
            kp = {t[0]: t[1:] for t in key.split("・")}
            gp = {t[0]: t[1:] for t in given.split("・")}
            parts = " ".join(f"{t}{'○' if gp.get(t) == kp[t] else '×'}" for t in kp)
            ok = given == key
        else:
            given = gen_pack.choice_of(ans)
            if not given:
                return self._json(200, "empty")
            ok = given == key
        self.audit("check", pack, no, f"{given}={'ok' if ok else 'ng'}")
        return self._json(200, ("ok" if ok else "ng") + "\t" + parts + "\t" + key)

    def end_headers(self):
        # ★静的ページもキャッシュさせない(2026-09-21: 再描画後も古いページが表示され
        #   「答え合わせボタンが見当たらない」となった。SimpleHTTPRequestHandler は
        #   Last-Modified だけ返すのでブラウザが古い HTML を使い回す)
        self.send_header("Cache-Control", "no-store, max-age=0")
        SimpleHTTPRequestHandler.end_headers(self)

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
    ap.add_argument("--console-port", type=int, default=0,
                    help="ラボのワークスペース(lab_console.py)のポート。/_lab の転送先(0=無効)")
    a = ap.parse_args()
    root = os.path.join(os.path.abspath(a.repo), "packs")
    os.makedirs(root, exist_ok=True)
    Handler.packs_root = root
    Handler.repo = os.path.abspath(a.repo)
    Handler.console_port = a.console_port
    Handler.console_probe = "127.0.0.1" if a.bind in ("0.0.0.0", "") else a.bind

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
