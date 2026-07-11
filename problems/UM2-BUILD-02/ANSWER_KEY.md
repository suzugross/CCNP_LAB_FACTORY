# UM2-BUILD-02 ANSWER KEY（受講者非公開）— ワンアームLB変種

**模範解答（全文）= [poc/um2/poc-um2-onearm-lab.yaml](../../poc/um2/poc-um2-onearm-lab.yaml)
の各ノード configuration**。`um2_ops.py --variant onearm solve` がこれをそのまま console 投入する。

素性: 2026-07-11 に実機検証済みだったワンアームLBプロトタイプ（インライン化前の
golden）をトランスクリプトから完全復元し、EEM NOSHUT-PARENT（IOSv 親IF day0 癖
対策）を同梱したもの。

## 採点実測（実機フルサイクル済・2026-07-11・出題可）

- 未構築（スケルトン直後）: **0/100**（複合チェック化により空取り無し）
- 模範解答投入後（solve→同期2分）: **100/100**（全20チェック一発 PASS）
- **LB腕断デモも同日実証**: LB1 Gi0/0 shut → 20秒後 LB2 が上下サブIFとも Active
  （track 設定ゼロ＝構造保証）・BACKBONE→2.2.2.1 inbound **10/10 無損失**・
  no shut 後は preempt で上下とも LB1 へ自動復帰

## BUILD-01 との差分（それ以外は完全同一）

| 項目 | BUILD-01（インライン） | **BUILD-02（ワンアーム）** |
|---|---|---|
| LB の腕 | 上流=Gi0/0.254（タグ）/ 下流=Gi0/1（タグ無し） | **Gi0/0 1本に .254/.251 を多重** |
| L3SW の LB ポート | trunk allowed 254 | **trunk allowed 251,254** |
| VLAN251 | L3SW に存在しない（LB下流の外側） | **L3SW に L2 のみ存在**（SVI 禁止は同じ） |
| inter-SW trunk | 100,243,244,245,254 | **+251** |
| DMZ-SV 収容 | SRV-SW（unmanaged・据付） | **L3SW2 Gi1/0 access 251（受講者設定）** |
| SRV-SW | あり（11ノード） | **なし（10ノード）** |
| LB 相互トラッキング | **IP SLA reachability 必須**（R7） | **不要**（下記） |
| FW / L3SW SVI・VRF / 据付 | 同一 | 同一 |

## ★R7 考察課題の答え: なぜワンアームはトラッキング不要か

上下（254/251）が**同じ物理IF Gi0/0 上のサブIF**なので、腕障害では両サブIFが
**同時に**通信不能になる。LB1 の腕が死ねば上下両方の HSRP で LB2 が Active になり、
「上流だけ移って下流が残る」**分裂が構造的に起こり得ない**。
- 対してインライン形（BUILD-01）は上流と下流が独立した物理IFなので、片側障害で
  上下が割れる → IP SLA reachability の相互トラッキングが必須（実機実証済）。
- スイッチ側障害（L3SW1 Gi1/1 shut）では CML の仮想リンク非伝播により LB1 の
  Gi0/0 は up のまま残るが、**LB1 は誰からも到達不能な孤島の Active** になるだけで、
  到達可能な側（LB2）が両グループとも Active を取るため通信は成立する
  （HSRP スプリットの無害なケース）。
- **この対比こそ両問を姉妹問にした教材価値の核**。採点後レビューで必ず解説する。

## 構築のポイント（BUILD-01 との差分のみ・共通部は BUILD-01 の ANSWER_KEY 参照）

### L3SW1/L3SW2
- VLAN 251（DMZ-SERVER）を**追加で L2 作成**（SVI は作らない — R1 は 245/251/254 の3つ）
- inter-SW トランク（Gi0/3）と LB 腕（Gi1/1）の allowed に 251 を追加
- **L3SW2 Gi1/0 = DMZ-SV 収容ポート（access 251 + portfast）**。据付サーバだが
  ポート設定は受講者作業（task.md に明記済み）

### LB1/LB2
- Gi0/0 親IF: IP なし・no shutdown（EEM NOSHUT-PARENT を模範解答は同梱）
- Gi0/0.254: 上流。dot1Q 254 / ip nat outside / HSRPv2 grp54 VIP 172.16.254.251
- Gi0/0.251: 下流。dot1Q 251 / ip nat inside / HSRPv2 grp51 VIP 172.16.251.1（サーバGW）
- VIP 終端: `ip nat inside source static 172.16.251.101 172.16.250.1`（両系同一）
- デフォルトルート → 172.16.254.254
- **track / ip sla は設定しない**（構造で保証・上記考察）

### FW1/FW2・DMZ-SV
- BUILD-01 と完全同一（FW は差分ゼロ。DMZ-SV の IP/GW も同一値）

## 運用上の注意

★CML Personal は同時 20 ノード上限。BUILD-01（11ノード）と BUILD-02（10ノード）は
**同時起動不可** — 片方を destroy してから build すること。

## 障害デモ手順（operator 用）

| デモ | 操作 | 期待挙動 |
|---|---|---|
| アップリンク障害 | L3SW1 `int Gi0/0 → shut` | Vl243 のみ 80→L3SW2 Active（BUILD-01 と同一） |
| FW フェールオーバー | L3SW1 `int Gi0/1 → shut` | Primary Failed / Secondary Active・無損失（同一） |
| **LB 腕断（本問の見せ場）** | LB1 `int Gi0/0 → shut` | **上下 HSRP が同時に LB2 へ**（track 無しで揃う=構造保証）。本パックで実測: 20秒後上下 Active・inbound 10/10 無損失・preempt 自動復帰 |
| スイッチ側 LB 腕断 | L3SW1 `int Gi1/1 → shut` | LB1 は孤島 Active 化（無害スプリット）・実通信は LB2 経由で継続 |

## 運用メモ

- 採点: `um2_ops.py --variant onearm grade`。チェック 20 個 = 100 点
  （BUILD-01 の LB トラッキングチェック 3 点は「L3SW2 VLAN251 L2 収容」チェックに差替え）
- alpine は cisco ユーザ放置シェルでも収集可（P_ALP は `[#$]` 受理・2026-07-11 修正）
