#!/usr/bin/env python3
"""RT(route-target) の import/export 集合 → VRF 表の到達 を評価する純関数 (BL-169・shape=mpls)。

`ospfpref_model.py` と同じ位置づけ: 小さい純関数・状態なし。
設計= problems/_drafts/PAPER-MPLS.design.md §6。実測との突合= poc/mpls-paper/README.md M6〜M9
(★PoC 完了までは「規格どおりの意味論」を暫定の正典とし、突合後に selftest の期待値を実測に合わせる)。

vrfs(dict) の形:
  {name: {"pe": "PE1", "rd": "65000:100",
          "imp": {"65000:100"}, "exp": {"65000:100"},
          "nets": ["172.16.1.0/24"]}}

規則(モデルの範囲):
  - VRF X の表に、VRF Y の nets が載る  ⇔  Y.exp ∩ X.imp ≠ ∅ (同一 PE 上の VRF 同士でも同じ)。
    自 VRF の nets は常に載る。RD はこの判定に**関与しない**(VPNv4 キーの一意化だけ)。
  - PE の VPNv4 表 = 自 PE の全 VRF の nets(各 VRF の rd 付き)
                   + 他 PE の VRF の nets のうち、自 PE のいずれかの VRF の imp と交わるもの
                     (自動 RT フィルタ。RR や `no bgp default route-target filter` は範囲外)。
  - ★PoC M8(IOL 17.15・2026-09-13)= 同一ルータ内で RD は重複できない
    (`% RD 65000:100 already in use by VRF CUST_A` で拒否)。よって同一 PE 上の 2 VRF が
    同じ RD を持つ盤面は不成立(ValueError)。PE 間では同じ RD でも構わない(規格どおり)。
"""

def _check(vrfs):
    for n, v in vrfs.items():
        for k in ("pe", "rd", "imp", "exp", "nets"):
            if k not in v:
                raise ValueError(f"vrf {n}: {k} が無い")


def visible(vrfs, x):
    """VRF x の表に載る {(prefix, src_vrf)}。"""
    _check(vrfs)
    out = {(p, x) for p in vrfs[x]["nets"]}
    for y, vy in vrfs.items():
        if y == x:
            continue
        if set(vy["exp"]) & set(vrfs[x]["imp"]):
            out |= {(p, y) for p in vy["nets"]}
    return out


def reach(vrfs):
    """全 VRF の表 {vrf: {(prefix, src_vrf)}}。"""
    return {x: visible(vrfs, x) for x in vrfs}


def matrix(vrfs):
    """{(src_vrf, dst_vrf): bool} — src の nets が dst の表に載るか(片方向)。対角は True。"""
    r = reach(vrfs)
    return {(s, d): (s == d or any(src == s for _p, src in r[d]))
            for s in vrfs for d in vrfs}


def symmetric_pairs(vrfs):
    """双方向に到達する VRF の組 {frozenset({a, b})}(a≠b)。"""
    m = matrix(vrfs)
    return {frozenset({a, b}) for a in vrfs for b in vrfs
            if a < b and m[(a, b)] and m[(b, a)]}


def vpnv4_entries(vrfs, pe):
    """PE の VPNv4 表に並ぶ [(rd, prefix, src_vrf)](rd, prefix 順)。同一 (rd, prefix) の衝突は ValueError。"""
    _check(vrfs)
    local = {n for n, v in vrfs.items() if v["pe"] == pe}
    rds = [vrfs[n]["rd"] for n in sorted(local)]
    if len(rds) != len(set(rds)):
        raise ValueError(f"{pe}: 同一ルータ内で RD が重複(IOS は拒否する・PoC M8)")
    imps = set().union(*(set(vrfs[n]["imp"]) for n in local)) if local else set()
    rows = []
    for n, v in vrfs.items():
        if v["pe"] == pe or (set(v["exp"]) & imps):
            rows += [(v["rd"], p, n) for p in v["nets"]]
    seen = {}
    for rd, p, n in rows:
        if (rd, p) in seen and seen[(rd, p)] != n:
            raise ValueError(f"{pe}: RD {rd} と {p} が {seen[(rd, p)]} と {n} で衝突(盤面不成立)")
        seen[(rd, p)] = n
    return sorted(rows)


# --------------------------------------------------------------------------
# 世界(要件)の判定に使う小道具
# --------------------------------------------------------------------------
def complies(vrfs, want):
    """want= {(src, dst): bool} の部分指定が全て一致するか(未指定の組は問わない)。"""
    m = matrix(vrfs)
    return all(m[k] == v for k, v in want.items())


def selftest():
    ng = 0

    def ok(cond, msg):
        nonlocal ng
        if not cond:
            ng += 1
            print("NG", msg)

    A = "65000:100"; B = "65000:200"; H = "65000:300"; S = "65000:301"; X = "65000:900"
    # 1) フルメッシュ: 同一 RT を import/export → 3 拠点が相互到達
    fm = {f"A{i}": {"pe": f"PE{i}", "rd": f"65000:10{i}", "imp": {A}, "exp": {A},
                    "nets": [f"172.16.{i}.0/24"]} for i in (1, 2, 3)}
    ok(len(symmetric_pairs(fm)) == 3, "fullmesh: 3 組が相互到達")
    # 2) ハブ&スポーク: hub exp=H imp=S / spoke exp=S imp=H → spoke 同士は不可
    hs = {"HUB": {"pe": "PE1", "rd": "65000:1", "imp": {S}, "exp": {H}, "nets": ["10.0.0.0/24"]},
          "SP2": {"pe": "PE2", "rd": "65000:2", "imp": {H}, "exp": {S}, "nets": ["10.0.2.0/24"]},
          "SP3": {"pe": "PE3", "rd": "65000:3", "imp": {H}, "exp": {S}, "nets": ["10.0.3.0/24"]}}
    m = matrix(hs)
    ok(m[("SP2", "HUB")] and m[("HUB", "SP2")], "hubspoke: spoke↔hub")
    ok(not m[("SP2", "SP3")] and not m[("SP3", "SP2")], "hubspoke: spoke↔spoke 不可")
    # 3) Extranet: 顧客 A/B は分離、共有サービス VRF とだけ相互到達
    ex = {"CA": {"pe": "PE1", "rd": "65000:100", "imp": {A, X}, "exp": {A}, "nets": ["172.16.1.0/24"]},
          "CB": {"pe": "PE1", "rd": "65000:200", "imp": {B, X}, "exp": {B}, "nets": ["172.16.1.0/24"]},
          "SVC": {"pe": "PE2", "rd": "65000:900", "imp": {A, B}, "exp": {X}, "nets": ["10.9.9.0/24"]}}
    m = matrix(ex)
    ok(m[("CA", "SVC")] and m[("SVC", "CA")] and m[("CB", "SVC")] and m[("SVC", "CB")], "extranet: 各顧客↔SVC")
    ok(not m[("CA", "CB")] and not m[("CB", "CA")], "extranet: 顧客同士は不可")
    # 4) 分離: 同一プレフィックスでも RT が違えば混ざらない。RD が同じでも reach は変わらない
    iso = {"CA": {"pe": "PE1", "rd": "65000:100", "imp": {A}, "exp": {A}, "nets": ["172.16.1.0/24"]},
           "CB": {"pe": "PE1", "rd": "65000:100", "imp": {B}, "exp": {B}, "nets": ["172.16.1.0/24"]}}
    ok(not matrix(iso)[("CA", "CB")], "isolate: RT が違えば載らない")
    try:
        vpnv4_entries(iso, "PE1")
        ok(False, "isolate: 同一 PE で (rd, prefix) 衝突は ValueError のはず")
    except ValueError:
        pass
    iso["CB"]["rd"] = "65000:200"
    ok(len(vpnv4_entries(iso, "PE1")) == 2, "isolate: RD を分ければ 2 本並ぶ")
    # 5) import の取り違え(v_cause の種): PE2 の import が誤り → 片方向だけ落ちる
    bad = {"A1": {"pe": "PE1", "rd": "65000:101", "imp": {A}, "exp": {A}, "nets": ["172.16.1.0/24"]},
           "A2": {"pe": "PE2", "rd": "65000:102", "imp": {X}, "exp": {A}, "nets": ["172.16.2.0/24"]}}
    m = matrix(bad)
    ok(m[("A2", "A1")] and not m[("A1", "A2")], "import 取り違え: PE1 側には載るが PE2 側に載らない")
    # 6) 自動 RT フィルタ: 他 PE の経路は import と交わるものだけ VPNv4 表に並ぶ
    rows = vpnv4_entries(bad, "PE2")
    ok([r[2] for r in rows] == ["A2"], "PE2 の VPNv4 表に A1 の経路は並ばない(import 不一致)")
    ok(complies(hs, {("SP2", "SP3"): False, ("SP2", "HUB"): True}), "complies: 部分指定")
    print(f"[rt_model selftest] {'OK' if ng == 0 else 'NG=' + str(ng)}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
