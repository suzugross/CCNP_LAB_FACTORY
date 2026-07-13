# 模範解答 (ENARSI-MPLS-L3VPN-05)

## 設計の考え方

- **CUST_A（フラット契約）**: 「全 PE が同じ経路集合を相互に import/export する」= RT 1 値の
  対称設計で要件充足。**触らない**（環境保存）。
- **CUST_B（本社経由契約）**: 「誰の経路を誰が受け取るか」を非対称にする必要がある。
  - 拠点 PE: 自拠点の経路を **export 65000:220（拠点発）**、受け取ってよいのは
    本社発のみ = **import 65000:210**。拠点同士は互いの RT を import しないので
    **直接経路が存在できない**。
  - 本社 PE（PE1）は「拠点の経路を集めて本社へ降ろす」（下り）と「本社 CE が折り返した
    経路を拠点へ配る」（上り）の 2 役。**1 つの VRF では同一 eBGP セッションで
    受けた経路をそのセッションへ送り返せない**（BGP は学習元ピアへ再広告しない）ため、
    **下り VRF（CUST_B: import 220 のみ）/ 上り VRF（CUST_B_UP: export 210 のみ）**
    に分離し、本社 CE の 2 セッション（VLAN10/20）で折り返す。

経路の流れ:
```
拠点 PE --(export 220)--> PE1:CUST_B --(eBGP VLAN10 下り)--> 本社CE(RT08)
  --(eBGP VLAN20 上り)--> PE1:CUST_B_UP --(export 210)--> 拠点 PE
```

## 投入 config（PE のみ・これで 100 点）

### RT01 (PE1)

```
vrf definition CUST_B_UP
 rd 65000:210
 address-family ipv4
  route-target export 65000:210
 exit-address-family
!
vrf definition CUST_B
 address-family ipv4
  no route-target export 65000:200
  no route-target import 65000:200
  route-target import 65000:220
 exit-address-family
!
interface Ethernet0/2
 no ip address
!
interface Ethernet0/2.10
 encapsulation dot1Q 10
 vrf forwarding CUST_B
 ip address 192.168.111.2 255.255.255.252
!
interface Ethernet0/2.20
 encapsulation dot1Q 20
 vrf forwarding CUST_B_UP
 ip address 192.168.112.2 255.255.255.252
!
router bgp 65000
 address-family ipv4 vrf CUST_B
  no neighbor 192.168.11.1
  neighbor 192.168.111.1 remote-as 65201
  neighbor 192.168.111.1 activate
 exit-address-family
 address-family ipv4 vrf CUST_B_UP
  neighbor 192.168.112.1 remote-as 65201
  neighbor 192.168.112.1 activate
  neighbor 192.168.112.1 allowas-in 1
 exit-address-family
```

### RT02 (PE2) / RT03 (PE3) — 共通（拠点 PE）

```
vrf definition CUST_B
 address-family ipv4
  no route-target export 65000:200
  no route-target import 65000:200
  route-target export 65000:220
  route-target import 65000:210
 exit-address-family
```

## ★隠しひねり: `allowas-in` — 仕様どおり組んでも spoke↔spoke が通らない

仕様どおり 2 VRF + 2 セッション + RT を組んでも、**CUST_B_UP に拠点経路が入らず**
spoke↔spoke は不通のまま（本社↔拠点は通る）。切り分けの芯:

1. 本社 CE 側（show は許可されている）: `show ip bgp neighbors 192.168.112.2
   advertised-routes` → **拠点経路×2 を上りセッションへ広告している**。
2. PE1 側: `show bgp vpnv4 unicast vrf CUST_B_UP | include 172.16` → **無い**。
   ★`soft-reconfiguration inbound` を付けて received-routes を見ても**現れない**
   （AS-PATH ループ検知は adj-RIB-in 格納前に破棄するため）。
3. `debug bgp all updates in`（★PE の VRF セッションは `debug ip bgp updates in`
   では出ない）→
   ```
   BGP(0): 192.168.112.1 rcv UPDATE w/ attr: ... merged path 65201 65000 65202, ...
   BGP(0): 192.168.112.1 rcv UPDATE about 172.16.2.0/24 -- DENIED due to: AS-PATH contains our own AS;
   ```
   折返し経路の AS_PATH は `65201 65000 6520x` = **自 AS 65000 を含む**ため
   受信側ループ検知で破棄されている。
4. CE は顧客管理で変更不可（allowas-in を CE に入れる選択肢はない）。SP 側の解は
   **上り neighbor への `allowas-in 1`**（path 中の 65000 は 1 回なので 1 で十分）。

## 検証（最終状態の指紋）

- PE1: `show bgp vpnv4 unicast vrf CUST_B_UP | include 172.16`
  → `172.16.2.0/24 192.168.112.1 ... 65201 65000 65202 i` / 同 65203。
- PE2: `show bgp vpnv4 unicast vrf CUST_B | include 172.16`
  → `172.16.3.0/24 1.1.1.1 ... 65201 65000 65203 i`（直接 3.3.3.3 経由は無い）。
- RT10: `show ip bgp 172.16.3.0` → AS_PATH `65000 65201 65000 65203`
  （**本社 AS 65201 の挟み込み** = 制御プレーンで本社経由を証明）。
- RT10: `traceroute 172.16.3.9 source 172.16.2.9 numeric`
  → `... 192.168.112.2 [MPLS] → 192.168.112.1 (本社CE) → 192.168.111.2 (PE1 再入)
  → ... → 192.168.13.1`（データプレーンで折返しを証明）。
- 本社→拠点の下り方向は CUST_B（下り VRF）の VPNv4 import 経路で直行
  （上りと非対称だが正常。折返しは拠点→拠点のみ）。

## よくある誤答

- **allowas-in を下り側（VLAN10）に付ける**: 下りは PE→CE 方向の広告が主で
  受信は本社 LAN のみ（ループ検知に当たらない）→ 意味がなく、spoke↔spoke は不通のまま。
- **拠点 PE が 220 も import**（import 210 220）: 直接経路が復活し AS_PATH 最短で
  勝つ = ポリシー違反のまま（採点は next-hop 3.3.3.3 の不在で検出）。
- **CUST_B_UP に import を付ける**: 上り VRF に VPNv4 経路が入り本社 CE へ
  逆流・経路が汚れる。要件上 import は不要（export 専用）。
- **旧 untagged ネイバー放置**: 本社 CE 側からは Idle ネイバーが残るだけだが、
  PE 側の IP 撤去を忘れると subif .10 と同一サブネットが衝突し得る（本問は
  111/112 で別サブネットのため衝突はしないが、仕様 R1 で撤去を要求）。
