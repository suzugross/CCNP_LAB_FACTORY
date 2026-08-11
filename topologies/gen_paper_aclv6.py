#!/usr/bin/env python3
"""IPv6 トラフィック・フィルタ 紙面ファミリ (BL-106 P3) — shape=aclv6 の素材。

設計= problems/_drafts/ACL-PAPER.design.md §9 P3 / 実測= poc/acl/README.md §14。
BL-100 の優先題材 ⑤（3.2.b IPv6 traffic filter）もここで消化する。

★**主題は IPv4 との差分**（実測 §14-5）:
  1. ワイルドカードではなく**プレフィックス長**。IPv4 の癖で書くと**構文エラー**になり
     その行は**入らない**（= 意図した許可が存在しないまま暗黙の拒否で落ちる）
  2. 適用は `ip access-group` ではなく **`ipv6 traffic-filter`**
  3. `show` は `sequence` が**行末**・running-config は**行頭**
  4. **`resequence` が無い**
  5. **空のリストは保持されない**（未定義と同一の状態）
  6. ★★**末尾に暗黙の `permit icmp any any nd-na` / `nd-ns` があり、明示的に
     `deny ipv6 any any` を書くとその暗黙の許可が失われて近隣探索ごと落ちる**
     （実測 §14-2・V7 で確定）。隣接は **INCMP** になり、
     `permit icmp any any nd-ns` / `nd-na` を明示 deny の手前に置けば回復する。
     → 本ファミリ**最大の考えさせポイント**（故障種 `v6_explicit_deny_nd`）。

評価は acl6_model（プレフィックス照合＋first-match）。一致範囲は必ず連続なので
IPv4 の三値キューブ代数（acl_cover）は使わない。

自己検査: `python3 gen_paper_aclv6.py --selftest`
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acl6_model as a6   # noqa: E402

KINDS = [
    "v6_prefix_too_short",   # プレフィックス長が短く、対象外まで許可
    "v6_prefix_too_long",    # 長すぎて対象の一部が漏れる
    "v6_wildcard_habit",     # ★IPv4 の癖でワイルドカードを書き、その行が入っていない
    "v6_undef_ref",          # 未定義（＝空と同一）→ 全許可
    "v6_order_shadow",       # 先行の広い permit が後続の拒否を影にする
    "v6_explicit_deny_nd",   # ★★明示 deny で近隣探索が落ち、隣接が解決できない
]
# 要件世界（select 形で正解を反転させる。IPv4 版と同じ設計＝意味×提示の組）
WORLDS = ["one_line", "exact_no_deny", "exact_min"]
# ★read 形が成立しない故障種＝「フィルタが実質不在で全部素通り」
# ★v6_explicit_deny_nd は**隣接が壊れて全部落ちる**ので read 形の対比が作れない
NO_READ_KINDS = ("v6_undef_ref", "v6_explicit_deny_nd")
ROLES = ["DUT", "UP", "DN"]


def draw(rnd, kind=None, world=None):
    d = {"shape": "aclv6"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["world"] = world or rnd.choice(WORLDS)
    d["role"] = "v6filter"
    site = rnd.randint(0x10, 0xFE)
    d["site"] = site
    # 対象= 連続する3つの /64。★base は**8 境界**に載せる。
    #   /62 が base..base+3、/61 が base..base+7 にちょうど対応し、
    #   除外網を base+5（/61 の中・/62 の外）に置くと **/61 が機械的に失格**になる。
    #   4 境界しか揃えないと base+5 が /61 の外に出て /61 も「直る候補」になり、
    #   one_line の世界で正解が2つになる（IPv4 側と同じ罠）。
    base = rnd.choice([0, 8, 16, 24, 32, 48, 64, 96, 128, 160, 192])
    d["base"] = base
    d["target"] = [base, base + 1, base + 2]
    d["fourth"] = base + 3
    d["fourth_forbidden"] = (d["world"] != "one_line") and rnd.random() < 0.5
    d["outsider"] = base + 5           # /61 の中・/62 の外
    d["faraway"] = 250 if base < 200 else 1
    d["excluded"] = ([d["fourth"]] if d["fourth_forbidden"] else []) \
        + [d["outsider"]]
    d["srv"] = f"2001:DB8:{site:X}:FF::"
    d["srv_host"] = f"2001:DB8:{site:X}:FF::10"
    d["port"] = rnd.choice([22, 80, 443])
    d["acl_name"] = rnd.choice(["V6-EDGE-IN", "V6-CUST-IN", "V6-FILTER-IN"])
    names = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(ROLES, names))
    d["roles"] = list(ROLES)
    verify_select(d)
    return d


def compatible_worlds(_kind):
    return WORLDS


def net6(d, o64, host=""):
    return f"2001:DB8:{d['site']:X}:{o64:X}::{host}"


def _pfx(o64, plen=64):
    return o64, plen


def _ent(d, action, o64, plen, seq, proto="ipv6"):
    return a6.entry(action, proto, src=net6(d, o64), src_len=plen,
                    dst="::", dst_len=0, seq=seq)


def target_entries(d):
    return [_ent(d, "permit", o, 64, (i + 1) * 10)
            for i, o in enumerate(d["target"])]


# --------------------------------------------------------------------------
# select 形（構築系）— 「この範囲を指定するのはどれか」
# ★IPv6 は連続マスクしか無いので、被覆は「プレフィックス長」だけで決まる。
# --------------------------------------------------------------------------
def select_candidates(d):
    b = d["base"]
    name = d["acl_name"]

    def lines(rows):
        return [f"sequence {(i + 1) * 10} {act} ipv6 {net6(d, o)}/{pl} any"
                for i, (act, o, pl) in enumerate(rows)]

    def ents(rows):
        return [_ent(d, act, o, pl, (i + 1) * 10)
                for i, (act, o, pl) in enumerate(rows)]

    cands = [
        ("p62", [("permit", b, 62)]),                       # 1行（4本目も入る）
        ("exact3", [("permit", o, 64) for o in d["target"]]),
        ("deny_first", [("deny", d["fourth"], 64), ("permit", b, 62)]),
        ("p63", [("permit", b, 63)]),                       # 狭い（2本）
        ("p61", [("permit", b, 61)]),                       # 広い（8本）
    ]
    out = [(k, lines(r), ents(r)) for k, r in cands]
    # ★IPv4 の癖でワイルドカードを書いた候補。実機は `% Invalid input` で**拒否**し、
    #   その行は入らない＝何も許可されない（実測 §14-1）。
    out.append(("wildcard",
                [f"sequence 10 permit ipv6 {net6(d, b)}/62 0.0.3.255 any"],
                []))
    return out


def _works(d, ents):
    if not ents:
        return False
    for o in d["target"]:
        if not _passes(ents, d, o):
            return False
    for o in d["excluded"]:
        if _passes(ents, d, o):
            return False
    return True


def _passes(ents, d, o64):
    return a6.evaluate(ents, {"proto": "tcp", "src": net6(d, o64, "5"),
                              "dst": d["srv_host"], "sport": 12345,
                              "dport": d["port"], "icmp_type": None})


def _exact(d, ents):
    """対象3本ちょうどか（連続マスクなので端点の確認で足りる）。"""
    probes = list(d["target"]) + [d["fourth"], d["outsider"], d["faraway"],
                                  d["base"] + 6, d["base"] + 7]
    for o in probes:
        want = o in d["target"]
        if _passes(ents, d, o) != want:
            return False
    return True


def _complies(d, lines, ents):
    w = d["world"]
    if w == "one_line":
        return len(lines) == 1
    if w == "exact_no_deny":
        return _exact(d, ents) and all(" deny " not in l for l in lines)
    if w == "exact_min":
        return _exact(d, ents)
    raise ValueError(w)


def verify_select(d):
    works = [(k, l, e) for k, l, e in select_candidates(d) if _works(d, e)]
    ok = [(k, l, e) for k, l, e in works if _complies(d, l, e)]
    if d["world"] == "exact_min" and len(ok) > 1:
        least = min(len(l) for _k, l, _e in ok)
        ok = [x for x in ok if len(x[1]) == least]
    if len(works) < 2:
        raise ValueError(f"aclv6 select 直る候補不足: kind={d['kind']} "
                         f"world={d['world']} works={[k for k, _, _ in works]}")
    if len(ok) != 1:
        raise ValueError(f"aclv6 select 一意性違反: kind={d['kind']} "
                         f"world={d['world']} ok={[k for k, _, _ in ok]}")
    d["_select_correct"] = ok[0][0]
    d["_select_works"] = [k for k, _, _ in works]
    return d["_select_correct"]


WHY_SELECT = {
    "p62": "対象としていないネットワークまでが、一致の対象に含まれる。",
    "exact3": "エントリが複数の行に分かれている。",
    "deny_first": "拒否のエントリが用いられている。",
    "p63": "対象としているネットワークのうち、一部が一致の対象から外れる。",
    "p61": "対象としていないネットワークまでが、一致の対象に含まれる。",
    "wildcard": "IPv6 のアクセス・リストにおいては、ワイルドカードによる指定は"
                "受理されない。",
}


def build_choices_select(d, rnd):
    correct = d["_select_correct"]
    out = []
    for key, lines, ents in select_candidates(d):
        why = "" if key == correct else WHY_SELECT[key]
        if key != correct and key in d["_select_works"]:
            why = {"one_line": "エントリが1行に収まっていない。",
                   "exact_no_deny": ("拒否のエントリが用いられている。"
                                     if any(" deny " in l for l in lines)
                                     else "対象としていないネットワークまでが"
                                          "一致の対象に含まれる。"),
                   "exact_min": "より少ない行数で同じ結果が得られる。",
                   }[d["world"]]
        out.append(("\n".join(lines), key == correct, why, lines))
    order = list(range(len(out)))
    rnd.shuffle(order)
    return [out[i] for i in order]


# --------------------------------------------------------------------------
# 現在状態（故障している ACL）
# --------------------------------------------------------------------------
def current_entries(d):
    """(entries, 名前)。entries が None は「未定義（＝空と同一）」。"""
    b, k = d["base"], d["kind"]
    if k == "v6_prefix_too_short":
        return [_ent(d, "permit", b, 61, 10)], d["acl_name"]
    if k == "v6_prefix_too_long":
        return [_ent(d, "permit", b, 63, 10)], d["acl_name"]
    if k == "v6_wildcard_habit":
        # ★1行目は入ったが、2行目はワイルドカード表記で**拒否され存在しない**
        #   （実測 §14-1）。結果、対象の残り2本は暗黙の拒否で落ちる。
        return [_ent(d, "permit", d["target"][0], 64, 10)], d["acl_name"]
    if k == "v6_undef_ref":
        return None, d["acl_name"]
    if k == "v6_order_shadow":
        return ([_ent(d, "permit", b, 61, 10),
                 _ent(d, "deny", d["outsider"], 64, 20)], d["acl_name"])
    if k == "v6_explicit_deny_nd":
        # ★一見「正しく書けている」ACL。業務トラフィックは permit されており、
        #   末尾の明示 deny も「暗黙 deny と同じだから無害」に見える。
        #   実際には**暗黙の nd-na / nd-ns 許可が失われ**、隣接が解決できなくなる。
        return ([_ent(d, "permit", b, 62, 10),
                 a6.entry("deny", "ipv6", "::", 0, "::", 0, seq=20)],
                d["acl_name"])
    raise ValueError(k)


def nd_broken(d):
    """★近隣探索が落ちているか（＝隣接が解決できず、事実上すべて到達不能）。

    実測 §14-2= 明示の `deny ipv6 any any` があると暗黙の nd-na / nd-ns 許可が
    失われる。手前に ND を明示許可していれば回復する。
    """
    ents, _n = current_entries(d)
    if not ents:
        return False
    return not a6.nd_survives(ents)


def flow_passes(d, o64):
    ents, _n = current_entries(d)
    if ents is None:
        return True                    # ★未定義＝全許可（実測 §14-3）
    if nd_broken(d):
        return False                   # 隣接が解決できないので、実際には届かない
    return _passes(ents, d, o64)


def show_text(d):
    """`show ipv6 access-list <name>`（★sequence は**行末**・実測 §14-1）。"""
    ents, name = current_entries(d)
    if ents is None:
        return ""                      # 未定義は何も出ない
    out = [f"IPv6 access list {name}"]
    for e in ents:
        out.append("    " + a6.render_entry(e))
    return "\n".join(out)


def config_text(d):
    """`show running-config | section ipv6 access-list`（★sequence は**行頭**）。"""
    ents, name = current_entries(d)
    if ents is None:
        return ""
    out = [f"ipv6 access-list {name}"]
    for e in ents:
        body = a6.render_entry(e)
        body = body.rsplit(" sequence ", 1)[0]
        out.append(f" sequence {e['seq']} {body}")
    return "\n".join(out)


# --------------------------------------------------------------------------
# read / counter / cause
# --------------------------------------------------------------------------
def neighbor_text(d):
    """`show ipv6 neighbors <onlink>`。★隣接が壊れると **INCMP / Link-layer が `-`**
    になる（実測 §14-2 V7）。これが故障の指紋になる。"""
    onlink = net6(d, d["target"][0], "3")
    hdr = ("IPv6 Address                              Age Link-layer Addr "
           "State Interface")
    if nd_broken(d):
        row = f"{onlink:<42}  0 -               INCMP Et0/0"
    else:
        row = f"{onlink:<42}  0 aabb.cc02.4f00  REACH Et0/0"
    return f"{hdr}\n{row}"


def read_items(d):
    probes = list(d["target"]) + [d["fourth"], d["outsider"], d["faraway"]]
    return [(f"送信元が {net6(d, o)}/64 のネットワークにあるホストから、"
             f"{d['srv_host']} の TCP ポート {d['port']} 宛ての通信",
             flow_passes(d, o)) for o in probes]


def read_polarity(d):
    items = read_items(d)
    t = sum(1 for _x, ok in items if ok)
    if t == 0 or t == len(items):
        return None
    return "pass" if t <= len(items) - t else "block"


def build_choices_read(d, rnd, want=1):
    pol = read_polarity(d)
    if pol is None:
        raise ValueError("aclv6 read: 一方しか無く設問が成立しない")
    items = read_items(d)
    hit = [t for t, ok in items if (ok if pol == "pass" else not ok)]
    miss = [t for t, ok in items if (ok if pol != "pass" else not ok)]
    if len(hit) < want or len(miss) < 2:
        raise ValueError("aclv6 read: 選択肢が足りない")
    rnd.shuffle(hit)
    rnd.shuffle(miss)
    why = ("示されているアクセス・リストでは、これは一致の対象とならない。"
           if pol == "pass" else "示されているアクセス・リストでは、これは許可される。")
    c = [(t, True, "") for t in hit[:want]]
    c += [(t, False, why) for t in miss[:max(5 - want, 2)]]
    order = list(range(len(c)))
    rnd.shuffle(order)
    d["_read_polarity"] = pol
    d["_read_want"] = want
    return [c[i] for i in order]


def counter_probe(d):
    ents, _n = current_entries(d)
    if not ents or len(ents) < 2:
        return None
    for o in list(d["target"]) + [d["fourth"], d["outsider"]]:
        v = {"proto": "tcp", "src": net6(d, o, "5"), "dst": d["srv_host"],
             "sport": 12345, "dport": d["port"], "icmp_type": None}
        hits = [i for i, e in enumerate(ents) if a6.entry_matches(e, v)]
        if len(hits) >= 2:
            return {"text": f"送信元が {net6(d, o, '5')} である1つのパケット",
                    "hits": hits, "first": hits[0]}
    return None


def build_choices_counter(d, rnd):
    p = counter_probe(d)
    if p is None:
        raise ValueError("aclv6 counter: 複数行に一致する観測が無い")
    ents, _n = current_entries(d)
    d["_counter_probe"] = p
    c = []
    for i, e in enumerate(ents):
        txt = f"`{a6.render_entry(e)}` の行"
        if i == p["first"]:
            c.append((txt, True, ""))
        elif i in p["hits"]:
            c.append((txt, False, "先行する行で一致が確定しているため、"
                                  "この行は評価されない。"))
        else:
            c.append((txt, False, "この行は当該のパケットに一致しない。"))
    c.append(("いずれの行のカウンタも増加しない(暗黙の拒否によって処理される)",
              False, "暗黙の拒否にはカウンタが存在しないが、"
                     "本件は明示された行に一致している。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


CLAIMS = {
    "v6_prefix_too_short": "プレフィックスの長さが短く、"
                           "対象としていないネットワークまでが一致の対象に含まれている",
    "v6_prefix_too_long": "プレフィックスの長さが長く、"
                          "対象としているネットワークの一部が一致の対象から外れている",
    "v6_wildcard_habit": "ワイルドカードによる指定が受理されず、"
                         "意図されたエントリが存在していない",
    "v6_undef_ref": "参照されているアクセス・リストが定義されていない",
    "v6_order_shadow": "先行するエントリが広い範囲を許可しており、"
                       "後続のエントリが評価されない",
    "v6_explicit_deny_nd": "末尾に明示の拒否のエントリが記述されているため、"
                           "近隣探索に対する暗黙の許可が失われ、"
                           "隣接のアドレスが解決できていない",
}
REFUTES = {
    "v6_prefix_too_short": "示されているプレフィックスの長さは、"
                           "対象としている範囲を超えていない。",
    "v6_prefix_too_long": "示されているプレフィックスの長さは、"
                          "対象としているネットワークをすべて含んでいる。",
    "v6_wildcard_habit": "示されているエントリに、ワイルドカードによる指定は存在しない。",
    "v6_undef_ref": "参照されているアクセス・リストは定義されている。",
    "v6_order_shadow": "示されているエントリの順序では、後続のエントリが評価される。",
    "v6_explicit_deny_nd": "示されているエントリに、末尾の明示の拒否は存在しない"
                           "(暗黙の拒否のみであり、近隣探索は影響を受けない)。",
}
# ★実測で**偽**と確定しているもっともらしい誤解（poc/acl §14）。
MISCONCEPTION = [
    ("空のアクセス・リストが参照されているため、暗黙の拒否によって"
     "すべてが破棄されている",
     "IPv6 では、エントリを持たないアクセス・リストは保持されない"
     "(参照しても全許可になる)。"),
    ("シーケンス番号が連続していないため、エントリが評価されていない",
     "シーケンス番号の間隔は、評価の順序にのみ影響し、"
     "評価されるかどうかには影響しない。"),
    ("アクセス・リストが `ip access-group` によって適用されている",
     "示されている構成では、`ipv6 traffic-filter` によって適用されている。"),
    ("インターフェイスにおいて IPv6 が有効にされていない",
     "示されている出力では、当該のインターフェイスに IPv6 アドレスが"
     "構成されている。"),
]


def build_choices_cause(d, rnd):
    kind = d["kind"]
    others = [k for k in KINDS if k != kind and not _also_true(d, k)]
    n_kind = min(3, len(others))
    c = [(CLAIMS[kind], True, "")]
    c += [(CLAIMS[k], False, REFUTES[k]) for k in rnd.sample(others, n_kind)]
    c += [(t, False, why)
          for t, why in rnd.sample(MISCONCEPTION,
                                   min(len(MISCONCEPTION), 5 - n_kind))]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _also_true(d, other):
    ents, _n = current_entries(d)
    if other == "v6_undef_ref":
        return ents is None
    if ents is None:
        return False
    if other == "v6_explicit_deny_nd":
        return nd_broken(d)
    if other == "v6_wildcard_habit":
        return False               # 提示物に現れないので、他の盤面では常に偽
    if other == "v6_prefix_too_short":
        return any(e["src_len"] < 64 and e["action"] == "permit" for e in ents)
    if other == "v6_prefix_too_long":
        return not all(flow_passes(d, o) for o in d["target"])
    if other == "v6_order_shadow":
        return len(ents) >= 2 and _has_shadow(ents)
    return False


def _has_shadow(ents):
    for i, e in enumerate(ents):
        if i == 0:
            continue
        # 先行のいずれかが、この行の範囲を完全に覆っているか
        for prev in ents[:i]:
            if prev["proto"] in ("ipv6", e["proto"]) \
                    and prev["src_len"] <= e["src_len"] \
                    and a6.in_prefix(e["src"], prev["src"], prev["src_len"]):
                return True
    return False


def kind_forms(kind, samples=8):
    """その故障種が**そもそも取り得る**出題形の集合。

    形は盤面ごとに成立可否が変わるので、数個引いて和集合を取る。
    `--forms` 指定時に「その形を持たない種」を選んでしまう事故を防ぐために使う。
    """
    out = set()
    for i in range(samples):
        for w in WORLDS:
            try:
                d = draw(random.Random(i * 131 + 7), kind=kind, world=w)
            except ValueError:
                continue
            out |= set(forms_for(d))
    return out


def forms_for(d):
    forms = ["cause", "select"]
    if d["kind"] not in NO_READ_KINDS and read_polarity(d) is not None:
        forms.append("read")
    if counter_probe(d) is not None:
        forms.append("counter")
    return forms


# --------------------------------------------------------------------------
def _selftest(n=40):
    ok = ng = 0
    fails = []
    for kind in KINDS:
        for world in WORLDS:
            for s in range(n):
                try:
                    draw(random.Random(s * 811 + 17), kind=kind, world=world)
                    ok += 1
                except ValueError as e:
                    ng += 1
                    fails.append(f"{kind}/{world}/{s}: {e}")
    print(f"  select 一意性: OK={ok} NG={ng}")
    for f in fails[:4]:
        print(f"    {f}")

    f_ok = f_ng = 0
    seen = set()
    for kind in KINDS:
        for world in WORLDS:
            for s in range(15):
                rnd = random.Random(s * 37 + 3)
                try:
                    d = draw(rnd, kind=kind, world=world)
                except ValueError:
                    continue
                avail = forms_for(d)
                seen |= set(avail)
                for form, fn in (("select", build_choices_select),
                                 ("read", build_choices_read),
                                 ("counter", build_choices_counter),
                                 ("cause", build_choices_cause)):
                    if form not in avail:
                        continue
                    try:
                        ch = fn(d, rnd)
                        assert sum(1 for _t, c, *_r in ch if c) == 1
                        assert len(ch) >= 3
                        f_ok += 1
                    except (ValueError, AssertionError) as e:
                        f_ng += 1
                        if f_ng < 5:
                            print(f"    {form} NG: {kind}/{world}: {e}")
    print(f"  各形の成立: OK={f_ok} NG={f_ng}")
    missing = {"select", "read", "counter", "cause"} - seen
    if missing:
        print(f"    ★成立しない形: {sorted(missing)}")
        f_ng += 1

    # 実測(poc/acl §14)との整合
    m_ok = m_ng = 0

    def chk(c, label):
        nonlocal m_ok, m_ng
        if c:
            m_ok += 1
        else:
            m_ng += 1
            print(f"    実測不一致: {label}")

    d = draw(random.Random(5), kind="v6_undef_ref", world="one_line")
    chk(all(flow_passes(d, o) for o in
            d["target"] + [d["outsider"], d["faraway"]]),
        "未定義＝全許可(§14-3)")
    chk(show_text(d) == "", "未定義は show に現れない(§14-3)")
    d = draw(random.Random(6), kind="v6_wildcard_habit", world="exact_no_deny")
    chk(flow_passes(d, d["target"][0])
        and not flow_passes(d, d["target"][1]),
        "ワイルドカード行は入らない＝残りは暗黙の拒否(§14-1)")
    # 書式: show は sequence が行末・config は行頭
    d = draw(random.Random(7), kind="v6_order_shadow", world="one_line")
    st = show_text(d).splitlines()[1]
    cf = config_text(d).splitlines()[1]
    chk(st.rstrip().endswith("sequence 10"), "show は sequence が行末(§14-1)")
    chk(cf.strip().startswith("sequence 10"), "config は sequence が行頭(§14-1)")
    # ★ND(実測 §14-2 V7): 暗黙のみ=生きる / 明示 deny=落ちる / 明示許可=回復
    d = draw(random.Random(8), kind="v6_explicit_deny_nd", world="one_line")
    chk(nd_broken(d), "明示 deny で近隣探索が落ちる(V7-b)")
    chk("INCMP" in neighbor_text(d), "隣接表に INCMP が出る(V7-b)")
    chk(not any(flow_passes(d, o) for o in d["target"]),
        "隣接が壊れると業務トラフィックも届かない")
    only_permit = [a6.entry("permit", "ipv6", net6(d, d["base"]), 62, seq=10)]
    chk(a6.nd_survives(only_permit), "暗黙の拒否のみなら近隣探索は生きる(V7-a)")
    rescued = only_permit + [
        a6.entry("permit", "icmp", "::", 0, "::", 0, icmp_type="nd-ns", seq=20),
        a6.entry("permit", "icmp", "::", 0, "::", 0, icmp_type="nd-na", seq=30),
        a6.entry("deny", "ipv6", "::", 0, "::", 0, seq=40)]
    chk(a6.nd_survives(rescued), "ND を明示許可すれば回復する(V7-c)")
    d2 = draw(random.Random(9), kind="v6_order_shadow", world="one_line")
    chk(not nd_broken(d2) and "REACH" in neighbor_text(d2),
        "明示 deny の無い盤面では隣接は正常")
    print(f"  実測との整合: OK={m_ok} NG={m_ng}")

    total = ng + f_ng + m_ng
    print(f"gen_paper_aclv6 selftest: NG合計={total}")
    return total == 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    print(__doc__)
