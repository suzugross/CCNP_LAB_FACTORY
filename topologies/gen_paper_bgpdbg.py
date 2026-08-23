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

★BL-136(b)(2026-08-23): 変種3つでは反復が体感に出る(ebgp_multihop 4連続の
ユーザ指摘)ため4種追加。素材= poc/bgpdbg/results-probe2.md(IOL 実測 b1/b1b/b2/b3):
  pw_mismatch    (難4) MD5 password 不一致。両側に %TCP-6-BADAUTH: **Invalid** MD5
                       digest が周期出力+ Connection timed out で Idle
  pw_oneside     (難4) 片側だけ password。持つ側にだけ %TCP-6-BADAUTH: **No** MD5
                       digest(両方向)・持たない側は BADAUTH 無し= 非対称が決め手
  remote_as_wrong(難3) eBGP 物理ピアで remote-as 誤り。誤設定側= `bad OPEN,
                       remote AS is X, expected Y`+NOTIFICATION **sent** 2/2、
                       健全側= NOTIFICATION **received**(sent/received で犯人が割れる)
  nbr_shutdown   (難3) neighbor shutdown 残骸。残骸側= debug 無音+summary
                       `Idle (Admin)`(★この変種のみ summary を提示= 唯一の証拠)、
                       対向= Connection refused 周期
新4種は essay 非対応・既存の nbr/upd/mh 構成格子に載せず変種別ブランチで持つ。
"""
import random

VARIANTS = ["addr_mismatch", "ebgp_multihop", "asym_up",
            "pw_mismatch", "pw_oneside", "remote_as_wrong", "nbr_shutdown"]
LEGACY = {"addr_mismatch", "ebgp_multihop", "asym_up"}
DIFF = {"addr_mismatch": 4, "ebgp_multihop": 4, "asym_up": 5,
        "pw_mismatch": 4, "pw_oneside": 4, "remote_as_wrong": 3,
        "nbr_shutdown": 3}


def draw(rnd, variant=None):
    d = {"shape": "bgpdbg"}
    d["variant"] = variant or rnd.choice(VARIANTS)
    a, b = rnd.sample(range(1, 99), 2)
    d["lo_a"], d["lo_b"] = f"{a}.{a}.{a}.{a}", f"{b}.{b}.{b}.{b}"
    o = rnd.randint(0, 240)
    d["link"] = f"10.{rnd.randint(0, 250)}.{o}"
    d["ip_a"], d["ip_b"] = f"{d['link']}.1", f"{d['link']}.2"
    if d["variant"] in ("ebgp_multihop", "remote_as_wrong"):
        d["as_a"], d["as_b"] = rnd.randint(64512, 65100), rnd.randint(65101, 65534)
    else:
        d["as_a"] = d["as_b"] = rnd.randint(64512, 65534)
    names = [f"RT{i:02d}" for i in range(1, 3)]
    rnd.shuffle(names)
    d["A"], d["B"] = names
    d["igp"] = rnd.choice([f"OSPF {rnd.randint(1, 99)} ", "スタティック・ルート"])
    # ---- BL-136(b) 追加変種の固有値 ----
    d["culprit"] = rnd.choice(["A", "B"])   # 誤設定/残骸を持つ側(legacy では未使用)
    d["key"] = f"{rnd.choice(['WAN', 'PEER', 'CORE'])}-KEY{rnd.randint(11, 99)}"
    d["key2"] = f"OLD-KEY{rnd.randint(11, 99)}"   # pw_mismatch の非準拠側の旧キー
    if d["variant"] == "remote_as_wrong":
        # 誤って設定されている remote-as(実在しない第3の AS)
        wrong = rnd.randint(64512, 65534)
        while wrong in (d["as_a"], d["as_b"]):
            wrong = rnd.randint(64512, 65534)
        d["as_wrong"] = wrong
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


def _dbg_pw_mismatch(d, rnd):
    """b1 実測: 両側で Invalid MD5 digest が再送間隔(1,2,4,8s)で並び、
    30秒後に Connection timed out で Idle へ落ちる。"""
    out = []
    for side, own, peer in (("A", d["lo_a"], d["lo_b"]),
                            ("B", d["lo_b"], d["lo_a"])):
        t = _Clock(rnd, 0 if side == "A" else 1)
        port = rnd.randint(20000, 59999)
        lines = [f"{t()}: BGP: {peer} active went from Idle to Active",
                 f"{t()}: BGP: {peer} open active, local address {own}"]
        for gap in (1, 2, 4, 8):
            lines.append(f"{t(gap)}: %TCP-6-BADAUTH: Invalid MD5 digest from "
                         f"{peer}({port}) to {own}(179) tableid - 0")
        lines += [f"{t(15)}: BGP: {peer} open failed: Connection timed out; "
                  "remote host not responding",
                  f"{t(0)}: BGP: {peer} Active open failed - tcb is not "
                  f"available, open active delayed "
                  f"{rnd.choice([8192, 10240, 13312])}ms (35000ms max, 60% jitter)",
                  f"{t(0)}: BGP: {peer} active went from Active to Idle"]
        out.append(lines)
    return out[0], out[1]


def _dbg_pw_oneside(d, rnd):
    """b1b 実測: ★BADAUTH(No MD5 digest)を出すのは password を**持つ側だけ**。
    両方向(相手の 179 発と、相手のエフェメラル発)が交互に並ぶ。
    持たない側は BADAUTH 無しで open が静かに失敗する。"""
    culp = d["culprit"]                     # password が**無い**側
    keep = "B" if culp == "A" else "A"
    lo = {"A": d["lo_a"], "B": d["lo_b"]}
    tk = _Clock(rnd, 0)
    e1, e2 = rnd.randint(20000, 39999), rnd.randint(40000, 59999)
    keep_lines = []
    for gap in (0, 2, 4, 2, 8):
        keep_lines.append(f"{tk(gap)}: %TCP-6-BADAUTH: No MD5 digest from "
                          f"{lo[culp]}(179) to {lo[keep]}({e1}) tableid - 0")
        keep_lines.append(f"{tk(0)}: %TCP-6-BADAUTH: No MD5 digest from "
                          f"{lo[culp]}({e2}) to {lo[keep]}(179) tableid - 0")
    keep_lines += [f"{tk(14)}: BGP: ses global {lo[culp]} (0x7161E623E350:0) act "
                   "Reset (Active open failed).",
                   f"{tk(0)}: BGP: {lo[culp]} active went from Active to Idle"]
    tc = _Clock(rnd, 1)
    culp_lines = [f"{tc()}: BGP: {lo[keep]} active went from Idle to Active",
                  f"{tc()}: BGP: {lo[keep]} open active, local address {lo[culp]}",
                  f"{tc(30)}: BGP: ses global {lo[keep]} (0x70F9F020C450:0) act "
                  "Reset (Active open failed).",
                  f"{tc(0)}: BGP: {lo[keep]} active went from Active to Idle",
                  f"{tc(0)}: BGP: nbr global {lo[keep]} Active open failed - "
                  "open timer running"]
    a_lines = keep_lines if keep == "A" else culp_lines
    b_lines = keep_lines if keep == "B" else culp_lines
    return a_lines, b_lines


def _dbg_remote_as(d, rnd):
    """b2 実測: 誤設定側= bad OPEN(actual/expected 両方の値が出る)+
    NOTIFICATION **sent** 2/2、健全側= OpenConfirm まで進んで **received**。
    2 bytes のペイロードは相手 AS の16進(実測 FDEA=65002)。"""
    culp = d["culprit"]
    ip = {"A": d["ip_a"], "B": d["ip_b"]}
    asn = {"A": d["as_a"], "B": d["as_b"]}
    # 実測の ID 表示は RID の16進(先頭ゼロ落ち): 2.2.2.2 → "2020202"
    rid = {s: f"{int(d['lo_' + s.lower()].split('.')[0]) * 0x01010101:X}"
           for s in ("A", "B")}
    keep = "B" if culp == "A" else "A"
    peer_of = {"A": "B", "B": "A"}
    actual = asn[peer_of[culp]]             # 相手の実 AS
    payload = f"{actual:04X}"
    tc = _Clock(rnd, 0)
    culp_lines = [
        f"{tc()}: BGP: {ip[keep]} passive rcv OPEN, version 4, holdtime 180 seconds",
        f"{tc(0)}: BGP: {ip[keep]} passive OPEN has 4-byte ASN CAP for: {actual}",
        f"{tc(0)}: BGP: {ip[keep]} passive bad OPEN, remote AS is {actual}, "
        f"expected {d['as_wrong']}  ",
        f"{tc(0)}: BGP: {ip[keep]} passive went from Connect to Closing",
        f"{tc(0)}: %BGP-3-NOTIFICATION: sent to neighbor {ip[keep]} passive 2/2 "
        f"(peer in wrong AS) 2 bytes {payload}",
        f"{tc(4)}: %BGP-5-NBR_RESET: Neighbor {ip[keep]} passive reset "
        "(BGP Notification sent)",
        f"{tc(0)}: BGP: {ip[keep]} passive went from Closing to Idle",
        f"{tc(0)}: %BGP-5-ADJCHANGE: neighbor {ip[keep]} passive Down "
        "BGP Notification sent"]
    tk = _Clock(rnd, 1)
    keep_lines = [
        f"{tk()}: BGP: {ip[culp]} passive went from Connect to OpenSent",
        f"{tk(0)}: BGP: {ip[culp]} passive sending OPEN, version 4, "
        f"my as: {asn[keep]}, holdtime 180 seconds, ID {rid[keep]}",
        f"{tk(0)}: BGP: {ip[culp]} passive went from OpenSent to OpenConfirm",
        f"{tk(0)}: %BGP-3-NOTIFICATION: received from neighbor {ip[culp]} "
        f"passive 2/2 (peer in wrong AS) 2 bytes {payload}",
        f"{tk(0)}: %BGP-5-NBR_RESET: Neighbor {ip[culp]} passive reset "
        "(BGP Notification received)",
        f"{tk(0)}: BGP: {ip[culp]} passive went from OpenConfirm to Closing",
        f"{tk(0)}: %BGP-5-ADJCHANGE: neighbor {ip[culp]} passive Down "
        "BGP Notification received"]
    a_lines = culp_lines if culp == "A" else keep_lines
    b_lines = culp_lines if culp == "B" else keep_lines
    return a_lines, b_lines


def _dbg_shutdown(d, rnd):
    """b3 実測: 残骸(shutdown)側は debug を有効にしても**一切の行が出ない**
    (FSM が動かない)。対向は Connection refused の周期。"""
    culp = d["culprit"]
    lo = {"A": d["lo_a"], "B": d["lo_b"]}
    keep = "B" if culp == "A" else "A"
    tk = _Clock(rnd, 0)
    keep_lines = []
    for _ in range(3):
        keep_lines += [
            f"{tk(rnd.randint(12, 16))}: BGP: {lo[culp]} active went from Idle to Active",
            f"{tk(0)}: BGP: {lo[culp]} open active, local address {lo[keep]}",
            f"{tk(0)}: BGP: {lo[culp]} open failed: Connection refused by "
            "remote host",
            f"{tk(0)}: BGP: {lo[culp]} Active open failed - tcb is not "
            f"available, open active delayed "
            f"{rnd.choice([7168, 13312, 14336])}ms (35000ms max, 60% jitter)",
            f"{tk(0)}: BGP: {lo[culp]} active went from Active to Idle"]
    culp_lines = []                          # ★無音が指紋
    a_lines = culp_lines if culp == "A" else keep_lines
    b_lines = culp_lines if culp == "B" else keep_lines
    return a_lines, b_lines


def debug_blocks(d, rnd):
    A, B = d["A"], d["B"]
    v = d["variant"]
    if v == "pw_mismatch":
        return _dbg_pw_mismatch(d, rnd)
    if v == "pw_oneside":
        return _dbg_pw_oneside(d, rnd)
    if v == "remote_as_wrong":
        return _dbg_remote_as(d, rnd)
    if v == "nbr_shutdown":
        return _dbg_shutdown(d, rnd)
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


def _summary_block(d, side, state):
    """b3 実測書式の summary(★nbr_shutdown 専用。他変種では出さない規約を守る)。
    Idle (Admin) が唯一の証拠になるため、この変種だけ例外的に提示する。"""
    own_lo = d["lo_a"] if side == "A" else d["lo_b"]
    peer_lo = d["lo_b"] if side == "A" else d["lo_a"]
    asn = d["as_a"]
    return (f"{d[side]}# show ip bgp summary\n"
            f"BGP router identifier {own_lo}, local AS number {asn}\n"
            "BGP table version is 1, main routing table version 1\n"
            "\n"
            "Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ "
            "Up/Down  State/PfxRcd\n"
            f"{peer_lo:<15} 4        {asn} {0:>7} {0:>7} {1:>8}    0    0 "
            f"never    {state}")


def extra_block(d):
    """variant 固有の補助出力(経路の存在=誤診の罠 等)。
    ★ebgp_multihop では **両側の経路表**を出す(2026-08-02 出題フィードバック):
      片側だけだと「対向に経路が無いのでは」という誤仮説を提示情報で否定できない。"""
    if d["variant"] == "ebgp_multihop":
        return (_route_out(d["A"], d["lo_b"], d["ip_b"], d["igp"]) + "\n```\n```\n"
                + _route_out(d["B"], d["lo_a"], d["ip_a"], d["igp"]))
    if d["variant"] == "nbr_shutdown":
        culp = d["culprit"]
        keep = "B" if culp == "A" else "A"
        return (_summary_block(d, culp, "Idle (Admin)") + "\n```\n```\n"
                + _summary_block(d, keep, "Idle"))
    if d["variant"] == "remote_as_wrong":
        # 物理ピア(直結)。データプレーン健全の証拠として素の ping を出す
        return (f"{d['A']}# ping {d['ip_b']} repeat 3\n"
                "Type escape sequence to abort.\n"
                f"Sending 3, 100-byte ICMP Echos to {d['ip_b']}, timeout is 2 seconds:\n"
                "!!!\n"
                "Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms")
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
             "asym_up": ["read", "fix", "dbgconf"],
             # BL-136(b): 新変種は各2形(fix を軸に、読解の器を1つ)
             "pw_mismatch": ["fix", "dbgconf"],
             "pw_oneside": ["read", "fix"],
             "remote_as_wrong": ["fix", "dbgconf"],
             "nbr_shutdown": ["fix", "read"]}

# 形の抽選比。★BL-122(2026-08-16 ユーザ方針)= config で解決させる形を厚めに。
# asym_up だけは「なぜ UP か」を問う read を最厚に維持する(記述式で配点40の主役)。
FORM_W = {"addr_mismatch": {"select2": 65, "dbgconf": 35},
          "ebgp_multihop": {"select2": 70, "dbgconf": 30},
          "asym_up": {"read": 45, "fix": 30, "dbgconf": 25},
          "pw_mismatch": {"fix": 60, "dbgconf": 40},
          "pw_oneside": {"read": 55, "fix": 45},
          "remote_as_wrong": {"fix": 55, "dbgconf": 45},
          "nbr_shutdown": {"fix": 60, "read": 40}}

# dbgconf / read で置く前提文(BL-123 の「示されているものが全て」パターン)。
# 未提示前提の補完余地を封じ、一意性を確実にする。
PREMISE = ("なお、両ルータの BGP のネイバーに関する構成について判断できることは、"
           "示されている出力が全てです。示されている以外の障害は、存在しません。")


def kind_forms(kind):
    """その variant が取り得る出題形(--forms の絞り込みに使う)。
    ★essay(記述式ルーブリック)は BL-085 由来の旧3変種のみ。"""
    return set(MCQ_FORMS[kind]) | ({"essay"} if kind in LEGACY else set())


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
    if d["variant"] in NEW_VARIANTS:
        pool = _nv_dbgconf_pool(d)
        fp0 = pool[0][1]
        c = [(pool[0][0], True,
              "BADAUTH / NOTIFICATION の種別と現れる側のすべてが、示されている"
              "出力と一致する。", pool[0][3])]
        for desc, fp, why, cli in pool[1:]:
            if fp == fp0:
                raise ValueError("bgpdbg dbgconf(new): 錯乱肢が実像と同一指紋")
            c.append((desc, False, why, cli))
        order = list(range(len(c)))
        rnd.shuffle(order)
        return [c[i] for i in order]
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
    正解の組は列挙総当たりで機械判定し、一意でなければ ValueError。
    新変種(BL-136(b))= 単一選択・ok は状態モデルで計算済み。"""
    import itertools
    if d["variant"] in NEW_VARIANTS:
        menu = _nv_fix_menu(d)
        if sum(1 for _t, ok, _w, _c in menu if ok) != 1:
            raise ValueError(f"bgpdbg fix({d['variant']}): 正解が一意でない")
        c = list(menu)
        order = list(range(len(c)))
        rnd.shuffle(order)
        return [c[i] for i in order]
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
    """asym_up / pw_oneside / nbr_shutdown(複数選択・6択・正解2)。事実文の
    真偽はモデルの帰結と提示物(ping・debug 行・summary)に対応させる。"""
    if d["variant"] in ("pw_oneside", "nbr_shutdown"):
        truths, falses = _nv_read_pool(d)
        c = ([(t, True, w) for t, w in rnd.sample(truths, 2)]
             + [(t, False, w) for t, w in rnd.sample(falses, 4)])
        order = list(range(len(c)))
        rnd.shuffle(order)
        return [c[i] for i in order]
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


# ==========================================================================
# BL-136(b) 新変種の機構(2026-08-23)。既存の nbr/upd/mh 格子には載せず、
# 変種ごとの極小状態モデルで正解を機械判定する(house 規約= 正解フラグを
# 手書きしない)。素材の実測= poc/bgpdbg/results-probe2.md。
# ==========================================================================
NEW_VARIANTS = {"pw_mismatch", "pw_oneside", "remote_as_wrong", "nbr_shutdown"}


def _nv_sides(d):
    culp = d["culprit"]
    return culp, ("B" if culp == "A" else "A")


def _pw_state(d):
    """password の実像 {側: キー名 or None}。"""
    culp, keep = _nv_sides(d)
    if d["variant"] == "pw_mismatch":
        return {culp: d["key2"], keep: d["key"]}    # culp 側が台帳非準拠の旧キー
    return {culp: None, keep: d["key"]}             # pw_oneside: culp に無い


def _pw_up(state):
    """MD5 の TCP レベル判定: 両側一致(無認証同士を含む)のときだけ確立。"""
    return state["A"] == state["B"]


def _pw_fingerprint(state):
    """debug に現れる可視指紋: 各側の BADAUTH 種別(invalid/no/なし)。
    Invalid= 双方 digest 付きで不一致(両側に出る) / No= digest 無しの
    パケットを受けた(★password を持つ側にだけ出る・b1b 実測)。"""
    a, b = state["A"], state["B"]
    if a is not None and b is not None and a != b:
        return ("invalid", "invalid")
    if (a is None) != (b is None):
        return tuple("no" if state[s] is not None else "silent" for s in "AB")
    return ("up", "up")                              # 一致(または両方無し)= 確立


def _ras_state(d):
    """remote-as の実像 {側: 相手に期待している AS}。"""
    culp, keep = _nv_sides(d)
    peer_as = {"A": d["as_b"], "B": d["as_a"]}
    return {culp: d["as_wrong"], keep: peer_as[keep]}


def _ras_up(d, exp):
    return exp["A"] == d["as_b"] and exp["B"] == d["as_a"]


def _ras_fingerprint(d, exp):
    """可視指紋: 各側が NOTIFICATION を sent するか received するか up か。
    自側の期待が誤り= bad OPEN を検出して **sent**。"""
    if _ras_up(d, exp):
        return ("up", "up")
    return tuple("sent" if exp[s] != {"A": d["as_b"], "B": d["as_a"]}[s]
                 else "received" for s in "AB")


def _nv_fix_menu(d):
    """(text, ok, why, cli)。ok は状態モデルで機械判定した値を入れる
    (組み立て時に計算するが、selftest が「正解ちょうど1」を常時検査する)。"""
    culp, keep = _nv_sides(d)
    C, K = d[culp], d[keep]
    lo = {"A": d["lo_a"], "B": d["lo_b"]}
    as_i = d["as_a"]
    v = d["variant"]
    if v == "pw_mismatch":
        st = _pw_state(d)

        def ok(new):
            return (_pw_up(new) and new["A"] == new["B"] == d["key"])
        return [
            (f"両ルータの password を、運用台帳のキー {d['key']} で設定し直す",
             ok({"A": d["key"], "B": d["key"]}),
             "両側のキーが一致して TCP の MD5 検証が通り、認証を維持したまま"
             "確立する。",
             [f"! {d['A']} と {d['B']} の両方で", f"router bgp {as_i}",
              f" neighbor <対向のLo0> password {d['key']}"]),
            (f"{C} から password の構成を削除する",
             ok(dict(st, **{culp: None})),
             "片側だけ digest が無い状態(No MD5 digest)に変わるだけで、"
             "確立しない。認証の維持、という要件にも違反する。",
             [f"! {C}", f"router bgp {as_i}",
              f" no neighbor {lo[keep]} password"]),
            ("両ルータから password の構成を削除する",
             ok({"A": None, "B": None}),
             "確立はするが、MD5 認証を維持する、という要件に違反する。",
             [f"! {d['A']} と {d['B']} の両方で", f"router bgp {as_i}",
              " no neighbor <対向のLo0> password"]),
            (f"{C} に、update-source Loopback0 を設定し直す",
             ok(st),
             "送信元の構成は既に正しい(local address はループバック)。"
             "MD5 の不一致は送信元とは無関係で、帰結は変わらない。",
             [f"! {C}", f"router bgp {as_i}",
              f" neighbor {lo[keep]} update-source Loopback0"]),
            ("両ルータで、clear ip bgp * を実行する",
             ok(st),
             "キーが不一致のままである限り、MD5 の検証の失敗は繰り返される。",
             [f"! {d['A']} と {d['B']} の両方で", "clear ip bgp *"]),
        ]
    if v == "pw_oneside":
        st = _pw_state(d)

        def ok2(new):
            # ①確立 ②認証維持(両側キーあり) ③既設側({keep})の構成は変更しない
            return (_pw_up(new) and new["A"] is not None
                    and new["B"] is not None and new[keep] == st[keep])
        return [
            (f"{C} に、運用台帳のキー {d['key']} で password を設定する",
             ok2(dict(st, **{culp: d["key"]})),
             f"digest の欠落側({C})にキーが入り、両側が一致して確立する。"
             "既設側の構成にも触れない。",
             [f"! {C}", f"router bgp {as_i}",
              f" neighbor {lo[keep]} password {d['key']}"]),
            (f"{K} から password の構成を削除して、両側を無認証で揃える",
             ok2(dict(st, **{keep: None})),
             "確立はするが、MD5 認証を維持する、という要件と、認証が構成されて"
             "いる側の構成は変更しない、という要件の両方に違反する。",
             [f"! {K}", f"router bgp {as_i}",
              f" no neighbor {lo[culp]} password"]),
            (f"{K} の password を、同じキーで設定し直す",
             ok2(st),
             f"{K} には既に同じキーが構成されており、何も変わらない"
             f"({C} 側の欠落が残る)。",
             [f"! {K}", f"router bgp {as_i}",
              f" neighbor {lo[culp]} password {d['key']}"]),
            (f"{C} に、update-source Loopback0 を設定し直す",
             ok2(st),
             "送信元の構成の問題ではない(No MD5 digest は認証オプションの"
             "欠落を示す)。",
             [f"! {C}", f"router bgp {as_i}",
              f" neighbor {lo[keep]} update-source Loopback0"]),
            ("両ルータで、clear ip bgp * を実行する",
             ok2(st),
             "構成が変わらない限り、digest の欠落による失敗は繰り返される。",
             [f"! {d['A']} と {d['B']} の両方で", "clear ip bgp *"]),
        ]
    if v == "remote_as_wrong":
        exp = _ras_state(d)
        peer_as = {"A": d["as_b"], "B": d["as_a"]}
        own_as = {"A": d["as_a"], "B": d["as_b"]}
        ip = {"A": d["ip_a"], "B": d["ip_b"]}

        def ok3(new_exp, own_changed=False):
            return (not own_changed) and _ras_up(d, new_exp)
        return [
            (f"{C} の neighbor 文の remote-as を、{peer_as[culp]} へ是正する",
             ok3(dict(exp, **{culp: peer_as[culp]})),
             f"期待する AS が対向の実際の AS({peer_as[culp]})と一致し、"
             "OPEN の検証が通って確立する。",
             [f"! {C}", f"router bgp {own_as[culp]}",
              f" no neighbor {ip[keep]} remote-as {d['as_wrong']}",
              f" neighbor {ip[keep]} remote-as {peer_as[culp]}"]),
            (f"{K} の neighbor 文の remote-as を、{d['as_wrong']} へ変更して"
             "両側を揃える",
             ok3(dict(exp, **{keep: d["as_wrong"]})),
             f"「揃える」対象が誤り。{K} の期待まで対向の実際の AS"
             f"({peer_as[keep]})と食い違い、両側とも確立しない。",
             [f"! {K}", f"router bgp {own_as[keep]}",
              f" no neighbor {ip[culp]} remote-as {peer_as[keep]}",
              f" neighbor {ip[culp]} remote-as {d['as_wrong']}"]),
            (f"{C} の BGP プロセスの AS 番号を、{d['as_wrong']} へ変更する",
             ok3(exp, own_changed=True),
             "自身の AS を変更しても、neighbor 文が期待する対向の AS の誤りは"
             "解消しない。各ルータの AS 番号は変更しない、という要件にも違反する。",
             [f"! {C}", f"no router bgp {own_as[culp]}",
              f"router bgp {d['as_wrong']}", " ..."]),
            (f"{C} に、{ip[keep]} 宛の ebgp-multihop を設定する",
             ok3(exp),
             "両ルータは直接に接続されており、直接接続の検査は失敗していない"
             "(OPEN の交換まで進んでいる)。",
             [f"! {C}", f"router bgp {own_as[culp]}",
              f" neighbor {ip[keep]} ebgp-multihop 2"]),
            ("両ルータで、clear ip bgp * を実行する",
             ok3(exp),
             "期待する AS の誤りが残る限り、NOTIFICATION 2/2 は繰り返される。",
             [f"! {d['A']} と {d['B']} の両方で", "clear ip bgp *"]),
        ]
    # nbr_shutdown
    shut = {culp: True, keep: False}

    def ok4(new_shut, design_kept=True):
        return design_kept and not any(new_shut.values())
    return [
        (f"{C} の neighbor 文から、shutdown の構成を解除する",
         ok4(dict(shut, **{culp: False})),
         "管理的な停止(Idle (Admin))が解除され、ネイバーの確立の処理が再開する。",
         [f"! {C}", f"router bgp {as_i}",
          f" no neighbor {lo[keep]} shutdown"]),
        ("両ルータで、clear ip bgp * を実行する",
         ok4(shut),
         "管理的に停止されたネイバーは、clear では再開しない(構成の解除が必要)。",
         [f"! {d['A']} と {d['B']} の両方で", "clear ip bgp *"]),
        (f"{C} の neighbor 文を、{K} の物理アドレス宛へ作り直す",
         ok4(dict(shut, **{culp: False}), design_kept=False),
         "shutdown は行ごと消えるが、対向の neighbor 文(ループバック宛)との"
         "不一致が生まれ、ループバック間のピアリング設計の維持、という要件にも"
         "違反する。",
         [f"! {C}", f"router bgp {as_i}",
          f" no neighbor {lo[keep]} remote-as {as_i}",
          f" neighbor {d['ip_b'] if keep == 'B' else d['ip_a']} remote-as {as_i}"]),
        (f"{K} に、{lo[culp]} 宛の update-source Loopback0 を設定し直す",
         ok4(shut),
         f"{K} の送信元の構成は既に正しい(local address はループバック)。"
         "拒否の原因は対向の管理的な停止である。",
         [f"! {K}", f"router bgp {as_i}",
          f" neighbor {lo[culp]} update-source Loopback0"]),
        (f"{K} に、{lo[culp]} への静的ルートを設定する",
         ok4(shut),
         "到達性の障害ではない(TCP RST が返っている= パケットは相手に"
         "届いている)。",
         [f"! {K}", f"ip route {lo[culp]} 255.255.255.255 "
          f"{d['ip_a'] if culp == 'A' else d['ip_b']}"]),
    ]


def _nv_dbgconf_pool(d):
    """(states_desc, fingerprint, why, cli) 正解含む候補列。可視指紋で一意性検査。"""
    culp, keep = _nv_sides(d)
    lo = {"A": d["lo_a"], "B": d["lo_b"]}
    as_i = d["as_a"]
    if d["variant"] == "pw_mismatch":
        def cli_pw(pa, pb):
            out = []
            for side, pw in (("A", pa), ("B", pb)):
                peer = lo["B" if side == "A" else "A"]
                out += [f"! {d[side]}", f"router bgp {as_i}",
                        f" neighbor {peer} remote-as {as_i}",
                        f" neighbor {peer} update-source Loopback0"]
                if pw:
                    out.append(f" neighbor {peer} password {pw}")
                out.append("!")
            return out

        def desc(pa, pb):
            return (f"{d['A']}= password {pa or 'なし'} / "
                    f"{d['B']}= password {pb or 'なし'}")
        st = _pw_state(d)
        pa, pb = st["A"], st["B"]
        cands = [
            ((pa, pb), None),
            ((d["key"], d["key"]),
             "両側のキーが一致していれば MD5 の検証が通って確立し、BADAUTH は"
             "現れない。"),
            ((None if culp == "A" else pa, None if culp == "B" else pb),
             "片側の欠落であれば、digest を持つ側に **No** MD5 digest が出る"
             "(示されているのは両側の **Invalid**= 双方が異なるキーで digest を"
             "付けている状態)。"),
            ((None if keep == "A" else pa, None if keep == "B" else pb),
             "同上(欠落の側が逆の鏡像)。No MD5 digest の側が入れ替わる。"),
        ]
        return [(desc(a, b), _pw_fingerprint({"A": a, "B": b}), why,
                 cli_pw(a, b)) for (a, b), why in cands]
    # remote_as_wrong
    ip = {"A": d["ip_a"], "B": d["ip_b"]}
    own_as = {"A": d["as_a"], "B": d["as_b"]}
    peer_as = {"A": d["as_b"], "B": d["as_a"]}

    def cli_ras(ea, eb):
        out = []
        for side, exp in (("A", ea), ("B", eb)):
            peer = ip["B" if side == "A" else "A"]
            out += [f"! {d[side]}", f"router bgp {own_as[side]}",
                    f" neighbor {peer} remote-as {exp}", "!"]
        return out

    def desc2(ea, eb):
        return (f"{d['A']}= remote-as {ea} / {d['B']}= remote-as {eb}")
    exp = _ras_state(d)
    cands = [
        ((exp["A"], exp["B"]), None),
        ((peer_as["A"], peer_as["B"]),
         "両側の期待が対向の実際の AS と一致していれば確立し、NOTIFICATION は"
         "現れない。"),
        ((peer_as["A"] if culp == "A" else d["as_wrong"],
          peer_as["B"] if culp == "B" else d["as_wrong"]),
         "誤りの側が逆の鏡像。NOTIFICATION の sent / received の側が、"
         "示されている出力と入れ替わる。"),
        ((d["as_wrong"], d["as_wrong"]),
         "両側とも誤りであれば、双方が bad OPEN を検出して双方の側に "
         "NOTIFICATION **sent** が出る(received は現れない)。"),
    ]
    return [(desc2(a, b), _ras_fingerprint(d, {"A": a, "B": b}), why,
             cli_ras(a, b)) for (a, b), why in cands]


def _nv_read_pool(d):
    """(text, true?, why) の候補。正解2・錯乱4で組む。"""
    culp, keep = _nv_sides(d)
    C, K = d[culp], d[keep]
    lo = {"A": d["lo_a"], "B": d["lo_b"]}
    if d["variant"] == "pw_oneside":
        truths = [
            (f"MD5 認証の構成は、{K} の側にだけ存在している",
             f"No MD5 digest を記録しているのは {K} だけであり、これは"
             "digest の**無い**パケットを受けた側= password を持つ側に出る。"),
            (f"{C} が送信するパケットには、MD5 の digest が付いていない",
             "No MD5 digest は、受信したパケットに digest が欠落していることを"
             "示す(Invalid ではない= 不一致ではなく欠落)。"),
            ("両側のキーの不一致ではなく、片側の構成の欠落である",
             "キーの不一致であれば **Invalid** MD5 digest となり、両側に"
             "記録される。示されているのは **No** MD5 digest で、しかも"
             "片側にしか出ていない。"),
        ]
        falses = [
            ("両ルータに構成されている password のキーが、一致していない",
             "不一致であれば Invalid MD5 digest になる。示されているのは "
             "No MD5 digest である。"),
            (f"{K} の update-source の構成が欠落しているため、接続が失敗して"
             "いる",
             f"{K} の open active の local address はループバックであり、"
             "update-source は構成されている。"),
            (f"{lo[keep]} への経路が {C} に存在しないため、接続が失敗している",
             "TCP のパケットは相手に届いている(届かなければ BADAUTH 自体が"
             "記録されない)。"),
            ("neighbor 文の宛先が、両側で食い違っている",
             "行頭の宛先は両側ともループバックで、互いに一致している。"),
        ]
    else:   # nbr_shutdown
        truths = [
            (f"{C} には、ネイバーに対する管理的な shutdown が構成されている",
             f"{C} の summary の状態 **Idle (Admin)** がそれを示す(Admin= "
             "管理的な停止)。debug に一切の行が出ないことにも整合する"
             "(FSM が動作していない)。"),
            (f"{K} の接続の試行は、{C} が接続を受け付けない状態にあるために"
             "拒否されている",
             f"{K} 側の Connection refused の周期がそれを示す。管理的に停止"
             "されたネイバーに対して、{} は TCP 179 の接続を受理しない。"
             .format(C)),
        ]
        falses = [
            ("neighbor 文の宛先が、両側で食い違っている",
             "行頭の宛先は両側ともループバックで、互いに一致している。"
             "また宛先の食い違いであれば、両側に接続の試行と拒否が現れる。"),
            (f"{lo[culp]} への経路が {K} に存在しない",
             "Connection refused は TCP RST であり、パケットは相手に届いて"
             "いる(経路の欠落では refused にならない)。"),
            ("MD5 認証のキーが、両側で一致していない",
             "BADAUTH の行は存在しない。認証の問題ではない。"),
            (f"{C} の debug に行が無いのは、debug ip bgp が有効にされて"
             "いないためである",
             "両方のルータで debug が有効にされた、と示されている。"
             "管理的に停止されたネイバーでは FSM が動作せず、行が出ない。"),
        ]
    return truths, falses


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
    if v == "pw_mismatch":
        return ["両ルータの間で、BGP のピアが確立されること。",
                "ネイバーの MD5 認証が、維持されること。",
                f"認証のキーは、運用台帳に登録されているキー {d['key']} に、"
                "統一されること。"]
    if v == "pw_oneside":
        return ["両ルータの間で、BGP のピアが確立されること。",
                "ネイバーの MD5 認証が、維持されること。",
                "現在、認証が構成されている側のルータの構成は、"
                "変更しないこと。",
                f"認証のキーは、運用台帳に登録されているキー {d['key']} を、"
                "使用すること。"]
    if v == "remote_as_wrong":
        return ["両ルータの間で、BGP のピアが確立されること。",
                "各ルータの BGP プロセスの AS 番号は、変更しないこと。"]
    if v == "nbr_shutdown":
        return ["両ルータの間で、BGP のピアが確立されること。",
                "ループバック・インターフェイスの間でピアリングを行う設計が、"
                "維持されること。"]
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
            if v in LEGACY:
                ebgp = v == "ebgp_multihop"
                up, ra, rb = session(actual_cfgs(d), ebgp)
                # 実測: asym_up だけ確立(発見1)・ebgp は両側 no_route(発見3)
                assert up == (v == "asym_up"), (v, up)
                if ebgp:
                    assert ra == rb == "no_route"
            else:
                # BL-136(b) 新変種の不変条件(probe2 実測)
                if v in ("pw_mismatch", "pw_oneside"):
                    st = _pw_state(d)
                    assert not _pw_up(st), (v, st)
                    fp = _pw_fingerprint(st)
                    if v == "pw_mismatch":
                        assert fp == ("invalid", "invalid"), fp
                    else:
                        # BADAUTH(No)は password を持つ側だけ・欠落側は無音
                        assert sorted(fp) == ["no", "silent"], fp
                elif v == "remote_as_wrong":
                    exp = _ras_state(d)
                    assert not _ras_up(d, exp)
                    assert sorted(_ras_fingerprint(d, exp)) == \
                        ["received", "sent"]
                # debug が描けること(nbr_shutdown は残骸側が空= 仕様)
                a_l, b_l = debug_blocks(d, _r.Random(seed))
                if v == "nbr_shutdown":
                    assert (a_l == []) != (b_l == []), "片側だけ無音のはず"
                else:
                    assert a_l and b_l
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
