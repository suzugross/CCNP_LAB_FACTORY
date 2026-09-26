# U-F1 / U-F2 マルチキャスト — 出典照合表(ソース検証マトリクス)

対象: [U-F-mcast.md](U-F-mcast.md) の知識項目 41 件。照合日 2026-09-22。
実機欄はすべて未実測(本表作成時点で IOL の実測なし)。実測の盤面は `problems/_POC-MCAST`(BL-217 PoC・IOL 8 台＋ioll2 1 台)を想定し、
「実機で裏どりが必要な論点」の M 番号に RT 名で確認手順を書いた。

**凡例**
- 出典欄: ○= 一致 / △= 表現差・一部のみ記載・版や機種の差 / ×= 相違 / —= 未記載。続けて出典キー(下表)と要旨・原文の短い引用。
- 引用の表記: 「」= 本文をテキストで取得して grep した**原文**(cisco.com は直接取得が 403 のため Wayback Machine の保存版、RFC は rfc-editor.org、
  ネットワークエンジニアとして はページを取得して grep)。〔要旨〕= WebFetch/WebSearch の要約経由で読んだもの(**原文ではない**。言い回しを出題の根拠にしない)。
- 実機欄: 要実測 / 不要(概念)。
- 判定: **確定**(出題に使ってよい) / **要実測**(IOL/ioll2 で確かめてから出題) / **要ユーザ判断**(出典どうしが割れている・出題上の扱いを決める必要)。

## 出典キー

### Cisco 公式

| キー | 文書 | URL | 取得方法 |
|---|---|---|---|
| C-OVW | IP Multicast: PIM Config Guide IOS XE 16.9 — IP Multicast Technology Overview | https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipmulti_pim/configuration/xe-16-9/imc-pim-xe-16-9-book/imc-tech-oview.html | Wayback 全文 |
| C-CR-S | Cisco IOS IP Multicast Command Reference — show ip dvmrp route through show ip sdr(`show ip mroute` の Field Descriptions 表を含む) | https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipmulti/command/imc-cr-book/imc_s1.html | Wayback 全文 |
| C-CR-IGMP | 同 Command Reference — ip igmp access-group through ip igmp v3lite | https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipmulti/command/imc-cr-book/imc_i1.html | Wayback 全文 |
| C-CR-MR | 同 Command Reference — ip mfib through ip multicast-routing(`ip mroute`・`ip msdp`・`ip multicast boundary`・`ip multicast multipath`・`ip multicast-routing`) | https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipmulti/command/imc-cr-book/imc_i2.html | Wayback 全文 |
| C-CR-PIM | 同 Command Reference — ip pgm host through ip pim version(`ip pim ...` 全般) | https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipmulti/command/imc-cr-book/imc_i3.html | Wayback 全文 |
| C-BASIC | IP Multicast Configuration Guide, IOS XE 17.x — Configuring Basic IP Multicast | https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-multicast/b-ip-multicast/m_imc_basic_cfg-0.html | WebFetch〔要旨〕 |
| C-C9K-IGMP | Catalyst 9300 IP Multicast Routing CG IOS XE 17.12 / 17.15 — Configuring IGMP(IGMP snooping を含む) | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/configuration_guide/ip_mcast_rtng/b_1715_ip_mcast_rtng_9300_cg/configuring_igmp.html | WebFetch〔要旨〕 |
| C-C9K-PIM | Catalyst 9300 IP Multicast Routing CG IOS XE 17.15 — Configuring PIM | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/configuration_guide/ip_mcast_rtng/b_1715_ip_mcast_rtng_9300_cg/configuring_pim.html | WebFetch〔要旨〕 |
| C-C9K-SSM | Catalyst 9300 IP Multicast Routing CG IOS XE 17.15 — Configuring SSM | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/configuration_guide/ip_mcast_rtng/b_1715_ip_mcast_rtng_9300_cg/configuring_ssm.html | WebFetch〔要旨〕 |
| C-PIMSNOOP | Catalyst 9500 IP Multicast Routing CG IOS XE 17.14 — Configuring PIM Snooping | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/17-14/configuration_guide/ip_mcast_rtng/b_1714_ip_mcast_rtng_9500_cg/configuing_pim_snooping.html | WebSearch〔要旨〕 |
| C-MSDP | IP Multicast Configuration Guide, IOS XE 17.x — Using MSDP to Interconnect Multiple PIM-SM Domains / Cat9400 17.15 Configuring MSDP | https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-multicast/b-ip-multicast/m_imc_msdp_im_pim_sim.html | WebSearch〔要旨〕 |
| C-V6ANY | IP Multicast Configuration Guide, IOS XE 17.x — PIMv6 Anycast RP Solution | https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-multicast/b-ip-multicast/m_ip6-pimv6-anycast-rp-xe.html | WebFetch〔要旨〕 |
| C-MLD | IP Multicast Configuration Guide, IOS XE 17.x — IPv6 Multicast Listener Discovery Protocol | https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-multicast/b-ip-multicast/m_ipv6-mcast-mld-xe.html | WebFetch〔要旨〕 |
| C-ECMP | IP Multicast Configuration Guide, IOS XE 17.x — IP Multicast Load Splitting across Equal-Cost Paths | https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-multicast/b-ip-multicast/m_imc_load_splt_ecmp-0.html | WebSearch〔要旨〕 |
| C-ALLOC | White paper: Guidelines for Enterprise IP Multicast Address Allocation | https://www.cisco.com/c/dam/en/us/support/docs/ip/ip-multicast/ipmlt_wp.pdf | WebSearch〔要旨〕 |
| C-ASSERT | Tech note: Understand the PIM Assert Mechanism (212595) | https://www.cisco.com/c/en/us/support/docs/ip/ip-multicast/212595-how-well-do-you-know-pim-assert-mechanis.html | WebSearch〔要旨〕 |
| C-JOIN | Tech note: Cisco IOS "ip igmp join-group" and "ip igmp static-group" Command Use (119383) | https://www.cisco.com/c/en/us/support/docs/ip/ip-multicast/119383-technote-ip-multicast-00.html | Wayback 全文 |
| C-TSG | Tech note: Troubleshoot IP Multicast Guide (16450) | https://www.cisco.com/c/en/us/support/docs/ip/ip-multicast/16450-mcastguide0.html | Wayback 全文 |
| C-CLI | Tech note: Troubleshoot Multicast Networks with CLI Tools (13726-57) | https://www.cisco.com/c/en/us/support/docs/ip/ip-multicast/13726-57.html | Wayback 全文 |
| C-RPENG | White paper: Configuring a Rendezvous Point(rps.html) | https://www.cisco.com/c/en/us/td/docs/ios/solutions_docs/ip_multicast/White_papers/rps.html | Wayback 全文 |
| C-AUTORP-MIX | Tech note: PIM Auto-RP Behavior with Other RP Distribution Techniques in SM Domain(118405) | https://www.cisco.com/c/en/us/support/docs/ip/multicast/118405-config-rp-00.html | WebFetch〔要旨〕 |

### RFC(Cisco と解説サイトが割れた時の裁定用)

| キー | 文書 |
|---|---|
| R-2236 | RFC 2236 IGMPv2(Leave は all-routers 224.0.0.2・Query Interval 既定 **125 秒**・Query Response Interval 100=10 秒) |
| R-3376 | RFC 3376 IGMPv3(Report 宛先 224.0.0.22) |
| R-3810 | RFC 3810 MLDv2(Report Type=143・宛先 FF02::16) |
| R-4607 | RFC 4607 SSM(232/8) |
| R-4610 | RFC 4610 Anycast-RP Using PIM(MSDP 不要) |
| R-3618 | RFC 3618 MSDP(TCP 639・IP の大きい側が listen) |
| R-5015 | RFC 5015 Bidir-PIM(DF 選出・RP ごと/リンクごと) |
| R-5059 | RFC 5059 BSR(C-BSR は大きい priority 優先・C-RP は小さい priority 優先) |
| R-7761 | RFC 7761 PIM-SM(Hello_Period 30 秒・Default_Hello_Holdtime 3.5×=**105 秒**・t_periodic 60 秒・J/P Holdtime 3.5×t_periodic=210 秒・Keepalive_Period 210 秒・Assert 比較順) |

### ネットワークエンジニアとして(www.infraexpert.com/study/)

| キー | ページ |
|---|---|
| J-z01 | multicastz01.html マルチキャストとは |
| J-z03 | multicastz03.html マルチキャスト IP アドレス(スコープ 3 分類・予約アドレス表) |
| J-z04 | multicastz04.html マルチキャスト MAC アドレス(01-00-5E・下位 23 ビット・32 対 1) |
| J-z08〜z11 | multicastz08〜11.html IGMP とは / IGMPv1 / IGMPv2 / IGMPv3 |
| J-z12 | multicastz12.html IGMP スヌーピング |
| J-z13・z14 | multicastz13・14.html ディストリビューションツリー / Dense・Sparse |
| J-z15 | multicastz15.html RPF チェック(等コスト時の RPF インターフェース) |
| J-z16〜z23 | multicastz16〜23.html PIM-DM(DR・フラグ・Assert・State Refresh) |
| J-z24〜z32 | multicastz24〜32.html PIM-SM(DR・(*,G)/(S,G)・スイッチオーバー・フラグ・エントリ削除) |
| J-z33〜z35 | multicastz33〜35.html Auto-RP その 1〜3 |
| J-z36・z37 | multicastz36・37.html BSR その 1・2 |
| J-z38・z39 | multicastz38・39.html Bidir-PIM |
| J-z40 | multicastz40.html SSM |
| J-z41 | multicastz41.html Anycast RP・MSDP |
| J-z42〜z46 | multicastz42〜46.html IPv6 マルチキャスト / MLD / MLDv1 / MLDv2 / IPv6 PIM |
| J-z49 | multicastz49.html PIM スヌーピング |
| J-y02・y03 | multicasty02・03.html Cisco 設定 PIM-SM スタティック RP その 1・2 |
| J-y04・y05 | multicasty04・05.html Cisco 設定 Auto-RP その 1・2(rp-announce-filter・boundary) |
| J-y06・y07 | multicasty06・07.html Cisco 設定 BSR その 1・2 |
| J-y08・y09 | multicasty08・09.html Cisco 設定 IGMP その 1・2(既定値表・join/static・ip igmp profile/filter) |
| J-y10 | multicasty10.html Cisco 設定 IGMP スヌーピング(既定値表・mrouter 学習) |
| J-y11 | multicasty11.html Cisco 設定 RPF インターフェース(ip mroute) |
| J-y12〜y14 | multicasty12〜14.html Cisco 設定 Bidir-PIM / SSM / Anycast RP・MSDP |
| J-y15 | multicasty15.html ip multicast ttl-threshold / boundary |
| J-y20 | multicasty20.html IPv6 マルチキャストルーティングの設定 |

## 1. 基礎

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 1 | 1 対多・送信元は 1 回送るだけ・受信者の集合= グループ | ○ C-OVW: グループアドレス宛てに送り、参加した全ホストが受信。「The source address for multicast datagrams is always the unicast source address」 | ○ J-z01: 「1対複数」「送信するパケットは1つでよい」/ J-z03: 送信元はユニキャストアドレス | 不要(概念) | 確定 |
| 2 | 224.0.0.0/4(クラス D)・224.0.0.0/24 リンクローカル(TTL 1)・232/8 SSM・239/8 組織内 | ○ C-OVW Table 1: Link-Local 224.0.0.0–224.0.0.255「not forwarded by IP routers」「typically sent with a time-to-live (TTL) value of 1」/ Globally Scoped 224.0.1.0–238.255.255.255 / SSM 232/8 / GLOP 233/8 / Limited Scope 239/8 | ○ J-z03: リンクローカル 224.0.0.0〜224.0.0.255(TTL 1)・グローバル 224.0.1.0〜238.255.255.255・プライベート 239/8。△ 232/8 はアドレスのページに無く J-z40(SSM)にだけ記載・GLOP の記述なし | 不要(概念) | 確定 |
| 3 | 224.0.0.1 全ホスト・224.0.0.2 全ルータ・224.0.0.13 全 PIM ルータ・224.0.0.22 IGMPv3 | ○ C-CR-PIM(bsr-candidate):「ALL-PIM-ROUTERS group address, 224.0.0.13」/ C-C9K-IGMP〔要旨〕: v3 Report は 224.0.0.22・v2 Leave は 224.0.0.2 / C-CLI の debug: `Send v2 Query ... to 224.0.0.1` | △ J-z03 の予約表に 224.0.0.1/.2/.13 あり。**224.0.0.22 はどのページにも無い**(J-z11 IGMPv3 にも宛先の記述なし) | 不要(概念) | 確定(224.0.0.22 の根拠は Cisco と R-3376) |
| 4 | 01:00:5E + IP 下位 23 ビット → 32 個の IP が 1 つの MAC | ○ C-ALLOC〔要旨〕: 接頭辞 0x0100.5E・23 ビット・5 ビットが失われ 32 グループが同じ MAC | ○ J-z04: 先頭 25 ビット固定(01-00-5E+0)・下位 23 ビット・224.10.1.1 と 224.138.1.1 が同じ MAC・「32対1」 | 不要(概念) | 確定 |
| 5 | SPT((S,G))と RPT((*,G)・根は RP) | ○ C-OVW: 「Shared trees are (*,G) and the source trees are (S,G)」・source tree= SPT・shared tree の root= RP | ○ J-z13: 送信元ツリー= SPT=(S,G)・共有ツリー= RP 中心 (*,G) | 不要(概念) | 確定 |
| 6 | IGMP(ホスト⇄ルータ)・PIM(ルータ間) | ○ C-OVW: IGMP は「IP routers and their immediately connected hosts」・PIM はルータ間 | ○ J-z08: IGMP は Receiver とラストホップルータ間 / J-z07: ルータ間は PIM | 不要(概念) | 確定 |

## 2. IGMP

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 7 | IGMPv2: Report・Leave(224.0.0.2)・General Query(224.0.0.1)/ Group-Specific Query | ○ C-C9K-IGMP〔要旨〕: v2 で leave・group-specific query・最大応答時間を追加。Leave は 224.0.0.2(ただし説明が「all devices on a subnet」で語が不正確→ D12)/ R-2236: Leave は all-routers 224.0.0.2 | ○ J-z10: Leave は 224.0.0.2・General Query は 224.0.0.1・Type 0x11/0x16/0x17。△ 参加の段落で「type 0x2」と v1 の値を書いている(v2 Report は 0x16) | 不要(概念) | 確定 |
| 8 | IGMPv2 querier= 最小 IP(PIM DR の最大 IP と逆) | ○ C-CR-IGMP(querier-timeout):「The router with the lowest IP address on the subnet is elected the IGMP querier.」/ C-C9K-IGMP 同旨 | ○ J-z10: 「最も小さいIPアドレスを持つルータがIGMPクエリア」 | 要実測(RT04/RT08 の受信 LAN で querier と DR が別ルータになることを表示で確認・M4) | 確定(表示は要実測) |
| 9 | Query 間隔 既定 60 秒(IOS)・last member query で離脱確認 | ○ C-CR-IGMP:「The IGMP query interval is 60 seconds.」・last-member-query-interval 既定「1000 milliseconds」・LMQC「2」・query-max-response-time「10 seconds」。× querier-timeout は「two times the IGMP query interval」(=120 秒)で、C-C9K-IGMP の既定表〔要旨〕「Query timeout: 60 seconds」と食い違う(D1)/ R-2236: Query Interval 既定 **125 秒**(IOS の 60 は RFC 既定と違う・D2) | ○ J-z09/z10/y08: 60 秒・最大応答 10 秒・Group-Specific Query の再送は最大 2 回 / × J-y08: 「クエリーのタイムアウト値 60秒」(Cisco CR は 120 秒) | 要実測(`show ip igmp interface` の各行・M2) | 確定(60 秒・10 秒・LMQ 1000ms×2)。querier timeout の値は**要実測**(D1) |
| 10 | IGMPv3: INCLUDE/EXCLUDE・Report 宛先 224.0.0.22・SSM に必須 | ○ C-C9K-IGMP〔要旨〕: 「IGMPv3 membership reports are destined to the address 224.0.0.22」/ C-OVW: SSM では「must use IGMP Version 3 (IGMPv3)」/ R-3376 | △ J-z11: INCLUDE/EXCLUDE・ソースフィルタ ○、Report Type 0x22 ○、**宛先 224.0.0.22 は記載なし** / J-z40: SSM は IGMPv3(INCLUDE のみ)・代替に IGMPv3 lite・URD | 要実測(`ip igmp version 3` と `ip igmp join-group 232.x.x.x source S` で (S,G) が立つか・M9) | 確定 |
| 11 | `join-group`= ルータ自身が参加し ping に応答 / `static-group`= 転送だけ | ○ C-CR-IGMP(join-group):「the router accepts the multicast packets in addition to forwarding them」/(static-group)「packets to the group are fast-switched out the interface」/ C-JOIN: join-group は CPU へ punt・L フラグ・MFIB で IC フラグ | ○ J-y08: 表(join-group= 転送○受信○Report 送信○ / static-group= 転送○のみ)・join-group は ICMP エコーに応答 | 要実測(L フラグの有無・group 宛 ping の応答・M21) | 確定 |
| 12 | `show ip igmp groups` / `show ip igmp interface`(バージョン・querier・タイマ) | △ C-CR-IGMP: コマンド自体は掲載(出力の全行はここでは未照合) | ○ J-y08: 両コマンドの用途 / J-z10: `show ip igmp groups` の出力例(Group Address・Interface・Uptime・Expires・Last Reporter) | 要実測(出力書式を取得・M2) | 確定(書式は要実測) |

## 3. L2 マルチキャスト

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 13 | IGMP snooping(既定で有効)・mrouter port | ○ C-C9K-IGMP〔要旨〕既定表: IGMP snooping「Enabled globally and per VLAN」・Multicast routers「None configured」・Immediate Leave「Disabled」・TCN flood query count「2」・report suppression「Enabled」。mrouter 学習= IGMP query・PIM パケットのスヌーピング+静的 / C-CR-IGMP:「IGMP snooping is enabled globally.」 | ○ J-y10: 既定表(グローバル・VLAN 単位で有効・mrouter 学習 PIM-DVMRP・即時脱退無効・レポート抑制有効)。△ mrouter 学習に DVMRP・CGMP を挙げる(旧 Catalyst の記述。C9K 17.x は IGMP query と PIM) / J-z12: 仕組み | 要実測(ioll2 で既定有効か・`show ip igmp snooping mrouter`・M18) | 確定(Catalyst の既定)。ioll2 の挙動は要実測 |
| 14 | snooping querier= ルータの無い VLAN で Query を代行 | ○ C-C9K-IGMP〔要旨〕: 既定 Disabled・「IGMP Versions 1 and 2」をサポート・マルチキャストルータの無いサブネットで snooping を働かせる / C-CR-IGMP(snooping querier): 既定 Disabled・VLAN の IP を送信元に使い、IP が無いと起動しない(7600 系の記述) | △ J-y10: 既定ディセーブル・`show ip igmp snooping querier` のみ(目的・動作の説明なし) | 要実測(ioll2 でコマンドがあるか・M18) | 確定(概念)。ラボ化は要実測 |
| 15 | IGMP filter(`ip igmp profile` + `ip igmp filter`) | ○ C-C9K-IGMP〔要旨〕: profile は permit/deny と group range・「only to Layer 2 access ports」・ルーテッドポート・SVI・EtherChannel 所属ポートには不可 | ○ J-y09: `ip igmp profile N`→`permit` / `deny`→`range`→IF で `ip igmp filter N`・物理 IF のみ(SVI・L3・EtherChannel 不可)・方向指定なしで着信 IGMP に適用 / ルータ側は `ip igmp access-group` | 要実測(ioll2 で受理されるか・M18) | 確定(構文)。IOL 可否は要実測 |
| 16 | PIM snooping= ルータが並ぶ VLAN で Join を覗いて転送を絞る | ○ C-PIMSNOOP〔要旨〕: 既定無効・IGMP snooping が前提・IP/PIM 設定不要・Hello/Join/Prune/bidir DF 選出を覗く・VLAN 単位・既定で DR へは flood(`no ip pim snooping dr-flood`) | ○ J-z49: 同内容(既定ディセーブル・IGMP スヌーピング必須・interface vlan で有効化・dr-flood) | 要実測(ioll2 にあるか・M19) | 確定(概念)。ラボ化は要実測 |
| 17 | MLD= IPv6 版 IGMP(MLDv1≒IGMPv2・MLDv2≒IGMPv3)・ICMPv6 | ○ C-MLD〔要旨〕: 「MLD version 1 is based on version 2 of the Internet Group Management Protocol (IGMP)」「MLD version 2 is based on version 3」「MLD uses the Internet Control Message Protocol (ICMP) to carry its messages」・link-local・hop limit 1。— Type 番号・FF02::16 の記載なし | ○ J-z42/z43: MLDv1=IGMPv2・MLDv2=IGMPv3 相当・ICMPv6 Type 130/131/132/143 / J-z44/z45: Done は FF02::2・MLDv2 Report は FF02::16 / J-y20: `ipv6 multicast-routing` で PIM と MLDv2 が自動有効 | 不要(概念)。IPv6 側のラボは任意(M20) | 確定(Type 番号・FF02::16 は R-3810 で裏どり済) |

## 4. PIM-SM

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 18 | ユニキャスト経路に依存・Hello は 224.0.0.13・既定 30 秒 | ○ C-OVW: 「PIM is not dependent on a specific unicast routing protocol」/ C-CR-PIM(query-interval):「PIM hello (query) messages are sent every 30 seconds.」。△ holdtime は「3 * the interval」「DR-failover interval occurs after 90 seconds」と書くが R-7761 は Default_Hello_Holdtime= 3.5×Hello_Period=**105 秒**(D3) | ○ J-z17/z25: Hello は 224.0.0.13(ALL-PIM-Routers)宛て 30 秒ごと / J-y03: `ip pim query-interval`。— holdtime の記述なし | 要実測(`show ip pim neighbor` の Expires 最大値・M3) | 確定(30 秒・224.0.0.13)。holdtime は**要実測**(D3) |
| 19 | DR= priority(既定 1)最大 → IP 最大。受信側 DR が Join・送信側 DR が Register | ○ C-CR-PIM(dr-priority):「The router with the highest priority value ... will be elected as the DR」・同値なら「highest IP address」・priority を広告しないルータは最高優先扱い・範囲 0〜4294967294 / 同(redundancy):「The default value of PIM DR priority is 1.」/ 同(query-interval): DR は受信者のための join と「registering local sources with the RP」を担当 | ○ J-z25: 選出基準 1= DR プライオリティ最大・2= IP 最大・DR は Join と Register を担う / J-y03: 既定 1 | 要実測(RT04/RT08 の LAN で DR 表示・M4) | 確定 |
| 20 | Register: 送信元側 DR が RP へユニキャストでカプセル化 → RP が (S,G) Join → Register-Stop | ○ C-OVW:「Hosts that send multicast packets are registered with the RP by the first hop router」・RP が送信元へ Join / C-CLI: debug で Register→RP が (S,G) Join→ネイティブ受信後に Register-Stop→「clears the register flag」/ C-CR-S: F フラグ= registering | ○ J-z27: ファーストホップルータが Register をユニキャスト→RP が (S,G) Join→SPT 経由で届くと Register-Stop。△ **受信者がいない時に RP が即 Register-Stop を返す**場合の記述なし(D14) | 要実測(`debug ip pim` と F フラグ・受信者なし時の Register-Stop・M13) | 確定(基本の流れ)。受信者なしの挙動は要実測 |
| 21 | SPT 切替: 最後のホップが最初のパケットで (S,G) Join(IOS 既定= 即時・`spt-threshold infinity` で RPT に留まる)→ RPT を Prune | ○ C-CR-PIM(spt-threshold)既定:「the PIM leaf router joins the shortest path tree immediately after the first packet arrives from a new source」・infinity=「all sources for the specified group will use the shared tree」/ C-CR-S(J):「The default SPT-Threshold setting is 0 kbps」「the J - Join SPT flag is always set on (*, G) entries and is never cleared」/ C-OVW: 既定動作・infinity で共有木に留める | ○ J-z28: SPT Threshold 既定 0・ラストホップで J フラグ・(S,G) Join・(S,G) RP-bit Prune / J-y03: `ip pim spt-threshold [kbps\|infinity] [group-list]`・既定 0 | 要実測(RT04 で (*,G) の J・(S,G) の JT、infinity で (S,G) が立たないこと・M5) | 確定 |
| 22 | Assert: AD → メトリック → IP 最大 | ○ C-ASSERT〔要旨〕: metric preference= AD・次に metric・同値なら最大 IP / R-7761 §4.6.3: 比較順は **rpt_bit_flag** → metric_preference → route_metric(小さい方が勝ち)→ 最大 IP / C-CR-S: RPF nbr の後ろの「*」は assert で学習 / C-JOIN: OIF フラグ「A - Assert winner」 | ○ J-z22: distance と metric が小さい方・同値なら IF の IP が大きい方が Assert Winner・Loser は Prune(PIM-DM の文脈) | 要実測(RT04・RT08 の両方に static-group を入れて LAN 上に二重転送を起こす・M12) | 確定(比較順)。RPT/SPT 混在(rpt_bit)は出題しない |
| 23 | Join/Prune は 60 秒ごとに再送・状態は 3.5 倍で失効 | △ C-CR-PIM(sparse sg-expiry-timer): PIM-SM の (S,G) mroute エントリの失効は既定「180 seconds」(データが来なくなってからの失効。J/P holdtime とは別のタイマ)。— J/P の送信周期を明記した箇所は照合範囲で見つからず / R-7761: t_periodic 既定 60 秒・J/P Holdtime= 3.5×t_periodic(=210 秒)・Keepalive_Period 210 秒 | △ J-z29: (*,G)/(S,G) は 180 秒以内に受信が無ければ削除。— Join/Prune の周期・3.5 倍の記述なし | 要実測(上流ルータの OIL Expires と (S,G) の Expires を並べて読む・M11) | **要実測**(D4: 「3.5 倍」は J/P の holdtime、IOS の (S,G) 失効は 180 秒。出題文でどちらを指すか書き分ける) |
| 24 | `ip multicast-routing`・IF の `ip pim sparse-mode` | ○ C-CR-MR:「IP multicast routing is disabled.」(既定)・「after enabling IP multicast routing, PIM must be configured on all interfaces」。△「Either the distributed keyword ... is required in Cisco IOS XE Release 3.3S and later releases」(D5)/ C-BASIC〔要旨〕: `ip multicast-routing [distributed]` | ○ J-y02: `ip multicast-routing`・Catalyst は機種により `ip multicast-routing distributed`・通り道の全 IF で `ip pim sparse-mode` / J-y03: PIM を有効にすると IGMPv2 が自動で有効 | 要実測(IOL で `distributed` が必要か・running に何と残るか・M1) | 確定(概念)。IOL での構文は**要実測** |

## 5. RP

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 25 | static RP(`ip pim rp-address`)・全ルータに同じ設定 | ○ C-CR-PIM(rp-address):「All routers in a PIM domain need to have a consistent configuration for the mode and RP addresses」・ACL 無しなら「224/4」・複数一致時は「the RP with the highest RP address configured」(到達性に関係なく)・1 コマンド 1 ACL | ○ J-y02: `ip pim rp-address ipaddress ACL [override]`・ACL 無しで全グループ / J-y03: RP 自身を含む全ルータに設定・通常は Loopback | 要実測(1 台だけ RP アドレスを変えた時の症状・M6) | 確定 |
| 26 | BSR(標準): C-BSR と C-RP・BSR が RP 集合を hop-by-hop で配る | ○ C-CR-PIM(bsr-candidate): C-RP は BSR へ「unicast」・BSR は「TTL of 1 to the ALL-PIM-ROUTERS group address, 224.0.0.13」・「hop-by-hop RPF flooding」・C-BSR priority 0〜255「The C-BSR with the highest priority value is preferred」・既定 0(RFC 5059 の既定 64 と違う)・hash-mask 既定 0 / (rp-candidate) C-RP priority 既定 0・「lowest priority value is preferred」(draft の既定 192 と違う)・interval 既定 60 秒 / C-OVW: BSR は TTL スコープ不可 / R-5059 | ○ J-z36: Auto-RP は Cisco 独自・BSR は PIMv2 のみ・C-RP 通知はユニキャスト・BSR メッセージは 224.0.0.13(TTL 1)hop-by-hop・BSR 選出= priority 大→IP 大 / J-z37: BSR は 1 台だけ動作・ブートストラップタイマ 150 秒・C-RP 60 秒ごと・150 秒で削除 / J-y06: `ip pim bsr-candidate IF hash-mask priority`(大きい方優先・既定 0)・`ip pim rp-candidate ... priority`(小さい方優先・既定 0) | 要実測(`show ip pim bsr-router`・`show ip pim rp mapping` の Info source・M6) | 確定 |
| 27 | Auto-RP(Cisco 独自): 224.0.1.39 announce・224.0.1.40 discovery・sparse では `autorp listener` | ○ C-OVW: IANA が 224.0.1.39/224.0.1.40 を割当・Cisco が実装・MA が衝突を調停して dense 方式で配る / C-CR-PIM(send-rp-announce): CISCO-RP-ANNOUNCE 224.0.1.39・interval 既定 60 秒・holdtime は 3 倍 /(send-rp-discovery)MA は「the candidate RP with the highest IP address」を選ぶ・discovery も 60 秒 /(rp-announce-filter)discovery は 224.0.1.40・「every 60 seconds by default with a holdtime of 180 seconds」/(autorp listener)既定無効 / C-BASIC〔要旨〕: listener＋sparse か sparse-dense のどちらか | ○ J-z33: 224.0.1.39(Cisco-RP-Announce)・224.0.1.40(Cisco-RP-Discovery)・60 秒ごと・最大 IP を選出・ルータは既定で 224.0.1.40 に参加 / J-z34: MA 冗長は主副なし・180 秒で削除 / J-z35・y04: sparse-dense か `ip pim autorp listener` | 要実測(sparse-mode のみ・listener なしで MA の先に届かないこと・(*,224.0.1.40) の L フラグ・M7) | 確定 |
| 28 | group-to-RP mapping の優先・`show ip pim rp mapping` | ○ C-CR-PIM(rp-address):「Dynamic group-to-RP mappings take precedence over static group-to-RP mappings--unless the override keyword is used」/ C-BASIC〔要旨〕: 「The simultaneous deployment of Auto-RP and BSR is not supported.」/ C-OVW:「by default, Auto-RP messages supersede static RP configurations」/ C-CR-PIM(bsr-candidate): BSR 学習 C-RP は **longest match → 最小 priority → hash → 最大 IP** / C-AUTORP-MIX〔要旨〕: override なしなら動的が優先 | △ J-y02: override= 「Auto-RP、BSRなどの設定があっても、このコマンド設定のRPを優先」○。BSR の RP 選出は priority→hash→RP アドレス最大の 3 段で **longest match の段がない** / Auto-RP は最大 IP ○ | 要実測(static と Auto-RP でグループ範囲が違う時・同じ時の勝者・override の有無・M6) | **要実測**(D6: 範囲が違う時の longest match が情報源をまたいで効くかは文書から断定できない) |
| 29 | anycast RP(IPv4)= 複数 RP に同じアドレス・MSDP で SA 共有 | ○ C-OVW: 同じ IP を Loopback に・「32-bit mask」・MSDP ピアで SA を交換・障害時はルーティングで収束 / C-CR-MR(msdp originator-id): 既定は「The RP address is used as the originator ID」・logical RP の時に変更 | ○ J-z41: Loopback /32 の同一アドレス・MSDP の SA で送信元を通知・最初のパケットだけカプセル化 / J-y14: router-id を静的に・MSDP ピアは anycast アドレスではない・`ip msdp originator-id`。△ 構文行が「connected-source」(正しくは `connect-source`。同ページの設定例は connect-source・D10) | 要実測(`show ip msdp peer`・`show ip msdp sa-cache`・M15) | 確定 |
| 30 | MSDP= RP 間で SA を TCP 639 で交換・ドメイン間にも | ○ C-OVW: RP 間の MSDP は「TCP connection」・最初のデータを SA にカプセル化・ISP 間用に開発 / C-MSDP〔要旨〕: TCP 639・IP の小さい側が能動接続・keepalive 60 秒・75 秒で reset / R-3618: 「well-known port 639」・IP の大きい側が listen | △ J-z41: 本来は AS 間用・SA ○。**TCP 639 の記述なし** | 要実測(`show tcp brief` で 639・M15) | 確定(639 は R-3618) |
| 31 | PIMv6 anycast RP(MSDP なしで PIM が同期) | ○ C-V6ANY〔要旨〕: 「it does not depend on the Multicast Source Discovery Protocol (MSDP), which runs only on IPv4」・RFC 4610・RP が Register を他の RP へ送る・`ipv6 pim anycast-rp <rp> <peer>` / R-4610: PIM のみのドメインで Anycast-RP | — J-z46/y20: IPv6 PIM は Sparse のみ・RP は static か BSR。anycast RP の記述なし | 要実測(任意・`ipv6 pim anycast-rp` の受理・M20) | 確定(概念) |
| 32 | `ip multicast boundary`・`ip pim rp-announce-filter` | ○ C-CR-MR(boundary): 標準 ACL= グループ・拡張 ACL=(S,G)・`in`= 送信元トラフィックを落とす・`out`= IGMP/Join による mroute 作成を防ぎ OIL に入れない・方向なしは両方・`filter-autorp` は Auto-RP の announce/discovery 内の範囲も削る(標準 ACL のみ)/ C-CR-PIM(rp-announce-filter):「This command should only be configured on RP mapping agents」・既定は全 announce を受理 | ○ J-y05: rp-announce-filter は MA で設定・`rp-list`/`group-list` / boundary で 224.0.1.39/40 を deny する例 / J-y15: boundary は in/out 両方に効く・TTL threshold 既定 0 | 要実測(`in`/`out`/`filter-autorp` の受理と効果・M16/M17) | 確定(構文)。効果は要実測 |

## 6. SSM と bidir

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 33 | SSM= 送信元指定・RP 不要・(S,G) だけ・232/8(`ip pim ssm default`)・IGMPv3 必須 | ○ C-CR-PIM(ssm): `default`=「Defines the SSM range access list to 232/8」・**既定は「The command is disabled.」**(D7)・SSM 範囲では MSDP SA を受けも出しもしない / C-C9K-SSM〔要旨〕: (S,G) の Join/Prune だけ・(*,G) は作らない・IGMPv1/v2 の Report は SSM mapping で送信元を補う / C-OVW: IGMPv3 必須 / C-CR-S: s フラグ「within the SSM range」・I フラグ(S,G) report 由来 / R-4607 | ○ J-z40: (*,G) を作らず (S,G) のみ・RP 不要・IGMPv3 INCLUDE・232/8・`ip pim ssm default`・`ip pim ssm range ACL` / J-y13: 受信側 IF で `ip igmp version 3` | 要実測(`ip pim ssm default` 無しで 232.x を v3 join した時の挙動・sLTI 等のフラグ・M9) | 確定(「IOS では既定で 232/8 が SSM になるわけではない」を明記) |
| 34 | bidir= 共有木で双方向・(S,G) なし・DF・多対多 | ○ C-OVW: bidir は (*,G) だけで転送・Register なし・RP アドレスはルータのアドレスでなくてよい / C-C9K-PIM〔要旨〕: 「The router with the most preferred unicast routing metric to the RP becomes the DF」「A DF is selected for every RP of bidirectional groups」「A router only creates (*, G) entries for bidirectional groups」/ C-CR-S: B フラグ= Bidir Group / C-CR-PIM(bidir-enable): Command Default「The command is enabled.」と Usage「Bidir-PIM is disabled by default」が**同じページで矛盾**(D8)/ R-5015 | ○ J-z38: DF= RP へのベストパス・リンクごと・RP ごと・同点は IF の IP 最大・多対多 / J-z39: (S,G) Join と Register は破棄・スイッチオーバーなし / J-y12: 全ルータで `ip pim bidir-enable`・RP 設定に `bidir`・表示 `Bidir-Upstream`・DF Winner | 要実測(bidir-enable の既定・`show ip pim interface df`・B フラグ・M8) | 確定(概念)。`bidir-enable` の要否は**要実測** |
| 35 | PIM-DM= flood & prune(参考) | ○ C-OVW:「This process repeats every 3 minutes.」・「you should avoid the use of PIM-DM」・sparse-mode のみの IF では dense fallback しない | ○ J-z14/z16: Flood & Prune・180 秒ごと / J-z23: State Refresh 60 秒 | 不要(概念) | 確定 |

## 7. RPF

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 36 | RPF check= 受信 IF が送信元(共有木では RP)への経路の出口と一致するか。不一致は破棄 | ○ C-OVW:「A router will forward a multicast packet only if it is received on the upstream interface」・一致しなければ「the packet is dropped」/ C-CR-S(Incoming interface):「If the packet is not received on this interface, it is discarded.」/ C-TSG:「Multicast routing does not forward a packet unless the source of the packet passes a RPF check.」 | ○ J-z15: 送信元への出力 IF と受信 IF が一致すれば成功・全ルータで既定動作 / J-z24: (S,G) は Sender、(*,G) は RP の IP で RPF IF が決まる | 不要(概念) | 確定 |
| 37 | `show ip rpf <送信元>`・RPF 失敗の典型 | ○ C-TSG: 等コスト時は「the interface that has a Protocol Independent Multicast (PIM) neighbor with the highest IP address」・debug で「not RPF interface」/ C-CR-S: `show ip mroute count` の「RPF failed」カウンタ | ○ J-y03: `show ip rpf x.x.x.x` で RPF IF と RPF ネイバー / J-z15・y11: 等コスト時は「ネクストホップアドレスの値が大きい」ルートの IF(△ PIM ネイバーであることの条件が書かれていない・D9) | 要実測(RT04 から RT01 への等コスト 2 経路で `show ip rpf`・高い方の IF の PIM を外した時・M10) | 確定(「最大 IP の PIM ネイバー」と書く) |
| 38 | `ip mroute` で RPF を変える・`ip multicast multipath` で等コストに分散 | ○ C-CR-MR(ip mroute):「Static mroutes are used to calculate RPF information, not to forward traffic.」・再配送不可・ルータローカル・longest match /(multipath)既定:「multicast traffic will not be load split」・既定の RPF は「this neighbor must have the highest IP address」・multipath は既定で送信元アドレスの S-hash・「load splits the traffic but does not load balance」・同一送信元は 1 経路 / C-ECMP〔要旨〕: s-g-hash basic / next-hop-based の選択肢 | △ J-y11: `ip mroute network mask ipaddress [IF]` ○。**`ip multicast multipath` の記述なし** | 要実測(送信元 2 つで経路が分かれるか・M10) | 確定(「分散」は送信元単位のハッシュで、パケット単位ではないと明記) |

## 8. 読解

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 39 | `show ip mroute` の (*,G)/(S,G)・Incoming interface・RPF nbr・Outgoing interface list | ○ C-CR-S Table 25: Incoming interface=「Expected interface for a multicast packet from the source」/ RPF nbr=「IP address of the upstream router to the source」・後ろの「*」は assert で学習 / Outgoing interface list=「Interfaces through which packets will be forwarded」/ Timers= Uptime/Expires / State/Mode= Forward・Pruned・Null と dense/sparse/sparse-dense | ○ J-z26: (*,G) の Incoming= RP への最短経路の IF・RP 自身では「Null」と RPF nbr「0.0.0.0」・OIL= Join 受信 IF・Receiver の IF・join-group/static-group の IF / J-z27: (S,G) は Sender への IF・OIL から RPF IF を除く | 要実測(RP・FHR・LHR 各々の表示を取得・M14) | 確定 |
| 40 | フラグ S・C・L・J・T・P・F・s・B | ○ C-CR-S Table 25(原文要約): D= dense・S= sparse・B= bidir・s= SSM 範囲・C=「A member of the multicast group is present on the directly connected interface」・L=「The router itself is a member」(join-group と **224.0.1.39/40 の RP mapping** も)・P=「Route has been pruned」・R=「the (S, G) entry is pointing toward the RP」(共有木上の prune 状態)・F=「the software is registering for a multicast source」・T=「packets have been received on the shortest path source tree」・J= 閾値超過(既定 0 kbps で (*,G) に常時)・M/A= MSDP・X= proxy join・I= (S,G) report(IGMPv3 等)で作成・E= extranet / OIF フラグ A= Assert winner(C-JOIN) | △ J-z29: S・C・L・P・T・F・R・J の表 ○。**R の説明が「共有ツリー経由のルーティングを停止している」、T が「(S,G) に従い転送される」で Cisco の定義文と言い回しが違う**(D11)・P は「OIL の全 IF が Prune」 / J-z20: D | 要実測(IOL の Flags 凡例行を丸ごと取得・M14) | 確定(定義文は Cisco の Table 25 を正) |
| 41 | `show ip pim neighbor` / `show ip pim interface`(DR)/ `show ip pim rp mapping` | △ C-CR-S: 各コマンド掲載(出力全行はここでは未照合)/ C-RPENG: `show ip pim rp mapping` の出力例(`Group(s) 224.0.0.0/4`・`Info source: ... via Auto-RP`)・`show ip pim bsr`(BSR address・priority・hash mask length) | ○ J-y03/y05/y07: 各コマンドの用途(neighbor に DR 情報・interface に DR・rp mapping・`show ip pim bsr-router`・`show ip pim rp-hash`) | 要実測(出力書式・M4/M6) | 確定(書式は要実測) |

## 食い違い・注意点

| ID | 論点 | 内容 | 出題への影響 |
|---|---|---|---|
| D1 | IGMP querier timeout(#9) | Cisco Command Reference は「two times the IGMP query interval」(既定 60 秒なら 120 秒)。Catalyst 9300 17.15 の既定表〔要旨〕と ネットワークエンジニアとして(J-y08)は 60 秒。RFC 2236 の Other Querier Present Interval は 2×Query Interval+½ Query Response Interval | 数値は IOL の `show ip igmp interface` で確かめるまで出さない(M2)。**要実測** |
| D2 | IGMP Query 間隔の「既定」(#9) | IOS の既定は 60 秒(Cisco・ネットエンジニアとして一致)。RFC 2236 の既定は 125 秒 | 「IGMPv2 の既定は 60 秒」と書かず「Cisco IOS の既定は 60 秒」と書く。項目表の表現で可 |
| D3 | PIM hello holdtime(#18) | RFC 7761 は 3.5×30= **105 秒**。Cisco Command Reference(`ip pim query-interval`)は「3 * the interval」「DR-failover ... after 90 seconds」。ネットエンジニアとして は holdtime を書いていない | 105 と 90 のどちらが IOS の実値かは IOL で `show ip pim neighbor` の Expires 最大値を見て決める(M3)。**要実測** |
| D4 | Join/Prune と「3.5 倍で失効」(#23) | RFC 7761: J/P は 60 秒周期・J/P Holdtime= 3.5×60= 210 秒・(S,G) Keepalive 210 秒。IOS: PIM-SM の (S,G) エントリ失効は 180 秒(`ip pim sparse sg-expiry-timer` 既定)。ネットエンジニアとして も「180 秒」。項目表の「状態は 3.5 倍で失効」は J/P で作った OIL の holdtime(210)を指すなら正しいが、mroute エントリの失効(180)と混同しやすい | 出題文で「どのタイマか」を明記する。IOL の OIL Expires と (S,G) Expires を実測(M11)。**要実測** |
| D5 | `ip multicast-routing` と `distributed`(#24) | Cisco Command Reference:「distributed ... is required in Cisco IOS XE Release 3.3S and later releases」。IOS XE 17 の基本設定ガイドは `[distributed]` を任意として記載〔要旨〕。ネットエンジニアとして は「Catalyst は機種により distributed」 | IOL で `ip multicast-routing` だけで通るか・running に `distributed` が付くか確認(M1)。穴埋めは `ip multicast-routing` を正とし、distributed は出題しない案 |
| D6 | group-to-RP mapping の優先(#28) | 文書で確定できるのは: 動的(Auto-RP・BSR)> static(override なし)/ override 付き static が最優先 / static が複数一致すれば RP アドレス最大 / BSR の C-RP 選出は longest match → priority 小 → hash → IP 大 / Auto-RP の MA は IP 最大 / Auto-RP と BSR の同時運用は非サポート。**static と動的でグループ範囲の長さが違う時に longest match が情報源をまたいで効くか**は読んだ文書に明文なし。ネットエンジニアとして の BSR 選出は longest match の段を欠く | 範囲違いの設問は実測後に出す(M6)。BSR の選出順は Cisco の 4 段で書く。**要実測** |
| D7 | SSM は既定で有効か(#33) | `ip pim ssm` の既定は「The command is disabled.」。232/8 が SSM として扱われるのは `ip pim ssm default` を入れた時 | 「IOS は既定で 232/8 を SSM として扱う」は誤り。穴埋めで `ip pim ssm default` を空欄にする時はこの点を解説に書く |
| D8 | `ip pim bidir-enable` の既定(#34) | Cisco Command Reference の同一ページで Command Default「The command is enabled.」と Usage「Bidir-PIM is disabled by default」が矛盾(後者は 12.0(18)ST 当時の互換の説明)。ネットエンジニアとして は全ルータで設定が必要と説明 | IOL で `show running-config all \| include bidir` と、bidir-enable 無しで `ip pim rp-address X bidir` が受理されるかを確認(M8)。**要実測**。確定するまで「必須」とは書かない |
| D9 | 等コスト時の RPF(#37・#38) | Cisco: 「PIM neighbor with the highest IP address」(PIM ネイバーであることが条件)。ネットエンジニアとして: 「ネクストホップアドレスの値が大きい」ルートの IF(ネイバー条件なし)。multipath の既定は分散しない・有効時は送信元単位のハッシュ | 「最大 IP の PIM ネイバー」と書く。高い方の経路で PIM を切ると RPF が低い方へ移るかを実測(M10) |
| D10 | MSDP の構文(#29・#30) | ネットエンジニアとして J-y14 の構文行は `connected-source`(同ページの設定例は `connect-source`)。Cisco は `ip msdp peer {peer-address} [connect-source IF] [remote-as N]`。TCP 639 はネットエンジニアとして に記載なし(RFC 3618 と Cisco 要旨で確定) | 構文は `connect-source` を正とする |
| D11 | フラグの定義文(#40) | Cisco の定義: R=「(S,G) entry is pointing toward the RP」(共有木上で prune している状態を表す)・T=「packets have been received on the shortest path source tree」・P=「Route has been pruned」。ネットエンジニアとして は R を「共有ツリー経由を停止している」、T を「(S,G) に従い転送される」と言い換えている。項目表の列挙には R・D・M・A・X・I・E と OIF の A(Assert winner)が無い | 選択肢の文言は Cisco の定義文に合わせる。R・A(Assert winner)・M は読解問題で使える候補として項目表に足すか検討(**要ユーザ判断**) |
| D12 | IGMPv2 Leave の宛先の言い方(#7) | Catalyst 9300 ガイド〔要旨〕は 224.0.0.2 を「all devices on a subnet」と説明。RFC 2236 は all-routers | 「全ルータ(224.0.0.2)」と書く |
| D13 | 224.0.0.22 と FF02::16(#3・#10・#17) | 224.0.0.22 はネットエンジニアとして に無く Cisco と RFC 3376 にある。FF02::16・ICMPv6 Type 130/131/132/143 はネットエンジニアとして と RFC 3810 にあり Cisco のガイドには番号なし | どちらも RFC で確定。出典は RFC を併記 |
| D14 | Register-Stop の時機(#20) | ネットエンジニアとして は「SPT でネイティブに届いたら Register-Stop」のみ。RFC 7761 では受信者がいない(OIL が空)時も RP は Register-Stop を返す | 「受信者がいない時の Register」は実測(M13)してから出題 |
| D15 | IGMP snooping の mrouter 学習(#13) | ネットエンジニアとして は IGMP query・PIM・DVMRP・CGMP(旧 Catalyst 系)。Catalyst 9300 17.x は IGMP query と PIM(＋静的)。snooping querier の対応版は C9K が v1/v2、旧 7600 の CR は v2 | 選択肢に DVMRP/CGMP を正解として入れない |
| D16 | Auto-RP の推奨・前提の書き方(#27) | IOS XE 16.9 の技術概要は「Auto-RP を推奨」「前提は sparse-dense」と古い書き方が残る。17.x 系の設定ガイドは listener＋sparse か sparse-dense のどちらか | 「Auto-RP には sparse-dense が必須」は誤りとして扱う(listener で代替可) |
| D17 | ネットエンジニアとして の RP 設定の注意(#26・#27) | Auto-RP・BSR のページにも「RP アドレスの設定は…全てのマルチキャストルータで設定する必要」とスタティック RP ページの文が複写されている | 動的 RP では各ルータに RP アドレスを設定しない。この一文は根拠にしない |
| D18 | Cisco の既定値が RFC と違う(#26) | C-BSR priority の既定は Cisco 0・RFC 5059 は 64。C-RP priority の既定は Cisco 0・draft は 192(Cisco CR が自ら明記) | 既定値を問う時は「Cisco IOS の既定」と明記。C-BSR は大きい方、C-RP は小さい方が優先という向きの違いは出題価値が高い |
| D19 | PIM snooping・IGMP snooping querier の IOL 可否(#14・#16) | 文書上は Catalyst の機能。ioll2 での有無は未確認 | ラボ化は実測後(M18・M19) |

## 実機で裏どりが必要な論点(CML PoC 候補・IOL / ioll2)

盤面は `problems/_POC-MCAST`(RT01 送信元 ─ RT02 送信元側 DR ─ RT03 RP 3.3.3.3 / RT05 ─ RT04・RT08 受信 LAN ─ SW01 ioll2 ─ RT06/RT07 受信者)を前提にした。
優先度: A= 出題の正誤に直結 / B= 表示・指紋(採点 regex)に必要 / C= 任意。

| # | 優先 | 論点 | 確認方法の案 | 関連項目 |
|---|---|---|---|---|
| M1 | A | IOL で `ip multicast-routing` 単独が通るか・`distributed` が必要か/自動で付くか | 全ルータで `ip multicast-routing` 投入→ `show running-config \| include multicast-routing`・`show ip multicast`・`show ip mroute` が出るか | #24・D5 |
| M2 | A | IGMP の既定値と表示: version 2・query 60 秒・querier timeout(60 か 120 か)・max response 10 秒・LMQC 2・LMQI 1000 ms・querier の IP | RT04 の受信 LAN IF で `show ip igmp interface Et0/2` を取得。`ip igmp query-interval 30` を入れて querier timeout が追従するか | #8・#9・#12・D1 |
| M3 | A | PIM neighbor holdtime(105 か 90 か) | `show ip pim neighbor` の Expires 直後の値・`debug ip pim hello`(holdtime 値)。`ip pim query-interval 10` で追従するか | #18・D3 |
| M4 | A | 受信 LAN(RT04/RT08)で DR= IP 最大・IGMP querier= IP 最小が別々に決まる/`ip pim dr-priority` で DR が移る | `show ip pim interface`(DR 列)・`show ip igmp interface`(querier 行)・`show ip pim neighbor`(DR マーク) | #8・#19・#41 |
| M5 | A | SPT 切替の既定と infinity: RT04 の (*,G) に J(`SJC`)・(S,G) に `JT`、RP 側で R フラグ付き (S,G) の Prune 状態。`ip pim spt-threshold infinity` で RT04 に (S,G) が立たない | RT01 から `ping 239.1.1.1 repeat 100`・RT06 で `ip igmp join-group 239.1.1.1`。RT02〜RT05 で `show ip mroute 239.1.1.1` | #21・#40 |
| M6 | A | group-to-RP の優先: static(override なし/あり)× Auto-RP、同範囲と範囲違い(例 static 224/4 と Auto-RP 239.1.1.0/24)・static 複数一致で RP アドレス最大・BSR の priority(小さい方)・C-BSR(大きい方) | `show ip pim rp mapping`(Info source・via Auto-RP/bootstrap/static)・`show ip pim rp-hash 239.1.1.1`・`show ip pim bsr-router` | #25・#26・#28・D6 |
| M7 | A | Auto-RP: 全 IF sparse-mode で listener なし→ MA の先へ discovery が届かない/listener ありで届く・(*,224.0.1.40) の L フラグ | RT03 を C-RP・RT05 を MA にして RT04 で `show ip pim rp mapping`・`show ip mroute 224.0.1.40` | #27・#40・D16 |
| M8 | A | `ip pim bidir-enable` の既定と要否・bidir の表示(B フラグ・`Bidir-Upstream`・DF) | `show running-config all \| include bidir`・`ip pim rp-address 3.3.3.3 bidir` の受理・`show ip pim interface df`・`show ip mroute` | #34・D8 |
| M9 | A | SSM: `ip pim ssm default` 無しで 232.1.1.1 に v3 join した時の挙動/有りで `sT`・`sLTI`・RP 不要 | RT04 で `ip igmp version 3`・`ip igmp join-group 232.1.1.1 source 10.0.1.1`(RT01)。`show ip mroute 232.1.1.1`・`show ip pim rp mapping` | #10・#33・D7 |
| M10 | A | 等コスト RPF: RT04 から RT01 へ RT03 経由と RT05 経由が等コスト→ `show ip rpf` が最大 IP の PIM ネイバーを選ぶ/その IF の PIM を外すと低い方へ移る/`ip multicast multipath` で送信元 2 つが別経路に分かれる | `show ip rpf 10.0.1.1`・`show ip mroute`(RPF nbr)・`show ip mroute count`(RPF failed) | #37・#38・D9 |
| M11 | B | タイマの読み分け: 上流ルータの OIL Expires(J/P holdtime 210?)と (S,G) 自体の Expires(180?) | M5 の盤面で RT03/RT05 の `show ip mroute` を 10 秒おきに数回取る | #23・D4 |
| M12 | B | Assert: RT04 と RT08 の両方に `ip igmp static-group 239.1.1.1` を入れて受信 LAN に二重転送→ 勝者の OIF に `A`・敗者は Prune・RPF nbr の `*` | `debug ip pim`・`show ip mroute 239.1.1.1`。AD/メトリックを変えて勝者が入れ替わるか | #22・#39・#40 |
| M13 | B | Register/Register-Stop: RT02 の (S,G) に F フラグ・受信者なしでも RP が Register-Stop を返すか | 受信者なしで RT01 から送信→ RT02・RT03 で `debug ip pim`・`show ip mroute` | #20・D14 |
| M14 | B | `show ip mroute` の IOL 表示: Flags 凡例行の全文(E・Z 等の有無)・OIF フラグ凡例・RP での `Incoming interface: Null, RPF nbr 0.0.0.0`・`(*, 224.0.1.40)` の常駐 | 各ルータで `show ip mroute` 全文を取得して採点 regex の基準にする | #39・#40 |
| M15 | B | MSDP/anycast RP: RT03 と RT05 に同じ Loopback を置き `ip msdp peer X connect-source Lo0`・`ip msdp originator-id`。`show ip msdp peer`(Up)・`show tcp brief`(639)・`show ip msdp sa-cache` | 2 台 RP 化して送信元・受信者を別 RP 側に置く | #29・#30・D10 |
| M16 | B | `ip multicast boundary`: `in`/`out`/`filter-autorp` の受理と効果(OIL に入らない・Auto-RP 範囲の削除) | RT04 の LAN 側 IF に 239.0.0.0/8 deny の boundary。`show ip mroute`・`show ip pim rp mapping` | #32 |
| M17 | B | `ip pim rp-announce-filter` を MA 以外に入れた時は効かないこと | MA(RT05)と非 MA で比較 | #32 |
| M18 | B | ioll2(SW01)の IGMP snooping: 既定有効か・`show ip igmp snooping groups`/`mrouter`・mrouter の学習元・`ip igmp snooping querier`・`ip igmp profile`/`ip igmp filter` の受理 | SW01 で各 show。RT04/RT08 の PIM を止めて querier を試す | #13・#14・#15・D15・D19 |
| M19 | C | ioll2 に `ip pim snooping` があるか | コマンド受理のみ | #16・D19 |
| M20 | C | IPv6: `ipv6 multicast-routing` で PIM/MLD が自動有効・`ipv6 mld join-group`・`ipv6 pim anycast-rp` の受理 | 2 台で `show ipv6 pim interface`・`show ipv6 mld interface` | #17・#31 |
| M21 | C | join-group と static-group の差: group 宛 ping に応答するのは join-group だけ・L フラグの有無 | RT06 に join-group、RT07 側は RT08 の static-group で比較 | #11 |
| M22 | C | IGMPv2 Leave と last member query: 離脱時に Group-Specific Query が 1 秒間隔で 2 回 | RT06 で `no ip igmp join-group`→ RT04 で `debug ip igmp` | #7・#9 |

---

更新方法: 実測したら該当行の「実機」欄を ○+要点に書き換え、判定を更新する。実測ログの詳細は PoC 側(`problems/_POC-MCAST` または
`poc/` 配下の README)に書き、この表には要点だけ書く。

## 実測の反映(2026-09-22・poc/mcast/README.md)

上の表の「実機」欄は作成時点のまま(要実測)。実測結果は次のとおりで、**判定はこちらを優先する**。

| 論点 | 実測(iol-xe 17.15.1) | 解消した食い違い |
|---|---|---|
| `ip multicast-routing` | distributed 無しで動作 | D5 |
| IGMP 既定 | v2・query 60・**querier timeout 120**・max resp 10・LMQC 2・LMQI 1000 ms | D1(120 が正)・D2(「IOS の既定」と書く) |
| PIM hello | 30 秒・neighbor の Expires は最大約 105 秒・J/P 60 秒 | D3(105) |
| DR / querier | DR= 最大 IP(dr-priority で変更)・querier= 最小 IP | — |
| SPT 切替 | 既定即時・`spt-threshold infinity` で受信側は (*,G) のみ | — |
| Assert | 同値なら IP 最大が勝つ・OIF に `A` | — |
| SSM | 既定無効(ssm default 無しでは v3 の (S,G) 参加も ASM の (*,G))・v2 の 232/8 参加は無視 | D7 |
| bidir | `ip pim bidir-enable` 既定無効・(*,G) のみ・`B`・`Bidir-Upstream`・DF | D8 |
| 等コスト RPF | IP 最大のネクスト ホップ・multipath でハッシュ選択 | D9(PIM ネイバー条件は未実測) |
| RP の優先 | 動的 > static(override なし)・override で static・**範囲の広狭は効かない(動的が勝つ)** | D6 |
| BSR / Auto-RP | C-RP priority 既定 0・小さい値が勝つ・同値はハッシュ/Auto-RP は IP 最大・listener 無しでは discovery が届かない | D18(Cisco 既定 0 を確認) |
| MSDP anycast | SA cache・`M`/`A` フラグ | — |
| boundary | deny したグループは IGMP にも載らない | — |
| ioll2 snooping | 既定有効・querier 可・**IGMP profile/filter は無い** | D19(filter は文書ベース・PIM snooping は未確認) |
