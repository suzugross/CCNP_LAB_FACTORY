#!/usr/bin/env python3
"""OSPF 隣接 debug 読解 紙面ファミリ (BL-177) — gen_paper_mcq.py の shape=ospfdbg 素材(bgpdbg の姉妹)。

設計= 非公開側の計画メモ(2026-09-18) §3 A1 / 指紋の正典= poc/paper-kb/results-raw.md P3(iol-xe 17.15.1 実測)。
`debug ip ospf adj|hello|events`・`show ip ospf neighbor`・syslog の**実出力の書式**を 1 台の視点で描き、
read(出力から分かること)/cause(原因)/fix(是正)/which(どの debug で見えるか)を問う。

kinds(=故障種。which は横断の即答 kind):
  mtu        MTU 不一致(視点= 小さい側 or 大きい側を抽選。larger/smaller interface MTU・Retransmitting DBD・Too many retransmissions)
  hello      hello/dead 不一致(Mismatched hello parameters・Dead R x C y, Hello R x C y)
  area       エリア不一致(Rcv pkt from X, area A, mismatched area B in the header・%OSPF-4-ERRRCV)
  auth_type  認証タイプ不一致(Mismatched Authentication type. Input packet specified type N, we use type M)
  auth_key   鍵文字列不一致(Mismatched Authentication key - ID N)
  auth_keyid 鍵 ID 不一致(Invalid cryptographic authentication Key ID N on interface)
  nettype    p2p×broadcast(broadcast 側だけ FULL/DR・経路は入らない・debug に異常なし)
  prio0      両側 priority 0(2WAY/DROTHER 固着・DR: none)
  stub       stub/E-bit 不一致(Hello from X with mismatched Stub/Transit area option bit・隣接なし)
  dup_rid    RID 重複(%OSPF-4-DUP_RTRID_NBR)
  unidir     片方向(自側 INIT・相手は空・Rcv hello はあるが 2WAY に進まない)
  passive    相手が passive(Dead timer expired・Rcv hello が無い)
  which      横断: 症状から「その不一致を確認する debug」を選ぶ(瞬発力枠)
★定説照合(計画メモ §5): 状態表記(EXSTART/EXCHANGE)は側と版で揺れるので正解肢は「再送を繰り返し最終的に DOWN」まで。
  mtu-ignore は小さい側に入れれば FULL(R2a・実測)。両側に入れる肢を正解に、片側の肢は R2a 再確認後に使う。

公開 API(svc 型ファミリ共通・gen_paper_svc.py の docstring 参照)。
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VARIANTS = ["mtu", "hello", "area", "auth_type", "auth_key", "auth_keyid", "nettype",
            "prio0", "stub", "dup_rid", "unidir", "passive"]
KINDS = VARIANTS + ["which"]
SPEED_KINDS = ["which"]
THINK_KINDS = VARIANTS
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {v: {"read", "cause", "fix"} for v in VARIANTS}
FORMS["nettype"] = {"read", "cause", "fix"}
FORMS["which"] = {"select"}
DIFF = {**{v: 4 for v in VARIANTS}, "which": 2, "nettype": 5, "unidir": 5}


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


NAMES = [("R1", "R2"), ("RT01", "RT02"), ("CORE1", "DIST1"), ("EDGE-A", "EDGE-B"), ("RA", "RB")]
IFS = [("Ethernet0/0", "Et0/0"), ("Ethernet0/1", "Et0/1"), ("GigabitEthernet0/0", "Gi0/0"), ("GigabitEthernet0/1", "Gi0/1")]
AUTH_TYPE_NAME = {0: "null(認証なし)", 1: "simple(平文)", 2: "message-digest(MD5)"}


# ==========================================================================
# 盤面
# ==========================================================================
def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    d["me"], d["nbr"] = rnd.choice(NAMES)
    d["ifl"], d["ifs"] = rnd.choice(IFS)
    o2, o3 = rnd.randint(1, 250), rnd.randint(0, 250)
    d["net"] = f"10.{o2}.{o3}.0"
    d["me_ip"], d["nbr_ip"] = f"10.{o2}.{o3}.1", f"10.{o2}.{o3}.2"
    if rnd.random() < 0.5:
        d["me_ip"], d["nbr_ip"] = d["nbr_ip"], d["me_ip"]
    a, b = rnd.sample([1, 2, 3, 4, 5, 6, 7, 8, 9], 2)
    d["me_rid"], d["nbr_rid"] = f"{a}.{a}.{a}.{a}", f"{b}.{b}.{b}.{b}"
    d["pid"] = rnd.choice([1, 1, 10, 100])
    d["area"] = rnd.choice([0, 0, 1, 10])
    v = kind if kind != "which" else rnd.choice([x for x in VARIANTS if x in WHICH_ANSWER])
    d["variant"] = v
    d["t0"] = (rnd.randint(0, 23), rnd.randint(0, 59), rnd.randint(0, 40))
    if v == "mtu":
        d["side"] = rnd.choice(["small", "small", "large"])     # 自ルータが小さい側(教材と同じ視点)を多め
        big, small = rnd.choice([(1500, 1400), (1500, 1380), (9000, 1500), (1600, 1500)])
        d["me_mtu"], d["nbr_mtu"] = (small, big) if d["side"] == "small" else (big, small)
    elif v == "hello":
        d["me_hello"], d["me_dead"] = rnd.choice([(10, 40), (10, 40), (30, 120)])
        d["nbr_hello"] = rnd.choice([h for h in (5, 15, 20, 3) if h != d["me_hello"]])
        d["nbr_dead"] = d["nbr_hello"] * 4
    elif v == "area":
        d["nbr_area"] = rnd.choice([x for x in (0, 1, 2, 10, 100) if x != d["area"]])
    elif v == "auth_type":
        d["me_auth"], d["nbr_auth"] = rnd.choice([(0, 2), (2, 0), (0, 1), (1, 2), (2, 1)])
    elif v == "auth_key":
        d["key_id"] = rnd.choice([1, 1, 2, 5])
    elif v == "auth_keyid":
        d["me_key"], d["nbr_key"] = rnd.sample([1, 2, 3, 5, 10], 2)
    elif v == "nettype":
        d["me_type"] = rnd.choice(["BROADCAST", "POINT_TO_POINT"])
        d["nbr_type"] = "POINT_TO_POINT" if d["me_type"] == "BROADCAST" else "BROADCAST"
    elif v == "prio0":
        pass
    elif v == "stub":
        if d["area"] == 0:
            d["area"] = rnd.choice([1, 10])
        d["stub_side"] = rnd.choice(["me", "nbr"])
    elif v == "dup_rid":
        d["nbr_rid"] = d["me_rid"]
    elif v == "unidir":
        d["blocker"] = rnd.choice(["nbr_acl", "nbr_acl", "link"])
    elif v == "passive":
        pass
    return d


# ==========================================================================
# exhibit
# ==========================================================================
def _ts(d, plus):
    h, m, s = d["t0"]
    s2 = s + plus
    m2 = m + s2 // 60
    h2 = (h + m2 // 60) % 24
    return f"*Sep 18 {h2:02d}:{m2 % 60:02d}:{s2 % 60:02d}.{(plus * 137) % 1000:03d}"


def _adj(d, plus, msg):
    return f"{_ts(d, plus)}: OSPF-{d['pid']} ADJ   {d['ifs']}: {msg}"


def _hello(d, plus, msg):
    return f"{_ts(d, plus)}: OSPF-{d['pid']} HELLO {d['ifs']}: {msg}"


def _adjchg(d, plus, frm, to, why):
    return (f"{_ts(d, plus)}: %OSPF-5-ADJCHG: Process {d['pid']}, Nbr {d['nbr_rid']} on {d['ifl']} "
            f"from {frm} to {to}, Neighbor Down: {why}")


def nbr_table(d, rows):
    L = ["Neighbor ID     Pri   State           Dead Time   Address         Interface"]
    for rid, pri, st, dead, ip in rows:
        L.append(f"{rid:<15} {pri:>3}   {st:<15} {dead:<11} {ip:<15} {d['ifl']}")
    return "\n".join(L)


def debug_lines(d):
    v = d["variant"]
    nb, ip = d["nbr_rid"], d["nbr_ip"]
    L = []
    if v == "mtu":
        if d["side"] == "small":
            L += [_adj(d, 0, f"Rcv DBD from {nb} seq 0x1DA8 opt 0x52 flag 0x7 len 32  mtu {d['nbr_mtu']} state EXSTART"),
                  _adj(d, 0, f"Nbr {nb} has larger interface MTU"),
                  _adj(d, 4, f"Send DBD to {nb} seq 0x255A opt 0x52 flag 0x7 len 32"),
                  _adj(d, 4, f"Retransmitting DBD to {nb} [23]"),
                  _adj(d, 5, f"Rcv DBD from {nb} seq 0x1DA8 opt 0x52 flag 0x7 len 32  mtu {d['nbr_mtu']} state EXSTART"),
                  _adj(d, 5, f"Nbr {nb} has larger interface MTU"),
                  _adj(d, 9, f"Send DBD to {nb} seq 0x255A opt 0x52 flag 0x7 len 32"),
                  _adj(d, 9, f"Retransmitting DBD to {nb} [24]"),
                  _adj(d, 14, f"Killing nbr {nb} due to excessive (25) retransmissions"),
                  _adj(d, 14, f"{nb} address {ip} is dead, state DOWN"),
                  _adjchg(d, 14, "EXSTART", "DOWN", "Too many retransmissions")]
        else:
            L += [_adj(d, 0, f"Rcv DBD from {nb} seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu {d['nbr_mtu']} state EXSTART"),
                  _adj(d, 0, f"Nbr {nb} has smaller interface MTU"),
                  _adj(d, 0, "NBR Negotiation Done. We are the SLAVE"),
                  _adj(d, 0, f"Send DBD to {nb} seq 0x1C4 opt 0x52 flag 0x2 len 52"),
                  _adj(d, 5, f"Nbr {nb} has smaller interface MTU"),
                  _adj(d, 5, f"Send DBD to {nb} seq 0x1C4 opt 0x52 flag 0x2 len 52"),
                  _adj(d, 10, f"Nbr {nb} has smaller interface MTU"),
                  _adj(d, 10, f"Send DBD to {nb} seq 0x1C4 opt 0x52 flag 0x2 len 52"),
                  _adj(d, 120, f"Killing nbr {nb} due to excessive (25) retransmissions"),
                  _adjchg(d, 120, "EXCHANGE", "DOWN", "Too many retransmissions")]
    elif v == "hello":
        L += [_hello(d, 0, f"Rcv hello from {nb} area {d['area']} {ip}"),
              _hello(d, 0, f"Mismatched hello parameters from {ip}"),
              _hello(d, 0, f"Dead R {d['nbr_dead']} C {d['me_dead']}, Hello R {d['nbr_hello']} C {d['me_hello']} Mask R 255.255.255.0 C 255.255.255.0"),
              _hello(d, 1, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _hello(d, d["nbr_hello"], f"Rcv hello from {nb} area {d['area']} {ip}"),
              _hello(d, d["nbr_hello"], f"Mismatched hello parameters from {ip}"),
              _hello(d, d["nbr_hello"], f"Dead R {d['nbr_dead']} C {d['me_dead']}, Hello R {d['nbr_hello']} C {d['me_hello']} Mask R 255.255.255.0 C 255.255.255.0")]
    elif v == "area":
        L += [_adj(d, 0, f"Rcv pkt from {ip}, area 0.0.0.{d['area']}, mismatched area 0.0.0.{d['nbr_area']} in the header"),
              f"{_ts(d, 0)}: %OSPF-4-ERRRCV: Received invalid packet: mismatched area ID from backbone area from {ip}, {d['ifl']}"
              if d["area"] == 0 else
              _adj(d, 10, f"Rcv pkt from {ip}, area 0.0.0.{d['area']}, mismatched area 0.0.0.{d['nbr_area']} in the header"),
              _hello(d, 4, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}")]
    elif v == "auth_type":
        L += [_adj(d, 0, f"Rcv pkt from {ip} : Mismatched Authentication type. Input packet specified type {d['nbr_auth']}, we use type {d['me_auth']}"),
              _hello(d, 4, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _adj(d, 10, f"Rcv pkt from {ip} : Mismatched Authentication type. Input packet specified type {d['nbr_auth']}, we use type {d['me_auth']}")]
    elif v == "auth_key":
        L += [_adj(d, 0, f"Rcv pkt from {ip} : Mismatched Authentication key - ID {d['key_id']}"),
              _hello(d, 4, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _adj(d, 10, f"Rcv pkt from {ip} : Mismatched Authentication key - ID {d['key_id']}")]
    elif v == "auth_keyid":
        L += [_adj(d, 0, f"Rcv pkt from {ip} : Mismatched Authentication Key - Invalid cryptographic authentication Key ID {d['nbr_key']} on interface"),
              _hello(d, 4, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _adj(d, 10, f"Rcv pkt from {ip} : Mismatched Authentication Key - Invalid cryptographic authentication Key ID {d['nbr_key']} on interface")]
    elif v == "prio0":
        L += [_hello(d, 0, f"Rcv hello from {nb} area {d['area']} {ip}"),
              _adj(d, 0, f"2 Way Communication to {nb}, state 2WAY"),
              _adj(d, 0, "DR/BDR election"),
              _adj(d, 0, "DR: none "),
              _adj(d, 0, "   BDR: none "),
              _hello(d, 10, f"Rcv hello from {nb} area {d['area']} {ip}"),
              _hello(d, 10, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}")]
    elif v == "stub":
        L += [_hello(d, 0, f"Rcv hello from {nb} area {d['area']} {ip}"),
              _hello(d, 0, f"Hello from {ip} with mismatched Stub/Transit area option bit"),
              _hello(d, 10, f"Rcv hello from {nb} area {d['area']} {ip}"),
              _hello(d, 10, f"Hello from {ip} with mismatched Stub/Transit area option bit")]
    elif v == "dup_rid":
        L += [_adjchg(d, 0, "LOADING", "FULL", "Loading Done").replace("Neighbor Down: ", ""),
              f"{_ts(d, 4)}: %OSPF-4-DUP_RTRID_NBR: OSPF detected duplicate router-id {d['me_rid']} from {ip} on interface {d['ifl']}",
              _adj(d, 4, f"{nb} address {ip} is dead, state DOWN"),
              _adjchg(d, 4, "FULL", "DOWN", "Interface down or detached")]
    elif v == "unidir":
        L += [_hello(d, 0, f"Rcv hello from {nb} area {d['area']} {ip}"),
              _hello(d, 1, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _hello(d, 10, f"Rcv hello from {nb} area {d['area']} {ip}"),
              _hello(d, 11, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _hello(d, 20, f"Rcv hello from {nb} area {d['area']} {ip}")]
    elif v == "passive":
        L += [_hello(d, 0, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _hello(d, 10, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _hello(d, 20, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}"),
              _adj(d, 31, f"{nb} address {ip} is dead"),
              _adj(d, 31, f"{nb} address {ip} is dead, state DOWN"),
              _adjchg(d, 31, "FULL", "DOWN", "Dead timer expired"),
              _hello(d, 40, f"Send hello to 224.0.0.5 area {d['area']} from {d['me_ip']}")]
    return L


def nbr_block(d):
    v = d["variant"]
    nb, ip = d["nbr_rid"], d["nbr_ip"]
    if v == "mtu":
        rows = [(nb, 1, "EXSTART/DR", "00:00:37", ip)] if d["side"] == "small" else [(nb, 1, "EXCHANGE/BDR", "00:00:38", ip)]
    elif v == "nettype":
        rows = [(nb, 1, "FULL/DR", "00:00:36", ip)] if d["me_type"] == "BROADCAST" else []
    elif v == "prio0":
        rows = [(nb, 0, "2WAY/DROTHER", "00:00:37", ip)]
    elif v == "unidir":
        rows = [(nb, 1, "INIT/DROTHER", "00:00:37", ip)]
    else:
        rows = []
    return f"{d['me']}# show ip ospf neighbor\n\n" + nbr_table(d, rows)


def extra_block(d):
    v = d["variant"]
    if v == "nettype":
        me = f"{d['me']}# show ip ospf interface {d['ifl']} | include Network Type|Neighbor Count\n  Process ID {d['pid']}, Router ID {d['me_rid']}, Network Type {d['me_type']}, Cost: 10"
        me += f"\n  Neighbor Count is {1 if d['me_type'] == 'BROADCAST' else 0}, Adjacent neighbor count is {1 if d['me_type'] == 'BROADCAST' else 0}"
        nb = f"{d['nbr']}# show ip ospf interface {d['ifl']} | include Network Type|Neighbor Count\n  Process ID {d['pid']}, Router ID {d['nbr_rid']}, Network Type {d['nbr_type']}, Cost: 10"
        nb += f"\n  Neighbor Count is {1 if d['nbr_type'] == 'BROADCAST' else 0}, Adjacent neighbor count is {1 if d['nbr_type'] == 'BROADCAST' else 0}"
        rt = f"{d['me']}# show ip route ospf\n(OSPF の経路はありません)"
        return f"{me}\n\n{nb}\n\n{rt}"
    if v == "unidir":
        return f"{d['nbr']}# show ip ospf neighbor\n\n" + nbr_table(d, [])
    if v == "prio0":
        return f"{d['nbr']}# show ip ospf neighbor\n\n" + nbr_table(d, [(d["me_rid"], 0, "2WAY/DROTHER", "00:00:36", d["me_ip"])])
    return ""


def exhibit(d):
    v = d["variant"]
    parts = []
    if v == "nettype":
        parts.append(nbr_block(d))
        parts.append(extra_block(d))
        return "\n\n".join(parts)
    dbg = ("adj" if v in ("mtu", "area", "auth_type", "auth_key", "auth_keyid", "dup_rid")
           else "hello" if v in ("hello", "stub", "unidir", "passive") else "adj" if v == "prio0" else "adj")
    hdr = f"{d['me']}# debug ip ospf {dbg}" + ("\n" + f"{d['me']}# debug ip ospf hello" if v == "prio0" else "")
    if v == "dup_rid":
        hdr = f"{d['me']}# show logging | include OSPF"
    parts.append(hdr + "\n" + "\n".join(debug_lines(d)))
    if v not in ("dup_rid", "hello", "area", "auth_type", "auth_key", "auth_keyid", "stub", "passive"):
        parts.append(nbr_block(d))
    ex = extra_block(d)
    if ex and v != "nettype":
        parts.append(ex)
    return "\n\n".join(parts)


# ==========================================================================
# read: 出力から分かること(記述, 真偽, 偽の理由)
# ==========================================================================
def read_pool(d):
    v = d["variant"]
    me, nb = d["me"], d["nbr"]
    P = []
    if v == "mtu":
        small = d["side"] == "small"
        P += [(f"{nb} のインターフェイス MTU は、{me} より大きい。", small, f"出力の文言は has {'larger' if small else 'smaller'} interface MTU であり、相手の MTU は自ルータより{'大きい' if small else '小さい'}。"),
              (f"{nb} のインターフェイス MTU は、{me} より小さい。", not small, f"出力の文言は has {'larger' if small else 'smaller'} interface MTU であり、相手の MTU は自ルータより{'大きい' if small else '小さい'}。"),
              (f"{me} は DBD パケットの再送を繰り返し、最終的に隣接は DOWN になった。", True, ""),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "DBD の交換段階(EXSTART/EXCHANGE)に達しており、Hello の受信は完了している。"),
              (f"再送の末に、隣接は最終的に FULL に達した。", False, "最終行は Too many retransmissions による DOWN であり、FULL には達していない。"),
              (f"{me} と {nb} の認証の設定が一致していない。", False, "出力に Mismatched Authentication の行は無く、認証の不一致ではない。"),
              (f"隣接は 25 回の再送の後に打ち切られた。", True, ""),
              (f"MTU の大きい側だけに ip ospf mtu-ignore を構成すれば、隣接は FULL になる。", False, "受信 DBD の MTU を拒否しているのは小さい側であり、大きい側だけの mtu-ignore では FULL にならない。")]
    elif v == "hello":
        P += [(f"{nb} の hello インターバルは {d['nbr_hello']} 秒である。", True, ""),
              (f"{me} の hello インターバルは {d['me_hello']} 秒である。", True, ""),
              (f"{nb} の hello インターバルは {d['me_hello']} 秒である。", False, "R(受信)の値が相手、C(構成)の値が自ルータであり、相手は R の値である。"),
              (f"{me} の dead インターバルは {d['nbr_dead']} 秒である。", False, "C(構成)の Dead は自ルータの値であり、R の値は相手のものである。"),
              (f"サブネット マスクが一致していない。", False, "Mask R と C は同じ値であり、マスクは一致している。"),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "Rcv hello の行があり、受信はできている(パラメータが不一致で捨てている)。"),
              (f"{nb} の dead インターバルは {d['nbr_dead']} 秒である。", True, "")]
    elif v == "area":
        P += [(f"{me} の {d['ifl']} はエリア {d['area']} に属している。", True, ""),
              (f"{nb} は、エリア {d['nbr_area']} としてパケットを送っている。", True, ""),
              (f"{me} の {d['ifl']} はエリア {d['nbr_area']} に属している。", False, "area 0.0.0.N が自ルータのエリア、mismatched area 0.0.0.M in the header が相手のエリアである。"),
              (f"{nb} は、エリア {d['area']} としてパケットを送っている。", False, "in the header の値が相手のパケットのエリアであり、自ルータのエリアとは異なる。"),
              (f"認証の設定が一致していない。", False, "出力はエリア ID の不一致であり、認証の行は無い。"),
              (f"{me} は {nb} からのパケットを受信できていない。", False, "Rcv pkt from の行があり、受信はできている(エリア不一致で捨てている)。")]
    elif v == "auth_type":
        P += [(f"{nb} の認証タイプは {AUTH_TYPE_NAME[d['nbr_auth']]} である。", True, ""),
              (f"{me} の認証タイプは {AUTH_TYPE_NAME[d['me_auth']]} である。", True, ""),
              (f"{me} の認証タイプは {AUTH_TYPE_NAME[d['nbr_auth']]} である。", False, "we use type が自ルータ、Input packet specified type が相手のタイプである。"),
              (f"{nb} の認証タイプは {AUTH_TYPE_NAME[d['me_auth']]} である。", False, "Input packet specified type が相手のタイプである。"),
              (f"両方のルータで認証タイプは一致しているが、鍵の文字列が異なる。", False, "出力は Authentication type の不一致であり、鍵の文字列の不一致(Mismatched Authentication key)ではない。"),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "Rcv pkt from の行があり、受信はできている。")]
    elif v == "auth_key":
        P += [(f"両方のルータで鍵 ID {d['key_id']} が使われているが、鍵の文字列が一致していない。", True, ""),
              (f"両方のルータで認証タイプは一致している。", True, ""),
              (f"{me} と {nb} で認証タイプが一致していない。", False, "認証タイプの不一致なら Mismatched Authentication type の行になる。"),
              (f"{nb} は鍵 ID {d['key_id']} を持っていない。", False, "鍵 ID が無い場合は Invalid cryptographic authentication Key ID の行になる。"),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "Rcv pkt from の行があり、受信はできている。"),
              (f"エリア ID が一致していない。", False, "出力は認証鍵の不一致であり、エリアの行は無い。")]
    elif v == "auth_keyid":
        P += [(f"{nb} は鍵 ID {d['nbr_key']} で認証したパケットを送っている。", True, ""),
              (f"{me} の {d['ifl']} には鍵 ID {d['nbr_key']} が構成されていない。", True, ""),
              (f"{me} は鍵 ID {d['nbr_key']} で認証したパケットを送っている。", False, "Invalid … Key ID N on interface の N は受信したパケットの鍵 ID であり、相手の鍵 ID である。"),
              (f"両方のルータで鍵 ID は一致しているが、鍵の文字列が異なる。", False, "鍵 ID が一致して文字列が違う場合は Mismatched Authentication key - ID N の行になる。"),
              (f"{me} と {nb} で認証タイプが一致していない。", False, "認証タイプの不一致なら Mismatched Authentication type の行になる。"),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "Rcv pkt from の行があり、受信はできている。")]
    elif v == "nettype":
        bc = d["me_type"] == "BROADCAST"
        P += [(f"{me} と {nb} で OSPF のネットワーク タイプが一致していない。", True, ""),
              (f"{'自ルータ' if bc else nb} 側の表示では隣接は FULL だが、OSPF の経路は交換されていない。", True, ""),
              (f"{me} と {nb} の hello インターバルが一致していない。", False, "BROADCAST と POINT_TO_POINT の hello/dead は同じ既定値であり、Hello は受け入れられている。"),
              (f"{me} と {nb} で MTU が一致していない。", False, "MTU の不一致なら DBD の段階で larger/smaller interface MTU が出る。"),
              (f"認証の設定が一致していない。", False, "認証の不一致なら Mismatched Authentication の行が出る。"),
              (f"両方のルータで隣接は FULL に達しており、経路も交換されている。", False, "OSPF の経路は入っておらず、片側(p2p 側)には隣接が表示されない。")]
    elif v == "prio0":
        P += [(f"両方のルータの OSPF プライオリティが 0 であり、DR も BDR も選出されていない。", True, ""),
              (f"隣接は 2WAY の状態で止まっており、データベースの交換に進んでいない。", True, ""),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "Rcv hello の行があり 2WAY に達している。"),
              (f"{me} と {nb} は DROTHER 同士であり、DR が別に存在する。", False, "DR: none / BDR: none であり、DR は存在しない。"),
              (f"MTU の不一致で DBD の再送を繰り返している。", False, "DBD の交換には進んでおらず、MTU の行も無い。"),
              (f"認証の設定が一致していない。", False, "認証の不一致の行は無い。")]
    elif v == "stub":
        P += [(f"{me} と {nb} で、エリア {d['area']} を stub にするかどうかの設定が一致していない。", True, ""),
              (f"{me} は {nb} からの Hello を受信しているが、隣接は形成されない。", True, ""),
              (f"エリア ID が一致していない。", False, "エリア ID の不一致なら mismatched area … in the header の行になる。"),
              (f"認証の設定が一致していない。", False, "認証の不一致の行は無い。"),
              (f"hello インターバルが一致していない。", False, "hello パラメータの不一致なら Mismatched hello parameters の行になる。"),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "Rcv hello の行があり、受信はできている。")]
    elif v == "dup_rid":
        P += [(f"{me} と {nb} の OSPF ルータ ID が同じである。", True, ""),
              (f"隣接はいったん FULL に達した後に DOWN した。", True, ""),
              (f"{me} と {nb} で認証の設定が一致していない。", False, "認証の不一致の行は無い。"),
              (f"エリア ID が一致していない。", False, "エリアの不一致の行は無い。"),
              (f"MTU の不一致で DBD の再送を繰り返している。", False, "MTU の行は無い。"),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "隣接は FULL に達しており、Hello は受信できている。")]
    elif v == "unidir":
        P += [(f"{me} は {nb} からの Hello を受信しているが、{me} が送る Hello は {nb} に届いていない。", True, ""),
              (f"{nb} の隣接テーブルには {me} が載っていない。", True, ""),
              (f"{me} は {nb} から Hello パケットを受け取れていない。", False, "Rcv hello の行があり INIT に達している(受信はできている)。"),
              (f"hello インターバルが一致していない。", False, "Mismatched hello parameters の行は無い。"),
              (f"認証の設定が一致していない。", False, "認証の不一致の行は無い。"),
              (f"隣接は 2WAY に達している。", False, "状態は INIT であり、相手の Hello に自ルータの ID が含まれていない。")]
    elif v == "passive":
        P += [(f"{me} は {nb} からの Hello を受信しなくなり、dead タイマの満了で隣接が DOWN した。", True, ""),
              (f"{me} は Hello を送信し続けている。", True, ""),
              (f"{me} と {nb} で hello インターバルが一致していない。", False, "Mismatched hello parameters の行は無い。"),
              (f"認証の設定が一致していない。", False, "認証の不一致の行は無い。"),
              (f"MTU の不一致で DBD の再送を繰り返している。", False, "MTU の行は無い。"),
              (f"{nb} からの Hello はパラメータが不一致で捨てられている。", False, "Rcv hello の行そのものが無く、受信していない。")]
    return P


def build_choices_read(d, rnd):
    pool = read_pool(d)
    trues = [(t, w) for t, ok, w in pool if ok]
    falses = [(t, w) for t, ok, w in pool if not ok]
    if not trues or len(falses) < 3:
        raise ValueError("read: 肢が組めない")
    t, _ = rnd.choice(trues)
    c = [(t, True, "")]
    for f, w in rnd.sample(falses, 3):
        c.append((f, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# cause
# ==========================================================================
def cause_text(d, v):
    me, nb = d["me"], d["nbr"]
    return {
        "mtu": f"{me} と {nb} のインターフェイス MTU が一致していない。",
        "hello": f"{me} と {nb} の hello インターバルまたは dead インターバルが一致していない。",
        "area": f"{me} と {nb} で、リンクを所属させているエリア ID が一致していない。",
        "auth_type": f"{me} と {nb} で OSPF の認証タイプが一致していない。",
        "auth_key": f"{me} と {nb} で同じ鍵 ID を使っているが、鍵の文字列が一致していない。",
        "auth_keyid": f"{me} と {nb} で使用している鍵 ID が一致していない。",
        "nettype": f"{me} と {nb} で OSPF のネットワーク タイプが一致していない。",
        "prio0": f"{me} と {nb} の両方で OSPF プライオリティが 0 に設定されている。",
        "stub": f"{me} と {nb} で、エリアを stub にする設定が片方にしか無い。",
        "dup_rid": f"{me} と {nb} に同じ OSPF ルータ ID が設定されている。",
        "unidir": f"{me} が送信する Hello が {nb} に届いていない(片方向の通信になっている)。",
        "passive": f"{nb} 側で当該インターフェイスが passive-interface に設定されている(または OSPF から外れている)。",
    }[v]


CAUSE_NEAR = {
    "mtu": ["hello", "auth_key", "nettype", "prio0"],
    "hello": ["mtu", "area", "auth_type", "passive"],
    "area": ["hello", "stub", "auth_type", "unidir"],
    "auth_type": ["auth_key", "auth_keyid", "hello", "area"],
    "auth_key": ["auth_type", "auth_keyid", "mtu", "hello"],
    "auth_keyid": ["auth_key", "auth_type", "hello", "area"],
    "nettype": ["mtu", "hello", "prio0", "auth_key"],
    "prio0": ["nettype", "mtu", "hello", "unidir"],
    "stub": ["area", "hello", "auth_type", "unidir"],
    "dup_rid": ["auth_key", "area", "mtu", "hello"],
    "unidir": ["passive", "hello", "auth_type", "prio0"],
    "passive": ["unidir", "hello", "auth_type", "area"],
}


def build_choices_cause(d, rnd):
    v = d["variant"]
    c = [(cause_text(d, v), True, "")]
    for k in rnd.sample(CAUSE_NEAR[v], 3):
        c.append((cause_text(d, k), False, _cause_why(d, k)))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _cause_why(d, k):
    return {
        "mtu": "MTU の不一致なら DBD の段階で larger/smaller interface MTU の行が出る。この出力には無い。",
        "hello": "hello/dead の不一致なら Mismatched hello parameters と Dead R/C, Hello R/C の行が出る。この出力には無い。",
        "area": "エリアの不一致なら mismatched area … in the header の行が出る。この出力には無い。",
        "auth_type": "認証タイプの不一致なら Mismatched Authentication type の行が出る。この出力には無い。",
        "auth_key": "鍵文字列の不一致なら Mismatched Authentication key - ID N の行が出る。この出力には無い。",
        "auth_keyid": "鍵 ID の不一致なら Invalid cryptographic authentication Key ID N の行が出る。この出力には無い。",
        "nettype": "ネットワーク タイプの不一致では片側が FULL のまま経路が入らず、debug に不一致の行は出ない。この出力とは合わない。",
        "prio0": "両側 priority 0 なら 2WAY/DROTHER で止まり DR: none になる。この出力とは合わない。",
        "stub": "stub の不一致なら mismatched Stub/Transit area option bit の行が出る。この出力には無い。",
        "dup_rid": "ルータ ID の重複なら %OSPF-4-DUP_RTRID_NBR が出る。この出力には無い。",
        "unidir": "片方向なら自側 INIT で Rcv hello が続き、相手側の隣接テーブルは空になる。この出力とは合わない。",
        "passive": "相手が passive なら Rcv hello が無いまま Dead timer expired で落ちる。この出力とは合わない。",
    }[k]


# ==========================================================================
# fix: 是正(候補 4・正解 1)。★正解は「両側で一致させる/安全側」の手に限る(R2a の片側 mtu-ignore は再確認後)
# ==========================================================================
def fix_menu(d):
    v = d["variant"]
    me, nb, ifl = d["me"], d["nbr"], d["ifl"]
    if v == "mtu":
        small = me if d["side"] == "small" else nb
        big = nb if d["side"] == "small" else me
        return [(f"{me} と {nb} の {ifl} に ip ospf mtu-ignore を構成する。", True, ""),
                (f"{big} の {ifl} にだけ ip ospf mtu-ignore を構成する。", False,
                 f"DBD の MTU 検査で受信を拒否しているのは MTU の小さい側({small})であり、大きい側だけに mtu-ignore を入れても隣接は FULL にならない(実測)。"),
                (f"{me} と {nb} の {ifl} で ip ospf hello-interval を同じ値にそろえる。", False, "hello の不一致ではなく、MTU の不一致である。"),
                (f"{small} の {ifl} で ip ospf network point-to-point を構成する。", False, "ネットワーク タイプを変えても、DBD の MTU 検査は変わらない(片側だけ変えると別の不一致になる)。")]
    if v == "hello":
        return [(f"{nb} の {ifl} で ip ospf hello-interval {d['me_hello']} を構成し、dead インターバルを {me} と同じにする。", True, ""),
                (f"{me} の {ifl} で ip ospf dead-interval {d['nbr_dead']} だけを構成する。", False, "dead だけをそろえても hello インターバルが異なるままで、不一致は解消しない。"),
                (f"{me} と {nb} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。"),
                (f"{nb} の {ifl} で ip ospf priority 0 を構成する。", False, "プライオリティは hello パラメータの一致には関係ない。")]
    if v == "area":
        return [(f"{nb} の network 文(または ip ospf {d['pid']} area)で、{ifl} をエリア {d['area']} に所属させる。", True, ""),
                (f"{me} の {ifl} をエリア {d['nbr_area']} に移す。", False, "自ルータ側のエリアを変えると、自ルータの他のリンクとの整合(バックボーンとの接続)を崩す。設問はネイバ側の是正を求めている。" if d["area"] == 0 else "エリアの一致だけが目的なら成立するが、設問は自ルータの設計(エリア {})を変えない前提である。".format(d["area"])),
                (f"{me} と {nb} の {ifl} で ip ospf hello-interval をそろえる。", False, "hello の不一致ではない。"),
                (f"{nb} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。")]
    if v == "auth_type":
        want = d["me_auth"]
        cli = {0: "no ip ospf authentication", 1: "ip ospf authentication", 2: "ip ospf authentication message-digest"}[want]
        return [(f"{nb} の {ifl} で {cli} を構成し、{me} と同じ認証タイプにする。", True, ""),
                (f"{nb} の {ifl} で ip ospf message-digest-key 1 md5 の鍵文字列を {me} と同じにする。", False, "鍵の文字列ではなく、認証タイプそのものが一致していない。"),
                (f"{me} と {nb} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。"),
                (f"{nb} の {ifl} で ip ospf hello-interval を {me} と同じにする。", False, "hello の不一致ではない。")]
    if v == "auth_key":
        return [(f"{nb} の {ifl} で ip ospf message-digest-key {d['key_id']} md5 の鍵文字列を {me} と同じにする。", True, ""),
                (f"{nb} の {ifl} で ip ospf authentication message-digest を構成する。", False, "認証タイプは既に一致しており、鍵の文字列が異なる。"),
                (f"{me} の {ifl} で ip ospf message-digest-key {d['key_id'] + 1} md5 を追加する。", False, "別の鍵 ID を足しても、受信したパケットの鍵 ID {} の文字列が一致しなければ検証に失敗する。".format(d["key_id"])),
                (f"{me} と {nb} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。")]
    if v == "auth_keyid":
        return [(f"{nb} の {ifl} で、鍵 ID {d['me_key']} に {me} と同じ鍵文字列を構成する(または {me} に鍵 ID {d['nbr_key']} を同じ文字列で追加する)。", True, ""),
                (f"{nb} の {ifl} で ip ospf authentication message-digest を構成する。", False, "認証タイプは既に一致しており、鍵 ID が異なる。"),
                (f"{me} の {ifl} で ip ospf hello-interval を {nb} と同じにする。", False, "hello の不一致ではない。"),
                (f"{me} と {nb} の {ifl} で ip ospf priority をそろえる。", False, "プライオリティは認証の検証に関係ない。")]
    if v == "nettype":
        other = "point-to-point" if d["me_type"] == "BROADCAST" else "broadcast"
        return [(f"{nb} の {ifl} で ip ospf network {d['me_type'].lower().replace('_', '-')} を構成し、{me} とネットワーク タイプをそろえる。", True, ""),
                (f"{me} と {nb} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。"),
                (f"{me} の {ifl} で ip ospf priority 0 を構成する。", False, "プライオリティを変えても、ネットワーク タイプの不一致は残る。"),
                (f"{me} と {nb} の {ifl} で ip ospf hello-interval を {10 if d['me_type'] == 'BROADCAST' else 30} にそろえる。", False, "hello パラメータは一致しており、不一致はネットワーク タイプである。")]
    if v == "prio0":
        return [(f"{me} または {nb} の {ifl} で ip ospf priority を 1 以上に設定する。", True, ""),
                (f"{me} と {nb} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。"),
                (f"{me} と {nb} の {ifl} で ip ospf hello-interval をそろえる。", False, "hello は一致している(2WAY に達している)。"),
                (f"{nb} の {ifl} で ip ospf authentication を構成する。", False, "認証の問題ではない。")]
    if v == "stub":
        has = d["me"] if d["stub_side"] == "me" else d["nbr"]
        lacks = d["nbr"] if d["stub_side"] == "me" else d["me"]
        return [(f"{lacks} の router ospf {d['pid']} で area {d['area']} stub を構成し、{has} とそろえる。", True, ""),
                (f"{has} の router ospf {d['pid']} で area {d['area']} nssa を構成する。", False, "NSSA にしても相手が非 stub のままなら E-bit の不一致は残る(両方が同じ設定である必要がある)。"),
                (f"{me} と {nb} の {ifl} で ip ospf hello-interval をそろえる。", False, "hello パラメータの不一致ではない。"),
                (f"{me} と {nb} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。")]
    if v == "dup_rid":
        return [(f"{nb} の router ospf {d['pid']} で router-id を {me} と異なる値に変更し、OSPF プロセスを再起動する。", True, ""),
                (f"{me} と {nb} の {ifl} で ip ospf hello-interval をそろえる。", False, "hello の不一致ではない。"),
                (f"{nb} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。"),
                (f"{nb} の {ifl} で ip ospf authentication を構成する。", False, "認証の問題ではない。")]
    if v == "unidir":
        return [(f"{nb} の {ifl} に着信方向で適用されているアクセス リストで、OSPF(プロトコル 89)を許可する。", True, ""),
                (f"{me} の {ifl} に着信方向で適用されているアクセス リストで、OSPF を許可する。", False, "自ルータは相手の Hello を受信できている(INIT)。届いていないのは自ルータが送る Hello である。"),
                (f"{me} と {nb} の {ifl} で ip ospf hello-interval をそろえる。", False, "hello の不一致ではない。"),
                (f"{me} の router ospf {d['pid']} で router-id を変更する。", False, "ルータ ID は関係ない。")]
    if v == "passive":
        return [(f"{nb} の router ospf {d['pid']} で no passive-interface {ifl} を構成する。", True, ""),
                (f"{me} の router ospf {d['pid']} で no passive-interface {ifl} を構成する。", False, "自ルータは Hello を送信しており、passive ではない。"),
                (f"{me} と {nb} の {ifl} で ip ospf dead-interval を長くする。", False, "dead を延ばしても、相手が Hello を送らなければいずれ満了する。"),
                (f"{me} の {ifl} に ip ospf mtu-ignore を構成する。", False, "MTU の不一致ではない。")]
    raise ValueError(v)


def build_choices_fix(d, rnd):
    c = list(fix_menu(d))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# which(瞬発力枠): 症状 → その不一致が見える debug
# ==========================================================================
WHICH_ANSWER = {
    "mtu": ("debug ip ospf adj", "DBD の交換(EXSTART/EXCHANGE)と MTU の比較は adj で見える。"),
    "hello": ("debug ip ospf hello", "hello パラメータの比較(Dead R/C, Hello R/C)は hello で見える。"),
    "area": ("debug ip ospf adj", "エリア ID の不一致(mismatched area … in the header)は adj で見える。"),
    "auth_type": ("debug ip ospf adj", "認証タイプの不一致は adj で見える。"),
    "auth_key": ("debug ip ospf adj", "認証鍵の不一致は adj で見える。"),
    "stub": ("debug ip ospf hello", "stub/transit の E-bit の不一致は hello で見える。"),
    "dup_rid": ("show logging", "ルータ ID の重複は %OSPF-4-DUP_RTRID_NBR の syslog として出る。"),
}
WHICH_SYMPTOM = {
    "mtu": "隣接が EXSTART と EXCHANGE の間で止まり、しばらくして DOWN する。MTU の不一致が疑われる。",
    "hello": "隣接がまったく形成されず、相手の Hello は届いているように見える。hello/dead インターバルの不一致が疑われる。",
    "area": "隣接が形成されず、リンクを所属させたエリアの食い違いが疑われる。",
    "auth_type": "隣接が形成されず、片方だけに認証が構成されている疑いがある。",
    "auth_key": "認証タイプは一致しているが隣接が形成されず、鍵の不一致が疑われる。",
    "stub": "隣接が形成されず、エリアの stub の設定の食い違いが疑われる。",
    "dup_rid": "隣接がいったん FULL になった直後に DOWN することを繰り返し、ルータ ID の重複が疑われる。",
}
WHICH_POOL = ["debug ip ospf adj", "debug ip ospf hello", "debug ip ospf events", "debug ip ospf packet", "show logging", "debug ip packet"]


def build_choices_select(d, rnd):
    v = d["variant"]
    ans, why = WHICH_ANSWER[v]
    d["which_symptom"] = WHICH_SYMPTOM[v]
    others = [x for x in WHICH_POOL if x != ans]
    picks = [ans] + rnd.sample(others, 3)
    rnd.shuffle(picks)
    c = []
    for p in picks:
        if p == ans:
            c.append((p, True, ""))
        else:
            c.append((p, False, _which_why(p, v)))
    return c


def _which_why(p, v):
    if p == "debug ip ospf adj":
        return "adj には DBD 交換・MTU・エリア・認証の不一致が出るが、この不一致(hello パラメータ/E-bit)は hello 側に出る。"
    if p == "debug ip ospf hello":
        return "hello には hello パラメータと E-bit の不一致が出るが、この不一致は adj(または syslog)に出る。"
    if p == "debug ip ospf events":
        return "events は構成変更などのイベントであり、この不一致の決め手の行は出ない。"
    if p == "debug ip ospf packet":
        return "packet は受信パケットのヘッダ要約であり、不一致の理由は出ない。"
    if p == "show logging":
        return "syslog に出るのは ADJCHG と DUP_RTRID_NBR などであり、この不一致の理由は debug でしか見えない。"
    if p == "debug ip packet":
        return "IP レベルの debug であり、OSPF の隣接の不一致の理由は出ない。"
    return ""


def build_choices_select2(d, rnd):
    raise ValueError("ospfdbg に select2 は無い")


def build_choices_allthat(d, rnd):
    raise ValueError("ospfdbg に allthat は無い")


def build_match(d, rnd):
    raise ValueError("ospfdbg に match は無い")


# ==========================================================================
# Markdown
# ==========================================================================
CORE = {
    "mtu": "MTU 不一致は DBD の段階で検出される。小さい側には has larger interface MTU、大きい側には has smaller interface MTU が出て、DBD の再送(Retransmitting DBD [N])が続き、25 回で Killing nbr … Too many retransmissions として DOWN する。是正は両側の ip ospf mtu-ignore か MTU の一致。★受信 DBD の MTU が自分の IF MTU より大きいときに拒否するのは小さい側なので、小さい側だけの mtu-ignore で FULL になり、大きい側だけでは不成立(iol-xe 17.15.1 で 5 試行一致)。",
    "hello": "Mismatched hello parameters の次行 Dead R x C y, Hello R x C y Mask R … C … は R=受信(相手)・C=構成(自分)。hello/dead/マスクのどれが違うかを R と C の比較で読む。",
    "area": "Rcv pkt from X, area A, mismatched area B in the header は A=自ルータのエリア・B=相手のパケットのエリア。バックボーン側では %OSPF-4-ERRRCV: mismatched area ID from backbone area も出る。",
    "auth_type": "Mismatched Authentication type. Input packet specified type N, we use type M は N=相手・M=自分。0=null・1=simple・2=MD5。",
    "auth_key": "Mismatched Authentication key - ID N は鍵 ID N が両側にあり文字列が違う。鍵 ID そのものが無い場合は Invalid cryptographic authentication Key ID N on interface になる。",
    "auth_keyid": "Invalid cryptographic authentication Key ID N on interface は、受信パケットの鍵 ID N を自ルータのインターフェイスが持っていない。",
    "nettype": "BROADCAST × POINT_TO_POINT では hello は通る(既定 10/40 が同じ)ので、broadcast 側だけ FULL/DR と表示され、p2p 側は隣接が出ず(DBD 再送)、両側とも経路が入らない。debug に「不一致」の行は出ないのが決め手。",
    "prio0": "両側 priority 0 では DR/BDR が選出されず(DR: none / BDR: none)、隣接は 2WAY/DROTHER のまま DBD 交換に進まない。",
    "stub": "Hello from X with mismatched Stub/Transit area option bit(E-bit 不一致)は Hello 段階で捨てられ、隣接テーブルに相手が現れない。両側で area N stub をそろえる。",
    "dup_rid": "%OSPF-4-DUP_RTRID_NBR: OSPF detected duplicate router-id X from Y。いったん FULL になっても直後に落ちる。片方の router-id を変えてプロセスを再起動する。",
    "unidir": "自ルータが INIT/DROTHER で Rcv hello が続くのに 2WAY に進まないのは、相手の Hello の隣接リストに自ルータが無い= 自ルータの Hello が相手に届いていない(相手側の着信 ACL など)。相手側の隣接テーブルは空。",
    "passive": "Rcv hello が無いまま Dead timer expired で FULL→DOWN。自ルータは Send hello を続けている。相手側の passive-interface(または OSPF からの離脱)が典型。",
    "which": "不一致の種類で見える場所が違う: hello パラメータ/E-bit= debug ip ospf hello、MTU/エリア/認証= debug ip ospf adj、ルータ ID 重複= syslog(%OSPF-4-DUP_RTRID_NBR)。",
}
TITLES = {**{v: "OSPF 隣接の debug 出力の分析" for v in VARIANTS}, "which": "OSPF の debug コマンドの選択"}


def _intro(d):
    v = d["variant"]
    me, nb = d["me"], d["nbr"]
    base = (f"{me} と {nb} は {d['ifl']} 同士で直接接続され、OSPF プロセス {d['pid']} のエリア {d['area']} で隣接を形成する構成です。")
    if v == "passive":
        return base + f" 隣接はこれまで FULL でしたが、{nb} の構成変更の後に次の出力が得られました。"
    if v == "dup_rid":
        return base + f" {nb} に新しい構成を投入した後、{me} で次のログが記録されています。"
    if v == "nettype":
        return base + " 隣接の状態と経路について、次の出力が得られました。"
    return base + f" 隣接が形成されないため、{me} でデバッグを有効にしたところ、次の出力が得られました。"


def question_body(d, choices, form):
    v = d["variant"]
    if d["kind"] == "which":
        before = d.get("which_symptom", WHICH_SYMPTOM[v])
        ask = "この事象の原因を確認するために、最初に実行するコマンドとして最も適切なものは、次のうちどれですか。(1つを選択してください)"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    ex = exhibit(d)
    before = f"{_intro(d)}\n\n```\n{ex}\n```"
    if form == "read":
        ask = "この出力から分かることとして、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
    elif form == "cause":
        ask = "この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
    else:
        ask = (f"{me_side(d)}この事象を解消するための変更として最も適切なものは、次のうちどれですか。(1つを選択してください)")
    ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    return before, ask, ch_md, ""


def me_side(d):
    v = d["variant"]
    if v in ("hello", "area", "auth_type", "auth_key", "nettype", "passive", "unidir"):
        return f"{d['me']} の構成は設計どおりであり、変更しないものとします。"
    return ""


def answer_body(d, choices, form):
    keys = [k for k, (t, ok, w) in zip("ABCDEFG", choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip("ABCDEFG", choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[d["variant"] if d["kind"] != "which" else "which"]]
    if d["kind"] != "which":
        lines += ["", f"- 仕込み: `{d['variant']}`" + (f"(視点= {'小さい' if d['side'] == 'small' else '大きい'} MTU 側)" if d["variant"] == "mtu" else ""),
                  "- 指紋の正典: poc/paper-kb/results-raw.md P3(iol-xe 17.15.1)。状態表記(EXSTART/EXCHANGE)は側と版で揺れるため、正解の弁別子にしていない。"]
    return "\n".join(lines)


def pick_count(form, choices):
    return 1


# ==========================================================================
# selftest
# ==========================================================================
def selftest(seeds=30):
    import random as _r
    import re as _re
    ng = n = 0
    bad = {}
    builders = {"read": build_choices_read, "cause": build_choices_cause, "fix": build_choices_fix,
                "select": build_choices_select}
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
                    before, ask, ch_md, terms_md = question_body(d, choices, form)
                    assert "```" in before or kind == "which", "exhibit なし"
                    ab = answer_body(d, choices, form)
                    assert "## 正解" in ab
                    if kind != "which":
                        ex = exhibit(d)
                        # 指紋の決め手の行が exhibit に含まれること
                        key = {"mtu": "interface MTU", "hello": "Mismatched hello parameters",
                               "area": "mismatched area", "auth_type": "Mismatched Authentication type",
                               "auth_key": "Mismatched Authentication key", "auth_keyid": "Invalid cryptographic",
                               "nettype": "Network Type", "prio0": "2WAY/DROTHER", "stub": "Stub/Transit",
                               "dup_rid": "DUP_RTRID_NBR", "unidir": "INIT/DROTHER", "passive": "Dead timer expired"}[kind]
                        assert key in ex, f"指紋 {key} が無い"
                except (AssertionError, ValueError, KeyError) as exc:
                    ng += 1
                    bad.setdefault((kind, form), [0, repr(exc)])[0] += 1
    for (k, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{f}: {cnt} 件 (例: {ex})")
    print(f"[gen_paper_ospfdbg selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
