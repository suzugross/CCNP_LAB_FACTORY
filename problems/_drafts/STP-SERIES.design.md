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

## 7. 構築問の要件をシードで振る(BL-220・2026-09-26 調査)

### 7.1 現状の切り分け
`design()` が振っているのは**値**だけ。要件書の行の並びは毎回同じ。

| seed で動く | 直書きで固定 |
|---|---|
| VLAN ID 3 個・SVI の第 2 オクテット | STP モード= Rapid PVST+ |
| どちらの DS が root か(x/y の入れ替え・2 通り) | root 配置の**型**= 2 VLAN が片方・1 VLAN が反対 |
| 持ち込み機器の接続先 AS とポート | DS 間の使い分け= A/C→リンク1・B→リンク2(向き固定) |
| エッジポートの所属 VLAN | 寄せる手段= 上流 port-priority 一択(要件で cost 禁止) |
| — | 保護= DS 間 loop guard / AS 向き root guard / エッジ portfast+bpduguard |
| — | パスコスト方式(L2 は long 固定)・err-disabled は自動復旧させない |

### 7.2 振れる軸(安全度順)
| 軸 | 実現 | 採点の影響 | 判定 |
|---|---|---|---|
| root 配置の型(2-1 / 1-2 / どの VLAN が単独か) | `design()` に型を抽選 | `expected_roles` が `d["root"]` から計算するので自動追従 | ◎ |
| 使い分けの向き(単独 VLAN をリンク1 に寄せる世界) | `base_state` の port-priority 付与先を可変に | steer チェックが `Et0/1`/`Et0/0` 直書き → 引数化 | ◎ |
| パスコスト方式 long / short | 要件表＋`long` チェックの反転 | 全リンク同速度なので役割は不変・安全 | ◎ |
| 保護機構の割当(loop guard を AS 上りに / root guard を DS 間にも) | 付与先を表で持つ | DS/AS 監査 regex を表から生成 | ○ |
| 寄せる手段の自由化(port-priority でも cost でも可) | 要件文から cost 禁止を外す | `common_audit` の cost 全面禁止を「設計行以外の cost 禁止」へ | △ regex が繊細 |
| err-disabled の自動復旧を要件化する世界 | recovery cause/interval | 復旧すると持ち込み機器チェック(err-disabled のまま・8点)が消える | ✗ 競合 |

### 7.3 触り所
`design()` に世界キー → `expected_roles()`(`pp` が VLAN B・`Et0/1` 直書き) → `base_state()` → `grading()`(steer / DS 監査 / AS 監査 / long / errdis の 5 箇所) → `task_md_build()`(要件表) → `selftest()` に世界軸。
`build_fix()` は `base_state` から導出しているので自動で追いつく。

### 7.4 注意
- TS モードも `design`/`base_state` を共有するため、世界軸を入れると **TS の盤面も自動で多様化**し、実機 E2E の対象が世界数だけ増える。まず build だけ振るのが現実的。
- `expected_roles` はイメージに関わらず 10M(cost 100)でモデル化している。役割判定は全リンク同速度なので問題ないが、`cost_ovr` 世界を入れるなら **IOSvL2(Gi・short=4)用の値表**が必要。
- MST 側も `inst_vlans()` が `{1:[A,C], 2:[B]}` 固定。同じ手当てで「どの VLAN が単独インスタンスか」「3 VLAN を 3 インスタンスへ」を振れる。
- 先例= `gen_v6addr_build.py`(LAN ごとに世界を抽選し要件文と採点を分岐)。

## 8. 別系トポロジによる難易度・論点の拡張(BL-221・2026-09-26 調査)

### 8.1 基盤の余裕(調査結果)
- **計算器は無改造で通る**: `stp_model.Topo.solve()` は Dijkstra + リンクごとの designated 判定で、任意グラフ(三角・リング・多段)に対応。制約は連結であることだけ。
  ただし役割語彙は Root/Desg/Altn の 3 つで **Backup が無い**(共有セグメントを作る系だけ追加が必要)。
- **ポート数の余裕**: `device_profiles` の L2 プロファイルは ioll2-xe / iosvl2 ともに **データ 15 ポート(Et|Gi 0/0〜3/2)＋mgmt は slot15(3/3)固定**。1 台 6 リンク＋エッジ 4 本でも余る。
- **非管理スイッチ(ハブ相当)が既に置ける**: `problem.yml` の `lab.switches: [HUB1]` で `unmanaged_switch` ノードが生える(`gen_cml_lab.py`)。共有セグメント系は基盤追加なしで組める(BPDU を透過するかは PoC 必須)。
- **台数**: 現行 stpts= 7 ノード(SW4+持ち込み+MGMTSW+EXTC)。1 台増えるごとに +1。CML Personal の同時 20 では 6 スイッチ系(9 ノード)が上限目安・Personal Plus(40)なら余裕。
- **IOSvL2 は起動が遅い**(BL-219 で既定を iosv に寄せた)。台数を増やすほど bringup が伸びるので、軽い系ほど IOSvL2 向き。

### 8.2 系の候補
| 系 | 台数 | 骨格 | 難 | 新しく出せる論点 | コスト |
|---|---|---|---|---|---|
| T1 三角 | 3(+持ち込み) | DS2+AS1・リンク3 | 2〜3 | 最小の root/RP/DP 選出・cost と port-priority の基礎。**速筋レーン(BL-145)向けの短時間構築** | 小 |
| T2 リング | 4 | 環状・階層なし | 4 | Altn の位置がコストの積み上げで決まる・BID 順が効く・root 位置で塞ぐ辺が回る | 小〜中 |
| T3 2 層横広 | 6 | DS2+AS3〜4 | 4 | VLAN 毎負荷分散が複数 AS に及ぶ・AS ごとに別リンクへ寄せる要件 | 中 |
| T4 3 層 | 6 | コア2+分配2+アクセス2 | 5 | root はコア・分配に root guard・コア間 loop guard・2 段の RP 決定 | 中〜大 |
| T5 共有セグメント | 3〜4+HUB | 1 台の 2 ポートを同一セグメントへ | 5 | **Backup ポート**(現行盤面では出せない唯一の役割)・BPDU の自己受信 | 中＋PoC |
| T6 EtherChannel 併用 | 4 | DS 間 2 本を Po に束ねる | 5 | STP から見て 1 論理リンク・Po の cost・U-A2(BL-003)と合流 | 中 |
| T7 旧機混在 | 5 | 一部を day0 から PVST+ | 5 | 版の境界・PVST+ 島の扱い。★実行中の移行は IOL が不安定(§6.9)なので day0 固定に限る | 中 |

### 8.3 触り所
盤面定数 `LINKS`/`POS`/`DSLINK`/`UPLINK`/`DOWNLINK`/`EDGE`(現在は module global を `set_image()` が組み立て)をトポロジ定義オブジェクトに束ねる。
採点側で座標を直書きしている箇所= DS の root guard 先(`0/2`・`0/3`)・不整合の `0/[0-3]` 監査・steer の `0/1`・疎通の SW03→SW04・持ち込み機器の `EDGE`。
day0 描画(`render`)は `ifn(i)` のスロット換算なのでトポロジ非依存。`gen_pack` の genre ごとに `nodes` 申告を更新。

### 8.4 PoC で先に潰す点
1. CML の `unmanaged_switch` が **BPDU を透過するか**(T5 の前提。透過しなければ T5 は不成立)。
2. T5 で実機が本当に `Backup` 役を出すか(`show spanning-tree` の表記・`stp_model` に Backup 役を足す根拠)。
3. T6 の Po 上で PVST+ の VLAN 毎 cost/port-priority が期待どおり効くか(IOSvL2 で LACP を含む)。
4. T4/T3 の 6 台構成で IOSvL2 の bringup 時間と SVI down 固着(BL-219 の副作用)が許容範囲か。

### 8.5 推奨順
T1(軽い・速筋レーンの穴を埋める) → T2 または T4 のどちらか 1 系 → T5 は PoC 価値が高い(紙面 P2 の Backup 論点の裏どりにもなる)。

### 8.6 T4 = 3 層キャンパス構築問の実装(2026-09-26・完了)
`gen_stp.py --world 3tier --mode build`(実体 `topologies/gen_stp_3tier.py`・ID は `GEN-STP-<seed>` のまま・難5・IOSvL2 既定)。
盤面= SW01/SW02 コア・SW03/SW04 分配・SW05/SW06 アクセス・SW07 持ち込み機器、リンク 10 本
(コア間 1・コア↔分配 4 のフルメッシュ・分配間 1・分配↔アクセス 4)。9 ノード(MGMTSW+EXTC 込み)。SVI はアクセス層のみ。

要件書の骨組み(値は seed・構成は固定):
- root= コア(VLAN A・C は x、B は y。24576)、予備 root= 反対のコア(28672)。アクセスは既定のまま。
- **分配は VLAN ごとに片方だけ 36864**。これが ①分配間リンクのブロック側 ②アクセスの上りが通る側 を同時に決める
  (= 2 段の負荷分散)。既定のままだと両方が MAC 依存になるので、要件に「MAC に依存せず決めること」を明記した。
- 保護は**方針**で与える(ポートを列挙しない)= 上位層へ向くポートと同一層のスイッチ間リンク= loop guard /
  下位層へ向くポート= root guard / エッジ= portfast+BPDU ガード(自動復旧なし)。20 ポートを解答者が分類する。
- パスコスト方式 long で統一・ポート単位の cost / port-priority は使用禁止(監査で降格)。
- 配点(合計 100)= root 3×3・予備 3×2・分配の 36864 3×2・役割 18×2・不整合 6×1・持ち込み機器 7・
  監査 core 2×3/dist 2×5/acc 2×3・errdisable recovery 2・SVI 疎通 3×2。44 チェック・収集コマンド 35。
  `long` は監査(`show running-config | include …`)に畳んで `show spanning-tree summary` の収集を省いた。

決定性(§2)の作り込み: どのセグメントも rpc か **設定した BID の差**で決まり MAC 比較に落ちない。
selftest は **MAC の並びを逆にした計算と役割が一致すること**を全 seed で検査する(iol/iosv 各 300 seed・600 件 NG=0)。

実機 E2E(seed 94001・IOSvL2×7):
- 基線(白紙) **16** → 模範解 `stp_ops.py fix` で **100**。
- 誤解法①「分配の priority を振らず MAC 任せ」= **78**。実測では SW03 が VLAN110/186 でも Desg 側に転び、
  設計とは逆(= 上りの寄せ先も逆)。3 本の 36864 チェック＋役割 8 本が落ちる。
- 誤解法②「方針の取り違え= root guard を上りに・loop guard を下りに(SW03 のみ)」= **82**。
  ★実機知見= root guard を上りに付けると**その上りが全 VLAN で Root Inconsistent**。さらに SW03 の
  ルートパスコストが上がった結果、**下位のアクセス側 BPDU が優位になり、まだ root guard のままだった
  アクセス向きポート(Gi1/0)まで VLAN83 で Root Inconsistent に巻き込まれた**(不整合 4 本)。
  → 方針型の要件は「1 ポートの取り違えが層をまたいで波及する」ので 難5 の題材として機能する。
- パスコスト長形式の確認= IOSvL2 の Gi は long で **20000**(short 4)。

パック= ジャンル `stp3build`(9 ノード・`--image iosv` 既定・group は `stp-build`)。★9 ノードは **BIG_NODES(9)以上= 大型スロット**扱いで、相方のラボは 4 台以下・追加枠なし(2026-09-26 dry-run で確認)。ただし 2026-09-27 の Personal Plus(40 ノード)化で、この制限は**予算が `BIG_RULE_BUDGET`(20)以下のときだけ**に変わった(別作業)。build ジャンルなので構築スロット(`--build-rate`)経由でしか出ない。既定の `--lab-genres` には入れず、
`--profile U-A3` か明示指定で出る。`units.yml` の U-A3 に追記済み。
残(BL-221 の続き)= TS モード(故障カタログを 3 層向けに作り直す)・T1 三角(難2・速筋レーン)・T5 共有セグメント(PoC 先)。

## 9. T4 3 層盤面の TS モード 設計(BL-221 の続き・2026-09-26 準備・**未実装**)
`gen_stp.py --world 3tier --mode ts`。盤面・採点表・要件書は構築版(§8.6)をそのまま使い、
**base_state(設計どおり)に故障を 2〜3 個注入**する形(2 層盤面・MST 世界と同じ作り)。難5。

### 9.1 故障カタログ(案・★= 3 層固有で 2 層盤面に無い形)
| 種別 | 注入 | 指紋(解答者が見るもの) |
|---|---|---|
| `t_core_prio_swap` | コアの priority を VLAN 間で入れ違いに | root が設計と違う VLAN がある |
| `t_dist_weak_missing` | 分配の 36864 を 1〜2 VLAN ぶん削除 | 分配間のブロック側とアクセスの上りが設計と逆(MAC 任せ)。初出題時の誤解法と同じ形= **78 点相当** |
| `t_dist_weak_wrong_vlan` | 36864 を別の VLAN に付け替え | 一部 VLAN だけ上りが逆 |
| ★`t_rootguard_up` | root guard を分配の上りに付ける(loop guard と入れ替え) | **上りが全 VLAN で Root Inconsistent**＋コスト増の連鎖で下向きポートまで巻き込む(§8.6 実測) |
| ★`t_loopguard_down` | 下向きを loop guard にする(root guard 無し) | **STP の状態は正常**・監査だけ落ちる= 要件違反型 |
| ★`t_acc_priority` | アクセスに低い priority を振る | 分配の root guard が発動しアクセスの上りが root-inconsistent = その VLAN が全断 |
| `t_cost_bump_dist` | 分配の上りに VLAN 単位 cost | その VLAN が他コア経由の遠回りになる(監査の cost 禁止にも触れる) |
| `t_allowed_hole` | 分配↔アクセスの allowed から 1 VLAN 抜く | STP 正常のまま 1 VLAN だけ不通(層が 3 つなので切り分けが増える) |
| `t_mode_pvst` | 1 台だけ起動時から `mode pvst` | 境界で相互運用に落ちる(★実行中の移行は不安定なので day0 固定に限る・§6.9) |
| `t_bpduguard_uplink` | アクセスの上りに bpduguard | 上り 1 本が起動以来使われない(err-disabled) |
| `t_loopguard_trip` | コア間か分配間の片側に bpdufilter | loop-inconsistent(2 層で実証済みの手法・コア間は root を含むので★要 PoC) |
| `t_pathcost_short` | 1 台だけ short 方式 | 2 ホップの比較が壊れる(★long/short 混在の効き方は要 PoC) |

排他(同時に選ばない): {`t_rootguard_up`, `t_loopguard_down`, `t_loopguard_trip`}(同じポートの guard を奪う)／
{`t_dist_weak_missing`, `t_dist_weak_wrong_vlan`}／{`t_core_prio_swap`, `t_acc_priority`}(どちらも root 位置に効く)。

### 9.2 症状文(不親切に・keep_ask 方針)
「特定 VLAN の通信が分配層で遠回りしている」／「アクセスの上り 1 本が起動以来使われていない」／
「点検で不整合状態のポートが報告された」／「特定 VLAN だけアクセス間で疎通しない(STP の状態は正常に見える)」。
故障種ごとに 1 文を対応させ、同文は重複排除して並べる(2 層・MST と同じ `SYMPTOM` 表)。

### 9.3 採点・難易度
構築版の 44 チェックをそのまま流用(root/予備/36864/役割/不整合/持ち込み機器/監査/errdisable/疎通)。配点も同じ。
難5 固定・故障は 2〜3(台数が多く収集 35 コマンドあるため 4 以上にはしない)。パックのジャンルは `stp3ts`(group `stp-ts`・9 ノード)。

### 9.4 着手時の段取り
1. **PoC(実機)を先に**: ①`t_loopguard_trip` をコア間で(root を含む区間での loop-inconsistent) ②`t_pathcost_short` の混在挙動
   ③`t_acc_priority` で root guard が確実に発動する priority 値。→ `poc/stp/README.md` 第 6 回として記録。
2. 注入関数 + `SYMPTOM` + 排他表 → selftest(故障が config に現れる・期待役割が壊れる・採点表が組める)。
3. 実機 E2E= 全故障 broken→`stp_ops.py fix`→100、加えて誤解法 1 本の降格確認。
4. CATALOG 追記・`units.yml` と `gen_pack` に `stp3ts` 追加・CURRICULUM §5 に 1 行。

## 10. 保護機構の「記述方式」を要件軸にする(BL-222・2026-09-26 準備・**未実装**)
初出題(GEN-STP-9444)のレビューで出た穴= 要件書は「実現手段は問わない」なのに、監査は
**インタフェース配下の `spanning-tree guard loop` 行**を要求するため、グローバル既定で同じ挙動を作った解答が
実機の状態が等価でも減点される。対象コマンドは 3 つ:

| コマンド | 効く範囲 | 3 層盤面での使い道 |
|---|---|---|
| `spanning-tree portfast edge default` | **access ポートだけ**(trunk には効かない) | アクセスのエッジ 4 本ぶんを 1 行で(上りの trunk は無影響なので安全) |
| `spanning-tree portfast edge bpduguard default` | portfast が有効なポート | 同じくエッジ 4 本ぶんの BPDU ガード |
| `spanning-tree loopguard default` | **全ポート**(portfast ポートは対象外) | 上り・同層の loop guard を 1 行で。下向きは IF で root guard を明示して上書き(★排他の優先関係は要 PoC) |

### 10.1 採点を「実効状態」に寄せる(推奨)
方式に依存しない監査へ移す:
- 既定の有効/無効= `show spanning-tree summary` の該当行(`Portfast Default` / `PortFast BPDU Guard Default` / `Loopguard Default`)。
- ポートごとの実効= `show spanning-tree detail` を 1 ノード 1 回収集し、ポートのブロック内に
  `Loop guard is enabled` / `Root guard is enabled` 相当の行があるかで判定(★出力書式は要 PoC。
  detail に出なければ `show spanning-tree interface <IF> detail` に落とすが、収集が 20 本/台 増えるので代表ポートに絞る)。
- これなら **method=port / global のどちらでも同じチェックで通る**。既存の port 方式の E2E を再走して等価を確認する。

### 10.2 要件軸 `--guard-style` を足す(BL-220 の要件世界軸と同じ機構)
- `port`(現行)= 「ポート単位で設定する。グローバル既定は使わない」と要件に明記 → 現行の監査でよい。
- `global`= 「可能な範囲はグローバル既定で与え、例外だけポート単位で書く」→ 実効監査＋ summary の既定行を要求。
- `any`= 「手段は問わない」と書き、採点は実効のみ(10.1 の監査だけ)。
seed で振れば「同じ盤面でも要件書の締め方が変わる」= BL-220 の狙いにそのまま乗る。

### 10.3 注意
- `loopguard default` は**全ポート**に効くため、エッジ(portfast)を除く 20 ポートが対象になる。下向きに root guard を
  明示しないと「下りも loop guard」になり要件違反 → `global` 世界でも下向きの明示は必須(そこが解答の山になる)。
- 2 層盤面(`gen_stp.py` の L2/L4)にも同じ穴がある。10.1 の監査に寄せる時は 3 層と一緒に直すか、
  3 層で実証してから移植するかを決める(移植時は 2 層の E2E 全数を再走)。

### 9.5 実装記録(2026-09-27・§9 の設計から変えた点を含む)
`gen_stp.py --world 3tier --mode ts`(実体 `gen_stp_3tier.py`)。故障 12 種・排他 4 組・`DAY0_ONLY={t_mode_pvst}`。
fix.json に **`break`**(故障を稼働中の盤面へ入れる conf)を持たせ、`stp_ops.py break <ID>` で注入できるようにした
(同じ seed で `--fault` を変えて再生成→注入→採点→fix→採点を 1 台の盤面で回すため)。
PoC 第6回(poc/stp/README.md)の結果で決めたこと:
- `t_loopguard_trip` はコア間(PoC T1= 両コアが相手の VLAN で孤立)。`t_acc_priority` は 4096/20480/28672 を抽選し、
  28672 のときは症状文を「状態に異常は無いが設計書に無い設定」に変える(PoC T3)。
- `t_cost_bump_dist` の値は **long の 1 リンク × 3**(iosv 60000 / iol 6000000)= 予備コア経由(2 本)の方が安くなる値。
  2 層盤面の 250〜500 は short 前提なので流用しない。
実機 E2E(`GEN-STP-94002`・port 方式・1 台の盤面へ break→fix で 4 バッチ):
- `t_core_prio_swap`+`t_dist_weak_missing`+`t_rootguard_up` = **61 → 100**
- `t_acc_priority`(20480)+`t_cost_bump_dist`+`t_allowed_hole`+`t_bpduguard_uplink` = **68 → 100**
  (分配 2 台の不整合と VLAN32 の SVI 間疎通断・err-disabled の上りは実効チェックで落ちる)
- `t_loopguard_down`+`t_dist_weak_wrong_vlan`+`t_pathcost_short` = **75 → 100**(この組では予備コアにも不整合が出た= 組合せの波及)
- `t_loopguard_trip` = **79 → 100**(両コアの不整合・分配の役割 6 本)
- day0 の検証= 新規に立てた `GEN-STP-94003`(global 方式・`t_mode_pvst`+`t_loopguard_down`)= **62 → 100**。
  ★`t_mode_pvst` を分配に当てると、**隣接 5 台すべての役割チェックが落ちる**(相手側ポートが `Peer(STP)`)= 1 故障で
  36 点を奪う最大の故障。指紋は明確(Peer(STP) が 1 台を指す)なので残すが、`--faults` の組合せでは他と並べた時の
  点の偏りに注意。

### 10.4 実装記録(BL-222・2026-09-27)
- 記述方式 `style` を `design()` の**最後に**抽選(追加前と同じ seed で他の値が変わらない・指定時も 1 回引いて捨てる)。
  `--guard-style {port,global,any}` で固定可。**global は IOSvL2 のみ**(ioll2 は `portfast edge` 構文が無い)→ iol で抽選が
  global に当たったら any に落とす。要件書は port/global のときだけ「保護機構の設定方法」行を足す(any は「実現手段は問わない」)。
- 採点を**実効状態**へ移した: `show spanning-tree vlan <A> detail` の各ポート ブロック内の
  `Loop guard is enabled( by default)? on the port` / `Root guard is enabled on the port`(PoC G2)。
  エッジの portfast/BPDU ガードは running-config で「IF の行 か `spanning-tree portfast (edge )?(bpduguard )?default`」のどちらか。
  記述方式の指定は running-config のグローバル行で見る(port= 3 種とも無いこと / global= loopguard default 全台・
  portfast/bpduguard default をアクセスに)。配点= 実効 12(core 2・dist 3・acc 1)/ 監査 10(core 1・dist 2・acc 2)。
- 模範解(global)= 全台 `loopguard default` + 下向き 8 本だけ `guard root` + アクセスに `portfast edge default` と
  `portfast edge bpduguard default`。持ち込み機器のポートは念のため上げ直す(下の実測では不要だった)。
- 実機 E2E(`GEN-STP-94002`・同じ設定のまま採点表だけ方式を差し替え):
  port 方式の設定 × any 世界 **100**／global 方式の設定 × global 世界 **100**・× any 世界 **100**・× port 世界 **90**
  (初回 96= 下の不具合。修正後に GEN-STP-94003 で実測 90)／port 方式の設定 × global 世界 **90**。
- ★E2E で見つけた不具合= port 世界の「既定値不使用」判定が `spanning-tree loopguard default` を取りこぼしていた
  (正規表現で `loopguard` の後の空白が抜けていた)→ 修正し、3 種＋旧構文の既定行すべてに当たることを selftest に追加。
- ★実測= **既定の BPDU ガードは bounce 無しでも発動した**(持ち込み機器のポートが up のまま `portfast edge default` と
  `portfast edge bpduguard default` を入れたら `err-disabled bpduguard`)。ただし直前まで IF に `spanning-tree portfast` が
  あった状態からの移行なので、「edge を一度も持たなかったポート」でも同じかは未確認。模範解の bounce は残す。
