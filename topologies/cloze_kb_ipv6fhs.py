#!/usr/bin/env python3
"""cloze_kb_ipv6fhs.py — 解説穴埋め形(shape=cloze) の知識ベース: IPv6 First Hop Security(BL-193)

書式は cloze_kb_mpls.py と同じ(PASSAGES / slots / vars / scope)。
範囲= ENARSI 4.x 「Describe IPv6 First Hop security features (RA guard, DHCP guard, binding table,
ND inspection/snooping, source guard)」。prefix guard / destination guard / RFC 7113 の回避手口は
解説(why)に留めるか `scope: beyond`。

事実の出所:
- 公式 IPv6 FHS 設定ガイド(IOS XE 17): RA Guard(RA と Redirect を検査・着信方向のみ・policy 副コマンド)/
  DHCPv6 Guard(サーバ発 ADVERTISE/REPLY とリレー→クライアントを破棄・クライアント発は通す)/
  Snooping(ND の NS/NA/RS/RA/Redirect と DHCPv6 の IA_NA/IA_PD から表を作る)/
  Source Guard(表に無い送信元を破棄・拒否時に DHCP 照会または ND で復元を試みる・permit link-local / deny global-autoconf / validate address|prefix)。
- poc/fhs/README.md(ioll2-xe 17.15.1 実測): 旧 `ipv6 snooping` は無く SISF=`device-tracking policy`・
  ポートポリシーが VLAN ポリシーに勝つ・VLAN だけに host を付けると正規 GW の RA も落ちる・
  `show running-config` は既定値(device-role host / security-level guard)を表示しない・
  Dropped 理由文字列= `RA guard: NDP RA [n] reason: Message unauthorized on port` /
  `DHCP Guard: DHCPv6 REP [n] reason: Message type is not authorized by the policy on this port, device-role mismatch` /
  `Preference flag error`(router-preference maximum 超過)。
"""

DIAG_ACCESS = (
    "graph LR\n"
    "  GW[GW ルータ] ---|{up_if}| SW[アクセス SW]\n"
    "  SW ---|{h1_if}| H1[PC1]\n"
    "  SW ---|{h2_if}| H2[PC2]\n"
    "  SW ---|{rog_if}| ROG[不正端末]\n"
)

PASSAGES = [
    # ------------------------------------------------------------------ 攻撃と機能の対応
    {
        "kind": "f_attacks",
        "title": "IPv6 の第一ホップで起きる攻撃と、それを止める機能",
        "diagram": None,
        "exhibit": None,
        "text": (
            "IPv6 の LAN では、端末はルータからの «ra» を受け取ってデフォルトゲートウェイと SLAAC 用のプレフィックスを知る。"
            "したがって同じ VLAN の端末が偽の広告を送るだけで、他の端末の既定経路を自分に向けられる。これをスイッチのポートで止めるのが «raguard» である。"
            "同様に、偽の DHCPv6 サーバが ADVERTISE/REPLY を返して誤った «dns» を配る攻撃は «dhcpguard» で止める。"
            "一方、端末が他人のアドレスを名乗る(NA を偽って ND キャッシュを書き換える、または送信元アドレスを偽装する)攻撃には、"
            "まず «snoop» でリンク上の「IPv6 アドレスと MAC とポート」の正しい対応を «bindtab» に集め、"
            "ND メッセージの検証は «ndinsp» が、データパケットの送信元検証は «srcguard» がこの表を引いて行う。"
            "つまり前の 2 つは制御メッセージそのものを検査し、残りの機能は表を作る側と表を使う側に分かれる。"
        ),
        "slots": {
            "ra": {"a": "RA(Router Advertisement)", "d": ["NS(Neighbor Solicitation)", "DHCPv6 ADVERTISE"], "why": "既定 GW とプレフィックスを配るのは RA"},
            "raguard": {"a": "RA guard", "d": ["DHCPv6 guard", "IPv6 source guard"], "why": "偽 RA を止めるのは RA guard"},
            "dns": {"a": "DNS サーバアドレス", "d": ["デフォルトゲートウェイ", "MAC アドレス"], "why": "DHCPv6 が配るのは DNS/ドメインなど。GW は RA が配る"},
            "dhcpguard": {"a": "DHCPv6 guard", "d": ["RA guard", "ND inspection"], "why": "偽 DHCPv6 サーバの応答を止めるのは DHCPv6 guard"},
            "snoop": {"a": "IPv6 snooping(アドレスグリーニング)", "d": ["IPv6 source guard", "RA guard"], "why": "ND/DHCPv6 を覗いて表を作るのが snooping(17.x では device-tracking)"},
            "bindtab": {"a": "バインディングテーブル", "d": ["ND キャッシュ", "MAC アドレステーブル"], "why": "FHS が参照する DB はバインディングテーブル。ND キャッシュはルータの解決結果"},
            "ndinsp": {"a": "ND inspection", "d": ["IPv6 source guard", "DHCPv6 guard"], "why": "ND メッセージの検証は ND inspection"},
            "srcguard": {"a": "IPv6 source guard", "d": ["ND inspection", "uRPF"], "why": "データの送信元を表で検証するのは source guard"},
        },
    },
    # ------------------------------------------------------------------ ND メッセージと DHCPv6 の基礎
    {
        "kind": "f_ndmsgs",
        "title": "FHS が検査する ND メッセージと DHCPv6 メッセージ",
        "diagram": None,
        "exhibit": (
            '| ICMPv6 type | 名称 | 主な宛先 |\n'
            '|---|---|---|\n'
            '| 133 | «rs» | ff02::2(全ルータ) |\n'
            '| 134 | «ra_name» | ff02::1(全ノード) または ユニキャスト |\n'
            '| 135 | NS(Neighbor Solicitation) | 要請ノードマルチキャスト ff02::1:ffxx:xxxx |\n'
            '| 136 | «na» | 要請元ユニキャスト(または ff02::1) |\n'
            '| 137 | Redirect | 送信元ホスト |\n'
            '| DHCPv6 | クライアント UDP «cport» / サーバ・リレー UDP «sport» | ff02::1:2(全 DHCP リレー/サーバ) |\n'
        ),
        "exhibit_md": True,
        "text": (
            "第一ホップの機能は上の表のメッセージを対象にする。端末は起動時に «rs» を全ルータ宛に送り、ルータは «ra_name» で応える。"
            "RA には M フラグと O フラグがあり、M=1 なら «mflag»、M=0/O=1 なら «oflag» を意味する。RA guard はこの RA と、"
            "経路変更を指示する «redirect» の 2 種類を検査する。DHCPv6 guard が破棄するのはサーバ側が送る «srv_msgs» で、"
            "クライアントが送る SOLICIT/REQUEST は通す。アドレス解決の NS と、それに答える «na» は ND inspection の検査対象で、"
            "表と食い違う「IPv6 アドレス→MAC」を主張する NA が捨てられる。"
        ),
        "slots": {
            "rs": {"a": "RS(Router Solicitation)", "d": ["NS(Neighbor Solicitation)", "Redirect"], "why": "type 133 は RS。ルータを探す"},
            "ra_name": {"a": "RA(Router Advertisement)", "d": ["NA(Neighbor Advertisement)", "DHCPv6 ADVERTISE"], "why": "type 134 は RA"},
            "na": {"a": "NA(Neighbor Advertisement)", "d": ["RA(Router Advertisement)", "RS(Router Solicitation)"], "why": "type 136 は NA。NS への応答"},
            "cport": {"a": "546", "d": ["547", "68"], "why": "DHCPv6 クライアントは UDP 546(IPv4 の 68 に相当)"},
            "sport": {"a": "547", "d": ["546", "67"], "why": "DHCPv6 サーバ/リレーは UDP 547"},
            "mflag": {"a": "ステートフル DHCPv6 でアドレスを取る", "d": ["SLAAC でアドレスを作る", "DHCPv6 で DNS だけ取る"], "why": "M(Managed)=1 はアドレスを DHCPv6 から"},
            "oflag": {"a": "アドレスは SLAAC・その他情報(DNS 等)は DHCPv6", "d": ["アドレスも DNS も DHCPv6", "DHCPv6 を使わない"], "why": "O(Other)=1 は情報だけ DHCPv6(stateless DHCPv6)"},
            "redirect": {"a": "Redirect(type 137)", "d": ["NS(type 135)", "RS(type 133)"], "why": "RA guard は RA と Redirect を検査する"},
            "srv_msgs": {"a": "ADVERTISE と REPLY", "d": ["SOLICIT と REQUEST", "RS と RA"], "why": "DHCPv6 guard はサーバ発(とリレー→クライアント)の応答を破棄"},
        },
    },
    # ------------------------------------------------------------------ RA guard のポリシー
    {
        "kind": "f_raguard",
        "title": "RA guard ポリシーの意味と適用先",
        "diagram": DIAG_ACCESS,
        "worlds": ["router", "host", "vlan_only"],
        "world_desc": {"router": "GW ポートに router ポリシー(正しい構成)",
                       "host": "GW ポートに端末用(host)ポリシーを付けてしまった",
                       "vlan_only": "host ポリシーを VLAN だけに付け、GW ポートにはポート側ポリシーが無い"},
        "exhibit": {
            "router": (
                "ipv6 nd raguard policy {pol_host}\n"
                " device-role host\n"
                "ipv6 nd raguard policy {pol_up}\n"
                " device-role router\n"
                " router-preference maximum {pref}\n"
                "!\n"
                "interface {up_if}\n"
                " ipv6 nd raguard attach-policy {pol_up}\n"
                "interface {h1_if}\n"
                " ipv6 nd raguard attach-policy {pol_host}\n"
                "interface {rog_if}\n"
                " ipv6 nd raguard attach-policy {pol_host}\n"
            ),
            "host": (
                "ipv6 nd raguard policy {pol_host}\n"
                " device-role host\n"
                "ipv6 nd raguard policy {pol_up}\n"
                " device-role router\n"
                " router-preference maximum {pref}\n"
                "!\n"
                "interface {up_if}\n"
                " ipv6 nd raguard attach-policy {pol_host}\n"
                "interface {h1_if}\n"
                " ipv6 nd raguard attach-policy {pol_host}\n"
                "interface {rog_if}\n"
                " ipv6 nd raguard attach-policy {pol_host}\n"
            ),
            "vlan_only": (
                "ipv6 nd raguard policy {pol_host}\n"
                " device-role host\n"
                "!\n"
                "vlan configuration {vlan}\n"
                " ipv6 nd raguard attach-policy {pol_host}\n"
                "!\n"
                "interface {up_if}\n"
                " switchport access vlan {vlan}\n"
                " ! (ポートにはポリシーなし)\n"
                "interface {h1_if}\n"
                " switchport access vlan {vlan}\n"
                "interface {rog_if}\n"
                " switchport access vlan {vlan}\n"
            ),
        },
        "text": (
            "上はアクセススイッチの設定で、{up_if} に正規 GW、{h1_if} に端末、{rog_if} に不正端末がつながる(全ポート VLAN {vlan})。"
            "RA guard は «direction» 方向でだけ働く。不正端末が {rog_if} から送る RA は «rog_result»。"
            "正規 GW が {up_if} から送る RA は «gw_result»。その結果、端末 {h1_if} は «host_state»。"
            "この盤面で `show device-tracking counters interface {up_if}` の Dropped 欄には «reason»。"
            "是正として妥当なのは «fix»。なおポートと VLAN の両方にポリシーがあるときは «precedence» が勝ち、"
            "検査を一切しないポートにしたいときは device-role の代わりに «trusted» を書く。"
        ),
        "slots": {
            "direction": {"a": "着信(ingress)", "d": ["送信(egress)", "双方向"], "why": "RA guard は ingress のみ"},
            "rog_result": {"a": {"router": "端末ポートの host ポリシーで破棄される",
                                 "host": "端末ポートの host ポリシーで破棄される",
                                 "vlan_only": "VLAN の host ポリシーで破棄される"},
                           "d": ["検査を通れば転送される", "ログだけ取られて転送される"],
                           "why": "不正端末側は host 扱いなので RA は捨てられる"},
            "gw_result": {"a": {"router": "優先度と prefix の検査を通れば転送される",
                                "host": "GW ポートに付いた host ポリシーで無条件に破棄される",
                                "vlan_only": "ポート側にポリシーが無く VLAN の host が効いて破棄される"},
                          "d": ["監視モードで通過する"],
                          "why": {"router": "router ポリシーは RA を通す(検査つき)",
                                  "host": "host は RA を無条件に捨てる",
                                  "vlan_only": "VLAN のポリシーは全ポートに効く(実測: 守り過ぎ)"}},
            "host_state": {"a": {"router": "GUA と既定 GW を正常に得る",
                                 "host": "リンクローカルだけで GUA も既定 GW も無い",
                                 "vlan_only": "リンクローカルだけで GUA も既定 GW も無い"},
                           "d": ["GUA はあるが DNS が無い"],
                           "why": "RA が届くかどうかで SLAAC と既定 GW の有無が決まる"},
            "reason": {"a": {"router": "何も出ない(GW の RA は落ちていない)",
                             "host": "Message unauthorized on port が出る",
                             "vlan_only": "Message unauthorized on port が出る"},
                       "d": ["Preference flag error が出る"],
                       "why": {"router": "落ちていないので理由は記録されない",
                               "host": "host 扱いのポートで RA を受けた理由文字列(実測)",
                               "vlan_only": "VLAN の host が効いたときも同じ理由文字列(実測)"}},
            "fix": {"a": {"router": "是正不要(意図どおり)",
                          "host": "{up_if} のポリシーを device-role router のものに付け替える",
                          "vlan_only": "{up_if} にポート側で device-role router のポリシーを付ける"},
                    "d": ["{h1_if} のポリシーを外す"],
                    "why": {"router": "GW の RA は通り、不正 RA は落ちている",
                            "host": "GW ポートは router(または trusted-port)",
                            "vlan_only": "ポートのポリシーが VLAN のポリシーに勝つ(実測)"}},
            "precedence": {"a": "ポートのポリシー", "d": ["VLAN のポリシー", "後から付けた方"], "why": "ポート > VLAN(実測)"},
            "trusted": {"a": "trusted-port", "d": ["device-role switch", "permit link-local"], "why": "trusted-port は RA guard の検査を無効化"},
        },
        "vars": {
            "pol_host": ["RAG-HOST", "HOSTS", "RA-EDGE"],
            "pol_up": ["RAG-UPLINK", "ROUTERS", "RA-GW"],
            "pref": ["medium", "high"],
            "vlan": ["10", "20", "30"],
            "up_if": ["Ethernet0/0", "GigabitEthernet1/0/1", "GigabitEthernet0/1"],
            "h1_if": ["Ethernet0/1", "GigabitEthernet1/0/10", "GigabitEthernet0/2"],
            "h2_if": ["Ethernet0/2", "GigabitEthernet1/0/11", "GigabitEthernet0/3"],
            "rog_if": ["Ethernet0/3", "GigabitEthernet1/0/12", "GigabitEthernet0/4"],
        },
        "var_links": {"up_if": "h1_if", "h1_if": "h2_if", "h2_if": "rog_if"},
    },
    # ------------------------------------------------------------------ DHCPv6 guard
    {
        "kind": "f_dhcpguard",
        "title": "DHCPv6 guard の検査対象とポリシー",
        "diagram": DIAG_ACCESS,
        "worlds": ["ok", "swapped", "none_edge"],
        "world_desc": {"ok": "GW ポート server・端末ポート client(正しい構成)",
                       "swapped": "GW ポートに端末用(client)ポリシーを付けてしまった",
                       "none_edge": "GW ポートは server だが不正端末のポートにポリシーが無い"},
        "exhibit": {
            "ok": (
                "ipv6 dhcp guard policy {pol_cli}\n device-role client\n"
                "ipv6 dhcp guard policy {pol_srv}\n device-role server\n match server access-list {acl}\n"
                "!\nipv6 access-list {acl}\n permit ipv6 host {srv_addr} any\n!\n"
                "interface {up_if}\n ipv6 dhcp guard attach-policy {pol_srv}\n"
                "interface {h1_if}\n ipv6 dhcp guard attach-policy {pol_cli}\n"
                "interface {rog_if}\n ipv6 dhcp guard attach-policy {pol_cli}\n"
            ),
            "swapped": (
                "ipv6 dhcp guard policy {pol_cli}\n device-role client\n"
                "ipv6 dhcp guard policy {pol_srv}\n device-role server\n match server access-list {acl}\n"
                "!\nipv6 access-list {acl}\n permit ipv6 host {srv_addr} any\n!\n"
                "interface {up_if}\n ipv6 dhcp guard attach-policy {pol_cli}\n"
                "interface {h1_if}\n ipv6 dhcp guard attach-policy {pol_cli}\n"
                "interface {rog_if}\n ipv6 dhcp guard attach-policy {pol_cli}\n"
            ),
            "none_edge": (
                "ipv6 dhcp guard policy {pol_cli}\n device-role client\n"
                "ipv6 dhcp guard policy {pol_srv}\n device-role server\n match server access-list {acl}\n"
                "!\nipv6 access-list {acl}\n permit ipv6 host {srv_addr} any\n!\n"
                "interface {up_if}\n ipv6 dhcp guard attach-policy {pol_srv}\n"
                "interface {h1_if}\n ipv6 dhcp guard attach-policy {pol_cli}\n"
                "interface {rog_if}\n ! (ポリシーなし)\n"
            ),
        },
        "text": (
            "上はアクセススイッチの設定で、{up_if} の先に正規の DHCPv6 サーバ(リレー)、{h1_if} に端末、{rog_if} に偽サーバを動かす不正端末がつながる。"
            "DHCPv6 guard が破棄するのは、サーバやリレーが «dir» 向きに送る «msgs» で、端末が送る SOLICIT/REQUEST は検査せず通す。"
            "この盤面で、正規サーバの応答が {up_if} から入ると «gw_reply»。偽サーバの応答が {rog_if} から入ると «rog_reply»。"
            "その結果、端末 {h1_if} は «symptom»。`show device-tracking counters interface {up_if}` の Dropped 欄には «reason»。"
            "是正として妥当なのは «fix»。なお «acl_match» でサーバ/リレーの送信元アドレスも検査でき、優先度は «pref_chk» で範囲を絞れる。"
        ),
        "slots": {
            "dir": {"a": "クライアント", "d": ["サーバ", "リレー"], "why": "守るのは端末へ届く応答"},
            "msgs": {"a": "ADVERTISE と REPLY", "d": ["SOLICIT と REQUEST", "RS と RA"], "why": "サーバ発の応答が対象"},
            "gw_reply": {"a": {"ok": "server ポリシーなので検査を通って転送される",
                               "swapped": "GW ポートに付いた client ポリシーで破棄される",
                               "none_edge": "server ポリシーなので検査を通って転送される"},
                         "d": ["ログだけ取られて転送される"],
                         "why": {"ok": "server 役のポートからの応答は許可", "swapped": "client 役のポートでは応答は捨てられる", "none_edge": "server 役のポートからの応答は許可"}},
            "rog_reply": {"a": {"ok": "端末ポートの client ポリシーで破棄される",
                                "swapped": "端末ポートの client ポリシーで破棄される",
                                "none_edge": "ポリシーが無いので素通りする"},
                          "d": ["match server access-list で破棄される"],
                          "why": {"ok": "client 役のポートからの応答は捨てる", "swapped": "client 役のポートからの応答は捨てる", "none_edge": "attach していないポートは検査されない"}},
            "symptom": {"a": {"ok": "正規サーバの DNS とドメインを正常に得る",
                              "swapped": "RA は正常だが DNS やドメイン名を取得できない",
                              "none_edge": "先に応答した方の DNS を掴み、偽サーバの値になることがある"},
                        "d": ["GUA が付かずリンクローカルだけになる"],
                        "why": {"ok": "応答は正規だけが届く", "swapped": "SLAAC は生きるので O フラグで取る情報だけ欠ける(実測)", "none_edge": "偽応答が端末に届く"}},
            "reason": {"a": {"ok": "何も出ない", "swapped": "device-role mismatch を含む理由が出る", "none_edge": "何も出ない"},
                       "d": ["Message unauthorized on port が出る"],
                       "why": {"ok": "GW ポートで落ちていない", "swapped": "DHCPv6 guard の理由文字列(実測)", "none_edge": "GW ポートで落ちていない"}},
            "fix": {"a": {"ok": "是正不要(意図どおり)",
                          "swapped": "{up_if} のポリシーを device-role server(または trusted-port)にする",
                          "none_edge": "{rog_if} に device-role client のポリシーを付ける"},
                    "d": ["{h1_if} のポリシーを外す"],
                    "why": {"ok": "正規は通り偽は落ちている", "swapped": "GW/リレー側は server", "none_edge": "端末側の全ポートに client を付ける"}},
            "acl_match": {"a": "match server access-list", "d": ["match ra prefix-list", "match ipv6 access-list"], "why": "サーバアドレスの検査は match server access-list。match ra prefix-list は RA guard"},
            "pref_chk": {"a": "preference min/max", "d": ["router-preference maximum", "hop-limit"], "why": "DHCPv6 の優先度は preference。router-preference は RA guard"},
        },
        "vars": {
            "pol_cli": ["DHG-CLIENT", "CLIENTS", "DH-EDGE"], "pol_srv": ["DHG-SERVER", "SERVERS", "DH-GW"],
            "acl": ["DHCP-SRV", "OK-DHCP", "SRV-ACL"], "srv_addr": ["FE80::1", "2001:DB8::53", "FE80::2"],
            "up_if": ["Ethernet0/0", "GigabitEthernet1/0/1", "GigabitEthernet0/1"],
            "h1_if": ["Ethernet0/1", "GigabitEthernet1/0/10", "GigabitEthernet0/2"],
            "h2_if": ["Ethernet0/2", "GigabitEthernet1/0/11", "GigabitEthernet0/3"],
            "rog_if": ["Ethernet0/3", "GigabitEthernet1/0/12", "GigabitEthernet0/4"],
        },
        "var_links": {"up_if": "h1_if", "h1_if": "h2_if", "h2_if": "rog_if"},
    },
    # ------------------------------------------------------------------ バインディングテーブル
    {
        "kind": "f_binding",
        "title": "バインディングテーブルの作られ方と読み方",
        "diagram": None,
        "exhibit": (
            "SW# show device-tracking database\n"
            "Binding Table has 4 entries, 4 dynamic\n"
            "Codes: L - Local, S - Static, ND - Neighbor Discovery, ARP - Address Resolution Protocol,\n"
            "       DH4 - IPv4 DHCP, DH6 - IPv6 DHCP, PKT - Other Packet, API - API created\n"
            "    Network Layer Address               Link Layer Address  Interface  vlan  age   state      Time left\n"
            "ND  2001:DB8:10::A8BB:CCFF:FE00:300     aabb.cc00.0300      Et0/2      10    12s   REACHABLE  288 s\n"
            "ND  FE80::A8BB:CCFF:FE00:300            aabb.cc00.0300      Et0/2      10    12s   REACHABLE  288 s\n"
            "DH6 2001:DB8:10::1A2B                   aabb.cc00.0200      Et0/1      10    40s   REACHABLE  260 s\n"
            "ND  FE80::A8BB:CCFF:FE00:200            aabb.cc00.0200      Et0/1      10    5s    REACHABLE  295 s\n"
        ),
        "text": (
            "バインディングテーブルは、リンク上の各端末について「IPv6 アドレス・MAC・«port»・VLAN・状態」を持つデータベースで、"
            "source guard や ND inspection など «consumers» がこれを引いて判定する。エントリは «nd_src» の NS/NA/RS/RA/Redirect を覗いて学ぶもの(Codes の ND)、"
            "DHCPv6 の IA_NA/IA_PD から学ぶもの(«dh6»)、`ipv6 neighbor binding` で手で入れるもの(S)に分かれる。"
            "上の出力では Et0/2 の端末は SLAAC で作った GUA とリンクローカルの 2 件が ND 由来、Et0/1 の端末の GUA は «dh6_mean» ことが読める。"
            "IOS XE 17.x では旧 `ipv6 snooping` コマンドは無く、この表を作る機能は «sisf» に統合され、"
            "`device-tracking policy` を作ってポートや VLAN に attach する。表を作る側の設定が無いと source guard は «no_table» ので、"
            "ガードの設定より先に表ができていることを確認する。エントリの状態は到達確認が取れていれば «reach» で、応答が無くなると STALE を経て消える。"
        ),
        "slots": {
            "port": {"a": "インターフェース(ポート)", "d": ["ルータ ID", "プレフィックス長"], "why": "どのポートの端末かが表の要"},
            "consumers": {"a": "表を参照する機能", "d": ["表を作る機能", "ルーティングプロトコル"], "why": "source guard/ND inspection は消費側"},
            "nd_src": {"a": "ND メッセージ", "d": ["データパケット", "LLDP"], "why": "Codes ND= ND スヌーピング由来"},
            "dh6": {"a": "DH6", "d": ["DH4", "PKT"], "why": "IPv6 DHCP 由来は DH6。DH4 は IPv4"},
            "dh6_mean": {"a": "DHCPv6 サーバから割り当てられた", "d": ["SLAAC で自動生成された", "静的に設定された"], "why": "Codes DH6"},
            "sisf": {"a": "SISF ベースの device-tracking", "d": ["IP source guard(IPv4)", "DHCP snooping(IPv4)"], "why": "17.x の FHS 基盤は SISF"},
            "no_table": {"a": "正当な端末の通信まで落とす", "d": ["すべて通してしまう", "エラーで設定できない"], "why": "表に無い送信元は拒否されるため、表が空だと全断"},
            "reach": {"a": "REACHABLE", "d": ["INCOMPLETE", "ESTABLISHED"], "why": "到達確認済みは REACHABLE"},
        },
    },
    # ------------------------------------------------------------------ ND inspection / snooping
    {
        "kind": "f_ndinsp",
        "title": "ND inspection(スヌーピング)の役割と security-level",
        "diagram": None,
        "exhibit": (
            "device-tracking policy {pol}\n"
            " ! security-level は既定のまま(show running-config には表示されない)\n"
            " device-role node\n"
            " limit address-count {limit}\n"
            "!\n"
            "vlan configuration {vlan}\n"
            " device-tracking attach-policy {pol}\n"
        ),
        "text": (
            "ND inspection(旧 IPv6 snooping・17.x では device-tracking)は、ポートを通る ND メッセージを見て "
            "«learn» を学習し、同時に「主張している IPv6 アドレスと MAC の対応」が表と «verify» ND メッセージを破棄する。"
            "これにより、他の端末のアドレスを名乗る NA で通信を横取りする «attack» を止められる。"
            "ポリシーの security-level は 3 段階で、«glean» は学習だけ、«guard»(既定)は学習して違反を破棄、inspect は学習して違反を記録する。"
            "既定値は show running-config に出ないので、実際の値は `show device-tracking policies` や `show device-tracking policy <名前>` で確認する。"
            "`limit address-count` は 1 ポートあたりの登録アドレス数の上限で、大量のアドレスを名乗って表を溢れさせる «dos» を抑える。"
            "この機能は表を作る側なので、RA/DHCPv6 の各ガードとは違い、単独では偽 RA や偽 DHCPv6 応答を «no_block»。"
        ),
        "slots": {
            "learn": {"a": "IPv6 アドレスと MAC とポートの対応(束縛)", "d": ["ルーティング情報", "VLAN の割り当て"], "why": "学ぶのは束縛(binding)"},
            "verify": {"a": "食い違う", "d": ["一致する", "重複しない"], "why": "表と矛盾する主張を捨てる"},
            "attack": {"a": "ND スプーフィング(中間者)", "d": ["偽 RA によるゲートウェイ乗っ取り", "DHCPv6 枯渇"], "why": "NA 偽装は ND inspection の守備範囲"},
            "glean": {"a": "glean", "d": ["guard", "inspect"], "why": "glean= 学習のみ"},
            "guard": {"a": "guard", "d": ["glean", "inspect"], "why": "guard= 学習+破棄(既定)"},
            "dos": {"a": "表の枯渇(DoS)", "d": ["ブロードキャストストーム", "ループ"], "why": "address-count の上限は表の DoS 対策"},
            "no_block": {"a": "止められない", "d": ["止められる", "記録だけする"], "why": "偽 RA/DHCPv6 応答はそれぞれ RA guard/DHCPv6 guard の担当"},
        },
        "vars": {"pol": ["TRACK", "SNOOP-VLAN", "DT-ACCESS"], "limit": ["10", "4", "16"], "vlan": ["10", "20", "30"]},
    },
    # ------------------------------------------------------------------ source guard
    {
        "kind": "f_srcguard",
        "title": "IPv6 source guard の前提と動作",
        "diagram": None,
        "exhibit": (
            "ipv6 source-guard policy {pol}\n"
            " «permit_ll»\n"
            " «deny_auto»\n"
            "!\n"
            "interface {h1_if}\n"
            " ipv6 source-guard attach-policy {pol}\n"
        ),
        "text": (
            "IPv6 source guard は、ポートに入ってきた «target» の送信元アドレスがバインディングテーブルに «cond» 場合にそのパケットを破棄する。"
            "ND や DHCPv6 のメッセージ自体は検査しない。表は ND inspection や DHCPv6 のグリーニングが作るので、それらが無いと "
            "«prereq»。拒否が起きたとき、スイッチは正当な端末の見落としを避けるために、«recover» によって束縛の復元を試みる。"
            "ポリシーには「リンクローカル送信元は表に無くても通す」指定や、"
            "«deny_auto_mean» を意味する指定を副コマンドとして書ける(上の設定例)。"
            "同じ枠組みで送信元の「プレフィックス」がこのリンクに正当かを検査するのが «prefix_guard» で、RA や DHCPv6 PD から学んだプレフィックスの範囲外を落とす。"
            "IPv4 の «v4_equiv» に相当する機能と考えると位置づけが分かりやすい。"
        ),
        "slots": {
            "target": {"a": "データパケット", "d": ["ND メッセージ", "DHCPv6 メッセージ"], "why": "source guard の対象はデータ。ND/DHCP は見ない"},
            "cond": {"a": "載っていない", "d": ["載っている", "重複している"], "why": "表に無い送信元を拒否"},
            "prereq": {"a": "正当な端末も全部落ちる", "d": ["何も落ちない", "自動で表が作られる"], "why": "表が空= 全拒否"},
            "recover": {"a": "DHCP サーバへの照会または ND", "d": ["RA の再送要求", "MAC テーブルの参照"], "why": "復元は DHCP 照会か ND(公式記述)"},
            "deny_auto_mean": {"a": "SLAAC で自動生成した GUA を送信元とするパケットを拒否する", "d": ["DHCPv6 で得た GUA を拒否する", "リンクローカルを拒否する"], "why": "global-autoconf= 自動設定のグローバルアドレス"},
            "prefix_guard": {"a": "IPv6 prefix guard", "d": ["IPv6 destination guard", "RA guard"], "why": "プレフィックスの妥当性は prefix guard(source guard の中で動く)"},
            "v4_equiv": {"a": "IP Source Guard(DHCP snooping 連携)", "d": ["DAI(Dynamic ARP Inspection)", "uRPF"], "why": "IPv4 で送信元を束縛表で検証するのは IP Source Guard。DAI は ARP 検査(= ND inspection 相当)"},
            "permit_ll": {"a": "permit link-local", "d": ["permit global", "trusted-port"], "why": "リンクローカルを通す副コマンド"},
            "deny_auto": {"a": "deny global-autoconf", "d": ["deny link-local", "deny dhcp"], "why": "自動設定 GUA を拒否する副コマンド"},
        },
        "vars": {"pol": ["SRCG", "SG-HOSTS", "SRC-EDGE"], "h1_if": ["Ethernet0/1", "GigabitEthernet1/0/10", "GigabitEthernet0/2"]},
    },
    # ------------------------------------------------------------------ 展開の流れ(どのポートに何を)
    {
        "kind": "f_deploy",
        "title": "アクセススイッチへの FHS 展開と確認の流れ",
        "diagram": DIAG_ACCESS,
        "exhibit": None,
        "text": (
            "FHS を入れる順序は「表を作る→制御メッセージを守る→データを守る」である。まず «step1» のポリシーを VLAN に付けてバインディングテーブルを育て、"
            "`show device-tracking database` に端末が載ることを確認する。次に RA guard と DHCPv6 guard を入れるが、役割の付け方は"
            "GW 側 {up_if} に «up_roles»、端末側 {h1_if}〜{rog_if} に «edge_roles» である。最後に、端末側だけに source guard を付ける。"
            "投入後の確認は、ポリシーの中身が `show ipv6 nd raguard policy` と `show ipv6 dhcp guard policy` と `show device-tracking policies`、"
            "実際に何が落ちたかは «counters» で見る。端末側の症状から逆引きすると、「GUA が付かずリンクローカルだけ」なら «sym_ll»、"
            "「GW もアドレスも正常だが DNS が取れない」なら «sym_dns» を疑う。"
            "一連の設定は show running-config では既定値が省かれるので、«verify_by» を正とする。"
        ),
        "slots": {
            "step1": {"a": "device-tracking(snooping)", "d": ["source guard", "RA guard"], "why": "最初に表を作る"},
            "up_roles": {"a": "router と server", "d": ["host と client", "router と client"], "why": "GW/リレー側は RA guard=router・DHCPv6 guard=server"},
            "edge_roles": {"a": "host と client", "d": ["router と server", "host と server"], "why": "端末側は host・client"},
            "counters": {"a": "show device-tracking counters interface", "d": ["show ipv6 neighbors", "show logging"], "why": "Dropped と理由文字列はカウンタで見る"},
            "sym_ll": {"a": "正規 GW の RA が RA guard で落ちている", "d": ["DHCPv6 guard の role 誤り", "source guard の表が空"], "why": "RA が届かないと SLAAC の GUA も既定 GW も無い"},
            "sym_dns": {"a": "GW ポートの DHCPv6 guard が client になっている", "d": ["RA guard の VLAN 適用", "prefix-list の誤り"], "why": "RA は通り DHCPv6 応答だけ落ちる(実測)"},
            "verify_by": {"a": "show の policy 表示", "d": ["show running-config", "show startup-config"], "why": "既定値(device-role host/security-level guard)は running-config に出ない"},
        },
        "vars": {
            "up_if": ["Ethernet0/0", "GigabitEthernet1/0/1"],
            "h1_if": ["Ethernet0/1", "GigabitEthernet1/0/10"],
            "h2_if": ["Ethernet0/2", "GigabitEthernet1/0/11"],
            "rog_if": ["Ethernet0/3", "GigabitEthernet1/0/12"],
        },
        "var_links": {"up_if": "h1_if", "h1_if": "h2_if", "h2_if": "rog_if"},
    },
    # ------------------------------------------------------------------ カウンタの読解
    {
        "kind": "f_counters",
        "title": "Dropped カウンタの理由から原因を読む",
        "diagram": DIAG_ACCESS,
        "worlds": ["role", "pref", "ok"],
        "world_desc": {"role": "GW ポートで RA が unauthorized on port で落ちている(host 扱い)",
                       "pref": "GW ポートで RA が Preference flag error で落ちている(上限が低い)",
                       "ok": "GW ポートでは何も落ちていない(正常)"},
        "exhibit": {
            "role": (
                "SW# show device-tracking counters interface {up_if}\n"
                "Received messages on {up_if}:\n  Protocol  Protocol message\n  NDP       RS[12] RA[40] NS[8] NA[8]\n"
                "Dropped messages on {up_if}:\n  Feature     Protocol Msg [Total dropped]\n  RA guard    NDP      RA  [40]\n"
                "     reason: Message unauthorized on port [40]\n\n"
                "SW# show device-tracking counters interface {rog_if}\n"
                "Dropped messages on {rog_if}:\n  Feature     Protocol Msg [Total dropped]\n  RA guard    NDP      RA  [15]\n"
                "     reason: Message unauthorized on port [15]\n  DHCP Guard  DHCPv6   REP [6]\n"
                "     reason: Message type is not authorized by the policy on this port, device-role mismatch [6]\n"
            ),
            "pref": (
                "SW# show device-tracking counters interface {up_if}\n"
                "Received messages on {up_if}:\n  Protocol  Protocol message\n  NDP       RS[12] RA[40] NS[8] NA[8]\n"
                "Dropped messages on {up_if}:\n  Feature     Protocol Msg [Total dropped]\n  RA guard    NDP      RA  [40]\n"
                "     reason: Preference flag error [40]\n\n"
                "SW# show device-tracking counters interface {rog_if}\n"
                "Dropped messages on {rog_if}:\n  Feature     Protocol Msg [Total dropped]\n  RA guard    NDP      RA  [15]\n"
                "     reason: Preference flag error [15]\n  DHCP Guard  DHCPv6   REP [6]\n"
                "     reason: Message type is not authorized by the policy on this port, device-role mismatch [6]\n"
            ),
            "ok": (
                "SW# show device-tracking counters interface {up_if}\n"
                "Received messages on {up_if}:\n  Protocol  Protocol message\n  NDP       RS[12] RA[40] NS[8] NA[8]\n"
                "Dropped messages on {up_if}:\n  (none)\n\n"
                "SW# show device-tracking counters interface {rog_if}\n"
                "Dropped messages on {rog_if}:\n  Feature     Protocol Msg [Total dropped]\n  RA guard    NDP      RA  [15]\n"
                "     reason: Message unauthorized on port [15]\n  DHCP Guard  DHCPv6   REP [6]\n"
                "     reason: Message type is not authorized by the policy on this port, device-role mismatch [6]\n"
            ),
        },
        "text": (
            "上は GW がつながる {up_if} と、不正端末がつながる {rog_if} のカウンタである。{rog_if} 側は «rog_side»。"
            "{up_if} 側の Dropped から読める状態は «cause» で、是正は «fix»。このとき端末は «host_state»。"
            "RA guard で落ちる理由は大きく 2 つあり、「Message unauthorized on port」は «mean_unauth»、「Preference flag error」は «mean_pref» を意味する。"
            "端末側の症状はどちらも同じなので、見分けるのは «distinguish» である。"
        ),
        "slots": {
            "rog_side": {"a": "意図どおり(不正 RA と偽 REPLY が落ちている)", "d": ["守り過ぎ(正規の応答まで落ちている)", "無防備(何も落ちていない)"], "why": "不正端末側で RA と REP が落ちるのは正常動作"},
            "cause": {"a": {"role": "GW ポートが host 扱い(host を付けた、または VLAN の host だけが効いている)",
                            "pref": "router-preference maximum が正規 GW の優先度より低い",
                            "ok": "問題なし(GW の RA は落ちていない)"},
                      "d": ["DHCPv6 guard の role 誤り"],
                      "why": {"role": "unauthorized on port= そのポートでは RA 自体が認められていない",
                              "pref": "Preference flag error= 上限超過(実測)", "ok": "Dropped が無い"}},
            "fix": {"a": {"role": "{up_if} にポート側で device-role router(または trusted-port)のポリシーを付ける",
                          "pref": "router-preference maximum を正規 GW の優先度以上にする(または role 方式にする)",
                          "ok": "是正不要"},
                    "d": ["{rog_if} のポリシーを外す"],
                    "why": {"role": "ポート > VLAN で上書きできる", "pref": "上限 medium なら正規(medium)は通る(実測)", "ok": "正常"}},
            "host_state": {"a": {"role": "リンクローカルだけで GUA も既定 GW も無い", "pref": "リンクローカルだけで GUA も既定 GW も無い", "ok": "GUA と既定 GW を正常に得る"},
                           "d": ["GUA はあるが DNS が無い"], "why": "RA が届くかどうかで決まる"},
            "mean_unauth": {"a": "そのポート(の役割)では RA を受け付けない", "d": ["RA の優先度が上限を超えた", "prefix-list に無いプレフィックスだった"], "why": "host 扱いのポートで RA を受けた"},
            "mean_pref": {"a": "RA の優先度が上限を超えた", "d": ["そのポート(の役割)では RA を受け付けない", "ホップリミットが範囲外だった"], "why": "router-preference maximum 超過"},
            "distinguish": {"a": "Dropped の理由文字列", "d": ["show running-config", "端末の ping 結果"], "why": "理由が違えば是正も違う"},
        },
        "vars": {"up_if": ["Ethernet0/0", "GigabitEthernet1/0/1"], "h1_if": ["Ethernet0/1", "GigabitEthernet1/0/10"],
                 "h2_if": ["Ethernet0/2", "GigabitEthernet1/0/11"], "rog_if": ["Ethernet0/3", "GigabitEthernet1/0/12"]},
        "var_links": {"up_if": "h1_if", "h1_if": "h2_if", "h2_if": "rog_if"},
    },
    # ------------------------------------------------------------------ 範囲外: destination guard / RFC 7113
    {
        "kind": "f_beyond",
        "scope": "beyond",   # ★ENARSI 範囲外(ブループリントの列挙に無い)= 既定の出題から外す
        "title": "destination guard と RA guard の回避手口(範囲外)",
        "diagram": None,
        "exhibit": None,
        "text": (
            "ブループリントに列挙されない機能として «destguard» がある。これはバインディングテーブルに «dest_cond» 宛先へのパケットをルータが解決(NS 送信)せずに捨てるもので、"
            "存在しないアドレスを大量に叩いて ND キャッシュを溢れさせる «nd_dos» を防ぐ。"
            "また RA guard には既知の回避手口があり、RA を «frag» に分割したり拡張ヘッダを重ねると、L2 スイッチが ICMPv6 ヘッダまで解析できず素通りすることがある。"
            "RFC 7113 はこれに対し、断片化された ND メッセージを «rfc7113» ことを推奨している。"
        ),
        "slots": {
            "destguard": {"a": "IPv6 destination guard", "d": ["IPv6 prefix guard", "IPv6 source guard"], "why": "宛先側の検査は destination guard"},
            "dest_cond": {"a": "載っていない", "d": ["載っている", "期限切れの"], "why": "表に無い宛先は解決しない"},
            "nd_dos": {"a": "ND キャッシュ枯渇攻撃", "d": ["RA フラッド", "DAD DoS"], "why": "解決を誘発する攻撃を止める"},
            "frag": {"a": "フラグメント", "d": ["ジャンボフレーム", "VLAN タグ"], "why": "断片化で上位ヘッダを隠す手口"},
            "rfc7113": {"a": "破棄する", "d": ["再組立てして検査する", "ログだけ取る"], "why": "RFC 7113 の勧告は断片化 ND の破棄"},
        },
    },
]
