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
  :::walk ... :::               … 1 ホップずつ追う図（設定の塊がパケットにどの順で効くか・下記。番号の所で設定例の行が出る）
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
      - [XE2, XE3, "疑似回線 210\n送らない"]   # "\n"(YAML のダブルクォート内)で改行。長いラベル向け
    frames:
      - {label: "VTP ドメイン TST", nodes: [SW1, SW2, SW3]}
    :::

:::walk — 入り組んだ設定(塊が別々の場所にあり、1 つのパケットに順に効く)を、パケットの道筋の上で見せる（YAML）。
  2026-11-08 ユーザ指示「入り組んだコンフィグは図で解説してほしい」。上から下へ 1 行ずつ積む:

    :::walk
    legend: 線の上のパケットは左が外側。橙は書き換わった印。     # 図の上の凡例(任意)
    rows:
      - {node: CE2, kind: host, say: ["~音声に EF を付けて送る"]}   # 機器。say= 右に書く行(1〜2 行)
      - {wire: "[[=18  tc 5]] [[IP  EF]] _外側= XR01 行き"}        # 線の上のパケット(1 行の文字列か行の並び)
      - panel: XR01                                               # 機器を広げた枠。中に設定の塊を効く順に
        sub: 出口の PE
        items:
          - {ref: 1, to: P1, code: "mpls ldp … explicit-null", say: ["P1 へ…と広告する"]}   # to= 制御の塊。破線で機器へ
          - ref: 2                                                # 番号つきの塊(設定例の注記の ② と結ぶ)
            head: "**Gi0/0/0/0 の入力** `service-policy input CORE-IN`"
            say: ["_クラスを上から調べる"]
            match:                                                # [行, 当たったか, 結果]
              - ["class EXP5  match mpls experimental topmost 5", false, 当たらない]
              - ["class EXP0  match mpls experimental topmost 0", true, "当たる → `set qos-group 7`"]
            then: ["→ 当たった後に続く動作の行(任意)"]
          - {say: ["~ここは QoS ではない", "[[IP  EF]] [[~qos-group 7]]"]}   # 番号なし= 破線の段
      - {aside: "①を書かないと", say: ["~P1 が外す → [[=24007  tc 5]] ~→ ②は 5 を読む"]}  # 図の下の別の場合
    :::

  行の中の書き方: [[小箱]](先頭 = ラベル・! 書き換わった印(橙)・~ 装置の中だけの印(紫の破線)・無し= IP)。
  文の頭の ~ 薄く・_ 小さく薄く・^ 橙の太字・+ 緑の太字。`コード`・**太字**。①〜⑨ は青い番号。
  ★番号(ref と文中の①〜⑨)は、図の後ろの :::config(同じ章= 次の h2 か次の :::walk まで。設定例が節をまたいでよい)の、
    注記の頭に同じ番号を付けた行と結ぶ。同じ番号の塊を図に 2 回置いてもよい(親のポリシーの入口と出口など)。
    カーソルを置く(スマホは押す)と、その行と親の階層の行(塊の頭に付ければ塊ごと)を小窓に出し、設定例の行にも色を付ける。

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

用語集(BL-260) — 辞書 <repo>/glossary/*.yml(＋本ごとの <src>/glossary.yml)の語を本文から拾い、カーソル(スマホはタップ)で
  説明を出す。本文に目印は付けない。出力先に glossary.html(逆引き付きの一覧)も作り、目次とナビ帯から飛べる。束ね版は 1 枚の末尾に付ける。
  辞書の書式と拾う規則は topologies/glossary.py の docstring が正典。`glossary: false`(book.yml)でその本だけ切る。

使い方:
  python3 topologies/gen_reading.py build --src private/reading/<key>
  python3 topologies/gen_reading.py glossary [--src <本> [--unknown]]   … 辞書の検査(本を渡すと本文に出る語・辞書に無い略語も)
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
import glossary as GL  # noqa: E402

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
/*  ワークスペースの Reading の枠の中では大きくしない。枠の外側(ワークスペース)が同じ条件で枠ごと拡大するので、
    ここでも上げると二重になる(2026-11-01)。class は READ_JS が枠の中の時に付ける */
html.framed{ font-size:100%; }
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

/* ---- 1 ホップずつ追う図(:::walk)と、番号の所に出す設定の小窓(WALK_JS) ---- */
svg.wk .wk-ref{ cursor:pointer; }
svg.wk g.wk-ref:hover .wk-box, svg.wk g.wk-ref.on .wk-box{ stroke:#3f7fbf; stroke-width:2.2; }
svg.wk tspan.wk-ref:hover, svg.wk tspan.wk-ref.on{ text-decoration:underline; }
#wkpop{ position:fixed; z-index:90; box-sizing:border-box; width:max-content; max-width:min(40rem, calc(100vw - 16px));
  background:#fff; color:#111; border:1px solid #c3c9d2; border-radius:7px; box-shadow:0 6px 24px rgba(20,30,45,.18);
  padding:.5rem .7rem .6rem; font-size:.84rem; line-height:1.6; letter-spacing:0; text-align:left;
  max-height:calc(100vh - 16px); overflow:auto; }
#wkpop[hidden]{ display:none; }
#wkpop .wp-h{ display:flex; gap:.45rem; align-items:baseline; margin:0 0 .35rem; }
#wkpop .wp-n{ color:#3f7fbf; font-weight:700; font-size:1rem; }
#wkpop .wp-t{ color:#5b6676; font-size:.8rem; }
#wkpop pre{ margin:0; padding:.45rem .65rem; background:#fbfcfd; border:1px solid #dfe4ea; border-radius:5px;
  font-family:"Cascadia Mono",Consolas,"DejaVu Sans Mono",monospace; font-size:.78rem; line-height:1.55;
  white-space:pre; overflow-x:auto; color:#14202e; }
#wkpop pre .wp-sep{ color:#9aa3ad; }
.cfg .cn .cref{ color:#3f7fbf; font-weight:700; margin-right:.15em; }
.cfg .cr.wk-hl > .cc, .cfg .cr.wk-hl > .cn{ background:#fff3c4; }

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

/* ---- 図の拡大表示(FIG_JS)。図をクリックすると画面いっぱいに出す ---- */
.topo svg, pre.mermaid svg, body.reading main img{ cursor:zoom-in; }
#figbig{ position:fixed; inset:0; z-index:80; background:rgba(20,24,30,.55); display:flex; padding:.9rem;
  box-sizing:border-box; }
#figbig[hidden]{ display:none; }
#figbig .fb-box{ flex:1; min-width:0; min-height:0; display:flex; flex-direction:column; background:#fff;
  border-radius:6px; box-shadow:0 10px 36px rgba(0,0,0,.35); overflow:hidden; }
#figbig .fb-bar{ flex:none; display:flex; align-items:center; gap:.5rem; padding:.4rem .65rem; background:#f3f4f6;
  border-bottom:1px solid #c9ced6; font-size:.82rem; line-height:1.4; letter-spacing:0; }
#figbig .fb-tip{ flex:1; min-width:0; color:#5b6676; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
#figbig .fb-bar button{ font:inherit; min-width:2.2em; border:1px solid #c9ced6; border-radius:4px; background:#fff;
  padding:.1rem .5rem; cursor:pointer; color:#111; }
#figbig .fb-bar button:hover{ background:#e9ecf0; }
#figbig .fb-view{ flex:1; min-height:0; position:relative; margin:0; overflow:hidden; cursor:grab; touch-action:none;
  outline:none; text-align:left; }
#figbig .fb-view.drag{ cursor:grabbing; }
#figbig .fb-view svg{ position:absolute; inset:0; width:100%; height:100%; max-width:none; }
"""

# 目次(index.html)だけに足す。単元ごとのカードを部ごとの格子に並べる
#   (2026-10-27 ユーザ要望「順番に羅列しているだけで分かりづらい・お目当ての単元に行きやすく」)。
#   行の左の色= ページの種類(青= 読み物・緑= 実践・灰= 付録)。
INDEX_CSS = """
body.reading.rindex main{ max-width:64rem; }
body.reading .glink{ margin:.6rem 0 0; font-size:.95rem; }
body.reading .glink span{ color:#7a8594; font-size:.86rem; }
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
        rows = str(lab).split("\n")    # "\n" で改行した長いラベルは複数行で描く
        w = max(_tw(r) for r in rows) * 7.4 + 10
        h = 18 * len(rows)
        top = y - h / 2
        parts.append(f'<rect class="tlb" x="{x-w/2:.0f}" y="{top:.0f}" '
                     f'width="{w:.0f}" height="{h}" rx="3"/>')
        ext.append((x - w / 2, top, x + w / 2, top + h))
        for i, r in enumerate(rows):
            parts.append(f'<text class="tlt" x="{x:.0f}" y="{top + 13 + 18 * i:.0f}">'
                         f"{html.escape(r)}</text>")
        # ラベルが機器の箱にかかると、箱が前面なので文字が切れて見える(2026-11-01 ユーザ指摘)。
        # 描く時に気づけるよう警告する。直し方= 箱の間隔を広げるか、"\n" で改行する
        for name, b in boxes.items():
            if (min(x + w / 2, b["x"] + b["w"] / 2) - max(x - w / 2, b["x"] - b["w"] / 2) > 0
                    and min(top + h, b["y"] + b["h"] / 2) - max(top, b["y"] - b["h"] / 2) > 0):
                print(f"[topo] warning: link label {str(lab)!r} is hidden under node {name}"
                      " (widen the gap or break the label with \\n)", file=sys.stderr)

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
# 1 ホップずつ追う図(:::walk → SVG)。書き方は冒頭の docstring。
#   2026-11-08 ユーザ指示「入り組んだコンフィグは図で解説してほしい」「図中の箇所に該当する config がホバーで出ると良い」。
#   縦に積む(本文の幅 44rem に 1 対 1 で収まる幅 700)。文字の幅は見積もり(全角 1em・半角 0.56em)で並べるので、
#   1 行の中で文の後ろに小箱を置く時は余白を多めに取る。図の中の番号と設定例の行の結び付けは WALK_JS が行う。
# --------------------------------------------------------------------------
WALK_RE = re.compile(r"^:::walk[ \t]*\n(.*?)^:::[ \t]*$", re.S | re.M)
WK_GLYPHS = "①②③④⑤⑥⑦⑧⑨"
WK_W, WK_SX, WK_RX = 700, 60, 140          # 図の幅・機器の列の中心・右の列の左端
WK_SANS = '"Segoe UI",system-ui,"Hiragino Sans","Noto Sans CJK JP",sans-serif'
WK_MONO = '"Cascadia Mono",Consolas,"DejaVu Sans Mono",monospace'
WK_INK, WK_MUTED, WK_BLUE, WK_HOT = "#1b2430", "#6b7685", "#3f7fbf", "#8a4b0f"
WK_CHIP = {"": ("#ffffff", "#8f99a6", WK_INK, None), "=": ("#e8eef6", "#8da2bd", WK_INK, None),
           "!": ("#fff1e0", "#d9822b", WK_HOT, None), "~": ("#f3eefb", "#8a6cc2", "#4b3480", "4 3")}
WK_TONE = {"~": {"fill": WK_MUTED}, "_": {"fill": WK_MUTED, "size": 11.5}, "^": {"fill": WK_HOT, "weight": 600},
           "+": {"fill": "#2f7d3b", "weight": 600}, "-": {"fill": "#9aa3ad"}}
WK_CHIP_RE = re.compile(r"\[\[([=!~]?)(.*?)\]\]")
WK_INLINE_RE = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|[①-⑨])")


def _wk_w(s, size, mono=False):
    """文字列の幅の見積もり(px)。"""
    import unicodedata
    w = 0.0
    for c in s:
        ea = unicodedata.east_asian_width(c)
        if ea in ("W", "F"):
            w += size
        elif ea == "A" and not c.isascii():     # →・✓・…など。フォントで幅が変わるので中間を取る
            w += size * 0.85
        elif c == " " and not mono:
            w += size * 0.3
        else:
            w += size * (0.6 if mono else 0.56)
    return w


def _wk_text(x, y, s, size=13, base=None, anchor="start"):
    """1 つの <text> に、`コード`・**太字**・①〜⑨ を tspan で入れる。(svg, 見積もった幅)。"""
    base = dict({"fill": WK_INK, "weight": 400}, **(base or {}))
    spans, w = [], 0.0
    for piece in WK_INLINE_RE.split(s):
        if not piece:
            continue
        a, mono, cls = dict(base), False, ""
        if piece.startswith("`") and piece.endswith("`") and len(piece) > 1:
            piece, mono = piece[1:-1], True
        elif piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            piece, a["weight"] = piece[2:-2], 600
        elif piece in WK_GLYPHS:
            a, cls = {"fill": WK_BLUE, "weight": 700}, f' class="wk-ref" data-ref="{WK_GLYPHS.index(piece) + 1}"'
        spans.append(f'<tspan{cls} font-family=\'{WK_MONO if mono else WK_SANS}\' fill="{a["fill"]}" '
                     f'font-weight="{a["weight"]}">{html.escape(piece)}</tspan>')
        w += _wk_w(piece, size, mono)
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" xml:space="preserve">'
            + "".join(spans) + "</text>"), w


def _wk_chip(x, cy, kind, s, size=12):
    fill, stroke, ink, dash = WK_CHIP[kind]
    w = _wk_w(s, size, True) + 16
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{cy - 11:.1f}" width="{w:.1f}" height="22" rx="3" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="1.2"{d}/><text x="{x + w / 2:.1f}" y="{cy + 4.5:.1f}" font-size="{size}" text-anchor="middle" '
            f'font-family=\'{WK_MONO}\' fill="{ink}" xml:space="preserve">{html.escape(s)}</text>'), w


def _wk_line(x, y, line, size=13, base=None):
    """1 行(小箱と文の混在)を描く。y は文字のベースライン。(svg の並び, 右端)。"""
    parts, pos = [], 0
    for m in list(WK_CHIP_RE.finditer(line)) + [None]:
        seg = line[pos:m.start()] if m else line[pos:]
        if seg.strip():
            lead = len(seg) - len(seg.lstrip(" "))
            x += lead * size * 0.3
            seg = seg.strip(" ")
            b, sz = dict(base or {}), size
            if seg[0] in WK_TONE:
                tone = WK_TONE[seg[0]]
                seg, sz = seg[1:].lstrip(" "), tone.get("size", size)
                b.update({k: v for k, v in tone.items() if k != "size"})
            svg, w = _wk_text(x, y, seg, sz, b)
            parts.append(svg)
            x += w * 1.08 + 8               # 後ろに小箱が来ても重ならないよう、見積もりより広めに空ける
        elif seg:
            x += 2
        if m:
            svg, w = _wk_chip(x, y - 4.5, m.group(1), m.group(2), size=min(12, size))
            parts.append(svg)
            x += w + 4
            pos = m.end()
    return parts, x


def _wk_lines(v):
    return [] if v is None else ([str(v)] if not isinstance(v, list) else [str(s) for s in v])


def _wk_badge(cx, cy, n, r=10):
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{WK_BLUE}"/>'
            f'<text x="{cx:.1f}" y="{cy + r * 0.45:.1f}" font-size="{r * 1.25:.1f}" font-family=\'{WK_SANS}\' '
            f'fill="#fff" font-weight="700" text-anchor="middle">{n}</text>')


def _wk_rect(x, y, w, h, fill, stroke, rx=6, sw=1.2, dash=None, cls=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    c = f' class="{cls}"' if cls else ""
    return (f'<rect{c} x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def _wk_arrow(x, y1, y2, color="#44506080", sw=1.7):
    k = 1 if y2 > y1 else -1
    return (f'<line x1="{x}" y1="{y1:.1f}" x2="{x}" y2="{y2:.1f}" stroke="{color}" stroke-width="{sw}"/>'
            f'<path d="M{x - 5},{y2 - 8 * k:.1f} L{x},{y2:.1f} L{x + 5},{y2 - 8 * k:.1f}" fill="none" '
            f'stroke="{color}" stroke-width="{sw}"/>')


def render_walk(src_yaml):
    import yaml
    spec = yaml.safe_load(src_yaml) or {}
    W, SX, RX = WK_W, WK_SX, WK_RX
    out, nodes, arrows = [], {}, []
    y = 12
    if spec.get("legend"):
        out += _wk_line(RX, 18, "_" + str(spec["legend"]))[0]
        y = 30
    prev = None                                  # 道筋の線の始点(直前の機器・枠の下端)

    def flow_to(top):
        if prev is not None:
            out.append(_wk_arrow(SX, prev, top))

    for row in spec.get("rows") or []:
        if "node" in row:                        # 機器
            host = row.get("kind") == "host"
            say = _wk_lines(row.get("say"))
            lh = [26 if WK_CHIP_RE.search(ln) else 18 for ln in say]
            h = max(34, sum(lh) + 4)
            flow_to(y)
            by = y + (h - 34) / 2
            out.append(_wk_rect(SX - 40, by, 80, 34, "#ffffff" if host else "#eef1f5",
                                "#5a6472" if host else "#2f3b4a", rx=16 if host else 5, sw=1.6))
            out.append(_wk_text(SX, by + 22, str(row["node"]), 14, {"weight": 600}, anchor="middle")[0])
            nodes[str(row["node"])] = by + 17
            yy = y + h / 2 - sum(lh) / 2
            for ln, l in zip(say, lh):
                out += _wk_line(RX, yy + l / 2 + 4.5, ln)[0]
                yy += l
            y += h
            prev = y
        elif "wire" in row:                      # 線の上のパケット
            lines = _wk_lines(row["wire"])
            for i, ln in enumerate(lines):
                out += _wk_line(RX, y + 24.5 + 26 * i, ln)[0]
            y += 40 + 26 * (len(lines) - 1)
        elif "panel" in row:                     # 機器を広げた枠
            top = y
            flow_to(top)
            at = len(out)
            out.append("")
            out.append(_wk_text(34, top + 24, str(row["panel"]), 14, {"weight": 600})[0])
            if row.get("sub"):
                out.append(_wk_text(34, top + 42, str(row["sub"]), 11.5, {"fill": WK_MUTED})[0])
            cy, last = top + 54, None
            items = row.get("items") or []
            for it in items:
                if it.get("to"):                 # 制御の塊(枠の見出しの右・破線で機器へ)
                    ux, uy = 118, top + 10
                    say = _wk_lines(it.get("say"))
                    uh = 30 + 19 * len(say)
                    g = [_wk_rect(ux, uy, W - 26 - ux, uh, "#f2f7fc", WK_BLUE, dash="5 4", cls="wk-box")]
                    if it.get("ref"):
                        g.append(_wk_badge(ux + 18, uy + 15, it["ref"]))
                    g += _wk_line(ux + 36, uy + 20, "`" + str(it.get("code", "")) + "`", 12)[0] if it.get("code") else []
                    for i, ln in enumerate(say):
                        g += _wk_line(ux + 36, uy + 39 + 19 * i, ln, 11.5, {"fill": WK_BLUE})[0]
                    out.append(f'<g class="wk-ref" data-ref="{it["ref"]}">' + "".join(g) + "</g>" if it.get("ref")
                               else "".join(g))
                    arrows.append((ux, uy + 24, str(it["to"])))
                    cy = max(cy, uy + uh + 14)
                    continue
                if last is not None:
                    out.append(_wk_arrow(SX, last, cy + 26))
                    cy += 26
                g = []
                if it.get("ref"):                # 番号つきの塊
                    say, match, then = _wk_lines(it.get("say")), it.get("match") or [], _wk_lines(it.get("then"))
                    gap = lambda ln: 26 if WK_CHIP_RE.search(ln) else 18
                    h = 30 + sum(gap(ln) for ln in say + then) + 20 * len(match) + (6 if match else 0)
                    h += 8 if any(WK_CHIP_RE.search(ln) for ln in say + then) else 0   # 小箱の行の下に余白
                    h += 4 if then and match else 0
                    g.append(_wk_rect(36, cy, W - 62, h, "#ffffff", "#c9d2dd", cls="wk-box"))
                    g.append(_wk_badge(54, cy + 18, it["ref"]))
                    g += _wk_line(72, cy + 23, str(it.get("head", "")))[0]
                    yy = cy + 23
                    for ln in say:
                        yy += gap(ln)
                        g += _wk_line(72, yy, ln, 11.5, {"fill": WK_MUTED})[0]
                    rx_ = max(300, 72 + max([_wk_w(str(m[0]), 12, True) for m in match] or [0]) + 24)
                    for code, hit, res in match:
                        yy += 20
                        if hit:
                            g.append(_wk_rect(66, yy - 14, W - 102, 20, "#eaf5ec", "#eaf5ec", rx=3, sw=0))
                        g.append(_wk_text(72, yy, "`" + str(code) + "`", 12,
                                          None if hit else {"fill": "#9aa3ad"})[0])
                        g += _wk_line(rx_, yy, ("+✓ " if hit else "-✗ ") + str(res), 12)[0]
                    for ln in then:
                        yy += gap(ln) + (4 if ln is then[0] and match else 0)
                        g += _wk_line(72, yy, ln, 12)[0]
                    out.append(f'<g class="wk-ref" data-ref="{it["ref"]}">' + "".join(g) + "</g>")
                else:                            # 番号なしの段(QoS ではない処理など)
                    say = _wk_lines(it.get("say"))
                    lh = [26 if WK_CHIP_RE.search(ln) or i else 22 for i, ln in enumerate(say)]
                    h = 14 + sum(lh)
                    out.append(_wk_rect(36, cy, W - 62, h, "#fbfbfb", "#b8c0ca", dash="5 4"))
                    yy = cy - 1
                    for ln, l in zip(say, lh):
                        yy += l
                        out += _wk_line(54, yy, ln, 12.5)[0]
                last = cy + h
                cy += h
            bot = (last if last is not None else cy) + 14
            out[at] = _wk_rect(20, top, W - 30, bot - top, "#f7f9fc", "#2f3b4a", rx=10, sw=1.6)
            y = bot
            prev = y
        elif "aside" in row:                     # 図の下の別の場合
            y += 22
            say = _wk_lines(row.get("say"))
            h = 42 + 26 * len(say)
            out.append(_wk_rect(20, y, W - 30, h, "#f4f4f2", "#c9c4b4", rx=8, dash="6 4"))
            out += _wk_line(34, y + 23, str(row["aside"]), 12.5, {"fill": "#5f5a4a", "weight": 600})[0]
            for i, ln in enumerate(say):
                out += _wk_line(34, y + 53 + 26 * i, ln, 12)[0]
            y += h
            prev = None
        if row.get("gap"):
            y += float(row["gap"])
    ax = 112
    for ux, uy, to in arrows:                    # 制御の塊 → 機器(破線)
        ny = nodes.get(to)
        if ny is None:
            print(f"[walk] warning: unknown node {to!r} in `to:`", file=sys.stderr)
            continue
        out.append(f'<path d="M{ux},{uy:.1f} L{ax},{uy:.1f} L{ax},{ny:.1f} L{SX + 44},{ny:.1f}" fill="none" '
                   f'stroke="{WK_BLUE}" stroke-width="1.4" stroke-dasharray="5 4"/>'
                   f'<path d="M{SX + 52},{ny - 5:.1f} L{SX + 43},{ny:.1f} L{SX + 52},{ny + 5:.1f}" fill="none" '
                   f'stroke="{WK_BLUE}" stroke-width="1.4"/>')
    H = y + 10
    return (f'<div class="topo walk"><svg class="wk" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" '
            f'width="{W}" style="width:{W / 16:.2f}rem" role="img">' + "".join(out) + "</svg></div>")


def expand_walk(md_text):
    return WALK_RE.sub(lambda m: "\n" + render_walk(m.group(1)) + "\n", md_text)


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


def _cfg_refs(rows):
    """:::walk の番号との結び付け。注記の頭に①〜⑨を付けた行と、その親の階層の行・子の行(字下げで判断)に番号を持たせる。"""
    ind = [len(c) - len(c.lstrip(" ")) for c, _n in rows]
    real = [bool(c.strip()) and c.strip() != "!" for c, _n in rows]
    refs = [set() for _ in rows]
    for i, (code, note) in enumerate(rows):
        if not note or note[0] not in WK_GLYPHS:
            continue
        n = WK_GLYPHS.index(note[0]) + 1
        refs[i].add(n)
        for j in range(i + 1, len(rows)):        # 子(字下げの深い行)。XR の RPL などの締め(end-policy・end-set)も塊に入れる
            if not rows[j][0].strip() or (ind[j] <= ind[i] and rows[j][0].strip()):
                if ind[j] == ind[i] and rows[j][0].strip().startswith("end-"):
                    refs[j].add(n)
                break
            refs[j].add(n)
        cur = ind[i]
        for j in range(i - 1, -1, -1):           # 親(字下げの浅い行をたどる)
            if cur == 0:
                break
            if real[j] and ind[j] < cur:
                refs[j].add(n)
                cur = ind[j]
    return refs


def render_config(fold, title, body):
    parsed = []
    for ln in body.rstrip("\n").split("\n"):
        m = CFG_NOTE_RE.search(ln)
        parsed.append((ln[:m.start()], m.group(1).strip()) if m else (ln, ""))
    rows = []
    for (code, note), refs in zip(parsed, _cfg_refs(parsed)):
        note_html = _cfg_inline(note)
        if note and note[0] in WK_GLYPHS:
            note_html = f'<span class="cref">{note[0]}</span>' + note_html[1:]
        ref = f' data-ref="{" ".join(str(n) for n in sorted(refs))}"' if refs else ""
        rows.append(f'<span class="cr"{ref}><code class="cc">{html.escape(code.rstrip()) or " "}</code>'
                    f'<span class="cn">{note_html}</span></span>')
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
    return expand_containers(expand_config(expand_walk(expand_topo(md_text))))


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
                 "config": "設定例", "copy": "コピー", "copied": "コピーしました", "open": "(クリックで開く)",
                 "glossary": "用語集"},
          "en": {"toc": "Contents", "back": "↑ Contents", "note": "Note", "sic": "Error in the source", "orig": "Original", "try": "Try it",
                 "portal": "‹ Portal", "prev": "Previous page", "next": "Next page", "reading": "Reading",
                 "config": "Configuration", "copy": "Copy", "copied": "Copied", "open": "(click to open)",
                 "glossary": "Glossary"}}


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
  if(framed) document.documentElement.classList.add('framed');   /* 枠の中では画面の倍率をワークスペースに任せる */
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

# 図の拡大表示(2026-11-01 ユーザ要望「規模が大きいと図が小さくて見づらい」)。ページと束ねた 1 枚の両方に入れる。
#   図(:::topo・Mermaid・本文の画像)をクリックすると写しを画面いっぱいに出す。拡大・移動は viewBox を書き換える
#   (画像は SVG の <image> に包んで同じ扱いにする)。ピンチ・Ctrl+ホイール・+/− で拡大縮小、ドラッグ・2 本指スクロールで移動、
#   Fit かダブルクリックで全体、Esc・✕・外側のクリックで閉じる。ワークスペースの結線図の拡大表示(lab_console)と同じ操作
FIG_JS = r"""
(function(){
  var NS = 'http://www.w3.org/2000/svg';
  var WORDS = {ja: {tip: 'ピンチか Ctrl+ホイールで拡大縮小 · ドラッグで移動', zout: '縮小', zin: '拡大', fit: '全体', close: '閉じる (Esc)'},
               en: {tip: 'Pinch or Ctrl+wheel to zoom · drag to move', zout: 'Zoom out', zin: 'Zoom in', fit: 'Fit', close: 'Close (Esc)'}};
  var o = null, tip, view, svg = null, vb = null, home = null, ptrs = {}, pinch = null, btns = {};
  function words(){
    var l = (document.body.dataset.lang || document.documentElement.lang || 'ja').slice(0, 2);
    return WORDS[l] || WORDS.en;
  }
  function set(v){ vb = v; svg.setAttribute('viewBox', v.map(function(n){ return n.toFixed(1); }).join(' ')); }
  function pan(dx, dy){                       /* 画面の px で動かす */
    var s = svg.getScreenCTM().a;
    set([vb[0] + dx / s, vb[1] + dy / s, vb[2], vb[3]]);
  }
  function zoom(f, cx, cy){                   /* f 倍に拡大。(cx, cy) の点は動かさない(省けば中央) */
    if(cx === undefined){ var r = view.getBoundingClientRect(); cx = r.left + r.width / 2; cy = r.top + r.height / 2; }
    var w = Math.min(home[2] * 1.5, Math.max(home[2] / 12, vb[2] / f)), k = w / vb[2];
    var pt = svg.createSVGPoint(); pt.x = cx; pt.y = cy;
    var p = pt.matrixTransform(svg.getScreenCTM().inverse());
    set([p.x - (p.x - vb[0]) * k, p.y - (p.y - vb[1]) * k, w, vb[3] * k]);
  }
  function close(){
    if(!o || o.hidden) return;
    o.hidden = true; ptrs = {}; pinch = null;
    document.documentElement.style.overflow = '';
  }
  function build(){
    o = document.createElement('div'); o.id = 'figbig'; o.hidden = true;
    var box = document.createElement('div'), bar = document.createElement('div');
    box.className = 'fb-box'; bar.className = 'fb-bar';
    tip = document.createElement('span'); tip.className = 'fb-tip'; bar.appendChild(tip);
    [['zout', '−', function(){ zoom(1 / 1.25); }], ['zin', '+', function(){ zoom(1.25); }],
     ['fit', '', function(){ set(home.slice()); }], ['close', '✕', close]].forEach(function(d){
      var b = document.createElement('button'); b.type = 'button'; b.dataset.label = d[1];
      b.addEventListener('click', d[2]); bar.appendChild(b); btns[d[0]] = b;
    });
    view = document.createElement('div'); view.tabIndex = -1;
    box.appendChild(bar); box.appendChild(view); o.appendChild(box);
    o.addEventListener('click', function(e){ if(e.target === o) close(); });
    o.addEventListener('keydown', function(e){
      if(e.key === 'Escape') close();
      else if(e.key === '+' || e.key === '=') zoom(1.25);
      else if(e.key === '-') zoom(1 / 1.25);
      else if(e.key === '0') set(home.slice());
      else return;
      e.preventDefault();
    });
    view.addEventListener('wheel', function(e){
      e.preventDefault();
      if(e.ctrlKey) zoom(Math.exp(-Math.max(-50, Math.min(50, e.deltaY)) * 0.01), e.clientX, e.clientY);
      else pan(e.deltaX, e.deltaY);
    }, {passive: false});
    /* 指 1 本(またはマウス)= 移動、指 2 本= ピンチで拡大縮小 */
    view.addEventListener('pointerdown', function(e){
      if(e.pointerType === 'mouse' && e.button !== 0) return;
      ptrs[e.pointerId] = {x: e.clientX, y: e.clientY};
      try{ view.setPointerCapture(e.pointerId); }catch(_e){}
      var ids = Object.keys(ptrs);
      if(ids.length === 2){ var a = ptrs[ids[0]], b = ptrs[ids[1]]; pinch = Math.hypot(a.x - b.x, a.y - b.y); }
    });
    view.addEventListener('pointermove', function(e){
      var prev = ptrs[e.pointerId];
      if(!prev) return;
      ptrs[e.pointerId] = {x: e.clientX, y: e.clientY};
      var ids = Object.keys(ptrs);
      if(ids.length >= 2){
        var a = ptrs[ids[0]], b = ptrs[ids[1]], d = Math.hypot(a.x - b.x, a.y - b.y);
        if(pinch) zoom(d / pinch, (a.x + b.x) / 2, (a.y + b.y) / 2);
        pinch = d; return;
      }
      view.classList.add('drag');
      pan(prev.x - e.clientX, prev.y - e.clientY);
    });
    function up(e){
      delete ptrs[e.pointerId];
      var n = Object.keys(ptrs).length;
      if(n < 2) pinch = null;
      if(!n) view.classList.remove('drag');
    }
    view.addEventListener('pointerup', up); view.addEventListener('pointercancel', up);
    view.addEventListener('dblclick', function(){ set(home.slice()); });
    document.body.appendChild(o);
  }
  function open(src){
    var s;
    if(src.tagName.toLowerCase() === 'img'){  /* 画像は SVG の <image> に包む */
      var w = src.naturalWidth || src.width, h = src.naturalHeight || src.height;
      if(!w || !h) return;
      s = document.createElementNS(NS, 'svg'); s.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
      var im = document.createElementNS(NS, 'image');
      im.setAttribute('href', src.currentSrc || src.src); im.setAttribute('width', w); im.setAttribute('height', h);
      s.appendChild(im);
    } else {
      s = src.cloneNode(true);
      ['style', 'width', 'height'].forEach(function(a){ s.removeAttribute(a); });
      if(!s.getAttribute('viewBox')){ var bb = src.getBBox(); s.setAttribute('viewBox', [bb.x, bb.y, bb.width, bb.height].join(' ')); }
    }
    if(!o) build();
    var t = words();
    tip.textContent = t.tip;
    ['zout', 'zin', 'fit', 'close'].forEach(function(k){
      btns[k].textContent = btns[k].dataset.label || t[k]; btns[k].title = t[k];
    });
    view.className = 'fb-view' + (src.closest('.topo') ? ' topo' : '');   /* :::topo の線や箱の色は .topo の下で効く */
    while(view.firstChild) view.removeChild(view.firstChild);
    view.appendChild(s); svg = s;
    home = s.getAttribute('viewBox').trim().split(/[\s,]+/).map(Number);
    set(home.slice());
    o.hidden = false; document.documentElement.style.overflow = 'hidden'; view.focus();
  }
  document.addEventListener('click', function(e){
    if(e.button !== 0 || e.defaultPrevented) return;
    var t = e.target;
    if(!t.closest || t.closest('#figbig') || t.closest('a') || t.closest('.wk-ref')) return;   /* 図の番号は設定の小窓(WALK_JS) */
    var fig = t.closest('.topo svg') || t.closest('pre.mermaid svg') || (t.tagName === 'IMG' && t.closest('main') ? t : null);
    if(fig) open(fig);
  });
})();
"""


# :::walk の番号 → 設定例の行(2026-11-08 ユーザ要望「図中の箇所に該当する config がホバーで(辞書のように)出ると良い」)。
#   図と設定例の結び付け= 図の後ろ・同じ章(次の h2 か次の図)までの設定例(2 言語の版はそれぞれの中で結ぶ)。
#   出し方は用語集(GLOSS_JS)にそろえる: カーソルを 0.3 秒置くと出す・押す(スマホはタップ)と固定・外側を押すか Esc で閉じる。
#   拡大表示(FIG_JS)の中の図でも出す(写しの svg も data-walk を持つ)。押した所は pointerdown で覚える
#   (拡大表示は移動のためにポインタを捕まえるので、click の宛先が図の部品にならない)。
WALK_JS = r"""
(function(){
  var figs = document.querySelectorAll('svg.wk');
  if(!figs.length) return;
  [].forEach.call(figs, function(svg, k){
    var id = 'wk' + k, n = svg.closest('.walk');
    svg.setAttribute('data-walk', id);
    for(n = n && n.nextElementSibling; n && n.tagName !== 'H2' && !n.classList.contains('walk'); n = n.nextElementSibling){
      if(n.classList.contains('cfg')) n.setAttribute('data-walk', id);
    }
  });
  var fine = !!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches);
  var G = '①②③④⑤⑥⑦⑧⑨';
  var pop = null, anchor = null, pinned = false, tShow = null, tHide = null, hoverEl = null, lit = [], down = null;
  function make(){
    pop = document.createElement('div'); pop.id = 'wkpop'; pop.hidden = true; pop.setAttribute('role', 'dialog');
    document.body.appendChild(pop);
    pop.addEventListener('mouseenter', function(){ clearTimeout(tHide); });
    pop.addEventListener('mouseleave', function(){ if(!pinned) hideSoon(); });
  }
  function fill(el){
    var svg = el.closest('svg.wk'), n = el.getAttribute('data-ref');
    var cfgs = svg ? document.querySelectorAll('.cfg[data-walk="' + svg.getAttribute('data-walk') + '"]') : [];
    var box = document.createDocumentFragment(), found = false;
    [].forEach.call(cfgs, function(c){
      var rows = [].slice.call(c.querySelectorAll('.cr')), last = -1, lines = [];
      rows.forEach(function(r, i){
        if((' ' + (r.getAttribute('data-ref') || '') + ' ').indexOf(' ' + n + ' ') < 0) return;
        var code = r.querySelector('.cc').textContent.replace(/\s+$/, '');
        if(last >= 0 && i > last + 1 && lines.length && lines[lines.length - 1] !== '!'){
          var ind = code.length - code.replace(/^ +/, '').length;
          lines.push(ind ? '\u0000' + new Array(ind + 1).join(' ') + '\u2026' : '\u0000!');
        }
        lines.push(code);
        last = i; lit.push(r);
      });
      if(!lines.length) return;
      found = true;
      var h = document.createElement('div'); h.className = 'wp-h';
      var b = document.createElement('span'); b.className = 'wp-n'; b.textContent = G.charAt(n - 1);
      var t = document.createElement('span'); t.className = 'wp-t';
      var ct = c.querySelector('.ctitle');
      if(ct){ ct = ct.cloneNode(true); var f = ct.querySelector('.cfold'); if(f) f.parentNode.removeChild(f); t.textContent = ct.textContent.trim(); }
      h.appendChild(b); h.appendChild(t); box.appendChild(h);
      var pre = document.createElement('pre');
      lines.forEach(function(l, i){
        if(i) pre.appendChild(document.createTextNode('\n'));
        if(l.charAt(0) === '\u0000'){ var s = document.createElement('span'); s.className = 'wp-sep'; s.textContent = l.slice(1); pre.appendChild(s); }
        else pre.appendChild(document.createTextNode(l));
      });
      box.appendChild(pre);
    });
    if(!found) return false;
    while(pop.firstChild) pop.removeChild(pop.firstChild);
    pop.appendChild(box);
    lit.forEach(function(r){ r.classList.add('wk-hl'); });
    return true;
  }
  function place(){
    if(!anchor || !pop || pop.hidden) return;
    var r = anchor.getBoundingClientRect(), vw = document.documentElement.clientWidth, vh = window.innerHeight, m = 8;
    if(r.bottom < 0 || r.top > vh){ hide(); return; }
    pop.style.left = '0px'; pop.style.top = '0px';
    var pw = pop.offsetWidth, ph = pop.offsetHeight, left, top;
    var svg = anchor.closest('svg.wk'), sr = svg ? svg.getBoundingClientRect() : r;
    var side = Math.min(Math.max(m, r.top), Math.max(m, vh - ph - m));
    if(vw - sr.right - 2 * m >= pw){ left = sr.right + m; top = side; }          /* 図の横に余白があれば横へ(図を隠さない) */
    else if(sr.left - 2 * m >= pw){ left = sr.left - pw - m; top = side; }
    else {                                                                      /* 無ければ番号の下(入らなければ上) */
      top = r.bottom + 6;
      if(top + ph > vh - m && r.top - 6 - ph >= m) top = r.top - 6 - ph;
      left = Math.max(m, Math.min(r.left, vw - pw - m));
    }
    pop.style.left = left + 'px';
    pop.style.top = Math.max(m, top) + 'px';
  }
  function unlit(){ lit.forEach(function(r){ r.classList.remove('wk-hl'); }); lit = []; }
  function show(el, pin){
    if(!pop) make();
    clearTimeout(tShow); clearTimeout(tHide);
    if(anchor) anchor.classList.remove('on');
    unlit();
    if(!fill(el)){ anchor = null; pop.hidden = true; return; }
    anchor = el; pinned = !!pin;
    /* カーソルで出している間は小窓がカーソルを遮らない(下の図の番号へそのまま移れる)。押して固定したら触れる */
    pop.style.pointerEvents = pinned ? 'auto' : 'none';
    pop.hidden = false; el.classList.add('on'); place();
  }
  function hide(){
    clearTimeout(tShow); clearTimeout(tHide);
    if(pop) pop.hidden = true;
    if(anchor) anchor.classList.remove('on');
    unlit(); anchor = null; pinned = false;
  }
  function hideSoon(){ clearTimeout(tHide); tHide = setTimeout(hide, 250); }
  function refOf(t){ return t && t.closest ? t.closest('svg.wk .wk-ref') : null; }
  if(fine){
    document.addEventListener('mousemove', function(e){
      if(e.movementX === 0 && e.movementY === 0) return;
      var g = refOf(e.target);
      if(g === hoverEl) return;
      hoverEl = g; clearTimeout(tShow);
      if(g){ clearTimeout(tHide); if(anchor !== g) tShow = setTimeout(function(){ show(g, false); }, 300); }
      else if(anchor && !pinned && !(pop && pop.contains(e.target))) hideSoon();
    });
  }
  document.addEventListener('pointerdown', function(e){ down = {t: e.target, x: e.clientX, y: e.clientY}; }, true);
  document.addEventListener('click', function(e){
    var t = e.target;
    if(down && t.closest && t.closest('#figbig') && Math.abs(e.clientX - down.x) + Math.abs(e.clientY - down.y) < 6) t = down.t;
    var g = refOf(t);
    if(g){ if(anchor === g && pinned){ hide(); return; } show(g, true); return; }
    if(pop && !pop.hidden && !pop.contains(e.target)) hide();
  });
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') hide(); });
  window.addEventListener('scroll', place, {passive: true});
  window.addEventListener('resize', place);
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
    if meta.get("_gl"):            # 用語集(BL-260)は目次の隣
        rows.append(f'<a class="rn-toc" href="glossary.html">{word("glossary")}</a>')
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
    out = RH.render(text, title=p["title"], extra_css=READING_CSS + (GL.GLOSS_CSS if meta.get("_gl") else ""),
                    body_class="reading", allow_html=True,
                    mermaid_mode=("cdn" if mermaid_mode == "local" else mermaid_mode), **kw)
    if mermaid_mode == "local":
        out = out.replace(RH.MERMAID_CDN, "mermaid.min.js")
    out, p["_sections"] = mark_sections(out)
    p["_tries"] = extract_tries(out)
    gl_tail = ""
    if meta.get("_gl"):            # 用語集(BL-260)。「やってみる」の取り出しの後(ワークスペースの小窓に包みを持ち込まない)
        out, p["_gl_hits"] = GL.annotate(out, meta["_gl"].matcher(meta["key"], p["file"]), langs[0])
        if p["_gl_hits"]:
            gl_tail = (GL.popup_data(meta["_gl"], {h[0] for h in p["_gl_hits"]}, "glossary.html")
                       + f"\n<script>{GL.GLOSS_JS}</script>\n")
    out = out.replace("</body>", f"{reading_nav(meta, i)}\n<script>{READ_JS}</script>\n<script>{CFG_JS}</script>\n<script>{FIG_JS}</script>\n<script>{WALK_JS}</script>\n{gl_tail}</body>", 1)
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
        n = meta.get("_gl_count")
        glink = (f'<p class="glink"><a href="glossary.html">{_w("glossary")}</a> <span>({n})</span></p>\n\n' if n else "")
        return (f'<p class="portal"><a href="/">{_w("portal")}</a></p>\n\n# {_pick(meta["title"], lang)}\n\n'
                + (f'<p class="lead">{html.escape(sub)}</p>\n\n' if sub else "")
                + glink + toc + "\n")

    kw = {"lang": langs[0], "alt_lang": langs[1], "alt_md": body(langs[1])} if len(langs) == 2 else {}
    first = body(langs[0])
    set_lang(meta)
    out = RH.render(first, title=_pick(meta["title"], langs[0]), extra_css=READING_CSS + INDEX_CSS,
                    body_class="reading rindex", allow_html=True, mermaid_mode="none", **kw)
    dst = os.path.join(out_dir, "index.html")
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(_finish_lang(out))
    return dst


def _sec_label(page, mark, lang):
    """逆引きに出す節の名前= (短い名前, 見出しの全文)。見出しが番号で始まれば番号だけ(「2.1 EVI と…」→ 2.1)、無ければ詰めた見出し。"""
    t = (page.get("_sections", {}).get(mark) or {})
    full = t.get(lang) or t.get("") or next(iter(t.values()), mark)
    m = re.match(r"(\d+(?:\.\d+)*)\.?\s", full)
    return (m.group(1) if m else GL._short(full, 14)), full


def _gl_page_ref(meta, lang, bundle_pages=None):
    """用語集の逆引き: ページへのリンク＋節へのリンク(4 つまで)。束ね版は 1 枚の中のページの錨(#pg<n>)へ。"""
    def ref(i, marks, lang_=lang):
        if bundle_pages is not None:
            return f'<a href="#pg{i}">{html.escape(bundle_pages[i]["title"])}</a>'
        p = meta["pages"][i]
        secs = [m for m in marks if m]
        more = f" +{len(secs) - 4}" if len(secs) > 4 else ""
        labels = [(m, *_sec_label(p, m, lang_)) for m in secs[:4]]
        inner = " ".join(f'<a href="{p["html"]}#{m}" title="{html.escape(full)}">{html.escape(short)}</a>'
                         for m, short, full in labels)
        return (f'<a href="{p["html"]}">{html.escape(p["_titles"][lang_])}</a>'
                + (f' <span class="gsec">{inner}{more}</span>' if inner else ""))
    return ref


def _load_glossary(src, meta):
    """book.yml の glossary: false で切る。この本に効く語が 1 つも無ければ None。"""
    if meta.get("glossary") is False:
        return None
    gl = GL.load(src)
    for p in gl.problems:
        print(f"[glossary] 警告: {p}", file=sys.stderr)
    return gl if gl.for_book(meta["key"]) else None


def build_glossary(meta, out_dir):
    """用語集ページ(glossary.html)。この本に出てくる語＋その関連語を、英語の見出し語の順に。"""
    gl, langs = meta["_gl"], meta["_langs"]
    refs = GL.collect([(i, p.get("_gl_hits") or []) for i, p in enumerate(meta["pages"])])
    ids = gl.closure(refs)

    def body(lang):
        return GL.page_md(gl, ids, refs, lang, _gl_page_ref(meta, lang))

    kw = {"lang": langs[0], "alt_lang": langs[1], "alt_md": body(langs[1])} if len(langs) == 2 else {}
    set_lang(meta)
    out = RH.render(body(langs[0]), title=f'{_w("glossary")} — {_pick(meta["title"], langs[0])}',
                    extra_css=READING_CSS + GL.GLOSS_PAGE_CSS, body_class="reading", allow_html=True,
                    mermaid_mode="none", **kw)
    out = out.replace("</body>", f"<script>{GL.GLOSS_PAGE_JS}</script>\n</body>", 1)
    with open(os.path.join(out_dir, "glossary.html"), "w", encoding="utf-8") as fh:
        fh.write(_finish_lang(out))
    return len(ids)


def build(src, mermaid_mode="local"):
    src = src if os.path.isabs(src) else os.path.join(REPO, src)
    meta = load_book(src)
    set_lang(meta)
    meta["_gl"] = _load_glossary(src, meta)
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
    if meta["_gl"]:
        meta["_gl_count"] = build_glossary(meta, out_dir)
        print(f"  {os.path.relpath(os.path.join(out_dir, 'glossary.html'), REPO)}  （用語 {meta['_gl_count']}）")
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
                   "pages": len(meta["pages"]), "glossary": meta.get("_gl_count") or 0,
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


_PAGE_LINK = re.compile(r'<a\s([^>]*?)href="([\w.-]+\.html)(?:#[^"]*)?"([^>]*)>(.*?)</a>', re.S)


def _bundle_links(page_html, pages, book_pages):
    """束ね版の中のページへのリンク(`b7-….html`・`….html#s2`)を付け替える。同じ 1 枚にあるページは 1 枚の中の錨(#pg<n>)へ、
    別の 1 枚にあるページは行き先が無いので文字だけ残す(2026-11-02。付録から追補のページへのリンクが切れていた)。"""
    idx = {p["html"]: i for i, p in enumerate(pages)}

    def rep(m):
        page = m.group(2)
        if page in idx:
            return f'<a {m.group(1)}href="#pg{idx[page]}"{m.group(3)}>{m.group(4)}</a>'
        return m.group(4) if page in book_pages else m.group(0)

    return _PAGE_LINK.sub(rep, page_html)


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
    gl = meta.get("_gl")
    out = RH.render(md, title=title, extra_css=READING_CSS + BUNDLE_CSS + (GL.GLOSS_CSS + GL.GLOSS_PAGE_CSS if gl else ""),
                    body_class="reading", allow_html=True, mermaid_mode=mode)
    out = _bundle_links(out, pages, {p["html"] for p in meta["pages"]})
    gl_tail = ""
    if gl:                         # 用語集(BL-260): 吹き出し＋1 枚の末尾の用語集の節(1 枚の中で完結)
        cache = {}

        def matcher_for(k):        # ページの錨(pg<n>)ごとに、そのページの scope で拾う
            if k not in cache:
                cache[k] = gl.matcher(meta["key"], pages[k]["file"] if k is not None else None)
            return cache[k]

        out, hits = GL.annotate(out, matcher_for, _LANG)
        by_page = {}
        for h in hits:
            if h[2].startswith("pg"):
                by_page.setdefault(int(h[2][2:]), []).append(h)
        refs = GL.collect(sorted(by_page.items()))
        ids = gl.closure(refs)
        if ids:
            sec = GL.bundle_section(gl, ids, refs, _LANG, _gl_page_ref(meta, _LANG, pages))
            out = out.replace("</main>", sec + "</main>", 1)
            gl_tail = GL.popup_data(gl, set(refs), "") + f"\n<script>{GL.GLOSS_JS}</script>\n"
    out = out.replace("<body", '<body id="top"', 1).replace("</body>", f"<script>{CFG_JS}</script>\n<script>{FIG_JS}</script>\n<script>{WALK_JS}</script>\n{gl_tail}</body>", 1)
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
    meta["_gl"] = _load_glossary(src, meta)
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
    ap.add_argument("cmd", choices=["build", "bundle", "glossary"])
    ap.add_argument("--src", help="読み物ソースのディレクトリ(glossary では任意)")
    ap.add_argument("--mermaid", default="local", choices=["local", "cdn", "embed", "none"],
                    help="local= mermaid.min.js を出力先に1本置いて共有(既定)")
    ap.add_argument("--out", help="bundle の出力先(既定 reading/<key>-offline.html)")
    ap.add_argument("--split", action="store_true", help="章ごとに 1 枚に分ける")
    ap.add_argument("--stage", action="store_true",
                    help="持ち出し用ディレクトリ reading/_offline/<key>/ へ出す(--split 前提)")
    ap.add_argument("--unknown", action="store_true", help="glossary: 本文に出るのに辞書に無い略語を並べる")
    a = ap.parse_args()
    if a.cmd == "glossary":
        src = a.src and (a.src if os.path.isabs(a.src) else os.path.join(REPO, a.src))
        sys.exit(GL.check(src, a.unknown, load_book))
    if not a.src:
        ap.error("--src が要る")
    if a.cmd == "bundle":
        build_bundle(a.src, a.out, a.split or a.stage, a.stage)
    else:
        build(a.src, a.mermaid)


if __name__ == "__main__":
    main()
