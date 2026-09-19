#!/usr/bin/env python3
"""経路選択の基礎 紙面ファミリ (BL-184 = 計画 B5・pref の kind 追加の代わりに svc 型ファミリとして実装)。

kinds:
  adfix   (思考) 誤った static(AD 1)が正しい IGP 経路を隠している → 正しい経路を採用させる設定を選ぶ(fix)。
          ★世界= 対抗プロトコル {OSPF 110 / EIGRP 90 / RIP 120 / EIGRP 外部 170 / eBGP 20 / iBGP 200} で
          floating static の閾値(正解の AD 値)が動く。同値(tie)は出題に使わない(閾値未満の肢は誤答)。
  adpath  (思考) 同じ宛先を static / OSPF / RIP で学習し、AD で勝つ低速経路を通る盤面。通る経路(select)と
          「何を消せば速くなるか」(select2)。
  ribread (思考) show ip eigrp topology all-links から「経路表に載る行」をすべて選ぶ(allthat)。
          等コスト successor 2 本・FS は載らない・[90/<FD>] の値を RD にすり替えた偽行(教材の罠)。
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KINDS = ["adfix", "adpath", "ribread"]
SPEED_KINDS = ["adpath"]                   # ★BL-186: AD 値の知識で即答(select/select2)
THINK_KINDS = ["adfix", "ribread"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {"adfix": {"fix", "cause"}, "adpath": {"select", "select2"}, "ribread": {"allthat"}}
DIFF = {"adfix": 3, "adpath": 3, "ribread": 4}
PROTOS = {"ospf": ("OSPF", 110, "O"), "eigrp": ("EIGRP", 90, "D"), "rip": ("RIP", 120, "R"),
          "eigrp_ext": ("EIGRP の外部経路(D EX)", 170, "D EX"), "ebgp": ("eBGP", 20, "B"), "ibgp": ("iBGP", 200, "B")}


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
    if kind == "adfix":
        d["proto"] = rnd.choice(list(PROTOS))
        d["r1"], d["r2"], d["r3"] = rnd.choice([("R1", "R2", "R3"), ("RT01", "RT02", "RT03"), ("EDGE", "CORE", "DIST")])
        d["dst"] = rnd.choice(["192.168.20.0", "10.20.0.0", "172.16.20.0"])
        d["good_nh"], d["bad_nh"] = rnd.choice([("10.10.100.2", "192.168.10.1"), ("10.0.12.2", "10.0.99.1"), ("172.31.1.2", "172.31.9.9")])
    elif kind == "adpath":
        d["ra"], d["rb"], d["rc"], d["rd"] = rnd.choice([("RA", "RB", "RC", "RD"), ("R1", "R2", "R3", "R4")])
        d["dst"] = rnd.choice(["192.168.200.0", "10.200.0.0", "172.16.200.0"])
        d["src"] = rnd.choice(["192.168.1.0", "10.1.0.0"])
        # 経路: 上(RB 経由・1G・OSPF)、直(RC 直結・100M・RIP)、下(RD 経由・10M・static)
        d["static_via"] = rnd.choice(["rd", "rd", "rc"])
    else:
        _draw_rib(d, rnd)
    return d


# ==========================================================================
# adfix
# ==========================================================================
def _adfix_exhibit(d):
    name, ad, code = PROTOS[d["proto"]]
    r1 = d["r1"]
    L = [f"{r1}# show ip route {d['dst']}", f"Routing entry for {d['dst']}/24", '  Known via "static", distance 1, metric 0',
         "  Routing Descriptor Blocks:", f"  * {d['bad_nh']}", "      Route metric is 0, traffic share count is 1", "",
         f"{r1}# show running-config | include ip route", f"ip route {d['dst']} 255.255.255.0 {d['bad_nh']}", ""]
    if d["proto"] in ("ospf",):
        L += [f"{r1}# show ip ospf database router {d['r3']} | include Link ID|Network/subnet", f"     (Link ID) Network/subnet number: {d['dst']}"]
    elif d["proto"] in ("eigrp", "eigrp_ext"):
        L += [f"{r1}# show ip eigrp topology {d['dst']}/24 | include via|successors", f"  {d['dst']}/24, 1 successors", f"        via {d['good_nh']} (409600/128256), Ethernet0/1"]
    elif d["proto"] == "rip":
        L += [f"{r1}# show ip rip database | include {d['dst']}", f"    [1] via {d['good_nh']}, 00:00:12, Ethernet0/1"]
    else:
        L += [f"{r1}# show ip bgp {d['dst']} | include from", f"  {d['good_nh']} from {d['good_nh']} ({d['r2']})"]
    return "\n".join(L)


def build_choices_fix(d, rnd):
    name, ad, code = PROTOS[d["proto"]]
    dst, bad = d["dst"], d["bad_nh"]
    good_val = rnd.choice([v for v in (ad + 5, ad + 10, ad + 40, 200, 250, 254) if v > ad][:3])
    low_vals = [v for v in (ad - 10, ad - 1, 5, 10, 100, 110, 120, 90, 170, 20) if 1 < v < ad]
    low = rnd.sample(sorted(set(low_vals)), 2) if len(set(low_vals)) >= 2 else [ad - 1, 5]
    c = [(f"ip route {dst} 255.255.255.0 {bad} {good_val}", True, ""),
         (f"ip route {dst} 255.255.255.0 {bad} {low[0]}", False, f"AD {low[0]} は {name}(AD {ad})より小さく、依然として static が優先される。"),
         (f"ip route {dst} 255.255.255.0 {bad} {low[1]}", False, f"AD {low[1]} は {name}(AD {ad})より小さく、依然として static が優先される。"),
         (f"no ip route {dst} 255.255.255.0 {bad}\nip route {dst} 255.255.255.0 {bad.rsplit('.', 1)[0]}.{int(bad.rsplit('.', 1)[1]) + 9}", False,
          "誤った next-hop を別の誤った next-hop に置き換えており、正しい経路は採用されない。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    d["_ans"] = good_val
    return [c[i] for i in order]


def build_choices_cause(d, rnd):
    name, ad, code = PROTOS[d["proto"]]
    c = [(f"静的経路の AD(1)が {name} の AD({ad})より小さく、誤った next-hop の静的経路がルーティング テーブルに採用されている。", True, ""),
         (f"{name} の経路が {d['r1']} に届いていない。", False, f"{name} の情報(トポロジ/データベース)には {d['dst']} が存在しており、届いている。"),
         (f"静的経路の AD が {name} より大きく、{name} の経路が採用されている。", False, "show ip route は Known via static, distance 1 であり、静的経路が採用されている。"),
         (f"{d['dst']} 宛の経路が複数あり、等コストで負荷分散されている。", False, "Routing Descriptor Blocks は 1 つだけであり、負荷分散はしていない。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# adpath
# ==========================================================================
def _adpath_exhibit(d):
    ra, rb, rc, rd = d["ra"], d["rb"], d["rc"], d["rd"]
    via = rd if d["static_via"] == "rd" else rc
    nh = "192.168.31.4" if via == rd else "192.168.21.3"
    L = ["トポロジ(帯域):", f"  {ra} — {rb}: 1G   {rb} — {rc}: 1G", f"  {ra} — {rc}: 100M", f"  {ra} — {rd}: 10M   {rd} — {rc}: 10M",
         f"  {d['src']}/24 は {ra} の LAN、{d['dst']}/24 は {rc} の LAN", "",
         "各ルータの設定:", "  ・全ルータで RIP を有効にしている", "  ・全ルータで OSPF を有効にしている",
         f"  ・{ra} は上記に加え ip route {d['dst']} 255.255.255.0 {nh} を設定している"]
    return "\n".join(L)


def build_choices_select(d, rnd):
    ra, rb, rc, rd = d["ra"], d["rb"], d["rc"], d["rd"]
    via = rd if d["static_via"] == "rd" else rc
    if via == rd:
        c = [(f"{rd} を経由して {rc} にパケットが届く。", True, ""),
             (f"{rb} を経由して {rc} にパケットが届く。", False, "OSPF の AD(110)は静的経路(1)より大きく、OSPF の経路は採用されない。"),
             (f"{rc} に直接パケットが届く。", False, "RIP の AD(120)は静的経路(1)より大きく、RIP の経路は採用されない。"),
             (f"{rb} 経由と {rd} 経由で負荷分散される。", False, "AD の異なる経路は負荷分散されず、AD の小さい静的経路だけが採用される。")]
    else:
        c = [(f"{rc} に直接パケットが届く。", True, ""),
             (f"{rb} を経由して {rc} にパケットが届く。", False, "OSPF の AD(110)は静的経路(1)より大きく、OSPF の経路は採用されない。"),
             (f"{rd} を経由して {rc} にパケットが届く。", False, "静的経路の next-hop は直結の {} であり、{} 経由ではない。".format(rc, rd)),
             (f"{rb} 経由と {rc} 直結で負荷分散される。", False, "AD の異なる経路は負荷分散されず、静的経路だけが採用される。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_select2(d, rnd):
    ra, rb, rc, rd = d["ra"], d["rb"], d["rc"], d["rd"]
    via = rd if d["static_via"] == "rd" else rc
    c = [(f"静的経路の設定を削除する。", True, ""),
         (f"静的経路の AD を 110 より大きい値に変更する。", True, ""),
         (f"OSPF の AD を 11 にする。", False, "11 に変更しても静的経路(1)より大きく、OSPF の経路は採用されない。"),
         (f"RIP の設定を削除する。", False, "RIP の経路はもともと採用されておらず、削除しても変わらない。"),
         (f"{via} で ip route {d['dst']} 255.255.255.0 を削除する。", False, f"静的経路は {ra} に設定されており、{via} には無い。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# ribread: EIGRP topology all-links
# ==========================================================================
def _draw_rib(d, rnd):
    d["ra"] = rnd.choice(["RA", "R1", "RT01"])
    d["nets"] = rnd.choice([("192.168.101.0/24", "192.168.102.0/24"), ("10.10.1.0/24", "10.10.2.0/24"), ("172.16.101.0/24", "172.16.102.0/24")])
    nh = rnd.choice([("192.168.2.2", "192.168.1.2", "192.168.3.2"), ("10.0.2.2", "10.0.1.2", "10.0.3.2")])
    d["nh"] = nh
    d["ifs"] = ("Ethernet0/2", "Ethernet0/0", "Ethernet0/1")
    fd = rnd.choice([286720, 307200, 435200])
    # net1: successor(nh0 FD) + FS(nh1: RD < FD)
    # net2: 2 successors(nh0, nh2 equal FD) + non-FS(nh1: RD > FD)
    d["fd"] = fd
    d["rd_fs"] = fd - rnd.choice([2560, 5120])
    d["fd_fs_total"] = fd + rnd.choice([20480, 23040])
    d["rd_nonfs"] = fd + rnd.choice([2560, 5120])
    d["fd_nonfs_total"] = fd + rnd.choice([28160, 30720])
    d["rd_succ"] = fd - rnd.choice([2560, 5120])


def _rib_exhibit(d):
    n1, n2 = d["nets"]
    nh0, nh1, nh2 = d["nh"]
    i0, i1, i2 = d["ifs"]
    fd = d["fd"]
    key = n1.rsplit(".", 2)[0]
    L = [f"{d['ra']}# show ip eigrp topology all-links | section P {key}",
         f"P {n1}, 1 successors, FD is {fd}, serno 163",
         f"        via {nh0} ({fd}/{d['rd_succ']}), {i0}",
         f"        via {nh1} ({d['fd_fs_total']}/{d['rd_fs']}), {i1}",
         f"P {n2}, 2 successors, FD is {fd}, serno 167",
         f"        via {nh0} ({fd}/{d['rd_succ']}), {i0}, serno 157",
         f"        via {nh2} ({fd}/{d['rd_succ']}), {i2}",
         f"        via {nh1} ({d['fd_nonfs_total']}/{d['rd_nonfs']}), {i1}"]
    return "\n".join(L)


def build_choices_allthat(d, rnd):
    n1, n2 = d["nets"]
    nh0, nh1, nh2 = d["nh"]
    fd = d["fd"]
    c = [(f"D {n1} [90/{fd}] via {nh0}", True, ""),
         (f"D {n2} [90/{fd}] via {nh0}", True, ""),
         (f"D {n2} [90/{fd}] via {nh2}", True, ""),
         (f"D {n1} [90/{d['rd_succ']}] via {nh0}", False, "経路表のメトリックは FD であり、RD(括弧内の右)ではない。"),
         (f"D {n2} [90/{d['rd_succ']}] via {nh0}", False, "経路表のメトリックは FD であり、RD ではない。"),
         (f"D {n1} [90/{d['fd_fs_total']}] via {nh1}", False, "フィージブル サクセサは経路表に載らない(不等コスト負荷分散なし)。"),
         (f"D {n2} [90/{d['fd_nonfs_total']}] via {nh1}", False, "RD がサクセサの FD 以上で FC を満たさず、サクセサでもない。")]
    trues = [x for x in c if x[1]]
    falses = [x for x in c if not x[1]]
    n_true = rnd.choice([2, 3, 3])
    picks = rnd.sample(trues, n_true) + rnd.sample(falses, 6 - n_true)
    rnd.shuffle(picks)
    return picks


def build_choices_read(d, rnd):
    raise ValueError("rtbasic に read は無い")


def build_match(d, rnd):
    raise ValueError("rtbasic に match は無い")


CORE = {
    "adfix": "最長一致 → AD → メトリックの順。static(1)は IGP より優先されるので、誤った static が正しい IGP 経路を隠す。是正は static の削除か floating static(AD を対抗プロトコルの AD より大きく: OSPF 110 / EIGRP 90 / RIP 120 / EIGRP 外部 170 / eBGP 20 / iBGP 200)。同値は使わない。",
    "adpath": "同じ宛先を複数プロトコルで学習したら AD の小さい経路が採用される(static 1 < eBGP 20 < EIGRP 90 < OSPF 110 < RIP 120)。低速でも static が勝つ。速い経路を使うには static を消すか AD を上げる。OSPF の AD を 11 にしても 1 には勝てない。",
    "ribread": "経路表に載るのはサクセサだけ(等コストなら複数)。表示メトリックは FD(括弧内の左)であり RD ではない。FS(RD < サクセサの FD)は topology にはあるが経路表に載らない(variance なし)。RD ≥ FD の経路は FS でもない。",
}
TITLES = {"adfix": "静的経路と動的経路の優先", "adpath": "AD による経路選択", "ribread": "EIGRP トポロジ テーブルと経路表"}


def question_body(d, choices, form):
    k = d["kind"]
    if k == "adfix":
        name, ad, code = PROTOS[d["proto"]]
        before = (f"{d['r1']} は {name}によって {d['dst']}/24 の正しい経路(next-hop {d['good_nh']})を学習していますが、"
                  f"PC から {d['dst']}/24 への ping が失敗します。\n\n```\n{_adfix_exhibit(d)}\n```")
        if form == "fix":
            ask = f"{d['r1']} で ping を成功させることができる設定はどれですか。なお、{name} の設定は変更しません。(1つを選択してください)"
            ch_md = "\n\n".join(f"**{'ABCDEFG'[i]}.**\n\n```\n{t}\n```" for i, (t, _, _) in enumerate(choices))
        else:
            ask = "この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
            ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    if k == "adpath":
        before = f"```\n{_adpath_exhibit(d)}\n```"
        if form == "select":
            ask = f"{d['src']}/24 から {d['dst']}/24 宛の通信について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
        else:
            ask = f"{d['src']}/24 から {d['dst']}/24 宛の通信を、より帯域の広い経路で転送させる方法を、次のうちから 2 つ選択してください。"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    before = f"```\n{_rib_exhibit(d)}\n```"
    ask = f"上記の情報から、{d['ra']} のルーティング テーブルに載っていると考えられる経路情報をすべて選んでください。なお、不等コスト負荷分散の設定は行っていません。"
    ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. `{t}`" for i, (t, _, _) in enumerate(choices))
    return before, ask, ch_md, ""


def answer_body(d, choices, form):
    keys = [k for k, (t, ok, w) in zip("ABCDEFG", choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip("ABCDEFG", choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[d["kind"]]]
    if d["kind"] == "adfix":
        lines += ["", f"- 世界: 対抗プロトコル= {PROTOS[d['proto']][0]}(AD {PROTOS[d['proto']][1]}) → floating static の閾値はそれより大きい値"]
    return "\n".join(lines)


def pick_count(form, choices):
    if form == "allthat":
        return -1
    if form == "select2":
        return 2
    return 1


def selftest(seeds=40):
    import random as _r
    import re as _re
    ng = n = 0
    bad = {}
    builders = {"select": build_choices_select, "select2": build_choices_select2, "allthat": build_choices_allthat,
                "cause": build_choices_cause, "fix": build_choices_fix}
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = draw(rnd, kind, None, form)
                    choices = builders[form](d, rnd)
                    n_true = sum(1 for x in choices if x[1])
                    if form == "allthat":
                        assert 2 <= n_true <= 3
                    else:
                        assert n_true == (2 if form == "select2" else 1), f"{form} 正解数 {n_true}"
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
    print(f"[gen_paper_rtbasic selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
