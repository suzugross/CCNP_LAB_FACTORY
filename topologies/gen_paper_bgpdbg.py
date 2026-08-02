#!/usr/bin/env python3
"""BGP ループバック・ピアリング debug 読解（記述式）紙面問題 (BL-085)。

ユーザ発案: 「debug メッセージからコンフィグを想像し、修正案まで提出させる」。
選択肢は無く、**記述式**(採点は Claude がルーブリックで実施)。

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
def _ts(rnd, base=0):
    h, m = 9 + base // 60, base % 60
    return f"*Aug  2 {h:02d}:{m:02d}:{rnd.randint(10,59)}.{rnd.randint(100,999)}"


def debug_blocks(d, rnd):
    A, B = d["A"], d["B"]
    v = d["variant"]
    if v == "ebgp_multihop":
        a_lines = [f"{_ts(rnd, i)}: BGP: {d['lo_b']} Active open failed - no route to "
                   f"peer, open active delayed {rnd.choice([6144, 8192, 9216, 12288])}ms "
                   "(35000ms max, 60% jitter)" for i in range(4)]
        b_lines = [f"{_ts(rnd, i)}: BGP: {d['lo_a']} Active open failed - no route to "
                   f"peer, open active delayed {rnd.choice([6144, 9216, 13312])}ms "
                   "(35000ms max, 60% jitter)" for i in range(3)]
    elif v == "asym_up":
        a_lines = [f"{_ts(rnd, 0)}: BGP: {d['lo_b']} active went from Idle to Active",
                   f"{_ts(rnd, 0)}: BGP: {d['lo_b']} open active, local address {d['lo_a']}",
                   f"{_ts(rnd, 1)}: %BGP-5-ADJCHANGE: neighbor {d['lo_b']} Up "]
        b_lines = [f"{_ts(rnd, 0)}: BGP: {d['lo_a']} active went from Idle to Active",
                   f"{_ts(rnd, 0)}: BGP: {d['lo_a']} open active, local address {d['ip_b']}",
                   f"{_ts(rnd, 0)}: BGP: {d['lo_a']} open failed: Connection refused by "
                   "remote host",
                   f"{_ts(rnd, 0)}: BGP: {d['lo_a']} Active open failed - tcb is not "
                   "available, open active delayed 12288ms (35000ms max, 60% jitter)",
                   f"{_ts(rnd, 1)}: %BGP-5-ADJCHANGE: neighbor {d['lo_a']} Up "]
    else:   # addr_mismatch
        a_lines = [f"{_ts(rnd, 0)}: BGP: {d['lo_b']} active went from Idle to Active",
                   f"{_ts(rnd, 0)}: BGP: {d['lo_b']} open active, local address {d['lo_a']}",
                   f"{_ts(rnd, 0)}: BGP: {d['lo_b']} open failed: Connection refused by "
                   "remote host",
                   f"{_ts(rnd, 0)}: BGP: {d['lo_b']} Active open failed - tcb is not "
                   "available, open active delayed 14336ms (35000ms max, 60% jitter)",
                   f"{_ts(rnd, 0)}: BGP: ses global {d['lo_b']} (0x7352B1A93C78:0) act "
                   "Reset (Active open failed).",
                   f"{_ts(rnd, 0)}: BGP: {d['lo_b']} active went from Active to Idle"]
        b_lines = [f"{_ts(rnd, 1)}: BGP: {d['ip_a']} active went from Idle to Active",
                   f"{_ts(rnd, 1)}: BGP: {d['ip_a']} open active, local address {d['ip_b']}",
                   f"{_ts(rnd, 1)}: BGP: {d['ip_a']} open failed: Connection refused by "
                   "remote host",
                   f"{_ts(rnd, 1)}: BGP: {d['ip_a']} Active open failed - tcb is not "
                   "available, open active delayed 12288ms (35000ms max, 60% jitter)",
                   f"{_ts(rnd, 1)}: BGP: ses global {d['ip_a']} (0x72F53161A0C0:0) act "
                   "Reset (Active open failed).",
                   f"{_ts(rnd, 1)}: BGP: {d['ip_a']} active went from Active to Idle"]
    return a_lines, b_lines


def summary_block(d):
    """show ip bgp summary(状態の裏取り)。"""
    A, B = d["A"], d["B"]
    if d["variant"] == "asym_up":
        pa = (f"{d['lo_b']:<16}4{d['as_b']:>12}      12      13        1    0    0 "
              "00:08:50        0")
        pb = (f"{d['lo_a']:<16}4{d['as_a']:>12}      13      13        1    0    0 "
              "00:09:07        0")
    elif d["variant"] == "ebgp_multihop":
        pa = f"{d['lo_b']:<16}4{d['as_b']:>12}       0       0        1    0    0 never    Idle"
        pb = f"{d['lo_a']:<16}4{d['as_a']:>12}       0       0        1    0    0 never    Idle"
    else:
        pa = (f"{d['lo_b']:<16}4{d['as_b']:>12}       0       0        1    0    0 "
              "00:02:37 Idle")
        pb = (f"{d['ip_a']:<16}4{d['as_a']:>12}       0       0        1    0    0 "
              "never    Idle")
    head = ("Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ "
            "Up/Down  State/PfxRcd")
    return (f"{A}# show ip bgp summary | begin Neighbor\n{head}\n{pa}",
            f"{B}# show ip bgp summary | begin Neighbor\n{head}\n{pb}")


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
