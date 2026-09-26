#!/usr/bin/env python3
"""STP ラボ生成器(BL-076・U-A3 L1〜L4)— `GEN-STP-<seed>`。

盤面(ioll2-xe×5・telnet 採点・ホスト無し):
    SW01(DS1) ==Et0/0,Et0/1== SW02(DS2)       DS 間 2 本(リンク1= Et0/0 / リンク2= Et0/1)
    SW01 Et0/2 - SW03 Et0/0    SW02 Et0/2 - SW03 Et0/1     SW03/SW04 = アクセス(2 系統上り)
    SW01 Et0/3 - SW04 Et0/0    SW02 Et0/3 - SW04 Et0/1     AS のエッジ = Et1/0〜Et1/3
    SW05 = 持ち込みスイッチ(管理外)。どちらかの AS のエッジ 1 本(駐車 VLAN 99= trunk に載らない)に常時接続。
    データ VLAN に置くと SW05 が root を奪い、一括設定の途中で bpduguard が発動した AS に「root port 無しの
    古い root 情報」が固着して DS の root guard が ROOT_Inc のまま戻らない IOL の挙動が 2/2 で再現した(2026-09-22)。
正しい状態では、そのエッジポートは bpduguard で err-disabled になっている(監査ポート方式・
poc/stp/README.md 第3回 T5)。採点は exec の show だけで完結する(collect_telnet は config 不可)。

モード:
  --mode ts   : L3 実務 TS。設計どおりの構成に故障 1〜3 個を入れる(本版で実装)。
  --mode build --level 1: L1 最小構築(全台 pvst から Rapid PVST+・root/予備 root・エッジ PortFast+BPDU ガード)。
  --mode build --level 2: L2 実務構築(要件書駆動・手段自由= long 方式・DS 間の使い分け(個別コスト禁止
                          → 上流の port-priority しか無い)・root/loop guard・errdisable 自動復旧禁止・pvst 混在)。
  --world mst : L4(MST リージョン+旧機の境界)= gen_stp_mst.py。--mode ts / build の両方。

設計の正典= problems/_drafts/STP-SERIES.design.md §6。期待値は stp_model.py(紙面 P2 の計算器)で導出し、
PoC 第3回 T1 で 4 台 24 ポートが実機と一致することを確認済み。

裏どり(CLAUDE.md 作問の裏どり・論点ごと。★=実機 poc/stp で測定):
  root primary/secondary の数値化・port-priority は上流側・cost は自分の受信ポート ★M2〜M4
  root guard は上位 BPDU を受けた VLAN で ROOT_Inc ★M9 / loop guard は BPDU 途絶で LOOP_Inc ★M10・T6
  IF の guard は後勝ちで 1 つ ★M10c / bpduguard+bpdufilter は filter が勝つ ★M8・T5b
  bpduguard は trunk にも効く(portfast は trunk に効かない) ★P3・M17
  pvst 混在= Peer(STP)・clear detected-protocols は打った側だけ ★M14
  allowed vlan の片側欠落= root port が迂回路へ ★T4 / native 不一致は PVID_Inc が出ず不採用 ★T3
  IOL の実ループは嵐にならない(CPU 0%)→ 誤解法は構造チェックで拾う ★T6b
  Cisco 公式: Catalyst 9300 STP Configuration Guide(root guard/loop guard/BPDU guard/filter の節)

故障カタログ(ts):
  root_hijack     : AS に `spanning-tree vlan V priority 4096` → DS 下りの root guard が ROOT_Inc
  secondary_only  : VLAN C の root 予定 DS に priority 行が無い → 予備(28672)の DS が root
  pprio_downstream: リンク2 寄せの port-priority を下流 DS に入れている(効かない)
  guard_swap      : DS 間ポートの guard が loop でなく root → 相手が root の VLAN で ROOT_Inc
  bpduguard_uplink: AS 上りに portfast+bpduguard → 起動時 err-disabled
  rogue_leak      : 持ち込み機器のポートで bpduguard が効かない(filter 併用 / guard 欠落)
  mode_mismatch   : AS 1 台が pvst → Peer(STP)
  cost_skew       : AS 上りに VLAN cost → root port が他方の DS へ
  loopguard_trip  : DS 間ポートに bpdufilter の残骸 → 対向 LOOP_Inc(誤解法= loop guard 撤去で実ループ)
  allowed_skew    : DS 下りの allowed vlan から 1 VLAN 欠落(片側) → AS の root port が迂回

使い方: gen_stp.py --repo . --seed N [--mode ts] [--faults K] [--fault a,b] [--selftest]
"""
import argparse
import json
import os
import random
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stp_model import Topo  # noqa: E402

DS = ["SW01", "SW02"]
AS = ["SW03", "SW04"]
ROGUE = "SW05"
# ★--image で切り替える命名(ioll2= Ethernet / IOSvL2= GigabitEthernet。スロット配置は同じ)
PFX, SH = "Ethernet", "Et"
EDGE = []            # エッジ(links[4..7])
DSLINK = []          # DS 間 2 本
UPLINK, DOWNLINK = {}, {}
MGMT_IF, AUDIT_CMD = "", ""


IMAGE_FAMILY = {"Ethernet": "iol", "GigabitEthernet": "iosv"}   # problem.yml の image_family


def set_image(image):
    """image= iol(ioll2・Et) / iosv(IOSvL2・Gi)。IF 名だけが変わる(スロット割当は共通)。"""
    global PFX, SH, EDGE, DSLINK, UPLINK, DOWNLINK, MGMT_IF, AUDIT_CMD
    PFX, SH = ("Ethernet", "Et") if image == "iol" else ("GigabitEthernet", "Gi")
    EDGE = [f"{PFX}1/{i}" for i in range(4)]
    DSLINK = [f"{PFX}0/0", f"{PFX}0/1"]
    UPLINK = {("SW03", "SW01"): f"{PFX}0/0", ("SW03", "SW02"): f"{PFX}0/1",
              ("SW04", "SW01"): f"{PFX}0/0", ("SW04", "SW02"): f"{PFX}0/1"}
    DOWNLINK = {("SW01", "SW03"): f"{PFX}0/2", ("SW01", "SW04"): f"{PFX}0/3",
                ("SW02", "SW03"): f"{PFX}0/2", ("SW02", "SW04"): f"{PFX}0/3"}
    MGMT_IF = f"{PFX}3/3"
    AUDIT_CMD = f"show running-config | include ^interface {PFX}|spanning-tree|allowed vlan"
PRIMARY, SECONDARY = 24576, 28672
# ★CML 上のノード配置(2026-09-26 ユーザ再配置のとおり)= 分配 2 台を上段・アクセス 2 台を下段。
#   持ち込み機器は接続先 AS の下。座標は見た目だけで採点には影響しない(gen_cml_lab.layout が使う)。
POS = {"SW01": [-480, -200], "SW02": [-120, -200], "SW03": [-520, 40], "SW04": [-80, 40]}
ROGUE_POS = {"SW03": [-560, 260], "SW04": [-40, 260]}
PVST_START = False
PARK = 99          # 未使用ポートの駐車 VLAN(AS にだけ作る・trunk に載せない)

# 物理配線(links[i] の i = ioll2 のスロット順。Et0/0=0 … Et1/0=4)
LINKS = [("SW01", 0, "SW02", 0), ("SW01", 1, "SW02", 1),
         ("SW01", 2, "SW03", 0), ("SW01", 3, "SW04", 0),
         ("SW02", 2, "SW03", 1), ("SW02", 3, "SW04", 1)]

FAULTS = ["root_hijack", "secondary_only", "pprio_downstream", "guard_swap", "bpduguard_uplink",
          "rogue_leak", "mode_mismatch", "cost_skew", "loopguard_trip", "allowed_skew"]
# 同じポート/同じ論点を奪い合う組(同時に選ばない)
EXCLUSIVE = [{"guard_swap", "loopguard_trip", "pprio_downstream"}, {"root_hijack", "cost_skew"}]


set_image("iol")                         # 既定(モジュール読み込み時)


def ifn(i):
    return f"{PFX}{i // 4}/{i % 4}"


def slot_port(name):
    """"...0/2" → (0, 2)。IF 名の接頭辞(Ethernet / GigabitEthernet)に依存しない。"""
    m = re.search(r"(\d+)/(\d+)$", name)
    return int(m.group(1)), int(m.group(2))


def short(name):
    return name.replace(PFX, SH)


# ---------------------------------------------------------------------------
# 設計(seed で決まる値)
# ---------------------------------------------------------------------------
def design(rnd):
    vl = rnd.sample([v for v in range(11, 255) if v != 99], 3)   # 第 3 オクテット= VLAN ID
    A, B, C = vl
    x = rnd.choice(DS)                       # VLAN A/C の root
    y = DS[1] if x == DS[0] else DS[0]       # VLAN B の root
    rogue_as = rnd.choice(AS)
    rogue_port = rnd.choice(EDGE)
    edge_vlan = {s: {p: rnd.choice([A, B, C]) for p in EDGE} for s in AS}
    edge_vlan[rogue_as][rogue_port] = PARK
    oct2 = rnd.randint(20, 250)
    return {"A": A, "B": B, "C": C, "vlans": [A, B, C], "root": {A: x, C: x, B: y},
            "backup": {A: y, C: y, B: x}, "rogue_as": rogue_as, "rogue_port": rogue_port,
            "edge_vlan": edge_vlan, "oct2": oct2}


def svi_ip(d, v, s):
    return f"10.{d['oct2']}.{v}.{int(s[-1])}"


def expected_roles(d, steer=True):
    """設計どおりの状態の VLAN ごとの role(stp_model)。{vlan: {(sw, 'Et0/0'): role}}
    steer= VLAN B をリンク2 へ寄せる要件があるか(ts・build L2 は有り / build L1 は無し)。"""
    E = lambda n: {"name": f"{SH}0/{n}", "num": n + 1}
    links = [(a, E(ia), b, E(ib), "10M") for a, ia, b, ib in LINKS]
    out = {}
    for v in d["vlans"]:
        sws = {}
        for i, s in enumerate(DS + AS, 1):
            prio = PRIMARY if d["root"][v] == s else SECONDARY if d["backup"][v] == s else 32768
            sws[s] = {"prio": prio, "mac": f"aabb.cc00.{i:02d}00"}
        pp = {(d["root"][v], f"{SH}0/1"): 64} if steer and v == d["B"] else {}
        t = Topo(sws, links, port_prio=pp, vlan=v).solve()
        assert t.root == d["root"][v]
        out[v] = t.role
    return out


# ---------------------------------------------------------------------------
# 構成(正しい状態のモデル → 故障で書き換え → 描画)
# ---------------------------------------------------------------------------
def base_state(d):
    st = {}
    for s in DS + AS:
        st[s] = {"mode": "rapid-pvst", "prio": {}, "ifs": {}}
    for v in d["vlans"]:
        st[d["root"][v]]["prio"][v] = PRIMARY
        st[d["backup"][v]]["prio"][v] = SECONDARY
    allv = ",".join(str(v) for v in sorted(d["vlans"]))
    for a, ia, b, ib in LINKS:
        for s, i in ((a, ia), (b, ib)):
            st[s]["ifs"][ifn(i)] = {"trunk": True, "allowed": allv, "lines": []}
    for s in DS:
        for p in DSLINK:
            st[s]["ifs"][p]["lines"].append("spanning-tree guard loop")
        for p in (f"{PFX}0/2", f"{PFX}0/3"):
            st[s]["ifs"][p]["lines"].append("spanning-tree guard root")
    st[d["root"][d["B"]]]["ifs"][DSLINK[1]]["lines"].append(
        f"spanning-tree vlan {d['B']} port-priority 64")
    for s in AS:
        for p in EDGE:
            st[s]["ifs"][p] = {"trunk": False, "vlan": d["edge_vlan"][s][p],
                               "lines": ["spanning-tree portfast", "spanning-tree bpduguard enable"]}
    return st


def pick_faults(rnd, want, forced):
    if forced:
        return forced
    pool = FAULTS[:]
    rnd.shuffle(pool)
    out = []
    for f in pool:
        if any(f in g and out and any(o in g for o in out) for g in EXCLUSIVE):
            continue
        out.append(f)
        if len(out) == want:
            break
    return out


def inject(rnd, d, st, faults):
    """故障を入れ、(症状メモ, 解答 conf) を返す。fix は switch → {"conf": [...], "exec": [...]}"""
    fix = {}
    note = []

    def add(s, conf=(), exe=()):
        f = fix.setdefault(s, {"conf": [], "exec": []})
        f["conf"] += list(conf)
        f["exec"] += list(exe)

    A, B, C = d["A"], d["B"], d["C"]
    for f in faults:
        if f == "root_hijack":
            s, v = rnd.choice(AS), rnd.choice(d["vlans"])
            st[s]["prio"][v] = rnd.choice([0, 4096])
            add(s, [f"no spanning-tree vlan {v} priority"])
            note.append({"fault": f, "sw": s, "vlan": v})
        elif f == "secondary_only":
            r = d["root"][C]
            del st[r]["prio"][C]
            add(r, [f"spanning-tree vlan {C} priority {PRIMARY}"])
            note.append({"fault": f, "sw": r, "vlan": C})
        elif f == "pprio_downstream":
            up, dn = d["root"][B], d["backup"][B]
            line = f"spanning-tree vlan {B} port-priority 64"
            st[up]["ifs"][DSLINK[1]]["lines"].remove(line)
            st[dn]["ifs"][DSLINK[1]]["lines"].append(line)
            add(dn, [f"interface {DSLINK[1]}", f"no spanning-tree vlan {B} port-priority"])
            add(up, [f"interface {DSLINK[1]}", line])
            note.append({"fault": f, "sw": dn})
        elif f == "guard_swap":
            s = rnd.choice(DS)
            p = rnd.choice(DSLINK)
            L = st[s]["ifs"][p]["lines"]
            L[L.index("spanning-tree guard loop")] = "spanning-tree guard root"
            add(s, [f"interface {p}", "spanning-tree guard loop"])
            note.append({"fault": f, "sw": s, "port": p})
        elif f == "bpduguard_uplink":
            s = rnd.choice(AS)
            p = rnd.choice(DSLINK)   # AS の上り 2 本(スロット配置は DS 間と同じ 0/0・0/1)
            st[s]["ifs"][p]["lines"] += ["spanning-tree portfast", "spanning-tree bpduguard enable"]
            add(s, [f"interface {p}", "no spanning-tree bpduguard enable", "no spanning-tree portfast",
                    "shutdown", "no shutdown"])
            note.append({"fault": f, "sw": s, "port": p})
        elif f == "rogue_leak":
            s, p = d["rogue_as"], d["rogue_port"]
            kind = rnd.choice(["filter", "noguard"])
            if kind == "filter":
                st[s]["ifs"][p]["lines"].append("spanning-tree bpdufilter enable")
                add(s, [f"interface {p}", "no spanning-tree bpdufilter enable"])
            else:
                st[s]["ifs"][p]["lines"] = ["spanning-tree portfast"]
                add(s, [f"interface {p}", "spanning-tree bpduguard enable"])
            note.append({"fault": f, "sw": s, "port": p, "kind": kind})
        elif f == "mode_mismatch":
            s = rnd.choice(AS)
            st[s]["mode"] = "pvst"
            add(s, ["spanning-tree mode rapid-pvst"])
            for t in DS + AS:
                add(t, exe=["clear spanning-tree detected-protocols"])
            note.append({"fault": f, "sw": s})
        elif f == "cost_skew":
            s, v = rnd.choice(AS), rnd.choice([A, C])
            p = UPLINK[(s, d["root"][v])]
            st[s]["ifs"][p]["lines"].append(f"spanning-tree vlan {v} cost {rnd.choice([250, 300, 500])}")
            add(s, [f"interface {p}", f"no spanning-tree vlan {v} cost"])
            note.append({"fault": f, "sw": s, "vlan": v, "port": p})
        elif f == "loopguard_trip":
            s = rnd.choice(DS)
            p = rnd.choice(DSLINK)
            st[s]["ifs"][p]["lines"].append("spanning-tree bpdufilter enable")
            add(s, [f"interface {p}", "no spanning-tree bpdufilter enable"])
            note.append({"fault": f, "sw": s, "port": p})
        elif f == "allowed_skew":
            s, a = rnd.choice(DS), rnd.choice(AS)
            v = rnd.choice([vv for vv in d["vlans"] if d["root"][vv] == s])
            p = DOWNLINK[(s, a)]
            st[s]["ifs"][p]["allowed"] = ",".join(str(x) for x in sorted(d["vlans"]) if x != v)
            add(s, [f"interface {p}", f"switchport trunk allowed vlan add {v}"])
            note.append({"fault": f, "sw": s, "port": p, "vlan": v})
        else:
            raise SystemExit(f"unknown fault {f}")
    return note, fix


# ---------------------------------------------------------------------------
# 構築モード(L1/L2): STP 設定を白紙にした初期状態と、設計書どおりの模範解答
# ---------------------------------------------------------------------------
def build_state(rnd, d, level):
    """VLAN・trunk(許可 VLAN 絞り= mgmt 隔離)・エッジの access VLAN・SVI は構築済み。STP だけ白紙。
    初期は全台 Rapid PVST+ の既定値(下の PVST_START 参照)。"""
    st = base_state(d)
    # ★2026-09-22 実測: 実行中の pvst→rapid 移行を含めると IOL が不安定(提案/合意の不成立で Desg BLK が固着・
    # 約 40 秒周期のトポロジ変更・IOL プロセスの停止 2 回)。起動時から rapid の TS では起きない。
    # → 旧方式からの移行は出題しない(PVST_START=False)。移行を題材にするなら TS の mode_mismatch(1 台だけ)。
    old = set() if not PVST_START else set(DS + AS) if level == "b1" else set(rnd.sample(DS + AS, rnd.randint(1, 3)))
    for sw in DS + AS:
        st[sw]["prio"] = {}
        st[sw]["mode"] = "pvst" if sw in old else "rapid-pvst"
        for c in st[sw]["ifs"].values():
            c["lines"] = []
    return st, sorted(old)


def build_fix(d, level):
    """模範解答(設計書どおり)。solution/fix.json の fix と同じ形。"""
    ok = base_state(d)
    fix = {}
    for sw in DS + AS:
        conf = ["spanning-tree mode rapid-pvst"]
        if level == "b2":
            conf.append("spanning-tree pathcost method long")
        conf += [f"spanning-tree vlan {v} priority {p}" for v, p in sorted(ok[sw]["prio"].items())]
        for name, c in sorted(ok[sw]["ifs"].items()):
            lines = c["lines"]
            if level == "b1":
                lines = [x for x in lines if not x.startswith("spanning-tree guard") and "port-priority" not in x]
            if lines:
                conf += [f"interface {name}"] + lines
        fix[sw] = {"conf": conf, "exec": ["clear spanning-tree detected-protocols"]}
    return fix


def render(d, st, s, seed):
    L = [f"! 自動生成(gen_stp) seed={seed} {s}", "vtp mode transparent"]
    for v in sorted(d["vlans"]):
        L += [f"vlan {v}", f" name DATA{v}"]
    if s in AS:
        L += [f"vlan {PARK}", " name PARK"]
    L += ["!", f"spanning-tree mode {st[s]['mode']}", "spanning-tree extend system-id"]
    for v, p in sorted(st[s]["prio"].items()):
        L.append(f"spanning-tree vlan {v} priority {p}")
    L.append("!")
    for name in sorted(st[s]["ifs"], key=slot_port):
        c = st[s]["ifs"][name]
        sl, po = slot_port(name)
        idx = sl * 4 + po
        L.append(f"interface {{{{ links[{idx}] }}}}")
        if c["trunk"]:
            L += [" switchport trunk encapsulation dot1q", " switchport mode trunk",
                  f" switchport trunk allowed vlan {c['allowed']}"]
        else:
            L += [" switchport mode access", f" switchport access vlan {c['vlan']}"]
        L += [f" {x}" for x in c["lines"]] + [" no shutdown", "!"]
    L += [f"interface {MGMT_IF}", " spanning-tree bpdufilter enable", "!"]
    for v in sorted(d["vlans"]):
        L += [f"interface Vlan{v}", f" ip address {svi_ip(d, v, s)} 255.255.255.0", " no shutdown", "!"]
    return "\n".join(L) + "\n"


def render_rogue(seed):
    return "\n".join([f"! 自動生成(gen_stp) seed={seed} SW05 = 持ち込みスイッチ(管理外)",
                      # priority 0= 接続先(駐車 VLAN 99)で root になり BPDU を出し続ける→ bpduguard が確実に発動。
                      # 最弱にすると root port 側になり RSTP では定期 BPDU を出さず、後から入れた bpduguard が
                      # 発動しない(2026-09-22 実測)。ioll2 には EEM が無くポートの定期上げ下げもできない。
                      "spanning-tree vlan 1 priority 0",
                      "interface {{ links[0] }}", " switchport mode access", " no shutdown", ""])


# ---------------------------------------------------------------------------
# 採点
# ---------------------------------------------------------------------------
# level ごとの配点(合計 100)。ts= 障害対応 / b1= 構築 L1(最小) / b2= 構築 L2(実務・要件書駆動)
POINTS = {
    "ts": {"root": 4, "backup": 2, "role": 3, "incon": 1, "rogue": 7, "ds": 6, "as": 4, "ping": 3, "long": 0, "errdis": 0, "steer": 6},
    "b1": {"root": 6, "backup": 3, "role": 3, "incon": 1, "rogue": 8, "ds": 2, "as": 6, "ping": 3, "long": 0, "errdis": 0, "steer": 0},
    "b2": {"root": 3, "backup": 2, "role": 3, "incon": 1, "rogue": 8, "ds": 5, "as": 3, "ping": 3, "long": 1, "errdis": 2, "steer": 6},
}


def grading(d, pid, level="ts"):
    P = POINTS[level]
    guards = level in ("ts", "b2")
    roles = expected_roles(d, steer=guards)
    rs = {"Root": "Root FWD", "Desg": "Desg FWD", "Altn": "Altn BLK"}
    allv = ",".join(str(v) for v in sorted(d["vlans"]))
    trunks = {s: sorted({ifn(i) for a, ia, b, ib in LINKS for w, i in ((a, ia), (b, ib)) if w == s}) for s in DS + AS}

    def common_audit(s):
        """設計書の「許可 VLAN は全 trunk 共通」「VLAN ごとのコスト変更はしない」"""
        out = [{"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? switchport trunk allowed vlan {allv}\r?\n"}
               for p in trunks[s]]
        out.append({"not_regex": r"(?m)^ spanning-tree (vlan \S+ )?cost "})
        return out
    checks = []
    for v in d["vlans"]:
        r = d["root"][v]
        checks.append({"name": f"VLAN{v}: root ブリッジが設計どおり {r}",
                       "node": r, "command": f"show spanning-tree vlan {v}",
                       "raw": [{"regex": "This bridge is the root"}], "points": P["root"]})
    for v in d["vlans"]:
        b = d["backup"][v]
        checks.append({"name": f"VLAN{v}: 予備 root({b})の bridge priority が {SECONDARY}",
                       "node": b, "command": f"show spanning-tree vlan {v}",
                       "raw": [{"regex": rf"Bridge ID\s+Priority\s+{SECONDARY + v}\b"}], "points": P["backup"]})
    for s in DS + AS:
        for v in d["vlans"]:
            raw = [{"regex": "Spanning tree enabled protocol rstp"}]
            for (sw, p), role in sorted(roles[v].items()):
                if sw == s:
                    raw.append({"regex": rf"(?m)^{p}\s+{rs[role]}\s"})
            raw.append({"not_regex": rf"(?m)^{SH}0/[0-3]\s.*(BKN|_Inc|Peer\(STP\))"})
            checks.append({"name": f"{s}: VLAN{v} の上り/下り/DS 間ポートの役割と状態が設計どおり(RSTP)",
                           "node": s, "command": f"show spanning-tree vlan {v}", "raw": raw, "points": P["role"]})
    for s in DS + AS:
        checks.append({"name": f"{s}: 不整合(inconsistent)状態のポートが無い",
                       "node": s, "command": "show spanning-tree inconsistentports",
                       "raw": [{"regex": r"in the system\s*:\s*0\b"}], "points": P["incon"]})
    ra, rp = d["rogue_as"], d["rogue_port"]
    checks.append({"name": f"{ra}: 持ち込み機器の {short(rp)} が BPDU ガードで遮断(err-disabled)されている",
                   "node": ra, "command": "show interfaces status err-disabled",
                   "raw": [{"regex": rf"(?m)^{short(rp)}\s.*err-disabled\s+bpduguard"}], "points": P["rogue"]})
    for s in DS:
        raw = []
        for p in DSLINK if guards else []:
            raw.append({"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? spanning-tree guard loop"})
        for p in (f"{PFX}0/2", f"{PFX}0/3") if guards else []:
            raw.append({"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? spanning-tree guard root"})
        raw.append({"not_regex": rf"interface {PFX}[0-2]/\d\r?\n(?: .*\r?\n)*? spanning-tree bpdufilter"})
        raw += common_audit(s)
        what = "保護方針(DS 間= loop guard / AS 向き= root guard / bpdufilter 無し)" if guards else "bpdufilter 無し"
        checks.append({"name": f"{s}: {what}・許可 VLAN・個別コスト無しが守られている",
                       "node": s, "command": AUDIT_CMD,
                       "raw": raw, "points": P["ds"]})
    for s in AS:
        raw = []
        for p in EDGE:
            raw.append({"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? spanning-tree portfast"})
            raw.append({"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? spanning-tree bpduguard enable"})
        raw.append({"not_regex": rf"interface {PFX}[0-2]/\d\r?\n(?: .*\r?\n)*? spanning-tree bpdufilter"})
        raw.append({"not_regex": r"(?m)^spanning-tree vlan \S+ priority"})
        raw += common_audit(s)
        checks.append({"name": f"{s}: エッジ({SH}1/0〜{SH}1/3)= portfast+BPDU ガード・bpdufilter 無し・priority 設定無し・許可 VLAN・コスト既定",
                       "node": s, "command": AUDIT_CMD,
                       "raw": raw, "points": P["as"]})
    for v in d["vlans"]:
        checks.append({"name": f"VLAN{v}: SW03 → SW04 の SVI 間疎通",
                       "node": "SW03", "command": f"ping {svi_ip(d, v, 'SW04')} repeat 5",
                       "raw": [{"regex": r"Success rate is (100|80) percent"}], "points": P["ping"]})
    if P["steer"]:
        nb = d["backup"][d["B"]]
        checks.append({"name": f"VLAN{d['B']}: DS 間はリンク2({SH}0/1)で転送(下流 {nb} の root port が {SH}0/1)",
                       "node": nb, "command": f"show spanning-tree vlan {d['B']}",
                       "raw": [{"regex": rf"(?m)^{SH}0/1\s+Root FWD\s"}, {"regex": rf"(?m)^{SH}0/0\s+Altn BLK\s"}],
                       "points": P["steer"]})
    if P["long"]:
        for s in DS + AS:
            checks.append({"name": f"{s}: パスコスト方式が long", "node": s,
                           "command": "show spanning-tree summary",
                           "raw": [{"regex": r"Configured Pathcost method used is long"}], "points": P["long"]})
    if P["errdis"]:
        checks.append({"name": f"{ra}: BPDU ガードによる err-disabled を自動復旧させていない", "node": ra,
                       "command": "show errdisable recovery",
                       "raw": [{"regex": r"(?m)^bpduguard\s+Disabled"}], "points": P["errdis"]})
    total = sum(c["points"] for c in checks)
    assert total == 100, total
    for c in checks:
        for r in c["raw"]:
            re.compile(list(r.values())[0])
    return {"problem": pid, "total_points": 100, "defaults": {"genie_os": "iosxe"}, "checks": checks}


# ---------------------------------------------------------------------------
# 問題文
# ---------------------------------------------------------------------------
SYMPTOM = {
    "root_hijack": "アクセス層の一部で、特定 VLAN の通信が分配層へ抜けなくなったとの申告がある。",
    "secondary_only": "新設 VLAN について、設計書と実際の root ブリッジが一致しないとの点検結果がある。",
    "pprio_downstream": "DS 間 2 本の使い分けが設計どおりになっていないとの点検結果がある(前任者は対処済みと報告)。",
    "guard_swap": "DS 間リンクで、一部 VLAN のポートが転送も待機もしていない状態との点検結果がある。",
    "bpduguard_uplink": "アクセススイッチの上りリンクの 1 本が、起動以来一度も使われていない。",
    "rogue_leak": "持ち込みスイッチの接続を検知したが、接続ポートが遮断されていない。",
    "mode_mismatch": "障害時の切替に数十秒かかる区間がある。",
    "cost_skew": "特定 VLAN の通信が、アクセス層から見て遠回りの経路を通っている。",
    "loopguard_trip": "DS 間リンクで、一部 VLAN のポートが転送も待機もしていない状態との点検結果がある。",
    "allowed_skew": "特定 VLAN の通信が、アクセス層から見て遠回りの経路を通っている。",
}


def task_md(d, pid, faults):
    A, B, C = d["A"], d["B"], d["C"]
    L = [f"# 障害対応 {pid} : キャンパス L2 のスパニングツリーが設計書と一致しない", "",
         "## 状況",
         "分配層 2 台(SW01・SW02)とアクセス層 2 台(SW03・SW04)で構成されたキャンパス L2 です。",
         "定期点検の結果、スパニングツリーの状態が設計書と一致しないことが判明しました。",
         "運用から次の申告も上がっています。", ""]
    seen = []
    for f in faults:
        if SYMPTOM[f] not in seen:
            seen.append(SYMPTOM[f])
    for s in seen:
        L.append(f"> - {s}")
    L += ["", "設計書どおりの状態に復旧してください。**原因は 1 か所とは限りません。**", "",
          "## 設計書(抜粋)", "",
          "| 項目 | 設計 |", "|---|---|",
          "| STP モード | 全スイッチ Rapid PVST+ |",
          f"| VLAN{A}・VLAN{C} | root= {d['root'][A]}(priority {PRIMARY})・予備 root= {d['backup'][A]}(priority {SECONDARY}) |",
          f"| VLAN{B} | root= {d['root'][B]}(priority {PRIMARY})・予備 root= {d['backup'][B]}(priority {SECONDARY}) |",
          "| アクセス層 | root にも予備 root にもならない(bridge priority は既定のまま) |",
          f"| DS 間 2 本の使い分け | VLAN{A}・VLAN{C} はリンク1({SH}0/0 同士)、VLAN{B} はリンク2({SH}0/1 同士)で転送する |",
          "| DS 間ポート | 両端で loop guard |",
          f"| DS のアクセス向きポート({SH}0/2・{SH}0/3) | root guard |",
          f"| アクセスのエッジ({SH}1/0〜{SH}1/3) | PortFast+BPDU ガード。BPDU を受けたポートは err-disabled のまま保持する(復旧は申請後) |",
          f"| trunk | 802.1Q・許可 VLAN は {','.join(str(v) for v in sorted(d['vlans']))} のみ(全 trunk 共通) |",
          "| パスコスト | 既定(short)・VLAN ごとのコスト変更はしない |", "",
          "## 構成台帳", "",
          "| 機器 | 役割 | 配線 |", "|---|---|---|",
          f"| SW01 | 分配 DS1 | {SH}0/0・{SH}0/1→SW02 / {SH}0/2→SW03 / {SH}0/3→SW04 |",
          f"| SW02 | 分配 DS2 | {SH}0/0・{SH}0/1→SW01 / {SH}0/2→SW03 / {SH}0/3→SW04 |",
          f"| SW03 | アクセス AS1 | {SH}0/0→SW01 / {SH}0/1→SW02 |",
          f"| SW04 | アクセス AS2 | {SH}0/0→SW01 / {SH}0/1→SW02 |",
          f"| SW05 | 持ち込み機器(管理外・ログイン禁止) | {d['rogue_as']} {short(d['rogue_port'])}(未使用ポート・駐車 VLAN {PARK})に接続 |", "",
          "SVI(疎通確認用): " + " / ".join(
              f"VLAN{v}= 10.{d['oct2']}.{v}.<SW 番号>/24" for v in sorted(d["vlans"])), "",
          "## 注意",
          f"- 管理 VLAN(999)・各機の {MGMT_IF} には触れないこと。SW05 にはログインしないこと。",
          "- 設計書にない設定で辻褄を合わせないこと(採点は設計書との一致も見る)。", "",
          "## ログイン / 採点",
          "CML コンソール、または管理 IP へ telnet(user SUZUKI / pass CCNP。管理 IP は出題時の割当表を参照)。", "```",
          f"scripts/lab.sh grade {pid}", "```", ""]
    return "\n".join(L)


def task_md_build(d, pid, level, old):
    A, B, C = d["A"], d["B"], d["C"]
    vls = ",".join(str(v) for v in sorted(d["vlans"]))
    rog = f"{d['rogue_as']} {short(d['rogue_port'])}"
    root_rows = [
        f"| VLAN{A}・VLAN{C} | root= {d['root'][A]}(bridge priority {PRIMARY})・予備 root= {d['backup'][A]}(bridge priority {SECONDARY}) |",
        f"| VLAN{B} | root= {d['root'][B]}(bridge priority {PRIMARY})・予備 root= {d['backup'][B]}(bridge priority {SECONDARY}) |",
        "| アクセス層(SW03・SW04) | bridge priority は既定のまま |"]
    if level == "b1":
        L = [f"# 構築 {pid} : キャンパス L2 のスパニングツリー初期設定", "",
             "## 状況",
             "分配層 2 台(SW01・SW02)とアクセス層 2 台(SW03・SW04)のキャンパス L2 を新設中です。",
             f"VLAN({vls})・trunk・SVI・エッジポートの所属 VLAN は構築済みですが、スパニングツリーは全台とも既定値(Rapid PVST+)のままです。",
             f"また、{rog} には利用者が持ち込んだスイッチ(SW05)が接続されたままになっています。", "",
             "次の要件どおりにスパニングツリーを設定してください。", "",
             "## 要件", "",
             "| 項目 | 要件 |", "|---|---|",
             "| STP モード | 全スイッチ Rapid PVST+(変更しない) |"] + root_rows + [
             f"| アクセスのエッジ({SH}1/0〜{SH}1/3) | PortFast と BPDU ガードを有効にする。BPDU を受けたポートは err-disabled のまま保持する(自動復旧させない) |",
             "| 変更範囲 | スパニングツリーの設定のみ。VLAN・trunk・SVI・パスコストは変更しない |", "",
             "## 完了条件",
             "- 各 VLAN の root・予備 root が要件どおりで、スイッチ間のポートの役割が設計どおりであること。",
             f"- {rog} が BPDU ガードで遮断されていること。",
             "- SW03 と SW04 の SVI 間で各 VLAN の疎通があること。"]
    else:
        L = [f"# 構築 {pid} : キャンパス L2 のスパニングツリー設計適用", "",
             "## 状況",
             "分配層 2 台(SW01・SW02)とアクセス層 2 台(SW03・SW04)のキャンパス L2 に、スパニングツリーの設計を適用します。",
             f"VLAN({vls})・trunk・SVI・エッジポートの所属 VLAN は構築済みです。スパニングツリーは各機とも既定値(Rapid PVST+)のままです。",
             f"また、{rog} には利用者が持ち込んだスイッチ(SW05)が接続されたままになっています。", "",
             "次の要件書に従って設定してください。実現手段は問いませんが、要件書に反する設定は減点します。", "",
             "## 要件書", "",
             "| 項目 | 要件 |", "|---|---|",
             "| STP モード | 全スイッチ Rapid PVST+(変更しない) |",
             "| パスコスト | 32 ビット値の方式(long)に全スイッチで統一する。ポート単位・VLAN 単位のパスコスト変更は使用しない |"] + root_rows + [
             f"| DS 間 2 本の使い分け | 正常時、VLAN{A}・VLAN{C} はリンク1({SH}0/0 同士)、VLAN{B} はリンク2({SH}0/1 同士)で転送する |",
             f"| DS のアクセス向きポート({SH}0/2・{SH}0/3) | アクセス側から優位な BPDU を受けても、root の座を明け渡さない |",
             "| DS 間ポート | BPDU が途絶えても(片方向障害など)転送状態へ移行させない |",
             f"| アクセスのエッジ({SH}1/0〜{SH}1/3) | 端末の接続時は待たずに転送を始める。BPDU を受けたら直ちに遮断し、自動復旧はさせない |",
             "| 変更範囲 | スパニングツリーの設定のみ。VLAN・trunk・SVI は変更しない |", "",
             "## 完了条件",
             "- 各 VLAN の root・予備 root・DS 間 2 本の使い分けが要件どおりで、スイッチ間の全ポートが RSTP で動作していること。",
             f"- {rog} が遮断されていること。SW03 と SW04 の SVI 間で各 VLAN の疎通があること。"]
    L += ["", "## 構成台帳", "",
          "| 機器 | 役割 | 配線 |", "|---|---|---|",
          f"| SW01 | 分配 DS1 | {SH}0/0・{SH}0/1→SW02 / {SH}0/2→SW03 / {SH}0/3→SW04 |",
          f"| SW02 | 分配 DS2 | {SH}0/0・{SH}0/1→SW01 / {SH}0/2→SW03 / {SH}0/3→SW04 |",
          f"| SW03 | アクセス AS1 | {SH}0/0→SW01 / {SH}0/1→SW02 / {SH}1/0〜{SH}1/3= エッジ |",
          f"| SW04 | アクセス AS2 | {SH}0/0→SW01 / {SH}0/1→SW02 / {SH}1/0〜{SH}1/3= エッジ |",
          f"| SW05 | 持ち込み機器(管理外・ログイン禁止) | {rog}(未使用ポート・駐車 VLAN {PARK})に接続 |", "",
          "SVI(疎通確認用): " + " / ".join(
              f"VLAN{v}= 10.{d['oct2']}.{v}.<SW 番号>/24" for v in sorted(d["vlans"])), "",
          "## 注意",
          f"- 管理 VLAN(999)・各機の {MGMT_IF} には触れないこと。SW05 にはログインしないこと。", "",
          "## ログイン / 採点",
          "CML コンソール、または管理 IP へ telnet(user SUZUKI / pass CCNP。管理 IP は出題時の割当表を参照)。", "```",
          f"scripts/lab.sh grade {pid}", "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------
def build_mst(repo, seed, mode, nfaults, forced):
    """L4 = MST 世界(gen_stp_mst.py)。ID は同じ GEN-STP-<seed>。"""
    import gen_stp_mst as M
    g = M.generate(seed, mode, nfaults, forced)
    pid = g["pid"]
    pdir = os.path.join(repo, "problems", pid)
    os.makedirs(os.path.join(pdir, "initial"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "solution"), exist_ok=True)
    problem = {"id": pid, "title": g["title"], "exam": "ENCOR",
               "topics": ["stp", "rstp", "l2"] + g["topics"] + ["generated"],
               "difficulty": g["diff"], "topology": "generated", "target_nodes": g["nodes"], "points": 100,
               "access": "telnet", "image_family": "iol",
               "lab": {"positions": g.get("positions", {}), "links": g["links"]}}
    with open(os.path.join(pdir, "problem.yml"), "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_stp.py) seed={seed} mode={mode} world=mst\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for s, txt in g["initial"].items():
        with open(os.path.join(pdir, "initial", f"{s}.cfg.j2"), "w", encoding="utf-8") as f:
            f.write(txt)
    with open(os.path.join(pdir, "grading.yml"), "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_stp.py --world mst) seed={seed}\n")
        yaml.safe_dump(g["grading"], f, sort_keys=False, allow_unicode=True)
    with open(os.path.join(pdir, "task.md"), "w", encoding="utf-8") as f:
        f.write(g["task"])
    json.dump({"world": "mst", "faults": g["note"], "fix": g["fix"],
               "design": {k: v for k, v in g["d"].items() if k != "edge_vlan"}},
              open(os.path.join(pdir, "solution", "fix.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)
    return pid, g["faults"], g["note"]


def build(repo, seed, mode, nfaults, forced, level=2):
    rnd = random.Random(seed)
    d = design(rnd)
    if mode == "ts":
        st = base_state(d)
        want = nfaults or rnd.choice([2, 3])
        faults = pick_faults(rnd, want, forced)
        note, fix = inject(rnd, d, st, faults)
        glevel, diff = "ts", (4 if len(faults) <= 2 else 5)
        title, topics = f"キャンパス L2 STP 障害対応 (seed={seed})", ["troubleshooting"]
    else:
        glevel = f"b{level}"
        st, old = build_state(rnd, d, glevel)
        faults, note, fix = [], {"level": level, "pvst_at_start": old}, build_fix(d, glevel)
        diff = 3 if level == 1 else 4
        title, topics = f"キャンパス L2 STP 構築 (seed={seed})", ["build"]
    pid = f"GEN-STP-{seed}"
    pdir = os.path.join(repo, "problems", pid)
    os.makedirs(os.path.join(pdir, "initial"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "solution"), exist_ok=True)
    ri = EDGE.index(d["rogue_port"]) + 4
    links = [{"a": a, "a_if": ia, "b": b, "b_if": ib} for a, ia, b, ib in LINKS]
    links.append({"a": d["rogue_as"], "a_if": ri, "b": ROGUE, "b_if": 0})
    problem = {"id": pid, "title": title, "exam": "ENCOR",
               "topics": ["stp", "rstp", "l2"] + topics + ["generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": DS + AS + [ROGUE], "points": 100, "access": "telnet",
               "image_family": IMAGE_FAMILY[PFX],
               "lab": {"positions": dict(POS, **{ROGUE: ROGUE_POS[d["rogue_as"]]}), "links": links}}
    with open(os.path.join(pdir, "problem.yml"), "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_stp.py) seed={seed} mode={mode} level={glevel}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for s in DS + AS:
        with open(os.path.join(pdir, "initial", f"{s}.cfg.j2"), "w", encoding="utf-8") as f:
            f.write(render(d, st, s, seed))
    with open(os.path.join(pdir, "initial", f"{ROGUE}.cfg.j2"), "w", encoding="utf-8") as f:
        f.write(render_rogue(seed))
    g = grading(d, pid, glevel)
    with open(os.path.join(pdir, "grading.yml"), "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_stp.py) seed={seed}\n")
        yaml.safe_dump(g, f, sort_keys=False, allow_unicode=True)
    with open(os.path.join(pdir, "task.md"), "w", encoding="utf-8") as f:
        f.write(task_md(d, pid, faults) if mode == "ts" else task_md_build(d, pid, level, note["pvst_at_start"]))
    json.dump({"faults": note, "fix": fix, "design": {k: v for k, v in d.items() if k != "edge_vlan"}},
              open(os.path.join(pdir, "solution", "fix.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)
    return pid, faults, note


def selftest():
    ng = 0
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "problems"))
        for seed in range(1, 201):
            for forced in [None] + [[f] for f in FAULTS]:
                try:
                    rnd = random.Random(seed)
                    d = design(rnd)
                    st0 = base_state(d)
                    base = {s: render(d, st0, s, seed) for s in DS + AS}
                    st = base_state(d)
                    faults = pick_faults(rnd, rnd.choice([2, 3]), forced)
                    for g in EXCLUSIVE:
                        assert len(g & set(faults)) <= 1, faults
                    inject(rnd, d, st, faults)
                    after = {s: render(d, st, s, seed) for s in DS + AS}
                    assert base != after, f"故障が構成に現れない {faults}"
                    roles = expected_roles(d)
                    for v, rl in roles.items():
                        for s in DS + AS:
                            if s != d["root"][v]:
                                assert sum(1 for (w, _), r in rl.items() if w == s and r == "Root") == 1
                    # リンク2 の使い分け(VLAN B は Et0/1、A/C は Et0/0)
                    nb = d["backup"][d["B"]]
                    assert roles[d["B"]][(nb, f"{SH}0/1")] == "Root"
                    assert roles[d["A"]][(d["backup"][d["A"]], f"{SH}0/0")] == "Root"
                    grading(d, "X")
                except AssertionError as e:
                    ng += 1
                    print(f"NG seed={seed} forced={forced}: {e}")
        for seed in range(1, 201):
            for lv in ("b1", "b2"):
                try:
                    rnd = random.Random(seed)
                    d = design(rnd)
                    st, old = build_state(rnd, d, lv)
                    assert PVST_START or not old
                    txt = "".join(render(d, st, sw, seed) for sw in DS + AS)
                    assert "guard" not in txt and "priority" not in txt and "portfast" not in txt
                    fx = build_fix(d, lv)
                    allc = "\n".join(x for f in fx.values() for x in f["conf"])
                    assert ("guard loop" in allc) == (lv == "b2") and ("port-priority" in allc) == (lv == "b2")
                    assert ("pathcost method long" in allc) == (lv == "b2")
                    assert allc.count("bpduguard enable") == 8
                    r1 = expected_roles(d, steer=(lv == "b2"))
                    nb = d["backup"][d["B"]]
                    assert r1[d["B"]][(nb, f"{SH}0/1" if lv == "b2" else f"{SH}0/0")] == "Root"
                    grading(d, "X", lv)
                    task_md_build(d, "X", int(lv[1]), old)
                except AssertionError as e:
                    ng += 1
                    print(f"NG build seed={seed} {lv}: {e}")
    print(f"selftest: {200 * (len(FAULTS) + 1) + 400} cases NG={ng}")
    return ng


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--mode", default="ts", choices=["ts", "build"])
    ap.add_argument("--image", default="iol", choices=["iol", "iosv"],
                    help="iol= ioll2(Ethernet・既定) / iosv= IOSvL2(GigabitEthernet)")
    ap.add_argument("--world", default="pvst", choices=["pvst", "mst"],
                    help="mst= L4(MST リージョン+旧機 Rapid PVST+ の境界・gen_stp_mst.py)")
    ap.add_argument("--level", type=int, default=2, choices=[1, 2], help="build の段階(1=最小構築 / 2=実務構築)")
    ap.add_argument("--faults", type=int, default=0, help="0=ランダム(2〜3)")
    ap.add_argument("--fault", default="", help="故障を指定(カンマ区切り・検証用)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        import gen_stp_mst
        ng = 0
        for img in ("iol", "iosv"):
            set_image(img)
            print(f"-- image={img}")
            ng += selftest()
        set_image("iol")
        sys.exit(1 if (ng + gen_stp_mst.selftest()) else 0)
    if a.seed is None:
        a.seed = random.SystemRandom().randint(1000, 99999)
    forced = [x for x in a.fault.split(",") if x]
    set_image(a.image)
    if a.world == "mst":
        if a.image != "iol":
            raise SystemExit("--world mst は今のところ iol のみ(IOSvL2 版は未検証)")
        pid, faults, note = build_mst(a.repo, a.seed, a.mode, a.faults, forced)
        print(f"wrote problems/{pid}: world=mst mode={a.mode}" + (f" faults={faults}" if a.mode == "ts" else ""))
        return
    pid, faults, note = build(a.repo, a.seed, a.mode, a.faults, forced, a.level)
    print(f"wrote problems/{pid}: mode={a.mode}" + (f" faults={faults}" if a.mode == "ts" else f" level={a.level} pvst={note['pvst_at_start']}"))


if __name__ == "__main__":
    main()
