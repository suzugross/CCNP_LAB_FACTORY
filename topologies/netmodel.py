#!/usr/bin/env python3
"""大域不変条件グレーダ（軸1）。

各ノードの全 RIB（show ip route）と トポロジモデル（loopbacks / links）から
*転送グラフ* を構築し、ネットワーク全体の性質を判定する。

従来の grade.py は「ノード単位のチェック（RT04 で X が不在 等）」しか書けず、
「ループが無い」「経路が最適」「冗長度2」といった *大域的な性質* を採点できなかった。
本モジュールは全ノードの RIB を突き合わせ、宛先 Loopback ごとに next-hop を辿って
転送をシミュレートし、以下の不変条件を判定する:

  reachability_all : 全順序対 (R,T) で R が T の Loopback へ転送到達する
  loop_free        : どの (R,T) でも転送ループ（同一ノード再訪）が起きない
  optimal          : どの (R,T) でも実経路ホップ数 == グラフ最短ホップ数
  single_default   : 指定ノードのデフォルト経路が「ちょうど1本」(任意で via 指定)
  disjoint_paths   : 指定 (R,T) に対しノード独立な転送経路が k 本以上ある

next-hop IP → 隣接ノードの対応は model.links の各端 IP / Loopback IP から一意に引く
（全 IP はグローバル一意）。最短ホップは model.links の無向グラフ上の BFS。

grade.py からは evaluate_invariants(model, ribs, invariants, genie_os) を呼ぶ。
ribs は {node: "show ip route の生テキスト"}（Genie で構造化する）。
単体テストや他生成器からは build_index / forward_paths / 各 inv_* を直接使える。
"""
import ipaddress
from collections import deque


# ----------------------------------------------------------------------------
# RIB パース（Genie 構造化 → 正規化 routes）
# ----------------------------------------------------------------------------
def routes_from_genie(parsed):
    """Genie の `show ip route` dict を正規化:
    [{prefix, src, nexthops:[ip,...]}]。connected/local は nexthops=[]。"""
    out = []
    if not parsed:
        return out
    try:
        afs = parsed["vrf"]["default"]["address_family"]["ipv4"]["routes"]
    except (KeyError, TypeError):
        # vrf 名が default 以外のこともあるので総当たりで routes を拾う
        afs = {}
        for vrf in (parsed.get("vrf") or {}).values():
            for af in (vrf.get("address_family") or {}).values():
                afs.update(af.get("routes") or {})
    for prefix, info in afs.items():
        nhs = []
        nh = info.get("next_hop", {}) or {}
        for ent in (nh.get("next_hop_list", {}) or {}).values():
            ip = ent.get("next_hop")
            if ip:
                nhs.append(ip)
        out.append({"prefix": prefix,
                    "src": info.get("source_protocol", ""),
                    "nexthops": nhs})
    return out


def parse_rib_text(text, genie_os="iosxe"):
    """show ip route の生テキストを Genie で構造化 → 正規化 routes。"""
    from genie.conf.base import Device
    dev = Device(name="nm", os=genie_os)
    dev.custom.setdefault("abstraction", {"order": ["os"]})
    try:
        parsed = dev.parse("show ip route", output=text or "")
    except Exception:
        return []
    return routes_from_genie(parsed)


# ----------------------------------------------------------------------------
# トポロジモデル → インデックス
# ----------------------------------------------------------------------------
def build_index(model):
    """model = {loopbacks:{node:ip}, links:[{a,a_ip,b,b_ip}]} から
    ip_owner（IP→ノード）/ adj（無向隣接）/ nodes / loopbacks を作る。"""
    loopbacks = dict(model.get("loopbacks", {}))
    nodes = list(loopbacks.keys())
    ip_owner = {}
    for n, ip in loopbacks.items():
        ip_owner[ip] = n
    adj = {n: set() for n in nodes}
    for ln in model.get("links", []):
        a, b = ln["a"], ln["b"]
        ip_owner[ln["a_ip"]] = a
        ip_owner[ln["b_ip"]] = b
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return {"loopbacks": loopbacks, "nodes": nodes,
            "ip_owner": ip_owner, "adj": {k: sorted(v) for k, v in adj.items()}}


def shortest_hops(adj, src, dst):
    """無向グラフ adj 上の src→dst 最短ホップ数（到達不能は None）。"""
    if src == dst:
        return 0
    seen = {src}
    q = deque([(src, 0)])
    while q:
        cur, d = q.popleft()
        for nb in adj.get(cur, []):
            if nb == dst:
                return d + 1
            if nb not in seen:
                seen.add(nb)
                q.append((nb, d + 1))
    return None


# ----------------------------------------------------------------------------
# 転送シミュレーション（RIB の next-hop を辿る）
# ----------------------------------------------------------------------------
def _lpm(routes, dst_ip):
    """routes（正規化リスト）から dst_ip への最長一致経路を返す（無ければ None）。"""
    addr = ipaddress.ip_address(dst_ip)
    best, best_len = None, -1
    for r in routes:
        try:
            net = ipaddress.ip_network(r["prefix"], strict=False)
        except ValueError:
            continue
        if addr in net and net.prefixlen > best_len:
            best, best_len = r, net.prefixlen
    return best


def forward_paths(idx, ribs, src, dst):
    """src から dst（の Loopback）への転送を RIB に従い辿る。
    ECMP は全分岐を DFS で展開。各分岐の結末を列挙して返す:
      [{result, path:[node...], (nh)}]
      result: reached / loop / no_route / no_nexthop / deadend / unknown_nh / no_rib / depth
    """
    dst_ip = idx["loopbacks"][dst]
    cap = len(idx["nodes"]) + 2
    results = []

    def dfs(cur, visited):
        if cur == dst:
            results.append({"result": "reached", "path": visited + [cur]})
            return
        if cur in visited:
            results.append({"result": "loop", "path": visited + [cur]})
            return
        if len(visited) > cap:
            results.append({"result": "depth", "path": visited + [cur]})
            return
        routes = ribs.get(cur)
        if routes is None:
            results.append({"result": "no_rib", "path": visited + [cur]})
            return
        r = _lpm(routes, dst_ip)
        if r is None:
            results.append({"result": "no_route", "path": visited + [cur]})
            return
        if r["src"] in ("connected", "local"):
            # /32 Loopback は所有者しか connected で持たない（所有者なら冒頭で reached）。
            # ここに来る＝別サブネットへ吸い込まれた行き止まり。
            results.append({"result": "deadend", "path": visited + [cur]})
            return
        if not r["nexthops"]:
            results.append({"result": "no_nexthop", "path": visited + [cur]})
            return
        for ip in r["nexthops"]:
            nxt = idx["ip_owner"].get(ip)
            if nxt is None:
                results.append({"result": "unknown_nh", "path": visited + [cur], "nh": ip})
                continue
            dfs(nxt, visited + [cur])

    dfs(src, [])
    return results


def reached_paths(paths):
    return [p["path"] for p in paths if p["result"] == "reached"]


# ----------------------------------------------------------------------------
# 不変条件の評価
# ----------------------------------------------------------------------------
def _pairs(nodes, only=None):
    if only:
        return [(a, b) for (a, b) in only]
    return [(R, T) for R in nodes for T in nodes if R != T]


def inv_reachability_all(idx, ribs, params):
    """全(または指定)順序対で転送到達する。ループ/到達不能を不合格事由に挙げる。"""
    fails = []
    for R, T in _pairs(idx["nodes"], params.get("pairs")):
        paths = forward_paths(idx, ribs, R, T)
        if not paths:
            fails.append(f"{R}->{T}: 経路探索不能")
            continue
        if any(p["result"] == "loop" for p in paths):
            fails.append(f"{R}->{T}: 転送ループ")
        elif not any(p["result"] == "reached" for p in paths):
            why = paths[0]["result"]
            fails.append(f"{R}->{T}: 到達不能 ({why})")
    return (not fails), {"failures": fails}


def inv_loop_free(idx, ribs, params):
    """どの順序対でも転送ループが無い（ループ経路を提示）。"""
    fails = []
    for R, T in _pairs(idx["nodes"], params.get("pairs")):
        for p in forward_paths(idx, ribs, R, T):
            if p["result"] == "loop":
                fails.append(f"{R}->{T}: " + "->".join(p["path"]))
                break
    return (not fails), {"failures": fails}


def inv_optimal(idx, ribs, params):
    """実経路ホップ数 == グラフ最短ホップ数（コスト等価前提・問題が opt-in）。"""
    fails = []
    for R, T in _pairs(idx["nodes"], params.get("pairs")):
        rp = reached_paths(forward_paths(idx, ribs, R, T))
        if not rp:
            fails.append(f"{R}->{T}: 到達不能")
            continue
        actual = min(len(p) - 1 for p in rp)
        best = shortest_hops(idx["adj"], R, T)
        if best is not None and actual > best:
            fails.append(f"{R}->{T}: {actual}ホップ (最短{best})")
    return (not fails), {"failures": fails}


def inv_single_default(idx, ribs, params):
    """指定ノードのデフォルト経路(0.0.0.0/0)が「ちょうど1本」。
    params: {nodes:[...], via:<ip>(任意)}。"""
    fails = []
    targets = params.get("nodes") or idx["nodes"]
    for n in targets:
        routes = ribs.get(n) or []
        defaults = [r for r in routes if r["prefix"] in ("0.0.0.0/0", "default")]
        if len(defaults) != 1:
            fails.append(f"{n}: デフォルト経路 {len(defaults)} 本（期待1本）")
            continue
        via = params.get("via")
        if via and via not in defaults[0]["nexthops"]:
            fails.append(f"{n}: デフォルト next-hop={defaults[0]['nexthops']} (期待 {via})")
    return (not fails), {"failures": fails}


def _max_disjoint(paths):
    """中継ノード（端点除く）が互いに素な経路の最大本数を貪欲＋後退で求める。"""
    cores = [set(p[1:-1]) for p in paths]
    best = [0]

    def rec(i, used, cnt):
        if cnt + (len(cores) - i) <= best[0]:
            return
        if i == len(cores):
            best[0] = max(best[0], cnt)
            return
        if not (cores[i] & used):           # 採用
            rec(i + 1, used | cores[i], cnt + 1)
        rec(i + 1, used, cnt)               # 不採用
    rec(0, set(), 0)
    return best[0]


def inv_disjoint_paths(idx, ribs, params):
    """指定 (R,T) にノード独立な転送経路が k 本以上ある（冗長度）。
    params: {pairs:[[R,T],...], k:2}。"""
    k = int(params.get("k", 2))
    fails = []
    for R, T in (params.get("pairs") or []):
        rp = reached_paths(forward_paths(idx, ribs, R, T))
        d = _max_disjoint(rp)
        if d < k:
            fails.append(f"{R}->{T}: 独立経路 {d} 本（期待 {k} 本以上）")
    return (not fails), {"failures": fails}


_INVARIANTS = {
    "reachability_all": inv_reachability_all,
    "loop_free": inv_loop_free,
    "optimal": inv_optimal,
    "single_default": inv_single_default,
    "disjoint_paths": inv_disjoint_paths,
}


def evaluate_invariants(model, ribs_text, invariants, genie_os="iosxe"):
    """grade.py から呼ぶ入口。
    model     : {loopbacks, links}
    ribs_text : {node: "show ip route 生テキスト"}（または既に正規化済み list）
    invariants: [{type, name, points, ...params}]
    戻り値    : [{name, ok, points, detail}]
    """
    idx = build_index(model)
    ribs = {}
    for n, val in ribs_text.items():
        ribs[n] = val if isinstance(val, list) else parse_rib_text(val, genie_os)
    out = []
    for inv in invariants:
        fn = _INVARIANTS.get(inv["type"])
        if fn is None:
            out.append({"name": inv.get("name", inv["type"]), "ok": False,
                        "points": inv.get("points", 0),
                        "detail": {"failures": [f"未知の不変条件: {inv['type']}"]}})
            continue
        ok, detail = fn(idx, ribs, inv)
        out.append({"name": inv.get("name", inv["type"]), "ok": ok,
                    "points": inv.get("points", 0), "detail": detail})
    return out
