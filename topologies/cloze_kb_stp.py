#!/usr/bin/env python3
"""cloze_kb_stp.py — 解説穴埋め形(shape=cloze) の知識ベース: STP(U-A3・BL-214)

書式は cloze_kb_mpls.py と同じ(PASSAGES / slots / vars / worlds / n_blanks / exhibit)。kind 接頭辞 `t_`(genre= l2)。
範囲= CCNA 2.5 / ENCOR 3.1.c / CCIE 1.1.e。単元の知識項目表= curriculum/U-A3-stp.md(この KB はその全項目を被覆する)。
セクション= 基礎(t_basics)/ RSTP(t_rstp)/ PVST+・MST(t_modes)/ チューニング(t_tuning)/ 保護機構(t_guard)/ 読解(t_read・世界機構)。

事実の出所:
- IEEE 802.1D/802.1w/802.1s の定義値(タイマ既定 hello 2 / forward delay 15 / max age 20、short パスコスト 100M=19・1G=4・10G=2、
  long 方式 1G=20000・10G=2000、priority 既定 32768・4096 刻み、port priority 既定 128・16 刻み、root primary=24576・secondary=28672、
  errdisable recovery interval 既定 300 秒)。
- poc/stp/README.md(BL-076 PoC・IOSvL2 実測): priority 明示でブロックポートが決定化・BPDU guard の err-disabled は採点可・
  MST リージョン不一致の指紋は `Bound(RSTP)`・IOSvL2 は旧構文 `spanning-tree portfast`(edge キーワード不可)・
  `show spanning-tree` の Bridge ID 表示は `priority 32768 sys-id-ext 10` 形式。
- 読解 passage の exhibit は IOS の `show spanning-tree vlan` の書式を写した(世界で Root/Altn の付くポートが入れ替わる)。
"""

_ROOTMAC = ["0011.2233.aa01", "5254.0012.0f01", "00d0.ba11.0001"]
_MYMAC = ["0011.2233.bb02", "5254.0034.0f02", "00d0.ba22.0002"]
_RNAME = ["REGION1", "CAMPUS", "HQ-MST"]
_REV = ["1", "10", "2026"]

PASSAGES = [
    # ------------------------------------------------------------------ 基礎(802.1D)
    {
        "kind": "t_basics",
        "title": "STP(802.1D)の基礎: root・ポート役割・状態・タイマ",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": (
            "STP(802.1D)は冗長リンクのある L2 網で «purpose» を防ぐため、論理的に木を作って余分なポートを止める。"
            "木の根になる root bridge は «root_rule» のスイッチで、その判定に使う Bridge ID は «bid» で構成される。"
            "BPDU は «bpdu_src» が hello 間隔(既定 «hello» 秒)で送り、他のスイッチはそれを中継しながら自分の情報で書き換える(宛先 MAC は 01:80:C2:00:00:00)。"
            "root 以外の各スイッチは root への合計コストが最小のポートを «rp» に選び、同点なら «rp_tie» で決める。"
            "各セグメントでは root への合計コストが最小のスイッチ側のポートが «dp» になり、root のポートはすべてこれである。"
            "それ以外のポートは «blk» として BPDU を受け取るだけになる。"
            "802.1D のポート状態は blocking → listening → learning → forwarding と進み、listening と learning はそれぞれ forward delay(既定 «fwd» 秒)を待つ。"
            "blocking のポートが動き出す判断は max age(既定 «maxage» 秒)の間 BPDU が来ないことで行うため、間接障害の収束は最大で約 «conv» 秒かかる。"
            "トポロジ変化に気づいたスイッチは «tcn» を root 向きに送り、root が TC フラグ付きの BPDU を流すと、全スイッチは MAC テーブルのエージング時間を forward delay に短縮する。"
        ),
        "slots": {
            "purpose": {"a": "ブリッジングループ(ブロードキャストストーム・MAC テーブルの不安定)", "d": ["ルーティングループ(TTL 切れ)", "VLAN 間の通信", "IP アドレスの重複"], "why": "L2 フレームには TTL が無いのでループは自然に消えない"},
            "root_rule": {"a": "Bridge ID が最小", "d": ["Bridge ID が最大", "MAC アドレスが最大", "アップリンク数が最多"], "grp": "elect", "why": "priority → MAC の順に小さい方が勝つ"},
            "bid": {"a": "priority(4096 刻み)+ extended system ID(VLAN 番号)+ MAC アドレス", "d": ["IP アドレス + MAC アドレス", "priority + ポート番号", "ホスト名 + シリアル番号"], "why": "表示の priority は設定値 + VLAN 番号になる"},
            "bpdu_src": {"a": "root bridge だけ", "d": ["すべてのスイッチ", "designated port を持つスイッチだけ"], "grp": "bpdu", "why": "802.1D では root が起点。RSTP は全スイッチが出す(対比)"},
            "hello": {"a": "2", "d": ["1", "4", "10"], "grp": "timer", "why": "hello 2 秒"},
            "rp": {"a": "root port", "d": ["designated port", "alternate port", "backup port"], "grp": "role", "why": "root に最も近いポート・スイッチごとに 1 つ"},
            "rp_tie": {"a": "送信元 Bridge ID → 送信元 port priority → 送信元 port ID の順", "d": ["自分のポート番号が小さい方", "リンク速度が速い方", "MAC アドレスが大きい方"], "grp": "elect", "why": "同点の決め方はすべて**対向(送信元)側**の値で決まる"},
            "dp": {"a": "designated port", "d": ["root port", "alternate port", "edge port"], "grp": "role", "why": "セグメントごとに 1 つ・root のポートは全部これ"},
            "blk": {"a": "non-designated(blocking)port", "d": ["designated port", "root port", "edge port"], "grp": "role", "why": "BPDU は受けるがフレームは転送しない"},
            "fwd": {"a": "15", "d": ["10", "30", "5"], "grp": "timer", "why": "forward delay 15 秒 × 2 段"},
            "maxage": {"a": "20", "d": ["10", "30", "6"], "grp": "timer", "why": "max age 20 秒= hello 10 回分"},
            "conv": {"a": "50", "d": ["30", "35", "60"], "grp": "timer", "why": "max age 20 + listening 15 + learning 15"},
            "tcn": {"a": "TCN BPDU", "d": ["Configuration BPDU", "Proposal BPDU", "ICMP Redirect"], "grp": "bpdu", "why": "Topology Change Notification。root port から上流へ"},
        },
    },
    # ------------------------------------------------------------------ RSTP(802.1w)
    {
        "kind": "t_rstp",
        "title": "RSTP(802.1w): 役割・状態・高速収束の仕組み",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": None,
        "text": (
            "RSTP(802.1w)は 802.1D の役割と状態を整理し、収束を «conv» にした。"
            "ポート役割は root・designated に加え、root port の予備である «altn» と、同じセグメントに自分のポートが 2 本ある時の予備である «back» を持つ。"
            "ポート状態は 802.1D の 5 つを三つに畳み、blocking と listening は «disc» にまとめられた。"
            "BPDU は «src» が hello ごとに出し、«miss» 回続けて届かなければ隣接情報を捨てる(802.1D の max age を待たない)。"
            "2 台の間で designated port を即座に forwarding にする仕組みが «pa» で、対向が全二重の «p2p» リンクであることが前提になる(半二重は shared 扱いで 802.1D と同じタイマ待ちになる)。"
            "端末が繋がるポートは «edge» として宣言すると即 forwarding になり、トポロジ変化にも数えられない。"
            "トポロジ変化(TC)を受けたスイッチは «flush» を消し、802.1D のように root へ TCN を上げる必要はない。"
            "対向が 802.1D しか話せない場合、そのポートだけが «compat» に落ちる。"
        ),
        "slots": {
            "conv": {"a": "数秒以内(サブ秒〜)", "d": ["30〜50 秒", "max age の 3 倍", "forward delay × 2"], "why": "proposal/agreement と alternate の即時切替で待ち時間を消した"},
            "altn": {"a": "alternate port", "d": ["backup port", "edge port", "trunk port"], "grp": "role", "why": "root port が落ちたら即 root port になる(802.1D の blocking に相当)"},
            "back": {"a": "backup port", "d": ["alternate port", "designated port", "edge port"], "grp": "role", "why": "同じセグメントに自分の designated が別にある(ハブ経由など)"},
            "disc": {"a": "discarding", "d": ["learning", "forwarding", "listening"], "why": "discarding / learning / forwarding の 3 状態"},
            "src": {"a": "すべてのスイッチ(自分の情報で)", "d": ["root bridge だけ", "designated port を持つスイッチだけ"], "grp": "bpdu", "why": "keepalive 兼用。802.1D は root だけが起点(対比)"},
            "miss": {"a": "3", "d": ["2", "10", "20"], "grp": "bpdu", "why": "hello 2 秒 × 3 = 6 秒で隣接失効"},
            "pa": {"a": "proposal/agreement(sync)", "d": ["TCN の交換", "hello の短縮", "BPDU guard"], "why": "上流が proposal・下流が自分の非 edge ポートを discarding にしてから agreement"},
            "p2p": {"a": "point-to-point", "d": ["shared", "edge", "trunk"], "why": "全二重= 相手は 1 台と判断して即時遷移を許す"},
            "edge": {"a": "edge port(PortFast)", "d": ["shared port", "backup port", "trunk port"], "why": "BPDU を受けたら edge を外れて通常ポートに戻る"},
            "flush": {"a": "edge 以外のポートで学習した MAC", "d": ["すべてのポートで学習した MAC", "TC を受けたポートで学習した MAC だけ", "ARP キャッシュ"], "why": "TC while の間、非 edge ポートの MAC を即フラッシュ"},
            "compat": {"a": "802.1D(旧 STP)モード", "d": ["MST モード", "discarding 固定", "err-disabled"], "why": "ポート単位で互換動作。そのポートだけ収束が遅くなる"},
        },
    },
    # ------------------------------------------------------------------ PVST+ / Rapid-PVST+ / MST
    {
        "kind": "t_modes",
        "title": "PVST+ / Rapid PVST+ / MST(802.1s)の使い分けとリージョン",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            "spanning-tree mode «mode_mst»\n"
            "!\n"
            "spanning-tree mst configuration\n"
            " name {rname}\n"
            " revision {rev}\n"
            " instance 1 vlan 10,20\n"
            " instance 2 vlan 30,40\n"
            "!\n"
            "spanning-tree mst 1 priority 24576\n"
            "spanning-tree mst 2 priority 28672\n"
        ),
        "text": (
            "Cisco スイッチの既定の STP モードは «pvst» で、VLAN ごとに独立した 802.1D の木を作る。"
            "`spanning-tree mode rapid-pvst` にすると VLAN ごとの木のまま RSTP になる。"
            "VLAN が多いと木の数だけ BPDU と計算が増えるので、複数の VLAN を 1 つのインスタンスにまとめるのが «mst»(802.1s)である。"
            "上の設定では VLAN 10 と 20 の木が 1 本、30 と 40 の木が 1 本になり、それぞれ root を変えて負荷分散している。"
            "どのインスタンスにも書かれていない VLAN(例: VLAN 50)は «ist» に属する。"
            "同じリージョンと見なされるには «region» の 3 つが完全に一致する必要があり、1 つでも違うスイッチは別リージョン扱いになって、その間のポートは «boundary» になる。"
            "リージョン間や 802.1D/PVST+ との接続には «cist» が 1 本だけ張られ、外から見ると各リージョンは 1 台の巨大なスイッチに見える。"
            "設定の確認は `show spanning-tree mst configuration` で、変更は «commit» まで反映されない。"
        ),
        "slots": {
            "mode_mst": {"a": "mst", "d": ["rapid-pvst", "pvst", "mstp"], "why": "MST を使うにはモードを mst にする"},
            "pvst": {"a": "PVST+(per-VLAN 802.1D)", "d": ["Rapid PVST+", "MST", "802.1D 単一インスタンス"], "grp": "mode", "why": "`spanning-tree mode pvst` が既定"},
            "mst": {"a": "MST(Multiple Spanning Tree)", "d": ["PVST+", "Rapid PVST+", "VTP"], "grp": "mode", "why": "インスタンスごとに 1 本の木・VLAN を束ねる"},
            "ist": {"a": "IST(instance 0)", "d": ["instance 1", "CIST の外", "どの木にも属さない(転送されない)"], "why": "未割当 VLAN は全部 instance 0"},
            "region": {"a": "リージョン名・revision 番号・VLAN とインスタンスの対応表", "d": ["リージョン名・VTP ドメイン名・VLAN 一覧", "ホスト名・revision 番号・priority", "リージョン名だけ"], "why": "3 つのダイジェストが BPDU に載って比較される"},
            "boundary": {"a": "boundary port(境界ポート)", "d": ["edge port", "backup port", "root port"], "why": "境界では CIST の BPDU だけを交換する"},
            "cist": {"a": "CIST(Common and Internal Spanning Tree)", "d": ["IST(instance 0)", "PVST+ の木", "VLAN 1 の木"], "why": "リージョン間を 1 本の木でつなぐ。リージョン内では IST がその一部"},
            "commit": {"a": "`exit` でサブモードを抜ける", "d": ["`write memory`", "`spanning-tree mst apply`", "`reload`"], "why": "mst configuration は抜けた時点で一括反映(`show pending` で下見)"},
        },
        "vars": {"rname": _RNAME, "rev": _REV},
        "keep": ["mode_mst"],          # `show spanning-tree mst configuration` が本文にあり、空欄にすると答えが露出する
    },
    # ------------------------------------------------------------------ チューニング
    {
        "kind": "t_tuning",
        "title": "root の配置とパス選択のチューニング(priority・cost・port-priority)",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": (
            "root の位置は運任せにせず priority で決める。`spanning-tree vlan 10 root primary` は priority を «prim» にする(現 root がそれより低ければ、現 root より priority を 1 段階下げた値)。"
            "`root secondary` は «sec» に固定される。priority を直接書く場合は «step» の倍数しか受け付けない(既定 32768)。"
            "ポートのコストは帯域から決まり、short 方式では 100 Mbps= «c100»・1 Gbps= «c1g»・10 Gbps= 2 である。long 方式(`spanning-tree pathcost method long`)では 1 Gbps= «l1g» になる。"
            "root への経路を変えたいとき、自分のどのポートを root port にするかは «cost_cmd» で変える。"
            "一方、対向スイッチのどのポートを root port にするかを自分側で決めるには «pp_cmd» を使う(既定 128・«pp_step» 刻み・小さいほど優先。対向から見た送信元 port ID として効く)。"
            "hello・forward delay・max age を変えるときは «timer_where» で設定する(BPDU に載って全体へ配られるため)。"
        ),
        "slots": {
            "prim": {"a": "24576", "d": ["20480", "4096", "32768"], "grp": "prio", "why": "root primary= 24576(現 root が 24576 未満、または同値で MAC 負けなら現 root − 4096・1 未満が必要なら失敗)"},
            "sec": {"a": "28672", "d": ["32768", "20480", "24576"], "grp": "prio", "why": "root secondary= 28672 固定"},
            "step": {"a": "4096", "d": ["1024", "256", "4095"], "grp": "prio", "why": "下位 12 bit が extended system ID なので 4096 刻み"},
            "c100": {"a": "19", "d": ["100", "10", "4"], "grp": "cost", "why": "short: 10M=100 / 100M=19 / 1G=4 / 10G=2"},
            "c1g": {"a": "4", "d": ["19", "1", "2"], "grp": "cost", "why": "short: 1G=4"},
            "l1g": {"a": "20000", "d": ["2000", "200000", "4"], "grp": "cost", "why": "long(802.1t): 1G=20000 / 10G=2000"},
            "cost_cmd": {"a": "`spanning-tree cost <値>`(インタフェース)", "d": ["`spanning-tree vlan 10 priority <値>`", "`bandwidth <値>`", "`spanning-tree port-priority <値>`(インタフェース)"], "grp": "cmd", "why": "cost は自分の root path cost に効く= 自分の root port 選択"},
            "pp_cmd": {"a": "`spanning-tree port-priority <値>`(インタフェース)", "d": ["`spanning-tree cost <値>`(インタフェース)", "`spanning-tree vlan 10 priority <値>`", "`spanning-tree vlan 10 root primary`"], "grp": "cmd", "why": "port priority は BPDU の送信元 port ID として**対向**の選択に効く"},
            "pp_step": {"a": "16", "d": ["8", "32", "64"], "why": "既定 128・16 刻み(0〜240)"},
            "timer_where": {"a": "root bridge(root で設定した値が配られる)", "d": ["すべてのスイッチで同じ値を", "タイマを変えたい非 root スイッチで", "VTP サーバで"], "why": "非 root で書いても使われない(root が配る値に従う)"},
        },
    },
    # ------------------------------------------------------------------ 保護機構
    {
        "kind": "t_guard",
        "title": "保護機構: PortFast・BPDU guard/filter・root guard・loop guard・UDLD・errdisable",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": (
            "端末が繋がるアクセスポートに «pf» を付けると listening/learning を飛ばして即 forwarding になる(グローバルに `spanning-tree portfast default` を書くとアクセスポート全部に効く)。"
            "そのポートにスイッチが繋がれて BPDU が届いた時に、ポートを err-disabled にして守るのが «bg» である(グローバル既定は `spanning-tree portfast bpduguard default`)。"
            "一方 «bf» は BPDU を送受信しなくする機能で、グローバル既定ではエッジ扱いのポートに掛かり、BPDU を受信するとそのポートのエッジ扱いが外れて通常の STP に戻る。インタフェースで明示すると BPDU を完全に無視するのでループの危険がある。"
            "下流に置いたスイッチが root を奪うのを防ぐには、designated 側のポートに «rg» を掛ける。superior BPDU を受けるとそのポートは «rg_state» になり、BPDU が止めば自動で戻る。"
            "逆に、片方向リンクで BPDU が届かなくなった blocking ポートが誤って forwarding に進むのを防ぐのが «lg» で、root/alternate 側のポートに掛け、BPDU 途絶でポートを loop-inconsistent にする。"
            "同じ片方向リンク対策でも «udld» は L2 のエコーで隣接の生死を確かめ、aggressive モードでは失敗時にポートを err-disabled にする。"
            "err-disabled からの自動復帰は «errdis» で有効にし、待ち時間の既定は «errint» 秒である。"
        ),
        "slots": {
            "pf": {"a": "PortFast", "d": ["BPDU filter", "UplinkFast", "trunk"], "why": "端末向け。スイッチに繋ぐと一時ループの元"},
            "bg": {"a": "BPDU guard", "d": ["BPDU filter", "root guard", "loop guard"], "grp": "guard", "why": "受信した瞬間に err-disabled(遮断)"},
            "bf": {"a": "BPDU filter", "d": ["BPDU guard", "root guard", "UDLD"], "grp": "guard", "why": "無視する(遮断しない)。グローバル既定形だけが安全側"},
            "rg": {"a": "root guard", "d": ["loop guard", "BPDU guard", "BPDU filter"], "grp": "guard", "why": "designated 側に掛ける(root port には掛けない)"},
            "rg_state": {"a": "root-inconsistent(blocking 相当)", "d": ["loop-inconsistent", "err-disabled", "forwarding のまま"], "why": "superior BPDU が止むと自動復帰"},
            "lg": {"a": "loop guard", "d": ["root guard", "UDLD", "BPDU guard"], "grp": "guard", "why": "root/alternate 側に掛ける。root guard と同一ポートには併用不可"},
            "udld": {"a": "UDLD", "d": ["loop guard", "CDP", "LACP"], "why": "normal= 通知のみ / aggressive= err-disabled"},
            "errdis": {"a": "`errdisable recovery cause bpduguard`(原因ごとに指定)", "d": ["`spanning-tree portfast bpduguard default`", "`shutdown` → `no shutdown` を EEM で", "`errdisable detect cause all`"], "why": "cause を指定しないと自動復帰しない"},
            "errint": {"a": "300", "d": ["30", "60", "600"], "why": "`errdisable recovery interval` の既定 300 秒"},
        },
    },
    # ------------------------------------------------------------------ 読解(世界: root port が入れ替わる)
    {
        "kind": "t_read",
        "title": "show spanning-tree vlan の読解: Root ID・Bridge ID・ポート役割",
        "diagram": None,
        "n_blanks": 5,
        "worlds": ["g1", "g2"],
        "world_desc": {"g1": "Gi0/1 が cost 4・Gi0/2 が cost 19(Gi0/1 が root port)",
                       "g2": "Gi0/2 が cost 4・Gi0/1 が cost 19(Gi0/2 が root port)"},
        "exhibit": {
            "g1": (
                "SW2# show spanning-tree vlan 10\n\n"
                "VLAN0010\n"
                "  Spanning tree enabled protocol rstp\n"
                "  Root ID    Priority    24586\n"
                "             Address     {rootmac}\n"
                "             Cost        4\n"
                "             Port        1 (GigabitEthernet0/1)\n"
                "             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec\n\n"
                "  Bridge ID  Priority    32778  (priority 32768 sys-id-ext 10)\n"
                "             Address     {mymac}\n"
                "             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec\n"
                "             Aging Time  300 sec\n\n"
                "Interface           Role Sts Cost      Prio.Nbr Type\n"
                "------------------- ---- --- --------- -------- --------------------------------\n"
                "Gi0/1               Root FWD 4         128.1    P2p\n"
                "Gi0/2               Altn BLK 19        128.2    P2p\n"
                "Gi0/3               Desg FWD 4         128.3    P2p Edge\n"
            ),
            "g2": (
                "SW2# show spanning-tree vlan 10\n\n"
                "VLAN0010\n"
                "  Spanning tree enabled protocol rstp\n"
                "  Root ID    Priority    24586\n"
                "             Address     {rootmac}\n"
                "             Cost        4\n"
                "             Port        2 (GigabitEthernet0/2)\n"
                "             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec\n\n"
                "  Bridge ID  Priority    32778  (priority 32768 sys-id-ext 10)\n"
                "             Address     {mymac}\n"
                "             Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec\n"
                "             Aging Time  300 sec\n\n"
                "Interface           Role Sts Cost      Prio.Nbr Type\n"
                "------------------- ---- --- --------- -------- --------------------------------\n"
                "Gi0/1               Altn BLK 19        128.1    P2p\n"
                "Gi0/2               Root FWD 4         128.2    P2p\n"
                "Gi0/3               Desg FWD 4         128.3    P2p Edge\n"
            ),
        },
        "text": (
            "この出力に「This bridge is the root」の行が無いので、SW2 は «notroot» である。"
            "Root ID の priority 24586 は «rprio» を意味し、Bridge ID の 32778 は既定の 32768 に «sysid» を足した表示である。"
            "SW2 の root port は «rp» で、Gi0/1 と Gi0/2 の両方が root に届くが、«why» ためにそちらが選ばれた。"
            "選ばれなかった方が Altn BLK なのは、«altn_mean» だからである。"
            "Gi0/3 の Type 欄の Edge は «edge» を、P2p は «p2p» を表す。"
        ),
        "slots": {
            "notroot": {"a": "root ではない(root の情報を Root ID 欄に持つだけ)", "d": ["root である", "VLAN 10 で STP が無効", "隣接スイッチの情報が無い"], "why": "root なら Root ID の下に This bridge is the root が出る"},
            "rprio": {"a": "root の priority 設定 24576 + VLAN 10(root primary の既定値)", "d": ["root の priority 設定 24586 そのまま", "32768 − 8192", "MAC アドレスの下位 16 bit"], "why": "表示= 設定値 + extended system ID(VLAN 番号)"},
            "sysid": {"a": "VLAN 番号 10(extended system ID)", "d": ["ポート番号 10", "インスタンス番号 10", "スイッチ台数 10"], "why": "sys-id-ext 10 の表示がそれ"},
            "rp": {"a": {"g1": "GigabitEthernet0/1", "g2": "GigabitEthernet0/2"}, "d": ["GigabitEthernet0/3"], "why": "Role= Root の行。Root ID の Port 欄にも同じポートが出る"},
            "why": {"a": "root path cost が小さい(4 と 19 の比較)", "d": ["ポート番号が小さい", "先に up した", "Prio.Nbr の値が小さい"],
                    "why": "root port 選択の第 1 基準は root path cost(本文で port 名を明かさないのは、③を出力から読ませるため)"},
            "altn_mean": {"a": "root への別経路を持つが cost で負けた予備(discarding)", "d": ["別セグメントの designated が負けた予備(backup)", "ケーブル障害で down している", "BPDU filter で止められている"], "why": "Altn= alternate。root port が落ちれば即 forwarding"},
            "edge": {"a": "PortFast 相当の端末向けポート(TC に数えない)", "d": ["トランクポート", "BPDU guard が有効", "root guard が有効"], "why": "Type 欄の Edge= edge port"},
            "p2p": {"a": "全二重リンク(proposal/agreement で高速収束)", "d": ["半二重の共有リンク(Shr)", "2 台以上と接続", "トランクの点対点"], "why": "link type point-to-point。半二重なら Shr"},
        },
        "vars": {"rootmac": _ROOTMAC, "mymac": _MYMAC},
    },
]
