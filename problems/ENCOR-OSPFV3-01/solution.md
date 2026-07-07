# 模範解答 ENCOR-OSPFV3-01

## 全ルータ共通：データIF有効化（day0/再起動で admin-down のことがある）
```
interface Ethernet0/0
 no shutdown
! RT02 は Ethernet0/1 も
```

## RT01
```
ipv6 router ospf 1
 router-id 1.1.1.1
interface Loopback0
 ipv6 ospf 1 area 0
interface Ethernet0/0
 ipv6 ospf 1 area 0
```

## RT02
```
ipv6 router ospf 1
 router-id 2.2.2.2
interface Loopback0
 ipv6 ospf 1 area 0
interface Ethernet0/0
 ipv6 ospf 1 area 0
interface Ethernet0/1
 ipv6 ospf 1 area 0
```

## RT03（OSPFv3 + IPv6 ACL）
```
ipv6 router ospf 1
 router-id 3.3.3.3
interface Loopback0
 ipv6 ospf 1 area 0
interface Ethernet0/0
 ipv6 ospf 1 area 0
!
ipv6 access-list BLOCK-RT01-TO-RT03
 deny icmp host 2001:DB8:1::1 host 2001:DB8:3::3
 permit ipv6 any any
interface Ethernet0/0
 ipv6 traffic-filter BLOCK-RT01-TO-RT03 in
```

## ポイント / 教育核心
- **OSPFv3 のルータ ID 自動選定の罠**：IPv6 only で IPv4 アドレスが 1 つも無いと、OSPFv3 は
  router-id を選べず隣接が立たない（BGP の `bgp router-id` と同型）。各プロセスで **`router-id` を手動指定**。
- **OSPFv3 の有効化はインタフェース単位**：`ipv6 ospf 1 area 0`（IPv4 OSPF の network 文と違い IF 直付け）。
  ※ `router ospfv3` + `ospfv3 1 ipv6 area 0`（アドレスファミリ方式）でも可。採点は効果ベースなので両方可。
- **IPv6 ACL の暗黙 deny**：`deny icmp host RT01lo host RT03lo` の後に **`permit ipv6 any any`** を置かないと、
  暗黙 deny で OSPFv3(next-header 89)まで落ちて隣接断 → 全到達崩壊。ND は ICMPv6 だがリンクローカル間なので
  この deny(グローバル同士)には掛からない。
- **ACL は inbound 方向**で RT02 からの流入を RT03 で濾過。送信元(RT01lo)で判別するので RT02→RT03lo は通る。
- 確認：`show ipv6 route ospf`／`ping 2001:DB8:3::3 source Lo0`（RT02=成功 / RT01=遮断）。
