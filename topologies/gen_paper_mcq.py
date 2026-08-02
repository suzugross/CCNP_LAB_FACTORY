#!/usr/bin/env python3
"""再配送 机上4択問題ジェネレータ (BL-080 Step1)。

紙面だけで解く ENARSI 筆記読解ドリル。gen_redist_field.py(chain) の抽選・故障注入を
そのまま素材にし、実機(CML)から show を収集して4択 Markdown を出力、ラボは必ず破棄する。

パイプライン(1問):
  1. 故障種別(missing / no_seed / filter)に合う sub-seed を探索(grf.draw リトライ)
  2. 使い捨て問題パック problems/PAPER-RD-<subseed>/ を書き出し(day0=故障入り)
  3. scripts/lab.sh provision → ブート/収束待ち → playbooks/paper_collect.yml で show 収集
  4. scripts/lab.sh teardown ＋ 問題パック削除(失敗時も必ず)
  5. questions/YYYYMMDD-NNN.md / answers/YYYYMMDD-NNN.md を生成

使い方:
  .venv/bin/python3 topologies/gen_paper_mcq.py --repo . --seed 1234 --count 3
  --no-lab      : CML に触れず文面だけ生成(show は PLACEHOLDER。テンプレ調整用)
  --keep-pack   : デバッグ用に problems/PAPER-RD-* を残す

冪等性: 同一 --seed → 同一のトポロジ・故障・選択肢・正解位置。
        show の生テキストのみ収集時刻依存(uptime 等)で揺れる。
"""
import argparse
import datetime
import glob
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_redist_field as grf  # noqa: E402  (chain 抽選・config 描画を素材として流用)
import gen_redist_arena as gra  # noqa: E402  (ring=再配送ループ抽選・config 描画を流用)
import gen_paper_pbr as gpp     # noqa: E402  (pbr=PBR×ワイルドカードACL・BL-081)
import gen_paper_urpf as gpu    # noqa: E402  (urpf=uRPF×ACL・BL-084)

KINDS = ["missing", "no_seed", "filter", "wrong_id"]
RING_KINDS = ["distance", "filter"]   # ring(ループ)の正解法軸(=arena の method)

# 基準(社内標準)の可変軸(exam・chain)。値も付与方式も抽選し、config・選択肢・要件を
# 連動させる。「default-metric は常にハズレ」等のメタ知識を封じるのが狙い。
METRIC_POOL = ["100000 100 255 1 1500", "1000000 100 255 1 1500",
               "10000 10 255 1 1500"]
ORIG_METRIC = grf.EIGRP_METRIC


def draw_policy(subseed):
    prnd = random.Random(subseed ^ 0x9019)
    return {"metric": prnd.choice(METRIC_POOL),
            "style": prnd.choice(["inline", "defmet"])}


def apply_seed_policy(lines, d, r, pol):
    """defmet ポリシー: BR の eigrp セクションで redistribute の inline metric を剥がし
    default-metric を注入する(no_seed 故障の対象セクションには入れない=それが故障)。"""
    if not pol or pol["style"] != "defmet":
        return lines
    f = d["faults"][0]
    is_br = r in d["brs"]
    out, cur_eigrp = [], None
    for ln in lines:
        if ln.startswith("router eigrp "):
            cur_eigrp = int(ln.split()[2])
            out.append(ln)
            fault_here = (r == f["br"] and f["kind"] == "no_seed"
                          and d["doms"][f["into"]]["type"] == "eigrp"
                          and d["doms"][f["into"]]["id"] == cur_eigrp)
            if is_br and not fault_here:
                out.append(f" default-metric {grf.EIGRP_METRIC}")
            continue
        if ln.startswith("router "):
            cur_eigrp = None
        if cur_eigrp and ln.startswith(" redistribute "):
            ln = ln.replace(f" metric {grf.EIGRP_METRIC}", "")
        out.append(ln)
    return out

# --exam の拠点オーバーレイ用(実試験の「拠点語彙で症状を語る」流儀の再現)
SITE_POOL = ["ロンドン", "フランクフルト", "シンガポール", "ダラス", "シドニー",
             "トロント", "サンパウロ", "ムンバイ", "ソウル", "ドバイ",
             "アムステルダム", "ヨハネスブルグ", "チューリッヒ", "オースティン"]


def assign_sites(d, rnd):
    """役割 -> 都市名。ルータ=拠点の代表(Loopback0 が拠点網の代弁)という約束。"""
    return dict(zip(d["roles"], rnd.sample(SITE_POOL, len(d["roles"]))))


# --------------------------------------------------------------------------
# 抽選: 故障種別に合う sub-seed を探索
# --------------------------------------------------------------------------
def pick_draw(qseed, kind, hard=False):
    """qseed 起点で決定的に探索し、kind の故障1本が成立する draw を返す。
    hard=True は K=3 固定(台数・設定ノイズ増)。故障は1本のまま(単一選択を保つ)。"""
    for k in range(300):
        s = qseed + k * 101
        try:
            d = grf.draw(random.Random(s), faults_n=1, fault_kind=kind, hard=hard)
        except SystemExit:
            continue
        if len(d["faults"]) == 1 and d["faults"][0]["kind"] == kind:
            return s, d
    raise SystemExit(f"kind={kind} が成立する seed が見つかりません(起点 {qseed})")


# --------------------------------------------------------------------------
# 使い捨て問題パック(展開用) — gen_redist_field.py main の chain 分岐と同形式
# --------------------------------------------------------------------------
def write_pack(repo, prob_id, d, subseed, extra=None, pol=None):
    m = d["m"]
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    lab_links = []
    for (ra, rb, _), seg in zip(d["links"], d["segs"]):
        sa = [s for s, sg, _, _ in grf.node_links(d, ra) if sg == seg][0]
        sb = [s for s, sg, _, _ in grf.node_links(d, rb) if sg == seg][0]
        lab_links.append({"a": m[ra], "a_if": sa, "b": m[rb], "b_if": sb})
    problem = {"id": prob_id,
               "title": f"机上問題スナップショット(使い捨て) seed={subseed}",
               "exam": "ENARSI", "topics": ["generated", "paper-mcq"],
               "difficulty": 4, "topology": "generated", "access": "ssh",
               "target_nodes": sorted(m.values()), "points": 100,
               "lab": {"links": lab_links}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fh:
        fh.write(f"# 自動生成 (gen_paper_mcq.py) 机上問題用・撤収後に削除される\n")
        yaml.safe_dump(problem, fh, sort_keys=False, allow_unicode=True)
    for r in d["roles"]:
        body = "\n".join(apply_seed_policy(grf.render_node(d, r), d, r, pol))
        if extra and m[r] in extra:
            body += "\n" + "\n".join(extra[m[r]])
        with open(f"{pdir}/initial/{m[r]}.cfg.j2", "w", encoding="utf-8") as fh:
            fh.write(body + "\n")
    return pdir


# --------------------------------------------------------------------------
# トポロジ多様化(exam・chain): 図の見慣れ対策。ドメイン内冗長リンク(三角形化)と
# 葉ノードを追加し、名前・リンク順・描画方向を振り直す。ドメイン間の注入点は
# 一切変えないので、grf.draw が保証する故障の決定性(木=リング不成立)は無傷。
# --------------------------------------------------------------------------
def augment_topology(d, rnd):
    deg = {r: 0 for r in d["roles"]}
    for a, b, _ in d["links"]:
        deg[a] += 1
        deg[b] += 1

    def new_seg():
        while True:
            p, q = rnd.randint(0, 254), rnd.randint(0, 254)
            seg = f"10.{p}.{q}"
            if (p, q) != (1, 10) and seg not in d["segs"]:
                return seg

    # 1) 葉ノード追加(0〜2台・IOLデータIF3本の範囲内)
    for i in range(rnd.choice([0, 1, 1, 2])):
        di = rnd.randrange(d["K"])
        anchors = [r for r in d["members"][di] if deg[r] < 3]
        if not anchors or len(d["roles"]) >= 9:
            continue
        anchor = rnd.choice(anchors)
        nr = f"XN{i + 1}"
        d["roles"].append(nr)
        d["members"][di].append(nr)
        d["links"].append((anchor, nr, di))
        d["segs"].append(new_seg())
        deg[nr] = 1
        deg[anchor] += 1
        used = {v.split(".")[0] for v in d["lo"].values()}
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and str(k) not in used:
                d["lo"][nr] = f"{k}.{k}.{k}.{k}"
                break
    # 2) ドメイン内の冗長リンク(0〜2本=三角形/メッシュ化。ECMP が経路表に現れる)
    for _ in range(rnd.choice([0, 1, 1, 2])):
        di = rnd.randrange(d["K"])
        mem = d["members"][di]
        cands = [(x, y) for xi, x in enumerate(mem) for y in mem[xi + 1:]
                 if deg[x] < 3 and deg[y] < 3
                 and not any({a, b} == {x, y} for a, b, _ in d["links"])]
        if not cands:
            continue
        x, y = rnd.choice(cands)
        d["links"].append((x, y, di))
        d["segs"].append(new_seg())
        deg[x] += 1
        deg[y] += 1
    # 3) リンク順(=スロット割当)と名前の振り直し・描画方向の抽選
    order = list(range(len(d["links"])))
    rnd.shuffle(order)
    d["links"] = [d["links"][i] for i in order]
    d["segs"] = [d["segs"][i] for i in order]
    names = [f"RT{i:02d}" for i in range(1, len(d["roles"]) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(d["roles"], names))
    d["_mmdir"] = rnd.choice(["LR", "LR", "TD", "RL"])


# --------------------------------------------------------------------------
# 赤ニシン(exam): 見た目は怪しいが実害ゼロの設定ノイズ。実機に流してから収集する
# ため「効いてしまったら経路表に出る」= 無害性を実機で保証できる。
# --------------------------------------------------------------------------
def _herring_objects(rnd, n, tgt_pool):
    """未適用の prefix-list / ACL / route-map 一式(グローバル定義のみ=無害)。"""
    lines, names = [], []
    for i in range(n):
        nm = f"{rnd.choice(['LEGACY', 'BACKUP', 'MIGR', 'OLD', 'STG'])}{i + 1}"
        tgt = rnd.choice(tgt_pool)
        acl = rnd.randint(10, 99)
        lines += [f"ip prefix-list PL-{nm} seq 5 deny {tgt}",
                  "ip prefix-list PL-" + nm + " seq 10 permit 0.0.0.0/0 le 32",
                  f"access-list {acl} deny   {tgt.split('/')[0]}",
                  f"access-list {acl} permit any",
                  f"route-map RM-{nm} deny 10",
                  f" match ip address prefix-list PL-{nm}",
                  f"route-map RM-{nm} permit 20", "!"]
        names.append(f"RM-{nm}")
    return lines, names


def _herring_noop_section(rnd, proto, pid):
    """適用済みだが定常状態に無害な行(passive Lo0 / タイマー変更=非既定で表示される)。"""
    if proto == "ospf":
        extra = rnd.choice([" timers throttle spf 50 200 5000", None])
    else:
        extra = rnd.choice([" timers active-time 5", None])
    return ([f"router {proto} {pid}", " passive-interface Loopback0"]
            + ([extra] if extra else []) + ["!"])


def herrings_chain(d, rnd):
    """chain 用: 全BR+ランダム1〜2台に赤ニシンを撒く。戻り値=(追記dict, BR上のRM名)。"""
    m = d["m"]
    pool = [f"{d['lo'][r]}/32" for r in d["roles"]]
    targets = list(dict.fromkeys(
        list(d["brs"]) + rnd.sample(d["roles"], min(2, len(d["roles"])))))
    extra, br_decoy = {}, None
    for r in targets:
        lines, names = _herring_objects(rnd, rnd.choice([1, 2]), pool)
        my = sorted({di for _, _, _, di in grf.node_links(d, r)})
        dom = d["doms"][rnd.choice(my)]
        lines += _herring_noop_section(rnd, dom["type"], dom["id"])
        extra[m[r]] = lines
        if r == d["faults"][0]["br"]:
            br_decoy = names[0]
    return extra, br_decoy


def herrings_ring(d, rnd):
    """ring 用: RC/RB(+ノイズ1台)に撒く。被害プレフィクスを deny する未適用リスト含む。"""
    m = d["m"]
    pool = [f"{v}/32" for v in d["lo"].values()] + [f"{d['p_net']}.0/24"]
    noise = [r for r in d["roles"] if r.startswith("NO")]
    targets = ["RC", "RB"] + (rnd.sample(noise, 1) if noise else [])
    extra, rc_decoy = {}, None
    for r in targets:
        lines, names = _herring_objects(rnd, rnd.choice([1, 2]), pool)
        proto, pid = (("eigrp", d["eigrp_as"]) if r == "RC"
                      else ("ospf", d["ospf_pid"]))
        lines += _herring_noop_section(rnd, proto, pid)
        extra[m[r]] = lines
        if r == "RC":
            rc_decoy = names[0]
    return extra, rc_decoy


# --------------------------------------------------------------------------
# 証拠セット(故障種別ごとの「見せる show」カタログ) — BL-080 設計の中核
# --------------------------------------------------------------------------
def _prefer_internal(cands):
    ints = [r for r in cands if not r.startswith("BR")]
    return ints or cands


def evidence_plan(d, rnd, hard=False, exam=False):
    """観測ノード・設定抜粋ノード・checks(node×command) を決める。
    hard=True は BR の show ip protocols を出さない(Redistributing 節が実効状態を
    ほぼ明かすため。route 表と config の突き合わせだけで切り分けさせる)。
    exam=True はさらに証拠ダイエット: 答えに直行する targeted show
    (show ip route <victim>)も出さない。full の経路表と config から自分で欠落に気づく。"""
    f = d["faults"][0]
    br, into, src = f["br"], f["into"], f["src"]
    # 症状ノード = 注入先ドメインの非BRメンバ(居なければ同ドメインの他BR)
    sym_c = [r for r in d["members"][into] if r != br]
    symptom = rnd.choice(_prefer_internal(sym_c))
    # 対比ノード = 出自側(こちらは対岸が見えている)。filter は被害者以外を優先
    con_c = [r for r in grf._side_roles(d, br, src) if r != br]
    if f["kind"] == "filter":
        non_v = [r for r in con_c if r != f["victim"]]
        con_c = non_v or con_c
    contrast = rnd.choice(_prefer_internal(con_c))
    # 設定抜粋: 通常= 全BR + 出自側内部1台(+足りなければ症状ノード)。
    # exam= 全ルータ(図からプロトコル情報を消すので、ドメイン再構築の材料を全量渡す)
    if exam:
        cfg_nodes = sorted(d["roles"], key=lambda r: d["m"][r])
    else:
        cfg_nodes = list(d["brs"]) + [contrast]
        if len(cfg_nodes) < 3 and symptom not in cfg_nodes:
            cfg_nodes.append(symptom)
    m = d["m"]
    checks = [{"node": m[symptom], "command": "show ip route"},
              {"node": m[contrast], "command": "show ip route"}]
    if exam:
        # 情報量を上げる: 無関係ルータの full 経路表を1枚混ぜる(重要な表の選別も仕事に)
        extra_c = [r for r in d["roles"] if r not in (symptom, contrast, br)]
        if extra_c:
            checks.append({"node": m[rnd.choice(extra_c)], "command": "show ip route"})
    if not (hard or exam):
        checks.append({"node": m[br], "command": "show ip protocols"})
    if exam:
        # 全種別で無名のポリシー show を出す(「RM の show がある=filter問」のメタ封じ。
        # 赤ニシンの未適用 RM/PL/ACL もここに写る)
        for cmd in ("show route-map", "show ip prefix-list", "show access-lists"):
            checks.append({"node": m[br], "command": cmd, "optional": True})
    elif f["kind"] == "filter":
        vlo = d["lo"][f["victim"]]
        checks.append({"node": m[symptom], "command": f"show ip route {vlo}"})
        checks.append({"node": m[br], "command": "show route-map RM-SVC"})
        checks.append({"node": m[br], "command": "show ip prefix-list PL-SVC"})
    for n in cfg_nodes:
        checks.append({"node": m[n], "command": "show running-config | section router"})
    return {"symptom": symptom, "contrast": contrast, "cfg_nodes": cfg_nodes,
            "checks": checks}


# --------------------------------------------------------------------------
# 選択肢(故障種別ごとのテンプレ+seed差し替え)
# --------------------------------------------------------------------------
def build_choices(d, rnd, plan=None, exam=False, pol=None):
    """[(text, is_correct, why_wrong), ...] を正解位置シャッフル済みで返す。
    exam=True は6択: 既存4(同ジャンル)+異ジャンルの尤もらしい修正2。
    pol.style=defmet では正解/標準外が反転する(default-metric が正・inline が標準外)。"""
    f = d["faults"][0]
    br, into, src = d["m"][f["br"]], f["into"], f["src"]
    tgt, srcd = d["doms"][into], d["doms"][src]
    tgt_p = f"router {'ospf' if tgt['type'] == 'ospf' else 'eigrp'} {tgt['id']}"
    rev_p = f"router {'ospf' if srcd['type'] == 'ospf' else 'eigrp'} {srcd['id']}"
    good = grf._redist_line(d, f["br"], into)
    wrong = grf._redist_line(d, f["br"], into, wrong=True)
    rev = grf._redist_line(d, f["br"], src)
    dm = ("default-metric " + (grf.EIGRP_METRIC if tgt["type"] == "eigrp"
                               else "20"))
    # defmet ポリシー(exam抽選): 標準= default-metric 集約。正解行は inline metric 無し・
    # inline 指定版は「直るが標準外」ディストラクタへ反転する。
    defmet = bool(pol and pol.get("style") == "defmet" and tgt["type"] == "eigrp")
    good_inline = good
    if defmet:
        good = grf._redist_line(d, f["br"], into, no_metric=True)
        wrong = grf._redist_line(d, f["br"], into, wrong=True, no_metric=True)
    if f["kind"] == "missing":
        if defmet:
            std_d = (f"{br} の {tgt_p} 配下に「{good_inline}」を追加する", False,
                     "経路は注入される(症状は改善する)が、seed metric の個別指定は"
                     "要件「default-metric への集約」に反する。")
        else:
            std_d = (f"{br} の {tgt_p} 配下に「{dm}」を追加する", False,
                     "default-metric は redistribute 文が存在して初めて意味を持つ。"
                     "注入そのものが欠落している本問では何も起きない。")
        c = [(f"{br} の {tgt_p} 配下に「{good}」を追加する", True, ""),
             (f"{br} の {tgt_p} 配下に「{wrong}」を追加する", False,
              "参照するプロセス/AS 番号が実在しない。IOS はエラーを出さず受理するが、"
              "対象プロセスが存在しないため経路は1本も注入されない。"),
             (f"{br} の {rev_p} 配下に「{rev}」を追加する", False,
              "逆方向の再配送は設定済みで正常(対比側の経路表で確認できる)。"
              "症状の原因である方向には作用しない。"),
             std_d]
    elif f["kind"] == "no_seed":
        # 既存行の引用は表示形(IOS は into-OSPF の subnets を暗黙化し表示しない)
        rev_d = (f"{br} の {rev_p} 配下の「{rev.replace(' subnets', '')}」に metric 20 を追加する",
                 False,
                 "逆方向(OSPF への注入)の設定であり、EIGRP 側で経路が広報されない"
                 "本問の症状には作用しない。逆方向は現に正常である。")
        if defmet:
            c = [(f"{br} の {tgt_p} 配下に「{dm}」を追加する", True, ""),
                 (f"{br} の {tgt_p} 配下で「{good_inline}」を設定する", False,
                  "経路は広報される(症状は改善する)が、seed metric の個別指定は"
                  "要件「default-metric への集約」に反する。"),
                 rev_d,
                 (f"{br} の {tgt_p} 配下に「redistribute connected」を追加する", False,
                  "境界ルータの接続セグメントしか対象にならない上、seed metric が"
                  "無効なままでは connected の注入も広告されない。")]
        else:
            c = [(f"{br} の {tgt_p} 配下で「{good}」を設定する", True, ""),
                 (f"{br} の {tgt_p} 配下に「{dm}」を追加する", False,
                  "経路は広報されるようになる(症状は改善する)が、要件"
                  "「seed metric の redistribute 文への直接指定」を満たさない。"),
                 rev_d,
                 (f"{br} の {tgt_p} 配下に「redistribute connected metric {grf.EIGRP_METRIC}」"
                  "を追加する", False,
                  "境界ルータの接続セグメントしか注入されない。対岸ドメインの Loopback 群は"
                  "connected ではないため症状は解消しない。")]
    elif f["kind"] == "wrong_id":
        bad_ref = (f"redistribute "
                   f"{'ospf' if srcd['type'] == 'ospf' else 'eigrp'} {srcd['id'] + 7}")
        rev_disp = rev.replace(" subnets", "")
        if defmet:
            wrong_inline = grf._redist_line(d, f["br"], into, wrong=True)
            metric_d = (f"{br} の {tgt_p} 配下の redistribute を「{wrong_inline}」に"
                        "置き換える", False,
                        "参照先のプロセス/AS が実在しない以上メトリックを与えても"
                        "注入は発生せず、個別指定は要件「default-metric への集約」にも反する。")
        else:
            metric_d = None
        c = [(f"{br} の {tgt_p} 配下で「no {bad_ref}」を実行し「{good}」を設定する",
              True, ""),
             (f"{br} の {tgt_p} 配下に「{good}」を追加する(既存行はそのまま)",
              False,
              "経路は注入されるようになる(症状は改善する)が、実在しないプロセス/AS への"
              "参照が残置され、要件「実在しないプロセスへの参照残置の禁止」を満たさない。"),
             metric_d if metric_d else
             (f"{br} の {tgt_p} 配下に「{dm}」を追加する", False,
              "参照先のプロセス/AS が実在しない以上、メトリックを与えても注入は発生しない。"
              "症状は解消しない。"),
             (f"{br} の {rev_p} 配下の「{rev_disp}」を削除して参照 ID を見直す", False,
              "逆方向の再配送は参照 ID も含めて正常(対比側の経路表で確認できる)。"
              "削除すればかえって逆方向の到達性を壊す。")]
    else:  # filter
        c = [(f"{br} の {tgt_p} 配下で redistribute から route-map RM-SVC を外し、"
              "route-map / prefix-list を削除する", True, ""),
             ("route-map RM-SVC のシーケンス 10 を deny から permit に変更する", False,
              "到達性は回復する(症状は改善する)が、再配送へのフィルタ適用が残る。"
              "要件「再配送へのフィルタ適用禁止」を満たさない。"),
             ("ip prefix-list PL-SVC に「seq 10 permit 0.0.0.0/0 le 32」を追加する", False,
              "PL-SVC は deny 節の match に使われているため、permit-all を足すと"
              "全経路が deny 10 に一致し全面遮断へ悪化する(被害の拡大)。"),
             (f"{br} の {rev_p} 配下の redistribute にも route-map RM-SVC を適用する", False,
              "フィルタの適用範囲を広げるだけで到達性は悪化しうる。"
              "要件「再配送へのフィルタ適用禁止」にも真っ向から反する。")]
    if exam and plan:
        sym = d["m"][plan["symptom"]]
        tgt_word = "OSPF" if tgt["type"] == "ospf" else "EIGRP"
        c += [(f"{sym} の {tgt_p} 配下で「no passive-interface <上流IF>」を設定する",
               False,
               "隣接関係は確立しており内部経路も学習済み。passive は本事象と無関係。"),
              (f"{br} で「clear ip route *」を実行する", False,
               "設定上の欠陥が原因であり、再計算しても状態は変わらない。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# Markdown 生成
# --------------------------------------------------------------------------
def mermaid(d, sites=None, blind=False):
    """blind=True(=exam): 図からプロトコル情報を消す。ドメイン境界の再構築は
    config(全ルータ提示)から解答者にやらせる — 「跨ぎルータ=容疑者」の即バレ防止。"""
    m, doms = d["m"], d["doms"]
    lines = ["```mermaid", f"graph {d.get('_mmdir', 'LR')}"]
    for r in sorted(d["roles"], key=lambda x: m[x]):
        my = sorted({di for _, _, _, di in grf.node_links(d, r)})
        protos = ("" if blind else
                  "<br/>" + " / ".join(grf._dom_label(doms[i]) for i in my))
        site = f"{sites[r]}<br/>" if sites else ""
        lines.append(f'  {m[r]}["{site}{m[r]}<br/>Lo0: {d["lo"][r]}/32{protos}"]')
    for (a, b, di), seg in zip(d["links"], d["segs"]):
        sa = [s for s, sg, _, _ in grf.node_links(d, a) if sg == seg][0]
        sb = [s for s, sg, _, _ in grf.node_links(d, b) if sg == seg][0]
        lab = f"{seg}.0/30<br/>{m[a]}:E0/{sa}=.1 {m[b]}:E0/{sb}=.2"
        if not blind:
            lab += f"<br/>{grf._dom_label(doms[di])}"
        lines.append(f'  {m[a]} ---|"{lab}"| {m[b]}')
    lines.append("```")
    return "\n".join(lines)


def topo_tables(d, sites=None, blind=False):
    """Mermaid 非対応プレビューでも解けるようにするテキスト表現(表＋リンク一覧)。
    sites 指定時は拠点列を先頭に足す(拠点網の代表 = そのルータの Loopback0 という約束)。
    blind=True はプロトコル情報を表からも消す(config から再構築させる)。"""
    m, doms = d["m"], d["doms"]
    rows = []
    for r in d["roles"]:
        my = sorted({di for _, _, _, di in grf.node_links(d, r)})
        protos = ("" if blind else
                  " " + " / ".join(grf._dom_label(doms[i]) for i in my) + " |")
        pre = f"| {sites[r]} " if sites else ""
        rows.append(f"{pre}| {m[r]} |{protos} `{d['lo'][r]}/32` |")
    edges = []
    for (a, b, di), seg in zip(d["links"], d["segs"]):
        sa = [s for s, sg, _, _ in grf.node_links(d, a) if sg == seg][0]
        sb = [s for s, sg, _, _ in grf.node_links(d, b) if sg == seg][0]
        dom_txt = "" if blind else f"{grf._dom_label(doms[di])} / "
        edges.append(f"  {m[a]}:E0/{sa}(.1) ── {m[b]}:E0/{sb}(.2)   "
                     f"{dom_txt}{seg}.0/30")
    if sites and blind:
        head = ("| 拠点 | ルータ | 拠点網(代表アドレス) |\n"
                "|------|--------|----------------------|\n")
    elif sites:
        head = ("| 拠点 | ルータ | 参加プロトコル | 拠点網(代表アドレス) |\n"
                "|------|--------|----------------|----------------------|\n")
    else:
        head = ("| ルータ | 参加プロトコル | Loopback0 |\n"
                "|--------|----------------|-----------|\n")
    return (head + "\n".join(sorted(rows))
            + "\n\nリンク一覧(接続・アドレス):\n```\n"
            + "\n".join(edges) + "\n```")


def _trim_route_table(text):
    """show ip route の凡例(Codes: ブロック)を落として抜粋らしくする。"""
    out, skipping = [], False
    for ln in text.splitlines():
        if ln.startswith("Codes:"):
            skipping = True
            continue
        if skipping:
            if ln.strip() == "" or not ln.startswith(" "):
                skipping = False
            else:
                continue
        out.append(ln.rstrip())
    return "\n".join([l for l in out if l.strip() != ""]).strip()


SYMPTOM_TEXT = {
    "missing": "いくつかのサイトの間において、通信が確立されることができない、"
               "ということが、報告されています。",
    "no_seed": "いくつかのルートが、期待されているとおりには、広告されていません。",
    "wrong_id": "いくつかのサイトの間において、通信が確立されることができない、"
                "ということが、報告されています。",
    "filter": None,  # victim を埋め込むため question_md 内で組み立て
}

FIXED_NOTE = "> **本問は機器に接続せずに解答すること。追加の show 実行は認めない。**"

# --------------------------------------------------------------------------
# 「Cisco 語」= 公式和訳の逐語訳調(conventions.md「問題文の文体規約」)。
# ★訳さなくてよい所を訳し / 訳してほしい所を訳さず / 同じ語の訳が文脈で揺れる。
# 訳語は seed で抽選し、問題ごと・箇所ごとに不統一を作る。
# --------------------------------------------------------------------------
TERMS = {
    "iface": ["インターフェイス", "インタフェース"],
    "route": ["ルート", "経路"],
    "config": ["構成", "コンフィギュレーション"],
    "verify": ["検証する", "確認する"],
    "network": ["ネットワーク", "網"],
    "reach": ["到達可能性", "リーチアビリティ"],
    "site": ["サイト", "拠点"],
    "device": ["デバイス", "装置"],
}


def cisco_terms(rnd):
    """訳語を抽選(主/副の2種を持ち、箇所により使い分けて不統一を演出する)。"""
    t = {}
    for k, v in TERMS.items():
        a = rnd.choice(v)
        b = [x for x in v if x != a][0]
        t[k], t[k + "2"] = a, b
    return t

# 要件の言い換えバリアント(意味は同一=正解一意性の装置は保つ)。exam では表現・並び・
# ダミー要件を seed で揺らし、「要件欄がいつも同じ」の暗記を封じる。{M}=seed metric。
REQ_VARIANTS = {
    "reach": [
        "すべてのルータのループバック・インターフェイス 0 (/32) が、"
        "すべてのドメインの間で、相互に到達可能であること。",
        "各サイトのネットワーク(ループバック 0)は、ドメインをまたいで、"
        "すべてのサイトから、到達されることができること。",
        "いずれのサイトからも、他のすべてのサイトのネットワークへの、"
        "IP リーチアビリティが、確保されていること。"],
    "seed": [
        "EIGRP へのルートの注入においては、redistribute のステートメントにおいて、"
        "シード・メトリック `{M}` が、直接に指定されなければなりません"
        "(default-metric による代替は、社内の標準の外にあるものです)。",
        "EIGRP へ再配送される際の初期のメトリックは `{M}` とし、そして、それぞれの "
        "redistribute のステートメントに、直接に記述されなければなりません"
        "(default-metric の使用は、認められていません)。",
        "シード・メトリック `{M}` は、redistribute のステートメントごとに、"
        "個別に指定されなければなりません"
        "(default-metric への集約は、監査に適合しません)。"],
    "seed_defmet": [
        "EIGRP へのルートの注入におけるシード・メトリックは、プロセスの配下の "
        "default-metric `{M}` によって、与えられなければなりません"
        "(redistribute のステートメントへの個別の指定は、社内の標準の外にあるものです)。",
        "EIGRP の初期のメトリックは、default-metric `{M}` へ集約されなければなりません"
        "(redistribute のステートメントごとの個別の指定は、監査に適合しません)。",
        "シード・メトリック `{M}` の付与は、default-metric の方式に統一されなければ"
        "なりません(redistribute のステートメントへの直接の記述は、認められていません)。"],
    "nofilter": [
        "再配送に対するフィルタ(route-map / distribute-list)の適用は、"
        "禁止されているところのものです。",
        "ルートの再配送に対して、フィルタ(route-map / distribute-list)が、"
        "適用されてはなりません。",
        "再配送される経路の、選択的な制限(route-map / distribute-list の適用)は、"
        "実施されてはなりません。"],
    "idmatch": [
        "redistribute によって参照されるところのプロセス ID / AS 番号は、"
        "その境界に実在する隣接のドメインのものと一致させられ、そして、"
        "実在しないプロセスへの参照が、残置されてはなりません。",
        "redistribute の参照先は、実在する隣接のプロセス/AS に限定され、"
        "無効な参照のステートメントが、コンフィギュレーションに残されてはなりません。",
        "存在しないプロセス/AS を参照するところの構成のステートメントが、"
        "残置されてはなりません(参照は、隣接のドメインの実際の ID に一致させます)。"],
}
REQ_DECOYS = [
    "スタティック・ルートおよび既定のルートによる迂回は、実施されてはなりません。",
    "ルーティング・プロトコルの種別およびプロセスの配置(ドメインの構成)は、"
    "変更されてはなりません。",
    "インタフェースの IP アドレッシングは、変更されてはなりません。",
    "管理のための構成(SSH / SNMP / NTP)に対して、変更が加えられてはなりません。",
    "本作業は、日中の時間帯において実施されるという理由により、"
    "対象外であるところのデバイスに対する構成の変更は、許可されていません。",
]


def chain_requirements(rnd, style="inline"):
    """exam 用: 言い換え抽選+ダミー1〜2+並びシャッフルの要件リスト(番号付き文字列)。
    style=defmet は seed metric の社内標準が「default-metric 集約」の世界(基準の可変)。"""
    seed_key = "seed_defmet" if style == "defmet" else "seed"
    reqs = [rnd.choice(REQ_VARIANTS[k]).replace("{M}", grf.EIGRP_METRIC)
            for k in ("reach", seed_key, "nofilter", "idmatch")]
    reqs += rnd.sample(REQ_DECOYS, rnd.choice([1, 2]))
    rnd.shuffle(reqs)
    return [f"{i}. {t}" for i, t in enumerate(reqs, 1)]


def exam_symptom_chain(d, plan, sites):
    """--exam: 症状を拠点語彙で語る(プレフィックス・対象ルータを書かない)。"""
    f = d["faults"][0]
    if f["kind"] == "filter":
        sv = sites[f["victim"]]
        return (f"複数のサイトから、{sv}のサイトへ到達することが、できない、"
                f"ということが、報告されています。{sv}のサイトが関与しないところの"
                "サイトの間の通信は、正常である、とのことです。")
    sA, sB = sites[plan["symptom"]], sites[plan["contrast"]]
    others = [r for r in d["members"][f["into"]]
              if r not in (f["br"], plan["symptom"])]
    extra = (f"{sites[others[0]]}のサイトからも、同様の申告が、上げられています。"
             if others else "影響を受けている範囲の全体は、まだ把握されていません。")
    return (f"{sA}のサイトのユーザーが、{sB}のサイトへ到達することが、できない、"
            f"ということが、報告されています。{extra}")


def build_cause_choices(d, plan, rnd, decoy=None, pol=None):
    """原因特定形の選択肢(6択): 正因1 + 同ジャンル(再配送系)の偽原因2〜3 + 異ジャンル2〜3。
    4故障型は相互排他な主張なので、同ジャンル偽原因は config 精読でしか消せない
    (=「再配送の問題」と分かってからが本番)。decoy=赤ニシン RM 名(未適用)があれば
    「その RM が拒否している」偽原因も混ぜる。全て提示済み証拠から消去可能。"""
    f = d["faults"][0]
    m = d["m"]
    br, into = m[f["br"]], f["into"]
    tgt = d["doms"][into]
    tgt_p = f"router {'ospf' if tgt['type'] == 'ospf' else 'eigrp'} {tgt['id']}"
    tgt_word = ("OSPF" if tgt["type"] == "ospf" else "EIGRP")
    sym, con = m[plan["symptom"]], m[plan["contrast"]]
    # 同ジャンルの主張カタログ(4故障型=相互排他。正因はそのまま、他2つは偽原因に使う)
    claim = {
        "missing": f"{br} の {tgt_p} 配下に redistribute が設定されていない",
        "wrong_id": f"{br} の {tgt_p} 配下の redistribute が、実在しないプロセス/AS を"
                    "参照している",
        "no_seed": f"{br} の {tgt_p} への redistribute に seed metric が指定されていない",
        "filter": f"{br} の redistribute に適用された route-map が特定の拠点網を"
                  " deny している",
    }
    defmet = bool(pol and pol.get("style") == "defmet" and tgt["type"] == "eigrp")
    if defmet:
        claim["no_seed"] = f"{br} の {tgt_p} に default-metric が設定されていない"
    refute = {
        "missing": "設定抜粋のとおり、当該境界の redistribute 文は存在する(欠落ではない)。",
        "wrong_id": ("redistribute 文自体が存在しないため誤参照の問題ではない。"
                     if f["kind"] == "missing" else
                     "参照 ID は隣接ドメインの実在プロセスと一致している。"),
        "no_seed": ("当該プロセスには default-metric が設定されている。" if defmet
                    else "当該 redistribute 行には seed metric が指定されている。"),
        "filter": "redistribute に route-map は適用されておらず、定義も存在しない。",
    }
    in_genre = {"missing": ["wrong_id", "filter"],
                "wrong_id": ["missing", "filter"],
                "no_seed": ["missing", "wrong_id"],
                "filter": ["missing", "wrong_id"]}[f["kind"]]
    pool = [
        (f"{sym} と隣接ルータの間で {tgt_word} のネイバー(隣接関係)が確立していない",
         f"{sym} の経路表に同一ドメインの内部経路(タイマー進行中)が載っており、"
         "隣接関係は確立している。"),
        (f"{sym} の {tgt_p} で、上流側インタフェースが passive-interface に"
         "設定されている",
         f"passive なら隣接自体が確立せず内部経路も学習できないが、{sym} の経路表には"
         "内部経路が存在する。"),
        (f"{sym} の {tgt_p} に Loopback0 の network 文が設定されていない",
         f"対向側 {con} の経路表には {sym} の拠点網が外部経路として載っており、"
         "広告は行われている(逆方向は健全)。"),
        (f"{br} と {sym} 側ドメインの間のリンクで MTU が一致していない",
         "経路表の経過タイマーが安定して進行しており、フラップの形跡がない。"),
    ]
    c = [(claim[f["kind"]], True, "")]
    c += [(claim[k], False, refute[k]) for k in in_genre]
    n_pool = 3
    if decoy and f["kind"] != "filter":
        c.append((f"{br} の route-map {decoy} が対象の経路を拒否している", False,
                  f"route-map {decoy} は定義されているだけで、どの redistribute にも"
                  "適用されていない(実効なし)。"))
        n_pool = 2
    c += [(t, False, why) for t, why in rnd.sample(pool, n_pool)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def question_md(d, plan, choices, collected, stamp, sites=None, blind=False,
                form="fix", reqs=None):
    f = d["faults"][0]
    m = d["m"]
    dom_words = " / ".join(grf._dom_label(x) for x in d["doms"])
    if sites:
        symptom = exam_symptom_chain(d, plan, sites)
    elif f["kind"] == "filter":
        symptom = (f"サーバ {d['lo'][f['victim']]} への到達性が一部の拠点で失われている"
                   "と報告されています。他の宛先への到達性は正常です。")
    else:
        symptom = SYMPTOM_TEXT[f["kind"]]
    # 現在の状態(show 抜粋) / 設定抜粋 の描画
    state, cfg = [], []
    for chk in plan["checks"]:
        body = collected.get((chk["node"], chk["command"]), "(未収集)")
        if chk["command"].startswith("show ip route"):
            body = _trim_route_table(body)
        block = f"```\n{chk['node']}# {chk['command']}\n{body.strip()}\n```"
        if chk["command"].startswith("show running-config"):
            cfg.append(block)
        else:
            state.append(block)
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
    else:
        q = ("この問題を解決し、そして、示されているところのすべての要件が"
             "満たされることを確実にするために、必要とされる手順は、どれですか。"
             "(1つを選択してください)")
    letters = [chr(65 + i) for i in range(len(choices))]
    opts = "\n".join(f"{l}. {t}" for l, (t, _, _) in zip(letters, choices))
    T = cisco_terms(random.Random(hash(stamp) & 0xFFFF))
    if blind:
        intro = ("あなたの会社のネットワークは、複数のルーティング・ドメインが、"
                 "境界のルータによって接続され、\nそして、相互の再配送という手段によって、"
                 f"すべての{T['site']}の{T['reach']}が提供されている、というものです。\n"
                 f"ルーティングの設計の詳細は、示されているところの{T['config']}から、"
                 "読み取られることが、期待されています。")
    else:
        intro = (f"あなたの会社のネットワークは、{d['K']} つのルーティング・ドメイン"
                 f"({dom_words})が、境界のルータによって接続され、\n"
                 f"そして、相互の再配送という手段によって、すべての{T['site']}の"
                 f"{T['reach']}が提供されている、というものです。")
    if sites:
        intro += (f"\n各{T['site']}のルータと、{T['site']}の{T['network']}との対応は、"
                  f"下記の表に示されているとおりです({T['site']}の{T['network']}の代表は、"
                  "当該ルータのループバック 0 です)。")
    if reqs is None:
        reqs = [
            "1. 全ルータの Loopback0 (/32) が、すべてのドメイン間で相互に到達可能であること。",
            f"2. EIGRP への経路注入は、redistribute 文で seed metric `{grf.EIGRP_METRIC}` "
            "を直接指定すること(default-metric による代替は社内標準外)。",
            "3. 再配送に対するフィルタ(route-map / distribute-list)の適用は禁止されていること。",
            "4. redistribute が参照するプロセス ID / AS 番号は、その境界に実在する隣接ドメインの"
            "ものと一致させ、実在しないプロセスへの参照を残置しないこと。"]
    return f"""# 問題 {stamp} : ルーティング到達性の分析

{FIXED_NOTE}

## トポロジ

{intro}

{mermaid(d, sites, blind)}

{topo_tables(d, sites, blind)}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{symptom}これは、意図された動作ではありません。示されているところの出力を、参照してください。

{chr(10).join(state)}

## 設定抜粋

{chr(10).join(cfg)}

## 設問

{q}

## 選択肢

{opts}
"""


def answer_md(d, plan, choices, stamp, master_seed, subseed, kind, prob_id,
              herr=None, pol=None):
    f = d["faults"][0]
    m = d["m"]
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, (_, ok, _) in zip(letters, choices) if ok][0]
    tgt = d["doms"][f["into"]]
    parent = f"router {'ospf' if tgt['type'] == 'ospf' else 'eigrp'} {tgt['id']}"
    kind_note = {
        "missing": "一方向の redistribute が丸ごと欠落(片側ドメインが対岸を全喪失)",
        "no_seed": "OSPF→EIGRP 注入の metric 欠落(∞メトリックで不広告。config は存在)",
        "filter": "redistribute に route-map が付き特定 Loopback だけ deny(部分喪失)",
        "wrong_id": "redistribute の参照プロセス/AS が誤り(config は一見完備・無言で経路ゼロ)",
    }[kind]
    wrongs = "\n".join(
        f"- **{l}**: {'(正解)' if ok else why}"
        for l, (t, ok, why) in zip(letters, choices))
    victim = (f"\n- フィルタ被害者: {m[f['victim']]} ({d['lo'][f['victim']]}/32)"
              if kind == "filter" else "")
    if herr:
        victim += ("\n- 赤ニシン: " + "・".join(sorted(herr))
                   + " に未適用の route-map/prefix-list/ACL と無害な適用行"
                   "(passive-interface Lo0 等)を混入(実害なし)")
    if pol:
        victim += (f"\n- 適用基準(可変): seed metric=`{pol['metric']}` / 付与方式="
                   f"{'default-metric 集約' if pol['style'] == 'defmet' else 'redistribute 文へ直接指定'}")
    fp = "D EX (external, AD 170)" if tgt["type"] == "eigrp" else "O E2"
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 注入した故障

- 種別: `{kind}` — {kind_note}
- 対象: {m[f['br']]} の {parent} への注入方向({grf._dom_label(d['doms'][f['src']])} 出自){victim}
- 生成: `gen_paper_mcq.py --seed {master_seed}`(sub-seed {subseed} / 展開パック {prob_id}・撤収済)

## 各選択肢の判定

{wrongs}

## 検証コマンドと期待される出力

- `show ip protocols`({m[f['br']]}): 対象プロセスの Redistributing 節に出自プロトコルが
  正しい ID・(EIGRP なら) metric 付きで載ること。
- `show ip route`(症状側 {m[plan['symptom']]}): 対岸 Loopback 群が `{fp}` として
  現れること。是正前は当該経路が不在(対比側 {m[plan['contrast']]} には最初からある)。
- 是正後に反映が遅い場合は境界ルータで `clear ip route *`。

## ENARSI ブループリント

- 1.0 Layer 3 Technologies — Troubleshoot redistribution (OSPF/EIGRP 間の相互再配送)
- 同 — Troubleshoot route filtering / seed metric・administrative distance の基本動作

## 教育核心

再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の見た目の完備と実効(show ip route / show ip protocols の Redistributing 節)を
突き合わせるのが切り分けの型(紙面でも同じ)。
"""


# --------------------------------------------------------------------------
# shape=ring — 再配送ループ(gen_redist_arena 流用・BL-080 Step2)
# --------------------------------------------------------------------------
def write_pack_ring(repo, prob_id, d, subseed, extra=None):
    m = d["m"]
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    problem = {"id": prob_id,
               "title": f"机上問題スナップショット(使い捨て) seed={subseed}",
               "exam": "ENARSI", "topics": ["generated", "paper-mcq"],
               "difficulty": 5, "topology": "generated", "access": "ssh",
               "target_nodes": sorted(m.values()), "points": 100,
               "lab": {"links": [{"a": m[x], "a_if": sa, "b": m[y], "b_if": sb}
                                 for x, sa, y, sb, _ in gra.links_of(d)]}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fh:
        fh.write("# 自動生成 (gen_paper_mcq.py) 机上問題用・撤収後に削除される\n")
        yaml.safe_dump(problem, fh, sort_keys=False, allow_unicode=True)
    for r in d["roles"]:
        body = "\n".join(gra.render_node(d, r))
        if extra and m[r] in extra:
            body += "\n" + "\n".join(extra[m[r]])
        with open(f"{pdir}/initial/{m[r]}.cfg.j2", "w", encoding="utf-8") as fh:
            fh.write(body + "\n")
    return pdir


def _ring_protos(d, r):
    return {"RE": f"BGP AS {d['bgp_as']}",
            "RC": "BGP / EIGRP / OSPF",
            "RA": f"EIGRP AS {d['eigrp_as']} / OSPF {d['ospf_pid']}",
            }.get(r, f"OSPF {d['ospf_pid']}")


def _ring_lo(d, r):
    return (f"{d['p_net']}.1/24 (`{d['p_net']}.0/24` を広告)"
            if r == "RE" else f"{d['lo'][r]}/32")


def mermaid_ring(d, sites=None, blind=False):
    m = d["m"]
    ospf_lbl = f"OSPF {d['ospf_pid']}"
    dom = {"ec": f"iBGP AS {d['bgp_as']}", "ca": f"EIGRP AS {d['eigrp_as']}"}
    lines = ["```mermaid", f"graph {d.get('_mmdir', 'LR')}"]
    for r in sorted(d["roles"], key=lambda x: m[x]):
        site = ""
        if sites:
            site = f"{sites[r]}{'(本社)' if r == 'RE' else ''}<br/>"
        protos = "" if blind else f"<br/>{_ring_protos(d, r)}"
        lines.append((f'  {m[r]}["{site}{m[r]}<br/>Lo0: {_ring_lo(d, r)}'
                      f'{protos}"]').replace("`", ""))
    for a, sa, b, sb, s in gra.links_of(d):
        label = f"{d['seg'][s]}.0/30<br/>{m[a]}:E0/{sa}=.1 {m[b]}:E0/{sb}=.2"
        if not blind:
            label += f"<br/>{dom.get(s, ospf_lbl)}"
        lines.append(f'  {m[a]} ---|"{label}"| {m[b]}')
    lines.append("```")
    return "\n".join(lines)


def topo_tables_ring(d, sites=None, blind=False):
    m = d["m"]
    ospf_lbl = f"OSPF {d['ospf_pid']} area 0"
    dom = {"ec": f"iBGP AS {d['bgp_as']}", "ca": f"EIGRP AS {d['eigrp_as']}"}
    rows = []
    for r in d["roles"]:
        pre = ""
        if sites:
            pre = f"| {sites[r]}{'(本社)' if r == 'RE' else ''} "
        protos = "" if blind else f" {_ring_protos(d, r)} |"
        rows.append(f"{pre}| {m[r]} |{protos} {_ring_lo(d, r)} |")
    edges = []
    for a, sa, b, sb, s in gra.links_of(d):
        dom_txt = "" if blind else f"{dom.get(s, ospf_lbl)} / "
        edges.append(f"  {m[a]}:E0/{sa}(.1) ── {m[b]}:E0/{sb}(.2)   "
                     f"{dom_txt}{d['seg'][s]}.0/30")
    if sites and blind:
        head = ("| 拠点 | ルータ | 拠点網 / 広告網 |\n"
                "|------|--------|------------------|\n")
    elif sites:
        head = ("| 拠点 | ルータ | 参加プロトコル | 拠点網 / 広告網 |\n"
                "|------|--------|----------------|------------------|\n")
    else:
        head = ("| ルータ | 参加プロトコル | Loopback0 / 広告網 |\n"
                "|--------|----------------|--------------------|\n")
    return (head + "\n".join(sorted(rows))
            + "\n\nリンク一覧(接続・アドレス):\n```\n"
            + "\n".join(edges) + "\n```")


def evidence_plan_ring(d, rnd, exam=False):
    """ループ問の証拠セット: リング3点の経路詳細＋RC の BGP 表＋traceroute＋設定4枚。
    exam=True は証拠ダイエット: targeted 詳細ビュー3枚をやめ、RC の full 経路表1枚に
    (被害プレフィクスの行を自分で拾わせる)。"""
    m, p = d["m"], d["p_net"]
    if exam:
        checks = [{"node": m["RC"], "command": "show ip route"}]
        for cmd in ("show route-map", "show ip prefix-list", "show access-lists"):
            checks.append({"node": m["RC"], "command": cmd, "optional": True})
    else:
        checks = [{"node": m[r], "command": f"show ip route {p}.0"}
                  for r in ("RC", "RA", "RB")]
    checks.append({"node": m["RC"], "command": "show ip bgp"})
    noise = [r for r in d["roles"] if r.startswith("NO")]
    tracer = rnd.choice(noise) if noise else "RB"
    checks.append({"node": m[tracer],
                   "command": f"traceroute {p}.1 probe 1 timeout 1 ttl 1 8",
                   "optional": True})   # 症状の生映像(取れなければ黙って落とす)
    for r in ("RC", "RA", "RB", "RE"):
        checks.append({"node": m[r], "command": "show running-config | section router"})
    return {"tracer": tracer, "checks": checks}


def build_choices_ring(d, rnd, exam=False):
    """ループ問の選択肢(method=正解法)。exam=True は6択。"""
    m, p = d["m"], d["p_net"]
    rc, ra, rb = m["RC"], m["RA"], m["RB"]
    bas, eas, pid = d["bgp_as"], d["eigrp_as"], d["ospf_pid"]
    inj_e = d["ring"] == "inject_eigrp"
    return_ad = 110 if inj_e else 170
    # RC から見た「戻り経路の IGP」と「BGP を注入している IGP」
    ret_p = f"router ospf {pid}" if inj_e else f"router eigrp {eas}"
    inj_p = f"router eigrp {eas}" if inj_e else f"router ospf {pid}"
    dist_line = f"distance bgp 20 {return_ad - 5} {return_ad - 5}"
    dist_choice = (f"{rc} の router bgp {bas} 配下に「{dist_line}」を設定し、"
                   "clear ip route * を実行する")
    filt_choice = (f"{rc} で `{p}.0/24` のみ deny(他は permit)の prefix-list PL-BLOCK "
                   f"を作成し、{ret_p} 配下に「distribute-list prefix PL-BLOCK in」を適用する")
    # 対象違い: 戻り経路側ドメインの別ルータで AD を操作(RC の経路選択は変わらない)
    if inj_e:
        wrong_tgt = (f"{rb} の router ospf {pid} 配下に「distance ospf external "
                     f"{return_ad + 95}」を設定する")
        wrong_tgt_why = (f"{rb} 自身の RIB の選好が変わるだけで、ループの分岐点である "
                         f"{rc} の経路選択(iBGP か戻り外部経路か)には影響しない。")
    else:
        wrong_tgt = (f"{ra} の router eigrp {eas} 配下に「distance eigrp 90 "
                     f"{return_ad + 35}」を設定する")
        wrong_tgt_why = (f"{ra} は当該外部経路の広告側で、自身の RIB 選好を変えても"
                         f"ループの分岐点である {rc} の経路選択には影響しない。")
    no_ri = (f"{rc} の router bgp {bas} 配下から「bgp redistribute-internal」を削除する",
             "iBGP 学習経路の IGP への注入が止まりループは解消するが、IGP 側の全ルータが "
             f"`{p}.0/24` への経路を失い、要件「全拠点からの到達性」を満たさない。")
    clear_only = (f"{rc} で「clear ip bgp *」および「clear ip route *」を実行する",
                  "定常ループは経路の構造(戻り外部経路の AD が iBGP に勝つ)に起因するため、"
                  "再収束後も同一の状態に戻る。一時対処にもならない。")
    rm_inj = (f"{rc} の {inj_p} 配下の「redistribute bgp {bas} ...」に "
              f"`{p}.0/24` を deny する route-map を適用する")
    rm_inj_why = ("BGP から IGP への注入そのものを止めるため、IGP 側の全ルータが "
                  f"`{p}.0/24` への経路を失い、要件「全拠点からの到達性」を満たさない(戻りの遮断と"
                  "注入の遮断の混同)。")
    rm_ra = (f"{ra} の相互再配送(redistribute)の両方向に `{p}.0/24` を deny する "
             "route-map を適用する")
    rm_ra_why = (f"出自の一周は止まるが、{ra} の先のドメインの各ルータが "
                 f"`{p}.0/24` への経路を失い、要件「全拠点からの到達性」を満たさない。")
    if d["method"] == "distance":
        c = [(dist_choice, True, ""),
             (wrong_tgt, False, wrong_tgt_why),
             (no_ri[0], False, no_ri[1]),
             (clear_only[0], False, clear_only[1])]
        if exam:
            c += [(rm_inj, False, rm_inj_why), (rm_ra, False, rm_ra_why)]
    else:  # filter(監査で distance 禁止)
        c = [(filt_choice, True, ""),
             (dist_choice, False,
              "到達性・ループとも解消する(症状は直る)が、監査要件"
              "「管理距離(distance)の変更禁止」に違反する。"),
             (rm_inj, False, rm_inj_why),
             (rm_ra, False, rm_ra_why)]
        if exam:
            c += [(no_ri[0], False, no_ri[1]),
                  (clear_only[0], False, clear_only[1])]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def ring_requirements(d, rnd):
    """exam 用(ring): 言い換え抽選+ダミー+並びシャッフル。監査要件(distance禁止)は
    filter 解法のときのみ=正解一意性の装置なので存在自体は維持する。"""
    p, re_name = d["p_net"], d["m"]["RE"]
    core = [
        rnd.choice([
            f"すべてのルータが、`{p}.0/24` を含むところのすべての宛先"
            "(それぞれのループバック)へ、到達することができること。",
            f"顧客のネットワーク `{p}.0/24` を含むすべての宛先への到達可能性が、"
            "すべてのサイトにおいて、確保されていること。"]),
        rnd.choice([
            f"`{p}.0/24` 宛のパケットが、広告元である {re_name} の方向へ転送され、"
            "そして、転送のループが存在していないこと。",
            f"`{p}.0/24` 宛のトラフィックが {re_name} へ配送され、"
            "経路の周回(転送のループ)が、発生していないこと。"]),
        rnd.choice([
            "それぞれのドメインの間の再配送の設計は、維持されなければなりません"
            "(redistribute の削除・停止、または、スタティック・ルートによる回避は、"
            "許可されていません)。",
            "既存の再配送の設計(それぞれの境界の redistribute)が、変更または撤去"
            "されてはなりません。スタティック・ルートによる回避も、許可されていません。"]),
    ]
    if d["method"] == "filter":
        core.append(rnd.choice([
            "管理距離(administrative distance)の変更は、監査のポリシーによって、"
            "禁止されているところのものです。",
            "distance コマンドによる管理距離の操作は、監査のポリシー上、"
            "使用されることができません。"]))
    core += rnd.sample([x for x in REQ_DECOYS if "静的経路" not in x],
                       rnd.choice([1, 2]))
    rnd.shuffle(core)
    return [f"{i}. {t}" for i, t in enumerate(core, 1)]


def question_md_ring(d, plan, choices, collected, stamp, sites=None, blind=False,
                     reqs=None):
    m, p = d["m"], d["p_net"]
    state, cfg = [], []
    for chk in plan["checks"]:
        body = collected.get((chk["node"], chk["command"]), "(未収集)")
        if chk.get("optional") and _bad(body):
            continue
        if chk["command"].startswith("show ip route"):
            body = _trim_route_table(body)
        block = f"```\n{chk['node']}# {chk['command']}\n{body.strip()}\n```"
        (cfg if chk["command"].startswith("show running-config") else state).append(block)
    if reqs is None:
        reqs = [f"1. すべてのルータが `{p}.0/24` を含む全宛先(各 Loopback)へ到達できること。",
                f"2. `{p}.0/24` 宛のパケットが広告元 {m['RE']} の方向へ転送され、"
                "転送ループが存在しないこと。",
                "3. 各ドメイン間の再配送設計は維持すること"
                "(redistribute の削除・停止や静的経路による回避は不可)。"]
        if d["method"] == "filter":
            reqs.append("4. 管理距離(administrative distance)の変更は監査ポリシーにより"
                        "禁止されていること。")
    letters = [chr(65 + i) for i in range(len(choices))]
    opts = "\n".join(f"{l}. {t}" for l, (t, _, _) in zip(letters, choices))
    if sites:
        hq = sites["RE"]
        intro = (f"本社({hq})の顧客のネットワークは、BGP AS {d['bgp_as']} の "
                 f"{m['RE']} によって、広告されています。\n"
                 "あなたの会社の内部は、BGP / EIGRP / OSPF という 3 つのドメインから"
                 "構成されており、そして、境界のいずれかにおいて、再配送が実施されています。\n"
                 "サイトと、ルータおよびアドレスとの対応は、下記の表に示されているとおりです。")
        symptom = (f"複数のサイトから、本社({hq})の顧客のネットワーク宛の通信が、"
                   "タイムアウトする、ということが、報告されています。\n"
                   "サイトの間(サイトのネットワークどうし)の通信は、正常です。\n"
                   "これは、意図された動作ではありません。示されているところの出力を、"
                   "参照してください。")
    else:
        intro = (f"本社の顧客のネットワーク `{p}.0/24` は、BGP AS {d['bgp_as']} の "
                 f"{m['RE']} によって、広告されています。\n"
                 "あなたの会社の内部は、BGP / EIGRP / OSPF という 3 つのドメインから"
                 "構成されており、そして、境界のいずれかにおいて、再配送が実施されています。")
        symptom = (f"複数のサイトから、`{p}.0/24` 宛の通信が、タイムアウトする、"
                   "ということが、報告されています。\n各ルータのループバック宛の通信は、"
                   "正常です。\nこれは、意図された動作ではありません。"
                   "示されているところの出力を、参照してください。")
    return f"""# 問題 {stamp} : ルーティング到達性の分析

{FIXED_NOTE}

## トポロジ

{intro}

{mermaid_ring(d, sites, blind)}

{topo_tables_ring(d, sites, blind)}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{symptom}

{chr(10).join(state)}

## 設定抜粋

{chr(10).join(cfg)}

## 設問

この問題を解決し、上記の要件をすべて満たすために必要な手順はどれですか。(1つ選択)

## 選択肢

{opts}
"""


def answer_md_ring(d, plan, choices, stamp, master_seed, subseed, prob_id,
                   herr=None):
    m, p = d["m"], d["p_net"]
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, (_, ok, _) in zip(letters, choices) if ok][0]
    inj_e = d["ring"] == "inject_eigrp"
    return_ad = 110 if inj_e else 170
    herr_note = ""
    if herr:
        herr_note = ("\n- 赤ニシン: " + "・".join(sorted(herr))
                     + " に未適用の route-map/prefix-list/ACL と無害な適用行を混入(実害なし)")
    victim = "O E2 (AD 110)" if inj_e else "D EX (AD 170)"
    loop_word = (f"{m['RC']} → {m['RB']} → {m['RA']} → {m['RC']}" if inj_e
                 else f"{m['RC']} → {m['RA']} → {m['RB']} → {m['RC']}")
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if ok else why}"
                       for l, (t, ok, why) in zip(letters, choices))
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態(故障ではなく設計の帰結)

- 種別: `ring/{d['method']}` — 再配送リングの定常ループ(ring={d['ring']})
- 機構: `{p}.0/24` は {m['RE']} が BGP 起点広告 → {m['RC']} が iBGP(AD 200) で学習。
  {m['RC']} が BGP を {'EIGRP' if inj_e else 'OSPF'} へ再配送し、{m['RA']} の相互再配送で
  出自が一周。戻ってきた {victim} が iBGP(200) に勝って {m['RC']} が採用
  → 定常転送ループ {loop_word}。
- 正解法: {d['method']}(distance=iBGP の AD を戻り {return_ad} 未満へ /
  filter=戻り経路を学習段で遮断。監査要件で出し分け)
- 生成: `gen_paper_mcq.py --shape ring --seed {master_seed}`
  (sub-seed {subseed} / 展開パック {prob_id}・撤収済){herr_note}

## 各選択肢の判定

{wrongs}

## 検証コマンドと期待される出力

- {m['RC']}: `show ip route {p}.0` が `Known via "bgp {d['bgp_as']}"` に変わること
  (是正前は `Known via "{'ospf' if inj_e else 'eigrp'}"`)。
- 任意ルータから `traceroute {p}.1` が {m['RE']} まで一直線(是正前はリングを周回)。
- distance 解の場合、投入だけでは BGP 表の `r>`(RIB-failure) が残るため
  `clear ip route *`(または clear ip bgp)で再計算が要る。

## ENARSI ブループリント

- 1.0 Layer 3 Technologies — Troubleshoot redistribution / routing loops
- 同 — Administrative distance の操作とその影響範囲(distance bgp / distance ospf external)

## 教育核心

既定 AD の並び(eBGP 20 / EIGRP内 90 / OSPF 110 / EIGRP外 170 / **iBGP 200**)。
再配送リングでは出自が一周して「自分が注いだ経路」が外部経路として戻り、
iBGP より強い AD で勝ってしまう。切り分けの型は
「`show ip bgp` の r>(RIB-failure) × `show ip route <prefix>` の Known via 不一致」。
"""


# --------------------------------------------------------------------------
# shape=pbr — PBR×ワイルドカードACL(gen_paper_pbr 流用・BL-081)
# --------------------------------------------------------------------------
def pick_draw_pbr(qseed, kind):
    """一意性検証(verify_choices)に通る draw を決定的に探索。"""
    for kk in range(200):
        s = qseed + kk * 131
        try:
            return s, gpp.draw(random.Random(s), kind=kind)
        except ValueError:
            continue
    raise SystemExit(f"pbr kind={kind} が成立する seed が見つかりません({qseed})")


def pick_draw_urpf(qseed, kind):
    for kk in range(200):
        s = qseed + kk * 137
        try:
            return s, gpu.draw(random.Random(s), kind=kind)
        except ValueError:
            continue
    raise SystemExit(f"urpf kind={kind} が成立する seed が見つかりません({qseed})")


def write_pack_pbr(repo, prob_id, d, subseed):
    m = d["m"]
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    problem = {"id": prob_id,
               "title": f"机上問題スナップショット(使い捨て) seed={subseed}",
               "exam": "ENARSI", "topics": ["generated", "paper-mcq"],
               "difficulty": 4, "topology": "generated", "access": "ssh",
               "target_nodes": sorted(m.values()), "points": 100,
               "lab": {"links": gpp.lab_links(d)}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fh:
        fh.write("# 自動生成 (gen_paper_mcq.py) 机上問題用・撤収後に削除される\n")
        yaml.safe_dump(problem, fh, sort_keys=False, allow_unicode=True)
    for r in d["roles"]:
        with open(f"{pdir}/initial/{m[r]}.cfg.j2", "w", encoding="utf-8") as fh:
            fh.write("\n".join(gpp.render_node(d, r)) + "\n")
    return pdir


def _pbr_site(d, sites, r):
    if not sites:
        return None
    suffix = {"DST": "(本社DC)", "HUB": "(コア)"}.get(r, "")
    return f"{sites[r]}{suffix}"


def pbr_requirements(d, rnd, sites):
    m = d["m"]
    a = _pbr_site(d, sites, "CLA") or m["CLA"]
    b = _pbr_site(d, sites, "CLB") or m["CLB"]
    t_txt = "・".join(f"`172.16.{o}.0/24`" for o in d["T"])
    e_txt = "・".join(f"`172.16.{o}.0/24`" for o in d["E"])
    core = [
        f"{a} および {b} のそれぞれのサイトから、業務のサービスのネットワーク "
        f"{t_txt} へ、到達することができること。",
        f"検証および隔離のためのネットワーク {e_txt} へは、ポリシーによる転送が、"
        "実施されてはなりません(到達が不可能であることが、正しい状態です)。",
        ("ポリシーの対象の指定は、1つのアクセス・リストのエントリによって、"
         "まかなわれなければなりません。"
         if d["world"] == "single" else
         "アクセス・リストは、対象であるところのネットワークのみに、一致させなければ"
         "なりません(対象外を含む指定は、監査に適合しません)。"),
        "PBR が適用されるポイント(インターフェイス)およびネクスト・ホップの設計は、"
        "変更されてはなりません。",
    ]
    core += rnd.sample([x for x in REQ_DECOYS if "静的経路" not in x], 1)
    rnd.shuffle(core)
    return [f"{i}. {t}" for i, t in enumerate(core, 1)]


def mermaid_pbr(d, sites=None):
    m = d["m"]
    lines = ["```mermaid", f"graph {d.get('_mmdir', 'LR')}"]
    lo_txt = "<br/>".join(f"172.16.{o}.0/24" for o in d["all_nets"])
    labels = {
        "HUB": f"{m['HUB']}",
        "DST": f"{m['DST']}<br/>{lo_txt}",
        "CLA": f"{m['CLA']}<br/>LAN 192.168.{d['lan_a']}.0/24",
        "CLB": f"{m['CLB']}<br/>LAN 192.168.{d['lan_b']}.0/24",
    }
    for r in d["roles"]:
        site = f"{_pbr_site(d, sites, r)}<br/>" if sites else ""
        lines.append(f'  {m[r]}["{site}{labels[r]}"]')
    seg = f"192.168.{d['seg']}.0/29"
    lines.append(f'  {m["HUB"]} ---|"{seg}<br/>{m["HUB"]}=.1 {m["DST"]}=.2"| {m["DST"]}')
    lines.append(f'  {m["HUB"]} ---|"192.168.{d["lan_a"]}.0/24 (.254)"| {m["CLA"]}')
    lines.append(f'  {m["HUB"]} ---|"192.168.{d["lan_b"]}.0/24 (.254)"| {m["CLB"]}')
    lines.append("```")
    return "\n".join(lines)


def question_md_pbr(d, plan, choices, collected, stamp, sites=None, form="fix",
                    reqs=None):
    m = d["m"]
    state, cfg = [], []
    for chk in plan["checks"]:
        body = collected.get((chk["node"], chk["command"]), "(未収集)")
        if chk.get("optional") and _bad(body):
            continue
        block = f"```\n{chk['node']}# {chk['command']}\n{body.strip()}\n```"
        (cfg if chk["command"].startswith("show running-config") else state).append(block)
    a = _pbr_site(d, sites, "CLA") or m["CLA"]
    b = _pbr_site(d, sites, "CLB") or m["CLB"]
    symptom = (f"{a}のサイトのサービスへの到達可能性が、要件において示されているとおり"
               f"ではない、ということが、報告されています。{b}のサイトは、"
               "要件のとおりに、動作しています。")
    if reqs is None:
        reqs = pbr_requirements(d, random.Random(0), sites)
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
    else:
        q = ("この問題を解決し、そして、示されているところのすべての要件が"
             "満たされることを確実にするために、必要とされる手順は、どれですか。"
             "(1つを選択してください)")
    letters = [chr(65 + i) for i in range(len(choices))]
    opts = "\n".join(f"{l}. {t}" for l, (t, _, _) in zip(letters, choices))
    return f"""# 問題 {stamp} : ポリシーによるルーティングのための分析

{FIXED_NOTE}

## トポロジ

コアのルータにおいて、ポリシー・ベース・ルーティング(PBR)という手段によって、
それぞれのサイトの LAN から、本社のデータ・センターのサービスのネットワークへの転送が、
制御されています。コアは、サービスのネットワークへのルーティングの情報を保持しておらず、
そして、ポリシーに一致したトラフィックのみが、ネクスト・ホップへ転送されます。

{mermaid_pbr(d, sites)}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{symptom}これは、意図された動作ではありません。示されているところの出力を、参照してください。

{chr(10).join(state)}

## 設定抜粋

{chr(10).join(cfg)}

## 設問

{q}

## 選択肢

{opts}
"""


def answer_md_pbr(d, plan, choices, stamp, master_seed, subseed, prob_id):
    m = d["m"]
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, (_, ok, _) in zip(letters, choices) if ok][0]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if ok else why}"
                       for l, (t, ok, why) in zip(letters, choices))
    kind_note = {
        "wc_narrow": "ワイルドカードが狭く対象の一部を取りこぼす(雛型ラボの 0.0.3.255 型)",
        "wc_wide": "ワイルドカードが広く隔離網まで一致(過剰転送)",
        "wc_bits": "非連続ワイルドカード(+16 ビット)で対象外に一致・対象の一部を欠落",
        "acl_dir": "extended ACL の送信元/宛先が逆(何にも一致しない)",
        "rm_no_match": "route-map に match が無く全トラフィックを吸引",
        "match_plist": "PBR で prefix-list を match(match 節が無視され全一致・PoC実測)",
    }[d["kind"]]
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 注入した故障

- 種別: `pbr/{d['kind']}` — {kind_note}
- 要件世界: {'1エントリ集約' if d['world'] == 'single' else '厳密一致(過剰マッチ禁止)'}
  (「直る候補」= {', '.join(d['_fixers']) or 'addmatch のみ'} のうち要件適合は1つ)
- 対象/隔離: T={{{', '.join(str(o) for o in d['T'])}}} / E={{{', '.join(str(o) for o in d['E'])}}}
  (第3オクテット・被覆はビット展開で機械検証済)
- 生成: `gen_paper_mcq.py --shape pbr --seed {master_seed}`
  (sub-seed {subseed} / 展開パック {prob_id}・撤収済)

## 各選択肢の判定

{wrongs}

## 検証コマンドと期待される出力

- クライアント発 ping: 対象網は `!!!!!`(100%)・隔離網は `U.U.U`(0%・コアが unreachable
  応答)となること。
- {m['HUB']}: `show access-lists` のマッチ数と `show route-map` の
  Policy routing matches が ping 発数に整合すること(0 のままなら match 不成立)。
- 是正後は対象網のみカウンタが増えること。

## ENARSI ブループリント

- 1.0 Layer 3 Technologies — Path control (PBR) / ACL・ワイルドカードマスク

## 教育核心

ワイルドカードは「範囲」でなく**ビットのすくい取り**(0.0.16.255 は {{X, X+16}} だけに
一致する)。PBR は match 不一致なら通常ルーティングに落ちる——本問の構成では
コアが経路を持たないため不達になり、ACL の被覆がそのまま到達性に写る。
また PBR の match に prefix-list を書くと match 節が無視され全トラフィックが
policy 適用される(IOL 17.15 実測)。カウンタ(ACL matches / Policy routing matches)が
切り分けの最短路。
"""


# --------------------------------------------------------------------------
# shape=urpf — uRPF×ACL (gen_paper_urpf 流用・BL-084)
# ★実機展開はしない(紙面専用): 証拠は PoC 実証済みの挙動から決定的に生成する。
#   (verification drops は「未設定なら統計行自体が無い」ため捏造でなく仕様の再現)
# --------------------------------------------------------------------------
def urpf_evidence(d, rnd):
    """紙面に出す show 出力を状態から決定的に組み立てる。"""
    st = gpu.state(d)
    m = d["m"]
    e, a, b = m["EDGE"], m["ISPA"], m["ISPB"]
    ifa, ifb = "Ethernet0/0", "Ethernet0/1"
    n_spoof, n_asym = 10, 10

    def ifblock(name, ip, mode, acl, applied, drops, suppressed):
        L = [f"{name} is up, line protocol is up",
             f"  Internet address is {ip}/30"]
        if applied:
            acl_txt = f" {acl}" if acl else ""
            L += [f"  IP verify source reachable-via {mode.upper()}{acl_txt}",
                  f"   {drops} verification drops",
                  f"   {suppressed} suppressed verification drops"]
        else:
            L.append("  IP verify source reachable-via is disabled")
        return "\n".join(L)

    # ISP-A 側: 対称のみ着信・スプーフ(IF不一致)が来る
    a_drop = n_spoof if gpu.spoof_dropped(d, st, "a") else 0
    # ISP-B 側: 非対称の正規フロー + 完全未広告スプーフ
    b_drop = 0
    b_sup = 0
    if st["b_applied"]:
        if gpu.spoof_dropped(d, st, "b"):
            b_drop += n_spoof
        if not gpu.flow_ok(d, st, "asym"):
            b_drop += n_asym                  # 正規フローまで破棄されている
        elif st["b_mode"] == "rx" and st["b_acl"]:
            b_sup = n_asym                    # ACL 許可= suppressed 側に計上
    blocks = [
        f"```\n{e}# show ip interface {ifa}\n" +
        ifblock(ifa, f"{d['link_a']}.1", st["a_mode"], st["a_acl"], True,
                a_drop, 0) + "\n```",
        f"```\n{e}# show ip interface {ifb}\n" +
        ifblock(ifb, f"{d['link_b']}.1", st["b_mode"], st["b_acl"],
                st["b_applied"], b_drop, b_sup) + "\n```",
    ]
    # 経路表(非対称の根拠: 非対称網は ISP-A 向き・実トラフィックは ISP-B 着信)
    rt = [f"{e}# show ip route | begin Gateway", "Gateway of last resort is not set",
          f"      {d['cust_sym']}.0/24 is subnetted, 1 subnets",
          f"O E2     {d['cust_sym']}.0 [110/20] via {d['link_b']}.2, {ifb}",
          f"      {d['cust_asym']}.0/24 is subnetted, 1 subnets",
          f"O E2     {d['cust_asym']}.0 [110/20] via {d['link_a']}.2, {ifa}"]
    blocks.append("```\n" + "\n".join(rt) + "\n```")
    # ACL(定義されているもの・無ければ「存在しない」ことが読めるよう空出力)
    acl_txt = "\n".join(gpu.acl_blocks(d, st)) or "(出力なし)"
    blocks.append(f"```\n{e}# show access-lists\n{acl_txt}\n```")
    # 構成抜粋
    cfg = [f"interface {ifa}", f" ip address {d['link_a']}.1 255.255.255.252"]
    if st["a_acl"]:
        cfg.append(f" ip verify unicast source reachable-via {st['a_mode']} {st['a_acl']}")
    else:
        cfg.append(f" ip verify unicast source reachable-via {st['a_mode']}")
    cfg += [f"interface {ifb}", f" ip address {d['link_b']}.1 255.255.255.252"]
    if st["b_applied"]:
        if st["b_acl"]:
            cfg.append(f" ip verify unicast source reachable-via {st['b_mode']} "
                       f"{st['b_acl']}")
        else:
            cfg.append(f" ip verify unicast source reachable-via {st['b_mode']}")
    blocks.append(f"```\n{e}# show running-config | section interface\n" +
                  "\n".join(cfg) + "\n```")
    return blocks, st


def urpf_requirements(d, rnd, sites):
    m = d["m"]
    h1, h2 = d["exc_host"], d["exc_host2"]
    core = [
        "エッジのルータの両方のアップリンクのインターフェイスにおいて、"
        "送信元アドレスの検証(anti-spoofing)が、有効にされていなければなりません。",
        f"監視のためのホストである {h1} および {h2} からの、"
        "正規のトラフィックが、破棄されてはなりません。",
        "着信のインターフェイスと一致しない送信元を持つところのトラフィックは、"
        "破棄されなければなりません。",
    ]
    if d["world"] == "host_exception":
        core.append("検証に対する例外は、個々のホストのアドレスに限定して、"
                    "アクセス・リストによって明示的に許可されなければなりません"
                    "(ネットワーク単位での許可は、認められていません)。")
    elif d["world"] == "net_exception":
        core.append("検証に対する例外は、当該のネットワークの単位で、"
                    "アクセス・リストによって許可されなければなりません"
                    "(個々のホストの列挙による運用は、認められていません)。")
    else:
        core.append("例外のリスト(アクセス・リスト)の運用は、"
                    "実施されてはなりません。検証のモードの選択によって対処すること。")
    core += rnd.sample([x for x in REQ_DECOYS if "スタティック" not in x], 1)
    rnd.shuffle(core)
    return [f"{i}. {t}" for i, t in enumerate(core, 1)]


def question_md_urpf(d, blocks, choices, stamp, sites=None, form="fix", reqs=None):
    m = d["m"]
    e, a, b = m["EDGE"], m["ISPA"], m["ISPB"]
    state_blocks = blocks[:4]
    cfg_blocks = blocks[4:]
    if reqs is None:
        reqs = urpf_requirements(d, random.Random(0), sites)
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
    else:
        q = ("この問題を解決し、そして、示されているところのすべての要件が"
             "満たされることを確実にするために、必要とされる手順は、どれですか。"
             "(1つを選択してください)")
    letters = [chr(65 + i) for i in range(len(choices))]
    opts = "\n".join(f"{l}. {t}" for l, (t, _, _) in zip(letters, choices))
    topo = (f"```\n"
            f"          {e} (エッジ・被験のデバイス)\n"
            f"   {'Ethernet0/0'} |            | {'Ethernet0/1'}\n"
            f"  {d['link_a']}.0/30      {d['link_b']}.0/30\n"
            f"        |                    |\n"
            f"      {a} (ISP-A)        {b} (ISP-B)\n```")
    return f"""# 問題 {stamp} : 送信元アドレスの検証のための分析

{FIXED_NOTE}

## トポロジ

あなたの会社のエッジのルータは、2つのアップリンクによって、2つのサービス・プロバイダへ
接続されている、というものです。顧客のネットワーク {d['cust_sym']}.0/24 および
{d['cust_asym']}.0/24 は、それぞれのプロバイダを経由して、広告されています。

{topo}

- 監視のためのホスト: `{d['exc_host']}` および `{d['exc_host2']}`
  ({d['cust_asym']}.0/24 の中に存在し、ISP-B 側から着信します)

## 要件

{chr(10).join(reqs)}

## 現在の状態

いくつかの事象が、報告されています。示されているところの出力を、参照してください。

{chr(10).join(state_blocks)}

## 設定抜粋

{chr(10).join(cfg_blocks)}

## 設問

{q}

## 選択肢

{opts}
"""


def answer_md_urpf(d, choices, stamp, master_seed, subseed):
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, (_, ok, _) in zip(letters, choices) if ok][0]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if ok else why}"
                        for l, (t, ok, why) in zip(letters, choices))
    kind_note = {
        "strict_on_asym": "非対称に広告される網の着信 IF に rx(strict) → 正規業務断",
        "loose_everywhere": "両 IF が any → RPF IF 不一致のスプーフが素通り",
        "acl_num_mismatch": "uRPF が参照する ACL 番号と定義された ACL 番号が不一致",
        "acl_wrong_host": "ACL の許可ホストが対象と違う",
        "acl_extended_form": "拡張番号帯・any→host(宛先側)に一致する形",
        "missing_on_uplink": "片側 IF に未適用",
    }[d["kind"]]
    world_note = {"host_exception": "例外はホスト単位の ACL のみ",
                  "net_exception": "例外はネットワーク単位の ACL",
                  "no_acl_ops": "例外リスト運用なし(モード選択で対処)"}[d["world"]]
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態

- 種別: `urpf/{d['kind']}` — {kind_note}
- 要件世界: {world_note}(「直る候補」= {', '.join(d['_works'])} のうち要件適合は1つ)
- 生成: `gen_paper_mcq.py --shape urpf --seed {master_seed}` (sub-seed {subseed})

## 各選択肢の判定

{wrongs}

## 検証コマンドと期待される出力

- `show ip interface <IF>`: `IP verify source reachable-via` の行と、
  **`N verification drops`** の増分。ACL で許可された分は
  `suppressed verification drops` に計上される。
- 正規の非対称フロー(監視ホスト発)の ping が 100% であること。

## ★この分野の最重要知見(BL-027 PoC 実証)

**偽装 ping の「失敗」を根拠にしてはならない。** 経路の無い送信元は uRPF が無くても
echo-reply が戻れず必ず 0% になる。ドロップの証拠は per-IF の
`verification drops` カウンタ一択(未設定なら統計行自体が存在しない)。
また **非対称ルーティング下で rx を無思慮に入れると正規通信が死ぬ**。

## ENARSI ブループリント

- 3.0 Infrastructure Security — uRPF (strict / loose)・ACL
"""


# --------------------------------------------------------------------------
# 展開・収集・撤収
# --------------------------------------------------------------------------
def sh(repo, args, **kw):
    print(f"  $ {' '.join(args)}", flush=True)
    return subprocess.run(args, cwd=repo, check=True, **kw)


def collect(repo, prob_id, checks, tag):
    """paper_collect.yml で show を収集し {(node, command): stdout} を返す。"""
    gen = f"{repo}/topologies/_generated/{prob_id}"
    os.makedirs(gen, exist_ok=True)
    cf, of = f"{gen}/paper_{tag}.json", f"{gen}/paper_{tag}_out.json"
    with open(cf, "w", encoding="utf-8") as fh:
        json.dump(checks, fh, ensure_ascii=False)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as vf:
        vf.write("CCNP\n")
        vpath = vf.name
    try:
        with open(f"{gen}/paper_collect.log", "a", encoding="utf-8") as lg:
            sh(repo, [f"{repo}/.venv/bin/ansible-playbook",
                      f"{repo}/playbooks/paper_collect.yml",
                      "-e", f"problem={prob_id}", "-e", f"checks_file={cf}",
                      "-e", f"out_file={of}", "--vault-password-file", vpath],
               stdout=lg, stderr=subprocess.STDOUT)
    finally:
        os.unlink(vpath)
    out = json.load(open(of, encoding="utf-8"))
    return {(c["node"], c["command"]): c.get("stdout", "") for c in out}


def _bad(text):
    return (not text.strip() or "console connect error" in text
            or "console execute error" in text or "not in testbed" in text)


def deploy_and_collect(repo, prob_id, d, plan, boot_wait, settle, tries=8):
    """provision → ブート待ち → 収束待ち → 本収集。teardown は呼び元 finally で。"""
    sh(repo, [f"{repo}/scripts/lab.sh", "provision", prob_id])
    print(f"  boot 待ち {boot_wait}s ...", flush=True)
    time.sleep(boot_wait)
    probe = [{"node": d["m"][r], "command": "show ip protocols | include Routing Protocol"}
             for r in d["roles"]]
    for t in range(tries):
        got = collect(repo, prob_id, probe, f"probe{t}")
        bad = [n for (n, _), v in got.items() if _bad(v)]
        if not bad:
            break
        print(f"  未応答 {bad} → 45s 後に再試行 ({t + 1}/{tries})", flush=True)
        time.sleep(45)
    else:
        raise RuntimeError(f"ブート待ちタイムアウト: {prob_id}")
    print(f"  収束待ち {settle}s ...", flush=True)
    time.sleep(settle)
    got = collect(repo, prob_id, plan["checks"], "final")
    optional = {(c["node"], c["command"]) for c in plan["checks"] if c.get("optional")}
    bad = [(n, c) for (n, c), v in got.items() if _bad(v) and (n, c) not in optional]
    if bad:
        raise RuntimeError(f"収集失敗: {bad}")
    return got


def teardown(repo, prob_id):
    """CML ラボと作業コピーを必ず破棄する(問題パックの削除は呼び元が最後に行う)。"""
    subprocess.run([f"{repo}/scripts/lab.sh", "teardown", prob_id], cwd=repo,
                   check=False)


# --------------------------------------------------------------------------
# 出題ファイル命名・漏えいリント
# --------------------------------------------------------------------------
def rebalance_position(repo, choices):
    """正解記号の3連続を防ぐ(直近2問の answers/ から正解記号を読み、同記号が続くなら
    選択肢を1つ回転)。分布はほぼ一様のまま「迷ったらC」的なメタ読みだけ潰す。"""
    files = sorted(glob.glob(f"{repo}/answers/*.md"))[-2:]
    recent = []
    for fp in files:
        mt = re.search(r"## 正解\n\n\*\*([A-H])\*\*", open(fp, encoding="utf-8").read())
        if mt:
            recent.append(mt.group(1))
    cur = "ABCDEFGH"[[i for i, c in enumerate(choices) if c[1]][0]]
    if len(recent) == 2 and recent[0] == recent[1] == cur:
        return choices[1:] + choices[:1]
    return choices


def next_stamp(repo, date):
    used = [int(mt.group(1)) for p in glob.glob(f"{repo}/questions/{date}-*.md")
            if (mt := re.search(rf"{date}-(\d{{3}})\.md$", p))]
    return f"{date}-{(max(used) + 1) if used else 1:03d}"


def leak_lint(text, tokens):
    hits = [t for t in tokens if t in text]
    if hits:
        raise RuntimeError(f"問題側に漏えいの疑い: {hits}")


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--date", default=None, help="YYYYMMDD(既定=今日)")
    ap.add_argument("--shape", choices=["chain", "ring", "pbr", "urpf", "mixed"],
                    default="chain",
                    help="chain=再配送欠落/誤設定系(既定) / ring=再配送リングの定常ループ(難5)"
                         " / pbr=PBR×ワイルドカードACL(BL-081)"
                         " / urpf=uRPF×ACL(BL-084・紙面専用)"
                         " / mixed=問題ごとに形・種別を抽選(ごちゃまぜ)")
    ap.add_argument("--kinds", default=None,
                    help=f"カンマ区切りで種別を明示(chain: {','.join(KINDS)} / "
                         f"ring: {','.join(RING_KINDS)}。既定=seedシャッフル巡回)")
    ap.add_argument("--hard", action="store_true",
                    help="chain 用高難度: K=3固定＋BRの show ip protocols を出さない")
    ap.add_argument("--exam", action="store_true",
                    help="実試験風: 症状を拠点語彙で記述(拠点オーバーレイ)＋証拠ダイエット"
                         "(targeted show 廃止・full 経路表と config のみ)")
    ap.add_argument("--no-lab", action="store_true",
                    help="CML に触れず文面のみ生成(show は PLACEHOLDER)")
    ap.add_argument("--keep-pack", action="store_true")
    ap.add_argument("--boot-wait", type=int, default=100)
    ap.add_argument("--settle", type=int, default=60)
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    date = a.date or datetime.date.today().strftime("%Y%m%d")
    os.makedirs(f"{repo}/questions", exist_ok=True)
    os.makedirs(f"{repo}/answers", exist_ok=True)

    # 既定は種別の巡回順も seed で混ぜる(--count 1 でも型が割れないように)。
    # qseeds の再現性を保つため base とは別の rng を使う。
    if a.shape == "mixed":
        kinds = None   # 問題ごとに shape/種別を抽選(--kinds は無視)
    else:
        pool = {"ring": RING_KINDS, "pbr": gpp.PBR_KINDS,
                "urpf": gpu.URPF_KINDS}.get(a.shape, KINDS)
        kinds = (a.kinds.split(",") if a.kinds
                 else random.Random(a.seed ^ 0x5EED).sample(pool, len(pool)))
        if not set(kinds) <= set(pool):
            raise SystemExit(f"--kinds({a.shape}) は {pool} から選ぶこと: {kinds}")
    base = random.Random(a.seed)
    qseeds = [base.randint(10**6, 10**7 - 1) for _ in range(a.count)]
    results = []
    for i, qseed in enumerate(qseeds):
        if a.shape == "mixed":
            roll = random.Random(qseed ^ 0xC0FE)
            r = roll.random()
            shape_i = ("ring" if r < 0.22 else "pbr" if r < 0.44
                       else "urpf" if r < 0.66 else "chain")
            kind = roll.choice({"ring": RING_KINDS, "pbr": gpp.PBR_KINDS,
                                "urpf": gpu.URPF_KINDS}.get(shape_i, KINDS))
        else:
            shape_i = a.shape
            kind = kinds[i % len(kinds)]
        if shape_i == "ring":
            subseed = qseed
            d = gra.draw(random.Random(subseed), method=kind)
        elif shape_i == "pbr":
            subseed, d = pick_draw_pbr(qseed, kind)
        elif shape_i == "urpf":
            subseed, d = pick_draw_urpf(qseed, kind)
        else:
            subseed, d = pick_draw(qseed, kind, hard=a.hard)
        prob_id = f"PAPER-RD-{subseed}"
        rnd = random.Random(subseed ^ 0xA5A5)
        # 基準(社内標準)の可変軸: exam×chain で seed metric 値・付与方式を抽選。
        # grf.EIGRP_METRIC を差し替えると config 描画・選択肢・要件が一括で追随する。
        grf.EIGRP_METRIC = ORIG_METRIC
        pol = None
        if a.exam and shape_i == "chain":
            pol = draw_policy(subseed)
            grf.EIGRP_METRIC = pol["metric"]
            augment_topology(d, random.Random(subseed ^ 0x70B0))
        elif a.exam:
            d["_mmdir"] = random.Random(subseed ^ 0x70B0).choice(["LR", "TD", "RL"])
        if shape_i == "ring":
            plan = evidence_plan_ring(d, rnd, exam=a.exam)
            choices = build_choices_ring(d, rnd, exam=a.exam)
        elif shape_i == "pbr":
            plan = gpp.evidence_plan(d, rnd)
            choices = gpp.build_choices_fix(d, rnd)
        elif shape_i == "urpf":
            plan = {"checks": []}          # 紙面専用(実機展開なし)
            choices = gpu.build_choices_fix(d, rnd)
        else:
            plan = evidence_plan(d, rnd, hard=a.hard, exam=a.exam)
            choices = build_choices(d, rnd, plan=plan, exam=a.exam, pol=pol)
        sites = assign_sites(d, rnd) if a.exam else None
        # 赤ニシン(exam): 未適用ポリシー+無害な適用行を config に混入(pbr は素で騒がしい)
        herr, decoy = None, None
        if a.exam and shape_i in ("chain", "ring"):
            herr, decoy = (herrings_ring(d, rnd) if shape_i == "ring"
                           else herrings_chain(d, rnd))
        # exam: 出題形式も seed で抽選(fix=是正手順 / cause=原因特定)。
        # cause 形は選択肢が別サブシステムの原因仮説になり、語彙で領域が割れない。
        form = "fix"
        if a.exam and shape_i == "chain" and rnd.random() < 0.5:
            form = "cause"
            choices = build_cause_choices(d, plan, rnd, decoy=decoy, pol=pol)
        elif a.exam and shape_i == "pbr" and rnd.random() < 0.5:
            form = "cause"
            choices = gpp.build_choices_cause(d, rnd)
        elif a.exam and shape_i == "urpf" and rnd.random() < 0.5:
            form = "cause"
            choices = gpu.build_choices_cause(d, rnd)
        choices = rebalance_position(repo, choices)
        reqs = None
        if a.exam:
            if shape_i == "ring":
                reqs = ring_requirements(d, rnd)
            elif shape_i == "pbr":
                reqs = pbr_requirements(d, rnd, sites)
            elif shape_i == "urpf":
                reqs = urpf_requirements(d, rnd, sites)
            else:
                reqs = chain_requirements(
                    rnd, style=pol["style"] if pol else "inline")
        # 進行表示に故障種別・対象ルータは出さない(実行者=解答者のネタバレ防止)
        print(f"[{i + 1}/{a.count}] sub-seed={subseed} nodes={len(d['roles'])}",
              flush=True)

        if shape_i == "urpf":
            collected = {}                 # 紙面専用: 実機展開・収集を行わない
        elif a.no_lab:
            collected = {(c["node"], c["command"]): "(PLACEHOLDER: --no-lab)"
                         for c in plan["checks"]}
        else:
            if shape_i == "ring":
                write_pack_ring(repo, prob_id, d, subseed, extra=herr)
            elif shape_i == "pbr":
                write_pack_pbr(repo, prob_id, d, subseed)
            else:
                write_pack(repo, prob_id, d, subseed, extra=herr, pol=pol)
            attempts, collected, err = 2, None, None
            for att in range(attempts):
                try:
                    collected = deploy_and_collect(repo, prob_id, d, plan,
                                                   a.boot_wait, a.settle)
                    break
                except Exception as e:
                    err = e
                    print(f"  展開/収集失敗({att + 1}/{attempts}): {e}", flush=True)
                finally:
                    teardown(repo, prob_id)   # ラボは成功/失敗を問わず必ず破棄
            if collected is None:
                # 失敗した問題のパックは原因調査用に残す(成功時は下で削除)
                print(f"  ★この問題はスキップ(sub-seed {subseed}): {err}", flush=True)
                print(f"    調査用に problems/{prob_id} を残しています", flush=True)
                continue
            if not a.keep_pack:
                shutil.rmtree(f"{repo}/problems/{prob_id}", ignore_errors=True)
                shutil.rmtree(f"{repo}/topologies/_generated/{prob_id}",
                              ignore_errors=True)

        stamp = next_stamp(repo, date)
        lint = [prob_id, "PAPER-RD", f"seed={subseed}", f"seed={a.seed}",
                "故障", "正解", "kind=", "method="]
        if shape_i == "ring":
            q_md = question_md_ring(d, plan, choices, collected, stamp, sites=sites,
                                    blind=a.exam, reqs=reqs)
            a_md = answer_md_ring(d, plan, choices, stamp, a.seed, subseed, prob_id,
                                  herr=herr)
            # 「ループ」「RIB-failure」は要件文・show ip bgp 凡例に正当に現れるため対象外
            lint += ["ring=", "inject_eigrp", "inject_ospf", "震源"]
        elif shape_i == "urpf":
            blocks, _st = urpf_evidence(d, rnd)
            q_md = question_md_urpf(d, blocks, choices, stamp, sites=sites,
                                    form=form, reqs=reqs)
            a_md = answer_md_urpf(d, choices, stamp, a.seed, subseed)
            lint += list(gpu.URPF_KINDS) + ["world=", "_works"]
        elif shape_i == "pbr":
            q_md = question_md_pbr(d, plan, choices, collected, stamp, sites=sites,
                                   form=form, reqs=reqs)
            a_md = answer_md_pbr(d, plan, choices, stamp, a.seed, subseed, prob_id)
            lint += ["wc_narrow", "wc_wide", "wc_bits", "acl_dir", "rm_no_match",
                     "match_plist", "world=", "fixer"]
        else:
            q_md = question_md(d, plan, choices, collected, stamp, sites=sites,
                               blind=a.exam, form=form, reqs=reqs)
            a_md = answer_md(d, plan, choices, stamp, a.seed, subseed, kind, prob_id,
                             herr=herr, pol=pol)
            lint += ["missing", "no_seed", "wrong_id"]
        leak_lint(q_md, lint)
        with open(f"{repo}/questions/{stamp}.md", "w", encoding="utf-8") as fh:
            fh.write(q_md)
        with open(f"{repo}/answers/{stamp}.md", "w", encoding="utf-8") as fh:
            fh.write(a_md)
        results.append((stamp, kind))
        print(f"  wrote questions/{stamp}.md + answers/{stamp}.md", flush=True)

    print("\n== 生成結果 ==")
    for stamp, _ in results:   # 種別は書かない(実行者が中身を推測できないように)
        print(f"  questions/{stamp}.md")
    if len(results) < a.count:
        print(f"  ★{a.count - len(results)} 問は展開失敗でスキップ(別 seed で再試行を)")


if __name__ == "__main__":
    main()
