# STP-SERIES — STP シリーズ設計 (BL-076・L2 空白の本丸)

- 起点: 2026-07-29 ユーザ指摘「本プロジェクトの弱点 = L2(STP)」→ 棚卸しで確定
  (STP 主役問ゼロ・CAMPUS-TS-01 の脇役のみ)。同日「CCIE ラボにも STP は出るか」
  → 出る(CCIE EI blueprint 1.x campus L2: Rapid-PVST+/MST・PortFast/BPDU guard/
  Root guard/Loop guard・priority/cost チューニング)。**この方針(CCIE の出方に整合)で準備**。

## 1. シリーズ構成(3段・実技先行)

| # | 問題 | 難 | CCIE での出方との対応 |
|---|------|----|----------------------|
| ① | ENCOR-STP-BUILD-01: root 配置設計 + 保護機能(3SW 三角×2VLAN・rapid-pvst 統一・VLAN 毎 root primary/secondary・access へ portfast+bpduguard・想定ブロックポートの検証) | 3 | Deploy 型(仕様どおり正確に組む) |
| ② | gen_stp_ts.py: STP TS 生成器(故障= root乗っ取り(priority)/trunk へ portfast/bpduguard 発火 err-disabled 放置/cost・port-priority 改変で意図しない経路/mode 不一致(pvst⇄rapid)/MST region 不一致) | 4-5 | Operate 型(大シナリオ内で静かに壊れる) |
| ③ | STP-MST-01: MST 設計問(region 名/revision/instance マッピング指定・仕様書完全準拠形・REDIST-POLICY/DHCPTS で確立した監査スタイル) | 4-5 | CCIE らしさの本丸(精密性トラップ) |

- プラットフォーム: **ioll2-xe ×3〜4・telnet 採点**(LAG 問で確立済のパス)。
  ioll2 profile: データ 15 ポート(Et0/0..Et3/2)・mgmt=Et3/3。
- 発展合流: CAMPUS-TS-01 への STP 故障軸追加 / LAG(BL-003)との複合。

## 2. 決定性の設計原則(採点が壊れないための約束)

- **bridge ID の MAC 依存を排除**: 全問で priority を明示配布(root 4096 / secondary 8192 /
  その他 32768)。tie-break が MAC に落ちる構成は作らない → ブロックポート位置が
  seed から決定的に導出できる。
- リンクコストは IOL Ethernet(10M)の既定 cost=100 で均一 → パス優劣は priority と
  ホップ数だけで決まる(cost 改変は故障側の道具)。
- 三角形が最小完全形(閉路がないと STP は無意味)。ノイズ拡張は arena 同様の接ぎ木。

## 3. 採点設計

- 構造: `show spanning-tree [vlan X]` を Genie 構造化(★PoC で IOL 出力の適合確認)
  → root bridge ID / 各ポートの role(Root/Desg/Altn)・state を find/match。
- 効果: SVI 間 ping + **「どのリンクが転送に使われているか」**(mac address-table /
  ブロックポートの state) — RIB が無い L2 では「転送パスの実効」をこれで代替。
- 保護機能: err-disabled 検出(`show interfaces status err-disabled`)・
  bpduguard/portfast の config 監査(regex)。
- 負の要件(例: 「SW03 が root になってはならない」)は正の root 確認とペアにする
  (既存教訓: 負の要件単独採点は偽陽性)。

## 4. PoC 項目(リスク3点+α)

| # | 確認 | 方法 |
|---|------|------|
| P1 | rapid-pvst の構文・動作・VLAN 毎 root 分離 | day0 焼き込み→show |
| P2 | ブロックポート位置の決定性(priority のみで固定できるか) | SW03 の per-VLAN ALTN 位置を机上予測→実機一致確認 |
| P3 | bpduguard → err-disabled の発火と検出コマンド | trunk 対向ポートに bpduguard を仕込み boot 時発火 |
| P4 | MST: region 設定(name/revision/instance map)・不一致時の boundary 挙動・是正後の合流 | telnet で mode 切替+region 投入 |
| P5 | Genie `show spanning-tree` パーサの IOL 出力適合 | 収集 stdout を grade.py 機構でオフラインパース |
| P6 | ioll2 の `spanning-tree portfast` 系構文(edge 形か旧形か) | 実機 ? 補完 |

**★PoC 実施済(2026-07-29)・P1〜P6 全クリア** → 結果と確定指紋は [poc/stp/README.md](../../poc/stp/README.md)。
要点: ①priority 明示でブロックポート完全決定化 ②bpduguard/err-disabled 採点可 ③MST 不一致指紋= `Bound(RSTP)` ④Genie 両モード適合 ⑤**旧構文 `spanning-tree portfast`(edge 不可)** ⑥**必須設計規則= データ trunk の allowed vlan 絞りで mgmt VLAN999 を演習 STP から隔離**(さもないと mgmt 断・実測済) ⑦config 投入は pexpect 直叩き(プロンプト regex 確立)。
PoC ラボ `problems/_POC-STP` は再利用可。**→ 準備完了。次は §5 手順2(①構築問)から即着手できる。**

## 5. 実装順(着手時)

1. PoC(上記・半日未満) → 2. ①構築問(1セッション・実機フルサイクル) →
3. ②生成器(故障カタログは PoC 知見で確定) → 4. ③MST 設計問。

## 6. 方針改訂(2026-09-22・ユーザ承認)— 生成器 1 本に統合

§1 の 3 段(固定 BUILD-01 / TS 生成器 / MST 設計問)を **`topologies/gen_stp.py` → `GEN-STP-<seed>` の 1 本**に統合する。
ID から型(build/ts/mst)が割れない(RDFIELD と同じ運用)。紙面 P2 の計算器 `stp_model.py` を期待値の正典にする(紙面とラボで答えが一致)。

### 6.1 盤面(ioll2×4・ホスト無し)

```
   DS1 ===(2本)=== DS2        DS1/DS2 = 分配(VLAN ごとに root を分担)
    |  \         /  |
    |    \     /    |          AS1/AS2 = アクセス(2 系統上り)
   AS1     (X)     AS2         AS の Et1/x = エッジ(portfast/bpduguard 対象)
```
- DS 間 2 本 = port-priority の論点(上流で効く・M4)用。
- mgmt 隔離は二重: 全データ trunk に `allowed vlan <データのみ>` + Et3/3 に `spanning-tree bpdufilter enable`(BL-135 恒久策)。
- ホストは置かない。効果採点は SVI 間 ping → `show mac address-table` の学習ポートで転送経路を確認。

### 6.2 モードと段階

| 段階 | モード | 中身 | 難 |
|---|---|---|---|
| L1 | `--mode build --level 1` | rapid-pvst 統一・VLAN 毎 root primary/secondary・エッジ portfast+bpduguard | 3 |
| L2 | `--mode build` | 要件書駆動(VLAN X はリンク B を使う/アクセス向きは上位 BPDU 拒否/long 方式統一 等・手段は自由) | 4 |
| L3 | `--mode ts --faults 1〜3` | §6.3 故障カタログ | 4-5 |
| L4 | `--world mst / mst_pvst` | MST region 設計＋PVST+ 旧 SW 共存(CIST root を PVST 側より強くしないと PVSTSIM_FAIL) | 5 |

### 6.3 故障カタログ(L3)

A(実測済): root_hijack / secondary_only(M3) / pprio_downstream(M4・効いていない形) / rootguard_allvlan(M9) /
bpduguard_uplink(P3) / filter_beats_guard(M8) / mode_mismatch(M14・clear 片側) / mst_region(P4/M15) / cost_skew(M4d)。
B(PoC 第3回で確認): loopguard_trip(片側 bpdufilter→対向 LOOP_Inc。loop guard 無しは実ループ=IOL 耐性要確認) /
native_mismatch(PVID_Inc) / allowed_vlan_skew(VLAN 毎トポロジ割れ) / 4 台盤面の決定性(計算器 vs 実機・全 VLAN 全ポート)。

### 6.4 採点
- 構造: VLAN 毎 root・ポート role/state(Genie + raw regex)。期待値は stp_model.py から導出。
- 効果: SVI 間 ping → mac テーブルの学習 trunk。
- 負の要件は正の root 確認とペア。filter_beats_guard の効果は**監査用 AS1-AS2 access 直結ポート**を採点時 no shut → err-disabled を見る(PoC 第3回)。
- 過剰解降格(root guard 全削除・bpduguard 撤去など)= 暗黙の最小変更原則。
- 収束待ち: rapid 数秒/loop guard 約 5 秒/IOL 対向リンクダウン約 5 秒。errdisable recovery(300 秒)に依存しない。

### 6.5 パック統合
`gen_pack.LAB_GENRES["l2"]` に `GEN-STP`(build は構築スロット)・`units.yml` U-A3 `lab.genres`・`genres.yml` families l2。

### 6.6 実装順
PoC 第3回 → L3 TS(A 9 種の broken→fix→100) → build L1/L2(0→100・誤解法降格) → MST 世界。

### 6.7 PoC 第3回の結果(2026-09-22・poc/stp/README.md 第3回)
- 決定性 ✅(4 台 2 VLAN 24 ポートが計算器と全一致)・mac テーブルで経路採点 ✅・監査ポート方式 ✅(対向は PARK VLAN 99・guard 無し)。
- loopguard_trip ✅採用(IOL の実ループは嵐にならず mgmt 無事。誤解法は構造チェックで拾う)。
- allowed_vlan_skew ✅採用(遠回り故障)。**native_mismatch ✗不採用**(allowed を絞ると PVID_Inc が出ない)。
- mgmt の bpdufilter は STP 盤面の initial にだけ入れる(baseline 共通化は VLAN999 ループの危険)。
- 確定カタログ(L3)= A 9 種＋loopguard_trip＋allowed_vlan_skew の 11 種。

### 6.8 L3 TS 実装(2026-09-22・完了)
`gen_stp.py --mode ts`。故障 10 種(native_mismatch 不採用後の確定版。loopguard_trip・allowed_skew を含む)。
監査ポートは持ち込み機器 SW05(常時接続・spanning-tree vlan 1 priority 0)→ 正解状態= 接続ポート err-disabled。
配点= root 5×3・予備 root 2×3・role 3×12・不整合 1×4・持ち込み遮断 8・DS 監査 7×2・AS 監査 4×2・SVI 疎通 3×3。
監査は `show running-config | include ^interface Ethernet|spanning-tree|allowed vlan` の 1 本で guard/filter/許可 VLAN/cost を見る。
E2E と誤解法の結果は BACKLOG BL-076 行。次= build(L1/L2)= 同じ盤面で STP 設定を白紙にし設計書から組む。

### 6.9 build モード(L1/L2・2026-09-22・完了)
- 初期= STP 設定だけ白紙(全台 Rapid PVST+ 既定)・VLAN/trunk(allowed 絞り)/SVI/エッジ所属 VLAN は構築済み。
- L1= root/予備 root(数値指定・`root primary/secondary` マクロでも可)+エッジ PortFast/BPDU ガード。
- L2= 要件書(long 方式統一・DS 間 2 本の使い分け+個別コスト禁止= 上流 port-priority が唯一解・root guard・loop guard・自動復旧禁止)。
  採点に「使い分け」専用チェック(6 点)を追加(ts にも)。
- ★実測で変えた設計(RSTP の規定と異なる IOL 固有挙動= 論点にしない):
  1. 実行中の pvst→rapid 移行 → Desg BLK 固着(`clear spanning-tree detected-protocols` で解ける)・約 40 秒周期の TC・
     IOL プロセス停止 2 回(`UNIX-EXT-SIGNAL: Segmentation fault(11), Process = VMATM Callback`→ CML iol-runner も panic)。
     起動時 rapid なら素直に収束 → 移行は出題しない(`PVST_START=False`。TS の mode_mismatch は 1 台だけなので E2E 通過のまま残す)。
  2. 持ち込み機器(priority 0)をデータ VLAN に置くと、一括設定中に bpduguard が発動した AS が
     `Root ID Priority 1 / Port 0 ()`(root port 無しの古い root 情報)を保持し続け、DS の root guard が ROOT_Inc のまま。
     clear・上りの shut・priority 再投入でも解けず、`no spanning-tree vlan N`→戻すでのみ解消(2/2 再現・手動の単発操作では再現せず)。
     → 持ち込み機器は駐車 VLAN 99(AS にだけ作り trunk に載せない)のエッジへ。影響が VLAN99 に閉じる。
  3. 持ち込み機器を最弱 priority にすると root port 側になり、RSTP では定期 BPDU を出さない → 後から入れた bpduguard が発動しない。
     ioll2 には `event manager` が無い(Invalid input)ので定期的なポート上げ下げもできない → root のまま駐車 VLAN に閉じ込める。
- 罠(実測・論点として使える): 持ち込み機器がデータ VLAN の root だと `root primary` は `% Failed to make the bridge root` で失敗する
  (M2 と同じ)。現行の盤面では駐車 VLAN に閉じるため出ない(紙面 P2 で扱う)。

### 6.10 L4 = MST 世界(2026-09-22・完了)
`gen_stp.py --world mst`(実体 `gen_stp_mst.py`)。SW01〜03= MST リージョン(名前・revision・inst1= VLAN A,C / inst2= VLAN B)・SW04= MST 非対応の旧機(Rapid PVST+・long)。
CIST+inst1 の root= x・inst2 の root= y(リンク2 は上流 port-priority)。持ち込み機器は置かない。
- ts 故障 13 種: m_rev / m_name / m_map / m_mode(SW03 が rapid)/ m_unmapped / m_pvstsim / m_cist / m_pprio_down / m_cost / m_allowed_hole / loopguard_trip / guard_swap / bpduguard_uplink。
- build: 初期は全台 rapid 白紙 → MST 化(rapid→MST の実行時移行は安定)。
- 採点: CIST/inst1/inst2 の root・予備・region 設定・MST 3 台×3 インスタンスの役割(DS の Et0/3 は `Bound(PVST)`・内部に Bound が無いこと)・
  SW04 の VLAN ごとの役割と `Root ID Priority 24576`・不整合 0・inst2 のリンク2・SW04 long・監査・SVI 疎通。
- 裏どり: PVST シミュレーション規則・allowed の穴(「同じインスタンスの VLAN は一緒に外せ」)・region の 3 属性= Cisco 公式と実測一致。
  SW04 の `Peer(STP)` は公式に記述が無いので採点しない。
- E2E: 93001 45→100 / 93002 54→100 / 93004 68→100 / 93005 67→100 / 93006 73→100 / 93007 85→100 / build 93003 13→100(region 名違い 86・下流 port-priority 90)。
