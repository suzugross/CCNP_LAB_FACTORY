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
  :::try  ... :::               … やってみる（緑。読者が自分で障害を起こして確かめる手順。書き下ろしの教材用）
  :::topo ... :::               … ネットワーク図（座標指定の SVG・下記）
  :::config <見出し> ... :::     … 設定例（左に設定の行・右に注記。行末の `  ## 注記` が注記の列へ。コピーは設定の行だけ）
  :::config fold <見出し> ... ::: … 同じく折りたたみ（課題の答えそのものになる例。見出しに「課題 … の答え」と書く）
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
                       `toc: units` … 目次(index.html)を単元(chapters:)ごとのカードに分けて並べる(既定はページの一覧)。
                         章の大きさがそろった教材向け。1 章に何十ページもある訳文の本は一覧のままのほうが読みやすい
                         カードの見出しは章の名前の先頭の語(「M4 IS-IS」→ バッジ M4・名前 IS-IS)。ページ題名の同じ接頭辞は落とす
                         `parts: [{title, chapters: [章番号]}]` … 単元を部に束ねる(部の見出し付き)。どの部にも無い単元は末尾に出る(警告)
                         ページの種類(行の色)は pages の `kind:`(read / practice / appendix)、無ければファイル名から
                         <src>/practice.yml(courses/ の実践ページの対応表)があれば、実践の行に課題のラボ ID を添える
  → 出力先に book.json(ポータルが読む一覧用のメタ。節の一覧 sections・ページ題名 page_titles・「やってみる」tries も)も書く
  ★節の目印(BL-252): h2/h3 に言語に依らない data-sec="s<n>" / "s<n>-<m>" を振る。`<ページ>.html#s2` で表示中の版の節へ飛ぶ。
    ラボのワークスペースの Reading タブ(learn.yml の read:)と実践ページのリンクが使う。2 版の見出しの並びがずれると警告する
  `<p class="tolab">…</p>`(行頭) … 配信時だけのリンク(ワークスペース・他ページの節)。持ち出しの 1 枚では落とす
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
body.reading{ font-size:1.03rem; line-height:2.05; letter-spacing:.012em; }
/*  画素の細かい広い画面(MacBook など)では、ページ全体を 100%→150% に大きくする(2026-10-31 ユーザ要望「いつも 150% に拡大して
    見ている」)。rem の基準(html の文字の大きさ)を画面の幅で上げる= ブラウザで拡大したのと同じ見え方(本文の幅も一緒に広がり、
    1 行の字数は変わらない)。幅 1000px で 100%、1200px 以上で 150%。狭い画面(スマホ・ワークスペースの Reading の枠)は条件に
    入らないので今のまま。ブラウザで 150% に拡大したままでも、拡大後の幅は約 1000px なので二重には大きくならない。
    ★この大きさに付いてくるよう、文字や幅は px でなく rem で書く(図の SVG も幅を rem で出す)。 */
@media (min-width:1000px) and (min-resolution:2dppx), (min-width:1000px) and (-webkit-min-device-pixel-ratio:2){
  html{ font-size:clamp(100%, calc(4vw - 24px), 150%); }
}
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

/* ---- ナビ帯(BL-253): 下端に固定・☰ で上に開く縦のメニュー ---- */
.rnav{ position:fixed; left:0; right:0; bottom:0; z-index:20; background:#fff; border-top:1px solid #222;
  display:flex; align-items:center; gap:.6rem; padding:.4rem .9rem; font-size:.88rem; line-height:1.4; }
.rnav a{ text-decoration:none; }
.rn-portal{ white-space:nowrap; }
.rn-menu{ position:relative; min-width:0; flex:0 1 auto; }
.rn-btn{ font:inherit; display:flex; align-items:center; gap:.45rem; max-width:100%; cursor:pointer;
  background:#f3f4f6; border:1px solid #c9ced6; border-radius:5px; padding:.28rem .7rem; color:#111; }
.rn-btn:hover{ background:#e9ecf0; } .rn-btn[aria-expanded="true"]{ background:#e3e8ef; border-color:#8796ab; }
.rn-cur{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:600; }
.rn-ic, .rn-car{ color:#555; flex:none; }
.rn-panel{ position:absolute; bottom:calc(100% + 8px); left:0; width:min(24rem, calc(100vw - 2rem));
  max-height:70vh; overflow:auto; background:#fff; border:1px solid #c9ced6; border-radius:7px;
  box-shadow:0 6px 24px rgba(0,0,0,.18); padding:.4rem 0; }
.rn-panel a{ display:block; padding:.36rem 1rem; color:#1a1f27; }
.rn-panel a:hover{ background:#eef2f7; }
.rn-panel a.cur{ background:#e3ebf6; border-left:3px solid #3f7fbf; padding-left:calc(1rem - 3px); font-weight:600; }
.rn-panel .rn-toc{ font-weight:600; }
.rn-panel .rn-toc{ border-bottom:1px solid #d5dae1; }
.rn-grp{ padding:.2rem 0; } .rn-grp + .rn-grp{ border-top:1px solid #d5dae1; }
.rn-grp.here{ background:#f4f7fb; }
.rn-sp{ flex:1; }
.rn-step{ font-size:1.05rem; padding:.1rem .45rem; border-radius:4px; }
.rn-step:hover{ background:#eef2f7; } .rn-step.off{ color:#c3c7cd; }

/* ---- 実践へのリンク(BL-252)= ワークスペースで開く・課題の背景の節 ---- */
body.reading .tolab{ font-size:.86rem; line-height:1.7; margin:.5rem 0 1rem; padding:.35rem .7rem;
  background:#f3f6fa; border-left:3px solid #3f7fbf; border-radius:3px; }
body.reading .tolab a{ text-decoration:none; } body.reading .tolab a:hover{ text-decoration:underline; }

/* ---- 端末風のコンソール出力 ---- */
.term{ margin:1.9rem 0; border-radius:7px; overflow:hidden;
  box-shadow:0 1px 4px rgba(0,0,0,.28); }
.termbar{ background:#2b2f36; padding:.42rem .7rem; display:flex; gap:.4rem;
  align-items:center; }
.termbar i{ width:.69rem; height:.69rem; border-radius:50%; display:inline-block; }
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
body.reading pre.code code{ font-size:.81rem; }               /* 素のコード欄(基本の 13px を rem に) */
body.reading .term pre.code code{ font-size:.845rem; }
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
.c-try{ background:#eef8ef; border-left:4px solid #3f8f4f; }
.c-try .tag{ background:#3f8f4f; color:#fff; }
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

/* ---- 設定例(:::config)= 左に設定の行・右に「何をする行か」。注記は選択してもコピーされない ---- */
.cfg{ display:block; margin:1.9rem 0; border:1px solid #cfd6df; border-radius:7px; background:#fbfcfd; overflow:hidden; }
.cfg > figcaption, .cfg > summary{ display:flex; align-items:center; gap:.55rem; padding:.45rem .75rem;
  background:#eef1f5; border-bottom:1px solid #d9dee5; font-size:.88rem; font-weight:600; color:#2c3540; line-height:1.5; }
.cfg > summary{ cursor:pointer; list-style:none; }
.cfg > summary::-webkit-details-marker{ display:none; }
.cfg > summary::before{ content:"▸"; color:#6b7685; flex:none; }
.cfg[open] > summary::before{ content:"▾"; }
details.cfg:not([open]) > summary{ border-bottom:0; }
.cfg .ctag{ flex:none; font-size:.72rem; font-weight:700; letter-spacing:.05em; background:#4a5a70; color:#fff;
  border-radius:3px; padding:.08rem .45rem; }
.cfg .ctitle{ flex:1; min-width:0; }
.cfg .cfold{ font-weight:400; color:#6b7685; font-size:.8rem; white-space:nowrap; }
.cfg .ccopy{ flex:none; font:inherit; font-size:.76rem; font-weight:400; cursor:pointer; background:#fff;
  border:1px solid #c3cad3; border-radius:4px; padding:.12rem .55rem; color:#2c3540; }
.cfg .ccopy:hover{ background:#f3f5f8; }
.cfg .cb{ display:grid; grid-template-columns:max-content minmax(13rem, 1fr); column-gap:1.5rem;
  padding:.75rem .95rem; overflow-x:auto; }
.cfg .cr{ display:contents; }
.cfg .cc{ font-family:"Cascadia Mono",Consolas,"DejaVu Sans Mono",monospace; font-size:.83rem; line-height:1.65;
  white-space:pre; padding:0; background:none; border:0; color:#14202e; }
.cfg .cn{ font-size:.82rem; line-height:1.65; color:#3f6286; user-select:none; -webkit-user-select:none; }
.cfg .cn code{ font-size:.92em; }

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
  body.reading{ font-size:1rem; line-height:1.95; }
  body.reading main{ padding:1rem .9rem 5rem; }
  body.reading h1{ font-size:1.35rem; }
  body.reading h2{ font-size:1.12rem; margin:2.7rem 0 .9rem; }
  body.reading h3{ margin:2.1rem 0 .7rem; }
  .term code, body.reading .term pre.code code{ font-size:.76rem; }
  .term pre{ padding:.8rem .85rem; }
  .callout{ margin:1.6rem 0; padding:.8rem .9rem; }
  .topo{ margin:1.7rem 0; }
  .cfg .cb{ grid-template-columns:1fr; padding:.65rem .75rem; }
  .cfg .cc{ font-size:.76rem; }
  .cfg .cn{ padding-left:1.2rem; margin-bottom:.3rem; font-size:.78rem; }
  .cfg .cn:empty{ display:none; }
  .nav{ font-size:.8rem; }
}

/* ---- ページ送り ---- */
.pager{ margin-top:4rem; padding-top:.9rem; border-top:1px solid #ccc;
  display:flex; justify-content:space-between; gap:1rem; font-size:.92rem; }
.pager a{ text-decoration:none; }
.toc li{ margin:.3rem 0; }
"""

# 目次(index.html)だけに足す。単元ごとのカードを部ごとの格子に並べる
#   (2026-10-27 ユーザ要望「順番に羅列しているだけで分かりづらい・お目当ての単元に行きやすく」)。
#   行の左の色= ページの種類(青= 読み物・緑= 実践・灰= 付録)。
INDEX_CSS = """
body.reading.rindex main{ max-width:64rem; }
.cidx{ margin:2.4rem 0 0; line-height:1.5; letter-spacing:normal; }
.cidx .ph{ display:flex; align-items:baseline; gap:.75rem; margin:2.8rem 0 1rem; padding:0 0 .4rem;
  border:0; border-bottom:1px solid #c9ced6; font-size:1.02rem; line-height:1.5; color:#2c3540; }
.cidx .ph:first-child{ margin-top:0; }
.cidx .pr{ font-size:.8rem; font-weight:600; color:#7a8594; }
.ugrid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(min(17.5rem, 100%), 1fr)); gap:1rem; }
.unit{ display:flex; flex-direction:column; gap:.2rem; background:#fff; border:1px solid #d5dae1;
  border-radius:8px; padding:.85rem .75rem .75rem; box-shadow:0 1px 3px rgba(20,30,45,.07); }
.cidx .uh{ display:flex; align-items:center; gap:.65rem; margin:0 0 .55rem; padding:0 .15rem; border:0;
  font-size:1.04rem; line-height:1.4; color:#111; }
.ucode{ flex:none; min-width:2.7rem; text-align:center; font:700 .9rem/1 "Cascadia Mono",Consolas,"DejaVu Sans Mono",monospace;
  background:#1f2a37; color:#fff; border-radius:5px; padding:.45rem .5rem; }
.uname{ font-weight:700; }
.cidx a.ur{ display:flex; align-items:center; gap:.6rem; padding:.45rem .6rem; border-left:3px solid #3f7fbf;
  border-radius:0 4px 4px 0; color:#1a1f27; text-decoration:none; font-size:.95rem; }
.cidx a.ur:hover{ background:#eef2f7; }
.cidx a.ur.k-practice{ border-left-color:#3f8f4f; }
.cidx a.ur.k-practice:hover{ background:#eef8ef; }
.cidx a.ur.k-appendix{ border-left-color:#a7b0bb; color:#4a5360; font-size:.9rem; }
.ut{ flex:1; min-width:0; }
.ulab{ flex:none; font:600 .74rem/1 "Cascadia Mono",Consolas,"DejaVu Sans Mono",monospace; color:#2f6b3b;
  background:#e3f2e5; border-radius:3px; padding:.3rem .42rem; }
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


def _tw(text):
    """図の文字列の幅を半角何文字ぶんかで見積もる。全角(日本語など)は半角の約 1.75 倍の幅で描かれる
    (文字数だけで見積もると、日本語の名前が箱や札からはみ出していた)。"""
    import unicodedata
    return sum(1.75 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in str(text))


def _box(name, spec):
    at = spec["at"] if isinstance(spec, dict) else spec
    kind = spec.get("kind", "sw") if isinstance(spec, dict) else "sw"
    label = spec.get("label", name) if isinstance(spec, dict) else name
    w0, h, fill, stroke, r = NODE_STYLE.get(kind, NODE_STYLE["sw"])
    w = max(w0, int(_tw(label) * 8.6) + 22)
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
    ext = []                       # 描いたものの外形(x1, y1, x2, y2)。描画範囲(viewBox)を決める

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
        ext.append((x1, y1, x2, y2))
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
        w = _tw(lab) * 7.4 + 10
        parts.append(f'<rect class="tlb" x="{x-w/2:.0f}" y="{y-9:.0f}" '
                     f'width="{w:.0f}" height="18" rx="3"/>')
        ext.append((x - w / 2, y - 9, x + w / 2, y + 9))
        parts.append(f'<text class="tlt" x="{x:.0f}" y="{y+4:.0f}">'
                     f"{html.escape(str(lab))}</text>")

    for b in boxes.values():       # ノードは最前面
        parts.append(
            f'<rect x="{b["x"]-b["w"]/2:.0f}" y="{b["y"]-b["h"]/2:.0f}" '
            f'width="{b["w"]}" height="{b["h"]}" rx="{b["r"]}" '
            f'fill="{b["fill"]}" stroke="{b["stroke"]}" stroke-width="1.6"/>')
        parts.append(f'<text class="tn" x="{b["x"]:.0f}" y="{b["y"]+5:.0f}">'
                     f'{html.escape(b["label"])}</text>')

    ext += [(b["x"] - b["w"] / 2, b["y"] - b["h"] / 2, b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)
            for b in boxes.values()]
    # 描画範囲= 既定は原点から「いちばん右下の箱+余白」。横に長い箱や枠が原点より左・上へはみ出す時は
    # その分だけ範囲を広げる(列 0 に名前の長い箱を置くと、枠の左上が切れていた。2026-10-25 ユーザ指摘)
    x0 = min(0, min(e[0] for e in ext) - 8)
    y0 = min(0, min(e[1] for e in ext) - 8)
    right = max(max(b["x"] + b["w"] / 2 for b in boxes.values()) + MARGIN, max(e[2] for e in ext) + 8)
    bottom = max(max(b["y"] + b["h"] / 2 for b in boxes.values()) + MARGIN, max(e[3] for e in ext) + 8)
    W, H = right - x0, bottom - y0
    body = "\n".join(parts)
    return (f'<div class="topo"><svg viewBox="{x0:.0f} {y0:.0f} {W:.0f} {H:.0f}" '
            f'width="{W:.0f}" style="width:{W / 16:.2f}rem" role="img">\n{body}\n</svg></div>')


TOPO_RE = re.compile(r"^:::topo[ \t]*\n(.*?)^:::[ \t]*$", re.S | re.M)


def expand_topo(md_text):
    return TOPO_RE.sub(lambda m: "\n" + render_topo(m.group(1)) + "\n", md_text)


# --------------------------------------------------------------------------
# 設定例(:::config → 注記つきの設定の欄)
#   2026-10-31 ユーザ指示「config 例を常に提示して。まとまった形で見せてもらわないと知識が断片化する」。
#   設定の行と「何をする行か」を左右に並べる(狭い画面では注記を行の下へ)。コピーのボタンと手での選択は設定の行だけを取る。
#   fold= 折りたたむ(課題の答えそのものになる例。見出しに「課題 … の答え」と書く)。
#   生成する HTML には空行も </div> も入れない(markdown-it の HTML ブロックが空行で切れる・:::try の取り出しが </div> で切れる)。
# --------------------------------------------------------------------------
CONFIG_RE = re.compile(r"^:::config(?:[ \t]+(fold)(?=[ \t]|$))?[ \t]*([^\n]*)\n(.*?)^:::[ \t]*$", re.S | re.M)
CFG_NOTE_RE = re.compile(r"\s+##\s?(.*)$")


def _cfg_inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)


def render_config(fold, title, body):
    rows = []
    for ln in body.rstrip("\n").split("\n"):
        m = CFG_NOTE_RE.search(ln)
        code, note = (ln[:m.start()], m.group(1).strip()) if m else (ln, "")
        rows.append(f'<span class="cr"><code class="cc">{html.escape(code.rstrip()) or " "}</code>'
                    f'<span class="cn">{_cfg_inline(note)}</span></span>')
    head = (f'<span class="ctag">{_w("config")}</span><span class="ctitle">{_cfg_inline(title.strip())}'
            + (f' <span class="cfold">{_w("open")}</span>' if fold else "") + "</span>"
            f'<button type="button" class="ccopy" data-done="{_w("copied")}">{_w("copy")}</button>')
    body_html = '<span class="cb">\n' + "\n".join(rows) + "\n</span>"
    if fold:
        return f'<details class="cfg">\n<summary>{head}</summary>\n{body_html}\n</details>'
    return f'<figure class="cfg">\n<figcaption>{head}</figcaption>\n{body_html}\n</figure>'


def expand_config(md_text):
    return CONFIG_RE.sub(lambda m: "\n" + render_config(bool(m.group(1)), m.group(2), m.group(3)) + "\n", md_text)


def expand_blocks(md_text):
    """ソースの独自記法(図・設定例・囲み)を開く。設定例は囲みより先(:::try の中の設定例の閉じを囲みの閉じと取り違えない)。"""
    return expand_containers(expand_config(expand_topo(md_text)))


# 設定例のコピー(配信のページは http= 安全でない文脈なので clipboard API が無い→ textarea で写す)
CFG_JS = r"""
(function(){
  function put(t){
    if(navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(t);
    var ta = document.createElement('textarea'); ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try{ document.execCommand('copy'); }catch(_e){}
    document.body.removeChild(ta); return Promise.resolve();
  }
  document.querySelectorAll('.cfg .ccopy').forEach(function(b){
    b.addEventListener('click', function(ev){
      ev.preventDefault(); ev.stopPropagation();
      var lines = [].map.call(b.closest('.cfg').querySelectorAll('.cc'), function(c){ return c.textContent.replace(/\s+$/, ''); });
      put(lines.join('\n') + '\n').then(function(){
        var o = b.textContent; b.textContent = b.dataset.done; setTimeout(function(){ b.textContent = o; }, 1500);
      });
    });
  });
})();
"""


# --------------------------------------------------------------------------
# ソース Markdown の前処理
# --------------------------------------------------------------------------
SIC_RE = re.compile(r"\{\{sic:(.+?)\|(.+?)\}\}", re.S)
FENCE_RE = re.compile(r"^```")

_TAGS = {"note": ("c-note", "訳注"), "sic": ("c-sic", "原典の誤り"),
         "orig": ("c-orig", "原文"), "try": ("c-try", "やってみる")}

# 画面の決まり文句。book.yml の `lang: en` で英語にする(既定は日本語。訳文でない英語の教材用・BL-246)。
# <html lang> も合わせる(読み上げ・フォント選択のため)。
_LANG = "ja"
_WORDS = {"ja": {"toc": "目次", "back": "↑ 目次へ", "note": "訳注", "sic": "原典の誤り", "orig": "原文", "try": "やってみる", "portal": "‹ ポータル",
                 "prev": "前のページ", "next": "次のページ", "reading": "読み物",
                 "config": "設定例", "copy": "コピー", "copied": "コピーしました", "open": "(クリックで開く)"},
          "en": {"toc": "Contents", "back": "↑ Contents", "note": "Note", "sic": "Error in the source", "orig": "Original", "try": "Try it",
                 "portal": "‹ Portal", "prev": "Previous page", "next": "Next page", "reading": "Reading",
                 "config": "Configuration", "copy": "Copy", "copied": "Copied", "open": "(click to open)"}}


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
    # 実践ページ → 課題のラボ ID(courses/ の practice.yml。目次の実践の行に添える)
    labs = {}
    pr = os.path.join(src, "practice.yml")
    if os.path.exists(pr):
        import yaml
        with open(pr, encoding="utf-8") as fh:
            labs = {e["file"]: e.get("problem") for e in (yaml.safe_load(fh) or {}).get("pages") or []}
    for p in meta["pages"]:
        if labs.get(p["file"]):
            p.setdefault("lab", labs[p["file"]])
            p.setdefault("kind", "practice")
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
    text = expand_blocks(text)
    text, notes = expand_sic(text, offset)
    text += notes_section(notes, offset)
    t = lambda j: html.escape(pages[j]["_titles"][lang])
    prev_ = f'<a href="{pages[i-1]["html"]}">← {t(i-1)}</a>' if i else "<span></span>"
    next_ = f'<a href="{pages[i+1]["html"]}">{t(i+1)} →</a>' if i + 1 < len(pages) else "<span></span>"
    return text + f'\n\n<div class="pager">{prev_}{next_}</div>\n', len(notes)


# 節の目印(BL-252): h2/h3 に言語に依らない番号 data-sec="s<h2 の番目>" / "s<h2>-<h3 の番目>" を振る。
#   2 版は見出しの並びがそろっている(courses/ の規約)ので、同じ番号が両方の版の同じ節を指す。
#   ラボのワークスペースの Reading タブや実践ページのリンクは `<ページ>.html#s2` の形で節を指し、
#   READ_JS がいま表示中の版の該当見出しへ送る(id は版ごとに重なるので使わない)。
_SEC_TOK = re.compile(r'<div class="lv" data-l="(\w+)">|<h([23])((?:\s[^>]*)?)>(.*?)</h\2>', re.S)


def mark_sections(page_html):
    """見出しに data-sec を振る。(HTML, {sec: {lang: 見出しの文字}})。1 言語のページは lang を "" で返す。"""
    secs, cnt, lang = {}, [0, 0], ""

    def rep(m):
        nonlocal lang
        if m.group(1):
            lang = m.group(1)
            cnt[:] = [0, 0]
            return m.group(0)
        lv, attrs, inner = m.group(2), m.group(3) or "", m.group(4)
        if lv == "2":
            cnt[0] += 1
            cnt[1] = 0
            sec = f"s{cnt[0]}"
        else:
            cnt[1] += 1
            sec = f"s{cnt[0]}-{cnt[1]}"
        secs.setdefault(sec, {})[lang] = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        return f'<h{lv}{attrs} data-sec="{sec}">{inner}</h{lv}>'

    return _SEC_TOK.sub(rep, page_html), secs


# 「やってみる」(:::try)を節ごとに取り出す(2026-10-24 ユーザ要望)。ラボのワークスペースは、課題の read: が指す節にある
# 囲みを、課題カードのボタンから浮かぶ小窓で出す(文面は読み物の 1 か所だけに持つ)。mark_sections の後の HTML から取る
# = 囲みの中身はまだ termify・wrap_tables の前(div を含まない)なので、最初の </div> までが中身。
_TRY_TOK = re.compile(r'<div class="lv" data-l="(\w+)">|<h[23][^>]*\sdata-sec="([^"]+)"|'
                      r'<div class="callout c-try">\s*(?:<span class="tag">.*?</span>)?(.*?)</div>', re.S)


def extract_tries(marked_html):
    """{節: [{言語: 中身の HTML}, …]}。2 版は同じ並びなので、節の中の順番で組にする。1 言語のページは言語を "" にする。"""
    per, lang, sec = {}, "", ""
    for m in _TRY_TOK.finditer(marked_html):
        if m.group(1):
            lang, sec = m.group(1), ""
        elif m.group(2):
            sec = m.group(2)
        else:
            per.setdefault(sec, {}).setdefault(lang, []).append(m.group(3).strip())
    out = {}
    for sec, by_lang in per.items():
        n = max(len(v) for v in by_lang.values())
        out[sec] = [{l: v[k] for l, v in by_lang.items() if k < len(v)} for k in range(n)]
    return out


# 読み物のページに足す動き(BL-252):
#   ・`#s2` などの節の目印へ送る(いま表示中の版の見出しへ。言語を切り替えた後の hashchange でも)
#   ・実践へのリンク(.tolab の中の /_learn?id=…)は、ラボのワークスペースの枠の中では親の Steps タブを開く合図に替える。
#     単体で開いた時はそのままワークスペースへ移る。持ち出し(file://)では行き先が無いので出さない
#   ・ポータルへ戻るリンクは、枠の中では画面ごと移る(枠の中にポータルを開かない)
READ_JS = r"""
(function(){
  var framed = window.top !== window.self, synced = false;
  function go(){
    var m = /^#(s\d+(?:-\d+)?)$/.exec(location.hash);
    if(!m) return;
    var lang = document.body.dataset.lang, root = lang ? document.querySelector('.lv[data-l="' + lang + '"]') : document;
    var h = (root || document).querySelector('[data-sec="' + m[1] + '"]');
    if(h) h.scrollIntoView({block: 'start'});
  }
  window.addEventListener('hashchange', go);
  window.addEventListener('load', go);
  window.addEventListener('message', function(ev){
    if(!ev.data || ev.source !== window.parent) return;
    if(typeof ev.data.ccnpGoto === 'string'){          /* 親(ワークスペース)が同じページの別の節を指した */
      if(ev.data.ccnpGoto) history.replaceState(null, '', '#' + ev.data.ccnpGoto);
      go(); return;
    }
    /* 開いた直後に親が言語を合わせた時だけ節へ送り直す(以後の切替は LANG_JS が読んでいた位置を保つ) */
    if(typeof ev.data.ccnpLang === 'string' && !synced){ synced = true; setTimeout(go, 0); }
  });
  if(location.protocol === 'file:')
    document.querySelectorAll('.tolab').forEach(function(p){ p.style.display = 'none'; });
  document.querySelectorAll('.tolab a[href^="/_learn"]').forEach(function(a){
    if(!framed) return;
    a.addEventListener('click', function(ev){
      if(ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.altKey || ev.button) return;
      ev.preventDefault();
      var u = new URL(a.href);
      try{ window.parent.postMessage({ccnpStep: u.searchParams.get('step') || '', ccnpLab: u.searchParams.get('id') || ''}, '*'); }catch(_e){}
    });
  });
  if(framed) document.querySelectorAll('a[href="/"]').forEach(function(a){ a.target = '_top'; });
})();
"""


# 読み物のナビ帯(BL-253・2026-10-18 ユーザ要望「ただ並べてあるだけで見づらい」)。画面の下端に固定:
#   ‹ ポータル | ☰ いまのページ名 ▴ | ← →
#   ☰ を押すと上に向かってメニューが開く= 目次・ページの一覧(いまのページに印)。単元(章)ごとのまとまりを線で区切り、
#   いまの単元は薄く色を付ける。
#   ★ページ内の節の一覧も章の見出しも置かない(2026-10-18 ユーザ指示「目線が散る・シンプルに」
#     「章の見出しはページ名と同じになっている」)。
#   言語ごとの文字は _both で 2 つ持ち、切替(body の data-lang)で片方だけ見せる。
READ_NAV_JS = r"""
(function(){
  var nav = document.querySelector('.rnav'); if(!nav) return;
  var btn = nav.querySelector('.rn-btn'), panel = nav.querySelector('.rn-panel');
  function set(open){
    panel.hidden = !open; btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if(open){ var c = panel.querySelector('.cur'); if(c) c.scrollIntoView({block: 'nearest'}); }
  }
  btn.addEventListener('click', function(ev){ ev.stopPropagation(); set(panel.hidden); });
  panel.addEventListener('click', function(ev){ if(ev.target.closest('a')) set(false); });
  document.addEventListener('click', function(ev){ if(!panel.hidden && !nav.contains(ev.target)) set(false); });
  document.addEventListener('keydown', function(ev){ if(ev.key === 'Escape' && !panel.hidden){ set(false); btn.focus(); } });
})();
"""


def reading_nav(meta, i):
    pages, langs = meta["pages"], meta["_langs"]
    both = lambda by_lang: _both(meta, {l: html.escape(by_lang.get(l) or next(iter(by_lang.values()), "")) for l in langs})
    word = lambda k: both({l: _WORDS[l][k] for l in langs})
    p = pages[i]
    rows = [f'<a class="rn-toc" href="index.html">{word("toc")}</a>']
    # 単元(章)ごとにまとめ、まとまりの間に線を引く。いまのページがある単元は薄く色を付ける
    groups = []
    for j, pg in enumerate(pages):
        ch = _chapter_of(pg)
        if not groups or groups[-1][0] != ch:
            groups.append((ch, []))
        cur = ' class="cur" aria-current="page"' if j == i else ""
        groups[-1][1].append(f'<a href="{pg["html"]}"{cur}>{both(pg["_titles"])}</a>')
    here = _chapter_of(p)
    rows += [f'<div class="rn-grp{" here" if ch == here else ""}">{"".join(links)}</div>' for ch, links in groups]
    prev_ = (f'<a class="rn-step" href="{pages[i-1]["html"]}" title="{html.escape(_WORDS[langs[0]]["prev"])}">←</a>'
             if i else '<span class="rn-step off">←</span>')
    next_ = (f'<a class="rn-step" href="{pages[i+1]["html"]}" title="{html.escape(_WORDS[langs[0]]["next"])}">→</a>'
             if i + 1 < len(pages) else '<span class="rn-step off">→</span>')
    return (f'<nav class="rnav"><a class="rn-portal" href="/">{word("portal")}</a>'
            f'<div class="rn-menu"><button type="button" class="rn-btn" aria-expanded="false" aria-haspopup="true">'
            f'<span class="rn-ic">☰</span><span class="rn-cur">{both(p["_titles"])}</span><span class="rn-car">▴</span></button>'
            f'<div class="rn-panel" hidden>{"".join(rows)}</div></div>'
            f'<span class="rn-sp"></span>{prev_}{next_}</nav>\n<script>{READ_NAV_JS}</script>')


def build_page(src, meta, i, out_dir, mermaid_mode):
    pages, langs = meta["pages"], meta["_langs"]
    p = pages[i]
    text, n = _page_text(meta, i, langs[0], p["_path"])
    kw = {}
    if len(langs) == 2 and p["_alt_path"]:
        alt_text, _n = _page_text(meta, i, langs[1], p["_alt_path"])
        kw = {"lang": langs[0], "alt_lang": langs[1], "alt_md": alt_text}
    set_lang(meta)
    # ナビ帯は読み物専用の作り(BL-253)。問題ページの横並びの帯(render の nav)は使わない
    out = RH.render(text, title=p["title"], extra_css=READING_CSS,
                    body_class="reading", allow_html=True,
                    mermaid_mode=("cdn" if mermaid_mode == "local" else mermaid_mode), **kw)
    if mermaid_mode == "local":
        out = out.replace(RH.MERMAID_CDN, "mermaid.min.js")
    out, p["_sections"] = mark_sections(out)
    p["_tries"] = extract_tries(out)
    out = out.replace("</body>", f"{reading_nav(meta, i)}\n<script>{READ_JS}</script>\n<script>{CFG_JS}</script>\n</body>", 1)
    out = _finish_lang(lazy_images(wrap_tables(termify(out))))
    dst = os.path.join(out_dir, p["html"])
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(out)
    return dst, n


def _unit_head(label):
    """章の名前 → (バッジ, 名前)。先頭の語に数字があればバッジにする(「M4 IS-IS」→ M4 / IS-IS、「第1章 OSPF」→ 第1章 / OSPF)。"""
    m = re.match(r"(\S*\d\S*)\s+(.+)$", label or "")
    return (m.group(1), m.group(2)) if m else ("", label or "")


def _short_title(title, code):
    """ページ題名から単元の接頭辞を落とす(「M4 — IS-IS をさらに深く」→「IS-IS をさらに深く」)。M1 が M10 を食わないように語の切れ目を見る。"""
    if not code:
        return title
    t = re.sub(rf"^{re.escape(code)}(?!\w)\s*[—–:：\-]?\s*", "", title)
    return t or title


def _page_kind(p):
    if p.get("kind") in ("read", "practice", "appendix"):
        return p["kind"]
    f = p["file"].lower()
    return "practice" if "practice" in f else "appendix" if "appendix" in f else "read"


def _index_units(meta):
    """目次の並び= [(部の名前 {言語: 文字}, [(章番号, [ページ])])]。部が無ければ名前なしの 1 つ。"""
    units = {}
    for p in meta["pages"]:
        units.setdefault(_chapter_of(p), []).append(p)
    groups, seen = [], set()
    for part in meta.get("parts") or []:
        keys = [str(k).zfill(2) for k in part.get("chapters") or []]
        us = [(k, units[k]) for k in keys if k in units and k not in seen]
        seen.update(k for k, _ in us)
        if us:
            groups.append((part.get("title") or "", us))
    rest = [(k, ps) for k, ps in units.items() if k not in seen]
    if rest:
        if meta.get("parts"):
            print(f"[reading] 警告: parts: のどの部にも入っていない単元 {[k for k, _ in rest]}(目次の末尾に出す)", file=sys.stderr)
        groups.append(("", rest))
    return groups


def _index_cards(meta, groups, lang):
    """単元ごとのカードを部ごとの格子に並べた HTML(空行を入れない= Markdown の生 HTML ブロックとして丸ごと通す)。"""
    chapters = meta.get("chapters") or {}
    out = ['<div class="cidx">']
    for part, units in groups:
        heads = [_unit_head(_pick(chapters.get(k), lang, k)) for k, _ in units]
        if part:
            codes = [c for c, _ in heads if c]
            span = (codes[0] if len(codes) == 1 else f"{codes[0]}–{codes[-1]}") if codes else ""
            out.append(f'<h2 class="ph"><span>{html.escape(_pick(part, lang))}</span>'
                       + (f'<span class="pr">{html.escape(span)}</span>' if span else "") + "</h2>")
        out.append('<div class="ugrid">')
        for (k, pages), (code, name) in zip(units, heads):
            out.append('<section class="unit"><h3 class="uh">'
                       + (f'<span class="ucode">{html.escape(code)}</span>' if code else "")
                       + f'<span class="uname">{html.escape(name)}</span></h3>')
            for p in pages:
                lab = f'<span class="ulab">{html.escape(p["lab"])}</span>' if p.get("lab") else ""
                t = _short_title(p["_titles"][lang], code)
                if t.casefold() == name.casefold():      # 見出しと同じ題名は繰り返さず、ページの種類で呼ぶ
                    t = _w("reading")
                out.append(f'<a class="ur k-{_page_kind(p)}" href="{p["html"]}">'
                           f'<span class="ut">{html.escape(t)}</span>{lab}</a>')
            out.append("</section>")
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)


def build_index(meta, out_dir):
    langs = meta["_langs"]
    groups = _index_units(meta) if meta.get("toc") == "units" and meta.get("chapters") else None

    def body(lang):
        set_lang(meta, lang)
        if groups:
            toc = _index_cards(meta, groups, lang)
        else:
            toc = '<ul class="toc">\n' + "\n".join(
                f'<li><a href="{p["html"]}">{html.escape(p["_titles"][lang])}</a></li>'
                for p in meta["pages"]) + "\n</ul>"
        sub = _pick(meta.get("subtitle"), lang)
        return (f'<p class="portal"><a href="/">{_w("portal")}</a></p>\n\n# {_pick(meta["title"], lang)}\n\n'
                + (f'<p class="lead">{html.escape(sub)}</p>\n\n' if sub else "")
                + toc + "\n")

    kw = {"lang": langs[0], "alt_lang": langs[1], "alt_md": body(langs[1])} if len(langs) == 2 else {}
    first = body(langs[0])
    set_lang(meta)
    out = RH.render(first, title=_pick(meta["title"], langs[0]), extra_css=READING_CSS + INDEX_CSS,
                    body_class="reading rindex", allow_html=True, mermaid_mode="none", **kw)
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
        langs = meta["_langs"]
        odd = [k for k, v in meta["pages"][i].get("_sections", {}).items() if set(v) != set(langs)]
        if len(langs) == 2 and odd:
            print(f"[reading] 警告: {meta['pages'][i]['html']} の 2 版で見出しの並びがそろっていない(節 {odd})", file=sys.stderr)
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
                   "pages": len(meta["pages"]),
                   # 節の一覧(BL-252)= {ページの html: {s2: {en: 見出し, ja: 見出し}}}。ワークスペースの Reading リンクの表示名
                   "sections": {pg["html"]: pg.get("_sections", {}) for pg in meta["pages"]},
                   "page_titles": {pg["html"]: pg["_titles"] for pg in meta["pages"]},
                   # 「やってみる」= {ページの html: {節: [{en: HTML, ja: HTML}]}}。ワークスペースの課題カードの小窓
                   "tries": {pg["html"]: pg["_tries"] for pg in meta["pages"] if pg.get("_tries")}},
                  fh, ensure_ascii=False, indent=1)
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
        text = expand_blocks(text)
        # ワークスペース・他ページの節へのリンク(BL-252)は配信している時だけのもの。持ち出しの 1 枚には行き先が無い
        text = re.sub(r'(?m)^<p class="tolab">.*</p>\n?', "", text)
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
    out = out.replace("<body", '<body id="top"', 1).replace("</body>", f"<script>{CFG_JS}</script>\n</body>", 1)
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
