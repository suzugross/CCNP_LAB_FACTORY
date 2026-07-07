# ENARSI-EIGRP-SIA-01 解説（IOL 実機で broken→fix→100 確認済み）

## 根本原因
RT01 の RT03 向けインタフェース（Ethernet0/1）に、次の**片方向 ACL が in で適用**されている：
```
ip access-list extended EIGRP-MCAST-ONLY
 permit eigrp any host 224.0.0.10   ! EIGRP マルチキャスト(Hello)は許可
 deny   eigrp any any               ! EIGRP ユニキャストを遮断 ★
 permit ip any any
interface Ethernet0/1
 ip access-group EIGRP-MCAST-ONLY in
```
EIGRP は **Hello=マルチキャスト(224.0.0.10)** だが、**Update / Query / Reply / ACK は
信頼配送のユニキャスト**。このフィルタは Hello だけ通すため、

- 隣接は成立する（`show ip eigrp neighbors` に RT03 が“見える”）＝**一見正常**。
- しかし RT01 は RT03 からのユニキャスト（更新・ACK・リプライ）を受け取れない → 信頼配送が
  完了せず、**Q Cnt が 1 のまま／RTO 5000**、やがて **retry limit exceeded** で隣接リセット →
  再確立 → また失敗、を周期的に繰り返す（`show logging` に up/down 連発）。
- 結果、**RT03 の先（RT04 の T=10.100.100.100 等）が RT01 で学習できない**。RT02 側は健全。

## 診断手順
1. `show ip eigrp neighbors`：RT02 隣接は Q=0/RTO=100 で安定、**RT03 隣接だけ Q=1・RTO=5000・
   uptime が若返る**（リセットの証拠）。
2. `show logging | include DUAL|Ethernet0/1`：`Neighbor 10.13.13.2 ... retry limit exceeded` の反復。
3. `show ip route eigrp`：RT03 の先（10.3.3.3 / 10.34.34.0 / 10.4.4.4 / T）が不在、RT02 側だけ有る。
4. 隣接は上がる＝L1/L2/Hello は OK → **ユニキャスト EIGRP だけ落ちている**と推定 →
   インタフェースの ACL を確認 → 犯人特定。

## 修復
Ethernet0/1 の入力フィルタを外す（または EIGRP ユニキャストを許可する）：
```
interface Ethernet0/1
 no ip access-group EIGRP-MCAST-ONLY in
```
数十秒で RT01-RT03 隣接が安定（Q=0）し、RT01 が T を含む RT03 配下を学習・全到達。

## SIA との関係（学びの核心）
- **SIA（Stuck-in-Active）** は、経路が Active になり Query を送ったのに **Reply が返らない**まま
  Active タイマ（既定3分）を超え、`%DUAL-3-SIA` でその隣接を落とす現象。原因は「リプライが
  返せない／返らない」＝**片方向リンク・輻輳・過大なクエリ範囲・本問のようなユニキャスト遮断**。
- 本問はその一族で、**ユニキャスト不達により Query/Reply/ACK が成立しない**状態を決定的に
  再現している（実機では retry-limit リセットが3分の Active タイマより先に発火するため、
  純粋な `DUAL-3-SIA` ログではなく `retry limit exceeded` として現れる）。
- **設計的な SIA 対策**（本問の直接原因とは別に、実務で重要）:
  - **`eigrp stub`**（スポークをスタブ化しクエリを送らせない＝クエリ範囲を絞る）
  - **集約（summary-address）**：集約点がクエリに即「その先は無い」と答え、**クエリの伝播を境界で止める**。
  - 片方向・不安定リンクや、EIGRP を通すべき区間の**フィルタ/ファイアウォール設定の是正**。

## 別解・補足
- ACL を残したまま「EIGRP ユニキャストも許可」する行を足す解でも可（`permit eigrp any any` を
  deny の前に）。採点は結果（T 到達・全疎通）で判定。
- スタティックルートでの“到達だけ”回避は不可（EIGRP で解決すること）。
