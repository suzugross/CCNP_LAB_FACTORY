#!/usr/bin/env python3
"""cloze_kb_mpls.py — 解説穴埋め形(shape=cloze) の知識ベース: MPLS / MPLS L3VPN

書式:
  PASSAGES = [passage, ...]
  passage = {
    "kind":    "m_roles",            # 出題 kind
    "title":   "…",                  # 見出し(出題文の冒頭に出す)
    "diagram": "graph LR …" | None,  # Mermaid(任意)
    "exhibit": "config text" | None, # 設定例など(任意)。«slot» と {var} を使える
    "text":    "…«slot»…{var}…",     # 解説文。«slot» = 空欄候補 / {var} = seed で振る値
    "slots":   {slot: {"a": 正解, "d": [誤答候補…], "ok": [同義で正解扱い…], "why": "誤答が不適な理由"}},
    "vars":    {var: [候補…]},        # 任意
  }

事実は公式コンフィグレーションガイド(IOS XE 17.x MPLS / L3VPN / TE)で裏取りした範囲に限る。
"scope": "beyond" を付けた passage は ENARSI 範囲外(TE の詳細)。既定の出題(KINDS/THINK_KINDS)には入らず、
`--kinds` で明示したときだけ出る(2026-09-19 ユーザ判断「後半は ENARSI の範囲を超えている」)。範囲内は
ブループリント 1.9 MPLS operations(LSR/LDP/label switching/LSP)・1.10 MPLS L3VPN の describe レベル＋教材が扱う周辺。
裏取りできない数値(ラベル既定レンジ・機種依存の収束時間など)は使わない。
"""

DIAG_LINE = (
    "graph LR\n"
    "  CE1[CE1] --- PE1[PE1]\n"
    "  PE1 --- P1[P1]\n"
    "  P1 --- P2[P2]\n"
    "  P2 --- PE2[PE2]\n"
    "  PE2 --- CE2[CE2]\n"
)

PASSAGES = [
    # ------------------------------------------------------------------ 役割
    {
        "kind": "m_roles",
        "title": "MPLS L3VPN を構成する 3 種類のルータ",
        "diagram": DIAG_LINE,
        "exhibit": None,
        "text": (
            "MPLS L3VPN の網は 3 種類のルータで構成される。顧客拠点側に置かれる «ce» は MPLS もラベルも意識せず、"
            "通常の IGP・eBGP・静的経路でプロバイダ側と経路を交換するだけである。プロバイダ網の縁に置かれる «pe» は"
            "顧客ごとに «vrf» を持ち、顧客経路を隔離して保持する唯一の装置である。網の中心にある «p» は顧客経路もその分離表も持たず、"
            "«igp» で学んだプロバイダ内部の経路と «ldp» で学んだラベルだけを使って転送する。"
            "したがって顧客経路を運ぶ «mpbgp» のピアは網の縁の装置同士の間だけで張られ、中心の装置は関与しない。"
            "顧客から見ると、プロバイダ網全体が 1 台の巨大なルータのように振る舞う。"
        ),
        "slots": {
            "ce": {"a": "CE", "d": ["PE", "P"], "why": "PE/P はプロバイダ側の装置で、MPLS を意識しないのは顧客側の CE だけ"},
            "pe": {"a": "PE", "d": ["P", "CE"], "why": "VRF を持ち顧客経路を保持するのはプロバイダ網の縁(PE)。P は顧客経路を持たない"},
            "vrf": {"a": "VRF", "d": ["グローバルルーティングテーブル", "VLAN"], "why": "顧客ごとの経路表分離は VRF。グローバル表はプロバイダ内部用"},
            "p": {"a": "P", "d": ["CE", "PE"], "why": "顧客経路も VRF も持たずラベルだけで転送するのは P"},
            "igp": {"a": "IGP(OSPF/IS-IS)", "d": ["MP-BGP", "eBGP"], "why": "P が持つのはプロバイダ内部の経路= IGP。MP-BGP は顧客経路用で P は持たない"},
            "ldp": {"a": "LDP", "d": ["MP-BGP", "NHRP"], "why": "トランスポートラベルを配るのは LDP(または RSVP-TE)。MP-BGP は VPN ラベル"},
            "mpbgp": {"a": "MP-BGP", "d": ["LDP", "IGP(OSPF/IS-IS)"], "why": "顧客経路(VPNv4)を PE 間で運ぶのは MP-BGP"},
        },
    },
    # ------------------------------------------------------------------ 3 本柱とラベル形式
    {
        "kind": "m_arch",
        "title": "MPLS L3VPN の 3 本柱とラベルの形式",
        "diagram": None,
        "exhibit": None,
        "text": (
            "MPLS L3VPN は 3 つの技術の組み合わせで成り立つ。«vrf» は PE 上で顧客ごとに経路表・転送表・所属インターフェースを分離する仕組みで、"
            "これ単体なら MPLS なしの軽量構成(いわゆる lite 構成)としても使える。«mpbgp» は VPNv4 というアドレスファミリを追加して、RD 付きプレフィックス・RT・«vpnlabel» を"
            "PE 間で運ぶ。«mpls_fwd» は IP ヘッダを見ずにラベルで転送する仕組みで、これのおかげで網の中心のルータが顧客経路を持たずに済む。"
            "ラベルは L2 ヘッダと «l3» ヘッダの間に挿入される。ラベルスタックの 1 エントリは «entry_len» ビットで、"
            "20 ビットのラベル値・3 ビットの TC(旧 EXP)・1 ビットの S(Bottom of Stack)・8 ビットの «ttl» からなる。"
            "MPLS 網内の LSR が顧客経路を一切持たなくてよいのは、«p» が転送に使うのがラベルだけだからである。"
        ),
        "slots": {
            "vrf": {"a": "VRF", "d": ["VLAN", "VDC"], "why": "L3 の経路表を分離するのは VRF。VLAN は L2 の分離"},
            "mpbgp": {"a": "MP-BGP", "d": ["LDP", "OSPF"], "why": "VPNv4 アドレスファミリを持つのは MP-BGP"},
            "vpnlabel": {"a": "VPN ラベル", "d": ["LDP ラベル", "TE ラベル"], "why": "MP-BGP が運ぶのは VPN ラベル。LDP ラベルは LDP が配る"},
            "mpls_fwd": {"a": "MPLS ラベルスイッチング", "d": ["CEF", "PBR"], "why": "IP ヘッダを見ずに転送するのがラベルスイッチング。CEF は IP 転送の高速化"},
            "l3": {"a": "L3(IP)", "d": ["L4(TCP/UDP)", "L1"], "why": "ラベルは L2 と L3 の間(いわゆる Layer 2.5)"},
            "entry_len": {"a": "32", "d": ["20", "64"], "why": "20+3+1+8 = 32 ビット。20 はラベル値だけの長さ"},
            "ttl": {"a": "TTL", "d": ["EXP", "チェックサム"], "why": "8 ビットは TTL。TC(EXP) は 3 ビット"},
            "p": {"a": "P ルータ", "d": ["PE ルータ", "CE ルータ"], "why": "PE は VRF に顧客経路を持つ。ラベルだけで動くのは P"},
        },
    },
    # ------------------------------------------------------------------ 用語 RD/RT/VPNv4
    {
        "kind": "m_terms",
        "title": "RD・RT・VPNv4 の役割分担",
        "diagram": None,
        "exhibit": None,
        "text": (
            "PE は VRF から学んだ IPv4 プレフィックスをそのまま MP-BGP に載せない。まず «rd» を前置して «vpnv4» プレフィックスに変換する。"
            "前置される値は «rd_len» バイトで、顧客間で重複する 10.0.0.0/24 のようなアドレスを BGP テーブル上で別物として区別するためだけに使われ、"
            "どの VRF に取り込むかの判断には使われない。取り込み先を決めるのは «rt» で、これは BGP の «extcomm» として経路に付加される。"
            "VRF の «export» 側に設定した値が送出時に付き、受信 PE は自分の各 VRF の «import» 一覧に一致する値を持つ経路だけを取り込む。"
            "したがって RD は PE ごと・VRF ごとに違っていても構わないが、RT は通信させたい VRF 同士でそろえる必要がある。"
        ),
        "slots": {
            "rd": {"a": "RD(Route Distinguisher)", "d": ["RT(Route Target)", "SoO"], "why": "プレフィックスに前置して一意化するのは RD。RT は取り込み制御"},
            "vpnv4": {"a": "VPNv4", "d": ["IPv4 unicast", "VPNv6"], "why": "RD+IPv4 で作るのは VPNv4 プレフィックス"},
            "rd_len": {"a": "8", "d": ["12", "4"], "why": "RD は 8 バイト。12 は RD+IPv4 を足した VPNv4 全体の長さ"},
            "rt": {"a": "RT(Route Target)", "d": ["RD(Route Distinguisher)", "コミュニティ no-export"], "why": "取り込み先 VRF を決めるのは RT"},
            "extcomm": {"a": "拡張コミュニティ", "d": ["標準コミュニティ", "AS_PATH"], "why": "RT は拡張コミュニティ属性(send-community extended が要る理由)"},
            "export": {"a": "export", "d": ["import", "both"], "why": "送出時に付けるのは export 側の値"},
            "import": {"a": "import", "d": ["export", "redistribute"], "why": "受信時の突き合わせは import 一覧"},
        },
    },
    # ------------------------------------------------------------------ ラベルスタック
    {
        "kind": "m_stack",
        "title": "2 段ラベルスタックとパケットの旅",
        "diagram": DIAG_LINE,
        "exhibit": None,
        "text": (
            "入口 PE は VRF 宛の顧客パケットに 2 段のラベルを «push» する。スタックの «bottom» に置かれるのが «vpnlabel» で、"
            "これは «mpbgp» により VPNv4 経路と一緒に配布され、出口 PE がどの VRF(あるいはどの出力先)へ届けるかを決めるためだけに使われる。"
            "スタックの «top» に置かれるのが «tlabel» で、出口 PE のループバックアドレスを FEC として «ldp» が配布したものである。"
            "途中の P ルータは先頭のラベルだけを «swap» し、底のラベルには一切触れない。"
            "ラベルエントリの «sbit» が 1 のものがスタックの底であることを示すので、出口 PE はそこまで剥がせばよいと判断できる。"
        ),
        "slots": {
            "push": {"a": "push", "d": ["pop", "swap"], "why": "入口で付けるのは push。swap は途中、pop は出口側"},
            "bottom": {"a": "底(bottom)", "d": ["先頭(top)"], "why": "VPN ラベルは内側=底。先頭はトランスポートラベル"},
            "vpnlabel": {"a": "VPN ラベル", "d": ["トランスポートラベル", "TE ラベル"], "why": "VRF を決めるのは VPN ラベル"},
            "mpbgp": {"a": "MP-BGP", "d": ["LDP", "RSVP-TE"], "why": "VPN ラベルは VPNv4 経路と共に MP-BGP が配る"},
            "top": {"a": "先頭(top)", "d": ["底(bottom)"], "why": "P が見るのは先頭。トランスポートラベルは外側"},
            "tlabel": {"a": "トランスポートラベル", "d": ["VPN ラベル", "Explicit Null"], "why": "出口 PE へ届けるためのラベルはトランスポートラベル"},
            "ldp": {"a": "LDP", "d": ["MP-BGP", "OSPF"], "why": "PE ループバック宛のラベルは LDP(または RSVP-TE)が配る"},
            "swap": {"a": "swap", "d": ["pop", "push"], "why": "P は先頭ラベルの付け替え(swap)。pop するのは PHP を行う最後の P だけ"},
            "sbit": {"a": "S ビット(Bottom of Stack)", "d": ["TTL", "TC(EXP)"], "why": "底を示すのは S ビット。TTL はループ防止、TC は QoS"},
        },
    },
    # ------------------------------------------------------------------ PHP と予約ラベル
    {
        "kind": "m_php",
        "title": "PHP と予約ラベル",
        "diagram": None,
        "exhibit": None,
        "text": (
            "ラベル値は 20 ビットで、0 から «resv_max» までは予約されている。出口 PE(egress LER)は自分に直結する FEC に対して、"
            "ラベル値 «impnull» の «impnull_name» を上流に通知するのが既定である。これを受け取った 1 つ手前のルータは、"
            "転送時に先頭ラベルを «pop» してから送るので、出口 PE は 2 回の検索(ラベル→IP)をせずに済む。この動作を «php» と呼ぶ。"
            "QoS 情報(TC/EXP)を出口まで保持したい場合は、代わりにラベル値 «expnull» の «expnull_name» を通知させ、出口自身に剥がさせる。"
            "ラベル値 1 は «ralert» で、途中のルータが制御プレーンで検査すべきパケットであることを示す。"
        ),
        "slots": {
            "resv_max": {"a": "15", "d": ["16", "1023"], "why": "予約は 0〜15 の 16 個。16 以降が動的ラベル"},
            "impnull": {"a": "3", "d": ["0", "1"], "why": "Implicit Null は 3。0 は IPv4 Explicit Null、1 は Router Alert"},
            "impnull_name": {"a": "Implicit Null", "d": ["Explicit Null", "Router Alert"], "why": "手前で pop させるのは Implicit Null"},
            "pop": {"a": "pop", "d": ["swap", "push"], "why": "PHP では手前が剥がす(pop)"},
            "php": {"a": "PHP(Penultimate Hop Popping)", "d": ["UHP(Ultimate Hop Popping)", "PIC"], "why": "手前(penultimate)で pop するのが PHP。出口自身が pop するのが UHP"},
            "expnull": {"a": "0", "d": ["3", "14"], "why": "IPv4 Explicit Null は 0。3 は Implicit Null"},
            "expnull_name": {"a": "Explicit Null", "d": ["Implicit Null", "OAM Alert"], "why": "ラベルを付けたまま出口まで届けさせるのは Explicit Null"},
            "ralert": {"a": "Router Alert", "d": ["OAM Alert", "Entropy Label"], "why": "ラベル 1 は Router Alert"},
        },
    },
    # ------------------------------------------------------------------ 4 つの表
    {
        "kind": "m_tables",
        "title": "MPLS ルータが持つ 4 つの表",
        "diagram": None,
        "exhibit": None,
        "text": (
            "MPLS ルータは 4 つの表を使い分ける。IP ルーティングプロトコルの学習結果は «rib» に入り、そこから転送用に最適化された «fib» が作られる。"
            "LDP で交換したラベルバインディングは、全ての隣接から受け取ったものをそのまま «lib» に保持し、そのうち IP 経路表のネクストホップと一致する"
            "最良のものだけが転送用の «lfib» に反映される。したがって全隣接のバインディングを一覧するには «cmd_lib» を、"
            "実際の転送に使われるラベルと動作を見るには «cmd_lfib» を使う。"
            "ラベルなしの IP パケットを受け取った入口 PE は IP 宛先で表を引いてラベルを «ingress_op» し、"
            "ラベル付きパケットを受け取った P ルータは先頭ラベルで表を引いて «transit_op» する。"
        ),
        "slots": {
            "rib": {"a": "RIB", "d": ["LIB", "LFIB"], "why": "IP 経路の学習結果は RIB。LIB はラベルバインディング"},
            "fib": {"a": "FIB", "d": ["LFIB", "LIB"], "why": "IP 転送用は FIB。LFIB はラベル転送用"},
            "lib": {"a": "LIB", "d": ["LFIB", "RIB"], "why": "全隣接のバインディングを持つのは LIB(制御プレーン)"},
            "lfib": {"a": "LFIB", "d": ["FIB", "LIB"], "why": "転送に使うラベルだけを持つのは LFIB"},
            "cmd_lib": {"a": "show mpls ldp bindings", "d": ["show mpls forwarding-table", "show mpls ldp neighbor"], "why": "bindings = LIB の内容"},
            "cmd_lfib": {"a": "show mpls forwarding-table", "d": ["show mpls ldp bindings", "show ip cef"], "why": "forwarding-table = LFIB の内容"},
            "ingress_op": {"a": "push", "d": ["swap", "pop"], "why": "入口はラベルを付ける(push)"},
            "transit_op": {"a": "swap", "d": ["push", "pop"], "why": "途中は付け替え(swap)"},
        },
    },
    # ------------------------------------------------------------------ LDP セッション確立
    {
        "kind": "m_ldp_sess",
        "title": "LDP 隣接の発見とセッション確立",
        "diagram": None,
        "exhibit": None,
        "text": (
            "直結した LSR 同士の LDP は、«hello_proto» の 646 番ポートでマルチキャスト «hello_dst» 宛に Hello を送り合って相手を見つける。"
            "この直結相手の発見手順を «basic» と呼ぶ。Hello の既定は «hello_int» 秒間隔・保持時間 «hello_hold» 秒である。"
            "相手を見つけると «sess_proto» の 646 番で LDP セッションを張るが、接続を開始するのは «active» 側で、これをアクティブ LSR と呼ぶ。"
            "直結していない LSR とセッションを組む場合は «targeted» をユニキャストで送り、この手順を «extended» と呼ぶ。"
            "セッションが確立すると、以後のラベル広告(Advertisement)やエラー通知(Notification)はこのセッション上で運ばれる。"
        ),
        "slots": {
            "hello_proto": {"a": "UDP", "d": ["TCP", "SCTP"], "why": "Hello(Discovery)は UDP 646。セッションは TCP 646"},
            "hello_dst": {"a": "224.0.0.2", "d": ["224.0.0.5", "224.0.0.9"], "why": "LDP Hello は全ルータ宛 224.0.0.2。.5 は OSPF、.9 は RIPv2"},
            "basic": {"a": "Basic Discovery", "d": ["Extended Discovery", "Targeted Discovery"], "why": "直結相手の発見= Basic Discovery"},
            "hello_int": {"a": "5", "d": ["10", "30"], "why": "Link Hello の既定間隔は 5 秒"},
            "hello_hold": {"a": "15", "d": ["40", "90"], "why": "Link Hello の既定保持時間は 15 秒"},
            "sess_proto": {"a": "TCP", "d": ["UDP", "GRE"], "why": "セッションは信頼性のある TCP 646"},
            "active": {"a": "トランスポートアドレスが大きい", "d": ["トランスポートアドレスが小さい", "先に Hello を受信した"], "why": "アクティブ役はトランスポートアドレス(既定= LDP ルータ ID)が大きい側"},
            "targeted": {"a": "Targeted Hello", "d": ["Link Hello", "Keepalive"], "why": "非直結相手には Targeted Hello をユニキャスト"},
            "extended": {"a": "Extended Discovery", "d": ["Basic Discovery", "Auto Discovery"], "why": "非直結相手の発見= Extended Discovery"},
        },
    },
    # ------------------------------------------------------------------ ラベル配布モードとルータ ID
    {
        "kind": "m_ldp_dist",
        "title": "ラベルバインディング・配布モード・LDP ルータ ID",
        "diagram": None,
        "exhibit": None,
        "text": (
            "LDP がラベルを結び付ける単位は «fec» で、宛先プレフィックスのように転送処理が同じになるパケットの集合である。"
            "各 LSR はこの単位ごとに自分のローカルラベルを割り当て(ラベルバインディング)、既定の «du» モードでは相手からの要求を待たずに"
            "全ての LDP ピアへ広告する。要求されたときだけ広告するモードは «dod» である。"
            "LSR を識別する LDP ルータ ID は、明示指定がなければ «rid_pref» の中で最大の IP アドレス、それも無ければ物理インターフェースの最大 IP が選ばれる。"
            "このルータ ID は既定で LDP セッションの «transport» にも使われるため、そのアドレスが IGP で到達可能でないとセッションが張れない。"
            "IOS では `mpls ldp router-id Loopback0 «force»` のように固定するのが定石で、末尾のキーワードは既存セッションを張り直してでも直ちに適用させる意味を持つ。"
        ),
        "slots": {
            "fec": {"a": "FEC(Forwarding Equivalence Class)", "d": ["LSP", "VRF"], "why": "バインディングの単位は FEC。LSP はラベル付き経路そのもの"},
            "du": {"a": "Downstream Unsolicited(DU)", "d": ["Downstream on Demand(DoD)", "Ordered Control"], "why": "IOS の LDP 既定は要求なしで配る DU"},
            "dod": {"a": "Downstream on Demand(DoD)", "d": ["Downstream Unsolicited(DU)", "Liberal Retention"], "why": "要求時のみ配るのが DoD"},
            "rid_pref": {"a": "up 状態のループバックインターフェース", "d": ["up 状態の物理インターフェース", "MPLS を有効にしたインターフェース"], "why": "OSPF と同じくループバックが優先"},
            "transport": {"a": "トランスポートアドレス", "d": ["Hello の送信元アドレス", "マルチキャストグループ"], "why": "TCP セッションの端点になるのがトランスポートアドレス"},
            "force": {"a": "force", "d": ["preferred", "sticky"], "why": "force はルータ ID 変更を即時適用(セッション再確立を伴う)"},
        },
    },
    # ------------------------------------------------------------------ LDP の可用性機能
    {
        "kind": "m_ldp_ha",
        "title": "LDP-IGP 同期・LDP セッション保護・Autoconfig",
        "diagram": None,
        "exhibit": None,
        "text": (
            "LDP と IGP の足並みがそろわないと、リンク復旧直後などに «blackhole» が起きる。IGP の隣接が先に上がり、ラベル交換が終わる前にそのリンクへ"
            "転送が始まるためである。«sync» はこれを防ぐ機能で、LDP が未確立のリンクに対して IGP が «maxmetric» を広告して迂回させる。"
            "有効化は `router ospf` 配下の «sync_cmd» で、対応する IGP は OSPF と «isis» である。"
            "一方、リンク障害時にセッションそのものを維持するのが «protect» で、直結リンク用の Link Hello 隣接に加えて «targeted» 隣接をあらかじめ張っておき、"
            "リンクが落ちても IP で到達できる限りセッションとラベルバインディングを保つ。復旧後の再学習が不要になるので収束が速い。"
            "バックアップ隣接の保持時間は既定で «duration» である。"
            "さらに `mpls ldp autoconfig` は指定した IGP が走る全インターフェースで LDP を自動有効化する機能で、インターフェースごとの «mpls_ip» 投入を省く。"
        ),
        "slots": {
            "blackhole": {"a": "ブラックホール(パケット損失)", "d": ["ルーティングループ", "隣接フラップ"], "why": "ラベル未交換のリンクへ転送すると捨てられる= ブラックホール"},
            "sync": {"a": "LDP-IGP 同期", "d": ["LDP セッション保護", "LDP Graceful Restart"], "why": "IGP の経路選択を LDP の状態に従わせるのが同期"},
            "maxmetric": {"a": "max-metric", "d": ["down 状態", "デフォルトルート"], "why": "リンクを落とさず最大メトリックで不利にする"},
            "sync_cmd": {"a": "mpls ldp sync", "d": ["mpls ldp session protection", "mpls ldp autoconfig"], "why": "同期の有効化コマンドは router ospf 配下の mpls ldp sync"},
            "isis": {"a": "IS-IS", "d": ["EIGRP", "BGP"], "why": "同期も autoconfig も対応 IGP は OSPF と IS-IS"},
            "protect": {"a": "LDP セッション保護", "d": ["LDP-IGP 同期", "BFD"], "why": "Targeted Hello でセッションを維持するのがセッション保護"},
            "targeted": {"a": "Targeted Hello", "d": ["Link Hello", "Keepalive"], "why": "非直結でも届く Targeted Hello をバックアップ隣接に使う"},
            "duration": {"a": "無期限(infinite)", "d": ["180 秒", "15 秒"], "why": "duration の既定は infinite"},
            "mpls_ip": {"a": "mpls ip", "d": ["mpls ldp sync", "ip cef"], "why": "インターフェースで LDP を有効化するのは mpls ip"},
        },
    },
    # ------------------------------------------------------------------ RSVP-TE
    {
        "kind": "m_rsvp",
        "title": "RSVP-TE による LSP のシグナリング",
        "diagram": None,
        "exhibit": None,
        "text": (
            "RSVP-TE は LDP と違い、IGP の最短路に追随するのではなく、帯域などの制約を満たす経路に LSP(TE トンネル)を張る。"
            "経路計算は «headend» が行い、TE 拡張された IGP(OSPF/IS-IS)が配る利用可能帯域や affinity を入力として «cspf» で求める。"
            "求めた経路はホップの列として «ero» に載せ、«path» メッセージを下流へ送る。"
            "«tailend» まで届くと折り返しに «resv» メッセージが上流へ返り、各ホップは帯域を予約すると同時に、自分が上流に使わせるラベルを割り当ててこのメッセージに載せる。"
            "つまり RSVP-TE でもラベルは «label_dir» 向きに配布される。実際に通ったホップと各ホップの保護状態は «rro» に記録されて入口まで戻る。"
        ),
        "slots": {
            "headend": {"a": "ヘッドエンド(入口ルータ)", "d": ["テールエンド(出口ルータ)", "途中の P ルータ"], "why": "TE トンネルの経路計算とシグナリング開始は入口(ヘッドエンド)"},
            "cspf": {"a": "CSPF", "d": ["通常の SPF", "ベストパス選択"], "why": "制約付き最短路= CSPF"},
            "ero": {"a": "ERO(Explicit Route Object)", "d": ["RRO(Record Route Object)", "SESSION_ATTRIBUTE"], "why": "通す経路を指定するのは ERO"},
            "path": {"a": "PATH", "d": ["RESV", "Hello"], "why": "下流へ送るのは PATH"},
            "tailend": {"a": "テールエンド(出口ルータ)", "d": ["ヘッドエンド(入口ルータ)", "PLR"], "why": "PATH の終点は出口(テールエンド)"},
            "resv": {"a": "RESV", "d": ["PATH", "ResvErr"], "why": "上流へ返るのは RESV"},
            "label_dir": {"a": "下流から上流", "d": ["上流から下流"], "why": "ラベルは RESV に載って下流から上流へ(LDP の DU と同じ向き)"},
            "rro": {"a": "RRO(Record Route Object)", "d": ["ERO(Explicit Route Object)", "LABEL_REQUEST"], "why": "通過ホップの記録は RRO"},
        },
    },
    # ------------------------------------------------------------------ Fast Reroute
    {
        "kind": "m_frr",
        "title": "MPLS-TE Fast Reroute の登場人物",
        "diagram": None,
        "exhibit": None,
        "text": (
            "MPLS-TE の Fast Reroute は、障害点の直前にいる上流ルータ «plr» が、あらかじめ用意した «backup» へ保護対象 LSP を局所的に載せ替えることで、"
            "ヘッドエンドの再計算を待たずに転送を続ける仕組みである。1 本のリンクだけを迂回して隣のルータで元の LSP に合流するトンネルは «nhop» で、"
            "«link_prot» を提供する。次のルータそのものを迂回してその先で合流するトンネルは «nnhop» で、«node_prot» に加えてリンク障害も守れる。"
            "両方が使えるとき IOS は後者を優先する。バックアップが元の LSP に戻る合流点のルータは «mp» と呼ぶ。"
            "LSP 側で保護を要求するのは «frr_cmd»、保護するインターフェース側で迂回用のトンネルを結び付けるのは «bp_cmd» である。"
        ),
        "slots": {
            "plr": {"a": "PLR(Point of Local Repair)", "d": ["MP(Merge Point)", "ヘッドエンド"], "why": "切り替えを行う障害点直前の上流ルータが PLR"},
            "backup": {"a": "バックアップトンネル", "d": ["プライマリトンネル", "セカンダリ IGP 経路"], "why": "FRR は事前確立したバックアップトンネルへ載せ替える"},
            "nhop": {"a": "NHOP(next-hop)トンネル", "d": ["NNHOP(next-next-hop)トンネル"], "why": "隣(next hop)で合流するのが NHOP= リンク保護"},
            "link_prot": {"a": "リンク保護", "d": ["ノード保護", "パス保護"], "why": "NHOP はリンク保護"},
            "nnhop": {"a": "NNHOP(next-next-hop)トンネル", "d": ["NHOP(next-hop)トンネル"], "why": "次の次(next-next hop)で合流するのが NNHOP= ノード保護"},
            "node_prot": {"a": "ノード保護", "d": ["リンク保護", "帯域保護"], "why": "NNHOP はノード保護"},
            "mp": {"a": "MP(Merge Point)", "d": ["PLR(Point of Local Repair)", "テールエンド"], "why": "合流点は MP"},
            "frr_cmd": {"a": "tunnel mpls traffic-eng fast-reroute", "d": ["mpls traffic-eng backup-path", "mpls traffic-eng tunnels"], "why": "トンネル IF で保護を要求するのは fast-reroute"},
            "bp_cmd": {"a": "mpls traffic-eng backup-path", "d": ["tunnel mpls traffic-eng fast-reroute", "tunnel mpls traffic-eng path-option"], "why": "物理 IF にバックアップトンネルを結ぶのは backup-path"},
        },
    },
    # ------------------------------------------------------------------ MP-BGP 設定例
    {
        "kind": "m_mpbgp_cfg",
        "title": "PE の MP-BGP 設定と各アドレスファミリが担う範囲",
        "diagram": DIAG_LINE,
        "exhibit": (
            "vrf definition {vrf}\n"
            " rd {asn}:{rdn}\n"
            " address-family ipv4\n"
            "  route-target export {asn}:{rtn}\n"
            "  route-target import {asn}:{rtn}\n"
            "!\n"
            "interface {ce_if}\n"
            " vrf forwarding {vrf}\n"
            " ip address {pe_ce_ip} 255.255.255.252\n"
            "!\n"
            "router bgp {asn}\n"
            " neighbor {pe2_lo} remote-as {asn}\n"
            " neighbor {pe2_lo} update-source Loopback0\n"
            " !\n"
            " address-family «af_core»\n"
            "  neighbor {pe2_lo} «activate»\n"
            "  neighbor {pe2_lo} send-community «extended»\n"
            " !\n"
            " address-family ipv4 vrf {vrf}\n"
            "  neighbor {ce_ip} remote-as {ce_asn}\n"
            "  neighbor {ce_ip} «activate»\n"
            "  neighbor {ce_ip} «asoverride»\n"
        ),
        "text": (
            "上は PE1 の設定である。`address-family «af_core»` 配下のネイバー {pe2_lo} は «core_side» に属する対向 PE で、"
            "この AF で VRF {vrf} の経路が RD {asn}:{rdn} 付きの VPNv4 経路と VPN ラベルとして交換される。"
            "RT は BGP の拡張コミュニティなので、この AF で `send-community «extended»` が無いと RT が伝わらず、対向 PE はどの VRF にも取り込めない。"
            "ネイバーアドレスに «lo0» を使うのは、その /32 に対して LDP が配るラベルがそのまま VPN パケットのトランスポートラベルになるからである。"
            "`address-family ipv4 vrf {vrf}` 配下のネイバー {ce_ip} は «cust_side» に属し、ここで学んだ経路は «vrf_rib» にだけ入る。"
            "両拠点の CE が同じ AS {ce_asn} を使うため、PE から CE へ広告する際に «asoverride» で AS_PATH 中の {ce_asn} を {asn} に書き換えないと、"
            "受け取った CE が自 AS を見つけてループ検出で捨ててしまう。"
        ),
        "slots": {
            "af_core": {"a": "vpnv4", "d": ["ipv4 unicast", "ipv4 vrf " + "{vrf}"], "why": "PE-PE で VPNv4 経路を交換する AF は vpnv4"},
            "activate": {"a": "activate", "d": ["next-hop-self", "route-reflector-client"], "why": "AF でネイバーを有効化するのは activate。next-hop-self は iBGP の次ホップ書き換え"},
            "extended": {"a": "extended", "d": ["standard"], "why": "RT は拡張コミュニティ。standard では RT が付かない"},
            "core_side": {"a": "プロバイダ網内(PE-PE の iBGP)", "d": ["顧客側(PE-CE の eBGP)", "P ルータとの間"], "why": "vpnv4 のピアは同一 AS の PE 同士(iBGP)。P とは BGP を張らない"},
            "lo0": {"a": "Loopback0 の /32 アドレス", "d": ["PE-CE リンクのアドレス", "P ルータのアドレス"], "why": "ネクストホップ=ループバック/32 に LDP ラベルが付くことがトランスポートの前提"},
            "cust_side": {"a": "顧客側(PE-CE の eBGP)", "d": ["プロバイダ網内(PE-PE の iBGP)", "P ルータとの間"], "why": "ipv4 vrf 配下は CE との eBGP"},
            "vrf_rib": {"a": "VRF {vrf} の経路表", "d": ["グローバル経路表", "LFIB"], "why": "VRF 配下の AF で学んだ経路はその VRF の RIB にだけ入る"},
            "asoverride": {"a": "as-override", "d": ["allowas-in", "remove-private-as"], "why": "PE 側で CE の AS を自 AS に書き換えるのが as-override。allowas-in は受信側(CE)で許容する設定"},
        },
        "vars": {
            "asn": ["65000", "65100", "64512", "65500"],
            "vrf": ["CUST_A", "BLUE", "TENANT1", "ACME"],
            "rdn": ["10", "20", "100", "200"],
            "rtn": ["10", "20", "100", "200"],
            "pe2_lo": ["2.2.2.2", "10.255.0.2", "192.168.255.2", "172.31.255.2"],
            "ce_if": ["GigabitEthernet0/1", "Ethernet0/2", "GigabitEthernet0/0/1"],
            "pe_ce_ip": ["192.168.1.1", "10.10.1.1", "172.16.100.1"],
            "ce_ip": ["192.168.1.2", "10.10.1.2", "172.16.100.2"],
            "ce_asn": ["65001", "65010", "64600"],
        },
        "var_links": {"pe_ce_ip": "ce_ip"},  # 同じ添字で選ぶ(同一サブネットにする)
    },
    # ------------------------------------------------------------------ 経路伝搬の流れ
    {
        "kind": "m_flow",
        "title": "顧客経路が対向拠点へ届くまで",
        "diagram": DIAG_LINE,
        "exhibit": None,
        "text": (
            "CE1 が広告した 172.16.1.0/24 が対向拠点の CE2 に届くまでを追う。PE1 は PE-CE の経路交換で受け取った経路を «vrf_rib» に入れる。"
            "それが BGP へ再配送または VRF 配下の AF で受信されると、PE1 は VRF に設定した RD を前置し、«export» の RT を付けて «vpnv4_table» に載せる。"
            "同時に PE1 はこの経路に «vpnlabel» を割り当てる(既定はプレフィックスごと)。"
            "MP-iBGP で PE2 に届くと、PE2 は自分の各 VRF の «import» 一覧と経路の RT を突き合わせ、一致した VRF にだけ取り込む。"
            "ネクストホップは PE1 の «nexthop» のままなので、PE2 からそこへ至る LSP が IGP と LDP で完成している必要があり、"
            "無ければ経路はベストにならず VRF に入らない。確認は、VPNv4 表全体なら `show ip bgp vpnv4 «all»`、"
            "特定 VRF の分だけなら `show ip route vrf <名前>` を使う。"
        ),
        "slots": {
            "vrf_rib": {"a": "VRF の経路表", "d": ["グローバル経路表", "VPNv4 BGP テーブル"], "why": "CE から学んだ経路はまず VRF の RIB"},
            "export": {"a": "export", "d": ["import", "both"], "why": "送出時に付けるのは export 側 RT"},
            "vpnv4_table": {"a": "VPNv4 BGP テーブル", "d": ["LFIB", "IPv4 unicast BGP テーブル"], "why": "RD 付きの経路が入るのは VPNv4 テーブル"},
            "vpnlabel": {"a": "VPN ラベル", "d": ["LDP ラベル", "TE ラベル"], "why": "PE が顧客経路に割り当てるのは VPN ラベル"},
            "import": {"a": "import", "d": ["export", "redistribute"], "why": "受信 PE の突き合わせは import 一覧"},
            "nexthop": {"a": "Loopback アドレス(/32)", "d": ["PE-CE リンクのアドレス", "CE1 のアドレス"], "why": "update-source Loopback0 のため NH は PE1 の Lo0。ここへの LSP が必須"},
            "all": {"a": "all", "d": ["vrf", "summary"], "why": "VPNv4 表全体は all。vrf は特定 VRF 分だけ"},
        },
    },
    # ------------------------------------------------------------------ VPN ラベル割当モード
    {
        "kind": "m_label_mode",
        "title": "VPN ラベルの割り当てモード",
        "diagram": None,
        "exhibit": None,
        "text": (
            "出口 PE が VPN ラベルをどう割り当てるかには 2 つのモードがある。IOS XE の既定は «perprefix» で、CE から学んだ経路 1 つずつに別のラベルを割り当てるため、"
            "出口 PE は «lfib_lookup» だけで出力インターフェースと次ホップを決められる。"
            "一方 VRF 単位のモードを有効にすると VRF 全体で 1 つの集約ラベルになり、出口 PE はラベルで «vrf_ident» を特定した後に、その中で IP 宛先の経路検索を行う。"
            "«resource» の消費を抑えたい多 VRF 環境で使い、コマンドは `mpls label mode vrf <名前> protocol bgp-vpnv4 «mode_kw»`、"
            "割り当て結果は `show ip bgp vpnv4 all «labels_kw»` で確認する。なお PE 自身に由来する経路(connected や Null0 宛の集約)は既定でも VRF 単位の集約ラベルになる。"
        ),
        "slots": {
            "perprefix": {"a": "per-prefix", "d": ["per-vrf", "per-ce"], "why": "既定はプレフィックスごとのラベル"},
            "lfib_lookup": {"a": "ラベル(LFIB)の検索", "d": ["IGP 経路の検索", "ARP 解決"], "why": "per-prefix ならラベルだけで出力先が決まる"},
            "vrf_ident": {"a": "所属 VRF", "d": ["出力インターフェース", "次ホップ"], "why": "集約ラベルが示すのは VRF まで。出力先は IP 検索で決める"},
            "resource": {"a": "ラベル数(メモリ)", "d": ["帯域", "TCAM の ACL エントリ"], "why": "per-vrf の目的はラベル消費の削減"},
            "mode_kw": {"a": "per-vrf", "d": ["per-prefix", "aggregate"], "why": "VRF 単位に切り替えるキーワードは per-vrf"},
            "labels_kw": {"a": "labels", "d": ["summary", "neighbors"], "why": "ラベル割当は show ip bgp vpnv4 all labels"},
        },
    },
    # ------------------------------------------------------------------ PE-CE プロトコル固有の問題
    {
        "kind": "m_pece",
        "title": "PE-CE プロトコルごとの MPLS 越え固有の問題",
        "diagram": None,
        "exhibit": None,
        "text": (
            "PE-CE 間のプロトコルごとに、MPLS 網を越えることで生じる固有の問題がある。"
            "eBGP では全拠点の CE が同じ AS 番号を使うと、対向 PE から届く経路の AS_PATH に自 AS が含まれるため CE が捨てる。"
            "対策は PE 側で «asoverride» を設定して CE の AS を自 AS に置き換えるか、CE 側で «allowasin» を設定して自 AS の重複を許容することである。"
            "OSPF では、PE が MP-BGP から学んだ対向拠点の経路を CE へ «lsa_type» として広告する(既定= 同じドメイン ID のとき)。"
            "拠点間にバックドアリンクがあると LSA Type-1 で学ぶバックドア経路の方が常に優先されるので、これを避けるには PE 間に «shamlink» を張り、"
            "MPLS 網も同じエリア内のリンクに見せて Type-1 のまま «metric» で比較させる。"
            "EIGRP では拠点への逆流によるループ防止に «soo» 拡張コミュニティを使い、同じ値が付いた経路は同じ値を持つインターフェースへ再広告しない。"
            "OSPF の場合はさらに、MP-BGP から再配送された経路の LSA に «dnbit» が立ち、別の PE がそれを再び BGP へ取り込むループを防ぐ。"
        ),
        "slots": {
            "asoverride": {"a": "as-override", "d": ["allowas-in", "local-as"], "why": "PE 側で書き換えるのが as-override"},
            "allowasin": {"a": "allowas-in", "d": ["as-override", "soft-reconfiguration"], "why": "受信側(CE)で自 AS を許容するのが allowas-in"},
            "lsa_type": {"a": "Type-3(Inter-Area) LSA", "d": ["Type-1(Router) LSA", "Type-5(External) LSA"], "why": "同じドメイン ID なら PE はエリア間経路(Type-3)として広告。ドメイン ID が違えば Type-5"},
            "shamlink": {"a": "sham-link", "d": ["virtual-link", "GRE トンネル"], "why": "PE 間の見せかけのエリア内リンクは sham-link。virtual-link はエリア 0 接続用"},
            "metric": {"a": "コスト(メトリック)", "d": ["AD(管理距離)", "プレフィックス長"], "why": "同じ Type-1 同士ならコストで比較できる"},
            "soo": {"a": "SoO(Site of Origin)", "d": ["RT(Route Target)", "RD(Route Distinguisher)"], "why": "拠点起源を示して逆流を止めるのは SoO"},
            "dnbit": {"a": "DN ビット(down bit)", "d": ["E ビット", "P ビット"], "why": "PE が生成した LSA に立つのは DN ビット"},
        },
    },
    # ================================================================== 追加(2026-09-19 午後・ユーザ要望= LDP/RSVP-TE/ラベルの中身と番号を厚く)
    # ------------------------------------------------------------------ ラベルヘッダの中身・TTL・MTU
    {
        "kind": "m_label_hdr",
        "title": "ラベルヘッダの中身と TTL・MTU への影響",
        "diagram": None,
        "exhibit": None,
        "text": (
            "MPLS のラベルスタックエントリ(shim ヘッダ)は 1 つ «entry_len» ビットで、先頭から «label_bits» ビットのラベル値、"
            "3 ビットの «tc»(QoS 用・旧称 EXP)、1 ビットの «sbit»、8 ビットの TTL の順に並ぶ。"
            "ラベル値のビット幅から理論上は 0〜1,048,575 だが、0〜15 は予約されているため動的に割り当てられるのは «dyn_min» 以上である。"
            "入口 LSR は既定で IP ヘッダの TTL をラベルの TTL に «ttl_copy» し、出口で戻す。この既定を `no mpls ip propagate-ttl «fwd_kw»` で"
            "顧客から転送されるパケットだけ無効にすると、ラベル TTL が 255 から始まるため顧客の traceroute に P ルータが «hide» ようになる。"
            "ラベル 1 枚につき «label_bytes» バイト増えるので、{stack_desc}の {depth} 段ラベルなら IP 1500 バイトのパケットは «total» バイトになり、"
            "網内リンクの `mpls mtu` を上げないと断片化や破棄が起こる。"
        ),
        "slots": {
            "entry_len": {"a": "32", "d": ["20", "40"], "why": "20+3+1+8 で 32 ビット(4 バイト)"},
            "label_bits": {"a": "20", "d": ["16", "24"], "why": "ラベル値は 20 ビット"},
            "tc": {"a": "TC(Traffic Class)", "d": ["DSCP", "CoS"], "why": "ラベル内の 3 ビットは TC(旧 EXP)。DSCP は IP ヘッダ、CoS は 802.1Q"},
            "sbit": {"a": "S(Bottom of Stack)", "d": ["フラグメント", "優先度"], "why": "1 ビットはスタックの底を示す S"},
            "dyn_min": {"a": "16", "d": ["0", "1024"], "why": "0〜15 が予約なので動的ラベルは 16 から"},
            "ttl_copy": {"a": "コピー(伝搬)", "d": ["255 に固定", "1 に設定"], "why": "既定は propagate-ttl 有効= IP TTL をコピー"},
            "fwd_kw": {"a": "forwarded", "d": ["local", "all"], "why": "forwarded= 転送パケットだけ(顧客向け)。local= 自分発のパケットだけ"},
            "hide": {"a": "現れない", "d": ["2 回ずつ現れる", "逆順に現れる"], "why": "P で TTL が尽きないので途中ホップが見えなくなる"},
            "label_bytes": {"a": "4", "d": ["8", "2"], "why": "1 ラベル= 32 ビット= 4 バイト"},
            "total": {"a": "{total}", "d": ["{total_alt}", "{total_x2}"], "why": "1500 + 4×{depth}= {total}"},
        },
        "vars": {"depth": ["2", "3"],
                 "stack_desc": lambda v, w: "L3VPN" if v["depth"] == "2" else "TE トンネル上の L3VPN(TE+LDP+VPN)",
                 "total": lambda v, w: 1500 + 4 * int(v["depth"]),
                 "total_alt": lambda v, w: 1500 + 4 * (int(v["depth"]) + (1 if v["depth"] == "2" else -1)),
                 "total_x2": lambda v, w: 1500 + 8 * int(v["depth"])},
    },
    # ------------------------------------------------------------------ 予約ラベルの番号
    {
        "kind": "m_reserved",
        "title": "予約ラベル 0〜15 の意味",
        "diagram": None,
        "exhibit": (
            '| ラベル値 | 名称 | 意味 |\n'
            '|---|---|---|\n'
            '| «l0» | IPv4 Explicit Null | ラベルを付けたまま出口へ。出口が pop して IPv4 として処理 |\n'
            '| «l1» | Router Alert | 受信ルータが制御プレーンで検査する |\n'
            '| «l2» | IPv6 Explicit Null | 同上(IPv6) |\n'
            '| «l3» | Implicit Null | 実際には付かない。手前のルータに pop させる(PHP) |\n'
            '| 4〜15 | 予約 | 7=ELI, 13=GAL, 14=OAM Alert など |\n'
        ),
        "exhibit_md": True,
        "text": (
            "上の表は予約ラベルの一覧である。IOS の LDP は、自分に直結する FEC(ループバック /32 など)に対して既定で «default_adv» を隣接に広告する。"
            "そのため 1 つ手前の LSR が先頭ラベルを外す «php» が起こり、出口 LSR はラベル検索と IP 検索の «two_lookup» を避けられる。"
            "ただし先頭ラベルが外れると TC(EXP) の値も一緒に失われるので、出口で QoS 情報を使いたい場合は `mpls ldp explicit-null` で «expnull» を広告させ、"
            "出口 LSR 自身に pop させる(«uhp»)。この値を受け取った手前の LSR はラベルを外さずその値に swap して送るため、出口には必ずラベルが付いて届く。"
            "なお予約ラベルはどれも LDP が動的に配る値としては使われず、`show mpls forwarding-table` の Outgoing 列に «popdisp» と表示されるのが、隣接から PHP を求められている印である。"
        ),
        "slots": {
            "l0": {"a": "0", "d": ["3", "15"], "grp": "labels", "why": "IPv4 Explicit Null は 0"},
            "l1": {"a": "1", "d": ["14", "2"], "grp": "labels", "why": "Router Alert は 1"},
            "l2": {"a": "2", "d": ["6", "0"], "grp": "labels", "why": "IPv6 Explicit Null は 2"},
            "l3": {"a": "3", "d": ["0", "1"], "grp": "labels", "why": "Implicit Null は 3"},
            "default_adv": {"a": "Implicit Null", "d": ["Explicit Null", "Router Alert"], "why": "既定は imp-null= PHP を要求"},
            "php": {"a": "PHP(Penultimate Hop Popping)", "d": ["UHP(Ultimate Hop Popping)", "ラベルスワップ"], "why": "手前で pop するのが PHP"},
            "two_lookup": {"a": "二重検索", "d": ["再帰検索", "逆引き"], "why": "PHP の目的は出口での 2 回検索の回避"},
            "expnull": {"a": "Explicit Null", "d": ["Implicit Null", "Router Alert"], "why": "TC を残すには exp-null で出口まで運ぶ"},
            "uhp": {"a": "UHP(Ultimate Hop Popping)", "d": ["PHP(Penultimate Hop Popping)", "ラベルスタッキング"], "why": "出口自身が外すのが UHP"},
            "popdisp": {"a": "Pop Label", "d": ["No Label", "Aggregate"], "why": "imp-null 受信= Pop Label。No Label は出力ラベルが無い(隣接が LDP を話さない等)"},
        },
    },
    # ------------------------------------------------------------------ LDP メッセージ・タイマ・モード
    {
        "kind": "m_ldp_msgs",
        "title": "LDP のメッセージ種別・タイマ・動作モード",
        "diagram": None,
        "exhibit": None,
        "text": (
            "LDP のメッセージは 4 種類に分かれる。隣接発見の «discovery»(Hello・UDP 646)、セッションの確立と維持の «session»(Initialization/KeepAlive)、"
            "ラベルの広告と取り消しの «advert»(Label Mapping/Withdraw/Release)、そしてエラー通知の Notification である。Hello 以外は TCP 646 のセッション上で運ばれる。"
            "セッションは KeepAlive で維持され、IOS の既定では保持時間 «sess_hold» 秒・KeepAlive 間隔はその 1/3 の «ka_int» 秒で、双方の設定値のうち小さい方が採用される。"
            "非直結の Targeted Hello は既定で «thello_int» 秒間隔・保持 90 秒と、Link Hello(5 秒/15 秒)より緩い。"
            "ラベルの保持方式は既定で «retention» で、ネクストホップでない隣接から受けたバインディングも LIB に残すため、経路変化時に再要求なしで切り替えられる。"
            "配布の制御は既定で «control» で、下流からのラベルを待たずに各 LSR が独立にラベルを割り当てて広告する。"
            "セッションの認証は `mpls ldp neighbor <peer> password <pw>` の «md5» で、不一致だとセッションが確立しない。"
        ),
        "slots": {
            "discovery": {"a": "Discovery", "d": ["Session", "Notification"], "why": "Hello は Discovery メッセージ"},
            "session": {"a": "Session", "d": ["Advertisement", "Discovery"], "why": "Initialization/KeepAlive は Session メッセージ"},
            "advert": {"a": "Advertisement", "d": ["Session", "Notification"], "why": "Label Mapping などは Advertisement"},
            "sess_hold": {"a": "180", "d": ["90", "15"], "why": "mpls ldp holdtime の既定は 180 秒"},
            "ka_int": {"a": "60", "d": ["30", "5"], "why": "KeepAlive は保持時間の 1/3= 60 秒"},
            "thello_int": {"a": "10", "d": ["5", "30"], "why": "Targeted Hello の既定間隔は 10 秒(保持 90 秒)"},
            "retention": {"a": "Liberal Retention", "d": ["Conservative Retention", "Ordered Retention"], "why": "IOS 既定は liberal= 全バインディングを保持"},
            "control": {"a": "Independent Control", "d": ["Ordered Control", "Downstream on Demand"], "why": "IOS 既定は independent= 下流を待たず広告"},
            "md5": {"a": "MD5 認証", "d": ["SHA-256 認証", "IPsec 認証"], "why": "LDP セッション認証は TCP MD5"},
        },
    },
    # ------------------------------------------------------------------ show mpls ldp neighbor の読解
    {
        "kind": "m_ldp_show",
        "title": "show mpls ldp neighbor detail の読み方",
        "diagram": None,
        "worlds": ["peer_passive", "local_passive"],
        "world_desc": {"peer_passive": "相手が 646 で待ち受け(自分の方がアドレスが大きい= 自分がアクティブ)",
                       "local_passive": "自分が 646 で待ち受け(相手の方がアドレスが大きい= 相手がアクティブ)"},
        "exhibit": {
            "peer_passive": (
                "P2# show mpls ldp neighbor detail\n"
                "    Peer LDP Ident: {peer}:0; Local LDP Ident {local}:0\n"
                "        TCP connection: {peer}.646 - {local}.14709; MD5 on\n"
                "        State: Oper; Msgs sent/rcvd: 1020/1019; Downstream\n"
                "        Up time: 02:13:40\n"
                "        LDP discovery sources:\n          Ethernet0/1; Src IP addr: {peer_if}\n"
                "            holdtime: 15000 ms, hello interval: 5000 ms\n"
                "        Addresses bound to peer LDP Ident:\n          {peer}        {peer_if2}       {peer_if}\n"
                "        Peer holdtime: 180000 ms; KA interval: 60000 ms; Peer state: estab\n"
            ),
            "local_passive": (
                "P2# show mpls ldp neighbor detail\n"
                "    Peer LDP Ident: {peer}:0; Local LDP Ident {local}:0\n"
                "        TCP connection: {peer}.23412 - {local}.646; MD5 on\n"
                "        State: Oper; Msgs sent/rcvd: 1020/1019; Downstream\n"
                "        Up time: 02:13:40\n"
                "        LDP discovery sources:\n          Ethernet0/1; Src IP addr: {peer_if}\n"
                "            holdtime: 15000 ms, hello interval: 5000 ms\n"
                "        Addresses bound to peer LDP Ident:\n          {peer}        {peer_if2}       {peer_if}\n"
                "        Peer holdtime: 180000 ms; KA interval: 60000 ms; Peer state: estab\n"
            ),
        },
        "text": (
            "上は P2({local})で採った出力である。`Peer LDP Ident` の値は相手の «ident» とラベル空間 ID の組で、末尾の :0 は «lspace» を意味する。"
            "`TCP connection` の行で、ポート 646 で待ち受けているのは «passive» 側で、一時ポートを使っている «active» 側が接続を開始した。"
            "これはトランスポートアドレス(既定はルータ ID)の «bigger» 方がアクティブになる規則と一致する。"
            "`State: Oper` はセッション確立済み、`Downstream` はラベル配布が «du» であることを示す。"
            "`Addresses bound to peer` が重要なのは、自分の RIB のネクストホップ({peer_if})がこの一覧に含まれていて初めて、相手から受けたラベルを LFIB に採用できるからである。"
        ),
        "slots": {
            "ident": {"a": "LDP ルータ ID", "d": ["インターフェースアドレス", "OSPF ルータ ID"], "why": "LDP Ident= LDP ルータ ID:ラベル空間 ID"},
            "lspace": {"a": "プラットフォーム全体のラベル空間", "d": ["インターフェースごとのラベル空間", "VRF 番号"], "why": ":0 = per-platform label space"},
            "passive": {"a": {"peer_passive": "相手({peer})", "local_passive": "自分({local})"}, "d": ["ネクストホップ({peer_if})"],
                        "why": "646 を持つ側が待ち受け(パッシブ)"},
            "active": {"a": {"peer_passive": "自分({local})", "local_passive": "相手({peer})"}, "d": ["ネクストホップ({peer_if})"],
                       "why": "一時ポート側が接続を開始(アクティブ)"},
            "bigger": {"a": "大きい", "d": ["小さい"], "why": {"peer_passive": "{local} > {peer}", "local_passive": "{peer} > {local}"}},
            "du": {"a": "Downstream Unsolicited", "d": ["Downstream on Demand", "Upstream Assigned"], "why": "Downstream 表示= DU モード"},
        },
        "vars": {"local": ["10.0.0.4"],
                 "peer": {"peer_passive": ["10.0.0.3", "10.0.0.2"], "local_passive": ["10.0.0.5", "10.0.0.9"]},
                 "peer_if": ["10.0.34.3", "10.0.24.2"], "peer_if2": ["10.0.13.3", "10.0.12.2"]},
        "var_links": {"peer_if": "peer_if2"},
    },
    # ------------------------------------------------------------------ show mpls forwarding-table の読解
    {
        "kind": "m_lfib_read",
        "title": "show mpls forwarding-table の読み方(PE の LFIB)",
        "diagram": DIAG_LINE,
        "exhibit": (
            "PE1# show mpls forwarding-table\n"
            "Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop\n"
            "Label      Label      or Tunnel Id     Switched      interface\n"
            "16         Pop Label  10.0.0.2/32      0             Et0/1      10.0.12.2\n"
            "17         {out}         10.0.0.4/32      524160        Et0/1      10.0.12.2\n"
            "18         No Label   10.0.99.0/24     0             Et0/3      10.0.99.9\n"
            "19         No Label   172.16.1.0/24[V] 0             Et0/0      192.168.1.2\n"
            "20         Aggregate  192.168.1.0/30[V] 0\n"
        ),
        "text": (
            "上は PE1 の LFIB である。ローカルラベル 16 の行は、隣接 P1(10.0.0.2)のループバック宛で Outgoing が «pop» になっている。"
            "これは P1 が自分の /32 に対して «impnull» を広告してきたためで、PE1 がその 1 つ手前として PHP を行う。"
            "ローカルラベル 17 の行は対向 PE2(10.0.0.4)宛で、受け取ったパケットのラベルを «swap_out» に付け替えて P1 へ送る。VPN パケットの先頭ラベルはこの行で決まる。"
            "ローカルラベル 18 の行は Outgoing が «nolabel» で、次ホップ 10.0.99.9 との間に LDP セッションが無い(または相手がその FEC を広告していない)ことを示す。"
            "この宛先へラベル付きで届いたパケットは IP パケットに戻して送られるため、その先が VPN 経路なら «lsp_hole» となって通信できない。"
            "末尾に «vmark» が付く 2 行は VRF の経路で、対向 PE から届いた VPN ラベル 19 はそのまま CE へ IP 転送され、"
            "ローカル生成の集約経路に付く «aggregate» は「ラベルで VRF を特定した後に IP 検索する」ことを意味する。"
        ),
        "slots": {
            "pop": {"a": "Pop Label", "d": ["No Label", "Aggregate"], "why": "imp-null を受けた FEC は Pop Label"},
            "impnull": {"a": "Implicit Null(3)", "d": ["Explicit Null(0)", "Router Alert(1)"], "why": "PHP を要求するのは imp-null"},
            "swap_out": {"a": "{out}", "d": ["17", "16"], "why": "Outgoing 列の {out} に swap(Local 17 → Outgoing {out})"},
            "nolabel": {"a": "No Label", "d": ["Pop Label", "Untagged VRF"], "why": "出力ラベルが無い= 次ホップから当該 FEC のラベルを受けていない"},
            "lsp_hole": {"a": "LSP の穴(ブラックホール)", "d": ["ルーティングループ", "PHP"], "why": "途中でラベルが外れると出口 PE は VPN ラベルを失い、P は VPN 経路を知らないので捨てる"},
            "vmark": {"a": "[V]", "d": ["[T]", "[A]"], "why": "[V]= VRF 経路。[T]= TE トンネル経由"},
            "aggregate": {"a": "Aggregate", "d": ["Pop Label", "No Label"], "why": "Aggregate= per-VRF 集約ラベル(IP 再検索)"},
        },
        "vars": {"out": ["23", "31", "42", "58"]},
    },
    # ------------------------------------------------------------------ TE トンネルの設定手順
    {
        "kind": "m_te_cfg",
        "scope": "beyond",   # ★ENARSI 範囲外(2026-09-19 ユーザ判断)= 既定の出題から外す。--kinds で明示したときだけ
        "title": "MPLS-TE トンネルを立てるための設定",
        "diagram": DIAG_LINE,
        "exhibit": (
            "! --- 全ルータ(PE1/P1/P2/PE2)共通 ---\n"
            "mpls traffic-eng tunnels\n"
            "!\n"
            "interface Ethernet0/1\n"
            " mpls traffic-eng tunnels\n"
            " «rsvp_bw» {bw_link}\n"
            "!\n"
            "router ospf 1\n"
            " «te_rid» Loopback0\n"
            " «te_area» 0\n"
            "!\n"
            "! --- ヘッドエンド PE1 だけ ---\n"
            "interface Tunnel{tun}\n"
            " ip unnumbered Loopback0\n"
            " tunnel destination {pe2_lo}\n"
            " tunnel mode mpls traffic-eng\n"
            " tunnel mpls traffic-eng bandwidth {bw_tun}\n"
            " tunnel mpls traffic-eng priority {prio} {prio}\n"
            " tunnel mpls traffic-eng path-option 1 «po_expl» name VIA-P2\n"
            " tunnel mpls traffic-eng path-option 2 «po_dyn»\n"
            " tunnel mpls traffic-eng «autoroute»\n"
            "!\n"
            "ip explicit-path name VIA-P2\n"
            " next-address {p2_lo}\n"
            " next-address {pe2_lo}\n"
        ),
        "text": (
            "MPLS-TE は 3 か所の設定がそろって初めて動く。第 1 に全ルータで TE を有効にし、TE リンクにする各インターフェースで «rsvp_bw» により "
            "RSVP が予約できる帯域(kbps)を宣言する。第 2 に IGP に TE 拡張を有効にする。OSPF では «te_rid» で TE ルータ ID を、"
            "«te_area» で TE 情報(利用可能帯域・属性フラグ・TE メトリック)を Opaque LSA(Type 10)で洪水させるエリアを指定する。IS-IS なら "
            "`metric-style wide` が必須になる。第 3 にヘッドエンドだけがトンネルインターフェースを持つ。トンネルは «unidir» なので、"
            "対向からの通信にも TE を使うなら PE2 側にも別のトンネルが要る。path-option は番号の «po_order» ものから試され、"
            "1 番の «po_expl» は `ip explicit-path` で列挙したホップ順を ERO に載せ、2 番の «po_dyn» は CSPF が制約(帯域 {bw_tun} kbps・優先度 {prio})を満たす経路を計算する。"
            "最後の «autoroute» が無いと、トンネルは張られても IGP の経路計算に使われず、トラフィックが載らない。"
        ),
        "slots": {
            "rsvp_bw": {"a": "ip rsvp bandwidth", "d": ["bandwidth", "mpls traffic-eng bandwidth"], "why": "RSVP の予約可能帯域は ip rsvp bandwidth。bandwidth は IGP メトリック用"},
            "te_rid": {"a": "mpls traffic-eng router-id", "d": ["router-id", "mpls ldp router-id"], "why": "TE のルータ ID は mpls traffic-eng router-id"},
            "te_area": {"a": "mpls traffic-eng area", "d": ["network … area", "area … stub"], "why": "TE 情報を流すエリアは mpls traffic-eng area"},
            "unidir": {"a": "単方向", "d": ["双方向", "マルチポイント"], "why": "TE トンネルは片方向。ip unnumbered にする理由でもある"},
            "po_order": {"a": "小さい", "d": ["大きい"], "why": "path-option は番号が小さいものが優先"},
            "po_expl": {"a": "explicit", "d": ["dynamic", "static"], "why": "経路を明示するのは explicit name …"},
            "po_dyn": {"a": "dynamic", "d": ["explicit", "auto"], "why": "CSPF に計算させるのは dynamic"},
            "autoroute": {"a": "autoroute announce", "d": ["forwarding-adjacency", "path-selection metric te"], "why": "ヘッドエンドの IGP にトンネルを使わせるのは autoroute announce"},
        },
        "vars": {
            "bw_link": ["100000", "50000", "200000"],
            "bw_tun": ["10000", "20000", "5000"],
            "prio": ["7", "5", "3"],
            "tun": ["1", "10", "100"],
            "pe2_lo": ["10.0.0.4", "2.2.2.2", "192.168.255.4"],
            "p2_lo": ["10.0.0.3", "3.3.3.3", "192.168.255.3"],
        },
        "var_links": {"pe2_lo": "p2_lo"},
    },
    # ------------------------------------------------------------------ RSVP-TE のオブジェクトと優先度・アフィニティ
    {
        "kind": "m_te_signal",
        "scope": "beyond",   # ★ENARSI 範囲外(2026-09-19 ユーザ判断)= 既定の出題から外す。--kinds で明示したときだけ
        "title": "RSVP-TE のオブジェクト・優先度・アフィニティ",
        "diagram": None,
        "exhibit": None,
        "text": (
            "ヘッドエンドが送る PATH メッセージには、通す経路を列挙した «ero»、要求帯域を示す «tspec»、下流にラベル割当を求める «lreq»、"
            "そしてトンネルの優先度や保護要求などを運ぶ «sattr» が入る。テールエンドから返る RESV メッセージには、各ホップが割り当てたラベルを運ぶ «lobj» と、"
            "通過ホップと保護状態を記録した RRO が入る。RSVP は «softstate» なので、PATH/RESV は既定で «refresh» 秒ごとに再送され、届かなくなった状態はやがて消える。"
            "優先度は setup と hold の 2 値(«prio_range»・小さいほど高い)で、新しいトンネルの setup 優先度が既存トンネルの hold 優先度より高ければ帯域を «preempt» できる。"
            "リンクには 32 ビットの属性フラグ(`mpls traffic-eng attribute-flags`)を付けられ、トンネル側の «affinity» と mask で"
            "「このビットが立つリンクだけ通す/避ける」という制約を CSPF に与える。"
        ),
        "slots": {
            "ero": {"a": "ERO(Explicit Route Object)", "d": ["RRO(Record Route Object)", "FLOWSPEC"], "why": "経路の指定は ERO"},
            "tspec": {"a": "SENDER_TSPEC", "d": ["FLOWSPEC", "FILTER_SPEC"], "why": "送信側の帯域要求は SENDER_TSPEC(FLOWSPEC は RESV 側)"},
            "lreq": {"a": "LABEL_REQUEST", "d": ["LABEL", "LABEL_SET"], "why": "PATH で要求するのは LABEL_REQUEST。LABEL は RESV"},
            "sattr": {"a": "SESSION_ATTRIBUTE", "d": ["SESSION", "STYLE"], "why": "優先度・保護要求・名前は SESSION_ATTRIBUTE"},
            "lobj": {"a": "LABEL", "d": ["LABEL_REQUEST", "ERO(Explicit Route Object)"], "why": "RESV で配るラベルは LABEL オブジェクト"},
            "softstate": {"a": "ソフトステート", "d": ["ハードステート", "コネクションレス"], "why": "RSVP は定期リフレッシュで状態を保つソフトステート"},
            "refresh": {"a": "30", "d": ["60", "180"], "why": "リフレッシュ間隔の既定は 30 秒"},
            "prio_range": {"a": "0〜7", "d": ["1〜255", "0〜15"], "why": "優先度は 0〜7。既定は 7 7(最低)"},
            "preempt": {"a": "プリエンプト(横取り)", "d": ["共有", "分割"], "why": "setup が相手の hold より高ければ既存 LSP を退ける"},
            "affinity": {"a": "affinity", "d": ["metric", "bandwidth"], "why": "属性フラグと突き合わせる値は affinity"},
        },
    },
    # ------------------------------------------------------------------ TE トンネルへのトラフィック誘導と経路計算
    {
        "kind": "m_te_routing",
        "scope": "beyond",   # ★ENARSI 範囲外(2026-09-19 ユーザ判断)= 既定の出題から外す。--kinds で明示したときだけ
        "title": "TE トンネルにトラフィックを載せる方法と経路の再計算",
        "diagram": None,
        "exhibit": None,
        "text": (
            "TE トンネルが張られただけではトラフィックは載らない。ヘッドエンドだけの経路計算でトンネルを使わせるのが «autoroute» で、"
            "テールエンドとその先の宛先への経路がトンネル経由に置き換わる。これに対し «fa» はトンネルを IGP のリンクとして広告するので、"
            "ヘッドエンド以外のルータもそのトンネルを最短路計算に使える。両者は同じトンネルに併用しない。"
            "宛先を限定したいときは、トンネルインターフェースを次ホップにした «static» でもよい。"
            "CSPF が使うリンクコストは既定で «te_metric» で、`mpls traffic-eng administrative-weight` を設定しなければ IGP メトリックと同じ値になる。"
            "トンネル単位で `tunnel mpls traffic-eng path-selection metric «igp_kw»` とすれば IGP メトリックで計算させられる。"
            "張られた LSP は既定で «reopt» 秒ごとに再最適化(より良い経路があれば張り替え)され、切り替えは新 LSP を張ってから旧 LSP を落とす «mbb» で無停止に行う。"
        ),
        "slots": {
            "autoroute": {"a": "autoroute announce", "d": ["forwarding adjacency", "policy-based routing"], "why": "ヘッドエンドローカルで IGP にトンネルを使わせる"},
            "fa": {"a": "forwarding adjacency", "d": ["autoroute announce", "sham-link"], "why": "トンネルを IGP のリンクとして広告するのは forwarding adjacency"},
            "static": {"a": "スタティックルート", "d": ["デフォルトルート", "再配送"], "why": "ip route … Tunnel1 で宛先限定に誘導できる"},
            "te_metric": {"a": "TE メトリック", "d": ["IGP メトリック", "帯域"], "why": "IOS の CSPF 既定は TE メトリック(未設定なら IGP メトリックと同値)"},
            "igp_kw": {"a": "igp", "d": ["te", "ospf"], "why": "path-selection metric igp"},
            "reopt": {"a": "3600", "d": ["30", "300"], "why": "reoptimize timers frequency の既定は 3600 秒(1 時間)"},
            "mbb": {"a": "make-before-break", "d": ["break-before-make", "fast reroute"], "why": "先に新 LSP を張る= make-before-break"},
        },
    },
    # ------------------------------------------------------------------ LDP と RSVP-TE の対比
    {
        "kind": "m_ldp_vs_rsvp",
        "title": "LDP と RSVP-TE の違い",
        "diagram": None,
        "exhibit": None,
        "text": (
            "LDP と RSVP-TE はどちらもトランスポートラベルを配るが、性格が違う。LDP は «ldp_path» に沿って全 FEC のラベルを自動で配る"
            "「敷き詰め型」で、設定は `mpls ip` を各インターフェースに入れるだけと簡単だが、経路を最短路以外に曲げることや帯域の予約は «ldp_bw»。"
            "RSVP-TE は «rsvp_unit» ごとにヘッドエンドが経路を計算して張る「トンネル型」で、帯域予約・明示経路・優先度・«frr» による 50 ミリ秒級の保護が使える代わりに、"
            "トンネル数が増えるとヘッドエンドと途中ルータの «state» が増える。ラベルの割当方向はどちらも «dir» で共通である。"
            "実務では、網全体に LDP を敷き、特定のトラフィックだけ RSVP-TE トンネルに載せる併用が多い。"
            "L3VPN の VPN ラベルは LDP でも RSVP-TE でもなく «vpnlabel_by» が配る点は変わらない。"
        ),
        "slots": {
            "ldp_path": {"a": "IGP の最短路", "d": ["CSPF の計算結果", "明示的なホップ列"], "why": "LDP は IGP に追随するだけ"},
            "ldp_bw": {"a": "できない", "d": ["できる", "既定で有効"], "why": "LDP に帯域予約や経路指定の仕組みは無い"},
            "rsvp_unit": {"a": "トンネル(LSP)", "d": ["FEC", "インターフェース"], "why": "RSVP-TE はトンネル単位で張る"},
            "frr": {"a": "Fast Reroute", "d": ["LDP セッション保護", "BFD"], "why": "事前のバックアップトンネルによる局所保護は TE FRR"},
            "state": {"a": "ソフトステート(維持すべき状態)", "d": ["LIB のエントリ数", "IGP の LSA 数"], "why": "RSVP は LSP ごとに状態をリフレッシュし続ける"},
            "dir": {"a": "下流から上流", "d": ["上流から下流"], "why": "LDP の DU も RSVP の RESV も下流がラベルを決めて上流へ渡す"},
            "vpnlabel_by": {"a": "MP-BGP", "d": ["LDP", "RSVP-TE"], "why": "VPN ラベルは VPNv4 経路と共に MP-BGP が配る"},
        },
    },
]

KINDS = sorted({p["kind"] for p in PASSAGES})
