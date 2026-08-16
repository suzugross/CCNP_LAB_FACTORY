#!/usr/bin/env python3
"""CoPP 紙面MCQ ファミリ (BL-125) — gen_paper_mcq.py の shape=copp 素材。

ENARSI 3.3(完全空白領域)の解消。挙動は全て PoC 実測(poc/copp/README.md・
IOL 17.15・盤面 _POC-COPP)の確定6点に基づく:

  1. `show policy-map control-plane` の byte 書式(bc 1500 は自動既定が show にだけ出る)
  2. ★CoPP は punt トラフィックのみ対象(transit は 100% 素通し・カウンタ不変)
  3. ★ACL の deny = 「拒否」ではなく「この class に乗せない」(分類除外)
  4. ★未定義 ACL 参照の class はどの punt にも一致しない(0 match のサイレント失効。
     IF 適用の「全許可」と結果は似るが機構が逆・BL-106 §1 と整合)
  5. pps ポリサは counters の bytes 欄がパケット数になる(書式罠)
  6. exceed-action transmit = 数えつつ転送(何も制限されない)

★モデル層 = BL-100 設計どおり acl_model.py(ACL 意味評価器)の上に
「分類→police」層を載せたもの。punt ベクタを policy の class 順で分類し
(permit=一致 / deny=除外 / 未定義=不一致 / class-default=全一致)、
policer の conform/exceed アクションから帰結を返す:

  pass    : 分類されず(または police なし)無制限に処理される(高レート)
  ok      : 低レートで conform 転送(サービス正常)
  counted : 高レートで conform/exceed とも transmit(計測のみ)
  limited : 高レートで超過分 drop(帯域制限)
  blocked : conform action が drop(完全遮断)
  flaky   : 低レートだが、同一 policer を高レートと共有し超過 drop(道連れ断)
  ifdrop  : 物理 IF の入力 ACL で事前に破棄(CoPP 以前・transit も巻き添え)

要件世界(worlds)が「機能的に直る候補」の中から正解を反転させる(urpf/leakmap 流)。
一意性(complies==1・works>=2)は draw 時に機械検証する。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acl_model  # noqa: E402

KINDS = ["undef_acl", "deny_misread", "exceed_transmit", "conform_drop",
         "class_order", "cdefault_police", "transit_expect"]
WORLDS = ["w_block", "w_limit", "w_protect", "w_monitor"]
# kind ごとに物語が成立する世界(symptom と要件が矛盾しない組だけ)
KIND_WORLDS = {
    "undef_acl": ["w_block", "w_limit", "w_protect", "w_monitor"],
    "deny_misread": ["w_block", "w_limit", "w_monitor"],
    "exceed_transmit": ["w_block", "w_limit", "w_protect"],
    "conform_drop": ["w_block", "w_limit", "w_protect", "w_monitor"],
    "class_order": ["w_block"],
    "cdefault_police": ["w_limit", "w_protect"],
    "transit_expect": ["w_limit"],       # cause 専用(要件描画のためだけの world)
}
ROLES = ["DUT", "EXT"]

PM_POOL = ["PM-COPP", "PM-CPP", "COPP-POLICY"]
CM_LIMIT_POOL = ["CM-ICMP", "CM-PING", "CM-ICMP-LIMIT"]
CM_BLOCK_POOL = ["CM-BLOCK", "CM-ATTACK", "CM-DENY-SRC"]
CM_MGMT_POOL = ["CM-MGMT", "CM-SSH", "CM-ADMIN"]
LIMIT_ACL_POOL = [110, 115, 120, 125, 130]
NEW_ACL_POOL = [150, 155, 160, 165]      # 修正候補が定義し直す番号(盤面と非衝突)


def kind_forms(kind):
    """その kind で成立する出題形(P2 で read/select2/allthat を追加)。
    - transit_expect: 構成が健全なので fix を持たない(cause/read/allthat)。
    - undef_acl: allthat を持たない(police の対象が空集合になり「すべて選べ」が
      成立しない= 正解 0 個は出題しない)。"""
    if kind == "transit_expect":
        return {"cause", "read", "allthat"}
    if kind == "undef_acl":
        return {"fix", "cause", "read", "select2"}
    return {"fix", "cause", "read", "select2", "allthat"}


def draw(rnd, kind=None, world=None):
    d = {"shape": "copp"}
    d["kind"] = kind or rnd.choice(KINDS)
    d["world"] = world or rnd.choice(KIND_WORLDS[d["kind"]])
    if d["world"] not in KIND_WORLDS[d["kind"]]:
        raise ValueError(f"copp: kind={d['kind']} は world={d['world']} を持たない")
    # 盤面アドレス
    on = f"10.{rnd.randint(1, 220)}.{rnd.randint(0, 250)}"
    inn = f"192.168.{rnd.randint(0, 99)}"
    d["out_net"], d["in_net"] = on, inn
    d["out_ip"], d["ext_ip"] = f"{on}.1", f"{on}.2"
    d["in_ip"] = f"{inn}.1"
    d["nms"] = f"{inn}.{rnd.randint(10, 99)}"
    d["srv"] = f"{inn}.{rnd.randint(100, 250)}"
    d["att"] = f"203.0.113.{rnd.randint(2, 250)}"
    # 名前・番号
    d["pm"] = rnd.choice(PM_POOL)
    d["cm_limit"] = rnd.choice(CM_LIMIT_POOL)
    d["cm_block"] = rnd.choice(CM_BLOCK_POOL)
    d["cm_mgmt"] = rnd.choice(CM_MGMT_POOL)
    d["acl_limit"] = rnd.choice(LIMIT_ACL_POOL)
    d["acl_mgmt"] = rnd.choice([x for x in LIMIT_ACL_POOL if x != d["acl_limit"]])
    d["acl_block"] = rnd.choice(
        [x for x in LIMIT_ACL_POOL if x not in (d["acl_limit"], d["acl_mgmt"])])
    # 参照タイポ番号(どの定義済み番号とも不一致・拡張帯に収める)
    cands = [d["acl_limit"] + 1, d["acl_limit"] + 9, d["acl_limit"] + 61]
    taken = {d["acl_limit"], d["acl_mgmt"], d["acl_block"]} | set(NEW_ACL_POOL)
    d["acl_typo"] = rnd.choice([x for x in cands if x not in taken and x <= 199])
    # policer 単位(PoC #5: pps は bytes 欄=パケット数の書式罠)
    d["unit"] = rnd.choice(["bps", "bps", "pps"])
    d["pps_rate"] = rnd.choice([10, 20, 50])
    # ★曖昧要件(BL-113・§0): 要件文の「管理のアクセス」からプロトコル名を落とす。
    #   盤面の vty(transport input ssh)が一意補完の錨= SSH。telnet を保護する
    #   錯乱肢(protect_telnet)は「管理アクセスを保護しない」ため機械的に落ちる。
    d["vague"] = rnd.random() < 0.4
    names = ["RT01", "RT02"]
    rnd.shuffle(names)
    d["m"] = dict(zip(ROLES, names))
    d["roles"] = list(ROLES)
    d["ifaces"] = {"out": "Ethernet0/0", "in": "Ethernet0/1"}
    verify_choices(d)
    return d


# --------------------------------------------------------------------------
# ACL(acl_model が読める show 形式テキスト = 紙面表示と評価の単一ソース)
# --------------------------------------------------------------------------
def acl_show(num, entries):
    lines = [f"Extended IP access list {num}"]
    for i, e in enumerate(entries, 1):
        lines.append(f"    {i * 10} {e}")
    return "\n".join(lines)


def _acl_entries(num, acls):
    txt = acl_show(num, acls[num])
    return acl_model.parse_show_access_lists(txt)[str(num)]


# --------------------------------------------------------------------------
# 状態モデル
# st = {"classes": [{"name", "acl", "police": None|{unit, rate, conform, exceed}}],
#       "cdefault": None|police, "acls": {num: [entry文字列]},
#       "iface_acl": None|{"num", "entries": [entry文字列]}}
# --------------------------------------------------------------------------
def _pol(d, conform="transmit", exceed="drop", unit=None):
    u = unit or d["unit"]
    return {"unit": u, "rate": 8000 if u == "bps" else d["pps_rate"],
            "conform": conform, "exceed": exceed}


def state(d):
    """現在(kind が決める)状態。transit_expect のみ健全。"""
    k = d["kind"]
    la, ma, ba = d["acl_limit"], d["acl_mgmt"], d["acl_block"]
    st = {"classes": [], "cdefault": None, "acls": {}, "iface_acl": None}
    if k == "undef_acl":
        # class はタイポ番号を参照(未定義)。正しい中身の ACL は別番号で定義済み
        st["classes"] = [{"name": d["cm_limit"], "acl": d["acl_typo"],
                          "police": _pol(d)}]
        st["acls"][la] = ["permit icmp any any"]
    elif k == "deny_misread":
        # 「攻撃元を遮断するために deny を追加した」直後の状態
        st["classes"] = [{"name": d["cm_limit"], "acl": la, "police": _pol(d)}]
        st["acls"][la] = [f"deny icmp host {d['att']} any",
                          "permit icmp any any"]
    elif k == "exceed_transmit":
        st["classes"] = [{"name": d["cm_limit"], "acl": la,
                          "police": _pol(d, exceed="transmit")}]
        st["acls"][la] = ["permit icmp any any"]
    elif k == "conform_drop":
        # 前任者が管理 class の action を逆に投入(conform drop / exceed transmit)
        st["classes"] = [
            {"name": d["cm_mgmt"], "acl": ma,
             "police": _pol(d, conform="drop", exceed="transmit", unit="bps")},
            {"name": d["cm_limit"], "acl": la, "police": _pol(d)}]
        st["acls"][ma] = [f"permit tcp host {d['nms']} any eq 22"]
        st["acls"][la] = ["permit icmp any any"]
    elif k == "class_order":
        # 広い制限 class が先・攻撃元の遮断 class が後 → 遮断に到達しない
        st["classes"] = [
            {"name": d["cm_limit"], "acl": la, "police": _pol(d)},
            {"name": d["cm_block"], "acl": ba,
             "police": _pol(d, conform="drop", exceed="drop")}]
        st["acls"][la] = ["permit icmp any any"]
        st["acls"][ba] = [f"permit icmp host {d['att']} any"]
    elif k == "cdefault_police":
        # 保護 class なしで class-default を police → 道連れ
        st["cdefault"] = _pol(d)
    elif k == "transit_expect":
        # 健全な構成(訴えの対象が transit というだけ)
        st["classes"] = [{"name": d["cm_limit"], "acl": la, "police": _pol(d)}]
        st["acls"][la] = ["permit icmp any any"]
    return st


# --------------------------------------------------------------------------
# 分類→police 層(acl_model の上に載せる評価器・PoC 確定挙動の写像)
# --------------------------------------------------------------------------
def vectors(d):
    """紙面の意味論を担う punt/transit ベクタ。"""
    return {
        "ssh": {"proto": "tcp", "src": d["nms"], "dst": d["in_ip"],
                "dport": 22, "rate": "low", "punt": True},
        "mon": {"proto": "icmp", "src": d["nms"], "dst": d["in_ip"],
                "rate": "low", "punt": True},
        "flood": {"proto": "icmp", "src": d["att"], "dst": d["out_ip"],
                  "rate": "high", "punt": True},
        "ospf": {"proto": "ospf", "src": d["ext_ip"], "dst": d["out_ip"],
                 "rate": "low", "punt": True},
        "transit": {"proto": "icmp", "src": d["att"], "dst": d["srv"],
                    "rate": "high", "punt": False},
    }


def classify(d, st, v):
    """class 順に評価。permit=一致 / deny・暗黙deny=除外 / ★未定義 ACL=不一致。
    どの class にも乗らなければ None(=class-default)。"""
    for c in st["classes"]:
        if c["acl"] not in st["acls"]:
            continue                     # ★PoC #4: 未定義参照はサイレント失効
        if acl_model.evaluate(_acl_entries(c["acl"], st["acls"]), v):
            return c
    return None


def _iface_dropped(d, st, name, v):
    if not st.get("iface_acl") or name not in ("flood", "ospf", "transit"):
        return False
    ia = st["iface_acl"]
    ents = acl_model.parse_show_access_lists(
        acl_show(ia["num"], ia["entries"]))[str(ia["num"])]
    return not acl_model.evaluate(ents, v)


def outcomes(d, st):
    """全ベクタの帰結。★PoC #2: 非 punt(transit)は CoPP の対象外。"""
    vs = vectors(d)
    cls = {}
    for name, v in vs.items():
        if _iface_dropped(d, st, name, v):
            cls[name] = "ifdrop"
        elif not v["punt"]:
            cls[name] = "pass"
        else:
            cls[name] = classify(d, st, v)   # class dict / None(=default)
    # policer の識別子(道連れ判定のための共有検出)
    def polkey(name):
        c = cls[name]
        if isinstance(c, str) or c is None and st["cdefault"] is None:
            return None
        if c is None:
            return "__default__"
        return c["name"] if c["police"] else None

    out = {}
    for name, v in vs.items():
        c = cls[name]
        if c == "ifdrop":
            out[name] = "ifdrop"
            continue
        if c == "pass":
            out[name] = "pass"
            continue
        pol = st["cdefault"] if c is None else c["police"]
        if pol is None:
            out[name] = "ok" if v["rate"] == "low" else "pass"
            continue
        shared_high = any(
            vs[o]["rate"] == "high" and o != name
            and polkey(o) is not None and polkey(o) == polkey(name)
            for o in vs)
        if v["rate"] == "low":
            if pol["conform"] == "drop":
                out[name] = "blocked"
            elif shared_high and pol["exceed"] == "drop":
                out[name] = "flaky"      # ★class-default 道連れ等(トークン競合)
            else:
                out[name] = "ok"
        else:
            if pol["conform"] == "drop":
                out[name] = "blocked"
            elif pol["exceed"] == "drop":
                out[name] = "limited"
            else:
                out[name] = "counted"    # ★PoC #6: 数えつつ転送
    return out


# --------------------------------------------------------------------------
# 修正候補(絶対状態)と要件適合
# --------------------------------------------------------------------------
CAND_KEYS = ["block_first", "limit_dedicated", "protect_explicit",
             "monitor_mode", "deny_exclude", "iface_acl_any", "cdefault_tight",
             "protect_telnet"]


def apply_cand(d, key):
    n1, n2, n3 = NEW_ACL_POOL[0], NEW_ACL_POOL[1], NEW_ACL_POOL[2]
    st = {"classes": [], "cdefault": None, "acls": {}, "iface_acl": None}
    if key == "block_first":
        st["classes"] = [
            {"name": "CM-BLOCK-NEW", "acl": n1,
             "police": _pol(d, conform="drop", exceed="drop")},
            {"name": "CM-LIMIT-NEW", "acl": n2, "police": _pol(d)},
            {"name": "CM-MGMT-NEW", "acl": n3, "police": None}]
        st["acls"] = {n1: [f"permit icmp host {d['att']} any"],
                      n2: ["permit icmp any any"],
                      n3: [f"permit tcp host {d['nms']} any eq 22"]}
    elif key == "limit_dedicated":
        st["classes"] = [
            {"name": "CM-MGMT-NEW", "acl": n3, "police": None},
            {"name": "CM-LIMIT-NEW", "acl": n2, "police": _pol(d)}]
        st["acls"] = {n2: ["permit icmp any any"],
                      n3: [f"permit tcp host {d['nms']} any eq 22"]}
    elif key == "protect_explicit":
        st["classes"] = [{"name": "CM-PROTECT-NEW", "acl": n3, "police": None}]
        st["acls"] = {n3: [f"permit tcp host {d['nms']} any eq 22",
                           "permit ospf any any"]}
        st["cdefault"] = _pol(d)
    elif key == "monitor_mode":
        st["classes"] = [{"name": "CM-LIMIT-NEW", "acl": n2,
                          "police": _pol(d, exceed="transmit")}]
        st["acls"] = {n2: ["permit icmp any any"]}
    elif key == "deny_exclude":
        st["classes"] = [{"name": "CM-LIMIT-NEW", "acl": n2, "police": _pol(d)}]
        st["acls"] = {n2: [f"deny icmp host {d['att']} any",
                           "permit icmp any any"]}
    elif key == "iface_acl_any":
        st["classes"] = [{"name": "CM-LIMIT-NEW", "acl": n2, "police": _pol(d)}]
        st["acls"] = {n2: ["permit icmp any any"]}
        st["iface_acl"] = {"num": 170, "entries": ["deny icmp any any",
                                                   "permit ip any any"]}
    elif key == "cdefault_tight":
        st["cdefault"] = _pol(d)
    elif key == "protect_telnet":
        # ★曖昧要件の錯乱肢: 「管理アクセス」を telnet と誤読した保護。
        #   盤面の vty は transport input ssh のみなので SSH が保護されず、
        #   class-default の制限に道連れ → works が機械的に落とす。
        st["classes"] = [{"name": "CM-PROTECT-NEW", "acl": n3, "police": None}]
        st["acls"] = {n3: [f"permit tcp host {d['nms']} any eq 23",
                           "permit ospf any any"]}
        st["cdefault"] = _pol(d)
    return st


def _host_specific(d, st):
    """class の参照 ACL に攻撃元を名指しするエントリがあるか(w_limit の禁止事項)。"""
    for c in st["classes"]:
        for e in st["acls"].get(c["acl"], []):
            if f"host {d['att']}" in e:
                return True
    return False


def _no_drop_anywhere(st):
    pols = [c["police"] for c in st["classes"] if c["police"]]
    if st["cdefault"]:
        pols.append(st["cdefault"])
    return all(p["conform"] == "transmit" and p["exceed"] == "transmit"
               for p in pols)


def _works(d, st):
    """機能要件: 管理と隣接が生きており、訴えの対象(flood)が対処されている。
    w_monitor では「対処」= 計測に乗っていること(counted 以上)。"""
    o = outcomes(d, st)
    base = o["ssh"] == "ok" and o["ospf"] == "ok"
    if d["world"] == "w_monitor":
        return base and o["flood"] in ("counted", "limited", "blocked")
    return base and o["flood"] in ("limited", "blocked", "ifdrop")


def _complies(d, st):
    o = outcomes(d, st)
    w = d["world"]
    if w == "w_block":
        return (o["flood"] == "blocked" and o["mon"] == "ok"
                and o["transit"] == "pass" and st["iface_acl"] is None)
    if w == "w_limit":
        vf = vectors(d)["flood"]
        return (o["flood"] == "limited" and not _host_specific(d, st)
                and classify(d, st, vf) is not None       # 専用 class で制限
                and st["cdefault"] is None and st["iface_acl"] is None)
    if w == "w_protect":
        vs = vectors(d)
        cs, co, cf = (classify(d, st, vs[k]) for k in ("ssh", "ospf", "flood"))
        return (cs is not None and cs["police"] is None
                and co is not None and co["police"] is None
                and cf is None and st["cdefault"] is not None
                and st["cdefault"]["conform"] == "transmit"
                and st["cdefault"]["exceed"] == "drop"
                and st["iface_acl"] is None)
    # w_monitor: 何も破棄しない・flood は計測に乗る・IF ACL 不使用
    return (_no_drop_anywhere(st) and outcomes(d, st)["flood"] == "counted"
            and st["iface_acl"] is None)


def verify_choices(d):
    if d["kind"] == "transit_expect":
        # cause 専用: 構成が健全である(訴えは仕様の誤解)ことだけ検証する
        if not _works(d, state(d)):
            raise ValueError("copp: transit_expect の盤面が健全でない")
        return
    works, ok = [], []
    for key in CAND_KEYS:
        st = apply_cand(d, key)
        if _works(d, st):
            works.append(key)
            if _complies(d, st):
                ok.append(key)
    if len(ok) != 1:
        raise ValueError(f"copp 一意性違反: kind={d['kind']} world={d['world']} "
                         f"works={works} ok={ok}")
    if len(works) < 2:
        raise ValueError(f"copp 直る候補不足: kind={d['kind']} works={works}")
    # ★壊れ判定は「要件に照らして」行う: class_order のように機能(帯域制限)は
    #   生きていて、要件(完全遮断)だけが満たされない kind があるため。
    cur = state(d)
    if _works(d, cur) and _complies(d, cur):
        raise ValueError(f"copp: kind={d['kind']} world={d['world']} が壊れていない")
    d["_correct_key"] = ok[0]
    d["_works"] = works


# --------------------------------------------------------------------------
# fix 選択肢(散文 = Cisco 語調・CLI = 新規名で組み直す状態収束形)
# --------------------------------------------------------------------------
def _police_cli(d, pol):
    if pol["unit"] == "pps":
        return [f"  police rate {pol['rate']} pps",
                f"   conform-action {pol['conform']}",
                f"   exceed-action {pol['exceed']}"]
    return [f"  police cir 8000 bc 1500",
            f"   conform-action {pol['conform']}",
            f"   exceed-action {pol['exceed']}"]


def _cand_cli(d, key):
    st = apply_cand(d, key)
    L = []
    for num, ents in sorted(st["acls"].items()):
        L += [f"access-list {num} {e}" for e in ents]
    for c in st["classes"]:
        L += [f"class-map match-all {c['name']}",
              f" match access-group {c['acl']}"]
    L.append(f"policy-map PM-NEW")
    for c in st["classes"]:
        L.append(f" class {c['name']}")
        if c["police"]:
            L += _police_cli(d, c["police"])
    if st["cdefault"]:
        L.append(" class class-default")
        L += _police_cli(d, st["cdefault"])
    L += ["control-plane",
          f" no service-policy input {d['pm']}",
          " service-policy input PM-NEW"]
    if st["iface_acl"]:
        ia = st["iface_acl"]
        L = [f"access-list {ia['num']} {e}" for e in ia["entries"]] + L
        L += [f"interface {d['ifaces']['out']}",
              f" ip access-group {ia['num']} in"]
    return L


def _rate_val(d):
    return "8000 bps" if d["unit"] == "bps" else f"{d['pps_rate']} pps"


def _rate_txt(d):
    return f"{_rate_val(d)} に"


def fix_candidates(d):
    """(key, 説明文, CLI行)。CLI は新規の名前・番号で policy を組み直して
    control-plane で置換する形(既存構成との衝突なしに絶対状態へ収束する)。"""
    dut = d["m"]["DUT"]
    att, nms = d["att"], d["nms"]
    prose = {
        "block_first": (
            f"{dut} において、発信元 {att} からの ICMP を permit によって"
            "一致させるところの class を、ポリシーの先頭に定義し、その police の"
            "アクションを、conform-action drop および exceed-action drop に"
            "構成する。続く class において、その他の ICMP の帯域を"
            f"{_rate_txt(d)}制限し、そして、{nms} からの SSH を一致させる"
            "class を、police なしで定義する"),
        "limit_dedicated": (
            f"{dut} において、{nms} からの SSH を一致させるところの class を、"
            "police なしで定義し、そして、ルータに宛てられた ICMP のすべてを "
            "permit によって一致させるところの専用の class において、帯域を"
            f"{_rate_txt(d)}制限する(超過は drop)"),
        "protect_explicit": (
            f"{dut} において、{nms} からの SSH、および、ルーティング・"
            "プロトコルのトラフィックを一致させるところの class を、police なしで"
            "定義する。そして、class-default に対して、帯域の制限"
            f"({_rate_val(d)})を、超過 drop のアクションで構成する"),
        "monitor_mode": (
            f"{dut} において、ルータに宛てられた ICMP を一致させるところの "
            "class に、police を conform-action transmit および exceed-action "
            "transmit のアクションで構成する"),
        "deny_exclude": (
            f"{dut} において、ICMP の class が参照するところのアクセス・リストの"
            f"先頭に、`deny icmp host {att} any` のエントリを追加する"),
        "iface_acl_any": (
            f"{dut} の外部のインターフェイスの in 方向に、`deny icmp any any` "
            "および `permit ip any any` からなるところのアクセス・グループを"
            "適用する(コントロール・プレーンのポリシーは、ICMP の帯域の制限の"
            "形を維持する)"),
        "cdefault_tight": (
            f"{dut} において、明示の class を定義せずに、class-default に対して、"
            f"帯域の制限({_rate_val(d)})を、超過 drop のアクションで"
            "構成する"),
        "protect_telnet": (
            f"{dut} において、{nms} からの telnet(TCP ポート 23)、および、"
            "ルーティング・プロトコルのトラフィックを一致させるところの class "
            "を、police なしで定義する。そして、class-default に対して、帯域の"
            f"制限({_rate_val(d)})を、超過 drop のアクションで構成する"),
    }
    return [(k, prose[k], _cand_cli(d, k)) for k in CAND_KEYS]


WHY = {
    "block_first": "", "limit_dedicated": "", "protect_explicit": "",
    "monitor_mode": "exceed のアクションが transmit であり、トラフィックは"
                    "計測されるのみで、破棄されない。",
    "deny_exclude": "deny のエントリは、当該の class の一致から除外するのみで"
                    "あり、破棄ではない。除外されたトラフィックは、"
                    "class-default において制限なしに処理される。",
    "iface_acl_any": "",
    "cdefault_tight": "class-default には、ルーティング・プロトコルや管理の"
                      "トラフィックを含む、分類されないすべてのルータ宛の"
                      "トラフィックが含まれ、道連れに制限される。",
    "protect_telnet": "盤面の vty は transport input ssh のみを受け付けており、"
                      "管理のアクセスは SSH である。telnet の保護は管理の"
                      "アクセスを保護せず、SSH は class-default の制限に"
                      "道連れとなる。",
}
WHY_BY_WORLD = {
    "w_block": {
        "limit_dedicated": "帯域の制限にとどまり、当該の発信元の完全な遮断と"
                           "いう要件に適合しない。",
        "protect_explicit": "帯域の制限にとどまり、当該の発信元の完全な遮断と"
                            "いう要件に適合しない。",
        "iface_acl_any": "ルータを通過するところのトラフィックまでもが"
                         "破棄され、転送への影響の禁止という要件に適合しない。"},
    "w_limit": {
        "block_first": "特定の発信元のアドレスを名指しにしており、"
                       "要件に適合しない。",
        "protect_explicit": "class-default の扱いを変更しており、"
                            "要件に適合しない。",
        "iface_acl_any": "インターフェイスのアクセス・グループによる対処で"
                         "あり、ルータを通過するところのトラフィックまでもが"
                         "破棄される(転送への影響の禁止、および、コントロール・"
                         "プレーンのポリシーによる実装という要件に適合しない)。"},
    "w_protect": {
        "block_first": "特定の発信元のための class を追加しており、"
                       "要件に適合しない。",
        "limit_dedicated": "制限が専用の class において行われており、"
                           "class-default における制限という要件に適合しない。",
        "iface_acl_any": "インターフェイスのアクセス・グループによる対処で"
                         "あり、ルータを通過するところのトラフィックまでもが"
                         "破棄される(転送への影響の禁止という要件に適合"
                         "しない)。"},
    "w_monitor": {
        "block_first": "破棄を行っており、計測のみという要件に適合しない。",
        "limit_dedicated": "超過するトラフィックが破棄され、計測のみという"
                           "要件に適合しない。",
        "protect_explicit": "超過するトラフィックが破棄され、計測のみという"
                            "要件に適合しない。",
        "iface_acl_any": "破棄を行っており、計測のみという要件に適合しない。"},
}


def _why(d, key):
    if key == "monitor_mode" and d["kind"] == "exceed_transmit":
        return ("exceed のアクションが transmit のままであり、現在の挙動と"
                "変わらない(計測のみで、事象が解消しない)。")
    if key == "deny_exclude" and d["kind"] == "deny_misread":
        return ("現在の状態と同じ deny の形であり、当該の発信元は class の"
                "一致から除外されたまま、制限なしに処理され続ける。")
    return WHY_BY_WORLD[d["world"]].get(key) or WHY[key]


def build_choices_fix(d, rnd):
    correct = d["_correct_key"]
    cands = {k: (txt, cli) for k, txt, cli in fix_candidates(d)}
    others_ok = [k for k in d["_works"] if k != correct]
    losers = [k for k in CAND_KEYS if k not in d["_works"]]
    pick_losers = rnd.sample(losers, min(2, len(losers)))
    # ★曖昧要件の盤面では telnet 誤読肢を必ず出す(曖昧さの解消を実際に課す)
    if d.get("vague") and "protect_telnet" in losers \
            and "protect_telnet" not in pick_losers:
        pick_losers[0] = "protect_telnet"
    keep = ([correct] + rnd.sample(others_ok, min(2, len(others_ok)))
            + pick_losers)
    c = [(cands[k][0], k == correct, "" if k == correct else _why(d, k),
          cands[k][1]) for k in keep]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# cause 選択肢
# --------------------------------------------------------------------------
CLAIMS = {
    "undef_acl": "class が match によって参照しているところの番号のアクセス・"
                 "リストが、定義されていない",
    "deny_misread": "アクセス・リストの deny のエントリによって、当該の発信元が "
                    "class の一致から除外されている",
    "exceed_transmit": "police の exceed のアクションが transmit に構成されて"
                       "おり、超過するトラフィックが破棄されていない",
    "conform_drop": "police の conform のアクションが drop に構成されており、"
                    "適合するトラフィックまでもが破棄されている",
    "class_order": "より広い一致を持つところの class が先に評価されており、"
                   "意図された class にトラフィックが到達していない",
    "cdefault_police": "保護のための明示の class が存在せず、管理およびルー"
                       "ティングのトラフィックが、class-default の制限に道連れ"
                       "にされている",
    "transit_expect": "報告されているトラフィックは、ルータを通過するところの"
                      "(transit の)ものであり、コントロール・プレーンの"
                      "ポリシーの対象の外にある",
}
REFUTES = {
    "undef_acl": "示されている出力のとおり、参照されている番号のアクセス・"
                 "リストは定義されている。",
    "deny_misread": "示されているアクセス・リストに、deny のエントリは"
                    "存在しない。",
    "exceed_transmit": "示されている出力のとおり、exceed のアクションは "
                       "drop である。",
    "conform_drop": "示されている出力のとおり、conform のアクションは "
                    "transmit である。",
    "class_order": "示されているポリシーの class の一致は重複しておらず、"
                   "評価の順序は事象に関係しない。",
    "cdefault_police": "class-default には police が構成されておらず、"
                       "道連れの制限は発生しない。",
    "transit_expect": "報告されている事象は、ルータ自身に宛てられたところの"
                      "トラフィックに関するものである。",
}
# 同一盤面で「同時に真」になり得る claim の排他(正解の一意性)
CAUSE_EXCLUDE = {
    # conform_drop の盤面では管理 class の exceed が transmit(半分真)
    "conform_drop": {"exceed_transmit"},
    # class_order の盤面では遮断 class の conform が drop(意図的・半分真)
    "class_order": {"conform_drop"},
    # cdefault_police の盤面には class が1つも無く、undef_acl の反証文
    # (「参照されている番号の ACL は定義されている」)が盤面と噛み合わない
    "cdefault_police": {"undef_acl"},
}
CROSS = [
    ("サービス・ポリシーが、コントロール・プレーンの output の方向に適用されて"
     "おり、着信するトラフィックに効果を持たない",
     "示されている構成のとおり、ポリシーは input の方向に適用されている。"),
    ("物理インターフェイスの in 方向のアクセス・グループによって、当該の"
     "トラフィックが事前に破棄されている",
     "示されている構成に、ip access-group のステートメントは存在しない。"),
    ("police のバーストの値が構成されていないという理由により、policer が"
     "動作していない",
     "バーストの値は、構成されない場合に既定の値が適用され、show の出力にも"
     "表示されている(構成に書いていない値が show にだけ現れる)。"),
]


def build_choices_cause(d, rnd):
    kind = d["kind"]
    others = [k for k in KINDS
              if k != kind and k not in CAUSE_EXCLUDE.get(kind, ())]
    if kind != "transit_expect":
        # transit の取り違え claim は kind プールから錯乱肢として供給される
        pass
    c = [(CLAIMS[kind], True, "")]
    c += [(CLAIMS[k], False, REFUTES[k]) for k in rnd.sample(others, 3)]
    cross = list(CROSS)
    c += [(t, False, why) for t, why in rnd.sample(cross, 2)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# read 形(P2): 「このパケットは、どのように扱われるか」— 帰結を1つ選ぶ。
# 対象パケットは kind の指紋が最も出る1本を固定で選ぶ(設問文が情報の担い手)。
# --------------------------------------------------------------------------
def read_target(d):
    """(ベクタ名, 設問文に埋める対象パケットの記述)。"""
    dut = d["m"]["DUT"]
    k = d["kind"]
    if k == "transit_expect":
        return ("transit",
                f"発信元 {d['att']} から、サーバ {d['srv']} に宛てられ、"
                f"{dut} を通過するところの ICMP のパケット")
    if k in ("conform_drop", "cdefault_police"):
        return ("ssh",
                f"{d['nms']} から、{dut} に宛てられた SSH"
                "(TCP ポート 22)のパケット")
    return ("flood",
            f"発信元 {d['att']} から、{dut} 自身のアドレス({d['out_ip']})"
            "に宛てられた ICMP のパケット")


def _read_stmts(d, st, cname):
    """帰結ステートメントの雛形(text と、誤答時の why を返す関数群)。"""
    act = {"transmit": "転送", "drop": "破棄"}
    pol_note = ""
    if st["classes"] and st["classes"][0]["police"]:
        p = st["classes"][0]["police"]
        pol_note = (f"当該の class のアクションは conform-action {p['conform']}"
                    f" / exceed-action {p['exceed']} である。")
    return {
        "cls_limited": (f"class {cname} に一致し、レートに適合する分は転送され、"
                        "そして、超過する分は破棄される", pol_note),
        "cls_counted": (f"class {cname} に一致して計測されるが、超過する分を"
                        "含めて、すべて転送される", pol_note),
        "cls_blocked": (f"class {cname} に一致し、レートへの適合に関わらず、"
                        "すべて破棄される", pol_note),
        "d_pass": ("いずれの police を持つ class にも一致せず、class-default に"
                   "おいて、制限なしに処理される", ""),
        "d_lim": ("class-default に一致し、帯域の制限を受ける"
                  "(超過する分は破棄される)", ""),
        "d_blk": ("class-default に一致し、すべて破棄される", ""),
        "d_cnt": ("class-default に一致して計測されるが、超過する分を含めて、"
                  "すべて転送される", ""),
        "exempt": ("コントロール・プレーンのポリシーの対象とならず、"
                   "通常どおり転送される", "当該のパケットはルータ自身に宛てられて"
                   "おり(punt)、ポリシーの評価の対象である。"),
    }


def build_choices_read(d, rnd):
    """5択・正解1。正解はモデルの帰結から機械的に決める。"""
    st = state(d)
    name, ttxt = read_target(d)
    d["_read_target"] = ttxt
    v = vectors(d)[name]
    o = outcomes(d, st)[name]
    c = classify(d, st, v) if v["punt"] else None
    cname = (c["name"] if c else
             (st["classes"][0]["name"] if st["classes"] else "class-default"))
    S = _read_stmts(d, st, cname)
    # 正解キーの決定(flaky は class-default 道連れ= d_lim の意味論)
    if not v["punt"]:
        ckey = "exempt"
    elif c is None and st["cdefault"] is None:
        ckey = "d_pass"
    elif c is None:
        ckey = {"limited": "d_lim", "flaky": "d_lim", "blocked": "d_blk",
                "counted": "d_lim", "ok": "d_lim"}[o]
        if o == "counted":
            ckey = "d_lim"        # cdefault 計測のみは現行 kind では出ない
    else:
        ckey = {"limited": "cls_limited", "counted": "cls_counted",
                "blocked": "cls_blocked", "flaky": "cls_limited",
                "ok": "cls_limited"}[o]
    # 誤答の why: 盤面の機構で上書きできるものは上書きする
    why_over = {}
    if d["kind"] == "undef_acl":
        why_over["cls_limited"] = why_over["cls_counted"] = \
            why_over["cls_blocked"] = (
                "class が参照している番号のアクセス・リストが定義されておらず、"
                "この class にはいかなるトラフィックも一致しない(実測: 0 match)。")
    if d["kind"] == "deny_misread" and name == "flood":
        why_over["cls_limited"] = why_over["cls_counted"] = \
            why_over["cls_blocked"] = (
                "deny のエントリによって、当該の発信元は class の一致から"
                "除外されている(deny は破棄ではない)。")
    if st["cdefault"] is None:
        why_over.setdefault("d_lim", "class-default に police は構成されていない。")
        why_over.setdefault("d_blk", "class-default に police は構成されていない。")
    if c is not None:
        why_over.setdefault("d_pass", f"当該のパケットは class {cname} に一致する。")
    # 錯乱肢プール(正解と同キー系の別帰結を優先的に混ぜる)
    pool = [k for k in S if k != ckey]
    if not st["classes"]:
        pool = [k for k in pool if not k.startswith("cls_")]
    # class_order 盤面では「遮断 class に一致してすべて破棄」を必ず出す(本題の罠)
    forced = []
    if d["kind"] == "class_order" and name == "flood":
        blk = d["m"]  # noqa: F841  (見出し合わせ・値は st から)
        bname = st["classes"][1]["name"]
        forced = [(f"class {bname} に一致し、レートへの適合に関わらず、"
                   "すべて破棄される", False,
                   f"より広い一致を持つ class {st['classes'][0]['name']} が先に"
                   "評価され、当該のパケットはこの class に到達しない。")]
        pool = [k for k in pool if k != "cls_blocked"]
    picks = rnd.sample(pool, 4 - len(forced))
    c_list = [(S[ckey][0], True, "")]
    c_list += forced
    for k in picks:
        why = why_over.get(k, S[k][1]) or "示されている構成の帰結と一致しない。"
        c_list.append((S[k][0], False, why))
    order = list(range(len(c_list)))
    rnd.shuffle(order)
    out = [c_list[i] for i in order]
    if sum(1 for x in out if x[1]) != 1 or len(out) != 5:
        raise ValueError("copp read: 選択肢構成が不正")
    return out


# --------------------------------------------------------------------------
# select2 形(P2): 構成の挙動に関する記述から「正しいものを2つ」選ぶ。
# スロット(観点)ごとに真/偽の両形を用意し、真にする2スロットを抽選する
# = 正解数2が構成的に保証される。単位ひっかけ(②近似値肢)は常に偽。
# --------------------------------------------------------------------------
def _select2_slots(d, st, o, rnd):
    """[(true_text, false_text, false_why)] — 5 極性スロット。"""
    dut, ext = d["m"]["DUT"], d["m"]["EXT"]
    att, nms, srv = d["att"], d["nms"], d["srv"]
    vs = vectors(d)
    slots = []
    # ① transit(punt 限定の理解・③ロール取り違え)
    slots.append((
        f"{srv} に宛てられ、{dut} を通過するところの ICMP は、ポリシーによる"
        "制限を受けない",
        f"{srv} に宛てられ、{dut} を通過するところの ICMP も、ポリシーによる"
        "帯域の制限の対象である",
        "CoPP はルータ自身に宛てられた(punt)トラフィックのみを対象とする"
        "(通過するトラフィックのカウンタは増加しない)。"))
    # ② flood の帰結
    fl = {
        "pass": f"発信元 {att} からの、ルータ自身に宛てられた ICMP は、"
                "制限なしに処理される",
        "counted": f"発信元 {att} からの、ルータ自身に宛てられた ICMP は、"
                   "計測されるが、破棄されることはない",
        "limited": f"発信元 {att} からの、ルータ自身に宛てられた ICMP は、"
                   "帯域が制限され、そして、超過する分は破棄される",
        "blocked": f"発信元 {att} からの、ルータ自身に宛てられた ICMP は、"
                   "すべて破棄される",
    }
    t = fl[o["flood"]]
    f = fl[rnd.choice([k for k in fl if k != o["flood"]])]
    slots.append((t, f, f"実際には、{t}。"))
    # ③ ssh の帰結
    if o["ssh"] == "blocked":
        t3 = f"{nms} からの SSH のパケットは、police のアクションによって破棄される"
        f3 = f"{nms} からの SSH のパケットが、破棄されることはない"
    elif o["ssh"] == "flaky":
        t3 = (f"{nms} からの SSH のパケットは、police のアクションによって"
              "破棄されることがあり得る")
        f3 = f"{nms} からの SSH のパケットが、破棄されることはない"
    else:
        t3 = f"{nms} からの SSH のパケットが、police によって破棄されることはない"
        f3 = (f"{nms} からの SSH のパケットは、police のアクションによって"
              "破棄されることがあり得る")
    slots.append((t3, f3, f"実際には、{t3}。"))
    # ④ class-default の扱い
    if st["cdefault"]:
        t4 = "class-default に一致するトラフィックは、帯域の制限を受ける"
        f4 = "class-default に一致するトラフィックは、制限なしに処理される"
    else:
        t4 = "class-default に一致するトラフィックは、制限なしに処理される"
        f4 = "class-default に一致するトラフィックは、帯域の制限を受ける"
    slots.append((t4, f4, f"実際には、{t4}。"))
    # ⑤ 盤面固有(deny 意味論 / 未定義 ACL のカウンタ / ルーティングの扱い)
    if d["kind"] == "deny_misread":
        t5 = ("アクセス・リストの deny に一致する発信元からの、ルータ宛の "
              "ICMP は、制限なしに処理される")
        f5 = ("アクセス・リストの deny に一致する発信元からの、ルータ宛の "
              "ICMP は、破棄される")
        w5 = ("deny は「この class に乗せない」であり、除外されたトラフィックは "
              "class-default(police なし)で処理される。")
    elif d["kind"] == "undef_acl":
        cm = st["classes"][0]["name"]
        t5 = f"class {cm} のカウンタが、増加することはない"
        f5 = f"class {cm} のカウンタは、着信の ICMP によって増加する"
        w5 = ("参照されている番号のアクセス・リストが未定義であり、この class "
              "にはいかなるトラフィックも一致しない(実測: 0 match)。")
    else:
        v = vs["ospf"]
        c = classify(d, st, v)
        pol = st["cdefault"] if c is None else c["police"]
        if pol is not None:
            t5 = "ルーティング・プロトコルのトラフィックは、police の対象である"
            f5 = ("ルーティング・プロトコルのトラフィックが、police の対象に"
                  "なることはない")
        else:
            t5 = ("ルーティング・プロトコルのトラフィックは、police による"
                  "制限を受けない")
            f5 = "ルーティング・プロトコルのトラフィックは、police の対象である"
        w5 = f"実際には、{t5}。"
    slots.append((t5, f5, w5))
    return slots


def build_choices_select2(d, rnd):
    """6択・正解ちょうど2(構成的に保証)。"""
    st = state(d)
    o = outcomes(d, st)
    slots = _select2_slots(d, st, o, rnd)
    true_idx = set(rnd.sample(range(len(slots)), 2))
    c = []
    for i, (t, f, w) in enumerate(slots):
        if i in true_idx:
            c.append((t, True, ""))
        else:
            c.append((f, False, w))
    # ⑥ 単位ひっかけ(常に偽・②近似値肢)
    if d["unit"] == "bps":
        c.append(("ポリサは、毎秒 8000 パケットまでを適合として扱う", False,
                  "cir 8000 の単位は bps(ビット/秒)である(パケット数ではない)。"))
    else:
        c.append(("ポリサのバーストの値は、1500 バイトである", False,
                  f"rate {d['pps_rate']} pps のポリサのバーストは 2 packets "
                  "(自動既定)である。bc 1500 bytes は bps(cir)形の既定値。"))
    order = list(range(len(c)))
    rnd.shuffle(order)
    out = [c[i] for i in order]
    if sum(1 for x in out if x[1]) != 2 or len(out) != 6:
        raise ValueError("copp select2: 正解数が2でない")
    return out


# --------------------------------------------------------------------------
# all-that-apply 形(P2・数非明示): 「police のアクションの対象になるものをすべて」
# 正解集合はモデル(分類→policer の有無)から機械的に決める。transit は常に対象外
# (=恒常の★罠)。undef_acl は集合が空になるため kind_forms で除外済み。
# --------------------------------------------------------------------------
def _policed(d, st, name):
    v = vectors(d)[name]
    if not v["punt"]:
        return False
    c = classify(d, st, v)
    pol = st["cdefault"] if c is None else c["police"]
    return pol is not None


def build_choices_allthat(d, rnd):
    st = state(d)
    dut, ext = d["m"]["DUT"], d["m"]["EXT"]
    att, nms, srv = d["att"], d["nms"], d["srv"]
    items = [
        ("flood", f"発信元 {att} から、{dut} 自身に宛てられた ICMP"),
        ("transit", f"発信元 {att} から、サーバ {srv} に宛てられ、{dut} を"
                    "通過する ICMP"),
        ("mon", f"{nms} から、{dut} 自身に宛てられた ICMP(死活監視の ping)"),
        ("ssh", f"{nms} から、{dut} への SSH のセッションのパケット"),
        ("ospf", f"{ext} からの、ルーティング・プロトコルのパケット"),
    ]
    whys = {
        "transit": "★CoPP は punt(ルータ自身宛)のみを対象とし、通過する"
                   "トラフィックには適用されない(カウンタも増加しない)。",
    }
    c = []
    n_true = 0
    for name, desc in items:
        tv = _policed(d, st, name)
        n_true += 1 if tv else 0
        if tv:
            c.append((desc, True, ""))
            continue
        why = whys.get(name)
        if why is None:
            v = vectors(d)[name]
            cl = classify(d, st, v)
            if cl is None and d["kind"] == "deny_misread" and name == "flood":
                why = ("deny のエントリによって class の一致から除外され、"
                       "police を持たない class-default で処理される。")
            elif cl is None:
                why = ("police を持つ class に一致せず、police の構成されて"
                       "いない class-default で処理される。")
            else:
                why = f"一致する class {cl['name']} に police は構成されていない。"
        c.append((desc, False, why))
    if not 1 <= n_true <= 4:
        raise ValueError(f"copp allthat: 正解数 {n_true} が範囲外")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
def selftest(seeds=40):
    import random as _r
    ng = 0
    n_fix = n_cause = 0
    units = set()
    for kind in KINDS:
        for world in KIND_WORLDS[kind]:
            for s in range(seeds):
                rnd = _r.Random(hash((kind, world, s)) & 0xFFFFFFFF)
                try:
                    d = draw(rnd, kind=kind, world=world)
                except ValueError as exc:
                    print(f"NG draw {kind}/{world}/{s}: {exc}")
                    ng += 1
                    continue
                units.add(d["unit"])
                # cause: 正解ちょうど1・6択
                cc = build_choices_cause(d, _r.Random(s))
                if len(cc) != 6 or sum(1 for x in cc if x[1]) != 1:
                    print(f"NG cause {kind}/{world}/{s}")
                    ng += 1
                n_cause += 1
                if "fix" in kind_forms(kind):
                    fc = build_choices_fix(d, _r.Random(s))
                    if len(fc) != 5 or sum(1 for x in fc if x[1]) != 1:
                        print(f"NG fix {kind}/{world}/{s}")
                        ng += 1
                    # ★曖昧要件の盤面では telnet 誤読肢が必ず提示される
                    if d.get("vague"):
                        tel = [x for x in fc if "telnet" in x[0]]
                        if len(tel) != 1 or tel[0][1]:
                            print(f"NG vague-telnet {kind}/{world}/{s}")
                            ng += 1
                    # 正解候補の状態が世界の要件に適合し、他は不適合(再確認)
                    st = apply_cand(d, d["_correct_key"])
                    if not (_works(d, st) and _complies(d, st)):
                        print(f"NG correct-state {kind}/{world}/{s}")
                        ng += 1
                    n_fix += 1
                # P2: read=5択1正解 / select2=6択2正解 / allthat=正解1〜4
                rc2 = build_choices_read(d, _r.Random(s ^ 0xEAD))
                if len(rc2) != 5 or sum(1 for x in rc2 if x[1]) != 1:
                    print(f"NG read {kind}/{world}/{s}")
                    ng += 1
                sc2 = build_choices_select2(d, _r.Random(s ^ 0x5E1))
                if len(sc2) != 6 or sum(1 for x in sc2 if x[1]) != 2:
                    print(f"NG select2 {kind}/{world}/{s}")
                    ng += 1
                if "allthat" in kind_forms(kind):
                    ac2 = build_choices_allthat(d, _r.Random(s ^ 0xA77))
                    n_t = sum(1 for x in ac2 if x[1])
                    if len(ac2) != 5 or not 1 <= n_t <= 4:
                        print(f"NG allthat {kind}/{world}/{s}")
                        ng += 1
                    # ★transit は決して正解集合に入らない(punt 限定の恒常罠)
                    tr = [x for x in ac2 if "通過する ICMP" in x[0]]
                    if len(tr) != 1 or tr[0][1]:
                        print(f"NG allthat-transit {kind}/{world}/{s}")
                        ng += 1
    total = n_fix + n_cause
    print(f"gen_paper_copp selftest: NG={ng} (fix {n_fix} / cause {n_cause} / "
          f"units={sorted(units)})")
    return ng == 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    print("gen_paper_copp は gen_paper_mcq.py --shape copp から使う"
          "(単体では --selftest のみ)")
