#!/usr/bin/env python3
"""IP SLA/track TS 生成器（BL-134・ENARSI 4.5）。

正準トポロジ(実機検証済みの ENCOR-IPSLA-02 を値ランダム化・PoC= poc/ipsla/README.md):
  RT01 ──/30── prim(primary ISP) ──/30── RT04(Internet)
      ╲─/30── bkup(backup ISP)  ──/30──┘   (prim/bkup は RT02/RT03 を seed で入替)
  RT02↔RT03 に inter-ISP リンク(経路未使用・盤面の赤ニシン)。
  RT04: Lo10=データ(両ISP到達可) / Lo20=ヘルスビーコン(primary 経路でのみ到達可)。
  戻り経路ポリシー: RT04→プローブ送信元(/30) は primary 限定(応答も primary 対称)、
  RT04→RT01 Lo0 は backup 優先+AD200(IOL リンクダウン非伝播対策・データは非対称)。

形式は「WAN 経路監視標準 突き合わせ型 TS」(gen_dhcp_ts / gen_fnf_ts と同型)。
day0 は「先般 監視の導入・変更作業が行われた直後」の体で故障を注入。

故障カタログ(--fault 指定・既定 seed 抽選。--faults 2 は別レイヤから2つ):
  sla:    sla_not_scheduled(難3) / sla_wrong_source(難4 backup側IF=全滅) /
          sla_wrong_source_lo(難5 ★Lo0=応答が backup 依存になり、backup 側奥障害で
          誤 Down→健全な primary から死んだ backup へ切替→全断=誤フェイルオーバ。
          p10 実測) /
          sla_wrong_target(難3 ★データ宛監視=この盤面では機能症状が出ない=
          構成監査指摘形。p10 監査で症状文を是正) /
          op_pathecho(難4 ★IOL では何をしても上がらない=icmp-echo 差し替えが唯一解) /
          op_udp_jitter(難4 responder 不在= return code "No connection") /
          op_tcp_connect(難4 listen なし= "Socket connect error")
  track:  track_wrong_sla(難3 存在しない SLA 参照。SLA 統計は成功・track は Down/Unknown)
  route:  pin_missing(難5 ★平常時は健全→障害後フェイルバック不能ラッチ) /
          pin_wrong_nh(難4 ビーコン固定が backup 側=プローブ恒久失敗) /
          route_track_missing(難4 primary default に track なし=切替不能・事後形) /
          ad_not_floating(難4 backup が AD1=ECMP 混走・従量課金)
  filter: acl_probe_block(難5 エッジ ACL がビーコン echo-reply だけ落とす)

★実機知見(iol-xe 17.15・2026-08-22 PoC・poc/ipsla/README.md が正典):
  ・return code 指紋5種= OK/Timeout/Unknown(不稼働)/No connection/Socket connect error
  ・稼働中 SLA は編集ロック(unschedule→編集→再 schedule で解除・life は 3600 に戻る)
    → fix.json は「no で消して作り直し→schedule」の3段(match none)
  ・timeout>frequency は schedule 時拒否 → tcp-connect は timeout 明示が必須
  ・track 遷移は frequency 10 で 7〜11s(採点の converge リトライで吸収できる)

出力: problems/GEN-IPSLATS-<seed>/ {problem.yml, initial/*.cfg.j2, task.md, grading.yml,
      solution/{fault.json, fix.json}}
使い方: gen_ipsla_ts.py --repo . --seed <int> [--fault <name>] [--faults 1|2]
検証(破壊デモ): ansible-playbook playbooks/verify_ipsla_generated.yml -e problem=<ID>
"""
import argparse
import json
import os
import random

import yaml

LAYERS = {
    "sla": ["sla_not_scheduled", "sla_wrong_source", "sla_wrong_source_lo",
            "sla_wrong_target", "op_pathecho", "op_udp_jitter", "op_tcp_connect"],
    "track": ["track_wrong_sla"],
    "route": ["pin_missing", "pin_wrong_nh", "route_track_missing",
              "ad_not_floating"],
    "filter": ["acl_probe_block"],
}
FAULTS = [f for fs in LAYERS.values() for f in fs]
DIFFICULTY = {"sla_not_scheduled": 3, "sla_wrong_source": 4,
              "sla_wrong_source_lo": 5, "sla_wrong_target": 3,
              "op_pathecho": 4, "op_udp_jitter": 4, "op_tcp_connect": 4,
              "track_wrong_sla": 3, "pin_missing": 5, "pin_wrong_nh": 4,
              "route_track_missing": 4, "ad_not_floating": 4,
              "acl_probe_block": 5}


def rand_values(rnd):
    p = rnd.randint(1, 254)
    o = rnd.sample(range(1, 250), 5)      # 各 /30 の第3オクテット(重複なし)
    prim, bkup = rnd.sample(["RT02", "RT03"], 2)
    c = rnd.randint(1, 4)                 # RT01..RT04 の Lo0 = c.c.c.c 〜 (c+3).(c+3)...
    v = {
        "prim": prim, "bkup": bkup,
        "net_pa": f"10.{p}.{o[0]}",       # RT01-primary access
        "net_ba": f"10.{p}.{o[1]}",       # RT01-backup access
        "net_ii": f"10.{p}.{o[2]}",       # inter-ISP (経路未使用)
        "net_pu": f"10.{p}.{o[3]}",       # primary-RT04 uplink
        "net_bu": f"10.{p}.{o[4]}",       # backup-RT04 uplink
        "lo": {n: f"{c + i}.{c + i}.{c + i}.{c + i}"
               for i, n in enumerate(["RT01", "RT02", "RT03", "RT04"])},
        "data": rnd.choice(["8.8.8.8", "9.9.9.9"]),
        "beacon": f"100.64.{rnd.randint(0, 254)}.{rnd.randint(1, 254)}",
        "sla": rnd.randint(1, 99), "track": rnd.randint(1, 99),
        "ad": rnd.choice([180, 200, 220, 250]),
        "uport": rnd.choice([16400, 17000, 20000]),
        "tport": rnd.choice([2020, 8080, 9000]),
        "acl": f"{rnd.choice(['EDGE', 'WAN', 'SEC'])}-PROTECT-IN",
    }
    v["src"] = f"{v['net_pa']}.1"                     # プローブ送信元(標準)
    v["pri_nh"] = f"{v['net_pa']}.2"
    v["bk_nh"] = f"{v['net_ba']}.2"
    v["sla_bad"] = v["sla"] + 1 if v["sla"] < 99 else v["sla"] - 1
    return v


def pick_faults(rnd, n, forced):
    if forced:
        picks = [forced]
        if n == 2:
            layer_of = {f: L for L, fs in LAYERS.items() for f in fs}
            picks.append(rnd.choice(
                [f for f in FAULTS if layer_of[f] != layer_of[forced]]))
        return picks
    layers = rnd.sample(list(LAYERS), k=n)
    return [rnd.choice(LAYERS[L]) for L in layers]


def sla_block(v, faults):
    """RT01 の ip sla 定義+schedule(故障変種込み)。"""
    S, B, src = v["sla"], v["beacon"], v["src"]
    op = f"icmp-echo {B} source-ip {src}"
    freq = 10
    extra = []
    if "sla_wrong_source" in faults:
        op = f"icmp-echo {B} source-ip {v['net_ba']}.1"
    elif "sla_wrong_source_lo" in faults:
        op = f"icmp-echo {B} source-ip {v['lo']['RT01']}"
    elif "sla_wrong_target" in faults:
        op = f"icmp-echo {v['data']} source-ip {src}"
    elif "op_pathecho" in faults:
        op, freq = f"path-echo {B} source-ip {src}", 30
    elif "op_udp_jitter" in faults:
        op = f"udp-jitter {B} {v['uport']} source-ip {src}"
    elif "op_tcp_connect" in faults:
        op = f"tcp-connect {B} {v['tport']} source-ip {src} control disable"
        extra = [" timeout 5000"]         # 既定 60000 は schedule 拒否(PoC 知見8)
    L = [f"ip sla {S}", f" {op}"] + extra + [f" frequency {freq}", "!"]
    if "sla_not_scheduled" not in faults:
        L.append(f"ip sla schedule {S} life forever start-time now")
    L.append("!")
    return L


def render_rt01(v, faults):
    B, T, S = v["beacon"], v["track"], v["sla"]
    ref = v["sla_bad"] if "track_wrong_sla" in faults else S
    L = ["! RT01 初期状態 (顧客エッジ・先般 監視の導入/変更作業を実施した直後の状態)"]
    if "acl_probe_block" in faults:
        L += [f"ip access-list extended {v['acl']}",
              f" deny icmp host {B} host {v['src']} echo-reply",
              " permit ip any any", "!"]
    # links[0]=RT02 向け・links[1]=RT03 向け(lab.links の並び順で固定)。
    # primary/backup の役割は prim 抽選に従って載せ替える。
    slot_of = {v["prim"]: 0 if v["prim"] == "RT02" else 1,
               v["bkup"]: 0 if v["bkup"] == "RT02" else 1}
    ifdef = {}
    ifdef[slot_of[v["prim"]]] = [
        f" description === to {v['prim']} (primary ISP access) ===",
        f" ip address {v['net_pa']}.1 255.255.255.252"]
    if "acl_probe_block" in faults:
        ifdef[slot_of[v["prim"]]].append(f" ip access-group {v['acl']} in")
    ifdef[slot_of[v["bkup"]]] = [
        f" description === to {v['bkup']} (backup ISP access) ===",
        f" ip address {v['net_ba']}.1 255.255.255.252"]
    for slot in (0, 1):
        L += [f"interface {{{{ links[{slot}] }}}}"] + ifdef[slot] + \
             [" no shutdown", "!"]
    L += [
          "interface Loopback0",
          f" ip address {v['lo']['RT01']} 255.255.255.255", "!"]
    L += sla_block(v, faults)
    L += [f"track {T} ip sla {ref} reachability", "!"]
    if "pin_missing" not in faults:
        nh = v["bk_nh"] if "pin_wrong_nh" in faults else v["pri_nh"]
        L.append(f"ip route {B} 255.255.255.255 {nh}")
    if "route_track_missing" in faults:
        L.append(f"ip route 0.0.0.0 0.0.0.0 {v['pri_nh']}")
    else:
        L.append(f"ip route 0.0.0.0 0.0.0.0 {v['pri_nh']} track {T}")
    if "ad_not_floating" in faults:
        L.append(f"ip route 0.0.0.0 0.0.0.0 {v['bk_nh']}")
    else:
        L.append(f"ip route 0.0.0.0 0.0.0.0 {v['bk_nh']} {v['ad']}")
    L.append("!")
    return L


def render_isp(node, v):
    """prim/bkup ISP(変更禁止)。links: [0]=RT01 [1]=対向ISP [2]=RT04。"""
    is_prim = (node == v["prim"])
    acc = v["net_pa"] if is_prim else v["net_ba"]
    upl = v["net_pu"] if is_prim else v["net_bu"]
    role = "primary" if is_prim else "backup"
    L = [f"! {node} 初期状態 ({role} ISP・プロバイダ管理・変更禁止)",
         "interface Loopback0",
         f" ip address {v['lo'][node]} 255.255.255.255", "!",
         "interface {{ links[0] }}",
         " description === to RT01 (customer access) ===",
         f" ip address {acc}.2 255.255.255.252", " no shutdown", "!",
         "interface {{ links[1] }}",
         " description === inter-ISP peering ===",
         f" ip address {v['net_ii']}.{1 if node == 'RT02' else 2} 255.255.255.252",
         " no shutdown", "!",
         "interface {{ links[2] }}",
         " description === to RT04 (Internet core uplink) ===",
         f" ip address {upl}.1 255.255.255.252", " no shutdown", "!",
         f"ip route {v['data']} 255.255.255.255 {upl}.2"]
    if is_prim:
        # Internet/ビーコンへ RT04 直結のみ(迂回なし)=奥障害が track に伝わる
        L.append(f"ip route {v['beacon']} 255.255.255.255 {upl}.2")
    L += [f"ip route {v['lo']['RT01']} 255.255.255.255 {acc}.1", "!"]
    return L


def render_rt04(v):
    """RT04(Internet コア・変更禁止)。links: [0]=RT02 [1]=RT03。"""
    up = {"RT02": v["net_pu"] if v["prim"] == "RT02" else v["net_bu"],
          "RT03": v["net_pu"] if v["prim"] == "RT03" else v["net_bu"]}
    pu, bu = v["net_pu"], v["net_bu"]
    L = ["! RT04 初期状態 (Internet コア・プロバイダ管理・変更禁止)",
         "interface Loopback0",
         f" ip address {v['lo']['RT04']} 255.255.255.255", "!",
         "interface Loopback10",
         f" description === Simulated Internet Service ({v['data']}) ===",
         f" ip address {v['data']} 255.255.255.255", "!",
         "interface Loopback20",
         " description === Primary-path Health Beacon ===",
         f" ip address {v['beacon']} 255.255.255.255", "!",
         "interface {{ links[0] }}",
         " description === to RT02 ===",
         f" ip address {up['RT02']}.2 255.255.255.252", " no shutdown", "!",
         "interface {{ links[1] }}",
         " description === to RT03 ===",
         f" ip address {up['RT03']}.2 255.255.255.252", " no shutdown", "!",
         "! データ(RT01 Lo0 宛戻り)は常時生存の backup 優先+primary フォールバック",
         "!   (IOL リンクダウン非伝播対策・ENCOR-IPSLA-02 と同方針)",
         f"ip route {v['lo']['RT01']} 255.255.255.255 {bu}.1",
         f"ip route {v['lo']['RT01']} 255.255.255.255 {pu}.1 200",
         "! プローブ送信元(/30)への戻りは primary 経由のみ(応答も primary 対称)",
         f"ip route {v['net_pa']}.0 255.255.255.252 {pu}.1", "!"]
    return L


def build_fix(v, faults):
    S, T, B = v["sla"], v["track"], v["beacon"]
    N = {"match": "none"}
    golden_op = [f"icmp-echo {B} source-ip {v['src']}", "frequency 10"]
    fixes = []
    recreate = {"sla_wrong_source", "sla_wrong_source_lo", "sla_wrong_target",
                "op_pathecho", "op_udp_jitter", "op_tcp_connect"}
    if recreate & set(faults):
        # 稼働中エントリは編集ロック → 消して作り直し(PoC 知見: unschedule でも
        # 可だが life が 3600 に戻るため、再作成+完全な schedule が最短で安全)
        fixes += [{"node": "RT01",
                   "lines": [f"no ip sla schedule {S}", f"no ip sla {S}"], **N},
                  {"node": "RT01", "parents": f"ip sla {S}",
                   "lines": golden_op, **N},
                  {"node": "RT01",
                   "lines": [f"ip sla schedule {S} life forever start-time now"],
                   **N}]
    if "sla_not_scheduled" in faults:
        fixes.append({"node": "RT01",
                      "lines": [f"ip sla schedule {S} life forever start-time now"]})
    if "track_wrong_sla" in faults:
        fixes.append({"node": "RT01",
                      "lines": [f"track {T} ip sla {S} reachability"], **N})
    if "pin_missing" in faults:
        fixes.append({"node": "RT01",
                      "lines": [f"ip route {B} 255.255.255.255 {v['pri_nh']}"]})
    if "pin_wrong_nh" in faults:
        fixes.append({"node": "RT01",
                      "lines": [f"no ip route {B} 255.255.255.255 {v['bk_nh']}",
                                f"ip route {B} 255.255.255.255 {v['pri_nh']}"],
                      **N})
    if "route_track_missing" in faults:
        fixes.append({"node": "RT01",
                      "lines": [f"no ip route 0.0.0.0 0.0.0.0 {v['pri_nh']}",
                                f"ip route 0.0.0.0 0.0.0.0 {v['pri_nh']} track {T}"],
                      **N})
    if "ad_not_floating" in faults:
        fixes.append({"node": "RT01",
                      "lines": [f"no ip route 0.0.0.0 0.0.0.0 {v['bk_nh']}",
                                f"ip route 0.0.0.0 0.0.0.0 {v['bk_nh']} {v['ad']}"],
                      **N})
    if "acl_probe_block" in faults:
        fixes.append({"node": "RT01", "parents": f"ip access-list extended {v['acl']}",
                      "lines": [f"no deny icmp host {B} host {v['src']} echo-reply"],
                      **N})
    return fixes


SYMPTOM = {
    "sla_not_scheduled":
        "監視導入の完了後から、すべての外部向けトラフィックが backup ISP を経由して"
        "転送されています。primary ISP に障害は報告されていません。",
    "sla_wrong_source":
        "すべての外部向けトラフィックが backup ISP を経由して転送されています。"
        "一次対応者は、監視の定義は投入されているように見えると報告しています。",
    # ★下2種の症状文は 2026-08-22 に実測(poc/ipsla p10)で是正済み。
    #   当初の机上予測(「切替されず Up のまま」「フラップ」)は盤面の戻り経路
    #   ポリシーと矛盾していた(ユーザが出題中に発見)。症状文は必ず実測とセットで。
    "sla_wrong_source_lo":
        "昨夜、backup ISP の上流側で障害が発生した際、監視が Down を報告して"
        " backup への切替が実行され、外部通信が失われました。primary ISP は"
        "終始健全であったと報告されています。",
    "sla_wrong_target":
        "先般の導入・変更作業の完了後、社内の構成監査から「WAN 経路監視標準に"
        "適合していない項目が残っている」との指摘を受領しています。機能上の"
        "障害報告は現時点で届いていません。",
    "op_pathecho":
        "すべての外部向けトラフィックが backup ISP を経由して転送されています。"
        "前任者の作業記録には「経路単位の詳細な計測を行うため監視方式を変更した」"
        "とあります。",
    "op_udp_jitter":
        "すべての外部向けトラフィックが backup ISP を経由して転送されています。"
        "前任者の作業記録には「遅延の揺らぎも計測できる方式へ高度化した」とあります。",
    "op_tcp_connect":
        "すべての外部向けトラフィックが backup ISP を経由して転送されています。"
        "前任者の作業記録には「サービスレベルでの死活確認へ変更した」とあります。",
    "track_wrong_sla":
        "監視導入後、外部向けトラフィックは一度も primary 経由へ切り替わって"
        "いません。監視の統計情報は成功を示している、と一次対応者は報告しています。",
    "pin_missing":
        "昨夜、primary ISP 上流側の短時間の障害が発生し、backup への切替は実行"
        "されました。しかし障害の復旧後も経路は backup に固定されたままとなり、"
        "定時確認で発見されるまで primary へ復帰しませんでした。",
    "pin_wrong_nh":
        "すべての外部向けトラフィックが backup ISP を経由して転送されています。"
        "監視の定義そのものは標準と一致しているように見える、と一次対応者は"
        "報告しています。",
    "route_track_missing":
        "昨夜の primary ISP 上流側の障害の際、backup への切替が実行されず外部通信が"
        "失われました。監視オブジェクトは Down へ遷移していたことがログから確認"
        "されています。",
    "ad_not_floating":
        "外部向けトラフィックの一部が常時 backup ISP を経由しており、従量課金が"
        "増加しています。切替イベントのログはありません。",
    "acl_probe_block":
        "先日実施されたエッジセキュリティ強化の後から、すべての外部向け"
        "トラフィックが backup ISP を経由して転送されています。",
}


def build_grading(v, prob_id):
    S, T = v["sla"], v["track"]
    rx = {k: str(v[k]).replace(".", r"\.")
          for k in ["beacon", "data", "src", "pri_nh", "bk_nh"]}
    checks = [
        {"name": f"SLA {S}: オペレーション定義が監視標準どおり (icmp-echo/ビーコン/送信元)",
         "node": "RT01", "command": f"show ip sla configuration {S}",
         "raw": [{"regex": r"Type of operation to perform: icmp-echo"},
                 {"regex": f"Target address/Source address: {rx['beacon']}/{rx['src']}"}],
         "points": 10},
        {"name": f"SLA {S}: 恒久スケジュールで稼働中 (life forever / Active)",
         "node": "RT01", "command": f"show ip sla configuration {S}",
         "raw": [{"regex": r"Life \(seconds\): Forever"},
                 {"regex": r"Status of entry \(SNMP RowStatus\): Active"}],
         "points": 10},
        {"name": f"効果: SLA {S} のプローブが成功している (return code OK)",
         "node": "RT01", "command": f"show ip sla statistics {S}",
         "raw": [{"regex": r"Latest operation return code: OK"}], "points": 10},
        {"name": f"Track {T}: SLA {S} の reachability を監視し Up",
         "node": "RT01", "command": f"show track {T}",
         "raw": [{"regex": f"IP SLA {S} reachability"},
                 {"regex": r"Reachability is Up"}], "points": 10},
        {"name": "ビーコン /32 が primary next-hop へ固定されている",
         "node": "RT01", "command": "show running-config | include ^ip route",
         "raw": [{"regex": rf"(?m)^ip route {rx['beacon']} 255\.255\.255\.255 {rx['pri_nh']}\s*$"},
                 {"not_regex": rf"ip route {rx['beacon']} 255\.255\.255\.255 {rx['bk_nh']}"}],
         "points": 10},
        {"name": f"default route 対が監視標準どおり (primary=track {T} / backup=AD {v['ad']})",
         "node": "RT01", "command": "show running-config | include ^ip route",
         "raw": [{"regex": rf"(?m)^ip route 0\.0\.0\.0 0\.0\.0\.0 {rx['pri_nh']} track {T}\s*$"},
                 {"regex": rf"(?m)^ip route 0\.0\.0\.0 0\.0\.0\.0 {rx['bk_nh']} {v['ad']}\s*$"},
                 {"not_regex": rf"(?m)^ip route 0\.0\.0\.0 0\.0\.0\.0 {rx['pri_nh']}\s*$"},
                 {"not_regex": rf"(?m)^ip route 0\.0\.0\.0 0\.0\.0\.0 {rx['bk_nh']}\s*$"}],
         "points": 15},
        {"name": "効果: RIB の default が primary 単独 (AD1・backup 混走なし)",
         "node": "RT01", "command": "show ip route 0.0.0.0",
         "raw": [{"regex": r"Known via \"static\", distance 1"},
                 {"regex": rf"\* {rx['pri_nh']}"},
                 {"not_regex": rx["bk_nh"]}], "points": 10},
        {"name": f"効果: {v['data']} への実疎通 (source Lo0)",
         "node": "RT01",
         "command": f"ping {v['data']} source Loopback0 repeat 10",
         "raw": [{"regex": r"Success rate is 100 percent"}], "points": 15},
        {"name": f"track-table: default が track {T} に連動 (state up)",
         "node": "RT01", "command": "show ip route track-table",
         "raw": [{"regex": rf"track {T} state is \[up\]"}], "points": 5},
        {"name": "監視標準外のオペレーション残骸なし",
         "node": "RT01", "command": "show running-config | section ^ip sla",
         "raw": [{"not_regex": r"(?m)^\s*(path-echo|udp-jitter|tcp-connect|icmp-jitter)"}],
         "points": 5},
    ]
    return {"problem": prob_id, "total_points": 100,
            "defaults": {"genie_os": "iosxe"}, "checks": checks}


def build_task(v, prob_id, faults, diff):
    tickets = "\n".join(f"> {i + 1}. {SYMPTOM[f]}" for i, f in enumerate(faults)) \
        if len(faults) > 1 else f"> {SYMPTOM[faults[0]]}"
    prim, bkup = v["prim"], v["bkup"]
    ii1, ii2 = ("RT02", "RT03")
    return f"""# 問題 {prob_id} : WAN 経路監視標準 適合トラブルシュート（難易度{diff}）

## シナリオ

あなたは、ある企業のネットワーク管理者です。エッジルータ RT01 はデュアルホームで
2つの ISP（{prim} = primary / {bkup} = backup）に接続されており、インターネット上の
サービス `{v['data']}` に到達します。この会社の「WAN 経路監視標準（抜粋・下記）」に
従い、primary 経路の健全性を能動的に監視し、障害時には backup へ自動的に切り替える
必要があります。

先般、この監視に関する導入・変更作業が実施されました。その後、下記の障害報告が
提出されています。監視標準に完全に準拠するように、RT01 の構成を調査し、是正して
ください。

## 障害報告

{tickets}

## トポロジ

```
RT01 ──{v['net_pa'] if prim == 'RT02' else v['net_ba']}.0/30── RT02 ──{v['net_pu'] if prim == 'RT02' else v['net_bu']}.0/30── RT04(Internet)
    ╲─{v['net_ba'] if prim == 'RT02' else v['net_pa']}.0/30── RT03 ──{v['net_bu'] if prim == 'RT02' else v['net_pu']}.0/30──┘
              （{ii1}↔{ii2} 間に inter-ISP リンク {v['net_ii']}.0/30 あり）
```

- 各 /30 は RT01 側・ISP 側の順に .1/.2、アップリンクは ISP 側 .1・RT04 側 .2 です。
- RT01 の社内アドレス: `Loopback0 = {v['lo']['RT01']}`（データ通信の送信元）。
- `{v['data']}` は primary / backup どちらの ISP からも到達可能です（データ用）。
- プロバイダは primary 経路の死活確認用に、**primary 経路（RT01→{prim}→RT04）での
  み到達可能なヘルスビーコン `{v['beacon']}`** を提供しています。backup ISP はこの
  ビーコンへの経路を持ちません。

## WAN 経路監視標準（抜粋）

1. **監視** — IP SLA **{v['sla']}** を使用し、**ICMP echo** でヘルスビーコン
   **`{v['beacon']}`** を監視する。送信元は primary 側インタフェースのアドレス
   **`{v['src']}`** とする。
2. **プローブ経路の固定** — ビーコン宛の /32 スタティックルートを primary
   next-hop **`{v['pri_nh']}`** へ固定する（プローブがデフォルトルートに依存
   しないこと）。
3. **トラッキング** — Track **{v['track']}** で IP SLA {v['sla']} の
   **reachability** を監視する。
4. **経路切替** — default route は、通常時 primary **`{v['pri_nh']}`**
   （Track {v['track']} 連動）、障害時 backup **`{v['bk_nh']}`**
   （AD **{v['ad']}** のフローティングスタティック）とする。
5. **スケジュール** — 監視は **恒久的（life forever, start-time now）**に実行する。
6. **是正の完全性** — 監視標準に含まれないオペレーション定義や、監視を阻害する
   フィルタを残置しないこと。

## 遵守事項

- **RT02 / RT03 / RT04 はプロバイダ管理機器です。参照は可能ですが、変更しては
  いけません。**設定を変更してよいのは RT01 のみです。
- RT01 のインタフェースアドレス・Loopback0 は変更してはいけません。
- 原因の種類・箇所・数は開示されません。監視標準と実機の状態を突き合わせて
  差分を特定してください。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）または CML コンソール。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
> 採点では、監視の定義・稼働状態・経路構成に加え、`{v['data']}` への実疎通を確認
> します。任意で、奥障害（{prim}↔RT04）の注入と切替・復帰の実証を行うには:
> `ansible-playbook playbooks/verify_ipsla_generated.yml -e problem={prob_id}`
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    ap.add_argument("--faults", type=int, choices=[1, 2], default=1)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    v = rand_values(rnd)
    faults = pick_faults(rnd, a.faults, a.fault)
    diff = min(max(DIFFICULTY[f] for f in faults) + (1 if len(faults) == 2 else 0), 5)

    prob_id = f"GEN-IPSLATS-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"WAN 経路監視標準 適合トラブルシュート (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["ip-sla", "track", "static-route", "path-control",
                          "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": ["RT01", "RT02", "RT03", "RT04"],
               "points": 100, "access": "ssh",
               "bringup_data_ifs": True,
               "lab": {"links": [
                   {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                   {"a": "RT01", "a_if": 1, "b": "RT03", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "RT03", "b_if": 1},
                   {"a": "RT02", "a_if": 2, "b": "RT04", "b_if": 0},
                   {"a": "RT03", "a_if": 2, "b": "RT04", "b_if": 1}],
                   "positions": {"RT01": [-320, 0], "RT02": [0, -140],
                                 "RT03": [0, 140], "RT04": [320, 0]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_ipsla_ts.py) seed={a.seed} "
                f"faults={','.join(faults)} prim={v['prim']}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/initial/RT01.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt01(v, faults)) + "\n")
    for node in ["RT02", "RT03"]:
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_isp(node, v)) + "\n")
    with open(f"{pdir}/initial/RT04.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt04(v)) + "\n")

    grading = build_grading(v, prob_id)
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_ipsla_ts.py) seed={a.seed} faults={','.join(faults)}\n"
                "# 監視標準の指定値で固定判定(ENCOR-IPSLA-01/02 の型)。効果チェックは\n"
                "# statistics OK/RIB/実疎通。破壊実証は verify_ipsla_generated.yml(任意)。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    meta = {"faults": faults, "difficulty": diff, "prim": v["prim"],
            "bkup": v["bkup"], "deep_if": "Ethernet0/2",
            "sla": v["sla"], "track": v["track"], "beacon": v["beacon"],
            "data": v["data"], "src": v["src"], "pri_nh": v["pri_nh"],
            "bk_nh": v["bk_nh"], "ad": v["ad"], "lo_rt01": v["lo"]["RT01"]}
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": build_fix(v, faults)}, f, ensure_ascii=False, indent=2)

    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(build_task(v, prob_id, faults, diff))
    print(f"wrote problems/{prob_id} : faults={','.join(faults)} diff={diff} "
          f"prim={v['prim']} sla={v['sla']} track={v['track']} beacon={v['beacon']}")


if __name__ == "__main__":
    main()
