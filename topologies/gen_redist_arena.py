#!/usr/bin/env python3
"""再配送ループ・アリーナ — トポロジ抽選型の定常ルーティングループ生成器 (BL-074 Phase1)。

gen_redist_loop_ts.py のリングモチーフ(M1・実機検証済の定石)を骨格に、
**トポロジと見た目を seed 抽選**して「固定トポロジへの慣れ」を封じる:

  1. ノード名の匿名化: 役割(起点/震源/中継…)と名前(RT01..RTn)の対応を seed でシャッフル。
     役割が名前から透けない。task.md の図・表も抽選された実形状から都度生成。
  2. ノイズノードの接ぎ木: OSPF ドメインに leaf / chain / fork を 1〜4 台抽選で接ぎ木
     (RB配下 leaf→chain/fork・RA配下 leaf)。ループ機構に無関係だが到達性採点には参加する
     (Lo は OSPF→BGP 再配送で起点からも到達可=全ノード一貫)。
  3. 値の抽選: 被害プレフィクス(192.168.X)・BGP AS・EIGRP AS・OSPF PID・Lo・セグメント。
  4. リング向き(BGP注入先IGP) × 解法(distance/filter) を抽選 → 4 組合せ。

★ループ成立の決定性はモチーフで担保(ランダム配線では定常ループは成立しない):
  被害プレフィクス P は起点 RE_role が BGP 広告 → 震源 RC_role が iBGP(AD200) 学習。
  再配送リングで出自が一周し、戻り経路(O E2 110 / D EX 170)が iBGP に勝って定常ループ。
  RC_role は BGP と戻りIGP の二重再配送で P を常時循環させ振動でなく定常に固定
  (この機構・是正・別解は gen_redist_loop_ts と同一。実機検証済)。

★EIGRP 側へのノイズ接ぎ木は Phase2 送り: EIGRP leaf の Lo は eigrp→bgp 再配送なしでは
  起点から到達不能になり、eigrp→bgp は ad_eigrp 型で distance 解を壊す実機知見があるため。

出力: problems/GEN-RDARENA-<seed>/ {problem.yml, initial/*.cfg.j2, grading.yml, task.md,
      solution.md, solution/fix.json}
  - 値は全て焼き込み(params 不使用)。initial のみ {{ links[n] }} を build 時描画。
  - fix.json は fix_generated.yml 形式(config+exec clear)。
使い方: gen_redist_arena.py --repo . --seed <int> [--ring inject_eigrp|inject_ospf]
        [--method distance|filter]
"""
import argparse
import json
import os
import random

import yaml

EIGRP_METRIC = "100000 100 255 1 1500"
ROLES_CORE = ["RE", "RC", "RA", "RB"]          # 起点 / 震源 / 相互再配送 / OSPF中継


# --------------------------------------------------------------------------
# 抽選
# --------------------------------------------------------------------------
def draw(rnd, ring=None, method=None):
    d = {}
    d["ring"] = ring or rnd.choice(["inject_eigrp", "inject_ospf"])
    d["method"] = method or rnd.choice(["distance", "filter"])
    # ノイズ(OSPFドメインのみ): NO1=RB配下leaf / NO2=NO1のchain / NO3=NO1のfork / NOA=RA配下leaf
    d["no1"] = rnd.random() < 0.7
    d["no2"] = d["no1"] and rnd.random() < 0.5
    d["no3"] = d["no1"] and rnd.random() < 0.3
    d["noa"] = rnd.random() < 0.5
    if not (d["no1"] or d["noa"]):
        d[rnd.choice(["no1", "noa"])] = True    # 最低1台は接ぎ木(素の正準形を出さない)
    roles = list(ROLES_CORE)
    for r, flag in [("NO1", "no1"), ("NO2", "no2"), ("NO3", "no3"), ("NOA", "noa")]:
        if d[flag]:
            roles.append(r)
    d["roles"] = roles

    # 匿名化: RT01..RTn を役割へシャッフル割当
    names = [f"RT{i:02d}" for i in range(1, len(roles) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(roles, names))

    # 値
    d["p_third"] = rnd.choice([x for x in range(20, 251) if x != 51])
    d["p_net"] = f"192.168.{d['p_third']}"
    d["bgp_as"] = rnd.randint(64600, 65500)
    d["eigrp_as"] = rnd.randint(100, 899)
    d["ospf_pid"] = rnd.randint(1, 99)
    used, lo = set(), {}
    for r in [x for x in roles if x != "RE"]:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    d["lo"] = lo
    seg_names = ["ec", "ca", "cb", "ab"] + \
        [s for s, f in [("b1", "no1"), ("n12", "no2"), ("n13", "no3"), ("a1", "noa")] if d[f]]
    useg, seg = set(), {}
    for s in seg_names:
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in useg:
                useg.add((p, q)); seg[s] = f"10.{p}.{q}"; break
    d["seg"] = seg
    return d


def links_of(d):
    """(role_a, slot_a, role_b, slot_b, seg名)。slot は IOL データIF 0-2。"""
    L = [("RE", 0, "RC", 0, "ec"), ("RC", 1, "RA", 0, "ca"),
         ("RC", 2, "RB", 0, "cb"), ("RA", 1, "RB", 1, "ab")]
    if d["no1"]:
        L.append(("RB", 2, "NO1", 0, "b1"))
    if d["no2"]:
        L.append(("NO1", 1, "NO2", 0, "n12"))
    if d["no3"]:
        L.append(("NO1", 2, "NO3", 0, "n13"))
    if d["noa"]:
        L.append(("RA", 2, "NOA", 0, "a1"))
    return L


def slot_map(d):
    """role -> [そのノードが使うリンクの (slot, seg, side)] (side: 1=.1側 / 2=.2側)。"""
    sm = {r: [] for r in d["roles"]}
    for a, sa, b, sb, s in links_of(d):
        sm[a].append((sa, s, 1))
        sm[b].append((sb, s, 2))
    return {r: sorted(v) for r, v in sm.items()}


# --------------------------------------------------------------------------
# 初期 config
# --------------------------------------------------------------------------
def _ifaces(d, role):
    """{{ links[n] }} 行を slot 順に描画。"""
    out = []
    for slot, s, side in slot_map(d)[role]:
        out += [f"interface {{{{ links[{slot}] }}}}",
                f" ip address {d['seg'][s]}.{side} 255.255.255.252", " no shutdown", "!"]
    return out


def render_node(d, role):
    m, seg, lo = d["m"], d["seg"], d["lo"]
    pid, eas, bas, p = d["ospf_pid"], d["eigrp_as"], d["bgp_as"], d["p_net"]
    inject_eigrp = d["ring"] == "inject_eigrp"
    if role == "RE":
        return ["! GEN-RDARENA 初期 (BGP 起点)",
                "interface Loopback0", f" ip address {p}.1 255.255.255.0", "!",
                *_ifaces(d, role),
                f"router bgp {bas}", f" bgp router-id {p}.1", " bgp log-neighbor-changes",
                f" network {p}.0 mask 255.255.255.0",
                f" neighbor {seg['ec']}.2 remote-as {bas}", "!"]
    if role in ("RB", "NO1", "NO2", "NO3", "NOA"):
        # OSPF ドメイン(中継 RB とノイズ達): Lo + 収容リンクを area0 へ。
        nets = [f" network {lo[role]} 0.0.0.0 area 0"] + \
               [f" network {seg[s]}.0 0.0.0.3 area 0" for _, s, _ in slot_map(d)[role]]
        return [f"! GEN-RDARENA 初期 (OSPF area0 {'中継' if role == 'RB' else '内部'})",
                "interface Loopback0", f" ip address {lo[role]} 255.255.255.255", "!",
                *_ifaces(d, role),
                f"router ospf {pid}", f" router-id {lo[role]}", *nets, "!"]
    if role == "RA":
        # 相互再配送境界(EIGRP⇄OSPF)。EIGRP=RC向けリンクのみ / OSPF=Lo+RB向け(+NOA向け)。
        ospf_nets = [f" network {lo[role]} 0.0.0.0 area 0",
                     f" network {seg['ab']}.0 0.0.0.3 area 0"]
        if d["noa"]:
            ospf_nets.append(f" network {seg['a1']}.0 0.0.0.3 area 0")
        return ["! GEN-RDARENA 初期 (EIGRP⇄OSPF 相互再配送・リング中継)",
                "interface Loopback0", f" ip address {lo[role]} 255.255.255.255", "!",
                *_ifaces(d, role),
                f"router eigrp {eas}",
                f" network {seg['ca']}.0 0.0.0.3", " no auto-summary",
                f" redistribute ospf {pid} metric {EIGRP_METRIC}", "!",
                f"router ospf {pid}", f" router-id {lo[role]}", *ospf_nets,
                f" redistribute eigrp {eas} subnets", "!"]
    # RC = 震源(iBGP + EIGRP + OSPF)。リング向きで BGP の注入先 IGP が変わる。
    eigrp_extra = ([f" redistribute bgp {bas} metric {EIGRP_METRIC}",
                    f" redistribute ospf {pid} metric {EIGRP_METRIC}"] if inject_eigrp else [])
    ospf_extra = ([] if inject_eigrp else
                  [f" redistribute bgp {bas} subnets",
                   f" redistribute eigrp {eas} subnets"])
    return ["! GEN-RDARENA 初期 (iBGP + EIGRP + OSPF 収容)",
            "interface Loopback0", f" ip address {lo[role]} 255.255.255.255", "!",
            *_ifaces(d, role),
            f"router eigrp {eas}",
            f" network {seg['ca']}.0 0.0.0.3", " no auto-summary", *eigrp_extra, "!",
            f"router ospf {pid}", f" router-id {lo[role]}",
            f" network {lo[role]} 0.0.0.0 area 0",
            f" network {seg['cb']}.0 0.0.0.3 area 0", *ospf_extra, "!",
            f"router bgp {bas}", f" bgp router-id {lo[role]}",
            " bgp log-neighbor-changes", " bgp redistribute-internal",
            f" network {lo[role]} mask 255.255.255.255",
            f" neighbor {seg['ec']}.1 remote-as {bas}",
            f" redistribute ospf {pid}", "!"]


# --------------------------------------------------------------------------
# 採点 / 解答
# --------------------------------------------------------------------------
def build_model(d):
    lb = {d["m"]["RE"]: f"{d['p_net']}.1"}
    lb.update({d["m"][r]: d["lo"][r] for r in d["roles"] if r != "RE"})
    links = [{"a": d["m"][a], "a_ip": f"{d['seg'][s]}.1",
              "b": d["m"][b], "b_ip": f"{d['seg'][s]}.2"}
             for a, _, b, _, s in links_of(d)]
    return {"loopbacks": lb, "links": links}


def fix_of(d):
    """(fix.json dict, 修正内容の説明, 監査用 return_ad)。"""
    m, p = d["m"], d["p_net"]
    inject_eigrp = d["ring"] == "inject_eigrp"
    return_ad = 110 if inject_eigrp else 170
    if d["method"] == "distance":
        line = f"distance bgp 20 {return_ad - 5} {return_ad - 5}"
        fixes = [{"node": m["RC"], "parents": [f"router bgp {d['bgp_as']}"], "lines": [line]}]
        desc = f"RC({m['RC']}) で {line}(iBGP<戻りAD {return_ad})"
    else:
        dl_parent = (f"router ospf {d['ospf_pid']}" if inject_eigrp
                     else f"router eigrp {d['eigrp_as']}")
        fixes = [
            {"node": m["RC"], "lines":
                [f"ip prefix-list DENY_FEEDBACK seq 5 deny {p}.0/24",
                 "ip prefix-list DENY_FEEDBACK seq 10 permit 0.0.0.0/0 le 32"]},
            {"node": m["RC"], "parents": [dl_parent],
             "lines": ["distribute-list prefix DENY_FEEDBACK in"]}]
        desc = f"RC({m['RC']}) で {dl_parent} に distribute-list prefix in(戻り遮断・distance不使用)"
    fixes.append({"node": m["RC"], "exec": ["clear ip route *"]})
    return {"_comment": desc + "。反映は clear ip route *。", "fixes": fixes}, desc, return_ad


def grading_text(d, prob_id):
    m, p = d["m"], d["p_net"]
    inject_eigrp = d["ring"] == "inject_eigrp"
    mo = build_model(d)
    model_yaml = yaml.safe_dump({"loopbacks": mo["loopbacks"], "links": mo["links"]},
                                sort_keys=False, allow_unicode=True, default_flow_style=False)
    model_yaml = "\n".join("  " + ln for ln in model_yaml.splitlines())
    # 最短転送の決定的ペア(モチーフ準拠・ノイズは reachability のみで見る)
    if inject_eigrp:
        pairs = [[m["RC"], m["RE"]], [m["RA"], m["RE"]], [m["RB"], m["RC"]], [m["RC"], m["RB"]]]
    else:
        pairs = [[m["RC"], m["RE"]], [m["RB"], m["RC"]], [m["RC"], m["RB"]]]
    loop_word = (f"{m['RC']} → {m['RB']} → {m['RA']} → {m['RC']}" if inject_eigrp
                 else f"{m['RC']} → {m['RA']} → {m['RB']} → {m['RC']}")
    rc_bgp_pts = 5 if d["method"] == "filter" else 10
    extra = ""
    if d["method"] == "filter":
        extra = f"""  - name: "{m['RC']}: 管理距離(distance)を変更していない(監査ポリシー遵守＝フィルタで解くこと)"
    node: {m['RC']}
    command: "show running-config | include distance"
    raw:
      - {{ not_regex: "distance" }}
    points: 5
"""
    return f"""# 自動生成 (gen_redist_arena.py) {prob_id} ring={d['ring']} method={d['method']}
# 初期: {p}.0/24 が {loop_word} で定常ループ。是正後: {m['RC']} が iBGP を採用し全到達。
problem: {prob_id}
total_points: 100
defaults:
  genie_os: iosxe
model:
{model_yaml}
invariants:
  - {{ type: reachability_all, name: "全ルータ間 Loopback 到達性(被害プレフィクスを含む)", points: 30 }}
  - {{ type: loop_free, name: "転送ループ無し({loop_word} の再配送リングループ解消)", points: 25 }}
  - type: optimal
    name: "被害プレフィクスへの最短転送(震源でループ・遠回りが無い)"
    points: 15
    pairs: {json.dumps(pairs)}
checks:
  - name: "{m['RC']}: {p}.0/24 を BGP(iBGP)で学習(戻り経路でなく起点方向を選択＝ループ解消の核心)"
    node: {m['RC']}
    command: "show ip route {p}.0"
    raw:
      - {{ regex: 'Known via "bgp {d['bgp_as']}"' }}
    points: {rc_bgp_pts}
  - name: "{m['RE']}: IGP側 Loopback({d['lo']['RB']}) を BGP(B)で学習(戻り再配送 IGP→BGP が機能)"
    node: {m['RE']}
    command: "show ip route bgp"
    raw:
      - {{ regex: "B\\\\s+{d['lo']['RB']}" }}
    points: 10
  - name: "{m['RB']}: {p}.0/24 を OSPF 外部(extern 2)で学習(再配送リングの OSPF 部が機能)"
    node: {m['RB']}
    command: "show ip route {p}.0"
    raw:
      - {{ regex: 'Known via "ospf' }}
      - {{ regex: "extern 2" }}
    points: 5
  - name: "{m['RC']}: 静的経路なし(暫定対処の残置禁止)"
    node: {m['RC']}
    command: "show ip route static"
    raw:
      - {{ not_regex: "(?m)^S" }}
    points: 5
{extra}"""


def task_text(d, prob_id):
    m, p, seg = d["m"], d["p_net"], d["seg"]
    inject = "EIGRP" if d["ring"] == "inject_eigrp" else "OSPF"
    # 図: 実形状からエッジリストを生成(ドメインラベル付き・物理的事実のみ)
    dom = {"ec": f"iBGP AS {d['bgp_as']}", "ca": f"EIGRP AS {d['eigrp_as']}"}
    edges = []
    for a, _, b, _, s in links_of(d):
        label = dom.get(s, f"OSPF {d['ospf_pid']} area 0")
        edges.append(f"  {m[a]} ── {m[b]}   ({label} / {seg[s]}.0/30)")
    edge_block = "\n".join(edges)
    # ルータ表(参加プロトコルと Lo のみ=実機で確認できる事実。再配送の役割は書かない)
    rows = []
    for r in d["roles"]:
        protos = {"RE": f"BGP AS {d['bgp_as']}",
                  "RC": f"BGP / EIGRP / OSPF",
                  "RA": "EIGRP / OSPF",
                  }.get(r, f"OSPF {d['ospf_pid']}")
        lo_txt = f"`{p}.1/24`(`{p}.0/24` を広告)" if r == "RE" else f"`{d['lo'][r]}/32`"
        rows.append(f"| {m[r]} | {protos} | {lo_txt} |")
    rows_block = "\n".join(sorted(rows))
    if d["method"] == "filter":
        constraint_extra = ("\n- **管理距離(administrative distance)の変更は監査ポリシーで禁止**"
                            "(`distance` 系コマンドは使用不可)。")
    else:
        constraint_extra = ""
    return f"""# 問題 {prob_id} : 経路到達性障害チケット(難易度5)

## 状況
本社の顧客網 `{p}.0/24` は **BGP AS {d['bgp_as']}** の起点ルータ **{m['RE']}** が広告している。
社内は BGP / EIGRP / OSPF の 3 ドメイン構成で、境界のどこかで再配送が行われている。
昨夜の作業以降、下記のチケットが届いている。

## リンク一覧(L2 直結・アドレスは /30 の .1/.2)

```
{edge_block}
```

## ルータ / 参加プロトコル / Loopback

| ルータ | 参加プロトコル | Loopback / 広告網 |
|--------|----------------|-------------------|
{rows_block}

## トラブルチケット(申告のみ・裏取りはあなたの仕事)
> 複数拠点から本社顧客網 **`{p}.0/24` 宛が届かない**。
> 他の宛先(各ルータの Loopback)は問題なく到達しているとのこと。
> 何が・どこで・どのように起きているか(届かない「型」)の特定から始めること。

## 到達目標
1. すべてのルータが全 Loopback へ**到達**できること(`{p}.0/24` を含む)。
2. **転送ループが無い**こと。特に `{p}.0/24` 宛が起点 {m['RE']} 方向へ正しく転送されること。
3. 各ドメインの再配送設計は**維持**すること(再配送そのものを止めて回避するのは不可)。

## 制約
- プロトコル配置(どのルータ・リンクが BGP / EIGRP / OSPF か)は変更不可。
- 静的経路・デフォルトルートの追加による回避は不可。
- 設定変更してよいのは **{m['RC']} のみ**。他のルータは変更禁止(show・ping・traceroute は可)。{constraint_extra}

## 備考
※ 設定変更後に経路が変わらない時は `clear ip route *` で再計算する。

## アクセス・採点
SSH `SUZUKI / CCNP`(mgmt は割当順に 10.1.10.11〜)。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
採点は **効果ベース**(到達性・ループ不在・最短転送・再配送設計の維持)。手段は問わない。
"""


def solution_md(d, prob_id, fix_desc, return_ad):
    m, p = d["m"], d["p_net"]
    inject = "EIGRP" if d["ring"] == "inject_eigrp" else "OSPF"
    victim = f"OSPF 外部(O E2・AD 110)" if d["ring"] == "inject_eigrp" else "EIGRP 外部(D EX・AD 170)"
    return f"""# 模範解答 : {prob_id} (ring={d['ring']} method={d['method']})

## 役割の種明かし(匿名化の解答)
- 起点 = {m['RE']} / **震源(被害) = {m['RC']}** / 相互再配送境界 = {m['RA']} / OSPF 中継 = {m['RB']}
- ノイズノード(ループ機構に無関係): {', '.join(m[r] for r in d['roles'] if r.startswith('NO')) or 'なし'}

## なぜ壊れるか
`{p}.0/24` は {m['RE']} が BGP 起点広告し、{m['RC']} が **iBGP(AD 200)** で学習する。
{m['RC']} は BGP を **{inject}** へ再配送し、{m['RA']} の EIGRP⇄OSPF 相互再配送で出自が一周、
戻ってきた **{victim}** が iBGP(200) に勝って {m['RC']} が採用 → 定常転送ループ。

## 解
{fix_desc}。投入後 `clear ip route *`。

## 確認
- {m['RC']}: `show ip route {p}.0` が `Known via "bgp {d['bgp_as']}"` に変わる。
- 任意ルータから `traceroute {p}.1` が {m['RE']} に一直線。

## 教育核心
既定 AD の並び(eBGP 20 / EIGRP内 90 / OSPF 110 / EIGRP外 170 / **iBGP 200**)と、
再配送リングで出自が一周して戻る構造。distance 解と フィルタ解(distribute-list in)は
表裏(前者=信用度を変える / 後者=戻りを学習段で捨てる)。
"""


# --------------------------------------------------------------------------
def generate(repo, seed, ring=None, method=None, prob_id=None):
    """1問生成して要約文字列を返す。prob_id 指定で ID を差し替え可能
    (gen_redist_field.py の shape=ring 統合用: GEN-RDFIELD-<seed> として出せる)。"""
    rnd = random.Random(seed)
    d = draw(rnd, ring=ring, method=method)
    m = d["m"]

    prob_id = prob_id or f"GEN-RDARENA-{seed}"
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    names_sorted = sorted(m.values())
    problem = {"id": prob_id,
               "title": f"再配送ループ・アリーナ ring={d['ring']} method={d['method']} (seed={seed})",
               "exam": "ENARSI",
               "topics": ["redistribution", "bgp", "eigrp", "ospf", "routing-loop",
                          "topology-randomized", "generated"],
               "difficulty": 5, "topology": "generated", "access": "ssh",
               "target_nodes": names_sorted, "points": 100,
               "lab": {"links": [{"a": m[x], "a_if": sa, "b": m[y], "b_if": sb}
                                 for x, sa, y, sb, _ in links_of(d)]}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_redist_arena.py) seed={seed} ring={d['ring']} "
                f"method={d['method']} roles={ {r: m[r] for r in d['roles']} }\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)

    for r in d["roles"]:
        with open(f"{pdir}/initial/{m[r]}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render_node(d, r)) + "\n")

    fixdoc, fix_desc, return_ad = fix_of(d)
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(grading_text(d, prob_id))
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task_text(d, prob_id))
    with open(f"{pdir}/solution.md", "w", encoding="utf-8") as f:
        f.write(solution_md(d, prob_id, fix_desc, return_ad))
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump(fixdoc, f, ensure_ascii=False, indent=2)

    noise = [r for r in d["roles"] if r.startswith("NO")]
    return (f"wrote problems/{prob_id} : ring={d['ring']} method={d['method']} "
            f"nodes={len(d['roles'])} noise={len(noise)} "
            f"roles={{RE:{m['RE']}, RC:{m['RC']}, RA:{m['RA']}, RB:{m['RB']}}} "
            f"p={d['p_net']} asB={d['bgp_as']} asE={d['eigrp_as']} pid={d['ospf_pid']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--ring", choices=["inject_eigrp", "inject_ospf"], default=None)
    ap.add_argument("--method", choices=["distance", "filter"], default=None)
    a = ap.parse_args()
    print(generate(a.repo, a.seed, ring=a.ring, method=a.method))


if __name__ == "__main__":
    main()
