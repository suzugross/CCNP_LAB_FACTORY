# 模範解答 (ENARSI-MPLS-L3VPN-06)

## 設計の考え方

- **共有＝VRF を混ぜることではなく、RT を「もう1値」足すこと。**
  - SVCS VRF: export **65000:300** / import **65000:301** — 「自分の LAN を配り、
    顧客の利用セグメントだけを受け取る」。
  - 顧客 VRF: 既存 RT はそのまま + import に **300** を追加（共有 LAN を受け取る）+
    利用セグメントに **301** を追加付与（共有側に渡す）。
  - 顧客同士は相手の RT を一切 import しない → **分離は構造的に維持**される。
- **なぜ「利用セグメントにのみ」301 を付けるのか**: 両顧客の 172.16 帯は重複しており、
  共有 VRF に持ち込むと同一 prefix が衝突して**片方が無言で負ける**
  （PoC 実測: `imported path from 65000:200:172.16.1.0/24` の 1 本だけが残り、
  CUST_A 版は代替パスとしても残らない = 監視が A のつもりで B に届く事故）。
  選択的に付与する SP 標準の道具が **export map**。

## 投入 config（PE のみ・これで 100 点）

### RT08 (SVC-PE)

```
vrf definition SVCS
 rd 65000:300
 address-family ipv4
  route-target export 65000:300
  route-target import 65000:301
 exit-address-family
!
interface Ethernet0/1
 vrf forwarding SVCS
 ip address 192.168.30.2 255.255.255.252
!
router bgp 65000
 address-family ipv4 vrf SVCS
  neighbor 192.168.30.1 remote-as 65300
  neighbor 192.168.30.1 activate
 exit-address-family
```
（vrf forwarding 投入で IP が消えるため入れ直す。この IF は元々 global 収容）

### RT01 (PE1) / RT03 (PE2) — 共通

```
ip prefix-list PL-SVC-ACCESS seq 5 permit 10.65.0.0/16 le 24
ip prefix-list PL-SVC-ACCESS seq 10 permit 10.66.0.0/16 le 24
!
route-map RM-SVC-EXP permit 10
 match ip address prefix-list PL-SVC-ACCESS
 set extcommunity rt 65000:301 additive
!
! 受信制御の拡張 (10.99 は暗黙 deny のまま維持)
ip prefix-list PL-CUST-LAN seq 10 permit 10.65.0.0/16 le 24
ip prefix-list PL-CUST-LAN seq 15 permit 10.66.0.0/16 le 24
!
vrf definition CUST_A
 address-family ipv4
  route-target import 65000:300
  export map RM-SVC-EXP
 exit-address-family
!
vrf definition CUST_B
 address-family ipv4
  route-target import 65000:300
  export map RM-SVC-EXP
 exit-address-family
```

## ★隠しひねり: `additive` — 仕様どおりでも自顧客のサイト間が壊れる

`set extcommunity rt 65000:301`（additive なし）だと**既定の export RT が置換されて
消える**。マッチした利用セグメントは RT 301 だけを持って出て行き:

- 共有 VRF には届く（import 301）→ 共有向けチェックは通ってしまう
- **自顧客の他 PE からは消える**（RT 100/200 が無い）→ 10.65.1 ↔ 10.65.2 が不通
- 172.16 LAN は map 非マッチで無傷 → **部分故障で気づきにくい**

指紋（debug 不要・決定的）:
```
show bgp vpnv4 unicast all 10.65.1.0 | include Extended
  Extended Community: RT:65000:301            ← 既定 RT:65000:100 が消えている
正解形:
  Extended Community: RT:65000:100 RT:65000:301
```
是正 = `set extcommunity rt 65000:301 additive`（**既存 RT に追加**の意）。

## 検証（最終状態の指紋）

- SVCS VRF: 10.65.1/2.0 + 10.66.1/2.0 の 4 本のみ（172.16 なし・10.99 なし）。
- 顧客 VRF: 172.30.0.0/24 が増える。相手顧客の 10.6x は**現れない**。
- 4 CE から `ping 172.30.0.1 source <Lo2>` 成功 / SVC-CE から各利用セグメントへ成功。
- export map 非マッチの経路（172.16）は**既定 RT のまま正常に export される**
  （export map はフィルタではなく RT 変更のみ・PoC 実測）。

## よくある誤答

- **additive 忘れ**: 上記のとおり。共有向けは通るのに自顧客サイト間だけ壊れる。
- **SVCS に RT 100/200 を直 import**（素朴解）: 重複 172.16 が衝突し片顧客が
  無言で負ける + チケット要件 3 違反（採点は SVCS の 172.16 不在で検出）。
- **RM-CE-IN を permit any 化**（手抜き拡張）: 10.99 が SP 網に流入し
  環境保存チェック（10.99 不在複合）で自壊。開けるのは 10.65/10.66 だけ。
- **利用セグメントを顧客 VRF の route-target export 65000:301 で一律付与**:
  172.16 にも 301 が付き SVCS に重複 prefix が流入 = 要件 3 違反。
  「選択的に付ける」には export map しかない。

## 考察の答え

1. 共有 VRF に重複 172.16 を import すると、BGP ベストパス選択で片方だけが
   テーブルに残る（どちらが勝つかは非決定的）。負けた顧客への監視・応答が
   もう片方の顧客に向かう = サイレントな誤配。
2. A → 共有基盤 → B の踏み台は**経路的に不成立**。A の VRF/CE には B の経路が
   存在せず（import していない）、10.66 宛のパケットはそもそも SP 網に入る
   経路が無い。ただし共有基盤ホスト自身は両顧客に到達できるため、
   実務では共有セグメント側の FW/ACL で顧客間フォワーディングを防ぐのが定石。
