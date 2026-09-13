# BL-169 PoC 生ログ(ENARSI-MPLS-L3VPN-02・IOL・2026-09-13 07:16)


## 0. 基線(02 解答の投入)


### 基線投入 — RT01# conf t: router ospf 10 vrf CUST_A / network 192.168.1.0 0.0.0.3 area 0 / redistribute bgp 65000 subnets / exit / router ospf 20 vrf CUST_B / network 192.168.11.0 0.0.0.3 area 0 / redistribute bgp 65000 subnets / exit / router bgp 65000 / address-family ipv4 vrf CUST_A / redistribute ospf 10 / redistribute connected / exit-address-family / address-family ipv4 vrf CUST_B / redistribute ospf 20 / redistribute connected / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#router ospf 10 vrf CUST_A
RT01(config-router)#network 192.168.1.0 0.0.0.3 area 0
RT01(config-router)#redistribute bgp 65000 subnets
RT01(config-router)#exit
RT01(config)#router ospf 20 vrf CUST_B
RT01(config-router)#network 192.168.11.0 0.0.0.3 area 0
RT01(config-router)#redistribute bgp 65000 subnets
RT01(config-router)#exit
RT01(config)#router bgp 65000
RT01(config-router)#address-family ipv4 vrf CUST_A
RT01(config-router-af)#redistribute ospf 10
RT01(config-router-af)#redistribute connected
RT01(config-router-af)#exit-address-family
RT01(config-router)#address-family ipv4 vrf CUST_B
RT01(config-router-af)#redistribute ospf 20
RT01(config-router-af)#redistribute connected
RT01(config-router-af)#exit-address-family
RT01(config-router)#exit
RT01(config)#end
RT01#
```


### 基線投入 — RT03# conf t: router ospf 10 vrf CUST_A / network 192.168.2.0 0.0.0.3 area 0 / redistribute bgp 65000 subnets / exit / router ospf 20 vrf CUST_B / network 192.168.12.0 0.0.0.3 area 0 / redistribute bgp 65000 subnets / exit / router bgp 65000 / address-family ipv4 vrf CUST_A / redistribute ospf 10 / redistribute connected / exit-address-family / address-family ipv4 vrf CUST_B / redistribute ospf 20 / redistribute connected / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT03(config)#router ospf 10 vrf CUST_A
RT03(config-router)#network 192.168.2.0 0.0.0.3 area 0
RT03(config-router)#redistribute bgp 65000 subnets
RT03(config-router)#exit
RT03(config)#router ospf 20 vrf CUST_B
RT03(config-router)#network 192.168.12.0 0.0.0.3 area 0
RT03(config-router)#redistribute bgp 65000 subnets
RT03(config-router)#exit
RT03(config)#router bgp 65000
RT03(config-router)#address-family ipv4 vrf CUST_A
RT03(config-router-af)#redistribute ospf 10
RT03(config-router-af)#redistribute connected
RT03(config-router-af)#exit-address-family
RT03(config-router)#address-family ipv4 vrf CUST_B
RT03(config-router-af)#redistribute ospf 20
RT03(config-router-af)#redistribute connected
RT03(config-router-af)#exit-address-family
RT03(config-router)#exit
RT03(config)#end
RT03#
```


### 基線確認 — RT01# show ip route vrf CUST_A

```

Routing Table: CUST_A
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
O        10.99.4.1 [110/11] via 192.168.1.1, 00:02:08, Ethernet0/1
B        10.99.5.1 [200/11] via 3.3.3.3, 00:01:40
      172.16.0.0/24 is subnetted, 2 subnets
O        172.16.1.0 [110/11] via 192.168.1.1, 00:02:08, Ethernet0/1
B        172.16.2.0 [200/11] via 3.3.3.3, 00:01:40
      192.168.1.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.1.0/30 is directly connected, Ethernet0/1
L        192.168.1.2/32 is directly connected, Ethernet0/1
      192.168.2.0/30 is subnetted, 1 subnets
B        192.168.2.0 [200/0] via 3.3.3.3, 00:01:40
```


### 基線確認(CE1→CE2) — RT04# ping 172.16.2.1 source 172.16.1.1 repeat 5

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 172.16.2.1, timeout is 2 seconds:
Packet sent with a source address of 172.16.1.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```


## M1 LFIB / M2 LDP / M3 traceroute / M6 VPNv4・VRF 表


### M1 — RT01# show mpls forwarding-table

```
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop    
Label      Label      or Tunnel Id     Switched      interface              
16         Pop Label  2.2.2.2/32       0             Et0/0      10.1.12.2   
17         Pop Label  10.1.23.0/30     0             Et0/0      10.1.12.2   
18         17         3.3.3.3/32       0             Et0/0      10.1.12.2   
19         No Label   10.99.4.1/32[V]  0             Et0/1      192.168.1.1 
20         No Label   172.16.1.0/24[V] 570           Et0/1      192.168.1.1 
21         No Label   192.168.1.0/30[V]   \
                                       0             aggregate/CUST_A 
22         No Label   10.99.6.1/32[V]  0             Et0/2      192.168.11.1
23         No Label   172.16.1.0/24[V] 0             Et0/2      192.168.11.1
24         No Label   192.168.11.0/30[V]   \
                                       0             aggregate/CUST_B
```


### M1 — RT02# show mpls forwarding-table

```
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop    
Label      Label      or Tunnel Id     Switched      interface              
16         Pop Label  1.1.1.1/32       3176          Et0/0      10.1.12.1   
17         Pop Label  3.3.3.3/32       2776          Et0/1      10.1.23.2
```


### M1 — RT03# show mpls forwarding-table

```
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop    
Label      Label      or Tunnel Id     Switched      interface              
16         Pop Label  2.2.2.2/32       0             Et0/0      10.1.23.1   
17         16         1.1.1.1/32       0             Et0/0      10.1.23.1   
18         Pop Label  10.1.12.0/30     0             Et0/0      10.1.23.1   
19         No Label   10.99.5.1/32[V]  0             Et0/1      192.168.2.1 
20         No Label   172.16.2.0/24[V] 570           Et0/1      192.168.2.1 
21         No Label   192.168.2.0/30[V]   \
                                       0             aggregate/CUST_A 
22         No Label   192.168.12.0/30[V]   \
                                       0             aggregate/CUST_B 
23         No Label   10.99.7.1/32[V]  0             Et0/2      192.168.12.1
24         No Label   172.16.2.0/24[V] 0             Et0/2      192.168.12.1
```


### M2 — RT01# show mpls ldp bindings

```
  lib entry: 1.1.1.1/32, rev 2
	local binding:  label: imp-null
	remote binding: lsr: 2.2.2.2:0, label: 16
  lib entry: 2.2.2.2/32, rev 6
	local binding:  label: 16
	remote binding: lsr: 2.2.2.2:0, label: imp-null
  lib entry: 3.3.3.3/32, rev 10
	local binding:  label: 18
	remote binding: lsr: 2.2.2.2:0, label: 17
  lib entry: 10.1.12.0/30, rev 4
	local binding:  label: imp-null
	remote binding: lsr: 2.2.2.2:0, label: imp-null
  lib entry: 10.1.23.0/30, rev 8
	local binding:  label: 17
	remote binding: lsr: 2.2.2.2:0, label: imp-null
```


### M2 — RT01# show mpls ldp neighbor

```
    Peer LDP Ident: 2.2.2.2:0; Local LDP Ident 1.1.1.1:0
	TCP connection: 2.2.2.2.57597 - 1.1.1.1.646
	State: Oper; Msgs sent/rcvd: 20/20; Downstream
	Up time: 00:10:45
	LDP discovery sources:
	  Ethernet0/0, Src IP addr: 10.1.12.2
        Addresses bound to peer LDP Ident:
          10.1.12.2       2.2.2.2         10.1.23.1
```


### M2 — RT01# show mpls ldp discovery

```
 Local LDP Identifier:
    1.1.1.1:0
    Discovery Sources:
    Interfaces:
	Ethernet0/0 (ldp): xmit/recv
	    LDP Id: 2.2.2.2:0
```


### M2 — RT01# show mpls ldp discovery detail

```
 Local LDP Identifier:
    1.1.1.1:0
    Discovery Sources:
    Interfaces:
	Ethernet0/0 (ldp): xmit/recv
	    Enabled: Interface config
	    Hello interval: 5000 ms; Transport IP addr: 1.1.1.1
	    LDP Id: 2.2.2.2:0
	      Src IP addr: 10.1.12.2; Transport IP addr: 2.2.2.2
	      Hold time: 15 sec; Proposed local/peer: 15/15 sec
	      Reachable via 2.2.2.2/32
	      Password: not required, none, in use
            Clients: IPv4, mLDP
```


### M2 — RT01# show mpls interfaces

```
Interface              IP            Tunnel   BGP Static Operational
Ethernet0/0            Yes (ldp)     No       No  No     Yes
```


### M2 — RT02# show mpls ldp neighbor

```
    Peer LDP Ident: 1.1.1.1:0; Local LDP Ident 2.2.2.2:0
	TCP connection: 1.1.1.1.646 - 2.2.2.2.57597
	State: Oper; Msgs sent/rcvd: 20/21; Downstream
	Up time: 00:10:56
	LDP discovery sources:
	  Ethernet0/0, Src IP addr: 10.1.12.1
        Addresses bound to peer LDP Ident:
          10.1.12.1       1.1.1.1         
    Peer LDP Ident: 3.3.3.3:0; Local LDP Ident 2.2.2.2:0
	TCP connection: 3.3.3.3.22056 - 2.2.2.2.646
	State: Oper; Msgs sent/rcvd: 20/19; Downstream
	Up time: 00:10:51
	LDP discovery sources:
	  Ethernet0/1, Src IP addr: 10.1.23.2
        Addresses bound to peer LDP Ident:
          10.1.23.2       3.3.3.3
```


### M3 — RT01# traceroute vrf CUST_A 172.16.2.1 source 192.168.1.2 numeric timeout 1

```
Type escape sequence to abort.
Tracing the route to 172.16.2.1
VRF info: (vrf in name/id, vrf out name/id)
  1 10.1.12.2 [MPLS: Labels 17/20 Exp 0] 1 msec 1 msec 0 msec
  2 192.168.2.2 [MPLS: Label 20 Exp 0] 1 msec 1 msec 0 msec
  3 192.168.2.1 1 msec *  2 msec
```


### M6 — RT01# show bgp vpnv4 unicast all

```
BGP table version is 19, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:100 (default for vrf CUST_A)
 *>   10.99.4.1/32     192.168.1.1             11         32768 ?
 *>i  10.99.5.1/32     3.3.3.3                 11    100      0 ?
 *>   172.16.1.0/24    192.168.1.1             11         32768 ?
 *>i  172.16.2.0/24    3.3.3.3                 11    100      0 ?
 *>   192.168.1.0/30   0.0.0.0                  0         32768 ?
 *>i  192.168.2.0/30   3.3.3.3                  0    100      0 ?
Route Distinguisher: 65000:200 (default for vrf CUST_B)
 *>   10.99.6.1/32     192.168.11.1            11         32768 ?
 *>i  10.99.7.1/32     3.3.3.3                 11    100      0 ?
 *>   172.16.1.0/24    192.168.11.1            11         32768 ?
 *>i  172.16.2.0/24    3.3.3.3                 11    100      0 ?
 *>   192.168.11.0/30  0.0.0.0                  0         32768 ?
 *>i  192.168.12.0/30  3.3.3.3                  0    100      0 ?
```


### M6 — RT01# show bgp vpnv4 unicast all summary

```
BGP router identifier 1.1.1.1, local AS number 65000
BGP table version is 19, main routing table version 19
12 network entries using 3168 bytes of memory
12 path entries using 1632 bytes of memory
8/8 BGP path/bestpath attribute entries using 2496 bytes of memory
4 BGP extended community entries using 240 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 7536 total bytes of memory
BGP activity 12/0 prefixes, 12/0 paths, scan interval 60 secs
12 networks peaked at 07:17:47 Sep 13 2026 UTC (00:02:24.097 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
3.3.3.3         4        65000      17      18       19    0    0 00:11:03        6
```


### M6 — RT01# show bgp vpnv4 unicast rd 65000:100 172.16.2.0/24

```
BGP routing table entry for 65000:100:172.16.2.0/24, version 12
Paths: (1 available, best #1, table CUST_A)
  Flag: 0x100
  Not advertised to any peer
  Refresh Epoch 1
  Local
    3.3.3.3 (metric 21) (via default) from 3.3.3.3 (3.3.3.3)
      Origin incomplete, metric 11, localpref 100, valid, internal, best
      Extended Community: RT:65000:100 OSPF DOMAIN ID:0x0005:0x0000000A0200 
        OSPF RT:0.0.0.0:2:0 OSPF ROUTER ID:192.168.2.2:0
      mpls labels in/out nolabel/20
      rx pathid: 0, tx pathid: 0x0
      Updated on Sep 13 2026 07:17:43 UTC
```


### M6 — RT01# show ip route vrf CUST_A

```

Routing Table: CUST_A
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
O        10.99.4.1 [110/11] via 192.168.1.1, 00:03:01, Ethernet0/1
B        10.99.5.1 [200/11] via 3.3.3.3, 00:02:33
      172.16.0.0/24 is subnetted, 2 subnets
O        172.16.1.0 [110/11] via 192.168.1.1, 00:03:01, Ethernet0/1
B        172.16.2.0 [200/11] via 3.3.3.3, 00:02:33
      192.168.1.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.1.0/30 is directly connected, Ethernet0/1
L        192.168.1.2/32 is directly connected, Ethernet0/1
      192.168.2.0/30 is subnetted, 1 subnets
B        192.168.2.0 [200/0] via 3.3.3.3, 00:02:33
```


### M6 — RT01# show ip route vrf CUST_B

```

Routing Table: CUST_B
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
O        10.99.6.1 [110/11] via 192.168.11.1, 00:02:58, Ethernet0/2
B        10.99.7.1 [200/11] via 3.3.3.3, 00:02:32
      172.16.0.0/24 is subnetted, 2 subnets
O        172.16.1.0 [110/11] via 192.168.11.1, 00:02:58, Ethernet0/2
B        172.16.2.0 [200/11] via 3.3.3.3, 00:02:32
      192.168.11.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.11.0/30 is directly connected, Ethernet0/2
L        192.168.11.2/32 is directly connected, Ethernet0/2
      192.168.12.0/30 is subnetted, 1 subnets
B        192.168.12.0 [200/0] via 3.3.3.3, 00:02:32
```


### M6 — RT01# show vrf

```
  Name                             Default RD            Protocols   Interfaces
  CUST_A                           65000:100             ipv4        Et0/1
  CUST_B                           65000:200             ipv4        Et0/2
  MGMT                             65001:1               ipv4        Et0/3
```


### M6 — RT01# show vrf detail CUST_A

```
VRF CUST_A (VRF Id = 2); default RD 65000:100; default VPNID <not set>
  New CLI format, supports multiple address-families
  Flags: 0x180C
  Interfaces:
    Et0/1                   
Address family ipv4 unicast (Table ID = 0x2):
  Flags: 0x0
  Export VPN route-target communities
    RT:65000:100            
  Import VPN route-target communities
    RT:65000:100            
  No import route-map
  No global export route-map
  No export route-map
  VRF label distribution protocol: not configured
  VRF label allocation mode: per-prefix
Address family ipv6 unicast not active
Address family ipv4 multicast not active
Address family ipv6 multicast not active
```


### M6 — RT01# show running-config | section vrf definition

```
vrf definition CUST_A
 rd 65000:100
 !
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:100
 exit-address-family
vrf definition CUST_B
 rd 65000:200
 !
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
vrf definition MGMT
 rd 65001:1
 !
 address-family ipv4
 exit-address-family
```


### M6 — RT01# show running-config | section router bgp

```
router bgp 65000
 bgp router-id 1.1.1.1
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 3.3.3.3 remote-as 65000
 neighbor 3.3.3.3 update-source Loopback0
 !
 address-family ipv4
 exit-address-family
 !
 address-family vpnv4
  neighbor 3.3.3.3 activate
  neighbor 3.3.3.3 send-community extended
 exit-address-family
 !
 address-family ipv4 vrf CUST_A
  redistribute connected
  redistribute ospf 10
 exit-address-family
 !
 address-family ipv4 vrf CUST_B
  redistribute connected
  redistribute ospf 20
 exit-address-family
```


### M6 — RT03# show bgp vpnv4 unicast all

```
BGP table version is 19, local router ID is 3.3.3.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:100 (default for vrf CUST_A)
 *>i  10.99.4.1/32     1.1.1.1                 11    100      0 ?
 *>   10.99.5.1/32     192.168.2.1             11         32768 ?
 *>i  172.16.1.0/24    1.1.1.1                 11    100      0 ?
 *>   172.16.2.0/24    192.168.2.1             11         32768 ?
 *>i  192.168.1.0/30   1.1.1.1                  0    100      0 ?
 *>   192.168.2.0/30   0.0.0.0                  0         32768 ?
Route Distinguisher: 65000:200 (default for vrf CUST_B)
 *>i  10.99.6.1/32     1.1.1.1                 11    100      0 ?
 *>   10.99.7.1/32     192.168.12.1            11         32768 ?
 *>i  172.16.1.0/24    1.1.1.1                 11    100      0 ?
 *>   172.16.2.0/24    192.168.12.1            11         32768 ?
 *>i  192.168.11.0/30  1.1.1.1                  0    100      0 ?
 *>   192.168.12.0/30  0.0.0.0                  0         32768 ?
```


## M4 LSP の穴(RT02 Et0/1 no mpls ip)


### M4 投入 — RT02# conf t: interface Ethernet0/1 / no mpls ip

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT02(config)#interface Ethernet0/1
RT02(config-if)#no mpls ip
RT02(config-if)#end
RT02#
```


### M4 — RT01# show mpls forwarding-table

```
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop    
Label      Label      or Tunnel Id     Switched      interface              
16         Pop Label  2.2.2.2/32       0             Et0/0      10.1.12.2   
17         Pop Label  10.1.23.0/30     0             Et0/0      10.1.12.2   
18         17         3.3.3.3/32       0             Et0/0      10.1.12.2   
19         No Label   10.99.4.1/32[V]  0             Et0/1      192.168.1.1 
20         No Label   172.16.1.0/24[V] 570           Et0/1      192.168.1.1 
21         No Label   192.168.1.0/30[V]   \
                                       1244          aggregate/CUST_A 
22         No Label   10.99.6.1/32[V]  0             Et0/2      192.168.11.1
23         No Label   172.16.1.0/24[V] 0             Et0/2      192.168.11.1
24         No Label   192.168.11.0/30[V]   \
                                       0             aggregate/CUST_B
```


### M4 — RT01# show mpls ldp neighbor

```
    Peer LDP Ident: 2.2.2.2:0; Local LDP Ident 1.1.1.1:0
	TCP connection: 2.2.2.2.57597 - 1.1.1.1.646
	State: Oper; Msgs sent/rcvd: 22/22; Downstream
	Up time: 00:12:18
	LDP discovery sources:
	  Ethernet0/0, Src IP addr: 10.1.12.2
        Addresses bound to peer LDP Ident:
          10.1.12.2       2.2.2.2         10.1.23.1
```


### M4 — RT01# show ip route vrf CUST_A | include 172.16.2

```
B        172.16.2.0 [200/11] via 3.3.3.3, 00:03:37
```


### M4 — RT01# ping vrf CUST_A 172.16.2.1 source 192.168.1.2 repeat 3

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.2 
...
Success rate is 0 percent (0/3)
```


### M4 — RT01# show ip route 3.3.3.3

```
Routing entry for 3.3.3.3/32
  Known via "ospf 1", distance 110, metric 21, type intra area
  Last update from 10.1.12.2 on Ethernet0/0, 00:12:25 ago
  Routing Descriptor Blocks:
  * 10.1.12.2, from 3.3.3.3, 00:12:25 ago, via Ethernet0/0
      Route metric is 21, traffic share count is 1
```


### M4 — RT02# show mpls ldp neighbor

```
    Peer LDP Ident: 1.1.1.1:0; Local LDP Ident 2.2.2.2:0
	TCP connection: 1.1.1.1.646 - 2.2.2.2.57597
	State: Oper; Msgs sent/rcvd: 22/23; Downstream
	Up time: 00:12:34
	LDP discovery sources:
	  Ethernet0/0, Src IP addr: 10.1.12.1
        Addresses bound to peer LDP Ident:
          10.1.12.1       1.1.1.1
```


### M4 — RT02# show mpls forwarding-table

```
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop    
Label      Label      or Tunnel Id     Switched      interface              
16         Pop Label  1.1.1.1/32       4579          Et0/0      10.1.12.1   
17         No Label   3.3.3.3/32       2494          Et0/1      10.1.23.2
```


### M4 — RT02# show mpls interfaces

```
Interface              IP            Tunnel   BGP Static Operational
Ethernet0/0            Yes (ldp)     No       No  No     Yes
```


### M4 — RT03# show mpls ldp neighbor

```
show mpls ldp neighbor
RT03#
```


### M4 復旧 — RT02# conf t: interface Ethernet0/1 / mpls ip

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT02(config)#interface Ethernet0/1
RT02(config-if)#mpls ip
RT02(config-if)#end
RT02#
```


### M4 復旧確認 — RT01# ping vrf CUST_A 172.16.2.1 source 192.168.1.2 repeat 3

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.2 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms
```


## M5 LDP router-id を未広告の Loopback9 に(transport address 不達)


### M5 投入 — RT01# conf t: interface Loopback9 / ip address 10.99.1.1 255.255.255.255 / exit / mpls ldp router-id Loopback9 force

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#interface Loopback9
RT01(config-if)#ip address 10.99.1.1 255.255.255.255
RT01(config-if)#exit
RT01(config)#mpls ldp router-id Loopback9 force
RT01(config)#end
RT01#
```


### M5 — RT01# show mpls ldp neighbor

```
show mpls ldp neighbor
RT01#
```


### M5 — RT01# show mpls ldp discovery

```
 Local LDP Identifier:
    10.99.1.1:0
    Discovery Sources:
    Interfaces:
	Ethernet0/0 (ldp): xmit/recv
	    LDP Id: 2.2.2.2:0
```


### M5 — RT01# show mpls ldp discovery detail

```
 Local LDP Identifier:
    10.99.1.1:0
    Discovery Sources:
    Interfaces:
	Ethernet0/0 (ldp): xmit/recv
	    Enabled: Interface config
	    Hello interval: 5000 ms; Transport IP addr: 10.99.1.1
	    LDP Id: 2.2.2.2:0
	      Src IP addr: 10.1.12.2; Transport IP addr: 2.2.2.2
	      Hold time: 15 sec; Proposed local/peer: 15/15 sec
	      Reachable via 2.2.2.2/32
	      Password: not required, none, in use
            Clients: IPv4, mLDP
```


### M5 — RT02# show mpls ldp neighbor

```
    Peer LDP Ident: 3.3.3.3:0; Local LDP Ident 2.2.2.2:0
	TCP connection: 3.3.3.3.15186 - 2.2.2.2.646
	State: Oper; Msgs sent/rcvd: 10/10; Downstream
	Up time: 00:01:45
	LDP discovery sources:
	  Ethernet0/1, Src IP addr: 10.1.23.2
        Addresses bound to peer LDP Ident:
          10.1.23.2       3.3.3.3
```


### M5 — RT02# show mpls ldp discovery detail

```
 Local LDP Identifier:
    2.2.2.2:0
    Discovery Sources:
    Interfaces:
	Ethernet0/0 (ldp): xmit/recv
	    Enabled: Interface config
	    Hello interval: 5000 ms; Transport IP addr: 2.2.2.2
	    LDP Id: 10.99.1.1:0; no route to transport addr
	      Src IP addr: 10.1.12.1; Transport IP addr: 10.99.1.1
	      Hold time: 15 sec; Proposed local/peer: 15/15 sec
	      Password: not required, none, in use
            Clients: IPv4, mLDP 
	Ethernet0/1 (ldp): xmit/recv
	    Enabled: Interface config
	    Hello interval: 5000 ms; Transport IP addr: 2.2.2.2
	    LDP Id: 3.3.3.3:0
	      Src IP addr: 10.1.23.2; Transport IP addr: 3.3.3.3
	      Hold time: 15 sec; Proposed local/peer: 15/15 sec
	      Reachable via 3.3.3.3/32
	      Password: not required, none, in use
            Clients: IPv4, mLDP
```


### M5 — RT01# ping vrf CUST_A 172.16.2.1 source 192.168.1.2 repeat 3

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.2 
...
Success rate is 0 percent (0/3)
```


### M5 復旧 — RT01# conf t: mpls ldp router-id Loopback0 force / no interface Loopback9

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#mpls ldp router-id Loopback0 force
RT01(config)#no interface Loopback9
RT01(config)#end
RT01#
```


### M5 復旧確認 — RT01# show mpls ldp neighbor | include Peer|TCP

```
    Peer LDP Ident: 2.2.2.2:0; Local LDP Ident 1.1.1.1:0
	TCP connection: 2.2.2.2.14098 - 1.1.1.1.646
```


## M7 RT import 取り違え(RT03 CUST_A import 65000:100→65000:555)


### M7 投入 — RT03# conf t: vrf definition CUST_A / address-family ipv4 / no route-target import 65000:100 / route-target import 65000:555 / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT03(config)#vrf definition CUST_A
RT03(config-vrf)#address-family ipv4
RT03(config-vrf-af)#no route-target import 65000:100
RT03(config-vrf-af)#route-target import 65000:555
RT03(config-vrf-af)#exit-address-family
RT03(config-vrf)#exit
RT03(config)#end
RT03#
```


### M7 — RT03# show ip route vrf CUST_A

```

Routing Table: CUST_A
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

      10.0.0.0/32 is subnetted, 1 subnets
O        10.99.5.1 [110/11] via 192.168.2.1, 00:08:24, Ethernet0/1
      172.16.0.0/24 is subnetted, 1 subnets
O        172.16.2.0 [110/11] via 192.168.2.1, 00:08:24, Ethernet0/1
      192.168.2.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.2.0/30 is directly connected, Ethernet0/1
L        192.168.2.2/32 is directly connected, Ethernet0/1
```


### M7 — RT03# show bgp vpnv4 unicast all

```
BGP table version is 22, local router ID is 3.3.3.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:100 (default for vrf CUST_A)
 *>   10.99.5.1/32     192.168.2.1             11         32768 ?
 *>   172.16.2.0/24    192.168.2.1             11         32768 ?
 *>   192.168.2.0/30   0.0.0.0                  0         32768 ?
Route Distinguisher: 65000:200 (default for vrf CUST_B)
 *>i  10.99.6.1/32     1.1.1.1                 11    100      0 ?
 *>   10.99.7.1/32     192.168.12.1            11         32768 ?
 *>i  172.16.1.0/24    1.1.1.1                 11    100      0 ?
 *>   172.16.2.0/24    192.168.12.1            11         32768 ?
 *>i  192.168.11.0/30  1.1.1.1                  0    100      0 ?
 *>   192.168.12.0/30  0.0.0.0                  0         32768 ?
```


### M7 — RT03# show bgp vpnv4 unicast vrf CUST_A

```
BGP table version is 22, local router ID is 3.3.3.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:100 (default for vrf CUST_A)
 *>   10.99.5.1/32     192.168.2.1             11         32768 ?
 *>   172.16.2.0/24    192.168.2.1             11         32768 ?
 *>   192.168.2.0/30   0.0.0.0                  0         32768 ?
```


### M7 — RT03# show bgp vpnv4 unicast all summary

```
BGP router identifier 3.3.3.3, local AS number 65000
BGP table version is 22, main routing table version 22
9 network entries using 2376 bytes of memory
9 path entries using 1224 bytes of memory
6/6 BGP path/bestpath attribute entries using 1872 bytes of memory
3 BGP extended community entries using 180 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 5652 total bytes of memory
BGP activity 12/3 prefixes, 12/3 paths, scan interval 60 secs
12 networks peaked at 07:17:47 Sep 13 2026 UTC (00:08:22.489 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65000      42      25       22    0    0 00:17:01        3
```


### M7 (PE1 側は不変か) — RT01# show ip route vrf CUST_A | include 172.16.2

```
B        172.16.2.0 [200/11] via 3.3.3.3, 00:08:29
```


### M7 (PE1 側) — RT01# show bgp vpnv4 unicast all

```
BGP table version is 19, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:100 (default for vrf CUST_A)
 *>   10.99.4.1/32     192.168.1.1             11         32768 ?
 *>i  10.99.5.1/32     3.3.3.3                 11    100      0 ?
 *>   172.16.1.0/24    192.168.1.1             11         32768 ?
 *>i  172.16.2.0/24    3.3.3.3                 11    100      0 ?
 *>   192.168.1.0/30   0.0.0.0                  0         32768 ?
 *>i  192.168.2.0/30   3.3.3.3                  0    100      0 ?
Route Distinguisher: 65000:200 (default for vrf CUST_B)
 *>   10.99.6.1/32     192.168.11.1            11         32768 ?
 *>i  10.99.7.1/32     3.3.3.3                 11    100      0 ?
 *>   172.16.1.0/24    192.168.11.1            11         32768 ?
 *>i  172.16.2.0/24    3.3.3.3                 11    100      0 ?
 *>   192.168.11.0/30  0.0.0.0                  0         32768 ?
 *>i  192.168.12.0/30  3.3.3.3                  0    100      0 ?
```


### M7 復旧 — RT03# conf t: vrf definition CUST_A / address-family ipv4 / no route-target import 65000:555 / route-target import 65000:100 / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT03(config)#vrf definition CUST_A
RT03(config-vrf)#address-family ipv4
RT03(config-vrf-af)#no route-target import 65000:555
RT03(config-vrf-af)#route-target import 65000:100
RT03(config-vrf-af)#exit-address-family
RT03(config-vrf)#exit
RT03(config)#end
RT03#
```


### M7 復旧確認 — RT03# show ip route vrf CUST_A | include 172.16.1

```
B        172.16.1.0 [200/11] via 1.1.1.1, 00:01:14
```


## M8 同一 PE で CUST_B の RD を CUST_A と同じ 65000:100 に


### M8 投入(応答) — RT01# conf t: vrf definition CUST_B / rd 65000:100 / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#vrf definition CUST_B
RT01(config-vrf)#rd 65000:100
% RD 65000:100 already in use by VRF CUST_A
RT01(config-vrf)#exit
RT01(config)#end
RT01#
```


### M8 — RT01# show vrf

```
  Name                             Default RD            Protocols   Interfaces
  CUST_A                           65000:100             ipv4        Et0/1
  CUST_B                           65000:200             ipv4        Et0/2
  MGMT                             65001:1               ipv4        Et0/3
```


### M8 — RT01# show ip interface brief | include Ethernet0/2

```
Ethernet0/2            192.168.11.2    YES TFTP   up                    up
```


### M8 — RT01# show running-config | section vrf definition CUST_B

```
vrf definition CUST_B
 rd 65000:200
 !
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
```


### M8 復旧(応答) — RT01# conf t: vrf definition CUST_B / rd 65000:200 / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#vrf definition CUST_B
RT01(config-vrf)#rd 65000:200
RT01(config-vrf)#exit
RT01(config)#end
RT01#
```


### M8 復旧確認 — RT01# show ip interface brief | include Ethernet0/2

```
Ethernet0/2            192.168.11.2    YES TFTP   up                    up
```


## M9a vpnv4 ネイバーの send-community extended を外す(PE1)


### M9a 投入 — RT01# conf t: router bgp 65000 / address-family vpnv4 / no neighbor 3.3.3.3 send-community extended / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#router bgp 65000
RT01(config-router)#address-family vpnv4
RT01(config-router-af)#no neighbor 3.3.3.3 send-community extended
RT01(config-router-af)#exit-address-family
RT01(config-router)#exit
RT01(config)#end
RT01#
```


### M9a — RT01# show running-config | section address-family vpnv4

```
 address-family vpnv4
  neighbor 3.3.3.3 activate
```


### M9a — RT03# show bgp vpnv4 unicast all summary

```
BGP router identifier 3.3.3.3, local AS number 65000
BGP table version is 34, main routing table version 34
6 network entries using 1584 bytes of memory
6 path entries using 816 bytes of memory
4/4 BGP path/bestpath attribute entries using 1248 bytes of memory
2 BGP extended community entries using 120 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 3768 total bytes of memory
BGP activity 15/9 prefixes, 15/9 paths, scan interval 60 secs
12 networks peaked at 07:17:47 Sep 13 2026 UTC (00:11:51.531 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65000      70      30       34    0    0 00:20:30        0
```


### M9a — RT03# show ip route vrf CUST_A

```

Routing Table: CUST_A
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

      10.0.0.0/32 is subnetted, 1 subnets
O        10.99.5.1 [110/11] via 192.168.2.1, 00:12:04, Ethernet0/1
      172.16.0.0/24 is subnetted, 1 subnets
O        172.16.2.0 [110/11] via 192.168.2.1, 00:12:04, Ethernet0/1
      192.168.2.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.2.0/30 is directly connected, Ethernet0/1
L        192.168.2.2/32 is directly connected, Ethernet0/1
```


### M9a — RT03# show bgp vpnv4 unicast all

```
BGP table version is 34, local router ID is 3.3.3.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 65000:100 (default for vrf CUST_A)
 *>   10.99.5.1/32     192.168.2.1             11         32768 ?
 *>   172.16.2.0/24    192.168.2.1             11         32768 ?
 *>   192.168.2.0/30   0.0.0.0                  0         32768 ?
Route Distinguisher: 65000:200 (default for vrf CUST_B)
 *>   10.99.7.1/32     192.168.12.1            11         32768 ?
 *>   172.16.2.0/24    192.168.12.1            11         32768 ?
 *>   192.168.12.0/30  0.0.0.0                  0         32768 ?
```


### M9a 復旧 — RT01# conf t: router bgp 65000 / address-family vpnv4 / neighbor 3.3.3.3 send-community extended / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#router bgp 65000
RT01(config-router)#address-family vpnv4
RT01(config-router-af)#neighbor 3.3.3.3 send-community extended
RT01(config-router-af)#exit-address-family
RT01(config-router)#exit
RT01(config)#end
RT01#
```


### M9a 復旧確認 — RT03# show ip route vrf CUST_A | include 172.16.1

```
B        172.16.1.0 [200/11] via 1.1.1.1, 00:01:12
```


## M9b vpnv4 ネイバーの activate を外す(PE1)


### M9b 投入 — RT01# conf t: router bgp 65000 / address-family vpnv4 / no neighbor 3.3.3.3 activate / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#router bgp 65000
RT01(config-router)#address-family vpnv4
RT01(config-router-af)#no neighbor 3.3.3.3 activate
RT01(config-router-af)#exit-address-family
RT01(config-router)#exit
RT01(config)#end
RT01#
```


### M9b — RT01# show running-config | section address-family vpnv4

```
 address-family vpnv4
```


### M9b — RT01# show bgp vpnv4 unicast all summary

```
show bgp vpnv4 unicast all summary
RT01#
```


### M9b — RT03# show bgp vpnv4 unicast all summary

```
BGP router identifier 3.3.3.3, local AS number 65000
BGP table version is 52, main routing table version 52
6 network entries using 1584 bytes of memory
6 path entries using 816 bytes of memory
8/4 BGP path/bestpath attribute entries using 2496 bytes of memory
4 BGP extended community entries using 240 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 5136 total bytes of memory
BGP activity 21/9 prefixes, 21/15 paths, scan interval 60 secs
12 networks peaked at 07:17:47 Sep 13 2026 UTC (00:13:57.747 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65000       0       0        1    0    0 00:00:35 Idle
```


### M9b — RT03# show ip route vrf CUST_A

```

Routing Table: CUST_A
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

      10.0.0.0/32 is subnetted, 1 subnets
O        10.99.5.1 [110/11] via 192.168.2.1, 00:14:10, Ethernet0/1
      172.16.0.0/24 is subnetted, 1 subnets
O        172.16.2.0 [110/11] via 192.168.2.1, 00:14:10, Ethernet0/1
      192.168.2.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.2.0/30 is directly connected, Ethernet0/1
L        192.168.2.2/32 is directly connected, Ethernet0/1
```


### M9b 復旧 — RT01# conf t: router bgp 65000 / address-family vpnv4 / neighbor 3.3.3.3 activate / neighbor 3.3.3.3 send-community extended / exit-address-family / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT01(config)#router bgp 65000
RT01(config-router)#address-family vpnv4
RT01(config-router-af)#neighbor 3.3.3.3 activate
RT01(config-router-af)#neighbor 3.3.3.3 send-community extended
RT01(config-router-af)#exit-address-family
RT01(config-router)#exit
RT01(config)#end
RT01#
```


### M9b 復旧確認 — RT01# show running-config | section address-family vpnv4

```
 address-family vpnv4
  neighbor 3.3.3.3 activate
  neighbor 3.3.3.3 send-community extended
```


### M9b 復旧確認 — RT03# show ip route vrf CUST_A | include 172.16.1

```
B        172.16.1.0 [200/11] via 1.1.1.1, 00:01:15
```


## M14 mpls ldp autoconfig(OSPF で受理・EIGRP で不可)


### M14 OSPF — RT02# conf t: router ospf 1 / mpls ldp autoconfig / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT02(config)#router ospf 1
RT02(config-router)#mpls ldp autoconfig
RT02(config-router)#exit
RT02(config)#end
RT02#
```


### M14 — RT02# show mpls interfaces

```
Interface              IP            Tunnel   BGP Static Operational
Ethernet0/0            Yes (ldp)     No       No  No     Yes        
Ethernet0/1            Yes (ldp)     No       No  No     Yes
```


### M14 — RT02# show running-config | section router ospf

```
router ospf 1
 router-id 2.2.2.2
 network 2.2.2.2 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
 network 10.1.23.0 0.0.0.3 area 0
 mpls ldp autoconfig
```


### M14 OSPF 復旧 — RT02# conf t: router ospf 1 / no mpls ldp autoconfig / exit

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT02(config)#router ospf 1
RT02(config-router)#no mpls ldp autoconfig
RT02(config-router)#exit
RT02(config)#end
RT02#
```


### M14 EIGRP(応答) — RT02# conf t: router eigrp 99 / mpls ldp autoconfig / exit / no router eigrp 99

```
configure terminal
Enter configuration commands, one per line.  End with CNTL/Z.
RT02(config)#router eigrp 99
RT02(config-router)#mpls ldp autoconfig
                     ^
% Invalid input detected at '^' marker.

RT02(config-router)#exit
RT02(config)#no router eigrp 99
RT02(config)#end
RT02#
```


## 最終基線確認


### 最終 — RT04# ping 172.16.2.1 source 172.16.1.1 repeat 5

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 172.16.2.1, timeout is 2 seconds:
Packet sent with a source address of 172.16.1.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/4 ms
```


### 最終 — RT01# show mpls ldp neighbor | include Peer

```
    Peer LDP Ident: 2.2.2.2:0; Local LDP Ident 1.1.1.1:0
```


(所要 1031 秒)
