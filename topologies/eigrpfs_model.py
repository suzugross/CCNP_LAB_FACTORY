#!/usr/bin/env python3
"""EIGRP FD/RD/FC/variance 評価器 (BL-127・shape=pref の EIGRP 側)。

`bgpbest_model.py` と同じ位置づけ: 小さい純関数・状態なし。
設計= problems/_drafts/PREF-PAPER.design.md §2.2。実測= poc/pref/README.md。

★スコープ:
  - 古典メトリック(K1/K3 既定)を **整数値として与える**。K 値変更・wide metric は範囲外。
  - FC は **RD < FD(successor)** の厳密不等号(等号は不成立)。PoC E2 で実測する軸。
  - `variance N` が乗せるのは **FS のみ**。FC 不成立の経路は倍率をいくら上げても
    乗らない(本ファミリ最大のひっかけ)。
  - successor が複数(FD 同値)= 等コスト ECMP。「1本が successor」という設問が
    壊れるので `successor(strict=True)` は ValueError(生成器が draw を捨てる)。

path(dict) のキー:
  key   識別子(例 "via 10.20.12.2 (RT02)")
  rd    Reported Distance(隣接が申告する距離)
  cost  自分から隣接までのリンクコスト(FD = rd + cost)
"""


def fd(p):
    """この経路を使ったときの Feasible Distance(topology 表示の左値)。"""
    return p["rd"] + p["cost"]


def successor(paths, strict=True):
    """FD 最小の経路。strict=True で FD 同値(ECMP)を拒否。"""
    if not paths:
        return None
    lo = min(fd(p) for p in paths)
    tie = [p for p in paths if fd(p) == lo]
    if len(tie) > 1:
        if strict:
            raise ValueError(f"equal-cost successors: {[p['key'] for p in tie]}")
        tie.sort(key=lambda p: p["key"])
    return tie[0]


def fd_succ(paths, strict=True):
    return fd(successor(paths, strict=strict))


def is_fc(p, fdsucc):
    """フィージビリティ条件: RD < successor の FD(**等号は不成立**)。"""
    return p["rd"] < fdsucc


def all_fs(paths, strict=True):
    """FS の key 集合(★successor 自身は含めない)。

    「successor 以外で FC を満たすもの」= 教科書どおりの FS 定義。
    設問文でも「現在の successor を除き」と明示する(allthat 形の一意性のため)。
    """
    s = successor(paths, strict=strict)
    f = fd(s)
    return [p["key"] for p in paths if p is not s and is_fc(p, f)]


def variance_installed(paths, v=1, strict=True):
    """`variance v` を入れたとき RIB に載る経路の key 集合(順序= FD 昇順)。

    successor ∪ { FS かつ FD <= v * FD(successor) }。
    ★FC 不成立の経路は v をいくら上げても入らない。
    """
    s = successor(paths, strict=strict)
    f = fd(s)
    fs = set(all_fs(paths, strict=strict))
    keep = [p for p in paths
            if p is s or (p["key"] in fs and fd(p) <= v * f)]
    keep.sort(key=lambda p: (fd(p), p["key"]))
    return [p["key"] for p in keep]


def min_variance_for(paths, key, strict=True):
    """その経路を乗せるのに必要な最小の variance 値。載せられないなら None。

    (FC 不成立なら None= 「倍率では解決しない」の機械的な根拠)
    """
    s = successor(paths, strict=strict)
    f = fd(s)
    tgt = next((p for p in paths if p["key"] == key), None)
    if tgt is None or tgt is s:
        return 1
    if not is_fc(tgt, f):
        return None
    need = fd(tgt) / f
    v = int(need)
    while v * f < fd(tgt):
        v += 1
    return max(v, 1)


def is_visible(p, fdsucc):
    """その経路が観測点の topology 表に**現れる**か(スプリット・ホライズン)。

    ★PoC 実測(poc/pref §E1/E4): RD が大きい経路は、隣接自身の最良経路が
    「観測点を経由する向き」に反転する。すると隣接はその経路を観測点へ
    広告し返さないので、**topology 表(all-links を含む)から丸ごと消える**。
    条件= 隣接の直行距離 RD < 隣接が観測点経由で得る距離(FD_succ + 逆向きコスト)。
    リンク対称(往復のコストが同値)を前提に p["cost"] を逆向きコストの代用にする。

    → 非 FC の経路を**表に見せたい**盤面は RD が
      [FD_succ, FD_succ + cost) の窓に入っていなければならない。
      窓を外れた盤面は紙面では描けても実機で再現できない(E2E 照合が壊れる)。
    """
    return p["rd"] < fdsucc + p["cost"]


def check_board(paths, strict=True):
    """紙面盤面として成立するか。不成立なら ValueError(生成器は draw を捨てる)。"""
    f = fd_succ(paths, strict=strict)
    bad = [p["key"] for p in paths if not is_visible(p, f)]
    if bad and strict:
        raise ValueError(f"split-horizon invisible paths: {bad}")
    return not bad


def classify(paths, strict=True):
    """各経路の位置づけ: "successor" | "fs" | "non_fc"。"""
    s = successor(paths, strict=strict)
    f = fd(s)
    out = {}
    for p in paths:
        if p is s:
            out[p["key"]] = "successor"
        elif is_fc(p, f):
            out[p["key"]] = "fs"
        else:
            out[p["key"]] = "non_fc"
    return out


ROLE_JA = {"successor": "サクセサ(現在の最短)",
           "fs": "フィージブルサクセサ(FC 成立)",
           "non_fc": "FC 不成立(RD がサクセサの FD 以上)"}


# ---------------------------------------------------------------- selftest
def _p(key, rd, cost):
    return {"key": key, "rd": rd, "cost": cost}


def selftest():
    ok = [0]

    def chk(name, got, want):
        assert got == want, f"{name}: got={got} want={want}"
        ok[0] += 1

    # PoC 盤面(poc/pref §E1): A=successor / B=FS / C=FC不成立
    A = _p("A", 409600, 25600)      # FD 435200
    B = _p("B", 409600, 76800)      # FD 486400 (RD < 435200 → FS)
    C = _p("C", 486400, 25600)      # FD 512000 (RD >= 435200 → 非FC)
    paths = [A, B, C]
    chk("successor", successor(paths)["key"], "A")
    chk("fd_succ", fd_succ(paths), 435200)
    chk("all_fs", all_fs(paths), ["B"])
    chk("classify", classify(paths),
        {"A": "successor", "B": "fs", "C": "non_fc"})
    # variance: 既定 1 は successor のみ / 2 で FS が乗る / C は乗らない
    chk("var1", variance_installed(paths, 1), ["A"])
    chk("var2", variance_installed(paths, 2), ["A", "B"])
    chk("var8 non_fc stays out", variance_installed(paths, 8), ["A", "B"])
    chk("min_var B", min_variance_for(paths, "B"), 2)
    chk("min_var C(非FC)", min_variance_for(paths, "C"), None)
    # ★等号は FC 不成立(RD == FD(successor))
    D = _p("D", 435200, 25600)
    chk("equal is not fc", all_fs([A, D]), [])
    chk("equal not installed", variance_installed([A, D], 4), ["A"])
    # 倍率境界: FS だが FD が範囲外(921600 > 2*435200)
    E = _p("E", 409600, 512000)     # FD 921600
    chk("var2 out of range", variance_installed([A, E], 2), ["A"])
    chk("var3 in range", variance_installed([A, E], 3), ["A", "E"])
    chk("min_var E", min_variance_for([A, E], "E"), 3)
    # FD 同値(ECMP)は strict で拒否
    try:
        successor([_p("x", 400000, 35200), _p("y", 410000, 25200)])
        raise AssertionError("等コストが素通りした")
    except ValueError:
        ok[0] += 1
    # ★スプリット・ホライズン(PoC E1/E4 の実測): PoC 盤面の C は
    #   RD 486400 >= FD_succ 435200 + cost 25600 = 460800 → 実機では表に出ない
    chk("C は不可視", is_visible(C, fd_succ(paths)), False)
    try:
        check_board(paths)
        raise AssertionError("不可視経路を含む盤面が素通りした")
    except ValueError:
        ok[0] += 1
    # 窓の中(RD 448000 ∈ [435200, 460800))なら非FC のまま可視
    C2 = _p("C2", 448000, 25600)     # FD 473600
    chk("C2 は可視", is_visible(C2, fd_succ([A, C2])), True)
    chk("C2 は非FC", classify([A, B, C2])["C2"], "non_fc")
    chk("C2 盤面OK", check_board([A, B, C2]), True)
    # 等号ケース(RD == FD_succ)は窓の下端 → 可視(PoC E2 で実機確認済)
    chk("D は可視", is_visible(D, fd_succ([A, D])), True)
    print(f"eigrpfs_model selftest: {ok[0]} checks OK")


if __name__ == "__main__":
    selftest()
