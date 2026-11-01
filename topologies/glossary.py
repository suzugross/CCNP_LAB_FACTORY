#!/usr/bin/env python3
"""用語集(BL-260) — 読み物の本文の専門用語に、カーソル(スマホはタップ)で説明を出す。用語集ページも同じ辞書から作る。

読み物ビルダー(gen_reading.py)が使う部品。原稿の Markdown には何も書き足さない: ビルド時に、できあがった HTML の本文から
辞書の語を拾って <span class="gl" data-g="<id>"> で包む。本文に目印は付けない(合図はカーソルの形だけ)。

辞書 — <repo>/glossary/*.yml(全教材で共通の 1 つ。分野ごとのファイルに分けてよい)＋ 本ごとの <src>/glossary.yml(任意):

    - id: evi                          # 英小文字・数字・ハイフン。全辞書で一意
      term: EVI                        # 見出し語。日英で違えば {en: …, ja: …}
      full: {en: EVPN instance, ja: EVPN インスタンス}   # 略語の正式名(任意)。日英同じなら文字列
      aka: [EVPN instances]            # 本文で拾う別の表記(任意)。見出し語と正式名は書かなくても拾う
      def:                             # 1〜3 文。`code` と **太字** が使える
        en: One E-Line or E-LAN service in EVPN …
        ja: EVPN の 1 つのサービスを表す番号。…
      see: [evpn, vrf]                 # 関連語の id(任意)
      books: [xr]                      # この本(book.yml の key)だけで拾う(任意)。同じ略語が本によって別の意味の時
      scope: ["b*-m11-*"]              # このページ(ファイル名の glob)だけで拾う(任意)。単元をまたぐと別物になる表記用

拾う規則:
  - 拾わない場所: pre・code・見出し・リンク・ボタン・図(svg)・ナビ・囲みのラベル・設定例の見出し(figcaption/summary)
  - 最長一致(「EVPN-VPWS」が登録されていれば「EVPN」より先に取る)
  - 英数字で始まる/終わる表記は、前後に英数字が続かないこと(「L2VPN」の中の「VPN」は拾わない)。ハイフンでつながった
    英数字も同じ語の一部とみなす(「RR-LINK」の「RR」・「PE-CE」の「PE」は拾わない。拾いたい複合語はその形で登録する)
  - 大文字だけの表記は大文字小文字を区別、小文字を含む表記は区別しない。英語の複数形(PEs・route targets・communities)も拾う
  - 表記の中の空白は、日本語の側ではあってもなくてもよい(「ルート ターゲット」=「ルートターゲット」)。原稿の改行も空白として扱い、
    日本語の文字どうしの間に原稿の改行が入っていても拾う(「疑似回線の\nラベル」)
  - 太字などの書式の境目はまたがない(「**種類 1** の経路」の「種類 1 の経路」は拾えない)

検査: python3 topologies/gen_reading.py glossary [--src <本> [--unknown]]
"""
import fnmatch
import glob
import html
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSSARY_DIR = os.path.join(REPO, "glossary")
LANGS = ("en", "ja")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

WORDS = {
    "ja": {"glossary": "用語集", "back": "‹ 目次", "see": "関連", "more": "用語集で開く →", "pages": "出てくるページ",
           "filter": "絞り込み(語・説明)", "none": "該当する語はありません。",
           "lead": "この本に出てくる専門用語 {n} 語。本文の語にカーソルを合わせると(スマホはタップすると)、ここと同じ説明が出ます。",
           "lead_bundle": "この 1 枚に出てくる専門用語 {n} 語。"},
    "en": {"glossary": "Glossary", "back": "‹ Contents", "see": "See also", "more": "Open in the glossary →",
           "pages": "Appears in", "filter": "Filter (term or text)", "none": "No matching terms.",
           "lead": "{n} technical terms used in this book. Hover over a term in the text (tap it on a phone) to see the same note.",
           "lead_bundle": "{n} technical terms used in this file."},
}


# --------------------------------------------------------------------------
# 辞書を読む
# --------------------------------------------------------------------------
def _by_lang(value):
    """文字列なら両方の言語に同じ値、{en, ja} ならそのまま(片方だけならもう片方へも写す)。"""
    if value is None:
        return None
    if isinstance(value, dict):
        v = {l: str(value[l]).strip() for l in LANGS if value.get(l)}
        if not v:
            return None
        for l in LANGS:
            v.setdefault(l, next(iter(v.values())))
        return v
    return {l: str(value).strip() for l in LANGS}


def inline(s):
    """説明文の小さな記法(`code` と **太字**)を HTML に。"""
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)


def _strip_inline(s):
    return re.sub(r"\*\*|`", "", s)


class Glossary:
    def __init__(self, entries, problems):
        self.entries = entries                  # id → 整えた項目
        self.problems = problems                # 読み込み時に見つけた不備(検査で出す)
        self._cache = {}

    # 本・ページで使う語だけの照合器
    def applies(self, e, book, page_file):
        """その本・そのページで拾う語か。page_file が None(どのページでもない所)では scope 付きの語は拾わない。"""
        if e["books"] and book not in e["books"]:
            return False
        if e["scope"] and (page_file is None or not any(fnmatch.fnmatch(page_file, g) for g in e["scope"])):
            return False
        return True

    def for_book(self, book):
        return [e for e in self.entries.values() if not e["books"] or book in e["books"]]

    def matcher(self, book, page_file):
        ids = tuple(sorted(i for i, e in self.entries.items() if self.applies(e, book, page_file)))
        if ids not in self._cache:
            self._cache[ids] = Matcher([self.entries[i] for i in ids])
        return self._cache[ids]

    def closure(self, ids):
        """使った語＋その関連語(1 段)。並びは英語の見出し語の順。"""
        out = set(i for i in ids if i in self.entries)
        for i in list(out):
            out.update(k for k in self.entries[i]["see"] if k in self.entries)
        return sorted(out, key=lambda i: self.entries[i]["_sort"])


def _files(src=None):
    paths = sorted(glob.glob(os.path.join(GLOSSARY_DIR, "*.yml")))
    if src and os.path.exists(os.path.join(src, "glossary.yml")):
        paths.append(os.path.join(src, "glossary.yml"))
    return paths


def load(src=None):
    """全教材の辞書＋本ごとの辞書を読んで 1 つにする。"""
    import yaml
    entries, problems = {}, []
    for path in _files(src):
        rel = os.path.relpath(path, REPO)
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or []
        if not isinstance(data, list):
            problems.append(f"{rel}: 項目の並び(YAML のリスト)になっていない")
            continue
        for k, raw in enumerate(data):
            where = f"{rel} #{k + 1}"
            gid = str((raw or {}).get("id") or "")
            if not ID_RE.match(gid):
                problems.append(f"{where}: id {gid!r} が書式に合わない(英小文字・数字・ハイフン)")
                continue
            if gid in entries:
                problems.append(f"{where}: id {gid} が重複({entries[gid]['_from']} と)")
                continue
            term, full = _by_lang(raw.get("term")), _by_lang(raw.get("full"))
            defs = raw.get("def") if isinstance(raw.get("def"), dict) else {}
            if not term:
                problems.append(f"{where} ({gid}): term が無い")
                continue
            for l in LANGS:
                if not str(defs.get(l) or "").strip():
                    problems.append(f"{where} ({gid}): def.{l} が無い")
            forms = []
            for f in list(term.values()) + list((full or {}).values()) + [str(a) for a in raw.get("aka") or []]:
                f = re.sub(r"\s+", " ", f).strip()
                if f and f not in forms:
                    forms.append(f)
            entries[gid] = {
                "id": gid, "term": term, "full": full,
                "def": {l: " ".join(str(defs.get(l) or defs.get("en") or defs.get("ja") or "").split()) for l in LANGS},
                "see": [str(s) for s in raw.get("see") or []],
                "books": [str(b) for b in raw.get("books") or []],
                "scope": [str(s) for s in raw.get("scope") or []],
                "_forms": forms, "_sort": term["en"].casefold(), "_from": rel,
            }
    for e in entries.values():
        for s in e["see"]:
            if s not in entries:
                problems.append(f"{e['_from']} ({e['id']}): see の {s} が辞書に無い")
    # 同じ表記を 2 つの項目が持つと、どちらに当たるかが辞書の並びで決まってしまう
    owner = {}
    for e in entries.values():
        for f in e["_forms"]:
            key = re.sub(r"\s+", "", f).casefold()
            other = owner.get(key)
            if other and other != e["id"] and _overlap(entries[other], e):
                problems.append(f"表記 {f!r} が {other} と {e['id']} の両方にある")
            owner.setdefault(key, e["id"])
    return Glossary(entries, problems)


def _overlap(a, b):
    """2 つの項目が同じ本・同じページで同時に効きうるか(books・scope で分けてあれば衝突ではない)。"""
    if a["books"] and b["books"] and not set(a["books"]) & set(b["books"]):
        return False
    if a["scope"] and b["scope"] and not set(a["scope"]) & set(b["scope"]):
        return False
    return True


# --------------------------------------------------------------------------
# 照合
# --------------------------------------------------------------------------
def _is_ascii_alnum(c):
    return c.isascii() and c.isalnum()


def _form_re(form):
    """1 つの表記 → 正規表現(本文は HTML のエスケープ済みの文字なので、表記もエスケープしてから合わせる)。"""
    pieces = re.split(r"( )", form)
    out = []
    for k, p in enumerate(pieces):
        if p == " ":
            a, b = pieces[k - 1][-1:], pieces[k + 1][:1]
            out.append(r"\s+" if _is_ascii_alnum(a) and _is_ascii_alnum(b) else r"\s*")
        else:
            # 日本語の文字どうしの間は、原稿の改行(行の折り返し)があっても拾う
            chars = [re.escape(html.escape(c, quote=True)) for c in p]
            out.append("".join(c + (r"\n?" if j + 1 < len(p) and not p[j].isascii() and not p[j + 1].isascii() else "")
                               for j, c in enumerate(chars)))
    body = "".join(out)
    if re.search(r"[^aeiou]y$", form):                     # 英語の複数形(community → communities)
        body = body[:-1] + r"(?:y|ies)"
    elif _is_ascii_alnum(form[-1]):
        body += r"(?:es|s)?" if re.search(r"[a-z]$", form) else r"s?"
    if re.search(r"[a-z]", form):
        body = f"(?i:{body})"
    # 前後に英数字が続かないこと。ハイフンでつながった英数字も同じ語の一部とみなす(RR-LINK の RR・PE-CE の PE は拾わない)
    if _is_ascii_alnum(form[0]):
        body = r"(?<![A-Za-z0-9_])(?<![A-Za-z0-9]-)" + body
    if _is_ascii_alnum(form[-1]):
        body += r"(?![A-Za-z0-9_]|-[A-Za-z0-9])"
    return body


class Matcher:
    def __init__(self, entries):
        forms = sorted(((f, e["id"]) for e in entries for f in e["_forms"]), key=lambda x: -len(x[0]))
        self.ids = [i for _, i in forms]
        self.re = re.compile("|".join(f"({_form_re(f)})" for f, _ in forms)) if forms else None

    def sub(self, text, hit):
        if not self.re:
            return text

        def rep(m):
            gid = self.ids[m.lastindex - 1]
            hit(gid)
            return f'<span class="gl" data-g="{gid}">{m.group(0)}</span>'

        return self.re.sub(rep, text)

    def ids_in(self, text):
        return [self.ids[m.lastindex - 1] for m in self.re.finditer(text)] if self.re else []


# 本文を拾わない要素
SKIP_TAGS = {"pre", "code", "kbd", "samp", "a", "h1", "h2", "h3", "h4", "h5", "h6", "button", "svg", "script",
             "style", "title", "textarea", "select", "nav", "summary", "figcaption", "input"}
SKIP_CLASSES = {"tag", "tolab", "portal", "pager", "langsw", "rnav", "gl", "glossary-sec"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_TOKEN = re.compile(r"<!--.*?-->|<(script|style)\b[^>]*>.*?</\1\s*>|<[^>]+>", re.S | re.I)
_TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)")


def annotate(page_html, matcher, lang):
    """本文の語を包む。(HTML, [(id, 言語, 目印)])。目印= 直前の節の data-sec(s2-1 など)か、束ね版のページの錨(pg3)。
    2 版を持つページは div.lv[data-l] の中ごとに言語を切り替えて数える。
    matcher は Matcher か、ページの番号(束ね版の錨 pg<n> の n。錨より前は None)→ Matcher の関数(ページごとの scope 用)。"""
    pick = matcher if callable(matcher) else (lambda _k: matcher)
    out, hits = [], []
    pos, skip, depth, in_body = 0, None, 0, False
    cur = {"lang": lang, "mark": "", "page": None}
    hit = lambda gid: hits.append((gid, cur["lang"], cur["mark"]))
    for m in _TOKEN.finditer(page_html):
        text = page_html[pos:m.start()]
        if text:
            out.append(pick(cur["page"]).sub(text, hit) if in_body and not skip and text.strip() else text)
        tok = m.group(0)
        out.append(tok)
        pos = m.end()
        if m.group(1) or tok.startswith("<!--"):
            continue
        t = _TAG.match(tok)
        if not t:
            continue
        closing, name = t.group(1) == "/", t.group(2).lower()
        if not closing:
            if name == "body":
                in_body = True
            lv = re.search(r'class="lv" data-l="(\w+)"', tok)
            if lv:
                cur.update(lang=lv.group(1), mark="")
            sec = re.search(r'\sdata-sec="([^"]+)"', tok)
            if sec:
                cur["mark"] = sec.group(1)
            pg = re.match(r'<a id="pg(\d+)"', tok)
            if pg:
                cur.update(mark=f"pg{pg.group(1)}", page=int(pg.group(1)))
        if skip:
            if name == skip:
                if closing:
                    depth -= 1
                    if not depth:
                        skip = None
                elif not tok.endswith("/>"):
                    depth += 1
            continue
        if closing or name in VOID or tok.endswith("/>"):
            continue
        cls = re.search(r'\bclass="([^"]*)"', tok)
        if name in SKIP_TAGS or (cls and SKIP_CLASSES & set(cls.group(1).split())):
            skip, depth = name, 1
    out.append(page_html[pos:])
    return "".join(out), hits


# --------------------------------------------------------------------------
# 吹き出し(ページに埋め込む辞書と JS)
# --------------------------------------------------------------------------
def popup_data(gl, ids, href):
    """そのページで使う語(＋関連語)だけを JSON で埋め込む。href= 用語集ページ(束ね版は "" = 同じ 1 枚の中)。"""
    data = {}
    for i in gl.closure(ids):
        e = gl.entries[i]
        data[i] = {"t": e["term"], "f": e["full"] or {}, "d": {l: inline(e["def"][l]) for l in LANGS},
                   "s": [k for k in e["see"] if k in gl.entries]}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="gl-data" data-href="{html.escape(href)}">{js}</script>'


GLOSS_CSS = """
/* ---- 用語集の吹き出し(BL-260)。本文の語に目印は付けない。合図はカーソルの形だけ ---- */
@media (hover:hover) and (pointer:fine){ .gl{ cursor:help; } }
@media (hover:none){ .gl{ cursor:pointer; -webkit-tap-highlight-color:transparent; } }   /* iOS はこれが無いとタップが届かない */
.gl.on{ background:#fff1b8; border-radius:2px; box-decoration-break:clone; -webkit-box-decoration-break:clone; }
#glpop{ position:fixed; z-index:60; box-sizing:border-box; width:max-content; max-width:min(24rem, calc(100vw - 16px));
  min-width:min(13rem, calc(100vw - 16px));
  background:#fff; color:#111; border:1px solid #c3c9d2; border-radius:7px; box-shadow:0 6px 24px rgba(20,30,45,.18);
  padding:.6rem .8rem .5rem; font-size:.86rem; line-height:1.75; letter-spacing:0; text-align:left; }
#glpop[hidden]{ display:none; }
#glpop .gp-h{ display:flex; flex-wrap:wrap; align-items:baseline; gap:.1rem .6rem; margin:0 0 .2rem; }
#glpop .gp-h b{ font-size:.96rem; }
#glpop .gp-f{ color:#5b6676; font-size:.8rem; }
#glpop .gp-s{ margin-top:.4rem; font-size:.8rem; color:#5b6676; }
#glpop .gp-s span{ margin-right:.25rem; }
#glpop .gp-m{ margin-top:.3rem; font-size:.8rem; text-align:right; }
#glpop code{ font-size:.84em; }
"""

GLOSS_JS = r"""
(function(){
  var el = document.getElementById('gl-data'); if(!el) return;
  var G; try{ G = JSON.parse(el.textContent); }catch(_e){ return; }
  var HREF = el.getAttribute('data-href') || '';
  var W = {ja: {more: '用語集で開く →', see: '関連'}, en: {more: 'Open in the glossary →', see: 'See also'}};
  var fine = !!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches);
  var pop = null, anchor = null, pinned = false, tShow = null, tHide = null, hoverEl = null;
  function lang(){
    var l = (document.body.getAttribute('data-lang') || document.documentElement.lang || 'ja').slice(0, 2);
    return l === 'en' ? 'en' : 'ja';
  }
  function pick(o, l){ return !o ? '' : (o[l] || o.en || o.ja || ''); }
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function make(){
    pop = document.createElement('div'); pop.id = 'glpop'; pop.hidden = true; pop.setAttribute('role', 'dialog');
    document.body.appendChild(pop);
    pop.addEventListener('mouseenter', function(){ clearTimeout(tHide); });
    pop.addEventListener('mouseleave', function(){ if(!pinned) hideSoon(); });
    pop.addEventListener('click', function(e){
      var s = e.target.closest('[data-see]');
      /* 中身を差し替えると押した要素が外れ、文書側の「外側を押した」判定に掛かるので、ここで止める */
      if(s){ e.preventDefault(); e.stopPropagation(); fill(s.getAttribute('data-see')); pinned = true; place(); return; }
      if(e.target.closest('.gp-m a')) setTimeout(hide, 0);
    });
  }
  function fill(id){
    var g = G[id]; if(!g) return;
    var l = lang(), w = W[l], t = pick(g.t, l);
    /* 正式名。日本語版では英語の正式名も添える(英語の語も覚えられるように) */
    var subs = [pick(g.f, l), l === 'ja' ? pick(g.f, 'en') : ''].filter(function(x, i, a){ return x && x !== t && a.indexOf(x) === i; });
    var h = '<div class="gp-h"><b>' + esc(t) + '</b>' + (subs.length ? '<span class="gp-f">' + esc(subs.join(' / ')) + '</span>' : '') + '</div>'
          + '<div class="gp-d">' + pick(g.d, l) + '</div>';
    var see = (g.s || []).filter(function(k){ return G[k]; });
    if(see.length) h += '<div class="gp-s"><span>' + w.see + '</span>' + see.map(function(k){
      return '<a href="#g-' + k + '" data-see="' + k + '">' + esc(pick(G[k].t, l)) + '</a>'; }).join(' · ') + '</div>';
    h += '<div class="gp-m"><a>' + w.more + '</a></div>';
    pop.innerHTML = h;
    var more = pop.querySelector('.gp-m a');
    more.setAttribute('href', HREF + '#g-' + id);   /* 束ね版の外部参照の検査に掛からないよう後から付ける */
    if(HREF && window.top !== window.self) more.target = '_blank';   /* ワークスペースの枠の中では別タブ(読んでいた位置を残す) */
  }
  function place(){
    if(!anchor || !pop || pop.hidden) return;
    var rs = anchor.getClientRects(), r = rs.length ? rs[0] : anchor.getBoundingClientRect();
    var vw = document.documentElement.clientWidth, vh = window.innerHeight, m = 8;
    if(r.bottom < 0 || r.top > vh){ hide(); return; }
    pop.style.left = '0px'; pop.style.top = '0px';
    var pw = pop.offsetWidth, ph = pop.offsetHeight, top = r.bottom + 6;
    if(top + ph > vh - m && r.top - 6 - ph >= m) top = r.top - 6 - ph;      /* 下に入らなければ上に出す */
    pop.style.left = Math.max(m, Math.min(r.left, vw - pw - m)) + 'px';
    pop.style.top = top + 'px';
  }
  function show(g, pin){
    if(!pop) make();
    clearTimeout(tShow); clearTimeout(tHide);
    if(anchor && anchor !== g) anchor.classList.remove('on');
    anchor = g; pinned = !!pin;
    fill(g.getAttribute('data-g'));
    pop.hidden = false; g.classList.add('on'); place();
  }
  function hide(){
    clearTimeout(tShow); clearTimeout(tHide);
    if(pop) pop.hidden = true;
    if(anchor) anchor.classList.remove('on');
    anchor = null; pinned = false;
  }
  function hideSoon(){ clearTimeout(tHide); tHide = setTimeout(hide, 250); }
  if(fine){
    /* カーソルを語の上に 0.35 秒置くと出す。スクロールで語がカーソルの下に来ただけ(動きが 0)では出さない */
    document.addEventListener('mousemove', function(e){
      if(e.movementX === 0 && e.movementY === 0) return;
      var g = e.target.closest ? e.target.closest('.gl') : null;
      if(g === hoverEl) return;
      hoverEl = g; clearTimeout(tShow);
      if(g){ clearTimeout(tHide); if(anchor !== g) tShow = setTimeout(function(){ show(g, false); }, 350); }
      else if(anchor && !pinned && !(pop && pop.contains(e.target))) hideSoon();
    });
  }
  /* クリック(スマホはタップ)で出して固定する。もう一度押すか、外側を押すと閉じる */
  document.addEventListener('click', function(e){
    var g = e.target.closest ? e.target.closest('.gl') : null;
    if(g){
      var sel = window.getSelection && window.getSelection();
      if(sel && !sel.isCollapsed && sel.toString()) return;          /* 文字を選んでいる時は邪魔しない */
      if(anchor === g && pinned){ hide(); return; }
      show(g, true); return;
    }
    if(pop && !pop.hidden && !pop.contains(e.target)) hide();
  });
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') hide(); });
  window.addEventListener('scroll', place, {passive: true});
  window.addEventListener('resize', place);
  if(window.MutationObserver) new MutationObserver(hide).observe(document.body, {attributes: true, attributeFilter: ['data-lang']});
})();
"""


# --------------------------------------------------------------------------
# 用語集ページ・束ね版の末尾の節
# --------------------------------------------------------------------------
def collect(hits_by_page):
    """[(ページの番号, [(id, 言語, 目印)])] → {id: {ページの番号: [目印(重複なし・出た順)]}}。"""
    refs = {}
    for i, hits in hits_by_page:
        for gid, _lang, mark in hits:
            marks = refs.setdefault(gid, {}).setdefault(i, [])
            if mark not in marks:
                marks.append(mark)
    return refs


def _letter(e):
    c = e["_sort"][:1].upper()
    return c if "A" <= c <= "Z" else "#"


def _short(s, n=26):
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def entries_html(gl, ids, refs, lang, page_ref, prefix):
    """語の一覧(頭文字ごと)。page_ref(ページの番号, 目印の並び, lang) → 逆引きの HTML。prefix= id の頭(版ごとに重ならないように)。"""
    w = WORDS[lang]
    groups = {}
    for i in ids:
        groups.setdefault(_letter(gl.entries[i]), []).append(i)
    order = sorted(groups, key=lambda c: (c != "#", c))
    az = "".join(f'<a href="#{prefix}L-{c}">{"0–9" if c == "#" else c}</a>' for c in order)
    out = [f'<nav class="gl-az">{az}</nav>', '<div class="gl-list">']
    for c in order:
        out.append(f'<div class="gl-grp" id="{prefix}L-{c}"><div class="gl-letter">{"0–9" if c == "#" else c}</div>')
        for i in groups[c]:
            e = gl.entries[i]
            t = e["term"][lang]
            subs = [x for x in dict.fromkeys([(e["full"] or {}).get(lang), (e["full"] or {}).get("en") if lang == "ja" else None])
                    if x and x != t]
            key = " ".join([*e["term"].values(), *(e["full"] or {}).values(), *e["_forms"],
                            *map(_strip_inline, e["def"].values())]).casefold()
            see = [k for k in e["see"] if k in ids]
            rows = [f'<p class="gh"><b>{html.escape(t)}</b>'
                    + (f' <span class="gf">{html.escape(" / ".join(subs))}</span>' if subs else "") + "</p>",
                    f'<p class="gd">{inline(e["def"][lang])}</p>']
            if see:
                rows.append(f'<p class="gs"><span class="glbl">{w["see"]}</span> ' + " · ".join(
                    f'<a href="#{prefix}{k}">{html.escape(gl.entries[k]["term"][lang])}</a>' for k in see) + "</p>")
            pages = refs.get(i) or {}
            if pages:
                rows.append(f'<p class="gr"><span>{w["pages"]}</span> '
                            + " · ".join(page_ref(p, marks, lang) for p, marks in sorted(pages.items())) + "</p>")
            out.append(f'<div class="gle" id="{prefix}{i}" data-gid="{i}" data-k="{html.escape(key)}">' + "".join(rows) + "</div>")
        out.append("</div>")
    out.append(f'<p class="gl-none" hidden>{w["none"]}</p></div>')
    return "\n".join(out)


def page_md(gl, ids, refs, lang, page_ref):
    """用語集ページ(1 言語ぶん)の Markdown。生 HTML の塊は空行を入れずに 1 つで通す。"""
    w = WORDS[lang]
    return (f'<p class="portal"><a href="index.html">{w["back"]}</a></p>\n\n# {w["glossary"]}\n\n'
            f'<p class="lead">{w["lead"].format(n=len(ids))}</p>\n\n'
            f'<div class="glp">\n<div class="gl-tools"><input type="search" class="gl-q" placeholder="{w["filter"]}" '
            f'aria-label="{w["filter"]}"></div>\n' + entries_html(gl, ids, refs, lang, page_ref, f"g-{lang}-") + "\n</div>\n")


def bundle_section(gl, ids, refs, lang, page_ref):
    """束ね版の末尾に付ける用語集の節(1 枚の中で完結。id は g-<id>= 吹き出しの「用語集で開く」の行き先)。"""
    w = WORDS[lang]
    return (f'<hr class="bsep">\n<section class="glossary-sec glp" id="glossary"><h2>{w["glossary"]}</h2>\n'
            f'<p class="lead">{w["lead_bundle"].format(n=len(ids))}</p>\n'
            + entries_html(gl, ids, refs, lang, page_ref, "g-") + "\n</section>\n")


GLOSS_PAGE_CSS = """
/* ---- 用語集ページ(BL-260) ---- */
.glp{ margin:1.6rem 0 0; line-height:1.75; }
.glp .gl-tools{ position:sticky; top:0; z-index:5; background:#fff; padding:.5rem 0 .4rem; }
.glp .gl-q{ width:100%; box-sizing:border-box; font:inherit; font-size:.95rem; padding:.45rem .7rem;
  border:1px solid #b9c0ca; border-radius:6px; }
.glp .gl-az{ display:flex; flex-wrap:wrap; gap:.15rem .25rem; margin:.4rem 0 1rem; font-size:.86rem; }
.glp .gl-az a{ display:inline-block; min-width:1.6rem; text-align:center; padding:.1rem .25rem; border:1px solid #d5dae1;
  border-radius:4px; text-decoration:none; }
.glp .gl-letter{ font-weight:700; font-size:1.05rem; color:#2c3540; border-bottom:1px solid #c9ced6; margin:1.6rem 0 .6rem;
  padding-bottom:.2rem; }
.glp .gle{ margin:0 0 1.1rem; padding:.15rem 0 .15rem .8rem; border-left:3px solid #d5dae1; scroll-margin-top:4.5rem; }
.glp .gle:target, .glp .gle.hit{ border-left-color:#d4a72c; background:#fffbea; }
.glp .gle p{ margin:.1rem 0; }
.glp .gh b{ font-size:1.02rem; }
.glp .gf{ color:#5b6676; font-size:.86rem; margin-left:.3rem; }
.glp .gs, .glp .gr{ font-size:.86rem; color:#5b6676; }
.glp .glbl{ font-weight:600; margin-right:.3rem; }
.glp .gr a{ white-space:nowrap; }
.glp .gr .gsec{ font-size:.8rem; }
.glp .gr .gsec a{ color:#5b6676; margin-left:.15rem; }
.glp .gl-grp[hidden], .glp .gle[hidden]{ display:none; }
"""

GLOSS_PAGE_JS = r"""
(function(){
  function lang(){ var l = (document.body.getAttribute('data-lang') || document.documentElement.lang || 'ja').slice(0, 2); return l === 'en' ? 'en' : 'ja'; }
  function root(){ return document.querySelector('.lv[data-l="' + lang() + '"]') || document; }
  function filter(q){
    var r = root(), any = false;
    q = (q || '').trim().toLowerCase();
    r.querySelectorAll('.gl-grp').forEach(function(g){
      var n = 0;
      g.querySelectorAll('.gle').forEach(function(e){ var ok = !q || e.getAttribute('data-k').indexOf(q) >= 0; e.hidden = !ok; if(ok) n++; });
      g.hidden = !n; if(n) any = true;
    });
    var none = r.querySelector('.gl-none'); if(none) none.hidden = any;
  }
  document.querySelectorAll('.gl-q').forEach(function(inp){ inp.addEventListener('input', function(){ filter(inp.value); }); });
  /* #g-<id>(吹き出しの「用語集で開く」)は、いま表示中の版の項目へ送る */
  function go(){
    var m = /^#g-([a-z0-9-]+)$/.exec(location.hash); if(!m) return;
    var e = root().querySelector('.gle[data-gid="' + m[1] + '"]'); if(!e) return;
    var inp = root().querySelector('.gl-q'); if(inp && inp.value){ inp.value = ''; filter(''); }
    document.querySelectorAll('.gle.hit').forEach(function(x){ x.classList.remove('hit'); });
    e.classList.add('hit'); e.scrollIntoView({block: 'start'});
  }
  window.addEventListener('hashchange', go);
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
"""


# --------------------------------------------------------------------------
# 検査と候補探し
# --------------------------------------------------------------------------
_FENCE_BLOCK = re.compile(r"^(```|:::topo|:::config).*?^(```|:::)[ \t]*$", re.S | re.M)


def _prose(md):
    """原稿から地の文だけを残す(コードの囲み・図・設定例・インラインのコード・見出し・リンクの宛先を落とす)。"""
    md = _FENCE_BLOCK.sub("", md)
    md = re.sub(r"`[^`\n]+`", " ", md)
    md = re.sub(r"(?m)^#+ .*$", "", md)
    md = re.sub(r"\]\([^)]*\)", "]", md)
    return re.sub(r"\*\*", "\x00", md)        # 太字の境目は本番と同じく語をまたがせない


def check(src=None, unknown=False, load_book=None):
    """辞書の検査。src(本のソース)を渡すと、その本の本文に出る語の数も数える(load_book= gen_reading.load_book)。"""
    gl = load(src)
    print(f"[glossary] {len(gl.entries)} 語({', '.join(os.path.relpath(p, REPO) for p in _files(src)) or '辞書なし'})")
    for p in gl.problems:
        print(f"  ★ {p}")
    if not src:
        return 1 if gl.problems else 0
    meta = load_book(src)
    counts, words = {}, {}
    for p in meta["pages"]:
        m = gl.matcher(meta["key"], p["file"])
        for path in filter(None, [p["_path"], p.get("_alt_path")]):
            with open(path, encoding="utf-8") as fh:
                text = html.escape(_prose(fh.read()), quote=True)
            for i in m.ids_in(text):
                counts[i] = counts.get(i, 0) + 1
            if unknown:
                # 大文字の略語(末尾が英字。XR01・CE1 のような機器名や Loopback0 のような名前は落とす)
                for w in re.findall(r"(?<![A-Za-z0-9_-])[A-Z][A-Z0-9]*[A-Z](?:-[A-Z0-9]*[A-Z])*(?![A-Za-z0-9_])", text):
                    words.setdefault(w, set()).add(p["file"])
    used = [e for e in gl.for_book(meta["key"])]
    print(f"[glossary] {meta['key']}: 本に効く {len(used)} 語のうち、本文に出る {len(counts)} 語")
    zero = [e["id"] for e in used if e["id"] not in counts]
    if zero:
        print(f"  本文に出てこない語: {' '.join(zero)}")
    if unknown:
        known = set()
        for e in gl.entries.values():
            known.update(re.sub(r"s$", "", f) for f in e["_forms"])
            known.update(e["_forms"])
        cand = sorted(((w, pages) for w, pages in words.items() if w not in known and w.rstrip("s") not in known
                       and len(pages) >= 2), key=lambda x: (-len(x[1]), x[0]))
        print(f"[glossary] 辞書に無く、2 ページ以上に出る略語 {len(cand)} 個(多い順):")
        for w, pages in cand[:120]:
            print(f"  {w:16} {len(pages):3} ページ")
    return 1 if gl.problems else 0


