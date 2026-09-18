#!/usr/bin/env python3
"""BGP アウトバウンド ポリシー小ファミリ (BL-182) — gen_paper_mcq.py の shape=bgppol 素材。

設計= 非公開側の計画メモ(2026-09-18) §3 B2。ラボ側= gen_bgp_ring_ts の prefix_steer / no_transit と対。
kinds:
  rm_implicit_deny (思考) 1 経路だけ AS-PATH prepend したら他の経路も迂回した(out route-map の暗黙 deny で
                   他プレフィックスが広告されなくなった)。fix= `route-map X permit 20` を足す / cause / read(show ip bgp の `>` の寄り)。
  nontransit_dl    (思考) 非トランジット AS: 隣接ごとの distribute-list out の ACL 対(deny X + permit any)を fill(select)。
                   適用先(隣接)と ACL 番号の対応・方向・permit/deny の向きが誤答肢。
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KINDS = ["rm_implicit_deny", "nontransit_dl"]
SPEED_KINDS = []
THINK_KINDS = KINDS
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {"rm_implicit_deny": {"fix", "cause", "read"}, "nontransit_dl": {"select", "cause"}}
DIFF = {"rm_implicit_deny": 4, "nontransit_dl": 4}


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    if kind == "rm_implicit_deny":
        _draw_rm(d, rnd)
    else:
        _draw_nt(d, rnd)
    return d


# ==========================================================================
# rm_implicit_deny: 5 AS リング(教材と同形)。RA(顧客 AS)が 4 プレフィックスを持ち、RE から見て
#   経路が RD 経由と RC 経由の 2 本。RD の out route-map で 1 本だけ prepend したら、他が全部消えた。
# ==========================================================================
def _draw_rm(d, rnd):
    names = rnd.choice([("RA", "RB", "RC", "RD", "RE"), ("R1", "R2", "R3", "R4", "R5"), ("CE1", "P1", "P2", "P3", "PE5")])
    d["ra"], d["rb"], d["rc"], d["rd"], d["re"] = names
    base = rnd.choice([65001, 65100, 64512, 65010])
    d["as"] = {names[i]: base + i for i in range(5)}
    net = rnd.choice(["10.1", "10.20", "172.16", "192.168"])
    d["pfx"] = [f"{net}.{i}.0/24" if net != "192.168" else f"192.168.{i}.0/24" for i in (1, 2, 3, 4)]
    d["steer"] = rnd.randint(0, 3)          # RC 経由にしたいプレフィックス
    d["nh_d"] = rnd.choice(["198.51.100.5", "203.0.113.5", "10.255.45.5"])
    d["nh_c"] = rnd.choice(["192.0.2.9", "198.18.0.9", "10.255.35.9"])
    d["nbr_e"] = d["nh_d"].rsplit(".", 1)[0] + ".6"
    d["acl"] = rnd.choice([1, 10, 20])
    d["rm"] = rnd.choice(["MAP1", "TO-RE", "PREPEND-OUT"])
    d["fixed"] = False


def _bgp_table(d, fixed=False):
    """RE の show ip bgp。fixed=False(現状)は全プレフィックスが RC 経由のみ(RD からは暗黙 deny で届かない)。
    fixed=True は是正後(steer だけ RD 経由が prepend 付きで劣後し、他は RD 経由が best)。"""
    ra, rb, rc, rd, re_ = d["ra"], d["rb"], d["rc"], d["rd"], d["re"]
    A = d["as"]
    L = [f"{re_}# show ip bgp", "BGP table version is 12, local router ID is 198.51.100.6",
         "Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,",
         "              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,",
         "              x best-external, a additional-path, c RIB-compressed,",
         "Origin codes: i - IGP, e - EGP, ? - incomplete", "",
         "     Network          Next Hop            Metric LocPrf Weight Path"]
    for i, p in enumerate(d["pfx"]):
        via_c = f"{A[rc]} {A[rb]} {A[ra]} i"
        via_d = f"{A[rd]} {A[ra]} i" if i != d["steer"] else f"{A[rd]} {A[rd]} {A[rd]} {A[ra]} i"
        row_c = f" *   {p:<16} {d['nh_c']:<19}                    0 {via_c}"
        row_d = f" *   {p:<16} {d['nh_d']:<19}      0             0 {via_d}"
        if not fixed:
            L.append(row_c.replace(" *   ", " *>  ", 1))
        elif i == d["steer"]:
            L.append(row_c.replace(" *   ", " *>  ", 1))
            L.append(row_d)
        else:
            L.append(row_d.replace(" *   ", " *>  ", 1))
            L.append(row_c)
    return "\n".join(L)


def _rd_config(d):
    rd, re_ = d["rd"], d["re"]
    A = d["as"]
    net = d["pfx"][d["steer"]].split("/")[0]
    L = [f"{rd}# show running-config | section access-list|route-map|router bgp",
         f"access-list {d['acl']} permit {net} 0.0.0.255",
         f"route-map {d['rm']} permit 10",
         f" match ip address {d['acl']}",
         f" set as-path prepend {A[rd]} {A[rd]}",
         f"router bgp {A[rd]}",
         f" neighbor {d['nbr_e']} remote-as {A[re_]}",
         f" neighbor {d['nbr_e']} route-map {d['rm']} out"]
    return "\n".join(L)


def _rm_exhibit(d):
    return _rd_config(d) + "\n\n" + _bgp_table(d, fixed=False)


def build_choices_fix(d, rnd):
    rd, rm, acl = d["rd"], d["rm"], d["acl"]
    others = [p for i, p in enumerate(d["pfx"]) if i != d["steer"]]
    c = [(f"route-map {rm} permit 20", True, ""),
         (f"route-map {rm} deny 20", False, "deny の空エントリは暗黙の deny と同じで、他のプレフィックスは引き続き広告されない。"),
         (f"access-list {acl + 1} permit {others[0].split('/')[0]} 0.0.0.255\nroute-map {rm} permit 20\n match ip address {acl + 1}", False,
          f"{others[0]} だけが許可され、残りの {len(others) - 1} 経路は依然として広告されない。"),
         (f"no access-list {acl} permit {d['pfx'][d['steer']].split('/')[0]} 0.0.0.255", False,
          "match の ACL を消すと未定義 ACL 参照になり、permit 10 が全経路に一致して全部が prepend される。他経路を通す手ではあるが要件(1 経路だけ prepend)を崩す。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_cause(d, rnd):
    if d["kind"] == "nontransit_dl":
        return _nt_cause(d, rnd)
    rd, re_, rm = d["rd"], d["re"], d["rm"]
    c = [(f"{rd} の {re_} 向け out のルート マップに、prepend の対象以外を許可するエントリが無く、暗黙の deny で他のプレフィックスが広告されていない。", True, ""),
         (f"{rd} のルート マップで set as-path prepend が全てのプレフィックスに適用されている。", False, "match の ACL は 1 プレフィックスだけに一致しており、prepend は 1 経路にしか付いていない(他は届いていない)。"),
         (f"{re_} が {rd} からの経路を RIB-failure で拒否している。", False, "show ip bgp に {rd} 経由の経路そのものが無く、RIB-failure(r)の表示も無い。"),
         (f"{rd} と {re_} の BGP セッションがダウンしている。", False, "セッションが無ければ prepend 対象の経路も含めて何も届かないが、問題は広告の範囲である。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_read(d, rnd):
    rd, rc, re_ = d["rd"], d["rc"], d["re"]
    steer = d["pfx"][d["steer"]]
    others = [p for i, p in enumerate(d["pfx"]) if i != d["steer"]]
    P = [
        (f"{re_} は、{steer} 以外のプレフィックスについて {rd} 経由の経路を受信していない。", True, ""),
        (f"{re_} は、全てのプレフィックスを {rc} 経由で転送する。", True, ""),
        (f"{re_} は、{others[0]} を {rd} 経由で転送する。", False, f"{others[0]} は {rc} 経由(AS パスが長い方)しか無く、{rd} 経由の経路は届いていない。"),
        (f"{re_} は、{steer} について {rd} 経由と {rc} 経由の 2 つの経路を持ち、AS パスの短い {rc} 経由を選んでいる。", False,
         f"{steer} も {rc} 経由しか表示されておらず、{rd} 経由の経路(prepend 付き)は届いていない。"),
        (f"{rd} は {re_} に対して、prepend の対象のプレフィックスだけを広告している。", False,
         "対象のプレフィックスも含めて、ルート マップの暗黙 deny により {} からは何も広告されていない(表に {} 経由が無い)。".format(rd, rd)),
    ]
    trues = [(t, w) for t, ok, w in P if ok]
    falses = [(t, w) for t, ok, w in P if not ok]
    t, _ = rnd.choice(trues)
    c = [(t, True, "")]
    for f, w in rnd.sample(falses, 3):
        c.append((f, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# nontransit_dl: AS1 - AS2(RB) - AS3。RB の隣接ごとの distribute-list out。
# ==========================================================================
def _draw_nt(d, rnd):
    d["ra"], d["rb"], d["rc"] = rnd.choice([("RA", "RB", "RC"), ("R1", "R2", "R3"), ("ISP-A", "EDGE", "ISP-B")])
    d["as1"], d["as2"], d["as3"] = rnd.choice([(1, 2, 3), (65001, 65002, 65003), (100, 200, 300)])
    d["p1"] = rnd.choice(["10.1.1.0", "172.16.1.0", "10.100.0.0"])
    d["p3"] = rnd.choice(["192.168.1.0", "172.31.9.0", "192.168.50.0"])
    d["p2"] = rnd.choice(["172.16.1.0", "10.2.2.0", "172.20.5.0"])
    if d["p2"] in (d["p1"], d["p3"]):
        d["p2"] = "10.9.9.0"
    d["ip_a"], d["ip_c"] = rnd.choice([("198.51.100.1", "198.51.100.6"), ("203.0.113.1", "203.0.113.6"), ("10.255.0.1", "10.255.0.6")])
    d["acl_to_a"], d["acl_to_c"] = rnd.choice([(3, 1), (1, 3), (10, 30), (30, 10)])
    d["dir"] = "out"


def _nt_exhibit(d):
    ra, rb, rc = d["ra"], d["rb"], d["rc"]
    nh = d['ip_a'].rsplit('.', 1)[0] + ".2"
    L = [f"{ra}# show ip bgp | begin Network",
         "     Network          Next Hop            Metric LocPrf Weight Path",
         f" *>  {d['p1'] + '/24':<16} {'0.0.0.0':<19}      0         32768 i",
         f" *>  {d['p2'] + '/24':<16} {nh:<19}      0             0 {d['as2']} i",
         f" *>  {d['p3'] + '/24':<16} {nh:<19}                    0 {d['as2']} {d['as3']} i",
         "",
         f"【{rb} に追加する設定】",
         f"{rb}(config)# 【?】",
         f"{rb}(config)# router bgp {d['as2']}",
         f"{rb}(config-router)# neighbor {d['ip_a']} distribute-list {d['acl_to_a']} out",
         f"{rb}(config-router)# neighbor {d['ip_c']} distribute-list {d['acl_to_c']} out"]
    return "\n".join(L)


def _acl_pair(d, to_a_deny, to_c_deny, num_a, num_c, permit_first=False):
    """to_a_deny: RA へ送らないプレフィックス。"""
    if permit_first:
        return (f"access-list {num_a} permit {to_a_deny} 0.0.0.255\naccess-list {num_a} deny any\n"
                f"access-list {num_c} permit {to_c_deny} 0.0.0.255\naccess-list {num_c} deny any")
    return (f"access-list {num_a} deny {to_a_deny} 0.0.0.255\naccess-list {num_a} permit any\n"
            f"access-list {num_c} deny {to_c_deny} 0.0.0.255\naccess-list {num_c} permit any")


def build_choices_select(d, rnd):
    ra, rc = d["ra"], d["rc"]
    a, c = d["acl_to_a"], d["acl_to_c"]
    p1, p3 = d["p1"], d["p3"]
    correct = _acl_pair(d, p3, p1, a, c)
    wrong_swap = _acl_pair(d, p1, p3, a, c)
    wrong_permit = _acl_pair(d, p3, p1, a, c, permit_first=True)
    wrong_num = _acl_pair(d, p3, p1, a * 10 + 1 if a < 10 else a + 5, c * 10 + 1 if c < 10 else c + 5)
    choices = [
        (correct, True, ""),
        (wrong_swap, False, f"ACL {a} は {ra}({ra} の AS)向けの out に適用されるので、止めるべきは {rc} 側の {p3} である。ACL {c} はその逆。対応が入れ替わっている。"),
        (wrong_permit, False, "ディストリビュート リストでは deny した経路がフィルタされる。止めたい経路を permit し他を deny すると、逆に止めたい経路だけが通る。"),
        (wrong_num, False, f"router bgp で参照している ACL 番号は {a} と {c} であり、番号が一致していない。"),
    ]
    order = list(range(len(choices)))
    rnd.shuffle(order)
    return [choices[i] for i in order]


def _nt_cause(d, rnd):
    ra, rb, rc = d["ra"], d["rb"], d["rc"]
    c = [(f"{rb} が {ra} から受け取った経路を {rc} に、{rc} から受け取った経路を {ra} に、そのまま広告している。", True, ""),
         (f"{ra} と {rc} が直接 BGP セッションを張っている。", False, f"{ra} の表では {d['p3']} の next-hop が {rb} 側であり、{rc} と直接のセッションは無い。"),
         (f"{rb} で synchronization が有効になっている。", False, "同期はいずれの経路も広告される事象とは関係ない。"),
         (f"{ra} の経路が {rb} で集約されている。", False, "個別のプレフィックスがそのまま届いている。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_select2(d, rnd):
    raise ValueError("bgppol に select2 は無い")


def build_choices_allthat(d, rnd):
    raise ValueError("bgppol に allthat は無い")


def build_match(d, rnd):
    raise ValueError("bgppol に match は無い")


CORE = {
    "rm_implicit_deny": "out 方向のルート マップは、どのエントリにも一致しない経路を暗黙の deny で落とす。1 経路だけ操作したいなら、残りを通す空の permit エントリ(route-map X permit 20)が要る。deny 20 は暗黙 deny と同じ。match の ACL を消す手は permit 10 が全一致になり全経路に prepend が付く。",
    "nontransit_dl": "非トランジット AS= 他 AS から学習した経路を別の他 AS へ広告しない。distribute-list out は deny した経路を止める(permit any を最後に)。隣接ごとに「その隣接へ送らない経路」を deny する: AS1 側の隣接には AS3 の経路を、AS3 側の隣接には AS1 の経路を deny。ACL 番号は router bgp の参照と一致させる。別解= prefix-list / filter-list(^$)/ community no-export。",
}
TITLES = {"rm_implicit_deny": "BGP のアウトバウンド ポリシー(ルート マップ)", "nontransit_dl": "BGP の非トランジット AS の構成"}


def question_body(d, choices, form):
    if d["kind"] == "rm_implicit_deny":
        ra, rc, rd, re_ = d["ra"], d["rc"], d["rd"], d["re"]
        steer = d["pfx"][d["steer"]]
        others = "、".join(p for i, p in enumerate(d["pfx"]) if i != d["steer"])
        A = d["as"]
        intro = (f"各ルータで BGP を動作させています。{ra}(AS {A[ra]})は {'、'.join(d['pfx'])} を広告し、{re_}(AS {A[re_]})には "
                 f"{rd}(AS {A[rd]})経由と {rc}(AS {A[rc]})経由の 2 つの経路が届く構成です。"
                 f"{re_} から {steer} 宛のパケットを {rc} 経由で転送するように、{rd} で次の設定を行いました。")
        before = f"{intro}\n\n```\n{_rm_exhibit(d)}\n```"
        if form == "fix":
            before += f"\n\nしかし、{others} も {rc} 経由で転送されるようになってしまいました。"
            ask = f"{others} を {rd} 経由で転送させるために {rd} に追加する設定として最も適切なものは、次のうちどれですか。(1つを選択してください)"
            ch_md = "\n\n".join(f"**{'ABCDEFG'[i]}.**\n\n```\n{t}\n```" for i, (t, _, _) in enumerate(choices))
        elif form == "cause":
            before += f"\n\nしかし、{others} も {rc} 経由で転送されるようになってしまいました。"
            ask = "この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
            ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        else:
            ask = f"{re_} の出力から分かることとして、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
            ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    ra, rb, rc = d["ra"], d["rb"], d["rc"]
    intro = (f"{ra}(AS {d['as1']})- {rb}(AS {d['as2']})- {rc}(AS {d['as3']})の順に eBGP で接続されています。{ra} は {d['p1']}/24、{rb} は {d['p2']}/24、"
             f"{rc} は {d['p3']}/24 を広告しています。AS {d['as2']} を非トランジット AS にしようとしましたが、AS {d['as1']} と AS {d['as3']} がそれぞれの経路を交換しています。")
    before = f"{intro}\n\n```\n{_nt_exhibit(d)}\n```"
    if form == "select":
        ask = (f"AS {d['as1']} に AS {d['as3']} の経路、AS {d['as3']} に AS {d['as1']} の経路が届かないようにするために {rb} で必要な【?】に当てはまる設定はどれですか。"
               f"なお、{ra} と {rc} は AS {d['as2']} の経路を動的に学習する必要があり、{rb} は AS {d['as1']} と AS {d['as3']} の経路を動的に学習する必要があります。(1つを選択してください)")
        ch_md = "\n\n".join(f"**{'ABCDEFG'[i]}.**\n\n```\n{t}\n```" for i, (t, _, _) in enumerate(choices))
    else:
        ask = f"AS {d['as1']} と AS {d['as3']} が互いの経路を学習している原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    return before, ask, ch_md, ""


def answer_body(d, choices, form):
    keys = [k for k, (t, ok, w) in zip("ABCDEFG", choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip("ABCDEFG", choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[d["kind"]]]
    return "\n".join(lines)


def pick_count(form, choices):
    return 1


def selftest(seeds=40):
    import random as _r
    import re as _re
    ng = n = 0
    bad = {}
    builders = {"select": build_choices_select, "read": build_choices_read, "cause": build_choices_cause, "fix": build_choices_fix}
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = draw(rnd, kind, None, form)
                    choices = builders[form](d, rnd)
                    n_true = sum(1 for x in choices if x[1])
                    assert n_true == 1, f"{form} 正解数 {n_true}"
                    texts = [x[0] for x in choices]
                    assert len(set(texts)) == len(texts), "選択肢の重複"
                    assert not any(_re.search(r"(ため|ので)[、。]", t) for t in texts), "肢に因果"
                    before, ask, ch_md, _ = question_body(d, choices, form)
                    assert "```" in before
                    assert "## 正解" in answer_body(d, choices, form)
                except (AssertionError, ValueError, KeyError) as exc:
                    ng += 1
                    bad.setdefault((kind, form), [0, repr(exc)])[0] += 1
    for (k, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{f}: {cnt} 件 (例: {ex})")
    print(f"[gen_paper_bgppol selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
