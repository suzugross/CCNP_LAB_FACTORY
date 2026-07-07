# 問題 GEN-CHAIN-9300 : ネットワーク全域トラブルシュート（連鎖故障・12台）

## 状況
本社(West)のユーザー LAN から、データセンター(East)のサーバ LAN への通信が
**完全に不通**になっている。前任者が複数の変更を行った直後から障害が続いており、
**故障は1つとは限らない**。また、**ある問題を直すと初めて次の症状が観測できる**
可能性がある。設計書（下記）へ完全復旧させよ。

```
 West OSPF area1        コア AS65001 (OSPF area0 + iBGP RR)         East EIGRP AS65100
 RT10 ─ RT11 ─ RT01 ─┬─ RT03(RR1) ─ RT05 ─┬─ RT02 ─ RT07 ─┬─ RT08
(User LAN)     (ABR)  └─ RT04(RR2) ─ RT06 ─┴─(RT06─RT09)───┴─(RT07─RT09)
                          └RT12(観測点)┘                    (Server LAN)
```

## 設計書（=復旧目標。これ以外の情報は与えられない）
1. **OSPF**: area0=コア（RT01-07,09,12 の該当リンク・Lo0）、area1=West
   （RT10/RT11・User LAN 172.20.0.0/24, 172.20.1.0/24）。RT01 が ABR。
2. **iBGP AS65001**: RR は RT03/RT04 の2台（クラスタ冗長）。client は
   RT01/RT02/RT05/RT06/RT07/RT09。RT12 は **非client** として両RRとピア。
   全ピアリングは Loopback0 間・**AF方式**（`no bgp default ipv4-unicast` ＋
   `address-family ipv4` で activate / send-community）。
3. **West経路**: User LAN(172.20.0.0/24, 172.20.1.0/24)は RT01 が OSPF→BGP 再配送し
   community **65001:100** を付与。RT01 は同 LAN を **area1 の範囲集約で
   not-advertise**（IA として流さない）＝ **User LAN の伝搬は BGP が唯一の経路**。
4. **East経路**: RT07/RT09 の2点で EIGRP⇄BGP 相互再配送（冗長）。
   EIGRP→BGP は Server LAN(172.21.0.0/24, 172.21.1.0/24)と RT08 Lo0 に
   community **65001:200** を付与。BGP→EIGRP はタグ **65001** を付け、
   EIGRP→BGP 側でそのタグを **deny**（再配送ループ防止）。境界の EIGRP側リンク
   (172.30.x/30) は **OSPF area0 へ passive で広告**（BGP next-hop の解決性確保）。
5. **健全性**: User LAN ⇄ Server LAN が両方向到達・転送ループ無し・
   static による暫定対処は禁止（残置は減点）。

## ルータ台帳
| ノード | Lo0 | 役割 |
|--------|-----|------|
| RT01 | 33.33.33.33/32 | 境界W (ABR・OSPF→BGP) |
| RT02 | 9.9.9.9/32 | コア client |
| RT03 | 54.54.54.54/32 | RR1 |
| RT04 | 57.57.57.57/32 | RR2 |
| RT05 | 43.43.43.43/32 | コア client |
| RT06 | 68.68.68.68/32 | コア client |
| RT07 | 52.52.52.52/32 | 境界E1 (EIGRP⇄BGP) |
| RT08 | 77.77.77.77/32 | East内部 (Server LAN) |
| RT09 | 48.48.48.48/32 | 境界E2 (EIGRP⇄BGP) |
| RT10 | 53.53.53.53/32 | West端末 (User LAN) |
| RT11 | 22.22.22.22/32 | Westアグリゲーション |
| RT12 | 76.76.76.76/32 | 観測点 (非client) |

## 制約
- 設計書にある構成要素の**削除・置換えは禁止**（例: RR を経由しない直接ピア追加、
  static での迂回、再配送の一本化）。修復のみで復旧させること。
- BGP 設定は**AF方式**（社内標準）。
- ポリシー変更を既存セッションへ反映させる操作は各自で行うこと。

## アクセス
SSH `SUZUKI / CCNP`（管理IPは出題時に提示）。CML コンソールでも可。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=GEN-CHAIN-9300 --vault-password-file <(printf 'CCNP\n')
```
採点は途中実行可能。修復が進むほど部分点が増える（どのレイヤまで直ったかの
進捗確認に使ってよい）。
