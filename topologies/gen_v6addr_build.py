#!/usr/bin/env python3
"""IPv6 自動アドレッシング 構築問 生成器（BL-153・GEN-V6BUILD・要件書駆動）。

gen_v6addr_ts.py（BL-149 TS 生成器）の反転: 同じ盤面（board=fhs 相当・8 ノード）を
**土台だけ**の状態で渡し、要件書どおりに RT01（DHCPv6 サーバ）/RT02（GW・RA・リレー）/
端末（CLA・CLB）/SWB（First-Hop Security）を組ませる。要件（世界×FHS 方式）を seed で
抽選するため、同じ盤面でも要件書が違えば正解 config が全部変わる（=ラボの顔が変わる）。

  RT01(サーバ, Lo0) ─core─ RT02(GW) ─LAN-A(点対点)─ CLA
                                  └─LAN-B─ Et0/0[SWB=ioll2]Et0/1─ CLB / Et0/2─ ROG(不正 RA+DHCPv6・変更不可)

要件軸:
  LAN-A の世界 ∈ {W_SO, W_M, W_MA, W_S, W_MP} / LAN-B の世界 ∈ {W_SO, W_M, W_MA, W_S}（相異なる）
  FHS 方式 ∈ {role（ポート役割）, prefix（許可プレフィックスリスト）}
採点: TS 生成器の挙動採点（lan_checks）＋ LAN-B の供給源正当性＋ SWB ガード有効＋方式指紋
      （device-tracking counters の drop 理由）＋ ROG/ポート無改変。telnet 収集（SWB は SSH 不可）。
模範解: solution/fix_console.json（fix_console.py 形式・全ノード）。
使い方: gen_v6addr_build.py --repo . --seed <int> [--method role|prefix]
"""
import argparse
import importlib.util
import json
import os
import random
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("gen_v6addr_ts", os.path.join(HERE, "gen_v6addr_ts.py"))
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

METHODS = ["role", "prefix"]
B_WORLDS = [w for w in T.WORLDS if w != "W_MP"]     # LAN-B は RT02 の RA が要る（正当性採点）


def links_to_if(lines):
    return [re.sub(r"\{\{ links\[(\d)\] \}\}", lambda m: f"Ethernet0/{m.group(1)}", l) for l in lines]


def build_values(rnd, method):
    v = T.rand_values(rnd)
    wa = rnd.choice(T.WORLDS)
    wb = rnd.choice([w for w in B_WORLDS if w != wa])
    v["lans"] = [
        {"name": "A", "pfx": v["lanA"], "world": wa, "gw_slot": 1, "client": "CLA", "pool": "POOL-A"},
        {"name": "B", "pfx": v["lanB"], "world": wb, "gw_slot": 2, "client": "CLB", "pool": "POOL-B",
         "multiaccess": True},
    ]
    v["bad"] = f"2001:DB8:{v['site']}:BAD"
    v["evil_dns"] = f"2001:DB8:{v['site']}:BAD::53"
    v["evil_dom"] = rnd.choice(["evil.example", "guest.local", "test-lab.internal"])
    v["vlan"] = rnd.choice([10, 20, 30, 100, 110, 200])
    v["method"] = method if method in METHODS else rnd.choice(METHODS)
    return v


# ---- 初期状態（土台のみ） ---------------------------------------------------
def init_rt01(v):
    return ["! RT01 初期状態 (DHCPv6 サーバ予定機・土台のみ: Lo0/コア IF/LAN 宛の戻り経路)",
            "ipv6 unicast-routing", "ipv6 cef", "!",
            "interface Loopback0", f" ipv6 address {v['slo']}/128", "!",
            "interface {{ links[0] }}", " description === to RT02 (core) ===",
            f" ipv6 address {v['core']}::1/64", " no shutdown", "!",
            f"ipv6 route {v['lanA']}::/64 {v['core']}::2",
            f"ipv6 route {v['lanB']}::/64 {v['core']}::2", "!"] + T.TELNET_VTY


def init_rt02(v):
    L = ["! RT02 初期状態 (ゲートウェイ予定機・土台のみ: IF アドレス/サーバ Lo0 宛経路)",
         "ipv6 unicast-routing", "ipv6 cef", "!",
         "interface {{ links[0] }}", " description === to RT01 (core) ===",
         f" ipv6 address {v['core']}::2/64", " no shutdown", "!"]
    for lan in v["lans"]:
        L += [f"interface {{{{ links[{lan['gw_slot']}] }}}}",
              f" description === LAN-{lan['name']} ===",
              f" ipv6 address {lan['pfx']}::1/64"]
        if lan["world"] == "W_MP":
            L.append(" ipv6 address FE80::1 link-local")     # 要件書に明記（土台）
        L += [" no shutdown", "!"]
    L += [f"ipv6 route 2001:DB8:{v['site']}:1::/64 {v['core']}::1", "!"] + T.TELNET_VTY
    return L


def init_client(lan):
    return [f"! {lan['client']} 初期状態 (LAN-{lan['name']} の端末・土台のみ: IF は up・IPv6 未設定)",
            "ipv6 unicast-routing", "ipv6 cef", "!",
            "interface {{ links[0] }}", f" description === to LAN-{lan['name']} ===",
            " no shutdown", "!"] + T.TELNET_VTY


def init_swb(v):
    vl = v["vlan"]
    L = ["! SWB 初期状態 (LAN-B アクセススイッチ・土台のみ: VLAN/アクセスポート・FHS 未設定)",
         f"vlan {vl}", " name LAN-B", "!"]
    for p, desc in (("{{ links[0] }}", "to RT02 (LAN-B GW)"), ("{{ links[1] }}", "to CLB (host)"),
                    ("{{ links[2] }}", "to ROG (other-dept device)")):
        L += [f"interface {p}", f" description === {desc} ===", " switchport",
              " switchport mode access", f" switchport access vlan {vl}", " no shutdown", "!"]
    return L


# ---- 模範解（fix_console.py 形式） --------------------------------------------
def solution(v):
    # ★投入順が重要: SWB(ガード)を最初に入れないと、端末の bounce が ROG の DHCPv6 情報を
    #   再学習して 24h キャッシュする(実測: 順序誤りで 93 点)。fix_console は dict 順に投入する。
    sol = {"SWB": None}
    # RT01: プール＋automatic bind（2 LAN が DHCPv6 なら named は不成立＝隠し罠）
    rt01 = [l for l in T.render_rt01(v, []) if not l.startswith("!")]
    sol["RT01"] = {"config": links_to_if(rt01)}
    rt02 = []
    for lan in v["lans"]:
        rt02 += [f"interface Ethernet0/{lan['gw_slot']}"] + T.ra_lines(v, lan, [])
    sol["RT02"] = {"config": rt02}
    for lan in v["lans"]:
        cl = [l for l in T.render_client(v, lan, []) if not l.startswith("!")]
        sol[lan["client"]] = {"config": links_to_if(cl)}
    vl = v["vlan"]
    if v["method"] == "role":
        sw = ["ipv6 nd raguard policy RAG-HOST", " device-role host",
              "ipv6 nd raguard policy RAG-UPLINK", " device-role router",
              "ipv6 dhcp guard policy DHG-CLIENT", " device-role client",
              "ipv6 dhcp guard policy DHG-SERVER", " device-role server",
              "interface Ethernet0/0", " ipv6 nd raguard attach-policy RAG-UPLINK",
              " ipv6 dhcp guard attach-policy DHG-SERVER",
              "interface Ethernet0/1", " ipv6 nd raguard attach-policy RAG-HOST",
              " ipv6 dhcp guard attach-policy DHG-CLIENT",
              "interface Ethernet0/2", " ipv6 nd raguard attach-policy RAG-HOST",
              " ipv6 dhcp guard attach-policy DHG-CLIENT"]
    else:
        sw = [f"ipv6 prefix-list RA-OK seq 10 permit {v['lanB']}::/64",
              "ipv6 nd raguard policy RAG-PL", " device-role router",
              " match ra prefix-list RA-OK",
              "ipv6 dhcp guard policy DHG-CLIENT", " device-role client",
              "ipv6 dhcp guard policy DHG-SERVER", " device-role server",
              f"vlan configuration {vl}", " ipv6 nd raguard attach-policy RAG-PL",
              "interface Ethernet0/0", " ipv6 dhcp guard attach-policy DHG-SERVER",
              "interface Ethernet0/1", " ipv6 dhcp guard attach-policy DHG-CLIENT",
              "interface Ethernet0/2", " ipv6 dhcp guard attach-policy DHG-CLIENT"]
    sol["SWB"] = {"config": sw}
    # 端末は ROG の情報を 24h キャッシュ → 模範解でも最後に bounce（SWB 適用後）
    sol["CLB"]["config"] += ["interface Ethernet0/0", " shutdown", " no shutdown"]
    return sol


# ---- 採点 --------------------------------------------------------------------
def grading(v, prob_id):
    checks = []
    checks += T.lan_checks(v, v["lans"][0])
    checks += T.lan_checks(v, v["lans"][1])
    checks.append({
        "name": "LAN-B: 未認可の高優先ルータ広告が端末に届いていない (正規 GW のみ)",
        "node": "CLB", "command": "show ipv6 routers",
        "raw": [{"not_regex": r"Preference=High"}, {"regex": r"Preference=Medium"}], "points": 10})
    checks.append({
        "name": "LAN-B: 端末に偽プレフィックスのアドレスが無い",
        "node": "CLB", "command": "show ipv6 interface brief Ethernet0/0",
        "raw": [{"not_regex": T.rx(v["bad"]) + ":"}], "points": 6})
    checks.append({
        "name": "SWB: RA Guard が有効 (ポリシーが適用されている)",
        "node": "SWB", "command": "show device-tracking policies",
        "raw": [{"regex": r"(?m)^.+\s(PORT|VLAN)\s+\S+\s+RA guard"}], "points": 6})
    checks.append({
        "name": "SWB: DHCPv6 Guard が有効 (ポリシーが適用されている)",
        "node": "SWB", "command": "show device-tracking policies",
        "raw": [{"regex": r"(?m)^.+\s(PORT|VLAN)\s+\S+\s+DHCP Guard"}], "points": 6})
    # 方式指紋: ROG の RA(30 秒周期)が「どの検証で」落ちているか（counters の理由行）
    reason = (r"Message unauthorized on port" if v["method"] == "role"
              else r"Unauthorized prefix in prefix list")
    label = "ポート役割方式" if v["method"] == "role" else "許可プレフィックスリスト方式"
    checks.append({
        "name": f"SWB: 要件どおりの方式({label})で不正 RA が遮断されている (drop 理由の指紋)",
        # ★`counters all`= ポート/VLAN どちらのスコープに attach しても drop が載る唯一の形
        #   (interface 指定はポートポリシー無しだと `% no ipv6 snooping policy attached`・
        #    vlan 指定は VLAN ポリシー無しだと同様に空 → 実出題 48213 で VLAN スコープ解が誤FAIL)。
        "node": "SWB", "command": "show device-tracking counters all",
        # 理由行は RA guard ブロック内の何行目でもよい（方式を切り替えた履歴が残っても可）。
        # ※DHCPv6 応答の drop 指紋は採らない: 端末が問い合わせた時だけ計上され(24h 周期/bounce)、
        #   W_S(O=0) では発生しない＝正解でも FAIL し得るため。ガード有効性はポリシー適用で見る。
        "raw": [{"regex": r"RA guard:[\s\S]*?reason:\s+" + reason}],
        "points": 8})
    checks.append({
        "name": "SWB: ROG 接続ポートが稼働中 (ポート閉塞による解決は不可)",
        "node": "SWB", "command": "show interfaces status",
        "raw": [{"regex": r"(?m)^Et0/2\s+.*\sconnected\s"}], "points": 6})
    checks.append({
        "name": "ROG: 他部署機器が無改変 (RA/DHCPv6 設定と IF が初期状態のまま)",
        "node": "ROG", "command": "show running-config interface Ethernet0/0",
        "raw": [{"regex": r"ipv6 nd router-preference High"}, {"regex": r"ipv6 dhcp server GUEST"},
                {"not_regex": r"(?m)^\s*shutdown"}, {"not_regex": r"ra suppress"}], "points": 6})
    for c in checks:
        for cond in c.get("raw", []):
            for k in ("regex", "not_regex"):
                if k in cond and not cond[k].startswith("(?i)"):
                    cond[k] = "(?i)" + cond[k]
    raw_total = sum(c["points"] for c in checks)
    acc = 0
    for c in checks[:-1]:
        c["points"] = round(c["points"] * 100 / raw_total)
        acc += c["points"]
    checks[-1]["points"] = 100 - acc
    return {"problem": prob_id, "total_points": 100, "defaults": {"genie_os": "iosxe"}, "checks": checks}


# ---- 要件書（task.md） ---------------------------------------------------------
def lan_spec(v, lan):
    """LAN ごとの要件（端末の振る舞い・GW の広告・サーバ）を仕様書調で。コマンドは書かない。"""
    w, n, pfx = lan["world"], lan["name"], lan["pfx"]
    cl = lan["client"]
    common_gw = f"- 端末 {cl} の既定ゲートウェイは RT02 とし、`{v['slo']}` に到達できること。"
    if w == "W_SO":
        return [f"- 端末 {cl} は、RT02 のルータ広告に基づいて **グローバルアドレスを自動生成**する。",
                f"- **DNS サーバおよびドメイン名は中央の DHCPv6 サーバ（RT01）から取得**する。"
                f"RT01 はこの LAN の端末にアドレスを割り当ててはならない（アドレスは自動生成のみ）。",
                common_gw]
    if w == "W_M":
        return [f"- 端末 {cl} は、**グローバルアドレスを中央の DHCPv6 サーバ（RT01）から取得**する"
                f"（サーバ管理・`{pfx}::/64` から割当）。",
                f"- この LAN では **端末による自動生成アドレスを併存させてはならない**"
                f"（RT02 の広告で自動生成を抑止すること）。",
                f"- DNS サーバおよびドメイン名も RT01 から配布する。",
                common_gw]
    if w == "W_MA":
        return [f"- 端末 {cl} は、**グローバルアドレスを中央の DHCPv6 サーバ（RT01）から取得**する"
                f"（サーバ管理・`{pfx}::/64` から割当）。",
                f"- 端末が RT02 の広告に基づいて自動生成したアドレスが**併存してもよい**。",
                f"- DNS サーバおよびドメイン名も RT01 から配布する。",
                common_gw]
    if w == "W_S":
        return [f"- 端末 {cl} は、RT02 のルータ広告に基づいて **グローバルアドレスを自動生成**する。",
                f"- **DNS サーバはルータ広告で端末に通知**する。この LAN では **DHCPv6 を一切使用しない**"
                f"（RT01 のプール・RT02 のリレーとも設けないこと）。",
                common_gw]
    # W_MP
    return [f"- この LAN では **セキュリティ方針により RT02 のルータ広告を停止**する"
            f"（定期広告・要請応答とも）。**RA を有効化してはならない。**",
            f"- 端末 {cl} は、**グローバルアドレスを中央の DHCPv6 サーバ（RT01）から取得**する"
            f"（サーバ管理・`{pfx}::/64` から割当）。DNS サーバおよびドメイン名も RT01 から配布する。",
            f"- 端末 {cl} の既定ゲートウェイは **静的に設定**する。RT02 の当該インタフェースの"
            f"リンクローカルアドレスは `FE80::1` に固定済み（土台）であり、端末の既定経路はこれを"
            f"指すこと。`{v['slo']}` に到達できること。"]


def task(v, prob_id, diff):
    la, lb = v["lans"]
    if v["method"] == "role":
        sec = ("- 保護は **ポートの役割に基づいて**行う。端末が接続されるアクセスポート"
               "（CLB・ROG のポート）では、**ルータ広告および DHCPv6 サーバ応答を一切通さない**。"
               "RT02 が接続されるポートのみ、それらを許可する。")
    else:
        sec = ("- 保護は **許可プレフィックスリストに基づいて**行う。LAN-B の正規プレフィックス"
               f"（`{v['lanB']}::/64`）を広告するルータ広告のみを VLAN 全体で許可し、それ以外の"
               "プレフィックスを含むルータ広告はどのポートから届いても遮断する。DHCPv6 サーバ応答は、"
               "RT02 が接続されるポート以外からは通さない。")
    A = "\n".join(lan_spec(v, la))
    B = "\n".join(lan_spec(v, lb))
    return f"""# 問題 {prob_id} : IPv6 自動アドレッシング 構築（要件書駆動・難易度{diff}）

## シナリオ

あなたは、ある企業のネットワーク管理者です。新設拠点の IPv6 アドレッシング基盤を、
下記の **要件書** に従って構築してください。中央のルータ **RT01** を DHCPv6 サーバ、
**RT02** を各 LAN のデフォルトゲートウェイとします。**LAN-B はアクセススイッチ SWB を介した
共有セグメント**で、利用者端末 **CLB** のほか、**他部署が管理する機器 ROG** も接続されて
います。ROG は他部署の業務に使用中であり、あなたの部署には設定変更の権限がありません。
また、ROG の接続ポートを閉塞することも業務上認められていません。

各機器には **土台（インタフェースアドレス・Loopback・コア間の静的経路・SWB の VLAN と
アクセスポート）だけ**が設定済みです。要件書に記載のない事項は、要件を満たす範囲で
あなたが決めてよいものとします。

## トポロジ

```
   RT01 (DHCPv6 サーバ, Lo0={v['slo']})
     │ {v['core']}::/64  (core)   RT01={v['core']}::1 / RT02={v['core']}::2
   RT02 (GW)
     ├─ {la['pfx']}::/64  LAN-A ── CLA
     └─ {lb['pfx']}::/64  LAN-B ── Et0/0 [SWB] Et0/1 ── CLB（端末）
                                          Et0/2 ── ROG（他部署機器）
```
RT02 の LAN 側アドレスは各 LAN の `::1`。SWB のアクセスポートはすべて VLAN {v['vlan']}（LAN-B）。

## 要件書

### 1. LAN-A（{T.WORLD_LABEL[la['world']]}）
{A}

### 2. LAN-B（{T.WORLD_LABEL[lb['world']]}）
{B}

### 3. DHCPv6 サーバ
- DHCPv6 の機能は **RT01 に集約**し、RT02 は各 LAN の要求を RT01 へ中継する（DHCPv6 を使う LAN のみ）。
- 配布する **DNS サーバは `{v['dns']}`**、DHCPv6 を使う LAN では **ドメイン名 `{v['dom']}`** も配布する。
- RT01 が DHCPv6 を提供するインタフェースは **コア側（RT02 向け）の 1 つのみ**とする。

### 4. LAN-B のセキュリティ（First-Hop Security）
- LAN-B では、**正規のゲートウェイ RT02 以外のルータ広告および DHCPv6 応答が端末に届いて
  はならない**。この保護は **アクセススイッチ SWB で実施**し、ROG 以外の機器が別のアクセス
  ポートに接続された場合にも有効であること。
{sec}

### 5. 制約
- **ROG は変更禁止**（他部署管理）。**SWB のポートを shutdown することも禁止**。
- 各機器の **インタフェースアドレス・Loopback0・土台の静的経路は変更しない**こと。
- 端末（CLA・CLB）の IPv6 設定は、それぞれの LAN の要件を満たす **最小限**の設定とする。
- 端末は、構築の途中で受け取った古い情報（既定ゲートウェイ・DNS 等）を保持している
  ことがある。構築完了後、端末のインタフェースを shutdown / no shutdown して再取得させてよい。

## アクセス・採点

telnet/SSH `SUZUKI / CCNP`（mgmt は割当順・**SWB は telnet のみ**）または CML コンソール。
```
scripts/lab.sh grade {prob_id}
```
> 採点では、各 LAN の端末の状態（アドレスの取得方法・DNS・`{v['slo']}` への実疎通）、
> RT02 の広告方針、LAN-B の供給源の正当性と保護方式、および ROG・ポートの無改変を確認します。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--method", choices=METHODS, default=None)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    v = build_values(rnd, a.method)
    wa, wb = v["lans"][0]["world"], v["lans"][1]["world"]
    diff = 4 + (1 if ("W_MP" in (wa, wb) or "W_M" in (wa, wb) or v["method"] == "prefix") else 0)

    prob_id = f"GEN-V6BUILD-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {
        "id": prob_id,
        "title": f"IPv6 自動アドレッシング 構築 (要件書駆動・seed={a.seed})",
        "exam": "ENARSI",
        # security タグで services(ipv6/dhcpv6/slaac)との同数タイを破り、ノルマの security 枠に数える
        "topics": ["ipv6", "dhcpv6", "slaac", "ra", "first-hop-security", "ra-guard",
                   "dhcpv6-guard", "security", "build", "generated"],
        "difficulty": diff, "topology": "generated",
        "target_nodes": ["RT01", "RT02", "CLA", "CLB", "ROG", "SWB"],
        "points": 100, "access": "telnet", "bringup_data_ifs": True,
        "bringup_nodes": ["RT01", "RT02", "CLA", "CLB", "ROG"],
        "lab": {"links": [
            {"a": "RT01", "a_if": 0, "b": "RT02", "b_if": 0},
            {"a": "RT02", "a_if": 1, "b": "CLA", "b_if": 0},
            {"a": "RT02", "a_if": 2, "b": "SWB", "b_if": 0},
            {"a": "CLB", "a_if": 0, "b": "SWB", "b_if": 1},
            {"a": "ROG", "a_if": 0, "b": "SWB", "b_if": 2}],
            "positions": {"RT01": [-320, -140], "RT02": [0, 0], "SWB": [200, 160],
                          "CLA": [320, -200], "CLB": [400, 80], "ROG": [400, 260]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_build.py) seed={a.seed} worlds=A:{wa},B:{wb} "
                f"method={v['method']}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    renders = {"RT01": init_rt01(v), "RT02": init_rt02(v),
               "CLA": init_client(v["lans"][0]), "CLB": init_client(v["lans"][1]),
               "ROG": T.render_rog_fhs(v), "SWB": init_swb(v)}
    for node, lines in renders.items():
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_v6addr_build.py) seed={a.seed} worlds=A:{wa},B:{wb} method={v['method']}\n"
                "# telnet 収集。挙動採点(TS と同型)+LAN-B 供給源正当性+FHS 方式指紋+ROG/ポート無改変。\n")
        yaml.safe_dump(grading(v, prob_id), f, sort_keys=False, allow_unicode=True)
    meta = {"worlds": {"A": wa, "B": wb}, "method": v["method"], "difficulty": diff,
            "site": v["site"], "core": v["core"], "lanA": v["lanA"], "lanB": v["lanB"],
            "bad": v["bad"], "vlan": v["vlan"], "slo": v["slo"], "dns": v["dns"], "dom": v["dom"],
            "evil_dns": v["evil_dns"], "evil_dom": v["evil_dom"]}
    with open(f"{pdir}/solution/spec.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix_console.json", "w", encoding="utf-8") as f:
        json.dump(solution(v), f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task(v, prob_id, diff))
    print(f"wrote problems/{prob_id} : worlds=A:{wa},B:{wb} method={v['method']} diff={diff} "
          f"site={v['site']} vlan={v['vlan']}")


if __name__ == "__main__":
    main()
