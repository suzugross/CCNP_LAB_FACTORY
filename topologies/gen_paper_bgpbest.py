#!/usr/bin/env python3
"""紙面ファミリ shape=bgpbest — BGP ベストパス読解 (BL-112・ENARSI 1.11.c)。

`show ip bgp` の合成表(書式は poc/bgpbest 実測の写し)を読ませ、
決定リスト(bgpbest_model.py)の適用・決め手の段の同定・要件世界での手段選択を問う。

★紙面専用(実機展開なし)。挙動の根拠= poc/bgpbest/README.md(B番号)・
  poc/bgp-ring/README.md(P番号)。モデルの詳細= bgpbest_model.py。

kinds(決め手の段/誤認の種):
  DECIDE 系(read/why): weight / lp / localorig / aspath / origin / med /
    med_cross(MED はあるのに異ASで比較されず後段で決まる) / ebgp / igp /
    rid(compare-routerid 前提・oldest の飛びを知らないと落ちる) /
    nh_invalid(候補にすら入らない)
  MISCONF 系(cause 専用): weight_remote(別ルータに設定=伝播しない) /
    lp_ebgp(eBGP へは送られない) / remote_lp(対向の LP が MED より先に決まる)

worlds(fix 形の正解レバー反転・要件文で表現):
  one_router(影響を当該ルータに限定)→ weight /
  whole_as(AS 全体で同一出口)→ LP(in) /
  return_med(戻り制御・MED 合意)→ MED(out) /
  return_prepend(戻り制御・MED 変更禁止)→ prepend(out) /
  respect_med(MED 合意を尊重・対向設定変更不可)→ bgp always-compare-med /
  igp_frozen(IGP 変更禁止)→ next-hop-self /
  bgp_frozen(BGP 変更禁止)→ IGP に外部セグメントを載せる

forms: read(ベストパスはどれか) / why(決め手の段はどれか) /
  fix(要件を満たして経路を変える設定・被覆エンジン) / cause(意図どおりにならない原因)
"""
import random
import sys

try:
    import bgpbest_model as bm
except ImportError:                      # topologies/ 外から import された場合
    from topologies import bgpbest_model as bm

# ---------------------------------------------------------------- 語彙
DECIDE_KINDS = ["weight", "lp", "localorig", "aspath", "origin", "med",
                "med_cross", "ebgp", "igp", "rid", "nh_invalid"]
CAUSE_KINDS = ["weight_remote", "lp_ebgp", "remote_lp"]
KINDS = DECIDE_KINDS + CAUSE_KINDS

# fix 形が成立する kind → worlds
FIX_WORLDS = {
    "aspath": ["one_router", "whole_as"],
    "origin": ["one_router", "whole_as"],
    "med": ["one_router", "whole_as", "return_med", "return_prepend"],
    "med_cross": ["respect_med", "whole_as"],
    "ebgp": ["one_router", "whole_as"],
    "igp": ["one_router", "whole_as"],
    "rid": ["one_router", "whole_as"],
    "nh_invalid": ["igp_frozen", "bgp_frozen"],
}

PREFIXES = ["198.51.100.0", "203.0.113.0", "192.0.2.0",
            "172.29.40.0", "172.31.208.0", "10.155.24.0"]
ISP_NAMES = [("ISP-EAST", "ISP-WEST"), ("TRANSIT-A", "TRANSIT-B"),
             ("CARRIER-1", "CARRIER-2"), ("UPLINK-A", "UPLINK-B")]


def worlds_for(kind):
    return FIX_WORLDS.get(kind, [])


def kind_forms(kind):
    """その kind が取り得る出題形。"""
    if kind in CAUSE_KINDS:
        return {"cause"}
    forms = {"read", "why"}
    if kind in FIX_WORLDS:
        forms.add("fix")
    if kind in ("med_cross", "nh_invalid"):
        forms.add("cause")
    if kind == "nh_invalid":
        # ★2 経路の対比が主題(デコイを足すと決め手の段が変わる)。
        #   「どれがベストか」より「なぜ選ばれていないか」(why/cause)で出す。
        forms.discard("read")
    return forms


def forms_for(d):
    return sorted(kind_forms(d["kind"]))


# ---------------------------------------------------------------- 盤面
def _rid(rnd, used, lo=1, hi=250):
    while True:
        n = rnd.randint(lo, hi)
        r = f"{n}.{n}.{n}.{n}"
        if r not in used:
            used.add(r)
            return r


def _mk(key, **kw):
    """モデル形 path + 表示用フィールド。"""
    d = {"key": key, "nh": None, "nh_ok": True, "weight": 0, "lp": None,
         "local": False, "aspath": [], "origin": "i", "med": None,
         "ebgp": True, "nbr_as": None, "igp_metric": 0, "age_rank": 9,
         "rid": None, "nbr_ip": None,
         # 表示用
         "lp_shown": None,      # 表の LocPrf 列(None= 空欄)
         "via": ""}             # 説明用(どの事業者経由か)
    d.update(kw)
    return d


def draw(rnd, kind=None, world=None):
    """盤面を 1 つ作る。成立しなければ ValueError(呼び手が seed を進める)。"""
    kind = kind or rnd.choice(KINDS)
    if world is None and kind in FIX_WORLDS:
        world = rnd.choice(worlds_for(kind))

    own_as = rnd.choice([65010, 65020, 65050, 64900, 65100])
    as_a = rnd.choice([65201, 65210, 64520, 65310])
    as_b = rnd.choice([65402, 65430, 64611, 65520])
    while as_b == as_a:
        as_b = rnd.choice([65402, 65430, 64611, 65520])
    far_as = rnd.choice([64700, 65533, 64830])       # 起源側の遠い AS
    ispa, ispb = rnd.choice(ISP_NAMES)
    prefix = rnd.choice(PREFIXES)
    vname = f"RT{rnd.randint(1, 19):02d}"
    used_rids = set()
    rid_v = _rid(rnd, used_rids)

    # 近隣アドレス(第3オクテットを散らす)
    o2 = rnd.randint(11, 98)
    ip_a1, ip_a2 = f"10.{o2}.12.2", f"10.{o2}.13.3"
    ip_b1 = f"10.{o2}.14.4"
    ip_c1, ip_c2 = f"{rnd.randint(2, 9)}.5.5.5", f"{rnd.randint(2, 9)}.6.6.6"
    while ip_c2.split(".")[0] == ip_c1.split(".")[0]:
        ip_c2 = f"{rnd.randint(2, 9)}.6.6.6"

    def _peer(key, base, kw):
        base.update(kw)
        return _mk(key, **base)

    def ebgp_a1(**kw):
        return _peer("a1", dict(nh=ip_a1, nbr_ip=ip_a1,
                                rid=_rid(rnd, used_rids), nbr_as=as_a,
                                aspath=[as_a, far_as], via=ispa), kw)

    def ebgp_a2(**kw):
        return _peer("a2", dict(nh=ip_a2, nbr_ip=ip_a2,
                                rid=_rid(rnd, used_rids), nbr_as=as_a,
                                aspath=[as_a, far_as], via=ispa), kw)

    def ebgp_b1(**kw):
        return _peer("b1", dict(nh=ip_b1, nbr_ip=ip_b1,
                                rid=_rid(rnd, used_rids), nbr_as=as_b,
                                aspath=[as_b, far_as], via=ispb), kw)

    def ibgp_c1(**kw):
        return _peer("c1", dict(nh=ip_c1, nbr_ip=ip_c1, rid=ip_c1,
                                ebgp=False, nbr_as=as_a,
                                aspath=[as_a, far_as], igp_metric=11,
                                lp_shown=100, via=f"{ispa}(境界経由)"), kw)

    def ibgp_c2(**kw):
        return _peer("c2", dict(nh=ip_c2, nbr_ip=ip_c2, rid=ip_c2,
                                ebgp=False, nbr_as=as_a,
                                aspath=[as_a, far_as], igp_metric=101,
                                lp_shown=100, via=f"{ispa}(境界経由)"), kw)

    opts = {}
    cause = None                 # cause 形の正解 claim キー
    detail_need = False          # detail 抜粋が必須か
    med_pair = (rnd.choice([20, 50, 80]), rnd.choice([200, 300, 400]))
    w_val = rnd.choice([25000, 35000, 40000])

    if kind == "weight":
        # a1 は AS 長が最長なのに weight で勝つ。foil= weight を外すと b1。
        paths = [ebgp_a1(weight=w_val, aspath=[as_a, as_a, far_as]),
                 ebgp_b1(), ibgp_c1()]
        expect, foil_kill = "weight", ("weight",)
    elif kind == "lp":
        # a1 は prepend で最長なのに LP 200 で勝つ。foil= LP を外すと b1。
        paths = [ebgp_a1(lp=200, lp_shown=200,
                         aspath=[as_a, as_a, as_a, far_as]),
                 ebgp_b1(), ibgp_c1()]
        expect, foil_kill = "lp", ("lp",)
    elif kind == "localorig":
        # 0.0.0.0 / 32768 の行を見落とすと b1 を選ぶ。
        paths = [_mk("lo", nh="0.0.0.0", nbr_ip="0.0.0.0", rid=rid_v,
                     weight=32768, local=True, ebgp=False, origin="i",
                     med=0, via="自機起源"),
                 ebgp_b1(), ebgp_a1()]
        # ★foil は構造的に作れない(自機起源は weight を消しても local 段・
        #   AS長 0 で勝ち続ける)。罠は「0.0.0.0/32768 行の読み落とし」側で成立。
        expect, foil_kill = "weight", ()
    elif kind == "aspath":
        # b1(len2) が勝つ。origin だけ見ると a1(i) を選ぶ(b1 は ?)。
        paths = [ebgp_a1(origin="i", aspath=[as_a, as_a, far_as]),
                 ebgp_b1(origin="?"),
                 ibgp_c1(aspath=[as_a, far_as, far_as, far_as])]
        expect, foil_kill = "aspath", ("aspath",)
    elif kind == "origin":
        # AS 長は同じ。origin i の a1 が勝つ。MED は b1 の方が小さい(比較されない)。
        paths = [ebgp_a1(origin="i", med=med_pair[1]),
                 ebgp_b1(origin="?", med=med_pair[0], age_rank=1)]
        expect, foil_kill = "origin", ("origin",)
    elif kind == "med":
        # 同一隣接 AS の 2 経路。MED 小の a1。foil= MED を消すと oldest で a2。
        paths = [ebgp_a1(med=med_pair[0], age_rank=2),
                 ebgp_a2(med=med_pair[1], age_rank=1),
                 ebgp_b1(aspath=[as_b, as_b, far_as], age_rank=3)]
        expect, foil_kill = "med", ("med",)
    elif kind == "med_cross":
        # MED はあるのに異 AS 同士で比較されず、oldest / RID まで落ちる。
        crid = rnd.random() < 0.5
        opts["compare_routerid"] = crid
        a = ebgp_a1(med=med_pair[1], age_rank=1)
        b = ebgp_b1(med=med_pair[0], age_rank=2)
        if crid:
            # RID 最小 = MED が大きい側(罠の維持)
            a["rid"], b["rid"] = sorted([a["rid"], b["rid"]],
                                        key=bm._ip_key)
        paths = [a, b]
        expect = "rid" if crid else "oldest"
        foil_kill = ()
        cause = "med_cross"
        detail_need = True
    elif kind == "ebgp":
        # eBGP(b1) vs iBGP(c1)。c1 の MED が小さい(異ASで比較されない)二重罠。
        paths = [ebgp_b1(med=500), ibgp_c1(med=10, age_rank=1)]
        expect, foil_kill = "ebgp", ()
        detail_need = True
    elif kind == "igp":
        # iBGP 同士は IGP メトリック。foil= 等メトリックなら RID で c2。
        # MED は両方欠落(トランジット経路の自然形・B17)= 比較で何も起きない。
        c1, c2 = ibgp_c1(age_rank=2), ibgp_c2(age_rank=1)
        c1["rid"], c2["rid"] = sorted([c1["rid"], c2["rid"]],
                                      key=bm._ip_key, reverse=True)
        paths = [c1, c2]
        expect, foil_kill = "igp", ("igp",)
        detail_need = True
    elif kind == "rid":
        # eBGP 全段タイ×compare-routerid。無ければ oldest で逆になる。
        opts["compare_routerid"] = True
        a1, a2 = ebgp_a1(age_rank=2), ebgp_a2(age_rank=1)
        a1["rid"], a2["rid"] = sorted([a1["rid"], a2["rid"]],
                                      key=bm._ip_key)
        paths = [a1, a2]
        expect, foil_kill = "rid", ()
        detail_need = True
    elif kind == "nh_invalid":
        # LP 200 の iBGP 経路が inaccessible。見た目最強の行が候補外。
        # ★next-hop は境界の対 ISP 区間の外部アドレスのまま(= next-hop-self
        #   欠落の実相。B15 実測: from はピア(Lo)・nh は外部アドレス)。
        paths = [ibgp_c1(lp=200, lp_shown=200, nh_ok=False,
                         nh=f"10.{o2}.25.2"),
                 ebgp_b1(aspath=[as_b, as_b, far_as])]
        expect, foil_kill = "nh", ()
        cause = "nh_no_self"
        detail_need = True
    elif kind == "weight_remote":
        # 境界(c1 の送り手)に weight を設定しても vantage には何も起きない。
        paths = [ebgp_b1(), ibgp_c1(age_rank=1)]
        expect, foil_kill = "ebgp", ()
        cause = "weight_remote"
    elif kind == "lp_ebgp":
        # eBGP ピアへ set local-preference out しても伝わらない(B16)。
        paths = [ebgp_a1(age_rank=1), ebgp_b1(age_rank=2)]
        expect, foil_kill = "oldest", ()
        cause = "lp_ebgp"
        detail_need = True
    elif kind == "remote_lp":
        # 戻りを MED で制御しようとしたが、対向の LP が先に決まる。
        paths = [ebgp_a1(age_rank=1), ebgp_a2(age_rank=2)]
        expect, foil_kill = "oldest", ()
        cause = "remote_lp"
    else:
        raise ValueError(f"unknown kind {kind}")

    # ★2経路の盤面にはデコイ(早い段で負ける第3経路)を足す。
    #   read 形の選択肢を成立させ、表の情報量も上げる(簡単すぎ防止)。
    #   MED 安全性: デコイは AS-PATH 長で先に消えるので MED 段に届かない。
    #   nh_invalid は除外(デコイが AS-PATH 段まで生き残り決め手が変わる。
    #   この種の主題は「候補に入らない」なので 2 経路の対比が最も鋭い)。
    if len(paths) == 2 and kind not in ("remote_lp", "nh_invalid"):
        dk = rnd.choice([k for k in ("a2", "b1", "c2")
                         if k not in {p["key"] for p in paths}])
        mk = {"a2": ebgp_a2, "b1": ebgp_b1, "c2": ibgp_c2}[dk]
        decoy = mk(age_rank=8)
        decoy["aspath"] = [decoy["aspath"][0]] * 2 + [far_as, far_as]
        decoy["med"] = None
        paths.append(decoy)

    # 年齢(oldest)の表示整合: age_rank 昇順 = 受信が古い = Updated on が早い
    base_min = rnd.randint(0, 500)
    for p in paths:
        p.setdefault("age_rank", 9)
    for i, p in enumerate(sorted(paths, key=lambda x: x["age_rank"])):
        p["updated_min"] = base_min + i * rnd.randint(7, 90) + rnd.randint(0, 5)

    bno = rnd.sample([n for n in range(1, 20)
                      if f"RT{n:02d}" != vname], 2)
    own_prefix = rnd.choice([p for p in PREFIXES if p != prefix])
    d = {"kind": kind, "world": world, "own_as": own_as, "as_a": as_a,
         "as_b": as_b, "far_as": far_as, "ispa": ispa, "ispb": ispb,
         "prefix": prefix, "plen": 24, "vname": vname, "rid_v": rid_v,
         "paths": paths, "opts": opts, "expect": expect, "cause": cause,
         "detail_need": detail_need, "w_val": w_val,
         "ip": {"a1": ip_a1, "a2": ip_a2, "b1": ip_b1,
                "c1": ip_c1, "c2": ip_c2},
         "bname": {"c1": f"RT{bno[0]:02d}", "c2": f"RT{bno[1]:02d}"},
         "ext_net": {"c1": f"10.{o2}.25.0", "c2": f"10.{o2}.36.0"},
         "own_prefix": own_prefix,          # 戻り世界で自 AS が広告する側
         "mon": rnd.choice(["Mar", "Apr", "May", "Jun", "Jul", "Aug"]),
         "day": rnd.randint(3, 27), "h0": rnd.randint(1, 13),
         "tblver": rnd.randint(5, 60)}
    # cause 形の「意図した経路」(claim の機械判定に使う)
    if kind == "med_cross":
        d["intent"] = min((p for p in paths if p.get("med") is not None),
                          key=lambda p: p["med"])["key"]
    elif kind == "nh_invalid":
        d["intent"] = next(p["key"] for p in paths if not p["nh_ok"])
    elif kind == "weight_remote":
        d["intent"] = "c1"
    elif kind == "lp_ebgp":
        d["intent"] = "a1"
    elif kind == "remote_lp":
        d["intent"] = "a2"

    r = bm.best(paths, opts)                       # MED 順序依存なら ValueError
    if r["step"] != expect:
        raise ValueError(f"decided={r['step']} expect={expect} ({kind})")
    d["winner"] = r["winner"]
    d["trace"] = r["trace"]

    # foil(段の取り違えで別解になること)の機械検証
    if foil_kill:
        neut = []
        for p in paths:
            q = dict(p)
            if "weight" in foil_kill:
                q["weight"] = 0
            if "local" in foil_kill:
                q["local"] = False
            if "lp" in foil_kill:
                q["lp"] = None
            if "med" in foil_kill:
                q["med"] = None
            if "aspath" in foil_kill:
                q["aspath"] = [own_as]
            if "origin" in foil_kill:
                q["origin"] = "i"
            if "igp" in foil_kill:
                q["igp_metric"] = 0
            neut.append(q)
        r2 = bm.best(neut, opts)
        if r2["winner"] == r["winner"]:
            raise ValueError(f"foil 不成立: {kind}")
        d["foil_winner"] = r2["winner"]
    # med_cross / ebgp: acm 仮定で別解になること(罠の実在)
    if kind in ("med_cross", "ebgp"):
        r3 = bm.best(paths, dict(opts, always_compare_med=True))
        if r3["winner"] == r["winner"]:
            raise ValueError(f"acm-foil 不成立: {kind}")
        d["foil_winner"] = r3["winner"]
    # rid: compare-routerid が無ければ oldest で逆になること
    if kind == "rid":
        r4 = bm.best(paths, {})
        if r4["winner"] == r["winner"]:
            raise ValueError("rid-foil 不成立")
        d["foil_winner"] = r4["winner"]
    # nh_invalid: 候補外の経路の方が「属性上は」強いこと
    if kind == "nh_invalid":
        alive = [dict(p, nh_ok=True) for p in paths]
        r5 = bm.best(alive, opts)
        if r5["winner"] == r["winner"]:
            raise ValueError("nh-foil 不成立")
        d["foil_winner"] = r5["winner"]

    if kind in FIX_WORLDS and world:
        _plan_fix(d, rnd)
    return d


# ---------------------------------------------------------------- fix 被覆
FIX_CAND_JA = {
    "W": "対象経路の近隣に weight を設定する(当該ルータのみ)",
    "LPIN": "inbound route-map で LOCAL_PREF を上げる",
    "PREP": "もう一方のリンクの outbound で AS-PATH prepend する",
    "MEDOUT": "優先したいリンクの outbound で MED を小さく広告する",
    "ACM": "bgp always-compare-med を設定する",
    "NHS": "境界ルータで neighbor next-hop-self を設定する",
    "NETIGP": "境界ルータで外部セグメントを IGP に広告する",
    "CLR": "clear ip bgp * soft を実行する",
}


def _apply_cand(d, ck, target):
    """候補 ck を適用した後の勝者を返す(順方向= vantage 視点)。"""
    paths = [dict(p) for p in d["paths"]]
    opts = dict(d["opts"])
    for p in paths:
        if p["key"] != target:
            continue
        if ck == "W":
            p["weight"] = 30000
        elif ck == "LPIN":
            p["lp"] = 200
        elif ck == "NHS" or ck == "NETIGP":
            p["nh_ok"] = True
    if ck == "ACM":
        opts["always_compare_med"] = True
    try:
        return bm.best(paths, opts)["winner"]
    except ValueError:
        return None


def _remote_best(d, ck):
    """戻り世界: 対向 AS(単一視点に単純化)がどちらのリンクを選ぶか。

    対向は自 AS からの 2 広告(リンク a1 / a2)を比較する。同一隣接 AS なので
    MED は既定で比較される。現状は a1 側(older)。
    """
    a1 = {"key": "a1", "nh_ok": True, "weight": 0, "lp": None, "local": False,
          "aspath": [d["own_as"]], "origin": "i", "med": 0, "ebgp": True,
          "nbr_as": d["own_as"], "igp_metric": 0, "age_rank": 1,
          "rid": "1.1.1.1", "nbr_ip": "10.0.0.1"}
    a2 = dict(a1, key="a2", age_rank=2, rid="2.2.2.2", nbr_ip="10.0.0.2")
    if ck == "PREP":
        a1["aspath"] = [d["own_as"]] * 3
    elif ck == "MEDOUT":
        a1["med"], a2["med"] = 200, 10
    elif ck == "LPIN" or ck == "W" or ck == "ACM":
        pass                                   # 自側 in / 自機ローカル= 対向に無関係
    return bm.best([a1, a2], {})["winner"]


def _plan_fix(d, rnd):
    """world ごとの works/complies を機械判定し、被覆(works>=2・complies=1)を検証。"""
    world = d["world"]
    kind = d["kind"]
    ret = world in ("return_med", "return_prepend")
    if ret:
        d["target"] = "a2"                     # 戻りをリンク a2 へ
    else:
        # 順方向: 現ベスト以外で「属性上の対抗馬」を目標にする
        losers = [p["key"] for p in d["paths"] if p["key"] != d["winner"]
                  and p.get("nh_ok", True)]
        if kind == "nh_invalid":
            d["target"] = [p["key"] for p in d["paths"]
                           if not p["nh_ok"]][0]
        else:
            d["target"] = d.get("foil_winner") if d.get("foil_winner") in losers \
                else losers[0]
    cands = ["W", "LPIN", "PREP", "MEDOUT", "ACM", "CLR"]
    if kind == "nh_invalid":
        cands = ["NHS", "NETIGP", "LPIN", "W", "CLR"]
    # ★works= 「vantage のベストパスを目標へ反転できる」(素朴な有効性)。
    #   whole_as の「AS 全体」や one_router の「他に影響させない」は complies 側で
    #   落とす(weight が whole_as で不適合、LP が one_router で不適合、が罠の本体)。
    #   戻り世界だけは works 自体を対向視点で評価する(方向違いの手段は無効)。
    works, complies = {}, {}
    for ck in cands:
        if ck == "CLR":
            works[ck] = False
        elif ret:
            works[ck] = _remote_best(d, ck) == d["target"]
        elif ck in ("PREP", "MEDOUT"):
            works[ck] = False                  # 順方向には効かない(戻り専用)
        else:
            works[ck] = _apply_cand(d, ck, d["target"]) == d["target"]
        complies[ck] = _complies(world, ck)
    ok = [c for c in cands if works[c] and complies[c]]
    n_works = sum(1 for c in cands if works[c])
    if len(ok) != 1 or n_works < 2:
        raise ValueError(
            f"fix 被覆不成立 kind={kind} world={world} works={n_works} ok={ok}")
    d["fix"] = {"cands": cands, "works": works, "complies": complies,
                "answer": ok[0]}


def _complies(world, ck):
    tbl = {
        "one_router": {"W"},
        "whole_as": {"LPIN"},
        "return_med": {"MEDOUT"},
        "return_prepend": {"PREP"},
        "respect_med": {"ACM"},
        "igp_frozen": {"NHS"},
        "bgp_frozen": {"NETIGP"},
    }
    allow = tbl[world]
    if ck in allow:
        return True
    # 制約に抵触しない中立候補(CLR 等)は complies=True のまま works で落ちる
    neutral = {"CLR"}
    # ★one_router で ACM を許すと「ローカル設定かつ有効」で正解が 2 つになる
    #   (ebgp 種の異AS MED)。要件文に「各事業者の MED は相互に調整されていない
    #   独自値であり判断基準にしない」を常設し、ACM は不適合とする(requirements)。
    if world in ("return_med", "return_prepend"):
        neutral |= {"LPIN", "W"}               # 方向違い= works で落ちる
    if world == "igp_frozen":
        neutral |= {"LPIN", "W"}
    if world == "bgp_frozen":
        return ck in {"NETIGP"}                # BGP 側は全部アウト
    return ck in neutral


# ---------------------------------------------------------------- cause claims
CLAIMS = {
    "med_cross": "MED は、異なる隣接 AS から受信した経路の間では、"
                 "既定では比較されない",
    "weight_remote": "weight は、それを設定したルータのローカルでのみ有効であり、"
                     "iBGP の近隣には伝播しない",
    "lp_ebgp": "LOCAL_PREF は iBGP でのみ交換される属性であり、"
               "eBGP の近隣には送信されない",
    "nh_no_self": "next-hop が IGP で解決できず、その経路はベストパス選択の"
                  "候補に入っていない",
    "remote_lp": "対向 AS 側で LOCAL_PREF による優先制御が行われており、"
                 "MED はベストパス選択のより後の段でしか評価されない",
    "no_clear": "設定変更後に BGP セッションの再評価(clear)が行われていない",
    "aspath_longer": "意図した経路の AS-PATH が、現用の経路よりも長い",
}


def claim_true(d, key):
    """claim の真偽を盤面から機械判定する。"""
    paths, opts = d["paths"], d["opts"]
    if key == "med_cross":
        # MED が付いた経路が複数の隣接 AS に跨り、比較されずに後段で決まったか
        alive = [p for p in paths if p.get("nh_ok", True)]
        meds = {p["nbr_as"] for p in alive if p.get("med") is not None}
        return (len(meds) > 1 and not opts.get("always_compare_med")
                and d["expect"] in ("oldest", "rid", "ebgp", "igp"))
    if key == "weight_remote":
        return d["kind"] == "weight_remote"
    if key == "lp_ebgp":
        return d["kind"] == "lp_ebgp"
    if key == "nh_no_self":
        return any(not p.get("nh_ok", True) for p in paths)
    if key == "remote_lp":
        return d["kind"] == "remote_lp"
    if key == "no_clear":
        return False    # 表に属性が反映済み= 伝播は済んでいる(観測が反証)
    if key == "aspath_longer":
        # ★「意図した経路の AS-PATH が長いから」— 意図経路(intent)と現用を比較。
        #   盤面全体の最長(デコイ)と比べると偽の真が出る(検証で発覚・修正済)。
        win = next(p for p in paths if p["key"] == d["winner"])
        it = next((p for p in paths if p["key"] == d.get("intent")), None)
        return bool(it) and len(it["aspath"]) > len(win["aspath"])
    raise KeyError(key)


def verify_choices(d):
    """一意性の総点検(pick_draw から呼ばれる)。NG なら ValueError。"""
    # read/why= モデルの勝者と決め手が一意に出ていること(draw で検証済み)
    if d["kind"] in FIX_WORLDS and d.get("world") and "fix" not in d:
        raise ValueError("fix 未計画")
    if d.get("cause"):
        # cause= 正解 claim がちょうど 1 つ真であること
        keys = cause_claim_keys(d)
        truth = [k for k in keys if claim_true(d, k)]
        if truth != [d["cause"]]:
            raise ValueError(f"cause 一意性 NG: true={truth} want={d['cause']}")
    return d


def cause_claim_keys(d):
    """cause 形の選択肢に使う claim キー(正解+錯乱肢)。"""
    pool = {
        "med_cross": ["med_cross", "aspath_longer", "no_clear", "lp_ebgp"],
        "nh_invalid": ["nh_no_self", "no_clear", "med_cross", "weight_remote"],
        "weight_remote": ["weight_remote", "no_clear", "lp_ebgp", "med_cross"],
        "lp_ebgp": ["lp_ebgp", "no_clear", "med_cross", "weight_remote"],
        "remote_lp": ["remote_lp", "no_clear", "lp_ebgp", "med_cross"],
    }
    return pool[d["kind"] if d["kind"] in pool else d["cause"]]


# ---------------------------------------------------------------- 合成 show
# ★書式は poc/bgpbest/results-raw.md の実測写し(IOL iol-xe 17.15)。
#   桁・マーカー・空欄規則(eBGP 行の LocPrf 空欄・MED 欠落の Metric 空欄)を守る。
TABLE_HDR = ("Status codes: s suppressed, d damped, h history, * valid, "
             "> best, i - internal, \n"
             "              r RIB-failure, S Stale, m multipath, "
             "b backup-path, f RT-Filter, \n"
             "              x best-external, a additional-path, "
             "c RIB-compressed, \n"
             "              t secondary path, L long-lived-stale,\n"
             "Origin codes: i - IGP, e - EGP, ? - incomplete\n"
             "RPKI validation codes: V valid, I invalid, N Not found\n\n"
             "     Network          Next Hop            Metric LocPrf "
             "Weight Path")

ORIGIN_LONG = {"i": "IGP", "e": "EGP", "?": "incomplete"}


def _rows_order(d):
    """表示順= 新しい経路が上(IOS の格納順。B13b flap 実測で確認)。"""
    return sorted(d["paths"], key=lambda p: -p["age_rank"])


def _net_name(d):
    """Network 列の表記: classful に一致するときだけ長さを省く(B17 実測=
    172.20.77.0/24 は `/24` 付き・198.51.100.0(クラスC)は無印)。"""
    o1 = int(d["prefix"].split(".")[0])
    classful = 8 if o1 < 128 else 16 if o1 < 192 else 24
    if d["plen"] == classful:
        return d["prefix"]
    return f"{d['prefix']}/{d['plen']}"


def _updated_str(d, p):
    mins = d["h0"] * 60 + p.get("updated_min", 0)
    return (f"{d['mon']} {d['day']} 2026 "
            f"{mins // 60:02d}:{mins % 60:02d}:{(p['age_rank'] * 7) % 60:02d}"
            " UTC")


def _row_txt(d, p, first, nobest=False):
    """`show ip bgp` の 1 行(桁は実測写し・_fidelity で byte 照合)。

    ★実測(B15)= next-hop 解決不能の行も `*`(valid) のまま表示され、
      **表だけでは見分けが付かない**(detail の `(inaccessible)` が唯一の証拠)。
    ★実測(B17)= MED 欠落は Metric 列が完全な空欄(present-0 の `0` とは別)。
    ★nobest= 選出前の過渡(B1 実測: `*` のみで `>` が無い)。read 形はこれで出す
      (`>` を出すと答えが表に書いてある)。
    """
    best = p["key"] == d["winner"] and not nobest
    flags = (" *" + (">" if best else " ")
             + ("i" if not p["ebgp"] and not p.get("local") else " ") + "  ")
    net = _net_name(d) if first else ""
    row = flags + f"{net:<17}" + p["nh"]
    med = "" if p.get("med") is None else str(p["med"])
    lp = "" if p.get("lp_shown") is None else str(p["lp_shown"])
    w = str(p.get("weight", 0))
    row = row.ljust(49 - len(med)) + med          # Metric 右端= 49 桁目
    row = row.ljust(56 - len(lp)) + lp            # LocPrf 右端= 56 桁目
    row = row.ljust(63 - len(w)) + w              # Weight 右端= 63 桁目
    return row + " " + (aspath_str(p) + " " if p["aspath"] else "") + p["origin"]


def render_table(d, nobest=False):
    L = [f"BGP table version is {d['tblver']}, "
         f"local router ID is {d['rid_v']}", TABLE_HDR]
    for i, p in enumerate(_rows_order(d)):
        L.append(_row_txt(d, p, i == 0, nobest=nobest))
    return "\n".join(L)


def render_detail(d, nobest=False):
    rows = _rows_order(d)
    n = len(rows)
    best_no = (None if nobest else
               [p["key"] for p in rows].index(d["winner"]) + 1
               if d["winner"] else None)
    L = [f"BGP routing table entry for {d['prefix']}/{d['plen']}, "
         f"version {d['tblver']}"]
    # ★B10/B13c 実測: bestpath 系ノブは detail 冒頭に状態行が出る
    if d["opts"].get("compare_routerid"):
        L.append("BGP Bestpath: compare-routerid")
    elif d["opts"].get("med_missing_as_worst"):
        L.append("BGP Bestpath: med")
    if best_no:
        L.append(f"Paths: ({n} available, best #{best_no}, table default)")
    else:
        L.append(f"Paths: ({n} available, no best path)")
    # iBGP のみの盤面は再広告先が無い(B12 実測)。no best も広告なし(B1 実測)
    if best_no and any(p["ebgp"] for p in rows):
        L.append("  Advertised to update-groups:")
        L.append(f"     {1 + d['tblver'] % 5}         ")
    else:
        L.append("  Not advertised to any peer")
    for p in rows:
        L.append(f"  Refresh Epoch {1 + (p['age_rank'] + d['tblver']) % 4}")
        L.append("  " + (aspath_str(p) if p["aspath"] else "Local"))
        nhline = f"    {p['nh']}"
        if not p.get("nh_ok", True):
            nhline += " (inaccessible)"          # B15
        elif p.get("igp_metric", 0):
            nhline += f" (metric {p['igp_metric']})"   # B12
        nhline += f" from {p['nbr_ip']} ({p['rid']})"
        if p.get("local"):
            nhline = f"    {p['nh']} from {p['nbr_ip']} ({d['rid_v']})"
        L.append(nhline)
        # ★B17 実測: MED 欠落時は `metric N,` 句ごと出ない
        attr = f"      Origin {ORIGIN_LONG[p['origin']]}, "
        if p.get("med") is not None:
            attr += f"metric {p['med']}, "
        attr += f"localpref {bm.lp_eff(p)}, "
        if p.get("weight"):
            attr += f"weight {p['weight']}, "
        attr += "valid, "
        attr += ("sourced, local" if p.get("local")
                 else "internal" if not p["ebgp"] else "external")
        if p["key"] == d["winner"] and not nobest:
            attr += ", best"
        L.append(attr)
        L.append("      rx pathid: 0, tx pathid: "
                 + ("0x0" if p["key"] == d["winner"] and not nobest else "0"))
        L.append(f"      Updated on {_updated_str(d, p)}")
    return "\n".join(L)


# ---------------------------------------------------------------- 表示部品
def path_of(d, key):
    return next(p for p in d["paths"] if p["key"] == key)


def aspath_str(p):
    return " ".join(str(a) for a in p["aspath"]) if p["aspath"] else "Local"


def path_label(d, key):
    p = path_of(d, key)
    if p.get("local"):
        return "この機器で起源されているところの経路(next hop 0.0.0.0)"
    return f"next hop {p['nh']} の経路"


def lost_at(d, key):
    """その経路が消えた段(trace から)。勝者は None。"""
    for step, _survivors, killed in d["trace"]:
        if key in killed:
            return step
    return None


def bgp_cfg_block(d):
    """vantage の `show running-config | section router bgp` 抜粋。

    ★cfgref 実測: neighbor は IP の昇順・neighbor 配下は remote-as →
      (shutdown) → update-source、AF 配下は activate → next-hop-self →
      route-map → weight(いずれも語順=アルファベット順)。
    """
    L = [f"router bgp {d['own_as']}", f" bgp router-id {d['rid_v']}",
         " bgp log-neighbor-changes"]
    if d["opts"].get("compare_routerid"):
        L.append(" bgp bestpath compare-routerid")
    if d["opts"].get("always_compare_med"):
        L.append(" bgp always-compare-med")
    if d["opts"].get("med_missing_as_worst"):
        L.append(" bgp bestpath med missing-as-worst")
    af = [" address-family ipv4"]
    if d["kind"] == "localorig":
        af.append(f"  network {d['prefix']} mask 255.255.255.0")
    for p in sorted((q for q in d["paths"] if not q.get("local")),
                    key=lambda q: bm._ip_key(q["nbr_ip"])):
        ras = d["own_as"] if not p["ebgp"] else p["nbr_as"]
        L.append(f" neighbor {p['nbr_ip']} remote-as {ras}")
        if not p["ebgp"]:
            L.append(f" neighbor {p['nbr_ip']} update-source Loopback0")
        af.append(f"  neighbor {p['nbr_ip']} activate")
        if d["kind"] == "lp" and p.get("lp") is not None:
            af.append(f"  neighbor {p['nbr_ip']} route-map RM-CUST-IN in")
        if d["kind"] == "lp_ebgp" and p["key"] == "a1":
            af.append(f"  neighbor {p['nbr_ip']} route-map RM-PREF-OUT out")
        if d["kind"] == "remote_lp":
            if p["key"] == "a1":
                af.append(f"  neighbor {p['nbr_ip']} route-map RM-MED-A out")
            elif p["key"] == "a2":
                af.append(f"  neighbor {p['nbr_ip']} route-map RM-MED-B out")
        if p.get("weight"):
            af.append(f"  neighbor {p['nbr_ip']} weight {p['weight']}")
    L.append(" !")
    L += af + [" exit-address-family"]
    return "\n".join(L)


def rmap_cfg_block(d):
    """route-map の抜粋(必要な kind のみ・無ければ None)。"""
    if d["kind"] == "lp":
        return "route-map RM-CUST-IN permit 10\n set local-preference 200"
    if d["kind"] == "lp_ebgp":
        return "route-map RM-PREF-OUT permit 10\n set local-preference 300"
    if d["kind"] == "remote_lp":
        return ("route-map RM-MED-A permit 10\n set metric 200\n!\n"
                "route-map RM-MED-B permit 10\n set metric 10")
    return None


def static_cfg_block(d):
    if d["kind"] == "localorig":
        return f"ip route {d['prefix']} 255.255.255.0 Null0 name AGGREGATE"
    return None


def border_cfg_block(d):
    """境界ルータ側の抜粋(nh_invalid= next-hop-self 欠落 / weight_remote= 誤設定)。"""
    if d["kind"] not in ("nh_invalid", "weight_remote"):
        return None
    key = "c1"
    ext_peer = d["ext_net"][key][:-1] + "2"     # 10.x.25.0 → 10.x.25.2
    L = [f"router bgp {d['own_as']}",
         f" bgp router-id {d['ip'][key]}",
         f" neighbor {d['rid_v']} remote-as {d['own_as']}",
         f" neighbor {d['rid_v']} update-source Loopback0",
         f" neighbor {ext_peer} remote-as {d['as_a']}",
         " !",
         " address-family ipv4",
         f"  neighbor {d['rid_v']} activate"]
    if d["kind"] == "weight_remote":
        L.append(f"  neighbor {d['rid_v']} next-hop-self")
        L.append(f"  neighbor {ext_peer} activate")
        L.append(f"  neighbor {ext_peer} weight {d['w_val']}")
    else:                                       # nh_invalid: next-hop-self 無し
        L.append(f"  neighbor {ext_peer} activate")
    L.append(" exit-address-family")
    return "\n".join(L)


def remote_view(d):
    """remote_lp 形の提示物: 対向 AS 側エッジルータの detail(彼らの LP が見える)。

    幾何は「自社ルータと対向 PE01 が 2 本のリンクで接続」に単純化する。
    MED は自社の RM-MED-A/B(200/10)と一致させ、対向の inbound ポリシーが
    リンク1 側に LP 300 を与えている(= MED より前の段で決まってしまう)を、
    値の並びだけで表現する(結論は書かない= 読者が順序を適用して気づく)。
    """
    o2 = d["ip"]["a1"].split(".")[1]
    us1, us2 = f"10.{o2}.12.1", f"10.{o2}.13.1"
    p1 = _mk("r1", nh=us1, nbr_ip=us1, rid=d["rid_v"], nbr_as=d["own_as"],
             aspath=[d["own_as"]], med=200, lp=300, lp_shown=300, age_rank=1,
             updated_min=5)
    p2 = _mk("r2", nh=us2, nbr_ip=us2, rid=d["rid_v"], nbr_as=d["own_as"],
             aspath=[d["own_as"]], med=10, lp=100, lp_shown=100, age_rank=2,
             updated_min=9)
    rv = {"prefix": d["own_prefix"], "plen": 24, "opts": {},
          "rid_v": "10.255.0.1", "tblver": d["tblver"] + 3,
          "mon": d["mon"], "day": d["day"], "h0": d["h0"],
          "paths": [p1, p2]}
    rv["winner"] = bm.best([p1, p2], {})["winner"]
    return rv


def mermaid_bgpbest(d):
    keys = {p["key"] for p in d["paths"]}
    if d["kind"] == "remote_lp":
        # 対向は単一の PE と 2 本のリンク(remote_view と同じ幾何)
        o2 = d["ip"]["a1"].split(".")[1]
        return "\n".join([
            "```mermaid", "graph LR",
            f'  subgraph asv["AS {d["own_as"]}(自社)"]',
            f'    V["{d["vname"]}"]', "  end",
            f'  subgraph aspa["AS {d["as_a"]}({d["ispa"]})"]',
            '    PE01["PE01"]', "  end",
            f'  V ---|"10.{o2}.12.0/24"| PE01',
            f'  V ---|"10.{o2}.13.0/24"| PE01',
            f'  note["自社の広告: {d["own_prefix"]}/24"]',
            "```"])
    L = ["```mermaid", "graph LR",
         f'  subgraph asv["AS {d["own_as"]}(自社)"]',
         f'    V["{d["vname"]}"]']
    for ck in ("c1", "c2"):
        if ck in keys:
            L.append(f'    {ck.upper()}["{d["bname"][ck]}"]')
    L.append("  end")
    if keys & {"a1", "a2"} or d["kind"] in ("remote_lp", "lp_ebgp"):
        L.append(f'  subgraph aspa["AS {d["as_a"]}({d["ispa"]})"]')
        if "a1" in keys or d["kind"] in ("remote_lp", "lp_ebgp"):
            L.append(f'    A1["{d["ip"]["a1"]}"]')
        if "a2" in keys or d["kind"] == "remote_lp":
            L.append(f'    A2["{d["ip"]["a2"]}"]')
        if keys & {"c1", "c2"}:
            L.append('    PA["(上流)"]')
        L.append("  end")
    elif "c1" in keys or "c2" in keys:
        L.append(f'  subgraph aspa["AS {d["as_a"]}({d["ispa"]})"]')
        L.append('    PA["(上流)"]')
        L.append("  end")
    if "b1" in keys:
        L.append(f'  subgraph aspb["AS {d["as_b"]}({d["ispb"]})"]')
        L.append(f'    B1["{d["ip"]["b1"]}"]')
        L.append("  end")
    if "a1" in keys or d["kind"] in ("remote_lp", "lp_ebgp"):
        L.append("  V --- A1")
    if "a2" in keys or d["kind"] == "remote_lp":
        L.append("  V --- A2")
    if "b1" in keys:
        L.append("  V --- B1")
    for ck in ("c1", "c2"):
        if ck in keys:
            L.append(f"  V --- {ck.upper()}")
            L.append(f"  {ck.upper()} --- PA")
    L.append(f'  note["宛先: {d["prefix"]}/24(AS {d["far_as"]} 起源)"]')
    L.append("```")
    return "\n".join(L)


# ---------------------------------------------------------------- 要件
def requirements(d, rnd, form):
    reqs = []
    if form == "fix":
        w = d["world"]
        tgt = d.get("target")
        if w == "one_router":
            reqs = [f"{d['vname']} における、{d['prefix']}/24 への転送は、"
                    f"{path_label(d, tgt)}を、使用すること。",
                    "この変更の影響は、当該のルータに、限定されること。"
                    "AS 内の、ほかのルータの経路選択を、変更してはならない。",
                    "各事業者から受信するところの MED の値は、相互に調整されて"
                    "いない、独自の値である。経路選択の判断基準として、"
                    "使用してはならない。"]
        elif w == "whole_as":
            reqs = [f"AS {d['own_as']} 内の、すべてのルータにおいて、"
                    f"{d['prefix']}/24 への転送が、{path_label(d, tgt)}を、"
                    "使用すること。",
                    "個々のルータに対する、個別の設定の繰り返しは、"
                    "行わないこと。"]
        elif w == "return_med":
            reqs = [f"対向 AS({d['as_a']})から、自 AS の {d['own_prefix']}/24 へ"
                    f"向かうところの、戻りのトラフィックが、{d['ip']['a2']} 側の"
                    "リンクを、経由すること。",
                    "リンクの優先順位は、事業者との合意に基づき、MED に"
                    "よって、表現すること。"]
        elif w == "return_prepend":
            reqs = [f"対向 AS({d['as_a']})から、自 AS の {d['own_prefix']}/24 へ"
                    f"向かうところの、戻りのトラフィックが、{d['ip']['a2']} 側の"
                    "リンクを、経由すること。",
                    "広告するところの MED の値は、課金システムと連動して"
                    "おり、変更してはならない。"]
        elif w == "respect_med":
            reqs = ["事業者間の合意により、経路の優先順位は、MED によって、"
                    "表現されている。この合意が、経路選択の結果に、"
                    "反映されること。",
                    "個々の経路に対する、優先度の上書き(weight、および、"
                    "LOCAL_PREF)は、行わないこと。",
                    "対向 AS の機器の設定は、変更することが、できない。"]
        elif w == "igp_frozen":
            reqs = [f"{path_label(d, tgt)}が、ベストパスとして、"
                    "選出されること。",
                    "IGP(OSPF)の設定は、変更が、承認されていない。"]
        elif w == "bgp_frozen":
            reqs = [f"{path_label(d, tgt)}が、ベストパスとして、"
                    "選出されること。",
                    "BGP の設定は、変更が、承認されていない。"]
        reqs.append("なお、設定の投入後、変更は、適切に、反映されている"
                    "ものとする。")
    else:
        reqs = ["示されているところの出力、および、構成に基づいて、"
                "判断すること。",
                "なお、機器の構成は、示されている抜粋のほかは、"
                "既定値である。"]
    return reqs


# ---------------------------------------------------------------- 選択肢
def build_choices_read(d, rnd):
    """read= 現在のベストパスはどれか。"""
    c = [(path_label(d, d["winner"]), True, "")]
    for p in d["paths"]:
        if p["key"] == d["winner"]:
            continue
        step = lost_at(d, p["key"])
        if step == "nh":
            note = "next-hop が解決できず、ベストパス選択の候補に入らない。"
        elif step:
            note = f"{bm.STEP_JA[step]}の段で、除外される。"
        else:
            note = "選出されない。"
        c.append((path_label(d, p["key"]), False, note))
    if rnd.random() < 0.3:
        c.append(("いずれの経路も、ベストパスとして、選出されない",
                  False, "有効なベストパスは、選出されている。"))
    if len(c) < 3:
        raise ValueError("bgpbest read: 選択肢不足")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


WHY_TRAPS = {
    "weight": ["lp", "aspath", "med"],
    "lp": ["aspath", "weight", "med"],
    "localorig": ["lp", "aspath", "origin"],
    "aspath": ["origin", "med", "lp"],
    "origin": ["med", "aspath", "igp"],
    "med": ["aspath", "oldest", "origin"],
    "med_cross": ["med", "aspath", "ebgp"],
    "ebgp": ["med", "igp", "aspath"],
    "igp": ["rid", "oldest", "med"],
    "rid": ["oldest", "med", "nbr_ip"],
    "nh_invalid": ["lp", "med", "aspath"],
}


def _why_refute(d, step):
    """誤答段への反証文(機械的に判定して書く)。"""
    exp = d["expect"]
    if step == "med":
        alive_as = {p["nbr_as"] for p in d["paths"]
                    if p.get("nh_ok", True) and p.get("med") is not None}
        if len(alive_as) > 1 and not d["opts"].get("always_compare_med"):
            return ("MED は、異なる隣接 AS から受信した経路の間では、"
                    "既定では比較されない。")
    if step == "oldest" and d["opts"].get("compare_routerid"):
        return ("bgp bestpath compare-routerid が設定されているため、"
                "この段は使用されない。")
    if step == "nh":
        return "すべての候補の next-hop は、解決できている。"
    order = {s: i for i, s in enumerate(bm.STEPS)}
    if order.get(step, 99) < order.get(exp, 99):
        # ★その段が一部の候補を消していても「決着」はしていない、を区別する
        if step in {s for s, _sv, _k in d["trace"]}:
            return ("その段では、一部の候補が除外されるにとどまり、"
                    "決着していない。")
        return "その段では、候補の間に、差が付いていない。"
    return "その段に到達する前に、選択は、決着している。"


def build_choices_why(d, rnd):
    """why= 決め手となった段はどれか(用語理解を文脈内で問う)。"""
    exp = d["expect"]
    traps = [s for s in WHY_TRAPS.get(d["kind"], []) if s != exp]
    pool = [s for s in bm.STEPS
            if s not in traps and s != exp and s in bm.STEP_JA]
    rnd.shuffle(pool)
    steps = traps + pool[:max(0, 4 - len(traps))]
    c = [(bm.STEP_JA[exp], True, "")]
    for s in steps[:4]:
        c.append((bm.STEP_JA[s], False, _why_refute(d, s)))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _cli_of(d, ck):
    """fix 候補の CLI(状態収束形)。"""
    tgt = d.get("target")
    p = path_of(d, tgt) if tgt in {q["key"] for q in d["paths"]} else None
    own = d["own_as"]
    if ck == "W":
        return (f"router bgp {own}\n address-family ipv4\n"
                f"  neighbor {p['nbr_ip']} weight 30000")
    if ck == "LPIN":
        return ("route-map RM-PRIMARY-IN permit 10\n"
                " set local-preference 200\n"
                f"router bgp {own}\n address-family ipv4\n"
                f"  neighbor {p['nbr_ip']} route-map RM-PRIMARY-IN in")
    if ck == "PREP":
        return ("route-map RM-BACKUP-OUT permit 10\n"
                f" set as-path prepend {own} {own}\n"
                f"router bgp {own}\n address-family ipv4\n"
                f"  neighbor {d['ip']['a1']} route-map RM-BACKUP-OUT out")
    if ck == "MEDOUT":
        return ("route-map RM-MED-A permit 10\n set metric 200\n"
                "route-map RM-MED-B permit 10\n set metric 10\n"
                f"router bgp {own}\n address-family ipv4\n"
                f"  neighbor {d['ip']['a1']} route-map RM-MED-A out\n"
                f"  neighbor {d['ip']['a2']} route-map RM-MED-B out")
    if ck == "ACM":
        return f"router bgp {own}\n bgp always-compare-med"
    if ck == "NHS":
        return (f"! {d['bname']['c1']}(境界)にて\n"
                f"router bgp {own}\n address-family ipv4\n"
                f"  neighbor {d['rid_v']} next-hop-self")
    if ck == "NETIGP":
        return (f"! {d['bname']['c1']}(境界)にて\n"
                "router ospf 1\n"
                f" network {d['ext_net']['c1']} 0.0.0.255 area 0")
    if ck == "CLR":
        return "clear ip bgp * soft"
    raise KeyError(ck)


def _fix_refute(d, ck):
    fx = d["fix"]
    if fx["works"][ck] and not fx["complies"][ck]:
        return "経路は変わるが、要件(制約)に、適合しない。"
    if ck == "CLR":
        return "属性が変わっていないため、再評価だけでは、選択は変わらない。"
    if ck in ("PREP", "MEDOUT") and d["world"] not in ("return_med",
                                                       "return_prepend"):
        return "出方向の属性であり、戻りの方向にしか、作用しない。"
    if ck in ("LPIN", "W") and d["world"] in ("return_med", "return_prepend"):
        return "自ルータの選択にしか作用せず、戻りの方向は、変わらない。"
    if ck == "ACM":
        return "この盤面では、MED の比較結果は、選択を変えない。"
    if ck in ("LPIN", "W"):
        return "next-hop が解決できないままであり、候補に入らない。"
    return "この盤面では、経路選択の結果を、変えられない。"


def build_choices_fix(d, rnd):
    """fix= 要件を満たして経路を変える設定(被覆エンジン)。"""
    fx = d["fix"]
    c = []
    for ck in fx["cands"]:
        correct = ck == fx["answer"]
        # cli は行リストで持つ(render_options の 'cli' style の前提)
        c.append((FIX_CAND_JA[ck], correct,
                  "" if correct else _fix_refute(d, ck),
                  _cli_of(d, ck).split("\n")))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


REFUTES = {
    "med_cross": "隣接 AS が異なるため、この盤面では MED は比較されていない。",
    "weight_remote": "weight は設定されたルータの外には、作用しない。",
    "lp_ebgp": "この属性が eBGP で送信されることは、ない。",
    "nh_no_self": "next-hop は、すべての経路で、解決できている。",
    "remote_lp": "対向 AS の優先制御は、示されていない。",
    "no_clear": "示されている表には、設定後の属性が、反映されている。",
    "aspath_longer": "AS-PATH 長は、意図されている経路のほうが、"
                     "長いわけではない。",
}


def build_choices_cause(d, rnd):
    """cause= 意図したとおりにならない原因(claim は機械判定済み)。"""
    keys = cause_claim_keys(d)
    c = []
    for k in keys:
        t = claim_true(d, k)
        c.append((CLAIMS[k], t, "" if t else REFUTES[k]))
    if sum(1 for x in c if x[1]) != 1:
        raise ValueError("bgpbest cause: 真 claim が一意でない")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---------------------------------------------------------------- 検査
def _fidelity():
    """renderer 出力と PoC 実測行(results-raw.md 逐語)との byte 一致。"""
    def mk(key, **kw):
        return _mk(key, **kw)

    def row(d_over, p, first=True):
        d = {"prefix": "198.51.100.0", "plen": 24, "winner": "w", "opts": {}}
        d.update(d_over)
        return _row_txt(d, p, first)

    # B1: iBGP 行(LocPrf 100・(i マーカー)
    assert row({}, mk("x", nh="5.5.5.5", ebgp=False, med=0, lp_shown=100,
                      aspath=[65200])) == \
        " * i  198.51.100.0     5.5.5.5                  0    100      0 65200 i"
    # B3: weight 行(LocPrf 空欄・Weight 40000・ネットワーク列は継続行で空)
    assert row({"winner": "x"},
               mk("x", nh="10.0.13.3", med=0, weight=40000, aspath=[65200]),
               first=False) == \
        " *>                    10.0.13.3                0         40000 65200 i"
    # B17: MED 欠落= Metric 列が完全空欄・classful 非一致は /24 付き
    assert row({"prefix": "172.20.77.0", "winner": "x"},
               mk("x", nh="10.0.13.3", aspath=[65200, 65400])) == \
        " *>   172.20.77.0/24   10.0.13.3                              0 65200 65400 i"
    # B5: 自機起源行(0.0.0.0・32768・Path 列は origin のみ)
    assert row({"prefix": "203.0.113.0", "winner": "x"},
               mk("x", nh="0.0.0.0", local=True, ebgp=False, med=0,
                  weight=32768, aspath=[])) == \
        " *>   203.0.113.0      0.0.0.0                  0         32768 i"
    # B4: LP 200 行(eBGP 受信に in で付けた LP は表に出る)
    assert row({"winner": "x"},
               mk("x", nh="10.0.14.4", med=0, lp_shown=200,
                  aspath=[65300, 65300, 65300]), first=False) == \
        " *>                    10.0.14.4                0    200      0 65300 65300 65300 i"
    # B1: no best 過渡(read 形の提示)= `>` 無し(勝者でも `*` のみ)
    d1 = {"prefix": "198.51.100.0", "plen": 24, "winner": "x", "opts": {}}
    p1 = mk("x", nh="10.0.14.4", med=0, aspath=[65300])
    assert _row_txt(d1, p1, True, nobest=True) == \
        " *    198.51.100.0     10.0.14.4                0             0 65300 i"
    # detail の属性行・nh 行(B17/B3/B5/B12/B15 の実測断片)
    dd = {"prefix": "198.51.100.0", "plen": 24, "winner": "b", "opts": {},
          "rid_v": "1.1.1.1", "tblver": 4, "mon": "Aug", "day": 12, "h0": 11}
    ps = [mk("b", nh="10.0.13.3", nbr_ip="10.0.13.3", rid="3.3.3.3",
             aspath=[65200, 65400], age_rank=1, updated_min=1),
          mk("i", nh="5.5.5.5", nbr_ip="5.5.5.5", rid="5.5.5.5", ebgp=False,
             med=0, igp_metric=11, aspath=[65200], age_rank=2, updated_min=2),
          mk("d", nh="10.0.25.2", nbr_ip="5.5.5.5", rid="5.5.5.5", ebgp=False,
             med=0, nh_ok=False, aspath=[65200], age_rank=3, updated_min=3)]
    out = render_detail(dict(dd, paths=ps))
    assert "      Origin IGP, localpref 100, valid, external, best" in out
    assert "    5.5.5.5 (metric 11) from 5.5.5.5 (5.5.5.5)" in out
    assert "    10.0.25.2 (inaccessible) from 5.5.5.5 (5.5.5.5)" in out
    assert "      Origin IGP, metric 0, localpref 100, valid, internal" in out
    out2 = render_detail(dict(dd, paths=ps,
                              opts={"compare_routerid": True}))
    assert "\nBGP Bestpath: compare-routerid\n" in out2
    out3 = render_detail(dict(dd, paths=ps), nobest=True)
    assert "no best path)" in out3 and ", best" not in out3
    assert "  Not advertised to any peer" in out3
    print("  fidelity: 実測行との byte 一致 OK")


def _selftest(n=40):
    _fidelity()
    ng = 0
    for kind in KINDS:
        worlds = worlds_for(kind) or [None]
        for world in worlds:
            got, bad = 0, None
            for s in range(n * 20):
                try:
                    rnd = random.Random(7000 + s)
                    d = draw(rnd, kind=kind, world=world)
                    verify_choices(d)
                    # 各形の選択肢が実際に組めること(重複・非一意はここで落ちる)
                    for form in sorted(kind_forms(kind)):
                        if form == "read":
                            ch = build_choices_read(d, rnd)
                        elif form == "why":
                            ch = build_choices_why(d, rnd)
                        elif form == "cause":
                            ch = build_choices_cause(d, rnd)
                        elif form == "fix":
                            if not world:
                                continue
                            ch = build_choices_fix(d, rnd)
                        texts = [x[0] for x in ch]
                        if len(set(texts)) != len(texts):
                            raise ValueError(f"{form}: 選択肢テキスト重複")
                        if sum(1 for x in ch if x[1]) != 1:
                            raise ValueError(f"{form}: 正解が一意でない")
                    got += 1
                    if got >= n:
                        break
                except ValueError as e:
                    bad = str(e)
                    continue
            status = "OK" if got >= n else f"NG({got}/{n}) 例: {bad}"
            if got < n:
                ng += 1
            print(f"  {kind:14s} world={str(world):15s} {status}")
    print(f"gen_paper_bgpbest selftest: NG={ng}")
    return ng == 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    d = draw(random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
    import json
    print(json.dumps({k: v for k, v in d.items() if k != "trace"},
                     ensure_ascii=False, indent=1, default=str))
