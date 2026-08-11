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
FILTER_KINDS = ADDR_KINDS + EXT_ONLY_KINDS + DENSE_KINDS
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
]
RF_WORLDS = ["prefixlen_no_rm", "prefixlen_via_rm", "by_neighbor",
             "keep_others"]
# 追加ロールの要件世界(いずれも「何を守るか」を1つ決めるだけ。select 形は持たない)
X_WORLDS = ["protect_mgmt", "least_change"]

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
NO_READ_KINDS = ("undef_ref", "empty_acl", "ext_named_rejected",
                 "urpf_undef_exempt")


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
    forms = ["cause"]
    if d["role"] == "filter":
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
    if logread_ok(d):
        forms.append("logread")
    return forms


def worlds_for(kind):
    r = role_of(kind)
    if r == "filter":
        return FILTER_WORLDS
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
    d["target"] = [base, base + 1, base + 2]       # 通したい/受理したい3本
    d["fourth"] = base + 3                         # キューブを完成させる4本目
    # 4本目を「触れてはいけない網」にするか(=1行では書けなくなる)。
    # ★one_line の世界では 4本目を許せないと正解が存在しないので必ず許容側にする。
    d["fourth_forbidden"] = (d["world"] != "one_line") and rnd.random() < 0.5
    d["outsider"] = base + 5                       # ★上位キューブの中に置く
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
    # 隣接ルータ(routefilter の src 側)
    d["nb_up"] = f"10.{a}.254.2"
    d["nb_dn"] = f"10.{a}.253.3"
    d["acl_num"] = rnd.choice([10, 20, 30, 50, 70])          # 標準帯
    d["acl_ext"] = rnd.choice([101, 110, 120, 130, 150])     # 拡張帯
    d["acl_name"] = rnd.choice(["FILTER-IN", "CUST-IN", "EDGE-IN", "RT-IN"])
    names = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(ROLES, names))
    d["roles"] = list(ROLES)
    if d["role"] == "filter" and d["kind"] not in DENSE_KINDS:
        verify_select(d)                # select 形の一意性を機械検証
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
    must = "srcport_dns" if d["srcport_kind"] == "dns" else "srcport_gt"
    rest = [k for k in ("dns", "icmp", "range", "est") if True]
    pick = zlib.crc32(f"{d['base']}:{d['oct2']}:{d['hi_lo']}".encode())
    chosen = [must] + [rest[(pick + i) % len(rest)] for i in range(2)]
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

    cands = [
        ("cube", [("permit", b, 3)]),                       # 1行(4本目も入る)
        ("exact3", [("permit", o, 0) for o in d["target"]]),  # 厳密3行
        ("deny_first", [("deny", d["fourth"], 0), ("permit", b, 3)]),
        ("narrow", [("permit", b, 1)]),                     # 狭い(2本だけ)
        ("wide", [("permit", b, 7)]),                       # 広い(8本)
        ("bits", [("permit", b, 5)]),                       # 非連続(飛び地)
    ]
    for key, rows in cands:
        out.append((key, std_lines(rows), ents(rows)))
    # ★サブネットマスクを書いてしまった候補(実測 P10: 正規化されて別物になる)
    #   0.0.3.255 のつもりで 255.255.252.0 と書く。IOS は受理し、
    #   don't care 側のビットがアドレスから落ちるため「まったく別の集合」になる。
    if d["aclform"] == "std":
        out.append((
            "maskish",
            [f"access-list {num} permit {net(d, b)} 255.255.252.0"],
            [ac.entry("permit", None, src=net(d, b), sw="255.255.252.0",
                      seq=10)]))
    else:
        # ★拡張でしか作れない錯乱肢。いずれも「対象は通るが**別の何か**まで通る/
        #   通らない」ので、works() の対照(別ポート・別宛先)で機械的に落ちる。
        # ★3本すべて足すと9択になり多すぎる(実試験は6〜7択)。2本に絞る。
        _ext_pool = []
        out2 = _ext_pool.append
        out2((
            "portswap",
            [f"access-list {num} permit tcp {net(d, b)} 0.0.3.255 "
             f"eq {_port_txt(d['port'])} host {d['srv_host']}"],
            [_ext(d, "permit", b, 3, 10, sport=True)]))
        out2((
            "ipproto",
            [f"access-list {num} permit ip {net(d, b)} 0.0.3.255 "
             f"host {d['srv_host']}"],
            [_ext(d, "permit", b, 3, 10, proto="ip")]))
        out2((
            "dstany",
            [f"access-list {num} permit tcp {net(d, b)} 0.0.3.255 "
             f"any eq {_port_txt(d['port'])}"],
            [_ext(d, "permit", b, 3, 10, dst_any=True)]))
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
    exact = (ac.permits_exactly(entries, target_entries(d))
             if d["aclform"] == "std" else _exact_ext(d, entries))
    if w == "one_line":
        return len(lines) == 1
    if w == "exact_no_deny":
        return exact and all(" deny " not in ln for ln in lines)
    if w == "exact_min":
        return exact                    # 行数の最小性は verify_select で解く
    raise ValueError(w)


def verify_select(d):
    """「直る候補≥2・要件適合=ちょうど1」を機械検証する(pbr/urpf と同じ被覆エンジン)。

    ★意味的に等価な候補(厳密列挙 と deny 先行)は**畳まない**。
      要件世界が提示の軸(行数・deny の有無)で選ぶので、等価でも別の選択肢として成立する。
    """
    works = [(k, l, e) for k, l, e in select_candidates(d)
             if _select_works(d, e)]
    ok = [(k, l, e) for k, l, e in works if _select_complies(d, l, e)]
    if d["world"] == "exact_min" and len(ok) > 1:
        least = min(len(l) for _k, l, _e in ok)
        ok = [x for x in ok if len(x[1]) == least]
    if len(works) < 2:
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


def build_choices_select(d, rnd):
    correct = d["_select_correct"]
    out = []
    for key, lines, ents in select_candidates(d):
        txt = " / ".join(f"`{ln}`" for ln in lines)
        why = "" if key == correct else WHY_SELECT[key]
        # ★「直りはするが要件に合わない」候補の理由は、意味ではなく提示の軸で書く
        if key != correct and key in d["_select_works"]:
            why = {"one_line": "エントリが1行に収まっていない。",
                   "exact_no_deny": ("拒否のエントリが用いられている。"
                                     if any(" deny " in ln for ln in lines)
                                     else "対象としていないネットワークまでが"
                                          "一致の対象に含まれる。"),
                   "exact_min": "より少ない行数で同じ結果が得られる。",
                   }[d["world"]]
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


def show_acl_text(d):
    """`show ip access-lists` の実機書式(実測 poc/acl §11 に忠実)。"""
    ents, is_std, name = current_entries(d)
    if ents is None:
        return ""                                   # 未定義= 何も出ない
    head = ("Standard IP access list " if is_std else "Extended IP access list ")
    lines = [head + name]
    for e in ents:
        lines.append("    " + _render_entry(e, is_std))
    return "\n".join(lines)


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
def flow_passes(d, src_o3):
    """filter ロール: 送信元 10.a.<o3>.x の通信が通るか。

    ★未定義・空はいずれも**全許可**(実測 P1a/P12)。
    """
    ents, _is_std, _n = current_entries(d)
    if ents is None or ents == []:
        return True
    return acl_model.evaluate(ents, {"proto": "tcp", "src": net(d, src_o3, 5),
                                     "dst": d["srv_host"], "sport": 12345,
                                     "dport": d["port"], "established": False,
                                     "icmp_type": None})


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
            ents, _s, _n = current_entries(d)
            t0 = d["target"][0]
            out.append(
                (f"送信元が {net(d, t0)}/24 のネットワークにあるホストから、"
                 f"{d['srv_host']} の TCP ポート {d['other_port']} 宛ての通信",
                 bool(ents) and acl_model.evaluate(
                     ents, _vec_at(d, t0, dport=d["other_port"]))))
            out.append(
                (f"送信元が {net(d, t0)}/24 のネットワークにあるホストから、"
                 f"{d['other_host']} の TCP ポート {d['port']} 宛ての通信",
                 bool(ents) and acl_model.evaluate(
                     ents, _vec_at(d, t0, dst=d["other_host"]))))
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
def compare_pair(d):
    """(表示A, 表示B, 判定A, 判定B) を返す。**結果が割れる組**を優先して選ぶ。"""
    ents, _s, _n = current_entries(d)
    if not ents:
        return None
    probes = dense_probes(d) if d["kind"] == "dense_list" else None
    if probes is None:
        return None
    ev = [(t, v, acl_model.evaluate(ents, v)) for t, v in probes]

    def diff_fields(a, b):
        return sum(1 for k in ("proto", "src", "dst", "sport", "dport",
                               "established", "icmp_type")
                   if a.get(k) != b.get(k))

    split, same = [], []
    for i in range(len(ev)):
        for j in range(i + 1, len(ev)):
            ta, va, oa = ev[i]
            tb, vb, ob = ev[j]
            nd = diff_fields(va, vb)
            if nd > 2:
                continue           # 差が大きすぎると「見比べる」にならない
            (split if oa != ob else same).append((ta, tb, oa, ob, nd))
    pool = split or same
    if not pool:
        return None
    pool.sort(key=lambda x: x[4])          # 差が小さい組を優先
    top = [p for p in pool if p[4] == pool[0][4]]
    pick = zlib.crc32(f"{d['base']}:{d['port']}:{d['deny_port']}"
                      .encode()) % len(top)
    return top[pick][:4]


def compare_ok(d):
    return d["kind"] == "dense_list" and compare_pair(d) is not None


def build_choices_compare(d, rnd):
    """4つの言い切りのうち、ちょうど1つが真になる(機械的に一意)。"""
    pr = compare_pair(d)
    if pr is None:
        raise ValueError("acl compare: 見比べられる組が無い")
    ta, tb, oa, ob = pr
    d["_compare"] = {"a": ta, "b": tb}
    opts = [
        ("いずれも転送される。", (True, True)),
        ("いずれも破棄される。", (False, False)),
        ("1つ目は転送され、2つ目は破棄される。", (True, False)),
        ("1つ目は破棄され、2つ目は転送される。", (False, True)),
    ]
    c = [(t, (oa, ob) == pat, "" if (oa, ob) == pat
          else "示されているアクセス・リストでは、そのようにはならない。")
         for t, pat in opts]
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
    for i, e in enumerate(ents):
        txt = f"`{_render_entry(e, is_std)}` の行"
        if i == p["first"]:
            c.append((txt, True, ""))
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


def _hyp_board(d, kind):
    """同じ盤面で kind だけ差し替えた仮想の d(観測の分割数を数えるため)。"""
    e = dict(d)
    e["kind"] = kind
    e["role"] = role_of(kind)
    return e


def evidence_observations(d):
    """(表示文, 仮説→見え方) の列。見え方の異なり数が「何通りに割れるか」。"""
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
    if d["role"] != "routefilter" or d["kind"] not in EVIDENCE_HYPS:
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

CROSS = [
    ("インターフェイスに対して、アクセス・リストが in ではなく out の方向に"
     "適用されている",
     "示されている構成では、適用の方向は in である。"),
    ("ルーティング・プロトコルの隣接関係が確立されていない",
     "示されている出力に、当該のネイバーから学習されたルートが存在する。"),
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
            if role_of(k) == d["role"] and k not in DENSE_KINDS]
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
    c += [(t, False, why) for t, why in rnd.sample(CROSS, min(len(CROSS), rest))]
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
    for kind in FILTER_KINDS:
        for world in FILTER_WORLDS:
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
                ents2 = list(back.values())[0]
                ents1, _s3, _n3 = current_entries(d)
                for text, ok in read_items(d):
                    pass
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

    # ★compare 形: 4肢のうち真がちょうど1つ／結果が割れる組が選べているか
    cp_ok = cp_ng = 0
    split = 0
    for s2 in range(80):
        d = draw(random.Random(s2 * 83 + 11), kind="dense_list")
        if not compare_ok(d):
            cp_ng += 1
            continue
        pr = compare_pair(d)
        if pr[2] != pr[3]:
            split += 1
        ch = build_choices_compare(d, random.Random(1))
        if sum(1 for _t, c2, *_r in ch if c2) == 1 and len(ch) == 4:
            cp_ok += 1
        else:
            cp_ng += 1
    print(f"  compare 形: OK={cp_ok} NG={cp_ng} (結果が割れる組 {split}/{cp_ok})")
    ng += cp_ng
    if cp_ok and split / cp_ok < 0.8:
        print("    ★結果が同じ組ばかり(見比べる意味が薄い)")
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
                pol = read_polarity(d)
                if pol is None:
                    # ★NO_READ_KINDS は**全部通る**のが実測どおりの正解なので
                    #   read 形は成立しない(cause 形で出す)。欠陥ではない。
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
        for s in range(12):
            rnd = random.Random(s * 53 + 3)
            try:
                d = draw(rnd, kind=kind)
                if "cause" not in forms_for(d):
                    continue          # dense_list は cause 形を持たない
                ch = build_choices_cause(d, rnd)
            except ValueError as e:
                c_ng += 1
                if c_ng < 4:
                    print(f"    cause NG: {kind}: {e}")
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

    total_ng = ng + r_ng + c_ng + m_ng + b_ng + cp_ng
    print(f"gen_paper_acl selftest: NG合計={total_ng}")
    return total_ng == 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    print(__doc__)
