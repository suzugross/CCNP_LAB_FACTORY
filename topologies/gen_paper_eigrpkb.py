#!/usr/bin/env python3
"""EIGRP 知識・読解小ファミリ (BL-180) — gen_paper_mcq.py の shape=eigrpkb 素材。

設計= 非公開側の計画メモ(2026-09-18) §3 A5。
kinds:
  named_mode (瞬発) 名前付きモードで「そのコマンドを入力するモード」を選ぶ(select)・4 コマンド↔4 モードの組合せ(match)・
             指定モードで入力するコマンドをすべて選ぶ(allthat)・classic↔named の等価(select2)。
             事実ベース= **iol-xe 17.15.1 の `?` 実測**(poc/paper-kb P1/P1b/P1c)。
  autosum    (思考) 不連続サブネット×auto-summary: クラスフル境界に位置するルータを選ぶ(select2/allthat)・原因(cause)・
             片側だけ直したときの帰結(read)。★IOS 15+ は既定 no auto-summary → 盤面に `auto-summary` を明示(計画メモ R1)。
             実測(P6)= 片側境界だけ直すと疎通は戻るが個別経路は載らない(/16 の要約のみ)。
"""
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KINDS = ["named_mode", "autosum"]
SPEED_KINDS = ["named_mode"]
THINK_KINDS = ["autosum"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {"named_mode": {"select", "select2", "allthat", "match"}, "autosum": {"select2", "allthat", "cause", "read"}}
DIFF = {"named_mode": 2, "autosum": 4}


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


# ==========================================================================
# named mode: コマンド → モード(実測 `?`)
# ==========================================================================
MODES = {
    "router": "(config-router)#",
    "af": "(config-router-af)#",
    "afi": "(config-router-af-interface)#",
    "topo": "(config-router-af-topology)#",
}
MODE_JA = {
    "router": "ルータ コンフィギュレーション モード (config-router)#",
    "af": "アドレス ファミリ コンフィギュレーション モード (config-router-af)#",
    "afi": "アドレス ファミリ インターフェイス コンフィギュレーション モード (config-router-af-interface)#",
    "topo": "アドレス ファミリ トポロジ コンフィギュレーション モード (config-router-af-topology)#",
}
# (named コマンド, モード, classic の相当コマンド(None=無し), 表示用)
CMDS = [
    ("address-family ipv4 unicast autonomous-system 100", "router", "router eigrp 100"),
    ("network 10.0.0.0", "af", "network 10.0.0.0(ルータ コンフィギュレーション モード)"),
    ("eigrp router-id 1.1.1.1", "af", "eigrp router-id 1.1.1.1(ルータ コンフィギュレーション モード)"),
    ("eigrp stub connected summary", "af", "eigrp stub connected summary(ルータ コンフィギュレーション モード)"),
    ("neighbor 10.0.0.2 Ethernet0/0", "af", "neighbor 10.0.0.2 Ethernet0/0(ルータ コンフィギュレーション モード)"),
    ("metric weights 0 1 0 1 0 0", "af", "metric weights 0 1 0 1 0 0(ルータ コンフィギュレーション モード)"),
    ("af-interface Ethernet0/0", "af", None),
    ("topology base", "af", None),
    ("passive-interface", "afi", "passive-interface Ethernet0/0(ルータ コンフィギュレーション モード)"),
    ("authentication mode md5", "afi", "ip authentication mode eigrp 100 md5(インターフェイス コンフィギュレーション モード)"),
    ("authentication key-chain KC1", "afi", "ip authentication key-chain eigrp 100 KC1(インターフェイス コンフィギュレーション モード)"),
    ("hello-interval 5", "afi", "ip hello-interval eigrp 100 5(インターフェイス コンフィギュレーション モード)"),
    ("hold-time 15", "afi", "ip hold-time eigrp 100 15(インターフェイス コンフィギュレーション モード)"),
    ("split-horizon", "afi", "ip split-horizon eigrp 100(インターフェイス コンフィギュレーション モード)"),
    ("next-hop-self", "afi", "ip next-hop-self eigrp 100(インターフェイス コンフィギュレーション モード)"),
    ("summary-address 172.16.0.0/16", "afi", "ip summary-address eigrp 100 172.16.0.0 255.255.0.0(インターフェイス コンフィギュレーション モード)"),
    ("bandwidth-percent 50", "afi", "ip bandwidth-percent eigrp 100 50(インターフェイス コンフィギュレーション モード)"),
    ("bfd", "afi", None),
    ("redistribute ospf 1 metric 100000 100 255 1 1500", "topo", "redistribute ospf 1 metric 100000 100 255 1 1500(ルータ コンフィギュレーション モード)"),
    ("variance 2", "topo", "variance 2(ルータ コンフィギュレーション モード)"),
    ("distance eigrp 90 170", "topo", "distance eigrp 90 170(ルータ コンフィギュレーション モード)"),
    ("offset-list 10 in 1000 Ethernet0/0", "topo", "offset-list 10 in 1000 Ethernet0/0(ルータ コンフィギュレーション モード)"),
    ("distribute-list prefix PL1 in", "topo", "distribute-list prefix PL1 in(ルータ コンフィギュレーション モード)"),
    ("maximum-paths 2", "topo", "maximum-paths 2(ルータ コンフィギュレーション モード)"),
    ("auto-summary", "topo", "auto-summary(ルータ コンフィギュレーション モード)"),
    ("default-metric 100000 100 255 1 1500", "topo", "default-metric 100000 100 255 1 1500(ルータ コンフィギュレーション モード)"),
    ("metric maximum-hops 50", "topo", None),
    ("timers active-time 5", "topo", None),
    ("default-information in", "topo", None),
]
CMD_BY_MODE = {}
for c, m, _ in CMDS:
    CMD_BY_MODE.setdefault(m, []).append(c)

# ==========================================================================
# autosum: 直列トポロジのクラスフル境界
# ==========================================================================
MAJORS = [("172.16", "172.17"), ("10", "172.16"), ("172.31", "10"), ("172.20", "172.21"), ("172.16", "10")]


def _draw_autosum(d, rnd):
    n = rnd.choice([4, 5, 6])
    d["n"] = n
    _pre = rnd.choice(["A", "B"])    # ★BL-187: 接頭辞はルータ列で統一(A1/A2/B3 のような混在を避ける)
    d["names"] = [f"R{i + 1}" for i in range(n)] if rnd.random() < 0.5 else [_pre + str(i + 1) for i in range(n)]
    d["names"] = [f"RT{i + 1:02d}" for i in range(n)] if rnd.random() < 0.3 else d["names"]
    mA, mB = rnd.choice(MAJORS)
    d["mA"], d["mB"] = mA, mB
    # リンクごとのメジャー(A または B)。端の LAN は A。中央に B の連続区間を 1〜(n-3) 本置く
    links = ["A"] * (n - 1)
    k = rnd.randint(1, max(1, n - 3))
    start = rnd.randint(1, n - 1 - k) if n - 1 - k >= 1 else 0
    for i in range(start, start + k):
        links[i] = "B"
    d["links"] = links
    # 各ルータの LAN(端の 2 台のみ・A)
    d["lan"] = {0: "A", n - 1: "A"}
    # 境界ルータ= 隣接するリンク(または LAN)のメジャーが異なるルータ
    segs = [[] for _ in range(n)]
    for i, m in enumerate(links):
        segs[i].append(m)
        segs[i + 1].append(m)
    segs[0].append("A")
    segs[n - 1].append("A")
    d["boundary"] = [i for i in range(n) if len(set(segs[i])) > 1]
    if len(d["boundary"]) < 1:
        raise ValueError("autosum: 境界なし")
    d["diff"] = 4


def _addr(d, major, idx, host):
    """メジャー major のサブネット idx のホスト host。"""
    if major.count(".") == 0:        # 10
        return f"{major}.{idx}.0.{host}"
    if major.count(".") == 1:        # 172.16
        return f"{major}.{idx}.{host}"
    return f"{major}.{idx * 16 + host}"   # 192.168.1 → /28 ではなく /24 内の擬似(表記用)


def _subnet(d, major, idx):
    if major.count(".") == 0:
        return f"{major}.{idx}.0.0/24"
    if major.count(".") == 1:
        return f"{major}.{idx}.0/24"
    return f"{major}.0/24({idx})"


def autosum_exhibit(d):
    n, names, links = d["n"], d["names"], d["links"]
    mA, mB = d["mA"], d["mB"]
    L = ["リンクとサブネット:"]
    lan_a = _subnet(d, mA, 11)
    lan_b = _subnet(d, mA, 41)
    L.append(f"  {names[0]} LAN: {lan_a}")
    for i, m in enumerate(links):
        major = mA if m == "A" else mB
        L.append(f"  {names[i]} — {names[i + 1]}: {_subnet(d, major, 20 + i)}")
    L.append(f"  {names[n - 1]} LAN: {lan_b}")
    L.append("")
    L.append(f"{names[0]}# show running-config | section router eigrp")
    L.append("router eigrp 1")
    L.append(f" network {mA if mA.count('.') else mA}.0.0.0" if mA.count(".") == 0 else f" network {mA}.0.0")
    if mB.count(".") == 0:
        L.append(f" network {mB}.0.0.0")
    else:
        L.append(f" network {mB}.0.0")
    L.append(" auto-summary")
    L.append(f"(他のルータも同じ router eigrp 1 の構成です)")
    return "\n".join(L)


CORE = {
    "named_mode": ("名前付き EIGRP のモード: (config-router)= address-family / service-family / shutdown だけ。"
                   "af= network・eigrp router-id・eigrp stub・neighbor・metric weights・af-interface・topology。"
                   "af-interface= authentication(mode/key-chain)・hello-interval・hold-time・passive-interface・split-horizon・next-hop-self・"
                   "summary-address(具体 IF のみ)・bandwidth-percent・bfd。af-topology= redistribute・distance・variance・offset-list・distribute-list・"
                   "maximum-paths・auto-summary・default-metric・metric maximum-hops・timers active-time。classic の IF 配下の ip … eigrp AS は af-interface に、"
                   "ルータ配下の経路制御は af-topology に対応する(実測 `?`: iol-xe 17.15.1)。"),
    "autosum": ("auto-summary はクラスフル境界(異なるメジャー ネットワークのインターフェイスを持つルータ)で要約を作り、"
                "自分には Null0 の要約経路を入れる。不連続サブネットでは境界ルータの向こう側の個別経路が届かない。"
                "是正は**境界に位置する全ルータ**で no auto-summary。非境界のルータで外しても効かない。"
                "片側の境界だけ外すと、相手側の /16 要約経由で疎通は戻るが個別経路は載らない(実測)。IOS 15 以降は既定で無効。"),
}
TITLES = {"named_mode": "名前付き EIGRP のコンフィギュレーション モード", "autosum": "EIGRP の自動集約と不連続サブネット"}


def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    if kind == "named_mode":
        d["cmd"], d["mode"], d["classic"] = rnd.choice(CMDS)
        d["as"] = 100
    else:
        _draw_autosum(d, rnd)
    return d


# ---- named_mode --------------------------------------------------------------
def build_choices_select(d, rnd):
    if d["kind"] != "named_mode":
        raise ValueError("select は named_mode のみ")
    modes = list(MODES)
    rnd.shuffle(modes)
    c = []
    for m in modes:
        if m == d["mode"]:
            c.append((MODE_JA[m], True, ""))
        else:
            c.append((MODE_JA[m], False, f"`{d['cmd']}` は {MODES[m]} では受け付けられない(実機の `?` に無い)。"))
    return c


def build_choices_select2(d, rnd):
    if d["kind"] == "autosum":
        return _autosum_routers(d, rnd, exact2=True)
    # classic → named の等価(2 つ: モードとコマンド)
    if d["classic"] is None:
        raise ValueError("classic 相当なし")
    truth_mode = d["mode"]
    correct = [(f"{MODES[truth_mode]} で `{d['cmd']}`", True, "")]
    wrong = []
    for m in MODES:
        if m != truth_mode:
            wrong.append((f"{MODES[m]} で `{d['cmd']}`", False, f"`{d['cmd']}` は {MODES[m]} では受け付けられない。"))
    # 2 つ目の正解: 同じ意味の別表現(モードの日本語名)
    correct.append((f"{MODE_JA[truth_mode]} に入ってから `{d['cmd']}` を入力する", True, ""))
    picks = correct + rnd.sample(wrong, 3)
    rnd.shuffle(picks)
    return picks


def build_choices_allthat(d, rnd):
    if d["kind"] == "autosum":
        return _autosum_routers(d, rnd, exact2=False)
    mode = d["mode"]
    d["allthat_mode"] = mode
    pool_t = list(CMD_BY_MODE[mode])
    pool_f = [c for m, cs in CMD_BY_MODE.items() if m != mode for c in cs]
    n_true = min(rnd.choice([1, 2, 2, 3]), len(pool_t))
    trues = rnd.sample(pool_t, n_true)
    falses = rnd.sample(pool_f, 5 - n_true)
    c = [(t, True, "") for t in trues]
    for f in falses:
        fm = next(m for cc, m, _ in CMDS if cc == f)
        c.append((f, False, f"`{f}` は {MODES[fm]} で入力する。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_match(d, rnd):
    if d["kind"] != "named_mode":
        raise ValueError("match は named_mode のみ")
    picks = [(rnd.choice(CMD_BY_MODE[m]), m) for m in MODES]
    rnd.shuffle(picks)
    terms = [("①②③④"[i], c) for i, (c, _) in enumerate(picks)]
    descs = list(enumerate(picks))
    rnd.shuffle(descs)
    letters = "ABCD"
    choices = [(letters[j], MODE_JA[picks[i][1]]) for j, (i, _) in enumerate(descs)]
    ans = {}
    for j, (i, _) in enumerate(descs):
        ans["①②③④"[i]] = letters[j]
    d["_match"] = picks
    return terms, choices, dict(sorted(ans.items()))


# ---- autosum -----------------------------------------------------------------
def _autosum_routers(d, rnd, exact2):
    names, boundary = d["names"], d["boundary"]
    if exact2 and len(boundary) != 2:
        raise ValueError("autosum: 境界が 2 でない")
    want = [names[i] for i in boundary]
    others = [x for x in names if x not in want]
    n_total = 5 if not exact2 else 5
    if len(others) < n_total - len(want):
        extra = []
    picks = want + rnd.sample(others, min(len(others), n_total - len(want)))
    rnd.shuffle(picks)
    c = []
    for p in picks:
        if p in want:
            c.append((f"{p}(config-router)# no auto-summary", True, ""))
        else:
            c.append((f"{p}(config-router)# no auto-summary", False, f"{p} はクラスフル境界に位置しておらず、自動集約を行っていない。"))
    return c


def _partial_desc(d):
    names, boundary = d["names"], d["boundary"]
    return names[boundary[0]]


def build_choices_read(d, rnd):
    names, boundary, mA, mB = d["names"], d["boundary"], d["mA"], d["mB"]
    first, last = names[0], names[-1]
    b0 = names[boundary[0]]
    majA = f"{mA}.0.0/16" if mA.count(".") == 1 else (f"{mA}.0.0.0/8" if mA.count(".") == 0 else f"{mA}.0/24")
    P = [
        (f"{first} のルーティング テーブルに、{last} の LAN の個別経路は載らない。", True, ""),
        (f"境界ルータ {b0} のルーティング テーブルには、Null0 を出口とする {majA} の要約経路が載る。", True, ""),
        (f"{first} から {last} の LAN への通信は成功する。", False, "要約の向こう側の個別経路が無く、境界ルータの Null0 要約に落ちる。"),
        (f"{b0} だけで no auto-summary を実行すると、{first} のルーティング テーブルに {last} の LAN の個別経路が載る。", len(boundary) == 1,
         f"もう一方の境界ルータが要約を続けるので、{first} には {majA} の要約だけが届く(疎通は回復する)。"),
        (f"{b0} だけで no auto-summary を実行すると、{first} から {last} の LAN への通信は成功する。", True, ""),
        (f"境界に位置しないルータで no auto-summary を実行すると、事象は解消する。", False, "自動集約は境界ルータでしか行われず、非境界のルータで外しても変化しない。"),
        (f"{first} で variance を設定すると、{last} の LAN の経路が載る。", False, "variance は不等コスト負荷分散の設定であり、学習していない経路を載せる効果は無い。"),
    ]
    trues = [(t, w) for t, ok, w in P if ok]
    falses = [(t, w) for t, ok, w in P if not ok]
    if not trues or len(falses) < 3:
        raise ValueError("autosum read: 肢が組めない")
    t, _ = rnd.choice(trues)
    c = [(t, True, "")]
    for f, w in rnd.sample(falses, 3):
        c.append((f, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_cause(d, rnd):
    names = d["names"]
    bnames = "・".join(names[i] for i in d["boundary"])
    c = [(f"クラスフル境界に位置する {bnames} が自動集約を行い、要約の向こう側の個別経路が届いていない。", True, ""),
         (f"{names[0]} と {names[-1]} の EIGRP の AS 番号が一致していない。", False, "全ルータが router eigrp 1 であり、AS は一致している。"),
         (f"{names[0]} で不等コスト負荷分散(variance)が設定されていない。", False, "variance は学習済みの経路の負荷分散であり、経路が届かない原因ではない。"),
         (f"中間のリンクで EIGRP の隣接が形成されていない。", False, "隣接は形成されており、要約経路は届いている(個別経路だけが要約に置き換わっている)。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_fix(d, rnd):
    raise ValueError("eigrpkb に fix は無い")


# ==========================================================================
# Markdown
# ==========================================================================

def _mmid(name):
    """Mermaid のノード ID(英数字以外は _ に。表示名は label 側に持つ・BL-187)。"""
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", str(name))


def _autosum_mermaid(d):
    n, names, links = d["n"], d["names"], d["links"]
    mA, mB = d["mA"], d["mB"]
    L = ["```mermaid", "graph LR", f'  LANA["{_subnet(d, mA, 11)}"]']
    L += [f'  {_mmid(x)}["{x}"]' for x in names]
    L.append(f'  LANB["{_subnet(d, mA, 41)}"]')
    L.append(f"  LANA --- {_mmid(names[0])}")
    for i, m in enumerate(links):
        major = mA if m == "A" else mB
        L.append(f'  {_mmid(names[i])} ---|"{_subnet(d, major, 20 + i)}"| {_mmid(names[i + 1])}')
    L.append(f"  {_mmid(names[-1])} --- LANB")
    L.append("```")
    return "\n".join(L)

def question_body(d, choices, form):
    if d["kind"] == "named_mode":
        if form == "match":
            terms, ch, _ = choices
            terms_md = "### 対応させる項目\n\n| # | コマンド |\n|---|------|\n" + "\n".join(f"| {k} | `{t}` |" for k, t in terms)
            ch_md = "\n\n".join(f"{k}. {t}" for k, t in ch)
            return "", "名前付きモードの EIGRP で、左側の①〜④のコマンドを入力するモードを、右側の A〜D から選択してください。", ch_md, terms_md
        if form == "select":
            before = f"EIGRP を名前付きモード(`router eigrp <名前>`)で構成しています。"
            ask = f"`{d['cmd']}` を入力するモードはどれですか。(1つを選択してください)"
        elif form == "select2":
            before = f"クラシック モードで `{d['classic']}` として設定していた内容を、名前付きモードで構成します。"
            ask = "同じ設定を名前付きモードで行う方法として正しいものを、次のうちから 2 つ選択してください。"
        else:
            before = "EIGRP を名前付きモードで構成しています。"
            ask = f"{MODE_JA[d['allthat_mode']]} で入力するコマンドを、すべて選んでください。"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    # autosum
    names = d["names"]
    before = (f"{_autosum_mermaid(d)}\n\n{names[0]} から {names[-1]} までを直列に接続し、全ルータで EIGRP(AS 1)を動作させています。"
              f"{names[0]} のルーティング テーブルを確認したところ、{names[-1]} の LAN のネットワークが載っていません。\n\n```\n{autosum_exhibit(d)}\n```")
    if form == "select2":
        ask = f"{names[0]} と {names[-1]} の両方のルーティング テーブルに相手の LAN の個別経路が載るようにするには、どのコマンドを使用すればよいですか。(2つを選択してください)"
    elif form == "allthat":
        ask = f"{names[0]} と {names[-1]} の両方のルーティング テーブルに相手の LAN の個別経路が載るようにするために必要なコマンドを、すべて選んでください。"
    elif form == "cause":
        ask = "この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
    else:
        ask = "この構成での動作について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
    ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    return before, ask, ch_md, ""


def answer_body(d, choices, form):
    if form == "match":
        terms, ch, ans = choices
        return "\n".join(["## 正解", "", "**" + "、".join(f"{k}－{v}" for k, v in ans.items()) + "**", "", "## 解説", "", CORE[d["kind"]]])
    keys = [k for k, (t, ok, w) in zip("ABCDEFG", choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip("ABCDEFG", choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[d["kind"]]]
    if d["kind"] == "autosum":
        lines += ["", f"- 仕込み: 境界ルータ= {[d['names'][i] for i in d['boundary']]} / リンクのメジャー= {d['links']}",
                  "- 実測(poc/paper-kb P6): 全台 auto-summary で疎通 0%・非境界 fix は無効・片側境界 fix で疎通は戻るが個別経路は要約のみ・両側 fix で個別経路"]
    else:
        lines += ["", f"- 正典: iol-xe 17.15.1 の `?` 実測(poc/paper-kb P1/P1b/P1c)"]
    return "\n".join(lines)


def pick_count(form, choices):
    if form == "allthat":
        return -1
    if form == "select2":
        return 2
    return 1


def selftest(seeds=40):
    import random as _r
    import re as _re
    ng = n = 0
    bad = {}
    builders = {"select": build_choices_select, "select2": build_choices_select2, "allthat": build_choices_allthat,
                "read": build_choices_read, "cause": build_choices_cause}
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = None
                    for k in range(40):
                        try:
                            dd = draw(_r.Random((hash((kind, form, s)) + k * 13) & 0xFFFFFFFF), kind, None, form)
                            choices = build_match(dd, rnd) if form == "match" else builders[form](dd, rnd)
                            d = dd
                            break
                        except ValueError:
                            continue
                    assert d is not None, "不成立"
                    if form == "match":
                        terms, ch, ans = choices
                        assert len(ans) == 4 and len(set(ans.values())) == 4
                    else:
                        n_true = sum(1 for x in choices if x[1])
                        if form == "allthat":
                            assert 1 <= n_true <= 4, f"allthat 正解数 {n_true}"
                        else:
                            assert n_true == (2 if form == "select2" else 1), f"{form} 正解数 {n_true}"
                        texts = [x[0] for x in choices]
                        assert len(set(texts)) == len(texts), "選択肢の重複"
                        assert not any(_re.search(r"(ため|ので)[、。]", t) for t in texts), "肢に因果"
                    before, ask, ch_md, _ = question_body(d, choices, form)
                    assert "## 正解" in answer_body(d, choices, form)
                except (AssertionError, ValueError, KeyError) as exc:
                    ng += 1
                    bad.setdefault((kind, form), [0, repr(exc)])[0] += 1
    for (k, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{f}: {cnt} 件 (例: {ex})")
    print(f"[gen_paper_eigrpkb selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
