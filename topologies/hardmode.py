#!/usr/bin/env python3
"""スーパーハードモード部品(BL-210/211)。ラボ生成器が `--hard <comp>` で呼ぶ共通モジュール。

C1 acl_wall(うんざり ACL・BL-210):
  40〜70 行の拡張 ACL(壁)を接点 IF に適用し、主題プロトコルに関わる欠陥を 1 つ埋める。
  正解= **既存行を消さず**、正しい位置(anti-spoof の後・ルータ保護 deny の前)に必要な 1 行を挿入する。
  seq が詰まった世界(gaps=packed)では `ip access-list resequence` が要る。
  採点= acl_model の意味評価(必要フロー permit・元の deny 生存・過剰解の排除)+must_have(元エントリの生存)
        +エントリ数(削除なし・最小変更)。
  設計= problems/_drafts/HARDMODE-COMPONENTS.design.md §2。実測= poc/dmvpn-wreck/README.md(Q1/Q2)。

使い方(生成器側):
    from hardmode import edge_wall, spoke_wall, wall_cfg, wall_fix, wall_check, wall_task_row, wall_readme
    w = edge_wall(rnd, name="EDGE-IN", protect_ip=HUB_NBMA, gw_ip=ISP_IP, peers=[spoke NBMA...],
                  target=("esp", None), defect=None, gaps=None, side=None)
"""
import random
from dataclasses import dataclass, field

import acl_model

DEFECTS = ("missing", "wrong_proto", "narrow", "shadowed")
GAPS = ("normal", "packed")
SIDES = ("in", "both")
# ★IOL 実測(2026-09-21 E2E): Ethernet の **out 方向** IP ACL は ARP フレームまで(ずれた offset で)評価し
#   `deny ip any any` に落とす→ day0 から適用すると ARP が解決できず全断(ARP キャッシュが温かい間だけ動く)。
#   よって out 側の壁は IOL では使わない。`both`= hub の in 壁(欠陥)＋**全 spoke の外側 in 壁(正しい＝囮)**。

DEFECT_DESC = {
    "missing": "必要な permit が無い(壁のどこにも無い)",
    "wrong_proto": "必要な行の代わりに `udp eq 50`(ESP を UDP ポートと勘違いした行)がある",
    "narrow": "必要な行の宛先が 1 つ違う(事業者側のアドレスに写し間違い)",
    "shadowed": "必要な行はあるが、ルータ保護の catch-all deny の**後ろ**にあり食われている"
                "(同一 ACE は重複不可なので、対向を絞った別の行を前に入れる)",
    "none": "欠陥なし(正しい壁= 囮)",
}
GAPS_DESC = {"normal": "seq 10 刻み(挿入できる)",
             "packed": "挿入すべき区間の seq が詰まっている(`ip access-list resequence` が要る)"}
SIDES_DESC = {"in": "hub の外側 in のみ",
              "both": "hub の外側 in(欠陥)＋全 spoke の外側 in(正しい＝囮。IOL は out 側 ACL が ARP を壊すので out 壁は使わない)"}

# 公開網らしいアドレス(ブロックリスト用・198.51.100/203.0.113/192.0.2 は使わない)
_PUB_FIRST = [5, 31, 37, 45, 46, 62, 77, 79, 80, 83, 85, 89, 91, 93, 95, 103, 109, 176, 178,
              185, 188, 193, 194, 195, 212, 213, 217]
ANTI_SPOOF = [
    "deny ip 10.0.0.0 0.255.255.255 any", "deny ip 172.16.0.0 0.15.255.255 any",
    "deny ip 192.168.0.0 0.0.255.255 any", "deny ip 127.0.0.0 0.255.255.255 any",
    "deny ip 0.0.0.0 0.255.255.255 any", "deny ip 169.254.0.0 0.0.255.255 any",
    "deny ip 224.0.0.0 15.255.255.255 any", "deny ip 240.0.0.0 15.255.255.255 any",
]
HYGIENE = [
    "deny tcp any any eq 23", "deny tcp any any eq 445", "deny tcp any any range 135 139",
    "deny tcp any any eq 3389", "deny tcp any any eq 21", "deny tcp any any eq 25",
    "deny udp any any eq 69", "deny udp any any eq 1900", "deny udp any any range 137 138",
    "deny udp any any eq 19", "deny udp any any eq 7", "deny tcp any any range 6000 6063",
    "deny tcp any any eq 1433", "deny tcp any any eq 3306", "deny udp any any eq 5060",
]
ICMP_OK = ["echo", "echo-reply", "unreachable", "time-exceeded"]
NOC, NMS, NTP = "192.0.2.10", "192.0.2.20", "192.0.2.123"


@dataclass
class Wall:
    name: str
    direction: str
    lines: list                      # [(seq, kind, text)]  kind= remark|entry
    defect: str = ""
    gaps: str = "normal"
    side: str = "in"
    protect_ip: str = ""
    needs_line: str = ""             # 挿入すべき正しい 1 行(本文)
    catchall_seq: int = 0            # ルータ保護 deny の seq
    anchor_seq: int = 0              # anti-spoof の最後の seq(この後ろに入れる)
    vectors: list = field(default_factory=list)
    must_have: list = field(default_factory=list)
    theme: str = "edge"              # edge= 外側 in(catch-all の前に入れる) / lan= 収容 IF in(anti-spoof の前に入れる)

    @property
    def entries(self):
        return [(s, t) for s, k, t in self.lines if k == "entry"]

    @property
    def n_entries(self):
        return len(self.entries)


def _pub_ip(rnd):
    return f"{rnd.choice(_PUB_FIRST)}.{rnd.randint(0, 255)}.{rnd.randint(0, 255)}.{rnd.randint(1, 254)}"


def _proto_line(proto, port, protect_ip):
    if proto in ("udp", "tcp"):
        return f"permit {proto} any host {protect_ip} eq {port}"
    return f"permit {proto} any host {protect_ip}"


def _cover(ips):
    """複数の IPv4 を覆う最小の (network, wildcard)。"""
    vals = [acl_model._ip(x) for x in ips]
    bits = 32
    while bits > 0 and len({v >> (32 - bits) for v in vals}) > 1:
        bits -= 1
    wild = (1 << (32 - bits)) - 1
    net = (vals[0] >> (32 - bits)) << (32 - bits) if bits else 0
    f = lambda n: ".".join(str((n >> sh) & 255) for sh in (24, 16, 8, 0))
    return f(net), f(wild)


def _seq_assign(blocks, gaps, packed_from, packed_to):
    """blocks=[(kind,text)...] に seq を振る。packed= [packed_from, packed_to] のインデックス区間を連番にする。"""
    out, seq = [], 0
    for i, (kind, text) in enumerate(blocks):
        if gaps == "packed" and packed_from < i <= packed_to:
            seq += 1
        else:
            seq = (seq // 10 + 1) * 10
        out.append((seq, kind, text))
    return out


def edge_wall(rnd, *, name, protect_ip, gw_ip, peers, target=("esp", None), needs=(),
              defect=None, gaps=None, side=None, ports_named=True):
    """接点 IF(in)の壁= edge_protect テーマ。target= 欠陥にする必要フロー(proto, port)。
    needs= 他の必要フロー(壁に正しく入れる)。peers= 採点で送信元にする対向アドレス。"""
    defect = defect or rnd.choice(DEFECTS)
    gaps = gaps or rnd.choice(GAPS)
    side = side or rnd.choice(SIDES)
    if defect == "none":
        gaps = "normal"
    blocks = [("remark", "=== EDGE PROTECTION (SEC-TEAM) - change via ticket only ==="),
              ("remark", "--- anti-spoofing ---")]
    blocks += [("entry", x) for x in ANTI_SPOOF[:rnd.randint(6, 8)]]
    anchor_idx = len(blocks) - 1
    blocks.append(("remark", f"--- SOC blocklist (updated 2026-0{rnd.randint(1, 9)}-{rnd.randint(10, 28)}) ---"))
    for _ in range(rnd.randint(14, 24)):
        ip = _pub_ip(rnd)
        if rnd.random() < 0.3:
            ip = ".".join(ip.split(".")[:3]) + ".0"
            blocks.append(("entry", f"deny ip {ip} 0.0.0.255 any"))
        else:
            blocks.append(("entry", f"deny ip host {ip} any"))
    blocks.append(("remark", "--- port hygiene ---"))
    hyg = list(HYGIENE)
    rnd.shuffle(hyg)
    blocks += [("entry", x) for x in hyg[:rnd.randint(9, 12)]]
    blocks.append(("remark", "=== VPN (SEC-TEAM) ==="))
    vpn = [_proto_line(p, q, protect_ip) for p, q in needs]
    tline = _proto_line(*target, protect_ip)
    tp, tq = target
    if defect == "missing":
        pass
    elif defect == "none":
        vpn.append(tline)
    elif defect == "wrong_proto":
        vpn.append(f"permit udp any host {protect_ip} eq 50" if tp == "esp"
                   else f"permit {'tcp' if tp == 'udp' else 'udp'} any host {protect_ip} eq {tq}")
    elif defect == "narrow":
        vpn.append(_proto_line(tp, tq, gw_ip))
    elif defect == "shadowed":
        pass                                  # 後で catch-all の後ろに置く
    rnd.shuffle(vpn)
    blocks += [("entry", x) for x in vpn]
    blocks.append(("entry", f"permit gre any host {protect_ip}"))        # 囮(protection 下では不要)
    blocks.append(("remark", "--- ICMP ---"))
    blocks += [("entry", f"permit icmp any host {protect_ip} {t}") for t in ICMP_OK]
    blocks.append(("remark", "--- management (NOC) ---"))
    mg = [f"permit tcp host {NOC} host {protect_ip} eq 22",
          f"permit udp host {NMS} host {protect_ip} eq {'snmp' if ports_named else 161}",
          f"permit udp host {NTP} host {protect_ip} eq {'ntp' if ports_named else 123}"]
    blocks += [("entry", x) for x in mg]
    blocks.append(("remark", "--- router protection ---"))
    blocks.append(("entry", f"deny ip any host {protect_ip} log"))
    catch_idx = len(blocks) - 1
    if defect == "shadowed":
        blocks.append(("entry", tline))
    blocks.append(("entry", "deny ip any any log"))
    lines = _seq_assign(blocks, gaps, anchor_idx, catch_idx)
    if defect == "shadowed":
        # ★IOS は内容が同じ ACE を 2 つ持てない(% Duplicate entry・E2E で発見)。食われている行を消せない
        #   (削除禁止)ので、正解は**対向を絞った別の行**を前に入れる
        net, wild = _cover(peers)
        tline = (f"permit {tp} {net} {wild} host {protect_ip}" if tq is None
                 else f"permit {tp} {net} {wild} host {protect_ip} eq {tq}")
    w = Wall(name=name, direction="in", lines=lines, defect=defect, gaps=gaps, side=side,
             protect_ip=protect_ip, needs_line=tline,
             catchall_seq=lines[catch_idx][0], anchor_seq=lines[anchor_idx][0])
    # 採点ベクタ
    vec = []
    for i, pr in enumerate(peers):
        vec.append({"id": f"need_{tp}_{i}", "proto": tp, "src": pr, "dst": protect_ip,
                    **({"dport": tq, "sport": 500 if tq == 500 else 40000 + i} if tq else {}),
                    "expect": "permit"})
    for p, q in needs:
        vec.append({"id": f"need_{p}{q}", "proto": p, "src": peers[0], "dst": protect_ip,
                    **({"dport": q, "sport": q if q in (500, 4500) else 40001} if q else {}),
                    "expect": "permit"})
    vec += [
        {"id": "spoof", "proto": tp, "src": "10.9.9.9", "dst": protect_ip,
         **({"dport": tq, "sport": 40002} if tq else {}), "expect": "deny"},
        {"id": "broad", "proto": tp, "src": peers[0], "dst": "8.8.4.4",      # 通過 ESP(permit esp any any の過剰解を落とす)
         **({"dport": tq, "sport": 40003} if tq else {}), "expect": "deny"},
        {"id": "telnet", "proto": "tcp", "src": "8.8.4.4", "sport": 40004, "dst": protect_ip,
         "dport": 23, "expect": "deny"},
        {"id": "snmp_out", "proto": "udp", "src": "8.8.4.4", "sport": 40005, "dst": protect_ip,
         "dport": 161, "expect": "deny"},
        {"id": "transit", "proto": "tcp", "src": "8.8.4.4", "sport": 40006, "dst": "10.1.1.1",
         "dport": 80, "expect": "deny"},
    ]
    # ブロックリストの 1 行を活かす
    bl = [t for s_, k, t in lines if k == "entry" and t.startswith("deny ip host ")]
    if bl:
        vec.append({"id": "blocklist", "proto": tp, "src": bl[0].split()[3], "dst": protect_ip,
                    **({"dport": tq, "sport": 40007} if tq else {}), "expect": "deny"})
    w.vectors = vec
    ents = [t for s_, k, t in lines if k == "entry"]
    canary = [x for x in ents if x.startswith("deny ip ") and " any" in x and "host" not in x][:2]
    canary += bl[:2]
    canary += [x for x in ents if x.startswith(("deny tcp", "deny udp"))][:2]
    canary += [f"permit gre any host {protect_ip}", f"deny ip any host {protect_ip} log"]
    w.must_have = canary
    return w


def lan_wall(rnd, *, name, segs, server_ip, dns_ip, defect=None, gaps=None):
    """クライアント収容 IF(in)の壁= guest_access テーマ(BL-210・DHCP 系)。
    target= DHCP ブートストラップ行 `permit udp any eq bootpc any eq bootps`。
    ★本試験形の罠: anti-spoof の `deny ip 0.0.0.0 0.255.255.255 any` が DISCOVER(src 0.0.0.0)を食う
      → 正解は **anti-spoof より前** に 1 行挿入(edge_wall と逆向き)。
    segs= 収容セグメント(例 ["10.5.6", "10.5.7"]・同じ壁を全収容 IF に適用)・server_ip= DHCP サーバ・
    dns_ip= 配布する DNS(壁で udp 53 を許可する先)。"""
    seg = segs[0]
    defect = defect or rnd.choice(DEFECTS)
    gaps = gaps or rnd.choice(GAPS)
    tline = "permit udp any eq bootpc any eq bootps"
    blocks = [("remark", "=== CLIENT SEGMENT POLICY (SEC-TEAM) - change via ticket only ==="),
              ("remark", "--- bootstrap ---")]
    boot = []
    if defect == "missing" or defect == "shadowed":
        pass
    elif defect == "none":
        boot.append(tline)
    elif defect == "wrong_proto":
        boot.append("permit tcp any eq 68 any eq 67")
    elif defect == "narrow":
        boot += [f"permit udp {x}.0 0.0.0.255 eq bootpc any eq bootps" for x in segs]
    blocks += [("entry", x) for x in boot]
    insert_before_idx = len(blocks)               # ここ(anti-spoof の直前)に入れるのが正解
    blocks.append(("remark", "--- anti-spoofing ---"))
    anti = ["deny ip 0.0.0.0 0.255.255.255 any", "deny ip 127.0.0.0 0.255.255.255 any",
            "deny ip 169.254.0.0 0.0.255.255 any", "deny ip 224.0.0.0 15.255.255.255 any"]
    blocks += [("entry", x) for x in anti]
    packed_to_idx = len(blocks) - 1
    if defect == "shadowed":
        blocks.append(("entry", tline))            # anti-spoof の後ろ= 食われる
    blocks.append(("remark", f"--- blocked destinations (SOC list {rnd.randint(2026, 2026)}-0{rnd.randint(1, 9)}) ---"))
    for _ in range(rnd.randint(18, 28)):
        ip = _pub_ip(rnd)
        if rnd.random() < 0.3:
            ip = ".".join(ip.split(".")[:3]) + ".0"
            blocks.append(("entry", f"deny ip any {ip} 0.0.0.255"))
        else:
            blocks.append(("entry", f"deny ip any host {ip}"))
    blocks.append(("remark", "--- guest hygiene ---"))
    hyg = ["deny tcp any any eq 25", "deny tcp any any eq 445", "deny tcp any any range 135 139",
           "deny udp any any range 137 138", "deny tcp any any eq 23", "deny udp any any eq 69",
           "deny tcp any any eq 3389", "deny udp any any eq 1900", "deny tcp any any eq 21"]
    rnd.shuffle(hyg)
    blocks += [("entry", x) for x in hyg[:rnd.randint(8, 9)]]
    blocks.append(("remark", "--- allowed services ---"))
    svc = []
    for x in segs:
        svc += [f"permit udp {x}.0 0.0.0.255 host {dns_ip} eq domain",
                f"permit tcp {x}.0 0.0.0.255 any eq www", f"permit tcp {x}.0 0.0.0.255 any eq 443",
                f"permit udp {x}.0 0.0.0.255 any eq ntp", f"permit tcp {x}.0 0.0.0.255 any eq 8443"]
    rnd.shuffle(svc)
    blocks += [("entry", x) for x in svc]
    blocks.append(("entry", "permit icmp any any"))
    blocks.append(("remark", "--- default ---"))
    blocks.append(("entry", "deny ip any any log"))
    # packed: 先頭〜anti-spoof の末尾まで詰める(挿入先に空き番号が無い)
    lines = _seq_assign(blocks, gaps, 0, packed_to_idx)
    catch_seq = lines[-1][0]
    anti_first_seq = [s_ for s_, k, t in lines if t == anti[0]][0]
    if defect == "shadowed":
        # ★同一 ACE は重複不可 → DISCOVER だけを通す具体版を anti-spoof の前に(更新は既存行で通る)
        tline = "permit udp host 0.0.0.0 eq bootpc host 255.255.255.255 eq bootps"
    w = Wall(name=name, direction="in", lines=lines, defect=defect, gaps=gaps, side="in",
             protect_ip=server_ip, needs_line=tline, catchall_seq=anti_first_seq,
             anchor_seq=lines[insert_before_idx - 1][0], theme="lan")
    w.vectors = [
        {"id": "need_discover", "proto": "udp", "src": "0.0.0.0", "sport": 68,
         "dst": "255.255.255.255", "dport": 67, "expect": "permit"},
        {"id": "need_renew", "proto": "udp", "src": f"{seg}.77", "sport": 68, "dst": server_ip,
         "dport": 67, "expect": "permit"},
        {"id": "icmp", "proto": "icmp", "src": f"{seg}.77", "dst": server_ip, "icmp_type": 8, "expect": "permit"},
        {"id": "dns_ok", "proto": "udp", "src": f"{seg}.77", "sport": 40001, "dst": dns_ip, "dport": 53,
         "expect": "permit"},
        {"id": "spoof", "proto": "udp", "src": "0.0.0.1", "sport": 40002, "dst": server_ip, "dport": 53,
         "expect": "deny"},
        {"id": "telnet", "proto": "tcp", "src": f"{seg}.77", "sport": 40003, "dst": server_ip, "dport": 23,
         "expect": "deny"},
        {"id": "dns_srv", "proto": "udp", "src": f"{seg}.77", "sport": 40004, "dst": server_ip, "dport": 53,
         "expect": "deny"},
        {"id": "smtp", "proto": "tcp", "src": f"{seg}.77", "sport": 40005, "dst": "8.8.4.4", "dport": 25,
         "expect": "deny"},
    ]
    for i, x in enumerate(segs[1:], 1):
        w.vectors.append({"id": f"need_renew{i}", "proto": "udp", "src": f"{x}.77", "sport": 68,
                          "dst": server_ip, "dport": 67, "expect": "permit"})
    bl = [t for s_, k, t in lines if k == "entry" and t.startswith("deny ip any host ")]
    if bl:
        w.vectors.append({"id": "blocklist", "proto": "tcp", "src": f"{seg}.77", "sport": 40006,
                          "dst": bl[0].split()[4], "dport": 443, "expect": "deny"})
    dns_line = [x for x in svc if "eq domain" in x][0]
    w.must_have = anti[:2] + bl[:2] + [x for x in hyg[:2]] + [dns_line, "deny ip any any log"]
    return w


def border_wall(rnd, *, name, me_ip, peer_ip, proto, defect=None, gaps=None):
    """ドメイン境界リンク(in)の壁= border テーマ(BL-210・再配送系)。target= `permit ospf|eigrp any any`。
    ルータ保護の catch-all `deny ip any host ME log` はマルチキャスト hello に当たらないので、
    shadowed では hello は通るのに DBD/Update(unicast)が落ちる= OSPF EXSTART 固着 / EIGRP retry-limit フラップ。
    narrow(`permit proto host PEER host ME`)は hello(224.0.0.x)が落ちて隣接が立たない。"""
    defect = defect or rnd.choice(DEFECTS)
    gaps = gaps or rnd.choice(GAPS)
    mcast = "224.0.0.5" if proto == "ospf" else "224.0.0.10"
    other = "eigrp" if proto == "ospf" else "ospf"
    tline = f"permit {proto} any any"
    blocks = [("remark", "=== DOMAIN BORDER FILTER (SEC-TEAM) - change via ticket only ==="),
              ("remark", "--- anti-spoofing ---")]
    anti = ["deny ip 172.16.0.0 0.15.255.255 any", "deny ip 192.168.0.0 0.0.255.255 any",
            "deny ip 127.0.0.0 0.255.255.255 any", "deny ip 0.0.0.0 0.255.255.255 any",
            "deny ip 169.254.0.0 0.0.255.255 any", "deny ip 240.0.0.0 15.255.255.255 any"]
    blocks += [("entry", x) for x in anti[:rnd.randint(5, 6)]]
    anchor_idx = len(blocks) - 1
    blocks.append(("remark", f"--- SOC blocklist (updated 2026-0{rnd.randint(1, 9)}-{rnd.randint(10, 28)}) ---"))
    for _ in range(rnd.randint(14, 22)):
        ip = _pub_ip(rnd)
        if rnd.random() < 0.3:
            ip = ".".join(ip.split(".")[:3]) + ".0"
            blocks.append(("entry", f"deny ip {ip} 0.0.0.255 any"))
        else:
            blocks.append(("entry", f"deny ip host {ip} any"))
    blocks.append(("remark", "--- port hygiene ---"))
    hyg = list(HYGIENE)
    rnd.shuffle(hyg)
    blocks += [("entry", x) for x in hyg[:rnd.randint(8, 11)]]
    blocks.append(("remark", "=== ROUTING (SEC-TEAM) ==="))
    if defect == "none":
        blocks.append(("entry", tline))
    elif defect == "wrong_proto":
        blocks.append(("entry", f"permit {other} any any"))
    elif defect == "narrow":
        blocks.append(("entry", f"permit {proto} host {peer_ip} host {me_ip}"))
    blocks.append(("entry", f"permit tcp host {peer_ip} host {me_ip} eq bgp"))      # 囮(BGP は無い)
    blocks.append(("remark", "--- router protection ---"))
    blocks += [("entry", f"permit icmp any host {me_ip} echo"), ("entry", f"permit icmp any host {me_ip} echo-reply"),
               ("entry", f"permit tcp host {NOC} host {me_ip} eq 22"),
               ("entry", f"deny ip any host {me_ip} log")]
    catch_idx = len(blocks) - 1
    if defect == "shadowed":
        blocks.append(("entry", tline))
    blocks.append(("remark", "--- transit (tcp/udp/icmp only) ---"))
    # ★transit に `permit ip` を書くと OSPF/EIGRP(proto 89/88)まで通って壁の欠陥が消える → tcp/udp/icmp だけ
    blocks += [("entry", "permit icmp any any"), ("entry", "permit tcp 10.0.0.0 0.255.255.255 any"),
               ("entry", "permit udp 10.0.0.0 0.255.255.255 any")]
    blocks.append(("entry", "deny ip any any log"))
    lines = _seq_assign(blocks, gaps, anchor_idx, catch_idx)
    if defect == "shadowed":
        tline = f"permit {proto} host {peer_ip} host {me_ip}"      # 同一 ACE は重複不可→unicast の具体行
    w = Wall(name=name, direction="in", lines=lines, defect=defect, gaps=gaps, side="in",
             protect_ip=me_ip, needs_line=tline, catchall_seq=lines[catch_idx][0],
             anchor_seq=lines[anchor_idx][0], theme="border")
    w.vectors = [
        {"id": f"need_{proto}_uni", "proto": proto, "src": peer_ip, "dst": me_ip, "expect": "permit"},
        {"id": f"need_{proto}_mcast", "proto": proto, "src": peer_ip, "dst": mcast, "expect": "permit"},
        {"id": "telnet", "proto": "tcp", "src": peer_ip, "sport": 40001, "dst": me_ip, "dport": 23, "expect": "deny"},
        {"id": "spoof", "proto": proto, "src": "0.0.0.1", "dst": me_ip, "expect": "deny"},
        {"id": "transit_ok", "proto": "icmp", "src": "10.5.5.1", "dst": "2.2.2.2", "icmp_type": 8, "expect": "permit"},
        {"id": "transit_deny", "proto": "tcp", "src": "8.8.4.4", "sport": 40002, "dst": "1.1.1.1", "dport": 80,
         "expect": "deny"},
    ]
    bl = [t for s_, k, t in lines if k == "entry" and t.startswith("deny ip host ")]
    if bl:
        w.vectors.append({"id": "blocklist", "proto": proto, "src": bl[0].split()[3], "dst": me_ip, "expect": "deny"})
    w.must_have = anti[:2] + bl[:2] + hyg[:2] + [f"deny ip any host {me_ip} log", "deny ip any any log"]
    return w


def spoke_wall(rnd, *, name, protect_ip, gw_ip, peers):
    """spoke の外側 in の壁= 正しい(囮)。hub 壁と同じ骨格・別の埋め草。"""
    return edge_wall(rnd, name=name, protect_ip=protect_ip, gw_ip=gw_ip, peers=peers,
                     target=("esp", None), needs=(("udp", 500), ("udp", 4500)),
                     defect="none", gaps="normal", side="in")


# ---------------------------------------------------------------- C2 打ちづらい識別子 / C3 囮の類似名(BL-211)
_CONFUSE = {"O": "0", "o": "0", "l": "1", "I": "1", "S": "5", "B": "8", "Z": "2"}


def _mix(rnd, word, p_conf=0.35):
    """大小混在＋紛らわしい字への置換(l→1・O→0 等)。? や空白は使わない。"""
    out = []
    for ch in word:
        c = ch.upper() if rnd.random() < 0.5 else ch.lower()
        if c in _CONFUSE and rnd.random() < p_conf:
            c = _CONFUSE[c]
        out.append(c)
    return "".join(out)


def hostile_names(rnd):
    """C2: 打ちづらい名前一式(IOS が受理する文字だけ= 英数と - _ . #)。nhrp_key は 8 文字ちょうど。"""
    sep = rnd.choice(["-", "_", "."])
    n = rnd.randint(1, 9)
    return {
        "prof": f"{_mix(rnd, 'IPsec')}{sep}{_mix(rnd, 'Prof')}{sep}{_mix(rnd, 'DmVPN')}{n}",
        "ts": f"{_mix(rnd, 'Ts')}{sep}{_mix(rnd, 'aes256')}{sep}{_mix(rnd, 'Sha2')}.v{n}",
        "acl": f"{_mix(rnd, 'Sec')}_{_mix(rnd, 'Edge')}-{_mix(rnd, 'IN')}.v{rnd.randint(1, 9)}",
        "psk": f"{_mix(rnd, 'pReshared')}-{_mix(rnd, 'Key')}#{rnd.randint(10, 99)}",
        "nhrp_key": f"{_mix(rnd, 'nHrP')}-{rnd.choice('kK')}{rnd.randint(10, 99)}",
    }


def similar_names(rnd, name, n):
    """C3: name に似た別名を n 個(1 文字違い・区切り違い・接尾辞)。name 自身とは必ず違う。"""
    cands = []
    for i, ch in enumerate(name):
        if ch in _CONFUSE:
            cands.append(name[:i] + _CONFUSE[ch] + name[i + 1:])
    cands += [name.replace("-", "_", 1), name.replace("_", "-", 1), name.replace(".", "-", 1),
              name + "-OLD", name + "1", name + "-BAK", name.lower() if name != name.lower() else name.upper(),
              name[:-1] + ("0" if name[-1] != "0" else "1") if name[-1].isdigit() else name + "2"]
    seen, out = {name}, []
    rnd.shuffle(cands)
    for c in cands:
        if c not in seen and " " not in c:
            seen.add(c)
            out.append(c)
        if len(out) == n:
            break
    return out


# ---------------------------------------------------------------- C5 設定ノイズ(BL-211)
def noise_lines(rnd, n_target=120, node_idx=0):
    """無害な設定を n_target 行前後。ルーティングに載らないアドレス(192.0.2.x・100.64.x.x)だけを使う。
    IF・vty・SNMP・NTP など運用に触るものは入れない(採点・SSH を壊さない)。
    ★Loopback の IP は**ノードごとに別**(node_idx)。同じ IP を全ノードに置くと、明示 router-id の無い
      EIGRP/OSPF がそれを RID に選び **RID 重複で経路が捨てられる**(E2E で発見)。生成器側は router-id を明示すること。"""
    L = []
    k = rnd.randint(6, 10)
    base = 16 * node_idx
    for i in range(k):
        L += [f"interface Loopback{100 + i}",
              f" description === LEGACY: {rnd.choice(['MPLS PE', 'old NMS probe', 'IPsla source', 'BGP RR', 'test'])} (decom 2025) ===",
              f" ip address 192.0.2.{100 + base + i} 255.255.255.255", "!"]
    L += ["class-map match-any CM-VOICE", " match dscp ef", " match dscp cs5", "!",
          "class-map match-any CM-VIDEO", " match dscp af41", " match dscp af42", "!",
          "class-map match-all CM-SCAVENGER", " match dscp cs1", "!",
          "policy-map PM-WAN-OUT", " class CM-VOICE", "  priority percent 10", " class CM-VIDEO",
          "  bandwidth percent 20", " class CM-SCAVENGER", "  bandwidth percent 1",
          " class class-default", "  fair-queue", "!"]
    for i in range(rnd.randint(8, 14)):
        L.append(f"ip route 100.64.{rnd.randint(0, 63)}.0 255.255.255.0 Null0 name DECOM-{rnd.randint(100, 999)}")
    L.append("!")
    L += ["ip prefix-list PL-LEGACY-SUMMARY seq 5 permit 100.64.0.0/10 le 24", "!",
          "ip access-list standard MGMT-HOSTS-OLD"] + \
         [f" permit 192.0.2.{rnd.randint(1, 99)}" for _ in range(rnd.randint(4, 8))] + ["!",
          "ip access-list extended NMS-POLL-OLD",
          " permit udp host 192.0.2.20 any eq snmp", " permit udp host 192.0.2.21 any eq snmp",
          " permit icmp host 192.0.2.20 any", "!",
          "route-map RM-LEGACY-OUT deny 10", " match ip address prefix-list PL-LEGACY-SUMMARY", "!",
          "route-map RM-LEGACY-OUT permit 20", "!",
          "ip sla 900", " icmp-echo 192.0.2.200 source-ip 192.0.2.100", " frequency 300", "!",
          "track 900 ip sla 900 reachability", "!",
          "ip domain list corp.example", "ip domain list legacy.example", "!"]
    j = 0
    while len(L) < n_target:
        L += [f"interface Loopback{200 + j}",
              " description === LEGACY: unused ===", f" ip address 100.127.{node_idx}.{j + 1} 255.255.255.255", "!"]
        j += 1
    return L


# ---------------------------------------------------------------- 出力
def wall_cfg(w):
    L = [f"ip access-list extended {w.name}"]
    for seq, kind, text in w.lines:
        L.append(f" {seq} {'remark ' if kind == 'remark' else ''}{text}")
    L.append("!")
    return L


def wall_apply(w):
    return f" ip access-group {w.name} {w.direction}"


def insert_seq(w):
    """正しい挿入位置の seq(normal)。packed なら resequence 後の位置を返す。"""
    if w.gaps == "normal":
        return w.catchall_seq - 5
    # ★resequence 10 10 後: **remark は消える**(IOL 17.15 実測・Q2)ので、エントリだけの位置 × 10
    pos = [i for i, (s_, t) in enumerate(w.entries) if s_ == w.catchall_seq][0] + 1
    return pos * 10 - 5


def wall_fix(w, node):
    fixes = []
    if w.gaps == "packed":
        fixes.append({"node": node, "lines": [f"ip access-list resequence {w.name} 10 10"], "match": "none"})
    fixes.append({"node": node, "parents": [f"ip access-list extended {w.name}"],
                  "lines": [f"{insert_seq(w)} {w.needs_line}"], "match": "none"})
    return fixes


def wall_check(w, node, points, name=None):
    return {"name": name or f"{node}: {w.name} が保全され(削除・置換なし)、必要な通信だけが追加で許可されている",
            "node": node, "command": f"show ip access-lists {w.name}",
            "acl_vectors": {"acl": w.name, "vectors": w.vectors, "must_have": w.must_have,
                            "min_entries": w.n_entries, "max_entries": w.n_entries + 2},
            "points": points}


def wall_task_row(w_in, spokes_too=False):
    """設定仕様書の行(Cisco 語)。壁の中身・欠陥は書かない。"""
    where = ("すべての拠点の外側のインターフェイスの着信に" if spokes_too
             else "本社の外側のインターフェイスの着信に")
    return (f"| 外側の保護 | {where}、アクセス リスト `{w_in.name}` が、セキュリティ チームによって管理され、"
            "適用されているところのものです。これらのアクセス リストのエントリは、削除、変更、または無効化されては"
            "なりません。必要とされる変更は、エントリの追加によってのみ、行われることができます。 |")


def wall_readme(w):
    if w.defect == "none":
        return f"- 囮の壁 `{w.name}`({w.direction}・{w.n_entries} エントリ・正しい。触る必要なし)\n"
    if w.theme == "lan":
        where = (f"先頭の remark(seq {w.anchor_seq})の後・anti-spoof の先頭 `deny ip 0.0.0.0 0.255.255.255 any`"
                 f"(seq {w.catchall_seq})の**前**に挿入")
        seen = ("CL の DISCOVER(src 0.0.0.0)だけが落ちる(更新は通る)。壁の `deny ip 0.0.0.0 0.255.255.255 any` の"
                "カウンタだけが増える(log 無しなのでログには出ない)")
        desc = DEFECT_DESC[w.defect].replace("ルータ保護の catch-all deny", "anti-spoof の deny")
    elif w.theme == "border":
        where = f"anti-spoof(seq {w.anchor_seq})の後・ルータ保護 deny(seq {w.catchall_seq})の前に挿入"
        seen = ("missing/wrong_proto/narrow= 隣接が立たない(hello 224.0.0.x が落ちる・narrow は unicast 行だけ)/ "
                "shadowed= hello は通るのに unicast(DBD/Update)が catch-all に落ちる= OSPF EXSTART 固着・EIGRP retry limit。"
                f"ログ `%SEC-6-IPACCESSLOGNP: list {w.name} denied 89|88 <peer> -> {w.protect_ip}`")
        desc = DEFECT_DESC[w.defect]
    else:
        where = f"anti-spoof(seq {w.anchor_seq})の後・ルータ保護 deny(seq {w.catchall_seq})の前に挿入"
        seen = ("ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・"
                f"hub ログ `%SEC-6-IPACCESSLOGNP: list {w.name} denied 50 <spoke> -> {w.protect_ip}`")
        desc = DEFECT_DESC[w.defect]
    return (f"- 壁 `{w.name}`({w.direction}・{w.n_entries} エントリ): 欠陥= `{w.defect}`({desc})"
            f" / seq= {w.gaps}({GAPS_DESC[w.gaps]}) / 世界= {w.side}({SIDES_DESC[w.side]})\n"
            f"  - 正解= `{w.needs_line}` を {where}"
            + (f"(seq が詰まっているので `ip access-list resequence {w.name} 10 10` → seq {insert_seq(w)}。"
               "★IOL では resequence で remark が消える)"
               if w.gaps == "packed" else f"(例: seq {insert_seq(w)})") + "\n"
            f"  - 見え方: {seen}\n")


# ---------------------------------------------------------------- selftest
def _apply_fix_text(w):
    """fix を適用した後の壁の show 相当テキスト(意味評価用)。"""
    if w.gaps == "packed":
        # resequence 10 10: remark は消え、エントリだけが位置 × 10 に renumber される(Q2 で実測)
        ents = [((i + 1) * 10, t) for i, (s_, t) in enumerate(w.entries)]
    else:
        ents = [(s_, t) for s_, k, t in w.lines if k == "entry"]
    ents.append((insert_seq(w), w.needs_line))
    ents.sort()
    return f"Extended IP access list {w.name}\n" + "\n".join(f"    {s_} {t}" for s_, t in ents) + "\n"


def _show_text(w):
    return f"Extended IP access list {w.name}\n" + "\n".join(f"    {s_} {t}" for s_, t in w.entries) + "\n"


def selftest(n=300):
    for seed in range(200):
        rnd = random.Random(seed)
        h = hostile_names(rnd)
        assert len(h["nhrp_key"]) == 8, h
        assert all("?" not in x and " " not in x and not x.startswith("!") for x in h.values()), h
        sims = similar_names(rnd, h["prof"], 3)
        assert len(sims) == 3 and h["prof"] not in sims and len(set(sims)) == 3, (h, sims)
    bad = 0
    for seed in range(n):
        rnd = random.Random(seed)
        for defect in DEFECTS:
            for gaps in GAPS:
                w = edge_wall(rnd, name="X", protect_ip="203.0.113.2", gw_ip="203.0.113.1",
                              peers=["198.51.100.2", "198.51.100.6", "198.51.100.10"],
                              target=("esp", None), needs=(("udp", 500), ("udp", 4500)),
                              defect=defect, gaps=gaps)
                spec = wall_check(w, "RT01", 10)["acl_vectors"]
                # 壊れた壁: 必要フロー(esp)だけが落ち、他(deny 群・udp 500)は満たす
                ok, det = acl_model.eval_acl_vectors(spec, _show_text(w))
                assert not ok, (seed, defect, gaps, "欠陥なのに PASS")
                mm = {m["vector"] for m in det.get("acl_mismatch", [])}
                assert mm and all(v.startswith("need_esp") for v in mm), (seed, defect, gaps, det)
                # 正解を挿入: 全部満たす
                ok, det = acl_model.eval_acl_vectors(spec, _apply_fix_text(w))
                assert ok, (seed, defect, gaps, det)
                # 過剰解(permit ip any any を先頭に)は落ちる
                over = "Extended IP access list X\n    5 permit ip any any\n" + _show_text(w).split("\n", 1)[1]
                ok, _ = acl_model.eval_acl_vectors(spec, over)
                assert not ok, (seed, defect, gaps, "過剰解が PASS")
                # anti-spoof の前(seq 5)に permit esp any を入れる= spoof ベクタで落ちる
                early = ("Extended IP access list X\n    5 permit esp any host 203.0.113.2\n"
                         + _show_text(w).split("\n", 1)[1])
                ok, det = acl_model.eval_acl_vectors(spec, early)
                assert not ok and "spoof" in {m["vector"] for m in det.get("acl_mismatch", [])}, (seed, defect, gaps)
                # 削除(catch-all を消す)は落ちる
                cut = _apply_fix_text(w).replace(f"deny ip any host 203.0.113.2 log\n", "")
                ok, _ = acl_model.eval_acl_vectors(spec, cut)
                assert not ok, (seed, defect, gaps, "削除が PASS")
                assert 40 <= w.n_entries <= 70, (seed, w.n_entries)
        for defect in DEFECTS:
            for gaps in GAPS:
                lw = lan_wall(rnd, name="G-DHCP-ONLY", segs=["10.5.6", "10.5.7"], server_ip="10.5.8.1",
                              dns_ip="198.51.100.53", defect=defect, gaps=gaps)
                spec = wall_check(lw, "RT02", 10)["acl_vectors"]
                ok, det = acl_model.eval_acl_vectors(spec, _show_text(lw))
                assert not ok, (seed, defect, gaps, "lan 欠陥なのに PASS")
                mm = {m["vector"] for m in det.get("acl_mismatch", [])}
                assert mm <= {"need_discover", "need_renew", "need_renew1"} and "need_discover" in mm, (seed, defect, gaps, det)
                ok, det = acl_model.eval_acl_vectors(spec, _apply_fix_text(lw))
                assert ok, (seed, defect, gaps, det)
                # anti-spoof の後ろに入れた(=位置違い)は need_discover で落ちる
                ents = list(lw.entries) + [(lw.catchall_seq + 3, lw.needs_line)]
                ents.sort()
                late = f"Extended IP access list {lw.name}\n" + "\n".join(f"    {a} {b}" for a, b in ents) + "\n"
                ok, det = acl_model.eval_acl_vectors(spec, late)
                assert not ok and "need_discover" in {m["vector"] for m in det.get("acl_mismatch", [])}, (seed, defect, gaps, det)
                assert 36 <= lw.n_entries <= 60, (seed, lw.n_entries)
        for proto in ("ospf", "eigrp"):
            for defect in DEFECTS:
                for gaps in GAPS:
                    bw = border_wall(rnd, name="BORDER-IN", me_ip="10.7.8.1", peer_ip="10.7.8.2", proto=proto,
                                     defect=defect, gaps=gaps)
                    spec = wall_check(bw, "RT01", 8)["acl_vectors"]
                    ok, det = acl_model.eval_acl_vectors(spec, _show_text(bw))
                    assert not ok, (seed, proto, defect, gaps, "border 欠陥なのに PASS")
                    mm = {m["vector"] for m in det.get("acl_mismatch", [])}
                    assert mm and all(v.startswith("need_") for v in mm), (seed, proto, defect, gaps, det)
                    ok, det = acl_model.eval_acl_vectors(spec, _apply_fix_text(bw))
                    assert ok, (seed, proto, defect, gaps, det)
                    assert 36 <= bw.n_entries <= 60, (seed, bw.n_entries)
        sw = spoke_wall(rnd, name="EDGE-IN", protect_ip="198.51.100.2", gw_ip="198.51.100.1",
                        peers=["203.0.113.2", "198.51.100.6"])
        ok, det = acl_model.eval_acl_vectors(wall_check(sw, "RT02", 1)["acl_vectors"], _show_text(sw))
        assert ok, ("spoke wall が正しくない", seed, det)
    print(f"hardmode selftest OK: {n} seeds × {len(DEFECTS)} defects × {len(GAPS)} gaps")


if __name__ == "__main__":
    selftest()
