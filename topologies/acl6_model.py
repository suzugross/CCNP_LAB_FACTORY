#!/usr/bin/env python3
"""IPv6 ACL 意味評価器 (BL-106 P3) — `acl_model.py` の IPv6 版。

IPv4 版との**構造的な差**（これが紙面 shape=aclv6 の主題そのもの）:

1. アドレスは**ワイルドカード・マスクではなくプレフィックス長**で書く
   （`2001:DB8:13::/64`）。したがって一致範囲は必ず**連続**であり、
   IPv4 のような非連続キューブは存在しない → 評価は前方ビット比較だけで足りる
   （`acl_cover.py` の三値キューブ代数は不要）。
2. 適用コマンドが `ip access-group` ではなく **`ipv6 traffic-filter`**。
3. ★**暗黙の許可が末尾に存在する**（近隣探索）。IPv4 の「暗黙 deny だけ」とは違い、
   明示的に `deny ipv6 any any` を書くと**近隣探索まで落ちて隣接が壊れる**。
   実挙動は poc/acl/README.md の V 系実測に従う（本モジュールは
   `implicit_nd` フラグでその規則を表現し、生成器から実測どおりに設定する）。

評価は first-match。エントリは dict で持つ（IPv4 版と同じ思想）:
  {"seq", "action", "proto", "src", "src_len", "dst", "dst_len",
   "dport", "sport", "icmp_type"}
アドレスは 128bit 整数、長さはプレフィックス長。

自己検査: `python3 acl6_model.py --selftest`
"""
import sys

FULL128 = (1 << 128) - 1

# ND のメッセージ種別（`permit icmp any any nd-ns` 等で書かれる語彙）
ND_TYPES = ("nd-ns", "nd-na")


def parse_v6(s):
    """IPv6 アドレス文字列 → 128bit 整数（`::` 圧縮に対応）。"""
    s = s.strip()
    if "/" in s:
        s = s.split("/")[0]
    if s == "::":
        return 0
    if "::" in s:
        head, tail = s.split("::", 1)
        hp = [x for x in head.split(":") if x != ""]
        tp = [x for x in tail.split(":") if x != ""]
        mid = ["0"] * (8 - len(hp) - len(tp))
        parts = hp + mid + tp
    else:
        parts = s.split(":")
    if len(parts) != 8:
        raise ValueError(f"IPv6 として解釈できない: {s}")
    v = 0
    for p in parts:
        v = (v << 16) | int(p or "0", 16)
    return v


def fmt_v6(v):
    """128bit 整数 → 実機表示に近い圧縮形（最長のゼロ連続を `::` に畳む）。"""
    parts = [(v >> (112 - 16 * i)) & 0xFFFF for i in range(8)]
    best_i = best_n = cur_i = cur_n = -1
    for i, p in enumerate(parts):
        if p == 0:
            if cur_n <= 0:
                cur_i, cur_n = i, 1
            else:
                cur_n += 1
            if cur_n > best_n:
                best_i, best_n = cur_i, cur_n
        else:
            cur_n = 0
    out = [format(p, "X") for p in parts]
    if best_n >= 2:
        return ":".join(out[:best_i]) + "::" + ":".join(out[best_i + best_n:])
    return ":".join(out)


def in_prefix(addr, net, plen):
    """addr が net/plen に含まれるか。★連続マスクなので前方 plen ビットの比較のみ。"""
    if plen == 0:
        return True
    mask = (FULL128 << (128 - plen)) & FULL128
    return (addr & mask) == (net & mask)


def entry(action, proto="ipv6", src="::", src_len=0, dst="::", dst_len=0,
          dport=None, sport=None, icmp_type=None, seq=10):
    """エントリを組み立てる（src/dst は文字列でも整数でも可）。"""
    return {"seq": seq, "action": action, "proto": proto,
            "src": parse_v6(src) if isinstance(src, str) else src,
            "src_len": src_len,
            "dst": parse_v6(dst) if isinstance(dst, str) else dst,
            "dst_len": dst_len,
            "dport": dport, "sport": sport, "icmp_type": icmp_type}


def _port_match(spec, port):
    if spec is None:
        return True
    if port is None:
        return False
    op, vals = spec
    if op == "eq":
        return port == vals[0]
    if op == "neq":
        return port != vals[0]
    if op == "gt":
        return port > vals[0]
    if op == "lt":
        return port < vals[0]
    if op == "range":
        return vals[0] <= port <= vals[1]
    raise ValueError(op)


def entry_matches(e, v):
    """1エントリとパケットベクタの照合。

    v = {"proto": "tcp"|"udp"|"icmp"|"ipv6", "src", "dst",
         "sport", "dport", "icmp_type"}
    """
    if e["proto"] != "ipv6" and e["proto"] != v["proto"]:
        return False
    src = v["src"] if isinstance(v["src"], int) else parse_v6(v["src"])
    dst = v["dst"] if isinstance(v["dst"], int) else parse_v6(v["dst"])
    if not in_prefix(src, e["src"], e["src_len"]):
        return False
    if not in_prefix(dst, e["dst"], e["dst_len"]):
        return False
    if e["proto"] in ("tcp", "udp"):
        if not _port_match(e.get("sport"), v.get("sport")):
            return False
        if not _port_match(e.get("dport"), v.get("dport")):
            return False
    if e.get("icmp_type") is not None and v.get("icmp_type") != e["icmp_type"]:
        return False
    return True


def first_match(entries, v):
    for i, e in enumerate(entries or []):
        if entry_matches(e, v):
            return i
    return None


def evaluate(entries, v, implicit_nd=True):
    """True=permit / False=deny。

    ★`implicit_nd`= 「明示のエントリに一致しなかった近隣探索は、
      末尾の暗黙の許可によって通る」という IPv6 固有の規則（実測に従って設定する）。
      **明示の deny に一致した場合はこの救済は働かない**（そこで確定するため）。
    """
    i = first_match(entries, v)
    if i is not None:
        return entries[i]["action"] == "permit"
    if implicit_nd and v.get("icmp_type") in ND_TYPES:
        return True                    # 暗黙の許可（nd-ns / nd-na）
    return False                       # 暗黙の拒否


def nd_survives(entries, implicit_nd=True):
    """★近隣探索が生き残るか= 隣接が壊れないか。

    ND(nd-ns / nd-na) が通るかどうかだけを見る。明示の `deny ipv6 any any` を
    末尾に置くと、暗黙の許可より**先に**一致して ND が落ちる。
    """
    for t in ND_TYPES:
        v = {"proto": "icmp", "src": parse_v6("FE80::1"),
             "dst": parse_v6("FE80::2"), "sport": None, "dport": None,
             "icmp_type": t}
        if not evaluate(entries, v, implicit_nd=implicit_nd):
            return False
    return True


def render(entries, name):
    """`show ipv6 access-list <name>` に近い書式で描く（実測に合わせて調整する）。"""
    out = [f"IPv6 access list {name}"]
    for e in entries:
        out.append("    " + render_entry(e))
    return "\n".join(out)


def render_entry(e):
    def addr(a, ln):
        if ln == 0:
            return "any"
        if ln == 128:
            return f"host {fmt_v6(a)}"
        return f"{fmt_v6(a)}/{ln}"
    body = f"{e['proto']} {addr(e['src'], e['src_len'])} " \
           f"{addr(e['dst'], e['dst_len'])}"
    if e.get("dport"):
        op, vals = e["dport"]
        body += f" {op} {vals[0]}"
    if e.get("icmp_type"):
        body += f" {e['icmp_type']}"
    return f"{e['action']} {body} sequence {e['seq']}"


def _selftest():
    ok = ng = 0

    def chk(c, label):
        nonlocal ok, ng
        if c:
            ok += 1
        else:
            ng += 1
            print(f"  NG: {label}")

    chk(parse_v6("2001:DB8:13::1") == parse_v6("2001:0DB8:0013:0000:0000:0000:0000:0001"),
        ":: 圧縮の展開")
    chk(fmt_v6(parse_v6("2001:DB8:13::1")) == "2001:DB8:13::1", "整形の往復")
    chk(fmt_v6(parse_v6("::")) == "::", ":: の整形")
    chk(in_prefix(parse_v6("2001:DB8:13::5"), parse_v6("2001:DB8:13::"), 64),
        "/64 の内包")
    chk(not in_prefix(parse_v6("2001:DB8:14::5"), parse_v6("2001:DB8:13::"), 64),
        "/64 の非内包")
    chk(in_prefix(parse_v6("2001:DB8:14::5"), parse_v6("2001:DB8::"), 32),
        "/32 の内包")

    # first-match と暗黙の拒否
    ents = [entry("permit", "tcp", "2001:DB8:13::", 64, "::", 0,
                  dport=("eq", [22]), seq=10),
            entry("permit", "ipv6", "2001:DB8:3::3", 128,
                  "2001:DB8:2::2", 128, seq=20)]
    v_ssh = {"proto": "tcp", "src": "2001:DB8:13::5", "dst": "2001:DB8:2::2",
             "sport": 1234, "dport": 22, "icmp_type": None}
    v_web = dict(v_ssh, dport=80)
    chk(evaluate(ents, v_ssh), "SSH は許可")
    chk(not evaluate(ents, v_web), "HTTP は暗黙の拒否")

    # ★ND: 暗黙のときは通り、明示 deny を足すと落ちる
    chk(nd_survives(ents), "暗黙の拒否のみなら ND は生きる")
    ents2 = ents + [entry("deny", "ipv6", "::", 0, "::", 0, seq=30)]
    chk(not nd_survives(ents2), "★明示 deny を書くと ND が落ちる")
    ents3 = ents + [entry("permit", "icmp", "::", 0, "::", 0,
                          icmp_type="nd-ns", seq=25),
                    entry("permit", "icmp", "::", 0, "::", 0,
                          icmp_type="nd-na", seq=26),
                    entry("deny", "ipv6", "::", 0, "::", 0, seq=30)]
    chk(nd_survives(ents3), "ND を明示許可すれば明示 deny があっても生きる")

    # 未定義・空（生成器側で扱うが、空リストの評価は暗黙 deny）
    chk(not evaluate([], v_ssh), "空リストは暗黙の拒否")
    chk(nd_survives([]), "空リストでも ND は暗黙の許可で通る")

    print(f"acl6_model selftest: OK={ok} NG={ng}")
    return ng == 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    print(__doc__)
