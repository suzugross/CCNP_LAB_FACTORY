# CLOZE-PAPER — 解説穴埋め形 紙面ファミリ(shape=cloze) 設計書

- 起票: BL-191(2026-09-19)・同日着手
- 目的: **問題を解きながら解説を頭に入れる**。1 問 = 書き下ろしの技術解説文 1 本に空欄 4 つ。
  解き終えた時点で「正しい説明文」が 1 本残る。採点後に提示する完成文がそのまま解説になる。
- 第 1 弾: MPLS(ENARSI 1.9 「MPLS operations」/ 1.10 「MPLS L3VPN」= describe レベル)。
  ユーザ要望により **MPLS は用語・機構をコンテキストごと厚く**扱う。
- 知識源: 公式コンフィグレーションガイド(IOS XE 17.x MPLS / L3VPN / TE)で裏取りした事実のみ採用。
  裏取りできない・機種依存の数値(ラベル既定レンジ等)は**使わない**(svc ファミリの前例= 不確かな項目は捨てる)。

## 1. 出題形式

```
次の説明文の空欄 [1]〜[4] に入る語を語群から選んでください。

<解説文 6〜12 行。空欄 [1]..[4] を含む。空欄にしなかった候補箇所は正しい語を埋めた状態で表示>

語群:
 A. …  B. …  C. …  D. …  E. …  F. …  G. …  H. …
```

- 語群 8 語 = 正解 4 + 誤答 4。誤答は各空欄の**対概念**(RD⇄RT・LDP ラベル⇄VPN ラベル・P⇄PE・UDP⇄TCP・DU⇄DoD…)から 1 つずつ採る。
  → 消去法で埋まらないよう、語群内の 8 語すべてが文中のどこかの空欄で「もっともらしい」よう構成する。
- **1 語 1 空欄**(同じ字を 2 か所に使わない)。出題文にその旨を明記。
- Config 穴埋め kind は、設定例(exhibit)の中の `[n]` と、その下の説明文の `[n]` を混在させる(例題 4 の形)。
- 図: MPLS のラベル転送・役割 kind には Mermaid で PE/P/CE の直列図を付ける(BL-187 と同じ経路で question_body 先頭)。

## 2. 解答・採点

- 解答 = 空欄ごとに 1 字。表記 `[1]=A [2]=C [3]=D [4]=E`(パック解答欄はプルダウン or ラジオ×4 行)。
- 採点 = 空欄ごとに正誤。**4/4 で正解**、それ以外は誤答(部分点はノルマ集計には載せない・表示だけ「3/4」を出す)。
- 紙面 2 段階ルール(CLAUDE.md)はそのまま: 全問正解→完成文+補足解説を即提示 / 誤答あり→正解率と問番号のみ。
  cloze の「解説」= 完成文 + 各空欄の**なぜ対概念ではないか**1〜2 行。

## 3. 生成器の構造(`topologies/gen_paper_cloze.py`)

```
PASSAGES[topic][kind] = [Passage, ...]
Passage = {
  "title": "…", "kind": "…", "diagram": <mermaid or None>,
  "exhibit": <config text with {slot} placeholders or None>,
  "text":    "… {s1} … {s2} … {s3} …",     # 候補箇所 6〜10
  "slots": { "s1": Slot(answer, distractors=[…], accept=[…同義…]), … },
  "vars":  { "asn": (65000,65100,…), "vrf": ("CUST_A","BLUE",…), … }   # seed で値を振る
}
```

生成手順(seed 決定的):
1. topic/kind/passage を抽選(`--kinds` で絞れる)。`vars` を抽選して本文・exhibit に埋める。
2. 候補箇所から **4 つ**を空欄化。残りは正解語を埋めて表示(= 読む量を確保しつつ文脈ヒントにもなる)。
3. 語群 = 4 正解 + 空欄ごとに対概念 1 つ。**一意性検査**: 語群の各語について「その語で意味が通る空欄」が
   正解の 1 か所だけであること(Slot.accept に同義語を持たせ、他空欄の accept に被る誤答は差し替え)。
4. 語群をシャッフルして A〜H を振る。
5. selftest: 全 passage × 空欄組合せ × N seed で一意性と「同一語 2 空欄」ゼロを機械確認。

## 4. MPLS 第 1 弾の kind と知識マップ

| kind | 解説文の主題 | 空欄候補(対概念) |
|---|---|---|
| `m_roles` | CE/PE/P の役割と境界(顧客経路を持つのは PE だけ・P はラベルだけ・CE は MPLS を知らない) | CE⇄PE⇄P, VRF⇄グローバル表, IGP+LDP⇄MP-BGP |
| `m_terms` | RD/RT/VPNv4 の定義と役割分担(RD=一意化 8B・VPNv4=RD+IPv4 12B・RT=拡張コミュニティで取り込み制御) | RD⇄RT, 8⇄12 バイト, import⇄export, 拡張⇄標準コミュニティ |
| `m_stack` | 2 段ラベルスタックと転送(先頭=トランスポート/LDP・底=VPN/MP-BGP・P は先頭だけ swap・出口 PE は VPN ラベルで VRF 決定) | LDP⇄VPN ラベル, push/swap/pop, 先頭⇄底, S ビット |
| `m_php` | PHP と予約ラベル(imp-null 3=手前で pop・explicit-null 0=UHP で QoS/EXP 保持・router alert 1) | 3⇄0⇄1, 手前(penultimate)⇄最終(ultimate), pop⇄swap |
| `m_tables` | 4 表の役割(RIB→FIB / LIB→LFIB・制御プレーン⇄転送プレーン・show 対応: `show mpls ldp bindings`=LIB / `show mpls forwarding-table`=LFIB) | LIB⇄LFIB, RIB⇄FIB, 全バインディング⇄最良のみ |
| `m_ldp_sess` | LDP セッション確立(Hello UDP 646 → 224.0.0.2・セッション TCP 646・トランスポートアドレス大がアクティブ・Hello 5s/hold 15s・Targeted Hello=非隣接) | UDP⇄TCP, 大⇄小, Basic⇄Extended Discovery, Link⇄Targeted Hello |
| `m_ldp_dist` | ラベル配布モード(DU 既定=要求なしで配布・DoD=要求時のみ)とラベルバインディングは FEC 単位・LDP router-id の選出順 | DU⇄DoD, FEC⇄プレフィックス, Loopback 最大⇄物理 IF 最大 |
| `m_ldp_ha` | LDP セッション保護(Targeted Hello adjacency をバックアップに持つ・リンク復旧後の再学習不要・`mpls ldp session protection`・duration 既定 infinite)/LDP-IGP 同期(LDP 未確立リンクに max-metric・`mpls ldp sync` under router ospf/isis・holddown 既定は無限待ち)/Autoconfig(OSPF/IS-IS の全 IF に LDP) | セッション保護⇄IGP 同期⇄autoconfig, max-metric⇄shutdown, OSPF/IS-IS⇄EIGRP |
| `m_rsvp` | RSVP-TE の動作(headend が PATH を下流へ・tailend が RESV を上流へ返しラベルは RESV で下流から割当・ERO で明示経路・CSPF が帯域/affinity 制約で計算・LDP との対比=LDP は IGP 最短路に追随し帯域予約なし) | PATH⇄RESV, 上流⇄下流, ERO⇄RRO, CSPF⇄SPF, LDP⇄RSVP-TE |
| `m_frr` | MPLS-TE Fast Reroute(PLR が事前に用意した backup tunnel へ局所切替・NHOP=リンク保護・NNHOP=ノード保護・NNHOP 優先・RRO で保護状態を headend へ・`tunnel mpls traffic-eng fast-reroute` / `mpls traffic-eng backup-path`) | NHOP⇄NNHOP, リンク⇄ノード保護, PLR⇄MP, headend⇄midpoint |
| `m_mpbgp_cfg` | **MP-BGP 設定例の穴埋め**: `address-family vpnv4`(PE-PE iBGP・activate・send-community extended)/`address-family ipv4 vrf X`(PE-CE eBGP or redistribute)/ `vrf definition`+`rd`+`route-target`/ update-source Loopback0・next-hop は PE Loopback /32 が IGP+LDP で到達 | vpnv4⇄ipv4 vrf⇄ipv4 unicast, activate⇄next-hop-self, extended⇄standard, PE-PE⇄PE-CE⇄P |
| `m_flow` | 経路伝搬の一連の流れ(CE→PE VRF RIB→export RT 付与→VPNv4 表→MP-iBGP→import RT 判定→対向 VRF RIB→CE)と対応する show(`show ip bgp vpnv4 all` / `vrf X` / `show ip route vrf X`) | export⇄import, VPNv4 表⇄VRF RIB, all⇄vrf |
| `m_label_mode` | VPN ラベル割当(既定 per-prefix・per-vrf は VRF に 1 ラベル= 出口で IP 再検索・`mpls label mode … per-vrf`・`show ip bgp vpnv4 all labels`) | per-prefix⇄per-vrf, ラベル検索⇄IP 検索 |
| `m_label_hdr` | ラベルヘッダの中身(32bit= 20/3/1/8)・動的ラベルは 16 以上・TTL 伝搬の既定と `no mpls ip propagate-ttl forwarded`(顧客 traceroute に P が出ない)・1 ラベル 4 バイトと `mpls mtu` | TC⇄DSCP, S⇄TTL, forwarded⇄local, 4⇄8 |
| `m_reserved` | 予約ラベル表(0=IPv4 exp-null/1=Router Alert/2=IPv6 exp-null/3=imp-null・7/13/14 は解説のみ)・既定広告は imp-null→PHP・exp-null で UHP(TC 保持)・LFIB の `Pop Label` | 0⇄3⇄1⇄2, PHP⇄UHP, Pop Label⇄No Label |
| `m_ldp_msgs` | 4 メッセージ種別(Discovery/Session/Advertisement/Notification)・セッション保持 180s/KA 60s・Targeted Hello 10s/90s・Liberal Retention/Independent Control 既定・MD5 | Discovery⇄Session⇄Advertisement, 180⇄90, liberal⇄conservative, independent⇄ordered |
| `m_ldp_show` | `show mpls ldp neighbor detail` の読解(Peer/Local Ident と :0=プラットフォーム全体・TCP 646 側=パッシブ/一時ポート側=アクティブ・Downstream=DU・Addresses bound to peer と RIB ネクストホップの突合) | パッシブ⇄アクティブ, 大⇄小, DU⇄DoD |
| `m_lfib_read` | `show mpls forwarding-table` の読解(Pop Label=imp-null 受信/swap の Outgoing 値/No Label=LSP の穴/[V]=VRF/Aggregate=IP 再検索) | Pop⇄No Label⇄Aggregate, [V]⇄[T] |
| `m_te_cfg` | **TE 設定例の穴埋め**(全ルータ `mpls traffic-eng tunnels`+IF `ip rsvp bandwidth`/OSPF `mpls traffic-eng router-id`+`area`/ヘッドエンドの Tunnel: path-option explicit/dynamic・autoroute announce・単方向) | ip rsvp bandwidth⇄bandwidth, te router-id⇄ldp router-id, explicit⇄dynamic, autoroute⇄forwarding-adjacency |
| `m_te_signal` | RSVP-TE のオブジェクト(PATH: ERO/SENDER_TSPEC/LABEL_REQUEST/SESSION_ATTRIBUTE・RESV: LABEL/RRO)・ソフトステート 30s・setup/hold 0〜7 とプリエンプト・attribute-flags と affinity | ERO⇄RRO, TSPEC⇄FLOWSPEC, LABEL_REQUEST⇄LABEL |
| `m_te_routing` | トラフィック誘導(autoroute announce=ヘッドエンドのみ/forwarding adjacency=IGP に広告/静的)・CSPF 既定は TE メトリック(`administrative-weight`・`path-selection metric igp`)・再最適化 3600s・make-before-break | autoroute⇄FA, TE⇄IGP メトリック, 3600⇄30, MBB⇄BBM |
| `m_ldp_vs_rsvp` | LDP(IGP 最短路に追随・帯域予約不可・敷き詰め型)と RSVP-TE(トンネル単位・帯域/明示経路/優先度/FRR・状態が増える)の対比・ラベル方向は共に下流→上流・VPN ラベルは MP-BGP | できる⇄できない, FEC⇄トンネル, MP-BGP⇄LDP |
| `m_pece` | PE-CE プロトコルの決め所(eBGP: as-override / allowas-in・OSPF: sham-link=バックドア対策で Type-1 のまま・EIGRP: SoO)※既存 mpls ファミリと被る部分は用語側に寄せる | as-override⇄allowas-in, sham-link⇄virtual-link, Type-1⇄Type-3 |

数値で使うもの(裏取り済): ラベル 20bit・予約 0〜15・imp-null=3・exp-null(IPv4)=0・router alert=1 /
LDP 646(UDP=Hello, TCP=Session)・224.0.0.2・Link Hello 5s/15s・Targeted Hello 10s/90s・セッション保持 180s/KA 60s / RD 8B・VPNv4 12B / RSVP リフレッシュ 30s・優先度 0〜7(既定 7 7)・再最適化 3600s / TTL 伝搬既定 ON・forwarded/local /
FRR は NNHOP 優先・duration 既定 infinite。**採用しない**: ラベル既定レンジ上限・EXP/TC 名称の版差・50ms 収束(機種依存と明記あり)。

## 4b. 第 2 弾 IPv6 First Hop Security(BL-193・2026-09-19)

`topologies/cloze_kb_ipv6fhs.py`。範囲= ENARSI 4.x の describe(RA guard/DHCP guard/binding table/ND inspection・snooping/source guard)。
知識源= 公式 FHS 設定ガイド(IOS XE 17)＋ poc/fhs/README.md(ioll2 実測: ポート>VLAN・VLAN だけ host で GW も落ちる・既定値は running-config に出ない・Dropped 理由文字列)。

| kind | 主題 | 対概念 |
|---|---|---|
| `f_attacks` | 攻撃と機能の対応(偽 RA→RA guard/偽 DHCPv6→DHCPv6 guard/ND 偽装→snooping→表→ND inspection・source guard) | 検査する側⇄表を作る側⇄表を使う側 |
| `f_ndmsgs` | ND メッセージ(RS133/RA134/NS135/NA136/Redirect137)と DHCPv6(546/547・ff02::1:2)・M/O フラグ・RA guard は RA と Redirect | RS⇄RA⇄NA, 546⇄547, M⇄O |
| `f_raguard` | ポリシー設定例(host/router・router-preference maximum・match ra prefix-list・trusted-port・ingress のみ・VLAN 適用と over-block・ポート>VLAN) | host⇄router, ポート⇄VLAN |
| `f_dhcpguard` | 設定例(client/server・match server access-list・preference min/max)・ADVERTISE/REPLY だけ破棄・role 誤りの症状(DNS だけ欠ける)・理由文字列 device-role mismatch | client⇄server, RA guard の語彙との混同 |
| `f_binding` | `show device-tracking database` 読解(Codes ND/DH6/S・REACHABLE)・17.x は SISF device-tracking・表が無いと source guard は全断 | ND⇄DH6, 作る側⇄使う側 |
| `f_ndinsp` | device-tracking policy(security-level glean/guard/inspect・limit address-count)・ND スプーフィング対策・単独では偽 RA を止めない | glean⇄guard⇄inspect |
| `f_srcguard` | データの送信元を表で検証・ND/DHCP は見ない・表が要る・拒否時は DHCP 照会/ND で復元・permit link-local / deny global-autoconf・prefix guard・IPv4 の IP Source Guard 相当 | データ⇄ND, IPSG⇄DAI⇄uRPF |
| `f_deploy` | 展開順(表→制御→データ)・GW 側 router/server・端末側 host/client・確認 show・症状からの逆引き(LL だけ/DNS だけ) | 役割の組合せ |
| `f_counters` | `show device-tracking counters interface` の Dropped 理由読解(unauthorized on port= role 誤り/Preference flag error= 上限低すぎ)・是正 | 理由文字列⇄原因⇄是正 |
| `f_beyond`(scope=beyond) | destination guard・RFC 7113(断片化 ND の破棄) | 範囲外 |

selftest 2040 NG0(範囲内 30 kind / 範囲外 4)。quota ジャンル= `genres.yml` に `cloze/f_*` → security。初出題= PACK-TEST-CLOZE4(6 問)。

## 4c. 第 3 弾 AAA と認証サーバ(BL-194・2026-09-19)

`topologies/cloze_kb_aaa.py`。範囲= ENARSI 4.1 IOS AAA(TACACS+/RADIUS/ローカル DB)。802.1X は扱わない。
知識源= poc/aaa/README.md(実測: Reject は local に落ちない 1.1s・無応答は 3s×2×2 台= 約 12.5s で落ちる・key 不一致と source-interface 欠落は機器側同一・
`aaa authorization exec` 無しは priv 1 固着・認可フォールバック無し×全断= 全員拒否・未定義リスト= default 挙動・dead-criteria 無しで deadtime 無効・enable via RADIUS は `$enab15$`)＋公式ガイド(RADIUS UDP 1812/1813・パスワードのみ暗号化・一体 / TACACS+ TCP 49・ボディ全体暗号化・分離・コマンド認可)。

| kind | 主題 |
|---|---|
| `a_compare` | RADIUS vs TACACS+ 対比表(トランスポート/暗号化範囲/分離/コマンド認可/AVPair shell:priv-lvl) |
| `a_methods` | メソッドリストの意味論(aaa new-model・default と名前付き・最大 4・**拒否は権威/無応答だけ次へ**・local-case・未定義名= default・none) |
| `a_cfg_radius` | RADIUS 設定例(radius server/address/key・group・ip radius source-interface と unknown client・dead-criteria・local フォールバック・authorization console) |
| `a_cfg_tacacs` | TACACS+ 設定例(commands 認可はコマンドごと・config-commands・if-authenticated・accounting start-stop・TCP 49) |
| `a_authz` | 認可の 3 事故(exec 認可無し= priv 1 固着・フォールバック無し×全断= 全員拒否・認可 Reject= EXEC 拒否・console 認可・サーバ属性優先) |
| `a_timing` | test aaa の 3 文言と秒数(0.1/1.1/12s= 3×2×2)・拒否と無応答でログインの見え方が変わる・鍵不一致は Response Authenticator 検証失敗で「無応答」に見える・決め手はサーバログ |
| `a_servers` | dead-criteria と deadtime(片方だけでは無効)・show aaa servers の DEAD・DEAD 後は 2 台目分 6 秒・非標準ポート可・DEAD は到達性 |
| `a_accounting` | exec/commands/network/system・start-stop/stop-only/wait-start・1813・コマンド記録は TACACS+・記録は操作を妨げない |
| `a_enable` | enable 認証をサーバへ(RADIUS は `$enab15$`・`% Error in authentication.`・末尾 enable は無応答時のみ・原則は共通) |

selftest 2580 NG0(範囲内 39 kind / 範囲外 4)。quota= `cloze/a_*` → security。初出題= PACK-TEST-CLOZE5(6 問)。

## 4d. 「正解が動く」世界(world)機構(BL-195・2026-09-19)

ユーザ質問「バリエーションで正解が変わる仕掛けはあるか」→ 無かったので追加。

- **schema**: passage に `worlds: [名]`・`world_desc: {名: 説明}`。slot の `a`/`d`/`ok`/`why` と `exhibit`/`text`/`vars` は world 別 dict にできる(`_pick`)。
  `keep: [slot]` は空欄にしない(世界を示す事実を必ず見せる)。`vars` の値に callable `f(vals, world) -> str` を許し導出値を作る(例: 待ち秒= timeout×(1+retransmit)×2)。
- **誤答の自動生成**: slot の `a` が dict のとき、他 world の正解語を誤答候補に自動追加(対概念が自然に錯乱肢になる)。
- **selftest 追加**: 同じ空欄集合で他 world を描いたとき見える部分がどこかで違うこと(= 世界が本文から一意に読める)。
- **適用済み**: `f_raguard`(router/host/vlan_only: GW の RA の行方・端末の症状・Dropped 理由・是正が動く)・
  `a_methods`(group→local / local→group / group のみ: local だけのユーザ・サーバだけのユーザ・全断時の結果が動く。`keep=methods`)・
  `a_timing`(timeout 3/5 × retransmit 1/2 → 待ち秒と式が動く)・`m_lfib_read`(swap 先ラベル値が表に従う)。
- 答案 md の解説冒頭に「この盤面の世界: …」を出す。selftest 2580 NG0。初出題用 PACK-TEST-CLOZE6(4 問)。
- **横展開(BL-196・同日)**= `f_dhcpguard`(ok/swapped/none_edge: 正規応答と偽応答の行方・症状・理由・是正)・`f_counters`(role/pref/ok: 原因・是正・症状)・
  `a_authz`(ok/no_exec/no_fb: 各ユーザの権限・全断時の結果・評価)・`a_servers`(crit/nocrit: State・理由・待ち秒・評価)・
  `m_ldp_show`(peer_passive/local_passive: パッシブ/アクティブ側が入れ替わる・world 別 vars)・`m_label_hdr`(段数 2/3 で合計バイトを導出)。
  世界あり= 10 kind / 導出値= 3 kind。selftest 2580 NG0。初出題用 PACK-TEST-CLOZE7(6 問)。
  ★書き方の学び= 世界別の正解語が本文の別所に素で出やすい(例:「DEAD」「15」)→ 正解語に短い補足を付けて一意な字面にする(「DEAD(スキップ対象)」)。

## 4e. 順番・レベル系(空欄 5〜6・BL-197・2026-09-20)

ユーザ要望「CCNP でよく問われるルールの順番系を、4 つではなく 5 つ以上の穴埋めで」。

- driver: passage 単位の `n_blanks`(既定 4・上限 7)。語群 8 のうち残り(2〜3)が誤答。設問文の「①〜④」は空欄数に追随。
- `topologies/cloze_kb_order.py`(topic=order): `o_bgp`(ベストパス 12 段・n=6)・`o_syslog`(重大度 0〜7 + 既定 con/mon/buf=7・trap=6・n=6)・
  `o_prec`(precedence 0〜7 の名称 + CS=×8・EF=5・AF31=3・n=6)・`o_ad`(AD 既定値 10 行 + 大小/EIGRP 外部/iBGP の理由・n=6)。
- 作法= 順序表の全項目に**共通の誤答候補**(表に無いもっともらしい語)を持たせる。空欄にならなかった項目は表に見えるので誤答に使えない。
  1 文字〜数字の正解(255/7/6)は本文に素で書かない(露出検査が効かない)。
- genre= o_bgp→bgp / o_syslog・o_prec→services / o_ad→igp。selftest 2820 NG0(範囲内 43 kind)。初出題= PACK-TEST-CLOZE8(4 問)。
- 候補(未実装)= OSPF 経路種別の優先順(O > O IA > E1 > N1 > E2 > N2)・EIGRP の K 値と複合メトリック・STP のルート選出順。

## 4f. 本文内プルダウンと Markdown 表(BL-198・2026-09-20)

- `render_html.render(inline_blanks={丸数字: <select>})`: 本文(表のセル・設定例の pre・説明文)の ［①］ をその場でプルダウンに置換。同番号の 2 回目以降は `span.bmirror` が選択値を映す。
- JS: `select.msel` の収集/復元を文書全体に拡張・本文中の change でも自動保存・`mirror()` で鏡と解答欄の要約 `.clsum`(「①A　②F …」)を更新。解答欄には案内と要約だけ。
- 生成器: passage `exhibit_md: True` で exhibit を Markdown 表としてそのまま出す(code fence に包まない)。順序表 4 本と m_reserved/a_compare/f_ndmsgs を変換。
- 答案 md の書式・採点(match_of)は不変。

## 4g. 数値デコイの保証(BL-199・2026-09-20)

- 空欄 5 以上の passage は語群 10(A〜J)。`_build_pool` は数値の正解を持つ空欄に先に数値デコイを配り、残りは空欄を巡回。
- selftest: 数値の空欄には正解でない数値が語群に 1 つ以上。
- 作問側の作法: 数値スロットの `d` には必ず数値の候補を 2 つ以上書く(例: cs_mult 8 → 4/2、ef_prec 5 → 6/4)。

## 4h. 逆引き形「何番目/何番か」(BL-200・2026-09-20)

- 順番系 4 kind に 2 本目の passage を追加。項目を順不同の箇条書きで並べ、各行の番号を空欄にする。語群は数字だけ(正解 + 残りの番号がデコイ)。
- 表形と逆引き形は同じ kind の passage 抽選(半々)。空欄にならなかった行は番号が見えるので手掛かりになる(部分知識で詰める余地を残す)。
- 数値の範囲が狭い syslog/precedence(0〜7)は n=5・pool 8。BGP(1〜12)/AD(10 値)は n=6・pool 10。
- 数字は本文に素で書かない(「全 12 段」で露出検査に引っかかった)。

## 4i. 消去法 1 択の機械排除(BL-201・2026-09-20)

- 原則: **どの空欄にも、語群の中に「その空欄用の誤答」か「同じ種類の別の空欄」がある**。無ければその語群は採用しない。
- 実装: slot に `grp`(同種の項目群。順序表の項目・予約ラベル値など)。`_build_pool` の covered()= 自分の d が語群にある or 同 grp の別空欄がある。
  数値の空欄は正解でない数値が語群に 1 つあればよい(全数値空欄で共有)。
- 作問の作法: 表以外の「説明スロット」(例: ORIGIN の順・MED の比較範囲・trap の既定)は必ず d を 2 つ以上書く。d が空で grp も無い slot は selftest で落ちる。

## 4j. 第 4 弾 Services の設定構造: SNMPv3・NetFlow/FNF・top-talkers(BL-202・2026-09-20)

- 契機= ユーザ質問「他にこの形式で埋めるべき単元は? SNMP や NetFlow(フレキシブル・top-talkers 含め)か」→ 推奨どおり SNMPv3+FNF を先に実装(DMVPN+IPsec は次)。
- 実装= `topologies/cloze_kb_svc.py`(kind 接頭辞 `s_`・genre services= `records/genres.yml` に `"cloze/s_*"`)。9 kind:

| kind | 形 | 内容 | 事実の出所 |
|---|---|---|---|
| `s_snmp_levels` | 表(空欄 5) | noAuthNoPriv/authNoPriv/authPriv × 守られるもの × group/host のキーワード(noauth/auth/priv)+ group= 最低レベル・弱い要求= authorizationError・鍵は engineID で局所化 | poc/svc-paper・公式 CR(engineID) |
| `s_snmp_cfg` | 設定例(空欄 5) | view→group→user→host の**名前の参照鎖**(空欄は参照先の名前・sha/aes)+ access= 送信元制限・user 行は running-config に出ない・161/162・enable traps 引数なし= 全種 | gen_snmpv3_ts の正規構文・poc/svc-paper |
| `s_snmp_resp` | 世界 4(空欄 4) | 管理ステーション側の設定 1 か所が違う盤面 → 応答(Wrong digest / 無応答 / authorizationError / Unknown USM user)・原因・是正が世界で変わる。USM の処理順(ユーザ名→認証→復号)・show snmp user | poc/svc-paper 実測表 |
| `s_snmp_notify` | 表(空欄 5) | trap vs inform(確認応答・再送・負担・バージョン・162)+ host の version 省略= v1 trap・informs キーワード・version 3 の後ろ= レベル+ユーザ | poc/svc-paper |
| `s_snmp_comm` | 設定例(空欄 4) | RO/RW・ACL 不許可= 無応答・**未定義 ACL= 全許可**・show snmp のカウンタ(Unknown community name / Illegal operation)・コミュニティは平文表示 | poc/svc-paper |
| `s_fnf_parts` | 設定例(空欄 5・世界 in/out) | record(match/collect)→ exporter(destination/source/transport/export-protocol)→ monitor(exporter/record)→ IF(input/output)。キーワード穴埋め+役割+既定 netflow-v9+cache 確認 | ENCOR-FNF-01・gen_fnf_ts |
| `s_fnf_change` | 操作ログ(空欄 4) | 使用中 record のロック(% Object is in use)・IF から外しても解錠されない・monitor の record は上書き不可・exporter は export-protocol だけ参照中不可・構築順 | gen_fnf_ts の IOL 実測(2026-07-25) |
| `s_nf_versions` | 表(空欄 5) | v5(固定・IPv4 のみ・ip flow ingress) / v9(テンプレート・RFC 3954) / IPFIX(RFC 7011)・FNF 既定 netflow-v9・従来の 7 キー・show ip cache flow | 公式ガイド |
| `s_nf_top` | 設定+show(空欄 5) | `ip flow-top-talkers` 配下 top/sort-by・前提 ip flow ingress・`show ip flow top-talkers`(N of M top talkers shown)・ローカルのキャッシュ操作・FNF は `cache sort highest counter bytes`(top <n>)・sort できるのはレコードにある項目だけ | 公式 NetFlow ガイド(Top Talkers・FNF Top N) |

- 範囲の判断= 3.2 SNMP(v2c, v3)・3.6 NetFlow(v5, v9, flexible) は describe/troubleshoot の範囲内。top-talkers は ENCOR 側の題材だがユーザ要望で採用(scope は beyond にしない)。
  inform の再送回数・タイムアウトの既定値は未計測なので数値を出さない(「回数・間隔は設定可」まで)。
- 作問で当たった罠= `s_nf_top` の FNF sort 例に `top {n}` を含めると、`top` を空欄にした回で本文に露出する(selftest 検出)→ 例から `top <n>` を外し「末尾に件数の指定を付けて絞る」と書いた。
- 検証= selftest 3360 件 NG0(範囲内 52 kind)・実生成 20260920-017〜025(9 kind 各 1)・`packs/PACK-TEST-CLOZE10`(9 問・--extra-paper)で表/設定例のプルダウン描画を確認。
- 次候補(§5)= DMVPN Phase 比較+IPsec → uRPF/IPv6 ACL/CoPP → OSPF LSA/ネットワークタイプ/隣接状態 → BGP 状態遷移・属性分類 → シードメトリック/K 値 → IPv6 マルチキャスト/DHCP オプション(2026-09-20 提案の優先順)。

## 4k. 第 5 弾 DMVPN Phase 1/2/3 比較＋IPsec(BL-203・2026-09-20)

- 契機= ユーザ指示「DMVPN Phase 比較+IPsec お願いします」(第 4 弾直後)。範囲= ENARSI 2.3 DMVPN(GRE/mGRE・NHRP・IPsec・dynamic neighbor・spoke-to-spoke)。IKE/ESP の基礎は DMVPN を守る文脈で扱う。
- 実装= `topologies/cloze_kb_dmvpn.py`(kind 接頭辞 `d_`・genre vpn= `"cloze/d_*"`)。10 kind(11 passage):

| kind | 形 | 内容 | 事実の出所 |
|---|---|---|---|
| `d_phases` | 表(空欄 6) | Phase 1/2/3 × スポークのトンネル・スポーク間経路・持つ経路・ハブ/スポークの追加設定・OSPF タイプ + 「集約できない/できる理由」(きっかけ= next-hop vs Redirect) | 教材(範囲確認)・DMVPN-POC-01/PHASE3-01 実測 |
| `d_nhrp` | 解説文(空欄 5) | NBMA/NHS/Registration/Resolution/Redirect(Traffic Indication)・holdtime 既定 7200・network-id はローカル有意・authentication 8 文字・tunnel key | IOSv/IOL 実測・公式 |
| `d_spoke_cfg` | 設定例(空欄 5) | Phase 3 スポークの Tunnel(mtu/mss・nhs 1 行形の multicast・shortcut・multipoint)+ 役割説明 | ENARSI-DMVPN-IPSEC-01 |
| `d_hub_cfg` | 設定例・**世界 p2/p3**(空欄 5) | ハブ Tunnel: map multicast dynamic / Phase を決める行(no ip next-hop-self ⇄ ip nhrp redirect) / no split-horizon。スポーク抜粋の shortcut 有無で世界を読む。next-hop・集約可否が世界で変わる | DMVPN-POC-01(P2)/PHASE3-01(P3) |
| `d_routing` | 表(空欄 5) | EIGRP(split-horizon/next-hop-self/summary) vs OSPF(network type・DR・集約)・p2mp は next-hop 書換・スポーク DR の弊害・Tunnel 既定 p2p | 教材(範囲確認)・公式 |
| `d_ipsec_chain` | 設定例(空欄 5)×2 passage | IKEv2 形(proposal→policy→keyring→ikev2 profile→ipsec profile→tunnel protection・wildcard・transport・set ikev2-profile 忘れ)/ IKEv1 形(isakmp policy・key address 0.0.0.0・transform-set・profile・crypto map との違い・keepalive=DPD) | ENARSI-DMVPN-IPSEC-01・IPSEC-VTI-01・GREIPSEC-MAP-01 |
| `d_ike_phases` | 表(空欄 6) | IKE フェーズ 1/2(SA・交渉内容・モード・確認コマンド・IKEv2 の対応)+ UDP 500/4500・ESP 50/AH 51・tunnel/transport | 公式・定数 |
| `d_show` | show 読解・**世界 ike/nhrp/up**(空欄 4) | `show dmvpn` の State で層を割る(IKE→NHRP→UP)・次の一手・Attrb S/D/DT1/DT2/X・IX/DX= per-peer keyring | IOSv/IOL 実測(2026-07-09・09-18) |
| `d_mtu` | 解説文(空欄 4・数値) | GRE 4(+key 4)・既定 1476・定石 1400/1360・adjust-mss の仕組み・断片化の害・実測(未設定でも ping は通る) | PoC 実測・[[ccnp-dmvpn-grading-mtu-note]] |
| `d_overlay` | 解説文(空欄 4) | 再帰ルーティング(RECURDOWN は p2p のみ・mGRE は 15 秒フラップ)・map multicast の引数は NBMA・shared・protection 変更で自動 shutdown・fVRF | IOSv/IOL 実測 |

- 作問で当たった罠= ①`d_spoke_cfg` の本文に「ip nhrp map multicast」と書くと `multicast` 空欄の回で露出(語を slot 参照に置換) ②本文に「正解」の語があると gen_paper_mcq の漏えい検査で生成が止まる(「定石」に変更)。 ③初出題(PACK-TEST-CLOZE11 Q11)で `d_nhrp` の認証スロット「ip nhrp authentication は［ ］で、値が一致しないと…」に network-id 用デコイ「両端で一致が必要」が意味的に嵌まった(解答者の初回答)→ 空欄を「文字列の長さは［ ］」に限定して是正。★教訓= 他スロットのデコイが同じ文に嵌まらないか、空欄の直前の語で属性(長さ・回数・場所)を限定する。
- 数値は裏の取れた定数のみ(500/4500/50/51/1476/1400/1360/7200)。inform 同様、未計測の既定値(NHRP registration timeout の秒数など)は出さない。
- 検証= selftest 3960 件 NG0(範囲内 62 kind)・実生成 20260920-026〜036・`packs/PACK-TEST-CLOZE11`(11 問・--paper-only)。

## 5. 後続展開(このファミリの topic 追加)

- ✅ `ipv6fhs`(BL-193) ✅ `aaa`(BL-194・2026-09-19) ✅ `svc`(SNMPv3/NetFlow・BL-202・2026-09-20) ✅ `dmvpn`(Phase 比較+IPsec・BL-203・2026-09-20) → 次候補= uRPF/IPv6 ACL/CoPP → OSPF LSA・ネットワークタイプ・隣接状態 → BGP 状態遷移・属性分類 → IP SLA の設定構造(svc に追加)。
- パック: **専用の穴埋め枠 `gen_pack --cloze`(既定 5)** で毎パックに混ぜる(2026-09-19 ユーザ指示「新規ジャンルとして 5 問程度」)。思考系(kbthink)・瞬発力枠には入れない。slot=cloze・status「(穴埋め)」。

## 6. 進捗

- 2026-09-20(夜): **第 5 弾 DMVPN+IPsec(BL-203)**= `cloze_kb_dmvpn.py` 10 kind/11 passage(§4k)。世界= d_hub_cfg(Phase 2/3)・d_show(IKE/NHRP/UP)。selftest 3960 NG0。実生成 20260920-026〜036・PACK-TEST-CLOZE11(11 問)。
- 2026-09-20(夕): **第 4 弾 Services(BL-202)**= `cloze_kb_svc.py` 9 kind(§4j)。裏取り= Cisco 公式(Top Talkers 構成ガイド・FNF Top N・snmp-server engineID)+ poc/svc-paper + gen_snmpv3_ts/gen_fnf_ts の実測。selftest 3360 NG0。実生成 20260920-017〜025・PACK-TEST-CLOZE10(9 問)。是正= FNF の export-protocol は netflow-v5 も指定可(初稿の「指定できない」を訂正)。
- 2026-09-19: 起票・設計・公式ドキュメント裏取り(LDP session protection / IGP sync / FRR / per-VRF label)。
- 2026-09-19(同日): 実装完了・E2E 済。
  - 実装= `topologies/gen_paper_cloze.py`(ドライバ)+`topologies/cloze_kb_mpls.py`(MPLS 知識ベース 15 kind: m_roles/m_arch/m_terms/m_stack/m_php/m_tables/m_ldp_sess/m_ldp_dist/m_ldp_ha/m_rsvp/m_frr/m_mpbgp_cfg/m_flow/m_label_mode/m_pece)。
  - 配管= §1 の `[1]..[4]` は **①〜④** に変更(BL-168 組合せ形の `match_terms`/`match_of`/`match_key_of` をそのまま流用するため)。
    設問直後に `### 対応させる項目` 表(空欄①〜④)・語群は `## 選択肢` A〜H・正解行 `**①－A、②－F…**`。
  - gen_paper_mcq: `KB_FAMILIES`/`KB_TITLES`/`--shape` に登録・形が 1 つしか無い family の既定形を `avail[0]` に(従来は "select" 固定で落ちる)・
    瞬発力枠は `SPEED_KINDS=[]` を明示した family を除外(従来は空リスト→全 kind に化けた)。
  - quota: `paper_shape()` が `shape/kind` を返し、`genres.yml` の shapes に `"cloze/m_*"` のようなパターンを書けるようにした(topic ごとにジャンルが違うため)。
  - gen_pack: `PAPER_GENRES["cloze"]` 追加(`--require-shape cloze`)。
  - 検証= selftest 900 NG0(語群一意性=各語が当てはまる空欄は正解 1 か所のみ・同じ語 2 空欄なし・**正解語が本文の別所に露出しない**(ASCII 語は単語境界))・
    実生成 20260919-039〜041/044〜046・`packs/PACK-TEST-CLOZE`(紙面のみ 3 問)で解答欄と採点経路(正解/3/4 不一致/手書き `①-E、②-F` 書式)を確認。
  - 設計判断= 空欄にしなかった候補箇所は正解語を埋めて表示(読む量と文脈)。1 文 6〜9 候補から seed で 4 つ選ぶので同じ kind でも空欄の組が変わる。
    語群は「正解 4 + 空欄ごとの対概念 1」。一意性が崩れる組は draw 時に引き直す(ValueError→再抽選)。
  - **是正(同日・ユーザ指摘「対応させる項目の存在理由がわからない/本文と選択肢が離れて参照しづらい」)**=
    表を廃止し `render_html.blank_terms()` が本文中の ［①］〜 マーカーから解答欄の行を作る(各行に空欄前後の文脈・設定例の行は丸ごと)。
    本文(図・設定例・解説文)は `## 設問` の直下に置き、直後に `## 選択肢`(語群)が来る並びにした。`match_terms()` は表が無いときこの経路に落ちる。
  - **初出題(PACK-TEST-CLOZE・m_roles/m_mpbgp_cfg/m_pece)= 3/3 正解・各 3.5〜4.5 分**。講評の宿題= BL-192。
  - **拡張(同日午後・ユーザ要望「LDP/RSVP-TE/TE/ラベルの中身と番号を充実」)= 9 kind 追加で計 24 kind**(上表)。
    追加時の学び= ①read 系(exhibit を読む kind)は正解語が exhibit に載っていてよいので露出検査は**解説文だけ**を対象にした
    ②1 文字の正解(ラベル値 0/3 など)は露出検査が効かないので本文から「値 0」「(3)」等の手掛かりを手で除く(個別チェック済)
    ③show 出力の値を正解にする場合、同じ値が本文の別所(「ローカルラベル 18 の行」)に出やすい→ 表の値を別番号にずらす。
  - **範囲判断(同日・PACK-TEST-CLOZE2 のユーザ所見「後半は ENARSI の範囲を超えている」)**= `m_te_signal`/`m_te_routing`/`m_te_cfg` に
    `scope: beyond` を付け、既定の抽選(KINDS/THINK_KINDS)から除外(範囲内 21 kind)。`--kinds` で明示したときだけ出る。
    根拠= ブループリント 1.9/1.10 は MPLS 動作と L3VPN の describe。RSVP オブジェクト名・setup/hold・affinity・autoroute vs FA・再最適化は範囲外。
    `m_rsvp`(PATH/RESV/CSPF/ERO の基本)と `m_ldp_vs_rsvp`(対比)・`m_frr`(教材の保護節に相当)は範囲内に残す(境界例。ユーザ判断で動かせる)。
    ★教訓= 「充実」は**範囲内の横幅**(用語・show 読解・設定例の文脈)で満たす。深さで満たすと範囲外に出る([[ccnp-above-exam-cognition]] の原則どおり)。
  - **パック統合(同日)**= `--cloze N`(既定 5)を瞬発力枠の後に別レーンとして追加(seed+47000・shape=cloze・avoid-recent-days 4 は共通)。THINK_KINDS=[] にして kbthink との二重出題を防止。PACK-TEST-CLOZE3(穴埋め枠のみ 5 問)で確認。
  - 残= 講評で文章の粒度・難度を調整。topic 追加(§5)。BL-192。**解答欄はプルダウン化済(2026-09-19 ユーザ要望)**= `gen_pack.answer_form` が「対応表なし＋［①］マーカーあり」を穴埋め形と判定し空欄ごとに `<select class="msel">`(option 値は組合せ形と同じ「①D」・表示は「D. 語句」)。`render_html` の JS は select の値も収集/復元。組合せ形(対応表あり)はラジオのまま。
