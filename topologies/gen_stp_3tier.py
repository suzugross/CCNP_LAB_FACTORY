#!/usr/bin/env python3
"""STP ラボ 3 層キャンパス世界(BL-221 の T4)。gen_stp.py `--world 3tier` から呼ぶ(ID は GEN-STP-<seed> のまま)。

盤面(L2 スイッチ×6 + 持ち込み機器×1):
    SW01/SW02= コア(CR1/CR2)・SW03/SW04= 分配(DS1/DS2)・SW05/SW06= アクセス(AS1/AS2)・SW07= 持ち込み機器(管理外)。
    リンク 10 本= コア間 1・コア↔分配 4(フルメッシュ)・分配間 1・分配↔アクセス 4。
    2 層盤面(gen_stp.py)との違い= 層が 3 つ・ポートの「向き」が 3 種(上り/同層/下り)・root がアクセスから 2 ホップ。
モード:
    build: STP だけ白紙(全台 Rapid PVST+ 既定)→ 要件書どおりに組ませる(2026-09-26)。
    ts   : 設計どおりの状態に故障を 2〜3 個注入(下の FAULTS・2026-09-27)。

要件書(seed で振るのは値と「保護機構の記述方式」・構成は固定):
    ・root= コア。VLAN A・C は x、VLAN B は y(24576)。予備 root= 反対のコア(28672)。
    ・分配は VLAN ごとに**片方だけ 36864**。これが ①分配間リンクでブロックする側 ②アクセスの上りが通る側 を
      決める(= 2 段の負荷分散)。既定のままにすると両者が MAC 依存になり決定性が崩れる(§2)。
    ・アクセスの priority は既定のまま(root guard で守る)。
    ・保護は**方針**で与える= 上位層へ向くポートと同一層のスイッチ間リンク= loop guard / 下位層へ向くポート= root guard /
      エッジ= portfast + BPDU ガード(自動復旧なし)。要件書にポート名は列挙しない(20 ポートを自分で分類させる)。
    ・パスコスト方式は long で全台統一。ポート単位・VLAN 単位の cost / port-priority は使わない(監査で降格)。
    ・**記述方式(style・BL-222)**= port(ポートごと・既定値は使わない)/ global(スイッチ全体の既定値で与え、
      例外だけポートごと)/ any(手段は問わない)。global は IOSvL2 のみ(ioll2 は `portfast edge` 構文が無い)。

採点(BL-222 で「実効状態」へ移行): 保護機構は `show spanning-tree vlan <A> detail` の各ポート ブロック内の
    `Loop guard is enabled( by default)? on the port` / `Root guard is enabled on the port` で見る(記述方式に依存しない)。
    エッジの portfast/BPDU ガードは running-config で「IF の行 か グローバル既定」のどちらかを受ける。
    記述方式の指定(port/global)は running-config のグローバル行の有無で見る。
決定性(STP-SERIES.design.md §2)= どのセグメントも root path cost か BID の**設定値の差**で決まり、MAC 比較に落ちない。
    selftest が MAC の並びを逆にした計算と突き合わせて全 seed で検査する。
裏どり(実機 PoC 第6回・poc/stp/README.md): detail の guard 行の書式・loopguard default と IF の root guard の優先関係
    (root guard の行だけになる)・bpduguard default の効き・TS 故障 3 種(コア間 loopguard_trip / pathcost 混在 /
    アクセスの priority)の実挙動。
"""
import os
import random
import re

from stp_model import Topo

CORE = ["SW01", "SW02"]
DIST = ["SW03", "SW04"]
ACC = ["SW05", "SW06"]
SWS = CORE + DIST + ACC
ROGUE = "SW07"
LAYER = {s: (0 if s in CORE else 1 if s in DIST else 2) for s in SWS}
LABEL = {"SW01": "コア CR1", "SW02": "コア CR2", "SW03": "分配 DS1", "SW04": "分配 DS2",
         "SW05": "アクセス AS1", "SW06": "アクセス AS2"}
PRIMARY, SECONDARY, WEAK, DEFAULT = 24576, 28672, 36864, 32768
PARK = 99          # 未使用ポートの駐車 VLAN(アクセスにだけ作る・trunk には載せない)
STYLES = ["port", "global", "any"]
GLOBAL_LINES = {"loopguard": "spanning-tree loopguard default",
                "pf": "spanning-tree portfast edge default",
                "bg": "spanning-tree portfast edge bpduguard default"}
LONG_BASE = {"Ethernet": 2000000, "GigabitEthernet": 20000}   # long 方式の 1 リンクのコスト(ioll2= 10M 扱い)

# 物理配線(添字 = スロット順。0/0=0 … 1/0=4。mgmt は 3/3=slot15 固定で触らない)
LINKS = [("SW01", 0, "SW02", 0),                                  # コア間
         ("SW01", 1, "SW03", 0), ("SW01", 2, "SW04", 0),          # CR1 → 分配
         ("SW02", 1, "SW03", 1), ("SW02", 2, "SW04", 1),          # CR2 → 分配
         ("SW03", 2, "SW04", 2),                                  # 分配間
         ("SW03", 3, "SW05", 0), ("SW03", 4, "SW06", 0),          # DS1 → アクセス
         ("SW04", 3, "SW05", 1), ("SW04", 4, "SW06", 1)]          # DS2 → アクセス
POS = {"SW01": [-380, -320], "SW02": [-20, -320],
       "SW03": [-380, -100], "SW04": [-20, -100],
       "SW05": [-420, 120], "SW06": [20, 120]}
ROGUE_POS = {"SW05": [-460, 300], "SW06": [60, 300]}

FAULTS = ["t_core_prio_swap", "t_dist_weak_missing", "t_dist_weak_wrong_vlan", "t_rootguard_up",
          "t_loopguard_down", "t_acc_priority", "t_cost_bump_dist", "t_allowed_hole", "t_mode_pvst",
          "t_bpduguard_uplink", "t_loopguard_trip", "t_pathcost_short"]
# 同じポート/同じ論点を奪い合う組(同時に選ばない)
EXCLUSIVE = [{"t_rootguard_up", "t_loopguard_down", "t_loopguard_trip"},
             {"t_dist_weak_missing", "t_dist_weak_wrong_vlan"},
             {"t_core_prio_swap", "t_acc_priority"},
             {"t_cost_bump_dist", "t_pathcost_short"}]
DAY0_ONLY = {"t_mode_pvst"}        # 実行中の rapid→pvst 移行は IOL で不安定(§6.9)。検証は day0 から
SYMPTOM = {
    "t_core_prio_swap": "特定 VLAN の root ブリッジが設計書と一致しないとの点検結果がある。",
    "t_dist_weak_missing": "分配間リンクでブロックしている側と、アクセス層の上りの使い分けが、VLAN によって設計書と違う。",
    "t_dist_weak_wrong_vlan": "分配間リンクでブロックしている側と、アクセス層の上りの使い分けが、VLAN によって設計書と違う。",
    "t_rootguard_up": "点検で、不整合(inconsistent)状態のポートが報告された。",
    "t_loopguard_down": "スパニングツリーの状態に異常は無いが、保護機構の点検で設計書との食い違いが指摘された。",
    "t_cost_bump_dist": "特定 VLAN の通信が、分配層からコア間リンクを経由する遠回りの経路を通っている。",
    "t_allowed_hole": "特定 VLAN だけ、アクセス層の上りの使い分けが設計書と違う(スパニングツリーの設定は設計どおりに見える)。",
    "t_mode_pvst": "スイッチ 1 台の周辺で、リンク障害時の切り替わりが他より遅いとの申告がある。",
    "t_bpduguard_uplink": "アクセススイッチの上りリンクの 1 本が、起動以来一度も使われていない。",
    "t_loopguard_trip": "点検で、不整合(inconsistent)状態のポートが報告された。",
    "t_pathcost_short": "特定 VLAN で、アクセス層の上りと分配間リンクの使い分けが設計書と違う。",
}
# t_acc_priority は値で症状が変わる(PoC T3: root より優位なら孤立・28672 なら状態に出ない)
SYMPTOM_ACC = {True: "特定 VLAN で、アクセススイッチ 1 台が他のアクセスへ疎通しない。",
               False: "スパニングツリーの状態に異常は無いが、アクセス層に設計書に無い設定があると点検で指摘された。"}

PFX, SH, EDGE, MGMT_IF, AUDIT_CMD = "Ethernet", "Et", [], "", ""
IMAGE_FAMILY = {"Ethernet": "iol", "GigabitEthernet": "iosv"}


def set_image(image):
    """image= iol(ioll2・Et) / iosv(IOSvL2・Gi)。IF 名だけが変わる(スロット割当は共通)。"""
    global PFX, SH, EDGE, MGMT_IF, AUDIT_CMD
    PFX, SH = ("Ethernet", "Et") if image == "iol" else ("GigabitEthernet", "Gi")
    EDGE = [f"{PFX}1/{i}" for i in range(4)]
    MGMT_IF = f"{PFX}3/3"
    AUDIT_CMD = f"show running-config | include ^interface {PFX}|spanning-tree|allowed vlan"


def ifn(i):
    return f"{PFX}{i // 4}/{i % 4}"


def sh(name):
    return name.replace(PFX, SH)


def slot_port(name):
    m = re.search(r"(\d+)/(\d+)$", name)
    return int(m.group(1)), int(m.group(2))


def port_dir():
    """{(sw, IF 名): 'up'(上位層へ) | 'peer'(同一層) | 'down'(下位層へ)}。保護方針の適用先を機械的に決める。"""
    out = {}
    for a, ia, b, ib in LINKS:
        for s, i, o in ((a, ia, b), (b, ib, a)):
            out[(s, ifn(i))] = ("down" if LAYER[o] > LAYER[s] else
                               "up" if LAYER[o] < LAYER[s] else "peer")
    return out


def guard_of(direction):
    return "spanning-tree guard root" if direction == "down" else "spanning-tree guard loop"


def trunks_of(s):
    return sorted({ifn(i) for a, ia, b, ib in LINKS for w, i in ((a, ia), (b, ib)) if w == s},
                  key=slot_port)


def ports_dir(s, want):
    pd = port_dir()
    return [p for p in trunks_of(s) if pd[(s, p)] == want]


def toward(s, peer):
    """s の IF のうち peer へ向くもの。"""
    for a, ia, b, ib in LINKS:
        if a == s and b == peer:
            return ifn(ia)
        if b == s and a == peer:
            return ifn(ib)
    raise KeyError((s, peer))


def other(pair, x):
    return pair[1] if x == pair[0] else pair[0]


set_image("iol")


# ---------------------------------------------------------------------------
# 設計(seed で決まる値)
# ---------------------------------------------------------------------------
def design(rnd, style=None):
    A, B, C = rnd.sample([v for v in range(11, 255) if v != PARK], 3)
    x = rnd.choice(CORE)                       # VLAN A・C の root
    y = other(CORE, x)                         # VLAN B の root
    wac = rnd.choice(DIST)                     # VLAN A・C で 36864 に落とす分配
    wb = other(DIST, wac)
    rogue_acc = rnd.choice(ACC)
    rogue_port = rnd.choice(EDGE)
    edge_vlan = {s: {p: rnd.choice([A, B, C]) for p in EDGE} for s in ACC}
    edge_vlan[rogue_acc][rogue_port] = PARK
    oct2 = rnd.randint(20, 250)
    # ★記述方式は最後に引く(2026-09-27 追加。これより前の値は追加前と同じ seed で同じになる)。
    #   指定があっても 1 回引いて捨てる= 故障の抽選列が指定の有無で変わらない。
    drawn = rnd.choice(STYLES)
    st = style or drawn
    if PFX == "Ethernet" and st == "global":
        if style:
            raise SystemExit("--guard-style global は IOSvL2(--image iosv)のみ(ioll2 は portfast edge 構文が無い)")
        st = "any"
    return {"A": A, "B": B, "C": C, "vlans": [A, B, C],
            "root": {A: x, C: x, B: y}, "backup": {A: y, C: y, B: x},
            "weak": {A: wac, C: wac, B: wb},          # 36864 を振る分配(= 分配間でブロックする側)
            "prefer": {A: wb, C: wb, B: wac},         # アクセスの上りが通る分配
            "rogue_acc": rogue_acc, "rogue_port": rogue_port,
            "edge_vlan": edge_vlan, "oct2": oct2, "style": st}


def svi_ip(d, v, s):
    return f"10.{d['oct2']}.{v}.{int(s[-1])}"


def prio_of(d, s, v):
    """設計どおりの bridge priority(既定のままなら 32768)。"""
    if d["root"][v] == s:
        return PRIMARY
    if d["backup"][v] == s:
        return SECONDARY
    if d["weak"][v] == s:
        return WEAK
    return DEFAULT


def _topo_links():
    E = lambda i: {"name": sh(ifn(i)), "num": i + 1}
    return [(a, E(ia), b, E(ib), "10M") for a, ia, b, ib in LINKS]


def expected_roles(d, rev_mac=False):
    """{vlan: {(sw, 'Et0/0'): 'Root'|'Desg'|'Altn'}}。rev_mac= MAC の並びを逆にする(決定性の検査用)。"""
    out = {}
    for v in d["vlans"]:
        sws = {}
        for i, s in enumerate(reversed(SWS) if rev_mac else SWS, 1):
            sws[s] = {"prio": prio_of(d, s, v), "mac": f"aabb.cc00.{i:02d}00"}
        t = Topo(sws, _topo_links(), method="long", vlan=v).solve()
        assert t.root == d["root"][v], (v, t.root)
        out[v] = t.role
    return out


def roles_of_state(d, st):
    """状態(故障注入後を含む)から役割を計算する。priority・VLAN 単位 cost だけを反映(selftest 用)。"""
    out = {}
    for v in d["vlans"]:
        sws = {s: {"prio": st[s]["prio"].get(v, DEFAULT), "mac": f"aabb.cc00.{i:02d}00"}
               for i, s in enumerate(SWS, 1)}
        ovr = {}
        for s in SWS:
            for name, c in st[s]["ifs"].items():
                for x in c["lines"]:
                    m = re.fullmatch(rf"spanning-tree vlan {v} cost (\d+)", x)
                    if m:     # 実機の値 → 計算器の単位(long・10M= 2000000/リンク)へ換算
                        ovr[(s, sh(name))] = int(m.group(1)) * 2000000 // LONG_BASE[PFX]
        out[v] = Topo(sws, _topo_links(), method="long", cost_ovr=ovr, vlan=v).solve().role
    return out


# ---------------------------------------------------------------------------
# 構成(設計どおりの状態 → 白紙化/故障注入 → 描画)
# ---------------------------------------------------------------------------
def base_state(d):
    glob = d["style"] == "global"
    st = {s: {"mode": "rapid-pvst", "long": True, "prio": {}, "ifs": {}, "glob": set()} for s in SWS}
    for v in d["vlans"]:
        for s in SWS:
            p = prio_of(d, s, v)
            if p != DEFAULT:
                st[s]["prio"][v] = p
    allv = ",".join(str(v) for v in sorted(d["vlans"]))
    pd = port_dir()
    for a, ia, b, ib in LINKS:
        for s, i in ((a, ia), (b, ib)):
            name = ifn(i)
            dirn = pd[(s, name)]
            # global= 上り/同層は loopguard default に任せ、下り(root guard)だけ明示する(PoC G3)
            lines = [guard_of(dirn)] if (not glob or dirn == "down") else []
            st[s]["ifs"][name] = {"trunk": True, "allowed": allv, "lines": lines}
    for s in ACC:
        for p in EDGE:
            st[s]["ifs"][p] = {"trunk": False, "vlan": d["edge_vlan"][s][p],
                               "lines": [] if glob else ["spanning-tree portfast", "spanning-tree bpduguard enable"]}
    if glob:
        for s in SWS:
            st[s]["glob"].add("loopguard")
        for s in ACC:
            st[s]["glob"] |= {"pf", "bg"}
    return st


def build_state(d):
    """VLAN・trunk(許可 VLAN 絞り= mgmt 隔離)・エッジの所属 VLAN・SVI は構築済み。STP だけ白紙。"""
    st = base_state(d)
    for s in SWS:
        st[s].update({"prio": {}, "long": False, "glob": set()})
        for c in st[s]["ifs"].values():
            c["lines"] = []
    return st


def prio_lines(st, s):
    return [f"spanning-tree vlan {v} priority {p}" for v, p in sorted(st[s]["prio"].items())]


def glob_lines(st, s):
    return [GLOBAL_LINES[k] for k in ("loopguard", "pf", "bg") if k in st[s]["glob"]]


def build_fix(d):
    """模範解答(設計書どおり)。solution/fix.json の fix と同じ形。any は port と同じ書き方。"""
    ok = base_state(d)
    fix = {}
    for s in SWS:
        conf = ["spanning-tree mode rapid-pvst", "spanning-tree pathcost method long"]
        conf += glob_lines(ok, s) + prio_lines(ok, s)
        for name in sorted(ok[s]["ifs"], key=slot_port):
            lines = ok[s]["ifs"][name]["lines"]
            if lines:
                conf += [f"interface {name}"] + lines
        if d["style"] == "global" and s == d["rogue_acc"]:
            # 既定の BPDU ガードは edge として動作中のポートにだけ効く。持ち込み機器のポートは既に BPDU を受けて
            # edge を外れているので、上げ直して edge から始めさせる(PoC G4 は bounce で発動を確認)。
            conf += [f"interface {d['rogue_port']}", "shutdown", "no shutdown"]
        fix[s] = {"conf": conf, "exec": ["clear spanning-tree detected-protocols"]}
    return fix


def pick_faults(rnd, want, forced):
    if forced:
        return list(forced)
    pool = FAULTS[:]
    rnd.shuffle(pool)
    out = []
    for f in pool:
        if any(f in g and any(o in g for o in out) for g in EXCLUSIVE):
            continue
        out.append(f)
        if len(out) == want:
            break
    return out


def set_guard(st, s, p, line):
    """ポート p の guard 行を line に置き換える(None= guard 行を消す)。他の行(cost など)は残す。"""
    L = [x for x in st[s]["ifs"][p]["lines"] if not x.startswith("spanning-tree guard")]
    if line:
        L.append(line)
    st[s]["ifs"][p]["lines"] = L


def inject(rnd, d, st, faults):
    """故障を入れ、(症状メモ, 解答 fix, 故障を実機へ入れる break) を返す。
    fix= switch → {"conf": [...], "exec": [...]} / break= switch → [conf 行](検証で稼働中の盤面へ注入する用)。"""
    fix, brk, note = {}, {}, []
    glob = d["style"] == "global"

    def add(s, conf=(), exe=(), b=()):
        f = fix.setdefault(s, {"conf": [], "exec": []})
        f["conf"] += list(conf)
        f["exec"] += list(exe)
        brk.setdefault(s, []).extend(b)

    A, B, C = d["A"], d["B"], d["C"]
    for f in faults:
        if f == "t_core_prio_swap":
            v = rnd.choice(d["vlans"])
            r, b = d["root"][v], d["backup"][v]
            st[r]["prio"][v], st[b]["prio"][v] = SECONDARY, PRIMARY
            add(r, [f"spanning-tree vlan {v} priority {PRIMARY}"], b=[f"spanning-tree vlan {v} priority {SECONDARY}"])
            add(b, [f"spanning-tree vlan {v} priority {SECONDARY}"], b=[f"spanning-tree vlan {v} priority {PRIMARY}"])
            note.append({"fault": f, "vlan": v, "root": r, "backup": b})
        elif f == "t_dist_weak_missing":
            vs = rnd.choice([[A, C], [B]])
            w = d["weak"][vs[0]]
            for v in vs:
                del st[w]["prio"][v]
            add(w, [f"spanning-tree vlan {v} priority {WEAK}" for v in vs],
                b=[f"no spanning-tree vlan {v} priority" for v in vs])
            note.append({"fault": f, "sw": w, "vlans": vs})
        elif f == "t_dist_weak_wrong_vlan":
            v = rnd.choice(d["vlans"])
            w = d["weak"][v]
            o = other(DIST, w)
            del st[w]["prio"][v]
            st[o]["prio"][v] = WEAK
            add(w, [f"spanning-tree vlan {v} priority {WEAK}"], b=[f"no spanning-tree vlan {v} priority"])
            add(o, [f"no spanning-tree vlan {v} priority"], b=[f"spanning-tree vlan {v} priority {WEAK}"])
            note.append({"fault": f, "vlan": v, "right": w, "wrong": o})
        elif f == "t_rootguard_up":
            s = rnd.choice(DIST)
            p = rnd.choice(ports_dir(s, "up"))
            set_guard(st, s, p, "spanning-tree guard root")
            add(s, [f"interface {p}", "no spanning-tree guard" if glob else "spanning-tree guard loop"],
                b=[f"interface {p}", "spanning-tree guard root"])
            note.append({"fault": f, "sw": s, "port": p})
        elif f == "t_loopguard_down":
            s = rnd.choice(CORE + DIST)
            p = rnd.choice(ports_dir(s, "down"))
            set_guard(st, s, p, None if glob else "spanning-tree guard loop")
            add(s, [f"interface {p}", "spanning-tree guard root"],
                b=[f"interface {p}", "no spanning-tree guard" if glob else "spanning-tree guard loop"])
            note.append({"fault": f, "sw": s, "port": p})
        elif f == "t_acc_priority":
            a = rnd.choice(ACC)
            v = rnd.choice(d["vlans"])
            pr = rnd.choice([4096, 20480, 28672])
            st[a]["prio"][v] = pr
            add(a, [f"no spanning-tree vlan {v} priority"], b=[f"spanning-tree vlan {v} priority {pr}"])
            note.append({"fault": f, "sw": a, "vlan": v, "prio": pr, "visible": pr < PRIMARY})
        elif f == "t_cost_bump_dist":
            s = rnd.choice(DIST)
            v = rnd.choice(d["vlans"])
            p = toward(s, d["root"][v])
            c = 3 * LONG_BASE[PFX]              # 直行(1 本)より、予備コア経由(2 本)の方が安くなる値
            st[s]["ifs"][p]["lines"].append(f"spanning-tree vlan {v} cost {c}")
            add(s, [f"interface {p}", f"no spanning-tree vlan {v} cost"],
                b=[f"interface {p}", f"spanning-tree vlan {v} cost {c}"])
            note.append({"fault": f, "sw": s, "vlan": v, "port": p, "cost": c})
        elif f == "t_allowed_hole":
            s = rnd.choice(DIST)
            v = rnd.choice([x for x in d["vlans"] if d["prefer"][x] == s])   # 上りが通るはずの側から抜く
            a = rnd.choice(ACC)
            p = toward(s, a)
            st[s]["ifs"][p]["allowed"] = ",".join(str(x) for x in sorted(d["vlans"]) if x != v)
            add(s, [f"interface {p}", f"switchport trunk allowed vlan add {v}"],
                b=[f"interface {p}", f"switchport trunk allowed vlan remove {v}"])
            note.append({"fault": f, "sw": s, "port": p, "vlan": v, "acc": a})
        elif f == "t_mode_pvst":
            s = rnd.choice(SWS)
            st[s]["mode"] = "pvst"
            add(s, ["spanning-tree mode rapid-pvst"], b=["spanning-tree mode pvst"])
            for t in SWS:
                add(t, exe=["clear spanning-tree detected-protocols"])
            note.append({"fault": f, "sw": s})
        elif f == "t_bpduguard_uplink":
            a = rnd.choice(ACC)
            p = rnd.choice(ports_dir(a, "up"))
            st[a]["ifs"][p]["lines"].append("spanning-tree bpduguard enable")
            add(a, [f"interface {p}", "no spanning-tree bpduguard enable", "shutdown", "no shutdown"],
                b=[f"interface {p}", "spanning-tree bpduguard enable"])
            note.append({"fault": f, "sw": a, "port": p})
        elif f == "t_loopguard_trip":
            s = rnd.choice(CORE)
            p = toward(s, other(CORE, s))
            st[s]["ifs"][p]["lines"].append("spanning-tree bpdufilter enable")
            add(s, [f"interface {p}", "no spanning-tree bpdufilter enable"],
                b=[f"interface {p}", "spanning-tree bpdufilter enable"])
            note.append({"fault": f, "sw": s, "port": p})
        elif f == "t_pathcost_short":
            s = rnd.choice(DIST)
            st[s]["long"] = False
            add(s, ["spanning-tree pathcost method long"], b=["spanning-tree pathcost method short"])
            note.append({"fault": f, "sw": s})
        else:
            raise SystemExit(f"unknown fault {f}")
    return note, fix, brk


def render(d, st, s, seed):
    L = [f"! 自動生成(gen_stp --world 3tier) seed={seed} {s} = {LABEL[s]}", "vtp mode transparent"]
    for v in sorted(d["vlans"]):
        L += [f"vlan {v}", f" name DATA{v}"]
    if s in ACC:
        L += [f"vlan {PARK}", " name PARK"]
    L += ["!", f"spanning-tree mode {st[s]['mode']}", "spanning-tree extend system-id"]
    if st[s]["long"]:
        L.append("spanning-tree pathcost method long")
    L += glob_lines(st, s) + prio_lines(st, s) + ["!"]
    for name in sorted(st[s]["ifs"], key=slot_port):
        c = st[s]["ifs"][name]
        sl, po = slot_port(name)
        L.append(f"interface {{{{ links[{sl * 4 + po}] }}}}")
        if c["trunk"]:
            L += [" switchport trunk encapsulation dot1q", " switchport mode trunk",
                  f" switchport trunk allowed vlan {c['allowed']}"]
        else:
            L += [" switchport mode access", f" switchport access vlan {c['vlan']}"]
        L += [f" {x}" for x in c["lines"]] + [" no shutdown", "!"]
    L += [f"interface {MGMT_IF}", " spanning-tree bpdufilter enable", "!"]
    if s in ACC:
        for v in sorted(d["vlans"]):
            L += [f"interface Vlan{v}", f" ip address {svi_ip(d, v, s)} 255.255.255.0", " no shutdown", "!"]
    return "\n".join(L) + "\n"


def render_rogue(seed):
    return "\n".join([f"! 自動生成(gen_stp --world 3tier) seed={seed} SW07 = 持ち込みスイッチ(管理外)",
                      # priority 0= 接続先(駐車 VLAN)で root になり BPDU を出し続ける → bpduguard が確実に発動。
                      # 最弱にすると root port 側になり RSTP では定期 BPDU を出さない(2 層盤面と同じ実測)。
                      "spanning-tree vlan 1 priority 0",
                      "interface {{ links[0] }}", " switchport mode access", " no shutdown", ""])


# ---------------------------------------------------------------------------
# 採点
# ---------------------------------------------------------------------------
P = {"root": 3, "backup": 2, "weak": 2, "role": 2, "incon": 1, "rogue": 7,
     "g_core": 2, "g_dist": 3, "g_acc": 1,           # 保護機構の実効(show spanning-tree vlan <A> detail)
     "a_core": 1, "a_dist": 2, "a_acc": 2,           # 監査(running-config)
     "errdis": 2, "ping": 2}
LOOP_LINE = r"Loop guard is enabled(?: by default)? on the port"
ROOT_LINE = r"Root guard is enabled on the port"


def guard_block_regex(p, v, line):
    """`show spanning-tree vlan <v> detail` の「 Port N (IF) of VLAN00NN is …」ブロック内に line があるか。
    次のポートのブロックへはみ出さない(PoC G2 の書式)。"""
    return (rf"(?m)^ Port \d+ \({re.escape(p)}\) of VLAN{v:04d} is [^\n]*\n"
            rf"(?:(?! Port \d+ \().*\n)*?\s+{line}")


def grading(d, pid):
    roles = expected_roles(d)
    rs = {"Root": "Root FWD", "Desg": "Desg FWD", "Altn": "Altn BLK"}
    allv = ",".join(str(v) for v in sorted(d["vlans"]))
    pd = port_dir()
    style = d["style"]
    gv = d["A"]
    ck = []
    for v in d["vlans"]:
        ck.append({"name": f"VLAN{v}: root ブリッジが設計どおり {d['root'][v]}({LABEL[d['root'][v]]})",
                   "node": d["root"][v], "command": f"show spanning-tree vlan {v}",
                   "raw": [{"regex": "This bridge is the root"}], "points": P["root"]})
    for v in d["vlans"]:
        b = d["backup"][v]
        ck.append({"name": f"VLAN{v}: 予備 root({b})の bridge priority が {SECONDARY}",
                   "node": b, "command": f"show spanning-tree vlan {v}",
                   "raw": [{"regex": rf"Bridge ID\s+Priority\s+{SECONDARY + v}\b"}], "points": P["backup"]})
    for v in d["vlans"]:
        w = d["weak"][v]
        ck.append({"name": f"VLAN{v}: 分配間でブロックする側({w})の bridge priority が {WEAK}(MAC 依存にしない)",
                   "node": w, "command": f"show spanning-tree vlan {v}",
                   "raw": [{"regex": rf"Bridge ID\s+Priority\s+{WEAK + v}\b"}], "points": P["weak"]})
    for s in SWS:
        for v in d["vlans"]:
            raw = [{"regex": "Spanning tree enabled protocol rstp"}]
            for (sw, p), role in sorted(roles[v].items()):
                if sw == s:
                    raw.append({"regex": rf"(?m)^{p}\s+{rs[role]}\s"})
            raw.append({"not_regex": rf"(?m)^{SH}[01]/\d\s.*(BKN|_Inc|Peer\(STP\))"})
            ck.append({"name": f"{s}({LABEL[s]}): VLAN{v} の各ポートの役割と状態が設計どおり(RSTP)",
                       "node": s, "command": f"show spanning-tree vlan {v}", "raw": raw, "points": P["role"]})
    for s in SWS:
        ck.append({"name": f"{s}: 不整合(inconsistent)状態のポートが無い",
                   "node": s, "command": "show spanning-tree inconsistentports",
                   "raw": [{"regex": r"in the system\s*:\s*0\b"}], "points": P["incon"]})
    ra, rp = d["rogue_acc"], d["rogue_port"]
    ck.append({"name": f"{ra}: 持ち込み機器の {sh(rp)} が BPDU ガードで遮断(err-disabled)されている",
               "node": ra, "command": "show interfaces status err-disabled",
               "raw": [{"regex": rf"(?m)^{sh(rp)}\s.*err-disabled\s+bpduguard"}], "points": P["rogue"]})
    # 保護機構の実効(記述方式に依存しない= BL-222)
    for s in SWS:
        raw = [{"regex": guard_block_regex(p, gv, ROOT_LINE if pd[(s, p)] == "down" else LOOP_LINE)}
               for p in trunks_of(s)]
        lay = "g_acc" if s in ACC else "g_dist" if s in DIST else "g_core"
        ck.append({"name": f"{s}({LABEL[s]}): 保護機構の実効(下位層へ向くポート= root guard・上位層/同一層= loop guard)",
                   "node": s, "command": f"show spanning-tree vlan {gv} detail", "raw": raw, "points": P[lay]})

    # 監査(running-config)
    def audit(s):
        out = [{"regex": rf"interface {p}\r?\n(?: .*\r?\n)*? switchport trunk allowed vlan {allv}\r?\n"}
               for p in trunks_of(s)]
        out.append({"regex": r"(?m)^spanning-tree pathcost method long"})
        out.append({"not_regex": r"(?m)^ spanning-tree (vlan \S+ )?cost "})
        out.append({"not_regex": r"(?m)^ spanning-tree (vlan \S+ )?port-priority "})
        out.append({"not_regex": rf"interface {PFX}[0-2]/\d\r?\n(?: .*\r?\n)*? spanning-tree bpdufilter"})
        out.append({"not_regex": r"(?m)^spanning-tree portfast (edge )?bpdufilter default"})
        if s in ACC:
            for p in EDGE:
                out.append({"regex": rf"(?m)(?:^spanning-tree portfast (?:edge )?default\r?$"
                                     rf"|^interface {p}\r?\n(?: .*\r?\n)*? spanning-tree portfast)"})
                out.append({"regex": rf"(?m)(?:^spanning-tree portfast (?:edge )?bpduguard default\r?$"
                                     rf"|^interface {p}\r?\n(?: .*\r?\n)*? spanning-tree bpduguard enable)"})
            out.append({"not_regex": r"(?m)^spanning-tree vlan \S+ priority"})
        if style == "port":
            out.append({"not_regex": r"(?m)^spanning-tree (loopguard |portfast (edge )?(bpduguard )?)default"})
        elif style == "global":
            out.append({"regex": r"(?m)^spanning-tree loopguard default"})
            if s in ACC:
                out.append({"regex": r"(?m)^spanning-tree portfast edge default"})
                out.append({"regex": r"(?m)^spanning-tree portfast edge bpduguard default"})
        return out

    how = {"port": "・既定値不使用", "global": "・既定値で付与", "any": ""}[style]
    for s in SWS:
        what = ("エッジ= portfast+BPDU ガード・priority 設定無し" if s in ACC else "priority 以外の個別設定無し")
        lay = "a_acc" if s in ACC else "a_dist" if s in DIST else "a_core"
        ck.append({"name": f"{s}({LABEL[s]}): 監査({what}{how}・許可 VLAN・long・個別 cost/port-priority・bpdufilter 無し)",
                   "node": s, "command": AUDIT_CMD, "raw": audit(s), "points": P[lay]})
    ck.append({"name": f"{ra}: BPDU ガードによる err-disabled を自動復旧させていない", "node": ra,
               "command": "show errdisable recovery",
               "raw": [{"regex": r"(?m)^bpduguard\s+Disabled"}], "points": P["errdis"]})
    for v in d["vlans"]:
        ck.append({"name": f"VLAN{v}: {ACC[0]} → {ACC[1]} の SVI 間疎通", "node": ACC[0],
                   "command": f"ping {svi_ip(d, v, ACC[1])} repeat 5",
                   "raw": [{"regex": r"Success rate is (100|80) percent"}], "points": P["ping"]})
    total = sum(c["points"] for c in ck)
    assert total == 100, total
    for c in ck:
        for r in c["raw"]:
            re.compile(list(r.values())[0])
    return {"problem": pid, "total_points": 100, "defaults": {"genie_os": "iosxe"}, "checks": ck}


# ---------------------------------------------------------------------------
# 問題文
# ---------------------------------------------------------------------------
STYLE_ROW = {
    "port": "| 保護機構の設定方法 | ポートごとに設定する。スイッチ全体の既定値として有効にする方法は使わない |",
    "global": "| 保護機構の設定方法 | エッジの 2 機能(待たずに転送・BPDU で遮断)と、上位層・同一層向けの BPDU 途絶対策は、"
              "**スイッチ全体の既定値として**有効にする。既定値のままでは要件を満たせないポートだけをポートごとに設定する |",
    "any": None,
}


def design_rows(d):
    A, B, C = d["A"], d["B"], d["C"]
    ac = "・".join(f"VLAN{v}" for v in sorted((A, C)))       # 表は VLAN 番号の昇順で見せる
    rows = [
        "| STP モード | 全スイッチ Rapid PVST+ |",
        "| パスコスト | 32 ビット値の方式(long)に全スイッチで統一する |",
        f"| {ac} | root= {d['root'][A]}(bridge priority {PRIMARY})・予備 root= {d['backup'][A]}"
        f"(bridge priority {SECONDARY}) |",
        f"| VLAN{B} | root= {d['root'][B]}(bridge priority {PRIMARY})・予備 root= {d['backup'][B]}"
        f"(bridge priority {SECONDARY}) |",
        "| 分配層(SW03・SW04) | **VLAN ごとに片方だけ bridge priority 36864** とし、もう片方は既定のままにする。"
        f"36864 を振るのは {ac} が {d['weak'][A]}、VLAN{B} が {d['weak'][B]}。"
        "これにより、分配間リンクでブロッキングになる側と、アクセス層の上りが通る側を"
        "スイッチの MAC アドレスに依存せず決める |",
        "| アクセス層(SW05・SW06) | bridge priority は既定のまま |",
        "| 保護機構(方針) | **上位層へ向くポートと同一層のスイッチ間リンク**は、BPDU が途絶えても"
        "(片方向障害など)転送状態へ移行させない。**下位層へ向くポート**は、下位側から優位な BPDU を受けても"
        " root の座を明け渡さない。ポートは列挙しない(構成台帳から判断すること) |",
        f"| アクセスのエッジ({SH}1/0〜{SH}1/3) | 端末の接続時は待たずに転送を始める。BPDU を受けたら直ちに遮断し、"
        "自動復旧はさせない |"]
    if STYLE_ROW[d["style"]]:
        rows.append(STYLE_ROW[d["style"]])
    rows.append("| 使用しない手段 | ポート単位・VLAN 単位のパスコスト変更と port-priority は使用しない |")
    rows.append(f"| trunk | 802.1Q・許可 VLAN は {','.join(str(v) for v in sorted(d['vlans']))} のみ(全 trunk 共通) |")
    return rows


def task_md(d, pid, mode="build", faults=(), note=()):
    vls = ",".join(str(v) for v in sorted(d["vlans"]))
    rog = f"{d['rogue_acc']} {sh(d['rogue_port'])}"
    if mode == "ts":
        seen = []
        for n in note:
            s = SYMPTOM_ACC[n["visible"]] if n["fault"] == "t_acc_priority" else SYMPTOM[n["fault"]]
            if s not in seen:
                seen.append(s)
        L = [f"# 障害対応 {pid} : 3 層キャンパス L2 のスパニングツリーが設計書と一致しない", "",
             "## 状況",
             "コア 2 台・分配 2 台・アクセス 2 台の 3 層キャンパス L2 です。定期点検の結果、"
             "スパニングツリーの状態と設定が設計書と一致しないことが判明しました。運用から次の申告も上がっています。", ""]
        L += [f"> - {s}" for s in seen]
        L += ["", f"なお、{rog} には利用者が持ち込んだスイッチ(SW07)が接続されたままで、"
                  "これが遮断されている状態が設計どおりです。", "",
              "設計書どおりの状態に復旧してください。**原因は 1 か所とは限りません。**", "",
              "## 設計書(抜粋)", "", "| 項目 | 設計 |", "|---|---|"] + design_rows(d)
    else:
        L = [f"# 構築 {pid} : 3 層キャンパス L2 のスパニングツリー設計適用", "",
             "## 状況",
             "コア 2 台・分配 2 台・アクセス 2 台の 3 層キャンパス L2 に、スパニングツリーの設計を適用します。",
             f"VLAN({vls})・trunk・アクセス層の SVI・エッジポートの所属 VLAN は構築済みで、スパニングツリーは"
             "全台とも既定値(Rapid PVST+)のままです。",
             f"また、{rog} には利用者が持ち込んだスイッチ(SW07)が接続されたままになっています。", "",
             "次の要件書に従って設定してください。"
             + ("実現手段は問いませんが、" if d["style"] == "any" else "")
             + "要件書に反する設定は減点します。", "",
             "## 要件書", "", "| 項目 | 要件 |", "|---|---|"] + design_rows(d) + [
             "| 変更範囲 | スパニングツリーの設定のみ。VLAN・trunk・SVI・ポートの所属 VLAN は変更しない |", "",
             "## 完了条件",
             "- 各 VLAN の root・予備 root が要件どおりで、6 台すべてのポートの役割が設計どおりであること。",
             "- 分配間リンクは正常時ブロッキングで、ブロックする側が要件どおりに固定されていること。",
             f"- {rog} が遮断され、自動復旧しないこと。",
             f"- {ACC[0]} と {ACC[1]} の SVI 間で各 VLAN の疎通があること。"]
    L += ["", "## 構成台帳", "", "| 機器 | 役割 | 配線 |", "|---|---|---|"]
    wiring = {s: [] for s in SWS}
    for a, ia, b, ib in LINKS:
        wiring[a].append(f"{sh(ifn(ia))}→{b}")
        wiring[b].append(f"{sh(ifn(ib))}→{a}")
    for s in SWS:
        w = " / ".join(wiring[s])
        if s in ACC:
            w += f" / {SH}1/0〜{SH}1/3= エッジ"
        L.append(f"| {s} | {LABEL[s]} | {w} |")
    L += [f"| {ROGUE} | 持ち込み機器(管理外・ログイン禁止) | {rog}(未使用ポート・駐車 VLAN {PARK})に接続 |", "",
          "SVI(疎通確認用・アクセス層のみ): " + " / ".join(
              f"VLAN{v}= 10.{d['oct2']}.{v}.<SW 番号>/24" for v in sorted(d["vlans"])), "",
          "## 注意",
          f"- 管理 VLAN(999)・各機の {MGMT_IF} には触れないこと。{ROGUE} にはログインしないこと。",
          "- ポートの shutdown / no shutdown は実施してよい(設定の変更には数えない)。"]
    if mode == "ts":
        L.append("- 設計書に無い設定は残さないこと。")
    L += ["", "## ログイン / 採点",
          "CML コンソール、または管理 IP へ telnet(user SUZUKI / pass CCNP。管理 IP は出題時の割当表を参照)。", "```",
          f"scripts/lab.sh grade {pid}", "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------
def generate(seed, mode, nfaults=0, forced=None, style=None):
    rnd = random.Random(seed)
    d = design(rnd, style)
    if mode == "ts":
        st = base_state(d)
        faults = pick_faults(rnd, nfaults or rnd.choice([2, 3]), forced)
        for g in EXCLUSIVE:
            if len(g & set(faults)) > 1:
                raise SystemExit(f"同時に選べない故障の組: {sorted(g & set(faults))}")
        note, fix, brk = inject(rnd, d, st, faults)
        title, topics = f"3 層キャンパス STP 障害対応 (seed={seed})", ["3tier", "troubleshooting"]
    else:
        st = build_state(d)
        faults, note, fix, brk = [], [], build_fix(d), {}
        title, topics = f"3 層キャンパス STP 構築 (seed={seed})", ["3tier", "build"]
    pid = f"GEN-STP-{seed}"
    initial = {s: render(d, st, s, seed) for s in SWS}
    initial[ROGUE] = render_rogue(seed)
    ri = EDGE.index(d["rogue_port"]) + 4
    links = [{"a": a, "a_if": ia, "b": b, "b_if": ib} for a, ia, b, ib in LINKS]
    links.append({"a": d["rogue_acc"], "a_if": ri, "b": ROGUE, "b_if": 0})
    return {"pid": pid, "d": d, "st": st, "faults": faults, "note": note, "fix": fix, "break": brk,
            "initial": initial, "grading": grading(d, pid), "task": task_md(d, pid, mode, faults, note),
            "diff": 5, "topics": topics + [f"style-{d['style']}"], "title": title,
            "nodes": SWS + [ROGUE], "links": links,
            "positions": dict(POS, **{ROGUE: ROGUE_POS[d["rogue_acc"]]}),
            "image_family": IMAGE_FAMILY[PFX]}


def selftest():
    ng = 0
    cases = 0
    # 0) port 世界の「既定値不使用」判定は 3 種すべてのグローバル既定に当たること(2026-09-27 E2E で loopguard の取りこぼしを修正)
    set_image("iosv")
    g0 = grading(design(random.Random(1), "port"), "X")
    nx = [r["not_regex"] for c in g0["checks"] if c["command"] == AUDIT_CMD for r in c["raw"]
          if "not_regex" in r and "default" in r["not_regex"] and "bpdufilter" not in r["not_regex"]][0]
    for line in list(GLOBAL_LINES.values()) + ["spanning-tree portfast default"]:
        if not re.search(nx, line):
            ng += 1
            print(f"NG 既定値の検出漏れ: {line}")
    for image in ("iol", "iosv"):
        set_image(image)
        styles = ("port", "any") if image == "iol" else STYLES
        for seed in range(1, 151):
            for style in styles:
                cases += 1
                try:
                    g = generate(seed, "build", style=style)
                    d = g["d"]
                    assert d["style"] == style
                    roles = expected_roles(d)
                    # 1) 決定性: MAC の並びを逆にしても役割が変わらない(§2)
                    assert roles == expected_roles(d, rev_mac=True), "MAC 依存の判定が残っている"
                    for v in d["vlans"]:
                        r = roles[v]
                        # 2) 分配間リンクは weak 側がブロック
                        assert r[(d["weak"][v], sh(ifn(2)))] == "Altn", "分配間のブロック側が設計と違う"
                        assert r[(d["prefer"][v], sh(ifn(2)))] == "Desg"
                        # 3) アクセスの root port は prefer 側の分配へ向くポート
                        for a in ACC:
                            assert r[(a, sh(toward(a, d["prefer"][v])))] == "Root", (a, v)
                            assert sum(1 for (w, _), x in r.items() if w == a and x == "Root") == 1
                        # 4) 予備コアの上りは root port・root コアは全ポート Desg
                        assert r[(d["backup"][v], sh(ifn(0)))] == "Root"
                        assert all(x == "Desg" for (w, _), x in r.items() if w == d["root"][v])
                    # 5) 白紙化: 初期 config に STP の設計要素が出ない
                    txt = "".join(g["initial"][s] for s in SWS)
                    for bad in ("guard", "priority", "portfast", "bpduguard", "pathcost", "loopguard"):
                        assert bad not in txt, f"初期 config に {bad} が残っている"
                    assert txt.count("spanning-tree bpdufilter enable") == len(SWS)   # mgmt 隔離のみ
                    # 6) 模範解: 方式ごとの形
                    allc = "\n".join(x for f in g["fix"].values() for x in f["conf"])
                    assert allc.count("guard root") == 8, allc.count("guard root")   # 下り 8 本は常に明示
                    assert allc.count("pathcost method long") == len(SWS)
                    assert allc.count("priority 24576") == 3 and allc.count("priority 28672") == 3
                    assert allc.count("priority 36864") == 3
                    if style == "global":
                        assert allc.count("guard loop") == 0 and allc.count("loopguard default") == 6
                        assert allc.count("portfast edge default") == 2
                        assert allc.count("portfast edge bpduguard default") == 2
                        assert "bpduguard enable" not in allc
                    else:
                        assert allc.count("guard loop") == 12, allc.count("guard loop")  # 上り 8 + 同層 4
                        assert allc.count("bpduguard enable") == 8 and allc.count("portfast") == 8
                        assert "default" not in allc
                    # 7) 採点表(収集コマンド数)と問題文
                    assert len({(c["node"], c["command"]) for c in g["grading"]["checks"]}) <= 41
                    assert ("保護機構の設定方法" in g["task"]) == (style != "any")
                    # 8) TS: 各故障が構成に現れる・fix/break がある・決定的な故障は役割を変える
                    base = {s: render(d, base_state(d), s, seed) for s in SWS}
                    for forced in [None] + [[f] for f in FAULTS]:
                        cases += 1
                        t = generate(seed, "ts", 0, forced, style)
                        for grp in EXCLUSIVE:
                            assert len(grp & set(t["faults"])) <= 1, t["faults"]
                        assert {s: t["initial"][s] for s in SWS} != base, f"故障が構成に現れない {t['faults']}"
                        assert t["fix"] and all(t["break"].get(s) or not f["conf"] for s, f in t["fix"].items())
                        if forced and forced[0] in ("t_core_prio_swap", "t_dist_weak_wrong_vlan", "t_cost_bump_dist"):
                            assert roles_of_state(t["d"], t["st"]) != roles, f"{forced} で役割が変わらない"
                        if forced == ["t_loopguard_down"] and style == "global":
                            n = t["note"][0]
                            assert t["st"][n["sw"]]["ifs"][n["port"]]["lines"] == []
                except AssertionError as e:
                    ng += 1
                    print(f"NG 3tier image={image} seed={seed} style={style}: {e}")
    set_image("iol")
    print(f"selftest(3tier): {cases} cases NG={ng}")
    return ng


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(1 if selftest() else 0)
