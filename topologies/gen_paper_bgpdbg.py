#!/usr/bin/env python3
"""BGP ループバック・ピアリング debug 読解 紙面問題 (BL-085 → BL-124 で選択式化)。

ユーザ発案: 「debug メッセージからコンフィグを想像し、修正案まで提出させる」。
BL-085 の原形は**記述式**(採点は Claude がルーブリックで実施)。
★BL-124(2026-08-16): 通常出題は選択式(dbgconf/select2/fix/read)へ改修し、
mixed・問題パックに合流した。記述式は `--forms essay` の明示時のみ
(BL-111 の MPLS L3VPN 記述式が essay 機構を流用予定のため温存)。

素材は PoC 実機採取(poc/bgpdbg/README.md・IOL 17.15)の実出力:
  ★`BGP: <peer> open active, local address <X>` … その機がどの送信元で開きに行ったか
     = update-source の有無が両側それぞれについて確定する
  ★行頭の <peer> … その機の neighbor 文の宛先(Lo宛か物理宛か)
  ★`open failed: Connection refused by remote host` … 相手がその送信元を neighbor として
     持っていない(TCP RST)。到達性の問題ではない
  ★eBGP × multihop 欠け = `Active open failed - no route to peer`
     (static で経路があるのに出る=シングルホップ検査。字面に釣られる罠)
  ★片側だけ update-source 欠けは **UP してしまう**(接続レースで update-source 側が勝つ)
     → 単独では故障にならない。variant='asym_up' で「なぜ UP か」を問う上級形に使う。

提示する出力は **debug ログ + variant 固有の補助出力(経路表 / ping)のみ**。
`show ip bgp summary` は出さない(上記の理由)。

variant:
  addr_mismatch (既定・難4) 両側の neighbor 宛先が食い違う(Lo宛 vs 物理宛)
  ebgp_multihop (難4)       eBGP Lo ピアで multihop 欠け(no route to peer)
  asym_up       (難5)       片側 update-source 欠けだが Established。なぜ動くか+是正
"""
import random

VARIANTS = ["addr_mismatch", "ebgp_multihop", "asym_up"]
DIFF = {"addr_mismatch": 4, "ebgp_multihop": 4, "asym_up": 5}


def draw(rnd, variant=None):
    d = {"shape": "bgpdbg"}
    d["variant"] = variant or rnd.choice(VARIANTS)
    a, b = rnd.sample(range(1, 99), 2)
    d["lo_a"], d["lo_b"] = f"{a}.{a}.{a}.{a}", f"{b}.{b}.{b}.{b}"
    o = rnd.randint(0, 240)
    d["link"] = f"10.{rnd.randint(0, 250)}.{o}"
    d["ip_a"], d["ip_b"] = f"{d['link']}.1", f"{d['link']}.2"
    if d["variant"] == "ebgp_multihop":
        d["as_a"], d["as_b"] = rnd.randint(64512, 65100), rnd.randint(65101, 65534)
    else:
        d["as_a"] = d["as_b"] = rnd.randint(64512, 65534)
    names = [f"RT{i:02d}" for i in range(1, 3)]
    rnd.shuffle(names)
    d["A"], d["B"] = names
    d["igp"] = rnd.choice([f"OSPF {rnd.randint(1, 99)} ", "スタティック・ルート"])
    return d


# --------------------------------------------------------------------------
# debug 出力(PoC 実出力の書式をそのまま値差し替え)
# --------------------------------------------------------------------------
class _Clock:
    """★debug のタイムスタンプは必ず単調増加させる(2026-08-02 出題で順不同を指摘)。
    ノードごとに独立した時刻列を持ち、呼ぶたびに数百ms〜数秒進める。"""

    def __init__(self, rnd, start_min=0):
        self.rnd = rnd
        self.sec = start_min * 60 + rnd.randint(0, 40)

    def __call__(self, step=None):
        self.sec += step if step is not None else self.rnd.randint(0, 3)
        h, m, s = 9 + self.sec // 3600, (self.sec // 60) % 60, self.sec % 60
        return f"*Aug  2 {h:02d}:{m:02d}:{s:02d}.{self.rnd.randint(100, 999)}"


def debug_blocks(d, rnd):
    A, B = d["A"], d["B"]
    v = d["variant"]
    ta, tb = _Clock(rnd, 0), _Clock(rnd, 1)
    if v == "ebgp_multihop":
        a_lines = [f"{ta(rnd.randint(50, 80))}: BGP: {d['lo_b']} Active open failed - no route to "
                   f"peer, open active delayed {rnd.choice([6144, 8192, 9216, 12288])}ms "
                   "(35000ms max, 60% jitter)" for i in range(4)]
        b_lines = [f"{tb(rnd.randint(50, 80))}: BGP: {d['lo_a']} Active open failed - no route to "
                   f"peer, open active delayed {rnd.choice([6144, 9216, 13312])}ms "
                   "(35000ms max, 60% jitter)" for i in range(3)]
    elif v == "asym_up":
        a_lines = [f"{ta()}: BGP: {d['lo_b']} active went from Idle to Active",
                   f"{ta()}: BGP: {d['lo_b']} open active, local address {d['lo_a']}",
                   f"{ta()}: %BGP-5-ADJCHANGE: neighbor {d['lo_b']} Up "]
        b_lines = [f"{tb()}: BGP: {d['lo_a']} active went from Idle to Active",
                   f"{tb()}: BGP: {d['lo_a']} open active, local address {d['ip_b']}",
                   f"{tb()}: BGP: {d['lo_a']} open failed: Connection refused by "
                   "remote host",
                   f"{tb()}: BGP: {d['lo_a']} Active open failed - tcb is not "
                   "available, open active delayed 12288ms (35000ms max, 60% jitter)",
                   f"{tb()}: %BGP-5-ADJCHANGE: neighbor {d['lo_a']} Up "]
    else:   # addr_mismatch
        a_lines = [f"{ta()}: BGP: {d['lo_b']} active went from Idle to Active",
                   f"{ta()}: BGP: {d['lo_b']} open active, local address {d['lo_a']}",
                   f"{ta()}: BGP: {d['lo_b']} open failed: Connection refused by "
                   "remote host",
                   f"{ta()}: BGP: {d['lo_b']} Active open failed - tcb is not "
                   "available, open active delayed 14336ms (35000ms max, 60% jitter)",
                   f"{ta()}: BGP: ses global {d['lo_b']} (0x7352B1A93C78:0) act "
                   "Reset (Active open failed).",
                   f"{ta()}: BGP: {d['lo_b']} active went from Active to Idle"]
        b_lines = [f"{tb()}: BGP: {d['ip_a']} active went from Idle to Active",
                   f"{tb()}: BGP: {d['ip_a']} open active, local address {d['ip_b']}",
                   f"{tb()}: BGP: {d['ip_a']} open failed: Connection refused by "
                   "remote host",
                   f"{tb()}: BGP: {d['ip_a']} Active open failed - tcb is not "
                   "available, open active delayed 12288ms (35000ms max, 60% jitter)",
                   f"{tb()}: BGP: ses global {d['ip_a']} (0x72F53161A0C0:0) act "
                   "Reset (Active open failed).",
                   f"{tb()}: BGP: {d['ip_a']} active went from Active to Idle"]
    return a_lines, b_lines


# ★show ip bgp summary は出さない(2026-08-02 ユーザ指摘): neighbor 宛先も状態も
#   debug の行から導けるため冗長であり、表を見るだけで答えに近づくヒントになる。


def _route_out(node, dst, via, igp):
    """★経路表の Known via は問題文の「到達性の提供元」と一致させること
    (2026-08-02: OSPF と書きながら static を出す不整合を修正)。"""
    if igp.strip().startswith("OSPF"):
        pid = igp.split()[1]
        known = f'  Known via "ospf {pid}", distance 110, metric 11, type intra area'
        extra = "      Route metric is 11, traffic share count is 1"
    else:
        known = '  Known via "static", distance 1, metric 0'
        extra = "      Route metric is 0, traffic share count is 1"
    return (f"{node}# show ip route {dst}\n"
            f"Routing entry for {dst}/32\n"
            f"{known}\n"
            "  Routing Descriptor Blocks:\n"
            f"  * {via}\n"
            f"{extra}")


def extra_block(d):
    """variant 固有の補助出力(経路の存在=誤診の罠 等)。
    ★ebgp_multihop では **両側の経路表**を出す(2026-08-02 出題フィードバック):
      片側だけだと「対向に経路が無いのでは」という誤仮説を提示情報で否定できない。"""
    if d["variant"] == "ebgp_multihop":
        return (_route_out(d["A"], d["lo_b"], d["ip_b"], d["igp"]) + "\n```\n```\n"
                + _route_out(d["B"], d["lo_a"], d["ip_a"], d["igp"]))
    return (f"{d['A']}# ping {d['lo_b']} source {d['lo_a']} repeat 3\n"
            "Type escape sequence to abort.\n"
            f"Sending 3, 100-byte ICMP Echos to {d['lo_b']}, timeout is 2 seconds:\n"
            f"Packet sent with a source address of {d['lo_a']}\n"
            "!!!\n"
            "Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/2 ms")


# --------------------------------------------------------------------------
# 設問・模範解答(ルーブリック)
# --------------------------------------------------------------------------
def questions(d):
    A, B = d["A"], d["B"]
    q = [f"1. 示されているところの出力から、{A} および {B} の、BGP のネイバーに"
         "関する構成が、それぞれ現在どのようになっていると判断されるか、"
         "根拠となる出力の行を挙げて、記述してください。",
         "2. 上記の判断の根拠として、示されているところのメッセージが、"
         "何を意味しているのかを、記述してください。",
         f"3. 要件({'両ルータの間で BGP ピアが確立されること' if d['variant'] != 'asym_up' else 'ピアの確立は維持しつつ、構成の非対称を解消すること'})を"
         "満たすために、どのルータに、どのような構成の変更を行うべきか、"
         "コマンドを含めて記述してください。"]
    return q


def rubric(d):
    A, B, v = d["A"], d["B"], d["variant"]
    if v == "addr_mismatch":
        return {
            "総点": 100,
            "項目": [
                (f"{A} の構成の特定(30点): neighbor は対向の**ループバック** "
                 f"{d['lo_b']} 宛。`open active, local address {d['lo_a']}` から "
                 f"**update-source Loopback0 が設定されている**と判断できる", 30),
                (f"{B} の構成の特定(30点): neighbor は対向の**物理インターフェイス** "
                 f"{d['ip_a']} 宛。`local address {d['ip_b']}` から "
                 "**update-source は設定されていない**と判断できる", 30),
                ("メッセージの解釈(20点): `Connection refused by remote host` は "
                 "**相手がその送信元アドレスを neighbor として持っていない**ため TCP RST "
                 "を返したもの。経路や IF の障害ではない(ping は成功している)", 20),
                (f"修正案(20点): {B} を `no neighbor {d['ip_a']} remote-as` → "
                 f"`neighbor {d['lo_a']} remote-as {d['as_a']}` + "
                 f"`neighbor {d['lo_a']} update-source Loopback0` に是正する"
                 f"(または {A} 側を物理宛に揃える。ただし Lo ピアの設計意図に反する)", 20),
            ],
            "減点": ["両側の判定が debug の行と対応づけられていない",
                     "到達性(経路・IF)の問題と誤診している",
                     "片側だけの修正で完了としている"],
        }
    if v == "ebgp_multihop":
        return {
            "総点": 100,
            "項目": [
                (f"両側の構成の特定(30点): 双方とも対向の**ループバック**宛の "
                 f"eBGP ピア(AS {d['as_a']} ⇔ AS {d['as_b']})。"
                 "**両側ともピア宛の静的経路を保持している**(出力で確認できる)。"
                 "ループバック同士のピアであるため `update-source Loopback0` が"
                 "設定されている(少なくとも必要である)ことに言及していれば加点", 30),
                ("メッセージの解釈(35点): `Active open failed - no route to peer` は "
                 "**eBGP のシングルホップ検査(直接接続の確認)に失敗**していることを示す。"
                 "★**両側とも経路を保持しているのに両側とも同じメッセージを出している**"
                 "という矛盾が根拠。字義どおりの『経路が無い』ではない", 35),
                (f"修正案(35点): 両ルータに `neighbor <対向Lo> ebgp-multihop 2` を設定する"
                 "(または `disable-connected-check`。**片側だけでは確立しない**)", 35),
            ],
            "減点": ["経路(static/IGP)の追加や修正で直そうとしている",
                     "片側にだけ multihop を設定している",
                     "update-source の欠落と誤診している"],
        }
    return {
        "総点": 100,
        "項目": [
            (f"{A} の構成の特定(20点): neighbor は対向 Lo {d['lo_b']} 宛・"
             f"`local address {d['lo_a']}` から update-source Loopback0 あり", 20),
            (f"{B} の構成の特定(20点): neighbor は対向 Lo {d['lo_a']} 宛だが、"
             f"`local address {d['ip_b']}` から **update-source は無い**", 20),
            (f"★確立している理由の説明(40点): {B} 発の接続(送信元 {d['ip_b']})は "
             f"{A} が neighbor として持たないため拒否されるが、**{A} 発の接続"
             f"(送信元 {d['lo_a']})は {B} の neighbor {d['lo_a']} に一致して受理**される。"
             "接続の競合において update-source を持つ側の接続が残るため Established になる", 40),
            (f"修正案(20点): {B} に `neighbor {d['lo_a']} update-source Loopback0` を"
             "設定し、両側の構成を対称にする(現状は片側の接続開始に依存しており、"
             "順序や再接続の条件によっては確立しない可能性がある)", 20),
        ],
        "減点": ["『UP しているので問題なし』と結論している",
                 "拒否メッセージと ADJCHANGE Up の共存を説明できていない"],
    }


# ==========================================================================
# 選択式化 (BL-124・2026-08-16) — 構成モデル・可視指紋・選択肢ビルダ
# ==========================================================================
# 記述式の難しさの核3点を選択式の各形で保存する:
#   dbgconf … 逆問題「この出力を生じさせている構成はどれか」(単一選択・全 variant。
#             aaa の dbgconf 形= BL-103① の前例に従う)
#   select2 … 是正の2アクション複数選択(addr_mismatch / ebgp_multihop。
#             ★ebgp_multihop は「片側だけでは確立しない」= Choose two が最も自然)
#   fix     … 是正の単一選択(asym_up: B への update-source が唯一の安全手)
#   read    … 状態の事実文を2つ選ぶ(asym_up の「なぜ UP か」の器・authread 方式)
#
# 構成は3属性で持つ: nbr("lo"/"phy")= neighbor 文の宛先 / upd= update-source /
# mh= ebgp-multihop。★可視指紋 visible() は「debug に実際に現れる要素」だけを
# 返すのが肝: ebgp_multihop の no route to peer は open active 行の**前**に失敗する
# = 送信元(update-source の有無)が観測できない。この可視性の欠落をモデル化しないと
# 「update-source だけ違う構成」が同一出力になり dbgconf が二重正解化する。

MCQ_FORMS = {"addr_mismatch": ["select2", "dbgconf"],
             "ebgp_multihop": ["select2", "dbgconf"],
             "asym_up": ["read", "fix", "dbgconf"]}

# 形の抽選比。★BL-122(2026-08-16 ユーザ方針)= config で解決させる形を厚めに。
# asym_up だけは「なぜ UP か」を問う read を最厚に維持する(記述式で配点40の主役)。
FORM_W = {"addr_mismatch": {"select2": 65, "dbgconf": 35},
          "ebgp_multihop": {"select2": 70, "dbgconf": 30},
          "asym_up": {"read": 45, "fix": 30, "dbgconf": 25}}

# dbgconf / read で置く前提文(BL-123 の「示されているものが全て」パターン)。
# 未提示前提の補完余地を封じ、一意性を確実にする。
PREMISE = ("なお、両ルータの BGP のネイバーに関する構成について判断できることは、"
           "示されている出力が全てです。示されている以外の障害は、存在しません。")


def kind_forms(kind):
    """その variant が取り得る出題形(--forms の絞り込みに使う)。"""
    return set(MCQ_FORMS[kind]) | {"essay"}


def forms_for(d):
    return sorted(kind_forms(d["variant"]))


def pick_form(d, rnd, allowed=None):
    """出題形の抽選。allowed(--forms)指定時はその中から比率を保って選ぶ。
    essay は明示指定の時だけ返す(通常抽選には出さない)。"""
    v = d["variant"]
    if allowed and set(allowed) == {"essay"}:
        return "essay"
    pool = [f for f in MCQ_FORMS[v] if not allowed or f in allowed]
    if not pool:
        raise ValueError(f"bgpdbg: variant={v} は forms={allowed} を持たない")
    weights = [FORM_W[v][f] for f in pool]
    x = rnd.random() * sum(weights)
    for f, w in zip(pool, weights):
        x -= w
        if x < 0:
            return f
    return pool[-1]


# ---------------------------------------------------------------- 構成モデル
def actual_cfgs(d):
    """variant ごとの実像(debug を生じさせている構成)。"""
    v = d["variant"]
    if v == "addr_mismatch":
        return {"A": {"nbr": "lo", "upd": True, "mh": False},
                "B": {"nbr": "phy", "upd": False, "mh": False}}
    if v == "ebgp_multihop":
        return {"A": {"nbr": "lo", "upd": True, "mh": False},
                "B": {"nbr": "lo", "upd": True, "mh": False}}
    return {"A": {"nbr": "lo", "upd": True, "mh": False},
            "B": {"nbr": "lo", "upd": False, "mh": False}}


def _accept(opener, peer, ebgp):
    """opener の active open の帰結。実機根拠= poc/bgpdbg/README.md。
    no_route= 自側の直接接続検査で TCP 以前に失敗(発見3) /
    refused = TCP RST(相手の neighbor 文に送信元が不一致・発見2)または
              相手側の multihop 検査(★片側だけの multihop では確立しない)。"""
    src = "lo" if opener["upd"] else "phy"
    if ebgp and opener["nbr"] == "lo" and not opener["mh"]:
        return "no_route"
    if peer["nbr"] != src:
        return "refused"
    if ebgp and src == "lo" and not peer["mh"]:
        return "refused"
    return "accepted"


def session(cfgs, ebgp):
    """(確立するか, A発の帰結, B発の帰結)。確立= どちらか一方の open が受理
    されること(発見1の接続レース)。"""
    ra = _accept(cfgs["A"], cfgs["B"], ebgp)
    rb = _accept(cfgs["B"], cfgs["A"], ebgp)
    return ("accepted" in (ra, rb)), ra, rb


def visible(cfgs, ebgp):
    """両側 debug の可視指紋 {側: (宛先種別, 送信元種別 or None, 帰結)}。
    dbgconf の一意性判定の土台。no_route は送信元が観測できない(None)。"""
    up, ra, rb = session(cfgs, ebgp)
    out = {}
    for side, res in (("A", ra), ("B", rb)):
        cfg = cfgs[side]
        src = "lo" if cfg["upd"] else "phy"
        if res == "no_route":
            out[side] = (cfg["nbr"], None, "no_route")
        elif res == "accepted":
            out[side] = (cfg["nbr"], src, "up_clean")
        else:
            out[side] = (cfg["nbr"], src, "refused_up" if up else "refused_idle")
    return out


def _peer_addr(d, side, kind):
    """side("A"/"B") の neighbor 文が指す対向アドレス。"""
    peer = "b" if side == "A" else "a"
    return d[("lo_" if kind == "lo" else "ip_") + peer]


def cfg_lines(d, side, cfg, ebgp):
    """1台分の router bgp 抜粋(dbgconf 選択肢の部品)。"""
    own_as = d["as_a"] if side == "A" else d["as_b"]
    peer_as = d["as_b"] if side == "A" else d["as_a"]
    tgt = _peer_addr(d, side, cfg["nbr"])
    lines = [f"router bgp {own_as}",
             f" neighbor {tgt} remote-as {peer_as}"]
    if cfg["upd"]:
        lines.append(f" neighbor {tgt} update-source Loopback0")
    if ebgp and cfg["mh"]:
        lines.append(f" neighbor {tgt} ebgp-multihop 2")
    return lines


def cfg_pair_lines(d, cfgs):
    ebgp = d["variant"] == "ebgp_multihop"
    return ([f"! {d['A']}"] + cfg_lines(d, "A", cfgs["A"], ebgp)
            + ["!", f"! {d['B']}"] + cfg_lines(d, "B", cfgs["B"], ebgp))


def _cfg_desc(d, cfgs):
    """選択肢の散文ラベル(解答 md での参照用)。"""
    ebgp = d["variant"] == "ebgp_multihop"
    parts = []
    for side in ("A", "B"):
        c = cfgs[side]
        p = [("ループバック宛" if c["nbr"] == "lo" else "物理宛"),
             ("update-source あり" if c["upd"] else "update-source なし")]
        if ebgp:
            p.append("multihop あり" if c["mh"] else "multihop なし")
        parts.append(f"{d[side]}= " + "・".join(p))
    return " / ".join(parts)


# ---------------------------------------------------------------- dbgconf 形
def _dbgconf_pool(d):
    """錯乱肢= 描き直すと**可視出力が変わる**近傍構成だけを置く(aaa dbgconf 前例)。
    ★ebgp_multihop では update-source 軸を動かさない(可視でない軸の変更は
    同一出力の構成を生み、二重正解になる)。"""
    A, B = d["A"], d["B"]
    v = d["variant"]
    if v == "addr_mismatch":
        return [
            ({"A": {"nbr": "lo", "upd": True, "mh": False},
              "B": {"nbr": "lo", "upd": True, "mh": False}},
             "この構成であれば両側の open が受理されて確立し、拒否のメッセージは"
             "現れない。"),
            ({"A": {"nbr": "lo", "upd": True, "mh": False},
              "B": {"nbr": "lo", "upd": False, "mh": False}},
             f"片側の update-source 欠けであれば {A} 発の接続が受理されて "
             f"Established になる(両側 Idle にはならない)。また {B} の行頭の"
             f"宛先が {d['lo_a']} になるはずである。"),
            ({"A": {"nbr": "lo", "upd": False, "mh": False},
              "B": {"nbr": "phy", "upd": False, "mh": False}},
             f"{A} の open active の local address が {d['ip_a']}(物理)になる"
             f"はずで、示されている {d['lo_a']} と一致しない。"),
            ({"A": {"nbr": "phy", "upd": False, "mh": False},
              "B": {"nbr": "phy", "upd": False, "mh": False}},
             "物理宛の対称構成であれば確立する。示されている宛先(ループバック)"
             "とも一致しない。"),
        ]
    if v == "ebgp_multihop":
        return [
            ({"A": {"nbr": "lo", "upd": True, "mh": True},
              "B": {"nbr": "lo", "upd": True, "mh": True}},
             "この構成であれば直接接続検査を通過して確立し、失敗のメッセージは"
             "現れない。"),
            ({"A": {"nbr": "phy", "upd": False, "mh": False},
              "B": {"nbr": "phy", "upd": False, "mh": False}},
             "物理宛の eBGP であれば直接接続の検査を満たして確立する。宛先の"
             "表示も物理になるはずである。"),
            ({"A": {"nbr": "phy", "upd": False, "mh": False},
              "B": {"nbr": "lo", "upd": True, "mh": False}},
             f"{A} 側の宛先・送信元が物理となり、示されている {A} 側の出力"
             "(ループバック宛・no route to peer)と一致しない。"),
            ({"A": {"nbr": "lo", "upd": True, "mh": False},
              "B": {"nbr": "phy", "upd": False, "mh": False}},
             f"{B} 側の宛先・送信元が物理となり、示されている {B} 側の出力"
             "(ループバック宛・no route to peer)と一致しない。"),
        ]
    return [
        ({"A": {"nbr": "lo", "upd": True, "mh": False},
          "B": {"nbr": "lo", "upd": True, "mh": False}},
         "対称な構成であれば両側の open が受理され、拒否の行は現れない。"),
        ({"A": {"nbr": "lo", "upd": False, "mh": False},
          "B": {"nbr": "lo", "upd": True, "mh": False}},
         f"鏡像の構成。拒否が現れるのは {A} の側になり、示されている出力と"
         "左右が逆である。"),
        ({"A": {"nbr": "lo", "upd": True, "mh": False},
          "B": {"nbr": "phy", "upd": False, "mh": False}},
         f"宛先が食い違う構成であれば両側とも拒否されて Idle となり、"
         f"ADJCHANGE Up は現れない。また {B} の行頭の宛先が物理になる。"),
        ({"A": {"nbr": "lo", "upd": False, "mh": False},
          "B": {"nbr": "lo", "upd": False, "mh": False}},
         "両側とも送信元が物理となり、どちらの接続も受理されず Idle となる。"),
    ]


def build_choices_dbgconf(d, rnd):
    """逆問題(単一選択・5択)。正解= 実像。錯乱肢= 可視指紋が異なる近傍構成。"""
    ebgp = d["variant"] == "ebgp_multihop"
    act = actual_cfgs(d)
    vis0 = visible(act, ebgp)
    c = [(_cfg_desc(d, act), True,
          "各行頭の宛先・open active の local address・帰結のすべてが、"
          "示されている出力と一致する。", cfg_pair_lines(d, act))]
    for cfgs, why in _dbgconf_pool(d):
        if visible(cfgs, ebgp) == vis0:
            raise ValueError("bgpdbg dbgconf: 錯乱肢が実像と同一の可視指紋")
        c.append((_cfg_desc(d, cfgs), False, why, cfg_pair_lines(d, cfgs)))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---------------------------------------------------------------- fix 系
def _apply(cfgs, deltas):
    """選択の組を構成へ適用。★neighbor の付け替えは update-source / multihop を
    道連れにリセットする(no neighbor で行ごと消えるため)。upd/mh の行は
    ループバック宛の neighbor 文を名指ししており、その neighbor が現存しない
    場合は投入エラー= 無効(no-op)としてモデル化する。"""
    import copy
    c = copy.deepcopy(cfgs)
    for dl in deltas:
        if "nbr" in dl:
            c[dl["side"]].update(nbr=dl["nbr"], upd=False, mh=False)
    for dl in deltas:
        for k in ("upd", "mh"):
            if k in dl and c[dl["side"]]["nbr"] == "lo":
                c[dl["side"]][k] = dl[k]
    return c


def _fix_ok(d, cfgs):
    """要件を満たすか。①確立 ②Lo間ピアリング設計の維持
    ③(addr_mismatch/asym_up) 確立が一方の側の接続開始に依存しない。"""
    ebgp = d["variant"] == "ebgp_multihop"
    up, ra, rb = session(cfgs, ebgp)
    if not up:
        return False
    if not (cfgs["A"]["nbr"] == "lo" == cfgs["B"]["nbr"]):
        return False
    if d["variant"] != "ebgp_multihop" and not (ra == rb == "accepted"):
        return False
    return True


def _fix_menu(d):
    """(text, deltas, why, cli) の一覧。正解フラグは機械判定(手書きしない)。
    ★鏡像(直す側が逆)の錯乱肢は1肢だけ(2肢置くと組で直る二重正解が生まれる)。"""
    A, B = d["A"], d["B"]
    v = d["variant"]
    as_a, as_b = d["as_a"], d["as_b"]
    if v == "addr_mismatch":
        return [
            (f"{B} の neighbor 文の宛先を、{A} のループバック({d['lo_a']})へ"
             "是正する",
             [{"side": "B", "nbr": "lo"}],
             f"{B} の neighbor 文が {A} の送信元(= {d['lo_a']})と一致し、"
             f"{A} 発の接続が受理されるようになる(2手の一方。これだけでは "
             f"{B} 発の接続が拒否されたままで、確立が {A} からの開始に依存する)。",
             [f"! {B}", f"router bgp {as_b}",
              f" no neighbor {d['ip_a']} remote-as {as_a}",
              f" neighbor {d['lo_a']} remote-as {as_a}"]),
            (f"{B} に、{d['lo_a']} 宛の update-source Loopback0 を設定する",
             [{"side": "B", "upd": True}],
             f"{B} 発の接続の送信元が {d['lo_b']} となり、{A} の neighbor 文に"
             "一致する(2手の一方。宛先の是正と併せて要件を満たす)。",
             [f"! {B}", f"router bgp {as_b}",
              f" neighbor {d['lo_a']} update-source Loopback0"]),
            (f"{A} の neighbor 文の宛先を、{B} の物理アドレス({d['ip_b']})へ"
             "付け替える",
             [{"side": "A", "nbr": "phy"}],
             "ピアは確立し得るが、ループバック・インターフェイスの間で"
             "ピアリングを行う設計の維持、という要件に違反する。",
             [f"! {A}", f"router bgp {as_a}",
              f" no neighbor {d['lo_b']} remote-as {as_b}",
              f" neighbor {d['ip_b']} remote-as {as_b}"]),
            (f"{B} に、{d['lo_a']} への静的ルートを設定する",
             [],
             "到達性の障害ではない(ping は成功しており、拒否は TCP RST で"
             "ある)。経路を追加しても接続の拒否は変わらない。",
             [f"! {B}", f"ip route {d['lo_a']} 255.255.255.255 {d['ip_a']}"]),
            (f"{A} に、{d['lo_b']} 宛の ebgp-multihop を設定する",
             [{"side": "A", "mh": True}],
             "両ルータは同一 AS の iBGP ピアであり、eBGP の直接接続の検査は"
             "行われない(事象と無関係)。",
             [f"! {A}", f"router bgp {as_a}",
              f" neighbor {d['lo_b']} ebgp-multihop 2"]),
            ("両ルータで、clear ip bgp * を実行する",
             [],
             "構成が変わらない限り、接続の試行は同じ帰結(拒否)に戻る。",
             [f"! {A} と {B} の両方で", "clear ip bgp *"]),
        ]
    if v == "ebgp_multihop":
        return [
            (f"{A} に、{d['lo_b']} 宛の ebgp-multihop を設定する",
             [{"side": "A", "mh": True}],
             f"{A} 側の直接接続の検査が解除される(2手の一方。★片側だけでは、"
             "対向側の検査が残るため確立しない)。",
             [f"! {A}", f"router bgp {as_a}",
              f" neighbor {d['lo_b']} ebgp-multihop 2"]),
            (f"{B} に、{d['lo_a']} 宛の ebgp-multihop を設定する",
             [{"side": "B", "mh": True}],
             f"{B} 側の直接接続の検査が解除される(2手の一方)。",
             [f"! {B}", f"router bgp {as_b}",
              f" neighbor {d['lo_a']} ebgp-multihop 2"]),
            (f"{A} に、{d['lo_b']} への静的ルートを設定する",
             [],
             "経路は既に存在している(経路表の提示のとおり)。このメッセージは"
             "経路の有無ではなく、eBGP の直接接続の検査の失敗を示す。また、"
             "到達性を提供している構成の変更は要件に違反する。",
             [f"! {A}", f"ip route {d['lo_b']} 255.255.255.255 {d['ip_b']}"]),
            (f"{B} に、{d['lo_a']} 宛の update-source Loopback0 を設定する",
             [{"side": "B", "upd": True}],
             "失敗は TCP の接続よりも前(直接接続の検査)で起きており、"
             "送信元アドレスの構成では帰結が変わらない。",
             [f"! {B}", f"router bgp {as_b}",
              f" neighbor {d['lo_a']} update-source Loopback0"]),
            (f"{A} の neighbor 文の宛先を、{B} の物理アドレス({d['ip_b']})へ"
             "付け替える",
             [{"side": "A", "nbr": "phy"}],
             "設計の維持の要件に違反するうえ、単独では対向側の neighbor 文との"
             "不一致が残り、確立しない。",
             [f"! {A}", f"router bgp {as_a}",
              f" no neighbor {d['lo_b']} remote-as {as_b}",
              f" neighbor {d['ip_b']} remote-as {as_b}"]),
            ("両ルータで、clear ip bgp * を実行する",
             [],
             "構成が変わらない限り、直接接続の検査の失敗は繰り返される。",
             [f"! {A} と {B} の両方で", "clear ip bgp *"]),
        ]
    return [
        (f"{B} に、{d['lo_a']} 宛の update-source Loopback0 を設定する",
         [{"side": "B", "upd": True}],
         f"{B} 発の接続の送信元が {d['lo_b']} となって {A} に受理されるように"
         "なり、どちらの側から開始しても確立する(非対称の解消)。",
         [f"! {B}", f"router bgp {as_b}",
          f" neighbor {d['lo_a']} update-source Loopback0"]),
        (f"{A} から、update-source Loopback0 を削除して両側を揃える",
         [{"side": "A", "upd": False}],
         "対称にはなるが、両側の送信元が物理アドレスとなり、どちら発の接続も"
         "相手の neighbor 文(ループバック宛)に一致しなくなる= 現在確立して"
         "いるピアまで失われる。",
         [f"! {A}", f"router bgp {as_a}",
          f" no neighbor {d['lo_b']} update-source Loopback0"]),
        ("両ルータの neighbor 文を、物理アドレス宛へ付け替える",
         [{"side": "A", "nbr": "phy"}, {"side": "B", "nbr": "phy"}],
         "確立はするが、ループバック・インターフェイスの間でピアリングを行う"
         "設計の維持、という要件に違反する。",
         [f"! {A}", f"router bgp {as_a}",
          f" no neighbor {d['lo_b']} remote-as {as_b}",
          f" neighbor {d['ip_b']} remote-as {as_b}",
          f"! {B}", f"router bgp {as_b}",
          f" no neighbor {d['lo_a']} remote-as {as_a}",
          f" neighbor {d['ip_a']} remote-as {as_a}"]),
        (f"{B} に、{d['lo_a']} への静的ルートを設定する",
         [],
         "到達性の障害ではない(拒否は TCP RST であり、経路・IF は生きている)。",
         [f"! {B}", f"ip route {d['lo_a']} 255.255.255.255 {d['ip_a']}"]),
        ("両ルータで、clear ip bgp * を実行する",
         [],
         "接続レースのやり直しに過ぎず、非対称(一方の側の開始への依存)は残る。",
         [f"! {A} と {B} の両方で", "clear ip bgp *"]),
    ]


def build_choices_fix(d, rnd):
    """是正形。addr_mismatch / ebgp_multihop= 2つ選択(select2)・asym_up= 単一。
    正解の組は列挙総当たりで機械判定し、一意でなければ ValueError。"""
    import itertools
    menu = _fix_menu(d)
    base = actual_cfgs(d)
    k = 1 if d["variant"] == "asym_up" else 2
    wins = [combo for combo in itertools.combinations(range(len(menu)), k)
            if _fix_ok(d, _apply(base, sum((menu[i][1] for i in combo), [])))]
    if len(wins) != 1:
        raise ValueError(f"bgpdbg fix({d['variant']}): 正解組が一意でない: {wins}")
    okset = set(wins[0])
    c = [(t, i in okset, w, cli) for i, (t, _dl, w, cli) in enumerate(menu)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---------------------------------------------------------------- read 形
def build_choices_read(d, rnd):
    """asym_up 専用(複数選択・6択・正解2)。事実文の真偽はモデルの帰結
    (session/visible)と提示物(ping・debug 行)に対応させる。"""
    if d["variant"] != "asym_up":
        raise ValueError("bgpdbg read: asym_up 専用")
    A, B = d["A"], d["B"]
    true_pool = [
        (f"確立されている TCP 接続は、{A} が開始したものである"
         f"(送信元 {d['lo_a']})",
         f"{A} の open active(local address {d['lo_a']})は {B} の "
         f"neighbor {d['lo_a']} に一致して受理される。{B} 発は拒否されて"
         "いるため、生き残る接続は {} 発のみ。".format(A)),
        (f"{B} が開始する接続(送信元 {d['ip_b']})は、{A} によって拒否され"
         "続けている",
         f"{B} 側の open failed: Connection refused がそれを示す。{A} は "
         f"{d['ip_b']} を neighbor として持たないため TCP RST を返す。"),
        (f"{B} の neighbor 文には、update-source の構成が伴っていない",
         f"{B} の open active の local address が {d['ip_b']}(物理)である"
         "ことから確定する。"),
    ]
    false_pool = [
        ("両ルータの BGP のネイバーの構成は、対称である",
         f"local address の行が {d['lo_a']}(ループバック)と {d['ip_b']}"
         "(物理)で食い違っており、非対称であることが確定する。"),
        (f"{d['lo_a']} への経路が {B} に存在しないため、{B} の接続の試行が"
         "失敗している",
         "ping(送信元・宛先ともループバック)の成功が往復の到達性を示す。"
         "拒否は TCP RST であり、経路の欠落では起こらない。"),
        (f"{A} の側の update-source の構成が、欠落している",
         f"{A} の open active の local address は {d['lo_a']} であり、"
         "Loopback0 を送信元とする構成が存在する。"),
        (f"ピアは、{B} が開始した接続の上で、確立されている",
         f"{B} 発の接続は拒否され続けている。ADJCHANGE Up は {A} 発の接続が"
         "受理されたことによる。"),
    ]
    c = ([(t, True, w) for t, w in rnd.sample(true_pool, 2)]
         + [(t, False, w) for t, w in false_pool])
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---------------------------------------------------------------- 要件
def requirements(d, form=None):
    """fix / select2 の一意性の担い手。リーンに保つ(BL-121 の方針)。"""
    v = d["variant"]
    if v == "addr_mismatch":
        return ["両ルータの間で、BGP のピアが確立されること。",
                "ループバック・インターフェイスの間でピアリングを行う設計が、"
                "維持されること。",
                "ピアの確立が、いずれか一方の側からの接続の開始に、"
                "依存しないこと。"]
    if v == "ebgp_multihop":
        return ["両ルータの間で、BGP のピアが確立されること。",
                "ループバック・インターフェイスの間でピアリングを行う設計が、"
                "維持されること。",
                "対向のループバックへの到達性を提供している構成は、"
                "変更しないこと。"]
    return ["現在確立されているピアが、失われないこと。",
            "ループバック・インターフェイスの間でピアリングを行う設計が、"
            "維持されること。",
            "ピアの確立が、いずれか一方の側からの接続の開始に、"
            "依存しないこと。"]


# ---------------------------------------------------------------- selftest
def selftest(n=200):
    """モデル不変条件(PoC の実測)と選択肢の一意性を機械検証する。"""
    import random as _r
    checked = 0
    for seed in range(n):
        for v in VARIANTS:
            d = draw(_r.Random(20000 + seed), variant=v)
            ebgp = v == "ebgp_multihop"
            up, ra, rb = session(actual_cfgs(d), ebgp)
            # 実測: asym_up だけ確立(発見1)・ebgp は両側 no_route(発見3)
            assert up == (v == "asym_up"), (v, up)
            if ebgp:
                assert ra == rb == "no_route"
            for form in MCQ_FORMS[v]:
                rnd = _r.Random(30000 + seed * 7 + hash(form) % 1000)
                ch = (build_choices_dbgconf(d, rnd) if form == "dbgconf"
                      else build_choices_read(d, rnd) if form == "read"
                      else build_choices_fix(d, rnd))
                want = 2 if form in ("select2", "read") else 1
                n_ok = sum(1 for c in ch if c[1])
                assert n_ok == want, (v, form, n_ok)
                texts = [c[0] for c in ch]
                assert len(set(texts)) == len(texts), (v, form, "重複肢")
                assert all(c[2] for c in ch if not c[1]), (v, form, "why欠落")
                checked += 1
    print(f"bgpdbg selftest OK ({checked} 通り)")


if __name__ == "__main__":
    selftest()
