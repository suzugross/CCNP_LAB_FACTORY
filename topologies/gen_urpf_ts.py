#!/usr/bin/env python3
"""uRPF トラブルシュート生成器（BL-030・ENARSI-URPF-01 の反転）。

正準トポロジ(実機検証済みの ENARSI-URPF-01 を値ランダム化):
  RT01(edge・被疑) -- RT02(E0/0側 ISP) / RT03(E0/1側 ISP) / RT02-RT03(ピアリング・OSPF外)
  非対称の作り: 顧客B プレフィックスは holder(ISP片方)が実体保持(OSPF未広告)、
  広告は advertiser(もう片方)の static + redistribute static subnets のみ
  → RT01 の経路は advertiser 向き・実着信は holder 向き IF。
  ★ピアリングリンクを OSPF に入れると FA が立ち E2 が ECMP 化して非対称が消える
    (実機で確認済みの罠・poc/urpf/README.md ★2)。holder/advertiser は seed でスワップ。

day0 は「昨日 anti-spoofing (uRPF) を導入した直後」の体で故障1種を注入した状態。

故障カタログ(--fault, 既定 seed ランダム):
  strict_on_asym      : 非対称着信side が strict → 顧客B 断（正解は loose）。難4
  acl_exempt_wrong    : 非対称side が strict+ACL例外だが ACL のプレフィックスが誤り
                        → 症状は同じだが config は「対処済みに見える」。難5
  missing_on_uplink   : 片方の uplink に uRPF が無い → 偽装が検証されず素通り。難3
  loose_on_strict_side: 対称side が loose → ポリシー(可能な限り厳格)違反・
                        実在プレフィックス偽装が素通り(suppressed 計上のみ)。難4

採点(ENARSI-URPF-01 で実機確立した構成+効果の9チェックを値差し替えで再利用):
  ★偽装 ping の成否は採点しない(uRPF 無しでも反射経路が無く失敗=偽陽性)。
  ドロップの証拠は per-IF `verification drops` カウンタ。0点「発射」チェック(ping)を
  カウンタ判定より前に置くことで同一試行内に収束する(チェックは記載順実行)。

出力: problems/GEN-URPF-<seed>/ {problem.yml, initial/*.cfg.j2, task.md, grading.yml,
      solution/{fault.json, fix.json}}。fix.json は fix_generated.yml 互換。
使い方: gen_urpf_ts.py --repo . --seed <int> [--fault <name>]
"""
import argparse
import json
import os
import random

import yaml

FAULTS = ["strict_on_asym", "acl_exempt_wrong", "missing_on_uplink", "loose_on_strict_side"]
DIFFICULTY = {"strict_on_asym": 4, "acl_exempt_wrong": 5,
              "missing_on_uplink": 3, "loose_on_strict_side": 4}
IF_OF = {"RT02": "Ethernet0/0", "RT03": "Ethernet0/1"}   # RT01 上の対向IF(配線固定)


def rand_values(rnd):
    """Lo/セグメント/顧客プレフィックス/ACL番号を seed から決める。"""
    lo, used = {}, set()
    for r in ["RT01", "RT02", "RT03"]:
        while True:
            k = rnd.randint(1, 99)
            if k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    seg, useg = {}, set()
    for name in ["12", "13", "23"]:
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) not in useg:
                useg.add((p, q)); seg[name] = f"10.{p}.{q}"; break
    b = rnd.randint(2, 250)
    custB = f"192.168.{b}"                      # 非対称(dual-home)顧客
    custC = f"192.168.{(b + rnd.randint(1, 3)) % 251 + 2}"   # 対称顧客
    spoof = f"203.0.113.{rnd.randint(1, 254)}"  # 完全未広告スプーフ源
    return lo, seg, custB, custC, spoof, rnd.randint(10, 99)


def urpf_lines(fault, node_if, correct_mode, acl_num, custB, custC):
    """RT01 の対向IF(node_if)に焼く uRPF 行(故障注入込み)を返す。"""
    is_asym = correct_mode == "any"
    if fault == "strict_on_asym" and is_asym:
        return [" ip verify unicast source reachable-via rx"]
    if fault == "acl_exempt_wrong" and is_asym:
        # ACL は焼くがプレフィックスが誤り(custC を救済してしまっている)
        return [f" ip verify unicast source reachable-via rx {acl_num}"]
    if fault == "missing_on_uplink" and is_asym:
        return []                                # 非対称側に uRPF 無し
    if fault == "loose_on_strict_side" and not is_asym:
        return [" ip verify unicast source reachable-via any"]
    return [f" ip verify unicast source reachable-via {correct_mode}"]


def render_rt01(lo, seg, fault, roles, acl_num, custB, custC):
    """RT01 初期構成。roles = {'holder': 'RT03', 'advertiser': 'RT02'} 等。"""
    holder = roles["holder"]
    L = [f"! RT01 初期構成 (uRPF TS・昨日 anti-spoofing を導入した直後の状態)",
         "interface Loopback0", f" ip address {lo['RT01']} 255.255.255.255", "!"]
    if fault == "acl_exempt_wrong":
        # 誤り: 非対称顧客(custB)でなく対称顧客(custC)を例外にしている
        L += [f"access-list {acl_num} permit {custC}.0 0.0.0.255", "!"]
    for slot, peer, sg in [(0, "RT02", seg["12"]), (1, "RT03", seg["13"])]:
        correct = "any" if peer == holder else "rx"
        L += [f"interface {{{{ links[{slot}] }}}}",
              f" description === Uplink-{'A' if slot == 0 else 'B'}: to ISP ({peer}) ===",
              f" ip address {sg}.1 255.255.255.252"]
        L += urpf_lines(fault, IF_OF[peer], correct, acl_num, custB, custC)
        L += [" no shutdown", "!"]
    L += ["router ospf 1", " router-id " + lo["RT01"],
          f" network {lo['RT01']} 0.0.0.0 area 0",
          f" network {seg['12']}.0 0.0.0.3 area 0",
          f" network {seg['13']}.0 0.0.0.3 area 0", "!"]
    return L


def render_isp(node, lo, seg, roles, custB, custC, spoof):
    """RT02/RT03 (ISP側・変更禁止) の初期構成。"""
    is_holder = node == roles["holder"]
    my_seg = seg["12"] if node == "RT02" else seg["13"]
    peer_ip23 = f"{seg['23']}.{2 if node == 'RT02' else 1}"   # 相手のピアリングIP
    my_ip23 = f"{seg['23']}.{1 if node == 'RT02' else 2}"
    L = [f"! {node} (ISP設備・変更禁止)",
         "interface Loopback0", f" ip address {lo[node]} 255.255.255.255", "!"]
    if is_holder:
        L += ["interface Loopback1",
              " description === Customer-B LAN (dual-homed) ===",
              f" ip address {custB}.1 255.255.255.0", "!",
              "interface Loopback2",
              " description === ISP NOC test source (do not modify) ===",
              f" ip address {spoof} 255.255.255.255", "!",
              "interface Loopback3",
              " description === Customer-C LAN ===",
              f" ip address {custC}.1 255.255.255.0",
              " ip ospf network point-to-point", "!"]
    else:
        L += ["interface Loopback2",
              " description === ISP NOC test source (do not modify) ===",
              f" ip address {custC}.99 255.255.255.255", "!"]
    L += ["interface {{ links[0] }}",
          " description === to RT01 (customer edge) ===",
          f" ip address {my_seg}.2 255.255.255.252", " no shutdown", "!",
          "interface {{ links[1] }}",
          " description === ISP peering ===",
          f" ip address {my_ip23} 255.255.255.252", " no shutdown", "!"]
    if not is_holder:                            # advertiser: 顧客Bを static 再配布で広告
        L += [f"ip route {custB}.0 255.255.255.0 {peer_ip23}", "!"]
    ospf = ["router ospf 1", f" router-id {lo[node]}",
            f" network {lo[node]} 0.0.0.0 area 0",
            f" network {my_seg}.0 0.0.0.3 area 0"]
    if is_holder:
        ospf.insert(2, f" network {custC}.0 0.0.0.255 area 0")
    else:
        ospf.insert(1, " redistribute static subnets")
    # ★ピアリングリンク(seg23)は意図的に OSPF 外(FA罠回避)
    L += ospf + ["!"]
    return L


def build_fix(fault, roles, acl_num, custB):
    """故障を健全へ是正する fix エントリ列(fix_generated.yml 互換)。"""
    holder, adv = roles["holder"], roles["advertiser"]
    asym_if, strict_if = IF_OF[holder], IF_OF[adv]
    if fault in ("strict_on_asym", "acl_exempt_wrong"):
        # 模範 fix = loose 化(最小)。acl_exempt_wrong は誤ACLの残骸も掃除
        fixes = [{"node": "RT01", "parents": f"interface {asym_if}",
                  "lines": ["ip verify unicast source reachable-via any"]}]
        if fault == "acl_exempt_wrong":
            fixes.append({"node": "RT01", "lines": [f"no access-list {acl_num}"]})
        return fixes
    if fault == "missing_on_uplink":
        return [{"node": "RT01", "parents": f"interface {asym_if}",
                 "lines": ["ip verify unicast source reachable-via any"]}]
    if fault == "loose_on_strict_side":
        return [{"node": "RT01", "parents": f"interface {strict_if}",
                 "lines": ["ip verify unicast source reachable-via rx"]}]
    raise SystemExit(f"unknown fault {fault}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    lo, seg, custB, custC, spoof, acl_num = rand_values(rnd)
    fault = a.fault or rnd.choice(FAULTS)
    holder = rnd.choice(["RT02", "RT03"])        # 非対称顧客の実体を持つ ISP
    roles = {"holder": holder,
             "advertiser": "RT03" if holder == "RT02" else "RT02"}
    adv = roles["advertiser"]
    asym_if, strict_if = IF_OF[holder], IF_OF[adv]
    adv_link_ip = f"{seg['12'] if adv == 'RT02' else seg['13']}.2"

    prob_id = f"GEN-URPF-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"anti-spoofing (uRPF) トラブルシュート (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["urpf", "security", "troubleshooting", "generated"],
               "difficulty": DIFFICULTY[fault], "topology": "generated",
               "target_nodes": ["RT01", "RT02", "RT03"], "points": 100, "access": "ssh",
               "lab": {"links": [
                   {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                   {"a": "RT01", "a_if": 1, "b": "RT03", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "RT03", "b_if": 1}],
                   "positions": {"RT01": [0, -300], "RT02": [-300, 0], "RT03": [300, 0]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_urpf_ts.py) seed={a.seed} fault={fault}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/initial/RT01.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt01(lo, seg, fault, roles, acl_num, custB, custC)) + "\n")
    for n in ["RT02", "RT03"]:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_isp(n, lo, seg, roles, custB, custC, spoof)) + "\n")

    # ---- 採点(ENARSI-URPF-01 実機確立版の値差し替え) ----
    rxB = custB.replace(".", r"\.")
    adv_ip_rx = adv_link_ip.replace(".", r"\.")
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"},
               "checks": [
                   {"name": f"RT01: {strict_if} ({adv}側・対称) が strict uRPF",
                    "node": "RT01", "command": f"show ip interface {strict_if}",
                    "raw": [{"regex": "IP verify source reachable-via RX"}], "points": 10},
                   {"name": f"RT01: {asym_if} ({holder}側) に uRPF が有効 (rx または any)",
                    "node": "RT01", "command": f"show ip interface {asym_if}",
                    "raw": [{"regex": "IP verify source reachable-via (RX|ANY)"}], "points": 5},
                   {"name": f"RT01: {custB}.0/24 の経路が OSPF(E2)・{adv}側のまま(経路変更なし)",
                    "node": "RT01", "command": f"show ip route {custB}.0 255.255.255.0",
                    "raw": [{"regex": 'Known via "ospf 1"'}, {"regex": adv_ip_rx}], "points": 5},
                   {"name": f"正規フロー維持: ISP NOC 死活監視 ({adv}発 src {lo[adv]})",
                    "node": adv, "command": f"ping {lo['RT01']} source {lo[adv]} repeat 10",
                    "raw": [{"regex": "Success rate is [1-9]"}], "points": 5},
                   {"name": f"★正規フロー維持: 顧客B(非対称着信) ({holder}発 src {custB}.1)",
                    "node": holder, "command": f"ping {lo['RT01']} source {custB}.1 repeat 10",
                    "raw": [{"regex": "Success rate is [1-9]"}], "points": 25},
                   {"name": f"(発射) 経路なし送信元からの到達試行 ({holder}発 src {spoof})",
                    "node": holder,
                    "command": f"ping {lo['RT01']} source {spoof} repeat 10 timeout 1",
                    "raw": [{"regex": "Success rate is"}], "points": 0},
                   {"name": f"(発射) RPF不一致送信元からの到達試行 ({adv}発 src {custC}.99)",
                    "node": adv,
                    "command": f"ping {lo['RT01']} source {custC}.99 repeat 10 timeout 1",
                    "raw": [{"regex": "Success rate is"}], "points": 0},
                   {"name": f"効果: {asym_if} が経路なし送信元をドロップ (verification drops 非0)",
                    "node": "RT01", "command": f"show ip interface {asym_if}",
                    "raw": [{"regex": "[1-9][0-9]* verification drops"}], "points": 25},
                   {"name": f"効果: {strict_if} の strict が RPF不一致送信元をドロップ (verification drops 非0)",
                    "node": "RT01", "command": f"show ip interface {strict_if}",
                    "raw": [{"regex": "[1-9][0-9]* verification drops"}], "points": 25}]}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_urpf_ts.py) seed={a.seed} fault={fault}\n"
                "# ★偽装pingの成否は採点しない(偽陽性)。0点「発射」→カウンタの順序を変えないこと。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"fault": fault, "roles": roles, "custB": custB, "custC": custC,
                   "spoof": spoof, "acl_num": acl_num, "loopbacks": lo},
                  f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": build_fix(fault, roles, acl_num, custB)},
                  f, ensure_ascii=False, indent=2)

    # ---- 症状ベース task.md(故障非公開) ----
    upl = {"RT02": "Uplink-A (E0/0)", "RT03": "Uplink-B (E0/1)"}
    sym = {
        "strict_on_asym":
            f"顧客B (`{custB}.0/24`) から RT01 (`{lo['RT01']}`) への通信が、"
            "昨日の anti-spoofing 導入後から**届かなくなった**と苦情が来ている。",
        "acl_exempt_wrong":
            f"顧客B (`{custB}.0/24`) から RT01 (`{lo['RT01']}`) への通信が、"
            "昨日の anti-spoofing 導入後から**届かなくなった**と苦情が来ている。"
            "導入担当者は「顧客B は例外処理済みのはず」と主張している。",
        "missing_on_uplink":
            f"SOC 検知: **{upl[holder]} から流入する送信元偽装疑いのパケットが"
            "検証されずに素通り**している(当該IFの検証ドロップ実績が無い)。",
        "loose_on_strict_side":
            f"SOC 検知: **{upl[adv]} に着信する、実在プレフィックスを騙った"
            "送信元偽装疑いのパケットが素通り**している(検証ドロップ実績が無い)。",
    }[fault]
    task = f"""# 問題 {prob_id} : anti-spoofing (uRPF) トラブルシュート（難易度{DIFFICULTY[fault]}）

## 状況

エッジルータ **RT01** は 2 つの ISP にマルチホーム接続しており(経路は OSPF 受信)、
昨日 SOC の指示で**両アップリンクに送信元アドレス検証 (uRPF) を導入した**。
その後、下記のトラブルチケットが発行された。原因を切り分けて**復旧**せよ。

```
            RT01 (あなたの管理対象, Lo0 = {lo['RT01']})
       E0/0 |              | E0/1
    (Uplink-A)          (Uplink-B)
            |              |
      RT02 (ISP)  ------  RT03 (ISP)
              (ISP間ピアリング)
```

## トラブルチケット

> {sym}

## 遵守事項（セキュリティポリシー・変更範囲）

1. 両アップリンクの送信元検証は**維持**すること（撤去による「復旧」は不可）。
2. 検証モードは**各インタフェースで技術的に可能な限り厳格なもの**を使用すること。
3. 正規フロー（ISP NOC 死活監視 `{lo[adv]}` 発・顧客B `{custB}.1` 発）を断しないこと。
4. RT01 の**ルーティング設定（OSPF・静的経路）の変更・追加は禁止**。
5. RT02 / RT03 (ISP設備) の設定変更は禁止（状態確認は可）。

## 切り分けの観点

- 原因の種類・場所は伏せている。`show ip interface <IF>`（検証統計）・
  `show ip route <prefix>`・`show ip cef` などで状態から切り分けること。
- 採点は設定の字面ではなく**状態と実際のドロップ挙動**を見る。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : fault={fault} holder={holder} "
          f"custB={custB}.0/24 diff={DIFFICULTY[fault]}")


if __name__ == "__main__":
    main()
