

# 実行 2026-08-16 10:54:02 — checks=['o1', 'e1']

## o1

RO1 `show ip route ospf`:
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

      2.0.0.0/32 is subnetted, 1 subnets
O        2.2.2.2 [110/11] via 10.10.12.2, 00:00:12, Ethernet0/0
      3.0.0.0/32 is subnetted, 1 subnets
O        3.3.3.3 [110/11] via 10.10.13.3, 00:00:07, Ethernet0/1
      4.0.0.0/32 is subnetted, 1 subnets
O IA     4.4.4.4 [110/21] via 10.10.13.3, 00:00:04, Ethernet0/1
      10.0.0.0/8 is variably subnetted, 10 subnets, 2 masks
O IA     10.10.34.0/24 [110/20] via 10.10.13.3, 00:00:07, Ethernet0/1
O E2     10.96.6.0/24 [110/20] via 10.10.12.2, 00:00:12, Ethernet0/0
O E1     10.97.7.0/24 [110/110] via 10.10.12.2, 00:00:12, Ethernet0/0
O        10.98.8.0/24 [110/510] via 10.10.12.2, 00:00:12, Ethernet0/0
```

RO1 `show ip route 10.98.8.0` (intra vs inter):
```
Routing entry for 10.98.8.0/24
  Known via "ospf 1", distance 110, metric 510, type intra area
  Last update from 10.10.12.2 on Ethernet0/0, 00:00:13 ago
  Routing Descriptor Blocks:
  * 10.10.12.2, from 2.2.2.2, 00:00:13 ago, via Ethernet0/0
      Route metric is 510, traffic share count is 1
```

RO1 `show ip route 10.97.7.0` (E1 vs E2):
```
Routing entry for 10.97.7.0/24
  Known via "ospf 1", distance 110, metric 110, type extern 1
  Last update from 10.10.12.2 on Ethernet0/0, 00:00:13 ago
  Routing Descriptor Blocks:
  * 10.10.12.2, from 2.2.2.2, 00:00:13 ago, via Ethernet0/0
      Route metric is 110, traffic share count is 1
```

RO1 `show ip route 10.96.6.0` (E2 vs E2):
```
Routing entry for 10.96.6.0/24
  Known via "ospf 1", distance 110, metric 20, type extern 2, forward metric 10
  Last update from 10.10.12.2 on Ethernet0/0, 00:00:14 ago
  Routing Descriptor Blocks:
  * 10.10.12.2, from 2.2.2.2, 00:00:14 ago, via Ethernet0/0
      Route metric is 20, traffic share count is 1
```

## e1

E1 RE1 `show ip eigrp topology`:
```
EIGRP-IPv4 Topology Table for AS(100)/ID(11.11.11.11)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 10.20.14.0/24, 1 successors, FD is 281600
        via Connected, Ethernet0/2
P 11.11.11.11/32, 1 successors, FD is 128256
        via Connected, Loopback0
P 33.33.33.33/32, 1 successors, FD is 460800
        via 10.20.13.3 (460800/128256), Ethernet0/1
P 10.20.45.0/24, 1 successors, FD is 332800, U
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (384000/307200), Ethernet0/1
P 10.20.12.0/24, 1 successors, FD is 281600
        via Connected, Ethernet0/0
P 44.44.44.44/32, 1 successors, FD is 409600, U
        via 10.20.14.4 (409600/128256), Ethernet0/2
P 55.55.55.55/32, 1 successors, FD is 435200, U
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 22.22.22.22/32, 1 successors, FD is 409600
        via 10.20.12.2 (409600/128256), Ethernet0/0
P 10.20.13.0/24, 1 successors, FD is 332800
        via Connected, Ethernet0/1
P 10.20.25.0/24, 1 successors, FD is 307200
        via 10.20.12.2 (307200/281600), Ethernet0/0
P 10.99.9.0/24, 1 successors, FD is 435200, U
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 10.20.35.0/24, 1 successors, FD is 332800, U
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (358400/281600), Ethernet0/1
```

E1 RE1 `show ip eigrp topology 10.99.9.0 255.255.255.0`:
```
EIGRP-IPv4 Topology Entry for AS(100)/ID(11.11.11.11) for 10.99.9.0/24
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 435200
  Descriptor Blocks:
  10.20.12.2 (Ethernet0/0), from 10.20.12.2, Send flag is 0x0
      Composite metric is (435200/409600), route is Internal
      Vector metric:
        Minimum bandwidth is 10000 Kbit
        Total delay is 7000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1500
        Hop count is 2
        Originating router is 55.55.55.55
  10.20.13.3 (Ethernet0/1), from 10.20.13.3, Send flag is 0x0
      Composite metric is (486400/409600), route is Internal
      Vector metric:
        Minimum bandwidth is 10000 Kbit
        Total delay is 9000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1500
        Hop count is 2
        Originating router is 55.55.55.55
```

E1 RE1 `show ip eigrp topology all-links`:
```
EIGRP-IPv4 Topology Table for AS(100)/ID(11.11.11.11)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 10.20.14.0/24, 1 successors, FD is 281600, serno 4
        via Connected, Ethernet0/2
P 11.11.11.11/32, 1 successors, FD is 128256, serno 1, anchored
        via Connected, Loopback0
P 33.33.33.33/32, 1 successors, FD is 460800, serno 7
        via 10.20.13.3 (460800/128256), Ethernet0/1
P 10.20.45.0/24, 1 successors, FD is 332800, U, serno 14, refcount 1
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (384000/307200), Ethernet0/1
        via 10.20.14.4 (384000/358400), Ethernet0/2
P 10.20.12.0/24, 1 successors, FD is 281600, serno 2
        via Connected, Ethernet0/0
P 44.44.44.44/32, 1 successors, FD is 409600, U, serno 9, refcount 1, anchored
        via 10.20.14.4 (409600/128256), Ethernet0/2
P 55.55.55.55/32, 1 successors, FD is 435200, U, serno 11, refcount 1
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 22.22.22.22/32, 1 successors, FD is 409600, serno 5
        via 10.20.12.2 (409600/128256), Ethernet0/0
P 10.20.13.0/24, 1 successors, FD is 332800, serno 3
        via Connected, Ethernet0/1
P 10.20.25.0/24, 1 successors, FD is 307200, serno 6
        via 10.20.12.2 (307200/281600), Ethernet0/0
        via 10.20.13.3 (384000/307200), Ethernet0/1
P 10.99.9.0/24, 1 successors, FD is 435200, U, serno 12, refcount 1
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 10.20.35.0/24, 1 successors, FD is 332800, U, serno 13, refcount 1
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (358400/281600), Ethernet0/1
```

E1 RE1 `show ip route 10.99.9.0`:
```
Routing entry for 10.99.9.0/24
  Known via "eigrp 100", distance 90, metric 435200, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 10.20.12.2 on Ethernet0/0, 00:00:01 ago
  Routing Descriptor Blocks:
  * 10.20.12.2, from 10.20.12.2, 00:00:01 ago, via Ethernet0/0
      Route metric is 435200, traffic share count is 1
      Total delay is 7000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
```

E1 RE1 `show ip eigrp neighbors`:
```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
2   10.20.14.4              Et0/2                    11 00:00:05 1998  5000  1  2
1   10.20.13.3              Et0/1                    13 00:00:10 1024  5000  0  8
0   10.20.12.2              Et0/0                    13 00:00:24  818  4908  0  9
```
- **期待値**: via RE2 FD=435200(successor) / via RE3 RD=409600 FD=486400(FS) / via RE4 RD=486400 FD=512000(FC不成立)


# 実行 2026-08-16 10:56:49 — checks=['o2', 'o3', 'o4', 'o5', 'o6', 'e1', 'e2', 'e3', 'e4']

## o2

O2 RO1 `show ip route 10.98.8.0`:
```
Routing entry for 10.98.8.0/24
  Known via "ospf 1", distance 110, metric 510, type intra area
  Last update from 10.10.12.2 on Ethernet0/0, 00:02:59 ago
  Routing Descriptor Blocks:
  * 10.10.12.2, from 2.2.2.2, 00:02:59 ago, via Ethernet0/0
      Route metric is 510, traffic share count is 1
```

O2 RO1 `show ip ospf database summary 10.98.8.0`:
```
OSPF Router with ID (1.1.1.1) (Process ID 1)

		Summary Net Link States (Area 0)

  LS age: 172
  Options: (No TOS-capability, DC, Upward)
  LS Type: Summary Links(Network)
  Link State ID: 10.98.8.0 (summary Network Number)
  Advertising Router: 3.3.3.3
  LS Seq Number: 80000001
  Checksum: 0x268B
  Length: 28
  Network Mask: /24
	MTID: 0 	Metric: 11
```
- **判定**: metric=510 / 表示型= intra(型記載なし) → intra が勝てば metric 510 のはず

## o3

O3 RO1 `show ip route 10.97.7.0`:
```
Routing entry for 10.97.7.0/24
  Known via "ospf 1", distance 110, metric 110, type extern 1
  Last update from 10.10.12.2 on Ethernet0/0, 00:02:59 ago
  Routing Descriptor Blocks:
  * 10.10.12.2, from 2.2.2.2, 00:02:59 ago, via Ethernet0/0
      Route metric is 110, traffic share count is 1
```
- **判定**: `type extern 1` かつ metric 110 なら型優先+累積の実証

## o4

O4 RO1 `show ip route 10.96.6.0`:
```
Routing entry for 10.96.6.0/24
  Known via "ospf 1", distance 110, metric 20, type extern 2, forward metric 10
  Last update from 10.10.12.2 on Ethernet0/0, 00:03:00 ago
  Routing Descriptor Blocks:
  * 10.10.12.2, from 2.2.2.2, 00:03:00 ago, via Ethernet0/0
      Route metric is 20, traffic share count is 1
```
- **判定**: via 10.10.12.2(RO2)・forward metric 10 なら実証(RO5 側は forward metric 100)

## o5

O5 RO1 e0/0 cost 60 後 `show ip route 10.97.7.0`:
```
Routing entry for 10.97.7.0/24
  Known via "ospf 1", distance 110, metric 160, type extern 1
  Last update from 10.10.12.2 on Ethernet0/0, 00:00:16 ago
  Routing Descriptor Blocks:
  * 10.10.12.2, from 2.2.2.2, 00:00:16 ago, via Ethernet0/0
      Route metric is 160, traffic share count is 1
```
- **判定**: E1 metric が 110→160 に動けば累積(外部100+内部60)

O5 同条件 `show ip route 10.96.6.0` (E2):
```
Routing entry for 10.96.6.0/24
  Known via "ospf 1", distance 110, metric 20, type extern 2, forward metric 60
  Last update from 10.10.12.2 on Ethernet0/0, 00:03:16 ago
  Routing Descriptor Blocks:
  * 10.10.12.2, from 2.2.2.2, 00:03:16 ago, via Ethernet0/0
      Route metric is 20, traffic share count is 1
```
- **判定**: E2 の metric は 20 のまま・forward metric だけ 10→60 (それでも RO5 の 100 より小さいので勝者不変)

## o6

O6 RO1 `show ip ospf database external 10.97.7.0`:
```
OSPF Router with ID (1.1.1.1) (Process ID 1)

		Type-5 AS External Link States

  LS age: 252
  Options: (No TOS-capability, DC, Upward)
  LS Type: AS External Link
  Link State ID: 10.97.7.0 (External Network Number )
  Advertising Router: 2.2.2.2
  LS Seq Number: 80000001
  Checksum: 0xEA6B
  Length: 36
  Network Mask: /24
	Metric Type: 1 (Comparable directly to link state metric)
	MTID: 0 
	Metric: 100 
	Forward Address: 0.0.0.0
	External Route Tag: 0

  LS age: 229
  Options: (No TOS-capability, DC, Upward)
  LS Type: AS External Link
  Link State ID: 10.97.7.0 (External Network Number )
  Advertising Router: 5.5.5.5
  LS Seq Number: 80000001
  Checksum: 0x8C97
  Length: 36
  Network Mask: /24
	Metric Type: 2 (Larger than any link state path)
	MTID: 0 
	Metric: 10 
	Forward Address: 0.0.0.0
	External Route Tag: 0
```

O6 RO1 `show ip ospf database external 10.96.6.0`:
```
OSPF Router with ID (1.1.1.1) (Process ID 1)

		Type-5 AS External Link States

  LS age: 252
  Options: (No TOS-capability, DC, Upward)
  LS Type: AS External Link
  Link State ID: 10.96.6.0 (External Network Number )
  Advertising Router: 2.2.2.2
  LS Seq Number: 80000001
  Checksum: 0x62C5
  Length: 36
  Network Mask: /24
	Metric Type: 2 (Larger than any link state path)
	MTID: 0 
	Metric: 20 
	Forward Address: 0.0.0.0
	External Route Tag: 0

  LS age: 230
  Options: (No TOS-capability, DC, Upward)
  LS Type: AS External Link
  Link State ID: 10.96.6.0 (External Network Number )
  Advertising Router: 5.5.5.5
  LS Seq Number: 80000001
  Checksum: 0x814
  Length: 36
  Network Mask: /24
	Metric Type: 2 (Larger than any link state path)
	MTID: 0 
	Metric: 20 
	Forward Address: 0.0.0.0
	External Route Tag: 0
```

O6 RO1 `show ip ospf database`:
```
OSPF Router with ID (1.1.1.1) (Process ID 1)

		Router Link States (Area 0)

Link ID         ADV Router      Age         Seq#       Checksum Link count
1.1.1.1         1.1.1.1         16          0x80000012 0x009504 4         
2.2.2.2         2.2.2.2         65          0x8000000C 0x001E17 3         
3.3.3.3         3.3.3.3         64          0x80000007 0x003D68 2         
5.5.5.5         5.5.5.5         52          0x80000009 0x003BEC 2         

		Net Link States (Area 0)

Link ID         ADV Router      Age         Seq#       Checksum
10.10.12.2      2.2.2.2         214         0x80000001 0x0046BD
10.10.13.3      3.3.3.3         209         0x80000001 0x0035C4
10.10.15.5      5.5.5.5         191         0x80000001 0x0013D2

		Summary Net Link States (Area 0)

Link ID         ADV Router      Age         Seq#       Checksum
4.4.4.4         3.3.3.3         206         0x80000001 0x00E431
10.10.34.0      3.3.3.3         248         0x80000001 0x0021CF
10.98.8.0       3.3.3.3         206         0x80000001 0x00268B

		Type-5 AS External Link States

Link ID         ADV Router      Age         Seq#       Checksum Tag
10.96.6.0       2.2.2.2         253         0x80000001 0x0062C5 0         
10.96.6.0       5.5.5.5         230         0x80000001 0x000814 0         
10.97.7.0       2.2.2.2         253         0x80000001 0x00EA6B 0         
10.97.7.0       5.5.5.5         230         0x80000001 0x008C97 0
```

O6 RO1 `show ip ospf border-routers`:
```
OSPF Router with ID (1.1.1.1) (Process ID 1)


		Base Topology (MTID 0)

Internal Router Routing Table
Codes: i - Intra-area route, I - Inter-area route

i 5.5.5.5 [100] via 10.10.15.5, Ethernet0/2, ASBR, Area 0, SPF 21
i 2.2.2.2 [10] via 10.10.12.2, Ethernet0/0, ASBR, Area 0, SPF 21
i 3.3.3.3 [10] via 10.10.13.3, Ethernet0/1, ABR, Area 0, SPF 21
```

## e1

E1 RE1 `show ip eigrp topology`:
```
EIGRP-IPv4 Topology Table for AS(100)/ID(11.11.11.11)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 10.20.14.0/24, 1 successors, FD is 281600
        via Connected, Ethernet0/2
P 11.11.11.11/32, 1 successors, FD is 128256
        via Connected, Loopback0
P 33.33.33.33/32, 2 successors, FD is 460800
        via 10.20.13.3 (460800/128256), Ethernet0/1
        via 10.20.12.2 (460800/435200), Ethernet0/0
P 10.20.45.0/24, 1 successors, FD is 332800
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (384000/307200), Ethernet0/1
P 10.20.12.0/24, 1 successors, FD is 281600
        via Connected, Ethernet0/0
P 44.44.44.44/32, 1 successors, FD is 409600
        via 10.20.14.4 (409600/128256), Ethernet0/2
P 55.55.55.55/32, 1 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 22.22.22.22/32, 1 successors, FD is 409600
        via 10.20.12.2 (409600/128256), Ethernet0/0
P 10.20.13.0/24, 1 successors, FD is 332800
        via Connected, Ethernet0/1
P 10.20.25.0/24, 1 successors, FD is 307200
        via 10.20.12.2 (307200/281600), Ethernet0/0
P 10.99.9.0/24, 1 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 10.20.35.0/24, 1 successors, FD is 332800
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (358400/281600), Ethernet0/1
```

E1 RE1 `show ip eigrp topology 10.99.9.0 255.255.255.0`:
```
EIGRP-IPv4 Topology Entry for AS(100)/ID(11.11.11.11) for 10.99.9.0/24
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 435200
  Descriptor Blocks:
  10.20.12.2 (Ethernet0/0), from 10.20.12.2, Send flag is 0x0
      Composite metric is (435200/409600), route is Internal
      Vector metric:
        Minimum bandwidth is 10000 Kbit
        Total delay is 7000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1500
        Hop count is 2
        Originating router is 55.55.55.55
  10.20.13.3 (Ethernet0/1), from 10.20.13.3, Send flag is 0x0
      Composite metric is (486400/409600), route is Internal
      Vector metric:
        Minimum bandwidth is 10000 Kbit
        Total delay is 9000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1500
        Hop count is 2
        Originating router is 55.55.55.55
```

E1 RE1 `show ip eigrp topology all-links`:
```
EIGRP-IPv4 Topology Table for AS(100)/ID(11.11.11.11)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 10.20.14.0/24, 1 successors, FD is 281600, serno 4
        via Connected, Ethernet0/2
P 11.11.11.11/32, 1 successors, FD is 128256, serno 1
        via Connected, Loopback0
P 33.33.33.33/32, 2 successors, FD is 460800, serno 15
        via 10.20.13.3 (460800/128256), Ethernet0/1
        via 10.20.12.2 (460800/435200), Ethernet0/0
P 10.20.45.0/24, 1 successors, FD is 332800, serno 14
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (384000/307200), Ethernet0/1
        via 10.20.14.4 (384000/358400), Ethernet0/2
P 10.20.12.0/24, 1 successors, FD is 281600, serno 2
        via Connected, Ethernet0/0
P 44.44.44.44/32, 1 successors, FD is 409600, serno 9
        via 10.20.14.4 (409600/128256), Ethernet0/2
P 55.55.55.55/32, 1 successors, FD is 435200, serno 11
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 22.22.22.22/32, 1 successors, FD is 409600, serno 5
        via 10.20.12.2 (409600/128256), Ethernet0/0
P 10.20.13.0/24, 1 successors, FD is 332800, serno 3
        via Connected, Ethernet0/1
        via 10.20.12.2 (358400/332800), Ethernet0/0
P 10.20.25.0/24, 1 successors, FD is 307200, serno 6
        via 10.20.12.2 (307200/281600), Ethernet0/0
        via 10.20.13.3 (384000/307200), Ethernet0/1
P 10.99.9.0/24, 1 successors, FD is 435200, serno 12
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 10.20.35.0/24, 1 successors, FD is 332800, serno 13
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (358400/281600), Ethernet0/1
```

E1 RE1 `show ip route 10.99.9.0`:
```
Routing entry for 10.99.9.0/24
  Known via "eigrp 100", distance 90, metric 435200, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 10.20.12.2 on Ethernet0/0, 00:07:21 ago
  Routing Descriptor Blocks:
  * 10.20.12.2, from 10.20.12.2, 00:07:21 ago, via Ethernet0/0
      Route metric is 435200, traffic share count is 1
      Total delay is 7000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
```

E1 RE1 `show ip eigrp neighbors`:
```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
2   10.20.14.4              Et0/2                    10 00:07:25 1278  5000  0  6
1   10.20.13.3              Et0/1                    10 00:07:30  819  4914  0  10
0   10.20.12.2              Et0/0                    14 00:07:44  654  3924  0  13
```
- **期待値**: via RE2 FD=435200(successor) / via RE3 RD=409600 FD=486400(FS) / via RE4 RD=486400 FD=512000(FC不成立)

## e2

E2 RE4 e0/1 delay 200 後 `show ip eigrp topology all-links`:
```
EIGRP-IPv4 Topology Table for AS(100)/ID(11.11.11.11)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 10.20.14.0/24, 1 successors, FD is 281600, serno 4
        via Connected, Ethernet0/2
P 11.11.11.11/32, 1 successors, FD is 128256, serno 1
        via Connected, Loopback0
P 33.33.33.33/32, 2 successors, FD is 460800, serno 15
        via 10.20.13.3 (460800/128256), Ethernet0/1
        via 10.20.12.2 (460800/435200), Ethernet0/0
        via 10.20.14.4 (486400/460800), Ethernet0/2
P 10.20.45.0/24, 2 successors, FD is 332800, serno 16
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.14.4 (332800/307200), Ethernet0/2
        via 10.20.13.3 (384000/307200), Ethernet0/1
P 10.20.12.0/24, 1 successors, FD is 281600, serno 2
        via Connected, Ethernet0/0
P 44.44.44.44/32, 1 successors, FD is 409600, serno 9
        via 10.20.14.4 (409600/128256), Ethernet0/2
P 55.55.55.55/32, 1 successors, FD is 435200, serno 11
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.14.4 (460800/435200), Ethernet0/2
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 22.22.22.22/32, 1 successors, FD is 409600, serno 5
        via 10.20.12.2 (409600/128256), Ethernet0/0
P 10.20.13.0/24, 1 successors, FD is 332800, serno 3
        via Connected, Ethernet0/1
        via 10.20.12.2 (358400/332800), Ethernet0/0
P 10.20.25.0/24, 1 successors, FD is 307200, serno 6
        via 10.20.12.2 (307200/281600), Ethernet0/0
        via 10.20.13.3 (384000/307200), Ethernet0/1
P 10.99.9.0/24, 1 successors, FD is 435200, serno 12
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.14.4 (460800/435200), Ethernet0/2
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 10.20.35.0/24, 1 successors, FD is 332800, serno 13
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.14.4 (358400/332800), Ethernet0/2
        via 10.20.13.3 (358400/281600), Ethernet0/1
```

E2 `show ip eigrp topology 10.99.9.0 255.255.255.0`:
```
EIGRP-IPv4 Topology Entry for AS(100)/ID(11.11.11.11) for 10.99.9.0/24
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 435200
  Descriptor Blocks:
  10.20.12.2 (Ethernet0/0), from 10.20.12.2, Send flag is 0x0
      Composite metric is (435200/409600), route is Internal
      Vector metric:
        Minimum bandwidth is 10000 Kbit
        Total delay is 7000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1500
        Hop count is 2
        Originating router is 55.55.55.55
  10.20.14.4 (Ethernet0/2), from 10.20.14.4, Send flag is 0x0
      Composite metric is (460800/435200), route is Internal
      Vector metric:
        Minimum bandwidth is 10000 Kbit
        Total delay is 8000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1500
        Hop count is 2
        Originating router is 55.55.55.55
  10.20.13.3 (Ethernet0/1), from 10.20.13.3, Send flag is 0x0
      Composite metric is (486400/409600), route is Internal
      Vector metric:
        Minimum bandwidth is 10000 Kbit
        Total delay is 9000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1500
        Hop count is 2
        Originating router is 55.55.55.55
```

E2 variance 4 で `show ip route 10.99.9.0`:
```
Routing entry for 10.99.9.0/24
  Known via "eigrp 100", distance 90, metric 435200, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 10.20.13.3 on Ethernet0/1, 00:00:21 ago
  Routing Descriptor Blocks:
    10.20.13.3, from 10.20.13.3, 00:00:21 ago, via Ethernet0/1
      Route metric is 486400, traffic share count is 43
      Total delay is 9000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
  * 10.20.12.2, from 10.20.12.2, 00:00:21 ago, via Ethernet0/0
      Route metric is 435200, traffic share count is 48
      Total delay is 7000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
```
- **判定**: RD(435200) == FD_succ(435200) の RE4 経路が **乗らなければ FC は厳密不等号**(モデルの核)。乗ってしまうなら等号可としてモデルを直す

## e3

E3 variance 2 `show ip route 10.99.9.0`:
```
Routing entry for 10.99.9.0/24
  Known via "eigrp 100", distance 90, metric 435200, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 10.20.13.3 on Ethernet0/1, 00:00:20 ago
  Routing Descriptor Blocks:
    10.20.13.3, from 10.20.13.3, 00:00:20 ago, via Ethernet0/1
      Route metric is 486400, traffic share count is 43
      Total delay is 9000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
  * 10.20.12.2, from 10.20.12.2, 00:00:20 ago, via Ethernet0/0
      Route metric is 435200, traffic share count is 48
      Total delay is 7000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
```

E3 variance 2 `show ip eigrp topology`:
```
EIGRP-IPv4 Topology Table for AS(100)/ID(11.11.11.11)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 10.20.14.0/24, 1 successors, FD is 281600
        via Connected, Ethernet0/2
P 11.11.11.11/32, 1 successors, FD is 128256
        via Connected, Loopback0
P 33.33.33.33/32, 2 successors, FD is 460800
        via 10.20.13.3 (460800/128256), Ethernet0/1
        via 10.20.12.2 (460800/435200), Ethernet0/0
P 10.20.45.0/24, 2 successors, FD is 332800
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (384000/307200), Ethernet0/1
P 10.20.12.0/24, 1 successors, FD is 281600
        via Connected, Ethernet0/0
P 44.44.44.44/32, 1 successors, FD is 409600
        via 10.20.14.4 (409600/128256), Ethernet0/2
P 55.55.55.55/32, 2 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 22.22.22.22/32, 1 successors, FD is 409600
        via 10.20.12.2 (409600/128256), Ethernet0/0
P 10.20.13.0/24, 1 successors, FD is 332800
        via Connected, Ethernet0/1
P 10.20.25.0/24, 1 successors, FD is 307200
        via 10.20.12.2 (307200/281600), Ethernet0/0
P 10.99.9.0/24, 2 successors, FD is 435200
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (486400/409600), Ethernet0/1
P 10.20.35.0/24, 2 successors, FD is 332800
        via 10.20.13.3 (358400/281600), Ethernet0/1
        via 10.20.12.2 (332800/307200), Ethernet0/0
```
- **判定**: via RE2(FD 435200)+via RE3(FD 486400)の2本のみ・RE4(非FC)は倍率 2 でも乗らない

## e4

E4 RE1 e0/1 delay 2000 `show ip eigrp topology all-links`:
```
EIGRP-IPv4 Topology Table for AS(100)/ID(11.11.11.11)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 10.20.14.0/24, 1 successors, FD is 281600, serno 4
        via Connected, Ethernet0/2
P 11.11.11.11/32, 1 successors, FD is 128256, serno 1
        via Connected, Loopback0
P 33.33.33.33/32, 1 successors, FD is 460800, serno 38
        via 10.20.12.2 (460800/435200), Ethernet0/0
        via 10.20.13.3 (896000/128256), Ethernet0/1
P 10.20.45.0/24, 1 successors, FD is 332800, serno 34
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (819200/307200), Ethernet0/1
        via 10.20.14.4 (384000/358400), Ethernet0/2
P 10.20.12.0/24, 1 successors, FD is 281600, serno 2
        via Connected, Ethernet0/0
P 44.44.44.44/32, 1 successors, FD is 409600, serno 9
        via 10.20.14.4 (409600/128256), Ethernet0/2
P 55.55.55.55/32, 1 successors, FD is 435200, serno 35
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (921600/409600), Ethernet0/1
P 22.22.22.22/32, 1 successors, FD is 409600, serno 5
        via 10.20.12.2 (409600/128256), Ethernet0/0
P 10.20.13.0/24, 1 successors, FD is 768000, serno 39
        via Connected, Ethernet0/1
        via 10.20.14.4 (435200/409600), Ethernet0/2
        via 10.20.12.2 (358400/332800), Ethernet0/0
P 10.20.25.0/24, 1 successors, FD is 307200, serno 6
        via 10.20.12.2 (307200/281600), Ethernet0/0
        via 10.20.13.3 (819200/307200), Ethernet0/1
P 10.99.9.0/24, 1 successors, FD is 435200, serno 36
        via 10.20.12.2 (435200/409600), Ethernet0/0
        via 10.20.13.3 (921600/409600), Ethernet0/1
P 10.20.35.0/24, 1 successors, FD is 332800, serno 37
        via 10.20.12.2 (332800/307200), Ethernet0/0
        via 10.20.13.3 (793600/281600), Ethernet0/1
```

E4 variance 2 `show ip route 10.99.9.0`:
```
Routing entry for 10.99.9.0/24
  Known via "eigrp 100", distance 90, metric 435200, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 10.20.12.2 on Ethernet0/0, 00:00:20 ago
  Routing Descriptor Blocks:
  * 10.20.12.2, from 10.20.12.2, 00:00:20 ago, via Ethernet0/0
      Route metric is 435200, traffic share count is 1
      Total delay is 7000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
```
- **判定**: FS(RD 409600 < 435200)だが FD 921600 > 2×435200 → 乗らない

E4 variance 3 `show ip route 10.99.9.0`:
```
Routing entry for 10.99.9.0/24
  Known via "eigrp 100", distance 90, metric 435200, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 10.20.13.3 on Ethernet0/1, 00:00:20 ago
  Routing Descriptor Blocks:
    10.20.13.3, from 10.20.13.3, 00:00:20 ago, via Ethernet0/1
      Route metric is 921600, traffic share count is 113
      Total delay is 26000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
  * 10.20.12.2, from 10.20.12.2, 00:00:20 ago, via Ethernet0/0
      Route metric is 435200, traffic share count is 240
      Total delay is 7000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
```
- **判定**: 倍率 3 で乗る(921600 <= 3×435200=1305600)
