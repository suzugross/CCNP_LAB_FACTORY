#!/usr/bin/env python3
"""EIGRP 集約×リーク 手段選択 紙面ファミリ (BL-095) — gen_paper_mcq.py の shape=leakmap 素材。

ユーザ手組みラボ「EIGRP leak-map」(2026-08-07) から発案。
「ブロックを集約しつつ特定の /32 だけ明細で届かせる」を、要件(制約)が正解の手段を
反転させる形で問う。挙動は全て実機確定表に基づく(poc/leakmap/README.md・IOL 17.15):

  - summary-address のみ                → 集約のみ(全明細抑止)
  - leak-map の route-map 未定義       → ★リークなし(「全リーク」ではない)
  - route-map 在り・参照リスト未定義   → ★全リーク
  - permit 節に match なし             → 全リーク
  - リストが成分に不一致               → リークなし
  - redistribute 投入成分のリーク      → 明細 D EX [170]・集約は D [90] のまま
  - match が標準 ACL                   → prefix-list と同様に機能
  - static Null0 + redistribute static → 集約 D EX・明細の抑止なし

3レバー分離(①投入=network/redistribute ②集約=summary-address/Null0静的
③リーク=leak-map のみ)が教育的核心。リスト・route-map はわざと乱立させ、
生きている参照チェーンの読解を課す(ユーザ要望)。
"""
import random

KINDS = ["no_leakmap", "rmap_undefined", "pl_undefined", "pl_wrong_prefix",
         "permit_no_match", "not_injected", "shared_map_wrong_target"]
# 要件世界: 正解の手段を反転させる制約
WORLDS = ["no_redist", "no_network_lo", "internal_only", "no_if_summary"]
ROLES = ["ADV", "RCV"]           # 広告側(被験) / 受信側

IN_MET = "[90/409600]"           # 実測値(Ethernet 直結・Lo /32)
EX_MET = "[170/409600]"          # 実測値(redistribute connected)
EX_STATIC_MET = "[170/281600]"   # 実測値(redistribute static→Null0 集約) V1

RM_POOL = ["RMAP01", "LEAK", "RM-LEAK", "MON-LEAK"]
PL_POOL = ["PL01", "PL-LEAK", "PL-MON", "MON32"]
ACL_POOL = [10, 15, 20, 30]


def _typo(name, rnd):
    """参照タイポ: ハイフン⇄アンダースコア・字消し等の紛らわしい変形。"""
    cands = []
    if "-" in name:
        cands += [name.replace("-", "_"), name.replace("-", "")]
    if name[-1].isdigit():
        cands.append(name[:-1] + str((int(name[-1]) + 1) % 10))
    cands.append(name + "S")
    return rnd.choice(cands)


def draw(rnd, kind=None, world=None):
    d = {"shape": "leakmap"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["world"] = world or rnd.choice(WORLDS)
    d["asn"] = rnd.choice([100, 200, 6571, 65100, rnd.randint(300, 64000)])
    # ブロック: /29(Lo 3〜5本) or /30(Lo 3本・ユーザラボ形)
    net = rnd.choice([f"10.{rnd.randint(1, 220)}.{rnd.randint(0, 250)}",
                      f"172.{rnd.randint(16, 31)}.{rnd.randint(0, 250)}",
                      f"192.168.{rnd.randint(0, 99)}"])
    d["wid"] = rnd.choice([29, 30])
    base = rnd.choice([0, 8, 16, 32] if d["wid"] == 29 else [0, 4, 8, 16])
    d["block"] = f"{net}.{base}"
    d["mask"] = "255.255.255.248" if d["wid"] == 29 else "255.255.255.252"
    n_lo = rnd.randint(3, 5) if d["wid"] == 29 else 3
    d["los"] = [f"{net}.{base + i}" for i in range(1, n_lo + 1)]
    ti = rnd.randrange(n_lo)
    d["target"] = d["los"][ti]                    # 監視用 Lo(リーク対象)
    d["other"] = d["los"][(ti + 1) % n_lo]        # 隣の Lo(誤リーク素材)
    # ブロック外の運用 Lo(集約対象外・常時広告)
    d["ops_lo"] = (f"10.{rnd.randint(221, 250)}.{rnd.randint(0, 250)}"
                   f".{rnd.randint(1, 250)}")
    d["link"] = f"10.{rnd.randint(1, 220)}.{rnd.randint(0, 250)}"  # .0/30
    while d["link"] in (net,):
        d["link"] = f"10.{rnd.randint(1, 220)}.{rnd.randint(0, 250)}"
    d["ifname"] = rnd.choice(["Ethernet0/0", "GigabitEthernet0/1"])
    # 生きている参照チェーンの一致手段(実機確定: どちらも機能する)
    d["mtype"] = rnd.choice(["pl", "acl"])
    d["rm_live"] = rnd.choice(RM_POOL)
    d["pl_live"] = rnd.choice(PL_POOL)
    d["acl_live"] = rnd.choice(ACL_POOL)
    # ★エコ形(BL-096③・ユーザ発案): redist_leak 候補の表面を
    #   「同一 route-map を redistribute と leak-map で共用・対象のみ投入」で描く
    d["eco"] = rnd.random() < 0.5
    names = ["RT01", "RT02"]
    rnd.shuffle(names)
    d["m"] = dict(zip(ROLES, names))
    d["roles"] = list(ROLES)
    _decoys(d, rnd)
    # 参照タイポ名(定義済みのどの名前とも衝突しないこと)
    taken = set(RM_POOL) | set(PL_POOL)
    d["rm_typo"] = _typo(d["rm_live"], rnd)
    d["pl_typo"] = _typo(d["pl_live"], rnd)
    while d["rm_typo"] in taken:
        d["rm_typo"] += "X"
    while d["pl_typo"] in taken:
        d["pl_typo"] += "X"
    verify_choices(d)
    return d


def _decoys(d, rnd):
    """乱立(ユーザ要望): 未参照のリスト/route-map を 2〜4 個仕込む。
    意味には影響しない(参照されない)ことをモデル上も保証する。"""
    rm_ghost = rnd.choice([x for x in RM_POOL if x != d["rm_live"]])
    pl_ghost = rnd.choice([x for x in PL_POOL if x != d["pl_live"]])
    pl_ghost2 = rnd.choice([x for x in PL_POOL
                            if x not in (d["pl_live"], pl_ghost)])
    acl_ghost = rnd.choice([x for x in ACL_POOL if x != d["acl_live"]])
    pool = [
        # ブロック全体を許可する未参照 PL(「全部漏らしたい人向け」の残骸)
        ("pl", pl_ghost, [f"{d['block']}/{d['wid']} le 32"]),
        # 対象を正しく許可しているのに未参照の PL(最も意地悪)
        ("pl", pl_ghost2, [f"{d['target']}/32"]),
        # 別の Lo を許可する未参照 ACL
        ("acl", acl_ghost, [d["other"]]),
        # 未参照 route-map(上の ghost PL を参照)
        ("rm", rm_ghost, [("permit", "pl", pl_ghost)]),
    ]
    d["ghosts"] = rnd.sample(pool, rnd.randint(2, 4))
    d["rm_ghost"], d["pl_ghost"] = rm_ghost, pl_ghost


# --------------------------------------------------------------------------
# 状態モデル
# st = { inject: [/32...], redist_conn: [prefixes]|None, redist_static: bool,
#        null0: bool, summary: {"leak": rm名|None}|None, dlist: [prefixes]|None,
#        rmaps: {名: [(action, mtype, ref)]}, pls: {名: [pfx/len]},
#        acls: {番号: [addr]} }
# --------------------------------------------------------------------------
def state(d):
    """現在(壊れている)状態を kind から組み立てる。"""
    k = d["kind"]
    st = {"inject": list(d["los"]) + [d["ops_lo"]], "redist_conn": None,
          "redist_rm": None, "redist_static": False, "null0": False,
          "summary": {"leak": d["rm_live"]}, "dlist": None,
          "rmaps": {}, "pls": {}, "acls": {}}
    live_ref = (("pl", d["pl_live"]) if d["mtype"] == "pl"
                else ("acl", d["acl_live"]))
    if k == "shared_map_wrong_target":
        # ★エコ形の編集副作用(実測 V5): 共用マップのリストが「別の Lo」を指す
        #   → 対象は投入ごと消える(明細もリークも無い)・別 Lo が D EX で漏れる
        st["inject"] = [d["ops_lo"]]
        st["redist_conn"] = [d["other"]]
        st["redist_rm"] = d["rm_live"]
        st["rmaps"][d["rm_live"]] = [("permit",) + live_ref]
        _def_list(st, live_ref, [f"{d['other']}/32"] if d["mtype"] == "pl"
                  else [d["other"]])
        for g in d["ghosts"]:
            typ, name, body = g
            {"pl": st["pls"], "acl": st["acls"]}.get(typ, st["rmaps"]) \
                .setdefault(name, body)
        return st
    if k == "no_leakmap":
        st["summary"] = {"leak": None}
    elif k == "rmap_undefined":
        # 参照はタイポ名(未定義)。紛らわしい ghost RM は _decoys が置く。
        st["summary"] = {"leak": d["rm_typo"]}
    elif k == "pl_undefined":
        st["rmaps"][d["rm_live"]] = [("permit", "pl", d["pl_typo"])]
    elif k == "pl_wrong_prefix":
        st["rmaps"][d["rm_live"]] = [("permit",) + live_ref]
        _def_list(st, live_ref, [f"{d['other']}/32"] if d["mtype"] == "pl"
                  else [d["other"]])
    elif k == "permit_no_match":
        st["rmaps"][d["rm_live"]] = [("permit", None, None)]
    elif k == "not_injected":
        st["inject"].remove(d["target"])
        st["rmaps"][d["rm_live"]] = [("permit",) + live_ref]
        _def_list(st, live_ref, [f"{d['target']}/32"] if d["mtype"] == "pl"
                  else [d["target"]])
    if k in ("no_leakmap", "rmap_undefined"):
        # 生きていない側にも「正しく見える」チェーンの部品を残す
        st["rmaps"].setdefault(d["rm_live"], [("permit",) + live_ref])
        _def_list(st, live_ref, [f"{d['target']}/32"] if d["mtype"] == "pl"
                  else [d["target"]])
    for g in d["ghosts"]:
        typ, name, body = g
        if typ == "pl":
            st["pls"].setdefault(name, body)
        elif typ == "acl":
            st["acls"].setdefault(name, body)
        else:
            st["rmaps"].setdefault(name, body)
    return st


def _def_list(st, ref, body):
    if ref[0] == "pl":
        st["pls"][ref[1]] = body
    else:
        st["acls"][ref[1]] = body


def _in_block(d, pfx):
    """pfx(/32 の IP 文字列)がブロックに含まれるか。"""
    def v(ip):
        a = [int(x) for x in ip.split(".")]
        return (a[0] << 24) | (a[1] << 16) | (a[2] << 8) | a[3]
    size = 1 << (32 - d["wid"])
    return v(d["block"]) <= v(pfx) < v(d["block"]) + size


def _list_matches(d, st, ref, pfx):
    """参照リストが /32 成分に一致するか。★未定義リスト participate= match-all(実測 E2)。"""
    mtype, name = ref
    if mtype == "pl":
        if name not in st["pls"]:
            return True                       # 未定義 → 全一致(実測)
        for ent in st["pls"][name]:
            if ent.endswith("le 32"):        # block/wid le 32 形
                if _in_block(d, pfx):
                    return True
            elif ent == f"{pfx}/32":
                return True
        return False
    if name not in st["acls"]:
        return True                           # 未定義 ACL → 全一致(実測系の対称)
    return pfx in st["acls"][name]


def _leaked(d, st, comps):
    """leak-map が通す成分の集合(実測ルールの写像)。"""
    if not st["summary"]:
        return set()
    lm = st["summary"]["leak"]
    if lm is None:
        return set()
    if lm not in st["rmaps"]:
        return set()                          # ★route-map 未定義 → リークなし(実測 E1)
    out = set()
    for pfx in comps:
        for ent in st["rmaps"][lm]:
            action, mtype, ref = ent[0], ent[1], ent[2] if len(ent) > 2 else None
            if mtype is None:                 # match なし → 全一致(実測 E3)
                hit = True
            else:
                hit = _list_matches(d, st, (mtype, ref), pfx)
            if hit:
                if action == "permit":
                    out.add(pfx)
                break
    return out


def recv(d, st):
    """RCV 側で観測される EIGRP 経路 {prefix: ("D"|"D EX", plen, metric)}。"""
    S = d["block"]
    comps_int = [p for p in st["inject"]]
    comps_ext = list(st["redist_conn"] or [])
    under = [p for p in comps_int + comps_ext if _in_block(d, p)]
    out = {}
    if st["summary"] and under:
        out[S] = ("D", d["wid"], IN_MET)      # 実測 V3: 成分が全て EX でも内部
        for p in _leaked(d, st, under):
            out[p] = (("D EX", 32, EX_MET) if p in comps_ext
                      else ("D", 32, IN_MET))
    else:
        for p in under:
            out[p] = (("D EX", 32, EX_MET) if p in comps_ext
                      else ("D", 32, IN_MET))
    if st["null0"] and st["redist_static"]:
        out[S] = ("D EX", d["wid"], EX_STATIC_MET)
    for p in comps_int + comps_ext:
        if not _in_block(d, p):
            out[p] = (("D EX", 32, EX_MET) if p in comps_ext
                      else ("D", 32, IN_MET))
    if st["dlist"] is not None:
        out = {p: v for p, v in out.items() if p in st["dlist"]}
    return out


# --------------------------------------------------------------------------
# 修正候補(最終状態)と要件適合
# --------------------------------------------------------------------------
def _conv_cli(d, key):
    """★状態収束 CLI: 現在(壊れた)状態に上乗せ適用しても、apply_cand の絶対状態に
    到達する行を組む(既存の summary/network の削除を含む)。モデルの評価
    (絶対状態)と、CLI 選択肢の適用結果が一致することの担保。"""
    a, w, ifn = d["asn"], d["mask"], d["ifname"]
    S = d["block"]
    cur = state(d)
    des = apply_cand(d, key)
    L = []
    for name, ents in sorted(des["pls"].items()):
        for i, e in enumerate(ents, 1):
            L.append(f"ip prefix-list {name} seq {i * 5} permit {e}")
    for name, ents in sorted(des["rmaps"].items()):
        for i, ent in enumerate(ents, 1):
            L.append(f"route-map {name} {ent[0]} {i * 10}")
            if ent[1] == "pl":
                L.append(f" match ip address prefix-list {ent[2]}")
    if des["null0"]:
        L.append(f"ip route {S} {w} Null0")
    dels = [p for p in cur["inject"] if p not in des["inject"]]
    adds = [p for p in des["inject"] if p not in cur["inject"]]
    # 既存 redistribute の撤去(現在状態が持つ場合のみ)。同名再入は IOS が置換する
    # ため、des 側が別 RM で redistribute する場合は明示の no は不要。
    del_redist = (cur["redist_conn"] is not None
                  and des["redist_conn"] is None)
    if dels or adds or del_redist or des["redist_conn"] is not None \
            or des["redist_static"] or des["dlist"] is not None:
        L.append(f"router eigrp {a}")
        L += [f" no network {p} 0.0.0.0" for p in dels]
        L += [f" network {p} 0.0.0.0" for p in adds]
        if del_redist:
            L.append(f" no redistribute connected route-map "
                     f"{cur.get('redist_rm') or 'RM-CONN'}")
        if des["redist_conn"] is not None:
            L.append(f" redistribute connected route-map "
                     f"{des.get('redist_rm') or 'RM-CONN'}")
        if des["redist_static"]:
            L.append(" redistribute static")
        if des["dlist"] is not None:
            L.append(f" distribute-list prefix PL-NEW out {ifn}")
    L.append(f"interface {ifn}")
    L.append(f" no ip summary-address eigrp {a} {S} {w}")
    if des["summary"]:
        lk = des["summary"]["leak"]
        L.append(f" ip summary-address eigrp {a} {S} {w}"
                 + (f" leak-map {lk}" if lk else ""))
    return L


def fix_candidates(d):
    """(key, 説明文, CLI行) — 最終状態。urpf 同様、kind は開始状態を決めるだけ。
    CLI は _conv_cli による状態収束形(既存構成の削除込み)。"""
    adv = d["m"]["ADV"]
    a, w = d["asn"], d["mask"]
    S, T = d["block"], d["target"]
    prose = {
        "network_leak":
            f"{adv} において、ブロックのループバックのすべてを network の"
            f"ステートメントによって EIGRP {a} へ参加させる。そして、集約を "
            f"`ip summary-address eigrp {a} {S} {w} leak-map RM-NEW` の形へ"
            f"構成し直し、RM-NEW は、{T}/32 を許可するところの"
            "プレフィックス・リストに一致させる",
        "redist_leak":
            (f"{adv} において、ブロックのループバックの network の"
             f"ステートメントを削除する。{T}/32 を許可するところの"
             "プレフィックス・リストに一致するルート・マップ RM-SHARED を"
             "作成し、`redistribute connected route-map RM-SHARED` によって"
             "対象を注入し、そして、**同じ** RM-SHARED を参照するところの "
             f"`ip summary-address eigrp {a} {S} {w} leak-map RM-SHARED` を"
             "構成する"
             if d.get("eco") else
             f"{adv} において、ブロックのループバックの network の"
             "ステートメントを削除し、それらを `redistribute connected "
             f"route-map` によって EIGRP {a} へ注入する。そして、集約を "
             f"`ip summary-address eigrp {a} {S} {w} leak-map RM-NEW` の形へ"
             f"構成し直し、RM-NEW は、{T}/32 を許可するところの"
             "プレフィックス・リストに一致させる"),
        "null0_static":
            f"{adv} において、インターフェイスの集約の構成、および、{T} を"
            "除くところのブロックのループバックの network のステートメントを"
            f"削除する。`ip route {S} {w} Null0` のスタティック・ルートを"
            f"作成し、それを EIGRP {a} へ再配送する",
        "summary_only":
            f"{adv} において、ブロックのループバックのすべてを network の"
            "ステートメントによって参加させ、そして、集約を "
            f"`ip summary-address eigrp {a} {S} {w}` の形(leak-map なし)へ"
            "構成し直す",
        "dlist_out":
            f"{adv} において、インターフェイスの集約の構成を削除し、"
            f"{T}/32 および {d['ops_lo']}/32 を許可するところの"
            "プレフィックス・リストを、distribute-list として "
            f"{d['ifname']} の out の方向に適用する",
        "wrong_target_leak":
            f"{adv} において、集約を `ip summary-address eigrp {a} {S} {w} "
            "leak-map RM-NEW` の形へ構成し直し、RM-NEW は、"
            f"{d['other']}/32 を許可するところのプレフィックス・リストに"
            "一致させる",
    }
    return [(key, prose[key], _conv_cli(d, key))
            for key in ("network_leak", "redist_leak", "null0_static",
                        "summary_only", "dlist_out", "wrong_target_leak")]


def apply_cand(d, key):
    """候補 key の最終状態(現在状態とは独立の絶対状態)。"""
    st = {"inject": [d["ops_lo"]], "redist_conn": None, "redist_rm": None,
          "redist_static": False, "null0": False, "summary": None, "dlist": None,
          "rmaps": {}, "pls": {}, "acls": {}}
    T = d["target"]
    if key == "network_leak":
        st["inject"] += list(d["los"])
        st["summary"] = {"leak": "RM-NEW"}
        st["rmaps"]["RM-NEW"] = [("permit", "pl", "PL-NEW")]
        st["pls"]["PL-NEW"] = [f"{T}/32"]
    elif key == "redist_leak":
        st["summary"] = {"leak": None}      # leak 名は下で分岐
        if d.get("eco"):
            # ★エコ形: 対象/32 のみ投入・redistribute と leak-map で同一 RM を共用
            #   (実測 V4: 集約 D [90] + 対象明細 D EX)
            st["redist_conn"] = [T]
            st["redist_rm"] = "RM-SHARED"
            st["summary"] = {"leak": "RM-SHARED"}
            st["rmaps"]["RM-SHARED"] = [("permit", "pl", "PL-SHARED")]
            st["pls"]["PL-SHARED"] = [f"{T}/32"]
        else:
            st["redist_conn"] = list(d["los"])
            st["redist_rm"] = "RM-CONN"
            st["summary"] = {"leak": "RM-NEW"}
            st["rmaps"]["RM-NEW"] = [("permit", "pl", "PL-NEW")]
            st["pls"]["PL-NEW"] = [f"{T}/32"]
            # redistribute が参照する選択チェーン(描画・CLI 用の定義)
            st["rmaps"]["RM-CONN"] = [("permit", "pl", "PL-CONN")]
            st["pls"]["PL-CONN"] = [f"{d['block']}/{d['wid']} le 32"]
    elif key == "null0_static":
        st["inject"].append(T)
        st["null0"] = st["redist_static"] = True
    elif key == "summary_only":
        st["inject"] += list(d["los"])
        st["summary"] = {"leak": None}
    elif key == "dlist_out":
        st["inject"] += list(d["los"])
        st["dlist"] = [T, d["ops_lo"]]
        st["pls"]["PL-NEW"] = [f"{T}/32", f"{d['ops_lo']}/32"]
    elif key == "wrong_target_leak":
        st["inject"] += list(d["los"])
        st["summary"] = {"leak": "RM-NEW"}
        st["rmaps"]["RM-NEW"] = [("permit", "pl", "PL-NEW")]
        st["pls"]["PL-NEW"] = [f"{d['other']}/32"]
    return st


def _works(d, st):
    """機能要件: 集約が届く・対象明細が届く・他の明細は抑止・運用 Lo が届く。"""
    r = recv(d, st)
    if d["block"] not in r or d["target"] not in r:
        return False
    if d["ops_lo"] not in r:
        return False
    others = [p for p in d["los"] if p != d["target"]]
    return not any(p in r for p in others)


def _complies(d, st):
    r = recv(d, st)
    w = d["world"]
    if w == "no_redist":
        return not (st["redist_conn"] or st["redist_static"])
    if w == "no_network_lo":
        return not any(p in st["inject"] for p in d["los"])
    if w == "internal_only":
        return (r.get(d["block"], ("",))[0] == "D"
                and r.get(d["target"], ("",))[0] == "D")
    return st["summary"] is None              # no_if_summary


def verify_choices(d):
    works, ok = [], []
    for key, _txt, _cli in fix_candidates(d):
        st = apply_cand(d, key)
        if _works(d, st):
            works.append(key)
            if _complies(d, st):
                ok.append(key)
    if len(ok) != 1:
        raise ValueError(f"leakmap 一意性違反: kind={d['kind']} "
                         f"world={d['world']} works={works} ok={ok}")
    if len(works) < 2:
        raise ValueError(f"leakmap 直る候補不足: works={works}")
    d["_correct_key"] = ok[0]
    d["_works"] = works
    # 現在状態が「壊れている」ことのモデル検証(read 形の healthy を除く)
    if d["kind"] in KINDS and _works(d, state(d)):
        raise ValueError(f"leakmap: kind={d['kind']} が壊れていない")


# --------------------------------------------------------------------------
# 選択肢(fix / cause / read)
# --------------------------------------------------------------------------
WHY = {
    "network_leak": "", "redist_leak": "", "null0_static": "",
    "summary_only": "集約のみが広告され、対象のホストの明細のルートが受信されない。",
    "dlist_out": "集約のルートが生成されず、要件を満たさない"
                 "(distribute-list は、集約を作成しない)。",
    "wrong_target_leak": "対象とは異なるところのホストの明細が広告され、"
                         "対象のホストの明細は受信されない。",
}
WHY_BY_WORLD = {
    "no_redist": {
        "redist_leak": "ルートの再配送を使用しており、要件に適合しない。",
        "null0_static": "ルートの再配送を使用しており、要件に適合しない。"},
    "no_network_lo": {
        "network_leak": "ブロックのループバックを network のステートメントに"
                        "よって参加させており、要件に適合しない。",
        "null0_static": "ブロックのループバックを network のステートメントに"
                        "よって参加させており、要件に適合しない。"},
    "internal_only": {
        "redist_leak": "リークされる明細が EIGRP の外部のルート(AD 170)として"
                       "受信され、要件に適合しない。",
        "null0_static": "集約が EIGRP の外部のルート(AD 170)として受信され、"
                        "要件に適合しない。"},
    "no_if_summary": {
        "network_leak": "インターフェイスにおける集約の構成を使用しており、"
                        "要件に適合しない。",
        "redist_leak": "インターフェイスにおける集約の構成を使用しており、"
                       "要件に適合しない。"},
}


def _why(d, key):
    return WHY_BY_WORLD[d["world"]].get(key) or WHY[key]


def build_choices_fix(d, rnd):
    correct = d["_correct_key"]
    cands = fix_candidates(d)
    # 6候補は多いので 5 に絞る(正解+機能する代替2+機能しない2をベースに抽選)
    keys = [k for k, _t, _c in cands]
    keep = set(d["_works"]) | {correct}
    losers = [k for k in keys if k not in keep]
    keep |= set(rnd.sample(losers, min(2, len(losers))))
    c = [(txt, key == correct, "" if key == correct else _why(d, key), cli)
         for key, txt, cli in cands if key in keep]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


CLAIMS = {
    "no_leakmap": "集約の構成において、leak-map のパラメータが指定されていない",
    "rmap_undefined": "leak-map が参照しているところの名前のルート・マップが、"
                      "定義されていない",
    "pl_undefined": "ルート・マップが参照しているところの名前のリストが、"
                    "定義されていない",
    "pl_wrong_prefix": "リストにおいて許可されているアドレスが、対象の"
                       "ループバックのアドレスと異なっている",
    "permit_no_match": "ルート・マップの permit のエントリに、match の"
                       "ステートメントが存在しない",
    "not_injected": "対象のループバックのネットワークが、EIGRP のプロセスへ"
                    "参加させられていない",
    "shared_map_wrong_target": "再配布が参照しているところのリストにおいて、"
                               "対象のループバックのアドレスが許可されていない",
}
REFUTES = {
    "no_leakmap": "示されている集約の構成には、leak-map のパラメータが"
                  "指定されている。",
    "rmap_undefined": "参照されているところの名前のルート・マップは、"
                      "定義されている。",
    "pl_undefined": "参照されているところの名前のリストは、定義されている。",
    "pl_wrong_prefix": "リストのエントリは、対象のループバックのアドレスに"
                       "一致している。",
    "permit_no_match": "ルート・マップの permit のエントリには、match の"
                       "ステートメントが存在する。",
    "not_injected": "示されている構成のとおり、対象のネットワークは EIGRP の"
                    "プロセスへ参加させられている。",
    "shared_map_wrong_target": "示されている構成に、redistribute の"
                               "ステートメントは存在しない。",
}
# cause 形で「同時に真」になり得る claim の排他(正解の一意性)
CAUSE_EXCLUDE = {
    # 共用マップ形では「リストの許可対象が違う」「対象がプロセスへ未参加」も
    # 事実として真になるため、錯乱肢に混ぜない
    "shared_map_wrong_target": {"pl_wrong_prefix", "not_injected"},
}
CROSS = [
    ("EIGRP の auto-summary が有効にされており、明細の広告に影響している",
     "示されている構成に auto-summary は存在しない(既定で無効である)。"),
    ("distribute-list によって、当該のインターフェイスからの広告が"
     "フィルタされている",
     "示されている構成に、distribute-list のステートメントは存在しない。"),
    ("EIGRP のスタブ・ルーティングの構成によって、広告が制限されている",
     "示されている構成に、eigrp stub のステートメントは存在しない。"),
    ("集約のメトリックの計算に失敗しており、集約そのものが広告されていない",
     "受信側の経路テーブルに、集約のルートは存在している。"),
]
CROSS_ACL = ("ルート・マップの match において、プレフィックス・リストではなく"
             "標準のアクセス・リストが使用されている",
             "leak-map のルート・マップにおける標準のアクセス・リストの一致は、"
             "有効に機能する。")


def build_choices_cause(d, rnd):
    kind = d["kind"]
    others = [k for k in KINDS
              if k != kind and k not in CAUSE_EXCLUDE.get(kind, ())]
    c = [(CLAIMS[kind], True, "")]
    c += [(CLAIMS[k], False, REFUTES[k]) for k in rnd.sample(others, 3)]
    cross = list(CROSS)
    # ACL チェーンの盤面でのみ「ACL だから動かない」という偽因果を混ぜられる
    if d["mtype"] == "acl" and d["kind"] not in ("pl_undefined",):
        cross.append(CROSS_ACL)
    c += [(t, False, why) for t, why in rnd.sample(cross, 2)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def read_variants(d):
    """read 形(逆引き): 正解の受信テーブル + 紛らわしい別挙動のテーブル群。
    描画後に重複排除するため多めに返す(ラベル付き)。"""
    cur = recv(d, state(d))
    alts = []
    st = state(d)
    st["summary"] = {"leak": None}
    alts.append(("集約のみ(リークなし)", recv(d, st)))
    st = state(d)
    st["summary"] = {"leak": "RM-ALL"}
    st["rmaps"]["RM-ALL"] = [("permit", None, None)]
    alts.append(("全リーク", recv(d, st)))
    st = state(d)
    st["summary"] = None
    alts.append(("集約なし(全明細)", recv(d, st)))
    st = state(d)                              # 意図どおり動いた場合(健全)
    st["summary"] = {"leak": "RM-OK"}
    st["rmaps"]["RM-OK"] = [("permit", "pl", "PL-OK")]
    st["pls"]["PL-OK"] = [f"{d['target']}/32"]
    if d["target"] not in st["inject"]:
        st["inject"].append(d["target"])
    alts.append(("健全動作(集約+対象明細)", recv(d, st)))
    st = state(d)                              # 別の明細が漏れる形
    st["summary"] = {"leak": "RM-OK"}
    st["rmaps"]["RM-OK"] = [("permit", "pl", "PL-OK")]
    st["pls"]["PL-OK"] = [f"{d['other']}/32"]
    alts.append(("別明細のリーク", recv(d, st)))
    return cur, alts
