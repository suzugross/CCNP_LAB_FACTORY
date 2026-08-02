#!/usr/bin/env python3
"""PBR×ワイルドカードACL 紙面ファミリ (BL-081) — gen_paper_mcq.py の shape=pbr 素材。

雛型=ユーザ手組み「CCNPラボPBR」(HUB が 172.16.x への経路を持たない=PBR 不一致なら
不達、という判定装置)。核は第3オクテットのビット被覆計算。

PoC 知見(2026-08-02 IOL17.15・poc/pbr/README.md):
- match ip address prefix-list は PBR では match 節が無視され全トラフィック一致
- ACL/route-map カウンタは ping 発数どおり温まる(収集は ping→show の順)
- 不一致時は HUB が unreachable 応答(U.U.U / 0 percent)

選択肢設計(ユーザ発案): 「到達性だけなら直る」候補を複数併置し、要件軸
(1エントリ / 厳密一致)だけが正解を一意化する。各候補の被覆集合を計算し
「直る候補>=2・要件適合=ちょうど1」を draw 時に機械検証する。
"""
import random

PBR_KINDS = ["wc_narrow", "wc_wide", "wc_bits", "acl_dir", "rm_no_match",
             "match_plist"]
WORLDS = ["single", "strict"]
ROLES = ["HUB", "DST", "CLA", "CLB"]


# --------------------------------------------------------------------------
# 被覆集合エンジン
# --------------------------------------------------------------------------
def cover(base, wc):
    """第3オクテットのワイルドカード被覆 {o : o&~wc == base&~wc}(0..255)。"""
    fixed = base & ~wc & 0xFF
    return {o for o in range(256) if (o & ~wc & 0xFF) == fixed}


def cube_of(octets):
    """集合を覆う最小キューブ (base, wc)。"""
    a, o = octets[0], octets[0]
    for x in octets[1:]:
        a &= x
        o |= x
    return a, (a ^ o)


def acl_eval(entries, octet):
    """entries=[(action, base, wc)] を先頭一致で評価。既定 deny。"""
    for act, b, w in entries:
        if octet in cover(b, w):
            return act == "permit"
    return False


def acl_result(entries, octets):
    return {o: acl_eval(entries, o) for o in octets}


# --------------------------------------------------------------------------
# 抽選
# --------------------------------------------------------------------------
def draw(rnd, kind=None, world=None):
    d = {"shape": "pbr"}
    d["kind"] = kind or rnd.choice(PBR_KINDS)
    d["world"] = world or rnd.choice(WORLDS)
    base = rnd.choice([0, 32, 64, 96, 128, 160])
    k = rnd.choice([3, 5, 6, 7])
    t1, t2 = base, base + k
    e1 = base + k + 1                      # キューブ直上(数値的には範囲内に見える事も)
    ebits = base + 16                      # 非連続ワイルドカード罠(t1 と1ビット差)
    d.update(base=base, k=k, T=[t1, t2], E=[e1, ebits])
    d["all_nets"] = [t1, t2, e1, ebits]
    # LAN・セグメントの第3オクテット(192.168.X)
    used = set()
    for key in ("lan_a", "lan_b", "seg"):
        while True:
            o = rnd.randint(10, 250)
            if o not in used:
                used.add(o)
                d[key] = o
                break
    d["hub_ip"] = f"192.168.{d['seg']}.1"
    d["dst_ip"] = f"192.168.{d['seg']}.2"
    # 健全 ACL(world 準拠)・故障 ACL
    d["healthy"] = ([("permit", base, k)] if d["world"] == "single"
                    else [("permit", t1, 0), ("permit", t2, 0)])
    wc_n = k & ~(1 << (k.bit_length() - 1))          # 最上位差ビット落ち(7→3 等)
    wb, ww = cube_of([t1, t2, e1])
    d["fault_entries"] = {
        "wc_narrow": [("permit", base, wc_n)],
        "wc_wide": [("permit", wb, ww)],
        "wc_bits": [("permit", base, 16)],
        "acl_dir": d["healthy"],           # 値は正・src/dst を逆に描画
        "rm_no_match": d["healthy"],       # ACL は正・map に match が無い
        "match_plist": d["healthy"],       # ACL は正・map が prefix-list 参照
    }[d["kind"]]
    # 役割→表示名
    names = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(names)
    d["m"] = dict(zip(ROLES, names))
    d["roles"] = list(ROLES)
    verify_choices(d)                      # 一意性の機械検証(失敗なら例外)
    return d


# --------------------------------------------------------------------------
# 選択肢(fix)候補: (key, text生成用データ) → 被覆で機械検証
# --------------------------------------------------------------------------
def _entry_txt(d, act, b, w):
    src = f"192.168.{d['lan_a']}.0 0.0.0.255"
    return f"{act} ip {src} 172.16.{b}.0 0.0.{w}.255"


def _cli_acl(d, entries):
    """ACL 全置換の設定コマンド列(削除→再作成)。"""
    out = ["no ip access-list extended ACL-A", "ip access-list extended ACL-A"]
    src = f"192.168.{d['lan_a']}.0 0.0.0.255"
    for i, (act, b, w) in enumerate(entries, 1):
        out.append(f" {i * 10} {act} ip {src} 172.16.{b}.0 0.0.{w}.255")
    return out


def fix_candidates(d):
    """[(key, entries|None, text, cli)] を返す。entries=None は ACL 以外の操作。"""
    base, k = d["base"], d["k"]
    t1, t2 = d["T"]
    e1 = d["E"][0]
    wb, ww = cube_of([t1, t2, e1])
    wc_n = k & ~(1 << (k.bit_length() - 1))
    single = [("permit", base, k)]
    strict = [("permit", t1, 0), ("permit", t2, 0)]
    deny3 = [("deny", e1, 0), ("permit", wb, ww)]
    cands = [
        ("single", single,
         f"ACL-A を「{_entry_txt(d, 'permit', base, k)}」の1行に置き換える",
         _cli_acl(d, single)),
        ("strict", strict,
         "ACL-A を「" + _entry_txt(d, "permit", t1, 0) + "」"
         f"「{_entry_txt(d, 'permit', t2, 0)}」の2行に置き換える",
         _cli_acl(d, strict)),
        ("deny3", deny3,
         f"ACL-A を「{_entry_txt(d, 'deny', e1, 0)}」"
         f"「{_entry_txt(d, 'permit', wb, ww)}」の2行(deny 先行)に置き換える",
         _cli_acl(d, deny3)),
        ("narrow", [("permit", base, wc_n)],
         f"ACL-A を「{_entry_txt(d, 'permit', base, wc_n)}」の1行に置き換える",
         _cli_acl(d, [("permit", base, wc_n)])),
        ("bits", [("permit", base, 16)],
         f"ACL-A を「{_entry_txt(d, 'permit', base, 16)}」の1行に置き換える",
         _cli_acl(d, [("permit", base, 16)])),
        ("plist", None,
         "MAP-A の match を「match ip address prefix-list PL-A」に変更する"
         f"(PL-A: 172.16.{t1}.0/24 と 172.16.{t2}.0/24 を permit)",
         [f"ip prefix-list PL-A seq 5 permit 172.16.{t1}.0/24",
          f"ip prefix-list PL-A seq 10 permit 172.16.{t2}.0/24",
          "route-map MAP-A permit 10",
          " no match ip address ACL-A",
          " match ip address prefix-list PL-A"]),
        ("addmatch", None,
         "MAP-A の match を「match ip address ACL-A」に設定し直す",
         ["route-map MAP-A permit 10", " match ip address ACL-A"]),
    ]
    # 展開済み故障値と同一の候補は出さない(値故障のみ。acl_dir は向きが違うので
    # 同値でも「正しい向きの書き直し」として意味がある)
    if d["kind"] in ("wc_narrow", "wc_wide", "wc_bits"):
        cands = [(key, e, t, c) for key, e, t, c in cands
                 if e is None or e != d["fault_entries"]]
    return cands


def _fixes(d, key, entries):
    """その候補で「T 全到達 かつ E 非転送」になるか(map 故障は addmatch のみ直せる)。"""
    map_fault = d["kind"] in ("rm_no_match", "match_plist")
    if key == "plist":
        return False                       # match-all 化=E まで転送(PoC 実測)
    if key == "addmatch":
        if d["kind"] == "acl_dir":
            return False                   # ACL が逆向きのままでは何にも一致しない
        # map を ACL 参照へ直す。ACL は現状のまま=map故障なら healthy が生きて直る
        acl = d["healthy"] if map_fault else d["fault_entries"]
        r = acl_result(acl, d["all_nets"])
        return (all(r[t] for t in d["T"]) and not any(r[e] for e in d["E"]))
    if entries is None:
        return False
    if map_fault:
        return False                       # ACL を替えても map が参照しない/無視する
    # ACL 書き換え候補は src/dst を明示するので acl_dir も含めて向きを是正できる
    r = acl_result(entries, d["all_nets"])
    return all(r[t] for t in d["T"]) and not any(r[e] for e in d["E"])


def _complies(d, key, entries):
    """要件軸への適合(fix が前提)。"""
    if key == "addmatch":
        return True                        # ACL は world 準拠のまま(map 故障の正解)
    if entries is None:
        return False
    if d["world"] == "single":
        return len(entries) == 1
    covered = {o for o in range(256) if acl_eval(entries, o)}
    return covered == set(d["T"])          # strict: 対象と完全一致


def verify_choices(d):
    """「直る候補>=2(ACL故障時)・要件適合=ちょうど1」を機械検証。"""
    cands = fix_candidates(d)
    fixers = [k for k, e, _t, _c in cands if _fixes(d, k, e)]
    ok = [k for k, e, _t, _c in cands if _fixes(d, k, e) and _complies(d, k, e)]
    map_fault = d["kind"] in ("rm_no_match", "match_plist")
    if len(ok) != 1:
        raise ValueError(f"pbr 一意性違反: kind={d['kind']} world={d['world']} "
                         f"fixers={fixers} ok={ok}")
    if not map_fault and len(fixers) < 2:
        raise ValueError(f"pbr 直る候補不足: {fixers}")
    d["_correct_key"] = ok[0]
    d["_fixers"] = fixers


# --------------------------------------------------------------------------
# config 描画({{ links[n] }} は build 時に IF 名へ)
# --------------------------------------------------------------------------
def _acl_lines(d, entries, swap=False):
    src = f"192.168.{d['lan_a']}.0 0.0.0.255"
    out = ["ip access-list extended ACL-A"]
    for i, (act, b, w) in enumerate(entries, 1):
        dst = f"172.16.{b}.0 0.0.{w}.255"
        a, z = (dst, src) if swap else (src, dst)
        out.append(f" {i * 10} {act} ip {a} {z}")
    out.append("!")
    return out


def render_node(d, role):
    m = d["m"]
    if role == "HUB":
        out = ["! PAPER-PBR hub",
               "interface {{ links[0] }}",
               f" ip address {d['hub_ip']} 255.255.255.248", " no shutdown", "!",
               "interface {{ links[1] }}",
               f" ip address 192.168.{d['lan_a']}.254 255.255.255.0",
               " ip policy route-map MAP-A", " no shutdown", "!",
               "interface {{ links[2] }}",
               f" ip address 192.168.{d['lan_b']}.254 255.255.255.0",
               " ip policy route-map MAP-B", " no shutdown", "!"]
        out += _acl_lines(d, d["fault_entries"], swap=(d["kind"] == "acl_dir"))
        # 健全なお手本 B(world 準拠・src は LAN-B)
        out.append("ip access-list extended ACL-B")
        for i, (act, b, w) in enumerate(d["healthy"], 1):
            out.append(f" {i * 10} {act} ip 192.168.{d['lan_b']}.0 0.0.0.255 "
                       f"172.16.{b}.0 0.0.{w}.255")
        out.append("!")
        if d["kind"] == "match_plist":
            for i, t in enumerate(d["T"]):
                out.append(f"ip prefix-list PL-A seq {(i + 1) * 5} permit "
                           f"172.16.{t}.0/24")
            out.append("!")
        out.append("route-map MAP-A permit 10")
        if d["kind"] == "rm_no_match":
            pass                            # match 無し=全吸引
        elif d["kind"] == "match_plist":
            out.append(" match ip address prefix-list PL-A")
        else:
            out.append(" match ip address ACL-A")
        out += [f" set ip next-hop {d['dst_ip']}", "!",
                "route-map MAP-B permit 10", " match ip address ACL-B",
                f" set ip next-hop {d['dst_ip']}", "!"]
        return out
    if role == "DST":
        out = ["! PAPER-PBR dest(サービス網ホスト)"]
        for i, o in enumerate(d["all_nets"]):
            out += [f"interface Loopback{i}",
                    f" ip address 172.16.{o}.1 255.255.255.0", "!"]
        out += ["interface {{ links[0] }}",
                f" ip address {d['dst_ip']} 255.255.255.248", " no shutdown", "!",
                f"ip route 192.168.{d['lan_a']}.0 255.255.255.0 {d['hub_ip']}",
                f"ip route 192.168.{d['lan_b']}.0 255.255.255.0 {d['hub_ip']}"]
        return out
    lan = d["lan_a"] if role == "CLA" else d["lan_b"]
    return [f"! PAPER-PBR client {role}",
            "interface {{ links[0] }}",
            f" ip address 192.168.{lan}.1 255.255.255.0", " no shutdown", "!",
            f"ip route 0.0.0.0 0.0.0.0 192.168.{lan}.254"]


def lab_links(d):
    m = d["m"]
    return [{"a": m["HUB"], "a_if": 0, "b": m["DST"], "b_if": 0},
            {"a": m["HUB"], "a_if": 1, "b": m["CLA"], "b_if": 0},
            {"a": m["HUB"], "a_if": 2, "b": m["CLB"], "b_if": 0}]


# --------------------------------------------------------------------------
# 証拠セット(ping 温め→show の順)
# --------------------------------------------------------------------------
def evidence_plan(d, rnd):
    m = d["m"]
    checks = []
    for o in d["all_nets"]:
        checks.append({"node": m["CLA"], "command": f"ping 172.16.{o}.1 repeat 5"})
    for o in (d["T"][1], d["E"][0]):       # 対比: 健全側は t2 成功 / e1 不達
        checks.append({"node": m["CLB"], "command": f"ping 172.16.{o}.1 repeat 5"})
    checks += [{"node": m["HUB"], "command": "show route-map"},
               {"node": m["HUB"], "command": "show access-lists"},
               {"node": m["HUB"], "command": "show ip prefix-list",
                "optional": True},
               {"node": m["HUB"], "command": "show running-config | section interface"},
               {"node": m["HUB"],
                "command": "show running-config | section route-map|access-list"}]
    for r in ("DST", "CLA", "CLB"):
        checks.append({"node": m[r],
                       "command": "show running-config | section interface|ip route"})
    return {"checks": checks}


# --------------------------------------------------------------------------
# 選択肢
# --------------------------------------------------------------------------
WHY_FIX = {
    "single": "1エントリ要件の世界での正解。厳密一致の世界では過剰マッチで不適合。",
    "strict": "厳密一致の世界での正解。1エントリ要件の世界では行数超過で不適合。",
    "deny3": "到達性は直るが、permit 側の被覆が対象外を含み(かつ複数行)、"
             "どちらの要件世界でも不適合。",
    "narrow": "対象の一部がワイルドカードの被覆から外れており、到達性が直らない。",
    "bits": "非連続ワイルドカードにより対象外(+16 のネットワーク)に一致し、"
            "対象の一部には一致しない。",
    "plist": "PBR では prefix-list の match 節は無視され全トラフィックが一致する"
             "(実機確認済)。隔離網まで転送され要件違反。",
    "addmatch": "route-map の match を ACL 参照へ直す操作。map 側故障の正解。"
                "ACL 側故障では既に match 済みで変化しない。",
}


def build_choices_fix(d, rnd):
    cands = fix_candidates(d)
    correct = d["_correct_key"]
    c = []
    for key, e, txt, cli in cands:
        ok = (key == correct)
        why = "" if ok else WHY_FIX[key]
        c.append((txt, ok, why, cli))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


CLAIMS = {
    "wc_narrow": "ACL-A の宛先ワイルドカードが、対象ネットワークの一部に一致していない",
    "wc_wide": "ACL-A の宛先ワイルドカードが、隔離網まで一致している",
    "wc_bits": "ACL-A の宛先ワイルドカードが、対象外のネットワークに一致し、"
               "対象の一部に一致していない",
    "acl_dir": "ACL-A の送信元と宛先の指定が逆になっている",
    "rm_no_match": "MAP-A のシーケンスに match 条件が設定されていない",
    "match_plist": "MAP-A の match が prefix-list を参照している",
}
REFUTES = {
    "wc_narrow": "被覆を展開すると対象は全て含まれている(設定抜粋から計算可)。",
    "wc_wide": "被覆に隔離網は含まれていない。",
    "wc_bits": "ワイルドカードは連続被覆で、対象外には一致していない。",
    "acl_dir": "送信元/宛先の並びは正しい。",
    "rm_no_match": "MAP-A には match 行が存在する。",
    "match_plist": "MAP-A の match は ACL を参照している。",
}
CROSS_POOL = [
    ("宛先ルータに戻り経路が無く、応答が返れない",
     "宛先ルータの設定抜粋に両 LAN への静的経路があり、健全側拠点は到達できている。"),
    ("set ip next-hop の指定が誤っている",
     "健全側の route-map が同じ next-hop で機能している。"),
    ("LAN インタフェースに ip policy が適用されていない",
     "設定抜粋のとおり適用済み(カウンタの計上有無も併せて判断できる)。"),
]


def build_choices_cause(d, rnd):
    kind = d["kind"]
    others = [k for k in PBR_KINDS if k != kind]
    in_genre = rnd.sample(others, 3)
    c = [(CLAIMS[kind], True, "")]
    c += [(CLAIMS[k], False, REFUTES[k]) for k in in_genre]
    c += [(t, False, why) for t, why in rnd.sample(CROSS_POOL, 2)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]
