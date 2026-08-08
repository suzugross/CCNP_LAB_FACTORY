
## sweep run (2026-08-07 13:03:58) IF=Ethernet0/0


### BASE

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP01
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:05, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:05, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:05, Ethernet0/0
```

### S0_no_leakmap

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 153 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/30 is subnetted, 1 subnets
D        1.1.1.0 [90/409600] via 172.16.17.1, 00:00:05, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:05, Ethernet0/0
```

### E1_rmap_undefined

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 173 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP_GHOST
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/30 is subnetted, 1 subnets
D        1.1.1.0 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### E2_pl_undefined

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP02
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.1/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.2/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### E3_permit_no_match

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP03
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.1/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.2/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### E4_pl_matches_nothing

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP04
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/30 is subnetted, 1 subnets
D        1.1.1.0 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### E5_external_component

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP01
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D EX     1.1.1.3/32 [170/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### E6_acl_match

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 171 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP_ACL
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### E7_single_component

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP01
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### FINAL_BASELINE_CHECK

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP01
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:07, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:07, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:07, Ethernet0/0
```

## sweep run (2026-08-07 13:12:46) IF=Ethernet0/0


### V1_null0_redist

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 98 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 256
  Descriptor Blocks:
  0.0.0.0, from Rstatic, Send flag is 0x0
      Composite metric is (256/0), route is External
      Vector metric:
        Minimum bandwidth is 10000000 Kbit
        Total delay is 0 microseconds
        Reliability is 0/255
        Load is 0/255
        Minimum MTU is 1500
        Hop count is 0
        Originating router is 10.10.10.10
      External data:
        AS number of route is 0
        External protocol is Static, external metric is 0
        Administrator tag is 0 (0x00000000)
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D EX     1.1.1.0/30 [170/281600] via 172.16.17.1, 00:00:05, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:05, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:05, Ethernet0/0
```

### V2_null0_no_suppress

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 98 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 256
  Descriptor Blocks:
  0.0.0.0, from Rstatic, Send flag is 0x0
      Composite metric is (256/0), route is External
      Vector metric:
        Minimum bandwidth is 10000000 Kbit
        Total delay is 0 microseconds
        Reliability is 0/255
        Load is 0/255
        Minimum MTU is 1500
        Hop count is 0
        Originating router is 10.10.10.10
      External data:
        AS number of route is 0
        External protocol is Static, external metric is 0
        Administrator tag is 0 (0x00000000)
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
D EX     1.1.1.0/30 [170/281600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.1/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.2/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### V3_all_external

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP01
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D EX     1.1.1.3/32 [170/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### FINAL_BASELINE_CHECK

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP01
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:07, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:07, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:07, Ethernet0/0
```

## sweep run (2026-08-07 23:33:57) IF=Ethernet0/0


### V4_eco_shared

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RM_ECO
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D EX     1.1.1.3/32 [170/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### V5_eco_edit_side_effect

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RM_ECO
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D EX     1.1.1.2/32 [170/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```

### FINAL_BASELINE_CHECK

RT01 `show run interface Ethernet0/0`:
```
Building configuration...

Current configuration : 169 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 172.16.17.1 255.255.255.252
 ip summary-address eigrp 6571 1.1.1.0 255.255.255.252 leak-map RMAP01
end

```
RT01 `show ip eigrp topology 1.1.1.0/30`:
```
EIGRP-IPv4 Topology Entry for AS(6571)/ID(10.10.10.10) for 1.1.1.0/30
  State is Passive, Query origin flag is 1, 1 Successor(s), FD is 128256
  Descriptor Blocks:
  0.0.0.0 (Null0), from 0.0.0.0, Send flag is 0x0
      Composite metric is (128256/0), route is Internal
      Vector metric:
        Minimum bandwidth is 8000000 Kbit
        Total delay is 5000 microseconds
        Reliability is 255/255
        Load is 1/255
        Minimum MTU is 1514
        Hop count is 0
        Originating router is 10.10.10.10
```
RT02 `show ip route eigrp`:
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

      1.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
D        1.1.1.0/30 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
D        1.1.1.3/32 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
      10.0.0.0/32 is subnetted, 1 subnets
D        10.10.10.10 [90/409600] via 172.16.17.1, 00:00:06, Ethernet0/0
```
