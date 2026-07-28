#!/usr/bin/env python3
"""VRF-aware EIGRP トラブルシュート生成器（BL-070②・ENARSI-EIGRP-VRF-01 の反転）。

正準トポロジ(実機検証済みの ENARSI-EIGRP-VRF-01 を値ランダム化):
  RT01(テナントA site1) ─ segA1/30 ─┐
  RT04(テナントA site2) ─ segA2/30 ─┤ RT02(共有集約・被疑・named mode)
  RT03(テナントB site1) ─ segB1/30 ─┘
  両テナントは 172.X の同一プレフィックスを重複使用(VRF分離の実効が前提)。

形式は「収容標準仕様書 突き合わせ型 TS」: 仕様(VRF/rd/IF収容・named mode 単一
インスタンス・テナント毎AS・MD5認証・/23集約・分離)を全文提示し、
昨夜の作業後から顧客申告が届いている、というチケットを1〜2枚出す。

故障カタログ(--fault で指定・既定は seed 抽選。--faults 2 は別レイヤから2つ):
  vrf:     vrf_if_swap(難4) / vrf_missing_on_if(難3)
  eigrp:   wrong_as_b(難3) / missing_network_a2(難3) / af_passive_a1(難3) /
           stub_rt02(難5・隣接UPのまま経路消失)
  auth:    key_string_mismatch(難4) / auth_missing_a1(難3)
  summary: summary_wrong_if(難4・仕様書突き合わせ)

fix.json は fix_generated.yml 互換(match: none・named mode は parents リストで
router eigrp → address-family → af-interface の3段ネスト)。

出力: problems/GEN-EGVRF-<seed>/ {problem.yml, initial/*.cfg.j2, task.md,
      grading.yml, solution/{fault.json, fix.json}}
使い方: gen_eigrp_vrf_ts.py --repo . --seed <int> [--fault <name>] [--faults 1|2]
"""
import argparse
import json
import os
import random

import yaml

LAYERS = {
    "vrf": ["vrf_if_swap", "vrf_missing_on_if"],
    "eigrp": ["wrong_as_b", "missing_network_a2", "af_passive_a1", "stub_rt02"],
    "auth": ["key_string_mismatch", "auth_missing_a1"],
    "summary": ["summary_wrong_if"],
}
FAULTS = [f for fs in LAYERS.values() for f in fs]
DIFFICULTY = {"vrf_if_swap": 4, "vrf_missing_on_if": 3, "wrong_as_b": 3,
              "missing_network_a2": 3, "af_passive_a1": 3, "stub_rt02": 5,
              "key_string_mismatch": 4, "auth_missing_a1": 3, "summary_wrong_if": 4}
IF0, IF1, IF2 = "Ethernet0/0", "Ethernet0/1", "Ethernet0/2"
VRF_A, VRF_B = "TENANT-A", "TENANT-B"


def rand_values(rnd):
    o2 = rnd.randint(16, 31)                      # 172.<o2> (RFC1918 172.16/12 内)
    s1 = rnd.randrange(4, 250, 2)                 # site1 の /24 ペア(偶数=/23 整列)
    pool = [x for x in range(4, 254) if x not in (s1, s1 + 1)]
    s2, b3 = rnd.sample(pool, 2)                  # A-site2 / B固有
    p, q = rnd.randint(0, 254), rnd.randint(0, 252)
    seg = {"a1": f"10.{p}.{q}", "a2": f"10.{p}.{q + 1}", "b1": f"10.{p}.{q + 2}"}
    as_a = rnd.choice([100, 110, 120, 130, 210, 310])
    as_b = rnd.choice([x for x in [200, 220, 230, 240, 320, 410] if x != as_a])
    inst = rnd.choice(["SUZUNET", "CORPNET", "AGGR01", "DCNET"])
    tag = rnd.choice(["A", "EDGE", "CORP", "DC1"])
    kc = f"KC-{tag}"
    key_id = rnd.randint(1, 9)
    key_str = f"Ten{rnd.randint(1000, 9999)}Key"
    return o2, s1, s2, b3, seg, as_a, as_b, inst, kc, key_id, key_str


def pick_faults(rnd, n, forced):
    if forced:
        picks = [forced]
        if n == 2:
            layer_of = {f: L for L, fs in LAYERS.items() for f in fs}
            others = [f for f in FAULTS if layer_of[f] != layer_of[forced]]
            picks.append(rnd.choice(others))
        return picks
    layers = rnd.sample(list(LAYERS), k=n)
    return [rnd.choice(LAYERS[L]) for L in layers]


def render_rt02(v, faults, wrong_as):
    o2, s1, s2, b3, seg, as_a, as_b, inst, kc, key_id, key_str = v
    sum_net, sum_mask = f"172.{o2}.{s1}.0", "255.255.254.0"
    # IF→VRF 収容(故障で変異)
    vrf_of = {0: VRF_A, 1: VRF_A, 2: VRF_B}
    if "vrf_if_swap" in faults:
        vrf_of[0], vrf_of[2] = VRF_B, VRF_A
    if "vrf_missing_on_if" in faults:
        del vrf_of[2]
    ks = key_str if "key_string_mismatch" not in faults else f"Ten{9999}Bad"
    L = ["! RT02 初期状態 (EIGRP×VRF TS・昨夜の収容作業直後の状態)",
         f"key chain {kc}", f" key {key_id}", f"  key-string {ks}", "!",
         f"vrf definition {VRF_A}", f" rd 65000:{as_a}",
         " address-family ipv4", " exit-address-family", "!",
         f"vrf definition {VRF_B}", f" rd 65000:{as_b}",
         " address-family ipv4", " exit-address-family", "!"]
    ips = {0: f"{seg['a1']}.2", 1: f"{seg['a2']}.2", 2: f"{seg['b1']}.2"}
    for slot in (0, 1, 2):
        L.append(f"interface {{{{ links[{slot}] }}}}")
        if slot in vrf_of:
            L.append(f" vrf forwarding {vrf_of[slot]}")
        L += [f" ip address {ips[slot]} 255.255.255.252", " no shutdown", "!"]
    # named mode: AF-A
    L.append(f"router eigrp {inst}")
    L.append(f" address-family ipv4 unicast vrf {VRF_A} autonomous-system {as_a}")
    L.append(f"  af-interface {IF0}")
    if "auth_missing_a1" not in faults:
        L += ["   authentication mode md5", f"   authentication key-chain {kc}"]
    if "af_passive_a1" in faults:
        L.append("   passive-interface")
    if "summary_wrong_if" in faults:
        L.append(f"   summary-address {sum_net} {sum_mask}")
    L.append("  exit-af-interface")
    L.append(f"  af-interface {IF1}")
    L += ["   authentication mode md5", f"   authentication key-chain {kc}"]
    if "summary_wrong_if" not in faults:
        L.append(f"   summary-address {sum_net} {sum_mask}")
    L.append("  exit-af-interface")
    L.append(f"  network {seg['a1']}.0 0.0.0.3")
    if "missing_network_a2" not in faults:
        L.append(f"  network {seg['a2']}.0 0.0.0.3")
    if "stub_rt02" in faults:
        L.append("  eigrp stub connected")
    L.append(" exit-address-family")
    # AF-B
    eff_as_b = wrong_as if "wrong_as_b" in faults else as_b
    L.append(f" address-family ipv4 unicast vrf {VRF_B} autonomous-system {eff_as_b}")
    L.append(f"  network {seg['b1']}.0 0.0.0.3")
    L += [" exit-address-family", "!"]
    return L


def render_ce(node, v):
    o2, s1, s2, b3, seg, as_a, as_b, inst, kc, key_id, key_str = v
    if node == "RT01":
        los = [(1, f"172.{o2}.{s1}.1"), (2, f"172.{o2}.{s1 + 1}.1")]
        my_seg, as_n, auth = seg["a1"], as_a, True
        nets = [f"172.{o2}.{s1}.0", f"172.{o2}.{s1 + 1}.0"]
        role = "テナントA site1"
    elif node == "RT04":
        los = [(1, f"172.{o2}.{s2}.1")]
        my_seg, as_n, auth = seg["a2"], as_a, True
        nets = [f"172.{o2}.{s2}.0"]
        role = "テナントA site2"
    else:                                          # RT03
        los = [(1, f"172.{o2}.{s1}.1"), (2, f"172.{o2}.{s1 + 1}.1"),
               (3, f"172.{o2}.{b3}.1")]
        my_seg, as_n, auth = seg["b1"], as_b, False
        nets = [f"172.{o2}.{s1}.0", f"172.{o2}.{s1 + 1}.0", f"172.{o2}.{b3}.0"]
        role = "テナントB site1(★Aと重複プレフィックス)"
    L = [f"! {node} 初期状態 ({role} CE・設定済/変更禁止)"]
    if auth:
        L += [f"key chain {kc}", f" key {key_id}", f"  key-string {key_str}", "!"]
    for n, ip in los:
        L += [f"interface Loopback{n}", f" ip address {ip} 255.255.255.0", "!"]
    L += ["interface {{ links[0] }}", f" ip address {my_seg}.1 255.255.255.252"]
    if auth:
        L += [f" ip authentication mode eigrp {as_n} md5",
              f" ip authentication key-chain eigrp {as_n} {kc}"]
    L += [" no shutdown", "!", f"router eigrp {as_n}",
          f" network {my_seg}.0 0.0.0.3"]
    L += [f" network {net} 0.0.0.255" for net in nets]
    L += [" no auto-summary", "!"]
    return L


def build_fix(v, faults, wrong_as):
    o2, s1, s2, b3, seg, as_a, as_b, inst, kc, key_id, key_str = v
    sum_net, sum_mask = f"172.{o2}.{s1}.0", "255.255.254.0"
    af_a = f"address-family ipv4 unicast vrf {VRF_A} autonomous-system {as_a}"
    af_b = f"address-family ipv4 unicast vrf {VRF_B} autonomous-system {as_b}"
    N = {"match": "none"}
    fixes = []
    if "vrf_if_swap" in faults:
        # ★実機知見(2026-07-27): af-interface <IF> は IF が当該AFのVRF非所属だと
        #   day0 で丸ごと破棄される → 収容復旧後に E0/0 の認証ブロック再投入が必須
        fixes += [{"node": "RT02", "parents": f"interface {IF0}",
                   "lines": [f"vrf forwarding {VRF_A}",
                             f"ip address {seg['a1']}.2 255.255.255.252"], **N},
                  {"node": "RT02", "parents": f"interface {IF2}",
                   "lines": [f"vrf forwarding {VRF_B}",
                             f"ip address {seg['b1']}.2 255.255.255.252"], **N},
                  {"node": "RT02",
                   "parents": [f"router eigrp {inst}", af_a, f"af-interface {IF0}"],
                   "lines": ["authentication mode md5",
                             f"authentication key-chain {kc}"], **N}]
    if "vrf_missing_on_if" in faults:
        fixes.append({"node": "RT02", "parents": f"interface {IF2}",
                      "lines": [f"vrf forwarding {VRF_B}",
                                f"ip address {seg['b1']}.2 255.255.255.252"], **N})
    if "wrong_as_b" in faults:
        fixes += [{"node": "RT02", "parents": f"router eigrp {inst}",
                   "lines": [f"no address-family ipv4 unicast vrf {VRF_B} "
                             f"autonomous-system {wrong_as}"], **N},
                  {"node": "RT02", "parents": [f"router eigrp {inst}", af_b],
                   "lines": [f"network {seg['b1']}.0 0.0.0.3"], **N}]
    if "missing_network_a2" in faults:
        fixes.append({"node": "RT02", "parents": [f"router eigrp {inst}", af_a],
                      "lines": [f"network {seg['a2']}.0 0.0.0.3"], **N})
    if "af_passive_a1" in faults:
        fixes.append({"node": "RT02",
                      "parents": [f"router eigrp {inst}", af_a, f"af-interface {IF0}"],
                      "lines": ["no passive-interface"], **N})
    if "stub_rt02" in faults:
        fixes.append({"node": "RT02", "parents": [f"router eigrp {inst}", af_a],
                      "lines": ["no eigrp stub"], **N})
    if "key_string_mismatch" in faults:
        fixes.append({"node": "RT02", "parents": [f"key chain {kc}", f"key {key_id}"],
                      "lines": [f"key-string {key_str}"], **N})
    if "auth_missing_a1" in faults:
        fixes.append({"node": "RT02",
                      "parents": [f"router eigrp {inst}", af_a, f"af-interface {IF0}"],
                      "lines": ["authentication mode md5",
                                f"authentication key-chain {kc}"], **N})
    if "summary_wrong_if" in faults:
        fixes += [{"node": "RT02",
                   "parents": [f"router eigrp {inst}", af_a, f"af-interface {IF0}"],
                   "lines": [f"no summary-address {sum_net} {sum_mask}"], **N},
                  {"node": "RT02",
                   "parents": [f"router eigrp {inst}", af_a, f"af-interface {IF1}"],
                   "lines": [f"summary-address {sum_net} {sum_mask}"], **N}]
    return fixes


SYMPTOM = {
    "vrf_if_swap":
        "テナントA site1 とテナントB の両顧客から同時に「不通」の申告。"
        "テナントA site2 だけは正常に開通している。",
    "vrf_missing_on_if":
        "テナントBから「開通予定日を過ぎても不通」の申告。テナントAは両サイト正常。",
    "wrong_as_b":
        "テナントBの隣接がどうしても確立しない。IF収容とアドレスは監査済みで"
        "相違なし、との引き継ぎメモがある。",
    "missing_network_a2":
        "テナントA site2 のみ不通。site1 とテナントBは正常。",
    "af_passive_a1":
        "テナントA site1 のみ不通。site2 とテナントBは正常。",
    "stub_rt02":
        "テナントAの両CEで**隣接は UP しているのに**、site1⇄site2 の相互の経路"
        "だけが載らない、と顧客から申告。",
    "key_string_mismatch":
        "テナントAの両サイトが不通。前任者は「認証は収容標準どおり設定した」と"
        "主張している。",
    "auth_missing_a1":
        "テナントA site1 のみ不通。site2 は正常(「同じテナントなのになぜ」と顧客)。",
    "summary_wrong_if":
        "テナントA site2 のルータに、収容標準で禁止されている**明細経路**が見えて"
        "いる。逆に site1 側 CE には不要な集約経路が広告されている。",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    ap.add_argument("--faults", type=int, choices=[1, 2], default=1)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    v = rand_values(rnd)
    o2, s1, s2, b3, seg, as_a, as_b, inst, kc, key_id, key_str = v
    faults = pick_faults(rnd, a.faults, a.fault)
    wrong_as = as_b + 50
    diff = min(max(DIFFICULTY[f] for f in faults) + (1 if len(faults) == 2 else 0), 5)

    prob_id = f"GEN-EGVRF-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"VRF-aware EIGRP 収容標準 適合トラブルシュート (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["eigrp", "vrf", "named-mode", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": ["RT01", "RT02", "RT03", "RT04"],
               "points": 100, "access": "ssh",
               "lab": {"links": [
                   {"a": "RT02", "a_if": 0, "b": "RT01", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "RT04", "b_if": 0},
                   {"a": "RT02", "a_if": 2, "b": "RT03", "b_if": 0}],
                   "positions": {"RT01": [-300, -120], "RT04": [-300, 120],
                                 "RT02": [0, 0], "RT03": [300, 0]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_eigrp_vrf_ts.py) seed={a.seed} faults={','.join(faults)}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/initial/RT02.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt02(v, faults, wrong_as)) + "\n")
    for n in ["RT01", "RT03", "RT04"]:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_ce(n, v)) + "\n")

    # ---- 採点 (ENARSI-EIGRP-VRF-01 の実機検証済みチェック構成を値パラメタ化) ----
    net_s1 = f"172\\.{o2}\\.{s1}\\.0"
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"},
               "checks": [
                   {"name": f"RT02: VRF {VRF_A} (rd 65000:{as_a}) に Et0/0, Et0/1 を収容",
                    "node": "RT02", "command": f"show vrf detail {VRF_A}",
                    "raw": [{"regex": f"RD 65000:{as_a}"},
                            {"regex": "Et0/0"}, {"regex": "Et0/1"}], "points": 10},
                   {"name": f"RT02: VRF {VRF_B} (rd 65000:{as_b}) に Et0/2 を収容",
                    "node": "RT02", "command": f"show vrf detail {VRF_B}",
                    "raw": [{"regex": f"RD 65000:{as_b}"}, {"regex": "Et0/2"},
                            {"not_regex": "Et0/[01]\\b"}], "points": 10},
                   {"name": f"RT02: named mode {inst} / AS{as_a} でテナントA隣接2本",
                    "node": "RT02", "command": f"show ip eigrp vrf {VRF_A} neighbors",
                    "raw": [{"regex": f"VR\\({inst}\\)"}, {"regex": f"AS\\({as_a}\\)"},
                            {"regex": seg["a1"].replace(".", r"\.") + r"\.1"},
                            {"regex": seg["a2"].replace(".", r"\.") + r"\.1"}],
                    "points": 10},
                   {"name": f"RT02: named mode {inst} / AS{as_b} でテナントB隣接",
                    "node": "RT02", "command": f"show ip eigrp vrf {VRF_B} neighbors",
                    "raw": [{"regex": f"VR\\({inst}\\)"}, {"regex": f"AS\\({as_b}\\)"},
                            {"regex": seg["b1"].replace(".", r"\.") + r"\.1"}],
                    "points": 10},
                   {"name": f"RT02: テナントA CE向けIFで MD5 認証 (key-chain {kc}) が有効",
                    "node": "RT02",
                    "command": f"show ip eigrp vrf {VRF_A} interfaces detail",
                    "raw": [{"regex": "md5"}, {"regex": kc}], "points": 10},
                   {"name": f"RT02: VRF {VRF_A} の 172.{o2}.{s1}.0/24 は RT01 から学習",
                    "node": "RT02",
                    "command": f"show ip route vrf {VRF_A} 172.{o2}.{s1}.0 255.255.255.0",
                    "raw": [{"regex": f"Routing entry for {net_s1}/24"},
                            {"regex": r"\* " + seg["a1"].replace(".", r"\.") + r"\.1"}],
                    "points": 10},
                   {"name": f"RT02: VRF {VRF_B} の 172.{o2}.{s1}.0/24 は RT03 から学習 (重複共存)",
                    "node": "RT02",
                    "command": f"show ip route vrf {VRF_B} 172.{o2}.{s1}.0 255.255.255.0",
                    "raw": [{"regex": f"Routing entry for {net_s1}/24"},
                            {"regex": r"\* " + seg["b1"].replace(".", r"\.") + r"\.1"}],
                    "points": 10},
                   {"name": "RT04: /23 集約のみ学習 (明細/24 なし・テナントB経路なし)",
                    "node": "RT04", "command": "show ip route eigrp",
                    "raw": [{"regex": f"D\\s+{net_s1}/23"},
                            {"not_regex": f"172\\.{o2}\\.{s1}\\.0/24"},
                            {"not_regex": f"172\\.{o2}\\.{s1 + 1}\\.0/24"},
                            {"not_regex": f"172\\.{o2}\\.{b3}\\.0"}], "points": 10},
                   {"name": f"RT01: site2 経路 (172.{o2}.{s2}.0/24) を学習・テナントB経路なし",
                    "node": "RT01", "command": "show ip route eigrp",
                    "raw": [{"regex": f"172\\.{o2}\\.{s2}\\.0"},
                            {"not_regex": f"172\\.{o2}\\.{b3}\\.0"}], "points": 5},
                   {"name": f"RT04: site1 (172.{o2}.{s1}.1) へ Lo 発着で疎通",
                    "node": "RT04",
                    "command": f"ping 172.{o2}.{s1}.1 source 172.{o2}.{s2}.1 repeat 5",
                    "raw": [{"regex": "Success rate is [1-9]"}], "points": 10},
                   {"name": f"RT02: VRF {VRF_B} から 172.{o2}.{b3}.1 へ疎通",
                    "node": "RT02",
                    "command": f"ping vrf {VRF_B} 172.{o2}.{b3}.1 repeat 5",
                    "raw": [{"regex": "Success rate is [1-9]"}], "points": 5}]}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_eigrp_vrf_ts.py) seed={a.seed} faults={','.join(faults)}\n"
                "# VRF×重複アドレスのため netmodel 不使用。負の要件は正の要件と複合。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"faults": faults, "instance": inst, "as_a": as_a, "as_b": as_b,
                   "wrong_as": wrong_as, "keychain": kc, "key_id": key_id,
                   "key_str": key_str, "o2": o2, "s1": s1, "s2": s2, "b3": b3,
                   "seg": seg, "difficulty": diff}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": build_fix(v, faults, wrong_as)},
                  f, ensure_ascii=False, indent=2)

    # ---- task.md(仕様書突き合わせ型・故障非公開) ----
    tickets = "\n".join(f"> {i + 1}. {SYMPTOM[f]}" for i, f in enumerate(faults)) \
        if len(faults) > 1 else f"> {SYMPTOM[faults[0]]}"
    task = f"""# 問題 {prob_id} : VRF-aware EIGRP 収容標準 適合トラブルシュート（難易度{diff}）

## 状況

共有集約ルータ **RT02** に、昨夜 前任者が 2テナントの EIGRP 収容作業を実施した。
今朝から下記のトラブルチケットが届いている。社内の**マルチテナント収容標準
（抜粋・下記）に完全準拠**するよう調査・是正せよ。

```
RT01 (テナントA site1) ──{seg['a1']}.0/30──┐e0/0
  Lo1 172.{o2}.{s1}.1/24  Lo2 172.{o2}.{s1 + 1}.1/24 │
                                        RT02 (共有集約・被疑)
RT04 (テナントA site2) ──{seg['a2']}.0/30──┤e0/1
  Lo1 172.{o2}.{s2}.1/24                    │
                                            │e0/2
RT03 (テナントB site1) ──{seg['b1']}.0/30──┘
  Lo1 172.{o2}.{s1}.1/24  Lo2 172.{o2}.{s1 + 1}.1/24  Lo3 172.{o2}.{b3}.1/24
  (★Lo1/Lo2 はテナントAと意図的に重複)
```

## トラブルチケット

{tickets}

## マルチテナント収容標準（抜粋）

1. **VRF**: `{VRF_A}` (rd **65000:{as_a}**) = `Ethernet0/0`, `Ethernet0/1` /
   `{VRF_B}` (rd **65000:{as_b}**) = `Ethernet0/2`。リンクアドレスは現行計画を維持。
2. **EIGRP**: named mode の単一仮想インスタンス **`{inst}`** に両テナントの
   アドレスファミリを収容。テナントA = **AS {as_a}** / テナントB = **AS {as_b}**。
3. **認証**: テナントA の CE 向け IF は **MD5**
   (key chain **`{kc}`** / key **{key_id}** / key-string **`{key_str}`**)。
4. **集約**: テナントA site2 (RT04) へは site1 の 2 つの /24 を
   **`172.{o2}.{s1}.0/23` に集約して広告**。site2 に明細 /24 を見せない。
5. **分離**: テナント間で経路が混ざらないこと。

## 遵守事項

- 設定変更は **RT02 のみ**。CE 3台(RT01/RT03/RT04)は変更禁止（show・ping は可）。
- 収容の**撤去・作り直しによる「復旧」は不可**（収容標準の名前・値に一致させる）。
- 静的ルート・再配送は使用しない。

## 切り分けの観点

- 原因の種類・場所・数は伏せている。収容標準と実機状態を突き合わせること。
- チケットは各顧客の**申告時点の記述**であり、相互に矛盾して見える場合は
  複数原因が重なっているサインと考えること。
- 採点は設定の字面に加え、**経路・疎通の実効**まで見る。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : faults={','.join(faults)} diff={diff} "
          f"inst={inst} asA={as_a} asB={as_b} o2={o2} s1={s1} s2={s2} b3={b3} "
          f"kc={kc}/{key_id}/{key_str}")


if __name__ == "__main__":
    main()
