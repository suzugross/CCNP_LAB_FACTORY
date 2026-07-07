#!/usr/bin/env python3
"""netmodel（大域不変条件グレーダ）のオフライン自己テスト。

CML を起動せずにエンジンの正しさを検証する。各シナリオは合成 RIB（正規化済み
routes か、Genie に通す生テキスト）を与え、不変条件の合否を assert する。

実行: .venv/bin/python3 topologies/test_netmodel.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netmodel as nm  # noqa: E402


# 4 ノードのチェーン RT01-RT02-RT03-RT04（各リンク /30）。
# Loopback は n.n.n.n/32。
MODEL = {
    "loopbacks": {"RT01": "1.1.1.1", "RT02": "2.2.2.2",
                  "RT03": "3.3.3.3", "RT04": "4.4.4.4"},
    "links": [
        {"a": "RT01", "a_ip": "10.0.12.1", "b": "RT02", "b_ip": "10.0.12.2"},
        {"a": "RT02", "a_ip": "10.0.23.2", "b": "RT03", "b_ip": "10.0.23.3"},
        {"a": "RT03", "a_ip": "10.0.34.3", "b": "RT04", "b_ip": "10.0.34.4"},
    ],
}
LO = MODEL["loopbacks"]
# 各ノードの隣接 next-hop（IP）: 左隣 / 右隣
NH = {  # (node, 行き先方向) -> next-hop IP
    ("RT01", "right"): "10.0.12.2",
    ("RT02", "left"): "10.0.12.1", ("RT02", "right"): "10.0.23.3",
    ("RT03", "left"): "10.0.23.2", ("RT03", "right"): "10.0.34.4",
    ("RT04", "left"): "10.0.34.3",
}


def r(prefix, src, nexthops=()):
    return {"prefix": prefix, "src": src, "nexthops": list(nexthops)}


def connected_rib(node):
    """その node が自分で持つ connected/local（Loopback + 直結リンク）。"""
    out = [r(LO[node] + "/32", "connected")]
    for ln in MODEL["links"]:
        if ln["a"] == node:
            out += [r("10." + ln["a_ip"].split(".", 1)[1].rsplit(".", 1)[0] + ".0/30", "connected")]
        if ln["b"] == node:
            out += [r("10." + ln["b_ip"].split(".", 1)[1].rsplit(".", 1)[0] + ".0/30", "connected")]
    return out


def good_chain():
    """正しい収束: 各ノードが遠い Loopback を「隣の正しい向き」へ向ける。"""
    return {
        "RT01": connected_rib("RT01") + [
            r("2.2.2.2/32", "ospf", [NH[("RT01", "right")]]),
            r("3.3.3.3/32", "ospf", [NH[("RT01", "right")]]),
            r("4.4.4.4/32", "ospf", [NH[("RT01", "right")]])],
        "RT02": connected_rib("RT02") + [
            r("1.1.1.1/32", "ospf", [NH[("RT02", "left")]]),
            r("3.3.3.3/32", "ospf", [NH[("RT02", "right")]]),
            r("4.4.4.4/32", "ospf", [NH[("RT02", "right")]])],
        "RT03": connected_rib("RT03") + [
            r("1.1.1.1/32", "ospf", [NH[("RT03", "left")]]),
            r("2.2.2.2/32", "ospf", [NH[("RT03", "left")]]),
            r("4.4.4.4/32", "ospf", [NH[("RT03", "right")]])],
        "RT04": connected_rib("RT04") + [
            r("1.1.1.1/32", "ospf", [NH[("RT04", "left")]]),
            r("2.2.2.2/32", "ospf", [NH[("RT04", "left")]]),
            r("3.3.3.3/32", "ospf", [NH[("RT04", "left")]])],
    }


PASSED = []


def expect(cond, msg):
    mark = "ok  " if cond else "FAIL"
    PASSED.append(cond)
    print(f"  [{mark}] {msg}")


def run(model, ribs, invs):
    return {x["name"]: x for x in nm.evaluate_invariants(model, ribs, invs)}


INVS = [
    {"type": "reachability_all", "name": "全到達性", "points": 40},
    {"type": "loop_free", "name": "ループ不在", "points": 30},
    {"type": "optimal", "name": "最短経路", "points": 30},
]


def test_good():
    print("シナリオ1: 正常収束 → 3不変条件すべて PASS")
    res = run(MODEL, good_chain(), INVS)
    expect(res["全到達性"]["ok"], "全到達性 PASS")
    expect(res["ループ不在"]["ok"], "ループ不在 PASS")
    expect(res["最短経路"]["ok"], "最短経路 PASS")


def test_unreachable():
    print("シナリオ2: RT04 が 1.1.1.1 を持たない → 到達性 FAIL")
    ribs = good_chain()
    ribs["RT04"] = [x for x in ribs["RT04"] if x["prefix"] != "1.1.1.1/32"]
    res = run(MODEL, ribs, INVS)
    expect(not res["全到達性"]["ok"], "全到達性 FAIL を検出")
    expect(any("RT04->RT01" in f for f in res["全到達性"]["detail"]["failures"]),
           "失敗ペア RT04->RT01 を提示")


def test_loop():
    print("シナリオ3: RT02⇄RT03 が 4.4.4.4 を互いに向ける → ループ検出")
    ribs = good_chain()
    # RT02 は 4.4.4.4 を「右(RT03)」に出すのが正しいが、誤って RT03 が「左(RT02)」へ返す
    for x in ribs["RT03"]:
        if x["prefix"] == "4.4.4.4/32":
            x["nexthops"] = [NH[("RT03", "left")]]   # RT03 -> RT02（誤り）
    res = run(MODEL, ribs, INVS)
    expect(not res["ループ不在"]["ok"], "ループ不在 FAIL を検出")
    expect(any("RT02" in f and "RT03" in f for f in res["ループ不在"]["detail"]["failures"]),
           "RT02-RT03 ループ経路を提示")


def test_suboptimal_clear():
    print("シナリオ4: 最短1ホップ(直結)を2ホップで迂回 → 最適性 FAIL")
    # 三角形 RT01-RT02-RT03 + RT01-RT03 直結（近道）。RT01->RT03 最短=1。
    chain = {
        "loopbacks": {"RT01": "1.1.1.1", "RT02": "2.2.2.2",
                      "RT03": "3.3.3.3", "RT04": "4.4.4.4"},
        "links": [
            {"a": "RT01", "a_ip": "10.0.12.1", "b": "RT02", "b_ip": "10.0.12.2"},
            {"a": "RT02", "a_ip": "10.0.23.2", "b": "RT03", "b_ip": "10.0.23.3"},
            {"a": "RT03", "a_ip": "10.0.34.3", "b": "RT04", "b_ip": "10.0.34.4"},
            {"a": "RT01", "a_ip": "10.0.13.1", "b": "RT03", "b_ip": "10.0.13.3"},  # 近道
        ],
    }
    # RT01->RT03 最短=1(直結)。遠回り: RT01->RT02->RT03=2。
    ribs = {
        "RT01": [r("1.1.1.1/32", "connected"), r("10.0.12.0/30", "connected"),
                 r("10.0.13.0/30", "connected"),
                 r("3.3.3.3/32", "ospf", ["10.0.12.2"])],   # RT01 -> RT02（遠回り）
        "RT02": [r("2.2.2.2/32", "connected"), r("10.0.12.0/30", "connected"),
                 r("10.0.23.0/30", "connected"),
                 r("3.3.3.3/32", "ospf", ["10.0.23.3"])],   # RT02 -> RT03
        "RT03": [r("3.3.3.3/32", "connected")],
        "RT04": [r("4.4.4.4/32", "connected")],
    }
    res = run(chain, ribs, [{"type": "optimal", "name": "最短経路",
                             "points": 30, "pairs": [["RT01", "RT03"]]}])
    expect(not res["最短経路"]["ok"], "遠回り(2ホップ vs 最短1) を FAIL 検出")
    expect(any("RT01->RT03" in f for f in res["最短経路"]["detail"]["failures"]),
           "RT01->RT03 の遠回りを提示")


def test_disjoint():
    print("シナリオ5: ダイヤモンドの ECMP → 独立経路2本(冗長度)")
    dia = {
        "loopbacks": {"RT01": "1.1.1.1", "RT02": "2.2.2.2",
                      "RT03": "3.3.3.3", "RT04": "4.4.4.4"},
        "links": [
            {"a": "RT01", "a_ip": "10.0.12.1", "b": "RT02", "b_ip": "10.0.12.2"},
            {"a": "RT01", "a_ip": "10.0.13.1", "b": "RT03", "b_ip": "10.0.13.3"},
            {"a": "RT02", "a_ip": "10.0.24.2", "b": "RT04", "b_ip": "10.0.24.4"},
            {"a": "RT03", "a_ip": "10.0.34.3", "b": "RT04", "b_ip": "10.0.34.4"},
        ],
    }
    ribs = {
        "RT01": [r("1.1.1.1/32", "connected"), r("10.0.12.0/30", "connected"),
                 r("10.0.13.0/30", "connected"),
                 r("4.4.4.4/32", "ospf", ["10.0.12.2", "10.0.13.3"])],  # ECMP
        "RT02": [r("2.2.2.2/32", "connected"), r("10.0.24.0/30", "connected"),
                 r("4.4.4.4/32", "ospf", ["10.0.24.4"])],
        "RT03": [r("3.3.3.3/32", "connected"), r("10.0.34.0/30", "connected"),
                 r("4.4.4.4/32", "ospf", ["10.0.34.4"])],
        "RT04": [r("4.4.4.4/32", "connected")],
    }
    res = run(dia, ribs, [{"type": "disjoint_paths", "name": "冗長度2",
                           "points": 20, "pairs": [["RT01", "RT04"]], "k": 2}])
    expect(res["冗長度2"]["ok"], "RT01->RT04 に独立経路2本を確認")
    # 片方の ECMP を落とすと冗長度1 → FAIL
    ribs["RT01"][-1]["nexthops"] = ["10.0.12.2"]
    res2 = run(dia, ribs, [{"type": "disjoint_paths", "name": "冗長度2",
                            "points": 20, "pairs": [["RT01", "RT04"]], "k": 2}])
    expect(not res2["冗長度2"]["ok"], "単一経路化で冗長度2 を FAIL 検出")


def test_single_default():
    print("シナリオ6: single_default（stub の一般化）")
    m = {"loopbacks": {"RT03": "3.3.3.3"},
         "links": [{"a": "RT02", "a_ip": "10.0.23.2",
                    "b": "RT03", "b_ip": "10.0.23.3"}]}
    ok_rib = {"RT03": [r("3.3.3.3/32", "connected"),
                       r("0.0.0.0/0", "ospf", ["10.0.23.2"])]}
    res = run(m, ok_rib, [{"type": "single_default", "name": "デフォルト1本",
                           "points": 20, "nodes": ["RT03"], "via": "10.0.23.2"}])
    expect(res["デフォルト1本"]["ok"], "デフォルト1本(via一致) PASS")
    bad_rib = {"RT03": [r("3.3.3.3/32", "connected"),
                        r("1.1.1.1/32", "ospf", ["10.0.23.2"]),  # 余計な inter-area
                        r("0.0.0.0/0", "ospf", ["10.0.23.2"])]}
    # single_default はデフォルト本数のみ見るので、ここでは2本デフォルトで FAIL を示す
    bad_rib2 = {"RT03": [r("0.0.0.0/0", "ospf", ["10.0.23.2"]),
                         r("0.0.0.0/0", "static", ["10.9.9.9"])]}
    res2 = run(m, bad_rib2, [{"type": "single_default", "name": "デフォルト1本",
                              "points": 20, "nodes": ["RT03"]}])
    expect(not res2["デフォルト1本"]["ok"], "デフォルト2本で FAIL 検出")
    _ = bad_rib


def test_genie_roundtrip():
    print("シナリオ7: 実機 show ip route テキスト → Genie パース経路で到達判定")
    import json
    p = "topologies/_generated/ENCOR-GRE-02/grade_input.json"
    if not os.path.exists(p):
        print("  [skip] サンプル grade_input.json 無し")
        return
    d = json.load(open(p))
    items = d if isinstance(d, list) else d.get("checks", [])
    txt = next((c["stdout"] for c in items
                if c.get("command") == "show ip route" and c.get("node") == "RT01"), None)
    if not txt:
        print("  [skip] RT01 の show ip route 無し")
        return
    routes = nm.parse_rib_text(txt, "iosxe")
    have = {x["prefix"] for x in routes}
    expect("1.1.1.1/32" in have and "2.2.2.2/32" in have,
           f"Genie パースで {len(routes)} 経路を正規化（1.1.1.1/32, 2.2.2.2/32 含む）")
    ro = nm._lpm(routes, "2.2.2.2")
    expect(ro and ro["src"] == "ospf" and ro["nexthops"] == ["10.0.12.2"],
           "2.2.2.2 への LPM が ospf via 10.0.12.2")


def main():
    for t in (test_good, test_unreachable, test_loop,
              test_suboptimal_clear, test_disjoint, test_single_default,
              test_genie_roundtrip):
        t()
    print("=" * 60)
    n_ok, n = sum(1 for x in PASSED if x), len(PASSED)
    print(f"  {n_ok}/{n} アサート PASS")
    print("=" * 60)
    sys.exit(0 if n_ok == n else 1)


if __name__ == "__main__":
    main()
