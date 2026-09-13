# BL-169 PoC 生ログ(ENARSI-MPLS-L3VPN-04・PE-CE eBGP・2026-09-13 07:22)


## 0. 基線(PE 側 eBGP ネイバーを as-override 無しで投入)


### 基線投入 — RT01# conf t: router bgp 65000 / address-family ipv4 vrf CUST_A / neighbor 192.168.1.1 remote-as 65101 / neighbor 192.168.1.1 activate / exit-address-family / address-family ipv4 vrf CUST_B / neighbor 192.168.11.1 remote-as 65200 / neighbor 192.168.11.1 activate / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#router bgp 65000
RT01(config-router)#address-family ipv4 vrf CUST_A
RT01(config-router-af)#neighbor 192.168.1.1 remote-as 65101
RT01(config-router-af)#neighbor 192.168.1.1 activate
RT01(config-router-af)#exit-address-family
RT01(config-router)#address-family ipv4 vrf CUST_B
RT01(config-router-af)#neighbor 192.168.11.1 remote-as 65200
RT01(config-router-af)#neighbor 192.168.11.1 activate
RT01(config-router-af)#exit-address-family
RT01(config-router)#exit
RT01(config)#end
RT01#
```


### 基線投入 — RT03# conf t: router bgp 65000 / address-family ipv4 vrf CUST_A / neighbor 192.168.2.1 remote-as 65102 / neighbor 192.168.2.1 activate / exit-address-family / address-family ipv4 vrf CUST_B / neighbor 192.168.12.1 remote-as 65200 / neighbor 192.168.12.1 activate / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT03(config)#router bgp 65000
RT03(config-router)#address-family ipv4 vrf CUST_A
RT03(config-router-af)#neighbor 192.168.2.1 remote-as 65102
RT03(config-router-af)#neighbor 192.168.2.1 activate
RT03(config-router-af)#exit-address-family
RT03(config-router)#address-family ipv4 vrf CUST_B
RT03(config-router-af)#neighbor 192.168.12.1 remote-as 65200
RT03(config-router-af)#neighbor 192.168.12.1 activate
RT03(config-router-af)#exit-address-family
RT03(config-router)#exit
RT03(config)#end
RT03#
```


## M10a as-override 無し: CUST_A(サイト毎 AS)は届き、CUST_B(同一 AS)は CE が捨てる


### M10a — RT01# show bgp vpnv4 unicast all summary

```
BGP router identifier 1.1.1.1, local AS number 65000
BGP table version is 13, main routing table version 13
8 network entries using 2112 bytes of memory
8 path entries using 1088 bytes of memory
6/4 BGP path/bestpath attribute entries using 1872 bytes of memory
3 BGP AS-PATH entries using 72 bytes of memory
2 BGP extended community entries using 48 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 5192 total bytes of memory
BGP activity 8/0 prefixes, 8/0 paths, scan interval 60 secs
8 networks peaked at 07:23:59 Sep 13 2026 UTC (00:00:04.713 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
3.3.3.3         4        65000       6       6       13    0    0 00:01:54        4
192.168.1.1     4        65101       5       5       13    0    0 00:01:34        2
192.168.11.1    4        65200       5       5       13    0    0 00:01:30        2
```


### M10a — RT01# show bgp vpnv4 unicast vrf CUST_B

```
BGP table version is 13, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:200 (default for vrf CUST_B)
 *>   10.99.6.1/32     192.168.11.1             0             0 65200 i
 *>i  10.99.7.1/32     3.3.3.3                  0    100      0 65200 i
 *>   172.16.1.0/24    192.168.11.1             0             0 65200 i
 *>i  172.16.2.0/24    3.3.3.3                  0    100      0 65200 i
```


### M10a — RT01# show bgp vpnv4 unicast vrf CUST_B neighbors 192.168.11.1 advertised-routes

```
BGP table version is 13, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:200 (default for vrf CUST_B)
 *>i  10.99.7.1/32     3.3.3.3                  0    100      0 65200 i
 *>i  172.16.2.0/24    3.3.3.3                  0    100      0 65200 i

Total number of prefixes 2
```


### M10a (CUST_A CE) — RT04# show ip bgp

```
BGP table version is 5, local router ID is 4.4.4.4
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.99.4.1/32     0.0.0.0                  0         32768 i
 *>   10.99.5.1/32     192.168.1.2                            0 65000 65102 i
 *>   172.16.1.0/24    0.0.0.0                  0         32768 i
 *>   172.16.2.0/24    192.168.1.2                            0 65000 65102 i
```


### M10a (CUST_A CE) — RT04# show ip bgp 172.16.2.0

```
BGP routing table entry for 172.16.2.0/24, version 5
Paths: (1 available, best #1, table default)
  Not advertised to any peer
  Refresh Epoch 1
  65000 65102
    192.168.1.2 from 192.168.1.2 (1.1.1.1)
      Origin IGP, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Sep 13 2026 07:23:49 UTC
```


### M10a (CUST_B CE) — RT06# show ip bgp

```
BGP table version is 3, local router ID is 6.6.6.6
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.99.6.1/32     0.0.0.0                  0         32768 i
 *>   172.16.1.0/24    0.0.0.0                  0         32768 i
```


### M10a (CUST_B CE) — RT06# show ip bgp summary

```
BGP router identifier 6.6.6.6, local AS number 65200
BGP table version is 3, main routing table version 3
2 network entries using 496 bytes of memory
2 path entries using 272 bytes of memory
1/1 BGP path/bestpath attribute entries using 296 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 1064 total bytes of memory
BGP activity 2/0 prefixes, 2/0 paths, scan interval 60 secs
2 networks peaked at 07:21:31 Sep 13 2026 UTC (00:02:48.967 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
192.168.11.2    4        65000       5       5        3    0    0 00:01:46        0
```


### M10a (CUST_B CE) — RT06# show ip route bgp

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
```


### M10a debug on — RT06# debug ip bgp updates in

```
BGP updates debugging is on (inbound) for address family: IPv4 Unicast
```


### M10a 再広告 — RT01# clear bgp vpnv4 unicast vrf CUST_B 192.168.11.1 soft out

```
                             ^
% Invalid input detected at '^' marker.
```


### M10a DENIED 指紋(debug ip bgp updates in) — RT06# (debug 出力)

```

```


## M10b as-override を PE に投入


### M10b 投入 — RT01# conf t: router bgp 65000 / address-family ipv4 vrf CUST_B / neighbor 192.168.11.1 as-override / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#router bgp 65000
RT01(config-router)#address-family ipv4 vrf CUST_B
RT01(config-router-af)#neighbor 192.168.11.1 as-override
RT01(config-router-af)#exit-address-family
RT01(config-router)#exit
RT01(config)#end
RT01#
```


### M10b 投入 — RT03# conf t: router bgp 65000 / address-family ipv4 vrf CUST_B / neighbor 192.168.12.1 as-override / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT03(config)#router bgp 65000
RT03(config-router)#address-family ipv4 vrf CUST_B
RT03(config-router-af)#neighbor 192.168.12.1 as-override
RT03(config-router-af)#exit-address-family
RT03(config-router)#exit
RT03(config)#end
RT03#
```


### M10b (CUST_B CE) — RT06# show ip bgp

```
BGP table version is 5, local router ID is 6.6.6.6
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.99.6.1/32     0.0.0.0                  0         32768 i
 *>   10.99.7.1/32     192.168.11.2                           0 65000 65000 i
 *>   172.16.1.0/24    0.0.0.0                  0         32768 i
 *>   172.16.2.0/24    192.168.11.2                           0 65000 65000 i
```


### M10b (CUST_B CE) — RT06# show ip bgp 172.16.2.0

```
BGP routing table entry for 172.16.2.0/24, version 5
Paths: (1 available, best #1, table default)
  Not advertised to any peer
  Refresh Epoch 1
  65000 65000
    192.168.11.2 from 192.168.11.2 (1.1.1.1)
      Origin IGP, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Sep 13 2026 07:25:13 UTC
```


### M10b (CUST_B CE) — RT06# show ip route bgp

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

      10.0.0.0/32 is subnetted, 2 subnets
B        10.99.7.1 [20/0] via 192.168.11.2, 00:00:27
      172.16.0.0/16 is variably subnetted, 3 subnets, 2 masks
B        172.16.2.0/24 [20/0] via 192.168.11.2, 00:00:27
```


### M10b — RT06# ping 172.16.2.9 source 172.16.1.9 repeat 3

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.2.9, timeout is 2 seconds:
Packet sent with a source address of 172.16.1.9 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 2/2/2 ms
```


### M10b — RT01# show bgp vpnv4 unicast vrf CUST_B neighbors 192.168.11.1 advertised-routes

```
BGP table version is 13, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:200 (default for vrf CUST_B)
 *>i  10.99.7.1/32     3.3.3.3                  0    100      0 65200 i
 *>i  172.16.2.0/24    3.3.3.3                  0    100      0 65200 i

Total number of prefixes 2
```


### M10b — RT01# show running-config | section address-family ipv4 vrf CUST_B

```
 address-family ipv4 vrf CUST_B
  neighbor 192.168.11.1 remote-as 65200
  neighbor 192.168.11.1 activate
  neighbor 192.168.11.1 as-override
```


## M11 as-override を外し、CE 側に allowas-in


### M11 as-override 解除 — RT01# conf t: router bgp 65000 / address-family ipv4 vrf CUST_B / no neighbor 192.168.11.1 as-override / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#router bgp 65000
RT01(config-router)#address-family ipv4 vrf CUST_B
RT01(config-router-af)#no neighbor 192.168.11.1 as-override
RT01(config-router-af)#exit-address-family
RT01(config-router)#exit
RT01(config)#end
RT01#
```


### M11 as-override 解除 — RT03# conf t: router bgp 65000 / address-family ipv4 vrf CUST_B / no neighbor 192.168.12.1 as-override / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT03(config)#router bgp 65000
RT03(config-router)#address-family ipv4 vrf CUST_B
RT03(config-router-af)#no neighbor 192.168.12.1 as-override
RT03(config-router-af)#exit-address-family
RT03(config-router)#exit
RT03(config)#end
RT03#
```


### M11 (解除後・CE) — RT06# show ip bgp

```
BGP table version is 7, local router ID is 6.6.6.6
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.99.6.1/32     0.0.0.0                  0         32768 i
 *>   172.16.1.0/24    0.0.0.0                  0         32768 i
```


### M11 allowas-in 投入(CE1) — RT06# conf t: router bgp 65200 / address-family ipv4 / neighbor 192.168.11.2 allowas-in / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT06(config)#router bgp 65200
RT06(config-router)#address-family ipv4
RT06(config-router-af)#neighbor 192.168.11.2 allowas-in
RT06(config-router-af)#exit-address-family
RT06(config-router)#exit
RT06(config)#end
RT06#
```


### M11 allowas-in 投入(CE2) — RT07# conf t: router bgp 65200 / address-family ipv4 / neighbor 192.168.12.2 allowas-in / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT07(config)#router bgp 65200
RT07(config-router)#address-family ipv4
RT07(config-router-af)#neighbor 192.168.12.2 allowas-in
RT07(config-router-af)#exit-address-family
RT07(config-router)#exit
RT07(config)#end
RT07#
```


### M11 (allowas-in 後・CE) — RT06# show ip bgp

```
BGP table version is 9, local router ID is 6.6.6.6
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.99.6.1/32     0.0.0.0                  0         32768 i
 *>   10.99.7.1/32     192.168.11.2                           0 65000 65200 i
 *>   172.16.1.0/24    0.0.0.0                  0         32768 i
 *>   172.16.2.0/24    192.168.11.2                           0 65000 65200 i
```


### M11 (allowas-in 後・CE) — RT06# show ip bgp 172.16.2.0

```
BGP routing table entry for 172.16.2.0/24, version 9
Paths: (1 available, best #1, table default)
  Not advertised to any peer
  Refresh Epoch 2
  65000 65200
    192.168.11.2 from 192.168.11.2 (1.1.1.1)
      Origin IGP, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Sep 13 2026 07:26:57 UTC
```


### M11 — RT06# ping 172.16.2.9 source 172.16.1.9 repeat 3

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.2.9, timeout is 2 seconds:
Packet sent with a source address of 172.16.1.9 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/2 ms
```


### M11 — RT06# show running-config | section router bgp

```
router bgp 65200
 bgp router-id 6.6.6.6
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 192.168.11.2 remote-as 65000
 !
 address-family ipv4
  network 10.99.6.1 mask 255.255.255.255
  network 172.16.1.0 mask 255.255.255.0
  neighbor 192.168.11.2 activate
  neighbor 192.168.11.2 allowas-in
 exit-address-family
```


### M11 復旧(CE1) — RT06# conf t: router bgp 65200 / address-family ipv4 / no neighbor 192.168.11.2 allowas-in / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT06(config)#router bgp 65200
RT06(config-router)#address-family ipv4
RT06(config-router-af)#no neighbor 192.168.11.2 allowas-in
RT06(config-router-af)#exit-address-family
RT06(config-router)#exit
RT06(config)#end
RT06#
```


### M11 復旧(CE2) — RT07# conf t: router bgp 65200 / address-family ipv4 / no neighbor 192.168.12.2 allowas-in / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT07(config)#router bgp 65200
RT07(config-router)#address-family ipv4
RT07(config-router-af)#no neighbor 192.168.12.2 allowas-in
RT07(config-router-af)#exit-address-family
RT07(config-router)#exit
RT07(config)#end
RT07#
```

## M10c DENIED 指紋の再採取(soft out の正しい構文で再広告)


### RT01# clear ip bgp vrf CUST_B 192.168.11.1 soft out

```
clear ip bgp vrf CUST_B 192.168.11.1 soft out
                                ^
% Invalid input detected at '^' marker.

RT01#
```


### RT01# clear bgp vpnv4 unicast 192.168.11.1 soft out

```
clear bgp vpnv4 unicast 192.168.11.1 soft out
% BGP: Unknown neighbor - "192.168.11.1"
RT01#
```


### RT06 debug ip bgp updates in(受信側の指紋)

```

```


### RT06# show ip bgp summary

```
BGP router identifier 6.6.6.6, local AS number 65200
BGP table version is 11, main routing table version 11
2 network entries using 496 bytes of memory
2 path entries using 272 bytes of memory
1/1 BGP path/bestpath attribute entries using 296 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 1064 total bytes of memory
BGP activity 6/4 prefixes, 6/4 paths, scan interval 60 secs
4 networks peaked at 07:25:13 Sep 13 2026 UTC (00:04:14.262 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
192.168.11.2    4        65000      19      12       11    0    0 00:06:53        0
```
