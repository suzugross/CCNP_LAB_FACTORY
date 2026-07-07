# 問題 GEN-BGPCX-6100 : BGP 複合トラブルシュート（難易度5）

## 状況
4AS 構成の BGP 網で障害・設計逸脱が発生。**下記の設計書どおり**に復旧してください。

## トラブルチケット（代表症状・1件）
> **RT01 から `172.16.0.0/24` へ到達できない。** 原因は1か所とは限りません。

## 監視環境（切り分けの入口）
- NOC の Zabbix が全ルータを SNMPv3 でポーリングしている
  （ZBX01 は RT04(leaf) 接続・インバンド 10.99.0.2）。
  **どのホストが赤いか＝障害範囲の第一ヒント**（コア赤とサイト赤で層が違う）。
- Zabbix Web UI: `http://<ZBX01のMGMT IP>:8080/`（`Admin` / `zabbix`）
- 監視対象（コア=Loopback0 / 外部AS=サイト代表IP）:

| ホスト | 監視対象IP |
|--------|-----------|
| RT02 | `10.0.91.91` |
| RT07 | `10.0.32.32` |
| RT05 | `10.0.96.96` |
| RT04 | `10.0.6.6` |
| RT03 | `172.16.0.1` |
| RT01 | `198.51.100.1` |
| RT06 | `172.31.0.1` |

- ZBX01（監視サーバ）の設定は正しい。触るのはルータのみ。復旧後の緑化は〜1分。

## 設計書（＝復旧目標。この状態が「正」）
- **AS65001（コア4台）**: OSPF area0 がアンダーレイ（Lo0＋内部リンク）。
  iBGP は **ルートリフレクタ（RR=中心ルータ・他はクライアント）**・**全セッション Loopback0 ピア（update-source）**。
- **AS65100** は 2 台の境界ルータにデュアルホーム。**primary＝be（東側境界）**:
  コア→AS65100 は backup(bw) が inbound で **AS-path prepend ×2** を適用し、be を primary とする。
  AS65100→コア（戻り）も be から入る設計: backup(bw) 側が outbound で **AS-path prepend ×2**。
- **AS65200** は **bw（西側境界）** と **Loopback 間 eBGP（multihop）**。
  相互 Loopback へは static。
  **AS65200 経路にはコア入口(bw)で運用タグ community `65001:600` を付与**し、
  コアの iBGP は **send-community** でタグを伝搬する（コアで確認できること）。
- **AS65300 の 172.31.0.0-3.0/24 ×4 は be（東側境界）で `172.31.0.0/22` に
  summary-only 集約**し、他の全ルータには **/22 のみ**が見えること（/24 の漏れは設計違反。
  集約元は構成要素 /24×4 を BGP テーブルに保持していること）。
  **スタブの AS65300 へは be がデフォルトルートも配布（default-originate）**。
- 境界ルータは iBGP へ **next-hop-self**。
- 全機 **MP-BGP 書式**（`no bgp default ipv4-unicast`＋`address-family ipv4 unicast` で
  **activate 必須**）。

## ルータ台帳（mgmt は割当順）
| ルータ | 役割 | AS | Loopback0 | mgmt(SSH) |
|--------|------|----|-----------|-----------|
| RT02 | hub | AS65001 | `10.0.91.91` | 10.1.10.11 |
| RT07 | bw | AS65001 | `10.0.32.32` | 10.1.10.12 |
| RT05 | be | AS65001 | `10.0.96.96` | 10.1.10.13 |
| RT04 | leaf | AS65001 | `10.0.6.6` | 10.1.10.14 |
| RT03 | cust | AS65100 | `10.0.45.45` | 10.1.10.15 |
| RT01 | mhop | AS65200 | `10.0.66.66` | 10.1.10.16 |
| RT06 | agg | AS65300 | `10.0.41.41` | 10.1.10.17 |

役割: hub=コア中心 / bw・be=境界(西・東) / leaf=コア内部 / cust=AS65100 /
mhop=AS65200(multihop) / agg=AS65300(集約元)

宛先: cust=`172.16.0-2.0/24` / mhop=`198.51.100.0/24` / agg=`172.31.0.0/22`(集約) /
leaf=`192.0.2.0/24`

## 到達目標 / 切り分け
- 全ルータが上記宛先を `show ip route bgp` で学習し相互到達。集約は /22 のみ。
- 故障の種類・場所・件数は非公開。**BGP の症状でも根本原因が下層（OSPF/静的経路/ACL/
  トランスポート）のことがある**。
- 切り分け: `show ip bgp summary` / `show ip bgp` / `show ip bgp neighbors <ip>` /
  `show ip route bgp` / `show ip ospf neighbor` / `show ip route <prefix>`。
- 勘所: **Established なのに PfxRcd 0** は何を意味するか。**BGP テーブルに有るのに
  RIB に無い**経路は何が原因か。Idle/Active の違い。RR の反射規則
  （client→全員 / 非client→client のみ）。**ベストパス選択順（weight > LP >
  AS-path > MED…）** — 設計どおりの経路にならない時は上位の属性から疑う。
  **ポリシー（route-map/フィルタ/weight/コミュニティ）変更後は `clear ip bgp * soft`**。
  セッションが **Idle のまま復帰しない**時は理由（`show ip bgp neighbors` / log の
  %BGP-・%TCP- 行）を見る — 設定を直しても **clear が要る**落ち方がある。
  コミュニティには **well-known（no-export 等）** があり、付いた経路の広告範囲が変わる。

## アクセス・採点
SSH `SUZUKI / CCNP`。
```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPCX-6100 --vault-password-file <(printf 'CCNP\n')
```
