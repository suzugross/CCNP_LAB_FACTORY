#!/usr/bin/env python3
"""読み物ビルダー — 訳文 Markdown を「読むための HTML」に組む（BL-230）。

問題ではない。技術書・ドキュメントを段階的に訳しながら読み進めるための機能。
問題用紙(render_html.py)と違い、次の点が逆になる:

  - 装飾してよい（問題用紙は「どこが要点か」の道標を消すため無装飾）
  - 図は Mermaid で描き直す / コンソール出力は端末風に見せる
  - 原典の誤りは**直さずそのまま訳し**、その場に訳注を付ける

ソース(Markdown)側の追加記法:

  {{sic:原文どおりの語|訳注}}   … 誤植・誤りをそのまま残し、上付き番号＋節末の訳注に落とす
  :::note ... :::               … 訳注ブロック（青）
  :::sic  ... :::               … 誤り・不整合の指摘ブロック（黄）
  :::orig ... :::               … 原文併記（既定は折りたたみ）
  :::topo ... :::               … ネットワーク図（座標指定の SVG・下記）
  ```console ... ```            … 端末風（プロンプト行を強調）
  ![説明](img/ファイル名)        … 図版（画面キャプチャ等の画像・下記）
  ```mermaid ... ```            … 図（render_html の機構をそのまま使う）

:::topo — ネットワーク図を **座標で** 置く（YAML）:

    :::topo
    nodes:
      SW1: [2, 0]                  # [列, 行]。小数可
      PC1: {at: [0, 2], kind: host, label: "PC-1"}
    links:
      - [SW1, SW2, "E3/0-1"]       # [端A, 端B, ラベル]
      - {a: SW2, b: SW5, label: "E6/0-1", t: 0.3}   # t= ラベルの位置(0=A 側, 1=B 側)
      - {a: SW1, b: SW2, la: "E2/1-2", lb: "E1/1-2"}   # 両端でポート番号が違う時は端ごとに
        # (ta/tb で位置を調整。既定 0.24 / 0.76)
    frames:
      - {label: "VTP ドメイン TST", nodes: [SW1, SW2, SW3]}
    :::

★Mermaid(dagre)の自動配置は、環状・メッシュのトポロジだと線が交差して読めなくなる
  （実例: 正方形＋対角線の 4 台メッシュが縦一列に潰れた・2026-09-29 ユーザ指摘）。
  **盤面の図は :::topo を使う**。Mermaid は系列図・状態遷移など「自動配置で困らない図」に限る。

図版（画像） — 描き直せない図（GUI の画面キャプチャ等）を **原書の位置にそのまま** 載せる:

  <src>/img/ に画像を置き、本文から `![説明](img/ファイル名)` で参照する。
  build は img/ を出力先へ写す。bundle は data URI で HTML に埋め込む（外部参照ゼロを保つ）。
  ★盤面（トポロジ）の図は引き続き :::topo で描く。画像で載せるのは描き直しが利かない図だけ。

ソースの置き場と出力:

  <src>/book.yml     … {key, title, subtitle, pages:[{file,title}...]} （無ければ NN-*.md を名前順）
                       `lang: en` で画面の決まり文句(目次・訳注など)と <html lang> を英語にする(既定 ja)
                       `shelf:` ポータルでの棚の名前／`order:` 棚の中の並び(小さい順・既定 50)／`labs: [問題 ID]` 学習モードで開くラボ
                       `alt_lang:` もう一方の言語。lang と合わせて en/ja の 2 言語の本になる(BL-248):
                         ページは <src>/<lang>/<file> と <src>/<alt_lang>/<file>。2 版を 1 ページに持ち、ボタンで切り替わる。
                         title・subtitle・chapters の値は {en: …, ja: …} で書ける。bundle は言語ごとに別の 1 枚を作る
  → 出力先に book.json(ポータルが読む一覧用のメタ)も書く
  <src>/NN-*.md      … 1 ファイル = 1 ページ
  <src>/img/         … 図版（任意）
  → <repo>/reading/<key>/NN-*.html ＋ index.html

使い方:
  python3 topologies/gen_reading.py build --src private/reading/<key>
  読むのはポータル(scripts/pack.sh serve → :8899 の Study Materials。book.yml の shelf: の棚に載る)
"""
import argparse
import base64
import html
import mimetypes
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_html as RH  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(REPO, "reading")

# --------------------------------------------------------------------------
# 読み物のテーマ（問題用紙の CSS に足す差分だけを書く）
# --------------------------------------------------------------------------
READING_CSS = """
/* ---- 読み物テーマ: 本文は読みやすさ優先。問題用紙の無装飾ルールは適用しない ---- */
/*  日本語の技術文なので「1行の長さを詰める・行間と段落間を広く取る」方向に振る。 */
body.reading{ font-size:16.5px; line-height:2.05; letter-spacing:.012em; }
body.reading main{ max-width:44rem; margin:0 auto; padding:1.6rem 1.2rem 7rem; }
body.reading h1{ font-size:1.6rem; line-height:1.6; margin:1.4rem 0 1.6rem;
  padding-bottom:.55rem; border-bottom:2px solid #111; }
body.reading h1 + *{ margin-top:0; }
body.reading main > h1 ~ h1{ margin-top:4.5rem; }   /* 章中の大見出しは大きく空ける */
body.reading h2{ font-size:1.22rem; line-height:1.7; margin:3.4rem 0 1.1rem;
  padding:.1rem 0 .1rem .62rem; border-left:5px solid #111; }
body.reading h3{ font-size:1.06rem; margin:2.6rem 0 .9rem; color:#111;
  border-bottom:1px dotted #bbb; padding-bottom:.3rem; }
body.reading h4{ font-size:1rem; margin:2rem 0 .6rem; color:#333; }
body.reading p{ margin:1.25rem 0; }
body.reading ul,body.reading ol{ margin:1.35rem 0; padding-left:1.6rem; }
body.reading li{ margin:.6rem 0; }
body.reading li > p{ margin:.5rem 0; }
body.reading hr{ border:0; border-top:1px solid #d5d5d5; margin:3.6rem 0; }
body.reading table{ border-collapse:collapse; margin:1.9rem 0; font-size:.94rem;
  line-height:1.8; }
body.reading th,body.reading td{ border:1px solid #999; padding:.45rem .8rem; }
body.reading th{ background:#f2f2f2; }
body.reading .lead{ color:#444; }
body.reading code{ padding:0 .22em; }

/* ---- 端末風のコンソール出力 ---- */
.term{ margin:1.9rem 0; border-radius:7px; overflow:hidden;
  box-shadow:0 1px 4px rgba(0,0,0,.28); }
.termbar{ background:#2b2f36; padding:.42rem .7rem; display:flex; gap:.4rem;
  align-items:center; }
.termbar i{ width:11px; height:11px; border-radius:50%; display:inline-block; }
.termbar i:nth-child(1){ background:#ff5f56; }
.termbar i:nth-child(2){ background:#ffbd2e; }
.termbar i:nth-child(3){ background:#27c93f; }
.termbar b{ color:#9aa4b2; font-weight:400; font-size:.76rem; margin-left:.5rem;
  letter-spacing:.03em; }
.term pre{ margin:0; background:#12151b; color:#d6dde6; padding:1rem 1.15rem;
  border:0; border-radius:0; overflow-x:auto; }
.term code{ font-family:"Cascadia Mono",Consolas,"DejaVu Sans Mono",monospace;
  font-size:.845rem; line-height:1.62; }
.term .prompt{ color:#7fd28c; font-weight:600; }
.term .cmt{ color:#8b98a6; font-style:italic; }

/* ---- 誤植・訳注 ---- */
.sic{ background:#fff3bf; border-bottom:1px dashed #b8860b; padding:0 .1em; }
.sic sup{ color:#a05a00; font-weight:700; font-size:.72em; margin-left:.12em; }
.callout{ margin:2rem 0; padding:.95rem 1.15rem; border-radius:5px;
  font-size:.93rem; line-height:1.8; }
.callout p:first-child{ margin-top:0; } .callout p:last-child{ margin-bottom:0; }
.callout .tag{ display:inline-block; font-size:.74rem; font-weight:700;
  letter-spacing:.05em; padding:.05rem .45rem; border-radius:3px;
  margin-right:.45rem; vertical-align:.08em; }
.c-note{ background:#eef4fb; border-left:4px solid #3f7fbf; }
.c-note .tag{ background:#3f7fbf; color:#fff; }
.c-sic{ background:#fdf6e3; border-left:4px solid #c08a2e; }
.c-sic .tag{ background:#c08a2e; color:#fff; }
.c-orig{ background:#f7f7f7; border-left:4px solid #aaa; }
.c-orig summary{ cursor:pointer; color:#555; font-size:.86rem; }
.c-orig pre,.c-orig p{ font-size:.86rem; color:#444; }

/* ---- ネットワーク図(:::topo) ---- */
.topo{ margin:2.4rem 0; text-align:center; overflow-x:auto; }
.topo svg{ max-width:100%; height:auto; }
.topo .tl{ stroke:#44506080; stroke-width:1.7; }
.topo .tl.dash{ stroke-dasharray:6 4; }
.topo .tn{ font-family:"Segoe UI",system-ui,sans-serif; font-size:14px;
  font-weight:600; fill:#1b2430; text-anchor:middle; }
.topo .tlt{ font-family:"Cascadia Mono",Consolas,monospace; font-size:11.5px;
  fill:#3a4756; text-anchor:middle; }
.topo .tlb{ fill:#ffffff; stroke:#dfe3e8; stroke-width:1; }
.topo .tf{ fill:#f8f5ee; stroke:#c3b48c; stroke-width:1.4; stroke-dasharray:7 5; }
.topo .tfl{ font-family:"Segoe UI",system-ui,sans-serif; font-size:12px;
  fill:#8a7a52; font-weight:600; }

/* ---- 図版(画面キャプチャ等) ---- */
body.reading main img{ display:block; max-width:100%; height:auto; margin:1.9rem auto;
  border:1px solid #d9dde3; border-radius:3px; }

/* ---- 節末の訳注一覧 ---- */
.notes{ margin-top:4.5rem; border-top:2px solid #111; padding-top:.7rem;
  font-size:.9rem; }
.notes h2{ font-size:1.02rem; border:0; padding:0; margin:.2rem 0 .6rem; }
.notes ol{ padding-left:1.4rem; } .notes li{ margin:.45rem 0; line-height:1.75; }
.notes .q{ background:#fff3bf; padding:0 .15em; }

/* ---- 表は横に溢れたらその枠だけスクロール（スマホ対策） ---- */
body.reading .tw{ overflow-x:auto; -webkit-overflow-scrolling:touch; margin:1.9rem 0; }
body.reading .tw table{ margin:0; }

/* ---- 画面が狭いとき ---- */
@media (max-width:640px){
  body.reading{ font-size:16px; line-height:1.95; }
  body.reading main{ padding:1rem .9rem 5rem; }
  body.reading h1{ font-size:1.35rem; }
  body.reading h2{ font-size:1.12rem; margin:2.7rem 0 .9rem; }
  body.reading h3{ margin:2.1rem 0 .7rem; }
  .term code{ font-size:.76rem; }
  .term pre{ padding:.8rem .85rem; }
  .callout{ margin:1.6rem 0; padding:.8rem .9rem; }
  .topo{ margin:1.7rem 0; }
  .nav{ font-size:.8rem; }
}

/* ---- ページ送り ---- */
.pager{ margin-top:4rem; padding-top:.9rem; border-top:1px solid #ccc;
  display:flex; justify-content:space-between; gap:1rem; font-size:.92rem; }
.pager a{ text-decoration:none; }
.toc li{ margin:.3rem 0; }
"""

# 端末に見せるフェンスの言語名
TERM_LANGS = ("console", "term", "shell")
# プロンプト行（エスケープ済み HTML に対して当てる。> は &gt;）
PROMPT_RE = re.compile(
    r"^([A-Za-z][\w.\-]*(?:\([\w\-]+\))?\s*[#]|[A-Za-z][\w.\-]*\s*&gt;)(.*)$", re.M)
# 行末コメント（! 以降）を落ち着いた色に
CMT_RE = re.compile(r"(\s)(![^\n<]*)$", re.M)


# --------------------------------------------------------------------------
# ネットワーク図（:::topo → SVG）
#   自動配置に任せず座標で置く。線は箱の縁で切り、ラベルは線上に白抜きで載せる。
# --------------------------------------------------------------------------
CELL_X, CELL_Y, MARGIN = 158, 108, 54
NODE_STYLE = {                     # kind: (最小幅, 高さ, 塗り, 枠, 角丸)
    "sw":    (86, 40, "#eef1f5", "#2f3b4a", 5),
    "host":  (82, 34, "#ffffff", "#5a6472", 16),
    "cloud": (98, 40, "#f3efe6", "#8a7a52", 18),
}


def _box(name, spec):
    at = spec["at"] if isinstance(spec, dict) else spec
    kind = spec.get("kind", "sw") if isinstance(spec, dict) else "sw"
    label = spec.get("label", name) if isinstance(spec, dict) else name
    w0, h, fill, stroke, r = NODE_STYLE.get(kind, NODE_STYLE["sw"])
    w = max(w0, int(len(label) * 8.6) + 22)
    return {"x": MARGIN + at[0] * CELL_X, "y": MARGIN + at[1] * CELL_Y,
            "w": w, "h": h, "fill": fill, "stroke": stroke, "r": r, "label": label}


def _clip(b, x2, y2):
    """箱 b の中心から (x2,y2) へ向かう線が、b の縁を出る点を返す。"""
    dx, dy = x2 - b["x"], y2 - b["y"]
    if dx == 0 and dy == 0:
        return b["x"], b["y"]
    hw, hh = b["w"] / 2 + 3, b["h"] / 2 + 3
    sx = hw / abs(dx) if dx else float("inf")
    sy = hh / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return b["x"] + dx * s, b["y"] + dy * s


def render_topo(src_yaml):
    import yaml
    spec = yaml.safe_load(src_yaml) or {}
    boxes = {n: _box(n, s) for n, s in (spec.get("nodes") or {}).items()}
    if not boxes:
        return "<p>(図の定義が空です)</p>"
    parts = []

    # 枠（VTP ドメイン等）は最背面に
    for fr in spec.get("frames") or []:
        ns = [boxes[n] for n in fr.get("nodes", []) if n in boxes]
        if not ns:
            continue
        pad = 24
        x1 = min(b["x"] - b["w"] / 2 for b in ns) - pad
        x2 = max(b["x"] + b["w"] / 2 for b in ns) + pad
        y1 = min(b["y"] - b["h"] / 2 for b in ns) - pad - 12
        y2 = max(b["y"] + b["h"] / 2 for b in ns) + pad
        parts.append(f'<rect class="tf" x="{x1:.0f}" y="{y1:.0f}" '
                     f'width="{x2-x1:.0f}" height="{y2-y1:.0f}" rx="12"/>')
        if fr.get("label"):
            parts.append(f'<text class="tfl" x="{x1+12:.0f}" y="{y1+16:.0f}">'
                         f'{html.escape(str(fr["label"]))}</text>')

    labels = []
    for ln in spec.get("links") or []:
        ends = []                      # 端ごとのラベル(la= A 側 / lb= B 側)
        if isinstance(ln, dict):
            a, b, lab, t = ln["a"], ln["b"], ln.get("label", ""), float(ln.get("t", 0.5))
            dash = ln.get("style") == "dashed"
            if ln.get("la"):
                ends.append((float(ln.get("ta", 0.24)), str(ln["la"])))
            if ln.get("lb"):
                ends.append((float(ln.get("tb", 0.76)), str(ln["lb"])))
        else:
            a, b = ln[0], ln[1]
            lab = ln[2] if len(ln) > 2 else ""
            t, dash = 0.5, False
        if a not in boxes or b not in boxes:
            continue
        ba, bb = boxes[a], boxes[b]
        x1, y1 = _clip(ba, bb["x"], bb["y"])
        x2, y2 = _clip(bb, ba["x"], ba["y"])
        cls = "tl dash" if dash else "tl"
        parts.append(f'<line class="{cls}" x1="{x1:.0f}" y1="{y1:.0f}" '
                     f'x2="{x2:.0f}" y2="{y2:.0f}"/>')
        if lab:
            labels.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, lab))
        for te, le in ends:
            labels.append((x1 + (x2 - x1) * te, y1 + (y2 - y1) * te, le))

    for x, y, lab in labels:       # ラベルは線より前面
        w = len(lab) * 7.4 + 10
        parts.append(f'<rect class="tlb" x="{x-w/2:.0f}" y="{y-9:.0f}" '
                     f'width="{w:.0f}" height="18" rx="3"/>')
        parts.append(f'<text class="tlt" x="{x:.0f}" y="{y+4:.0f}">'
                     f"{html.escape(str(lab))}</text>")

    for b in boxes.values():       # ノードは最前面
        parts.append(
            f'<rect x="{b["x"]-b["w"]/2:.0f}" y="{b["y"]-b["h"]/2:.0f}" '
            f'width="{b["w"]}" height="{b["h"]}" rx="{b["r"]}" '
            f'fill="{b["fill"]}" stroke="{b["stroke"]}" stroke-width="1.6"/>')
        parts.append(f'<text class="tn" x="{b["x"]:.0f}" y="{b["y"]+5:.0f}">'
                     f'{html.escape(b["label"])}</text>')

    W = max(b["x"] + b["w"] / 2 for b in boxes.values()) + MARGIN
    H = max(b["y"] + b["h"] / 2 for b in boxes.values()) + MARGIN
    body = "\n".join(parts)
    return (f'<div class="topo"><svg viewBox="0 0 {W:.0f} {H:.0f}" '
            f'width="{W:.0f}" role="img">\n{body}\n</svg></div>')


TOPO_RE = re.compile(r"^:::topo[ \t]*\n(.*?)^:::[ \t]*$", re.S | re.M)


def expand_topo(md_text):
    return TOPO_RE.sub(lambda m: "\n" + render_topo(m.group(1)) + "\n", md_text)


# --------------------------------------------------------------------------
# ソース Markdown の前処理
# --------------------------------------------------------------------------
SIC_RE = re.compile(r"\{\{sic:(.+?)\|(.+?)\}\}", re.S)
FENCE_RE = re.compile(r"^```")

_TAGS = {"note": ("c-note", "訳注"), "sic": ("c-sic", "原典の誤り"),
         "orig": ("c-orig", "原文")}

# 画面の決まり文句。book.yml の `lang: en` で英語にする(既定は日本語。訳文でない英語の教材用・BL-246)。
# <html lang> も合わせる(読み上げ・フォント選択のため)。
_LANG = "ja"
_WORDS = {"ja": {"toc": "目次", "back": "↑ 目次へ", "note": "訳注", "sic": "原典の誤り", "orig": "原文", "portal": "‹ ポータル"},
          "en": {"toc": "Contents", "back": "↑ Contents", "note": "Note", "sic": "Error in the source", "orig": "Original",
                 "portal": "‹ Portal"}}


def set_lang(meta, lang=None):
    """画面の決まり文句の言語を決める。lang を渡せばその言語、無ければ book.yml の lang:。
    words: は決まり文句の上書き。`{note: 補足}`(既定の言語に効く)でも `{ja: {note: 補足}}`(言語ごと)でもよい。"""
    global _LANG
    base = meta.get("lang") if meta.get("lang") in _WORDS else "ja"
    _LANG = lang if lang in _WORDS else base
    words = meta.get("words") or {}
    per = words if words and all(k in _WORDS and isinstance(v, dict) for k, v in words.items()) else {base: words}
    if per.get(_LANG):
        _WORDS[_LANG] = dict(_WORDS[_LANG], **per[_LANG])


def _w(key):
    return _WORDS[_LANG][key]


def _finish_lang(page_html):
    return page_html if _LANG == "ja" else page_html.replace('<html lang="ja">', f'<html lang="{_LANG}">', 1)


def expand_containers(md_text):
    """:::note / :::sic / :::orig … ::: を HTML ブロックへ開く。

    markdown-it(html:true) は生 HTML ブロックの**前後に空行があれば**中身を
    通常の Markdown として処理する。開き・閉じの行を独立させて挟むだけでよい。
    """
    out, in_fence, stack = [], False, []
    for line in md_text.split("\n"):
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence:
            m = re.match(r"^:::\s*(\w+)\s*$", line)
            if m and m.group(1) in _TAGS:
                cls = _TAGS[m.group(1)][0]
                label = _w(m.group(1))
                if m.group(1) == "orig":
                    out += ["", f'<details class="callout {cls}">',
                            f"<summary>{label}（クリックで開く）</summary>", ""]
                    stack.append("</details>")
                else:
                    out += ["", f'<div class="callout {cls}">',
                            f'<span class="tag">{label}</span>', ""]
                    stack.append("</div>")
                continue
            if line.strip() == ":::" and stack:
                out += ["", stack.pop(), ""]
                continue
        out.append(line)
    while stack:
        out += ["", stack.pop(), ""]
    return "\n".join(out)


def expand_sic(md_text, offset=0):
    """{{sic:語|注}} → 本文は語のまま・上付き番号。注は節末へ回す。

    offset= 束ね版でページをまたいで通し番号にするための開始位置。
    """
    notes = []

    def rep(m):
        word, note = m.group(1).strip(), m.group(2).strip()
        notes.append((word, note))
        n = offset + len(notes)
        return (f'<span class="sic" id="sic{n}">{html.escape(word)}'
                f'<sup>[{n}]</sup></span>')

    return SIC_RE.sub(rep, md_text), notes


def notes_section(notes, offset=0):
    if not notes:
        return ""
    items = "\n".join(
        f'<li><a href="#sic{i}">[{i}]</a> '
        f'<span class="q">{html.escape(w)}</span> — {html.escape(n)}</li>'
        for i, (w, n) in enumerate(notes, offset + 1))
    return ('\n\n<section class="notes">\n<h2>訳注（原典の記述をそのまま残した箇所）</h2>\n'
            f"<ol>\n{items}\n</ol>\n</section>\n")


# --------------------------------------------------------------------------
# 生成後の HTML 加工
# --------------------------------------------------------------------------
def wrap_tables(page_html):
    """表を横スクロールできる枠で包む（スマホで画面外へ消えないように）。"""
    return (page_html.replace("<table>", '<div class="tw"><table>')
                     .replace("</table>", "</table></div>"))


def termify(page_html):
    """```console → 端末ウィンドウ風に包み、プロンプト行とコメントを強調する。"""
    pat = re.compile(
        r'<pre class="code"><code class="lang-(' + "|".join(TERM_LANGS) +
        r')">(.*?)</code></pre>', re.S)

    def rep(m):
        body = CMT_RE.sub(r'\1<span class="cmt">\2</span>', m.group(2))
        body = PROMPT_RE.sub(r'<span class="prompt">\1</span>\2', body)
        return ('<div class="term"><div class="termbar"><i></i><i></i><i></i>'
                "<b>console</b></div>"
                f'<pre class="code"><code>{body}</code></pre></div>')

    return pat.sub(rep, page_html)


IMG_DIR = "img"
IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc=")(' + IMG_DIR + r'/[^"]+)(")')


def lazy_images(page_html):
    """図版は画面に入ってから読む（キャプチャが数十枚あるページの初期表示を軽くする）。"""
    return page_html.replace("<img ", '<img loading="lazy" decoding="async" ')


def copy_images(src, out_dir):
    """<src>/img/ を出力先へ写す。無ければ何もしない。"""
    d = os.path.join(src, IMG_DIR)
    if os.path.isdir(d):
        shutil.copytree(d, os.path.join(out_dir, IMG_DIR), dirs_exist_ok=True)
        return len(os.listdir(d))
    return 0


def inline_images(page_html, src):
    """束ね版用: img/… への参照を data URI に置き換える（外部参照ゼロを保つ）。"""
    cache = {}

    def rep(m):
        rel = html.unescape(m.group(2))
        if rel not in cache:
            path = os.path.join(src, rel)
            if not os.path.exists(path):
                print(f"[reading] 警告: 図版が無い {rel}", file=sys.stderr)
                cache[rel] = None
            else:
                mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
                with open(path, "rb") as fh:
                    cache[rel] = f"data:{mime};base64," + base64.b64encode(fh.read()).decode("ascii")
        return m.group(0) if cache[rel] is None else m.group(1) + cache[rel] + m.group(3)

    return IMG_SRC_RE.sub(rep, page_html)


# --------------------------------------------------------------------------
# ページ構成
# --------------------------------------------------------------------------
def _first_heading(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        m = re.search(r"^#\s+(.+)$", fh.read(), re.M)
    return m.group(1).strip() if m else default


def _pick(value, lang, default=""):
    """book.yml の値が {en: …, ja: …} ならその言語の分、文字列ならそのまま。"""
    if isinstance(value, dict):
        return value.get(lang) or default or next(iter(value.values()), "")
    return value if value is not None else default


def load_book(src):
    """book.yml があれば読む。無ければ NN-*.md を名前順に並べる。

    ★2 言語の本(BL-248): book.yml に `lang:` と `alt_lang:`(en / ja)を書くと、ページは
      <src>/<lang>/<file>(既定で出す版)と <src>/<alt_lang>/<file>(切替先)の 2 版を 1 ページに持ち、
      ページの中のボタンで切り替わる(問題パックと同じ仕組み・選んだ言語は共通で覚える)。
      切替先のファイルが無いページは 1 版のまま出す。title・subtitle・chapters の値は {en: …, ja: …} で書ける。
    """
    meta = {"key": os.path.basename(os.path.abspath(src)), "title": "読み物",
            "subtitle": "", "pages": []}
    y = os.path.join(src, "book.yml")
    if os.path.exists(y):
        import yaml
        with open(y, encoding="utf-8") as fh:
            meta.update(yaml.safe_load(fh) or {})
    lang, alt = meta.get("lang"), meta.get("alt_lang")
    two = {lang, alt} == {"en", "ja"}
    meta["_langs"] = [lang, alt] if two else [lang if lang in _WORDS else "ja"]
    base = os.path.join(src, lang) if two else src
    if not meta["pages"]:
        files = sorted(f for f in os.listdir(base)
                       if f.endswith(".md") and not f.startswith("_"))
        meta["pages"] = [{"file": f} for f in files]
    for p in meta["pages"]:
        p["_path"] = os.path.join(base, p["file"])
        alt_path = os.path.join(src, alt, p["file"]) if two else None
        p["_alt_path"] = alt_path if alt_path and os.path.exists(alt_path) else None
        if not p.get("title"):
            p["title"] = _first_heading(p["_path"], p["file"])
        # 言語ごとの題名(ナビ・目次・前後のページへのリンクに使う)
        p["_titles"] = {meta["_langs"][0]: _pick(p["title"], meta["_langs"][0])}
        if two:
            p["_titles"][alt] = (_pick(p["title"], alt) if isinstance(p["title"], dict)
                                 else _first_heading(p["_alt_path"], p["_titles"][lang]) if p["_alt_path"]
                                 else p["_titles"][lang])
        p["title"] = p["_titles"][meta["_langs"][0]]
        p["html"] = os.path.splitext(p["file"])[0] + ".html"
    return meta


def _both(meta, by_lang):
    """言語ごとの文字列 → 片方だけ見える 2 つの span(1 言語の本ならその 1 つをそのまま)。中身は呼ぶ側でエスケープ済み。"""
    langs = meta["_langs"]
    if len(langs) == 1:
        return by_lang[langs[0]]
    return "".join(f'<span data-l="{l}">{by_lang[l]}</span>' for l in langs)


def _page_text(meta, i, lang, path, offset=0):
    """1 ページ・1 言語ぶんの本文(記法を開き、前後のページへのリンクを付ける)。(Markdown, 訳注の数)。"""
    pages = meta["pages"]
    set_lang(meta, lang)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text = expand_containers(expand_topo(text))
    text, notes = expand_sic(text, offset)
    text += notes_section(notes, offset)
    t = lambda j: html.escape(pages[j]["_titles"][lang])
    prev_ = f'<a href="{pages[i-1]["html"]}">← {t(i-1)}</a>' if i else "<span></span>"
    next_ = f'<a href="{pages[i+1]["html"]}">{t(i+1)} →</a>' if i + 1 < len(pages) else "<span></span>"
    return text + f'\n\n<div class="pager">{prev_}{next_}</div>\n', len(notes)


def build_page(src, meta, i, out_dir, mermaid_mode):
    pages, langs = meta["pages"], meta["_langs"]
    p = pages[i]
    text, n = _page_text(meta, i, langs[0], p["_path"])
    kw = {}
    if len(langs) == 2 and p["_alt_path"]:
        alt_text, _n = _page_text(meta, i, langs[1], p["_alt_path"])
        kw = {"lang": langs[0], "alt_lang": langs[1], "alt_md": alt_text}
    set_lang(meta)
    # ナビの文言は言語ごとに出し分ける。render はラベルをエスケープするので、目印を置いて後から差し替える
    marks = {}

    def mark(by_lang):
        key = f"@@RNAV{len(marks)}@@"
        marks[key] = _both(meta, {l: html.escape(v) for l, v in by_lang.items()})
        return key

    word = lambda k: {l: _WORDS[l][k] for l in langs}
    # 先頭= 配信サーバのトップ(ポータル・BL-247)。`/` はどの配信のしかたでもサーバの根を指す
    nav = [{"label": mark(word("portal")), "href": "/"}, {"label": mark(word("toc")), "href": "index.html"}] + [
        {"label": mark(pg["_titles"]), "href": pg["html"], "current": j == i}
        for j, pg in enumerate(pages)]
    out = RH.render(text, title=p["title"], nav=nav, extra_css=READING_CSS,
                    body_class="reading", allow_html=True,
                    mermaid_mode=("cdn" if mermaid_mode == "local" else mermaid_mode), **kw)
    for key, val in marks.items():
        out = out.replace(key, val)
    if mermaid_mode == "local":
        out = out.replace(RH.MERMAID_CDN, "mermaid.min.js")
    out = _finish_lang(lazy_images(wrap_tables(termify(out))))
    dst = os.path.join(out_dir, p["html"])
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(out)
    return dst, n


def build_index(meta, out_dir):
    langs = meta["_langs"]

    def body(lang):
        set_lang(meta, lang)
        items = "\n".join(
            f'<li><a href="{p["html"]}">{html.escape(p["_titles"][lang])}</a></li>'
            for p in meta["pages"])
        sub = _pick(meta.get("subtitle"), lang)
        return (f'<p class="portal"><a href="/">{_w("portal")}</a></p>\n\n# {_pick(meta["title"], lang)}\n\n'
                + (f'<p class="lead">{html.escape(sub)}</p>\n\n' if sub else "")
                + f'<ul class="toc">\n{items}\n</ul>\n')

    kw = {"lang": langs[0], "alt_lang": langs[1], "alt_md": body(langs[1])} if len(langs) == 2 else {}
    first = body(langs[0])
    set_lang(meta)
    out = RH.render(first, title=_pick(meta["title"], langs[0]), extra_css=READING_CSS,
                    body_class="reading", allow_html=True, mermaid_mode="none", **kw)
    dst = os.path.join(out_dir, "index.html")
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(_finish_lang(out))
    return dst


def build(src, mermaid_mode="local"):
    src = src if os.path.isabs(src) else os.path.join(REPO, src)
    meta = load_book(src)
    set_lang(meta)
    out_dir = os.path.join(OUT_ROOT, meta["key"])
    os.makedirs(out_dir, exist_ok=True)
    if mermaid_mode == "local":
        dst = os.path.join(out_dir, "mermaid.min.js")
        if os.path.exists(RH.MERMAID_JS) and not os.path.exists(dst):
            shutil.copyfile(RH.MERMAID_JS, dst)
        elif not os.path.exists(RH.MERMAID_JS):
            print("[reading] 警告: mermaid.min.js が無いので CDN にします", file=sys.stderr)
            mermaid_mode = "cdn"
    copy_images(src, out_dir)
    total = 0
    for i in range(len(meta["pages"])):
        dst, n = build_page(src, meta, i, out_dir, mermaid_mode)
        total += n
        print(f"  {os.path.relpath(dst, REPO)}  （訳注 {n}）")
    build_index(meta, out_dir)
    # ポータル(配信サーバのトップ・BL-247)が教材の一覧を作るためのメタ。出力先だけを見れば足りるようにする
    # (ソースは非公開側にあることもあるので、ポータルはソースを読まない)。
    import json
    with open(os.path.join(out_dir, "book.json"), "w", encoding="utf-8") as fh:
        langs = meta["_langs"]
        json.dump({"key": meta["key"], "title": _pick(meta["title"], langs[0]),
                   "subtitle": _pick(meta.get("subtitle"), langs[0]),
                   "title_alt": _pick(meta["title"], langs[-1]) if len(langs) == 2 else "",
                   "subtitle_alt": _pick(meta.get("subtitle"), langs[-1]) if len(langs) == 2 else "",
                   "shelf": meta.get("shelf", ""), "lang": langs[0], "langs": langs,
                   "order": meta.get("order", 50), "labs": meta.get("labs") or [],
                   "pages": len(meta["pages"])}, fh, ensure_ascii=False, indent=1)
    print(f"[reading] {len(meta['pages'])} ページ / 訳注 {total} 件 → "
          f"{os.path.relpath(out_dir, REPO)}/index.html")
    return out_dir


# --------------------------------------------------------------------------
# 束ね版: 全ページを 1 枚の HTML に。外部参照ゼロ＝オフラインで読める
#   （Drive へ上げてスマホに落として開く、という使い方を想定・2026-09-29）
# --------------------------------------------------------------------------
BUNDLE_CSS = """
body.reading .btoc{ margin:2rem 0 1rem; padding:1rem 1.2rem; background:#f7f8fa;
  border:1px solid #dde1e6; border-radius:6px; }
body.reading .btoc ol{ margin:.4rem 0; }
body.reading .btoc li{ margin:.4rem 0; }
body.reading .bsep{ border:0; border-top:3px double #bbb; margin:5rem 0 0; }
body.reading .bhome{ display:block; margin:2.4rem 0 0; font-size:.86rem; }
"""


def _chapter_of(page):
    """ページの所属章。book.yml の chapter:、無ければファイル名の chNN から。"""
    if page.get("chapter") is not None:
        return str(page["chapter"]).zfill(2)
    m = re.search(r"ch(\d+)", page["file"], re.I)
    return m.group(1).zfill(2) if m else "00"


def _assemble(meta, pages, title, dst):
    """指定ページ群を 1 枚の自己完結 HTML に組む。"""
    chunks, offset = [], 0
    toc = "\n".join(f'<li><a href="#pg{i}">{html.escape(p["title"])}</a></li>'
                     for i, p in enumerate(pages))
    head = [f"# {title}", ""]
    if _pick(meta.get("subtitle"), _LANG):
        head.append(f'<p class="lead">{html.escape(_pick(meta.get("subtitle"), _LANG))}</p>')
    head += [f'<nav class="btoc"><strong>{_w("toc")}</strong>', f"<ol>\n{toc}\n</ol>", "</nav>"]
    chunks.append("\n".join(head))

    for i, p in enumerate(pages):
        with open(p["_path"], encoding="utf-8") as fh:
            text = fh.read()
        text = expand_containers(expand_topo(text))
        text, notes = expand_sic(text, offset)
        text += notes_section(notes, offset)
        offset += len(notes)
        sep = '<hr class="bsep">\n\n' if i else ""
        chunks.append(f'{sep}<a id="pg{i}"></a>\n\n{text}\n\n'
                      f'<a class="bhome" href="#top">{_w("back")}</a>')

    md = "\n\n".join(chunks)
    mode = "embed" if "```mermaid" in md else "none"
    out = RH.render(md, title=title, extra_css=READING_CSS + BUNDLE_CSS,
                    body_class="reading", allow_html=True, mermaid_mode=mode)
    out = out.replace("<body", '<body id="top"', 1)
    out = _finish_lang(inline_images(wrap_tables(termify(out)), os.path.dirname(pages[0]["_path"])))
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(out)
    ext = re.findall(r'(?:src|href)="(?!#|data:)([^"]+)"', out)
    print(f"  {os.path.relpath(dst, REPO):46} {len(out)/1024:7.0f}KB  "
          f"{len(pages)} ページ / 訳注 {offset} 件"
          + ("" if not ext else f"  ★外部参照 {ext}"))
    return dst


def stage_dir(key):
    """持ち出し用の置き場。ここを丸ごと Drive へ同期する（中身＝章ごとの HTML だけ）。"""
    return os.path.join(OUT_ROOT, "_offline", key)


def build_bundle(src, out_path=None, split=False, stage=False):
    """split=True で **章ごとに 1 枚**。既定は全ページを 1 枚。

    ★持ち出し(Drive→スマホ)を考えると章ごとが扱いやすい。章 1 つ＝数十〜数百 KB で、
      更新した章だけ入れ替えられる。stage=True で持ち出し用ディレクトリへ出す
      （そこを rclone で同期する。作成・改訂・削除がそのまま反映される）。
    ★2 言語の本は **言語ごとに別の 1 枚**を作る(切替式にしない)。持ち出し先の閲覧アプリではスクリプトが
      動かないことがあり、切替ボタンが効かないと片方の言語が読めなくなるため。置き場は言語ごとの下位フォルダ
      (stage なら reading/_offline/<key>/<言語>/)。
    """
    src = src if os.path.isabs(src) else os.path.join(REPO, src)
    meta = load_book(src)
    key, titles, langs = meta["key"], (meta.get("chapters") or {}), meta["_langs"]
    two = len(langs) == 2
    made = []
    if split and stage:                # 消えた章を残さないため、毎回作り直す
        shutil.rmtree(stage_dir(key), ignore_errors=True)
    for lang in langs:
        set_lang(meta, lang)
        # その言語の版のページ(切替先のファイルが無いページは既定の版で代える)
        pages = [dict(p, title=p["_titles"][lang],
                      _path=(p["_alt_path"] if lang != langs[0] and p["_alt_path"] else p["_path"]))
                 for p in meta["pages"]]
        book_title = _pick(meta["title"], lang)
        tag = f"-{lang}" if two else ""
        if split:
            chs = {}
            for p in pages:
                chs.setdefault(_chapter_of(p), []).append(p)
            for ch, ps in sorted(chs.items()):
                name = str(_pick(titles.get(ch) or titles.get(int(ch)), lang) or f"ch{ch}")
                dst = (os.path.join(stage_dir(key), lang if two else "", f"{name}.html") if stage
                       else os.path.join(OUT_ROOT, f"{key}{tag}-ch{ch}-offline.html"))
                made.append(_assemble(meta, ps, f"{book_title} — {name}", dst))
        else:
            made.append(_assemble(meta, pages, book_title,
                                  out_path or os.path.join(OUT_ROOT, f"{key}{tag}-offline.html")))
    set_lang(meta)
    return made



def main():
    ap = argparse.ArgumentParser(description="読み物 Markdown → HTML")
    ap.add_argument("cmd", choices=["build", "bundle"])
    ap.add_argument("--src", required=True, help="読み物ソースのディレクトリ")
    ap.add_argument("--mermaid", default="local", choices=["local", "cdn", "embed", "none"],
                    help="local= mermaid.min.js を出力先に1本置いて共有(既定)")
    ap.add_argument("--out", help="bundle の出力先(既定 reading/<key>-offline.html)")
    ap.add_argument("--split", action="store_true", help="章ごとに 1 枚に分ける")
    ap.add_argument("--stage", action="store_true",
                    help="持ち出し用ディレクトリ reading/_offline/<key>/ へ出す(--split 前提)")
    a = ap.parse_args()
    if a.cmd == "bundle":
        build_bundle(a.src, a.out, a.split or a.stage, a.stage)
    else:
        build(a.src, a.mermaid)


if __name__ == "__main__":
    main()
