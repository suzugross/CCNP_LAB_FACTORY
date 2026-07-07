#!/usr/bin/env python3
"""L2 EtherChannel トラブルシュート問題 生成器（値・故障をランダム化）。

正準トポロジ: SW01-SW02 を 2 本（Et0/0 / Et0/1）で接続し Port-channel1(LACP/access)
にまとめ、データ VLAN の SVI 間で疎通させる。正しい構成に L2 故障を注入した初期
config を生成する。出題は症状ベース（束が組めない/疎通しない）。

採点（固定構造・値のみ可変）:
  1) SW01 Po1 が LACP up・Et0/0/Et0/1 両方 bundled
  2) SW02 同上
  3) SW01 の VLAN-SVI から SW02-SVI へ ping 成功（束＋VLAN一致の効果確認）

故障カタログ:
  passive_passive : 両機の全メンバが mode passive → 束が永遠に組まれない
  mode_on         : 片機のメンバが mode on(静的) → 動的(LACP)要件を満たさない/折衝不成立
  missing_member  : 片機の片メンバが channel-group 未投入 → 1 本しか束ねられない
  vlan_mismatch   : 片機の Po/メンバが別 access VLAN → 束は出来ても L2 分断で不通

mode 系(passive_passive/mode_on)は排他。故障は 2〜3 個をランダム選択。
収集/投入は telnet（IOL L2 は SSH 非対応）。自己検品用に solution/fix.json に
「telnet で投入する正規化手順（per-switch のコマンド列）」を出力する。

使い方: gen_l2_troubleshoot.py --repo . --seed <int> [--faults N]
"""
import argparse
import json
import os
import random

import yaml

SW = ["SW01", "SW02"]
MEMBERS = ["Ethernet0/0", "Ethernet0/1"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=0, help="0=ランダム(2〜3)")
    a = ap.parse_args()
    rnd = random.Random(a.seed)

    # ---- ランダム値 ----
    dv = rnd.choice([v for v in range(20, 200) if v != 999])      # データ VLAN
    bv = rnd.choice([v for v in range(20, 200) if v not in (dv, 999)])  # ダミー VLAN
    oct2, oct3 = rnd.randint(20, 250), rnd.randint(0, 250)
    net = f"10.{oct2}.{oct3}"
    svi = {"SW01": f"{net}.1", "SW02": f"{net}.2"}

    # ---- 故障選択 ----
    catalog = ["passive_passive", "mode_on", "missing_member", "vlan_mismatch"]
    mode_fault = rnd.choice([None, "passive_passive", "mode_on"])
    pool = ["missing_member", "vlan_mismatch"]
    rnd.shuffle(pool)
    faults = ([mode_fault] if mode_fault else []) + pool[:]
    rnd.shuffle(faults)
    want = a.faults if a.faults else rnd.choice([2, 3])
    faults = faults[:max(2, min(want, len(faults)))]
    if not faults:
        faults = ["passive_passive", "missing_member"]

    miss_sw = rnd.choice(SW)
    vlan_sw = rnd.choice(SW)
    on_sw = rnd.choice(SW)

    # ---- 正しい状態のモデル → 故障注入 ----
    def fresh(swname):
        return {"po_vlan": dv,
                "mem": {m: {"mode": "active", "cg": True, "vlan": dv} for m in MEMBERS}}
    st = {s: fresh(s) for s in SW}

    if "passive_passive" in faults:
        for s in SW:
            for m in MEMBERS:
                st[s]["mem"][m]["mode"] = "passive"
    if "mode_on" in faults:
        for m in MEMBERS:
            st[on_sw]["mem"][m]["mode"] = "on"
    if "missing_member" in faults:
        st[miss_sw]["mem"][MEMBERS[1]]["cg"] = False
    if "vlan_mismatch" in faults:
        st[vlan_sw]["po_vlan"] = bv
        for m in MEMBERS:
            st[vlan_sw]["mem"][m]["vlan"] = bv

    # ---- 初期 config(.cfg.j2) 生成 ----
    def render_initial(s):
        v = st[s]
        peer = "SW02" if s == "SW01" else "SW01"
        L = [f"! 自動生成(gen_l2_troubleshoot) 初期状態 ({s})  seed={a.seed}",
             f"vlan {dv}", f" name DATA{dv}"]
        if v["po_vlan"] != dv:
            L += [f"vlan {v['po_vlan']}", f" name BOGUS{v['po_vlan']}"]
        L += [f"interface Vlan{dv}",
              f" description === DATA{dv} SVI (test) ===",
              f" ip address {svi[s]} 255.255.255.0", " no shutdown",
              "interface Port-channel1",
              f" description === bundle to {peer} ===",
              " switchport", " switchport mode access",
              f" switchport access vlan {v['po_vlan']}"]
        for i, m in enumerate(MEMBERS):
            mm = v["mem"][m]
            L += [f"interface {{{{ links[{i}] }}}}",
                  f" description === to {peer} (member {i + 1}) ===",
                  " switchport", " switchport mode access",
                  f" switchport access vlan {mm['vlan']}"]
            if mm["cg"]:
                L.append(f" channel-group 1 mode {mm['mode']}")
            L.append(" no shutdown")
        return "\n".join(L) + "\n"

    # ---- 自己検品用 telnet 正規化手順（必ず正解状態へ）----
    def telnet_fix(s):
        lines = ["configure terminal", f"vlan {dv}", "interface Port-channel1",
                 "switchport", "switchport mode access", f"switchport access vlan {dv}"]
        for m in MEMBERS:
            lines += [f"interface {m}", "switchport", "switchport mode access",
                      f"switchport access vlan {dv}",
                      "no channel-group 1", "channel-group 1 mode active",
                      "no shutdown"]
        lines += ["end"]
        return lines

    # ---- 難易度 ----
    diff = 3 + (1 if len(faults) >= 3 else 0) + (1 if mode_fault else 0)
    diff = min(5, diff)

    prob_id = f"GEN-L2TS-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    problem = {"id": prob_id,
               "title": f"L2 EtherChannel トラブルシュート (seed={a.seed})",
               "exam": "ENCOR", "topics": ["etherchannel", "lag", "l2", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "baseline-8rt",
               "target_nodes": SW, "points": 100, "access": "telnet",
               "lab": {"links": [{"a": "SW01", "a_if": 0, "b": "SW02", "b_if": 0},
                                 {"a": "SW01", "a_if": 1, "b": "SW02", "b_if": 1}]}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_l2_troubleshoot.py) seed={a.seed} faults={len(faults)}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for s in SW:
        with open(f"{pdir}/initial/{s}.cfg.j2", "w", encoding="utf-8") as f:
            f.write(render_initial(s))

    # ---- grading.yml（LAG-TS と同構造・値のみ可変）----
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": []}
    for s in SW:
        grading["checks"].append({
            "name": f"{s}: Po1 が LACP で up・Et0/0 と Et0/1 が両方 bundled",
            "node": s, "command": "show etherchannel summary",
            "parser": "show etherchannel summary", "find": "interfaces.*",
            "match": {"protocol": "lacp", "oper_status": "up",
                      "members.Ethernet0/0.bundled": True,
                      "members.Ethernet0/1.bundled": True},
            "points": 30})
    grading["checks"].append({
        "name": f"SW01: VLAN{dv} SVI から SW02-SVI({svi['SW02']}) へ疎通する（束＋VLAN一致の効果確認）",
        "node": "SW01", "command": f"ping {svi['SW02']} source Vlan{dv} repeat 5",
        "raw": [{"regex": "Success rate is [1-9]"}], "points": 40})
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_l2_troubleshoot.py) seed={a.seed}\n")
        yaml.safe_dump(grading, f, sort_keys=False, allow_unicode=True)

    # ---- 解答（採点者専用）----
    json.dump({"telnet_fix": {s: telnet_fix(s) for s in SW},
               "faults": faults, "data_vlan": dv, "bogus_vlan": bv,
               "svi": svi, "miss_sw": miss_sw, "vlan_sw": vlan_sw, "on_sw": on_sw},
              open(f"{pdir}/solution/fix.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # ---- task.md（症状ベース・故障は伏せる）----
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(f"# 障害対応 {prob_id} : EtherChannel（束が組めない / 疎通しない）\n\n")
        f.write("## 状況\nSW01–SW02 間の 2 本の物理リンク（`Ethernet0/0` / `Ethernet0/1`）を "
                f"**Port-channel1 に束ね**、データ VLAN{dv} を流す設計です。"
                "構築作業の後、**束が正しく形成されず、通信もできない**との申告が上がっています。\n\n")
        f.write("## 受付チケット\n")
        f.write(f"> 「SW01 と SW02 の **VLAN{dv} SVI 間（`{svi['SW01']}` ⇔ `{svi['SW02']}`）"
                "で ping が通らない**。Port-channel1 を見ても 2 本がうまく束ねられていないようだ。」\n>\n")
        f.write("> 切り分けて原因を特定し、恒久的に復旧してください。**原因は 1 か所とは限りません。**\n\n")
        f.write("## 構成台帳\n| 機器 | 管理IP(telnet) | SVI |\n|---|---|---|\n")
        f.write(f"| SW01 | 10.1.10.11 | `{svi['SW01']}/24` |\n")
        f.write(f"| SW02 | 10.1.10.12 | `{svi['SW02']}/24` |\n\n")
        f.write("- 束ねは **両端が動的にネゴシエーションして確立する方式（LACP）** とすること。\n\n")
        f.write("## 完了条件\n"
                "1. Port-channel1 が **LACP で up**し、**`Et0/0`・`Et0/1` 両方が bundled**（SW01・SW02 とも）。\n"
                f"2. **VLAN{dv} SVI 間（`{svi['SW01']}` ⇔ `{svi['SW02']}`）の ping が成功**すること。\n\n")
        f.write("## ログイン（telnet）/ 採点\n```\n")
        f.write("telnet 10.1.10.11   # SW01（user SUZUKI / pass CCNP）\n")
        f.write("telnet 10.1.10.12   # SW02\n")
        f.write(f"ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')\n")
        f.write("```\n> 起点：`show etherchannel summary` / `show lacp neighbor` / `show interfaces status`。"
                "管理 VLAN(999) には触れないこと。\n")

    print(f"wrote problems/{prob_id}: faults={faults} vlan={dv}/{bv} net={net}")


if __name__ == "__main__":
    main()
