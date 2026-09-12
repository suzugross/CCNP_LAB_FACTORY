#!/usr/bin/env python3
"""OSPF→BGP 再配送の範囲(match オプション) 紙面ファミリ (BL-163) —
gen_paper_mcq.py の shape=ospfbgp 素材。

定番題材派生。「BGP への OSPF 再配送は、既定ではエリア内/エリア間のルートだけ」を、
**結果の BGP テーブルから設定を逆算させる**形で問う。

★紙面専用: 挙動は実機確定表(poc/ospfbgp/README.md・IOL 17.15)の写像モデルから
決定的に生成する(実機展開・収集は行わない)。

盤面(固定・4 ルータ):
    RCV(BGP のみ) ─ DUT(BGP + OSPF) ─ ABR(OSPF・ASBR 兼 ABR) ─ EDGE(RIP)
  DUT から見た OSPF テーブルには 4 種が揃う:
    O(エリア内) / O IA(エリア間) / O E1 / O E2 ＋ 接続セグメント(エリア内)

状態モデル(実測の遷移規則がそのまま実装されている):
  state = 集合 S ⊆ {"i", "e1", "e2"}（空にならない）
  - `redistribute ospf P`(match 無し)     → S = {"i"}          ★リセット(マージではない)
  - `redistribute ospf P match <集合>`    → S = S ∪ <集合>      ★マージ(置換ではない)
  - `no redistribute ospf P match <集合>` → S = S - <集合>(空なら {"i"})
  表示形は S=={"i"} のときだけ素の `redistribute ospf P`。
"""
import random

# 現状の設定(=盤面) / 要件(=正解を反転させる世界)
KINDS = ["default_only", "ext_only", "int_ext1", "ext2_only"]
WORLDS = ["all", "internal_only", "ext1_only"]

STATE_OF = {"default_only": {"i"}, "ext_only": {"e1", "e2"},
            "int_ext1": {"i", "e1"}, "ext2_only": {"e2"}}
TARGET_OF = {"all": {"i", "e1", "e2"}, "internal_only": {"i"},
             "ext1_only": {"e1"}}
ORDER = ["i", "e1", "e2"]
LABEL = {"i": "internal", "e1": "external 1", "e2": "external 2"}

NAME_POOL = [("R1", "R2", "R3", "R4"), ("RT01", "RT02", "RT03", "RT04"),
             ("CE01", "PE01", "P01", "X01"), ("RA", "RB", "RC", "RD")]


def disp(pid, s):
    """状態集合 → running-config の表示形(実測どおり)。"""
    if s == {"i"}:
        return f"redistribute ospf {pid}"
    return (f"redistribute ospf {pid} match "
            + " ".join(LABEL[k] for k in ORDER if k in s))


def apply_cmd(s, cmd):
    """コマンド(下の CANDS のキー形式)を状態へ適用。実測の遷移規則。"""
    kind, arg = cmd
    if kind == "plain":
        return {"i"}                      # ★match 無しの再発行は既定へリセット
    if kind == "add":
        return set(s) | set(arg)          # ★マージ
    if kind == "del":
        out = set(s) - set(arg)
        return out or {"i"}
    if kind == "reset_add":               # no redistribute → 入れ直し
        return set(arg)
    raise ValueError(kind)


def cmd_lines(pid, cmd, af=True):
    kind, arg = cmd
    body = " ".join(LABEL[k] for k in ORDER if k in (arg or ()))
    if kind == "plain":
        return [f"redistribute ospf {pid}"]
    if kind == "add":
        return [f"redistribute ospf {pid} match {body}"]
    if kind == "del":
        return [f"no redistribute ospf {pid} match {body}"]
    return [f"no redistribute ospf {pid}",
            f"redistribute ospf {pid} match {body}"]


# 候補コマンド(選択肢の母集団)。正誤はモデル評価で決める(固定しない)。
CANDS = [("plain", None),
         ("add", ("i",)), ("add", ("e1",)), ("add", ("e2",)),
         ("add", ("e1", "e2")), ("add", ("i", "e1")), ("add", ("i", "e2")),
         ("add", ("i", "e1", "e2")),
         ("del", ("e1",)), ("del", ("e2",)),
         ("reset_add", ("e1",)), ("reset_add", ("e2",)),
         ("reset_add", ("i", "e1", "e2"))]


def draw(rnd, kind=None, world=None):
    d = {"shape": "ospfbgp"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["world"] = world or rnd.choice(WORLDS)
    if TARGET_OF[d["world"]] == STATE_OF[d["kind"]]:
        raise ValueError("既に要件を満たしている組合せ")
    d["m"] = dict(zip(("RCV", "DUT", "ABR", "EDGE"),
                      rnd.choice(NAME_POOL)))
    d["asn"] = rnd.choice([65000, 65001, 64512, 100, 200, rnd.randint(64512, 65534)])
    d["pid"] = rnd.choice([1, 2, 10, 20, 100])
    # アドレス群(第3オクテットを散らす)
    o3 = rnd.sample(range(1, 60), 3)
    base = rnd.choice([192, 172, 10])
    if base == 192:
        pfx = lambda x: f"192.168.{x}.0"      # noqa: E731
    elif base == 172:
        pfx = lambda x: f"172.{rnd.choice([16, 20, 24])}.{x}.0"   # noqa: E731
    else:
        pfx = lambda x: f"10.{rnd.choice([1, 2, 3])}.{x}.0"       # noqa: E731
    d["link_bgp"] = pfx(o3[0])         # RCV-DUT(BGP 区間)
    d["link_ospf"] = pfx(o3[1])        # DUT-ABR(OSPF 区間・エリア内)
    d["link_rip"] = pfx(o3[2])         # ABR-EDGE(RIP 区間)
    o3b = rnd.sample(range(60, 120), 4)
    d["net_o"] = pfx(o3b[0])           # O   (エリア内)
    d["net_oia"] = pfx(o3b[1])         # O IA(エリア間)
    d["net_e1"] = pfx(o3b[2])          # O E1
    d["net_e2"] = pfx(o3b[3])          # O E2
    d["area"] = rnd.choice([1, 2, 10])
    # メトリック(実測レンジ)
    d["m_o"] = rnd.choice([11, 20, 21, 30])
    d["m_ia"] = d["m_o"] + rnd.choice([0, 10])
    d["m_e1"] = rnd.choice([30, 40, 51])
    d["m_e2"] = rnd.choice([20, 100])
    d["ver"] = rnd.randint(3, 19)
    return d


# ---------------------------------------------------------------- 盤面の描画
def routes_in_bgp(d, s):
    """状態 → RCV の BGP テーブル行((net, metric, best) のリスト)。
    ★内部が入っていないと next-hop(OSPF 区間)が解決できず best にならない(実測)。"""
    best = "i" in s
    rows = []
    if "i" in s:
        rows.append((d["link_ospf"], 0, True, True))     # 最終列=自ネイバー経由
        rows.append((d["net_o"], d["m_o"], True, False))
        rows.append((d["net_oia"], d["m_ia"], True, False))
    if "e1" in s:
        rows.append((d["net_e1"], d["m_e1"], best, False))
    if "e2" in s:
        rows.append((d["net_e2"], d["m_e2"], best, False))
    return rows


def bgp_table(d, s):
    m = d["m"]
    nh_dut = f"{d['link_bgp'][:-1]}2"
    nh_abr = f"{d['link_ospf'][:-1]}3"
    L = [f"BGP table version is {d['ver']}, local router ID is "
         f"{d['link_bgp'][:-1]}1",
         "Status codes: s suppressed, d damped, h history, * valid, > best, "
         "i - internal, ",
         "              r RIB-failure, S Stale, m multipath, b backup-path, "
         "f RT-Filter, ",
         "              x best-external, a additional-path, c RIB-compressed, ",
         "Origin codes: i - IGP, e - EGP, ? - incomplete", "",
         "     Network          Next Hop            Metric LocPrf Weight Path"]
    for net, met, best, own in routes_in_bgp(d, s):
        mark = "*>i" if best else "* i"
        nh = nh_dut if own else nh_abr
        L.append(f" {mark}  {net:<16s} {nh:<19s} {met:>6d}    100      0 ?")
    if len(L) == 7:
        L.append("")
    return "\n".join(L)


def ospf_table(d):
    """DUT の OSPF テーブル(全状態で共通の入力)。"""
    nh = f"{d['link_ospf'][:-1]}3"
    return "\n".join([
        "Gateway of last resort is not set", "",
        f"O     {d['net_o']}/24 [110/{d['m_o']}] via {nh}, 00:41:12, Ethernet0/1",
        f"O IA  {d['net_oia']}/24 [110/{d['m_ia']}] via {nh}, 00:38:04, "
        "Ethernet0/1",
        f"O E1  {d['net_e1']}/24 [110/{d['m_e1']}] via {nh}, 00:12:37, "
        "Ethernet0/1",
        f"O E2  {d['net_e2']}/24 [110/{d['m_e2']}] via {nh}, 00:12:37, "
        "Ethernet0/1"])


def dut_cfg(d, s=None):
    s = STATE_OF[d["kind"]] if s is None else s
    p, m = d["pid"], d["m"]
    return "\n".join([
        f"router ospf {p}",
        f" router-id {d['link_ospf'][:-1]}2",
        f" network {d['link_ospf']} 0.0.0.255 area 0",
        "!",
        f"router bgp {d['asn']}",
        " bgp log-neighbor-changes",
        " no bgp default ipv4-unicast",
        f" neighbor {d['link_bgp'][:-1]}1 remote-as {d['asn']}",
        " !",
        " address-family ipv4",
        f"  {disp(p, s)}",
        f"  neighbor {d['link_bgp'][:-1]}1 activate",
        " exit-address-family"])


# ---------------------------------------------------------------- 選択肢
def works(d, cmd):
    """候補コマンドを適用した結果が要件を満たすか。"""
    return apply_cmd(STATE_OF[d["kind"]], cmd) == TARGET_OF[d["world"]]


def why_wrong(d, cmd):
    p = d["pid"]
    got = apply_cmd(STATE_OF[d["kind"]], cmd)
    want = TARGET_OF[d["world"]]
    miss = [LABEL[k] for k in ORDER if k in want - got]
    extra = [LABEL[k] for k in ORDER if k in got - want]
    if cmd[0] == "plain" and STATE_OF[d["kind"]] != {"i"}:
        head = ("`match` を伴わない再発行は、対象を既定(内部ルートのみ)へ"
                "**戻す**ため、現に設定されている外部ルートの指定が失われる。")
    elif cmd[0] == "add" and extra and not miss:
        head = ("`match` の指定は既存の指定と**統合される**(置き換えではない)ため、"
                "不要な種別が残る。")
    else:
        head = "適用後の対象が要件と一致しない。"
    tail = []
    if miss:
        tail.append("不足: " + "、".join(miss))
    if extra:
        tail.append("過剰: " + "、".join(extra))
    return head + ("(" + " / ".join(tail) + ")" if tail else "") \
        + f" 適用後の表示は `{disp(p, got)}`。"


def build_choices_fix(d, rnd, n=4):
    """候補からモデル評価で正解1つ＋不正解を選ぶ(一意性を構成で保証)。"""
    p = d["pid"]
    ok = [c for c in CANDS if works(d, c)]
    ng = [c for c in CANDS if not works(d, c)]
    if not ok:
        raise ValueError("正解候補なし")
    # 正解が複数ある場合は最短(行数・語数)を採り、他は選択肢から外す
    ok.sort(key=lambda c: (len(cmd_lines(p, c)), len(" ".join(cmd_lines(p, c)))))
    correct = ok[0]
    rnd.shuffle(ng)
    # 紛らわしい順(同じ種類の操作)を優先して詰める
    ng.sort(key=lambda c: 0 if c[0] == correct[0] else 1)
    picked = [correct] + ng[:n - 1]
    out = [(("\n".join(cmd_lines(p, c))), c == correct,
            "" if c == correct else why_wrong(d, c), cmd_lines(p, c))
           for c in picked]
    order = list(range(len(out)))
    rnd.shuffle(order)
    return [out[i] for i in order]


def build_choices_cause(d, rnd):
    """原因特定形(現状の設定が、なぜその BGP テーブルになるのか)。"""
    s = STATE_OF[d["kind"]]
    m = d["m"]
    true_claims = {
        "default_only": ("OSPF から BGP への再配送では、既定で対象となるのが"
                         "エリア内ルートとエリア間ルートだけであるため"),
        "ext_only": ("`match` によって外部ルートだけが対象とされており、"
                     "内部ルート(エリア内・エリア間)が対象から外れているため"),
        "int_ext1": ("`match` の指定に外部タイプ 2 が含まれていないため"),
        "ext2_only": ("`match` によって外部タイプ 2 だけが対象とされており、"
                      "内部ルートおよび外部タイプ 1 が対象から外れているため"),
    }
    pool = [
        ("OSPF から BGP への再配送では、既定で外部ルートだけが対象となるため",
         "既定の対象は内部ルート(エリア内・エリア間)であり、記述が逆である。"),
        (f"{m['DUT']} の BGP に `default-metric` が設定されていないため",
         "BGP への再配送ではメトリックは必須ではなく、"
         "設定の有無で対象の範囲は変わらない。"),
        (f"{m['DUT']} で `redistribute` に `subnets` が指定されていないため",
         "`subnets` は **OSPF への**再配送で用いるオプションであり、"
         "BGP への再配送では用いない。"),
        (f"{m['ABR']} から {m['DUT']} へ当該ルートが広告されていないため",
         f"{m['DUT']} の経路表には当該ルートが載っており、広告は行われている。"),
        (f"{m['DUT']} と {m['RCV']} の間で BGP のピアが確立していないため",
         "他のルートは受信できており、ピアは確立している。"),
        ("ディストリビュート・リストによって当該ルートが"
         "フィルタリングされているため",
         "示された構成には、そのようなフィルタは設定されていない。"),
    ]
    c = [(true_claims[d["kind"]], True, "")]
    c += [(t, False, w) for t, w in rnd.sample(pool, 3)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_read(d, rnd):
    """読解形: この設定のとき RCV の BGP テーブルはどれか(表そのものを選ばせる)。"""
    s = STATE_OF[d["kind"]]
    cands = [s]
    for alt in ({"i"}, {"i", "e1", "e2"}, {"e1", "e2"}, {"i", "e1"}, {"e2"},
                {"i", "e2"}):
        if alt != s and not any(alt == x for x in cands):
            cands.append(alt)
    cands = cands[:4]
    # ★フェンスは render_options が付ける(ここで付けると二重になる)
    out = [(bgp_table(d, x), x == s,
            "" if x == s else
            f"これは対象が `{disp(d['pid'], x)}` であるときの内容。")
           for x in cands]
    order = list(range(len(out)))
    rnd.shuffle(order)
    return [out[i] for i in order]


def forms_for(d):
    f = ["fix", "cause"]
    # read は「現状の表」を答えにするので、fix/cause と同時には出さない
    return f + ["read"]


def requirements(d, rnd, form="fix"):
    m, w = d["m"], d["world"]
    core = {
        "all": (f"{m['RCV']} は、{m['ABR']} 配下のすべてのネットワーク"
                f"(エリア内・エリア間・外部のいずれも)を、BGP によって"
                f"学習しなければなりません。"),
        "internal_only": (f"{m['RCV']} が BGP によって学習するのは、OSPF の"
                          f"**内部ルート(エリア内およびエリア間)に限られ**なければ"
                          f"なりません。外部ルートが BGP に注入されてはなりません。"),
        "ext1_only": (f"{m['RCV']} が BGP によって学習するのは、**外部タイプ 1 の"
                      f"ルートに限られ**なければなりません。内部ルート"
                      f"(エリア内・エリア間)および外部タイプ 2 のルートが"
                      f"BGP に注入されてはなりません。"),
    }[w]
    reqs = [core,
            (f"変更は {m['DUT']} の BGP の構成においてのみ行われ、"
             "OSPF 側の構成が変更されてはなりません。"),
            ]
    decoy = rnd.sample([
        "スタティック・ルートの追加によって代替されてはなりません。",
        "BGP のピアリングの構成が変更されてはなりません。",
        "インタフェースのアドレッシングが変更されてはなりません。",
    ], rnd.choice([1, 2]))
    reqs += decoy
    rnd.shuffle(reqs)
    return [f"{i + 1}. {t}" for i, t in enumerate(reqs)]
