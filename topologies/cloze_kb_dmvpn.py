#!/usr/bin/env python3
"""cloze_kb_dmvpn.py — 解説穴埋め形(shape=cloze) の知識ベース: DMVPN Phase 1/2/3 比較と IPsec(BL-203)

書式は cloze_kb_mpls.py と同じ(PASSAGES / slots / vars / worlds / n_blanks / exhibit_md)。kind 接頭辞 `d_`(genre= vpn)。
範囲= ENARSI 2.3 「Configure and verify DMVPN (single hub): GRE/mGRE, NHRP, IPsec, dynamic neighbor, spoke-to-spoke」。
IKE/ESP の基礎(フェーズ・モード・プロトコル番号)は DMVPN を守る IPsec の文脈で扱う。

事実の出所:
- poc/dmvpn-ipsec/README.md + problems/_drafts/DMVPN-IPSEC.design.md(IOSv 15.9・2026-07-09 実測):
  per-peer keyring= hub-spoke 正常・spoke 間 ping も通る(永久ハブ折返し)・show dmvpn に IX/DX / spoke を p2p GRE 化= 対向に `UNKNOWN <IP> IKE never IX` /
  tunnel key 不一致= IKEv2 READY のまま State NHRP 固着・`show ip nhrp nhs detail` に `Registration Request … expired` / NHRP 認証不一致= サイレント登録拒否 /
  tunnel protection 片側欠落= hub が平文 GRE を破棄 / network-id 不一致= 非故障(ローカル有意) / mode transport/tunnel 齟齬= Tunnel に合意して動く /
  ip mtu 1400 欠落= 外側 GRE が断片化して ping は通る(DF は外側に複製されない)。
- 2026-09-18 IOL(iol-xe 17.15.1)実測: State 列で層を割る IKE→NHRP→UP / hub 側の auth 不一致ログ `wrong authentication string` /
  `tunnel protection` 変更は Tunnel 自動 shutdown / `shared` は同一 source+同一 profile の全 Tunnel に必要(片方だけは拒否) /
  Phase3 shortcut 後は spoke `show dmvpn` に DT1/DT2・`show ip route next-hop-override` に `%`・詳細ビューの next-hop はハブのまま。
- problems/ENARSI-DMVPN-IPSEC-01(Phase3+IKEv2・実機 100/100)・DMVPN-POC-01(Phase2)・DMVPN-PHASE3-01・ENARSI-IPSEC-VTI-01(IKEv1)・
  ENARSI-GREIPSEC-MAP-01(crypto map)の正規構文。NHRP authentication は最大 8 文字(day0 で黙って蒸発)。
- 教材(非公開・範囲確認のみ): Phase 1= 全通信ハブ経由(スポーク p2p GRE)/Phase 2= スポーク間直接(スポークも mGRE)/Phase 3= ハブ集約可(redirect/shortcut)、
  OSPF は Phase1 p2mp・Phase2/3 broadcast(スポーク priority 0)、EIGRP は hub の no split-horizon(+Phase2 no next-hop-self)、
  IPsec は transport・静的 NAT は可・動的 NAT/PAT は不可。
- 定数: ESP= IP プロトコル 50・AH= 51・ISAKMP UDP 500・NAT-T UDP 4500・GRE ヘッダ 4 バイト(+key 4)・GRE Tunnel の既定 ip mtu 1476・
  NHRP holdtime 既定 7200 秒。
"""

_HNBMA = ["10.0.14.1", "203.0.113.1", "198.51.100.1"]
_SNBMA = ["10.0.24.1", "203.0.113.2", "198.51.100.2"]
_ONBMA = ["10.0.34.1", "203.0.113.3", "198.51.100.3"]
_AUTH = ["DMVPNKEY", "NHRPK3Y", "CCNP2026"]        # ★8 文字以内
_TKEY = ["100", "1", "65001"]
_NID = ["1", "100", "10"]
_AS = ["100", "1", "65100"]
_PROF = ["IPSEC-DMVPN", "IPSEC-PROF", "DMVPN-PROF"]
_WAN = ["GigabitEthernet0/0", "Ethernet0/0", "GigabitEthernet0/1"]
_PSK = ["Ss2026#Dmvpn", "Dmvpn-Psk-77", "Wan#Key2026"]

_SHOW_LEGEND = (
    "Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete\n"
    "        N - NATed, L - Local, X - No Socket\n"
    "        T1 - Route Installed, T2 - Nexthop-override\n"
    "        # Ent --> Number of NHRP entries with same NBMA peer\n"
    "        NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting\n"
)

PASSAGES = [
    # ------------------------------------------------------------------ Phase 比較表
    {
        "kind": "d_phases",
        "title": "DMVPN Phase 1 / 2 / 3 の比較",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": (
            '| 項目 | Phase 1 | Phase 2 | Phase 3 |\n'
            '|---|---|---|---|\n'
            '| スポークのトンネル | «p1_mode» | mGRE | mGRE |\n'
            '| スポーク間トラフィックの経路 | 常にハブ経由 | «p2_path» | «p3_path» |\n'
            '| スポークが持つ経路 | «p1_route» | «p2_route» | 集約や default でよい(next-hop はハブのまま) |\n'
            '| ハブの追加設定(EIGRP の場合) | なし | «p2_hub» | «p3_hub» |\n'
            '| スポークの追加設定 | なし | なし | «p3_spoke» |\n'
            '| OSPF ネットワークタイプの定石 | «p1_ospf» | broadcast(ハブが DR・スポークは priority 0) | broadcast(同左) |\n'
        ),
        "exhibit_md": True,
        "text": (
            "Phase の番号は «phase_def» で、ハブは 3 つのどれでも mGRE である。"
            "Phase 2 でハブが経路を集約できないのは、スポーク間直接通信のきっかけが «p2_trigger» だからである。"
            "Phase 3 では «p3_trigger» がきっかけになるので、スポークの経路はハブ向きのままでよく、ハブで集約しても直接通信が成立する。"
            "どの Phase でもハブの EIGRP には no ip split-horizon が要る(同じ Tunnel から学んだスポークの経路を他のスポークへ反射させるため)。"
        ),
        "slots": {
            "p1_mode": {"a": "p2p GRE(tunnel destination でハブを固定)", "d": ["mGRE(tunnel destination なし)", "IPsec VTI(tunnel mode ipsec ipv4)"], "why": "Phase 1 のスポークは点対点 GRE でよい"},
            "p2_path": {"a": "スポーク間の動的トンネルで直接(経路の next-hop が対向スポーク)", "d": ["常にハブ経由", "ハブ経由だが暗号化はスポーク間で直接"], "grp": "path", "why": "Phase 2= 経路制御で直接通信"},
            "p3_path": {"a": "スポーク間の動的トンネルで直接(経路はハブ向きのまま転送だけ切り替え)", "d": ["常にハブ経由", "ハブ経由だが暗号化はスポーク間で直接"], "grp": "path", "why": "Phase 3= NHRP redirect/shortcut で転送だけ直接"},
            "p1_route": {"a": "集約や default でよい(next-hop はハブ)", "d": ["対向 LAN ごとの具体的な経路が要る", "経路は不要(NHRP が全て解決する)"], "grp": "route", "why": "全部ハブ経由なのでハブ向きの経路だけでよい"},
            "p2_route": {"a": "対向 LAN ごとの具体的な経路が要る(集約不可・next-hop= 対向スポーク)", "d": ["集約や default でよい(next-hop はハブ)", "経路は不要(NHRP が全て解決する)"], "grp": "route", "why": "next-hop が対向スポークでないと直接通信が起きない"},
            "p2_hub": {"a": "no ip next-hop-self eigrp(+ no ip split-horizon eigrp)", "d": ["ip nhrp redirect(+ no ip split-horizon eigrp)", "ip summary-address eigrp", "ip nhrp shortcut"], "grp": "hub", "why": "Phase 2 はハブが next-hop を書き換えないことが核心"},
            "p3_hub": {"a": "ip nhrp redirect(+ no ip split-horizon eigrp)", "d": ["no ip next-hop-self eigrp(+ no ip split-horizon eigrp)", "ip summary-address eigrp", "ip nhrp shortcut"], "grp": "hub", "why": "Phase 3 はハブが Redirect を送る"},
            "p3_spoke": {"a": "ip nhrp shortcut", "d": ["ip nhrp redirect", "no ip next-hop-self eigrp", "tunnel destination <ハブ NBMA>"], "why": "Redirect を受けて解決・直接転送するのがスポーク側の shortcut"},
            "p1_ospf": {"a": "point-to-multipoint", "d": ["point-to-point(既定のまま)", "non-broadcast"], "why": "全通信がハブ経由なら p2mp が素直。既定の p2p は複数隣接を張れない"},
            "phase_def": {"a": "設定の組合せで決まる動作モード(ソフトウェアの版ではない)", "d": ["IOS のライセンスレベル", "NHRP プロトコルのバージョン"], "why": "redirect/shortcut や next-hop-self の有無で決まる"},
            "p2_trigger": {"a": "経路の next-hop が対向スポークのトンネル IP であること(その解決で NHRP が走る)", "d": ["ハブから送られる NHRP Redirect", "ハブが GRE キープアライブを返すこと"], "why": "だから集約すると next-hop がハブになり直接通信が消える"},
            "p3_trigger": {"a": "ハブが中継時に送る NHRP Redirect と、それを受けたスポークの解決(shortcut)", "d": ["経路の next-hop が対向スポークであること", "スポーク同士の IKE の事前交渉"], "why": "転送面だけがオンデマンドで切り替わる"},
        },
    },
    # ------------------------------------------------------------------ NHRP の役割と用語
    {
        "kind": "d_nhrp",
        "title": "NHRP の役割: 登録・解決・Redirect と主要パラメータ",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": None,
        "text": (
            "DMVPN のスポークは 2 つのアドレスを持つ。トンネルの内側のトンネル IP と、外側の «nbma» である。"
            "起動したスポークはハブ(«nhs_role»)に «reg» を送り、自分のトンネル IP と外側アドレスの対応を登録する。"
            "スポーク間通信では、送信元スポークが «res» で相手のトンネル IP に対応する外側アドレスを問い合わせ、"
            "その応答は解決先のスポークから直接返ってくる(これで両者の動的トンネルが張れる)。"
            "Phase 3 ではハブがスポーク宛のパケットを中継したときに «redirect_msg» を送信元へ送り、スポークの解決を促す。"
            "登録や解決の応答には «holdtime» が載り、相手側キャッシュの保持時間になる(既定 «hold_def» 秒・登録はその 1/3 ごとに再送)。"
            "`ip nhrp network-id` は «netid» なので、hub と spoke で値が違っても登録も通信も成立する(実測)。"
            "`ip nhrp authentication` の文字列の長さは «auth_len» で、値が一致しないと登録要求はエラーも返さずに黙殺される(実測)。"
            "`tunnel key` は GRE のキーで、不一致だと GRE 自体を受け入れないため NHRP 登録に進めない。"
        ),
        "slots": {
            "nbma": {"a": "NBMA アドレス(tunnel source の物理/WAN アドレス)", "d": ["ループバックアドレス", "NHS アドレス"], "why": "Non-Broadcast Multi-Access= トンネルを運ぶ外側の網のアドレス"},
            "nhs_role": {"a": "Next Hop Server", "d": ["Next Hop Client", "Route Reflector"], "why": "ハブ= NHS・スポーク= NHC"},
            "reg": {"a": "Registration Request", "d": ["Resolution Request", "Purge Request"], "grp": "msg", "why": "登録はスポーク→ハブのユニキャスト"},
            "res": {"a": "Resolution Request", "d": ["Registration Request", "Purge Request"], "grp": "msg", "why": "解決要求はハブ経由で相手スポークへ届き、応答は直接返る"},
            "redirect_msg": {"a": "NHRP Redirect(Traffic Indication)", "d": ["ICMP Redirect", "Purge Request"], "grp": "msg", "why": "ip nhrp redirect を持つハブが送る"},
            "holdtime": {"a": "ip nhrp holdtime の値", "d": ["ip nhrp registration timeout の値", "tunnel key の値"], "why": "自分の情報を相手にどれだけ保持させるか"},
            "hold_def": {"a": "7200", "d": ["3600", "180", "600"], "why": "既定 2 時間。登録は 1/3(2400 秒)ごと"},
            "netid": {"a": "ローカル有意(ワイヤに乗らない)", "d": ["両端で一致が必要(不一致は登録失敗)", "IPsec の識別子として送られる"], "why": "同じルータ内で NHRP ドメインを区別するだけ。故障の原因にはならない"},
            "auth_len": {"a": "最大 8 文字", "d": ["最大 16 文字", "最大 32 文字"], "why": "9 文字以上は day0 で黙って捨てられる(実測)"},
        },
    },
    # ------------------------------------------------------------------ スポーク設定
    {
        "kind": "d_spoke_cfg",
        "title": "スポーク(Phase 3・IPsec あり)の Tunnel 設定例",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            "interface Tunnel0\n"
            " ip address {stip} 255.255.255.0\n"
            " ip mtu «mtu»\n"
            " ip tcp adjust-mss «mss»\n"
            " ip nhrp authentication {auth}\n"
            " ip nhrp network-id {nid}\n"
            " ip nhrp nhs {htip} nbma {hnbma} «mcast»\n"
            " «shortcut»\n"
            " tunnel source {wan}\n"
            " tunnel mode gre «mp»\n"
            " tunnel key {tkey}\n"
            " tunnel protection ipsec profile {prof}\n"
            "!\n"
            "! ハブ: トンネル IP {htip} / NBMA {hnbma}   スポークの WAN IF= {wan}\n"
        ),
        "text": (
            "NHS の行は従来の map・map «mcast»・nhs の 3 行を 1 行にまとめた現代構文で、末尾の «mcast» は "
            "«mcast_role» を意味する。{hnbma} は «hnbma_role» である。"
            "tunnel destination を書かないのは «no_dest» からで、そのために tunnel mode を gre «mp» にする。"
            "«shortcut» はハブからの Redirect を受けて解決・直接転送するための Phase 3 のスポーク設定である。"
            "MSS は IP ヘッダと TCP ヘッダの分だけ ip mtu より «mss_diff» バイト小さくする。"
            "tunnel protection を付けると «prot_effect»。"
        ),
        "slots": {
            "mtu": {"a": "1400", "d": ["1500", "1476"], "why": "GRE+IPsec の余地を見た定番値"},
            "mss": {"a": "1360", "d": ["1436", "1460"], "why": "1400 − 40"},
            "mcast": {"a": "multicast", "d": ["broadcast", "dynamic", "priority"], "why": "ハブの NBMA をマルチキャスト(Hello)の宛先に加える"},
            "shortcut": {"a": "ip nhrp shortcut", "d": ["ip nhrp redirect", "ip nhrp map multicast dynamic", "no ip next-hop-self eigrp {as}"], "why": "Phase 3 のスポーク側"},
            "mp": {"a": "multipoint", "d": ["ip", "ipv6"], "why": "tunnel mode gre multipoint= mGRE"},
            "mcast_role": {"a": "ルーティングプロトコルの Hello などマルチキャストをハブへ送るための対応", "d": ["ハブをマルチキャストのランデブーポイントにする指定", "スポークが DR になることの宣言"], "why": "map multicast <NBMA> と同じ意味"},
            "hnbma_role": {"a": "ハブの NBMA(WAN 物理)アドレス", "d": ["ハブのトンネル IP", "ハブのループバック"], "why": "登録要求を運ぶ外側の宛先"},
            "no_dest": {"a": "宛先(ハブや対向スポークの NBMA)を NHRP が解決する", "d": ["IPsec プロファイルが宛先を持つ", "tunnel key が宛先を識別する"], "why": "mGRE は宛先固定なし"},
            "mss_diff": {"a": "40", "d": ["20", "24", "60"], "why": "IP 20 + TCP 20"},
            "prot_effect": {"a": "GRE パケット全体が ESP で保護される(平文 GRE は相手に捨てられる)", "d": ["NHRP だけが暗号化される", "トンネル IP がハブに登録される"], "why": "片側だけ欠けるとハブが平文 GRE を破棄し登録も失敗(実測)"},
        },
        "vars": {"tnet": ["10.255.0", "172.31.255", "10.200.0"],
                 "htip": lambda v, w: f"{v['tnet']}.1", "stip": lambda v, w: f"{v['tnet']}.2",
                 "hnbma": _HNBMA, "auth": _AUTH, "nid": _NID, "tkey": _TKEY, "prof": _PROF, "wan": _WAN, "as": _AS},
    },
    # ------------------------------------------------------------------ ハブ設定(Phase 2 / 3 の世界)
    {
        "kind": "d_hub_cfg",
        "title": "ハブの Tunnel 設定と Phase の判定(EIGRP)",
        "diagram": None,
        "n_blanks": 5,
        "worlds": ["p2", "p3"],
        "world_desc": {"p2": "Phase 2(ハブが next-hop を書き換えない・スポークに shortcut なし)",
                       "p3": "Phase 3(ハブが redirect・スポークに shortcut)"},
        "exhibit": {
            "p2": (
                "! Hub\n"
                "interface Tunnel0\n"
                " ip address {htip} 255.255.255.0\n"
                " no ip redirects\n"
                " ip mtu 1400\n"
                " ip tcp adjust-mss 1360\n"
                " ip nhrp authentication {auth}\n"
                " «mcast_dyn»\n"
                " ip nhrp network-id {nid}\n"
                " «phase_line»\n"
                " «nosh»\n"
                " tunnel source {wan}\n"
                " tunnel mode gre multipoint\n"
                " tunnel key {tkey}\n"
                " tunnel protection ipsec profile {prof}\n"
                "!\n"
                "! Spoke(抜粋): ip nhrp nhs {htip} nbma {hnbma} multicast / tunnel mode gre multipoint\n"
                "!              (ip nhrp shortcut は設定されていない)\n"
            ),
            "p3": (
                "! Hub\n"
                "interface Tunnel0\n"
                " ip address {htip} 255.255.255.0\n"
                " no ip redirects\n"
                " ip mtu 1400\n"
                " ip tcp adjust-mss 1360\n"
                " ip nhrp authentication {auth}\n"
                " «mcast_dyn»\n"
                " ip nhrp network-id {nid}\n"
                " «phase_line»\n"
                " «nosh»\n"
                " tunnel source {wan}\n"
                " tunnel mode gre multipoint\n"
                " tunnel key {tkey}\n"
                " tunnel protection ipsec profile {prof}\n"
                "!\n"
                "! Spoke(抜粋): ip nhrp nhs {htip} nbma {hnbma} multicast / tunnel mode gre multipoint\n"
                "!              ip nhrp shortcut\n"
            ),
        },
        "text": (
            "この構成は Phase «which» である。«mcast_dyn» は «mcast_why» ための行で、これが無いとスポークはハブからの Hello を受け取れず隣接が片側だけになる。"
            "«nosh» は «nosh_why» ために要る(Phase に関係なく必須)。"
            "«phase_line» が Phase を決める行で、スポークが持つ対向スポークの LAN 経路の next-hop は «sp_nh» になる。"
            "この Phase でハブが対向スポークの経路を集約することは «sum»。"
            "tunnel key は全メンバで一致させ、`no ip redirects` は Tunnel 上で ICMP Redirect を出さないための定石である。"
        ),
        "slots": {
            "mcast_dyn": {"a": "ip nhrp map multicast dynamic", "d": ["ip nhrp map multicast {hnbma}", "ip nhrp nhs dynamic"], "why": "ハブは登録してきたスポークの NBMA をマルチキャスト宛先に自動追加"},
            "phase_line": {"a": {"p2": "no ip next-hop-self eigrp {as}", "p3": "ip nhrp redirect"},
                           "d": ["ip nhrp shortcut", "ip summary-address eigrp {as} 0.0.0.0 0.0.0.0"],
                           "why": {"p2": "スポークに shortcut が無いので Phase 2。ハブは next-hop を書き換えない", "p3": "スポークに shortcut があるので Phase 3。ハブは Redirect を送る"}},
            "nosh": {"a": "no ip split-horizon eigrp {as}", "d": ["no ip next-hop-self eigrp {as}", "ip split-horizon eigrp {as}"], "why": "同じ Tunnel から学んだ経路を同じ Tunnel へ広告するため"},
            "which": {"a": {"p2": "2", "p3": "3"}, "d": ["1"], "why": {"p2": "shortcut なし・next-hop-self 無効= Phase 2", "p3": "redirect+shortcut= Phase 3"}},
            "mcast_why": {"a": "登録してきたスポークの NBMA を Hello などマルチキャストの宛先に自動で加える", "d": ["スポークからのマルチキャスト登録を受け付ける", "ハブをマルチキャストの DR にする"], "why": "スポークごとの map multicast を書かずに済む"},
            "nosh_why": {"a": "同じ Tunnel から学んだスポークの経路を、他のスポークへ同じ Tunnel から広告する", "d": ["ハブが自分の LAN をスポークへ広告する", "スポーク間の直接トンネルを禁止する"], "why": "距離ベクタの split horizon をハブで解除"},
            "sp_nh": {"a": {"p2": "対向スポークのトンネル IP", "p3": "ハブのトンネル IP({htip})のまま"},
                      "d": ["対向スポークの NBMA アドレス"],
                      "why": {"p2": "Phase 2 の署名= next-hop が対向スポーク", "p3": "Phase 3 の署名= next-hop はハブ・転送だけ直接(show ip route next-hop-override に %)"}},
            "sum": {"a": {"p2": "できない(集約すると next-hop がハブになり直接通信が消える)", "p3": "できる(next-hop はもともとハブ・Redirect で直接通信が成立)"},
                    "d": ["どちらの Phase でもできない"],
                    "why": {"p2": "Phase 2 の制約", "p3": "Phase 3 の利点"}},
        },
        "vars": {"tnet": ["10.255.0", "172.31.255", "10.200.0"], "htip": lambda v, w: f"{v['tnet']}.1",
                 "hnbma": _HNBMA, "auth": _AUTH, "nid": _NID, "tkey": _TKEY, "prof": _PROF, "wan": _WAN, "as": _AS},
    },
    # ------------------------------------------------------------------ ルーティングプロトコルの注意点
    {
        "kind": "d_routing",
        "title": "DMVPN 上の EIGRP と OSPF の設定上の注意",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            '| 項目 | EIGRP | OSPF |\n'
            '|---|---|---|\n'
            '| ハブがスポークの経路を他スポークへ広告するために | «e_sh» | 不要(リンクステートに split horizon の概念は無い) |\n'
            '| Phase 2 で next-hop を対向スポークのまま届ける | «e_nhs» | «o_p2» |\n'
            '| トンネル IF のネットワークタイプ | (概念なし) | «o_type» |\n'
            '| DR/BDR | (概念なし) | «o_dr» |\n'
            '| Phase 3 のハブでの経路集約 | «e_sum» | エリア境界でしか集約できない(全員が同一エリアなら不可) |\n'
        ),
        "exhibit_md": True,
        "text": (
            "OSPF の point-to-multipoint は «p2mp_nh» ので Phase 1 向きで、Phase 2 の直接通信には使えない。"
            "broadcast タイプではスポークが DR になると «spoke_dr» ため、スポーク側で priority を 0 にする。"
            "Tunnel IF の OSPF ネットワークタイプは既定で «tun_def» であり、そのままでは複数のスポークと隣接を張れない。"
            "EIGRP では Phase を問わずハブの split horizon 解除が要り、Phase 2 だけ next-hop-self の無効化も要る。"
        ),
        "slots": {
            "e_sh": {"a": "no ip split-horizon eigrp <AS>", "d": ["no ip next-hop-self eigrp <AS>", "ip summary-address eigrp <AS>", "no auto-summary"], "grp": "eigrp", "why": "同じ Tunnel への再広告"},
            "e_nhs": {"a": "no ip next-hop-self eigrp <AS>", "d": ["no ip split-horizon eigrp <AS>", "ip summary-address eigrp <AS>", "no auto-summary"], "grp": "eigrp", "why": "ハブが next-hop を自分に書き換えない"},
            "e_sum": {"a": "ip summary-address eigrp <AS> <集約> <マスク>", "d": ["no ip split-horizon eigrp <AS>", "no ip next-hop-self eigrp <AS>", "no auto-summary"], "grp": "eigrp", "why": "Phase 3 では集約しても直接通信が成立"},
            "o_p2": {"a": "ip ospf network broadcast(next-hop が元のまま届く)", "d": ["ip ospf network point-to-multipoint", "ip ospf network point-to-point"], "why": "broadcast/non-broadcast は next-hop を書き換えない"},
            "o_type": {"a": "Phase 1= point-to-multipoint / Phase 2・3= broadcast", "d": ["Phase 1= broadcast / Phase 2・3= point-to-multipoint", "全 Phase で point-to-point"], "why": "教材の定石どおり"},
            "o_dr": {"a": "ハブだけが DR(スポークは ip ospf priority 0)", "d": ["スポークの 1 台が DR・ハブが BDR", "DR は不要(p2p なので)"], "why": "スポークは互いに直接届かないので DR になれない"},
            "p2mp_nh": {"a": "next-hop を常に広告元(ハブ)に書き換える", "d": ["DR を必要とする", "ホスト経路を広告しない"], "why": "p2mp は /32 のホスト経路を広告し next-hop は自分"},
            "spoke_dr": {"a": "他のスポークがその DR と直接隣接を張れず LSDB が同期しない", "d": ["ハブが BDR に降格して経路が消える", "hello の間隔が変わって隣接が落ちる"], "why": "スポーク同士のマルチキャストは届かない"},
            "tun_def": {"a": "point-to-point", "d": ["broadcast", "point-to-multipoint", "non-broadcast"], "why": "Tunnel IF の既定は p2p"},
        },
    },
    # ------------------------------------------------------------------ IPsec の連鎖(IKEv2 形)
    {
        "kind": "d_ipsec_chain",
        "title": "DMVPN を守る IPsec の連鎖(IKEv2 + IPsec プロファイル)",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            "crypto ikev2 proposal PROP-NGE\n"
            " encryption aes-gcm-256\n"
            " prf sha384\n"
            " group 19\n"
            "crypto ikev2 policy POL-NGE\n"
            " proposal PROP-NGE\n"
            "crypto ikev2 keyring KR-DMVPN\n"
            " peer ANY\n"
            "  address «wild»\n"
            "  pre-shared-key {psk}\n"
            "crypto ikev2 profile IKEV2-DMVPN\n"
            " match identity remote address «match»\n"
            " authentication remote pre-share\n"
            " authentication local pre-share\n"
            " keyring local KR-DMVPN\n"
            " dpd 30 5 on-demand\n"
            "crypto ipsec transform-set TS-GCM esp-gcm 256\n"
            " mode «mode»\n"
            "crypto ipsec profile {prof}\n"
            " set transform-set TS-GCM\n"
            " set pfs group19\n"
            " «setprof» IKEV2-DMVPN\n"
            "!\n"
            "interface Tunnel0\n"
            " tunnel protection ipsec profile {prof}\n"
        ),
        "text": (
            "オブジェクトは «chain» の順に参照される。keyring と profile を «wild_why» ため wildcard にしている。"
            "ピアごとにアドレスを絞ると «perpeer» ので、症状が hub-spoke 間に出ず気づきにくい(実測)。"
            "transform-set を «mode» にするのは «mode_why» からで、両端で食い違っても不通にはならず Tunnel モードに合意して上がる(実測)。"
            "«setprof» を書き忘れると «setprof_miss»。dpd は «dpd_role» で、IPsec で保護したトンネルでは GRE キープアライブの代わりになる。"
            "crypto map と違い、この方式ではどのトラフィックを暗号化するかの ACL が要らず、Tunnel を通る全パケットが対象になる。"
        ),
        "slots": {
            "wild": {"a": "0.0.0.0 0.0.0.0", "d": ["{hnbma} 255.255.255.255", "0.0.0.0 255.255.255.255"], "why": "任意のピア(スポーク間の対向は事前に不定)"},
            "match": {"a": "0.0.0.0", "d": ["{hnbma}", "any"], "why": "match identity remote address 0.0.0.0= 任意"},
            "mode": {"a": "transport", "d": ["tunnel", "aggressive"], "why": "GRE 済みなので transport"},
            "setprof": {"a": "set ikev2-profile", "d": ["set isakmp-profile", "set peer"], "why": "IPsec プロファイルから IKEv2 プロファイルを参照"},
            "chain": {"a": "proposal → policy → keyring → ikev2 profile → ipsec profile → tunnel protection", "d": ["keyring → proposal → policy → tunnel protection → ipsec profile", "ipsec profile → ikev2 profile → keyring → proposal"], "why": "定義される側が先・参照する側が後"},
            "wild_why": {"a": "スポーク間直接通信の相手 NBMA が事前に分からない", "d": ["ハブの NBMA が DHCP で変わる", "IKEv2 は個別アドレスの指定を許さない"], "why": "Phase 2/3 の動的直結には任意ピアが要る"},
            "perpeer": {"a": "hub-spoke は正常でスポーク間の直接通信だけ成立せず、通信自体はハブ折返しで通り続ける", "d": ["hub-spoke の IKE も成立しなくなる", "スポークの NHRP 登録が失敗する"], "why": "show dmvpn に IX/DX・traceroute 2 ホップ(実測)"},
            "mode_why": {"a": "GRE で外側 IP ヘッダが既に付いており、tunnel モードの外側 IP 20 バイトが無駄になる", "d": ["transport でないと NHRP が通らない", "IKEv2 は transport しか扱えない"], "why": "GRE over IPsec の定石"},
            "setprof_miss": {"a": "IKEv1(ISAKMP)にフォールバックし、ポリシーが無いので SA が上がらない", "d": ["既定の IKEv2 プロファイルが自動で使われる", "平文 GRE で通信が続く"], "why": "IPsec プロファイルは既定で ISAKMP を使う"},
            "dpd_role": {"a": "相手の死活監視(Dead Peer Detection)", "d": ["鍵の再交換間隔", "NAT 越えのキープアライブ"], "why": "on-demand= トラフィックがあるときだけ確認"},
        },
        "vars": {"psk": _PSK, "prof": _PROF, "hnbma": _HNBMA},
    },
    {
        "kind": "d_ipsec_chain",
        "title": "DMVPN を守る IPsec の連鎖(IKEv1/ISAKMP + IPsec プロファイル)",
        "diagram": None,
        "n_blanks": 5,
        "exhibit": (
            "crypto isakmp policy 10\n"
            " encryption aes 256\n"
            " hash sha256\n"
            " «auth_ps» pre-share\n"
            " group 14\n"
            "crypto isakmp key {psk} address «wild1»\n"
            "crypto isakmp keepalive 10 3\n"
            "crypto ipsec transform-set TS-AES esp-aes 256 esp-sha256-hmac\n"
            " mode «mode»\n"
            "crypto ipsec profile {prof}\n"
            " «set_ts» TS-AES\n"
            "!\n"
            "interface Tunnel0\n"
            " «tp» ipsec profile {prof}\n"
        ),
        "text": (
            "isakmp policy は «p1_role» で、encryption・hash・«auth_ps»・group・lifetime を相手と一致させる。"
            "事前共有鍵の address を «wild1» にしているのは «wild_why» ためである。"
            "transform-set は «p2_role» で、GRE 済みのトンネルなので «mode» にする。"
            "IPsec プロファイルは transform-set(と pfs)を束ねる器で、«tp» で Tunnel に貼ると Tunnel を通る全パケットが対象になる。"
            "crypto map 方式との違いは «vs_map» である。`crypto isakmp keepalive` は «ka_role» である。"
        ),
        "slots": {
            "auth_ps": {"a": "authentication", "d": ["encryption", "identity"], "why": "authentication pre-share= 事前共有鍵"},
            "wild1": {"a": "0.0.0.0", "d": ["{hnbma}", "255.255.255.255"], "why": "任意のピア(スポーク間の対向は事前に不定)"},
            "mode": {"a": "transport", "d": ["tunnel", "main"], "why": "GRE 済みなので transport"},
            "set_ts": {"a": "set transform-set", "d": ["set peer", "match address"], "why": "プロファイルは transform-set を参照"},
            "tp": {"a": "tunnel protection", "d": ["crypto map", "tunnel mode ipsec ipv4"], "why": "Tunnel IF に IPsec を直載せ"},
            "p1_role": {"a": "IKE フェーズ 1(ISAKMP SA)の交渉条件", "d": ["IKE フェーズ 2(IPsec SA)の交渉条件", "GRE トンネルの認証"], "why": "policy= フェーズ 1"},
            "wild_why": {"a": "スポーク間直接通信の相手 NBMA が事前に分からない", "d": ["ハブの NBMA が DHCP で変わる", "IKEv1 は個別アドレスの指定を許さない"], "why": "Phase 2/3 の動的直結には任意ピアが要る"},
            "p2_role": {"a": "IKE フェーズ 2(IPsec SA)で使う ESP のアルゴリズムとモード", "d": ["IKE フェーズ 1 の暗号とハッシュ", "NHRP の認証方式"], "why": "transform-set= フェーズ 2"},
            "vs_map": {"a": "暗号化対象を ACL で列挙せず、物理 IF ではなく Tunnel IF に適用する", "d": ["ISAKMP ポリシーが要らない", "事前共有鍵の代わりに証明書が必須になる"], "why": "crypto map= 物理 IF + match address ACL"},
            "ka_role": {"a": "DPD(相手の死活監視)の間隔と回数", "d": ["GRE キープアライブの間隔", "SA のライフタイム"], "why": "IPsec 上では GRE keepalive は使えない"},
        },
        "vars": {"psk": _PSK, "prof": _PROF, "hnbma": _HNBMA},
    },
    # ------------------------------------------------------------------ IKE フェーズと ESP/AH
    {
        "kind": "d_ike_phases",
        "title": "IKE フェーズ 1 / 2 と ESP・AH・モードの整理",
        "diagram": None,
        "n_blanks": 6,
        "exhibit": (
            '| 項目 | IKE フェーズ 1 | IKE フェーズ 2 |\n'
            '|---|---|---|\n'
            '| 作る SA | «p1_sa» | «p2_sa» |\n'
            '| 交渉する内容 | «p1_neg» | «p2_neg» |\n'
            '| IKEv1 のモード | «p1_mode» | クイックモード |\n'
            '| 確認コマンド | show crypto isakmp sa(QM_IDLE なら完了) | «p2_show» |\n'
            '| IKEv2 での対応 | «v2_p1» | CHILD_SA(CREATE_CHILD_SA で追加・鍵更新) |\n'
        ),
        "exhibit_md": True,
        "text": (
            "IKE は UDP «ike_port» で動き、途中に NAT があると UDP «natt_port» の NAT-T に切り替わる。"
            "データを運ぶのは «esp» で、暗号化と認証の両方を提供する。もう 1 つのプロトコル AH(IP プロトコル 51)は «ah» ので、NAT 環境では使えない。"
            "tunnel モードは «tun_mode»、transport モードは元の IP ヘッダを残してペイロードだけを保護する。"
            "DMVPN では GRE が外側ヘッダを付けるので transport が定石である。"
        ),
        "slots": {
            "p1_sa": {"a": "ISAKMP SA(IKE SA・双方向で 1 本)", "d": ["IPsec SA(方向ごとに 1 本・計 2 本)", "GRE トンネル"], "grp": "sa", "why": "制御用の 1 本"},
            "p2_sa": {"a": "IPsec SA(方向ごとに 1 本・計 2 本)", "d": ["ISAKMP SA(IKE SA・双方向で 1 本)", "GRE トンネル"], "grp": "sa", "why": "データ用は片方向ずつ"},
            "p1_neg": {"a": "暗号・ハッシュ・認証方式・DH グループ・ライフタイム(ポリシー)", "d": ["トランスフォームセット(ESP/AH・アルゴリズム・モード)と PFS", "NHRP の認証文字列と holdtime"], "grp": "neg", "why": "HAGLE"},
            "p2_neg": {"a": "トランスフォームセット(ESP/AH・アルゴリズム・モード)と PFS", "d": ["暗号・ハッシュ・認証方式・DH グループ・ライフタイム(ポリシー)", "NHRP の認証文字列と holdtime"], "grp": "neg", "why": "データ保護の条件"},
            "p1_mode": {"a": "メインモード(6 メッセージ)またはアグレッシブモード(3 メッセージ)", "d": ["クイックモード", "トランスポートモード"], "why": "フェーズ 1 の 2 方式"},
            "p2_show": {"a": "show crypto ipsec sa(encaps/decaps のカウンタ)", "d": ["show crypto isakmp policy", "show dmvpn"], "why": "IPsec SA と実トラフィックの確認"},
            "v2_p1": {"a": "IKE_SA_INIT + IKE_AUTH(4 メッセージで IKE SA と最初の CHILD_SA)", "d": ["メインモード(6 メッセージ)", "CREATE_CHILD_SA"], "why": "IKEv2 は往復 2 回で完了"},
            "ike_port": {"a": "500", "d": ["4500", "51", "50"], "grp": "num", "why": "ISAKMP/IKE= UDP 500"},
            "natt_port": {"a": "4500", "d": ["500", "51", "50"], "grp": "num", "why": "NAT-T= UDP 4500 に ESP を包む"},
            "esp": {"a": "ESP(IP プロトコル 50)", "d": ["AH(IP プロトコル 51)", "GRE(IP プロトコル 47)"], "why": "暗号化+認証"},
            "ah": {"a": "IP ヘッダを含めて認証し暗号化はしない", "d": ["暗号化だけを行う", "ペイロードだけを認証する"], "why": "NAT で IP ヘッダが変わると認証が壊れる"},
            "tun_mode": {"a": "元のパケット全体を包んで新しい外側 IP ヘッダを付ける", "d": ["元の IP ヘッダを残してペイロードだけを保護する", "GRE ヘッダだけを暗号化する"], "why": "拠点間 VPN の既定"},
        },
    },
    # ------------------------------------------------------------------ show dmvpn の読み方(世界)
    {
        "kind": "d_show",
        "title": "show dmvpn の State/Attrb で故障の層を割る",
        "diagram": None,
        "worlds": ["ike", "nhrp", "up"],
        "world_desc": {"ike": "State IKE(IPsec が上がらない: 鍵・NBMA 到達性・protection 片側欠落)",
                       "nhrp": "State NHRP(IKEv2 は READY・登録が通らない: tunnel key・NHRP 認証・NHS アドレス)",
                       "up": "State UP(正常)"},
        "exhibit": {
            "ike": (
                "RT02# show dmvpn\n" + _SHOW_LEGEND +
                "Interface: Tunnel0, IPv4 NHRP Details\n"
                "Type:Spoke, NHRP Peers:1,\n"
                " # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb\n"
                " ----- --------------- --------------- ----- -------- -----\n"
                "     1 {hnbma}       {htip}     IKE    never     S\n"
                "RT02# show crypto ikev2 sa\n"
                " IPv4 Crypto IKEv2  SA\n"
                "(エントリなし)\n"
            ),
            "nhrp": (
                "RT02# show dmvpn\n" + _SHOW_LEGEND +
                "Interface: Tunnel0, IPv4 NHRP Details\n"
                "Type:Spoke, NHRP Peers:1,\n"
                " # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb\n"
                " ----- --------------- --------------- ----- -------- -----\n"
                "     1 {hnbma}       {htip}    NHRP    never     S\n"
                "RT02# show crypto ikev2 sa\n"
                " IPv4 Crypto IKEv2  SA\n"
                "Tunnel-id Local                 Remote                fvrf/ivrf            Status\n"
                "1         {snbma}/500          {hnbma}/500          none/none            READY\n"
                "RT02# show ip nhrp nhs detail\n"
                "Legend: E=Expecting replies, R=Responding, W=Waiting\n"
                "Tunnel0:\n"
                "{htip}  E priority = 0 cluster = 0  req-sent 42  req-failed 0  repl-recv 0\n"
                "Pending Registration Requests:\n"
                "Registration Request: Reqid 8, Ret 64  NHS {htip} expired\n"
            ),
            "up": (
                "RT02# show dmvpn\n" + _SHOW_LEGEND +
                "Interface: Tunnel0, IPv4 NHRP Details\n"
                "Type:Spoke, NHRP Peers:1,\n"
                " # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb\n"
                " ----- --------------- --------------- ----- -------- -----\n"
                "     1 {hnbma}       {htip}     UP 00:12:34     S\n"
                "RT02# show crypto ikev2 sa\n"
                " IPv4 Crypto IKEv2  SA\n"
                "Tunnel-id Local                 Remote                fvrf/ivrf            Status\n"
                "1         {snbma}/500          {hnbma}/500          none/none            READY\n"
            ),
        },
        "text": (
            "State 列は下の層から «order» の順に上がる。この盤面で疑うべきなのは «layer» で、次に打つコマンドは «next_cmd»。"
            "Attrb の S は «attrb_s»、ハブ側で見える D は «attrb_d» を表す。"
            "Phase 3 でショートカットが成立すると Attrb に «dt» が付く。"
            "State が UP でも Attrb に «ix» が残っているときは、スポーク間の IPsec ソケットが作れていない(keyring をピアごとに絞った典型)。"
            "tunnel key の不一致はハブ側に痕跡が出ない一方、NHRP 認証の不一致はハブのログに wrong authentication string が出る(IOL 実測)。"
        ),
        "slots": {
            "order": {"a": "IKE → NHRP → UP", "d": ["NHRP → IKE → UP", "UP → NHRP → IKE"], "why": "IPsec が上がらないと GRE/NHRP に進めない"},
            "layer": {"a": {"ike": "IPsec/IKE(事前共有鍵・ハブ NBMA への到達性・tunnel protection の片側欠落)",
                            "nhrp": "GRE/NHRP(tunnel key・NHRP 認証・NHS のトンネル IP)",
                            "up": "どの層も正常(次はルーティングプロトコルの隣接を見る)"},
                      "d": ["EIGRP(split-horizon・next-hop-self の誤り)"],
                      "why": {"ike": "State IKE= IPsec 不成立", "nhrp": "IKEv2 READY なのに登録が通らない= GRE/NHRP 層", "up": "UP は NHRP 登録まで完了"}},
            "next_cmd": {"a": {"ike": "show crypto ikev2 sa(IKEv1 なら show crypto isakmp sa)", "nhrp": "show ip nhrp nhs detail", "up": "show ip eigrp neighbors"},
                         "d": ["show ip route"],
                         "why": {"ike": "IKE SA の有無と状態", "nhrp": "登録要求の送信回数と応答ゼロを見る", "up": "次の層へ"}},
            "attrb_s": {"a": "静的エントリ(スポークが設定で持つ NHS の対応)", "d": ["ショートカットで学んだエントリ", "NAT 越えのエントリ"], "why": "S= Static"},
            "attrb_d": {"a": "動的エントリ(登録や解決で学んだ対応)", "d": ["静的エントリ(設定で持つ対応)", "不完全なエントリ"], "why": "D= Dynamic"},
            "dt": {"a": "DT1 / DT2(T1= 経路がインストール済・T2= next-hop override)", "d": ["S / D", "N / L"], "why": "shortcut 成立の印(実測)"},
            "ix": {"a": "X(No Socket)= IX や DX", "d": ["T2", "L"], "why": "ソケット無し= IPsec が組めていない残骸"},
        },
        "vars": {"tnet": ["10.255.0", "172.31.255", "10.200.0"], "htip": lambda v, w: f"{v['tnet']}.1",
                 "hnbma": _HNBMA, "snbma": _SNBMA},
        "var_links": {"hnbma": "snbma"},
    },
    # ------------------------------------------------------------------ MTU / MSS
    {
        "kind": "d_mtu",
        "title": "GRE/IPsec のオーバーヘッドと ip mtu / ip tcp adjust-mss",
        "diagram": None,
        "exhibit": None,
        "text": (
            "GRE は元のパケットに新しい IP ヘッダ 20 バイトと GRE ヘッダ «gre_hdr» バイト(tunnel key 付きなら +4)を足すので、"
            "物理 MTU 1500 の Tunnel IF の既定 ip mtu は «def_mtu» になる。IPsec(ESP transport)がさらに 50〜60 バイトほど足す。"
            "DMVPN の定石は Tunnel IF に `ip mtu «rec_mtu»` と `ip tcp adjust-mss «rec_mss»` で、MSS は ip mtu から IP と TCP のヘッダ分を引いた値にする。"
            "adjust-mss は «mss_how» ので、PMTUD が ICMP フィルタで壊れている環境でも効く。"
            "ip mtu を書かなくても小さな ping は通る(実測では外側 GRE が断片化して救済され、DF は外側に複製されない)が、"
            "断片化は «frag_cost» を招くので明示するのが定石である。"
        ),
        "slots": {
            "gre_hdr": {"a": "4", "d": ["8", "20", "24"], "grp": "num", "why": "GRE 基本ヘッダ 4(+key 4)。IP 20 と合わせて 24"},
            "def_mtu": {"a": "1476", "d": ["1500", "1400", "1472"], "grp": "num", "why": "1500 − 24"},
            "rec_mtu": {"a": "1400", "d": ["1476", "1460", "1500"], "grp": "num", "why": "IPsec の余地を見込んだ定番"},
            "rec_mss": {"a": "1360", "d": ["1400", "1436", "1460"], "grp": "num", "why": "1400 − 40(IP 20 + TCP 20)"},
            "mss_how": {"a": "TCP の SYN に載る MSS を書き換えて端末に最初から小さいセグメントを送らせる", "d": ["ICMP Fragmentation Needed を代理で返す", "GRE ヘッダを圧縮して MTU を稼ぐ"], "why": "エンド側で未然防止"},
            "frag_cost": {"a": "ハブの CPU 負荷と PMTUD ブラックホール", "d": ["NHRP 登録の失敗", "IKE SA の再交渉"], "why": "断片化の再構成はプロセス処理"},
        },
    },
    # ------------------------------------------------------------------ オーバーレイ運用の罠
    {
        "kind": "d_overlay",
        "title": "オーバーレイ運用の罠: 再帰ルーティング・map multicast の引数・shared・protection 変更",
        "diagram": None,
        "exhibit": None,
        "text": (
            "トンネルの宛先(NBMA)への経路をトンネル自身から学ぶと «recur» になる。p2p GRE では «recur_log» が出て Tunnel が周期的に落ちるが、"
            "mGRE ではこのログが出ず、約 15 秒周期の EIGRP 隣接フラップと `show ip route <NBMA>` が via Tunnel0 になることで見抜く(実測)。"
            "原因の典型はハブが underlay の網をクラスフルな network 文でオーバーレイの IGP に広告してしまうことで、対策は «recur_fix»。"
            "旧来 3 行構文の `ip nhrp map multicast` の引数は «mcast_arg» で、トンネル IP を書くとユニキャストは全部正常なのに EIGRP だけ retry limit でフラップする(実測)。"
            "同じ tunnel source を持つ複数の Tunnel に同じ IPsec プロファイルを貼るときは «shared» が要り、片方だけに付けると設定が拒否される(実測)。"
            "稼働中の Tunnel で tunnel protection を変更すると «prot_change» ので、作業手順に no shutdown を入れておく(実測)。"
            "underlay と overlay の経路表を分けたいときは «fvrf» で tunnel source 側の IF と default route を別 VRF に置く。"
        ),
        "slots": {
            "recur": {"a": "再帰ルーティング(トンネルが自分の中を通ろうとして落ちる)", "d": ["非対称ルーティング", "ルーティングループ(TTL 切れ)"], "why": "tunnel destination が Tunnel 経由になる矛盾"},
            "recur_log": {"a": "%TUN-5-RECURDOWN", "d": ["%DMVPN-3-DMVPN_NHRP_ERROR", "%DUAL-5-NBRCHANGE", "%TUN-4-MTUCONFIG"], "why": "p2p GRE 専用のメッセージ"},
            "recur_fix": {"a": "underlay の経路をオーバーレイの IGP に入れない(NBMA への経路は WAN 向きの static/既定経路に限る)", "d": ["tunnel key を両端で揃える", "ip nhrp holdtime を短くする"], "why": "NBMA への経路は必ず物理側"},
            "mcast_arg": {"a": "ハブの NBMA アドレス", "d": ["ハブのトンネル IP", "224.0.0.10"], "why": "map multicast <NBMA>(実測: トンネル IP だと EIGRP だけフラップ)"},
            "shared": {"a": "tunnel protection … shared(全 Tunnel に)", "d": ["tunnel key を Tunnel ごとに変える", "ip nhrp network-id を Tunnel ごとに変える"], "why": "暗号ソケットの共有。同一 source+同一 profile の全 Tunnel に必要"},
            "prot_change": {"a": "Tunnel が自動的に shutdown される", "d": ["IKE SA だけが再交渉される", "NHRP キャッシュが消えるだけで通信は続く"], "why": "%Shutting down TunnelN interface due to IPsec tunnel protection modification(実測)"},
            "fvrf": {"a": "front-door VRF(tunnel vrf <名>)", "d": ["ip nhrp network-id", "tunnel key"], "why": "underlay を fVRF に隔離すると再帰ルーティングも構造的に防げる"},
        },
    },
]
