#!/usr/bin/env python3
"""ACL 意味評価器（BL-014・GEN-DOJO-ACL の採点エンジン）。

`show access-lists` / `show ip access-lists` の**正規化出力**（running-config は
使わない）をパースして ACL モデルを作り、テストパケットベクタ
  {proto: tcp|udp|icmp, src, dst, sport, dport, established, icmp_type}
を **first-match＋暗黙deny** で評価する。

対応: 標準/拡張・番号/named、host/any、ワイルドカード（**非連続含む**）、
ポート演算子 eq/neq/gt/lt/range、established、icmp タイプ（名前/番号）、
ポート名⇔番号（www/telnet/domain/bootps 等）、"(N matches)" と "log" の除去。

表示仕様の注意（実機検証 2026-07-12・IOL-XE 17.15）:
  - 標準 ACL のサブネットは「A, wildcard bits W」形式・ホストは裸の IP。
  - 拡張 ACL の既知ポートは名前表示（eq www 等）→ PORT_NAMES で番号へ正規化。
  - エントリは seq 番号順に評価する（標準 ACL はハッシュ順表示があり得るため
    表示順でなく seq でソート）。

grade.py の新チェック種 `acl_vectors:` から使う:
  {"acl": "<名前|番号>",
   "vectors": [{...vector..., "expect": "permit"|"deny"}, ...]}
"""
import re

# 名前→番号（IOS が show で名前表示する既知ポートを中心に）。
# tcp/udp で同番異名（514 = cmd(tcp)/syslog(udp) 等）は評価が番号ベースのため
# 名前→番号の一方向写像で足りる。
PORT_NAMES = {
    "echo": 7, "discard": 9, "daytime": 13, "chargen": 19,
    "ftp-data": 20, "ftp": 21, "ssh": 22, "telnet": 23, "smtp": 25,
    "time": 37, "nameserver": 42, "whois": 43, "tacacs": 49, "domain": 53,
    "bootps": 67, "bootpc": 68, "tftp": 69, "gopher": 70, "finger": 79,
    "www": 80, "hostname": 101, "pop2": 109, "pop3": 110, "sunrpc": 111,
    "ident": 113, "nntp": 119, "ntp": 123, "netbios-ns": 137,
    "netbios-dgm": 138, "netbios-ss": 139, "snmp": 161, "snmptrap": 162,
    "xdmcp": 177, "bgp": 179, "irc": 194, "dnsix": 195, "mobile-ip": 434,
    "pim-auto-rp": 496, "isakmp": 500, "exec": 512, "biff": 512,
    "login": 513, "who": 513, "cmd": 514, "syslog": 514, "lpd": 515,
    "talk": 517, "rip": 520, "uucp": 540, "klogin": 543, "kshell": 544,
    "non500-isakmp": 4500,
}
ICMP_TYPES = {
    "echo-reply": 0, "unreachable": 3, "source-quench": 4, "redirect": 5,
    "echo": 8, "router-advertisement": 9, "router-solicitation": 10,
    "time-exceeded": 11, "parameter-problem": 12, "timestamp-request": 13,
    "timestamp-reply": 14, "information-request": 15, "information-reply": 16,
    "mask-request": 17, "mask-reply": 18, "traceroute": 30,
}


class AclParseError(ValueError):
    pass


def _ip(s):
    parts = s.split(".")
    if len(parts) != 4:
        raise AclParseError(f"IPv4 でない: {s}")
    v = 0
    for p in parts:
        n = int(p)
        if not 0 <= n <= 255:
            raise AclParseError(f"IPv4 でない: {s}")
        v = (v << 8) | n
    return v


def _port(tok):
    if tok.isdigit():
        return int(tok)
    if tok in PORT_NAMES:
        return PORT_NAMES[tok]
    raise AclParseError(f"未知のポート: {tok}")


def _icmp(tok):
    if tok.isdigit():
        return int(tok)
    if tok in ICMP_TYPES:
        return ICMP_TYPES[tok]
    raise AclParseError(f"未知の icmp タイプ: {tok}")


def _looks_ip(s):
    parts = s.split(".")
    return len(parts) == 4 and all(p.isdigit() and int(p) <= 255 for p in parts)


def _addr_spec(toks, i):
    """toks[i:] から (addr, wild, 次位置) を読む。
    any / host A / A W / A（標準 ACL の裸ホスト表示 = /32）。"""
    t = toks[i]
    if t == "any":
        return 0, 0xFFFFFFFF, i + 1
    if t == "host":
        return _ip(toks[i + 1]), 0, i + 2
    if i + 1 < len(toks) and _looks_ip(toks[i + 1]):
        return _ip(t), _ip(toks[i + 1]), i + 2
    return _ip(t), 0, i + 1


def _port_spec(toks, i):
    """toks[i:] にポート演算子があれば ((op, [値..]), 次位置)、無ければ (None, i)。"""
    if i < len(toks) and toks[i] in ("eq", "neq", "gt", "lt"):
        return (toks[i], [_port(toks[i + 1])]), i + 2
    if i < len(toks) and toks[i] == "range":
        return ("range", [_port(toks[i + 1]), _port(toks[i + 2])]), i + 3
    return None, i


def parse_entry(kind, seq, action, body):
    """1エントリの本文（action の後ろ）をモデル化する。"""
    e = {"seq": seq, "action": action, "proto": None,
         "src": 0, "src_wild": 0xFFFFFFFF, "sport": None,
         "dst": 0, "dst_wild": 0xFFFFFFFF, "dport": None,
         "established": False, "icmp_type": None}
    # 標準 ACL のサブネット表示「A, wildcard bits W」を「A W」へ正規化
    body = body.replace(", wildcard bits ", " ")
    toks = body.split()
    # 末尾の "(N matches)" は呼び出し前に除去済み・"log" はここで無視
    if toks and toks[-1] == "log":
        toks = toks[:-1]
    if kind == "standard":
        e["src"], e["src_wild"], i = _addr_spec(toks, 0)
        if i != len(toks):
            raise AclParseError(f"標準 ACL の余剰トークン: {toks[i:]}")
        return e
    proto = toks[0]
    if proto not in ("ip", "tcp", "udp", "icmp", "gre", "esp", "ospf", "eigrp"):
        raise AclParseError(f"未知のプロトコル: {proto}")
    e["proto"] = proto
    e["src"], e["src_wild"], i = _addr_spec(toks, 1)
    if proto in ("tcp", "udp"):
        e["sport"], i = _port_spec(toks, i)
    e["dst"], e["dst_wild"], i = _addr_spec(toks, i)
    if proto in ("tcp", "udp"):
        e["dport"], i = _port_spec(toks, i)
    while i < len(toks):
        t = toks[i]
        if proto == "tcp" and t == "established":
            e["established"] = True
        elif proto == "icmp" and e["icmp_type"] is None:
            e["icmp_type"] = _icmp(t)
        else:
            raise AclParseError(f"未知の末尾トークン: {t}")
        i += 1
    return e


HEADER_RX = re.compile(r"^(Standard|Extended) IP access list (\S+)\s*$")
ENTRY_RX = re.compile(r"^\s+(\d+)\s+(permit|deny)\s+(.+?)"
                      r"(?:\s+\(\d+ match(?:es)?\))?\s*$")


def parse_show_access_lists(text):
    """show access-lists 出力 → {ACL名: [entry...] (seq昇順)}。"""
    acls, cur_name, cur_kind = {}, None, None
    for line in (text or "").splitlines():
        m = HEADER_RX.match(line.strip()) if not line.startswith(" ") else None
        if m:
            cur_kind, cur_name = m.group(1).lower(), m.group(2)
            acls[cur_name] = []
            continue
        m = ENTRY_RX.match(line)
        if m and cur_name is not None:
            seq, action, body = int(m.group(1)), m.group(2), m.group(3)
            acls[cur_name].append(parse_entry(cur_kind, seq, action, body))
    for name in acls:
        acls[name].sort(key=lambda e: e["seq"])
    return acls


# ---------------------------------------------------------------------------
# 評価（first-match・暗黙deny）
# ---------------------------------------------------------------------------
def _addr_match(base, wild, addr):
    return ((_ip(addr) ^ base) & ~wild & 0xFFFFFFFF) == 0


def _port_match(spec, port):
    if spec is None:
        return True
    op, vals = spec
    if port is None:
        return False
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
    raise AclParseError(f"未知のポート演算子: {op}")


def entry_matches(e, v):
    if e["proto"] is None:                       # 標準 ACL: 送信元のみ
        return _addr_match(e["src"], e["src_wild"], v["src"])
    if e["proto"] != "ip" and e["proto"] != v["proto"]:
        return False
    if not _addr_match(e["src"], e["src_wild"], v["src"]):
        return False
    if not _addr_match(e["dst"], e["dst_wild"], v["dst"]):
        return False
    if not _port_match(e["sport"], v.get("sport")):
        return False
    if not _port_match(e["dport"], v.get("dport")):
        return False
    if e["established"] and not v.get("established"):
        return False
    if e["icmp_type"] is not None and v.get("icmp_type") != e["icmp_type"]:
        return False
    return True


def evaluate(entries, vector):
    """True=permit / False=deny（暗黙deny 込み）。"""
    for e in entries:
        if entry_matches(e, vector):
            return e["action"] == "permit"
    return False


def eval_acl_vectors(spec, stdout):
    """grade.py のチェック種 `acl_vectors:` 本体。
    spec = {"acl": name, "vectors": [{...vector, "expect": "permit"|"deny"}]}
    戻り値: (ok, detail)。"""
    try:
        acls = parse_show_access_lists(stdout)
    except AclParseError as exc:
        return False, {"reason": f"ACL パース失敗: {exc}"}
    name = str(spec["acl"])
    if name not in acls:
        return False, {"reason": f"ACL {name} が存在しない（show 出力に無い）"}
    entries = acls[name]
    mismatches = []
    for v in spec["vectors"]:
        got = "permit" if evaluate(entries, v) else "deny"
        if got != v["expect"]:
            mismatches.append({
                "vector": v.get("id") or _vector_str(v),
                "expected": v["expect"], "observed": got})
    if mismatches:
        return False, {"acl_mismatch": mismatches}
    return True, {}


def _vector_str(v):
    s = f"{v['proto']} {v['src']}"
    if v.get("sport"):
        s += f":{v['sport']}"
    s += f" -> {v['dst']}"
    if v.get("dport"):
        s += f":{v['dport']}"
    if v.get("established"):
        s += " est"
    if v.get("icmp_type") is not None:
        s += f" type{v['icmp_type']}"
    return s
