#!/usr/bin/env python3
"""ACL 単独読解 紙面ファミリ (BL-106) — gen_paper_mcq.py の shape=acl 素材。

設計= problems/_drafts/ACL-PAPER.design.md / 実測= poc/acl/README.md(P0・2026-08-10)。

**レバーは「ACL の意味評価」1本**。フィルタ/ルートフィルタ等の**ロール(衣装)は
permit/deny の帰結写像**であって別レバーではない、という整理で直交性を保つ。

P1a のロールは 2 種(設計メモ §10 のユーザ決定):
  filter       `ip access-group N in|out`     permit=転送 / deny=破棄
  routefilter  `distribute-list N in`         permit=経路を受理 / deny=捨てる

★★ routefilter の意味論は**実測で定説が覆っている**(poc/acl/README.md §4):
  - 標準 ACL   … 照合対象は**広告されたネットワークアドレス**(長さは見ない)
  - 拡張 ACL   … **src = 広告元の隣接ルータ / dst = 広告されたネットワーク**
                 (教科書の「src=網・dst=サブネットマスク」は**不成立**)
  - **名前付きの拡張 ACL は distribute-list に指定できない**(コマンドごと拒否)
  - 標準でも拡張でも**プレフィックス長は区別できない** → prefix-list が唯一解

一意性の機械検証は topologies/acl_cover.py(32bit 三値キューブ代数)で行う。
ベクタ評価は topologies/acl_model.py(既存の意味評価器)。**提示と判定は同じ関数から出す**
(BL-103 ⑤の教訓= 別実装にすると「提示に無い事実で判定する」事故が起きる)。

自己検査: `python3 gen_paper_acl.py --selftest`
"""
import os
import collections
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zlib               # noqa: E402
import acl_cover as ac    # noqa: E402
import acl_model          # noqa: E402

# --------------------------------------------------------------------------
# 論点カタログ
# --------------------------------------------------------------------------
# filter ロール(ip access-group)= ACL の中身そのものの誤り
# アドレス系(標準/拡張のどちらでも成立する)
ADDR_KINDS = [
    "wc_narrow",        # ワイルドカードが狭く、対象の一部が漏れる
    "wc_wide",          # 広すぎて対象外まで許可してしまう
    "wc_bits",          # 非連続ワイルドカード(桁落ち)で飛び地を許可
    "mask_as_wildcard",  # ★サブネットマスクを書いた(実測 P10: 正規化で別物になる)
    "order_shadow",     # 先行の広い permit が後続の deny を影にする
]
# ★拡張 ACL でしか起きない誤り(設計メモ 論点カタログ C節)。
#   標準 ACL は送信元しか見ないので、宛先・プロトコル・ポートの誤りは表現できない。
EXT_ONLY_KINDS = [
    "port_swap",         # ★eq を**送信元側**に書いた(拡張の定番)
    "proto_ip_not_tcp",  # `permit ip` にしてポートの制限が効いていない
    "dst_any_too_wide",  # 宛先を any にしてサーバ以外にも到達できる
]
# ★多エントリ読解(ユーザ要望 2026-08-11「エントリー多めで、細かく条件に合致するか
#   どうかを確認させるものがいい」)。1〜2行の盤面では first-match をたどる作業が
#   ほとんど発生していなかった。6〜8行の現実的な ACL を読ませる。
DENSE_KINDS = ["dense_list"]
# ★適用点(BL-109 段A)。ユーザ指摘 2026-08-11「access-group の設定が問題の仕掛けとして
#   全く機能していない」。ACL の**中身は正しい**が、適用されていない/別の ACL が
#   適用されている、という型。実測= poc/acl/README.md §16-4。
#   これらは `ip access-group` 行を読まないと解けない(＝適用点が主題になる)。
APPLY_KINDS = [
    "apply_wrong_acl",    # 正しい ACL と広い ACL が両方あり、**広いほう**が適用されている
    "apply_missing",      # ACL は要件どおりだが、どの IF にも適用されていない
    "apply_other_iface",  # 要件と無関係な IF(管理セグメント側)に適用されている
    "filter_undef_ref",   # 適用行が**存在しない ACL** を指している(実測 §1= 全許可)
    "filter_empty_acl",   # 適用されている ACL の中身が空(実測 §2= 全許可)
]
# ★段B(BL-109)= 向き/IF の取り違え。**往路と復路を別々に評価**しないと表現できない。
#   実測 §16-10= 末尾に `permit any` の無い(=要件どおりの)ACL には暗黙の拒否があるので、
#   復路に当たる位置に付けると**復路が落ちて疎通しない**(往路は素通りのまま)。
#   §16-5 の「完全な no-op」は `permit ip any any` 付きの ACL での話であり、こことは別。
DIRECTION_KINDS = [
    "apply_direction",    # 同じ IF で向きだけ逆(顧客側の out)= 復路に当たる
    "apply_iface_swap",   # 隣の IF の in(サーバ側の in)= やはり復路に当たる
]
# ★段B の構築系= 「このアクセス リストを**どこに・どの向きで**適用すべきか」。
#   故障ではないので症状は出さない(ACL は書けていて、まだ適用されていない状態)。
PLACE_KINDS = ["apply_place"]
# ★戻り通信(論点14)。盤面に**2枚**のリストを置く=
#   顧客側の in(往路用)＋サーバ側の in(復路用)。復路を許可する手段が主題。
#   実測= poc/acl/README.md §17(E1)。
EST_KINDS = [
    "est_missing",     # 復路用リストに `established` の行が無い → 戻りが落ちる
    "est_wrong_side",  # `established` を**往路側**に書いた → SYN が落ちる
    # ★往路は**全部通る**のに一部の顧客網だけセッションが張れない= 対比が作れる。
    #   全断の2種と違って read / compare が成立する(復路を主題にした比較ができる)。
    "est_ret_narrow",  # 復路用リストの範囲が狭く、一部の顧客網の戻りだけ落ちる
]
# ★構築系= 復路用リストを**これから書く**。「established を正しく書けるか」を問う。
EST_BUILD_KINDS = ["est_build"]
# ★このうち4種は「フィルタが実質不在」＝**全部素通り**になり、症状では割れない。
#   割れるのは出力(§16-4)。read 形は作らず、cause / evidence で出す。
INERT_FILTER_KINDS = ("apply_missing", "apply_other_iface",
                      "filter_undef_ref", "filter_empty_acl")
# ★向きの取り違えは逆に**全断**になる(復路が落ちるため)。read 形はこちらも作れない。
# ★全断になる種= 復路(または往路)が落ちて**どのセッションも成立しない**。
#   read 形は作れない(対比が無い)ので cause / evidence で出す。
BLACKOUT_FILTER_KINDS = (tuple(DIRECTION_KINDS)
                         + ("est_missing", "est_wrong_side"))
APPLY_KINDS = (APPLY_KINDS + DIRECTION_KINDS + PLACE_KINDS + EST_KINDS
               + EST_BUILD_KINDS)
FILTER_KINDS = ADDR_KINDS + EXT_ONLY_KINDS + DENSE_KINDS + APPLY_KINDS
# routefilter ロール(distribute-list)= 実測で確定した意味論に基づく誤り
RF_KINDS = [
    "std_len_blind",       # 標準 ACL は長さを区別できない(同一網アドレスを巻き添え)
    "ext_named_rejected",  # ★名前付き拡張 ACL は distribute-list に指定できない
    "ext_src_is_network",  # 拡張 ACL の src に「網」を書いた(実際は広告元ルータ)
    "undef_ref",           # 参照先が未定義 → 全許可(素通り)
    "empty_acl",           # 中身が空 → 全許可(素通り)
]
# P1c で追加したロール。★狙いは「**同じ ACL でも衣装で permit の意味が変わる**」を
#   出題として成立させること。各ロールは実測(poc/acl)で裏の取れた1点に絞る。
COPP_KINDS = ["copp_deny_to_default"]   # deny は「通す」ではなく class-default 行き
URPF_KINDS_X = ["urpf_undef_exempt"]    # 未定義の例外リスト= **全免除**(uRPF が無力化)
NAT_KINDS = ["nat_deny_scope"]          # deny = 変換しない。範囲を誤ると業務網が素通り
VTY_KINDS = ["vty_wc_wrong"]            # access-class の WC 誤りで管理端末を締め出す

KINDS = (FILTER_KINDS + RF_KINDS + COPP_KINDS + URPF_KINDS_X + NAT_KINDS
         + VTY_KINDS)

# 要件世界。select 形(構築系)で正解を反転させる軸。
# ★設計= **works() は意味・complies() は提示**で分ける。
#   意味だけの世界(「過剰に許可するな」)は、厳密一致の書き方が複数あるため
#   単独では一意化できない(exact3 と deny_first は**意味的に等価**)。
#   そこで「過剰に許可しない」×「拒否行を使わない/行数最小」の組で一意化する。
FILTER_WORLDS = [
    "one_line",       # 1行で書く          → 過剰被覆キューブが正解
    "exact_no_deny",  # 過剰許可なし＋deny 禁止 → 厳密列挙が正解
    "exact_min",      # 過剰許可なし＋行数最小  → deny 先行が正解
    # ★BL-121 P2(2026-08-16)= リーン要件世界(v6 と同設計)。排他の担い手が違う:
    #   lean_only= 明文の非包含なし。「のみ」+deny禁止から排他を**導出**させる。
    #   lean_hole= 「のみ」も無し。名指し禁止網(4本目=base+3)が集約の踏み絵。
    "lean_only",
    "lean_hole",
    # ★ワイルドカードの組み立てそのものを主題にする世界(ユーザ要望 2026-08-11
    #   「送信元のアドレス定義をもう少しバリエーション豊かに。
    #     ワイルドカードマスクを上手く使ったちょっとしたトリックなど」)。
    #   対象の**集合の形**が変わり、1行で書くために必要なワイルドカードが変わる。
    #   上の3世界と違い**1行の答えが厳密**(過剰被覆ではない)なので、
    #   一意化は「1行で書く」という提示制約だけで足りる。
    "wc_even",        # 第3オクテットが偶数の4本 → 0.0.6.255
    "wc_odd",         # 第3オクテットが奇数の4本 → base を +1 して 0.0.6.255
    "wc_split",       # 飛び地2ブロック          → **非連続** 0.0.5.255
    "wc_block",       # 連続4本(/22 相当)        → 0.0.3.255
    # ★論点4「ビット境界に載らないレンジ」(設計メモ §3 A-4)。
    #   対象は base..base+6 の**7本**= 最小のキューブ(8本)より1本少ないので
    #   **1行では厳密に書けない**。分解すると**大きさの違うキューブ3つ**になる
    #   (これが集約の本題)。deny を使ってよいかで正解が反転する。
    "nb_min",         # 行数最小(deny 可)   → 過剰被覆＋deny 先行の 2行
    "nb_no_deny",     # deny 禁止＋行数最小 → **異なる大きさのキューブ3行**
]
NB_WORLDS = ("nb_min", "nb_no_deny")
# 対象集合の形。offs= base からの第3オクテットのずれ / ans= (base のずれ, WC の第3値)
# near= 1行だが**成立しない**候補(いずれも過不足がある)
SRC_PATTERNS = {
    "wc_even":  {"offs": [0, 2, 4, 6], "ans": (0, 6),
                 "near": [(0, 7), (0, 2), (0, 4), (1, 6)]},
    "wc_odd":   {"offs": [1, 3, 5, 7], "ans": (1, 6),
                 "near": [(0, 7), (1, 2), (1, 4), (0, 6)]},
    "wc_split": {"offs": [0, 1, 4, 5], "ans": (0, 5),
                 "near": [(0, 7), (0, 1), (0, 4), (0, 3)]},
    "wc_block": {"offs": [0, 1, 2, 3], "ans": (0, 3),
                 "near": [(0, 7), (0, 1), (0, 5), (0, 2)]},
}
WC_WORLDS = tuple(SRC_PATTERNS)
# ★kind × world の非両立。**仕込んだ誤りがその世界では正しい**組み合わせを宣言する
#   (wc_bits の `0.0.5.255` は wc_split の対象集合そのもの= 症状が出ない)。
#   実行時にも draw() が同じことを検査する(将来の組み合わせを取りこぼさないため)。
INCOMPATIBLE = {("wc_bits", "wc_split")}
RF_WORLDS = ["prefixlen_no_rm", "prefixlen_via_rm", "by_neighbor",
             "keep_others"]
# 追加ロールの要件世界(いずれも「何を守るか」を1つ決めるだけ。select 形は持たない)
X_WORLDS = ["protect_mgmt", "least_change"]
# ★apply 形の要件世界= **どちら向きの通信を絞るのか**。これで正解の IF が反転する
#   (src_customer → 顧客側の in / src_server → サーバ側の in)。
#   src_* の2世界では「出口側に置く解」も意味的に成立してしまうので(実測 §16-5 (iv))、
#   「不要なトラフィックは可能なかぎり早い段階で破棄する」を1行入れて一意化する。
# ★★deny_to_mgmt は**定石から外れる**世界(ユーザ発案 2026-08-11)=
#   「標準 ACL で、顧客側から**管理セグメント宛だけ**を拒否し、
#     顧客からサーバ側への通信には影響を与えない」。
#   標準 ACL は**送信元しか見ない**ので、入口(顧客側の in)に置くと
#   サーバ宛まで巻き添えになる。**宛先の側= 管理 IF の out** に置くしかない。
#   → 「早い段階で破棄」の制約は**入れない**(入れると正解と矛盾する)。
#     一意性は制約ではなく**構造**から出る(works がそもそも1つ)。
APPLY_PLACE_WORLDS = ["src_customer", "src_server", "deny_to_mgmt"]

ROLES = ["DUT", "UP", "DN"]

ROLE_OF_KIND = {}
for _k in FILTER_KINDS:
    ROLE_OF_KIND[_k] = "filter"
for _k in RF_KINDS:
    ROLE_OF_KIND[_k] = "routefilter"
for _k in COPP_KINDS:
    ROLE_OF_KIND[_k] = "copp"
for _k in URPF_KINDS_X:
    ROLE_OF_KIND[_k] = "urpf"
for _k in NAT_KINDS:
    ROLE_OF_KIND[_k] = "nat"
for _k in VTY_KINDS:
    ROLE_OF_KIND[_k] = "vty"

# ロール→適用コマンド(config 抜粋の描画に使う)
ROLE_APPLY = {
    "filter": "ip access-group {n} in",
    "routefilter": "distribute-list {n} in",
    "copp": "match access-group name {n}",
    "urpf": "ip verify unicast source reachable-via rx {n}",
    "nat": "ip nat inside source list {n} interface Ethernet0/1 overload",
    "vty": "access-class {n} in",
}


# ★フィルタが実質「不在」になる故障種= **全部素通り**が実測どおりの正解なので、
#   「通るのはどれか」という read 形が成立しない(対比が作れない)。cause 形で出す。
#   3種が同じ症状に化けるのは偶然ではなく、この分野の教育点そのもの
#   (未定義=全許可 / 空=全許可 / 名前付き拡張=コマンドごと拒否)。
NO_READ_KINDS = (("undef_ref", "empty_acl", "ext_named_rejected",
                  "urpf_undef_exempt")
                 + INERT_FILTER_KINDS + BLACKOUT_FILTER_KINDS)


def role_of(kind):
    return ROLE_OF_KIND[kind]


def kind_forms(kind, samples=8):
    """その故障種が**そもそも取り得る**出題形の集合。

    形は盤面ごとに成立可否が変わるので、数個引いて和集合を取る。
    `--forms` 指定時に「その形を持たない種」を選んでしまう事故を防ぐために使う。
    """
    out = set()
    for i in range(samples):
        for w in worlds_for(kind):
            try:
                d = draw(random.Random(i * 131 + 7), kind=kind, world=w)
            except ValueError:
                continue
            out |= set(forms_for(d))
    return out


def forms_for(d):
    """この盤面で成立する出題形。gen_paper_mcq の形抽選はこれに従う。

    ★成立しない形を抽選させない(=「答えが無い問題」を作らない)ための関門。
    """
    if d["kind"] == "dense_list":
        # ★多エントリ読解は「どれが通るか」「どの行のカウンタが増えるか」に絞る。
        #   故障を1点に特定する形(cause)や、これから書く行を選ぶ形(select)は
        #   多エントリ盤面では成立しない(誤りが1か所に定まらない)。
        f = ["read"]
        # ★counter は「全行＋どの行も増えない」が選択肢になるので、
        #   記号が A〜J に収まる範囲(=9行まで)でのみ成立させる。
        ents, _s, _n = current_entries(d)
        if len(ents) <= 9 and counter_probe(d) is not None:
            f.append("counter")
        if compare_ok(d):
            f.append("compare")
        return f
    if d["kind"] in PLACE_KINDS:
        return ["apply"]                # 構築系。故障ではないので他の形は無い
    if d["kind"] in EST_BUILD_KINDS:
        return ["select"]               # 構築系(復路用リストを書く)
    # ★apply_wrong_acl は cause 形を持たない。
    #   症状表(到達可/不可)だけで「別の ACL が効いている」と分かってしまい、
    #   **`ip access-group` 行を読まずに解ける**(初出題 20260811-011 で判明)。
    #   read / counter なら「どちらの ACL が効いているか」を読まないと答えられない。
    forms = [] if d["kind"] == "apply_wrong_acl" else ["cause"]
    # ★適用点の故障は「これから書くべき行を選ぶ」形(select)を持たない
    #   (中身は正しいので、書くべき行は既に存在している)。
    if d["role"] == "filter" and d["kind"] not in APPLY_KINDS:
        forms.append("select")
    if d["kind"] not in NO_READ_KINDS:
        forms.append("read")
    if counter_probe(d) is not None:
        forms.append("counter")
    if patch_ok(d):
        forms.append("patch")
    if fix_ok(d):
        forms.append("fix")
    if evidence_ok(d):
        forms.append("evidence")
    if compare_ok(d):
        forms.append("compare")
    if logread_ok(d):
        forms.append("logread")
    return forms


def worlds_for(kind):
    r = role_of(kind)
    if kind in PLACE_KINDS:
        return APPLY_PLACE_WORLDS
    if kind in EST_BUILD_KINDS:
        return ["ret_established"]
    if r == "filter":
        return [w for w in FILTER_WORLDS if (kind, w) not in INCOMPATIBLE]
    if r == "routefilter":
        return RF_WORLDS
    return X_WORLDS


# --------------------------------------------------------------------------
# 抽選
# --------------------------------------------------------------------------
def draw(rnd, kind=None, world=None):
    d = {"shape": "acl"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["role"] = role_of(d["kind"])
    d["world"] = world or rnd.choice(worlds_for(d["kind"]))
    if d["world"] not in worlds_for(d["kind"]):
        raise ValueError(f"acl: world={d['world']} は kind={d['kind']} と非両立")

    a = rnd.randint(16, 200)                       # 10.<a>.x.x を客先網に使う
    d["oct1"] = 10
    d["oct2"] = a
    # 対象レンジ= 第3オクテットの連続3本。★base は**8境界**に載せる。
    #   base..base+3 = 1つのキューブ(/22 相当)= `0.0.3.255`
    #   base..base+7 = 1つ上のキューブ(/21 相当)= `0.0.7.255`
    # 「触れてはいけない網」を base+5(= 上位キューブの中・下位キューブの外)に置くと、
    # **広すぎる候補(0.0.7.255)と非連続候補(0.0.5.255)が機械的に失格**になる。
    base = rnd.choice([0, 8, 16, 24, 32, 40, 48, 56, 64, 96, 128, 160, 192, 224])
    d["base"] = base
    if d["world"] in NB_WORLDS:
        # ★ビット境界に載らないレンジ= 7本(最小キューブは8本)。
        #   除外はブロック内の1本(base+7)と、ブロックの外の1本。
        d["target"] = [base + i for i in range(7)]
        d["fourth"] = base + 7
        d["outsider"] = base + 9
        d["fourth_forbidden"] = True
        d["excluded"] = [base + 7, base + 9]
    elif d["world"] in WC_WORLDS:
        # ★ワイルドカードの形が主題。対象は 8 本のブロックの中の**部分集合**で、
        #   ブロック内の非対象は**すべて**除外対象にする(= 1行の答えが厳密になる)。
        pat = SRC_PATTERNS[d["world"]]
        d["target"] = [base + o for o in pat["offs"]]
        rest = [base + o for o in range(8) if o not in pat["offs"]]
        d["fourth"] = rest[0]
        d["outsider"] = rest[1]
        d["fourth_forbidden"] = True
        d["excluded"] = rest
    else:
        d["target"] = [base, base + 1, base + 2]   # 通したい/受理したい3本
        d["fourth"] = base + 3                     # キューブを完成させる4本目
        # 4本目を「触れてはいけない網」にするか(=1行では書けなくなる)。
        # ★one_line の世界では 4本目を許せないと正解が存在しないので必ず許容側にする。
        # ★BL-121: lean_hole は4本目の名指しが排他の唯一の錨=必ず禁止。
        #   lean_only は「のみ」だけで過剰被覆を落とすのが主題=名指ししない。
        if d["world"] == "lean_hole":
            d["fourth_forbidden"] = True
        elif d["world"] in ("one_line", "lean_only"):
            d["fourth_forbidden"] = False
        else:
            d["fourth_forbidden"] = rnd.random() < 0.5
        d["outsider"] = base + 5                   # ★上位キューブの中に置く
        d["excluded"] = ([d["fourth"]] if d["fourth_forbidden"] else []) \
            + [d["outsider"]]
    d["faraway"] = 250 if base < 200 else 1        # 明確に無関係な網(read の錯乱肢用)

    # サーバ網(宛先側)とポート
    d["srv"] = f"172.{rnd.randint(16, 31)}.{rnd.randint(1, 200)}"
    d["srv_host"] = f"{d['srv']}.{rnd.randint(10, 99)}"
    d["port"] = rnd.choice([22, 80, 443, 3389])
    # ★対照用: 許可してはいけない「別のポート」「別の宛先」
    d["other_port"] = rnd.choice([p for p in (21, 23, 25, 8080)
                                  if p != d["port"]])
    d["other_host"] = f"{d['srv']}.{rnd.randint(100, 199)}"
    # --- 多エントリ読解(dense_list)用の値 ---
    d["dns"] = f"{d['srv']}.{rnd.randint(200, 250)}"
    d["mgmt_net"] = rnd.choice([o for o in range(20, 240)
                                if o not in d["target"] + [d["fourth"],
                                                           d["outsider"]]])
    d["blk_net"] = d["target"][1]          # ★全面禁止され、後続の許可を影にする網
    d["hi_lo"] = rnd.choice([8000, 9000, 16384])
    d["deny_port"] = rnd.choice([p for p in (23, 21, 512)
                                 if p != d["other_port"]])
    d["dense_n"] = rnd.choice([7, 8])
    # ★近接肢の本数(ユーザ指摘 2026-08-11「錯乱肢が明らかに一致しない行ばかりで
    #   実質3択になっている」)。**1フィールドだけ違う行**を混ぜて、
    #   1行ずつ突き合わせないと消せないようにする。
    d["dense_near"] = 2            # 中核に固定で2本(行数を9に保つ)
    d["srcport_kind"] = rnd.choice(["dns", "gt"])   # ★送信元ポートの軸
    # ★compare 形は `range` の境界を突けると密度が上がる。盤面の半分で入れる
    #   (常に入れると特徴の多様性が落ちるため)。
    d["_want_range"] = rnd.random() < 0.5
    # ★ACL の形式。拡張でしか起きない故障種は必ず拡張。
    #   アドレス系は標準/拡張のどちらでも成立するので抽選する。
    #   ★これを持たせる前は **要件が宛先とポートを指定しているのに標準 ACL しか
    #     出さない**という不整合があった(標準は送信元しか見ないので要件を字面どおり
    #     満たせない)。要件文は aclform に追随させること。
    d["aclform"] = ("ext" if d["kind"] in EXT_ONLY_KINDS
                    else ("ext" if rnd.random() < 0.5 else "std"))
    # ★mask_as_wildcard は**標準 ACL 固有**の罠(2行目はプロトコルも宛先も持たない
    #   素のアドレス指定)。拡張形にすると1行目だけ拡張・2行目は標準という
    #   混在になり、見出し(Standard/Extended)と中身が食い違う。
    if d["kind"] == "mask_as_wildcard":
        d["aclform"] = "std"
    if d["kind"] in DENSE_KINDS:
        d["aclform"] = "ext"           # 多エントリ読解は拡張でしか作れない
    if d["kind"] in EST_KINDS + EST_BUILD_KINDS:
        d["aclform"] = "ext"           # established は拡張 ACL でしか書けない
    if d["kind"] in PLACE_KINDS:
        # ★apply 形の ACL は送信元だけを見る標準形。番号も標準帯でなければ
        #   `Standard IP access list 150` のような**実機にあり得ない見出し**になる。
        d["aclform"] = "std"
    # 隣接ルータ(routefilter の src 側)
    d["nb_up"] = f"10.{a}.254.2"
    d["nb_dn"] = f"10.{a}.253.3"
    d["acl_num"] = rnd.choice([10, 20, 30, 50, 70])          # 標準帯
    d["acl_ext"] = rnd.choice([101, 110, 120, 130, 150])     # 拡張帯
    d["acl_name"] = rnd.choice(["FILTER-IN", "CUST-IN", "EDGE-IN", "RT-IN"])
    # ★apply_wrong_acl 用の「もう1枚」。同じ帯から別番号を採る
    #   (帯が違うと標準/拡張の別で見分けが付いてしまう)。
    d["acl_other"] = rnd.choice([n for n in [10, 20, 30, 50, 70]
                                 if n != d["acl_num"]]) \
        if d["aclform"] != "ext" \
        else rnd.choice([n for n in [101, 110, 120, 130, 150]
                         if n != d["acl_ext"]])
    # --- 適用点(BL-109)。被験デバイスの IF は3本 ---
    slot = rnd.choice([0, 1, 2])
    d["if_dn"] = f"Ethernet{slot}/0"      # 顧客の側
    d["if_up"] = f"Ethernet{slot}/1"      # サーバの側
    d["if_mgmt"] = f"Ethernet{slot}/2"    # 管理セグメント
    d["mgmt_o3"] = 255                    # 管理セグメントの第3オクテット
    names = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(ROLES, names))
    d["roles"] = list(ROLES)
    if (d["role"] == "filter" and d["kind"] not in DENSE_KINDS
            and (d["kind"] not in APPLY_KINDS
                 or d["kind"] in EST_BUILD_KINDS)):
        verify_select(d)                # select 形の一意性を機械検証
    if d["kind"] in PLACE_KINDS:
        verify_apply(d)                 # apply 形の一意性を機械検証
    # ★「症状の無い故障」を作らない。対象集合の形を世界で変えられるようにしたことで、
    #   仕込んだはずの誤り(例: 非連続ワイルドカード)が**その世界では正しい**という
    #   組み合わせが生まれた(wc_bits × wc_split)。機械で弾く。
    if d["kind"] in ADDR_KINDS + EXT_ONLY_KINDS:
        _ents, _s, _n = current_entries(d)
        if _ents and _select_works(d, _ents):
            raise ValueError(f"acl: 症状の無い盤面 kind={d['kind']} "
                             f"world={d['world']}")
    return d


def compatible_worlds(d_kind):
    return worlds_for(d_kind)


def net(d, o3, host=0):
    return f"{d['oct1']}.{d['oct2']}.{o3}.{host}"


# --------------------------------------------------------------------------
# ACL の組み立て(entries は acl_model / acl_cover 共通形式)
# --------------------------------------------------------------------------
def _std(d, action, o3, wc3, seq):
    return ac.entry(action, None, src=net(d, o3), sw=f"0.0.{wc3}.255", seq=seq)


def _ext(d, action, o3, wc3, seq, proto="tcp", dst=None, dport=True,
         sport=False, dst_any=False):
    """拡張 ACL のエントリ。既定= `<action> tcp <src> <wc> host <SRV> eq <port>`。

    sport=True で **eq を送信元側に置く**(port_swap の再現)。
    dst_any=True で宛先を any に。proto="ip" でポートの制限が消える。
    """
    dst_ip = "0.0.0.0" if dst_any else (dst or d["srv_host"])
    dst_w = "255.255.255.255" if dst_any else "0.0.0.0"
    op = ("eq", [d["port"]])
    return ac.entry(action, proto, src=net(d, o3), sw=f"0.0.{wc3}.255",
                    dst=dst_ip, dw=dst_w,
                    sport=(op if (proto in ("tcp", "udp") and sport) else None),
                    dport=(op if (proto in ("tcp", "udp") and dport
                                  and not sport) else None),
                    seq=seq)


def _row(d, action, o3, wc3, seq):
    """aclform に応じて標準/拡張のどちらかで1行を作る。"""
    return (_std(d, action, o3, wc3, seq) if d["aclform"] == "std"
            else _ext(d, action, o3, wc3, seq))


def _row_txt(d, action, o3, wc3):
    if d["aclform"] == "std":
        return f"{action} {net(d, o3)} 0.0.{wc3}.255"
    return (f"{action} tcp {net(d, o3)} 0.0.{wc3}.255 "
            f"host {d['srv_host']} eq {_port_txt(d['port'])}")


# --------------------------------------------------------------------------
# 多エントリ読解 (dense_list)
# ★狙い= first-match を**実際にたどらせる**。1行ごとに
#   「プロトコル / 送信元 / 宛先 / ポート演算子 / フラグ」を突き合わせないと解けない。
# --------------------------------------------------------------------------
def dense_entries(d):
    """★**常に9行**。中核4行＋特徴5行(盤面から決定的に選ぶ)。

    行数を固定するのは counter 形の選択肢が A〜J に収まるようにするため
    (9行＋「どの行も増えない」= 10択)。

    中核(順序に意味がある):
      1 特定ポートの全面禁止 / 2 正規の許可 /
      3・4 **近接肢**(1フィールドだけ違う・生きている) /
      5 ある網の全面禁止 → 6 をその影にする
    特徴(末尾に3行): DNS / ICMP タイプ / ポート範囲 / established /
      ★**送信元ポート**(DNS 応答・エフェメラル)
    """
    e, seq = [], 10

    def add(ent):
        nonlocal seq
        e.append(dict(ent, seq=seq))
        seq += 10

    srv, dns, blk = d["srv_host"], d["dns"], d["blk_net"]
    add(ac.entry("deny", "tcp", src="0.0.0.0", sw="255.255.255.255",
                 dst=srv, dw="0.0.0.0", dport=("eq", [d["deny_port"]])))
    add(ac.entry("permit", "tcp", src=net(d, d["target"][0]), sw="0.0.0.255",
                 dst=srv, dw="0.0.0.0", dport=("eq", [d["port"]])))
    # ★近接肢(probe と1フィールドだけ違う。影より前なので生きている)
    add(ac.entry("permit", "tcp", src=net(d, blk), sw="0.0.0.255",
                 dst=srv, dw="0.0.0.0", dport=("eq", [d["other_port"]])))
    add(ac.entry("permit", "udp", src=net(d, blk), sw="0.0.0.255",
                 dst=srv, dw="0.0.0.0", dport=("eq", [d["port"]])))
    # ★影を作る組
    add(ac.entry("deny", "ip", src=net(d, blk), sw="0.0.0.255",
                 dst="0.0.0.0", dw="255.255.255.255"))
    add(ac.entry("permit", "tcp", src=net(d, blk), sw="0.0.0.255",
                 dst=srv, dw="0.0.0.0", dport=("eq", [d["port"]])))
    # --- 末尾の特徴3行 ---
    pool = {
        # ★送信元ポート: DNS サーバからの応答(送信元 53)
        "srcport_dns": ac.entry("permit", "udp", src=dns, sw="0.0.0.0",
                                sport=("eq", [53]),
                                dst="0.0.0.0", dw="255.255.255.255"),
        # ★送信元ポート: エフェメラルからの接続だけ許可
        "srcport_gt": ac.entry("permit", "tcp", src="0.0.0.0",
                               sw="255.255.255.255", sport=("gt", [1023]),
                               dst=srv, dw="0.0.0.0",
                               dport=("eq", [d["other_port"]])),
        "dns": ac.entry("permit", "udp", src="0.0.0.0", sw="255.255.255.255",
                        dst=dns, dw="0.0.0.0", dport=("eq", [53])),
        "icmp": ac.entry("permit", "icmp", src="0.0.0.0",
                         sw="255.255.255.255", dst="0.0.0.0",
                         dw="255.255.255.255", icmp_type=0),
        "range": ac.entry("permit", "tcp", src="0.0.0.0",
                          sw="255.255.255.255", dst=srv, dw="0.0.0.0",
                          dport=("range", [d["hi_lo"], d["hi_lo"] + 10])),
        "est": ac.entry("permit", "tcp", src=srv, sw="0.0.0.0",
                        dst="0.0.0.0", dw="255.255.255.255",
                        established=True),
    }
    # ★送信元ポートの行は必ず1本入れる(ユーザ要望 2026-08-11)
    must = ["srcport_dns" if d["srcport_kind"] == "dns" else "srcport_gt"]
    # ★compare 形の盤面では `range` も必ず入れる(出題 20260811-010 の反省=
    #   `range` が無いと「どの行にも当たらない」フローが生まれ、
    #   そのフローだけ判定が早く終わって比較の密度が落ちる)。
    if d.get("_want_range"):
        must.append("range")
    rest = [k for k in ("dns", "icmp", "range", "est") if k not in must]
    pick = zlib.crc32(f"{d['base']}:{d['oct2']}:{d['hi_lo']}".encode())
    chosen = must + [rest[(pick + i) % len(rest)]
                     for i in range(3 - len(must))]
    seen = []
    for k in chosen:
        if k not in seen:
            seen.append(k)
    for k in ("dns", "icmp", "range", "est"):   # 3行に満たなければ補充
        if len(seen) >= 3:
            break
        if k not in seen:
            seen.append(k)
    for k in seen[:3]:
        add(pool[k])
    d["_dense_feat"] = seen[:3]
    return e


def dense_probes(d):
    """(表示文, ベクタ)。★1本ごとに違う軸を突く。"""
    srv, dns = d["srv_host"], d["dns"]
    t0, blk = d["target"][0], d["blk_net"]
    out = [
        (f"`{net(d, t0, 5)}` から `{srv}` の TCP ポート {d['port']} 宛て",
         {"proto": "tcp", "src": net(d, t0, 5), "dst": srv, "sport": 40001,
          "dport": d["port"], "established": False, "icmp_type": None}),
        (f"`{net(d, blk, 5)}` から `{srv}` の TCP ポート {d['port']} 宛て",
         {"proto": "tcp", "src": net(d, blk, 5), "dst": srv, "sport": 40002,
          "dport": d["port"], "established": False, "icmp_type": None}),
        (f"`{net(d, t0, 6)}` から `{srv}` の TCP ポート {d['deny_port']} 宛て",
         {"proto": "tcp", "src": net(d, t0, 6), "dst": srv, "sport": 40003,
          "dport": d["deny_port"], "established": False, "icmp_type": None}),
        (f"`{net(d, d['mgmt_net'], 7)}` から `{dns}` の UDP ポート 53 宛て",
         {"proto": "udp", "src": net(d, d["mgmt_net"], 7), "dst": dns,
          "sport": 51000, "dport": 53, "established": False,
          "icmp_type": None}),
        (f"`{net(d, d['mgmt_net'], 8)}` から `{srv}` 宛ての "
         f"ICMP エコー要求(type 8)",
         {"proto": "icmp", "src": net(d, d["mgmt_net"], 8), "dst": srv,
          "sport": None, "dport": None, "established": False, "icmp_type": 8}),
        (f"`{net(d, d['mgmt_net'], 9)}` から `{srv}` 宛ての "
         f"ICMP エコー応答(type 0)",
         {"proto": "icmp", "src": net(d, d["mgmt_net"], 9), "dst": srv,
          "sport": None, "dport": None, "established": False, "icmp_type": 0}),
        (f"`{net(d, d['mgmt_net'], 10)}` から `{srv}` の "
         f"TCP ポート {d['hi_lo'] + 5} 宛て",
         {"proto": "tcp", "src": net(d, d["mgmt_net"], 10), "dst": srv,
          "sport": 40004, "dport": d["hi_lo"] + 5, "established": False,
          "icmp_type": None}),
        (f"`{net(d, d['mgmt_net'], 11)}` から `{srv}` の "
         f"TCP ポート {d['hi_lo'] + 50} 宛て",
         {"proto": "tcp", "src": net(d, d["mgmt_net"], 11), "dst": srv,
          "sport": 40005, "dport": d["hi_lo"] + 50, "established": False,
          "icmp_type": None}),
    ]
    if d["dense_n"] >= 8:
        out.append(
            (f"`{srv}` から `{net(d, t0, 12)}` 宛ての、"
             "確立済みのセッションに属する TCP セグメント",
             {"proto": "tcp", "src": srv, "dst": net(d, t0, 12),
              "sport": d["port"], "dport": 40006, "established": True,
              "icmp_type": None}))
    # ★近接肢の行を**多重一致の観測**にも使う(ACL の行数は増やさない)。
    #   これらは「近接肢の permit(先)」と「deny ip(後)」の両方に一致するので、
    #   counter 形の正解が **permit 行**になる組を作れる。
    #   → 「deny ip の行を探せばよい」というメタ解法が誤答を引く近道に変わる。
    if d["dense_near"] >= 1:
        out.append(
            (f"`{net(d, blk, 13)}` から `{srv}` の "
             f"TCP ポート {d['other_port']} 宛て",
             {"proto": "tcp", "src": net(d, blk, 13), "dst": srv,
              "sport": 40007, "dport": d["other_port"], "established": False,
              "icmp_type": None}))
    out.append(
        (f"`{net(d, blk, 14)}` から `{srv}` の UDP ポート {d['port']} 宛て",
         {"proto": "udp", "src": net(d, blk, 14), "dst": srv,
          "sport": 51001, "dport": d["port"], "established": False,
          "icmp_type": None}))
    # ★送信元ポートが効く観測(同じ組で送信元ポートだけ違えている)
    if d.get("srcport_kind") == "dns":
        out.append(
            (f"`{dns}` の **UDP ポート 53 発**で `{net(d, d['mgmt_net'], 20)}` "
             "宛ての応答",
             {"proto": "udp", "src": dns, "dst": net(d, d["mgmt_net"], 20),
              "sport": 53, "dport": 51002, "established": False,
              "icmp_type": None}))
        out.append(
            (f"`{dns}` の **UDP ポート 5353 発**で "
             f"`{net(d, d['mgmt_net'], 21)}` 宛ての応答",
             {"proto": "udp", "src": dns, "dst": net(d, d["mgmt_net"], 21),
              "sport": 5353, "dport": 51003, "established": False,
              "icmp_type": None}))
    else:
        out.append(
            (f"`{net(d, d['mgmt_net'], 22)}` の **TCP ポート 40100 発**で "
             f"`{srv}` の TCP ポート {d['other_port']} 宛て",
             {"proto": "tcp", "src": net(d, d["mgmt_net"], 22), "dst": srv,
              "sport": 40100, "dport": d["other_port"], "established": False,
              "icmp_type": None}))
        out.append(
            (f"`{net(d, d['mgmt_net'], 23)}` の **TCP ポート 80 発**で "
             f"`{srv}` の TCP ポート {d['other_port']} 宛て",
             {"proto": "tcp", "src": net(d, d["mgmt_net"], 23), "dst": srv,
              "sport": 80, "dport": d["other_port"], "established": False,
              "icmp_type": None}))
    return out


def target_entries(d):
    """「ちょうど対象の3本だけ」を表す基準の permit 集合(比較用)。"""
    return [_std(d, "permit", o, 0, (i + 1) * 10)
            for i, o in enumerate(d["target"])]


# --------------------------------------------------------------------------
# select 形(構築系)— 「このレンジを指定するのはどれか」
# --------------------------------------------------------------------------
def select_candidates(d):
    """(key, 表示行のリスト, entries) を返す。entries は acl_cover で厳密評価する。"""
    b = d["base"]
    out = []

    num = d["acl_num"] if d["aclform"] == "std" else d["acl_ext"]

    def std_lines(rows):
        return [f"access-list {num} {_row_txt(d, act, o, wc)}"
                for act, o, wc in rows]

    def ents(rows):
        return [_row(d, act, o, wc, (i + 1) * 10)
                for i, (act, o, wc) in enumerate(rows)]

    if d["kind"] in EST_BUILD_KINDS:
        return est_build_candidates(d)
    if d["world"] in NB_WORLDS:
        # ★1行では書けないレンジ。候補は「行数」と「deny を使うか」で競わせる。
        cands = [
            # 過剰被覆＋deny 先行= 2行(最小)
            ("deny1", [("deny", b + 7, 0), ("permit", b, 7)]),
            # ★大きさの違うキューブ3つに分解= 3行(deny を使わない中では最小)
            ("split3", [("permit", b, 3), ("permit", b + 4, 1),
                        ("permit", b + 6, 0)]),
            # 分解の仕方が最小でない= 4行
            ("split4", [("permit", b, 1), ("permit", b + 2, 1),
                        ("permit", b + 4, 1), ("permit", b + 6, 0)]),
            # 1行で書けると思った= base+7 まで通してしまう
            ("cube8", [("permit", b, 7)]),
            # 狭い= 前半4本しか通らない
            ("narrow", [("permit", b, 3)]),
            # ★成立しない deny 候補。これが無いと**正解が「唯一 deny を含む肢」**
            #   になり、要件に「deny 禁止」が無いことに気付くだけで
            #   **アドレスを検証せずに当てられる**(出題 20260811-015 で判明)。
            #   落とす網を1つずらすと、対象が1本欠けかつ除外が1本通る。
            ("deny_off", [("deny", b + 6, 0), ("permit", b, 7)]),
        ]
    elif d["world"] in WC_WORLDS:
        # ★ワイルドカードの組み立てが主題。1行の候補は**正解1つ+近い誤り3つ**にし、
        #   さらに「動くが1行でない」候補(厳密列挙・deny 先行)を混ぜる。
        pat = SRC_PATTERNS[d["world"]]
        a_off, a_wc = pat["ans"]
        # ★1本目(=ブロック全体 0.0.7.255「広すぎ」)は**常に入れる**。
        #   最も典型的な誤りなので、抽選で落ちる回があってはならない
        #   (WC トリック初出題 20260811-014 で実際に落ちた)。
        wide, rest = pat["near"][0], list(pat["near"][1:])
        pick = zlib.crc32(f"wc:{d['base']}:{d['oct2']}".encode()) % len(rest)
        near = [wide] + [rest[(pick + i) % len(rest)] for i in range(2)]
        cands = [("cube", [("permit", b + a_off, a_wc)])]
        cands += [(f"near{i}", [("permit", b + o, w)])
                  for i, (o, w) in enumerate(near)]
        cands.append(("exactN", [("permit", o, 0) for o in d["target"]]))
        cands.append(("deny_first",
                      [("deny", x, 0) for x in d["excluded"]]
                      + [("permit", b, 7)]))
    else:
        cands = [
            ("cube", [("permit", b, 3)]),                   # 1行(4本目も入る)
            ("exact3", [("permit", o, 0) for o in d["target"]]),  # 厳密3行
            ("deny_first", [("deny", d["fourth"], 0), ("permit", b, 3)]),
            ("narrow", [("permit", b, 1)]),                 # 狭い(2本だけ)
            ("wide", [("permit", b, 7)]),                   # 広い(8本)
            ("bits", [("permit", b, 5)]),                   # 非連続(飛び地)
        ]
    for key, rows in cands:
        out.append((key, std_lines(rows), ents(rows)))
    # ★サブネットマスクを書いてしまった候補(実測 P10: 正規化されて別物になる)
    #   0.0.3.255 のつもりで 255.255.252.0 と書く。IOS は受理し、
    #   don't care 側のビットがアドレスから落ちるため「まったく別の集合」になる。
    if d["aclform"] == "std":
        # ★正解のワイルドカードを**マスク形で書いてしまった**版にする。
        #   固定文字列(255.255.252.0)にすると WC トリック世界では正解と対応せず、
        #   「この選択肢だけ毛色が違う」という手掛かりになってしまう。
        if d["world"] in WC_WORLDS:
            _m_off, _m_wc = SRC_PATTERNS[d["world"]]["ans"]
        else:
            _m_off, _m_wc = 0, 3
        mask = f"255.255.{255 - _m_wc}.0"
        out.append((
            "maskish",
            [f"access-list {num} permit {net(d, b + _m_off)} {mask}"],
            [ac.entry("permit", None, src=net(d, b + _m_off), sw=mask,
                      seq=10)]))
    else:
        # ★拡張でしか作れない錯乱肢。いずれも「対象は通るが**別の何か**まで通る/
        #   通らない」ので、works() の対照(別ポート・別宛先)で機械的に落ちる。
        # ★3本すべて足すと9択になり多すぎる(実試験は6〜7択)。2本に絞る。
        _ext_pool = []
        out2 = _ext_pool.append
        # ★WC 世界では「アドレス指定は正しいが別の要素で外す」錯乱肢にする
        #   (0.0.3.255 固定のままだと、アドレスの時点で落ちて対照にならない)
        if d["world"] in WC_WORLDS:
            _a_off, _a_wc = SRC_PATTERNS[d["world"]]["ans"]
        else:
            _a_off, _a_wc = 0, 3
        _ab, _aw = net(d, b + _a_off), f"0.0.{_a_wc}.255"
        out2((
            "portswap",
            [f"access-list {num} permit tcp {_ab} {_aw} "
             f"eq {_port_txt(d['port'])} host {d['srv_host']}"],
            [_ext(d, "permit", b + _a_off, _a_wc, 10, sport=True)]))
        out2((
            "ipproto",
            [f"access-list {num} permit ip {_ab} {_aw} "
             f"host {d['srv_host']}"],
            [_ext(d, "permit", b + _a_off, _a_wc, 10, proto="ip")]))
        out2((
            "dstany",
            [f"access-list {num} permit tcp {_ab} {_aw} "
             f"any eq {_port_txt(d['port'])}"],
            [_ext(d, "permit", b + _a_off, _a_wc, 10, dst_any=True)]))
        # 盤面から決定的に2本を選ぶ(seed 依存・再現性を保つ)
        pick = zlib.crc32(f"{d['base']}:{d['oct2']}:{d['port']}"
                          .encode()) % 3
        out += [_ext_pool[(pick + i) % 3] for i in range(2)]
    return out


def _vec_at(d, o3, dst=None, dport=None):
    return {"proto": "tcp", "src": net(d, o3, 5),
            "dst": dst or d["srv_host"], "sport": 12345,
            "dport": dport or d["port"], "established": False,
            "icmp_type": None}


def _select_works(d, entries):
    """対象3本を**すべて**許可し、許してはいけないものを**1つも**許可しないか。

    ★拡張形では「別のポート」「別の宛先」も対照に入れる。これを入れないと
      `permit ip <cube> host SRV`(ポート制限なし)や
      `permit tcp <cube> any eq <port>`(宛先 any)が「直る候補」として通ってしまう。
    """
    if not entries:
        return False
    if d["kind"] in EST_BUILD_KINDS:
        return est_build_works(d, entries)
    for o in d["target"]:
        if not acl_model.evaluate(entries, _vec_at(d, o)):
            return False
    for o in d["excluded"]:
        if acl_model.evaluate(entries, _vec_at(d, o)):
            return False
    if d["aclform"] == "ext":
        t0 = d["target"][0]
        if acl_model.evaluate(entries, _vec_at(d, t0, dport=d["other_port"])):
            return False
        if acl_model.evaluate(entries, _vec_at(d, t0, dst=d["other_host"])):
            return False
    return True


def _exact_ext(d, entries):
    """拡張形の「過剰に許可しない」= 4本目(fourth)まで通していないこと。"""
    return not acl_model.evaluate(entries, _vec_at(d, d["fourth"]))


def _select_complies(d, lines, entries):
    """提示側の要件(行数・deny の有無)＋「過剰に許可しないこと」。"""
    w = d["world"]
    if d["kind"] in EST_BUILD_KINDS:
        return True                    # 一意性は構造から出る(制約で絞らない)
    exact = (ac.permits_exactly(entries, target_entries(d))
             if d["aclform"] == "std" else _exact_ext(d, entries))
    if w == "nb_min":
        return exact               # 行数の最小性は verify_select で解く
    if w == "nb_no_deny":
        return exact and all(" deny " not in ln for ln in lines)
    if w in WC_WORLDS or w == "one_line":
        return len(lines) == 1
    if w == "exact_no_deny":
        return exact and all(" deny " not in ln for ln in lines)
    if w == "exact_min":
        return exact                    # 行数の最小性は verify_select で解く
    if w == "lean_only":
        # ★BL-121: 非包含の明文は無いが「のみ」が排他を担う(deny 禁止下では
        #   permit 一致=通過なので、のみ⇒正確被覆が定理)。機械判定は
        #   exact_no_deny と同一。
        return exact and all(" deny " not in ln for ln in lines)
    if w == "lean_hole":
        # ★BL-121: 「のみ」も無い。排他は名指し禁止網(excluded)が担い、
        #   それは _select_works が既に落としている。残る要件は deny 禁止のみ。
        return all(" deny " not in ln for ln in lines)
    raise ValueError(w)


def verify_select(d):
    """「直る候補≥2・要件適合=ちょうど1」を機械検証する(pbr/urpf と同じ被覆エンジン)。

    ★意味的に等価な候補(厳密列挙 と deny 先行)は**畳まない**。
      要件世界が提示の軸(行数・deny の有無)で選ぶので、等価でも別の選択肢として成立する。
    """
    works = [(k, l, e) for k, l, e in select_candidates(d)
             if _select_works(d, e)]
    ok = [(k, l, e) for k, l, e in works if _select_complies(d, l, e)]
    if d["world"] in ("exact_min",) + NB_WORLDS and len(ok) > 1:
        least = min(len(l) for _k, l, _e in ok)
        ok = [x for x in ok if len(x[1]) == least]
    if len(works) < 2 and d["kind"] not in EST_BUILD_KINDS:
        raise ValueError(f"acl select 直る候補不足: kind={d['kind']} "
                         f"world={d['world']} works={[k for k, _, _ in works]}")
    if len(ok) != 1:
        raise ValueError(f"acl select 一意性違反: kind={d['kind']} "
                         f"world={d['world']} works={[k for k, _, _ in works]} "
                         f"ok={[k for k, _, _ in ok]}")
    d["_select_correct"] = ok[0][0]
    d["_select_works"] = [k for k, _, _ in works]
    return d["_select_correct"]


WHY_SELECT = {
    "cube": "対象としていないネットワークまでが、一致の対象に含まれる。",
    "exact3": "エントリが複数の行に分かれている。",
    "deny_first": "拒否のエントリが用いられている。",
    "narrow": "対象としているネットワークのうち、一部が一致の対象から外れる。",
    "wide": "対象としていないネットワークまでが、一致の対象に含まれる。",
    "bits": "ワイルドカードのビットが連続しておらず、"
            "対象としていないネットワークが一致の対象に含まれる。",
    "maskish": "ワイルドカードとしてサブネット・マスクが記述されており、"
               "一致の対象が意図したものと異なる。",
    "portswap": "ポートの演算子が**送信元の側**に記述されているため、"
                "実際のクライアントからの通信には一致しない。",
    "ipproto": "プロトコルが ip であるため、ポートによる制限が行われず、"
               "当該のサーバの他のポートへの通信までが許可される。",
    "dstany": "宛先が any であるため、当該のサーバ以外の宛先への通信までが"
              "許可される。",
}


def _why_near(d, ents):
    """★1行の錯乱肢の理由は**盤面から計算**する(WC トリック世界は候補が可変なので、
    静的な表に書くと『広すぎる』『狭すぎる』を取り違える)。"""
    over = any(acl_model.evaluate(ents, _vec_at(d, o)) for o in d["excluded"])
    under = any(not acl_model.evaluate(ents, _vec_at(d, o)) for o in d["target"])
    if over and under:
        return ("対象としているネットワークの一部が一致の対象から外れ、"
                "かつ対象としていないネットワークが一致の対象に含まれる。")
    if over:
        return "対象としていないネットワークまでが、一致の対象に含まれる。"
    if under:
        return "対象としているネットワークのうち、一部が一致の対象から外れる。"
    return "示されている要件を満たさない。"


def build_choices_select(d, rnd):
    correct = d["_select_correct"]
    out = []
    for key, lines, ents in select_candidates(d):
        txt = " / ".join(f"`{ln}`" for ln in lines)
        if key == correct:
            why = ""
        elif d["kind"] in EST_BUILD_KINDS:
            # ★同じ key 名(ipproto 等)が往路用の理由表にもあるので**先に**引く
            why = EST_BUILD_WHY.get(key, "示されている要件を満たさない。")
        elif key in WHY_SELECT:
            why = WHY_SELECT[key]
        elif key == "exactN":
            why = "エントリが複数の行に分かれている。"
        elif key in EST_BUILD_WHY:
            why = EST_BUILD_WHY[key]
        elif key in ("deny1", "split3", "split4", "cube8", "deny_off"):
            why = _why_near(d, ents)
        else:
            why = _why_near(d, ents)
        # ★「直りはするが要件に合わない」候補の理由は、意味ではなく提示の軸で書く
        if key != correct and key in d["_select_works"]:
            why = {w: "エントリが1行に収まっていない。" for w in WC_WORLDS}
            why.update({"one_line": "エントリが1行に収まっていない。",
                   "exact_no_deny": ("拒否のエントリが用いられている。"
                                     if any(" deny " in ln for ln in lines)
                                     else "対象としていないネットワークまでが"
                                          "一致の対象に含まれる。"),
                   "exact_min": "より少ない行数で同じ結果が得られる。",
                   "nb_min": "より少ない行数で同じ結果が得られる。",
                   "nb_no_deny": ("拒否のエントリが用いられている。"
                                  if any(" deny " in ln for ln in lines)
                                  else "より少ない行数で同じ結果が得られる。"),
                   # ★BL-121: lean_only は導出チェーンごと説明する
                   "lean_only": ("拒否のエントリが用いられている。"
                                 if any(" deny " in ln for ln in lines)
                                 else "「のみ」の要件に反する(拒否のエントリが"
                                      "禁止されている以上、permit への一致は"
                                      "通過を意味し、対象外のネットワークが"
                                      "許可されてしまう)。"),
                   "lean_hole": "拒否のエントリが用いられている。",
                   })
            why = why[d["world"]]
        # ★BL-121 lean_hole: 過剰被覆の候補は works 前で死ぬ(名指し網を踏む)。
        #   汎用の「対象外まで含まれる」でなく名指し違反として説明する。
        if key != correct and d["world"] == "lean_hole" \
                and key not in d["_select_works"] \
                and why.startswith("対象としていないネットワークまでが"):
            why = ("許可されることはできないと指定されている"
                   "ネットワークが、一致の対象に含まれる。")
        out.append((txt, key == correct, why, lines))
    order = list(range(len(out)))
    rnd.shuffle(order)
    return [out[i] for i in order]


# --------------------------------------------------------------------------
# 現在状態(故障している ACL)— read / cause 形の土台
# --------------------------------------------------------------------------
def current_entries(d):
    """kind に応じた「いま入っている ACL」。(entries, 標準か, 表示名) を返す。"""
    k, b = d["kind"], d["base"]
    ext = d.get("aclform") == "ext"
    num = str(d["acl_ext"] if ext else d["acl_num"])
    if k == "wc_narrow":
        return [_row(d, "permit", b, 1, 10)], not ext, num
    if k == "wc_wide":
        return [_row(d, "permit", b, 7, 10)], not ext, num
    if k == "wc_bits":
        return [_row(d, "permit", b, 5, 10)], not ext, num
    if k == "mask_as_wildcard":
        # ★1行目は正しく書けており、2行目だけワイルドカードの代わりに
        #   サブネット・マスクを書いてしまっている。
        #   実測(§10)どおり don't care 側のビットがアドレスから落ちるため、
        #   `10.a.base.0 255.255.252.0` は「第3オクテットの下位2ビットが 0 かつ
        #   第4オクテットが 0」という**まったく別の集合**になり、
        #   実際のホスト宛てトラフィックには一致しない(=対象の残り2本が落ちる)。
        return ([_row(d, "permit", d["target"][0], 0, 10),
                 ac.entry("permit", None, src=net(d, b), sw="255.255.252.0",
                          seq=20)], True, str(d["acl_num"]))
    if k == "order_shadow":
        # 先行の広い permit が、後続の「特定網だけ拒否」を影にする
        return ([_row(d, "permit", b, 7, 10),
                 _row(d, "deny", d["outsider"], 0, 20)], not ext, num)
    # --- 拡張 ACL でしか起きない誤り ---
    if k == "port_swap":
        # ★1行目は正しく、2行目だけ eq を送信元側に書いてしまっている。
        #   実クライアントの送信元ポートは任意なので、その行は一致しない。
        return ([_ext(d, "permit", d["target"][0], 0, 10),
                 _ext(d, "permit", b, 3, 20, sport=True)], False, num)
    if k == "proto_ip_not_tcp":
        # プロトコルが ip なのでポートの制限が効かない(別ポートまで通る)
        return ([_ext(d, "permit", b, 3, 10, proto="ip")], False, num)
    if k == "dst_any_too_wide":
        # 宛先が any なのでサーバ以外まで通る
        return ([_ext(d, "permit", b, 3, 10, dst_any=True)], False, num)
    if k == "dense_list":
        return dense_entries(d), False, num
    # --- 適用点(BL-109 段A)。返すのは「**いま効いている** ACL」 ---
    #   盤面に定義されている ACL 全部は defined_acls() が返す。
    if k == "apply_wrong_acl":
        # 適用されているのは**広いほう**。対象外の網まで通ってしまう。
        return _wrong_acl(d), not ext, str(d["acl_other"])
    if k in EST_KINDS + EST_BUILD_KINDS:
        # ★往路に効いているのは顧客側のリスト。復路は defined_acls / apply_map 側。
        return _fwd_acl(d, est=(k == "est_wrong_side")), False, est_refs(d)[0]
    if k in PLACE_KINDS:
        return None, d.get("aclform") != "ext", num   # まだ適用されていない
    if k in ("apply_missing", "apply_other_iface") + tuple(DIRECTION_KINDS):
        # 中身は要件どおりだが、**往路には効いていない**。
        #   未適用/別IF → 全許可 / 向きの取り違え → 往路は素通りで**復路が落ちる**
        #   (どちらも「効いている ACL は無い」なので None。判定は session_ok が行う)
        return None, not ext, num
    if k == "filter_undef_ref":
        return None, True, d["acl_name"]           # 定義そのものが無い(実測 §1)
    if k == "filter_empty_acl":
        return [], True, d["acl_name"]             # 定義はあるが空(実測 §2)
    # --- routefilter 系 ---
    if k == "std_len_blind":
        return ([_std(d, "deny", d["target"][0], 0, 10),
                 ac.entry("permit", None, seq=20)], True, str(d["acl_num"]))
    if k == "ext_src_is_network":
        # ★1行目は**正しい**書き方(src=広告元の隣接ルータ / dst=広告された網)で、
        #   2行目だけ src に「網」を書いてしまっている。実測(§4-2 E2/E4)のとおり
        #   src はネットワークではないので、2行目は**何にも一致しない**。
        #   → 1本だけ受理され、残りは暗黙の拒否で消える(部分的な症状になる)。
        return ([ac.entry("permit", "ip", src=d["nb_up"], sw="0.0.0.0",
                          dst=net(d, d["target"][0]), dw="0.0.0.0", seq=10),
                 ac.entry("permit", "ip", src=net(d, d["target"][1]),
                          sw="0.0.0.0", seq=20)], False, str(d["acl_ext"]))
    if k == "ext_named_rejected":
        return ([ac.entry("permit", "ip", src=d["nb_up"], sw="0.0.0.0",
                          seq=10)], False, d["acl_name"])
    if k == "undef_ref":
        # ★識別子は名前で統一する(evidence 形で3仮説を区別不能にするため。
        #   番号と名前が混ざると `show running-config` の見え方だけで割れてしまう)。
        # ★実測 P15= **未定義を参照しても ACL は自動生成されない**
        #   (`show ip access-lists` は空のまま)。よって「未定義」と「空」は
        #   出力で区別できる = 仮説として並立する。
        return None, True, d["acl_name"]           # 定義そのものが無い
    if k == "empty_acl":
        return [], True, d["acl_name"]             # 定義はあるが中身が空
    # --- P1c で追加したロール ---
    if k == "copp_deny_to_default":
        # ★deny は「通す」ではなく「このクラスに入れない」= class-default 行き(実測 §8)
        return ([ac.entry("deny", "icmp", src=net(d, d["target"][0], 5),
                          sw="0.0.0.0", seq=10),
                 ac.entry("permit", "icmp", seq=20)], False, d["acl_name"])
    if k == "urpf_undef_exempt":
        return None, True, str(d["acl_num"])       # 例外リストが未定義= 全免除
    if k == "nat_deny_scope":
        # VPN 宛だけ変換から外すつもりが、ワイルドカードが広く業務網まで除外している
        return ([_std(d, "deny", b, 1, 10),        # base と base+1 を除外(広すぎ)
                 _std(d, "permit", b, 7, 20)], True, str(d["acl_num"]))
    if k == "vty_wc_wrong":
        # 管理端末のいるネットワークが許可範囲から外れている
        return ([_std(d, "permit", d["target"][0], 0, 10)], True,
                str(d["acl_num"]))
    raise ValueError(k)


# --------------------------------------------------------------------------
# ロール写像層(P1c で 6 ロールに拡張)
# ★同じ permit/deny でも、着ている衣装によって**帰結が違う**というのが本 shape の核。
#   未定義・空 ACL の帰結もロールで割れる(実測 poc/acl §1)。
# --------------------------------------------------------------------------
def _vec(d, o3):
    return {"proto": "tcp", "src": net(d, o3, 5), "dst": d["srv_host"],
            "sport": 12345, "dport": d["port"], "established": False,
            "icmp_type": None}


def _icmp_vec(d, o3):
    return {"proto": "icmp", "src": net(d, o3, 5), "dst": d["srv_host"],
            "sport": None, "dport": None, "established": False,
            "icmp_type": 8}


def copp_to_default(d, o3):
    """CoPP: この送信元は **class-default に落ちるか**。

    ★実測 §8= ACL の deny に当たった分は「通る」のではなく、
      クラスに入らず class-default(=既定の police)で処理される。
    """
    ents, _s, _n = current_entries(d)
    if not ents:
        return True                       # 未定義・空= 何にも一致しない(実測 §1)
    return not acl_model.evaluate(ents, _icmp_vec(d, o3))


def urpf_exempt(d, o3):
    """uRPF: この送信元は**例外として免除されるか**(=RPF 失敗でも通る)。"""
    ents, _s, _n = current_entries(d)
    if ents is None or ents == []:
        return True                       # ★未定義= 全免除(実測 §1・uRPF が無力化)
    return acl_model.evaluate(ents, {"proto": "ip", "src": net(d, o3, 5),
                                     "dst": "0.0.0.0"})


def nat_translated(d, o3):
    """NAT: この送信元は**変換されるか**。deny= 変換しない(素通り)。"""
    ents, _s, _n = current_entries(d)
    if ents is None or ents == []:
        return False                      # ★未定義= 変換されない(実測 §1・逆の帰結)
    return acl_model.evaluate(ents, {"proto": "ip", "src": net(d, o3, 5),
                                     "dst": "0.0.0.0"})


def vty_allowed(d, o3):
    """vty: この送信元からの管理接続が**受理されるか**。"""
    ents, _s, _n = current_entries(d)
    if ents is None or ents == []:
        return True
    return acl_model.evaluate(ents, {"proto": "ip", "src": net(d, o3, 5),
                                     "dst": "0.0.0.0"})


def read_labels(d):
    """(観測列の見出し, 真の語, 偽の語, 設問の主語(真側/偽側))。"""
    r = d["role"]
    if d["kind"] in EST_KINDS + EST_BUILD_KINDS:
        # ★戻り通信の盤面は**セッションが張れるか**が観測。到達可/不可より正確
        #   (実測 §17= 往路で落ちたか復路で落ちたかは TCP の応答で割れる)。
        return ("TCP セッション", "確立できる", "確立できない",
                "セッションを確立できるもの", "セッションを確立できないもの")
    if r == "filter":
        return ("サーバへの到達", "到達可", "到達不可", "転送されるもの",
                "破棄されるもの")
    if r == "routefilter":
        return ("ルーティング テーブル", "保持される", "除外される",
                "ルーティング・テーブルに保持されるもの",
                "ルーティング・テーブルから除外されるもの")
    if r == "copp":
        return ("分類されるクラス", "class-default", "CM-MGMT",
                "class-default に分類されるもの",
                "定義されたクラスに分類されるもの")
    if r == "urpf":
        return ("検証の結果", "免除される", "破棄される",
                "検証から免除されるもの", "検証によって破棄されるもの")
    if r == "nat":
        return ("アドレスの変換", "変換される", "変換されない",
                "変換されるもの", "変換されないもの")
    return ("管理接続", "受理される", "拒否される",
            "接続が受理されるもの", "接続が拒否されるもの")


def _right_acl(d):
    """要件どおりに書けている ACL(適用点の故障で「中身は正しい」側になるもの)。"""
    return [_row(d, "permit", o, 0, 10 + i * 10)
            for i, o in enumerate(d["target"])]


def _wrong_acl(d):
    """誤って適用されている別の ACL。

    ★症状が**両方向**に出るように作る= 対象の1本を落とし(deny)、
      対象外の網まで通す(広い permit)。
    ★2行が重なる(deny の網は permit のキューブの中)ので counter 形も成立する。
    """
    return [_row(d, "deny", d["target"][1], 0, 10),
            _row(d, "permit", d["base"], 7, 20)]


def _fwd_acl(d, est=False):
    """往路用リスト= 顧客網からサーバの当該ポートへ。

    est=True で **`established` を付けてしまった**版(SYN に一致しなくなる)。
    """
    return [ac.entry("permit", "tcp", src=net(d, o), sw="0.0.0.255",
                     dst=d["srv_host"], dw="0.0.0.0",
                     dport=("eq", [d["port"]]), established=est,
                     seq=10 + i * 10)
            for i, o in enumerate(d["target"])]


def _ret_acl(d, est=True):
    """復路用リスト= サーバから顧客網への**戻り**だけを許可する。

    est=False で `established` の行が**無い**版(戻りが暗黙の拒否で落ちる)。
    ★est=False でも**リストは空にしない**(空だと実測 §2 のとおり全許可になり、
      「リストはあるのに戻りが通らない」という主題が消える)。
    """
    if est:
        # ★narrow=True で**顧客側の範囲を狭める**(前半だけ)。
        #   往路は全部通るのに、後半の顧客網だけ戻りが落ちる= 対比が作れる。
        wc = "0.0.1.255" if d["kind"] == "est_ret_narrow" else "0.0.7.255"
        return [ac.entry("permit", "tcp", src=d["srv_host"], sw="0.0.0.0",
                         sport=("eq", [d["port"]]),
                         dst=net(d, d["base"]), dw=wc,
                         established=True, seq=10)]
    return [ac.entry("permit", "ip", src=d["srv_host"], sw="0.0.0.0",
                     dst=f"{d['oct1']}.{d['oct2']}.{d['mgmt_o3']}.0",
                     dw="0.0.0.255", seq=10)]


def defined_acls(d):
    """`show ip access-lists` に現れるもの**全部**。(entries, 標準か, 名前) の列。

    ★通常は1枚だが、apply_wrong_acl だけは2枚出る(どちらが適用されているかを
      `ip access-group` 行で確かめさせるのが狙い)。
    """
    ents, is_std, name = current_entries(d)
    k = d["kind"]
    if k == "apply_wrong_acl":
        ext = d.get("aclform") == "ext"
        prim = str(d["acl_ext"] if ext else d["acl_num"])
        two = [(int(prim), _right_acl(d), not ext, prim),
               (int(d["acl_other"]), _wrong_acl(d), not ext,
                str(d["acl_other"]))]
        two.sort(key=lambda t: t[0])       # 実機は番号順に並べる
        return [(e, s, n) for _num, e, s, n in two]
    if k in EST_BUILD_KINDS:
        # ★復路用リストは**まだ書かれていない**。往路用だけを提示する。
        return [(_fwd_acl(d), False, est_refs(d)[0])]
    if k in EST_KINDS:
        fwd, ret = est_refs(d)
        return [(_fwd_acl(d, est=(k == "est_wrong_side")), False, fwd),
                (_ret_acl(d, est=(k != "est_missing")), False, ret)]
    if k in PLACE_KINDS:
        return [(place_acl(d), True, name)]
    if k in ("apply_missing", "apply_other_iface") + tuple(DIRECTION_KINDS):
        return [(_right_acl(d), is_std, name)]
    if ents is None:
        return []                                   # 未定義= 何も出ない
    return [(ents, is_std, name)]


def show_acl_text(d):
    """`show ip access-lists` の実機書式(実測 poc/acl §11 に忠実)。"""
    out = []
    for ents, is_std, name in defined_acls(d):
        head = ("Standard IP access list " if is_std
                else "Extended IP access list ")
        out.append(head + name)
        for e in ents:
            out.append("    " + _render_entry(e, is_std))
    return "\n".join(out)


# --------------------------------------------------------------------------
# 適用点(BL-109 段A)
# ★実測 poc/acl §16-1= 現行の `show run | section access-list|access-group|...`
#   では**インターフェイス名が出ない**(IOS の section は子行がマッチしても親を
#   出さない)ため、適用点を読み取る手段が盤面に存在しなかった。
#   → filter ロールは `show run | section ^interface` に差し替える。
# --------------------------------------------------------------------------
def apply_binding(d):
    """(適用先 IF or None, 方向, 参照している ACL の名前)。

    ★**保存せず kind から導出する**。evidence 形は kind を差し替えた仮想の盤面を
      作るので、保存値だと適用点だけ古いまま残る。
    """
    if d["role"] != "filter":
        return (None, None, None)
    k = d["kind"]
    ext = d.get("aclform") == "ext"
    prim = str(d["acl_ext"] if ext else d["acl_num"])
    if k == "apply_missing" or k in PLACE_KINDS:
        # ★apply 形(構築系)も**まだ適用されていない**状態で提示する。
        #   ここを既定値(顧客側の in)のままにすると、設問「どこに適用すべきか」に
        #   対して**すでに適用済みの構成**を見せることになり自己矛盾する。
        return (None, "in", prim)
    if k == "apply_other_iface":
        return (d["if_mgmt"], "in", prim)
    if k in ("filter_undef_ref", "filter_empty_acl"):
        return (d["if_dn"], "in", d["acl_name"])
    if k == "apply_wrong_acl":
        return (d["if_dn"], "in", str(d["acl_other"]))
    if k == "apply_direction":          # 同じ IF で向きだけ逆
        return (d["if_dn"], "out", prim)
    if k == "apply_iface_swap":         # 隣の IF の in
        return (d["if_up"], "in", prim)
    return (d["if_dn"], "in", prim)


# --------------------------------------------------------------------------
# 段B: 適用マップと**入口/出口の二段評価**
# ★実測 poc/acl §16-2= 入口の in と出口の out は**両方**で評価される。
#   §16-10= 要件どおりの ACL(末尾に permit any が無い)を復路に当たる位置へ付けると、
#   **往路は素通りのまま復路が暗黙の拒否で落ちる**(= 疎通しないのにカウンタは 0)。
# --------------------------------------------------------------------------
def est_refs(d):
    """戻り通信の盤面で使う2枚の ACL 名 (往路用, 復路用)。"""
    ext = d.get("aclform") == "ext"
    return (str(d["acl_ext"] if ext else d["acl_num"]), str(d["acl_other"]))


def apply_map(d):
    """{(IF名, "in"|"out"): 参照している ACL 名}。

    ★戻り通信の盤面(EST_KINDS)だけは**2枚**を持つ
      (顧客側の in= 往路用 / サーバ側の in= 復路用)。
    """
    if d["kind"] in EST_BUILD_KINDS:
        return {(d["if_dn"], "in"): est_refs(d)[0]}   # 復路はこれから書く
    if d["kind"] in EST_KINDS:
        fwd, ret = est_refs(d)
        return {(d["if_dn"], "in"): fwd, (d["if_up"], "in"): ret}
    a_if, a_dir, a_ref = apply_binding(d)
    return {} if a_if is None else {(a_if, a_dir): a_ref}


def acl_by_ref(d, ref):
    """参照名から entries を引く。未定義なら None(= 全許可・実測 §1)。"""
    for ents, _s, name in defined_acls(d):
        if name == ref:
            return ents
    return None


def path_stages(d, direction):
    """通過する検査点を (IF名, 方向) の順で返す。

    fwd = 顧客 → サーバ / rev = サーバ → 顧客。
    ★管理セグメントを絡めた経路は ifs_of() で明示する(fwd/rev には載らない)。
    """
    if direction == "fwd":
        return ifs_of(d["if_dn"], d["if_up"])
    return ifs_of(d["if_up"], d["if_dn"])


def ifs_of(in_if, out_if):
    """入口 IF と出口 IF から検査点の並びを作る。"""
    return [(in_if, "in"), (out_if, "out")]


def stage_pass(d, vec, direction, amap=None):
    """★二段評価。落ちたら (False, 落ちた検査点) を返す。

    direction は "fwd"/"rev" のほか、[(IF, 方向), ...] を直接渡してもよい。
    """
    amap = apply_map(d) if amap is None else amap
    stages = (path_stages(d, direction) if isinstance(direction, str)
              else direction)
    for point in stages:
        ref = amap.get(point)
        if ref is None:
            continue
        ents = acl_by_ref(d, ref)
        if ents is None or ents == []:
            continue                    # 未定義・空= 全許可(実測 §1・§2)
        if not acl_model.evaluate(ents, vec):
            return False, point
    return True, None


def rev_of(v):
    """往路のベクタから**復路**のベクタを作る(送信元と宛先・ポートを入れ替える)。

    ★戻りの TCP セグメントなので established を立てる。
    """
    return {"proto": v["proto"], "src": v["dst"], "dst": v["src"],
            "sport": v.get("dport"), "dport": v.get("sport"),
            "established": True, "icmp_type": v.get("icmp_type")}


def flow_ok(d, in_if, out_if, vec, amap=None):
    """★1本の通信が成立するか= **行きと戻りの両方**が通ること。

    ★戻りは入口と出口が入れ替わる= (出口 IF の in, 入口 IF の out)。
    """
    ok, _p = stage_pass(d, vec, ifs_of(in_if, out_if), amap)
    if not ok:
        return False
    ok, _p = stage_pass(d, rev_of(vec), ifs_of(out_if, in_if), amap)
    return ok


def session_ok(d, o3=None, amap=None, vec=None):
    """★通信が成立するか= **往路と復路の両方**が通ること。

    紙面の観測「サーバへの到達」は往復の到達性なので、
    復路だけが落ちる盤面(apply_direction / apply_iface_swap)もここで False になる
    (実測 §16-10= 要件どおりの ACL には暗黙の拒否があるため復路で落ちる)。
    """
    v = vec if vec is not None else _vec_at(d, o3)
    return flow_ok(d, d["if_dn"], d["if_up"], v, amap)


def interface_blocks(d):
    """`show running-config | section ^interface` の中身(実測 §16-1 の書式)。

    ★実機は `!` の区切りを入れず、ブロックを続けて出す。
    """
    amap = apply_map(d)
    rows = [(d["if_dn"], f"=== to {d['m']['DN']} ===",
             f"{d['oct1']}.{d['oct2']}.253.1"),
            (d["if_up"], f"=== to {d['m']['UP']} ===",
             f"{d['oct1']}.{d['oct2']}.254.1"),
            (d["if_mgmt"], "=== management ===",
             f"{d['oct1']}.{d['oct2']}.{d['mgmt_o3']}.1")]
    out = []
    for ifn, desc, ip in rows:
        out += [f"interface {ifn}", f" description {desc}",
                f" ip address {ip} 255.255.255.0"]
        for dr in ("in", "out"):
            if (ifn, dr) in amap:
                out.append(f" ip access-group {amap[(ifn, dr)]} {dr}")
    return out


# --------------------------------------------------------------------------
# apply 形(段B の構築系)= 「このアクセス リストをどこに・どの向きで適用するか」
# ★実測 §16-5 (iv)= 送信元ベースの ACL は「入口の in」でも「出口の out」でも
#   同じ結果になるので、**素のままでは正解が2つ**。要件で一意化する。
# ★実測 §16-11= 出口側に置くと自機の EIGRP hello が暗黙の拒否に食われて
#   ルーティングが壊れる。これは「入口に置くべき」理由の裏付け(解説で使う)。
# --------------------------------------------------------------------------
def mgmt_host(d):
    return f"{d['oct1']}.{d['oct2']}.{d['mgmt_o3']}.10"


def place_hosts(d):
    """apply 形で要件文に並べる送信元(世界で入れ替わる)。"""
    if d["world"] == "src_server":
        return [d["srv_host"], d["other_host"], d["dns"]]
    return [net(d, o) for o in d["target"]]


def place_acl(d):
    """apply 形の盤面に置く ACL(要件どおりに書けている・まだ適用されていない)。"""
    if d["world"] == "src_server":
        return [ac.entry("permit", None, src=h, sw="0.0.0.0", seq=10 + i * 10)
                for i, h in enumerate(place_hosts(d))]
    if d["world"] == "deny_to_mgmt":
        # ★拒否のリスト+ 末尾の permit any。標準なので**送信元しか見ない**。
        ents = [_std(d, "deny", o, 0, 10 + i * 10)
                for i, o in enumerate(d["target"])]
        ents.append(ac.entry("permit", None, seq=10 * (len(ents) + 1)))
        return ents
    return _right_acl(d)


def _mgmt_vec(d, o3):
    return {"proto": "tcp", "src": net(d, o3, 5), "dst": mgmt_host(d),
            "sport": 12345, "dport": 22, "established": False,
            "icmp_type": None}


def place_flows(d):
    """(表示文, 入口 IF, 出口 IF, ベクタ, 許可されるべきか) の列。"""
    out = []
    if d["world"] == "src_server":
        dst = net(d, d["target"][0], 5)
        allowed = place_hosts(d)
        probes = allowed + [f"{d['srv']}.{int(d['srv_host'].split('.')[-1]) + 1}"]
        for h in probes:
            out.append((f"送信元が `{h}` であるホストから、"
                        f"顧客の側の `{net(d, d['target'][0])}/24` 宛ての通信",
                        d["if_up"], d["if_dn"],
                        {"proto": "tcp", "src": h, "dst": dst,
                         "sport": 40000, "dport": 445,
                         "established": False, "icmp_type": None},
                        h in allowed))
        return out + _mgmt_side_flows(d)
    if d["world"] == "deny_to_mgmt":
        for o in d["target"]:  # deny_to_mgmt は元から管理セグメントを含む
            out.append((f"{net(d, o)}/24 から、管理セグメントの "
                        f"`{mgmt_host(d)}` 宛ての通信",
                        d["if_dn"], d["if_mgmt"], _mgmt_vec(d, o), False))
            out.append((f"{net(d, o)}/24 から、サーバである "
                        f"`{d['srv_host']}` 宛ての通信",
                        d["if_dn"], d["if_up"], _vec_at(d, o), True))
        # ★対象外の顧客網は管理セグメントにも到達できたままでなければならない
        out.append((f"{net(d, d['outsider'])}/24 から、管理セグメントの "
                    f"`{mgmt_host(d)}` 宛ての通信",
                    d["if_dn"], d["if_mgmt"], _mgmt_vec(d, d["outsider"]), True))
        return out
    for o in list(d["target"]) + [d["outsider"]]:
        out.append((f"送信元が {net(d, o)}/24 のネットワークにあるホストから、"
                    f"サーバである `{d['srv_host']}` 宛ての通信",
                    d["if_dn"], d["if_up"], _vec_at(d, o), o in d["target"]))
    out += _mgmt_side_flows(d)
    return out


def _mgmt_side_flows(d):
    """★管理セグメントを絡めた「影響を与えてはならない」通信2本。

    これが無いと、管理 IF に置く2肢が「対象の通信がそこを通らない」だけで
    自明に落ちてしまい、**出口側に置く解も意味的には成立**してしまう
    (実質2択・出題 20260811-012 の反省)。この2本を入れると、
    出口側に置く解は**関係のない通信を巻き添えにする**ので実質的に落ちる。
    """
    mh, t0 = mgmt_host(d), net(d, d["target"][0], 5)
    srv = d["srv_host"] if d["world"] == "src_customer" else place_hosts(d)[0]
    if d["world"] == "src_customer":
        return [
            (f"管理セグメントの `{mh}` から、"
             f"顧客の側の `{net(d, d['target'][0])}/24` 宛ての通信",
             d["if_mgmt"], d["if_dn"],
             {"proto": "tcp", "src": mh, "dst": t0, "sport": 40000,
              "dport": 22, "established": False, "icmp_type": None}, True),
            (f"サーバである `{srv}` から、管理セグメントの `{mh}` 宛ての通信",
             d["if_up"], d["if_mgmt"],
             {"proto": "tcp", "src": srv, "dst": mh, "sport": 40001,
              "dport": 514, "established": False, "icmp_type": None}, True),
        ]
    return [
        (f"管理セグメントの `{mh}` から、サーバである `{srv}` 宛ての通信",
         d["if_mgmt"], d["if_up"],
         {"proto": "tcp", "src": mh, "dst": srv, "sport": 40000,
          "dport": 22, "established": False, "icmp_type": None}, True),
        (f"顧客の側の `{net(d, d['target'][0])}/24` から、"
         f"管理セグメントの `{mh}` 宛ての通信",
         d["if_dn"], d["if_mgmt"],
         {"proto": "tcp", "src": t0, "dst": mh, "sport": 40001,
          "dport": 514, "established": False, "icmp_type": None}, True),
    ]


# --------------------------------------------------------------------------
# est_build(構築系)= 「復路用のアクセス リストをどう書くか」
# ★実測 §17= SYN は established に一致せず RST/ACK は一致する。
#   established を省くと「**送信元ポートを当該サービスに合わせた新規接続**」まで
#   通ってしまう(教科書どおりの危険)。それを (ii) の観測で機械的に落とす。
# --------------------------------------------------------------------------
def _est_stage(d, fwd, ret, vec, stages):
    for ifn, dr in stages:
        ents = (fwd if (ifn, dr) == (d["if_dn"], "in")
                else ret if (ifn, dr) == (d["if_up"], "in") else None)
        if ents is None:
            continue
        if not acl_model.evaluate(ents, vec):
            return False
    return True


def est_build_flows(d):
    """(表示文, ベクタ, 検査する段, 許可されるべきか)。"""
    dn, up = d["if_dn"], d["if_up"]
    v = _vec_at(d, d["target"][0])
    new_from_srv = dict(rev_of(v), established=False)
    other_port = dict(rev_of(v), sport=("eq", [d["other_port"]]))
    other_host = dict(rev_of(v), src=d["other_host"])
    return [
        (f"{net(d, d['target'][0])}/24 からサーバへの TCP セッション",
         v, [(dn, "in"), (up, "out")], True),
        ("★サーバの側から新たに開始される通信"
         "(送信元ポートは当該のサービスのもの・ACK を持たない)",
         new_from_srv, [(up, "in")], False),
        ("サーバの**別のポート**からの戻りの通信",
         other_port, [(up, "in")], False),
        ("**別のサーバ**からの戻りの通信",
         other_host, [(up, "in")], False),
    ]


def est_build_works(d, ret):
    fwd = _fwd_acl(d)
    dn, up = d["if_dn"], d["if_up"]
    for _txt, vec, stages, want in est_build_flows(d):
        if _est_stage(d, fwd, ret, vec, stages) != want:
            return False
        if want:      # 許可されるべき通信は**戻りも**通ること
            if not _est_stage(d, fwd, ret, rev_of(vec),
                              [(up, "in"), (dn, "out")]):
                return False
    return True


def est_build_candidates(d):
    """(key, 提示行, 復路用リストの entries)。"""
    num = est_refs(d)[1]
    srv, cst, wc = d["srv_host"], net(d, d["base"]), "0.0.7.255"
    pt = _port_txt(d["port"])

    def e(**kw):
        base = dict(proto="tcp", src=srv, sw="0.0.0.0",
                    sport=("eq", [d["port"]]), dst=cst, dw=wc,
                    established=True, seq=10)
        base.update(kw)
        return [ac.entry("permit", base.pop("proto"), **base)]

    return [
        ("est", [f"access-list {num} permit tcp host {srv} eq {pt} "
                 f"{cst} {wc} established"], e()),
        ("bare", [f"access-list {num} permit tcp host {srv} eq {pt} "
                  f"{cst} {wc}"], e(established=False)),
        ("swap", [f"access-list {num} permit tcp {cst} {wc} "
                  f"host {srv} eq {pt} established"],
         [ac.entry("permit", "tcp", src=cst, sw=wc, dst=srv, dw="0.0.0.0",
                   dport=("eq", [d["port"]]), established=True, seq=10)]),
        ("noport", [f"access-list {num} permit tcp host {srv} any established"],
         e(sport=None, dst="0.0.0.0", dw="255.255.255.255")),
        ("ipproto", [f"access-list {num} permit ip host {srv} {cst} {wc}"],
         [ac.entry("permit", "ip", src=srv, sw="0.0.0.0", dst=cst, dw=wc,
                   seq=10)]),
        ("anysrc", [f"access-list {num} permit tcp any eq {pt} "
                    f"{cst} {wc} established"],
         e(src="0.0.0.0", sw="255.255.255.255")),
    ]


EST_BUILD_WHY = {
    "bare": "established が無いため、サーバの側から**新たに開始される**通信"
            "(送信元ポートを当該のサービスに合わせたもの)まで許可される。",
    "swap": "送信元と宛先が逆であり、戻りのパケットには一致しない"
            "(セッションが確立できない)。",
    "noport": "送信元のポートが限定されていないため、"
              "当該のサーバの他のポートからの戻りまで許可される。",
    "ipproto": "プロトコルが ip であるため established を指定できず、"
               "サーバの側から新たに開始される通信まで許可される。",
    "anysrc": "送信元が any であるため、当該のサーバ以外からの戻りまで"
              "許可される。",
}


def apply_points(d):
    """候補となる適用点。3つの IF × in/out = 6通り。"""
    return [(ifn, dr) for ifn in (d["if_dn"], d["if_up"], d["if_mgmt"])
            for dr in ("in", "out")]


def _place_map(d, pt):
    ext = d.get("aclform") == "ext"
    return {pt: str(d["acl_ext"] if ext else d["acl_num"])}


def apply_works(d, pt):
    """その適用点に置いたとき、要件のフロー集合が**過不足なく**実現するか。"""
    amap = _place_map(d, pt)
    for _txt, in_if, out_if, vec, want in place_flows(d):
        if flow_ok(d, in_if, out_if, vec, amap) != want:
            return False
    return True


def verify_apply(d):
    """★一意性は**構造**から出す(文体上の制約に頼らない)。

    以前は「不要なトラフィックは可能なかぎり早い段階で破棄する」という制約で
    出口側の解を落としていたが、管理セグメントとの通信を要件に入れたことで
    **出口側は関係のない通信を巻き添えにする**= 意味的に成立しなくなった。
    誤答肢がすべて実質的な理由で落ちるので、消去法が効きにくくなる。
    """
    good = [pt for pt in apply_points(d) if apply_works(d, pt)]
    if len(good) != 1:
        raise ValueError(f"acl apply 一意性違反: works={good} "
                         f"(world={d['world']})")
    d["_apply_correct"] = good[0]
    return good[0]


def apply_why(d, pt):
    """その適用点が要件を満たさない理由を**盤面から**書く。"""
    amap = _place_map(d, pt)
    for txt, in_if, out_if, vec, want in place_flows(d):
        got = flow_ok(d, in_if, out_if, vec, amap)
        if got == want:
            continue
        if want:
            return f"この位置に適用すると、{txt}が破棄される。"
        return f"この位置では、{txt}を破棄することができない。"
    return "示されている要件を満たさない。"


def build_choices_apply(d, rnd):
    correct = verify_apply(d)
    c = []
    for pt in apply_points(d):
        txt = f"`interface {pt[0]}` において `ip access-group " \
              f"{_place_map(d, pt)[pt]} {pt[1]}`"
        c.append((txt, pt == correct,
                  "" if pt == correct else apply_why(d, pt)))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def ipif_acl_text(d, ifn):
    """`show ip interface <IF> | include access list` の実機書式(実測 §16-1)。

    ★IOS-XE 17.15 は Common access list の行が挟まる。
      `Inbound  access list` は空白2つ。
    """
    amap = apply_map(d)
    inb = amap.get((ifn, "in"), "not set")
    outb = amap.get((ifn, "out"), "not set")
    return ("  Outgoing Common access list is not set\n"
            f"  Outgoing access list is {outb}\n"
            "  Inbound  Common access list is not set\n"
            f"  Inbound  access list is {inb}")


def _render_entry(e, is_std):
    act = e["action"]
    src = _addr_txt(e["src"], e["src_wild"], std=is_std)
    if is_std:
        return f"{e['seq']} {act}{'   ' if act == 'deny' else ' '}{src}"
    dst = _addr_txt(e["dst"], e["dst_wild"], std=False)
    # ★送信元のポート演算子は**送信元アドレスの直後**に出る(実機の語順)。
    #   ここを描かないと port_swap の故障が提示物に現れず、
    #   「表示された ACL では通るはずなのに通らない」= 解答不能な問題になる
    #   (BL-106 の拡張 ACL 追加時に実際に作ってしまった)。
    if e.get("sport"):
        src = f"{src} {_port_op_txt(e['sport'])}"
    body = f"{e['proto']} {src} {dst}"
    if e.get("dport"):
        body += f" {_port_op_txt(e['dport'])}"
    # ★range の第2値・established・ICMP タイプの描画漏れは、
    #   提示と判定の不一致(あるいはパース不能)に直結する。
    if e.get("established"):
        body += " established"
    if e.get("icmp_type") is not None:
        body += f" {_icmp_txt(e['icmp_type'])}"
    return f"{e['seq']} {act}{'   ' if act == 'deny' else ' '}{body}"


def _addr_txt(v, w, std):
    ip = ".".join(str((v >> s) & 0xFF) for s in (24, 16, 8, 0))
    if w == 0xFFFFFFFF:
        return "any"
    if w == 0:
        return ip if std else f"host {ip}"
    wc = ".".join(str((w >> s) & 0xFF) for s in (24, 16, 8, 0))
    # ★標準 ACL は「A, wildcard bits W」形式(実測・acl_model のパーサもこの形)
    return f"{ip}, wildcard bits {wc}" if std else f"{ip} {wc}"


_PORT_NAME = {80: "www", 21: "ftp", 23: "telnet", 53: "domain", 25: "smtp",
              512: "exec", 513: "login", 514: "cmd"}
# 番号→名前(acl_model.ICMP_TYPES の逆引き)。実測で `echo-reply` 表示を確認済み。
_ICMP_NAME = {v: k for k, v in acl_model.ICMP_TYPES.items()}


def _port_txt(p):
    # 実測: 22 は数字のまま・80 は www と表示される
    return _PORT_NAME.get(p, str(p))


def _icmp_txt(t):
    return _ICMP_NAME.get(t, str(t))


def _port_op_txt(spec):
    """ポート演算子の描画。★range は**2値**を出す(第1値だけだと構文が壊れる)。"""
    op, v = spec
    if op == "range":
        return f"range {_port_txt(v[0])} {_port_txt(v[1])}"
    return f"{op} {_port_txt(v[0])}"


# --------------------------------------------------------------------------
# ロール写像層 — permit 集合 → 症状
# --------------------------------------------------------------------------
def _flow_ok(ents, v):
    """★フィルタが実質不在(未定義/空/未適用/別 IF)なら**全許可**。

    実測= §1(未定義)・§2(空)・§16-4(未適用・別 IF)。ここを `bool(ents) and ...` に
    すると、拡張形の追加観測だけ「落ちる」ことになり提示と判定が食い違う。
    """
    if ents is None or ents == []:
        return True
    return acl_model.evaluate(ents, v)


def flow_passes(d, src_o3):
    """filter ロール: 送信元 10.a.<o3>.x の通信が成立するか。

    ★未定義・空はいずれも**全許可**(実測 P1a/P12)。
    ★BL-109 段B 以降は**往路と復路の二段**で見る(session_ok)。
      適用点が正常な盤面では復路に検査点が無いので、従来と同じ結果になる。
    """
    return session_ok(d, src_o3)


def route_kept(d, adv_router, o3, plen=24):
    """routefilter ロール: その経路が受理されるか。

    ★実測(poc/acl §4)の意味論をそのまま写す:
      - 標準 ACL  … 照合対象は**広告されたネットワークアドレス**
      - 拡張 ACL  … **src=広告元ルータ / dst=広告されたネットワーク**
      - **プレフィックス長はどちらでも見られない**(plen は判定に使わない)
      - 名前付き拡張 ACL を指定した場合は**コマンドごと拒否**され filter は不在
      - 未定義・空は全許可
    """
    ents, is_std, _n = current_entries(d)
    if d["kind"] == "ext_named_rejected":
        return True                       # 適用されていない= 素通り
    if ents is None or ents == []:
        return True
    network = net(d, o3)
    if is_std:
        v = {"proto": "ip", "src": network, "dst": "0.0.0.0"}
    else:
        v = {"proto": "ip", "src": adv_router, "dst": network}
    return acl_model.evaluate(ents, v)


# --------------------------------------------------------------------------
# read 形 — 「通過するのはどれか」/「経路表に残るのはどれか」
# --------------------------------------------------------------------------
def read_items(d):
    """(表示文, 真か) の列。★**提示も判定もこの1関数から出す**(BL-103 ⑤の教訓)。

    「真」の意味はロールで違う(read_labels が語彙を与える)=
    転送される / 経路が残る / class-default に落ちる / 免除される / 変換される / 受理される。
    """
    r = d["role"]
    probes = list(d["target"]) + [d["fourth"], d["outsider"], d["faraway"]]
    if d["kind"] == "dense_list":
        ents, _s, _n = current_entries(d)
        return [(t, acl_model.evaluate(ents, v)) for t, v in dense_probes(d)]
    if r == "filter":
        out = [(f"送信元が {net(d, o)}/24 のネットワークにあるホストから、"
                f"{d['srv_host']} の TCP ポート {d['port']} 宛ての通信",
                flow_passes(d, o)) for o in probes]
        if d.get("aclform") == "ext":
            # ★拡張形の症状は「別のポート」「別の宛先」にも出る。
            #   これを観測に出さないと proto_ip_not_tcp / dst_any_too_wide の
            #   症状が見えない(BL-103 ③ と同型の事故になる)。
            t0 = d["target"][0]
            out.append(
                (f"送信元が {net(d, t0)}/24 のネットワークにあるホストから、"
                 f"{d['srv_host']} の TCP ポート {d['other_port']} 宛ての通信",
                 session_ok(d, vec=_vec_at(d, t0, dport=d["other_port"]))))
            out.append(
                (f"送信元が {net(d, t0)}/24 のネットワークにあるホストから、"
                 f"{d['other_host']} の TCP ポート {d['port']} 宛ての通信",
                 session_ok(d, vec=_vec_at(d, t0, dst=d["other_host"]))))
        return out
    if r == "routefilter":
        routes = [(d["nb_up"], o, 24) for o in d["target"]] + \
                 [(d["nb_dn"], d["target"][0], 28),
                  (d["nb_up"], d["outsider"], 24),
                  (d["nb_dn"], d["faraway"], 24)]
        return [(f"{adv} から広告された {net(d, o)}/{pl}",
                 route_kept(d, adv, o, pl)) for adv, o, pl in routes]
    if r == "copp":
        return [(f"{net(d, o, 5)} から {d['m']['DUT']} 宛ての ICMP エコー要求",
                 copp_to_default(d, o)) for o in probes]
    if r == "urpf":
        return [(f"送信元が {net(d, o, 5)} であるところの、"
                 f"Ethernet0/0 に着信するパケット", urpf_exempt(d, o))
                for o in probes]
    if r == "nat":
        return [(f"送信元が {net(d, o, 5)} であるホストから、"
                 "外部のネットワーク宛ての通信", nat_translated(d, o))
                for o in probes]
    return [(f"{net(d, o, 5)} から {d['m']['DUT']} への SSH による管理接続",
             vty_allowed(d, o)) for o in probes]


# --------------------------------------------------------------------------
# compare 形(P1d)— 2つのフローを見比べる
# ★狙い= 「同じアクセス・リストでも、どの行で確定するかはフローごとに変わる」。
#   1本ずつ判定するのではなく、**差が1フィールドしかない2本を並べて対比**させる。
# --------------------------------------------------------------------------
def _cmp_diff(a, b):
    return sum(1 for k in ("proto", "src", "dst", "sport", "dport",
                           "established", "icmp_type")
               if a.get(k) != b.get(k))


def _compare_probes(d):
    """compare 形の材料 [(表示, ベクタ, 結果), ...]。

    ★dense_list は**片方向**の first-match 読解。
    ★est_ret_narrow は**往復**で判定する(session_ok)= 往路は全部通るのに
      復路用リストの範囲が狭くて一部だけセッションが張れない、という比較になる。
    """
    if d["kind"] == "dense_list":
        ents, _s, _n = current_entries(d)
        if not ents:
            return None
        return [(t, v, acl_model.evaluate(ents, v)) for t, v in dense_probes(d)]
    if d["kind"] == "est_ret_narrow":
        out = []
        for o in list(d["target"]) + [d["fourth"], d["outsider"]]:
            v = _vec_at(d, o)
            out.append((f"送信元が {net(d, o)}/24 のネットワークにあるホストから、"
                        f"`{d['srv_host']}` の TCP ポート {d['port']} への "
                        f"TCP セッション", v, session_ok(d, vec=v)))
        return out
    return None


def compare_flows(d):
    """見比べさせるフローの並び [(表示, 通るか), ...] を返す。

    ★3本を優先する(8通りのうち真は1つ= 当てずっぽう 1/8)。
      3本が作れなければ2本(4通り)に落とす。
    条件:
      - **宛先が同じ**ものから採る(比較として成立させる)
      - 結果が**割れている**こと(全部同じだと見比べる意味が無い)
      - 互いの差が小さい順に選ぶ(1フィールド違いを優先)
    """
    ev = _compare_probes(d)
    if not ev:
        return None
    by_dst = {}
    for item in ev:
        by_dst.setdefault(item[1]["dst"], []).append(item)

    best = None
    for group in by_dst.values():
        if len(group) < 3:
            continue
        for a in range(len(group)):
            for b in range(a + 1, len(group)):
                for c in range(b + 1, len(group)):
                    tri = [group[a], group[b], group[c]]
                    outs = {x[2] for x in tri}
                    if len(outs) < 2:
                        continue          # 全部同じ= 見比べる意味が無い
                    cost = (_cmp_diff(tri[0][1], tri[1][1])
                            + _cmp_diff(tri[1][1], tri[2][1])
                            + _cmp_diff(tri[0][1], tri[2][1]))
                    if best is None or cost < best[0]:
                        best = (cost, tri)
    if best:
        # 同点の中から盤面で決定的に選ぶ
        cands = []
        for group in by_dst.values():
            if len(group) < 3:
                continue
            for a in range(len(group)):
                for b in range(a + 1, len(group)):
                    for c in range(b + 1, len(group)):
                        tri = [group[a], group[b], group[c]]
                        if len({x[2] for x in tri}) < 2:
                            continue
                        cost = (_cmp_diff(tri[0][1], tri[1][1])
                                + _cmp_diff(tri[1][1], tri[2][1])
                                + _cmp_diff(tri[0][1], tri[2][1]))
                        if cost == best[0]:
                            cands.append(tri)
        pick = zlib.crc32(f"{d['base']}:{d['port']}:{d['deny_port']}"
                          .encode()) % len(cands)
        return [(x[0], x[2]) for x in cands[pick]]

    # --- 2本に落とす ---
    pool = []
    for i2 in range(len(ev)):
        for j2 in range(i2 + 1, len(ev)):
            if ev[i2][1]["dst"] != ev[j2][1]["dst"]:
                continue
            if ev[i2][2] == ev[j2][2]:
                continue
            pool.append((_cmp_diff(ev[i2][1], ev[j2][1]), ev[i2], ev[j2]))
    if not pool:
        return None
    pool.sort(key=lambda x: x[0])
    top = [p for p in pool if p[0] == pool[0][0]]
    pick = zlib.crc32(f"{d['base']}:{d['port']}".encode()) % len(top)
    _c, x1, x2 = top[pick]
    return [(x1[0], x1[2]), (x2[0], x2[2])]


def compare_ok(d):
    return compare_flows(d) is not None


def _cmp_label(idx, n, d=None):
    """通るものの番号の集合 → 言い切りの文。

    ★往復で判定する盤面(est 系)は「転送」ではなく「セッションを確立できる」。
    """
    if d is not None and d.get("kind") in EST_KINDS + EST_BUILD_KINDS:
        yes, no = "セッションを確立できる", "セッションを確立できない"
    else:
        yes, no = "転送される", "破棄される"
    if not idx:
        return f"いずれも{no}。"
    if len(idx) == n:
        return f"いずれも{yes}。"
    nums = "、".join(str(i + 1) for i in sorted(idx))
    return f"{nums} のみが{yes}。"


def build_choices_compare(d, rnd):
    """★n 本のフローに対し 2^n 通りの言い切りを並べる(真はちょうど1つ)。"""
    fl = compare_flows(d)
    if fl is None:
        raise ValueError("acl compare: 見比べられる組が無い")
    n = len(fl)
    d["_compare"] = [t for t, _ok in fl]
    truth = frozenset(i for i, (_t, ok) in enumerate(fl) if ok)
    c = []
    for mask in range(1 << n):
        idx = frozenset(i for i in range(n) if mask & (1 << i))
        c.append((_cmp_label(idx, n, d), idx == truth,
                  "" if idx == truth
                  else "示されているアクセス・リストでは、そのようにはならない。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def read_polarity(d):
    """設問の向きを決める。少数派を正解にすると選択肢が作りやすい。

    戻り値: "pass"= 通る(残る)ものを選ぶ / "block"= 通らない(消える)ものを選ぶ。
    どちらの向きでも作れないときは None(read 形は使えない)。
    """
    items = read_items(d)
    t = sum(1 for _x, ok in items if ok)
    f = len(items) - t
    if t == 0 or f == 0:
        return None                      # 症状が観測に出ない= 設問が成立しない
    if t <= f:
        return "pass"
    return "block"


def build_choices_read(d, rnd, want=1):
    """want=1 は単一選択・2 は複数選択(「2つ選べ」)。

    正解は少数派の側から採る(多数派を正解にすると錯乱肢が足りない)。
    """
    pol = read_polarity(d)
    if pol is None:
        raise ValueError("acl read: 通る/通らないの一方しか無く設問が成立しない")
    items = read_items(d)
    hit = [t for t, ok in items if (ok if pol == "pass" else not ok)]
    miss = [t for t, ok in items if (ok if pol != "pass" else not ok)]
    if len(hit) < want or len(miss) < 2:
        raise ValueError(f"acl read: 選択肢が足りない(hit={len(hit)} "
                         f"miss={len(miss)} want={want})")
    rnd.shuffle(hit)
    rnd.shuffle(miss)
    why = ("示されているアクセス・リストでは、これは一致の対象とならない。"
           if pol == "pass" else
           "示されているアクセス・リストでは、これは許可される。")
    # ★複数選択では選択肢を厚くする(6つ)。2つ選べ×6択なら当てずっぽうは 1/15。
    n_miss = min(len(miss), max(6 - want, 2))
    picked = [(t, True, "") for t in hit[:want]]
    picked += [(t, False, why) for t in miss[:n_miss]]
    order = list(range(len(picked)))
    rnd.shuffle(order)
    d["_read_polarity"] = pol
    d["_read_want"] = want
    return [picked[i] for i in order]


# --------------------------------------------------------------------------
# counter 形(新)— 「この通信でカウンタが増えるのはどの行か」
# ★first-match の理解が直撃する。後続の一致する行は**増えない**のが要点。
# --------------------------------------------------------------------------
def first_match(entries, vector):
    """先頭一致した**エントリの位置**を返す(0 起点)。一致無しは None。"""
    for i, e in enumerate(entries or []):
        if acl_model.entry_matches(e, vector):
            return i
    return None


def _probe_vectors(d):
    """counter 形の候補となる観測(表示文, ベクタ)。ロールで意味が違う。"""
    out = []
    if d["kind"] == "dense_list":
        return dense_probes(d)
    if d["role"] == "filter":
        for o in list(d["target"]) + [d["fourth"], d["outsider"], d["faraway"]]:
            out.append((f"送信元が {net(d, o, 5)} のホストから、"
                        f"{d['srv_host']} の TCP ポート {d['port']} 宛ての1つのパケット",
                        {"proto": "tcp", "src": net(d, o, 5), "dst": d["srv_host"],
                         "sport": 12345, "dport": d["port"],
                         "established": False, "icmp_type": None}))
        return out
    ents, is_std, _n = current_entries(d)
    for adv, o in [(d["nb_up"], t) for t in d["target"]] + \
                  [(d["nb_dn"], d["target"][0]), (d["nb_up"], d["outsider"])]:
        if is_std:
            v = {"proto": "ip", "src": net(d, o), "dst": "0.0.0.0"}
        else:
            v = {"proto": "ip", "src": adv, "dst": net(d, o)}
        out.append((f"{adv} から広告された {net(d, o)} のルート1本", v))
    return out


def counter_probe(d):
    """★**2つ以上の行に一致する**観測から1つを選ぶ。

    無ければ counter 形は作らない(1行しか一致しないなら「先頭一致」を問う意味が
    無く、ただの読み取りになる)。
    ★候補が複数あるときは**盤面から決定的に抽選**する。先頭固定にすると
      正解が毎回「deny ip の行」になり、『deny ip を探せばよい』という
      メタ解法が成立してしまう(出題で判明・2026-08-11)。
    """
    ents, _is_std, _n = current_entries(d)
    if not ents or len(ents) < 2:
        return None
    cands = []
    for text, v in _probe_vectors(d):
        hits = [i for i, e in enumerate(ents) if acl_model.entry_matches(e, v)]
        if len(hits) >= 2:
            cands.append({"text": text, "vector": v, "hits": hits,
                          "first": hits[0]})
    if not cands:
        return None
    pick = zlib.crc32(f"{d['base']}:{d['oct2']}:{d['deny_port']}"
                      .encode()) % len(cands)
    return cands[pick]


def build_choices_counter(d, rnd):
    p = counter_probe(d)
    if p is None:
        raise ValueError("acl counter: 複数行に一致する観測が無い")
    ents, is_std, name = current_entries(d)
    d["_counter_probe"] = p
    c = []
    # ★盤面に ACL が複数あるとき(apply_wrong_acl)は**両方の行**を選択肢に並べる。
    #   こうしないと「効いていないほうの ACL」を読む必要が消え、
    #   `ip access-group` 行を見なくても答えられてしまう(BL-109 段A の反省)。
    lists = defined_acls(d)
    multi = len(lists) > 1

    def label(e, std, nm):
        head = f"アクセス リスト {nm} の " if multi else ""
        return f"{head}`{_render_entry(e, std)}` の行"

    for l_ents, l_std, l_name in lists:
        eff = (l_name == name)
        for i, e in enumerate(l_ents):
            txt = label(e, l_std, l_name)
            if eff and i == p["first"]:
                c.append((txt, True, ""))
            elif not eff:
                # ★効いていない ACL の行= どれだけ一致していてもカウンタは進まない。
                c.append((txt, False,
                          "このアクセス リストは、いずれのインターフェイスにも"
                          "適用されていない。"))
            elif i in p["hits"]:
                # ★最大の罠= 「この行にも一致するはず」。先頭一致で既に確定している。
                c.append((txt, False,
                          "先行する行で一致が確定しているため、"
                          "この行は評価されない。"))
            else:
                c.append((txt, False, "この行は当該のパケットに一致しない。"))
    c.append(("いずれの行のカウンタも増加しない(暗黙の拒否によって処理される)",
              False, "暗黙の拒否にはカウンタが存在しないが、"
                     "本件は明示された行に一致している。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# patch 形(新)— 「1行だけ挿入する。★挿入位置が本題」
# --------------------------------------------------------------------------
PATCH_BASE_KINDS = ("wc_wide", "order_shadow")


def patch_targets(d):
    """patch の要件= この観測集合だけで判定する(要件文と判定を字面で一致させる)。

    「<outsider> は拒否・<target...> は影響を受けない」。
    """
    want = [(o, True) for o in d["target"]] + [(d["outsider"], False)]
    return want


def _patch_eval(entries, d):
    for o, expect in patch_targets(d):
        v = {"proto": "tcp", "src": net(d, o, 5), "dst": d["srv_host"],
             "sport": 12345, "dport": d["port"], "established": False,
             "icmp_type": None}
        if acl_model.evaluate(entries, v) != expect:
            return False
    return True


def patch_candidates(d):
    """(key, 提示する CLI 行, 適用後の entries)。★同じ1行を**どこに入れるか**を競わせる。"""
    ents, _is_std, name = current_entries(d)
    deny = _std(d, "deny", d["outsider"], 0, 0)
    line = f"deny {net(d, d['outsider'])} 0.0.0.255"
    out = []
    for seq in (5, 15, 25):
        new = [dict(e) for e in ents]
        ins = dict(deny, seq=seq)
        new.append(ins)
        new.sort(key=lambda e: e["seq"])
        out.append((f"ins{seq}",
                    [f"ip access-list standard {name}", f" {seq} {line}"], new))
    # ★番号付きのグローバル形式は**必ず末尾に付く**(実測 poc/acl §6)
    tail = [dict(e) for e in ents] + [dict(deny, seq=max(e["seq"] for e in ents) + 10)]
    out.append(("append",
                [f"access-list {name} {line}"], tail))
    return out


def patch_ok(d):
    if d["role"] != "filter" or d["kind"] not in PATCH_BASE_KINDS:
        return False
    ents, _is_std, _n = current_entries(d)
    if not ents:
        return False
    if _patch_eval(ents, d):
        return False                    # 既に要件を満たしている= 直す必要が無い
    good = [k for k, _l, e in patch_candidates(d) if _patch_eval(e, d)]
    return len(good) == 1


def build_choices_patch(d, rnd):
    good = [k for k, _l, e in patch_candidates(d) if _patch_eval(e, d)]
    if len(good) != 1:
        raise ValueError(f"acl patch 一意性違反: good={good}")
    correct = good[0]
    why = {
        "ins5": "", "ins15": "先行する許可の行で一致が確定するため、効果を持たない。",
        "ins25": "先行する許可の行で一致が確定するため、効果を持たない。",
        "append": "この形式では、エントリはリストの末尾に追加される。"
                  "先行する許可の行で一致が確定するため、効果を持たない。",
    }
    c = [("\n".join(lines), k == correct, "" if k == correct else why[k], lines)
         for k, lines, _e in patch_candidates(d)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# fix 形(新)— routefilter の是正手段。★実測の意味論が正解を決める
# --------------------------------------------------------------------------
# ★実測 C1(2026-08-11)= **参照経路で拡張 ACL の意味論が切り替わる**。
#   直接指定 `distribute-list <番号> in` … src=広告元 / dst=網（長さは見ない）
#   route-map 経由 `distribute-list route-map <名前> in` … src=網 / dst=サブネットマスク
#   → **長さで絞る手段は prefix-list だけではない**（route-map 経由でも絞れる）。
#   そこで「どちらを禁じるか」を要件世界にして正解を反転させる。
FIX_WORLDS = ("prefixlen_no_rm", "prefixlen_via_rm", "by_neighbor")


def fix_ok(d):
    return d["role"] == "routefilter" and d["world"] in FIX_WORLDS


def fix_routes(d):
    """(広告元, 第3オクテット, 長さ, 残すべきか)。★世界ごとに盤面が変わる。"""
    if d["world"] in ("prefixlen_no_rm", "prefixlen_via_rm"):
        # ★同じ隣接から**同じネットワークアドレスで長さ違い**が届く。
        #   直接指定の ACL は長さを見ないので分離できない(実測 F4)。
        return [(d["nb_up"], d["target"][0], 24, True),
                (d["nb_up"], d["target"][0], 28, False),
                (d["nb_up"], d["target"][1], 24, True)]
    # by_neighbor: 広告元で切り分ける。ACL の src が意味を持つのは拡張だけ(実測 E3)
    return [(d["nb_up"], d["target"][0], 24, True),
            (d["nb_up"], d["target"][1], 24, True),
            (d["nb_dn"], d["target"][2], 24, False),
            (d["nb_dn"], d["outsider"], 24, False)]


def fix_candidates(d):
    """(key, 説明, CLI, 判定関数)。判定は**実測の意味論**をそのまま関数化する。"""
    n, x, nm = d["acl_num"], d["acl_ext"], d["acl_name"]
    t0, t1 = net(d, d["target"][0]), net(d, d["target"][1])
    nb = d["nb_dn"]

    def std_deny_t0(adv, o, pl):
        # 標準 ACL: 照合はネットワークアドレスのみ(長さも広告元も見ない)
        return not (net(d, o) == t0)

    def ext_named(adv, o, pl):
        # ★この順序(定義→参照)ではコマンドごと拒否され、フィルタは不在(実測 §4-1)。
        #   ただし**参照→定義の順なら受理される**(実測 C3)= 順序依存。
        return True

    def ext_src_net(adv, o, pl):
        return False         # src に網を書くと何にも一致しない→暗黙拒否で全滅

    def ext_src_nb(adv, o, pl):
        return adv != nb     # src=広告元ルータ。当該ネイバー発だけ落ちる

    def plist(adv, o, pl):
        # prefix-list は**長さで区別できる**
        return not (net(d, o) == t0 and pl == 28)

    def rm_mask(adv, o, pl):
        # ★route-map 経由の拡張 ACL= src=網 / dst=サブネットマスク(実測 C1b/C1d)。
        #   `permit ip <網> <wc> host 255.255.255.0` で **/24 だけ**通せる。
        return pl == 24

    return [
        ("std_deny",
         f"標準のアクセス・リスト {n} において `{t0}` を拒否し、"
         "distribute-list から参照する",
         [f"access-list {n} deny {t0} 0.0.0.255",
          f"access-list {n} permit any",
          "router eigrp 100", f" distribute-list {n} in"], std_deny_t0),
        ("ext_named",
         f"名前付きの拡張のアクセス・リスト {nm} を作成し、distribute-list から参照する",
         [f"ip access-list extended {nm}",
          f" permit ip host {d['nb_up']} any",
          "router eigrp 100", f" distribute-list {nm} in"], ext_named),
        ("ext_src_net",
         f"拡張のアクセス・リスト {x} において、送信元として対象のネットワークを"
         "指定し、distribute-list から参照する",
         [f"access-list {x} permit ip host {t1} any",
          "router eigrp 100", f" distribute-list {x} in"], ext_src_net),
        ("ext_src_nb",
         f"拡張のアクセス・リスト {x} において、送信元として `{d['nb_up']}` を"
         "指定し、distribute-list から参照する",
         [f"access-list {x} permit ip host {d['nb_up']} any",
          "router eigrp 100", f" distribute-list {x} in"], ext_src_nb),
        ("plist",
         f"プレフィックス・リスト PL-IN において長さを指定し、"
         "distribute-list prefix から参照する",
         [f"ip prefix-list PL-IN seq 5 deny {t0}/28",
          "ip prefix-list PL-IN seq 10 permit 0.0.0.0/0 le 32",
          "router eigrp 100", " distribute-list prefix PL-IN in"], plist),
        ("rm_mask",
         f"拡張のアクセス・リスト {x} において、送信元にネットワークを、"
         "宛先にサブネット・マスクを指定し、ルート・マップを経由して参照する",
         [f"access-list {x} permit ip any host 255.255.255.0",
          "route-map RM-IN permit 10", f" match ip address {x}",
          "router eigrp 100", " distribute-list route-map RM-IN in"], rm_mask),
    ]


def _fix_works(d, fn):
    return all(fn(adv, o, pl) == keep for adv, o, pl, keep in fix_routes(d))


def _fix_complies(d, key):
    """要件世界の**手段の制約**。works(意味)とは分けて判定する。"""
    w = d["world"]
    if w == "prefixlen_no_rm":
        return key != "rm_mask"        # ルート・マップの使用は認められていない
    if w == "prefixlen_via_rm":
        return key != "plist"          # プレフィックス・リストの使用は認められていない
    return True                        # by_neighbor は手段が1つしか無い


def verify_fix(d):
    works = [k for k, _t, _c, fn in fix_candidates(d) if _fix_works(d, fn)]
    ok = [k for k in works if _fix_complies(d, k)]
    if len(ok) != 1:
        raise ValueError(f"acl fix 一意性違反: world={d['world']} "
                         f"works={works} ok={ok}")
    d["_fix_works"] = works
    return ok[0]


WHY_FIX = {
    "std_deny": "標準のアクセス・リストは、ネットワークのアドレスのみを照合するため、"
                "プレフィックスの長さも、広告元も、区別することができない。",
    "ext_named": "この順序(アクセス・リストを定義してから参照する)では、"
                 "名前付きの拡張のアクセス・リストは distribute-list に受理されず、"
                 "フィルタが適用されない。",
    "ext_src_net": "拡張のアクセス・リストの送信元は、広告元のルータであって、"
                   "ネットワークではないため、いずれのルートにも一致しない。",
    "ext_src_nb": "広告元のルータによる切り分けは行われるが、"
                  "プレフィックスの長さは区別されない。",
    "plist": "プレフィックスの長さによる区別は行われるが、"
             "広告元のルータによる切り分けは行われない。",
    "rm_mask": "ルート・マップを経由した場合、送信元はネットワーク、"
               "宛先はサブネット・マスクとして照合されるため、"
               "広告元のルータによる切り分けは行われない。",
}


def build_choices_fix(d, rnd):
    correct = verify_fix(d)
    reason_by_world = {
        "prefixlen_no_rm": "ルート・マップの使用は、認められていない。",
        "prefixlen_via_rm": "プレフィックス・リストの使用は、認められていない。",
    }
    c = []
    for k, txt, cli, _fn in fix_candidates(d):
        if k == correct:
            why = ""
        elif k in d.get("_fix_works", []):
            # ★「結果は出せるが手段が要件に反する」候補は、意味ではなく手段で落とす
            why = reason_by_world.get(d["world"], WHY_FIX[k])
        else:
            why = WHY_FIX[k]
        c.append((txt, k == correct, why, cli))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# evidence 形(P1c)— 「次に取得すべき出力はどれか」
# ★成立の根拠= 実測で確定した**区別不能クラス**。
#   undef_ref / empty_acl / ext_named_rejected はいずれも「フィルタが実質不在=全部素通り」
#   に化けるので、症状(経路表)だけでは割れない。どの出力なら何通りに割れるかを機械採点する。
# --------------------------------------------------------------------------
EVIDENCE_HYPS = ("undef_ref", "empty_acl", "ext_named_rejected")
# ★filter ロール版(BL-109 段A)。実測 §16-4 で「フィルタが実質不在」の類型が
#   3種→5種に増えた。うち filter ロールに載るのはこの4種。
#   ★4つ並べると `show ip access-lists` と `show run | section ^interface` が
#     どちらも3分割になって**最良の出力が一意でなくなる**ので、盤面から
#     決定的に1つ落として3仮説にする(下の filter_evidence_hyps)。
FILTER_EVIDENCE_HYPS = ("filter_undef_ref", "filter_empty_acl",
                        "apply_missing", "apply_other_iface")
# ★全断系(症状が「どのセッションも成立しない」で同じ)の仮説群。
#   ★4つ並べると `show ip access-lists` と `show run | section ^interface` が
#     どちらも3分割になって最良が一意でなくなる。
#     **est の2種＋apply の1種**という組にすると `show ip access-lists` だけが
#     3分割になり一意に決まる(下の blackout_evidence_hyps)。
BLACKOUT_EVIDENCE_HYPS = ("apply_direction", "apply_iface_swap",
                          "est_missing", "est_wrong_side")


def blackout_evidence_hyps(d):
    applies = ["apply_direction", "apply_iface_swap"]
    if d["kind"] in applies:
        pick = d["kind"]
    else:
        pick = applies[zlib.crc32(f"bo:{d['base']}:{d['oct2']}".encode()) % 2]
    keep = {pick, "est_missing", "est_wrong_side"}
    return tuple(h for h in BLACKOUT_EVIDENCE_HYPS if h in keep)


def filter_evidence_hyps(d):
    others = [h for h in FILTER_EVIDENCE_HYPS if h != d["kind"]]
    drop = zlib.crc32(f"ev:{d['base']}:{d['oct2']}:{d['acl_num']}"
                      .encode()) % len(others)
    keep = {d["kind"]} | {h for i, h in enumerate(others) if i != drop}
    return tuple(h for h in FILTER_EVIDENCE_HYPS if h in keep)


def evidence_hyps(d):
    if d["kind"] in BLACKOUT_EVIDENCE_HYPS:
        return blackout_evidence_hyps(d)
    if d["role"] == "filter":
        return filter_evidence_hyps(d)
    return EVIDENCE_HYPS


def _hyp_board(d, kind):
    """同じ盤面で kind だけ差し替えた仮想の d(観測の分割数を数えるため)。"""
    e = dict(d)
    e["kind"] = kind
    e["role"] = role_of(kind)
    return e


def _filter_evidence_observations(d):
    """filter ロールの evidence(実測 §16-4 の割れ方をそのまま写す)。"""
    hyps = evidence_hyps(d)
    m, ifn = d["m"], d["if_dn"]
    obs = []

    def add(text, fn):
        obs.append((text, {k: fn(_hyp_board(d, k)) for k in hyps}))

    # 3分割になり得る: 未定義=何も出ない / 空=ヘッダのみ / 定義済み=エントリあり
    add(f"{m['DUT']} における `show ip access-lists`", show_acl_text)
    # 3分割になり得る: 顧客側に適用 / どこにも無い / 管理側に適用
    add(f"{m['DUT']} における "
        "`show running-config | section ^interface`",
        lambda e: "|".join(l for l in interface_blocks(e)
                           if "access-group" in l) or "(none)")
    # 2分割: 当該 IF に付いているか否か(未適用と別 IF 適用は**同じに見える**)
    add(f"{m['DUT']} における "
        f"`show ip interface {ifn} | include access list`",
        lambda e: ipif_acl_text(e, ifn))
    # 1分割(無意味): どの仮説でも全部素通りなので症状も経路表も同じ
    add(f"{m['DUT']} における `show ip route`", lambda e: "same")
    add(f"{m['DUT']} における `show interfaces {ifn} | include packets`",
        lambda e: "same")
    return obs


def evidence_observations(d):
    """(表示文, 仮説→見え方) の列。見え方の異なり数が「何通りに割れるか」。"""
    if d["role"] == "filter":
        return _filter_evidence_observations(d)
    obs = []

    def add(text, fn):
        obs.append((text, {k: fn(_hyp_board(d, k)) for k in EVIDENCE_HYPS}))

    # ★3分割: 未定義=何も出ない / 空=ヘッダのみ / 名前付き拡張=ヘッダ+エントリ
    add(f"{d['m']['DUT']} における `show ip access-lists`",
        lambda e: show_acl_text(e))
    # 2分割(実測 P15)= 名前付き拡張は**コマンドごと拒否**され構成に残らない。
    #   未定義・空はどちらも `distribute-list <NAME> in` が残る。
    add(f"{d['m']['DUT']} における "
        "`show running-config | include distribute-list`",
        lambda e: "" if e["kind"] == "ext_named_rejected"
        else f"distribute-list {current_entries(e)[2]} in")
    # 2分割(実測 P15)= `Incoming update filter list ... is <NAME>` / `not set`
    add(f"{d['m']['DUT']} における `show ip protocols`",
        lambda e: "not set" if e["kind"] == "ext_named_rejected"
        else f"is {current_entries(e)[2]}")
    # 1分割(無意味): 症状はどの仮説でも同じ
    add(f"{d['m']['DUT']} における `show ip route eigrp`",
        lambda e: "all-routes")
    add(f"{d['m']['DUT']} における `show ip interface Ethernet0/0`",
        lambda e: "no-acl")
    return obs


def evidence_ok(d):
    if d["role"] == "filter":
        if d["kind"] not in FILTER_EVIDENCE_HYPS + BLACKOUT_EVIDENCE_HYPS:
            return False
    elif d["role"] != "routefilter" or d["kind"] not in EVIDENCE_HYPS:
        return False
    splits = [len(set(v.values())) for _t, v in evidence_observations(d)]
    top = max(splits)
    return top >= 3 and splits.count(top) == 1     # 最良が一意であること


def build_choices_evidence(d, rnd):
    obs = evidence_observations(d)
    splits = [len(set(v.values())) for _t, v in obs]
    top = max(splits)
    if splits.count(top) != 1:
        raise ValueError("acl evidence: 最良の出力が一意でない")
    c = []
    for (text, _v), n in zip(obs, splits):
        if n == top:
            c.append((text, True, ""))
        elif n >= 2:
            # ★「惜しい」肢= 2通りには割れるが3通りには割れない。消去法を潰す
            c.append((text, False,
                      "この出力では、候補を2つまでしか絞り込むことができない。"))
        else:
            c.append((text, False,
                      "この出力は、いずれの候補においても同じ内容になる。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# logread 形(P1c)— ログから何が起きたかを読む
# ★核心(実測 §9)= **`log` を書いた行でしか記録されない**。カウンタは進むのに
#   ログに無い= 「記録の無い行で落ちた」という消去推論が成立する。
# --------------------------------------------------------------------------
def logread_board(d):
    """ログ用の盤面。`log` 付きの deny と `log` 無しの deny を必ず同居させる。"""
    b = d["base"]
    name = d["acl_name"]
    ents = [
        ac.entry("deny", "tcp", src=net(d, d["outsider"]), sw="0.0.0.255",
                 dst=d["srv_host"], dw="0.0.0.0",
                 dport=("eq", [d["port"]]), seq=10),          # log あり
        ac.entry("deny", "tcp", src=net(d, d["fourth"]), sw="0.0.0.255",
                 dst=d["srv_host"], dw="0.0.0.0",
                 dport=("eq", [d["port"]]), seq=20),          # log なし
        ac.entry("permit", "ip", seq=30),
    ]
    logged = {10}
    return name, ents, logged


def logread_lines(d):
    """実機書式のログ行(実測 §9 に忠実)。log 付きの行に当たった分だけ出す。"""
    name, ents, logged = logread_board(d)
    out = []
    for o in (d["outsider"], d["fourth"], d["target"][0]):
        v = {"proto": "tcp", "src": net(d, o, 7), "dst": d["srv_host"],
             "sport": 19314 + o, "dport": d["port"], "established": False,
             "icmp_type": None}
        i = first_match(ents, v)
        if i is None:
            continue
        e = ents[i]
        if e["seq"] in logged and e["action"] == "deny":
            out.append(f"%SEC-6-IPACCESSLOGP: list {name} denied tcp "
                       f"{net(d, o, 7)}({v['sport']}) -> "
                       f"{d['srv_host']}({d['port']}), 1 packet")
    return out


def logread_facts(d):
    """(文, 真偽)。★すべてログと ACL から機械導出する。"""
    name, ents, logged = logread_board(d)
    lines = logread_lines(d)
    f = []

    def hit(o):
        v = {"proto": "tcp", "src": net(d, o, 7), "dst": d["srv_host"],
             "sport": 19314 + o, "dport": d["port"], "established": False,
             "icmp_type": None}
        return first_match(ents, v)

    i_out, i_fourth, i_ok = hit(d["outsider"]), hit(d["fourth"]), hit(d["target"][0])
    f.append((f"`{net(d, d['outsider'], 7)}` からの通信は、"
              "アクセス・リストによって拒否された。",
              ents[i_out]["action"] == "deny"))
    f.append((f"`{net(d, d['fourth'], 7)}` からの通信は、記録には現れていないが、"
              "アクセス・リストによって拒否された。",
              ents[i_fourth]["action"] == "deny"
              and ents[i_fourth]["seq"] not in logged))
    f.append((f"`{net(d, d['fourth'], 7)}` からの通信は、許可された。",
              ents[i_fourth]["action"] == "permit"))
    f.append((f"`{net(d, d['target'][0], 7)}` からの通信は、拒否された。",
              ents[i_ok]["action"] == "deny"))
    f.append(("記録に現れていない通信は、いずれも許可されたものである。",
              all(ents[hit(o)]["seq"] in logged
                  for o in (d["outsider"], d["fourth"])
                  if ents[hit(o)]["action"] == "deny")))
    f.append((f"拒否のエントリのうち、`log` のキーワードを伴うものは1つだけである。",
              len(logged) == 1))
    f.append((f"記録されている通信の宛先ポートは {d['port']} である。",
              bool(lines)))
    return f


def logread_ok(d):
    return d["role"] == "filter"


def build_choices_logread(d, rnd, want=2):
    facts = logread_facts(d)
    trues = [t for t, ok in facts if ok]
    falses = [t for t, ok in facts if not ok]
    if len(trues) < want or len(falses) < 2:
        raise ValueError(f"acl logread: 選択肢が足りない "
                         f"(true={len(trues)} false={len(falses)})")
    rnd.shuffle(trues)
    rnd.shuffle(falses)
    c = [(t, True, "") for t in trues[:want]]
    c += [(t, False, "示されている記録および構成からは、そのようには読み取れない。")
          for t in falses[:max(5 - want, 2)]]
    order = list(range(len(c)))
    rnd.shuffle(order)
    d["_logread_want"] = want
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# cause 形
# --------------------------------------------------------------------------
CLAIMS = {
    "wc_narrow": "ワイルドカードのビットが不足しており、"
                 "対象としているネットワークの一部が一致の対象から外れている",
    "wc_wide": "ワイルドカードのビットが過剰であり、"
               "対象としていないネットワークまでが一致の対象に含まれている",
    "wc_bits": "ワイルドカードのビットが連続しておらず、"
               "一致の対象が飛び飛びになっている",
    "mask_as_wildcard": "ワイルドカードとして記述されている値が、"
                        "サブネット・マスクの形式になっている",
    "order_shadow": "先行するエントリが広い範囲を許可しており、"
                    "後続のエントリが評価されない",
    "port_swap": "ポートの演算子が、宛先の側ではなく送信元の側に記述されている",
    "proto_ip_not_tcp": "プロトコルとして ip が指定されているため、"
                        "ポートによる制限が行われていない",
    "dst_any_too_wide": "宛先として any が指定されているため、"
                        "当該のサーバ以外への通信までが許可されている",
    "apply_wrong_acl": "インターフェイスに適用されているアクセス・リストが、"
                       "意図されているものとは別のアクセス・リストである",
    "apply_missing": "アクセス・リストが、いずれのインターフェイスにも"
                     "適用されていない",
    "apply_other_iface": "アクセス・リストが、管理のためのインターフェイスに"
                         "適用されている",
    "apply_direction": "インターフェイスに対して、アクセス・リストが in ではなく "
                       "out の方向に適用されている",
    "est_missing": "戻りの通信を許可するアクセス・リストに、"
                   "established のキーワードを伴うエントリが存在しない",
    "est_wrong_side": "established のキーワードが、戻りの側ではなく、"
                      "通信を開始する側のアクセス・リストに記述されている",
    "est_ret_narrow": "戻りの通信を許可するアクセス・リストの範囲が、"
                      "対象としているネットワークの一部しか含んでいない",
    "apply_iface_swap": "アクセス・リストが、顧客の側ではなくサーバの側の"
                        "インターフェイスに、着信の方向で適用されている",
    "filter_undef_ref": "インターフェイスから参照されているアクセス・リストが、"
                        "定義されていない",
    "filter_empty_acl": "インターフェイスに適用されているアクセス・リストに、"
                        "エントリが1つも存在しない",
    "std_len_blind": "標準のアクセス・リストが用いられており、"
                     "プレフィックスの長さが区別されていない",
    "ext_named_rejected": "名前付きの拡張のアクセス・リストが指定されており、"
                          "フィルタ自体が適用されていない",
    "ext_src_is_network": "拡張のアクセス・リストの送信元に、"
                          "ネットワークのアドレスが記述されている",
    "undef_ref": "参照されているアクセス・リストが定義されていない",
    "empty_acl": "アクセス・リストにエントリが1つも存在しない",
    "copp_deny_to_default": "アクセス・リストの拒否のエントリに一致するトラフィックが、"
                            "定義されたクラスには分類されず、class-default において"
                            "処理されている",
    "urpf_undef_exempt": "検証の例外として参照されているアクセス・リストが定義されておらず、"
                         "すべての送信元が検証から免除されている",
    "nat_deny_scope": "変換の対象を選択するアクセス・リストにおいて、"
                      "拒否の範囲が広すぎる",
    "vty_wc_wrong": "接続元を制限するアクセス・リストの範囲が、"
                    "管理のための端末を含んでいない",
}
REFUTES = {
    "wc_narrow": "示されているワイルドカードは、対象としているネットワークを"
                 "すべて含んでいる。",
    "wc_wide": "示されているワイルドカードは、対象としている範囲を超えていない。",
    "wc_bits": "示されているワイルドカードのビットは連続している。",
    "mask_as_wildcard": "示されている値はワイルドカードの形式である。",
    "order_shadow": "示されているエントリの順序では、後続のエントリが評価される。",
    "port_swap": "ポートの演算子は、宛先の側に記述されている。",
    "proto_ip_not_tcp": "示されているエントリのプロトコルは tcp である。",
    "dst_any_too_wide": "示されているエントリの宛先は、当該のサーバに限定されている。",
    "apply_wrong_acl": "示されている構成において、適用されているアクセス・リストは"
                       "1つだけである。",
    "apply_missing": "示されている構成に、アクセス・リストを適用する"
                     "ステートメントが存在する。",
    "apply_other_iface": "アクセス・リストは、管理のためのインターフェイスには"
                         "適用されていない。",
    "apply_direction": "示されている構成では、適用の方向は in である。",
    "est_missing": "戻りの通信のアクセス・リストには、"
                   "established を伴うエントリが存在する。",
    "est_wrong_side": "通信を開始する側のアクセス・リストには、"
                      "established は記述されていない。",
    "est_ret_narrow": "戻りの通信のアクセス・リストは、"
                      "対象としているネットワークをすべて含んでいる。",
    "apply_iface_swap": "アクセス・リストは、顧客の側のインターフェイスに"
                        "適用されている。",
    "filter_undef_ref": "参照されているアクセス・リストは定義されている。",
    "filter_empty_acl": "アクセス・リストにはエントリが存在する。",
    "std_len_blind": "用いられているのは標準のアクセス・リストではない。",
    "ext_named_rejected": "指定されているアクセス・リストは番号付きである。",
    "ext_src_is_network": "送信元にはネットワークのアドレスは記述されていない。",
    "undef_ref": "参照されているアクセス・リストは定義されている。",
    "empty_acl": "アクセス・リストにはエントリが存在する。",
    "copp_deny_to_default": "示されている構成に、サービス・ポリシーは存在しない。",
    "urpf_undef_exempt": "示されている構成に、送信元の検証のステートメントは存在しない。",
    "nat_deny_scope": "示されている構成に、アドレスの変換のステートメントは存在しない。",
    "vty_wc_wrong": "示されている構成に、接続元を制限するステートメントは存在しない。",
}
# ★ロール固有の「もっともらしい誤解」= 単独 kind のロールで錯乱肢に使う。
#   いずれも実測(poc/acl)で**偽**と確定している主張。
MISCONCEPTION = {
    "copp": [
        ("アクセス・リストの拒否のエントリに一致するトラフィックは、"
         "ポリシーの対象から外れ、そのまま制限なく転送される",
         "拒否のエントリに一致したトラフィックは、当該のクラスに分類されないだけであり、"
         "class-default において処理される。"),
        ("サービス・ポリシーが、出力の方向に適用されている",
         "コントロール・プレーンに対するポリシーは、入力の方向で適用されている。"),
    ],
    "urpf": [
        ("検証のモードが、着信インターフェイスの一致を要求しない設定になっている",
         "示されている構成では、着信インターフェイスの一致が要求されている。"),
        ("例外として参照されているアクセス・リストが、空である",
         "参照されているアクセス・リストは、定義そのものが存在しない。"),
    ],
    "nat": [
        ("拒否のエントリに一致するトラフィックは、破棄される",
         "変換の対象を選択するアクセス・リストにおける拒否は、"
         "破棄ではなく「変換しない」ことを意味する。"),
        ("内部および外部のインターフェイスの指定が、逆になっている",
         "示されている構成では、内部および外部の指定は正しい。"),
    ],
    "vty": [
        ("アクセス・リストが、インターフェイスに対して適用されている",
         "示されている構成では、回線に対して適用されている。"),
        ("拡張のアクセス・リストが用いられている",
         "示されているのは標準のアクセス・リストである。"),
    ],
}

# ★「in ではなく out に適用されている」は BL-109 段B で**実在の故障種**
#   (apply_direction)になったので、無条件の錯乱肢としては使えない
#   (真になる盤面があるのに常に偽として出してしまう)。CLAIMS 側へ移動済み。
# ★3つ目の要素= 「この盤面では**実機で真になり得る**か」の判定。
#   偽の錯乱肢として出してよいのは、真になり得ない盤面だけ
#   (CROSS から in/out を外したのと同じ方針)。
CROSS = [
    ("ルーティング・プロトコルの隣接関係が確立されていない",
     "示されている構成には、ルーティング・プロトコルの設定は含まれていない。",
     # ★実測 G12/G11= 向きや IF を取り違えた ACL は**自機の hello も落とす**ので、
     #   実機では隣接が本当に落ちる。紙面はその効果をモデル化していないが、
     #   「偽である」と言い切ることはできない。
     lambda d: d.get("kind") in BLACKOUT_FILTER_KINDS),
    ("インターフェイスが管理上シャットダウンされている",
     "示されている出力では、当該のインターフェイスは up の状態である。"),
    ("プレフィックス・リストがルート・マップから参照されていない",
     "示されている構成に、プレフィックス・リストおよびルート・マップは存在しない。"),
]


def build_choices_cause(d, rnd):
    kind = d["kind"]
    # ★同じロールの主張から採る(別ロールの主張は「構成が存在しない」で自明に落ち、
    #   錯乱肢として機能しないため)。足りない分は CROSS で埋める。
    pool = [k for k in KINDS
            if role_of(k) == d["role"] and k not in DENSE_KINDS
            and k in CLAIMS]
    others = [k for k in pool if k != kind]
    # ★同時に真になり得る主張は錯乱肢に採らない(cause の一意性)。
    others = [k for k in others if not _also_true(d, k)]
    if len(others) < 2 and not MISCONCEPTION.get(d["role"]):
        raise ValueError(f"acl cause: 錯乱肢が足りない kind={kind}")
    # ★同時に真になる主張を除くと候補が減ることがあるので、不足分は
    #   別サブシステムの錯乱肢(CROSS)で埋めて選択肢数を一定に保つ。
    n_kind = min(3, len(others))
    c = [(CLAIMS[kind], True, "")]
    c += [(CLAIMS[k], False, REFUTES[k]) for k in rnd.sample(others, n_kind)]
    # ★同じロールに他の kind が無い場合(copp/urpf/nat/vty)は、
    #   **そのロール固有のもっともらしい誤解**で埋める(汎用の錯乱肢だけだと
    #   「ACL と無関係な話」ばかりになり、消去法で解けてしまう)。
    mis = MISCONCEPTION.get(d["role"], [])
    n_mis = min(len(mis), max(0, 3 - n_kind))
    c += [(t, False, why) for t, why in rnd.sample(mis, n_mis)]
    rest = max(0, 5 - n_kind - n_mis)
    cross = [(x[0], x[1]) for x in CROSS
             if len(x) < 3 or not x[2](d)]
    c += [(t, False, why)
          for t, why in rnd.sample(cross, min(len(cross), rest))]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _also_true(d, other_kind):
    """別の kind の主張が、この盤面でも**真になってしまう**か(機械判定)。"""
    ents, is_std, name = current_entries(d)
    if other_kind == "undef_ref":
        return ents is None
    if other_kind == "empty_acl":
        return ents == []
    # ★適用点(BL-109): 盤面の**適用の状態**から機械判定する。
    #   ents(=効いている ACL)ではなく defined_acls / apply_binding を見ること。
    if other_kind in APPLY_KINDS:
        a_if, a_dir, _ref = apply_binding(d)
        defined = defined_acls(d)
        if other_kind == "apply_direction":
            return a_if == d.get("if_dn") and a_dir == "out"
        if other_kind == "apply_iface_swap":
            return a_if == d.get("if_up") and a_dir == "in"
        if other_kind in PLACE_KINDS:
            return False               # 故障ではない(構築系)
        if other_kind in EST_KINDS:
            # ★盤面に復路用のリストがあるか / どちら側に established があるか
            if d["kind"] not in EST_KINDS:
                return False
            lists = defined_acls(d)
            if other_kind == "est_missing":
                return not any(e.get("established")
                               for ents, _s, _n in lists for e in ents)
            if other_kind == "est_ret_narrow":
                if len(lists) < 2:
                    return False
                # 復路リストが**対象の全部**を覆っていなければ真
                return any(not stage_pass(d, rev_of(_vec_at(d, o)), "rev")[0]
                           for o in d["target"])
            return any(e.get("established") for e in lists[0][0])
        if other_kind == "apply_wrong_acl":
            return len(defined) >= 2
        if other_kind == "apply_missing":
            return d["role"] == "filter" and a_if is None
        if other_kind == "apply_other_iface":
            return a_if == d.get("if_mgmt")
        if other_kind == "filter_undef_ref":
            return d["role"] == "filter" and not defined
        if other_kind == "filter_empty_acl":
            return any(e == [] for e, _s, _n in defined)
    if ents is None or ents == []:
        return False
    if other_kind == "std_len_blind":
        return is_std and d["role"] == "routefilter"
    if other_kind == "ext_named_rejected":
        return (not is_std) and not name.isdigit()
    if other_kind == "mask_as_wildcard":
        return any(e["src_wild"] & 0xFF000000 for e in ents)
    if other_kind == "wc_bits":
        return any(_noncontiguous(e["src_wild"]) for e in ents)
    if other_kind == "wc_narrow":
        return not ac.covers(ents, target_entries(d))
    if other_kind == "wc_wide":
        return (ac.covers(ents, target_entries(d))
                and not ac.permits_exactly(ents, target_entries(d)))
    if other_kind == "order_shadow":
        return _has_shadow(ents)
    if other_kind == "ext_src_is_network":
        return (not is_std) and any(
            e["src"] & 0xFF == 0 and e["src_wild"] == 0 for e in ents)
    # ★拡張 ACL 固有(機械判定にして手書きの排他表にしない)
    if other_kind == "port_swap":
        return any(e.get("sport") for e in ents)
    if other_kind == "proto_ip_not_tcp":
        return any(e["proto"] == "ip" and e["action"] == "permit"
                   for e in ents)
    if other_kind == "dst_any_too_wide":
        return any(e["proto"] in ("tcp", "udp", "ip") and e["action"] == "permit"
                   and e["dst_wild"] == 0xFFFFFFFF for e in ents)
    return False


def _noncontiguous(w):
    """ワイルドカードのビットが連続していない(=飛び地になる)か。"""
    if w == 0:
        return False
    return bool((w + 1) & w)          # 連続なら w は 2^n-1 の形


def _has_shadow(entries):
    """後続のエントリが、先行のエントリに完全に食われているか。"""
    for i, e in enumerate(entries):
        if i == 0:
            continue
        rest = ac.permit_set([dict(e, action="permit")])
        prev = ac.permit_set([dict(x, action="permit") for x in entries[:i]])
        if ac.set_is_empty(ac.set_minus(rest, prev)):
            return True
    return False


# --------------------------------------------------------------------------
# 自己検査
# --------------------------------------------------------------------------
def _selftest(n=60):
    ok = ng = 0
    fails = []
    # select 形: 全 kind(filter) × 全 world × n seed で一意性
    #   ★apply_place は要件世界が別系統(APPLY_PLACE_WORLDS)なので worlds_for に従う
    for kind in FILTER_KINDS:
        for world in worlds_for(kind):
            good = 0
            for s in range(n):
                try:
                    draw(random.Random(s * 977 + 13), kind=kind, world=world)
                    good += 1
                except ValueError as e:
                    fails.append(f"{kind}/{world}/seed{s}: {e}")
            if good:
                ok += good
            ng += n - good
    print(f"  select 一意性: OK={ok} NG={ng}")

    # ★同一 ACL の中で標準/拡張が混在していないか(見出しと中身の食い違い防止)
    mix = 0
    for kind in FILTER_KINDS:
        for world in FILTER_WORLDS:
            for s2 in range(20):
                try:
                    d = draw(random.Random(s2 * 29 + 5), kind=kind, world=world)
                except ValueError:
                    continue
                ents, is_std, _n = current_entries(d)
                if not ents:
                    continue
                if any((e["proto"] is None) != is_std for e in ents):
                    mix += 1
                    if mix < 4:
                        print(f"    標準/拡張の混在: {kind}/{world}")
    print(f"  標準/拡張の混在: {mix} 件")
    ng += mix

    # ★提示された ACL の文面だけから読み戻して、判定と一致するか
    #   (描画漏れがあると「表示では通るのに判定では通らない」問題になる)
    import acl_model as _am
    rb = 0
    for kind in FILTER_KINDS:
        for world in FILTER_WORLDS:
            for s2 in range(12):
                try:
                    d = draw(random.Random(s2 * 41 + 9), kind=kind, world=world)
                except ValueError:
                    continue
                txt = show_acl_text(d)
                if not txt:
                    continue
                try:
                    back = _am.parse_show_access_lists(txt)
                except Exception as e:
                    rb += 1
                    if rb < 4:
                        print(f"    読み戻し失敗: {kind}/{world}: {e}")
                    continue
                ents1, _s3, name1 = current_entries(d)
                if ents1 is None or ents1 == []:
                    continue        # フィルタ実質不在(適用点の故障)= 比べる先が無い
                # ★盤面に ACL が複数出ることがある(apply_wrong_acl)。
                #   読み戻す先は**いま効いている 1 枚**でなければならない。
                if name1 not in back:
                    rb += 1
                    if rb < 4:
                        print(f"    読み戻しに効いている ACL が無い: "
                              f"{kind}/{world} name={name1}")
                    continue
                ents2 = back[name1]
                for o3 in list(d["target"]) + [d["fourth"], d["outsider"]]:
                    v = _vec_at(d, o3)
                    if _am.evaluate(ents1, v) != _am.evaluate(ents2, v):
                        rb += 1
                        if rb < 5:
                            print(f"    ★提示と判定の不一致: {kind}/{world} "
                                  f"src={o3}")
                        break
    print(f"  提示ACLの読み戻し一致: NG={rb}")
    ng += rb

    # ★dense_list: 「読ませる価値がある盤面か」を機械で担保する
    dn_ok = dn_ng = 0
    for s2 in range(60):
        d = draw(random.Random(s2 * 53 + 7), kind="dense_list")
        ents, _s3, _n3 = current_entries(d)
        items = read_items(d)
        t = sum(1 for _x, ok2 in items if ok2)
        # (a) 通る/通らないが両方あること (b) 行数が6以上
        # (c) ★影になっている行が実在すること(先行 deny に食われる permit)
        shadowed = any(
            first_match(ents, v) is not None
            and ents[first_match(ents, v)]["action"] == "deny"
            and any(acl_model.entry_matches(e2, v) for e2 in ents
                    if e2["action"] == "permit"
                    and e2["seq"] > ents[first_match(ents, v)]["seq"])
            for _t2, v in dense_probes(d))
        if 0 < t < len(items) and len(ents) >= 6 and shadowed:
            dn_ok += 1
        else:
            dn_ng += 1
            if dn_ng < 4:
                print(f"    dense NG: 通る{t}/{len(items)} 行数{len(ents)} "
                      f"影={shadowed}")
    print(f"  dense_list の盤面: OK={dn_ok} NG={dn_ng}")
    ng += dn_ng

    # ★近接肢の質= counter 形の観測に対し「1フィールドだけ違う行」が何本あるか。
    #   これが少ないと選択肢数のわりに実質の判断が浅くなる(出題で判明)。
    nr_ok = nr_ng = 0
    for s2 in range(60):
        d = draw(random.Random(s2 * 67 + 3), kind="dense_list")
        p2 = counter_probe(d)
        if p2 is None:
            continue
        ents, _s3, _n3 = current_entries(d)
        v = p2["vector"]
        near = 0
        for i, e2 in enumerate(ents):
            if i in p2["hits"]:
                continue
            # 送信元が一致するのに、他の1要素で外れている行= 近接肢
            if acl_model._addr_match(e2["src"], e2["src_wild"], v["src"]):
                near += 1
        if near >= 2:
            nr_ok += 1
        else:
            nr_ng += 1
            if nr_ng < 4:
                print(f"    近接肢が少ない: {near} 本")
    print(f"  counter の近接肢(2本以上): OK={nr_ok} NG={nr_ng}")
    ng += nr_ng

    # ★counter の正解が deny 行に固定されていないか(メタ解法の封じ込め)
    act = collections.Counter()
    for s2 in range(120):
        d = draw(random.Random(s2 * 71 + 13), kind="dense_list")
        p2 = counter_probe(d)
        if p2 is None:
            continue
        ents, _s3, _n3 = current_entries(d)
        act[ents[p2["first"]]["action"]] += 1
    tot = sum(act.values())
    share = (act.get("permit", 0) / tot) if tot else 0
    print(f"  counter の正解の内訳: {dict(act)} (permit 率 {share:.0%})")

    # ★compare 形: 2^n 肢のうち真がちょうど1つ／結果が割れていること／
    #   3フロー(=8肢・当てずっぽう 1/8)が主であること
    cp_ok = cp_ng = tri = 0
    for s2 in range(80):
        d = draw(random.Random(s2 * 83 + 11), kind="dense_list")
        fl = compare_flows(d)
        if fl is None:
            cp_ng += 1
            continue
        if len(fl) == 3:
            tri += 1
        outs = {ok2 for _t2, ok2 in fl}
        ch = build_choices_compare(d, random.Random(1))
        if (len(outs) == 2 and len(ch) == (1 << len(fl))
                and sum(1 for _t2, c2, *_r in ch if c2) == 1):
            cp_ok += 1
        else:
            cp_ng += 1
    print(f"  compare 形: OK={cp_ok} NG={cp_ng} (3フロー {tri}/{cp_ok})")
    ng += cp_ng
    if cp_ok and tri / cp_ok < 0.8:
        print("    ★2フローに落ちる盤面が多い(当てずっぽうが 1/4 のまま)")
        ng += 1

    # ★送信元ポートの行が必ず1本入っているか(ユーザ要望)
    sp = sum(1 for s2 in range(60)
             if any(e2.get("sport")
                    for e2 in current_entries(
                        draw(random.Random(s2 * 97 + 5),
                             kind="dense_list"))[0]))
    print(f"  送信元ポートの行を含む盤面: {sp}/60")
    if sp < 60:
        ng += 1
    if share < 0.2:
        print("    ★正解が deny 行に偏っている(『deny を探す』で解けてしまう)")
        ng += 1
    if fails:
        for f in fails[:5]:
            print(f"    {f}")

    # read 形: 提示と判定が同じ関数から出ていること＋選択肢が作れること
    r_ok = r_ng = r_skip = 0
    for kind in KINDS:
        for world in worlds_for(kind):
            for s in range(12):
                rnd = random.Random(s * 31 + 7)
                try:
                    d = draw(rnd, kind=kind, world=world)
                except ValueError:
                    continue
                if "read" not in forms_for(d):
                    # ★そもそも read を持たない種(全許可系・全断系・構築系)。
                    #   一覧を二重管理しないよう forms_for に判断を委ねる。
                    r_skip += 1
                    continue
                pol = read_polarity(d)
                if pol is None:
                    if kind in NO_READ_KINDS:
                        r_skip += 1
                        continue
                    r_ng += 1
                    if r_ng < 4:
                        print(f"    read 症状なし: {kind}/{world}")
                    continue
                try:
                    ch = build_choices_read(d, rnd)
                    assert sum(1 for _t, c, _w in ch if c) == 1
                    assert len(ch) >= 3
                    r_ok += 1
                except (ValueError, AssertionError) as e:
                    r_ng += 1
                    if r_ng < 6:
                        print(f"    read 選択肢NG: {kind}/{world}: {e}")
    print(f"  read 観測: OK={r_ok} NG={r_ng} (read不可={r_skip}=全許可系)")

    # cause 形: 正解1つ・錯乱肢が偽であること
    c_ok = c_ng = 0
    for kind in KINDS:
        for world in worlds_for(kind):
            for s in range(4):
                rnd = random.Random(s * 53 + 3)
                try:
                    d = draw(rnd, kind=kind, world=world)
                    if "cause" not in forms_for(d):
                        continue      # dense_list / apply 系は cause を持たない
                    ch = build_choices_cause(d, rnd)
                except ValueError as e:
                    c_ng += 1
                    if c_ng < 4:
                        print(f"    cause NG: {kind}/{world}: {e}")
                    continue
                if sum(1 for _t, c, _w in ch if c) == 1:
                    c_ok += 1
                else:
                    c_ng += 1
    print(f"  cause 一意性: OK={c_ok} NG={c_ng}")

    # 実測との整合(poc/acl/README.md)
    m_ok = m_ng = 0

    def chk(cond, label):
        nonlocal m_ok, m_ng
        if cond:
            m_ok += 1
        else:
            m_ng += 1
            print(f"    実測不一致: {label}")

    d = draw(random.Random(1), kind="undef_ref", world="keep_others")
    chk(route_kept(d, d["nb_up"], d["target"][0]), "未定義参照= 全許可(§1)")
    d = draw(random.Random(2), kind="empty_acl", world="keep_others")
    chk(route_kept(d, d["nb_up"], d["target"][0]), "空 ACL= 全許可(§2)")
    d = draw(random.Random(3), kind="std_len_blind", world="prefixlen_no_rm")
    chk(not route_kept(d, d["nb_up"], d["target"][0], 24)
        and not route_kept(d, d["nb_dn"], d["target"][0], 28),
        "標準 ACL は /24 と /28 を区別しない(§3)")
    d = draw(random.Random(4), kind="ext_named_rejected", world="by_neighbor")
    chk(all(route_kept(d, a, o) for a, o in
            [(d["nb_up"], d["target"][0]), (d["nb_dn"], d["outsider"])]),
        "名前付き拡張は適用されず素通り(§4-1)")
    d = draw(random.Random(5), kind="ext_src_is_network", world="by_neighbor")
    # 1行目(src=広告元ルータ)は効き、2行目(src=網)は何にも一致しない
    chk(route_kept(d, d["nb_up"], d["target"][0]),
        "拡張で src=広告元ルータ の行は効く(§4-2 E3)")
    chk(not route_kept(d, d["nb_up"], d["target"][1])
        and not route_kept(d, d["nb_up"], d["target"][2]),
        "拡張の src に網を書いた行は何にも一致しない(§4-2 E2/E4)")
    # 拡張で src=広告元ルータなら、その隣接の経路だけ残る(§4-2 E3)
    ents = [ac.entry("permit", "ip", src=d["nb_up"], sw="0.0.0.0", seq=10)]
    up = acl_model.evaluate(ents, {"proto": "ip", "src": d["nb_up"],
                                   "dst": net(d, d["target"][0])})
    dn = acl_model.evaluate(ents, {"proto": "ip", "src": d["nb_dn"],
                                   "dst": net(d, d["target"][0])})
    chk(up and not dn, "拡張の src= 広告元ルータ(§4-2 E3)")
    # マスク書き間違いは別物になる(§10)
    d = draw(random.Random(6), kind="mask_as_wildcard", world="exact_no_deny")
    chk(not flow_passes(d, d["target"][1]) or not flow_passes(d, d["target"][2]),
        "サブネットマスク記述は意図した集合にならない(§10)")
    # ★C1(2026-08-11): 参照経路で意味論が切り替わる
    d = draw(random.Random(21), kind="std_len_blind", world="prefixlen_via_rm")
    cand = {k: fn for k, _t, _c, fn in fix_candidates(d)}
    chk(cand["rm_mask"](d["nb_up"], d["target"][0], 24)
        and not cand["rm_mask"](d["nb_up"], d["target"][0], 28),
        "route-map 経由は dst=マスクで長さを絞れる(C1d)")
    chk(not cand["ext_src_nb"](d["nb_up"], d["target"][0], 24) is None,
        "直接指定は src=広告元(C1c で route-map には無い概念)")
    chk(verify_fix(d) == "rm_mask", "prefix-list 禁止の世界では route-map が正解")
    d2 = draw(random.Random(22), kind="std_len_blind", world="prefixlen_no_rm")
    chk(verify_fix(d2) == "plist", "route-map 禁止の世界では prefix-list が正解")
    chk("rm_mask" in d2.get("_fix_works", []),
        "route-map 解も『結果は出せる』候補として成立している")
    print(f"  実測との整合: OK={m_ok} NG={m_ng}")

    # --- P1b: counter / patch / fix ---
    b_ok = b_ng = 0
    seen_forms = set()
    for kind in KINDS:
        for world in worlds_for(kind):
            for s in range(20):
                rnd = random.Random(s * 71 + 5)
                try:
                    d = draw(rnd, kind=kind, world=world)
                except ValueError:
                    continue
                avail = forms_for(d)
                seen_forms |= set(avail)
                for form, fn in (("counter", build_choices_counter),
                                 ("patch", build_choices_patch),
                                 ("fix", build_choices_fix),
                                 ("evidence", build_choices_evidence),
                                 ("logread", build_choices_logread)):
                    if form not in avail:
                        continue
                    try:
                        ch = fn(d, rnd)
                        n_cor = sum(1 for _t, c, *_r in ch if c)
                        want = 2 if form == "logread" else 1
                        assert n_cor == want, f"正解 {n_cor} 個(想定 {want})"
                        assert len(ch) >= 3, f"選択肢 {len(ch)} 個"
                        b_ok += 1
                    except (ValueError, AssertionError) as e:
                        b_ng += 1
                        if b_ng < 6:
                            print(f"    {form} NG: {kind}/{world}: {e}")
    print(f"  P1b/P1c(counter/patch/fix/evidence/logread): "
          f"OK={b_ok} NG={b_ng}")
    need = {"counter", "patch", "fix", "evidence", "logread"}
    missing = need - seen_forms
    if missing:
        print(f"    ★成立しない形がある: {sorted(missing)}")
        b_ng += 1

    # counter 形の要点(後続の一致行は増えない)が実際に成り立っているか
    cp_ok = cp_ng = 0
    for s in range(40):
        d = draw(random.Random(s * 97 + 11), kind="order_shadow")
        p = counter_probe(d)
        if p and len(p["hits"]) >= 2 and p["first"] == p["hits"][0]:
            cp_ok += 1
        elif p:
            cp_ng += 1
    print(f"  counter 先頭一致: OK={cp_ok} NG={cp_ng}")

    # ★適用点(BL-109 段A)。ここで担保するのは3点:
    #   (a) 提示(interface_blocks / ipif_acl_text)と apply_binding が一致すること
    #   (b) 故障が**提示物のどこかに現れる**こと(現れないと解答不能)
    #   (c) 「実質不在」4種が本当に全許可になっていること(実測 §16-4)
    ap_ok = ap_ng = 0
    for kind in APPLY_KINDS:
        for s2 in range(30):
            d = draw(random.Random(s2 * 31 + 5), kind=kind)
            amap = apply_map(d)
            blocks = interface_blocks(d)
            bad = None
            # (a) 提示された適用行の集合が apply_map と**過不足なく**一致すること
            cur, seen = None, {}
            for l in blocks:
                if l.startswith("interface "):
                    cur = l.split()[1]
                elif "access-group" in l:
                    _x, _y, ref, dr = l.split()
                    seen[(cur, dr)] = ref
            if seen != amap:
                bad = f"適用行が apply_map と不一致: {seen} != {amap}"
            a_if, a_dir, a_ref = apply_binding(d)
            # `show ip interface` の描画も binding に追随すること
            #   ★方向も見る(apply_direction は Outgoing 側に出る)
            if not bad:
                for ifn in (d["if_dn"], d["if_up"], d["if_mgmt"]):
                    txt = ipif_acl_text(d, ifn)
                    for dr, label in (("in", "Inbound  access list is"),
                                      ("out", "Outgoing access list is")):
                        want = amap.get((ifn, dr), "not set")
                        if f"{label} {want}" not in txt:
                            bad = (f"show ip interface {ifn} の {dr} が "
                                   f"binding と不一致")
                            break
                    if bad:
                        break
            # (b) 健全な盤面(正しい ACL を顧客側 in)と提示物が違うこと
            if not bad:
                h = dict(d, kind="wc_narrow")     # 適用点は正常な kind
                same_acl = show_acl_text(d) == show_acl_text(h)
                same_if = interface_blocks(d) == interface_blocks(h)
                if same_acl and same_if:
                    bad = "健全な盤面と提示物が同一(解答不能)"
            # (c) 実質不在の4種は全許可
            if not bad and kind in INERT_FILTER_KINDS:
                if not all(ok for _t, ok in read_items(d)):
                    bad = "実質不在のはずが落ちる観測がある"
            if not bad and kind in BLACKOUT_FILTER_KINDS:
                if any(ok for _t, ok in read_items(d)):
                    bad = "全断のはずが通る観測がある"
            if bad:
                ap_ng += 1
                if ap_ng < 5:
                    print(f"    ★適用点 NG: {kind}: {bad}")
            else:
                ap_ok += 1
    print(f"  適用点の提示と binding: OK={ap_ok} NG={ap_ng}")

    # ★filter ロールの evidence 形= 最良の出力が一意であること(実測 §16-4)
    ev_ok = ev_ng = 0
    for kind in FILTER_EVIDENCE_HYPS + BLACKOUT_EVIDENCE_HYPS:
        for s2 in range(20):
            d = draw(random.Random(s2 * 37 + 11), kind=kind)
            if not evidence_ok(d):
                ev_ng += 1
                if ev_ng < 4:
                    sp = [len(set(v.values()))
                          for _t, v in evidence_observations(d)]
                    print(f"    ★evidence NG: {kind} splits={sp} "
                          f"hyps={evidence_hyps(d)}")
                continue
            ch = build_choices_evidence(d, random.Random(s2))
            # ★仮説は問題文に**明示**される(gen_paper_mcq.acl_evidence_lead)ので、
            #   すべて CLAIMS を持っていなければならない。
            if not all(k in CLAIMS for k in evidence_hyps(d)):
                ev_ng += 1
                print(f"    ★evidence NG: {kind}: CLAIMS の無い仮説がある "
                      f"{[k for k in evidence_hyps(d) if k not in CLAIMS]}")
            elif sum(1 for _t, ok, _w in ch if ok) != 1:
                ev_ng += 1
            else:
                ev_ok += 1
    print(f"  filter evidence の一意性: OK={ev_ok} NG={ev_ng}")

    # ★ワイルドカードの組み立てが主題の世界(ユーザ要望 2026-08-11)。
    #   ①正解は**パターンが指すワイルドカード**そのものであること
    #   ②1行の錯乱肢が3本以上あり、いずれも成立しないこと
    #   ③対象集合がパターンどおりであること
    wc_ok = wc_ng = 0
    for world in WC_WORLDS:
        pat = SRC_PATTERNS[world]
        for kind in ("wc_narrow", "wc_wide", "order_shadow", "port_swap"):
            if (kind, world) in INCOMPATIBLE:
                continue
            for s2 in range(8):
                try:
                    d = draw(random.Random(s2 * 61 + 5), kind=kind, world=world)
                except ValueError as e:
                    wc_ng += 1
                    if wc_ng < 4:
                        print(f"    ★WC NG: {kind}/{world}: {e}")
                    continue
                b0 = d["base"]
                cands = select_candidates(d)
                good = [k for k, l, e in cands
                        if _select_works(d, e) and _select_complies(d, l, e)]
                ones = [k for k, l, e in cands if len(l) == 1]
                bad = None
                if d["target"] != [b0 + o for o in pat["offs"]]:
                    bad = f"対象集合がパターンと違う: {d['target']}"
                elif good != ["cube"]:
                    bad = f"正解が cube でない: {good}"
                elif len(ones) < 4:
                    bad = f"1行の候補が少ない({len(ones)})"
                else:
                    a_off, a_wc = pat["ans"]
                    want = f"{net(d, b0 + a_off)} 0.0.{a_wc}.255"
                    line = [l for k, l, _e in cands if k == "cube"][0][0]
                    if want not in line:
                        bad = f"正解の WC がパターンと違う: {line}"
                if bad:
                    wc_ng += 1
                    if wc_ng < 4:
                        print(f"    ★WC NG: {kind}/{world}: {bad}")
                else:
                    wc_ok += 1
    print(f"  WC トリック世界: OK={wc_ok} NG={wc_ng}")

    # ★1行では書けないレンジ(論点4)。
    #   ①1行の候補が**1つも成立しない**こと(=「1行で書ける」は誤り)
    #   ②nb_min の正解は deny 先行2行・nb_no_deny の正解は**大きさの違う3つ**
    #   ③2世界で正解が反転すること
    nb_ok = nb_ng = 0
    nb_correct = {}
    for world in NB_WORLDS:
        for kind in ("wc_narrow", "wc_wide", "order_shadow", "port_swap"):
            for s2 in range(8):
                try:
                    d = draw(random.Random(s2 * 67 + 9), kind=kind, world=world)
                except ValueError as e:
                    nb_ng += 1
                    if nb_ng < 4:
                        print(f"    ★NB NG: {kind}/{world}: {e}")
                    continue
                cands = select_candidates(d)
                bad = None
                if len(d["target"]) != 7:
                    bad = f"対象が7本でない: {len(d['target'])}"
                elif any(len(l) == 1 and _select_works(d, e)
                         for _k, l, e in cands):
                    bad = "1行で成立する候補がある(レンジが境界に載っている)"
                elif sum(1 for _k, l, _e in cands
                         if any(" deny " in ln for ln in l)) < 2:
                    # ★正解が「唯一 deny を含む肢」だと見た目で当てられる
                    bad = "deny を含む候補が1本しかない"
                else:
                    nb_correct.setdefault(world, set()).add(
                        d["_select_correct"])
                    if d["_select_correct"] != ("deny1" if world == "nb_min"
                                                else "split3"):
                        bad = f"正解が想定と違う: {d['_select_correct']}"
                if bad:
                    nb_ng += 1
                    if nb_ng < 4:
                        print(f"    ★NB NG: {kind}/{world}: {bad}")
                else:
                    nb_ok += 1
    if nb_correct.get("nb_min") == nb_correct.get("nb_no_deny"):
        nb_ng += 1
        print(f"    ★NB NG: 2世界で正解が反転していない {nb_correct}")
    print(f"  1行で書けないレンジ: OK={nb_ok} NG={nb_ng} "
          f"(正解: {[(w, sorted(v)) for w, v in sorted(nb_correct.items())]})")

    # ★戻り通信(P2-⑤)。①est_build は works がちょうど1(構造で一意)
    #   ②est_ret_narrow は read / compare が成立する(全断でない)
    eb_ok = eb_ng = 0
    for s2 in range(30):
        d = draw(random.Random(s2 * 71 + 3), kind="est_build")
        cands = est_build_candidates(d)
        good = [k for k, _l, e in cands if est_build_works(d, e)]
        ch = build_choices_select(d, random.Random(s2))
        bad = None
        if good != ["est"]:
            bad = f"works が est 1つでない: {good}"
        elif len(ch) != 6:
            bad = f"選択肢が6つでない({len(ch)})"
        elif sum(1 for _t, o, _w, _l in ch if o) != 1:
            bad = "正解が1つでない"
        elif any(not w for _t, o, w, _l in ch if not o):
            bad = "誤答肢に理由が付いていない"
        elif any("access-group" in l for l in interface_blocks(d)
                 if d["if_up"] in l):
            bad = "復路用リストが既に適用されている(構築系なのに)"
        if bad:
            eb_ng += 1
            if eb_ng < 4:
                print(f"    ★est_build NG: {bad}")
        else:
            eb_ok += 1
    en_ok = en_ng = 0
    for s2 in range(30):
        d = draw(random.Random(s2 * 73 + 5), kind="est_ret_narrow")
        fs = forms_for(d)
        vals = [ok2 for _t, ok2 in read_items(d)]
        if "read" not in fs or "compare" not in fs:
            en_ng += 1
            if en_ng < 3:
                print(f"    ★est_ret_narrow NG: forms={fs}")
        elif not (any(vals) and not all(vals)):
            en_ng += 1
        else:
            en_ok += 1
    print(f"  戻り通信: est_build OK={eb_ok} NG={eb_ng} / "
          f"est_ret_narrow OK={en_ok} NG={en_ng}")

    # ★apply 形(段B の構築系)= 「意味的に成立する候補≥2・制約適合=ちょうど1」
    #   ＋世界で**正解の IF が反転する**こと(被覆エンジンの狙いが機能しているか)。
    pl_ok = pl_ng = 0
    seen_correct = {}
    for world in APPLY_PLACE_WORLDS:
        for s2 in range(30):
            d = draw(random.Random(s2 * 43 + 3), kind="apply_place", world=world)
            pt = d["_apply_correct"]
            seen_correct.setdefault(world, set()).add(
                "dn" if pt[0] == d["if_dn"] else
                "up" if pt[0] == d["if_up"] else "mgmt")
            ch = build_choices_apply(d, random.Random(s2))
            bad = None
            blocks = interface_blocks(d)
            names = {n for _e, _s, n in defined_acls(d)}
            if any("access-group" in l for l in blocks):
                # ★「どこに適用すべきか」を問うのに適用済みの構成を見せない
                bad = "構築系なのに提示の構成に適用行がある"
            elif not all(any(f"access-group {n} " in txt
                             for n in names) for txt, _o, _w in ch):
                bad = "選択肢が提示された ACL を参照していない"
            elif len(ch) != 6:
                bad = f"選択肢が6つでない({len(ch)})"
            elif sum(1 for _t, o, _w in ch if o) != 1:
                bad = "正解が1つでない"
            elif len([q for q in apply_points(d) if apply_works(d, q)]) != 1:
                bad = "意味的に成立する候補が1つでない(構造で一意になっていない)"
            elif any(not w for _t, _o, w in ch if not _o):
                bad = "誤答肢に理由が付いていない"
            if bad:
                pl_ng += 1
                if pl_ng < 4:
                    print(f"    ★apply NG: {world}: {bad}")
            else:
                pl_ok += 1
    if seen_correct.get("src_customer") != {"dn"} or \
            seen_correct.get("src_server") != {"up"} or \
            seen_correct.get("deny_to_mgmt") != {"mgmt"}:
        pl_ng += 1
        print(f"    ★apply NG: 世界で正解の IF が反転していない {seen_correct}")
    print(f"  apply 形の一意性: OK={pl_ok} NG={pl_ng} "
          f"(正解IF: {[(w, sorted(v)) for w, v in sorted(seen_correct.items())]})")

    total_ng = (ng + r_ng + c_ng + m_ng + b_ng + cp_ng + ap_ng + ev_ng
                + pl_ng + wc_ng + nb_ng + eb_ng + en_ng)

    print(f"gen_paper_acl selftest: NG合計={total_ng}")
    return total_ng == 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    print(__doc__)
