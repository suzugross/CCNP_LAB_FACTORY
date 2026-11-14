#!/usr/bin/env python3
"""ルーティング経路づくり(BL-271)の経路の計算器。IOS の決まりどおりに経路表を作り、パケットを流す。

ゲーム(route_path.py)・画面・PoC はすべてここだけで計算する(stp_model と同じ位置づけ)。

  経路表(rib):
    - up のインターフェースの connected(C・AD 0)と local(L・/32)。/32 のインターフェース(ループバック)は C だけ。
    - static(S・既定 AD 1)は次の行き先(next-hop)が解決できるときだけ入る。next-hop を経路表で引き、
      connected に行き着けば解決(隣でない next-hop は再帰で解決)。Null0 宛ては常に入る。
      自分の宛先と同じプレフィックスの行では解決しない(自分で自分を支えない)。
    - 同じ宛先に複数の static: AD の小さいものだけが入る(フローティング)。同じ AD なら全部(ECMP)。
    - 同じ宛先の connected と static: connected が勝つ(AD 0)。
  転送(decide / trace):
    - 宛先に当てはまる行のうちプレフィックスが一番長いもの(AD は同じ宛先の中でだけ比べる)。
    - connected の LAN に当たれば端末へ(その IP の端末が無ければ ARP が返らず落ちる= nohost)。
    - 当たる行が無い= noroute。Null0 = null0。同じルータへ戻った= loop(TTL が尽きて落ちる)。
    - ECMP は道が分かれる(trace は道の一覧を返す)。
  障害: down に入れたリンクの両端のインターフェースが down → connected が消え、その IP を next-hop にした static が外れる。

  実機での照合(poc/route/README.md・IOL iol-xe 17.15.1・2026-11-12)で決めた点:
    - next-hop はデフォルト経路だけでは解決しない(VIA_DEFAULT = False。表に入らず、転送はほかの行で行われる)
    - Null0 の行を通る再帰は解決する(表に入る)。転送は Null0 で捨てる
    - ECMP の via は next-hop の IP の降順に並ぶ(show ip route の表示)
    - 「is subnetted」(マスク 1 種類)の段では、行にマスクを書かない

  python3 topologies/route_model.py selftest

設計= problems/_drafts/ROUTE-PATH.design.md §4。
"""
from __future__ import annotations

import functools
import ipaddress
import re
import sys

AD_STATIC = 1
MAXROUND = 8
VIA_DEFAULT = False            # 再帰の解決にデフォルト経路を使わない(PoC 3b: IOL 17.15 で non-active [N] のまま)


@functools.lru_cache(maxsize=65536)
def net(p):
    return ipaddress.ip_network(p, strict=False)        # 同じ文字列を何度も解析しないように覚えておく(探索で何万回も呼ぶ)


@functools.lru_cache(maxsize=65536)
def addr(ip):
    return ipaddress.ip_address(ip)


def mask_of(p):
    return str(net(p).netmask)


def rnum(name):
    m = re.search(r"(\d+)$", name)
    return int(m.group(1)) if m else 0


# ==========================================================================
# 盤面の組み立て(アドレスの決まり・設計 §3)
# ==========================================================================
def build_net(routers, links, lans, lo=False):
    """
    routers: [{"name": "R1", "site": 1, "fixed": False}, …]
    links:   [{"a": "R1", "b": "R2"} …]  prefix を省くと 172.16.XY.0/30(X < Y・X 側が .1)
    lans:    [{"router": "R1", "k": 1, "hosts": [{"name": "PC1", "kind": "pc"}, …]} …]
             prefix を省くと 10.<site>.<k>.0/24・ゲートウェイは .1・端末は pc= .10 から・srv= .100 から
    lo:      True ならルータごとにループバック 10.255.0.N/32
    戻り値は JSON にできる dict(routers・links・lans)。インターフェースは LAN が先(Gi0/0 …)、次にリンクの順。
    """
    R = {r["name"]: {"site": r.get("site", rnum(r["name"])), "fixed": bool(r.get("fixed")),
                     "label": r.get("label"), "ifs": [], "lo": None} for r in routers}

    def add_if(rname, ip, plen, to, link=None):
        ifs = R[rname]["ifs"]
        name = "Gi0/%d" % len(ifs)
        ifs.append({"name": name, "ip": ip, "plen": plen, "to": to, "link": link})
        return name

    out_lans = []
    for ln in lans:
        r = ln["router"]
        site = R[r]["site"]
        p = net(ln.get("prefix") or "10.%d.%d.0/24" % (site, ln.get("k", 1)))
        base = int(p.network_address)
        gw = str(ipaddress.ip_address(base + 1))
        lid = ln.get("id") or "%s-%d" % (r, ln.get("k", 1))
        ifn = add_if(r, gw, p.prefixlen, "LAN:" + lid)
        hosts, npc, nsrv = [], 10, 100
        for h in ln.get("hosts", []):
            if h.get("ip"):
                ip = h["ip"]
            elif h.get("kind") == "srv":
                ip = str(ipaddress.ip_address(base + nsrv))
                nsrv += 1
            else:
                ip = str(ipaddress.ip_address(base + npc))
                npc += 1
            hosts.append({"name": h["name"], "ip": ip, "kind": h.get("kind", "pc"), "gw": h.get("gw") or gw})
        out_lans.append({"id": lid, "router": r, "prefix": str(p), "gw": gw, "if": ifn, "hosts": hosts,
                         "label": ln.get("label")})
    out_links = []
    for i, lk in enumerate(links):
        a, b = lk["a"], lk["b"]
        if lk.get("prefix"):
            p = net(lk["prefix"])
            ipa = lk.get("ipa") or str(ipaddress.ip_address(int(p.network_address) + 1))
            ipb = lk.get("ipb") or str(ipaddress.ip_address(int(p.network_address) + 2))
        else:
            x, y = sorted((rnum(a), rnum(b)))
            p = net("172.16.%d%d.0/30" % (x, y))
            lo_ip = str(ipaddress.ip_address(int(p.network_address) + 1))
            hi_ip = str(ipaddress.ip_address(int(p.network_address) + 2))
            ipa, ipb = (lo_ip, hi_ip) if rnum(a) < rnum(b) else (hi_ip, lo_ip)
        ia = add_if(a, ipa, p.prefixlen, b, i)
        ib = add_if(b, ipb, p.prefixlen, a, i)
        out_links.append({"a": a, "b": b, "prefix": str(p), "ipa": ipa, "ipb": ipb, "ia": ia, "ib": ib})
    if lo:
        for name, r in R.items():
            r["lo"] = "10.255.0.%d" % rnum(name)
    return {"routers": R, "links": out_links, "lans": out_lans}


# ==========================================================================
# 索引(盤面ごとに 1 回)
# ==========================================================================
class Index:
    def __init__(self, nw):
        self.nw = nw
        self.owner = {}                     # IP → (ルータ, IF)   ルータのインターフェースの IP(設計どおりの値)
        self.host = {}                      # IP → (端末名, LAN id, ルータ)
        self.hinfo = {}                     # IP → 端末(name・ip・kind・gw)
        self.hostname = {}                  # 端末名 → IP
        self.lan_of = {}                    # LAN id → LAN
        for rname, r in nw["routers"].items():
            for i in r["ifs"]:
                self.owner[i["ip"]] = (rname, i["name"])
            if r.get("lo"):
                self.owner[r["lo"]] = (rname, "Loopback0")
        for ln in nw["lans"]:
            self.lan_of[ln["id"]] = ln
            for h in ln["hosts"]:
                self.host[h["ip"]] = (h["name"], ln["id"], ln["router"])
                self.hinfo[h["ip"]] = h
                self.hostname[h["name"]] = h["ip"]
        self.neighbors = {r: [] for r in nw["routers"]}     # ルータ → [(隣, 自分の IF, 隣の IP, リンク番号)]
        for k, lk in enumerate(nw["links"]):
            self.neighbors[lk["a"]].append((lk["b"], lk["ia"], lk["ipb"], k))
            self.neighbors[lk["b"]].append((lk["a"], lk["ib"], lk["ipa"], k))

    def gateway_of(self, host_ip):
        return self.host[host_ip][2]

    def ip_of(self, host):
        return self.hostname[host]

    def iface(self, r, name):
        return next(i for i in self.nw["routers"][r]["ifs"] if i["name"] == name)


def seg_of(i):
    """インターフェースのつながる区間: LAN は "LAN:<id>"、リンクは "L:<番号>"。"""
    return i["to"] if i["link"] is None else "L:%d" % i["link"]


class Eff:
    """インターフェースの実際の状態。設定の上書き(ifs)・shutdown・リンク断(down)を反映する。
    ifs= {ルータ: {IF 名: {"ip": "10.2.1.1/24" か None(IP なし), "shut": bool}}}(書いた項目だけ上書き)。
    リンク(ルータどうしの直結)は、どちらかの端が shutdown か down に入っていれば両端とも down(実機の直結と同じ)。
    LAN 側はスイッチを挟む想定なので、そのインターフェースだけが down。"""
    def __init__(self, ix, ifs=None, down=()):
        self.ix = ix
        self.ifs = {}
        down = set(down)
        ifs = ifs or {}
        dead = set(down)
        for r, R in ix.nw["routers"].items():
            for i in R["ifs"]:
                o = ifs.get(r, {}).get(i["name"], {})
                ip, plen = i["ip"], i["plen"]
                if "ip" in o:
                    if o["ip"]:
                        q = ipaddress.ip_interface(o["ip"])
                        ip, plen = str(q.ip), q.network.prefixlen
                    else:
                        ip = None
                shut = bool(o.get("shut", False))
                self.ifs[(r, i["name"])] = {"ip": ip, "plen": plen, "shut": shut, "seg": seg_of(i), "link": i["link"]}
                if shut and i["link"] is not None:
                    dead.add(i["link"])
        for v in self.ifs.values():
            v["up"] = not v["shut"] and not (v["link"] is not None and v["link"] in dead)
        self.seg_owner = {}                 # 区間 → {IP: ("router", ルータ) / ("host", 端末)}
        for (r, n), v in self.ifs.items():
            if v["up"] and v["ip"]:
                self.seg_owner.setdefault(v["seg"], {})[v["ip"]] = ("router", r)
        for ln in ix.nw["lans"]:
            for h in ln["hosts"]:
                self.seg_owner.setdefault("LAN:" + ln["id"], {})[h["ip"]] = ("host", h["name"])

    def owner(self, seg, ip):
        return self.seg_owner.get(seg, {}).get(ip)


def overlaps(ix, ifs, r):
    """ルータ r のインターフェースどうしでサブネットが重なる組 [(IF, IF)]。IOS はこの設定を受け付けない
    (shutdown のインターフェースとも比べる)。"""
    eff = Eff(ix, ifs)
    nets = [(n, net("%s/%d" % (v["ip"], v["plen"]))) for (rr, n), v in eff.ifs.items() if rr == r and v["ip"]]
    lo = ix.nw["routers"][r].get("lo")
    if lo:
        nets.append(("Loopback0", net(lo + "/32")))
    out = []
    for x in range(len(nets)):
        for y in range(x + 1, len(nets)):
            if nets[x][1].overlaps(nets[y][1]):
                out.append((nets[x][0], nets[y][0]))
    return out


# ==========================================================================
# 経路表
# ==========================================================================
def _lpm(rows, ip, skip_prefix=None):
    a = addr(ip)
    best = None
    for row in rows:
        p = row["net"]
        if a in p and p != skip_prefix and (best is None or p.prefixlen > best["net"].prefixlen):
            best = row
    return best


def _resolve(eff, rows, nh, own):
    """next-hop を経路表で引いて、直接つながった次の行き先の一覧 [(nh, out, 隣)] を返す。解決できなければ None。
    own= その static 自身の宛先(この行では解決しない)。隣= その IP を持つルータ(いなければ None= ARP が返らない)。"""
    row = _lpm(rows, nh, skip_prefix=own)
    if row is None or row["code"] == "L":
        return None
    if row["code"] == "C":
        if row["out"] == "Loopback0":
            return None
        o = eff.owner(row["seg"], nh)
        return [(nh, row["out"], o[1] if o and o[0] == "router" else None)]
    if row["net"].prefixlen == 0 and not VIA_DEFAULT:
        return None
    if any(x[1] == "Null0" for x in row["res"]):
        return [(None, "Null0", None)]              # 表に入り、転送は Null0 で捨てる
    return row["res"] or None


def rib(ix, r, routes, down=(), eff=None):
    """ルータ r の経路表。routes= そのルータの static の一覧 [{"p","nh","ad"}]。down= 落ちたリンクの番号。
    eff= インターフェースの実際の状態(省くと設計どおりの IP・全部 up・down だけ反映)。
    戻り値 {"rows": [行], "skipped": [{"i", "why"}], "eff": eff}。
    行= {"net", "p", "code"(C/L/S), "ad", "out"(C/L), "seg"(C/L), "via": [設定の next-hop(S)], "res": [(nh, out, 隣)],
         "rid": [static の番号]}"""
    if eff is None:
        eff = Eff(ix, None, down)
    R = ix.nw["routers"][r]
    conn = []
    for i in R["ifs"]:
        v = eff.ifs[(r, i["name"])]
        if not v["up"] or not v["ip"]:
            continue
        p = net("%s/%d" % (v["ip"], v["plen"]))
        conn.append({"net": p, "p": str(p), "code": "C", "ad": 0, "out": i["name"], "seg": v["seg"],
                     "res": [], "via": [], "rid": []})
        if p.prefixlen < 32:
            q = net(v["ip"] + "/32")
            conn.append({"net": q, "p": str(q), "code": "L", "ad": 0, "out": i["name"], "seg": v["seg"],
                         "res": [], "via": [], "rid": []})
    if R.get("lo"):
        q = net(R["lo"] + "/32")
        conn.append({"net": q, "p": str(q), "code": "C", "ad": 0, "out": "Loopback0", "seg": None,
                     "res": [], "via": [], "rid": []})
    cnets = {row["net"] for row in conn}
    sts = [(k, net(s["p"]), s.get("nh", "Null0"), int(s.get("ad", AD_STATIC))) for k, s in enumerate(routes)]

    rows = list(conn)
    skipped = {}
    for _ in range(MAXROUND):
        cand = {}
        why = {}
        for k, p, nh, ad in sts:
            if ad >= 255:
                why[k] = "ad255"                # AD 255 は設定に入るが表には入らない(PoC input_form #6・公式)
                continue
            if p in cnets:
                why[k] = "connected"
                continue
            if nh == "Null0":
                res = [(None, "Null0", None)]
            else:
                res = _resolve(eff, rows, nh, p)
                if res is None:
                    why[k] = "unresolved"
                    continue
            cand.setdefault(p, []).append((ad, k, nh, res))
        new = list(conn)
        for p, lst in cand.items():
            best = min(x[0] for x in lst)
            win = [x for x in lst if x[0] == best]
            for x in lst:
                if x[0] != best:
                    why[x[1]] = "worse_ad"
            res, via = [], []
            win.sort(key=lambda x: (x[2] == "Null0", -int(addr(x[2])) if x[2] != "Null0" else 0))
            for _, k, nh, rr in win:
                via.append(nh)
                for y in rr:
                    if y not in res:
                        res.append(y)
            new.append({"net": p, "p": str(p), "code": "S", "ad": best, "out": None, "seg": None, "via": via,
                        "res": res, "rid": [x[1] for x in win]})
        if _same(new, rows):
            rows, skipped = new, why
            break
        rows, skipped = new, why
    rows.sort(key=lambda x: (int(x["net"].network_address), x["net"].prefixlen))
    return {"rows": rows, "skipped": [{"i": k, "why": w} for k, w in sorted(skipped.items())], "eff": eff}


def _same(a, b):
    def sig(rows):
        return sorted((str(x["net"]), x["code"], x["ad"], tuple(x["res"])) for x in rows)
    return sig(a) == sig(b)


def tables(ix, cfg, down=(), ifs=None):
    """全ルータの経路表。cfg= {ルータ: [static …]}。ifs= インターフェースの設定の上書き(Eff を見よ)。"""
    eff = Eff(ix, ifs, down)
    return {r: rib(ix, r, cfg.get(r, []), down, eff) for r in ix.nw["routers"]}


# ==========================================================================
# 転送
# ==========================================================================
def matches(table, ip):
    """宛先 ip に当てはまる行(長い順)。先頭が選ばれる行。"""
    a = addr(ip)
    return sorted([x for x in table["rows"] if a in x["net"]], key=lambda x: -x["net"].prefixlen)


def decide(ix, table, r, ip):
    """ルータ r が宛先 ip のパケットをどうするか。
    ("deliver", 端末) / ("nohost",) / ("local",) / ("router", 隣) / ("fwd", [隣 …], 行) / ("null0", 行) / ("noroute",)
    届けるのは、宛先の端末がいる区間に向いたインターフェースの connected に当たったときだけ。"""
    eff = table.get("eff") or Eff(ix)
    row = _lpm(table["rows"], ip)
    if row is None:
        return ("noroute",)
    if row["code"] == "L":
        return ("local",)
    if row["code"] == "C":
        if row["out"] == "Loopback0":
            return ("local",)
        o = eff.owner(row["seg"], ip)
        if o is None:
            return ("nohost",)
        if o[0] == "host":
            return ("deliver", o[1])
        return ("local",) if o[1] == r else ("router", o[1])
    if any(x[1] == "Null0" for x in row["res"]):
        return ("null0", row)
    peers = [peer for nh, out, peer in row["res"]]
    if any(p is None for p in peers):
        return ("nohost",)                  # next-hop の IP を持つ機器がいない(ARP が返らない)
    return ("fwd", sorted(set(peers), key=peers.index), row)


def first_hop(ix, eff, src_ip, dst_ip):
    """端末が最初にどこへ渡すか。("direct", 持ち主 or None)(同じサブネット)/ ("gw", ルータ)/ ("nogw", ゲートウェイの IP)。
    端末は自分のサブネットの外へは既定ゲートウェイへ渡す。ゲートウェイの IP を持つルータが同じ LAN にいなければ最初の 1 歩で落ちる。"""
    h = ix.hinfo[src_ip]
    lid = ix.host[src_ip][1]
    ln = ix.lan_of[lid]
    seg = "LAN:" + lid
    if addr(dst_ip) in net(ln["prefix"]):
        return ("direct", eff.owner(seg, dst_ip))
    gw = h.get("gw") or ln["gw"]
    o = eff.owner(seg, gw)
    if o and o[0] == "router":
        return ("gw", o[1])
    return ("nogw", gw)


def trace(ix, tabs, src_ip, dst_ip, maxpaths=8):
    """src_ip の端末から dst_ip へのパケットの道。[{"hops": [ルータ …], "end": 種類, "at": ルータ}] (ECMP で複数)。
    end: deliver / nohost / local / router / null0 / noroute / loop / nogw(ゲートウェイに渡せない)"""
    eff = next(iter(tabs.values()))["eff"] if tabs else Eff(ix)
    fh = first_hop(ix, eff, src_ip, dst_ip)
    if fh[0] == "direct":
        o = fh[1]
        if o and o[0] == "host":
            return [{"hops": [], "end": "deliver", "at": None, "host": o[1]}]
        return [{"hops": [], "end": "nohost", "at": None}]
    if fh[0] == "nogw":
        return [{"hops": [], "end": "nogw", "at": None, "gw": fh[1]}]
    out = []

    def walk(r, hops):
        if len(out) >= maxpaths:
            return
        if r in hops:
            out.append({"hops": hops + [r], "end": "loop", "at": r})
            return
        hops = hops + [r]
        d = decide(ix, tabs[r], r, dst_ip)
        if d[0] == "fwd":
            for p in d[1]:
                walk(p, hops)
            return
        rec = {"hops": hops, "end": d[0], "at": r}
        if d[0] == "deliver":
            rec["host"] = d[1]
        out.append(rec)

    walk(fh[1], [])
    return out


# ==========================================================================
# IOS の表示とコマンド
# ==========================================================================
def route_cli(s, no=False):
    p = net(s["p"])
    nh = s.get("nh", "Null0")
    ad = int(s.get("ad", AD_STATIC))
    line = "ip route %s %s %s" % (p.network_address, p.netmask, nh)
    if ad != AD_STATIC and not no:
        line += " %d" % ad
    return ("no " if no else "") + line


def key_of(s):
    return (str(net(s["p"])), s.get("nh", "Null0"))


def diff(init, cur):
    """初期の設定 → 今の設定の差分を、IOS のコマンドの行で返す [(ルータ, 行)]。行の数が手数(設計 §2)。"""
    out = []
    for r in sorted(set(init) | set(cur), key=lambda x: (rnum(x), x)):
        a = {key_of(s): s for s in init.get(r, [])}
        b = {key_of(s): s for s in cur.get(r, [])}
        for k, s in a.items():
            if k not in b:
                out.append((r, route_cli(s, no=True)))
        for k, s in b.items():
            if k not in a or int(a[k].get("ad", AD_STATIC)) != int(s.get("ad", AD_STATIC)):
                out.append((r, route_cli(s)))
    return out


def moves(init, cur):
    return len(diff(init, cur))


def _classful(p):
    a = int(p.network_address) >> 24
    plen = 8 if a < 128 else 16 if a < 192 else 24
    return net("%s/%d" % (p.network_address, plen))


def _ifname(i):
    return {"Gi": "GigabitEthernet", "Et": "Ethernet"}.get(i[:2], "") + i[2:] if i[:2] in ("Gi", "Et") else i


def show_ip_route(table, codes=True):
    """IOS の show ip route の形(Codes の凡例は短く)。"""
    rows = table["rows"]
    lines = []
    if codes:
        lines += ["Codes: L - local, C - connected, S - static, * - candidate default", ""]
    dflt = next((x for x in rows if x["net"].prefixlen == 0), None)
    if dflt:
        gw = dflt["via"][0] if dflt["via"] and dflt["via"][0] != "Null0" else "0.0.0.0"
        lines.append("Gateway of last resort is %s to network 0.0.0.0" % gw)
    else:
        lines.append("Gateway of last resort is not set")
    lines.append("")
    groups = {}
    for x in rows:
        if x["net"].prefixlen == 0:
            continue
        groups.setdefault(_classful(x["net"]), []).append(x)

    def body(x, indent, nomask=False):
        code = x["code"] + ("*" if x["net"].prefixlen == 0 else "")
        pad = code.ljust(indent)
        p = str(x["net"].network_address) if nomask else x["p"]
        if x["code"] in ("C", "L"):
            return [pad + "%s is directly connected, %s" % (p, _ifname(x["out"]))]
        if x["via"] == ["Null0"]:
            return [pad + "%s is directly connected, Null0" % p]
        first = pad + "%s [%d/0] via %s" % (p, x["ad"], x["via"][0])
        cont = [" " * (len(pad) + len(p) + 1) + "[%d/0] via %s" % (x["ad"], v) for v in x["via"][1:]]
        return [first] + cont
    if dflt:
        lines += body(dflt, 6)
    for cf in sorted(groups, key=lambda p: int(p.network_address)):
        g = groups[cf]
        if len(g) == 1 and g[0]["net"] == cf:
            lines += body(g[0], 6)
            continue
        masks = {x["net"].prefixlen for x in g}
        one = len(masks) == 1
        if one:
            lines.append("      %s/%d is subnetted, %d subnets" % (cf.network_address, next(iter(masks)), len(g)))
        else:
            lines.append("      %s is variably subnetted, %d subnets, %d masks" % (cf, len(g), len(masks)))
        for x in g:
            lines += body(x, 9, nomask=one)
    return "\n".join(lines)


def ios_config(ix, r, routes, ifmap=None):
    """PoC 用: ルータ r の config(hostname・インターフェース・static)。ifmap= {"Gi0/0": "Ethernet0/0"} などの読み替え。"""
    R = ix.nw["routers"][r]
    out = ["hostname " + r]
    for i in R["ifs"]:
        name = (ifmap or {}).get(i["name"], _ifname(i["name"]))
        p = net("%s/%d" % (i["ip"], i["plen"]))
        out += ["interface " + name, " ip address %s %s" % (i["ip"], p.netmask), " no shutdown"]
    if R.get("lo"):
        out += ["interface Loopback0", " ip address %s 255.255.255.255" % R["lo"]]
    out += [route_cli(s) for s in routes]
    return out


# ==========================================================================
# selftest
# ==========================================================================
def _square(lo=False, extra_hosts=False):
    """R1─R2 / R1─R3 / R2─R4 / R3─R4 の四角。R1 に PC1、R4 に SRV1。"""
    routers = [{"name": "R%d" % i, "site": i} for i in (1, 2, 3, 4)]
    links = [{"a": "R1", "b": "R2"}, {"a": "R1", "b": "R3"}, {"a": "R2", "b": "R4"}, {"a": "R3", "b": "R4"}]
    lans = [{"router": "R1", "k": 1, "hosts": [{"name": "PC1"}]},
            {"router": "R4", "k": 1, "hosts": [{"name": "SRV1", "kind": "srv"}] +
             ([{"name": "SRV2", "kind": "srv"}] if extra_hosts else [])},
            {"router": "R4", "k": 2, "hosts": [{"name": "SRV3", "kind": "srv"}]}]
    return build_net(routers, links, lans, lo=lo)


def S(p, nh, ad=1):
    return {"p": p, "nh": nh, "ad": ad}


def selftest():
    ng = []

    def ok(cond, msg):
        if not cond:
            ng.append(msg)

    nw = _square(lo=True, extra_hosts=True)
    ix = Index(nw)
    pc1, srv1, srv2, srv3 = (ix.ip_of(h) for h in ("PC1", "SRV1", "SRV2", "SRV3"))
    ok(pc1 == "10.1.1.10" and srv1 == "10.4.1.100" and srv2 == "10.4.1.101" and srv3 == "10.4.2.100", "アドレス " + pc1 + srv1)
    lk = {(l["a"], l["b"]): l for l in nw["links"]}
    ok(lk[("R1", "R2")]["prefix"] == "172.16.12.0/30" and lk[("R1", "R2")]["ipa"] == "172.16.12.1"
       and lk[("R2", "R4")]["ipb"] == "172.16.24.2", "リンクのアドレス")

    def paths(cfg, s, d, down=()):
        t = tables(ix, cfg, down)
        return [(tuple(p["hops"]), p["end"]) for p in trace(ix, t, s, d)]

    # 1) 経路なし: R1 は 10.4.1.0/24 を知らない
    ok(paths({}, pc1, srv1) == [(("R1",), "noroute")], "経路なし")
    # 2) 片道: 行きは届くが戻りは R4 で落ちる
    cfg = {"R1": [S("10.4.1.0/24", "172.16.12.2")], "R2": [S("10.4.1.0/24", "172.16.24.2")]}
    ok(paths(cfg, pc1, srv1) == [(("R1", "R2", "R4"), "deliver")], "行き %s" % paths(cfg, pc1, srv1))
    ok(paths(cfg, srv1, pc1) == [(("R4",), "noroute")], "戻りなし")
    # 3) ロンゲストマッチ: R2 の /32 が SRV2 だけ R1 へ戻す → ループ
    cfg2 = {"R1": [S("10.4.0.0/16", "172.16.12.2")],
            "R2": [S("10.4.0.0/16", "172.16.24.2"), S("10.4.1.101/32", "172.16.12.1")]}
    ok(paths(cfg2, pc1, srv1) == [(("R1", "R2", "R4"), "deliver")], "/16 で届く")
    ok(paths(cfg2, pc1, srv2) == [(("R1", "R2", "R1"), "loop")], "/32 の横取りでループ %s" % paths(cfg2, pc1, srv2))
    # 4) /32 の static は connected の /24 より長いので勝つ
    cfg3 = {"R4": [S("10.4.1.100/32", "172.16.24.1")]}
    t = tables(ix, cfg3)
    ok(decide(ix, t["R4"], "R4", srv1)[0] == "fwd" and decide(ix, t["R4"], "R4", srv2)[0] == "deliver", "/32 が connected に勝つ")
    # 5) AD より長さが先: /24 の AD 250 が /16 の AD 1 に勝つ
    cfg4 = {"R1": [S("10.4.0.0/16", "172.16.12.2"), S("10.4.1.0/24", "172.16.13.2", 250)]}
    t = tables(ix, cfg4)
    d = decide(ix, t["R1"], "R1", srv1)
    ok(d[0] == "fwd" and d[1] == ["R3"], "長さが先 %s" % (d,))
    # 6) フローティング: 平常は AD 1 だけが入り、R1–R2 が落ちると AD 5 が入る
    cfg5 = {"R1": [S("10.4.0.0/16", "172.16.12.2"), S("10.4.0.0/16", "172.16.13.2", 5)]}
    t = tables(ix, cfg5)
    rows = [x for x in t["R1"]["rows"] if x["p"] == "10.4.0.0/16"]
    ok(len(rows) == 1 and rows[0]["via"] == ["172.16.12.2"] and rows[0]["ad"] == 1, "平常は AD 1")
    ok({"i": 1, "why": "worse_ad"} in t["R1"]["skipped"], "AD 5 は skipped")
    k12 = next(i for i, l in enumerate(nw["links"]) if (l["a"], l["b"]) == ("R1", "R2"))
    t = tables(ix, cfg5, down={k12})
    rows = [x for x in t["R1"]["rows"] if x["p"] == "10.4.0.0/16"]
    ok(len(rows) == 1 and rows[0]["via"] == ["172.16.13.2"] and rows[0]["ad"] == 5, "障害で AD 5")
    ok(not any(x["p"] == "172.16.12.0/30" for x in t["R1"]["rows"]), "落ちたリンクの C は消える")
    ok({"i": 0, "why": "unresolved"} in t["R1"]["skipped"], "落ちた next-hop の static は外れる")
    # 6b) AD 255 は設定に入るが表に入らない(PoC input_form #6)
    t = tables(ix, {"R1": [S("10.4.0.0/16", "172.16.12.2", 255)]})
    ok(not any(x["p"] == "10.4.0.0/16" for x in t["R1"]["rows"]) and {"i": 0, "why": "ad255"} in t["R1"]["skipped"], "AD 255 は表に入らない")
    # 7) デフォルトどうしの向け合い → ループ
    cfg6 = {"R1": [S("0.0.0.0/0", "172.16.12.2")], "R2": [S("0.0.0.0/0", "172.16.12.1")]}
    ok(paths(cfg6, pc1, srv1) == [(("R1", "R2", "R1"), "loop")], "デフォルトのループ")
    # 8) Null0 でループを止める
    cfg7 = {"R1": [S("0.0.0.0/0", "172.16.12.2")],
            "R2": [S("0.0.0.0/0", "172.16.12.1"), S("10.4.0.0/16", "Null0")]}
    ok(paths(cfg7, pc1, "10.4.9.9") == [(("R1", "R2"), "null0")], "Null0")
    # 9) 再帰: ループバック宛ての next-hop
    cfg8 = {"R1": [S("10.4.0.0/16", "10.255.0.4"), S("10.255.0.4/32", "172.16.13.2")],
            "R3": [S("10.4.0.0/16", "172.16.34.2")]}
    t = tables(ix, cfg8)
    row = next(x for x in t["R1"]["rows"] if x["p"] == "10.4.0.0/16")
    ok(row["via"] == ["10.255.0.4"] and row["res"] == [("172.16.13.2", "Gi0/2", "R3")], "再帰の解決 %s" % (row["res"],))
    ok(paths(cfg8, pc1, srv1) == [(("R1", "R3", "R4"), "deliver")], "再帰で届く")
    # 10) 解決できない next-hop は表に入らない(自分で自分を支えない)
    cfg9 = {"R1": [S("10.255.0.0/16", "10.255.0.4")]}
    t = tables(ix, cfg9)
    ok(not any(x["code"] == "S" for x in t["R1"]["rows"]) and t["R1"]["skipped"] == [{"i": 0, "why": "unresolved"}],
       "自分で自分を支えない")
    # 11) ECMP
    cfg10 = {"R1": [S("10.4.0.0/16", "172.16.12.2"), S("10.4.0.0/16", "172.16.13.2")],
             "R2": [S("10.4.0.0/16", "172.16.24.2")], "R3": [S("10.4.0.0/16", "172.16.34.2")]}
    ok(sorted(paths(cfg10, pc1, srv1)) == [(("R1", "R2", "R4"), "deliver"), (("R1", "R3", "R4"), "deliver")], "ECMP")
    # 12) connected と同じ宛先の static は入らない
    cfg11 = {"R4": [S("10.4.1.0/24", "172.16.24.1")]}
    t = tables(ix, cfg11)
    ok(t["R4"]["skipped"] == [{"i": 0, "why": "connected"}], "connected が優先")
    # 13) 端末のいない IP: ARP が返らない
    t = tables(ix, cfg)
    ok(decide(ix, t["R4"], "R4", "10.4.1.99") == ("nohost",), "nohost")
    # 14) デフォルト経由の再帰(仮の決まり)
    cfg12 = {"R1": [S("0.0.0.0/0", "172.16.12.2"), S("10.4.0.0/16", "10.255.0.4")]}
    t = tables(ix, cfg12)
    ok(any(x["p"] == "10.4.0.0/16" for x in t["R1"]["rows"]) == VIA_DEFAULT, "デフォルト経由の再帰")
    # 14b) Null0 の行を通る再帰: 表に入り、Null0 で捨てる
    cfg13 = {"R1": [S("10.255.0.0/16", "Null0"), S("10.4.0.0/16", "10.255.0.4")]}
    t = tables(ix, cfg13)
    ok(any(x["p"] == "10.4.0.0/16" for x in t["R1"]["rows"]) and decide(ix, t["R1"], "R1", srv1)[0] == "null0",
       "Null0 を通る再帰")
    # 11b) ECMP の via は next-hop の降順
    t = tables(ix, cfg10)
    row = next(x for x in t["R1"]["rows"] if x["p"] == "10.4.0.0/16")
    ok(row["via"] == ["172.16.13.2", "172.16.12.2"], "ECMP の並び %s" % row["via"])
    # 15) 差分と手数
    init = {"R1": [S("0.0.0.0/0", "172.16.12.2")]}
    cur = {"R1": [S("0.0.0.0/0", "172.16.13.2")], "R2": [S("10.4.0.0/16", "172.16.24.2", 5)]}
    ok(diff(init, cur) == [("R1", "no ip route 0.0.0.0 0.0.0.0 172.16.12.2"), ("R1", "ip route 0.0.0.0 0.0.0.0 172.16.13.2"),
                           ("R2", "ip route 10.4.0.0 255.255.0.0 172.16.24.2 5")], "差分 %s" % diff(init, cur))
    ok(moves(init, init) == 0 and moves(cfg5, {"R1": [S("10.4.0.0/16", "172.16.12.2"), S("10.4.0.0/16", "172.16.13.2", 10)]}) == 1,
       "AD だけ変えるのは 1 行")
    # 16) show ip route の形
    t = tables(ix, cfg7)
    txt = show_ip_route(t["R2"])
    ok("Gateway of last resort is 172.16.12.1 to network 0.0.0.0" in txt and
       "S*    0.0.0.0/0 [1/0] via 172.16.12.1" in txt and "S        10.4.0.0/16 is directly connected, Null0" in txt and
       "C        172.16.12.0/30 is directly connected, GigabitEthernet0/0" in txt, "show ip route\n" + txt)

    # 17〜) connected の段(ルータ 1 台・LAN 3 つ)
    one = build_net([{"name": "R1", "site": 1}], [],
                    [{"router": "R1", "k": 1, "hosts": [{"name": "PC1"}]},
                     {"router": "R1", "k": 2, "hosts": [{"name": "SRV1", "kind": "srv"}]},
                     {"router": "R1", "k": 3, "hosts": [{"name": "PC3"}]}])
    i1 = Index(one)
    a, b = i1.ip_of("PC1"), i1.ip_of("SRV1")

    def p1(ifs):
        t = tables(i1, {}, (), ifs)
        return [(tuple(x["hops"]), x["end"]) for x in trace(i1, t, a, b)]
    ok(p1(None) == [(("R1",), "deliver")], "connected だけで届く")
    ok(p1({"R1": {"Gi0/1": {"shut": True}}}) == [(("R1",), "noroute")], "shutdown で C が消える")
    ok(p1({"R1": {"Gi0/1": {"ip": None}}}) == [(("R1",), "noroute")], "IP なし")
    ok(p1({"R1": {"Gi0/1": {"ip": "10.1.9.1/24"}}}) == [(("R1",), "noroute")], "別のサブネット")
    ok(p1({"R1": {"Gi0/0": {"ip": "10.1.1.254/24"}}}) == [((), "nogw")], "ゲートウェイと違う IP(.254)")
    ok(p1({"R1": {"Gi0/0": {"ip": "10.1.1.254/24"}}}) != [] and
       [(tuple(x["hops"]), x["end"]) for x in trace(i1, tables(i1, {}, (), {"R1": {"Gi0/0": {"ip": "10.1.1.254/24"}}}), b, a)]
       == [(("R1",), "deliver")], ".254 でもルータから端末へは届く(戻りは別)")
    # SRV1 の LAN の札に、別の LAN 側の IF で同じサブネットを付けても届かない(区間が違う)
    t = tables(i1, {}, (), {"R1": {"Gi0/1": {"ip": None}, "Gi0/2": {"ip": "10.1.2.1/24"}}})
    ok(decide(i1, t["R1"], "R1", b) == ("nohost",), "向きの違う IF の C では届かない")
    ok(overlaps(i1, {"R1": {"Gi0/2": {"ip": "10.1.2.5/24"}}}, "R1") == [("Gi0/1", "Gi0/2")], "重なり")
    ok(overlaps(i1, None, "R1") == [], "重なりなし")
    ok([(tuple(x["hops"]), x["end"]) for x in trace(i1, tables(i1, {}), a, "10.1.1.99")] == [((), "nohost")],
       "同じサブネットは直接(いない IP)")
    # リンクの片端の shutdown で両端が down
    t = tables(ix, cfg5, (), {"R2": {"Gi0/0": {"shut": True}}})
    rows = [x for x in t["R1"]["rows"] if x["p"] == "10.4.0.0/16"]
    ok(rows and rows[0]["via"] == ["172.16.13.2"], "片端の shutdown で両端が down(フローティングへ)")

    for m in ng:
        print("NG:", m)
    print("route_model selftest: NG %d" % len(ng))
    return not ng


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    print(__doc__)
