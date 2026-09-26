# U-A3 STP — 出典照合表(ソース検証マトリクス)

対象: [U-A3-stp.md](U-A3-stp.md) の知識項目 47 件。照合日 2026-09-22。
実機欄の根拠は [poc/stp/README.md](../poc/stp/README.md)(2026-07-29・ioll2 三角形・P1〜P6)と
[STP-SERIES.design.md](../problems/_drafts/STP-SERIES.design.md) の実測メモ。

**凡例**
- 出典欄: ○= 一致 / △= 表現差・一部のみ記載・プラットフォーム差 / ×= 相違 / —= 未記載。続けて出典キー(下表)と要旨・原文の短い引用。
- 実機欄: ○= poc/stp で実測済(要点) / 要実測 / 不要(概念)。
- 判定: **確定**(出題に使ってよい) / **要実測**(IOL/ioll2 で確かめてから出題) / **要ユーザ判断**(出典どうしが割れている・出題上の扱いを決める必要)。
- 出典の引用は照合時に読んだ本文の要約か短い抜粋。英語原文は「」で示す。

## 出典キー

### Cisco 公式

| キー | 文書 | URL |
|---|---|---|
| C-STP9k | Catalyst 9300 L2 Config Guide IOS XE 17.15 — Configuring Spanning Tree Protocol | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/configuration_guide/lyr2/b_1715_lyr2_9300_cg/configuring_spanning_tree_protocol.html |
| C-STP2960X | Catalyst 2960-X Consolidated Guide 15.2(3)E — Configuring STP | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960x/software/15-2_3_e/consolidated_guide/b_1523e_consolidated_2960x_cg/m_lay2_stp_cg_old.html |
| C-STP9500 | Catalyst 9500 L2/L3 Config Guide 16.6 — Configuring STP | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/16-6/configuration_guide/b_166_lyr2_lyr3_9500_cg/b_166_lyr2_lyr3_9500_cg_chapter_00.html |
| C-MST9k | Catalyst 9300 L2 Config Guide 17.15 — Configuring Multiple Spanning-Tree Protocol | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/configuration_guide/lyr2/b_1715_lyr2_9300_cg/configuring_multiple_spanning_tree_protocol.html |
| C-OPT9k | Catalyst 9300 L2 Config Guide 17.15 — Configuring Optional Spanning-Tree Features | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/configuration_guide/lyr2/b_1715_lyr2_9300_cg/configuring_optional_spanning_tree_features.html |
| C-OPT2960X | Catalyst 2960-X Consolidated Guide 15.2(4)E — Configuring Optional Spanning-Tree Features(portfast edge 形) | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960x/software/15-2_4_e/configurationguide/b_1524e_consolidated_2960x_cg/b_1524e_consolidated_2960x_cg_chapter_01111.html |
| C-UDLD9k | Catalyst 9300 L2 Config Guide 17.15 — Configuring UniDirectional Link Detection | https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/configuration_guide/lyr2/b_1715_lyr2_9300_cg/configuring_unidirectional_link_detection.html |
| C-UDLDTN | Tech note: Configure the UDLD Protocol Feature (10591-77) | https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/10591-77.html |
| C-RSTP | Tech note: Understand Rapid Spanning Tree Protocol (802.1w) (24062-146) | https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24062-146.html |
| C-MSTTN | Tech note: Understand Multiple Spanning Tree Protocol (802.1s) (24248-147) | https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24248-147.html |
| C-RG | Tech note: Spanning Tree Protocol Root Guard Enhancement (10588-74) | https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/10588-74.html |
| C-LG | Tech note: STP Enhancements using Loop Guard and BPDU Skew Detection (10596-84) | https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/10596-84.html |
| C-PF | Tech note: Spanning Tree PortFast and BPDU Guard (10586-65) | https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/10586-65.html |
| C-TMR | Tech note: Understand and Tune STP Timers (19120-122) | https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/19120-122.html |
| C-PVID | Tech note: Troubleshoot Spanning Tree PVID- and Type-Inconsistencies (24063) | https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24063-pvid-inconsistency-24063.html |

### ネットワークエンジニアとして(www.infraexpert.com/study/)

| キー | ページ |
|---|---|
| J-1 | stpz1.html STP とは(BPDU フォーマット・ブリッジ ID・パスコスト表) |
| J-2 | stpz2.html STP の動作(root/RP/DP/NDP 選出) |
| J-3 | stpz3.html ポートの状態遷移とコンバージェンス |
| J-4 | stpz4.html PVST+ とは(拡張システム ID) |
| J-5 | stpz5.html STP 設定(priority・root primary/secondary) |
| J-6 | stpz6.html show spanning-tree の見方 |
| J-7 | stpz7.html PortFast / UplinkFast / BackboneFast |
| J-8 | stpz8.html RSTP とは(役割・状態) |
| J-9 | stpz9.html RSTP BPDU フォーマット |
| J-9.5 | stpz9.5.html RSTP Proposal/Agreement・リンクタイプ |
| J-10 | stpz10.html RSTP 設定(mode・cost・port-priority) |
| J-11 | stpz11.html BPDU ガード |
| J-12 | stpz12.html BPDU フィルタリング |
| J-13 | stpz13.html ルートガード |
| J-14 | stpz14.html ループガード |
| J-15 | stpz15.html Catalyst STP/RSTP/MSTP のデフォルト値 |
| J-16 | stpz16.html MSTP とは |
| J-17 | stpz17.html MSTP 用語(instance/region/IST/CIST)・802.1D 相互運用 |
| J-18 | stpz18.html MSTP 設定その 1(mst configuration・name・revision・instance) |
| J-19 | stpz19.html MSTP 設定その 2(mst priority/root/cost/port-priority) |
| J-20 | stpz20.html MSTP 設定その 3(設定例・show pending・show コマンド) |
| J-21 | stpz21.html MSTP リージョン内の動作 |
| J-22 | stpz22.html MSTP リージョン間の動作 |
| J-UDLD | l2control01.html UDLD とは |
| J-ERR | catalyst27.html errdisable の原因と復旧 |

URL は `https://www.infraexpert.com/study/<ページ>` の形。

---

## 1. 基礎(802.1D)

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 1 | STP の目的= L2 ループ・ブロードキャストストーム・MAC テーブル不安定の防止 | △ C-STP9k: STP は冗長リンクを持ちつつループを防ぐ(ストーム・MAC 不安定は明記なし) | △ J-1: ループ→「ブロードキャストストーム」・帯域と CPU を消費(MAC テーブル不安定の語はない) | 不要(概念) | 確定 |
| 2 | BPDU は Configuration/TCN の 2 種・root が生成・宛先 MAC 01:80:C2:00:00:00 | △ C-STP2960X「The hello time is the time interval between configuration messages generated and sent by the root switch」/ C-PVID: IEEE 宛先 0180.c200.0000 は VLAN1(native)のみ、**VLAN1 以外の PVST+ BPDU は 0100.0ccc.cccd(SSTP)宛て・802.1Q タグ付き** | ○ J-1: 「定期的にBPDUをマルチキャストアドレス(0180.C200.0000)で送信」・Message Type= Configuration 0x00 / TCN 0x80(PVST+ 宛先 MAC は記載なし) | 要実測(任意・CML キャプチャで PVST+ の 2 宛先を確認) | 要ユーザ判断(PVST+ 前提の出題なら 0100.0CCC.CCCD を併記するか決める) |
| 3 | Bridge ID= priority(4 bit・4096 刻み)+ 拡張システム ID(12 bit = VLAN)+ MAC | ○ C-STP9k: 2 バイトを「4-bit priority value and a 12-bit extended system ID value equal to the VLAN ID」に再割当 | ○ J-4: 拡張システム ID により「ブリッジプライオリティが4ビット」→「4096の単位でのみ設定」 | ○ P1: sys-id-ext 込み表示 4096+10=4106 | 確定 |
| 4 | root 選出= 最小 BID(priority → MAC の順) | ○ C-STP2960X: 最小 priority 値が root・全員既定 32768 なら「lowest MAC address」 | ○ J-2: 「先ずブリッジプライオリティ値を比較して、この値が同じ場合にはMACアドレスを比較」 | ○ P2: priority 明示で机上予測と一致 | 確定 |
| 5 | RP 選出= root path cost → 送信元 BID → 送信元 port priority → 送信元 port 番号 | △ C-STP9k/C-STP2960X は「cost → port priority → lowest interface number」と**自装置目線で書く**(送信元 BID・送信元ポート ID という比較順の明記なし) | ○ J-2/J-8: 「各ポートのルートパスコスト→送信元ブリッジID→送信元ポートID、の順で比較」・ポート ID= ポートプライオリティ+ポート番号 | 要実測(上流の port-priority 変更で下流 RP が変わることの実証。#31 と同時) | 確定(順序は標準)。ただし #31 の実測を推奨 |
| 6 | DP= セグメントごとに 1 つ・root の全ポートは DP | △ C-STP9k: designated device/port の概念説明のみ | ○ J-2: 「各リンクごとに1ポート」「ルートブリッジの全てのポートは必ず指定ポート」 | ○ P1/P2(root 側 Desg を観測) | 確定 |
| 7 | 非指定ポート= blocking | ○ C-STP9k: Blocking「does not participate in frame forwarding」 | ○ J-2: NDP「データフレームが送受信されない(BPDUは受信する)ブロッキング状態」 | ○ P2: `Et0/1 Altn BLK` | 確定 |
| 8 | ポート状態 Disabled/Blocking/Listening/Learning/Forwarding と各段の動作 | ○ C-STP2960X: 状態遷移「initialization→blocking→listening→learning→forwarding(各段から disabled)」/ C-STP9k: 各状態の定義 | ○ J-3: Blocking=BPDU 受信のみ / Listening=BPDU 送受信・MAC 学習しない / Learning=MAC 学習・転送しない / Forwarding | 不要(概念。IOL は rapid 運用のため 802.1D 状態の観測は任意) | 確定 |
| 9 | タイマ hello 2 / forward delay 15 / max age 20・収束 30〜50 秒 | ○ C-STP9k 既定値表(2/15/20・Transmit hold count 6)/ △ C-TMR: 既定値は diameter 7 前提(30〜50 秒の数値は明記なし) | ○ J-3: 間接障害=max age 20+15+15=50 秒、直接障害=30 秒 / J-15: 2/15/20・転送保留 6 BPDU | 不要(概念) | 確定 |
| 10 | TCN BPDU で MAC エージングを forward delay(15 秒)に短縮 | △ C-TMR: TCN 受信後のエージングを forward delay(15 秒)にする関係を説明(本照合では短い要約のみ確認) | — J-1: Message Type の TCN=0x80 と Flags の TC/TCA ビットのみ。短縮の記述なし | 要実測(任意: `show spanning-tree detail` の TC カウンタ) | 確定(標準動作。出題は Cisco 表現に寄せる) |
| 11 | パスコスト short: 10M=100・100M=19・1G=4・10G=2 / long(802.1t): 1G=20000・10G=2000 | △ C-STP2960X 既定表: 1G=4/100M=19/10M=100(short)。C-STP9k の既定表は **10M=2000000・100M=200000・1G=20000・10G=2000・40G=500・100G=200**(long 値)を載せつつ本文は「The short path cost method is the default」→ 同一ページ内で食い違い。C-STP9500: 一部 9500 機種は long が既定 | ○ J-1/J-2: 「IEEE改定後」2/4/19/100・改定前(1000/速度)1/1/10/100 / J-15・J-19: MST モード時 10M=2,000,000 … 10G=2,000・100G=200 | ○ rapid-pvst で IOL Ethernet= **100**(10M 扱い)/ MST で **2000000** | 確定(値そのもの)。IOL の Et は 10M 扱い → 盤面では Gi 前提の値が出ない点に注意 |

## 2. RSTP(802.1w)

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 12 | 役割 Root/Designated/Alternate/Backup | ○ C-RSTP: 4 役割。Backup=「receives more useful BPDUs from the same bridge it is on」(同一ブリッジが共有セグメントに 2 本) | ○ J-8: AP=RP のバックアップ(UplinkFast 相当)/ BP=DP のバックアップ・リピータハブ等の共有メディアで発生・送信元ポート ID の小さい方が DP | ○ Root/Desg/Altn は観測済。Backup は要実測(CML の unmanaged switch で共有セグメントを作れば再現可能か) | 確定(Backup の盤面は要実測) |
| 13 | 状態 Discarding/Learning/Forwarding の 3 つ | ○ C-RSTP「Discarding, Learning, and Forwarding」 | ○ J-8: Disabled/Blocking/Listening を Discarding に統合 | ○ 表示は `BLK`(Discarding でも Sts 列は BLK) | 確定 |
| 14 | 全スイッチが hello ごとに BPDU を出す・3 回欠落(6 秒)で失効 | ○ C-RSTP: 「BPDUs are sent every hello-time」・「if hellos are not received three consecutive times, protocol information can be immediately aged out」 | — J-8/J-9.5 に「3 回」「6 秒」の記述なし(「数秒以内で収束」のみ) | 要実測(IOL はリンクダウンが対向に伝わらない既知の癖あり→失効経路の確認) | 確定 |
| 15 | Proposal/Agreement(sync)で即時 forwarding・p2p リンク限定 | ○ C-RSTP: 高速遷移は「edge ports and on point-to-point links」のみ | ○ J-9.5: Proposal 受信側は RP を転送状態にし他ポートを一時 Discarding にして Agreement を返す・高速収束には p2p が必要 | 不要(概念) | 確定 |
| 16 | Edge port(PortFast)・link type は duplex から自動判定(全二重=p2p / 半二重=shared) | ○ C-RSTP: 「link type is automatically derived from the duplex mode」・edge は BPDU 受信で「immediately loses edge port status」 | ○ J-9.5: p2p=全二重・shared=半二重 / J-10: RSTP でも端末ポートは PortFast | 要実測(IOL で half duplex/`spanning-tree link-type shared` が効くか・Type 列 `Shr` の表示) | 確定(IOL 表示は要実測) |
| 17 | Alternate が RP を即時引き継ぐ | ○ C-RSTP: UplinkFast/BackboneFast/PortFast 相当を標準で内蔵 | ○ J-8/J-9.5: AP は「即座にルートポートの役割を引き継ぎ」 | ○ 自側 shut= 1 秒以内に Altn→Root / 対向 shut= 約 5 秒(IOL はリンクダウン非伝播・hello 3 回失効)(M13) | 確定(即時は自側のリンク障害。IOL で対向障害を出題の盤面にしない) |
| 18 | TC= 非 edge ポートが forwarding に移る時だけ発生・TC While(2×hello)・受信ポート以外の MAC をフラッシュ | ○ C-RSTP: TC は「non-edge ports … move to the forwarding state」のみ・TC While= hello の 2 倍・受信ポート以外の MAC を消去 / C-STP9k: rapid PVST+ は TC 受信で MAC をポート単位で即時削除 | △ J-9.5: 発生源が TC ビット付き BPDU を全体にフラッディング(TC While・edge 除外の明記なし) | 不要(概念) | 確定 |
| 19 | 802.1D との互換= ポート単位で 802.1D に落ちる | ○ C-RSTP: ポート単位・migration delay 3 秒 | △ J-8: 「下位互換性があり…相互接続可能」(ポート単位の明記なし)/ J-17(MST 側): 802.1D BPDU 受信ポートは 802.1D BPDU のみ送信・自動では戻らず `clear spanning-tree detected-protocol(s)` | ○ `P2p Peer(STP)`・`Peer is STP`。戻り方はポートにより自然消滅/残存。`clear spanning-tree detected-protocols` は打った側だけ(M14) | 確定(自動で戻るとは断定しない) |

## 3. PVST+ / Rapid-PVST+ / MST(802.1s)

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 20 | Cisco 既定= PVST+・`spanning-tree mode rapid-pvst` | × C-STP9k 既定表: Mode= **Rapid PVST+** / C-STP2960X「Beginning in Cisco IOS Release 15.2(4)E, the default STP mode is Rapid PVST+」 | ○(項目と一致・Cisco とは相違) J-15: 「PVST＋(Rapid PVST+ と MSTP はディセーブル)」/ J-10: 「デフォルトで…STP(PVST+)」・mode [mst \| ○ ioll2 17.15 の既定= Rapid PVST+(`no spanning-tree mode` でも rapid-pvst)(M1) | 確定(ユーザ決定 U1: 版で答えが変わる。問題文で機種/版を示す) | 要実測(PoC は明示 `rapid-pvst` 投入。ioll2 の素の既定は未確認) | **要ユーザ判断**(「既定」を旧 IOS=PVST+ とするか現行=Rapid PVST+ とするか。出題文で機種/版を固定する等) |
| 21 | PVST+ の負荷分散= VLAN ごとに root を変える | △ C-STP9k: VLAN ごとに独立したインスタンス(負荷分散の語は薄い) | ○ J-4: 「VLANごとのロードバランシング通信が可能」(SWA=VLAN10 root・SWB=VLAN20 root の例) | ○ P1/P2: VLAN10/20 で root 分離・ブロック位置も VLAN で違う | 確定 |
| 22 | MST= 複数 VLAN を 1 インスタンスに束ねる | ○ C-MST9k / C-MSTTN: MSTI は RSTP インスタンス | ○ J-16: VLAN を束ねて BPDU と CPU 負荷を削減 | ○ P4 | 確定 |
| 23 | MST リージョン= name・revision・VLAN→instance 対応の 3 つが一致 | ○ C-MST9k「same VLAN-to-instance map, the same configuration revision number, and the same name」/ C-MSTTN: name 32 バイト・revision 2 バイト・4096 要素の表(digest) | ○ J-21: 3 項目を同じに / J-18: name 最大 32 文字・revision 0〜65535 | ○ P4: 不一致で境界 `P2p Bound(RSTP)`+`Regional Root this switch` | 確定 |
| 24 | IST(instance 0)・CIST・boundary port | ○ C-MST9k: IST=instance 0・CIST=各リージョンの IST+CST・boundary port の定義 / C-MSTTN: IST は RSTP インスタンス | ○ J-17: IST=インスタンス 0・BPDU を送受信する唯一のインスタンス・MSTI は M レコード / J-21: 境界ポートでは IST BPDU のみ | ○ P4 | 確定 |
| 25 | `spanning-tree mst configuration` / `name` / `revision` / `instance N vlan …` / `show spanning-tree mst configuration` | ○ C-MST9k: `spanning-tree mst configuration`・`spanning-tree mode mst` | ○ J-18/J-20: 設定例と `show pending`・`show spanning-tree mst configuration` | ○ P4(`[digest]` も確認) | 確定 |
| 26 | 未割当 VLAN は IST(instance 0)に属する | ○ C-MST9k「By default, all VLANs are assigned to the IST」/ C-MSTTN「Avoid mapping any VLANs onto instance 0」(推奨) | ○ J-17: 「インスタンス 0 にはすべてのVLANが割り当て」/ J-20: show pending で `0 1-10, 31-4094` | 要実測(任意: `show spanning-tree mst configuration` の instance 0 行) | 確定 |
| 27 | MST と PVST+ の相互接続(PVST simulation) | ○ C-MSTTN: 境界で「replicates the IST BPDU on all the VLANs to simulate a PVST+ neighbor」 | — J-22: 802.1D/CST との相互運用のみ。PVST simulation の語なし | ○ 境界 `Bound(PVST) *PVST_Inc`・`PVST Sim. Inconsistent`・`%SPANTREE-2-PVSTSIM_FAIL`(M15) | 確定 |

## 4. チューニング(root 配置・パス選択)

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 28 | `root primary`= 24576(現 root がそれ以下なら 4096 引く)/ `secondary`= 28672 | ○ C-STP2960X: 24576 で root になれるならそれ・「If any root switch for the specified VLAN has a switch priority lower than 24576, the switch sets its own priority for the specified VLAN to 4096 less than the lowest switch priority」・「fails if the value necessary to be the root switch is less than 1」・secondary は既定 32768 から 28672 へ / △ C-STP9k: 24576 の文のみ(4096 減の文なし) | △ J-5: 既存 root 32768 なら 24576 の例のみ・「既存よりも小さい値が適用」・secondary は「プライオリティ値が常に 28672 になるだけ」(非推奨・明示 0/4096 を推奨) | ○ 32768→24576・16384→12288・24576(MAC 負け)→20480・4096/0→失敗(`% Failed to make the bridge root`)。running には数値のみ・後で追従しない。secondary は常に 28672(全員既定なら root になる)(M2/M3) | 確定(文言は「24576 未満」「1 未満が必要なら失敗」) |
| 29 | `spanning-tree vlan N priority X`= 4096 の倍数・既定 32768 | ○ C-STP9k: 0〜61440・4096 刻み・既定 32768 | ○ J-5/J-10: 0〜61440・4096 単位 | ○ P1/P2: 4096/8192 投入 | 確定(倍数でない値の拒否メッセージは任意で実測) |
| 30 | `spanning-tree cost` は自分の RP 選択に効く | ○ C-STP2960X: ループ時に forwarding を選ぶのに cost を使う・範囲 1〜200000000(C-STP9k) | ○ J-10: `spanning-tree vlan N cost`・VLAN 省略で全 VLAN。△ 範囲を「1〜20000000」と記載(Cisco は 1〜200000000) | 要実測(IOL の受理範囲・盤面効果は L2 で) | 確定(範囲の数値は出題しない) |
| 31 | `port-priority`(既定 128・16 刻み)は**対向**の RP 選択に効く | ○ C-STP9k: 0〜240・16 刻み・既定 128・「Lower the number, the higher the priority」。△ どちら側の値が効くかは自装置目線の記述のみ | ○ J-10/J-19: 既定 128・16 の倍数・0〜240 / J-2: 比較は「送信元ポートID」(=上流の値) | ○ 刻み 16・上流で変えると下流の RP が移る・下流で変えても不変(M4) | 確定 |
| 32 | `spanning-tree pathcost method long` | △ C-STP9k:「short … is the default」・既定表は long 値 / C-STP9500: 一部機種は long 既定 / C-MST9k:「When the device is in MST mode, it uses the long path-cost calculation method」/ コマンドリファレンス: long は 32 bit・1〜200,000,000、スイッチ上の全インスタンスに適用。**どのスイッチに設定すべきかの明文は見つからず** | — J: pathcost method コマンドの記載なし(MST モード時の long 値表のみ) | ○ 3 台そろえて summary `Configured Pathcost method used is long`・Et=2000000(M5) | 確定(ユーザ決定 U4: 1 問の中で全 SW をそろえる。混在は出題しない) |
| 33 | タイマ変更は root で行う・diameter | ○ C-TMR: 効くのは root に設定した値だけ・BPDU で配布・既定値は diameter 7 前提 / C-STP2960X: `root primary [diameter 2-7 [hello-time]]`・secondary にも同じ diameter を使う | △ J-3: タイマは変更可能だが非推奨(root で設定する話・diameter の記載なし) | 不要(概念) | 確定 |
| 34 | `show spanning-tree root` / `vlan N` / `summary` | △ C-STP9k 監視コマンド一覧: `show spanning-tree active/detail/vlan/interface/summary`(summary の表示項目は公式ガイド本文になし。Cisco コミュニティの出力例に「Switch is in … mode」「Extended system ID is enabled」「Portfast Default is disabled」「PortFast BPDU Guard Default」「Loopguard Default」「Pathcost method used is short」) | △ J-6: `show spanning-tree` の各欄のみ(root/summary は記載なし) | ○ summary の文言を取得(`Switch is in rapid-pvst mode` ほか・edge の語なし)(M6) | 確定 |

## 5. 保護機構

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 35 | PortFast= listening/learning を飛ばす・端末ポート限定・`spanning-tree portfast` / global `portfast default`(アクセスポートのみ)/ `portfast trunk` | ○ C-OPT9k: `spanning-tree portfast default` は「all nontrunking ports」・trunk は `spanning-tree portfast trunk`・「Use PortFast only when connecting a single end station」。△ C-OPT2960X(15.2(4)E): `spanning-tree portfast edge [trunk]` / `portfast network` / global `portfast edge default`(edge/network/normal の 3 種) | ○ J-7: global は「全てのアクセスポート」(非推奨)・警告文「will only have effect when the interface is in a non-trunking mode」・PortFast ポートでも BPDU は送信され続ける | ○ 旧形のみ(P6)・Type 列 `P2p Edge`・trunk IF への portfast は警告のみで無効・`portfast trunk` で trunk も Edge(M17) | 確定(構文は旧形を正) |
| 36 | BPDU guard= BPDU 受信で err-disabled・interface `bpduguard enable` / global `portfast bpduguard default`(PortFast ポートのみ) | ○ C-OPT9k: global は「ports that are in a PortFast operational state」のみ・interface は PortFast なしでも受信で error-disabled / C-PF | ○ J-11: ポート単位は「portfastの設定の有無に関係なく」・グローバルは「portfastが設定されている全てのポート」・ログ `%SPANTREE-2-BLOCK_BPDUGUARD` `%PM-4-ERR_DISABLE` | ○ P3: boot 時発火・`Et0/2 err-disabled bpduguard` | 確定 |
| 37 | BPDU filter= interface は送受信とも停止(危険)/ global は PortFast ポートのみ・受信で PortFast 解除 | ○ C-OPT9k: global はリンクアップ時に「still send a few BPDUs」その後フィルタ・受信で「loses its PortFast operational status, and BPDU filtering is disabled」/ interface は送受信停止・「the same as disabling spanning tree on it and can result in spanning-tree loops」。送出数は公式ガイドでは「a few」のみ(「10 個」「11 個」は旧資料・コミュニティ) | △ J-12: interface=「実質的にポート上でのSTPの無効化」○・global は PortFast ポートのみ・受信で PortFast 解除し BPDU 送信再開 ○。リンクアップ時の数個送出の記述なし | ○ global: 最初は filter のまま BPDU を送る→ 受信で filter/portfast が外れる。送出数は確定不可(M7) | 確定(定性のみ。送出数は出題しない) |
| 38 | Root guard= designated 側・superior BPDU で root-inconsistent・自動復帰 | ○ C-RG: 「moves this port to a root-inconsistent STP state」(listening 相当・転送なし)・superior BPDU が止まれば「Recovery is automatic」・`spanning-tree guard root` / C-OPT9k: インターフェースが属する全 VLAN に適用・MST では designated を強制 | ○ J-13: root-inconsistent・受信しなくなると回復・ポート単位のみ設定・`show spanning-tree inconsistentports`・ログ `%SPANTREE-2-ROOTGUARD_BLOCK` | ○ `Root Inconsistent`・`%SPANTREE-2-ROOTGUARD_BLOCK`・約 2 秒で UNBLOCK・ポート上の全 VLAN に効く(M9) | 確定 |
| 39 | Loop guard= root/alternate 側・BPDU 途絶で loop-inconsistent・片方向リンク対策 | ○ C-LG: 非 designated ポートで BPDU が来なくなると「loop-inconsistent blocking state」・受信再開で自動復帰・「root and alternate ports」・VLAN 単位・「cannot be enabled on ports where portfast is enabled」・global `spanning-tree loopguard default` / interface `spanning-tree guard loop` / C-UDLD9k: loop guard は p2p リンクでのみ動作 | ○ J-14: 「代替ポートまたはルートポート」が DP になるのを防ぐ・loop-inconsistent・自動復旧・一般にグローバルで有効化・ログ `LOOPGUARD_BLOCK/UNBLOCK` | ○ BPDU 途絶から約 5 秒で `Loop Inconsistent`・`%SPANTREE-2-LOOPGUARD_BLOCK`・Altn/Root の VLAN のみ・受信再開で即復帰(M10) | 確定 |
| 40 | UDLD normal/aggressive(片方向リンク検出・err-disabled) | ○ C-UDLDTN: normal は片方向でも「marks the logical link as undetermined and does not disable the port」・aggressive は近隣情報失効後「sending one message per second for eight seconds」→再確立できなければ disable・メッセージ間隔既定 15 秒 / C-UDLD9k: 間隔 1〜90 秒・既定 15 秒・global `udld {aggressive \| enable \| △ ioll2 に UDLD あり・Et で `udld port [aggressive]` が Bidirectional。片方向は再現不可(MAC ACL で UDLD は落ちない)(M11) | 確定(片方向時の挙動は Cisco 公式どおり= normal はタイムアウトで無効化しない・aggressive は再確立失敗で err-disable。誤配線時の normal は出題しない・ユーザ決定 U3) | 要実測(ioll2 に UDLD があるか・Et は光でないので global では効かず `udld port` が必要か・CML で片方向を作れるか) | 要実測(IOL での出題可否)。normal の誤配線時の扱いは要ユーザ判断(下記 D9) |
| 41 | errdisable recovery= `errdisable recovery cause bpduguard`・interval 既定 300 秒 | ○ C-PF: 既定 300 秒(自動復旧自体は既定無効)・`errdisable recovery interval` / C-UDLD9k: `errdisable recovery cause udld` | ○ J-ERR: 既定 300 秒・範囲 30〜86400 秒 / J-11: 300 秒ごとに自動復旧 | ○ 既定 Disabled・300 秒・最小 30。既に err-disabled のポートは旧タイマのまま(M12) | 確定 |
| 42 | Loop guard と Root guard は同一ポートで同時不可 | ○ C-OPT9k「You cannot enable both loop guard and root guard at the same time」/ C-LG「mutually exclusive」 | ○ J-14: 「排他的な関係にあり、両方の機能を同時にイネーブルにできません」 | ○ IF の guard は後勝ちで置換・global loopguard より IF guard root が優先(M10c) | 確定 | 確定(組合せ時の挙動は要実測) |
| 43 | BPDU guard と BPDU filter の違い(遮断 vs 無視) | ○ C-OPT9k(#36・#37 の記述) | ○ J-12: guard はループ防止で推奨・filter はループを起こし得るため非推奨 | ○ 同一ポートに両方= filter が勝つ(err-disable しない)(M8) | 確定 |

## 6. 読解

| # | 事実(短く) | Cisco公式 | ネットワークエンジニアとして | 実機 | 判定 |
|---|---|---|---|---|---|
| 44 | `show spanning-tree vlan N` の Root ID / Bridge ID / This bridge is the root | △ C-STP9k: 監視コマンド一覧のみ(出力例の解説なし) | ○ J-6: プロトコル行 `ieee`=PVST+ / `rstp`=rapid-pvst・Root ID・「This bridge is the root」・Bridge ID `(priority 32768 sys-id-ext 1)`・Aging 300 秒 | ○ P1/P5(Genie でパース可・`protocol rstp`) | 確定 |
| 45 | ポート行 Role(Root/Desg/Altn/Back)・Sts(FWD/BLK/LRN)・Cost・Prio.Nbr・Type(P2p/Shr/Edge) | — | ○ J-6: Root/Desg/Altn・FWD/BLK・コスト 2/4/19/100・Prio.Nbr= 128+ポート番号・Type `P2p` / PortFast は `Edge P2p` | ○ `Et0/1 Altn BLK`・`P2p Bound(RSTP)`(MST 不一致)。Back/Shr/Edge の表示は要実測 | 確定(Back/Shr/Edge の IOL 表示は要実測) |
| 46 | priority 表示値= 設定値+VLAN ID | ○ C-STP9k: 12 bit 拡張システム ID= VLAN ID | ○ J-4: 32768+1=32769・32768+10=32778 / J-20: MST では**インスタンス ID** が加算 | ○ P1: 4096+10=4106 | 確定(MST ではインスタンス番号が加算される点を併記) |
| 47 | root path cost= 自分の受信ポートのコスト+上流の root path cost | △ C-STP2960X: BPDU に「spanning-tree path cost to the root」を載せる | ○ J-2: root は cost 0 で送信・受信側が自ポートのコストを加算(4+19=23 の例) | ○ P2(机上計算とブロック位置が一致)。IOL の Et は 100 刻み | 確定 |

---

## 実測の反映(2026-09-22)

M1〜M17 を ioll2-xe 17.15.1 で実測し、上の表の「実機」「判定」欄を更新した。詳細= [poc/stp/README.md](../poc/stp/README.md) 第2回。
未実測= M16(Backup/Shared)・M18(BPDU 宛先 MAC・U2 で IEEE のみに決定)・M19・M21(いずれも C 群)。

## 食い違い・注意点

| ID | 論点 | 内容 | 出題への影響 |
|---|---|---|---|
| D1 | 既定モード(#20) | Cisco 現行(Catalyst 9000・IOS 15.2(4)E 以降)は **Rapid PVST+ が既定**。ネットワークエンジニアとして と知識項目表は PVST+。ioll2 の既定は未確認 | 「既定モードは?」は機種・版を固定しない限り正解が割れる。**要ユーザ判断** |
| D2 | パスコストの値と IOL(#11・#32・#47) | IOL の Ethernet は 10M 扱い= short **100** / long(MST)**2000000**(実測)。試験の典型(Gi=4/20000)とは違う。Cat9300 17.15 ガイドは既定表に long 値を載せつつ本文で short が既定と書く(同一文書内の食い違い)。Cat9500 の一部機種は long が既定 | 盤面(show 出力)を IOL から取るとコストが 100 系になる。紙面では Gi 前提の値に作り替えるか、IOL の値のまま出すかを決める |
| D3 | PortFast 構文(#35) | 15.2(4)E 系の文書は `spanning-tree portfast edge [trunk]`・`portfast edge default`・`portfast edge bpduguard/bpdufilter default`。Cat9300 17.15 ガイドは旧形(`portfast`・`portfast default`・`portfast trunk`)を記載。**ioll2 は旧形のみ受理(`edge` は % Invalid・P6 実測)** | ラボは旧形必須。紙面で edge 形を出すなら「機種による」と明示するか、旧形に統一 |
| D4 | root primary の算法(#28) | 「24576 未満の root がいれば最小値から 4096 引く」「1 未満が必要なら失敗」は 2960-X ガイドにある。Cat9300 17.15 ガイドには 24576 の文だけ。ネットワークエンジニアとして は 24576 の例と「既存より小さい値」のみで、4096 減の規則は書いていない。知識項目表の「それ以下なら」は Cisco 原文では「lower than(未満)」 | 項目文言を「24576 未満なら」に直すのが正確。24576 同値で MAC 負けの場合は文書で決まらない → 実測 |
| D5 | BPDU filter(global)のリンクアップ時送出数(#37) | 現行ガイドは「a few」のみ。「10 個」「11 個」は旧資料・コミュニティの記述で割れている。ネットエンジニアとして はこの送出自体に触れない | 数値は出題しない(または実測値を根拠にする) |
| D6 | BPDU 宛先 MAC(#2) | IEEE 形式は 01:80:C2:00:00:00。PVST+ は VLAN1 以外の BPDU を **01:00:0C:CC:CC:CD(SSTP)** へ 802.1Q タグ付きで送る(VLAN1 は両方の宛先へ送る)。ネットエンジニアとして・知識項目表は IEEE 形式のみ | PVST+ 前提の設問で「宛先は 0180.C200.0000」とだけ書くと不正確になり得る。**要ユーザ判断** |
| D7 | MST のインスタンス数・番号範囲(#22〜26) | C-MSTTN(旧資料)は「16 instances: one IST and 15 MSTIs」。Cat9k は 65(スタック当たり)。ネットエンジニアとして は IST+64(計 65)。番号範囲はネットエンジニアとして内でも 0〜4096(J-17・J-21)と 0〜4094(J-19)が混在 | 最大数・番号範囲は機種差があるため出題しないか、機種を明示 |
| D8 | cost の範囲(#30) | ネットエンジニアとして は 1〜20,000,000、Cisco は 1〜200,000,000(long 時)。short 時は 1〜65535 | 範囲の数値は出題しない |
| D9 | UDLD normal モード(#40) | ネットエンジニアとして「normal は err-disabled にしない」。Cisco は「片方向(Layer 1 で分からないもの)は undetermined で disable しない」「normal は光の誤配線(misconnect)を検出する」と書く。誤配線を検出した時に normal でも disable するかは今回読んだ文書の文言では断定できない | 「normal は一切 err-disable しない」と断定する設問は避ける。**要ユーザ判断** |
| D10 | root guard の syslog 名(#38) | Cisco の旧テクノート(CatOS 時代)は `%SPANTREE-2-ROOTGUARDBLOCK`、ネットエンジニアとして は `%SPANTREE-2-ROOTGUARD_BLOCK` | ログ文言を出すなら IOL の実物に合わせる(要実測) |
| D11 | port-priority の刻み(#31) | Catalyst IOS/IOS XE は 0〜240・16 刻み。NX-OS 系は 0〜224・32 刻みとの情報あり(照合は検索結果レベル) | ioll2 で実測し、紙面は 16 刻みに統一 |
| D12 | PVST+ の最大インスタンス数 | 2960-X= 128・ネットエンジニアとして= 128・Cat9k(17.2.1 以降)= 300 | 出題しないか機種を明示 |
| D13 | RSTP の 3 hello 失効(#14) | Cisco は明記。ネットエンジニアとして には記述なし | Cisco を根拠にしてよい |
| D14 | IOL のリンクダウン非伝播(#14・#17) | 既存メモ(BFD 変種の実測)で、IOL は片側 shutdown が対向のリンクダウンにならない。RSTP の「Alternate 即時切替」がラボでは 6 秒失効経由になる可能性 | L3(TS)で切替時間を採点するなら実測が前提 |
| D15 | mgmt VLAN の巻き込み(ラボ全般) | poc/stp: データ trunk が VLAN999 を運ぶと mgmt セグメントが STP に参加し Et3/3 が BLK になり得る(実測) | 既定規則どおり trunk allowed vlan 絞り必須(文書照合とは別の運用制約) |

## 実機で裏どりが必要な論点(CML PoC 候補・ioll2 / ioll2-xe)

優先度: A= 出題の正誤に直結 / B= 表示・指紋(採点 regex)に必要 / C= 任意。

| # | 優先 | 論点 | 確認方法の案 | 関連項目 |
|---|---|---|---|---|
| M1 | A | ioll2 の素の既定 STP モード(pvst か rapid-pvst か) | 設定なしで起動し `show spanning-tree summary` の 1 行目 | #20・D1 |
| M2 | A | `root primary` の境界: 現 root 32768→24576 / 16384→12288 / 4096→0 / 0→失敗(メッセージ文言)/ 24576 同値で MAC 負け / running-config に残る行 | 3 台で root の priority を段階的に変えて投入 | #28・D4 |
| M3 | A | `root secondary` は常に 28672 か(現 root が 28672 以下でも) | 同上 | #28 |
| M4 | A | port-priority の刻み(16/32)と範囲・**上流で変えると下流の RP が変わり、下流で変えても下流の RP は変わらない**こと | 2 本並列リンクで上流側/下流側それぞれ変更 | #5・#31・D11 |
| M5 | A | `spanning-tree pathcost method long` の受理・`Pathcost method used` 表示・Et コスト(2000000?)・MST では設定に関係なく long か | pvst/rapid/mst の各モードで summary と port 行を取る | #11・#32・D2 |
| M6 | B | `show spanning-tree summary` の文言(Portfast Default / EDGE 表記・BPDU Guard/Filter Default・Loopguard Default) | global 設定の有無で差分を取る | #34・#35 |
| M7 | B | BPDU filter(global): リンクアップ時の送出数・BPDU 受信で PortFast が外れる様子 / interface filter でループ成立 | CML のパケットキャプチャ | #37・#43・D5 |
| M8 | B | BPDU guard と BPDU filter を同一ポートに設定した時の優先 | interface に両方入れて BPDU を受ける | #43 |
| M9 | B | root guard の指紋: `show spanning-tree inconsistentports`・syslog ニーモニック・superior BPDU 停止後の復帰時間 | 下流 SW の priority を 0 にして root guard ポートへ | #38・D10 |
| M10 | B | loop guard の発火手段(対向 designated に interface bpdufilter 等)・`loop-inconsistent` 表示・syslog・復帰・global loopguard と interface guard root の併用時の挙動 | 三角形の Altn 側で発火させる | #39・#42 |
| M11 | B | UDLD が ioll2 にあるか・Et に global `udld enable` が効くか(光ポートのみの制約)・`show udld` の表示・CML で片方向リンクを作れるか | コマンド受理と表示だけでも先に確認 | #40・D9 |
| M12 | B | `errdisable recovery interval` の既定値・最小値・`show errdisable recovery` の表示 | bpduguard 発火後に recovery を有効化 | #41 |
| M13 | B | RSTP の Alternate 切替時間(対向 shutdown・自側 shutdown・リンク削除で比較) | ping 連打で断時間を測る | #14・#17・D14 |
| M14 | B | pvst⇄rapid-pvst 混在時の表示(`Peer(STP)` 等)と `clear spanning-tree detected-protocols` の要否 | 1 台だけ pvst に戻す | #19 |
| M15 | B | MST⇄PVST+ 境界(PVST simulation)の指紋: PVST 側に root を置いた時の inconsistent 表示・`spanning-tree mst simulate pvst` の有無 | 1 台を rapid-pvst のまま MST リージョンに接続 | #27 |
| M16 | C | Backup ポート・Shared リンクの再現(CML unmanaged switch で共有セグメント)・`Back`/`Shr` の表示 | 同一 SW の 2 ポートを unmanaged switch に接続 | #12・#16・#45 |
| M17 | C | Edge ポートの表示(`P2p Edge` の並び)・edge ポートで BPDU を受けた時に edge が外れること | portfast ポートに SW を接続(bpduguard なし) | #16・#45 |
| M18 | C | BPDU 宛先 MAC(VLAN1/その他 VLAN/MST)の実物 | CML キャプチャ | #2・D6 |
| M19 | C | MST インスタンス番号の受理範囲・最大数 | `instance 4094 vlan …` 等を投入 | D7 |
| M20 | C | `spanning-tree cost` の受理範囲・priority に 4096 の倍数でない値を入れた時のエラー文言 | コマンド投入のみ | #29・#30・D8 |
| M21 | C | TC の観測(`show spanning-tree detail` の topology change 回数・発生元ポート) | ポート flap で差分 | #10・#18 |

---

更新方法: 実測したら該当行の「実機」欄を ○+要点に書き換え、判定を更新する。実測ログの詳細は
[poc/stp/README.md](../poc/stp/README.md) に追記する(この表には要点だけ書く)。
