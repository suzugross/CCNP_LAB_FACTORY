#!/usr/bin/env python3
"""OSPF パス選好 決定リスト評価器 (BL-127・shape=pref の OSPF 側)。

`bgpbest_model.py` と同じ位置づけ: 小さい純関数・状態なし。
設計= problems/_drafts/PREF-PAPER.design.md §2.1。実測= poc/pref/README.md。

★スコープ:
  - 型優先(intra > inter > E1/N1 > E2/N2)→ メトリック → (E2/N2 のみ)forward metric。
  - **完全タイ= 実機は ECMP**。「1本を選ぶ」設問が壊れるので `best(strict=True)` は
    ValueError を投げ、生成器側で draw を捨てる(bgpbest の strict 拒否の踏襲)。
    ECMP そのものを問う形は `installed()` を使う。
  - E1/N1 と E2/N2 は同順位(NSSA 内から見た表示違い)。同順位混在の盤面は
    `best(strict=True)` が拒否する(同一プレフィックスに対し E1 と N1 が
    同時に見える盤面は本ファミリの範囲外)。
  - AD(110)は全型共通なので比較に入れない。外部の AD 変更・distance ospf は範囲外。

path(dict) のキー:
  key    盤面での識別子(例 "via RT02")
  kind   "intra" | "inter" | "e1" | "e2" | "n1" | "n2"
  cost   int  intra/inter のメトリック(観測点からの合計コスト)
  ext    int  外部メトリック(E1/E2/N1/N2。LSA の Metric 値)
  fwd    int  ASBR までの内部コスト(= detail の forward metric)
  rid    str  広告元 RID(表示・解説用。選好には使わない)
"""

TYPE_RANK = {"intra": 0, "inter": 1, "e1": 2, "n1": 2, "e2": 3, "n2": 3}
EXTERNAL = ("e1", "e2", "n1", "n2")
TYPE2 = ("e2", "n2")          # forward metric 段を持つ型
STEPS = ["type", "metric", "fwd"]

# 段→日本語(why 形の選択肢・解説で使う)
STEP_JA = {
    "type": "経路の型(intra > inter > E1 > E2)。メトリックより先に効く",
    "metric": "メトリック(小さいほうが優先)",
    "fwd": "forward metric(E2 同値時の第2段= ASBR までの内部コスト)",
    "only": "候補が 1 本しかない",
}

TYPE_JA = {"intra": "エリア内(O)", "inter": "エリア間(O IA)",
           "e1": "外部タイプ1(O E1)", "e2": "外部タイプ2(O E2)",
           "n1": "NSSA 外部タイプ1(O N1)", "n2": "NSSA 外部タイプ2(O N2)"}

# 表示用の型ラベル(`show ip route` の左端)
TYPE_CODE = {"intra": "O", "inter": "O IA", "e1": "O E1", "e2": "O E2",
             "n1": "O N1", "n2": "O N2"}


def metric_eff(p):
    """RIB/表に出るメトリック。

    - intra/inter: cost をそのまま
    - E1/N1: **外部メトリック + ASBR までの内部コスト**(累積)
    - E2/N2: 外部メトリック固定(内部コストは載らない)
    """
    k = p["kind"]
    if k in ("e1", "n1"):
        return p["ext"] + p["fwd"]
    if k in TYPE2:
        return p["ext"]
    return p["cost"]


def _min_keep(paths, keyfn):
    lo = min(keyfn(p) for p in paths)
    return [p for p in paths if keyfn(p) == lo]


def _mixed_same_rank(paths):
    """同順位(E1×N1 / E2×N2)が混在しているか= 未検証の比較規則。"""
    for a, b in (("e1", "n1"), ("e2", "n2")):
        ks = {p["kind"] for p in paths}
        if a in ks and b in ks:
            return True
    return False


def best(paths, strict=True):
    """勝者と決め手の段を返す。

    返り値: {"winner": key, "step": 段名, "trace": [(step, 残った key 列, 消えた key 列)]}
    strict=True で「完全タイ(= 実機は ECMP)」と「同順位型の混在」に ValueError。
    """
    if not paths:
        return {"winner": None, "step": None, "trace": []}
    if strict and _mixed_same_rank(paths):
        raise ValueError("same-rank external types mixed (rejected)")
    alive = list(paths)
    trace = []
    if len(alive) == 1:
        return {"winner": alive[0]["key"], "step": "only", "trace": trace}

    def cut(step, survivors):
        nonlocal alive
        if len(survivors) < len(alive):
            trace.append((step, [p["key"] for p in survivors],
                          [p["key"] for p in alive if p not in survivors]))
            alive = survivors
        return len(alive) == 1

    if cut("type", _min_keep(alive, lambda p: TYPE_RANK[p["kind"]])):
        return {"winner": alive[0]["key"], "step": "type", "trace": trace}
    if cut("metric", _min_keep(alive, metric_eff)):
        return {"winner": alive[0]["key"], "step": "metric", "trace": trace}
    if all(p["kind"] in TYPE2 for p in alive):
        if cut("fwd", _min_keep(alive, lambda p: p["fwd"])):
            return {"winner": alive[0]["key"], "step": "fwd", "trace": trace}
    if strict:
        raise ValueError(f"ECMP tie: {[p['key'] for p in alive]}")
    return {"winner": alive[0]["key"], "step": "ecmp", "trace": trace}


def installed(paths):
    """RIB に載る経路の key 集合(タイは ECMP として全部返す)。"""
    r = best(paths, strict=False)
    if r["winner"] is None:
        return []
    alive = list(paths)
    alive = _min_keep(alive, lambda p: TYPE_RANK[p["kind"]])
    alive = _min_keep(alive, metric_eff)
    if all(p["kind"] in TYPE2 for p in alive):
        alive = _min_keep(alive, lambda p: p["fwd"])
    return [p["key"] for p in alive]


# ---------------------------------------------------------------- selftest
def _p(key, kind="intra", **kw):
    d = {"key": key, "kind": kind, "cost": 10, "ext": 20, "fwd": 10,
         "rid": "9.9.9.9"}
    d.update(kw)
    return d


def selftest():
    ok = [0]

    def chk(name, got, want):
        assert got == want, f"{name}: got={got} want={want}"
        ok[0] += 1

    # O2: intra(コスト510) > inter(コスト21) — 型がメトリックに先行
    r = best([_p("a", "intra", cost=510), _p("b", "inter", cost=21)])
    chk("O2 type intra>inter", (r["winner"], r["step"]), ("a", "type"))
    # O3: E1(累積110) > E2(10) — 型が先
    r = best([_p("a", "e1", ext=100, fwd=10), _p("b", "e2", ext=10, fwd=100)])
    chk("O3 type e1>e2", (r["winner"], r["step"]), ("a", "type"))
    # O5: E1 の実効メトリックは累積
    chk("O5 e1 accum", metric_eff(_p("a", "e1", ext=100, fwd=60)), 160)
    chk("O5 e2 fixed", metric_eff(_p("a", "e2", ext=20, fwd=60)), 20)
    # O4: E2 同値 → forward metric
    r = best([_p("a", "e2", ext=20, fwd=10), _p("b", "e2", ext=20, fwd=100)])
    chk("O4 fwd", (r["winner"], r["step"]), ("a", "fwd"))
    # E1 同士は累積後のメトリックで決まる(forward metric 段には落ちない)
    r = best([_p("a", "e1", ext=100, fwd=10), _p("b", "e1", ext=50, fwd=10)])
    chk("E1 metric", (r["winner"], r["step"]), ("b", "metric"))
    # inter 同士はコスト比較
    r = best([_p("a", "inter", cost=30), _p("b", "inter", cost=20)])
    chk("inter metric", (r["winner"], r["step"]), ("b", "metric"))
    # ★完全タイ(E1 同士・累積も同じ)は ECMP → strict で拒否
    try:
        best([_p("a", "e1", ext=100, fwd=10), _p("b", "e1", ext=100, fwd=10)])
        raise AssertionError("ECMP タイが素通りした")
    except ValueError:
        ok[0] += 1
    chk("ECMP installed", sorted(installed(
        [_p("a", "e1", ext=100, fwd=10), _p("b", "e1", ext=100, fwd=10)])),
        ["a", "b"])
    # ★E2 同士で ext も fwd も同じ = ECMP
    try:
        best([_p("a", "e2", ext=20, fwd=10), _p("b", "e2", ext=20, fwd=10)])
        raise AssertionError("E2 完全タイが素通りした")
    except ValueError:
        ok[0] += 1
    # ★同順位型の混在(E1×N1)は拒否
    try:
        best([_p("a", "e1"), _p("b", "n1")])
        raise AssertionError("同順位混在が素通りした")
    except ValueError:
        ok[0] += 1
    # N2 は E2 と同じ段構成(NSSA 内観測)
    r = best([_p("a", "n2", ext=20, fwd=5), _p("b", "n2", ext=20, fwd=50)])
    chk("N2 fwd", (r["winner"], r["step"]), ("a", "fwd"))
    # 1本しかない
    r = best([_p("a", "e2")])
    chk("only", (r["winner"], r["step"]), ("a", "only"))
    print(f"ospfpref_model selftest: {ok[0]} checks OK")


if __name__ == "__main__":
    selftest()
