#!/usr/bin/env python3
"""OSPFv3 ⇄ EIGRPv6 相互再配送「C1↔C2 を通すには」紙面ファミリ (BL-098) —
gen_paper_mcq.py の shape=v6redist 素材。

ユーザ手組みラボ「IPv6redistribute01」(2026-08-08)から発案。
盤面は単独 ASBR による双方向の相互再配送で、**再配送は動いているのに客先 LAN が
届かない**状態を起点に、「C1↔C2 を通すには何をするか」を**要件(制約)が正解の手段を
反転させる**形で問う(gen_paper_pbr / gen_paper_leakmap の被覆エンジン方式)。

    C1 ──── RA ──────── RT-C ──────── RB ──── C2
      C1LAN     OTRAN    (ASBR)  ETRAN    C2LAN
      └─ OSPFv3 area 0 ─┘        └─ EIGRP named AS ─┘

挙動は全て実機確定表に基づく(poc/v6redist/README.md・IOL 17.15):

  - 基線: 両方向とも通るのは include-connected が拾った**自分の足元のリンクだけ**
  - route-map 節を書かずに redistribute を再発行 → ★**route-map は外れない**(マージ)
  - route-map ごと未定義 → **全拒否** / 参照 prefix-list 未定義 → **全許可**
  - include-connected 由来の経路も **route-map の適用を受ける**
  - EIGRP 側 redistribute の metric 省略 → **広告ゼロ**(default-metric で救済可)
  - af-interface の shutdown 解除 → トランジットが EX[170] → **D[90]**
  - match internal は OSPF 外部を落とす / metric-type 1 はコストが累積
  - default-information originate は **always 必須**(→ OE2 [110/1])
  - EIGRP summary-address ::/0 は more-specific を全抑止 + 自身に AD5 Null0
  - 中継だけの静的では**クライアントに伝播しない**(広告と到達は別)
  - 症状3値: `% No valid route` / `..`(片方向だけ修理) / `!!`
"""
import random

# 現在(壊れている)状態の種別。
# ★いずれも「その1点を直せば C1↔C2 が回復する」十分原因であること(cause 形の一意性)。
#   no_incl(include-connected 欠落)は**単独では成立しない**ため種別から外してある:
#   客先 LAN は学習経路であって connected ではないので、include-connected の有無は
#   トランジットの見え方しか変えない(実測 E4 の「全滅」は PL がトランジットのみ許可
#   していたこととの合わせ技)。錯乱肢(CLAIMS)としてのみ使う。
KINDS = ["pl_transit_only", "pl_one_side", "rm_typo", "no_metric",
         "rm_deny_first"]

# 要件世界: 正解の手段を反転させる制約
WORLDS = ["hide_transit", "filter_frozen", "detail_static", "default_only",
          "explicit_only", "internal_ad", "e1_type", "pass_external"]

# 「形」を問う世界だけに投入する候補(他の世界では等価解が並立するため出さない)
WORLD_SHAPE_CAND = {"internal_ad": "afif_up_pl", "e1_type": "pl_add_mt1",
                    "pass_external": "pl_add_matchext"}

# 実測メトリック(IOL 17.15)
MET_EX_RB, MET_EX_C2 = 1536000, 2048000      # EIGRP 側 1ホップ / 2ホップ
MET_OE2 = 20                                  # OSPF E2 は経路上で不変
MET_DEF_OSPF = 1                              # default-information originate
AD = {"D": 90, "EX": 170, "OE1": 110, "OE2": 110, "S": 1}

RM_POOL = ["OMAP01", "EMAP01", "RM-OSPF", "RM-EIGRP", "REDIST-MAP", "MAP-IN"]
PL_POOL = ["O544", "E5400", "PL-OSPF", "PL-EIGRP", "PL-REDIST", "PL-CORE"]


def _typo(name, rnd):
    """参照タイポ: ハイフン⇄アンダースコア・末尾字の増減など紛らわしい変形。"""
    c = []
    if "-" in name:
        c += [name.replace("-", "_"), name.replace("-", "")]
    if name[-1].isdigit():
        c.append(name[:-1] + str((int(name[-1]) + 1) % 10))
    c.append(name + "1")
    return rnd.choice(c)


def _hx(rnd):
    """IPv6 らしい 16 進のグループ(A/1A/544 等の紛らわしさを意図的に作る)。"""
    return rnd.choice(["1", "2", "A", "B", "1A", "2A", "10", "20", "AA", "1:1",
                       "C", "1C"])


def draw(rnd, kind=None, world=None):
    d = {"shape": "v6redist"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["world"] = world or rnd.choice(WORLDS)
    d["ospf_pid"] = rnd.choice([1, 10, 100, 544, 6500, rnd.randint(2, 999)])
    d["eigrp_as"] = rnd.choice([1, 100, 5400, 65001, rnd.randint(2, 65000)])
    d["eigrp_name"] = rnd.choice(["NAMED", "CORE", "WAN", "LAB"])
    # 4 つの /64。重複しないように引き当てる
    seen, seg = set(), []
    while len(seg) < 5:
        s = f"2001:DB8:{_hx(rnd)}:{_hx(rnd)}::"
        if s not in seen:
            seen.add(s)
            seg.append(s)
    d["c1lan"], d["otran"], d["etran"], d["c2lan"], d["ext"] = seg
    d["m"] = {"ASBR": "RT-C", "RA": "RA", "RB": "RB", "C1": "C1", "C2": "C2"}
    # ★2 つを独立に抽選するため、RT-C だけ Ethernet と GigabitEthernet が
    #   混在することがある(他機は Ethernet 固定)。IOL 実機には Gi は無いので
    #   実機とは離れるが、**本番試験のエキシビットらしい紛らわしさ**として
    #   ユーザ判断でこのまま残す(2026-08-08 確認済・揃えないこと)。
    d["oif"] = rnd.choice(["Ethernet0/0", "GigabitEthernet0/0"])
    d["eif"] = rnd.choice(["Ethernet0/1", "GigabitEthernet0/1"])
    d["rid_ospf"] = f"{rnd.randint(1, 9)}.{rnd.randint(1, 9)}." \
                    f"{rnd.randint(1, 9)}.{rnd.randint(1, 9)}"
    d["rid_eigrp"] = f"{rnd.randint(1, 9)}.{rnd.randint(1, 9)}." \
                     f"{rnd.randint(1, 9)}.{rnd.randint(1, 9)}"
    d["metric"] = rnd.choice(["10000 100 255 1 1500", "1000 10 255 1 1500",
                              "100000 100 255 1 1500"])
    d["e1_metric"] = rnd.choice([100, 500, 1000])
    # 生きている参照チェーン(OSPF→EIGRP 用 / EIGRP→OSPF 用)
    d["rm_o2e"] = rnd.choice(RM_POOL)
    d["rm_e2o"] = rnd.choice([x for x in RM_POOL if x != d["rm_o2e"]])
    d["pl_o2e"] = rnd.choice(PL_POOL)
    d["pl_e2o"] = rnd.choice([x for x in PL_POOL if x != d["pl_o2e"]])
    d["rm_typo_o2e"] = _typo(d["rm_o2e"], rnd)
    d["broken_side"] = rnd.choice(["o2e", "e2o"])     # 片側故障の向き
    _decoys(d, rnd)
    if world is None:
        d["world"] = rnd.choice(compatible_worlds(d) or WORLDS)
    return d


def compatible_worlds(d):
    """この故障種で正解が一意に立つ要件世界だけを返す。

    ★例: `default_only`(明細を持たない)は、現在状態で既に対向の明細が漏れている
    種別とは両立しない。デフォルトの配布は OSPF 側の**既存の明細を消さない**ため
    (実測 E12: EIGRP 側は summary-address が more-specific を全抑止するが、
    OSPF 側は default-information originate をしてもトランジットの明細が残る)。
    """
    out = []
    for w in WORLDS:
        try:
            verify_choices(dict(d, world=w))
            out.append(w)
        except ValueError:
            pass
    return out


def _decoys(d, rnd):
    """乱立(ユーザ要望): 未参照のリスト/route-map を 2〜4 個仕込む。
    参照されないことをモデル上も保証する(意味に影響しない)。"""
    used = {d["rm_o2e"], d["rm_e2o"], d["pl_o2e"], d["pl_e2o"]}
    rm_g = [x for x in RM_POOL if x not in used]
    pl_g = [x for x in PL_POOL if x not in used]
    rm_ghost = rnd.choice(rm_g)
    pl_ghost, pl_ghost2 = rnd.sample(pl_g, 2)
    pool = [
        # 「全部通したい人」の残骸(未参照)
        ("pl", pl_ghost, ["::/0 le 64"]),
        # 客先 LAN を正しく許可しているのに未参照(最も意地悪)
        ("pl", pl_ghost2, [d["c1lan"] + "/64", d["c2lan"] + "/64"]),
        # 未参照 route-map(上の ghost PL を参照)
        ("rm", rm_ghost, [("permit", pl_ghost)]),
        # トランジットだけを許可する未参照 PL
        ("pl", rnd.choice(pl_g), [d["otran"] + "/64"]),
    ]
    d["ghosts"] = rnd.sample(pool, rnd.randint(2, 4))
    d["rm_ghost"], d["pl_ghost"] = rm_ghost, pl_ghost


# --------------------------------------------------------------------------
# 状態モデル
#   o2e = OSPF→EIGRP(EIGRP named の topology base 配下)
#   e2o = EIGRP→OSPF(ospfv3 の address-family 配下)
# --------------------------------------------------------------------------
def _blank():
    return {
        "o2e": {"on": True, "match": {"internal"}, "metric": True,
                "default_metric": False, "rm": None, "incl": True},
        "e2o": {"on": True, "mtype": 2, "metric": None, "rm": None,
                "incl": True},
        "afif_shut": True,          # EIGRP は OSPF 側リンクで喋らない
        "def_orig": None,           # OSPFv3 default-information originate
        "eigrp_def": False,         # EIGRP af-interface summary-address ::/0
        "static": {"RA": [], "RB": [], "C1": [], "C2": []},
        "pls": {}, "rmaps": {},
    }


def state(d):
    """現在(壊れている)状態を kind から組み立てる。"""
    k = d["kind"]
    st = _blank()
    st["o2e"]["rm"], st["e2o"]["rm"] = d["rm_o2e"], d["rm_e2o"]
    # 基線: 双方向とも「自分の足元のトランジットだけ」を許可する PL
    st["rmaps"][d["rm_o2e"]] = [("permit", d["pl_o2e"])]
    st["rmaps"][d["rm_e2o"]] = [("permit", d["pl_e2o"])]
    st["pls"][d["pl_o2e"]] = [d["otran"] + "/64"]
    st["pls"][d["pl_e2o"]] = [d["etran"] + "/64"]

    if k == "pl_one_side":
        # 片側だけ客先 LAN を許可 → NOROUTE と 0% の非対称が出る
        if d["broken_side"] == "o2e":
            st["pls"][d["pl_e2o"]].append(d["c2lan"] + "/64")
        else:
            st["pls"][d["pl_o2e"]].append(d["c1lan"] + "/64")
    elif k == "rm_typo":
        # 参照先がタイポ(未定義)→ ★全拒否。紛らわしい ghost RM は _decoys が置く。
        # PL は双方とも客先 LAN を許可済み = タイポだけが唯一の阻害要因になる
        st["o2e"]["rm"] = d["rm_typo_o2e"]
        st["pls"][d["pl_o2e"]].append(d["c1lan"] + "/64")
        st["pls"][d["pl_e2o"]].append(d["c2lan"] + "/64")
    elif k == "no_metric":
        # EIGRP 側の metric 欠落 → ★広告ゼロ。PL は両方とも客先 LAN を許可済み
        st["o2e"]["metric"] = False
        st["pls"][d["pl_o2e"]].append(d["c1lan"] + "/64")
        st["pls"][d["pl_e2o"]].append(d["c2lan"] + "/64")
    elif k == "rm_deny_first":
        # seq 影: 先頭の deny 節が客先 LAN を先取りする
        st["rmaps"][d["rm_o2e"]] = [("deny", d["pl_ghost"]),
                                    ("permit", None)]
        st["pls"][d["pl_ghost"]] = [d["c1lan"] + "/64"]
        st["rmaps"][d["rm_e2o"]] = [("deny", d["pl_e2o"]),
                                    ("permit", None)]
        st["pls"][d["pl_e2o"]] = [d["c2lan"] + "/64"]
    for typ, name, body in d["ghosts"]:
        (st["pls"] if typ == "pl" else st["rmaps"]).setdefault(name, body)
    return st


# --------------------------------------------------------------------------
# 転送モデル(実機確定表の写像)
# --------------------------------------------------------------------------
def _rm_pass(st, rmname, pfx):
    """route-map による通過判定(★実測 E7/E8 の非対称を実装)。

    - rmname が None      → フィルタ無し(通す)
    - rmname が**未定義** → ★全拒否
    - 節を順に評価: ref が None(match 無し) → 全一致 /
      ref が**未定義リスト** → ★全一致 / 定義済み → 収録プレフィクスに一致。
      最初に一致した節の action で決定。どの節にも一致しなければ暗黙 deny。
    """
    if rmname is None:
        return True
    ents = st["rmaps"].get(rmname)
    if ents is None:
        return False                       # ★器ごと無い → 全拒否
    for act, ref in ents:
        if ref is None:
            hit = True                     # match 無し permit → 全一致
        else:
            body = st["pls"].get(ref)
            if body is None:
                hit = True                 # ★中身が空振り → 全一致
            else:
                hit = any(e.split()[0] == pfx + "/64" or e.startswith("::/0")
                          for e in body)
        if hit:
            return act == "permit"
    return False                           # 暗黙 deny


def into_eigrp(d, st):
    """EIGRP ドメインへ入るプレフィクス {pfx: code}。"""
    o = st["o2e"]
    out = {}
    if o["on"] and (o["metric"] or o["default_metric"]):
        cands = []
        if "internal" in o["match"]:
            cands.append(d["c1lan"])                  # OSPF 内部(O)
        if "external" in o["match"]:
            cands.append(d["ext"])                    # OSPF 外部(OE2)
        if o["incl"]:
            cands.append(d["otran"])                  # connected
        out = {p: "EX" for p in cands if _rm_pass(st, o["rm"], p)}
    if not st["afif_shut"]:
        # EIGRP がその IF で有効 → connected がネイティブ内部経路として広告される
        out[d["otran"]] = "D"
    if st["eigrp_def"]:
        # summary-address ::/0 は more-specific を全抑止(実測 E12)
        out = {"::": "D"}
    return out


def into_ospf(d, st):
    """OSPF ドメインへ入るプレフィクス {pfx: code}。"""
    e = st["e2o"]
    out = {}
    if e["on"]:
        cands = [d["c2lan"]]                          # EIGRP 内部(D)
        if e["incl"]:
            cands.append(d["etran"])                  # connected
        code = "OE1" if e["mtype"] == 1 else "OE2"
        out = {p: code for p in cands if _rm_pass(st, e["rm"], p)}
    if st["def_orig"] and (st["def_orig"]["always"] or st["eigrp_def"]):
        # RT-C 自身が ::/0 を持たない限り always が要る(実測 E11)。
        # eigrp_def は RT-C に Null0 の ::/0 を作るため always 不要になる
        out["::"] = "OE2"
    return out


def _ospf_met(d, st, pfx, code, node):
    if pfx == "::":
        return MET_DEF_OSPF
    if code == "OE1":
        m = st["e2o"]["metric"] or d["e1_metric"]
        return m + (10 if node == "RA" else 20)       # ★E1 はコストが累積(実測)
    return MET_OE2                                    # E2 は経路上で不変


def routes(d, st):
    """各ノードの経路表 {node: {pfx: (code, ad, metric)}}(ドメイン越えの分のみ)。"""
    tbl = {n: {} for n in ("C1", "RA", "RB", "C2")}
    for p, code in into_ospf(d, st).items():
        for n in ("RA", "C1"):
            tbl[n][p] = (code, AD[code], _ospf_met(d, st, p, code, n))
    for p, code in into_eigrp(d, st).items():
        tbl["RB"][p] = (code, AD[code], MET_EX_RB)
        tbl["C2"][p] = (code, AD[code], MET_EX_C2)
    # RA が OSPFv3 へ注入している 外部の ルート(OSPF ドメイン内では常に見える)
    tbl["C1"][d["ext"]] = ("OE2", 110, MET_OE2)
    for n, pfxs in st["static"].items():
        for p in pfxs:
            tbl[n][p] = ("S", 1, 0)
    return tbl


# 各ノードが自ドメイン内で元から知っているプレフィクス
def _native(d, node):
    return ([d["c1lan"], d["otran"]] if node in ("C1", "RA")
            else [d["etran"], d["c2lan"]])


def _has(d, tbl, node, dst):
    return (dst in _native(d, node) or dst in tbl[node]
            or "::" in tbl[node])


def pings(d, st):
    """(C1→C2, C2→C1)。実測どおり NOROUTE / 0% / 100% の3値。"""
    tbl = routes(d, st)
    fwd = _has(d, tbl, "C1", d["c2lan"]) and _has(d, tbl, "RA", d["c2lan"])
    rev = _has(d, tbl, "C2", d["c1lan"]) and _has(d, tbl, "RB", d["c1lan"])
    def one(src, dst_lan, ok):
        if not _has(d, tbl, src, dst_lan):
            return "NOROUTE"
        return "100%" if (fwd and rev) else "0%"
    return (one("C1", d["c2lan"], fwd), one("C2", d["c1lan"], rev))


# --------------------------------------------------------------------------
# 修正候補(最終状態)と要件適合
# --------------------------------------------------------------------------
# explicit = 「明示的に許可したものだけが再配送される」性質(将来の追加が自動で漏れない)。
# 手段そのものの性質なので、これだけは差分から導けず宣言で持つ。
EXPLICIT = {"pl_add", "pl_replace", "static_full", "static_mid", "rm_reissue",
            "afif_up_pl", "pl_add_mt1", "pl_add_matchext"}


def cand_meta(d, key):
    """★候補の性質は「現在状態との差分」から導出する(宣言で持つと、提示する
    CLI と要件適合の判定がずれる)。"""
    cur, des = state(d), apply_cand(d, key)
    filt = (cur["pls"] != des["pls"] or cur["rmaps"] != des["rmaps"]
            or cur["o2e"] != des["o2e"] or cur["e2o"] != des["e2o"])
    added = {n: [p for p in des["static"].get(n, [])
                 if p not in cur["static"].get(n, [])]
             for n in ("RA", "RB", "C1", "C2")}
    return dict(
        filt=filt,
        other=any(added.values()),          # 静的は全て RT-C 以外に置かれる
        static=any(added.values()),
        igp_default=(cur["def_orig"] != des["def_orig"]
                     or cur["eigrp_def"] != des["eigrp_def"]),
        explicit=key in EXPLICIT,
    )
CORE_KEYS = ["pl_add", "pl_replace", "rm_detach", "pl_delete", "default_route",
             "static_full", "static_mid", "rm_reissue", "rm_detach_nomet"]


def _both_pl_open(d, st, replace=False):
    """両方向の PL を客先 LAN が通るように整える。"""
    o = [d["c1lan"] + "/64"] if replace else [d["otran"] + "/64",
                                              d["c1lan"] + "/64"]
    e = [d["c2lan"] + "/64"] if replace else [d["etran"] + "/64",
                                              d["c2lan"] + "/64"]
    st["pls"][d["pl_o2e"]], st["pls"][d["pl_e2o"]] = o, e
    st["rmaps"][d["rm_o2e"]] = [("permit", d["pl_o2e"])]
    st["rmaps"][d["rm_e2o"]] = [("permit", d["pl_e2o"])]
    st["o2e"]["rm"], st["e2o"]["rm"] = d["rm_o2e"], d["rm_e2o"]
    st["o2e"]["metric"] = True


def _clone(st):
    out = dict(st)
    out["o2e"], out["e2o"] = dict(st["o2e"]), dict(st["e2o"])
    out["pls"] = {k: list(v) for k, v in st["pls"].items()}
    out["rmaps"] = {k: list(v) for k, v in st["rmaps"].items()}
    out["static"] = {k: list(v) for k, v in st["static"].items()}
    return out


def apply_cand(d, key):
    """候補 key を**現在状態へ適用した後**の状態。

    ★絶対状態(素の基線+手段)ではなく現在状態からの差分にすること。さもないと
    「フィルタに触らない」はずの手段(静的・デフォルト)の最終状態が、故障している
    route-map を暗黙に修復してしまい、提示する CLI と要件適合の判定がずれる。
    """
    st = _clone(state(d))
    if key == "rm_reissue":
        # ★実測 E16: route-map 節を書かずに再発行しても行はマージされ、
        #   route-map は外れない = 現在状態から何も変わらない
        return st
    if key == "pl_add":
        _both_pl_open(d, st)
    elif key == "pl_replace":
        _both_pl_open(d, st, replace=True)
    elif key in ("rm_detach", "rm_detach_nomet"):
        st["o2e"]["rm"] = st["e2o"]["rm"] = None
        st["o2e"]["metric"] = (key == "rm_detach")   # ★nomet は広告ゼロ(実測 E5)
    elif key == "pl_delete":
        st["pls"].pop(d["pl_o2e"], None)             # ★未定義リスト参照=全許可
        st["pls"].pop(d["pl_e2o"], None)
    elif key == "default_route":
        st["def_orig"] = {"always": True}
        st["eigrp_def"] = True
    elif key in ("static_full", "static_mid"):
        st["static"]["RA"] = [d["c2lan"]]
        st["static"]["RB"] = [d["c1lan"]]
        if key == "static_full":
            st["static"]["C1"] = ["::"]
            st["static"]["C2"] = ["::"]
    elif key == "afif_up_pl":
        _both_pl_open(d, st)
        st["afif_shut"] = False                      # ★トランジットが D[90] に
    elif key == "pl_add_mt1":
        _both_pl_open(d, st)
        st["e2o"]["mtype"] = 1
        st["e2o"]["metric"] = d["e1_metric"]
    elif key == "pl_add_matchext":
        _both_pl_open(d, st)
        st["o2e"]["match"] = {"internal", "external"}
        st["pls"][d["pl_o2e"]].append(d["ext"] + "/64")
    return st


def _works(d, st):
    """機能要件: C1↔C2 が双方向で疎通すること。"""
    return pings(d, st) == ("100%", "100%")


def _complies(d, st, key):
    """要件世界への適合(機能要件は別途 _works で判定)。"""
    w, mt = d["world"], cand_meta(d, key)
    tbl = routes(d, st)
    if w == "hide_transit":
        return (d["otran"] not in tbl["RB"] and d["otran"] not in tbl["C2"]
                and d["etran"] not in tbl["RA"] and d["etran"] not in tbl["C1"])
    if w == "filter_frozen":
        return not mt["filt"] and not mt["other"]
    if w == "detail_static":
        # RT-C の再配送/フィルタは凍結・IGP へのデフォルト生成も禁止
        return not mt["filt"] and not mt["igp_default"]
    if w == "default_only":
        # 対向ドメインの明細を、いずれのルータも保持しないこと
        return (d["c2lan"] not in tbl["RA"] and d["c2lan"] not in tbl["C1"]
                and d["c1lan"] not in tbl["RB"] and d["c1lan"] not in tbl["C2"])
    if w == "explicit_only":
        return (mt["explicit"] and not mt["static"] and not mt["igp_default"]
                and d["otran"] in tbl["RB"] and d["etran"] in tbl["RA"])
    if w == "internal_ad":
        return tbl["RB"].get(d["otran"], ("",))[0] == "D"
    if w == "e1_type":
        return tbl["C1"].get(d["c2lan"], ("",))[0] == "OE1"
    # pass_external
    return d["ext"] in tbl["RB"]


def cand_keys(d):
    """候補キー列。「形」を問う世界のみ専用候補を1つ足す(等価解の並立を防ぐ)。"""
    keys = list(CORE_KEYS)
    extra = WORLD_SHAPE_CAND.get(d["world"])
    if extra:
        keys.append(extra)
    return keys


def verify_choices(d):
    works, ok = [], []
    for key in cand_keys(d):
        st = apply_cand(d, key)
        if _works(d, st):
            works.append(key)
            if _complies(d, st, key):
                ok.append(key)
    if len(ok) != 1:
        raise ValueError(f"v6redist 一意性違反: kind={d['kind']} "
                         f"world={d['world']} works={works} ok={ok}")
    if len(works) < 2:
        raise ValueError(f"v6redist 直る候補不足: works={works}")
    if _works(d, state(d)):
        raise ValueError(f"v6redist: kind={d['kind']} が壊れていない")
    d["_correct_key"] = ok[0]
    d["_works"] = works
    return d


# --------------------------------------------------------------------------
# CLI(★状態収束形): 現在の壊れた状態へ上乗せ適用しても apply_cand の絶対状態に
# 到達する行を組む。★redistribute は再発行でマージされ route-map が外れないため
# (実測 E16)、変更時は必ず `no redistribute ...` を前置する。
# --------------------------------------------------------------------------
def _redist_o2e_line(d, o):
    m = " ".join(sorted(o["match"], reverse=True))     # internal (external)
    s = f"redistribute ospf {d['ospf_pid']} match {m}"
    if o["metric"]:
        s += f" metric {d['metric']}"
    if o["rm"]:
        s += f" route-map {o['rm']}"
    if o["incl"]:
        s += " include-connected"
    return s


def _redist_e2o_line(d, e):
    s = f"redistribute eigrp {d['eigrp_as']}"
    if e["metric"]:
        s += f" metric {e['metric']}"
    if e["mtype"] == 1:
        s += " metric-type 1"
    if e["rm"]:
        s += f" route-map {e['rm']}"
    if e["incl"]:
        s += " include-connected"
    return s


def _conv_cli(d, key):
    cur, des = state(d), apply_cand(d, key)
    if key == "rm_reissue":
        # ★見た目は正しいが効かない形(route-map 節を省いた再発行・no を前置しない)
        o = dict(cur["o2e"]); o["rm"] = None
        e = dict(cur["e2o"]); e["rm"] = None
        return [f"router eigrp {d['eigrp_name']}",
                f" address-family ipv6 unicast autonomous-system {d['eigrp_as']}",
                "  topology base",
                f"   {_redist_o2e_line(d, o)}",
                "  exit-af-topology", " exit-address-family", "exit",
                f"router ospfv3 {d['ospf_pid']}", " address-family ipv6 unicast",
                f"  {_redist_e2o_line(d, e)}", " exit-address-family", "exit"]
    L = []
    for name in sorted(set(cur["pls"]) | set(des["pls"])):
        if cur["pls"].get(name) == des["pls"].get(name):
            continue
        L.append(f"no ipv6 prefix-list {name}")
        for i, e in enumerate(des["pls"].get(name, []), 1):
            L.append(f"ipv6 prefix-list {name} seq {i * 5} permit {e}")
    for name in sorted(set(cur["rmaps"]) | set(des["rmaps"])):
        if cur["rmaps"].get(name) == des["rmaps"].get(name):
            continue
        L.append(f"no route-map {name}")
        for i, (act, ref) in enumerate(des["rmaps"].get(name, []), 1):
            L.append(f"route-map {name} {act} {i * 10}")
            if ref:
                L.append(f" match ipv6 address prefix-list {ref}")
    redist_o2e = cur["o2e"] != des["o2e"]
    afif = cur["afif_shut"] != des["afif_shut"]
    edef = cur["eigrp_def"] != des["eigrp_def"]
    if redist_o2e or afif or edef:
        L += [f"router eigrp {d['eigrp_name']}",
              f" address-family ipv6 unicast autonomous-system {d['eigrp_as']}"]
        if afif:
            L += [f"  af-interface {d['oif']}",
                  ("   no shutdown" if not des["afif_shut"] else "   shutdown"),
                  "  exit-af-interface"]
        if edef:
            L += [f"  af-interface {d['eif']}", "   summary-address ::/0",
                  "  exit-af-interface"]
        if redist_o2e:
            # ★no を前置しない限り route-map / metric / match は残る(実測 E16)
            L += ["  topology base",
                  f"   no redistribute ospf {d['ospf_pid']}",
                  f"   {_redist_o2e_line(d, des['o2e'])}",
                  "  exit-af-topology"]
        L += [" exit-address-family", "exit"]
    osp = []
    if cur["e2o"] != des["e2o"]:
        osp += [f"  no redistribute eigrp {d['eigrp_as']}",
                f"  {_redist_e2o_line(d, des['e2o'])}"]
    if cur["def_orig"] != des["def_orig"] and des["def_orig"]:
        osp.append("  default-information originate"
                   + (" always" if des["def_orig"]["always"] else ""))
    if osp:
        L += [f"router ospfv3 {d['ospf_pid']}", " address-family ipv6 unicast"] \
            + osp + [" exit-address-family", "exit"]
    for n in ("RA", "RB", "C1", "C2"):
        adds = [p for p in des["static"].get(n, [])
                if p not in cur["static"].get(n, [])]
        if not adds:
            continue
        L.append(f"! --- {n} ---")
        for p in adds:
            nh = {"RA": d["otran"] + "1", "RB": d["etran"] + "1",
                  "C1": d["c1lan"] + "1", "C2": d["c2lan"] + "1"}[n]
            dst = "::/0" if p == "::" else p + "/64"
            L.append(f"ipv6 route {dst} {nh}")
    return L or ["! (変更なし)"]


PROSE = {
    "pl_add": "双方の プレフィックス・リスト に対して、対向のドメインの"
              "クライアントの ネットワーク を許可するところの エントリ を追加する"
              "(既存の エントリ は、そのまま残される)",
    "pl_replace": "双方の プレフィックス・リスト を、対向のドメインの"
                  "クライアントの ネットワーク のみを許可するところの内容へ"
                  "置き換える(トランジット の エントリ は削除される)",
    "rm_detach": "双方の redistribute の ステートメント を、いったん削除したうえで、"
                 "route-map の 指定を伴わない形で、再度、構成する"
                 "(メトリック の 指定は維持される)",
    "pl_delete": "route-map から参照されているところの プレフィックス・リスト を、"
                 "双方とも削除する",
    "default_route": "OSPFv3 において デフォルト の ルート を生成し、そして、"
                     "EIGRP 側の インターフェイス において ::/0 の 集約を構成する",
    "static_full": "RA および RB に対向の ネットワーク への スタティック・ルート を"
                   "構成し、そして、C1 および C2 に 既定の ゲートウェイ を構成する",
    "static_mid": "RA および RB に対して、対向の ネットワーク への"
                  " スタティック・ルート を構成する",
    "rm_reissue": "双方の redistribute の ステートメント を、route-map の 指定を"
                  "伴わない形で、あらためて入力する",
    "rm_detach_nomet": "双方の redistribute の ステートメント を、いったん削除した"
                       "うえで、route-map および メトリック の 指定を伴わない形で、"
                       "再度、構成する",
    "afif_up_pl": "双方の プレフィックス・リスト に対向の クライアントの"
                  " ネットワーク を追加し、そして、EIGRP の af-interface における"
                  " shutdown を解除する",
    "pl_add_mt1": "双方の プレフィックス・リスト に対向の クライアントの"
                  " ネットワーク を追加し、そして、OSPFv3 への 再配送 を"
                  " メトリック・タイプ 1 で構成する",
    "pl_add_matchext": "双方の プレフィックス・リスト に対向の クライアントの"
                       " ネットワーク を追加し、そして、EIGRP への 再配送 の"
                       " match の 条件に external を加える",
}


def fix_candidates(d):
    return [(k, PROSE[k], _conv_cli(d, k)) for k in cand_keys(d)]


# 不正解の理由(因果は書かず、観測される事実のみを述べる)
WHY = {
    "static_mid": "RA および RB は対向の ネットワーク の ルート を保持するが、"
                  "C1 および C2 の 経路テーブル は変化せず、疎通は回復しない。",
    "rm_reissue": "redistribute の ステートメント は既存の行と統合され、"
                  "route-map の 指定は解除されない。経路テーブル は変化しない。",
    "rm_detach_nomet": "EIGRP へ 再配送 される ルート が 1 つも広告されず、"
                       "RB および C2 の 経路テーブル は空のままとなる。",
}
WHY_BY_WORLD = {
    "hide_transit": {
        "pl_add": "トランジット の ネットワーク が、対向の ドメイン において"
                  "引き続き受信され、要件に適合しない。",
        "rm_detach": "トランジット の ネットワーク が、対向の ドメイン において"
                     "引き続き受信され、要件に適合しない。",
        "pl_delete": "すべての ルート が 再配送 され、トランジット の"
                     " ネットワーク も受信され、要件に適合しない。",
        "default_route": "EIGRP 側の トランジット の ネットワーク が、OSPFv3 の"
                         " ドメイン において引き続き受信され、要件に適合しない。",
        "static_full": "トランジット の ネットワーク が、対向の ドメイン において"
                       "引き続き受信され、要件に適合しない。"},
    "filter_frozen": {
        "pl_add": "プレフィックス・リスト を変更しており、要件に適合しない。",
        "pl_replace": "プレフィックス・リスト を変更しており、要件に適合しない。",
        "rm_detach": "redistribute の 構成を変更しており、要件に適合しない。",
        "pl_delete": "プレフィックス・リスト を変更しており、要件に適合しない。",
        "static_full": "RT-C 以外の デバイス の 構成を変更しており、"
                       "要件に適合しない。"},
    "detail_static": {
        "pl_add": "再配送 に対する フィルタ の 構成を変更しており、"
                  "要件に適合しない。",
        "pl_replace": "再配送 に対する フィルタ の 構成を変更しており、"
                      "要件に適合しない。",
        "rm_detach": "再配送 の 構成を変更しており、要件に適合しない。",
        "pl_delete": "再配送 に対する フィルタ の 構成を変更しており、"
                     "要件に適合しない。",
        "default_route": "ルーティング・プロトコル において デフォルト の"
                         " ルート を生成しており、要件に適合しない。"},
    "default_only": {
        "pl_add": "対向の ドメイン の 明細の ルート が 経路テーブル に現れ、"
                  "要件に適合しない。",
        "pl_replace": "対向の ドメイン の 明細の ルート が 経路テーブル に現れ、"
                      "要件に適合しない。",
        "rm_detach": "対向の ドメイン の 明細の ルート が 経路テーブル に現れ、"
                     "要件に適合しない。",
        "pl_delete": "対向の ドメイン の 明細の ルート が 経路テーブル に現れ、"
                     "要件に適合しない。",
        "static_full": "RA および RB が 対向の ネットワーク の 明細の ルート を"
                       "保持しており、要件に適合しない。"},
    "explicit_only": {
        "pl_replace": "トランジット の ネットワーク が 対向の ドメイン において"
                      "受信されなくなり、要件に適合しない。",
        "rm_detach": "以後に追加されるところの ネットワーク が、明示的な許可を"
                     "伴わずに 再配送 され、要件に適合しない。",
        "pl_delete": "以後に追加されるところの ネットワーク が、明示的な許可を"
                     "伴わずに 再配送 され、要件に適合しない。",
        "default_route": "デフォルト の ルート による到達であり、要件に適合しない。",
        "static_full": " スタティック・ルート を使用しており、要件に適合しない。"},
    "internal_ad": {
        "pl_add": "トランジット の ネットワーク が EIGRP の 外部の ルート"
                  "(アドミニストレーティブ・ディスタンス 170)として受信され、"
                  "要件に適合しない。",
        "pl_replace": "トランジット の ネットワーク が受信されず、"
                      "要件に適合しない。",
        "rm_detach": "トランジット の ネットワーク が EIGRP の 外部の ルート"
                     "として受信され、要件に適合しない。",
        "pl_delete": "トランジット の ネットワーク が EIGRP の 外部の ルート"
                     "として受信され、要件に適合しない。",
        "default_route": "トランジット の ネットワーク が受信されず、"
                         "要件に適合しない。",
        "static_full": "トランジット の ネットワーク が EIGRP の 外部の ルート"
                       "として受信され、要件に適合しない。"},
    "e1_type": {
        "pl_add": "対向の ネットワーク が タイプ 2 の 外部の ルート として"
                  "受信され、要件に適合しない。",
        "pl_replace": "対向の ネットワーク が タイプ 2 の 外部の ルート として"
                      "受信され、要件に適合しない。",
        "rm_detach": "対向の ネットワーク が タイプ 2 の 外部の ルート として"
                     "受信され、要件に適合しない。",
        "pl_delete": "対向の ネットワーク が タイプ 2 の 外部の ルート として"
                     "受信され、要件に適合しない。",
        "default_route": "対向の ネットワーク の 明細の ルート が受信されず、"
                         "要件に適合しない。",
        "static_full": "対向の ネットワーク が OSPFv3 の ルート として"
                       "受信されず、要件に適合しない。"},
    "pass_external": {
        "pl_add": "OSPFv3 の 外部の ルート が EIGRP の ドメイン において"
                  "受信されず、要件に適合しない。",
        "pl_replace": "OSPFv3 の 外部の ルート が EIGRP の ドメイン において"
                      "受信されず、要件に適合しない。",
        "rm_detach": "OSPFv3 の 外部の ルート が EIGRP の ドメイン において"
                     "受信されず、要件に適合しない。",
        "pl_delete": "OSPFv3 の 外部の ルート が EIGRP の ドメイン において"
                     "受信されず、要件に適合しない。",
        "default_route": "OSPFv3 の 外部の ルート が EIGRP の ドメイン において"
                         "受信されず、要件に適合しない。",
        "static_full": "OSPFv3 の 外部の ルート が EIGRP の ドメイン において"
                       "受信されず、要件に適合しない。"},
}


def _why(d, key):
    return WHY_BY_WORLD.get(d["world"], {}).get(key) or WHY.get(key, "")


def build_choices_fix(d, rnd):
    correct = d["_correct_key"]
    cands = fix_candidates(d)
    keys = [k for k, _t, _c in cands]
    keep = set(d["_works"]) | {correct}
    losers = [k for k in keys if k not in keep]
    keep |= set(rnd.sample(losers, min(2, len(losers))))
    # 5 択を超えないよう、正解以外の「機能する」候補から間引く
    while len(keep) > 5:
        # ★集合をそのままたどると **反復順が起動ごとに変わり非決定的**になる
        #   (文字列の hash に PYTHONHASHSEED が効くため)。安定した順序の
        #   `keys` 側をたどること。2026-08-08 に mixed の決定性検査で検出。
        drop = [k for k in keys if k in keep and k != correct and k in d["_works"]]
        if not drop:
            break
        keep.discard(rnd.choice(drop))
    c = [(txt, key == correct, "" if key == correct else _why(d, key), cli)
         for key, txt, cli in cands if key in keep]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# cause 形(原因特定)
# --------------------------------------------------------------------------
CLAIMS = {
    "pl_transit_only": "双方の プレフィックス・リスト が、隣接している リンク の"
                       " ネットワーク のみを許可している",
    "pl_one_side": "一方の 方向 の プレフィックス・リスト のみが、対向の"
                   " クライアント の ネットワーク を許可している",
    "rm_typo": "redistribute が参照しているところの名前の route-map が、"
               "定義されていない",
    "no_metric": "EIGRP への redistribute の ステートメント において、"
                 " メトリック が指定されていない",
    "no_incl": "redistribute の ステートメント において、include-connected が"
               "指定されていない",
    "rm_deny_first": "route-map の 先頭の エントリ が、対向の クライアント の"
                     " ネットワーク を拒否している",
}
REFUTES = {
    "pl_transit_only": "少なくとも一方の プレフィックス・リスト は、対向の"
                       " クライアント の ネットワーク を許可している。",
    "pl_one_side": "いずれの 方向 の プレフィックス・リスト も、対向の"
                   " クライアント の ネットワーク を許可していない。",
    "rm_typo": "redistribute が参照しているところの route-map は、"
               "定義されている。",
    "no_metric": "EIGRP への redistribute の ステートメント には、"
                 " メトリック が指定されている。",
    "no_incl": "redistribute の ステートメント には、include-connected が"
               "指定されている。",
    "rm_deny_first": "route-map の エントリ に、deny の ステートメント は"
                     "存在しない。",
}
# cause 形で提示しうる claim の全体(KINDS ＋ 種別にはしない no_incl)
CLAIM_KEYS = list(KINDS) + ["no_incl"]


def _live_pl(st, rmname):
    """route-map が実際に参照している prefix-list の内容(無ければ None)。"""
    ents = st["rmaps"].get(rmname)
    if not ents:
        return None
    for _act, ref in ents:
        if ref is not None:
            return st["pls"].get(ref)
    return None


def claim_true(d, st, key):
    """★claim を現在状態に対して機械判定する。
    錯乱肢は「事実として偽」のものだけを採ることで、cause 形の正解を一意にする
    (手書きの排他表だと故障種を足したときに破綻するため)。"""
    o_pl = _live_pl(st, st["o2e"]["rm"])
    e_pl = _live_pl(st, st["e2o"]["rm"])
    o_ok = bool(o_pl) and any(x.startswith(d["c1lan"] + "/") for x in o_pl)
    e_ok = bool(e_pl) and any(x.startswith(d["c2lan"] + "/") for x in e_pl)
    # 「リストの中身」に関する claim は、参照チェーンが健全なときにのみ意味を持つ
    # (route-map が未定義・deny 節がある場合、阻害要因はリストの内容ではない)
    names = (st["o2e"]["rm"], st["e2o"]["rm"])
    chains_ok = (all(n in st["rmaps"] for n in names)
                 and not any(act == "deny" for n in names
                             for act, _ref in st["rmaps"].get(n, [])))
    if key == "pl_transit_only":
        return chains_ok and not o_ok and not e_ok
    if key == "pl_one_side":
        return chains_ok and (o_ok != e_ok)
    if key == "rm_typo":
        return (st["o2e"]["rm"] not in st["rmaps"]
                or st["e2o"]["rm"] not in st["rmaps"])
    if key == "no_metric":
        return not (st["o2e"]["metric"] or st["o2e"]["default_metric"])
    if key == "no_incl":
        return not st["o2e"]["incl"] or not st["e2o"]["incl"]
    # rm_deny_first
    return any(act == "deny"
               for name in (st["o2e"]["rm"], st["e2o"]["rm"])
               for act, _ref in st["rmaps"].get(name, []))

CROSS = [
    ("RT-C と 隣接の ルータ の 間で、ルーティング・プロトコル の 隣接関係 が"
     "確立されていない",
     "いずれの ドメイン においても、隣接する ネットワーク の ルート は"
     "受信されており、隣接関係 は確立されている。"),
    ("RT-C において ipv6 unicast-routing が有効にされていない",
     "RT-C は 双方の ドメイン の ルート を 経路テーブル に保持しており、"
     " IPv6 の ユニキャスト の ルーティング は有効である。"),
    ("双方の ドメイン の 間で ルーティング・ループ が発生しており、"
     " ルート が抑制されている",
     "再配送 を行うところの ルータ は 1 台のみであり、ループ の 経路は"
     "存在しない。"),
    ("アドミニストレーティブ・ディスタンス の 競合により、再配送 された ルート が"
     " 経路テーブル へ 導入されていない",
     "対向の ドメイン の ルート を提供するところの プロトコル は 1 つのみであり、"
     "競合は発生しない。"),
    ("C1 および C2 において、それぞれの ドメイン の ルーティング・プロトコル が"
     "構成されていない",
     "C1 および C2 は、自身の ドメイン の ルート を受信している。"),
]


def build_choices_cause(d, rnd):
    kind, st = d["kind"], state(d)
    if not claim_true(d, st, kind):
        raise ValueError(f"cause: 正解 claim が偽 kind={kind}")
    # ★事実として偽の claim だけを錯乱肢にする(同時に真=正解が割れるのを防ぐ)
    others = [k for k in CLAIM_KEYS
              if k != kind and not claim_true(d, st, k)]
    if len(others) < 3:
        raise ValueError(f"cause: 錯乱肢不足 kind={kind} others={others}")
    c = [(CLAIMS[kind], True, "")]
    c += [(CLAIMS[k], False, REFUTES[k]) for k in rnd.sample(others, 3)]
    c += [(t, False, why) for t, why in rnd.sample(CROSS, 2)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# 描画(実測書式に忠実)
# --------------------------------------------------------------------------
def _ll(d, node):
    """観測ルータから見た next-hop の リンクローカル(実測書式・d から決定的)。"""
    n = {"C1": 0x10, "RA": 0x20, "RB": 0x30, "C2": 0x40}[node]
    h = (sum(ord(c) for c in d["c1lan"] + d["otran"]) + n) % 0xF0
    return f"FE80::A8BB:CCFF:FE01:{h:02X}00"


def _if_of(d, node):
    """観測ノードから見た「コア方向」の出口 IF。C1/RA/RB/C2 は素の IOL で、
    いずれも Ethernet0/0 が ASBR 側を向く(RT-C の IF 名だけが seed で変わる)。"""
    return "Ethernet0/0"


def route_table(d, st, node):
    """`show ipv6 route <proto> | include ^X|via` の忠実な描画。"""
    tbl = routes(d, st)[node]
    dom = "ospf" if node in ("C1", "RA") else "eigrp"
    lines = []
    # IOS は ::/0 を先頭に、以降はアドレス順で並べる
    def _key(p):
        if p == "::":
            return (0,)
        return (1,) + tuple(int(x or "0", 16)
                            for x in p.rstrip(":").split(":")[:4])
    for p in sorted(tbl, key=_key):
        code, ad, met = tbl[p]
        if dom == "ospf" and code not in ("O", "OI", "OE1", "OE2"):
            continue
        if dom == "eigrp" and code not in ("D", "EX"):
            continue
        addr = "::/0" if p == "::" else p + "/64"
        lines.append(f"{code:<4}{addr} [{ad}/{met}]")
        lines.append(f"     via {_ll(d, node)}, {_if_of(d, node)}")
    return "\n".join(lines) if lines else "(no entries)"


def table_cmd(node):
    return (f"show ipv6 route ospf | include ^O|via" if node in ("C1", "RA")
            else "show ipv6 route eigrp | include ^D|^EX|via")


def ping_block(d, src, dst_addr, result, repeat=5):
    head = ("Type escape sequence to abort.\n"
            f"Sending {repeat}, 100-byte ICMP Echos to {dst_addr}, "
            "timeout is 2 seconds:")
    if result == "NOROUTE":
        body = "\n% No valid route for destination\nSuccess rate is 0 percent (0/1)"
    elif result == "0%":
        body = ("." * repeat) + f"\nSuccess rate is 0 percent (0/{repeat})"
    else:
        body = ("!" * repeat) + (f"\nSuccess rate is 100 percent "
                                 f"({repeat}/{repeat}), round-trip "
                                 "min/avg/max = 1/1/2 ms")
    return f"{src}# ping {dst_addr}\n{head}\n{body}"


def addr_of(d, node):
    return {"C1": d["c1lan"] + "2", "C2": d["c2lan"] + "2"}[node]


def trace_block(d, st):
    """C1→C2 と C2→C1 の ping 出力を並べた ブロック(★症状3値の読み分け)。"""
    p1, p2 = pings(d, st)
    return (ping_block(d, "C1", addr_of(d, "C2"), p1) + "\n\n"
            + ping_block(d, "C2", addr_of(d, "C1"), p2))


def read_variants(d):
    """read 形(逆引き): 観測ノードの経路表 + 紛らわしい別状態の経路表。"""
    node = "C1" if d["kind"] in ("pl_one_side", "no_metric") else "RB"
    cur = route_table(d, state(d), node)
    alts = []
    for label, key in (("フィルタを外した状態", "rm_detach"),
                       ("リストを置き換えた状態", "pl_replace"),
                       ("デフォルトのみを配布した状態", "default_route"),
                       ("リストを削除した状態", "pl_delete"),
                       ("メトリックを落とした状態", "rm_detach_nomet")):
        alts.append((label, route_table(d, apply_cand(d, key), node)))
    return node, cur, alts


def cfg_block(d, st):
    """ASBR の running-config 抜粋(乱立リスト込み・現在状態の忠実な描画)。"""
    L = [f"interface {d['oif']}",
         f" description === to {d['m']['RA']} ===",
         " no ip address",
         f" ipv6 address {d['otran']}1/64",
         " ipv6 enable",
         f" ipv6 ospf {d['ospf_pid']} area 0",
         "!",
         f"interface {d['eif']}",
         f" description === to {d['m']['RB']} ===",
         " no ip address",
         f" ipv6 address {d['etran']}1/64",
         " ipv6 enable",
         "!",
         f"router eigrp {d['eigrp_name']}",
         " !",
         f" address-family ipv6 unicast autonomous-system {d['eigrp_as']}",
         "  !"]
    if st["afif_shut"]:
        L += [f"  af-interface {d['oif']}", "   shutdown", "  exit-af-interface",
              "  !"]
    if st["eigrp_def"]:
        L += [f"  af-interface {d['eif']}", "   summary-address ::/0",
              "  exit-af-interface", "  !"]
    L.append("  topology base")
    if st["o2e"]["default_metric"]:
        L.append(f"   default-metric {d['metric']}")
    if st["o2e"]["on"]:
        L.append(f"   {_redist_o2e_line(d, st['o2e'])}")
    L += ["  exit-af-topology", f"  eigrp router-id {d['rid_eigrp']}",
          " exit-address-family", "!",
          f"router ospfv3 {d['ospf_pid']}", f" router-id {d['rid_ospf']}", " !",
          " address-family ipv6 unicast"]
    if st["def_orig"]:
        L.append("  default-information originate"
                 + (" always" if st["def_orig"]["always"] else ""))
    if st["e2o"]["on"]:
        L.append(f"  {_redist_e2o_line(d, st['e2o'])}")
    L += [" exit-address-family", "!"]
    for name in sorted(st["pls"]):
        for i, e in enumerate(st["pls"][name], 1):
            L.append(f"ipv6 prefix-list {name} seq {i * 5} permit {e}")
    L.append("!")
    for name in sorted(st["rmaps"]):
        for i, (act, ref) in enumerate(st["rmaps"][name], 1):
            L.append(f"route-map {name} {act} {i * 10}")
            if ref:
                L.append(f" match ipv6 address prefix-list {ref}")
    L.append("!")
    return "\n".join(L)


def topo_block(d):
    a, ra, rb = d["m"]["ASBR"], d["m"]["RA"], d["m"]["RB"]
    return "\n".join([
        "```",
        f"      <---- OSPFv3 {d['ospf_pid']} area 0 ---->"
        f"      <---- EIGRP {d['eigrp_name']} AS {d['eigrp_as']} ---->",
        f"  [C1]---(a)---[{ra}]---(b)---[{a}]---(c)---[{rb}]---(d)---[C2]",
        "",
        f"  (a) {d['c1lan']}/64     C1 = {d['c1lan']}2",
        f"  (b) {d['otran']}/64",
        f"  (c) {d['etran']}/64",
        f"  (d) {d['c2lan']}/64     C2 = {d['c2lan']}2",
        "",
        f"  OSPFv3 の ドメイン には、{ra} によって注入されたところの",
        f"  外部の ルート {d['ext']}/64 が存在する。",
        "```"])


WORLD_REQS = {
    "hide_transit": lambda d: [
        f"いずれの ドメイン の ルータ の 経路テーブル にも、対向する ドメイン の"
        f" トランジット の リンク の ネットワーク({d['otran']}/64 および "
        f"{d['etran']}/64)が、現れてはなりません。"],
    "filter_frozen": lambda d: [
        "再配送 に対する フィルタ(route-map および プレフィックス・リスト)の"
        " 構成は、監査の対象であるという理由により、変更されてはなりません。",
        f"{d['m']['ASBR']} 以外の デバイス に対する 構成の変更は、"
        "許可されていません。"],
    "detail_static": lambda d: [
        f"{d['m']['ASBR']} における 再配送 および フィルタ の 構成は、"
        "変更されてはなりません。",
        "ルーティング・プロトコル において デフォルト の ルート を生成することは、"
        "認められていません。"],
    "default_only": lambda d: [
        "いずれの ルータ も、対向する ドメイン の 明細の ルート を、"
        " 経路テーブル に保持してはなりません"
        "(到達は、デフォルト の ルート によって行われなければなりません)。"],
    "explicit_only": lambda d: [
        "明示的に許可されたところの ネットワーク のみが 再配送 されなければ"
        "なりません(以後に追加されるところの ネットワーク が、自動的に"
        " 再配送 されてはなりません)。",
        f"トランジット の リンク の ネットワーク({d['otran']}/64 および "
        f"{d['etran']}/64)は、引き続き、対向する ドメイン において"
        "受信されなければなりません。",
        " スタティック・ルート および デフォルト の ルート の 生成は、"
        "認められていません。"],
    "internal_ad": lambda d: [
        f"EIGRP の ドメイン において、{d['otran']}/64 は、EIGRP の 内部の"
        " ルート(アドミニストレーティブ・ディスタンス 90)として"
        "受信されなければなりません。"],
    "e1_type": lambda d: [
        f"C1 において、{d['c2lan']}/64 は、タイプ 1 の 外部の ルート として"
        "受信されなければなりません。"],
    "pass_external": lambda d: [
        f"OSPFv3 の ドメイン に存在するところの 外部の ルート({d['ext']}/64)も、"
        " EIGRP の ドメイン へ 配布されなければなりません。"],
}


def requirements(d):
    """要件(核 + 世界の制約)。番号付けは呼び出し側(finalize_reqs)が行う。"""
    return ["C1 と C2 は、相互に 通信 できなければなりません。"] \
        + WORLD_REQS[d["world"]](d)


def _set_side(d, st, side, permit_client):
    """片方向の参照チェーンを健全化し、客先 LAN を通す/通さないを決める。"""
    if side == "o2e":
        st["o2e"]["rm"] = d["rm_o2e"]
        st["o2e"]["metric"] = True
        st["rmaps"][d["rm_o2e"]] = [("permit", d["pl_o2e"])]
        st["pls"][d["pl_o2e"]] = [d["otran"] + "/64"] \
            + ([d["c1lan"] + "/64"] if permit_client else [])
    else:
        st["e2o"]["rm"] = d["rm_e2o"]
        st["rmaps"][d["rm_e2o"]] = [("permit", d["pl_e2o"])]
        st["pls"][d["pl_e2o"]] = [d["etran"] + "/64"] \
            + ([d["c2lan"] + "/64"] if permit_client else [])


def trace_variants(d):
    """trace 形: ping の 3 値(`% No valid route` / `..` / `!!`)の 組合せを問う。

    到達性の型を**明示的に**作り分ける(候補の写像から採ると組合せが重複して
    選択肢が畳まれるため)。いずれも実測で確認された 3 値の組合せのみ。
    """
    cur = trace_block(d, state(d))
    outs = []
    for label, o_ok, e_ok, cli_def in (
            ("双方向とも開通した状態", True, True, False),
            ("OSPFv3 の 方向 だけが開通した状態", False, True, False),
            ("EIGRP の 方向 だけが開通した状態", True, False, False),
            ("双方向とも不通の状態", False, False, False),
            ("クライアントにのみ既定ゲートウェイを置いた状態", False, False, True)):
        st = _clone(state(d))
        _set_side(d, st, "o2e", o_ok)
        _set_side(d, st, "e2o", e_ok)
        if cli_def:
            st["static"]["C1"], st["static"]["C2"] = ["::"], ["::"]
        outs.append((label, trace_block(d, st)))
    return cur, outs


# --------------------------------------------------------------------------
def _selftest(seeds=40):
    """モデル一意性の総当たり検証。
    ① world 明示: 成立しない (kind, world) を列挙(意味的に両立しない組がある)
    ② world 未指定(実際の出題経路): 必ず成立すること
    """
    import collections
    skip = collections.Counter()
    ok = tot = 0
    for k in KINDS:
        for w in WORLDS:
            for s in range(seeds):
                tot += 1
                d = draw(random.Random(s * 977 + 13), kind=k, world=w)
                try:
                    verify_choices(d)
                    rnd = random.Random(s)
                    assert sum(1 for x in build_choices_fix(d, rnd) if x[1]) == 1
                    assert sum(1 for x in build_choices_cause(d, rnd) if x[1]) == 1
                    assert [c for c in CLAIM_KEYS
                            if claim_true(d, state(d), c)] == [k]
                    read_variants(d)
                    _, alts = trace_variants(d)
                    assert len({t for _l, t in alts}) >= 3
                    ok += 1
                except (ValueError, AssertionError):
                    skip[f"{k}/{w}"] += 1
    print(f"[1] world 明示: {ok}/{tot}  成立しない組= {dict(skip)}")
    ok2 = 0
    dist = collections.Counter()
    for k in KINDS:
        for s in range(seeds * 3):
            d = draw(random.Random(s * 31 + 7), kind=k)
            verify_choices(d)
            rnd = random.Random(s)
            assert sum(1 for x in build_choices_fix(d, rnd) if x[1]) == 1
            assert sum(1 for x in build_choices_cause(d, rnd) if x[1]) == 1
            read_variants(d)
            trace_variants(d)
            cfg_block(d, state(d))
            dist[d["world"]] += 1
            ok2 += 1
    print(f"[2] world 未指定: {ok2}/{len(KINDS) * seeds * 3} (全て成立)")
    print(f"    世界の分布: {dict(sorted(dist.items()))}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seeds", type=int, default=40)
    a = ap.parse_args()
    if a.selftest:
        _selftest(a.seeds)
    else:
        ap.error("この モジュール は gen_paper_mcq.py --shape v6redist から使う"
                 "(単体では --selftest のみ)")
