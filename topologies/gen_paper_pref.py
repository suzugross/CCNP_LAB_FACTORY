#!/usr/bin/env python3
"""経路選好 紙面MCQ ファミリ (BL-127・shape=pref) — gen_paper_mcq.py の素材。

ENARSI 1.10.d(OSPF パス選好)と 1.9.c(EIGRP FD/FS/variance)を **1つの shape**
に統合する(ユーザ判断 2026-08-16・kinds で系を分ける)。
挙動は全て PoC 実測(poc/pref/README.md・IOL 17.15・盤面 _POC-PREF)に基づく:

  OSPF  型優先はメトリックに先行(intra 510 が inter 21 に勝つ)/ E1 は累積・
        E2 は固定+forward metric の第2段 / detail の型句と forward metric の
        出現規則(★E2 にしか出ない)
  EIGRP FC は **厳密不等号**(RD == FD(successor) は不成立。variance 4 でも
        載らず、FD がより大きい FS のほうが載る)/ variance は FS のみ /
        ★非 FC の経路はスプリット・ホライズンで topology 表から消えるため
        盤面には可視の窓(`eigrpfs_model.check_board`)がある

モデル層= `ospfpref_model.py` / `eigrpfs_model.py`(純関数・決定リスト)。
本モジュールは「盤面の抽選」と「実測書式の描画」と「選択肢の構成」を持つ。
P1= read/why、P2= fix/cause/allthat+曖昧要件世界。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eigrpfs_model as efs   # noqa: E402
import ospfpref_model as opm  # noqa: E402

KINDS = ["type_intra", "type_e1e2", "e2_fwd", "e1_accum",
         "fc_strict", "fs_allthat", "variance_bound", "variance_nonfc"]
OSPF_KINDS = ["type_intra", "type_e1e2", "e2_fwd", "e1_accum"]
EIGRP_KINDS = ["fc_strict", "fs_allthat", "variance_bound", "variance_nonfc"]
FAM = {k: ("ospf" if k in OSPF_KINDS else "eigrp") for k in KINDS}

WORLDS = ["w_freeze_area", "w_no_e1", "w_variance_cap", "w_single_touch",
          "w_local_only", "w_target_only"]
# kind ごとに要件世界が成立する組(fix の正解を反転させるレバー)。
# ★どの世界で一意になるかは盤面依存なので、draw が機械検証して落とす
#  (成立しない組は ValueError → 生成器が別 seed で引き直す)。
KIND_WORLDS = {
    "type_intra": ["w_freeze_area", "w_single_touch"],
    "type_e1e2": ["w_target_only", "w_single_touch", "w_local_only"],
    "e2_fwd": ["w_target_only", "w_no_e1", "w_single_touch", "w_local_only"],
    "e1_accum": ["w_target_only", "w_no_e1", "w_single_touch", "w_local_only"],
    "fc_strict": ["w_single_touch", "w_local_only", "w_variance_cap",
                  "w_target_only"],
    "fs_allthat": ["w_variance_cap", "w_single_touch", "w_target_only"],
    "variance_bound": ["w_variance_cap", "w_single_touch", "w_local_only",
                       "w_target_only"],
    "variance_nonfc": ["w_single_touch", "w_variance_cap", "w_target_only"],
}

# 要件世界= 制約の束(copp と同じ考え方)。候補の属性に対する述語で表す。
#   n_changes      触る箇所の数
#   scope          "local"= 観測点のみ / "remote"= 他のデバイスも触る
#   raises_var     variance の倍率を上げる
#   changes_type   外部メトリックの型(タイプ1/2)を変える
#   changes_area   エリア構成を変える
#   worsens        現在の最良経路のメトリックを悪化させる
#   touches_winner 現在選好されている経路の側の構成を触る
# ★worsens は**静的な属性ではなくモデルから実測**する(_worsens)。
#   「型を変えると悪化する」等の思い込みを要件文に書くと、判定文が事実に反する。
WORLD_RULES = {
    "w_single_touch": dict(max_changes=1, worsens=False),
    "w_local_only": dict(max_changes=1, scope="local", worsens=False),
    "w_variance_cap": dict(max_changes=1, raises_var=False),
    "w_no_e1": dict(max_changes=1, changes_type=False),
    "w_freeze_area": dict(max_changes=1, changes_area=False),
    "w_target_only": dict(max_changes=1, touches_winner=False),
}

# 盤面の名前プール(BL-118: 定数は seed 抽選して暗記を無効化する)
OSPF_PROC_POOL = [1, 10, 100]
EIGRP_AS_POOL = [100, 110, 200]
AREA_POOL = [1, 2, 3, 10, 20]


def kind_forms(kind):
    """その kind が原理的に取り得る出題形(盤面に依らない上限)。

    - `type_intra`(エリア内 > エリア間)は **fix を持たない**。型優先は
      「どちらが勝つか」が構造で決まっており、1 手の是正で反転させられない
      (エリア構成の変更しか手が無く、候補が 2 本立たない)。
    - `allthat`(FS をすべて選べ)は **fs_allthat のみ**。選択肢=盤面の経路
      なので、4 本以上の経路を持つ盤面でないと 4 択に届かない。
    """
    if FAM[kind] == "eigrp":
        base = {"read", "why", "fix", "cause"}
        return base | ({"allthat"} if kind == "fs_allthat" else set())
    if kind == "type_intra":
        return {"read", "why", "cause"}
    return {"read", "why", "fix", "cause"}


def forms_for(d):
    """**その盤面で実際に成立する**形(fix は一意性の検証に通ったときだけ)。"""
    avail = set(kind_forms(d["kind"]))
    if not d.get("_fix_ok"):
        avail.discard("fix")
    return avail


# --------------------------------------------------------------------------
# 盤面の抽選
# --------------------------------------------------------------------------
def _names(rnd, n):
    start = rnd.choice([1, 11, 21, 31])
    return [f"RT{start + i:02d}" for i in range(n)]


def _pfx(rnd):
    a, b = rnd.randint(16, 199), rnd.choice([0, 8, 16, 24, 32, 40, 48])
    return f"10.{a}.{b}.0", f"10.{a}.{b}.0/24"


def draw(rnd, kind=None, world=None):
    d = {"shape": "pref"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["world"] = world or rnd.choice(KIND_WORLDS[d["kind"]])
    if d["world"] not in KIND_WORLDS[d["kind"]]:
        raise ValueError(f"pref: kind={d['kind']} は world={d['world']} を持たない")
    d["fam"] = FAM[d["kind"]]
    d["pfx"], d["pfx_len"] = _pfx(rnd)
    d["obs"], *nb = _names(rnd, 5)
    d["nbr_names"] = nb
    d["net"] = f"10.{rnd.randint(200, 249)}"
    if d["fam"] == "ospf":
        _draw_ospf(d, rnd)
    else:
        _draw_eigrp(d, rnd)
    # ★fix を持つ kind は「一意な是正が存在する盤面」だけを採用する
    #   (copp と同じ方針= 一意性は生命線。落ちた draw は生成器が引き直す)。
    verify_fix(d)
    if "fix" in kind_forms(d["kind"]) and not d["_fix_ok"]:
        raise ValueError(f"pref: fix の一意性が立たない kind={d['kind']} "
                         f"world={d['world']}")
    _set_vague(d, rnd)
    return d


def _vague_ok(d):
    """曖昧要件(対象の名指しを落とす)が **一意に補完できる**盤面か。

    BL-113 の3条件(矛盾なし/一意に補完可/一意性維持)の機械保証。
    - OSPF= 「より小さい外部メトリックが広告されている側」で一意に指せること。
      外部メトリックが同値の盤面(e2_fwd)や内部系(type_intra)では成立しない。
    - EIGRP= 「現在は搭載されていない冗長なパス」がちょうど 1 本であること。
    """
    if not d.get("_fix_target"):
        return False
    if d["fam"] == "ospf":
        if d["kind"] not in ("type_e1e2", "e1_accum"):
            return False
        m = {p["key"]: p for p in d["paths"]}
        t, w = m[d["_fix_target"]], m[d["_winner"]]
        return t["ext"] < w["ext"]
    return len([p for p in d["paths"]
                if p["key"] not in d["_installed"]]) == 1


def _set_vague(d, rnd):
    d["vague"] = bool(d.get("_fix_ok")) and _vague_ok(d) and rnd.random() < 0.4


# ---------------------------------------------------------------- OSPF 盤面
def _o_nbr(d, i, cost):
    """観測点から見た i 番目の隣接(next-hop・IF・観測点側のリンクコスト)。"""
    return {"name": d["nbr_names"][i],
            "rid": f"{i + 2}.{i + 2}.{i + 2}.{i + 2}",
            "nh": f"{d['net']}.{i + 2}.{i + 2}",
            "net": f"{d['net']}.{i + 2}.0/24",
            "iface": f"Ethernet0/{i}",
            "cost": cost}


def _draw_ospf(d, rnd):
    d["proc"] = rnd.choice(OSPF_PROC_POOL)
    d["area"] = rnd.choice(AREA_POOL)
    d["obs_rid"] = "1.1.1.1"
    k = d["kind"]
    # 観測点→隣接のリンクコスト(2本。決定化のため必ず異なる値にする)
    c1, c2 = rnd.sample([5, 10, 20, 30, 40, 50, 60, 100], 2)
    n1, n2 = _o_nbr(d, 0, c1), _o_nbr(d, 1, c2)
    d["nbrs"] = [n1, n2]
    if k == "type_intra":
        # エリア内(コスト大) vs エリア間(コスト小)= 型がコストに先行
        stub = rnd.choice([200, 300, 400, 500])          # 広告元 IF のコスト
        m3 = rnd.choice([1, 5, 11, 15])                  # Type-3 の Metric
        d["stub_cost"], d["t3_metric"] = stub, m3
        d["paths"] = [
            dict(key=f"via {n1['nh']}", kind="intra", cost=n1["cost"] + stub,
                 ext=0, fwd=0, rid=n1["rid"], nbr=n1),
            dict(key=f"via {n2['nh']}", kind="inter", cost=n2["cost"] + m3,
                 ext=0, fwd=0, rid=n2["rid"], nbr=n2)]
        d["abr"] = n2
    elif k == "type_e1e2":
        # E1(累積で大きい) vs E2(表示は小さい)= 型が先
        e1 = rnd.choice([50, 100, 150, 200])
        e2 = rnd.choice([5, 10, 20])
        d["paths"] = [
            dict(key=f"via {n1['nh']}", kind="e1", cost=0, ext=e1,
                 fwd=n1["cost"], rid=n1["rid"], nbr=n1),
            dict(key=f"via {n2['nh']}", kind="e2", cost=0, ext=e2,
                 fwd=n2["cost"], rid=n2["rid"], nbr=n2)]
    elif k == "e2_fwd":
        # E2 同値 → forward metric(= ASBR までの内部コスト)の第2段
        e = rnd.choice([10, 20, 30, 50])
        d["paths"] = [
            dict(key=f"via {n1['nh']}", kind="e2", cost=0, ext=e,
                 fwd=n1["cost"], rid=n1["rid"], nbr=n1),
            dict(key=f"via {n2['nh']}", kind="e2", cost=0, ext=e,
                 fwd=n2["cost"], rid=n2["rid"], nbr=n2)]
    else:  # e1_accum: 外部メトリックだけ見ると逆になる組を作る
        #   ext1 > ext2 かつ ext1+fwd1 < ext2+fwd2 になるよう選ぶ
        for _ in range(200):
            e1 = rnd.choice([20, 30, 40, 50, 60])
            e2 = rnd.choice([10, 15, 20, 25])
            if e1 > e2 and e1 + n1["cost"] < e2 + n2["cost"]:
                break
        else:
            raise ValueError("pref: e1_accum の組が作れない")
        d["paths"] = [
            dict(key=f"via {n1['nh']}", kind="e1", cost=0, ext=e1,
                 fwd=n1["cost"], rid=n1["rid"], nbr=n1),
            dict(key=f"via {n2['nh']}", kind="e1", cost=0, ext=e2,
                 fwd=n2["cost"], rid=n2["rid"], nbr=n2)]
    r = opm.best(d["paths"])          # strict: ECMP 盤面は ValueError で捨てる
    d["_winner"], d["_step"] = r["winner"], r["step"]
    if k == "type_intra" and d["_step"] != "type":
        raise ValueError("pref: type_intra が型段で決まっていない")
    if k == "e2_fwd" and d["_step"] != "fwd":
        raise ValueError("pref: e2_fwd が forward metric 段で決まっていない")
    if k == "e1_accum" and d["_step"] != "metric":
        raise ValueError("pref: e1_accum がメトリック段で決まっていない")
    d["_fix_target"] = [p["key"] for p in d["paths"]
                        if p["key"] != d["_winner"]][0]
    # LSA の見た目(age/seq/checksum)は seed 決定・盤面ごとに固定
    for i, p in enumerate(d["paths"]):
        p["age"] = rnd.randint(60, 900)
        p["seq"] = f"8000000{rnd.randint(1, 9)}"
        p["cksum"] = f"0x{rnd.randint(0x1000, 0xFFFF):04X}"
    return d


# --------------------------------------------------------------- EIGRP 盤面
LO_DELAY = 500          # 宛先 Loopback の delay(10us 単位・PoC 実測 5000us)
BW_TERM = 1000          # 10^7 / 10000kbps(Ethernet)


def _e_metric(far, near=0):
    return 256 * (BW_TERM + LO_DELAY + far + near)


def _e_path(d, i, far, near):
    """RD/cost をリンク遅延から作る(PoC 実測の算術そのまま)。"""
    nh = f"{d['net']}.{i + 2}.{i + 2}"
    return {"key": f"via {nh}", "rd": _e_metric(far), "cost": 256 * near,
            "nh": nh, "iface": f"Ethernet0/{i}", "far": far, "near": near,
            "name": d["nbr_names"][i]}


def _draw_eigrp(d, rnd):
    d["asn"] = rnd.choice(EIGRP_AS_POOL)
    d["obs_rid"] = f"{rnd.randint(11, 99)}.0.0.1"
    k = d["kind"]
    na = rnd.choice([100, 150, 200])            # successor 側の近リンク遅延
    A = _e_path(d, 0, far=100, near=na)         # successor
    fd_a = efs.fd(A)
    paths = [A]
    if k == "fc_strict":
        # ★RD == FD(successor) ちょうど= FC 不成立(等号)。可視(窓の下端)。
        nb = rnd.choice([x for x in (250, 300, 350, 400) if x != na])
        B = _e_path(d, 1, far=100, near=nb)     # FS
        C = _e_path(d, 2, far=100 + na, near=rnd.choice([100, 150]))
        paths += [B, C]
        d["variance"] = rnd.choice([3, 4])
    elif k == "variance_nonfc":
        # 非 FC だが倍率の範囲内に見える(可視の窓に収める)
        nc = rnd.choice([100, 150, 200])
        far_c = 100 + na + max(1, nc // 2)      # 窓 (100+na, 100+na+nc) の内側
        C = _e_path(d, 2, far=far_c, near=nc)
        nb = rnd.choice([x for x in (250, 300, 350) if x != na])
        B = _e_path(d, 1, far=100, near=nb)     # FS(比較用)
        paths += [B, C]
        d["variance"] = rnd.choice([2, 3])
    elif k == "variance_bound":
        # FS だが FD が倍率の範囲外 → 乗らない(倍率を上げれば乗る)。
        # 対照として「範囲内の FS」も置き、範囲だけが分岐点であることを見せる。
        v = rnd.choice([2, 3])
        need = v * fd_a
        inr = [x for x in range(na + 50, na + 2000, 50)
               if _e_metric(100, x) <= need]
        outr = [x for x in range(na + 100, na + 4000, 50)
                if _e_metric(100, x) > need]
        if not inr or not outr:
            raise ValueError("pref: variance_bound の組が作れない")
        nc = rnd.choice(inr)
        nb = rnd.choice([x for x in outr if x > nc][:6] or outr[:1])
        C = _e_path(d, 2, far=100, near=nc)     # FS(範囲内 → 載る)
        B = _e_path(d, 1, far=100, near=nb)     # FS(範囲外 → 載らない)
        paths += [B, C]
        d["variance"] = v
        d["_min_var"] = None                    # 後段で埋める
    else:  # fs_allthat: successor + FS×2 + 非FC×1(allthat の正解集合を作る)
        nb1, nb2 = rnd.sample([250, 300, 350, 400, 450], 2)
        B = _e_path(d, 1, far=100, near=nb1)
        C = _e_path(d, 2, far=rnd.choice([120, 150, 180]), near=nb2)
        nd = rnd.choice([100, 150])
        D = _e_path(d, 3, far=100 + na + max(1, nd // 2), near=nd)
        paths += [B, C, D]
        d["variance"] = rnd.choice([2, 3])
    d["paths"] = paths
    # FD 一意(ECMP 拒否)・スプリット・ホライズン窓の機械検証
    efs.successor(paths)
    efs.check_board(paths)
    if len({efs.fd(p) for p in paths}) != len(paths):
        raise ValueError("pref: FD が重複している(表示が非決定になる)")
    d["_roles"] = efs.classify(paths)
    d["_succ"] = efs.successor(paths)["key"]
    d["_installed"] = efs.variance_installed(paths, d["variance"])
    if k == "fc_strict" and d["_roles"][paths[2]["key"]] != "non_fc":
        raise ValueError("pref: fc_strict の C が非FCになっていない")
    if k == "fc_strict" and paths[2]["rd"] != efs.fd_succ(paths):
        raise ValueError("pref: fc_strict の C が等号になっていない")
    if k == "fc_strict" and efs.fd(paths[2]) >= efs.fd(paths[1]):
        # ★本題: 「載らない経路の FD のほうが小さい」でないと罠にならない
        raise ValueError("pref: fc_strict の FD 関係が逆(罠が立たない)")
    if k == "variance_nonfc":
        if d["_roles"][paths[2]["key"]] != "non_fc":
            raise ValueError("pref: variance_nonfc の C が非FCでない")
        if efs.fd(paths[2]) > d["variance"] * efs.fd_succ(paths):
            raise ValueError("pref: variance_nonfc の C が倍率の外(罠が立たない)")
    if k == "variance_bound":
        d["_min_var"] = efs.min_variance_for(paths, paths[1]["key"])
        if paths[1]["key"] in d["_installed"]:
            raise ValueError("pref: variance_bound の B が乗ってしまう")
        if d["_roles"][paths[1]["key"]] != "fs":
            raise ValueError("pref: variance_bound の B が FS でない")
    if k == "fs_allthat" and len(efs.all_fs(paths)) < 2:
        raise ValueError("pref: fs_allthat の FS が 2 本未満")
    why_target(d)          # why 形の理由が一意でない盤面は捨てる
    out = [p for p in paths if p["key"] not in d["_installed"]]
    d["_fix_target"] = min(out, key=efs.fd)["key"] if out else None
    return d


# --------------------------------------------------------------------------
# 描画(PoC 実測の byte 書式)
# --------------------------------------------------------------------------
def _ext_lsa(d, p):
    """`show ip ospf database external` の 1 LSA 分(★タブ字下げは実測どおり)。"""
    mt = 1 if p["kind"] in ("e1", "n1") else 2
    note = ("Comparable directly to link state metric" if mt == 1
            else "Larger than any link state path")
    return "\n".join([
        f"  LS age: {p['age']}",
        "  Options: (No TOS-capability, DC, Upward)",
        "  LS Type: AS External Link",
        f"  Link State ID: {d['pfx']} (External Network Number )",
        f"  Advertising Router: {p['rid']}",
        f"  LS Seq Number: {p['seq']}",
        f"  Checksum: {p['cksum']}",
        "  Length: 36",
        "  Network Mask: /24",
        f"\tMetric Type: {mt} ({note})",
        "\tMTID: 0 ",
        f"\tMetric: {p['ext']} ",
        "\tForward Address: 0.0.0.0",
        "\tExternal Route Tag: 0"])


def ospf_db_external(d):
    head = [f"OSPF Router with ID ({d['obs_rid']}) (Process ID {d['proc']})", "",
            "\t\tType-5 AS External Link States", ""]
    return "\n".join(head) + "\n\n".join(_ext_lsa(d, p) for p in d["paths"])


def ospf_db_summary(d):
    """type_intra 用: エリア間経路の証拠(Type-3)。"""
    p = [x for x in d["paths"] if x["kind"] == "inter"][0]
    return "\n".join([
        f"OSPF Router with ID ({d['obs_rid']}) (Process ID {d['proc']})", "",
        "\t\tSummary Net Link States (Area 0)", "",
        f"  LS age: {p['age']}",
        "  Options: (No TOS-capability, DC, Upward)",
        "  LS Type: Summary Links(Network)",
        f"  Link State ID: {d['pfx']} (summary Network Number)",
        f"  Advertising Router: {p['rid']}",
        f"  LS Seq Number: {p['seq']}",
        f"  Checksum: {p['cksum']}",
        "  Length: 28",
        "  Network Mask: /24",
        f"\tMTID: 0 \tMetric: {d['t3_metric']}"])


def ospf_border_routers(d):
    """★観測点→各 ASBR/ABR の内部コストを 1 行で示す実測書式。

    E1 の累積・E2 の forward metric を計算させるための中心的な証拠ブロック。
    """
    L = [f"OSPF Router with ID ({d['obs_rid']}) (Process ID {d['proc']})", "", "",
         "\t\tBase Topology (MTID 0)", "",
         "Internal Router Routing Table",
         "Codes: i - Intra-area route, I - Inter-area route", ""]
    spf = 21
    for p in d["paths"]:
        if p["kind"] in ("intra",):
            continue
        role = "ABR" if p["kind"] == "inter" else "ASBR"
        n = p["nbr"]
        L.append(f"i {p['rid']} [{n['cost']}] via {n['nh']}, {n['iface']}, "
                 f"{role}, Area 0, SPF {spf}")
    return "\n".join(L)


def _eigrp_extra_rows(d):
    """実機の表に必ず混じる直結・隣接 Lo の行(盤面の現実味と読み分けの負荷)。"""
    rows = []
    for i, p in enumerate(d["paths"][:2]):
        net = f"{d['net']}.{i + 2}.0/24"
        rows.append((net, [("Connected", None, None, p["iface"])],
                     _e_metric(0, p["near"]) - 256 * LO_DELAY))
    return rows


def eigrp_topology(d, all_links=True, applied=False):
    """`show ip eigrp topology [all-links]` の byte 忠実な描画。

    ★実測の規則:
      - all-links でないときは **successor と FS のみ**が出る(非 FC は出ない)
      - variance 適用時は `N successors` の N が RIB に載った本数に変わる
      - via 行は `(FD/RD)` の順

    ★`applied=False`(既定)= **variance を構成する前**の表を描く。
      設問は「variance を構成した場合にどうなるか」を問うので、適用後の表を
      出すと `N successors` が答え(本数)を漏らす。E2E 照合など適用後の表が
      要るときだけ applied=True。
    """
    paths = list(d["paths"])
    fdsucc = efs.fd_succ(paths)
    shown = [p for p in paths
             if all_links or p["key"] == d["_succ"] or efs.is_fc(p, fdsucc)]
    shown.sort(key=lambda p: efs.fd(p))
    n_succ = len(d["_installed"]) if applied else 1
    L = [f"EIGRP-IPv4 Topology Table for AS({d['asn']})/ID({d['obs_rid']})",
         "Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,",
         "       r - reply Status, s - sia Status ", ""]
    # 直結エントリ(表の現実味)
    for i, p in enumerate(paths[:2]):
        net = f"{d['net']}.{i + 2}.0/24"
        tail = f", serno {i + 2}" if all_links else ""
        L.append(f"P {net}, 1 successors, FD is {256 * (BW_TERM + p['near'])}"
                 f"{tail}")
        L.append(f"        via Connected, {p['iface']}")
    tail = f", serno {len(paths) + 4}, refcount 1" if all_links else ""
    L.append(f"P {d['pfx_len']}, {n_succ} successors, FD is {fdsucc}{tail}")
    for p in shown:
        L.append(f"        via {p['nh']} ({efs.fd(p)}/{p['rd']}), {p['iface']}")
    return "\n".join(L)


def eigrp_route(d):
    """`show ip route <pfx>`(variance 適用後の RIB)。

    ★successor のブロックだけ `  * ` が付き、他は 4 字下げ(実測)。
    traffic share count は実測の比が非自明なので **1 本のときだけ**描画し、
    複数本のときは比を問わない形にする(盤面の嘘を避ける)。
    """
    paths = {p["key"]: p for p in d["paths"]}
    inst = [paths[k] for k in d["_installed"]]
    L = [f"Routing entry for {d['pfx_len']}",
         f'  Known via "eigrp {d["asn"]}", distance 90, metric '
         f"{efs.fd_succ(d['paths'])}, precedence routine (0), type internal",
         f"  Redistributing via eigrp {d['asn']}",
         f"  Last update from {inst[0]['nh']} on {inst[0]['iface']}, "
         "00:00:21 ago",
         "  Routing Descriptor Blocks:"]
    for p in sorted(inst, key=lambda x: efs.fd(x)):
        star = "  * " if p["key"] == d["_succ"] else "    "
        L += [f"{star}{p['nh']}, from {p['nh']}, 00:00:21 ago, via {p['iface']}",
              f"      Route metric is {efs.fd(p)}, traffic share count is 1",
              f"      Total delay is {10 * (LO_DELAY + p['far'] + p['near'])} "
              "microseconds, minimum bandwidth is 10000 Kbit",
              "      Reliability 255/255, minimum MTU 1500 bytes",
              "      Loading 1/255, Hops 2"]
    return "\n".join(L)


# --------------------------------------------------------------------------
# fix 形 — 「目的の経路を使わせる 1 手はどれか」
#   ★候補をモデルに適用して works(目的が達成される)を機械判定し、
#     要件世界の制約で complies を絞る。complies==1 / works>=2 を draw で強制。
# --------------------------------------------------------------------------
def _cand(key, prose, cli, **attr):
    a = dict(n_changes=1, scope="local", raises_var=False, changes_type=False,
             changes_area=False, worsens=False, touches_winner=False)
    a.update(attr)
    return dict(key=key, prose=prose, cli=cli, **a)


def _o_fix_cands(d):
    """OSPF の是正候補。値は「効くはずの値」を計算して置く(効くかはモデルが決める)。"""
    ps = {p["key"]: p for p in d["paths"]}
    W, T = ps[d["_winner"]], ps[d["_fix_target"]]
    mW, mT = opm.metric_eff(W), opm.metric_eff(T)
    tn, wn = T["nbr"], W["nbr"]
    out = []
    # ① 対象を外部タイプ 1 にする(型で先行させる)
    out.append(_cand(
        "mt1_target",
        f"{tn['name']} における再配送を、外部タイプ 1(metric-type 1)へ変更する",
        [f"router ospf {d['proc']}",
         " redistribute static subnets metric-type 1"],
        scope="remote", changes_type=True))
    # ② 現在の勝者を外部タイプ 2 に落とす
    out.append(_cand(
        "mt2_winner",
        f"{wn['name']} における再配送を、外部タイプ 2(metric-type 2)へ変更する",
        [f"router ospf {d['proc']}",
         " redistribute static subnets metric-type 2"],
        scope="remote", changes_type=True, touches_winner=True))
    # ③ 観測点側のコストを下げて、対象の実効メトリックを下げる
    newc = max(1, (mW - T["ext"] - 1) if T["kind"] in ("e1", "n1")
               else W["fwd"] - 1)
    if newc < T["fwd"]:
        out.append(_cand(
            "cost_down_target",
            f"{d['obs']} の {tn['iface']} の OSPF のコストを {newc} へ下げる",
            [f"interface {tn['iface']}", f" ip ospf cost {newc}"]))
    # ④ 観測点側のコストを上げて、現在の勝者を悪化させる
    upc = wn["cost"] + max(1, mT - mW + 1)
    out.append(_cand(
        "cost_up_winner",
        f"{d['obs']} の {wn['iface']} の OSPF のコストを {upc} へ上げる",
        [f"interface {wn['iface']}", f" ip ospf cost {upc}"],
        touches_winner=True))
    # ⑤ 対象の外部メトリックを下げる
    newe = max(1, (mW - T["fwd"] - 1) if T["kind"] in ("e1", "n1") else mW - 1)
    if newe < T["ext"]:
        out.append(_cand(
            "ext_down_target",
            f"{tn['name']} における再配送のメトリックを {newe} へ下げる",
            [f"router ospf {d['proc']}",
             f" redistribute static subnets metric {newe}"], scope="remote"))
    # ⑥ AD を触る(同一プロセス内の選好には効かない= 常に無効)
    out.append(_cand(
        "distance_ospf",
        f"{d['obs']} において、外部の経路のアドミニストレーティブ・"
        "ディスタンスを 105 へ変更する",
        [f"router ospf {d['proc']}", " distance ospf external 105"]))
    # ⑦ 2 箇所を同時に触る(効くが「1 箇所のみ」の世界に反する)
    out.append(_cand(
        "both_cost",
        f"{d['obs']} の {tn['iface']} のコストを {max(1, newc)} へ下げ、"
        f"かつ {wn['iface']} のコストを {upc} へ上げる",
        [f"interface {tn['iface']}", f" ip ospf cost {max(1, newc)}",
         f"interface {wn['iface']}", f" ip ospf cost {upc}"],
        n_changes=2, touches_winner=True))
    return out


def _o_apply(d, cand):
    ps = [dict(p) for p in d["paths"]]
    m = {p["key"]: p for p in ps}
    W, T = m[d["_winner"]], m[d["_fix_target"]]
    k = cand["key"]
    if k == "mt1_target":
        T["kind"] = "e1" if T["kind"] in ("e2", "e1") else T["kind"]
    elif k == "mt2_winner":
        W["kind"] = "e2" if W["kind"] in ("e1", "e2") else W["kind"]
    elif k in ("cost_down_target", "both_cost"):
        T["fwd"] = _num(cand["cli"][1])
        T["cost"] = T["cost"] - (d["paths"][0]["fwd"] - T["fwd"]) \
            if T["kind"] in ("intra", "inter") else T["cost"]
        if k == "both_cost":
            W["fwd"] = _num(cand["cli"][3])
    elif k == "cost_up_winner":
        W["fwd"] = _num(cand["cli"][1])
    elif k == "ext_down_target":
        T["ext"] = _num(cand["cli"][1])
    return ps


def _num(line):
    return int(line.strip().split()[-1])


def _e_fix_cands(d):
    ps = {p["key"]: p for p in d["paths"]}
    T = ps[d["_fix_target"]]
    S = ps[d["_succ"]]
    need = efs.min_variance_for(d["paths"], T["key"])
    vup = need if need else d["variance"] + 2
    out = [
        _cand("variance_up",
              f"{d['obs']} の EIGRP のプロセスにおいて、variance を {vup} へ"
              "引き上げる",
              [f"router eigrp {d['asn']}", f" variance {vup}"],
              raises_var=True),
        _cand("delay_near_down",
              f"{d['obs']} の {T['iface']} の delay を 100 へ下げる",
              [f"interface {T['iface']}", " delay 100"]),
        _cand("delay_far_down",
              f"{T['name']} の、宛先の側のインタフェースの delay を 100 へ"
              "下げる",
              ["interface <宛先の側>", " delay 100"], scope="remote"),
        _cand("delay_succ_up",
              f"{d['obs']} の {S['iface']} の delay を {S['near'] + 500} へ"
              "上げる",
              [f"interface {S['iface']}", f" delay {S['near'] + 500}"],
              touches_winner=True),
        _cand("static_route",
              f"{d['obs']} において、{d['pfx_len']} へのスタティック・ルートを "
              f"{T['nh']} 宛てに追加する",
              [f"ip route {d['pfx']} 255.255.255.0 {T['nh']}"]),
        _cand("both_delay",
              f"{d['obs']} の {T['iface']} の delay を 100 へ下げ、かつ "
              f"{T['name']} の宛先の側の delay を 100 へ下げる",
              [f"interface {T['iface']}", " delay 100",
               "! および " + T["name"] + " 側", " delay 100"],
              n_changes=2, scope="remote"),
    ]
    return out


def _e_apply(d, cand):
    ps = [dict(p) for p in d["paths"]]
    m = {p["key"]: p for p in ps}
    T, S = m[d["_fix_target"]], m[d["_succ"]]
    v = d["variance"]
    k = cand["key"]
    if k == "variance_up":
        v = _num(cand["cli"][1])
    elif k == "delay_near_down":
        T["cost"] = 256 * 100
    elif k == "delay_far_down":
        T["rd"] = _e_metric(100)
    elif k == "delay_succ_up":
        S["cost"] = 256 * (S["near"] + 500)
    elif k == "both_delay":
        T["cost"], T["rd"] = 256 * 100, _e_metric(100)
    return ps, v


def _worsens(d, cand):
    """★その候補が「現在の最良の経路」を悪化させるかを **モデルで実測**する。

    OSPF= 現在の勝者の(実効メトリック, forward metric)が増える。
    EIGRP= サクセサの FD が増える。
    静的な思い込み(型を変えれば悪化する 等)で判定すると、選択肢の判定文が
    盤面の数値と矛盾する(2026-08-16 に実際に踏んだ欠陥)。
    """
    try:
        if d["fam"] == "ospf":
            m0 = {p["key"]: p for p in d["paths"]}[d["_winner"]]
            m1 = {p["key"]: p for p in _o_apply(d, cand)}[d["_winner"]]
            return ((opm.metric_eff(m1), m1["fwd"])
                    > (opm.metric_eff(m0), m0["fwd"]))
        ps, _v = _e_apply(d, cand)
        return efs.fd_succ(ps, strict=False) > efs.fd_succ(d["paths"],
                                                           strict=False)
    except (ValueError, KeyError, IndexError):
        return False


def _fix_works(d, cand):
    """その候補で「目的」が達成されるか(モデルによる機械判定)。"""
    try:
        if d["fam"] == "ospf":
            ps = _o_apply(d, cand)
            return opm.best(ps, strict=False)["winner"] == d["_fix_target"]
        ps, v = _e_apply(d, cand)
        if efs.successor(ps, strict=False)["key"] != d["_succ"]:
            return False        # サクセサが入れ替わるのは「目的」ではない
        return d["_fix_target"] in efs.variance_installed(ps, v, strict=False)
    except (ValueError, KeyError, IndexError):
        return False


def _fix_complies(d, cand):
    r = WORLD_RULES[d["world"]]
    if cand["n_changes"] > r.get("max_changes", 99):
        return False
    if r.get("scope") == "local" and cand["scope"] != "local":
        return False
    if r.get("worsens") is False and _worsens(d, cand):
        return False
    for a in ("raises_var", "changes_type", "changes_area", "touches_winner"):
        if a in r and r[a] is False and cand[a]:
            return False
    return True


def fix_candidates(d):
    return (_o_fix_cands(d) if d["fam"] == "ospf" else _e_fix_cands(d))


def verify_fix(d):
    """fix 形の一意性(complies==1・works>=2)を機械検証する。

    成立しない盤面は `_fix_ok=False` にして fix を出さない(read/why/cause は可)。
    """
    cands = fix_candidates(d)
    works = [c["key"] for c in cands if _fix_works(d, c)]
    ok = [c["key"] for c in cands
          if c["key"] in works and _fix_complies(d, c)]
    d["_fix_works"], d["_fix_ok"] = works, (len(ok) == 1 and len(works) >= 2)
    d["_fix_correct"] = ok[0] if len(ok) == 1 else None
    return d["_fix_ok"]


# ★その kind の「本題の誤解」に対応する錯乱肢。抽選で落とすと、問題の核心を
#   突く肢が盤面から消えてしまうので、必ず提示する。
FORCED_DISTRACTORS = {
    "fc_strict": ["variance_up", "delay_near_down"],
    "variance_nonfc": ["variance_up", "delay_near_down"],
    "variance_bound": ["variance_up"],
    "fs_allthat": ["variance_up"],
    "type_e1e2": ["cost_down_target", "ext_down_target"],
    "e1_accum": ["ext_down_target"],
    "e2_fwd": ["ext_down_target"],
}


def build_choices_fix(d, rnd):
    """5択・正解1。錯乱肢は「機能しない候補」と「機能するが要件に反する候補」。"""
    cands = {c["key"]: c for c in fix_candidates(d)}
    cor = cands[d["_fix_correct"]]
    losers = [c for k, c in cands.items() if k != cor["key"]]
    # ★「機能するが要件に反する」肢を必ず 1 つ以上入れる(要件世界が効いている証拠)
    viol = [c for c in losers
            if c["key"] in d["_fix_works"] and not _fix_complies(d, c)]
    fails = [c for c in losers if c["key"] not in d["_fix_works"]]
    rnd.shuffle(viol)
    rnd.shuffle(fails)
    forced = [cands[k] for k in FORCED_DISTRACTORS.get(d["kind"], [])
              if k in cands and k != cor["key"]]
    rest = [c for c in (viol[:2] + fails) if c not in forced]
    picks = (forced + rest)[:4]
    if len(picks) < 4:
        picks = (forced + viol + fails)[:4]
    out = [(cor["prose"], True, "")]
    seen = {cor["prose"]}
    for c in picks:
        if c["prose"] in seen:
            continue
        seen.add(c["prose"])
        out.append((c["prose"], False, _fix_why(d, c)))
    if len(out) != 5:
        raise ValueError(f"pref fix: 選択肢が不足 kind={d['kind']}")
    rnd.shuffle(out)
    return out


def _fix_why(d, c):
    if c["key"] in d["_fix_works"]:
        r = WORLD_RULES[d["world"]]
        if c["n_changes"] > r.get("max_changes", 99):
            return ("目的は達成されるが、変更が 2 箇所に及んでおり、"
                    "示されている要件に反する。")
        if r.get("scope") == "local" and c["scope"] != "local":
            return ("目的は達成されるが、観測点以外のデバイスの構成を"
                    "変更しており、示されている要件に反する。")
        if r.get("raises_var") is False and c["raises_var"]:
            return ("目的は達成されるが、倍率を引き上げており、"
                    "示されている要件に反する。")
        if r.get("changes_type") is False and c["changes_type"]:
            return ("目的は達成されるが、外部のメトリックの型を変更しており、"
                    "示されている要件に反する。")
        if r.get("touches_winner") is False and c["touches_winner"]:
            return ("目的は達成されるが、現在選好されている経路の側の構成を"
                    "変更しており、示されている要件に反する。")
        if r.get("worsens") is False and _worsens(d, c):
            return ("目的は達成されるが、現在の最良の経路のメトリックを"
                    "悪化させており、示されている要件に反する。")
        return "示されている要件に反する。"
    return _fix_why_fail(d, c)


def _fix_why_fail(d, c):
    k = c["key"]
    if d["fam"] == "ospf":
        return {
            "mt1_target": "型を変更しても、実効のメトリックが現在の勝者を"
                          "下回らないため、選好は変わらない。",
            "mt2_winner": "型を変更しても、当該の経路が依然として先に"
                          "選好される。",
            "cost_down_target": "外部タイプ 2 の経路のメトリックは、ASBR まで"
                                "の内部のコストを含まない。あるいは、型の段で"
                                "先に決着しているため、コストの変更は選好を"
                                "変えない。",
            "cost_up_winner": "型の段で先に決着しているため、コストを上げても"
                              "選好は変わらない。",
            "ext_down_target": "型の段で先に決着しているため、外部メトリックの"
                               "変更は選好を変えない。",
            "distance_ostf": "",
            "distance_ospf": "いずれの経路も同一の OSPF のプロセスにより"
                             "学習されており、アドミニストレーティブ・"
                             "ディスタンスは経路の選好に影響しない。",
            "both_cost": "型の段で先に決着しているため、コストの変更は"
                         "選好を変えない。",
        }.get(k, "示されている構成の帰結を変えない。")
    return {
        "variance_up": "★当該の経路はフィージビリティの条件を満たしておらず、"
                       "variance の倍率をいくら引き上げても搭載されない。"
                       "variance は、条件を満たす経路の中から範囲に収まるものを"
                       "選ぶ機構である。",
        "delay_near_down": "観測点の側の delay を下げても、隣接が申告する "
                           "RD は変わらない。フィージビリティの条件は "
                           "RD とサクセサの FD の比較であるため、条件は"
                           "満たされないままである。",
        "delay_far_down": "当該の変更では、条件または範囲が満たされない。",
        "delay_succ_up": "サクセサ側の delay を上げると、当該の経路は"
                         "搭載され得るが、現在の最良の経路のメトリックが"
                         "悪化する。",
        "static_route": "スタティック・ルートの追加は、EIGRP の経路の選択"
                        "そのものを変更しない(かつ、示されている要件により"
                        "禁止されている)。",
        "both_delay": "当該の変更では、条件または範囲が満たされない。",
    }.get(k, "示されている構成の帰結を変えない。")


def fix_question(d):
    m = {p["key"]: p for p in d["paths"]}
    t = m[d["_fix_target"]]
    if d["fam"] == "ospf":
        tgt = (f"{t['nbr']['name']}({t['nbr']['nh']})経由" if not d.get("vague")
               else "より小さい外部メトリックが広告されている側の ASBR を経由"
                    "するところ")
        return (f"{tgt}の経路が {d['obs']} において選好されるようにするために、"
                "実施されなければならない変更は、どれですか。"
                "(1つを選択してください)")
    tgt = (f"{t['name']}({t['nh']})経由" if not d.get("vague")
           else "現在は搭載されていない冗長なパス")
    return (f"現在の最良の経路を変更することなく、{tgt}の経路も転送に"
            "利用されるようにするために、実施されなければならない変更は、"
            "どれですか。(1つを選択してください)")


# --------------------------------------------------------------------------
# cause 形 — 「設計の意図どおりにならない原因はどれか」
# --------------------------------------------------------------------------
CAUSE_TXT = {
    "type_intra": "当該の経路はエリア間(inter area)であり、エリア内"
                  "(intra area)の経路に対して、メトリックの比較より前の段で"
                  "選好されないため",
    "type_e1e2": "当該の経路は外部タイプ 2 として広告されており、外部タイプ 1 "
                 "の経路に対して、メトリックの比較より前の段で選好されないため",
    "e2_fwd": "2 つの経路の外部メトリックが同一であり、ASBR までの内部の"
              "コスト(forward metric)が大きい側が選好されないため",
    "e1_accum": "外部タイプ 1 の実効のメトリックは、外部メトリックに ASBR "
                "までの内部のコストが加算された値であり、当該の経路の合計が"
                "大きいため",
    "fc_strict": "当該の経路の RD が、現在のサクセサの FD 以上であり、"
                 "フィージビリティの条件を満たさないため",
    "variance_nonfc": "当該の経路の RD が、現在のサクセサの FD 以上であり、"
                      "フィージビリティの条件を満たさないため",
    "variance_bound": "当該の経路はフィージブル・サクセサであるが、その FD が "
                      "variance × サクセサの FD の範囲を超えているため",
    "fs_allthat": "当該の経路はフィージビリティの条件を満たさないため",
}
CAUSE_NO = {
    "type_intra": "この盤面に、エリア内とエリア間の競合は存在しない。",
    "type_e1e2": "この盤面の 2 つの経路は、いずれも同一の外部の型である。",
    "e2_fwd": "この盤面では、外部メトリックが同一ではない。",
    "e1_accum": "この盤面では、外部タイプ 1 同士の合計の比較は行われていない。",
    "fc_strict": "この盤面では、フィージビリティの条件は満たされている。",
    "variance_bound": "この盤面では、FD は variance の範囲に収まっている。",
}
CAUSE_GENERIC = [
    ("アドミニストレーティブ・ディスタンスが、他方の経路より大きいため",
     "いずれの経路も同一のプロセスにより学習されており、"
     "アドミニストレーティブ・ディスタンスは同一である。"),
    ("当該の経路のホップ数が、他方の経路より多いため",
     "ホップ数は、既定のメトリックの計算に含まれない。"),
    ("当該の経路の最小の帯域幅が、他方の経路より小さいため",
     "いずれの経路も、最小の帯域幅は同一である。"),
    ("当該の経路の隣接関係が確立されていないため",
     "当該の経路は、テーブルに現れており、隣接関係は確立されている。"),
]


def build_choices_cause(d, rnd):
    k = d["kind"]
    cor = CAUSE_TXT[k]
    same_fam = [x for x in (OSPF_KINDS if d["fam"] == "ospf" else EIGRP_KINDS)
                if x != k and x in CAUSE_NO]
    pool = [(CAUSE_TXT[x], CAUSE_NO[x]) for x in same_fam]
    pool += CAUSE_GENERIC
    # ★同義の機構(fc_strict と variance_nonfc)は文面が一致するので除く
    pool = [(t, w) for t, w in pool if t != cor]
    picks = rnd.sample(pool, 4)
    out = [(cor, True, "")] + [(t, False, w) for t, w in picks]
    if len({t for t, *_ in out}) != 5:
        raise ValueError("pref cause: 選択肢が重複")
    rnd.shuffle(out)
    return out


def cause_question(d):
    m = {p["key"]: p for p in d["paths"]}
    t = m[d.get("_fix_target", d["paths"][-1]["key"])]
    name = (f"{t['nbr']['name']}({t['nbr']['nh']})経由" if d["fam"] == "ospf"
            else f"{t['name']}({t['nh']})経由")
    tail = ("が選好されることが期待されていましたが、そうなっていません。"
            if d["fam"] == "ospf" else
            "も転送に利用されることが期待されていましたが、そうなっていません。")
    return (f"{name}の経路{tail}この事象の原因として、最も適切なものは、"
            "どれですか。(1つを選択してください)")


# --------------------------------------------------------------------------
# allthat 形(数非明示)— 「FS になり得る経路をすべて選べ」
# --------------------------------------------------------------------------
def build_choices_allthat(d, rnd):
    fs = set(efs.all_fs(d["paths"]))
    fdsucc = efs.fd_succ(d["paths"])
    out = []
    for p in sorted(d["paths"], key=efs.fd):
        why = ""
        if p["key"] not in fs:
            why = (f"サクセサ自身であり、FS には数えない(設問の指定)。"
                   if p["key"] == d["_succ"] else
                   f"RD {p['rd']} が、サクセサの FD {fdsucc} 以上であり、"
                   "フィージビリティの条件を満たさない。")
        out.append((_e_label(d, p), p["key"] in fs, why))
    if sum(1 for c in out if c[1]) < 1 or len(out) < 4:
        raise ValueError("pref allthat: 正解集合または選択肢が不足")
    rnd.shuffle(out)
    return out


def allthat_question(d):
    return (f"{d['obs']} における {d['pfx_len']} への経路のうち、"
            "**現在のサクセサを除き**、フィージビリティの条件を満たすもの"
            "(フィージブル・サクセサ)を、すべて選んでください。")


# --------------------------------------------------------------------------
# read 形 — 「RIB に載るのはどれか」
# --------------------------------------------------------------------------
def _o_label(d, p):
    return f"{p['nbr']['name']}({p['nbr']['nh']})経由"


def _o_opt(d, p, metric=None):
    """★選択肢の文面は必ずこの1関数で作る(正解だけ書式が違う=指紋 を防ぐ)。"""
    v = opm.metric_eff(p) if metric is None else metric
    return (f"{_o_label(d, p)}が、メトリック {v} で、"
            "ルーティング・テーブルに搭載される")


def build_choices_read(d, rnd):
    """OSPF: 勝者+メトリック / EIGRP: 載る経路の集合。正解1。"""
    if d["fam"] == "ospf":
        return _read_ospf(d, rnd)
    return _read_eigrp(d, rnd)


def _read_ospf(d, rnd):
    win = [p for p in d["paths"] if p["key"] == d["_winner"]][0]
    lose = [p for p in d["paths"] if p["key"] != d["_winner"]][0]
    out = [(_o_opt(d, win), True, "")]
    # ①「真だが答えていない/型を無視してコストで選ぶ」= 本題の罠
    out.append((_o_opt(d, lose), False, _why_type_trap(d, win, lose)))
    # ②近似値肢: 累積・forward metric の取り違えから生じる値
    approx = _read_approx(d, win, lose)
    out.append(approx)
    # ③両方載る(ECMP)= メトリックの一致だけを見た誤り
    out.append((f"{_o_label(d, win)}と{_o_label(d, lose)}の両方が、"
                "等コストのパスとして搭載される", False,
                "2 つの経路は、型またはメトリックが異なっており、"
                "等コストのパスにはならない。"))
    # ④「搭載されない」肢
    out.append((f"いずれの経路も搭載されず、{d['pfx_len']} は"
                "ルーティング・テーブルに現れない", False,
                "いずれの経路も有効であり、いずれか一方が必ず搭載される。"))
    rnd.shuffle(out)
    return out


def _why_type_trap(d, win, lose):
    if d["kind"] == "type_intra":
        return ("エリア内(intra area)の経路は、エリア間(inter area)の経路より"
                "**先に**選好される。コストの大小は、型の比較のあとに"
                "評価される。")
    if d["kind"] == "type_e1e2":
        return ("外部タイプ 1(E1)は、外部タイプ 2(E2)より先に選好される。"
                "E2 の表示するメトリックが小さいことは、型の比較を覆さない。")
    if d["kind"] == "e2_fwd":
        return ("2 つの経路の外部メトリックは同一であり、この場合は "
                "forward metric(ASBR までの内部のコスト)の小さいほうが"
                "選好される。")
    return ("外部タイプ 1 のメトリックは、外部メトリックと ASBR までの内部の"
            "コストの**合計**である。外部メトリックだけの比較は誤りである。")


def _read_approx(d, win, lose):
    """近似値肢(WCトリック型のひっかけ)。"""
    if d["kind"] in ("type_e1e2", "e1_accum"):
        v = win["ext"]                     # 累積を忘れた値
        return (_o_opt(d, win, v), False,
                "外部タイプ 1 のメトリックは、ASBR までの内部のコストが"
                f"加算される(この経路では {win['ext']} + {win['fwd']} = "
                f"{opm.metric_eff(win)})。")
    if d["kind"] == "e2_fwd":
        v = win["ext"] + win["fwd"]        # E2 なのに累積した値
        return (_o_opt(d, win, v), False,
                "外部タイプ 2 のメトリックは、ASBR までの内部のコストを"
                f"**含まない**(表示は {win['ext']} のまま。内部のコストは "
                "forward metric として別に保持される)。")
    v = d["t3_metric"]                     # ABR のコストを足し忘れた値
    return (_o_opt(d, lose, v), False,
            "エリア間の経路のメトリックは、Type-3 の Metric に、"
            f"ABR({lose['rid']})までの内部のコストが加算される"
            f"(この経路では {d['t3_metric']} + {lose['nbr']['cost']} = "
            f"{opm.metric_eff(lose)})。この経路は、そもそも型で選好されない。")


def _e_label(d, p):
    return f"{p['name']}({p['nh']})経由"


def _set_txt(d, keys):
    m = {p["key"]: p for p in d["paths"]}
    return "・".join(_e_label(d, m[k]) for k in keys)


def _read_eigrp(d, rnd):
    """搭載される経路の**集合**を選ばせる。錯乱肢はすべて実在の誤読に対応。"""
    inst = d["_installed"]
    m = {p["key"]: p for p in d["paths"]}
    fdsucc = efs.fd_succ(d["paths"])
    lim = d["variance"] * fdsucc
    fs = efs.all_fs(d["paths"])

    def why_excluded(key):
        p = m[key]
        if d["_roles"][key] == "non_fc":
            return (f"{_e_label(d, p)}は、フィージビリティの条件を満たさない"
                    f"(RD {p['rd']} が、サクセサの FD {fdsucc} 以上である)。")
        return (f"{_e_label(d, p)}は、FD {efs.fd(p)} が variance の範囲"
                f"({d['variance']} × {fdsucc} = {lim})を超えている。")

    # 錯乱肢の候補(すべて「実在の誤読」に対応させる)
    cands = [
        # ①FD が倍率の範囲内なら全部乗る= FC を確認しない誤り(本題の罠)
        ([p["key"] for p in d["paths"] if efs.fd(p) <= lim],
         "FD が variance の範囲に収まっていても、フィージビリティの条件"
         "(RD が、現在のサクセサの FD **より小さい**こと)を満たさない経路は、"
         "搭載されない。"),
        # ②FS はすべて乗る= 倍率の範囲を確認しない誤り
        ([d["_succ"]] + fs,
         "フィージブル・サクセサであっても、その FD が variance × サクセサの "
         f"FD({d['variance']} × {fdsucc} = {lim})を超えるものは、搭載されない。"),
        # ③サクセサのみ
        ([d["_succ"]],
         "variance が構成されているため、条件を満たす不等コストのパスも"
         "搭載される。"),
        # ④トポロジ表に出ている全経路
        ([p["key"] for p in d["paths"]],
         "トポロジ・テーブルに現れるすべての経路が、搭載されるわけではない。"),
        # ⑤サクセサを数え落とす誤り(FS だけが載ると読む)
        (fs, "サクセサ自身は、常に搭載される。"),
    ]
    # ⑥載らない経路を 1 本ずつ足した集合(近似値型のひっかけ)
    for p in sorted((x for x in d["paths"] if x["key"] not in inst),
                    key=efs.fd):
        cands.append((inst + [p["key"]], why_excluded(p["key"])))
    # ⑦載る経路を 1 本ずつ落とした集合
    for k in inst:
        if len(inst) > 1:
            cands.append(([x for x in inst if x != k],
                          f"{_e_label(d, m[k])}は、"
                          + ("サクセサであり、常に搭載される。"
                             if k == d["_succ"] else
                             "フィージビリティの条件を満たし、かつ FD "
                             f"{efs.fd(m[k])} が範囲({lim})に収まっている。")))

    def why_missing(key):
        p = m[key]
        if key == d["_succ"]:
            return f"{_e_label(d, p)}はサクセサであり、常に搭載される。"
        return (f"{_e_label(d, p)}は、フィージビリティの条件を満たし、かつ "
                f"FD {efs.fd(p)} が範囲({lim})に収まっている。")

    def why_for(keys):
        """任意の集合に対する「なぜ違うか」を、最初の食い違いから機械生成する。"""
        s = set(keys)
        for p in sorted(d["paths"], key=efs.fd):
            if p["key"] in s and p["key"] not in inst:
                return why_excluded(p["key"])
        for k in inst:
            if k not in s:
                return why_missing(k)
        return "帰結と一致しない。"

    # ⑧ 総当たりの控え(principled な候補で 5 択に届かない盤面の保険)。
    #    why は why_for が盤面から機械生成するので、説明の正しさは保たれる。
    keys_all = [p["key"] for p in sorted(d["paths"], key=efs.fd)]
    for size in range(1, len(keys_all) + 1):
        for i in range(len(keys_all)):
            sub = keys_all[i:i + size]
            if len(sub) == size:
                cands.append((sub, None))

    def txt(keys):
        ks = [p["key"] for p in sorted(d["paths"], key=efs.fd)
              if p["key"] in set(keys)]
        return f"{_set_txt(d, ks)}の {len(ks)} 本が搭載される"

    out = [(txt(inst), True, "")]
    seen = {frozenset(inst)}
    for keys, why in cands:
        if len(out) >= 5:
            break
        fk = frozenset(keys)
        if not keys or fk in seen:
            continue
        seen.add(fk)
        out.append((txt(keys), False, why or why_for(keys)))
    if len(out) != 5:
        raise ValueError(f"pref read(eigrp): 錯乱肢が不足 kind={d['kind']}")
    rnd.shuffle(out)
    return out


def read_question(d):
    """設問文(gen_paper_mcq が埋める)。"""
    if d["fam"] == "ospf":
        return (f"{d['obs']} のルーティング・テーブルに、{d['pfx_len']} の経路"
                "として搭載されるものは、どれですか。(1つを選択してください)")
    return (f"{d['obs']} の EIGRP のプロセスに `variance {d['variance']}` が"
            f"構成された場合、{d['pfx_len']} に対して、ルーティング・"
            "テーブルに搭載される経路は、どれですか。(1つを選択してください)")


# --------------------------------------------------------------------------
# why 形 — 「決め手はどの段か」
# --------------------------------------------------------------------------
OSPF_WHY = {
    "type": "経路の型による選好(エリア内 > エリア間 > 外部タイプ1 > 外部タイプ2)",
    "metric": "メトリックの比較(小さいほうが選好される)",
    "fwd": "forward metric(ASBR までの内部のコスト)の比較",
}
EIGRP_WHY = {
    "fc": "フィージビリティの条件(RD が、現在のサクセサの FD より小さいこと)",
    "var": "variance による倍率の範囲(FD が variance × サクセサの FD 以下であること)",
    "fd": "FD の大小の比較",
    "hop": "ホップ数の比較",
    "ad": "アドミニストレーティブ・ディスタンスの比較",
    "bw": "最小の帯域幅の比較",
}


def why_target(d):
    """why 形の対象経路と「唯一の理由」。

    ★対象は「搭載されない理由が **ちょうど1つ**」の経路でなければならない。
    FC 不成立かつ倍率の範囲外の経路を選ぶと、正解が 2 つある設問になる。
    """
    lim = d["variance"] * efs.fd_succ(d["paths"])
    out = [p for p in d["paths"] if p["key"] not in d["_installed"]]
    for p in sorted(out, key=efs.fd):
        non_fc = d["_roles"][p["key"]] == "non_fc"
        out_range = efs.fd(p) > lim
        if non_fc != out_range:
            return p, ("fc" if non_fc else "var")
    raise ValueError("pref: why の理由が一意な経路がない")


def build_choices_why(d, rnd):
    if d["fam"] == "ospf":
        cor = OSPF_WHY[d["_step"]]
        pool = [(v, _why_no(d, k)) for k, v in OSPF_WHY.items()
                if k != d["_step"]]
        pool.append(("アドミニストレーティブ・ディスタンスの比較",
                     "いずれの経路も同一のプロトコル(OSPF)により学習されており、"
                     "アドミニストレーティブ・ディスタンスは 110 で同一である。"))
        pool.append(("広告元のルータ ID の比較",
                     "ルータ ID は、この盤面の選好には用いられない。"))
    else:
        _tgt, key = why_target(d)
        cor = EIGRP_WHY[key]
        pool = [(v, _why_no(d, k)) for k, v in EIGRP_WHY.items() if k != key]
    picks = rnd.sample(pool, 4)
    out = [(cor, True, "")] + [(t, False, w) for t, w in picks]
    rnd.shuffle(out)
    return out


def _why_no(d, k):
    if d["fam"] == "ospf":
        return {
            "type": "2 つの経路の型は同一であり、型では決着していない。",
            "metric": ("2 つの経路のメトリックでは決着していない"
                       if d["_step"] == "fwd" else
                       "メトリックの比較は、型の比較のあとに行われる。"),
            "fwd": "forward metric は、外部タイプ 2 の経路が同一のメトリックを"
                   "持つ場合にのみ用いられる。",
        }[k]
    return {
        "fc": "フィージビリティの条件は満たされている。",
        "var": "variance の範囲には収まっている。",
        "fd": "FD の大小は、この経路が搭載されない理由ではない"
              "(FD がより大きい経路が搭載されている場合がある)。",
        "hop": "EIGRP の既定のメトリックに、ホップ数は含まれない"
               "(ホップ数は最大値の制限にのみ用いられる)。",
        "ad": "いずれの経路も同一のプロセスにより学習されており、"
              "アドミニストレーティブ・ディスタンスは 90 で同一である。",
        "bw": "いずれの経路も、最小の帯域幅は同一である。",
    }[k]


def why_question(d):
    if d["fam"] == "ospf":
        m = {p["key"]: p for p in d["paths"]}
        w = m[d["_winner"]]
        return (f"{_o_label(d, w)}の経路が搭載されるという結果を、直接に"
                "決定づけているものは、どれですか。(1つを選択してください)")
    tgt, _key = why_target(d)
    d["_why_target"] = tgt["key"]
    return (f"{_e_label(d, tgt)}の経路が、`variance {d['variance']}` を"
            "構成しても搭載されない理由は、どれですか。"
            "(1つを選択してください)")


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
def selftest(n=60):
    import random
    ok = fail = 0
    seen = {k: 0 for k in KINDS}
    for kind in KINDS:
        for i in range(n):
            rnd = random.Random(9000 + i * 7)
            try:
                d = draw(rnd, kind=kind)
            except ValueError:
                continue
            seen[kind] += 1
            avail = forms_for(d)
            builders = {"read": build_choices_read, "why": build_choices_why,
                        "fix": build_choices_fix, "cause": build_choices_cause,
                        "allthat": build_choices_allthat}
            for form in sorted(avail):
                builder = builders[form]
                ch = builder(d, random.Random(i))
                if form == "allthat":
                    # ★数非明示: 正解数は 1 以上・全肢が盤面の実在の経路
                    if not (1 <= sum(1 for c in ch if c[1]) < len(ch)) \
                            or len(ch) < 4:
                        print(f"NG {kind}/allthat: 正解集合 "
                              f"{sum(1 for c in ch if c[1])}/{len(ch)}")
                        fail += 1
                    else:
                        ok += 1
                    continue
                if len(ch) != 5 or sum(1 for c in ch if c[1]) != 1:
                    print(f"NG {kind}/{form}: 選択肢構成 {len(ch)}択 "
                          f"正解{sum(1 for c in ch if c[1])}")
                    fail += 1
                    continue
                txts = [c[0] for c in ch]
                if len(set(txts)) != len(txts):
                    print(f"NG {kind}/{form}: 選択肢が重複")
                    fail += 1
                    continue
                # ★書式の指紋検査(実際に踏んだ欠陥): 正解肢だけ助詞前の空白が
                #   無い等、文面の作り方が違うと正解が形から割れる。
                bad = [t for t in txts
                       if form == "read" and "メトリック" in t
                       and not re.search(r"メトリック \d+ で、", t)]
                if bad:
                    print(f"NG {kind}/{form}: メトリック肢の書式不揃い {bad}")
                    fail += 1
                    continue
                ok += 1
            # 描画が例外なく通ること
            if d["fam"] == "ospf":
                ospf_db_external(d) if d["kind"] != "type_intra" else None
                ospf_border_routers(d)
                if d["kind"] == "type_intra":
                    ospf_db_summary(d)
            else:
                eigrp_topology(d, all_links=True)
                eigrp_topology(d, all_links=False)
                eigrp_route(d)
            read_question(d)
            why_question(d)
            cause_question(d)
            if "fix" in forms_for(d):
                fix_question(d)
            if "allthat" in forms_for(d):
                allthat_question(d)
    empty = [k for k, v in seen.items() if v == 0]
    print(f"pref selftest: OK={ok} NG={fail} 成立盤面={seen}")
    if empty:
        print(f"NG: 盤面が1つも成立しない kind={empty}")
        fail += 1
    return fail


if __name__ == "__main__":
    raise SystemExit(1 if selftest() else 0)
