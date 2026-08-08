#!/usr/bin/env python3
"""OSPFv3 マルチエリア prefix-list 紙面ファミリ (BL-097) — gen_paper_mcq.py の
shape=ospfv3pl 素材。

ユーザ手組みラボ「OSPFv3 Prefix-List exam」(2026-08-07) から発案。マルチエリア
OSPFv3 のエリア間フィルタを、prefix-list の包含判定(16進の繰り上がり・
ヘクステット中間マスク /44〜/47・ge/le)を軸に問う。挙動は全て実機確定表
(poc/ospfv3-pl/README.md・iol-xe 17.15)の写像モデルから決定的に生成:

  - area X filter-list out  → X 発の Type-3 を全他エリアで遮断(in は当該エリアのみ)
  - distribute-list in(内部) → RIB のみ(LSDB は残る)
  - distribute-list in(ABR)  → ★Type-3 origination ごと停止(下流からも消える)
  - area range               → 明細抑止+集約1本(not-advertise で両方なし)
  - filter-list は intra-area に効かない
  - ge/le は厳密に len < ge ≤ le(len 同値は投入自体が拒否される)
  - permit ::/0 単体 → デフォルトのみマッチ(inter-area 全滅)

盤面: R2(ABR) をハブに R1(Area a1)・Ra(Area 0・Lo×4=2001:DB8:h:h::/64)・
R3(Area a2)。第3ヘクステットは 8〜F の連続4値を seed 抽選し、
/45⇄/46⇄/47 の1bit差で被覆が反転する層を常設する。
"""

import copy

# 現在状態の型(壊れ方・盤面の見せ方)
KINDS = ["none", "mask_off", "le_missing", "le_off", "tail_default",
         "seq_shadow", "dir_swap", "dl_abr",
         "block_off", "mask_narrow", "dual_swap"]
# 要件世界: 制約が正解の手段を反転させる
WORLDS = ["area10_only", "hide_all", "rib_only", "summarize", "suppress_all",
          "dual_select"]
# kind ごとに成立する世界(現在状態が「その世界の要件への失敗した試み」になる組)
VALID_WORLDS = {
    "none": list(WORLDS),
    "mask_off": ["area10_only", "hide_all", "rib_only", "summarize",
                 "suppress_all", "dual_select"],
    "le_missing": ["area10_only", "dual_select"],
    "le_off": ["area10_only", "dual_select"],
    "tail_default": ["hide_all", "rib_only"],
    "seq_shadow": ["hide_all", "rib_only", "dual_select"],
    "dir_swap": ["area10_only", "hide_all"],
    "dl_abr": ["rib_only"],
    "block_off": ["area10_only", "dual_select"],     # 範囲ずれ(隣の/47ブロック)
    "mask_narrow": ["area10_only", "dual_select"],   # 狭すぎ(/48で片割れ欠け)
    "dual_swap": ["dual_select"],                    # 方向逆(in/outの取り違え)
}
PL_POOL = ["PL10", "PL-AREA10", "PL-TYPE3", "PL-LO", "PL-CORE", "PL01"]

# ノード役割は固定(トポロジ図と対応): R2=ABR / R1=対象エリア / R3=第3エリア / Ra=Area0
NODES = ["R1", "R2", "R3", "Ra"]


# --------------------------------------------------------------------------
# プレフィックス表現: (val, plen)。val は 2001:DB8::/32 配下の 128bit 整数。
# --------------------------------------------------------------------------
def v6(h3, h4=0):
    return (0x2001 << 112) | (0x0DB8 << 96) | (h3 << 80) | (h4 << 64)


def fmt(h3, h4, plen):
    if plen == 0:
        return "::/0"
    if h4:
        return f"2001:DB8:{h3:X}:{h4:X}::/{plen}"
    return f"2001:DB8:{h3:X}::/{plen}"


def fmt_v(val, plen):
    h3 = (val >> 80) & 0xFFFF
    h4 = (val >> 64) & 0xFFFF
    return fmt(h3, h4, plen)


def block_base(h, plen):
    """h を含む /plen(44〜48)ブロックの第3ヘクステット先頭値。"""
    return h & ~((1 << (48 - plen)) - 1) & 0xFFFF


def ent_matches(ent, route):
    """prefix-list エントリ1個の一致判定(実機規則の写像)。
    ent=(action, b3, b4, plen, ge, le) / route=(val, rlen)。"""
    _a, b3, b4, plen, ge, le = ent
    val, rlen = route
    if (val >> (128 - plen)) != (v6(b3, b4) >> (128 - plen)):
        return False
    if ge is None and le is None:
        return rlen == plen
    lo = ge if ge is not None else plen
    hi = le if le is not None else (128 if ge is not None else plen)
    if ge is not None and le is None:
        hi = 128
    if ge is None and le is not None:
        lo = plen
    return lo <= rlen <= hi


def pl_permit(st, name, route):
    """先勝ち+暗黙 deny。未定義参照は生成しない(実機挙動が未測のため)。"""
    for ent in st["pls"][name]:
        if ent_matches(ent, route):
            return ent[0] == "permit"
    return False


# --------------------------------------------------------------------------
# 盤面モデル
#   経路の生成元: Area 0 = Lo×4 + リンク網(0:A) / Area a1 = 1:1, 2:2 /
#                 Area a2 = 3:3。すべて /64。
#   st = {"fl": (area, "in"|"out", pl名)|None, "dl": ("R1"|"R2", pl名)|None,
#         "range": (plen, notadv)|None, "pls": {名: [ent]}}
# --------------------------------------------------------------------------
# リンク網の第3/第4ヘクステットは draw で毎回抽選する(d["lnk"])。
# 第3ヘクステットは 0..7(主役 Lo の 8..F 帯とマスク衝突しない)に制限。
LNK_KEYS = ["a1", "a1b", "a0", "a2"]   # R2-R1 / R1セカンダリ / R2-Ra / R2-R3

MET_LO, MET_LINK, MET_AGG = 21, 20, 21    # 実測メトリック


def empty_state():
    return {"fl": [], "dl": None, "range": None, "pls": {}}


def _origins(d):
    """[(area_key, val, plen, metric)] area_key ∈ {"0","a1","a2"}。"""
    out = [("0", v6(h, h), 64, MET_LO) for h in d["los"]]
    out.append(("0", v6(*d["lnk"]["a0"]), 64, MET_LINK))
    out.append(("a1", v6(*d["lnk"]["a1"]), 64, MET_LINK))
    out.append(("a1", v6(*d["lnk"]["a1b"]), 64, MET_LINK))
    out.append(("a2", v6(*d["lnk"]["a2"]), 64, MET_LINK))
    return out


def model(d, st):
    """全観測点の状態を返す:
    {"t1": {(val,plen): met}(R1 の OI), "t3": 同(R3), "lsdb1": set(R1 へ流入する
    Type-3 の (val,plen)), "r2_lost": set(dl で R2 RIB から消えた O ルート)}。"""
    ranged = set()
    agg = None
    if st["range"]:
        plen, notadv = st["range"]
        base = block_base(d["s"], plen)
        bmask = v6(base, 0) >> (128 - plen)
        # ★実機忠実: range は Area 0 の全生成元(リンク網含む)を範囲で畳む
        for area, val, vplen, _m in _origins(d):
            if area == "0" and (val >> (128 - plen)) == bmask:
                ranged.add(val)
        if not notadv:
            agg = (v6(base, 0), plen, MET_AGG)
    r2_lost = set()
    if st["dl"] and st["dl"][0] == "R2":
        for area, val, plen, _m in _origins(d):
            # dl は OSPF 学習ルート(O)のみに効く(C には効かない)。
            # R2 の O = 他ルータ発 = Lo×4 と 2:2(1:1/0:A/3:3 は R2 の C)。
            if (val, plen) in [(v6(h, h), 64) for h in d["los"]] \
                    or (val, plen) == (v6(*d["lnk"]["a1b"]), 64):
                if not pl_permit(st, st["dl"][1], (val, plen)):
                    r2_lost.add((val, plen))

    def into(dest):
        out = {}
        for area, val, plen, met in _origins(d):
            if area == dest:
                continue
            if (val, plen) in [(v, 64) for v in ranged] and area == "0":
                continue                       # range に畳まれた明細
            if (val, plen) in r2_lost:
                continue                       # ★ABR の dl は origination を止める
            drop = False
            for fa, fdir, fname in st["fl"]:
                if fdir == "out" and fa == area \
                        and not pl_permit(st, fname, (val, plen)):
                    drop = True
                if fdir == "in" and fa == dest \
                        and not pl_permit(st, fname, (val, plen)):
                    drop = True
            if drop:
                continue
            out[(val, plen)] = met
        if agg:
            aval, aplen, amet = agg
            ok = True
            for fa, fdir, fname in st["fl"]:
                if fdir == "out" and fa == "0" \
                        and not pl_permit(st, fname, (aval, aplen)):
                    ok = False
                if fdir == "in" and fa == dest \
                        and not pl_permit(st, fname, (aval, aplen)):
                    ok = False
            if ok:
                out[(aval, aplen)] = amet
        return out

    lsdb1 = set(into("a1"))
    t1 = dict(into("a1"))
    if st["dl"] and st["dl"][0] == "R1":
        t1 = {r: m for r, m in t1.items() if pl_permit(st, st["dl"][1], r)}
    return {"t1": t1, "t3": into("a2"), "lsdb1": lsdb1, "r2_lost": r2_lost}


def baseline(d):
    return model(d, empty_state())


# --------------------------------------------------------------------------
# 抽選
# --------------------------------------------------------------------------
def _widen(d, h):
    """h だけを狙ったつもりで巻き添えを生む最小の広げマスク(/47→/46→/45)。
    巻き添え(盤面の Lo に実在する余分な一致)が出る最初の長さを返す。"""
    for plen in (47, 46, 45):
        base = block_base(h, plen)
        cover = [x for x in d["los"]
                 if block_base(x, plen) == base]
        if len(cover) >= 2:
            return plen
    return 44                                   # /44 は全 Lo を含む


def _widen_pair(d):
    """pair(/47 の2本)を狙ったつもりで巻き添えが実際に出る広げマスク。
    /46 のブロックが pair と一致してしまう配置では /45 (以深)まで広げる。"""
    want = {d["pair"], d["pair"] + 1}
    for plen in (46, 45, 44):
        base = block_base(d["pair"], plen)
        cover = {x for x in d["los"] if block_base(x, plen) == base}
        if cover > want:
            return plen
    raise ValueError("ospfv3pl: pair の巻き添えマスクが構成できない")


def draw(rnd, kind=None, world=None):
    d = {"shape": "ospfv3pl"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["world"] = world or rnd.choice(VALID_WORLDS[d["kind"]])
    if d["world"] not in VALID_WORLDS[d["kind"]]:
        raise ValueError(f"ospfv3pl: kind={d['kind']} と world={d['world']} は非互換")
    d["proc"] = rnd.choice([1, 10, 100])
    d["a1"] = rnd.choice([10, 1, 5, 11])        # 対象エリア(R1)
    d["a2"] = rnd.choice([20, 2, 50, 30])       # 第3エリア(R3)
    while d["a2"] == d["a1"]:
        d["a2"] = rnd.choice([20, 2, 50, 30])
    s = rnd.choice([8, 9, 0xA, 0xB, 0xC])       # 連続4値の先頭(16進繰り上がり帯)
    d["s"] = s
    d["los"] = [s, s + 1, s + 2, s + 3]
    d["minlen"] = 46 if s % 4 == 0 else 45      # 4本の最小被覆プレフィックス長
    pairs = [h for h in d["los"] if h % 2 == 0 and h + 1 in d["los"]]
    d["pair"] = rnd.choice(pairs)               # W1/W6 の「届ける2本」(= /47 で括れる)
    d["target"] = rnd.choice(d["los"])          # W2/W3 の単一対象
    d["keep_links"] = rnd.random() < 0.4        # W1: リンク網も維持する変種
    # リンク網は毎回抽選(第3ヘクステットは 0..7=Lo 帯 8..F の外・4本相互に重複なし)
    lk_pool = [(h3, h4) for h3 in range(0, 8) for h4 in range(0, 16)]
    d["lnk"] = dict(zip(LNK_KEYS, rnd.sample(lk_pool, 4)))
    if d["world"] == "dual_select":
        # 両掛け: in=pair 配布 / out=pair 内の1本を全域停止。リンク網は in で明示維持
        d["target"] = rnd.choice([d["pair"], d["pair"] + 1])
        d["keep_links"] = True
    d["pl_live"] = rnd.choice(PL_POOL)
    # 正解の permit 形の表面: le 64 / ge 64 le 64 (等価・実測 P8b)
    d["le_style"] = rnd.choice(["le", "gele"])
    # le_missing/le_off の表面: le なし / le 63 (どちらも /64 を拾えない)
    d["noLe_style"] = rnd.choice(["none", "le63"])
    _decoys(d, rnd)
    verify_choices(d)
    return d


def _decoys(d, rnd):
    """未参照の prefix-list を 2〜3 個(生きた参照は最大1本)。"""
    names = [x for x in PL_POOL if x != d["pl_live"]]
    rnd.shuffle(names)
    cover = block_base(d["s"], d["minlen"])
    pool = [
        # 正しく見える未参照リスト(最も意地悪)
        (names[0], [("permit", cover, 0, d["minlen"], None, 64)]),
        # 対象 /64 をピンポイントに(未参照)
        (names[1], [("permit", d["target"], d["target"], 64, None, None)]),
        # ::/0 ge 1(デフォルト以外の全部・実測 P10)の残骸
        (names[2], [("permit", 0, 0, 0, 1, None)]),
    ]
    d["ghosts"] = rnd.sample(pool, rnd.randint(2, 3))


# --------------------------------------------------------------------------
# エントリ組み立て(正解/誤答の list 本体)
# --------------------------------------------------------------------------
def _tail64(d):
    """permit 形の長さ指定(正解面): le 64 or ge 64 le 64(等価)。"""
    return (None, 64) if d["le_style"] == "le" else (64, 64)


def ents_pair(d, plen=47, good=True, base=None):
    """W1/W6: pair を許可(+keep_links ならリンク網 /64 も)。base 指定で範囲ずれ形。"""
    base = base if base is not None else block_base(d["pair"], plen)
    ge, le = _tail64(d) if good else (
        (None, None) if d["noLe_style"] == "none" else (None, 63))
    ents = [("permit", base, 0, plen, ge, le)]
    if d["keep_links"]:
        ents.append(("permit",) + d["lnk"]["a0"] + (64, None, None))
        ents.append(("permit",) + d["lnk"]["a2"] + (64, None, None))
    return ents


def ents_deny_one(d, h=None, plen=64, tail_le=128):
    """deny 形: 対象を deny + permit ::/0 le 128(tail_le=None で le なしの罠形)。"""
    h = h if h is not None else d["target"]
    base = block_base(h, plen) if plen < 64 else h
    ents = [("deny", base, h if plen == 64 else 0, plen,
             None, 64 if plen < 64 else None)]
    ents.append(("permit", 0, 0, 0, None, tail_le))
    return ents


def ents_shadow(d):
    """seq 影: 広い permit が先・deny が死に文。"""
    return [("permit", 0, 0, 0, None, 128),
            ("deny", d["target"], d["target"], 64, None, None)]


def ents_cover(d, plen=None):
    base = block_base(d["s"], plen or d["minlen"])
    ge, le = _tail64(d)
    return [("permit", base, 0, plen or d["minlen"], ge, le)]


def ents_denyall(d):
    base = block_base(d["s"], d["minlen"])
    return [("deny", base, 0, d["minlen"], None, 64),
            ("permit", 0, 0, 0, None, 128)]


# --------------------------------------------------------------------------
# 現在状態(kind → st)
# --------------------------------------------------------------------------
STOP_PL = "PL-STOP"                          # dual の out 側リスト名(現在状態用)


def _dual_state(d, in_ents, out_shadow=False):
    """dual 盤面: in=配布リスト(P) + out=全域停止リスト(PL-STOP)。"""
    st = empty_state()
    P = d["pl_live"]
    st["fl"] = [("0", "out", STOP_PL), ("a1", "in", P)]
    st["pls"][P] = in_ents
    st["pls"][STOP_PL] = (ents_shadow(d) if out_shadow
                          else ents_deny_one(d))
    return st


def state(d):
    k, w = d["kind"], d["world"]
    P = d["pl_live"]
    a1 = "a1"                                    # 内部キー(番号は CLI 描画時に変換)
    if w == "dual_select" and k != "none":
        if k == "mask_off":
            st = _dual_state(d, ents_pair(d, plen=_widen_pair(d)))
        elif k in ("le_missing", "le_off"):
            if k == "le_off":
                d["noLe_style"] = "le63"
            st = _dual_state(d, ents_pair(d, good=False))
        elif k == "block_off":                   # 範囲ずれ: 隣の /47 ブロック
            st = _dual_state(d, ents_pair(d, base=d["pair"] ^ 2))
        elif k == "mask_narrow":                 # 狭すぎ: 停止対象の /48 のみ
            st = _dual_state(d, ents_pair(d, plen=48, base=d["target"]))
        elif k == "dual_swap":                   # 方向逆: 2枚の適用先を取り違え
            st = empty_state()
            P = d["pl_live"]
            st["fl"] = [("0", "out", P), ("a1", "in", STOP_PL)]
            st["pls"][P] = ents_pair(d)
            st["pls"][STOP_PL] = ents_deny_one(d)
        else:                                    # seq_shadow: out 側が死に文
            st = _dual_state(d, ents_pair(d), out_shadow=True)
        for name, ents in d["ghosts"]:
            st["pls"].setdefault(name, ents)
        return st
    st = empty_state()
    if k == "none":
        pass
    elif k == "mask_off":
        if w == "area10_only":
            st["fl"] = [(a1, "in", P)]
            st["pls"][P] = ents_pair(d, plen=_widen_pair(d))
        elif w == "hide_all":
            st["fl"] = [("0", "out", P)]
            st["pls"][P] = ents_deny_one(d, plen=_widen(d, d["target"]))
        elif w == "rib_only":
            st["dl"] = ("R1", P)
            st["pls"][P] = ents_deny_one(d, plen=_widen(d, d["target"]))
        elif w == "summarize":
            st["range"] = (d["minlen"] + 1, False)
        else:                                    # suppress_all
            st["range"] = (d["minlen"] + 1, True)
    elif k in ("le_missing", "le_off"):          # area10_only
        st["fl"] = [(a1, "in", P)]
        st["pls"][P] = ents_pair(d, good=False)
        if k == "le_off":
            d["noLe_style"] = "le63"
            st["pls"][P] = ents_pair(d, good=False)
    elif k == "tail_default":
        ents = ents_deny_one(d, tail_le=None)    # permit ::/0(le なし)
        if w == "hide_all":
            st["fl"] = [("0", "out", P)]
        else:
            st["dl"] = ("R1", P)
        st["pls"][P] = ents
    elif k == "seq_shadow":
        if w == "hide_all":
            st["fl"] = [("0", "out", P)]
        else:
            st["dl"] = ("R1", P)
        st["pls"][P] = ents_shadow(d)
    elif k == "dir_swap":
        if w == "area10_only":                   # in のつもりで out
            st["fl"] = [("0", "out", P)]
            st["pls"][P] = ents_pair(d)
        else:                                    # hide_all: out のつもりで in
            st["fl"] = [(a1, "in", P)]
            st["pls"][P] = ents_deny_one(d)
    elif k == "dl_abr":                          # rib_only: R1 のつもりで R2
        st["dl"] = ("R2", P)
        st["pls"][P] = ents_deny_one(d)
    elif k == "block_off":                       # area10_only: 隣ブロックを許可
        st["fl"] = [(a1, "in", P)]
        st["pls"][P] = ents_pair(d, base=d["pair"] ^ 2)
    elif k == "mask_narrow":                     # area10_only: /48 で片割れ欠け
        st["fl"] = [(a1, "in", P)]
        st["pls"][P] = ents_pair(d, plen=48, base=d["pair"])
    for name, ents in d["ghosts"]:
        st["pls"].setdefault(name, ents)
    return st


# --------------------------------------------------------------------------
# 修正候補(絶対状態)・要件適合
# --------------------------------------------------------------------------
CAND_KEYS = {
    "area10_only": ["fl_in_ok", "fl_in_mask", "fl_in_noLe", "fl_out_pair",
                    "dl_r1_pair"],
    "hide_all": ["fl_out_ok", "fl_out_mask", "fl_in_target", "dl_r2_target",
                 "fl_out_taildef"],
    "rib_only": ["dl_r1_ok", "dl_r1_mask", "fl_in_target", "dl_r2_target",
                 "dl_r1_taildef"],
    "summarize": ["range_ok", "range_nonmin", "range_noncover", "fl_in_cover",
                  "range_na_wrong"],
    "suppress_all": ["range_na_ok", "fl_out_all", "range_adv_wrong",
                     "dl_r2_all", "range_na_noncover"],
    "dual_select": ["dual_ok", "in_only", "out_only", "dual_swapped",
                    "dual_in_mask"],
}


def apply_cand(d, key):
    """候補 key の最終状態(現在状態から独立の絶対状態)。ghost は残置される。"""
    st = empty_state()
    a1 = "a1"                                    # 内部キー
    N, N2 = "PL-NEW", "PL-STOP2"
    if key == "fl_in_ok":
        st["fl"] = [(a1, "in", N)]
        st["pls"][N] = ents_pair(d)
    elif key == "fl_in_mask":
        st["fl"] = [(a1, "in", N)]
        st["pls"][N] = ents_pair(d, plen=_widen_pair(d))
    elif key == "fl_in_noLe":
        st["fl"] = [(a1, "in", N)]
        st["pls"][N] = ents_pair(d, good=False)
    elif key == "fl_out_pair":
        st["fl"] = [("0", "out", N)]
        st["pls"][N] = ents_pair(d)
    elif key == "dl_r1_pair":
        st["dl"] = ("R1", N)
        st["pls"][N] = ents_pair(d)
    elif key == "fl_out_ok":
        st["fl"] = [("0", "out", N)]
        st["pls"][N] = ents_deny_one(d)
    elif key == "fl_out_mask":
        st["fl"] = [("0", "out", N)]
        st["pls"][N] = ents_deny_one(d, plen=_widen(d, d["target"]))
    elif key == "fl_in_target":
        st["fl"] = [(a1, "in", N)]
        st["pls"][N] = ents_deny_one(d)
    elif key == "dl_r2_target":
        st["dl"] = ("R2", N)
        st["pls"][N] = ents_deny_one(d)
    elif key == "fl_out_taildef":
        st["fl"] = [("0", "out", N)]
        st["pls"][N] = ents_deny_one(d, tail_le=None)
    elif key == "dual_ok":
        st["fl"] = [("0", "out", N2), (a1, "in", N)]
        st["pls"][N] = ents_pair(d)
        st["pls"][N2] = ents_deny_one(d)
    elif key == "in_only":
        st["fl"] = [(a1, "in", N)]
        st["pls"][N] = ents_pair(d)
    elif key == "out_only":
        st["fl"] = [("0", "out", N2)]
        st["pls"][N2] = ents_deny_one(d)
    elif key == "dual_swapped":
        st["fl"] = [("0", "out", N), (a1, "in", N2)]
        st["pls"][N] = ents_pair(d)              # 役割逆転: 配布リストを out へ
        st["pls"][N2] = ents_deny_one(d)
    elif key == "dual_in_mask":
        st["fl"] = [("0", "out", N2), (a1, "in", N)]
        st["pls"][N] = ents_pair(d, plen=_widen_pair(d))
        st["pls"][N2] = ents_deny_one(d)
    elif key == "dl_r1_ok":
        st["dl"] = ("R1", N)
        st["pls"][N] = ents_deny_one(d)
    elif key == "dl_r1_mask":
        st["dl"] = ("R1", N)
        st["pls"][N] = ents_deny_one(d, plen=_widen(d, d["target"]))
    elif key == "dl_r1_taildef":
        st["dl"] = ("R1", N)
        st["pls"][N] = ents_deny_one(d, tail_le=None)
    elif key == "range_ok":
        st["range"] = (d["minlen"], False)
    elif key == "range_nonmin":
        st["range"] = (d["minlen"] - 1, False)
    elif key == "range_noncover":
        st["range"] = (d["minlen"] + 1, False)
    elif key == "fl_in_cover":
        st["fl"] = [(a1, "in", N)]
        st["pls"][N] = ents_cover(d)
    elif key == "range_na_wrong":
        st["range"] = (d["minlen"], True)
    elif key == "range_na_ok":
        st["range"] = (d["minlen"], True)
    elif key == "range_adv_wrong":
        st["range"] = (d["minlen"], False)
    elif key == "fl_out_all":
        st["fl"] = [("0", "out", N)]
        st["pls"][N] = ents_denyall(d)
    elif key == "dl_r2_all":
        st["dl"] = ("R2", N)
        st["pls"][N] = ents_denyall(d)
    elif key == "range_na_noncover":
        st["range"] = (d["minlen"] + 1, True)
    else:
        raise KeyError(key)
    for name, ents in d["ghosts"]:
        st["pls"].setdefault(name, ents)
    return st


def _mech(key):
    for m in ("fl_in", "fl_out", "dl_r1", "dl_r2", "range_na", "range"):
        if key.startswith(m):
            return m
    raise KeyError(key)


def _works(d, st):
    """機能要件(観測される表)への適合。世界ごとの goal と厳密比較。"""
    m = model(d, st)
    b = baseline(d)
    los = {(v6(h, h), 64) for h in d["los"]}
    t1, t3 = set(m["t1"]), set(m["t3"])
    b1, b3 = set(b["t1"]), set(b["t3"])
    if m["r2_lost"]:
        return False                             # R2 自身の RIB は常に不可侵
    w = d["world"]
    if w == "area10_only":
        want = {(v6(h, h), 64) for h in (d["pair"], d["pair"] + 1)}
        if d["keep_links"]:
            want |= {(v6(*d["lnk"]["a0"]), 64), (v6(*d["lnk"]["a2"]), 64)}
        return t1 == want and t3 == b3
    tgt = (v6(d["target"], d["target"]), 64)
    if w == "dual_select":
        want = {(v6(h, h), 64) for h in (d["pair"], d["pair"] + 1)} - {tgt}
        want |= {(v6(*d["lnk"]["a0"]), 64), (v6(*d["lnk"]["a2"]), 64)}
        return t1 == want and t3 == b3 - {tgt}
    if w == "hide_all":
        return t1 == b1 - {tgt} and t3 == b3 - {tgt}
    if w == "rib_only":
        return t1 == b1 - {tgt} and t3 == b3
    if w == "summarize":
        aggs = [r for r in t1 if r[1] < 64]
        return (len(aggs) == 1 and not (t1 & los)
                and all(block_base(h, aggs[0][1])
                        == (aggs[0][0] >> 80) & 0xFFFF for h in d["los"])
                and t1 - set(aggs) == b1 - los and t3 - set(aggs) == b3 - los)
    if w == "suppress_all":
        return t1 == b1 - los and t3 == b3 - los
    raise KeyError(w)


def _complies(d, key):
    """制約要件(手段の縛り)への適合。"""
    w = d["world"]
    if w == "dual_select":
        return True                              # works が全て決める
    m = _mech(key)
    if w == "area10_only":
        return m != "dl_r1"                      # 全ルータへ等しく適用の縛り
    if w == "rib_only":
        return m == "dl_r1"                      # LSDB 維持+他ルータ不可侵
    if w == "summarize":
        return not key.endswith("nonmin")        # 最長プレフィックス(最小範囲)
    if w == "suppress_all":
        return m.startswith("range")             # prefix-list 新設の禁止
    return True                                  # hide_all は works が全て決める


def verify_choices(d):
    works, ok = [], []
    for key in CAND_KEYS[d["world"]]:
        st = apply_cand(d, key)
        if _works(d, st):
            works.append(key)
            if _complies(d, key):
                ok.append(key)
    if len(ok) != 1:
        raise ValueError(f"ospfv3pl 一意性違反: kind={d['kind']} "
                         f"world={d['world']} s={d['s']:X} works={works} ok={ok}")
    d["_correct_key"] = ok[0]
    d["_works"] = works
    if _works(d, state(d)):
        raise ValueError(f"ospfv3pl: kind={d['kind']}/{d['world']} が壊れていない")
    if d["world"] == "dual_select" and d["kind"] != "none":
        _verify_patch(d)


# --------------------------------------------------------------------------
# CLI 描画(状態収束形: 現在の適用・リストの削除込み)
# --------------------------------------------------------------------------
def ent_cli(name, seq, ent):
    act, b3, b4, plen, ge, le = ent
    s = f"ipv6 prefix-list {name} seq {seq} {act} {fmt(b3, b4, plen)}"
    if ge is not None:
        s += f" ge {ge}"
    if le is not None:
        s += f" le {le}"
    return s


def _af_lines(d, inner):
    return ([f"router ospfv3 {d['proc']}", "address-family ipv6 unicast"]
            + inner)


def area_num(d, key):
    """内部エリアキー → 実エリア番号。"""
    return {"0": 0, "a1": d["a1"], "a2": d["a2"]}[key]


def _fl_line(d, fl, no=False):
    fa, fdir, fname = fl
    return (("no " if no else "")
            + f"area {area_num(d, fa)} filter-list prefix {fname} {fdir}")


def _range_line(d, rng, no=False):
    plen, notadv = rng
    base = block_base(d["s"], plen)
    return (("no " if no else "") + f"area 0 range {fmt(base, 0, plen)}"
            + (" not-advertise" if notadv else ""))


def cand_cli(d, key):
    """候補 key の投入 CLI(プロンプト付き)。現在状態の撤去を含む状態収束形。
    デバイスは候補の機構で決まる(dl_r1 のみ R1・他は R2)。"""
    cur, des = state(d), apply_cand(d, key)
    dev_des = "R1" if (des["dl"] and des["dl"][0] == "R1") else "R2"
    L = []

    def emit(dev, mode, line):
        L.append(f"{dev}({mode})# {line}")

    # --- 現在状態の撤去(存在する場合のみ・撤去先のデバイスに注意) ---
    cur_dev = "R1" if (cur["dl"] and cur["dl"][0] == "R1") else "R2"
    af_no = []
    for fl in cur["fl"]:
        af_no.append(_fl_line(d, fl, no=True))
    if cur["range"]:
        af_no.append(_range_line(d, cur["range"], no=True))
    if cur["dl"]:
        af_no.append(f"no distribute-list prefix-list {cur['dl'][1]} in")
    # --- 望みの状態の投入 ---
    af_add = []
    for fl in des["fl"]:
        af_add.append(_fl_line(d, fl))
    if des["range"]:
        af_add.append(_range_line(d, des["range"]))
    if des["dl"]:
        af_add.append(f"distribute-list prefix-list {des['dl'][1]} in")

    live_new = [n for n in des["pls"]
                if n not in dict(d["ghosts"])]
    for n in live_new:
        for i, ent in enumerate(des["pls"][n], 1):
            emit(dev_des, "config", ent_cli(n, i * 5, ent))
    if af_no and cur_dev == dev_des:
        # 同一デバイス: 1 つの AF セクションで撤去+投入
        emit(dev_des, "config", f"router ospfv3 {d['proc']}")
        emit(dev_des, "config-router", "address-family ipv6 unicast")
        for ln in af_no + af_add:
            emit(dev_des, "config-router-af", ln)
    else:
        if af_no:
            emit(cur_dev, "config", f"router ospfv3 {d['proc']}")
            emit(cur_dev, "config-router", "address-family ipv6 unicast")
            for ln in af_no:
                emit(cur_dev, "config-router-af", ln)
        if af_add:
            emit(dev_des, "config", f"router ospfv3 {d['proc']}")
            emit(dev_des, "config-router", "address-family ipv6 unicast")
            for ln in af_add:
                emit(dev_des, "config-router-af", ln)
    cur_lives = [fl[2] for fl in cur["fl"]]
    if cur["dl"]:
        cur_lives.append(cur["dl"][1])
    for name in cur_lives:
        if name not in dict(d["ghosts"]) and name not in live_new:
            emit(cur_dev, "config", f"no ipv6 prefix-list {name}")
    return L


# --------------------------------------------------------------------------
# fix 選択肢
# --------------------------------------------------------------------------
def _pfx_txt(d, key):
    des = apply_cand(d, key)
    names = [n for n in des["pls"] if n not in dict(d["ghosts"])]
    if names:
        ents = des["pls"][names[0]]
        return " / ".join(ent_cli("", 0, e).split(None, 4)[-1]
                          for e in ents)
    return ""


PROSE = {
    "fl_in_ok": "R2 において、対象を許可するところのプレフィックス・リストを、"
                "エリア {a1} の filter-list として、in の方向に適用する",
    "fl_in_mask": "R2 において、対象を含むより広い範囲に一致するところのリストを、"
                  "エリア {a1} の filter-list として、in の方向に適用する",
    "fl_in_noLe": "R2 において、長さの範囲の指定を伴わないリストを、"
                  "エリア {a1} の filter-list として、in の方向に適用する",
    "fl_out_pair": "R2 において、対象を許可するところのリストを、"
                   "エリア 0 の filter-list として、out の方向に適用する",
    "dl_r1_pair": "R1 において、対象を許可するところのリストを、"
                  "distribute-list として、in の方向に適用する",
    "fl_out_ok": "R2 において、対象を拒否するところのリストを、"
                 "エリア 0 の filter-list として、out の方向に適用する",
    "fl_out_mask": "R2 において、対象を含む範囲のプレフィックスを拒否するところの"
                   "リストを、エリア 0 の filter-list として、out の方向に適用する",
    "fl_in_target": "R2 において、対象を拒否するところのリストを、"
                    "エリア {a1} の filter-list として、in の方向に適用する",
    "dl_r2_target": "R2 において、対象を拒否するところのリストを、"
                    "distribute-list として、in の方向に適用する",
    "fl_out_taildef": "R2 において、対象を拒否し、そして、既定のプレフィックスを"
                      "許可するところのリストを、エリア 0 の filter-list として、"
                      "out の方向に適用する",
    "dl_r1_ok": "R1 において、対象を拒否するところのリストを、"
                "distribute-list として、in の方向に適用する",
    "dl_r1_mask": "R1 において、対象を含む範囲のプレフィックスを拒否するところの"
                  "リストを、distribute-list として、in の方向に適用する",
    "dl_r1_taildef": "R1 において、対象を拒否し、そして、既定のプレフィックスを"
                     "許可するところのリストを、distribute-list として、"
                     "in の方向に適用する",
    "range_ok": "R2 において、4本のプレフィックスを包含するところの最小の範囲の "
                "area range を、エリア 0 に構成する",
    "range_nonmin": "R2 において、より広い範囲の area range を、エリア 0 に"
                    "構成する",
    "range_noncover": "R2 において、より狭い範囲の area range を、エリア 0 に"
                      "構成する",
    "fl_in_cover": "R2 において、4本のプレフィックスの範囲を許可するところの"
                   "リストを、エリア {a1} の filter-list として、in の方向に"
                   "適用する",
    "range_na_wrong": "R2 において、not-advertise を伴う area range を、"
                      "エリア 0 に構成する",
    "range_na_ok": "R2 において、4本のプレフィックスを包含するところの範囲の "
                   "area range を、not-advertise を伴って、エリア 0 に構成する",
    "fl_out_all": "R2 において、4本のプレフィックスの範囲を拒否するところの"
                  "リストを、エリア 0 の filter-list として、out の方向に適用する",
    "range_adv_wrong": "R2 において、not-advertise を伴わない area range を、"
                       "エリア 0 に構成する",
    "dl_r2_all": "R2 において、4本のプレフィックスの範囲を拒否するところの"
                 "リストを、distribute-list として、in の方向に適用する",
    "range_na_noncover": "R2 において、より狭い範囲の area range を、"
                         "not-advertise を伴って、エリア 0 に構成する",
    "dual_ok": "R2 において、配布する2本とリンクのネットワークを許可するところの"
               "リストをエリア {a1} の filter-list として in の方向に適用し、"
               "そして、停止の対象を拒否するところのリストをエリア 0 の "
               "filter-list として out の方向に適用する",
    "in_only": "R2 において、配布する2本とリンクのネットワークを許可するところの"
               "リストを、エリア {a1} の filter-list として、in の方向に適用する",
    "out_only": "R2 において、停止の対象を拒否するところのリストを、"
                "エリア 0 の filter-list として、out の方向に適用する",
    "dual_swapped": "R2 において、配布する2本とリンクのネットワークを許可する"
                    "ところのリストをエリア 0 の filter-list として out の方向に"
                    "適用し、そして、停止の対象を拒否するところのリストを"
                    "エリア {a1} の filter-list として in の方向に適用する",
    "dual_in_mask": "R2 において、対象を含むより広い範囲を許可するところの"
                    "リストをエリア {a1} の filter-list として in の方向に適用し、"
                    "そして、停止の対象を拒否するところのリストをエリア 0 の "
                    "filter-list として out の方向に適用する",
}

WHY = {
    "fl_in_mask": "リストの一致の範囲が広く、意図されていないところの"
                  "プレフィックスまでもが、許可される。",
    "fl_in_noLe": "長さの範囲の指定を欠くエントリは、当該の長さのプレフィックス"
                  "そのものにのみ一致し、/64 のルートには一致しない。結果として、"
                  "すべてのエリア間のルートが、拒否される。",
    "fl_out_pair": "エリア 0 の out の方向のフィルタは、他のすべてのエリアに"
                   "対して作用し、第3のエリアのルータの経路テーブルにも、"
                   "影響が及ぶ。",
    "dl_r1_pair": "distribute-list は、そのルータの経路テーブルにのみ作用する。"
                  "エリアへの LSA の流入は継続し、他のルータには適用されない。",
    "fl_out_mask": "リストの一致の範囲が広く、対象ではないところの"
                   "プレフィックスまでもが、遮断される。",
    "fl_in_target": "in の方向の適用は、当該のエリアに対してのみ作用し、"
                    "第3のエリアでは、対象のルートが受信され続ける。",
    "dl_r2_target": "ABR への distribute-list は、Type-3 の生成そのものを停止し、"
                    "すべてのエリア、および、R2 自身の経路テーブルに影響が及ぶ。",
    "fl_out_taildef": "le 128 を欠く permit ::/0 は、既定のプレフィックスにのみ"
                      "一致する。結果として、すべてのエリア間のルートが、"
                      "拒否される。",
    "dl_r1_mask": "リストの一致の範囲が広く、対象ではないところのルートまでもが、"
                  "経路テーブルから除外される。",
    "dl_r1_taildef": "le 128 を欠く permit ::/0 は、既定のプレフィックスにのみ"
                     "一致する。結果として、すべての OSPF のルートが、"
                     "経路テーブルから除外される。",
    "range_nonmin": "集約は機能するものの、要求されているところの最長の"
                    "プレフィックス長(最小の範囲)ではない。",
    "range_noncover": "範囲が狭く、包含されないところのプレフィックスの明細が、"
                      "引き続き広告される。",
    "fl_in_cover": "filter-list は、集約のルートを生成しない。明細が"
                   "そのまま流入するのみである。",
    "range_na_wrong": "not-advertise により、集約のルートそのものも、"
                      "広告されない。",
    "fl_out_all": "遮断は機能するものの、プレフィックス・リストの新設を"
                  "必要とし、制約に適合しない。",
    "range_adv_wrong": "not-advertise を欠くため、範囲の集約のルートが、"
                       "広告されてしまう。",
    "dl_r2_all": "R2 自身の経路テーブルからも、対象のルートが失われる。",
    "range_na_noncover": "範囲が狭く、包含されないところのプレフィックスが、"
                         "引き続き広告される。",
    "in_only": "エリアへの流入のみが制御され、停止の対象のルートは、"
               "第3のエリアにおいて受信され続ける。",
    "out_only": "全域の停止のみが実現され、配布の限定が行われない。"
                "対象外のループバックのルートが、当該のエリアへ流入する。",
    "dual_swapped": "out の方向の許可リストは全他エリアに作用し、"
                    "第3のエリアにおいて、対象外のルートまでもが失われる。",
    "dual_in_mask": "in 側のリストの一致の範囲が広く、意図されていないところの"
                    "プレフィックスまでもが、当該のエリアへ流入する。",
}


def build_choices_fix(d, rnd):
    correct = d["_correct_key"]
    keys = list(CAND_KEYS[d["world"]])
    rnd.shuffle(keys)
    keep = keys[:4] if correct in keys[:4] else [correct] + keys[:3]
    c = [(PROSE[k].format(a1=d["a1"]), k == correct,
          "" if k == correct else WHY[k], cand_cli(d, k))
         for k in keep]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# patch 形(★ユーザ要望 2026-08-08): 両掛けが既に構成済みで理想でない盤面に対し、
# 「どの最小修正で要件を満たすか」を選ばせる。切り分け(in/out どちらの層の
# どのエントリが原因か)が主役。健全な側を触る錯乱肢を常備する。
# --------------------------------------------------------------------------
def _patch_defs(d):
    """[(key, prose, why, cli(プロンプト付き), delta_fn)] を返す。
    delta_fn は state(d) の deepcopy に適用され、cli と同じ意味の状態遷移を行う。"""
    k = d["kind"]
    P, S = d["pl_live"], STOP_PL
    partner = d["pair"] + 1 if d["target"] == d["pair"] else d["pair"]
    correct = ents_pair(d)[0]
    # 惜しい誤値: 盤面の欠陥と同一にならない側を選ぶ(le_off 盤面=le63 なので le なし)
    if d["kind"] == "le_off":
        wrongv = correct[:4] + (None, None)
        wrongv_prose = "in 側のリストの先頭のエントリを、長さの範囲の指定を" \
                       "除いた形へ書き換える"
        wrongv_why = "長さの範囲の指定を欠くエントリは、当該の長さの" \
                     "プレフィックスそのものにのみ一致し、/64 のルートは、" \
                     "依然として流入しない。"
    else:
        wrongv = correct[:4] + (None, 63)
        wrongv_prose = "in 側のリストの先頭のエントリを、le 63 を伴う形へ" \
                       "書き換える"
        wrongv_why = "le 63 は /64 のルートに一致せず、ループバックのルートは、" \
                     "依然として流入しない。"
    wide = ents_pair(d, plen=_widen_pair(d))[0]

    def cfg(lines):
        return [f"R2(config)# {x}" for x in lines]

    def af(lines):
        return ([f"R2(config)# router ospfv3 {d['proc']}",
                 "R2(config-router)# address-family ipv6 unicast"]
                + [f"R2(config-router-af)# {x}" for x in lines])

    def fix_in(ent):
        def f(st):
            st["pls"][P][0] = ent
        return f

    def fix_out_first(ent):
        def f(st):
            st["pls"][S][0] = ent
        return f

    def drop_fl(fdir):
        def f(st):
            st["fl"] = [x for x in st["fl"] if x[1] != fdir]
        return f

    defs = []
    if k == "dual_swap":
        def reapply(st):
            st["fl"] = [("0", "out", S), ("a1", "in", P)]
        defs.append(("p_reapply",
                     "2枚のリストの適用を、正しい方向の組へ入れ替える",
                     "",
                     af([f"no area 0 filter-list prefix {P} out",
                         f"no area {d['a1']} filter-list prefix {S} in",
                         f"area 0 filter-list prefix {S} out",
                         f"area {d['a1']} filter-list prefix {P} in"]),
                     reapply))
        defs.append(("p_remove_out",
                     "out の方向の適用のみを削除する",
                     "配布の限定が in へ移らず、停止の対象以外のルートが、"
                     "当該のエリアへ流入し続ける。",
                     af([f"no area 0 filter-list prefix {P} out"]),
                     drop_fl("out")))
        defs.append(("p_remove_in",
                     "in の方向の適用のみを削除する",
                     "out に残る許可のリストが全他エリアに作用し、第3のエリアの"
                     "欠落が解消されない。",
                     af([f"no area {d['a1']} filter-list prefix {S} in"]),
                     drop_fl("in")))
        def add_a2(st):
            st["fl"] = st["fl"] + [("a2", "in", S)]
        defs.append(("p_add_a2_in",
                     f"エリア {d['a2']} にも、停止のリストを in の方向で適用する",
                     "適用方向の取り違えが解消されず、第3のエリアの欠落も、"
                     "配布の限定も回復しない。",
                     af([f"area {d['a2']} filter-list prefix {S} in"]),
                     add_a2))
        return defs
    if k == "seq_shadow":
        def reseq(st):
            st["pls"][S] = [st["pls"][S][1], st["pls"][S][0]]
        defs.append(("p_fix_out_seq",
                     "out 側のリストの permit のエントリを、deny の後方へ移動する",
                     "",
                     cfg([f"no ipv6 prefix-list {S} seq 5",
                          ent_cli(S, 15, ("permit", 0, 0, 0, None, 128))]),
                     reseq))
        def del_deny(st):
            st["pls"][S] = [st["pls"][S][0]]
        defs.append(("p_del_deny",
                     "out 側のリストの deny のエントリを削除する",
                     "停止そのものが失われ、対象のルートが、すべてのエリアで"
                     "受信され続ける。",
                     cfg([f"no ipv6 prefix-list {S} seq 10"]),
                     del_deny))
        defs.append(("p_fix_in_wide",
                     "in 側のリストの一致の範囲を、広い側へ修正する",
                     "原因は out 側のシーケンスの順序にある。in 側の変更は、"
                     "意図されていないルートの流入を招くのみである。",
                     cfg([f"no ipv6 prefix-list {P} seq 5",
                          ent_cli(P, 5, wide)]),
                     fix_in(wide)))
        defs.append(("p_remove_out",
                     "out の方向の適用を削除する",
                     "停止そのものが失われる。",
                     af([f"no area 0 filter-list prefix {S} out"]),
                     drop_fl("out")))
        return defs
    # in 側に欠陥がある盤面(mask_off / le_missing / le_off / block_off / mask_narrow)
    defs.append(("p_fix_in",
                 "in 側のリストの先頭のエントリを、正しい一致へ書き換える",
                 "",
                 cfg([f"no ipv6 prefix-list {P} seq 5",
                      ent_cli(P, 5, correct)]),
                 fix_in(correct)))
    defs.append(("p_fix_in_wrongv",
                 wrongv_prose,
                 wrongv_why,
                 cfg([f"no ipv6 prefix-list {P} seq 5",
                      ent_cli(P, 5, wrongv)]),
                 fix_in(wrongv)))
    deny_partner = ("deny", partner, partner, 64, None, None)
    defs.append(("p_fix_out_wrongside",
                 "out 側のリストの deny のエントリを、別のプレフィックスへ"
                 "書き換える",
                 "原因は in 側のリストにある。健全であるところの停止のリストを"
                 "変更すると、停止の対象までもが入れ替わってしまう。",
                 cfg([f"no ipv6 prefix-list {S} seq 5",
                      ent_cli(S, 5, deny_partner)]),
                 fix_out_first(deny_partner)))
    defs.append(("p_remove_in",
                 "in の方向の適用を削除する",
                 "配布の限定が失われ、対象外のループバックのルートが、"
                 "当該のエリアへ流入する。",
                 af([f"no area {d['a1']} filter-list prefix {P} in"]),
                 drop_fl("in")))
    return defs


def _verify_patch(d):
    ok = []
    for key, _p, _w, _c, delta in _patch_defs(d):
        st = copy.deepcopy(state(d))
        delta(st)
        if _works(d, st):
            ok.append(key)
    if len(ok) != 1:
        raise ValueError(f"ospfv3pl patch 一意性違反: kind={d['kind']} "
                         f"s={d['s']:X} ok={ok}")
    d["_patch_correct"] = ok[0]


def build_choices_patch(d, rnd):
    correct = d["_patch_correct"]
    c = [(prose, key == correct, "" if key == correct else why, cli)
         for key, prose, why, cli, _delta in _patch_defs(d)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# read 形の素材: 現在状態の表 + 紛らわしい別解釈の表
# --------------------------------------------------------------------------
def read_variants(d):
    """(正解の R1 表, [(ラベル, 表), ...])。表は {(val,plen): met}。"""
    cur = model(d, state(d))["t1"]
    alts = []
    alts.append(("フィルタが作用しないという解釈(基線)",
                 baseline(d)["t1"]))
    fixed = apply_cand(d, d["_correct_key"])
    alts.append(("意図どおりに動作したと仮定した場合",
                 model(d, fixed)["t1"]))
    st = state(d)
    if len(st["fl"]) == 2:
        # dual: 片側のフィルタを見落とした場合の表
        import copy
        for i, label in ((0, "out 側のフィルタの見落とし"),
                         (1, "in 側のフィルタの見落とし")):
            stx = copy.deepcopy(st)
            stx["fl"] = [f for j, f in enumerate(st["fl"]) if j != i]
            alts.append((label, model(d, stx)["t1"]))
    if st["fl"] or st["dl"]:
        # 一致範囲を 1 ビット読み違えた場合の表(in 側優先)
        ins = [f for f in st["fl"] if f[1] == "in"]
        name = (ins[0][2] if ins else st["fl"][0][2]) if st["fl"] \
            else st["dl"][1]
        import copy
        st2 = copy.deepcopy(st)
        ents = st2["pls"][name]
        act, b3, b4, plen, ge, le = ents[0]
        if 44 < plen < 48:
            ents[0] = (act, block_base(b3, plen + 1), b4, plen + 1, ge, le)
            alts.append(("一致範囲を 1 ビット狭く読んだ場合", model(d, st2)["t1"]))
        # 暗黙の deny を見落とした場合(permit 形のみ意味を持つ)
        if all(e[0] == "permit" for e in st["pls"][name][:1]):
            t = dict(model(d, state(d))["t1"])
            for lk in (d["lnk"]["a0"], d["lnk"]["a2"]):
                t[(v6(*lk), 64)] = MET_LINK
            alts.append(("暗黙の deny の見落とし", t))
    if st["range"]:
        st3 = state(d)
        st3["range"] = (d["minlen"], st["range"][1])
        alts.append(("範囲の包含の読み違え", model(d, st3)["t1"]))
    if d["kind"] == "none":
        # 未参照リストが「勝手に作用する」と誤解した場合
        for name, ents in d["ghosts"][:2]:
            st4 = state(d)
            st4["fl"] = [("a1", "in", name)]
            alts.append((f"未参照のリスト {name} が適用されるという誤解",
                         model(d, st4)["t1"]))
    return cur, alts
