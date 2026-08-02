#!/usr/bin/env python3
"""uRPF 紙面MCQ ファミリ (BL-084) — gen_paper_mcq.py の shape=urpf 素材。

BL-027(ENARSI-URPF-01)の PoC 実証済み知見をそのまま紙面へ横展開する
(poc/urpf/README.md・problems/_drafts/URPF-01.design.md):

★1 **偽装 ping の「失敗」を根拠にしてはならない**: 経路の無い送信元は uRPF が
   無くても echo-reply が戻れず 0% → 未設定でも「効いている」ように見える。
   **証拠は per-IF の `verification drops` カウンタ**(`show ip interface`)。
   紙面でもドロップの証拠はカウンタで示し、ping 成否は「正規フローの断」にだけ使う。
★2 **非対称ルーティング下で strict(rx) を入れると正規業務が死ぬ**(loose=any なら通る)。
★3 非対称は**プレフィックス単位**で作る(ip ospf cost では作れない)・OSPF FA 罠あり。

ACL 併用形(`ip verify unicast source reachable-via <mode> <acl>`)は、
ユーザ手組みラボ「uRPF」の形を土台にする。ACL の意味は topologies/acl_model.py
(汎用ACL意味評価器)で機械評価し、「直る候補>=2・要件適合=ちょうど1」を検証する。

論点カタログ(v1・6種):
  strict_on_asym    非対称 IF に rx → 正規業務断(drops が正規フローで増える)
  loose_everywhere  全 IF any → RPF IF 不一致のスプーフが素通り
  acl_num_mismatch  ★uRPF が参照する ACL 番号と、定義されている ACL 番号が違う
  acl_wrong_host    ACL は適用されているが permit するホストが違う
  acl_extended_form 標準ACL のつもりが拡張番号帯・src/dst の取り違え
  missing_on_uplink 片方の IF にだけ適用(もう片方から素通り)
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acl_model  # noqa: E402

URPF_KINDS = ["strict_on_asym", "loose_everywhere", "acl_num_mismatch",
              "acl_wrong_host", "acl_extended_form", "missing_on_uplink"]
# 要件世界: 厳格優先 / 業務継続優先 / 例外は ACL 明示許可のみ
WORLDS = ["host_exception", "net_exception", "no_acl_ops"]
ROLES = ["EDGE", "ISPA", "ISPB"]


def draw(rnd, kind=None, world=None):
    d = {"shape": "urpf"}
    d["kind"] = kind or rnd.choice(URPF_KINDS)
    d["world"] = world or rnd.choice(WORLDS)
    o = rnd.randint(1, 200)
    d["lo_edge"] = f"{rnd.randint(1, 9)}.{rnd.randint(1, 9)}.{rnd.randint(1, 9)}.1"
    d["link_a"] = f"10.{o}.12"          # EDGE-ISPA /30
    d["link_b"] = f"10.{o}.13"          # EDGE-ISPB /30
    d["cust_sym"] = f"192.168.{rnd.randint(1, 99)}"    # 対称・両ISPから対称広告
    d["cust_asym"] = f"192.168.{rnd.randint(100, 199)}"  # ★非対称(広告A/実体B)
    d["spoof"] = f"203.0.113.{rnd.randint(2, 250)}"      # 完全未広告
    # ACL 番号: 標準帯の似た2つ + 拡張帯
    a1 = rnd.choice([1, 5, 7, 10, 15, 20])
    a2 = a1 * 10 if a1 * 10 <= 99 else a1 + 1          # 10 と 100 のような紛らわしさ
    if a2 > 99:
        a2 = a1 + rnd.choice([1, 5])
    d["acl_ok"], d["acl_other"] = a1, a2
    d["acl_ext"] = rnd.choice([101, 110, 120, 130])
    # 例外許可したいホスト(監視サーバ等・非対称網の中の1台)
    d["exc_host"] = f"{d['cust_asym']}.{rnd.randint(10, 99)}"
    d["exc_host2"] = f"{d['cust_asym']}.{rnd.randint(100, 199)}"
    names = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(ROLES, names))
    d["roles"] = list(ROLES)
    verify_choices(d)
    return d


# --------------------------------------------------------------------------
# ACL 定義(acl_model が読める show 形式テキストを作る)
# --------------------------------------------------------------------------
def acl_text(d, num, hosts, extended=False):
    if extended:
        lines = [f"Extended IP access list {num}"]
        for i, h in enumerate(hosts, 1):
            lines.append(f"    {i * 10} permit ip any host {h}")   # ★src/dst 取り違え
    else:
        lines = [f"Standard IP access list {num}"]
        for i, h in enumerate(hosts, 1):
            lines.append(f"    {i * 10} permit {h}")
    return "\n".join(lines)


def acl_permits(text, src):
    """acl_model で「その送信元が permit されるか」を機械評価。"""
    acls = acl_model.parse_show_access_lists(text)
    name = list(acls)[0]
    return acl_model.evaluate(acls[name], {"src": src, "dst": "0.0.0.0",
                                           "proto": "ip"})


# --------------------------------------------------------------------------
# 状態(config)の組み立て
# --------------------------------------------------------------------------
def state(d):
    """現在の構成(紙面に出す事実)を dict で返す。"""
    k = d["kind"]
    st = {"a_mode": "rx", "b_mode": "rx", "a_acl": None, "b_acl": None,
          "acls": [], "b_applied": True}
    exc = [d["exc_host"], d["exc_host2"]]
    if k == "strict_on_asym":
        st["acls"] = []                       # ACL 無し・両IF strict
    elif k == "loose_everywhere":
        st["a_mode"] = st["b_mode"] = "any"
    elif k == "acl_num_mismatch":
        st["b_mode"] = "rx"
        st["b_acl"] = d["acl_ok"]             # 参照は acl_ok
        st["acls"] = [(d["acl_other"], exc, False)]   # 定義は acl_other(番号違い)
    elif k == "acl_wrong_host":
        st["b_acl"] = d["acl_ok"]
        st["acls"] = [(d["acl_ok"], [d["exc_host2"]], False)]  # 許可ホストが違う
    elif k == "acl_extended_form":
        st["b_acl"] = d["acl_ext"]
        st["acls"] = [(d["acl_ext"], exc, True)]      # 拡張帯・any→host(dst側)
    elif k == "missing_on_uplink":
        st["b_applied"] = False                        # ISP-B 側に未適用
    return st


def acl_blocks(d, st):
    return [acl_text(d, num, hosts, ext) for num, hosts, ext in st["acls"]]


# --------------------------------------------------------------------------
# 効果モデル(PoC 実証の挙動をそのまま関数化)
# --------------------------------------------------------------------------
def flow_ok(d, st, flow):
    """正規フローが通るか。flow: 'sym_a'|'sym_b'|'asym'(=非対称・B着信)。
    非対称フローは B 側 IF が rx かつ ACL で許可されていない場合のみ落ちる。"""
    if flow in ("sym_a", "sym_b"):
        return True                            # 対称は strict でも通る
    if not st["b_applied"] or st["b_mode"] == "any":
        return True
    if st["b_acl"] is None:
        return False                           # rx のみ=非対称は落ちる
    # ACL 併用: 参照番号の ACL が定義されていなければ「ACL 無し」と同じ
    defined = {num: (hosts, ext) for num, hosts, ext in st["acls"]}
    if st["b_acl"] not in defined:
        return False
    hosts, ext = defined[st["b_acl"]]
    txt = acl_text(d, st["b_acl"], hosts, ext)
    # ★正規の非対称フローは「例外として届け出られている2台」からのもの
    #   (網全体ではない)。→ ホスト単位 ACL でも網単位 ACL でも復旧しうる=
    #   「直る候補が複数・要件が一意化する」構造が成立する。
    return all(acl_permits(txt, h)
               for h in (d["exc_host"], d["exc_host2"]))


def spoof_dropped(d, st, iface):
    """RPF IF 不一致スプーフが落ちるか(iface='a'|'b')。any でも未広告源は落ちる。
    ★loose(any)は『経路が存在すれば通す』ため、対称網を騙る IF 不一致は素通り。"""
    mode = st["a_mode"] if iface == "a" else st["b_mode"]
    applied = True if iface == "a" else st["b_applied"]
    if not applied:
        return False
    if mode == "any":
        return False                           # 経路はあるので loose は通す
    return True                                # rx なら IF 不一致で落ちる


# --------------------------------------------------------------------------
# 修正候補と要件適合(機械検証)
# ★候補は「最終状態」で定義する(kind は開始状態=何が壊れているかを決めるだけ)。
# --------------------------------------------------------------------------
def fix_candidates(d):
    e = d["m"]["EDGE"]
    h1, h2 = d["exc_host"], d["exc_host2"]
    net = f"{d['cust_asym']}.0"
    return [
        ("acl_host",
         f"{e} の両方のアップリンクのインターフェイスに "
         f"`ip verify unicast source reachable-via rx {d['acl_ok']}` を構成し、"
         f"`access-list {d['acl_ok']} permit {h1}` および "
         f"`access-list {d['acl_ok']} permit {h2}` を定義する"),
        ("acl_net",
         f"{e} の両方のアップリンクのインターフェイスに "
         f"`ip verify unicast source reachable-via rx {d['acl_ok']}` を構成し、"
         f"`access-list {d['acl_ok']} permit {net} 0.0.0.255` を定義する"),
        ("b_any",
         f"{e} の ISP-A 向けを `ip verify unicast source reachable-via rx`、"
         "ISP-B 向けを `ip verify unicast source reachable-via any` に構成する"),
        ("b_rx_only",
         f"{e} の両方のアップリンクのインターフェイスに "
         "`ip verify unicast source reachable-via rx` を構成する"),
        ("b_off",
         f"{e} の ISP-B 向けインターフェイスから、送信元の検証の構成を削除する"),
        ("acl_only",
         f"`access-list {d['acl_ok']} permit {h1}` および "
         f"`access-list {d['acl_ok']} permit {h2}` を定義する"),
    ]


def apply_cand(d, key):
    st = dict(state(d))
    st["acls"] = list(st["acls"])
    h1, h2 = d["exc_host"], d["exc_host2"]
    if key == "acl_host":
        st.update(a_mode="rx", b_mode="rx", b_applied=True,
                  a_acl=d["acl_ok"], b_acl=d["acl_ok"],
                  acls=[(d["acl_ok"], [h1, h2], False)])
    elif key == "acl_net":
        st.update(a_mode="rx", b_mode="rx", b_applied=True,
                  a_acl=d["acl_ok"], b_acl=d["acl_ok"],
                  acls=[(d["acl_ok"], [f"{d['cust_asym']}.0 0.0.0.255"], False)])
    elif key == "b_any":
        st.update(a_mode="rx", b_mode="any", b_applied=True, b_acl=None, acls=[])
    elif key == "b_rx_only":
        st.update(a_mode="rx", b_mode="rx", b_applied=True, b_acl=None, acls=[])
    elif key == "b_off":
        st.update(b_applied=False)
    elif key == "acl_only":
        st["acls"] = st["acls"] + [(d["acl_ok"], [h1, h2], False)]
    return st


def _acl_covers_net(d, st):
    defined = {n: (h, e) for n, h, e in st["acls"]}
    if st["b_acl"] not in defined:
        return False
    hosts, ext = defined[st["b_acl"]]
    txt = acl_text(d, st["b_acl"], hosts, ext)
    probes = [f"{d['cust_asym']}.1", f"{d['cust_asym']}.200"]
    return all(acl_permits(txt, x) for x in probes)


def _flows_ok(d, st):
    return all(flow_ok(d, st, f) for f in ("sym_a", "sym_b", "asym"))


def _works(d, st, world):
    if not _flows_ok(d, st):
        return False
    if world == "no_acl_ops":
        return st["b_applied"]
    return spoof_dropped(d, st, "a") and spoof_dropped(d, st, "b")


def _complies(d, st, world):
    if world == "host_exception":
        return (st["b_mode"] == "rx" and st["b_acl"] is not None
                and not _acl_covers_net(d, st))
    if world == "net_exception":
        return (st["b_mode"] == "rx" and st["b_acl"] is not None
                and _acl_covers_net(d, st))
    return (st["a_mode"] == "rx" and st["b_mode"] == "any"
            and st["b_applied"] and st["b_acl"] is None)


def _sig(d, st):
    """最終状態の意味的シグネチャ(等価な候補を1つに畳むため)。"""
    probes = [d["exc_host"], d["exc_host2"], f"{d['cust_asym']}.1",
              f"{d['cust_asym']}.200"]
    defined = {n: (h, e) for n, h, e in st["acls"]}
    if st["b_acl"] in defined:
        hosts, ext = defined[st["b_acl"]]
        txt = acl_text(d, st["b_acl"], hosts, ext)
        perms = tuple(acl_permits(txt, x) for x in probes)
    else:
        perms = None
    return (st["a_mode"], st["b_mode"], st["b_applied"],
            st["b_acl"] is not None, perms)


def live_candidates(d):
    """意味的に重複する候補を畳んだ提示用リスト(先勝ち)。"""
    seen, out = set(), []
    for key, txt in fix_candidates(d):
        sig = _sig(d, apply_cand(d, key))
        if sig in seen:
            continue
        seen.add(sig)
        out.append((key, txt))
    return out


def verify_choices(d):
    w = d["world"]
    works, ok = [], []
    for key, _ in live_candidates(d):
        st = apply_cand(d, key)
        if _works(d, st, w):
            works.append(key)
            if _complies(d, st, w):
                ok.append(key)
    if len(ok) != 1:
        raise ValueError(f"urpf 一意性違反: kind={d['kind']} world={w} "
                         f"works={works} ok={ok}")
    if len(works) < 2:
        raise ValueError(f"urpf 直る候補不足: kind={d['kind']} world={w} works={works}")
    d["_correct_key"] = ok[0]
    d["_works"] = works


WHY = {
    "acl_host": "", "acl_net": "", "b_any": "",
    "b_rx_only": "非対称に広告されているところのネットワークからの正規のトラフィックが、"
                 "検証によって破棄される。",
    "b_off": "当該インターフェイスにおける送信元の検証が、行われなくなる。",
    "acl_only": "アクセス・リストが定義されるのみであり、"
                "インターフェイスの検証の構成からは参照されない。",
}
WHY_BY_WORLD = {
    "host_exception": {
        "acl_net": "例外がネットワーク単位で許可されており、個々のホストに限定する"
                   "という要件に適合しない。",
        "b_any": "着信インターフェイスの一致が要求されなくなり、アクセス・リストによる"
                 "明示の許可という要件に適合しない。"},
    "net_exception": {
        "acl_host": "例外が個々のホストに限定されており、当該ネットワーク単位で許可する"
                    "という要件に適合しない。",
        "b_any": "着信インターフェイスの一致が要求されなくなり、アクセス・リストによる"
                 "明示の許可という要件に適合しない。"},
    "no_acl_ops": {
        "acl_host": "例外のリストの運用を行わないという要件に適合しない。",
        "acl_net": "例外のリストの運用を行わないという要件に適合しない。"},
}


def _why(d, key):
    return WHY_BY_WORLD[d["world"]].get(key) or WHY[key]


def build_choices_fix(d, rnd):
    correct = d["_correct_key"]
    c = [(txt, key == correct, "" if key == correct else _why(d, key))
         for key, txt in live_candidates(d)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


CLAIMS = {
    "strict_on_asym": "ISP-B 向けインターフェイスの検証モードが、"
                      "非対称に広告されているネットワークに対して厳格すぎる",
    "loose_everywhere": "両方のインターフェイスの検証モードが、"
                        "着信インターフェイスの一致を要求していない",
    "acl_num_mismatch": "検証の構成が参照しているアクセス・リストの番号と、"
                        "定義されているアクセス・リストの番号とが一致していない",
    "acl_wrong_host": "アクセス・リストにおいて許可されているホストが、"
                      "対象のホストと異なっている",
    "acl_extended_form": "アクセス・リストが拡張の番号帯で定義され、"
                         "送信元ではなく宛先に一致している",
    "missing_on_uplink": "ISP-B 向けインターフェイスに検証の構成が適用されていない",
}
REFUTES = {
    "strict_on_asym": "当該インターフェイスの検証モードは示されているとおりである。",
    "loose_everywhere": "示されている構成では、着信インターフェイスの一致が"
                        "要求されている。",
    "acl_num_mismatch": "参照されている番号と定義されている番号は一致している。",
    "acl_wrong_host": "アクセス・リストのエントリは対象のホストを許可している。",
    "acl_extended_form": "アクセス・リストは標準の番号帯で定義されている。",
    "missing_on_uplink": "示されている構成のとおり、当該インターフェイスには"
                         "検証の構成が適用されている。",
}
CROSS = [
    ("ISP-B との間のルーティングの隣接関係が確立されていない",
     "示されているルーティング・テーブルに、当該のネイバーからのルートが存在する。"),
    ("エッジのルータに、既定のルートが構成されていない",
     "既定のルートの有無は、示されている事象とは関係しない"
     "(検証のカウンタが増加している)。"),
    ("アクセス・リストが、インターフェイスの in 方向に適用されている",
     "示されている構成に、ip access-group のステートメントは存在しない。"),
]


def build_choices_cause(d, rnd):
    kind = d["kind"]
    others = [k for k in URPF_KINDS if k != kind]
    c = [(CLAIMS[kind], True, "")]
    c += [(CLAIMS[k], False, REFUTES[k]) for k in rnd.sample(others, 3)]
    c += [(t, False, why) for t, why in rnd.sample(CROSS, 2)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]
