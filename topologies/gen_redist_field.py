#!/usr/bin/env python3
"""再配送フィールド — ドメイングラフ抽選型・再配送起因トラブル生成器 (BL-074 Phase2A)。

ユーザ要望「トポロジがガラッと変わって、でも再配送起因のトラブル」への回答。
アリーナ(ループ特化・リング固定)と違い、**ドメイン構成そのものを抽選**する:

  - ドメイン数 K=2〜3 の数珠つなぎ(木構造)。各ドメインのプロトコルは OSPF(pid抽選) /
    EIGRP(AS抽選) を抽選(OSPF×OSPF や EIGRP×EIGRP の同種異インスタンス隣接もあり)。
  - 境界ルータ(BR)がドメインを跨ぎ、相互再配送で全 Loopback 到達を成立させる(健全形)。
  - 各ドメインの内部ルータ数(0〜2)と内部配線(木)を抽選。ノード名は RT01..RTn へシャッフル
    (役割が名前から透けない)。合計 4〜8 台。
  - ★木構造ゆえ再配送リングが無い=定常ループは構造的に不成立 → 故障カタログは
    「欠落・誤参照・seed metric・フィルタ誤爆」系(どんな抽選形でも決定的に成立)。

故障カタログ(BR の再配送方向単位に注入・--faults 1〜2):
  missing   : 一方向の redistribute 丸ごと欠落 → 片側ドメイン群が対岸を全喪失(難4)
  wrong_id  : redistribute の参照プロセス/AS 番号が誤り(無言で経路ゼロ・config は一見完備)(難5)
  no_seed   : OSPF→EIGRP 注入の metric 欠落(∞メトリックで不広告・config は存在)(難5)
  filter    : redistribute に route-map が付き特定 Loopback だけ deny(部分喪失)(難4)

採点: netmodel reachability_all(40)+loop_free(10・ガード) ＋ 仕様書突き合わせ監査
  (BR 毎の redistribute 行 regex・フィルタ不在 not_regex) ＋ 対岸学習の指紋(D EX / O E2)。
出力: problems/GEN-RDFIELD-<seed>/ {problem.yml, initial/*.cfg.j2, grading.yml, task.md,
      solution.md, solution/fix.json}
使い方: gen_redist_field.py --repo . --seed <int> [--faults 1|2] [--fault <型>]
"""
import argparse
import json
import os
import random

import yaml

EIGRP_METRIC = "100000 100 255 1 1500"
FAULTS = ["missing", "wrong_id", "no_seed", "filter"]


# --------------------------------------------------------------------------
# 抽選: ドメイン列・メンバ・木配線
# --------------------------------------------------------------------------
def draw(rnd, faults_n=None, fault_kind=None, hard=False):
    d = {}
    K = 3 if hard else rnd.choice([2, 3])
    d["K"] = K
    # ドメインプロトコル(隣接同種も許すが同一インスタンスは不可)
    doms, used_ids = [], set()
    for i in range(K):
        t = rnd.choice(["ospf", "eigrp"])
        while True:
            pid = rnd.randint(1, 99) if t == "ospf" else rnd.randint(100, 899)
            if (t, pid) not in used_ids:
                used_ids.add((t, pid)); break
        doms.append({"type": t, "id": pid})
    d["doms"] = doms
    # 役割: BRi = ドメイン i と i+1 の境界。内部 = 端ドメイン 1〜2 / 中間 0〜1。
    brs = [f"BR{i+1}" for i in range(K - 1)]
    members = {i: [] for i in range(K)}          # domain idx -> roles
    for i, br in enumerate(brs):
        members[i].append(br); members[i + 1].append(br)
    internals = []
    for i in range(K):
        is_end = (i == 0 or i == K - 1)
        n_int = rnd.randint(1, 2) if is_end else rnd.randint(0, 1)
        for j in range(n_int):
            r = f"D{i}I{j+1}"
            internals.append(r); members[i].append(r)
    d["brs"], d["internals"], d["members"] = brs, internals, members
    roles = brs + internals
    # ドメイン内を木で配線(次数≤3)
    deg = {r: 0 for r in roles}
    links = []                                   # (role_a, role_b, domain_idx)
    for i in range(K):
        placed = [members[i][0]]
        for r in members[i][1:]:
            cands = [x for x in placed if deg[x] < 3]
            if not cands:
                raise SystemExit(f"degree overflow seed retry needed (dom {i})")
            up = rnd.choice(cands)
            links.append((up, r, i)); deg[up] += 1; deg[r] += 1
            placed.append(r)
    d["links"] = links
    # 匿名化
    names = [f"RT{i:02d}" for i in range(1, len(roles) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(roles, names))
    d["roles"] = roles
    # 値
    used, lo = set(), {}
    for r in roles:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    d["lo"] = lo
    useg, segs = set(), []
    for _ in links:
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            if (p, q) != (1, 10) and (p, q) not in useg:
                useg.add((p, q)); segs.append(f"10.{p}.{q}"); break
    d["segs"] = segs
    # 故障抽選: 方向 = (br, into_domain_idx)
    dirs = []
    for i, br in enumerate(brs):
        dirs.append((br, i))          # into 左ドメイン(src=右)
        dirs.append((br, i + 1))      # into 右ドメイン(src=左)
    n_f = faults_n or rnd.choice([1, 1, 2])
    rnd.shuffle(dirs)
    faults = []
    for br, into in dirs:
        if len(faults) >= n_f:
            break
        src_idx = _src_of(br, into, brs)
        applicable = ["missing", "wrong_id", "filter"]
        # wrong_id の誤ID(+7)が同種の実ドメインIDと衝突する形では wrong_id を出さない
        # (ospf⇄ospf 等で「自プロセスへの再配送」になり故障が成立しない)。
        if any(x["type"] == doms[src_idx]["type"] and x["id"] == doms[src_idx]["id"] + 7
               for x in doms):
            applicable.remove("wrong_id")
        # filter はトポロジ全体で1本まで(route-map/prefix-list 名の衝突防止)
        if any(x["kind"] == "filter" for x in faults):
            applicable.remove("filter")
        if doms[into]["type"] == "eigrp" and doms[src_idx]["type"] == "ospf":
            applicable.append("no_seed")
        if fault_kind:
            if fault_kind not in applicable:
                continue
            kind = fault_kind
        elif hard and not any(x["kind"] in ("wrong_id", "no_seed") for x in faults):
            # hard: 「config が完備に見えるのに効かない」系(wrong_id/no_seed)を最低1本保証。
            subtle = [k for k in applicable if k in ("wrong_id", "no_seed")]
            if not subtle and len(faults) + 1 >= n_f:
                continue          # この方向では subtle 不成立 → 別方向へ
            kind = rnd.choice(subtle or applicable)
        else:
            kind = rnd.choice(applicable)
        victim = None
        if kind == "filter":
            far = _side_roles(d, br, src_idx)      # src 側の Lo から1つ deny
            victim = rnd.choice([r for r in far if r != br])
        faults.append({"br": br, "into": into, "src": src_idx, "kind": kind,
                       "victim": victim})
    if not faults:
        raise SystemExit("fault 抽選失敗(--fault と抽選形の不整合)。別 seed か指定無しで。")
    d["faults"] = faults
    return d


def _src_of(br, into, brs):
    i = brs.index(br)
    return i + 1 if into == i else i


def _side_roles(d, br, side_idx):
    """br から見て side_idx ドメイン側(チェーン方向)に属する役割一覧(br 自身を含まず)。"""
    i = d["brs"].index(br)
    if side_idx <= i:
        dom_set = range(0, i + 1)
    else:
        dom_set = range(i + 1, d["K"])
    out = set()
    for di in dom_set:
        out.update(d["members"][di])
    out.discard(br)
    # 反対側 BR がチェーン上に居れば除外しない(その BR も side に属する)
    return sorted(out)


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------
def node_links(d, role):
    """role の (slot, seg_prefix, side, domain_idx) を列挙(生成順=slot順)。"""
    out, slot = [], 0
    for (a, b, dom_i), seg in zip(d["links"], d["segs"]):
        if a == role:
            out.append((slot, seg, 1, dom_i)); slot += 1
        elif b == role:
            out.append((slot, seg, 2, dom_i)); slot += 1
    return out


def _redist_line(d, br, into, wrong=False, with_rm=None, no_metric=False):
    src = d["doms"][_src_of(br, into, d["brs"])]
    sid = src["id"] + 7 if wrong else src["id"]
    src_txt = (f"ospf {sid} match internal external 1 external 2"
               if src["type"] == "ospf" else f"eigrp {sid}")
    tgt = d["doms"][into]
    if tgt["type"] == "eigrp":
        line = f"redistribute {src_txt}"
        if not no_metric:
            line += f" metric {EIGRP_METRIC}"
    else:
        line = f"redistribute {src_txt} subnets"
    if with_rm:
        line += f" route-map {with_rm}"
    return line


def render_node(d, role):
    m, lo = d["m"], d["lo"]
    out = ["! GEN-RDFIELD 初期", "interface Loopback0",
           f" ip address {lo[role]} 255.255.255.255", "!"]
    for slot, seg, side, _ in node_links(d, role):
        out += [f"interface {{{{ links[{slot}] }}}}",
                f" ip address {seg}.{side} 255.255.255.252", " no shutdown", "!"]
    # 参加ドメイン(役割から導出): BR=2つ / 内部=1つ
    my_doms = sorted({di for _, _, _, di in node_links(d, role)})
    fault_by_dir = {(f["br"], f["into"]): f for f in d["faults"]}
    # ★OSPF⇄OSPF 境界の BR は Lo の network を「先頭ドメインのみ」に出す。
    #   1 IF は同時に 1 OSPF プロセスにしか属せず、二重 network は片方が死に文になる
    #   (2026-07-29 GEN-RDFIELD-4471 でユーザ指摘→実機確認済)。非所有側ドメインへは
    #   redistribute の connected-subnets 随伴仕様で E2 として届く(到達性は不変)。
    ospf_doms = [di for di in my_doms if d["doms"][di]["type"] == "ospf"]
    dual_ospf_br = role in d["brs"] and len(ospf_doms) == 2
    for di in my_doms:
        dom = d["doms"][di]
        nets = [(seg, di2) for _, seg, _, di2 in node_links(d, role) if di2 == di]
        if dom["type"] == "ospf":
            out += [f"router ospf {dom['id']}", f" router-id {lo[role]}"]
            if not (dual_ospf_br and di != ospf_doms[0]):
                out.append(f" network {lo[role]} 0.0.0.0 area 0")
            out += [f" network {seg}.0 0.0.0.3 area 0" for seg, _ in nets]
        else:
            out += [f"router eigrp {dom['id']}",
                    f" network {lo[role]} 0.0.0.0", " no auto-summary"]
            out += [f" network {seg}.0 0.0.0.3" for seg, _ in nets]
        # BR: このドメインへの注入(健全 or 故障形)
        if role in d["brs"]:
            f = fault_by_dir.get((role, di))
            if f is None:
                out.append(" " + _redist_line(d, role, di))
            elif f["kind"] == "missing":
                pass
            elif f["kind"] == "wrong_id":
                out.append(" " + _redist_line(d, role, di, wrong=True))
            elif f["kind"] == "no_seed":
                out.append(" " + _redist_line(d, role, di, no_metric=True))
            elif f["kind"] == "filter":
                out.append(" " + _redist_line(d, role, di, with_rm="RM-SVC"))
        out.append("!")
    # filter 故障の route-map / prefix-list(グローバル)
    for f in d["faults"]:
        if f["kind"] == "filter" and f["br"] == role:
            vlo = lo[f["victim"]]
            out += [f"ip prefix-list PL-SVC seq 5 permit {vlo}/32", "!",
                    "route-map RM-SVC deny 10", " match ip address prefix-list PL-SVC", "!",
                    "route-map RM-SVC permit 20", "!"]
    return out


# --------------------------------------------------------------------------
# 採点 / 解答 / 提示
# --------------------------------------------------------------------------
def build_model(d):
    lb = {d["m"][r]: d["lo"][r] for r in d["roles"]}
    links = [{"a": d["m"][a], "a_ip": f"{seg}.1", "b": d["m"][b], "b_ip": f"{seg}.2"}
             for (a, b, _), seg in zip(d["links"], d["segs"])]
    return {"loopbacks": lb, "links": links}


def _dom_label(dom):
    return f"OSPF {dom['id']}" if dom["type"] == "ospf" else f"EIGRP AS {dom['id']}"


def grading_text(d, prob_id):
    m = d["m"]
    mo = build_model(d)
    model_yaml = yaml.safe_dump(mo, sort_keys=False, allow_unicode=True,
                                default_flow_style=False)
    model_yaml = "\n".join("  " + ln for ln in model_yaml.splitlines())
    # BR 監査(方向別の redistribute 行 regex)＋フィルタ不在
    checks = []
    n_br = len(d["brs"])
    audit_pts = 15 if n_br == 1 else 10
    for br in d["brs"]:
        regs = []
        for into in [d["brs"].index(br), d["brs"].index(br) + 1]:
            # ★監査は「表示形」で照合する: iol-xe 17.15 は into-OSPF の `subnets` を
            #   暗黙化し running-config に表示しない(BL-058 知見)。config には書くが
            #   regex からは外す。
            line = _redist_line(d, br, into).replace(" subnets", "")
            regs.append("      - { regex: '" + line.replace(" ", " +") + "' }")
        checks.append(f"""  - name: "{m[br]}: 収容標準どおりの相互再配送(方向・参照ID・seed metric)"
    node: {m[br]}
    command: "show running-config | include redistribute"
    raw:
{chr(10).join(regs)}
    points: {audit_pts}""")
    nofil_pts = 25 if n_br == 1 else 10
    for br in d["brs"]:
        checks.append(f"""  - name: "{m[br]}: 再配送にフィルタ類が残っていない(収容標準=全 Loopback 相互到達)"
    node: {m[br]}
    command: "show running-config | include redistribute"
    raw:
      - {{ not_regex: "redistribute .*route-map" }}
    points: {nofil_pts}""")
    # 対岸学習の指紋: 端ドメインの代表ノードが反対端の Lo を外部経路で学習
    left = [r for r in d["members"][0] if r not in d["brs"]] or [d["brs"][0]]
    right = [r for r in d["members"][d["K"] - 1] if r not in d["brs"]] or [d["brs"][-1]]
    probe, target = left[0], right[-1]
    if probe == target:
        target = d["brs"][-1]
    pd = d["doms"][0]
    fp = ("distance 170" if pd["type"] == "eigrp" else "extern 2")
    checks.append(f"""  - name: "{m[probe]}: 対岸 {m[target]} の Loopback({d['lo'][target]}) を外部経路として学習"
    node: {m[probe]}
    command: "show ip route {d['lo'][target]}"
    raw:
      - {{ regex: 'Known via' }}
      - {{ regex: "{fp}" }}
    points: 10""")
    checks_txt = "\n".join(checks)
    return f"""# 自動生成 (gen_redist_field.py) {prob_id} K={d['K']} faults={[(f['br'], f['kind']) for f in d['faults']]}
problem: {prob_id}
total_points: 100
defaults:
  genie_os: iosxe
model:
{model_yaml}
invariants:
  - {{ type: reachability_all, name: "全ルータ間 Loopback 相互到達", points: 40 }}
  - {{ type: loop_free, name: "転送ループ無し", points: 10 }}
checks:
{checks_txt}
"""


def task_text(d, prob_id):
    m, doms = d["m"], d["doms"]
    dom_words = " / ".join(_dom_label(x) for x in doms)
    edges = []
    for (a, b, di), seg in zip(d["links"], d["segs"]):
        edges.append(f"  {m[a]} ── {m[b]}   ({_dom_label(doms[di])} / {seg}.0/30)")
    rows = []
    for r in d["roles"]:
        my_doms = sorted({di for _, _, _, di in node_links(d, r)})
        protos = " / ".join(_dom_label(doms[i]) for i in my_doms)
        rows.append(f"| {m[r]} | {protos} | `{d['lo'][r]}/32` |")
    brs_txt = "、".join(m[b] for b in d["brs"])
    # チケット(故障の張本人はぼかし、申告として観測事実だけ)
    tickets = []
    for i, f in enumerate(d["faults"], 1):
        if f["kind"] == "filter":
            v = m[f["victim"]]
            tickets.append(f"> {i}. 一部拠点から **{v} のサーバ({d['lo'][f['victim']]})にだけ届かない**。"
                           "他のアドレスは正常に見える、と申告あり。")
        else:
            side = [m[r] for r in _side_roles(d, f["br"], f["into"])]
            tickets.append(f"> {i}. **{'・'.join(side[:3])} 側の拠点**と他拠点の間の通信が"
                           "**全滅**しているとの申告(方向・範囲の裏取りはまだ)。")
    tickets_txt = "\n".join(tickets)
    diff = 5 if (len(d["faults"]) >= 2 or
                 any(f["kind"] in ("wrong_id", "no_seed") for f in d["faults"])) else 4
    return f"""# 問題 {prob_id} : 経路到達性障害チケット(難易度{diff})

## 状況
社内網は **{d['K']} つのルーティングドメイン({dom_words})** を数珠つなぎにした構成で、
境界ルータ({brs_txt})が相互再配送で各ドメインを結んでいる。昨夜、境界まわりの作業が
行われた形跡があり、今朝から下記のチケットが届いている。
**社内の収容標準(下記)に完全準拠**するよう調査・是正せよ。

## リンク一覧(L2 直結・アドレスは /30 の .1/.2)

```
{chr(10).join(edges)}
```

## ルータ / 参加プロトコル / Loopback

| ルータ | 参加プロトコル | Loopback |
|--------|----------------|----------|
{chr(10).join(sorted(rows))}

## トラブルチケット(申告のみ・裏取りはあなたの仕事)
{tickets_txt}

## 収容標準(抜粋)
1. 境界ルータは隣接ドメイン間で**相互再配送**を行い、**全ルータの Loopback が相互到達**すること。
2. **EIGRP への注入は seed metric `{EIGRP_METRIC}` を必須**とする。
3. **OSPF 出自の再配送は internal / external とも対象**(match internal external 1 external 2)。
4. 再配送への**フィルタ類(route-map / distribute-list)の適用は禁止**。
5. 参照するプロセス ID / AS 番号は本書のドメイン表記({dom_words})に一致させること。

## 制約
- 設定変更してよいのは境界ルータ({brs_txt})のみ。他は変更禁止(show・ping・traceroute は可)。
- 静的経路・デフォルトルート・ドメイン構成の変更による回避は不可。

## 備考
※ 設定変更後に経路が変わらない時は `clear ip route *` で再計算する。

## アクセス・採点
SSH `SUZUKI / CCNP`(mgmt は割当順に 10.1.10.11〜)。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
採点は **効果ベース(到達性)＋収容標準との突き合わせ監査**。
"""


def solution_md(d, prob_id):
    m = d["m"]
    parts = []
    for f in d["faults"]:
        dom = d["doms"][f["into"]]
        parent = (f"router ospf {dom['id']}" if dom["type"] == "ospf"
                  else f"router eigrp {dom['id']}")
        good = _redist_line(d, f["br"], f["into"])
        head = f"### {m[f['br']]} / {parent} ({f['kind']})"
        if f["kind"] == "missing":
            body = f"注入方向が丸ごと欠落。`{good}` を投入。"
        elif f["kind"] == "wrong_id":
            body = (f"redistribute の参照 ID が誤り(存在しないプロセス/AS を参照=無言で経路ゼロ)。"
                    f"誤行を `no` で除去し `{good}` を投入。")
        elif f["kind"] == "no_seed":
            body = (f"metric 欠落で EIGRP 注入が∞メトリック=不広告(config は在るのに効かない)。"
                    f"`{good}` を再投入(上書き)。")
        else:
            body = (f"route-map RM-SVC が {m[f['victim']]} の Lo({d['lo'][f['victim']]}/32) を "
                    f"deny(収容標準はフィルタ禁止)。`no redistribute ...` → `{good}` で貼り替え、"
                    "route-map/prefix-list も撤去。")
        parts.append(f"{head}\n{body}")
    roles_txt = ", ".join(f"{r}={m[r]}" for r in d["roles"])
    return f"""# 模範解答 : {prob_id}

## 役割の種明かし
{roles_txt}(ドメイン: {' / '.join(_dom_label(x) for x in d['doms'])})

## 故障と是正
{chr(10).join(parts)}

投入後 `clear ip route *`(対象 BR)。

## 教育核心
再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の**見た目の完備**と**実効**(show ip route / show ip protocols の
Redistributing 節)を突き合わせるのが切り分けの型。
"""


def fix_json(d):
    fixes = []
    for f in d["faults"]:
        dom = d["doms"][f["into"]]
        parent = (f"router ospf {dom['id']}" if dom["type"] == "ospf"
                  else f"router eigrp {dom['id']}")
        good = _redist_line(d, f["br"], f["into"])
        node = d["m"][f["br"]]
        if f["kind"] == "missing":
            fixes.append({"node": node, "parents": [parent], "lines": [good]})
        elif f["kind"] == "no_seed":
            fixes.append({"node": node, "parents": [parent], "lines": [good],
                          "match": "none"})
        elif f["kind"] == "wrong_id":
            bad_src = d["doms"][f["src"]]
            bad = (f"no redistribute {bad_src['type']} {bad_src['id'] + 7}")
            fixes.append({"node": node, "parents": [parent], "lines": [bad, good],
                          "match": "none"})
        else:
            src = d["doms"][f["src"]]
            src_word = f"{src['type']} {src['id']}"
            fixes.append({"node": node, "parents": [parent],
                          "lines": [f"no redistribute {src_word}", good],
                          "match": "none"})
            fixes.append({"node": node, "lines": ["no route-map RM-SVC",
                                                  "no ip prefix-list PL-SVC"],
                          "match": "none"})
    for n in sorted({d["m"][f["br"]] for f in d["faults"]}):
        fixes.append({"node": n, "exec": ["clear ip route *"]})
    return {"_comment": "gen_redist_field fix(仕様書どおりの再配送へ復旧)", "fixes": fixes}


# --------------------------------------------------------------------------
# shape=twoborder — 2点相互再配送(M2・gen_redist_mutual_ts の定石を匿名化+装飾して移植)
#   OSPF(pid) ⇄ EIGRP(AS) を境界2台が相互再配送。EIGRP外部AD=95固定(会社ポリシー)が
#   次善誘発の決定性キー。健全形=双方向+seed metric+タグ衛生(SET_TAG/BLOCK_TAG)。
#   故障は両境界に対称注入(mutual_ts と同じ・実機検証済の型)。
# --------------------------------------------------------------------------
M2_FAULTS = ["no_tag", "missing_o2e", "missing_e2o", "missing_seed_metric"]
M2_DIFF = {"no_tag": 5, "missing_o2e": 4, "missing_e2o": 4, "missing_seed_metric": 5}


def draw_twoborder(rnd, hard=False):
    d = {"shape": "twoborder"}
    d["pid"] = rnd.randint(1, 99)
    d["eas"] = rnd.randint(100, 899)
    d["tag"] = rnd.randint(100, 999)
    kinds = ["no_tag", "missing_seed_metric"] if hard else M2_FAULTS
    d["kind"] = rnd.choice(kinds)
    d["la1"] = rnd.random() < 0.6
    d["la2"] = d["la1"] and rnd.random() < 0.4
    d["lb1"] = rnd.random() < 0.6
    d["lb2"] = d["lb1"] and rnd.random() < 0.4
    roles = ["B1", "B2", "IA", "IB"] +         [r for r, f in [("LA1", "la1"), ("LA2", "la2"), ("LB1", "lb1"), ("LB2", "lb2")] if d[f]]
    d["roles"] = roles
    names = [f"RT{i:02d}" for i in range(1, len(roles) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(roles, names))
    used, lo = set(), {}
    for r in roles:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in used:
                used.add(k); lo[r] = f"{k}.{k}.{k}.{k}"; break
    d["lo"] = lo
    segn = ["ia1", "ia2", "bb", "ib1", "ib2"] +         [s for s, f in [("la1", "la1"), ("la2", "la2"), ("lb1", "lb1"), ("lb2", "lb2")] if d[f]]
    useg, seg = set(), {}
    for s in segn:
        while True:
            pq = (rnd.randint(0, 254), rnd.randint(0, 254))
            if pq != (1, 10) and pq not in useg:
                useg.add(pq); seg[s] = f"10.{pq[0]}.{pq[1]}"; break
    d["seg"] = seg
    return d


def m2_links(d):
    """(role_a, slot_a, role_b, slot_b, seg名, domain) domain: 'o'=OSPF / 'e'=EIGRP。"""
    L = [("IA", 0, "B1", 0, "ia1", "o"), ("IA", 1, "B2", 0, "ia2", "o"),
         ("B1", 1, "B2", 1, "bb", "e"),
         ("B1", 2, "IB", 0, "ib1", "e"), ("B2", 2, "IB", 1, "ib2", "e")]
    if d["la1"]:
        L.append(("IA", 2, "LA1", 0, "la1", "o"))
    if d["la2"]:
        L.append(("LA1", 1, "LA2", 0, "la2", "o"))
    if d["lb1"]:
        L.append(("IB", 2, "LB1", 0, "lb1", "e"))
    if d["lb2"]:
        L.append(("LB1", 1, "LB2", 0, "lb2", "e"))
    return L


def m2_node_links(d, role):
    out = []
    for a, sa, b, sb, s, dom in m2_links(d):
        if a == role:
            out.append((sa, s, 1, dom))
        elif b == role:
            out.append((sb, s, 2, dom))
    return sorted(out)


def m2_boundary_blocks(d):
    """(global_lines, ospf_extra, eigrp_extra) — 初期(故障注入済・両境界対称)。"""
    pid, eas, tag, metric = d["pid"], d["eas"], d["tag"], EIGRP_METRIC
    rmaps = ["route-map SET_TAG permit 10", f" set tag {tag}",
             "route-map BLOCK_TAG deny 10", f" match tag {tag}",
             "route-map BLOCK_TAG permit 20"]
    o2e_ok = [f"redistribute ospf {pid} metric {metric} route-map SET_TAG",
              "distribute-list route-map BLOCK_TAG in"]
    e2o = [f"redistribute eigrp {eas} subnets"]
    k = d["kind"]
    if k == "no_tag":
        return [], e2o, [f"redistribute ospf {pid} metric {metric}"]
    if k == "missing_o2e":
        return [], e2o, []
    if k == "missing_e2o":
        return rmaps, [], o2e_ok
    # missing_seed_metric
    return rmaps, e2o, [f"redistribute ospf {pid} route-map SET_TAG",
                        "distribute-list route-map BLOCK_TAG in"]


def m2_render(d, role):
    m, lo, seg = d["m"], d["lo"], d["seg"]
    pid, eas = d["pid"], d["eas"]
    out = ["! GEN-RDFIELD 初期", "interface Loopback0",
           f" ip address {lo[role]} 255.255.255.255", "!"]
    for slot, s, side, _ in m2_node_links(d, role):
        out += [f"interface {{{{ links[{slot}] }}}}",
                f" ip address {seg[s]}.{side} 255.255.255.252", " no shutdown", "!"]
    onets = [seg[s] for _, s, _, dom in m2_node_links(d, role) if dom == "o"]
    enets = [seg[s] for _, s, _, dom in m2_node_links(d, role) if dom == "e"]
    if role in ("B1", "B2"):
        gl, ospf_extra, eigrp_extra = m2_boundary_blocks(d)
        out += [f"router ospf {pid}", f" router-id {lo[role]}",
                f" network {lo[role]} 0.0.0.0 area 0"]
        out += [f" network {s}.0 0.0.0.3 area 0" for s in onets]
        out += [f" {x}" for x in ospf_extra] + ["!"]
        out += [f"router eigrp {eas}"]
        out += [f" network {s}.0 0.0.0.3" for s in enets]
        out += [" no auto-summary", " distance eigrp 90 95"]
        out += [f" {x}" for x in eigrp_extra] + ["!"]
        if gl:
            out += gl + ["!"]
    elif onets:   # OSPF 側(IA/LA*)
        out += [f"router ospf {pid}", f" router-id {lo[role]}",
                f" network {lo[role]} 0.0.0.0 area 0"]
        out += [f" network {s}.0 0.0.0.3 area 0" for s in onets] + ["!"]
    else:         # EIGRP 側(IB/LB*)
        out += [f"router eigrp {eas}", f" network {lo[role]} 0.0.0.0"]
        out += [f" network {s}.0 0.0.0.3" for s in enets]
        out += [" no auto-summary", "!"]
    return out


def m2_fix(d):
    pid, eas, tag, metric = d["pid"], d["eas"], d["tag"], EIGRP_METRIC
    rmap_def = ["route-map SET_TAG permit 10", f" set tag {tag}",
                "route-map BLOCK_TAG deny 10", f" match tag {tag}",
                "route-map BLOCK_TAG permit 20"]
    fixes = []
    for br in ("B1", "B2"):
        node = d["m"][br]
        k = d["kind"]
        if k == "no_tag":
            fixes += [{"node": node, "lines": rmap_def},
                      {"node": node, "parents": [f"router eigrp {eas}"], "match": "none",
                       "lines": [f"no redistribute ospf {pid}",
                                 f"redistribute ospf {pid} metric {metric} route-map SET_TAG",
                                 "distribute-list route-map BLOCK_TAG in"]}]
        elif k == "missing_o2e":
            fixes += [{"node": node, "lines": rmap_def},
                      {"node": node, "parents": [f"router eigrp {eas}"],
                       "lines": [f"redistribute ospf {pid} metric {metric} route-map SET_TAG",
                                 "distribute-list route-map BLOCK_TAG in"]}]
        elif k == "missing_e2o":
            fixes += [{"node": node, "parents": [f"router ospf {pid}"],
                       "lines": [f"redistribute eigrp {eas} subnets"]}]
        else:  # missing_seed_metric
            fixes += [{"node": node, "parents": [f"router eigrp {eas}"], "match": "none",
                       "lines": [f"no redistribute ospf {pid}",
                                 f"redistribute ospf {pid} metric {metric} route-map SET_TAG"]}]
    return {"_comment": f"twoborder kind={d['kind']} 両境界を健全形(双方向+タグ衛生+seed metric)へ。",
            "fixes": fixes}


def m2_grading(d, prob_id):
    m, lo = d["m"], d["lo"]
    model = {"loopbacks": {m[r]: lo[r] for r in d["roles"]},
             "links": [{"a": m[a], "a_ip": f"{d['seg'][s]}.1",
                        "b": m[b], "b_ip": f"{d['seg'][s]}.2"}
                       for a, _, b, _, s, _ in m2_links(d)]}
    rxa = lo["IA"].replace(".", "\\.")
    rxb = lo["IB"].replace(".", "\\.")
    pairs = [[m["B1"], m["IA"]], [m["B2"], m["IA"]], [m["IB"], m["IA"]],
             [m["IA"], m["IB"]], [m["B1"], m["IB"]], [m["B2"], m["IB"]]]
    grading = {"problem": prob_id, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "model": model,
               "invariants": [
                   {"type": "reachability_all", "name": "全ルータ間 Loopback 相互到達", "points": 30},
                   {"type": "optimal",
                    "name": "ドメイン内代表宛先への最短転送(再配送由来の次善が無い)",
                    "points": 40, "pairs": pairs},
                   {"type": "loop_free", "name": "転送ループ無し", "points": 10}],
               "checks": [
                   {"name": f"{m['IB']}: {lo['IA']}/32 を EIGRP外部(D EX)で学習(OSPF→EIGRP)",
                    "node": m["IB"], "command": "show ip route eigrp",
                    "raw": [{"regex": f"D EX\\s+{rxa}"}], "points": 10},
                   {"name": f"{m['IA']}: {lo['IB']}/32 を OSPF外部(O E2)で学習(EIGRP→OSPF)",
                    "node": m["IA"], "command": "show ip route ospf",
                    "raw": [{"regex": f"O E2\\s+{rxb}"}], "points": 10}]}
    return grading


def m2_task(d, prob_id):
    m, lo, seg = d["m"], d["lo"], d["seg"]
    pid, eas, tag = d["pid"], d["eas"], d["tag"]
    edges = []
    for a, _, b, _, s, dom in m2_links(d):
        label = f"OSPF {pid} area 0" if dom == "o" else f"EIGRP AS {eas}"
        edges.append(f"  {m[a]} ── {m[b]}   ({label} / {seg[s]}.0/30)")
    rows = []
    for r in d["roles"]:
        doms = {dom for _, _, _, dom in m2_node_links(d, r)}
        protos = (f"OSPF {pid} / EIGRP AS {eas}" if len(doms) == 2
                  else f"OSPF {pid}" if "o" in doms else f"EIGRP AS {eas}")
        rows.append(f"| {m[r]} | {protos} | `{lo[r]}/32` |")
    k = d["kind"]
    if k == "no_tag":
        ticket = (f"> 1. 監視チームから「**一部区間で経路が遠回り**になっている(同一ドメイン内の"
                  f"宛先なのに対向ドメインを経由するホップが見える)」との申告(範囲の裏取りはまだ)。")
    elif k == "missing_e2o":
        ticket = (f"> 1. **{m['IA']} 側の拠点**から EIGRP 側の宛先に**届かない**との申告"
                  f"(方向・範囲の裏取りはまだ)。")
    else:
        ticket = (f"> 1. **{m['IB']} 側の拠点**から OSPF 側の宛先に**届かない**との申告"
                  f"(方向・範囲の裏取りはまだ)。")
    return f"""# 問題 {prob_id} : 経路到達性障害チケット(難易度{M2_DIFF[k]})

## 状況
社内網は **OSPF {pid} ドメインと EIGRP AS {eas} ドメイン**を、**境界2台({m['B1']}、{m['B2']})** の
相互再配送で結ぶ冗長構成である。昨夜、境界まわりの作業が行われた形跡があり、
今朝から下記のチケットが届いている。**社内の収容標準(下記)に完全準拠**するよう調査・是正せよ。

## リンク一覧(L2 直結・アドレスは /30 の .1/.2)

```
{chr(10).join(edges)}
```

## ルータ / 参加プロトコル / Loopback

| ルータ | 参加プロトコル | Loopback |
|--------|----------------|----------|
{chr(10).join(sorted(rows))}

## トラブルチケット(申告のみ・裏取りはあなたの仕事)
{ticket}

## 収容標準(抜粋)
1. 境界2台は OSPF⇄EIGRP の**相互再配送**を行い、**全ルータの Loopback が相互到達**すること。
2. **EIGRP への注入は seed metric `{EIGRP_METRIC}` を必須**とする。
3. **2点相互再配送の再注入対策**: OSPF 出自の経路には**タグ `{tag}` を付与**し、
   境界の **EIGRP 受信(in)で自ドメイン発(タグ `{tag}`)を遮断**すること。
4. **EIGRP の AD は internal 90 / external 95 に固定(変更不可・会社ポリシー)**。
5. 経路は**最短**であること(再配送由来の次善経路・ループの残存は不適合)。

## 制約
- 設定変更してよいのは境界2台({m['B1']}、{m['B2']})のみ。他は変更禁止(show・ping・traceroute は可)。
- 静的経路・デフォルトルート・AD 変更・ドメイン構成の変更による回避は不可。

## 備考
※ 設定変更後に経路が変わらない時は `clear ip route *` で再計算する。

## アクセス・採点
SSH `SUZUKI / CCNP`(mgmt は割当順に 10.1.10.11〜)。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
採点は **効果ベース(到達性・最短・ループ不在)＋収容標準との突き合わせ**。
"""


def m2_solution_md(d, prob_id):
    m = d["m"]
    k = d["kind"]
    desc = {"no_tag": "双方向再配送はあるがタグ衛生(SET_TAG/BLOCK_TAG)が無く、OSPF発の経路が"
                      "対向境界の EIGRP 外部(AD95<110)として戻り**次善経路化**。両境界にタグ付与+受信遮断を実装",
            "missing_o2e": "OSPF→EIGRP 方向の再配送が両境界で欠落。タグ衛生込みで o2e を投入",
            "missing_e2o": "EIGRP→OSPF 方向の再配送が両境界で欠落。e2o(subnets)を投入",
            "missing_seed_metric": "o2e に seed metric が無く∞メトリックで不広告(config は存在)。metric 付きで再投入"}[k]
    roles_txt = ", ".join(f"{r}={m[r]}" for r in d["roles"])
    return f"""# 模範解答 : {prob_id} (shape=twoborder kind={k})

## 役割の種明かし
{roles_txt}(境界= {m['B1']}/{m['B2']}・OSPF内部代表= {m['IA']}・EIGRP内部代表= {m['IB']})

## 故障と是正
{desc}。是正は**両境界に対称**に行う(片側だけでは症状が残る)。
詳細の投入行は solution/fix.json のとおり。

## 教育核心
2点相互再配送では自ドメイン発の経路が対向境界から**外部経路として再注入**される。
EIGRP 外部 AD 95(<OSPF 110) の会社ポリシー下では次善経路化として顕在化(no_tag)。
対策の定石= **出自タグ+境界受信での自ドメイン発遮断**(SET_TAG/BLOCK_TAG)。
"""


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, choices=[1, 2], default=None)
    ap.add_argument("--fault", choices=FAULTS, default=None)
    ap.add_argument("--shape", choices=["chain", "twoborder", "ring"], default=None)
    ap.add_argument("--hard", action="store_true",
                    help="chain=K3+subtle保証 / twoborder=no_tag・seed_metric系 / ring=そのまま")
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    # shape 抽選(chain 50% / twoborder 25% / ring 25%)。ID は全 shape 共通 GEN-RDFIELD。
    roll = rnd.random()
    shape = a.shape or ("chain" if roll < 0.5 else "twoborder" if roll < 0.75 else "ring")
    prob_id = f"GEN-RDFIELD-{a.seed}"

    if shape == "ring":
        import gen_redist_arena as arena
        info = arena.generate(a.repo, a.seed, prob_id=prob_id)
        print(f"{info} shape=ring")
        return

    if shape == "twoborder":
        d = draw_twoborder(rnd, hard=a.hard)
        m = d["m"]
        pdir = f"{a.repo}/problems/{prob_id}"
        os.makedirs(f"{pdir}/initial", exist_ok=True)
        os.makedirs(f"{pdir}/solution", exist_ok=True)
        lab_links = []
        for ra, sa, rb, sb, s, _ in m2_links(d):
            lab_links.append({"a": m[ra], "a_if": sa, "b": m[rb], "b_if": sb})
        problem = {"id": prob_id,
                   "title": f"再配送フィールド shape=twoborder kind={d['kind']} (seed={a.seed})",
                   "exam": "ENARSI",
                   "topics": ["redistribution", "ospf", "eigrp", "topology-randomized",
                              "generated"],
                   "difficulty": M2_DIFF[d["kind"]], "topology": "generated", "access": "ssh",
                   "target_nodes": sorted(m.values()), "points": 100,
                   "lab": {"links": lab_links}}
        with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fh:
            fh.write(f"# 自動生成 (gen_redist_field.py) seed={a.seed} shape=twoborder "
                     f"kind={d['kind']} roles={ {r: m[r] for r in d['roles']} }\n")
            yaml.safe_dump(problem, fh, sort_keys=False, allow_unicode=True)
        for r in d["roles"]:
            with open(f"{pdir}/initial/{m[r]}.cfg.j2", "w", encoding="utf-8") as fh:
                fh.write("\n".join(m2_render(d, r)) + "\n")
        with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as fh:
            fh.write(f"# 自動生成 (gen_redist_field.py) {prob_id} shape=twoborder kind={d['kind']}\n")
            yaml.safe_dump(m2_grading(d, prob_id), fh, sort_keys=False, allow_unicode=True)
        with open(f"{pdir}/task.md", "w", encoding="utf-8") as fh:
            fh.write(m2_task(d, prob_id))
        with open(f"{pdir}/solution.md", "w", encoding="utf-8") as fh:
            fh.write(m2_solution_md(d, prob_id))
        with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as fh:
            json.dump(m2_fix(d), fh, ensure_ascii=False, indent=2)
        print(f"wrote problems/{prob_id} : shape=twoborder kind={d['kind']} "
              f"nodes={len(d['roles'])} pid={d['pid']} eas={d['eas']} tag={d['tag']}")
        return

    # ---- shape=chain(従来) ----
    d = draw(rnd, faults_n=(a.faults or (2 if a.hard else None)),
             fault_kind=a.fault, hard=a.hard)
    m = d["m"]

    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    lab_links = []
    for (ra, rb, _), seg in zip(d["links"], d["segs"]):
        sa = [s for s, sg, side, _ in node_links(d, ra) if sg == seg][0]
        sb = [s for s, sg, side, _ in node_links(d, rb) if sg == seg][0]
        lab_links.append({"a": m[ra], "a_if": sa, "b": m[rb], "b_if": sb})
    problem = {"id": prob_id,
               "title": f"再配送フィールド(ドメイングラフ抽選) seed={a.seed}",
               "exam": "ENARSI",
               "topics": ["redistribution", "ospf", "eigrp", "topology-randomized",
                          "generated"],
               "difficulty": 5, "topology": "generated", "access": "ssh",
               "target_nodes": sorted(m.values()), "points": 100,
               "lab": {"links": lab_links}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fh:
        fh.write(f"# 自動生成 (gen_redist_field.py) seed={a.seed} shape=chain "
                 f"faults={[(f['br'], f['into'], f['kind']) for f in d['faults']]} "
                 f"roles={ {r: m[r] for r in d['roles']} }\n")
        yaml.safe_dump(problem, fh, sort_keys=False, allow_unicode=True)

    for r in d["roles"]:
        with open(f"{pdir}/initial/{m[r]}.cfg.j2", "w", encoding="utf-8") as fh:
            fh.write("\n".join(render_node(d, r)) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as fh:
        fh.write(grading_text(d, prob_id))
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as fh:
        fh.write(task_text(d, prob_id))
    with open(f"{pdir}/solution.md", "w", encoding="utf-8") as fh:
        fh.write(solution_md(d, prob_id))
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as fh:
        json.dump(fix_json(d), fh, ensure_ascii=False, indent=2)

    print(f"wrote problems/{prob_id} : shape=chain K={d['K']} doms={[_dom_label(x) for x in d['doms']]} "
          f"nodes={len(d['roles'])} faults={[(m[f['br']], f['kind']) for f in d['faults']]}")


if __name__ == "__main__":
    main()
