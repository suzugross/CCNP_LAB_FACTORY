#!/usr/bin/env python3
"""再配送リング×AD反転による定常ルーティングループ生成器（Ping-t #28776 ファミリ）。

正準トポロジ(4台・値を seed ランダム化・ENARSI-REDIST-BGP-LOOP-01 を一般化):
  RE ──(BGP iBGP)── RC ──(EIGRP AS100)── RA
                     │                     │
                     └────(OSPF area0)──── RB
  BGP AS65000 = {RE(起点 192.168.51.0/24), RC}
  EIGRP AS100 = {RC, RA}
  OSPF area0  = {RC, RA, RB}
  RA は EIGRP⇄OSPF を完全相互再配送(両変種で共通)。RE/RB も共通。
  変種で変わるのは **RC が被害プレフィクスをどのIGPへ注入するか**(＝リングの回り方)だけ。

ループの核心(全変種共通): 被害プレフィクス 192.168.51.0/24 は RE が BGP 起点広告し、
  RC が iBGP(AD200)で学習する。再配送が「リング」を成すため出自が一周して RC に戻り、
  戻り経路の AD が iBGP(200)より低いので RC がそれを優先→ RC を含む3台の定常転送ループ。
  RC は RIB 勝者を再配送源にするので、注入先IGPと戻り先IGPの両方を RC で再配送し
  (bgp＋戻りIGP の二重再配送)、P を常時循環させて **振動でなく定常ループに固定**する。
  是正: RC で BGP の AD を戻り経路の AD 未満に下げる(distance bgp)。別解=戻り側の外部AD>200。
  ★distance 変更は既存経路に即反映されないため clear ip route * が必要。

変種(--variant, 既定 seed ランダム):
  ad_ospf : iBGP(200) が戻り O E2(110) に負ける。リング BGP→EIGRP→OSPF。ループ RC→RB→RA→RC。
            RC は BGP を EIGRP へ注入(＋ospf→eigrp 保持)。RC の被害経路は "ospf 1 extern 2"。
            是正= distance bgp 20 105 105(iBGP<110) 別解= distance ospf external 205。
  ad_eigrp: iBGP(200) が戻り D EX(170) に負ける(僅差)。リング BGP→OSPF→EIGRP。ループ RC→RA→RB→RC。
            RC は BGP を OSPF へ注入(＋eigrp→ospf 保持)。RC の被害経路は "eigrp 100 external"。
            是正= distance bgp 20 165 165(iBGP<170) 別解= distance eigrp 90 201。

採点: netmodel 大域不変条件 reachability_all(30)/loop_free(25)/optimal(15,被害prefix宛)
  ＋checks: RC が是正後 bgp 学習(10)/RE が IGP側 Lo を B 学習(10)/RB が O E2 でP保持=リング維持(5)/
  RC static 不在(5)。
出力: problems/GEN-REDISTLOOP-<seed>/ {problem.yml, params/, initial/*.cfg.j2, grading.yml.j2,
       task.md.j2, solution.json, solution.md}。既存 build/grade/solve パイプライン互換。
使い方: gen_redist_loop_ts.py --repo . --seed <int> [--variant ad_ospf|ad_eigrp]
"""
import argparse
import json
import os
import random

import yaml

P_NET = "192.168.51"                 # 被害プレフィクス(RE Lo0=.1/24, network 広告)
EIGRP_METRIC = "100000 100 255 1 1500"
NODES = ["RE", "RC", "RA", "RB"]

# 変種メタ: RC のIGP再配送配置と是正/指紋/難易度のみが変わる。
VARIANTS = {
    "ad_ospf": {
        "difficulty": 5,
        "ring": "BGP → EIGRP → OSPF",
        "loop_path": "RC → RB → RA → RC",
        "victim_src": 'ospf 1',           # 破損時 RC の P 学習元
        "victim_word": "OSPF 外部(O E2・AD 110)",
        "return_ad": 110,
        # RC が BGP を EIGRP へ注入(＋ospf→eigrp で常時循環)。OSPF側は素。
        "rc_eigrp_extra": ["redistribute bgp 65000 metric " + EIGRP_METRIC,
                           "redistribute ospf 1 metric " + EIGRP_METRIC],
        "rc_ospf_extra": [],
        "method": "distance",
        "fix_line": "distance bgp 20 105 105",
        "fix_alt": "distance ospf external 205",
        # 被害prefix宛の最短が決定的な組(RA は EIGRP 直結で RC 経由=2ホップ最短)。
        "opt_pairs": [["RC", "RE"], ["RA", "RE"], ["RB", "RC"], ["RC", "RB"]],
    },
    "ad_eigrp": {
        "difficulty": 5,
        "ring": "BGP → OSPF → EIGRP",
        "loop_path": "RC → RA → RB → RC",
        "victim_src": 'eigrp 100',
        "victim_word": "EIGRP 外部(D EX・AD 170)",
        "return_ad": 170,
        # RC が BGP を OSPF へ注入(＋eigrp→ospf で常時循環)。EIGRP側は素。
        "rc_eigrp_extra": [],
        "rc_ospf_extra": ["redistribute bgp 65000 subnets",
                          "redistribute eigrp 100 subnets"],
        "method": "distance",
        "fix_line": "distance bgp 20 165 165",
        "fix_alt": "distance eigrp 90 201",
        # RA は P を OSPF 経由(RB 経由)でしか学習しないため RA->RE は構造上 3 ホップ→除外。
        "opt_pairs": [["RC", "RE"], ["RB", "RC"], ["RC", "RB"]],
    },
    # 同じリング(BGP→EIGRP→OSPF)・同じループだが、会社ポリシーで管理距離の変更を禁止する変種。
    # → distance 系が封じられ、解法は「戻り経路を RC の RIB 学習段でフィルタ遮断」(distribute-list in)。
    #   AD 調整とは別カテゴリの解法(フィルタリング)を要求する。難易度は同5だが要求スキルが変わる。
    "filter_ospf": {
        "difficulty": 5,
        "ring": "BGP → EIGRP → OSPF",
        "loop_path": "RC → RB → RA → RC",
        "victim_src": 'ospf 1',
        "victim_word": "OSPF 外部(O E2・AD 110)",
        "return_ad": 110,
        "rc_eigrp_extra": ["redistribute bgp 65000 metric " + EIGRP_METRIC,
                           "redistribute ospf 1 metric " + EIGRP_METRIC],
        "rc_ospf_extra": [],
        "method": "filter",
        # フィルタ解: 被害プレフィクスの「戻り(O E2)」を RC の OSPF 学習で遮断→ RC は iBGP を採用。
        # LSDB は無傷なので RB 側の到達性は維持される。distance は一切変えない。
        "fix_blocks": [
            {"parents": None, "lines":
                [f"ip prefix-list DENY_FEEDBACK seq 5 deny {P_NET}.0/24",
                 "ip prefix-list DENY_FEEDBACK seq 10 permit 0.0.0.0/0 le 32"]},
            {"parents": "router ospf 1", "lines": ["distribute-list prefix DENY_FEEDBACK in"]}],
        "opt_pairs": [["RC", "RE"], ["RA", "RE"], ["RB", "RC"], ["RC", "RB"]],
    },
}


def rand_values(rnd):
    """loopbacks(RC/RA/RB) と /30 セグメント(ec/ca/cb/ab)。p_net/AS/AD は固定。"""
    used, lo = set(), {}
    for r in ["RC", "RA", "RB"]:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    useg, seg = set(), {}
    for name in ["ec", "ca", "cb", "ab"]:
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in useg:      # mgmt 10.1.10 回避
                useg.add((p, q)); seg[name] = f"10.{p}.{q}"; break
    return lo, seg


# --------------------------------------------------------------------------
# 各ノードの初期 config（{{ links[n] }} と params は build 時に描画）
# --------------------------------------------------------------------------
def render_node(node, var):
    v = VARIANTS[var]
    if node == "RE":
        return [
            "! GEN-REDISTLOOP 初期 RE : BGP AS65000 起点(192.168.51.0/24 を広告)",
            "interface Loopback0",
            f" ip address {P_NET}.1 255.255.255.0", "!",
            "interface {{ links[0] }}",
            " ip address {{ params.seg_ec }}.1 255.255.255.252", " no shutdown", "!",
            "router bgp 65000",
            f" bgp router-id {P_NET}.1", " bgp log-neighbor-changes",
            f" network {P_NET}.0 mask 255.255.255.0",
            " neighbor {{ params.seg_ec }}.2 remote-as 65000", "!"]
    if node == "RB":
        return [
            "! GEN-REDISTLOOP 初期 RB : OSPF area0 内部(PC4 サイト相当)",
            "interface Loopback0",
            " ip address {{ params.rb_lo }} 255.255.255.255", "!",
            "interface {{ links[0] }}",
            " ip address {{ params.seg_cb }}.2 255.255.255.252", " no shutdown", "!",
            "interface {{ links[1] }}",
            " ip address {{ params.seg_ab }}.2 255.255.255.252", " no shutdown", "!",
            "router ospf 1", " router-id {{ params.rb_lo }}",
            " network {{ params.rb_lo }} 0.0.0.0 area 0",
            " network {{ params.seg_cb }}.0 0.0.0.3 area 0",
            " network {{ params.seg_ab }}.0 0.0.0.3 area 0", "!"]
    if node == "RA":
        # RA は両変種共通: EIGRP⇄OSPF 完全相互再配送(リング中継＋戻り経路)。
        return [
            "! GEN-REDISTLOOP 初期 RA : EIGRP AS100 ⇄ OSPF area0 完全相互再配送(リング中継)",
            "interface Loopback0",
            " ip address {{ params.ra_lo }} 255.255.255.255", "!",
            "interface {{ links[0] }}",
            " ip address {{ params.seg_ca }}.2 255.255.255.252", " no shutdown", "!",
            "interface {{ links[1] }}",
            " ip address {{ params.seg_ab }}.1 255.255.255.252", " no shutdown", "!",
            "router eigrp 100",
            " network {{ params.seg_ca }}.0 0.0.0.3", " no auto-summary",
            f" redistribute ospf 1 metric {EIGRP_METRIC}", "!",
            "router ospf 1", " router-id {{ params.ra_lo }}",
            " network {{ params.ra_lo }} 0.0.0.0 area 0",
            " network {{ params.seg_ab }}.0 0.0.0.3 area 0",
            " redistribute eigrp 100 subnets", "!"]
    # RC : 変種で IGP 注入先だけが変わる被害/震源ルータ。
    L = [
        "! GEN-REDISTLOOP 初期 RC : 被害ルータ(BGP iBGP + EIGRP + OSPF)",
        f"!   ★変種={var} : リング {v['ring']} で 192.168.51.0/24 の出自が一周して戻り",
        f"!     戻り経路(AD {v['return_ad']}) が iBGP(200) に勝ち {v['loop_path']} のループ。",
        "interface Loopback0",
        " ip address {{ params.rc_lo }} 255.255.255.255", "!",
        "interface {{ links[0] }}",
        " ip address {{ params.seg_ec }}.2 255.255.255.252", " no shutdown", "!",
        "interface {{ links[1] }}",
        " ip address {{ params.seg_ca }}.1 255.255.255.252", " no shutdown", "!",
        "interface {{ links[2] }}",
        " ip address {{ params.seg_cb }}.1 255.255.255.252", " no shutdown", "!",
        "router eigrp 100",
        " network {{ params.seg_ca }}.0 0.0.0.3", " no auto-summary"]
    L += [f" {x}" for x in v["rc_eigrp_extra"]]
    L += ["!", "router ospf 1", " router-id {{ params.rc_lo }}",
          " network {{ params.rc_lo }} 0.0.0.0 area 0",
          " network {{ params.seg_cb }}.0 0.0.0.3 area 0"]
    L += [f" {x}" for x in v["rc_ospf_extra"]]
    L += ["!", "router bgp 65000", " bgp router-id {{ params.rc_lo }}",
          " bgp log-neighbor-changes", " bgp redistribute-internal",
          " network {{ params.rc_lo }} mask 255.255.255.255",
          " neighbor {{ params.seg_ec }}.1 remote-as 65000",
          # OSPF→BGP のみ再配送(RE の IGP側到達性用)。EIGRP→BGP は入れない:
          # ad_eigrp では被害経路が RC の RIB で eigrp になり、eigrp→bgp が weight32768 の
          # ローカル経路として BGP ベストを奪い、distance bgp が効かなくなる(実機確認)。
          " redistribute ospf 1", "!"]
    return L


def build_model():
    """netmodel 用トポロジモデル(RE の代表 Loopback = 192.168.51.1)。"""
    return {
        "loopbacks": {"RE": f"{P_NET}.1", "RC": "{{ params.rc_lo }}",
                      "RA": "{{ params.ra_lo }}", "RB": "{{ params.rb_lo }}"},
        "links": [
            {"a": "RE", "a_ip": "{{ params.seg_ec }}.1", "b": "RC", "b_ip": "{{ params.seg_ec }}.2"},
            {"a": "RC", "a_ip": "{{ params.seg_ca }}.1", "b": "RA", "b_ip": "{{ params.seg_ca }}.2"},
            {"a": "RC", "a_ip": "{{ params.seg_cb }}.1", "b": "RB", "b_ip": "{{ params.seg_cb }}.2"},
            {"a": "RA", "a_ip": "{{ params.seg_ab }}.1", "b": "RB", "b_ip": "{{ params.seg_ab }}.2"}]}


def grading_text(prob_id, var):
    """grading.yml.j2 本文(params 参照込み)。method=filter は distance 禁止チェックを追加。"""
    v = VARIANTS[var]
    m = build_model()
    model_yaml = yaml.safe_dump({"loopbacks": m["loopbacks"], "links": m["links"]},
                                sort_keys=False, allow_unicode=True, default_flow_style=False)
    model_yaml = "\n".join("  " + ln for ln in model_yaml.splitlines())
    # method=filter は「distance を変更していない」ことを 5 点で確認し、RC-bgp を 5 点に落として合計 100 維持。
    rc_bgp_pts = 5 if v["method"] == "filter" else 10
    extra = ""
    if v["method"] == "filter":
        extra = """  - name: "RC: 管理距離(distance)を変更していない(監査ポリシー遵守＝フィルタで解くこと)"
    node: RC
    command: "show running-config | include distance"
    raw:
      - { not_regex: "distance" }
    points: 5
"""
    return f"""# 自動生成 (gen_redist_loop_ts.py) {prob_id} variant={var} method={v['method']}
# 初期: 192.168.51.0/24 が {v['loop_path']} で定常ループ→ reachability/loop_free が 0。
# 是正後: RC が iBGP(起点RE方向)を選び→全到達＋ループ消失。
problem: {prob_id}
total_points: 100
defaults:
  genie_os: iosxe
model:
{model_yaml}
invariants:
  - {{ type: reachability_all, name: "全ルータ間 Loopback 到達性(被害プレフィクスを含む)", points: 30 }}
  - {{ type: loop_free, name: "転送ループ無し({v['loop_path']} の再配送リングループ解消)", points: 25 }}
  - type: optimal
    name: "被害プレフィクスへの最短転送(震源 RC でループ・遠回りが無い)"
    points: 15
    pairs: {json.dumps(v["opt_pairs"])}
checks:
  - name: "RC: 192.168.51.0/24 を BGP(iBGP)で学習(戻り経路でなく起点 RE 方向を選択＝ループ解消の核心)"
    node: RC
    command: "show ip route 192.168.51.0"
    raw:
      - {{ regex: 'Known via "bgp 65000"' }}
    points: {rc_bgp_pts}
  - name: "RE: OSPF/EIGRP側 Loopback({{{{ params.rb_lo }}}}) を BGP(B)で学習(戻り再配送 IGP→BGP が機能)"
    node: RE
    command: "show ip route bgp"
    raw:
      - {{ regex: "B\\\\s+{{{{ params.rb_lo }}}}" }}
    points: 10
  - name: "RB: 192.168.51.0/24 を OSPF 外部(extern 2)で学習(再配送リングの OSPF 部が機能)"
    node: RB
    command: "show ip route 192.168.51.0"
    raw:
      - {{ regex: 'Known via "ospf' }}
      - {{ regex: "extern 2" }}
    points: 5
  - name: "RC: 静的経路なし(暫定対処の残置禁止)"
    node: RC
    command: "show ip route static"
    raw:
      - {{ not_regex: "(?m)^S" }}
    points: 5
{extra}"""


def task_text(prob_id, var):
    v = VARIANTS[var]
    inject = "OSPF" if v["rc_ospf_extra"] else "EIGRP"
    if v["method"] == "filter":
        constraint_extra = ("\n- **管理距離(administrative distance)の変更は監査ポリシーで禁止**"
                            "(`distance` / `distance bgp` / `distance ospf external` / "
                            "`distance eigrp` は使用不可)。")
        hint = (f"RC で `show ip route {P_NET}.0` を見て、この経路の**学習元プロトコル**を確認せよ。"
                "本来 iBGP で受け取るべき経路を、RC が一周して戻ってきた別プロトコル経由で"
                "採用してしまっている。**管理距離は触れない**ので、その『戻り』の経路が RC の"
                "経路表に**載らないようにする**方法を考えよ(何を・どの方向で止めるか)。\n"
                "※ 設定変更後に経路が変わらない時は `clear ip route *` で再計算する。")
    else:
        constraint_extra = ""
        hint = (f"RC で `show ip route {P_NET}.0` を見て、この経路の**学習元プロトコルと管理距離**を"
                "確認せよ。「起点 RE から本来 iBGP で受け取っているはずの経路」を、RC が"
                "**別プロトコル経由で優先していないか**。既定の管理距離"
                "(eBGP 20 / OSPF 110 / EIGRP内部 90・外部 170 / **iBGP 200**)の並びが手掛かり。\n"
                "※ 設定変更後に経路が変わらない時は、既存経路の再計算(`clear ip route *`)が要る。")
    return f"""# 問題 {prob_id} : 再配送リングによる経路ループ(難易度{v['difficulty']})

## 状況
本社の顧客網 `{P_NET}.0/24` は **BGP AS 65000** の起点ルータ **RE** が広告している。
社内は 3 つのルーティングドメインが数珠つなぎ(**{v['ring']}** のリング)になっている。

```
  RE ──(BGP iBGP)── RC ──(EIGRP AS100)── RA
                     │                     │
                     └────(OSPF area0)──── RB
```

- **RC**: 起点 RE から `{P_NET}.0/24` を **iBGP** で受け取り、それを **{inject}** へ再配送している。
  さらにもう一方の IGP にも参加している。
- **RA**: **EIGRP ⇄ OSPF** を相互再配送している。
- **RB**: **OSPF** 内部(`PC4` 側サイト)。

## トラブルチケット(代表症状)
> `RB`(PC4 側)や `RC` から本社顧客網 **`{P_NET}.0/24` 宛が届かない**。
> `traceroute {P_NET}.1` すると **{v['loop_path']} …** と同じ3台を**ぐるぐる回って**
> TTL 超過で落ちる。他の宛先(各ルータの Loopback)は問題なく到達する。

## ルータ / 役割 / Loopback
| ルータ | 役割 | Loopback / 広告網 |
|--------|------|-------------------|
| RE | BGP 起点 | `{P_NET}.1/24`(`{P_NET}.0/24` を広告)|
| RC | iBGP/EIGRP/OSPF 収容・BGP→{inject} 再配送 | `{{{{ params.rc_lo }}}}/32` |
| RA | EIGRP⇄OSPF 相互再配送 | `{{{{ params.ra_lo }}}}/32` |
| RB | OSPF 内部 | `{{{{ params.rb_lo }}}}/32` |

## 到達目標
1. すべてのルータが全 Loopback へ**到達**できること(`{P_NET}.0/24` を含む)。
2. **転送ループが無い**こと。特に `{P_NET}.0/24` 宛が起点 RE 方向へ正しく転送されること。
3. 各ドメインの再配送設計は**維持**すること(再配送そのものを止めて回避するのは不可)。

## 制約
- プロトコル配置(どのルータ・リンクが BGP / EIGRP / OSPF か)は変更不可。
- 静的経路・デフォルトルートの追加による回避は不可。
- RE・RA・RB は変更しないこと。設定するのは **RC** のみ。{constraint_extra}

## 進め方のヒント(控えめ)
{hint}

## アクセス・採点
SSH `SUZUKI / CCNP`(mgmt は割当順に 10.1.10.11〜)。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
採点は **効果ベース**(到達性・ループ不在・最短転送・再配送設計の維持)。手段は問わない。
"""


def solution_md(prob_id, var):
    v = VARIANTS[var]
    inject = "OSPF" if v["rc_ospf_extra"] else "EIGRP"
    ret = v["victim_src"].split()[0].upper()   # ospf/eigrp
    if v["method"] == "filter":
        fix_section = f"""## 解(RC・管理距離は使わない)
戻ってきた `{P_NET}.0/24`(**{v['victim_word']}**)を、**RC の経路表に載らないようフィルタ**する。
プレフィックスリストで当該プレフィックスだけを OSPF 学習(`distribute-list ... in`)で遮断すると、
RC はそれを RIB に入れず **iBGP(起点 RE 方向)** を採用する。OSPF の LSDB は無傷なので **RB 側の
到達性は維持**される(distance には一切触れない)。

```
ip prefix-list DENY_FEEDBACK seq 5 deny {P_NET}.0/24
ip prefix-list DENY_FEEDBACK seq 10 permit 0.0.0.0/0 le 32
!
router ospf 1
 distribute-list prefix DENY_FEEDBACK in
```

### ★変更後は経路の再計算
`distribute-list in` 追加後、`clear ip route *`(RC)で反映する。

## 確認
- RC: `show ip route {P_NET}.0` が **`Known via "bgp 65000"`**(`{v['victim_src']}` ではない)。
  `distance` は 200 のまま(変えていない)。
- RC/RB/RA から `traceroute {P_NET}.1` が **RE に一直線**(3台を回らない)。

## 別解(いずれも distance を使わない・効果ベース採点)
- 拡張 ACL ベースの `distribute-list <acl> in`、または OSPF 学習側 `route-map`(match tag)で
  自ドメイン発の戻りを遮断。**経路タグ**方式(BGP→EIGRP 注入時に `set tag`、戻りをタグで遮断)も可だが
  タグが再配送を跨いで伝播することの確認が要る(本問の実機では prefix-list の方が確実)。
- **不可**: `distance` 系の使用(監査ポリシー違反)、いずれかの再配送の丸ごと削除、静的経路での回避。"""
    else:
        fix_section = f"""## 解(RC)
BGP の管理距離を戻り経路の AD(**{v['return_ad']}**)未満に下げ、RC が **iBGP(＝起点 RE 方向)** を選ぶ。

```
router bgp 65000
 {v['fix_line']}
```

### ★変更後は経路の再計算が必要
`distance` は既にインストール済みの経路に即時反映されない。RC で

```
clear ip route *
```

を実行して初めて iBGP が採用される(実行前は BGP エントリが `RIB-failure(17)` のまま)。

## 確認
- RC: `show ip route {P_NET}.0` が **`Known via "bgp 65000"`**(`{v['victim_src']}` ではない)。
- RC/RB/RA から `traceroute {P_NET}.1` が **RE に一直線**(3台を回らない)。

## 別解(効果ベース採点なのでいずれも可)
- **`{v['fix_alt']}`**(戻り側の外部経路 AD を iBGP 200 超へ)＝ RC が iBGP を優先。
- **経路タグ / フィルタ**: RC が BGP→{inject} 再配送時に `set tag`、戻ってきた自ドメイン発を
  RC の学習側で `distribute-list ... in` 遮断(プレフィックスリスト等)。
- **不可**: いずれかの再配送を丸ごと削除して回避、静的経路・デフォルトでの回避。"""
    return f"""# 模範解答 : {prob_id}(variant={var})

## なぜ壊れるか(再配送リングのループ)
`{P_NET}.0/24` は RE が **BGP** で起点広告し、RC が **iBGP(AD 200)** で学習する。
再配送が **{v['ring']}** のリングを成すため、この経路の出自がドメインを一周して RC に戻る。
戻ってきた経路は **{v['victim_word']}** で、その **AD が iBGP(200)より低い**ため RC はそれを優先し、
`{P_NET}.0/24` 宛を {ret} 側へ転送してしまう → **{v['loop_path']}** の定常転送ループ。

RC は RIB 勝者プロトコルを再配送源にするので、BGP だけでなく戻り側 IGP も {inject} へ再配送して
P を常時循環させている(＝振動でなく定常ループに固定)。

{fix_section}

## 教育核心(Ping-t #28776 型)
- 多点再配送がドメインをまたいで **リング**を成すと、経路の出自が一周して戻る。戻り経路の AD が
  元の学習元より低いとループ/振動する。
- 既定 AD(eBGP 20・EIGRP内部 90・OSPF 110・EIGRP外部 170・**iBGP 200**)の並びは必修。
  **iBGP は最も信用されない(200)** ため、iBGP 経路を IGP へ再配送するとこの罠を踏みやすい。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--variant", choices=sorted(VARIANTS), default=None)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    lo, seg = rand_values(rnd)
    var = a.variant or rnd.choice(sorted(VARIANTS))
    v = VARIANTS[var]

    prob_id = f"GEN-REDISTLOOP-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/params", exist_ok=True)

    # params: base.yml(この seed の確定値) を variant 無指定 build 用に置く。
    params = {"p_net": P_NET, "rc_lo": lo["RC"], "ra_lo": lo["RA"], "rb_lo": lo["RB"],
              "seg_ec": seg["ec"], "seg_ca": seg["ca"], "seg_cb": seg["cb"], "seg_ab": seg["ab"]}
    with open(f"{pdir}/params/base.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_loop_ts.py) seed={a.seed} variant={var}\n")
        yaml.safe_dump(params, f, sort_keys=False, allow_unicode=True)

    problem = {"id": prob_id,
               "title": f"再配送リング定常ループTS variant={var} (seed={a.seed})",
               "exam": "ENARSI",
               "topics": ["redistribution", "bgp", "eigrp", "ospf",
                          "administrative-distance", "routing-loop", "generated"],
               "difficulty": v["difficulty"], "topology": "generated",
               "access": "ssh", "target_nodes": NODES, "points": 100,
               "lab": {"links": [
                   {"a": "RE", "a_if": 0, "b": "RC", "b_if": 0},
                   {"a": "RC", "a_if": 1, "b": "RA", "b_if": 0},
                   {"a": "RC", "a_if": 2, "b": "RB", "b_if": 0},
                   {"a": "RA", "a_if": 1, "b": "RB", "b_if": 1}],
                   "positions": {"RE": [-760, -160], "RC": [-400, -160],
                                 "RA": [-40, -360], "RB": [-40, 40]}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_loop_ts.py) seed={a.seed} variant={var}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    for n in NODES:
        with open(f"{pdir}/initial/{n}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_node(n, var)) + "\n")

    with open(f"{pdir}/grading.yml.j2", "w", encoding="utf-8") as f:
        f.write(grading_text(prob_id, var))
    with open(f"{pdir}/task.md.j2", "w", encoding="utf-8") as f:
        f.write(task_text(prob_id, var))
    with open(f"{pdir}/solution.md", "w", encoding="utf-8") as f:
        f.write(solution_md(prob_id, var))

    if v["method"] == "filter":
        sol = {"_comment": f"variant={var}(distance 禁止): RC で prefix-list distribute-list in により "
                           f"戻り {P_NET}.0/24(O E2) を RIB 学習で遮断→ RC は iBGP を採用。clear ip route * で反映。",
               "nodes": {}, "post_clear": ["RC"],
               "filters": [{"node": "RC", "blocks": v["fix_blocks"]}]}
    else:
        sol = {"_comment": f"variant={var}: RC で {v['fix_line']}(BGP AD<戻りAD {v['return_ad']})。"
                           "distance 変更は clear ip route * で反映(solve 後に別途 clear)。"
                           f"別解={v['fix_alt']} / フィルタ。",
               "nodes": {}, "post_clear": ["RC"],
               "filters": [{"node": "RC",
                            "blocks": [{"parents": "router bgp 65000", "lines": [v["fix_line"]]}]}]}
    with open(f"{pdir}/solution.json", "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=2)

    print(f"wrote problems/{prob_id} : variant={var} diff={v['difficulty']} "
          f"ring='{v['ring']}' loop='{v['loop_path']}'")


if __name__ == "__main__":
    main()
