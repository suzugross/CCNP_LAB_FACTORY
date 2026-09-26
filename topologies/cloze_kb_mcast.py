#!/usr/bin/env python3
"""cloze_kb_mcast.py — 解説穴埋め形(shape=cloze) の知識ベース: IP マルチキャスト(U-F1/U-F2・BL-217)

書式は cloze_kb_mpls.py / cloze_kb_stp.py と同じ(PASSAGES / slots / vars / worlds / n_blanks / exhibit)。kind 接頭辞 `g_`(genre= mcast)。
範囲= ENCOR 3.3.d(describe: RPF・PIM SM・IGMP v2/v3・SSM・bidir・MSDP)/ CCIE 1.6(IGMP snooping/querier/filter・MLD・RPF・PIM SM・
static RP/BSR/Auto-RP・mapping・SSM・boundary・anycast RP(MSDP)・multipath)。単元の知識項目表= curriculum/U-F-mcast.md(全項目を被覆)。
セクション= 基礎(g_basics)/ IGMP(g_igmp)/ L2(g_l2)/ PIM-SM(g_pim)/ RP(g_rp)/ SSM・bidir(g_ssm)/ RPF(g_rpf)/ 読解(g_read・世界機構)。

裏どり(CLAUDE.md「作問の裏どり」): 照合表 curriculum/U-F-mcast.sources.md(Cisco 公式・解説サイト・RFC)＋実機 poc/mcast/README.md
(iol-xe / ioll2-xe 17.15.1)。**文書で割れて実測でも決められなかったものは載せない**(J/P holdtime の 3.5 倍・PIM ネイバー条件付きの RPF・
MLD のメッセージ番号など)。実測で決めた値: IGMP querier timeout 120 秒・PIM neighbor holdtime 105 秒・SSM と bidir は既定無効・
動的 RP マッピングは static(override なし)より優先で範囲の広狭は効かない・Auto-RP は listener 無しだと sparse-mode の先に届かない・
C-RP priority は Cisco 既定 0 で小さい方が勝つ・ioll2 には IGMP filter が無い(filter の記述は Cisco 文書に基づく)。
読解 passage の exhibit は実測の `show ip mroute` を写した(世界で SPT 切り替えの有無が変わる)。
"""

_GRP = ["239.1.1.1", "239.10.20.30", "239.0.100.5"]
_SRC = ["10.0.12.1", "172.16.1.10", "192.168.50.20"]

PASSAGES = [
    # ------------------------------------------------------------------ 基礎
    {
        "kind": "g_basics",
        "title": "マルチキャストの基礎: アドレス・MAC への写像・配信木",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": (
            "マルチキャストでは、送信元は «send_once» だけで、受信を希望するホストの集まり(グループ)に届く。"
            "IPv4 のマルチキャスト アドレスは «range» で、このうち 224.0.0.0/24 は «linklocal» として扱われ、ルータはこの範囲を転送しない。"
            "232.0.0.0/8 は «ssm_range» に、239.0.0.0/8 は組織内で使う管理スコープに割り当てられている。"
            "L2 では、IP アドレスの «low23» を 01:00:5E に続けて MAC アドレスを作るため、«overlap» 個の IP マルチキャスト アドレスが同じ MAC アドレスを共有する。"
            "ルータ間で作る配信木には、送信元を根とする «spt»(表記は (S,G))と、RP を根とする «rpt»(表記は (*,G))がある。"
            "ホストとルータの間でグループへの参加を伝えるのは IGMP で、ルータ間で木を作るのは PIM である。"
        ),
        "slots": {
            "send_once": {"a": "パケットを 1 回送る", "d": ["受信者の数だけ複製して送る", "ブロードキャストで送る", "受信者ごとに TCP で送る"], "why": "複製は木の分岐点のルータが行う"},
            "range": {"a": "224.0.0.0/4", "d": ["240.0.0.0/4", "192.0.0.0/4", "224.0.0.0/8"], "grp": "addr", "why": "クラス D= 224.0.0.0〜239.255.255.255"},
            "linklocal": {"a": "リンク ローカル(TTL 1)", "d": ["SSM 用", "組織内の管理スコープ", "Auto-RP 専用"], "grp": "scope", "why": "224.0.0.1(全ホスト)・224.0.0.2(全ルータ)・224.0.0.13(全 PIM ルータ)など"},
            "ssm_range": {"a": "SSM(Source Specific Multicast)", "d": ["リンク ローカル", "組織内の管理スコープ", "Auto-RP 専用"], "grp": "scope", "why": "SSM の既定の範囲。IOS では `ip pim ssm default` で有効にする"},
            "low23": {"a": "下位 23 ビット", "d": ["下位 24 ビット", "上位 23 ビット", "下位 16 ビット"], "why": "IP 側の 28 ビットのうち上位 5 ビットは写らない"},
            "overlap": {"a": "32", "d": ["16", "64", "128"], "why": "写らない 5 ビット= 2^5= 32"},
            "spt": {"a": "送信元木(SPT)", "d": ["共有木(RPT)", "スパニング ツリー", "最小全域木"], "grp": "tree", "why": "(S,G)= 送信元ごと・遅延が小さい"},
            "rpt": {"a": "共有木(RPT)", "d": ["送信元木(SPT)", "スパニング ツリー", "最小全域木"], "grp": "tree", "why": "(*,G)= 全送信元で共有・根は RP"},
        },
    },
    # ------------------------------------------------------------------ IGMP
    {
        "kind": "g_igmp",
        "title": "IGMP: v2 の参加と離脱・querier・v3",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": (
            "IGMPv2 のホストは、グループに参加するとき Membership Report を送り、離脱するときは «leave_dst» 宛てに Leave Group を送る。"
            "同じ LAN にルータが複数あると、Query を送る querier は «querier_rule» のルータに決まる(PIM の DR の決め方とは逆)。"
            "Cisco IOS の既定では General Query を «qint» 秒ごとに送り、querier からの Query が 120 秒途絶えると他のルータが querier を引き継ぐ。"
            "Leave を受けた querier は Group-Specific Query を 1 秒間隔で «lmqc» 回送り、応答が無ければそのグループを消す。"
            "IGMPv3 では «v3_feature» ができ、Report の宛先は «v3_dst» である。SSM を使うにはこの IGMPv3 が必要になる。"
            "ルータのインターフェイスで `ip igmp join-group` を設定すると、ルータ自身がグループに参加し、グループ宛ての ping に応答する。"
        ),
        "slots": {
            "leave_dst": {"a": "224.0.0.2(全ルータ)", "d": ["224.0.0.1(全ホスト)", "グループ アドレス", "224.0.0.13(全 PIM ルータ)"], "grp": "dst", "why": "Leave は全ルータ宛て。v2 の Report はグループ宛て"},
            "querier_rule": {"a": "IP アドレスが最小", "d": ["IP アドレスが最大", "DR priority が最大", "ルータ ID が最大"], "grp": "elect", "why": "実測: 受信 LAN で querier= .4(最小)・DR= .8(最大)が別々に決まった"},
            "qint": {"a": "60", "d": ["125", "30", "10"], "grp": "num", "why": "IOS の既定 60 秒(RFC の既定 125 秒とは違う)。実測でも 60"},
            "lmqc": {"a": "2", "d": ["1", "3", "5"], "grp": "num", "why": "last member query count 2・interval 1000 ms(実測: 離脱から約 2〜3 秒で消えた)"},
            "v3_feature": {"a": "送信元を指定した参加(INCLUDE / EXCLUDE)", "d": ["RP の指定", "Leave の省略", "TTL の指定"], "why": "(S,G) 単位で受けたい送信元を選べる"},
            "v3_dst": {"a": "224.0.0.22", "d": ["224.0.0.2", "224.0.0.1", "グループ アドレス"], "grp": "dst", "why": "IGMPv3 対応ルータ全体宛て"},
        },
    },
    # ------------------------------------------------------------------ L2
    {
        "kind": "g_l2",
        "title": "L2 のマルチキャスト: IGMP snooping・querier・filter・MLD",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": None,
        "text": (
            "スイッチは既定ではマルチキャスト フレームを VLAN 内に «flood» が、IGMP snooping を使うと IGMP のメッセージを覗いて «snoop_to» にだけ転送する(Catalyst では既定で有効)。"
            "ルータが接続されたポートは «mrouter» として学習され、そこにはグループに関係なく転送される。"
            "ルータのいない VLAN では Query を送る機器が無いため、スイッチの «sq» を有効にして Query を代行させる。"
            "特定のポートで参加できるグループを制限するには、`ip igmp profile` で範囲を定義し、インターフェイスに «filter_cmd» を適用する。"
            "IPv6 では IGMP の代わりに MLD を使い、MLDv1 は IGMPv2 に、MLDv2 は IGMPv3 に相当する。MLD のメッセージは «mld_proto» の一部として送られる。"
        ),
        "slots": {
            "flood": {"a": "フラッディングする", "d": ["破棄する", "ルータ ポートだけに送る", "最初のポートだけに送る"], "why": "宛先 MAC がマルチキャストなので MAC テーブルに載らない"},
            "snoop_to": {"a": "受信者のいるポート", "d": ["すべてのポート", "トランク ポートだけ", "ルートポートだけ"], "why": "実測: `show ip igmp snooping groups` に参加したポートだけが載った"},
            "mrouter": {"a": "mrouter ポート", "d": ["エッジ ポート", "ルート ポート", "指定ポート"], "why": "実測: PIM ルータの接続ポートが dynamic で学習された"},
            "sq": {"a": "IGMP snooping querier", "d": ["IGMP filter", "BPDU ガード", "DHCP snooping"], "why": "`ip igmp snooping querier`"},
            "filter_cmd": {"a": "`ip igmp filter`", "d": ["`ip igmp access-group`", "`ip multicast boundary`", "`ip igmp static-group`"], "why": "profile を参照してポートの参加を制限する(Cisco 文書。ioll2 には無い)"},
            "mld_proto": {"a": "ICMPv6", "d": ["UDP", "TCP", "IPv6 の拡張ヘッダだけ"], "why": "MLD は ICMPv6 のメッセージ"},
        },
    },
    # ------------------------------------------------------------------ PIM-SM
    {
        "kind": "g_pim",
        "title": "PIM-SM: DR・Join・Register・SPT への切り替え・Assert",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": (
            "PIM は独自の経路表を持たず、«pim_rib» を使って RPF を判断する(Protocol Independent の由来)。"
            "Hello は 224.0.0.13 宛てに 30 秒ごとに送られ、LAN 上の DR は «dr_rule» のルータに決まる。"
            "受信者のいる LAN の DR は、IGMP で参加を知ると RP へ向けて «star_join» を送り、共有木を作る。"
            "送信元の LAN の DR は、最初のパケットを «register» して RP へ届ける。RP が送信元へ (S,G) Join を送って木ができると、RP は Register-Stop を返す(受信者がいなくても返す)。"
            "Cisco IOS の既定では、受信側のルータは «spt_when» 送信元木へ切り替え、`ip pim spt-threshold infinity` を設定すると共有木に留まる。"
            "同じ LAN に 2 台のルータが同じフローを転送すると Assert が起き、AD → メトリック → «assert_tie» の順で勝った 1 台だけが転送を続ける。"
        ),
        "slots": {
            "pim_rib": {"a": "ユニキャストの経路表", "d": ["PIM 専用の経路表", "IGMP のグループ表", "MAC アドレス テーブル"], "why": "OSPF でも EIGRP でも static でもよい"},
            "dr_rule": {"a": "DR priority が最大、同じなら IP アドレスが最大", "d": ["IP アドレスが最小", "ルータ ID が最小", "先に起動した"], "grp": "elect", "why": "既定 priority 1。実測: `ip pim dr-priority 10` で IP の小さいルータが DR になった"},
            "star_join": {"a": "(*,G) Join", "d": ["(S,G) Join", "Register", "Graft"], "grp": "msg", "why": "RP を根とする共有木への参加"},
            "register": {"a": "ユニキャストでカプセル化(Register)", "d": ["マルチキャストのまま流して", "(*,G) Join に載せて", "MSDP の SA で"], "grp": "msg", "why": "実測: 送信元側 DR の (S,G) に F(Register)フラグ"},
            "spt_when": {"a": "最初のパケットを受けた時点で", "d": ["10 kbps を超えたときに", "RP の許可を得てから", "切り替えない(常に共有木)"], "why": "既定の SPT しきい値は 0(実測: 受信側 DR の (S,G) に JT)"},
            "assert_tie": {"a": "IP アドレスが最大", "d": ["IP アドレスが最小", "DR priority が最大", "ルータ ID が最小"], "grp": "elect", "why": "実測: AD とメトリックが同じで .8 が .4 に勝った(OIF フラグ A)"},
        },
    },
    # ------------------------------------------------------------------ RP
    {
        "kind": "g_rp",
        "title": "RP の決め方: static・BSR・Auto-RP・anycast RP(MSDP)",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": None,
        "text": (
            "static RP は `ip pim rp-address` で指定し、«static_where» に同じ設定が必要である。"
            "標準の方式は BSR で、候補 BSR から選ばれた BSR が候補 RP の一覧を hop-by-hop で配る。候補 RP の priority は «bsr_prio» が優先される(Cisco の既定値は 0)。"
            "Cisco 独自の Auto-RP では、候補 RP が 224.0.1.39 へ announce し、mapping agent が «ma_rule» の RP を選んで 224.0.1.40 で配る。"
            "インターフェイスが sparse-mode だけの場合、この 2 つのグループには RP が無いため、«listener» を設定しないと mapping agent の先へ情報が届かない。"
            "同じグループに static と動的(BSR / Auto-RP)の情報があると、«precedence»。"
            "anycast RP では複数の RP に同じアドレスを設定し、RP 同士は «msdp» で送信元の情報(SA)を交換する。"
            "管理スコープの境界では `ip multicast boundary` で該当するグループを止め、その範囲への IGMP の参加も受け付けない。"
        ),
        "slots": {
            "static_where": {"a": "すべての PIM ルータ", "d": ["RP だけ", "DR だけ", "送信元側のルータだけ"], "why": "RP の位置を各ルータが知っている必要がある"},
            "bsr_prio": {"a": "値が小さい方", "d": ["値が大きい方", "IP アドレスが小さい方", "先に届いた方"], "grp": "prio", "why": "実測: priority 10 の候補より 0 の候補が選ばれた。同値ならハッシュ"},
            "ma_rule": {"a": "IP アドレスが最大", "d": ["IP アドレスが最小", "priority が最小", "最初に announce した"], "grp": "prio", "why": "実測: 3.3.3.3 と 5.5.5.5 から 5.5.5.5 が選ばれた"},
            "listener": {"a": "`ip pim autorp listener`", "d": ["`ip pim bsr-candidate`", "`ip pim ssm default`", "`ip pim spt-threshold infinity`"], "why": "実測: 無しでは MA の先に discovery が届かず、設定後に届いた"},
            "precedence": {"a": "static に override を付けない限り動的の情報が使われる", "d": ["常に static が使われる", "グループの範囲が狭い方が使われる", "RP の IP アドレスが大きい方が使われる"],
                           "why": "実測: static を 239.1.1.0/24 に絞っても 224/4 の Auto-RP が使われた。override で static"},
            "msdp": {"a": "MSDP(TCP 639)", "d": ["BSR", "Auto-RP", "PIM Hello"], "why": "SA cache に (S,G) と発信元 RP が載る(実測)"},
        },
    },
    # ------------------------------------------------------------------ SSM / bidir
    {
        "kind": "g_ssm",
        "title": "SSM と bidir PIM",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": None,
        "text": (
            "SSM では受信者が送信元を指定して参加するので、«ssm_rp» になり、ルータには (S,G) だけが作られる。"
            "Cisco IOS で 232.0.0.0/8 を SSM として扱うには «ssm_cmd» が必要で(既定では無効)、受信側の LAN は IGMPv3 で動かす。"
            "SSM の範囲に IGMPv2 で(送信元を指定せずに)参加しても、その参加は «ssm_v2»。"
            "bidir PIM は共有木だけで双方向に配送し、«bidir_state»。多数の送信元と受信者が混在する用途に向く。"
            "(参考: dense mode は全体へ流してから不要な枝を Prune する方式で、現在の設計では使わない。)"
            "この方式を使うには `ip pim bidir-enable`(既定では無効)を設定し、RP を «bidir_kw» のように指定する。各セグメントでは DF が RP 方向への転送を受け持つ。"
        ),
        "slots": {
            "ssm_rp": {"a": "RP は不要", "d": ["RP が必須", "BSR が必須", "MSDP が必須"], "why": "実測: RP には状態が作られなかった"},
            "ssm_cmd": {"a": "`ip pim ssm default`", "d": ["`ip igmp version 3` だけ", "`ip pim bidir-enable`", "`ip pim autorp listener`"], "why": "実測: 外すと v3 の (S,G) 参加も (*,G) の ASM 扱いになった"},
            "ssm_v2": {"a": "受け付けられない", "d": ["(*,G) として扱われる", "RP 経由で転送される", "自動で IGMPv3 に変換される"], "why": "実測: IGMP のグループにも載らなかった(SSM mapping を使わない場合)"},
            "bidir_state": {"a": "(S,G) を作らない", "d": ["送信元ごとに (S,G) を作る", "RP を使わない", "IGMPv3 が必須"], "why": "実測: (*,G) のみ・flags B・`Bidir-Upstream` 行"},
            "bidir_kw": {"a": "`ip pim rp-address 3.3.3.3 20 bidir`", "d": ["`ip pim rp-address 3.3.3.3 20 override`", "`ip pim ssm range 20`", "`ip pim spt-threshold infinity group-list 20`"],
                         "why": "RP の指定に bidir キーワード(実測: ACL 名を BIDIR にするとキーワードと衝突して Ambiguous になる→ 番号 ACL で可)"},
        },
    },
    # ------------------------------------------------------------------ RPF
    {
        "kind": "g_rpf",
        "title": "RPF チェック",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": None,
        "text": (
            "ルータはマルチキャスト パケットを受けると、受信インターフェイスが «rpf_ref» へのユニキャスト経路の出口と一致するかを確かめる(RPF チェック)。"
            "一致しなければそのパケットは «rpf_fail»。共有木を流れるパケットでは、RPF の基準は «rpt_ref» になる。"
            "等コストの経路が複数あるとき、Cisco IOS は既定で «ecmp_rule» のネクスト ホップを RPF に使い、`ip multicast multipath` を設定するとフローごとのハッシュで分散する。"
            "ユニキャストの経路と PIM の経路を変えたいときは «mroute_cmd» で RPF を静的に指定でき、`show ip rpf` では RPF type が multicast (static) と表示される。"
        ),
        "slots": {
            "rpf_ref": {"a": "送信元", "d": ["宛先のグループ", "RP", "DR"], "grp": "ref", "why": "ループを防ぐため、送信元へ戻る方向から来たものだけを受け付ける"},
            "rpf_fail": {"a": "破棄される", "d": ["全インターフェイスへ転送される", "RP へ Register される", "受信インターフェイスへ返される"], "why": "`show ip mroute count` の RPF failed に数えられる(実測)"},
            "rpt_ref": {"a": "RP", "d": ["送信元", "DR", "querier"], "grp": "ref", "why": "(*,G) の Incoming interface は RP 方向"},
            "ecmp_rule": {"a": "IP アドレスが最大", "d": ["IP アドレスが最小", "先に学習した", "インターフェイス番号が小さい"], "why": "実測: 10.0.34.3 と 10.0.45.5 から 10.0.45.5 を選び、multipath で変わった"},
            "mroute_cmd": {"a": "`ip mroute`", "d": ["`ip route`", "`ip pim rp-address`", "`ip multicast boundary`"], "why": "static mroute(実測で RPF type multicast (static))"},
        },
    },
    # ------------------------------------------------------------------ 読解
    {
        "kind": "g_read",
        "title": "show ip mroute の読解: (*,G) と (S,G)・フラグ・RPF",
        "diagram": None,
        "n_blanks": 5,
        "worlds": ["spt", "rpt"],
        "world_desc": {"spt": "既定(SPT へ切り替え済み= (S,G) に JT)", "rpt": "spt-threshold infinity(共有木のみ= (*,G) だけ)"},
        "exhibit": {
            "spt": (
                "RT08# show ip mroute {grp}\n"
                "(*, {grp}), 00:00:39/stopped, RP 3.3.3.3, flags: SJC\n"
                "  Incoming interface: Ethernet0/0, RPF nbr 10.0.34.3\n"
                "  Outgoing interface list:\n"
                "    Ethernet0/2, Forward/Sparse, 00:00:39/00:02:50, flags:\n\n"
                "({src}, {grp}), 00:00:24/00:02:35, flags: JT\n"
                "  Incoming interface: Ethernet0/1, RPF nbr 10.0.58.5\n"
                "  Outgoing interface list:\n"
                "    Ethernet0/2, Forward/Sparse, 00:00:24/00:02:35, flags:\n"
            ),
            "rpt": (
                "RT08# show ip mroute {grp}\n"
                "(*, {grp}), 00:00:36/00:02:53, RP 3.3.3.3, flags: SC\n"
                "  Incoming interface: Ethernet0/0, RPF nbr 10.0.34.3\n"
                "  Outgoing interface list:\n"
                "    Ethernet0/2, Forward/Sparse, 00:00:36/00:02:53, flags:\n"
            ),
        },
        "text": (
            "(*, G) のエントリは «star_mean» を表し、その Incoming interface と RPF nbr は «star_iif» を向いている。"
            "フラグの S は sparse mode、C は «flag_c» を意味する。"
            "Outgoing interface list の Ethernet0/2 は、グループのパケットを «oil_mean» インターフェイスである。"
            "このルータが送信元木に切り替えているかどうかは «spt_state» から読み取れる。"
        ),
        "slots": {
            "star_mean": {"a": "RP を根とする共有木", "d": ["送信元を根とする送信元木", "IGMP の参加表", "RPF 失敗の記録"], "grp": "tree", "why": "(*,G)= RPT。(S,G)= SPT"},
            "star_iif": {"a": "RP の方向", "d": ["送信元の方向", "受信者の方向", "DR の方向"], "grp": "dir", "why": "共有木の RPF は RP が基準"},
            "flag_c": {"a": "直接接続された受信者がいる", "d": ["RP である", "Register 中である", "Prune されている"], "why": "C= Connected(IGMP の参加がある)"},
            "oil_mean": {"a": "送り出す", "d": ["受け取る", "破棄する", "Register する"], "why": "OIL= 転送先"},
            "spt_state": {"a": {"spt": "(S,G) のエントリに J と T が付いていること(切り替え済み)", "rpt": "(S,G) のエントリが無いこと(共有木に留まっている)"},
                          "d": ["(*,G) の RP 欄", "Outgoing interface list の数", "(*,G) のフラグ S"],
                          "why": "既定では最初のパケットで SPT へ切り替える(J= Join SPT・T= SPT-bit)。spt-threshold infinity なら (S,G) を作らない(実測)"},
        },
        "vars": {"grp": _GRP, "src": _SRC},
    },
]
