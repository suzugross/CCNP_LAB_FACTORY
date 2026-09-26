#!/usr/bin/env python3
"""STP ラボ L4 = MST 世界(BL-076)。gen_stp.py `--world mst` から呼ぶ(ID は GEN-STP-<seed> のまま)。

盤面(ioll2-xe×4・持ち込み機器なし):
    SW01/SW02(DS)・SW03(AS1)= MST リージョン / SW04(AS2)= MST 非対応の旧機(Rapid PVST+)= リージョン境界。
    CIST と MSTI1(VLAN A・C)の root= x、MSTI2(VLAN B)の root= y。MSTI2 は DS 間リンク2 を使う(上流の port-priority)。
モード:
    ts   : 起動時から MST。故障 1〜3 個(下の MFAULTS)。
    build: 初期は全台 Rapid PVST+ の既定値(STP 設定白紙)→ MST 化させる(rapid→MST の実行時移行は PoC で 3/3 安定)。

PoC 第4回(poc/stp/README.md・2026-09-22)で決めたこと:
    ・持ち込み機器は置かない: MST では駐車 VLAN の BPDU も CIST に入り、priority 0 の機器がリージョン全体の CIST root になる。
    ・MST→rapid の実行時移行は Dispute/Desg BLK が出て不安定 → 出題で要求しない(IOS も "Changing STP mode can disrupt
      the traffic and make system unstable" と警告する)。
    ・SW04 の上りは常に `Peer(STP)` 表示(clear でも消えない・公式に記述なし)→ 採点・論点に使わない。
裏どり(★=実機 PoC 第4回):
    PVST シミュレーション= CIST root がリージョン内なら、PVST 側の VLAN2 以降は CIST root より劣位でなければ
      境界が `Bound(PVST) *PVST_Inc`・`PVST Sim. Inconsistent`(全インスタンス)・`%SPANTREE-2-PVSTSIM_FAIL`
      (Cisco「PVST Simulation on MST Switches」と一致 ★N2)。PVST 側を全 VLAN 優位(vlan 1-4094 priority 4096)にしても
      VLAN2 以降が sys-id 分だけ VLAN1 より劣位で不整合のまま(公式の「VLAN2 以降は VLAN1 より優位」規則どおり ★N3)。
    region 不一致(revision/name/instance 対応)= 別リージョン扱い `Bound(RSTP)`・MSTI の root 側ポートは `Mstr` ★N4・N5。
      digest は VLAN 対応だけを反映(revision 違いでは同じ digest)★N4。
    MSTI の port-priority は上流側で効く(`spanning-tree mst 2 port-priority 64`)★s10。MST のパスコストは long(2000000)。
"""
import os
import random
import re

from stp_model import Topo

DS = ["SW01", "SW02"]
AS = ["SW03", "SW04"]
REGION = ["SW01", "SW02", "SW03"]
LEGACY = "SW04"
EDGE = ["Ethernet1/0", "Ethernet1/1", "Ethernet1/2", "Ethernet1/3"]
LINKS = [("SW01", 0, "SW02", 0), ("SW01", 1, "SW02", 1),
         ("SW01", 2, "SW03", 0), ("SW01", 3, "SW04", 0),
         ("SW02", 2, "SW03", 1), ("SW02", 3, "SW04", 1)]
UPLINK = {("SW03", "SW01"): "Ethernet0/0", ("SW03", "SW02"): "Ethernet0/1",
          ("SW04", "SW01"): "Ethernet0/0", ("SW04", "SW02"): "Ethernet0/1"}
DSLINK = ["Ethernet0/0", "Ethernet0/1"]
PRIMARY, SECONDARY = 24576, 28672
# ★CML 上のノード配置(gen_stp と共通・分配を上段/アクセスを下段)。見た目だけで採点に影響しない。
POS = {"SW01": [-480, -200], "SW02": [-120, -200], "SW03": [-520, 40], "SW04": [-80, 40]}
AUDIT_CMD = "show running-config | include ^interface Ethernet|spanning-tree|allowed vlan"
NAMES = ["CAMPUS", "BLDG-A", "HQ-L2", "CORE-EAST", "SITE01"]

MFAULTS = ["m_rev", "m_name", "m_map", "m_mode", "m_pvstsim", "m_cist", "m_pprio_down",
           "m_unmapped", "m_cost", "m_allowed_hole", "loopguard_trip", "guard_swap", "bpduguard_uplink"]
EXCLUSIVE = [{"m_rev", "m_name", "m_map", "m_mode", "m_unmapped"},
             {"m_pprio_down", "guard_swap", "loopguard_trip"}, {"m_cist", "m_pvstsim"}]

SYMPTOM = {
    "m_rev": "リージョン内のはずのスイッチ間で、インスタンスごとの経路の使い分けが効いていない区間がある。",
    "m_name": "リージョン内のはずのスイッチ間で、インスタンスごとの経路の使い分けが効いていない区間がある。",
    "m_map": "特定 VLAN の経路が、設計書のインスタンスの経路と一致しない。",
    "m_mode": "アクセススイッチ 1 台が、リージョンの外にいるように見える。",
    "m_pvstsim": "旧機(SW04)の上りが両方とも使えず、SW04 の VLAN が分配層へ抜けない。",
    "m_cist": "CIST の root が設計書と一致しないとの点検結果がある。",
    "m_pprio_down": "DS 間 2 本の使い分けが設計どおりになっていないとの点検結果がある(前任者は対処済みと報告)。",
    "m_unmapped": "特定 VLAN の経路が、設計書のインスタンスの経路と一致しない。",
    "m_cost": "特定インスタンスの通信が、アクセス層から見て遠回りの経路を通っている。",
    "m_allowed_hole": "特定 VLAN だけ、アクセススイッチ SW03 から他のスイッチへ疎通しない(STP の状態は正常に見える)。",
    "loopguard_trip": "DS 間リンクで、一部インスタンスのポートが転送も待機もしていない状態との点検結果がある。",
    "guard_swap": "DS 間リンクで、一部インスタンスのポートが転送も待機もしていない状態との点検結果がある。",
    "bpduguard_uplink": "アクセススイッチの上りリンクの 1 本が、起動以来一度も使われていない。",
}


def ifn(i):
    return f"Ethernet{i // 4}/{i % 4}"


def short(n):
    return n.replace("Ethernet", "Et")


# ---------------------------------------------------------------------------
def design(rnd):
    A, B, C = rnd.sample([v for v in range(11, 255) if v != 99], 3)
    x = rnd.choice(DS)
    y = DS[1] if x == DS[0] else DS[0]
    return {"A": A, "B": B, "C": C, "vlans": [A, B, C], "x": x, "y": y,
            "name": rnd.choice(NAMES), "rev": rnd.randint(1, 9),
            "edge_vlan": {s: {p: rnd.choice([A, B, C]) for p in EDGE} for s in AS},
            "oct2": rnd.randint(20, 250)}


def svi_ip(d, v, s):
    return f"10.{d['oct2']}.{v}.{int(s[-1])}"


def inst_vlans(d):
    return {1: sorted([d["A"], d["C"]]), 2: [d["B"]]}


def expected(d):
    """{"cist": roles, 1: roles, 2: roles}。roles= {(sw, 'Et0/n'): 'Root'|'Desg'|'Altn'}"""
    E = lambda n: {"name": f"Et0/{n}", "num": n + 1}
    x, y = d["x"], d["y"]
    macs = {s: f"aabb.cc00.{i:02d}00" for i, s in enumerate(REGION + [LEGACY], 1)}
    allk = [(a, E(ia), b, E(ib), "10M") for a, ia, b, ib in LINKS]
    cp = {x: PRIMARY, y: SECONDARY, "SW03": 32768, "SW04": 32769}   # SW04 は VLAN1 の BPDU(32768+1)
    cist = Topo({s: {"prio": cp[s], "mac": macs[s]} for s in cp}, allk, method="long").solve()
    assert cist.root == x
    out = {"cist": cist.role}
    reg = [l for l in allk if LEGACY not in (l[0], l[2])]
    for i, (r, b) in {1: (x, y), 2: (y, x)}.items():
        pr = {r: PRIMARY, b: SECONDARY, "SW03": 32768}
        pp = {(y, "Et0/1"): 64} if i == 2 else {}
        t = Topo({s: {"prio": pr[s], "mac": macs[s]} for s in REGION}, reg, method="long", port_prio=pp).solve()
        assert t.root == r
        role = dict(t.role)
        for s in DS:                                    # 境界ポートは CIST の役割をそのまま継ぐ
            role[(s, "Et0/3")] = cist.role[(s, "Et0/3")]
        out[i] = role
    return out


# ---------------------------------------------------------------------------
def base_state(d):
    x, y = d["x"], d["y"]
    allv = ",".join(str(v) for v in sorted(d["vlans"]))
    st = {}
    for s in REGION + [LEGACY]:
        st[s] = {"mode": "mst" if s in REGION else "rapid-pvst", "ifs": {}, "mstprio": {}, "vprio": {},
                 "long": s == LEGACY,
                 "region": {"name": d["name"], "rev": d["rev"], "map": {k: list(v) for k, v in inst_vlans(d).items()}}
                 if s in REGION else None}
    st[x]["mstprio"] = {0: PRIMARY, 1: PRIMARY, 2: SECONDARY}
    st[y]["mstprio"] = {0: SECONDARY, 1: SECONDARY, 2: PRIMARY}
    for a, ia, b, ib in LINKS:
        for s, i in ((a, ia), (b, ib)):
            st[s]["ifs"][ifn(i)] = {"trunk": True, "allowed": allv, "lines": []}
    for s in DS:
        for p in DSLINK:
            st[s]["ifs"][p]["lines"].append("spanning-tree guard loop")
        for p in ("Ethernet0/2", "Ethernet0/3"):
            st[s]["ifs"][p]["lines"].append("spanning-tree guard root")
    st[y]["ifs"]["Ethernet0/1"]["lines"].append("spanning-tree mst 2 port-priority 64")
    for s in AS:
        for p in EDGE:
            st[s]["ifs"][p] = {"trunk": False, "vlan": d["edge_vlan"][s][p],
                               "lines": ["spanning-tree portfast", "spanning-tree bpduguard enable"]}
    return st


def build_state(d):
    """build: VLAN/trunk/SVI/エッジ所属は構築済み・STP は全台 Rapid PVST+ の既定値。"""
    st = base_state(d)
    for s in st:
        st[s].update({"mode": "rapid-pvst", "mstprio": {}, "vprio": {}, "long": False, "region": None})
        for c in st[s]["ifs"].values():
            c["lines"] = []
    return st


def region_lines(r):
    L = ["spanning-tree mst configuration", f" name {r['name']}", f" revision {r['rev']}"]
    for i in sorted(r["map"]):
        if r["map"][i]:
            L.append(f" instance {i} vlan {','.join(str(v) for v in sorted(r['map'][i]))}")
    return L


def render(d, st, s, seed):
    c = st[s]
    L = [f"! 自動生成(gen_stp --world mst) seed={seed} {s}", "vtp mode transparent"]
    for v in sorted(d["vlans"]):
        L += [f"vlan {v}", f" name DATA{v}"]
    L.append("!")
    if c["region"]:
        L += region_lines(c["region"]) + [" exit", "!"]
    if c["long"]:
        L.append("spanning-tree pathcost method long")
    for i, p in sorted(c["mstprio"].items()):
        L.append(f"spanning-tree mst {i} priority {p}")
    for v, p in sorted(c["vprio"].items()):
        L.append(f"spanning-tree vlan {v} priority {p}")
    L += [f"spanning-tree mode {c['mode']}", "!"]
    for name in sorted(c["ifs"], key=lambda n: (int(n[8]), int(n[10]))):
        f = c["ifs"][name]
        idx = int(name[8]) * 4 + int(name[10])
        L.append(f"interface {{{{ links[{idx}] }}}}")
        if f["trunk"]:
            L += [" switchport trunk encapsulation dot1q", " switchport mode trunk",
                  f" switchport trunk allowed vlan {f['allowed']}"]
        else:
            L += [" switchport mode access", f" switchport access vlan {f['vlan']}"]
        L += [f" {x}" for x in f["lines"]] + [" no shutdown", "!"]
    L += ["interface Ethernet3/3", " spanning-tree bpdufilter enable", "!"]
    for v in sorted(d["vlans"]):
        L += [f"interface Vlan{v}", f" ip address {svi_ip(d, v, s)} 255.255.255.0", " no shutdown", "!"]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
def pick_faults(rnd, want, forced):
    if forced:
        return forced
    pool = MFAULTS[:]
    rnd.shuffle(pool)
    out = []
    for f in pool:
        if any(f in g and any(o in g for o in out) for g in EXCLUSIVE):
            continue
        out.append(f)
        if len(out) == want:
            break
    return out


def inject(rnd, d, st, faults):
    fix, note = {}, []
    x, y, A, B, C = d["x"], d["y"], d["A"], d["B"], d["C"]

    def add(s, conf=(), exe=()):
        f = fix.setdefault(s, {"conf": [], "exec": []})
        f["conf"] += list(conf)
        f["exec"] += list(exe)

    for f in faults:
        if f == "m_rev":
            s = rnd.choice(REGION)
            st[s]["region"]["rev"] = d["rev"] + rnd.choice([1, 10])
            add(s, ["spanning-tree mst configuration", f"revision {d['rev']}", "exit"])
            note.append({"fault": f, "sw": s})
        elif f == "m_name":
            s = rnd.choice(REGION)
            st[s]["region"]["name"] = rnd.choice([d["name"].lower(), d["name"].title(), d["name"] + "1"])
            add(s, ["spanning-tree mst configuration", f"name {d['name']}", "exit"])
            note.append({"fault": f, "sw": s})
        elif f == "m_map":
            s = rnd.choice(REGION)
            v = rnd.choice([A, C])
            st[s]["region"]["map"][1].remove(v)
            st[s]["region"]["map"][2].append(v)
            add(s, ["spanning-tree mst configuration", f"no instance 2 vlan {v}", f"instance 1 vlan {v}", "exit"])
            note.append({"fault": f, "sw": s, "vlan": v})
        elif f == "m_unmapped":
            for s in REGION:
                st[s]["region"]["map"][1].remove(C)
                add(s, ["spanning-tree mst configuration", f"instance 1 vlan {C}", "exit"])
            note.append({"fault": f, "vlan": C})
        elif f == "m_mode":
            st["SW03"]["mode"] = "rapid-pvst"
            add("SW03", ["spanning-tree mode mst"])
            for s in REGION + [LEGACY]:
                add(s, exe=["clear spanning-tree detected-protocols"])
            note.append({"fault": f, "sw": "SW03"})
        elif f == "m_pvstsim":
            v = rnd.choice(d["vlans"])
            st[LEGACY]["vprio"][v] = rnd.choice([0, 4096])
            add(LEGACY, [f"no spanning-tree vlan {v} priority"])
            note.append({"fault": f, "sw": LEGACY, "vlan": v})
        elif f == "m_cist":
            del st[x]["mstprio"][0]
            add(x, [f"spanning-tree mst 0 priority {PRIMARY}"])
            note.append({"fault": f, "sw": x})
        elif f == "m_pprio_down":
            line = "spanning-tree mst 2 port-priority 64"
            st[y]["ifs"]["Ethernet0/1"]["lines"].remove(line)
            st[x]["ifs"]["Ethernet0/1"]["lines"].append(line)
            add(x, ["interface Ethernet0/1", "no spanning-tree mst 2 port-priority"])
            add(y, ["interface Ethernet0/1", line])
            note.append({"fault": f, "sw": x})
        elif f == "m_cost":
            i = rnd.choice([1, 2])
            p = UPLINK[("SW03", x if i == 1 else y)]
            st["SW03"]["ifs"][p]["lines"].append(f"spanning-tree mst {i} cost {rnd.choice([5000000, 8000000])}")
            add("SW03", [f"interface {p}", f"no spanning-tree mst {i} cost"])
            note.append({"fault": f, "sw": "SW03", "inst": i, "port": p})
        elif f == "m_allowed_hole":
            v = rnd.choice([A, C])
            c = st[x]["ifs"]["Ethernet0/2"]
            c["allowed"] = ",".join(str(w) for w in sorted(d["vlans"]) if w != v)
            add(x, ["interface Ethernet0/2", f"switchport trunk allowed vlan add {v}"])
            note.append({"fault": f, "sw": x, "vlan": v})
        elif f == "loopguard_trip":
            s, p = rnd.choice(DS), rnd.choice(DSLINK)
            st[s]["ifs"][p]["lines"].append("spanning-tree bpdufilter enable")
            add(s, [f"interface {p}", "no spanning-tree bpdufilter enable"])
            note.append({"fault": f, "sw": s, "port": p})
        elif f == "guard_swap":
            s, p = rnd.choice(DS), rnd.choice(DSLINK)
            L = st[s]["ifs"][p]["lines"]
            L[L.index("spanning-tree guard loop")] = "spanning-tree guard root"
            add(s, [f"interface {p}", "spanning-tree guard loop"])
            note.append({"fault": f, "sw": s, "port": p})
        elif f == "bpduguard_uplink":
            s = rnd.choice(AS)
            p = rnd.choice(["Ethernet0/0", "Ethernet0/1"])
            st[s]["ifs"][p]["lines"] += ["spanning-tree portfast", "spanning-tree bpduguard enable"]
            add(s, [f"interface {p}", "no spanning-tree bpduguard enable", "no spanning-tree portfast",
                    "shutdown", "no shutdown"])
            note.append({"fault": f, "sw": s, "port": p})
        else:
            raise SystemExit(f"unknown fault {f}")
    return note, fix


def build_fix(d):
    ok = base_state(d)
    fix = {}
    for s in REGION + [LEGACY]:
        c = ok[s]
        conf = []
        if c["region"]:
            conf += [x.strip() for x in region_lines(c["region"])] + ["exit"]
        if c["long"]:
            conf.append("spanning-tree pathcost method long")
        conf += [f"spanning-tree mst {i} priority {p}" for i, p in sorted(c["mstprio"].items())]
        for name, f in sorted(c["ifs"].items()):
            if f["lines"]:
                conf += [f"interface {name}"] + f["lines"]
        if s in REGION:
            conf += ["exit", "spanning-tree mode mst"]
        fix[s] = {"conf": conf, "exec": ["clear spanning-tree detected-protocols"]}
    return fix


# ---------------------------------------------------------------------------
P = {"root": 4, "backup": 1, "region": 5, "role": 3, "legacy": 2, "incon": 1, "steer": 7,
     "long": 1, "ds": 5, "as": 3, "ping": 3}


def grading(d, pid):
    ex = expected(d)
    rs = {"Root": "Root FWD", "Desg": "Desg FWD", "Altn": "Altn BLK"}
    x, y = d["x"], d["y"]
    allv = ",".join(str(v) for v in sorted(d["vlans"]))
    trunks = {s: sorted({ifn(i) for a, ia, b, ib in LINKS for w, i in ((a, ia), (b, ib)) if w == s})
              for s in REGION + [LEGACY]}
    iv = inst_vlans(d)
    ck = []
    for n, sw, lab in ((0, x, "the CIST"), (1, x, "MST1"), (2, y, "MST2")):
        ck.append({"name": f"{'CIST' if n == 0 else f'インスタンス{n}'}: root が設計どおり {sw}", "node": sw,
                   "command": f"show spanning-tree mst {n}",
                   "raw": [{"regex": rf"Root\s+this switch for {lab}"}], "points": P["root"]})
    for n, sw in ((0, y), (1, y), (2, x)):
        ck.append({"name": f"{'CIST' if n == 0 else f'インスタンス{n}'}: 予備 root({sw})の priority が {SECONDARY}",
                   "node": sw, "command": f"show spanning-tree mst {n}",
                   "raw": [{"regex": rf"Bridge\s+address \S+\s+priority\s+{SECONDARY + n}\s"}], "points": P["backup"]})
    for s in REGION:
        raw = [{"regex": rf"Name\s+\[{re.escape(d['name'])}\]"}, {"regex": rf"Revision\s+{d['rev']}\s"}]
        for i, vs in iv.items():
            raw.append({"regex": rf"(?m)^{i}\s+{','.join(str(v) for v in vs)}\s*$"})
        ck.append({"name": f"{s}: MST リージョン設定(名前・リビジョン・インスタンス対応)が設計どおり", "node": s,
                   "command": "show spanning-tree mst configuration", "raw": raw, "points": P["region"]})
    for s in REGION:
        for n in (0, 1, 2):
            roles = ex["cist"] if n == 0 else ex[n]
            raw = [{"regex": rf"(?m)^{p}\s+{rs[r]}\s"} for (w, p), r in sorted(roles.items()) if w == s]
            raw.append({"not_regex": r"(?m)^Et0/[0-3]\s.*(BKN|_Inc|Bound\(RSTP\))"})
            if s in DS:
                raw.append({"regex": r"(?m)^Et0/3\s.*Bound\(PVST\)"})
                raw.append({"not_regex": r"(?m)^Et0/[0-2]\s.*Bound"})
            ck.append({"name": f"{s}: {'CIST' if n == 0 else f'インスタンス{n}'} のポートの役割と状態が設計どおり",
                       "node": s, "command": f"show spanning-tree mst {n}", "raw": raw, "points": P["role"]})
    for v in sorted(d["vlans"]):
        raw = [{"regex": rf"Root ID\s+Priority\s+{PRIMARY}\b"}]
        raw += [{"regex": rf"(?m)^{p}\s+{rs[r]}\s"} for (w, p), r in sorted(ex["cist"].items()) if w == LEGACY]
        raw.append({"not_regex": r"(?m)^Et0/[01]\s.*(BKN|_Inc)"})
        ck.append({"name": f"SW04(旧機): VLAN{v} の root が CIST root で、上りの役割が設計どおり", "node": LEGACY,
                   "command": f"show spanning-tree vlan {v}", "raw": raw, "points": P["legacy"]})
    for s in REGION + [LEGACY]:
        ck.append({"name": f"{s}: 不整合(inconsistent)状態のポートが無い", "node": s,
                   "command": "show spanning-tree inconsistentports",
                   "raw": [{"regex": r"in the system\s*:\s*0\b"}], "points": P["incon"]})
    ck.append({"name": f"インスタンス2: DS 間はリンク2(Et0/1)で転送(下流 {x} の root port が Et0/1)", "node": x,
               "command": "show spanning-tree mst 2",
               "raw": [{"regex": r"(?m)^Et0/1\s+Root FWD\s"}, {"regex": r"(?m)^Et0/0\s+Altn BLK\s"}], "points": P["steer"]})
    ck.append({"name": "SW04(旧機): パスコスト方式が long", "node": LEGACY, "command": "show spanning-tree summary",
               "raw": [{"regex": r"Configured Pathcost method used is long"}], "points": P["long"]})

    def common(s):
        out = [{"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? switchport trunk allowed vlan {allv}\r?\n"} for p in trunks[s]]
        out.append({"not_regex": r"(?m)^ spanning-tree ((mst|vlan) \S+ )?cost "})
        out.append({"not_regex": r"interface Ethernet[0-2]/\d\r?\n(?: .*\r?\n)*? spanning-tree bpdufilter"})
        return out
    for s in DS:
        raw = [{"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? spanning-tree guard loop"} for p in DSLINK]
        raw += [{"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? spanning-tree guard root"} for p in ("Ethernet0/2", "Ethernet0/3")]
        raw += common(s)
        ck.append({"name": f"{s}: 保護方針(DS 間= loop guard / AS 向き= root guard)・許可 VLAN・個別コスト無し・bpdufilter 無し",
                   "node": s, "command": AUDIT_CMD, "raw": raw, "points": P["ds"]})
    for s in AS:
        raw = []
        for p in EDGE:
            raw.append({"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? spanning-tree portfast"})
            raw.append({"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? spanning-tree bpduguard enable"})
        raw.append({"not_regex": r"(?m)^spanning-tree (mst|vlan) \S+ priority"})
        raw += common(s)
        ck.append({"name": f"{s}: エッジ= portfast+BPDU ガード・priority 設定無し・許可 VLAN・個別コスト無し",
                   "node": s, "command": AUDIT_CMD, "raw": raw, "points": P["as"]})
    for v in sorted(d["vlans"]):
        ck.append({"name": f"VLAN{v}: SW03 → SW04 の SVI 間疎通", "node": "SW03",
                   "command": f"ping {svi_ip(d, v, 'SW04')} repeat 5",
                   "raw": [{"regex": r"Success rate is (100|80) percent"}], "points": P["ping"]})
    total = sum(c["points"] for c in ck)
    assert total == 100, total
    for c in ck:
        for r in c["raw"]:
            re.compile(list(r.values())[0])
    return {"problem": pid, "total_points": 100, "defaults": {"genie_os": "iosxe"}, "checks": ck}


# ---------------------------------------------------------------------------
def task_md(d, pid, mode, faults):
    x, y, A, B, C = d["x"], d["y"], d["A"], d["B"], d["C"]
    vls = ",".join(str(v) for v in sorted(d["vlans"]))
    design_rows = [
        f"| MST リージョン | SW01・SW02・SW03。名前 `{d['name']}`・リビジョン {d['rev']}。インスタンス1= VLAN{A}・VLAN{C}、インスタンス2= VLAN{B}(それ以外の VLAN は IST) |",
        "| SW04 | MST 非対応の旧機。Rapid PVST+ のまま運用する(リージョン外)。パスコスト方式は long |",
        f"| CIST・インスタンス1 | root= {x}(priority {PRIMARY})・予備 root= {y}(priority {SECONDARY}) |",
        f"| インスタンス2 | root= {y}(priority {PRIMARY})・予備 root= {x}(priority {SECONDARY}) |",
        "| アクセス層(SW03・SW04)の priority | 既定のまま(どの VLAN・インスタンスでも root にならない) |",
        "| DS 間 2 本の使い分け | 正常時、インスタンス1 はリンク1(Et0/0 同士)、インスタンス2 はリンク2(Et0/1 同士)で転送する。ポート単位・インスタンス単位のパスコスト変更は使用しない |",
        "| DS 間ポート | BPDU が途絶えても転送状態へ移行させない(両端) |",
        "| DS のアクセス向きポート(Et0/2・Et0/3) | アクセス側から優位な BPDU を受けても root の座を明け渡さない |",
        "| アクセスのエッジ(Et1/0〜Et1/3) | 端末の接続時は待たずに転送を始める。BPDU を受けたら直ちに遮断する |",
        f"| trunk | 802.1Q・許可 VLAN は {vls} のみ(全 trunk 共通) |"]
    if mode == "ts":
        L = [f"# 障害対応 {pid} : MST リージョンと旧機の境界が設計書と一致しない", "",
             "## 状況",
             "分配層 2 台(SW01・SW02)とアクセス層 2 台(SW03・SW04)のキャンパス L2 です。SW01〜SW03 は MST、"
             "SW04 は MST 非対応の旧機(Rapid PVST+)で、リージョンの境界になっています。",
             "定期点検の結果、スパニングツリーの状態が設計書と一致しないことが判明しました。運用から次の申告も上がっています。", ""]
        seen = []
        for f in faults:
            if SYMPTOM[f] not in seen:
                seen.append(SYMPTOM[f])
        L += [f"> - {s}" for s in seen]
        L += ["", "設計書どおりの状態に復旧してください。**原因は 1 か所とは限りません。**", "", "## 設計書(抜粋)", "",
              "| 項目 | 設計 |", "|---|---|"] + design_rows
    else:
        L = [f"# 構築 {pid} : MST リージョンの導入(旧機との共存)", "",
             "## 状況",
             "分配層 2 台(SW01・SW02)とアクセス層 2 台(SW03・SW04)のキャンパス L2 に MST を導入します。",
             f"VLAN({vls})・trunk・SVI・エッジポートの所属 VLAN は構築済みで、スパニングツリーは全台とも既定値(Rapid PVST+)のままです。",
             "SW04 は MST 非対応の旧機のため、Rapid PVST+ のまま残します。", "",
             "次の要件書に従って設定してください。実現手段は問いませんが、要件書に反する設定は減点します。", "",
             "## 要件書", "", "| 項目 | 要件 |", "|---|---|"] + design_rows
    L += ["", "## 構成台帳", "", "| 機器 | 役割 | 配線 |", "|---|---|---|",
          "| SW01 | 分配 DS1(MST) | Et0/0・Et0/1→SW02 / Et0/2→SW03 / Et0/3→SW04 |",
          "| SW02 | 分配 DS2(MST) | Et0/0・Et0/1→SW01 / Et0/2→SW03 / Et0/3→SW04 |",
          "| SW03 | アクセス AS1(MST) | Et0/0→SW01 / Et0/1→SW02 / Et1/0〜Et1/3= エッジ |",
          "| SW04 | アクセス AS2(旧機・Rapid PVST+) | Et0/0→SW01 / Et0/1→SW02 / Et1/0〜Et1/3= エッジ |", "",
          "SVI(疎通確認用): " + " / ".join(f"VLAN{v}= 10.{d['oct2']}.{v}.<SW 番号>/24" for v in sorted(d["vlans"])), "",
          "## 注意", "- 管理 VLAN(999)・各機の Ethernet3/3 には触れないこと。",
          "- SW04 のスパニングツリーのモードは変更しないこと。", "",
          "## ログイン / 採点",
          "CML コンソール、または管理 IP へ telnet(user SUZUKI / pass CCNP。管理 IP は出題時の割当表を参照)。", "```",
          f"scripts/lab.sh grade {pid}", "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------
def generate(seed, mode, nfaults, forced):
    """(files, meta)。files= {相対パス: 内容}。gen_stp.build が書き出す。"""
    rnd = random.Random(seed)
    d = design(rnd)
    if mode == "ts":
        st = base_state(d)
        faults = pick_faults(rnd, nfaults or rnd.choice([2, 3]), forced)
        note, fix = inject(rnd, d, st, faults)
        diff, topics, title = 5, ["mst", "troubleshooting"], f"MST 境界 障害対応 (seed={seed})"
    else:
        st = build_state(d)
        faults, note, fix = [], {"world": "mst"}, build_fix(d)
        diff, topics, title = 5, ["mst", "build"], f"MST 導入 構築 (seed={seed})"
    pid = f"GEN-STP-{seed}"
    initial = {s: render(d, st, s, seed) for s in REGION + [LEGACY]}
    return {"pid": pid, "d": d, "faults": faults, "note": note, "fix": fix, "initial": initial,
            "grading": grading(d, pid), "task": task_md(d, pid, mode, faults), "diff": diff, "topics": topics,
            "title": title, "nodes": REGION + [LEGACY],
            "links": [{"a": a, "a_if": ia, "b": b, "b_if": ib} for a, ia, b, ib in LINKS],
            "positions": dict(POS)}


def selftest():
    ng = 0
    for seed in range(1, 201):
        for forced in [None] + [[f] for f in MFAULTS] + ["build"]:
            try:
                if forced == "build":
                    g = generate(seed, "build", 0, None)
                    txt = "".join(g["initial"].values())
                    assert "spanning-tree mst" not in txt and "guard" not in txt and "priority" not in txt
                    allc = "\n".join(x for f in g["fix"].values() for x in f["conf"])
                    assert allc.count("spanning-tree mode mst") == 3 and "pathcost method long" in allc
                    continue
                base = generate(seed, "ts", 0, ["m_cost"])      # 1 故障で基準と差分を比べる
                g = generate(seed, "ts", 0, forced)
                for grp in EXCLUSIVE:
                    assert len(grp & set(g["faults"])) <= 1, g["faults"]
                d = g["d"]
                ok = {s: render(d, base_state(d), s, seed) for s in REGION + [LEGACY]}
                assert ok != g["initial"], f"故障が構成に現れない {g['faults']}"
                ex = expected(d)
                assert ex[2][(d["x"], "Et0/1")] == "Root" and ex[1][(d["y"], "Et0/0")] == "Root"
                assert ex["cist"][("SW04", "Et0/" + UPLINK[("SW04", d["x"])][-1])] == "Root"
            except AssertionError as e:
                ng += 1
                print(f"NG mst seed={seed} forced={forced}: {e}")
    print(f"selftest(mst): {200 * (len(MFAULTS) + 2)} cases NG={ng}")
    return ng
