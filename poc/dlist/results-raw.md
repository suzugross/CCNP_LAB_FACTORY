
## D0 基線  (2026-09-21 23:07)

- D0: 基線 13/13 経路(0s)

**D0 基線の経路**

```
10.50.0.0/22(RT02) / 10.50.0.0/24(RT02+RT03) / 10.50.0.0/26(RT02) / 10.50.0.0/28(RT03) / 10.50.0.16/28(RT02) / 10.50.1.0/24(RT02) / 10.50.2.0/24(RT02+RT03) / 10.50.2.128/25(RT02) / 10.50.3.0/24(RT02) / 10.50.9.0/24(RT03) / 10.60.0.0/24(RT02) / 10.60.0.0/28(RT02) / 10.60.1.0/24(RT02)
```

**D0 — RT01# show ip route eigrp**

```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      10.0.0.0/8 is variably subnetted, 18 subnets, 6 masks
D        10.0.24.0/24 [90/307200] via 10.0.12.2, 00:00:36, Ethernet0/0
D EX     10.50.0.0/22 [170/307200] via 10.0.12.2, 00:00:36, Ethernet0/0
D EX     10.50.0.0/24 [170/307200] via 10.0.13.3, 00:00:32, Ethernet0/1
                      [170/307200] via 10.0.12.2, 00:00:32, Ethernet0/0
D EX     10.50.0.0/26 [170/307200] via 10.0.12.2, 00:00:36, Ethernet0/0
D EX     10.50.0.0/28 [170/307200] via 10.0.13.3, 00:00:32, Ethernet0/1
D EX     10.50.0.16/28 [170/307200] via 10.0.12.2, 00:00:36, Ethernet0/0
D EX     10.50.1.0/24 [170/307200] via 10.0.12.2, 00:00:36, Ethernet0/0
D EX     10.50.2.0/24 [170/307200] via 10.0.13.3, 00:00:32, Ethernet0/1
                      [170/307200] via 10.0.12.2, 00:00:32, Ethernet0/0
D EX     10.50.2.128/25 [170/307200] via 10.0.12.2, 00:00:36, Ethernet0/0
D EX     10.50.3.0/24 [170/307200] via 10.0.12.2, 00:00:36, Ethernet0/0
D EX     10.50.9.0/24 [170/307200] via 10.0.13.3, 00:00:32, Ethernet0/1
D EX     10.60.0.0/24 [170/332800] via 10.0.12.2, 00:00:34, Ethernet0/0
D EX     10.60.0.0/28 [170/332800] via 10.0.12.2, 00:00:34, Ethernet0/0
D EX     10.60.1.0/24 [170/332800] via 10.0.12.2, 00:00:34, Ethernet0/0
```

**D0 — RT01# show ip eigrp neighbors**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
1   10.0.13.3               Et0/1                    14 00:00:39    1   100  0  3
0   10.0.12.2               Et0/0                    10 00:00:43    1   100  0  7
```


## D5 反映時間  (2026-09-21 23:11)

- D5: 反映の推移(秒, 経路数)= [(1, 13), (4, 13), (7, 13), (11, 4), (14, 4)]

**D5 log — RT01 show logging**

```
*Sep 21 23:07:06.768: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is up: new adjacency
*Sep 21 23:07:10.289: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is up: new adjacency
*Sep 21 23:09:26.177: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:09:26.177: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
*Sep 21 23:09:36.650: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:09:36.650: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
*Sep 21 23:09:54.776: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:09:54.776: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
*Sep 21 23:10:04.866: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:10:04.866: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
*Sep 21 23:10:22.841: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:10:22.841: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
*Sep 21 23:11:05.925: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:11:05.925: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
*Sep 21 23:11:17.502: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:11:17.502: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1a 標準 ACL `permit 10.50.0.0`(K1)  (2026-09-21 23:11)

**D1 部品の定義**

```
access-list 10 permit 10.50.0.0
access-list 110 permit ip any host 10.50.0.0
access-list 111 permit ip host 10.50.0.0 any
access-list 112 permit ip host 10.0.13.3 any
access-list 113 permit ip host 10.0.24.4 any
access-list 114 permit ip host 10.0.12.2 host 10.60.0.0
access-list 120 permit ip host 10.50.0.0 host 255.255.255.0
access-list 11 permit 10.50.0.0 0.0.2.255
route-map RM120 permit 10
match ip address 120
exit
ip prefix-list P1 seq 5 permit 10.50.0.0/16 ge 24 le 24
---
% Duplicate permit statement ignored
```

- == D1a: 標準 ACL `permit 10.50.0.0`(K1)(基線復帰 11s)

**D1a 投入**

```
router eigrp 100
distribute-list 10 in
---
(応答なし)
```

**D1a 残った経路(22s で安定)**

```
10.50.0.0/22(RT02) / 10.50.0.0/24(RT02+RT03) / 10.50.0.0/26(RT02) / 10.50.0.0/28(RT03)
```

**D1a — RT01# show access-lists 10**

```
Standard IP access list 10
    10 permit 10.50.0.0 (5 matches)
```

**D1a log — RT01 show logging**

```
*Sep 21 23:11:46.805: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:11:46.805: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1b 拡張・直接 `permit ip any host 10.50.0.0`(K2 dst=網)  (2026-09-21 23:12)

- == D1b: 拡張・直接 `permit ip any host 10.50.0.0`(K2 dst=網)(基線復帰 11s)

**D1b 投入**

```
router eigrp 100
distribute-list 110 in
---
(応答なし)
```

**D1b 残った経路(22s で安定)**

```
10.50.0.0/22(RT02) / 10.50.0.0/24(RT02+RT03) / 10.50.0.0/26(RT02) / 10.50.0.0/28(RT03)
```

**D1b — RT01# show access-lists 110**

```
Extended IP access list 110
    10 permit ip any host 10.50.0.0 (5 matches)
```

**D1b log — RT01 show logging**

```
*Sep 21 23:12:23.225: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:12:23.225: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1c 拡張・直接 `permit ip host 10.50.0.0 any`(K2 src に網を書く)  (2026-09-21 23:13)

- == D1c: 拡張・直接 `permit ip host 10.50.0.0 any`(K2 src に網を書く)(基線復帰 11s)

**D1c 投入**

```
router eigrp 100
distribute-list 111 in
---
(応答なし)
```

**D1c 残った経路(22s で安定)**

```
(なし)
```

**D1c — RT01# show access-lists 111**

```
Extended IP access list 111
    10 permit ip host 10.50.0.0 any
```

**D1c log — RT01 show logging**

```
*Sep 21 23:12:59.984: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:12:59.984: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1d 拡張・直接 `permit ip host 10.0.13.3 any`(K2 src=広告元 RT03)  (2026-09-21 23:13)

- == D1d: 拡張・直接 `permit ip host 10.0.13.3 any`(K2 src=広告元 RT03)(基線復帰 11s)

**D1d 投入**

```
router eigrp 100
distribute-list 112 in
---
(応答なし)
```

**D1d 残った経路(22s で安定)**

```
10.50.0.0/24(RT03) / 10.50.0.0/28(RT03) / 10.50.2.0/24(RT03) / 10.50.9.0/24(RT03)
```

**D1d — RT01# show access-lists 112**

```
Extended IP access list 112
    10 permit ip host 10.0.13.3 any (14 matches)
```

**D1d log — RT01 show logging**

```
*Sep 21 23:13:37.151: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:13:37.151: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1e 拡張・直接 `permit ip host 10.0.24.4 any`(K3 RT04= 作ったルータ)  (2026-09-21 23:14)

- == D1e: 拡張・直接 `permit ip host 10.0.24.4 any`(K3 RT04= 作ったルータ)(基線復帰 11s)

**D1e 投入**

```
router eigrp 100
distribute-list 113 in
---
(応答なし)
```

**D1e 残った経路(22s で安定)**

```
(なし)
```

**D1e — RT01# show access-lists 113**

```
Extended IP access list 113
    10 permit ip host 10.0.24.4 any
```

**D1e log — RT01 show logging**

```
*Sep 21 23:14:13.143: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:14:13.144: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1f 拡張・直接 `permit ip host 10.0.12.2 host 10.60.0.0`(K3 広告元 RT02 × 網)  (2026-09-21 23:15)

- == D1f: 拡張・直接 `permit ip host 10.0.12.2 host 10.60.0.0`(K3 広告元 RT02 × 網)(基線復帰 11s)

**D1f 投入**

```
router eigrp 100
distribute-list 114 in
---
(応答なし)
```

**D1f 残った経路(22s で安定)**

```
10.60.0.0/24(RT02) / 10.60.0.0/28(RT02)
```

**D1f — RT01# show access-lists 114**

```
Extended IP access list 114
    10 permit ip host 10.0.12.2 host 10.60.0.0 (2 matches)
```

**D1f log — RT01 show logging**

```
*Sep 21 23:14:49.248: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:14:49.248: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1g route-map 経由 `permit ip host 10.50.0.0 host 255.255.255.0`(K4)  (2026-09-21 23:15)

- == D1g: route-map 経由 `permit ip host 10.50.0.0 host 255.255.255.0`(K4)(基線復帰 11s)

**D1g 投入**

```
router eigrp 100
distribute-list route-map RM120 in
---
(応答なし)
```

**D1g 残った経路(22s で安定)**

```
10.50.0.0/24(RT02+RT03)
```

**D1g — RT01# show access-lists 120**

```
Extended IP access list 120
    10 permit ip host 10.50.0.0 host 255.255.255.0 (2 matches)
```

**D1g log — RT01 show logging**

```
*Sep 21 23:15:25.594: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:15:25.594: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1h prefix-list `10.50.0.0/16 ge 24 le 24`(K5)  (2026-09-21 23:16)

- == D1h: prefix-list `10.50.0.0/16 ge 24 le 24`(K5)(基線復帰 11s)

**D1h 投入**

```
router eigrp 100
distribute-list prefix P1 in
---
(応答なし)
```

**D1h 残った経路(21s で安定)**

```
10.50.0.0/24(RT02+RT03) / 10.50.1.0/24(RT02) / 10.50.2.0/24(RT02+RT03) / 10.50.3.0/24(RT02) / 10.50.9.0/24(RT03)
```

**D1h — RT01# show ip prefix-list P1**

```
ip prefix-list P1: 1 entries
   seq 5 permit 10.50.0.0/16 ge 24 le 24
```

**D1h log — RT01 show logging**

```
*Sep 21 23:16:01.548: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:16:01.548: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D1i 標準 ACL 非連続 `permit 10.50.0.0 0.0.2.255`(K6)  (2026-09-21 23:16)

- == D1i: 標準 ACL 非連続 `permit 10.50.0.0 0.0.2.255`(K6)(基線復帰 11s)

**D1i 投入**

```
router eigrp 100
distribute-list 11 in
---
(応答なし)
```

**D1i 残った経路(22s で安定)**

```
10.50.0.0/22(RT02) / 10.50.0.0/24(RT02+RT03) / 10.50.0.0/26(RT02) / 10.50.0.0/28(RT03) / 10.50.0.16/28(RT02) / 10.50.2.0/24(RT02+RT03) / 10.50.2.128/25(RT02)
```

**D1i — RT01# show access-lists 11**

```
Standard IP access list 11
    10 permit 10.50.0.0, wildcard bits 0.0.2.255 (9 matches)
```

**D1i log — RT01 show logging**

```
*Sep 21 23:16:36.742: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:16:36.742: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D2a 全体 prefix P24(/24 だけ) + IF(e0/1=RT03) ACL 30(10.50.0.0 のみ)  (2026-09-21 23:17)

**D2 部品**

```
access-list 30 permit 10.50.0.0
ip prefix-list P24 seq 5 permit 0.0.0.0/0 ge 24 le 24
---
(応答なし)
```

- == D2a: 全体 prefix P24(/24 だけ) + IF(e0/1=RT03) ACL 30(10.50.0.0 のみ)(基線復帰 11s)

**D2a 投入**

```
router eigrp 100
distribute-list prefix P24 in
distribute-list 30 in Ethernet0/1
---
(応答なし)
```

**D2a 残った経路(22s で安定)**

```
10.50.0.0/24(RT02+RT03) / 10.50.1.0/24(RT02) / 10.50.2.0/24(RT02) / 10.50.3.0/24(RT02) / 10.60.0.0/24(RT02) / 10.60.1.0/24(RT02)
```

**D2a — RT01# show ip protocols | include filter|Distribute|Ethernet**

```
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is (prefix-list) P24
    Ethernet0/1 filtered by 30 (per-user), default is not set
```

**D2a log — RT01 show logging**

```
*Sep 21 23:17:13.287: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:17:13.287: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D3a 同 IF(e0/0=RT02) に ACL 31(10.50.0.x)→ prefix P26(/26) の順で投入  (2026-09-21 23:18)

**D3 部品**

```
ip prefix-list P26 seq 5 permit 0.0.0.0/0 ge 26 le 26
access-list 31 permit 10.50.0.0 0.0.0.255
---
(応答なし)
```

- == D3a: 同 IF(e0/0=RT02) に ACL 31(10.50.0.x)→ prefix P26(/26) の順で投入(基線復帰 11s)

**D3a 投入**

```
router eigrp 100
distribute-list 31 in Ethernet0/0
distribute-list prefix P26 in Ethernet0/0
---
%EIGRP: Access-list filter exists, de-config first
```

**D3a 残った経路(22s で安定)**

```
10.50.0.0/22(RT02) / 10.50.0.0/24(RT02+RT03) / 10.50.0.0/26(RT02) / 10.50.0.0/28(RT03) / 10.50.0.16/28(RT02) / 10.50.2.0/24(RT03) / 10.50.9.0/24(RT03)
```

**D3a — RT01# show running-config | section router eigrp**

```
router eigrp 100
 distribute-list 31 in Ethernet0/0
 network 10.0.12.0 0.0.0.255
 network 10.0.13.0 0.0.0.255
 eigrp router-id 1.1.1.1
```

**D3a — RT01# show ip protocols | include filter|Distribute|Ethernet**

```
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
    Ethernet0/0 filtered by 31 (per-user), default is not set
```

**D3a log — RT01 show logging**

```
*Sep 21 23:17:51.484: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: intf route configuration changed
```

## D3b 同 IF(e0/0) に ACL 31 → route-map RM120 の順で投入  (2026-09-21 23:18)

- == D3b: 同 IF(e0/0) に ACL 31 → route-map RM120 の順で投入(基線復帰 11s)

**D3b 投入**

```
router eigrp 100
distribute-list 31 in Ethernet0/0
distribute-list route-map RM120 in Ethernet0/0
---
%EIGRP: Access-list filter exists, de-config first
```

**D3b 残った経路(22s で安定)**

```
10.50.0.0/22(RT02) / 10.50.0.0/24(RT02+RT03) / 10.50.0.0/26(RT02) / 10.50.0.0/28(RT03) / 10.50.0.16/28(RT02) / 10.50.2.0/24(RT03) / 10.50.9.0/24(RT03)
```

**D3b — RT01# show running-config | section router eigrp**

```
router eigrp 100
 distribute-list 31 in Ethernet0/0
 network 10.0.12.0 0.0.0.255
 network 10.0.13.0 0.0.0.255
 eigrp router-id 1.1.1.1
```

**D3b log — RT01 show logging**

```
*Sep 21 23:18:28.711: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: intf route configuration changed
```

## D4a route-map 経由 dst= `255.255.255.0 0.0.0.255`(マスク /24〜/32 のつもり)  (2026-09-21 23:19)

**D4 部品**

```
access-list 121 permit ip 10.50.0.0 0.0.255.255 255.255.255.0 0.0.0.255
route-map RM121 permit 10
match ip address 121
exit
access-list 122 permit ip 10.50.0.0 0.0.255.255 host 255.255.255.0
route-map RM122 permit 10
match ip address 122
exit
---
(応答なし)
```

- == D4a: route-map 経由 dst= `255.255.255.0 0.0.0.255`(マスク /24〜/32 のつもり)(基線復帰 11s)

**D4a 投入**

```
router eigrp 100
distribute-list route-map RM121 in
---
(応答なし)
```

**D4a 残った経路(22s で安定)**

```
10.50.0.0/24(RT02+RT03) / 10.50.0.0/26(RT02) / 10.50.0.0/28(RT03) / 10.50.0.16/28(RT02) / 10.50.1.0/24(RT02) / 10.50.2.0/24(RT02+RT03) / 10.50.2.128/25(RT02) / 10.50.3.0/24(RT02) / 10.50.9.0/24(RT03)
```

**D4a — RT01# show access-lists 121**

```
Extended IP access list 121
    10 permit ip 10.50.0.0 0.0.255.255 255.255.255.0 0.0.0.255 (11 matches)
```

**D4a log — RT01 show logging**

```
*Sep 21 23:19:06.933: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:19:06.933: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```

## D4b route-map 経由 dst= `host 255.255.255.0`・src= 10.50/16(/24 ちょうど)  (2026-09-21 23:19)

- == D4b: route-map 経由 dst= `host 255.255.255.0`・src= 10.50/16(/24 ちょうど)(基線復帰 11s)

**D4b 投入**

```
router eigrp 100
distribute-list route-map RM122 in
---
(応答なし)
```

**D4b 残った経路(21s で安定)**

```
10.50.0.0/24(RT02+RT03) / 10.50.1.0/24(RT02) / 10.50.2.0/24(RT02+RT03) / 10.50.3.0/24(RT02) / 10.50.9.0/24(RT03)
```

**D4b — RT01# show access-lists 122**

```
Extended IP access list 122
    10 permit ip 10.50.0.0 0.0.255.255 host 255.255.255.0 (7 matches)
```

**D4b log — RT01 show logging**

```
*Sep 21 23:19:42.516: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.13.3 (Ethernet0/1) is resync: route configuration changed
*Sep 21 23:19:42.516: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.0.12.2 (Ethernet0/0) is resync: route configuration changed
```
