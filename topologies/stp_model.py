#!/usr/bin/env python3
"""STP の計算器(BL-216)— 紙面 `gen_paper_stp.py` の盤面と、ラボ L1 の期待値計算に使う。

1 VLAN の point-to-point トポロジについて、802.1D/RSTP 共通の選出を行う。
  root bridge   = 最小 (priority, MAC)
  root port     = 最小 (root path cost, 送信元 BID, 送信元 port ID, 自 port ID)
  designated    = セグメント(リンク)ごとに最小 (root path cost, BID, port ID) の端
  それ以外      = Alternate(RSTP の呼び方。802.1D の blocking)
共有セグメント(ハブ)は扱わない= Backup ポートはこの計算器では生じない。

実測で確かめた前提(poc/stp/README.md 第2回・ioll2-xe 17.15.1):
  ・port-priority は**送信元(上流)側**の値が下流の root port 選択に効く(M4)。
  ・spanning-tree cost は**自分**の受信ポートのコスト(M4d)。
  ・表示の priority = 設定値 + VLAN ID(sys-id-ext)。
パスコスト値は Cisco 公式の既定表(short: 10G=2・1G=4・100M=19・10M=100 / long: 10G=2000・1G=20000・
100M=200000・10M=2000000)。1 つの盤面の中で方式は混在させない(ユーザ決定 U4)。
"""
from __future__ import annotations

import heapq

COST = {
    "short": {"10G": 2, "1G": 4, "100M": 19, "10M": 100},
    "long": {"10G": 2000, "1G": 20000, "100M": 200000, "10M": 2000000},
}


def mac_key(mac):
    return int(mac.replace(".", ""), 16)


class Topo:
    """switches: {name: {"prio": int, "mac": "xxxx.xxxx.xxxx"}}
    links: [(swA, ifA, swB, ifB, speed)]  ifX= {"name": "Gi1/0/1", "num": 1}
    port_prio: {(sw, ifname): int}   cost_ovr: {(sw, ifname): int}
    """

    def __init__(self, switches, links, method="short", port_prio=None, cost_ovr=None, vlan=10):
        self.sw = switches
        self.links = links
        self.method = method
        self.port_prio = dict(port_prio or {})
        self.cost_ovr = dict(cost_ovr or {})
        self.vlan = vlan

    # ---- 基本量 -----------------------------------------------------------
    def bid(self, s):
        return (self.sw[s]["prio"], mac_key(self.sw[s]["mac"]))

    def pid(self, s, ifc):
        return (self.port_prio.get((s, ifc["name"]), 128), ifc["num"])

    def pcost(self, s, ifc, speed):
        return self.cost_ovr.get((s, ifc["name"]), COST[self.method][speed])

    def ports(self, s):
        """s のポート一覧: (自 if, 相手 sw, 相手 if, speed)"""
        out = []
        for a, ia, b, ib, sp in self.links:
            if a == s:
                out.append((ia, b, ib, sp))
            if b == s:
                out.append((ib, a, ia, sp))
        return out

    # ---- 選出 -------------------------------------------------------------
    def solve(self):
        root = min(self.sw, key=self.bid)
        rpc = {s: None for s in self.sw}
        rpc[root] = 0
        pq = [(0, root)]
        while pq:
            c, s = heapq.heappop(pq)
            if c != rpc[s]:
                continue
            for ifc, n, nif, sp in self.ports(s):
                nc = c + self.pcost(n, nif, sp)     # 相手 n が受信するポート nif のコスト
                if rpc[n] is None or nc < rpc[n]:
                    rpc[n] = nc
                    heapq.heappush(pq, (nc, n))
        if any(v is None for v in rpc.values()):
            raise ValueError("非連結")
        rp = {}
        for s in self.sw:
            if s == root:
                continue
            best = None
            for ifc, n, nif, sp in self.ports(s):
                vec = (rpc[n] + self.pcost(s, ifc, sp), self.bid(n), self.pid(n, nif), self.pid(s, ifc))
                if best is None or vec < best[0]:
                    best = (vec, ifc["name"])
            rp[s] = best[1]
        role = {}
        for a, ia, b, ib, sp in self.links:
            va = (rpc[a], self.bid(a), self.pid(a, ia))
            vb = (rpc[b], self.bid(b), self.pid(b, ib))
            des, oth = ((a, ia), (b, ib)) if va < vb else ((b, ib), (a, ia))
            role[(des[0], des[1]["name"])] = "Desg"
            role[(oth[0], oth[1]["name"])] = "Root" if rp.get(oth[0]) == oth[1]["name"] else "Altn"
        for s, ifn in rp.items():
            if role[(s, ifn)] != "Root":
                raise ValueError("root port が designated 側に来た(計算器の不整合)")
        self.root, self.rpc, self.rp, self.role = root, rpc, rp, role
        return self

    # ---- 派生 -------------------------------------------------------------
    def state(self, s, ifn):
        return "BLK" if self.role[(s, ifn)] == "Altn" else "FWD"

    def cost_of(self, s, ifn):
        for ifc, n, nif, sp in self.ports(s):
            if ifc["name"] == ifn:
                return self.pcost(s, ifc, sp)
        raise KeyError(ifn)

    def blocked(self):
        return sorted(k for k, v in self.role.items() if v == "Altn")

    def active_adj(self):
        adj = {s: [] for s in self.sw}
        for a, ia, b, ib, sp in self.links:
            if self.role[(a, ia["name"])] != "Altn" and self.role[(b, ib["name"])] != "Altn":
                adj[a].append(b)
                adj[b].append(a)
        return adj

    def path(self, src, dst):
        """転送に使われる木の上の経路(スイッチ名の列)。"""
        adj = self.active_adj()
        prev = {src: None}
        q = [src]
        while q:
            x = q.pop(0)
            for y in adj[x]:
                if y not in prev:
                    prev[y] = x
                    q.append(y)
        if dst not in prev:
            raise ValueError("木の上で不達")
        out = [dst]
        while prev[out[-1]] is not None:
            out.append(prev[out[-1]])
        return out[::-1]


# ==========================================================================
# selftest: 手計算の定番盤面と一致すること
# ==========================================================================
def _gi(n):
    return {"name": f"Gi1/0/{n}", "num": n}


def _te(n):
    return {"name": f"Te1/1/{n}", "num": 48 + n}


def selftest():
    ng = 0

    def chk(name, got, want):
        nonlocal ng
        if got != want:
            ng += 1
            print(f"  NG {name}: got={got} want={want}")

    # 1) 三角形・全 1G・priority で root=SW1、SW2 < SW3(MAC)→ SW3 の SW2 側がブロック
    sw = {"SW1": {"prio": 24576, "mac": "0019.aa00.0300"}, "SW2": {"prio": 32768, "mac": "0019.aa00.0100"},
          "SW3": {"prio": 32768, "mac": "0019.aa00.0200"}}
    L = [("SW1", _gi(1), "SW2", _gi(1), "1G"), ("SW1", _gi(2), "SW3", _gi(1), "1G"), ("SW2", _gi(2), "SW3", _gi(2), "1G")]
    t = Topo(sw, L).solve()
    chk("tri root", t.root, "SW1")
    chk("tri blocked", t.blocked(), [("SW3", "Gi1/0/2")])
    chk("tri rpc", (t.rpc["SW2"], t.rpc["SW3"]), (4, 4))
    chk("tri path SW2->SW3", t.path("SW2", "SW3"), ["SW2", "SW1", "SW3"])

    # 2) 同じ三角形で SW1-SW3 を 100M にすると SW3 は SW2 経由(4+4=8 < 19)→ SW3 Gi1/0/1 がブロック
    L2 = [("SW1", _gi(1), "SW2", _gi(1), "1G"), ("SW1", _gi(2), "SW3", _gi(1), "100M"), ("SW2", _gi(2), "SW3", _gi(2), "1G")]
    t = Topo(sw, L2).solve()
    chk("tri100 rp", t.rp["SW3"], "Gi1/0/2")
    chk("tri100 blocked", t.blocked(), [("SW3", "Gi1/0/1")])
    chk("tri100 rpc", t.rpc["SW3"], 8)

    # 3) 並列 2 本(SW1 root)。下流 SW2 の RP は送信元 port ID の小さい Gi1/0/1。上流の port-priority で逆転
    sw2 = {"SW1": {"prio": 4096, "mac": "0019.aa00.0100"}, "SW2": {"prio": 32768, "mac": "0019.aa00.0200"}}
    P = [("SW1", _gi(1), "SW2", _gi(3), "1G"), ("SW1", _gi(2), "SW2", _gi(4), "1G")]
    t = Topo(sw2, P).solve()
    chk("par rp", t.rp["SW2"], "Gi1/0/3")
    t = Topo(sw2, P, port_prio={("SW2", "Gi1/0/4"): 16}).solve()      # 下流で変えても不変
    chk("par down-prio", t.rp["SW2"], "Gi1/0/3")
    t = Topo(sw2, P, port_prio={("SW1", "Gi1/0/2"): 64}).solve()      # 上流で変えると逆転
    chk("par up-prio", t.rp["SW2"], "Gi1/0/4")
    t = Topo(sw2, P, cost_ovr={("SW2", "Gi1/0/3"): 10}).solve()       # 下流の自側 cost で逆転
    chk("par down-cost", t.rp["SW2"], "Gi1/0/4")

    # 4) 四角形(リング 4 台)・root=SW1・対角 SW3 で合流→ BID の大きい側から来る方がブロック
    sw4 = {"SW1": {"prio": 4096, "mac": "0019.aa00.0400"}, "SW2": {"prio": 32768, "mac": "0019.aa00.0300"},
           "SW3": {"prio": 32768, "mac": "0019.aa00.0200"}, "SW4": {"prio": 32768, "mac": "0019.aa00.0100"}}
    R = [("SW1", _gi(1), "SW2", _gi(1), "1G"), ("SW2", _gi(2), "SW3", _gi(1), "1G"),
         ("SW3", _gi(2), "SW4", _gi(2), "1G"), ("SW4", _gi(1), "SW1", _gi(2), "1G")]
    t = Topo(sw4, R).solve()
    chk("sq rpc SW3", t.rpc["SW3"], 8)
    chk("sq rp SW3", t.rp["SW3"], "Gi1/0/2")          # SW4(BID 小)側から
    chk("sq blocked", t.blocked(), [("SW3", "Gi1/0/1")])

    # 5) long 方式・10G と 1G の混在: 10G 2 本(2000+2000) < 1G 1 本(20000)
    L5 = [("SW1", _te(1), "SW2", _te(1), "10G"), ("SW1", _gi(2), "SW3", _gi(1), "1G"), ("SW2", _te(2), "SW3", _te(2), "10G")]
    t = Topo(sw, L5, method="long").solve()
    chk("long rp SW3", t.rp["SW3"], "Te1/1/2")
    chk("long rpc SW3", t.rpc["SW3"], 4000)
    chk("long blocked", t.blocked(), [("SW3", "Gi1/0/1")])

    # 6) 同コストで送信元 BID の比較: SW4 は SW2・SW3 のどちらからも 8。SW3 の方が BID が小さい
    sw6 = {"SW1": {"prio": 4096, "mac": "0019.aa00.0900"}, "SW2": {"prio": 32768, "mac": "0019.aa00.0500"},
           "SW3": {"prio": 28672, "mac": "0019.aa00.0600"}, "SW4": {"prio": 32768, "mac": "0019.aa00.0100"}}
    D = [("SW1", _gi(1), "SW2", _gi(1), "1G"), ("SW1", _gi(2), "SW3", _gi(1), "1G"),
         ("SW2", _gi(2), "SW4", _gi(1), "1G"), ("SW3", _gi(2), "SW4", _gi(2), "1G")]
    t = Topo(sw6, D).solve()
    chk("dia rp SW4", t.rp["SW4"], "Gi1/0/2")
    chk("dia blocked", t.blocked(), [("SW4", "Gi1/0/1")])
    chk("dia path SW2->SW4", t.path("SW2", "SW4"), ["SW2", "SW1", "SW3", "SW4"])

    # 7) 実機一致(poc/stp 第2回 s1/s2・ioll2 は Et=10M 扱いで cost 100)。
    #    SW01-SW02 Et0/0-Et0/0 / SW01-SW03 Et0/1-Et0/0 / SW02-SW03 Et0/1-Et0/1 と Et0/2-Et0/2
    def _et(n):
        return {"name": f"Et0/{n}", "num": n + 1}
    E = [("SW01", _et(0), "SW02", _et(0), "10M"), ("SW01", _et(1), "SW03", _et(0), "10M"),
         ("SW02", _et(1), "SW03", _et(1), "10M"), ("SW02", _et(2), "SW03", _et(2), "10M")]
    macs = {"SW01": "aabb.cc02.4000", "SW02": "aabb.cc02.4100", "SW03": "aabb.cc02.4200"}
    v10 = {s: {"prio": p, "mac": macs[s]} for s, p in (("SW01", 4096), ("SW02", 8192), ("SW03", 32768))}
    t = Topo(v10, E).solve()
    chk("iol v10 SW03", {k: v for k, v in t.role.items() if k[0] == "SW03"},
        {("SW03", "Et0/0"): "Root", ("SW03", "Et0/1"): "Altn", ("SW03", "Et0/2"): "Altn"})
    v20 = {s: {"prio": p, "mac": macs[s]} for s, p in (("SW01", 8192), ("SW02", 4096), ("SW03", 32768))}
    t = Topo(v20, E).solve()
    chk("iol v20 SW03", {k: v for k, v in t.role.items() if k[0] == "SW03"},
        {("SW03", "Et0/0"): "Altn", ("SW03", "Et0/1"): "Root", ("SW03", "Et0/2"): "Altn"})
    t = Topo(v20, E, port_prio={("SW02", "Et0/2"): 64}).solve()      # 実測 M4b: 上流 64 で RP が Et0/2 へ
    chk("iol v20 up-prio", t.rp["SW03"], "Et0/2")
    t = Topo(v20, E, cost_ovr={("SW03", "Et0/1"): 200}).solve()       # 実測 M4d: 自側 cost 200 で Et0/2 へ
    chk("iol v20 down-cost", t.rp["SW03"], "Et0/2")

    print(f"[stp_model selftest] NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
