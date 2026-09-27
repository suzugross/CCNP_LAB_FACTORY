#!/usr/bin/env python3
"""cloze_kb_order.py — 解説穴埋め形(shape=cloze) の知識ベース: 順番・レベル系(BL-197)

「順序表の n 個(5〜6)を空欄にして埋める」形。語群 8 のうち残り 2〜3 が誤答(表に無いもっともらしい語)。
書式は cloze_kb_mpls.py と同じ + `n_blanks`(passage 単位の空欄数)。

事実の出所:
- BGP ベストパス選択順: 公式「BGP Best Path Selection Algorithm」(weight → local pref → ローカル生成 → AS_PATH →
  origin → MED → eBGP>iBGP → IGP メトリック → (multipath) → 最古の eBGP → ルータ ID → クラスタリスト長 → ネイバーアドレス)。
- syslog 重大度 0〜7 と IOS の既定(console/monitor/buffered= debugging・trap= informational)= poc/svc-paper 実測。
- IP precedence 0〜7 の名称と DSCP との対応(CS= precedence×8・EF 46= precedence 5)。
- アドミニストレーティブディスタンス既定値(connected 0/static 1/eBGP 20/EIGRP 90/OSPF 110/IS-IS 115/RIP 120/EIGRP external 170/iBGP 200/255)。
"""

PASSAGES = [
    # ------------------------------------------------------------------ BGP ベストパス
    {
        "kind": "o_bgp",
        "title": "BGP ベストパス選択の順序",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": (
            '| 順 | 比較する属性と勝つ条件 |\n'
            '|---|---|\n'
            '| 1 | «s1» |\n'
            '| 2 | «s2» |\n'
            '| 3 | «s3» |\n'
            '| 4 | «s4» |\n'
            '| 5 | «s5» |\n'
            '| 6 | «s6» |\n'
            '| 7 | «s7» |\n'
            '| 8 | «s8» |\n'
            '| 9 | «s9» |\n'
            '| 10 | «s10» |\n'
            '| 11 | «s11» |\n'
            '| 12 | «s12» |\n'
        ),
        "exhibit_md": True,
        "text": (
            "上は Cisco IOS の BGP ベストパス選択で、同じプレフィックスの候補を上から順に比較して 1 本に絞る手順である。"
            "先頭 2 つは自 AS の中だけで意味を持つ値で、1 番は «w_scope»。3 番は自分で生成した経路を優先する段で、"
            "network/redistribute 由来が aggregate 由来より勝つ。4 番以降は AS 間で運ばれる属性の比較になり、5 番の origin は «origin_order» の順で小さい方が勝つ。"
            "6 番の MED は既定では «med_scope» 経路どうしでだけ比較される。8 番までで決まらなければ安定性のために古い経路を残し、"
            "最後は識別子の小さい方という機械的な決着になる。なお maximum-paths を設定していると 8 番の後で等コストの複数経路が採用され、"
            "その場合でもベストパスは 1 本だけ選ばれる。"
        ),
        "slots": {
            "s1": {"a": "Weight が最大", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "Cisco 独自・ローカル有意・既定 0(自己生成は 32768)"},
            "s2": {"a": "LOCAL_PREF が最大", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "AS 内で共有・既定 100"},
            "s3": {"a": "ローカルで生成した経路(network/redistribute > aggregate)", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "自分で作った経路を優先"},
            "s4": {"a": "AS_PATH が最短", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "AS の数(bgp bestpath as-path ignore で無効化可)"},
            "s5": {"a": "ORIGIN が小さい(IGP < EGP < Incomplete)", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "i < e < ?"},
            "s6": {"a": "MED が最小", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "既定は同一隣接 AS からの経路間だけ"},
            "s7": {"a": "eBGP 経路が iBGP 経路より優先", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "外部学習を優先"},
            "s8": {"a": "ネクストホップへの IGP メトリックが最小", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "最寄りの出口"},
            "s9": {"a": "最も古い eBGP 経路(受信が早い方)", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "経路のフラップ抑止のため古い方を残す"},
            "s10": {"a": "ルータ ID が最小", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "識別子で機械的に決める"},
            "s11": {"a": "クラスタリスト長が最短", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "RR 環境での決着"},
            "s12": {"a": "ネイバーアドレスが最小", "d": ["ホップ数が最少", "コミュニティ値が最小", "AD が最小", "プレフィックス長が最長"], "grp": "items", "why": "最後の決着。誤答のホップ数/コミュニティ/AD/プレフィックス長は選択基準に無い"},
            "w_scope": {"a": "そのルータの中だけで有効(隣接へ広告されない)", "d": ["AS 内の iBGP 全体で共有される", "eBGP 越しにも伝わる"], "why": "Weight はローカル有意"},
            "origin_order": {"a": "IGP(i) → EGP(e) → Incomplete(?)", "d": ["Incomplete(?) → EGP(e) → IGP(i)", "EGP(e) → IGP(i) → Incomplete(?)"], "why": "i が最良"},
            "med_scope": {"a": "同じ隣接 AS から受けた", "d": ["すべての", "iBGP で受けた"], "why": "bgp always-compare-med を入れない限り AS 間比較はしない"},
        },
    },
    # ------------------------------------------------------------------ syslog 重大度
    {
        "kind": "o_syslog",
        "title": "syslog の重大度レベルと IOS の既定",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": (
            '| レベル | キーワード | 意味 |\n'
            '|---|---|---|\n'
            '| 0 | «l0» | システムが使用不能 |\n'
            '| 1 | «l1» | 直ちに対処が必要 |\n'
            '| 2 | «l2» | 致命的な状態 |\n'
            '| 3 | «l3» | エラー |\n'
            '| 4 | «l4» | 警告 |\n'
            '| 5 | «l5» | 正常だが重要な事象(IF up/down・設定変更など) |\n'
            '| 6 | «l6» | 情報 |\n'
            '| 7 | «l7» | デバッグ出力 |\n'
        ),
        "exhibit_md": True,
        "text": (
            "syslog のレベルは数字が小さいほど重大で、`logging` 系のコマンドで指定したレベル «lte» のメッセージが出力される。"
            "IOS の既定はコンソール・モニタ・バッファがレベル «con_default» まで、syslog サーバへ送る `logging trap` がレベル «trap_default» までである。"
            "つまり既定のままでは最も軽微なデバッグ出力はサーバに届かない。メッセージ本体の `%LINK-3-UPDOWN` のような書式では、"
            "ハイフンで区切られた真ん中の数字が «msg_num» を示す。`show logging` の先頭にはこれらの設定値と各出力先のカウントが並ぶ。"
        ),
        "slots": {
            "l0": {"a": "emergencies", "d": ["fatal", "verbose", "trace", "severe"], "grp": "items", "why": "0"},
            "l1": {"a": "alerts", "d": ["fatal", "verbose", "trace", "severe"], "grp": "items", "why": "1"},
            "l2": {"a": "critical", "d": ["fatal", "verbose", "trace", "severe"], "grp": "items", "why": "2"},
            "l3": {"a": "errors", "d": ["fatal", "verbose", "trace", "severe"], "grp": "items", "why": "3"},
            "l4": {"a": "warnings", "d": ["fatal", "verbose", "trace", "severe"], "grp": "items", "why": "4"},
            "l5": {"a": "notifications", "d": ["fatal", "verbose", "trace", "severe"], "grp": "items", "why": "5"},
            "l6": {"a": "informational", "d": ["fatal", "verbose", "trace", "severe"], "grp": "items", "why": "6"},
            "l7": {"a": "debugging", "d": ["fatal", "verbose", "trace", "severe"], "grp": "items", "why": "7。fatal/verbose/trace/severe は syslog のキーワードに無い"},
            "lte": {"a": "以下(そのレベルとより重大なもの)", "d": ["以上(そのレベルとより軽微なもの)", "ちょうど一致するものだけ"], "why": "指定レベル以下(数字が小さい側)が出る"},
            "con_default": {"a": "7", "d": ["5", "0"], "why": "console/monitor/buffered の既定は debugging(7)(実測)"},
            "trap_default": {"a": "6", "d": ["4", "7"], "why": "logging trap の既定は informational(6)(実測)"},
            "msg_num": {"a": "そのメッセージの重大度レベル", "d": ["ファシリティの番号", "発生回数"], "why": "%FACILITY-SEVERITY-MNEMONIC"},
        },
    },
    # ------------------------------------------------------------------ IP precedence
    {
        "kind": "o_prec",
        "title": "IP precedence の値と名称・DSCP との対応",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": (
            '| precedence | 名称(IOS キーワード) | 対応する DSCP クラスセレクタ |\n'
            '|---|---|---|\n'
            '| 0 | «p0» | CS0(default) |\n'
            '| 1 | «p1» | CS1 |\n'
            '| 2 | «p2» | CS2 |\n'
            '| 3 | «p3» | CS3 |\n'
            '| 4 | «p4» | CS4 |\n'
            '| 5 | «p5» | CS5(EF 46 もここ) |\n'
            '| 6 | «p6» | CS6 |\n'
            '| 7 | «p7» | CS7 |\n'
        ),
        "exhibit_md": True,
        "text": (
            "IP precedence は ToS バイトの上位 3 ビットで 0〜7、DSCP は上位 6 ビットで 0〜63 である。"
            "クラスセレクタ CSn の DSCP 値は precedence の «cs_mult» 倍で、EF(46)は precedence «ef_prec» の範囲に入る。"
            "AFxy のクラス番号 x も precedence と同じ位置のビットなので、AF31 は precedence «af31_prec» として扱われる。"
            "6 と 7 はルーティングプロトコルなどネットワーク制御用に予約された扱いで、ユーザトラフィックには通常使わない。"
            "`ip precedence` や `set ip precedence` で名称と数値のどちらでも指定できる。"
        ),
        "slots": {
            "p0": {"a": "routine", "d": ["urgent", "bulk", "expedited", "assured"], "grp": "items", "why": "0"},
            "p1": {"a": "priority", "d": ["urgent", "bulk", "expedited", "assured"], "grp": "items", "why": "1"},
            "p2": {"a": "immediate", "d": ["urgent", "bulk", "expedited", "assured"], "grp": "items", "why": "2"},
            "p3": {"a": "flash", "d": ["urgent", "bulk", "expedited", "assured"], "grp": "items", "why": "3"},
            "p4": {"a": "flash-override", "d": ["urgent", "bulk", "expedited", "assured"], "grp": "items", "why": "4"},
            "p5": {"a": "critical", "d": ["urgent", "bulk", "expedited", "assured"], "grp": "items", "why": "5"},
            "p6": {"a": "internet", "d": ["urgent", "bulk", "expedited", "assured"], "grp": "items", "why": "6(internetwork control)"},
            "p7": {"a": "network", "d": ["urgent", "bulk", "expedited", "assured"], "grp": "items", "why": "7(network control)。urgent/bulk は名称に無く、expedited/assured は DSCP の PHB 名"},
            "cs_mult": {"a": "8", "d": ["4", "2"], "why": "CSn = n×8(3 ビット左シフト)"},
            "ef_prec": {"a": "5", "d": ["6", "4"], "why": "46 = 101110b → 上位 3 ビット 101 = 5"},
            "af31_prec": {"a": "3", "d": ["1", "31"], "why": "AF31 = 011010b → 上位 3 ビット 011 = 3"},
        },
    },
    # ------------------------------------------------------------------ アドミニストレーティブディスタンス
    {
        "kind": "o_ad",
        "title": "アドミニストレーティブディスタンスの既定値",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": (
            '| 経路の出所 | AD |\n'
            '|---|---|\n'
            '| 直接接続 | «a_conn» |\n'
            '| スタティック | «a_static» |\n'
            '| eBGP | «a_ebgp» |\n'
            '| EIGRP(内部) | «a_eigrp» |\n'
            '| OSPF | «a_ospf» |\n'
            '| IS-IS | «a_isis» |\n'
            '| RIP | «a_rip» |\n'
            '| EIGRP(外部) | «a_eigrpx» |\n'
            '| iBGP | «a_ibgp» |\n'
            '| 不明(使わない) | «a_unknown» |\n'
        ),
        "exhibit_md": True,
        "text": (
            "AD は同じプレフィックスを複数の出所から学んだときに、どれを経路表に載せるかを決める信頼度で、«smaller» 方が勝つ。"
            "同じプロトコル内の優劣はメトリックで決めるが、プロトコルをまたぐ比較はメトリックでは行えないので AD が要る。"
            "EIGRP は内部経路と外部(再配送)経路で値が違い、再配送ループを防ぐ意図で外部の方が «eigrpx_rel»。"
            "BGP も eBGP と iBGP で値が違い、iBGP が大きいのは «ibgp_why» ためである。"
            "値はプロトコル配下の `distance` コマンドで変えられ、AD を最大値にした経路は「信頼しない」扱いで経路表に載らない。"
        ),
        "slots": {
            "a_conn": {"a": "0", "d": ["100", "130", "150", "5"], "grp": "items", "why": "直接接続"},
            "a_static": {"a": "1", "d": ["100", "130", "150", "5"], "grp": "items", "why": "スタティック"},
            "a_ebgp": {"a": "20", "d": ["100", "130", "150", "5"], "grp": "items", "why": "eBGP"},
            "a_eigrp": {"a": "90", "d": ["100", "130", "150", "5"], "grp": "items", "why": "EIGRP 内部"},
            "a_ospf": {"a": "110", "d": ["100", "130", "150", "5"], "grp": "items", "why": "OSPF"},
            "a_isis": {"a": "115", "d": ["100", "130", "150", "5"], "grp": "items", "why": "IS-IS"},
            "a_rip": {"a": "120", "d": ["100", "130", "150", "5"], "grp": "items", "why": "RIP"},
            "a_eigrpx": {"a": "170", "d": ["100", "130", "150", "5"], "grp": "items", "why": "EIGRP 外部"},
            "a_ibgp": {"a": "200", "d": ["100", "130", "150", "5"], "grp": "items", "why": "iBGP"},
            "a_unknown": {"a": "255", "d": ["100", "130", "150", "5"], "grp": "items", "why": "255 は不信= 経路表に載らない。100/130/150/5 は既定値に無い"},
            "smaller": {"a": "小さい", "ok": ["小さい(信頼度が高い)"], "d": ["大きい"], "why": "AD は小さいほど信頼"},
            "eigrpx_rel": {"a": "大きい(信頼度が低い)", "ok": ["大きい"], "d": ["小さい(信頼度が高い)", "同じ"], "why": "170 > 90"},
            "ibgp_why": {"a": "AS 内では IGP の経路を優先させたい", "d": ["iBGP は eBGP より収束が速い", "iBGP はフルメッシュが要る"], "why": "200 は IGP 全部より大きい"},
        },
    },
]


# ==========================================================================
# 逆引き形「この項目は何番目/何番か」(BL-200・2026-09-20 ユーザ要望)
#   同じ kind に 2 本目の passage として追加(抽選で表形と逆引き形が半々に出る)。
#   項目を順不同で並べ、番号を空欄にする。語群は数字だけ(正解 + 残りの番号がデコイ)。
# ==========================================================================
def _pos_lines(items):
    return "\n".join(f"- {name} …… 【«{sid}»】" for sid, name in items)


_BGP_ITEMS = [("q_med", "MED が最小"), ("q_ebgp", "eBGP 経路が iBGP 経路より優先"), ("q_weight", "Weight が最大"),
              ("q_rid", "ルータ ID が最小"), ("q_aspath", "AS_PATH が最短"), ("q_igp", "ネクストホップへの IGP メトリックが最小"),
              ("q_lp", "LOCAL_PREF が最大"), ("q_oldest", "最も古い eBGP 経路"), ("q_origin", "ORIGIN が小さい(i < e < ?)"),
              ("q_nbr", "ネイバーアドレスが最小"), ("q_local", "ローカルで生成した経路"), ("q_cluster", "クラスタリスト長が最短")]
_BGP_POS = {"q_weight": "1", "q_lp": "2", "q_local": "3", "q_aspath": "4", "q_origin": "5", "q_med": "6",
            "q_ebgp": "7", "q_igp": "8", "q_oldest": "9", "q_rid": "10", "q_cluster": "11", "q_nbr": "12"}
_NUMS12 = [str(i) for i in range(1, 13)]

_SYS_ITEMS = [("v_warn", "warnings"), ("v_emerg", "emergencies"), ("v_info", "informational"), ("v_crit", "critical"),
              ("v_notif", "notifications"), ("v_debug", "debugging"), ("v_alert", "alerts"), ("v_err", "errors")]
_SYS_LV = {"v_emerg": "0", "v_alert": "1", "v_crit": "2", "v_err": "3", "v_warn": "4", "v_notif": "5", "v_info": "6", "v_debug": "7"}

_PREC_ITEMS = [("c_flash", "flash"), ("c_net", "network"), ("c_routine", "routine"), ("c_crit", "critical"),
               ("c_prio", "priority"), ("c_inet", "internet"), ("c_imm", "immediate"), ("c_fo", "flash-override")]
_PREC_NUM = {"c_routine": "0", "c_prio": "1", "c_imm": "2", "c_flash": "3", "c_fo": "4", "c_crit": "5", "c_inet": "6", "c_net": "7"}
_NUMS8 = [str(i) for i in range(0, 8)]

_AD_ITEMS = [("d_ospf", "OSPF"), ("d_ebgp", "eBGP"), ("d_rip", "RIP"), ("d_static", "スタティック"), ("d_eigrpx", "EIGRP(外部)"),
             ("d_conn", "直接接続"), ("d_ibgp", "iBGP"), ("d_isis", "IS-IS"), ("d_eigrp", "EIGRP(内部)"), ("d_unknown", "不明(信頼しない)")]
_AD_VAL = {"d_conn": "0", "d_static": "1", "d_ebgp": "20", "d_eigrp": "90", "d_ospf": "110", "d_isis": "115",
           "d_rip": "120", "d_eigrpx": "170", "d_ibgp": "200", "d_unknown": "255"}
_AD_NUMS = ["0", "1", "20", "90", "110", "115", "120", "170", "200", "255"]

PASSAGES += [
    {
        "kind": "o_bgp",
        "title": "BGP ベストパス選択で、この比較は何番目か",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": ("次の各項目は、Cisco IOS の BGP ベストパス選択(先頭から最後まで)の何番目に比較されるか。番号を選べ。\n\n"
                 + _pos_lines(_BGP_ITEMS) + "\n\n"
                 "Weight と LOCAL_PREF は AS の外へ出ない「自分たちの都合」の値なので最初に見る。AS_PATH 以降は経路と一緒に運ばれてきた属性の比較で、"
                 "属性で決まらなければ古さと識別子で機械的に決着する。"),
        "slots": {sid: {"a": _BGP_POS[sid], "d": _NUMS12, "grp": "items", "why": name} for sid, name in _BGP_ITEMS},
    },
    {
        "kind": "o_syslog",
        "title": "syslog のこのキーワードはレベル何番か",
        "diagram": None,
        "n_blanks": 5,
        "pool_size": 8,
        "exhibit": None,
        "text": ("次の各キーワードは syslog の重大度レベル(0〜7)の何番か。番号を選べ。\n\n"
                 + _pos_lines(_SYS_ITEMS) + "\n\n"
                 "数字が小さいほど重大で、`logging trap <レベル>` を指定するとそのレベル以下(より重大な側)がサーバへ送られる。"
                 "IOS の既定は trap が informational、コンソール・モニタ・バッファが debugging である。"),
        "slots": {sid: {"a": _SYS_LV[sid], "d": _NUMS8, "grp": "items", "why": name} for sid, name in _SYS_ITEMS},
    },
    {
        "kind": "o_prec",
        "title": "IP precedence のこの名称は値いくつか",
        "diagram": None,
        "n_blanks": 5,
        "pool_size": 8,
        "exhibit": None,
        "text": ("次の各名称は IP precedence(0〜7)の値いくつか。番号を選べ。\n\n"
                 + _pos_lines(_PREC_ITEMS) + "\n\n"
                 "DSCP のクラスセレクタ CSn は precedence n に対応し、値は n×8。EF(46)は precedence 5 の範囲、AFxy の x が precedence に相当する。"),
        "slots": {sid: {"a": _PREC_NUM[sid], "d": _NUMS8, "grp": "items", "why": name} for sid, name in _PREC_ITEMS},
    },
    {
        "kind": "o_ad",
        "title": "この経路の出所のアドミニストレーティブディスタンスはいくつか",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": ("次の各出所の経路の既定 AD はいくつか。値を選べ。\n\n"
                 + _pos_lines(_AD_ITEMS) + "\n\n"
                 "AD は小さいほど信頼され、同じプレフィックスを複数の出所から学んだときに経路表へ載せる方を決める。"
                 "EIGRP は内部と外部で値が違い、BGP は eBGP と iBGP で値が違う。"),
        "slots": {sid: {"a": _AD_VAL[sid], "d": _AD_NUMS, "grp": "items", "why": name} for sid, name in _AD_ITEMS},
    },
]
