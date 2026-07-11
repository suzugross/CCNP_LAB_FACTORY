# UM2「Untrustワンアーム構成」ブループリント（プロジェクト適合版・BL-042）

一次入力: ユーザ提供の設計下書き `um2/`（UM2_CML_設計書.md / um2_cml_lab.yaml / 構成図
・2026-07-10受領）。書籍デザインパターン UM2 の CML 再現。
本書は下書きレビュー（修正点・穴）と、本プロジェクトの実証済み資産
（BL-038 ASAv PoC / BL-040 CAMPUS-TS-01 / BL-041 HA×ワンアーム PoC）への適合を定める。

---

## A. 下書きレビュー結果

### A-1. 実機実証と衝突する点（Must fix — 直さないと動かない/自動化不能）

| # | 指摘 | 根拠 | 修正 |
|---|------|------|------|
| M1 | **ASAv の day0 は適用されない**。下書きは「day-0投入済み」「FW2はday-0でsecondary指定済み」前提だが、実際は工場出荷状態で起動する | BL-038 実機（イメージが first-boot 消費済み） | YAML の configuration は「正準ソース」として維持し、**bootstrap 方式**（FW1=フル投入→Active化、FW2=failover 9行のみ→自動複製）。BL-041 で 9 行複製まで実証済み |
| M2 | **ASA の認証設定が皆無**（enable/username 無し）。9.22 は初回 enable でパスワード設定ウィザード（**8文字以上強制**）が出るため、自動化が確実に詰まる | BL-038 実機 | `enable password CCNPccnp`＋`username SUZUKI password CCNPccnp privilege 15` を FW1 正準 config に追加。**IOS 側も CCNPccnp に統一**（収集レイヤの単一クレデンシャル制約・CAMPUS-TS-01 と同じ規約） |
| M3 | **`monitor-interface` 欠落**。サブIFは既定 **Not-Monitored** のため、§6 シナリオ3「FW1–L3SW1 間リンク断→ASA のインターフェース監視で FW2 へ」は**現状 config では発動しない**（Active が腕を失ったまま黒穴化） | BL-041 実機（`show failover` に Not-Monitored 表示） | `monitor-interface outside` / `inside` / `dmz` を追加。切替感度は `failover polltime interface` で調整可 |
| M4 | **hostname の複製誤解**。FW2 の day0 に `hostname FW2` とあるが、ペア形成後は **hostname も Active から複製され両ユニット同名**になる | BL-041 実機 | ユニット識別は `show failover｜This host` で行う（自動化・採点・解説すべて）。混乱防止に `prompt hostname priority state` の採用を推奨 |

### A-2. 動作疑義・実装上の穴（Should fix / Phase 0 で検証）

| # | 指摘 | 対処 |
|---|------|------|
| S1 | **IOSvL2 の VRF-Lite + HSRPv2 + track は本リポ未実証**（CAMPUS は HSRPv1+グローバル）。`vrf forwarding` SVI・`standby version 2`・`track N interface ... line-protocol` の組合せが day0 で素直に立つかは要プローブ | Phase 0 P1 |
| S2 | **スプリットブレイン系の実挙動が未検証**。HA リンクを L3SW 経由にした書籍忠実構成では「VLAN245 だけ切れてデータ面は生きている」状態が作れる（L8 トランクからの 245 漏れ等）。monitor-interface があれば ASA はデータ IF 経由の mate 生存確認でスプリットブレインを回避するはず → 実機確認。**確認結果そのものが TS 問の上玉ネタ** | Phase 0 P2 |
| S3 | **alpine の day0（シェルスクリプト）は本リポ未実証**。下書き自身が「効かない場合は手動」とヘッジしており、自動化パイプラインでは許容不可 | 推奨=**ubuntu へ置換**（cloud-init/SSH/curl 全て実績・RAM +3.5GB でも余裕）。書籍再現の最小性を優先するなら Phase 0 P3 で alpine day0 を検証してから決定 |
| S4 | **MGMT ネットワークが無い**（コンソール前提）。採点自動化（Linux=SSH 収集・リース台帳・複数ラボ共存）はプロジェクト規約上 MGMT 前提 | 出題版は **MGMT オーバーレイ追加**（全ノード mgmt NIC + MGMTSW + EXTC + mgmt_alloc リース）。データプレーンの書籍忠実性には影響しない |
| S5 | `spanning-tree portfast edge` — IOSvL2(15.2系) は `edge` キーワード**非対応の可能性大**（day0 で無言スキップ） | `spanning-tree portfast` に修正（CAMPUS 実績構文） |
| S6 | image_definition 未指定（node_definition のみ） | 明示する（`iosv-159-3-m9` / `iosvl2-2020` / `asav-9-22-1-1`）。本リポの罠「存在しない image ID は無言差し戻し」対策の規約 |
| S7 | preempt に遅延が無く、復旧時に即切り戻る（フラップ増幅リスク） | 任意: `standby N preempt delay minimum 60`。出題では「即切り戻り」も観察対象なので golden は現状維持でも可 |
| S8 | interfaces の `type: loopback` エントリ・ノード内ローカルな IF id（i0,i1…）は CML エクスポート風で恐らく import 可だが、本リポ生成器の規約（グローバル一意 id）と異なる | gen_um2_lab.py で再生成する際に本リポ規約へ正規化（下書き YAML は原本として保存） |

### A-3. 下書きの良い点（そのまま採用）

- **VLAN 245/254 に SVI を作らない**理由の明記（FW 迂回）— 書籍の核心。そのまま **TS 故障ネタ**（SVI を作ってしまう故障）としても最高の教材
- ACL を**実IP**（172.16.254.101）で記述 — ASA 8.3+ の罠を正しく回避済み
- PAT を host オブジェクト（2.2.2.10）への `dynamic` で定義 — 正しい PAT 構文
- `vtp mode transparent` が YAML に入っている（BL-040 の必須知見と一致）
- 書籍 IP → ASA Active/Standby IP の写像方針（§1 注記）が明快
- track による Untrust VRF のみのフェールオーバー（Trust は L3SW1 残留）— 書籍
  図2.4.11 忠実。非対称だが経路は成立（机上トレース済み）

---

## B. 確定設計（golden・下書き＋修正の統合）

トポロジ/VLAN/IP/ルーティング/NAT は下書き §2〜§5 を踏襲（変更なし）。差分のみ:

1. **認証**: IOS/ASA とも `SUZUKI / CCNPccnp`（enable 同）・Linux `suzuki / CCNP`
2. **FW1 正準 config 追加行**:
   ```
   enable password CCNPccnp
   username SUZUKI password CCNPccnp privilege 15
   monitor-interface outside
   monitor-interface inside
   monitor-interface dmz
   prompt hostname priority state
   ```
3. **FW2 は failover 9行のみ**（unit secondary / FOLINK 定義×2 / interface ip /
   key / failover ＋ Gi0/1 no shut）。★failover key（8字）を両ユニットに追加
   — 下書きは key 無し（平文 failover）。規約として `failover key CCNPccnp`
4. **L3SW**: `spanning-tree portfast`（edge 除去）。ほか下書きどおり
5. **エンドポイント**: USER-PC / DMZ-SV = **ubuntu**（cloud-init: 静的IP+GW、
   DMZ-SV は nginx + /big.bin 不要・index のみ）。alpine 継続希望時は Phase 0 P3 通過が条件
6. **MGMT オーバーレイ**: 全7 VM + MGMTSW(unmanaged) + EXTC。
   iosv/iosvl2 は空きIF（iosv=Gi0/1 or 0/2、iosvl2=Gi3/3 routed port）、
   ASA=Management0/0(management-only)、ubuntu=ens2。mgmt_alloc リース 7個
7. ノード数: 7 VM + BB-SW + MGMTSW + EXTC = **10 CMLオブジェクト**・RAM ≒ 10GB
   → 20 ノード上限に大幅余裕（CAMPUS より軽い）

## C. Phase 0 プローブ（golden 実装前・半日想定）

**→ 全プローブ✅（2026-07-11 実機・poc/um2/README.md に全記録）**

- P1 ✅ VRF-Lite+HSRPv2+track 成立・track で Untrust のみ移動・非対称状態で無損失。
  ★新知見: アクセスポートのみメンバーの SVI はブート後 down 固着＋HSRP が
  `Init (interface down)` 残留 → **安定後の2回目バウンス**で解消（構築問では受講者の
  対話投入なので影響小・ANSWER_KEY に処方箋）
- P2a ✅ FOLINK 経路断でも**スプリットブレインは起きない**（monitor-interface の
  データIFハローで mate 生存確認・Standby Ready 維持）→ ha_vlan_pruned 故障は
  「通信正常・冗長喪失」の潜在障害型として出題
- P2b ✅ 腕断で monitor-interface 発動 → Failed/Active 切替・無損失。M3 修正の妥当性を両面実証
- P3 ✅ **alpine の day0 スクリプトは実行される** → alpine 採用確定（ubuntu 置換不要）
- golden 試験 G1〜G3（PAT/静的NAT/ゾーン分離）✅ → **golden=模範解答 完成済み**
- `prompt hostname priority state` により プロンプトでユニット/状態判別可（M4 の実用解）

## C-2. DMZ-LB 拡張（2026-07-11 ユーザ承認・書籍の LB#1/#2 を復元）

「LB省略」をやめ、IOSv×2 を LB 代わりの L3 デバイスとして DMZ ゾーンに追加。
ルーティング/NAT/VIP 終端/サーバ GW を再現する（負荷分散そのものはしない）。

### 追加/変更点

| 項目 | 内容 |
|---|---|
| LB1/LB2 (iosv) | ワンアーム trunk（dot1q サブIF 254/251）。LB1→L3SW1 Gi1/1、LB2→L3SW2 Gi1/1 |
| VLAN 254 (FW-LB) | FW dmz .254/.252（既存）＋ **LB1 .253 / LB2 .249 / HSRP VIP .251**（grp54・FWのルート先） |
| **VLAN 251 (サーバVLAN)** 新設 | 172.16.251.0/24。LB1 .2 / LB2 .3 / **HSRP VIP .1**（grp51・サーバのGW）。DMZ-SV .101 を 254→251 へ移設。L3SW は L2 のみ（SVI 無し原則踏襲）・inter-SW trunk と LB trunk の allowed に追加 |
| **VIP subnet 172.16.250.0/24** | **実VLANなし**。VIP 172.16.250.1 は LB の static NAT が終端（実LBのVIP=論理アドレスの再現）。FW は 250/24・251/24 → 172.16.254.251 へルーティング |
| LB の NAT | `ip nat inside source static 172.16.251.101 172.16.250.1`（outside=.254サブIF/inside=.251サブIF）。両LBに同一投入（ステートレス冗長） |
| FW 変更 | 静的NAT先を **2.2.2.1→172.16.250.1（LB VIP・書籍どおり）** に変更。OUTSIDE-IN ACL の実IPも 172.16.250.1 へ。dmz 向けルート2本追加 |
| NATチェーン | `2.2.2.1 →(FW)→ 172.16.250.1 →(LB)→ 172.16.251.101` の二段 |

- LB 冗長はステートレス（実LBのセッション同期は無い）→ LB 切替で既存 TCP は切れ、
  新規は即通る。「安価な LB 冗長の現実」として教材化
- リソース: +iosv×2 = 計10 VM。20 ノード上限内
- 受講者スコープ増: LB×2（trunk サブIF/HSRP×2/static NAT/デフォルトルート）

**→ 拡張 golden 実機検証 全✅（2026-07-11・poc/um2/README.md）**: 二段NAT貫通(9/10)・
user→VIP 200・**LB切替 10/10 無損失**。★実IP直宛は LB の SNAT により不成立=仕様
（VIP経由が正・教材ポイント）。★IOSv も IP無し親IFは day0 no shutdown 無効
→ EEM no-shut を day0 同梱で解決

### C-2b. 書籍準拠のインライン形へ再変更（2026-07-11 ユーザ指摘）

ワンアームLB（腕1本に254/251多重）→ **書籍どおりのインライン形**へ:
上流= Gi0/0 dot1q サブIF(タグ254) / 下流= Gi0/1 タグ無し（SRV-SW 配下に
サーバセグメント 172.16.251.0/24）。L3SW から VLAN251 が完全に消える。
- ★インライン化で「上下 HSRP が片側障害で割れる」問題が発生 →
  **相互トラッキングは IP SLA reachability**（上流=FW dmz宛/下流=サーバ宛）で解決。
  `line-protocol` トラッキングは **CML の仮想リンク非伝播**（IOL/BFD 知見の一般形）
  により対向側障害を検知できず不成立（実機実証: 下流が LB1 に残り黒穴）
- 再検証済: build→solve→**100/100**・上流腕断で上下揃って LB2 切替・inbound 10/10 無損失

## D. 出題化ロードマップ

1. **UM2-BUILD-01（構築問・難5想定）**: golden を仕様書（設計書§2〜5相当の
   パラメータ表）として渡し、L3SW×2 + FW HA を組ませる。採点= 下書き§8 の
   試験項目を grading.yml 化（下記）
2. **UM2-TS 系（fault 注入・campus 方式）**: gen_um2_lab.py に faults トグル、
   um2_ops.py で inject/reset。**故障候補（実証根拠つき）**:
   - `svi_on_dmz_vlan`: VLAN254 に SVI 作成 → **FW 迂回**（書籍の注意点そのもの・
     ゾーン分離試験だけが落ちる）
   - `monitor_interface_missing`: 腕断でフェールオーバー不発（BL-041 知見の逆用）
   - `ha_vlan_pruned`: L8 トランクから VLAN245 漏れ → スプリットブレイン or
     データIF hello 回避（P2 の結果次第で症状確定）
   - `track_missing`: アップリンク断で Untrust Active が移らず黒穴（図2.4.11 の逆）
   - `acl_mapped_ip`: OUTSIDE-IN を 2.2.2.1（マップIP）で書く → inbound 全落ち
     （8.3 罠・BL-038 実証済み）
   - `pat_object_range`: PAT を dynamic NAT 化 → 2人目から出られない
3. **grading.yml 骨子（100点）**: HSRP 設計一致（VRF別）/ FW1 Active+Standby
   Ready / track 動作 / outbound PAT 実測（xlate に 2.2.2.10）/ inbound static
   NAT 実測（BACKBONE→2.2.2.1 http 200）/ ゾーン分離（user→DMZ が FW 経由 =
   `show conn` に実在）/ 障害試験は operator 手順として ANSWER_KEY へ
4. 収集: IOS=collect_console / ASA=pexpect 収集 / ubuntu=SSH（campus_ops 方式流用）

## E. 進め方（提案）

1. Phase 0 プローブ（P1/P2 (+P3)）→ 結果を本書 C 節へ追記
2. gen_um2_lab.py + um2_ops.py（campus 系のコピー起点・工数小）
3. golden 全 green → 障害3シナリオ実機 → BUILD 問 or TS 問の順で出題化

原本（無修正の下書き）: `um2/` に保存。修正は生成器側で吸収し原本は変更しない。
