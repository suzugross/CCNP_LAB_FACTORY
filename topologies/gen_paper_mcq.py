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
import zlib
import shutil
import subprocess
import sys
import tempfile
import time

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_redist_field as grf  # noqa: E402  (chain 抽選・config 描画を素材として流用)
import gen_redist_arena as gra  # noqa: E402  (ring=再配送ループ抽選・config 描画を流用)
import gen_redist_mp_ts as gmp  # noqa: E402  (mploop=同AD・メトリック差ループの盤面を流用)
import gen_paper_pbr as gpp     # noqa: E402  (pbr=PBR×ワイルドカードACL・BL-081)
import gen_paper_urpf as gpu    # noqa: E402  (urpf=uRPF×ACL・BL-084)
import gen_paper_bgpdbg as gpb  # noqa: E402  (bgpdbg=BGP debug 読解・記述式・BL-085)
import gen_paper_leakmap as gpk  # noqa: E402  (leakmap=EIGRP集約×リーク・BL-095)
import gen_paper_acl as gpl     # noqa: E402  (acl=ACL単独読解・BL-106)
import gen_paper_aclv6 as gp6   # noqa: E402  (aclv6=IPv6フィルタ・BL-106 P3)
import gen_paper_ospfv3pl as gpo  # noqa: E402  (ospfv3pl=OSPFv3 prefix-list・BL-097)
import gen_paper_v6redist as gpv  # noqa: E402  (v6redist=OSPFv3⇄EIGRPv6 相互再配送・BL-098)
import gen_paper_aaa as gpa    # noqa: E402  (aaa=IOS AAA(RADIUS)読解・BL-101)

KINDS = ["missing", "no_seed", "filter", "wrong_id"]
# ring(ループ)の正解法軸。arena の method をそのまま借りるが、tag は紙面専用の追加軸
# (初期 config は method に依存しない=どの解法でも同じ盤面。要件文で正解を一意化する)。
RING_KINDS = ["distance", "filter", "tag"]

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
_CLI_RE = re.compile(r"^(\S+) の (router \S+ \S+) 配下[でに]?(?:の)?.*?「([^」]+)」")


def _with_cli(d, ch):
    """説明形の選択肢から設定コマンド列を導出して4要素目に付ける(導出不能は None)。"""
    if len(ch) > 3:
        return ch
    txt, ok, why = ch[0], ch[1], ch[2]
    m = _CLI_RE.match(txt)
    if m and not txt.startswith("no "):
        node, parent, cmd = m.groups()
        # 「no <誤行>」を実行してから設定する型。★_CLI_RE の 「...」 は非貪欲なので
        #   この型では先頭の no 行を掴んでいる(cmd が no 行と同一になる) →
        #   設定行は「を実行し」の後ろから別途取る(取れなければ no 行だけにする)。
        m2 = re.search(r"「(no [^」]+)」を実行し(?:、)?「([^」]+)」", txt)
        lines = [m2.group(1), m2.group(2)] if m2 else [cmd]
        return (txt, ok, why, [parent] + [f" {x}" for x in lines])
    if "clear ip route" in txt:
        return (txt, ok, why, ["clear ip route *"])
    if "passive-interface" in txt:
        m3 = re.match(r"^(\S+) の (router \S+ \S+) 配下", txt)
        if m3:
            return (txt, ok, why, [m3.group(2), " no passive-interface <上流IF>"])
    if "route-map RM-SVC" in txt or "prefix-list PL-SVC" in txt:
        return (txt, ok, why, None)
    return (txt, ok, why, None)


def _cli_lines(parent, lines, pre=None):
    """設定コマンド列(親ブロック配下にぶら下げる)。"""
    return (pre or []) + [parent] + [f" {x}" for x in lines]


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
        src_word = (f"ospf {srcd['id']}" if srcd["type"] == "ospf"
                    else f"eigrp {srcd['id']}")
        c = [(f"{br} の {tgt_p} 配下で redistribute から route-map RM-SVC を外し、"
              "route-map / prefix-list を削除する", True, "",
              [tgt_p, f" no redistribute {src_word}", f" {good}",
               "no route-map RM-SVC", "no ip prefix-list PL-SVC"]),
             ("route-map RM-SVC のシーケンス 10 を deny から permit に変更する", False,
              "到達性は回復する(症状は改善する)が、再配送へのフィルタ適用が残る。"
              "要件「再配送へのフィルタ適用禁止」を満たさない。",
              ["no route-map RM-SVC deny 10", "route-map RM-SVC permit 10",
               " match ip address prefix-list PL-SVC"]),
             ("ip prefix-list PL-SVC に「seq 10 permit 0.0.0.0/0 le 32」を追加する", False,
              "PL-SVC は deny 節の match に使われているため、permit-all を足すと"
              "全経路が deny 10 に一致し全面遮断へ悪化する(被害の拡大)。",
              ["ip prefix-list PL-SVC seq 10 permit 0.0.0.0/0 le 32"]),
             (f"{br} の {rev_p} 配下の redistribute にも route-map RM-SVC を適用する", False,
              "フィルタの適用範囲を広げるだけで到達性は悪化しうる。"
              "要件「再配送へのフィルタ適用禁止」にも真っ向から反する。",
              [rev_p, f" {rev.replace(' subnets', '')} route-map RM-SVC"])]
    if exam and plan:
        sym = d["m"][plan["symptom"]]
        tgt_word = "OSPF" if tgt["type"] == "ospf" else "EIGRP"
        c += [(f"{sym} の {tgt_p} 配下で「no passive-interface <上流IF>」を設定する",
               False,
               "隣接関係は確立しており内部経路も学習済み。passive は本事象と無関係。"),
              (f"{br} で「clear ip route *」を実行する", False,
               "設定上の欠陥が原因であり、再計算しても状態は変わらない。")]
    c = [_with_cli(d, x) for x in c]
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


MESSY_MGMT_LABEL = "管理スイッチ<br/>10.1.10.0/26 (VRF MGMT)<br/>各機 E0/3 収容"


def messy_mermaid(block):
    """図の「読みやすすぎ」を殺す後処理(BL-087・ユーザ要望「もっとへんてこに・リアル寄りに」)。

    ★正確さは落とさない: 直下の**リンク一覧(表)が正典**で、図はその劣化コピー、
      という関係にする。図から情報を削っても解答に必要な事実は表に全部ある。
    - 宣言とエッジを混ぜてシャッフルし、一部のエッジは端点を反転 →
      dagre の配置が崩れて交差の多い図になる(整った木構造にならない)
    - エッジ・ラベルの粒度を不揃いに(全部 / セグメントのみ / IF のみ) →
      実際の構成図にある「描いた人の気分で情報量が違う」癖
    - 帯域外管理セグメント(実在: 各機の E0/3・VRF MGMT)を確率で描き足す →
      本物だが解には一切関係しない配線が増え、star 状に視線が散る
    決定的: block 本文の CRC から乱数を起こすので、同じ問題は毎回同じ図になる。
    """
    lines = block.splitlines()
    if len(lines) < 3 or not lines[0].startswith("```mermaid"):
        return block
    rnd = random.Random(zlib.crc32(block.encode("utf-8")))
    e_re = re.compile(r'^\s*(\S+)\s+---\|"(.*)"\|\s+(\S+)\s*$')
    d_re = re.compile(r'^\s*(\S+)\[(".*")\]\s*$')
    decls, edges, passthru = [], [], []
    for ln in lines[2:]:
        if ln.startswith("```") or not ln.strip():
            continue
        m = e_re.match(ln)
        if m:
            edges.append([m.group(1), m.group(2), m.group(3)])
            continue
        m = d_re.match(ln)
        if m:
            decls.append([m.group(1), m.group(2)])
            continue
        passthru.append(ln)

    # 機器の箱の形を一部だけ変える(実務の図が機種・作図者ごとに不揃いなのを真似る)
    base = rnd.choice(["[{}]", "({})", "[{}]"])
    alt = "({})" if base == "[{}]" else "[{}]"
    out_decl = [f"  {i}{(alt if rnd.random() < 0.3 else base).format(lab)}"
                for i, lab in decls]

    # ★エッジ・ラベルは描かない(2026-08-05・ユーザ指摘2回目で方針転換)。
    #   mermaid はラベルをエッジの**中点に固定**で置くため、宣言順シャッフルと
    #   端点反転でエッジがレイアウトを横断すると、中点がノードの箱の上に来るのを
    #   防ぐ手段が無い(短くしても発生確率が下がるだけ)。
    #   → 図は「どこがどこと繋がっているか」だけを負い、アドレス情報は
    #      直下のリンク一覧(表)に一本化する。衝突は構造的に起きなくなり、
    #      かつ「図だけ眺めて当たりを付ける」ことも出来なくなる(元々の狙いに合致)。
    out_edge = []
    for a, _lab, b in edges:
        if rnd.random() < 0.4:                            # 端点反転で back-edge を作る
            a, b = b, a
        out_edge.append(f"  {a} --- {b}")

    body = out_decl + out_edge
    rnd.shuffle(body)                                     # 宣言とエッジを混ぜる
    node_ids = [i for i, _ in decls]
    tail = []
    if len(node_ids) >= 4 and rnd.random() < 0.5:
        tail = ['  subgraph OOB["帯域外管理"]',
                f'    MGMTSW(["{MESSY_MGMT_LABEL}"])',
                '  end'] + [f"  {n} -.- MGMTSW" for n in node_ids]
    direction = rnd.choice(["LR", "TD", "RL", "BT", lines[1].split()[-1]])
    return "\n".join(["```mermaid", f"graph {direction}"]
                      + body + passthru + tail + ["```"])


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
        head = ("| 拠点 | ルータ | 拠点網 |\n"
                "|------|--------|----------------------|\n")
    elif sites:
        head = ("| 拠点 | ルータ | 参加プロトコル | 拠点網 |\n"
                "|------|--------|----------------|----------------------|\n")
    else:
        head = ("| ルータ | 参加プロトコル | Loopback0 |\n"
                "|--------|----------------|-----------|\n")
    return (head + "\n".join(sorted(rows))
            + "\n\nリンク一覧:\n```\n"
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

def render_options(choices, style="prose"):
    """選択肢の提示。style='cli' は設定コマンドのみを列挙する(ユーザ要望の第2形式)。
    choices の要素は (text, ok, why) または (text, ok, why, cli_lines)。"""
    letters = [chr(65 + i) for i in range(len(choices))]
    out = []
    for l, ch in zip(letters, choices):
        cli = ch[3] if len(ch) > 3 else None
        if style == "cli" and cli:
            body = "\n".join(cli)
            out.append(f"**{l}.**\n```\n{body}\n```")
        elif "\n" in ch[0]:
            # ★本文そのものが複数行(patch 形のコマンド列など)。素で並べると
            #   Markdown が段落に畳んで**一列に潰れる**(2026-08-08 ユーザ指摘)。
            #   CLI 行の配列を持たない選択肢もここで必ずコードブロックに入れる。
            out.append(f"**{l}.**\n```\n{ch[0]}\n```")
        else:
            out.append(f"{l}. {ch[0]}")
    # ★空行で区切る(2026-08-08): 改行1つだと Markdown が連続行を1段落に畳み、
    # 選択肢が全部つながって表示される(VSCode プレビュー・HTML とも)。
    return "\n\n".join(out)


def choice_style(rnd, choices, form):
    """提示形式の抽選: fix 形かつ全候補が CLI を持つときのみ 50% で cli。"""
    if form != "fix" or not all(len(c) > 3 and c[3] for c in choices):
        return "prose"
    return "cli" if rnd.random() < 0.5 else "prose"


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

# --------------------------------------------------------------------------
# 「不親切化」(BL-088・ユーザ要望): 括弧の補足を落とし、日本語版 Cisco 試験に
# ありがちな直訳調へ寄せる。★適用は要件文・導入文・症状文のみ。
# show 出力 / 表 / 選択肢 / コマンドには一切触れない(採点と再現性に関わるため)。
# --------------------------------------------------------------------------
_JA = re.compile(r"[ぁ-んァ-ヶ一-龥]")
_PAREN = re.compile(r"[(（]([^()（）]*)[)）]")
# 中黒でつないだカタカナ複合語(Cisco 和訳は中黒でなく空白か無区切りが多い)
_KATA_NAKAGURO = re.compile(r"([ァ-ヶー]{2,})・([ァ-ヶー]{2,})")
_LONG_VOWEL = [("ルータ", "ルーター"), ("フィルタ", "フィルター"),
               ("パラメータ", "パラメーター"), ("ヘッダ", "ヘッダー")]


def strip_parens(s):
    """括弧の補足を落とす。短い記法( (/32) (.254) )だけ残す。
    ★落として良いのは「本文だけで辛うじて読み取れる」補足に限る
      (制約の唯一の担い手になっている括弧は、事前に本文へ畳んである)。"""
    def rep(m):
        inner = m.group(1)
        if len(inner) <= 4 and not _JA.search(inner):
            return m.group(0)          # (/32) (.1) (.254) 等は残す
        return ""
    out = _PAREN.sub(rep, s)
    return re.sub(r"[、。]\s*(?=[、。])", "", out).replace(" 、", "、").strip()


def terse_jp(s, rnd=None):
    """括弧を落としたうえで、和訳版 Cisco 試験の癖を軽く混ぜる。
    ★揺らぎは箇所ごとに独立(文書内で不統一なのが本物の癖)。"""
    if rnd is None:
        rnd = random.Random(zlib.crc32(s.encode("utf-8")))
    s = strip_parens(s)
    if rnd.random() < 0.5:             # 中黒 → 半角スペース(問題単位で寄せる)
        s = _KATA_NAKAGURO.sub(r"\1 \2", s)
        s = _KATA_NAKAGURO.sub(r"\1 \2", s)      # 3語連結の2回目
    for a, b in _LONG_VOWEL:           # 長音の揺れ(出現ごとに独立に抽選)
        if a in s:
            s = "".join(
                (b if (x == a and rnd.random() < 0.35) else x)
                for x in re.split(f"({a})", s))
    # 述語の直訳化(受動+義務の言い回しを混ぜる)
    if rnd.random() < 0.45:
        s = s.replace("されなければなりません", "される必要があります")
    if rnd.random() < 0.35:
        # ★「が…することはできません」は主体がずれて読める(態の崩れ)。
        #   受動を保った直訳形にする(Cisco 和訳の「〜されることはできません」)。
        s = s.replace("されてはなりません", "されることはできません")
    if rnd.random() < 0.3:
        s = s.replace("しなければなりません", "する必要があります")
    return s


# --------------------------------------------------------------------------
# 「道標(signpost)の除去」(BL-088・ユーザ要望「ぱっと見、何を問われているのかすら
# 分からないレベルに」)。★情報は1ビットも減らさない — 触るのは配置と道標だけで、
# 要件の中身・証拠・選択肢は現状維持(正解が一意に決まる性質を保つ)。
# 完成した Markdown に対する後処理として独立させてある(将来ラボ問の task.md にも
# 同じ関数を掛けられるように)。
# --------------------------------------------------------------------------
LEAD_IN = [
    "あなたは、ネットワークの運用を担当しています。",
    "あなたは、下記のネットワークの保守を担当する技術者です。",
    "あなたの組織は、下記に示されているところのネットワークを運用しています。",
]
DIRECTIVE = [
    "あなたは、示されているところの出力および構成に基づいて、その構成が、"
    "下記において記述されているとおりに動作していない理由を、判断する必要があります。",
    "あなたは、提示されているところの情報のみを使用して、要求されている状態が"
    "満たされていない理由を、特定しなければなりません。",
    "示されているところの出力および構成に基づいて、要求されているところの動作が"
    "得られていない理由が、判断されなければなりません。",
]
VAGUE_SYMPTOM = [
    "いくつかの宛先への通信について、報告が上がっています。",
    "一部の通信が、意図されているとおりに動作していない、という報告があります。",
    "ユーザーから、通信に関する事象が、報告されています。",
    "通信の一部において、想定されていない挙動が、観測されています。",
]
GENERIC_ASK = "次のうち、正しいものは、どれですか。"
# 導入から機構の名指しを抜く(config を読めば分かる=情報は失われない)
INTRO_DENAME = [
    ("そして、相互の再配送という手段によって、", "そして、"),
    ("相互の再配送という手段によって、", ""),
    ("ており、そして、境界のいずれかにおいて、再配送が実施されています。", "ています。"),
    ("そして、それぞれの境界において、\n相互の再配送が実施されている、というものです。",
     "そして、それらは境界において接続されています。"),
    ("そして、それぞれの境界において、相互の再配送が実施されている、というものです。",
     "そして、それらは境界において接続されています。"),
    ("ポリシー・ベース・ルーティングという手段によって、", ""),
    ("ポリシー ベース ルーティングという手段によって、", ""),
]


def _split_sections(md):
    """'## 見出し' 単位に (見出し, 本文行list) へ分解。先頭は ('', 前文)。"""
    out, cur, body = [], "", []
    for ln in md.splitlines():
        if ln.startswith("## "):
            out.append((cur, body)); cur, body = ln[3:].strip(), []
        else:
            body.append(ln)
    out.append((cur, body))
    return out


def _prose_and_rest(lines):
    """節の本文を (先頭の散文, 残り=図/表/出力) に割る。"""
    i = 0
    while i < len(lines) and not (lines[i].startswith("```")
                                  or lines[i].startswith("|")):
        i += 1
    return lines[:i], lines[i:]


def _fenced_blocks(lines):
    """``` で囲まれた塊のリストと、それ以外の行を返す。"""
    blocks, other, buf, inside = [], [], [], False
    for ln in lines:
        if ln.startswith("```"):
            buf.append(ln)
            if inside:
                blocks.append(buf); buf = []
            inside = not inside
            continue
        (buf if inside else other).append(ln)
    if buf:
        blocks.append(buf)
    # ★空行を全部捨てると、表 → 見出し行 → 表 のような塊が 1 つに潰れ、
    #   **2 つ目以降の表が表として描画されない**(aaa に全断の観測表を足して発覚)。
    #   前後の空行だけ落とし、**内部の空行は残す**(全 shape に効く)。
    while other and not other[0].strip():
        other.pop(0)
    while other and not other[-1].strip():
        other.pop()
    return blocks, other


def obfuscate_md(md, rnd, essay=False, keep_ask=False):
    """①タイトル無機質化 ②設問の抽象化 ④症状の抽象化 ⑦直訳の前置き=常時 /
    ③シナリオへの散文統合(⑤機構名の除去を含む) ⑥出力順のランダム化=50%。

    ★keep_ask: 設問文と症状本文を**そのまま残す**。BL-088 の不変条件は
    「情報は1ビットも減らさない」であり、evidence 形(aaa)のように
    **設問文と症状文そのものが情報の担い手**(対立する2仮説の提示)である形では、
    設問の統一・症状の抽象化を掛けると解答不能になるため。
    ★dbgconf 形も同様。選択肢が構成そのものなので、設問を汎用文
    「次のうち、正しいものは、どれですか」に均すと「要件に適合する構成はどれか」
    という**別の設問に化ける**(2026-08-08 実装時に検出)。
    """
    md = re.sub(r"^(# 問題 \S+)\s*:.*$", r"\1", md, count=1, flags=re.M)
    if essay:
        return md
    prose_mode = rnd.random() < 0.5
    shuffle_out = rnd.random() < 0.5
    secs = _split_sections(md)
    get = {k: v for k, v in secs}
    head = secs[0][1]

    topo_prose, topo_rest = _prose_and_rest(get.get("トポロジ", []))
    intro = "".join(x.strip() for x in topo_prose if x.strip())
    for a, b in INTRO_DENAME:
        intro = intro.replace(a.replace("\\n", "\n"), b)
    reqs = [re.sub(r"^\d+\.\s*", "", x.strip())
            for x in get.get("要件", []) if x.strip()]
    st_prose, st_rest = _prose_and_rest(get.get("現在の状態", []))
    state_blocks, state_other = _fenced_blocks(st_rest)
    cfg_blocks, _ = _fenced_blocks(get.get("設定抜粋", []))
    vague = rnd.choice(VAGUE_SYMPTOM)
    ask = GENERIC_ASK
    if keep_ask:
        ask = "\n".join(x for x in get.get("設問", []) if x.strip()).strip()
        vague = "".join(x.strip() for x in st_prose if x.strip())

    if prose_mode:
        scenario = (rnd.choice(LEAD_IN) + intro + vague
                    + ("" if keep_ask else rnd.choice(DIRECTIVE))
                    + "".join(reqs))
        out = state_blocks + cfg_blocks
        if shuffle_out:
            rnd.shuffle(out)
        parts = ["\n".join(head).rstrip(), "", "## シナリオ", "", scenario, ""]
        parts += ["\n".join(topo_rest).strip(), "", "## 出力", ""]
        # ★フェンスに入っていない状態ブロック(表など)も必ず載せる。
        #   ここを落とすと「情報は1ビットも減らさない」(BL-088 の不変条件)に反し、
        #   症状そのものが消えて解答不能になる(aaa の cause 形で発覚・2026-08-08)。
        if state_other:
            parts += state_other + [""]
        parts += ["\n".join(b) for b in out]
        parts += ["", "## 設問", "", ask, "", "## 選択肢",
                  "\n".join(get.get("選択肢", [])).strip(), ""]
        return "\n".join(parts)

    # 見出しは残すが、道標だけ抜く形
    if shuffle_out:
        rnd.shuffle(state_blocks)
    rebuilt = ["\n".join(head).rstrip(), "", "## トポロジ", "",
               rnd.choice(LEAD_IN) + intro, "",
               "\n".join(topo_rest).strip(), "",
               "## 要件", ""] + [f"{i}. {x}" for i, x in enumerate(reqs, 1)] + [
               "", "## 現在の状態", "",
               vague + ("" if keep_ask else rnd.choice(DIRECTIVE)), ""]
    rebuilt += state_other + [""] if state_other else []
    rebuilt += ["\n".join(b) for b in state_blocks]
    if cfg_blocks:                      # ★空の見出しを残さない
        rebuilt += ["", "## 設定抜粋", ""] + ["\n".join(b) for b in cfg_blocks]
    rebuilt += ["", "## 設問", "", ask, "", "## 選択肢",
                "\n".join(get.get("選択肢", [])).strip(), ""]
    return "\n".join(rebuilt)


PBR_INTRO = (
    "コアのルータにおいて、ポリシー・ベース・ルーティングという手段によって、"
    "それぞれのサイトの LAN から、本社のデータ・センターのサービスのネットワークへの"
    "転送が、制御されています。コアは、サービスのネットワークへのルーティングの情報を"
    "保持しておらず、そして、ポリシーに一致したトラフィックのみが、ネクスト・ホップへ"
    "転送されます。")

URPF_INTRO = (
    "あなたの会社のエッジのルータは、2つのアップリンクによって、"
    "2つのサービス・プロバイダへ接続されている、というものです。"
    "顧客のネットワーク {a}.0/24 および {b}.0/24 は、"
    "それぞれのプロバイダを経由して、広告されています。")


def finalize_reqs(core, rnd):
    """要件リストの仕上げ: 不親切化 → 連番付与。"""
    return [f"{i}. {terse_jp(t, rnd)}" for i, t in enumerate(core, 1)]


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
    return finalize_reqs(reqs, rnd)


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
                form="fix", reqs=None, style="prose"):
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
    elif style == "cli":
        q = ("示されているところのすべての要件が満たされることを確実にするために、"
             "適用されなければならない構成は、どれですか。(1つを選択してください)")
    else:
        q = ("この問題を解決し、そして、示されているところのすべての要件が"
             "満たされることを確実にするために、必要とされる手順は、どれですか。"
             "(1つを選択してください)")
    opts = render_options(choices, style)
    T = cisco_terms(random.Random(zlib.crc32(stamp.encode()) & 0xFFFF))
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

{terse_jp(intro)}

{messy_mermaid(mermaid(d, sites, blind))}

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
    correct = [l for l, c in zip(letters, choices) if c[1]][0]
    tgt = d["doms"][f["into"]]
    parent = f"router {'ospf' if tgt['type'] == 'ospf' else 'eigrp'} {tgt['id']}"
    kind_note = {
        "missing": "一方向の redistribute が丸ごと欠落(片側ドメインが対岸を全喪失)",
        "no_seed": "OSPF→EIGRP 注入の metric 欠落(∞メトリックで不広告。config は存在)",
        "filter": "redistribute に route-map が付き特定 Loopback だけ deny(部分喪失)",
        "wrong_id": "redistribute の参照プロセス/AS が誤り(config は一見完備・無言で経路ゼロ)",
    }[kind]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                        for l, c in zip(letters, choices))
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
            + "\n\nリンク一覧:\n```\n"
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
    # RA の再注入(出自が一周する箇所)。tag 解でここに match tag deny を置く
    ra_p = ret_p
    ra_line = (f"redistribute eigrp {eas}" if inj_e else f"redistribute ospf {pid}")
    dist_line = f"distance bgp 20 {return_ad - 5} {return_ad - 5}"
    dist_choice = (f"{rc} の router bgp {bas} 配下に「{dist_line}」を設定し、"
                   "clear ip route * を実行する")
    cli = {
        "dist": [f"router bgp {bas}", f" {dist_line}", "end", "clear ip route *"],
        "filt": [f"ip prefix-list PL-BLOCK seq 5 deny {p}.0/24",
                 "ip prefix-list PL-BLOCK seq 10 permit 0.0.0.0/0 le 32",
                 ret_p, " distribute-list prefix PL-BLOCK in"],
        "wrong_tgt": ([f"router ospf {pid}", f" distance ospf external {return_ad + 95}"]
                      if inj_e else
                      [f"router eigrp {eas}", f" distance eigrp 90 {return_ad + 35}"]),
        "no_ri": [f"router bgp {bas}", " no bgp redistribute-internal"],
        "clear": ["clear ip bgp *", "clear ip route *"],
        "rm_inj": [f"ip prefix-list PL-X seq 5 deny {p}.0/24",
                   "ip prefix-list PL-X seq 10 permit 0.0.0.0/0 le 32",
                   "route-map RM-INJ permit 10",
                   " match ip address prefix-list PL-X",
                   inj_p, f" redistribute bgp {bas} route-map RM-INJ"],
        "rm_ra": ["! " + ra + " 側で両方向の redistribute に deny route-map を適用",
                  "route-map RM-BLK deny 10",
                  f" match ip address prefix-list PL-BLK",
                  "route-map RM-BLK permit 20"],
        "tag": [f"! {rc}", "route-map RM-ORIGIN permit 10",
                f" set tag {bas}",
                inj_p, f" redistribute bgp {bas} route-map RM-ORIGIN",
                f"! {ra}", "route-map RM-NOBACK deny 10",
                f" match tag {bas}",
                "route-map RM-NOBACK permit 20",
                ra_p, f" {ra_line} route-map RM-NOBACK"],
    }
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
    tag_choice = (f"{rc} の {inj_p} 配下の redistribute に「set tag {bas}」を付与する "
                  f"route-map を適用し、{ra} の {ra_p} 配下の再配送に「match tag {bas}」を "
                  "deny する route-map を適用する")
    tag_why = ("出自のタグは付くが、一周した経路を落とす側の deny が無いため、"
               "戻り外部経路はそのまま学習され、ループは解消しない。")
    if d["method"] == "distance":
        c = [(dist_choice, True, "", cli["dist"]),
             (wrong_tgt, False, wrong_tgt_why, cli["wrong_tgt"]),
             (no_ri[0], False, no_ri[1], cli["no_ri"]),
             (clear_only[0], False, clear_only[1], cli["clear"])]
        if exam:
            c += [(rm_inj, False, rm_inj_why, cli["rm_inj"]),
                  (rm_ra, False, rm_ra_why, cli["rm_ra"])]
    elif d["method"] == "tag":   # 監査で distance 禁止 かつ プレフィクス個別列挙も禁止
        c = [(tag_choice, True, "", cli["tag"]),
             (filt_choice, False,
              "到達性・ループとも解消する(症状は直る)が、被害プレフィックスを個別に"
              "列挙する形であり、要件「遮断は経路の出自に基づくこと"
              "(プレフィックスの列挙による指定は不可)」を満たさない。", cli["filt"]),
             (dist_choice, False,
              "到達性・ループとも解消する(症状は直る)が、監査要件"
              "「管理距離(distance)の変更禁止」に違反する。", cli["dist"]),
             (rm_ra, False, rm_ra_why, cli["rm_ra"])]
        if exam:
            c += [(f"{rc} の {inj_p} 配下の redistribute に「set tag {bas}」を付与する "
                   "route-map を適用する", False, tag_why,
                   [f"route-map RM-ORIGIN permit 10", f" set tag {bas}",
                    inj_p, f" redistribute bgp {bas} route-map RM-ORIGIN"]),
                  (no_ri[0], False, no_ri[1], cli["no_ri"])]
    else:  # filter(監査で distance 禁止)
        c = [(filt_choice, True, "", cli["filt"]),
             (dist_choice, False,
              "到達性・ループとも解消する(症状は直る)が、監査要件"
              "「管理距離(distance)の変更禁止」に違反する。", cli["dist"]),
             (rm_inj, False, rm_inj_why, cli["rm_inj"]),
             (rm_ra, False, rm_ra_why, cli["rm_ra"])]
        if exam:
            c += [(no_ri[0], False, no_ri[1], cli["no_ri"]),
                  (clear_only[0], False, clear_only[1], cli["clear"])]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_cause_choices_ring(d, rnd, exam=False):
    """ring の原因特定形(BL-086②③)。正因1 + 偽原因。
    ★偽原因には「そもそもループではない」機構(等コスト分散・遠回り)と、
    「結果を原因と取り違える」もの(RIB-failure)を必ず含める。
    ring の fix 形は traceroute の周回を見た時点で「ループだ」と即断できてしまうため、
    cause 形ではその即断を潰す(= traceroute だけでは肢を絞れない)。"""
    m, p = d["m"], d["p_net"]
    rc, ra, rb, re_n = m["RC"], m["RA"], m["RB"], m["RE"]
    inj_e = d["ring"] == "inject_eigrp"
    return_ad = 110 if inj_e else 170
    ext_word = "OSPF の外部経路" if inj_e else "EIGRP の外部経路"
    inj_word = "EIGRP" if inj_e else "OSPF"
    # ★正解肢だけ長く具体的にしない(数値・因果を書くと形で割れる)。
    #   他肢と同じ粒度の「観測された状態の言明」に揃える。
    correct = (f"{rc} が、一周して戻ってきた外部経路を iBGP の経路より優先して"
               "採用している", True, "")
    pool = [
        (f"{ra} と {rb} の間で等コストの複数経路が成立し、パケットが分散されている",
         False,
         "等コスト分散であれば宛先には到達する。示された traceroute は同一のホップ列を"
         "反復しており、分散ではなく周回である。"),
        (f"{rc} の BGP テーブルにおいて当該経路が RIB-failure となり、"
         "ベストパスが選出できていない",
         False,
         "`r>` の `>` はベストパス選出済みを示し、RIB-failure は選出後に RIB へ"
         "載せられなかったという表示。これは原因ではなく、原因(他プロトコルが RIB を"
         "占有していること)の結果である。"),
        (f"{re_n} からの広告が {rc} に到達していない",
         False,
         f"{rc} の BGP テーブルに当該プレフィックスが存在する(広告は届いている)。"),
        (f"BGP から {inj_word} への再配送に seed metric が指定されておらず、"
         "経路が広告されていない",
         False,
         "IGP 側の各ルータは当該プレフィックスを学習している(経路表に存在する)。"
         "広告そのものは成立している。"),
        (f"{ra} の相互再配送において経路が収束せず、振動している",
         False,
         "経路表の経過時間は単調に進行しており、再学習(タイマーのリセット)の痕跡がない。"
         "定常状態のループである。"),
        (f"当該プレフィックスの next-hop が最適でなく、遠回りの経路が選択されている",
         False,
         "遠回りであっても宛先には到達する。到達していない以上、"
         "経路の優劣ではなく転送の周回が生じている。"),
        (f"{rc} において当該プレフィックスの外部経路タイプが E2 であり、"
         "内部コストが加算されていない",
         False,
         "外部経路タイプは同一プロトコル内の優劣に影響するに過ぎず、"
         "iBGP と IGP 外部経路の比較は管理距離で決まる。"),
    ]
    rnd.shuffle(pool)
    c = [correct] + pool[:(5 if exam else 3)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def ring_requirements(d, rnd, form="fix"):
    """exam 用(ring): 言い換え抽選+ダミー+並びシャッフル。監査要件(distance禁止/
    出自ベース遮断)は fix 形での正解一意性の装置なので、その時だけ載せる。
    ★cause 形では載せない: 修正手段を問わない上、「遮断は出自に基づくこと」は
    原因(出自が一周している)を示唆してしまい、ヒントになる(BL-086)。"""
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
    if form == "fix" and d["method"] in ("filter", "tag"):
        core.append(rnd.choice([
            "管理距離(administrative distance)の変更は、監査のポリシーによって、"
            "禁止されているところのものです。",
            "distance コマンドによる管理距離の操作は、監査のポリシー上、"
            "使用されることができません。"]))
    if form == "fix" and d["method"] == "tag":
        core.append(rnd.choice([
            "経路の遮断は、当該の経路の出自に基づいて、実施されなければなりません"
            "(個々のプレフィックスを列挙する形式の指定は、将来における網の追加に際して"
            "境界の再構成を要するという理由により、認められていません)。",
            "遮断の条件は、プレフィックスの列挙によるものであってはならず、"
            "その経路がどこから来たものであるか、という属性によって、"
            "表現されなければなりません。"]))
    core += rnd.sample([x for x in REQ_DECOYS if "静的経路" not in x],
                       rnd.choice([1, 2]))
    rnd.shuffle(core)
    return finalize_reqs(core, rnd)


def question_md_ring(d, plan, choices, collected, stamp, sites=None, blind=False,
                     reqs=None, style="prose", form="fix"):
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
        if form == "fix" and d["method"] in ("filter", "tag"):
            reqs.append("4. 管理距離(administrative distance)の変更は監査ポリシーにより"
                        "禁止されていること。")
        if form == "fix" and d["method"] == "tag":
            reqs.append("5. 遮断は経路の出自に基づくこと"
                        "(プレフィックスの列挙による指定は不可)。")
    opts = render_options(choices, style)
    ask = ("この問題を解決し、上記の要件をすべて満たすために必要な手順はどれですか。"
           "(1つ選択)" if form == "fix" else
           "示されているところの事象を説明しているものとして、最も適切なものは、"
           "どれですか。(1つを選択してください)")
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

{terse_jp(intro)}

{messy_mermaid(mermaid_ring(d, sites, blind))}

{topo_tables_ring(d, sites, blind)}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{terse_jp(symptom)}

{chr(10).join(state)}

## 設定抜粋

{chr(10).join(cfg)}

## 設問

{ask}

## 選択肢

{opts}
"""


def answer_md_ring(d, plan, choices, stamp, master_seed, subseed, prob_id,
                   herr=None, form="fix"):
    m, p = d["m"], d["p_net"]
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, c in zip(letters, choices) if c[1]][0]
    inj_e = d["ring"] == "inject_eigrp"
    return_ad = 110 if inj_e else 170
    herr_note = ""
    if herr:
        herr_note = ("\n- 赤ニシン: " + "・".join(sorted(herr))
                     + " に未適用の route-map/prefix-list/ACL と無害な適用行を混入(実害なし)")
    victim = "O E2 (AD 110)" if inj_e else "D EX (AD 170)"
    loop_word = (f"{m['RC']} → {m['RB']} → {m['RA']} → {m['RC']}" if inj_e
                 else f"{m['RC']} → {m['RA']} → {m['RB']} → {m['RC']}")
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                        for l, c in zip(letters, choices))
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態(故障ではなく設計の帰結)

- 種別: `ring/{d['method']}` — 再配送リングの定常ループ(ring={d['ring']})
- 機構: `{p}.0/24` は {m['RE']} が BGP 起点広告 → {m['RC']} が iBGP(AD 200) で学習。
  {m['RC']} が BGP を {'EIGRP' if inj_e else 'OSPF'} へ再配送し、{m['RA']} の相互再配送で
  出自が一周。戻ってきた {victim} が iBGP(200) に勝って {m['RC']} が採用
  → 定常転送ループ {loop_word}。
- 出題形式: {form}({'是正手順を選ばせる' if form == 'fix' else '機構(原因)を選ばせる。錯乱肢に「そもそもループでない」機構=等コスト分散・遠回りと、結果を原因と取り違える RIB-failure を混入'})
- 正解法: {d['method']}(distance=iBGP の AD を戻り {return_ad} 未満へ /
  filter=戻り経路を学習段で遮断(distribute-list) /
  tag=注入時に出自タグを付け、一周する箇所で match tag deny。監査要件で出し分け)
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
- tag 解の場合、{m['RC']} で `Known via "bgp"` に変わり、かつ {m['RA']} は当該網を
  引き続き保持していること(戻りの再注入だけが止まる)を見る。
  タグの付与だけでは何も変わらない(deny 側が本体)。

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
# shape=mploop — 多点相互再配送の「同AD・メトリック差」誤選択ループ(BL-086 ④a)
#   ring(AD 反転)とは診断の型が別物: 候補が両方 D EX(AD 170)で、
#   管理距離を見ても答えが出ない。決め手は seed metric の付き方。
#   盤面は BL-058 の実機検証済みトポロジ(gen_redist_mp_ts)をそのまま借りる。
# --------------------------------------------------------------------------
MPLOOP_KINDS = list(gmp.MODES)      # acl / prefix / routemap / distance


def mploop_names(rnd):
    """RA..RF を RT01..RT06 へシャッフル割当(役割が名前から割れないように)。"""
    tags = [f"RT{i:02d}" for i in range(1, len(gmp.NODES) + 1)]
    rnd.shuffle(tags)
    return dict(zip(gmp.NODES, tags))


MPLOOP_LINKS = [("RA", 0, "RB", 0), ("RA", 1, "RC", 0), ("RB", 1, "RD", 0),
                ("RC", 1, "RD", 1), ("RD", 2, "RE", 0), ("RE", 1, "RF", 0)]
MPLOOP_SEG = {("RA", "RB"): "seg_o1", ("RA", "RC"): "seg_o2",
              ("RB", "RD"): "seg_e11", ("RC", "RD"): "seg_e12",
              ("RD", "RE"): "seg_e31", ("RE", "RF"): "seg_e41"}


def write_pack_mploop(repo, prob_id, p, names, subseed):
    pdir = f"{repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/params", exist_ok=True)
    with open(f"{pdir}/params/base.yml", "w", encoding="utf-8") as fh:
        fh.write(f"# 自動生成 (gen_paper_mcq.py shape=mploop) seed={subseed}\n")
        yaml.safe_dump(p, fh, sort_keys=False, allow_unicode=True)
    problem = {"id": prob_id,
               "title": f"机上問題スナップショット(使い捨て) seed={subseed}",
               "exam": "ENARSI", "topics": ["generated", "paper-mcq"],
               "difficulty": 5, "topology": "generated", "access": "ssh",
               "target_nodes": sorted(names.values()), "points": 100,
               "lab": {"links": [{"a": names[a], "a_if": ia, "b": names[b], "b_if": ib}
                                 for a, ia, b, ib in MPLOOP_LINKS]}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fh:
        fh.write("# 自動生成 (gen_paper_mcq.py) 机上問題用・撤収後に削除される\n")
        yaml.safe_dump(problem, fh, sort_keys=False, allow_unicode=True)
    for role in gmp.NODES:
        # 役割を書いた先頭コメント(! GEN-REDISTMP 初期 RB : ...)は落とす
        body = [ln for ln in gmp.render_node(role)
                if not ln.startswith("! GEN-REDISTMP")]
        with open(f"{pdir}/initial/{names[role]}.cfg.j2", "w", encoding="utf-8") as fh:
            fh.write("\n".join(body) + "\n")
    return pdir


def _mploop_lo(p, role):
    return (f"{p['p_net']}.6/24 (`{p['p_net']}.0/24` を広告)" if role == "RF"
            else f"{p[role.lower() + '_lo']}/32")


def mermaid_mploop(p, names, sites=None, blind=True):
    lines = ["```mermaid", f"graph {p.get('_mmdir', 'LR')}"]
    for role in sorted(gmp.NODES, key=lambda r: names[r]):
        site = f"{sites[role]}<br/>" if sites else ""
        lines.append((f'  {names[role]}["{site}{names[role]}<br/>'
                      f'Lo0: {_mploop_lo(p, role)}"]').replace("`", ""))
    for a, ia, b, ib in MPLOOP_LINKS:
        seg = p[MPLOOP_SEG[(a, b)]]
        lines.append(f'  {names[a]} ---|"{seg}.0/24<br/>'
                     f'{names[a]}:E0/{ia}=.{gmp.HOST[a]} '
                     f'{names[b]}:E0/{ib}=.{gmp.HOST[b]}"| {names[b]}')
    lines.append("```")
    return "\n".join(lines)


def topo_tables_mploop(p, names, sites=None):
    head = ("| 拠点 | ルータ | 拠点網 / 広告網 |\n"
            "|------|--------|------------------|\n") if sites else \
           ("| ルータ | 拠点網 / 広告網 |\n|--------|------------------|\n")
    rows = []
    for role in gmp.NODES:
        pre = f"| {sites[role]} " if sites else ""
        rows.append(f"{pre}| {names[role]} | {_mploop_lo(p, role)} |")
    edges = [f"  {names[a]}:E0/{ia}(.{gmp.HOST[a]}) ── "
             f"{names[b]}:E0/{ib}(.{gmp.HOST[b]})   {p[MPLOOP_SEG[(a, b)]]}.0/24"
             for a, ia, b, ib in MPLOOP_LINKS]
    return (head + "\n".join(sorted(rows))
            + "\n\nリンク一覧:\n```\n" + "\n".join(edges) + "\n```")


def evidence_plan_mploop(p, names, rnd):
    """誤選択の現場 RD の経路表＋EIGRP トポロジ(=メトリック比較の一次証拠)、
    正規経路側 RE の経路表(対比)、OSPF 側 RA の経路表、周回の生映像、全 config。"""
    victim = f"{p['p_net']}.0"
    checks = [{"node": names["RD"], "command": "show ip route"},
              {"node": names["RD"],
               "command": f"show ip eigrp topology {victim} 255.255.255.0",
               "optional": True},
              {"node": names["RE"], "command": "show ip route"},
              {"node": names["RA"], "command": "show ip route"},
              {"node": names["RA"],
               "command": f"traceroute {p['p_net']}.6 probe 1 timeout 1 ttl 1 8",
               "optional": True}]
    for role in gmp.NODES:
        checks.append({"node": names[role],
                       "command": "show running-config | section router"})
    return {"checks": checks}


def _mploop_fix_text(p, names, mode):
    """mode ごとの是正内容(RB/RC 両方に対で入れるのが正解)。gmp.fix_filters と整合。"""
    pid, asn, v = p["pid"], p["asn"], p["p_net"]
    b, c = names["RB"], names["RC"]
    if mode == "acl":
        body = (f"`access-list {p['acl_no']} deny {v}.0 0.0.0.255` / "
                f"`permit any` を作成し、router eigrp {asn} 配下に "
                f"`distribute-list {p['acl_no']} out ospf {pid}` を適用する")
        cli = [f"access-list {p['acl_no']} deny {v}.0 0.0.0.255",
               f"access-list {p['acl_no']} permit any",
               f"router eigrp {asn}",
               f" distribute-list {p['acl_no']} out ospf {pid}"]
    elif mode == "prefix":
        body = (f"`{gmp.PFX_NAME}` に `{v}.0/24` を deny・他を permit で作成し、"
                f"router eigrp {asn} 配下に "
                f"`distribute-list prefix {gmp.PFX_NAME} out ospf {pid}` を適用する")
        cli = [f"ip prefix-list {gmp.PFX_NAME} seq 5 deny {v}.0/24",
               f"ip prefix-list {gmp.PFX_NAME} seq 10 permit 0.0.0.0/0 le 32",
               f"router eigrp {asn}",
               f" distribute-list prefix {gmp.PFX_NAME} out ospf {pid}"]
    elif mode == "routemap":
        body = (f"EIGRP→OSPF 再配送で `set tag {p['tag']}` を付与し、"
                f"OSPF→EIGRP 再配送で `match tag {p['tag']}` を deny する")
        cli = ["route-map SET-TAG permit 10", f" set tag {p['tag']}",
               "route-map DENY-TAG deny 10", f" match tag {p['tag']}",
               "route-map DENY-TAG permit 20",
               f"router ospf {pid}",
               f" redistribute eigrp {asn} subnets route-map SET-TAG",
               f"router eigrp {asn}",
               f" redistribute ospf {pid} metric {gmp.SEED_METRIC} route-map DENY-TAG"]
    else:
        body = f"router ospf {pid} 配下に `distance ospf external 180` を設定する"
        cli = [f"router ospf {pid}", " distance ospf external 180"]
    return (f"{b} と {c} の両方で、{body}", ["! " + b + " と " + c + " の両方に投入"] + cli)


def build_choices_mploop(p, names, mode, rnd, exam=False):
    """是正手順形。★この shape 固有の錯乱肢= 「片側の境界にだけ入れる」(鏡像ループ残存)と
    「RD で distance を触る」(候補が両方 D EX 170 なので効かない)。"""
    pid, asn, v = p["pid"], p["asn"], p["p_net"]
    b, c, dd, ff = names["RB"], names["RC"], names["RD"], names["RF"]
    good_txt, good_cli = _mploop_fix_text(p, names, mode)
    others = [m for m in gmp.MODES if m != mode]
    alt = rnd.choice(others)
    alt_txt, alt_cli = _mploop_fix_text(p, names, alt)
    alt_word = {"acl": "番号付き標準 ACL の distribute-list",
                "prefix": "prefix-list の distribute-list",
                "routemap": "経路タグ(route-map)",
                "distance": "管理距離(distance)の変更"}[alt]
    one_side_txt = good_txt.replace(f"{b} と {c} の両方で、", f"{b} でのみ、")
    c_list = [
        (good_txt, True, "", good_cli),
        (one_side_txt, False,
         "片方の境界にだけ入れると、もう一方の境界を起点とする鏡像の再注入が残り、"
         "ループは解消しない(2 つの境界が役割を分担して周回を維持している)。",
         [f"! {b} にのみ投入"] + good_cli[1:]),
        (alt_txt, False,
         f"到達性・ループとも解消する(症状は直る)が、{alt_word} は変更凍結の対象であり、"
         "指定されている実装手段に反する。", alt_cli),
        (f"{dd} の router eigrp {asn} 配下に `distance eigrp 90 200` を設定する",
         False,
         f"{dd} が比較している 2 つの候補はいずれも EIGRP 外部(AD 170)であり、"
         "同一プロトコル・同一 AD の間では管理距離は優劣を決めない。何も変わらない。",
         [f"router eigrp {asn}", " distance eigrp 90 200"]),
    ]
    if exam:
        c_list += [
            (f"{ff} の router eigrp {asn} 配下の `redistribute rip` の seed metric を"
             "より小さい値へ変更する",
             False,
             "正規経路側のメトリックを下げれば当面の選択は変わりうるが、"
             "再注入の経路そのものは残るため構造的な解決にならず、"
             "トポロジ変化で容易に再発する。",
             [f"router eigrp {asn}", f" redistribute rip metric 100 1 255 1 1500"]),
            (f"{dd} で `clear ip route *` を実行する", False,
             "設定に起因する定常状態であり、再計算しても同じ選択に戻る。",
             ["clear ip route *"]),
        ]
    order = list(range(len(c_list)))
    rnd.shuffle(order)
    return [c_list[i] for i in order]


def build_cause_choices_mploop(p, names, rnd, exam=False):
    """原因特定形。★AD ではなくメトリックが争点、という一点を問う。"""
    dd, b, c, e, f6 = (names["RD"], names["RB"], names["RC"],
                       names["RE"], names["RF"])
    # ★正解肢の長さを誤答肢に揃える(形で割れないように)
    correct = (f"{dd} が、境界から再注入された経路を正規の経路より良いものとして"
               "選択している", True, "")
    pool = [
        (f"{dd} において、再注入された経路の管理距離が正規の経路より小さい", False,
         "いずれも EIGRP 外部(AD 170)であり、管理距離は同一。優劣はメトリックで決まっている。"),
        (f"{f6} からの再配送に seed metric が指定されておらず、経路が広告されていない",
         False,
         "当該プレフィックスは各ルータの経路表に存在する。広告そのものは成立している。"),
        (f"{b} と {c} の間で OSPF の隣接が確立しておらず、経路情報が同期していない",
         False,
         "両者は同一エリアの経路を保持しており、隣接は確立している。"),
        (f"{e} が当該プレフィックスを広告しておらず、正規の経路が存在しない", False,
         f"{e} の経路表には正規の経路が存在する(そちらが選ばれていないだけ)。"),
        (f"{dd} と境界の間で等コストの複数経路が成立し、パケットが分散されている", False,
         "等コスト分散であれば宛先には到達する。示された経路は同一区間を反復している。"),
        (f"当該プレフィックスの経路が収束せず、境界の間で振動している", False,
         "経路表の経過時間は単調に進行しており、再学習の痕跡がない。定常状態である。"),
        (f"{dd} において当該プレフィックスの外部経路タイプが誤っている", False,
         "外部経路の種別は EIGRP では優劣に関与せず、比較は複合メトリックで行われる。"),
    ]
    rnd.shuffle(pool)
    cs = [correct] + pool[:(5 if exam else 3)]
    order = list(range(len(cs)))
    rnd.shuffle(order)
    return [cs[i] for i in order]


MPLOOP_POLICY = {
    "acl": "是正は、番号付き標準アクセス・リストと、再配送点における distribute-list に"
           "よって、実装されなければなりません(prefix-list / route-map の新設、および"
           "管理距離の変更は、変更の凍結により、使用することができません)。",
    "prefix": "是正は、prefix-list と、再配送点における distribute-list によって、"
              "実装されなければなりません(番号による ACL、route-map の新設、および"
              "管理距離の変更は、使用することができません)。",
    "routemap": "是正は、経路の出自に対するマーキング(タグ)によって、実装されなければ"
                "なりません(distribute-list / prefix-list、および管理距離の変更は、"
                "使用することができません)。",
    "distance": "フィルタの新設(ACL / prefix-list / route-map / distribute-list)は、"
                "変更の凍結により、使用することができません。是正は、管理距離の調整"
                "のみによって、実装されなければなりません。",
}


def mploop_requirements(p, names, mode, rnd, form="fix"):
    v, ff = p["p_net"], names["RF"]
    core = [
        rnd.choice([
            f"すべてのサイトから、`{v}.0/24` を含むところのすべての宛先へ、"
            "到達することができること。",
            f"顧客のネットワーク `{v}.0/24` への到達可能性が、"
            "すべてのサイトにおいて、確保されていること。"]),
        rnd.choice([
            f"`{v}.0/24` 宛のパケットが、広告元である {ff} の方向へ転送され、"
            "そして、転送のループが存在していないこと。",
            f"`{v}.0/24` 宛のトラフィックが {ff} へ配送され、"
            "経路の周回が、発生していないこと。"]),
        "スタティック・ルートおよび既定のルートによる迂回は、実施されてはなりません。",
        "既存の相互再配送の設計(それぞれの境界の redistribute)が、削除または停止"
        "されてはなりません。",
    ]
    if form == "fix":
        core.append(MPLOOP_POLICY[mode])
    core += rnd.sample([x for x in REQ_DECOYS if "静的経路" not in x],
                       rnd.choice([1, 2]))
    rnd.shuffle(core)
    return finalize_reqs(core, rnd)


def question_md_mploop(p, names, plan, choices, collected, stamp, sites=None,
                       reqs=None, style="prose", form="fix"):
    state, cfg = [], []
    for chk in plan["checks"]:
        body = collected.get((chk["node"], chk["command"]), "(未収集)")
        if chk.get("optional") and _bad(body):
            continue
        if chk["command"].startswith("show ip route"):
            body = _trim_route_table(body)
        block = f"```\n{chk['node']}# {chk['command']}\n{body.strip()}\n```"
        (cfg if chk["command"].startswith("show running-config")
         else state).append(block)
    opts = render_options(choices, style)
    ask = ("この問題を解決し、そして、示されているところのすべての要件が満たされることを"
           "確実にするために、適用されなければならない構成は、どれですか。"
           "(1つを選択してください)" if form == "fix" else
           "示されているところの事象を説明しているものとして、最も適切なものは、"
           "どれですか。(1つを選択してください)")
    hq = sites["RF"] if sites else "本社"
    intro = (f"あなたの会社のネットワークは、OSPF のドメインと EIGRP のドメインとが、"
             "2 つの境界のルータによって接続され、そして、それぞれの境界において、"
             "相互の再配送が実施されている、というものです。\n"
             f"顧客のネットワーク `{p['p_net']}.0/24` は、{hq} のサイトにおいて、"
             "別のルーティング・プロトコルによって学習され、そして、"
             "再配送によって、社内へ持ち込まれています。\n"
             "ルーティングの設計の詳細は、示されているところのコンフィギュレーション"
             "から、読み取られることが、期待されています。")
    symptom = (f"複数のサイトから、`{p['p_net']}.0/24` 宛の通信が、タイムアウトする、"
               "ということが、報告されています。\n"
               "サイトの間(それぞれのループバック宛)の通信は、正常です。\n"
               "これは、意図された動作ではありません。"
               "示されているところの出力を、参照してください。")
    return f"""# 問題 {stamp} : ルーティング到達性の分析

{FIXED_NOTE}

## トポロジ

{terse_jp(intro)}

{messy_mermaid(mermaid_mploop(p, names, sites))}

{topo_tables_mploop(p, names, sites)}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{terse_jp(symptom)}

{chr(10).join(state)}

## 設定抜粋

{chr(10).join(cfg)}

## 設問

{ask}

## 選択肢

{opts}
"""


def answer_md_mploop(p, names, mode, choices, stamp, master_seed, subseed,
                     prob_id, form="fix"):
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, ch in zip(letters, choices) if ch[1]][0]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if ch[1] else ch[2]}"
                        for l, ch in zip(letters, choices))
    b, c, dd, e, f6 = (names["RB"], names["RC"], names["RD"],
                       names["RE"], names["RF"])
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態(故障ではなく設計の帰結)

- 種別: `mploop/{mode}` — 多点相互再配送の**同AD・メトリック差**による誤選択ループ
  (BL-058 の実機検証済み盤面を紙面化・BL-086 ④a)
- 出題形式: {form}
- 機構: `{p['p_net']}.0/24` は {f6} が別プロトコルで学習し、seed metric
  `{gmp.SEED_METRIC}` を付けて EIGRP へ注入。正規経路は {f6} → {e} → {dd}。
  一方 {b}/{c} は EIGRP→OSPF→EIGRP と再注入し、その際に**境界で seed metric が
  付け直される**ため、{dd} から見て 1 ホップ分だけ良いメトリックの候補になる。
  **どちらも D EX(AD 170)で管理距離は同じ**なので、{dd} は複合メトリックで
  再注入側を選び、周回が成立する。
- 正解法: {mode}(要件のポリシーで出し分け。**{b} と {c} の両方**に入れるのが必須で、
  片側だけでは鏡像の再注入が残る)
- 生成: `gen_paper_mcq.py --shape mploop --seed {master_seed}`
  (sub-seed {subseed} / 展開パック {prob_id}・撤収済)

## 各選択肢の判定

{wrongs}

## 検証コマンドと期待される出力

- {dd}: `show ip route {p['p_net']}.0` の next-hop が {e} 方向へ戻ること。
- {dd}: `show ip eigrp topology {p['p_net']}.0 255.255.255.0` の successor が
  境界側から正規経路側へ入れ替わること。
- 任意のサイトから `traceroute {p['p_net']}.6` が {f6} まで一直線に届くこと。

## ENARSI ブループリント

- 1.0 Layer 3 Technologies — Troubleshoot redistribution / routing loops
- 同 — 経路選択における「管理距離 → メトリック」の順序と、その診断

## 教育核心

ring 形(AD 反転)との違いはここ: **候補が両方とも同じプロトコル・同じ AD** なので、
管理距離をいくら眺めても答えが出ない。決め手は「再配送のたびに seed metric が
付け直される」という性質で、これにより**遠い経路が近く見える**。
2 点相互再配送では、フィルタ/タグは**両方の境界に対で**入れないと、
役割が入れ替わった鏡像のループが残る。
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


# --------------------------------------------------------------------------
# shape=acl — ACL 単独読解 (gen_paper_acl 流用・BL-106)
# ★紙面専用: 挙動は実機確定表(poc/acl/README.md)の写像モデルから決定的に生成。
# --------------------------------------------------------------------------
def pick_draw_aclv6(qseed, kind):
    for kk in range(200):
        s = qseed + kk * 151
        try:
            return s, gp6.draw(random.Random(s), kind=kind)
        except ValueError:
            continue
    raise SystemExit(f"aclv6 kind={kind} が成立する seed が見つかりません({qseed})")


def aclv6_requirements(d, rnd):
    m = d["m"]
    tg = "、".join(f"`{gp6.net6(d, o)}/64`" for o in d["target"])
    core = [f"{m['DUT']} において、{tg} のネットワークからの通信のみが、"
            f"`{d['srv_host']}` の TCP ポート {d['port']} に到達できなければなりません。"]
    if d["fourth_forbidden"]:
        core.append(f"`{gp6.net6(d, d['fourth'])}/64` からの通信は、"
                    "許可されてはなりません。")
    core.append(f"`{gp6.net6(d, d['outsider'])}/64` からの通信は、"
                "許可されてはなりません。")
    core.append({"one_line": "アクセス・リストのエントリは、1行で構成されなければ"
                             "なりません。",
                 "exact_no_deny": "対象としていないネットワークが、一致の対象に"
                                  "含まれてはなりません。また、拒否のエントリを"
                                  "使用してはなりません。",
                 "exact_min": "対象としていないネットワークが、一致の対象に"
                              "含まれてはなりません。また、エントリの行数は、"
                              "最小でなければなりません。",
                 }[d["world"]])
    core += rnd.sample([x for x in REQ_DECOYS if "スタティック" not in x], 1)
    rnd.shuffle(core)
    return finalize_reqs(core, rnd)


def aclv6_evidence(d, rnd, form):
    """★select 形では現在の ACL を出さない(これから書く行を選ぶ形のため)。"""
    m = d["m"]
    if form == "select":
        return [], []
    state, cfg = [], []
    state.append(f"```\n{m['DUT']}# show ipv6 access-list\n"
                 + gp6.show_text(d) + "\n```")
    if form == "cause":
        rows = ["観測 | サーバへの到達", "--- | ---"]
        for text, ok in gp6.read_items(d):
            rows.append(f"{text} | {'到達可' if ok else '到達不可'}")
        state.append("\n".join(rows))
        # ★隣接の状態は近隣探索が落ちる故障(v6_explicit_deny_nd)の**指紋**。
        #   常に出す(壊れている盤面だけ出すと、表の有無が道標になる)。
        state.append(f"```\n{m['DUT']}# show ipv6 neighbors\n"
                     + gp6.neighbor_text(d) + "\n```")
    cfg.append(f"```\n{m['DUT']}# show running-config | section "
               f"ipv6 access-list|traffic-filter\n"
               + (gp6.config_text(d) + "\n" if gp6.config_text(d) else "")
               + f"interface Ethernet0/0\n"
               f" ipv6 traffic-filter {d['acl_name']} in\n```")
    return state, cfg


def question_md_aclv6(d, blocks, choices, stamp, form="cause", reqs=None,
                      style="prose"):
    m = d["m"]
    state_blocks, cfg_blocks = blocks
    if reqs is None:
        reqs = aclv6_requirements(d, random.Random(0))
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
    elif form == "select":
        q = ("示されているところのすべての要件を満たすものは、どれですか。"
             "(1つを選択してください)")
    elif form == "counter":
        q = (f"{d['_counter_probe']['text']} が処理されるとき、"
             "一致のカウンタが増加するのは、どの行ですか。(1つを選択してください)")
    else:
        want = d.get("_read_want", 1)
        subj = ("転送されるもの" if d.get("_read_polarity") == "pass"
                else "破棄されるもの")
        q = (f"示されているところの構成において、{subj}は、どれですか。"
             f"({'2つ' if want == 2 else '1つ'}を選択してください)")
    opts = render_options(choices, style)
    intro = (f"ある企業のネットワークにおいて、{m['DUT']} は、顧客の側の"
             "ネットワークと、サーバの側のネットワークとの間に配置されており、"
             "IPv6 によって運用されています。")
    body_state = "\n".join(state_blocks) if state_blocks else ""
    sec_state = f"## 現在の状態\n\n{body_state}\n" if body_state else ""
    sec_cfg = f"## 設定抜粋\n\n{chr(10).join(cfg_blocks)}\n" if cfg_blocks else ""
    return f"""# 問題 {stamp} : IPv6 のトラフィック・フィルタの分析

{FIXED_NOTE}

## トポロジ

{terse_jp(intro)}

```
   {m['DN']} (顧客の側) --- {m['DUT']} (被験のデバイス) --- {m['UP']} (サーバの側)
```

## 要件

{chr(10).join(reqs)}

{sec_state}{sec_cfg}## 設問

{q}

## 選択肢

{opts}
"""


def answer_md_aclv6(d, choices, stamp, master_seed, subseed, form):
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = ", ".join(l for l, c in zip(letters, choices) if c[1])
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                        for l, c in zip(letters, choices))
    kind_note = {
        "v6_prefix_too_short": "プレフィックス長が短く、対象外まで許可している",
        "v6_prefix_too_long": "プレフィックス長が長く、対象の一部が漏れている",
        "v6_wildcard_habit": "★IPv4 の癖でワイルドカードを書き、その行が受理されずに"
                             "存在していない",
        "v6_undef_ref": "★未定義の参照 → 全許可(IPv6 では空のリストは保持されないので"
                        "「空」と同一の状態)",
        "v6_order_shadow": "先行の広い permit が後続を影にしている",
        "v6_explicit_deny_nd": "★★末尾に明示の `deny ipv6 any any` を書いたため、"
                               "暗黙の `permit icmp any any nd-na` / `nd-ns` が失われ、"
                               "近隣探索ごと落ちて隣接が解決できない"
                               "(`show ipv6 neighbors` が INCMP)",
    }[d["kind"]]
    world_note = {"one_line": "1行で書く", "exact_no_deny": "過剰許可なし＋deny 禁止",
                  "exact_min": "過剰許可なし＋行数最小"}[d["world"]]
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態

- 種別: `aclv6/{d['kind']}` — {kind_note}
- 要件世界: {world_note}
- 出題形: {form}
- 生成: `gen_paper_mcq.py --shape aclv6 --seed {master_seed}` (sub-seed {subseed})

## 各選択肢の判定

{wrongs}

## ★IPv4 との差分(BL-106 P3 実測・poc/acl/README.md §14)

1. **ワイルドカードは使えない**。`permit ipv6 2001:DB8:x::/64 0.0.3.255 any` は
   `% Invalid input detected` で拒否され、**その行は存在しないまま**になる。
   指定は**プレフィックス長**で行う。
2. 適用は `ip access-group` ではなく **`ipv6 traffic-filter`**。
3. **`show` では `sequence` が行末**に出るが、**running-config では行頭**に出る。
4. **`resequence` に相当するコマンドが無い**。
5. **空のリストは保持されない**（作っても `show` にも running-config にも現れない）。
   したがって IPv6 では「未定義」と「空」は**同一の状態**である。
6. ★★**末尾には暗黙で `permit icmp any any nd-na` / `permit icmp any any nd-ns` が
   存在する**。したがって**明示的に `deny ipv6 any any` を記述すると、その暗黙の許可が
   失われ、近隣探索ごと落ちて隣接が解決できなくなる**（`show ipv6 neighbors` が
   **INCMP**・リンク層アドレスが `-` になる）。回復させるには、明示の拒否の**手前に**
   `permit icmp any any nd-ns` および `permit icmp any any nd-na` を記述する。

## ENARSI ブループリント

- 3.2.b IPv6 トラフィック・フィルタ
"""


def pick_draw_acl(qseed, kind):
    for kk in range(200):
        s = qseed + kk * 149
        try:
            return s, gpl.draw(random.Random(s), kind=kind)
        except ValueError:
            continue
    raise SystemExit(f"acl kind={kind} が成立する seed が見つかりません({qseed})")


def acl_topo(d):
    m = d["m"]
    return (f"```\n"
            f"   {m['DN']} (顧客の側)                {m['UP']} (サーバの側)\n"
            f"        |  {d['oct1']}.{d['oct2']}.253.0/24        "
            f"{d['oct1']}.{d['oct2']}.254.0/24  |\n"
            f"        +--------- {m['DUT']} ---------+\n"
            f"                (被験のデバイス)\n```")


def acl_evidence(d, rnd, form):
    """紙面に出すブロック群。select 形では**現在の ACL を出さない**
    (これから書くべき行を選ぶ形なので、既設の誤りは提示物に含めない)。"""
    m = d["m"]
    state, cfg = [], []
    if form == "select":
        return state, cfg
    acl_txt = gpl.show_acl_text(d)
    if acl_txt:
        state.append(f"```\n{m['DUT']}# show ip access-lists\n{acl_txt}\n```")
    else:
        # ★未定義のときは実機も**何も出さない**。説明文を足さないこと
        #   (BL-088 の不変条件= 出力ブロックに実機が出さない文字列を入れない)。
        state.append(f"```\n{m['DUT']}# show ip access-lists\n```")
    ents, is_std, name = gpl.current_entries(d)
    lines = [f"{m['DUT']}# show running-config | section "
             f"access-list|access-group|distribute-list|"
             f"verify unicast|ip nat|access-class|class-map"]
    lines.append(" " + gpl.ROLE_APPLY[d["role"]].format(n=name))
    cfg.append("```\n" + "\n".join(lines) + "\n```")
    # ★症状そのものを観測に出す(BL-103 ③の教訓=「観測に現れない故障」を作らない)。
    #   read / counter 形は症状表が答えそのものになるので出さない。
    if form in ("cause", "patch", "fix"):
        state.append(acl_symptom_block(d))
    return state, cfg


def acl_evidence_blocks(d, rnd):
    """evidence 形= **症状だけ**を出す。構成を出すと仮説が割れてしまう
    (どの出力を取りに行くかを問う形なので、答えになる出力は提示しない)。"""
    return [acl_symptom_block(d)], []


def acl_logread_blocks(d, rnd):
    """logread 形= ACL と syslog を出す。★log の有無が読解の鍵になる。"""
    m = d["m"]
    name, ents, _lg = gpl.logread_board(d)
    acl = [f"Extended IP access list {name}"]
    for e in ents:
        line = "    " + gpl._render_entry(e, False)
        if e["seq"] in _lg:
            line += " log"
        acl.append(line)
    logs = gpl.logread_lines(d)
    state = ["```\n" + f"{m['DUT']}# show logging | include SEC-6\n"
             + "\n".join(logs) + "\n```"]
    cfg = ["```\n" + f"{m['DUT']}# show ip access-lists {name}\n"
           + "\n".join(acl) + "\n```"]
    return state, cfg


def acl_symptom_block(d):
    """症状の観測。★判定と同じ関数(gpl.read_items)から描く= 提示と判定の一本化。"""
    m = d["m"]
    if d["role"] != "routefilter":
        col, tw, fw, _s1, _s2 = gpl.read_labels(d)
        rows = [f"観測 | {col}", "--- | ---"]
        for text, ok in gpl.read_items(d):
            rows.append(f"{text} | {tw if ok else fw}")
        return "\n".join(rows)
    out = [f"```\n{m['DUT']}# show ip route eigrp | begin Gateway",
           "Gateway of last resort is not set", ""]
    shown = [(d["nb_up"], o, 24) for o in d["target"]] + \
            [(d["nb_dn"], d["target"][0], 28), (d["nb_up"], d["outsider"], 24)]
    kept = [(adv, o, pl) for adv, o, pl in shown if gpl.route_kept(d, adv, o, pl)]
    if kept:
        o2 = f"{d['oct1']}.{d['oct2']}.0.0"
        out.append(f"      {o2}/16 is variably subnetted, "
                   f"{len(kept)} subnets, {len({p for _a, _o, p in kept})} masks")
        for adv, o, pl in kept:
            out.append(f"D        {gpl.net(d, o)}/{pl} [90/409600] "
                       f"via {adv}, 00:04:11, Ethernet0/1")
    out.append("```")
    return "\n".join(out)


def acl_requirements(d, rnd, form):
    m = d["m"]
    tg = "、".join(f"`{gpl.net(d, o)}/24`" for o in d["target"])
    core = []
    if d["role"] == "filter":
        core.append(f"{m['DUT']} において、{tg} のネットワークからの通信のみが、"
                    f"サーバである `{d['srv_host']}` の TCP ポート "
                    f"{d['port']} に到達できなければなりません。")
        if d["fourth_forbidden"]:
            core.append(f"`{gpl.net(d, d['fourth'])}/24` からの通信は、"
                        "許可されてはなりません。")
        core.append(f"`{gpl.net(d, d['outsider'])}/24` からの通信は、"
                    "許可されてはなりません。")
        w = {"one_line": "アクセス・リストのエントリは、1行で構成されなければなりません。",
             "exact_no_deny": "対象としていないネットワークが、"
                              "一致の対象に含まれてはなりません。"
                              "また、拒否のエントリを使用してはなりません。",
             "exact_min": "対象としていないネットワークが、"
                          "一致の対象に含まれてはなりません。"
                          "また、エントリの行数は、最小でなければなりません。",
             }[d["world"]]
        core.append(w)
    elif d["role"] in ("copp", "urpf", "nat", "vty"):
        goal = {
            "copp": f"{m['DUT']} において、管理のためのトラフィックが、"
                    "意図されたクラスにおいて処理されなければなりません。",
            "urpf": f"{m['DUT']} において、着信インターフェイスと一致しない送信元を"
                    "持つところのトラフィックが、破棄されなければなりません。",
            "nat": f"{m['DUT']} において、{tg} のネットワークからの通信のみが、"
                   "アドレスの変換の対象とされなければなりません。",
            "vty": f"{m['DUT']} への管理のための接続は、"
                   f"{tg} のネットワークからのみ、受理されなければなりません。",
        }[d["role"]]
        core.append(goal)
        core.append({"protect_mgmt": "管理のための端末からの接続および運用に、"
                                     "影響を与えてはなりません。",
                     "least_change": "変更は、必要最小限に留められなければなりません。",
                     }[d["world"]])
    else:
        core.append(f"{m['DUT']} は、{tg} のルートのみを、"
                    "ルーティング・テーブルに保持しなければなりません。")
        w = {"prefixlen_no_rm": "プレフィックスの長さが異なるルートは、"
                                "区別して扱われなければなりません。"
                                "ルート・マップを使用してはなりません。",
             "prefixlen_via_rm": "プレフィックスの長さが異なるルートは、"
                                 "区別して扱われなければなりません。"
                                 "プレフィックス・リストを使用してはなりません。",
             "by_neighbor": "フィルタリングは、ルートを広告している"
                            "ネイバーに基づいて、行われなければなりません。",
             "keep_others": "上記以外のルートの受理には、"
                            "影響を与えてはなりません。",
             }[d["world"]]
        core.append(w)
    core += rnd.sample([x for x in REQ_DECOYS if "スタティック" not in x], 1)
    rnd.shuffle(core)
    return finalize_reqs(core, rnd)


def acl_requirements_patch(d, rnd):
    """★patch は要件と判定の対象を**字面で一致**させる(BL-101 の教訓=
    「評価モデルが守る対象と、問題文が要求する対象は一致していなければならない」)。
    判定に使う観測集合(gpl.patch_targets)そのものを要件文に書く。"""
    m = d["m"]
    keep = "、".join(f"`{gpl.net(d, o)}/24`" for o in d["target"])
    core = [
        f"`{gpl.net(d, d['outsider'])}/24` からの通信は、"
        f"{m['DUT']} において拒否されなければなりません。",
        f"{keep} からの通信には、影響を与えてはなりません。",
        "既存のエントリを、削除または変更してはなりません"
        "(追加のみが認められています)。",
    ]
    rnd.shuffle(core)
    return finalize_reqs(core, rnd)


def acl_requirements_fix(d, rnd):
    """★fix も同様に、残すルート・落とすルートを**判定に使う集合そのもの**で書く。"""
    m = d["m"]
    keep = [f"`{gpl.net(d, o)}/{pl}`" for _a, o, pl, k in gpl.fix_routes(d) if k]
    drop = [f"`{gpl.net(d, o)}/{pl}`" for _a, o, pl, k in gpl.fix_routes(d)
            if not k]
    core = [
        f"{m['DUT']} は、{'、'.join(keep)} のルートを、"
        "ルーティング・テーブルに保持しなければなりません。",
        f"{'、'.join(drop)} のルートは、受理されてはなりません。",
    ]
    if d["world"] == "prefixlen_no_rm":
        core.append("プレフィックスの長さが異なるルートは、"
                    "区別して扱われなければなりません。"
                    "ルート・マップを使用してはなりません。")
    elif d["world"] == "prefixlen_via_rm":
        core.append("プレフィックスの長さが異なるルートは、"
                    "区別して扱われなければなりません。"
                    "プレフィックス・リストを使用してはなりません。")
    else:
        core.append("フィルタリングは、ルートを広告しているネイバーに基づいて、"
                    "行われなければなりません。")
    rnd.shuffle(core)
    return finalize_reqs(core, rnd)


def question_md_acl(d, blocks, choices, stamp, form="cause", reqs=None,
                    style="prose"):
    m = d["m"]
    state_blocks, cfg_blocks = blocks
    if reqs is None:
        reqs = acl_requirements(d, random.Random(0), form)
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
    elif form == "counter":
        pr = d["_counter_probe"]["text"]
        q = (f"{pr} が処理されるとき、一致のカウンタが増加するのは、どの行ですか。"
             "(1つを選択してください)")
    elif form == "patch":
        q = ("既存のエントリを変更することなく、1つのエントリを追加することによって、"
             "示されているところの要件を満たすものは、どれですか。"
             "(1つを選択してください)")
    elif form == "fix":
        q = ("示されているところのすべての要件が満たされることを確実にするために、"
             "適用されなければならない構成は、どれですか。(1つを選択してください)")
    elif form == "evidence":
        q = ("この事象の原因を特定するために、次に取得するべき出力として、"
             "最も多くの候補を除外できるものは、どれですか。(1つを選択してください)")
    elif form == "logread":
        q = ("示されているところの記録および構成から読み取ることができるものは、"
             "どれですか。(2つを選択してください)")
    elif form == "select":
        q = ("示されているところのすべての要件を満たすものは、どれですか。"
             "(1つを選択してください)")
    else:
        want = d.get("_read_want", 1)
        _c, _t, _f, s_true, s_false = gpl.read_labels(d)
        subj = s_true if d.get("_read_polarity") == "pass" else s_false
        n = "2つ" if want == 2 else "1つ"
        q = (f"示されているところの構成において、{subj}は、どれですか。"
             f"({n}を選択してください)")
    opts = render_options(choices, style)
    intro = (f"ある企業のネットワークにおいて、{m['DUT']} は、顧客の側の"
             f"ネットワークと、サーバの側のネットワークとの間に、"
             f"配置されています。")
    if d["role"] == "routefilter":
        intro += (f"{m['DUT']} は、{m['UP']} および {m['DN']} の両方から、"
                  "ルーティング・プロトコルによってルートを学習しています。")
    body_state = ("\n".join(state_blocks) if state_blocks else "")
    sec_state = (f"## 現在の状態\n\n{body_state}\n" if body_state else "")
    sec_cfg = (f"## 設定抜粋\n\n{chr(10).join(cfg_blocks)}\n" if cfg_blocks else "")
    return f"""# 問題 {stamp} : アクセス・リストの分析

{FIXED_NOTE}

## トポロジ

{terse_jp(intro)}

{acl_topo(d)}

## 要件

{chr(10).join(reqs)}

{sec_state}{sec_cfg}## 設問

{q}

## 選択肢

{opts}
"""


def answer_md_acl(d, choices, stamp, master_seed, subseed, form):
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = ", ".join(l for l, c in zip(letters, choices) if c[1])
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                       for l, c in zip(letters, choices))
    kind_note = {
        "wc_narrow": "ワイルドカードが狭く、対象の一部が一致しない",
        "wc_wide": "ワイルドカードが広く、対象外まで一致する",
        "wc_bits": "非連続ワイルドカードで一致が飛び地になる",
        "mask_as_wildcard": "★ワイルドカード欄にサブネット・マスクを記述"
                            "(実機は受理するが、アドレスが正規化されて別集合になる)",
        "order_shadow": "先行の広い permit が後続を影にする",
        "std_len_blind": "★標準 ACL はプレフィックス長を区別できない",
        "ext_named_rejected": "★名前付き拡張 ACL は distribute-list に指定できず、"
                              "フィルタ自体が適用されない",
        "ext_src_is_network": "★拡張 ACL の src は「広告元のルータ」であって"
                              "「ネットワーク」ではない",
        "undef_ref": "★未定義の ACL を参照 → 全許可",
        "empty_acl": "★空の ACL → 全許可",
        "copp_deny_to_default": "★CoPP の deny は「通す」ではなく class-default 行き",
        "urpf_undef_exempt": "★uRPF の例外 ACL が未定義 → 全免除(検証が無力化)",
        "nat_deny_scope": "NAT の変換対象を選ぶ ACL で、deny の範囲が広すぎる",
        "vty_wc_wrong": "access-class の許可範囲が管理端末を含んでいない",
    }[d["kind"]]
    world_note = {
        "one_line": "1行で書く(過剰被覆キューブが正解)",
        "exact_no_deny": "過剰許可なし＋deny 禁止(厳密列挙が正解)",
        "exact_min": "過剰許可なし＋行数最小(deny 先行が正解)",
        "prefixlen_no_rm": "長さを区別する(ルート・マップ禁止)→ prefix-list が正解",
        "prefixlen_via_rm": "長さを区別する(prefix-list 禁止)→ ★route-map 経由の拡張 ACL が正解",
        "by_neighbor": "広告元のネイバーに基づいて絞る",
        "keep_others": "他のルートに影響を与えない",
        "protect_mgmt": "管理のための接続・運用に影響を与えない",
        "least_change": "変更は必要最小限",
    }[d["world"]]
    works = (f"(「要件を無視すれば成立する候補」= "
             f"{', '.join(d.get('_select_works', []))} のうち要件適合は1つ)"
             if form == "select" else "")
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態

- 種別: `acl/{d['kind']}`(ロール= {d['role']}) — {kind_note}
- 要件世界: {world_note}{works}
- 出題形: {form}
- 生成: `gen_paper_mcq.py --shape acl --seed {master_seed}` (sub-seed {subseed})

## 各選択肢の判定

{wrongs}

## ★この分野の最重要知見(BL-106 PoC 実測・poc/acl/README.md)

1. **未定義の ACL を参照したときの帰結は、ロールによって違う**。
   インターフェイス(`ip access-group`)・`distribute-list`・uRPF の例外リストは
   **全許可**になる。一方 CoPP の `match access-group` と NAT の `source list` は
   **どれにも一致しない**。**空の ACL も全許可**であり、「暗黙 deny だけが残って
   全断」ではない。
2. ★★**`distribute-list` における拡張 ACL の意味は、参照の経路によって切り替わる**
   (実測 poc/acl §4・§16):
   - **直接指定** `distribute-list <番号> in` …
     **src = ルートを広告してきた隣接ルータ / dst = 広告されたネットワーク**
     (プレフィックスの長さは見ない)
   - **ルート・マップ経由** `distribute-list route-map <名前> in` …
     **src = ネットワーク / dst = サブネット・マスク**(いわゆる教科書の形)。
     こちらには「広告元」の概念が無い。
   同じアクセス・リストでも、**どちらから参照されるかで意味が変わる**。
3. したがって**プレフィックスの長さを区別する手段は2つある**=
   **prefix-list** と、**ルート・マップ経由の拡張 ACL**(`... host 255.255.255.0`)。
   一方、**直接指定の拡張 ACL では長さを区別できない**
   (同じネットワーク・アドレスの /24 と /28 は必ず道連れになる)。
   また **名前付きの拡張 ACL は、先に定義してから参照すると拒否される**が、
   **先に参照してから定義すると受理される**(投入の順序に依存する)。
4. ワイルドカードの欄に**サブネット・マスクを書いても IOS は受理する**が、
   don't care 側のビットがアドレスから落とされるため、
   `10.0.0.0 255.0.0.0` は `0.0.0.0, wildcard bits 255.0.0.0` として扱われる
   (= 「10.x.x.x」ではなく「第2〜4オクテットが 0.0.0 の全アドレス」)。

## ENARSI ブループリント

- 3.2.a IPv4 アクセス・コントロール・リスト(標準/拡張)
- 1.2 ルート・マップ / フィルタリング(distribute-list)
"""


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
    return finalize_reqs(core, rnd)


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


def topo_links_pbr(d):
    """pbr のリンク一覧。図からエッジ・ラベルを外した(BL-087)ぶん、
    配線とアドレスはここが正典になる。"""
    m = d["m"]
    return ("リンク一覧:\n```\n"
            + f"  {m['HUB']}(.1) ── {m['DST']}(.2)   192.168.{d['seg']}.0/29\n"
            + f"  {m['HUB']}(.254) ── {m['CLA']}      192.168.{d['lan_a']}.0/24\n"
            + f"  {m['HUB']}(.254) ── {m['CLB']}      192.168.{d['lan_b']}.0/24\n"
            + "```")


def question_md_pbr(d, plan, choices, collected, stamp, sites=None, form="fix",
                    reqs=None, style="prose"):
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
    opts = render_options(choices, style)
    return f"""# 問題 {stamp} : ポリシーによるルーティングのための分析

{FIXED_NOTE}

## トポロジ

{terse_jp(PBR_INTRO)}

{messy_mermaid(mermaid_pbr(d, sites))}

{topo_links_pbr(d)}

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
    correct = [l for l, c in zip(letters, choices) if c[1]][0]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                        for l, c in zip(letters, choices))
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
    return finalize_reqs(core, rnd)


def question_md_urpf(d, blocks, choices, stamp, sites=None, form="fix", reqs=None,
                     style="prose"):
    m = d["m"]
    e, a, b = m["EDGE"], m["ISPA"], m["ISPB"]
    state_blocks = blocks[:4]
    cfg_blocks = blocks[4:]
    if reqs is None:
        reqs = urpf_requirements(d, random.Random(0), sites)
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
    elif style == "cli":
        q = ("示されているところのすべての要件が満たされることを確実にするために、"
             "適用されなければならない構成は、どれですか。(1つを選択してください)")
    else:
        q = ("この問題を解決し、そして、示されているところのすべての要件が"
             "満たされることを確実にするために、必要とされる手順は、どれですか。"
             "(1つを選択してください)")
    opts = render_options(choices, style)
    topo = (f"```\n"
            f"          {e} (エッジ・被験のデバイス)\n"
            f"   {'Ethernet0/0'} |            | {'Ethernet0/1'}\n"
            f"  {d['link_a']}.0/30      {d['link_b']}.0/30\n"
            f"        |                    |\n"
            f"      {a} (ISP-A)        {b} (ISP-B)\n```")
    return f"""# 問題 {stamp} : 送信元アドレスの検証のための分析

{FIXED_NOTE}

## トポロジ

{terse_jp(URPF_INTRO.format(a=d['cust_sym'], b=d['cust_asym']))}

{topo}

- 監視のためのホスト `{d['exc_host']}` および `{d['exc_host2']}` は、ISP-B を経由して着信します。

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
    correct = [l for l, c in zip(letters, choices) if c[1]][0]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                        for l, c in zip(letters, choices))
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
# shape=leakmap — EIGRP 集約×リーク 手段選択 (gen_paper_leakmap 流用・BL-095)
# ★紙面専用: 挙動は実機確定表(poc/leakmap/README.md)の写像モデルから決定的に生成。
# --------------------------------------------------------------------------
def pick_draw_leakmap(qseed, kind):
    for kk in range(200):
        s = qseed + kk * 139
        try:
            return s, gpk.draw(random.Random(s), kind=kind)
        except ValueError:
            continue
    raise SystemExit(f"leakmap kind={kind} が成立する seed が見つかりません({qseed})")


def _lm_classful(pfx):
    a = int(pfx.split(".")[0])
    o = pfx.split(".")
    if a < 128:
        return f"{o[0]}.0.0.0", 8
    if a < 192:
        return f"{o[0]}.{o[1]}.0.0", 16
    return f"{o[0]}.{o[1]}.{o[2]}.0", 24


def _lm_v(ip):
    a = [int(x) for x in ip.split(".")]
    return (a[0] << 24) | (a[1] << 16) | (a[2] << 8) | a[3]


def leakmap_table(d, recvmap, upt):
    """RCV 側 show ip route eigrp | begin Gateway の忠実な描画(実測書式)。"""
    lines = ["Gateway of last resort is not set"]
    groups = {}
    for p, (code, plen, met) in recvmap.items():
        major, clen = _lm_classful(p)
        groups.setdefault((major, clen), []).append((p, code, plen, met))
    for (major, clen), ents in sorted(groups.items(),
                                      key=lambda kv: _lm_v(kv[0][0])):
        plens = {e[2] for e in ents}
        if len(plens) == 1:
            pl = plens.pop()
            lines.append(f"      {major}/{pl} is subnetted, {len(ents)} subnets")
            sfx = False
        else:
            lines.append(f"      {major}/{clen} is variably subnetted, "
                         f"{len(ents)} subnets, {len(plens)} masks")
            sfx = True
        for p, code, plen, met in sorted(ents, key=lambda e: _lm_v(e[0])):
            addr = f"{p}/{plen}" if sfx else p
            lines.append(f"{code:<9}{addr} {met} via {d['link']}.1, "
                         f"{upt}, {d['ifname']}")
    return "\n".join(lines)


def leakmap_cfg(d, st):
    """ADV 側 running-config 抜粋(乱立リスト込み・現在状態の忠実な描画)。"""
    a, S, w = d["asn"], d["block"], d["mask"]
    L = []
    for i, lo in enumerate(d["los"]):
        L += [f"interface Loopback{i}", f" ip address {lo} 255.255.255.255"]
    L += ["interface Loopback10",
          f" ip address {d['ops_lo']} 255.255.255.255"]
    L += [f"interface {d['ifname']}",
          f" description === to {d['m']['RCV']} ===",
          f" ip address {d['link']}.1 255.255.255.252"]
    if st["summary"]:
        lk = st["summary"]["leak"]
        L.append(f" ip summary-address eigrp {a} {S} {w}"
                 + (f" leak-map {lk}" if lk else ""))
    L += ["!", f"router eigrp {a}"]
    for p in st["inject"]:
        L.append(f" network {p} 0.0.0.0")
    L.append(f" network {d['link']}.0 0.0.0.3")
    if st["redist_static"]:
        L.append(" redistribute static")
    if st["redist_conn"] is not None:
        L.append(f" redistribute connected route-map "
                 f"{st.get('redist_rm') or 'RM-CONN'}")
    L.append("!")
    if st["null0"]:
        L += [f"ip route {S} {w} Null0", "!"]
    for name, ents in sorted(st["pls"].items()):
        for i, e in enumerate(ents, 1):
            L.append(f"ip prefix-list {name} seq {i * 5} permit {e}")
    for num, hosts in sorted(st["acls"].items()):
        for h in hosts:
            L.append(f"access-list {num} permit {h}")
    L.append("!")
    for name, ents in sorted(st["rmaps"].items()):
        for i, ent in enumerate(ents, 1):
            act, mtype = ent[0], ent[1]
            ref = ent[2] if len(ent) > 2 else None
            L.append(f"route-map {name} {act} {i * 10}")
            if mtype == "pl":
                L.append(f" match ip address prefix-list {ref}")
            elif mtype == "acl":
                L.append(f" match ip address {ref}")
    L.append("!")
    return "\n".join(L)


def leakmap_evidence(d, rnd, form):
    """紙面に出すブロック群(state=経路表 / cfg=構成)。read 形は経路表を出さない。"""
    st = gpk.state(d)
    adv, rcv = d["m"]["ADV"], d["m"]["RCV"]
    upt = f"00:{rnd.randint(0, 20):02d}:{rnd.randint(10, 59):02d}"
    state_blocks = []
    if form != "read":
        state_blocks.append(
            f"```\n{rcv}# show ip route eigrp | begin Gateway\n"
            + leakmap_table(d, gpk.recv(d, st), upt) + "\n```")
    cfg_blocks = [f"```\n{adv}# show running-config\n"
                  "Building configuration...\n!\n" + leakmap_cfg(d, st) + "\n```"]
    return state_blocks, cfg_blocks


def leakmap_requirements(d, rnd):
    S, T = d["block"], d["target"]
    rcv = d["m"]["RCV"]
    world_txt = {
        "no_redist": "ルートの再配送(redistribute)は、いかなる形においても、"
                     "使用されてはなりません。",
        "no_network_lo": "ブロックのループバックのインターフェイスを、network の"
                         "ステートメントによって EIGRP へ参加させることは、"
                         "認められていません。",
        "internal_only": "集約のルートおよび明細のルートは、いずれも、EIGRP の"
                         "内部のルート(アドミニストレーティブ・ディスタンス 90)"
                         "として受信されなければなりません。",
        "no_if_summary": "インターフェイスにおける集約"
                         "(ip summary-address)の構成は、過去の障害の経緯という"
                         "理由により、認められていません。",
    }[d["world"]]
    core = [
        f"{rcv} に対して、ブロック {S}/{d['wid']} は、集約のルートとして"
        "広告されなければなりません。",
        "ブロックの内部の明細のルートは、広告されてはなりません。",
        f"ただし、監視のためのホストである {T} (/32) の明細のルートは、"
        "集約とともに、受信されなければなりません。",
        f"運用のためのループバック {d['ops_lo']} (/32) は、引き続き"
        "受信されなければなりません。",
        world_txt,
    ]
    core += rnd.sample([x for x in REQ_DECOYS if "スタティック" not in x], 1)
    rnd.shuffle(core)
    return finalize_reqs(core, rnd)


def build_choices_read(d, rnd):
    """read 形: RCV の経路表そのものを選択肢にする(描画で重複排除)。"""
    upt = f"00:{rnd.randint(0, 20):02d}:{rnd.randint(10, 59):02d}"
    cur, alts = gpk.read_variants(d)
    # ★設問が汎用化(obfuscate)されても自立して読めるよう、プロンプト行を含める
    pr = f"{d['m']['RCV']}# show ip route eigrp | begin Gateway\n"
    correct_txt = pr + leakmap_table(d, cur, upt)
    seen = {correct_txt}
    c = [(correct_txt, True, "")]
    rnd.shuffle(alts)
    for label, rm in alts:
        txt = pr + leakmap_table(d, rm, upt)
        if txt in seen:
            continue
        seen.add(txt)
        c.append((txt, False, f"別の状態({label})の観測結果である。"))
        if len(c) == 4:
            break
    if len(c) < 3:
        raise ValueError("leakmap read: 選択肢が畳まれすぎ")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


LEAKMAP_INTRO = (
    "拠点のルータ {adv} は、複数のループバック・インターフェイスによって、"
    "サービスのためのアドレスのブロック {S}/{wid} を収容しています。"
    "{adv} と {rcv} は、1本のリンクによって直接に接続されており、そして、"
    "EIGRP {asn} が構成されています。")


def question_md_leakmap(d, blocks, choices, stamp, form="fix", reqs=None,
                        style="prose"):
    adv, rcv = d["m"]["ADV"], d["m"]["RCV"]
    state_blocks, cfg_blocks = blocks
    if reqs is None:
        reqs = leakmap_requirements(d, random.Random(0))
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
        opts = render_options(choices, "prose")
    elif form == "read":
        q = (f"示されているところの構成に基づいて、{rcv} において観測される"
             "ところの出力は、どれですか。(1つを選択してください)")
        letters = [chr(65 + i) for i in range(len(choices))]
        opts = "\n".join(f"**{l}.**\n```\n{c[0]}\n```"
                         for l, c in zip(letters, choices))
    elif style == "cli":
        q = ("示されているところのすべての要件が満たされることを確実にするために、"
             "適用されなければならない構成は、どれですか。(1つを選択してください)")
        opts = render_options(choices, style)
    else:
        q = ("この問題を解決し、そして、示されているところのすべての要件が"
             "満たされることを確実にするために、必要とされる手順は、どれですか。"
             "(1つを選択してください)")
        opts = render_options(choices, style)
    topo = (f"```\n  [{adv}]  Lo: {', '.join(d['los'])} (+ {d['ops_lo']})\n"
            f"    {d['link']}.1 ─────({d['ifname']})───── {d['link']}.2\n"
            f"  [{rcv}]\n```")
    fam_missing = d["kind"] in ("no_leakmap", "rmap_undefined",
                                "pl_wrong_prefix", "not_injected",
                                "shared_map_wrong_target")
    if form == "read":
        sympt = "構成の変更の適用後の、観測の結果が、確認されようとしています。"
    elif fam_missing:
        sympt = (f"監視のためのホスト {d['target']} の /32 の明細のルートが、"
                 f"{rcv} の経路テーブルに存在しない、ということが、"
                 "報告されています。")
    else:
        sympt = ("抑止されているはずであるところのブロックの明細のルートが、"
                 f"{rcv} において受信されている、ということが、報告されています。")
    intro = LEAKMAP_INTRO.format(adv=adv, rcv=rcv, S=d["block"],
                                 wid=d["wid"], asn=d["asn"])
    return f"""# 問題 {stamp} : EIGRP の集約とリークの分析

{FIXED_NOTE}

## トポロジ

{terse_jp(intro)}

{topo}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{terse_jp(sympt)}

{chr(10).join(state_blocks)}

## 設定抜粋

{chr(10).join(cfg_blocks)}

## 設問

{q}

## 選択肢

{opts}
"""


def answer_md_leakmap(d, choices, stamp, master_seed, subseed, form):
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, c in zip(letters, choices) if c[1]][0]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                       for l, c in zip(letters, choices))
    kind_note = {
        "no_leakmap": "summary-address に leak-map 未指定 → リークなし",
        "rmap_undefined": "leak-map の参照 route-map がタイポで未定義 → "
                          "★リークなし(全リークではない・実測)",
        "pl_undefined": "route-map は在るが参照リストが未定義 → ★全リーク(実測)",
        "pl_wrong_prefix": "リストの許可対象が別 Lo → 対象は漏れず別明細が漏れる",
        "permit_no_match": "permit 節に match なし → 全リーク",
        "not_injected": "対象 Lo が EIGRP に未参加 → リークなし"
                        "(★集約経由で ping は通る=広告と到達の乖離)",
        "shared_map_wrong_target": "★エコ形(redistribute×leak-map が同一 RM 共用)"
                                   "の編集副作用 → 対象は投入ごと消失・別 Lo が "
                                   "D EX で漏れる(実測 V5)",
    }[d["kind"]]
    world_note = {
        "no_redist": "再配送禁止 → network 投入+leak-map が唯一適合",
        "no_network_lo": "Lo の network 参加禁止 → redistribute connected 投入"
                         "+leak-map(明細は D EX で届く・実測)",
        "internal_only": "内部ルート(AD90)限定 → network 投入+leak-map",
        "no_if_summary": "IF 集約禁止 → static Null0+redistribute static"
                         "(集約は D EX [170/281600]・実測)",
    }[d["world"]]
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態

- 種別: `leakmap/{d['kind']}` — {kind_note}
- 要件世界: `{d['world']}` — {world_note}
- 出題形: {form}(機能的に「直る候補」= {', '.join(d['_works'])})
- 生成: `gen_paper_mcq.py --shape leakmap --seed {master_seed}` (sub-seed {subseed})

## 各選択肢の判定

{wrongs}

## 検証コマンドと期待される出力

- 受信側 `show ip route eigrp`: 集約 `{d['block']}/{d['wid']}` と、リークされた
  `{d['target']}/32` の**両方**が存在すること(他の明細が存在しないこと)。
- 広告側 `show ip eigrp topology {d['block']}/{d['wid']}`: Null0 サクセサの
  集約エントリ(summary-address 使用時)。

## ★この分野の最重要知見(BL-095 PoC 実測・poc/leakmap/README.md)

**「投入・集約・リーク」は独立した3レバー**であり、リークには「成分がトポロジ・
テーブルに存在する」かつ「leak-map の route-map が permit する」の両方が必要。
そして挙動は非対称: **route-map ごと未定義なら「何も漏れない」が、route-map の
器だけ在って中身が空振り(未定義リスト参照・match なし permit)だと「全部漏れる」**。
また、network に参加していないブロック内アドレスも、集約に吸われて到達自体は
できてしまう(広告されていない=届かない、ではない)。

## ENARSI ブループリント

- 1.0 Layer 3 Technologies — EIGRP summarization / route filtering
"""


# --------------------------------------------------------------------------
# shape=ospfv3pl — OSPFv3 マルチエリア prefix-list (gen_paper_ospfv3pl 流用・BL-097)
# ★紙面専用: 挙動は実機確定表(poc/ospfv3-pl/README.md)の写像モデルから決定的に生成。
# --------------------------------------------------------------------------
def pick_draw_ospfv3pl(qseed, kind):
    for kk in range(200):
        s = qseed + kk * 139
        try:
            return s, gpo.draw(random.Random(s), kind=kind)
        except ValueError:
            continue
    raise SystemExit(f"ospfv3pl kind={kind} が成立する seed が見つかりません({qseed})")


def _o3pl_ll(d, dev):
    """観測ルータから見た R2 のリンクローカル(実測書式・d から決定的に導出)。"""
    bb = 0x20 + (d["s"] * 29 + d["a1"] * 7 + d["proc"]) % 0xC0
    port = "00" if dev == "R1" else "20"
    return f"FE80::A8BB:CCFF:FE01:{bb:02X}{port}"


def o3pl_table(d, rows, dev):
    """`show ipv6 route ospf | include ^O|via` の忠実な描画(実測書式)。"""
    ll = _o3pl_ll(d, dev)
    lines = []
    for (val, plen), met in sorted(rows.items()):
        lines.append(f"OI  {gpo.fmt_v(val, plen)} [110/{met}]")
        lines.append(f"     via {ll}, Ethernet0/0")
    return "\n".join(lines)


def ospfv3pl_cfg(d, st):
    """R2 running-config 抜粋(現在状態の忠実な描画・乱立リスト込み)。"""
    p, a1, a2 = d["proc"], d["a1"], d["a2"]
    L = []
    for ifn, lkey, area in [("Ethernet0/0", "a1", a1),
                            ("Ethernet0/1", "a0", 0),
                            ("Ethernet0/2", "a2", a2)]:
        net = gpo.fmt(*d["lnk"][lkey], 64)[:-3]      # "…::" 形
        L += [f"interface {ifn}", " no ip address",
              f" ipv6 address {net}2/64", " ipv6 enable",
              f" ipv6 ospf {p} area {area}", "!"]
    L += [f"router ospfv3 {p}", " router-id 2.2.2.2", " !",
          " address-family ipv6 unicast"]
    for fl in st["fl"]:
        L.append("  " + gpo._fl_line(d, fl))
    if st["range"]:
        L.append("  " + gpo._range_line(d, st["range"]))
    if st["dl"] and st["dl"][0] == "R2":
        L.append(f"  distribute-list prefix-list {st['dl'][1]} in")
    L += [" exit-address-family", "!"]
    for name in sorted(st["pls"]):
        for i, ent in enumerate(st["pls"][name], 1):
            L.append(gpo.ent_cli(name, i * 5, ent))
        L.append("!")
    return "\n".join(L)


def ospfv3pl_cfg_r1(d, st):
    """R1 側の ospfv3 セクション(distribute-list が R1 に載る盤面のみ提示)。"""
    L = [f"router ospfv3 {d['proc']}", " router-id 1.1.1.1", " !",
         " address-family ipv6 unicast"]
    if st["dl"] and st["dl"][0] == "R1":
        L.append(f"  distribute-list prefix-list {st['dl'][1]} in")
    L += [" exit-address-family"]
    return "\n".join(L)


def ospfv3pl_evidence(d, rnd, form):
    """紙面に出すブロック群。read 形は経路表を出さない(逆引きのため)。"""
    st = gpo.state(d)
    m = gpo.model(d, st)
    state_blocks = []
    if form != "read":
        state_blocks.append(
            "```\nR1# show ipv6 route ospf | include ^O|via\n"
            + o3pl_table(d, m["t1"], "R1") + "\n```")
        state_blocks.append(
            "```\nR3# show ipv6 route ospf | include ^O|via\n"
            + o3pl_table(d, m["t3"], "R3") + "\n```")
    cfg_blocks = [f"```\nR2# show running-config\n"
                  "Building configuration...\n!\n" + ospfv3pl_cfg(d, st) + "\n```"]
    if st["dl"] and st["dl"][0] == "R1":
        cfg_blocks.append(
            "```\nR1# show running-config | section router ospfv3\n"
            + ospfv3pl_cfg_r1(d, st) + "\n```")
    return state_blocks, cfg_blocks


def ospfv3pl_requirements(d, rnd):
    a1, a2 = d["a1"], d["a2"]
    pair_t = (f"{gpo.fmt(d['pair'], d['pair'], 64)} および "
              f"{gpo.fmt(d['pair'] + 1, d['pair'] + 1, 64)}")
    tgt = gpo.fmt(d["target"], d["target"], 64)
    world_reqs = {
        "area10_only": [
            f"エリア {a1} のルータの経路テーブルには、ループバックに由来する"
            f"エリア間のルートとして、{pair_t} のみが存在しなければなりません。"
            + ("リンクのネットワークのルートは、引き続き受信されなければ"
               "なりません。" if d["keep_links"] else
               "その他のエリア間のルートは、存在してはなりません。"),
            f"エリア {a2} のルータの経路テーブルは、いかなる影響も"
            "受けてはなりません。",
            f"この制御は、エリア {a1} に今後追加されるところの、いかなる"
            "ルータに対しても、等しく適用されなければなりません。",
        ],
        "hide_all": [
            f"{tgt} のルートは、バックボーン以外のすべてのエリアから、"
            "隠されなければなりません。",
            "その他のルートの広告は、いかなる影響も受けてはなりません。",
            "適用は、単一のステートメントの追加によって、実現されなければ"
            "なりません。",
            "R2 自身の経路テーブルは、影響を受けてはなりません。",
        ],
        "rib_only": [
            f"R1 の経路テーブルから、{tgt} のルートが、除外されなければ"
            "なりません。",
            f"エリア {a1} へ広告される LSA(データベースの内容)は、"
            "維持されなければなりません。",
            "他のいかなるルータの経路テーブルにも、影響が及んでは"
            "なりません。",
        ],
        "summarize": [
            "4本のループバックのプレフィックスは、単一の集約のルートとして、"
            "他のエリアへ広告されなければなりません。",
            "集約は、対象を包含するところの、最長のプレフィックス長"
            "(最小の範囲)でなければなりません。",
            "ループバックの明細のルートは、広告されてはなりません。",
            "リンクのネットワークの広告は、影響を受けてはなりません。",
        ],
        "suppress_all": [
            "4本のループバックのプレフィックスは、集約としても、明細としても、"
            "いかなるエリアへも広告されてはなりません。",
            "新たなプレフィックス・リストの定義は、認められていません。",
            "R2 自身の経路テーブルは、影響を受けてはなりません。",
        ],
        "dual_select": [
            f"エリア {a1} へ配布されるループバック由来のエリア間のルートは、"
            f"{pair_t} に限定されなければなりません。リンクのネットワークの"
            "ルートは、引き続き受信される必要があります。",
            f"ただし、{tgt} のルートは、障害の対応という理由により、"
            "**すべてのエリアにおいて**、一時的に停止されなければなりません。",
            f"エリア {a2} においては、{tgt} を除くいかなるルートの受信にも、"
            "影響が及んではなりません。",
            f"この制御は、エリア {a1} に今後追加されるところの、いかなる"
            "ルータに対しても、等しく適用されなければなりません。",
        ],
    }[d["world"]]
    core = list(world_reqs) + rnd.sample(REQ_DECOYS, 1)
    rnd.shuffle(core)
    return finalize_reqs(core, rnd)


def build_choices_read_o3pl(d, rnd):
    """read 形: R1 の経路表そのものを選択肢にする(描画で重複排除)。"""
    cur, alts = gpo.read_variants(d)
    pr = "R1# show ipv6 route ospf | include ^O|via\n"
    correct_txt = pr + o3pl_table(d, cur, "R1")
    seen = {correct_txt}
    c = [(correct_txt, True, "")]
    rnd.shuffle(alts)
    for label, rows in alts:
        txt = pr + o3pl_table(d, rows, "R1")
        if txt in seen:
            continue
        seen.add(txt)
        c.append((txt, False, f"別の解釈({label})に基づく出力である。"))
        if len(c) == 4:
            break
    if len(c) < 3:
        raise ValueError("ospfv3pl read: 選択肢が畳まれすぎ")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


O3PL_SYMPTOM = {
    "none": "要件は、まだ実装されていません。構成の変更が、計画されています。",
    "mask_off": {
        "dual_select": "意図されていないところのエリア間のルートが、R1 において"
                       "受信され続けている、ということが、報告されています。",
        "area10_only": "意図されていないところのエリア間のルートが、R1 において"
                       "受信され続けている、ということが、報告されています。",
        "hide_all": "対象ではないところのルートまでもが、複数のエリアにおいて"
                    "失われている、ということが、報告されています。",
        "rib_only": "対象ではないところのルートまでもが、R1 の経路テーブルから"
                    "失われている、ということが、報告されています。",
        "summarize": "一部の明細のルートが、引き続き広告されている、ということが、"
                     "報告されています。",
        "suppress_all": "一部の明細のルートが、引き続き広告されている、ということが、"
                        "報告されています。",
    },
    "le_missing": "R1 において、ループバックに由来するエリア間のルートが、"
                  "すべて経路テーブルから消失している、ということが、"
                  "報告されています。",
    "le_off": "R1 において、ループバックに由来するエリア間のルートが、"
              "すべて経路テーブルから消失している、ということが、"
              "報告されています。",
    "tail_default": {
        "hide_all": "すべてのエリアにおいて、エリア間のルートが、経路テーブルから"
                    "消失している、ということが、報告されています。",
        "rib_only": "R1 において、すべての OSPF のルートが、経路テーブルから"
                    "消失している、ということが、報告されています。",
    },
    "seq_shadow": "変更の適用の後においても、停止されているはずであるところの"
                  "ルートが、受信され続けている、ということが、報告されています。",
    "dir_swap": {
        "area10_only": "エリア {a2} のルータにおいても、ルートの欠落が発生している、"
                       "ということが、報告されています。",
        "hide_all": "エリア {a2} のルータにおいて、対象のルートが、受信され続けて"
                    "いる、ということが、報告されています。",
    },
    "dl_abr": "対象のルートが、R2 自身、および、エリア {a2} のルータからも、"
              "消失している、ということが、報告されています。",
    "block_off": "期待されているところのルートが不足し、そして、対象ではない"
                 "ところのルートが受信されている、ということが、報告されています。",
    "mask_narrow": "配布されるべきであるところのルートの一部が、経路テーブルに"
                   "存在しない、ということが、報告されています。",
    "dual_swap": "エリア {a2} において、対象外のルートの欠落が発生し、そして、"
                 "停止されているはずであるところのルートは、受信され続けている、"
                 "ということが、報告されています。",
}


def _o3pl_symptom(d):
    s = O3PL_SYMPTOM[d["kind"]]
    if isinstance(s, dict):
        s = s[d["world"]]
    return s.format(a2=d["a2"])


O3PL_INTRO = (
    "拠点の集約ルータ Ra は、サービスのためのプレフィックスを、4つの"
    "ループバック・インターフェイスによって収容しています。R2 は、"
    "エリア {a1}・エリア 0・エリア {a2} を接続するところの ABR であり、"
    "そして、すべてのルータにおいて、OSPFv3 のプロセス {p} が構成されています。")


def question_md_ospfv3pl(d, blocks, choices, stamp, form="fix", reqs=None,
                         style="prose"):
    state_blocks, cfg_blocks = blocks
    if reqs is None:
        reqs = ospfv3pl_requirements(d, random.Random(0))
    if form == "read":
        q = ("示されているところの構成に基づいて、R1 において観測される"
             "ところの出力は、どれですか。(1つを選択してください)")
        letters = [chr(65 + i) for i in range(len(choices))]
        opts = "\n".join(f"**{l}.**\n```\n{c[0]}\n```"
                         for l, c in zip(letters, choices))
    elif form == "patch":
        q = ("示されているところのすべての要件が満たされることを確実にするために、"
             "適用されなければならない修正は、どれですか。(1つを選択してください)")
        letters = [chr(65 + i) for i in range(len(choices))]
        opts = "\n".join(f"**{l}.**\n```\n" + "\n".join(c[3]) + "\n```"
                         for l, c in zip(letters, choices))
    elif style == "cli":
        q = ("示されているところのすべての要件が満たされることを確実にするために、"
             "適用されなければならない構成は、どれですか。(1つを選択してください)")
        opts = render_options(choices, style)
    else:
        q = ("この問題を解決し、そして、示されているところのすべての要件が"
             "満たされることを確実にするために、必要とされる手順は、どれですか。"
             "(1つを選択してください)")
        opts = render_options(choices, style)
    los_t = ", ".join(gpo.fmt(h, h, 64) for h in d["los"])
    # エリアラベルは各リンク区間の中央に動的配置(ずれると誤読を招く)
    main = (f"  [R1]--(E0/0: {gpo.fmt(*d['lnk']['a1'], 64)})--[R2]"
            f"--(E0/1: {gpo.fmt(*d['lnk']['a0'], 64)})--[Ra]")
    i_r2, i_ra = main.index("[R2]"), main.index("[Ra]")
    hdr = [" "] * len(main)

    def put(center, text):
        s = max(0, center - len(text) // 2)
        hdr[s:s + len(text)] = list(text)

    put((6 + i_r2) // 2, f"Area {d['a1']}")
    put((i_r2 + 4 + i_ra) // 2, "Area 0")
    branch = (" " * (i_r2 + 2)
              + f"└--(E0/2: {gpo.fmt(*d['lnk']['a2'], 64)})--[R3]"
              + f"  Area {d['a2']}")
    topo = ("```\n" + "".join(hdr).rstrip() + "\n" + main + "\n"
            + branch + "\n"
            f"  R1 E0/0 セカンダリ: {gpo.fmt(*d['lnk']['a1b'], 64)}"
            f" (Area {d['a1']})\n"
            f"  Ra Loopback: {los_t} (Area 0)\n```")
    if form == "read":
        sympt = "構成の適用後の、観測の結果が、確認されようとしています。"
    else:
        sympt = _o3pl_symptom(d)
    intro = O3PL_INTRO.format(a1=d["a1"], a2=d["a2"], p=d["proc"])
    return f"""# 問題 {stamp} : OSPFv3 のエリア間ルート・フィルタリング

{FIXED_NOTE}

## トポロジ

{terse_jp(intro)}

{topo}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{terse_jp(sympt)}

{chr(10).join(blocks[0])}

## 設定抜粋

{chr(10).join(cfg_blocks)}

## 設問

{q}

## 選択肢

{opts}
"""


def answer_md_ospfv3pl(d, choices, stamp, master_seed, subseed, form):
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, c in zip(letters, choices) if c[1]][0]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                       for l, c in zip(letters, choices))
    kind_note = {
        "none": "フィルタ未適用(構築問)",
        "mask_off": "一致範囲のマスク長違い(巻き添え/取り漏らし)",
        "le_missing": "le 欠落 → 当該長そのものにのみ一致=全滅(実測 E5)",
        "le_off": "le 63 → /64 を拾えず全滅(実測・追測)",
        "tail_default": "permit ::/0 の le 128 欠落 → デフォルトのみ一致=全滅"
                        "(実測 P9)",
        "seq_shadow": "広い permit が先行し deny が死に文(先勝ち)",
        "dir_swap": "in/out の取り違え(out は全他エリアに作用・実測 P1/P2)",
        "dl_abr": "ABR への distribute-list → Type-3 生成ごと停止(実測 P4)",
        "block_off": "範囲ずれ(隣の /47 ブロックを許可・16進の読み違い)",
        "mask_narrow": "狭すぎ(/48 で片割れ欠け)",
        "dual_swap": "方向逆(2枚のリストの in/out 取り違え)",
    }[d["kind"]]
    world_note = {
        "area10_only": "対象エリアだけに効かせる → area <a1> filter-list in"
                       "(out は第3エリアを巻き込む・dl は単一ルータのみ)",
        "hide_all": "全非バックボーンから1行で隠す → area 0 filter-list out",
        "rib_only": "RIB のみ・LSDB 維持 → R1 で distribute-list in"
                    "(ABR 適用は波及・filter-list は LSA ごと消す)",
        "summarize": "最小範囲の集約 → area 0 range(/45 か /46 かは"
                     "4値の並びの LCP で決まる)",
        "suppress_all": "PL 新設禁止で全停止 → area 0 range not-advertise",
        "dual_select": "★両掛け(手組ラボの主題): in=配布の限定(permit形・エリア"
                       "単位) × out=特定ルートの全域停止(deny形)の役割分担。"
                       "in だけでは第3エリアに停止が及ばず、out だけでは配布の"
                       "限定ができない",
    }[d["world"]]
    cover = gpo.fmt(gpo.block_base(d["s"], d["minlen"]), 0, d["minlen"])
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態

- 種別: `ospfv3pl/{d['kind']}` — {kind_note}
- 要件世界: `{d['world']}` — {world_note}
- 盤面: Lo 第3ヘクステット = {', '.join(f"{h:X}" for h in d['los'])}
  (最小被覆 = {cover})
- 出題形: {form}(機能的に成立する候補 = {', '.join(d['_works'])})
- 生成: `gen_paper_mcq.py --shape ospfv3pl --seed {master_seed}` (sub-seed {subseed})

## 各選択肢の判定

{wrongs}

## 検証コマンドと期待される出力

- R1/R3 `show ipv6 route ospf`: 要件どおりの OI ルートのみが存在すること。
- R2 `show ipv6 ospf database inter-area prefix`: フィルタ後に生成されている
  Type-3 の一覧(distribute-list と filter-list の効く層の違いを確認できる)。

## ★この分野の最重要知見(BL-097 PoC 実測・poc/ospfv3-pl/README.md)

- `area X filter-list out` は X 発の Type-3 を**全他エリア**で遮断し、`in` は
  当該エリアへの流入だけを遮断する(第3エリアがあると in/out は非等価)。
- distribute-list in は内部ルータでは RIB のみ(LSDB 残存)だが、
  **ABR に掛けると Type-3 の生成ごと止まり下流全域から消える**(生成は RIB 依存)。
- prefix-list の ge/le は厳密に len < ge ≤ le。le を欠くエントリは当該長のみ、
  `permit ::/0` はデフォルトのみ、`::/0 ge 1` はデフォルト以外の全部に一致する。
- /44〜/47 のヘクステット中間マスクは、第3ヘクステットを2進展開して判定する
  (1bit で被覆が 16/8/4/2 本と反転する)。

## ENARSI ブループリント

- 1.0 Layer 3 Technologies — OSPFv3 / route filtering (filter-list,
  distribute-list, area range)
"""


# --------------------------------------------------------------------------
# shape=bgpdbg — BGP debug 読解(★記述式・選択肢なし) BL-085
# 採点は自動化しない(自由記述)。answers/ にルーブリックを出し、Claude が採点する。
# --------------------------------------------------------------------------
def question_md_bgpdbg(d, stamp, rnd):
    A, B = d["A"], d["B"]
    a_lines, b_lines = gpb.debug_blocks(d, rnd)
    qs = gpb.questions(d)
    ebgp = d["variant"] == "ebgp_multihop"
    as_txt = (f"{A} は AS {d['as_a']}、{B} は AS {d['as_b']} に所属しています。"
              if ebgp else f"両ルータは、同一の AS {d['as_a']} に所属しています。")
    return f"""# 問題 {stamp} : BGP ピアの確立に関する分析(記述式)

> **本問は機器に接続せずに解答すること。追加の show 実行は認めない。**
> **本問は選択式ではありません。求められている内容を、文章で記述してください。**

## トポロジ

2台のルータが、1本のリンクによって直接に接続されており、そして、
それぞれのループバック・インターフェイスを使用して、BGP のピアが構成されています。
{as_txt}

```
  [{A}]  Lo0={d['lo_a']}          [{B}]  Lo0={d['lo_b']}
    {d['ip_a']} ────────────────── {d['ip_b']}   ({d['link']}.0/30)
```

- 対向のループバックへの到達性は、{d['igp']}によって提供されています。

## 現在の状態

ネイバーの状態に関する事象が、報告されています。調査のために、両方のルータにおいて
`debug ip bgp` が有効にされ、そして、ログが採取されました。

```
{A}# show logging | include BGP:
{chr(10).join(a_lines)}
```
```
{B}# show logging | include BGP:
{chr(10).join(b_lines)}
```
```
{gpb.extra_block(d)}
```

## 設問(記述式)

{chr(10).join(qs)}

---
> 解答は、この問題文の下に追記するか、チャットに記述してください。
> 採点は、示されているところの根拠に基づいて行われます。
"""


def answer_md_bgpdbg(d, stamp, master_seed, subseed):
    rb = gpb.rubric(d)
    items = "\n".join(f"- **{t}**" for t, _p in rb["項目"])
    minus = "\n".join(f"- {x}" for x in rb["減点"])
    v_note = {"addr_mismatch": "両側の neighbor 宛先が食い違う(Lo宛 vs 物理宛)",
              "ebgp_multihop": "eBGP ループバック・ピアで ebgp-multihop 欠落",
              "asym_up": "片側 update-source 欠けだが Established(接続レース)"}[d["variant"]]
    return f"""# 解答・採点ルーブリック {stamp}

## 出題の仕込み

- variant: `{d['variant']}` — {v_note}(難易度 {gpb.DIFF[d['variant']]})
- {d['A']}: Lo0={d['lo_a']} / 物理={d['ip_a']} / AS {d['as_a']}
- {d['B']}: Lo0={d['lo_b']} / 物理={d['ip_b']} / AS {d['as_b']}
- 生成: `gen_paper_mcq.py --shape bgpdbg --seed {master_seed}` (sub-seed {subseed})

## 採点項目(計 {rb['総点']} 点)

{items}

## 減点の観点

{minus}

## 出題素材の根拠(実機 PoC・poc/bgpdbg/README.md)

- `open active, local address <X>` … その機がどの送信元で開きに行ったか
  = **update-source の有無**が両側それぞれについて確定する。
- 行頭のピアアドレス … その機の **neighbor 文の宛先**(ループバック宛か物理宛か)。
- `open failed: Connection refused by remote host` … 相手がその送信元を neighbor として
  **持っていない**(TCP RST)。到達性の障害ではない。
- `Active open failed - no route to peer` … eBGP の**シングルホップ検査**の失敗。
  経路が存在していても出る(字面に釣られると誤診する)。
- ★片側だけ update-source が欠けている場合、**セッションは確立してしまう**
  (update-source を持つ側が開いた接続が受理されるため)。
"""


# --------------------------------------------------------------------------
# shape=v6redist — OSPFv3 ⇄ EIGRPv6 相互再配送 手段選択 (gen_paper_v6redist・BL-098)
# ★紙面専用: 挙動は実機確定表(poc/v6redist/README.md)の写像モデルから決定的に生成。
# --------------------------------------------------------------------------
def pick_draw_v6redist(qseed, kind):
    for kk in range(200):
        s = qseed + kk * 139
        try:
            return s, gpv.verify_choices(gpv.draw(random.Random(s), kind=kind))
        except ValueError:
            continue
    raise SystemExit(f"v6redist kind={kind} が成立する seed が見つかりません({qseed})")


def v6redist_evidence(d, rnd, form):
    """紙面に出すブロック群(状態=経路表/ping・構成=ASBR の running-config)。"""
    st = gpv.state(d)
    state_blocks = []
    if form == "read":
        # 逆引き: 経路表は選択肢側にあるので、症状は ping だけを見せる
        state_blocks.append("```\n" + gpv.trace_block(d, st) + "\n```")
    elif form == "trace":
        # ping の読み分けが設問なので、証拠は経路表のみ
        for n in ("C1", "RB"):
            state_blocks.append(f"```\n{n}# {gpv.table_cmd(n)}\n"
                                + gpv.route_table(d, st, n) + "\n```")
    else:
        for n in ("C1", "RB"):
            state_blocks.append(f"```\n{n}# {gpv.table_cmd(n)}\n"
                                + gpv.route_table(d, st, n) + "\n```")
        state_blocks.append("```\n" + gpv.trace_block(d, st) + "\n```")
    cfg_blocks = [f"```\n{d['m']['ASBR']}# show running-config\n"
                  "Building configuration...\n!\n" + gpv.cfg_block(d, st) + "\n```"]
    return state_blocks, cfg_blocks


def v6redist_requirements(d, rnd):
    core = list(gpv.requirements(d))
    core += rnd.sample([x for x in REQ_DECOYS if "スタティック" not in x], 1)
    head, tail = core[0], core[1:]
    rnd.shuffle(tail)
    return finalize_reqs([head] + tail, rnd)


def build_choices_read_v6(d, rnd):
    """read 形: 観測ノードの経路表そのものを選択肢にする(描画で重複排除)。"""
    node, cur, alts = gpv.read_variants(d)
    pr = f"{node}# {gpv.table_cmd(node)}\n"
    correct_txt = pr + cur
    seen = {correct_txt}
    c = [(correct_txt, True, "")]
    rnd.shuffle(alts)
    for label, tx in alts:
        txt = pr + tx
        if txt in seen:
            continue
        seen.add(txt)
        c.append((txt, False, f"別の状態({label})の観測結果である。"))
        if len(c) == 4:
            break
    if len(c) < 3:
        raise ValueError("v6redist read: 選択肢が畳まれすぎ")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_trace_v6(d, rnd):
    """trace 形(★この盤面固有): ping の 3 値の 組合せを読み分けさせる。"""
    cur, alts = gpv.trace_variants(d)
    seen = {cur}
    c = [(cur, True, "")]
    rnd.shuffle(alts)
    for label, tx in alts:
        if tx in seen:
            continue
        seen.add(tx)
        c.append((tx, False, f"別の状態({label})において観測される結果である。"))
        if len(c) == 4:
            break
    if len(c) < 3:
        raise ValueError("v6redist trace: 選択肢が畳まれすぎ")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def mermaid_v6redist(d):
    """v6redist の構成図。house の流儀に従い**エッジにラベルを描かない**
    (mermaid はラベルを中点固定で置くため箱と衝突する)。アドレスは直下の
    リンク一覧(表)が正典で、図は「どこが繋がっているか」だけを負う。"""
    a = d["m"]["ASBR"]
    lines = ["```mermaid", f"graph {d.get('_mmdir', 'LR')}",
             f'  C1["C1<br/>クライアント<br/>OSPFv3 {d["ospf_pid"]}"]',
             '  RA["RA<br/>中継"]',
             f'  RTC["{a}<br/>ASBR<br/>双方向の再配送"]',
             '  RB["RB<br/>中継"]',
             f'  C2["C2<br/>クライアント<br/>EIGRP AS {d["eigrp_as"]}"]',
             '  C1 ---|"a"| RA',
             '  RA ---|"b"| RTC',
             '  RTC ---|"c"| RB',
             '  RB ---|"d"| C2',
             "```"]
    return "\n".join(lines)


def topo_tables_v6redist(d):
    """Mermaid 非対応プレビューでも解ける正典のテキスト表現(表＋リンク一覧)。"""
    a = d["m"]["ASBR"]
    rows = [
        f"| C1 | クライアント | OSPFv3 {d['ospf_pid']} area 0 |",
        f"| RA | 中継 | OSPFv3 {d['ospf_pid']} area 0 |",
        f"| {a} | **ASBR(2 つの ドメイン の 境界)** | 双方向の 再配送 |",
        f"| RB | 中継 | EIGRP {d['eigrp_name']} AS {d['eigrp_as']} |",
        f"| C2 | クライアント | EIGRP {d['eigrp_name']} AS {d['eigrp_as']} |",
    ]
    head = ("| ルータ | 位置づけ | 参加プロトコル |\n"
            "|--------|----------|----------------|\n")
    raw = [
        ("(a)", "C1:Et0/0", "RA:Et0/1", d["c1lan"], f"C1 = {d['c1lan']}2"),
        ("(b)", "RA:Et0/0", f"{a}:{d['oif']}", d["otran"], ""),
        ("(c)", f"{a}:{d['eif']}", "RB:Et0/0", d["etran"], ""),
        ("(d)", "RB:Et0/1", "C2:Et0/0", d["c2lan"], f"C2 = {d['c2lan']}2"),
    ]
    wl = max(len(x[1]) for x in raw)
    wr = max(len(x[2]) for x in raw)
    wp = max(len(x[3]) + 3 for x in raw)
    edges = [f"  {tag} {lhs:<{wl}} ── {rhs:<{wr}}   "
             f"{pfx + '/64':<{wp}}{('   ' + note) if note else ''}".rstrip()
             for tag, lhs, rhs, pfx, note in raw]
    return (head + "\n".join(rows)
            + "\n\nリンク一覧:\n```\n" + "\n".join(edges) + "\n```\n"
            + f"\nOSPFv3 の ドメイン には、RA によって注入されたところの"
              f" 外部の ルート `{d['ext']}/64` が存在する。")


V6R_INTRO = (
    # ★先頭に「あなたの組織は…運用しています」を置かない: obfuscate_md が
    #   LEAD_IN を前置するため、同一文が二重になることがある。
    "クライアントである C1 は OSPFv3 の ドメイン に、そして、C2 は EIGRP の"
    " ドメイン に、それぞれ収容されています。{asbr} は、2 つの ドメイン の"
    "境界に位置しており、双方向の 再配送 が構成されています。")


def question_md_v6redist(d, blocks, choices, stamp, form="fix", reqs=None,
                         style="prose"):
    asbr = d["m"]["ASBR"]
    state_blocks, cfg_blocks = blocks
    if reqs is None:
        reqs = v6redist_requirements(d, random.Random(0))
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
        opts = render_options(choices, "prose")
    elif form in ("read", "trace"):
        q = (("示されているところの構成に基づいて、観測されるところの出力は、"
              "どれですか。(1つを選択してください)"))
        letters = [chr(65 + i) for i in range(len(choices))]
        opts = "\n".join(f"**{l}.**\n```\n{c[0]}\n```"
                         for l, c in zip(letters, choices))
    elif style == "cli":
        q = ("示されているところのすべての要件が満たされることを確実にするために、"
             "適用されなければならない構成は、どれですか。(1つを選択してください)")
        opts = render_options(choices, style)
    else:
        q = ("この問題を解決し、そして、示されているところのすべての要件が"
             "満たされることを確実にするために、必要とされる手順は、どれですか。"
             "(1つを選択してください)")
        opts = render_options(choices, style)
    if form in ("read", "trace"):
        sympt = "構成の変更の適用後の、観測の結果が、確認されようとしています。"
    else:
        sympt = ("C1 と C2 の 間の 通信 が成立しない、ということが、"
                 "報告されています。示されているところの出力および構成に基づいて、"
                 "要求されているところの動作が得られていない理由が、"
                 "判断されなければなりません。")
    return f"""# 問題 {stamp} : IPv6 の 相互 再配送 の 分析

{FIXED_NOTE}

## トポロジ

{terse_jp(V6R_INTRO.format(asbr=asbr))}

{messy_mermaid(mermaid_v6redist(d))}

{topo_tables_v6redist(d)}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{terse_jp(sympt)}

{chr(10).join(state_blocks)}

## 設定抜粋

{chr(10).join(cfg_blocks)}

## 設問

{q}

## 選択肢

{opts}
"""


def answer_md_v6redist(d, choices, stamp, master_seed, subseed, form):
    letters = [chr(65 + i) for i in range(len(choices))]
    correct = [l for l, c in zip(letters, choices) if c[1]][0]
    wrongs = "\n".join(f"- **{l}**: {'(正解)' if c[1] else c[2]}"
                       for l, c in zip(letters, choices))
    kind_note = {
        "pl_transit_only": "双方の prefix-list が隣接リンクのみを許可 "
                           "→ ★include-connected が拾ったトランジットだけが渡る"
                           "(ユーザ手組みラボの原型)",
        "pl_one_side": "片方向の prefix-list のみ客先 LAN を許可 → "
                       "★NOROUTE と タイムアウト の非対称が出る",
        "rm_typo": "redistribute の参照 route-map がタイポで未定義 → "
                   "★全拒否(全許可ではない・実測)",
        "no_metric": "EIGRP 側 redistribute の metric 欠落 → "
                     "★広告ゼロ(named mode でも必要・実測)",
        "no_incl": "include-connected 欠落 → 両ドメインとも受信ゼロ(実測 E4)",
        "rm_deny_first": "route-map の先頭 deny が客先 LAN を先取り(seq 影)",
    }[d["kind"]]
    world_note = {
        "hide_transit": "トランジット秘匿 → prefix-list の**置換**が唯一適合"
                        "(★include-connected 由来の経路も route-map に従う・実測 E3)",
        "filter_frozen": "フィルタ凍結＋RT-C 以外変更禁止 → "
                         "default-information originate always + EIGRP ::/0 集約",
        "detail_static": "フィルタ凍結＋IGP でのデフォルト生成禁止 → "
                         "静的 + クライアント既定 GW(★中継だけでは伝播しない・実測 E13)",
        "default_only": "明細を持たない → デフォルト配布のみが適合(実測 E12)",
        "explicit_only": "明示許可のみ＋トランジット維持＋静的/デフォルト禁止 → "
                         "prefix-list への**追記**",
        "internal_ad": "トランジットを内部(AD90)で受ける → "
                       "af-interface の shutdown 解除(実測 E9)",
        "e1_type": "タイプ 1 の外部経路 → metric-type 1"
                   "(★E1 はコストが経路上で累積・実測 E15)",
        "pass_external": "OSPF 外部も渡す → match internal external"
                         "(★match internal は外部を落とす・実測 E10)",
    }[d["world"]]
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 仕込んだ状態

- 種別: `v6redist/{d['kind']}` — {kind_note}
- 要件世界: `{d['world']}` — {world_note}
- 出題形: {form}(機能的に「直る候補」= {', '.join(d['_works'])})
- 生成: `gen_paper_mcq.py --shape v6redist --seed {master_seed}` (sub-seed {subseed})

## 各選択肢の判定

{wrongs}

## 検証コマンドと期待される出力

- `C1# show ipv6 route ospf` に {d['c2lan']}/64(または `::/0`)が存在すること。
- `C2# show ipv6 route eigrp` に {d['c1lan']}/64(または `::/0`)が存在すること。
- `C1# ping {d['c2lan']}2` および `C2# ping {d['c1lan']}2` が、いずれも成功すること。

## ★この分野の最重要知見(BL-098 PoC 実測・poc/v6redist/README.md)

**この盤面の核心**: 再配送は両方向とも「動いて」おり、経路も 1 本ずつ渡っている。
だが渡っているのは `include-connected` が拾った **ASBR 自身の足元のリンク**だけで、
本来届けたい**客先 LAN は prefix-list に落ちている**。`show ipv6 protocols` には
両方向の Redistribution 行が正常に出るため、**壊れているように見えない**。

実測で確定した 4 つの非対称:

1. **外したつもりが外れていない** — `redistribute` は**再発行でマージ**され、
   `route-map` 節を省いて打ち直しても route-map は外れない。外すには
   `no redistribute <proto> <id>` の前置が必須(`metric` / `match` も同様)。
2. **器が無い=全拒否 / 中身が空振り=全許可** — route-map ごと未定義なら何も
   再配送されず、route-map は在って参照 prefix-list が未定義なら全部通る。
   BL-095(EIGRP leak-map)の非対称と**完全に同型**。
3. **片方向だけ修理の指紋** — 未修理側からの ping は `% No valid route`、
   修理済み側からは `..`。★`source` を指定すると `% No valid route` が
   `..` に化けて、経路欠落の証拠が消える。
4. **広告と到達は別** — 中継(RA/RB)だけに静的を置いてもクライアントには
   伝播しない。「静的ルートを設定する」は置き場所を誤ると半正解にしかならない。

その他: EIGRP 側は metric 省略で広告ゼロ(`default-metric` で救済可)/
`default-information originate` は `always` 必須(→ `OE2 [110/1]`)/
EIGRP の `summary-address ::/0` は more-specific を全抑止し ASBR 自身に
**AD 5 の Null0** を作る(上流を持たない構成ではブラックホール)。

## ENARSI ブループリント

- 1.0 Layer 3 Technologies — Configure and verify redistribution between any routing protocols
- 1.0 Layer 3 Technologies — Configure and verify routing protocol authentication / filtering (route-map, prefix-list)
"""


# --------------------------------------------------------------------------
# shape=aaa — IOS AAA(RADIUS) の読解 (gen_paper_aaa・BL-101 P1a)
# ★紙面専用: 挙動は実機確定表(poc/aaa/README.md)の写像である aaa_model.py から生成。
# ★P1a の形は read / cause / trace / evidence(fix・patch は P1b)。
# --------------------------------------------------------------------------
def pick_draw_aaa(qseed, kind):
    for kk in range(200):
        s = qseed + kk * 149
        try:
            return s, gpa.verify_choices(gpa.draw(random.Random(s), kind=kind))
        except ValueError:
            continue
    raise SystemExit(f"aaa kind={kind} が成立する seed が見つかりません({qseed})")


def aaa_evidence_blocks(d, rnd, form):
    """紙面に出すブロック群。

    ★evidence 形だけは**機器の構成を出さない**。構成を見せてしまうと
    「次に何を見るか」が自明になり、設問が成立しないため(症状とサーバ仕様のみ提示)。
    """
    state, cfg = [], []
    if form == "read":
        # 結果表そのものが選択肢なので、症状側は test aaa だけ見せる
        state.append("```\n" + gpa.trace_block(d) + "\n```")
    elif form == "trace":
        state.append(gpa.render_obs(d))
    elif form == "evidence":
        state.append(gpa.render_obs(d))
        state.append("```\n" + gpa.trace_block(d) + "\n```")
    elif form == "patch":
        # ★移行途中の構成のみを見せる(症状はまだ起きていないので出さない)
        for site in ("A", "B"):
            cfg.append(f"```\n{d['rt'][site]}# show running-config | section aaa\n"
                       + gpa.patch_state_block(d, site) + "\n```")
        return state, cfg
    elif form == "authread":
        # ★enable の debug と、enable 認証まわりの構成だけを見せる。
        #   ログイン層の観測は関係しない(遍歴が出るのは service=ENABLE だけ)。
        site = "B" if d["scope"] == "B" else "A"
        a = d["_auth"]
        state.append(f"```\n{d['rt'][site]}# debug aaa authentication\n"
                     + gpa.enable_debug_block(d, site, pw_ok=a["pw_ok"],
                                              with_list=a["with_list"],
                                              on_console=a["on_console"])
                     + "\n```")
        cfg.append(f"```\n{d['rt'][site]}# show running-config | section aaa\n"
                   + gpa.enable_cfg_block(d, site, with_list=a["with_list"])
                   + "\n```")
        return state, cfg
    elif form in ("dbgread", "dbgconf"):
        # ★debug から構成を読ませる形。症状も構成も出さない
        #   (dbgconf は構成そのものが選択肢なので、なおさら出せない)
        site = "B" if d["scope"] == "B" else "A"
        state.append(f"```\n{d['rt'][site]}# debug radius authentication\n"
                     + gpa.debug_block(d, site) + "\n```")
    else:                                   # cause
        state.append(gpa.render_obs(d))
        state.append("```\n" + gpa.trace_block(d) + "\n```")
    if form not in ("evidence", "dbgread", "dbgconf", "patch"):
        # ★両拠点の構成を出す。片方だけだと「他拠点は健全」という前提が
        #   問題文のどこにも無く、結果表を一意に決められない(出題前検分で検出)。
        for site in ("A", "B"):
            cfg.append(f"```\n{d['rt'][site]}# show running-config | section aaa\n"
                       + gpa.cfg_block(d, site) + "\n```")
    return state, cfg


def aaa_requirements(d, rnd, form=None):
    core = list(gpa.requirements(d, form))
    head, tail = core[0], core[1:]
    rnd.shuffle(tail)
    return finalize_reqs([head] + tail, rnd)


def build_choices_read_aaa(d, rnd):
    """read 形: 「誰がどこから入れるか」の結果表そのものを選択肢にする。"""
    cur, alts = gpa.read_variants(d)
    seen = {cur}
    c = [(cur, True, "")]
    rnd.shuffle(alts)
    for label, tx in alts:
        if tx in seen:
            continue
        seen.add(tx)
        c.append((tx, False, f"別の状態({label})において観測される結果である。"))
        if len(c) == 4:
            break
    if len(c) < 3:
        raise ValueError("aaa read: 選択肢が畳まれすぎ")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_trace_aaa(d, rnd):
    """trace 形: `test aaa` の文言と所要時間の組合せを読み分けさせる。"""
    cur, alts = gpa.trace_variants(d)
    seen = {cur}
    c = [(cur, True, "")]
    rnd.shuffle(alts)
    for label, tx in alts:
        if tx in seen:
            continue
        seen.add(tx)
        c.append((tx, False, f"別の状態({label})において観測される結果である。"))
        if len(c) == 4:
            break
    if len(c) < 3:
        raise ValueError("aaa trace: 選択肢が畳まれすぎ")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


AAA_INTRO = ("2 つの拠点のルータが、共通の認証サーバ群を用いて、"
             "管理者の認証を行うように構成されています。"
             "一方のルータはサーバと直結しており、"
             "他方はそのルータを経由してサーバに到達します。")


def mermaid_aaa(d):
    a, b = d["rt"]["A"], d["rt"]["B"]
    return "\n".join([
        "```mermaid", f"graph {d.get('_mmdir', 'LR')}",
        '  S1["SRV01<br/>認証サーバ"]', '  S2["SRV02<br/>認証サーバ"]',
        f'  A["{a}"]', f'  B["{b}"]',
        '  S1 ---|"a"| A', '  S2 ---|"b"| A', '  A ---|"c"| B',
        "```",
    ])


def question_md_aaa(d, blocks, choices, stamp, form="read", reqs=None):
    state_blocks, cfg_blocks = blocks
    if reqs is None:
        reqs = aaa_requirements(d, random.Random(0), form)
    if form == "cause":
        q = ("この事象の原因である可能性が、最も高いものは、どれですか。"
             "(1つを選択してください)")
        opts = render_options(choices, "prose")
    elif form == "patch":
        q = ("現在の接続が失われることなく、移行を進めるために、次に適用されなければ"
             "ならない構成は、どれですか。(1つを選択してください)")
        opts = render_options(choices, "cli")
    elif form == "fix":
        q = ("示されているところのすべての要件が満たされることを確実にするために、"
             "適用されなければならない構成は、どれですか。(1つを選択してください)")
        opts = render_options(choices, "cli")
    elif form == "dbgread":
        q = ("示されているところの出力から読み取ることができる構成は、どれですか。"
             "(1つを選択してください)")
        opts = render_options(choices, "prose")
    elif form == "authread":
        q = ("示されているところの出力について、正しい記述は、どれですか。"
             "(2つを選択してください)")
        opts = render_options(choices, "prose")
    elif form == "dbgconf":
        q = ("示されているところの出力を生じさせる構成は、どれですか。"
             "(1つを選択してください)")
        letters = [chr(65 + i) for i in range(len(choices))]
        opts = "\n".join(f"**{l}.**\n```\n{c[0]}\n```"
                         for l, c in zip(letters, choices))
    elif form == "evidence":
        nh = len(gpa.evidence_variants(d)[0])
        q = (("想定されているところの原因の、いずれであるかを、判断するために、"
              "**最も多くの候補を除外できる**出力は、どれですか。"
              "(1つを選択してください)") if nh > 2 else
             ("2 つの原因の、いずれであるかを、判断するために、"
              "次に取得されなければならない出力は、どれですか。"
              "(1つを選択してください)"))
        opts = render_options(choices, "prose")
    else:
        q = ("示されているところの構成に基づいて、観測されるところの結果は、"
             "どれですか。(1つを選択してください)")
        letters = [chr(65 + i) for i in range(len(choices))]
        opts = "\n".join(f"**{l}.**\n```\n{c[0]}\n```"
                         for l, c in zip(letters, choices))
    if form == "patch":
        sympt = ("ローカルの認証から、認証サーバ群を用いる認証への移行が、"
                 "実施されようとしています。作業は、遠隔からの接続によって"
                 "行われています。")
    elif form == "fix":
        sympt = ("一部の利用者が、意図されたとおりに機器を操作できない、"
                 "ということが、報告されています。")
    elif form == "authread":
        sympt = ("特権レベルへの昇格が試行された際の、デバッグの出力が、"
                 "採取されました。")
    elif form in ("dbgread", "dbgconf"):
        sympt = ("認証の動作を確認するために、デバッグの出力が、採取されました。")
    elif form == "evidence":
        hyps = gpa.evidence_variants(d)[0]
        # ★正解が先頭に来ないよう、仮説の提示順は seed で並べ替える
        # ★hash() はプロセスごとに塩が変わり決定性を壊す(監査1) → crc32 で安定化
        shown = sorted(hyps, key=lambda k: zlib.crc32(f"{d['kind']}/{k}".encode()))
        joined = " と ".join(f"**{gpa.CLAIMS[k]}**" for k in shown)
        sympt = ("利用者の認証が、意図されたとおりに行われていない、ということが、"
                 f"報告されています。原因として、{joined} の {len(shown)} つが、"
                 "想定されています。機器の構成は、まだ取得されていません。")
    elif form in ("read", "trace"):
        sympt = "構成の適用後の、観測の結果が、確認されようとしています。"
    else:
        sympt = ("一部の利用者が、機器にログインできない、ということが、"
                 "報告されています。示されているところの出力および構成に基づいて、"
                 "要求されているところの動作が得られていない理由が、"
                 "判断されなければなりません。")
    cfg_sec = ("\n## 設定抜粋\n\n" + chr(10).join(cfg_blocks)) if cfg_blocks else ""
    return f"""# 問題 {stamp} : 認証 の 分析

{FIXED_NOTE}

## トポロジ

{terse_jp(AAA_INTRO)}

{messy_mermaid(mermaid_aaa(d))}

### 認証サーバの仕様

{gpa.server_spec(d)}

### ルータのアドレス

{gpa.addr_table(d)}

## 要件

{chr(10).join(reqs)}

## 現在の状態

{terse_jp(sympt)}

{chr(10).join(state_blocks)}
{cfg_sec}

## 設問

{q}

## 選択肢

{opts}
"""


def answer_md_aaa(d, choices, stamp, master_seed, subseed, form):
    letters = [chr(65 + i) for i in range(len(choices))]
    # ★複数正解(authread は 2 つ選択)に対応。単一正解のときは従来どおり 1 文字。
    hits = [l for l, c in zip(letters, choices) if c[1]]
    correct = "・".join(hits)
    why = "\n".join(f"- **{l}**: {c[2]}" for l, c in zip(letters, choices) if c[2])
    return f"""# 解答 {stamp}

## 正解

**{correct}**

## 解説

- 種別: `aaa/{d['kind']}` — 要件世界 `{d['world']}` / 故障拠点 `{d['scope']}`
- 形式: `{form}`
- 生成: `gen_paper_mcq.py --shape aaa --seed {master_seed}` (sub-seed {subseed})

{why}

## ★この分野の最重要知見(BL-101 PoC 実測・poc/aaa/README.md)

**拒否(Reject)と無応答(timeout)は、まったく別のものである。**

- `group <G> local` の `local` は、**サーバが応答しないときにだけ**使われる。
  サーバが**拒否を返した場合は、後段の手段へは進まない**。
  local に登録されている利用者であっても、サーバが拒否すればログインできない。
- この原則は **認証・認可・特権昇格の 3 層すべて**で成立する。
  昇格を `group <G> enable` とした場合も、サーバに `$enab15$` が無ければ拒否となり、
  enable secret へは落ちない。
- **権限レベルは認可が与える。** 認可の方式リストが無ければ、
  `username X privilege 15` の利用者であっても権限レベルは 1 になる。
- 応答が無い場合の待ち時間は
  `timeout × (retransmit + 1) × 到達できないサーバ数` で決まる。
- **共有鍵の不一致と、送信元アドレスの誤りは、`test aaa` と `show aaa servers`
  では区別できない。** いずれも `No authoritative response from any server.` となり、
  所要時間も同じになる。**区別できるのは `debug radius authentication` である。**
  鍵の不一致では応答が届いており `Response (n) failed decrypt` が出る。
  送信元の誤りでは `cfg_addr=0.0.0.0` と
  `RADIUS/ENCODE: Best Local IP-Address ...` が出て、要求の送信元が
  意図した Loopback ではないことが読み取れる。
- **未定義の方式リストを参照した回線は、既定の方式リストで動作する。**
  そのため「リストを適用し忘れた場合」と「未定義のリストを参照した場合」は、
  症状がまったく同じになる。

## ENARSI ブループリント

- 3.0 Infrastructure Security — Troubleshoot device security using IOS AAA (TACACS+, RADIUS, local database)
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


def deploy_and_collect(repo, prob_id, d, plan, boot_wait, settle, tries=8,
                       nodes=None):
    """provision → ブート待ち → 収束待ち → 本収集。teardown は呼び元 finally で。
    nodes: 生存確認をかけるノード名の明示指定(shape=mploop のように d が
    roles/m を持たない盤面用)。省略時は d["roles"]/d["m"] から導く。"""
    sh(repo, [f"{repo}/scripts/lab.sh", "provision", prob_id])
    print(f"  boot 待ち {boot_wait}s ...", flush=True)
    time.sleep(boot_wait)
    node_names = nodes if nodes else [d["m"][r] for r in d["roles"]]
    probe = [{"node": n, "command": "show ip protocols | include Routing Protocol"}
             for n in node_names]
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
    if not choices:
        return choices
    files = sorted(glob.glob(f"{repo}/answers/*.md"))[-2:]
    recent = []
    for fp in files:
        # ★複数正解(`**B・C**`)も拾えるようにする。拾えないと直近2問の窓が
        #   欠けて 3 連続防止が効かなくなる(監査指摘)。判定には先頭の記号を使う。
        mt = re.search(r"## 正解\n\n\*\*([A-H])(?:・[A-H])*\*\*",
                       open(fp, encoding="utf-8").read())
        if mt:
            recent.append(mt.group(1))
    hits = [i for i, c in enumerate(choices) if c[1]]
    if len(hits) != 1:
        return choices          # ★複数正解の形(authread)では回転しない
    cur = "ABCDEFGH"[hits[0]]
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
    ap.add_argument("--shape",
                    choices=["chain", "ring", "pbr", "urpf", "bgpdbg", "mploop",
                             "leakmap", "ospfv3pl", "v6redist", "aaa", "acl",
                             "aclv6", "mixed"],
                    default="chain",
                    help="chain=再配送欠落/誤設定系(既定) / ring=再配送リングの定常ループ(難5)"
                         " / pbr=PBR×ワイルドカードACL(BL-081)"
                         " / urpf=uRPF×ACL(BL-084・紙面専用)"
                         " / bgpdbg=BGP debug読解(BL-085・★記述式)"
                         " / mploop=多点相互再配送の同AD・メトリック差ループ(難5)"
                         " / leakmap=EIGRP集約×リーク手段選択(BL-095・紙面専用)"
                         " / ospfv3pl=OSPFv3エリア間prefix-list(BL-097・紙面専用)"
                         " / v6redist=OSPFv3⇄EIGRPv6相互再配送の手段選択"
                         "(BL-098・紙面専用)"
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
                "urpf": gpu.URPF_KINDS, "mploop": MPLOOP_KINDS,
                "bgpdbg": gpb.VARIANTS, "leakmap": gpk.KINDS,
                "ospfv3pl": gpo.KINDS, "v6redist": gpv.KINDS,
                "aaa": gpa.KINDS, "acl": gpl.KINDS,
                "aclv6": gp6.KINDS}.get(a.shape, KINDS)
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
            # ★配分(2026-08-10 acl 追加時に再調整)= どの shape も概ね 8〜12% に均す。
            #   acl の枠は**再配送系(chain/ring/mploop)を薄める**ことで作った
            #   (BL-100 の突合せで「再配送だけが飽和」と出ているため)。
            shape_i = ("ring" if r < 0.12 else "pbr" if r < 0.23
                       else "urpf" if r < 0.34 else "mploop" if r < 0.43
                       else "leakmap" if r < 0.54 else "ospfv3pl" if r < 0.65
                       else "v6redist" if r < 0.74
                       else "aaa" if r < 0.83
                       else "acl" if r < 0.88
                       else "aclv6" if r < 0.94 else "chain")
            kind = roll.choice({"ring": RING_KINDS, "pbr": gpp.PBR_KINDS,
                                "urpf": gpu.URPF_KINDS, "mploop": MPLOOP_KINDS,
                                "leakmap": gpk.KINDS, "ospfv3pl": gpo.KINDS,
                                "v6redist": gpv.KINDS,
                                "aaa": gpa.KINDS,
                                "acl": gpl.KINDS,
                                "aclv6": gp6.KINDS}.get(shape_i, KINDS))
        else:
            shape_i = a.shape
            kind = kinds[i % len(kinds)]
        if shape_i == "mploop":
            subseed = qseed
            mp_rnd = random.Random(subseed)
            d = gmp.rand_values(mp_rnd)
            d["_mmdir"] = mp_rnd.choice(["LR", "TD", "RL"])
            mp_names = mploop_names(mp_rnd)
        elif shape_i == "ring":
            subseed = qseed
            # ★tag 解は ring=inject_ospf に限定する(BL-086)。
            #   inject_eigrp では出自が一周する箇所が RA の EIGRP→OSPF 再配送であり、
            #   そこを tag で落とすと OSPF ドメイン(RB＋ノイズ葉)が当該網への経路を
            #   丸ごと失う=到達性要件を破る。inject_ospf なら一周箇所は
            #   RA の OSPF→EIGRP で、EIGRP 側の構成員は RC/RA のみのため副作用が無い。
            d = gra.draw(random.Random(subseed), method=kind,
                         ring=("inject_ospf" if kind == "tag" else None))
        elif shape_i == "pbr":
            subseed, d = pick_draw_pbr(qseed, kind)
        elif shape_i == "urpf":
            subseed, d = pick_draw_urpf(qseed, kind)
        elif shape_i == "leakmap":
            subseed, d = pick_draw_leakmap(qseed, kind)
        elif shape_i == "ospfv3pl":
            subseed, d = pick_draw_ospfv3pl(qseed, kind)
        elif shape_i == "v6redist":
            subseed, d = pick_draw_v6redist(qseed, kind)
        elif shape_i == "aaa":
            subseed, d = pick_draw_aaa(qseed, kind)
        elif shape_i == "acl":
            subseed, d = pick_draw_acl(qseed, kind)
        elif shape_i == "aclv6":
            subseed, d = pick_draw_aclv6(qseed, kind)
        elif shape_i == "bgpdbg":
            subseed = qseed
            d = gpb.draw(random.Random(subseed), variant=kind)
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
        if shape_i == "mploop":
            plan = evidence_plan_mploop(d, mp_names, rnd)
            choices = build_choices_mploop(d, mp_names, kind, rnd, exam=a.exam)
        elif shape_i == "ring":
            plan = evidence_plan_ring(d, rnd, exam=a.exam)
            choices = build_choices_ring(d, rnd, exam=a.exam)
        elif shape_i == "pbr":
            plan = gpp.evidence_plan(d, rnd)
            choices = gpp.build_choices_fix(d, rnd)
        elif shape_i == "urpf":
            plan = {"checks": []}          # 紙面専用(実機展開なし)
            choices = gpu.build_choices_fix(d, rnd)
        elif shape_i == "leakmap":
            plan = {"checks": []}          # 紙面専用(実機確定表の写像モデル)
            choices = gpk.build_choices_fix(d, rnd)
        elif shape_i == "ospfv3pl":
            plan = {"checks": []}          # 紙面専用(実機確定表の写像モデル)
            choices = gpo.build_choices_fix(d, rnd)
        elif shape_i == "v6redist":
            plan = {"checks": []}          # 紙面専用(実機確定表の写像モデル)
            choices = gpv.build_choices_fix(d, rnd)
        elif shape_i == "aaa":
            plan = {"checks": []}          # 紙面専用(実機確定表の写像モデル)
            choices = build_choices_read_aaa(d, rnd)   # 既定形= read
        elif shape_i == "acl":
            plan = {"checks": []}          # 紙面専用(実機確定表の写像モデル)
            choices = gpl.build_choices_cause(d, rnd)  # 既定形= cause(全 kind で成立)
        elif shape_i == "aclv6":
            plan = {"checks": []}          # 紙面専用(実機確定表の写像モデル)
            choices = gp6.build_choices_cause(d, rnd)
        elif shape_i == "bgpdbg":
            plan = {"checks": []}          # 紙面専用・記述式(選択肢なし)
            choices = []
        else:
            plan = evidence_plan(d, rnd, hard=a.hard, exam=a.exam)
            choices = build_choices(d, rnd, plan=plan, exam=a.exam, pol=pol)
        if a.exam and shape_i == "mploop":
            sites = dict(zip(gmp.NODES, rnd.sample(SITE_POOL, len(gmp.NODES))))
        else:
            sites = (assign_sites(d, rnd)
                     if (a.exam and shape_i not in ("bgpdbg", "leakmap",
                                                    "ospfv3pl", "v6redist",
                                                    "aaa", "acl", "aclv6"))
                     else None)
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
        elif a.exam and shape_i == "ring" and rnd.random() < 0.5:
            form = "cause"
            choices = build_cause_choices_ring(d, rnd, exam=a.exam)
        elif a.exam and shape_i == "mploop" and rnd.random() < 0.5:
            form = "cause"
            choices = build_cause_choices_mploop(d, mp_names, rnd, exam=a.exam)
        elif a.exam and shape_i == "pbr" and rnd.random() < 0.5:
            form = "cause"
            choices = gpp.build_choices_cause(d, rnd)
        elif a.exam and shape_i == "urpf" and rnd.random() < 0.5:
            form = "cause"
            choices = gpu.build_choices_cause(d, rnd)
        elif a.exam and shape_i == "leakmap":
            r_form = rnd.random()          # fix / cause / read の3形を抽選
            if r_form < 0.34:
                form = "cause"
                choices = gpk.build_choices_cause(d, rnd)
            elif r_form < 0.62:
                form = "read"
                choices = build_choices_read(d, rnd)
        elif a.exam and shape_i == "ospfv3pl":
            r_form = rnd.random()
            if d["world"] == "dual_select" and d["kind"] != "none" \
                    and r_form < 0.5:
                form = "patch"             # ★両掛けTS(最小修正の切り分け)
                choices = gpo.build_choices_patch(d, rnd)
            elif r_form < 0.45 or (d["world"] == "dual_select"
                                   and d["kind"] != "none" and r_form < 0.8):
                try:                       # 表が畳まれる盤面は fix に戻す
                    choices = build_choices_read_o3pl(d, rnd)
                    form = "read"
                except ValueError:
                    pass
        elif a.exam and shape_i == "v6redist":
            r_form = rnd.random()      # fix / cause / read / trace の4形を抽選
            if r_form < 0.25:
                form = "cause"
                choices = gpv.build_choices_cause(d, rnd)
            elif r_form < 0.42:
                try:                       # 表が畳まれる盤面は fix に戻す
                    choices = build_choices_read_v6(d, rnd)
                    form = "read"
                except ValueError:
                    pass
            elif r_form < 0.57:
                try:                   # ★trace=ping の3値の読み分け(本 shape 固有)
                    choices = build_choices_trace_v6(d, rnd)
                    form = "trace"
                except ValueError:
                    pass
        elif a.exam and shape_i == "aclv6":
            avail = gp6.forms_for(d)
            form = rnd.choice(avail)
            if form == "select":
                choices = gp6.build_choices_select(d, rnd)
            elif form == "counter":
                choices = gp6.build_choices_counter(d, rnd)
            elif form == "read":
                want = 2 if rnd.random() < 0.3 else 1
                try:
                    choices = gp6.build_choices_read(d, rnd, want=want)
                except ValueError:
                    form = "cause"
                    choices = gp6.build_choices_cause(d, rnd)
        elif a.exam and shape_i == "acl":
            # ★成立する形だけから選ぶ(gen_paper_acl.forms_for)。
            #   フィルタが実質不在になる故障種は「全部素通り」が正解なので
            #   read 形が成立しない(対比が作れない)。
            avail = gpl.forms_for(d)
            form = rnd.choice(avail)
            if form == "select":
                choices = gpl.build_choices_select(d, rnd)
            elif form == "counter":
                choices = gpl.build_choices_counter(d, rnd)
            elif form == "patch":
                choices = gpl.build_choices_patch(d, rnd)
            elif form == "fix":
                choices = gpl.build_choices_fix(d, rnd)
            elif form == "evidence":
                choices = gpl.build_choices_evidence(d, rnd)
            elif form == "logread":
                choices = gpl.build_choices_logread(d, rnd, want=2)
            elif form == "read":
                want = 2 if rnd.random() < 0.35 else 1   # ★複数選択(2つ選べ)
                try:
                    choices = gpl.build_choices_read(d, rnd, want=want)
                except ValueError:
                    try:
                        choices = gpl.build_choices_read(d, rnd, want=1)
                    except ValueError:
                        form = "cause"
                        choices = gpl.build_choices_cause(d, rnd)
        elif a.exam and shape_i == "aaa":
            # read / cause / trace / evidence / dbgread / dbgconf / fix / patch
            r_form = rnd.random()
            form = "read"
            if r_form < 0.22:
                form = "cause"
                choices = gpa.build_choices_cause(d, rnd)
            elif r_form < 0.42:
                try:
                    choices = build_choices_trace_aaa(d, rnd)
                    form = "trace"
                except ValueError:
                    pass
            elif r_form < 0.58:
                try:                    # ★evidence=「次に何を見るか」(本 shape の目玉)
                    choices = gpa.build_choices_evidence(d, rnd)
                    form = "evidence"
                except ValueError:
                    pass
            elif r_form < 0.68:
                try:                    # ★dbgread= debug から構成値を推測(ユーザ要望)
                    choices = gpa.build_choices_dbgread(d, rnd)
                    form = "dbgread"
                except ValueError:
                    pass
            elif r_form < 0.74:
                try:                    # ★dbgconf= 逆問題「この出力を生む構成はどれか」
                    choices = gpa.build_choices_dbgconf(d, rnd)
                    form = "dbgconf"
                except ValueError:
                    pass
            elif r_form < 0.84:
                # ★authread= enable の方式リスト遍歴を読む(複数選択・BL-103 ⑥)。
                #   到達可否は盤面の稼働状態から決まるので、リスト有りの枝では
                #   全断を抽選して ERROR→ENABLE の遍歴も出せるようにする。
                # ★`console × 方式リスト有り` は実測が無い(監査指摘)。
                #   コンソールは方式リスト無しの枝に限る。
                _wl = rnd.random() < 0.6
                d["_auth"] = {"with_list": _wl, "pw_ok": rnd.random() < 0.5,
                              "on_console": (not _wl) and rnd.random() < 0.4}
                if d["_auth"]["with_list"] and rnd.random() < 0.5:
                    d["all_down"] = True
                try:
                    choices = gpa.build_choices_authread(d, rnd)
                    form = "authread"
                except ValueError:
                    d.pop("all_down", None)
            elif r_form < 0.92:
                w = gpa.fix_world(d)    # ★P1b fix= 是正手段(成立する世界を選び直す)
                if w:
                    d["world"] = w
                    choices = gpa.build_choices_fix(d, rnd)
                    form = "fix"
            else:
                try:                    # ★P1b patch= 切らずに移行する順序
                    choices = gpa.build_choices_patch(d, rnd)
                    d["world"] = "no_lockout"
                    form = "patch"
                except ValueError:
                    pass
        if choices:
            choices = rebalance_position(repo, choices)
        opt_style = choice_style(rnd, choices, form) if choices else "prose"
        if shape_i == "aclv6" and form == "select":
            opt_style = "cli"          # ★プレフィックス長が読めるようそのまま出す
        if shape_i == "acl" and form == "patch":
            opt_style = "cli"          # ★挿入位置が本題なのでコマンドのまま出す
        if shape_i == "acl" and form == "select":
            # ★select は「ACL の行そのもの」を選ばせる形。散文に均すと
            #   ワイルドカードが読めなくなるので常にコマンドのまま提示する。
            opt_style = "cli"
        if shape_i == "v6redist" and form == "fix":
            # ★v6redist の fix は常に CLI 提示にする。手段の散文表現では
            # 「参照やメトリックの是正も含むのか」が曖昧になり、提示と
            # 要件適合の判定がずれるため(CLI は状態収束形で完全に explicit)。
            opt_style = "cli"
        reqs = None
        if a.exam and shape_i != "bgpdbg":
            if shape_i == "mploop":
                reqs = mploop_requirements(d, mp_names, kind, rnd, form=form)
            elif shape_i == "ring":
                reqs = ring_requirements(d, rnd, form=form)
            elif shape_i == "pbr":
                reqs = pbr_requirements(d, rnd, sites)
            elif shape_i == "urpf":
                reqs = urpf_requirements(d, rnd, sites)
            elif shape_i == "leakmap":
                reqs = leakmap_requirements(d, rnd)
            elif shape_i == "ospfv3pl":
                reqs = ospfv3pl_requirements(d, rnd)
            elif shape_i == "v6redist":
                reqs = v6redist_requirements(d, rnd)
            elif shape_i == "aaa":
                reqs = aaa_requirements(d, rnd, form)
            elif shape_i == "aclv6":
                reqs = aclv6_requirements(d, rnd)
            elif shape_i == "acl":
                reqs = (acl_requirements_patch(d, rnd) if form == "patch"
                        else acl_requirements_fix(d, rnd) if form == "fix"
                        else acl_requirements(d, rnd, form))
            else:
                reqs = chain_requirements(
                    rnd, style=pol["style"] if pol else "inline")
        # 進行表示に故障種別・対象ルータは出さない(実行者=解答者のネタバレ防止)
        print(f"[{i + 1}/{a.count}] sub-seed={subseed} "
              f"nodes={len(gmp.NODES) if shape_i == 'mploop' else len(d.get('roles', [d.get('A'), d.get('B')]))}", flush=True)

        if shape_i in ("urpf", "bgpdbg", "leakmap", "ospfv3pl", "v6redist",
                       "aaa", "acl", "aclv6"):
            collected = {}                 # 紙面専用: 実機展開・収集を行わない
        elif a.no_lab:
            collected = {(c["node"], c["command"]): "(PLACEHOLDER: --no-lab)"
                         for c in plan["checks"]}
        else:
            if shape_i == "mploop":
                write_pack_mploop(repo, prob_id, d, mp_names, subseed)
            elif shape_i == "ring":
                write_pack_ring(repo, prob_id, d, subseed, extra=herr)
            elif shape_i == "pbr":
                write_pack_pbr(repo, prob_id, d, subseed)
            else:
                write_pack(repo, prob_id, d, subseed, extra=herr, pol=pol)
            attempts, collected, err = 2, None, None
            for att in range(attempts):
                try:
                    collected = deploy_and_collect(
                        repo, prob_id, d, plan, a.boot_wait, a.settle,
                        nodes=(sorted(mp_names.values())
                               if shape_i == "mploop" else None))
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
        if shape_i == "mploop":
            q_md = question_md_mploop(d, mp_names, plan, choices, collected, stamp,
                                      sites=sites, reqs=reqs, style=opt_style,
                                      form=form)
            a_md = answer_md_mploop(d, mp_names, kind, choices, stamp, a.seed,
                                    subseed, prob_id, form=form)
            lint += ["mploop", "seg_o1", "rand_values"]
        elif shape_i == "ring":
            q_md = question_md_ring(d, plan, choices, collected, stamp, sites=sites,
                                    blind=a.exam, reqs=reqs, style=opt_style,
                                    form=form)
            a_md = answer_md_ring(d, plan, choices, stamp, a.seed, subseed, prob_id,
                                  herr=herr, form=form)
            # 「ループ」「RIB-failure」は要件文・show ip bgp 凡例に正当に現れるため対象外
            lint += ["ring=", "inject_eigrp", "inject_ospf", "震源"]
        elif shape_i == "bgpdbg":
            q_md = question_md_bgpdbg(d, stamp, rnd)
            a_md = answer_md_bgpdbg(d, stamp, a.seed, subseed)
            lint += list(gpb.VARIANTS) + ["variant=", "ルーブリック"]
        elif shape_i == "aclv6":
            blocks = aclv6_evidence(d, rnd, form)
            q_md = question_md_aclv6(d, blocks, choices, stamp, form=form,
                                     reqs=reqs, style=opt_style)
            a_md = answer_md_aclv6(d, choices, stamp, a.seed, subseed, form)
            lint += list(gp6.KINDS) + ["world=", "_select_works",
                                       "_select_correct"]
        elif shape_i == "acl":
            blocks = (acl_evidence_blocks(d, rnd) if form == "evidence"
                      else acl_logread_blocks(d, rnd) if form == "logread"
                      else acl_evidence(d, rnd, form))
            q_md = question_md_acl(d, blocks, choices, stamp, form=form,
                                   reqs=reqs, style=opt_style)
            a_md = answer_md_acl(d, choices, stamp, a.seed, subseed, form)
            lint += list(gpl.KINDS) + ["world=", "_select_works",
                                       "_select_correct", "role="]
        elif shape_i == "urpf":
            blocks, _st = urpf_evidence(d, rnd)
            q_md = question_md_urpf(d, blocks, choices, stamp, sites=sites,
                                    form=form, reqs=reqs, style=opt_style)
            a_md = answer_md_urpf(d, choices, stamp, a.seed, subseed)
            lint += list(gpu.URPF_KINDS) + ["world=", "_works"]
        elif shape_i == "leakmap":
            blocks = leakmap_evidence(d, rnd, form)
            q_md = question_md_leakmap(d, blocks, choices, stamp, form=form,
                                       reqs=reqs, style=opt_style)
            a_md = answer_md_leakmap(d, choices, stamp, a.seed, subseed, form)
            lint += list(gpk.KINDS) + ["world=", "_works", "_correct"]
        elif shape_i == "ospfv3pl":
            blocks = ospfv3pl_evidence(d, rnd, form)
            q_md = question_md_ospfv3pl(d, blocks, choices, stamp, form=form,
                                        reqs=reqs, style=opt_style)
            a_md = answer_md_ospfv3pl(d, choices, stamp, a.seed, subseed, form)
            lint += [k for k in gpo.KINDS if k != "none"] \
                + ["world=", "_works", "_correct"]
        elif shape_i == "aaa":
            blocks = aaa_evidence_blocks(d, rnd, form)
            q_md = question_md_aaa(d, blocks, choices, stamp, form=form, reqs=reqs)
            a_md = answer_md_aaa(d, choices, stamp, a.seed, subseed, form)
            lint += list(gpa.KINDS) + ["world=", "scope="]
        elif shape_i == "v6redist":
            blocks = v6redist_evidence(d, rnd, form)
            q_md = question_md_v6redist(d, blocks, choices, stamp, form=form,
                                        reqs=reqs, style=opt_style)
            a_md = answer_md_v6redist(d, choices, stamp, a.seed, subseed, form)
            lint += list(gpv.KINDS) + ["world=", "_works", "_correct"]
        elif shape_i == "pbr":
            q_md = question_md_pbr(d, plan, choices, collected, stamp, sites=sites,
                                   form=form, reqs=reqs, style=opt_style)
            a_md = answer_md_pbr(d, plan, choices, stamp, a.seed, subseed, prob_id)
            lint += ["wc_narrow", "wc_wide", "wc_bits", "acl_dir", "rm_no_match",
                     "match_plist", "world=", "fixer"]
        else:
            q_md = question_md(d, plan, choices, collected, stamp, sites=sites,
                               blind=a.exam, form=form, reqs=reqs, style=opt_style)
            a_md = answer_md(d, plan, choices, stamp, a.seed, subseed, kind, prob_id,
                             herr=herr, pol=pol)
            lint += ["missing", "no_seed", "wrong_id"]
        # 道標の除去(BL-088)。essay(bgpdbg)はタイトルのみ触る。
        q_md = obfuscate_md(q_md, random.Random(subseed ^ 0x0BF0),
                            essay=(shape_i == "bgpdbg"),
                            # ★patch も設問文が情報の担い手(「接続を失わずに」「移行の途中」)
                            # ★acl の read も同様(BL-106・4例目)= 設問文が
                            #   **向き**(転送される/破棄される)と**選ぶ個数**を担っており、
                            #   汎用文に均すと解答不能になる。
                            keep_ask=(form in ("evidence", "patch", "dbgconf",
                                               "authread")
                                      or (shape_i == "acl"
                                          and form in ("read", "counter",
                                                       "patch", "logread",
                                                       "evidence"))
                                      or (shape_i == "aclv6"
                                          and form in ("read", "counter"))))
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
