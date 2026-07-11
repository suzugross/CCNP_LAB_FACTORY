# UM2 golden プローブ (BL-042 Phase 0) — 結果 (2026-07-11)

UM2「Untrustワンアーム構成」の golden（修正統合版）を実機検証した。
**全プローブ✅ → UM2-BUILD-01（構築問）実装へ進める。golden＝模範解答が完成済み**。

## 検証環境（poc-um2-lab.yaml・8ノード・console専用）

原本 um2/um2_cml_lab.yaml に UM2.design.md の Must fix 4点＋Should fix を統合したもの。
BACKBONE(iosv)+BB-SW+L3SW×2(iosvl2)+FW×2(asav)+USER-PC/DMZ-SV(alpine)。

## プローブ結果（全✅）

| # | 検証 | 結果 |
|---|------|------|
| P1 | IOSvL2 の VRF-Lite + HSRPv2 + track | ✅ day0 一発で成立（下記固着癖のみ）。track 発火で Vl243 のみ 110→80、Untrust Active が L3SW2 へ移動・Trust 系は L3SW1 残留（書籍図2.4.11/12 再現）。**非対称状態で outbound 無損失(5/5)** |
| P2a | FOLINK 経路断（トランクから VLAN245 除去）のスプリットブレイン | ✅ **起きない**。FW2 は mate の全データIFを `Normal (Monitored)` で監視し続け Standby Ready を維持（monitor-interface のデータIFハローが効く） |
| P2b | 腕リンク断（L3SW1 Gi0/1 shut）のフェイルオーバー | ✅ monitor-interface 発動 → `Primary - Failed / Secondary - Active`。**切替後 outbound 8/8 無損失**。復旧→`failover active` で切り戻し成功 |
| P3 | alpine の day0（シェルスクリプト） | ✅ **実行される**（IP/route/httpd 自動設定・マーカー生成）。ubuntu 置換不要、alpine 採用確定（256MB・軽量） |
| G1 | outbound PAT（USER-PC→198.51.100.1） | ✅ 貫通（初発 ARP 損のみ） |
| G2 | inbound 静的NAT（BACKBONE→2.2.2.1:80 telnet） | ✅ TCP 確立し httpd 応答（= static NAT + 実IP ACL 動作） |
| G3 | ゾーン分離（USER-PC→DMZ 直宛） | ✅ ping/wget 到達・FW xlate に `dmz:172.16.254.101 to outside:2.2.2.1` |

## ★実機知見

1. **IOSvL2 SVI 固着の一般化**: 「アクセスポートのみをメンバーに持つ SVI」（Vl10/Vl100）
   はブート後 down 固着（トランクをメンバーに持つ Vl243/244 は自然に up）。
   さらに bounce で SVI が up しても **HSRP が `Init (interface down)` を掴んだまま**
   になる → **安定後にもう一度 shut/no shut（2回バウンス）で解消**。
   既存知見（Vlan999 mgmt SVI bounce）の一般形。構築問では受講者が対話投入する
   ため発生しにくいが、ANSWER_KEY に「SVI up なのに HSRP Init」の処方箋として記載する
2. **ha_vlan_pruned は「潜在障害」型の上玉 TS ネタ**: FOLINK 経路が切れても
   通信は完全正常・スプリットブレインも起きない。症状は「冗長性の喪失」だけ
   （`show failover` の精読が解答筋）— 「壊れているのに気づかない」系
3. **monitor-interface の妥当性を両面実証**: 有り→腕断で正しく切替（P2b）/
   スプリットブレイン回避（P2a）。無し（原本下書きのまま）なら腕断で黒穴
4. `prompt hostname priority state` 採用で **プロンプトだけでユニット/状態判別可**
   （`FW1/pri/act#` / `FW1/sec/stby#`）。hostname 複製問題（M4）の実用解
5. FW1 フル bootstrap（53行）＋FW2 9行複製の方式は UM2 構成でもそのまま成立
6. FOLINK は「ローカルリンク up・経路断」のとき ASA 表示上 `FOLINK (up)` のまま
   → 切り分けでは `show failover history` / mate 状態を見る必要（出題の切り分けポイント）

## DMZ-LB 拡張検証（2026-07-11・ユーザ承認による書籍 LB#1/#2 復元・全✅）

LB1/LB2(iosv・ワンアーム trunk 254/251)を追加し、VIP 172.16.250.1 を LB の
static NAT で終端。サーバVLAN 251 新設（GW=LB HSRP VIP 172.16.251.1）。
FW の静的NAT先は書籍どおり LB VIP に変更（2.2.2.1→172.16.250.1→172.16.251.101 の二段）。

| 検証 | 結果 |
|------|------|
| inbound 二段NAT（BACKBONE→2.2.2.1） | ✅ 9/10（初発ARPのみ）。FW→LB→サーバ貫通 |
| outbound PAT / user→VIP HTTP | ✅ 5/5 / HTTP 200 |
| LB 切替（LB1 腕断→LB2 HSRP 引き継ぎ） | ✅ **inbound 10/10 無損失**・VIP HTTP 継続（ステートレスNAT+HSRP） |
| user→サーバ実IP直宛 | ❌ **仕様として不成立**（正しい挙動）: サーバ発の戻りが LB static NAT で必ず VIP に SNAT されるため実IP宛セッションは戻り不一致。**LB配下サーバは VIP 経由が正** — 実運用の定番ハマりの忠実な再現（教材ポイント・ゾーン分離試験は VIP 宛で定義する） |

### ★追加の実機知見

- **IOSv でも「IP を持たない親IF」は day0 の `no shutdown` が無効**（IOL の既知癖と
  同族）。サブIF 構成の LB 親 Gi0/0 が admin down のまま → **EEM applet
  (countdown 45s → no shut) を day0 に同梱**して解決（yaml 反映済み）。
  構築問では受講者が no shut するので影響なし
- LB の HSRP は親IF up 後に即 Active/Standby 形成。切替は HSRP 既定タイマで数秒

### ★C-2b: 書籍準拠インライン形へ再変更（2026-07-11・最終形）

ユーザ指摘により LB をワンアーム→**インライン**へ: 上流=タグ254サブIF /
下流=Gi0/1 タグ無し（SRV-SW 配下 172.16.251.0/24）。L3SW から VLAN251 消滅。
- ★**HSRP 相互トラッキングは IP SLA reachability 必須**: `track interface
  line-protocol` は CML 仮想リンクの**対向断非伝播**（IOL/BFD 知見の一般形）で
  スイッチ側障害を検知できず、上下 HSRP が割れて黒穴（実機実証）。
  SLA 方式（上流=FW dmz 宛/下流=サーバ宛 icmp-echo・freq 5s）で
  上流腕断→約20秒で上下揃って LB2・inbound 10/10 無損失を実測
- 再検証: スケルトン build→solve→**100/100**

## 構築問（UM2-BUILD-01）への引き継ぎ

- golden = 本 PoC の yaml がそのまま模範解答（poc-um2-lab.yaml の configuration 群・DMZ-LB 拡張込み 10 VM）
- 受講者スコープに LB×2 を追加: trunk サブIF/HSRP×2/static NAT(VIP終端)/デフォルトルート
- 受講者スコープ案: L3SW×2 の VRF/VLAN/SVI/HSRP/track ＋ FW1 の全設定 ＋ FW2 の
  failover bootstrap（9行を自力で書く）。BACKBONE/alpine は据え付け（変更禁止）
- 採点softは campus 方式流用: IOS=console / ASA=pexpect / alpine=console(root シェル)
  ＋ 機能試験 G1〜G3 ＋ HSRP/failover 状態 ＋「VLAN245/254 に SVI が無いこと」
- 障害試験（§8 の 5〜8）は operator デモ手順として ANSWER_KEY へ

## 再現手順

1. `python3 poc/um2/um2_tools.py up` → `wait`（8ノード・約4分）
2. `um2_tools.py bootstrap FW1` → `bootstrap FW2`（Standby Ready まで約1分）
3. ★L3SW×2 で Vl10/Vl100 を bounce（SVI up 後、HSRP が Init のままなら再 bounce）
4. 検証: `um2_tools.py cmd <NODE> "..."`（G1〜G3・P1/P2 の手順は本文参照）
5. 片付け: `um2_tools.py down`
