#!/usr/bin/env python3
"""BGP ベストパス決定リスト評価器 (BL-112・shape=bgpbest の土台)。

`aaa_model.py` と同じ位置づけ: 小さい純関数・状態なし。
各段の挙動は PoC 実測(poc/bgpbest/README.md の B 番号・poc/bgp-ring の P 番号)に紐付く。

★スコープ:
  - 段9(multipath)・段12(cluster list)・confederation・`bgp deterministic-med` は範囲外。
  - ★MED の順序依存(3経路以上×異AS混在の有名問題)は**モデル化しない**。
    順序依存が起き得る盤面は `best(strict=True)` が ValueError を投げ、
    生成器側で draw を捨てる(モデルが黙って誤答するより安全)。
    順序非依存の十分条件 = acm ON / MED が異なる複数経路グループが唯一 /
    各グループ内で MED が全て等しい(=MED が何も消さない)。

path(dict) のキー:
  key       盤面での識別子(例 "RT02")
  nh        next-hop 文字列
  nh_ok     next-hop が解決可能か(False= inaccessible・候補外) [B15]
  weight    int(既定0・自機起源32768) [B3/B5]
  lp        int or None(None= 受信時 LOCAL_PREF 無し。実効 100) [B4]
  local     bool 自機起源
  aspath    list[int](prepend も展開して数える) [B4]
  origin    "i" | "e" | "?" [B7]
  med       int or None(None= 欠落。既定 0 扱い) [B8/B10]
  ebgp      bool [B11]
  nbr_as    int or None(隣接AS= MED 比較グループ) [B8 vs bgp-ring P4]
  igp_metric int(next-hop への IGP メトリック。直結/自機= 0) [B12]
  age_rank  int(小さいほど古い=先着) [B13]
  rid       ピアの BGP RID(dotted) [B13]
  nbr_ip    ピアアドレス(最終タイブレーク。盤面では使わない)

opts(dict): always_compare_med / med_missing_as_worst / compare_routerid
"""

STEPS = ["nh", "weight", "lp", "local", "aspath", "origin", "med",
         "ebgp", "igp", "oldest", "rid", "nbr_ip"]

ORIGIN_RANK = {"i": 0, "e": 1, "?": 2}
MED_INF = 4294967295

# 段→日本語(why 形の選択肢・解説で使う)
STEP_JA = {
    "nh": "next-hop の解決可否(そもそも候補に入らない)",
    "weight": "weight(大きいほうが優先)",
    "lp": "LOCAL_PREF(大きいほうが優先)",
    "local": "自機起源の経路の優先",
    "aspath": "AS-PATH 長(短いほうが優先)",
    "origin": "origin コード(i < e < ?)",
    "med": "MED(小さいほうが優先)",
    "ebgp": "eBGP > iBGP",
    "igp": "next-hop への IGP メトリック(小さいほうが優先)",
    "oldest": "最も古い経路(eBGP 同士のタイ)",
    "rid": "送り手の BGP ルータ ID(小さいほうが優先)",
    "nbr_ip": "近隣アドレス(小さいほうが優先)",
    "only": "有効な候補が 1 本しかない",
}


def lp_eff(p):
    v = p.get("lp")
    return 100 if v is None else v


def med_eff(p, opts):
    if p.get("med") is None:
        return MED_INF if opts.get("med_missing_as_worst") else 0
    return p["med"]


def _ip_key(ip):
    return tuple(int(x) for x in ip.split("."))


def _med_groups(paths):
    g = {}
    for p in paths:
        g.setdefault(p.get("nbr_as"), []).append(p)
    return g


def med_order_independent(paths, opts):
    """MED 段が順序非依存で決まる盤面か(docstring の十分条件)。"""
    if opts.get("always_compare_med"):
        return True
    groups = _med_groups(paths)
    hot = [as_ for as_, ps in groups.items()
           if len(ps) >= 2 and len({med_eff(p, opts) for p in ps}) > 1]
    return not hot or (len(hot) == 1 and len(groups) == 1)


def med_default_exercised(paths, opts):
    """『MED 欠落 vs 有値』の比較が実際に起きる盤面か。

    ★欠落=0 扱い(missing-as-worst で反転)は RFC/文書上の既定だが、
    **B10 の測定は失敗した**(network 起源は必ず MED=0 を付けるため、
    route-map を外しても「欠落」にならない=真の欠落は 2 AS ホップ経路
    のみ・B17)。未実測の比較規則に依存する盤面は strict で拒否する。
    """
    def mixed(ps):
        v = [p.get("med") is None for p in ps]
        return any(v) and not all(v)
    if opts.get("always_compare_med"):
        return mixed(paths)
    return any(len(ps) >= 2 and mixed(ps)
               for ps in _med_groups(paths).values())


def _min_keep(paths, keyfn):
    lo = min(keyfn(p) for p in paths)
    return [p for p in paths if keyfn(p) == lo]


def _max_keep(paths, keyfn):
    hi = max(keyfn(p) for p in paths)
    return [p for p in paths if keyfn(p) == hi]


def best(paths, opts=None, strict=True):
    """勝者と決め手を返す。

    返り値: {"winner": key or None, "step": 段名, "trace": [...]}
      trace= [(step, 通過した key 列, 消えた key 列)] — 消去が起きた段のみ記録。
    strict=True で MED 順序依存の盤面に ValueError(生成器は draw を捨てる)。
    """
    opts = opts or {}
    trace = []
    alive = [p for p in paths if p.get("nh_ok", True)]
    dropped = [p["key"] for p in paths if not p.get("nh_ok", True)]
    if dropped:
        trace.append(("nh", [p["key"] for p in alive], dropped))
    if not alive:
        return {"winner": None, "step": "nh", "trace": trace}
    if len(alive) == 1:
        return {"winner": alive[0]["key"],
                "step": "nh" if dropped else "only", "trace": trace}

    def cut(step, survivors):
        nonlocal alive
        if len(survivors) < len(alive):
            trace.append((step, [p["key"] for p in survivors],
                          [p["key"] for p in alive
                           if p not in survivors]))
            alive = survivors
        return len(alive) == 1

    if cut("weight", _max_keep(alive, lambda p: p.get("weight", 0))):
        return _fin(alive, "weight", trace)
    if cut("lp", _max_keep(alive, lp_eff)):
        return _fin(alive, "lp", trace)
    if any(p.get("local") for p in alive):
        if cut("local", [p for p in alive if p.get("local")]):
            return _fin(alive, "local", trace)
    if cut("aspath", _min_keep(alive, lambda p: len(p.get("aspath", [])))):
        return _fin(alive, "aspath", trace)
    if cut("origin", _min_keep(alive, lambda p: ORIGIN_RANK[p.get("origin", "i")])):
        return _fin(alive, "origin", trace)

    # --- MED(順序依存の検査 → グループ内最小のみ残す)
    if strict and not med_order_independent(alive, opts):
        raise ValueError("MED order-dependent board (rejected)")
    if strict and med_default_exercised(alive, opts):
        raise ValueError("MED missing/present mixed (unverified default)")
    if opts.get("always_compare_med"):
        if cut("med", _min_keep(alive, lambda p: med_eff(p, opts))):
            return _fin(alive, "med", trace)
    else:
        keep = []
        for ps in _med_groups(alive).values():
            keep += _min_keep(ps, lambda p: med_eff(p, opts))
        if cut("med", keep):
            return _fin(alive, "med", trace)

    if any(p.get("ebgp") for p in alive) and not all(
            p.get("ebgp") for p in alive):
        if cut("ebgp", [p for p in alive if p.get("ebgp")]):
            return _fin(alive, "ebgp", trace)
    if cut("igp", _min_keep(alive, lambda p: p.get("igp_metric", 0))):
        return _fin(alive, "igp", trace)
    if all(p.get("ebgp") for p in alive) and not opts.get("compare_routerid"):
        if cut("oldest", _min_keep(alive, lambda p: p["age_rank"])):
            return _fin(alive, "oldest", trace)
    if cut("rid", _min_keep(alive, lambda p: _ip_key(p["rid"]))):
        return _fin(alive, "rid", trace)
    if cut("nbr_ip", _min_keep(alive, lambda p: _ip_key(p["nbr_ip"]))):
        return _fin(alive, "nbr_ip", trace)
    raise ValueError(f"tie not broken: {[p['key'] for p in alive]}")


def _fin(alive, step, trace):
    return {"winner": alive[0]["key"], "step": step, "trace": trace}


# ---------------------------------------------------------------- selftest
def _p(key, **kw):
    d = {"key": key, "nh": "10.0.0.1", "nh_ok": True, "weight": 0, "lp": None,
         "local": False, "aspath": [65200], "origin": "i", "med": None,
         "ebgp": True, "nbr_as": 65200, "igp_metric": 0, "age_rank": 9,
         "rid": "9.9.9.9", "nbr_ip": "10.0.0.1"}
    d.update(kw)
    return d


def selftest():
    ok = [0]

    def chk(name, got, want):
        assert got == want, f"{name}: got={got} want={want}"
        ok[0] += 1

    # B3: weight は全段に先行(AS長・LP が不利でも勝つ)
    r = best([_p("a", weight=40000, aspath=[65200, 65200, 65200]),
              _p("b", lp=500), _p("c", aspath=[65300])])
    chk("B3 weight", (r["winner"], r["step"]), ("a", "weight"))
    # B4: LP は AS-PATH 長より強い
    r = best([_p("a", lp=200, aspath=[65300] * 3), _p("b", aspath=[65200])])
    chk("B4 lp", (r["winner"], r["step"]), ("a", "lp"))
    # B5: 自機起源は weight 32768 で勝つ(=決め手は weight 段)
    r = best([_p("a", weight=32768, local=True, aspath=[], ebgp=False,
                 nbr_as=None, nh="0.0.0.0", rid="1.1.1.1"),
              _p("b", aspath=[65200])])
    chk("B5 local32768", (r["winner"], r["step"]), ("a", "weight"))
    # B7: origin i < ?
    r = best([_p("a", origin="?", age_rank=1, rid="2.2.2.2"),
              _p("b", origin="i", age_rank=2, rid="3.3.3.3")])
    chk("B7 origin", (r["winner"], r["step"]), ("b", "origin"))
    # B8: MED 同一隣接AS = 小さい方
    r = best([_p("a", med=200, age_rank=1), _p("b", med=50, age_rank=2)])
    chk("B8 med", (r["winner"], r["step"]), ("b", "med"))
    # bgp-ring P4: 異AS の MED は比較されず後段(oldest)で決まる
    r = best([_p("a", med=200, nbr_as=65200, age_rank=1, rid="2.2.2.2"),
              _p("b", med=50, nbr_as=65300, aspath=[65300], age_rank=2,
                 rid="3.3.3.3")])
    chk("P4 med_cross", (r["winner"], r["step"]), ("a", "oldest"))
    # bgp-ring P4: always-compare-med で MED 決着に変わる
    r = best([_p("a", med=200, nbr_as=65200, age_rank=1),
              _p("b", med=50, nbr_as=65300, aspath=[65300], age_rank=2)],
             {"always_compare_med": True})
    chk("P4 acm", (r["winner"], r["step"]), ("b", "med"))
    # ★B10 は測定不能だった(network 起源は常に MED=0 を付ける)。
    #   「欠落 vs 有値」の比較を含む盤面は strict で拒否されること。
    try:
        best([_p("a", med=None, age_rank=2), _p("b", med=200, age_rank=1)])
        raise AssertionError("missing/present mixed が素通りした")
    except ValueError:
        ok[0] += 1
    # 欠落同士(比較で何も起きない)は許容= igp 種の自然形(B17)
    r = best([_p("a", med=None, ebgp=False, igp_metric=11, rid="5.5.5.5",
                 age_rank=2),
              _p("b", med=None, ebgp=False, igp_metric=101, rid="6.6.6.6",
                 age_rank=1)])
    chk("B17 both-missing ok", (r["winner"], r["step"]), ("a", "igp"))
    # B11: eBGP > iBGP(MED は異ASなので比較されない)
    r = best([_p("a", nbr_as=65300, aspath=[65300]),
              _p("b", ebgp=False, nh="5.5.5.5", igp_metric=11,
                 rid="5.5.5.5", age_rank=1)])
    chk("B11 ebgp", (r["winner"], r["step"]), ("a", "ebgp"))
    # B12: iBGP 同士は IGP メトリック
    r = best([_p("a", ebgp=False, igp_metric=101, rid="6.6.6.6", age_rank=1),
              _p("b", ebgp=False, igp_metric=11, rid="5.5.5.5", age_rank=2)])
    chk("B12 igp", (r["winner"], r["step"]), ("b", "igp"))
    # B13: eBGP 全段タイ → oldest / compare-routerid で RID
    r = best([_p("a", age_rank=2, rid="2.2.2.2"),
              _p("b", age_rank=1, rid="3.3.3.3")])
    chk("B13 oldest", (r["winner"], r["step"]), ("b", "oldest"))
    r = best([_p("a", age_rank=2, rid="2.2.2.2"),
              _p("b", age_rank=1, rid="3.3.3.3")], {"compare_routerid": True})
    chk("B13 rid", (r["winner"], r["step"]), ("a", "rid"))
    # ★iBGP 同士のタイは oldest を飛ばして RID(compare-routerid 不要)
    r = best([_p("a", ebgp=False, age_rank=2, rid="2.2.2.2", igp_metric=11),
              _p("b", ebgp=False, age_rank=1, rid="3.3.3.3", igp_metric=11)])
    chk("iBGP tie rid", (r["winner"], r["step"]), ("a", "rid"))
    # B15: nh 解決不能は属性がどれだけ良くても候補外
    r = best([_p("a", lp=500, nh_ok=False, ebgp=False, rid="5.5.5.5"),
              _p("b")])
    chk("B15 inaccessible", (r["winner"], r["step"]), ("b", "nh"))
    # MED 順序依存の盤面は strict で拒否される
    try:
        best([_p("a", med=10, nbr_as=65200, aspath=[65200]),
              _p("b", med=200, nbr_as=65200, aspath=[65200]),
              _p("c", med=50, nbr_as=65300, aspath=[65300])])
        raise AssertionError("MED unsafe board が素通りした")
    except ValueError:
        ok[0] += 1
    # 同一グループ内の MED が等値なら異AS混在でも安全(何も消えない)
    r = best([_p("a", med=100, nbr_as=65200, age_rank=1),
              _p("b", med=100, nbr_as=65200, age_rank=2),
              _p("c", med=999, nbr_as=65300, aspath=[65300], age_rank=3)])
    chk("MED no-op safe", r["winner"], "a")
    print(f"bgpbest_model selftest: {ok[0]} checks OK")


if __name__ == "__main__":
    selftest()
