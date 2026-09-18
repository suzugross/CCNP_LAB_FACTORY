
## P8 source/prefix/destination guard(ioll2-xe 17.15.1)  (2026-09-18 15:46)

**P8-0 SWB RA guard + device-tracking**

```
ipv6 nd raguard policy HOST
device-role host
exit
ipv6 nd raguard policy ROUTER
device-role router
exit
device-tracking policy TRACK
exit
vlan configuration 10
device-tracking attach-policy TRACK
exit
interface Ethernet0/0
ipv6 nd raguard attach-policy ROUTER
exit
interface Ethernet0/1
ipv6 nd raguard attach-policy HOST
exit
interface Ethernet0/2
ipv6 nd raguard attach-policy HOST
exit
---
(応答なし)
```

**P8-0 RT02 受信カウンタ ACL**

```
ipv6 access-list CNT
sequence 10 permit icmp 2001:DB8:98::/64 any
sequence 20 permit icmp 2001:DB8:99::/64 any
sequence 30 permit icmp 2001:DB8:33:B::/64 any
sequence 40 permit icmp any any
sequence 50 permit ipv6 any any
exit
interface Ethernet0/0
ipv6 traffic-filter CNT in
exit
---
(応答なし)
```

**P8-0 CLB show ipv6 interface brief (GUA after 15.639678716659546s)**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:6500
    2001:DB8:33:B:A8BB:CCFF:FE01:6500
```

**P8-0 CLB show ipv6 routers**

```
Router FE80::A8BB:CCFF:FE01:6400 on Ethernet0/0, last update 0 min
  Hops 64, Lifetime 1800 sec, AddrFlag=0, OtherFlag=1, MTU=1500
  HomeAgentFlag=0, Preference=Medium
  Reachable time 0 (unspecified), Retransmit time 0 (unspecified)
  Prefix 2001:DB8:33:B::/64 onlink autoconfig
    Valid lifetime 2592000, preferred lifetime 604800
```

**P8-0 CLB 範囲外アドレス追加(Et0/0=98::1 / Lo0=99::1)**

```
interface Loopback0
ipv6 address 2001:DB8:99::1/64
exit
interface Ethernet0/0
ipv6 address 2001:DB8:98::1/64
exit
---
(応答なし)
```

**P8-0 SWB show device-tracking database**

```
 VPC role NONE VPC state CREATING
Binding Table has 7 entries, 7 dynamic (limit 200000)
Codes: L - Local, S - Static, ND - Neighbor Discovery, ARP - Address Resolution Protocol, DH4 - IPv4 DHCP, DH6 - IPv6 DHCP, PKT - Other Packet, API - API created
Preflevel flags (prlvl):
0001:MAC and LLA match     0002:Orig trunk            0004:Orig access           
0008:Orig trusted trunk    0010:Orig trusted access   0020:DHCP assigned         
0040:Cga authenticated     0080:Cert authenticated    0100:Statically assigned   


    Network Layer Address                    Link Layer Address     Interface  vlan/bd    prlvl      age        state      Time left       
ND  FE80::A8BB:CCFF:FE01:6600                aabb.cc01.6600         Et0/2      10         0005       22s        REACHABLE  280 s           
ND  FE80::A8BB:CCFF:FE01:6500                aabb.cc01.6500         Et0/1      10         0005       22s        REACHABLE  292 s           
ND  FE80::A8BB:CCFF:FE01:6400                aabb.cc01.6400         Et0/0      10         0005       12s        REACHABLE  291 s           
ND  2001:DB8:98::1                           aabb.cc01.6500         Et0/1      10         0005       14s        REACHABLE  285 s           
ND  2001:DB8:33:BAD::1                       aabb.cc01.6600         Et0/2      10         0005       36s        REACHABLE  264 s           
ND  2001:DB8:33:B:A8BB:CCFF:FE01:6500        aabb.cc01.6500         Et0/1      10         0005       27s        REACHABLE  283 s           
ND  2001:DB8:33:B::1                         aabb.cc01.6400         Et0/0      10         0005       38s        REACHABLE  269 s
```

**P8-0 SWB show device-tracking database details**

```
   TID   Vlan    MAC             Interface
   D06853  10      aabb.cc01.6500  Et0/1
 VPC role NONE VPC state CREATING


 Binding table configuration:
 ----------------------------
 max/box  : no limit
 max/vlan : no limit
 max/port : no limit
 max/mac  : no limit

 Binding table current counters:
 ------------------------------
 dynamic  : 7
 local    : 0
 total    : 7

 Binding table counters by state:
 ----------------------------------
 REACHABLE  : 7
   total    : 7

Codes: L - Local, S - Static, ND - Neighbor Discovery, ARP - Address Resolution Protocol, DH4 - IPv4 DHCP, DH6 - IPv6 DHCP, PKT - Other Packet, API - API created
Preflevel flags (prlvl):
0001:MAC and LLA match     0002:Orig trunk            0004:Orig access           
0008:Orig trusted trunk    0010:Orig trusted access   0020:DHCP assigned         
0040:Cga authenticated     0080:Cert authenticated    0100:Statically assigned   


    Network Layer Address                    Link Layer Address     Interface  mode       vlan/bd(prim)      prlvl      age        state      Time left        Filter     In Crimson   Client ID          Session ID                 Policy (feature) 
ND  FE80::A8BB:CCFF:FE01:6600                aabb.cc01.6600(R)      Et0/2      access     10  (  10)      0005       23s        REACHABLE  280 s            no         yes          0000.0000.0000     (unspecified)              TRACK (Device-tracking)
ND  FE80::A8BB:CCFF:FE01:6500                aabb.cc01.6500(R)      Et0/1      access     10  (  10)      0005       23s        REACHABLE  291 s            no         yes          0000.0000.0000     (unspecified)              TRACK (Device-tracking)
ND  FE80::A8BB:CCFF:FE01:6400                aabb.cc01.6400(R)      Et0/0      access     10  (  10)      0005       13s        REACHABLE  290 s            no         yes          0000.0000.0000     (unspecified)              TRACK (Device-tracking)
ND  2001:DB8:98::1                           aabb.cc01.6500(R)      Et0/1      access     10  (  10)      0005       15s        REACHABLE  285 s            no         yes          0000.0000.0000     (unspecified)              TRACK (Device-tracking)
ND  2001:DB8:33:BAD::1                       aabb.cc01.6600(R)      Et0/2      access     10  (  10)      0005       37s        REACHABLE  263 s            no         yes          0000.0000.0000     (unspecified)              TRACK (Device-tracking)
ND  2001:DB8:33:B:A8BB:CCFF:FE01:6500        aabb.cc01.6500(R)      Et0/1      access     10  (  10)      0005       28s        REACHABLE  283 s            no         yes          0000.0000.0000     (unspecified)              TRACK (Device-tracking)
ND  2001:DB8:33:B::1                         aabb.cc01.6400(R)      Et0/0      access     10  (  10)      0005       39s        REACHABLE  269 s            no         yes          0000.0000.0000     (unspecified)              TRACK (Device-tracking)
```

**P8-0 SWB show device-tracking policies**

```
Target               Type  Policy               Feature        Target range
Et0/0                PORT  ROUTER               RA guard       vlan all
Et0/1                PORT  HOST                 RA guard       vlan all
Et0/2                PORT  HOST                 RA guard       vlan all
vlan 10              VLAN  TRACK                Device-tracking vlan all
```

**P8-0 ガード無し (a) CLB 既定送信元(SLAAC GUA)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/5 ms
```

**P8-0 ガード無し (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:98::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:98::1
.....
Success rate is 0 percent (0/5)
```

**P8-0 ガード無し (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:99::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:99::1
.....
Success rate is 0 percent (0/5)
```

**P8-0 ガード無し RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)**

```
IPv6 access list CNT
    permit icmp 2001:DB8:98::/64 any (5 matches) sequence 10
    permit icmp 2001:DB8:99::/64 any (5 matches) sequence 20
    permit icmp 2001:DB8:33:B::/64 any (7 matches) sequence 30
    permit icmp any any (2 matches) sequence 40
    permit ipv6 any any (1 match) sequence 50
```

- P8-0 ガード無し ping 成功率 a=100% b=0% c=0%

**P8-1 SWB source-guard SG(既定) → Et0/1**

```
ipv6 source-guard policy SG
exit
interface Ethernet0/1
ipv6 source-guard attach-policy SG
exit
---
(応答なし)
```

**P8-1 SWB show ipv6 source-guard policy SG**

```
Source guard policy SG configuration: 
  validate address
Policy SG is applied on the following targets: 
Target               Type  Policy               Feature        Target range
Et0/1                PORT  SG                   Source guard   vlan all
```

**P8-1 SWB show device-tracking policies**

```
Target               Type  Policy               Feature        Target range
Et0/0                PORT  ROUTER               RA guard       vlan all
Et0/1                PORT  HOST                 RA guard       vlan all
Et0/1                PORT  SG                   Source guard   vlan all
Et0/2                PORT  HOST                 RA guard       vlan all
vlan 10              VLAN  TRACK                Device-tracking vlan all
```

**P8-1 source-guard(address) (a) CLB 既定送信元(SLAAC GUA)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/1 ms
```

**P8-1 source-guard(address) (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:98::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:98::1
.....
Success rate is 0 percent (0/5)
```

**P8-1 source-guard(address) (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:99::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:99::1
.....
Success rate is 0 percent (0/5)
```

**P8-1 source-guard(address) RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)**

```
IPv6 access list CNT
    permit icmp 2001:DB8:98::/64 any (5 matches) sequence 10
    permit icmp 2001:DB8:99::/64 any (5 matches) sequence 20
    permit icmp 2001:DB8:33:B::/64 any (5 matches) sequence 30
    permit icmp any any sequence 40
    permit ipv6 any any (1 match) sequence 50
```

- P8-1 source-guard(address) ping 成功率 a=100% b=0% c=0%

**P8-1 SWB show device-tracking counters interface Ethernet0/1**

```
Received messages on Et0/1:
Protocol        Protocol message
NDP             
DHCPv6          INF[1] 
ARP             
DHCPv4          
ACD&DAD         

Received Broadcast/Multicast messages on Et0/1:
Protocol        Protocol message
NDP             
DHCPv6          INF[1] 
ARP             
DHCPv4          

Bridged messages from Et0/1:
Protocol        Protocol message
NDP             
DHCPv6          INF[1] 
ARP             
DHCPv4          
ACD&DAD         

Broadcast/Multicast converted to unicast messages from Et0/1:
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Probe message on Et0/1:
Type            Protocol message
PROBE_SEND      
PROBE_REPLY     

Limited Broadcast to Local message on Et0/1:
Type            Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Dropped messages on Et0/1:
Feature             Protocol Msg [Total dropped]

Faults on Et0/1:
```

**P8-1 SWB show device-tracking database**

```
 VPC role NONE VPC state CREATING
Binding Table has 7 entries, 7 dynamic (limit 200000)
Codes: L - Local, S - Static, ND - Neighbor Discovery, ARP - Address Resolution Protocol, DH4 - IPv4 DHCP, DH6 - IPv6 DHCP, PKT - Other Packet, API - API created
Preflevel flags (prlvl):
0001:MAC and LLA match     0002:Orig trunk            0004:Orig access           
0008:Orig trusted trunk    0010:Orig trusted access   0020:DHCP assigned         
0040:Cga authenticated     0080:Cert authenticated    0100:Statically assigned   


    Network Layer Address                    Link Layer Address     Interface  vlan/bd    prlvl      age        state      Time left       
ND  FE80::A8BB:CCFF:FE01:6600                aabb.cc01.6600         Et0/2      10         0005       42s        REACHABLE  271 s           
ND  FE80::A8BB:CCFF:FE01:6500                aabb.cc01.6500         Et0/1      10         0005       47s        REACHABLE  253 s           
ND  FE80::A8BB:CCFF:FE01:6400                aabb.cc01.6400         Et0/0      10         0005       42s        REACHABLE  267 s           
ND  2001:DB8:98::1                           aabb.cc01.6500         Et0/1      10         0005       71s        REACHABLE  229 s           
ND  2001:DB8:33:BAD::1                       aabb.cc01.6600         Et0/2      10         0005       93s        REACHABLE  207 s           
ND  2001:DB8:33:B:A8BB:CCFF:FE01:6500        aabb.cc01.6500         Et0/1      10         0005       50s        REACHABLE  259 s           
ND  2001:DB8:33:B::1                         aabb.cc01.6400         Et0/0      10         0005       55s        REACHABLE  257 s
```

**P8-1 SWB — SWB show logging**

```

```

**P8-2 SWB PG(validate prefix) → Et0/1**

```
interface Ethernet0/1
no ipv6 source-guard attach-policy SG
exit
ipv6 source-guard policy PG
validate prefix
exit
interface Ethernet0/1
ipv6 source-guard attach-policy PG
exit
---
(応答なし)
```

**P8-2 SWB show ipv6 source-guard policy PG**

```
Source guard policy PG configuration: 
  validate prefix
  validate address
Policy PG is applied on the following targets: 
Target               Type  Policy               Feature        Target range
Et0/1                PORT  PG                   Source guard   vlan all
```

**P8-2 SWB show run | section source-guard**

```
ipv6 source-guard policy PG
 validate prefix
ipv6 source-guard policy SG
 ipv6 source-guard attach-policy PG
```

**P8-2 prefix-guard(validate prefix) (a) CLB 既定送信元(SLAAC GUA)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/1 ms
```

**P8-2 prefix-guard(validate prefix) (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:98::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:98::1
.....
Success rate is 0 percent (0/5)
```

**P8-2 prefix-guard(validate prefix) (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:99::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:99::1
.....
Success rate is 0 percent (0/5)
```

**P8-2 prefix-guard(validate prefix) RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)**

```
IPv6 access list CNT
    permit icmp 2001:DB8:98::/64 any (5 matches) sequence 10
    permit icmp 2001:DB8:99::/64 any (5 matches) sequence 20
    permit icmp 2001:DB8:33:B::/64 any (6 matches) sequence 30
    permit icmp any any (2 matches) sequence 40
    permit ipv6 any any sequence 50
```

- P8-2 prefix-guard(validate prefix) ping 成功率 a=100% b=0% c=0%

**P8-2 SWB show device-tracking counters interface Ethernet0/1**

```
Received messages on Et0/1:
Protocol        Protocol message
NDP             NS[1] NA[2] 
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Received Broadcast/Multicast messages on Et0/1:
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Bridged messages from Et0/1:
Protocol        Protocol message
NDP             NS[1] NA[2] 
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Broadcast/Multicast converted to unicast messages from Et0/1:
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Probe message on Et0/1:
Type            Protocol message
PROBE_SEND      
PROBE_REPLY     

Limited Broadcast to Local message on Et0/1:
Type            Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Dropped messages on Et0/1:
Feature             Protocol Msg [Total dropped]

Faults on Et0/1:
```

**P8-2 SWB show device-tracking database**

```
 VPC role NONE VPC state CREATING
Binding Table has 7 entries, 7 dynamic (limit 200000)
Codes: L - Local, S - Static, ND - Neighbor Discovery, ARP - Address Resolution Protocol, DH4 - IPv4 DHCP, DH6 - IPv6 DHCP, PKT - Other Packet, API - API created
Preflevel flags (prlvl):
0001:MAC and LLA match     0002:Orig trunk            0004:Orig access           
0008:Orig trusted trunk    0010:Orig trusted access   0020:DHCP assigned         
0040:Cga authenticated     0080:Cert authenticated    0100:Statically assigned   


    Network Layer Address                    Link Layer Address     Interface  vlan/bd    prlvl      age        state      Time left       
ND  FE80::A8BB:CCFF:FE01:6600                aabb.cc01.6600         Et0/2      10         0005       77s        REACHABLE  236 s           
ND  FE80::A8BB:CCFF:FE01:6500                aabb.cc01.6500         Et0/1      10         0005       6s         REACHABLE  302 s           
ND  FE80::A8BB:CCFF:FE01:6400                aabb.cc01.6400         Et0/0      10         0005       11s        REACHABLE  294 s           
ND  2001:DB8:98::1                           aabb.cc01.6500         Et0/1      10         0005       106s       REACHABLE  194 s           
ND  2001:DB8:33:BAD::1                       aabb.cc01.6600         Et0/2      10         0005       128s       REACHABLE  172 s           
ND  2001:DB8:33:B:A8BB:CCFF:FE01:6500        aabb.cc01.6500         Et0/1      10         0005       17s        REACHABLE  288 s           
ND  2001:DB8:33:B::1                         aabb.cc01.6400         Et0/0      10         0005       90s        REACHABLE  221 s
```

**P8-2 SWB — SWB show logging**

```

```

**P8-2b PG に validate address 追加**

```
ipv6 source-guard policy PG
validate address
exit
---
(応答なし)
```

**P8-2b SWB show ipv6 source-guard policy PG**

```
Source guard policy PG configuration: 
  validate prefix
  validate address
Policy PG is applied on the following targets: 
Target               Type  Policy               Feature        Target range
Et0/1                PORT  PG                   Source guard   vlan all
```

**P8-2b prefix+address (a) CLB 既定送信元(SLAAC GUA)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
```

**P8-2b prefix+address (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:98::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:98::1
.....
Success rate is 0 percent (0/5)
```

**P8-2b prefix+address (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:99::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:99::1
.....
Success rate is 0 percent (0/5)
```

**P8-2b prefix+address RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)**

```
IPv6 access list CNT
    permit icmp 2001:DB8:98::/64 any (5 matches) sequence 10
    permit icmp 2001:DB8:99::/64 any (5 matches) sequence 20
    permit icmp 2001:DB8:33:B::/64 any (5 matches) sequence 30
    permit icmp any any sequence 40
    permit ipv6 any any sequence 50
```

- P8-2b prefix+address ping 成功率 a=100% b=0% c=0%

**P8-2b SWB show device-tracking counters interface Ethernet0/1**

```
Received messages on Et0/1:
Protocol        Protocol message
NDP             NS[1] NA[1] 
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Received Broadcast/Multicast messages on Et0/1:
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Bridged messages from Et0/1:
Protocol        Protocol message
NDP             NS[1] NA[1] 
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Broadcast/Multicast converted to unicast messages from Et0/1:
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Probe message on Et0/1:
Type            Protocol message
PROBE_SEND      
PROBE_REPLY     

Limited Broadcast to Local message on Et0/1:
Type            Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Dropped messages on Et0/1:
Feature             Protocol Msg [Total dropped]

Faults on Et0/1:
```

**P8-3 SWB destination-guard CLI 有無**

```
ipv6 destination-guard policy DG
enforcement always
exit
```

**P8-3 SWB show run | section destination-guard**

```
ipv6 destination-guard policy DG
```

**P8-3 RT02 未知宛先の静的 ND**

```
ipv6 neighbor 2001:DB8:33:B::DEAD Ethernet0/0 aabb.cc00.0dea
---
(応答なし)
```

**P8-3 DG 無し RT02→CLB 2001:DB8:33:B:A8BB:CCFF:FE01:6500(表にある宛先) — RT02# ping 2001:DB8:33:B:A8BB:CCFF:FE01:6500 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B:A8BB:CCFF:FE01:6500, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/1 ms
```

**P8-3 DG 無し RT02→::DEAD(表に無い宛先・静的 ND) — RT02# ping 2001:DB8:33:B::DEAD repeat 3 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 2001:DB8:33:B::DEAD, timeout is 2 seconds:
...
Success rate is 0 percent (0/3)
```

**P8-3 SWB DG → Et0/0(ルータ側)**

```
interface Ethernet0/0
ipv6 destination-guard attach-policy DG
exit
---
(応答なし)
```

**P8-3 SWB show ipv6 destination-guard policy DG**

```
Destination guard policy DG configuration: 
  enforcement always
Policy DG is applied on the following targets: 
Target               Type  Policy               Feature        Target range
Et0/0                PORT  DG                   Destination Guard vlan all
```

**P8-3 SWB show device-tracking policies**

```
Target               Type  Policy               Feature        Target range
Et0/0                PORT  ROUTER               RA guard       vlan all
Et0/0                PORT  DG                   Destination Guard vlan all
Et0/1                PORT  HOST                 RA guard       vlan all
Et0/2                PORT  HOST                 RA guard       vlan all
vlan 10              VLAN  TRACK                Device-tracking vlan all
```

**P8-3 DG あり RT02→CLB 2001:DB8:33:B:A8BB:CCFF:FE01:6500(表にある宛先) — RT02# ping 2001:DB8:33:B:A8BB:CCFF:FE01:6500 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B:A8BB:CCFF:FE01:6500, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/1 ms
```

**P8-3 DG あり RT02→::DEAD(表に無い宛先) — RT02# ping 2001:DB8:33:B::DEAD repeat 3 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 2001:DB8:33:B::DEAD, timeout is 2 seconds:
...
Success rate is 0 percent (0/3)
```

**P8-3 SWB show device-tracking counters interface Ethernet0/0**

```
Received messages on Et0/0:
Protocol        Protocol message
NDP             NA[1] 
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Received Broadcast/Multicast messages on Et0/0:
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Bridged messages from Et0/0:
Protocol        Protocol message
NDP             NA[1] 
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Broadcast/Multicast converted to unicast messages from Et0/0:
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Probe message on Et0/0:
Type            Protocol message
PROBE_SEND      
PROBE_REPLY     

Limited Broadcast to Local message on Et0/0:
Type            Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Dropped messages on Et0/0:
Feature             Protocol Msg [Total dropped]

Faults on Et0/0:
```

**P8-3 SWB show device-tracking counters vlan 10**

```
Received messages on vlan 10   :
Protocol        Protocol message
NDP             NS[1] NA[1] 
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Received Broadcast/Multicast messages on vlan 10   :
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Bridged messages from vlan 10   :
Protocol        Protocol message
NDP             NS[1] NA[1] 
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Broadcast/Multicast converted to unicast messages from vlan 10   :
Protocol        Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          
ACD&DAD         

Probe message on vlan 10   :
Type            Protocol message
PROBE_SEND      
PROBE_REPLY     

Limited Broadcast to Local message on vlan 10   :
Type            Protocol message
NDP             
DHCPv6          
ARP             
DHCPv4          

Dropped messages on vlan 10   :
Feature             Protocol Msg [Total dropped]

Faults on vlan 10   :
```

**P8-3 SWB — SWB show logging**

```

```
