#!/usr/bin/env python3
"""解説穴埋め形(BL-191) — gen_paper_mcq.py の shape=cloze 素材。

狙い: **問題を解きながら解説を頭に入れる**。1 問 = 書き下ろしの技術解説文 1 本に空欄 ①〜④。
語群 8 語(正解 4 + 対概念の誤答 4)から 1 字ずつ選ぶ。空欄ごとに採点し、4/4 で正解。
採点後に提示する「完成文」がそのまま解説になる。

配管は BL-168 の組合せ形(match)を流用する:
  - 本文中の ［①］〜［④］ マーカーを render_html.blank_terms() が拾い、パックの解答欄が「空欄ごとに記号を 1 つ選ぶ」ラジオになる
    (「対応させる項目」の表は置かない= 解く側に意味が無く本文と語群を遠ざける・2026-09-19 ユーザ指摘)
  - 候補は `## 選択肢` に `A. …`〜`H. …`
  - 正解行は `**①－C、②－A、③－H、④－E**`(match_key_of が読む)。組合せ形と違い**全単射ではない**(未使用の錯乱肢 4 つ)。

知識ベースは topic ごとのモジュール(cloze_kb_<topic>.py)に分離。第 1 弾は MPLS(cloze_kb_mpls.py)。
公開 API は他の KB ファミリと同じ(KINDS/kind_forms/worlds_for/draw/build_match/question_body/answer_body/
pick_count/CORE/TITLES/selftest)。形は match のみ。SPEED_KINDS=[] (瞬発力枠には出さない= 読む量があるため)。THINK_KINDS=[] (パックの専用枠 --cloze で出す)。
"""
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cloze_kb_mpls  # noqa: E402
import cloze_kb_ipv6fhs  # noqa: E402
import cloze_kb_aaa  # noqa: E402
import cloze_kb_order  # noqa: E402
import cloze_kb_svc  # noqa: E402
import cloze_kb_dmvpn  # noqa: E402

TOPICS = {"mpls": cloze_kb_mpls, "ipv6fhs": cloze_kb_ipv6fhs, "aaa": cloze_kb_aaa, "order": cloze_kb_order,
          "svc": cloze_kb_svc, "dmvpn": cloze_kb_dmvpn}   # svc= SNMPv3/NetFlow(BL-202) / dmvpn= Phase 比較+IPsec(BL-203)

PASSAGES = []
for _t, _m in TOPICS.items():
    for _p in _m.PASSAGES:
        _p = dict(_p)
        _p["topic"] = _t
        PASSAGES.append(_p)

ALL_KINDS = sorted({p["kind"] for p in PASSAGES})
# ★範囲外(scope="beyond")の kind は既定の抽選(KINDS/THINK_KINDS)から外す。--kinds で明示したときだけ draw できる。
BEYOND_KINDS = sorted({p["kind"] for p in PASSAGES if p.get("scope") == "beyond"})
KINDS = [k for k in ALL_KINDS if k not in BEYOND_KINDS]
SPEED_KINDS = []                 # 瞬発力枠には載せない
THINK_KINDS = []                 # ★パックに専用の穴埋め枠(gen_pack --cloze・既定 5)を持つので mixed の kbthink 枠には乗せない
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in ALL_KINDS}
FORMS = {k: {"match"} for k in ALL_KINDS}
DIFF = {k: 3 for k in ALL_KINDS}
N_BLANKS = 4
N_POOL = 8                       # 語群の既定サイズ(空欄 4)。空欄 5 以上は 10(A〜J)= 誤答を 4 つ確保(BL-199)
N_POOL_WIDE = 10
CIRC = "①②③④⑤⑥⑦⑧"
LETTERS = "ABCDEFGHIJ"
_NUM_RE = re.compile(r"[0-9][0-9.,:/×x\- ]*(倍|秒|分|バイト|ビット|ms|s)?")


def _is_num(s):
    return bool(_NUM_RE.fullmatch(s.strip()))


def pool_size(p):
    n = min(int(p.get("n_blanks", N_BLANKS)), N_POOL_WIDE - 1)
    return int(p.get("pool_size", N_POOL_WIDE if n >= 5 else N_POOL))

TITLES = {}
for _p in PASSAGES:
    TITLES.setdefault(_p["kind"], _p["title"])

CORE = {}
for _p in PASSAGES:
    # kind → 1 行要約(解答 md の「種別」行に載る)。空欄候補の正解語を並べる。
    CORE.setdefault(_p["kind"], _p["title"] + (f"(世界 {len(_p['worlds'])} 種)" if _p.get("worlds") else "") + " — 要点語: " + " / ".join(
        re.sub(r"\{([a-z_]+)\}", r"<\1>", "|".join(s["a"].values()) if isinstance(s["a"], dict) else s["a"]) for s in _p["slots"].values()))


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


# --------------------------------------------------------------------------
# 置換ユーティリティ
# --------------------------------------------------------------------------
_VAR_RE = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
_SLOT_RE = re.compile(r"«([a-z_][a-z0-9_]*)»")


def _subst_vars(text, vals):
    if not text:
        return text
    return _VAR_RE.sub(lambda m: vals.get(m.group(1), m.group(0)), text)


def _pick(x, world):
    """world 別 dict なら当該 world の値、そうでなければそのまま(BL-195)。"""
    if isinstance(x, dict) and world is not None and world in x:
        return x[world]
    return x


def _draw_vars(p, rnd, world=None):
    vals = {}
    links = p.get("var_links", {})
    idx = {}
    derived = []
    for name, cands in (p.get("vars") or {}).items():
        cands = _pick(cands, world)
        if callable(cands):                       # ★BL-195: 導出値 f(vals, world) -> str。後段でまとめて評価
            derived.append((name, cands))
            continue
        i = rnd.randrange(len(cands))
        idx[name] = i
        vals[name] = cands[i]
    # 連動(同じ添字)。鎖(a→b→c)も効くよう dst の添字を更新しながら順に処理する。
    for src, dst in links.items():
        if src in idx and dst in (p.get("vars") or {}):
            cands = _pick(p["vars"][dst], world)
            idx[dst] = idx[src] % len(cands)
            vals[dst] = cands[idx[dst]]
    for name, fn in derived:
        vals[name] = str(fn(vals, world))
    return vals


def _acceptable(word, slot):
    return word == slot["a"] or word in slot.get("ok", [])


def _build_pool(p, blanks, slots, rnd):
    """語群を作る。正解 n + 残りは誤答。一意性を満たさなければ None。

    ★BL-199(2026-09-20 ユーザ指摘「数字にはデコイが要る」): 数値の正解を持つ空欄には、まず**その空欄専用の
      数値デコイ**を確保する(語群に数字が 1 つしか無いと消去法で埋まる)。残りの枠は空欄を巡回して 1 つずつ配る。
    """
    n = len(blanks)
    size = pool_size(p)
    pool = [slots[b]["a"] for b in blanks]
    if len(set(pool)) != len(pool):
        return None
    blank_slots = [slots[b] for b in blanks]

    def ok_distractor(w):
        if w in pool:
            return False
        return not any(_acceptable(w, s) for s in blank_slots)

    def take_one(b, pred=lambda w: True):
        ds = list(slots[b].get("d", []))
        rnd.shuffle(ds)
        for w in ds:
            if pred(w) and ok_distractor(w):
                pool.append(w)
                return True
        return False

    # 0) ★BL-201(2026-09-20 ユーザ指摘「ORIGIN の順は選択肢が 1 つしか無く消去法で埋まる」):
    #    どの空欄も「その空欄の誤答候補が語群にある」か「同じグループ(grp)の別の空欄がある」のどちらかを満たす。
    #    満たせない空欄が 1 つでもあれば None(別の空欄集合で引き直し)。
    def covered(b):
        s = slots[b]
        if s.get("grp") and any(slots[o].get("grp") == s["grp"] for o in blanks if o != b):
            return True
        return any(w in pool for w in s.get("d", []))
    # 1) 数値の空欄があれば、正解でない数値デコイを語群に最低 1 つ(全数値空欄で共有)
    answers = set(pool)
    for b in blanks:
        if len(pool) >= size:
            break
        if _is_num(slots[b]["a"]) and not any(_is_num(w) and w not in answers for w in pool):
            take_one(b, _is_num)
    # 1b) グループで守られていない空欄 → 専用デコイを 1 つずつ(数値で確保済みなら不要)
    for b in blanks:
        if len(pool) >= size:
            break
        if not covered(b):
            take_one(b)
    # 2) 残りの枠は空欄を(シャッフルして)巡回
    order_b = list(blanks)
    rnd.shuffle(order_b)
    progressed = True
    while len(pool) < size and progressed:
        progressed = False
        for b in order_b:
            if len(pool) >= size:
                break
            if take_one(b):
                progressed = True
    # 3) 足りなければ他スロット(非空欄も含む)の誤答から補う
    if len(pool) < size:
        spare = []
        for sid, s in slots.items():
            spare += list(s.get("d", []))
        rnd.shuffle(spare)
        for w in spare:
            if len(pool) >= size:
                break
            if ok_distractor(w):
                pool.append(w)
    if len(pool) != size:
        return None
    if not all(covered(b) for b in blanks):          # ★消去法で埋まる空欄が残る組は不採用
        return None
    # 最終検査: 各語が「当てはまる空欄」ちょうど 1 つ(正解語)か 0(誤答語)
    for w in pool:
        fits = [b for b in blanks if _acceptable(w, slots[b])]
        if w in pool[:n]:
            if len(fits) != 1:
                return None
        elif fits:
            return None
    return pool


def draw(rnd, kind, world=None, form=None):
    if kind not in ALL_KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    cands = [p for p in PASSAGES if p["kind"] == kind]
    p = rnd.choice(cands)
    worlds = list(p.get("worlds") or [])
    w = (world if world in worlds else rnd.choice(worlds)) if worlds else None
    vals = _draw_vars(p, rnd, w)
    slots = _make_slots(p, vals, w)
    order = _slot_order(p, w)
    keep = set(p.get("keep") or [])
    pickable = [s for s in order if s not in keep]
    n = min(int(p.get("n_blanks", N_BLANKS)), N_POOL_WIDE - 1)  # ★BL-197: passage 単位の空欄数(上限 9)
    if len(pickable) < n:
        raise ValueError(f"{kind}: 空欄候補が {n} 未満")
    pool = None
    for _try in range(120):
        blanks = sorted(rnd.sample(pickable, n), key=order.index)
        pool = _build_pool(p, blanks, slots, rnd)
        if pool:
            break
    if not pool:
        raise ValueError(f"{kind}: 一意な語群を作れない")
    d = {"kind": kind, "world": w or "-", "form": form or "match", "diff": DIFF[kind],
         "topic": p["topic"], "title": p["title"], "passage": p, "vals": vals,
         "slots": slots, "blanks": blanks, "pool": pool}
    return d


def _make_slots(p, vals, w):
    """スロットの文字列に world と変数を反映。他 world の正解語は自動で誤答候補に加える(BL-195)。"""
    worlds = list(p.get("worlds") or [])
    slots = {}
    for sid, s in p["slots"].items():
        a_ = _subst_vars(_pick(s["a"], w), vals)
        ds = [_subst_vars(x, vals) for x in _pick(s.get("d", []), w)]
        if isinstance(s["a"], dict):
            for ow in worlds:
                if ow != w and ow in s["a"]:
                    x = _subst_vars(s["a"][ow], vals)
                    if x != a_ and x not in ds:
                        ds.append(x)
        slots[sid] = {"a": a_, "d": ds, "grp": s.get("grp"),
                      "ok": [_subst_vars(x, vals) for x in _pick(s.get("ok", []), w)],
                      "why": _subst_vars(_pick(s.get("why", ""), w), vals)}
    return slots


def _slot_order(p, w):
    """本文に現れる順のスロット id(空欄番号は出現順)。"""
    body_all = (_pick(p.get("exhibit"), w) or "") + "\n" + _pick(p["text"], w)
    order = []
    for m in _SLOT_RE.finditer(body_all):
        if m.group(1) not in order:
            order.append(m.group(1))
    return order


def _render(text, d, mode):
    """mode: 'q' = 空欄を ［①］ に・他スロットは正解語 / 'a' = 全スロットを **正解語** (空欄は番号付き)"""
    if not text:
        return ""
    text = _subst_vars(text, d["vals"])
    num = {b: CIRC[i] for i, b in enumerate(d["blanks"])}

    def rep(m):
        sid = m.group(1)
        s = d["slots"][sid]
        if sid in num:
            return f"［{num[sid]}］" if mode == "q" else f"**［{num[sid]}］{s['a']}**"
        return s["a"]
    out = _SLOT_RE.sub(rep, text)
    # 和文と和文(全角)の間に残る半角スペースは詰める(「アドレス を使う」→「アドレスを使う」)。
    # 英数字に隣接するスペースはこのリポの表記(「VRF を持ち」)なので残す。
    return re.sub(r"(?<=[^\x00-\x7f]) (?=[^\x00-\x7f])", "", out)


def build_match(d, rnd):
    """(terms, choices, ans) — BL-168 の組合せ形と同じ 3 タプル。"""
    pool = list(d["pool"])
    rnd.shuffle(pool)
    letters = dict(zip(pool, LETTERS))
    terms = [(CIRC[i], f"空欄 {CIRC[i]}") for i in range(len(d["blanks"]))]
    choices = [(LETTERS[i], w) for i, w in enumerate(pool)]
    ans = {CIRC[i]: letters[d["slots"][b]["a"]] for i, b in enumerate(d["blanks"])}
    d["_letters"] = letters
    return terms, choices, dict(sorted(ans.items()))


def _diagram_md(p, d=None):
    dg = p.get("diagram")
    if not dg:
        return ""
    if d is not None:
        dg = _subst_vars(dg, d["vals"])
    return "```mermaid\n" + dg.rstrip("\n") + "\n```"


def question_body(d, choices, form):
    if form != "match":
        raise ValueError("cloze は match のみ")
    terms, ch, _ = choices
    p = d["passage"]
    parts = []
    dg = _diagram_md(p, d)
    if dg:
        parts.append(dg)
    ex = _pick(p.get("exhibit"), d.get("world"))
    if ex:
        if p.get("exhibit_md"):                      # ★Markdown の表などをそのまま出す(BL-198)
            parts.append(_render(ex, d, "q").rstrip("\n"))
        else:
            parts.append("```\n" + _render(ex, d, "q").rstrip("\n") + "\n```")
    parts.append(_render(_pick(p["text"], d.get("world")), d, "q"))
    # ★本文(図・設定例・解説文)は設問の直下に置き、その直後に語群(## 選択肢)が来る並びにする。
    #   「対応させる項目」の表は出さない(解答欄のラジオ行は render_html.blank_terms が ［①］ から作る)。
    last = CIRC[len(d["blanks"]) - 1]
    last_l = LETTERS[len(d["pool"]) - 1]
    ask = (f"次の説明文(設定例を含む)の空欄 ①〜{last} に入る語句を、下の語群 A〜{last_l} から 1 つずつ選択してください。"
           "同じ語句を 2 つの空欄に使うことはありません。語群にはどの空欄にも当てはまらない語句が含まれます。"
           "\n\n" + "\n\n".join(parts))
    ch_md = "\n\n".join(f"{k}. {t}" for k, t in ch)
    return "", ask, ch_md, ""


def answer_body(d, choices, form):
    terms, ch, ans = choices
    p = d["passage"]
    letters = d.get("_letters") or {w: k for k, w in ch}
    L = ["## 正解", "", "**" + "、".join(f"{k}－{v}" for k, v in ans.items()) + "**", "", "## 解説", ""]
    L.append(f"### 完成文: {p['title']}")
    L.append("")
    w = d.get("world")
    if p.get("worlds"):
        desc = (p.get("world_desc") or {}).get(w, w)
        L.append(f"(この盤面の世界: **{desc}** — 同じ kind でも世界が違えば正解が変わる)")
        L.append("")
    ex = _pick(p.get("exhibit"), w)
    if ex:
        if p.get("exhibit_md"):
            L.append(_render(ex, d, "a").rstrip("\n"))
        else:
            L.append("```\n" + _render(ex, d, "a").replace("**", "").rstrip("\n") + "\n```")
        L.append("")
    L.append(_render(_pick(p["text"], w), d, "a"))
    L.append("")
    L.append("### 各空欄の要点")
    L.append("")
    for i, b in enumerate(d["blanks"]):
        s = d["slots"][b]
        L.append(f"- {CIRC[i]} = **{letters[s['a']]}. {s['a']}** — {s['why'] or ''}".rstrip(" —"))
    used = {d["slots"][b]["a"] for b in d["blanks"]}
    rest = [w for w in d["pool"] if w not in used]
    if rest:
        L.append("")
        L.append("### 語群の残り(どの空欄にも入らない)")
        L.append("")
        for w in rest:
            # その語を誤答候補に持つ空欄の why を引く
            why = ""
            for b in d["blanks"]:
                if w in d["slots"][b]["d"]:
                    why = d["slots"][b]["why"]
                    break
            L.append(f"- {letters[w]}. {w}" + (f" — {why}" if why else ""))
    return "\n".join(L)


def pick_count(form, choices):
    return 1


def selftest(seeds=60):
    import random as _r
    ng = n = 0
    bad = {}
    for kind in ALL_KINDS:
        for s in range(seeds):
            n += 1
            try:
                rnd = _r.Random(hash((kind, s)) & 0xFFFFFFFF)
                d = draw(rnd, kind, None, "match")
                terms, ch, ans = build_match(d, rnd)
                n_exp = min(int(d["passage"].get("n_blanks", N_BLANKS)), N_POOL_WIDE - 1)
                assert len(ans) == n_exp, "空欄数"
                assert len(set(ans.values())) == n_exp, "同じ字が 2 空欄"
                pool = [w for _, w in ch]
                size = pool_size(d["passage"])
                assert len(pool) == size and len(set(pool)) == size, "語群の重複/不足"
                # ★BL-201: どの空欄も専用デコイ(自分の d)か同グループの別空欄を持つ(消去法で 1 択にならない)
                for b in d["blanks"]:
                    s_ = d["slots"][b]
                    same = [o for o in d["blanks"] if o != b and s_.get("grp") and d["slots"][o].get("grp") == s_["grp"]]
                    if not same and not any(w in pool for w in s_.get("d", [])):
                        raise AssertionError(f"空欄 {b}(正解「{s_['a'][:20]}」)は語群に専用デコイが無く消去法で埋まる")
                # ★BL-199: 数値の正解には、正解でない数値デコイが語群に少なくとも 1 つ
                answers = {d["slots"][b]["a"] for b in d["blanks"]}
                for b in d["blanks"]:
                    a_ = d["slots"][b]["a"]
                    if _is_num(a_):
                        assert any(_is_num(w) and w not in answers for w in pool), f"数値の空欄 {a_} にデコイが無い"
                for i, b in enumerate(d["blanks"]):
                    fits = [w for w in pool if _acceptable(w, d["slots"][b])]
                    assert fits == [d["slots"][b]["a"]], f"空欄 {CIRC[i]} に当てはまる語が {fits}"
                before, ask, ch_md, terms_md = question_body(d, (terms, ch, ans), "match")
                before = before + "\n" + ask          # 本文は設問側(ask)に入る
                assert "«" not in before and "»" not in before, "未置換スロット"
                assert not _VAR_RE.search(before), f"未置換変数: {_VAR_RE.search(before).group(0)}"
                assert not _VAR_RE.search(answer_body(d, (terms, ch, ans), "match")), "解答側に未置換変数"
                for i in range(n_exp):
                    assert f"［{CIRC[i]}］" in before, f"空欄 {CIRC[i]} が本文にない"
                # 空欄化した正解語が**解説文**の別の場所に素で出ていない(答えの丸見え)。
                #   exhibit(show 出力・設定例)は読解の対象なので正解語が載っていてよい= 検査対象外。
                plain = re.sub(r"［[①-⑧]］", "", _render(_pick(d["passage"]["text"], d.get("world")), d, "q"))
                for b in d["blanks"]:
                    a_ = d["slots"][b]["a"]
                    if len(a_) < 2:
                        continue
                    if re.fullmatch(r"[A-Za-z0-9_.-]+", a_):
                        hit = re.search(r"(?<![A-Za-z0-9_-])" + re.escape(a_) + r"(?![A-Za-z0-9_-])", plain)
                    else:
                        hit = a_ in plain
                    if hit:
                        raise AssertionError(f"正解語「{a_}」が本文に露出")
                a_md = answer_body(d, (terms, ch, ans), "match")
                assert "## 正解" in a_md and "«" not in a_md
                # ★BL-195: 世界が本文(空欄を除いた見える部分)から一意に読めること= 同じ空欄集合で
                #   他 world を描いたとき、見える部分がどこかで違う(違わなければ解答不能)
                pz = d["passage"]
                if pz.get("worlds"):
                    def visible(dd):
                        b_, a_, _, _ = question_body(dd, (terms, ch, ans), "match")
                        return re.sub(r"［[①-⑧]］", "", b_ + a_)
                    me = visible(d)
                    for ow in pz["worlds"]:
                        if ow == d["world"]:
                            continue
                        d2 = dict(d); d2["world"] = ow
                        d2["slots"] = _make_slots(pz, d["vals"], ow)
                        if visible(d2) == me:
                            raise AssertionError(f"世界 {d['world']} と {ow} が本文から区別できない(空欄 {d['blanks']})")
            except (AssertionError, ValueError, KeyError) as exc:
                ng += 1
                bad.setdefault(kind, [0, repr(exc)])[0] += 1
    for k, (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}: {cnt} 件 (例: {ex})")
    print(f"[gen_paper_cloze selftest] {n} 件 / NG {ng}  (範囲内 {len(KINDS)} kind / 範囲外 {len(BEYOND_KINDS)} kind= {BEYOND_KINDS})")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
