#!/usr/bin/env python3
"""FHRP 経路問ファミリ (BL-228・単元 U-A6 の紙面) — gen_paper_mcq.py の shape=fhrp 素材。

「この盤面で通信はどう抜けるか」: ラボと同じ L2 盤面(STP)＋分配ペアの SVI と HSRP で、PC-A(VLAN X)→ PC-B(VLAN Y)の
ping の**往路(エコー要求)と復路(エコー応答)が通るスイッチを順に**、ルーティングする機器とあわせて全部記入させる。
全空欄一致で正答(STP の s_rolemap と同じ穴埋め形の UI)。設計= problems/_drafts/FHRP-PATH.design.md。

kinds:
  h_path: STP(VLAN ごと)＋ HSRP(priority・preempt・起動/再起動の経緯)から往路・復路を決める。
  h_acl : h_path に分配の SVI の ACL(in/out)を足す= 経路に加えて「ping は成功するか・どこで破棄されるか」も記入(ハード)。

裏どり(実機 PoC・poc/fhrp/README.md・IOSvL2 2020):
  選出= priority → 同値なら実 IP の大きい方(同時起動)/ preempt 無しは後から上がった高 priority でも奪わない /
  preempt は priority が**上回る**ときだけ(同値なら IP が大きくても奪わない)/ 同値・preempt 無しで先に上がった方が Active のまま /
  往路は送信元 VLAN の Active、復路は宛先 VLAN の Active がルーティングし、自分の SVI から直接出す(非対称)/
  SVI の ACL は入ってきた VLAN の in・出ていく VLAN の out で評価(ACL 計数で往路=Active X・復路=Active Y を確認)/
  復路が通らない機器の ACL は効かない(片側だけの deny は素通り)。v2 の仮想 MAC= 0000.0c9f.fXXX(グループの 16 進)。
正解= stp_model(VLAN ごとの木の経路)・HSRP の選出は下の _active・ACL は acl_model(実機検証済みの意味評価器)。

公開 API は gen_paper_stp.py と同じ(KINDS/kind_forms/draw/build_match/question_body/answer_body/pick_count/selftest)。
"""
import copy
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acl_model as am  # noqa: E402
import gen_paper_stp as gst  # noqa: E402
import stp_model as sm  # noqa: E402

KINDS = ["h_path", "h_acl"]
SPEED_KINDS = []
THINK_KINDS = ["h_path", "h_acl"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {"h_path": {"match"}, "h_acl": {"match"}}
SPEED_FORMS = {}
DIFF = {"h_path": 4, "h_acl": 5}
TITLES = {"h_path": "FHRP と通信の経路", "h_acl": "FHRP・ACL と通信の経路"}
CIRC = gst.CIRC
LET = "ABCDEFGHIJ"
NONE_TXT = "—(ここで終わり)"
RESULTS = ["成功する", "往路(エコー要求)が破棄される", "復路(エコー応答)が破棄される"]
VLANS = [10, 20, 30, 40, 100, 110, 120, 200, 210]
HSRP_PRIOS = [90, 100, 100, 100, 105, 110, 110, 120]

CORE_PATH = ("往路= 送信元 VLAN の Active がルーティングし、宛先 VLAN へは**自分の SVI から**出す。復路= 宛先側 VLAN の Active が"
        "同じようにルーティングする。VLAN ごとに Active が違えば往路と復路は別の分配を通る(非対称)。フレームは各 VLAN の"
        "スパニング ツリーの木に沿って進むので、root と Active がずれていると分配間やコアを余計に回る。HSRP の選出= priority → "
        "同値なら実 IP の大きい方(同時に起動した場合)。preempt が無ければ後から上がった側は priority が高くても Active を奪わない。"
        "preempt は priority が上回るときだけ働く(同値なら IP が大きくても奪わない)。")
CORE_ACL = ("SVI の ACL は、ルーティングされるパケットが**入ってきた VLAN の SVI で in**・**出ていく VLAN の SVI で out** で評価される。"
            "ACL は状態を持たないので、エコー応答はエコー応答として別に評価される。復路が通らない機器の ACL は復路に効かない。")
CORE = {"h_path": CORE_PATH, "h_acl": CORE_PATH + " " + CORE_ACL}     # gen_paper_mcq が kind で引く


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


# ==========================================================================
# 盤面
# ==========================================================================
def _layout(b):
    """(ゲートウェイの分配ペア, アクセス, L2 だけのコア)。"""
    if b["shape"].startswith("3tier"):
        return ["SW03", "SW04"], ["SW05", "SW06"], ["SW01", "SW02"]
    return ["SW01", "SW02"], ["SW03", "SW04"], []


def _active(hs, ds, scen):
    """HSRP の Active。hs= {sw: {"prio", "pre", "ip4"}}(ip4= 実 IP の最終オクテット)。
    scen= ("sim",) 同時起動 / ("reboot", R) 同時起動→ R を再起動して復帰。"""
    a, c = ds
    first = max(ds, key=lambda x: (hs[x]["prio"], hs[x]["ip4"]))
    if scen[0] == "sim":
        return first, "同時に起動したので priority が高い方" + ("(同値なので実 IP の大きい方)" if hs[a]["prio"] == hs[c]["prio"] else "")
    r = scen[1]
    other = c if r == a else a
    if first != r:
        return first, f"{r} は再起動前から Standby。復帰しても {other} より priority が上回らないので Standby のまま"
    if hs[r]["prio"] > hs[other]["prio"] and hs[r]["pre"]:
        return r, f"{r} の再起動中は {other} が Active。{r} は priority が上回り preempt があるので、復帰後に Active を取り戻す"
    why = ("preempt が無い" if not hs[r]["pre"] else "priority が同値(preempt は priority が上回るときだけ働く)")
    return other, f"{r} の再起動中に {other} が Active になり、{r} は復帰しても{why}ので {other} が Active のまま"


def _topo(b, sw, v, cost_ovr=None, port_prio=None):
    return sm.Topo(sw, b["links"], b["method"], port_prio or {}, cost_ovr or {}, v).solve()


def _acl_text(name, lines):
    return "\n".join([f"Extended IP access list {name}"] + [f"    {10 * (i + 1)} {x}" for i, x in enumerate(lines)])


def _draw_board(rnd):
    for _ in range(200):
        b = gst._draw_rolemap(rnd, family=rnd.choice(["lab", "lab", "mut"]))
        if not (b["shape"].startswith("3tier") or b["shape"].startswith("2tier")):
            continue
        return b
    raise ValueError("盤面が作れない")


def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    for _try in range(400):
        d = _draw_once(rnd, kind)
        if d is not None:
            return d
    raise ValueError("条件を満たす盤面が作れない")


def _draw_once(rnd, kind):
    b = _draw_board(rnd)
    ds, acc, core = _layout(b)
    X, Y = rnd.sample(VLANS, 2)
    oct2 = rnd.randint(20, 250)
    swX = copy.deepcopy(b["sw"])
    swY = copy.deepcopy(b["sw"])
    if rnd.random() < 0.6:                                  # VLAN Y の priority は別に引く(MAC は同じ)
        for x in swY:
            swY[x]["prio"] = rnd.choice(gst.RM_FREE_PRIOS)
    try:
        tX = _topo(b, swX, X, b["cost_ovr"], b["port_prio"])
        tY = _topo(b, swY, Y)
    except ValueError:
        return None
    hs = {v: {x: {"prio": rnd.choice(HSRP_PRIOS), "pre": rnd.random() < 0.5, "ip4": int(x[-1])} for x in ds} for v in (X, Y)}
    scen = ("sim",) if rnd.random() < 0.6 else ("reboot", rnd.choice(ds))
    actX, whyX = _active(hs[X], ds, scen)
    actY, whyY = _active(hs[Y], ds, scen)
    pa, pb = rnd.choice(acc), rnd.choice(acc)
    fwd = tX.path(pa, actX) + tY.path(actX, pb)[1:]
    ret = tY.path(pb, actY) + tX.path(actY, pa)[1:]
    extra = 1 if kind == "h_acl" else rnd.choice([1, 2])
    slots = max(len(fwd), len(ret)) + extra                # 経路長が枠の数から割れないよう余白を 1〜2
    n_bl = 2 * slots + 2 + (2 if kind == "h_acl" else 0)
    if n_bl > 20:
        return None
    ip = {"A": f"10.{oct2}.{X}.101", "B": f"10.{oct2}.{Y}.102"}
    d = {"kind": kind, "world": "-", "form": "match", "diff": DIFF[kind], "b": b, "ds": ds, "acc": acc, "core": core,
         "X": X, "Y": Y, "oct2": oct2, "swX": swX, "swY": swY, "tX": tX, "tY": tY, "hs": hs, "scen": scen,
         "act": {X: actX, Y: actY}, "why": {X: whyX, Y: whyY}, "pa": pa, "pb": pb, "ip": ip,
         "fwd": fwd, "ret": ret, "slots": slots, "acls": []}
    if kind == "h_acl":
        if not _draw_acls(rnd, d):
            return None
    return d


# ---- ハード: SVI の ACL ------------------------------------------------------------
def _acl_templates(d):
    a, bb = d["ip"]["A"], d["ip"]["B"]
    netA, netB = f"10.{d['oct2']}.{d['X']}.0", f"10.{d['oct2']}.{d['Y']}.0"
    return [
        ["deny icmp any any echo-reply", "permit ip any any"],
        [f"deny icmp host {a} host {bb} echo", "permit ip any any"],
        [f"deny icmp host {bb} host {a} echo-reply", "permit ip any any"],
        ["permit icmp any any echo", "permit tcp any any eq www"],                 # 応答は暗黙 deny
        [f"deny icmp {netB} 0.0.0.255 any", "permit ip any any"],
        [f"deny icmp {netA} 0.0.0.255 {netB} 0.0.0.255 echo", "permit ip any any"],
        ["permit ip any any"],
        [f"permit icmp {netA} 0.0.0.255 any", f"permit icmp {netB} 0.0.0.255 any"],
    ]


def _eval_acls(d):
    """(結果の番号 0/1/2, 破棄した機器 or None, 評価の記録 [(適用, パケット, 許否, 当たった行)])。"""
    X, Y = d["X"], d["Y"]
    req = {"proto": "icmp", "src": d["ip"]["A"], "dst": d["ip"]["B"], "icmp_type": 8}
    rep = {"proto": "icmp", "src": d["ip"]["B"], "dst": d["ip"]["A"], "icmp_type": 0}
    trail = []

    def run(sw, steps, vec, label):
        for vl, direction in steps:
            for ap in d["acls"]:
                if (ap["sw"], ap["vlan"], ap["dir"]) == (sw, vl, direction):
                    ents = am.parse_show_access_lists(_acl_text(ap["name"], ap["lines"]))[ap["name"]]
                    hit = next((e for e in ents if am.entry_matches(e, vec)), None)
                    ok = am.evaluate(ents, vec)
                    trail.append((ap, label, ok, (f"{hit['seq']} " + ap["lines"][hit["seq"] // 10 - 1]) if hit else "暗黙の deny"))
                    if not ok:
                        return False
        return True

    if not run(d["act"][X], [(X, "in"), (Y, "out")], req, "往路"):
        return 1, d["act"][X], trail
    if not run(d["act"][Y], [(Y, "in"), (X, "out")], rep, "復路"):
        return 2, d["act"][Y], trail
    return 0, None, trail


def _draw_acls(rnd, d):
    want = rnd.randrange(3)                                     # 成功 / 往路で破棄 / 復路で破棄 を均等に
    temps = _acl_templates(d)
    for _ in range(60):
        n = rnd.choice([1, 2, 2, 3])
        places = rnd.sample([(x, v, dr) for x in d["ds"] for v in (d["X"], d["Y"]) for dr in ("in", "out")], n)
        d["acls"] = [{"sw": x, "vlan": v, "dir": dr, "name": f"SVI{v}-{dr.upper()}", "lines": rnd.choice(temps)}
                     for x, v, dr in places]
        res, where, trail = _eval_acls(d)
        used = {(t[0]["sw"], t[0]["vlan"], t[0]["dir"]) for t in trail}
        decoy = any((a["sw"], a["vlan"], a["dir"]) not in used for a in d["acls"])
        if res == want and decoy:                               # 経路外に置いた ACL(効かない罠)を必ず 1 つ含む
            d["res"], d["drop"], d["trail"] = res, where, trail
            return True
    return False


# ==========================================================================
# 設問・解答
# ==========================================================================
def _choices(d):
    ch = [(LET[i], x) for i, x in enumerate(d["b"]["names"])]
    ch.append((LET[len(ch)], NONE_TXT))
    if d["kind"] == "h_acl":
        for r in RESULTS:
            ch.append((LET[len(ch)], r))
    return ch


def _cells(d):
    """空欄の並び= [(ラベル, 正解の記号)]。往路 1..n・復路 1..n・ルーティング機器 2・(ハード)結果・破棄する機器。"""
    ch = _choices(d)
    let = {t: l for l, t in ch}
    out = []
    for name, path in (("往路", d["fwd"]), ("復路", d["ret"])):
        for i in range(d["slots"]):
            out.append((f"{name} {i + 1}", let[path[i]] if i < len(path) else let[NONE_TXT]))
    out.append(("往路でルーティングする機器", let[d["act"][d["X"]]]))
    out.append(("復路でルーティングする機器", let[d["act"][d["Y"]]]))
    if d["kind"] == "h_acl":
        out.append(("ping の結果", let[RESULTS[d["res"]]]))
        out.append(("破棄する機器", let[d["drop"]] if d["drop"] else let[NONE_TXT]))
    return out


def build_match(d, rnd):
    cells = _cells(d)
    if len(cells) > len(CIRC):
        raise ValueError("空欄が 20 を超える")
    terms = [(CIRC[i], lab) for i, (lab, _l) in enumerate(cells)]
    ans = {CIRC[i]: l for i, (_lab, l) in enumerate(cells)}
    return terms, _choices(d), ans


def build_choices_select(d, rnd):
    raise ValueError("fhrp は全記入(match)のみ")


build_choices_select2 = build_choices_allthat = build_choices_read = build_choices_cause = build_choices_fix = build_choices_select


def _mermaid(b):
    L = ["```mermaid", "graph TD"]
    for li, layer in enumerate(b["layers"]):
        L.append(f'  subgraph L{li}["{b["layer_names"][li]}"]')
        L += [f'    {gst._mm(x)}["{x}"]' for x in layer]
        L.append("  end")
    for a, ia, c, ic, _sp in b["links"]:
        L.append(f'  {gst._mm(a)} ---|"{ia["name"]} — {ic["name"]}"| {gst._mm(c)}')
    L.append("```")
    return L


def _hsrp_cfg(d, x):
    L = [f"{x}(config)# ip routing"]
    for v in (d["X"], d["Y"]):
        h = d["hs"][v][x]
        L += [f"{x}(config)# interface Vlan{v}",
              f"{x}(config-if)# ip address 10.{d['oct2']}.{v}.{h['ip4']} 255.255.255.0",
              f"{x}(config-if)# standby version 2",
              f"{x}(config-if)# standby {v} ip 10.{d['oct2']}.{v}.254"]
        if h["prio"] != 100:
            L.append(f"{x}(config-if)# standby {v} priority {h['prio']}")
        if h["pre"]:
            L.append(f"{x}(config-if)# standby {v} preempt")
        for ap in d["acls"]:
            if ap["sw"] == x and ap["vlan"] == v:
                L.append(f"{x}(config-if)# ip access-group {ap['name']} {ap['dir']}")
    for ap in d["acls"]:
        if ap["sw"] == x:
            L.append(f"{x}(config)# ip access-list extended {ap['name']}")
            L += [f"{x}(config-ext-nacl)# {ln}" for ln in ap["lines"]]
    return "\n".join(L)


def question_body(d, choices, form):
    b, X, Y = d["b"], d["X"], d["Y"]
    L = _mermaid(b)
    # 接続表(2026-09-29 ユーザ要望= 図の線をたどらなくても配線を引けるように)。図と同じ順・同じ IF 名。
    L += ["", "| スイッチ | インタフェース(ポート番号) | 対向スイッチ | 対向インタフェース(ポート番号) |", "|---|---|---|---|"]
    for a, ia, c, ic, _sp in b["links"]:
        L.append(f"| {a} | {ia['name']}({ia['num']}) | {c} | {ic['name']}({ic['num']}) |")
    L += ["", f"| スイッチ | 役割 | ブリッジ プライオリティ(VLAN {X}) | ブリッジ プライオリティ(VLAN {Y}) | MAC アドレス |",
          "|---|---|---|---|---|"]
    for x in b["names"]:
        L.append(f"| {x} | {b['label'][x]} | {d['swX'][x]['prio']} | {d['swY'][x]['prio']} | {b['sw'][x]['mac']} |")
    extra = []
    for (x, ifn), v in sorted(b["cost_ovr"].items()):
        extra.append(f"{x}(config)# interface {ifn}\n{x}(config-if)# spanning-tree vlan {X} cost {v}")
    for (x, ifn), v in sorted(b["port_prio"].items()):
        extra.append(f"{x}(config)# interface {ifn}\n{x}(config-if)# spanning-tree vlan {X} port-priority {v}")
    if extra:
        L += ["", "スパニング ツリーで既定値から変更している設定は次のとおりです。", "", "```", "\n".join(extra), "```"]
    gw = "・".join(d["ds"])
    L += ["", f"全スイッチで Rapid PVST+ を使用し、パス コストは{'ロング' if b['method'] == 'long' else 'ショート'}方式にそろえています。"
          f"スイッチ間のリンクはすべて 1 Gbps・全二重のトランクで、VLAN {X}・VLAN {Y} を通します。"
          "ポート ID はポート プライオリティ(既定 128)とポート番号で構成します。",
          "", f"{gw} は VLAN {X}・VLAN {Y} の SVI を持ち、HSRP で既定ゲートウェイを冗長化しています。"
          + ("コアは L2 の中継だけを行います。" if d["core"] else "") + "アクセスのスイッチはルーティングしません。", ""]
    for x in d["ds"]:
        L += ["```", _hsrp_cfg(d, x), "```", ""]
    L += ["| 端末 | VLAN | 接続先 | IP アドレス | 既定ゲートウェイ |", "|---|---|---|---|---|",
          f"| PC-A | {X} | {d['pa']} | {d['ip']['A']}/24 | 10.{d['oct2']}.{X}.254 |",
          f"| PC-B | {Y} | {d['pb']} | {d['ip']['B']}/24 | 10.{d['oct2']}.{Y}.254 |", ""]
    if d["scen"][0] == "sim":
        L.append(f"{gw} は同時に起動し、その後は構成の変更も障害もありません。")
    else:
        L.append(f"{gw} は同時に起動しました。その後 {d['scen'][1]} を再起動し、完全に復帰しています。ほかに構成の変更や障害はありません。")
    L.append("ARP と MAC アドレスの学習は完了しているものとします。")
    ask = (f"PC-A から PC-B へ ping を 1 回実行します。エコー要求(往路)とエコー応答(復路)が通るスイッチを、"
           "PC 側のアクセス スイッチから順に選んでください。同じスイッチを 2 回通るときはその都度記入し、経路が終わったら"
           f"残りの欄は「{NONE_TXT}」を選びます。あわせて、往路と復路をそれぞれルーティングする機器を選んでください。"
           + ("さらに ping の結果と、破棄される場合はそれを破棄する機器(成功する場合は「—」)を選んでください。"
              "往路・復路の経路は ACL に関係なく転送の仕組みで決まる経路を答えます(破棄される場合も、破棄されなかったとした経路)。"
              if d["kind"] == "h_acl" else "")
           + f"**①〜{CIRC[len(choices[0]) - 1]} のすべてを正しく選んだ場合にのみ得点**になります。")
    head = "| 項目 | " + " | ".join(str(i + 1) for i in range(d["slots"])) + " |"
    sep = "|---|" + "---|" * d["slots"]
    rows = [head, sep]
    for k, name in enumerate(("往路", "復路")):
        rows.append(f"| {name} | " + " | ".join(f"［{CIRC[k * d['slots'] + i]}］" for i in range(d["slots"])) + " |")
    base = 2 * d["slots"]
    tail = ["", "| 項目 | 選択 |", "|---|---|",
            f"| 往路でルーティングする機器 | ［{CIRC[base]}］ |", f"| 復路でルーティングする機器 | ［{CIRC[base + 1]}］ |"]
    if d["kind"] == "h_acl":
        tail += [f"| ping の結果 | ［{CIRC[base + 2]}］ |", f"| 破棄する機器 | ［{CIRC[base + 3]}］ |"]
    tbl = "\n".join(["### 解答の表"] + [""] + rows + tail)
    ch_md = "\n\n".join(f"{a}. {t}" for a, t in choices[1])
    return "\n".join(L), ask, ch_md, tbl


def answer_body(d, choices, form):
    _terms, ch, ans = choices
    name = dict(ch)
    X, Y = d["X"], d["Y"]
    fw = " → ".join(d["fwd"])
    rt = " → ".join(d["ret"])
    L = ["## 正解", "", "**" + "、".join(f"{k}－{v}" for k, v in ans.items()) + "**", "", "## 解説", "",
         f"- 往路: {fw}(VLAN {X} の木で {d['pa']} → {d['act'][X]}、{d['act'][X]} がルーティングして VLAN {Y} の木で → {d['pb']})",
         f"- 復路: {rt}(VLAN {Y} の木で {d['pb']} → {d['act'][Y]}、{d['act'][Y]} がルーティングして VLAN {X} の木で → {d['pa']})",
         f"- VLAN {X} の Active= **{d['act'][X]}**: {d['why'][X]}。",
         f"- VLAN {Y} の Active= **{d['act'][Y]}**: {d['why'][Y]}。"]
    if d["act"][X] != d["act"][Y]:
        L.append(f"- VLAN ごとに Active が違うので、往路は {d['act'][X]}・復路は {d['act'][Y]} を通る(非対称)。")
    if d["kind"] == "h_acl":
        L += ["", f"- ping の結果= **{RESULTS[d['res']]}**" + (f"(破棄= {d['drop']})" if d["drop"] else "") + "。評価された ACL:"]
        for ap, lab, ok, line in d["trail"]:
            L.append(f"  - {lab}: {ap['sw']} の Vlan{ap['vlan']} {ap['dir']}({ap['name']})→ {'許可' if ok else '拒否'}(当たった行= {line})")
        used = {(t[0]["sw"], t[0]["vlan"], t[0]["dir"]) for t in d["trail"]}
        for ap in d["acls"]:
            if (ap["sw"], ap["vlan"], ap["dir"]) not in used:
                L.append(f"  - {ap['sw']} の Vlan{ap['vlan']} {ap['dir']}({ap['name']})は、この ping の往路も復路も通らないので評価されない。")
    L += ["", "| 空欄 | 項目 | 正しい選択 |", "|---|---|---|"]
    for (k, lab), (_k, l) in zip(_terms, ans.items()):
        L.append(f"| {k} | {lab} | {l}. {name[l]} |")
    L += ["", f"### VLAN {X} のスパニング ツリー", "", gst.explain_board({**d["b"], "sw": d["swX"], "names": d["b"]["names"]}, d["tX"]),
          "", f"### VLAN {Y} のスパニング ツリー", "", gst.explain_board({**d["b"], "sw": d["swY"], "names": d["b"]["names"]}, d["tY"]),
          "", CORE_PATH + ("\n\n" + CORE_ACL if d["kind"] == "h_acl" else ""),
          "", "- 根拠: HSRP の選出・preempt・非対称経路・SVI の ACL の効き方は実機(IOSvL2)で確認済み(poc/fhrp/README.md)。"]
    return "\n".join(L)


def pick_count(form, choices):
    return 1


# ==========================================================================
# selftest
# ==========================================================================
def selftest(seeds=400):
    ng = n = 0
    bad = {}
    stat = {"asym": 0, "res": [0, 0, 0], "reboot": 0}
    for kind in KINDS:
        for s in range(seeds):
            n += 1
            try:
                rnd = random.Random(hash((kind, s)) & 0xFFFFFFFF)
                d = draw(rnd, kind)
                ch = build_match(d, rnd)
                terms, choices, ans = ch
                assert len(ans) <= 20
                letters = {l for l, _ in choices}
                assert set(ans.values()) <= letters
                assert d["fwd"][0] == d["pa"] and d["fwd"][-1] == d["pb"] and d["act"][d["X"]] in d["fwd"]
                assert d["ret"][0] == d["pb"] and d["ret"][-1] == d["pa"] and d["act"][d["Y"]] in d["ret"]
                assert max(len(d["fwd"]), len(d["ret"])) < d["slots"], "余白が無い"
                before, ask, ch_md, tbl = question_body(d, ch, "match")
                assert len(re.findall(r"［[①-⑳]］", tbl)) == len(ans), "空欄の数"
                assert not re.search(r"正解|故障|kind=|method=", before + ask + tbl + ch_md), "漏えい語"
                assert "対応" not in "\n".join(l for l in (before + ask + tbl).split("\n") if l.startswith("#"))
                body = answer_body(d, ch, "match")
                key = re.search(r"^\*\*(.+)\*\*$", body, re.M).group(1)
                assert len(re.findall(r"[①-⑳]－[A-J]", key)) == len(ans)
                if d["act"][d["X"]] != d["act"][d["Y"]]:
                    stat["asym"] += 1
                if d["scen"][0] == "reboot":
                    stat["reboot"] += 1
                if kind == "h_acl":
                    stat["res"][d["res"]] += 1
                    assert (d["drop"] is None) == (d["res"] == 0)
            except (AssertionError, ValueError, KeyError) as exc:
                ng += 1
                bad.setdefault(kind, [0, repr(exc)])[0] += 1
    # 選出の規則(実機 PoC の 4 点)
    ds = ["SW01", "SW02"]
    hs = lambda p1, p2, e1, e2: {"SW01": {"prio": p1, "pre": e1, "ip4": 1}, "SW02": {"prio": p2, "pre": e2, "ip4": 2}}
    rules = [(hs(100, 100, 0, 0), ("sim",), "SW02"),                  # 同値→ IP の大きい方
             (hs(110, 100, 0, 0), ("sim",), "SW01"),
             (hs(110, 100, 0, 0), ("reboot", "SW01"), "SW02"),        # preempt 無し→ 取り戻さない
             (hs(110, 100, 1, 0), ("reboot", "SW01"), "SW01"),        # 上回る＋preempt→ 取り戻す
             (hs(100, 100, 1, 1), ("reboot", "SW02"), "SW01")]        # 同値の preempt は働かない
    for h, sc, want in rules:
        n += 1
        if _active(h, ds, sc)[0] != want:
            ng += 1
            bad.setdefault("rules", [0, repr((sc, want))])[0] += 1
    for k, (c, ex) in sorted(bad.items()):
        print(f"  NG {k}: {c} 件 (例: {ex})")
    print(f"[gen_paper_fhrp selftest] {n} 件 / NG {ng}  非対称 {stat['asym']}・再起動の経緯 {stat['reboot']}・ACL 結果(成功/往路/復路) {stat['res']}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
