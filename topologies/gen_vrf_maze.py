#!/usr/bin/env python3
"""おまけ「VRF迷路」生成器（BL-092・たたき台）。

物理は RT01(迷路本体) ─ Et0/0 1本 ─ RT02(折り返し役) の2台のみ。
その1本を dot1q サブIF × 2(n-1) 本の「廊下」に分割し、パケットが
  ROOM1(RT01) →廊下1→ TURN1(RT02) →廊下2→ ROOM2(RT01) →廊下3→ ...
と同じ物理リンクを何往復もしながら、渡るたびに別 VRF(部屋)へ入り直す。
各 VRF は入り口/出口のサブIF2本だけを持ち、静的経路2本(順路=GOAL宛・
帰路=START宛)で次の部屋へ縫う。START/GOAL は RT01 上の部屋 Lo。

  traceroute の各行 = 「何歩目にどの廊下を渡ったか」の足跡になる。

故障カタログ(--fault で指定・既定は seed 抽選):
  fw_gap        順路静的の欠落(迷路が途中で行き止まり)              難2
  bw_gap        帰路静的の欠落(行けるのに帰れない・全ホップ*)        難3
  vlan_mismatch RT02側サブIFの encapsulation 誤り(死に廊下)          難2
  vrf_cross     RT01側入り口サブIFの部屋違い(壁抜けショートカット。
                ping は成功するが歩数が仕様より短い)                 難3
  loop_static   順路静的が後ろ向き(同じ廊下を往復して TTL 切れ)      難3
  healthy       故障なし(デモ・実機PoC用)

出力: problems/GEN-VRFMAZE-<seed>/ {problem.yml, initial/*.cfg.j2, task.md,
      grading.yml, solution/{fault.json, fix.json}}
使い方: gen_vrf_maze.py --repo . --seed <int> [--rooms 3-5] [--fault <name>]
        gen_vrf_maze.py --selftest   (転送シミュレータで全故障×多seedを機械検証)

★実機未検証(たたき台)。特に要確認: ①IOL day0 でのサブIF+VRF受理
②IPなし物理IFの up 維持 ③traceroute 最終行が GOAL 表記か着信IF表記か
(採点は両対応 regex にしてある)。IOSv で使う場合は cvac_bringup 必須。
"""
import argparse
import json
import os
import random

import yaml

FAULTS = ["fw_gap", "bw_gap", "vlan_mismatch", "vrf_cross", "loop_static"]
DIFFICULTY = {"fw_gap": 2, "bw_gap": 3, "vlan_mismatch": 2,
              "vrf_cross": 3, "loop_static": 3, "healthy": 2}
COLORS = ["RED", "BLUE", "GREEN", "AMBER", "IVORY", "OLIVE", "RUBY", "TEAL"]
PHY = "Ethernet0/0"          # iol 既定(problem.yml の image_family 未指定)
PHY_SHORT = "Et0/0"          # show vrf detail の表示形


class Maze:
    """迷路の正解モデル。k=1..L が廊下(VLAN)番号。奇数k=RT01→RT02 向き。"""

    def __init__(self, rnd, n_rooms):
        self.n = n_rooms
        self.L = 2 * (n_rooms - 1)
        self.rooms = [f"ROOM-{c}" for c in rnd.sample(COLORS, n_rooms)]
        self.turns = [f"TURN{i}" for i in range(1, n_rooms)]
        picks = rnd.sample(range(101, 900), self.L + 1)
        self.vlans = picks[:self.L]          # 廊下k の VLAN = vlans[k-1]
        self.wrong_vlan = picks[self.L]      # vlan_mismatch 用(未使用番号)
        self.x = rnd.randint(60, 99)         # 中継 /30 = 10.<x>.<k>.0/30
        o2 = rnd.randint(16, 31)
        sa, sb = rnd.sample(range(2, 250), 2)
        self.start = f"172.{o2}.{sa}.1"      # RT01 Lo11 (部屋1)
        self.goal = f"172.{o2}.{sb}.1"       # RT01 Lo99 (最終部屋)

    # --- 正解の所属・縫い ---
    def room_of(self, k):        # RT01側サブIF(廊下k)の部屋 index(1..n)
        return (k + 1) // 2 if k % 2 else k // 2 + 1

    def turn_of(self, k):        # RT02側サブIF(廊下k)の TURN index(1..n-1)
        return (k + 1) // 2

    def sub(self, k):
        return f"{PHY}.{self.vlans[k - 1]}"

    def ip1(self, k):
        return f"10.{self.x}.{k}.1"          # RT01 側

    def ip2(self, k):
        return f"10.{self.x}.{k}.2"          # RT02 側

    def rt01_statics(self):      # (vrf, dest, 廊下k, next-hop) の一覧
        out = []
        for j in range(1, self.n + 1):
            if j < self.n:                   # 順路: 部屋j → 廊下2j-1
                out.append((self.rooms[j - 1], self.goal, 2 * j - 1,
                            self.ip2(2 * j - 1), "fw"))
            if j > 1:                        # 帰路: 部屋j → 廊下2j-2
                out.append((self.rooms[j - 1], self.start, 2 * j - 2,
                            self.ip2(2 * j - 2), "bw"))
        return out

    def rt02_statics(self):
        out = []
        for i in range(1, self.n):
            out.append((self.turns[i - 1], self.goal, 2 * i,
                        self.ip1(2 * i), "fw"))
            out.append((self.turns[i - 1], self.start, 2 * i - 1,
                        self.ip1(2 * i - 1), "bw"))
        return out

    def footprints(self):        # 健全時の traceroute 足跡(1..L歩目の中継IP)
        # 奇数k=RT02が受ける(.2)・偶数k=RT01が受ける(.1)。最終L歩目はGOAL部屋着。
        return [self.ip2(k) if k % 2 else self.ip1(k)
                for k in range(1, self.L)] + [self.goal]


def pick_fault_detail(rnd, m, fault):
    """故障の被害箇所を seed から決める。fix と task で共有する値を返す。"""
    d = {"fault": fault}
    if fault == "fw_gap":
        side = rnd.choice(["RT01", "RT02"])
        d["side"] = side
        d["idx"] = rnd.randint(1, m.n - 1)   # 部屋j / TURNi
    elif fault == "bw_gap":
        side = rnd.choice(["RT01", "RT02"])
        d["side"] = side
        d["idx"] = rnd.randint(2, m.n) if side == "RT01" else rnd.randint(1, m.n - 1)
    elif fault == "vlan_mismatch":
        d["k"] = rnd.randint(1, m.L)         # RT02 側サブIFの encap を壊す
    elif fault == "vrf_cross":
        j = rnd.randint(2, m.n - 1)          # 被害=部屋j の入り口(偶数廊下2j-2)
        d["j"] = j
        d["k"] = 2 * (j - 1)
        d["to"] = rnd.randint(j + 1, m.n)    # 前向きの別部屋へ(決定的ショートカット)
    elif fault == "loop_static":
        d["j"] = rnd.randint(2, m.n - 1)     # 部屋j の順路を後ろ向きに
    return d


def render_rt01(m, fd):
    L = ["! RT01 初期状態 (VRF迷路・迷路本体。各部屋=VRF)"]
    for i, r in enumerate(m.rooms, 1):
        L += [f"vrf definition {r}", f" rd 65000:{100 + i}",
              " address-family ipv4", " exit-address-family", "!"]
    L += ["interface {{ links[0] }}", " no shutdown", "!"]
    for k in range(1, m.L + 1):
        room = m.rooms[m.room_of(k) - 1]
        if fd.get("fault") == "vrf_cross" and k == fd.get("k"):
            room = m.rooms[fd["to"] - 1]
        L += [f"interface {{{{ links[0] }}}}.{m.vlans[k - 1]}",
              f" encapsulation dot1q {m.vlans[k - 1]}",
              f" vrf forwarding {room}",
              f" ip address {m.ip1(k)} 255.255.255.252", "!"]
    L += ["interface Loopback11", f" vrf forwarding {m.rooms[0]}",
          f" ip address {m.start} 255.255.255.255", "!",
          "interface Loopback99", f" vrf forwarding {m.rooms[-1]}",
          f" ip address {m.goal} 255.255.255.255", "!"]
    for vrf, dest, k, nh, kind in m.rt01_statics():
        j = m.rooms.index(vrf) + 1
        if fd.get("fault") == "fw_gap" and fd.get("side") == "RT01" \
                and kind == "fw" and j == fd["idx"]:
            continue
        if fd.get("fault") == "bw_gap" and fd.get("side") == "RT01" \
                and kind == "bw" and j == fd["idx"]:
            continue
        if fd.get("fault") == "loop_static" and kind == "fw" and j == fd["j"]:
            kb = 2 * j - 2                   # 後ろ向き(入り口廊下へ送り返す)
            L.append(f"ip route vrf {vrf} {dest} 255.255.255.255 "
                     f"{{{{ links[0] }}}}.{m.vlans[kb - 1]} {m.ip2(kb)}")
            continue
        L.append(f"ip route vrf {vrf} {dest} 255.255.255.255 "
                 f"{{{{ links[0] }}}}.{m.vlans[k - 1]} {nh}")
    return L


def render_rt02(m, fd):
    L = ["! RT02 初期状態 (VRF迷路・折り返し役)"]
    for i, t in enumerate(m.turns, 1):
        L += [f"vrf definition {t}", f" rd 65000:{200 + i}",
              " address-family ipv4", " exit-address-family", "!"]
    L += ["interface {{ links[0] }}", " no shutdown", "!"]
    for k in range(1, m.L + 1):
        vlan = m.vlans[k - 1]
        encap = vlan
        if fd.get("fault") == "vlan_mismatch" and k == fd.get("k"):
            encap = m.wrong_vlan
        L += [f"interface {{{{ links[0] }}}}.{vlan}",
              f" encapsulation dot1q {encap}",
              f" vrf forwarding {m.turns[m.turn_of(k) - 1]}",
              f" ip address {m.ip2(k)} 255.255.255.252", "!"]
    for vrf, dest, k, nh, kind in m.rt02_statics():
        i = m.turns.index(vrf) + 1
        if fd.get("fault") == "fw_gap" and fd.get("side") == "RT02" \
                and kind == "fw" and i == fd["idx"]:
            continue
        if fd.get("fault") == "bw_gap" and fd.get("side") == "RT02" \
                and kind == "bw" and i == fd["idx"]:
            continue
        L.append(f"ip route vrf {vrf} {dest} 255.255.255.255 "
                 f"{{{{ links[0] }}}}.{m.vlans[k - 1]} {nh}")
    return L


def build_fix(m, fd):
    """fix_generated.yml 互換。parents 省略=グローバル config。"""
    N = {"match": "none"}
    f = fd.get("fault")
    if f == "healthy":
        return []
    if f in ("fw_gap", "bw_gap"):
        node, idx = fd["side"], fd["idx"]
        table = m.rt01_statics() if node == "RT01" else m.rt02_statics()
        names = m.rooms if node == "RT01" else m.turns
        kind = "fw" if f == "fw_gap" else "bw"
        vrf, dest, k, nh, _ = next(
            r for r in table if r[4] == kind and names.index(r[0]) + 1 == idx)
        return [{"node": node, "lines": [
            f"ip route vrf {vrf} {dest} 255.255.255.255 {m.sub(k)} {nh}"], **N}]
    if f == "vlan_mismatch":
        k = fd["k"]
        return [{"node": "RT02", "parents": f"interface {m.sub(k)}",
                 "lines": [f"encapsulation dot1q {m.vlans[k - 1]}",
                           f"ip address {m.ip2(k)} 255.255.255.252"], **N}]
    if f == "vrf_cross":
        k = fd["k"]
        room = m.rooms[m.room_of(k) - 1]
        return [{"node": "RT01", "parents": f"interface {m.sub(k)}",
                 "lines": [f"vrf forwarding {room}",     # ★IPが剥がれるので再投入
                           f"ip address {m.ip1(k)} 255.255.255.252"], **N}]
    if f == "loop_static":
        j = fd["j"]
        vrf = m.rooms[j - 1]
        kb, kf = 2 * j - 2, 2 * j - 1
        return [{"node": "RT01", "lines": [
            f"no ip route vrf {vrf} {m.goal} 255.255.255.255 "
            f"{m.sub(kb)} {m.ip2(kb)}",
            f"ip route vrf {vrf} {m.goal} 255.255.255.255 "
            f"{m.sub(kf)} {m.ip2(kf)}"], **N}]
    raise ValueError(f)


def build_grading(m, prob_id):
    esc = lambda ip: ip.replace(".", r"\.")
    checks = []
    # --- 構成: 部屋/TURN の所属(表示形 Et0/0.<vlan>) 計40点 ---
    struct = []
    for j, r in enumerate(m.rooms, 1):
        rx = []
        if j > 1:
            rx.append({"regex": rf"{PHY_SHORT}\.{m.vlans[2 * j - 3]}\b"})
        if j < m.n:
            rx.append({"regex": rf"{PHY_SHORT}\.{m.vlans[2 * j - 2]}\b"})
        if j == 1:
            rx.append({"regex": r"Lo11\b"})
        if j == m.n:
            rx.append({"regex": r"Lo99\b"})
        struct.append({"name": f"RT01: 部屋 {r} の収容(入口/出口サブIF)",
                       "node": "RT01", "command": f"show vrf detail {r}",
                       "raw": rx})
    for i, t in enumerate(m.turns, 1):
        struct.append({"name": f"RT02: {t} の収容(廊下{2 * i - 1}/{2 * i})",
                       "node": "RT02", "command": f"show vrf detail {t}",
                       "raw": [{"regex": rf"{PHY_SHORT}\.{m.vlans[2 * i - 2]}\b"},
                               {"regex": rf"{PHY_SHORT}\.{m.vlans[2 * i - 1]}\b"}]})
    base, rem = divmod(40, len(struct))
    for i, c in enumerate(struct):
        c["points"] = base + (rem if i == 0 else 0)
    checks += struct
    # --- 実効: 温めping(0点) → 判定ping → 帰路ping → 足跡 → 歩数 ---
    r1, rn = m.rooms[0], m.rooms[-1]
    checks.append({"name": "RT01: 温め(ARP解決・採点対象外)", "node": "RT01",
                   "command": f"ping vrf {r1} {m.goal} source {m.start} repeat 3",
                   "raw": [{"regex": "Success rate"}], "points": 0})
    checks.append({"name": f"RT01: START→GOAL 迷路走破 ({m.start}→{m.goal})",
                   "node": "RT01",
                   "command": f"ping vrf {r1} {m.goal} source {m.start} repeat 10",
                   "raw": [{"regex": r"Success rate is (100|[89][0-9]) percent"}],
                   "points": 20})
    checks.append({"name": "RT01: GOAL→START 帰路走破",
                   "node": "RT01",
                   "command": f"ping vrf {rn} {m.start} source {m.goal} repeat 10",
                   "raw": [{"regex": r"Success rate is (100|[89][0-9]) percent"}],
                   "points": 10})
    trace = f"traceroute vrf {r1} {m.goal} source {m.start} numeric timeout 1 probe 2"
    fps = m.footprints()
    # ★実機知見(2026-08-05): ①最終行は GOAL でなく着信IF表記(10.x.L.1)
    #   ②ICMP レート制限で probe の一部が * になる → [* ]* を前置して吸収
    rx = [{"regex": rf"(?m)^\s*{h}\s+[* ]*{esc(ip)}\b"}
          for h, ip in enumerate(fps[:-1], 1)]
    rx.append({"regex": rf"(?m)^\s*{m.L}\s+[* ]*({esc(m.goal)}|{esc(m.ip1(m.L))})\b"})
    checks.append({"name": "RT01: traceroute 足跡が設計の順路と完全一致",
                   "node": "RT01", "command": trace, "raw": rx, "points": 20})
    checks.append({"name": f"RT01: ちょうど {m.L} 歩で GOAL(近道・遠回りなし)",
                   "node": "RT01", "command": trace,
                   "raw": [{"regex": rf"(?m)^\s*{m.L}\s+[* ]*({esc(m.goal)}|{esc(m.ip1(m.L))})\b"},
                           {"not_regex": rf"(?m)^\s*{m.L + 1}\s"}],
                   "points": 10})
    return {"problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"}, "checks": checks}


def build_task(m, prob_id, diff, seed):
    dir_ = {1: "RT01 → RT02", 0: "RT02 → RT01"}
    rows = []
    for k in range(1, m.L + 1):
        rows.append(f"| {k} | {m.vlans[k - 1]} | 10.{m.x}.{k}.0/30 "
                    f"| {m.rooms[m.room_of(k) - 1]} | {m.turns[m.turn_of(k) - 1]} "
                    f"| {dir_[k % 2]} |")
    room_rows = [f"| {j} | {r} | 65000:{100 + j} |"
                 + (f" Loopback11 = {m.start}/32 (START) |" if j == 1 else
                    f" Loopback99 = {m.goal}/32 (GOAL) |" if j == m.n else " - |")
                 for j, r in enumerate(m.rooms, 1)]
    return f"""# 問題 {prob_id} : VRF 迷路 — サブインターフェイス折り返しチェーン（おまけ・難易度{diff}）

## 状況

これは、通常の演習の合間の、1つの「おまけ」の問題です。

あなたのラボには、**RT01** と **RT02** という2つのルータが、**1本の物理リンク**
(`Ethernet0/0`) だけで、接続されています。この1本のリンクの上に、
dot1q サブインターフェイスによって、**{m.L} 本の「廊下」**が、構成されています。

RT01 は、**迷路の本体**です。{m.n} 個の VRF（以下「部屋」）を持ち、パケットは、
START の部屋から、廊下を渡って RT02 で折り返し、**そのたびに 1 つ先の部屋へ**
入り直しながら、GOAL の部屋を目指すことが、意図されています。RT02 は、
**折り返しの役**です。廊下のペアごとに 1 つの VRF（TURN）で、パケットを
折り返します。各 VRF の中の経路は、スタティック・ルートによって、縫われています。

しかしながら、直近の巡回検証において、この迷路は、**下記の設計仕様書の
とおりには動作していない**ことが、報告されています。あなたのタスクは、
原因を特定し、迷路が設計仕様書のとおりに動作することを、確実にすることです。

```
        ┌──────────── 廊下1 (VLAN {m.vlans[0]}) ───────────┐
 RT01   ├──────────── 廊下2 (VLAN {m.vlans[1]}) ───────────┤   RT02
(迷路)  ├──────────── ...  計{m.L}本 すべて Et0/0 上 ──────┤ (折り返し)
        └──────────── 廊下{m.L} (VLAN {m.vlans[-1]}) ──────┘
```

## 設計仕様書（正典）

### 部屋（RT01 の VRF）

| # | VRF | rd | Loopback |
|---|-----|----|----------|
{chr(10).join(room_rows)}

### 廊下（サブインターフェイス。サブIF番号 = VLAN ID・/30 の RT01 側 = .1 / RT02 側 = .2）

| 歩 | VLAN | 中継サブネット | RT01 側 VRF | RT02 側 VRF | 進行方向 |
|----|------|----------------|-------------|-------------|----------|
{chr(10).join(rows)}

### 経路の縫い方

- 各 VRF は、**GOAL ({m.goal}/32) 宛の順路**と、**START ({m.start}/32) 宛の帰路**の、
  スタティック・ルートを、上表の歩順のとおりに持つ（出口サブIF＋対向 IP 指定）。
- START の部屋には帰路は不要であり、GOAL の部屋には順路は不要です。

## 要求される最終状態

1. `ping vrf {m.rooms[0]} {m.goal} source {m.start}` が、成功すること。
2. `ping vrf {m.rooms[-1]} {m.start} source {m.goal}` （帰路）も、成功すること。
3. `traceroute vrf {m.rooms[0]} {m.goal} source {m.start}` が、**ちょうど {m.L} 歩**で、
   上表の順路のとおりの中継 IP を示すこと（近道も、遠回りも、あってはなりません）。

## 遵守事項

- RT01 / RT02 の**どちらにも**原因がある可能性があります（原因の種類・数は伏せる）。
- 追加の VRF・リンク・ルーティング・プロトコルを、導入してはなりません。
  スタティック・ルートは、設計仕様書の縫い順のもの**のみ**が、許可されます。
- 迷路を短絡させる直接経路（部屋を飛ばすルート・リーク等）は、禁止です。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""


# ---------------------------------------------------------------- selftest --
def simulate(m, fd, dest, start_room):
    """抽象転送シミュレータ。戻り=(結果, 足跡[受信側IP列])。"""
    vrf01 = {k: m.rooms[m.room_of(k) - 1] for k in range(1, m.L + 1)}
    if fd.get("fault") == "vrf_cross":
        vrf01[fd["k"]] = m.rooms[fd["to"] - 1]
    vrf02 = {k: m.turns[m.turn_of(k) - 1] for k in range(1, m.L + 1)}
    encap01 = {k: m.vlans[k - 1] for k in range(1, m.L + 1)}
    encap02 = dict(encap01)
    if fd.get("fault") == "vlan_mismatch":
        encap02[fd["k"]] = m.wrong_vlan
    routes = {}
    for vrf, d, k, _nh, kind in m.rt01_statics():
        j = m.rooms.index(vrf) + 1
        if fd.get("fault") == "fw_gap" and fd.get("side") == "RT01" \
                and kind == "fw" and j == fd["idx"]:
            continue
        if fd.get("fault") == "bw_gap" and fd.get("side") == "RT01" \
                and kind == "bw" and j == fd["idx"]:
            continue
        if fd.get("fault") == "loop_static" and kind == "fw" and j == fd["j"]:
            k = 2 * j - 2
        routes[("RT01", vrf, d)] = k
    for vrf, d, k, _nh, kind in m.rt02_statics():
        i = m.turns.index(vrf) + 1
        if fd.get("fault") == "fw_gap" and fd.get("side") == "RT02" \
                and kind == "fw" and i == fd["idx"]:
            continue
        if fd.get("fault") == "bw_gap" and fd.get("side") == "RT02" \
                and kind == "bw" and i == fd["idx"]:
            continue
        routes[("RT02", vrf, d)] = k
    local = {("RT01", m.rooms[0]): m.start, ("RT01", m.rooms[-1]): m.goal}
    cur, fps, ttl = ("RT01", m.rooms[start_room]), [], 40
    while ttl:
        if local.get(cur) == dest:
            return "arrived", fps
        k = routes.get((cur[0], cur[1], dest))
        if k is None:
            return "no-route", fps
        rtr = cur[0]
        tag = (encap01 if rtr == "RT01" else encap02)[k]
        other = "RT02" if rtr == "RT01" else "RT01"
        oenc = encap01 if other == "RT01" else encap02
        k2 = next((kk for kk, t in oenc.items() if t == tag), None)
        if k2 is None:
            return "dead-link", fps
        fps.append(m.ip1(k2) if other == "RT01" else m.ip2(k2))
        cur = (other, (vrf01 if other == "RT01" else vrf02)[k2])
        ttl -= 1
    return "ttl-expired", fps


def selftest():
    bad = 0
    for seed in range(1, 41):
        rnd = random.Random(seed)
        m = Maze(rnd, rnd.randint(3, 5))
        for fault in ["healthy"] + FAULTS:
            fd = pick_fault_detail(random.Random(seed * 100), m, fault) \
                if fault != "healthy" else {"fault": "healthy"}
            fw, ffps = simulate(m, fd, m.goal, 0)
            bw, _ = simulate(m, fd, m.start, -1)
            exp = m.footprints()
            ok = {
                "healthy": fw == "arrived" and bw == "arrived"
                and ffps[:-1] == exp[:-1] and len(ffps) == m.L,
                "fw_gap": fw == "no-route" and len(ffps) < m.L,
                "bw_gap": fw == "arrived" and bw == "no-route",
                "vlan_mismatch": fw == "dead-link" or bw == "dead-link",
                "vrf_cross": fw == "arrived" and len(ffps) < m.L
                and bw == "arrived",
                "loop_static": fw == "ttl-expired",
            }[fault]
            if not ok:
                bad += 1
                print(f"NG seed={seed} n={m.n} fault={fault} fd={fd} "
                      f"fw={fw}({len(ffps)}歩) bw={bw}")
    print("selftest:", "ALL OK (40 seeds x 6 modes)" if not bad else f"{bad} NG")
    return 1 if bad else 0


# --------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--rooms", type=int, choices=[3, 4, 5], default=None)
    ap.add_argument("--fault", choices=FAULTS + ["healthy"], default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    if a.seed is None:
        ap.error("--seed は必須(--selftest 時を除く)")
    rnd = random.Random(a.seed)
    m = Maze(rnd, a.rooms or rnd.randint(3, 5))
    fault = a.fault or rnd.choice(FAULTS)
    fd = pick_fault_detail(rnd, m, fault) if fault != "healthy" \
        else {"fault": "healthy"}
    diff = DIFFICULTY[fault]

    prob_id = f"GEN-VRFMAZE-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"おまけ: VRF迷路 サブIF折り返しチェーン (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["vrf", "static-routing", "dot1q", "maze",
                          "troubleshooting", "generated", "bonus"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": ["RT01", "RT02"], "points": 100, "access": "ssh",
               # ★実機知見(2026-08-05): IPなし物理IF(トランク親)は IOL でも day0
               #   最終パスで強制 shutdown される(IOSv CVAC と同族)。SSH bringup で
               #   親+全サブIFを no shut する(サブIF名は seed 依存なので明示列挙)。
               "bringup_data_ifs": True,
               "bringup_ifs": [PHY] + [m.sub(k) for k in range(1, m.L + 1)],
               "lab": {"links": [{"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0}],
                       "positions": {"RT01": [-200, 0], "RT02": [200, 0]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_vrf_maze.py) seed={a.seed} fault={fault}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/initial/RT01.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt01(m, fd)) + "\n")
    with open(f"{pdir}/initial/RT02.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt02(m, fd)) + "\n")

    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_vrf_maze.py) seed={a.seed}\n"
                "# 足跡採点=traceroute のホップ番号×中継IPで順路まで拘束。\n")
        yaml.safe_dump(build_grading(m, prob_id), f,
                       sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({**fd, "difficulty": diff, "rooms": m.rooms, "turns": m.turns,
                   "vlans": m.vlans, "wrong_vlan": m.wrong_vlan, "x": m.x,
                   "start": m.start, "goal": m.goal, "steps": m.L,
                   "footprints": m.footprints()},
                  f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": build_fix(m, fd)}, f, ensure_ascii=False, indent=2)

    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(build_task(m, prob_id, diff, a.seed))
    print(f"wrote problems/{prob_id} : fault={fault} fd={fd} rooms={m.n} "
          f"steps={m.L} vlans={m.vlans} start={m.start} goal={m.goal}")


if __name__ == "__main__":
    main()
