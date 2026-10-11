#!/usr/bin/env python3
"""紙面問題の英語版(提示用の訳文)= 置き場と、原文との機械照合(BL-236 ③)。

紙面は生成器が日本語で出す(`questions/<ID>.md`)。英語出題はラボと同じく**提示物だけ**を英訳して行う:
訳文は原文の隣の `en/` に置き(`questions/en/<ID>.md`)、原文・正解キー・採点には一切触れない。
訳すのは出題者(quiz スキル「紙面の英語出題」節)。このモジュールが決めるのは次の 3 つ:

  en_path(src)   … 訳文の置き場(`<原文のディレクトリ>/en/<同名>.md`)
  status(…)      … 訳文を使ってよいか: missing(無い) / ng(原文と食い違う) / ok
  check(ja, en)  … 食い違いの中身(空リスト= 食い違いなし)

パックの描画(gen_pack.write_pages)と解説ページは **status が ok の訳文だけ**を使い、それ以外は日本語の原文で出す
(訳文の不備で解けない・誤採点になる問題を出さない)。

照合が見るのは「訳しても変わってはいけないもの」:
  ・選択肢の記号の並び／選ぶ個数／空欄 ［①］ の集合／対応付けの項目
  ・見出しの階層の並び・表の行(列数)・番号付き項目・箇条書き・引用行の数
  ・コードブロックの数と行数。日本語を含まない行(= show 出力・config・図の配線)は一字一句同じ
  ・数字を含む識別子(アドレス・IF 名・AS 番号・ホスト名・問題 ID …)とインラインコードが訳文に残っている
  ・訳文に日本語の文字が残っていない
見ないもの= 訳の良し悪し・文体(それは訳す側の規約)。数字を含まない識別子(route-map 名など)は
インラインコードかコードブロックに入っている限りで守られる。

単体で使う:
  paper_en.py questions/20261007-015.md …    # 原文(repo 相対)ごとに状態と食い違いを出す。全部 ok なら rc=0
パック単位は `scripts/pack.sh en <PACK-ID>|--today`(gen_pack.cmd_en)。
"""
import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_html  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN_DIR = "en"

# 訳文に残っていてはいけない文字(かな・カナ・漢字・和文の句読点・全角形)。
# 空欄マーカーの ［ ］ だけは構造なので除く。丸数字・矢印・★ などの記号は対象外。
JA_CHAR_RE = re.compile(r"[　-〿぀-ヿ㐀-䶿一-鿿＀-￯]")
_BLANK_BRACKETS = "［］"

# 数字を含む識別子(アドレス・プレフィックス・IF 名・ホスト名・AS 番号・タイマ値・問題 ID …)
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9./:_\-]*")
# 1 桁の数は英語で綴ってよい(3 台 → three routers／第 3 オクテット → the third octet)
_DIGIT_WORDS = {
    "0": ("zero", "no"), "1": ("one", "first", "single", "once", "a", "an", "each"),
    "2": ("two", "second", "both", "twice"), "3": ("three", "third"),
    "4": ("four", "fourth"), "5": ("five", "fifth"), "6": ("six", "sixth"),
    "7": ("seven", "seventh"), "8": ("eight", "eighth"), "9": ("nine", "ninth"),
}
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
CIRCLED_RE = re.compile(r"[①-⑳]")


def en_path(src_path):
    """原文のパス → 訳文のパス(`<dir>/en/<name>.md`)。相対・絶対のどちらでも同じ形で返す。"""
    d, name = os.path.split(src_path)
    return os.path.join(d, EN_DIR, name)


def has_ja(s):
    return any(c not in _BLANK_BRACKETS for c in JA_CHAR_RE.findall(s))


def tokens(s):
    """行から数字を含む識別子を取り出す(末尾の句読点は落とす)。"""
    out = []
    for t in TOKEN_RE.findall(s):
        t = t.rstrip("./:_-")
        if t and any(c.isdigit() for c in t):
            out.append(t)
    return out


def en_tokens(s):
    """訳文側の識別子の集合。英語は「20 ビット」を 20-bit と書くので、ハイフンで割った断片も含める。"""
    out = set()
    for t in tokens(s):
        out.add(t)
        out.update(x.rstrip("./:_") for x in t.split("-") if any(c.isdigit() for c in x))
    return out


def split_fences(text):
    """本文を (フェンス外の行のリスト, [(info, [行…]), …]) に分ける。"""
    prose, fences, cur = [], [], None
    for line in text.split("\n"):
        st = line.lstrip()
        if st.startswith("```") or st.startswith("~~~"):
            if cur is None:
                cur = (st[3:].strip(), [])
            else:
                fences.append(cur)
                cur = None
            continue
        (cur[1] if cur is not None else prose).append(line)
    if cur is not None:              # 閉じ忘れ= 残りを全部フェンスとして数える(照合で数が合わなくなる)
        fences.append(cur)
    return prose, fences


def _shape(prose):
    """フェンス外の行から、訳しても変わらないはずの骨組みを取り出す。"""
    heads = [len(m.group(1)) for l in prose if (m := re.match(r"^(#{1,6})\s", l))]
    rows = [l.count("|") for l in prose if l.lstrip().startswith("|")]
    numbered = sum(1 for l in prose if re.match(r"^\s*\d+[.)]\s", l))
    bullets = sum(1 for l in prose if re.match(r"^\s*[-*+]\s", l))
    quotes = sum(1 for l in prose if l.startswith(">"))
    return heads, rows, numbered, bullets, quotes


def _missing_tokens(ja_line_tokens, en_text_tokens, en_words):
    miss = []
    for t in ja_line_tokens:
        if t in en_text_tokens:
            continue
        if len(t) == 1 and any(w in en_words for w in _DIGIT_WORDS.get(t, ())):
            continue
        miss.append(t)
    return miss


def check(ja, en):
    """原文(ja)と訳文(en)の食い違いを文字列のリストで返す。空なら照合を通る。"""
    out = []
    R = render_html

    # --- 解答欄の形を決めるもの(ここが違うと解けない・誤採点になる) -------------
    jl, el = R.choice_letters(ja), R.choice_letters(en)
    if jl != el:
        out.append(f"選択肢の記号が違う: 原文 {''.join(jl) or '(なし)'} / 訳文 {''.join(el) or '(なし)'}"
                   "(見出しは `## Choices`・記号と順序は原文どおり)")
    jp, ep = R.pick_count(ja), R.pick_count(en)
    if jp != ep:
        out.append(f"選ぶ個数が違う: 原文 {jp} / 訳文 {ep}"
                   "(`(Choose two.)`・数非明示は `(Choose all that apply.)`。-1 = 数非明示)")
    jb = collections.Counter(R.BLANK_RE.findall(ja))
    eb = collections.Counter(R.BLANK_RE.findall(en))
    if jb != eb:
        out.append(f"空欄 ［n］ が違う: 原文 {dict(jb)} / 訳文 {dict(eb)}(マーカーは ［①］ のまま写す)")
    jm = [k for k, _ in R.match_terms(ja)]
    em = [k for k, _ in R.match_terms(en)]
    if jm != em:
        out.append(f"対応付け・空欄の項目が違う: 原文 {''.join(jm)} / 訳文 {''.join(em)}"
                   "(対応付けの表の見出しは `### Items to Match`)")
    jc, ec = set(CIRCLED_RE.findall(ja)), set(CIRCLED_RE.findall(en))
    if jc != ec:
        out.append(f"丸数字が違う: 原文 {''.join(sorted(jc))} / 訳文 {''.join(sorted(ec))}")

    # --- 骨組み -------------------------------------------------------------
    jprose, jf = split_fences(ja)
    eprose, ef = split_fences(en)
    for name, a, b in zip(("見出しの階層の並び", "表の行と列数", "番号付き項目の数", "箇条書きの数", "引用行の数"),
                          _shape(jprose), _shape(eprose)):
        if a != b:
            out.append(f"{name}が違う: 原文 {a} / 訳文 {b}")

    # --- コードブロック ------------------------------------------------------
    if len(jf) != len(ef):
        out.append(f"コードブロックの数が違う: 原文 {len(jf)} / 訳文 {len(ef)}")
    for i, ((jinfo, jlines), (einfo, elines)) in enumerate(zip(jf, ef), 1):
        if jinfo != einfo:
            out.append(f"コードブロック {i}: 種別が違う(原文 `{jinfo}` / 訳文 `{einfo}`)")
        if len(jlines) != len(elines):
            out.append(f"コードブロック {i}: 行数が違う(原文 {len(jlines)} / 訳文 {len(elines)})")
            continue
        for n, (a, b) in enumerate(zip(jlines, elines), 1):
            if has_ja(a):
                miss = _missing_tokens(tokens(a), en_tokens(b), set(re.findall(r"[a-z]+", b.lower())))
                if miss:
                    out.append(f"コードブロック {i} の {n} 行目: 識別子が落ちている {miss}: {b.strip()[:70]}")
            elif a.rstrip() != b.rstrip():
                out.append(f"コードブロック {i} の {n} 行目: 日本語を含まない行は原文どおりに写す: "
                           f"原文 `{a.strip()[:60]}` / 訳文 `{b.strip()[:60]}`")

    # --- 識別子(フェンス外) ---------------------------------------------------
    etok = en_tokens("\n".join(eprose))
    ewords = set(re.findall(r"[a-z]+", "\n".join(eprose).lower()))
    miss = []
    for l in jprose:
        for t in _missing_tokens(tokens(l), etok, ewords):
            if t not in miss:
                miss.append(t)
    if miss:
        out.append(f"本文の識別子・数値が訳文に無い: {miss}(数は数字のまま書く。1 桁の数だけは綴ってよい)")
    ecode = set(INLINE_CODE_RE.findall("\n".join(eprose)))
    lost = []
    for l in jprose:
        for c in INLINE_CODE_RE.findall(l):
            if not has_ja(c) and c not in ecode and c not in lost:
                lost.append(c)
    if lost:
        out.append(f"インラインコードが訳文に無い: {lost}")

    # --- 日本語の残り ---------------------------------------------------------
    left = []
    for n, l in enumerate(en.split("\n"), 1):
        if has_ja(l):
            left.append(f"{n} 行目 `{l.strip()[:50]}`")
    if left:
        out.append("訳文に日本語の文字(かな・漢字・全角の句読点や括弧)が残っている: " + " / ".join(left[:6])
                   + (f" ほか {len(left) - 6} 行" if len(left) > 6 else ""))
    return out


def status(repo, src):
    """(状態, 食い違いのリスト)。状態= missing / ng / ok。src は repo 相対の原文。"""
    ja_path = os.path.join(repo, src)
    e_path = en_path(ja_path)
    if not os.path.exists(ja_path) or not os.path.exists(e_path):
        return "missing", []
    with open(ja_path, encoding="utf-8") as fh:
        ja = fh.read()
    with open(e_path, encoding="utf-8") as fh:
        en = fh.read()
    problems = check(ja, en)
    return ("ng" if problems else "ok"), problems


def presented(repo, src, lang="en"):
    """その問題を画面に出す時に使うソース(repo 相対)。英語版が照合を通っていれば英語版、でなければ原文。"""
    if not src or lang != "en":
        return src
    st, _ = status(repo, src)
    return en_path(src) if st == "ok" else src


STATUS_JA = {"ok": "OK", "missing": "未訳", "ng": "要修正"}


def report(repo, srcs, log=print):
    """原文のリストについて状態を出す。全部 ok なら True。"""
    all_ok = True
    for label, src in srcs:
        st, problems = status(repo, src)
        all_ok = all_ok and st == "ok"
        log(f"  {label:<4} {STATUS_JA[st]:<4} {src}  →  {en_path(src)}")
        for p in problems:
            log(f"         - {p}")
    return all_ok


def main():
    ap = argparse.ArgumentParser(description="紙面問題の英語版を原文と照合する")
    ap.add_argument("src", nargs="+", help="原文(repo 相対。例: questions/20261007-015.md)")
    ap.add_argument("--repo", default=REPO)
    a = ap.parse_args()
    ok = report(os.path.abspath(a.repo), [("", s) for s in a.src])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
