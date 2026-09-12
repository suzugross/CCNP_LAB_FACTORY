#!/usr/bin/env python3
"""問題文 Markdown → 単一ファイル HTML レンダラ (BL-099 問題パック用)。

問題パック `packs/<PACK-ID>/` に置く問題用紙を生成する。ユーザは HTML を
ブラウザ / VSCode のプレビュー拡張で開いて解く。

設計方針:
  - **既定は「ふつうの HTML」**(--mermaid cdn): CSS はインライン、mermaid だけ CDN 参照。
    1ファイル数十KBで、Windows 側のブラウザからそのまま開ける想定。
  - オフラインで使いたい時は `--mermaid embed` で mermaid 本体(3.5MB)も埋め込み、
    外部参照ゼロの単一ファイルにできる(ネットに出られない閲覧環境向け)。
  - どちらのモードでも**描画に失敗したら警告を出し、図のソースは残す**。
  - **show 出力と ASCII 図を絶対に崩さない**。コードフェンスは等幅・折り返し無し・
    横スクロール。紙面問題は図と show 出力が主役なのでここが品質の要。
  - **テーマは試験画面風の白一色**(ユーザ要望 2026-08-08)。ダークモードには追随せず
    常に白・装飾なし・罫線だけで区切る。本番の試験シムの見え方に寄せる。
  - **正解キー(answers/)を読んだら異常終了**する漏洩ガードを持つ(§3 設計メモ)。

使い方:
  render_html.py --in questions/20260808-001.md --out packs/P/q1.html \
                 --title "Q1 紙面" [--nav-json nav.json] [--source-link ../..]
  render_html.py --selftest        # questions/ 全件を一時領域へ描画して自己診断

モジュールとしても使う: render(md_text, title=..., nav=[...]) -> str
"""

import argparse
import html
import json
import os
import re
import sys
import tempfile

from markdown_it import MarkdownIt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MERMAID_JS = os.path.join(REPO, "topologies", "assets", "mermaid.min.js")
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
MERMAID_MODES = ("cdn", "embed", "none")

# 正解キーの混入を検出するマーカ(answers/*.md の見出し語)。
# 問題文には現れない語だけを選ぶ(「正解」単体は選択肢の指示文に現れうるので使わない)。
KEY_MARKERS = ["## 正解", "## 各選択肢の判定", "## 仕込んだ状態", "ルーブリック",
               "## 検証コマンドと期待される出力"]


# --------------------------------------------------------------------------
# 漏洩ガード
# --------------------------------------------------------------------------
def assert_not_answer_key(path, text):
    """answers/ 由来・正解キー相当の入力を拒否する。

    パック配下に正解が混入する事故は「その日の学習が丸ごと無駄になる」ため、
    パス・内容の二重で弾き、疑わしきは異常終了(rc=3)させる。
    """
    norm = os.path.normpath(os.path.abspath(path)).replace(os.sep, "/")
    if "/answers/" in norm:
        sys.exit(f"[render_html] 拒否: answers/ 配下は描画できません: {path}")
    hits = [m for m in KEY_MARKERS if m in text]
    if hits:
        sys.exit(f"[render_html] 拒否: 正解キーらしき見出しを検出: {hits} ({path})")


# --------------------------------------------------------------------------
# Markdown → 本文 HTML
# --------------------------------------------------------------------------
def _fence_rule(self, tokens, idx, options, env):
    """コードフェンスの描画。mermaid だけ <pre class="mermaid"> に落とす。

    ハイライトは行わない: 問題文のフェンスは show 出力・config・ASCII 図で、
    色を付けると「どこが要点か」の道標になってしまう(BL-088 道標の除去と同じ理由)。
    """
    tok = tokens[idx]
    info = (tok.info or "").strip().split()
    lang = info[0] if info else ""
    if lang == "mermaid":
        env["has_mermaid"] = True
        return f'<pre class="mermaid">{html.escape(tok.content)}</pre>\n'
    cls = f' class="lang-{html.escape(lang)}"' if lang else ""
    return f'<pre class="code"><code{cls}>{html.escape(tok.content)}</code></pre>\n'


def make_md():
    md = MarkdownIt("default")          # CommonMark + table + strikethrough
    md.add_render_rule("fence", _fence_rule)
    return md


# 選択肢の行頭記号(A. / **A.** / A) / Ａ． など)。
# ★A-F 決め打ちは不可(2026-08-08 実機で 7択=A-G の問題が出て G が欠落した)。
CHOICE_RE = re.compile(r"^(\*{0,2})([A-J])([.．)）])")


def separate_choices(md_text):
    """「## 選択肢」節の各選択肢を独立した段落にする。

    ★問題文の Markdown は選択肢を改行だけで並べており、Markdown の規則では
    連続行が1段落に畳まれる = 全選択肢が1行につながって表示される(VSCode の
    プレビューでも同じ)。読みづらさの原因なので、描画側で空行を補って分ける。
    (問題文そのものは書き換えない = 採点・生成側に一切影響しない)
    """
    out, in_fence, in_sec = [], False, False
    for line in md_text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            in_sec = "選択肢" in line
        if in_sec and not in_fence and CHOICE_RE.match(line) \
                and out and out[-1].strip():
            out.append("")
        out.append(line)
    return "\n".join(out)


def choice_letters(md_text):
    """「## 選択肢」節にある選択肢の記号を順に返す(A, B, C, ...)。

    解答フォームのラジオボタンを、その問題に実在する選択肢だけで作るために使う。
    """
    letters, in_fence, in_sec = [], False, False
    for line in md_text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            in_sec = "選択肢" in line
        if in_sec and not in_fence:
            m = CHOICE_RE.match(line)
            if m and m.group(2) not in letters:
                letters.append(m.group(2))
    return letters


def pick_count(md_text):
    """設問が何個選ばせるかを返す（「(2つを選択してください)」→ 2。既定 1。
    ★「すべて選んでください」(数非明示= all-that-apply・BL-125)は **-1**）。

    ★解答フォームの形（ラジオ／チェックボックス）を決めるために使う。
      正解キーは絶対に見ない — 問題文だけから判断する。
    """
    m = re.search(r"[(（]\s*([0-9０-９一二三四五六七八九])\s*つ(?:を)?\s*選[^)）]*"
                  r"[)）]", md_text)
    if not m:
        # ★括弧なしの「…、2つ選択してください。」(aaa/patchseq 等の設問文)も複数選択
        #   (2026-09-06 PACK-20260906-B Q2: ラジオになり B・C を選べず誤採点→BL-156)。
        #   設問見出し以降に限定して本文中の偶然の一致を避ける。
        tail = md_text.split("## 設問", 1)[1] if "## 設問" in md_text else md_text
        m = re.search(r"([0-9０-９一二三四五六七八九])\s*つ(?:を)?\s*選(?:択|ん)", tail)
    if not m:
        # 数非明示の複数選択。個数はヒントにも出さない(採点は記号集合の一致)。
        if re.search(r"すべて選んでください", md_text):
            return -1
        return 1
    z = m.group(1).translate({ord(c): ord(c) - 0xFEE0 for c in "０１２３４５６７８９"})
    return {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9}.get(z, int(z) if z.isdigit() else 1)


def mark_choices(body):
    """選択肢の段落に、記号を切り出したカード用のクラスを付ける。

    ★後処理は「選択肢」見出し以降だけに限定する(本文中の「A. 〜」を巻き込まない)。
    """
    m = re.search(r"<h2>[^<]*選択肢[^<]*</h2>", body)
    if not m:
        return body
    head, tail = body[:m.end()], body[m.end():]
    # 形式2: **A.** の直後にコードブロックが続く形(経路表を選ばせる問)
    tail = re.sub(
        r"<p><strong>([A-J])[.．)）]?</strong></p>\s*<pre class=\"code\">(.*?)</pre>",
        r'<div class="choice"><span class="cl">\1</span>'
        r'<pre class="code">\2</pre></div>',
        tail, flags=re.S)
    # 形式1: A. 〜 の1行テキスト
    tail = re.sub(r"<p>([A-J])[.．)）]\s*",
                  r'<p class="choice"><span class="cl">\1</span>', tail)
    return head + tail


def md_to_body(md_text):
    """Markdown 本文を HTML 断片へ。(body, has_mermaid) を返す。"""
    env = {}
    body = make_md().render(separate_choices(md_text), env)
    body = mark_choices(body)
    # 表は横スクロール容器で包む(リンク一覧が広い問題で本文が横に伸びるのを防ぐ)
    body = body.replace("<table>", '<div class="tablewrap"><table>')
    body = body.replace("</table>", "</table></div>")
    return body, bool(env.get("has_mermaid"))


# --------------------------------------------------------------------------
# ページ組み立て
# --------------------------------------------------------------------------
CSS = """
/* 試験画面風テーマ: 白一色・装飾なし・罫線だけで区切る。
   ダークモードには追随しない(常に白。本番の試験シムに合わせる)。 */
:root{ color-scheme: light; }
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#ffffff;color:#000000}
body{
  font-family:"Segoe UI","Yu Gothic UI",Meiryo,"Hiragino Kaku Gothic ProN",
              system-ui,sans-serif;
  line-height:1.75; font-size:15px;
}
a{color:#0645ad}
a:visited{color:#0645ad}
.nav{
  position:sticky; top:0; z-index:10; background:#ffffff;
  border-bottom:1px solid #000000; padding:.5rem 1rem;
  display:flex; gap:.9rem; align-items:center; flex-wrap:wrap; font-size:.88rem;
}
.nav .cur{color:#555555}
.nav .sp{flex:1}
main{max-width:1000px; margin:0 auto; padding:1rem 1.2rem 5rem}
h1{font-size:1.4rem; font-weight:600; border-bottom:1px solid #000000;
   padding-bottom:.35rem; margin:1rem 0 .8rem}
h2{font-size:1.1rem; font-weight:600; border-bottom:1px solid #aaaaaa;
   padding-bottom:.25rem; margin:1.8rem 0 .6rem}
h3{font-size:1rem; font-weight:600; margin:1.4rem 0 .5rem}
p{margin:.7rem 0}
blockquote{
  margin:.9rem 0; padding:.5rem .9rem; background:#ffffff;
  border:1px solid #000000;
}
blockquote p{margin:.2rem 0}
/* show 出力・config・ASCII 図: 折り返さず横スクロール(崩さないことが最優先) */
pre.code{
  background:#ffffff; color:#000000; border:1px solid #999999;
  padding:.7rem .9rem; overflow-x:auto; margin:.9rem 0;
}
pre.code code{
  font-family:Consolas,"DejaVu Sans Mono","Liberation Mono",monospace;
  font-size:13px; line-height:1.45; white-space:pre; display:block;
}
code{font-family:Consolas,"DejaVu Sans Mono",monospace; font-size:.92em}
pre.code code{background:none; padding:0}
pre.mermaid{
  background:#ffffff; border:1px solid #999999; padding:.9rem;
  overflow-x:auto; margin:.9rem 0; text-align:center;
  font-family:Consolas,"DejaVu Sans Mono",monospace; font-size:13px;
  white-space:pre;
}
pre.mermaid svg{max-width:100%; height:auto}
/* 選択肢: 罫線だけの素っ気ない箱。記号は左肩に固定 */
.choice{
  position:relative; margin:.5rem 0; padding:.6rem .9rem .6rem 2.6rem;
  border:1px solid #999999; background:#ffffff;
}
.choice .cl{
  position:absolute; left:.8rem; top:.55rem; font-weight:700; color:#000000;
}
.choice pre.code{margin:.2rem 0 0; border-color:#cccccc}
/* 解答欄: 本文とはっきり分ける(上に太い罫線) */
.answer{margin:2.2rem 0 0; padding:1rem 0 0; border-top:3px solid #000000}
.answer h2{border:0; margin:0 0 .6rem; padding:0}
.answer .opts{display:flex; flex-wrap:wrap; gap:.4rem; margin:.4rem 0 .9rem}
.answer .opts label{
  display:inline-flex; align-items:center; gap:.35rem;
  border:1px solid #999999; padding:.35rem .8rem; cursor:pointer;
  min-width:3.4rem; justify-content:center; font-weight:600;
}
.answer .opts label:hover{background:#f2f2f2}
.answer .opts input{margin:0}
.answer .opts label.on{border:2px solid #000000; padding:.3rem .75rem}
.answer label.row{display:block; margin:.6rem 0 .2rem; font-size:.9rem}
.answer textarea{
  width:100%; min-height:4.5rem; padding:.5rem; border:1px solid #999999;
  font-family:inherit; font-size:.95rem; line-height:1.6; background:#ffffff;
  color:#000000;
}
.answer .done{display:flex; align-items:center; gap:.4rem; margin:.8rem 0 0;
  font-weight:600}
.answer .timer{display:flex; align-items:center; gap:.6rem; margin:.9rem 0 0;
  padding:.5rem .7rem; border:1px solid #cccccc; background:#fafafa}
.answer .timer button{font:inherit; padding:.25rem .8rem; border:1px solid #333333;
  background:#ffffff; cursor:pointer}
.answer .timer button:hover{background:#eeeeee}
.answer .timer button:disabled{color:#aaaaaa; border-color:#bbbbbb; cursor:default}
.answer .timer .telapsed{font-variant-numeric:tabular-nums; font-weight:600;
  min-width:4.5rem}
.answer .timer .tkind{font-size:.8rem; color:#777777}
.answer .savemsg{font-size:.83rem; color:#555555; margin-top:.5rem;
  min-height:1.2em}
.answer .savemsg.err{color:#a00000; font-weight:600}
.tablewrap{overflow-x:auto; margin:.9rem 0}
table{border-collapse:collapse; width:100%; font-size:.92rem}
th,td{border:1px solid #999999; padding:.4rem .65rem; text-align:left}
th{background:#ffffff; font-weight:600}
hr{border:0; border-top:1px solid #aaaaaa; margin:1.8rem 0}
ul,ol{padding-left:1.5rem}
li{margin:.25rem 0}
.meta{color:#555555; font-size:.83rem; margin:.2rem 0 1.2rem}
.diagnote{
  margin:.9rem 0 -.4rem; padding:.45rem .7rem; font-size:.86rem;
  border:1px solid #000000; background:#ffffff; color:#000000;
}
@media print{
  .nav{display:none}
  body{font-size:10.5pt}
  pre.code{white-space:pre-wrap; word-break:break-all}
  main{max-width:none; padding:0}
}
"""

MERMAID_INIT = """
(function(){
  /* 図が出ない時に「黙って崩れる」ことを避ける: 失敗したブロックには注記を出し、
     ソースはそのまま残す(BL-087 の原則によりリンク一覧が正典なので解答は可能)。 */
  function note(el, msg){
    if(!el || el.dataset.noted) return;
    el.dataset.noted = '1';
    var d = document.createElement('div');
    d.className = 'diagnote';
    d.textContent = '⚠ 図の描画に失敗しました（' + msg +
                    '）。以下の図ソースとリンク一覧を参照してください。';
    el.parentNode.insertBefore(d, el);
  }
  var blocks = Array.prototype.slice.call(
                 document.querySelectorAll('pre.mermaid'));
  if(!window.mermaid){
    blocks.forEach(function(el){
      note(el, 'mermaid を読み込めなかった（ネットに出られない環境なら ' +
               'pack.sh new --mermaid embed で作り直す）');
    });
    return;
  }
  try{
    window.mermaid.initialize({
      startOnLoad:false, theme:'neutral',   /* 白基調・グレースケール寄り */
      securityLevel:'loose', flowchart:{htmlLabels:true, useMaxWidth:true}
    });
    Promise.resolve(window.mermaid.run({querySelector:'pre.mermaid'}))
      .catch(function(e){ blocks.forEach(function(el){ note(el, String(e)); }); })
      .then(function(){
        blocks.forEach(function(el){
          if(!el.querySelector('svg')) note(el, '描画結果なし');
        });
      });
  }catch(e){
    blocks.forEach(function(el){ note(el, String(e)); });
  }
})();
"""

ANSWER_JS = r"""
(function(){
  var box = document.querySelector('.answer'); if(!box) return;
  var pack = box.dataset.pack, no = box.dataset.no, kind = box.dataset.kind;
  var ref = box.dataset.ref;
  var msg = box.querySelector('.savemsg');
  var timer = null, loaded = false;

  function say(t, err){ msg.textContent = t; msg.className = 'savemsg' + (err ? ' err' : ''); }
  function api(){ return '/_api/sheet?pack=' + encodeURIComponent(pack) + '&no=' + no; }

  /* ---- ストップウォッチ(BL-144) --------------------------------------
     ページを開いたら自動開始(2026-08-24 ユーザ要望)。ページ離脱で自動一時停止・
     再訪で自動再開する(開きっぱなしで別の問題を解くと二重計上になるのを防ぐ)。
     ★「一時停止」ボタン・「解答済み」チェックによる**明示的な停止は尊重**し、
       開き直しても勝手に再開しない(p='user')。タブ切替(hidden)では止めない —
       ラボ問は CML コンソール作業中ページが隠れるため、止めると過小計測になる。
     「解答済み/実装完了」チェックで一時停止=確定し、所要: 行として保存される。
     状態は localStorage に持ちリロード・再訪に耐える。 */
  var TKEY = 'ccnp-timer:' + pack + ':' + no;
  /* e=累積ms, r=計測中なら開始epoch,
     k=open(ページ表示で開始)|manual|auto(入力で開始・押し忘れ保険),
     p=停止の由来 ''|user(明示停止=再開しない)|page(離脱停止=再訪で再開) */
  var ts = {e: 0, r: 0, k: '', p: ''};
  try{ ts = JSON.parse(localStorage.getItem(TKEY)) || ts; }catch(_e){}
  function tsave(){ try{ localStorage.setItem(TKEY, JSON.stringify(ts)); }catch(_e){} }
  function tnow(){ return ts.e + (ts.r ? Date.now() - ts.r : 0); }
  function tfmt(ms){
    var s = Math.floor(ms / 1000), h = Math.floor(s / 3600);
    var m = Math.floor(s % 3600 / 60), r = s % 60;
    function z(n){ return (n < 10 ? '0' : '') + n; }
    return h ? h + ':' + z(m) + ':' + z(r) : m + ':' + z(r);
  }
  var tui = document.createElement('div');
  tui.className = 'timer';
  tui.innerHTML = '<button type="button" class="tstart">スタート</button>' +
                  '<button type="button" class="tpause">一時停止</button>' +
                  '<span class="telapsed">0:00</span><span class="tkind"></span>';
  function tstart(kind){
    if(ts.r) return;
    ts.r = Date.now(); if(!ts.k) ts.k = kind;
    ts.p = '';
    tsave(); trender();
  }
  function tpause(by){
    if(!ts.r) return;
    ts.e += Date.now() - ts.r; ts.r = 0; ts.p = by || 'user';
    tsave(); trender(); queue();     /* 中断時点の所要も 解答.md へ反映しておく */
  }
  function trender(){
    tui.querySelector('.telapsed').textContent = tfmt(tnow());
    tui.querySelector('.tkind').textContent =
      (ts.r ? '計測中' : (ts.k ? '停止中' : '未計測')) +
      (ts.k === 'auto' ? '・自動開始' :
       (ts.k === 'open' ? '・ページ表示で開始' : ''));
    tui.querySelector('.tstart').disabled = !!ts.r;
    tui.querySelector('.tpause').disabled = !ts.r;
  }
  tui.querySelector('.tstart').addEventListener('click', function(){ tstart('manual'); });
  tui.querySelector('.tpause').addEventListener('click', function(){ tpause('user'); });
  setInterval(function(){ if(ts.r) trender(); }, 1000);
  /* ページ表示で自動開始。明示停止(p='user')済み・解答済みの問題は再開しない。
     ★過去データ(pなし)の停止は由来不明=明示停止扱いにして勝手に動かさない。 */
  function topen(){
    var done = box.querySelector('.done input');
    if(done && done.checked) return;
    if(ts.r || ts.p === 'user') return;
    if(ts.k && ts.p !== 'page') return;
    if(document.visibilityState !== 'hidden'){ tstart('open'); return; }
    /* バックグラウンドタブで開かれた時は、最初に表に出た瞬間から計り始める */
    document.addEventListener('visibilitychange', function h(){
      if(document.visibilityState === 'hidden') return;
      document.removeEventListener('visibilitychange', h);
      if(!ts.r && ts.p !== 'user') tstart('open');
    });
  }
  /* 離脱(次の問題へ移動・タブを閉じる)で自動一時停止=二重計上の防止。
     fetch はもう完走しないので sendBeacon で 所要: を 解答.md へ滑り込ませる。 */
  window.addEventListener('pagehide', function(){
    if(!ts.r) return;
    ts.e += Date.now() - ts.r; ts.r = 0; ts.p = 'page'; tsave();
    if(loaded && navigator.sendBeacon){
      try{
        navigator.sendBeacon(api(),
          new Blob([build()], {type: 'text/plain; charset=utf-8'}));
      }catch(_e){}
    }
  });
  /* 戻る/進むで bfcache から復活した時(load は走らない)も再開判定をやり直す */
  window.addEventListener('pageshow', function(ev){
    if(!ev.persisted) return;
    try{ ts = JSON.parse(localStorage.getItem(TKEY)) || ts; }catch(_e){}
    trender(); topen();
  });
  /* 押し忘れフォールバック: 解答欄への最初の入力で自動開始
     (タイマー操作と「解答済み」チェック自体は対象外) */
  function tguard(ev){
    if(ev.target.closest('.timer') || ev.target.closest('.done')) return;
    var done = box.querySelector('.done input');
    if(!ts.k && !ts.r && !(done && done.checked)) tstart('auto');
  }
  box.addEventListener('input', tguard, true);
  box.addEventListener('change', tguard, true);

  /* 解答.md の該当セクション本文を組み立てる(パーサと同じ書式を保つ) */
  function build(){
    var done = box.querySelector('.done input').checked;
    var label = kind === 'lab' ? (done ? '[x] 実装完了' : '[ ] 未着手')
                               : (done ? '[x] 解答済' : '[ ] 未着手');
    var head = '## Q' + no + ' (' + (kind === 'lab' ? 'ラボ' : '紙面') + ' ' +
               ref + ')   状態: ' + label;
    var lines = [head, ''];
    if(kind === 'lab'){
      lines.push('メモ: ' + val('.memo'));
    }else{
      lines.push('解答: ' + ansValue());
      lines.push('根拠: ' + val('.why'));
    }
    if(ts.k){                        /* 計測があった時だけ 所要: 行を書く(BL-144) */
      lines.push('所要: ' + tfmt(tnow()) + (ts.k === 'auto' ? ' (自動開始)' : ''));
    }
    return lines.join('\n') + '\n';
  }
  /* 選択式はラジオ/チェックボックス、記述式は textarea。
     ★複数選択は**チェックされた全部**を「・」で連結する(1つ目だけ読むと
       解答が欠ける。2026-08-11 に複数選択問題を追加した際の修正)。 */
  function ansValue(){
    var on = box.querySelectorAll('.opts input:checked');
    if(on.length){
      return Array.prototype.map.call(on, function(e){ return e.value; })
             .sort().join('・');
    }
    return val('.ans');
  }
  function val(sel){
    var el = box.querySelector(sel);
    if(!el) return '';
    return (el.value || '').replace(/\r/g, '').replace(/\n/g, ' ').trim();
  }

  /* 既存の 解答.md を読んでフォームへ復元(VSCode で直接書いた内容も拾う) */
  function load(){
    fetch(api()).then(function(r){
      if(!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    }).then(function(t){
      var m = t.match(/状態:\s*\[([ xX])\]/);
      if(m) box.querySelector('.done input').checked = m[1].toLowerCase() === 'x';
      var a = t.match(/^[ \t]*解答:[ \t]*(.*)$/m);
      var w = t.match(/^[ \t]*根拠:[ \t]*(.*)$/m);
      var mm = t.match(/^[ \t]*メモ:[ \t]*(.*)$/m);
      /* ★選択式(ラジオ/チェックボックス)には .ans 要素が無い。ここで .ans の
         存在を条件にすると**選択式の解答だけ復元されない**(保存はされているので
         開き直すと選択が消えたように見える。2026-08-12 にユーザ報告で発覚)。
         setAns() は選択式・記述式の両方を扱えるので、無条件に呼ぶ。 */
      if(a) setAns(a[1].trim());
      if(w && box.querySelector('.why')) box.querySelector('.why').value = w[1].trim();
      if(mm && box.querySelector('.memo')) box.querySelector('.memo').value = mm[1].trim();
      /* 所要の復元: localStorage が空(別ブラウザ等)なら 解答.md の値を種にする */
      var du = t.match(/^[ \t]*所要:[ \t]*(?:(\d+):)?(\d+):(\d\d)(\s*\(自動開始\))?/m);
      if(du && !ts.k && !ts.e){
        ts.e = ((+(du[1] || 0)) * 3600 + (+du[2]) * 60 + (+du[3])) * 1000;
        ts.k = du[4] ? 'auto' : 'manual';
        tsave();
      }
      trender();
      loaded = true; sync(); say('読み込み済み');
      topen();                       /* 解答済みかどうか確定してから自動開始判定 */
    }).catch(function(e){
      say('解答.md に書き込めません（' + e.message +
          '）。scripts/pack.sh serve 経由で開いてください', true);
      box.classList.add('offline');
      topen();                       /* 保存不能でも計測自体は生かす(localStorage) */
    });
  }
  function setAns(v){
    var letters = (v || '').toUpperCase().match(/[A-J]/g);
    var hit = false;
    if(letters){
      letters.forEach(function(L){
        var r = box.querySelector('.opts input[value="' + L + '"]');
        if(r){ r.checked = true; hit = true; }
      });
    }
    if(hit) return;
    var free = box.querySelector('.ans');
    if(free && free.tagName === 'TEXTAREA') free.value = v;
  }
  function sync(){
    box.querySelectorAll('.opts label').forEach(function(l){
      l.classList.toggle('on', l.querySelector('input').checked);
    });
  }

  function save(){
    if(!loaded) return;
    var body = build();
    say('保存中…');
    fetch(api(), {method:'POST', headers:{'Content-Type':'text/plain; charset=utf-8'},
                  body: body})
      .then(function(r){
        if(!r.ok) throw new Error('HTTP ' + r.status);
        /* ★何が保存されたかを必ず表示する。「保存しました」だけだと、
           保存が効いているのか確かめる術が無い(2026-08-12 ユーザ指摘)。 */
        var m = body.match(/^[ \t]*(解答|メモ):[ \t]*(.*)$/m);
        var what = m ? m[1] + ' ' + (m[2].trim() || '(空)') : '';
        var t = new Date().toTimeString().slice(0, 8);
        say('保存しました ' + t + ' — ' + what);
      })
      .catch(function(e){ say('保存に失敗: ' + e.message, true); });
  }
  function queue(){ sync(); clearTimeout(timer); timer = setTimeout(save, 600); }

  box.addEventListener('input', queue);
  box.addEventListener('change', queue);
  /* タイマーUIを「解答済み」チェックの直前に置き、チェックで計測を確定する */
  var doneLbl = box.querySelector('.done');
  if(doneLbl){
    doneLbl.parentNode.insertBefore(tui, doneLbl);
    doneLbl.querySelector('input').addEventListener('change', function(ev){
      if(ev.target.checked) tpause('user');
    });
  }
  trender();
  load();
})();
"""


PAGE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{nav}
<main>
{meta}
{body}
</main>
{scripts}
</body>
</html>
"""


def build_nav(nav):
    """nav = [{'label':..., 'href':..., 'current':bool}, ...] → ナビ HTML。"""
    if not nav:
        return ""
    parts = []
    for i, it in enumerate(nav):
        label = html.escape(it["label"])
        if it.get("spacer"):
            parts.append('<span class="sp"></span>')
        if it.get("current"):
            parts.append(f'<span class="cur">{label}</span>')
        else:
            parts.append(f'<a href="{html.escape(it["href"])}">{label}</a>')
        if i < len(nav) - 1 and not nav[i + 1].get("spacer"):
            parts.append('<span class="cur">·</span>')
    return '<div class="nav">' + "".join(parts) + "</div>"


def render(md_text, title="問題", nav=None, meta="", mermaid_js=None,
           mermaid_mode="cdn", answer_form=""):
    """Markdown 文字列 → HTML 文字列。

    mermaid_mode:
      cdn   … ふつうの HTML。mermaid は CDN から読む(既定・数十KB)
      embed … mermaid 本体を埋め込む(3.5MB・外部参照ゼロ・オフライン用)
      none  … 図はソースのまま表示(JS を一切入れない)
    mermaid_js: embed 時に使うソース(None なら MERMAID_JS を読む)。
    """
    body, has_mermaid = md_to_body(md_text)
    scripts = ""
    if has_mermaid and mermaid_mode != "none":
        if mermaid_mode == "cdn":
            scripts = (f'<script src="{MERMAID_CDN}"></script>\n'
                       f"<script>{MERMAID_INIT}</script>")
        else:
            js = mermaid_js if mermaid_js is not None else read_mermaid()
            if js:
                scripts = f"<script>{js}</script>\n<script>{MERMAID_INIT}</script>"
    meta_html = f'<div class="meta">{html.escape(meta)}</div>' if meta else ""
    if answer_form:
        body += answer_form
        scripts += "\n<script>" + ANSWER_JS + "</script>"
    return PAGE.format(title=html.escape(title), css=CSS, nav=build_nav(nav),
                       meta=meta_html, body=body, scripts=scripts)


_MERMAID_CACHE = {}


def read_mermaid(path=MERMAID_JS):
    """同梱用 mermaid.min.js を読む(無ければ None=図はソース表示にフォールバック)。"""
    if path in _MERMAID_CACHE:
        return _MERMAID_CACHE[path]
    js = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            js = fh.read()
        # </script> がソース中にあると埋め込みが壊れる(mermaid には現れないが保険)
        js = js.replace("</script>", "<\\/script>")
    else:
        print(f"[render_html] 警告: {path} が無いため図はソース表示になります",
              file=sys.stderr)
    _MERMAID_CACHE[path] = js
    return js


def render_file(in_path, out_path, title=None, nav=None, meta="", mermaid_js=None,
                mermaid_mode="cdn", answer_form=""):
    with open(in_path, encoding="utf-8") as fh:
        text = fh.read()
    assert_not_answer_key(in_path, text)
    if title is None:
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = m.group(1).strip() if m else os.path.basename(in_path)
    out = render(text, title=title, nav=nav, meta=meta, mermaid_js=mermaid_js,
                 mermaid_mode=mermaid_mode, answer_form=answer_form)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out)
    return out_path


# --------------------------------------------------------------------------
# 自己診断: questions/ 全件を描画して構造を機械検分する
# --------------------------------------------------------------------------
def selftest(repo=REPO):
    import glob
    srcs = sorted(glob.glob(f"{repo}/questions/*.md"))
    if not srcs:
        sys.exit("[selftest] questions/*.md が見つかりません")
    outdir = tempfile.mkdtemp(prefix="render_selftest_")
    ng, n_mermaid, n_fence = 0, 0, 0
    sizes = []
    for src in srcs:
        with open(src, encoding="utf-8") as fh:
            text = fh.read()
        body, has_mm = md_to_body(text)
        n_mermaid += 1 if has_mm else 0
        # フェンスの中身が1文字も欠けていないことを確認(show 出力の保全)
        for block in re.findall(r"^```[^\n]*\n(.*?)^```$", text, re.M | re.S):
            n_fence += 1
            if html.escape(block).rstrip("\n") not in body:
                print(f"  NG フェンス欠落: {os.path.basename(src)}")
                ng += 1
                break
        # 選択肢が1つずつカード化されているか。
        # ★原文側の数え上げは CHOICE_RE と別の広い正規表現で行う(同じ式で数えると
        #   A-F 決め打ちのような取りこぼしを検出できない。2026-08-08 に G が落ちた)
        if "## 選択肢" in text:
            sec = text.split("## 選択肢", 1)[1]
            n_ch = body.count('class="choice"')
            n_src = len(re.findall(r"^\*{0,2}([A-Z])[.．)）]\*{0,2}[ \t]*$|"
                                   r"^\*{0,2}([A-Z])[.．)）]\*{0,2}[ \t]+\S",
                                   sec, re.M))
            if n_ch < 2 or n_ch != n_src:
                print(f"  NG 選択肢の分割 {os.path.basename(src)}: "
                      f"HTML {n_ch} 個 / 原文 {n_src} 個")
                ng += 1
        # 未エスケープの生タグが本文に漏れていないか(<br/> は mermaid 内のみ)
        stripped = re.sub(r'<pre class="mermaid">.*?</pre>', "", body, flags=re.S)
        if "<br/>" in stripped:
            print(f"  NG 生タグ漏れ: {os.path.basename(src)}")
            ng += 1
        out = os.path.join(outdir, os.path.basename(src).replace(".md", ".html"))
        render_file(src, out)
        sizes.append(os.path.getsize(out))
    print(f"[selftest] {len(srcs)} 件描画 / mermaid 図あり {n_mermaid} 件 / "
          f"コードフェンス {n_fence} 個 / NG {ng} 件")
    print(f"[selftest] ページサイズ 中央値 {sorted(sizes)[len(sizes) // 2] // 1024}KB "
          f"/ 最大 {max(sizes) // 1024}KB (mermaid=cdn)")
    print(f"[selftest] 出力: {outdir}")
    # 正解キーを弾けることの確認(ガードが生きているか)
    keys = sorted(glob.glob(f"{repo}/answers/*.md"))
    if keys:
        import subprocess
        r = subprocess.run([sys.executable, __file__, "--in", keys[-1],
                            "--out", os.path.join(outdir, "leak.html")],
                           capture_output=True, text=True)
        ok = r.returncode == 3 or "拒否" in (r.stdout + r.stderr)
        print(f"[selftest] 漏洩ガード: {'OK(拒否した)' if ok else 'NG(通してしまった)'}")
        ng += 0 if ok else 1
    return 1 if ng else 0


def main():
    ap = argparse.ArgumentParser(description="問題文 Markdown → 単一ファイル HTML")
    ap.add_argument("--in", dest="src", help="入力 Markdown")
    ap.add_argument("--out", dest="dst", help="出力 HTML")
    ap.add_argument("--title", default=None)
    ap.add_argument("--meta", default="", help="タイトル下の小さな注記")
    ap.add_argument("--nav-json", default=None,
                    help="ナビ定義 JSON([{label,href,current,spacer}])")
    ap.add_argument("--mermaid", choices=MERMAID_MODES, default="cdn",
                    help="図の描画方法(既定 cdn=ふつうのHTML / embed=オフライン用)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())
    if not a.src or not a.dst:
        ap.error("--in と --out は必須(または --selftest)")
    nav = None
    if a.nav_json:
        with open(a.nav_json, encoding="utf-8") as fh:
            nav = json.load(fh)
    print(render_file(a.src, a.dst, title=a.title, nav=nav, meta=a.meta,
                      mermaid_mode=a.mermaid))


if __name__ == "__main__":
    main()
