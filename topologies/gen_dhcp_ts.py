#!/usr/bin/env python3
"""DHCPv4 トラブルシュート生成器（BL-067・ENCOR-DHCP-01 の反転）。

正準トポロジ(実機検証済みの ENCOR-DHCP-01 を値ランダム化・手動バインディングは除外*):
  CL3 ─ RT01(DHCPサーバ) ─p2p/30─ RT02(リレー) ┬─ CL1 (segment A /24)
  (LOCAL /24)                                   └─ CL2 (segment B /24)
  クライアントは `ip address dhcp` 既設(変更禁止)。ACL DHCP-ONLY 相当(明示deny付き)も既設。
  *) 手動バインディングは MAC が provision 毎に変わり day0 に焼けないため TS では扱わない
     (BL-066 構築問の領分)。

形式は「アドレス配布標準仕様書 突き合わせ型 TS」(BL-065 FNF と同型)。
day0 は「昨日 DHCP 集約とセキュリティ強化を実施した直後」の体で故障を注入。

故障カタログ(--fault 指定・既定 seed 抽選。--faults 2 は別レイヤから2つ):
  relay:  helper_missing(難3) / helper_wrong_ip(難3) /
          relay_service_off(難5) ★helper完備・IF設定は仕様どおりに見えるのに
          リレー機の `no service dhcp` で DHCP リレーエージェントだけが死んでいる
  acl:    acl_no_dhcp_permit(難4) / acl_src_narrow(難5) ★送信元をサブネットで絞った
          permit → unicast 更新は通るが DISCOVER(src 0.0.0.0)だけ落ちる
  server: pool_wrong_subnet(難4) / excluded_swallows(難4) / service_dhcp_off(難3)

★実機知見(iol-xe 17.15・2026-07-26 PoC):
  ・`no ip forward-protocol udp bootps` は day0 で黙殺される上に、ライブ適用しても
    **DHCP リレーは止まらない**(helper の DHCP 転送は forward-protocol でなく
    DHCP リレーエージェント=service dhcp の管轄)→ 故障として不成立・relay_service_off に差替
  ・採点で release を発火すると毎試行 DORA がリセットされ完了前に次のリセットが来る
    構造的競合で健全ラボでも偽 FAIL → **renew のみ発火＋CL1 判定は最後尾**

採点(構築問 BL-066 で確立したイディオムを踏襲):
  ・renew 発火は CL1 のみ・チェック列の先頭、CL1 実 IP 判定は最後尾(settle 最大化)
  ・負の要件は明示 deny のヒットカウンタ(telnet 文字列は no route と識別不能)
  ・クライアント実 IP は excluded 回避込みで判定

fix.json は fix_generated.yml 互換。ACL 修正は「削除→全行再作成」を match: none で
発行(部分挿入は deny より後ろに permit が付く事故・stale diff no-op を両方回避)。

出力: problems/GEN-DHCPTS-<seed>/ {problem.yml, initial/*.cfg.j2, task.md, grading.yml,
      solution/{fault.json, fix.json}}
使い方: gen_dhcp_ts.py --repo . --seed <int> [--fault <name>] [--faults 1|2]
"""
import argparse
import json
import os
import random

import yaml

LAYERS = {
    "relay": ["helper_missing", "helper_wrong_ip", "relay_service_off"],
    "acl": ["acl_no_dhcp_permit", "acl_src_narrow"],
    "server": ["pool_wrong_subnet", "excluded_swallows", "service_dhcp_off"],
}
FAULTS = [f for fs in LAYERS.values() for f in fs]
DIFFICULTY = {"helper_missing": 3, "helper_wrong_ip": 3, "relay_service_off": 5,
              "acl_no_dhcp_permit": 4, "acl_src_narrow": 5,
              "pool_wrong_subnet": 4, "excluded_swallows": 4, "service_dhcp_off": 3}
IF_A, IF_B = "Ethernet0/1", "Ethernet0/2"        # RT02 のクライアント収容 IF


def rand_values(rnd):
    # p≤240: excluded の not_regex(\.25[0-4]) と衝突しない / q≤180: wrong_net(+60)が255未満
    p, q = rnd.randint(1, 240), rnd.randint(0, 180)
    seg = {"L": f"10.{p}.{q}", "A": f"10.{p}.{q + 1}", "B": f"10.{p}.{q + 2}",
           "P": f"10.{p}.{q + 3}"}                # P = RT01-RT02 p2p /30
    tag = rnd.choice(["CORP", "BRANCH", "CAMPUS", "OPS"])
    pools = {"L": f"NET-{tag}-L", "A": f"NET-{tag}-A", "B": f"NET-{tag}-B"}
    acl = f"{tag}-DHCP-ONLY"
    dns = f"{rnd.choice(['198.51.100', '203.0.113'])}.{rnd.randint(10, 250)}"
    return seg, pools, acl, dns


def pick_faults(rnd, n, forced):
    if forced:
        picks = [forced]
        if n == 2:
            layer_of = {f: L for L, fs in LAYERS.items() for f in fs}
            picks.append(rnd.choice([f for f in FAULTS if layer_of[f] != layer_of[forced]]))
        return picks
    layers = rnd.sample(list(LAYERS), k=n)
    return [rnd.choice(LAYERS[L]) for L in layers]


def render_rt01(seg, pools, dns, faults, tgt, wrong_net):
    srv = f"{seg['P']}.1"
    L = ["! RT01 初期状態 (DHCPサーバ・昨日 配布集約を実施した直後の状態)"]
    if "service_dhcp_off" in faults:
        L += ["no service dhcp", "!"]
    L += ["interface {{ links[0] }}", " description === to RT02 (relay uplink) ===",
          f" ip address {srv} 255.255.255.252", " no shutdown", "!",
          "interface {{ links[1] }}", " description === LOCAL segment (CL3) ===",
          f" ip address {seg['L']}.1 255.255.255.0", " no shutdown", "!"]
    for s in ["L", "A", "B"]:
        hi = "254" if ("excluded_swallows" in faults and s == tgt) else "9"
        L.append(f"ip dhcp excluded-address {seg[s]}.1 {seg[s]}.{hi}")
    L.append("!")
    for s in ["L", "A", "B"]:
        net = wrong_net if ("pool_wrong_subnet" in faults and s == tgt) else seg[s]
        L += [f"ip dhcp pool {pools[s]}",
              f" network {net}.0 255.255.255.0",
              f" default-router {seg[s]}.1",
              f" dns-server {dns}", "!"]
    L += ["! リレー戻り経路 (既設・変更禁止)",
          f"ip route {seg['A']}.0 255.255.255.0 {seg['P']}.2",
          f"ip route {seg['B']}.0 255.255.255.0 {seg['P']}.2", "!"]
    return L


def render_rt02(seg, acl, faults, tgt):
    srv = f"{seg['P']}.1"
    L = ["! RT02 初期状態 (リレー+セキュリティACL・昨日 強化を実施した直後の状態)"]
    if "relay_service_off" in faults:
        L += ["no service dhcp", "!"]     # リレーエージェント停止(helper は完璧に見える)
    # --- ACL(変種込み) ---
    L.append(f"ip access-list extended {acl}")
    if "acl_no_dhcp_permit" in faults:
        pass                                     # DHCP permit 欠落
    elif "acl_src_narrow" in faults:
        L += [f" permit udp {seg['A']}.0 0.0.0.255 eq bootpc any eq bootps",
              f" permit udp {seg['B']}.0 0.0.0.255 eq bootpc any eq bootps"]
    else:
        L.append(" permit udp any eq bootpc any eq bootps")
    L += [" permit icmp any any", " deny ip any any", "!"]
    L += ["interface {{ links[0] }}", " description === to RT01 (DHCP server) ===",
          f" ip address {seg['P']}.2 255.255.255.252", " no shutdown", "!"]
    for slot, s, ifn, cl in [(1, "A", IF_A, "CL1"), (2, "B", IF_B, "CL2")]:
        L += [f"interface {{{{ links[{slot}] }}}}",
              f" description === CLIENT segment {s} ({cl}) ===",
              f" ip address {seg[s]}.1 255.255.255.0"]
        drop_helper = (("helper_missing" in faults or "helper_wrong_ip" in faults)
                       and s == tgt)
        if not drop_helper:
            L.append(f" ip helper-address {srv}")
        elif "helper_wrong_ip" in faults:
            L.append(f" ip helper-address {seg['P']}.9")   # /30 外の空アドレス
        L += [f" ip access-group {acl} in", " no shutdown", "!"]
    L += ["! LOCAL セグメントへの経路 (既設・変更禁止)",
          f"ip route {seg['L']}.0 255.255.255.0 {srv}", "!"]
    return L


def render_client(name, s, seg):
    return [f"! {name} 初期状態 (DHCP クライアント・設定は正しい/変更禁止)",
            "interface {{ links[0] }}",
            f" description === segment {s} (ip address dhcp 既設) ===",
            " ip address dhcp", " no shutdown", "!"]


def build_fix(seg, pools, acl, faults, tgt, wrong_net):
    srv = f"{seg['P']}.1"
    N = {"match": "none"}
    fixes = []
    if "service_dhcp_off" in faults:
        fixes.append({"node": "RT01", "lines": ["service dhcp"]})
    if "excluded_swallows" in faults:
        fixes.append({"node": "RT01", "lines": [
            f"no ip dhcp excluded-address {seg[tgt]}.1 {seg[tgt]}.254",
            f"ip dhcp excluded-address {seg[tgt]}.1 {seg[tgt]}.9"]})
    if "pool_wrong_subnet" in faults:
        fixes.append({"node": "RT01", "parents": f"ip dhcp pool {pools[tgt]}",
                      "lines": [f"no network {wrong_net}.0 255.255.255.0",
                                f"network {seg[tgt]}.0 255.255.255.0"]})
    if "relay_service_off" in faults:
        fixes.append({"node": "RT02", "lines": ["service dhcp"]})
    tgt_if = IF_A if tgt == "A" else IF_B
    if "helper_missing" in faults:
        fixes.append({"node": "RT02", "parents": f"interface {tgt_if}",
                      "lines": [f"ip helper-address {srv}"]})
    if "helper_wrong_ip" in faults:
        fixes.append({"node": "RT02", "parents": f"interface {tgt_if}",
                      "lines": [f"no ip helper-address {seg['P']}.9",
                                f"ip helper-address {srv}"]})
    if ("acl_no_dhcp_permit" in faults) or ("acl_src_narrow" in faults):
        # 部分挿入は deny の後ろに permit が付く事故になる → 全消し→全行再作成(match none)
        fixes.append({"node": "RT02",
                      "lines": [f"no ip access-list extended {acl}"], **N})
        fixes.append({"node": "RT02", "parents": f"ip access-list extended {acl}",
                      "lines": ["permit udp any eq bootpc any eq bootps",
                                "permit icmp any any", "deny ip any any"], **N})
    return fixes


SYMPTOM = {
    "helper_missing":
        "**segment {tseg} の端末だけが全くアドレスを取得できない**"
        "（他セグメントは正常に配布されている）。",
    "helper_wrong_ip":
        "**segment {tseg} の端末だけが全くアドレスを取得できない**。"
        "現地担当は「リレー設定は入っているように見える」と報告している。",
    "relay_service_off":
        "**両リモートセグメント(A/B)の端末が取得できない**。ローカルセグメントは正常。"
        "一次対応者は「リレー機のクライアント収容 IF の設定は仕様書どおりで、"
        "サーバへの ping も通る」と報告している。",
    "acl_no_dhcp_permit":
        "昨日のセキュリティ強化の直後から、**両リモートセグメントで取得不能**。"
        "ローカルセグメントは正常。",
    "acl_src_narrow":
        "セキュリティ監査対応で ACL を「最小権限に強化」した直後から、"
        "**リース切れや初期化をした端末だけが取得できない**"
        "（既存リースの更新は通っている形跡がある）。",
    "pool_wrong_subnet":
        "**segment {tseg} だけ取得不能**。サーバ担当は「DISCOVER は届いているのに"
        "OFFER を返していないようだ」と報告している。",
    "excluded_swallows":
        "**segment {tseg} だけ取得不能**。サーバ担当は「プールは定義済みのはず」と"
        "主張している。",
    "service_dhcp_off":
        "**全セグメント（ローカル含む）で一斉に取得不能**になった。",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    ap.add_argument("--faults", type=int, choices=[1, 2], default=1)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    seg, pools, acl, dns = rand_values(rnd)
    faults = pick_faults(rnd, a.faults, a.fault)
    tgt = rnd.choice(["A", "B"])                  # セグメント限定故障の対象
    wrong_net = f"{seg[tgt].rsplit('.', 1)[0]}.{int(seg[tgt].rsplit('.', 1)[1]) + 60}"
    diff = min(max(DIFFICULTY[f] for f in faults) + (1 if len(faults) == 2 else 0), 5)
    srv = f"{seg['P']}.1"

    prob_id = f"GEN-DHCPTS-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"DHCPv4 配布標準 適合トラブルシュート (seed={a.seed})",
               "exam": "ENCOR",
               "topics": ["dhcp", "dhcp-relay", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": ["RT01", "RT02", "CL1", "CL2", "CL3"],
               "points": 100, "access": "ssh",
               "bringup_data_ifs": True,
               "lab": {"links": [
                   {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                   {"a": "RT01", "a_if": 1, "b": "CL3", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "CL1", "b_if": 0},
                   {"a": "RT02", "a_if": 2, "b": "CL2", "b_if": 0}],
                   "positions": {"RT01": [0, 0], "RT02": [300, 0], "CL3": [0, 200],
                                 "CL1": [500, -100], "CL2": [500, 100]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dhcp_ts.py) seed={a.seed} faults={','.join(faults)} tgt={tgt}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/initial/RT01.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt01(seg, pools, dns, faults, tgt, wrong_net)) + "\n")
    with open(f"{pdir}/initial/RT02.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt02(seg, acl, faults, tgt)) + "\n")
    for name, s in [("CL1", "A"), ("CL2", "B"), ("CL3", "L")]:
        with open(f"{pdir}/initial/{name}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_client(name, s, seg)) + "\n")

    # ---- 採点 ----
    rx = {k: v.replace(".", r"\.") for k, v in seg.items()}
    dns_rx = dns.replace(".", r"\.")
    srv_rx = srv.replace(".", r"\.")
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"},
               "checks": [
                   # ★release は発火しない: 毎試行の release が DORA を完了前にリセットし
                   #   健全ラボでも CL1 が偽 FAIL する(実機で構造的競合を確認)。
                   #   renew のみ = Bound中は無切断更新 / 未Bound は DISCOVER 再開。
                   {"name": "(発火) CL1: renew dhcp", "node": "CL1",
                    "command": "renew dhcp Ethernet0/0",
                    "raw": [{"regex": ".*"}], "points": 0},
                   {"name": "RT01: 3プールの network/GW/DNS が配布標準どおり",
                    "node": "RT01",
                    "command": "show running-config | section ip dhcp pool",
                    "raw": [{"regex": f"network {rx[s]}\\.0 255\\.255\\.255\\.0"}
                            for s in ["L", "A", "B"]] +
                           [{"regex": f"default-router {rx[s]}\\.1"}
                            for s in ["L", "A", "B"]] +
                           [{"regex": f"dns-server {dns_rx}"}], "points": 10},
                   {"name": "RT01: excluded-address (.1-.9) が3セグメントとも標準どおり",
                    "node": "RT01",
                    "command": "show running-config | include ip dhcp excluded-address",
                    "raw": [{"regex": f"excluded-address {rx[s]}\\.1 {rx[s]}\\.9"}
                            for s in ["L", "A", "B"]] +
                           [{"not_regex": r"excluded-address \S+ \S+\.25[0-4]"}],
                    "points": 10},
                   {"name": "RT01: アドレス配布サービス基盤が有効",
                    "node": "RT01",
                    "command": "show running-config | include service dhcp",
                    "raw": [{"not_regex": "no service dhcp"}], "points": 5},
                   {"name": f"RT02: {IF_A} (segment A) のリレー設定が標準どおり",
                    "node": "RT02",
                    "command": f"show running-config interface {IF_A}",
                    "raw": [{"regex": f"ip helper-address {srv_rx}"},
                            {"not_regex": r"helper-address \S+\.9\b"}], "points": 5},
                   {"name": f"RT02: {IF_B} (segment B) のリレー設定が標準どおり",
                    "node": "RT02",
                    "command": f"show running-config interface {IF_B}",
                    "raw": [{"regex": f"ip helper-address {srv_rx}"},
                            {"not_regex": r"helper-address \S+\.9\b"}], "points": 5},
                   {"name": "RT02: リレー転送基盤(DHCPリレーエージェント)が有効",
                    "node": "RT02",
                    "command": "show running-config | include service dhcp",
                    "raw": [{"not_regex": "no service dhcp"}],
                    "points": 5},
                   {"name": f"RT02: ACL {acl} が {IF_A} の in に適用",
                    "node": "RT02", "command": f"show ip interface {IF_A}",
                    "raw": [{"regex": f"Inbound\\s+access list is {acl}"}], "points": 5},
                   {"name": f"RT02: ACL {acl} が {IF_B} の in に適用",
                    "node": "RT02", "command": f"show ip interface {IF_B}",
                    "raw": [{"regex": f"Inbound\\s+access list is {acl}"}], "points": 5},
                   # BL-094(2026-08-06): 書式regex→acl_vectors意味評価へ差し替え。
                   # 汎用形以外の等価解(セグメント絞り+rebind broadcast行など)を救済
                   # (7710でユーザの意味的等価解がregexに弾かれた実戦教訓)。
                   # ベクタ= DISCOVER/renew単方向×2seg/rebind broadcast×2seg/
                   #         icmp許可/非許可(telnet・DNS)遮断
                   {"name": f"RT02: ACL {acl} の中身が配布標準どおり (DHCP/ICMP許可+明示deny)",
                    "node": "RT02", "command": f"show access-lists {acl}",
                    "acl_vectors": {"acl": acl, "vectors": [
                        {"id": "discover", "proto": "udp", "src": "0.0.0.0", "sport": 68,
                         "dst": "255.255.255.255", "dport": 67, "expect": "permit"},
                        {"id": "renew_a", "proto": "udp", "src": f"{seg['A']}.50", "sport": 68,
                         "dst": f"{seg['P']}.1", "dport": 67, "expect": "permit"},
                        {"id": "renew_b", "proto": "udp", "src": f"{seg['B']}.50", "sport": 68,
                         "dst": f"{seg['P']}.1", "dport": 67, "expect": "permit"},
                        {"id": "rebind_a", "proto": "udp", "src": f"{seg['A']}.50", "sport": 68,
                         "dst": "255.255.255.255", "dport": 67, "expect": "permit"},
                        {"id": "rebind_b", "proto": "udp", "src": f"{seg['B']}.50", "sport": 68,
                         "dst": "255.255.255.255", "dport": 67, "expect": "permit"},
                        {"id": "icmp_ok", "proto": "icmp", "src": f"{seg['B']}.50",
                         "dst": f"{seg['L']}.1", "expect": "permit"},
                        {"id": "telnet_ng", "proto": "tcp", "src": f"{seg['B']}.50", "sport": 40000,
                         "dst": f"{seg['P']}.1", "dport": 23, "expect": "deny"},
                        {"id": "dns_ng", "proto": "udp", "src": f"{seg['B']}.50", "sport": 12345,
                         "dst": f"{seg['P']}.1", "dport": 53, "expect": "deny"},
                    ]}, "points": 10},
                   {"name": "効果: CL3 が LOCAL プールから取得 (excluded 回避)",
                    "node": "CL3",
                    "command": "show ip interface Ethernet0/0 | include Internet",
                    "raw": [{"regex": f"Internet address is {rx['L']}\\.\\d+/24"},
                            {"not_regex": f"Internet address is {rx['L']}\\.[1-9]/"}],
                    "points": 5},
                   {"name": "効果: CL2 が segment B から取得 (excluded 回避)",
                    "node": "CL2",
                    "command": "show ip interface Ethernet0/0 | include Internet",
                    "raw": [{"regex": f"Internet address is {rx['B']}\\.\\d+/24"},
                            {"not_regex": f"Internet address is {rx['B']}\\.[1-9]/"}],
                    "points": 10},
                   {"name": f"効果: ACL 越し ICMP + 配布 GW でセグメント間疎通 (CL2→{seg['L']}.1)",
                    "node": "CL2", "command": f"ping {seg['L']}.1 repeat 5",
                    "raw": [{"regex": "Success rate is [1-9]"}], "points": 5},
                   {"name": "(発火) CL2→サーバへの非許可通信の試行 (telnet)",
                    "node": "CL2", "command": f"telnet {srv}",
                    "raw": [{"regex": ".*"}], "points": 0},
                   {"name": f"効果: 非許可通信は遮断 ({acl} の明示 deny がヒット)",
                    "node": "RT02", "command": f"show access-lists {acl}",
                    "raw": [{"regex": r"deny\s+ip any any \([1-9][0-9]* match"}],
                    "points": 5},
                   # ★CL1 は最後尾: renew 発火(先頭)からの経過時間を最大化して DORA を収束させる
                   {"name": "★効果: CL1 が renew 後に segment A から(再)取得",
                    "node": "CL1",
                    "command": "show ip interface Ethernet0/0 | include Internet",
                    "raw": [{"regex": f"Internet address is {rx['A']}\\.\\d+/24"},
                            {"not_regex": f"Internet address is {rx['A']}\\.[1-9]/"}],
                    "points": 15}]}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dhcp_ts.py) seed={a.seed} faults={','.join(faults)} tgt={tgt}\n"
                "# ★renew のみ発火(release は DORA リセット競合で偽 FAIL)・CL1 判定は最後尾。\n"
                "#   負の要件は deny カウンタ。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"faults": faults, "target_segment": tgt, "segments": seg,
                   "pools": pools, "acl": acl, "dns": dns, "difficulty": diff},
                  f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": build_fix(seg, pools, acl, faults, tgt, wrong_net)},
                  f, ensure_ascii=False, indent=2)

    # ---- task.md ----
    tseg = f"{tgt} ({seg[tgt]}.0/24)"
    tickets = "\n".join(f"> {i + 1}. {SYMPTOM[f].format(tseg=tseg)}"
                        for i, f in enumerate(faults)) \
        if len(faults) > 1 else f"> {SYMPTOM[faults[0]].format(tseg=tseg)}"
    task = f"""# 問題 {prob_id} : DHCPv4 配布標準 適合トラブルシュート（難易度{diff}）

## 状況

昨日、アドレス配布の **RT01 (DHCPサーバ) への集約**と**クライアント収容 IF の
セキュリティ強化**を実施した。その直後から下記のトラブルチケットが届いている。
社内の**アドレス配布標準仕様書（抜粋・下記）に完全準拠**するよう調査・是正せよ。

```
CL3 ── RT01(DHCPサーバ) ──{seg['P']}.0/30── RT02(リレー) ─┬─ CL1  segment A: {seg['A']}.0/24
LOCAL: {seg['L']}.0/24        .1        .2                └─ CL2  segment B: {seg['B']}.0/24
```

## トラブルチケット

{tickets}

## アドレス配布標準仕様書（抜粋）

1. **プール** — LOCAL=`{pools['L']}` / segment A=`{pools['A']}` / segment B=`{pools['B']}`。
   各セグメントの network・default-router(各 GW `.1`)・DNS **`{dns}`** を配布する。
2. **配布禁止** — 各セグメント **`.1`〜`.9`** を excluded とする。
3. **リレー** — RT02 の両クライアント収容 IF から **`{srv}`** へリレーする。
4. **セキュリティ** — RT02 の両クライアント収容 IF の in に ACL **`{acl}`** を適用し、
   **DHCP (UDP 67/68) と ICMP のみ許可**・最終行は**明示の `deny ip any any`**。
   この状態で**初回取得(DISCOVER)・更新とも壊れないこと**。

## 遵守事項

- 標準仕様の**撤去・別名での作り直しによる「復旧」は不可**（仕様の名前・値に一致させる）。
- クライアント (CL1〜CL3) の設定は**正しい・変更禁止**（状態確認・release/renew は可）。
- RT01/RT02 の IF アドレス・静的経路は変更禁止。
- 原因の種類・場所・数は伏せている。仕様書と実機を突き合わせて差分を特定すること。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
> 採点では release/renew の実効（ACL 適用状態での再取得）まで確認する。
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : faults={','.join(faults)} tgt={tgt} diff={diff} "
          f"segs L/A/B={seg['L']}/{seg['A']}/{seg['B']} acl={acl}")


if __name__ == "__main__":
    main()
