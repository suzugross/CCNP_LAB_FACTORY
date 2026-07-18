#!/usr/bin/env python3
"""多点相互再配送×seed metric 定常ループ生成器（Ping-t #26308 ファミリ・BL-058）。

正準トポロジ(6台・PDF #26308 忠実・値を seed ランダム化):
  OSPF area0          EIGRP AS               RIPv2
     RB ──── segE11 ────┐
  segO1│                │
     RA                 RD ── segE31 ── RE ── segE41 ── RF ── Lo0 <victim>.6/24
  segO2│                │                                     (rip network)
     RC ──── segE12 ────┘
  RB/RC = OSPF⇄EIGRP の2点相互再配送(タグ/フィルタ無し=故障状態)。
  RF = RIP→EIGRP 片方向再配送。seed metric は全て 1000000 1 255 1 1500。

ループの核心(PoC 済 poc/redist-mp-loop/):
  RIP 発 <victim>/24 が EIGRP→OSPF→EIGRP と一周して再注入され、**AD 無操作のまま**
  同 AD(D EX 170)同士の seed metric 差(再注入点の方が RD に1ホップ近い)で RD が誤選択
  → 4台(RA/RB/RC/RD)の定常転送ループ。2境界が「E→O 起点 / O→E 再注入源」に役割分担
  して固定されるため振動しない(非対称平衡・鏡像の向きは収束レースで非保証)。

解法モード(--solution, 既定 seed ランダム)= 監査ポリシーで解法を1つに強制:
  acl      : 番号標準ACL + distribute-list <n> out ospf <pid> (PDF 正解・再配送点 out)
  prefix   : prefix-list + distribute-list prefix <name> out ospf <pid>
  routemap : 経路タグ(E→O 再配送で set tag / O→E 再配送 route-map で match tag deny)
  distance : AD 調整(境界の distance ospf external >170 等)で戻り O E2 の優先を崩す
  ※初期 config は全モード共通(故障は1種)。task.md の監査ポリシーと grading の
    「指紋 raw + 他解法禁止 not_regex」だけが変わる。

採点: netmodel 大域不変条件 reachability_all(25)/loop_free(25)/optimal(10, RB/RC→RF
  除外=フィルタ系解法では片境界の O E2 遠回りが正常残留するため)
  ＋checks: RD が正規経路(RE 方向)(10)/RA の O E2 維持=再配送設計保存(5)/
  RB・RC の解法指紋+他解法禁止(各10)/RD 静的経路なし(5)。
実機指紋(PoC/probe 済): "Redistributed ospf <pid> filtered by <n>" /
  "filtered by (prefix-list) <name>" / RA "Tag <t>, type extern 2" /
  "Distance: ... external <ad>"。distance は clear 不要(16秒自然収束・実測)。

出力: problems/GEN-REDISTMP-<seed>/ {problem.yml, params/base.yml, initial/*.cfg.j2,
      grading.yml.j2, task.md.j2, solution.md, solution.json}
      既存 build_topology/lab_up/grade/solve_generated パイプライン互換。
使い方: gen_redist_mp_ts.py --repo . --seed <int> [--solution acl|prefix|routemap|distance]
"""
import argparse
import json
import os
import random
import re

import yaml

NODES = ["RA", "RB", "RC", "RD", "RE", "RF"]
HOST = {"RA": 1, "RB": 2, "RC": 3, "RD": 4, "RE": 5, "RF": 6}   # 各セグメントのホスト部
SEED_METRIC = "1000000 1 255 1 1500"
PFX_NAME = "PL-NO-FEEDBACK"

MODES = ["acl", "prefix", "routemap", "distance"]
DIFFICULTY = {"acl": 4, "prefix": 4, "routemap": 5, "distance": 5}


# ---------------------------------------------------------------- 値ランダム化
def rand_values(rnd):
    """seed から一意な値集合を作る(構造は固定・値だけ変える)。"""
    segs = rnd.sample(range(1, 200), 6)               # 172.16.X の第3オクテット×6(重複なし)
    p = {
        "pid": rnd.randint(1, 99),                    # OSPF process-id
        "asn": rnd.randint(1, 99),                    # EIGRP AS
        "acl_no": rnd.randint(1, 99),                 # acl モードの標準ACL番号
        "tag": rnd.randint(100, 999),                 # routemap モードの出自タグ
        "p_net": f"192.168.{rnd.randint(1, 254)}",    # 被害プレフィクス(RIP 発)
        "seg_o1": f"172.16.{segs[0]}",                # RA-RB (OSPF)
        "seg_o2": f"172.16.{segs[1]}",                # RA-RC (OSPF)
        "seg_e11": f"172.16.{segs[2]}",               # RB-RD (EIGRP)
        "seg_e12": f"172.16.{segs[3]}",               # RC-RD (EIGRP)
        "seg_e31": f"172.16.{segs[4]}",               # RD-RE (EIGRP)
        "seg_e41": f"172.16.{segs[5]}",               # RE-RF (EIGRP)
    }
    used, lo = set(), {}
    for r in ["RA", "RB", "RC", "RD", "RE"]:          # RF の代表アドレスは被害 Lo0(.6)
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    p.update({f"{r.lower()}_lo": lo[r] for r in lo})
    return p


# ---------------------------------------------------------------- 初期 config
def render_node(node):
    """initial/<node>.cfg.j2 の行リスト({{ params.* }} と {{ links[n] }} は build 時描画)。
    故障=RB/RC の相互再配送にタグ/フィルタが無い(PDF #26308 の初期状態)。全モード共通。"""
    h = HOST[node]
    if node == "RA":
        return [
            "! GEN-REDISTMP 初期 RA : OSPF area0 内部(両境界へのハブ)",
            "interface Loopback0",
            " ip address {{ params.ra_lo }} 255.255.255.255", "!",
            "interface {{ links[0] }}",
            f" ip address {{{{ params.seg_o1 }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "interface {{ links[1] }}",
            f" ip address {{{{ params.seg_o2 }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "router ospf {{ params.pid }}",
            " router-id {{ params.ra_lo }}",
            " network {{ params.ra_lo }} 0.0.0.0 area 0",
            " network {{ params.seg_o1 }}.0 0.0.0.255 area 0",
            " network {{ params.seg_o2 }}.0 0.0.0.255 area 0", "!"]
    if node in ("RB", "RC"):
        seg_o = "seg_o1" if node == "RB" else "seg_o2"
        seg_e = "seg_e11" if node == "RB" else "seg_e12"
        lo = f"{node.lower()}_lo"
        return [
            f"! GEN-REDISTMP 初期 {node} : OSPF⇄EIGRP 境界(相互再配送・タグ/フィルタ無し=故障)",
            "interface Loopback0",
            f" ip address {{{{ params.{lo} }}}} 255.255.255.255", "!",
            "interface {{ links[0] }}",
            f" ip address {{{{ params.{seg_o} }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "interface {{ links[1] }}",
            f" ip address {{{{ params.{seg_e} }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "router eigrp {{ params.asn }}",
            f" network {{{{ params.{seg_e} }}}}.0 0.0.0.255",
            f" redistribute ospf {{{{ params.pid }}}} metric {SEED_METRIC}", "!",
            "router ospf {{ params.pid }}",
            f" router-id {{{{ params.{lo} }}}}",
            " redistribute eigrp {{ params.asn }} subnets",
            f" network {{{{ params.{lo} }}}} 0.0.0.0 area 0",
            f" network {{{{ params.{seg_o} }}}}.0 0.0.0.255 area 0", "!"]
    if node == "RD":
        return [
            "! GEN-REDISTMP 初期 RD : EIGRP 内部(両境界と RE に接続=誤選択の現場)",
            "interface Loopback0",
            " ip address {{ params.rd_lo }} 255.255.255.255", "!",
            "interface {{ links[0] }}",
            f" ip address {{{{ params.seg_e11 }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "interface {{ links[1] }}",
            f" ip address {{{{ params.seg_e12 }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "interface {{ links[2] }}",
            f" ip address {{{{ params.seg_e31 }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "router eigrp {{ params.asn }}",
            " network {{ params.rd_lo }} 0.0.0.0",
            " network {{ params.seg_e11 }}.0 0.0.0.255",
            " network {{ params.seg_e12 }}.0 0.0.0.255",
            " network {{ params.seg_e31 }}.0 0.0.0.255", "!"]
    if node == "RE":
        return [
            "! GEN-REDISTMP 初期 RE : EIGRP 内部(RF への正規経路の中継)",
            "interface Loopback0",
            " ip address {{ params.re_lo }} 255.255.255.255", "!",
            "interface {{ links[0] }}",
            f" ip address {{{{ params.seg_e31 }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "interface {{ links[1] }}",
            f" ip address {{{{ params.seg_e41 }}}}.{h} 255.255.255.0", " no shutdown", "!",
            "router eigrp {{ params.asn }}",
            " network {{ params.re_lo }} 0.0.0.0",
            " network {{ params.seg_e31 }}.0 0.0.0.255",
            " network {{ params.seg_e41 }}.0 0.0.0.255", "!"]
    # RF : RIPv2 起点(被害プレフィクスの真の出自)
    return [
        "! GEN-REDISTMP 初期 RF : RIPv2 サイト(被害プレフィクスの起点)＋RIP→EIGRP 再配送",
        "interface Loopback0",
        "! 顧客 LAN の模擬(RIPv2 ドメイン)",
        f" ip address {{{{ params.p_net }}}}.{h} 255.255.255.0", "!",
        "interface {{ links[0] }}",
        f" ip address {{{{ params.seg_e41 }}}}.{h} 255.255.255.0", " no shutdown", "!",
        "router eigrp {{ params.asn }}",
        " network {{ params.seg_e41 }}.0 0.0.0.255",
        f" redistribute rip metric {SEED_METRIC}", "!",
        "router rip",
        " version 2",
        " no auto-summary",
        " network {{ params.p_net }}.0", "!"]


# ---------------------------------------------------------------- 採点
def build_model(p):
    """netmodel 用モデル(値は baked)。RF の代表アドレス=被害 Lo0。"""
    def ip(seg, node):
        return f"{p[seg]}.{HOST[node]}"
    return {
        "loopbacks": {"RA": p["ra_lo"], "RB": p["rb_lo"], "RC": p["rc_lo"],
                      "RD": p["rd_lo"], "RE": p["re_lo"], "RF": f"{p['p_net']}.6"},
        "links": [
            {"a": "RA", "a_ip": ip("seg_o1", "RA"), "b": "RB", "b_ip": ip("seg_o1", "RB")},
            {"a": "RA", "a_ip": ip("seg_o2", "RA"), "b": "RC", "b_ip": ip("seg_o2", "RC")},
            {"a": "RB", "a_ip": ip("seg_e11", "RB"), "b": "RD", "b_ip": ip("seg_e11", "RD")},
            {"a": "RC", "a_ip": ip("seg_e12", "RC"), "b": "RD", "b_ip": ip("seg_e12", "RD")},
            {"a": "RD", "a_ip": ip("seg_e31", "RD"), "b": "RE", "b_ip": ip("seg_e31", "RE")},
            {"a": "RE", "a_ip": ip("seg_e41", "RE"), "b": "RF", "b_ip": ip("seg_e41", "RF")}]}


# 全モード共通の「解法指紋+他解法禁止」用 include コマンド(1コマンドで全対象語を拾う)
INCLUDE_CMD = ("show running-config | include "
               "redistribute |distribute-list|distance |route-map|prefix-list"
               "|^ip route |set tag|match tag")


def mode_checks(mode, p):
    """RB/RC の解法指紋チェック(正の指紋 AND 他解法禁止の複合)。"""
    pid, asn = p["pid"], p["asn"]
    ban_static = {"not_regex": r"(?m)^ip route "}
    if mode == "acl":
        raw = [{"regex": rf"distribute-list {p['acl_no']} out ospf {pid}\b"},
               {"not_regex": "route-map"}, {"not_regex": "prefix-list"},
               {"not_regex": r"(?m)^\s*distance "}, ban_static]
        name = (f"番号ACL {p['acl_no']} の distribute-list out ospf {pid} で実装"
                "(route-map/prefix-list/distance/静的は監査ポリシー違反)")
    elif mode == "prefix":
        raw = [{"regex": rf"distribute-list prefix \S+ out ospf {pid}\b"},
               {"not_regex": r"(?m)^\s*distribute-list \d"}, {"not_regex": "route-map"},
               {"not_regex": r"(?m)^\s*distance "}, ban_static]
        name = (f"prefix-list の distribute-list out ospf {pid} で実装"
                "(番号ACL直指定/route-map/distance/静的は監査ポリシー違反)")
    elif mode == "routemap":
        # ★iol-xe 17.15 は OSPF の redistribute で subnets が暗黙定＝running-config に
        #   表示されない(BL-019 と同種)。投入は subnets 付きでも表示は無し→両対応。
        raw = [{"regex": rf"redistribute eigrp {asn} (subnets )?route-map \S+"},
               {"regex": rf"redistribute ospf {pid} metric \S+ \S+ \S+ \S+ \S+ route-map \S+"},
               {"regex": rf"set tag {p['tag']}\b"},
               {"regex": rf"match tag {p['tag']}\b"},
               {"not_regex": "distribute-list"}, {"not_regex": "prefix-list"},
               {"not_regex": r"(?m)^\s*distance "}, ban_static]
        name = (f"経路タグ {p['tag']} 方式で実装(E→O 再配送で set tag / O→E 再配送で遮断。"
                "distribute-list/prefix-list/distance/静的は監査ポリシー違反)")
    else:  # distance
        raw = [{"regex": r"(?m)^\s*distance (\d|ospf|eigrp)"},
               {"not_regex": "distribute-list"}, {"not_regex": "route-map"},
               {"not_regex": "prefix-list"}, ban_static]
        name = ("管理距離(AD)の調整のみで実装"
                "(distribute-list/route-map/prefix-list/静的は変更凍結中=監査ポリシー違反)")
    return raw, name


def build_grading(prob_id, mode, p):
    """grading dict(YAML 化して .j2 として書く。baked 値のみ=描画は素通し)。"""
    victim = f"{p['p_net']}.0"
    opt_pairs = [[r, t] for r in NODES for t in NODES
                 if r != t and not (t == "RF" and r in ("RB", "RC"))]
    ra_raw = [{"regex": 'Known via "ospf'}, {"regex": "extern 2"}]
    if mode == "routemap":
        ra_raw.append({"regex": rf"Tag {p['tag']}, type extern 2"})
    checks = [
        {"name": f"RD: {victim}/24 を正規経路(RE 方向 {p['seg_e31']}.5)で学習(再注入経路の排除)",
         "node": "RD", "command": f"show ip route {victim}",
         # 詳細ビュー(show ip route <pfx>)の next-hop 行は「* <ip>, from <ip>, ... via <IF名>」
         # 形式(via の後は IF 名)。IP の存在で判定する(選択経路のブロックしか表示されない)。
         "raw": [{"regex": 'Known via "eigrp'},
                 {"regex": rf"\* {re.escape(p['seg_e31'])}\.5,"}],
         "points": 10},
        {"name": f"RA: {victim}/24 を O E2 で学習(EIGRP→OSPF 再配送設計の維持"
                 + ("＋出自タグ付与" if mode == "routemap" else "") + ")",
         "node": "RA", "command": f"show ip route {victim}",
         "raw": ra_raw, "points": 5},
    ]
    for node in ("RB", "RC"):
        raw, name = mode_checks(mode, p)
        checks.append({"name": f"{node}: {name}", "node": node,
                       "command": INCLUDE_CMD, "raw": raw, "points": 10})
    checks.append({"name": "RD: 静的経路による回避なし", "node": "RD",
                   "command": "show running-config | include ^ip route ",
                   "raw": [{"not_regex": r"(?m)^ip route "}], "points": 5})
    assert sum(c["points"] for c in checks) + 25 + 25 + 10 == 100
    return {
        "problem": prob_id,
        "total_points": 100,
        "defaults": {"genie_os": "iosxe"},
        "model": build_model(p),
        "invariants": [
            {"type": "reachability_all", "points": 25,
             "name": f"全ルータ間到達性({victim}/24 を含む)"},
            {"type": "loop_free", "points": 25,
             "name": "転送ループ無し(RA/RB/RC/RD の再配送フィードバックループ解消)"},
            {"type": "optimal", "points": 10, "pairs": opt_pairs,
             "name": "最短転送(RB/RC→RF はフィルタ系解法で片側 O E2 遠回りが正常のため除外)"}],
        "checks": checks}


# ---------------------------------------------------------------- 監査ポリシー/解答
def policy_md(mode, p):
    pid, asn = p["pid"], p["asn"]
    if mode == "acl":
        return (f"- 是正は**番号付き標準 ACL** と **`distribute-list <ACL番号> out ospf {pid}`**"
                f"(再配送点でのフィルタ)で実装すること(ACL 番号は **{p['acl_no']}** を使用)。\n"
                "- **prefix-list / route-map の新設、および管理距離(distance)の変更は変更凍結中で使用不可。**\n"
                "- 静的経路・デフォルトルートによる回避は不可。")
    if mode == "prefix":
        return (f"- 是正は **prefix-list** と **`distribute-list prefix <名前> out ospf {pid}`**"
                "(再配送点でのフィルタ)で実装すること(prefix-list 名は任意)。\n"
                "- **番号 ACL の distribute-list、route-map の新設、管理距離(distance)の変更は使用不可。**\n"
                "- 静的経路・デフォルトルートによる回避は不可。")
    if mode == "routemap":
        return (f"- 是正は**経路タグ方式**で実装すること: **EIGRP→OSPF 再配送で出自タグ "
                f"{p['tag']} を付与**し、**OSPF→EIGRP 再配送でタグ {p['tag']} の経路を遮断**する"
                "(route-map を再配送コマンドに適用)。\n"
                "- **distribute-list / prefix-list / 管理距離(distance)の変更は使用不可**"
                "(プレフィクス直指定でなく「出自マーキング」で解くこと)。\n"
                "- 静的経路・デフォルトルートによる回避は不可。")
    return ("- **フィルタ系(ACL / prefix-list / route-map / distribute-list)の新設は変更凍結中で使用不可。**\n"
            "- 是正は**管理距離(administrative distance)の調整のみ**で実装すること。\n"
            "- 静的経路・デフォルトルートによる回避は不可。")


def fix_filters(mode, p):
    """solution.json の filters(RB/RC 両方に同一ブロック)。"""
    pid, asn = p["pid"], p["asn"]
    victim = p["p_net"]
    if mode == "acl":
        blocks = [
            {"parents": None, "lines": [
                f"access-list {p['acl_no']} deny {victim}.0 0.0.0.255",
                f"access-list {p['acl_no']} permit any"]},
            {"parents": f"router eigrp {asn}", "lines": [
                f"distribute-list {p['acl_no']} out ospf {pid}"]}]
    elif mode == "prefix":
        blocks = [
            {"parents": None, "lines": [
                f"ip prefix-list {PFX_NAME} seq 5 deny {victim}.0/24",
                f"ip prefix-list {PFX_NAME} seq 10 permit 0.0.0.0/0 le 32"]},
            {"parents": f"router eigrp {asn}", "lines": [
                f"distribute-list prefix {PFX_NAME} out ospf {pid}"]}]
    elif mode == "routemap":
        blocks = [
            {"parents": "route-map SET-TAG permit 10", "lines": [f"set tag {p['tag']}"]},
            {"parents": "route-map DENY-TAG deny 10", "lines": [f"match tag {p['tag']}"]},
            {"parents": None, "lines": ["route-map DENY-TAG permit 20"]},
            {"parents": f"router ospf {pid}", "lines": [
                f"redistribute eigrp {asn} subnets route-map SET-TAG"]},
            {"parents": f"router eigrp {asn}", "lines": [
                f"redistribute ospf {pid} metric {SEED_METRIC} route-map DENY-TAG"]}]
    else:  # distance
        blocks = [{"parents": f"router ospf {pid}", "lines": ["distance ospf external 180"]}]
    return [{"node": n, "blocks": blocks} for n in ("RB", "RC")]


def task_text(prob_id, mode, p):
    victim = p["p_net"]
    d = DIFFICULTY[mode]
    return f"""# 問題 {prob_id} : 多点相互再配送によるルーティングループ(難易度{d})

## 状況
社内は 3 つのルーティングドメインが数珠つなぎになっている。**RB と RC の 2 台**が
OSPF⇄EIGRP を**相互再配送**し、**RF** が顧客サイトの RIPv2 網 `{victim}.0/24` を
EIGRP へ再配送している(シードメトリックは全再配送で `{SEED_METRIC}`)。

```
   [OSPF area0]        [EIGRP AS{p['asn']}]                          [RIPv2]
        RB ──── {p['seg_e11']}.0/24 ────┐
 {p['seg_o1']}.0/24│                        │
        RA                          RD ── {p['seg_e31']}.0/24 ── RE ── {p['seg_e41']}.0/24 ── RF ═ {victim}.0/24
 {p['seg_o2']}.0/24│                        │
        RC ──── {p['seg_e12']}.0/24 ────┘
```

## トラブルチケット(代表症状)
> OSPF 側(RA など)から顧客網 **`{victim}.0/24` 宛が届かない**。
> `traceroute {victim}.6` すると**同じ 4 台のルータをぐるぐる回って** TTL 超過で落ちる。
> それ以外の宛先(各ルータの Loopback 等)は正常に到達する。

## ルータ / 役割
| ルータ | 役割 | 代表アドレス |
|--------|------|--------------|
| RA | OSPF 内部 | Lo0 `{p['ra_lo']}/32` |
| RB | **OSPF⇄EIGRP 境界(相互再配送)** | Lo0 `{p['rb_lo']}/32` |
| RC | **OSPF⇄EIGRP 境界(相互再配送)** | Lo0 `{p['rc_lo']}/32` |
| RD | EIGRP 内部(両境界と RE に接続) | Lo0 `{p['rd_lo']}/32` |
| RE | EIGRP 内部 | Lo0 `{p['re_lo']}/32` |
| RF | RIPv2 サイト・**RIP→EIGRP 再配送** | Lo0 `{victim}.6/24`(顧客 LAN) |

## 到達目標
1. すべてのルータから **`{victim}.6` へ到達**できること(全 Loopback 相互到達も維持)。
2. **転送ループが無い**こと。
3. 各ドメインの**再配送設計は維持**すること(いずれかの再配送の削除・停止は不可)。

## 制約(変更管理・監査ポリシー)
- プロトコル配置(どのルータ・リンクが OSPF / EIGRP / RIP か)は変更不可。
- **設定変更は RB と RC のみ**。RA / RD / RE / RF は変更禁止。
{policy_md(mode, p)}

## 進め方のヒント(控えめ)
`traceroute {victim}.6` の繰り返しパターンを読み、ループ上の各ルータで
`show ip route {victim}.0` の **Known via(学習元)とメトリック**を 1 台ずつ追え。
RD にはこの宛先の経路情報が**複数**あるはずだ — それぞれが「**どこから来た情報か**」を
突き止めると、止めるべき場所と方向が見える。

## アクセス・採点
SSH `SUZUKI / CCNP`(mgmt は割当順に 10.1.10.x)。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
採点は **効果ベース(到達性・ループ不在・最短転送)＋監査ポリシー適合**。
"""


def solution_md(prob_id, mode, p):
    pid, asn, victim, tag = p["pid"], p["asn"], p["p_net"], p["tag"]
    fixes = {
        "acl": f"""```
access-list {p['acl_no']} deny {victim}.0 0.0.0.255
access-list {p['acl_no']} permit any
!
router eigrp {asn}
 distribute-list {p['acl_no']} out ospf {pid}
```
`out ospf {pid}` は「**OSPF {pid} を源とする再配送**」だけに掛かる out フィルタ。
EIGRP ネイバーへの通常アドバタイズや他の再配送には影響しない(PDF #26308 の正解形)。""",
        "prefix": f"""```
ip prefix-list {PFX_NAME} seq 5 deny {victim}.0/24
ip prefix-list {PFX_NAME} seq 10 permit 0.0.0.0/0 le 32
!
router eigrp {asn}
 distribute-list prefix {PFX_NAME} out ospf {pid}
```
番号 ACL 版と同じ再配送点 out フィルタの prefix-list 形。
`show ip protocols` の指紋は `Redistributed ospf {pid} filtered by (prefix-list) {PFX_NAME}`。""",
        "routemap": f"""```
route-map SET-TAG permit 10
 set tag {tag}
!
route-map DENY-TAG deny 10
 match tag {tag}
route-map DENY-TAG permit 20
!
router ospf {pid}
 redistribute eigrp {asn} subnets route-map SET-TAG
router eigrp {asn}
 redistribute ospf {pid} metric {SEED_METRIC} route-map DENY-TAG
```
**出自マーキング**: EIGRP→OSPF で入った経路すべてにタグ {tag} を焼き、OSPF→EIGRP の
再配送でタグ {tag} を弾く。被害プレフィクスを名指ししないので、**将来 RIP 側に別の
プレフィクスが増えても自動で守られる**(実務のベストプラクティス形)。
`DENY-TAG permit 20`(素通し)を忘れると OSPF 発の正常経路まで全滅する(暗黙 deny)。""",
        "distance": f"""```
router ospf {pid}
 distance ospf external 180
```
境界 2 台で **O E2 の AD を EIGRP 外部(170)より上げる**と、境界は戻り経路(O E2)でなく
EIGRP 外部(正規方向)を選ぶ。RIB が EIGRP になるため `redistribute ospf {pid}` が
被害プレフィクスを拾わなくなり、**再注入そのものが止まる**(火元の消火)。
`distance eigrp 90 100` のように **EIGRP 外部を 110 未満へ下げる**形でも同じ効果(別解)。
★実機では設定後 15〜20 秒で自然収束する(`clear ip route *` は不要・実測)。""",
    }
    return f"""# 模範解答 : {prob_id}(solution={mode})

## なぜ壊れるか(多点相互再配送×seed metric の定常ループ・Ping-t #26308 型)
`{victim}.0/24` は RIP 発。RF が EIGRP へ再配送し(D EX・AD 170)、境界 RB/RC が
EIGRP→OSPF へ再配送(O E2・AD 110)、それが**もう一方の境界で OSPF→EIGRP に再注入**される。

- 境界では **O E2(110) が D EX(170) に勝つ**ため、片方の境界(鏡像はどちらでも)が
  「OSPF 勝ち=再注入源」、他方が「EIGRP 勝ち=Type-5 起点」に**役割分担して固定**される。
- RD から見ると候補は 2 つとも D EX(170) だが、**再注入点の方が 1 ホップ近い**ため
  seed metric 起算の合成メトリックが小さく、RD は誤った方(境界向き)を選ぶ。
- 結果、`RA→(境界)→RD→(逆側境界)→RA` の **4 台定常転送ループ**。AD は一切
  操作していないのに成立するのが本問の核心(教科書的な AD 逆転とは別物)。

### 診断の決定打
- RD `show ip eigrp topology {victim}.0/24` : 候補が 2 つ見え、External data の
  **External protocol が片方 OSPF・片方 RIP**。「EIGRP の外部経路なのに出自が OSPF」
  =どこかで一周して戻ってきた再注入の動かぬ証拠。
- 境界の `show ip route {victim}.0` : 片方が `Known via "ospf {pid}"` で
  `Advertised by eigrp {asn} ...` 表示(=OSPF 勝ち側が EIGRP へ再注入している)。

## 解(RB・RC の**両方**に投入)
{fixes[mode]}

**片側だけ**直すと、逆向きの再注入が残って**鏡像のループが継続**する(2 点相互再配送の
定石: 対策は必ず両境界に対で入れる)。

## 確認
- RD: `show ip route {victim}.0` が `via {p['seg_e31']}.5`(RE 方向)へ復帰。
- RA: `traceroute {victim}.6` が RA→(境界)→RD→RE→RF で完走(巡回しない)。
- フィルタ系解法では、片側境界の `{victim}.0` が O E2(遠回りだが到達可)のまま残るのは
  **正常**(O→E 再注入だけを止めたため。距離調整版では両境界とも EIGRP 直行になる)。

## 教育核心
- **多点(2 点以上)相互再配送**は、出自が一周して戻る**フィードバック経路**を必ず作る。
  防御は①再配送点フィルタ(distribute-list out)②出自タグ③AD 調整④メトリック劣化の
  4 家系 — 本問は監査ポリシーで {mode} 家系を指定して解かせる形。
- `distribute-list <list> out <protocol>` の **out+プロトコル引数**は「再配送の入口で
  絞る」ための構文(ネイバー向け out とは別物)。ENARSI 頻出。
"""


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--solution", choices=MODES, default=None)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    p = rand_values(rnd)
    mode = a.solution or rnd.choice(MODES)

    prob_id = f"GEN-REDISTMP-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/params", exist_ok=True)

    with open(f"{pdir}/params/base.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_mp_ts.py) seed={a.seed} solution={mode}\n")
        yaml.safe_dump(p, f, sort_keys=False, allow_unicode=True)

    problem = {"id": prob_id,
               "title": f"多点相互再配送 定常ループTS solution={mode} (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["redistribution", "ospf", "eigrp", "rip",
                          "distribute-list", "routing-loop", "generated"],
               "difficulty": DIFFICULTY[mode], "topology": "generated",
               "access": "ssh", "target_nodes": NODES, "points": 100,
               "lab": {"links": [
                   {"a": "RA", "a_if": 0, "b": "RB", "b_if": 0},
                   {"a": "RA", "a_if": 1, "b": "RC", "b_if": 0},
                   {"a": "RB", "a_if": 1, "b": "RD", "b_if": 0},
                   {"a": "RC", "a_if": 1, "b": "RD", "b_if": 1},
                   {"a": "RD", "a_if": 2, "b": "RE", "b_if": 0},
                   {"a": "RE", "a_if": 1, "b": "RF", "b_if": 0}],
                   "positions": {"RA": [-760, -160], "RB": [-480, -320],
                                 "RC": [-480, 0], "RD": [-200, -160],
                                 "RE": [80, -160], "RF": [360, -160]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_mp_ts.py) seed={a.seed} solution={mode}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    for n in NODES:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_node(n)) + "\n")

    grading = build_grading(prob_id, mode, p)
    with open(f"{pdir}/grading.yml.j2", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_mp_ts.py) {prob_id} solution={mode}\n"
                f"# 初期: {p['p_net']}.0/24 が RA/RB/RC/RD で定常ループ"
                "(reachability/loop_free/optimal/RD正規経路/指紋 が 0)。\n"
                "# 是正後: RB/RC 両方に指定解法 → 全到達＋ループ消失＋指紋成立。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True,
                       default_flow_style=False, width=120)
    with open(f"{pdir}/task.md.j2", "w", encoding="utf-8") as f:
        f.write(task_text(prob_id, mode, p))
    with open(f"{pdir}/solution.md", "w", encoding="utf-8") as f:
        f.write(solution_md(prob_id, mode, p))

    sol = {"_comment": f"solution={mode}: RB/RC 両方に対で投入(片側のみは鏡像ループ残存)。"
                       "distance 変更も本トポロジでは clear 不要(15-20秒自然収束・実測)。",
           "nodes": {}, "filters": fix_filters(mode, p)}
    with open(f"{pdir}/solution.json", "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=2)

    print(f"wrote problems/{prob_id} : solution={mode} diff={DIFFICULTY[mode]} "
          f"victim={p['p_net']}.0/24 pid={p['pid']} asn={p['asn']}")


if __name__ == "__main__":
    main()
