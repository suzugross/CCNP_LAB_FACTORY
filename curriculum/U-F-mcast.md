# U-F1 / U-F2 マルチキャスト — 知識項目表(単元シラバス)

台帳: [CURRICULUM.md](../CURRICULUM.md) U-F1(IGMP/MLD・L2)・U-F2(PIM/RP)。資格= ENCOR 3.3.d(describe: RPF check・PIM SM・IGMP v2/v3・SSM・bidir・MSDP)/
CCIE 1.6(IGMPv2/v3・IGMP snooping・PIM snooping・querier・IGMP filter・MLD・RPF・PIM SM・static RP/BSR/Auto-RP・group-to-RP mapping・SSM・
boundary・RP announcement filter・PIMv6 anycast RP・MSDP anycast RP・multipath)。BL-217(P1)・BL-077(ラボ)。
**この表が「網羅的」の物差し**。P1(穴埋め)は各項目を少なくとも 1 セクションで空欄または本文に載せる。
照合表(Cisco 公式・解説サイト・実機)= [U-F-mcast.sources.md](U-F-mcast.sources.md)。

凡例= P1 列: 穴埋め KB `cloze_kb_mcast.py` の kind(接頭辞 `g_`)。○= 本文に載る(空欄候補)・△= 本文に載るが空欄にしない・✗= 未収録。

## 1. 基礎 — kind `g_basics`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 1 | マルチキャストの用途(1 対多・送信元は 1 回送るだけ・受信者の集合= グループ) | ○ g_basics | ✗ | — |
| 2 | IPv4 マルチキャスト アドレス 224.0.0.0/4(クラス D)・224.0.0.0/24 はリンク ローカル(TTL 1)・232.0.0.0/8 は SSM・239.0.0.0/8 は組織内(administratively scoped) | ○ g_basics | ✗ | — |
| 3 | 予約アドレスの例: 224.0.0.1 全ホスト・224.0.0.2 全ルータ・224.0.0.13 全 PIM ルータ・224.0.0.22 IGMPv3 | △ g_basics / g_igmp / g_pim | ✗ | — |
| 4 | L2 への写像: 01:00:5E + IP の下位 23 ビット → 32 個の IP が 1 つの MAC を共有する | ○ g_basics | ✗ | — |
| 5 | 配信木: 送信元木(SPT・(S,G))と共有木(RPT・(*,G)・根は RP) | ○ g_basics / g_read | ✗ | L1 |
| 6 | 受信者の居場所を知る方法= IGMP(ホスト⇄ルータ)・ルータ間の木= PIM | △ g_basics | ✗ | — |

## 2. IGMP — kind `g_igmp`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 7 | IGMPv2: Membership Report(参加)・Leave Group(224.0.0.2 宛)・General Query / Group-Specific Query | ○ g_igmp | ✗ | L1 |
| 8 | IGMPv2 の querier 選出= 最小 IP アドレス(PIM DR の最大 IP と逆) | ○ g_igmp | ✗ | L1 |
| 9 | Query 間隔 既定 60 秒(IOS)・last member query で離脱を確認 | ○ g_igmp(実測 60・querier timeout 120) | ✗ | — |
| 10 | IGMPv3: 送信元を指定した参加(INCLUDE/EXCLUDE)・Report の宛先 224.0.0.22・SSM に必須 | ○ g_igmp | ✗ | L2 |
| 11 | `ip igmp join-group`(ルータ自身が参加し ping に応答)・`ip igmp static-group`(転送だけ) | △ g_igmp | ✗ | L1 |
| 12 | `show ip igmp groups` / `show ip igmp interface`(バージョン・querier・タイマ) | △ g_igmp | ✗ | L1 |

## 3. L2 マルチキャスト — kind `g_l2`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 13 | IGMP snooping= スイッチが IGMP を覗いて受信者のポートにだけ転送(既定で有効)・マルチキャスト ルータのポート(mrouter port) | ○ g_l2 | ✗ | L2 |
| 14 | IGMP snooping querier= ルータの無い VLAN で Query を代行 | ○ g_l2 | ✗ | L3 |
| 15 | IGMP filter(`ip igmp profile` + `ip igmp filter`)・参加できるグループを制限 | ○ g_l2(文書ベース・ioll2 に無い) | ✗ | L3 |
| 16 | PIM snooping= ルータが並ぶ VLAN で PIM Join を覗いて転送を絞る | ✗(ioll2 未確認・文書のみ) | ✗ | — |
| 17 | MLD= IPv6 版 IGMP(MLDv1≒IGMPv2・MLDv2≒IGMPv3)・ICMPv6 のメッセージ | ○ g_l2 | ✗ | — |

## 4. PIM-SM — kind `g_pim`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 18 | PIM は経路を自分で持たない(ユニキャスト経路表に依存= protocol independent)・Hello は 224.0.0.13・既定 30 秒 | ○ g_pim | ✗ | L1 |
| 19 | DR 選出= DR priority(既定 1)が最大 → IP が最大。受信側 DR が (*,G) Join を RP へ・送信側 DR が Register | ○ g_pim | ✗ | L1 |
| 20 | Register: 送信元側 DR が最初のパケットを RP へユニキャストでカプセル化 → RP が (S,G) Join → Register-Stop | ○ g_pim | ✗ | L2 |
| 21 | SPT への切り替え: 最後のホップのルータが最初のパケットで (S,G) Join(IOS の既定は即時・`ip pim spt-threshold infinity` で RPT に留まる)→ RPT 側を Prune | ○ g_pim / g_read | ✗ | L2 |
| 22 | Assert: 同じ LAN に 2 台が転送したとき、AD → メトリック → IP 最大の順で勝者が転送 | ○ g_pim | ✗ | L3 |
| 23 | Join/Prune は 60 秒ごと(既定)に再送・状態は 3.5 倍で失効 | ✗(3.5 倍の値が資料で割れる・出さない) | ✗ | — |
| 24 | `ip multicast-routing`・インターフェイスの `ip pim sparse-mode` | △ g_pim / g_ssm | ✗ | L1 |

## 5. RP — kind `g_rp`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 25 | static RP(`ip pim rp-address`)・全ルータに同じ設定が必要 | ○ g_rp | ✗ | L1 |
| 26 | BSR(PIMv2 標準): candidate BSR と candidate RP・BSR が RP 集合を hop-by-hop で配る・`ip pim bsr-candidate` / `ip pim rp-candidate` | ○ g_rp | ✗ | L2 |
| 27 | Auto-RP(Cisco 独自): 候補 RP が 224.0.1.39 へ announce・mapping agent が 224.0.1.40 で discovery・sparse mode では `ip pim autorp listener` が必要 | ○ g_rp | ✗ | L2 |
| 28 | group-to-RP mapping の優先(同じグループに複数の情報源がある時の選び方)・`show ip pim rp mapping` | ○ g_rp(実測: 動的が static より優先・範囲は効かない) | ✗ | L2 |
| 29 | anycast RP(IPv4)= 複数の RP に同じアドレス・MSDP で送信元情報(SA)を共有 | ○ g_rp | ✗ | L3 |
| 30 | MSDP= RP 間で Source-Active を TCP 639 で交換・ドメイン間のマルチキャストにも使う | ○ g_rp | ✗ | L3 |
| 31 | PIMv6 anycast RP(MSDP 無しで PIM 自身が RP 間を同期) | ✗(未実測) | ✗ | — |
| 32 | multicast boundary(`ip multicast boundary`)・RP announcement filter(`ip pim rp-announce-filter`) | △ g_rp(boundary のみ・rp-announce-filter は未) | ✗ | L3 |

## 6. SSM と bidir — kind `g_ssm`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 33 | SSM= 受信者が送信元を指定・RP 不要・(S,G) だけ・232.0.0.0/8(`ip pim ssm default`)・IGMPv3 が必要 | ○ g_ssm / g_basics | ✗ | L2 |
| 34 | bidir PIM= 共有木だけで双方向・(S,G) を作らない・DF(designated forwarder)・多対多に向く | ○ g_ssm | ✗ | — |
| 35 | PIM-DM(dense)= flood & prune・参考(現行の設計では使わない) | △ g_ssm | ✗ | — |

## 7. RPF — kind `g_rpf`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 36 | RPF check= 受信インターフェイスが、送信元(共有木では RP)へのユニキャスト経路の出口と一致するか。不一致は破棄 | ○ g_rpf | ✗ | L1 |
| 37 | `show ip rpf <送信元>`・RPF 失敗の典型(ユニキャストの経路と PIM の有効なインターフェイスが食い違う) | ○ g_rpf | ✗ | L3 |
| 38 | 静的 mroute(`ip mroute`)で RPF を変える・`ip multicast multipath` で等コストに分散 | ○ g_rpf | ✗ | L3 |

## 8. 読解 — kind `g_read`(世界機構)

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 39 | `show ip mroute` の (*,G) と (S,G)・Incoming interface・RPF nbr・Outgoing interface list | ○ g_read | ✗ | L1 |
| 40 | フラグ: S(sparse)・C(接続された受信者)・L(ローカル)・J(SPT へ参加)・T(SPT 上)・P(prune)・F(register)・s(SSM)・B(bidir) | ○ g_read(S/C/J/T) | ✗ | L1 |
| 41 | `show ip pim neighbor` / `show ip pim interface`(DR)/ `show ip pim rp mapping` | △ g_pim | ✗ | L1 |

## ラボ段階(参考・BL-077)

- L1: PIM-SM static RP・IGMP join で受信・`show ip mroute` で木を確認
- L2: BSR/Auto-RP・SSM・SPT 切り替え
- L3: TS(RPF 失敗・RP 不一致・PIM 無効の IF・boundary・snooping)
