# U-A3 STP — 知識項目表(単元シラバス)

台帳: [CURRICULUM.md](../CURRICULUM.md) U-A3。資格= CCNA 2.5 / ENCOR 3.1.c / CCIE 1.1.e。
**この表が「網羅的」の物差し**。P1(穴埋め)は各項目を少なくとも 1 セクションで空欄または本文に載せる。
サブジャンル(セクション)= 基礎 / RSTP / PVST+・MST / チューニング / 保護機構 / 読解。

凡例= P1 列: 穴埋め KB `cloze_kb_stp.py` の kind(`t_basics` 等)。P2 列: 選択問 `gen_paper_stp.py`(`--shape stp`・BL-216)の kind。○= 本文に載る(空欄候補)・△= 本文に載るが空欄にしない・✗= 未収録。

## 1. 基礎(802.1D)— kind `t_basics`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 1 | STP の目的(L2 ループ・ブロードキャストストーム・MAC テーブル不安定) | ○ t_basics | ○ s_basic | — |
| 2 | BPDU(Configuration/TCN)・送信元は root・宛先 MAC 01:80:C2:00:00:00 | ○ t_basics | ○ s_basic(IEEE 宛先のみ・U2) | — |
| 3 | Bridge ID= priority(4 bit・4096 刻み)+ extended system ID(VLAN)+ MAC | ○ t_basics / t_read | ○ s_basic / s_read | — |
| 4 | Root bridge 選出= 最小 BID(priority → MAC) | ○ t_basics | ○ s_elect / s_basic | L1 |
| 5 | Root port 選出= root path cost → 送信元 BID → 送信元 port priority → 送信元 port ID | ○ t_basics / t_tuning | ○ s_elect / s_basic | L1 |
| 6 | Designated port(セグメントごとに 1 つ・root の全ポート) | ○ t_basics | ○ s_elect / s_basic | L1 |
| 7 | Non-designated(Blocking)port | ○ t_basics | ○ s_elect | L1 |
| 8 | ポート状態 Disabled/Blocking/Listening/Learning/Forwarding と各段の動作 | ○ t_basics | ○ s_basic | — |
| 9 | タイマ hello 2 / forward delay 15 / max age 20・収束 30〜50 秒 | ○ t_basics | ○ s_basic | — |
| 10 | TCN BPDU と MAC エージング短縮(forward delay) | ○ t_basics | ✗(Cisco 側の根拠が要約のみ・未出題) | — |
| 11 | パスコスト(short: 10M=100・100M=19・1G=4・10G=2 / long 802.1t: 1G=20000・10G=2000) | ○ t_tuning | ○ s_basic / s_elect | L1 |

## 2. RSTP(802.1w)— kind `t_rstp`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 12 | ポート役割 Root/Designated/Alternate/Backup | ○ t_rstp | ○ s_rstp | L1 |
| 13 | ポート状態 Discarding/Learning/Forwarding(3 状態) | ○ t_rstp | ○ s_rstp | — |
| 14 | 全スイッチが hello ごとに BPDU を出す・3 回欠落で失効(6 秒) | ○ t_rstp | ○ s_rstp | — |
| 15 | Proposal/Agreement(sync)による即時 forwarding | ○ t_rstp | ○ s_rstp | — |
| 16 | Edge port(PortFast)と link type point-to-point(全二重)/shared(半二重) | ○ t_rstp / t_guard | ○ s_rstp | L1 |
| 17 | Alternate による root port の即時切替 | ○ t_rstp | ○ s_rstp | L3 |
| 18 | TC 処理= 非 edge ポートの MAC フラッシュ・TC While | ○ t_rstp | ○ s_rstp | — |
| 19 | 802.1D スイッチとの互換(ポート単位で 802.1D に落ちる) | ○ t_rstp | ○ s_rstp / s_ts | L3 |

## 3. PVST+ / Rapid-PVST+ / MST(802.1s)— kind `t_modes`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 20 | Cisco 既定= PVST+(VLAN ごとに 802.1D)・`spanning-tree mode rapid-pvst` | ○ t_modes | ○ s_modes(版を示す・U1) | L1 |
| 21 | PVST+ の負荷分散(VLAN ごとに root を変える) | ○ t_modes / t_tuning | ○ s_modes | L2 |
| 22 | MST= 複数 VLAN を 1 インスタンスに束ねる・インスタンスごとに 1 本の木 | ○ t_modes | ○ s_modes | L1 |
| 23 | MST リージョン= name・revision・VLAN→instance 対応表の 3 つが一致 | ○ t_modes | ○ s_mst / s_ts | L3 |
| 24 | IST(instance 0)と CIST・リージョン境界(boundary port) | ○ t_modes | ○ s_mst | L3 |
| 25 | `spanning-tree mst configuration` / `name` / `revision` / `instance N vlan …` / `show spanning-tree mst configuration` | ○ t_modes | ○ s_modes | L1 |
| 26 | インスタンス未割当 VLAN は IST(instance 0)に属する | ○ t_modes | ○ s_mst | L3 |
| 27 | MST と PVST+ の相互接続(PVST simulation) | △ t_modes | ○ s_ts | — |

## 4. チューニング(root 配置・パス選択)— kind `t_tuning`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 28 | `spanning-tree vlan N root primary`= 24576(現 root が 24576 未満、または同値で MAC 負けなら現 root より 4096 小さい値・1 未満が必要なら失敗・一度きりの計算) / `secondary`= 常に 28672 | ○ t_tuning | ○ s_tuning | L1 |
| 29 | `spanning-tree vlan N priority X`(4096 の倍数・既定 32768) | ○ t_tuning | ○ s_basic | L1 |
| 30 | `spanning-tree cost` でポートコストを変える(自分の root port 選択に効く) | ○ t_tuning | ○ s_tuning | L2 |
| 31 | `spanning-tree port-priority`(既定 128・16 刻み)は**対向**の root port 選択に効く | ○ t_tuning | ○ s_tuning | L2 |
| 32 | `spanning-tree pathcost method long` | ○ t_tuning | ○ s_tuning | — |
| 33 | タイマ変更は root で行う(`spanning-tree vlan N hello-time/forward-time/max-age`)・diameter | ○ t_tuning | ○ s_basic(diameter は未) | — |
| 34 | `show spanning-tree root` / `show spanning-tree vlan N` / `show spanning-tree summary` | ○ t_read | △ s_read(vlan のみ・summary 未) | L1 |

## 5. 保護機構— kind `t_guard`

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 35 | PortFast(listening/learning を飛ばす・端末ポート限定・`spanning-tree portfast` / global `portfast default`) | ○ t_guard | ○ s_guard | L1 |
| 36 | BPDU guard(BPDU 受信で err-disabled・`spanning-tree bpduguard enable` / global `portfast bpduguard default`) | ○ t_guard | ○ s_guard / s_ts | L1 |
| 37 | BPDU filter(BPDU を送受信しない・global は portfast ポートのみ・受信で portfast 解除) | ○ t_guard | ○ s_guard | L3 |
| 38 | Root guard(designated 側・superior BPDU で root-inconsistent・自動復帰) | ○ t_guard | ○ s_guard / s_ts | L2 |
| 39 | Loop guard(root/alternate 側・BPDU 途絶で loop-inconsistent・片方向リンク対策) | ○ t_guard | ○ s_guard / s_ts | L3 |
| 40 | UDLD normal/aggressive(片方向リンク検出・err-disabled) | ○ t_guard | ○ s_guard(Cisco 公式の見解・U3) | L3 |
| 41 | errdisable recovery(`errdisable recovery cause bpduguard`・interval 既定 300 秒) | ○ t_guard | ○ s_guard | L1 |
| 42 | Loop guard と Root guard は同一ポートに同時不可 | △ t_guard | ○ s_guard | — |
| 43 | BPDU guard と BPDU filter の違い(遮断 vs 無視) | ○ t_guard | ○ s_guard / s_ts | L3 |

## 6. 読解— kind `t_read`(世界機構: 盤面で root port が変わる)

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 44 | `show spanning-tree vlan N` の Root ID / Bridge ID / This bridge is the root | ○ t_read | ○ s_read | L1 |
| 45 | ポート行 Role(Root/Desg/Altn/Back)・Sts(FWD/BLK/LRN)・Cost・Prio.Nbr・Type(P2p/Shr/Edge) | ○ t_read | ○ s_read | L1 |
| 46 | priority 表示値= 設定値 + VLAN ID(extended system ID) | ○ t_read | ○ s_read | L1 |
| 47 | root path cost の合算(自分のコスト + 上流の root path cost) | ○ t_read / t_tuning | ○ s_elect / s_read | L2 |

## 7. 追加項目(2026-09-22・問題集の論点の洗い出しから・BL-216)

| # | 項目 | P1 | P2 | L |
|---|------|----|----|---|
| 48 | EtherChannel はスパニング ツリーから 1 本の論理リンクとして扱われる | ✗ | ○ s_basic | — |
| 49 | 起動直後は自分をルート ブリッジとみなして BPDU を送る | ✗ | ○ s_basic | — |
| 50 | 規格番号(802.1D / 802.1w / 802.1s) | △ | ○ s_rstp / s_modes | — |
| 51 | trunk⇔access 誤接続時のスパニング ツリーの反応(不一致による inconsistent) | ✗ | ✗(未実測) | L3 |
| 52 | PortFast はトランクにも `spanning-tree portfast trunk` で設定できる・trunk への `spanning-tree portfast` は無効 | ✗ | ○ s_guard | L1 |

## ラボ段階(参考・BL-076 設計書 STP-SERIES.design.md)

- L1: 3 台 IOSvL2 三角・root 指定・PortFast/BPDU guard・`show spanning-tree` で役割確認(難 2)
- L2: 4〜5 台・VLAN ごとの root 分散・port-priority/cost でパス指定・MST リージョン設計(要件書・難 4)
- L3: TS 生成器(root 乗っ取り・MST リージョン不一致・BPDU filter 事故・loop guard 発火・UDLD)(難 4〜5)
- L4: CAMPUS-TS-01(既存・HSRP/OSPF と同居)

★ラボ制約(メモリ・BL-076 PoC): priority 明示でブロックポート決定化・err-disabled 採点可・MST 不一致指紋= Bound(RSTP)・
旧構文 portfast(edge 不可)・**trunk allowed vlan 絞りで mgmt VLAN999 を隔離**(さもないと mgmt 断)。
