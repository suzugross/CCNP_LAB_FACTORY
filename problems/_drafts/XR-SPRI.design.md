# XR トラックの SPRI(300-510)対応 — 実現性の調査(BL-256)

2026-10-27 ユーザ依頼「XR 学習セクションが将来 SPRI の内容に対応できるか情報を集める。できなさそうなら何が必要かもまとめる」。
**調査だけ・実装は未着手**。XR トラック本体の設計は [XR-TRACK.design.md](XR-TRACK.design.md)(BL-246)。

**着手の時期(2026-10-27 ユーザ方針)**= トラックの 3 段目。① SPCOR 準拠の単元を M13 まで貯める(BL-246)→
② 単元ごとに SPCOR 向けに充実させる(読み物・ラボ問・紙面問。BL-257)→ ③ SPCOR でやれることがなくなったら SPRI に同じ手順で進む(この BL-256)。
着手時は版を再確認し(§1)、§4.3 の PoC から始める。

根拠の区分= 【公式】Cisco の公式文書／【CML】CML の公式文書／【実測】このリポの実測／【netlab】netlab の自動試験(弱〜中)／
【コミュニティ】Cisco Community の投稿(弱)／【推定】推論。

## 0. 結論

- **今の CML 2.10.1 とホスト(16 コア・空き 47GB)のままで、SPRI の大部分は実機で扱える**見込み。
  盤面は「XRv9000 1 台+XRd 数台+IOL」が基本形になり、XRv9000 の同時 2 台の上限は決定的な壁にならない。
- ただし **今の XR トラックの単元計画(M0〜M13)だけでは届かない**。SPRI の末端 77 項目に対して:

  | 状態 | 項目数 | 中身 |
  |---|---|---|
  | 実践済み | 19 | IS-IS のマルチレベル・RPL の中核・LDP・Unified MPLS・BFD・NSF など |
  | 一部 | 11 | OSPF マルチエリアの TS・RR・マルチホーミング・トラフィックの誘導など |
  | 計画内 | 14 | M10 の SR・TI-LFA と M12 の IPv6 ポリシー(実践の計画 5)、SR-TE・SRv6(**読み物だけの計画** 9) |
  | 空白 | 33 | **マルチキャスト 15 項目すべて**(単元が無い)・BGP の運用機能・BGP PIC/add-path・IPv6 トンネル・RSVP-TE・SR の移行手順など |

- **仮想機ではどの機種でも XR で実機にできない項目**は少数= NAT64/MAP-T と 6to4(XR では不可)・FlowSpec の適用(XRv9000 は制御側のみ)・
  NSR(RP 2 枚が要る)・Tree-SID の複製(未確認)・遅延を実測する SR-TE(仮想機は静的な値のみ)。
  前の 3 つは IOS XE(Cat8000v)側なら実機にでき、残りは読み物と紙面で受ける。
- **必要なもの**= ①単元の追加(8 つ前後・§4.1) ②紙面(SPRI は筆記試験だが XR トラックに紙面が無い・§4.2)
  ③機種の挙動を確かめる PoC(10 項目・§4.3) ④(任意)Cat8000v 17.18 のイメージ・ホストのメモリ増設(§4.4)。
  **新しいライセンスや機材は必須ではない**。

## 1. SPRI の版と範囲

- 現行は **v1.1**(公式の出題範囲 PDF `300-510_SPRI_v1.1.pdf`・2024 年版)と判断。原典の抽出= `private/blueprints/300-510-SPRI-v1.1.txt`(2026-10-27 取得)。
  Cisco の試験ページ(2026-10-27 閲覧)に版・終了日の記載は無く、新版の告知も見つからない。2026-02 の資格改訂(DevNet→Automation 等)に
  SP の変更は含まれていない(二次情報)。**着手前に版を再確認する**。
- 配点= 1.0 ユニキャスト 35%・2.0 マルチキャスト 15%・3.0 ルーティング ポリシー 25%・4.0 MPLS と SR 25%。
- XR トラックの軸の SPCOR(350-501 v1.1)との違い= SPRI は SPCOR のルーティング(2.x)・MPLS/SR(3.x)を深くしたもの。
  加えてマルチキャストのルーティング(SPCOR 4.4 はサービスとしての扱い)・SR-TE と SRv6 の**実装**・FlowSpec・IPv6 移行の比重が上がる。
- 参考: CCIE SP v5.1 の改訂ノート【公式】はラボ機材を仮想機(CSR 17.9・XRv9000 7.x・XRd 7.x)に切り替えており、同時に MAP-T と NG-mVPN を足している。
  → Cisco 自身が SP の主要な論点を仮想機で扱える前提にしている(ただし CCIE の機材は台数の制約が無い)。

## 2. 項目ごとの現状と扱い方

「現状」は今の XR トラック(M0〜M8 追補)と計画(M9〜M13)に対して。「機種」は §3 の調査に基づく見込み。

### 2.1 ユニキャスト(35%・29 項目)

| 項番 | 内容 | 現状 | 機種の見込み | 必要なもの |
|---|---|---|---|---|
| 1.1 | OSPF と IS-IS の比較 | 済(M3・M4 の読み物) | — | 紙面 |
| 1.2.a/b | OSPF マルチエリアの TS(v4/v6)・広告・要約 | 一部(M3= スタブ・完全スタブ・range) | XRd | M3 追補(NSSA・v6 の要約・TS) |
| 1.3.a/b | IS-IS マルチレベルの TS・広告・要約 | 済(M4・M4 追補) | XRd | — |
| 1.4.a・1.5.c | コンフェデレーション | 空白 | XRd | BGP 追補 |
| 1.4.b・1.5.b | ルート リフレクタ | 一部(M8 追補で RR を使う) | XRd(vRR は XRd の本来の用途【公式】) | BGP 追補で TS に |
| 1.5.a | 広告の TS | 済(M6) | XRd | — |
| 1.5.d | マルチホーミング | 一部(XRT-03 の 2 ISP・プリペンド) | XRd | BGP 追補で TS に |
| 1.5.e | TTL セキュリティと AS 間の保護 | 空白 | XRd・IOL ○【netlab】 | BGP 追補 |
| 1.5.f/g | 最大プレフィックス・ダンプニング | 空白 | XRd(要確認) | BGP 追補 |
| 1.5.h | 動的ネイバー | 空白 | **XR 側の対応は要確認**(PoC)・IOS は `bgp listen range` | BGP 追補 |
| 1.5.i | コミュニティ | 一部(M5 の community-set) | XRd | — |
| 1.5.j | FlowSpec | 空白 | 制御側= XR(XRd・XRv9000)。**適用側は Cat8000v**(XRv9000 は適用不可【コミュニティ】・IOS XE はクライアントのみ【公式】) | 盤面に Cat8000v を 1 台 |
| 1.6.a | 静的 IPv6-in-IPv4 | 空白 | XRv9000 の GRE ○【公式】・XRd の GRE は不明(7.8.1 の「GRE for XRd vRouter」から CP は怪しい【推定】) | 読み物+短い課題 |
| 1.6.b | 6to4 | 空白 | **XR は不可**【コミュニティ】→ IOS XE(Cat8000v ○【公式】・IOL は要確認) | 読み物・紙面 |
| 1.6.c | 6PE | 空白 | XRv9000 ○【公式】・IOL ○【netlab】・XRd は要確認 | M8/M9 の盤面に足す |
| 1.6.d | IPv6 のポリシー適用 | 計画内(M12) | — | M12 で IPv6 を明示する |
| 1.6.e | NAT64・MAP-T | 空白 | **XR の仮想機は不可**(CGN は ASR 9000 の線カード側【公式】)→ Cat8000v(NAT64 ○・MAP-T は BR のみ確実【公式】) | 読み物・紙面(任意で Cat8000v の短いラボ) |
| 1.7.a/b | BFD・NSF | 済(M7) | XRv9000(XRd は BFD のセッションを作らない【実測】) | — |
| 1.7.c | NSR | 一部(読み物だけ) | **XRv9000 は RP 1 枚で NSR 不可**【公式】 | 読み物・紙面で受ける |
| 1.7.d | タイマー | 一部(M7) | — | — |
| 1.7.e | BGP PIC(edge/core) | 空白 | XRv9000 ○【公式・データシート】 | 収束の追補 |
| 1.7.f | LFA/IP FRR | 計画内(M10 の TI-LFA) | **要 PoC**(XRv9000 7.1.2 の「LFA FRR feature is not supported」が 7.3.3 以降の版から消えたが、追加の告知も無い【公式】) | PoC |
| 1.7.g | add-path・backup path | 空白 | 制御面は XRd・切り替えの観察は XRv9000 | 収束の追補 |

### 2.2 マルチキャスト(15%・15 項目)— **すべて空白**(XR トラックに単元が無い)

| 項番 | 内容 | 機種の見込み |
|---|---|---|
| 2.1・2.2.a/c/f | 概念・MAC への対応・PIM-SM・IGMP/MLD | 読み物と紙面。IOS 側の穴埋め `cloze_kb_mcast.py`(BL-217)をそのまま使える |
| 2.2.b | マルチキャストの MP-BGP | XR の制御面(XRd でも可の見込み) |
| 2.2.d・2.3.d | MSDP | IOL ○【実測】・XRv9000 はコマンドあり・転送は要 PoC・**XRd は MSDP のコマンドが無い**【実測】 |
| 2.2.e | mLDP/P2MP | XRv9000 の公式の対応表は mVPN が **Rosen GRE(プロファイル 0/3/11)だけ**・mLDP は要 PoC。Cat8000v ○【公式】・IOL は制御面 ○【実測】・データ面は要 PoC |
| 2.3.a | Auto-RP・BSR・anycast RP・phantom RP | IOL ○【実測】・XRv9000 は要 PoC |
| 2.3.b | bidir | IOL ○【実測】・XRv9000 は要 PoC |
| 2.3.c | SSM | IOL ○【実測】・XRv9000 ○(「IGMP, MLD, PIM SM/SSM in default VRF」【公式】) |
| 2.4.a/b | 単一ドメイン・複数ドメインの TS | XRv9000 1 台+IOL(2 ドメインを MSDP でつなぐ)で組める見込み |

- IOL では PIM-SM/BSR/Auto-RP/SSM/bidir/MSDP がデータの転送まで動く(poc/mcast/README.md・2026-09-22)。**XR は RP・MSDP の相手・PE の 1 台に置き、残りを IOL にする形**が組みやすい。
- XRd のマルチキャストの転送は公式に記載が無い(パッケージ xr-mcast・xr-pird-mcast はある)。動けば MSDP 以外の役に XRd を使える(PoC)。

### 2.3 ルーティング ポリシー(25%・15 項目)

| 項番 | 内容 | 現状 | 必要なもの |
|---|---|---|---|
| 3.1・3.2.a/b/d/g/i/j | RPL と route-map の比較・操作・意味・セット・prefix-set・属性・階層とパラメータ | 済(M5) | 紙面 |
| 3.2.c | 正規表現 | 一部(as-path-set) | M5 追補 |
| 3.2.e/h | タグ・経路の種類(`tag is`・`route-type is`) | 空白 | M5 追補(XRd で可) |
| 3.2.f | ACL | 空白(IOS の route-map 側は Enterprise で既習) | 紙面 |
| 3.3.a | IGP の経路操作の TS(IS-IS) | 済(M4 の漏らし) | — |
| 3.3.b | 同(OSPF) | 一部(M6 の OSPF 再配送) | M5 追補 |
| 3.4.a/b | BGP の経路の絞り込み・トラフィックの誘導 | 済/一部(M5・M6 のプリペンド) | BGP 追補で local-pref・MED を足す |

- 3.0 は今の XR トラックで一番進んでいる領域。追補は XRd で足りる。

### 2.4 MPLS と SR(25%・18 項目)

| 項番 | 内容 | 現状 | 機種の見込み |
|---|---|---|---|
| 4.1.a–d | LDP・LSP・Unified BGP・BGP フリー コア | 済(M8・M8 追補) | XRd |
| 4.1.e | RSVP-TE トンネル | **空白(計画にも無い)** | XRd に xr-rsvp-te があり、ラベル付きの転送は XRd で正常【実測】→ 要 PoC。Cat8000v ○【公式】・IOL は要 PoC |
| 4.2.a–c | SR の拡張(BGP/OSPF/IS-IS)・SRGB/SRLB・TI-LFA | 計画内(M10) | XRd+IOL(IOL の SR-MPLS ○【netlab】・IOS XE は IPv6 プレフィックスに SID を振れない【公式】)。TI-LFA の切り替えは要 PoC |
| 4.2.d | 移行(SR 優先・マッピング サーバ) | 空白(M10 の計画に明記なし) | IOL を LDP だけの機器、XR をマッピング サーバにする形が自然 |
| 4.3.a–d | SR-TE(自動ステアリングと色・制約と指標・PCE・SRLG) | **読み物だけの計画** | **XRd は PCE が本来の用途**【公式】・ヘッドエンドも公式サンプルが XRd CP で ping 成功を期待値にしている。IOL の PCC(`mpls traffic-eng pcc`)は要 PoC。遅延の指標は仮想機では静的な値のみ【二次情報】 |
| 4.3.e | Tree-SID | 読み物だけの計画 | PCE 側は XR ○【公式】・複製(データ面)は未確認・IOS XE には無い → 読み物・紙面(PoC で動けばラボ) |
| 4.4.a–d | SRv6(制御面・データ面・Flex-Algo・ロケータ/uSID/カプセル化/相互接続 GW) | **読み物だけの計画** | XRv9000 ○(uSID を含む【公式】)・XRd CP は公式サンプルが uSID L3VPN の ping を期待値にしている・IOL 17.18.02 は SRv6 上の VPNv4/v6 ○【netlab】・Cat8000v 17.15 は uSID L3VPN と TI-LFA ○(Flex-Algo は 17.18.1a から【公式】)。途中の機器は SRv6 を知らない普通の IPv6 ルータでよい。相互接続 GW は XR だけ(XRv9000 で要 PoC) |

## 3. 機種ごとに分かったこと(2026-10-27 調査)

| | XRv9000(26.1.1) | XRd Control Plane(26.1.1・CML 同梱) | IOL-XE(17.15/17.18) | Cat8000v(17.15) |
|---|---|---|---|---|
| 1 台の資源 | 7 vCPU/20GB(手で設定・実使用 約 17GB)・**同時 2 台が上限** | 2 vCPU/3GB | 1 vCPU/1GB | 1 vCPU/4GB |
| 位置づけ | 転送まで持つ仮想 PE | 「minimal forwarding capabilities」・用途は vRR と PCE【公式】 | IOS の機能はおおむね揃う・公式の機能一覧は無い | IOS XE 17 の各ガイドが適用製品に明記【公式】 |
| マルチキャスト | PIM-SM/SSM・IGMP/MLD(既定 VRF)・mVPN は Rosen GRE のみ【公式】。ほかは要 PoC | パッケージはある・MSDP 無し【実測】・転送は不明 | PIM 一式・MSDP まで転送 ○【実測】 | ○【公式】(mLDP 型 mVPN の章あり) |
| SR-MPLS・TI-LFA | 制御面 ○・TI-LFA の転送は要 PoC | 制御面 ○・ラベル転送 ○【実測】・TI-LFA は計算まで(公式サンプル) | SR-MPLS ○【netlab】・TI-LFA は要 PoC | ○(TI-LFA 17.3.2〜・Flex-Algo 17.3.1〜)【公式】 |
| SR-TE・PCE | ○・PCE の推奨機【公式】 | PCE が本来の用途【公式】・ヘッドエンドはサンプルで ping | 要 PoC | SR ポリシー 17.4〜・PCC ○【公式】 |
| SRv6 | ○(uSID 含む)【公式】 | サンプルで uSID L3VPN の ping | 17.18.02 で L3VPN ○【netlab】 | 17.12.1a〜(uSID F3216・IS-IS のみ)【公式】 |
| RSVP-TE | コマンドあり・要 PoC | パッケージあり・要 PoC | 要 PoC | ○【公式】 |
| BFD | ○(BLB ○・マルチホップは不明) | **セッションを作らない**【実測】 | ○ | ○ |
| FlowSpec | **制御側のみ**【コミュニティ】 | 不明(設定コマンドはある) | パーサにある・実装は要 PoC | **クライアントのみ**【公式】 |
| NAT64・MAP-T・6to4 | 不可【推定】 | 不可【推定】 | 要確認 | NAT64 ○・MAP-T は BR・6to4 ○【公式】 |
| 制約 | 無ライセンスで **200 kbps** に制限【公式】・24.4.x/25.1.x は仮想機非対応【公式】・NSR 不可(RP 1 枚) | 通過する TCP/UDP の L4 チェックサムを壊す(ラベル付きは正常)【実測】・ntp/ipsla/pbr 無し | **MTU 1500 固定**【netlab】・リンクを落としてもキャリアが落ちない【CML】・LACP 不可【実測】 | demo mode・CML 上 約 11 Mbit/s【CML】・SR/SRv6 に `license boot level network-premier`+再起動が要る【netlab】 |

- XRd vRouter(データ面つき)は CML では動かない見込み(データ ポートに PCI が要る・CML の XRd は Docker 型)。
  containerlab の `cisco_xrd_vrouter`(vrnetlab の VM の中で動かす)はあるが、4 vCPU/8〜10GB・nested KVM・hugepages が要り、
  イメージは cisco.com から(サービス契約が要る見込み)。XRv9000 より軽いのはメモリだけで手間が大きい → **推奨しない**。
- XRd のチェックサム異常: CML の XRd 定義は全ポートに `chksum`(受信した TCP/UDP のチェックサムを付け直す指定)を付けているのに起きている。
  Cisco 自身のツール(xr-compose)は XR⇔XR のリンクでは付けない → XR⇔XR のリンクだけ外した定義で比べる余地がある(§4.3 の 10)。

## 4. 足りないもの(何が必要か)

### 4.1 単元の追加(案・8 つ前後)

| 案 | 中身(SPRI 項番) | 機種 |
|---|---|---|
| BGP 追補 | コンフェデレーション・RR の TS・マルチホーミングの TS・GTSM・最大プレフィックス・ダンプニング・動的ネイバー・local-pref/MED の誘導・FlowSpec(1.4・1.5・3.4.b) | XRd+IOL(+FlowSpec の適用に Cat8000v 1 台) |
| 収束の追補 | BGP PIC edge/core・add-path・backup path・LFA(1.7.e–g) | XRv9000+IOL |
| M5 追補 | タグ・経路の種類・正規表現・OSPF の経路操作(3.2.c/e/h・3.3.b) | XRd |
| M3 追補 | OSPF マルチエリアの TS・NSSA・v6 の要約(1.2) | XRd |
| IPv6 移行 | 6PE/6VPE を M8/M9 の盤面に足す・GRE の IPv6-in-IPv4。6to4・NAT64・MAP-T は読み物+紙面(1.6) | XRv9000 か XRd(要 PoC)+IOL。NAT64/MAP-T は Cat8000v |
| **マルチキャスト(新単元)** | PIM-SM・RP 3 種+phantom・bidir・SSM・MSDP と anycast RP・マルチキャストの MP-BGP・mLDP(2.x) | XRv9000 1 台+IOL(XRd は PoC 次第) |
| **RSVP-TE(新単元)** | トンネル・経路の指定・autoroute・FRR(4.1.e)。SR-TE と対比する前段 | XRd か XRv9000(PoC)+IOL/Cat8000v |
| M10 を 3 つに分ける | ① SR-MPLS(拡張・SRGB/SRLB・TI-LFA・移行= SR 優先とマッピング サーバ)② SR-TE と PCE(色・ODN・制約・SRLG・XRd を PCE)③ SRv6(uSID・L3VPN・Flex-Algo・相互接続 GW)(4.2〜4.4) | ① XRd+IOL(切り替えは XRv9000)② XRd(PCE)+XRd/XRv9000+IOL ③ XRv9000/XRd+IOL 17.18 |

- 並びの案(未決・ユーザ判断)= M9 L3VPN → M10① SR-MPLS → RSVP-TE → M10② SR-TE → M10③ SRv6 → マルチキャスト(mVPN は L3VPN の後)。
  BGP 追補・収束の追補・M3/M5 追補は短いので合間に入れられる。
- 既存の計画は XR トラックの方針(ゆるく SPCOR 寄り・XR で手が動くことが先)のまま。SPRI 対応はその上に**追補を足す**形にし、単元番号は変えない。

### 4.2 紙面

- SPRI は筆記試験(選択式など)。XR トラックは全単元「紙面なし」で、パックとノルマの対象外。
- 要るもの= XR の show 出力を読む・RPL の判定を追う・SRGB とインデックスからラベルを出す・PIM の状態とフラグを読む・SR-TE の経路の選ばれ方 など。
  既存の紙面基盤(gen_paper_mcq・cloze の知識ベース)に XR/SP の知識ベースを足す形にする。IOS 側のマルチキャストは `cloze_kb_mcast.py` を流用できる。
- **決めること**(ユーザ判断)= SP の紙面をパック(`pack.sh new --profile …`)に入れて日次の出題に混ぜるか、XR トラックの単元末の確認問にとどめるか。

### 4.3 PoC(優先順)

| # | 確かめること | 決まること |
|---|---|---|
| 1 | XRv9000 26.1.1 のマルチキャスト= PIM-SM/SSM の転送・BSR/Auto-RP・bidir・MSDP と anycast RP(相手は IOL)・mLDP | マルチキャスト単元の盤面 |
| 2 | XRd のマルチキャストの転送(MSDP 以外) | XRd を足せるか |
| 3 | TI-LFA・LFA の切り替え(XRv9000/XRd)= `show cef … detail` のバックアップ・CML のリンク条件で落として ping の欠落を測る(BFD は XRv9000 だけ) | M10① と収束の追補の機種 |
| 4 | SR-TE= XRd を PCE・XRd/XRv9000 をヘッドエンド(ODN・色)・IOL を PCC | M10② の盤面 |
| 5 | SRv6 uSID L3VPN= XRd/XRv9000+IOL 17.18.02(+Cat8000v 17.15)・Flex-Algo・相互接続 GW(XRv9000)・XRd の通過で壊れないか | M10③ の盤面 |
| 6 | RSVP-TE= XRd での動作・IOL の対応・FRR | RSVP-TE 単元の機種 |
| 7 | BGP= XR の動的ネイバー・PIC・add-path・FlowSpec(XR が制御→ Cat8000v が適用) | BGP 追補・収束の追補 |
| 8 | 6PE を XRd で・GRE の IPv6-in-IPv4 を XRd/XRv9000 で | IPv6 移行の機種 |
| 9 | (XRv9000 が 3 台以上要る時だけ)26.1.1 を 4〜5 vCPU で安定して動かせるか(24.3.1 は 4 vCPU で不安定だった) | 台数の上限 |
| 10 | XRd のチェックサム異常= XR⇔XR のリンクで `chksum` を外したノード定義と比べる(CML の定義を足す操作なのでユーザ判断) | XRd を通過の役に使えるか |

- 公式の記述が足りない論点(XRd の機能・XRv9000 の未記載の機能)は実機で決める。CLAUDE.md の裏どりの順(公式・実機が最上位)どおり、
  公式と実機が食い違えばユーザに報告してから決める。

### 4.4 資源・イメージ・ライセンス

- 典型の盤面= XRv9000 1(20GB)+XRd 3(9GB)+IOL 4(4GB)≈ 33GB → **今のホストに収まる**。
  XRv9000 2 台にすると残りは約 7GB(XRd 1+IOL 数台)。窮屈なのは、XR どうしのデータ面を 3 台以上で見たい場合だけ
  (相互接続 GW・Tree-SID・両側の PE が XR の mVPN)。
- 必要になった時の打ち手= ①ホストのメモリ増設(XRv9000 は 1 台 20GB) ②PoC 9(vCPU を減らす) ③containerlab の XRd vRouter(§3・推奨しない)。
- イメージ: IOL 17.18.02・XRv9000 26.1.1・XRd 26.1.1 は登録済み。**Cat8000v 17.18 は SRv6 の Flex-Algo を IOS XE 側でもやる時だけ**要る(手元は 17.15)。
  XRv9000 を入れ替える時は 25.2 以降か 26.x(24.4.x・25.1.x は仮想機非対応【公式】)。
- ライセンス: 新規は不要。XRv9000 は無ライセンスで 200 kbps・Cat8000v は demo mode。ping と少量のマルチキャストには足りる。**帯域を測る課題は作らない**。

### 4.5 IOS XE 側の扱い

- SPRI は IOS XE と XR の両方を問う(3.1 の RPL と route-map の比較など)。XR トラックは XR が主役なので、
  IOS XE 側の SR(`sr-label-preferred` 等)・NAT64/MAP-T・6to4 は盤面の IOL/Cat8000v に課題を置くか、既存の IOS 系の資産(紙面・ラボ)で受ける。
- IOL の制約が効く場面= MTU 1500 固定(SRv6 やラベル積みの MTU の課題)・リンクを落としてもキャリアが落ちない
  (障害の検知は BFD か hello。M7 と同じく CML のリンク条件 loss 100 で起こす)。

### 4.6 裏どり

- SR-TE・SRv6 の設計情報は xrdocs.io に多いが、自動では取得しない決まり(CLAUDE.md)。
  Cisco Live の PDF・ASR 9000/NCS 5500 の設定ガイド・RFC(8402・8660・8667・8986・9252・9256・9350・9352 など)で固め、
  必要な記事だけユーザに貼ってもらう。

## 5. 出典(2026-10-27 閲覧)

- SPRI v1.1 出題範囲: https://learningcontent.cisco.com/documents/marketing/exam-topics/300-510_SPRI_v1.1.pdf
- CCIE SP v5.1 改訂ノート: https://learningcontent.cisco.com/documents/marketing/exam-topics/CCIE-SP-5.1-release-notes-v1_edited-kz.pdf
- Cisco の試験ページ: https://www.cisco.com/site/us/en/learn/training-certifications/exams/spri.html
- XRv9000 リリース ノート(24.1.1・7.11.1・7.1.2・7.3.3・25.1.1・25.x/26.x): https://www.cisco.com/c/en/us/td/docs/routers/virtual-routers/ 配下と https://www.cisco.com/c/en/us/td/docs/routers/iosxr/release-notes/
- XRv9000 データシート: https://www.cisco.com/c/en/us/products/collateral/routers/ios-xrv-9000-router/datasheet-c78-734034.html
- XRv9000 導入ガイドの付録(冗長構成非対応): https://www.cisco.com/c/en/us/td/docs/routers/virtual-routers/configuration/guide/b-xrv9k-cg/b-xrv9k-cg_chapter_0111.html
- ASR 9000 SR-PCE(7.8)・SRv6 uSID(7.9)・CGv6(26.x)の設定ガイド(cisco.com の asr9000 配下)
- XRd データシート: https://www.cisco.com/c/en/us/products/collateral/routers/ios-xrd/ios-xrd-ds.html
- xrd-tools(公式 GitHub・サンプルと起動の制約): https://github.com/ios-xr/xrd-tools
- containerlab の XRd vRouter: https://containerlab.dev/manual/kinds/cisco_xrd_vrouter/
- IOS XE 17 の SR/SRv6・マルチキャスト・MPLS・BGP・NAT64/MAP-T の設定ガイド(cisco.com の ios-xe / ios/config/17-x 配下)
- Cat8000v 17.18 リリース ノート・データシート(cisco.com の C8000V 配下)
- mVPN プロファイル(TAC 118985): https://www.cisco.com/c/en/us/support/docs/ip/multicast/118985-configure-mcast-00.html
- CML の文書(IOL・Cat8000v・FAQ・2.10 リリース ノート): https://developer.cisco.com/docs/modeling-labs/
- Cisco Live BRKSPG-1552(EMEA 2023)・BRKCLD-1005(2023)・BRKSPG-2051(APJC 2025)
- 弱い根拠: netlab の IOL 試験結果(https://tests.netlab.tools/_html/iol.html)・Cisco Community の投稿(FlowSpec・P2MP-TE・マルチホップ BFD)
- xrdocs.io は開いていない。問題集サイトは使っていない。
