#!/usr/bin/env python3
"""MPLS L3VPN 紙面ファミリ (BL-169) — gen_paper_mcq.py の shape=mpls 素材。

設計= problems/_drafts/PAPER-MPLS.design.md。2.1/2.2 は describe レベルなので、
器は「知識(term 群)＋読解(vrfcfg 群)」。正解の一意性は事実ベースのタグ排他と
rt_model(RT の import/export 集合→VRF 表の到達)で機械検証する。

P1(CML 非依存): term= t_roles / t_label / t_ldp / t_vpn(select/select2/allthat/match)
                 vrfcfg= v_peer(fix) / v_reach(read/select2) / v_cause(cause)
P2(PoC 後):     label= l_read / l_cause、pece= p_asoverride / p_soo
                 (exhibit は poc/mpls-paper の byte 写しが要る)

公開 API(copp/pref と同じ作法):
  KINDS / WORLDS / KIND_WORLDS / kind_forms(kind) / worlds_for(kind)
  draw(rnd, kind, world=None, form=None) -> d
  build_choices_<form>(d, rnd) -> [(text, is_correct, why)] (match は build_match)
  question_body(d, choices, form) / answer_body(d, choices, form) -> Markdown 断片
  selftest()
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rt_model  # noqa: E402

KINDS = ["t_roles", "t_label", "t_ldp", "t_vpn", "v_peer", "v_reach", "v_cause",
         "p_asoverride", "l_read", "l_cause"]
TERM_KINDS = ["t_roles", "t_label", "t_ldp", "t_vpn"]
VRF_KINDS = ["v_peer", "v_reach", "v_cause"]
PECE_KINDS = ["p_asoverride"]
LABEL_KINDS = ["l_read", "l_cause"]
WORLDS = ["w_fullmesh", "w_hubspoke", "w_extranet", "w_isolate", "w_ce_frozen", "w_pe_frozen"]
KIND_WORLDS = {
    "t_roles": ["-"], "t_label": ["-"], "t_ldp": ["-"], "t_vpn": ["-"],
    "v_peer": ["w_fullmesh", "w_hubspoke", "w_isolate"],
    "v_reach": ["w_fullmesh", "w_hubspoke", "w_extranet", "w_isolate"],
    "v_cause": ["w_fullmesh", "w_hubspoke", "w_extranet"],
    "p_asoverride": ["w_ce_frozen", "w_pe_frozen"],
    "l_read": ["-"],
    "l_cause": ["-"],
}
FORMS = {
    "t_roles": {"select", "select2", "allthat", "match"},
    "t_label": {"select", "select2", "allthat", "match"},
    "t_ldp": {"select", "select2", "allthat", "match"},
    "t_vpn": {"select", "select2", "allthat", "match"},
    "v_peer": {"fix"},
    "v_reach": {"read", "select2"},
    "v_cause": {"cause"},
    "p_asoverride": {"fix", "cause", "read"},
    "l_read": {"read"},
    "l_cause": {"cause"},
}
DIFF = {"t_roles": 2, "t_label": 2, "t_ldp": 3, "t_vpn": 3,
        "v_peer": 3, "v_reach": 3, "v_cause": 4, "p_asoverride": 4,
        "l_read": 3, "l_cause": 4}


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


# ==========================================================================
# 事実ベース(term 群)。tag → [(記述, 真偽, 偽なら反証)]
# ★選択肢に因果を書かない(BL-080)。記述は「〜である」で閉じ、理由を付けない。
# ★真偽は規格(RFC 3031/3032/5036/4364)と IOS の既定に基づく。実機依存の値は無い。
# ==========================================================================
FACTS = {
    "roles": [
        ("PE ルータは、顧客から受信した IPv4 経路に RD を付加して VPNv4 経路とし、MPLS 網へ転送するパケットにラベルを付加する。", True, ""),
        ("P ルータは、付加されたラベルに基づいてパケットを転送し、顧客の経路情報を保持しない。", True, ""),
        ("CE ルータは、MPLS のラベルを認識せず、通常の IP ルーティングによって PE ルータと接続する。", True, ""),
        ("LER は、ラベルの付加と除去を行うルータである。", True, ""),
        ("LSR は、受信したラベルを別のラベルに交換して転送するルータである。", True, ""),
        ("CE ルータは、MP-BGP を用いて PE ルータと VPNv4 経路を交換する。", False, "VPNv4 経路の交換は PE 間の MP-BGP であり、CE は通常の IPv4 経路を PE と交換する。"),
        ("P ルータは、収容する各顧客の VRF を保持する。", False, "VRF を保持するのは PE であり、P は顧客の経路情報を持たない。"),
        ("PE ルータは、P ルータとの間で LDP を有効にする必要がない。", False, "PE と P の間でもラベルの配布が要り、LDP(または他のラベル配布手段)が必要である。"),
        ("CE ルータは、収容される PE ルータと同じ VRF を構成しなければならない。", False, "VRF は PE 側の構成であり、CE に VRF は要らない。"),
    ],
    "label": [
        ("MPLS ヘッダは 32 ビットで、20 ビットのラベル、3 ビットの EXP、1 ビットの S、8 ビットの TTL から成る。", True, ""),
        ("ラベルは、レイヤ 2 ヘッダとレイヤ 3 ヘッダの間に挿入される。", True, ""),
        ("S ビットが 1 のラベルは、ラベル・スタックの最下段である。", True, ""),
        ("ラベル値 0 から 15 は予約されており、3 は暗黙 NULL(imp-null)を表す。", True, ""),
        ("ラベルは、転送等価クラス(FEC)を識別するために使用される。", True, ""),
        ("ラベルのフィールドは 32 ビットである。", False, "ラベルのフィールドは 20 ビットである(ヘッダ全体が 32 ビット)。"),
        ("S フィールドは 8 ビットである。", False, "S は 1 ビットであり、8 ビットなのは TTL である。"),
        ("ラベルは、レイヤ 3 ヘッダの後ろに付加される。", False, "ラベルはレイヤ 2 ヘッダとレイヤ 3 ヘッダの間に挿入される。"),
        ("MPLS パケットに付加できるラベルは最大 2 つである。", False, "ラベル・スタックの段数に規格上の上限はなく、L3VPN では 2 段が典型というだけである。"),
    ],
    "lsp": [
        ("LSP は、ラベルが付加されたパケットが入口の LER から出口の LER まで通過する片方向の経路である。", True, ""),
        ("PHP では、出口 LER の 1 つ手前の LSR がラベルを除去する。", True, ""),
        ("imp-null(暗黙 NULL)は、隣接に対して最終ホップの手前でラベルを除去させるために広告される値である。", True, ""),
        ("LSP は双方向の経路であり、往復で同じラベルが使用される。", False, "LSP は片方向であり、往復は別の LSP である。"),
        ("PHP は、入口の LER でラベルを除去する動作である。", False, "PHP は出口の手前の LSR がラベルを除去する動作である。"),
        ("imp-null を受信した LSR は、新しいラベルを付加して転送する。", False, "imp-null はラベルを除去して転送させる指示である。"),
    ],
    "ldp": [
        ("LDP のセッションは、TCP のポート 646 で確立される。", True, ""),
        ("LDP の隣接の発見には、UDP のポート 646 の Hello メッセージが使用される。", True, ""),
        ("LDP のルータ ID は、明示的に構成されていない場合、ループバック・インターフェイスの中で最も大きい IP アドレスが選ばれる。", True, ""),
        ("LDP の transport address は、隣接から到達可能でなければセッションが確立しない。", True, ""),
        ("mpls ldp router-id コマンドに force を付けると、構成したルータ ID が即座に反映される。", True, ""),
        ("LDP の自動構成(autoconfig)は、OSPF と IS-IS で利用できる。", True, ""),
        ("LDP は、転送等価クラスごとにラベルを配布する。", True, ""),
        ("LDP のセッションは、UDP で確立される。", False, "セッションは TCP(646)であり、UDP(646)は Hello に使われる。"),
        ("LDP のルータ ID は、ループバックの有無にかかわらず、最も大きい IP アドレスを持つ物理インターフェイスから選ばれる。", False, "ループバックがあればループバックが優先される。"),
        ("LDP のルータ ID は、重複していなければ相互の到達性は不要である。", False, "transport address への到達性が無いとセッションが確立しない。"),
        ("LDP の自動構成は、EIGRP と RIPv2 で利用できる。", False, "autoconfig は OSPF と IS-IS で利用できる。"),
        ("LDP には、MPLS トラフィック・エンジニアリングが必要である。", False, "LDP は TE を必要としない。TE のラベル配布は RSVP-TE である。"),
    ],
    "rd": [
        ("RD は 64 ビットの値であり、IPv4 プレフィックスの前に付加して 96 ビットの VPNv4 プレフィックスを作る。", True, ""),
        ("RD は、顧客間で重複する IPv4 プレフィックスを MP-BGP の中で一意に区別するために使用される。", True, ""),
        ("RD は VRF ごとに構成し、PE ルータ間で一致させる必要はない。", True, ""),
        ("RD は、経路の VRF への取り込みを制御しない。", True, ""),
        ("RD の値は、PE ルータ間で一致させておく必要がある。", False, "RD は VPNv4 プレフィックスを一意にするための値であり、PE 間で一致する必要はない。"),
        ("RD によって、受信した経路がどの VRF に取り込まれるかが決まる。", False, "取り込みを決めるのは RT(import)であり、RD ではない。"),
        ("RD は 32 ビットの値である。", False, "RD は 64 ビットである。"),
        ("RD の値は、ローカルのルータ内で RT と一致させておく必要がある。", False, "RD と RT は別の値であり、一致させる必要はない。"),
    ],
    "rt": [
        ("RT は BGP の拡張コミュニティであり、export の値が VPNv4 経路に付与され、import の値と一致する経路が VRF に取り込まれる。", True, ""),
        ("同一の VRF において、RT の import の値と export の値は異なっていてもよい。", True, ""),
        ("1 つの VRF に、複数の RT を import として構成できる。", True, ""),
        ("RT は、1 つの VRF に 1 つしか構成できない。", False, "import/export とも複数の RT を構成できる。"),
        ("RT の import の値と export の値は、同一の VRF では一致させなければならない。", False, "一致させる必要はない(ハブ&スポークでは異なる値を使う)。"),
        ("RT は、VPNv4 プレフィックスを一意にするために IPv4 プレフィックスの前に付加される。", False, "プレフィックスの前に付加されて一意にするのは RD である。RT は拡張コミュニティとして付与される。"),
    ],
    "mpbgp": [
        ("PE ルータ間の VPNv4 経路の交換には、MP-BGP の vpnv4 アドレス・ファミリが使用される。", True, ""),
        ("MP-BGP は、VPNv4 経路とともに VPN ラベルを配布する。", True, ""),
        ("send-community extended が構成されていない場合、RT が伝わらず、対向の PE の VRF に経路が取り込まれない。", True, ""),
        ("P ルータは、BGP を動作させる必要がない。", True, ""),
        ("VPNv4 経路は、LDP によって PE ルータ間で配布される。", False, "VPNv4 経路の配布は MP-BGP であり、LDP はトランスポート・ラベルの配布を行う。"),
        ("P ルータにも、vpnv4 アドレス・ファミリの BGP セッションが必要である。", False, "P は VPNv4 経路を扱わない(BGP フリー・コア)。"),
        ("MP-BGP は、顧客拠点のネットワークを集約するために使用される。", False, "MP-BGP の役割は VPNv4 経路とラベルの伝播であり、集約が目的ではない。"),
    ],
    "te": [
        ("MPLS トラフィック・エンジニアリングのラベル配布には、RSVP-TE が使用される。", True, ""),
        ("MPLS トラフィック・エンジニアリングのラベル配布には、LDP が使用される。", False, "TE のラベル配布は RSVP-TE であり、LDP は最短経路のラベル配布を行う。"),
    ],
}
# kind → (設問の主題語, 主タグ, 「真だが設問外」肢を供給するタグ)
TERM_SCOPE = {
    "t_roles": ("MPLS 網を構成するルータの役割", ["roles"], ["ldp", "te"]),
    "t_label": ("MPLS のラベルと LSP", ["label", "lsp"], ["ldp", "rd"]),
    "t_ldp": ("LDP", ["ldp"], ["te", "mpbgp"]),
    "t_vpn": ("MPLS L3VPN における RD・RT・MP-BGP", ["rd", "rt", "mpbgp"], ["ldp", "te"]),
}
# 対応付け(match)の用語セット: kind → [(用語, 説明)] (説明は事実ベースと矛盾しない短文)
MATCH_SETS = {
    "t_roles": [("PE", "ラベルの付加および除去を行い、顧客の経路を VPNv4 経路として扱う機器"),
                ("CE", "MPLS を有効にせず、ラベルを認識しない機器"),
                ("P", "付加されたラベルに基づいてパケットを転送する機器"),
                ("LSP", "ラベルが付加されたパケットが通過する片方向の経路")],
    "t_label": [("Label", "20 ビットのフィールドで、転送等価クラスを識別する値"),
                ("EXP", "3 ビットのフィールドで、QoS のクラスに使用される"),
                ("S", "1 ビットのフィールドで、スタックの最下段を示す"),
                ("TTL", "8 ビットのフィールドで、ホップごとに減算される")],
    "t_ldp": [("Hello", "UDP のポート 646 で送信され、隣接の発見に使用されるメッセージ"),
              ("セッション", "TCP のポート 646 で確立される、ラベル配布のための接続"),
              ("transport address", "セッションの確立に使用され、隣接から到達可能でなければならないアドレス"),
              ("autoconfig", "IGP のインターフェイスで LDP を自動的に有効にする機能")],
    "t_vpn": [("RD", "IPv4 プレフィックスの前に付加され、VPNv4 プレフィックスを一意にする値"),
              ("RT", "拡張コミュニティとして付与され、VRF への取り込みを制御する値"),
              ("MP-BGP", "PE 間で VPNv4 経路と VPN ラベルを伝播するプロトコル"),
              ("LDP", "転送等価クラスごとにトランスポート・ラベルを配布するプロトコル")],
}


# ==========================================================================
# 盤面の抽選
# ==========================================================================
PE_NAMES = [["PE1", "PE2", "PE3"], ["RT01", "RT02", "RT03"], ["PE-A", "PE-B", "PE-C"]]
VRF_NAMES = [("CUST_A", "CUST_B"), ("Blue", "Red"), ("VPN_ALPHA", "VPN_BETA"), ("Customer_A", "Customer_B")]
AS_POOL = [65000, 65001, 65010, 65100, 64512]
LO_POOL = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]


def draw(rnd, kind, world=None, form=None):
    """盤面 d を抽選する。term 群は事実ベースだけなので盤面は薄い。"""
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    if kind in TERM_KINDS:
        return {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    if kind in PECE_KINDS:
        return _draw_pece(rnd, kind, world, form)
    if kind in LABEL_KINDS:
        return _draw_label(rnd, kind, form)
    if world is None:
        world = rnd.choice(KIND_WORLDS[kind])
    if world not in KIND_WORLDS[kind]:
        raise ValueError(f"{kind} は world {world} を持たない")
    pes = rnd.choice(PE_NAMES)
    asn = rnd.choice(AS_POOL)
    na, nb = rnd.choice(VRF_NAMES)
    site_net = rnd.choice(["172.16", "10.10", "192.168", "172.20"])
    d = {"kind": kind, "world": world, "form": form, "diff": DIFF[kind],
         "pes": pes, "asn": asn, "na": na, "nb": nb, "net": site_net,
         "lo": {pes[i]: LO_POOL[i] for i in range(3)}}
    rt_a, rt_b = f"{asn}:{rnd.choice([100, 110, 1000])}", f"{asn}:{rnd.choice([200, 220, 2000])}"
    rt_h, rt_s = f"{asn}:{rnd.choice([300, 301, 3000])}", f"{asn}:{rnd.choice([310, 311, 3100])}"
    rt_x = f"{asn}:{rnd.choice([900, 999, 9000])}"
    d.update(rt_a=rt_a, rt_b=rt_b, rt_h=rt_h, rt_s=rt_s, rt_x=rt_x)

    def rd(site, cust):        # 規約: <AS>:<顧客番号><拠点>(例 65000:101) — 世界の「RD 規約」に使う
        return f"{asn}:{cust}0{site}"

    def net(site, cust=None):
        return f"{site_net}.{site}.0/24"
    vrfs = {}
    if world == "w_fullmesh":
        for i in (1, 2, 3):
            vrfs[f"{na}@{pes[i-1]}"] = {"pe": pes[i-1], "rd": rd(i, 1), "imp": {rt_a}, "exp": {rt_a}, "nets": [net(i)]}
        d["ask_pairs"] = "全拠点が相互に通信できる"
    elif world == "w_hubspoke":
        vrfs[f"{na}@{pes[0]}"] = {"pe": pes[0], "rd": rd(1, 1), "imp": {rt_s}, "exp": {rt_h}, "nets": [net(1)]}
        for i in (2, 3):
            vrfs[f"{na}@{pes[i-1]}"] = {"pe": pes[i-1], "rd": rd(i, 1), "imp": {rt_h}, "exp": {rt_s}, "nets": [net(i)]}
        d["hub"] = pes[0]
        d["ask_pairs"] = f"各拠点は {pes[0]} に収容されたハブ拠点とだけ通信でき、ハブ以外の拠点同士は直接には通信できない"
    elif world == "w_extranet":
        vrfs[f"{na}@{pes[0]}"] = {"pe": pes[0], "rd": rd(1, 1), "imp": {rt_a, rt_x}, "exp": {rt_a}, "nets": [net(1)]}
        vrfs[f"{nb}@{pes[0]}"] = {"pe": pes[0], "rd": rd(1, 2), "imp": {rt_b, rt_x}, "exp": {rt_b}, "nets": [net(1)]}
        vrfs[f"SHARED@{pes[1]}"] = {"pe": pes[1], "rd": rd(9, 9), "imp": {rt_a, rt_b}, "exp": {rt_x}, "nets": [f"{site_net}.99.0/24"]}
        d["ask_pairs"] = f"{na} と {nb} は互いに通信できないまま、両顧客が共有サービスの拠点とだけ通信できる"
    elif world == "w_isolate":
        vrfs[f"{na}@{pes[0]}"] = {"pe": pes[0], "rd": rd(1, 1), "imp": {rt_a}, "exp": {rt_a}, "nets": [net(1)]}
        vrfs[f"{nb}@{pes[0]}"] = {"pe": pes[0], "rd": rd(1, 2), "imp": {rt_b}, "exp": {rt_b}, "nets": [net(1)]}
        vrfs[f"{na}@{pes[1]}"] = {"pe": pes[1], "rd": rd(2, 1), "imp": {rt_a}, "exp": {rt_a}, "nets": [net(2)]}
        vrfs[f"{nb}@{pes[1]}"] = {"pe": pes[1], "rd": rd(2, 2), "imp": {rt_b}, "exp": {rt_b}, "nets": [net(2)]}
        d["ask_pairs"] = f"{na} の拠点同士、{nb} の拠点同士だけが通信でき、{na} と {nb} は同じアドレスを使っていても混ざらない"
    d["vrfs"] = vrfs
    d["want"] = _want_matrix(d)
    if kind == "v_peer":
        _draw_peer(d, rnd)
    elif kind == "v_cause":
        _draw_cause(d, rnd)
    return d


def _want_matrix(d):
    """世界が要求する到達行列(部分指定)。正しい盤面の matrix から作る(=規則の写し)。"""
    return dict(rt_model.matrix(d["vrfs"]))


def _split(name):
    return name.split("@")          # (vrf名, PE)


# --------------------------------------------------------------------------
# v_peer(fix): 片側 PE の VRF 構成を見せ、対向 PE の VRF 構成を選ばせる
# --------------------------------------------------------------------------
def _draw_peer(d, rnd):
    pes = d["pes"]
    names = [n for n in d["vrfs"] if _split(n)[1] != pes[0]]
    target = rnd.choice(names)               # 構成させる対向 PE の VRF
    d["target"] = target
    vname, tpe = _split(target)
    ref = [n for n in d["vrfs"] if _split(n)[0] == vname and _split(n)[1] == pes[0]][0]
    d["ref"] = ref                           # 提示する側(PE1)の VRF
    d["rd_rule"] = f"RD は <AS>:<顧客番号>0<拠点番号> の形式とし、拠点ごとに異なる値を用いる"


def _vrf_cli(pe, vname, rd, imps, exps):
    L = [f"{pe}(config)#vrf definition {vname}", f"{pe}(config-vrf)#rd {rd}",
         f"{pe}(config-vrf)#address-family ipv4"]
    for e in sorted(exps):
        L.append(f"{pe}(config-vrf-af)#route-target export {e}")
    for i in sorted(imps):
        L.append(f"{pe}(config-vrf-af)#route-target import {i}")
    return "\n".join(L)


def _vrf_section(pe, vrfs):
    """`show running-config | section vrf definition` の写し(その PE の全 VRF)。"""
    out = []
    for n, v in vrfs.items():
        vname, vpe = _split(n)
        if vpe != pe:
            continue
        out += [f"vrf definition {vname}", f" rd {v['rd']}", " !", " address-family ipv4"]
        out += [f"  route-target export {e}" for e in sorted(v["exp"])]
        out += [f"  route-target import {i}" for i in sorted(v["imp"])]
        out += [" exit-address-family", "!"]
    return "\n".join(out)


def peer_candidates(d):
    """(key, 適用後の vrfs, CLI 文字列)。正解= works かつ complies がちょうど 1。"""
    vname, tpe = _split(d["target"])
    cur = d["vrfs"][d["target"]]
    ref = d["vrfs"][d["ref"]]
    site = int(cur["nets"][0].split(".")[2])
    cust = cur["rd"].split(":")[1][0]
    good_rd = cur["rd"]
    cands = {
        "correct": (good_rd, set(cur["imp"]), set(cur["exp"])),
        "same_rd_as_ref": (ref["rd"], set(cur["imp"]), set(cur["exp"])),           # 機能はする・規約違反
        "swapped": (good_rd, set(cur["exp"]), set(cur["imp"])),                     # import/export 逆
        "copy_ref": (good_rd, set(ref["imp"]), set(ref["exp"])),                    # 提示側の値をそのまま写す
        "export_only": (good_rd, set(), set(cur["exp"])),                           # import 欠落
    }
    out = []
    for key, (rd, imps, exps) in cands.items():
        vv = {k: dict(v) for k, v in d["vrfs"].items()}
        vv[d["target"]] = dict(cur, rd=rd, imp=set(imps), exp=set(exps))
        out.append((key, vv, _vrf_cli(tpe, vname, rd, imps, exps)))
    return out


def _works(d, vv):
    try:
        return rt_model.complies(vv, d["want"])
    except ValueError:
        return False


def _complies(d, vv, key):
    if not _works(d, vv):
        return False
    tgt = vv[d["target"]]
    ref = d["vrfs"][d["ref"]]
    return tgt["rd"] != ref["rd"]            # RD 規約(拠点ごとに異なる値)


WHY_FIX = {
    "same_rd_as_ref": "この構成でも経路は交換されるが、RD が提示側と同じ値であり、要件の RD の規約に反する。",
    "swapped": "import と export が逆であり、提示側の export と一致する import が無い。経路は VRF に取り込まれない。",
    "copy_ref": "提示側の値をそのまま写しており、要件の到達関係(import と export の対)が成立しない。",
    "export_only": "import が構成されておらず、対向からの経路が VRF に取り込まれない。",
    "wrong_as": "import の RT の AS 部分が提示側の export と一致せず、経路が取り込まれない。",
    "other_cust": "別の顧客の RT を import しており、要件の到達関係が成立しない。",
    "import_only": "export が構成されておらず、この拠点の経路が対向の VRF に届かない。",
}


def build_choices_fix(d, rnd):
    if d["kind"] in PECE_KINDS:
        return build_choices_fix_pece(d, rnd)
    """5 択。適用後の状態が同じ候補は 1 つに畳み(フルメッシュでは swap や写しが正解と同値)、
    足りない分は誤り候補プールから補う。正解= works かつ規約適合がちょうど 1。"""
    vname, tpe = _split(d["target"])
    cur = d["vrfs"][d["target"]]
    extra = {
        "wrong_as": (cur["rd"], {x.replace(str(d["asn"]), str(d["asn"] + 1)) for x in cur["imp"]}, set(cur["exp"])),
        "other_cust": (cur["rd"], {d["rt_b"] if d["rt_b"] not in cur["imp"] else d["rt_x"]}, set(cur["exp"])),
        "import_only": (cur["rd"], set(cur["imp"]), set()),
    }
    cands = peer_candidates(d)
    for key, (rd, imps, exps) in extra.items():
        vv = {k: dict(v) for k, v in d["vrfs"].items()}
        vv[d["target"]] = dict(cur, rd=rd, imp=set(imps), exp=set(exps))
        cands.append((key, vv, _vrf_cli(tpe, vname, rd, imps, exps)))
    seen, c = set(), []
    for key, vv, cli in cands:
        tg = vv[d["target"]]
        sig = (tg["rd"], frozenset(tg["imp"]), frozenset(tg["exp"]))
        if sig in seen:
            continue
        seen.add(sig)
        ok = _complies(d, vv, key)
        c.append((cli, ok, "" if ok else WHY_FIX.get(key, "要件の到達関係が成立しない。")))
        if len(c) == 5:
            break
    if sum(1 for x in c if x[1]) != 1 or len(c) < 5:
        raise ValueError(f"v_peer: 正解数 {sum(1 for x in c if x[1])} / 候補 {len(c)}")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# v_reach(read/select2): どの拠点の経路がどの VRF 表に載るか
# --------------------------------------------------------------------------
def build_choices_read(d, rnd):
    if d["kind"] in PECE_KINDS:
        return build_choices_read_pece(d, rnd)
    if d["kind"] in LABEL_KINDS:
        return build_choices_read_label(d, rnd)
    """「PE-x の VRF y の経路表に、他の拠点の経路として載る宛先」を 1 つ選ぶ。
    宛先は拠点(VRF@PE＋プレフィックス)で表す(顧客間でプレフィックスが重複する盤面があるため)。"""
    names = list(d["vrfs"])
    target = rnd.choice(names)
    d["target"] = target
    others = [n for n in names if n != target]
    vis = {src for _p, src in rt_model.visible(d["vrfs"], target) if src != target}
    truth = tuple(n for n in others if n in vis)

    def lab(n):
        v, pe = _split(n)
        return f"{pe} の VRF {v} の拠点({d['vrfs'][n]['nets'][0]})"

    def fmt(ns):
        return "、".join(lab(n) for n in ns) if ns else "他の拠点の経路は載らない"
    cands = {truth}
    alts = [tuple(others), tuple(), tuple(n for n in others if n not in vis)]
    rdv = d["vrfs"][target]["rd"].split(":")[1][0]
    alts.append(tuple(n for n in others if d["vrfs"][n]["rd"].split(":")[1][0] == rdv))   # RD の顧客番号が同じ(誤解)
    for o in others:
        alts.append((o,))
        alts.append(tuple(n for n in truth if n != o))
        alts.append(tuple(n for n in others if n in truth or n == o))
    c = [(fmt(truth), True, "")]
    for a in alts:
        if a in cands or len(c) >= 4:
            continue
        cands.add(a)
        c.append((fmt(a), False, "import の RT と一致する export を持つ VRF の経路だけが載る(RD は取り込みに関与しない)。"))
    if len(c) < 4:
        raise ValueError("v_reach read: 錯乱肢が足りない")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# pece 群: p_asoverride(PE-CE eBGP・同一 AS 顧客)。表示は poc/mpls-paper/results-raw-04.md の byte 写し。
# ==========================================================================
BGP_STATUS_HDR = (
    "Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, \n"
    "              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, \n"
    "              x best-external, a additional-path, c RIB-compressed, \n"
    "              t secondary path, L long-lived-stale,\n"
    "Origin codes: i - IGP, e - EGP, ? - incomplete\n"
    "RPKI validation codes: V valid, I invalid, N Not found\n"
    "\n"
    "     Network          Next Hop            Metric LocPrf Weight Path")


def bgp_row(status, net, nh, metric, locprf, weight, path):
    """`show ip bgp`/`show bgp vpnv4 unicast vrf` の 1 行(列幅は実測どおり)。"""
    return f" {status:<5}{net:<17}{nh:<20}{metric:>6}{locprf:>7}{weight:>7} {path}"


def bgp_table(rid, tv, rows, rd_line=None, total=None):
    out = [f"BGP table version is {tv}, local router ID is {rid}", BGP_STATUS_HDR]
    if rd_line:
        out.append(rd_line)
    out += rows
    if total is not None:
        out += ["", f"Total number of prefixes {total}"]
    return "\n".join(out)


def bgp_summary_row(nbr, asn, rcvd, sent, tblver, updown, pfx):
    return f"{nbr:<16}{4:>1}{asn:>13}{rcvd:>8}{sent:>8}{tblver:>9}{0:>5}{0:>5} {updown:>8}{pfx:>9}"


def _draw_pece(rnd, kind, world, form):
    if world is None:
        world = rnd.choice(KIND_WORLDS[kind])
    if world not in KIND_WORLDS[kind]:
        raise ValueError(f"{kind} は world {world} を持たない")
    pes = rnd.choice(PE_NAMES)[:2]
    asn = rnd.choice(AS_POOL)
    ce_as = rnd.choice([65200, 65210, 65300, 64600])        # 同一 AS 顧客(B)
    a_as = (rnd.choice([65101, 65111, 65121]), rnd.choice([65102, 65112, 65122]))   # サイト毎 AS 顧客(A・対照)
    na, nb = rnd.choice(VRF_NAMES)
    net = rnd.choice(["172.16", "10.20", "172.30"])
    l1, l2 = rnd.choice([(11, 12), (21, 22), (31, 32)])
    d = {"kind": kind, "world": world, "form": form, "diff": DIFF[kind], "pes": pes, "asn": asn,
         "ce_as": ce_as, "a_as": a_as, "na": na, "nb": nb, "net": net,
         "lo": {pes[0]: "1.1.1.1", pes[1]: "2.2.2.2"},
         "rd_b": f"{asn}:{rnd.choice([200, 220, 2000])}",
         "ce": {"B1": f"CE-{nb}1", "B2": f"CE-{nb}2", "A1": f"CE-{na}1"},
         "link": {"B1": f"192.168.{l1}", "B2": f"192.168.{l2}", "A1": f"192.168.{l1 - 10}"},
         "lan": {"B1": f"{net}.1.0/24", "B2": f"{net}.2.0/24", "A1": f"{net}.1.0/24", "A2": f"{net}.2.0/24"},
         "rid": {"B1": "6.6.6.6", "B2": "7.7.7.7", "A1": "4.4.4.4"}}
    d["frozen"] = "CE" if world == "w_ce_frozen" else "PE"
    return d


def pece_exhibits(d):
    pe1, pe2 = d["pes"]
    nb, na = d["nb"], d["na"]
    b1ip, b2ip = d["link"]["B1"] + ".1", d["link"]["B2"] + ".1"
    pe1_b = d["link"]["B1"] + ".2"
    blocks = []
    # PE1 の VRF B の BGP 表(ローカル= CE1 から・リモート= PE2 経由)
    rows = [bgp_row("*>", d["lan"]["B1"], b1ip, "0", "", "0", f"{d['ce_as']} i"),
            bgp_row("*>i", d["lan"]["B2"], d["lo"][pe2], "0", "100", "0", f"{d['ce_as']} i")]
    blocks.append((f"{pe1}# show bgp vpnv4 unicast vrf {nb}",
                   bgp_table(d["lo"][pe1], 13, rows, rd_line=f"Route Distinguisher: {d['rd_b']} (default for vrf {nb})")))
    blocks.append((f"{pe1}# show bgp vpnv4 unicast vrf {nb} neighbors {b1ip} advertised-routes",
                   bgp_table(d["lo"][pe1], 13, [rows[1]], rd_line=f"Route Distinguisher: {d['rd_b']} (default for vrf {nb})", total=1)))
    # CE1 の要約と表
    blocks.append((f"{d['ce']['B1']}# show ip bgp summary | begin Neighbor",
                   "Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd\n"
                   + bgp_summary_row(pe1_b, d["asn"], 19, 12, 3, "00:06:53", 0)))
    blocks.append((f"{d['ce']['B1']}# show ip bgp",
                   bgp_table(d["rid"]["B1"], 3, [bgp_row("*>", d["lan"]["B1"], "0.0.0.0", "0", "", "32768", "i")])))
    # 対照: 顧客 A(サイト毎 AS)の CE は届いている
    a1ip_pe = d["link"]["A1"] + ".2"
    blocks.append((f"{d['ce']['A1']}# show ip bgp",
                   bgp_table(d["rid"]["A1"], 5, [bgp_row("*>", d["lan"]["A1"], "0.0.0.0", "0", "", "32768", "i"),
                                                 bgp_row("*>", d["lan"]["A2"], a1ip_pe, "", "", "0", f"{d['asn']} {d['a_as'][1]} i")])))
    # 構成
    blocks.append((f"{pe1}# show running-config | section address-family ipv4 vrf {nb}",
                   f" address-family ipv4 vrf {nb}\n  neighbor {b1ip} remote-as {d['ce_as']}\n  neighbor {b1ip} activate\n exit-address-family"))
    blocks.append((f"{d['ce']['B1']}# show running-config | section router bgp",
                   f"router bgp {d['ce_as']}\n bgp router-id {d['rid']['B1']}\n bgp log-neighbor-changes\n no bgp default ipv4-unicast\n"
                   f" neighbor {pe1_b} remote-as {d['asn']}\n !\n address-family ipv4\n  network {d['lan']['B1'].split('/')[0]} mask 255.255.255.0\n"
                   f"  neighbor {pe1_b} activate\n exit-address-family"))
    return blocks


PECE_CLAIMS = {
    "loop": "両拠点の CE が同一の AS 番号を使用しており、CE が受信した AS_PATH に自身の AS 番号を検出して経路を破棄している",
    "vpnv4_down": "PE 間の VPNv4 のセッションが確立していない",
    "rt": "PE の VRF の route-target が一致しておらず、対向拠点の経路が VRF に取り込まれていない",
    "rmap": "PE から CE への広告が、route-map によって止められている",
    "ebgp_down": "PE と CE の間の eBGP のセッションが確立していない",
    "nexthop": "対向拠点の経路の next-hop が到達不能であり、経路が無効になっている",
}
PECE_REFUTE = {
    "vpnv4_down": "PE の VRF の表に、対向 PE を next-hop とする経路(*>i)が存在している。",
    "rt": "対向拠点の経路は PE の VRF の表に取り込まれており、advertised-routes にも載っている。",
    "rmap": "示されている構成に route-map は無く、advertised-routes に経路が載っている。",
    "ebgp_down": "CE の要約で PE とのセッションは確立しており(Up/Down に時間)、受信数が 0 なだけである。",
    "nexthop": "PE の表で当該の経路は valid かつ best であり、CE へ広告されている。",
}


def build_choices_cause_pece(d, rnd):
    c = [(PECE_CLAIMS["loop"], True, "")]
    for k in rnd.sample([k for k in PECE_CLAIMS if k != "loop"], 4):
        c.append((PECE_CLAIMS[k], False, PECE_REFUTE[k]))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def pece_fix_candidates(d):
    pe1, pe2 = d["pes"]
    b1ip, b2ip = d["link"]["B1"] + ".1", d["link"]["B2"] + ".1"
    pe1_b, pe2_b = d["link"]["B1"] + ".2", d["link"]["B2"] + ".2"
    nb = d["nb"]
    return {
        "pe_override": (f"{pe1}(config)#router bgp {d['asn']}\n{pe1}(config-router)#address-family ipv4 vrf {nb}\n{pe1}(config-router-af)#neighbor {b1ip} as-override\n"
                        f"{pe2}(config)#router bgp {d['asn']}\n{pe2}(config-router)#address-family ipv4 vrf {nb}\n{pe2}(config-router-af)#neighbor {b2ip} as-override",
                        True, "PE"),
        "ce_allowas": (f"{d['ce']['B1']}(config)#router bgp {d['ce_as']}\n{d['ce']['B1']}(config-router)#address-family ipv4\n{d['ce']['B1']}(config-router-af)#neighbor {pe1_b} allowas-in\n"
                       f"{d['ce']['B2']}(config)#router bgp {d['ce_as']}\n{d['ce']['B2']}(config-router)#address-family ipv4\n{d['ce']['B2']}(config-router-af)#neighbor {pe2_b} allowas-in",
                       True, "CE"),
        "pe_allowas": (f"{pe1}(config)#router bgp {d['asn']}\n{pe1}(config-router)#address-family ipv4 vrf {nb}\n{pe1}(config-router-af)#neighbor {b1ip} allowas-in\n"
                       f"{pe2}(config)#router bgp {d['asn']}\n{pe2}(config-router)#address-family ipv4 vrf {nb}\n{pe2}(config-router-af)#neighbor {b2ip} allowas-in",
                       False, "PE"),
        "ce_override": (f"{d['ce']['B1']}(config)#router bgp {d['ce_as']}\n{d['ce']['B1']}(config-router)#address-family ipv4\n{d['ce']['B1']}(config-router-af)#neighbor {pe1_b} as-override\n"
                        f"{d['ce']['B2']}(config)#router bgp {d['ce_as']}\n{d['ce']['B2']}(config-router)#address-family ipv4\n{d['ce']['B2']}(config-router-af)#neighbor {pe2_b} as-override",
                        False, "CE"),
        "ce_multihop": (f"{d['ce']['B1']}(config)#router bgp {d['ce_as']}\n{d['ce']['B1']}(config-router)#neighbor {pe1_b} ebgp-multihop 2\n"
                        f"{d['ce']['B2']}(config)#router bgp {d['ce_as']}\n{d['ce']['B2']}(config-router)#neighbor {pe2_b} ebgp-multihop 2",
                        False, "CE"),
    }


PECE_WHY = {
    "pe_override": "as-override は機能するが、PE 側の構成変更であり、要件に反する。",
    "ce_allowas": "allowas-in は機能するが、CE 側の構成変更であり、要件に反する。",
    "pe_allowas": "PE が CE から受信する AS_PATH に PE 自身の AS は含まれておらず、PE 側の allowas-in は事象に無関係である。",
    "ce_override": "as-override は広告する側(PE)で対向の AS を置換する機能であり、CE 側に構成しても CE の受信には効かない。",
    "ce_multihop": "セッションは確立しており、ebgp-multihop は経路の受け入れとは無関係である。",
}


def build_choices_fix_pece(d, rnd):
    cands = pece_fix_candidates(d)
    c = []
    for key, (cli, works, side) in cands.items():
        ok = works and side != d["frozen"]
        c.append((cli, ok, "" if ok else PECE_WHY[key]))
    if sum(1 for x in c if x[1]) != 1:
        raise ValueError("p_asoverride fix: 正解数")
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_read_pece(d, rnd):
    asn, ce = d["asn"], d["ce_as"]
    if d["frozen"] == "CE":         # as-override が適用された後
        truth = f"{asn} {asn}"
        alts = [(f"{asn} {ce}", "as-override は CE の AS を PE の AS に置換するため、CE の AS は残らない。"),
                (f"{ce}", "PE の AS は必ず AS_PATH に前置される。"),
                (f"{asn}", "対向拠点の CE の AS が PE の AS に置換されて 1 つ増えるため、AS 番号は 2 つ並ぶ。")]
    else:                            # allowas-in が適用された後
        truth = f"{asn} {ce}"
        alts = [(f"{asn} {asn}", "allowas-in は受信側で自 AS の存在を許容するだけで、AS_PATH は書き換えられない。"),
                (f"{ce}", "PE の AS は必ず AS_PATH に前置される。"),
                (f"{asn}", "対向拠点の CE の AS はそのまま残る。")]
    c = [(truth, True, "")] + [(a, False, w) for a, w in alts]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _question_pece(d, choices, form):
    pe1, pe2 = d["pes"]
    nb, na = d["nb"], d["na"]
    frozen = ("顧客の CE ルータの構成は、顧客の管理下にあり、変更することができません。" if d["frozen"] == "CE"
              else f"事業者の PE ルータのネイバー・ポリシーは、変更することができません。")
    before = [f"あなたの組織は、AS {d['asn']} の MPLS L3VPN 網を運用しています。顧客 {nb} は、2 つの拠点を、"
              f"いずれも AS {d['ce_as']} の CE ルータで、{pe1} および {pe2} に eBGP で接続しています。"
              f"顧客 {na} は、拠点ごとに異なる AS({d['a_as'][0]} と {d['a_as'][1]})の CE ルータで接続しています。",
              "", f"- {frozen}", ""]
    for cmd, body in pece_exhibits(d):
        before += ["```", cmd, body, "```"]
    before += ["", f"顧客 {nb} の拠点間で通信できない、ということが、報告されています。顧客 {na} の拠点間は、正常に通信できています。"]
    if form == "cause":
        ask = "示されている出力および構成に基づいて、この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    elif form == "fix":
        ask = "示されている要件のもとで、顧客の拠点間の通信を回復させるために適用されなければならない構成は、次のうちどれですか。(1つを選択してください)"
        ch_md = "\n\n".join(f"**{'ABCDEFG'[i]}.**\n\n```\n{t}\n```" for i, (t, _, _) in enumerate(choices))
    else:
        applied = (f"{pe1} および {pe2} の VRF {nb} のネイバーに as-override" if d["frozen"] == "CE"
                   else f"顧客 {nb} の両拠点の CE ルータに allowas-in")
        ask = (f"{applied} が構成され、通信が回復しました。このとき、{d['ce']['B1']} が受信する {d['lan']['B2']} の "
               "AS_PATH は、次のうちどれですか。(1つを選択してください)")
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    return "\n".join(before), ask, ch_md, ""


# ==========================================================================
# label 群: l_read / l_cause。表示は poc/mpls-paper/results-raw.md(M1〜M5)の byte 写し。
# 盤面= PE1 — P — PE2 の直線コア(IOL・Ethernet0/x)。ラベルは 16 から順に割り当てる。
# ==========================================================================
LFIB_HDR = ("Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop    \n"
            "Label      Label      or Tunnel Id     Switched      interface              ")


def lfib_row(local, outg, prefix, nbytes, oif, nh):
    if len(prefix) >= 17:                     # 実機は長いプレフィックスを折り返す
        return f"{local:<11}{outg:<11}{prefix}   \\\n" + " " * 39 + f"{nbytes:<14}{oif}"
    return (f"{local:<11}{outg:<11}{prefix:<17}{nbytes:<14}{oif:<11}{nh}").rstrip()


def _draw_label(rnd, kind, form):
    pes = rnd.choice(PE_NAMES)
    pe1, pe2 = pes[0], pes[2] if rnd.random() < 0.5 else pes[1]
    pname = rnd.choice(["P1", "P", "RT02", "CORE1"])
    if pname in (pe1, pe2):
        pname = "P1"
    asn = rnd.choice(AS_POOL)
    o2 = rnd.choice([1, 8, 10, 20])                     # コアリンクの第 2 オクテット
    lo_style = rnd.choice(["n.n.n.n", "10.255.0.n"])
    def lo(n):
        return f"{n}.{n}.{n}.{n}" if lo_style == "n.n.n.n" else f"10.255.0.{n}"
    na = rnd.choice(VRF_NAMES)[0]
    net = rnd.choice(["172.16", "10.20", "172.30"])
    l_tr = rnd.choice([17, 18, 19])                     # P が PE2 のループバックに割り当てる(トランスポート)ラベル
    l_vpn = rnd.choice([20, 21, 22, 23])                # PE2 が顧客経路に割り当てる VPN ラベル
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind], "pe1": pe1, "p": pname, "pe2": pe2,
         "asn": asn, "lo": {pe1: lo(1), pname: lo(2), pe2: lo(3)},
         "l12": f"10.{o2}.12", "l23": f"10.{o2}.23",       # PE1-P / P-PE2 の /30(PE1=.1,P=.2 / P=.1,PE2=.2)
         "vrf": na, "lan1": f"{net}.1.0/24", "lan2": f"{net}.2.0/24",
         "ce1": "192.168.1", "ce2": "192.168.2",           # PE-CE /30(PE=.2, CE=.1)
         "l_tr": l_tr, "l_vpn": l_vpn}
    if kind == "l_read":
        d["sub"] = rnd.choice(["pop_meaning", "stack", "php_trace", "impnull"])
    else:
        d["sub"] = rnd.choice(["lsp_hole", "transport_unreach"])
    return d


def label_exhibits(d, broken=None):
    """(コマンド, 出力) のリスト。broken= None / "lsp_hole" / "transport_unreach"。"""
    pe1, p, pe2, v = d["pe1"], d["p"], d["pe2"], d["vrf"]
    lo1, lop, lo2 = d["lo"][pe1], d["lo"][p], d["lo"][pe2]
    l12, l23 = d["l12"], d["l23"]
    tr, vpn = d["l_tr"], d["l_vpn"]
    ex = []
    # PE1 の LFIB。lsp_hole では PE1 側は不変(M4 実測)。transport_unreach では PE1 と P の
    # LDP セッションが無いので PE1 は remote binding を持たず、コア宛はすべて No Label(M4 の類推)。
    if broken == "transport_unreach":
        rows = [lfib_row("16", "No Label", f"{lop}/32", "0", "Et0/0", f"{l12}.2"),
                lfib_row("17", "No Label", f"{l23}.0/30", "0", "Et0/0", f"{l12}.2"),
                lfib_row("18", "No Label", f"{lo2}/32", "0", "Et0/0", f"{l12}.2")]
    else:
        rows = [lfib_row("16", "Pop Label", f"{lop}/32", "0", "Et0/0", f"{l12}.2"),
                lfib_row("17", "Pop Label", f"{l23}.0/30", "0", "Et0/0", f"{l12}.2"),
                lfib_row("18", str(tr), f"{lo2}/32", "0", "Et0/0", f"{l12}.2")]
    rows += [
            lfib_row("19", "No Label", f"{d['lan1']}[V]", "570", "Et0/1", f"{d['ce1']}.1"),
            lfib_row("20", "No Label", f"{d['ce1']}.0/30[V]", "0", f"aggregate/{v}", "")]
    ex.append((f"{pe1}# show mpls forwarding-table", LFIB_HDR + "\n" + "\n".join(rows)))
    # P の LFIB
    if broken == "lsp_hole":
        prow = [lfib_row("16", "Pop Label", f"{lo1}/32", "4579", "Et0/0", f"{l12}.1"),
                lfib_row(str(tr), "No Label", f"{lo2}/32", "2494", "Et0/1", f"{l23}.2")]
    elif broken == "transport_unreach":
        prow = [lfib_row("16", "No Label", f"{lo1}/32", "0", "Et0/0", f"{l12}.1"),
                lfib_row(str(tr), "Pop Label", f"{lo2}/32", "2776", "Et0/1", f"{l23}.2")]
    else:
        prow = [lfib_row("16", "Pop Label", f"{lo1}/32", "3176", "Et0/0", f"{l12}.1"),
                lfib_row(str(tr), "Pop Label", f"{lo2}/32", "2776", "Et0/1", f"{l23}.2")]
    ex.append((f"{p}# show mpls forwarding-table", LFIB_HDR + "\n" + "\n".join(prow)))
    if broken is None:
        ex.append((f"{pe1}# show mpls ldp bindings",
                   f"  lib entry: {lo1}/32, rev 2\n\tlocal binding:  label: imp-null\n\tremote binding: lsr: {lop}:0, label: 16\n"
                   f"  lib entry: {lop}/32, rev 6\n\tlocal binding:  label: 16\n\tremote binding: lsr: {lop}:0, label: imp-null\n"
                   f"  lib entry: {lo2}/32, rev 10\n\tlocal binding:  label: 18\n\tremote binding: lsr: {lop}:0, label: {tr}\n"
                   f"  lib entry: {l12}.0/30, rev 4\n\tlocal binding:  label: imp-null\n\tremote binding: lsr: {lop}:0, label: imp-null\n"
                   f"  lib entry: {l23}.0/30, rev 8\n\tlocal binding:  label: 17\n\tremote binding: lsr: {lop}:0, label: imp-null"))
        ex.append((f"{pe1}# traceroute vrf {v} {d['lan2'].replace('.0/24', '.1')} source {d['ce1']}.2 numeric timeout 1",
                   f"Type escape sequence to abort.\nTracing the route to {d['lan2'].replace('.0/24', '.1')}\nVRF info: (vrf in name/id, vrf out name/id)\n"
                   f"  1 {l12}.2 [MPLS: Labels {tr}/{vpn} Exp 0] 1 msec 1 msec 0 msec\n"
                   f"  2 {d['ce2']}.2 [MPLS: Label {vpn} Exp 0] 1 msec 1 msec 0 msec\n"
                   f"  3 {d['ce2']}.1 1 msec *  2 msec"))
        return ex
    # 故障時の共通証拠: VRF 経路はある・IGP も正常・VPN の ping だけ落ちる
    ex.append((f"{pe1}# show ip route vrf {v} | include {d['lan2'].split('/')[0][:-2]}",
               f"B        {d['lan2'].split('/')[0]} [200/11] via {lo2}, 00:03:37"))
    ex.append((f"{pe1}# show ip route {lo2}",
               f"Routing entry for {lo2}/32\n  Known via \"ospf 1\", distance 110, metric 21, type intra area\n"
               f"  Last update from {l12}.2 on Ethernet0/0, 00:12:25 ago\n  Routing Descriptor Blocks:\n"
               f"  * {l12}.2, from {lo2}, 00:12:25 ago, via Ethernet0/0\n      Route metric is 21, traffic share count is 1"))
    ex.append((f"{pe1}# ping vrf {v} {d['lan2'].replace('.0/24', '.1')} source {d['ce1']}.2 repeat 3",
               f"Type escape sequence to abort.\nSending 3, 100-byte ICMP Echos to {d['lan2'].replace('.0/24', '.1')}, timeout is 2 seconds:\n"
               f"Packet sent with a source address of {d['ce1']}.2 \n...\nSuccess rate is 0 percent (0/3)"))
    if broken == "lsp_hole":
        ex.append((f"{p}# show mpls interfaces",
                   "Interface              IP            Tunnel   BGP Static Operational\nEthernet0/0            Yes (ldp)     No       No  No     Yes"))
        ex.append((f"{p}# show mpls ldp neighbor",
                   f"    Peer LDP Ident: {lo1}:0; Local LDP Ident {lop}:0\n\tTCP connection: {lo1}.646 - {lop}.57597\n"
                   f"\tState: Oper; Msgs sent/rcvd: 22/23; Downstream\n\tUp time: 00:12:34\n\tLDP discovery sources:\n"
                   f"\t  Ethernet0/0, Src IP addr: {l12}.1\n        Addresses bound to peer LDP Ident:\n          {l12}.1       {lo1}"))
        ex.append((f"{pe2}# show mpls ldp neighbor", ""))
    else:
        ex.append((f"{pe1}# show mpls ldp neighbor", ""))
        ex.append((f"{p}# show mpls ldp discovery detail",
                   f" Local LDP Identifier:\n    {lop}:0\n    Discovery Sources:\n    Interfaces:\n"
                   f"\tEthernet0/0 (ldp): xmit/recv\n\t    Enabled: Interface config\n\t    Hello interval: 5000 ms; Transport IP addr: {lop}\n"
                   f"\t    LDP Id: 10.99.1.1:0; no route to transport addr\n\t      Src IP addr: {l12}.1; Transport IP addr: 10.99.1.1\n"
                   f"\t      Hold time: 15 sec; Proposed local/peer: 15/15 sec\n\t      Password: not required, none, in use\n            Clients: IPv4, mLDP \n"
                   f"\tEthernet0/1 (ldp): xmit/recv\n\t    Enabled: Interface config\n\t    Hello interval: 5000 ms; Transport IP addr: {lop}\n"
                   f"\t    LDP Id: {lo2}:0\n\t      Src IP addr: {l23}.2; Transport IP addr: {lo2}\n"
                   f"\t      Hold time: 15 sec; Proposed local/peer: 15/15 sec\n\t      Reachable via {lo2}/32\n"
                   f"\t      Password: not required, none, in use\n            Clients: IPv4, mLDP"))
        ex.append((f"{pe1}# show running-config | include mpls ldp router-id|^interface Loopback9|ip address 10.99",
                   "interface Loopback9\n ip address 10.99.1.1 255.255.255.255\nmpls ldp router-id Loopback9 force"))
        ex.append((f"{pe1}# show ip ospf interface brief",
                   "Interface    PID   Area            IP Address/Mask    Cost  State Nbrs F/C\n"
                   f"Lo0          1     0               {lo1}/32          1     LOOP  0/0\n"
                   f"Et0/0        1     0               {l12}.1/30       10    P2P   1/1"))
    return ex


def build_choices_read_label(d, rnd):
    pe1, p, pe2 = d["pe1"], d["p"], d["pe2"]
    tr, vpn, lo2 = d["l_tr"], d["l_vpn"], d["lo"][pe2]
    sub = d["sub"]
    if sub == "pop_meaning":
        d["ask_text"] = f"{p} の LFIB において、{lo2}/32 の Outgoing Label が Pop Label と表示されていることの意味は、次のうちどれですか。"
        c = [(f"{pe2} が自身のループバックに対して imp-null を広告しており、{p} が最終ホップの手前としてラベルを除去して転送する。", True, ""),
             (f"{p} に {lo2}/32 のラベルが割り当てられておらず、{pe2} との LDP セッションが確立していない。", False, "セッションが無い場合の表示は No Label であり、Pop Label は正常な PHP の表示である。"),
             (f"{p} が入口の LER として、パケットに新しいラベルを付加して転送する。", False, "ラベルの付加は入口 PE(LER)の動作であり、P は行わない。"),
             (f"{p} が受信したラベルを {tr} に交換して転送する。", False, "交換(swap)の場合、Outgoing Label には数値のラベルが表示される。")]
    elif sub == "stack":
        d["ask_text"] = (f"{pe1} に接続された顧客の拠点から、{pe2} に接続された拠点 {d['lan2']} 宛のパケットが {pe1} から送出されるときの"
                         "ラベル・スタックとして正しいものは、次のうちどれですか。")
        c = [(f"外側(上段)が {tr}、内側(下段)が {vpn} の 2 段", True, ""),
             (f"外側(上段)が {vpn}、内側(下段)が {tr} の 2 段", False, "トランスポート・ラベル(LDP)が外側、VPN ラベル(MP-BGP)が内側である。"),
             (f"{tr} の 1 段", False, "VPN ラベルが無いと出口 PE は VRF を判別できない。"),
             (f"18 と {vpn} の 2 段", False, f"18 は {pe1} が自身で割り当てた Local Label であり、送出には隣接 {p} から受け取った {tr} を使う。")]
    elif sub == "php_trace":
        d["ask_text"] = (f"traceroute の 1 ホップ目には 2 つのラベル、2 ホップ目には 1 つのラベルが表示されています。"
                         "2 ホップ目でラベルが 1 つになっている理由として正しいものは、次のうちどれですか。")
        c = [(f"{p} が PHP によってトランスポート・ラベル {tr} を除去し、VPN ラベル {vpn} だけを {pe2} に渡している。", True, ""),
             (f"{pe2} が VPN ラベルを除去し、トランスポート・ラベルだけが残っている。", False, f"2 ホップ目に残っているのは VPN ラベル {vpn} であり、除去されたのはトランスポート・ラベルである。"),
             (f"{p} と {pe2} の間で LDP が無効であり、ラベルが 1 つ失われている。", False, "LDP が無効なら VPN の通信は成立せず、traceroute は完了しない。"),
             (f"{pe1} が 2 ホップ目のパケットには 1 つのラベルしか付加していない。", False, "入口 PE は経路上のすべてのパケットに同じスタックを付加する。")]
    else:
        d["ask_text"] = (f"{pe1} の `show mpls ldp bindings` において、{d['lo'][pe1]}/32 の local binding が imp-null と表示されていることの意味は、"
                         "次のうちどれですか。")
        c = [(f"{pe1} 自身のループバック宛の経路であり、隣接に対して最終ホップの手前でラベルを除去するよう要求している。", True, ""),
             (f"{pe1} が {d['lo'][pe1]}/32 に対してラベルの割り当てに失敗している。", False, "imp-null(ラベル値 3)は正常な暗黙 NULL の広告である。"),
             (f"{p} が {d['lo'][pe1]}/32 に対して imp-null を割り当てて {pe1} に広告している。", False, "local binding は自身の割り当てであり、remote binding が隣接からの受信である。"),
             (f"{d['lo'][pe1]}/32 が LDP の配布対象から除外されている。", False, "配布対象外なら lib entry 自体が現れない。")]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


LABEL_CAUSE = {
    "lsp_hole": (f"P ルータの出口 PE 向けインターフェイスで LDP が有効になっておらず、出口 PE のループバック宛のラベルが無く、LSP が途切れている",
                 None),
    "transport_unreach": ("入口 PE の LDP ルータ ID(transport address)が IGP で広告されておらず、隣接がセッションを確立できない",
                          None),
}
LABEL_DISTRACT = [
    ("PE 間の OSPF の隣接が確立しておらず、出口 PE のループバックへの経路が無い", "示されている出力のとおり、出口 PE のループバックは OSPF で学習されている。"),
    ("PE 間の VPNv4 のセッションが確立しておらず、顧客の経路が交換されていない", "示されている出力のとおり、顧客の経路は VRF の経路表に BGP で載っている。"),
    ("VRF の route-target が一致しておらず、対向拠点の経路が VRF に取り込まれていない", "対向拠点の経路は VRF の経路表に存在している。"),
    ("LDP のパスワードが隣接間で一致していない", "discovery の出力に Password: not required とあり、パスワードは構成されていない。"),
    ("顧客向けインターフェイスで MPLS が有効になっていない", "PE と CE の間はラベルを使わない IP 転送であり、MPLS を有効にする必要はない。"),
]


def build_choices_cause_label(d, rnd):
    sub = d["sub"]
    truth = LABEL_CAUSE[sub][0].replace("P ルータ", d["p"]).replace("入口 PE", d["pe1"]).replace("出口 PE", d["pe2"])
    other = [k for k in LABEL_CAUSE if k != sub][0]
    alt = LABEL_CAUSE[other][0].replace("P ルータ", d["p"]).replace("入口 PE", d["pe1"]).replace("出口 PE", d["pe2"])
    alt_why = ("discovery の出力に「no route to transport addr」は無く、LDP のセッション自体は確立している。" if sub == "lsp_hole"
               else f"{d['p']} の LFIB では出口 PE のループバックに Pop Label が付いており、その IF で LDP は有効である。")
    c = [(truth, True, ""), (alt, False, alt_why)]
    for txt, why in rnd.sample(LABEL_DISTRACT, 3):
        c.append((txt.replace("出口 PE", d["pe2"]), False, why))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def _question_label(d, choices, form):
    pe1, p, pe2, v = d["pe1"], d["p"], d["pe2"], d["vrf"]
    before = [f"あなたの組織は、AS {d['asn']} の MPLS L3VPN 網を運用しています。コアは {pe1} — {p} — {pe2} の直線で、"
              f"顧客 {v} の拠点は {pe1} と {pe2} に収容されています。IGP は OSPF、ラベルの配布は LDP です。", ""]
    if form == "read":
        for cmd, body in label_exhibits(d):
            before += ["```", cmd, body, "```"]
        ask = d["ask_text"] + "(1つを選択してください)"
    else:
        for cmd, body in label_exhibits(d, broken=d["sub"]):
            before += ["```", cmd, body, "```"]
        before += ["", f"{pe1} に収容されている顧客 {v} の拠点から、{pe2} に収容されている拠点 {d['lan2']} へ通信できない、"
                   f"ということが、報告されています。コアのルータ間の IP の到達性には、問題がありません。"]
        ask = "示されている出力に基づいて、この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
    ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
    return "\n".join(before), ask, ch_md, ""


def build_choices_select2(d, rnd):
    """(v_reach) 相互に通信できる拠点の組を 2 つ選ぶ / (term) 正しい記述を 2 つ。"""
    if d["kind"] in TERM_KINDS:
        return _term_choices(d, rnd, n_true=2, n_total=5)
    names = list(d["vrfs"])
    m = rt_model.matrix(d["vrfs"])
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]

    def lab(n):
        v, pe = _split(n)
        return f"{pe} の VRF {v} の拠点"
    # 肯定文(通信できる)と否定文(通信できない)を混ぜ、真がちょうど 2 になるよう組む
    trues, falses = [], []
    for a, b in pairs:
        both = m[(a, b)] and m[(b, a)]
        pos = f"{lab(a)} と {lab(b)} は、相互に通信できる"
        neg = f"{lab(a)} と {lab(b)} は、相互には通信できない"
        if both:
            trues.append((pos, ""))
            falses.append((neg, "一方の export が他方の import と一致しており、双方向に通信できる。"))
        else:
            trues.append((neg, ""))
            falses.append((pos, "一方の export と他方の import が一致せず、双方向には通信できない。"))
    if len(trues) < 2 or len(falses) < 3:
        raise ValueError("v_reach select2: 組が足りない")
    c = [(t, True, "") for t, _ in rnd.sample(trues, 2)]
    c += [(t, False, w) for t, w in rnd.sample(falses, 3)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# v_cause(cause): 片方向だけ落ちる盤面を作り、原因を選ばせる
# --------------------------------------------------------------------------
CAUSE_CLAIMS = {
    "imp_wrong": "被疑の PE の VRF の route-target import が、対向の VRF の export と一致していない",
    "exp_wrong": "対向の PE の VRF の route-target export が、被疑の VRF の import と一致していない",
    "rd_mismatch": "PE 間で VRF の RD が一致していない",
    "no_extcomm": "vpnv4 のネイバーに send-community extended が構成されていない",
    "no_activate": "vpnv4 のアドレス・ファミリでネイバーが activate されていない",
    "no_redist": "被疑の PE の VRF のアドレス・ファミリで、顧客の経路が BGP に取り込まれていない",
    "ldp_hole": "コアの一部のインターフェイスで LDP が有効になっておらず、LSP が途切れている",
}
CAUSE_REFUTE = {
    "rd_mismatch": "RD は VPNv4 プレフィックスを一意にする値であり、PE 間で一致させる必要はない。",
    "no_extcomm": "示されている構成のとおり、vpnv4 のネイバーには send-community extended が構成されている。",
    "no_activate": "示されている構成のとおり、vpnv4 のネイバーは activate されている。",
    "no_redist": "示されている構成のとおり、VRF のアドレス・ファミリで経路は BGP に取り込まれている。",
    "ldp_hole": "同じ PE 間で他の VRF(または他方向)の通信が成立しており、LSP は途切れていない。",
}


def _draw_cause(d, rnd):
    """片方向だけ落ちる盤面。★どちら側の値が誤りかが一意に読めるよう、壊していない側の
    値が**第三の VRF によって裏付けられる**組だけを採る(例: peer の export は他の VRF も
    import して到達できている → 誤りは victim の import)。裏付けの無い組は捨てる。"""
    names = list(d["vrfs"])
    m = rt_model.matrix(d["vrfs"])
    cands = []
    for src in names:
        for dst in names:
            if src == dst or _split(src)[1] == _split(dst)[1] or not (m[(src, dst)] and m[(dst, src)]):
                continue
            # imp_wrong: dst の import を壊す。src の export を他の VRF も受け取れていること
            if any(w not in (src, dst) and m[(src, w)] for w in names):
                cands.append(("imp_wrong", src, dst))
            # exp_wrong: src の export を壊す。dst が他の VRF の経路は受け取れていること
            if any(w not in (src, dst) and m[(w, dst)] for w in names):
                cands.append(("exp_wrong", src, dst))
    if not cands:
        raise ValueError("v_cause: 裏付けのある組が無い")
    d["cause"], src, dst = rnd.choice(cands)
    broken = {k: dict(v, imp=set(v["imp"]), exp=set(v["exp"])) for k, v in d["vrfs"].items()}
    wrong = f"{d['asn']}:{rnd.choice([555, 777, 888])}"
    if d["cause"] == "imp_wrong":
        broken[dst]["imp"] = {wrong}
    else:
        broken[src]["exp"] = {wrong}
    d["broken"] = broken
    d["victim"], d["peer"] = dst, src
    mb = rt_model.matrix(broken)
    # 症状文に添える「動いている通信」(裏付け)
    if d["cause"] == "imp_wrong":
        d["witness"] = [w for w in names if w not in (src, dst) and mb[(src, w)]]
    else:
        d["witness"] = [w for w in names if w not in (src, dst) and mb[(w, dst)]]


def build_choices_cause(d, rnd):
    if d["kind"] in PECE_KINDS:
        return build_choices_cause_pece(d, rnd)
    if d["kind"] in LABEL_KINDS:
        return build_choices_cause_label(d, rnd)
    truth = d["cause"]
    others = [k for k in CAUSE_CLAIMS if k not in ("imp_wrong", "exp_wrong")]
    c = [(CAUSE_CLAIMS[truth], True, "")]
    # もう片方の import/export 仮説は「他の VRF が同じ値で到達できている」事実で否定できる
    alt = "exp_wrong" if truth == "imp_wrong" else "imp_wrong"
    why = ("対向の VRF の export は、他の拠点の VRF が同じ値を import して到達できており、誤っていない。"
           if truth == "imp_wrong" else
           "被疑の VRF の import は、他の拠点の経路を同じ値で受け取れており、誤っていない。")
    c.append((CAUSE_CLAIMS[alt], False, why))
    for k in rnd.sample(others, 3):
        c.append((CAUSE_CLAIMS[k], False, CAUSE_REFUTE[k]))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# --------------------------------------------------------------------------
# term 群: select / select2 / allthat / match
# --------------------------------------------------------------------------
def _term_choices(d, rnd, n_true, n_total, offscope=True):
    subject, tags, off_tags = TERM_SCOPE[d["kind"]]
    pool_t = [(t, w) for tag in tags for t, tv, w in FACTS[tag] if tv]
    pool_f = [(t, w) for tag in tags for t, tv, w in FACTS[tag] if not tv]
    trues = rnd.sample(pool_t, n_true)
    c = [(t, True, "") for t, _ in trues]
    n_false = n_total - n_true
    if offscope and n_false >= 3:
        # 「真だが設問に答えていない」肢を 1 つ(別タグの真の記述)
        off = [(t, w) for tag in off_tags for t, tv, w in FACTS[tag] if tv]
        t, _ = rnd.choice(off)
        c.append((t, False, f"記述そのものは正しいが、設問({subject})についての記述ではない。"))
        n_false -= 1
    for t, w in rnd.sample(pool_f, n_false):
        c.append((t, False, w))
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_select(d, rnd):
    return _term_choices(d, rnd, n_true=1, n_total=4)


def build_choices_allthat(d, rnd):
    """数非明示。正解数は 1〜4 を抽選(選択肢 5)。"""
    n_true = rnd.choice([1, 2, 2, 3, 3, 4])
    return _term_choices(d, rnd, n_true=n_true, n_total=5, offscope=(n_true <= 2))


def build_match(d, rnd):
    """[(丸数字, 用語)], [(記号, 説明)], {丸数字: 記号}。"""
    items = list(MATCH_SETS[d["kind"]])
    rnd.shuffle(items)
    terms = [("①②③④"[i], t) for i, (t, _) in enumerate(items)]
    descs = list(enumerate(items))
    rnd.shuffle(descs)
    letters = "ABCD"
    choices = [(letters[j], items[i][1]) for j, (i, _) in enumerate(descs)]
    ans = {}
    for j, (i, _) in enumerate(descs):
        ans["①②③④"[i]] = letters[j]
    return terms, choices, dict(sorted(ans.items()))


# ==========================================================================
# Markdown(設問本文と解答本文)。gen_paper_mcq 側がヘッダと見出しを付ける。
# ==========================================================================
ASK = {
    "select": "{subject}について、正しく述べられているものは、次のうちどれですか。(1つを選択してください)",
    "select2": "{subject}について、正しく述べられているものを、次のうちから 2 つ選択してください。",
    "allthat": "{subject}について、正しく述べられているものを、すべて選んでください。",
    "match": "{subject}について、左側の①〜④の用語に対応する説明を、右側の A〜D から選択してください。",
}


def _bgp_section(d, pe):
    """vpnv4 と各 VRF の AF が正しく構成されていることを示す(cause の反証の根拠)。"""
    lo = d["lo"]
    L = [f"router bgp {d['asn']}", f" bgp router-id {lo[pe]}", " no bgp default ipv4-unicast"]
    for o in d["pes"]:
        if o != pe:
            L += [f" neighbor {lo[o]} remote-as {d['asn']}", f" neighbor {lo[o]} update-source Loopback0"]
    L += [" !", " address-family vpnv4"]
    for o in d["pes"]:
        if o != pe:
            L += [f"  neighbor {lo[o]} activate", f"  neighbor {lo[o]} send-community extended"]
    L += [" exit-address-family"]
    for n, v in d["vrfs"].items():
        vname, vpe = _split(n)
        if vpe == pe:
            L += [" !", f" address-family ipv4 vrf {vname}", "  redistribute connected", "  redistribute static", " exit-address-family"]
    return "\n".join(L)


def question_body(d, choices, form):
    """## 設問 の前に置く本文(シナリオ・出力)と、設問文・選択肢の Markdown を返す。
    戻り= (before_ask, ask_text, choices_md, terms_md or "")"""
    kind = d["kind"]
    if kind in TERM_KINDS:
        subject = TERM_SCOPE[kind][0]
        ask = ASK[form].format(subject=subject)
        if form == "match":
            terms, ch, _ = choices
            terms_md = "### 対応させる項目\n\n| # | 用語 |\n|---|------|\n" + "\n".join(f"| {k} | {t} |" for k, t in terms)
            ch_md = "\n\n".join(f"{k}. {t}" for k, t in ch)
            return "", ask, ch_md, terms_md
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return "", ask, ch_md, ""
    if kind in PECE_KINDS:
        return _question_pece(d, choices, form)
    if kind in LABEL_KINDS:
        return _question_label(d, choices, form)
    # vrfcfg 群
    pes = d["pes"]
    before = [f"あなたの組織は、AS {d['asn']} の MPLS L3VPN 網を運用しています。要件は、次のとおりです。", "",
              f"- {d['ask_pairs']}こと。"]
    if kind == "v_peer":
        vname, tpe = _split(d["target"])
        before += [f"- {d['rd_rule']}こと。", "", f"{pes[0]} の VRF の構成は、次のとおりです。", "",
                   "```", f"{pes[0]}# show running-config | section vrf definition", _vrf_section(pes[0], d["vrfs"]), "```"]
        ask = (f"{tpe} において、VRF {vname} を構成しなければなりません。要件を満たすところの構成は、次のうちどれですか。"
               "(1つを選択してください)")
        ch_md = "\n\n".join(f"**{'ABCDEFG'[i]}.**\n\n```\n{t}\n```" for i, (t, _, _) in enumerate(choices))
        return "\n".join(before), ask, ch_md, ""
    if kind == "v_reach":
        for pe in pes:
            if any(_split(n)[1] == pe for n in d["vrfs"]):
                before += ["", "```", f"{pe}# show running-config | section vrf definition", _vrf_section(pe, d["vrfs"]), "```"]
        if form == "read":
            vname, tpe = _split(d["target"])
            ask = (f"すべての PE ルータにおいて、VPNv4 のセッションは確立しており、各 VRF の経路は BGP に取り込まれています。"
                   f"{tpe} の VRF {vname} の経路表に、他の拠点の経路として載るところの宛先は、次のうちどれですか。(1つを選択してください)")
        else:
            ask = ("すべての PE ルータにおいて、VPNv4 のセッションは確立しており、各 VRF の経路は BGP に取り込まれています。"
                   "相互に通信できるところの拠点の組を、次のうちから 2 つ選択してください。")
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return "\n".join(before), ask, ch_md, ""
    if kind == "v_cause":
        vv = d["broken"]
        vname_v, pe_v = _split(d["victim"])
        vname_p, pe_p = _split(d["peer"])
        net_p = vv[d["peer"]]["nets"][0]
        for pe in pes:
            if any(_split(n)[1] == pe for n in vv):
                before += ["", "```", f"{pe}# show running-config | section vrf definition", _vrf_section(pe, vv), "```"]
                if pe in (pe_v, pe_p):
                    before += ["```", f"{pe}# show running-config | section router bgp", _bgp_section(d, pe), "```"]
        wit = "、".join(f"{_split(w)[1]} の VRF {_split(w)[0]} の拠点" for w in d.get("witness", []))
        before += ["", f"{pe_v} に収容されている VRF {vname_v} の拠点から、{pe_p} に収容されている VRF {vname_p} の拠点 {net_p} へ通信できない、"
                   f"ということが、報告されています。{pe_v} の VRF {vname_v} の経路表に、{net_p} は存在しません。"
                   f"一方、{pe_p} の VRF {vname_p} の経路表には、{pe_v} 側の拠点の経路が存在しています。"
                   + (f"なお、{wit}は、{'当該の拠点 ' + net_p + ' ' if d['cause'] == 'imp_wrong' else pe_v + ' の VRF ' + vname_v + ' の拠点'}と、正常に通信できています。" if wit else "")]
        ask = "示されている構成に基づいて、この事象の原因として最も適切なものは、次のうちどれですか。(1つを選択してください)"
        ch_md = "\n\n".join(f"{'ABCDEFG'[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return "\n".join(before), ask, ch_md, ""
    raise ValueError(kind)


CORE = {
    "t_roles": "PE がラベルの付加・除去と VRF/VPNv4 を担い、P はラベル交換だけを行い、CE は MPLS を知らない。",
    "t_label": "ヘッダは 32 ビット(Label 20/EXP 3/S 1/TTL 8)、LSP は片方向、PHP は出口手前で imp-null により除去。",
    "t_ldp": "セッションは TCP 646・Hello は UDP 646、router-id はループバック優先、transport address の到達性が必須。",
    "t_vpn": "RD は一意化(64 ビット・PE 間で一致不要)、RT が取り込みを制御(import≠export 可)、MP-BGP が VPNv4 とラベルを運ぶ。",
    "v_peer": "対向 PE の VRF は「提示側の export を import し、提示側の import に一致する export を持つ」形にする。RD は一致させる必要がなく、規約に従う。",
    "v_reach": "VRF 表に載るのは、自 VRF の import と一致する export を持つ VRF の経路だけ。RD は取り込みに関与しない。",
    "v_cause": "片方向だけ落ちるのは RT の import/export の不一致。RD の不一致・vpnv4 の構成・LSP は、示されている事実で否定できる。",
    "l_read": "LFIB は Local/Outgoing のラベルと動作を示す。Pop Label= 対向が imp-null を広告(PHP・最終ホップ手前で除去)、数値= swap、No Label [V]= VRF 宛(ラベルを外して IP 転送)。PE を出る VPN パケットは外側=トランスポート(LDP)・内側=VPN(MP-BGP)の 2 段で、PHP により出口 PE には VPN ラベルだけが届く(traceroute の Labels 17/20 → Label 20)。",
    "l_cause": "IGP は正常で VPN だけ落ちるのは LSP の穴。P の LFIB で出口 PE のループバック宛が No Label(その IF で LDP 無効)か、LDP の transport address に経路が無く(`no route to transport addr`)セッションが張れていないか、の指紋で切り分ける。",
    "p_asoverride": "同一 AS の拠点間では、CE が受信 AS_PATH に自身の AS を見つけて経路を捨てる(PE の advertised-routes には載るのに CE の PfxRcd が 0)。PE 側の as-override(CE の AS を PE の AS に置換= 受信 AS_PATH `65000 65000`)か、CE 側の allowas-in(自 AS を許容= `65000 65200`)で通る。どちらを採るかは「どちら側の構成を変えられるか」で決まる。",
}


def answer_body(d, choices, form):
    """## 正解 と ## 各選択肢の判定 と ## 解説 を返す(種別行は呼び元が付ける)。"""
    if form == "match":
        terms, ch, ans = choices
        lines = ["## 正解", "", "**" + "、".join(f"{k}－{v}" for k, v in ans.items()) + "**", "", "## 解説", "", CORE[d["kind"]]]
        return "\n".join(lines)
    keys = [k for k, (t, ok, w) in zip("ABCDEFG", choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for k, (t, ok, w) in zip("ABCDEFG", choices):
        lines.append(f"- **{k}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[d["kind"]]]
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
def selftest(seeds=30):
    import random as _r
    import re as _re
    ng = n = 0
    bad = {}
    for kind in KINDS:
        for world in KIND_WORLDS[kind]:
            for form in sorted(FORMS[kind]):
                for s in range(seeds):
                    n += 1
                    rnd = _r.Random(hash((kind, world, form, s)) & 0xFFFFFFFF)
                    try:
                        d = draw(rnd, kind, None if world == "-" else world, form)
                        if form == "match":
                            terms, ch, ans = build_match(d, rnd)
                            assert len(ans) == 4 and len(set(ans.values())) == 4, "全単射でない"
                            # 対応の正しさ: 用語→説明が MATCH_SETS と一致
                            want = dict(MATCH_SETS[kind])
                            got = {t: dict(ch)[ans[k]] for k, t in terms}
                            assert got == want, "対応が壊れた"
                            choices = (terms, ch, ans)
                        else:
                            choices = {"select": build_choices_select, "select2": build_choices_select2,
                                       "allthat": build_choices_allthat, "fix": build_choices_fix,
                                       "read": build_choices_read, "cause": build_choices_cause}[form](d, rnd)
                            n_true = sum(1 for x in choices if x[1])
                            want = {"select": 1, "fix": 1, "read": 1, "cause": 1, "select2": 2}.get(form)
                            if form == "allthat":
                                assert 1 <= n_true <= 4, f"allthat 正解数 {n_true}"
                            else:
                                assert n_true == want, f"{form} 正解数 {n_true}"
                            texts = [x[0] for x in choices]
                            assert len(set(texts)) == len(texts), "選択肢の重複"
                            # 因果を書かない(BL-080): 「〜ため」「〜ので」を肢に含めない
                            assert not any(_re.search(r"(ため|ので)[、。]", t) for t in texts), "肢に因果"
                        before, ask, ch_md, terms_md = question_body(d, choices, form)
                        ab = answer_body(d, choices, form)
                        assert "## 正解" in ab
                        # 決定性
                        rnd2 = _r.Random(hash((kind, world, form, s)) & 0xFFFFFFFF)
                        d2 = draw(rnd2, kind, None if world == "-" else world, form)
                        c2 = build_match(d2, rnd2) if form == "match" else \
                            {"select": build_choices_select, "select2": build_choices_select2,
                             "allthat": build_choices_allthat, "fix": build_choices_fix,
                             "read": build_choices_read, "cause": build_choices_cause}[form](d2, rnd2)
                        assert question_body(d2, c2, form) == (before, ask, ch_md, terms_md), "非決定的"
                    except (AssertionError, ValueError) as exc:
                        ng += 1
                        key = (kind, world, form)
                        bad.setdefault(key, [0, str(exc)])[0] += 1
    for (k, w, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{w}/{f}: {cnt} 件 (例: {ex})")
    # 実測 byte 写しとの一致(poc/mpls-paper/results-raw-04.md)
    samples = [
        (bgp_row("*>", "10.99.6.1/32", "192.168.11.1", "0", "", "0", "65200 i"),
         " *>   10.99.6.1/32     192.168.11.1             0             0 65200 i"),
        (bgp_row("*>i", "10.99.7.1/32", "3.3.3.3", "0", "100", "0", "65200 i"),
         " *>i  10.99.7.1/32     3.3.3.3                  0    100      0 65200 i"),
        (bgp_row("*>", "10.99.4.1/32", "0.0.0.0", "0", "", "32768", "i"),
         " *>   10.99.4.1/32     0.0.0.0                  0         32768 i"),
        (bgp_row("*>", "172.16.2.0/24", "192.168.1.2", "", "", "0", "65000 65102 i"),
         " *>   172.16.2.0/24    192.168.1.2                            0 65000 65102 i"),
        (bgp_summary_row("192.168.11.2", 65000, 19, 12, 11, "00:06:53", 0),
         "192.168.11.2    4        65000      19      12       11    0    0 00:06:53        0"),
        (lfib_row("16", "Pop Label", "2.2.2.2/32", "0", "Et0/0", "10.1.12.2"),
         "16         Pop Label  2.2.2.2/32       0             Et0/0      10.1.12.2"),
        (lfib_row("19", "No Label", "10.99.4.1/32[V]", "0", "Et0/1", "192.168.1.1"),
         "19         No Label   10.99.4.1/32[V]  0             Et0/1      192.168.1.1"),
        (lfib_row("20", "No Label", "172.16.1.0/24[V]", "570", "Et0/1", "192.168.1.1"),
         "20         No Label   172.16.1.0/24[V] 570           Et0/1      192.168.1.1"),
        (lfib_row("21", "No Label", "192.168.1.0/30[V]", "0", "aggregate/CUST_A", ""),
         "21         No Label   192.168.1.0/30[V]   \\\n                                       0             aggregate/CUST_A"),
        (lfib_row("17", "No Label", "3.3.3.3/32", "2494", "Et0/1", "10.1.23.2"),
         "17         No Label   3.3.3.3/32       2494          Et0/1      10.1.23.2"),
    ]
    for got, want in samples:
        if got != want:
            ng += 1
            print(f"NG byte 写し:\n  got  {got!r}\n  want {want!r}")
    print(f"[gen_paper_mpls selftest] {n} 件 / NG {ng}")
    return ng


if __name__ == "__main__":
    raise SystemExit(selftest())
