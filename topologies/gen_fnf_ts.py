#!/usr/bin/env python3
"""Flexible NetFlow トラブルシュート生成器（BL-065・ENCOR-FNF-01 の反転）。

正準トポロジ(実機検証済みの ENCOR-FNF-01 を値ランダム化):
  RT01(送信元) ─ seg12/30 ─ RT02(FNF・被疑) ─ seg23/30 ─ RT03(宛先)   OSPF area0 既設
  RT02: Et0/0(links[0]) = RT01向け(仕様の監視点: ingress) / Et0/1(links[1]) = RT03向け

形式は「監視標準仕様書 突き合わせ型 TS」: 仕様(record キー/collect・exporter の
destination/source/udp port/export-protocol・monitor 束ね・E0/0 ingress 適用)を全文提示し、
昨日導入された FNF が仕様どおり動かない、というチケットを1〜2枚出す。

故障カタログ(--fault で指定・既定は seed 抽選。--faults 2 は別レイヤから2つ):
  apply:    apply_direction_output(難3) / apply_wrong_if(難3) / monitor_not_applied(難3)
  monitor:  monitor_no_exporter(難3) / monitor_wrong_record(難4・旧REC-OLD参照)
  record:   record_missing_key(難4・proto/L4port のどれか欠落)
  exporter: exporter_wrong_dest(難3) / exporter_wrong_port(難3) /
            exporter_wrong_source(難4) / exporter_wrong_version(難4・v9残置/仕様ipfix)

採点の要: cache 実効は `show flow monitor <MON> cache format table` の
**同一行 `src\\s+dst` regex**（contains 2連は逆向きフローで偽陽性→方向故障を検出できない）。

fix.json は常に「①現適用点から monitor を外す→②構造修正→③E0/0 input へ適用」の3段
（IOS は使用中 record/monitor の編集を拒否するため）。fix_generated.yml 互換。

出力: problems/GEN-FNFTS-<seed>/ {problem.yml, initial/*.cfg.j2, task.md, grading.yml,
      solution/{fault.json, fix.json}}
使い方: gen_fnf_ts.py --repo . --seed <int> [--fault <name>] [--faults 1|2]
"""
import argparse
import json
import os
import random

import yaml

LAYERS = {
    "apply": ["apply_direction_output", "apply_wrong_if", "monitor_not_applied"],
    "monitor": ["monitor_no_exporter", "monitor_wrong_record"],
    "record": ["record_missing_key"],
    "exporter": ["exporter_wrong_dest", "exporter_wrong_port",
                 "exporter_wrong_source", "exporter_wrong_version"],
}
FAULTS = [f for fs in LAYERS.values() for f in fs]
DIFFICULTY = {"apply_direction_output": 3, "apply_wrong_if": 3, "monitor_not_applied": 3,
              "monitor_no_exporter": 3, "monitor_wrong_record": 4, "record_missing_key": 4,
              "exporter_wrong_dest": 3, "exporter_wrong_port": 3,
              "exporter_wrong_source": 4, "exporter_wrong_version": 4}
IF0, IF1 = "Ethernet0/0", "Ethernet0/1"          # links[0]=RT01向け / links[1]=RT03向け
MATCH_KEYS = ["ipv4 source address", "ipv4 destination address", "ipv4 protocol",
              "transport source-port", "transport destination-port"]
COLLECTS = ["counter bytes", "counter packets"]
# record_missing_key で欠落させてよいキー(src/dst addr は cache 実効まで壊れて別故障化するため除外)
DROPPABLE_KEYS = MATCH_KEYS[2:]
VER_CFG = {"netflow-v9": "netflow-v9", "ipfix": "ipfix"}
VER_SHOW = {"netflow-v9": r"NetFlow Version 9", "ipfix": r"IPFIX"}


def rand_values(rnd):
    lo, used = {}, set()
    for r in ["RT01", "RT02", "RT03"]:
        while True:
            k = rnd.randint(1, 99)
            if k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    seg = {}
    p, q = rnd.randint(0, 254), rnd.randint(0, 253)
    seg["12"], seg["23"] = f"10.{p}.{q}", f"10.{p}.{q + 1}"
    tag = rnd.choice(["CORP", "WAN", "EDGE", "NOC", "OPS"])
    names = {"rec": f"REC-{tag}", "exp": f"EXP-{tag}", "mon": f"MON-{tag}"}
    col_net = rnd.choice(["198.51.100", "203.0.113"])
    collector = f"{col_net}.{rnd.randint(10, 250)}"
    port = rnd.choice([2055, 4739, 9995, 9996])
    ver = rnd.choice(list(VER_CFG))
    return lo, seg, names, collector, port, ver


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


def fnf_lines(faults, names, collector, port, spec_ver, wrong):
    """RT02 に焼く FNF ブロック(故障注入済み)を返す。wrong = 誤り値辞書。"""
    L = []
    # --- flow record(s) ---
    if "monitor_wrong_record" in faults:
        L += ["flow record REC-OLD",
              " description legacy record (pre-standard)",
              " match ipv4 source address",
              " match ipv4 destination address",
              " collect counter bytes", "!"]
    L.append(f"flow record {names['rec']}")
    for k in MATCH_KEYS:
        if "record_missing_key" in faults and k == wrong["missing_key"]:
            continue
        L.append(f" match {k}")
    L += [f" collect {c}" for c in COLLECTS] + ["!"]
    # --- flow exporter ---
    dest = wrong["dest"] if "exporter_wrong_dest" in faults else collector
    udp = wrong["port"] if "exporter_wrong_port" in faults else port
    L += [f"flow exporter {names['exp']}", f" destination {dest}"]
    if "exporter_wrong_source" in faults:
        L.append(f" source {IF1}")
    else:
        L.append(" source Loopback0")
    L.append(f" transport udp {udp}")
    # exporter_wrong_version: 仕様は ipfix だが既定(v9)のまま = 行を焼かない
    if "exporter_wrong_version" not in faults and spec_ver != "netflow-v9":
        L.append(f" export-protocol {VER_CFG[spec_ver]}")
    L.append("!")
    # --- flow monitor ---
    rec = "REC-OLD" if "monitor_wrong_record" in faults else names["rec"]
    L += [f"flow monitor {names['mon']}", f" record {rec}"]
    if "monitor_no_exporter" not in faults:
        L.append(f" exporter {names['exp']}")
    L.append("!")
    return L


def attach_state(faults, mon):
    """故障状態での monitor 適用点 (if_slot, direction) を返す。未適用は None。"""
    if "monitor_not_applied" in faults:
        return None
    if "apply_wrong_if" in faults:
        return (1, "input")
    if "apply_direction_output" in faults:
        return (0, "output")
    return (0, "input")


def render_rt02(lo, seg, faults, names, collector, port, spec_ver, wrong):
    L = ["! RT02 初期状態 (FNF TS・昨日 監視チームが FNF を導入した直後の状態)",
         "interface Loopback0", f" ip address {lo['RT02']} 255.255.255.255", "!"]
    L += fnf_lines(faults, names, collector, port, spec_ver, wrong)
    att = attach_state(faults, names["mon"])
    for slot, desc, ip in [(0, "to RT01 (customer traffic in)", f"{seg['12']}.2"),
                           (1, "to RT03 (upstream)", f"{seg['23']}.1")]:
        L += [f"interface {{{{ links[{slot}] }}}}", f" description === {desc} ===",
              f" ip address {ip} 255.255.255.252"]
        if att and att[0] == slot:
            L.append(f" ip flow monitor {names['mon']} {att[1]}")
        L += [" no shutdown", "!"]
    L += ["router ospf 1", f" router-id {lo['RT02']}",
          f" network {lo['RT02']} 0.0.0.0 area 0",
          f" network {seg['12']}.0 0.0.0.3 area 0",
          f" network {seg['23']}.0 0.0.0.3 area 0", "!"]
    return L


def render_edge(node, lo, seg):
    slotseg = seg["12"] if node == "RT01" else seg["23"]
    my_ip = f"{slotseg}.{1 if node == 'RT01' else 2}"
    return [f"! {node} 初期状態 (変更禁止・トラフィック{'送信元' if node == 'RT01' else '宛先'}側)",
            "interface Loopback0", f" ip address {lo[node]} 255.255.255.255", "!",
            "interface {{ links[0] }}", " description === to RT02 ===",
            f" ip address {my_ip} 255.255.255.252", " no shutdown", "!",
            "router ospf 1", f" router-id {lo[node]}",
            f" network {lo[node]} 0.0.0.0 area 0",
            f" network {slotseg}.0 0.0.0.3 area 0", "!"]


def build_fix(faults, names, collector, port, spec_ver, wrong):
    """fix 生成: ①現適用点から外す→②構造修正→③E0/0 input 適用。

    ★実機確定ルール(iol-xe 17.15, 2026-07-25):
      - flow monitor の record は上書き不可(% Failed to set record: Already there is
        an existing record ...)→ 必ず `no record` → `record <正>` の2段。
      - flow record のフィールド編集は IF から外しても解錠されない(% Object is in use)。
        monitor 側の `no record`(参照解除)が必要 → 編集後に `record <正>` で戻す。
      - ios_config は上記 % エラーを握りつぶして changed を返す(属性神隠しの FNF 版)。
      - 同一行の detach→attach はループ内 diff の stale 判定で attach が no-op になる
        → 全エントリ match: none(無条件投入)で発行する。
    """
    mon, rec, exp = names["mon"], names["rec"], names["exp"]
    N = {"match": "none"}
    fixes = []
    att = attach_state(faults, mon)
    if att:
        cur_if = IF0 if att[0] == 0 else IF1
        fixes.append({"node": "RT02", "parents": f"interface {cur_if}",
                      "lines": [f"no ip flow monitor {mon} {att[1]}"], **N})
    touches_record = ("record_missing_key" in faults) or ("monitor_wrong_record" in faults)
    if touches_record:                            # 参照解除(record 編集の解錠を兼ねる)
        fixes.append({"node": "RT02", "parents": f"flow monitor {mon}",
                      "lines": ["no record"], **N})
    if "record_missing_key" in faults:
        fixes.append({"node": "RT02", "parents": f"flow record {rec}",
                      "lines": [f"match {wrong['missing_key']}"], **N})
    if touches_record:                            # 正しい record を張り直す
        fixes.append({"node": "RT02", "parents": f"flow monitor {mon}",
                      "lines": [f"record {rec}"], **N})
    if "monitor_wrong_record" in faults:          # 参照が外れた後なら消せる
        fixes.append({"node": "RT02", "lines": ["no flow record REC-OLD"], **N})
    # export-protocol は monitor から参照中は変更不可(% Object is in use)。
    # destination/source/udp はライブ変更可という非対称(実機確定)。
    # → version 変更時のみ exporter を参照解除してから変更し、後で張り直す。
    unlink_exporter = ("exporter_wrong_version" in faults
                       and "monitor_no_exporter" not in faults)
    if unlink_exporter:
        fixes.append({"node": "RT02", "parents": f"flow monitor {mon}",
                      "lines": [f"no exporter {exp}"], **N})
    exp_lines = []
    if "exporter_wrong_dest" in faults:
        exp_lines.append(f"destination {collector}")
    if "exporter_wrong_port" in faults:
        exp_lines.append(f"transport udp {port}")
    if "exporter_wrong_source" in faults:
        exp_lines.append("source Loopback0")
    if "exporter_wrong_version" in faults:
        exp_lines.append(f"export-protocol {VER_CFG[spec_ver]}")
    if exp_lines:
        fixes.append({"node": "RT02", "parents": f"flow exporter {exp}",
                      "lines": exp_lines, **N})
    if unlink_exporter or "monitor_no_exporter" in faults:
        # exporter のパラメータ確定後に張り(直)す
        fixes.append({"node": "RT02", "parents": f"flow monitor {mon}",
                      "lines": [f"exporter {exp}"], **N})
    fixes.append({"node": "RT02", "parents": f"interface {IF0}",
                  "lines": [f"ip flow monitor {mon} input"], **N})
    return fixes


SYMPTOM = {
    "apply_direction_output":
        "コレクタに **RT03→RT01 方向のフローしか届いていない**。監視標準が求める"
        "顧客側→上流方向のフローが欠けている、と NMS チームから指摘。",
    "apply_wrong_if":
        "コレクタに**期待した方向のフローが出てこない**（逆方向とおぼしきフローは見える）、"
        "と NMS チームから指摘。",
    "monitor_not_applied":
        "コレクタにフローが**一切届かず**、機器側のフローキャッシュも**空のまま**。",
    "monitor_no_exporter":
        "機器の**フローキャッシュにはフローが見えている**のに、コレクタには"
        "**一切レコードが届かない**。",
    "monitor_wrong_record":
        "フロー自体は届くが、**フィールド構成が監視標準と異なる**（プロトコル/ポートの"
        "情報が無い、旧世代の形式に見える）と NMS チームから指摘。",
    "record_missing_key":
        "届いたレコードで**特定のフィールドが常に欠落**していると NMS チームから指摘。",
    "exporter_wrong_dest":
        "機器はエクスポートしているように見えるが、**コレクタにレコードが届かない**。",
    "exporter_wrong_port":
        "コレクタの**受信ポートにレコードが届かない**（コレクタは監視標準の"
        "ポートで待ち受けている）。",
    "exporter_wrong_source":
        "コレクタが「**未登録ソース IP からの NetFlow パケットを破棄**」と警告している。"
        "NMS はエクスポータを **Loopback0 の IP で登録**している。",
    "exporter_wrong_version":
        "コレクタが「**サポート外のエクスポート形式/バージョンのため解析不能**」と"
        "エラーを記録している。",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    ap.add_argument("--faults", type=int, choices=[1, 2], default=1)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    lo, seg, names, collector, port, spec_ver = rand_values(rnd)
    faults = pick_faults(rnd, a.faults, a.fault)
    if "exporter_wrong_version" in faults:
        spec_ver = "ipfix"                       # 既定(v9)残置を故障にするため仕様は ipfix
    wrong = {"missing_key": rnd.choice(DROPPABLE_KEYS),
             "dest": f"{collector.rsplit('.', 1)[0]}.{(int(collector.rsplit('.', 1)[1]) + 111) % 240 + 10}",
             "port": rnd.choice([p for p in [2055, 4739, 9995, 9996] if p != port])}
    diff = max(DIFFICULTY[f] for f in faults) + (1 if len(faults) == 2 else 0)
    diff = min(diff, 5)

    prob_id = f"GEN-FNFTS-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"Flexible NetFlow 監視標準 適合トラブルシュート (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["netflow", "flexible-netflow", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated",
               "target_nodes": ["RT01", "RT02", "RT03"], "points": 100, "access": "ssh",
               "lab": {"links": [
                   {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
                   {"a": "RT02", "a_if": 1, "b": "RT03", "b_if": 0}],
                   "positions": {"RT01": [-300, 0], "RT02": [0, 0], "RT03": [300, 0]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_fnf_ts.py) seed={a.seed} faults={','.join(faults)}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/initial/RT02.cfg.j2", "w", encoding="utf-8") as f:
        f.write("\n".join(render_rt02(lo, seg, faults, names, collector, port,
                                      spec_ver, wrong)) + "\n")
    for n in ["RT01", "RT03"]:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_edge(n, lo, seg)) + "\n")

    # ---- 採点 ----
    rec, exp, mon = names["rec"], names["exp"], names["mon"]
    src_rx, dst_rx = lo["RT01"].replace(".", r"\."), lo["RT03"].replace(".", r"\.")
    col_rx = collector.replace(".", r"\.")
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"},
               "checks": [
                   {"name": f"RT02: flow record {rec} の match/collect が監視標準どおり",
                    "node": "RT02", "command": f"show flow record {rec}",
                    "raw": [{"regex": f"match {k}"} for k in MATCH_KEYS] +
                           [{"regex": f"collect {c}"} for c in COLLECTS], "points": 15},
                   {"name": f"RT02: exporter {exp} の宛先 {collector} / UDP {port}",
                    "node": "RT02", "command": f"show flow exporter {exp}",
                    "raw": [{"regex": f"[Dd]estination.*{col_rx}"},
                            {"regex": f"[Dd]estination [Pp]ort:\\s+{port}"}], "points": 10},
                   {"name": f"RT02: exporter {exp} の source が Loopback0",
                    "node": "RT02", "command": f"show flow exporter {exp}",
                    "raw": [{"regex": r"[Ss]ource [Ii]nterface:\s+Loopback0"}], "points": 10},
                   {"name": f"RT02: exporter {exp} の export-protocol が {spec_ver}",
                    "node": "RT02", "command": f"show flow exporter {exp}",
                    "raw": [{"regex": f"Export protocol:\\s+{VER_SHOW[spec_ver]}"}],
                    "points": 10},
                   {"name": f"RT02: monitor {mon} が record {rec} を参照",
                    "node": "RT02", "command": f"show flow monitor {mon}",
                    "raw": [{"regex": f"[Rr]ecord.*{rec}"},
                            {"not_regex": "REC-OLD"}], "points": 10},
                   {"name": f"RT02: monitor {mon} が exporter {exp} を参照",
                    "node": "RT02", "command": f"show flow monitor {mon}",
                    "raw": [{"regex": f"[Ee]xporter.*{exp}"}], "points": 10},
                   {"name": f"RT02: {IF0} (RT01向け) の ingress に {mon} を適用",
                    "node": "RT02", "command": f"show running-config interface {IF0}",
                    "raw": [{"regex": f"ip flow monitor {mon} input"}], "points": 15},
                   {"name": "(発射) RT01→RT03 の監視対象トラフィックが疎通",
                    "node": "RT01",
                    "command": f"ping {lo['RT03']} source {lo['RT01']} repeat 10",
                    "raw": [{"regex": "Success rate is [1-9]"}], "points": 5},
                   {"name": f"効果: cache に順方向フロー(src {lo['RT01']} → dst {lo['RT03']})が採取される",
                    "node": "RT02",
                    "command": f"show flow monitor {mon} cache format table",
                    "raw": [{"regex": f"{src_rx}\\s+{dst_rx}"}], "points": 15}]}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_fnf_ts.py) seed={a.seed} faults={','.join(faults)}\n"
                "# ★cache 実効は format table の同一行 regex(src dst 隣接列)。\n"
                "#   contains 2連へ緩めると逆向きフローで偽陽性になり方向故障を検出できない。\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"faults": faults, "names": names, "collector": collector,
                   "port": port, "spec_ver": spec_ver, "wrong": wrong,
                   "loopbacks": lo, "difficulty": diff}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": build_fix(faults, names, collector, port, spec_ver, wrong)},
                  f, ensure_ascii=False, indent=2)

    # ---- task.md(仕様書突き合わせ型・故障非公開) ----
    tickets = "\n".join(f"> {i+1}. {SYMPTOM[f]}" for i, f in enumerate(faults)) \
        if len(faults) > 1 else f"> {SYMPTOM[faults[0]]}"
    task = f"""# 問題 {prob_id} : Flexible NetFlow 監視標準 適合トラブルシュート（難易度{diff}）

## 状況

中継ルータ **RT02** に、昨日 監視チームが Flexible NetFlow を導入した。
しかし NMS/コレクタ運用チームから下記のトラブルチケットが届いている。
社内の**監視標準仕様書（抜粋・下記）に完全準拠**するよう調査・是正せよ。

```
RT01(顧客側, Lo0={lo['RT01']}) ─── RT02(FNF・被疑) ─── RT03(上流側, Lo0={lo['RT03']})
                          Et0/0            Et0/1
```

## トラブルチケット

{tickets}

## 監視標準仕様書（抜粋）

RT02 で顧客側からの **入り (ingress) トラフィック**を計測しエクスポートする。

1. **flow record `{rec}`** — match キー: IPv4 送信元/宛先アドレス・IPv4 プロトコル・
   L4 送信元/宛先ポート。collect: counter bytes / counter packets。
2. **flow exporter `{exp}`** — コレクタ **`{collector}`** へ **UDP `{port}`**。
   エクスポート元は **`Loopback0`**。エクスポート形式は **`{spec_ver}`**。
3. **flow monitor `{mon}`** — 上記 record と exporter を束ねる。
4. **適用** — RT02 の **RT01 向け IF (`{IF0}`) の ingress (input)**。

## 遵守事項

- FNF の**撤去や別名での作り直しによる「復旧」は不可**（仕様書の名前・値に一致させる）。
- 設定変更は **RT02 のみ**。RT01 / RT03 は変更禁止（状態確認・ping 送信は可）。
- OSPF・アドレッシングは変更しない。
- コレクタ `{collector}` は実在しない（エクスポート先の指定のみ。動作確認はキャッシュで行う）。

## 切り分けの観点

- 原因の種類・場所・数は伏せている。仕様書と実機の状態(`show flow ...` 系)を
  突き合わせて差分を特定すること。
- 採点は設定の字面に加え、**フローキャッシュに仕様どおりのフローが採取されること**まで見る。

## アクセス・採点

SSH `SUZUKI / CCNP`（mgmt は割当順）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : faults={','.join(faults)} diff={diff} "
          f"names={names['rec']}/{names['exp']}/{names['mon']} "
          f"collector={collector}:{port} ver={spec_ver}")


if __name__ == "__main__":
    main()
