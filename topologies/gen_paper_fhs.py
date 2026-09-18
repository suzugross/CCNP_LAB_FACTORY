#!/usr/bin/env python3
"""IPv6 First-Hop Security 紙面ファミリ (BL-146 紙面側) — gen_paper_mcq.py の shape=fhs 素材。

設計= 非公開側の計画メモ(2026-09-18) §3 A2 / 事実ベース= Cisco IPv6 FHS 設定ガイド原文(同 §8)＋
poc/fhs/README.md(ioll2-xe 17.15.1 実測: RA Guard/DHCPv6 Guard/device-tracking・VLAN スコープ罠・
ポート>VLAN 優先・router-preference 上限・Dropped 理由文字列)。

kinds:
  term   = 機能↔記述(select/select2/allthat/match)。★機能を抽選する(対象を差し替えると正解集合が動く)。
  pick   = シナリオ→有効にすべき機能(select/select2/allthat)。選択肢は機能名の固定集合。
  policy = ポリシー構成の読解・原因・是正(read/cause/fix)。小さな真偽関数モデル(§MODEL)で
           「どのメッセージがどの理由で落ちるか」を機械決定し、fix は「直る候補==1」を検証する。
レーン: term/pick= 瞬発力枠(SPEED_KINDS)・policy= 思考系(THINK_KINDS)。

公開 API(svc と同じ作法):
  KINDS / SPEED_KINDS / THINK_KINDS / WORLDS / KIND_WORLDS / kind_forms(kind) / worlds_for(kind)
  draw(rnd, kind, world=None, form=None) -> d
  build_choices_<form>(d, rnd) -> [(text, is_correct, why)]  (match は build_match)
  question_body(d, choices, form) / answer_body(d, choices, form) -> Markdown 断片
  pick_count(form, choices) / TITLES / CORE / selftest()
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KINDS = ["term", "pick", "policy"]
SPEED_KINDS = ["term", "pick"]
THINK_KINDS = ["policy"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {
    "term":   {"select", "select2", "allthat", "match"},
    "pick":   {"select", "select2", "allthat"},
    "policy": {"read", "cause", "fix"},
}
DIFF = {"term": 2, "pick": 2, "policy": 4}


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


# ==========================================================================
# 機能の正典(名前・記述)。出典= Cisco IPv6 FHS 設定ガイド(xe-16/xe-16-8/15-s/c9000 SISF)
# ==========================================================================
FEATURES = {
    "raguard":    "IPv6 RA ガード",
    "dhcpguard":  "IPv6 DHCPv6 ガード",
    "srcguard":   "IPv6 ソース ガード",
    "prefguard":  "IPv6 プレフィックス ガード",
    "destguard":  "IPv6 宛先ガード",
    "bindtab":    "IPv6 バインディング テーブル",
    "ndinsp":     "IPv6 ND インスペクション(デバイス トラッキング)",
    "snoop":      "IPv6 スヌーピング(アドレス グリーニング)",
}
FEATURE_KEYS = list(FEATURES)

# tag → [(記述, 真偽, 偽なら反証)]  ★選択肢に因果を書かない(「〜である」で閉じる)
FACTS = {
    "raguard": [
        ("不正なルータから送られてくる RA メッセージを、L2 デバイスで破棄する。", True, ""),
        ("ポリシーは着信(ingress)方向でのみ機能する。", True, ""),
        ("ポリシーの device-role を host にすると、そのポートで受信した RA は破棄される。", True, ""),
        ("router-preference maximum を指定すると、それより高い優先度を広告する RA は破棄される。", True, ""),
        ("match ra prefix-list を指定すると、リストで許可されないプレフィックスを含む RA は破棄される。", True, ""),
        ("trusted-port を指定したポリシーを適用したポートでは、RA の検査は行われない。", True, ""),
        ("ポリシーは、ポートにも VLAN にも適用できる。", True, ""),
        ("バインディング テーブルに載っていない送信元のデータ トラフィックを破棄する。", False, "それは IPv6 ソース ガードの動作である。RA ガードは RA メッセージを検査する。"),
        ("不正な DHCPv6 サーバからの応答メッセージを破棄する。", False, "それは IPv6 DHCPv6 ガードの動作である。"),
        ("送信(egress)方向にも適用できる。", False, "RA ガードは着信方向でのみサポートされる。"),
        ("device-role を router にしたポートでは、すべての RA が無条件に破棄される。", False, "router は RA の送信を許される役割であり、無条件に破棄されるのは host である。"),
    ],
    "dhcpguard": [
        ("認可されていない DHCPv6 サーバやリレー エージェントからの応答(REPLY)とアドバタイズ(ADVERTISE)を破棄する。", True, ""),
        ("クライアントから送られるメッセージ(SOLICIT・REQUEST など)は破棄しない。", True, ""),
        ("ポリシーの device-role に client を指定したポートでは、サーバからの応答メッセージは破棄される。", True, ""),
        ("match server access-list で、認可するサーバやリレーのアドレスを指定できる。", True, ""),
        ("match reply prefix-list で、応答に含まれるプレフィックスを検査できる。", True, ""),
        ("preference の最小値と最大値を指定して、サーバの優先度を検査できる。", True, ""),
        ("不正なルータから送られてくる RA メッセージを破棄する。", False, "それは IPv6 RA ガードの動作である。"),
        ("クライアントが送る SOLICIT メッセージを検査して、認可されていないクライアントを遮断する。", False, "DHCPv6 ガードが検査するのはサーバ側のメッセージであり、クライアントのメッセージは遮断しない。"),
        ("バインディング テーブルに載っていない宛先へのパケットを破棄する。", False, "それは IPv6 宛先ガードの動作である。"),
    ],
    "srcguard": [
        ("バインディング テーブルに載っていないアドレスを送信元とするデータ トラフィックを破棄する。", True, ""),
        ("ND や DHCP のパケットは検査せず、ND インスペクションやアドレス グリーニングと組み合わせて機能する。", True, ""),
        ("バインディング テーブルにプレフィックスが載っていることが、機能する前提である。", True, ""),
        ("トラフィックを拒否したとき、DHCP サーバへの照会または ND によってバインディングの復元が試みられる。", True, ""),
        ("バインディング テーブルとデータ トラフィックのフィルタリングとの間のインターフェイスとして働く。", True, ""),
        ("不正なルータから送られてくる RA メッセージをすべて破棄する。", False, "それは IPv6 RA ガードの動作である。"),
        ("認可されていない DHCPv6 サーバからの応答を破棄する。", False, "それは IPv6 DHCPv6 ガードの動作である。"),
        ("ND メッセージを検査して、有効な束縛を持たない ND メッセージを破棄する。", False, "それは IPv6 ND インスペクションの動作である。ソース ガードは ND を検査しない。"),
        ("宛先がバインディング テーブルに無いパケットを破棄する。", False, "それは IPv6 宛先ガードの動作である。"),
    ],
    "prefguard": [
        ("トポロジ的に正しくない(範囲外の)アドレスを送信元とするトラフィックを破棄する。", True, ""),
        ("IPv6 ソース ガードの機能の中で動作する。", True, ""),
        ("許可するプレフィックスは、RA のプレフィックス、DHCP プレフィックス委任、静的設定から得る。", True, ""),
        ("送信元アドレスのプレフィックスが、許可された範囲に含まれるかを検証する。", True, ""),
        ("バインディング テーブルに載っていない宛先へのパケットを破棄する。", False, "それは IPv6 宛先ガードの動作である。"),
        ("不正なルータから送られてくる RA メッセージを破棄する。", False, "それは IPv6 RA ガードの動作である。"),
        ("許可するプレフィックスは、DHCPv6 サーバのプールから直接読み取る。", False, "出所は RA のプレフィックス グリーン、DHCP プレフィックス委任のグリーン、静的設定である。"),
    ],
    "destguard": [
        ("宛先がバインディング テーブルに載っていないパケットを破棄する。", True, ""),
        ("リンク上で活動が確認されている宛先に対してだけ、アドレス解決(ND)を行わせる。", True, ""),
        ("宛先が表に載っている場合は、ND による解決が行われる。", True, ""),
        ("バインディング テーブルは、NDP と DHCP のメッセージのスヌーピングで作られる。", True, ""),
        ("送信元がバインディング テーブルに載っていないパケットを破棄する。", False, "それは IPv6 ソース ガードの動作である。"),
        ("不正な DHCPv6 サーバからのアドバタイズ メッセージを破棄する。", False, "それは IPv6 DHCPv6 ガードの動作である。"),
        ("宛先が表に無い場合、その宛先に対して ND による解決を行ってから転送する。", False, "表に無い宛先のパケットは解決を行わずに破棄される。"),
    ],
    "bindtab": [
        ("IPv6 スヌーピング(アドレス グリーニング)や ND インスペクションで集めた情報から作られる、リンク上の IPv6 ネイバのデータベースである。", True, ""),
        ("IPv6 ソース ガード、宛先ガード、プレフィックス ガードが、束縛の検証に利用する。", True, ""),
        ("リカバリ機構により、デバイスのリブート時に表を復元できる。", True, ""),
        ("リカバリ機構は、宛先アドレスの解決に失敗したときに、DHCP サーバまたは宛先ホストへ照会して欠落したエントリを復元する。", True, ""),
        ("復元の途中は、表に載っていない送信元からのデータ トラフィックは遮断される。", True, ""),
        ("リカバリの対象は、プロトコルごとにプレフィックス リストで絞ることができる。", True, ""),
        ("エントリには、ホストの IPv6 アドレスと MAC アドレス、インターフェイス、VLAN、状態などが含まれる。", True, ""),
        ("リカバリ機構は、DHCP リレー エージェントを実装したルータへ照会して表を復元する。", False, "照会先は DHCP サーバまたは宛先ホストである。"),
        ("リカバリ機構は、宛先ガードでアドレス解決に成功したときに動作する。", False, "解決に失敗したときに復元が試みられる。"),
        ("不正な RA メッセージを検出して破棄する。", False, "それは IPv6 RA ガードの動作である。表は検査ではなく記録である。"),
        ("有効な束縛を持たない ND メッセージを破棄する。", False, "それは IPv6 ND インスペクションの動作である。"),
    ],
    "ndinsp": [
        ("ND メッセージを解析して信頼できるバインディング テーブルを作り、有効な束縛を持たない ND メッセージを破棄する。", True, ""),
        ("ステートレス自動設定のアドレスの束縛を学習して、L2 ネイバ テーブルで保護する。", True, ""),
        ("Cisco IOS XE 17.1.1 以降では、SISF ベースのデバイス トラッキングが同じ機能を提供する。", True, ""),
        ("ND メッセージから学習した束縛を、バインディング テーブルに登録する。", True, ""),
        ("バインディング テーブルに載っていない送信元のデータ トラフィックを破棄する。", False, "それは IPv6 ソース ガードの動作である。"),
        ("不正なルータから送られてくる RA メッセージを破棄する。", False, "それは IPv6 RA ガードの動作である。"),
        ("認可されていない DHCPv6 サーバからの応答を破棄する。", False, "それは IPv6 DHCPv6 ガードの動作である。"),
    ],
    "snoop": [
        ("リンク上の ND と DHCP のメッセージを覗き見てアドレスを集め、バインディング テーブルに登録する。", True, ""),
        ("正確なバインディング テーブルを必要とする他の IPv6 FHS 機能の基盤となる。", True, ""),
        ("他の FHS 機能を有効にするためのコンテナ ポリシーとして働く。", True, ""),
        ("新しい Cisco IOS XE では、スヌーピング ポリシーに代わって SISF ベースのデバイス トラッキングが推奨される。", True, ""),
        ("宛先がバインディング テーブルに載っていないパケットを破棄する。", False, "それは IPv6 宛先ガードの動作である。"),
        ("不正なルータから送られてくる RA メッセージを破棄する。", False, "それは IPv6 RA ガードの動作である。"),
        ("送信元がバインディング テーブルに載っていないデータ トラフィックを破棄する。", False, "それは IPv6 ソース ガードの動作である。スヌーピングは記録であって遮断ではない。"),
        ("認可されていない DHCPv6 サーバからの応答を破棄する。", False, "それは IPv6 DHCPv6 ガードの動作である。"),
    ],
}
MATCH_SET = [
    ("raguard",   "不正なルータから送られてくる RA メッセージを破棄する機能"),
    ("dhcpguard", "認可されていない DHCPv6 サーバからの応答とアドバタイズを破棄する機能"),
    ("srcguard",  "バインディング テーブルに載っていない送信元からのトラフィックを破棄する機能"),
    ("destguard", "バインディング テーブルに載っていない宛先へのパケットを破棄する機能"),
    ("prefguard", "トポロジ的に正しくないプレフィックスの送信元からのトラフィックを破棄する機能"),
    ("bindtab",   "リンク上の IPv6 ネイバの一覧を保持し、他の機能が束縛の検証に用いるデータベース"),
    ("ndinsp",    "ND メッセージを検査して、有効な束縛を持たないものを破棄する機能"),
]

# pick: シナリオ → 有効にすべき機能(集合)
PICK_SCENARIOS = [
    ("アクセス ポートに接続された端末が偽の RA を送信し、他の端末のデフォルト ルータが書き換えられる事象を、スイッチで止めたい。", {"raguard"}),
    ("アクセス ポートに接続された端末が DHCPv6 サーバとして応答し、他の端末に誤った DNS サーバのアドレスを配る事象を、スイッチで止めたい。", {"dhcpguard"}),
    ("端末が、自身に割り当てられていない IPv6 アドレスを送信元として偽装したパケットを送る事象を、スイッチで止めたい。", {"srcguard"}),
    ("リンク上に存在しない宛先アドレスに向けた大量のパケットによって、ルータの ND による解決が誘発される事象を防ぎたい。", {"destguard"}),
    ("端末が、そのリンクに割り当てられていないプレフィックスのアドレスを送信元として送信する事象を、スイッチで止めたい。", {"prefguard"}),
    ("偽の RA を止め、あわせて偽の DHCPv6 サーバからの応答も止めたい。", {"raguard", "dhcpguard"}),
    ("偽の RA を止め、あわせて表に載っていない送信元アドレスからのデータ トラフィックも止めたい。", {"raguard", "srcguard"}),
    ("偽の DHCPv6 サーバからの応答を止め、あわせてリンク上に存在しない宛先への解決が誘発されないようにしたい。", {"dhcpguard", "destguard"}),
]
PICK_ALLTHAT = [
    ("バインディング テーブルの内容を参照して動作する機能を、すべて選んでください。", {"srcguard", "destguard", "prefguard"}),
    ("RA メッセージそのものを検査の対象とする機能を、すべて選んでください。", {"raguard"}),
    ("DHCPv6 のメッセージのうち、サーバ側から送られるものを検査の対象とする機能を、すべて選んでください。", {"dhcpguard"}),
    ("バインディング テーブルを作る(情報を集める)側の機能を、すべて選んでください。", {"snoop", "ndinsp"}),
    ("送信元アドレスの正当性を検証する機能を、すべて選んでください。", {"srcguard", "prefguard"}),
]

CORE = {
    "term": ("RA ガード= 不正 RA を着信方向で破棄(device-role host/router・router-preference maximum・match ra prefix-list・trusted-port)。"
             "DHCPv6 ガード= 認可されていないサーバ/リレー発の REPLY・ADVERTISE を破棄(client 発は通す)。"
             "ソース ガード= 表に無い送信元のデータを破棄(ND/DHCP は検査しない・表にプレフィックスが要る・拒否時は DHCP 照会/ND で復元を試みる)。"
             "プレフィックス ガード= 範囲外プレフィックスの送信元を破棄(RA/DHCP-PD/静的から許可範囲を得る・ソース ガードの中で動く)。"
             "宛先ガード= 表に無い宛先は解決せず破棄。バインディング テーブル= スヌーピング/ND インスペクション由来のネイバ DB・"
             "リブート時に復元・解決失敗時は DHCP サーバまたは宛先ホストへ照会。ND インスペクション= 17.1.1 以降は SISF device-tracking。"),
    "pick": ("止めたい事象から機能を選ぶ: 偽 RA→RA ガード / 偽 DHCPv6 応答→DHCPv6 ガード / 送信元偽装→ソース ガード / "
             "範囲外プレフィックスの送信元→プレフィックス ガード / 存在しない宛先への解決誘発→宛先ガード。"
             "表を参照するのはソース・宛先・プレフィックス ガード、表を作るのはスヌーピング(グリーニング)と ND インスペクション。"),
    "policy": ("RA ガード/DHCPv6 ガードのポリシーは device-role が核: host は RA を破棄、router は RA を許す(上限や prefix-list の検査つき)。"
               "client は DHCPv6 の応答を破棄、server は許す。trusted-port は検査を無効化。"
               "適用先は ポートと VLAN の両方が可能で、**ポートのポリシーが VLAN のポリシーに優先**する。"
               "VLAN だけに host を適用すると正規ルータの RA も落ちる(守り過ぎ)。show running-config は既定値(device-role host)を表示しない。"),
}
TITLES = {"term": "IPv6 First-Hop Security の機能", "pick": "IPv6 First-Hop Security の機能選択",
          "policy": "IPv6 First-Hop Security のポリシー構成の分析"}

NAMES = [["SW1", "R1", "PC1"], ["ASW01", "GW01", "HOST-A"], ["ACC-SW2", "RTR-A", "CLIENT1"], ["SWA", "CORE-R1", "PC-A"]]


# ==========================================================================
# 盤面の抽選
# ==========================================================================
def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    d["sw"], d["rtr"], d["pc"] = rnd.choice(NAMES)
    if kind == "term":
        d["feature"] = rnd.choice(FEATURE_KEYS)
    elif kind == "policy":
        _draw_policy(d, rnd)
    return d


# ==========================================================================
# term: 事実ベースの選択肢(select / select2 / allthat / match)
# ==========================================================================
def _fact_choices(d, rnd, n_true, n_total, offscope=True):
    feat = d["feature"]
    pool_t = [(t, w) for t, tv, w in FACTS[feat] if tv]
    pool_f = [(t, w) for t, tv, w in FACTS[feat] if not tv]
    if len(pool_t) < n_true:
        raise ValueError(f"{feat}: 真の肢が足りない")
    trues = rnd.sample(pool_t, n_true)
    c = [(t, True, "") for t, _ in trues]
    n_false = n_total - n_true
    if offscope and n_false >= 3:
        # 「真だが設問外」= 他の機能について真の記述を 1 つ混ぜる(記述は機能名を含まない)
        others = [k for k in FEATURE_KEYS if k != feat]
        cand = [(t, k) for k in others for t, tv, w in FACTS[k] if tv and t not in [x[0] for x in c]]
        t, k = rnd.choice(cand)
        c.append((t, False, f"記述そのものは {FEATURES[k]} については正しいが、設問({FEATURES[feat]})についての記述ではない。"))
        n_false -= 1
    if len(pool_f) < n_false:
        raise ValueError(f"{feat}: 偽の肢が足りない")
    for t, w in rnd.sample(pool_f, n_false):
        c.append((t, False, w))
    texts = [x[0] for x in c]
    if len(set(texts)) != len(texts):
        raise ValueError("選択肢の重複")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_select(d, rnd):
    if d["kind"] == "pick":
        return _pick_choices(d, rnd, "select")
    return _fact_choices(d, rnd, n_true=1, n_total=4)


def build_choices_select2(d, rnd):
    if d["kind"] == "pick":
        return _pick_choices(d, rnd, "select2")
    return _fact_choices(d, rnd, n_true=2, n_total=5)


def build_choices_allthat(d, rnd):
    if d["kind"] == "pick":
        return _pick_choices(d, rnd, "allthat")
    n_true = rnd.choice([1, 2, 2, 3, 3, 4])
    n_true = min(n_true, sum(1 for _, tv, _ in FACTS[d["feature"]] if tv))
    return _fact_choices(d, rnd, n_true=n_true, n_total=5, offscope=(n_true <= 2))


def build_match(d, rnd):
    items = rnd.sample(MATCH_SET, 4)
    terms = [("①②③④"[i], FEATURES[k]) for i, (k, _) in enumerate(items)]
    descs = list(enumerate(items))
    rnd.shuffle(descs)
    letters = "ABCD"
    choices = [(letters[j], items[i][1]) for j, (i, _) in enumerate(descs)]
    ans = {}
    for j, (i, _) in enumerate(descs):
        ans["①②③④"[i]] = letters[j]
    d["_match_keys"] = [k for k, _ in items]
    return terms, choices, dict(sorted(ans.items()))


# ==========================================================================
# pick: シナリオ → 機能名
# ==========================================================================
def _pick_choices(d, rnd, form):
    if form == "allthat":
        ask, want = rnd.choice(PICK_ALLTHAT)
    elif form == "select2":
        ask, want = rnd.choice([s for s in PICK_SCENARIOS if len(s[1]) == 2])
    else:
        ask, want = rnd.choice([s for s in PICK_SCENARIOS if len(s[1]) == 1])
    d["pick_ask"] = ask
    n_total = 4 if form == "select" else 5
    others = [k for k in FEATURE_KEYS if k not in want]
    picks = sorted(want) + rnd.sample(others, n_total - len(want))
    rnd.shuffle(picks)
    c = []
    for k in picks:
        if k in want:
            c.append((FEATURES[k], True, ""))
        else:
            c.append((FEATURES[k], False, f"{FEATURES[k]}は、この事象を止める(または問われた性質を持つ)機能ではない。"))
    return c


# ==========================================================================
# policy: 真偽関数モデル(MODEL)
#   盤面= アクセス SW の VLAN 10 に 正規ルータ(rtr・Et0/0)・端末(pc・Et0/1)・不明な装置(Et0/2)。
#   不明な装置は RA(優先度 rogue_pref・偽プレフィックス)と DHCPv6 応答(偽 DNS)を送る。
#   ポリシー= RA ガード / DHCPv6 ガードを ポート or VLAN に適用。ポート適用が VLAN 適用に優先。
#   故障種(1 つだけ仕込む):
#     vlan_overblock  = host ポリシーを VLAN にだけ適用 → 正規 RA も落ちる
#     role_swapped    = router を端末ポート・host を GW ポートに適用 → 正規 RA が落ち偽 RA が通る
#     pref_equal      = router-preference maximum が偽 RA の優先度と同じ → 偽 RA が通る
#     pref_low        = router-preference maximum が正規 RA の優先度より低い → 正規 RA が落ちる
#     plist_wrong     = match ra prefix-list が正規プレフィックスを許可しない → 正規 RA が落ちる
#     trusted_rogue   = 不明な装置のポートに trusted-port → 偽 RA が通る
#     dhcp_client_gw  = DHCPv6 ガード client を GW ポートにも適用 → 正規の応答が落ちる
#     dhcp_missing    = DHCPv6 ガードが未適用 → 偽の応答が通る(RA ガードは正しい)
# ==========================================================================
PREF_ORDER = {"low": 0, "medium": 1, "high": 2}
PREF_JA = {"low": "Low", "medium": "Medium", "high": "High"}
FAULTS = ["vlan_overblock", "role_swapped", "pref_equal", "pref_low", "plist_wrong",
          "trusted_rogue", "dhcp_client_gw", "dhcp_missing"]


def _draw_policy(d, rnd):
    fault = rnd.choice(FAULTS)
    d["fault"] = fault
    d["vlan"] = rnd.choice([10, 20, 30, 100])
    d["ok_pfx"] = rnd.choice(["2001:DB8:10::/64", "2001:DB8:A::/64", "2001:DB8:100::/64", "2001:DB8:20::/64"])
    d["bad_pfx"] = rnd.choice(["2001:DB8:BAD::/64", "2001:DB8:FFFF::/64", "2001:DB8:99::/64"])
    d["p_host"] = rnd.choice(["HOSTS", "ACCESS-HOST", "END-HOSTS"])
    d["p_rtr"] = rnd.choice(["ROUTERS", "UPLINK-RTR", "GW-ROUTER"])
    d["p_cli"] = rnd.choice(["CLIENTS", "DHCP-CLIENT", "NO-SERVER"])
    d["plname"] = rnd.choice(["PL-RA", "OK-PREFIX", "SITE-PFX"])
    d["ports"] = {"rtr": "Ethernet0/0", "pc": "Ethernet0/1", "rogue": "Ethernet0/2"}
    # RA の優先度
    if fault == "pref_equal":
        d["rogue_pref"], d["legit_pref"], d["pref_max"] = "medium", "medium", "medium"
    elif fault == "pref_low":
        d["rogue_pref"], d["legit_pref"], d["pref_max"] = "high", "medium", "low"
    else:
        d["rogue_pref"] = rnd.choice(["high", "high", "medium"])
        d["legit_pref"] = "medium"
        d["pref_max"] = "medium"
    # ポリシーの組立
    ra_policies, ra_attach = {}, {"vlan": None, "port": {}}
    dh_policies, dh_attach = {}, {"vlan": None, "port": {}}
    P = d["ports"]
    if fault == "vlan_overblock":
        ra_policies[d["p_host"]] = {"role": "host"}
        ra_attach["vlan"] = d["p_host"]
    elif fault == "role_swapped":
        ra_policies[d["p_host"]] = {"role": "host"}
        ra_policies[d["p_rtr"]] = {"role": "router"}
        ra_attach["port"] = {P["rtr"]: d["p_host"], P["pc"]: d["p_rtr"], P["rogue"]: d["p_rtr"]}
    elif fault in ("pref_equal", "pref_low"):
        ra_policies[d["p_rtr"]] = {"role": "router", "pref_max": d["pref_max"]}
        ra_attach["vlan"] = d["p_rtr"]
    elif fault == "plist_wrong":
        ra_policies[d["p_rtr"]] = {"role": "router", "plist": d["plname"]}
        d["plist_permits"] = d["bad_pfx"]          # ★正規プレフィックスを許可していない
        ra_attach["vlan"] = d["p_rtr"]
    elif fault == "trusted_rogue":
        ra_policies[d["p_host"]] = {"role": "host"}
        ra_policies[d["p_rtr"]] = {"role": "router"}
        ra_policies["TRUSTED"] = {"role": "host", "trusted": True}
        ra_attach["port"] = {P["rtr"]: d["p_rtr"], P["pc"]: d["p_host"], P["rogue"]: "TRUSTED"}
    else:  # dhcp 系: RA ガードは正しい(ポート role)
        ra_policies[d["p_host"]] = {"role": "host"}
        ra_policies[d["p_rtr"]] = {"role": "router"}
        ra_attach["port"] = {P["rtr"]: d["p_rtr"], P["pc"]: d["p_host"], P["rogue"]: d["p_host"]}
    if fault == "dhcp_client_gw":
        dh_policies[d["p_cli"]] = {"role": "client"}
        dh_attach["vlan"] = d["p_cli"]             # VLAN 適用= GW ポートにも効く
    elif fault == "dhcp_missing":
        pass
    else:
        # 健全な DHCPv6 ガード(ポート role・GW は server)
        dh_policies[d["p_cli"]] = {"role": "client"}
        dh_policies["DHCP-SERVER"] = {"role": "server"}
        dh_attach["port"] = {P["rtr"]: "DHCP-SERVER", P["pc"]: d["p_cli"], P["rogue"]: d["p_cli"]}
    d["ra_policies"], d["ra_attach"] = ra_policies, ra_attach
    d["dh_policies"], d["dh_attach"] = dh_policies, dh_attach
    st = state(d)
    d["_state"] = st
    # 故障が症状を持つこと(健全な盤面を出さない)
    if not (st["legit_ra_dropped"] or st["rogue_ra_passed"] or st["legit_dh_dropped"] or st["rogue_dh_passed"]):
        raise ValueError("policy: 症状が無い")
    # fix 候補の一意性(fix 形で使う。draw 時に検証しておく)
    d["_fix"] = fix_candidates(d)
    if sum(1 for _, ok, _ in d["_fix"] if ok) != 1:
        raise ValueError("policy: 直る候補が 1 でない")


def _eff(attach, port):
    """有効ポリシー名(ポート適用 > VLAN 適用)。"""
    return attach["port"].get(port) or attach["vlan"]


def _ra_verdict(d, pol, src):
    """RA ガードの判定。src= 'legit' | 'rogue'。戻り (dropped, reason)。"""
    if pol is None:
        return False, ""
    p = d["ra_policies"][pol]
    if p.get("trusted"):
        return False, ""
    if p["role"] == "host":
        return True, "Message unauthorized on port"
    pref = d["legit_pref"] if src == "legit" else d["rogue_pref"]
    if p.get("pref_max") and PREF_ORDER[pref] > PREF_ORDER[p["pref_max"]]:
        return True, "Preference flag error"
    if p.get("plist"):
        pfx = d["ok_pfx"] if src == "legit" else d["bad_pfx"]
        if pfx != d["plist_permits"]:
            return True, "Prefix not permitted by prefix-list"
    return False, ""


def _dh_verdict(d, pol):
    if pol is None:
        return False, ""
    p = d["dh_policies"][pol]
    if p.get("trusted"):
        return False, ""
    if p["role"] == "client":
        return True, "Message type is not authorized by the policy on this port, device-role mismatch"
    return False, ""


def state(d):
    P = d["ports"]
    st = {}
    st["legit_ra_dropped"], st["legit_ra_reason"] = _ra_verdict(d, _eff(d["ra_attach"], P["rtr"]), "legit")
    rd, rr = _ra_verdict(d, _eff(d["ra_attach"], P["rogue"]), "rogue")
    st["rogue_ra_passed"], st["rogue_ra_reason"] = (not rd), rr
    st["legit_dh_dropped"], st["legit_dh_reason"] = _dh_verdict(d, _eff(d["dh_attach"], P["rtr"]))
    dd, dr = _dh_verdict(d, _eff(d["dh_attach"], P["rogue"]))
    st["rogue_dh_passed"], st["rogue_dh_reason"] = (not dd), dr
    # 端末から見た帰結
    routers = []
    if not st["legit_ra_dropped"]:
        routers.append(("legit", d["legit_pref"]))
    if st["rogue_ra_passed"]:
        routers.append(("rogue", d["rogue_pref"]))
    st["pc_routers"] = routers
    if routers:
        best = max(PREF_ORDER[p] for _, p in routers)
        st["pc_default"] = [s for s, p in routers if PREF_ORDER[p] == best]
    else:
        st["pc_default"] = []
    st["pc_dns"] = ("rogue" if st["rogue_dh_passed"] else "legit" if not st["legit_dh_dropped"] else "none")
    return st


def _healthy(st):
    return not (st["legit_ra_dropped"] or st["rogue_ra_passed"] or st["legit_dh_dropped"] or st["rogue_dh_passed"])


# ---- fix 候補: 変更を適用した仮想盤面で「健全」になる候補がちょうど 1 --------
def _apply(d, key):
    import copy
    e = copy.deepcopy(d)
    P = e["ports"]
    f = e["fault"]
    if key == "port_router_gw":       # GW ポートに router ポリシーをポート適用
        e["ra_policies"].setdefault(e["p_rtr"], {"role": "router"})
        e["ra_attach"]["port"][P["rtr"]] = e["p_rtr"]
    elif key == "vlan_router":        # VLAN 適用を router ポリシーへ差し替え(全ポートが router に)
        e["ra_policies"].setdefault(e["p_rtr"], {"role": "router"})
        e["ra_attach"]["vlan"] = e["p_rtr"]
    elif key == "swap_back":          # 役割を正しく付け直す
        e["ra_attach"]["port"] = {P["rtr"]: e["p_rtr"], P["pc"]: e["p_host"], P["rogue"]: e["p_host"]}
    elif key == "pref_max_low":       # 上限を low に
        for p in e["ra_policies"].values():
            if "pref_max" in p:
                p["pref_max"] = "low"
    elif key == "pref_max_high":
        for p in e["ra_policies"].values():
            if "pref_max" in p:
                p["pref_max"] = "high"
    elif key == "pref_max_medium":
        for p in e["ra_policies"].values():
            if "pref_max" in p:
                p["pref_max"] = "medium"
    elif key == "host_rogue_port":   # 不明な装置のポートに host ポリシーをポート適用(ポート優先)
        e["ra_policies"].setdefault(e["p_host"], {"role": "host"})
        e["ra_attach"]["port"][P["rogue"]] = e["p_host"]
    elif key == "plist_fix":          # prefix-list を正規プレフィックスに
        e["plist_permits"] = e["ok_pfx"]
    elif key == "plist_add_bad":      # prefix-list に偽プレフィックスを追加(無意味)
        pass
    elif key == "untrust_rogue":      # 不明な装置のポートを host ポリシーへ
        e["ra_attach"]["port"][P["rogue"]] = e["p_host"]
    elif key == "trust_gw":           # GW ポートを trusted に
        e["ra_policies"]["TRUSTED"] = {"role": "host", "trusted": True}
        e["ra_attach"]["port"][P["rtr"]] = "TRUSTED"
    elif key == "dh_server_gw":       # GW ポートに server ポリシーをポート適用
        e["dh_policies"]["DHCP-SERVER"] = {"role": "server"}
        e["dh_attach"]["port"][P["rtr"]] = "DHCP-SERVER"
    elif key == "dh_client_ports":    # 端末ポートに client ポリシーを適用
        e["dh_policies"].setdefault(e["p_cli"], {"role": "client"})
        e["dh_attach"]["port"][P["pc"]] = e["p_cli"]
        e["dh_attach"]["port"][P["rogue"]] = e["p_cli"]
    elif key == "dh_client_vlan":     # client ポリシーを VLAN に適用(GW も落ちる)
        e["dh_policies"].setdefault(e["p_cli"], {"role": "client"})
        e["dh_attach"]["vlan"] = e["p_cli"]
    elif key == "dh_remove":
        e["dh_attach"] = {"vlan": None, "port": {}}
    elif key == "ra_host_vlan":       # host を VLAN に(守り過ぎ)
        e["ra_policies"].setdefault(e["p_host"], {"role": "host"})
        e["ra_attach"]["vlan"] = e["p_host"]
    return e


FIX_CLI = {
    "port_router_gw": lambda d: f"interface {d['ports']['rtr']}\n ipv6 nd raguard attach-policy {d['p_rtr']}",
    "vlan_router":    lambda d: f"vlan configuration {d['vlan']}\n ipv6 nd raguard attach-policy {d['p_rtr']}",
    "swap_back":      lambda d: (f"interface {d['ports']['rtr']}\n ipv6 nd raguard attach-policy {d['p_rtr']}\n"
                                 f"interface range {d['ports']['pc']} , {d['ports']['rogue']}\n ipv6 nd raguard attach-policy {d['p_host']}"),
    "pref_max_low":   lambda d: f"ipv6 nd raguard policy {d['p_rtr']}\n router-preference maximum low",
    "pref_max_high":  lambda d: f"ipv6 nd raguard policy {d['p_rtr']}\n router-preference maximum high",
    "pref_max_medium": lambda d: f"ipv6 nd raguard policy {d['p_rtr']}\n router-preference maximum medium",
    "host_rogue_port": lambda d: f"ipv6 nd raguard policy {d['p_host']}\n device-role host\ninterface {d['ports']['rogue']}\n ipv6 nd raguard attach-policy {d['p_host']}",
    "plist_fix":      lambda d: f"ipv6 prefix-list {d['plname']} seq 5 permit {d['ok_pfx']}",
    "plist_add_bad":  lambda d: f"ipv6 prefix-list {d['plname']} seq 15 permit {d['bad_pfx']}",
    "untrust_rogue":  lambda d: f"interface {d['ports']['rogue']}\n ipv6 nd raguard attach-policy {d['p_host']}",
    "trust_gw":       lambda d: f"ipv6 nd raguard policy TRUSTED\n trusted-port\ninterface {d['ports']['rtr']}\n ipv6 nd raguard attach-policy TRUSTED",
    "dh_server_gw":   lambda d: f"ipv6 dhcp guard policy DHCP-SERVER\n device-role server\ninterface {d['ports']['rtr']}\n ipv6 dhcp guard attach-policy DHCP-SERVER",
    "dh_client_ports": lambda d: (f"ipv6 dhcp guard policy {d['p_cli']}\n device-role client\n"
                                  f"interface range {d['ports']['pc']} , {d['ports']['rogue']}\n ipv6 dhcp guard attach-policy {d['p_cli']}"),
    "dh_client_vlan": lambda d: f"ipv6 dhcp guard policy {d['p_cli']}\n device-role client\nvlan configuration {d['vlan']}\n ipv6 dhcp guard attach-policy {d['p_cli']}",
    "dh_remove":      lambda d: f"vlan configuration {d['vlan']}\n no ipv6 dhcp guard attach-policy",
    "ra_host_vlan":   lambda d: f"vlan configuration {d['vlan']}\n ipv6 nd raguard attach-policy {d['p_host']}",
}
FIX_WHY = {
    "port_router_gw": "正規ルータのポートにだけ router のポリシーをポート適用する変更。ポート適用は VLAN 適用に優先するので、正規の RA は通り、他のポートは VLAN の host のままで偽 RA は落ちる。",
    "vlan_router":    "VLAN 全体を router にすると、不明な装置のポートでも RA が許されてしまう。",
    "swap_back":      "役割をポートに合わせて付け直す変更。",
    "pref_max_low":   "上限を low にすると、Medium の正規 RA まで落ちる。",
    "pref_max_high":  "上限を high にすると、High の偽 RA も通ってしまう。",
    "pref_max_medium": "上限を medium にする変更。Medium の正規 RA は通り、High の偽 RA は落ちる。",
    "host_rogue_port": "不明な装置のポートに host のポリシーをポート適用する変更。ポート適用は VLAN 適用に優先するので、そのポートの RA だけが落ちる。",
    "plist_fix":      "許可リストに正規のプレフィックスを含める変更。",
    "plist_add_bad":  "偽のプレフィックスを許可しても、正規の RA が通らない状況は変わらない。",
    "untrust_rogue":  "不明な装置のポートを host のポリシーに戻す変更。",
    "trust_gw":       "正規ルータのポートを trusted にする変更。検査は行われず RA は通る。",
    "dh_server_gw":   "正規ルータのポートに server のポリシーをポート適用する変更。VLAN の client より優先される。",
    "dh_client_ports": "端末側のポートに client のポリシーを適用する変更。",
    "dh_client_vlan": "VLAN に client を適用すると、正規ルータの応答まで落ちる。",
    "dh_remove":      "DHCPv6 ガードを外すと、偽の応答も通る。",
    "ra_host_vlan":   "host を VLAN に適用すると、正規ルータの RA まで落ちる。",
}
FIX_MENU = {
    "vlan_overblock": ["port_router_gw", "vlan_router", "pref_max_high", "dh_client_vlan"],
    "role_swapped":   ["swap_back", "vlan_router", "trust_gw", "ra_host_vlan"],
    "pref_equal":     ["host_rogue_port", "pref_max_low", "pref_max_high", "trust_gw"],
    "pref_low":       ["pref_max_medium", "pref_max_high", "pref_max_low", "ra_host_vlan"],
    "plist_wrong":    ["plist_fix", "plist_add_bad", "pref_max_high", "ra_host_vlan"],
    "trusted_rogue":  ["untrust_rogue", "trust_gw", "vlan_router", "pref_max_high"],
    "dhcp_client_gw": ["dh_server_gw", "dh_remove", "dh_client_vlan", "ra_host_vlan"],
    "dhcp_missing":   ["dh_client_ports", "dh_client_vlan", "dh_remove", "pref_max_low"],
}


def fix_candidates(d):
    out = []
    for key in FIX_MENU[d["fault"]]:
        e = _apply(d, key)
        ok = _healthy(state(e))
        out.append((key, ok, FIX_WHY[key]))
    return out


def build_choices_fix(d, rnd):
    c = []
    for key, ok, why in d["_fix"]:
        c.append((FIX_CLI[key](d), ok, "" if ok else why))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---- cause 形 --------------------------------------------------------------
CAUSE_TEXT = {
    "vlan_overblock": "device-role が host のポリシーが VLAN に適用されており、正規ルータのポートで受信する RA も破棄されている。",
    "role_swapped":   "正規ルータのポートに host のポリシー、端末側のポートに router のポリシーが適用されている。",
    "pref_equal":     "router-preference maximum の値が偽の RA の優先度と同じであり、その RA は上限以下として許可されている。",
    "pref_low":       "router-preference maximum の値が正規ルータの RA の優先度より低く、正規の RA が破棄されている。",
    "plist_wrong":    "match ra prefix-list で参照するプレフィックス リストが正規ルータの広告するプレフィックスを許可していない。",
    "trusted_rogue":  "不明な装置のポートに trusted-port のポリシーが適用されており、そのポートでは RA が検査されない。",
    "dhcp_client_gw": "device-role が client の DHCPv6 ガード ポリシーが VLAN に適用されており、正規ルータからの応答も破棄されている。",
    "dhcp_missing":   "DHCPv6 ガードのポリシーがどのポートにも適用されておらず、不明な装置からの応答が検査されていない。",
}
CAUSE_WRONG_GENERIC = [
    ("RA ガードのポリシーは VLAN には適用できず、ポートに適用したものだけが有効になっている。", "RA ガードのポリシーはポートにも VLAN にも適用できる(ポート適用が優先)。"),
    ("device-tracking のポリシーが VLAN に適用されておらず、RA ガードの検査が動作していない。", "RA ガードの検査は device-tracking のポリシーの有無に依存しない。"),
    ("端末側のポートが trunk ではなく、アクセス ポートではポリシーが有効にならない。", "アクセス ポートにもポリシーは適用される。"),
    ("正規ルータのポートに device-role router のポリシーが適用されており、そのポートで受信する RA は破棄されている。", "router の役割は RA を許す側であり、破棄の原因にはならない。"),
]


def symptom(d):
    st = d["_state"]
    pc, rtr = d["pc"], d["rtr"]
    if d["fault"] in ("vlan_overblock", "role_swapped", "pref_low", "plist_wrong"):
        if st["rogue_ra_passed"]:
            return f"{pc} のデフォルト ルータが {rtr} ではなく {d['ports']['rogue']} に接続された装置になっており、{rtr} からのプレフィックスによるアドレスを取得していません。"
        return f"{pc} はリンクローカル アドレスしか持たず、デフォルト ルータも学習していません。"
    if d["fault"] in ("pref_equal", "trusted_rogue"):
        tie = len(st["pc_default"]) > 1
        tail = ("その装置もデフォルト ルータの候補として学習しています。" if tie
                else "その装置をデフォルト ルータとして使用しています。")
        return f"{pc} が {d['ports']['rogue']} に接続された装置の広告するプレフィックス {d['bad_pfx']} のアドレスを取得し、{tail}"
    if d["fault"] == "dhcp_client_gw":
        return f"{pc} は {rtr} からのプレフィックスでアドレスを取得していますが、DHCPv6 で配布されるはずの DNS サーバとドメイン名を取得できていません。"
    if d["fault"] == "dhcp_missing":
        return f"{pc} は {rtr} をデフォルト ルータとして使用していますが、DNS サーバとして {d['ports']['rogue']} に接続された装置の配った偽のアドレスを使用しています。"
    raise ValueError(d["fault"])


def build_choices_cause(d, rnd):
    truth = d["fault"]
    c = [(CAUSE_TEXT[truth], True, "")]
    # 近い故障種の原因文を 2 つ(この盤面では成り立たない)＋汎用の誤りを 1 つ
    near = [k for k in FAULTS if k != truth]
    for k in rnd.sample(near, 2):
        c.append((CAUSE_TEXT[k], False, f"示されている構成にはその状態が無い({FEATURES['raguard'] if 'dhcp' not in k else FEATURES['dhcpguard']}の構成を読むとこの原因は成り立たない)。"))
    t, w = rnd.choice(CAUSE_WRONG_GENERIC)
    c.append((t, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ---- read 形: この構成で起きることを選ぶ ------------------------------------
def _read_pool(d):
    """(記述, 真偽, 偽の理由) の候補。★同点優先度で両方が通る盤面では「デフォルト ルータ」の
    肢を出さない(端末がどちらを選ぶかは一意でない)。"""
    st = d["_state"]
    P = d["ports"]
    pc, rtr = d["pc"], d["rtr"]
    rogue = f"{P['rogue']} に接続された装置"
    ra_pol_rtr = _eff(d["ra_attach"], P["rtr"])
    ra_pol_rog = _eff(d["ra_attach"], P["rogue"])
    dh_pol_rtr = _eff(d["dh_attach"], P["rtr"])
    dh_pol_rog = _eff(d["dh_attach"], P["rogue"])

    def ra_why(pol, src, dropped):
        p = d["ra_policies"].get(pol) if pol else None
        where = "ポート適用" if pol and pol in d["ra_attach"]["port"].values() and pol == d["ra_attach"]["port"].get(P[src if src == "rtr" else "rogue"]) else "VLAN 適用"
        if p is None:
            return "そのポートには RA ガードのポリシーが適用されておらず、RA は検査されない。"
        if p.get("trusted"):
            return f"そのポートの有効なポリシー {pol} は trusted-port であり、RA は検査されない。"
        if p["role"] == "host":
            return f"そのポートの有効なポリシー {pol}({where})は device-role host であり、受信した RA は破棄される。"
        # router
        if dropped:
            return f"そのポートの有効なポリシー {pol} は device-role router であり、上限や prefix-list の条件を満たす RA は破棄されない。"
        return f"そのポートの有効なポリシー {pol} は device-role router だが、上限または prefix-list の条件を満たさない RA は破棄される。"

    def dh_why(pol, dropped):
        p = d["dh_policies"].get(pol) if pol else None
        if p is None:
            return "そのポートには DHCPv6 ガードのポリシーが適用されておらず、応答は検査されない。"
        if p["role"] == "client":
            return f"そのポートの有効なポリシー {pol} は device-role client であり、サーバからの応答は破棄される。"
        return f"そのポートの有効なポリシー {pol} は device-role server であり、応答は破棄されない。"

    pool = []
    pool.append((f"{rtr} が送信する RA は、{P['rtr']} で破棄される。", st["legit_ra_dropped"], ra_why(ra_pol_rtr, "rtr", True)))
    pool.append((f"{rogue}が送信する RA は、{P['rogue']} で破棄される。", not st["rogue_ra_passed"], ra_why(ra_pol_rog, "rogue", True)))
    pool.append((f"{pc} は、{rtr} が広告するプレフィックス {d['ok_pfx']} のアドレスを取得する。", not st["legit_ra_dropped"], ra_why(ra_pol_rtr, "rtr", False)))
    pool.append((f"{pc} は、{rogue}が広告するプレフィックス {d['bad_pfx']} のアドレスを取得する。", st["rogue_ra_passed"], ra_why(ra_pol_rog, "rogue", False)))
    routers = dict(st["pc_routers"])
    tie = len(st["pc_default"]) > 1
    if not tie:
        for src, label in (("legit", rtr), ("rogue", rogue)):
            truth = st["pc_default"] == [src]
            other = "rogue" if src == "legit" else "legit"
            if src not in routers:
                why = "その RA は破棄されており、デフォルト ルータの候補にならない。"
            elif truth:
                why = ""
            elif other in routers:
                why = f"両方の RA が届き、優先度は{'正規ルータ' if other == 'legit' else '不明な装置'}側が高い。"
            else:
                why = "その RA だけが届いており、デフォルト ルータはそれになる。"
            pool.append((f"{pc} は、{label} をデフォルト ルータとして学習する。", truth, why))
    if d["dh_policies"] or d["fault"] == "dhcp_missing":
        pool.append((f"{rogue}からの DHCPv6 の応答は、{P['rogue']} で破棄される。", not st["rogue_dh_passed"], dh_why(dh_pol_rog, True)))
        pool.append((f"{rtr} からの DHCPv6 の応答は、{P['rtr']} で破棄される。", st["legit_dh_dropped"], dh_why(dh_pol_rtr, True)))
        dns = st["pc_dns"]
        pool.append((f"{pc} は、DHCPv6 で DNS サーバのアドレスを取得できない。", dns == "none",
                     "正規ルータまたは不明な装置のどちらかの応答が届いており、DNS サーバのアドレスは取得される。"))
        pool.append((f"{pc} は、{rogue}が配布する DNS サーバのアドレスを使用する。", dns == "rogue",
                     "不明な装置からの応答は破棄されており、その DNS サーバのアドレスは届かない。"))
    return pool


def build_choices_read(d, rnd):
    pool = _read_pool(d)
    trues = [(t, w) for t, ok, w in pool if ok]
    falses = [(t, w) for t, ok, w in pool if not ok]
    if not trues or len(falses) < 3:
        raise ValueError("read: 肢が組めない")
    t, _ = rnd.choice(trues)
    c = [(t, True, "")]
    for f, w in rnd.sample(falses, 3):
        c.append((f, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# exhibit(show running-config の抜粋)。★既定値(device-role host)は表示されない(実測)
# ==========================================================================
def _policy_lines(name, p):
    L = [f"ipv6 nd raguard policy {name}"]
    if p.get("trusted"):
        L.append(" trusted-port")
    if p["role"] == "router":
        L.append(" device-role router")
    if p.get("pref_max"):
        L.append(f" router-preference maximum {p['pref_max']}")
    if p.get("plist"):
        L.append(f" match ra prefix-list {p['plist']}")
    return L


def exhibit(d):
    P = d["ports"]
    L = [f"{d['sw']}# show running-config | section raguard|dhcp guard|prefix-list|vlan configuration|interface Ethernet0/"]
    for name, p in d["ra_policies"].items():
        L += _policy_lines(name, p)
    for name, p in d["dh_policies"].items():
        L.append(f"ipv6 dhcp guard policy {name}")
        if p["role"] == "server":
            L.append(" device-role server")
        if p["role"] == "client":
            L.append(" device-role client")
    if "plist_permits" in d:
        L.append(f"ipv6 prefix-list {d['plname']} seq 10 permit {d['plist_permits']}")
    if d["ra_attach"]["vlan"] or d["dh_attach"]["vlan"]:
        L.append(f"vlan configuration {d['vlan']}")
        if d["ra_attach"]["vlan"]:
            L.append(f" ipv6 nd raguard attach-policy {d['ra_attach']['vlan']}")
        if d["dh_attach"]["vlan"]:
            L.append(f" ipv6 dhcp guard attach-policy {d['dh_attach']['vlan']}")
    desc = {P["rtr"]: f"to {d['rtr']}", P["pc"]: f"to {d['pc']}", P["rogue"]: "access"}
    for port in (P["rtr"], P["pc"], P["rogue"]):
        L.append(f"interface {port}")
        L.append(f" description {desc[port]}")
        L.append(f" switchport access vlan {d['vlan']}")
        L.append(" switchport mode access")
        if port in d["ra_attach"]["port"]:
            L.append(f" ipv6 nd raguard attach-policy {d['ra_attach']['port'][port]}")
        if port in d["dh_attach"]["port"]:
            L.append(f" ipv6 dhcp guard attach-policy {d['dh_attach']['port'][port]}")
    return "\n".join(L)


def scenario_text(d):
    P = d["ports"]
    return (f"アクセス スイッチ {d['sw']} の VLAN {d['vlan']} には、正規のルータ {d['rtr']}({P['rtr']})、端末 {d['pc']}({P['pc']})、"
            f"および管理者が把握していない装置({P['rogue']})が接続されています。{d['rtr']} は優先度 {PREF_JA[d['legit_pref']]} の RA で "
            f"プレフィックス {d['ok_pfx']} を広告し、DHCPv6 で DNS サーバとドメイン名を配布しています。"
            f"{P['rogue']} の装置は優先度 {PREF_JA[d['rogue_pref']]} の RA でプレフィックス {d['bad_pfx']} を広告し、"
            f"DHCPv6 サーバとしても応答しています。{d['sw']} には次の構成があります。")


# ==========================================================================
# Markdown
# ==========================================================================
ASK_FACT = {
    "select": "{subject}について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)",
    "select2": "{subject}について、正しく述べられているものを、次のうちから 2 つ選択してください。",
    "allthat": "{subject}について、正しく述べられているものを、すべて選んでください。",
    "match": "IPv6 First-Hop Security の機能について、左側の①〜④の項目に対応する説明を、右側の A〜D から選択してください。",
}
ASK_PICK = {
    "select": "この要件を満たすために有効にする機能として最も適切なものは、次のうちどれですか。(1つを選択してください)",
    "select2": "この要件を満たすために有効にする機能を、次のうちから 2 つ選択してください。",
}


def question_body(d, choices, form):
    kind = d["kind"]
    if kind == "term":
        subject = FEATURES[d["feature"]]
        ask = ASK_FACT[form].format(subject=subject)
        if form == "match":
            terms, ch, _ = choices
            terms_md = "### 対応させる項目\n\n| # | 項目 |\n|---|------|\n" + "\n".join(f"| {k} | {t} |" for k, t in terms)
            ch_md = "\n\n".join(f"{k}. {t}" for k, t in ch)
            return "", ask, ch_md, terms_md
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return "", ask, ch_md, ""
    if kind == "pick":
        if form == "allthat":
            before, ask = "", d["pick_ask"]
        else:
            before, ask = d["pick_ask"], ASK_PICK[form]
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    # policy
    ex = exhibit(d)
    before = f"{scenario_text(d)}\n\n```\n{ex}\n```"
    if form == "read":
        ask = "この構成での動作について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    elif form == "cause":
        before += f"\n\n{symptom(d)}"
        ask = "この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    else:
        before += f"\n\n{symptom(d)}"
        ask = (f"{d['ports']['rogue']} の装置からの不正なメッセージを止めたうえで、{d['pc']} が {d['rtr']} から正しくアドレスと DHCPv6 の情報を"
               f"取得できるようにします。{d['sw']} に加える変更として最も適切なものは、次のうちどれですか。"
               "なお、端末とルータの構成は変更できません。(1つを選択してください)")
        ch_md = "\n\n".join(f"**{'ABCDEFG'[i]}.**\n\n```\n{t}\n```" for i, (t, _, _) in enumerate(choices))
    return before, ask, ch_md, ""


def answer_body(d, choices, form):
    if form == "match":
        terms, ch, ans = choices
        lines = ["## 正解", "", "**" + "、".join(f"{k}－{v}" for k, v in ans.items()) + "**", "", "## 解説", "", CORE[d["kind"]]]
        return "\n".join(lines)
    keys = [k for k, (t, ok, w) in zip("ABCDEFG", choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip("ABCDEFG", choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[d["kind"]]]
    if d["kind"] == "policy":
        st = d["_state"]
        lines += ["", "### 盤面の判定(モデル)", "",
                  f"- 仕込み: `{d['fault']}`",
                  f"- 正規 RA: {'破棄(' + st['legit_ra_reason'] + ')' if st['legit_ra_dropped'] else '通過'} / 偽 RA: {'通過' if st['rogue_ra_passed'] else '破棄(' + st['rogue_ra_reason'] + ')'}",
                  f"- 正規 DHCPv6 応答: {'破棄' if st['legit_dh_dropped'] else '通過'} / 偽 DHCPv6 応答: {'通過' if st['rogue_dh_passed'] else '破棄'}",
                  f"- 端末のデフォルト ルータ候補: {st['pc_default'] or 'なし'} / DNS の出所: {st['pc_dns']}",
                  "- 実測の Dropped 理由文字列(poc/fhs): RA guard= `Message unauthorized on port` / `Preference flag error`、DHCP guard= `device-role mismatch`"]
    return "\n".join(lines)


def pick_count(form, choices):
    if form == "allthat":
        return -1
    if form == "select2":
        return 2
    return 1


# ==========================================================================
# selftest
# ==========================================================================
def selftest(seeds=40):
    import random as _r
    import re as _re
    ng = n = 0
    bad = {}
    builders = {"select": build_choices_select, "select2": build_choices_select2,
                "allthat": build_choices_allthat, "read": build_choices_read,
                "fix": build_choices_fix, "cause": build_choices_cause}
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = None
                    for k in range(50):
                        try:
                            d = draw(_r.Random((hash((kind, form, s)) + k * 7) & 0xFFFFFFFF), kind, None, form)
                            break
                        except ValueError:
                            continue
                    assert d is not None, "draw 不成立"
                    if form == "match":
                        terms, ch, ans = build_match(d, rnd)
                        assert len(ans) == 4 and len(set(ans.values())) == 4, "全単射でない"
                        got = {t: dict(ch)[ans[k]] for k, t in terms}
                        want = {FEATURES[k]: dict(MATCH_SET)[k] for k in d["_match_keys"]}
                        assert got == want, "対応が壊れた"
                        choices = (terms, ch, ans)
                    else:
                        choices = builders[form](d, rnd)
                        n_true = sum(1 for x in choices if x[1])
                        want = {"select": 1, "select2": 2, "read": 1, "fix": 1, "cause": 1}.get(form)
                        if form == "allthat":
                            assert 1 <= n_true <= 4, f"allthat 正解数 {n_true}"
                        else:
                            assert n_true == want, f"{form} 正解数 {n_true}"
                        texts = [x[0] for x in choices]
                        assert len(set(texts)) == len(texts), "選択肢の重複"
                        assert not any(_re.search(r"(ため|ので)[、。]", t) for t in texts), "肢に因果"
                    before, ask, ch_md, terms_md = question_body(d, choices, form)
                    ab = answer_body(d, choices, form)
                    assert "## 正解" in ab
                except (AssertionError, ValueError, KeyError) as exc:
                    ng += 1
                    key = (kind, form)
                    bad.setdefault(key, [0, repr(exc)])[0] += 1
    # policy: 全故障種で fix 一意・症状あり(各故障種が成立する seed が 300 以内に見つかること)
    seen = set()
    for s in range(300):
        rnd = _r.Random(hash(("pol", s)) & 0xFFFFFFFF)
        try:
            d = draw(rnd, "policy")
        except ValueError:
            continue
        seen.add(d["fault"])
        if len(seen) == len(FAULTS):
            break
    for f in FAULTS:
        if f not in seen:
            ng += 1
            print(f"  NG policy/{f}: 300 seed で一度も成立しない")
    for (k, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{f}: {cnt} 件 (例: {ex})")
    print(f"[gen_paper_fhs selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
