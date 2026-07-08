# 問題 GEN-CHAIN-9700 : ネットワーク全域トラブルシュート（連鎖故障・12台）

## 状況
本社(West)のユーザー LAN から、データセンター(East)のサーバ LAN への通信が
**完全に不通**になっている。前任者が複数の変更を行った直後から障害が続いており、
**故障は1つとは限らない**。また、**ある問題を直すと初めて次の症状が観測できる**
可能性がある。設計書（下記）へ完全復旧させよ。

```
 West EIGRP 65100      コア AS65001 (OSPF area0 + iBGP)       East OSPF proc2
 RT10 ─ RT11 ─ RT01 ─┬─ RT03      ─ RT05 ─┬─ RT02 ─ RT07 ─┬─ RT08
(User LAN)     (境W)  └─ RT04      ─ RT06 ─┴─(RT06─RT09)───┴─(RT07─RT09)
                          └RT12(観測点)┘                    (Server LAN)
```

## 設計書（=復旧目標。これ以外の情報は与えられない）
1. **IGP**: コア=OSPF area0（RT01-07,09,12）。West=**EIGRP AS65100**
   （RT10/RT11・User LAN 172.20.0.0/24, 172.20.1.0/24。RT01 が単一境界）。
   East=**OSPF プロセス2**（RT07/RT08/RT09。RT07/09 が二重境界）。
2. **iBGP AS65001**: **フルメッシュ**（RRなし・BGP話者9台が全対全でピア。RT03/RT04/RT12 も対等な一般ノード）。
   全ピアリングは Loopback0 間・**AF方式**（`no bgp default ipv4-unicast` ＋
   `address-family ipv4` で activate / send-community）。
3. **West経路**: User LAN と RT10/RT11 の Lo0 は RT01 が EIGRP→BGP 再配送し
   community **65001:100** を付与（**West の伝搬は BGP が唯一の経路**）。
   BGP→EIGRP はタグ **65001**＋EIGRP→BGP 側で deny（還流防止）。
   再配送経路の next-hop は **自Lo0 に set**（解決性の自己完結）。
4. **East経路**: RT07/RT09 の2点で OSPF2⇄BGP 相互再配送（冗長）。
   OSPF2→BGP は Server LAN と RT08 Lo0 に community **65001:200** を付与し
   **next-hop を自Lo0 に set**。BGP→OSPF2 は **subnets**＋タグ **65001**、
   OSPF2→BGP 側でタグを **deny**（再配送ループ防止）。
5. **健全性**: User LAN ⇄ Server LAN が両方向到達・転送ループ無し・
   static による暫定対処は禁止（残置は減点）。

## ルータ台帳
| ノード | Lo0 | 役割 |
|--------|-----|------|
| RT01 | 15.15.15.15/32 | 境界W (EIGRP⇄BGP) |
| RT02 | 13.13.13.13/32 | コア |
| RT03 | 4.4.4.4/32 | コア |
| RT04 | 69.69.69.69/32 | コア |
| RT05 | 93.93.93.93/32 | コア |
| RT06 | 51.51.51.51/32 | コア |
| RT07 | 75.75.75.75/32 | 境界E1 (OSPF2⇄BGP) |
| RT08 | 87.87.87.87/32 | East内部 (Server LAN) |
| RT09 | 63.63.63.63/32 | 境界E2 (OSPF2⇄BGP) |
| RT10 | 97.97.97.97/32 | West端末 (User LAN) |
| RT11 | 70.70.70.70/32 | Westアグリゲーション |
| RT12 | 20.20.20.20/32 | コア (観測点) |

## 制約
- 設計書にある構成要素の**削除・置換えは禁止**（例: RR を経由しない直接ピア追加、
  static での迂回、再配送の一本化）。修復のみで復旧させること。
- BGP 設定は**AF方式**（社内標準）。
- ポリシー変更を既存セッションへ反映させる操作は各自で行うこと。

## アクセス
SSH `SUZUKI / CCNP`（管理IPは出題時に提示）。CML コンソールでも可。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=GEN-CHAIN-9700 --vault-password-file <(printf 'CCNP\n')
```
採点は途中実行可能。修復が進むほど部分点が増える（どのレイヤまで直ったかの
進捗確認に使ってよい）。
