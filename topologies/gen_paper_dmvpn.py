#!/usr/bin/env python3
"""DMVPN 紙面ファミリ (BL-179 = BL-118 P4 の実体) — gen_paper_mcq.py の shape=dmvpn 素材。

設計= 非公開側の計画メモ(2026-09-18) §3 A4。
kinds:
  syntax  (瞬発) `ip nhrp <X> ?` / `tunnel <X> ?` の後続オプション集合(**iol-xe 17.15.1 の `?` 実測**= poc/paper-kb P1)。
          X を抽選すると正解集合が動く(select2/allthat)。誤答肢は他コマンドの後続語だけから作る(版依存の語は正解側にしか置かない)。
  meaning (瞬発) キーワードの意味(shared / map multicast dynamic / tunnel key / nhs 単行形 / registration no-unique / holdtime /
          redirect / shortcut / mode gre multipoint / authentication)の事実ベース(select/select2/allthat/match)。
  phase   (思考) hub/spoke の構成を読んでフェーズと spoke 間通信の経路を判定する read/cause/fix(小さな真偽関数)。
★`show dmvpn` 等の実出力読解(cause)は P7(IOL で IPsec 込みの実測)後に追加する。
"""
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KINDS = ["syntax", "meaning", "phase", "nhrp"]
SPEED_KINDS = ["syntax", "meaning"]
THINK_KINDS = ["phase", "nhrp"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {"syntax": {"select2", "allthat"}, "meaning": {"select", "select2", "allthat", "match"},
         "phase": {"read", "cause", "fix"}, "nhrp": {"read", "cause", "fix"}}
DIFF = {"syntax": 2, "meaning": 2, "phase": 4, "nhrp": 4}


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


# ==========================================================================
# syntax: 実機 `?` の後続オプション(iol-xe 17.15.1・poc/paper-kb P1)
#   (表示用コマンド, 正解集合, 表示ラベル)
# ==========================================================================
SYNTAX = {
    "ip nhrp registration": (["differential", "no-unique", "req-def-map", "timeout"], "登録(registration)パケットの設定"),
    "ip nhrp map": (["A.B.C.D(宛先のトンネル IP アドレス)", "multicast"], "宛先 IP から NBMA アドレスへのマッピング"),
    "ip nhrp map multicast": (["A.B.C.D(NBMA アドレス)", "X:X:X:X::X(IPv6 の NBMA アドレス)", "dynamic"], "マルチキャストのマッピング"),
    "ip nhrp nhs": (["A.B.C.D(NHS のプロトコル アドレス)", "cluster", "dynamic", "fallback"], "ネクスト ホップ サーバの指定"),
    "ip nhrp nhs <NHS のアドレス>": (["cluster", "nbma", "priority"], "ネクスト ホップ サーバの指定(アドレスの後)"),
    "ip nhrp nhs <NHS のアドレス> nbma <NBMA アドレス>": (["cluster", "multicast", "priority"], "ネクスト ホップ サーバの指定(nbma の後)"),
    "ip nhrp shortcut": (["virtual-template"], "ショートカット スイッチングの有効化"),
    "ip nhrp redirect": (["interest", "timeout"], "リダイレクトの有効化"),
    "tunnel mode gre": (["ip", "ipv6", "multipoint"], "GRE トンネルのモード"),
    "tunnel protection": (["ipsec", "psk"], "トンネルの保護"),
    "tunnel protection ipsec profile <プロファイル名>": (["ikev2-profile", "isakmp-profile", "shared"], "IPsec プロファイルの適用"),
}
# 全コマンドの後続語ボキャブラリ(誤答肢の供給源)。★正解集合に含まれない語だけを使う
VOCAB = ["authentication", "holdtime", "network-id", "gre multipoint", "multicast dynamic", "nbma", "priority", "shared",
         "differential", "no-unique", "req-def-map", "timeout", "dynamic", "fallback", "cluster", "interest",
         "virtual-template", "multipoint", "ipsec", "psk", "ikev2-profile", "isakmp-profile", "key", "source", "destination",
         "unique", "register", "ipv6", "ip", "mode", "server-only", "shortcut", "redirect", "map", "nhs"]
VOCAB_WHY = {
    "authentication": "authentication は ip nhrp authentication として独立したコマンドであり、このコマンドの後続語ではない。",
    "holdtime": "holdtime は ip nhrp holdtime として独立したコマンドであり、このコマンドの後続語ではない。",
    "network-id": "network-id は ip nhrp network-id として独立したコマンドであり、このコマンドの後続語ではない。",
    "gre multipoint": "gre multipoint は tunnel mode gre multipoint の語であり、このコマンドの後続語ではない。",
    "multicast dynamic": "multicast dynamic は ip nhrp map multicast dynamic の語であり、このコマンドの後続語ではない。",
}


def _norm(opt):
    return opt.split("(")[0]


# ==========================================================================
# meaning: 事実ベース
# ==========================================================================
KEYWORDS = {
    "shared": "tunnel protection ipsec profile <名> shared",
    "mcast_dyn": "ip nhrp map multicast dynamic",
    "tkey": "tunnel key",
    "nhs_one": "ip nhrp nhs <トンネル IP> nbma <NBMA> multicast",
    "no_unique": "ip nhrp registration no-unique",
    "holdtime": "ip nhrp holdtime",
    "redirect": "ip nhrp redirect",
    "shortcut": "ip nhrp shortcut",
    "mgre": "tunnel mode gre multipoint",
    "auth": "ip nhrp authentication",
}
FACTS = {
    "shared": [
        ("トンネルの送信元インターフェイスが同一である複数のトンネル インターフェイスで、同じ IPsec プロファイルを使うときに指定する。", True, ""),
        ("複数のトンネルで暗号ソケットを共用する(実機のヘルプでは Use a shared socket for the crypto connection)。", True, ""),
        ("トンネルの送信元インターフェイスが異なる複数のトンネルで、異なる IPsec プロファイルを使うときに指定する。", False, "送信元が同じで同じプロファイルを使うときの指定である。"),
        ("トンネルの送信元インターフェイスが同一である複数のトンネルで、それぞれ異なる IPsec プロファイルを使うときに指定する。", False, "同じプロファイルを共有するときの指定である。"),
        ("同じ送信元と同じプロファイルを持つ 2 本目のトンネルに、このキーワード無しで tunnel protection を構成すると、設定はエラーで拒否される。", True, ""),
        ("既に稼働しているトンネルにこのキーワードを追加すると、トンネル インターフェイスは自動的に shutdown され、no shutdown が必要になる。", True, ""),
        ("2 本目のトンネルにだけ指定すれば、1 本目のトンネルの設定は変更しなくてよい。", False, "同じ送信元と同じプロファイルを持つすべてのトンネルに shared が必要である(片方だけではエラーになる)。"),
        ("送信元が同じでも、IPsec プロファイルが異なるトンネル同士には、このキーワードが必要である。", False, "条件は同一の送信元かつ同一のプロファイルであり、プロファイルが異なれば不要である。"),
        ("IKE の事前共有鍵を複数のピアで共有することを意味する。", False, "shared は IPsec プロファイル(暗号ソケット)の共有であり、鍵の共有ではない。"),
    ],
    "mcast_dyn": [
        ("ハブで設定し、登録してきたスポークの NBMA アドレスをマルチキャスト(ルーティング プロトコルの Hello など)の宛先として自動的に加える。", True, ""),
        ("ハブでスポークごとの ip nhrp map multicast <NBMA> の記述を不要にする。", True, ""),
        ("ハブでこの設定を外すと、ハブはスポークからの Hello を受け取り続けるが、スポークはハブからの Hello を受け取れず、ルーティング プロトコルの隣接が片側だけに見える。", True, ""),
        ("ハブでこの設定を外しても、スポークとのユニキャストの通信(ping)は成立する。", True, ""),
        ("ハブでこの設定を外すと、スポークの NHRP 登録が失敗する。", False, "登録はユニキャストであり成立する(show dmvpn は UP のまま)。影響を受けるのはマルチキャストの複製だけである。"),
        ("スポークで設定し、ハブの NBMA アドレスを動的に学習する。", False, "スポークはハブの NBMA を静的に指定する(ip nhrp map multicast <ハブ NBMA> または nhs 単行形)。"),
        ("ユニキャストの宛先解決をハブに動的に問い合わせる設定である。", False, "ユニキャストの解決は NHRP の resolution であり、この設定はマルチキャストのマッピングである。"),
    ],
    "tkey": [
        ("同じ送信元と宛先を持つ複数のトンネルを識別するための値であり、DMVPN では全メンバで一致させる。", True, ""),
        ("値が一致しないトンネル間では、GRE パケットが受け入れられず NHRP の登録も成立しない。", True, ""),
        ("IPsec の事前共有鍵を指定するコマンドである。", False, "tunnel key は GRE のキーであり、IPsec の鍵ではない。"),
        ("NHRP の認証文字列を指定するコマンドである。", False, "NHRP の認証は ip nhrp authentication である。"),
    ],
    "nhs_one": [
        ("ip nhrp nhs・ip nhrp map・ip nhrp map multicast の 3 行を 1 行にまとめた書き方である。", True, ""),
        ("スポークで設定し、ハブのトンネル IP と NBMA アドレス、およびマルチキャストの宛先を同時に指定する。", True, ""),
        ("ハブで設定し、スポークからの登録を受け付ける設定である。", False, "ハブ側は登録を受ける側であり、nhs の指定はスポーク側である。"),
        ("multicast を付けると、そのスポークがマルチキャストのルータ(DR)になる。", False, "multicast はマルチキャストのマッピングの追加であり、DR の指定ではない。"),
    ],
    "no_unique": [
        ("登録要求に Unique フラグを立てず、スポークの NBMA アドレスが変わったときにハブのマッピングを上書きできるようにする。", True, ""),
        ("スポークの物理アドレスが DHCP などで変わる構成で、ハブが古いマッピングの保持時間の満了を待たずに更新できるようにする。", True, ""),
        ("ハブに同じトンネル IP を持つスポークが複数登録することを許す。", False, "Unique フラグは NBMA アドレスの更新可否に関する指示であり、重複登録の許可ではない。"),
        ("登録の間隔を秒で指定する。", False, "登録の間隔は ip nhrp registration timeout である。"),
    ],
    "holdtime": [
        ("自分の NBMA アドレスの情報を、相手の NHRP キャッシュに保持させる時間(秒)を指定する。", True, ""),
        ("値は NHRP の登録や解決の応答に載せて相手へ通知される。", True, ""),
        ("NHRP の登録を再送するまでの時間を指定する。", False, "登録の再送間隔は ip nhrp registration timeout である。"),
        ("GRE トンネルのキープアライブの間隔を指定する。", False, "キープアライブは keepalive コマンドであり、holdtime は NHRP キャッシュの保持時間である。"),
    ],
    "redirect": [
        ("ハブで設定し、スポーク宛のパケットを別のスポークへ中継したときに、送信元スポークへ NHRP Redirect を送る(フェーズ 3)。", True, ""),
        ("ハブがトラフィックを中継しながら、スポーク間に直接のトンネルを組ませるきっかけを与える。", True, ""),
        ("スポークで設定し、ハブから受け取った Redirect に基づいて経路を書き換える。", False, "スポーク側の設定は ip nhrp shortcut である。"),
        ("フェーズ 2 のスポーク間通信を有効にする設定である。", False, "redirect/shortcut はフェーズ 3 の機構である。"),
    ],
    "shortcut": [
        ("スポークで設定し、ハブからの NHRP Redirect を受けて宛先を解決し、解決した経路で直接転送する(フェーズ 3)。", True, ""),
        ("解決した情報は、ルーティング テーブルの経路より優先して転送に使われる(ショートカット)。", True, ""),
        ("ハブで設定し、スポークへ Redirect を送る。", False, "ハブ側の設定は ip nhrp redirect である。"),
        ("スポークのトンネルをポイントツーポイントの GRE にする設定である。", False, "トンネルのモードは tunnel mode gre multipoint で指定する。"),
    ],
    "mgre": [
        ("1 つのトンネル インターフェイスで複数の対向とトンネルを張るモードであり、ハブでは必須である。", True, ""),
        ("宛先は tunnel destination で固定せず、NHRP で解決した NBMA アドレスを使う。", True, ""),
        ("フェーズ 2 以降のスポーク間直接通信には、スポークもこのモードである必要がある。", True, ""),
        ("フェーズ 1 のスポークで必須の設定である。", False, "フェーズ 1 のスポークはポイントツーポイントの GRE(tunnel destination 指定)でよい。"),
        ("tunnel destination と組み合わせて使う。", False, "multipoint では tunnel destination を指定しない(NHRP が宛先を解決する)。"),
    ],
    "auth": [
        ("NHRP のパケットに付ける認証文字列で、DMVPN の全メンバで一致させる。", True, ""),
        ("文字列は最大 8 文字である。", True, ""),
        ("一致しない場合、NHRP の登録や解決は受け付けられない。", True, ""),
        ("IPsec の事前共有鍵を指定する。", False, "IPsec の鍵は crypto isakmp key / keyring で指定する。"),
        ("文字列は最大 32 文字である。", False, "上限は 8 文字である。"),
    ],
}
MATCH_SET = [
    ("shared", "同じ送信元インターフェイスの複数のトンネルで同じ IPsec プロファイルを使うときに指定するキーワード"),
    ("mcast_dyn", "登録してきたスポークの NBMA アドレスをマルチキャストの宛先に自動で加えるハブ側の設定"),
    ("redirect", "スポーク宛のパケットを中継したときに送信元スポークへ Redirect を送るハブ側の設定"),
    ("shortcut", "Redirect を受けて解決した経路で直接転送するスポーク側の設定"),
    ("no_unique", "スポークの NBMA アドレスの変更をハブが受け付けられるようにする登録のオプション"),
    ("holdtime", "自分の NBMA 情報を相手のキャッシュに保持させる時間"),
    ("tkey", "同じ送信元と宛先の複数トンネルを識別する GRE の値"),
]

CORE = {
    "syntax": "後続オプションは実機の `?` から機械生成(iol-xe 17.15.1)。registration= differential/no-unique/req-def-map/timeout(旧 IOS は no-unique/timeout の 2 つ)。map= A.B.C.D | multicast、map multicast= NBMA | dynamic、nhs= addr | cluster | dynamic | fallback、nhs <addr>= cluster | nbma | priority、… nbma <x>= cluster | multicast | priority、shortcut= virtual-template、redirect= interest | timeout、tunnel mode gre= ip | ipv6 | multipoint、tunnel protection= ipsec | psk、… ipsec profile X= ikev2-profile | isakmp-profile | shared。",
    "meaning": "shared= 同じ tunnel source の複数トンネルで同じ IPsec プロファイル(暗号ソケット共用)。map multicast dynamic= ハブが登録スポークをマルチキャスト宛先に自動追加。tunnel key= GRE のキー(全メンバ一致)。nhs 単行形= nhs+map+map multicast。registration no-unique= NBMA 変更をハブが受け付ける。holdtime= 自分の情報の相手側保持時間。redirect(ハブ)/shortcut(スポーク)= フェーズ 3。gre multipoint= 1 IF で多対向(ハブ必須・フェーズ 2/3 はスポークも)。authentication= 8 文字以内で全員一致。",
    "nhrp": "show dmvpn の State 列で層を割る: IKE= IKEv2 SA が成立しない(NBMA/到達性/鍵)・NHRP= IKE は READY で NHRP 登録が通らない(authentication/tunnel key/NHS アドレス)・UP= 登録済み。NHRP 同士はハブ側の痕跡で割る: authentication 不一致= ハブに %DMVPN-3-DMVPN_NHRP_ERROR wrong authentication string・NHS トンネル IP 誤り= ハブの show dmvpn に IX のエントリと NHRP Encap Error・tunnel key 不一致= GRE が捨てられハブに痕跡が残らない。network-id はローカル有意で不一致でも登録・ショートカットは成立する(実測)。ショートカット後はスポークに DT1(NBMA 解決・経路導入)/DT2(next-hop override・%/[NHO])が並び、show ip route の詳細ビューの next-hop はハブのまま。iol-xe 17.15.1 実測(poc/paper-kb P7)。",
    "phase": "フェーズ 1= スポークが p2p GRE(全通信がハブ経由)。フェーズ 2= スポークも mGRE・ハブは redirect なし。スポーク間直接通信には**スポークがもう一方のスポークを next-hop とする経路**が要る(EIGRP: ハブで no ip split-horizon と no ip next-hop-self / OSPF: broadcast 型でハブを DR)。集約すると直接通信できない。フェーズ 3= ハブ ip nhrp redirect＋スポーク ip nhrp shortcut。next-hop がハブでも Redirect/解決で直接化でき、集約も可(split-horizon の解除はやはり必要)。",
}
TITLES = {"syntax": "DMVPN(NHRP/トンネル)のコマンド構文", "meaning": "DMVPN のキーワードの意味", "phase": "DMVPN のフェーズと経路の分析",
          "nhrp": "DMVPN の show 出力の分析(NHRP 登録・ショートカット)"}
NAMES = [("HUB", "SPOKE1", "SPOKE2"), ("R1", "R2", "R3"), ("HQ", "BR1", "BR2"), ("DC-HUB", "SITE-A", "SITE-B")]


# ==========================================================================
# draw
# ==========================================================================
def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    d["hub"], d["s1"], d["s2"] = rnd.choice(NAMES)
    if kind == "syntax":
        d["cmd"] = rnd.choice([c for c, (opts, _) in SYNTAX.items() if len(opts) >= 2])
    elif kind == "meaning":
        d["kw"] = rnd.choice(list(KEYWORDS))
    elif kind == "nhrp":
        _draw_nhrp(d, rnd, form)
    else:
        _draw_phase(d, rnd)
    return d


# ---- syntax ----------------------------------------------------------------
def _syntax_choices(d, rnd, n_total, n_true=None):
    opts, _ = SYNTAX[d["cmd"]]
    want = list(opts)
    if n_true is None:
        n_true = len(want)
    if n_true > len(want):
        raise ValueError("syntax: 正解が足りない")
    trues = rnd.sample(want, n_true)
    norm_want = {_norm(o) for o in want}
    pool = [v for v in VOCAB if v not in norm_want and not any(v == _norm(o) for o in want)]
    # ★同じ語が正解集合の一部(例: multicast)と衝突しないよう、正解の語を含む複合語も外す
    pool = [v for v in pool if not any(w in v.split() for w in norm_want)]
    falses = rnd.sample(pool, n_total - n_true)
    c = [(t, True, "") for t in trues]
    for f in falses:
        c.append((f, False, VOCAB_WHY.get(f, f"{f} は、このコマンドの後続語として実機の `?` に現れない(別のコマンドの語)。")))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_select2(d, rnd):
    if d["kind"] == "syntax":
        opts, _ = SYNTAX[d["cmd"]]
        if len(opts) < 2:
            raise ValueError("syntax: select2 は正解が 2 つ要る")
        return _syntax_choices(d, rnd, n_total=5, n_true=2)
    if d["kind"] == "meaning":
        return _fact_choices(d, rnd, n_true=2, n_total=5)
    raise ValueError("phase に select2 は無い")


def build_choices_allthat(d, rnd):
    if d["kind"] == "syntax":
        opts, _ = SYNTAX[d["cmd"]]
        n_true = min(len(opts), rnd.choice([1, 2, 2, 3, 3, 4]))
        return _syntax_choices(d, rnd, n_total=5, n_true=n_true)
    if d["kind"] == "meaning":
        n_true = min(rnd.choice([1, 2, 2, 3]), sum(1 for _, tv, _ in FACTS[d["kw"]] if tv))
        return _fact_choices(d, rnd, n_true=n_true, n_total=5, offscope=(n_true <= 2))
    raise ValueError("phase に allthat は無い")


# ---- meaning ---------------------------------------------------------------
def _fact_choices(d, rnd, n_true, n_total, offscope=True):
    kw = d["kw"]
    pool_t = [(t, w) for t, tv, w in FACTS[kw] if tv]
    pool_f = [(t, w) for t, tv, w in FACTS[kw] if not tv]
    if len(pool_t) < n_true:
        raise ValueError("meaning: 真の肢が足りない")
    c = [(t, True, "") for t, _ in rnd.sample(pool_t, n_true)]
    n_false = n_total - n_true
    if offscope and n_false >= 3:
        others = [k for k in KEYWORDS if k != kw]
        cand = [(t, k) for k in others for t, tv, w in FACTS[k] if tv]
        t, k = rnd.choice(cand)
        c.append((t, False, f"記述そのものは {KEYWORDS[k]} については正しいが、設問({KEYWORDS[kw]})についての記述ではない。"))
        n_false -= 1
    if len(pool_f) < n_false:
        raise ValueError("meaning: 偽の肢が足りない")
    for t, w in rnd.sample(pool_f, n_false):
        c.append((t, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_select(d, rnd):
    if d["kind"] == "meaning":
        return _fact_choices(d, rnd, n_true=1, n_total=4)
    raise ValueError("select は meaning のみ")


def build_match(d, rnd):
    items = rnd.sample(MATCH_SET, 4)
    terms = [("①②③④"[i], KEYWORDS[k]) for i, (k, _) in enumerate(items)]
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
# phase: 小さな真偽関数
#   属性: spoke_mode(p2p|mgre) / redirect(hub) / shortcut(spoke) / igp(eigrp|ospf) /
#         sh(hub split-horizon 無効=True) / nhs(hub next-hop-self 無効=True) / ospf_type(broadcast|p2mp) / summary(hub 集約)
# ==========================================================================
def phase_of(a):
    if a["spoke_mode"] == "p2p":
        return 1
    if a["redirect"] and a["shortcut"]:
        return 3
    return 2


def spoke_routes_present(a):
    """スポークが他スポークの LAN 経路を持つか(EIGRP はハブの split-horizon 解除が要る)。"""
    if a["igp"] == "eigrp":
        return a["sh"]
    return True


def direct_ok(a):
    """スポーク間の直接通信(ハブを経由しない)が成立するか。"""
    if not spoke_routes_present(a):
        return False
    ph = phase_of(a)
    if ph == 1:
        return False
    if ph == 3:
        return True
    # phase 2: next-hop が相手スポークのまま届くこと
    if a["summary"]:
        return False
    if a["igp"] == "eigrp":
        return a["nhs"]
    return a["ospf_type"] == "broadcast"


FAULTS = ["nhs_on", "sh_on", "p2mp", "summary_p2", "no_shortcut", "no_redirect", "spoke_p2p"]


def _draw_phase(d, rnd):
    fault = rnd.choice(FAULTS)          # ★盤面は常に 1 つ壊れている(read/cause/fix が全て成立する)
    a = {"spoke_mode": "mgre", "redirect": False, "shortcut": False, "igp": rnd.choice(["eigrp", "ospf"]),
         "sh": True, "nhs": True, "ospf_type": "broadcast", "summary": False}
    intent = 2
    if fault in ("healthy3", "no_shortcut", "no_redirect", "summary_p2"):
        intent = 3 if fault != "summary_p2" else 2
    if fault == "nhs_on":
        a["igp"] = "eigrp"; a["nhs"] = False
    elif fault == "sh_on":
        a["igp"] = "eigrp"; a["sh"] = False
    elif fault == "p2mp":
        a["igp"] = "ospf"; a["ospf_type"] = "p2mp"
    elif fault == "summary_p2":
        a["summary"] = True
    elif fault == "no_shortcut":
        a["redirect"] = True; a["shortcut"] = False
    elif fault == "no_redirect":
        a["redirect"] = False; a["shortcut"] = True
    elif fault == "spoke_p2p":
        a["spoke_mode"] = "p2p"
    elif fault == "healthy3":
        a["redirect"] = True; a["shortcut"] = True; a["summary"] = rnd.choice([True, False])
    d["attr"], d["fault"], d["intent"] = a, fault, intent
    d["tun"] = rnd.choice(["Tunnel0", "Tunnel100", "Tunnel1"])
    d["tnet"] = rnd.choice(["10.0.0", "172.16.100", "192.168.255"])
    d["nbma_hub"] = rnd.choice(["203.0.113.1", "198.51.100.1", "192.0.2.1"])
    d["as"] = rnd.choice([1, 100, 65000])
    d["lan1"], d["lan2"] = rnd.choice([("10.1.1.0/24", "10.1.2.0/24"), ("172.16.1.0/24", "172.16.2.0/24"), ("192.168.10.0/24", "192.168.20.0/24")])


def hub_cfg(d):
    a = d["attr"]
    L = [f"interface {d['tun']}", f" ip address {d['tnet']}.1 255.255.255.0", " ip nhrp authentication DMVPN01",
         " ip nhrp map multicast dynamic", " ip nhrp network-id 1"]
    if a["redirect"]:
        L.append(" ip nhrp redirect")
    if a["igp"] == "eigrp":
        if a["sh"]:
            L.append(f" no ip split-horizon eigrp {d['as']}")
        if a["nhs"]:
            L.append(f" no ip next-hop-self eigrp {d['as']}")
        if a["summary"]:
            L.append(f" ip summary-address eigrp {d['as']} {d['lan1'].rsplit('.', 2)[0]}.0.0 255.255.0.0")
    else:
        L.append(" ip ospf network " + ("broadcast" if a["ospf_type"] == "broadcast" else "point-to-multipoint"))
        if a["ospf_type"] == "broadcast":
            L.append(" ip ospf priority 255")
    L += [" tunnel source GigabitEthernet0/0", " tunnel mode gre multipoint", " tunnel key 100"]
    if a["igp"] == "eigrp":
        L += ["!", f"router eigrp {d['as']}", f" network {d['tnet']}.0 0.0.0.255", " network 10.0.0.0"]
    else:
        L += ["!", "router ospf 1", f" network {d['tnet']}.0 0.0.0.255 area 0"]
    return "\n".join(L)


def spoke_cfg(d, name):
    a = d["attr"]
    L = [f"interface {d['tun']}", f" ip address {d['tnet']}.{2 if name == d['s1'] else 3} 255.255.255.0", " ip nhrp authentication DMVPN01",
         f" ip nhrp nhs {d['tnet']}.1 nbma {d['nbma_hub']} multicast", " ip nhrp network-id 1"]
    if a["shortcut"]:
        L.append(" ip nhrp shortcut")
    if a["igp"] == "ospf":
        L.append(" ip ospf network " + ("broadcast" if a["ospf_type"] == "broadcast" else "point-to-multipoint"))
        if a["ospf_type"] == "broadcast":
            L.append(" ip ospf priority 0")
    L.append(" tunnel source GigabitEthernet0/0")
    if a["spoke_mode"] == "p2p":
        L.append(f" tunnel destination {d['nbma_hub']}")
    else:
        L.append(" tunnel mode gre multipoint")
    L.append(" tunnel key 100")
    return "\n".join(L)


def phase_exhibit(d):
    return (f"{d['hub']}# show running-config | section interface {d['tun']}|router\n{hub_cfg(d)}\n\n"
            f"{d['s1']}# show running-config | section interface {d['tun']}\n{spoke_cfg(d, d['s1'])}\n\n"
            f"({d['s2']} は {d['s1']} と同じ構成で、トンネル IP は {d['tnet']}.3 です)")


def _phase_pool(d):
    a = d["attr"]
    ph = phase_of(a)
    hub, s1, s2 = d["hub"], d["s1"], d["s2"]
    routes = spoke_routes_present(a)
    direct = direct_ok(a)
    P = [
        (f"この構成は DMVPN フェーズ {ph} である。", True, ""),
        (f"この構成は DMVPN フェーズ {1 if ph != 1 else 2} である。", False, f"スポークが{'p2p GRE' if ph == 1 else 'mGRE'}で redirect/shortcut が{'両方ある' if ph == 3 else '揃っていない'}ので、フェーズ {ph} である。"),
        (f"{s1} は {s2} の LAN({d['lan2']})への経路を学習する。", routes, f"ハブで split-horizon が有効なままなので、{s1} は {s2} の LAN を学習しない。"),
        (f"{s1} から {s2} の LAN への通信は、{hub} を経由せずスポーク間で直接転送される。", direct, _direct_why(d)),
        (f"{s1} から {s2} の LAN への通信は、{hub} を経由して転送される。", routes and not direct, "スポーク間の直接転送が成立する構成である。" if direct else "そもそも経路が無く、通信は成立しない。"),
    ]
    if a["igp"] == "eigrp":
        P.append((f"{s1} が学習する {d['lan2']} の next-hop は {s2} のトンネル IP である。", routes and a["nhs"] and not a["summary"],
                  "ハブで next-hop-self が有効(または集約)であり、next-hop はハブのトンネル IP になる。" if routes else "経路を学習していない。"))
    else:
        P.append((f"{s1} が学習する {d['lan2']} の next-hop は {s2} のトンネル IP である。", a["ospf_type"] == "broadcast" and not a["summary"],
                  "point-to-multipoint ではハブが next-hop になる。"))
    return P


def _direct_why(d):
    a = d["attr"]
    if a["spoke_mode"] == "p2p":
        return "スポークが p2p GRE(フェーズ 1)であり、全通信がハブ経由になる。"
    if not spoke_routes_present(a):
        return "ハブで split-horizon が有効なままで、スポークは相手の経路を持たない。"
    if phase_of(a) == 2:
        if a["summary"]:
            return "フェーズ 2 で集約すると next-hop がハブになり、直接通信は成立しない。"
        if a["igp"] == "eigrp" and not a["nhs"]:
            return "ハブの next-hop-self が有効で、next-hop がハブになる。"
        if a["igp"] == "ospf" and a["ospf_type"] != "broadcast":
            return "point-to-multipoint ではハブが next-hop になる。"
    return ""


def build_choices_read(d, rnd):
    if d["kind"] == "nhrp":
        return _nhrp_read(d, rnd)
    P = _phase_pool(d)
    trues = [(t, w) for t, ok, w in P if ok]
    falses = [(t, w) for t, ok, w in P if not ok]
    if not trues or len(falses) < 3:
        raise ValueError("phase read: 肢が組めない")
    t, _ = rnd.choice(trues)
    c = [(t, True, "")]
    for f, w in rnd.sample(falses, 3):
        c.append((f, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


CAUSE_TEXT = {
    "nhs_on": "{hub} の {tun} で EIGRP の next-hop-self が有効なままであり、スポークが学習する経路の next-hop がハブになっている。",
    "sh_on": "{hub} の {tun} で EIGRP の split-horizon が有効なままであり、スポークが他のスポークの経路を学習していない。",
    "p2mp": "OSPF のネットワーク タイプが point-to-multipoint であり、スポークが学習する経路の next-hop がハブになっている。",
    "summary_p2": "フェーズ 2 の構成でハブが経路を集約しており、スポークが学習する経路の next-hop がハブになっている。",
    "no_shortcut": "スポークに ip nhrp shortcut が無く、ハブからの Redirect を受けても経路を書き換えない。",
    "no_redirect": "{hub} に ip nhrp redirect が無く、スポークへ Redirect が送られない。",
    "spoke_p2p": "スポークのトンネルがポイントツーポイントの GRE(tunnel destination 指定)であり、スポーク間のトンネルを張れない。",
}
FIX_TEXT = {
    "nhs_on": ("{hub}(config-if)# no ip next-hop-self eigrp {as}", True),
    "sh_on": ("{hub}(config-if)# no ip split-horizon eigrp {as}", True),
    "p2mp": ("{hub} と全スポークの {tun} で ip ospf network broadcast を構成し、ハブの ip ospf priority を最大・スポークを 0 にする。", True),
    "summary_p2": ("{hub} に ip nhrp redirect、全スポークに ip nhrp shortcut を構成する(フェーズ 3 にする)。", True),
    "no_shortcut": ("全スポークの {tun} に ip nhrp shortcut を構成する。", True),
    "no_redirect": ("{hub} の {tun} に ip nhrp redirect を構成する。", True),
    "spoke_p2p": ("全スポークの {tun} で tunnel destination を削除し、tunnel mode gre multipoint を構成する。", True),
}
FIX_WRONG = [
    ("{hub}(config-if)# ip nhrp map multicast dynamic", "既に構成されている(マルチキャストのマッピングの問題ではない)。"),
    ("全スポークの {tun} で ip nhrp registration no-unique を構成する。", "NBMA アドレスの変更の許可であり、経路の next-hop や Redirect には関係ない。"),
    ("{hub} の {tun} で tunnel key を変更する。", "tunnel key は全メンバで一致しており、変更すると通信そのものが止まる。"),
    ("全スポークの {tun} で ip nhrp holdtime を長くする。", "キャッシュの保持時間であり、直接通信の成立には関係ない。"),
    ("{hub}(config-if)# ip nhrp shortcut", "shortcut はスポーク側の設定であり、ハブに入れても Redirect は送られない。"),
    ("全スポークの {tun} に ip nhrp redirect を構成する。", "redirect はハブ側(中継する側)の設定である。"),
]


def _fmt(d):
    return dict(hub=d["hub"], s1=d["s1"], s2=d["s2"], tun=d["tun"], **{"as": d["as"]})


def build_choices_cause(d, rnd):
    if d["kind"] == "nhrp":
        return _nhrp_cause(d, rnd)
    f = d["fault"]
    if f.startswith("healthy"):
        raise ValueError("phase cause: 健全な盤面")
    fmt = _fmt(d)
    c = [(CAUSE_TEXT[f].format(**fmt), True, "")]
    others = [k for k in FAULTS if k != f and _cause_applicable(d, k)]
    for k in rnd.sample(others, 3):
        c.append((CAUSE_TEXT[k].format(**fmt), False, _cause_why(d, k)))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _cause_applicable(d, k):
    a = d["attr"]
    if k in ("nhs_on", "sh_on") and a["igp"] != "eigrp":
        return False
    if k == "p2mp" and a["igp"] != "ospf":
        return False
    return True


def _cause_why(d, k):
    a = d["attr"]
    fmt = _fmt(d)
    return {
        "nhs_on": "構成に no ip next-hop-self eigrp があり、next-hop-self は無効である。",
        "sh_on": "構成に no ip split-horizon eigrp があり、split-horizon は無効である。",
        "p2mp": "ネットワーク タイプは broadcast であり、point-to-multipoint ではない。",
        "summary_p2": "ハブに集約(ip summary-address)は無い。",
        "no_shortcut": "スポークに ip nhrp shortcut がある。" if a["shortcut"] else "この構成はフェーズ 2 を意図しており、shortcut の有無は直接通信の条件ではない。",
        "no_redirect": "ハブに ip nhrp redirect がある。" if a["redirect"] else "この構成はフェーズ 2 を意図しており、redirect の有無は直接通信の条件ではない。",
        "spoke_p2p": "スポークのトンネルは tunnel mode gre multipoint であり、p2p ではない。",
    }[k].format(**fmt)


def build_choices_fix(d, rnd):
    if d["kind"] == "nhrp":
        return _nhrp_fix(d, rnd)
    f = d["fault"]
    if f.startswith("healthy"):
        raise ValueError("phase fix: 健全な盤面")
    fmt = _fmt(d)
    t, ok = FIX_TEXT[f]
    c = [(t.format(**fmt), True, "")]
    for w, why in rnd.sample(FIX_WRONG, 3):
        c.append((w.format(**fmt), False, why))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# nhrp: show dmvpn / show ip nhrp / ログ の読解(実測 P7・iol-xe 17.15.1)
#   故障 4(auth/tkey/nhs_ip/nhs_nbma)= read/cause/fix、健全 2(netid/shortcut)= read のみ
# ==========================================================================
NHRP_FAULTS = ["auth", "tkey", "nhs_ip", "nhs_nbma"]
NHRP_READONLY = ["netid", "shortcut"]
DMVPN_LEGEND = ("Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete\n"
                "\tN - NATed, L - Local, X - No Socket\n"
                "\tT1 - Route Installed, T2 - Nexthop-override, B - BGP\n"
                "\tC - CTS Capable, I2 - Temporary\n"
                "\t# Ent --> Number of NHRP entries with same NBMA peer\n"
                "\tNHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting\n"
                "\tUpDn Time --> Up or Down Time for a Tunnel\n"
                "==========================================================================\n")
DMVPN_HDR = (" # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb\n"
             " ----- --------------- --------------- ----- -------- -----")


def _draw_nhrp(d, rnd, form):
    pool = NHRP_FAULTS if form in ("cause", "fix") else NHRP_FAULTS + NHRP_READONLY
    d["fault"] = rnd.choice(pool)
    d["tun"] = rnd.choice(["Tunnel0", "Tunnel1", "Tunnel100"])
    d["tnet"] = f"10.{rnd.choice([255, 254, 200, 250])}.{rnd.randint(0, 99)}"
    d["hub_tip"], d["s1_tip"], d["s2_tip"] = (f"{d['tnet']}.{i}" for i in (1, 2, 3))
    d["hub_nbma"] = f"203.0.113.{rnd.randint(2, 60)}"
    d["s1_nbma"] = f"198.51.100.{rnd.randint(2, 60)}"
    d["s2_nbma"] = f"192.0.2.{rnd.randint(2, 60)}"
    d["hub_wan"] = f"203.0.113.{rnd.randint(70, 120)}"     # ハブの物理 WAN IF(tunnel source ではない)
    a, b = rnd.sample(range(10, 90), 2)
    d["lan1"], d["lan2"] = f"192.168.{a}.0/24", f"192.168.{b}.0/24"
    words = ["HONSHA", "SECNET", "WANSEC", "OVLNET", "BRANCH", "CRYPTD"]
    d["key"] = f"{rnd.choice(words)}{rnd.randint(10, 99)}"
    k = d["key"]
    d["wrong_key"] = k[:-2] + k[-1] + k[-2] if k[-1] != k[-2] else k[:-2] + f"{(int(k[-2:]) + 13) % 100:02d}"
    d["tkey"] = rnd.randint(100, 899)
    d["wrong_tkey"] = d["tkey"] + rnd.choice([1, 10, -1])
    d["netid"] = rnd.randint(1, 99)
    d["wrong_netid"] = (d["netid"] + rnd.randint(1, 50)) % 100 or 100
    d["wrong_tip"] = f"{d['tnet']}.{rnd.choice([11, 22, 254, 10, 100])}"
    d["as"] = rnd.randint(100, 899)
    # ★デコイ: 故障 4 種の cause/fix では 1/2 の確率で network-id も不一致にする(効かない残骸)
    d["netid_decoy"] = d["fault"] in NHRP_FAULTS and rnd.random() < 0.5
    d["up_h"], d["up_m"] = rnd.randint(1, 20), rnd.randint(0, 59)


def _nhrp_hub_cfg(d):
    L = [f"interface {d['tun']}", f" ip address {d['hub_tip']} 255.255.255.0", " no ip redirects", " ip mtu 1400",
         f" ip nhrp authentication {d['key']}", " ip nhrp map multicast dynamic", f" ip nhrp network-id {d['netid']}",
         " ip nhrp redirect", " ip tcp adjust-mss 1360", " tunnel source Loopback0", " tunnel mode gre multipoint",
         f" tunnel key {d['tkey']}", " tunnel protection ipsec profile IPSEC-DMVPN"]
    return "\n".join(L)


def _nhrp_s2_cfg(d):
    f = d["fault"]
    key = d["wrong_key"] if f == "auth" else d["key"]
    tkey = d["wrong_tkey"] if f == "tkey" else d["tkey"]
    netid = d["wrong_netid"] if (f == "netid" or d.get("netid_decoy")) else d["netid"]
    nhs_tip = d["wrong_tip"] if f == "nhs_ip" else d["hub_tip"]
    nhs_nbma = d["hub_wan"] if f == "nhs_nbma" else d["hub_nbma"]
    L = [f"interface {d['tun']}", f" ip address {d['s2_tip']} 255.255.255.0", " no ip redirects", " ip mtu 1400",
         f" ip nhrp authentication {key}", f" ip nhrp network-id {netid}",
         f" ip nhrp nhs {nhs_tip} nbma {nhs_nbma} multicast", " ip nhrp shortcut", " ip tcp adjust-mss 1360",
         " tunnel source Loopback0", " tunnel mode gre multipoint", f" tunnel key {tkey}",
         " tunnel protection ipsec profile IPSEC-DMVPN"]
    return "\n".join(L)


def _t(d, m_off=0):
    m = (d["up_m"] - m_off) % 60
    return f"{d['up_h']:02d}:{m:02d}:{(d['up_m'] * 7) % 60:02d}"


def _nhrp_hub_show(d):
    f = d["fault"]
    rows = [f"     1 {d['s1_nbma']:<15} {d['s1_tip']:>15}    UP {_t(d)}     D"]
    if f == "nhs_ip":
        rows.append(f"     0 {'UNKNOWN':<15} {d['s2_tip']:>15}  NHRP    never    IX")
    if f in ("netid", "shortcut"):
        rows.append(f"     1 {d['s2_nbma']:<15} {d['s2_tip']:>15}    UP {_t(d, 3)}     D")
    n = len([r for r in rows if "  UP " in r]) + (1 if f == "nhs_ip" else 0)
    return (f"{d['hub']}# show dmvpn\n{DMVPN_LEGEND}\nInterface: {d['tun']}, IPv4 NHRP Details \nType:Hub, NHRP Peers:{n}, \n\n"
            f"{DMVPN_HDR}\n" + "\n".join(rows))


def _nhrp_hub_log(d):
    f = d["fault"]
    tun, s2t, s2n, ht, hn = d["tun"], d["s2_tip"], d["s2_nbma"], d["hub_tip"], d["hub_nbma"]
    base = [f"%DMVPN-5-CRYPTO_SS:  {tun}: local address : {hn} remote address : {s2n} socket is UP"]
    if f == "auth":
        base += [f"%DMVPN-3-DMVPN_NHRP_ERROR:  {tun}: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: {ht} NBMA: {hn})"] * 2
    elif f == "nhs_ip":
        base += [f"%DMVPN-3-DMVPN_NHRP_ERROR:  {tun}: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: {ht} NBMA: {hn})",
                 f"%DMVPN-3-DMVPN_NHRP_ERROR:  {tun}: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: {ht} NBMA: {hn})"]
    elif f == "tkey":
        base += [f"%DUAL-5-NBRCHANGE: EIGRP-IPv4 {d['as']}: Neighbor {s2t} ({tun}) is down: holding time expired"]
    elif f == "nhs_nbma":
        base = [f"%DMVPN-5-NHRP_NHC_DOWN: {tun}: Next Hop Client : (Tunnel: {s2t} NBMA: {s2n} ) for (Tunnel: {ht} NBMA: {hn}) is DOWN, Reason: External(NHRP Registration timeout)",
                f"%DUAL-5-NBRCHANGE: EIGRP-IPv4 {d['as']}: Neighbor {s2t} ({tun}) is down: holding time expired"]
    ts = [f"*Sep 18 {d['up_h'] % 24:02d}:{(d['up_m'] + i) % 60:02d}:{(11 * i + 7) % 60:02d}.{(137 * i) % 1000:03d}: " for i in range(len(base))]
    return f"{d['hub']}# show logging | include DMVPN|DUAL\n" + "\n".join(t + b for t, b in zip(ts, base))


def _nhrp_s2_show(d):
    f = d["fault"]
    tun = d["tun"]
    peer_tip = d["wrong_tip"] if f == "nhs_ip" else d["hub_tip"]
    peer_nbma = d["hub_wan"] if f == "nhs_nbma" else d["hub_nbma"]
    state = "IKE" if f == "nhs_nbma" else "NHRP"
    dm = (f"{d['s2']}# show dmvpn\n{DMVPN_LEGEND}\nInterface: {tun}, IPv4 NHRP Details \nType:Spoke, NHRP Peers:1, \n\n{DMVPN_HDR}\n"
          f"     1 {peer_nbma:<15} {peer_tip:>15}  {state:>4} 00:01:1{d['up_m'] % 10}     S")
    nhs = (f"{d['s2']}# show ip nhrp nhs detail\nLegend:\tE=Expecting replies, R=Responding, W=Waiting, D=Dynamic\n{tun}:\n"
           f"{peer_tip}   E  NBMA Address: {peer_nbma} priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 \n"
           f"Pending Registration Requests:\nRegistration Request: Reqid 14, Ret 64  NHS {peer_tip} expired (Tu{tun[6:]})")
    if f == "nhs_nbma":
        ike = (f"{d['s2']}# show crypto ikev2 sa\n IPv4 Crypto IKEv2  SA \n\nTunnel-id Local                 Remote                fvrf/ivrf            Status \n"
               f"1         {d['s2_nbma']}/500        {peer_nbma}/500        none/none            DELETE \n"
               f"      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK\n\n IPv6 Crypto IKEv2  SA \n")
    else:
        ike = (f"{d['s2']}# show crypto ikev2 sa\n IPv4 Crypto IKEv2  SA \n\nTunnel-id Local                 Remote                fvrf/ivrf            Status \n"
               f"1         {d['s2_nbma']}/500        {d['hub_nbma']}/500        none/none            READY  \n"
               f"      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK\n"
               f"      Life/Active Time: 86400/9{d['up_m'] % 10} sec\n\n IPv6 Crypto IKEv2  SA \n")
    return dm + "\n\n" + nhs + "\n\n" + ike


def _nhrp_s1_dmvpn(d):
    tun = d["tun"]
    return (f"{d['s1']}# show dmvpn\n{DMVPN_LEGEND}\nInterface: {tun}, IPv4 NHRP Details \nType:Spoke, NHRP Peers:2, \n\n{DMVPN_HDR}\n"
            f"     1 {d['hub_nbma']:<15} {d['hub_tip']:>15}    UP {_t(d)}     S\n"
            f"     2 {d['s2_nbma']:<15} {d['s2_tip']:>15}    UP 00:00:2{d['up_m'] % 10}   DT1\n"
            f"       {'':<15} {d['s2_tip']:>15}    UP 00:00:2{d['up_m'] % 10}   DT2")


def _nhrp_s1_show_shortcut(d):
    tun = d["tun"]
    dm = _nhrp_s1_dmvpn(d)
    lan2 = d["lan2"]
    nh = (f"{d['s1']}# show ip nhrp\n{d['hub_tip']}/32 via {d['hub_tip']}\n   {tun} created {_t(d)}, never expire \n   Type: static, Flags: used \n   NBMA address: {d['hub_nbma']}\n"
          f"{d['s2_tip']}/32 via {d['s2_tip']}\n   {tun} created 00:00:2{d['up_m'] % 10}, expire 00:09:3{d['up_m'] % 10}\n   Type: dynamic, Flags: router nhop rib \n   NBMA address: {d['s2_nbma']}\n"
          f"{lan2} via {d['s2_tip']}\n   {tun} created 00:00:2{d['up_m'] % 10}, expire 00:09:3{d['up_m'] % 10}\n   Type: dynamic, Flags: router used rib nho \n   NBMA address: {d['s2_nbma']}\n"
          f"{d['lan1']} via {d['s1_tip']}\n   {tun} created 00:00:2{d['up_m'] % 10}, expire 00:09:3{d['up_m'] % 10}\n   Type: dynamic, Flags: router unique local \n   NBMA address: {d['s1_nbma']}\n    (no-socket)")
    rt = (f"{d['s1']}# show ip route next-hop-override | begin Gateway\nGateway of last resort is {d['s1_nbma'][:-2]}1 to network 0.0.0.0\n\n"
          f"S*    0.0.0.0/0 [1/0] via {d['s1_nbma'][:-2]}1\n"
          f"      10.0.0.0/8 is variably subnetted, 3 subnets, 2 masks\nC        {d['tnet']}.0/24 is directly connected, {tun}\nL        {d['s1_tip']}/32 is directly connected, {tun}\n"
          f"H        {d['s2_tip']}/32 is directly connected, 00:00:2{d['up_m'] % 10}, {tun}\n"
          f"C     {d['lan1']} is directly connected, Loopback1\n"
          f"D   % {lan2} [90/28288000] via {d['hub_tip']}, {_t(d)}, {tun}\n"
          f"                     [NHO][90/255] via {d['s2_tip']}, 00:00:2{d['up_m'] % 10}, {tun}")
    det = (f"{d['s1']}# show ip route {lan2.split('/')[0]}\nRouting entry for {lan2}\n  Known via \"eigrp {d['as']}\", distance 90, metric 28288000, type internal\n  Redistributing via eigrp {d['as']}\n"
           f"  Last update from {d['hub_tip']} on {tun}, {_t(d)} ago\n  Routing Descriptor Blocks:\n  * {d['hub_tip']}, from {d['hub_tip']}, {_t(d)} ago, via {tun}\n      Route metric is 28288000, traffic share count is 1")
    return dm + "\n\n" + nh + "\n\n" + rt + "\n\n" + det


def nhrp_exhibit(d, form):
    f = d["fault"]
    if f == "shortcut":
        return _nhrp_s1_show_shortcut(d)
    parts = []
    if f == "netid" or form == "fix":
        parts += [f"{d['hub']}# show running-config interface {d['tun']}\n{_nhrp_hub_cfg(d)}",
                  f"{d['s2']}# show running-config interface {d['tun']}\n{_nhrp_s2_cfg(d)}"]
    parts.append(_nhrp_hub_show(d))
    if f == "netid":
        parts.append(_nhrp_s1_dmvpn(d))
        return "\n\n".join(parts)
    parts += [_nhrp_hub_log(d), _nhrp_s2_show(d)]
    return "\n\n".join(parts)


def _nhrp_read_pool(d):
    f = d["fault"]
    hub, s1, s2, tun = d["hub"], d["s1"], d["s2"], d["tun"]
    if f == "shortcut":
        return [
            (f"{s1} から {d['lan2']} 宛のトラフィックは、{hub} を経由せず {s2} へ直接転送される。", True, ""),
            (f"show ip route {d['lan2'].split('/')[0]} の詳細では next-hop が {hub} のトンネル アドレスのままだが、転送には {s2} への NHO が使われる。", True, ""),
            (f"{s1} は {s2} の NBMA アドレスを NHRP の解決(Resolution)で動的に学習している。", True, ""),
            (f"{d['s2_tip']}/32 の H の経路は、NHRP によって導入されたホスト経路である。", True, ""),
            (f"DT2 の T2 は、next-hop の上書き(Nexthop-override)を表す。", True, ""),
            (f"{s1} から {d['lan2']} 宛のトラフィックは、{hub} を経由して転送される。", False, "DT2 と [NHO] があり、next-hop は上書きされて " + s2 + " へ直接転送される。"),
            (f"経路の % は、その経路が集約されたことを表す。", False, "% は next hop override(NHO)を表す(凡例)。"),
            (f"DT2 の T2 は、BGP から学習したことを表す。", False, "凡例では T2 - Nexthop-override であり、BGP は B である。"),
            (f"{s1} の {s2} 向けのエントリは、ip nhrp map で静的に構成されている。", False, "Attrb が D(Dynamic)であり、静的(S)ではない。"),
            (f"{s1} は {d['lan2']} を {s2} から EIGRP で直接学習している。", False, "EIGRP の経路の next-hop(via)は " + hub + " のトンネル アドレスであり、直接の経路は NHRP による上書きである。"),
        ]
    if f == "netid":
        return [
            (f"{hub} と {s2} の network-id は一致していないが、{s2} の登録は成立している。", True, ""),
            (f"{s1} と {s2} の間には、スポーク間の直接のトンネル(ショートカット)が成立している。", True, ""),
            (f"ip nhrp network-id は、ルータ内でインターフェイスを NHRP のドメインに関連付ける値であり、対向と一致させる必要はない。", True, ""),
            (f"{s2} は network-id が {hub} と一致するまで登録できない。", False, "show dmvpn では " + s2 + " が UP/D で登録済みである。network-id はローカルに有意である。"),
            (f"{s1} の {s2} 向けのエントリは静的(S)である。", False, "Attrb は DT1/DT2 であり動的である。"),
            (f"{hub} の {s2} 向けのエントリは、ip nhrp map で静的に構成されている。", False, "Attrb は D であり、登録で動的に作られたものである。"),
            (f"network-id を {hub} に合わせるまで、スポーク間の直接通信は成立しない。", False, "DT1/DT2 が既にあり、直接通信は成立している。"),
        ]
    ike_ok = f != "nhs_nbma"
    P = [
        (f"{hub} と {s2} の間の IKEv2 SA は確立している。", ike_ok, "show crypto ikev2 sa に READY が無く(DELETE のみ)、show dmvpn の State も IKE である。"),
        (f"{s2} は、NHRP の登録要求に対する応答を受け取っていない。", True, ""),
        (f"{hub} は {s2} の登録要求を受信し、認証文字列の不一致で拒否している。", f == "auth", "ハブのログに wrong authentication string は無い。" if f != "auth" else ""),
        (f"{hub} には、{s2} からの NHRP パケットが届いていない(または受け入れられていない)。", f in ("tkey", "nhs_nbma"),
         "ハブのログに登録要求の受信(認証エラー / Encap Error)が記録されている。"),
        (f"{s2} は、登録要求を {hub} のトンネル アドレスとは別のアドレス宛に送っている。", f == "nhs_ip", "show dmvpn の Peer Tunnel Add は " + hub + " のトンネル アドレスである。" if f != "nhs_ip" else ""),
        (f"{hub} の show dmvpn には、{s2} に関するエントリが無い。", f != "nhs_ip", "Peer NBMA Addr が UNKNOWN で Attrb IX の不完全なエントリがある。" if f == "nhs_ip" else ""),
        (f"{s2} の show dmvpn の State は NHRP であり、IKE の段階は通過している。", f != "nhs_nbma", "State は IKE であり、IKE の段階で止まっている。" if f == "nhs_nbma" else ""),
        (f"{s2} が IKE の相手にしているアドレスは、{hub} のトンネル送信元アドレスではない。", f == "nhs_nbma",
         "Peer NBMA Addr は " + d["hub_nbma"] + "(ハブのトンネル送信元)である。" if f != "nhs_nbma" else ""),
        (f"{hub} は、{s2} の登録要求を宛先アドレスの不一致によるカプセル化エラーとして処理している。", f == "nhs_ip",
         "ハブのログに NHRP Encap Error は無い。" if f != "nhs_ip" else ""),
    ]
    return P


def _nhrp_read(d, rnd):
    pool = _nhrp_read_pool(d)
    trues = [(t, w) for t, ok, w in pool if ok]
    falses = [(t, w) for t, ok, w in pool if not ok]
    if not trues or len(falses) < 3:
        raise ValueError("nhrp read: 肢が組めない")
    t, _ = rnd.choice(trues)
    c = [(t, True, "")]
    for f_, w in rnd.sample(falses, 3):
        c.append((f_, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


NHRP_CAUSE = {
    "auth": "{s2} の {tun} の ip nhrp authentication の文字列が、{hub} と一致していない。",
    "tkey": "{s2} の {tun} の tunnel key が、{hub} と一致していない。",
    "nhs_ip": "{s2} の ip nhrp nhs で指定している NHS のアドレスが、{hub} のトンネル アドレスではない。",
    "nhs_nbma": "{s2} の ip nhrp nhs で指定している NBMA アドレスが、{hub} のトンネル送信元アドレスではない。",
    "psk": "{s2} と {hub} の IKEv2 の事前共有鍵が一致していない。",
    "netid": "{s2} の ip nhrp network-id が、{hub} と一致していない。",
    "mcast": "{hub} の {tun} に ip nhrp map multicast dynamic が構成されていない。",
    "underlay": "{s2} から {hub} の NBMA アドレスへの到達性が無い。",
    "shortcut": "{s2} の {tun} に ip nhrp shortcut が構成されていない。",
}
NHRP_CAUSE_NEAR = {
    "auth": ["tkey", "nhs_ip", "nhs_nbma", "psk", "netid", "underlay"],
    "tkey": ["auth", "nhs_ip", "nhs_nbma", "psk", "netid", "underlay", "mcast"],
    "nhs_ip": ["auth", "tkey", "nhs_nbma", "psk", "netid", "shortcut"],
    "nhs_nbma": ["psk", "underlay", "auth", "tkey", "netid"],
}


def _nhrp_cause_why(d, k):
    f = d["fault"]
    hub, s2 = d["hub"], d["s2"]
    if k == "auth":
        return f"認証文字列の不一致なら {hub} のログに wrong authentication string が出る。この出力には無い。"
    if k == "tkey":
        if f == "nhs_nbma":
            return "tunnel key の不一致でも IKEv2 SA は確立する(READY)。この出力では IKE の段階で止まっている。"
        return f"tunnel key の不一致では GRE が受け入れられず、{hub} 側に NHRP の痕跡が残らない。この出力では {hub} が登録要求を処理している。"
    if k == "nhs_ip":
        return f"NHS のアドレス誤りなら {hub} の show dmvpn に Attrb IX のエントリと NHRP Encap Error のログが出る。この出力には無い。"
    if k == "nhs_nbma":
        return "NBMA の誤りなら IKE の相手が変わり IKEv2 SA が確立せず、State は IKE になる。この出力では IKEv2 SA は READY で State は NHRP である。"
    if k == "psk":
        if f == "nhs_nbma":
            return f"Peer NBMA Addr が {hub} のトンネル送信元({d['hub_nbma']})ではなく、IKE の相手そのものが誤っている。鍵以前の問題である。"
        return "事前共有鍵の不一致なら IKEv2 SA が確立しない。この出力では READY である。"
    if k == "netid":
        return "network-id はローカルに有意であり、不一致でも登録は成立する(実測)。"
    if k == "mcast":
        return "map multicast dynamic はマルチキャストの複製先の設定であり、ユニキャストの NHRP 登録には関係ない。"
    if k == "underlay":
        if f == "nhs_nbma":
            return f"IKE の相手が {hub} のトンネル送信元ではない({d['hub_wan']})。到達性ではなく宛先の誤りである。"
        return "到達性が無ければ IKEv2 SA が確立しない。この出力では READY である。"
    if k == "shortcut":
        return "shortcut はフェーズ 3 のスポーク間直接通信の設定であり、ハブへの登録には関係ない。"
    return ""


def _nhrp_cause(d, rnd):
    f = d["fault"]
    if f not in NHRP_FAULTS:
        raise ValueError("nhrp cause: 健全な盤面")
    fmt = dict(hub=d["hub"], s1=d["s1"], s2=d["s2"], tun=d["tun"])
    near = list(NHRP_CAUSE_NEAR[f])
    pick = ["netid"] if (d.get("netid_decoy") and "netid" in near) else []
    rest = [k for k in near if k not in pick]
    pick += rnd.sample(rest, 3 - len(pick))
    c = [(NHRP_CAUSE[f].format(**fmt), True, "")]
    for k in pick:
        c.append((NHRP_CAUSE[k].format(**fmt), False, _nhrp_cause_why(d, k)))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _nhrp_fix_ok(d):
    s2, tun = d["s2"], d["tun"]
    return {
        "auth": f"{s2} の {tun} で ip nhrp authentication {d['key']} を構成する。",
        "tkey": f"{s2} の {tun} で tunnel key {d['tkey']} を構成する。",
        "nhs_ip": f"{s2} の {tun} で NHS の指定を ip nhrp nhs {d['hub_tip']} nbma {d['hub_nbma']} multicast に置き換える。",
        "nhs_nbma": f"{s2} の {tun} で NHS の指定を ip nhrp nhs {d['hub_tip']} nbma {d['hub_nbma']} multicast に置き換える。",
    }[d["fault"]]


def _nhrp_fix_wrong(d):
    hub, s2, tun, f = d["hub"], d["s2"], d["tun"], d["fault"]
    W = [
        (f"{s2} の {tun} で ip nhrp network-id {d['netid']} を構成する({hub} と一致させる)。",
         "network-id はローカルに有意であり、一致させても登録の失敗は解消しない(実測)。"),
        (f"{hub} の {tun} で ip nhrp map multicast dynamic を構成する。", "既に構成されている。またマルチキャストの複製先の設定であり、登録には関係ない。"),
        (f"{s2} の {tun} で tunnel protection ipsec profile IPSEC-DMVPN shared を構成する。", "shared は同じ送信元の複数トンネルで同じプロファイルを使うときの指定であり、単一トンネルでは不要である。"),
        (f"{hub} で clear crypto ikev2 sa を実行する。", "IKE の段階は正常(または宛先自体が誤り)であり、SA の再確立では解消しない。"),
        (f"{s2} の {tun} で ip nhrp registration no-unique を構成する。", "no-unique は NBMA アドレスの変更を許す登録オプションであり、登録の失敗の原因ではない。"),
        (f"{hub} の {tun} で ip nhrp redirect を削除する。", "redirect はフェーズ 3 のショートカットの契機であり、登録には関係ない。"),
    ]
    if f != "auth":
        W.append((f"{s2} の {tun} で ip nhrp authentication {d['key']} を構成する。", f"認証文字列は既に {hub} と一致している。"))
    if f != "tkey":
        W.append((f"{s2} の {tun} で tunnel key {d['tkey']} を構成する。", f"tunnel key は既に {hub} と一致している。"))
    if f not in ("nhs_ip", "nhs_nbma"):
        W.append((f"{s2} の {tun} で NHS の指定を ip nhrp nhs {d['hub_tip']} nbma {d['hub_nbma']} multicast に置き換える。", "NHS の指定は既に正しい。"))
    return W


def _nhrp_fix(d, rnd):
    f = d["fault"]
    if f not in NHRP_FAULTS:
        raise ValueError("nhrp fix: 健全な盤面")
    W = _nhrp_fix_wrong(d)
    pick = [W[0]] if d.get("netid_decoy") else []
    rest = [w for w in W if w not in pick]
    pick += rnd.sample(rest, 3 - len(pick))
    c = [(_nhrp_fix_ok(d), True, "")]
    for w, why in pick:
        c.append((w, False, why))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _nhrp_question(d, choices, form):
    f = d["fault"]
    hub, s1, s2 = d["hub"], d["s1"], d["s2"]
    intro = (f"{hub} をハブ、{s1} と {s2} をスポークとする DMVPN(フェーズ 3・IKEv2/IPsec で保護)です。各スポークの LAN は {d['lan1']}({s1})と {d['lan2']}({s2})で、"
             f"EIGRP {d['as']} をトンネル上で動作させています。{hub} のトンネル送信元は Loopback0({d['hub_nbma']})、トンネルのネットワークは {d['tnet']}.0/24 です。")
    if f == "shortcut":
        intro += f" {s1} から {d['lan2']} 宛に通信を行った直後に、{s1} で次の出力を採取しました。"
    elif f == "netid":
        intro += f" 保守担当者が、{s2} の network-id が {hub} と異なることに気づきました。"
    else:
        intro += f" 昨日まで全拠点が正常に通信していましたが、{s2} のトンネル設定を変更した後、{s2} の LAN と他拠点との通信ができなくなりました。{s1} は正常です。"
    before = f"{_dmvpn_mermaid(d, d['hub_nbma'], d['s1_nbma'], d['s2_nbma'])}\n\n{intro}\n\n```\n{nhrp_exhibit(d, form)}\n```"
    if form == "read":
        ask = "この出力について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
    elif form == "cause":
        ask = "この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
    else:
        ask = f"{s2} の登録を回復させるために必要な変更として最も適切なものは、次のうちどれですか。(1つを選択してください)"
    ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    return before, ask, ch_md, ""


SYMPTOM = {
    "nhs_on": "{s1} から {s2} の LAN({lan2})への通信が、常に {hub} を経由して転送されています。",
    "sh_on": "{s1} のルーティング テーブルに {s2} の LAN({lan2})が載っていません。",
    "p2mp": "{s1} から {s2} の LAN({lan2})への通信が、常に {hub} を経由して転送されています。",
    "summary_p2": "{s1} から {s2} の LAN({lan2})への通信が、常に {hub} を経由して転送されています。",
    "no_shortcut": "{s1} から {s2} の LAN({lan2})への通信が、常に {hub} を経由して転送されています。",
    "no_redirect": "{s1} から {s2} の LAN({lan2})への通信が、常に {hub} を経由して転送されています。",
    "spoke_p2p": "{s1} から {s2} の LAN({lan2})への通信が、常に {hub} を経由して転送されています。",
}



def _mmid(name):
    """Mermaid のノード ID(英数字以外は _ に。表示名は label 側に持つ・BL-187)。"""
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", str(name))


def _dmvpn_mermaid(d, hub_nbma, s1_nbma=None, s2_nbma=None):
    """hub-spoke の図(WAN/NBMA 雲を介した 3 拠点・トンネル IP と LAN を併記)。"""
    hub, s1, s2 = d["hub"], d["s1"], d["s2"]
    tun = d["tun"]
    tnet = d.get("tnet")
    hub_t = d.get("hub_tip") or f"{tnet}.1"
    s1_t = d.get("s1_tip") or f"{tnet}.2"
    s2_t = d.get("s2_tip") or f"{tnet}.3"
    def lab(name, nbma, tip, lan=None):
        parts = [name, f"NBMA {nbma}" if nbma else None, f"{tun} {tip}", f"LAN {lan}" if lan else None]
        return "<br/>".join(x for x in parts if x)
    return "\n".join([
        "```mermaid", "graph TB",
        f'  {_mmid(hub)}["{lab(hub, hub_nbma, hub_t)}"]',
        '  WAN(("WAN / NBMA"))',
        f'  {_mmid(s1)}["{lab(s1, s1_nbma, s1_t, d["lan1"])}"]',
        f'  {_mmid(s2)}["{lab(s2, s2_nbma, s2_t, d["lan2"])}"]',
        f"  {_mmid(hub)} --- WAN", f"  WAN --- {_mmid(s1)}", f"  WAN --- {_mmid(s2)}",
        "```"])

def question_body(d, choices, form):
    k = d["kind"]
    if k == "syntax":
        opts, label = SYNTAX[d["cmd"]]
        before = f"トンネル インターフェイスの構成で、`{d['cmd']}` に続けて指定できるオプションを考えます({label})。"
        if form == "select2":
            ask = "指定できるオプションを、次のうちから 2 つ選択してください。"
        else:
            ask = "指定できるオプションを、すべて選んでください。"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    if k == "meaning":
        subject = f"`{KEYWORDS[d['kw']]}`"
        if form == "match":
            terms, ch, _ = choices
            terms_md = "### 対応させる項目\n\n| # | 項目 |\n|---|------|\n" + "\n".join(f"| {kk} | `{t}` |" for kk, t in terms)
            ch_md = "\n\n".join(f"{kk}. {t}" for kk, t in ch)
            return "", "DMVPN の設定について、左側の①〜④のコマンドに対応する説明を、右側の A〜D から選択してください。", ch_md, terms_md
        ask = {"select": f"{subject} について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)",
               "select2": f"{subject} について、正しく述べられているものを、次のうちから 2 つ選択してください。",
               "allthat": f"{subject} について、正しく述べられているものを、すべて選んでください。"}[form]
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return "", ask, ch_md, ""
    if k == "nhrp":
        return _nhrp_question(d, choices, form)
    # phase
    fmt = dict(_fmt(d), lan1=d["lan1"], lan2=d["lan2"])
    intro = (f"{d['hub']} をハブ、{d['s1']} と {d['s2']} をスポークとする DMVPN です。各スポークの LAN は {d['lan1']}({d['s1']})と {d['lan2']}({d['s2']})で、"
             f"{'EIGRP' if d['attr']['igp'] == 'eigrp' else 'OSPF'} をトンネル上で動作させています。")
    before = f"{_dmvpn_mermaid(d, d['nbma_hub'])}\n\n{intro}\n\n```\n{phase_exhibit(d)}\n```"
    if form == "read":
        ask = "この構成について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)"
    elif form == "cause":
        before += "\n\n" + SYMPTOM[d["fault"]].format(**fmt) + (" スポーク間の直接通信を意図した設計です。" if d["intent"] == 2 else " フェーズ 3 のスポーク間直接通信を意図した設計です。")
        ask = "この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
    else:
        before += "\n\n" + SYMPTOM[d["fault"]].format(**fmt) + (" スポーク間の直接通信を成立させます。" if d["intent"] == 2 else " フェーズ 3 のスポーク間直接通信を成立させます。")
        ask = "必要な変更として最も適切なものは、次のうちどれですか。(1つを選択してください)"
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
    if d["kind"] == "phase":
        a = d["attr"]
        lines += ["", f"- 仕込み: `{d['fault']}` / 属性: {a} / フェーズ判定: {phase_of(a)} / 直接通信: {direct_ok(a)}"]
    if d["kind"] == "nhrp":
        lines += ["", f"- 仕込み: `{d['fault']}` / デコイ network-id 不一致: {d.get('netid_decoy')} / 表示は iol-xe 17.15.1 実測(poc/paper-kb P7)"]
    if d["kind"] == "syntax":
        lines += ["", "- 正解集合は iol-xe 17.15.1 の `?` 実測(poc/paper-kb P1)。旧 IOS では registration の後続は no-unique/timeout の 2 つ。"]
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
                "read": build_choices_read, "cause": build_choices_cause, "fix": build_choices_fix}
    # nhrp は kind 内で分岐(build_choices_* が d["kind"] を見る)
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = None
                    for k in range(30):
                        try:
                            dd = draw(_r.Random((hash((kind, form, s)) + k * 11) & 0xFFFFFFFF), kind, None, form)
                            if form == "match":
                                choices = build_match(dd, rnd)
                            else:
                                choices = builders[form](dd, rnd)
                            d = dd
                            break
                        except ValueError:
                            continue
                    assert d is not None, "draw/choices 不成立"
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
    print(f"[gen_paper_dmvpn selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
